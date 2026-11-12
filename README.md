# My YouTube editor: the Claude Code skill

This is the skill that edits my YouTube videos. It's the one from my video "I Fully Automated My Video Editing Using Claude Code (Full Walkthrough)".

I record, drop the raw files into Claude Code, and it hands me back a first version: every cut, zoom, animation, sound effect and music bed, rendered in 4K. I watch it, give it notes, and anything worth keeping goes back into the skill. That last part is why it keeps getting better. Every rule in it came from a real note I gave on a real video.

## What's inside

| File or folder | What it is |
|---|---|
| `.claude/skills/youtube-edit/` | The skill, installed where Claude Code loads it. `SKILL.md` is the rulebook Claude reads. `scripts/` are the tools it runs: cutting, the dead-air scan, the animation composer, stock B-roll search, render checks, the music and loudness finish, and the final assembly. `assets/fonts/` is the font. |
| `youtube-edit/` | The same skill, as a copy to hand out or install somewhere else. Keep it in sync with `rsync -a --delete .claude/skills/youtube-edit/ youtube-edit/`. |
| `.mcp.json` | Connects the Epidemic Sound MCP server (music and sound effects). The key comes from your environment, not this file. |
| `CLAUDE.md` | Notes for Claude Code on how the repo and the pipeline fit together. |
| `SETUP.md` | How to set it up, step by step. Plan on 30 minutes. Most of it installs itself. |
| `PROMPTS.md` | The exact prompts I type, from setup to "save this to the skill". |
| `STYLE-GUIDE.md` | My look: colours, font, cards, motion, camera, sound and cuts. Change it to yours. |
| `LICENSES/` | The licences for the font and for the code parts adapted from an open-source starter kit. |

## Install

New to Claude Code? Do `SETUP.md` steps 1 to 6 first (the app, a plan, permissions, connectors). Then pick one of
these.

### Option A: clone it and work in it (easiest)

The repo is already a ready-to-go project: the skill sits in `.claude/skills/youtube-edit/`, where Claude Code
loads it.

```bash
git clone https://github.com/harperaa/YouTube-Editor.git
cd YouTube-Editor
claude
```

Your videos go in `videos/<project>/` inside it. That folder is git-ignored, so footage and renders never get
committed.

### Option B: add the skill to a project you already have

```bash
git clone https://github.com/harperaa/YouTube-Editor.git /tmp/YouTube-Editor
mkdir -p .claude/skills
cp -R /tmp/YouTube-Editor/youtube-edit .claude/skills/
```

Run that from your project folder. To get the skill in every project, copy it to `~/.claude/skills/` instead.

Prefer to let Claude do it? Put the cloned folder inside your project and type:

> Install the youtube-edit skill from the YouTube-Editor folder into this project's .claude/skills folder. Then check everything it needs, install what's missing, and run its tests.

### Install what it needs

Claude checks and installs these itself the first time you use the skill (see "Setup check" in `SKILL.md`).
If you'd rather do it by hand on a Mac:

| Tool | What it's for | Install |
|---|---|---|
| Node.js 22+ | runs HyperFrames | `brew install node` |
| HyperFrames | draws the animations, renders the frames | comes through `npx`; then `npx hyperframes doctor` |
| Parakeet | writes down every word with its exact time | `npx hyperframes models install parakeet` |
| FFmpeg | cuts, joins and encodes the video | `brew install ffmpeg` |
| Python 3 + numpy | the cutting and audio scripts | `python3 -m pip install numpy` |
| auto-editor | finds where you speak | `pip install auto-editor` or `brew install auto-editor` |
| Google Chrome | snapshots and renders | google.com/chrome |

On Windows, `winget install ffmpeg` and nodejs.org stand in for the brew lines.

Check it all with:

```bash
node -v && npx hyperframes --version && npx hyperframes doctor
ffmpeg -version && python3 -c "import numpy" && auto-editor --version
cd .claude/skills/youtube-edit/scripts && python3 -m unittest tests   # must end with OK
```

### API keys (optional)

**Stock B-roll (Pexels and/or Pixabay).** Get a free key from pexels.com/api and/or pixabay.com/api/docs. Put them in
a file named `.env.local` in your project folder, one per line:

```
PEXELS_API_KEY=your-pexels-key
PIXABAY_API_KEY=your-pixabay-key
```

`stock-search.py` uses every provider it finds a key for. With both keys it searches both and takes the better clip.
With neither, the skill leaves B-roll out and says so in the report.

**Music and sound effects (Epidemic Sound).** `.mcp.json` connects the Epidemic Sound MCP server and reads the key
from the `EPIDEMIC_SOUND_API_KEY` environment variable. Claude Code doesn't read `.env.local` for that, so put the key in
`.claude/settings.local.json`:

```json
{
  "env": { "EPIDEMIC_SOUND_API_KEY": "your-epidemic-key" },
  "enabledMcpjsonServers": ["epidemic-sound"]
}
```

Or `export` it in your shell before running `claude`. You can also use the Epidemic Sound connector in the Claude app
(`SETUP.md` step 6) instead. Without Epidemic Sound, the skill uses the free HyperFrames sound library
(`npx hyperframes skills update media-use`).

Type keys into these files yourself. Never paste them into the chat. Both `.env.local` and
`.claude/settings.local.json` are git-ignored.

**Your own sounds, music and images.** None ship with the kit. Keep them in `videos/_shared/` (`sfx/`, `music/`,
`img/`, `img/thumbs/`) and the composer copies in what each video uses.

### First edit

Open a **new** Claude Code thread (skills load when a thread starts). Drop in a raw clip and use the first editing
prompt from `PROMPTS.md`. Start with a 30 to 60 second hook.

## What this version adds

These were added on top of the version from the video:

- **Stock B-roll from Pexels and Pixabay.** `stock-search.py` searches one slot at a time (for example "the person or
  job you just named"), writes a shortlist with a thumbnail sheet, and downloads the pick in 4K (or 1080p when there's
  no 4K). It records the page, author and licence in `clips.json`. `broll-conform.py` then makes it a cutaway: 30 fps,
  no audio, BT.709, and readable logos blurred. Every clip and its licence is listed in `STORYBOARD.md`. It adds about
  one shot a minute on the people and jobs you name. It never uses AI B-roll in an unattended run (that costs credits),
  and it skips Mixkit Restricted clips, clips labelled AI-generated and anything from a paid tier.
- **Hands-off by default.** Point it at a video and it delivers the finished master without stopping to ask. Each
  stage checks itself: Gate A after the cut, Gate B after the plan, Gate C on the master. If a check fails, it fixes
  it and runs it again. `REPORT.md` lists every choice it made for you, every check result, and the timestamps worth
  watching first. Say "review mode" if you want it to stop for you at the cut and the plan.
- **Music bed and finish.** `finish-master.py` adds a lo-fi bed that ducks under your voice (with a bit of tension
  under the hook). It measures the bed in the finished file and corrects it until it sits 14.2 dB (hook) and 17.2 dB
  (body) under your voice. It brings everything to -14 LUFS, embeds chapters, and writes a no-music copy next to it.
- **Tella exports.** Give it an MP4 you exported from Tella and it cuts the audio locally, maps the cuts back onto a
  copy of the Tella video (`tella-map-cuts.py`), exports that in 4K, and renders only the overlay windows on top
  (`overlay-patches.py`). Your original Tella video is never touched.
- **More checks before rendering.** `layout-check.py` finds text that spills out of its card or off the frame.
  `dead-air.py` keeps a 0.5 s lead-in of room tone before the first word. `word-audit.py`, `join-check.py` and
  `tail-audit.py` catch clipped words at the cuts. `window-patch.py` re-renders just one time window instead of the
  whole video.
- **Delivery folder.** Each finished video lands in `~/Movies/YouTube Renders/<project>/`. Next to the master are
  `STORYBOARD.md`, `VERIFY.md`, `chapters.txt`, `MD5.txt` and `REPORT.md`. An earlier delivery moves into a `v<n>/`
  folder; it's never deleted.

## What it costs to run

The skill itself is free, and so are most of the tools it uses (HyperFrames, FFmpeg, auto-editor, the Parakeet transcription). The $20 Claude plan is enough to set everything up. Editing a full video uses a lot more: I'm on the $200 Max plan, and in the video I break down what one video costs me. Tella (screen recordings) and Epidemic Sound (music) are paid tools I use. You can skip both: record your screen with anything, and pull sounds from the free library the skill points to.

## Make it yours

The first version will look like my channel, because that's what it learned on. To make it look like yours:

1. Open `STYLE-GUIDE.md` and change the colours, the font and the rules you don't like.
2. Tell Claude: "Here's my style guide. Update the youtube-edit skill to match it."
3. Edit a short clip, give notes in plain words ("the text is too small", "no sound on this part"), and after each round say: "Save this to the skill."

That's how mine learned. Every note I've saved, it hasn't made that mistake again.

## Where to get help

Questions go in the free community, in the post for this video: https://www.skool.com/wearenocode

## Licences

- The font is DM Sans, under the SIL Open Font License (`LICENSES/OFL-DM-Sans.txt`).
- Some of the scripts started from an open-source starter kit under the MIT License. Its notice is in `LICENSES/MIT-starter-kit.txt` and stays with the code.
- No music, sound effects, footage or logos ship with this kit. Use your own, or ones you have the rights to.
