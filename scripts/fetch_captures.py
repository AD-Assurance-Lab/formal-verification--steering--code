#!/usr/bin/env python3
"""Fetch the captured frames the certifier reads, and prove they are the right ones.

The certificates in this repository are computed from captured images, not from a live
simulator, so anyone can reproduce them on a laptop -- but the captures are 641 MB and
do not belong in git. They are published as a dataset instead, and this script puts them
where the certifier looks:

    results/town06/captures/          four full-lap captures, one per condition
    results/town04_v2/calibration/    eight, two directions by four conditions

    python3 scripts/fetch_captures.py           # download what is missing
    python3 scripts/fetch_captures.py --check   # verify what is already here
    python3 scripts/fetch_captures.py --force   # download again regardless
    python3 scripts/fetch_captures.py --stage DIR   # build the upload tree from here

EVERY FILE IS CHECKED AGAINST A DIGEST RECORDED HERE, and a mismatch is fatal. This is
not about transport errors. A capture is the certifier's whole input, and a bound
computed from the wrong frames is not a weaker result, it is a statement about a
different experiment -- one that still prints a verdict and a margin and looks finished.
The digests below are of the exact files the paper's numbers came from.

No new dependency: this uses urllib against the dataset's public file URLs. If you would
rather use the Hugging Face client, `hf download` on the same repository is equivalent.
"""
import argparse
import hashlib
import os
import shutil
import sys
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = "AD-Assurance-Lab/steering-verification-captures"
BASE = f"https://huggingface.co/datasets/{DATASET}/resolve/main/captures"

# (path in the dataset, path in this repository, sha256)
FILES = [
    ("town06/capture_gate.json", "results/town06/captures/capture_gate.json",
     "591b909c5a5605ffa76e33fe897b451928c5aead0fc4255af5b8dece870bfe3b"),
    ("town06/lap_lap_clear.npz", "results/town06/captures/lap_lap_clear.npz",
     "cd583d61cb9f8c812d48106ed0c1e8c552476f4fd09d91e8c8f7b3043c174f21"),
    ("town06/lap_lap_fog.npz", "results/town06/captures/lap_lap_fog.npz",
     "f6cbb3fd3aa3168b796460bda62e4f68893185192416e9bfe1d297f4443cab1e"),
    ("town06/lap_lap_low_sun.npz", "results/town06/captures/lap_lap_low_sun.npz",
     "9107aecf74cf6fc96ce6276e5782071b6b83e14970ad8e327c3cf8ab83b76fc4"),
    ("town06/lap_lap_night.npz", "results/town06/captures/lap_lap_night.npz",
     "abe8f269cbd03f4853445f005b008ee20c82096abf3aeaf53738c523e1723c6b"),
    ("town04_v2/capture_gate.json", "results/town04_v2/calibration/capture_gate.json",
     "85f0a7ceae809837615b57dc4c242f895c97247b39e3ad0d9158bdbcef24232c"),
    ("town04_v2/scope.json", "results/town04_v2/calibration/scope.json",
     "22cf8d35d04eaa43b12ae4251bf18e5a1b67b91c23e00a34a3adcf1376f90cd1"),
    ("town04_v2/lap_eastbound_clear.npz",
     "results/town04_v2/calibration/lap_eastbound_clear.npz",
     "9e3a19fd60e03ff58530779134716e23506c55956591b12ff5a5bf0c4a9fcb96"),
    ("town04_v2/lap_eastbound_fog.npz",
     "results/town04_v2/calibration/lap_eastbound_fog.npz",
     "23f56df0565a787f0ccc3b13faf66ca43105659eef9fd120d7825c4c24a7f573"),
    ("town04_v2/lap_eastbound_night.npz",
     "results/town04_v2/calibration/lap_eastbound_night.npz",
     "2a4ada73c230d13be0495f9713c889cefecaeb0b997d49d74c048baa6ea078a8"),
    ("town04_v2/lap_eastbound_shadows.npz",
     "results/town04_v2/calibration/lap_eastbound_shadows.npz",
     "b58d68c51f565c2280a0128e0e5a946b70c528cb18180e3cfb48aa364d777427"),
    ("town04_v2/lap_westbound_clear.npz",
     "results/town04_v2/calibration/lap_westbound_clear.npz",
     "368dc433a70a29e53a51690cbf26bb07e14bb770514fd585d306114db216f098"),
    ("town04_v2/lap_westbound_fog.npz",
     "results/town04_v2/calibration/lap_westbound_fog.npz",
     "c07b5caa4e21f9efb48fa4ef8c695be01c4120fee4f7b326b00dcec30d94d78e"),
    ("town04_v2/lap_westbound_night.npz",
     "results/town04_v2/calibration/lap_westbound_night.npz",
     "46d02215d96bd2b4846b94ad80c17bfbaf82ab924811a7387bcae611998ee3fa"),
    ("town04_v2/lap_westbound_shadows.npz",
     "results/town04_v2/calibration/lap_westbound_shadows.npz",
     "3f45779f32b0ba92b7d8d0b9cc6da59b7dc7f584ca8a508ddfa32d290cb9623f"),
]


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    # Download to a temporary name and rename only once the digest matches, so an
    # interrupted fetch can never leave a short file sitting where the certifier
    # will read it and bound a fraction of the road without saying so.
    with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        seen = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            seen += len(chunk)
            if total:
                print(f"\r    {seen / 1e6:7.1f} / {total / 1e6:.1f} MB", end="")
        print("\r" + " " * 40 + "\r", end="")
    return tmp


def stage(out):
    """Build the upload tree from the captures here. The reverse of downloading, and
    it shares this file's table so the two cannot describe different files.

    Refuses on any mismatch. Publishing a capture whose digest is not the one recorded
    here would leave every reader's `fetch_captures.py` rejecting the real dataset.
    """
    missing, wrong, n = [], [], 0
    for name, rel, want in FILES:
        src = os.path.join(REPO, rel)
        if not os.path.exists(src):
            missing.append(rel)
            continue
        if digest(src) != want:
            wrong.append(rel)
            continue
        dest = os.path.join(out, "captures", name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(src, dest)
        n += 1

    if missing or wrong:
        for rel in missing:
            print(f"  missing: {rel}", file=sys.stderr)
        for rel in wrong:
            print(f"  digest does not match the table: {rel}", file=sys.stderr)
        print("\nRefusing to stage. The dataset must hold exactly the files this "
              "script's table describes, or every reader's fetch will reject it.",
              file=sys.stderr)
        return 1

    with open(os.path.join(out, "SHA256SUMS"), "w") as f:
        for name, _, want in FILES:
            f.write(f"{want}  captures/{name}\n")

    # The dataset's front page ships from here too, so what is published describes what
    # is published. A card maintained only on the hub drifts from the files under it.
    shutil.copyfile(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "captures_dataset_card.md"),
                    os.path.join(out, "README.md"))

    print(f"staged {n} files and the dataset card into {out}")
    print("\nUpload with:")
    print("  pip install -U huggingface_hub      # provides the `hf` command")
    print("  hf auth login                       # a token with write access")
    print(f"  hf upload {DATASET} {out} . --repo-type dataset --create")
    print("\nThen check the round trip from a clean clone:")
    print("  python3 scripts/fetch_captures.py --force")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="verify what is already on disk and download nothing")
    ap.add_argument("--force", action="store_true",
                    help="download every file again, even if it is present and correct")
    ap.add_argument("--stage", metavar="DIR",
                    help="build the tree to upload to the dataset, from the captures on "
                         "this machine, checking each against the table below")
    args = ap.parse_args()

    if args.stage:
        return stage(args.stage)

    bad, got, have = [], 0, 0
    for name, rel, want in FILES:
        dest = os.path.join(REPO, rel)
        if os.path.exists(dest) and not args.force:
            if digest(dest) == want:
                have += 1
                continue
            if args.check:
                bad.append(f"{rel}: on disk but the digest does not match")
                continue
            print(f"  {rel}: digest does not match, downloading again")
        if args.check:
            if not os.path.exists(dest):
                bad.append(f"{rel}: missing")
            continue

        print(f"  {rel}")
        try:
            tmp = download(f"{BASE}/{name}", dest)
        except urllib.error.HTTPError as e:
            bad.append(f"{rel}: {e.code} {e.reason} from {BASE}/{name}")
            continue
        except urllib.error.URLError as e:
            print(f"\nCould not reach {BASE}: {e.reason}", file=sys.stderr)
            return 2
        if digest(tmp) != want:
            os.remove(tmp)
            bad.append(f"{rel}: downloaded, but the digest does not match the record")
            continue
        os.replace(tmp, dest)
        got += 1

    if args.check:
        print(f"\n{have} of {len(FILES)} captures present and correct")
    else:
        print(f"\n{got} downloaded, {have} already present, {len(FILES)} needed")

    if bad:
        print("\nPROBLEMS:", file=sys.stderr)
        for b in bad:
            print(f"  {b}", file=sys.stderr)
        print("\nDo not certify against these. Every published verdict was computed "
              "from the exact files recorded here.", file=sys.stderr)
        return 1
    print("\nReady. Reproduce the certificates with:")
    print("  STUDY_MAP=Town06 python3 scripts/certify_town06.py --out /tmp/cert.json")
    print("  STUDY_MAP=Town04 TOWN04_REDO=1 python3 scripts/certify_sustained_bound.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
