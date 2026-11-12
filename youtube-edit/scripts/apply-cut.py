#!/usr/bin/env python3
"""apply-cut.py: turn cut-list.json into a frame-accurate flat cut (one re-encode, dense keyframes, BT.709 tags).

Every kept start/end is first SNAPPED to the source frame grid (r_frame_rate, 30000/1001 handled, relative to the
video stream's start_time). Video is trimmed with a half-frame guard so segment k keeps exactly frames k0..k1-1;
audio is trimmed at the same snapped times. Without the snap each segment ran to its longer stream (whole frames
vs exact audio), ~1/6 frame long on average: 200 joins drifted the flat cut ~1.1 s past cut-map.json.

Each segment gets a 20 ms audio fade at both ends so cuts never click, then all are concatenated. Output is the
HyperFrames-ready intermediate: H.264 CRF 16, keyframe every 30 frames, 30 fps CFR, AAC 256k, full BT.709 tags.
Also writes cut-map.json (where every jump cut landed in the flat cut, and where it came from in the source,
all in snapped times) for the dressing pass and for patch-cut.py --drop-flat.

After encoding it probes the output: video duration must equal flat_duration within one output frame and the
video and audio streams must agree within 0.12 s. Otherwise it prints a loud DRIFT line and exits 2 (the file
is still written).

Usage:
  python3 apply-cut.py --input raw.mp4 --cut-list cut-list.json --out public/input-video.mp4 [--fps 30] [--crf 16]
  python3 apply-cut.py --input raw.mp4 --cut-list cut-list.json --out W/audio.wav --audio-only
    the same snapped joins and cut-map.json, the flat AUDIO only (16 kHz mono WAV): for the dead-air passes when the
    video will be cut elsewhere (a Tella export re-cut in Tella). A 17-minute 4K flat cut took ~23 minutes per pass
    and was thrown away four times; the audio takes seconds.
"""
import argparse, json, subprocess, os, sys
from fractions import Fraction

ap = argparse.ArgumentParser()
ap.add_argument("--input", required=True)
ap.add_argument("--cut-list", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--crf", type=int, default=16)
ap.add_argument("--preset", default="fast")
ap.add_argument("--audio-only", action="store_true", help="write the flat audio (16 kHz mono WAV) and cut-map.json, no video")
args = ap.parse_args()

def probe(path, *entries):
    r = subprocess.run(["ffprobe", "-v", "error"] + [x for e in entries for x in ("-show_entries", e)] + ["-of", "json", path],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)

def num(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default

# ---- source frame grid ---------------------------------------------------------------------------------
info = probe(args.input, "stream=codec_type,r_frame_rate,start_time", "format=start_time")
vs = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
if vs is None:
    sys.exit("no video stream in %s" % args.input)
rate = Fraction(vs.get("r_frame_rate", "%d/1" % args.fps))
if rate <= 0:
    rate = Fraction(args.fps)
# ffmpeg shifts every stream by the container start_time, so inside the filter graph the first video frame sits
# at (video start_time - format start_time); the grid is k / rate from there.
origin = num(vs.get("start_time")) - num(info.get("format", {}).get("start_time"))
# A source at a whole multiple of the output rate (60 fps camera, 30 fps cut) snaps to the OUTPUT grid: every output
# frame is also a source frame, and segments of whole output frames concatenate to exactly the cut-map length (on the
# 1/60 grid, odd-frame segments rounded up and a 17-minute cut ended 1.5 frames long, a false DRIFT).
src_rate = rate
if rate > args.fps and (rate / args.fps).denominator == 1:
    rate = Fraction(args.fps)
half = 0.5 / float(rate)
snap = lambda t: int(round((Fraction(t) - Fraction(origin)) * rate))
at = lambda k: origin + float(Fraction(k) / rate)

cl = json.load(open(args.cut_list))
FADE = 0.02
parts, chain, cut_map, skipped = [], [], [], []
flat = Fraction(0)
for s in cl["kept"]:
    k0, k1 = max(0, snap(s["start"])), snap(s["end"])
    if k1 <= k0:
        skipped.append(s); continue
    i = len(parts)
    t0, t1 = at(k0), at(k1)
    d = float(Fraction(k1 - k0) / rate)
    if not args.audio_only:
        chain.append("[0:v]trim=start=%.6f:end=%.6f,setpts=PTS-STARTPTS[v%d]" % (t0 - half, t1 - half, i))
    chain.append("[0:a]atrim=start=%.6f:end=%.6f,asetpts=PTS-STARTPTS,afade=t=in:d=%.3f,afade=t=out:st=%.6f:d=%.3f[a%d]"
                 % (t0, t1, FADE, max(0.0, d - FADE), FADE, i))
    parts.append(("[a%d]" if args.audio_only else "[v%d][a%d]") % ((i,) if args.audio_only else (i, i)))
    f0 = flat; flat += Fraction(k1 - k0) / rate
    cut_map.append({"flat_start": round(float(f0), 3), "flat_end": round(float(flat), 3),
                    "src_start": round(t0, 4), "src_end": round(t1, 4), "frames": k1 - k0})
if not parts:
    sys.exit("no kept segment is at least one frame long")
chain.append("".join(parts) + ("concat=n=%d:v=0:a=1[a]" if args.audio_only else "concat=n=%d:v=1:a=1[v][a]") % len(parts))
fc = ";".join(chain)

if args.audio_only:
    script = args.out + ".ffscript"
    open(script, "w").write(fc)
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", args.input, "-/filter_complex", script, "-map", "[a]", "-t", "%.6f" % float(flat),
           "-ar", "16000", "-ac", "1", args.out]
    subprocess.run(cmd, check=True); os.remove(script)
else:
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", args.input, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
           "-r", str(args.fps), "-fps_mode", "cfr",
           # cap at the exact flat length: a high-rate source converted to cfr pads a frame or two at the very end
           "-t", "%.6f" % float(flat),
           "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf), "-g", str(args.fps), "-keyint_min", str(args.fps),
           "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
           "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart+write_colr", args.out]
    subprocess.run(cmd, check=True)
flat_d = round(float(flat), 3)
json.dump({"cuts": [c["flat_start"] for c in cut_map[1:]], "segments": cut_map, "flat_duration": flat_d,
           "source_fps": "%d/%d" % (src_rate.numerator, src_rate.denominator), "grid_fps": "%d/%d" % (rate.numerator, rate.denominator), "frame_origin": round(origin, 6)},
          open(os.path.join(os.path.dirname(args.cut_list), "cut-map.json"), "w"), indent=1)
for s in skipped:
    print("skipped %.3f-%.3f: shorter than half a frame" % (s["start"], s["end"]))
print("flat cut %.3fs, %d segments, %d jump cuts, snapped to the %s fps grid -> %s"
      % (flat_d, len(parts), len(parts) - 1, "%g" % float(rate), args.out))

# ---- verify: the file must be as long as cut-map.json says ---------------------------------------------
if args.audio_only:
    ad = num(probe(args.out, "format=duration").get("format", {}).get("duration"), None)
    if ad is None or abs(ad - flat_d) > 0.02:
        print("!!! DRIFT: audio %s s vs cut-map %.3f s" % ("%.3f" % ad if ad is not None else "?", flat_d)); sys.exit(2)
    print("verified: audio %.3f s = cut-map %.3f s" % (ad, flat_d)); sys.exit(0)
out = probe(args.out, "stream=codec_type,duration", "format=duration")
dur = {s.get("codec_type"): num(s.get("duration"), None) for s in out.get("streams", [])}
v, a = dur.get("video"), dur.get("audio")
frame = 1.0 / args.fps
problems = []
if v is None or abs(v - flat_d) > frame + 1e-6:
    problems.append("video %s s vs cut-map %.3f s (limit one frame, %.3f s)" % ("%.3f" % v if v is not None else "?", flat_d, frame))
if v is None or a is None or abs(v - a) > 0.12:
    problems.append("video %s s vs audio %s s (limit 0.12 s)" % tuple("%.3f" % x if x is not None else "?" for x in (v, a)))
if problems:
    print("!!! DRIFT: %s. cut-map.json does not describe this file; do not dress it." % "; ".join(problems))
    sys.exit(2)
print("verified: video %.3f s = cut-map %.3f s (%+.1f ms), audio %.3f s" % (v, flat_d, 1000 * (v - flat_d), a))
