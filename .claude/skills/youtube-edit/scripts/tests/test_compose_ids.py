"""compose.py refuses two beats with one id: the id is the DOM id, the GSAP selector and the overlay window name, so a
"microwave" line and a "microwave" clip rendered the cutaway into the line's box as a squashed strip, twice."""
import os, unittest
from .helpers import run, scratch, write


class ComposeIds(unittest.TestCase):
    def build(self, beats):
        d = scratch(self)
        sp = write(os.path.join(d, "storyboard.json"), {"id": "t", "duration": 20.0, "beats": beats})
        return run("compose.py", "--spec", sp, "--out", os.path.join(d, "public"))

    def test_duplicate_id_fails(self):
        r = self.build([{"type": "line", "id": "mw", "text": "the microwave video", "in": 2.0, "out": 5.0, "anchor": "-"},
                        {"type": "clip", "id": "mw", "src": "broll/x.mp4", "in": 6.0, "out": 8.0, "anchor": "-"}])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("duplicate beat id", r.stdout + r.stderr)
        self.assertIn("mw", r.stdout + r.stderr)

    def test_unique_ids_build(self):
        r = self.build([{"type": "line", "id": "mw-line", "text": "the microwave video", "in": 2.0, "out": 5.0, "anchor": "-"},
                        {"type": "line", "id": "mw-two", "text": "again", "in": 6.0, "out": 8.0, "anchor": "-"}])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
