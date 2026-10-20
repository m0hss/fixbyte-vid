"""Derive crops and an upscaled logo from ../assets into ./build."""
import os
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(ROOT, '..', 'assets')
B = os.path.join(ROOT, 'build')
os.makedirs(B, exist_ok=True)


def shot(name):
    return Image.open(os.path.join(A, 'screenshots', name)).convert('RGB')


def save(im, name):
    im.save(os.path.join(B, name), optimize=True)
    print(name, im.size)


# --- FixByte logo: 4x upscale with re-sharpened alpha (source is only 300x140)
logo = Image.open(os.path.join(A, 'logo-fixbyte.png')).convert('RGBA').crop((24, 26, 276, 116))
big = logo.resize((logo.width * 4, logo.height * 4), Image.BICUBIC)
arr = np.array(big).astype(np.float32)
al = arr[:, :, 3] / 255.0
al = np.clip((al - 0.5) * 3.2 + 0.5, 0, 1)            # steepen the soft edge
al = np.array(Image.fromarray((al * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.1))) / 255.0
teal = (arr[:, :, 0] < 140) & (arr[:, :, 3] > 30)
rgb = np.zeros_like(arr[:, :, :3]) + 255
rgb[teal] = (0, 167, 154)               # same teal as the Studio mark
rgb = np.array(Image.fromarray(rgb.astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)))
out = np.dstack([rgb, (al * 255).astype(np.uint8)])
save(Image.fromarray(out.astype(np.uint8), 'RGBA'), 'logo-fixbyte@4x.png')
stu = Image.open(os.path.join(A, 'logo-studio.png')).convert('RGBA').crop((24, 45, 816, 296))
save(stu, 'logo-studio.png')

# --- Hero: trim the page's black side margins so the browser frame shows the hero card
save(shot('hero.png').crop((190, 0, 1704, 944)), 'hero.png')

# --- Marquee cards (410x410 each, uniform pitch)
mq = shot('templates marquee.png')
for i, (x, y) in enumerate([(400, 48), (834, 48), (495, 482), (929, 482)]):
    save(mq.crop((x, y, x + 410, y + 410)), f'mq{i}.png')

# --- Services tiles
sv = shot('services.png')
for i, box in enumerate([(211, 197, 683, 725), (707, 197, 1179, 725), (1203, 197, 1675, 725),
                         (211, 749, 931, 932), (955, 749, 1675, 932)]):
    save(sv.crop(box), f'svc{i}.png')

# --- Method cards: flood-fill each card from a seed point, then fill its holes (text, icons) row by row
mc = np.array(shot('method-cards.png')).astype(np.int32)
lum = mc.mean(2)


def flood(mask, seed):
    comp = np.zeros_like(mask)
    comp[seed[1], seed[0]] = True
    while True:
        grown = comp.copy()
        grown[1:] |= comp[:-1]; grown[:-1] |= comp[1:]
        grown[:, 1:] |= comp[:, :-1]; grown[:, :-1] |= comp[:, 1:]
        grown &= mask
        if (grown == comp).all():
            return comp
        comp = grown


def fill_holes(m):
    out = m.copy()
    for r in range(m.shape[0]):
        cols = np.where(m[r])[0]
        if len(cols):
            out[r, cols[0]:cols[-1] + 1] = True
    return out


# region of interest keeps the flood fills cheap
X0, Y0, X1, Y1 = 370, 235, 1480, 575
roi = lum[Y0:Y1, X0:X1]
seeds = [((390, 380), roi > 250), ((675, 380), roi < 40), ((960, 380), roi > 250), ((1300, 380), roi < 40)]
comps = [fill_holes(flood(mask, (sx - X0, sy - Y0))) for (sx, sy), mask in seeds]
over = np.array(Image.fromarray((comps[3] * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))) > 0
comps[2] &= ~over                                        # card 04 overlaps card 03
rows = np.where(comps[3].any(1))[0][20:-20]              # cut 03 along 04's (tilted) left edge
firsts = np.array([np.where(comps[3][r])[0][0] for r in rows])
a, b = np.polyfit(rows, firsts, 1)
yy, xx = np.mgrid[0:comps[2].shape[0], 0:comps[2].shape[1]]
comps[2] &= xx < a * yy + b - 3
for i, comp in enumerate(comps):
    alpha = Image.fromarray((comp * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.6))
    im = Image.fromarray(np.dstack([mc[Y0:Y1, X0:X1].astype(np.uint8), np.array(alpha)]), 'RGBA')
    bb = im.getbbox()
    print('card', i, 'offset', X0 + bb[0], Y0 + bb[1])
    save(im.crop(bb), f'method{i}.png')
