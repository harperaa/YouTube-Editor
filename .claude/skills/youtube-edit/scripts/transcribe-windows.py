#!/usr/bin/env python3
"""transcribe-windows.py: Parakeet on a long file, in ~25 s windows, merged into one transcript.json.

Parakeet drops whole sentences on files over ~3 minutes, so long audio is transcribed in windows and the word times are
shifted back. Windows are cut at auto-editor silences (--speech, the midpoint of a silent chunk 15-35 s after the last
cut). When there is no silence there (a Tella export carries room tone or music; one had a single silence in 17
minutes), the cut goes on the quietest 20 ms frame within +-5 s of the target: a fixed 25 s cut lands mid-word and the
word comes out twice ("leads every day. Day.") or not at all.

Usage: python3 transcribe-windows.py --audio W/audio.wav --out W/transcript.json [--speech W/speech.v1] [--target 25]
       [--plan-only]   (print the window cuts and stop; no transcription)
Needs numpy, ffmpeg and `npx hyperframes transcribe --engine parakeet`.
"""
import argparse, json, os, subprocess, sys, tempfile, wave

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--audio", help="16 kHz mono WAV")
ap.add_argument("--out")
ap.add_argument("--speech", help="auto-editor v1 JSON of the same audio")
ap.add_argument("--target", type=float, default=25.0)
ap.add_argument("--plan-only", action="store_true")
ap.add_argument("--overlap", type=float, default=1.5, help="seconds each window reaches into its neighbours")
ap.add_argument("--dedupe", metavar="FILE", help="only remove boundary duplicates from an existing transcript (in place)")
a = ap.parse_args()


def dedupe(words):
    """A cut inside a word lets both windows hear it, and their start times can land either side of the cut, so it is
    kept twice ("And And", "GitHub GitHub", "So So" on one 19-minute file, each read as a stutter to cut). A spoken
    double never overlaps itself in time; a boundary duplicate does. Drop the second of two equal words that overlap."""
    import re
    n = lambda t: re.sub(r"[^a-z0-9]", "", t.lower())
    out, dropped = [], 0
    for w in words:
        if out and n(w["text"]) == n(out[-1]["text"]) and w["start"] < out[-1]["end"] - 0.02:
            dropped += 1; continue
        out.append(w)
    return out, dropped


if a.dedupe:
    d = json.load(open(a.dedupe)); lst = d["words"] if isinstance(d, dict) and "words" in d else d
    out, dropped = dedupe(lst)
    for i, w in enumerate(out): w["id"] = "w%d" % i
    json.dump(out, open(a.dedupe, "w"), indent=0)
    print("%d boundary duplicate(s) removed -> %s" % (dropped, a.dedupe)); sys.exit(0)

if not (a.audio and a.out):
    ap.error("--audio and --out are required (or --dedupe FILE)")

f = wave.open(a.audio); sr = f.getframerate(); n = f.getnframes()
x = np.frombuffer(f.readframes(n), dtype=np.int16).astype(np.float32)
if f.getnchannels() > 1:
    x = x.reshape(-1, f.getnchannels()).mean(axis=1)
dur = len(x) / sr
hop = int(0.02 * sr)
rms = np.sqrt(np.add.reduceat(x[: len(x) // hop * hop] ** 2, np.arange(0, len(x) // hop * hop, hop)) / hop)

sil = []
if a.speech:
    d = json.load(open(a.speech)); num, den = [int(v) for v in str(d.get("timebase", "30/1")).split("/")]
    sil = [((s + e) / 2) * den / num for s, e, sp in d["chunks"] if sp != 1.0]


def quietest(t, w=5.0):
    i0, i1 = max(0, int((t - w) / 0.02)), min(len(rms), int((t + w) / 0.02))
    return (i0 + int(np.argmin(rms[i0:i1]))) * 0.02 + 0.01


cuts = [0.0]
while cuts[-1] + a.target < dur - 8:
    cand = [s for s in sil if cuts[-1] + 15 <= s <= cuts[-1] + 35]
    cuts.append(min(cand, key=lambda s: abs(s - (cuts[-1] + a.target))) if cand else quietest(cuts[-1] + a.target))
cuts.append(dur)
if a.plan_only:
    print(json.dumps([round(c, 3) for c in cuts]))
    sys.exit(0)

words, tmp = [], tempfile.mkdtemp(prefix="tw-")
for i, (c0, c1) in enumerate(zip(cuts, cuts[1:])):
    # each window overlaps its neighbours by --overlap and keeps only the words that START inside [c0, c1): a word
    # that straddles a cut is heard whole in one window and never twice ("let's take Take", "mentee" -> "Mantis")
    t0, t1 = max(0.0, c0 - a.overlap), min(dur, c1 + a.overlap)
    wd = os.path.join(tmp, "w%03d" % i); os.makedirs(wd)
    wav = os.path.join(wd, "a.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % t0, "-t", "%.3f" % (t1 - t0), "-i", a.audio, "-c", "copy", wav], check=True)
    r = subprocess.run(["npx", "hyperframes", "transcribe", wav, "-d", wd, "--engine", "parakeet", "--json"], capture_output=True, text=True)
    p = os.path.join(wd, "transcript.json")
    if r.returncode != 0 or not os.path.exists(p):
        sys.exit("window %d (%.1f-%.1f) failed: %s" % (i, t0, t1, (r.stderr or r.stdout)[-400:]))
    t = json.load(open(p)); lst = t["words"] if isinstance(t, dict) else t
    kept = [w for w in lst if c0 <= w["start"] + t0 < c1 or (i == len(cuts) - 2 and w["start"] + t0 >= c0)]
    for w in kept:
        words.append({"text": w["text"], "start": round(w["start"] + t0, 3), "end": round(w["end"] + t0, 3)})
    print("window %d %.1f-%.1f: %d words" % (i, c0, c1, len(kept)), flush=True)
words, dropped = dedupe(words)
if dropped: print("%d boundary duplicate(s) removed" % dropped)
for i, w in enumerate(words):
    w["id"] = "w%d" % i
json.dump(words, open(a.out, "w"), indent=0)
print("%d words in %d windows -> %s" % (len(words), len(cuts) - 1, a.out))
