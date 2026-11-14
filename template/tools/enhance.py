# Prepares the still pictures that get a camera move: small ones are upscaled (Real-ESRGAN, in overlapping
# tiles) and each gets a depth map (Depth Anything V2 small), so plates.py can move a camera through it.
# Usage: enhance.py <modelsDir> <outDir> <rawDir> <timeline.js>
#   Writes <outDir>/<name>.jpg (about 2100 px on the short side when upscaled) and <outDir>/<name>.depth.png
#   The upscaler is in modelsDir/sr; the depth model (99 MB) is downloaded there on first use. Without it the
#   moves still work, as plain zooms and pans with no parallax.
import json, os, re, subprocess, sys
import numpy as np
import onnxruntime as ort
from PIL import Image

models, out, raw = sys.argv[1:4]
tl = json.loads(re.sub(r'^[^{]*', '', open(sys.argv[4], encoding='utf-8').read()).strip().rstrip(';'))
os.makedirs(out, exist_ok=True)
DEPTH_URL = 'https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx'
TILE, STEP = 128, 96
todo = []
for name in sorted({s['photo'] for s in tl['shots'] if 'move' in s}):
    src = os.path.join(raw, name + '.jpg'); dst = os.path.join(out, name + '.jpg')
    if not (os.path.exists(dst) and os.path.exists(dst[:-4] + '.depth.png') and os.path.getmtime(dst) >= os.path.getmtime(src)):
        todo.append((name, src, dst))
if not todo:
    sys.exit()
SR = ort.InferenceSession(os.path.join(models, 'sr', 'model.onnx'), providers=['CPUExecutionProvider'])
depth_path = os.path.join(models, 'depth_small.onnx')
if not os.path.exists(depth_path):
    print('downloading the depth model (99 MB, once)...', flush=True)
    if subprocess.run(['curl', '-sS', '-L', '-f', '-m', '900', '-o', depth_path + '.part', DEPTH_URL]).returncode == 0:
        os.replace(depth_path + '.part', depth_path)
DEPTH = ort.InferenceSession(depth_path, providers=['CPUExecutionProvider']) if os.path.exists(depth_path) else None
if DEPTH is None:
    print('no depth model: camera moves will be flat zooms and pans')


def upscale(im):
    # x4 in 128 px tiles; tiles overlap and are blended with a soft window so no seams show
    a = np.asarray(im).astype(np.float32) / 255; h, w = a.shape[:2]
    ph, pw = max(TILE, h), max(TILE, w)
    a = np.pad(a, ((0, ph - h), (0, pw - w), (0, 0)), mode='reflect')
    ys = sorted(set(list(range(0, ph - TILE, STEP)) + [ph - TILE])); xs = sorted(set(list(range(0, pw - TILE, STEP)) + [pw - TILE]))
    acc = np.zeros((ph * 4, pw * 4, 3), np.float32); wsum = np.zeros((ph * 4, pw * 4, 1), np.float32)
    ramp = np.minimum(np.arange(TILE * 4) + 1, np.arange(TILE * 4)[::-1] + 1).astype(np.float32); ramp = np.minimum(ramp, 64) / 64
    win = (ramp[:, None] * ramp[None, :])[:, :, None]
    for y in ys:
        for x in xs:
            t = SR.run(None, {'image': a[y:y + TILE, x:x + TILE].transpose(2, 0, 1)[None]})[0][0].transpose(1, 2, 0)
            acc[y * 4:(y + TILE) * 4, x * 4:(x + TILE) * 4] += t * win; wsum[y * 4:(y + TILE) * 4, x * 4:(x + TILE) * 4] += win
    return Image.fromarray(((acc / wsum)[:h * 4, :w * 4].clip(0, 1) * 255).astype(np.uint8))


def depth(im):
    # Relative depth: 1 near, 0 far, at the model's own resolution
    if DEPTH is None:
        return Image.fromarray(np.full((64, 64), 32768, np.uint16))
    w, h = im.size; k = 518 / min(w, h); W, H = int(round(w * k / 14)) * 14, int(round(h * k / 14)) * 14
    x = (np.asarray(im.resize((W, H), Image.BICUBIC)).astype(np.float32) / 255 - [.485, .456, .406]) / [.229, .224, .225]
    d = DEPTH.run(None, {'pixel_values': x.transpose(2, 0, 1)[None].astype(np.float32)})[0][0]
    lo, hi = np.percentile(d, 1), np.percentile(d, 99)
    return Image.fromarray((((d - lo) / (hi - lo + 1e-6)).clip(0, 1) * 65535).astype(np.uint16))


for name, src, dst in todo:
    im = Image.open(src).convert('RGB'); w, h = im.size; note = 'as is'
    if min(w, h) < 1500:
        im = upscale(im); k = 2100 / min(im.size)                      # x4 is more than a 1080x1920 frame needs
        if k < 1:
            im = im.resize((round(im.size[0] * k), round(im.size[1] * k)), Image.LANCZOS)
        note = f'upscaled from {w}x{h}'
    im.save(dst, quality=93); depth(im).save(dst[:-4] + '.depth.png')
    print(name, f'{im.size[0]}x{im.size[1]}', note, flush=True)
