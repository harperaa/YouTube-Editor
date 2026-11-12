"""The video opens on 0.5 s of room tone: dead-air --opens-video flags a lead-in shorter than 0.45 s."""
import json, os, unittest, wave
import numpy as np
from .helpers import run, scratch, write


def make(d, lead):
    sr = 16000
    x = np.random.RandomState(1).normal(0, 8, int(sr * (lead + 1.5)))           # room tone
    s0 = int(sr * lead); x[s0:s0 + sr] += 3000 * np.sin(np.arange(sr) * 2 * np.pi * 220 / sr)   # one second of "speech"
    with wave.open(os.path.join(d, "audio.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(x.astype(np.int16).tobytes())
    write(os.path.join(d, "cut-map.json"), {"cuts": [], "flat_duration": lead + 1.5})
    write(os.path.join(d, "transcript.json"), [{"text": "Hello.", "start": lead, "end": lead + 1.0}])


class OpensVideoHead(unittest.TestCase):
    def test_short_lead_in_is_flagged(self):
        d = scratch(self); make(d, 0.08)
        r = run("dead-air.py", d, "--opens-video")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("HEAD SHORT", r.stdout)

    def test_half_second_lead_in_is_kept(self):
        d = scratch(self); make(d, 0.55)
        r = run("dead-air.py", d, "--opens-video", "--plan")
        self.assertNotIn("HEAD SHORT", r.stdout)
        self.assertNotIn("head 0.55 s: drop", r.stdout)     # 0.55 s is inside the 0.5 s target (+0.15): the head stays

    def test_section_default_unchanged(self):
        d = scratch(self); make(d, 0.08)
        r = run("dead-air.py", d)
        self.assertNotIn("HEAD SHORT", r.stdout)


if __name__ == "__main__":
    unittest.main()
