#!/usr/bin/env python3
"""overlay-patches.py: dress a finished long video (a Tella 4K export) by rendering ONLY the overlay windows.

A 17-minute 4K render costs half an hour or more; ten overlay windows cost minutes. For each window
"name t0 t1" (t0 before its first host enters, t1 after its last host exits; 0.5 s of margin each side) this:
  --render   makes a window-patch.py copy of --public and renders it (4K, 45 Mb/s, one worker) to PATCHES/name.mp4,
             skipping windows already rendered;
  --composite lays every patch over --base inside its window (frame-exact, shifted to t0), mixes the storyboard's
             "sfx_mix" sounds ({"src","at","volume"}, peak-trimmed files; the patches are picture only), and encodes
             --out at 45 Mb/s with full BT.709 tags.
Prove alignment on one patch: PSNR of its first frame against the base at t0 and the frames either side; the true match
scores highest (46 dB after three encodes is normal; a one-frame slip drops to ~36).

  --make-windows writes --windows from --storyboard first: every beat AND every chapter tag, [in - 0.5, out + 0.5],
             merged when under 1 s apart (a tag left out of every window is never rendered: window-patch hides it).

Usage: python3 overlay-patches.py --public W/public --base W/export-4k.mp4 --windows W/windows.txt --patches W/patches
         [--storyboard W/storyboard.json] --out W/composite-4k.mp4 [--render] [--composite] [--encoder libx264]
  windows.txt: one "name t0 t1" per line (# comments allowed).
"""
import argparse, json, os, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument("--public"); ap.add_argument("--base", required=True); ap.add_argument("--windows", required=True)
ap.add_argument("--patches", required=True); ap.add_argument("--storyboard"); ap.add_argument("--out")
ap.add_argument("--render", action="store_true"); ap.add_argument("--composite", action="store_true")
ap.add_argument("--encoder", default="h264_videotoolbox", help="libx264 where there is no VideoToolbox")
ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--make-windows", action="store_true", help="write --windows from --storyboard (beats + chapter tags)")
a = ap.parse_args()
if not (a.render or a.composite or a.make_windows):
    ap.error("pass --make-windows, --render, --composite or a mix")
if a.make_windows:
    if not a.storyboard: sys.exit("--make-windows needs --storyboard")
    sb = json.load(open(a.storyboard))
    items = [(b["id"], float(b["in"]), float(b["out"])) for b in sb.get("beats", [])]
    items += [("tag%d" % i, float(t["in"]), float(t["out"])) for i, t in enumerate(sb.get("tags") or [], 1)]
    merged = []
    for n, s0, s1 in sorted(items, key=lambda x: x[1]):
        s0, s1 = max(0.0, s0 - 0.5), s1 + 0.5
        if merged and s0 - merged[-1][2] < 1.0:
            merged[-1][2] = max(merged[-1][2], s1); merged[-1][0] += "+" + n
        else:
            merged.append([n, s0, s1])
    open(a.windows, "w").write("".join("%s %.2f %.2f\n" % (n[:80], s0, s1) for n, s0, s1 in merged))
    print("windows: %d (%.0f s of %d beats and %d tags) -> %s" % (len(merged), sum(x[2] - x[1] for x in merged),
          len(sb.get("beats", [])), len(sb.get("tags") or []), a.windows))
HERE = os.path.dirname(os.path.abspath(__file__))
wins = []
for line in open(a.windows):
    line = line.split("#")[0].split()
    if len(line) == 3:
        wins.append((line[0], round(float(line[1]) * a.fps) / a.fps, round(float(line[2]) * a.fps) / a.fps))
os.makedirs(a.patches, exist_ok=True)

if a.render:
    if not a.public: sys.exit("--render needs --public")
    env = dict(os.environ, PRODUCER_BROWSER_GPU_MODE="hardware", NODE_OPTIONS="--max-old-space-size=8192")
    for n, t0, t1 in wins:
        mp4 = os.path.join(a.patches, n + ".mp4")
        if os.path.exists(mp4) and os.path.getsize(mp4) > 0:
            print("skip", n); continue
        proj = os.path.join(a.patches, n)
        subprocess.run([sys.executable, os.path.join(HERE, "window-patch.py"), "--public", a.public, "--t0", str(t0),
                        "--t1", str(t1), "--out", proj], check=True, capture_output=True)
        r = subprocess.run(["npx", "hyperframes", "render", os.path.join(proj, "public"), "--resolution", "4k", "--video-bitrate",
                            "45M", "--gpu", "--workers", "1", "-o", mp4], env=env, capture_output=True, text=True)
        print(("OK %s %.3f-%.3f" % (n, t0, t1)) if r.returncode == 0 else ("FAIL %s: %s" % (n, r.stderr[-300:])), flush=True)

if a.composite:
    if not a.out: sys.exit("--composite needs --out")
    sfx = json.load(open(a.storyboard)).get("sfx_mix", []) if a.storyboard else []
    sfx_root = os.path.dirname(a.storyboard) if a.storyboard else "."
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", a.base]
    for n, _, _ in wins:
        p = os.path.join(a.patches, n + ".mp4")
        if not os.path.exists(p): sys.exit("missing patch %s: run --render first" % p)
        cmd += ["-i", p]
    for s in sfx:
        cmd += ["-i", s["src"] if os.path.isabs(s["src"]) else os.path.join(sfx_root, "public", s["src"])]
    fc, last = [], "0:v"
    for i, (n, t0, t1) in enumerate(wins, start=1):
        fc.append("[%d:v]setpts=PTS-STARTPTS+%.4f/TB[p%d]" % (i, t0, i))
        fc.append("[%s][p%d]overlay=enable='between(t,%.4f,%.4f)':eof_action=pass[v%d]" % (last, i, t0, t1 - 0.5 / a.fps, i))
        last = "v%d" % i
    k, mix = len(wins) + 1, ["[0:a]"]
    for j, s in enumerate(sfx):
        ms = int(round(float(s["at"]) * 1000))
        fc.append("[%d:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=%.3f,adelay=%d|%d[s%d]" % (k + j, s.get("volume", 0.33), ms, ms, j))
        mix.append("[s%d]" % j)
    fc.append("%samix=inputs=%d:duration=first:normalize=0[a]" % ("".join(mix), len(mix)))
    venc = ["-c:v", a.encoder] + (["-b:v", "45M", "-maxrate", "60M"] if a.encoder != "libx264" else ["-crf", "16", "-preset", "medium"])
    cmd += ["-filter_complex", ";".join(fc), "-map", "[%s]" % last, "-map", "[a]"] + venc + [
            "-g", str(2 * a.fps), "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-color_range", "tv", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+write_colr+faststart", a.out]
    subprocess.run(cmd, check=True)
    print("wrote %s: %d patches, %d sounds" % (a.out, len(wins), len(sfx)))
