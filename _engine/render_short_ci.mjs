// Data-driven short renderer: node render_short_ci.mjs <short_data.json> [outDir]
// Frame-steps short_template_dd.html at 30fps for window.TOTAL_DURATION() seconds.
import puppeteer from 'puppeteer';
import { mkdirSync, readFileSync, rmSync } from 'fs';
import { fileURLToPath, pathToFileURL } from 'url';
import path from 'path';

const here = path.dirname(fileURLToPath(import.meta.url));
const dataPath = process.argv[2];
const FRAMES = process.argv[3] || path.join(here, 'frames_dd');
const data = JSON.parse(readFileSync(dataPath, 'utf8'));
rmSync(FRAMES, { recursive: true, force: true });
mkdirSync(FRAMES, { recursive: true });

const FPS = 30;
const browser = await puppeteer.launch({ headless: 'shell', args: ['--no-sandbox', '--disable-setuid-sandbox'] });
const page = await browser.newPage();
await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(path.join(here, 'short_template_dd.html')).href, { waitUntil: 'networkidle0' });
await page.evaluate(d => { window.SHORT_DATA = d; }, data);
const dur = await page.evaluate(() => window.TOTAL_DURATION());
const total = Math.round(FPS * dur);
console.log(`duration=${dur.toFixed(2)}s frames=${total}`);

const t0 = Date.now();
for (let i = 0; i < total; i++) {
  await page.evaluate(tt => window.renderFrame(tt), i / FPS);
  await page.screenshot({
    path: path.join(FRAMES, `${String(i).padStart(4, '0')}.jpg`),
    type: 'jpeg', quality: 90, clip: { x: 0, y: 0, width: 1080, height: 1920 },
  });
  if (i % 150 === 0) console.log(`  frame ${i}/${total} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
}
await browser.close();
console.log(`FRAMES_DONE ${total} -> ${FRAMES}`);
