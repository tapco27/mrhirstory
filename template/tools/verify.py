# Measures the finished reel. Stills can be looked at but sound cannot be heard here, so this reports what
# can be measured: loudness and peak, whether each voice sits where the timeline put it, and a contact sheet
# with one frame at every beat and every graphic.
# Usage: verify.py <reel.mp4> [voice-over file]     (run from the project folder, after a build)
import json, os, re, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

reel = sys.argv[1]; vo = sys.argv[2] if len(sys.argv) > 2 else None
tl = json.loads(re.sub(r'^[^{]*', '', open('src/timeline.js', encoding='utf-8').read()).strip().rstrip(';'))
find = lambda folder, name: next(os.path.join(folder, f) for f in sorted(os.listdir(folder)) if os.path.splitext(f)[0] == name)


def envelope(path, extra=()):
    x = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', *extra, '-i', path, '-vn', '-ac', '1', '-ar', '8000', '-f', 'f32le', '-'], capture_output=True, check=True).stdout, np.float32)
    return np.convolve(np.abs(x), np.ones(80) / 80, 'same')[::8]                 # one value per millisecond


def offset(mix, ref, at):
    # How far (ms) the reference sits from second `at` of the mix: best match of a stretch from its middle
    n = len(ref); a, b = int(n * .25), int(n * .25) + min(20000, n // 2); best = (0, -1.0)
    for lag in range(-400, 401, 2):
        w = mix[int(at * 1000) + a + lag:int(at * 1000) + b + lag]
        if len(w) == b - a:
            r = float(np.corrcoef(w, ref[a:b])[0, 1])
            if r > best[1]: best = (lag, r)
    return best


info = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate:format=duration,size', '-of', 'csv=p=0', reel], capture_output=True, text=True).stdout.split()
print('file:', ' '.join(info).replace(',', ' '), f'| planned {tl["duration"]}s')
log = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', reel, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
print('loudness:', re.findall(r'I:\s+(-?[\d.]+) LUFS', log)[-1], 'LUFS (target -14) | peak', re.findall(r'Peak:\s+(-?[\d.]+) dBFS', log)[-1], 'dBFS (keep under -1)')
mix = envelope(reel)
for c in tl['clips']:
    lag, r = offset(mix, envelope(find('assets/clips', c['file']), ['-ss', str(c['src'][0]), '-to', str(c['src'][1])]), c['t0'])
    print(f"clip {c['file']}: sound {lag} ms from its picture (match {r:.2f}; over 40 ms shows as a lip-sync error)")
if vo:
    lag, r = offset(mix, envelope(vo), tl['voAt'])
    print(f'voice-over: {lag} ms from its planned place (match {r:.2f})')
# Contact sheet: one frame shortly after every beat starts and every graphic lands
times = sorted({round(b['t0'] + .6, 1) for b in tl['beats']} | {round(c['at'] + .7, 1) for b in tl['beats'] for c in b['cards']} | {round(tl['duration'] - .5, 1)})
os.makedirs('build/chk', exist_ok=True); tiles = []
for t in times:
    f = f'build/chk/v_{t:06.1f}.jpg'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', reel, '-frames:v', '1', '-vf', 'scale=216:384', '-q:v', '4', f])
    im = Image.open(f); ImageDraw.Draw(im).text((6, 4), f'{t}s', fill='#0f0'); tiles.append(im)
cols = 12; sheet = Image.new('RGB', (cols * 216, ((len(tiles) + cols - 1) // cols) * 384))
for k, im in enumerate(tiles):
    sheet.paste(im, ((k % cols) * 216, (k // cols) * 384))
sheet.save('build/chk/verify.jpg', quality=86); print(f'{len(tiles)} frames -> build/chk/verify.jpg (look at it)')
