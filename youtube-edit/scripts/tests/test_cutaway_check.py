"""cutaway-check.py: a clip that covers the frame passes; one squashed into a strip (most of the frame still the base)
fails. The microwave cutaway once rendered as a strip at the bottom of the face frame."""
import os, unittest
from .helpers import ffmpeg, needs_ffmpeg, run, scratch, write

SB = {"id": "t", "duration": 6.0, "beats": [{"type": "clip", "id": "mw-clip", "src": "broll/x.mp4", "in": 2.0, "out": 4.0, "anchor": "-"}]}


@needs_ffmpeg
class CutawayCheck(unittest.TestCase):
    def setUp(self):
        self.d = scratch(self)
        self.base = os.path.join(self.d, "base.mp4")
        ffmpeg("-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=6", "-c:v", "libx264", "-crf", "0", "-pix_fmt", "yuv444p", self.base)
        self.sb = write(os.path.join(self.d, "storyboard.json"), SB)

    def render(self, name, overlay):
        out = os.path.join(self.d, name)
        ffmpeg("-i", self.base, "-f", "lavfi", "-i", "color=c=red:s=640x360:r=30:d=6", "-filter_complex", overlay,
               "-c:v", "libx264", "-crf", "0", "-pix_fmt", "yuv444p", out)
        return out

    def test_full_cover_passes(self):
        v = self.render("full.mp4", "[0][1]overlay=enable='between(t,2,4)'")
        r = run("cutaway-check.py", "--storyboard", self.sb, "--video", v, "--base", self.base)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_squashed_strip_fails(self):
        v = self.render("strip.mp4", "[1]scale=640:50[s];[0][s]overlay=0:290:enable='between(t,2,4)'")
        r = run("cutaway-check.py", "--storyboard", self.sb, "--video", v, "--base", self.base)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("FAIL", r.stdout)


if __name__ == "__main__":
    unittest.main()
