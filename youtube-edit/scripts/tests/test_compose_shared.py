"""compose.py --shared staging: img subfolders are kept, a folder inside sfx/ does not crash the build, and an asset
edited after a build is copied again (a resized logo once stayed stale and rendered 50 px wide)."""
import os, time, unittest
from .helpers import read, run, scratch, write

SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'


class ComposeShared(unittest.TestCase):
    def test_subfolders_dirs_and_restage(self):
        d = scratch(self)
        shared = os.path.join(d, "shared")
        write(os.path.join(shared, "img", "logos", "brand.svg"), SVG % (50, 50))
        write(os.path.join(shared, "img", "site.png"), "png")
        write(os.path.join(shared, "sfx", "pop.mp3"), "mp3")
        os.makedirs(os.path.join(shared, "sfx", "raw"))           # original downloads parked inside sfx/
        spec = write(os.path.join(d, "storyboard.json"), {"id": "t", "duration": 10.0, "beats": [
            {"type": "logo", "id": "lg", "src": "img/logos/brand.svg", "pos": "tl", "in": 1.0, "out": 3.0, "pop": 1.1, "anchor": "-"}]})
        out = os.path.join(d, "public")
        r = run("compose.py", "--spec", spec, "--out", out, "--shared", shared)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.exists(os.path.join(out, "img", "logos", "brand.svg")))
        self.assertTrue(os.path.exists(os.path.join(out, "img", "site.png")))
        self.assertTrue(os.path.exists(os.path.join(out, "sfx", "pop.mp3")))
        self.assertFalse(os.path.exists(os.path.join(out, "sfx", "raw")))
        time.sleep(1.1)                                            # mtime resolution
        write(os.path.join(shared, "img", "logos", "brand.svg"), SVG % (512, 512))
        r = run("compose.py", "--spec", spec, "--out", out, "--shared", shared)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('width="512"', read(os.path.join(out, "img", "logos", "brand.svg")))


if __name__ == "__main__":
    unittest.main()


class ComposeTags(unittest.TestCase):
    def test_plain_chapter_tags_without_pips(self):
        d = scratch(self)
        spec = write(os.path.join(d, "storyboard.json"), {"id": "t", "duration": 20.0, "beats": [],
            "tags": [{"label": "Chapter one", "in": 1.0, "out": 5.0, "pos": "tr", "anchor": "-"},
                     {"label": "Part 2", "n": 2, "of": 4, "in": 8.0, "out": 12.0, "pos": "tr", "anchor": "-"}]})
        out = os.path.join(d, "public")
        r = run("compose.py", "--spec", spec, "--out", out)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        page = read(os.path.join(out, "index.html"))
        self.assertIn("Chapter one", page); self.assertIn("Part 2", page)
        self.assertEqual(page.count('<span class="pip'), 1 + 4)
