#!/usr/bin/env node
// Records the atlas for the README: the opening reveal, then a few plates re-scanning into place.
// The atlas animates on the wall clock, so frames come from Chrome's screencast stream as they render, each
// with its own timestamp; ffmpeg's concat demuxer then plays them back at their true spacing.
//
//   python -I bin/nyotti.py serve --no-open
//   node scripts/capture-atlas.mjs --url http://127.0.0.1:4343/atlas.html --out docs/media [--lang ko --prefix ko-]

import { spawn, execFileSync } from 'node:child_process';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { parseArgs } from 'node:util';

const { values: o } = parseArgs({
  options: {
    url: { type: 'string', default: 'http://127.0.0.1:4343/atlas.html' },
    out: { type: 'string', default: 'docs/media' },
    lang: { type: 'string', default: 'en' },
    prefix: { type: 'string', default: '' },
    chrome: { type: 'string', default: process.env.CHROME_PATH || defaultChrome() },
    width: { type: 'string', default: '1360' },
    height: { type: 'string', default: '850' },
    plates: { type: 'string', default: 'by-coin,account-shape,regimes' },
    'gif-width': { type: 'string', default: '880' },
    'gif-fps': { type: 'string', default: '10' },
  },
});

function defaultChrome() {
  if (process.platform === 'win32') return 'C:/Program Files/Google/Chrome/Application/chrome.exe';
  if (process.platform === 'darwin') return '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  return 'google-chrome';
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const W = Number(o.width), H = Number(o.height);
const outDir = path.resolve(o.out);
const framesDir = await fs.mkdtemp(path.join(os.tmpdir(), 'atlas-frames-'));
const profile = await fs.mkdtemp(path.join(os.tmpdir(), 'atlas-chrome-'));
await fs.mkdir(outDir, { recursive: true });

const port = 9300 + Math.floor(Math.random() * 500);
const chrome = spawn(o.chrome, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, '--hide-scrollbars',
  '--no-first-run', '--no-default-browser-check', `--window-size=${W},${H}`, '--ignore-gpu-blocklist', 'about:blank',
], { stdio: 'ignore' });

let ws, nextId = 1, recording = false;
const pending = new Map();
const frames = [];
const writes = [];
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
          if (msg.method === 'Page.screencastFrame') {
            const { data, sessionId, metadata } = msg.params;
            if (ws.readyState === WebSocket.OPEN) send('Page.screencastFrameAck', { sessionId }).catch(() => {});
            if (recording) {
              const file = path.join(framesDir, `f${String(frames.length).padStart(5, '0')}.jpg`);
              frames.push({ file, t: metadata.timestamp * 1000 });
              writes.push(fs.writeFile(file, Buffer.from(data, 'base64')));
            }
            return;
          }
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

async function record(seconds) {
  recording = true;
  await sleep(seconds * 1000);
  recording = false;
}

try {
  await connect();
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false });
  await send('Page.startScreencast', { format: 'jpeg', quality: 88, everyNthFrame: 1 });
  await send('Page.navigate', { url: `${o.url}?lang=${o.lang}` });
  // Start recording as soon as the data is in, so the reveal is caught from the first frame.
  for (let i = 0; i < 200 && !(await evaluate('!!(window.__atlas && window.__atlas.ready)')); i++) await sleep(50);
  await evaluate("document.querySelector('.grain').style.display = 'none'; true"); // film grain costs GIF bytes, not meaning
  await record(3.2);
  for (const id of o.plates.split(',')) {
    await evaluate(`document.getElementById(${JSON.stringify(id)}).scrollIntoView({behavior:'instant', block:'start'}); true`);
    await record(2.4);
  }
  await send('Page.stopScreencast');
  await Promise.all(writes);
  const { data } = await send('Page.captureScreenshot', { format: 'png' });
  await fs.writeFile(path.join(outDir, `${o.prefix}atlas.png`), Buffer.from(data, 'base64'));
} finally {
  ws?.close();
  chrome.kill();
}

// Each frame lasts until the next one was taken.
const list = frames.map((f, i) => `file '${f.file.replace(/\\/g, '/')}'\nduration ${(((frames[i + 1]?.t ?? f.t + 80) - f.t) / 1000).toFixed(3)}`).join('\n');
const listFile = path.join(framesDir, 'frames.txt');
await fs.writeFile(listFile, `ffconcat version 1.0\n${list}\nfile '${frames.at(-1).file.replace(/\\/g, '/')}'\n`);
const gifW = Number(o['gif-width']), gifFps = Number(o['gif-fps']);
const input = ['-f', 'concat', '-safe', '0', '-i', listFile];
const palette = path.join(framesDir, 'palette.png');
const name = `${o.prefix}atlas`;
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', ...input, '-vf', `fps=${gifFps},scale=${gifW}:-1:flags=lanczos,palettegen=max_colors=96:stats_mode=diff`, palette]);
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', ...input, '-i', palette, '-lavfi',
  `fps=${gifFps},scale=${gifW}:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=none:diff_mode=rectangle`, path.join(outDir, `${name}.gif`)]);
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', ...input, '-vf', `fps=30,scale=${gifW}:-2:flags=lanczos,format=yuv420p`,
  '-c:v', 'libx264', '-crf', '22', '-movflags', '+faststart', path.join(outDir, `${name}.mp4`)]);
const { size } = await fs.stat(path.join(outDir, `${name}.gif`));
const span = (frames.at(-1).t - frames[0].t) / 1000;
console.log(`  ${frames.length} frames over ${span.toFixed(1)} s (${(frames.length / span).toFixed(1)} fps) · ${name}.gif ${(size / 1048576).toFixed(1)} MiB · ${name}.mp4 · ${name}.png`);
await fs.rm(framesDir, { recursive: true, force: true });
await fs.rm(profile, { recursive: true, force: true }).catch(() => {});
