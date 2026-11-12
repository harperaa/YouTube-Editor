# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Claude Code skill kit that edits YouTube videos end to end: raw camera clip in, cut and animated 4K MP4 out, rendered
locally with HyperFrames (Chrome + FFmpeg). There is no app to build or run; the deliverable is the skill itself.

- `youtube-edit/` is the distributable kit copy. `.claude/skills/youtube-edit/` is the installed copy that Claude
  actually loads. **Edit the installed copy and sync the kit copy** (or vice versa) so they do not drift:
  `rsync -a --delete .claude/skills/youtube-edit/ youtube-edit/`.
- `youtube-edit/SKILL.md` (~1100 lines) is the rulebook: setup table, routes, the format library (numbered formats
  such as 2 lower line, 4a logo card, 9 progress tag, 27 pipeline), long-form doctrine, camera, sound, Tella route,
  assembly, render checks, traps. Every rule came from a real note on a real video. When the user says
  **"save this to the skill"**, write the note as one plain rule in the matching section of `SKILL.md`, not a new file.
- `STYLE-GUIDE.md` is the user-facing look (colours, font, cards, motion, camera, sound, cuts). When it changes, update
  the matching `SKILL.md` rules and the `:root` colour tokens near the top of `scripts/compose.py`. The style guide wins.
- `PROMPTS.md` holds the prompts the creator types; `SETUP.md` is the human setup walkthrough.
- Videos are worked on under `videos/<project>/` (one folder per video; `videos/_shared/` holds reusable `sfx/`,
  `img/`, `img/thumbs/`). No footage, sounds, logos or images ship with the kit; only fonts (`assets/fonts`, OFL).

## Commands

Shell variables used throughout `SKILL.md`: `SK=".claude/skills/youtube-edit"`, `W="videos/<project>"`.

```bash
# Tests (synthetic media; must end OK; media tests skip without ffmpeg). Run from scripts/, not tests/.
cd "$SK/scripts" && python3 -m unittest tests            # -v for names
cd "$SK/scripts" && python3 -m unittest tests.test_patch_cut                    # one module
cd "$SK/scripts" && python3 -m unittest tests.test_patch_cut.TestPatchCut.test_x  # one test

# Environment check (also the install table in SKILL.md "Setup check")
node -v && npx hyperframes --version && npx hyperframes doctor
ffmpeg -version && python3 -c "import numpy" && auto-editor --version
npx hyperframes models install parakeet                  # transcriber; always pass --engine parakeet
```

Scripts are standalone CLIs (`python3 "$SK/scripts/<name>.py" --help`); none import each other except the tests. Two
Node scripts (`find-cut-candidates.mjs`, `build-edl-review.mjs`) are driven by `stutter-scan.py` and `cutlist-to-edl.py`.
`tests/helpers.py` runs scripts via `subprocess` with `sys.executable`, so tests work from any install path.

## Pipeline architecture

Runs unattended end to end by default: the two checkpoints are self-gates (SKILL.md "Autonomous run": Claude checks,
fixes and moves on; the user reviews only the finished delivery and its `REPORT.md`). Review mode only when asked.

1. **Cut stage** (raw clip to flat cut). Extract 16 kHz mono WAV, `hyperframes transcribe --engine parakeet --json`,
   `auto-editor` for speech chunks, then `paper-cut.py` writes `cut-list.json` + `PAPER-CUT.md` (**Gate A**).
   The fixed order after that: `hand-cut.py` fixes → `tighten-cut.py` → `sliver.py --fix` → `edge-audit.py` to 0 issues
   → `apply-cut.py` (frame-accurate re-encode to `public/input-video.mp4` + `cut-map.json`) → re-transcribe →
   `dead-air.py --plan` → `patch-cut.py --drop-flat` (flat time, mapped back through `cut-map.json`) → repeat until
   dead-air prints 0 pauses. `cut-list.json` is always in raw-source time; `cut-map.json` maps flat time back to it.
2. **Storyboard** (`storyboard.json`, **Gate B**, with `snaps/sheet.png`). It is both the review artifact and
   the source of truth: beats (`type`, `id`, `in`, `out`, `anchor` phrase), `camera` moves, `tag`, `loops`, and
   `raw_html`/`raw_js` escape hatches. `compose.py` turns it into `public/index.html` (HyperFrames page, GSAP timeline,
   fonts staged into `public/fonts/`, `--shared` assets copied in). `formats/claude_chat.py` is a format plugin.
   `beat-check.py` verifies every anchored element enters 0.10 to 0.60 s before its word against `transcript.json`;
   `snap-beats.py` snapshots each beat; `gap-scan.py` checks long-form coverage density;
   `layout-check.py` runs `hyperframes check` at every beat's fully built moment (text outside its card or the frame).
   `finish-master.py` turns a composite into the two delivery masters (chapters, -14 LUFS, ducked music bed + no-music twin).
3. **Render and verify.** `npx hyperframes render` to 4K, FFmpeg retags BT.709, `verify-render.py` checks black runs,
   tags, bitrate, duration, A/V and clipped words (exit 1 on FAIL). `assemble.py` joins segment masters from
   `assembly.json` into one -14 LUFS 4K master with chapters. `window-patch.py` re-renders only a time window.

Other routes: `ingest.py` joins several raw clips (keeps `ingest.json` for source-time mapping); `sync-tracks.py`
aligns face + screen files by audio cross-correlation; `tella-*.py` handle Tella screen tutorials; `broll-conform.py`
normalises cutaways (30 fps, no audio, keyframe every 15 frames, BT.709); `teardown.py` measures reference videos.
An MP4 that is a Tella export is cut locally, mapped back with `tella-map-cuts.py`, laid out in Tella, exported, and
dressed with `overlay-patches.py` (renders only the overlay windows). Cut-stage helpers: `dropped-runs.py` (what the cut
removes), `join-check.py` (a join transcribed as it plays), `transcribe-windows.py` (long files). Stock B-roll:
`stock-search.py` (Pexels/Pixabay; keys in the project's `.env.local`, never in chat or git).

## Conventions worth knowing

- Formats marked `*` in the library are built and snapshot-tested but less used; DRAFT formats need the creator's yes
  on a snapshot before shipping, so the autonomous run never uses them. A new format needs a test under `scripts/tests/` and the seek-back check in Traps.
- Timing values are seconds as floats in flat-cut time unless a script says otherwise; fps is 30.
- numpy is required by `sync-tracks.py`, `tighten-cut.py`, `sliver.py`, `edge-audit.py`, `dead-air.py`.
- Skills load at thread start: after changing `SKILL.md`, tell the user to open a new thread.
