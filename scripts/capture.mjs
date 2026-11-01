#!/usr/bin/env node
// Records the README media from a running viewer (`python -I bin/nyotti.py serve --no-open`):
// a hero GIF/MP4 of the four-year replay followed by a few Jev lenses, plus stills.
// The page exposes window.__nyotti.step(dt), so every frame advances the animation by exactly
// 1/fps of a second no matter how long a screenshot takes. Headless Chrome over the DevTools
// protocol with Node's built-in WebSocket; ffmpeg stitches the frames.
//
//   node scripts/capture.mjs --url http://127.0.0.1:4343/ --out docs/media

import { spawn, execFileSync } from 'node:child_process';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { parseArgs } from 'node:util';

const { values: o } = parseArgs({
  options: {
    url: { type: 'string', default: 'http://127.0.0.1:4343/' },
    out: { type: 'string', default: 'docs/media' },
    lang: { type: 'string', default: 'en' },
    chrome: { type: 'string', default: process.env.CHROME_PATH || defaultChrome() },
    width: { type: 'string', default: '1360' },
    height: { type: 'string', default: '1000' },
    fps: { type: 'string', default: '12' },
    'replay-seconds': { type: 'string', default: '20' },
    'gif-width': { type: 'string', default: '1080' },
    prefix: { type: 'string', default: '' },
  },
});

function defaultChrome() {
  if (process.platform === 'win32') return 'C:/Program Files/Google/Chrome/Application/chrome.exe';
  if (process.platform === 'darwin') return '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  return 'google-chrome';
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const W = Number(o.width), H = Number(o.height), FPS = Number(o.fps);
const outDir = path.resolve(o.out);
const framesDir = await fs.mkdtemp(path.join(os.tmpdir(), 'nyotti-frames-'));
const profile = await fs.mkdtemp(path.join(os.tmpdir(), 'nyotti-chrome-'));
await fs.mkdir(outDir, { recursive: true });

const port = 9300 + Math.floor(Math.random() * 500);
const chrome = spawn(o.chrome, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  '--hide-scrollbars', '--no-first-run', '--no-default-browser-check', `--window-size=${W},${H}`, 'about:blank',
], { stdio: 'ignore' });

let ws, nextId = 1;
const pending = new Map();
function send(method, params = {}) {
  const id = nextId++;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}
const evaluate = (expression) => send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
  .then((r) => r.result?.value);

async function connect() {
  for (let i = 0; i < 50; i++) {
    try {
      const list = await fetch(`http://127.0.0.1:${port}/json/list`).then((r) => r.json());
      const page = list.find((t) => t.type === 'page');
      if (page) {
        ws = new WebSocket(page.webSocketDebuggerUrl);
        await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
        ws.onmessage = (e) => {
          const msg = JSON.parse(e.data);
          const p = pending.get(msg.id);
          if (!p) return;
          pending.delete(msg.id);
          msg.error ? p.reject(new Error(msg.error.message)) : p.resolve(msg.result);
        };
        return;
      }
    } catch {
      // chrome still starting
    }
    await sleep(200);
  }
  throw new Error('Could not reach Chrome DevTools.');
}

let frame = 0;
async function shot(file, clip) {
  const { data } = await send('Page.captureScreenshot', {
    format: 'png', captureBeyondViewport: true, ...(clip ? { clip: { ...clip, scale: 1 } } : {}),
  });
  await fs.writeFile(file, Buffer.from(data, 'base64'));
}
const nextFrame = (clip) => shot(path.join(framesDir, `f${String(frame++).padStart(4, '0')}.png`), clip);
async function hold(clip, seconds) {
  const file = path.join(framesDir, `f${String(frame).padStart(4, '0')}.png`);
  await shot(file, clip);
  frame++;
  for (let i = 1; i < Math.round(seconds * FPS); i++) {
    await fs.copyFile(file, path.join(framesDir, `f${String(frame++).padStart(4, '0')}.png`));
  }
}
// The clip box: the width of <main>, from the top of one element to the bottom of another.
const box = (fromSel, toSel) => evaluate(`(() => {
  const m = document.querySelector('main').getBoundingClientRect();
  const a = document.querySelector(${JSON.stringify(fromSel)}).getBoundingClientRect();
  const b = document.querySelector(${JSON.stringify(toSel)}).getBoundingClientRect();
  return { x: m.left + 4, y: a.top + scrollY - 20, width: m.width - 8, height: b.bottom - a.top + 36 };
})()`);

try {
  await connect();
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: `${o.url}?autoplay=0&lang=${o.lang}` });
  for (let i = 0; i < 100 && !(await evaluate('!!window.__ready')); i++) await sleep(150);
  await sleep(800); // fonts

  const hero = await box('.hero-copy', '#replay-legend');
  hero.height = Math.min(hero.height, 1080);
  console.log(`  replay clip ${Math.round(hero.width)}x${Math.round(hero.height)}`);
  await evaluate('window.__nyotti.seek(0); true');
  const steps = Math.round(Number(o['replay-seconds']) * FPS);
  const dt = 30 / (steps - 1); // the viewer's 30 s replay squeezed into replay-seconds
  await nextFrame(hero);
  for (let i = 1; i < steps; i++) {
    await evaluate(`window.__nyotti.step(${dt}); true`);
    await nextFrame(hero);
  }
  for (let i = 0; i < FPS; i++) { await evaluate(`window.__nyotti.step(${1 / FPS}); true`); await nextFrame(hero); }
  await hold(hero, 1.0);
  await shot(path.join(outDir, `${o.prefix}replay.png`), hero);

  // Lenses: same clip size, anchored on the lens section.
  const lensTop = await evaluate(`document.querySelector('.lens-wrap').getBoundingClientRect().top + scrollY - 20`);
  const lens = { ...hero, y: lensTop };
  for (const k of ['panic', 'after_pain', 'boldness']) {
    await evaluate(`window.__nyotti.lens(${JSON.stringify(k)}); true`);
    await sleep(150);
    await hold(lens, 1.1);
  }
  await evaluate(`window.__nyotti.lens('panic'); window.__nyotti.pick(window.__nyotti.find('panic', 0.9)); true`);
  await sleep(600);
  await hold(lens, 2.2);
  await shot(path.join(outDir, `${o.prefix}lenses.png`), lens);

  const cardsTop = await evaluate(`document.querySelector('.findings').getBoundingClientRect().top + scrollY - 20`);
  await shot(path.join(outDir, `${o.prefix}findings.png`), { ...hero, y: cardsTop, height: Math.min(1400, hero.height + 300) });
} finally {
  ws?.close();
  chrome.kill();
}

console.log(`  ${frame} frames at ${FPS} fps = ${(frame / FPS).toFixed(1)} s`);
const gifW = Number(o['gif-width']);
const palette = path.join(framesDir, 'palette.png');
const input = ['-framerate', String(FPS), '-i', path.join(framesDir, 'f%04d.png')];
const name = `${o.prefix}hero`;
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', ...input,
  '-vf', `scale=${gifW}:-1:flags=lanczos,palettegen=max_colors=160:stats_mode=diff`, palette]);
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', ...input, '-i', palette,
  '-lavfi', `scale=${gifW}:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=none:diff_mode=rectangle`,
  path.join(outDir, `${name}.gif`)]);
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', ...input,
  '-vf', `scale=${gifW}:-2:flags=lanczos,format=yuv420p`, '-c:v', 'libx264', '-crf', '22', '-movflags', '+faststart',
  path.join(outDir, `${name}.mp4`)]);
const { size } = await fs.stat(path.join(outDir, `${name}.gif`));
console.log(`  ${name}.gif ${(size / 1048576).toFixed(1)} MiB · ${name}.mp4 written`);
await fs.rm(framesDir, { recursive: true, force: true });
await fs.rm(profile, { recursive: true, force: true }).catch(() => {});
