#!/usr/bin/env python3
"""finish-master.py: a composited 4K master in, the two delivery masters out (voice-only and with the music bed).

The finish that was typed by hand on "Daily Leads", as one command:
  1. chapters: from the storyboard's chapter tags (each starts at floor(tag in - 0.5), the first at 0:00), titles from
     --chapters ("m:ss Title" lines, in order) or the tag labels; or --chapters as-is without a storyboard.
     Checked: first at 0:00, at least 3, each at least 10 s (YouTube's rules). Written as NAME-chapters.txt + ffmetadata.
  2. NAME-nomusic-4k.mp4: the audio alone, two-pass loudnorm (-14 LUFS, true peak -1.5) on a 24-bit WAV, the video
     stream-copied, the chapters embedded. (A one-pass limiter before AAC measured +0.1 dBFS true peak afterwards.)
  3. NAME-4k.mp4 (with --music): the bed looped, louder under the hook than under the body (a 2 s ramp at --hook-end),
     faded in 1 s and out over the last --fade-out s, ducked under the voice (sidechaincompress), mixed to WAV, two-pass
     loudnorm again, video copied, chapters kept. The bed is set by what it MEASURES under the voice, not by a fixed gain:
     the ducking took a bed at -18.5 / -21.5 dB to ~30 dB under the voice, where the creator could not hear it. A first mix
     at --hook-db / --body-db is measured (energy of the ducked bed vs the voice over the frames where the voice speaks),
     the gains are corrected by the miss (the ducking follows the voice, so the bed's gain passes through linearly), the
     bed is mixed again and measured again: --hook-under / --body-under dB under the voice, within --bed-tol.
  4. measures both (ebur128, true peak) and exits 1 when loudness is off by more than 0.5 LU, the true peak is above -1 dB
     or the bed misses its level.

Usage: python3 finish-master.py --in W/final/composite-4k.mp4 --out-dir W/final --name daily-leads-v3
         [--storyboard W/final/storyboard.json] [--chapters W/final/chapters.txt] [--title "Video title"]
         [--music videos/_shared/music/bed.mp3] [--hook-end 19] [--hook-under 14.2] [--body-under 17.2] [--fade-out 4]
         [--lufs -14] [--tp -1.5] [--intro "Intro"]
"""
import argparse, json, math, os, re, subprocess, sys, tempfile
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--in", dest="inp", required=True); ap.add_argument("--out-dir", required=True); ap.add_argument("--name", required=True)
ap.add_argument("--storyboard"); ap.add_argument("--chapters"); ap.add_argument("--title", default="")
ap.add_argument("--intro", default="Intro", help="first chapter's title when the tags give none for 0:00")
ap.add_argument("--music"); ap.add_argument("--hook-end", type=float, default=19.0)
ap.add_argument("--hook-db", type=float, default=-18.5, help="first-pass bed gain under the hook (corrected by measurement)")
ap.add_argument("--body-db", type=float, default=-21.5, help="first-pass bed gain under the body (corrected by measurement)")
ap.add_argument("--hook-under", type=float, default=14.2, help="dB the ducked bed sits under the voice in the hook, measured")
ap.add_argument("--body-under", type=float, default=17.2, help="dB the ducked bed sits under the voice in the body, measured")
ap.add_argument("--bed-tol", type=float, default=1.5, help="dB the measured bed may miss its target")
ap.add_argument("--fade-out", type=float, default=4.0)
ap.add_argument("--lufs", type=float, default=-14.0); ap.add_argument("--tp", type=float, default=-1.5)
a = ap.parse_args()


def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


dur = float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.inp]).stdout.strip())

# ---- 1. chapters
def parse_lines(p):
    out = []
    for line in open(p):
        m = re.match(r"\s*(?:(\d+):)?(\d+):(\d\d)\s+(.+?)\s*$", line)
        if m:
            h, mi, se, t = m.groups(); out.append((int(h or 0) * 3600 + int(mi) * 60 + int(se), t))
    return out

chapters = []
if a.storyboard:
    tags = sorted((json.load(open(a.storyboard)).get("tags") or []), key=lambda t: float(t["in"]))
    starts = [0] + [max(0, int(math.floor(float(t["in"]) - 0.5))) for t in tags]
    names = [a.intro] + [t.get("chapter") or t["label"] for t in tags]
    if a.chapters:
        given = parse_lines(a.chapters)
        if len(given) == len(starts): names = [t for _, t in given]
        else: sys.exit("--chapters has %d lines, the storyboard %d chapters (tags + the opening)" % (len(given), len(starts)))
    if len(starts) > 1 and starts[1] == 0: starts, names = starts[1:], names[1:]     # a tag at 0:00 opens the video itself
    chapters = list(zip(starts, names))
elif a.chapters:
    chapters = parse_lines(a.chapters)
problems = []
if chapters:
    if chapters[0][0] != 0: problems.append("first chapter must start at 0:00")
    if len(chapters) < 3: problems.append("YouTube needs at least 3 chapters")
    for (s0, t0), (s1, _) in zip(chapters, chapters[1:]):
        if s1 - s0 < 10: problems.append("%r is %d s long (10 s minimum)" % (t0, s1 - s0))
    if problems: sys.exit("chapters: " + "; ".join(problems))
os.makedirs(a.out_dir, exist_ok=True)
tmp = tempfile.mkdtemp(prefix="finish-")
meta = os.path.join(tmp, "chapters.ffmeta")
with open(meta, "w") as f:
    f.write(";FFMETADATA1\n" + ("title=%s\n" % a.title if a.title else ""))
    for i, (s0, t) in enumerate(chapters):
        e = chapters[i + 1][0] if i + 1 < len(chapters) else dur
        f.write("[CHAPTER]\nTIMEBASE=1/1000\nSTART=%d\nEND=%d\ntitle=%s\n" % (s0 * 1000, int(e * 1000), t.replace("=", "\\=")))
if chapters:
    txt = os.path.join(a.out_dir, a.name + "-chapters.txt")
    open(txt, "w").write("".join("%d:%02d %s\n" % (s0 // 60, s0 % 60, t) if s0 < 3600 else
                                 "%d:%02d:%02d %s\n" % (s0 // 3600, s0 % 3600 // 60, s0 % 60, t) for s0, t in chapters))
    print("chapters: %d -> %s" % (len(chapters), txt))


# ---- 2/3. two-pass loudnorm on a WAV, then the video copied
def loudnorm_filter(wav):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", wav, "-af", "loudnorm=I=%g:TP=%g:LRA=11:print_format=json" % (a.lufs, a.tp),
                        "-f", "null", "-"], capture_output=True, text=True)
    d = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    return ("loudnorm=I=%g:TP=%g:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true"
            % (a.lufs, a.tp, d["input_i"], d["input_tp"], d["input_lra"], d["input_thresh"], d["target_offset"]))


def mux(video_src, wav, out):
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", video_src, "-i", wav, "-i", meta, "-map", "0:v", "-map", "1:a",
           "-map_metadata", "2", "-map_chapters", "2" if chapters else "-1", "-c:v", "copy", "-af", loudnorm_filter(wav),
           "-ar", "48000", "-c:a", "aac", "-b:a", "256k", "-movflags", "+write_colr+faststart", out]
    sh(cmd)


voice = os.path.join(tmp, "voice.wav")
sh(["ffmpeg", "-y", "-v", "error", "-i", a.inp, "-vn", "-c:a", "pcm_s24le", "-ar", "48000", voice])
nomusic = os.path.join(a.out_dir, a.name + "-nomusic-4k.mp4")
mux(a.inp, voice, nomusic)
outs = [nomusic]
bed_ok, bed_lines = True, []
if a.music:
    g = lambda db: 10 ** (db / 20)
    he = a.hook_end

    def pcm(path):
        """16 kHz mono float samples of an audio file, for the bed measurement"""
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                             capture_output=True, check=True).stdout
        return np.frombuffer(raw, dtype=np.int16).astype(float)

    def under(v, b, t0, t1):
        """dB the bed sits under the voice over [t0, t1): energy over the 100 ms frames where the voice speaks"""
        i0, i1 = int(t0 * 10), int(t1 * 10)
        n = min(len(v), len(b)) // 1600
        if i1 > n: i1 = n
        if i1 - i0 < 5: return None
        fv = (v[: n * 1600].reshape(n, 1600) ** 2).mean(axis=1)[i0:i1]
        fb = (b[: n * 1600].reshape(n, 1600) ** 2).mean(axis=1)[i0:i1]
        sp = fv > fv.max() * 10 ** (-30 / 10)                       # speaking frames: within 30 dB of the loudest
        if sp.sum() < 3 or fb[sp].mean() <= 0: return None
        return 10 * math.log10(fv[sp].mean() / fb[sp].mean())

    def bed_mix(hdb, bdb):
        hg, bg = g(hdb), g(bdb)
        vol = "if(lt(t,%.3f),%.5f,if(lt(t,%.3f),%.5f+(%.5f-%.5f)*(t-%.3f)/2,%.5f))" % (he, hg, he + 2, hg, bg, hg, he, bg)
        fc = ("[0:a]asplit=2[voice][sc];[1:a]aformat=sample_rates=48000:channel_layouts=stereo,volume='%s':eval=frame,afade=t=in:d=1,"
              "afade=t=out:st=%.3f:d=%.3f[bed];[bed][sc]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350,asplit=2[duck][bout];"
              "[voice][duck]amix=inputs=2:duration=first:normalize=0[a]" % (vol, max(0.0, dur - a.fade_out), a.fade_out))
        mix, bedw = os.path.join(tmp, "mix.wav"), os.path.join(tmp, "bed.wav")
        sh(["ffmpeg", "-y", "-v", "error", "-i", nomusic, "-stream_loop", "-1", "-i", a.music, "-filter_complex", fc,
            "-map", "[a]", "-t", "%.3f" % dur, "-c:a", "pcm_s24le", "-ar", "48000", mix,
            "-map", "[bout]", "-t", "%.3f" % dur, "-c:a", "pcm_s24le", "-ar", "48000", bedw])
        b = pcm(bedw)
        return mix, under(V, b, 1.0, he), under(V, b, he + 2, dur - a.fade_out - 1)

    V = pcm(nomusic)                                       # the voice exactly as it enters the mix
    withmusic = os.path.join(a.out_dir, a.name + "-4k.mp4")

    def in_master():
        """the bed as it plays in the finished master: master minus the no-music master, the voice gain-matched first
        (each master has its own loudnorm gain, and loudnorm can turn dynamic and squeeze the bed)"""
        m = pcm(withmusic); n = min(len(m), len(V)); m, v = m[:n], V[:n]
        gm = float(np.dot(m, v) / np.dot(v, v)); v = gm * v; b = m - v
        return under(v, b, 1.0, he), under(v, b, he + 2, dur - a.fade_out - 1)

    hdb, bdb = a.hook_db, a.body_db
    for rnd in range(3):                                   # mix, measure in the master, correct by the miss (the bed's
        mix, _, _ = bed_mix(hdb, bdb)                      # gain passes the ducking linearly), at most three rounds
        mux(nomusic, mix, withmusic)
        uh, ub = in_master()
        miss = [abs(u - w) for u, w in ((uh, a.hook_under), (ub, a.body_under)) if u is not None]
        if not miss or max(miss) <= a.bed_tol / 2: break
        if uh is not None: hdb += uh - a.hook_under
        if ub is not None: bdb += ub - a.body_under
    for lab, u, want, gain in (("hook", uh, a.hook_under, hdb), ("body", ub, a.body_under, bdb)):
        if u is None:
            bed_lines.append("bed  %s: no speech to measure" % lab); continue
        ok = abs(u - want) <= a.bed_tol
        bed_ok &= ok
        bed_lines.append("%-4s bed %s %.1f dB under the voice in the master (target %.1f, gain %.1f dB)" % ("OK" if ok else "FAIL", lab, u, want, gain))
    outs.append(withmusic)

# ---- 4. measure
bad = False
for o in outs:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", o, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    summ = r[r.rindex("Summary:"):]
    i = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summ).group(1)); tp = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summ).group(1))
    nch = len(json.loads(sh(["ffprobe", "-v", "error", "-show_chapters", "-of", "json", o]).stdout).get("chapters", []))
    ok_ch = nch == len(chapters)
    ok = abs(i - a.lufs) <= 0.5 and tp <= -1.0 and ok_ch
    bad |= not ok
    print("%-4s %s  %.1f LUFS, true peak %.1f dBFS, %d chapters" % ("OK" if ok else "FAIL", os.path.basename(o), i, tp, nch))
for line in bed_lines: print(line)
sys.exit(1 if bad or not bed_ok else 0)
