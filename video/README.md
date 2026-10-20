# FixByte Studio — 30 s promo

Deterministic, code-driven edit: `promo.html` renders any frame from a time `t`; `render.mjs`
captures 900 frames (30 fps) with headless Chromium and encodes them with ffmpeg together with the music.

## Outputs
- `out/fixbyte-studio-promo-16x9.mp4` — 1920×1080, 30 fps, H.264 + AAC
- `out/fixbyte-studio-promo-9x16.mp4` — 1080×1920 re-layout for Reels / Shorts

## Rebuild
```bash
python3 prep.py                 # crops + upscaled logo -> build/
node render.mjs                 # 16:9
node render.mjs --v             # 9:16
node render.mjs --stills 8.3,28.9   # preview frames -> out/stills/
```
Needs Node + Playwright (Chromium), ffmpeg, Python 3 with Pillow/numpy, fonts Inter Display + JetBrains Mono.

## Beat grid
Measured from the track: **120 BPM** (beat 0.50 s), first beat at 0.24 s, drop at **8.24 s**.
Scene cuts sit on bar downbeats: 0 · 4.24 · 8.24 · 16.24 · 22.24 · 26.24 · 30.0.

| Time | Scene |
|---|---|
| 0.00–4.24 | Hook — scan line, `72:00:00`, “Your business. / Online. / In 72 hours.” |
| 4.24–8.24 | Build — hero in a tilted browser, line geometry per beat, zoom-blur + white flash |
| 8.24–16.24 | Drop — laptop/phone montage (whip-pans, diagonal wipes; phones use the mobile captures `cafe-phone.png` / `travel-phone.png`), marquee |
| 16.24–22.24 | Services — five equal cards from `service-full-screenshot.png` (3 + 2, bottom row centred) snap in every 2 beats with STRATEGY · DESIGN · DEVELOPMENT · AI · MOTION |
| 22.24–26.24 | Method — cards 01→04 on consecutive beats, captions, collapse to centre |
| 26.24–30.00 | Tagline hits, FixByte → Studio lockup, light sweep, URL + “Free trial”, clean hold from 28.8 s |
