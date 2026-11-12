# My YouTube editor: the Claude Code skill

This is the skill that edits my YouTube videos. It's the one from my video "I Fully Automated My Video Editing Using Claude Code (Full Walkthrough)".

I record, drop the raw files into Claude Code, and it hands me back a first version: every cut, zoom, animation, sound effect and music bed, rendered in 4K. I watch it, give it notes, and anything worth keeping goes back into the skill. That last part is why it keeps getting better. Every rule in it came from a real note I gave on a real video.

## What's inside

| File or folder | What it is |
|---|---|
| `youtube-edit/` | The skill. `SKILL.md` is the rulebook Claude reads. `scripts/` are the tools it runs: cutting, the dead-air scan, the animation composer, render checks and the final assembly. `assets/fonts/` is the font. |
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

For stock B-roll and music, make a file named `.env.local` in your project folder, one key per line:

```
PEXELS_API_KEY=your-pexels-key
PIXABAY_API_KEY=your-pixabay-key
EPIDEMIC_SOUND_API_KEY=your-epidemic-key
```

Type the keys into the file yourself. Never paste them into the chat. `.env.local` is git-ignored.

### First edit

Open a **new** Claude Code thread (skills load when a thread starts). Drop in a raw clip and use the first editing
prompt from `PROMPTS.md`. Start with a 30 to 60 second hook.

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
