# Finds when each word of the script is really spoken, in the host's clips and in the voice-over,
# so every caption, counter and cut follows the speech.
# Usage: align.py <episode.json> <clipsDir> <out words.json> [voice-over file]
import json, os, re, subprocess, sys
from difflib import SequenceMatcher
import numpy as np

ep = json.load(open(sys.argv[1], encoding='utf-8'))
clips_dir, out_path = sys.argv[2], sys.argv[3]
vo_file = sys.argv[4] if len(sys.argv) > 4 else None
SR, HOP = 16000, 160


def audio(path):
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.float32)


def hear(path):
    # Word times that came with a generated voice (tools/voice.py) need no transcription
    side = os.path.splitext(path)[0] + '.words.json'
    if os.path.exists(side) and os.path.getmtime(side) >= os.path.getmtime(path) - 1:
        return json.load(open(side, encoding='utf-8'))
    # Otherwise transcribe, and keep the result beside the build so a rebuild does not transcribe again
    cache = os.path.join('build', 'heard', os.path.basename(path) + '.json'); stamp = os.path.getmtime(path)
    if os.path.exists(cache):
        got = json.load(open(cache, encoding='utf-8'))
        if got['stamp'] == stamp:
            return got['words']
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit(f'{path} has to be transcribed for its word times: pip install faster-whisper')
    segs, _ = WhisperModel('turbo', device='cpu', compute_type='int8').transcribe(audio(path), language='ar', word_timestamps=True, vad_filter=False, beam_size=5)
    words = [{'w': w.word.strip(), 'a': round(w.start, 2), 'b': round(w.end, 2)} for s in segs for w in s.words]
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    json.dump({'stamp': stamp, 'words': words}, open(cache, 'w', encoding='utf-8'), ensure_ascii=False)
    return words


def norm(w):
    w = re.sub(r'[ً-ْـ]', '', w)
    w = w.translate(str.maketrans('أإآٱةىؤئ٠١٢٣٤٥٦٧٨٩', 'ااااهيوي0123456789'))
    return re.sub(r'[^\w]', '', w).lower()


def sim(a, b):
    if not a or not b:
        return 0
    if a.isdigit() or b.isdigit():
        return 1.0 if a == b else .55        # a number may be a word in the script and digits to the transcriber
    return SequenceMatcher(None, a, b).ratio()


def pauses(x):
    # Silent stretches of at least 0.12 s
    db = 20 * np.log10(np.sqrt(np.mean(x[:len(x) // HOP * HOP].reshape(-1, HOP) ** 2, axis=1)) + 1e-7)
    quiet = db < np.percentile(db, 90) - 32; runs = []; i = 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]: j += 1
            if (j - i) * HOP / SR >= .12: runs.append((i * HOP / SR, j * HOP / SR))
            i = j
        else:
            i += 1
    return runs


def match(script, heard, runs, label):
    # script: [(beat, word)]. One script word to one heard word, or to two (T1 -> "تي واحد"),
    # or two script words to one heard, or a skip.
    S = [norm(w) for _, w in script]; H = [norm(h['w']) for h in heard]; n, m = len(S), len(H)
    best = np.full((n + 1, m + 1), -1e9); back = {}; best[0, 0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            if best[i, j] < -1e8:
                continue
            moves = []
            if i < n and j < m: moves.append((1, 1, sim(S[i], H[j])))
            if i < n and j + 1 < m: moves.append((1, 2, sim(S[i], H[j] + H[j + 1]) - .1))
            if i + 1 < n and j < m: moves.append((2, 1, sim(S[i] + S[i + 1], H[j]) - .1))
            if i < n: moves.append((1, 0, -.6))
            if j < m: moves.append((0, 1, -.6))
            for di, dj, sc in moves:
                if best[i, j] + sc > best[i + di, j + dj]:
                    best[i + di, j + dj] = best[i, j] + sc; back[(i + di, j + dj)] = (i, j)
    path = []; cur = (n, m)
    while cur != (0, 0):
        path.append((back[cur], cur)); cur = back[cur]
    times = [None] * n
    for (i0, j0), (i1, j1) in reversed(path):
        if i1 == i0:
            print(f'  {label}: extra word heard "{heard[j0]["w"]}" at {heard[j0]["a"]}s'); continue
        if j1 == j0:
            print(f'  {label}: not heard "{script[i0][1]}"'); continue
        a, b = heard[j0]['a'], heard[j1 - 1]['b']
        if i1 - i0 == 2:
            cut = a + (b - a) * len(S[i0]) / max(1, len(S[i0]) + len(S[i0 + 1]))
            times[i0], times[i0 + 1] = [a, cut], [cut, b]
        else:
            times[i0] = [a, b]; said = ' '.join(h['w'] for h in heard[j0:j1])
            if sim(S[i0], norm(said)) < .99:
                print(f'  {label}: "{script[i0][1]}" heard as "{said}" at {a}s')
    for i in range(n):                        # an unheard word takes no time, right after the word before it
        if times[i] is None:
            t = times[i - 1][1] if i else 0; times[i] = [t, t]
    # The transcriber gives each word the silence around it: trim words back to where the sound is
    for t in times:
        for a, b in runs:
            if a <= t[0] + .15 and t[0] < b < t[1]: t[0] = b
            if b >= t[1] - .15 and t[0] < a < t[1]: t[1] = a
    out = {}
    for (bn, w), t in zip(script, times):
        out.setdefault(str(bn), []).append({'w': w, 'a': round(t[0], 3), 'b': round(t[1], 3)})
    return out


result = {'clips': {}}
for n, b in enumerate(ep['beats']):
    if 'clip' in b:
        path = next(os.path.join(clips_dir, f) for f in sorted(os.listdir(clips_dir)) if os.path.splitext(f)[0] == b['clip'])
        s0, s1 = b['src']; heard = [h for h in hear(path) if s0 - .2 <= h['a'] < s1]
        result['clips'][str(n)] = match([(n, w) for w in b['say'].split()], heard, pauses(audio(path)), f'clip {b["clip"]}')[str(n)]
if vo_file:
    script = [(n, w) for n, b in enumerate(ep['beats']) if 'clip' not in b and 'say' in b for w in b['say'].split()]
    x = audio(vo_file)
    result['vo'] = {'file': vo_file, 'length': round(len(x) / SR, 3), 'beats': match(script, hear(vo_file), pauses(x), 'voice-over')}
json.dump(result, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"{len(result['clips'])} clip(s) aligned; voice-over " + (f"{result['vo']['length']}s aligned" if vo_file else 'not given'))
