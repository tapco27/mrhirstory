// Captures a film page frame by frame.
// Usage: node render.mjs <page.html> <outDir> <worker> <workers> | node render.mjs <page.html> --stills <outDir> t1,t2,...
import { createRequire } from 'node:module';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const { chromium } = createRequire(import.meta.url)('playwright');
const here = path.dirname(fileURLToPath(import.meta.url));
const url = 'file://' + path.join(here, process.argv[2]);
const args = process.argv.slice(3);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
page.on('pageerror', e => { console.error('PAGE ERROR', e.message); process.exitCode = 1; });
await page.goto(url);
await page.waitForFunction('window.filmReady === true');
const duration = await page.evaluate('window.DURATION');
const FPS = await page.evaluate('window.FPS || 30');

// Stills mode: a handful of timestamps for review
if (args[0] === '--stills') {
  mkdirSync(args[1], { recursive: true });
  for (const t of args[2].split(',').map(Number)) {
    await page.evaluate(x => window.renderAt(x), t);
    await page.screenshot({ path: path.join(args[1], `t_${t.toFixed(2).padStart(6, '0')}.jpg`), type: 'jpeg', quality: 88 });
  }
  await browser.close();
  process.exit();
}

// Frame mode: this worker renders every Nth frame
const [outDir, worker, workers, from = 0, to = duration] = [args[0], +args[1], +args[2], args[3] && +args[3], args[4] && +args[4]].map(v => v === false ? undefined : v);
mkdirSync(outDir, { recursive: true });
const first = Math.round((from ?? 0) * FPS), last = Math.round((to ?? duration) * FPS);
for (let f = first; f < last; f++) {
  if (f % workers !== worker) continue;
  await page.evaluate(x => window.renderAt(x), f / FPS);
  await page.screenshot({ path: path.join(outDir, `f_${String(f).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 95 });
}
await browser.close();
