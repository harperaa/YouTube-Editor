"""edge-audit --fix never moves an edge over a dropped word or into a neighbouring segment.

Without --keeps (the documented SKILL.md invocation) every transcript word counts as kept, so a word that starts up to
0.35 s before a segment, the last word of a dropped take, used to become the head fix's anchor and was pulled back in."""
import os, unittest, wave
import numpy as np
from .helpers import run, scratch, write, load


def make(d, tones, words, kept, dur=4.0):
    sr = 16000
    x = np.random.RandomState(1).normal(0, 8, int(sr * dur))                    # room tone
    for t0, t1 in tones:                                                        # each tone is one "word"
        s0, s1 = int(sr * t0), int(sr * t1)
        x[s0:s1] += 3000 * np.sin(np.arange(s1 - s0) * 2 * np.pi * 220 / sr)
    with wave.open(os.path.join(d, "audio.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(x.astype(np.int16).tobytes())
    write(os.path.join(d, "transcript.json"), [{"text": "w%d" % i, "start": s, "end": e} for i, (s, e) in enumerate(words)])
    write(os.path.join(d, "cut-list.json"), {"kept": [{"start": s, "end": e} for s, e in kept]})


def fix(test, d):
    r = run("edge-audit.py", "--audio", os.path.join(d, "audio.wav"), "--cut-list", os.path.join(d, "cut-list.json"),
            "--transcript", os.path.join(d, "transcript.json"), "--fix")
    test.assertEqual(r.returncode, 0, r.stdout + r.stderr)
    return load(os.path.join(d, "cut-list.json"))["kept"]


class EdgeAuditFix(unittest.TestCase):
    def test_head_fix_does_not_bring_back_dropped_word(self):
        # kept word 0.5-1.2, dropped word 1.75-2.05, kept word 2.15-3.5; segment 1 starts inside the dropped word
        d = scratch(self)
        tones = [(0.5, 1.2), (1.75, 2.05), (2.15, 3.5)]
        make(d, tones, tones, [(0.4, 1.35), (2.0, 3.6)])
        K = fix(self, d)
        self.assertEqual(len(K), 2, K)
        self.assertGreaterEqual(K[1]["start"], 2.0, "head moved back over the dropped 1.75-2.05 word: %s" % K)
        self.assertLessEqual(K[1]["start"], 2.15, "head cut into the kept 2.15 word: %s" % K)

    def test_head_fix_never_overlaps_previous_segment(self):
        # a word straddles the join: it starts in segment 0, segment 1 starts while it still plays
        d = scratch(self)
        tones = [(0.3, 1.25), (1.4, 2.5)]
        make(d, tones, [(0.3, 0.9), (1.0, 1.25), (1.4, 2.5)], [(0.2, 1.05), (1.1, 2.6)])
        K = fix(self, d)
        for a, b in zip(K, K[1:]):
            self.assertGreaterEqual(b["start"], a["end"], "segments overlap (audio played twice): %s" % K)

    def test_tail_fix_never_passes_original_end_or_next_segment(self):
        # segment 0 ends mid-word 0.95-1.3, a word whose start + 0.15 lies past the segment's end
        d = scratch(self)
        tones = [(0.5, 1.3), (1.6, 2.5)]
        make(d, tones, [(0.5, 0.9), (0.95, 1.3), (1.6, 2.5)], [(0.4, 1.0), (1.05, 2.6)])
        K = fix(self, d)
        self.assertLessEqual(K[0]["end"], 1.0, "tail moved past the segment's original end: %s" % K)
        for a, b in zip(K, K[1:]):
            self.assertGreaterEqual(b["start"], a["end"], "segments overlap (audio played twice): %s" % K)


if __name__ == "__main__":
    unittest.main()
