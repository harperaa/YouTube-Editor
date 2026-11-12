"""The tools added after the "Daily Leads" Tella lesson: dropped-runs, tella-map-cuts, stock-search (offline parse),
transcribe-windows (window plan), join-check (dry), overlay-patches (composite). No network, no model."""
import json, os, struct, unittest, wave
from .helpers import ffmpeg, load, needs_ffmpeg, read, run, scratch, write


def words(*spec):
    return [{"text": t, "start": s, "end": e} for t, s, e in spec]


class DroppedRuns(unittest.TestCase):
    def test_inner_drop_is_flagged(self):
        d = scratch(self)
        tr = write(os.path.join(d, "t.json"), words(("its", 0.0, 0.2), ("own", 0.2, 0.4), ("culture,", 0.4, 0.8), ("its", 0.9, 1.1),
                                                   ("own", 1.1, 1.3), ("vibe,", 1.3, 1.6), ("its", 1.7, 1.9), ("own", 1.9, 2.1), ("way.", 2.1, 2.5),
                                                   ("Next", 3.0, 3.3), ("one.", 3.3, 3.6)))
        cl = write(os.path.join(d, "cut-list.json"), {"kept": [{"start": 0.0, "end": 0.85}, {"start": 1.65, "end": 2.6}]})
        r = run("dropped-runs.py", "--transcript", tr, "--cut-list", cl)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("inner", r.stdout); self.assertIn("[[its own vibe,]]", r.stdout)
        self.assertIn("whole", r.stdout); self.assertIn("[[Next one.]]", r.stdout)


class TellaMapCuts(unittest.TestCase):
    def test_maps_through_existing_cuts_and_merges_slivers(self):
        d = scratch(self)
        # clip A plays 0-10 s of the export; its raw recording has a 2 s cut at raw 4 s (so playback 4 = raw 6)
        tl = write(os.path.join(d, "timeline.json"), {"clips": [
            {"id": "A", "timelineStartMs": 0, "durationMs": 10000}, {"id": "B", "timelineStartMs": 10000, "durationMs": 5000}],
            "details": {"clips": [{"clipId": "A", "cuts": [{"startTimeMs": 4000, "durationMs": 2000}]}, {"clipId": "B", "cuts": []}]}})
        # keep export 0-3, 5-9.97 (the 30 ms tail before the clip end becomes a sliver cut), and 11-15
        cl = write(os.path.join(d, "cut-list.json"), {"kept": [{"start": 0, "end": 3}, {"start": 5, "end": 9.97}, {"start": 11, "end": 15}]})
        out = os.path.join(d, "new.json")
        r = run("tella-map-cuts.py", "--cut-list", cl, "--timeline", tl, "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        n = load(out)
        # A: raw 0-3 kept, raw 3-7 cut (playback 3-5 = raw 3-4 + the old 4-6 cut + raw 6-7), raw 7-11.97 kept, tail 30 ms cut
        self.assertEqual(n["A"], [{"startTimeMs": 3000, "durationMs": 4000}, {"startTimeMs": 11970, "durationMs": 30}])
        self.assertEqual(n["B"], [{"startTimeMs": 0, "durationMs": 1000}])


class StockSearch(unittest.TestCase):
    def test_parses_pixabay_and_prefers_4k(self):
        d = scratch(self)
        resp = write(os.path.join(d, "resp.json"), {"totalHits": 2, "hits": [
            {"id": 1, "pageURL": "https://pixabay.com/videos/id-1/", "user": "a", "duration": 9, "tags": "car",
             "videos": {"large": {"url": "", "width": 0, "height": 0, "size": 0, "thumbnail": ""},
                        "medium": {"url": "https://x/1m.mp4", "width": 1920, "height": 1080, "size": 1, "thumbnail": ""},
                        "small": {"url": "https://x/1s.mp4", "width": 1280, "height": 720, "size": 1, "thumbnail": ""}}},
            {"id": 2, "pageURL": "https://pixabay.com/videos/id-2/", "user": "b", "duration": 12, "tags": "office",
             "videos": {"large": {"url": "https://x/2l.mp4", "width": 3840, "height": 2160, "size": 9, "thumbnail": ""},
                        "medium": {"url": "https://x/2m.mp4", "width": 1920, "height": 1080, "size": 1, "thumbnail": ""},
                        "small": {"url": "https://x/2s.mp4", "width": 1280, "height": 720, "size": 1, "thumbnail": ""}}}]})
        r = run("stock-search.py", "--slot", "ceo", "--out-dir", d, "--provider", "pixabay", "--from-json", resp)
        self.assertEqual(r.returncode, 0, r.stderr)
        s = load(os.path.join(d, "shortlist-ceo.json"))
        self.assertEqual([h["id"] for h in s], [2, 1])                 # 4K first
        self.assertEqual(s[0]["url"], "https://x/2l.mp4"); self.assertEqual(s[1]["url"], "https://x/1m.mp4")
        self.assertEqual(s[0]["licence"], "Pixabay Content License")
        self.assertIn("`pixabay:2`", read(os.path.join(d, "shortlist-ceo.md")))


class TranscribeWindows(unittest.TestCase):
    def test_no_silence_cuts_on_the_quietest_frame(self):
        d = scratch(self)
        p = os.path.join(d, "a.wav"); sr = 16000
        with wave.open(p, "w") as w:                                    # 70 s of tone, quiet only at 26.0 s and 52.0 s
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            frames = bytearray()
            for i in range(70 * sr):
                t = i / sr
                amp = 20 if (25.98 < t < 26.04 or 51.98 < t < 52.04) else 8000
                frames += struct.pack("<h", int(amp * (1 if (i // 20) % 2 else -1)))
            w.writeframes(bytes(frames))
        r = run("transcribe-windows.py", "--audio", p, "--out", os.path.join(d, "t.json"), "--plan-only")
        self.assertEqual(r.returncode, 0, r.stderr)
        cuts = json.loads(r.stdout)
        self.assertAlmostEqual(cuts[1], 26.0, delta=0.05); self.assertAlmostEqual(cuts[2], 52.0, delta=0.05)


class TranscribeWindowsDedupe(unittest.TestCase):
    def test_boundary_duplicate_removed_real_double_kept(self):
        # both windows heard "And" across a cut at 197.65: 197.58-197.82 and 197.67-197.91 overlap, so one goes;
        # "that that" spoken twice does not overlap and stays
        d = scratch(self)
        t = write(os.path.join(d, "t.json"), [
            {"text": "itself.", "start": 196.78, "end": 197.58}, {"text": "And", "start": 197.58, "end": 197.82},
            {"text": "And", "start": 197.67, "end": 197.91}, {"text": "that", "start": 197.91, "end": 198.15},
            {"text": "that", "start": 198.2, "end": 198.4}, {"text": "allowed", "start": 198.45, "end": 198.8}])
        r = run("transcribe-windows.py", "--dedupe", t)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual([w["text"] for w in load(t)], ["itself.", "And", "that", "that", "allowed"])


class JoinCheck(unittest.TestCase):
    def test_try_replaces_pieces_inside_window(self):
        d = scratch(self)
        cl = write(os.path.join(d, "cut-list.json"), {"kept": [{"start": 0, "end": 5}, {"start": 6, "end": 7}, {"start": 8, "end": 12}]})
        r = run("join-check.py", "--cut-list", cl, "--audio", "unused.wav", "--t0", 4, "--t1", 10, "--try", "6.2-7.5", "--dry")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [[4.0, 5.0], [6.2, 7.5], [8.0, 10.0]])


@needs_ffmpeg
class OverlayPatches(unittest.TestCase):
    def test_patch_shows_only_in_its_window_and_sfx_mixed(self):
        d = scratch(self)
        base = os.path.join(d, "base.mp4")
        ffmpeg("-f", "lavfi", "-i", "color=c=red:size=160x90:rate=30:duration=6", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
               "-t", "6", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", base)
        os.makedirs(os.path.join(d, "patches"))
        ffmpeg("-f", "lavfi", "-i", "color=c=blue:size=160x90:rate=30:duration=1", "-c:v", "libx264", "-preset", "ultrafast",
               "-pix_fmt", "yuv420p", os.path.join(d, "patches", "p1.mp4"))
        os.makedirs(os.path.join(d, "public", "sfx"))
        ffmpeg("-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=48000:duration=0.3", os.path.join(d, "public", "sfx", "pop.mp3"))
        sb = write(os.path.join(d, "storyboard.json"), {"sfx_mix": [{"src": "sfx/pop.mp3", "at": 4.0, "volume": 1.0}]})
        win = write(os.path.join(d, "windows.txt"), "p1 2.0 3.0\n")
        out = os.path.join(d, "out.mp4")
        r = run("overlay-patches.py", "--base", base, "--windows", win, "--patches", os.path.join(d, "patches"), "--storyboard", sb,
                "--out", out, "--composite", "--encoder", "libx264")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

        def pixel(t):
            import subprocess
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", out, "-frames:v", "1", "-vf", "scale=1:1", "-f", "rawvideo",
                                  "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
            return tuple(raw[:3])
        self.assertGreater(pixel(1.0)[0], 150); self.assertGreater(pixel(2.5)[2], 150); self.assertGreater(pixel(4.5)[0], 150)

        import subprocess
        def peak(t0, dur):
            r2 = subprocess.run(["ffmpeg", "-v", "info", "-ss", str(t0), "-t", str(dur), "-i", out, "-af", "volumedetect", "-f", "null", "-"],
                                capture_output=True, text=True).stderr
            return float(r2.split("max_volume:")[1].split("dB")[0])
        self.assertGreater(peak(4.0, 0.3), -30); self.assertLess(peak(1.0, 0.5), -60)

    def test_make_windows_covers_tags(self):
        d = scratch(self)
        sb = write(os.path.join(d, "storyboard.json"), {"beats": [{"id": "a", "in": 2.0, "out": 4.0}, {"id": "b", "in": 4.6, "out": 6.0}],
                                                       "tags": [{"label": "Recap", "in": 20.0, "out": 24.5}]})
        win = os.path.join(d, "windows.txt")
        r = run("overlay-patches.py", "--base", "x.mp4", "--windows", win, "--patches", os.path.join(d, "p"), "--storyboard", sb, "--make-windows")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(open(win).read().split("\n")[:2], ["a+b 1.50 6.50", "tag1 19.50 25.00"])


if __name__ == "__main__":
    unittest.main()


class StoryboardMd(unittest.TestCase):
    def test_dict_and_dock_items(self):
        d = scratch(self)
        write(os.path.join(d, "storyboard.json"), {"id": "t", "duration": 20.0, "beats": [
            {"type": "pills", "id": "p", "in": 1, "out": 4, "anchor": "-", "items": [{"text": "I agree", "at": 1.2}]},
            {"type": "dock", "id": "k", "in": 5, "out": 8, "anchor": "-", "items": [["img/tiktok.svg", "TikTok", 5.2]]},
            {"type": "stats", "id": "s", "in": 9, "out": 12, "anchor": "-", "items": [{"value": 10000, "label": "emails", "at": 9.2}]}]})
        out = os.path.join(d, "SB.md")
        r = run("storyboard-md.py", "--title", "T", "--project", "%s:t:T" % d, "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        md = read(out)
        self.assertIn("I agree", md); self.assertIn("TikTok", md); self.assertIn("10000 emails", md)

    def test_chapter_tags_listed_in_time_order(self):
        d = scratch(self)
        write(os.path.join(d, "storyboard.json"), {"id": "t", "duration": 30.0, "tags": [{"label": "Recap", "in": 20.0, "out": 24.0}],
              "beats": [{"type": "chip", "id": "c", "text": "Early", "in": 2, "out": 4, "anchor": "-"},
                        {"type": "chip", "id": "e", "text": "Late", "in": 25, "out": 27, "anchor": "-"}]})
        out = os.path.join(d, "SB.md")
        r = run("storyboard-md.py", "--title", "T", "--project", "%s:t:T" % d, "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        md = read(out)
        self.assertLess(md.index("Early"), md.index("chapter tag | Recap"))
        self.assertLess(md.index("Recap"), md.index("Late"))


class TailAudit(unittest.TestCase):
    def wav(self, path, parts, sr=16000):
        import random
        rnd = random.Random(3)
        with wave.open(path, "w") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            fr = bytearray()
            for kind, dur, amp in parts:
                for i in range(int(dur * sr)):
                    if kind == "tone": v = amp * (1 if (i // 40) % 2 else -1)        # a voiced, low-pitched vowel
                    elif kind == "hiss": v = amp * rnd.uniform(-1, 1)               # the final "s"
                    else: v = rnd.uniform(-3, 3)                                    # room tone
                    fr += struct.pack("<h", int(v))
            w.writeframes(bytes(fr))

    def test_restores_a_clipped_final_s_but_not_a_breath(self):
        d = scratch(self)
        p = os.path.join(d, "a.wav")
        # word 1: vowel 0.3-1.0, 30 ms stop, the "s" 1.03-1.20, silence; word 2 at 2.0-2.6 then a soft breath 2.63-2.9
        self.wav(p, [("room", 0.3, 0), ("tone", 0.7, 3000), ("room", 0.03, 0), ("hiss", 0.17, 1500), ("room", 0.8, 0),
                     ("tone", 0.6, 3000), ("room", 0.03, 0), ("hiss", 0.27, 60), ("room", 1.0, 0)])
        cl = write(os.path.join(d, "cut-list.json"), {"kept": [{"start": 0.25, "end": 1.0}, {"start": 1.95, "end": 2.6}]})
        r = run("tail-audit.py", "--audio", p, "--cut-list", cl, "--fix")
        self.assertEqual(r.returncode, 0, r.stderr)
        k = load(cl)["kept"]
        self.assertGreater(k[0]["end"], 1.19); self.assertLess(k[0]["end"], 1.30)   # the "s" is back
        self.assertAlmostEqual(k[1]["end"], 2.6, places=3)                            # the breath stays cut


class WordAudit(unittest.TestCase):
    def test_flags_a_word_lost_at_a_join(self):
        d = scratch(self)
        raw = write(os.path.join(d, "raw.json"), words(("we", 0.0, 0.2), ("need", 0.2, 0.5), ("leads", 0.5, 0.9), ("every", 1.5, 1.8),
                                                      ("day", 1.8, 2.1), ("now", 3.0, 3.3), ("go", 3.3, 3.6)))
        cl = write(os.path.join(d, "cut-list.json"), {"kept": [{"start": 0.0, "end": 2.2}, {"start": 3.0, "end": 3.7}]})
        # the finished file lost "day" at the join and the transcriber heard "lead" for "leads"
        fin = write(os.path.join(d, "final.json"), words(("we", 0.0, 0.2), ("need", 0.2, 0.5), ("lead", 0.5, 0.8), ("every", 1.5, 1.8),
                                                        ("now", 2.2, 2.5), ("go", 2.5, 2.8)))
        r = run("word-audit.py", "--raw", raw, "--cut-list", cl, "--final", fin)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("1 mismatches at a join", r.stdout)
        self.assertIn("'day'", r.stdout); self.assertIn("'leads'", r.stdout)


@needs_ffmpeg
class WordAuditEarly(unittest.TestCase):
    def test_flat_audio_is_the_kept_audio(self):
        d = scratch(self)
        src = os.path.join(d, "audio-raw.wav")
        ffmpeg("-f", "lavfi", "-i", "sine=frequency=300:sample_rate=16000:duration=10", "-ac", "1", src)
        cl = write(os.path.join(d, "cut-list.json"), {"kept": [{"start": 0.5, "end": 2.0}, {"start": 3.0, "end": 3.75}, {"start": 6.0, "end": 9.0}]})
        raw = write(os.path.join(d, "raw.json"), words(("a", 0.6, 0.8)))
        r = run("word-audit.py", "--raw", raw, "--cut-list", cl, "--audio", src, "--final", os.path.join(d, "flat.json"), "--flat-only")
        self.assertEqual(r.returncode, 0, r.stderr)
        import subprocess
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    os.path.join(d, "flat-audio.wav")], capture_output=True, text=True).stdout)
        self.assertAlmostEqual(dur, 1.5 + 0.75 + 3.0, delta=0.02)


class WindowPatchMediaStart(unittest.TestCase):
    def test_media_start_lands_inside_the_first_frame(self):
        # "%.3f" of 23.0333 is 23.033: before frame 691, so the browser showed 690 and every patch ran one frame late
        d = scratch(self)
        os.makedirs(os.path.join(d, "public"))
        write(os.path.join(d, "public", "index.html"),
              '<div id="stage" data-start="0" data-duration="60.000">\n'
              '<video id="bg-video" src="input-video.mp4" data-start="0" data-duration="60.000"></video>\n'
              '<div class="card-host" id="host-a" data-start="23.500" data-duration="2.000"></div>\n'
              '<script>const tl = gsap.timeline({paused: true}); window.__timelines["main"] = tl;</script>\n</div>\n')
        r = run("window-patch.py", "--public", os.path.join(d, "public"), "--t0", "23.03", "--t1", "25.0", "--out", os.path.join(d, "w"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        import re
        html = open(os.path.join(d, "w", "public", "index.html")).read()
        ms = float(re.search(r'id="bg-video"[^>]*data-media-start="([0-9.]+)"', html).group(1))
        self.assertGreater(ms, 691 / 30); self.assertLess(ms, 691.5 / 30)
