# Requesting the DENSE fog-chamber data

**This is the external-validity path.** Everything in this study so far is CARLA's image
formation with real parameters. The one honest way to close that gap is a controlled
facility with *measured* visibility, and this is it. Registration is human-gated with
unknown turnaround, so start it early -- it is the only lead-time item in the project.

---

## Request the PIXEL ACCURATE DEPTH BENCHMARK, not Seeing Through Fog

The previous generation's notes recorded "DENSE / Seeing Through Fog: 17 measured fog
visibility levels, 12-bit RGB, lidar depth". **Those properties belong to a different
dataset in the same family.** Verified 2026-08-11:

| | Seeing Through Fog (STF) | **Pixel Accurate Depth Benchmark (PADB)** |
|---|---|---|
| fog chamber samples | 1,500 | 1,600 |
| **fog visibility levels** | ~3 (30 / 40 / 50 m) | **17, 20-100 m in 5 m steps** |
| also captured | — | clear, light rain, heavy rain, day + night |
| RGB | 12-bit stereo | 12-bit stereo (Aptina AR0230, 1920x1024) |
| depth ground truth | lidar | **Leica ScanStation P30 survey scanner**, ~157M pts, accumulated from multiple positions |
| purpose | object detection in adverse weather | depth/photometric evaluation under controlled weather |
| download | one huge split archive, 12,000 road samples we do not need | the benchmark subset |

Requesting STF would mean a very large download dominated by annotated road driving that
this study has no use for, and only three visibility levels.

### Why PADB is the right instrument for *this* study

1. **17 visibility levels on our actual axis.** Fog is parameterized by meteorological
   optical range, and this samples MOR densely rather than at two or three points. Caveat
   to state in the paper: the chamber covers **20-100 m**, while our declared fog range is
   2000 m down to 60 m. Only the severe end is externally validated; the light-fog end is
   not, and a chamber cannot produce 2 km visibility.
2. **It solves the identifiability failure directly.** The vehicle is static while
   **50x50 cm diffusive Zenith Polymer reflectance targets** are moved to known distances.
   Known reflectance at known depth, with known MOR, makes the Koschmieder pair
   `(beta, A)` *measurable* rather than fitted. That is the precise fix for the previous
   generation's unidentifiable airlight, where identifiability and fit quality were
   mutually exclusive across the ROI.
3. **Survey-grade depth, not lidar depth.** Removes the depth uncertainty that every prior
   identifiability failure traced back to.
4. **12-bit RGB.** No 8-bit quantization, and a characterizable camera response -- which
   matters because our own exposure findings say a certificate is only meaningful with a
   declared response.

---

## How to register

**Form:** <https://www.uni-ulm.de/en/in/institute-of-measurement-control-and-microtechnology/research/data-sets/dense-datasets/dense-registration-form/>

Fields (all required): First name, Last name, Email for data download, Organisation type
(Company / University / Research Institution), Name of organisation, Street, Number, ZIP,
City, Country. Then tick **"I have read and understood the Terms of Use."**

Choose **University** as the organisation type and use the WMU address and a `wmich.edu`
address if you have one -- the licence is scoped to research and teaching, and a
university affiliation is the clean basis for it.

**Terms, as published:**
- permanent, **royalty-free**, non-exclusive licence for **own research and teaching**
- **commercial use prohibited**
- no disclosure to third parties
- persons and vehicle licence plates must be unrecognizable in any published image
- the associated papers must be cited

**If the form stalls or the response is slow**, the dataset contacts are
`werner.r.ritter@daimler.com`, `tobias.gruber@daimler.com`, `mario.bijelic@daimler.com`.
A short note naming the Pixel Accurate Depth Benchmark specifically, and the fog-chamber
subset within it, will get a more useful answer than a generic DENSE request.

**Note:** the Princeton portal
(<https://light.princeton.edu/datasets/automated_driving_dataset/>) is the download path
for *Seeing Through Fog* and sits behind an AWS Cognito login. The Ulm form is the route
for the DENSE family including PADB.

---

## ⚠ The commercial-use restriction is a real constraint on the demo

"Commercial use prohibited" and "own research and teaching" are narrow. The academic paper
is unambiguously fine. **An investor-facing demo built on this data is not obviously
covered**, and this project has an explicit commercial goal.

Two clean options, and this should be decided before the data is used, not after:

1. **Keep DENSE strictly inside the academic work** -- external-validity evidence in the
   paper -- and build the funding demo entirely on CARLA results, which carry no such
   restriction. Costs nothing and is the safe default.
2. **Ask.** The contacts above can say whether a spin-out demonstration is acceptable, or
   offer commercial terms. Worth doing early precisely because the answer may take time.

Do not blur the two. A licence problem discovered after a demo has been shown is far worse
than an email sent now.

---

## What to do with it once it arrives

The fog-chamber subset supports one specific, high-value experiment:

> Fit `(beta, A)` from the reflectance targets at measured MOR, then ask whether the
> disturbance model calibrated in CARLA predicts the real chamber imagery at the same MOR.

That is the sentence that turns "certified above 85 m visibility **in simulation**" into a
claim with a real-camera anchor. It does not require re-training anything, and it is
scoped to fog only -- which is the point: one condition validated against reality is worth
more than four validated against a renderer.

Cite: Gruber et al., *Pixel-Accurate Depth Evaluation in Realistic Driving Scenarios*
(arXiv:1906.08953), and Bijelic et al., *Seeing Through Fog Without Seeing Fog* (CVPR
2020, arXiv:1902.08913) for the wider dataset.
