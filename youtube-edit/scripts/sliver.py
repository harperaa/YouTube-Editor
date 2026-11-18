#!/usr/bin/env python3
"""sliver.py --cut-list W/cut-list.json --audio <the raw clip's audio wav> [--threshold 300] [--fix]: the glitches edge-audit's
RMS window lets through (breath or tail fragments, and heads carrying a previous word's tail; a long take can hold a handful
of each). Run it after tighten-cut and before edge-audit; --fix rewrites the cut list.
  1. a segment with no 10 ms frame above --threshold RMS (default 300, as edge-audit; lower it for a quiet recording): a
     breath or the decaying tail of a dropped take that tighten-cut split off (it keeps a Parakeet word start inside, so
     edge-audit's fragment check misses it) -> drop
  2. a HEAD that continues the sound before it (30 ms before and after the cut both over 100 RMS) and decays into a quiet run
     (>= 50 ms under 70 RMS) inside its first 0.35 s: the tail of the dropped word rides in -> start moves into the quiet run,
     LEAD s before the next sound
  3. a TAIL whose last 0.35 s holds a quiet run followed by rising sound up to the cut, while the sound continues after the cut:
     the onset of the next dropped word leaks out -> end moves into the quiet run, TAIL s after the last sound
  4. a lead or tail under 40 ms with quiet room outside it -> widened into the room (max 0.10 s)
After the fixes, widening stops at the neighbouring segment's edge (no frame plays twice) and a segment whose fixes leave
start >= end is dropped and logged. --fix refuses to write a cut list with no speech segment left (exit 1)."""
import json, os, sys, wave, numpy as np
import argparse
ap = argparse.ArgumentParser(); ap.add_argument("--cut-list", required=True); ap.add_argument("--audio", required=True)
ap.add_argument("--threshold", type=float, default=300, help="RMS a 10 ms frame must pass to count as sound (default 300, as edge-audit)")
ap.add_argument("--fix", action="store_true"); A = ap.parse_args(); fix = A.fix; TH = A.threshold
w = wave.open(A.audio); sr = w.getframerate(); FR = sr // 100                       # one RMS frame = 10 ms
x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
if w.getnchannels() > 1: x = x.reshape(-1, w.getnchannels()).mean(axis=1)
n = len(x) // FR; r = np.sqrt((x[: n * FR].reshape(n, FR) ** 2).mean(axis=1))
F = lambda t: int(round(t * 100))
rm = lambda a, b: float(np.sqrt(np.mean(x[int(a * sr):max(int(b * sr), int(a * sr) + 1)] ** 2)))
LEAD, TAIL, Q, QRUN = 0.08, 0.10, 70, 5
P = A.cut_list; sec = os.path.basename(os.path.dirname(os.path.abspath(P))); d = json.load(open(P)); out, idx, changes = [], [], []
def quiet_runs(i0, i1):
    runs, k = [], i0
    while k < i1:
        if r[k] < Q:
            j = k
            while j + 1 < i1 and r[j + 1] < Q: j += 1
            if j - k + 1 >= QRUN: runs.append((k, j))
            k = j + 1
        else: k += 1
    return runs
for i, s in enumerate(d["kept"]):
    if s.get("room_tone"): out.append(s); idx.append(i); continue
    a, b = F(s["start"]), F(s["end"])
    if not (r[a:b] > TH).any():
        changes.append("seg %d %.3f-%.3f: no frame over %g RMS (breath or tail of a dropped take), dropped" % (i, s["start"], s["end"], TH)); continue
    ns, ne = s["start"], s["end"]
    # 2. head continuing the previous sound
    if rm(ns - 0.03, ns) > 100 and rm(ns, ns + 0.03) > 100:
        qr = [q for q in quiet_runs(a, min(b, a + 35)) if (r[q[1] + 1:q[1] + 30] > TH).any()]
        if qr:
            k0, k1 = qr[0]; t = max((k0 + 2) / 100, (k1 + 1) / 100 - LEAD)
            changes.append("seg %d head %.3f -> %.3f: the sound before the cut rides in and decays (quiet run %.2f-%.2f)" % (i, ns, t, k0 / 100, (k1 + 1) / 100)); ns = t
    # 3. tail leaking the next onset
    if rm(ne - 0.03, ne) > 100 and rm(ne, ne + 0.03) > 100:
        qr = [q for q in quiet_runs(max(a, b - 35), b) if (r[max(a, q[0] - 30):q[0]] > TH).any()]
        if qr:
            k0, k1 = qr[-1]; t = min((k1 - 1) / 100, k0 / 100 + TAIL)
            changes.append("seg %d tail %.3f -> %.3f: an onset after a quiet run leaks out (quiet run %.2f-%.2f)" % (i, ne, t, k0 / 100, (k1 + 1) / 100)); ne = t
    # 4. tight lead / tail with quiet room outside
    A, Bf = F(ns), F(ne); loud = np.where(r[A:Bf] > TH)[0]
    if len(loud):
        lead = loud[0] / 100; tail = (Bf - A - 1 - loud[-1]) / 100
        if lead < 0.04:
            room = 0
            while A - room - 1 > 0 and r[A - room - 1] < Q and room < 10: room += 1
            if room >= 3:
                t = ns - min(room, 10) / 100 + 0.01; changes.append("seg %d head %.3f -> %.3f: lead %.2f s widened into quiet" % (i, ns, t, lead)); ns = t
        if tail < 0.04:
            room = 0
            while Bf + room < n and r[Bf + room] < Q and room < 10: room += 1
            if room >= 3:
                t = ne + min(room, 10) / 100 - 0.01; changes.append("seg %d tail %.3f -> %.3f: tail %.2f s widened into quiet" % (i, ne, t, tail)); ne = t
    out.append(dict(s, start=round(ns, 3), end=round(ne, 3))); idx.append(i)
# consistency: each segment was fixed on its own; walk them in source-time order
def drop_inverted():
    for k in [k for k, s in enumerate(out) if s["start"] >= s["end"]][::-1]:
        changes.append("seg %d %.3f-%.3f: the fixes leave start >= end (%.3f-%.3f), dropped"
                       % (idx[k], d["kept"][idx[k]]["start"], d["kept"][idx[k]]["end"], out[k]["start"], out[k]["end"]))
        del out[k]; del idx[k]
drop_inverted()
order = sorted(range(len(out)), key=lambda k: (d["kept"][idx[k]]["start"], d["kept"][idx[k]]["end"]))
for p, c in zip(order, order[1:]):
    sp, sc = out[p], out[c]; g0, g1 = d["kept"][idx[p]]["end"], d["kept"][idx[c]]["start"]
    if sp["end"] <= sc["start"] or g0 > g1: continue                  # no overlap, or the input already overlapped (left as is)
    wp, wc = sp["end"] > g0, sc["start"] < g1                          # who widened into the gap
    t = sc["start"] if not wc else sp["end"] if not wp else min(max(round((g0 + g1) / 2, 3), sc["start"]), sp["end"])
    if sp["end"] != t: changes.append("seg %d tail %.3f -> %.3f: widening stopped at seg %d's head" % (idx[p], sp["end"], t, idx[c]))
    if sc["start"] != t: changes.append("seg %d head %.3f -> %.3f: widening stopped at seg %d's tail" % (idx[c], sc["start"], t, idx[p]))
    out[p] = dict(sp, end=t); out[c] = dict(sc, start=t)
drop_inverted()
print("%s: %d segments, %d changes" % (sec, len(d["kept"]), len(changes)))
for c in changes: print("  " + c)
if changes and not any(not s.get("room_tone") for s in out):
    msg = ("every speech segment would be dropped (see above). If they say 'no frame over %g RMS', the recording is quiet: "
           "rerun with a lower --threshold (e.g. 150; give edge-audit the same value)" % TH)
    if fix: sys.exit("sliver.py: %s; %s not written" % (msg, P))
    print("WARNING: " + msg)
if fix and changes:
    d["kept"] = out; d["kept_seconds"] = round(sum(k["end"] - k["start"] for k in out), 3)
    d.setdefault("hand_fixes", []).extend("sliver.py: " + c for c in changes)
    json.dump(d, open(P, "w"), indent=1); print("wrote %s (%d segments, %.2f s)" % (P, len(out), d["kept_seconds"]))
