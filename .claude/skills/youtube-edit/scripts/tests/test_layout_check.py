"""List cards fit their longest item, and layout-check samples every beat where it is fully built.

The "Daily Leads" quick-win card was given width 440 and "3 valuable comments" ran 144 px out of the glass; the full
check passed because its 9 evenly spaced samples never landed on the card. Browser half: YT_EDIT_BROWSER_TESTS=1."""
import json, os, re, shutil, unittest
from .helpers import read, run, scratch, write

LIST = {"type": "list", "id": "qw", "eyebrow": "TODAY", "marker": "check", "pos": "tl", "width": 440, "size": 50,
        "in": 2.0, "out": 9.0, "anchor": "-",
        "items": [["Pick one platform", 2.3, "-"], ["3 valuable comments", 4.0, "-"], ["One short post", 6.0, "-"]]}


class ListFitsItsItems(unittest.TestCase):
    def compose(self, d):
        spec = write(os.path.join(d, "storyboard.json"), {"id": "t", "duration": 10.0, "beats": [LIST],
                                                         "tags": [{"label": "Quick win", "in": 1.0, "out": 5.0, "pos": "tr", "anchor": "-"}]})
        out = os.path.join(d, "public")
        r = run("compose.py", "--spec", spec, "--out", out)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return spec, out, read(os.path.join(out, "index.html"))

    def test_width_is_a_minimum_and_items_are_in_layout(self):
        d = scratch(self)
        _, _, html = self.compose(d)
        self.assertIn("min-width:440px", html)
        self.assertNotRegex(html, r'id="qw-glass" style="[^"]*(?<!min-)width:440px')
        self.assertNotRegex(html, r"\.list \.item \{[^}]*display:none")          # hidden items must still size the card
        self.assertIn("tl.set('#qw-i1', { visibility: 'visible', height: 'auto', marginBottom: 22 }, 4.000);", html)
        self.assertNotIn("tl.set('#qw-i1', { display: 'flex' }", html)

    def test_plan_samples_each_item_mid_end_and_tag(self):
        d = scratch(self)
        spec, out, _ = self.compose(d)
        r = run("layout-check.py", "--project", out, "--storyboard", spec, "--plan-only")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        times = [float(x) for x in r.stdout.split("\n")[1].split()]
        for t in (2.8, 4.5, 6.5, 5.5, 8.55, 2.0):        # items + 0.5, mid, out - 0.45, tag in + 1.0
            self.assertIn(t, times)

    def test_reports_overflow_by_beat_and_ignores_media_fit(self):
        d = scratch(self)
        spec, out, _ = self.compose(d)
        bad = write(os.path.join(d, "bad.json"), {"layout": {"findings": [
            {"code": "text_box_overflow", "severity": "error", "time": 4.5, "selector": "#qw-i1 > div:nth-of-type(2)",
             "containerSelector": "#qw-glass", "text": "3 valuable comments", "overflow": {"right": 143.9}}]},
            "craft": {"findings": [{"code": "clip_media_fit", "severity": "warning", "selector": "audio"}]}})
        r = run("layout-check.py", "--project", out, "--storyboard", spec, "--from-json", bad)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("1 finding(s) in 1 beat(s): qw", r.stdout)
        self.assertIn("144 px", r.stdout)
        low = write(os.path.join(d, "low.json"), {"layout": {"findings": []}, "contrast": {"findings": [
            {"code": "contrast_aa_failure", "severity": "error", "time": 4.5, "selector": "#qw-i1 > span", "text": "SBOM:", "ratio": 1.1}]}})
        r = run("layout-check.py", "--project", out, "--storyboard", spec, "--from-json", low)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("contrast_aa_failure", r.stdout)
        ok = write(os.path.join(d, "ok.json"), {"layout": {"findings": []}, "craft": {"findings": [
            {"code": "clip_media_fit", "severity": "warning", "selector": "audio"}]}})
        r = run("layout-check.py", "--project", out, "--storyboard", spec, "--from-json", ok)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_stacked_stat_tile_hidden_until_its_number(self):
        d = scratch(self)
        spec = write(os.path.join(d, "storyboard.json"), {"id": "t", "duration": 10.0, "beats": [
            {"type": "stats", "id": "st", "layout": "stack", "pos": "tr", "in": 1.0, "out": 8.0, "anchor": "-",
             "items": [{"value": 8000, "label": "followers", "at": 1.3}, {"value": 10000, "label": "emails", "at": 5.0}]}]})
        out = os.path.join(d, "public")
        r = run("compose.py", "--spec", spec, "--out", out)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        html = read(os.path.join(out, "index.html"))
        self.assertRegex(html, r"\.st-stack \.st-tile \{[^}]*visibility:hidden")
        self.assertIn("tl.set('#st-t1', { visibility: 'visible' }, 5.000);", html)

    @unittest.skipUnless(os.environ.get("YT_EDIT_BROWSER_TESTS") and shutil.which("npx"), "browser test: YT_EDIT_BROWSER_TESTS=1")
    def test_composed_list_passes_in_the_browser(self):
        d = scratch(self)
        spec, out, _ = self.compose(d)
        r = run("layout-check.py", "--project", out, "--storyboard", spec)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()


class ChipOnDarkGlass(unittest.TestCase):
    def test_chip_goes_near_solid_on_a_dark_glass_storyboard(self):
        # magenta on a .45 chip over a white lesson page measured 1.1:1 (contrast error); dark-glass storyboards get .88
        for glass, want in (("rgba(17,17,17,0.55)", "rgba(17,17,17,0.88)"), (None, "rgba(17,17,17,0.45)")):
            d = scratch(self)
            sb = {"id": "t", "duration": 6.0, "beats": [{"type": "chip", "id": "c", "text": "SBOM: bill", "em": [0], "in": 1, "out": 4, "anchor": "-"}]}
            if glass: sb["glass_bg"] = glass
            spec = write(os.path.join(d, "storyboard.json"), sb)
            r = run("compose.py", "--spec", spec, "--out", os.path.join(d, "public"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("backgroundColor: '%s', y: 0" % want, read(os.path.join(d, "public", "index.html")))


class EquationOnDarkGlass(unittest.TestCase):
    def test_equation_strip_goes_near_solid_on_dark_glass(self):
        # "No refusals = No protection" over a white lesson page: the .6 '=' and the magenta result failed contrast on .55 glass
        for glass, want in (("rgba(17,17,17,0.55)", "0.42, 'rgba(17,17,17,0.88)');"), (None, "0.42, '');")):
            d = scratch(self)
            sb = {"id": "t", "duration": 6.0, "beats": [{"type": "equation", "id": "eq", "pos": "bottom", "in": 1, "out": 4, "anchor": "-",
                                                         "terms": [["No refusals", 1.2], ["=", 1.8], ["No protection", 2.0, "pay"]]}]}
            if glass: sb["glass_bg"] = glass
            spec = write(os.path.join(d, "storyboard.json"), sb)
            r = run("compose.py", "--spec", spec, "--out", os.path.join(d, "public"))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("glassIn('#eq-glass', 1.000, { y: 20 }, " + want, read(os.path.join(d, "public", "index.html")))
