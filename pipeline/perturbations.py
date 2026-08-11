#!/usr/bin/env python3
"""
v2 verifiable perturbation modules.

Each module maps a low-dimensional physical parameter vector `theta` in a calibrated
box to a perturbed image, using only layers a bound propagator supports: linear/conv,
and monotone piecewise-linear (ReLU). Prepending one to the student turns
"certify the steering over real-world weather" into a standard bounded-input problem.

Pixel clamping is NOT optional (read this before removing it)
-------------------------------------------------------------
The affine model can push pixels outside [0,1] (the calibrated fog box reaches 1.16,
night's reaches 2.44), and a real camera saturates instead. It is tempting to bound the
unclamped linear map and call it conservative. **That is unsound.** auto_LiRPA bounds
the exact *linear image* of the parameter box, which is much tighter than the box hull;
the true perturbed image `clamp(L(theta))` is generally **not** in that linear image, so
bounds on `f(L(theta))` say nothing about `f(clamp(L(theta)))`.

Clamping is therefore built into the verified network as monotone piecewise-linear ops:

    clamp(v) = min(max(v, 0), 1) = 1 - relu(1 - relu(v))

which costs 2 ReLUs per pixel (14,112 extra at 84x28x3, versus the student's own 5,152).
That is a real cost, and it is the price of a sound certificate. `clamp=False` exists
only for ablation and must never be used for a reported certificate.
"""
import torch
import torch.nn as nn


class Clamp01(nn.Module):
    """Monotone piecewise-linear clamp to [0,1], expressed with ReLUs so a bound
    propagator can handle it exactly."""

    def __init__(self):
        super().__init__()
        self.lo = nn.ReLU()
        self.hi = nn.ReLU()

    def forward(self, x):
        x = self.lo(x)                    # max(x, 0)
        return 1.0 - self.hi(1.0 - x)     # min(x, 1)


class AffinePerturbation(nn.Module):
    """theta = [eps_c, eps_b]  ->  x' = clamp(x0 * (1 + eps_c) + eps_b).

    Implemented as `nn.Linear(2, n_pixels)` with Weight = [x0 | 1], Bias = x0, which is
    the v1 reformulation retained deliberately: the elementwise form triggers a stride-2
    `as_strided` RuntimeError in auto_LiRPA's patches mode.
    """

    def __init__(self, x0, clamp=True):
        super().__init__()
        _, c, h, w = x0.shape
        flat = x0.reshape(-1)
        n = flat.numel()
        self.fc = nn.Linear(2, n)
        with torch.no_grad():
            self.fc.weight.copy_(torch.stack([flat, torch.ones_like(flat)], dim=1))
            self.fc.bias.copy_(flat.clone())
        self.clamp = Clamp01() if clamp else None
        self.shape = (1, c, h, w)
        self.dim = 2

    def forward(self, theta):
        x = self.fc(theta).view(self.shape)
        return self.clamp(x) if self.clamp is not None else x


class ToneCurvePerturbation(nn.Module):
    """Monotone piecewise-linear tone curve with K knots, for conditions whose effect is
    a nonlinear remap of intensity rather than a global gain (night's shadow crush and
    highlight compression).

    x' = clamp( sum_k  delta_k * relu(x0 - t_k) + x0 * (1 + theta_0) )

    The `relu(x0 - t_k)` terms are constants given a fixed nominal frame, so the map is
    LINEAR in theta and stays cheap to bound. Monotonicity is enforced by construction
    only if the deltas are constrained non-negative; we do not impose that here, and
    instead let the calibrated box decide, so a non-monotone curve is representable if
    the data calls for one.
    """

    def __init__(self, x0, knots, clamp=True):
        super().__init__()
        _, c, h, w = x0.shape
        flat = x0.reshape(-1)
        n = flat.numel()
        k = len(knots)
        basis = [flat] + [torch.relu(flat - float(t)) for t in knots]   # (K+1, n)
        self.fc = nn.Linear(k + 1, n)
        with torch.no_grad():
            self.fc.weight.copy_(torch.stack(basis, dim=1))
            self.fc.bias.copy_(flat.clone())
        self.clamp = Clamp01() if clamp else None
        self.shape = (1, c, h, w)
        self.knots = list(knots)
        self.dim = k + 1

    def forward(self, theta):
        x = self.fc(theta).view(self.shape)
        return self.clamp(x) if self.clamp is not None else x


class PerturbedNetwork(nn.Module):
    """Perturbation module followed by the steering network, bounded end to end."""

    def __init__(self, perturbation, base):
        super().__init__()
        self.pert = perturbation
        self.base = base

    def forward(self, theta):
        return self.base(self.pert(theta))


class ContrastPerturbation(nn.Module):
    """Mean-preserving contrast perturbation: x' = clamp(x0 + eps_c * (x0 - mu)).

    This is the correct disturbance model for an **auto-exposed** camera, which is what
    an AV actually runs. Auto-exposure holds the recorded mean roughly constant (measured
    in V2_FINDINGS F16: road brightness across bright daylight and headlight-lit night
    varies by only 1.77x, less than within-set scene variation), so the weather's effect
    that survives to the network is a change in *contrast about the mean*, not an
    absolute brightness shift. Absolute airlight cannot be recovered from auto-exposed
    imagery and is deliberately not modelled.

    Reproduces the calibration by construction: sigma(x') = sigma(x0) * (1 + eps_c) and
    mean(x') = mean(x0), so the estimator `eps_c = sigma_adverse/sigma_clear - 1` is
    exactly this parameter.

    theta is **1-dimensional**, which matters practically: the perturbation set is
    smaller than the 2-D affine box, so fewer clamp ReLUs are unstable, and input-space
    branch-and-bound splits an interval rather than a rectangle.
    """

    def __init__(self, x0, clamp=True):
        super().__init__()
        _, c, h, w = x0.shape
        flat = x0.reshape(-1)
        mu = float(flat.mean())
        self.fc = nn.Linear(1, flat.numel())
        with torch.no_grad():
            self.fc.weight.copy_((flat - mu).unsqueeze(1))
            self.fc.bias.copy_(flat.clone())
        self.clamp = Clamp01() if clamp else None
        self.shape = (1, c, h, w)
        self.mu = mu
        self.dim = 1

    def forward(self, theta):
        x = self.fc(theta).view(self.shape)
        return self.clamp(x) if self.clamp is not None else x


class FogVeilPerturbation(nn.Module):
    """Depth-dependent Koschmieder veiling: x' = clamp(A + t_row * (x0 - A)).

    This is the term F19 showed we cannot do without. Unlike a global contrast map,
    which is invertible and therefore preserves all information, veiling **destroys**
    it: as t -> 0 in the far field, distant content is replaced by the airlight A and
    lane markings at range cease to exist. That is the dominant real hazard of fog, and
    the reason a clear-trained model sails through a contrast-only perturbation.

    Parameterization. `theta` is the per-row transmission vector `t`, so the map is
    LINEAR in theta (`A` is a constant), hence one prepended linear layer as usual.
    Physically the rows are coupled through a single extinction coefficient,
    `t(d) = exp(-beta*d)`, and `d(row)` comes from the platform's exact known geometry.
    Verifying over a beta *interval* therefore means verifying over a 1-D curve in
    t-space; we bound it by the per-row t-interval it induces, which is sound and, since
    t is monotone in beta, tight per row.

    Depth within one output row spans a wide range near the horizon, so each output row's
    transmission is the average of exp(-beta*d) over the input rows that map into it,
    matching what INTER_AREA downsampling does to the image itself.
    """

    def __init__(self, x0, t_rows, airlight, clamp=True):
        super().__init__()
        _, c, h, w = x0.shape
        A = float(airlight)
        t = torch.as_tensor(t_rows, dtype=x0.dtype, device=x0.device).reshape(1, 1, h, 1)
        # x' = A + t*(x0 - A); linear in t with coefficient (x0 - A) and offset A
        coeff = (x0 - A).expand(1, c, h, w).reshape(-1)
        self.register_buffer("coeff", coeff)
        self.register_buffer("t_shape", torch.zeros(0))
        n = coeff.numel()
        self.fc = nn.Linear(h, n)
        with torch.no_grad():
            # column j of the weight selects the pixels belonging to output row j
            W = torch.zeros(n, h, dtype=x0.dtype, device=x0.device)
            flat_idx = torch.arange(n, device=x0.device).reshape(1, c, h, w)
            for j in range(h):
                mask = (flat_idx[:, :, j, :].reshape(-1))
                W[mask, j] = coeff.reshape(1, c, h, w)[:, :, j, :].reshape(-1)
            self.fc.weight.copy_(W)
            self.fc.bias.copy_(torch.full((n,), A, dtype=x0.dtype))
        self.clamp = Clamp01() if clamp else None
        self.shape = (1, c, h, w)
        self.A = A
        self.dim = h
        self.t_nominal = t.reshape(-1).clone()

    def forward(self, t):
        x = self.fc(t).view(self.shape)
        return self.clamp(x) if self.clamp is not None else x


def transmission_rows(beta, in_h, crop_top, crop_bot, f_px, h_cam_m, horizon_row):
    """Per-output-row transmission for a given extinction coefficient.

    Averages exp(-beta*d) over the source rows that fall into each output row, so rows
    near the horizon (where depth spans a huge range) get the correct mean attenuation
    rather than the value at a single depth.
    """
    import numpy as np
    edges = np.linspace(crop_top, crop_bot, in_h + 1)
    out = np.empty(in_h)
    for j in range(in_h):
        rows = np.arange(np.floor(edges[j]), np.ceil(edges[j + 1])) + 0.5
        below = rows - horizon_row
        d = np.where(below > 0, h_cam_m * f_px / np.maximum(below, 1e-9), np.inf)
        out[j] = np.mean(np.exp(-beta * d))          # exp(-beta*inf) = 0
    return out


# =================================================================================
# Condition-specific structure on top of the shared visibility core
# =================================================================================
# Every adverse condition imposes (a) a VISIBILITY LIMIT, which destroys far-field
# information, plus (b) condition-specific near-field structure. Parameterizing (a) by
# meteorological optical range keeps all four conditions on one measured, standardized
# axis and avoids leaning on rate-to-visibility conversions, which Rasmussen et al.
# (1999) show vary widely with crystal type, riming and wetness for snow, and which are
# similarly scattered for rain.
#
#   fog   : veiling only
#   rain  : veiling + bright oriented streaks
#   snow  : veiling toward white + bright flake blobs (occlusion-like)
#   night : beam-limited illumination (headlights reach ~60-70 m) + sensor noise
#
# All remain LINEAR in their bounded parameters, so each is one prepended linear layer.

def streak_basis(h, w, angle_deg=15.0, density=0.02, length=9, seed=0):
    """Fixed oriented streak pattern for rain, normalized to max 1.

    The pattern is FIXED and only its amplitude is bounded, which keeps the model linear
    and verifiable. Real streak placement is random per frame; bounding the amplitude of
    a fixed basis covers a family of intensities rather than every placement, which is a
    stated approximation, not a hidden one.
    """
    import numpy as np
    rng = np.random.RandomState(seed)
    img = np.zeros((h, w), np.float32)
    n = max(1, int(density * h * w / length))
    dy = np.cos(np.radians(angle_deg))
    dx = np.sin(np.radians(angle_deg))
    for _ in range(n):
        y0, x0 = rng.randint(0, h), rng.randint(0, w)
        for k in range(length):
            y, x = int(y0 + k * dy), int(x0 + k * dx)
            if 0 <= y < h and 0 <= x < w:
                img[y, x] = 1.0
    if img.max() > 0:
        img /= img.max()
    return img


def blob_basis(h, w, density=0.004, radius=1, seed=0):
    """Fixed bright-blob pattern for snow flakes, normalized to max 1.

    Flakes *replace* content rather than adding to it, which is genuinely non-affine.
    Modelling them as a bounded additive bright layer is an over-approximation of
    occlusion in the bright direction and an under-approximation of full replacement;
    that limitation is the honest edge of what this paradigm certifies.
    """
    import numpy as np
    rng = np.random.RandomState(seed)
    img = np.zeros((h, w), np.float32)
    for _ in range(max(1, int(density * h * w))):
        y, x = rng.randint(0, h), rng.randint(0, w)
        y0, y1 = max(0, y - radius), min(h, y + radius + 1)
        x0, x1 = max(0, x - radius), min(w, x + radius + 1)
        img[y0:y1, x0:x1] = 1.0
    return img


def headlight_rows(h, crop_top, crop_bot, f_px, h_cam_m, horizon_row, **kw):
    """Per-output-row relative headlight illumination, reduced from `headlight.py`."""
    import numpy as np
    from headlight import headlight_map
    L = headlight_map(int(crop_bot) + 1, 64, f_px, h_cam_m, horizon_row, **kw)
    edges = np.linspace(crop_top, crop_bot, h + 1).astype(int)
    prof = L.max(axis=1)
    return np.array([prof[edges[j]:edges[j + 1]].mean() for j in range(h)])
