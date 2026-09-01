#!/usr/bin/env python3
"""Log the manually-driven vehicle's position, so a human can point at places in the map.

Choosing a route by looking is the right method -- it is how the Town04 lap end was
settled -- but a hand-drawn overlay cannot be turned into waypoints. This closes that gap:
drive manual_control, say "here", and the position is already recorded with a timestamp.

READ-ONLY, and deliberately so. manual_control runs the world asynchronously, so this
never ticks and cannot interfere with it; it only reads transforms. Two clients ticking
one world is the corruption R-SIM-3 forbids, and nothing here ticks.

Also records what the map says at each point -- junction or not, and the lane markings on
each side -- because that is the criterion for whether the policy can drive it or PPC must
bridge it.

    STUDY_MAP=Town06 CARLA_PORT=3000 python3 scripts/log_ego_position.py
"""
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "pipeline"))
import carla                                                  # noqa: E402
import config as C                                            # noqa: E402

OUT = REPO / "results" / "town06_logs" / "ego_track.csv"


def main():
    client = carla.Client("127.0.0.1", int(C.PORT)); client.set_timeout(30.0)
    world = client.get_world()
    m = world.get_map()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fh = open(OUT, "w", buffering=1)
    fh.write("t,x,y,yaw,road_id,lane_id,is_junction,left_mark,right_mark\n")
    print(f"logging to {OUT}\n  drive in the manual_control window; say 'here' any time "
          f"and I will read the latest row.\n  Ctrl-C to stop.", flush=True)
    t0 = time.time()
    last = None
    try:
        while True:
            veh = [a for a in world.get_actors() if a.type_id.startswith("vehicle")]
            if veh:
                v = max(veh, key=lambda a: a.id)
                tf = v.get_transform()
                wp = m.get_waypoint(tf.location, project_to_road=True)
                lm = str(wp.left_lane_marking.type).split(".")[-1]
                rm = str(wp.right_lane_marking.type).split(".")[-1]
                row = (f"{time.time()-t0:.1f},{tf.location.x:.2f},{tf.location.y:.2f},"
                       f"{tf.rotation.yaw:.1f},{wp.road_id},{wp.lane_id},"
                       f"{wp.is_junction},{lm},{rm}")
                fh.write(row + "\n")
                if row.split(",")[4:] != (last or []):
                    print(f"  ({tf.location.x:8.1f},{tf.location.y:7.1f})  road {wp.road_id:4d} "
                          f"lane {wp.lane_id:3d}  junction={str(wp.is_junction):5s} "
                          f"marks {lm}/{rm}", flush=True)
                    last = row.split(",")[4:]
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n  stopped")
    finally:
        fh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
