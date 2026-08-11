# Making a physical disturbance formally verifiable

This is the technical core of the study. Everything else is infrastructure.

## The problem

A verifier bounds a network's output over a set of inputs. If the input set is "every image
reachable under fog", that set is a subset of a 10^5-dimensional pixel space and any
axis-aligned or L2 over-approximation of it is astronomically loose — measured at ~60x
vacuous on this network and frame.

The disturbance must therefore reach the verifier as a **low-dimensional parameter**, not as
a region of pixel space. The physical parameter `theta` (visibility in metres, illuminance
in lux) is 1- or 2-dimensional. The whole trick is to keep it that way through to the
bound propagation.

## The template

Every verifiable disturbance in this study has this form:

```
x(theta) = clamp01( m(u) (*) x0 + a(u) )        u = phi(theta)
```

- `x0` — the clear image at full sensor resolution
- `m(u)`, `a(u)` — per-pixel gain and offset maps, each **affine in `u`**
- `u = phi(theta)` — a reparameterization chosen to make the physics affine
- `(*)` — elementwise product

Because `m` and `a` are affine in `u`, the whole map is one `nn.Linear`:

```
W = [ x0 (*) M | M ]        b = x0
```

with `M` the stacked per-pixel basis maps. The verifier's input is `u`, of dimension `k`,
not the image. CROWN bounds this layer **exactly** — the disturbance contributes no
relaxation error of its own.

Then `clamp01` composes in soundly as two ReLUs:

```
clamp01(v) = 1 - relu(1 - relu(v))
```

Do not omit it. Without it, bright additive layers look linear when they are not.

## The four-step derivation, per condition

1. **Write the physics as per-pixel gain and offset.** `x' = m (*) x0 + a`.
2. **Find `u` making `(m, a)` affine.** Usually the physics is affine in some intermediate
   quantity (transmission, illuminance ratio) and nonlinear only in the *physical* parameter.
   Reparameterize to the intermediate.
3. **Map the physical interval into `u`-space.** If `phi` is monotone this is an interval;
   if the components couple, it is a low-rank set, which is where branch-and-bound earns
   its place.
4. **Bound the residual.** `eps_lin = max over the interval of |true physics - affine model|`,
   carried as a sound additive envelope `x in [model - eps_lin, model + eps_lin]`.
   `verifiable_disturbance.py` probes for exactly this number.

**Step 4 is where a condition lives or dies.** If `eps_lin` is large, the bounds go vacuous
and the condition cannot be certified regardless of how good the physics is. Probe it early.

## The mistake to not make

Once you have per-pixel bounds it is tempting to hand the verifier a box over all pixels.
**Do not.** A box permits pixel `i` to sit at `beta_lo` while pixel `j` sits at `beta_hi`.
That is physically impossible — every pixel shares one `beta` — and discarding that
correlation is exactly what makes pixel-space verification vacuous. The low dimensionality
of `theta` is the contribution.

## Per condition

### Night / illuminance — `k = 2`, zero residual

```
x' = g * x0 + c * H
```

`H` is the measured headlight irradiance map; `g` and `c` are functions of road illuminance
in lux. Exactly affine in `(g, c)` — no reparameterization needed, no residual, no
branch-and-bound required for the disturbance itself.

**This is the easiest condition to certify and it is why night is first.** `H` was already
validated against CARLA's empirical headlight map at `r = 0.9898` in the previous study.
Transplant it; do not rebuild it.

### Fog / MOR — `k = 1` per branch, residual shrinks with splitting

Koschmieder:

```
I_i = I0_i * t_i + A * (1 - t_i)        t_i = exp(-beta * d_i)
```

Affine in transmission `t`, nonlinear in `beta`, and `t` is per-pixel — driven by one
scalar `beta` through the measured depth map `d`.

On a branch-and-bound subinterval `[beta_1, beta_2]`, write

```
t_i = tbar_i + s * delta_i        s in [-1, 1]
tbar_i  = (t_i(beta_1) + t_i(beta_2)) / 2
delta_i = (t_i(beta_1) - t_i(beta_2)) / 2
```

A **single scalar** `s` now carries the whole transmission field — a rank-1 model of how
transmission varies across the subinterval. `k = 1`. The residual is the curvature of
`exp(-beta*d)` over the subinterval and is bounded analytically; it **shrinks quadratically
as the subinterval narrows**, which is exactly why input-space branch-and-bound is the right
tool here and not an implementation detail.

`A` is a single global scalar and must be *measured*, not assumed — see D4 in `STUDY.md`.
An unidentifiable `A` was what broke this condition last time.

### Shadows / solar elevation — `k = 1`, but only in the fixed-mask form

```
x' = x0 (*) (1 - s * S)
```

`S` is a shadow mask in [0,1] per pixel, `s` the shadow depth. Affine in `s` at a fixed
mask. Fine.

**Letting the mask move with solar elevation is not affine** — shadow edges translate
across pixels, which is a spatially discontinuous change in `theta` and will blow up
`eps_lin`. If elevation-varying shadows are wanted, expect the probe to reject them, and
fall back to fixed geometry with varying depth. Shadows may end up closed-loop-only, and
that is an acceptable outcome to report.

### Rain / rain rate — no known low-rank form

Garg-Nayar streaks are high-frequency, spatially stochastic, and depend on drop-size
distribution and exposure time. There is no per-pixel affine map with a small `k`.
Attempted last, and a negative result here is publishable as a scoping statement about what
this technique covers.

## Probe order at M5

Run `verifiable_disturbance.py` on all four conditions **before committing to any of them**.
It needs captured frames and no GPU, and it returns `(W, b, lo, hi, max_linearity_error)`.
The expected ordering of `max_linearity_error` is night < fog < shadows < rain. If the
measured ordering differs, that is information about which condition to pursue, delivered
in an afternoon rather than after a month of calibration.

Two rules while probing, both learned expensively:

- Use the **float path with no clipping**. Clipping makes bright additive layers look
  nonlinear.
- Choose the probe `delta` large enough to clear uint8 quantisation. `delta = 0.01`
  amplifies a +/-1/255 rounding error by 100x.
- Probe in the **linearized parameterization** `u`, not in `theta`. The physical parameters
  are not the linear ones.

## Where this connects to the rest of the study

The disturbance model built here is the *same object* the mixed student trains on and the
same axis closed-loop tests sample from. That is the design rule in `CLAUDE.md`. In the
previous study the student trained on affine photometric boxes and was verified against
Koschmieder fog, and the resulting mismatch produced a headline "finding" that was probably
an artifact.
