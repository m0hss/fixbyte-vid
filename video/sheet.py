"""Tile still frames into contact sheets for review: python3 sheet.py out/stills h"""
import sys, glob, os
from PIL import Image, ImageDraw
d, pre = sys.argv[1], sys.argv[2]
fs = sorted(glob.glob(f'{d}/{pre}-*.png'), key=lambda f: float(os.path.basename(f)[2:-4]))
per = 4 if pre == 'h' else 6
for k in range(0, len(fs), per):
    ims = [Image.open(f).convert('RGB') for f in fs[k:k + per]]
    tw = 960 if pre == 'h' else 360
    th = ims[0].height * tw // ims[0].width
    cols = 2 if pre == 'h' else 6
    rows = (len(ims) + cols - 1) // cols
    S = Image.new('RGB', (tw * cols + 6 * (cols - 1), th * rows + 6 * (rows - 1)), (255, 0, 255))
    for i, (im, f) in enumerate(zip(ims, fs[k:k + per])):
        im = im.resize((tw, th), Image.LANCZOS)
        ImageDraw.Draw(im).text((8, 8), os.path.basename(f), fill=(255, 255, 0))
        S.paste(im, ((i % cols) * (tw + 6), (i // cols) * (th + 6)))
    S.save(f'{d}/sheet-{pre}-{k // per:02d}.jpg', quality=88)
