#!/usr/bin/env python3
"""TIER 1: is the SIMULATOR deterministic, with the feedback loop cut?

Tier 0 proved the inference path is bit-exact, so whatever varies is inside CARLA.
The closed-loop probe cannot say WHERE, because it measures physics, rendering and
feedback amplification at once: a one-LSB pixel difference and a physics divergence
produce the same symptom, a trajectory that drifts apart.

So this cuts the loop. The vehicle is driven by a FIXED, PRE-SCRIPTED control sequence
that is a pure function of the step index -- no camera, no CTE, no controller state.
The commands are therefore identical across reps BY CONSTRUCTION, and any difference in
what comes back is the simulator's own.

Three streams are recorded per step, and they separate the three candidates:

  POSE      x, y, yaw, velocity          -> is PHYSICS deterministic?
  RAW SHA   sha of the camera buffer     -> is the RENDERER deterministic?
  PRE SHA   sha of student_preprocess()  -> does render noise SURVIVE downsampling?
  NN STEER  the model's output, COMPUTED BUT NOT APPLIED
                                         -> how much steering entropy actually enters
                                            the control loop, in steering units?

That last one is the number that matters. The closed loop is only as reproducible as
its most sensitive link, and a renderer that differs by 1 LSB in a handful of pixels is
irrelevant if crop-and-resize averages it away before the network sees it. Computing
the steering without applying it measures the injected entropy without letting it
amplify, which is the whole point of an open-loop probe.

Knobs exist because they are the SUSPECTS, and each is swept separately:

  --no-spectator      update_spectator fires an async set_transform every step and its
                      own docstring documents uncontrollable RPC/tick ordering jitter.
                      It is cosmetic, so it is free to remove from measurement runs.
  --postprocess off   enable_postprocess_effects; CARLA leaves it True.
  --motion-blur 0     motion_blur_intensity defaults to 0.45 and spawn_camera never
                      sets it. Motion blur is TEMPORAL -- it reads the previous frame's
                      velocity buffer -- so it is the leading suspect for a renderer
                      that is not a pure function of world state.
  --bloom / --lens-flare  same argument, weaker priors.

Town06 only. Nothing here touches Town04 or the published artifact.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/determinism_tier1_openloop.py \
        --reps 3 --tag baseline
"""
import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))

import numpy as np  # noqa: E402
import torch  # noqa: E402
import carla  # noqa: E402

import config as C  # noqa: E402
import carla_env as env  # noqa: E402
from student import StudentNet, student_preprocess  # noqa: E402

OUT = REPO / "results" / "town06" / "determinism"


def sha(b):
    return hashlib.sha256(b).hexdigest()[:16]


def scripted_control(step, constant=False):
    """The control sequence. A pure function of the step index -- THAT is the point.

    Settle on the brake, accelerate at a constant throttle, then hold a slow sinusoidal
    steer. The sinusoid keeps the car roughly on the carriageway while continuously
    changing yaw, which keeps the scenery moving and the motion-blur velocity buffer
    non-trivial. A straight-line probe would under-exercise exactly the temporal render
    path this is hunting.
    """
    if step < 15:
        return 0.0, 1.0, 0.0
    if constant:
        # ONE command change in the whole run, at step 15. If physics stays bit-exact
        # here but splits under the varying script, the trigger is the change itself.
        return 0.45, 0.0, 0.0
    if step < 30:
        return 0.6, 0.0, 0.0
    return 0.45, 0.0, 0.05 * math.sin((step - 30) / 14.0)


def _wheel_angle(vehicle):
    """Front-left steered-wheel angle. Steering is applied through the wheel model, so
    this shows a drivetrain split that has not yet moved the chassis."""
    try:
        return float(vehicle.get_wheel_steer_angle(carla.VehicleWheelLocation.FL_Wheel))
    except Exception:
        return 0.0


def spawn_camera_tuned(world, vehicle, condition, pp=None):
    """spawn_camera, plus the postprocess attributes the study never pins.

    Deliberately a separate function rather than an edit to carla_env.spawn_camera:
    the published Town04 pipeline must keep rendering exactly what it rendered, and a
    change there would silently alter it. If a suspect is confirmed, THEN it is promoted
    into the pipeline behind a Town06 guard.
    """
    exposure = C.exposure_for(condition)
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(C.CAM_WIDTH))
    bp.set_attribute("image_size_y", str(C.CAM_HEIGHT))
    bp.set_attribute("fov", str(C.CAM_FOV))
    bp.set_attribute("exposure_mode", C.EXPOSURE_MODE)
    bp.set_attribute("shutter_speed", str(exposure["shutter"]))
    bp.set_attribute("iso", str(exposure["iso"]))
    bp.set_attribute("fstop", str(exposure["fstop"]))
    bp.set_attribute("gamma", str(exposure["gamma"]))
    for k, v in (pp or {}).items():
        bp.set_attribute(k, v)
    tf = carla.Transform(carla.Location(x=C.CAM_X, y=C.CAM_Y, z=C.CAM_Z))
    cam = world.spawn_actor(bp, tf, attach_to=vehicle)
    import queue
    q = queue.Queue()
    cam.listen(q.put)
    return cam, q


def one_rep(args, model, device, pp, rep_ix=0):
    dump_steps = set(int(v) for v in args.dump_steps.split(",") if v != "") if args.dump_steps else set()
    dump_dir = OUT / "frames"
    if dump_steps:
        dump_dir.mkdir(parents=True, exist_ok=True)
    client = env.connect()
    world = env.load_study_map(client)
    original = env.enable_sync_mode(world)
    vehicle = camera = None
    rows = []
    try:
        spawn = C.SPAWNS[args.section]
        vehicle = env.spawn_vehicle(world, spawn)
        # --no-camera is a CONTROL, not an optimisation. grab_frame blocks until the
        # sensor delivers, which synchronises the client to the render thread; without a
        # camera the tick returns as soon as physics is done. If physics diverges only
        # when a camera is attached, the render path is perturbing the simulation rather
        # than merely being read by it, and that is a different bug with a different fix.
        if args.no_camera:
            camera = q = None
        else:
            camera, q = spawn_camera_tuned(world, vehicle, args.condition, pp)
        env.set_weather(world, args.condition, vehicle)
        env.verify_condition(world, args.condition)

        # Settle the spawn before the scripted sequence starts, so rep-to-rep
        # differences cannot come from an un-drained queue or a mid-drop chassis.
        # --warmup-ticks extends this to test the STREAMING hypothesis: if the render
        # differences are asynchronous texture/mesh residency rather than a per-frame
        # computation, they should shrink once everything in view has had time to
        # become resident, and a longer warmup is the cheapest way to find out.
        for _ in range(10 + args.warmup_ticks):
            f = world.tick()
            if q is not None:
                try:
                    env.grab_frame(q, f)
                except env.FrameDesync:
                    pass

        for step in range(args.steps):
            if not args.no_spectator:
                env.update_spectator(world, vehicle)
            thr, brk, steer = scripted_control(step, args.constant_control)
            ctrl = carla.VehicleControl(throttle=thr, brake=brk, steer=steer)
            if args.control_mode == "batch_sync":
                # THE FIX UNDER TEST. vehicle.apply_control() is a FIRE-AND-FORGET RPC:
                # it returns as soon as the message is written, and whether the server
                # has registered it before it processes world.tick() is a timing race.
                # While the command is unchanged the race is invisible -- a late arrival
                # re-applies the same value -- which is why divergence only ever starts
                # on a step where the command CHANGES.
                #
                # apply_batch_sync blocks until the server acknowledges, so the command
                # is provably registered before the tick that consumes it.
                client.apply_batch_sync(
                    [carla.command.ApplyVehicleControl(vehicle.id, ctrl)], False)
            else:
                vehicle.apply_control(ctrl)
            frame = world.tick()
            if q is not None:
                image = env.grab_frame(q, frame)
                raw = np.frombuffer(image.raw_data, dtype=np.uint8)
                bgr = env.raw_to_bgr(image)
                pre = student_preprocess(bgr, model.in_w, model.in_h)
                with torch.no_grad():
                    nn_steer = float(model(torch.from_numpy(pre).unsqueeze(0).to(device)).item())
                raw_sha_, pre_sha_, pre_mean_ = sha(raw.tobytes()), sha(pre.tobytes()), float(pre.mean())
                # A sha says frames DIFFER; it cannot say how, and the how is what
                # names the cause. One-LSB noise smeared over the whole image is shader
                # or accumulation nondeterminism; a few thousand pixels wrong by a lot,
                # in a contiguous region, is asset streaming or LOD popping. Dump the
                # buffers for the requested steps and diff them properly.
                if step in dump_steps:
                    np.save(dump_dir / f"{args.tag}_rep{rep_ix}_step{step:04d}.npy",
                            raw.reshape(C.CAM_HEIGHT, C.CAM_WIDTH, 4))
            else:
                raw_sha_ = pre_sha_ = "no-camera"
                pre_mean_, nn_steer = 0.0, 0.0

            tf = vehicle.get_transform()
            v = vehicle.get_velocity()
            av = vehicle.get_angular_velocity()
            # DRIVETRAIN AND CONTROL READBACK. Pose and velocity can agree bit-for-bit
            # while gear, engine speed or the control the server ACTUALLY applied have
            # already diverged -- and that hidden state is what surfaces later as a
            # sudden pose split. get_control() is the readback: if it differs from the
            # command that was sent, the apply_control RPC lost its race with the tick.
            pc = vehicle.get_control()
            rows.append(dict(
                gear=int(pc.gear), wheel_fl_deg=_wheel_angle(vehicle),
                ap_thr=float(pc.throttle), ap_brk=float(pc.brake), ap_steer=float(pc.steer),
                ap_rev=bool(pc.reverse), ap_hand=bool(pc.hand_brake),
                step=step, frame=int(frame),
                x=tf.location.x, y=tf.location.y, z=tf.location.z,
                yaw=tf.rotation.yaw, pitch=tf.rotation.pitch, roll=tf.rotation.roll,
                vx=v.x, vy=v.y, vz=v.z, avz=av.z,
                thr=thr, brk=brk, steer=steer,
                raw_sha=raw_sha_, pre_sha=pre_sha_,
                pre_mean=pre_mean_, nn_steer=nn_steer,
            ))
    finally:
        env.cleanup([camera, vehicle], world, original)
    return rows


def compare(traces, label):
    """First divergence per stream, and the magnitude of what enters the loop."""
    n = min(len(t) for t in traces)
    pose_keys = ("x", "y", "yaw", "vx", "vy", "avz")

    first_pose = first_raw = first_pre = first_nn = first_ctrl = None
    max_pose_d = max_nn_d = 0.0
    n_raw_diff = n_pre_diff = 0

    for k in range(n):
        rs = [t[k] for t in traces]
        pd = max(abs(a[key] - b[key]) for key in pose_keys for a in rs for b in rs)
        max_pose_d = max(max_pose_d, pd)
        if first_pose is None and pd > 0.0:
            first_pose = (k, pd)

        if first_ctrl is None and len({(r["ap_thr"], r["ap_brk"], r["ap_steer"],
                                        r["gear"]) for r in rs}) > 1:
            first_ctrl = (k, sorted({(r["ap_thr"], r["gear"]) for r in rs}))

        if len({r["raw_sha"] for r in rs}) > 1:
            n_raw_diff += 1
            if first_raw is None:
                first_raw = k
        if len({r["pre_sha"] for r in rs}) > 1:
            n_pre_diff += 1
            if first_pre is None:
                first_pre = k

        nd = max(abs(a["nn_steer"] - b["nn_steer"]) for a in rs for b in rs)
        max_nn_d = max(max_nn_d, nd)
        if first_nn is None and nd > 0.0:
            first_nn = (k, nd)

    print(f"\n  === {label} === {len(traces)} reps, {n} compared steps")
    print(f"  PHYSICS  pose/velocity : ", end="")
    print("IDENTICAL every step" if first_pose is None
          else f"diverges at step {first_pose[0]} (delta {first_pose[1]:.3e}), "
               f"max over run {max_pose_d:.4f}")
    print(f"  APPLIED  control/gear  : ", end="")
    print("IDENTICAL every step" if first_ctrl is None
          else f"differs at step {first_ctrl[0]}: {first_ctrl[1]}")
    print(f"  RENDER   raw camera    : ", end="")
    print("IDENTICAL every step" if first_raw is None
          else f"differs from step {first_raw}, in {n_raw_diff}/{n} steps "
               f"({100.0*n_raw_diff/n:.0f}%)")
    print(f"  SURVIVES preprocessed  : ", end="")
    print("IDENTICAL every step" if first_pre is None
          else f"differs from step {first_pre}, in {n_pre_diff}/{n} steps "
               f"({100.0*n_pre_diff/n:.0f}%)")
    print(f"  INJECTED nn_steer      : ", end="")
    print("IDENTICAL every step" if first_nn is None
          else f"diverges at step {first_nn[0]}, max |dsteer| over run {max_nn_d:.3e}")

    # PER-PAIR, because the pooled figure hides the shape of the disagreement. If rep0
    # is the outlier and every later pair agrees, the cause is a cold server warming up,
    # which is fixable by discarding a warmup run. If every pair disagrees equally, it
    # is a per-frame nondeterminism and no amount of warmup helps.
    print("  pairwise -- raw-differing steps / preproc-differing / max |dsteer|:")
    for a in range(len(traces)):
        for b in range(a + 1, len(traces)):
            ta, tb = traces[a], traces[b]
            nr = sum(1 for k in range(n) if ta[k]["raw_sha"] != tb[k]["raw_sha"])
            npre = sum(1 for k in range(n) if ta[k]["pre_sha"] != tb[k]["pre_sha"])
            dn = max(abs(ta[k]["nn_steer"] - tb[k]["nn_steer"]) for k in range(n))
            print(f"    rep{a} vs rep{b}: {nr:4d}/{n}  {npre:4d}/{n}  {dn:.3e}")

    return dict(label=label, n_steps=n, n_reps=len(traces),
                physics_identical=first_pose is None,
                render_identical=first_raw is None,
                preproc_identical=first_pre is None,
                nn_identical=first_nn is None,
                control_identical=first_ctrl is None,
                first_control_divergence=first_ctrl[0] if first_ctrl else None,
                first_pose_divergence=first_pose[0] if first_pose else None,
                max_pose_delta=max_pose_d,
                first_raw_divergence=first_raw, raw_diff_steps=n_raw_diff,
                first_pre_divergence=first_pre, pre_diff_steps=n_pre_diff,
                max_nn_steer_delta=max_nn_d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--section", default="s02")
    ap.add_argument("--condition", default="clear")
    ap.add_argument("--ck", default="S_clear_t06_168x28_w2")
    ap.add_argument("--channels", default="16,32,32")
    ap.add_argument("--fc", type=int, default=64)
    ap.add_argument("--in-w", type=int, default=168)
    ap.add_argument("--in-h", type=int, default=28)
    ap.add_argument("--no-spectator", action="store_true")
    ap.add_argument("--no-camera", action="store_true")
    ap.add_argument("--warmup-ticks", type=int, default=0)
    ap.add_argument("--control-mode", default="async", choices=["async", "batch_sync"],
                    help="async = vehicle.apply_control (the study's current path); "
                         "batch_sync = acknowledged batch command, no RPC/tick race")
    ap.add_argument("--constant-control", action="store_true",
                    help="never change the command after warmup; isolates whether "
                         "divergence is triggered by a control CHANGE (an apply_control "
                         "RPC losing its race with the tick) rather than by physics")
    ap.add_argument("--postprocess", default=None, choices=["on", "off"])
    ap.add_argument("--motion-blur", type=float, default=None)
    ap.add_argument("--bloom", type=float, default=None)
    ap.add_argument("--lens-flare", type=float, default=None)
    ap.add_argument("--dump-steps", default="",
                    help="comma-separated steps whose RAW camera buffer is saved, for "
                         "pixel-level diffing across reps")
    ap.add_argument("--tag", default="baseline")
    ap.add_argument("--compare-only", action="store_true",
                    help="compare already-written rep traces for --tag and exit. Used by "
                         "the fresh-server-per-rep driver, where each rep is its own "
                         "process against its own newly restarted server -- which is the "
                         "configuration a real measurement run actually uses (R-SIM-1), "
                         "and therefore the one whose reproducibility matters.")
    ap.add_argument("--rep-index", type=int, default=None,
                    help="run ONE rep and write its trace; the driver restarts CARLA between")
    args = ap.parse_args()

    if C.MAP_NAME != "Town06":
        raise SystemExit(f"Town06 only; STUDY_MAP is {C.MAP_NAME}. Town04 stays untouched.")

    pp = {}
    if args.postprocess is not None:
        pp["enable_postprocess_effects"] = "True" if args.postprocess == "on" else "False"
    if args.motion_blur is not None:
        pp["motion_blur_intensity"] = str(args.motion_blur)
    if args.bloom is not None:
        pp["bloom_intensity"] = str(args.bloom)
    if args.lens_flare is not None:
        pp["lens_flare_intensity"] = str(args.lens_flare)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = StudentNet(args.in_h, args.in_w,
                       channels=tuple(int(v) for v in args.channels.split(",")),
                       fc=args.fc).to(device)
    model.load_state_dict(torch.load(os.path.join(C.CHECKPOINT_DIR, f"{args.ck}.pth"),
                                     map_location=device))
    model.eval()

    OUT.mkdir(parents=True, exist_ok=True)

    if args.compare_only:
        import glob
        paths = sorted(glob.glob(str(OUT / f"{args.tag}_rep*.json")))
        traces = [json.loads(Path(p_).read_text())["rows"] for p_ in paths]
        if len(traces) < 2:
            raise SystemExit(f"need >=2 rep traces for {args.tag}, found {len(traces)}")
        summary = compare(traces, f"{args.tag} ({len(traces)} reps, fresh server each)")
        (OUT / f"{args.tag}_summary.json").write_text(json.dumps(summary, indent=2))
        return 0

    if args.rep_index is not None:
        rows = one_rep(args, model, device, pp, args.rep_index)
        p = OUT / f"{args.tag}_rep{args.rep_index:02d}.json"
        p.write_text(json.dumps(dict(args=vars(args), pp=pp, rows=rows)))
        mx = max(abs(r["nn_steer"]) for r in rows)
        print(f"  rep {args.rep_index}: {len(rows)} steps, "
              f"max|nn_steer| {mx:.4f}, last x={rows[-1]['x']:.3f} y={rows[-1]['y']:.3f}")
        return 0

    traces = [one_rep(args, model, device, pp, i) for i in range(args.reps)]
    for i, t in enumerate(traces):
        (OUT / f"{args.tag}_rep{i:02d}.json").write_text(
            json.dumps(dict(args=vars(args), pp=pp, rows=t)))
    summary = compare(traces, args.tag)
    (OUT / f"{args.tag}_summary.json").write_text(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    from carla_lock import carla_lock, CarlaBusy
    try:
        with carla_lock(owner=" ".join(sys.argv[:3])):
            sys.exit(main())
    except CarlaBusy as exc:
        raise SystemExit(str(exc))
