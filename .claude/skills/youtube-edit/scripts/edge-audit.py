#!/usr/bin/env python3
"""edge-audit.py: check every edge of a cut list by the AUDIO, not the transcript, and optionally fix it.

Why: Parakeet merges a leaked sliver of a dropped take into the next word, so a transcript
looks clean while the viewer hears "right. [ght] A couple hours ago". Three glitch shapes, all found by level alone:
  - a segment that STARTS while sound is already playing (the tail of a dropped take rides in),
  - a segment that ENDS mid-sound (a chopped word, or the first sliver of the next dropped take),
  - a very short segment that holds no kept word (a restart fragment left behind by a later cut).

Fixes, in the direction that never loses a kept word:
  - a loud head moves to the quietest 10 ms in [first kept word start - 0.28, first kept word start + 0.10]
    (search BACKWARD from the first kept word; searching forward from the old start skipped "if you want the").
    The first kept word starts at or after the previous segment's end and at most 0.05 s before the old start
    (0.35 s with --keeps); without --keeps an earlier word may be the last word of a dropped take,
  - a loud tail moves to the quietest 10 ms in [end - 0.35, end], never before the start + 0.15 of the last word
    the segment holds at least 0.15 s of,
  - a short fragment (< 0.5 s, no kept word) is dropped,
  - no fix moves a start before the previous segment's end, or an end past its own end or the next segment's start.

Usage:
  edge-audit.py --audio W/audio-raw.wav --cut-list W/cut-list.json --transcript W/transcript-raw.json
                [--keeps W/build/keeps.args] [--fix] [--threshold 300]
--keeps is the hand-cut keep list ("--keep A-B ..."); without it every transcript word counts as kept.
Always re-run after --fix: it must print "0 issues". Then apply-cut, then check the joins of the NEW file the same way.
"""
import argparse, json, re, wave
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--audio", required=True); ap.add_argument("--cut-list", required=True); ap.add_argument("--transcript", required=True)
ap.add_argument("--keeps", default=""); ap.add_argument("--fix", action="store_true"); ap.add_argument("--threshold", type=float, default=300)
a = ap.parse_args()

w = wave.open(a.audio); sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
if w.getnchannels() > 1: x = x.reshape(-1, w.getnchannels()).mean(axis=1)
rms = lambda s, e: float(np.sqrt(np.mean(x[max(0, int(s * sr)):max(int(e * sr), int(s * sr) + 1)] ** 2)))
def valley(s, e):
    ts = np.arange(s, max(e, s + 0.02), 0.005); v = [rms(t, t + 0.02) for t in ts]; i = int(np.argmin(v)); return round(float(ts[i] + 0.01), 3), v[i]

T = json.load(open(a.transcript)); T = T["words"] if isinstance(T, dict) else T
keeps = [tuple(map(float, m.split("-"))) for m in re.findall(r"([\d.]+-[\d.]+)", open(a.keeps).read())] if a.keeps else []
kept = lambda t: (not keeps) or any(k0 - 0.02 <= t <= k1 + 0.02 for k0, k1 in keeps)
C = json.load(open(a.cut_list)); K = C["kept"]; issues, out = [], []
for i, s in enumerate(K):
    st, en = s["start"], s["end"]
    prev_end = out[-1]["end"] if out else float("-inf")                         # an edge never crosses a neighbour:
    next_st = K[i + 1]["start"] if i + 1 < len(K) else float("inf")             # that plays the same audio twice
    # without --keeps a word starting before the segment can't be told from a dropped take, so it is never an anchor
    lo = max(prev_end, st - (0.35 if keeps else 0.05))
    words = [q for q in T if lo <= q["start"] < en and kept(q["start"])]
    if en - st < 0.5 and not any(st - 0.05 <= q["start"] < en for q in words):
        issues.append("seg %d %.2f-%.2f: short fragment, no kept word" % (i, st, en))
        if a.fix: continue
    if rms(st, st + 0.03) > a.threshold:
        issues.append("seg %d starts mid-sound at %.2f (rms %d)" % (i, st, rms(st, st + 0.03)))
        if a.fix and words:
            t, v = valley(max(words[0]["start"] - 0.28, prev_end), words[0]["start"] + 0.10); s["start"] = max(t, prev_end)
    if rms(en - 0.03, en) > a.threshold:
        issues.append("seg %d ends mid-sound at %.2f (rms %d)" % (i, en, rms(en - 0.03, en)))
        if a.fix:
            held = [q for q in words if q["start"] + 0.15 <= en]                # a word the segment holds 0.15 s of;
            floor = (held[-1]["start"] + 0.15) if held else s["start"] + 0.2    # a shorter onset is a leaked sliver
            t, v = valley(min(max(en - 0.35, floor), en - 0.02), en); s["end"] = min(t, en, next_st)
    out.append(s)
print("%d segments, %d issues" % (len(K), len(issues))); print("\n".join(issues))
if a.fix:
    C["kept"] = out; C["kept_seconds"] = round(sum(q["end"] - q["start"] for q in out), 3); C["edge_audit"] = "fixed by edge-audit.py"
    json.dump(C, open(a.cut_list, "w"), indent=1); print("wrote %s (%d segments, %.2f s); run again without --fix to confirm" % (a.cut_list, len(out), C["kept_seconds"]))
