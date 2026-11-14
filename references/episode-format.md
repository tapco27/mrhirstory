# episode.json

One file describes an episode. `tools/plan.py` turns it into the timeline; times are never written by hand, they
come from the words. Start from the example in `template/episode.json`.

## Top level

| Field | Meaning |
| --- | --- |
| `fps` | 24, the rate of the host clips |
| `handle`, `series` | `@hassan.tabsho`, `مستر تاريخ`: the tag at the top left and the closing card |
| `title` | The episode title, lettered on the gate's plaque (it shrinks to fit; keep it under about 25 letters) |
| `music` | Name of a file in `assets/music` without its extension (`sufi`). Leave it out, or leave the file out, and a ney-and-frame-drum score is synthesized |
| `musicStart` | Seconds into the track to start from (default 0) |
| `voice` | For `tools/voice.py`: `{"id": "<ElevenLabs voice id>", "model": "", "stability": 0.5, "similarity": 0.75, "speed": 1.0}` |
| `beats` | The episode, in order |

## Beats

**The host's clip.** Plays whole, at its own speed, with its own sound.

```json
{ "clip": "intro", "src": [0.55, 12.2], "caps": false, "say": "مرحبا، أنا مستر تاريخ. ..." }
```

`clip` is a file in `assets/clips` (any video extension). `src` is the stretch to use, in seconds; trim dead air
at both ends but keep a quarter second after his last word. `say` is what he says, used to find his words in the
sound. Keep `caps` false.

**The gate.** `{ "door": true, "dur": 3.4 }`. It needs no words. The first picture of the next line is already
playing behind the door, so choose that picture to be a good reveal.

**A narrated line.**

```json
{
  "say": "القصة بلّشت سنة 1609، لما قرر السلطان أحمد الأول يبني مسجداً يخلّد اسمه عبر التاريخ.",
  "shots": [ { "photo": "bm_ext_h", "move": "right" }, { "photo": "bm_ahmed_a", "move": "push", "on": "السلطان" } ],
  "cards": [ { "type": "year", "value": 1609, "on": "1609", "off": "السلطان" } ]
}
```

- `say` is the caption text and, unless `tts` is given, what the voice speaks.
- `tts` is what to speak when it should differ: a number spelled out, a foreign word written as it sounds,
  diacritics on a word the voice reads wrong.
- `caps: false` hides the caption for the line (the closing line, whose words are on its card).
- `tail` adds seconds of picture after the line (0.7 to let a title sit, 2.6 on the last line so the music can rise).

## Cue words

`on` and `off` name a word of the line: the first word that contains the text, ignoring diacritics and
punctuation. A shot with `on` starts just before that word; a card appears on it. `plan.py` stops with a clear
message if the word is not in the line, so a typo cannot silently mistime something. The first shot of a line
takes no `on`.

## Shots

| Shot | Fields |
| --- | --- |
| A picture with a camera move | `photo` (file in `assets/raw`, no extension), `move`, and optionally `focus`, `zoom`, `css`, `blur`, `air` |
| A still with a slow drift | `photo`, `kb: [scale, x, y, scale, x, y]` (start and end; x and y are shares of the picture). Used for the host's picture on the closing card |
| Video | `video` (an `.mp4` in `assets/raw`), `src: [start, end]`, `x: [from, to]` (centre of the 9:16 window as a share of the width; `[0.5, 0.5]` for vertical footage), optional `grade` (an ffmpeg filter) |

Moves: `push` and `pull` travel toward or away from the subject; `rise` and `sink` crane up or down; `left` and
`right` track sideways; `orbit` arcs around. Near things slide against far ones, using a depth map made by
`tools/enhance.py`.

- `focus: [x, y]` is the point of interest; the move is centred on it. Give four numbers for an explicit start
  and end. Set it whenever the subject is not in the middle, or a wide picture will show sky.
- `zoom: [from, to]` overrides how tight the shot is. A wide picture cropped to 9:16 is already tight; a tall one
  can take `[1.0, 1.14]`.
- `css` is a CSS filter (`"sepia(.35) contrast(1.08)"` for archive pictures).
- `blur` (pixels) softens a picture that sits behind a big graphic.
- `air` adds life: `"birds"` over exteriors, `"dust"` in the light indoors.
- `ai: true` shows a small "مشهد توضيحي بالذكاء الاصطناعي" tag. Set it on any generated footage of a real place.

Pair moves so consecutive shots do not all do the same thing: a push, then a rise, then a sideways track.

## Cards

Every card takes `type`, `on` (default: the start of the line) and `off` (default: the end of the line); `y`
overrides its height on screen.

| Type | Fields | Use |
| --- | --- | --- |
| `ribbon` | `text` | A small label: whose story this is, a name under a portrait (`y: 1120`) |
| `title` | `text`, `sub` (Latin name), `text2`, `on2`, `tint` | The place's name on a plate with a map pin; `text2` pops under it on the word `on2`, in the colour `tint` |
| `year` | `value`, optional `from` | A big year. With `from`, the years roll from that number down to `value` |
| `span` | `from`, `to`, `label`, `full` | Two years joined by a bar that fills; it completes on the word `full` and then shows `label` |
| `chip` | `num`, `plus`, `label` or just `text` | A counter that runs up to `num` on the right side; several stack |
| `tally` | `n`, `label` | Minarets rising one by one with a count |
| `ask` | `text` | A big question |
| `duo` | `a: {latin, ar}`, `b: {latin, ar}`, `on2` | Two foreign words and their meanings; the second is the first losing its last letters on `on2` |
| `stamp` | `text` | A red stamp slammed onto the frame: "بدون دليل تاريخي" |
| `cta` | `line1`, `line2`, `on2` | The closing card with the handle |

Two cards that share the top of the frame need `off` on the first so they do not overlap. A new kind of card is
a new entry in `KIND` in `src/reel.html` (its markup, its height, a `draw` that is a pure function of time) and,
if it should sound, a line in `tools/music.py`.

## Where files go

```
assets/clips/      the host's clips
assets/raw/        pictures and stock video; photo_sources.tsv is their record
assets/voice/      narration.mp3 (and narration.words.json when the voice was generated)
assets/music/      the series track
assets/sfx/        recorded sound kit
assets/door/       the gate's wood; the wall and leaves are drawn on the first build
assets/hd/         made by the build: upscaled pictures and depth maps
build/, out/       made by the build
```
