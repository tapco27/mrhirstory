# The four add-ons

The owner asked for four Claude Code add-ons to be folded into this template. Three are services reached through
connectors or keys, which a skill cannot carry inside it; one is a separate studio. This page says what each one
gives an episode, how to tell whether it is available in the session you are in, and what to do when it is not.
Never stand in for a missing service with made-up results: fall back to the route in the last column of the table
in `SKILL.md` and tell the owner what would unlock the better one.

## ElevenLabs: the narrator's voice

The narrator is an ElevenLabs voice: "Mohammad - Syrian Storyteller", id `bJ9NjytdzbUo4Vxy5pI5`, model
`eleven_v4`, stability 0.5, similarity 0.75. The example `episode.json` already carries these in its `voice`
block; keep them for every episode so the series has one narrator. (An earlier test used "Anas - Natural
Levantine Arabic", `G1S5GeMHqTltMO57mRYa`.) `tools/voice.py` speaks the script with that voice and, with the
audio, gets the time of every character back, so the reel is timed to the voice exactly and nothing has to be
transcribed.

```bash
python3 tools/voice.py voices Mohammad      # find the voice id; put it in episode.json under "voice": {"id": ...}
python3 tools/voice.py models               # if a specific model is wanted ("voice": {"model": ...})
python3 tools/voice.py say episode.json     # writes assets/voice/narration.mp3 and narration.words.json
bash build.sh out/reel.mp4                     # picks the narration up by itself
```

- **Is it available?** Run `voices`. An answer of 401 or 403 means no key is reaching ElevenLabs.
- **The key.** When one is saved on the session's cloud environment for the host `api.elevenlabs.io`, the tool
  reaches ElevenLabs with nothing to configure. Otherwise ask for a credential for that host with the header
  `xi-api-key` (the secure form; never ask for the key in chat). On the owner's own computer, the environment
  variable `ELEVENLABS_API_KEY`. A key belongs to one Claude account's environment; another account saves its own.
- **It spends credits,** one per character spoken. `say` prints the character count; tell the owner the count and
  get a yes before the first generation of a script, and do not regenerate to chase small differences.
- **Pronunciation.** If a word comes out wrong, give that line a `tts` text: the number spelled out
  ("ألف وستمية وتسعة"), a foreign word written as it sounds ("ألتِن"), or diacritics on the one word. Captions
  keep showing `say`.
- **Without a key,** send the owner the numbered script (and a diacritized copy for the generator), and they
  return an MP3. Put it at `assets/voice/narration.mp3`; `tools/align.py` transcribes it to find the words.
- The "ElevenLabs" entry in Claude's connector directory manages voice agents; it is not what speaks a script.
  The local `elevenlabs-mcp` server, if its tools are present, can also produce the MP3, but it returns no word
  times, so the file is transcribed like a recording.

## Magnific: footage

Magnific's MCP server generates and edits images, video and audio from the owner's Magnific account. It is the
answer to the two things this template cannot make from code: real-looking moving footage of a place, and new
clips of the host.

- **Is it available?** Look for its tools (search the tool list for "magnific"; names such as `video_generate`,
  `images_upscale`, `library_create`, `simulate_cost`). They exist only in a session started after the owner
  connected it.
- **Connecting it** is the owner's step: add a custom connector named `Magnific` with the URL
  `https://mcp.magnific.com` at https://claude.ai/customize/connectors (on their own computer:
  `claude mcp add --transport http magnific https://mcp.magnific.com`), sign in, then start a new session.
- **It spends credits.** Call `simulate_cost` for what you are about to make, tell the owner the total, and wait
  for a yes. Read each tool's own description for its parameters: they were not available when this page was
  written, so none are assumed here.

What to use it for, most valuable first:

1. **Drone and interior shots from the real pictures.** Give `video_generate` one of the episode's real
   pictures as the start image and ask for a slow, simple camera move (an aerial push toward the dome, a rise
   along the minaret) with nothing added to the scene. Four to six seconds is enough. Save the result as
   `assets/raw/<name>.mp4` and use it as a video shot with `"x": [0.5, 0.5]` and `"ai": true`. Look at its frames
   before using it: reject a clip that grows a minaret, changes the building or writes text.
2. **Clips of the host.** Save the host once as a character with `library_create` from `assets/raw/host.jpg`,
   then generate the intro for a new episode, or a few seconds of him pushing the gate open (the owner asked for
   that and it could not be done from a still). A talking clip must carry its own voice so lips and sound match;
   put it in `assets/clips` and use it as a `clip` beat.
3. **Upscaling.** The first intro clip is 576x1024 and looks soft beside the graphics; `video_upscale` fixes
   that. Pictures are already upscaled by the bundled model, so image upscaling is rarely worth credits.

Keep the honesty rules of `house-style.md`: the tag on generated footage of real places, no generated likeness
of real people.

## Playwright: the renderer

The template already renders with Playwright: `src/render.mjs` opens `src/reel.html`, steps time frame by frame
and screenshots each one. Cloud sessions have Playwright and Chromium installed; on another machine,
`npm i -g playwright && npx playwright install chromium`. The Playwright MCP server drives a browser by hand,
which adds nothing to a build. If its tools are present, their one use here is research: opening a site's
official page to confirm opening hours or a ticket price before it goes on screen.

## Reel Studio: a separate studio, and a sound kit

Reel Studio (github.com/mohamedabdou-ai/reel-studio, Apache-2.0) is a complete editing studio that lives in its
own folder on a Windows computer: a Remotion engine, eleven styles, a live review editor, its own skill and
agents, and tools it downloads during setup. It edits a recording of a person talking into a captioned reel with
motion graphics. It cannot be packed into this skill, and the two do not share a renderer, so it was not merged.

What was taken from it: its recorded CC0 sound kit, now `assets/sfx/` (with its ledger and notice; see
`NOTICE.md`), which replaced most of the synthesized effects.

How the two live side by side:

- Mr. History episodes are made here. Their shape (host clip, gate, moving pictures) is not one of Reel Studio's
  styles.
- If the owner records themselves talking, or wants clips cut from a long recording, that is Reel Studio's job.
  They install it on their Windows computer by opening an empty folder in Claude Code and sending:
  `نزّل Reel Studio في الفولدر ده من https://github.com/mohamedabdou-ai/reel-studio واتبع AGENTS.md اللي فيه عشان تجهّزه`
- Its notice must stay with anything copied from it, and its name is not used for other work.
