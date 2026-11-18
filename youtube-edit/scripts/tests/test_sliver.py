"""sliver.py: the RMS threshold is a flag, --fix never writes an empty, overlapping or inverted cut list.
Audio is synthesised with numpy + wave (no ffmpeg): a 200 Hz tone whose 10 ms frame RMS follows a level profile."""
import os, unittest, wave
import numpy as np
from .helpers import load, read, run, scratch, write

SR = 16000


def wav(path, runs, seconds):
    """runs: (start_s, end_s, frame RMS) spans of a 200 Hz tone; silence elsewhere."""
    lv = np.zeros(int(seconds * SR))
    for a, b, rms in runs:
        lv[int(round(a * SR)):int(round(b * SR))] = rms
    x = lv * np.sqrt(2) * np.sin(2 * np.pi * 200 * np.arange(len(lv)) / SR)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(x.astype(np.int16).tobytes())
    return path


class Sliver(unittest.TestCase):
    def setUp(self):
        self.d = scratch(self)

    def case(self, runs, seconds, kept):
        audio = wav(os.path.join(self.d, "audio.wav"), runs, seconds)
        cl = write(os.path.join(self.d, "cut-list.json"), {"source_duration": seconds, "kept": [{"start": a, "end": b} for a, b in kept]})
        return audio, cl

    def kept(self, cl):
        return [(s["start"], s["end"]) for s in load(cl)["kept"]]

    # low-gain speech: two bursts peaking at 350 (frame RMS ~247), under the old hard-coded 300
    QUIET = [(1.0, 2.0, 350 / np.sqrt(2)), (3.0, 4.5, 350 / np.sqrt(2))]

    def test_threshold_flag_keeps_quiet_speech(self):
        audio, cl = self.case(self.QUIET, 5.0, [(0.85, 2.2), (2.85, 4.7)])
        r = run("sliver.py", "--cut-list", cl, "--audio", audio, "--threshold", "150", "--fix")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.kept(cl)), 2, r.stdout)
        self.assertNotIn("dropped", r.stdout)

    def test_refuses_to_write_an_empty_cut(self):
        audio, cl = self.case(self.QUIET, 5.0, [(0.85, 2.2), (2.85, 4.7)])
        before = read(cl)
        r = run("sliver.py", "--cut-list", cl, "--audio", audio, "--fix")
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn("--threshold", r.stderr)
        self.assertEqual(read(cl), before)

    def test_widening_stops_at_the_neighbour(self):
        # seg 0's tail is widened into the 2.0-2.07 room that seg 1 already keeps
        audio, cl = self.case([(0.5, 1.985, 2000), (2.07, 3.5, 2000)], 4.0, [(0.5, 1.99), (2.0, 3.5)])
        r = run("sliver.py", "--cut-list", cl, "--audio", audio, "--fix")
        self.assertEqual(r.returncode, 0, r.stderr)
        k = self.kept(cl)
        self.assertEqual(len(k), 2, r.stdout)
        for (a0, b0), (a1, b1) in zip(k, k[1:]):
            self.assertLessEqual(b0, a1, "segments overlap: %s" % k)
        self.assertEqual(k, [(0.41, 2.0), (2.0, 3.59)])
        self.assertIn("widening stopped at seg 1's head", r.stdout)

    def test_no_inverted_segment(self):
        # head rule moves start into the 0.20-0.42 quiet run; tail rule sees the same run clipped to its 0.35 s window
        # (0.24-0.42) and moves end to 0.34, so start >= end
        runs = [(0.0, 0.20, 600), (0.20, 0.42, 30), (0.42, 0.48, 2000), (0.48, 0.70, 600), (0.80, 0.90, 2000)]
        audio, cl = self.case(runs, 1.2, [(0.15, 0.59), (0.75, 0.95)])
        r = run("sliver.py", "--cut-list", cl, "--audio", audio, "--fix")
        self.assertEqual(r.returncode, 0, r.stderr)
        for a, b in self.kept(cl):
            self.assertLess(a, b, "inverted segment written: %s\n%s" % (self.kept(cl), r.stdout))
        self.assertEqual(self.kept(cl), [(0.75, 0.95)])
        self.assertIn("seg 0 0.150-0.590: the fixes leave start >= end", r.stdout)
        self.assertTrue(any("start >= end" in h for h in load(cl)["hand_fixes"]))

    def test_breath_only_segment_dropped_between_loud_neighbours(self):
        runs = [(1.0, 2.0, 2000), (2.5, 2.8, 150), (3.0, 4.0, 2000)]          # a breath at 150 RMS between two words
        audio, cl = self.case(runs, 5.0, [(0.9, 2.1), (2.4, 2.9), (2.95, 4.1)])
        r = run("sliver.py", "--cut-list", cl, "--audio", audio, "--fix")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.kept(cl), [(0.9, 2.1), (2.95, 4.1)])
        self.assertIn("seg 1 2.400-2.900: no frame over 300 RMS", r.stdout)

    def test_room_tone_passes_through(self):
        runs = [(1.0, 2.0, 2000), (2.5, 2.8, 150), (3.0, 4.0, 2000)]
        audio, cl = self.case(runs, 5.0, [(0.9, 2.1), (2.4, 2.9), (2.95, 4.1)])
        d = load(cl); d["kept"][1]["room_tone"] = True; write(cl, d)
        before = read(cl)
        r = run("sliver.py", "--cut-list", cl, "--audio", audio, "--fix")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("0 changes", r.stdout)
        self.assertEqual(read(cl), before)

    def test_clean_cut_is_left_alone(self):
        audio, cl = self.case([(1.0, 2.0, 2000), (3.0, 4.0, 2000)], 5.0, [(0.9, 2.1), (2.9, 4.1)])
        before = read(cl)
        r = run("sliver.py", "--cut-list", cl, "--audio", audio, "--fix")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("0 changes", r.stdout)
        self.assertEqual(read(cl), before)


if __name__ == "__main__":
    unittest.main()
