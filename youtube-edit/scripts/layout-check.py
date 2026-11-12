#!/usr/bin/env python3
"""layout-check.py: every overlay checked for text outside its box or the frame, at the moments it is fully built.

`hyperframes check` samples 9 evenly spaced moments: on a long video that misses almost every beat, so a list item
spilling out of its glass card ("3 valuable comments" running past a 440 px card) shipped with the check green. This
samples each beat where it is complete and each item where it has just landed:
  every item / pill / stat at its own time + 0.5 s, every beat at its midpoint and at out - 0.45 s (all items in,
  exit not started), every chapter tag at in + 1.0 s
and runs `hyperframes check --at <those> --frame-check` in batches. Reported, by beat:
  text_box_overflow      text outside its card or glass (error in check)
  container_overflow     nowrap text wider than its row (the cause of the above)
  any frame / clip finding  text leaving the 1920x1080 frame
  contrast_aa_failure    text under WCAG AA against what is behind it at that moment (magenta in a .45 chip over a
                         white page measured 1.1:1; the 9-sample check found it only by luck)
Exit 1 when anything is found. Run it at Checkpoint B (after compose, before snapshots) and after every storyboard change.

Usage: python3 layout-check.py --project W/public [--storyboard W/storyboard.json] [--out W/LAYOUT.md] [--batch 40]
  --plan-only        print the sample times and stop (no browser)
  --from-json F ...  read saved `check --json` outputs instead of running the browser (tests, re-reports)
"""
import argparse, json, os, re, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True, help="the composed public/ folder")
ap.add_argument("--storyboard", help="default: storyboard.json next to the public/ folder")
ap.add_argument("--out"); ap.add_argument("--batch", type=int, default=40)
ap.add_argument("--plan-only", action="store_true"); ap.add_argument("--from-json", nargs="+")
a = ap.parse_args()
sb_path = a.storyboard or os.path.join(os.path.dirname(os.path.abspath(a.project)), "storyboard.json")
S = json.load(open(sb_path))
D = float(S.get("duration", 0)) or 1e9


def item_times(b):
    out = []
    for i in b.get("items") or []:
        if isinstance(i, dict):
            t = i.get("at", i.get("t"))
        elif isinstance(i, (list, tuple)):
            t = next((x for x in i if isinstance(x, (int, float)) and not isinstance(x, bool)), None)
        else:
            t = None
        if t is not None: out.append(float(t))
    return out


samples = {}                                   # time -> beat id (the beat that time was chosen for)
for b in S.get("beats", []):
    t0, t1 = float(b["in"]), float(b["out"])
    ts = [t + 0.5 for t in item_times(b)] + [(t0 + t1) / 2, t1 - 0.45]
    for t in ts:
        t = round(min(max(t, t0 + 0.3), t1 - 0.2, D - 0.05), 2)
        if t > 0: samples.setdefault(t, b["id"])
for i, t in enumerate(S.get("tags") or [], 1):
    samples.setdefault(round(min(float(t["in"]) + 1.0, float(t["out"]) - 0.2), 2), "tag%d" % i)
times = sorted(samples)
if a.plan_only:
    print("%d samples over %d beats and %d tags" % (len(times), len(S.get("beats", [])), len(S.get("tags") or [])))
    print(" ".join("%.2f" % t for t in times)); sys.exit(0)

reports = []
if a.from_json:
    reports = [json.load(open(p)) for p in a.from_json]
else:
    for k in range(0, len(times), a.batch):
        chunk = times[k:k + a.batch]
        r = subprocess.run(["npx", "hyperframes", "check", a.project, "--json", "--at", ",".join("%.2f" % t for t in chunk),
                            "--frame-check", "--no-collapse-static", "--max-issues", "2000"],
                           capture_output=True, text=True)
        try:
            reports.append(json.loads(r.stdout))
        except ValueError:
            sys.exit("hyperframes check gave no JSON (exit %d): %s" % (r.returncode, r.stderr[-400:]))
        print("checked %d/%d samples" % (min(k + a.batch, len(times)), len(times)), file=sys.stderr, flush=True)

LAYOUT = re.compile(r"overflow|frame|offscreen|off_screen|outside|clip|contrast_aa", re.I)
found = {}
for rep in reports:
    for sec in ("layout", "craft", "contrast"):
        for f in (rep.get(sec) or {}).get("findings", []) or []:
            code = f.get("code", "")
            if not LAYOUT.search(code) or code.startswith("clip_media"): continue
            sel = f.get("selector", "")
            m = re.match(r"#([A-Za-z0-9_-]+?)(?:-(?:i|pi|b|glass|inner|chip|si)\d*)?(?:[ >.:#\[]|$)", sel)
            t = f.get("time")
            beat = m.group(1) if m else samples.get(round(float(t), 2), "?") if t is not None else "?"
            key = (beat, code, f.get("text") or sel)
            ov = f.get("overflow") or {}
            px = max([abs(float(v)) for v in ov.values()] or [0]) if ov else float(f.get("ratio") or 0)
            if key not in found or px > found[key][1]:
                found[key] = (t, px, f.get("severity", ""), sel, f.get("containerSelector", ""))
lines = ["%8s  %-14s %-20s %-7s %5.0f px  %-36r in %s" % ("%.2f" % v[0] if v[0] is not None else "-", k[0][:14], k[1][:20], v[2], v[1],
         k[2][:36], v[4] or v[3]) for k, v in sorted(found.items(), key=lambda kv: kv[1][0] or 0)]
beats = sorted({k[0] for k in found})
head = "layout-check: %d samples, %d finding(s) in %d beat(s)%s" % (len(times), len(found), len(beats),
       (": " + ", ".join(beats)) if beats else "; every overlay inside its box and the frame")
text = head + "\n" + "".join(l + "\n" for l in lines)
if a.out: open(a.out, "w").write("# Layout check\n\n```\n" + text + "```\n")
print(text, end="")
sys.exit(1 if found else 0)
