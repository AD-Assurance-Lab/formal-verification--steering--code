#!/usr/bin/env python3
"""
Bridge from the physical disturbance models to a verifiable prepended layer.

The disturbance models in `disturbance_models.py` act at FULL sensor resolution, and the
network sees a cropped, downsampled image. That whole chain

    theta -> full-resolution disturbance -> crop -> downsample -> network input

is **linear in theta**, because each disturbance is linear in its bounded parameters and
crop plus area-average downsampling are themselves linear. So the composite is exactly a
single `nn.Linear(k, n_pixels)` layer, and we never have to hand-derive it: we recover it
numerically by probing.

    b      = P(model(x0, theta = 0))
    W[:,i] = P(model(x0, theta = e_i)) - b

where P is crop-then-downsample. Then `x'(theta) = W theta + b` exactly, for the real
model at real resolution. This is checked, not assumed: `verify_linearity` compares the
reconstruction against the true model at random theta and reports the residual.

Why this matters: it means the certificate covers the *same* disturbance the closed-loop
simulation injects, at the resolution weather actually acts, with no separate hand-written
"verifiable approximation" that could drift from the model being simulated.

Non-linear terms are handled honestly rather than silently:
  * `clamp` to [0,1] is applied AFTER the linear map, inside the verified network, as
    monotone piecewise-linear ReLU ops (see `perturbations.Clamp01`).
  * the level-matching rescale is a per-frame constant, so it folds into W and b.
  * the additive noise term is a bounded per-pixel box, handled as its own perturbation.
"""
import numpy as np
import torch
import torch.nn as nn
import cv2

from student import student_preprocess, STUDENT_CROP_TOP, STUDENT_CROP_BOT
from perturbations import Clamp01
import disturbance_models as dm


# ---------------------------------------------------------------- linear parameterization
# MEASURED, NOT ASSUMED: probing the models in their PHYSICAL parameters (MOR, etc.)
# gives max pixel errors of 5e-2 to 7.6e-1 against the true model, i.e. they are NOT
# linear in those. Three reasons, all real:
#   1. t = exp(-ln(20)*d/MOR) is exponential in MOR. The models are linear in
#      TRANSMISSION, not in visibility.
#   2. match_level recomputes its gain from the disturbed mean, so the gain varies with
#      theta.
#   3. the models clip internally before projection.
#
# So verification is parameterized by the quantities the models really are linear in:
# per-band transmission plus the structure amplitudes. A visibility interval maps to a
# per-band transmission interval (t is monotone in MOR), so bounding the transmission box
# soundly covers the visibility range; decoupling the bands is an over-approximation,
# which is the safe direction. The exposure gain is fixed at the operating point and that
# approximation is stated rather than hidden.
BANDS = 6


def banded_transmission_box(mor_lo, mor_hi, h_full=480, bands=BANDS,
                            geom=None):
    """Per-band transmission interval induced by a visibility interval."""
    geom = geom or dm.CARLA_GEOM
    t_lo = dm.transmission(h_full, mor_lo, geom)      # denser fog -> lower t
    t_hi = dm.transmission(h_full, mor_hi, geom)
    edges = np.linspace(dm.CARLA_GEOM["horizon_row"], h_full, bands + 1).astype(int)
    lo = np.array([t_lo[a:b].min() for a, b in zip(edges[:-1], edges[1:])])
    hi = np.array([t_hi[a:b].max() for a, b in zip(edges[:-1], edges[1:])])
    return lo, hi, edges


def _apply_banded_veil(x, t_bands, edges, airlight):
    """Veil with a per-band transmission vector; linear in t_bands by construction."""
    A = np.asarray(airlight, np.float32).reshape(1, 1, -1)
    y = x.copy()
    for k, (a, b) in enumerate(zip(edges[:-1], edges[1:])):
        y[a:b] = A + t_bands[k] * (x[a:b] - A)
    y[:edges[0]] = A                                  # above the horizon: pure airlight
    return y


# ---------------------------------------------------------------- parameterizations
# Each entry maps a condition to (theta names, function building kwargs from theta,
# nominal theta, and a default box). theta is always the vector the verifier bounds.
def _fog_kwargs(theta, base):
    return dict(mor_m=float(theta[0]), airlight=tuple(base["airlight"]))


def _rain_kwargs(theta, base):
    return dict(mor_m=float(theta[0]), streaks=float(theta[1]), wet=float(theta[2]),
                specular=base["specular"], pooling=float(theta[3]),
                s_offset_m=base["s_offset_m"])


def _snow_kwargs(theta, base):
    return dict(mor_m=float(theta[0]), flakes=float(theta[1]), wet=base["wet"],
                specular=base["specular"], accumulation=float(theta[2]))


def _night_kwargs(theta, base):
    return dict(ambient=float(theta[0]), noise=0.0, auto_exposure=False)


SPECS = {
    "fog":   dict(names=["mor_m"], fn=_fog_kwargs,
                  base=dict(airlight=(0.78, 0.78, 0.76))),
    "rain":  dict(names=["mor_m", "streaks", "wet", "pooling"], fn=_rain_kwargs,
                  base=dict(specular=0.30, s_offset_m=0.0)),
    "snow":  dict(names=["mor_m", "flakes", "accumulation"], fn=_snow_kwargs,
                  base=dict(wet=0.20, specular=0.14)),
    "night": dict(names=["ambient"], fn=_night_kwargs, base=dict()),
}


def _project(full_bgr_float, w, h, quantize=False):
    """Crop and downsample exactly as the network's preprocessing does.

    `quantize=False` keeps the whole path in float. The deployed pipeline does pass
    through uint8, but that quantisation is a +/-1/255 nonlinearity, and probing a linear
    map by finite differences DIVIDES by the probe step, amplifying it (a step of 0.01
    amplifies quantisation 100x, which is exactly what made an exact linear map look
    nonlinear at 1.6e-1). We therefore recover W in float and cover quantisation
    separately as a small bounded per-pixel term, which is sound and honest.
    """
    if quantize:
        u8 = np.clip(full_bgr_float * 255.0, 0, 255).astype(np.uint8)
        return student_preprocess(u8, w, h)
    # NO clipping here: saturation belongs inside the verified network as ReLU ops.
    # Clipping in the probe makes bright additive layers (streaks, flakes) look
    # nonlinear and silently breaks the recovered map.
    rgb = cv2.cvtColor(np.ascontiguousarray(full_bgr_float), cv2.COLOR_BGR2RGB)
    crop = rgb[STUDENT_CROP_TOP:STUDENT_CROP_BOT]
    return cv2.resize(crop, (w, h), interpolation=cv2.INTER_AREA).transpose(2, 0, 1)


def build_linear_map(cond, x0_full_bgr, theta_nom, deltas, w=84, h=28, match_level=True):
    """Recover (W, b) for the composite disturbance-plus-preprocessing map.

    `theta_nom` is the operating point; `deltas` are the probe steps per parameter. The
    map is linear, so the recovered W is exact up to floating point regardless of the
    step sizes; the deltas only need to avoid degenerate cases (e.g. zero visibility).
    """
    spec = SPECS[cond]
    model = dm.MODELS[cond]

    def render(theta):
        y = model(x0_full_bgr, **spec["fn"](np.asarray(theta, float), spec["base"]))
        if match_level:
            y = dm.match_level(y, x0_full_bgr, cond)
        return _project(y, w, h).reshape(-1)

    b = render(theta_nom)
    cols = []
    for i, d in enumerate(deltas):
        tp = np.array(theta_nom, float)
        tp[i] += d
        cols.append((render(tp) - b) / d)
    W = np.stack(cols, axis=1)                    # (n_pixels, k)
    return W.astype(np.float32), b.astype(np.float32)


def verify_linearity(cond, x0_full_bgr, theta_nom, deltas, box, n=6, w=84, h=28,
                     match_level=True, seed=0):
    """Check the recovered map against the true model at random theta inside the box.

    Reports max absolute pixel error. A large residual means the model is NOT linear in
    the parameters as assumed, which would invalidate the certificate, so this must be
    run before any verification result is reported.
    """
    spec = SPECS[cond]
    model = dm.MODELS[cond]
    W, b = build_linear_map(cond, x0_full_bgr, theta_nom, deltas, w, h, match_level)
    rng = np.random.RandomState(seed)
    lo, hi = np.asarray(box[0], float), np.asarray(box[1], float)
    worst = 0.0
    for _ in range(n):
        th = lo + rng.rand(len(lo)) * (hi - lo)
        y = model(x0_full_bgr, **spec["fn"](th, spec["base"]))
        if match_level:
            y = dm.match_level(y, x0_full_bgr, cond)
        true = _project(y, w, h).reshape(-1)
        pred = b + W @ (th - np.asarray(theta_nom, float))
        worst = max(worst, float(np.abs(true - pred).max()))
    return worst, W, b


class LinearDisturbance(nn.Module):
    """x'(theta) = clamp(W theta_rel + b), the recovered composite map.

    theta_rel is the offset from the operating point, which keeps the bounded input
    centred and is what the verifier perturbs.
    """

    def __init__(self, W, b, shape, clamp=True):
        super().__init__()
        n, k = W.shape
        self.fc = nn.Linear(k, n)
        with torch.no_grad():
            self.fc.weight.copy_(torch.from_numpy(W))
            self.fc.bias.copy_(torch.from_numpy(b))
        self.clamp = Clamp01() if clamp else None
        self.shape = shape
        self.dim = k

    def forward(self, theta_rel):
        x = self.fc(theta_rel).view(self.shape)
        return self.clamp(x) if self.clamp is not None else x


# ---------------------------------------------------------------- per-condition linear maps
def linear_map_for(cond, x0_full_bgr, ranges, w=84, h=28, probe=0.1, seed=0, n_check=6):
    """Build (W, b, lo, hi) for a condition, and CHECK linearity before returning.

    Each condition is parameterized by quantities the model is genuinely linear in:

      fog   : per-band transmission t (visibility interval -> transmission interval)
      rain  : per-band t, streak amplitude, puddle amplitude
      snow  : per-band t, flake amplitude, accumulation amplitude
      night : g = 1/(1+ambient), because x*(L+a)/(1+a) = x*(1 - g*(1-L)) is linear in g
              while it is NOT linear in a

    Returns (W, b, lo, hi, max_linearity_error). Callers must reject the map if the error
    is not near machine precision; a nonlinear parameterization silently invalidates the
    certificate.
    """
    xf = x0_full_bgr.astype(np.float32) / 255.0
    H, Wd = xf.shape[:2]

    if cond == "night":
        L = dm.headlight_field(H, Wd)[..., None].astype(np.float32)
        # RETROREFLECTION. Lane markings are retroreflective by design: they return light
        # toward the source, and the camera sits beside the headlights, so at night the
        # marking-to-asphalt contrast RISES. A model that only scales brightness preserves
        # the daylight contrast ratio and therefore does not look like night to a network
        # trained on it -- which is exactly how the 7f fidelity gate failed (the model
        # left the near field pixel-identical to clear).
        #
        # Retroreflected radiance is proportional to incident headlight irradiance times
        # the surface's retro coefficient. Markings are the bright road pixels, so we use
        # a fixed ReLU basis on the NOMINAL frame: relu(x0 - t_road). That is a constant
        # image given x0, so the term stays LINEAR in its amplitude and verifiable.
        t_road = float(np.percentile(xf[dm.ROAD_TOP:dm.ROAD_BOT], 75))
        retro = (L * np.maximum(xf - t_road, 0.0)).astype(np.float32)
        def render(th):
            g, a_r = float(th[0]), float(th[1])
            return _project((xf * (1.0 - g * (1.0 - L)) + a_r * retro).astype(np.float32),
                            w, h).reshape(-1)
        a_lo, a_hi = ranges["ambient"]
        r_lo, r_hi = ranges.get("retro", (0.0, 3.0))
        lo = np.array([1.0 / (1.0 + a_hi), r_lo])     # g is decreasing in a
        hi = np.array([1.0 / (1.0 + a_lo), r_hi])
    else:
        t_lo, t_hi, edges = banded_transmission_box(ranges["mor"][0], ranges["mor"][1], H)
        A = ranges.get("airlight", (0.76, 0.78, 0.78))
        extras = ranges.get("extras", [])             # list of (layer_array, (lo, hi))
        k = len(t_lo)

        def render(th):
            y = _apply_banded_veil(xf, th[:k], edges, A)
            y = y * (1.0 - ranges.get("wet", 0.0))
            for j, (layer, _) in enumerate(extras):
                y = y + float(th[k + j]) * layer
            return _project(y.astype(np.float32), w, h).reshape(-1)

        lo = np.concatenate([t_lo] + [np.array([e[1][0]]) for e in extras])
        hi = np.concatenate([t_hi] + [np.array([e[1][1]]) for e in extras])

    nom = 0.5 * (lo + hi)
    b = render(nom)
    W = np.stack([(render(nom + np.eye(len(nom))[i] * probe) - b) / probe
                  for i in range(len(nom))], axis=1)

    rng = np.random.RandomState(seed)
    err = 0.0
    for _ in range(n_check):
        th = lo + rng.rand(len(lo)) * (hi - lo)
        err = max(err, float(np.abs(render(th) - (b + W @ (th - nom))).max()))
    return W.astype(np.float32), b.astype(np.float32), lo - nom, hi - nom, err
