#!/usr/bin/env python3
"""join-check.py: hear a stretch of the cut the way the flat cut will play it, as text, with | at every join.

Use it on every word-level cut (a stutter, a doubled word, a restart without a pause): Parakeet merges doubled words in
the raw transcript ("brings Brings" was one "brings"), stutter-scan times come from that transcript, and a cut placed
on them took "that brings" or "pick one" with it. Try candidate edges with --try before writing them to the cut list.

Usage: python3 join-check.py --cut-list W/cut-list.json --audio W/audio-raw.wav --t0 1015 --t1 1022
       python3 join-check.py ... --t0 1015 --t1 1022 --try 1016.08-1017.70,1018.28-1021.34   (replace the kept pieces
                                                                                             inside [t0, t1] with these)
       [--dry]  print the pieces and stop (no transcription)
Times are source (raw) seconds, as in cut-list.json. Pad the window ~3 s each side: Parakeet returns nothing on very
short audio.
"""
import argparse, json, os, subprocess, sys, tempfile

ap = argparse.ArgumentParser()
ap.add_argument("--cut-list", required=True); ap.add_argument("--audio", required=True)
ap.add_argument("--t0", type=float, required=True); ap.add_argument("--t1", type=float, required=True)
ap.add_argument("--try", dest="trial"); ap.add_argument("--dry", action="store_true")
a = ap.parse_args()

K = [(float(k["start"]), float(k["end"])) for k in json.load(open(a.cut_list))["kept"]]
if a.trial:
    inner = [tuple(map(float, p.split("-"))) for p in a.trial.split(",")]
    K = [(s, e) for s, e in K if e <= min(x for x, _ in inner) or s >= max(y for _, y in inner)] + inner
K = sorted((max(s, a.t0), min(e, a.t1)) for s, e in K if e > a.t0 and s < a.t1)
if a.dry or not K:
    print(json.dumps([[round(s, 3), round(e, 3)] for s, e in K]))
    sys.exit(0 if K else 1)

d = tempfile.mkdtemp(prefix="jc-"); parts = []
for i, (s, e) in enumerate(K):
    p = os.path.join(d, "p%03d.wav" % i)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % s, "-t", "%.3f" % (e - s), "-i", a.audio, p], check=True)
    parts.append(p)
open(os.path.join(d, "list.txt"), "w").write("".join("file '%s'\n" % p for p in parts))
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", os.path.join(d, "list.txt"), os.path.join(d, "j.wav")], check=True)
subprocess.run(["npx", "hyperframes", "transcribe", os.path.join(d, "j.wav"), "-d", d, "--engine", "parakeet", "--json"],
               capture_output=True)
tp = os.path.join(d, "transcript.json")
if not os.path.exists(tp):
    sys.exit("no transcript (window too short? pad it to 6 s or more)")
w = json.load(open(tp)); w = w["words"] if isinstance(w, dict) else w
joins, acc = [], 0.0
for s, e in K:
    acc += e - s; joins.append(acc)
out, j = [], 0
for x in w:
    while j < len(joins) - 1 and x["start"] >= joins[j]:
        out.append("|"); j += 1
    out.append(x["text"])
print(" ".join(out))
