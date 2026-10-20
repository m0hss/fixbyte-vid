// Renders promo.html frame by frame with headless Chromium and pipes the frames into ffmpeg.
//   node render.mjs                 -> out/fixbyte-studio-promo-16x9.mp4
//   node render.mjs --v             -> out/fixbyte-studio-promo-9x16.mp4
//   node render.mjs --stills 1,8.5  -> out/stills/*.png (quick previews)
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

const here = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const vertical = args.includes('--v');
const stillsArg = args.includes('--stills') ? args[args.indexOf('--stills') + 1] : null;
const W = vertical ? 1080 : 1920, H = vertical ? 1920 : 1080;
const FPS = 30, DUR = 30, FRAMES = FPS * DUR;
const outDir = join(here, 'out');
mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH || undefined,
  args: ['--allow-file-access-from-files', '--force-color-profile=srgb', '--disable-lcd-text', '--font-render-hinting=none'],
});
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
page.on('console', m => console.log('[page]', m.text()));
page.on('pageerror', e => { console.error('[pageerror]', e); process.exit(1); });
await page.goto(pathToFileURL(join(here, 'promo.html')).href + (vertical ? '?v=1' : ''));
await page.evaluate(() => window.ready);

const frame = async t => {
  await page.evaluate(tt => window.render(tt), t);
  return page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: W, height: H } });
};

if (stillsArg) {
  const dir = join(outDir, 'stills'); mkdirSync(dir, { recursive: true });
  for (const s of stillsArg.split(',')) {
    writeFileSync(join(dir, `${vertical ? 'v' : 'h'}-${Number(s).toFixed(2)}.png`), await frame(Number(s)));
  }
  await browser.close();
  process.exit(0);
}

const music = join(here, '..', 'assets', 'music', 'jonasblakewood-cyberpunk-cyberpunk-music-528055.mp3');
const out = join(outDir, `fixbyte-studio-promo-${vertical ? '9x16' : '16x9'}.mp4`);
const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error',
  '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
  '-i', music,
  '-filter_complex',
  // low-opacity temporal film grain; music trimmed to 0:00–0:30 with a 1.5 s fade-out
  `[0:v]noise=c0s=5:c0f=t+u,format=yuv420p[v];[1:a]atrim=0:${DUR},asetpts=PTS-STARTPTS,afade=t=out:st=${DUR - 1.5}:d=1.5[a]`,
  '-map', '[v]', '-map', '[a]',
  '-c:v', 'libx264', '-preset', 'slow', '-crf', '19', '-maxrate', '14M', '-bufsize', '28M', '-tune', 'grain', '-profile:v', 'high', '-r', String(FPS),
  '-c:a', 'aac', '-b:a', '256k', '-t', String(DUR), '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });

const t0 = Date.now();
for (let i = 0; i < FRAMES; i++) {
  const buf = await frame(i / FPS);
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  if (i % 60 === 0) console.log(`frame ${i}/${FRAMES}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
}
ff.stdin.end();
await new Promise(r => ff.on('close', r));
await browser.close();
console.log('wrote', out);
