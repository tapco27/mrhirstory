# Builds the story's gate: a stone portal with a pointed arch of two-coloured stones, a plaque for the episode
# title, and a double door of real carved wood (from a public-domain photo). Writes the wall with a hole where
# the door hangs, the two leaves, and the geometry the page needs to swing them open.
# Usage: portal.py <carved wood photo> <outDir>
import json, sys
import cv2
import numpy as np

wood_src = cv2.imread(sys.argv[1]).astype(np.float32) / 255; out = sys.argv[2]
W, H = 2160, 3840
rng = np.random.default_rng(11)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
CX = W / 2
FRAME = (230, 560, 1930, 3470)            # portal frame, left top right bottom
SPRING, HALF, R, BAND = 1660, 640, 832, 170   # arch: springing line, half span, radius of each side, depth of its stones
DOOR = (560, 1980, 1040, 1490)            # door opening: left, top, width, height
PLAQUE = (500, 1640, 1160, 236)
STEP_Y, GROUND_Y = 3470, 3610


def noise(sigma, shape=(H, W)):
    n = cv2.GaussianBlur(rng.normal(0, 1, shape).astype(np.float32), (0, 0), sigma)
    return n / (n.std() + 1e-6)


def emboss(mask, depth=3, soft=1.2):
    # Light from the upper left: a soft dark edge below and right of the mask, a light one above and left
    m = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), soft)
    return np.roll(m, (-depth, -depth), (0, 1)) - np.roll(m, (depth, depth), (0, 1))


def ashlar(base, row, wide, tone=.06):
    # Courses of cut stone: each block its own shade, joints dark with a lit lower edge
    img = np.ones((H, W), np.float32); joints = np.zeros((H, W), np.float32); y = -rng.integers(0, row)
    while y < H:
        h = int(row * rng.uniform(.9, 1.12)); x = -rng.integers(0, wide)
        while x < W:
            w = int(wide * rng.uniform(.7, 1.35))
            img[max(y, 0):y + h, max(x, 0):x + w] = 1 + rng.uniform(-tone, tone)
            if 0 < x < W: joints[max(y, 0):y + h, x - 2:x + 3] = 1
            x += w
        if 0 < y < H: joints[y - 2:y + 3] = 1
        y += h
    shade = 1 - .42 * cv2.GaussianBlur(joints, (0, 0), 2.2) + .10 * np.roll(cv2.GaussianBlur(joints, (0, 0), 1.5), 5, 0)
    return base[None, None, :] * (img * shade * (1 + .05 * noise(46) + .035 * noise(7) + .03 * noise(1.2)))[:, :, None]


STONE, LIGHT, DARK = np.float32([138, 176, 204]) / 255, np.float32([196, 224, 240]) / 255, np.float32([112, 150, 182]) / 255   # BGR
wall = ashlar(STONE, 176, 420)

# ---- Arch geometry: each side is a circle centred beyond the middle, so the two meet in a point ----
cl, cr = CX + (R - HALF), CX - (R - HALF)                     # centres of the left and right sides
d_l = np.hypot(xx - cl, yy - SPRING); d_r = np.hypot(xx - cr, yy - SPRING)
d = np.where(xx < CX, d_l, d_r)                               # distance that defines the arch on each side
above = yy <= SPRING
inside = np.where(above, d < R, np.abs(xx - CX) < HALF) & (yy < STEP_Y)       # the recess under the arch and between the jambs
band = above & (d >= R) & (d < R + BAND)
# Two-coloured arch stones, cut along the radius
ang = np.degrees(np.arctan2(SPRING - yy, np.where(xx < CX, cl - xx, xx - cr)))
seg = np.floor(ang / 9.2).astype(int)
tone = np.where(seg % 2 == 0, 1.0, 0.0)[:, :, None]
vous = (LIGHT[None, None] * tone + DARK[None, None] * (1 - tone)) * (1 + .04 * noise(30) + .03 * noise(1.5))[:, :, None]
cuts = (np.abs(ang / 9.2 - np.round(ang / 9.2)) < .028) & band
vous *= (1 - .45 * cv2.GaussianBlur(cuts.astype(np.float32), (0, 0), 1.6))[:, :, None]
wall = np.where(band[:, :, None], vous, wall)

# ---- Recess: darker stone under the arch, a hood of small niches, and the plaque ----
recess = ashlar(STONE * .86, 150, 330, .04)
hood = inside & above & (yy < PLAQUE[1] - 60)
cell = 132.0                                                  # rows of little pointed niches, each shaded like a hollow
row = np.floor((yy - 700) / (cell * .82)); u = ((xx - CX + (row % 2) * cell / 2) % cell) / cell - .5; v = ((yy - 700) % (cell * .82)) / (cell * .82)
niche = np.clip(1 - (np.abs(u) * 2) ** 1.6 - (1 - v) * .9, 0, 1)
recess = np.where(hood[:, :, None], recess * (.72 + .42 * v + .22 * (niche > 0))[:, :, None], recess)
wall = np.where(inside[:, :, None], recess, wall)

# ---- Frame mouldings, the lintel over the door and its surround ----
lines = np.zeros((H, W), np.float32)
for k, inset in enumerate((0, 34, 62)):
    cv2.rectangle(lines, (FRAME[0] + inset, FRAME[1] + inset), (FRAME[2] - inset, FRAME[3] + 40), 1, 7 if k == 0 else 4)
edge_arch = (np.abs(d - R) < 5) & above | (np.abs(d - R - BAND) < 5) & above | (np.abs(np.abs(xx - CX) - HALF) < 5) & ~above & (yy < STEP_Y)
lines = np.maximum(lines, edge_arch.astype(np.float32))
dx, dy, dw, dh = DOOR
surround = np.zeros((H, W), np.float32); cv2.rectangle(surround, (dx - 74, dy - 74), (dx + dw + 74, STEP_Y), 1, -1); cv2.rectangle(surround, (dx, dy), (dx + dw, STEP_Y), 0, -1)
marble = LIGHT * .97
wall = np.where((surround > 0)[:, :, None], marble[None, None] * (1 + .03 * noise(60) + .02 * noise(2))[:, :, None], wall)
cv2.rectangle(lines, (dx - 74, dy - 74), (dx + dw + 74, STEP_Y + 6), 1, 5); cv2.rectangle(lines, (dx - 30, dy - 30), (dx + dw + 30, STEP_Y + 6), 1, 3)
wall *= (1 + .5 * emboss(lines > 0, 3))[:, :, None]

# ---- Plaque and the two roundels ----
px, py, pw, ph = PLAQUE
GREEN, GOLD = np.float32([40, 62, 18]) / 255, np.float32([98, 186, 226]) / 255
cv2.rectangle(wall, (px - 14, py - 14), (px + pw + 14, py + ph + 14), GOLD.tolist(), -1)
cv2.rectangle(wall, (px, py), (px + pw, py + ph), GREEN.tolist(), -1)
cv2.rectangle(wall, (px + 12, py + 12), (px + pw - 12, py + ph - 12), (GOLD * .9).tolist(), 3)
for sx in (-1, 1):
    c = (int(CX + sx * 640), 860)
    cv2.circle(wall, c, 104, GOLD.tolist(), -1, cv2.LINE_AA); cv2.circle(wall, c, 90, GREEN.tolist(), -1, cv2.LINE_AA)
    pts = np.array([[c[0] + np.cos(a) * (62 if i % 2 == 0 else 47), c[1] + np.sin(a) * (62 if i % 2 == 0 else 47)] for i, a in enumerate(np.arange(16) * np.pi / 8 - np.pi / 2)])
    cv2.fillPoly(wall, [np.int32(pts * 16)], GOLD.tolist(), cv2.LINE_AA, 4)

# ---- Shadows: the recess is set back, so its upper and left edges fall dark ----
dist = cv2.distanceTransform(inside.astype(np.uint8), cv2.DIST_L2, 5)
ao = np.where(inside, np.exp(-dist / 70), 0); ao *= np.clip(1.25 - (yy - 700) / 2400, .45, 1.25)
wall *= (1 - .42 * ao)[:, :, None]

# ---- Step and paving ----
step = (yy >= STEP_Y) & (yy < GROUND_Y)
veins = noise(40) * .5 + cv2.resize(noise(6, (H // 8, W)), (W, H)) * .5
wall = np.where(step[:, :, None], np.float32([232, 236, 238]) / 255 * (1 + .035 * veins - .25 * np.clip((yy - STEP_Y - 96) / 44, 0, 1))[:, :, None], wall)
ground = yy >= GROUND_Y
wall = np.where(ground[:, :, None], ashlar(STONE * .74, 120, 620, .05) * (1 - .25 * (yy - GROUND_Y) / (H - GROUND_Y))[:, :, None], wall)
wall *= (1 - .3 * np.exp(-np.abs(yy - GROUND_Y) / 14))[:, :, None]
# Warm light from the upper left, the corners falling off
wall *= (1.07 - .14 * (xx / W * .5 + yy / H * .5) - .22 * (((xx - CX) / W) ** 2 + ((yy - H / 2) / H) ** 2))[:, :, None]

alpha = np.full((H, W), 255, np.uint8); alpha[dy:dy + dh, dx:dx + dw] = 0
cv2.imwrite(f'{out}/wall.png', np.dstack([np.clip(wall * 255, 0, 255).astype(np.uint8), alpha]), [cv2.IMWRITE_PNG_COMPRESSION, 6])

# ---- Leaves: stiles and rails of plain walnut around panels of the carved wood ----
lw = dw // 2
carve = wood_src[:, 110:1790]                                   # the carved field of the photo, without its plain borders
carve = np.clip((carve - .5) * 1.35 + .5, 0, 1) ** 1.15 * np.float32([.60, .80, 1.02])      # deeper, darker walnut
grain = cv2.GaussianBlur(rng.normal(0, 1, (dh, lw)).astype(np.float32), (0, 0), sigmaX=1.6, sigmaY=70); grain /= grain.std()
plain = np.float32([30, 52, 84]) / 255 * (1 + .16 * grain + .05 * noise(1.0, (dh, lw)))[:, :, None]            # plain walnut, grain running up the leaf
leaf = plain.copy(); stile, rail = 46, 40
pw_, ph_ = lw - 2 * stile, (dh - 2 * stile - rail) // 2
top = cv2.resize(carve[:, :int(carve.shape[0] * pw_ / ph_)] if carve.shape[1] >= carve.shape[0] * pw_ / ph_ else carve, (pw_, ph_), interpolation=cv2.INTER_AREA)
for k, panel in enumerate((top, top[::-1])):
    y0 = stile + k * (ph_ + rail); leaf[y0:y0 + ph_, stile:stile + pw_] = panel
m = np.zeros((dh, lw), np.float32)
for k in range(2):
    y0 = stile + k * (ph_ + rail); cv2.rectangle(m, (stile, y0), (stile + pw_, y0 + ph_), 1, 6)
cv2.rectangle(m, (2, 2), (lw - 3, dh - 3), 1, 5)
leaf *= (1 + .6 * emboss(m > 0, 3))[:, :, None]
leaf *= (1.04 - .14 * np.linspace(0, 1, dh, dtype=np.float32))[:, None, None]
for y in (stile + ph_ // 2, stile + ph_ + rail + ph_ // 2):       # brass studs down the meeting stile
    cv2.circle(leaf, (lw - 23, y), 13, (GOLD * .55).tolist(), -1, cv2.LINE_AA); cv2.circle(leaf, (lw - 26, y - 3), 9, GOLD.tolist(), -1, cv2.LINE_AA)
ring = (lw - 86, stile + ph_ + rail // 2)                        # ring pull at hand height
cv2.circle(leaf, ring, 46, (GOLD * .5).tolist(), 12, cv2.LINE_AA); cv2.circle(leaf, (ring[0] - 3, ring[1] - 3), 46, GOLD.tolist(), 7, cv2.LINE_AA); cv2.circle(leaf, (ring[0], ring[1] - 46), 17, GOLD.tolist(), -1, cv2.LINE_AA)
leaf = np.clip(leaf * 255, 0, 255).astype(np.uint8)
cv2.imwrite(f'{out}/leaf_l.jpg', leaf, [cv2.IMWRITE_JPEG_QUALITY, 93]); cv2.imwrite(f'{out}/leaf_r.jpg', leaf[:, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 93])
geo = {'w': W, 'h': H, 'box': list(DOOR), 'left': lw, 'plaque': list(PLAQUE), 'lamps': [[int(CX - 930), 2060], [int(CX + 930), 2060]]}
open(f'{out}/door.js', 'w').write('window.DOOR = ' + json.dumps(geo) + ';\n')
print('portal', W, H, 'door', DOOR)
