# Builds a contact sheet from review stills. Usage: sheet.py <stillsDir> <out.jpg> [cols]
import sys, glob, os
from PIL import Image, ImageDraw
files = sorted(glob.glob(os.path.join(sys.argv[1], '*.jpg')))
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 6
w, h = 360, 640
rows = (len(files) + cols - 1) // cols
sheet = Image.new('RGB', (cols * w, rows * h), '#111')
for i, f in enumerate(files):
    im = Image.open(f).resize((w, h), Image.LANCZOS)
    ImageDraw.Draw(im).text((8, 6), os.path.basename(f)[2:8] + 's', fill='#0f0')
    sheet.paste(im, ((i % cols) * w, (i // cols) * h))
sheet.save(sys.argv[2], quality=88)
print(len(files), 'stills')
