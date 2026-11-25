#!/usr/bin/env python3
"""Every full-frame cutaway (clip, site) really covers the frame in the render.

A cutaway that went wrong (a squashed strip in a lower-line box, a clip that never loaded, a panel that stayed
transparent) leaves most of the frame as it was underneath. This compares the render with the base it was dressed
over at three moments inside each full-frame beat: the share of pixels that still match the base must stay small.

  cutaway-check.py --storyboard storyboard.json --video out/composite-4k.mp4 --base tella-4k.mp4 [--max-match 0.25]

--base is the video under the overlays (the Tella export, or public/input-video.mp4). Exit 1 on any FAIL.
"""
import argparse, json, subprocess, sys
import numpy as np

FULL = ("clip", "site")   # a concept panel sits inset over the video, so it is not checked here
W, H = 320, 180

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--storyboard", required=True)
ap.add_argument("--video", required=True, help="the render: composite or master")
ap.add_argument("--base", required=True, help="the video under the overlays")
ap.add_argument("--max-match", type=float, default=0.25, help="largest share of pixels allowed to match the base")
ap.add_argument("--types", default=",".join(FULL), help="beat types that must cover the frame")
a = ap.parse_args()


def frame(path, t):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.3f" % t, "-i", path, "-frames:v", "1", "-vf",
                        "scale=%d:%d,format=gray" % (W, H), "-f", "rawvideo", "-"], capture_output=True)
    if len(r.stdout) < W * H:
        return None
    return np.frombuffer(r.stdout[:W * H], np.uint8).astype(np.int16)


sb = json.load(open(a.storyboard))
types = set(a.types.split(","))
beats = [b for b in sb.get("beats", []) if b.get("type") in types or b.get("full")]
fails = 0
for b in beats:
    t0, t1 = float(b["in"]), float(b["out"])
    pad = min(0.4, (t1 - t0) / 4)
    worst = 0.0
    for t in (t0 + pad, (t0 + t1) / 2, t1 - pad):
        v, s = frame(a.video, t), frame(a.base, t)
        if v is None or s is None:
            print("FAIL %-8s %-16s %7.2f  no frame at %.2f" % (b["type"], b["id"], t0, t)); fails += 1; break
        worst = max(worst, float(np.mean(np.abs(v - s) <= 3)))
    else:
        bad = worst > a.max_match
        fails += bad
        print("%s %-8s %-16s %7.2f-%7.2f  %3.0f%% of the frame still the base" %
              ("FAIL" if bad else "ok  ", b["type"], b["id"], t0, t1, 100 * worst))
print("%d full-frame beats, %d FAIL" % (len(beats), fails))
sys.exit(1 if fails else 0)
