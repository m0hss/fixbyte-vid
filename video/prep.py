"""Derive crops and an upscaled logo from ../assets into ./build."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

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

sv = shot('service-full-screenshot.png')

# --- Services: the five 3D objects cut out of their cards (alpha from distance to the card grey)
sva = np.array(sv).astype(np.int32)
for i, (x0, y0, x1, y1) in enumerate([(214, 160, 572, 445), (610, 160, 968, 445), (1006, 150, 1364, 445),
                                      (214, 600, 770, 885), (809, 600, 1365, 885)]):
    reg = sva[y0:y1, x0:x1]
    diff = np.abs(reg - 17).max(2)
    ys, xs = np.where(diff > 22)
    m = 24
    bx0, by0 = max(0, xs.min() - m), max(0, ys.min() - m)
    bx1, by1 = min(reg.shape[1], xs.max() + m), min(reg.shape[0], ys.max() + m)
    crop = reg[by0:by1, bx0:bx1]
    al = np.clip((np.abs(crop - 17).max(2) - 8) / 18, 0, 1)
    ell = Image.new('L', (crop.shape[1], crop.shape[0]), 0)
    ImageDraw.Draw(ell).ellipse((4, 4, crop.shape[1] - 4, crop.shape[0] - 4), fill=255)
    ell = np.array(ell.filter(ImageFilter.GaussianBlur(10))) / 255
    al = np.array(Image.fromarray((al * ell * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7)))
    save(Image.fromarray(np.dstack([crop.astype(np.uint8), al]), 'RGBA'), f'obj{i}.png')

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
cards = []
for i, comp in enumerate(comps):
    alpha = Image.fromarray((comp * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.6))
    im = Image.fromarray(np.dstack([mc[Y0:Y1, X0:X1].astype(np.uint8), np.array(alpha)]), 'RGBA')
    cards.append(im.crop(im.getbbox()))

# card 03: card 04 covered its right edge; continue each row with the blank right edge of card 01
# (same card style and size), seamed just inside 03's last opaque pixel
c1 = np.array(cards[0]); c3 = np.array(cards[2])
fa = c1.copy()
for r in range(min(c1.shape[0], c3.shape[0])):
    cols = np.where(c3[r, :, 3] > 200)[0]
    if len(cols):
        seam = cols[-1] - 3
        fa[r, :seam] = c3[r, :seam]
fa[:, :120, 3] = c3[:, :120, 3]                          # keep 03's own left corners (chamfer)
cards[2] = Image.fromarray(fa, 'RGBA')

# card 04: undo its tilt (angle of the fitted left edge), whichever sign straightens it
def tilt(im):
    al = np.array(im.split()[3]) > 128
    rs = np.where(al.any(1))[0][25:-25]
    return np.polyfit(rs, [np.where(al[r])[0][0] for r in rs], 1)[0]

ang = np.degrees(np.arctan(a))
best = min((cards[3].rotate(sg * ang, Image.BICUBIC, expand=True) for sg in (1, -1)), key=lambda im: abs(tilt(im)))
cards[3] = best.crop(best.getbbox())
print('card 04 tilt', round(ang, 2), 'deg -> residual slope', round(tilt(cards[3]), 4))
# French copy is replaced by English text in promo.html: clear the text area to the flat card colour
for i, im in enumerate(cards):
    arr = np.array(im)
    bg = 255 if i % 2 == 0 else 0
    region = arr[150:arr.shape[0] - 14, 12:arr.shape[1] - 14]
    solid = region[:, :, 3] == 255
    region[solid, :3] = bg
    save(Image.fromarray(arr, 'RGBA'), f'method{i}.png')
