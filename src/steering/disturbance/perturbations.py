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
