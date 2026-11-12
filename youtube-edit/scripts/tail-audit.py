#!/usr/bin/env python3
"""tail-audit.py: find (and fix) word endings the cut clips off: the "-ce" of "audience", the "-rs" of "dollars".

A word often ends: vowel, a 20-60 ms near-silent stop or dip, then a soft final consonant (s, ce, ts, rs, st) that is
mostly high-frequency hiss. tighten-cut and edge-audit see the dip as the end of speech (full-band RMS under ~300), so
the edge lands in it and the final consonant is cut: "no audien", "three hundred thousand dolla". Viewers hear it.

For every kept segment end this looks 0.45 s past the edge at 10 ms steps, full band and a high band (first difference,
the hiss), against the file's own room tone. If sound resumes within --gap (0.08 s), reaches a real consonant (--min-high 80 in the high band, or --min-full
150 full band; breath and room noise stay under that), and then stops into real silence
(--quiet 0.12 s) before --max (0.45 s), the edge is moved to the end of that sound plus --release (0.04 s), never
into the next kept segment. If the sound runs on past --max (the next word follows without a pause) the edge is
reported as RUN-ON for join-check.py, not moved.

Usage: python3 tail-audit.py --audio W/audio-raw.wav --cut-list W/cut-list.json [--fix] [--report W/TAILS.md]
Run it after edge-audit is at 0 and before apply-cut, on every cut; again after any patch.
"""
import argparse, json, wave

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--audio", required=True); ap.add_argument("--cut-list", required=True)
ap.add_argument("--fix", action="store_true"); ap.add_argument("--report")
ap.add_argument("--transcript", help="raw transcript: skip an extension that would bring back the start of another (dropped) word")
ap.add_argument("--gap", type=float, default=0.08)
ap.add_argument("--min-high", type=float, default=80, help="high-band peak a real final consonant reaches (breath ~30-60)")
ap.add_argument("--min-full", type=float, default=150, help="or a full-band peak (voiced endings: -ed, -n, a vowel decay)"); ap.add_argument("--quiet", type=float, default=0.12)
ap.add_argument("--max", type=float, default=0.45); ap.add_argument("--release", type=float, default=0.04)
a = ap.parse_args()

f = wave.open(a.audio); sr = f.getframerate()
x = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32)
if f.getnchannels() > 1:
    x = x.reshape(-1, f.getnchannels()).mean(axis=1)
h = np.diff(x, prepend=x[0])                                  # first difference: weights the hiss of s / ce / ts
hop = int(0.01 * sr); n = len(x) // hop
F = np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1))
H = np.sqrt((h[: n * hop].reshape(n, hop) ** 2).mean(1))
# room tone from the file itself: the 10th percentile of each band, floored so a digital-silence file still works
tf, th = max(4 * np.percentile(F, 10), 40.0), max(4 * np.percentile(H, 10), 20.0)
sound = (F > tf) | (H > th)

cl = json.load(open(a.cut_list)); K = cl["kept"]
W = []
if a.transcript:
    raw = json.load(open(a.transcript)); W = raw["words"] if isinstance(raw, dict) and "words" in raw else raw
    W = sorted((float(w["start"]), w["text"]) for w in W)
fixed, runon, lines = 0, 0, []
for i, seg in enumerate(K):
    e = float(seg["end"]); limit = float(K[i + 1]["start"]) if i + 1 < len(K) else len(x) / sr
    k0 = int(round(e / 0.01)); kmax = min(n, int((e + a.max) / 0.01))
    if k0 >= n: continue
    # the first sound frame after the edge, within --gap
    first = next((k for k in range(k0, min(kmax, k0 + int(a.gap / 0.01) + 1)) if sound[k]), None)
    if first is None: continue
    # the end of that sound: the first run of --quiet silent frames
    q, last, k = int(a.quiet / 0.01), None, first
    while k < kmax:
        if not sound[k:k + q].any():
            last = k; break
        k += 1
    if last is None:
        runon += 1; lines.append("%8.3f  RUN-ON  sound continues past +%.2f s: check with join-check.py" % (e, a.max)); continue
    new = min(last * 0.01 + a.release, limit - 0.02)
    if new - e < 0.02: continue
    p0 = max(first, k0 + 1)                                   # skip the edge frame: a hard stop there spikes the high band
    peak = int(H[p0:last].max()) if last > p0 else 0
    fpeak = int(F[p0:last].max()) if last > p0 else 0
    if peak < a.min_high and fpeak < a.min_full:
        continue                                              # a breath or room noise after the word: leave it cut
    intruder = [t for st, t in W if e + 0.08 < st < new - 0.06]
    if intruder:                                              # another word starts inside: that is dropped speech
        lines.append("%8.3f  SKIP    +%.3f s would bring back %r: check with join-check.py" % (e, new - e, " ".join(intruder)))
        continue
    word = next((t for st, t in reversed(W) if st < e), "") if W else ""
    lines.append("%8.3f  TAIL    +%.3f s %-14s (high-band peak %d after a %.0f ms gap)%s" % (e, new - e, ("%r" % word) if word else "",
                 peak, (first - k0) * 10, "  -> fixed" if a.fix else ""))
    if a.fix:
        seg["end"] = round(new, 3)
    fixed += 1
# ---- heads: the same test backwards from every segment start (a clipped first consonant: "that" -> "at") ----
heads, runback = 0, 0
for i, seg in enumerate(K):
    s = float(seg["start"]); prev = float(K[i - 1]["end"]) if i else 0.0
    k0 = int(round(s / 0.01)); kmin = max(0, int((s - a.max) / 0.01))
    if k0 <= 0 or k0 > n: continue
    last = next((k for k in range(k0 - 1, max(kmin, k0 - 1 - int(a.gap / 0.01)) - 1, -1) if sound[k]), None)
    if last is None: continue
    q, onset, k = int(a.quiet / 0.01), None, last
    while k > kmin:
        if not sound[max(0, k - q):k].any():
            onset = k; break
        k -= 1
    if onset is None:
        runback += 1; lines.append("%8.3f  RUN-BACK sound runs back past -%.2f s (a dropped take's tail?): check with join-check.py" % (s, a.max)); continue
    new = max(onset * 0.01 - 0.03, prev + 0.02)
    if s - new < 0.02: continue
    peak = int(H[onset:k0 - 1].max()) if k0 - 1 > onset else 0
    fpeak = int(F[onset:k0 - 1].max()) if k0 - 1 > onset else 0
    if peak < a.min_high and fpeak < a.min_full:
        continue
    intruder = [t for st, t in W if new + 0.06 < st < s - 0.08]
    if intruder:
        lines.append("%8.3f  SKIP    -%.3f s would bring back %r (dropped): leave it" % (s, s - new, " ".join(intruder)))
        continue
    word = next((t for st, t in W if st >= s - 0.4), "") if W else ""
    lines.append("%8.3f  HEAD    -%.3f s %-14s (high-band peak %d)%s" % (s, s - new, ("%r" % word) if word else "", peak,
                 "  -> fixed" if a.fix else ""))
    if a.fix:
        seg["start"] = round(new, 3)
    heads += 1
head = "tail-audit: %d segments, %d clipped tails%s, %d run-on; %d clipped heads%s, %d run-back (room tone: full %.0f, high %.0f)" % (
    len(K), fixed, " fixed" if a.fix else "", runon, heads, " fixed" if a.fix else "", runback, tf / 4, th / 4)
fixed += heads
if a.fix and fixed:
    cl["kept_seconds"] = round(sum(s["end"] - s["start"] for s in K), 2)
    json.dump(cl, open(a.cut_list, "w"), indent=1)
text = head + "\n" + "\n".join(lines) + "\n"
if a.report:
    open(a.report, "w").write("# Tail audit\n\n```\n" + text + "```\n")
print(text, end="")
