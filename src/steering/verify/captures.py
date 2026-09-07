"""Reading a capture bundle, and deciding which of its poses a scope scores.

Split out of certify_town06.py because three tools need it: the certifier, the
witness search, and the varying-intensity probe. It was imported across script
files before, which only worked when the caller had already patched sys.path.
"""
import os
from pathlib import Path

import numpy as np

from steering import REPO_ROOT as _REPO_ROOT

REPO = Path(_REPO_ROOT)

# The capture set. An 84x28 student's frames are a DIFFERENT PROJECTION and live in
# their own directory -- certifying it against the committed 168x56 captures would
# silently bound a different network on the wrong frames.
#
# Overridable, and the override is chained to the certificate's output path: a
# non-canonical capture set may not write the canonical certificate, because that
# file's whole meaning is "the shipped students, on the committed frames".
CAPTURES = Path(os.environ.get("TOWN06_CAPTURES_DIR",
                               REPO / "results" / "arterial" / "captures"))
CANONICAL_CAPTURES = REPO / "results" / "arterial" / "captures"


def scope_mask(path, scope):
    """Which captured poses lie on road the `scope` scores.

    `full` keeps every captured pose, which is what the committed certificate used: the
    capture rig already skips the ODD bridges, so its poses ARE the full scored road.
    `capped` additionally drops poses on road over SMAX_CAP -- the constant
    build_town06_sections.py enforced and build_town06_lap_from_track.py does not.

    The pose's position on the route is recomputed by projecting it onto the route's own
    vertices, never read from an index the capture stored, so this stays a measurement of
    where the frames actually are (standing rule 7).
    """
    from steering.verify import scored_scope as ss
    from steering.drive.route import load_route

    z = np.load(path, allow_pickle=True)
    if "pose_x" not in z.files:
        raise RuntimeError(f"{path.name}: no pose track; cannot scope it")
    px = np.asarray(z["pose_x"], float)
    py = np.asarray(z["pose_y"], float)
    if scope == "full":
        return np.ones(len(px), dtype=bool)
    rt = np.asarray(load_route("lap"), float)[:, :2]
    seg = np.linalg.norm(np.diff(rt, axis=0), axis=1)
    arc = np.concatenate([[0.0], np.cumsum(seg)])
    # nearest route vertex per pose -> its arc length
    d2 = ((px[:, None] - rt[None, :, 0]) ** 2 + (py[:, None] - rt[None, :, 1]) ** 2)
    here = arc[np.argmin(d2, axis=1)]
    spans = ss.excluded_spans("lap", ss.SMAX_CAP)
    keep = np.ones(len(px), dtype=bool)
    for a, b in spans:
        keep &= ~((here >= a) & (here <= b))
    return keep


def nominal(path, cond, mask=None):
    z = np.load(path, allow_pickle=True)
    conds = [str(c) for c in z["conds"]]
    if cond not in conds:
        return None
    # frames is (conds, POSES, offsets, yaws, 3, H, W). Indexing fr[oi, yi] took the
    # offset index off the POSE axis and the yaw index off the OFFSET axis, returning a
    # single pose instead of the whole section -- so a certificate meant to pool ~270
    # poses per cell was computed from 6, one per section, and reported "6 poses" as if
    # that were normal. The pose axis is the one being kept, so it must be sliced.
    fr = z["frames"][conds.index(cond)]
    oi = int(np.argmin(np.abs(z["offsets"])))
    yi = int(np.argmin(np.abs(z["yaws"])))
    out = fr[:, oi, yi]
    # Check the POSE COUNT, not just the rank: the buggy fr[oi, yi] also returned a
    # 4-D array, (1,3,H,W), so a rank check would have passed it.
    if out.ndim != 4 or out.shape[0] != fr.shape[0]:
        raise RuntimeError(f"{path.name}: expected ({fr.shape[0]},3,H,W), got {out.shape}")
    # The scope filter is applied AFTER the shape check, so a mask can never disguise an
    # indexing fault as a short capture.
    if mask is not None:
        if len(mask) != out.shape[0]:
            raise RuntimeError(f"{path.name}: mask covers {len(mask)} poses, "
                               f"capture has {out.shape[0]}")
        out = out[mask]
    return out


def baseline_for(cond_path, fallback, mask=None):
    """Paired clear baseline if the condition capture recorded its own, else foreign.

    A clear baseline from a different session shifts the bound materially. Which
    one was used is printed and recorded, never chosen silently.
    """
    own = nominal(cond_path, "clear", mask)
    return (own, "paired") if own is not None else (fallback, "foreign")
