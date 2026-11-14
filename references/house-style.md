# House style, with reasons

## Identity

- **Series:** مستر تاريخ, on `@hassan.tabsho`. A cartoon host in Ottoman dress (cream turban with an emerald,
  green velvet robe with gold embroidery) tells the history of a place in Syrian Arabic.
- **Palette:** deep green `#0E3B2E` and `#07241A`, gold `#D9AE55` to `#F6DD9A`, cream `#F8EFDC`, a red `#A3302A`
  for stamps and pins. They are the host's own colours, so graphics look like they belong to him.
- **Type:** Lalezar for display (titles, numbers), Tajawal 800 for captions and labels, Aref Ruqaa for the gate's
  plaque. All are typeset by the page.

## Frame

- 1080x1920 at 24 fps. Instagram covers the top 220 px and the bottom 340 px, and its buttons take the right
  130 px, so text lives between y=220 and y=1580 and stays clear of the right edge.
- Top band (y 230 to 560): titles, years, ribbons. Right side (y 620 down): counters. Caption: y 1330.
- A dark gradient fades in behind the top band and behind the caption only while text is there. The host's clip
  gets no shade.

## The gate

Drawn by `tools/portal.py`: ashlar wall, a pointed arch of alternating light and dark stones, a hood of small
niches, a green plaque with a gold rim for the title, brass lanterns that sway and flicker, and a double door
whose panels are a real carved-wood photograph (public domain) set in walnut stiles. The owner asked for this
kind of door after rejecting a plain one. The wall and leaves are regenerated only when missing; delete
`assets/door/wall.png` to redraw after changing `portal.py`.

## Story pictures

- Real pictures of the real place, full frame, each with a camera move. Small pictures are upscaled four times
  and reduced, which is why 1000 px sources hold up.
- Archive photographs and engravings get a sepia filter and open the historical lines; modern colour pictures
  carry the present.
- Cuts land a little before a spoken word, with a short white flash. The cut from the host to the gate gets a
  fuller flash.
- Birds or dust give a still picture something that moves on its own.

## Captions

White Tajawal 800, 62 px, dark outline, no box, one phrase at a time. The word being spoken turns gold. Phrases
break at punctuation or after six words. Latin words and numbers are isolated so they do not flip the line.

## Sound

- **Voices lead.** The host's clip and the narration are levelled to the same loudness and lightly compressed.
- **Music** is the track in `assets/music`. Full level where nobody speaks (the gate, the close), 14 dB lower
  under any voice, easing down over half a second and back up over 0.8. Pauses shorter than 1.3 seconds stay
  ducked so the music does not pump between sentences.
- **Effects** are short and quiet: recorded clicks, pops, ticks, a wooden thud and a page from the CC0 kit; air on
  cuts and the door's creak are synthesized.
- **Master:** -14 LUFS integrated, limiter ceiling about -1.5 dBFS.
- With no `music` in the episode, `tools/music.py` plays its own score in the same manner: a breathy ney in
  makam Ussak over a drone, a slow frame drum, a long dark reverb.

## Honesty

- Facts come from the owner's script. Numbers added on screen (a count of tiles, a duration) must be true and
  common knowledge, and the owner is told they were added.
- A legend is shown as a legend.
- Generated footage of a real monument carries the tag, and is checked frame by frame for invented architecture:
  a six-minaret mosque keeps six.
- A real person's likeness is not generated. The sultan is shown through a period portrait.
- Every picture has a recorded source and a licence that allows advertising use (`SOURCES.md`).
