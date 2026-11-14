# Turns episode.json into the timeline the film page reads.
# Usage: plan.py <episode.json> <out timeline.js> [words.json from align.py]
# A beat is a clip of the host talking (its own sound, real length), the gate opening into the story, or a
# narrated line over pictures.
# Narrated lines are timed by the real voice-over when words.json has one, otherwise by an estimate.
import json, re, sys

PACE = 10.0        # letters per second when estimating: the pace of the generated voice
GAP = 0.30         # breath between lines
VO_LEAD = 0.15     # the voice-over starts this long after the last clip ends

ep = json.load(open(sys.argv[1], encoding='utf-8'))
heard = json.load(open(sys.argv[3], encoding='utf-8')) if len(sys.argv) > 3 else {}
FPS = ep.get('fps', 30)
vo = heard.get('vo')

bare = lambda s: re.sub(r'[ً-ْ…؟?!.:،,«»]', '', s)
letters = lambda w: len(re.sub(r'[^\w]', '', bare(w)))
pause = lambda w: .32 if re.search(r'[…؟?!.:]$', w) else .14 if re.search(r'[،,]$', w) else 0


def estimate(text, t):
    out = []
    for w in text.split():
        d = max(letters(w), 2) / PACE
        if re.fullmatch(r'[\d,+]+', re.sub(r'[^\w,+]', '', w)):
            d = max(d, 1.1)                 # numbers are read out as several words
        out.append({'w': w, 'a': round(t, 3), 'b': round(t + d, 3)})
        t += d + pause(w)
    return out


def cue(words, key, default):
    # Start of the first word containing `key`; a number is a share of the line; missing means `default`
    if key is None:
        return default
    a, e = words[0]['a'], words[-1]['b']
    if isinstance(key, (int, float)):
        return a + (e - a) * key
    for w in words:
        if bare(key).lower() in bare(w['w']).lower():
            return w['a']
    raise SystemExit(f'cue word "{key}" is not in the line: {" ".join(w["w"] for w in words)}')


t = 0.0; vo_at = None; door_from = None
beats, shots, clips = [], [], []
for n, b in enumerate(ep['beats']):
    t0 = t
    if b.get('door'):                                      # the gate opens: no words; the next line's first picture is already behind it
        t = t0 + b.get('dur', 3.2); door_from = t0
        beats.append({**b, 'n': n, 't0': round(t0, 3), 't1': round(t, 3), 'sa': t0, 'sb': t0, 'words': [], 'cards': []})
        continue
    if 'clip' in b:
        s0, s1 = b['src']; lead = b.get('lead', 0)              # lead: the door opens before the clip starts
        c0 = t0 + lead; t1 = c0 + (s1 - s0)
        got = heard.get('clips', {}).get(str(n))
        words = [{'w': w['w'], 'a': round(c0 + w['a'] - s0, 3), 'b': round(c0 + w['b'] - s0, 3)} for w in got] if got else estimate(b['say'], c0 + .3)
        clips.append({'file': b['clip'], 't0': round(c0, 3), 'src': b['src']})
        beat_shots = [{'clip': b['clip'], 'src': b['src'], 'lead': lead}]
    else:
        if vo_at is None:
            vo_at = t0 + VO_LEAD
        words = [{'w': w['w'], 'a': round(vo_at + w['a'], 3), 'b': round(vo_at + w['b'], 3)} for w in vo['beats'][str(n)]] if vo else estimate(b['say'], t0 + (VO_LEAD if not beats or 'say' not in ep['beats'][n - 1] or 'clip' in ep['beats'][n - 1] else GAP / 2))
        e = words[-1]['b']; t1 = e + GAP / 2 + b.get('tail', 0)
        nxt = n + 1 < len(ep['beats']) and vo and vo['beats'].get(str(n + 1))
        if nxt:                                            # the beat changes in the middle of the pause before the next line
            t1 = min(max(e, (e + vo_at + nxt[0]['a']) / 2), vo_at + nxt[0]['a'] - .04)
        beat_shots = b['shots']
    beat = {k: v for k, v in b.items() if k not in ('shots', 'cards')}
    beat.update({'n': n, 't0': round(t0, 3), 't1': round(t1, 3), 'sa': words[0]['a'], 'sb': words[-1]['b'], 'words': words, 'cards': []})
    for c in b.get('cards', []):
        c = {**c, 'at': round(cue(words, c.get('on'), t0 + .15), 3), 'offAt': round(cue(words, c.get('off'), t1), 3)}
        for key in ('on2', 'full'):
            if key in c:
                c[key + 'At'] = round(cue(words, c[key], t0), 3)
        beat['cards'].append(c)
    # Shots fill the beat; each starts at its cue word, a little early so the cut leads the word
    starts = [t0 if door_from is None else door_from] + [max(t0 + .4, cue(words, s.get('on'), t0) - .12) for s in beat_shots[1:]]; door_from = None
    for k, s in enumerate(beat_shots):
        shots.append({**s, 'id': f'b{n}s{k}', 'beat': n, 't0': round(starts[k], 3), 't1': round(starts[k + 1] if k + 1 < len(starts) else t1, 3)})
    beats.append(beat)
    t = t1

duration = round(t * FPS) / FPS
tl = {'fps': FPS, 'duration': duration, 'handle': ep['handle'], 'series': ep.get('series', ''), 'title': ep.get('title', ''), 'beats': beats, 'shots': shots,
      'clips': clips, 'voAt': round(vo_at or 0, 3), 'voiced': bool(vo), 'music': ep.get('music'), 'musicStart': ep.get('musicStart', 0)}
open(sys.argv[2], 'w', encoding='utf-8').write('window.TL = ' + json.dumps(tl, ensure_ascii=False, indent=1) + ';\n')
print(f'{duration:.2f}s at {FPS} fps, {len(beats)} beats, {len(shots)} shots, voice-over ' + (f'placed at {vo_at:.2f}s' if vo else 'not recorded yet (estimated)'))
for b in beats:
    print(f"  {b['t0']:6.2f}-{b['t1']:6.2f}  {'door ' if b.get('door') else 'clip ' if 'clip' in b else 'line '} {b.get('say', '')[:70]}")
