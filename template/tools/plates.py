# Cuts every moving shot of the timeline into 1080x1920 frames at the film's rate:
#   - the host's clips, whole and at their own speed (their sound is lip-synced);
#   - stock video, through a 9:16 window that pans across it;
#   - still pictures with a "move": a camera travelling through the picture, near things sliding past far
#     ones according to the depth map made by enhance.py.
# Usage: plates.py <timeline.js> <rawDir> <clipsDir> <hdDir> <outDir>
import json, os, re, shutil, subprocess, sys
from multiprocessing import Pool
import cv2
import numpy as np

tl = json.loads(re.sub(r'^[^{]*', '', open(sys.argv[1], encoding='utf-8').read()).strip().rstrip(';'))
raw, clips, hd, out = sys.argv[2:6]
FPS = tl['fps']; W, H = 1080, 1920
# Camera moves: zoom from..to, focus point from..to (shares of the picture), sideways/vertical travel (share of
# the picture's width that near things slide against far ones), and how much nearer things grow on a push.
MOVES = {
    'push':  dict(zoom=(1.06, 1.26), focus=(.5, .5, .5, .5), travel=(0, 0), dolly=.15),
    'pull':  dict(zoom=(1.26, 1.06), focus=(.5, .5, .5, .5), travel=(0, 0), dolly=-.15),
    'rise':  dict(zoom=(1.10, 1.17), focus=(.5, .62, .5, .42), travel=(0, .024), dolly=.06),
    'sink':  dict(zoom=(1.17, 1.10), focus=(.5, .40, .5, .60), travel=(0, -.024), dolly=-.06),
    'left':  dict(zoom=(1.12, 1.15), focus=(.57, .5, .43, .5), travel=(-.03, 0), dolly=.04),
    'right': dict(zoom=(1.12, 1.15), focus=(.43, .5, .57, .5), travel=(.03, 0), dolly=.04),
    'orbit': dict(zoom=(1.12, 1.18), focus=(.5, .5, .5, .5), travel=(.034, 0), dolly=.08),
}


def find(folder, name):
    return next(os.path.join(folder, f) for f in sorted(os.listdir(folder)) if os.path.splitext(f)[0] == name)


def frames_of(s):
    film = s['t1'] - s['t0']
    return round(film * FPS) + 2 if 'clip' in s else round((film + .5) * FPS)


def stamp_of(s, src):
    return json.dumps([src, s.get('src'), s.get('x'), s.get('grade'), s.get('move'), s.get('focus'), s.get('zoom'), s.get('lead'), frames_of(s), FPS, 'v2', os.path.getmtime(src)])


def footage(s, d):
    film = s['t1'] - s['t0']; n = frames_of(s); src0, src1 = s['src']
    if 'clip' in s:
        src = find(clips, s['clip']); lead = s.get('lead', 0); n -= round(lead * FPS)
        # The host's footage plays at its own speed; light denoise, sharpen after upscaling
        vf = f"fps={FPS},hqdn3d=1.5:1.5:3:3,scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},unsharp=7:7:0.7"
    else:
        src = os.path.join(raw, s['video'] + '.mp4'); speed = (src1 - src0) / film; x0, x1 = s['x']
        pan = f"(iw*({x0}+({x1}-{x0})*min(t/{film + .5:.3f}\\,1))-ow/2)"
        vf = (f"setpts=PTS/{speed:.5f},fps={FPS},crop=ih*9/16:ih:'max(0\\,min(iw-ow\\,{pan}))':0,"
              f"scale={W}:{H}:flags=lanczos,unsharp=5:5:0.6" + (',' + s['grade'] if s.get('grade') else ''))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(src0), '-i', src, '-vf', vf, '-frames:v', str(n), '-q:v', '3', os.path.join(d, 't_%05d.jpg')], check=True)
    got = sorted(f for f in os.listdir(d) if f.startswith('t_'))
    hold = round(s.get('lead', 0) * FPS)                   # before a clip starts (the door opening), its first frame holds
    for k in range(1, frames_of(s) + 1):
        j = min(max(k - hold, 1), len(got)); shutil.copy(os.path.join(d, got[j - 1]), os.path.join(d, f'p_{k:05d}.jpg'))
    for f in got:
        os.remove(os.path.join(d, f))


def camera(s, d):
    m = {**MOVES[s['move']]}
    if 'zoom' in s: m['zoom'] = s['zoom']
    if 'focus' in s:                                       # a point of interest the move is centred on, or an explicit start and end
        f = s['focus']; a = m['focus']
        m['focus'] = f if len(f) == 4 else (a[0] - .5 + f[0], a[1] - .5 + f[1], a[2] - .5 + f[0], a[3] - .5 + f[1])
    img = cv2.imread(os.path.join(hd, s['photo'] + '.jpg')); ih, iw = img.shape[:2]
    depth = cv2.imread(os.path.join(hd, s['photo'] + '.depth.png'), cv2.IMREAD_UNCHANGED).astype(np.float32) / 65535
    # Near things are widened a little and every depth edge is softened: the picture then stretches smoothly where
    # depth changes instead of tearing, and the stretch falls on the plainer background
    depth = cv2.dilate(cv2.resize(depth, (iw, ih), interpolation=cv2.INTER_CUBIC), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (iw // 110 | 1, iw // 110 | 1)))
    depth = cv2.GaussianBlur(depth, (0, 0), iw / 95)
    cover = max(W / iw, H / ih); n = frames_of(s)
    u, v = np.meshgrid(np.arange(W, dtype=np.float32) - W / 2, np.arange(H, dtype=np.float32) - H / 2)
    fx0, fy0, fx1, fy1 = m['focus']
    # The depth the camera looks at stays still; things nearer or farther slide around it
    cx, cy = int((fx0 + fx1) / 2 * iw), int((fy0 + fy1) / 2 * ih); r = int(.12 * iw)
    d0 = float(np.median(depth[max(cy - r, 0):cy + r, max(cx - r, 0):cx + r]))
    for k in range(n):
        p = k / max(n - 1, 1); e = p * p * (3 - 2 * p) * .7 + p * .3; q = e - .5
        scale = cover * (m['zoom'][0] + (m['zoom'][1] - m['zoom'][0]) * e)
        fx, fy = (fx0 + (fx1 - fx0) * e) * iw, (fy0 + (fy1 - fy0) * e) * ih
        # Keep the window inside the picture
        fx = min(max(fx, W / 2 / scale + .03 * iw), iw - W / 2 / scale - .03 * iw) if iw * scale > W * 1.07 else iw / 2
        fy = min(max(fy, H / 2 / scale + .03 * ih), ih - H / 2 / scale - .03 * ih) if ih * scale > H * 1.07 else ih / 2
        bx, by = fx + u / scale, fy + v / scale
        sx, sy = bx, by
        for _ in range(3):
            dd = np.clip(cv2.remap(depth, sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE) - d0, -.45, .45)
            sx = bx + dd * (m['travel'][0] * iw * 2 * q - (bx - fx) * m['dolly'] * 2 * q)
            sy = by + dd * (m['travel'][1] * iw * 2 * q - (by - fy) * m['dolly'] * 2 * q)
        frame = cv2.remap(img, sx, sy, cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
        cv2.imwrite(os.path.join(d, f'p_{k + 1:05d}.jpg'), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])


def build(s):
    d = os.path.join(out, s['id'])
    src = find(clips, s['clip']) if 'clip' in s else os.path.join(raw, s['video'] + '.mp4') if 'video' in s else os.path.join(hd, s['photo'] + '.jpg')
    stamp = stamp_of(s, src)
    if os.path.exists(d + '/.stamp') and open(d + '/.stamp').read() == stamp:
        return None
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    (camera if 'move' in s else footage)(s, d)
    open(d + '/.stamp', 'w').write(stamp)
    return f"{s['id']} {os.path.basename(src)} {frames_of(s)} frames" + (f" ({s['move']})" if 'move' in s else '')


if __name__ == '__main__':
    todo = [s for s in tl['shots'] if 'video' in s or 'clip' in s or 'move' in s]
    with Pool(4) as pool:
        for line in pool.imap_unordered(build, todo):
            if line:
                print(line, flush=True)
