#!/usr/bin/env python3
"""word-audit.py: did every kept word make it into the finished audio, whole?

Builds the words the cut KEEPS from the raw transcript (a word counts when 60 ms of its first 0.4 s is
inside a kept segment), maps them to flat time through cut-list.json, and aligns them with a fresh transcript of the finished file
(the flat cut, or a Tella export of it). Every mismatch is listed with the distance to the nearest join:
  AT-JOIN  within --near (0.6 s) of a join: a clipped or leaked word until proven otherwise; listen with join-check.py
  ASR      away from any join: two transcriptions of the same audio disagreeing (numbers, names, fillers)
A clipped final consonant often changes the word the transcriber hears ("leads" -> "lead", "audience" -> "audien"), so
this catches what level-based edge checks pass. It does not replace listening at each AT-JOIN line.

Usage: python3 word-audit.py --raw W/transcript-raw.json --cut-list W/cut-list.json --final W/final/transcript.json
         [--offset 0] [--near 0.6] [--out W/WORDS.md]
  --offset: seconds to add to flat time when the finished file starts later (none for a straight export)

EARLY (the default place to run it, at Checkpoint A, before any encode, Tella update, overlay or render):
  python3 word-audit.py --raw W/transcript-raw.json --cut-list W/cut-list.json --audio W/audio-raw.wav --final W/flat-words.json
  builds the cut's audio straight from the raw WAV (seconds, no video), transcribes it with transcribe-windows.py
  (overlapping windows) into --final, then compares. Fix every AT-JOIN line, re-run, then apply the cut anywhere.
  --flat-only writes W/flat-audio.wav and stops (no transcription).
"""
import argparse, bisect, difflib, json, os, re, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument("--raw", required=True); ap.add_argument("--cut-list", required=True); ap.add_argument("--final", required=True)
ap.add_argument("--offset", type=float, default=0.0); ap.add_argument("--near", type=float, default=0.6); ap.add_argument("--out")
ap.add_argument("--audio", help="raw 16 kHz WAV: build the cut's audio and transcribe it into --final first (the early audit)")
ap.add_argument("--flat-only", action="store_true", help="with --audio: write flat-audio.wav and stop")
a = ap.parse_args()

if a.audio:
    kept = [(float(k["start"]), float(k["end"])) for k in json.load(open(a.cut_list))["kept"]]
    flat_wav = os.path.join(os.path.dirname(os.path.abspath(a.cut_list)), "flat-audio.wav")
    script = os.path.join(os.path.dirname(os.path.abspath(a.final)), ".flat-audio.ffscript")
    # atrim + 10 ms fades + concat, the same joins apply-cut.py makes (its 20 ms video-side fades are inaudible here)
    parts = ["[0:a]atrim=start=%.4f:end=%.4f,asetpts=PTS-STARTPTS,afade=t=in:d=0.01,afade=t=out:st=%.4f:d=0.01[a%d]"
             % (s0, s1, max(0.0, s1 - s0 - 0.01), i) for i, (s0, s1) in enumerate(kept)]
    graph = ";\n".join(parts) + ";\n" + "".join("[a%d]" % i for i in range(len(kept))) + "concat=n=%d:v=0:a=1[out]" % len(kept)
    open(script, "w").write(graph)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", a.audio, "-/filter_complex", script, "-map", "[out]",
                    "-ar", "16000", "-ac", "1", flat_wav], check=True)
    os.remove(script)
    print("flat audio %.1f s -> %s" % (sum(e - s0 for s0, e in kept), flat_wav))
    if a.flat_only:
        sys.exit(0)
    subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "transcribe-windows.py"),
                    "--audio", flat_wav, "--out", a.final], check=True)


def load(p):
    d = json.load(open(p)); return d["words"] if isinstance(d, dict) and "words" in d else d


NUM = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8",
       "nine": "9", "ten": "10"}
norm = lambda s: NUM.get(re.sub(r"[^a-z0-9]", "", s.lower()), re.sub(r"[^a-z0-9]", "", s.lower()))
K = [(float(k["start"]), float(k["end"])) for k in json.load(open(a.cut_list))["kept"]]
offs, acc = [], 0.0
for s, e in K:
    offs.append(acc); acc += e - s
joins = offs[1:]


def flat(t):
    for (s, e), o in zip(K, offs):
        if s - 0.03 <= t < e: return o + max(0.0, t - s)
    return None


exp = []
for w in load(a.raw):
    s, e = float(w["start"]), float(w["end"])
    # kept when at least 60 ms of its first 0.4 s plays: Parakeet marks starts up to 0.4 s early, so a strict test
    # drops words that start just before a cut edge and still play in full
    e2 = min(e, s + 0.4); spans = [(max(s, x), min(e2, y)) for x, y in K if min(e2, y) > max(s, x)]
    if spans and sum(b - a_ for a_, b in spans) >= min(0.06, 0.5 * max(e2 - s, 0.02)):
        f = flat(spans[0][0])
        if f is not None and norm(w["text"]): exp.append((norm(w["text"]), f + a.offset, w["text"]))
fin = [(norm(w["text"]), float(w["start"]), w["text"]) for w in load(a.final) if norm(w["text"])]


def near_join(t):
    t -= a.offset; i = bisect.bisect_left(joins, t); c = [abs(t - joins[j]) for j in (i - 1, i) if 0 <= j < len(joins)]
    return min(c) if c else 99


sm = difflib.SequenceMatcher(a=[x[0] for x in exp], b=[x[0] for x in fin], autojunk=False)
lines, at_join, asr = [], 0, 0
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op == "equal": continue
    said = " ".join(x[2] for x in exp[i1:i2]); heard = " ".join(x[2] for x in fin[j1:j2])
    t = fin[j1][1] if j1 < len(fin) else (exp[i1][1] if i1 < len(exp) else 0)
    if i1 < len(exp): t = min(t, exp[i1][1]) if j1 < j2 else exp[i1][1]
    d = min([near_join(x[1]) for x in exp[i1:i2]] + [near_join(x[1]) for x in fin[j1:j2]] or [99])
    tag = "AT-JOIN" if d <= a.near else "ASR"
    at_join += tag == "AT-JOIN"; asr += tag == "ASR"
    lines.append("%7.2f  %-7s %+.2fs  said: %-32s heard: %s" % (t, tag, d, repr(said)[:32], repr(heard)))
head = "word-audit: %d kept words vs %d heard; %d mismatches at a join, %d elsewhere (transcriber variance)" % (len(exp), len(fin), at_join, asr)
text = head + "\n" + "\n".join(lines) + "\n"
if a.out: open(a.out, "w").write("# Word audit\n\n```\n" + text + "```\n")
print(text, end="")
