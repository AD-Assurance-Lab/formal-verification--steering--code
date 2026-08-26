#!/usr/bin/env python3
"""M6: run one verification sweep and write it to the ledger as a cell. No CARLA.

This is the right half of the ledger. `certify_fog.py` / `certify_night.py` are the
per-condition studies; this is the thing that produces a VERDICT, using the aggregation
rule pre-registered in `study.design.verify_verdict` before any cell was run.

    python scripts/certify_cell.py --student S_clear_84x28 --condition fog \
        --channels 8,16,16 --fc 32 --cell-name S_clear

The blind protocol (CLAUDE.md) requires these to be committed BEFORE the matching
closed-loop cell. `python -m study.ledger --check-order` checks that against git history.

Corridor is centred on CLEAR-WEATHER steering, not on the disturbed midpoint (trap 6).
Centring on the midpoint certifies insensitivity to the disturbance parameter while
allowing an arbitrary systematic offset from what clear weather would do -- which is the
actual hazard, and the bug that once made night read 100% certified while failing 85% of
closed-loop frames.
"""

import argparse
import csv
import heapq
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "pipeline"))

import config as C  # noqa: E402
import disturbance_models as dm  # noqa: E402
import verifiable_disturbance as vd  # noqa: E402
from student import StudentNet  # noqa: E402
from study import design  # noqa: E402

from auto_LiRPA import BoundedModule, BoundedTensor, PerturbationLpNorm  # noqa: E402

LEDGER = REPO / "results" / "ledger"
SHADOW_MASK = REPO / "results" / "calibration" / "shadow_mask.npy"
# Prefer the frozen-physics sweep: the earlier one captured 0.29 m above ride height,
# which biases depth-per-row and therefore the (MOR, k) fit. See D-04.
FOG_CAL = REPO / "results" / "calibration" / "fog_density_sweep_frozen.json"
FOG_CAL_OLD = REPO / "results" / "calibration" / "fog_density_sweep.json"
FOG_CAL_FALLBACK = REPO / "results" / "calibration" / "operating_point_fog.json"

# Declared axes, in the LINEARIZED parameterization each condition is affine in.
NIGHT_AMBIENT = (0.02, 0.50)
NIGHT_RETRO = (0.0, 3.0)
FOG_MOR = (60.0, 2000.0)
SHADOW_DEPTH = (0.0, 1.0)      # s in x0*(1-s*S); s=0 clear, s=1 IS the measured CARLA shadows frame


def clear_frames(n):
    """Clear-weather frames sampled evenly along the route, both directions."""
    base = REPO / "pipeline" / "data" / "conditions"
    with open(base / "manifest.csv") as fh:
        rows = [r for r in csv.DictReader(fh) if r["weather"] == "clear"]
    picks = rows[:: max(1, len(rows) // n)][:n]
    return [cv2.imread(str(base / r["image"])) for r in picks]


def paired_frames(n, other, max_pos_m=0.15, max_yaw_deg=0.30):
    """(clear, other) frames at the SAME POSE, sampled evenly along the route.

    Needed because a mask averaged over many poses is not a shadow mask. Cast shadows are
    static in the world and therefore MOVE through the image as the ego drives, so
    averaging ratio images across poses blurs them into a smooth global dimming and throws
    away the very spatial structure that distinguishes shadows from a brightness change.

    Pairing is possible because the ego drives the same scripted route under each condition
    and the manifest records (x, y, yaw). Pairs looser than the thresholds are dropped.
    """
    base = REPO / "pipeline" / "data" / "conditions"
    with open(base / "manifest.csv") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for direction in ("eastbound", "westbound"):
        cr = [r for r in rows if r["weather"] == "clear" and r["direction"] == direction]
        orr = [r for r in rows if r["weather"] == other and r["direction"] == direction]
        if not cr or not orr:
            continue
        cp = np.array([[float(r["x"]), float(r["y"]), float(r["yaw"])] for r in cr])
        op = np.array([[float(r["x"]), float(r["y"]), float(r["yaw"])] for r in orr])
        dist = np.linalg.norm(cp[:, None, :2] - op[None, :, :2], axis=2)
        j = dist.argmin(1)
        dmin = dist[np.arange(len(cp)), j]
        dyaw = np.abs(((cp[:, 2] - op[j, 2] + 180) % 360) - 180)
        ok = np.flatnonzero((dmin < max_pos_m) & (dyaw < max_yaw_deg))
        for i in ok:
            out.append((cr[i], orr[j[i]], float(dmin[i])))
    out = out[:: max(1, len(out) // n)][:n]
    return [(cv2.imread(str(base / a["image"])), cv2.imread(str(base / b["image"])), d)
            for a, b, d in out]


def clear_steer(student, xf, device, w, h):
    with torch.no_grad():
        return float(student(torch.from_numpy(
            vd._project(xf, w, h).reshape(1, 3, h, w).astype(np.float32)).to(device)).item())


# ── per-condition linear maps ────────────────────────────────────────────────
# Each returns a callable (lo, hi) -> (W, b) giving the affine map from a box in the
# linearized parameter u to the student's input, plus the initial box.

def fog_map(xf, w, h, airlight):
    """Rank-1 in one scalar per MOR sub-interval. Transmission is PER-ROW, never banded
    (F8: 6-band discretization was the binding constraint, not the method)."""
    H = xf.shape[0]
    A = np.asarray(airlight, np.float32).reshape(1, 1, 3)

    def veil(t_rows):
        return A + t_rows.astype(np.float32).reshape(-1, 1, 1) * (xf - A)

    def build(lo, hi):
        # box is in MOR metres; rank-1 reparameterization s in [-1, 1]
        t_lo = dm.transmission(H, hi[0], dm.CARLA_GEOM)   # larger MOR -> larger t
        t_hi = dm.transmission(H, lo[0], dm.CARLA_GEOM)
        tbar, delta = 0.5 * (t_lo + t_hi), 0.5 * (t_hi - t_lo)
        b = vd._project(veil(tbar), w, h).reshape(-1).astype(np.float32)
        W = (vd._project(veil(tbar + delta), w, h).reshape(-1).astype(np.float32)
             - b).reshape(-1, 1)
        return W, b, np.array([-1.0]), np.array([1.0])

    return build, np.array([FOG_MOR[0]]), np.array([FOG_MOR[1]])


def fog_map_illum(xf, w, h, airlight, k_range):
    """Koschmieder WITH surface-illumination attenuation, rank-1 per MOR sub-interval.

        x'(MOR) = A*(1 - t(MOR)) + t(MOR) * k(MOR) * x0
        u1 = t(MOR),  u2 = t(MOR) * k,  k in a MEASURED INTERVAL

    Plain Koschmieder (`fog_map`) is retained only as a diagnostic: measured against
    pose-paired CARLA frames it fails D3(a), brightening the road ROI by +0.015 where CARLA
    darkens it by -0.031, at ROI R^2 -0.03. Certifying our students against it would
    reproduce the train/verify family mismatch CLAUDE.md blames for the previous study.

    `k` is the attenuation of the sunlight reaching the road. It is BOUNDED, not fitted --
    see render_u for why -- so a sub-interval is rank-2 in (u1, u2) rather than rank-1.
    """
    H = xf.shape[0]
    A = np.asarray(airlight, np.float32).reshape(1, 1, 3)
    k_lo, k_hi = k_range

    def render_u(u1, u2):
        """x' = A*(1 - u1) + u2 * x0, with u1 = t and u2 = t*k, both per row.

        BOUNDING k RATHER THAN FITTING IT. Two honest fits disagree: route frames put
        k ~ 0.70 at fog_density 70 with a sharp rmse minimum, the static-pose sweep puts it
        near 1.1. Picking either would be choosing the number that suits me. Treating k as
        an INTERVAL that contains both is sound whichever is right, and the cost is that a
        sub-interval becomes rank-2 instead of rank-1 -- d = 2, which night already pays.

        u1 and u2 are bounded independently even though u2 = u1*k couples them. That is an
        over-approximation, never an under-approximation, so certificates stay valid and
        only tightness suffers.
        """
        y = A * (1.0 - u1) + u2 * xf
        return vd._project(y.astype(np.float32), w, h).reshape(-1).astype(np.float32)

    def _t(mor):
        return dm.transmission(H, mor, dm.CARLA_GEOM).astype(np.float32).reshape(-1, 1, 1)

    def _boxes(lo, hi):
        t_lo, t_hi = _t(float(lo[0])), _t(float(hi[0]))   # larger MOR -> larger t
        u1_bar, u1_del = 0.5 * (t_lo + t_hi), 0.5 * (t_hi - t_lo)
        p_lo, p_hi = t_lo * k_lo, t_hi * k_hi
        u2_bar, u2_del = 0.5 * (p_lo + p_hi), 0.5 * (p_hi - p_lo)
        return u1_bar, u1_del, u2_bar, u2_del

    def render(mor, k=None):
        """The TRUE map at a physical (MOR, k), used for the deviation check."""
        t = _t(mor)
        kk = 0.5 * (k_lo + k_hi) if k is None else k
        return render_u(t, t * kk)

    def build(lo, hi):
        u1_bar, u1_del, u2_bar, u2_del = _boxes(lo, hi)
        b = render_u(u1_bar, u2_bar)
        c1 = render_u(u1_bar + u1_del, u2_bar) - b
        c2 = render_u(u1_bar, u2_bar + u2_del) - b
        W = np.stack([c1, c2], axis=1)
        return W, b, np.array([-1.0, -1.0]), np.array([1.0, 1.0])

    def deviation(lo, hi, n=5):
        """Max distance from the true x'(MOR) curve to the rank-1 SEGMENT, in pixel units.

        The rank-1 trick interpolates between the sub-interval endpoints, but the true
        curve bows away from that chord, so the bound is only as sound as this deviation is
        small. `DISTURBANCE_MATH.md` says it shrinks quadratically as the interval narrows
        and that it is 'bounded analytically' -- but nothing in the code ever measured it,
        so the claim rode on an assertion. This CAN measure it per cell.

        **It has no callers.** Attaching it to `build` was as far as this got, so the
        rank-1 chord error is still unmeasured and the docstring above still describes an
        intention rather than a check that runs. Two consequences worth being precise
        about: it affects only the rank-1 path used by the RETIRED per-condition
        instrument, not `certify_sustained_bound.py`, whose family is a chord by
        construction rather than an approximation to a curve; and anyone reviving that
        path must call this first.
        """
        W, b, _, _ = build(lo, hi)
        worst = 0.0
        G = W.T @ W
        for m in np.linspace(float(lo[0]), float(hi[0]), n):
            for kk in (k_range[0], 0.5 * (k_range[0] + k_range[1]), k_range[1]):
                y = render(float(m), kk)
                rhs = W.T @ (y - b)
                try:
                    coef = np.linalg.solve(G, rhs)
                except np.linalg.LinAlgError:
                    continue
                coef = np.clip(coef, -1.0, 1.0)
                worst = max(worst, float(np.abs(y - (b + W @ coef)).max()))
        return worst

    build.deviation = deviation
    return build, np.array([FOG_MOR[0]]), np.array([FOG_MOR[1]])


NIGHT_GAIN = REPO / "results" / "calibration" / "night_gain.npy"
NIGHT_S = (0.0, 1.0)   # s=0 clear, s=1 the MEASURED CARLA night


def night_map_gain(xf, w, h, G):
    """Night as a MEASURED illumination field: x' = x0 * (1 + s*(G-1)). d = 1.

    Replaces the analytic ambient-plus-assumed-beam model, which reproduced CARLA at
    road-ROI R^2 0.243 and drove S_mixed's steering 27x further than reality. The assumed
    beam shape was wrong, and the multiplicative form could only dim, while CARLA's
    headlight pool is 1.42x BRIGHTER than the overcast clear baseline near the bumper.

    G is measured from pose-paired frames and is predictive -- applying it needs only the
    clear image. Held out: road-ROI R^2 +0.832. It captures ambient dimming and the
    headlight pool (fixed in image coordinates, so it survives pooling over poses); it does
    NOT capture retroreflection off markings, which move between poses and average out.

    Values stay in [0,1] wherever G <= 1/x0, so unlike the old model this one rarely
    saturates and does not need the sensor-clamp path.
    """
    Gf = G.astype(np.float32)

    def render(s):
        return vd._project((xf * (1.0 + s * (Gf - 1.0))).astype(np.float32),
                           w, h).reshape(-1).astype(np.float32)

    def build(lo, hi):
        mid = 0.5 * (lo + hi)
        b = render(float(mid[0]))
        W = ((render(float(mid[0]) + 1e-2) - b) / 1e-2).reshape(-1, 1)
        return W, b, lo - mid, hi - mid

    return build, np.array([NIGHT_S[0]]), np.array([NIGHT_S[1]])


def night_map_sensor(xf, R, Cm):
    """Night with saturation applied at SENSOR resolution (physically correct).

    `night_map` clamps the 84x28 projection; the camera clamps before downsampling. The
    fitted retroreflection amplitude is negative, so night is the one condition that leaves
    [0,1], and the two orderings differ by up to 1.3e-2 -- larger than the 0.012 corridor.
    Measured against the true composition this path is exact to ~1e-07 where the old one
    was off by 1.3e-02.
    """
    H, Wd = xf.shape[:2]
    L = dm.headlight_field(H, Wd)[..., None].astype(np.float32)
    t_road = float(np.percentile(xf[dm.ROAD_TOP:dm.ROAD_BOT], 75))
    retro = (L * np.maximum(xf - t_road, 0.0)).astype(np.float32)

    def render_full(g, a_r):
        y = xf * (1.0 - g * (1.0 - L)) + a_r * retro
        return vd.project_crop_rgb(y.astype(np.float32)).reshape(-1).astype(np.float32)

    shape = vd.project_crop_rgb(xf).shape

    def build(lo, hi):
        mid = 0.5 * (lo + hi)
        b = render_full(*mid)
        cols = [(render_full(mid[0] + 1e-2, mid[1]) - b) / 1e-2,
                (render_full(mid[0], mid[1] + 1e-2) - b) / 1e-2]
        return np.stack(cols, 1), b, lo - mid, hi - mid

    build.sensor = (R, Cm, shape)
    return build, np.array([1.0 / (1.0 + NIGHT_AMBIENT[1]), NIGHT_RETRO[0]]), \
        np.array([1.0 / (1.0 + NIGHT_AMBIENT[0]), NIGHT_RETRO[1]])


class SensorBounder:
    """Bounder for maps whose clamp lives at sensor resolution.

    Unlike `Bounder` this cannot cache the traced graph: which pixels are provably stable
    depends on the box, so the module is rebuilt per sub-box. That is cheap -- only the
    genuinely unstable pixels carry ReLUs (~500 of 403,200 at the night operating point),
    so each graph is small even though the underlying image is not.
    """

    def __init__(self, k, student, device, R, Cm, shape):
        self.k, self.student, self.device = k, student, device
        self.R, self.Cm, self.shape = R, Cm, shape

    def __call__(self, W, b, lo, hi):
        head = vd.SparseSensorDisturbance(W, b, self.R, self.Cm, self.shape, lo, hi)
        net = nn.Sequential(head, self.student).to(self.device).eval()
        centre = torch.zeros(1, self.k, device=self.device)
        ptb = PerturbationLpNorm(
            norm=float("inf"),
            x_L=torch.tensor(lo, dtype=torch.float32, device=self.device).unsqueeze(0),
            x_U=torch.tensor(hi, dtype=torch.float32, device=self.device).unsqueeze(0))
        bm = BoundedModule(net, torch.empty_like(centre), device=self.device)
        lb, ub = bm.compute_bounds(x=(BoundedTensor(centre, ptb),),
                                   method="CROWN-Optimized")
        out = float(lb.min()), float(ub.max())
        del bm, net, head
        return out


def night_map(xf, w, h):
    """d = 2, exactly affine in u = (g, a_retro) by construction."""
    H, Wd = xf.shape[:2]
    L = dm.headlight_field(H, Wd)[..., None].astype(np.float32)
    t_road = float(np.percentile(xf[dm.ROAD_TOP:dm.ROAD_BOT], 75))
    retro = (L * np.maximum(xf - t_road, 0.0)).astype(np.float32)

    def render(g, a_r):
        return vd._project((xf * (1.0 - g * (1.0 - L)) + a_r * retro).astype(np.float32),
                           w, h).reshape(-1).astype(np.float32)

    def build(lo, hi):
        mid = 0.5 * (lo + hi)
        b = render(*mid)
        cols = [(render(mid[0] + 1e-2, mid[1]) - b) / 1e-2,
                (render(mid[0], mid[1] + 1e-2) - b) / 1e-2]
        return np.stack(cols, 1), b, lo - mid, hi - mid

    # g = 1/(1+ambient) is decreasing in ambient
    return build, np.array([1.0 / (1.0 + NIGHT_AMBIENT[1]), NIGHT_RETRO[0]]), \
        np.array([1.0 / (1.0 + NIGHT_AMBIENT[0]), NIGHT_RETRO[1]])


def shadow_map(xf, w, h, mask):
    """d = 1, fixed mask with bounded depth: x' = x0 * (1 - s*S). Affine in s.

    The mask is MEASURED from this frame's own pose-matched shadows counterpart, per
    channel (a low sun could warm as well as dim). Letting the mask move with solar
    elevation is NOT affine (DISTURBANCE_MATH.md) and is deliberately not attempted --
    but the mask may be measured PER FRAME, which is different: for a given frame it is a
    constant image, so the map stays affine in the single bounded parameter s.

    WHAT s MEANS, AND WHY THE AXIS IS ALREADY CALIBRATED. S is the raw fractional dimming
    1 - shadows/clear, unnormalized, so s = 1 reproduces the observed CARLA shadows frame
    exactly and s = 0 is clear. The axis is therefore "fraction of the measured solar
    elevation 90 -> 15 effect", and the closed-loop operating point sits at exactly s = 1.
    That is the preset-to-axis alignment M5 still owes fog and night; for shadows it falls
    out of the measurement.
    """
    S = mask.astype(np.float32)
    if S.ndim == 2:
        S = S[..., None]

    def render(s):
        return vd._project((xf * (1.0 - s * S)).astype(np.float32),
                           w, h).reshape(-1).astype(np.float32)

    def build(lo, hi):
        mid = 0.5 * (lo + hi)
        b = render(float(mid[0]))
        W = ((render(float(mid[0]) + 1e-2) - b) / 1e-2).reshape(-1, 1)
        return W, b, lo - mid, hi - mid

    return build, np.array([SHADOW_DEPTH[0]]), np.array([SHADOW_DEPTH[1]])


# ── branch and bound ─────────────────────────────────────────────────────────
class Bounder:
    """alpha-CROWN over a rebindable affine head.

    Constructing a BoundedModule costs far more than the bound itself here -- the network
    is tiny and the graph trace dominates. Since every sub-box differs only in the WEIGHTS
    of the leading Linear layer, the graph is identical and can be traced once per frame,
    then rebound in place. Measured: ~8.3 s/bound rebuilding versus the time below.

    This is a soundness-relevant shortcut, so `check_equivalence` verifies it against a
    freshly constructed module rather than assuming auto_LiRPA reads live weights.
    """

    def __init__(self, k, student, device, h, w, method="CROWN-Optimized"):
        # `method` is selectable because the closed-loop tube needs thousands of bounds
        # rather than dozens. Measured on this network, one interpolation cell: CROWN 47 ms
        # at width 0.0186 against CROWN-Optimized 3654 ms at width 0.0175 -- 78x the cost
        # for 6% tightness, which turns a 7.5-minute sweep into a 10-hour one. IBP is not a
        # valid option here at width 1.42, 76x looser than either.
        self.device, self.k, self.method = device, k, method
        dummy_W = np.zeros((3 * h * w, k), np.float32)
        dummy_b = np.zeros(3 * h * w, np.float32)
        self.head = vd.LinearDisturbance(dummy_W, dummy_b, (1, 3, h, w))
        self.net = nn.Sequential(self.head, student).to(device).eval()
        self.centre = torch.zeros(1, k, device=device)
        self.bounded = BoundedModule(self.net, torch.empty_like(self.centre),
                                     device=device)

    def _bind(self, W, b):
        with torch.no_grad():
            self.head.fc.weight.copy_(torch.from_numpy(W).to(self.device))
            self.head.fc.bias.copy_(torch.from_numpy(b).to(self.device))

    def __call__(self, W, b, lo, hi):
        self._bind(W, b)
        ptb = PerturbationLpNorm(
            norm=float("inf"),
            x_L=torch.tensor(lo, dtype=torch.float32, device=self.device).unsqueeze(0),
            x_U=torch.tensor(hi, dtype=torch.float32, device=self.device).unsqueeze(0))
        lb, ub = self.bounded.compute_bounds(
            x=(BoundedTensor(self.centre, ptb),), method=self.method)
        return float(lb.min()), float(ub.max())

    def check_equivalence(self, W, b, lo, hi, student, h, w, tol=1e-4):
        """Same box, cached module vs a fresh one, PLUS a staleness probe.

        Two things are being checked, and only the second is really about soundness:

        1. AGREEMENT. Tolerance is relative to the bound's own width, not absolute. The
           bound is optimised (CROWN-Optimized runs a gradient loop on the alpha
           parameters with early stopping), so two independent constructions converge to
           slightly different alphas. Every alpha yields a VALID bound -- that is what
           alpha-CROWN soundness means -- so a small disagreement is optimiser noise, not
           unsoundness. Measured: 1.6e-07 on the 5,152-ReLU student against a bound width
           of 0.21, and 2.8e-04 on the 15,456-ReLU student against a width of 2.12. Both
           are ~1e-6 to 1e-4 RELATIVE; an absolute 1e-4 threshold simply scales wrong with
           network size and bound magnitude.

        2. STALENESS -- the failure this guard actually exists for. If the cached module
           ignored the rebound weights it would silently evaluate every sub-box with the
           FIRST box's map. That does not look like 0.02%; it looks like the bound not
           moving at all. So bind a materially different W and require the bound to move
           far more than the agreement tolerance.
        """
        l1, u1 = self(W, b, lo, hi)
        fresh_net = nn.Sequential(vd.LinearDisturbance(W, b, (1, 3, h, w)),
                                  student).to(self.device).eval()
        centre = torch.zeros(1, self.k, device=self.device)
        ptb = PerturbationLpNorm(
            norm=float("inf"),
            x_L=torch.tensor(lo, dtype=torch.float32, device=self.device).unsqueeze(0),
            x_U=torch.tensor(hi, dtype=torch.float32, device=self.device).unsqueeze(0))
        fresh = BoundedModule(fresh_net, torch.empty_like(centre), device=self.device)
        l2, u2 = fresh.compute_bounds(x=(BoundedTensor(centre, ptb),),
                                      method="CROWN-Optimized")
        l2, u2 = float(l2.min()), float(u2.max())
        err = max(abs(l1 - l2), abs(u1 - u2))
        width = max(abs(u2 - l2), 1e-9)
        rel_tol = max(tol, 1e-3 * width)
        agree = err <= rel_tol

        # staleness probe: a halved map must produce a visibly different bound
        l3, u3 = self(0.5 * W, b, lo, hi)
        moved = max(abs(l3 - l1), abs(u3 - u1))
        # Staleness shows up as the bound NOT MOVING when the map changes, so the probe
        # must be compared against how much cached and fresh disagree -- not against the
        # tolerance. Keying it to rel_tol misfires whenever the bound is legitimately
        # narrow: shadows on S_mixed agrees to 3.0e-08 and the probe moved 9.0e-04, a
        # 30,000x separation that is obviously responsive, yet 9.0e-04 < 10*rel_tol
        # aborted the sweep.
        responsive = moved > 100.0 * max(err, 1e-9)
        # restore the real map before the sweep uses this bounder
        self._bind(W, b)
        return (agree and responsive), err, (l1, u1), (l2, u2), rel_tol, moved


def sweep(build, box_lo, box_hi, bounder, corridor, budget):
    """Largest-volume-first BaB over the declared axis box.

    Largest-first, NOT LIFO: `stack.pop()` is depth-first on the smallest box, which
    descends into a tiny corner while large undecided siblings sit untouched. Measured
    symptom of that bug: raising the budget 48 -> 400 changed resolved volume by nothing.
    """
    total = float(np.prod(box_hi - box_lo))
    heap, cells, n, ctr = [], [], 0, 0
    heapq.heappush(heap, (-total, ctr, box_lo, box_hi))
    while heap and n < budget:
        _, _, lo, hi = heapq.heappop(heap)
        W, b, u_lo, u_hi = build(lo, hi)
        l, u = bounder(W, b, u_lo, u_hi)
        n += 1
        vol = float(np.prod(hi - lo))
        if l >= corridor[0] and u <= corridor[1]:
            cells.append(("CERTIFIED", vol, lo.tolist(), hi.tolist()))
        elif u < corridor[0] or l > corridor[1]:
            cells.append(("FALSIFIED", vol, lo.tolist(), hi.tolist()))
        else:
            d = int(np.argmax(hi - lo))
            mid = 0.5 * (lo[d] + hi[d])
            a_hi = hi.copy(); a_hi[d] = mid
            b_lo = lo.copy(); b_lo[d] = mid
            for s_lo, s_hi in ((lo, a_hi), (b_lo, hi)):
                ctr += 1
                heapq.heappush(heap, (-float(np.prod(s_hi - s_lo)), ctr, s_lo, s_hi))
    for _, _, lo, hi in heap:
        cells.append(("UNKNOWN", float(np.prod(hi - lo)), lo.tolist(), hi.tolist()))
    frac = {v: sum(x for t, x, _, _ in cells if t == v) / total
            for v in ("CERTIFIED", "FALSIFIED", "UNKNOWN")}
    return frac, n, cells


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--student", required=True)
    ap.add_argument("--condition", required=True,
                    choices=["clear", "fog", "night", "shadows"])
    ap.add_argument("--cell-name", required=True, help="ledger name: S_clear or S_mixed")
    ap.add_argument("--channels", default="8,16,16")
    ap.add_argument("--fc", type=int, default=32)
    ap.add_argument("--w", type=int, default=84)
    ap.add_argument("--h", type=int, default=28)
    ap.add_argument("--frames", type=int, default=design.VERIFY_FRAMES)
    ap.add_argument("--budget", type=int, default=design.VERIFY_CELL_BUDGET)
    ap.add_argument("--fog-model", choices=["illum", "koschmieder"], default="illum",
                    help="'koschmieder' is the D3-failing diagnostic; see FINDINGS")
    ap.add_argument("--night-analytic", action="store_true",
                    help="use the superseded analytic beam model (R^2 0.243) instead of "
                         "the measured illumination field (R^2 0.832)")
    ap.add_argument("--night-ambient", default=None, metavar="LO,HI",
                    help="override the declared night ambient range. The pre-registered "
                         "axis is 0.02-0.50, which does NOT contain CARLA's measured 0.553 "
                         "(F16), so verdicts over it say nothing about the condition closed "
                         "loop actually drives.")
    ap.add_argument("--fog-k", default=None,
                    help="override the measured k interval, e.g. '0.6,1.25'")
    ap.add_argument("--airlight", type=float, default=None,
                    help="override the MEASURED airlight; default reads calibration")
    args = ap.parse_args()
    LEDGER.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    student = StudentNet(args.h, args.w,
                         channels=tuple(int(v) for v in args.channels.split(",")),
                         fc=args.fc).to(device)
    student.load_state_dict(torch.load(
        f"{C.CHECKPOINT_DIR}/{args.student}.pth", map_location=device))
    student.eval()
    tol = C.CLOSED_LOOP_TOLERANCE
    nrelu = student.num_relu_neurons()

    print(f"{args.condition} / {args.cell_name}  ({args.student}, {nrelu} ReLU)")
    print(f"corridor +/-{tol:.4f} around clear-weather steering, "
          f"{args.frames} frames x {args.budget} bounds\n")

    # ── the degenerate cell ──────────────────────────────────────────────────
    if args.condition == "clear":
        record = {"condition": "clear", "student": args.cell_name,
                  "instrument": "verify", "verdict": "CERTIFIED", "vacuous": True,
                  "checkpoint": args.student,
                  "relu_neurons": nrelu, "tolerance": tol,
                  "note": ("Degenerate by construction: the clear disturbance box has zero "
                           "width, so the bound is exact and equals the clear-weather "
                           "steering it is compared against. Recorded for completeness; "
                           "not evidence, and excluded from certified-rate summaries.")}
        path = LEDGER / f"clear__{args.cell_name}__verify.json"
        json.dump(record, open(path, "w"), indent=2)
        print(f"VACUOUS CERTIFIED (zero-width box)\nwrote {path}")
        return 0

    # Shadows uses a PER-FRAME mask measured from that frame's own pose-matched shadows
    # counterpart. The pooled mask from measure_shadow_mask.py is retained as a diagnostic
    # but is not used here: averaged across poses it blurs moving cast shadows into a
    # smooth global dimming.
    if args.condition == "shadows":
        pairs = paired_frames(args.frames, "shadows")
        if len(pairs) < args.frames:
            print(f"ERROR: only {len(pairs)} pose-matched shadow pairs, need {args.frames}")
            return 2
        frames_in = [p[0] for p in pairs]
        masks = []
        for cimg, simg, _ in pairs:
            cf = cimg.astype(np.float32) / 255.0
            sf = simg.astype(np.float32) / 255.0
            # raw fractional dimming; s = 1 reproduces the observed shadows frame
            masks.append(np.clip(1.0 - np.divide(sf, cf, out=np.ones_like(sf),
                                                 where=cf > 0.04), 0.0, 1.0))
        print(f"  [shadow masks] {len(pairs)} pose-matched pairs, "
              f"median pose err {np.median([p[2] for p in pairs]):.3f} m, "
              f"mean dimming {np.mean([m.mean() for m in masks]):.3f}, "
              f"mean spatial std {np.mean([m.std() for m in masks]):.3f}")
    else:
        frames_in = clear_frames(args.frames)
        masks = [None] * len(frames_in)

    fog_A, fog_k = (0.78, 0.78, 0.78), (1.0, 1.0)
    if args.condition == "fog":
        srcs = [q for q in (FOG_CAL, FOG_CAL_FALLBACK) if q.exists()]
        if FOG_CAL not in srcs and FOG_CAL_OLD.exists():
            srcs.append(FOG_CAL_OLD)
        if not srcs:
            print("ERROR: no fog calibration. Run scripts/fit_operating_point.py and/or "
                  "scripts/fog_density_sweep.py first -- an ASSUMED airlight is exactly "
                  "what D4 exists to eliminate.")
            return 2
        ks, As = [], []
        for q in srcs:
            cal = json.load(open(q))
            if "densities" in cal:
                row = min(cal["densities"], key=lambda r: abs(r["fog_density"] - 70.0))
                As.append(row["airlight"]); ks.append(float(np.mean(row["k"])))
            else:
                As.append(cal["airlight_median"])
                if "k_median" in cal:
                    ks.append(float(np.mean(cal["k_median"])))
        fog_A = tuple(float(np.mean([a[c] for a in As])) for c in range(3))
        if args.airlight is not None:
            fog_A = (args.airlight,) * 3
        # k is BOUNDED across every fit we have, with a margin, because the fits disagree.
        if args.fog_k is not None:
            lo, hi = (float(v) for v in args.fog_k.split(","))
        elif ks:
            lo, hi = min(ks) * 0.9, max(ks) * 1.1
        else:
            lo, hi = 0.60, 1.25
        fog_k = (lo, hi)
        print(f"  [fog calibration] A = [{fog_A[0]:.3f} {fog_A[1]:.3f} {fog_A[2]:.3f}], "
              f"k in [{lo:.3f}, {hi:.3f}] from {len(srcs)} fit(s), model = {args.fog_model}")

    rows = []
    print(f"  {'frame':>5s} {'clear':>8s} {'cert':>8s} {'fals':>8s} {'unk':>8s} {'bnds':>6s}")
    print("  " + "-" * 50)
    for i, img in enumerate(frames_in):
        mask = masks[i]
        xf = img.astype(np.float32) / 255.0
        if args.condition == "fog":
            if args.fog_model == "illum":
                build, lo, hi = fog_map_illum(xf, args.w, args.h, fog_A, fog_k)
            else:
                build, lo, hi = fog_map(xf, args.w, args.h, fog_A)
        elif args.condition == "night":
            if args.night_ambient:
                # `import scripts.certify_cell as _self` here was a SILENT NO-OP. Run as a
                # script this module is __main__; that import loads a SECOND copy of the
                # file and the override landed on the copy, while night_map_sensor read
                # __main__.NIGHT_AMBIENT and never saw it. The flag appeared to work and
                # changed nothing. Rebind on the module actually executing instead.
                _self = sys.modules[__name__]
                a_lo, a_hi = (float(v) for v in args.night_ambient.split(","))
                _self.NIGHT_AMBIENT = (a_lo, a_hi)
                assert NIGHT_AMBIENT == (a_lo, a_hi), "override did not take effect"
            # Night is the ONLY condition that leaves [0,1] (negative retro amplitude), so
            # it is the only one where clamp placement changes the answer -- and it changes
            # it by more than the corridor. Use the sensor-resolution path.
            if NIGHT_GAIN.exists() and not args.night_analytic:
                build, lo, hi = night_map_gain(xf, args.w, args.h, np.load(NIGHT_GAIN))
            else:
                R_, C_ = vd.load_projection()
                build, lo, hi = night_map_sensor(xf, R_, C_)
        else:
            build, lo, hi = shadow_map(xf, args.w, args.h, mask)

        cs = clear_steer(student, xf, device, args.w, args.h)
        corridor = (cs - tol, cs + tol)
        # The BaB box is in PHYSICAL units (MOR alone, so 1-D for fog) while the
        # linearized map may have more columns (fog is rank-2 in (u1, u2) once k is
        # bounded). Size the bounded module from the map, not from the box.
        _W_probe = build(lo, hi)[0]
        if getattr(build, "sensor", None) is not None:
            R_, C_, shp = build.sensor
            bounder = SensorBounder(_W_probe.shape[1], student, device, R_, C_, shp)
        else:
            bounder = Bounder(_W_probe.shape[1], student, device, args.h, args.w)

        # The cached-module shortcut is checked against a fresh construction ONCE per
        # cell, on the full box. A silent mismatch here would make every bound in the
        # sweep wrong in a way no downstream number would reveal.
        if i == 0 and getattr(build, "sensor", None) is None:
            W0, b0, u_lo0, u_hi0 = build(lo, hi)
            ok, err, cached, fresh, rtol, moved = bounder.check_equivalence(
                W0, b0, u_lo0, u_hi0, student, args.h, args.w)
            print(f"  [cache check] cached {cached[0]:+.6f},{cached[1]:+.6f}  "
                  f"fresh {fresh[0]:+.6f},{fresh[1]:+.6f}\n"
                  f"                err {err:.2e} vs rel_tol {rtol:.2e}; "
                  f"staleness probe moved bound {moved:.2e}  "
                  f"{'OK' if ok else 'MISMATCH'}")
            if not ok:
                print("  ABORT: cached BoundedModule disagrees with a fresh one; "
                      "the sweep would be unsound.")
                return 3

        frac, n, cells = sweep(build, lo, hi, bounder, corridor, args.budget)
        print(f"  {i:5d} {cs:+8.4f} {frac['CERTIFIED']:7.1%} {frac['FALSIFIED']:7.1%} "
              f"{frac['UNKNOWN']:7.1%} {n:6d}")
        rows.append({"frame": i, "clear_steer": cs, "bounds": n,
                     "certified": frac["CERTIFIED"], "falsified": frac["FALSIFIED"],
                     "unknown": frac["UNKNOWN"],
                     "falsified_regions": [[c[2], c[3]] for c in cells
                                           if c[0] == "FALSIFIED"]})

    cert = [r["certified"] for r in rows]
    fals = [r["falsified"] for r in rows]
    verdict = design.verify_verdict(cert, fals)

    print("\n" + "=" * 52)
    print(f"  median certified {np.median(cert):.1%}   "
          f"median falsified {np.median(fals):.1%}   "
          f"median unknown {np.median([r['unknown'] for r in rows]):.1%}")
    print(f"  frames with any falsified region: "
          f"{sum(1 for f in fals if f > 0)}/{len(fals)}")
    print(f"  VERDICT  {verdict}   (pre-registered expectation "
          f"{design.expected(args.cell_name, args.condition, 'verify')})")
    print("=" * 52)

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()
    record = {"condition": args.condition, "student": args.cell_name,
              "instrument": "verify", "verdict": verdict,
              "checkpoint": args.student, "relu_neurons": nrelu,
              "tolerance": tol, "frames": len(rows),
              "cell_budget": args.budget,
              "axis": {"fog": FOG_MOR, "night": [NIGHT_AMBIENT, NIGHT_RETRO],
                       "shadows": SHADOW_DEPTH}[args.condition],
              "airlight": list(fog_A) if args.condition == "fog" else None,
              "fog_model": args.fog_model if args.condition == "fog" else None,
              "fog_k_interval": list(fog_k) if args.condition == "fog" else None,
              "median_certified": float(np.median(cert)),
              "median_falsified": float(np.median(fals)),
              "median_unknown": float(np.median([r["unknown"] for r in rows])),
              "rule_commit": head, "per_frame": rows}
    path = LEDGER / f"{args.condition}__{args.cell_name}__verify.json"
    json.dump(record, open(path, "w"), indent=2)
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
