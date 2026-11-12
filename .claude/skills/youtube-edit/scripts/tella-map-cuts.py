#!/usr/bin/env python3
"""tella-map-cuts.py: a cut list made on a Tella EXPORT -> the full `cuts` array for update_clip, per clip.

When the file you were handed is an export of a Tella video's timeline (its duration matches get_timeline's durationMs;
search_videos by title finds the video), the cut is made locally on that file as usual and then sent back to Tella:
export time = timeline time, so each kept stretch is split per clip (timelineStartMs, durationMs), mapped from the
clip's playback time to its raw-recording time through the clip's EXISTING cuts, and the complement becomes the new
cut set (update_clip replaces the whole set). Kept slivers under --sliver ms between two cuts are cut too (they played
as a flash frame where a new edge met an old cut). Different from tella-cuts.py, which maps a cut list made on a raw
SOURCE download (with Tella's ~2.4 s lead-in).

Usage: python3 tella-map-cuts.py --cut-list W/cut-list.json --timeline W/tella/timeline.json --out W/tella/new-cuts.json
  timeline.json: the get_timeline response saved as is (include: ["cuts"]), or {"clips":[{"id","start","dur","cuts":[[s,d],..]}]}
  Prints one line per clip; new-cuts.json = {clipId: [{"startTimeMs","durationMs"}, ...]}. Keep the old timeline.json:
  it is the undo.
"""
import argparse, json

ap = argparse.ArgumentParser()
ap.add_argument("--cut-list", required=True); ap.add_argument("--timeline", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--sliver", type=float, default=80, help="ms; kept pieces shorter than this between cuts are cut")
ap.add_argument("--min-cut", type=float, default=40, help="ms; cuts shorter than this are dropped (a 20 ms cut is a pointless micro-jump)")
a = ap.parse_args()

t = json.load(open(a.timeline))
if "clips" in t and t["clips"] and "timelineStartMs" in t["clips"][0]:
    det = {c["clipId"]: c for c in t.get("details", {}).get("clips", [])}
    clips = [{"id": c["id"], "start": c["timelineStartMs"], "dur": c["durationMs"],
              "cuts": [[x["startTimeMs"], x["durationMs"]] for x in det.get(c["id"], {}).get("cuts", [])]}
             for c in sorted(t["clips"], key=lambda c: c["timelineStartMs"])]
else:
    clips = t["clips"]
K = [(float(k["start"]) * 1000, float(k["end"]) * 1000) for k in json.load(open(a.cut_list))["kept"]]

out = {}
for c in clips:
    cuts = sorted((s, d) for s, d in c["cuts"] if d > 0)
    rawmax = c["dur"] + sum(d for _, d in cuts)

    def pieces(p0, p1):
        res, p, r = [], 0.0, 0.0
        for s, d in cuts + [(rawmax, 0)]:
            n = s - r; lo, hi = max(p0, p), min(p1, p + n)
            if hi > lo: res.append((r + (lo - p), r + (hi - p)))
            p += n; r = s + d
        return res

    kept = []
    for s, e in K:
        lo, hi = max(s, c["start"]) - c["start"], min(e, c["start"] + c["dur"]) - c["start"]
        if hi - lo > 1: kept += pieces(lo, hi)
    kept.sort()
    new, r = [], 0.0
    for s, e in kept:
        if s - r >= 1: new.append([round(r), round(s - r)])
        r = e
    if rawmax - r >= 1: new.append([round(r), round(rawmax - r)])
    merged = []
    for s, d in new:
        if merged and s - (merged[-1][0] + merged[-1][1]) < a.sliver:
            merged[-1][1] = s + d - merged[-1][0]
        else:
            merged.append([s, d])
    merged = [[s, d] for s, d in merged if d >= a.min_cut or s == 0 or s + d >= rawmax - 1]
    out[c["id"]] = [{"startTimeMs": s, "durationMs": d} for s, d in merged]
    print("%s: %d cuts, plays %.2f s (was %.2f s)" % (c["id"], len(merged), (rawmax - sum(d for _, d in merged)) / 1000, c["dur"] / 1000))
json.dump(out, open(a.out, "w"))
print("wrote", a.out, "- send each clip's array with update_clip(cuts=...), then read get_transcript at every changed join")
