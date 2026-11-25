"""compose.py, the concept illustration (formats/concept.py): every element kind builds, arrives on its own time, and the
seek-safety rules hold (no CSS transform on a GSAP-moved element, typing and counting from one proxy tween each)."""
import os, re, unittest
from .helpers import run, scratch, write, read

CONCEPT = {"type": "concept", "id": "cn", "in": 2.0, "out": 12.0, "anchor": "-", "title": "ONE VIDEO", "title_at": 2.1,
           "els": [{"k": "box", "id": "oven", "x": 250, "y": 250, "w": 900, "h": 560, "at": 2.2, "label": "VSL", "fill": "cyan"},
                   {"k": "line", "id": "seam", "x1": 900, "y1": 270, "x2": 900, "y2": 790, "at": 2.6},
                   {"k": "icon", "id": "icp", "name": "user", "x": 480, "y": 400, "size": 200, "color": "cyan", "at": 3.0, "label": "YOUR ICP"},
                   {"k": "wire", "id": "w", "pts": [[1150, 530], [1330, 530]], "at": 3.5, "run": 4.0},
                   {"k": "meter", "id": "m", "x": 1340, "y": 240, "w": 100, "h": 600, "at": 3.6,
                    "steps": [[0.2, 4.0, "cyan", "COLD"], [0.6, 5.0, "amber", "LUKEWARM"], [1.0, 6.0, "magenta", "HOT"]]},
                   {"k": "glow", "id": "g", "x": 300, "y": 310, "w": 560, "h": 440, "steps": [[0.2, 4.0, "cyan"], [0.5, 6.0, "magenta"]]},
                   {"k": "text", "id": "t", "x": 960, "y": 900, "text": "Every element on its word", "at": 6.5},
                   {"k": "stamp", "id": "s", "x": 700, "y": 905, "text": "HOT", "color": "magenta", "at": 7.0},
                   {"k": "check", "id": "ok", "x": 1500, "y": 900, "at": 7.5},
                   {"k": "cross", "id": "no", "x": 1650, "y": 900, "at": 7.8},
                   {"k": "count", "id": "c", "x": 1600, "y": 200, "to": 10, "suffix": " min", "at": 8.0},
                   {"k": "term", "id": "tm", "x": 200, "y": 820, "w": 800, "h": 160, "lines": [["$ npm install", 8.5]]},
                   {"k": "scale", "id": "sc", "x": 960, "y": 400, "left": "RISK", "right": "REWARD", "at": 9.0, "tilts": [[-12, 9.6], [-20, 10.4]]},
                   {"k": "icon", "id": "hero", "name": "user", "x": 100, "y": 100, "at": 9.2, "moves": [[300, 0, 9.8], [600, 0, 10.6]], "dim": 11.5}]}


class ComposeConcept(unittest.TestCase):
    def build(self, beats):
        d = scratch(self)
        sp = write(os.path.join(d, "storyboard.json"), {"id": "t", "duration": 20.0, "beats": beats})
        r = run("compose.py", "--spec", sp, "--out", os.path.join(d, "public"))
        return r, (read(os.path.join(d, "public", "index.html")) if r.returncode == 0 else "")

    def test_every_kind_builds_on_its_time(self):
        r, page = self.build([CONCEPT])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(".cn-panel", page)                                   # the CSS goes in once a concept is present
        for needle in ('id="cn-oven"', 'id="cn-oven-l"', 'id="cn-icp"', 'id="cn-w-r"', 'id="cn-m-f"', 'id="cn-g"',
                       'id="cn-s"', 'id="cn-sc-beam"', 'id="cn-hero-mv"', 'id="cn-ok"', 'id="cn-no"', 'id="cn-c"', 'id="cn-tm-ln0"', 'id="cn-title"'):
            self.assertIn(needle, page)
        self.assertRegex(page, r"tl\.fromTo\('#cn-oven', \{ strokeDashoffset: 1 \}.*2\.200\)")
        self.assertRegex(page, r"tl\.to\('#cn-m-f', \{ scaleY: 1\.000.*6\.000\)")

    def test_seek_safety(self):
        r, page = self.build([CONCEPT])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotRegex(page, r'id="cn-m-f"[^>]*transform:scale')     # GSAP owns the meter's transform
        self.assertIn("s.slice(0, Math.floor(p.n))", page)                 # typing from one proxy tween
        self.assertIn("Math.round(p.n)", page)                             # counting from one proxy tween

    def test_unknown_kind_fails(self):
        bad = dict(CONCEPT, els=[{"k": "spiral", "at": 2.5}])
        r, _ = self.build([bad])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("concept element kind", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
