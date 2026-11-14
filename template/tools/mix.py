# Mixes the host's clip sound, the voice-over (when there is one), the score and the effects.
# The score is the episode's own track when it names one (episode "music"), otherwise the synthesized one.
# It plays up where nobody speaks (the gate, the ending) and drops under every voice.
# Usage: mix.py <timeline.js> <clipsDir> <musicDir> <synth score.wav> <sfx.wav> <out.wav> [voice-over file]
import json, os, re, subprocess, sys, wave
import numpy as np

SR = 44100
tl = json.loads(re.sub(r'^[^{]*', '', open(sys.argv[1], encoding='utf-8').read()).strip().rstrip(';'))
clips_dir, music_dir = sys.argv[2], sys.argv[3]; vo_file = sys.argv[7] if len(sys.argv) > 7 else None
SCORE_RMS, DUCK, SFX, VOICE_RMS = .125, .2, .8, .11        # score alone about -18 dBFS; under a voice 14 dB lower
JOIN, DOWN, UP = 1.3, .5, .8                              # pauses shorter than JOIN stay ducked; fade down / back up, seconds
CLEAN = 'highpass=f=75,acompressor=threshold=0.05:ratio=4:attack=2:release=60'
find = lambda folder, name: next(os.path.join(folder, f) for f in sorted(os.listdir(folder)) if os.path.splitext(f)[0] == name)


def decode(path, extra=(), af=None, ch=2):
    cmd = ['ffmpeg', '-v', 'error', *extra, '-i', path] + (['-af', af] if af else []) + ['-ac', str(ch), '-ar', str(SR), '-f', 'f32le', '-']
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).astype(np.float64).reshape(-1, ch)


def speech_from(path, extra=()):
    # Rumble filter and light compression, then one loudness for every voice in the film
    x = decode(path, extra, CLEAN, 1)[:, 0]; act = x[np.abs(x) > .02 * np.abs(x).max()]
    return x * VOICE_RMS / (np.sqrt(np.mean(act ** 2)) + 1e-9)


N = int((tl['duration'] + .1) * SR)
# Score: the chosen stretch of the track (looped if the film is longer), levelled, with a tail fade
track = tl.get('music')
try:
    track_file = find(music_dir, track) if track else None
except (StopIteration, FileNotFoundError):
    print(f'assets/music has no "{track}": using the synthesized score'); track = track_file = None
score = decode(track_file, ['-ss', str(tl.get('musicStart', 0))]) if track_file else decode(sys.argv[4])
score = np.tile(score, (N // len(score) + 1, 1))[:N]
# A track that builds as it goes would swell too far at the end: even its level out, slowly, then set it
k = int(3 * SR); power = np.concatenate([[0], np.cumsum(np.mean(score ** 2, 1))])          # running mean over six seconds
lo, hi = np.clip(np.arange(N) - k, 0, N), np.clip(np.arange(N) + k, 0, N)
slow = np.sqrt((power[hi] - power[lo]) / (hi - lo) + 1e-9)
score *= (np.clip(np.sqrt(np.mean(score ** 2)) / slow, .5, 2) ** .85)[:, None]
score *= SCORE_RMS / (np.sqrt(np.mean(score ** 2)) + 1e-9)
sfx = decode(sys.argv[5]); sfx = np.pad(sfx, ((0, max(0, N - len(sfx))), (0, 0)))[:N]

speech = np.zeros((N, 2)); spans = []
for c in tl['clips']:
    x = speech_from(find(clips_dir, c['file']), ['-ss', str(c['src'][0]), '-to', str(c['src'][1])]); f = int(.05 * SR)
    x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
    i = int(c['t0'] * SR); n = min(len(x), N - i); speech[i:i + n] += x[:n, None]
if vo_file:
    x = speech_from(vo_file); i = int(tl['voAt'] * SR); n = min(len(x), N - i); speech[i:i + n] += x[:n, None]
# Where somebody is speaking, measured on the voices themselves (word times can miss a first syllable)
win = int(.05 * SR); level = np.sqrt(np.mean(speech[:N // win * win, 0].reshape(-1, win) ** 2, axis=1))
for k in np.where(level > .012)[0]:
    a, b = k * win / SR, (k + 1) * win / SR
    if spans and a - spans[-1][1] < JOIN: spans[-1][1] = b
    else: spans.append([a, b])
spans = [s for s in spans if s[1] - s[0] > .15]
# A stretch ends with its last word, not with the rustle of a page after it
ends = sorted(w['b'] for b in tl['beats'] for w in b['words'])
for s in spans:
    said = [e for e in ends if s[0] < e <= s[1] + .3]
    if said: s[1] = min(s[1], said[-1] + .25)
# Score level: down before each stretch of speech, back up after it
gain = np.ones(N); t = np.arange(N) / SR
for a, b in spans:
    down = np.clip((t - (a - DOWN)) / DOWN, 0, 1); up = np.clip((t - b) / UP, 0, 1)
    dip = (.5 - .5 * np.cos(np.pi * down)) * (.5 + .5 * np.cos(np.pi * up))        # 1 while speaking, eased at both ends
    gain = np.minimum(gain, 1 - (1 - DUCK) * dip)
fade = np.minimum(1, t / .4) * np.clip((tl['duration'] - t) / 1.2, 0, 1)
mix = score * (gain * fade)[:, None] + sfx * SFX * (.7 + .3 * gain[:, None]) + speech
peak = np.abs(mix).max()
if peak > .98:
    mix *= .98 / peak
with wave.open(sys.argv[6], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype('<i2').tobytes())
rms = lambda v: 20 * np.log10(np.sqrt(np.mean(v ** 2)) + 1e-9)
on = np.abs(speech[:, 0]) > .01; free = gain > .98
print(f"score: {'track ' + track if track else 'synthesized'} | speech {rms(speech[on, 0]):.1f} dBFS | score under speech {rms((score * gain[:, None])[on].mean(1)):.1f} | score where nobody speaks {rms(score[free].mean(1)):.1f} ({free.sum() / SR:.1f}s) | peak {peak:.2f}" + ('' if vo_file else ' | voice-over not recorded yet'))
print('  speech stretches: ' + ', '.join(f'{a:.1f}-{b:.1f}s' for a, b in spans))
print('  score level through the film (dB below full): ' + ', '.join(f'{x:.0f}s {20 * np.log10(gain[int(x * SR)] * fade[int(x * SR)] + 1e-9):.0f}' for x in np.arange(0, tl['duration'] - .5, 4)))
