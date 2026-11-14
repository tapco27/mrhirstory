---
name: mr-history
description: Makes Mr. History (مستر تاريخ) Instagram reels for @hassan.tabsho - vertical 9:16 history and tourism stories about places in Istanbul and beyond, in the series' approved shape. The cartoon host's own clip opens without captions, a carved gate swings open and the camera goes through it, then a narrated story plays over real pictures given drone-like camera moves, with word-timed Arabic captions, animated graphics (rolling years, counters, title plates, word plays, stamps) and Sufi music that rises when nobody speaks and drops under the voice, mastered at 1080x1920. Use this whenever the user asks for a Mr. History reel or episode ("ريل مستر تاريخ", "حلقة جديدة", "قصة" عن مكان, "فيديو تاريخي / سياحي"), sends a script, a host clip, a voice-over or music for one, wants an episode re-timed, shortened, re-voiced or restyled, or wants its voice generated with ElevenLabs or its footage generated with Magnific, even if they do not name the template.
---

# Mr. History reel

A project template that turns a script, the host's intro clip and a narration into a finished reel. Everything is
rendered from code: a web page draws each frame, Playwright captures it, ffmpeg encodes it, and Python does the
timing, the camera moves through still pictures, the sound effects and the mix. Nothing needs an API key; two
optional services (ElevenLabs for the voice, Magnific for footage) plug in when the owner has connected them.

The template is in `template/`. It holds the first approved episode, "قصة المسجد الأزرق", as the worked example:
its `episode.json`, pictures, host clip, narration and music build as they are.

## The shape of an episode

The owner arrived at this shape over many rounds and rejected the alternatives, so keep it unless they ask for a change.

1. **The host.** His own clip with his own voice, full frame, no captions and no graphics over him. He greets,
   names the series and announces today's story.
2. **The gate.** A stone portal with a carved wooden door; the episode title is on its plaque. The leaves swing
   open, light spills out, the camera goes through. Nobody speaks here and the music is at full level.
3. **The story.** The narrator's lines over real pictures of the place. Every picture moves like a camera shot
   (push in, rise, orbit), the frame changes every few seconds on a spoken word, graphics land on the words they
   illustrate, and a light caption follows the voice word by word.
4. **The close.** The host's picture, "wait for the next video", "send it to someone going there", the handle.

## Making an episode

The owner decides by watching, not by reading plans. Work in rounds: a draft they can play, then their voice,
then fixes. Reply in Syrian Arabic, briefly.

1. **Find out what you have.** You need the story script and the host's intro clip. If one is missing, ask for
   it; if the Magnific tools are connected, offer to generate the clip (see `references/integrations.md`). Music,
   handle and series look are already set.
2. **Set up.** Copy `template/` to a working folder the owner can open, then run `bash setup.sh` in it.
3. **Shape the script** into narrated lines: one idea per line, a sentence or two. Keep the owner's words and
   dialect. Fix only what is broken (an unfinished sentence, a line that repeats what the host clip already says)
   and tell them exactly what you changed. Do not add facts. A legend stays a legend: say so on screen (the
   `stamp` graphic) rather than presenting it as history.
4. **Find pictures.** `python3 tools/photos.py search "<place>"` lists free-to-use pictures, `get` downloads
   them and records their source, `sheet` makes a contact sheet. Look at the sheet. Plan two or three pictures per
   line so the frame changes every 2.5 to 4 seconds, and mix distances: far, near, inside, detail.
5. **Write `episode.json`.** The fields are in `references/episode-format.md`; start from the example.
6. **Build a draft** with no narration (`bash build.sh out/draft.mp4`), run `tools/verify.py`, look at its contact
   sheet, fix what is off, and send the draft together with the numbered narration script (the format is in
   `template/script-blue-mosque.md`: the lines as written, then a diacritized copy with numbers spelled out for
   the voice generator). The owner asked for exactly this: see the video and get the text before recording.
7. **Add the voice.** Their recording goes to `assets/voice/narration.mp3` (or generate it with
   `tools/voice.py` when an ElevenLabs key is configured). Build again: every cut, graphic and caption now follows
   the real words. Verify, look, send.
8. **Revise.** Change `episode.json` and rebuild; shots that did not change are not rendered again.

```bash
bash setup.sh                                   # once per copy: fonts, Python packages, tool check
python3 tools/photos.py search "blue mosque interior"      # then: get <id>=<name> ...; sheet; sources
bash build.sh out/draft.mp4                     # first build of an episode: 15 to 25 minutes (it upscales every picture and fetches a model); rebuilds: 4 to 6
python3 tools/verify.py out/draft.mp4        # add the narration file as a second argument once there is one
node src/render.mjs reel.html --stills build/seq 12.5,31,48   # a few frames in seconds, to check a change
python3 tools/sheet.py build/seq build/sheet.jpg 6           # contact sheet of those stills
```

Run long builds in the background and say roughly how long they take. `--stills` needs one earlier build (it
reads `src/timeline.js` and the cached shots).

## What the owner taught this template

Each of these cost a rejected version. The reason matters more than the rule.

- **The host is real footage, never a puppet.** Animating his still picture (a tilting head, a mouth swapped by
  loudness) was built and rejected. He appears only in clips the owner supplies or approves, and as a still on the
  closing card.
- **No captions on the host.** His clip is a performance; text over it made it look like a slideshow.
- **Pictures fill the frame and move.** Framed photo cards over a blurred background were rejected as flat. Use
  `move` on every story picture; reserve graphics for facts.
- **The gate comes after the intro,** so the host is the first thing seen and the door is his hand-off into the
  story.
- **The music is the owner's Sufi track.** It rises the moment the host stops and at the end, and sits low under
  both voices. `tools/mix.py` does this from the voices themselves; do not flatten it.
- **Only pictures that may be used commercially.** This is an advertising account. A picture with a watermark, or
  from a library whose licence is personal-use only, is not used even when the owner sends it: build or find an
  equivalent and say why.
- **Say what you measured and what only ears can judge.** Frames can be looked at; sound cannot be heard here.

## Look and sound

`references/house-style.md` has the palette, type, safe zones, the gate, the graphics and the mix levels. Read it
before changing how anything looks or sounds, or adding a new kind of graphic.

## The four add-ons

`references/integrations.md` explains each: what it gives this template, how to tell whether it is available in
the session, and what to do when it is not. In short:

| Add-on | Role here | Without it |
| --- | --- | --- |
| ElevenLabs | `tools/voice.py` speaks the narration and returns exact word times | The owner generates or records the MP3 and sends it; it is transcribed for timing |
| Magnific (MCP) | Generates footage: drone and interior shots from real pictures, new host clips, upscaling | Still pictures with camera moves; the owner supplies host clips |
| Playwright | Already the renderer (`src/render.mjs`); its MCP adds nothing to a build | - |
| Reel Studio | Its recorded CC0 sound kit is bundled; the studio itself is a separate Windows workspace | Effects are synthesized |

Generating a voice or footage spends the owner's credits. Tell them what will be generated and get a yes first.

## Checking the work

`tools/verify.py <reel.mp4> [narration]` prints the loudness (target -14 LUFS, peak under -1 dBFS), how many
milliseconds each voice sits from where the timeline put it (the host clip must be within 40 ms of its picture or
lips drift), and writes `build/chk/verify.jpg` with a frame at every beat and graphic. Read that image: check
that text stays inside the safe zones, that no graphic covers a face or the subject of a picture, and that each
picture shows what the line is talking about. For camera moves, also look at the first and last frame of a shot
(`build/plates/<shot>/`): tall thin things in front of sky (minarets, finials) are where the depth warp can bend.

## Delivering

Send the MP4 as a file. Say what changed, what was measured, and what they should listen for: the music level
under the voice, the join between the host's voice and the narrator's, any word the voice may have read wrong.
In a cloud session the files are temporary, so tell them to download.

## Lessons already paid for

- **Picture sources.** Openverse (`tools/photos.py`) works but often answers 504 on the first try; the tool
  retries. Wikimedia refuses bursts, so downloads are spaced. Pexels, Pixabay and Unsplash block automated
  access. Most Mixkit videos of Istanbul are under its restricted licence (no commercial use).
- **Transcription invents endings.** Over music with no speech, Whisper writes phrases such as
  "ترجمة نانسي قنقر". They are not in the audio; `tools/align.py` reports them as extra words and ignores them.
- **Word times start late.** The transcriber can miss a first syllable, so the music is ducked from the measured
  sound of the voices, not from word times.
- **A track that builds** would swell at the end of the reel; the mix evens its level out before setting it.
- **Depth edges tear.** The depth map is widened and blurred before warping; a sharper map looks better on
  paper and bends minarets in motion.
- **The film page must be a pure function of time** (`renderAt(t)`), with no CSS animations or timers, because
  four workers render interleaved frames.
- **24 fps** matches the host clips; mixing rates makes his motion stutter.
- **Arabic on screen is always typeset by the page,** never taken from generated video, which garbles letters.
