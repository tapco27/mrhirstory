# Synthesizes the reel's score and sound effects from the timeline.
# The score is in the Sufi manner: a breathy ney improvising in makam Ussak over a held drone, with a slow
# frame drum (dum - te ke) and a few plucked notes. Under the host's own clip there is only the drone, so his
# voice stays clear; the ney enters when the door opens.
# Usage: music.py <timeline.js> <music.wav> <sfx.wav> [sound kit folder]
import json, os, re, sys, wave
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly

SR = 44100
tl = json.loads(re.sub(r'^[^{]*', '', open(sys.argv[1], encoding='utf-8').read()).strip().rstrip(';'))
DUR = tl['duration']; N = int((DUR + .1) * SR)
rng = np.random.default_rng(7)
BPM = 66; BEAT = 60 / BPM; BAR = 4 * BEAT
TONIC = 440.0                                                   # A: the ney's home note
T0 = next((b['t0'] for b in tl['beats'] if 'clip' not in b), 0)      # the story starts here (at the door, if there is one)
cents = lambda c: TONIC * 2 ** (c / 1200)


def put(buf, x, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N or i < 0:
        return
    n = min(len(x), N - i)
    buf[i:i + n, 0] += x[:n] * gain * (1 - max(pan, 0))
    buf[i:i + n, 1] += x[:n] * gain * (1 + min(pan, 0))


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], btype='band', fs=SR, output='sos'), x)


def ney(phrase):
    # One breath: notes joined by glides, vibrato that grows on held notes, breath noise riding on the tone.
    # phrase: [(cents above the tonic, beats)]
    total = sum(b for _, b in phrase) * BEAT; n = int(total * SR); t = np.arange(n) / SR
    pitch = np.zeros(n); amp = np.zeros(n); held = np.zeros(n); at = 0.0
    for k, (c, beats) in enumerate(phrase):
        i0, i1 = int(at * SR), min(int((at + beats * BEAT) * SR), n); pitch[i0:i1] = c
        held[i0:i1] = np.arange(i1 - i0) / SR                       # time since this note began
        swell = .8 + .2 * np.sin(np.linspace(0, np.pi, i1 - i0)); amp[i0:i1] = swell * (1.0 if k else .9)
        at += beats * BEAT
    glide = int(.085 * SR); pitch = np.convolve(np.pad(pitch, glide, mode='edge'), np.hanning(glide * 2) / np.hanning(glide * 2).sum(), 'same')[glide:-glide]
    vib = np.clip((held - .22) / .5, 0, 1) * 17 * np.sin(2 * np.pi * (5.1 * t + .25 * np.sin(2 * np.pi * .31 * t)))
    f = cents(pitch + vib + 4 * np.sin(2 * np.pi * .6 * t)); ph = 2 * np.pi * np.cumsum(f) / SR
    env = amp * np.minimum(1, t / .09) * np.minimum(1, (total - t) / .22)
    tone = np.sin(ph) + .34 * np.sin(2 * ph + .4) + .17 * np.sin(3 * ph) + .07 * np.sin(4 * ph) + .035 * np.sin(5 * ph)
    breath = bp(rng.normal(0, 1, n), 1400, 6500) * (.10 + .16 * np.exp(-held / .05)) + bp(rng.normal(0, 1, n), 500, 1400) * .05
    return (tone * (.92 + .08 * bp(rng.normal(0, 1, n), 4, 14)) + breath) * env


def drum(kind):
    # Frame drum: "dum" is the open skin with its rattle, "te" and "ke" are the rim
    t = np.arange(int((.95 if kind == 'dum' else .2) * SR)) / SR
    if kind == 'dum':
        skin = np.sin(2 * np.pi * (96 * t + 30 * (1 - np.exp(-t * 18)) / 18)) * np.exp(-t * 5.5) + .5 * np.sin(2 * np.pi * 178 * t) * np.exp(-t * 8)
        return skin + bp(rng.normal(0, 1, len(t)), 250, 1500) * np.exp(-t * 14) * .28
    return (np.sin(2 * np.pi * (300 if kind == 'te' else 250) * t) * np.exp(-t * 34) + bp(rng.normal(0, 1, len(t)), 900, 3600) * np.exp(-t * 46) * .7) * (1 if kind == 'te' else .7)


def pluck(c, dur):
    t = np.arange(int(dur * SR)) / SR; f = cents(c); x = np.zeros_like(t)
    for h in range(1, 10):
        x += np.sin(2 * np.pi * f * h * (1 + .0005 * h * h) * t + rng.uniform(0, 6.28)) / h ** 1.2 * np.exp(-t * (1.6 + 1.2 * h))
    return x * np.minimum(1, t / .004)


def drone(c, dur):
    t = np.arange(int(dur * SR)) / SR; f = cents(c)
    x = sum(np.sin(2 * np.pi * f * k * t * (1 + d) + rng.uniform(0, 6.28)) / k ** 1.4 for k in (1, 2, 3, 4) for d in (-.0015, .0015))
    hum = bp(rng.normal(0, 1, len(t)), f * 1.4, f * 3.2) * .5                 # a breath of voices in the room
    return (x + hum) * (.85 + .15 * np.sin(2 * np.pi * .11 * t)) * np.minimum(1, t / 1.5) * np.minimum(1, (dur - t) / 1.5)


music = np.zeros((N, 2))
# The makam's notes above the tonic, in cents: the second degree sits between B flat and B
A, Bq, C, D, E, F, G, A2 = 0, 160, 300, 500, 700, 800, 1000, 1200
PHRASES = [
    [(E, 1), (A2, 3), (G, 1), (F, 1), (E, 3)],                                    # the call: up to the octave
    [(D, 2), (C, 1), (Bq, 1), (A, 4)],
    [(A, 1), (Bq, 1), (C, 2), (D, 2), (C, 1), (Bq, 1), (A, 4)],
    [(C, 1), (D, 1), (E, 3), (D, 1), (C, 1), (D, 1), (C, 1), (Bq, 1), (A, 4)],
    [(E, 2), (F, 1), (E, 1), (D, 2), (E, 1), (D, 1), (C, 2), (Bq, 1), (A, 3)],
    [(E, 1), (G, 1), (A2, 3), (G, 1), (F, 1), (E, 3), (D, 1), (E, 1), (C, 2)],
    [(A2, 2), (G, 1), (F, 1), (E, 2), (D, 1), (C, 1), (D, 1), (C, 1), (Bq, 1), (A, 4)],
]
CLOSE = [(D, 1), (C, 1), (Bq, 1), (A, 5)]                                         # home, held
# Drone under everything; fuller once the story starts
put(music, drone(-1200, DUR), 0, .030); put(music, drone(-500, DUR), 0, .016)
if DUR - T0 > 4:
    put(music, drone(-1200, DUR - T0), T0, .030); put(music, drone(0, DUR - T0), T0, .012)
# Ney: phrase after phrase, each starting on a bar, with a breath between; the last one comes home
t = T0 + .2; k = 0; end = DUR - sum(b for _, b in CLOSE) * BEAT - .6
while True:
    ph = PHRASES[k % len(PHRASES)]; length = sum(b for _, b in ph) * BEAT
    if t + length > end:
        break
    put(music, ney(ph), t, .22, -.12); k += 1
    t = T0 + np.ceil((t + length + 1.6 * BEAT - T0) / BAR) * BAR
put(music, ney(CLOSE), min(t, end), .22, -.12)
# Frame drum: dum . te ke, soft; a plucked tonic or fifth on some bars
for b in range(int((DUR - T0) / BAR) + 1):
    tb = T0 + BAR * b
    if tb > DUR - 1.2:
        break
    put(music, drum('dum'), tb, .30); put(music, drum('te'), tb + 2 * BEAT, .16, .2); put(music, drum('ke'), tb + 3 * BEAT, .13, -.2)
    if b % 2 == 1: put(music, drum('te'), tb + 3.5 * BEAT, .07, .2)
    put(music, pluck(-1200 if b % 4 != 2 else -500, 2.4), tb, .13, .15)
put(music, drum('dum'), DUR - 1.0, .3)
# The room: a long, dark reverb
ir_t = np.arange(int(2.4 * SR)) / SR
wet = np.stack([fftconvolve(music[:, c], bp(rng.normal(0, 1, len(ir_t)), 200, 3800) * np.exp(-ir_t / .55), 'full')[:N] for c in (0, 1)], 1)
music = music + wet * (.34 * np.abs(music).max() / (np.abs(wet).max() + 1e-9))

# ---------- Sound effects ----------
# Short recorded sounds come from the CC0 kit in assets/sfx (clicks, pops, ticks, a wooden thud, a page);
# what the kit has no sound for (air on a cut, the door's creak, the light) is synthesized here.
sfx = np.zeros((N, 2))
KIT = sys.argv[4] if len(sys.argv) > 4 else ''


def kit(name):
    path = os.path.join(KIT, name + '.wav')
    if not os.path.exists(path):
        return None
    w = wave.open(path); x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float64).reshape(-1, w.getnchannels()).mean(1) / 32768
    x = resample_poly(x, SR, w.getframerate()) if w.getframerate() != SR else x
    return x / (np.abs(x).max() + 1e-9)


def whoosh(dur=.34):
    t = np.arange(int(dur * SR)) / SR; n = rng.normal(0, 1, len(t)); p = t / dur
    return (bp(n, 300, 1200) * (1 - p) + bp(n, 1200, 5000) * p) * np.sin(np.pi * p) ** 2


def pop(f=620):
    t = np.arange(int(.09 * SR)) / SR
    return np.sin(2 * np.pi * (f * t + f * .6 * t * t / .09)) * np.exp(-t * 42)


def boom():
    t = np.arange(int(.7 * SR)) / SR
    return np.sin(2 * np.pi * (70 * t + 90 * (1 - np.exp(-t * 14)) / 14)) * np.exp(-t * 7)


def creak(dur):
    # An old door: a rough tone that climbs and stutters as the hinge sticks and slips
    t = np.arange(int(dur * SR)) / SR; f = 150 + 120 * (t / dur) ** .7 + 14 * np.sin(2 * np.pi * 5 * t)
    tone = sum(np.sin(2 * np.pi * np.cumsum(f * h) / SR) / h for h in (1, 2, 3, 5))
    grip = .55 + .45 * np.sign(np.sin(2 * np.pi * np.cumsum(24 + 16 * t / dur) / SR))
    return bp(tone * grip + rng.normal(0, .25, len(t)), 220, 2600) * np.sin(np.pi * t / dur) ** .6


def shimmer(dur):
    t = np.arange(int(dur * SR)) / SR
    return bp(rng.normal(0, 1, len(t)), 3000, 9000) * (t / dur) ** 2 * np.minimum(1, (dur - t) / .15)


def hit(name, at, gain, pan=0.0, fallback=None):
    x = kit(name)
    put(sfx, x if x is not None else (fallback if fallback is not None else pop()), at, gain if x is not None else gain * .9, pan)


def count(at, dur, gain, pan=0.0):
    # A counter running: ticks that start fast and slow down as the number settles
    t = 0.0; k = 0
    while t < dur:
        hit(f'tick-{k % 3 + 1}', at + t, gain * (1 - .5 * t / dur), pan, pop(1500)); t += .045 + .11 * (t / dur) ** 1.5; k += 1


for s in tl['shots']:
    if s['t0'] > 0:
        put(sfx, whoosh(), s['t0'] - .2, .14)
for b in tl['beats']:
    if b.get('door'):                                      # a page closes, the bolt drops, the door creaks open, the camera goes through
        L = b['t1'] - b['t0'] - .45
        hit('paper-flip', b['t0'] + .05, .2); hit('landing-wood', b['t0'] + .18 * L, .34, 0, boom())
        put(sfx, boom(), b['t0'] + .18 * L, .16); put(sfx, creak(.64 * L), b['t0'] + .18 * L, .05)
        put(sfx, shimmer(.5 * L), b['t0'] + .3 * L, .05); put(sfx, whoosh(.9), b['t0'] + L - .55, .24)
    for c in b['cards']:
        kind = c['type']
        hit('pop-select' if kind in ('chip', 'title') else 'pop-organic', c['at'] - .05, .2, .2)
        if kind == 'year' and c.get('from'): count(c['at'], 1.5, .14)
        if kind == 'chip' and c.get('num', 0) > 50: count(c['at'], .85, .12, .2)
        if kind == 'tally':
            for k in range(c['n']): hit('pop-minimal', c['at'] + .15 + k * .17, .16, 0, pop(520 + 60 * k))
        if kind in ('title', 'duo', 'cta') and 'on2At' in c: hit('pop-select', c['on2At'] - .05, .2, -.2, pop(760))
        if kind == 'stamp': hit('landing-wood', c['at'] + .1, .4, 0, boom()); put(sfx, boom(), c['at'] + .1, .14)
        if kind == 'cta': hit('chime-soft', c['at'] + .5, .16)

for path, buf in ((sys.argv[2], music), (sys.argv[3], sfx)):
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(buf * .5, -1, 1) * 32767).astype('<i2').tobytes())
print(f'score {DUR:.1f}s, ney from {T0:.2f}s, {k + 1} phrases at {BPM} bpm')
