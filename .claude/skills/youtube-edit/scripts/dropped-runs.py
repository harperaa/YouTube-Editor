#!/usr/bin/env python3
"""dropped-runs.py: every run of words a cut list removes, with the words around it, for Checkpoint A.

PAPER-CUT.md shows the kept text, so a drop INSIDE a sentence is easy to miss: on one 20-minute lesson paper-cut.py
read lists ("its own culture, its own vibe, its own way"), the second half of a story, a tool's name ("a tool called
Eden") and whole real sentences as restarts. Read this list before approving the cut: each line is either a real
restart / retake (fine) or content (put it back with hand-cut.py / patch-cut.py --add).

Usage: python3 dropped-runs.py --transcript W/transcript-raw.json --cut-list W/cut-list.json [--min-words 1] [--out W/DROPPED.md]
A run is "inner" when the words on both sides are kept and the drop does not end a sentence: those deserve the hardest look.
"""
import argparse, json

ap = argparse.ArgumentParser()
ap.add_argument("--transcript", required=True); ap.add_argument("--cut-list", required=True)
ap.add_argument("--min-words", type=int, default=1); ap.add_argument("--context", type=int, default=5)
ap.add_argument("--out")
a = ap.parse_args()

raw = json.load(open(a.transcript)); words = raw["words"] if isinstance(raw, dict) and "words" in raw else raw
words = [{"text": w["text"], "start": float(w["start"]), "end": float(w["end"])} for w in words]
kept = [(float(k["start"]), float(k["end"])) for k in json.load(open(a.cut_list))["kept"]]


def is_kept(w):
    # a word counts as kept when most of its first 0.12 s is inside a kept segment (ASR word ends stretch into pauses)
    s, e = w["start"], min(w["end"], w["start"] + 0.12)
    inside = sum(max(0.0, min(e, b) - max(s, a_)) for a_, b in kept)
    return inside >= 0.5 * (e - s)


flags = [is_kept(w) for w in words]
runs, cur = [], []
for i, k in enumerate(flags):
    if not k:
        cur.append(i)
    elif cur:
        runs.append(cur); cur = []
if cur:
    runs.append(cur)

lines = ["# Dropped runs", "", "%d runs; `inner` = kept words on both sides inside one sentence." % len(runs), ""]
for r in runs:
    if len(r) < a.min_words:
        continue
    i0, i1 = r[0], r[-1]
    before = " ".join(w["text"] for w in words[max(0, i0 - a.context):i0])
    after = " ".join(w["text"] for w in words[i1 + 1:i1 + 1 + a.context])
    drop = " ".join(w["text"] for w in words[i0:i1 + 1])
    prev_end = i0 > 0 and words[i0 - 1]["text"].rstrip('"').endswith((".", "?", "!"))
    inner = i0 > 0 and i1 + 1 < len(words) and not prev_end and not words[i1]["text"].rstrip('"').endswith((".", "?", "!"))
    tag = "inner" if inner else "whole"
    if len(r) > 25:
        drop = drop[:160] + " ... (%d words)" % len(r)
    lines.append("%8.2f  %-5s  ...%s [[%s]] %s..." % (words[i0]["start"], tag, before, drop, after))
text = "\n".join(lines) + "\n"
if a.out:
    open(a.out, "w").write(text)
print(text, end="")
