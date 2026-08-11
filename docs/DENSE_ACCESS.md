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

## Availability is uncertain -- status 2026-08-11

Zach submitted the form and got the on-screen German confirmation ("you will receive a
confirmation email about receipt of the data"), so the submission registered. **No email
arrived.**

What is actually broken, checked rather than assumed:

| | |
|---|---|
| README link in `gruberto/PixelAccurateDepthBenchmark` (`uni-ulm.de/en/in/driveu/projects/dense-datasets`) | **404, dead** |
| the registration form page above | live, accepts submissions |
| `gruberto/PixelAccurateDepthBenchmark` issue #1, "Unable to download dataset" | opened May 2020, closed with no visible resolution |

Nothing proves the data is gone. But the DENSE project has formally ended, the maintainers
are split between Ulm and Daimler, the repo's own download link has rotted, and the one
public access issue went unanswered. **Treat delivery as uncertain rather than delayed.**

Next steps: check spam (a German-language mail from `uni-ulm.de` is a likely filter
casualty), then email `werner.r.ritter@daimler.com`, `tobias.gruber@daimler.com`,
`mario.bijelic@daimler.com` directly, naming the Pixel Accurate Depth Benchmark and its
fog-chamber subset specifically and mentioning the dead README link. Give it about a week.

### Fallback: REHEARSE (Cerema PAVIN chamber) -- downloadable NOW, verify first

**Verified 2026-08-11.** No registration, direct S3, **CC BY 4.0** -- so unlike DENSE it
permits commercial use, and would also be usable for the funding demo.

Landing page:
<https://s3.ice.ri.se/roadview-WP3-Warwick/T3.2%20-%20Create%20Dataset/rehearse/index.html>

CEREMA = the PAVIN chamber. Confirmed live by HTTP HEAD, sizes from `content-length`:

| file | size |
|---|---|
| `CE_dataset/targets.tar.gz` | **43.0 GB** -- calibrated reflectance targets, the one we want |
| `CE_dataset/car.tar.gz` | 42.7 GB |
| `CE_dataset/ped_bike.tar.gz` | 44 GB |

Base URL:
`https://s3.ice.ri.se/roadview-WP3-Warwick/T3.2%20-%20Create%20Dataset/database/`

**PAVIN's fog range is 10 m to 1000 m MOR** -- wider than PADB's 20-100 m, covering most
of our declared 2000-60 m axis. The chamber also runs "reference tests with calibrated
targets in reflectance", the property that makes `(beta, A)` measurable rather than fitted.

#### Two things must be true, and NEITHER is documented

Established by range-fetching the first 400 MB and listing the tar, not by assuming:

1. **Format is OSI protobuf, not images.** Leaf files are `camera_sv_350_300.osi`,
   `obj_sv_350_300.osi`, `lidar_sd_350_300.osi`. Open Simulation Interface *can* carry
   image data in a SensorView, but `obj_sv` suggests object-level content. **If the camera
   stream is detections rather than pixels, the dataset cannot support photometric work**
   and downloading it does not help.
2. **Fog MOR logging is unconfirmed.** Condition IS encoded in the path --
   `01_night/01_rain/01_14mm/01_lights_on/10m/` gives weather, intensity, lights, target
   distance -- so fog folders very likely carry a MOR label. But that is a *setpoint*, not
   necessarily the measured value, and the dataset's own `adverse_weather.html` documents
   only rain validation and still reads **"CEREMA TO PUT DATA"**.

400 MB of streaming never left the first rain condition, so the fog branch cannot be
inspected without pulling many GB.

#### What the archive actually contains -- INSPECTED 2026-08-11, from 25 MB not 43 GB

Extracted the leading complete files from a range request and decoded them:

| file | size | content |
|---|---|---|
| `FLIR/camera_sv_*.osi` | 9.65 MB | **298 embedded JPEGs**, first decodes at **640x512 GRAYSCALE** -- the thermal camera |
| `MEMS_LIDAR/lidar_sd_*.osi` | 32.0 MB | lidar sensor data |
| `CAMERA_TARGET/obj_sv_*.osi` | **88 bytes** | object detections only -- no pixels |
| `LIDAR_TARGET/obj_sv_*.osi` | 88 bytes | object detections only |

So **OSI here carries real pixels**, as JPEG frame sequences -- the format is not an
obstacle and needs no protobuf schema to read (scan for `FFD8FF`, cut at `FFD9`, hand to
cv2).

**But in the leaf sampled, the only imagery is THERMAL.** The camera folder yields 88-byte
detections. The rig spec does say the sensor roster includes "cameras (RGB and Thermal)",
so visible imagery may exist in other branches of the archive -- this was one condition at
one target distance.

**This matters more than the format question: a thermal-only release is useless for this
study.** Our disturbance models are visible-band photometry, and the whole point is
comparing modelled against measured RGB at known MOR.

**Still worth asking <info@accelopment.com> or <https://roadview-project.eu/contact/>:
is raw RGB imagery included, or only camera-derived detections? And is measured MOR
recorded for the CEREMA fog sequences?**

#### Not suitable: Cerema AWP

<https://ceremadlcfmds.wixsite.com/cerema-databases> has only **two fog intensities**. Too
coarse for a MOR sweep; fine as a qualitative plausibility check.

#### Ranking for this study

| | fit | availability |
|---|---|---|
| **PADB** | best -- 17 MOR levels, calibrated targets, survey depth, 12-bit RGB | uncertain; email sent |
| **REHEARSE / PAVIN** | good range 10-1000 m, calibrated targets, CC BY 4.0 | downloadable now; format risk |
| Cerema AWP | 2 fog levels only | available |

**Shared limitation, for the paper either way:** no chamber produces 2 km visibility, so
the light-fog end of a 2000-60 m axis is never externally validated. Inherent, not a
consequence of dataset choice.

## ⚠ The commercial-use restriction is a real constraint on the demo

"Commercial use prohibited" and "own research and teaching" are narrow. The academic paper
is unambiguously fine. **An investor-facing demo built on this data is not obviously
covered**, and this project has an explicit commercial goal.

**RESOLVED 2026-08-11 (Zach): paper only.** DENSE/PADB data stays inside the academic
work; the funding demo is built entirely on CARLA results, which carry no such
restriction. Recorded here so the boundary is not blurred later.

The original options, kept for the record:

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
