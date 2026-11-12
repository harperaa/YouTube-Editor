"""finish-master.py: chapters from the storyboard's tags with the titles from chapters.txt, both masters at -14 LUFS with
true peak under -1 dB, chapters embedded, and the chapter rules enforced (the finish once took a dozen hand-typed commands)."""
import os, subprocess, unittest
from .helpers import ffmpeg, read, run, scratch, write


@unittest.skipUnless(subprocess.run(["which", "ffmpeg"], capture_output=True).returncode == 0, "needs ffmpeg")
class FinishMaster(unittest.TestCase):
    def media(self, d):
        src = os.path.join(d, "comp.mp4")
        # 40 s: a quiet "voice" (tone bursts) on a small picture
        ffmpeg("-f", "lavfi", "-i", "color=c=gray:size=320x180:rate=30:duration=40", "-f", "lavfi",
               "-i", "sine=frequency=220:sample_rate=48000:duration=40,volume='0.05*gt(mod(t,2),0.6)':eval=frame",
               "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", src)
        bed = os.path.join(d, "bed.mp3")
        ffmpeg("-f", "lavfi", "-i", "sine=frequency=660:sample_rate=48000:duration=7", bed)
        return src, bed

    def test_both_masters_and_chapters_from_tags(self):
        d = scratch(self)
        src, bed = self.media(d)
        sb = write(os.path.join(d, "storyboard.json"), {"tags": [{"label": "Part one", "in": 12.6, "out": 16.0},
                                                                 {"label": "Recap", "in": 27.4, "out": 31.0}]})
        ch = write(os.path.join(d, "chapters.txt"), "0:00 Why it matters\n0:11 The first part, in full\n0:26 Recap\n")
        r = run("finish-master.py", "--in", src, "--out-dir", d, "--name", "t", "--storyboard", sb, "--chapters", ch,
                "--title", "T", "--music", bed, "--hook-end", "5")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(read(os.path.join(d, "t-chapters.txt")), "0:00 Why it matters\n0:12 The first part, in full\n0:26 Recap\n")
        self.assertEqual(r.stdout.count("OK   t-"), 2, r.stdout)
        self.assertIn("3 chapters", r.stdout)
        self.assertTrue(os.path.exists(os.path.join(d, "t-4k.mp4")) and os.path.exists(os.path.join(d, "t-nomusic-4k.mp4")))
        # the bed is set by its measured level under the voice (the ducking once buried a -21.5 dB bed ~30 dB under it)
        self.assertRegex(r.stdout, r"OK   bed hook 1[3-5]\.\d dB under the voice in the master \(target 14\.2")
        self.assertRegex(r.stdout, r"OK   bed body 1[6-8]\.\d dB under the voice in the master \(target 17\.2")

    def test_bed_level_is_independently_audible(self):
        # decode the master and the no-music master, subtract, and check the bed really sits ~17 dB under the voice
        import numpy as np
        d = scratch(self)
        src, bed = self.media(d)
        r = run("finish-master.py", "--in", src, "--out-dir", d, "--name", "t", "--music", bed, "--hook-end", "5")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        pcm = lambda p: np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                                                     capture_output=True).stdout, dtype=np.int16).astype(float)
        m, v = pcm(os.path.join(d, "t-4k.mp4")), pcm(os.path.join(d, "t-nomusic-4k.mp4"))
        n = min(len(m), len(v)); m, v = m[:n], v[:n]
        gm = np.dot(m, v) / np.dot(v, v)          # each master has its own loudnorm gain: match the voice first
        v = gm * v; b = m - v
        w = slice(16000 * 8, 16000 * 34)
        fv = (v[w].reshape(-1, 1600) ** 2).mean(axis=1); fb = (b[w].reshape(-1, 1600) ** 2).mean(axis=1)
        sp = fv > fv.max() * 1e-3
        under = 10 * np.log10(fv[sp].mean() / fb[sp].mean())
        self.assertLess(abs(under - 17.2), 2.0, "bed %.1f dB under the voice" % under)

    def test_rejects_a_short_chapter(self):
        d = scratch(self)
        src, _ = self.media(d)
        ch = write(os.path.join(d, "chapters.txt"), "0:00 A\n0:05 B\n0:20 C\n")
        r = run("finish-master.py", "--in", src, "--out-dir", d, "--name", "t", "--chapters", ch)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("10 s minimum", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
