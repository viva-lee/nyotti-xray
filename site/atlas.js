// The atlas: thirty readings of one trading record, each drawn by the same 24,000 points.
// Every point stands for one real unit of the record (a day, an order, a decision, a bitcoin), and each
// plate says which. Scrolling to a plate re-scans the field into that plate's layout.
(function () {
  'use strict';
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const params = new URLSearchParams(location.search);
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const DPR = Math.min(2, window.devicePixelRatio || 1);
  const POOL = 24000;
  const OFF = { decision: 0, order: 0, hour: 0, lot: 0, day: 10200, btc: 12000, minute: 20000, event: 23000 };
  const T0 = Date.parse('2018-03-05T00:00:00Z');
  const T_END = (Date.parse('2022-01-01T00:00:00Z') - T0) / 60000;

  // Validated dark steps (dataviz reference palette); see README for the checks.
  const C = {
    ink: '#a3bed2', bright: '#f4f8fb', buy: '#3987e5', sell: '#d95926', loss: '#e66767',
    btc: '#c98500', usd: '#199e70', dust: '#7f9bb0',
    exposure: ['#86b6ef', '#3987e5', '#1c5cab', '#5f6068', '#e66767'],
  };

  // ------------------------------------------------------------------ text
  const T = {
    en: {
      notice: 'Past records only. Not investment advice.', replay: 'Replay', index: 'Index', close: 'Close',
      heroTitle: 'One trading record, read thirty ways',
      heroSub: (m) => `In September 2026 the trader known as Wonyotti (BitMEX account aoa) published every fill he made from 2018 to 2021: ${m.fills.toLocaleString('en-US')} of them, each since found on the exchange's own public tape. This atlas reads that record thirty ways. The first twenty findings were measured again another way, and ten readings are new.`,
      heroCheck: 'The first twenty, measured again:',
      heroCount: (k, n) => ({ holds: `${n} hold`, nuance: `${n} gained a nuance`, revised: `${n} revised` }[k]),
      heroUnit: 'Each dot is one of 10,169 Bitcoin decisions, at its time and price.',
      scroll: 'Scroll to read the plates',
      plate: (n, total) => `Plate ${n} of ${total}`, isNew: 'New reading',
      verdict: { holds: 'Re-checked: holds', nuance: 'Re-checked: holds, with a nuance', revised: 'Re-checked: revised' },
      summaryTitle: 'The second look, plate by plate',
      summaryLead: 'Every original finding was measured again another way. Two titles said more than the numbers did, so they were rewritten. One finding gained a nuance. The rest hold.',
      aboutTitle: 'What this is, and is not',
      about: [
        ['What it is', 'An independent, unofficial reading of a trade history its owner chose to publish. Every number is computed from that release and from BitMEX\'s public data by the code in the repository.'],
        ['What it is not', 'Not investment advice, a signal, a strategy or a forecast. No live data, no "what would he do now", no bot, no copy-trading, no backtest of following him. Not affiliated with him, BitMEX or TypeSafe.'],
        ['In his own words', '"If a trading bot looked like it would really make money, I already have the data, so I would have built it and run it first. Please don\'t be fooled, and don\'t buy one." From the letter included in the release (translated).'],
      ],
      buy: 'Bought', sell: 'Sold', kinds: ['opened', 'added', 'reduced', 'flipped', 'closed'], exposure: 'exposure',
      years: 'year', prev: 'Previous plate', next: 'Next plate',
      noGL: 'This browser cannot draw the dot field (WebGL is off), so each plate shows its chart instead.',
    },
    ko: {
      notice: '과거 기록 분석일 뿐, 투자 조언이 아닙니다.', replay: '리플레이', index: '목차', close: '닫기',
      heroTitle: '하나의 매매 기록, 서른 번의 판독',
      heroSub: (m) => `2026년 9월, 워뇨띠(BitMEX 계정 aoa)가 2018~2021년 체결 전부를 공개했다. ${m.fills.toLocaleString('ko-KR')}건이고, 하나도 빠짐없이 거래소 공개 테이프에서 다시 찾았다. 이 아틀라스는 그 기록을 서른 가지로 판독한다. 처음 발견 20개는 다른 방법으로 다시 쟀고, 10개는 새 판독이다.`,
      heroCheck: '처음 20개를 다시 잰 결과:',
      heroCount: (k, n) => ({ holds: `유지 ${n}`, nuance: `단서 추가 ${n}`, revised: `수정 ${n}` }[k]),
      heroUnit: '점 하나가 비트코인 결정 하나다(10,169개). 결정한 시각과 가격에 놓였다.',
      scroll: '스크롤해서 판독 보기',
      plate: (n, total) => `판독 ${n} / ${total}`, isNew: '새 판독',
      verdict: { holds: '재검증: 유지', nuance: '재검증: 유지, 단서 추가', revised: '재검증: 수정' },
      summaryTitle: '두 번째 판독, 한눈에',
      summaryLead: '처음 발견은 모두 다른 방법으로 다시 쟀다. 두 개는 제목이 숫자보다 앞서 나가서 고쳤고, 하나는 단서를 더했다. 나머지는 그대로 유지된다.',
      aboutTitle: '이 프로젝트가 하는 것과 하지 않는 것',
      about: [
        ['무엇인가', '기록의 주인이 스스로 공개한 거래 내역에 대한 독립적인 비공식 판독이다. 모든 숫자는 공개 자료와 BitMEX 공개 데이터로부터 레포의 코드가 계산했다.'],
        ['무엇이 아닌가', '투자 조언, 신호, 전략, 예측이 아니다. 실시간 데이터, "지금 그라면?", 봇, 카피트레이딩, 그를 따라 했을 때의 백테스트가 없다. 그, BitMEX, TypeSafe와 무관하다.'],
        ['그의 말', '"매매봇이 실제 수익이 날 것 같을 경우 이미 자료가 있는 제가 먼저 만들어서 돌리고 있었을 것입니다. 절대 속지 말고 구매도 하지 않으셨으면 좋겠습니다." 공개 자료에 포함된 서한 중.'],
      ],
      buy: '매수', sell: '매도', kinds: ['신규 진입', '추가', '축소', '반대 전환', '전량 청산'], exposure: '노출도',
      years: '년', prev: '이전 판독', next: '다음 판독',
      noGL: '이 브라우저는 점 그림(WebGL)을 그릴 수 없어서 판독마다 차트를 대신 보여준다.',
    },
  };
  let lang = 'en';
  try { lang = localStorage.getItem('nyotti-lang') || ((navigator.language || '').startsWith('ko') ? 'ko' : 'en'); } catch (e) { /* storage blocked */ }
  if (params.get('lang')) lang = params.get('lang') === 'ko' ? 'ko' : 'en';
  const t = (k) => T[lang][k];
  const L = (o) => (o && typeof o === 'object' ? o[lang] ?? o.en : o);

  // ------------------------------------------------------------------ helpers
  function hash(i, k) {
    let h = (Math.imul(i + 1, 374761393) + Math.imul(k + 7, 668265263)) | 0;
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
  }
  const rgbCache = {};
  function rgb(hex) {
    if (!rgbCache[hex]) rgbCache[hex] = [1, 3, 5].map((k) => parseInt(hex.slice(k, k + 2), 16) / 255);
    return rgbCache[hex];
  }
  const lin = (d0, d1, r0, r1) => (v) => r0 + ((v - d0) / (d1 - d0)) * (r1 - r0);
  const logS = (d0, d1, r0, r1) => { const a = Math.log10(d0), b = Math.log10(d1); return (v) => r0 + ((Math.log10(Math.max(v, d0 * 1e-3)) - a) / (b - a)) * (r1 - r0); };
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const num = (v, d = 0) => (v == null ? '–' : v.toLocaleString(lang === 'ko' ? 'ko-KR' : 'en-US', { minimumFractionDigits: d, maximumFractionDigits: d }));
  const pct = (v, d = 0) => (v == null ? '–' : (v * 100).toFixed(d) + '%');
  const dayDate = (d) => new Date(Date.parse(A.days.start + 'T00:00:00Z') + d * 864e5);
  const ymd = (dt) => dt.toISOString().slice(0, 10);
  const minDate = (m) => new Date(T0 + m * 60000);
  const yearMin = (y) => (Date.parse(`${y}-01-01T00:00:00Z`) - T0) / 60000;

  // ------------------------------------------------------------------ data
  let INS, D, A, CARD = {}, ORDER = [], gl = null, stage = { x: 0, y: 0, w: 1, h: 1 }, view = { w: 1, h: 1 };
  let current = null, tipFn = null, overlayTimer = 0, pickGrid = null, target = null;

  Promise.all(['data/insights.json', 'data/decisions.json', 'data/atlas.json'].map((u) => fetch(u).then((r) => r.json())))
    .then(([ins, dec, atlas]) => {
      INS = ins; D = dec; A = atlas;
      INS.cards.forEach((c) => { CARD[c.id] = c; });
      ORDER = A.chapters.flatMap((ch) => ch.cards.filter((id) => CARD[id]));
      try { gl = window.XAtlasGL.create($('#field'), POOL); } catch (e) { gl = null; }
      if (!gl) document.body.classList.add('no-gl');
      build();
      measure();
      bindScroll();
      bindPointer();
      bindKeys();
      const hash0 = decodeURIComponent(location.hash.slice(1));
      if (hash0 && CARD[hash0]) {
        document.getElementById(hash0)?.scrollIntoView({ behavior: 'instant', block: 'start' });
        activate(hash0, true);
      } else {
        activate('hero', false);
      }
      window.addEventListener('resize', () => { measure(); if (current) activate(current, true); }, { passive: true });
      window.__atlas = { activate, order: () => ORDER, ready: true };
    });

  // ------------------------------------------------------------------ geometry
  function measure() {
    view = { w: window.innerWidth, h: window.innerHeight };
    const wide = view.w >= 960;
    document.body.classList.toggle('narrow', !wide);
    const head = $('.top').getBoundingClientRect().height;
    if (wide) {
      const col = $('.column').getBoundingClientRect();
      const x0 = Math.round(col.right + 20);
      stage = { x: x0, y: Math.round(head + 26), w: Math.round(view.w - x0 - 30), h: Math.round(view.h - head - 60) };
    } else {
      stage = { x: 12, y: Math.round(head + 10), w: Math.round(view.w - 24), h: Math.round(Math.min(view.h * 0.5, view.w * 0.95)) };
    }
    const fr = $('.frame');
    Object.assign(fr.style, { left: stage.x + 'px', top: stage.y + 'px', width: stage.w + 'px', height: stage.h + 'px' });
    // On narrow screens the unit caption under the stage can take two lines; the backdrop covers it too.
    const bottom = stage.y + stage.h + (wide ? 10 : 52);
    $('.backdrop').style.height = bottom + 'px';
    document.documentElement.style.setProperty('--stage-bottom', bottom + 'px');
    if (gl) gl.resize(view.w, view.h, DPR);
  }

  // ------------------------------------------------------------------ targets
  function blank(S) {
    const x = new Float32Array(POOL), y = new Float32Array(POOL), s = new Float32Array(POOL), rgba = new Float32Array(POOL * 4);
    const [r, g, b] = rgb(C.dust);
    for (let i = 0; i < POOL; i++) {
      x[i] = S.x + hash(i, 1) * S.w;
      y[i] = S.y + hash(i, 2) * S.h;
      s[i] = 1.1;
      const a = 0.05 + 0.06 * hash(i, 3);
      rgba[i * 4] = r; rgba[i * 4 + 1] = g; rgba[i * 4 + 2] = b; rgba[i * 4 + 3] = a;
    }
    return { x, y, s, rgba, used: new Uint8Array(POOL) };
  }
  function put(T_, i, x, y, size, hex, a) {
    if (i < 0 || i >= POOL) return;
    const [r, g, b] = rgb(hex);
    T_.x[i] = x; T_.y[i] = y; T_.s[i] = size;
    T_.rgba[i * 4] = r; T_.rgba[i * 4 + 1] = g; T_.rgba[i * 4 + 2] = b; T_.rgba[i * 4 + 3] = a;
    T_.used[i] = 1;
  }
  const inset = (S, m) => ({ x: S.x + m.l, y: S.y + m.t, w: S.w - m.l - m.r, h: S.h - m.t - m.b });

  // Best dot step and dots-per-row for `groups` columns (counts) side by side, stacked up (and down for negatives).
  function fitColumns(counts, R, gapRatio = 0.7, maxStep = 13) {
    const G = counts.length;
    const up = Math.max(1, ...counts.map((c) => Math.max(0, c)));
    const down = Math.max(0, ...counts.map((c) => Math.max(0, -c)));
    let best = { s: 0, k: 1 };
    for (let k = 1; k <= 80; k++) {
      const s = Math.min(R.w / (k * (G + gapRatio * (G - 1))), R.h / (Math.ceil(up / k) + Math.ceil(down / k) + (down ? 0.6 : 0)));
      if (s > best.s) best = { s, k };
    }
    best.s = Math.min(best.s, maxStep);
    const colW = best.k * best.s;
    const total = G * colW + (G - 1) * gapRatio * colW;
    best.x0 = R.x + (R.w - total) / 2;
    best.colW = colW;
    best.pitch = colW * (1 + gapRatio);
    best.base = down ? R.y + (R.h * Math.ceil(up / best.k)) / (Math.ceil(up / best.k) + Math.ceil(down / best.k) + 0.6) : R.y + R.h;
    // Leave the stack's own height above the base, centred vertically when the stage is roomier than needed.
    const need = (Math.ceil(up / best.k) + Math.ceil(down / best.k)) * best.s;
    if (!down) best.base = R.y + R.h - Math.max(0, (R.h - need) / 2);
    else best.base = R.y + Math.ceil(up / best.k) * best.s + Math.max(0, (R.h - need) / 2);
    return best;
  }
  // Position of the j-th dot in column g (j counts outward from the base; negative columns stack downward).
  function colDot(f, g, j, down = false) {
    const row = Math.floor(j / f.k), c = j % f.k;
    const x = f.x0 + g * f.pitch + (c + 0.5) * f.s;
    const y = down ? f.base + (row + 0.5) * f.s + f.s * 0.3 : f.base - (row + 0.5) * f.s;
    return [x, y];
  }
  // Grid fit for n dots in a rect, row-major from the top.
  function fitGrid(n, R) {
    let s = Math.sqrt((R.w * R.h) / n);
    let cols = Math.max(1, Math.floor(R.w / s));
    while (Math.ceil(n / cols) * s > R.h) { s *= 0.97; cols = Math.max(1, Math.floor(R.w / s)); }
    const rows = Math.ceil(n / cols);
    return { s, cols, rows, x0: R.x + (R.w - cols * s) / 2 + s / 2, y0: R.y + (R.h - rows * s) / 2 + s / 2 };
  }
  // Stack values into bins; each bin is a column of dots `k` wide.
  function dotHist(values, lo, hi, bins, R) {
    const n = values.length;
    const idx = values.map((v) => clamp(Math.floor(((v - lo) / (hi - lo)) * bins), 0, bins - 1));
    const counts = new Array(bins).fill(0);
    idx.forEach((b) => counts[b]++);
    const binW = R.w / bins;
    let s = Math.sqrt((R.w * R.h * 0.5) / n);
    for (let it = 0; it < 30; it++) {
      const k = Math.max(1, Math.floor(binW / s));
      if (Math.ceil(Math.max(...counts) / k) * s <= R.h) break;
      s *= 0.94;
    }
    const k = Math.max(1, Math.floor(binW / s));
    const seen = new Array(bins).fill(0);
    return idx.map((b) => {
      const j = seen[b]++;
      const row = Math.floor(j / k), c = j % k;
      const x0 = R.x + b * binW + (binW - k * s) / 2;
      return [x0 + (c + 0.5) * s, R.y + R.h - (row + 0.5) * s, s];
    });
  }

  // ------------------------------------------------------------------ overlay (SVG in stage coordinates)
  const OV = {
    start: () => [],
    text: (o, x, y, s, cls = 'ov', anchor = 'start') => o.push(`<text class="${cls}" x="${(x - stage.x).toFixed(1)}" y="${(y - stage.y).toFixed(1)}" text-anchor="${anchor}">${esc(s)}</text>`),
    line: (o, x1, y1, x2, y2, cls = 'ov-rule') => o.push(`<line class="${cls}" x1="${(x1 - stage.x).toFixed(1)}" y1="${(y1 - stage.y).toFixed(1)}" x2="${(x2 - stage.x).toFixed(1)}" y2="${(y2 - stage.y).toFixed(1)}"/>`),
    swatch: (o, x, y, color, label) => {
      o.push(`<circle cx="${(x - stage.x).toFixed(1)}" cy="${(y - stage.y - 4).toFixed(1)}" r="4" fill="${color}"/>`);
      OV.text(o, x + 10, y, label, 'ov');
    },
    // A row of swatches that wraps when it runs out of width. With `up`, extra rows stack above `y` instead of below.
    // Returns the y below the last row.
    legend(o, items, x, y, maxW, up = false) {
      let cx = x, row = 0;
      const placed = items.map(([color, label]) => {
        const w = 26 + String(label).length * (lang === 'ko' ? 11.5 : 6.6);
        if (cx > x && cx + w > x + maxW) { cx = x; row++; }
        const at = [cx, row, color, label];
        cx += w + 14;
        return at;
      });
      const y0 = up ? y - row * 22 : y;
      placed.forEach(([px, r, color, label]) => OV.swatch(o, px, y0 + r * 22, color, label));
      return y0 + (row + 1) * 22;
    },
    yearAxis(o, R, xAt, top = false) {
      const y = top ? R.y - 10 : R.y + R.h + 22;
      OV.text(o, R.x, y, '2018', 'ov-tick');
      [2019, 2020, 2021].forEach((yr) => {
        const x = xAt(yearMin(yr));
        OV.line(o, x, R.y, x, R.y + R.h, 'ov-grid');
        OV.text(o, x + 4, y, String(yr), 'ov-tick');
      });
    },
    end: (o) => o.join(''),
  };
  const timeX = (R) => lin(0, T_END, R.x, R.x + R.w);
  const dayX = (R) => (d) => R.x + ((d * 1440) / T_END) * R.w;

  // ------------------------------------------------------------------ tooltips
  function decisionTip(i) {
    const k = D.kind[i];
    const ex = D.exp0[i] == null ? '' : `<br>${t('exposure')} ${D.exp0[i].toFixed(2)}x → ${D.exp1[i].toFixed(2)}x`;
    return `<b>${minDate(D.t[i]).toISOString().slice(0, 16).replace('T', ' ')} UTC</b><br>` +
      `<span class="sw" style="background:${D.side[i] ? C.buy : C.sell}"></span>${D.side[i] ? t('buy') : t('sell')} $${D.usd[i].toFixed(2)}M · ${T[lang].kinds[k]}` +
      `<br>XBTUSD @ ${num(D.px[i], 1)}${ex}`;
  }
  const dayTip = (d, extra) => `<b>${ymd(dayDate(d))}</b>${extra ? '<br>' + extra : ''}`;

  // ------------------------------------------------------------------ scenes
  // Each scene fills the target arrays for its units and returns {unit, overlay, tip}.
  const PLOT = { l: 58, r: 28, t: 46, b: 52 };
  const SCENES = {};

  SCENES.hero = (T_, S) => {
    // Full-bleed on the opening screen: the price silhouette keeps to the lower part, under the headline.
    const R = S.w > stage.w ? inset(S, { l: 24, r: 70, t: Math.round(S.h * (view.w >= 960 ? 0.4 : 0.62)), b: 40 }) : inset(S, { l: 24, r: 70, t: 30, b: 46 });
    const ps = D.px;
    let lo = Infinity, hi = 0;
    for (const p of ps) { if (p < lo) lo = p; if (p > hi) hi = p; }
    const x = timeX(R), y = logS(lo * 0.92, hi * 1.06, R.y + R.h, R.y);
    for (let i = 0; i < D.t.length; i++) {
      put(T_, OFF.decision + i, x(D.t[i]), y(D.px[i]), 1.4 + Math.min(4.5, Math.sqrt(D.usd[i]) * 0.85), D.side[i] ? C.buy : C.sell, 0.62);
    }
    const o = OV.start();
    [3000, 5000, 10000, 20000, 40000, 60000].forEach((p) => {
      OV.line(o, R.x, y(p), R.x + R.w, y(p), 'ov-grid');
      OV.text(o, R.x + R.w + 8, y(p) + 4, `$${p / 1000}k`, 'ov-tick');
    });
    OV.yearAxis(o, R, x);
    return { unit: t('heroUnit'), overlay: OV.end(o), tip: (i) => (i < D.t.length ? decisionTip(i) : null), full: true };
  };

  SCENES.verified = (T_, S) => {
    const c = CARD.verified.chart;
    const R = inset(S, { l: 56, r: 20, t: 40, b: 64 });
    const years = [2018, 2019, 2020, 2021];
    const bandH = R.h / 4;
    const cell = Math.min(R.w / 54, (bandH - 14) / 7);
    const o = OV.start();
    const firstSunday = (yr) => new Date(Date.UTC(yr, 0, 1)).getUTCDay();
    c.days.forEach((ds, k) => {
      const dt = new Date(ds + 'T00:00:00Z');
      const yr = dt.getUTCFullYear(), b = years.indexOf(yr);
      const doy = Math.floor((dt - Date.UTC(yr, 0, 1)) / 864e5);
      const week = Math.floor((doy + firstSunday(yr)) / 7), wd = dt.getUTCDay();
      const ok = c.ok[k] === c.total[k];
      put(T_, OFF.day + k, R.x + (week + 0.5) * cell, R.y + b * bandH + 14 + (wd + 0.5) * cell, cell * 0.78, ok ? C.ink : C.loss, ok ? 0.8 : 1);
    });
    years.forEach((yr, b) => OV.text(o, R.x - 10, R.y + b * bandH + 14 + 3.8 * cell, String(yr), 'ov-tick', 'end'));
    const L1 = lang === 'ko' ? ['체결이 전부 테이프에 있는 날', '강제청산·자전거래 체결이 빠진 날'] : ['every fill on the tape', 'a liquidation or self-trade missing'];
    OV.legend(o, [[C.ink, L1[0]], [C.loss, L1[1]]], R.x, R.y + R.h + 26, R.w);
    return {
      unit: lang === 'ko' ? '점 하나 = 체결이 있던 날 하루' : '1 dot = 1 day with fills', overlay: OV.end(o),
      tip: (i) => { const k = i - OFF.day; return k >= 0 && k < c.days.length ? `<b>${c.days[k]}</b><br>${num(c.ok[k])} / ${num(c.total[k])} ${lang === 'ko' ? '체결 일치' : 'fills matched'}` : null; },
    };
  };

  function ordersGrid(T_, S, colorOf, sizeOf, alphaOf) {
    const R = inset(S, { l: 20, r: 20, t: 30, b: 96 });
    const n = A.orders.t.length;
    const g = fitGrid(n, R);
    for (let k = 0; k < n; k++) {
      const col = k % g.cols, row = Math.floor(k / g.cols);
      put(T_, OFF.order + k, g.x0 + col * g.s, g.y0 + row * g.s, sizeOf(k, g.s), colorOf(k), alphaOf(k));
    }
    return { R, g };
  }
  const orderTip = (k) => {
    const o = A.orders;
    if (k < 0 || k >= o.t.length) return null;
    const src = o.sources[o.src[k]];
    const names = lang === 'ko'
      ? { website: '웹사이트 주문', amended: '가격을 끌어 정정한 주문', close: '포지션 종료 버튼', stop: '스톱 주문', liquidation: '강제청산' }
      : { website: 'website order', amended: 'website order, dragged to a new price', close: 'Close button', stop: 'stop order', liquidation: 'liquidation' };
    return `<b>${minDate(o.t[k]).toISOString().slice(0, 16).replace('T', ' ')} UTC</b><br>${names[src]}<br>$${num(Math.pow(10, o.lu[k]) / 1e6, 2)}M · ${lang === 'ko' ? '메이커' : 'maker'} ${pct(o.mk[k])}`;
  };

  SCENES['by-hand'] = (T_, S) => {
    const o = A.orders, col = { 0: C.ink, 1: C.buy, 2: C.bright, 3: C.sell, 4: C.loss };
    const { R } = ordersGrid(T_, S, (k) => col[o.src[k]], (k, s) => s * (o.src[k] ? 0.95 : 0.72), (k) => (o.src[k] ? 0.95 : 0.5));
    const counts = [0, 0, 0, 0, 0];
    o.src.forEach((v) => counts[v]++);
    const names = lang === 'ko' ? ['웹사이트', '가격을 끌어 정정', '종료 버튼', '스톱 발동', '강제청산(거래소 주문 ID)'] : ['Website', 'Dragged to a new price', 'Close button', 'Stop triggered', 'Liquidation (exchange ids)'];
    const ov = OV.start();
    const yEnd = OV.legend(ov, [0, 1, 2, 3, 4].map((k) => [col[k], `${names[k]} ${num(counts[k])}`]), R.x, R.y + R.h + 26, R.w);
    OV.text(ov, R.x, yEnd + 4, lang === 'ko' ? 'API 주문: 0개' : 'API orders: 0', 'ov-strong');
    return { unit: lang === 'ko' ? '점 하나 = 주문 하나(시간순)' : '1 dot = 1 order, in time order', overlay: OV.end(ov), tip: (i) => orderTip(i - OFF.order) };
  };

  SCENES.ledger = (T_, S) => {
    const c = CARD.ledger.numbers;
    const years = Object.keys(c.by_year);
    const R = inset(S, { l: 30, r: 30, t: 54, b: 60 });
    const totals = [c.rebuilt, c.wallet];
    const f = fitColumns(totals.map((v) => Math.round(v)), R, 1.4, 9);
    const shades = ['#4f6a80', '#a3bed2', '#4f6a80', '#dbe7f0'];
    let i = OFF.btc;
    const ov = OV.start();
    [0, 1].forEach((g) => {
      let j = 0;
      years.forEach((y, yi) => {
        const n = Math.round(c.by_year[y][g]);
        for (let q = 0; q < n; q++, j++) {
          const [x, yy] = colDot(f, g, j);
          put(T_, i++, x, yy, f.s * 0.8, shades[yi], 0.92);
        }
        const [, yTop] = colDot(f, g, j - 1);
        if (g === 1) OV.text(ov, f.x0 + g * f.pitch + f.colW + 10, yTop + 4, `${y}`, 'ov-tick');
      });
      OV.text(ov, f.x0 + g * f.pitch + f.colW / 2, f.base + 22, [lang === 'ko' ? '체결로 재구성' : 'Rebuilt from fills', lang === 'ko' ? '지갑' : 'Wallet'][g], 'ov', 'middle');
      OV.text(ov, f.x0 + g * f.pitch + f.colW / 2, f.base + 40, `${num(totals[g], 2)} BTC`, 'ov-strong', 'middle');
    });
    return { unit: lang === 'ko' ? '점 하나 = 1 BTC, 색은 연도' : '1 dot = 1 BTC, shaded by year', overlay: OV.end(ov), tip: null };
  };

  SCENES.transfers = (T_, S) => {
    const n = CARD.transfers.numbers;
    const wy = CARD.transfers.chart;
    const groups = [{ v: n.deposits, c: C.bright, l: lang === 'ko' ? '입금' : 'Deposited' }]
      .concat(wy.labels.en.map((y, k) => ({ v: wy.values[k], c: C.ink, l: (lang === 'ko' ? `${y} 출금` : `Out ${y}`) })))
      .concat([{ v: n.final_wallet, c: C.btc, l: lang === 'ko' ? '마지막 잔고' : 'Left at the end' }]);
    const R = inset(S, { l: 20, r: 20, t: 40, b: 64 });
    const f = fitColumns(groups.map((g) => Math.ceil(g.v)), R, 0.55, 10);
    const ov = OV.start();
    let i = OFF.btc;
    groups.forEach((g, gi) => {
      const cnt = Math.ceil(g.v);
      for (let j = 0; j < cnt; j++) { const [x, y] = colDot(f, gi, j); put(T_, i++, x, y, f.s * 0.82, g.c, 0.95); }
      const top = f.base - Math.ceil(cnt / f.k) * f.s;
      OV.text(ov, f.x0 + gi * f.pitch + f.colW / 2, top - 8, num(g.v, g.v < 100 ? 1 : 0), 'ov-strong', 'middle');
      OV.text(ov, f.x0 + gi * f.pitch + f.colW / 2, f.base + 22, g.l, 'ov', 'middle');
    });
    return { unit: lang === 'ko' ? '점 하나 = 1 BTC' : '1 dot = 1 BTC', overlay: OV.end(ov), tip: null };
  };

  SCENES['by-coin'] = (T_, S) => {
    const by = CARD['by-coin'].numbers.by_coin;
    const coins = Object.keys(by).filter((k) => Math.abs(by[k]) >= 1);
    const R = inset(S, { l: 20, r: 20, t: 40, b: 40 });
    const vals = coins.map((k) => Math.round(by[k]));
    const f = fitColumns(vals, R, 0.6, 9);
    const ov = OV.start();
    let i = OFF.btc;
    coins.forEach((k, g) => {
      const v = vals[g], down = v < 0;
      for (let j = 0; j < Math.abs(v); j++) { const [x, y] = colDot(f, g, j, down); put(T_, i++, x, y, f.s * 0.82, down ? C.loss : (k === 'BTC' ? C.btc : C.ink), 0.95); }
      const rows = Math.ceil(Math.abs(v) / f.k);
      const cx = f.x0 + g * f.pitch + f.colW / 2;
      if (down) { OV.text(ov, cx, f.base + rows * f.s + 18, `${num(by[k], 1)}`, 'ov-strong', 'middle'); OV.text(ov, cx, f.base - 8, k, 'ov', 'middle'); }
      else { OV.text(ov, cx, f.base - rows * f.s - 8, `+${num(by[k], 0)}`, 'ov-strong', 'middle'); OV.text(ov, cx, f.base + 18, k, 'ov', 'middle'); }
    });
    OV.line(ov, R.x, f.base, R.x + R.w, f.base, 'ov-rule');
    return { unit: lang === 'ko' ? '점 하나 = 1 BTC, 실현손익' : '1 dot = 1 BTC of realised PnL', overlay: OV.end(ov), tip: null };
  };

  SCENES.funding = (T_, S) => {
    const n = CARD.funding.numbers;
    const years = Object.keys(n.funding_by_year);
    const unit = 0.5;
    // Received is up, paid is down: funding and fees side by side for each year.
    const cols = [];
    years.forEach((y) => { cols.push({ v: -n.funding_by_year[y], y, kind: 'funding' }); cols.push({ v: -n.fees_by_year[y], y, kind: 'fees' }); });
    const R = inset(S, { l: 20, r: 20, t: 40, b: 50 });
    const f = fitColumns(cols.map((c) => Math.round(c.v / unit)), R, 0.45, 9);
    const ov = OV.start();
    let i = OFF.btc;
    cols.forEach((c, g) => {
      const cnt = Math.round(Math.abs(c.v) / unit), down = c.v < 0;
      const color = c.kind === 'funding' ? C.btc : C.ink;
      for (let j = 0; j < cnt; j++) { const [x, y] = colDot(f, g, j, down); put(T_, i++, x, y, f.s * 0.8, color, down ? 0.62 : 0.95); }
      const cx = f.x0 + g * f.pitch + f.colW / 2;
      const rows = Math.ceil(cnt / f.k);
      OV.text(ov, cx, down ? f.base + rows * f.s + 16 : f.base - rows * f.s - 8, `${c.v > 0 ? '+' : ''}${num(c.v, 1)}`, 'ov-strong', 'middle');
      if (g % 2 === 0) OV.text(ov, cx + f.pitch / 2, R.y + R.h + 34, c.y, 'ov-tick', 'middle');
    });
    OV.line(ov, R.x, f.base, R.x + R.w, f.base, 'ov-rule');
    OV.text(ov, R.x + R.w, f.base - 8, lang === 'ko' ? '받음 ↑' : 'received ↑', 'ov-tick', 'end');
    OV.text(ov, R.x + R.w, f.base + 18, lang === 'ko' ? '냄 ↓' : 'paid ↓', 'ov-tick', 'end');
    OV.legend(ov, lang === 'ko' ? [[C.btc, '펀딩비'], [C.ink, '거래 수수료(메이커 리베이트 포함)']] : [[C.btc, 'funding'], [C.ink, 'trading fees, maker rebates included']], R.x, R.y - 14, R.w);
    return { unit: lang === 'ko' ? '점 하나 = 0.5 BTC' : '1 dot = 0.5 BTC', overlay: OV.end(ov), tip: null };
  };

  SCENES.concentration = (T_, S) => {
    const pnl = [];
    A.days.pnl.forEach((v, d) => { if (v != null) pnl.push([v, d]); });
    pnl.sort((a, b) => b[0] - a[0]);
    const net = pnl.reduce((s, p) => s + p[0], 0);
    let cum = 0;
    const pts = pnl.map(([v, d]) => { cum += v; return [cum / net, v, d]; });
    const peak = Math.max(...pts.map((p) => p[0]));
    const R = inset(S, PLOT);
    const x = lin(0, pts.length - 1, R.x, R.x + R.w), y = lin(0, peak * 1.04, R.y + R.h, R.y);
    const half = CARD.concentration.numbers.days_to_half;
    pts.forEach(([c, v, d], k) => put(T_, OFF.day + d, x(k), y(c), k < half ? 5 : 2.6, k < half ? C.bright : (v < 0 ? C.loss : C.ink), k < half ? 1 : 0.75));
    const ov = OV.start();
    [0, 0.5, 1].forEach((g) => { OV.line(ov, R.x, y(g), R.x + R.w, y(g), 'ov-grid'); OV.text(ov, R.x - 8, y(g) + 4, pct(g), 'ov-tick', 'end'); });
    OV.text(ov, x(half) + 12, y(0.5) + 18, lang === 'ko' ? `상위 ${half}일 = 순이익의 절반` : `top ${half} days = half the net`, 'ov-strong');
    const top = pts.findIndex((p) => p[0] === peak);
    OV.text(ov, x(top), y(peak) - 12, lang === 'ko' ? `이긴 날만 더하면 순이익의 ${pct(peak)}` : `winning days alone: ${pct(peak)} of the net`, 'ov-strong', 'middle');
    OV.text(ov, R.x + R.w, R.y + R.h + 24, lang === 'ko' ? '좋은 날부터 나쁜 날 순 →' : 'days, best to worst →', 'ov-tick', 'end');
    OV.text(ov, R.x, R.y - 14, lang === 'ko' ? '순실현손익 누적 비중' : 'running share of net realised PnL', 'ov-tick');
    return {
      unit: lang === 'ko' ? '점 하나 = 실현손익이 기록된 하루' : '1 dot = 1 day with realised PnL', overlay: OV.end(ov),
      tip: (i) => { const d = i - OFF.day; const v = A.days.pnl[d]; return v == null ? null : dayTip(d, `${v > 0 ? '+' : ''}${num(v, 2)} BTC`); },
    };
  };

  function equityCurve(T_, R, valueOf, lo, hi, color, alpha) {
    const x = dayX(R), y = logS(lo, hi, R.y + R.h, R.y);
    A.days.eq.forEach((_, d) => { const v = valueOf(d); if (v != null && v > 0) put(T_, OFF.day + d, x(d), y(v), 2.2, color, alpha); });
    return { x, y };
  }

  SCENES.payday = (T_, S) => {
    const R = inset(S, PLOT);
    const { x, y } = equityCurve(T_, R, (d) => A.days.eq[d], 0.1, 3000, C.ink, 0.55);
    const ev = CARD.payday.numbers.events;
    const start = Date.parse(A.days.start + 'T00:00:00Z');
    ev.forEach((e, k) => {
      const d = Math.round((Date.parse(e.day + 'T00:00:00Z') - start) / 864e5);
      const eq = A.days.eq[d] ?? A.days.eq[d - 1];
      put(T_, OFF.event + k, x(d), y(Math.max(0.1, eq)), 4 + Math.sqrt(e.btc) * 0.9, e.near ? C.bright : C.btc, 0.95);
    });
    const ov = OV.start();
    [1, 10, 100, 1000].forEach((v) => { OV.line(ov, R.x, y(v), R.x + R.w, y(v), 'ov-grid'); OV.text(ov, R.x - 8, y(v) + 4, `${v} BTC`, 'ov-tick', 'end'); });
    OV.yearAxis(ov, R, (m) => R.x + (m / T_END) * R.w);
    const lk = lang === 'ko' ? ['30일 고점의 5% 이내 출금', '그 밖의 출금', '계좌 자산(BTC, 로그)'] : ['withdrawal within 5% of a 30-day high', 'other withdrawal', 'account equity (BTC, log)'];
    OV.legend(ov, [[C.bright, lk[0]], [C.btc, lk[1]]], R.x + 8, R.y - 14, R.w - 8, true);
    return {
      unit: lang === 'ko' ? '작은 점 = 하루의 자산, 큰 점 = 출금 한 번' : 'small dot = 1 day of equity, large dot = 1 withdrawal', overlay: OV.end(ov),
      tip: (i) => {
        if (i >= OFF.event && i < OFF.event + ev.length) { const e = ev[i - OFF.event]; return `<b>${e.day}</b><br>${lang === 'ko' ? '출금' : 'withdrew'} ${num(e.btc, 2)} BTC (${pct(e.share)} ${lang === 'ko' ? '자산 대비' : 'of equity'})`; }
        const d = i - OFF.day; return A.days.eq[d] == null ? null : dayTip(d, `${num(A.days.eq[d], 1)} BTC`);
      },
    };
  };

  const BUCKET_NAMES = { en: ['Net short bet', 'Parked in dollars', 'Partly hedged', 'Like Bitcoin', 'Leveraged long'], ko: ['순숏 베팅', '달러로 파킹', '일부 헤지', 'BTC와 비슷', '레버리지 롱'] };
  const bucketOf = (e) => (e <= -0.25 ? 0 : e < 0.25 ? 1 : e < 0.85 ? 2 : e <= 1.15 ? 3 : 4);

  SCENES['short-is-not-bearish'] = (T_, S) => {
    // Every other net-short hour, sorted by the whole account's exposure and stacked by bucket.
    const hours = A.short_hours.filter((_, k) => k % 2 === 0);
    const groups = [[], [], [], []];
    hours.forEach((e) => groups[Math.min(3, bucketOf(e))].push(e));
    groups.forEach((g) => g.sort((a, b) => a - b));
    const R = inset(S, { l: 24, r: 24, t: 74, b: 70 });
    const f = fitColumns(groups.map((g) => g.length), R, 0.5, 9);
    const split = CARD['short-is-not-bearish'].numbers.exposure_split;
    const ov = OV.start();
    const at = [];
    let i = OFF.hour;
    groups.forEach((g, b) => {
      g.forEach((e, j) => { const [x, y] = colDot(f, b, j); at[i - OFF.hour] = e; put(T_, i++, x, y, f.s * 0.86, C.exposure[b], 0.92); });
      const cx = f.x0 + b * f.pitch + f.colW / 2;
      OV.text(ov, cx, f.base - Math.ceil(g.length / f.k) * f.s - 10, pct(split[b]), 'ov-strong', 'middle');
      OV.text(ov, cx, f.base + 22, BUCKET_NAMES[lang][b], 'ov', 'middle');
      OV.text(ov, cx, f.base + 40, ['≤ -0.25x', '-0.25x to 0.25x', '0.25x to 0.85x', '0.85x to 1x'][b], 'ov-tick', 'middle');
    });
    OV.text(ov, R.x, R.y - 50, lang === 'ko' ? '숏이던 시간을 그때 계좌 전체의 BTC 노출도로 나눴다' : "Short hours, sorted by the whole account's Bitcoin exposure at the time", 'ov-tick');
    return {
      unit: lang === 'ko' ? '점 하나 = XBTUSD 순숏이던 2시간(2019~2021)' : '1 dot = 2 hours net short XBTUSD, 2019-2021', overlay: OV.end(ov),
      tip: (i) => { const e = at[i - OFF.hour]; return e == null ? null : `${t('exposure')} ${e.toFixed(2)}x<br>${BUCKET_NAMES[lang][bucketOf(e)]}`; },
    };
  };

  SCENES['account-shape'] = (T_, S) => {
    const b = A.days.bucket;
    const quarters = new Map();
    b.forEach((v, d) => {
      if (v == null) return;
      const dt = dayDate(d);
      const q = `${dt.getUTCFullYear()}Q${Math.floor(dt.getUTCMonth() / 3) + 1}`;
      if (!quarters.has(q)) quarters.set(q, []);
      quarters.get(q).push(d);
    });
    const keys = [...quarters.keys()];
    const R = inset(S, { l: 20, r: 20, t: 60, b: 60 });
    const f = fitColumns(keys.map((k) => quarters.get(k).length), R, 0.35, 11);
    keys.forEach((q, g) => {
      const ds = quarters.get(q).slice().sort((a, c) => b[a] - b[c] || a - c);
      ds.forEach((d, j) => { const [x, y] = colDot(f, g, j); put(T_, OFF.day + d, x, y, f.s * 0.84, C.exposure[b[d]], 0.95); });
    });
    const ov = OV.start();
    keys.forEach((q, g) => { if (q.endsWith('Q1') || g === 0) OV.text(ov, f.x0 + g * f.pitch, f.base + 22, q.slice(0, 4), 'ov-tick'); });
    OV.legend(ov, [4, 3, 2, 1, 0].map((k) => [C.exposure[k], BUCKET_NAMES[lang][k]]), R.x, R.y - 30, R.w, true);
    return { unit: lang === 'ko' ? '점 하나 = 하루, 그날 노출도 중앙값의 색. 기둥 하나 = 분기' : '1 dot = 1 day, colored by its median exposure; 1 column = 1 quarter', overlay: OV.end(ov), tip: (i) => { const d = i - OFF.day; return b[d] == null ? null : dayTip(d, `${t('exposure')} ${A.days.exp[d]?.toFixed(2)}x · ${BUCKET_NAMES[lang][b[d]]}`); } };
  };

  SCENES['two-currencies'] = (T_, S) => {
    const R = inset(S, PLOT);
    const x = dayX(R), y = lin(-0.75, 0, R.y + R.h, R.y);
    const n = A.days.n;
    for (let d = 0; d < n; d++) {
      const b = A.days.dd_btc[d], u = A.days.dd_usd[d];
      if (b != null) put(T_, OFF.day + d, x(d), y(Math.max(-0.75, b)), 3, C.btc, 0.9);
      if (u != null) put(T_, OFF.minute + d, x(d), y(Math.max(-0.75, u)), 3, C.usd, 0.9);
    }
    const ov = OV.start();
    [0, -0.25, -0.5, -0.75].forEach((g) => { OV.line(ov, R.x, y(g), R.x + R.w, y(g), 'ov-grid'); OV.text(ov, R.x - 8, y(g) + 4, pct(g), 'ov-tick', 'end'); });
    // Label each year's low in both units.
    const nn = CARD['two-currencies'].numbers;
    const start = Date.parse(A.days.start + 'T00:00:00Z');
    const dayOf = (ds) => Math.round((Date.parse(ds + 'T00:00:00Z') - start) / 864e5);
    Object.keys(nn.worst_btc).forEach((yr) => {
      [[nn.worst_btc[yr], nn.worst_btc_day[yr], 'BTC', 14], [nn.worst_usd[yr], nn.worst_usd_day[yr], 'USD', 30]].forEach(([v, ds, u, dy]) => {
        const d = dayOf(ds);
        OV.line(ov, x(d), y(v) + 4, x(d), y(v) + dy - 10, 'ov-rule');
        OV.text(ov, x(d), y(v) + dy, `${u} ${pct(v)} ${ds.slice(5)}`, 'ov-strong', 'middle');
      });
    });
    OV.yearAxis(ov, R, (m) => R.x + (m / T_END) * R.w);
    OV.legend(ov, [[C.btc, lang === 'ko' ? '비트코인 기준 낙폭' : 'drawdown counted in bitcoin'], [C.usd, lang === 'ko' ? '달러 기준 낙폭' : 'drawdown counted in dollars']], R.x + 8, R.y - 14, R.w - 8, true);
    return {
      unit: lang === 'ko' ? '점 하나 = 하루(그해 고점 대비)' : '1 dot = 1 day, measured from that year\'s high', overlay: OV.end(ov),
      tip: (i) => {
        const d = i >= OFF.minute ? i - OFF.minute : i - OFF.day;
        if (d < 0 || d >= n || A.days.dd_btc[d] == null) return null;
        return dayTip(d, `BTC ${pct(A.days.dd_btc[d], 1)} · USD ${pct(A.days.dd_usd[d], 1)}`);
      },
    };
  };

  SCENES.leverage = (T_, S) => {
    const R = inset(S, PLOT);
    const x = dayX(R), y = logS(0.05, 60, R.y + R.h, R.y);
    A.days.lev.forEach((v, d) => { if (v != null && v > 0) put(T_, OFF.day + d, x(d), y(v), 2.6, v >= 5 ? C.loss : C.ink, 0.85); });
    const ov = OV.start();
    [0.1, 1, 5, 10, 50].forEach((v) => { OV.line(ov, R.x, y(v), R.x + R.w, y(v), 'ov-grid'); OV.text(ov, R.x - 8, y(v) + 4, `${v}x`, 'ov-tick', 'end'); });
    const p95 = CARD.leverage.numbers.p95;
    Object.entries(p95).forEach(([yr, v]) => {
      const a = Math.max(0, yearMin(+yr)), b = Math.min(T_END, yearMin(+yr + 1));
      const xa = R.x + (a / T_END) * R.w, xb = R.x + (b / T_END) * R.w;
      OV.line(ov, xa, y(v), xb, y(v), 'ov-mark');
      OV.text(ov, xb - 4, y(v) - 6, `p95 ${v.toFixed(1)}x`, 'ov-strong', 'end');
    });
    OV.yearAxis(ov, R, (m) => R.x + (m / T_END) * R.w);
    return { unit: lang === 'ko' ? '점 하나 = 하루의 최대 총 레버리지(로그)' : '1 dot = 1 day, its highest gross leverage (log)', overlay: OV.end(ov), tip: (i) => { const d = i - OFF.day; const v = A.days.lev[d]; return v == null ? null : dayTip(d, `${lang === 'ko' ? '최대 레버리지' : 'max leverage'} ${v.toFixed(2)}x`); } };
  };

  SCENES.liquidations = (T_, S) => {
    const R = inset(S, PLOT);
    let lo = Infinity, hi = 0;
    for (const p of D.px) { if (p < lo) lo = p; if (p > hi) hi = p; }
    const x = timeX(R), y = logS(lo * 0.92, hi * 1.06, R.y + R.h, R.y);
    for (let i = 0; i < D.t.length; i++) put(T_, OFF.decision + i, x(D.t[i]), y(D.px[i]), 1.5, C.ink, 0.3);
    // Each liquidation sits on the price line at its minute.
    A.liq.forEach((e, k) => {
      let j = 0;
      while (j < D.t.length - 1 && D.t[j + 1] <= e.t) j++;
      put(T_, OFF.event + k, x(e.t), y(D.px[j]), 5 + Math.min(16, Math.sqrt(e.btc) * 2.2), C.loss, 0.92);
    });
    const ov = OV.start();
    OV.yearAxis(ov, R, x);
    const by = CARD.liquidations.numbers.by_year;
    Object.entries(by).forEach(([yr, n], k) => OV.text(ov, R.x + k * Math.min(120, R.w / 4.5), R.y - 14, `${yr}: ${n}`, n ? 'ov-alert' : 'ov-tick'));
    return {
      unit: lang === 'ko' ? '빨간 점 = 강제청산 한 번(크기 = BTC 규모), 흐린 점 = 결정' : 'red dot = 1 liquidation (size = BTC), faint dots = decisions', overlay: OV.end(ov),
      tip: (i) => { if (i >= OFF.event && i < OFF.event + A.liq.length) { const e = A.liq[i - OFF.event]; return `<b>${minDate(e.t).toISOString().slice(0, 16).replace('T', ' ')} UTC</b><br>${e.sym} ${num(e.qty)} ${lang === 'ko' ? '계약' : 'contracts'} · ${num(e.btc, 2)} BTC`; } return null; },
    };
  };

  SCENES['year-2018'] = (T_, S) => {
    const R = inset(S, PLOT);
    const months = 10;
    const y = logS(0.05, 60, R.y + R.h, R.y);
    const colW = R.w / months;
    for (let i = 0; i < D.t.length; i++) {
      const dt = minDate(D.t[i]);
      if (dt.getUTCFullYear() !== 2018) continue;
      const lev = A.dx.lev[i];
      if (lev == null || lev <= 0) continue;
      const m = dt.getUTCMonth() - 2;
      const jx = (hash(i, 9) - 0.5) * colW * 0.7;
      put(T_, OFF.decision + i, R.x + (m + 0.5) * colW + jx, y(lev), 2.2, lev >= 10 ? C.loss : C.ink, 0.7);
    }
    const n = CARD['year-2018'].numbers;
    const ov = OV.start();
    [0.1, 1, 10, 50].forEach((v) => { OV.line(ov, R.x, y(v), R.x + R.w, y(v), 'ov-grid'); OV.text(ov, R.x - 8, y(v) + 4, `${v}x`, 'ov-tick', 'end'); });
    Object.entries(n.p95).forEach(([day, v], m) => {
      OV.line(ov, R.x + m * colW + colW * 0.12, y(v), R.x + (m + 1) * colW - colW * 0.12, y(v), 'ov-mark');
      const lab = lang === 'ko' ? `${m + 3}월` : new Date(day + 'T00:00:00Z').toLocaleString('en-US', { month: 'short', timeZone: 'UTC' });
      OV.text(ov, R.x + (m + 0.5) * colW, R.y + R.h + 22, lab, 'ov-tick', 'middle');
      const liq = n.liquidations[day];
      if (liq) OV.text(ov, R.x + (m + 0.5) * colW, R.y - 10, `${liq}`, 'ov-alert', 'middle');
    });
    OV.text(ov, R.x - 8, R.y - 10, lang === 'ko' ? '강제청산' : 'liquidations', 'ov-tick', 'end');
    return { unit: lang === 'ko' ? '점 하나 = 2018년 결정 하나, 높이 = 그때의 총 레버리지(로그). 가로선 = 월별 95백분위' : '1 dot = 1 decision in 2018 at its gross leverage (log); bars = monthly 95th percentile', overlay: OV.end(ov), tip: (i) => (i < D.t.length ? decisionTip(i) + `<br>${lang === 'ko' ? '총 레버리지' : 'gross leverage'} ${A.dx.lev[i]?.toFixed(1)}x` : null) };
  };

  SCENES['distance-to-zero'] = (T_, S) => {
    const R = inset(S, { l: 64, r: 28, t: 64, b: 52 });
    const x = dayX(R), y = logS(0.01, 1.2, R.y + R.h, R.y + 22);
    A.days.dz.forEach((v, d) => {
      if (A.days.exp[d] == null) return;
      if (v == null) { put(T_, OFF.day + d, x(d), R.y + 3 + hash(d, 4) * 10, 2, C.ink, 0.6); return; }
      const a = Math.abs(v);
      put(T_, OFF.day + d, x(d), y(Math.min(1.2, a)), a < 0.35 ? 3.4 : 2.4, v > 0 ? C.loss : C.buy, a < 0.35 ? 1 : 0.7);
    });
    const ov = OV.start();
    [0.02, 0.05, 0.1, 0.25, 0.5, 1].forEach((g) => { OV.line(ov, R.x, y(g), R.x + R.w, y(g), 'ov-grid'); OV.text(ov, R.x - 8, y(g) + 4, pct(g), 'ov-tick', 'end'); });
    OV.text(ov, R.x - 8, R.y + 12, lang === 'ko' ? '불가능' : 'none', 'ov-tick', 'end');
    const nz = CARD['distance-to-zero'].numbers;
    const start = Date.parse(A.days.start + 'T00:00:00Z');
    Object.entries(nz.closest).forEach(([yr, v]) => {
      const d = Math.floor((Date.parse(nz.closest_at[yr].replace(' ', 'T') + 'Z') - start) / 864e5);
      OV.text(ov, x(d) + 8, y(v) + 16, `${yr} ${pct(v, 1)}`, 'ov-strong');
    });
    OV.yearAxis(ov, R, (m) => R.x + (m / T_END) * R.w);
    OV.legend(ov, [[C.loss, lang === 'ko' ? '이만큼 하락하면 0' : 'a fall this big empties it'], [C.buy, lang === 'ko' ? '이만큼 상승하면 0' : 'a rise this big empties it'],
      [C.ink, lang === 'ko' ? '어떤 움직임으로도 0이 안 됨' : 'no move empties it']], R.x + 8, R.y - 30, R.w - 8, true);
    return {
      unit: lang === 'ko' ? '점 하나 = 하루, 그날 가장 위험했던 시간 기준(로그)' : '1 dot = 1 day, at its closest hour (log)', overlay: OV.end(ov),
      tip: (i) => { const d = i - OFF.day; if (d < 0 || d >= A.days.n || A.days.exp[d] == null) return null; const v = A.days.dz[d]; return dayTip(d, v == null ? (lang === 'ko' ? 'BTC가 어떻게 움직여도 0이 안 됨' : 'no Bitcoin move could empty it') : `${lang === 'ko' ? (v > 0 ? '하락' : '상승') : (v > 0 ? 'a fall of' : 'a rise of')} ${pct(Math.abs(v), 1)}`); },
    };
  };

  function tapeCase(id) {
    return (T_, S) => {
      const c = CARD[id].chart;
      const R = inset(S, { l: 60, r: 24, t: 40, b: 46 });
      const n = c.price.length;
      const lo = Math.min(...c.price), hi = Math.max(...c.price);
      const priceH = R.h * 0.62, volTop = R.y + priceH + 22, volH = R.h - priceH - 22;
      const x = lin(0, n - 1, R.x, R.x + R.w), y = lin(lo, hi, R.y + priceH, R.y);
      c.price.forEach((p, k) => put(T_, OFF.minute + k, x(k), y(p), 2.6, C.bright, 0.95));
      // His volume: 1 dot per unit of contracts, stacked up (buys) and down (sells) from the middle line.
      // The unit is sized so the busiest 5 minutes fit their half-panel and the whole case fits its particles.
      const tot = c.buy.reduce((a, b) => a + b, 0) + c.sell.reduce((a, b) => a + b, 0);
      const step = 2.4, fit = Math.max(4, Math.floor((volH / 2) / step));
      const unit = Math.max(0.25, Math.max(...c.buy, ...c.sell) / fit, tot / 2200);
      const mid = volTop + volH / 2;
      let i = OFF.minute + n;
      c.buy.forEach((v, k) => { for (let j = 0; j < Math.round(v / unit) && i < OFF.event; j++) put(T_, i++, x(k), mid - (j + 0.5) * step, step * 0.9, C.buy, 0.9); });
      c.sell.forEach((v, k) => { for (let j = 0; j < Math.round(v / unit) && i < OFF.event; j++) put(T_, i++, x(k), mid + (j + 0.5) * step, step * 0.9, C.sell, 0.9); });
      const ov = OV.start();
      OV.text(ov, R.x - 8, y(hi) + 4, `$${num(hi)}`, 'ov-tick', 'end');
      OV.text(ov, R.x - 8, y(lo) + 4, `$${num(lo)}`, 'ov-tick', 'end');
      OV.line(ov, R.x, mid, R.x + R.w, mid, 'ov-rule');
      OV.line(ov, x(n / 2), R.y, x(n / 2), R.y + R.h, 'ov-grid');
      OV.text(ov, R.x, R.y + R.h + 22, c.days[0], 'ov-tick');
      OV.text(ov, x(n / 2) + 6, R.y + R.h + 22, c.days[1], 'ov-tick');
      OV.legend(ov, [[C.bright, lang === 'ko' ? 'XBTUSD 가격(테이프, 5분)' : 'XBTUSD price (tape, 5 min)'], [C.buy, lang === 'ko' ? '그의 매수' : 'his buys'],
        [C.sell, lang === 'ko' ? '그의 매도' : 'his sells']], R.x + 8, R.y - 14, R.w - 8, true);
      return { unit: lang === 'ko' ? `큰 점 = 5분 가격, 작은 점 = ${num(unit, 2)}M 계약` : `large dots = 5-minute price; small dot = ${num(unit, 2)}M contracts`, overlay: OV.end(ov), tip: null };
    };
  }
  SCENES['worst-day'] = tapeCase('worst-day');
  SCENES['black-thursday'] = tapeCase('black-thursday');

  function lotStrip(T_, S, lots, split) {
    const R = inset(S, { l: 56, r: 24, t: 40, b: 52 });
    const years = lots.years;
    const rowH = R.h / years.length;
    const x = logS(1 / 60, 24 * 60, R.x, R.x + R.w);
    for (let k = 0; k < lots.y.length; k++) {
      const yi = lots.y[k];
      let yc = R.y + (yi + 0.5) * rowH, spread = rowH * 0.72;
      let color = C.ink;
      if (split) {
        const win = lots.w[k];
        yc = R.y + yi * rowH + (win ? 0.3 : 0.72) * rowH;
        spread = rowH * 0.34;
        color = win ? C.ink : C.loss;
      }
      put(T_, OFF.lot + k, x(Math.min(24 * 60, lots.h[k])), yc + (hash(k, 5) - 0.5) * spread, 2, color, 0.6);
    }
    const ov = OV.start();
    [[1 / 60, '1m'], [10 / 60, '10m'], [1, '1h'], [6, '6h'], [24, '1d'], [168, '7d'], [720, '30d']].forEach(([h, l]) => {
      OV.line(ov, x(h), R.y, x(h), R.y + R.h, 'ov-grid');
      OV.text(ov, x(h), R.y + R.h + 22, l, 'ov-tick', 'middle');
    });
    years.forEach((yr, yi) => OV.text(ov, R.x - 10, R.y + (yi + 0.5) * rowH + 4, String(yr), 'ov-tick', 'end'));
    return { R, x, rowH, ov };
  }

  SCENES['scalps-to-swings'] = (T_, S) => {
    const lots = A.lots.fifo;
    const { R, x, rowH, ov } = lotStrip(T_, S, lots, false);
    const med = CARD['scalps-to-swings'].numbers.median_hold_hours;
    lots.years.forEach((yr, yi) => {
      const h = med[String(yr)];
      OV.line(ov, x(h), R.y + yi * rowH + 6, x(h), R.y + (yi + 1) * rowH - 6, 'ov-mark');
      OV.text(ov, x(h) + 6, R.y + yi * rowH + 16, h < 1 ? `${Math.round(h * 60)} min` : `${h.toFixed(1)} h`, 'ov-strong');
    });
    return { unit: lang === 'ko' ? '점 하나 = 그해 청산 계약의 1/2,000(FIFO 보유시간, 로그). 세로선 = 중앙값' : "1 dot = 1/2,000 of the year's closed contracts (FIFO hold, log); line = median", overlay: OV.end(ov), tip: null };
  };

  SCENES['winners-first'] = (T_, S) => {
    const lots = A.lots.lifo;
    const { R, x, rowH, ov } = lotStrip(T_, S, lots, true);
    const n = CARD['winners-first'].numbers;
    const hm = (h) => (h < 1 ? `${Math.round(h * 60)}${lang === 'ko' ? '분' : ' min'}` : `${h.toFixed(1)}${lang === 'ko' ? '시간' : ' h'}`);
    lots.years.forEach((yr, yi) => {
      [[n.win_hours[yr], 0.3], [n.loss_hours[yr], 0.72]].forEach(([h, f]) => {
        const yc = R.y + yi * rowH + f * rowH;
        OV.line(ov, x(h), yc - rowH * 0.19, x(h), yc + rowH * 0.19, 'ov-mark');
        OV.text(ov, x(h) + 6, yc + 4, hm(h), 'ov-strong');
      });
    });
    OV.legend(ov, [[C.ink, lang === 'ko' ? '이익으로 닫힌 계약(윗줄)' : 'closed at a gain (upper lane)'], [C.loss, lang === 'ko' ? '손실로 닫힌 계약(아랫줄)' : 'closed at a loss (lower lane)']], R.x + 8, R.y - 14, R.w - 8, true);
    return { unit: lang === 'ko' ? '점 하나 = 그해 청산 계약의 1/2,000(LIFO, 로그). 세로선 = 중앙값' : "1 dot = 1/2,000 of the year's closed contracts (LIFO, log); line = median", overlay: OV.end(ov), tip: null };
  };

  SCENES['order-craft'] = (T_, S) => {
    const o = A.orders;
    const R = inset(S, PLOT);
    const x = timeX(R), y = lin(2, 7.8, R.y + R.h, R.y);
    for (let k = 0; k < o.t.length; k++) {
      const mk = o.mk[k];
      put(T_, OFF.order + k, x(o.t[k]), y(clamp(o.lu[k], 2, 7.8)), 2.1, mk >= 0.7 ? C.ink : mk <= 0.3 ? C.sell : '#8a7f78', 0.66);
    }
    const ov = OV.start();
    [[3, '$1k'], [4, '$10k'], [5, '$100k'], [6, '$1M'], [7, '$10M']].forEach(([v, l]) => { OV.line(ov, R.x, y(v), R.x + R.w, y(v), 'ov-grid'); OV.text(ov, R.x - 8, y(v) + 4, l, 'ov-tick', 'end'); });
    OV.yearAxis(ov, R, x);
    OV.legend(ov, [[C.ink, lang === 'ko' ? '대부분 호가에 걸려 체결(메이커)' : 'mostly rested on the book (maker)'], [C.sell, lang === 'ko' ? '대부분 바로 체결(테이커)' : 'mostly took liquidity (taker)']], R.x + 8, R.y - 14, R.w - 8, true);
    return { unit: lang === 'ko' ? '점 하나 = 주문 하나, 높이 = 주문 금액(로그)' : '1 dot = 1 order at its size (log)', overlay: OV.end(ov), tip: (i) => orderTip(i - OFF.order) };
  };

  SCENES['plain-orders'] = (T_, S) => {
    const o = A.orders;
    const { R, g } = ordersGrid(T_, S, (k) => (o.src[k] === 3 ? C.btc : (o.flag[k] & 2) ? C.buy : C.ink), (k, s) => (o.src[k] === 3 ? Math.max(6, s * 2.6) : (o.flag[k] & 2) ? s * 1.4 : s * 0.66), (k) => (o.src[k] === 3 ? 1 : (o.flag[k] & 2) ? 0.95 : 0.34));
    const n = CARD['plain-orders'].numbers;
    const ov = OV.start();
    // Mark the row where each year's first order sits.
    [2019, 2020, 2021].forEach((yr) => {
      const k = o.t.findIndex((m) => m >= yearMin(yr));
      if (k < 0) return;
      const yRow = g.y0 + Math.floor(k / g.cols) * g.s - g.s / 2;
      OV.line(ov, R.x - 8, yRow, R.x + R.w + 4, yRow, 'ov-rule');
      OV.text(ov, R.x + R.w + 2, yRow - 4, String(yr), 'ov-tick', 'end');
    });
    OV.text(ov, R.x + R.w + 2, R.y - 4, '2018', 'ov-tick', 'end');
    const yEnd = OV.legend(ov, [[C.btc, lang === 'ko' ? `스톱 주문 ${n.stops}개` : `${n.stops} stop orders`], [C.buy, lang === 'ko' ? `숨긴 주문이 섞인 주문 ${n.hidden_orders}개` : `${n.hidden_orders} orders with hidden fills`]], R.x, R.y + R.h + 30, R.w);
    OV.text(ov, R.x, yEnd + 2, lang === 'ko' ? '아이스버그 주문: 0개' : 'Iceberg orders: 0', 'ov-strong');
    return { unit: lang === 'ko' ? '점 하나 = 주문 하나(시간순)' : '1 dot = 1 order, in time order', overlay: OV.end(ov), tip: (i) => orderTip(i - OFF.order) };
  };

  SCENES['underwater-adds'] = (T_, S) => {
    const R = inset(S, PLOT);
    const x = timeX(R), y = lin(-4, 4, R.y + R.h, R.y);
    let n = 0;
    for (let i = 0; i < D.t.length; i++) {
      const g = A.dx.gap[i];
      if (g == null) continue;
      n++;
      put(T_, OFF.decision + i, x(D.t[i]), y(clamp(-g, -4, 4)), 2.8, g > 0 ? C.loss : C.ink, 0.8);
    }
    const ov = OV.start();
    [-4, -2, 0, 2, 4].forEach((v) => { OV.line(ov, R.x, y(v), R.x + R.w, y(v), v === 0 ? 'ov-rule' : 'ov-grid'); OV.text(ov, R.x - 8, y(v) + 4, `${v > 0 ? '+' : ''}${v}%`, 'ov-tick', 'end'); });
    OV.text(ov, R.x + R.w, y(0) - 8, lang === 'ko' ? '포지션 평균 진입가' : 'average entry of the position', 'ov-tick', 'end');
    const share = CARD['underwater-adds'].numbers.underwater_share;
    OV.text(ov, R.x + 6, y(-3.4), lang === 'ko' ? `손실 중에 추가 ${pct(share)}` : `added while underwater: ${pct(share)}`, 'ov-alert');
    OV.text(ov, R.x + 6, y(3.4), lang === 'ko' ? `이익 중에 추가 ${pct(1 - share)}` : `added while in profit: ${pct(1 - share)}`, 'ov-strong');
    OV.yearAxis(ov, R, x);
    return { unit: lang === 'ko' ? `점 하나 = 기존 포지션에 더한 결정 하나(${num(n)}개)` : `1 dot = 1 decision that added to a position (${num(n)})`, overlay: OV.end(ov), tip: (i) => (A.dx.gap[i] == null ? null : decisionTip(i) + `<br>${lang === 'ko' ? '진입가 대비' : 'vs entry'} ${A.dx.gap[i] > 0 ? '-' : '+'}${Math.abs(A.dx.gap[i]).toFixed(2)}%`) };
  };

  SCENES.clock = (T_, S) => {
    const cx = S.x + S.w / 2, cy = S.y + S.h / 2 + 6;
    const Rm = Math.min(S.w, S.h) / 2 - 44, R0 = Rm * 0.3, ring = (Rm - R0) / 7;
    for (let i = 0; i < D.t.length; i++) {
      const kst = new Date(T0 + D.t[i] * 60000 + 9 * 3600e3);
      const minute = kst.getUTCHours() * 60 + kst.getUTCMinutes();
      const wd = (kst.getUTCDay() + 6) % 7;
      const ang = (minute / 1440) * Math.PI * 2 - Math.PI / 2;
      const r = R0 + (wd + 0.12 + hash(i, 6) * 0.76) * ring;
      put(T_, OFF.decision + i, cx + Math.cos(ang) * r, cy + Math.sin(ang) * r, 1.9, wd >= 5 ? C.btc : C.ink, 0.6);
    }
    const ov = OV.start();
    for (let h = 0; h < 24; h += 3) {
      const ang = (h / 24) * Math.PI * 2 - Math.PI / 2;
      OV.line(ov, cx + Math.cos(ang) * R0 * 0.9, cy + Math.sin(ang) * R0 * 0.9, cx + Math.cos(ang) * (Rm + 6), cy + Math.sin(ang) * (Rm + 6), 'ov-grid');
      OV.text(ov, cx + Math.cos(ang) * (Rm + 22), cy + Math.sin(ang) * (Rm + 22) + 4, `${String(h).padStart(2, '0')}`, 'ov-tick', 'middle');
    }
    OV.text(ov, cx, cy - 4, 'KST', 'ov-strong', 'middle');
    OV.text(ov, cx, cy + 14, lang === 'ko' ? '안쪽 월 → 바깥 일' : 'Mon inside, Sun outside', 'ov-tick', 'middle');
    OV.swatch(ov, S.x + 14, S.y + 22, C.btc, lang === 'ko' ? '주말' : 'weekend');
    return { unit: lang === 'ko' ? '점 하나 = 결정 하나, 한국 시각의 시계 위에' : '1 dot = 1 decision, on a 24-hour Korean clock', overlay: OV.end(ov), tip: (i) => (i < D.t.length ? decisionTip(i) : null) };
  };

  SCENES['jev-check'] = (T_, S) => {
    const R = inset(S, { l: 70, r: 30, t: 56, b: 56 });
    const x = lin(0, 1, R.x, R.x + R.w);
    const bandH = R.h / 2 - 12;
    let agree = 0, n = 0;
    for (let i = 0; i < D.t.length; i++) {
      const p = D.against_move[i];
      if (p == null || A.dx.move[i] < 0) continue;
      const truth = A.dx.move[i] === 0;
      const ok = (p > 0.5) === truth;
      agree += ok; n++;
      const y0 = truth ? R.y : R.y + R.h / 2 + 12;
      put(T_, OFF.decision + i, x(clamp(p + (hash(i, 7) - 0.5) * 0.012, 0, 1)), y0 + hash(i, 8) * bandH, ok ? 2 : 3.6, ok ? C.ink : C.loss, ok ? 0.5 : 1);
    }
    const ov = OV.start();
    [0, 0.3, 0.5, 0.7, 1].forEach((g) => { OV.line(ov, x(g), R.y, x(g), R.y + R.h, g === 0.5 ? 'ov-rule' : 'ov-grid'); OV.text(ov, x(g), R.y + R.h + 22, String(g), 'ov-tick', 'middle'); });
    OV.text(ov, R.x - 10, R.y + bandH / 2, lang === 'ko' ? '정답: 역행' : 'code: yes', 'ov-tick', 'end');
    OV.text(ov, R.x - 10, R.y + R.h / 2 + 12 + bandH / 2, lang === 'ko' ? '정답: 아님' : 'code: no', 'ov-tick', 'end');
    OV.text(ov, R.x, R.y - 14, lang === 'ko' ? `"24시간 흐름 역행"에 대한 Jev의 확률 →  일치 ${pct(agree / n, 1)}` : `Jev's probability for "against the 24h move" →  agreement ${pct(agree / n, 1)}`, 'ov-strong');
    return { unit: lang === 'ko' ? '점 하나 = 결정 하나. 빨간 점 = 코드와 Jev가 엇갈린 결정' : '1 dot = 1 decision; red = Jev and code disagree', overlay: OV.end(ov), tip: (i) => (i < D.t.length ? decisionTip(i) + `<br>Jev ${pct(D.against_move[i])}` : null) };
  };

  SCENES.regimes = (T_, S) => {
    const n = CARD.regimes.numbers;
    const years = Object.keys(n.against_by_year);
    const groups = years.map(() => ({ against: [], flat: [], with: [] }));
    for (let i = 0; i < D.t.length; i++) {
      const mv = A.dx.move[i];
      if (mv < 0) continue;
      const g = groups[years.indexOf(String(minDate(D.t[i]).getUTCFullYear()))];
      if (!g) continue;
      [g.against, g.flat, g.with][mv].push(i);
    }
    const R = inset(S, { l: 30, r: 60, t: 50, b: 60 });
    const totals = groups.map((g) => g.against.length + g.flat.length + g.with.length);
    // 100% columns: the same height for every year, so shares compare directly.
    const H = R.h, colW = Math.min(150, R.w / (years.length * 1.7)), gap = (R.w - colW * years.length) / (years.length + 1);
    const ov = OV.start();
    years.forEach((yr, gi) => {
      const g = groups[gi], tot = totals[gi];
      const k = Math.max(1, Math.round(Math.sqrt((tot * colW) / H)));
      const s = colW / k;
      const rowsTotal = Math.ceil(tot / k);
      const sy = H / rowsTotal;
      const x0 = R.x + gap + gi * (colW + gap);
      let j = 0;
      [[g.against, C.btc], [g.flat, '#4b5a66'], [g.with, C.buy]].forEach(([arr, color]) => arr.forEach((i) => {
        const row = Math.floor(j / k), c = j % k;
        put(T_, OFF.decision + i, x0 + (c + 0.5) * s, R.y + R.h - (row + 0.5) * sy, Math.min(s, sy) * 0.86, color, 0.9);
        j++;
      }));
      const yLine = R.y + R.h - n.chance_by_year[yr] * H;
      const yTop = R.y + R.h - n.against_by_year[yr] * H;
      OV.line(ov, x0 - 4, yLine, x0 + colW + 8, yLine, 'ov-mark');
      if (gap > 44) OV.text(ov, x0 + colW + 12, yLine + 4, pct(n.chance_by_year[yr]), 'ov-tick');
      OV.text(ov, x0 + colW / 2, R.y + R.h + 22, yr, 'ov-tick', 'middle');
      OV.text(ov, x0 + colW / 2, Math.max(yTop + 20, Math.min(yLine, yTop) + 20), pct(n.against_by_year[yr]), 'ov-strong', 'middle');
    });
    OV.legend(ov, [[C.btc, lang === 'ko' ? '24시간 흐름 역행' : 'against the 24h move'], ['#4b5a66', lang === 'ko' ? '보합(±1%)' : 'flat (within 1%)'],
      [C.buy, lang === 'ko' ? '흐름을 따름' : 'with the move']], R.x + 4, R.y - 26, R.w - 4, true);
    OV.text(ov, R.x + 4, R.y - 4, lang === 'ko' ? '흰 선 = 방향을 무작위로 골랐을 때의 역행 비중' : 'white line = the against-the-move share if sides were random', 'ov-tick');
    return { unit: lang === 'ko' ? '점 하나 = 결정 하나, 기둥 하나 = 한 해(100%)' : '1 dot = 1 decision; each column is one year at 100%', overlay: OV.end(ov), tip: (i) => (i < D.t.length ? decisionTip(i) + `<br>24h ${A.dx.r24[i] > 0 ? '+' : ''}${A.dx.r24[i]}%` : null) };
  };

  SCENES['into-the-panic'] = (T_, S) => {
    const groups = [[], [], []];
    for (let i = 0; i < D.t.length; i++) {
      if (D.panic[i] != null && D.panic[i] > 0.5) groups[0].push(i);
      else if (D.euphoria[i] != null && D.euphoria[i] > 0.5) groups[2].push(i);
      else groups[1].push(i);
    }
    groups.forEach((g) => g.sort((a, b) => D.side[b] - D.side[a] || a - b));
    const R = inset(S, { l: 20, r: 20, t: 50, b: 64 });
    const widths = [0.22, 0.52, 0.22];
    const names = lang === 'ko' ? ['패닉 매도장', '그 밖의 결정', '급등 과열장'] : ['Panic selling', 'Everything else', 'Buying frenzy'];
    const ov = OV.start();
    let x0 = R.x;
    groups.forEach((g, gi) => {
      const w = R.w * widths[gi] - 14;
      const box = { x: x0, y: R.y, w, h: R.h };
      const f = fitGrid(g.length, box);
      g.forEach((i, j) => put(T_, OFF.decision + i, f.x0 + (j % f.cols) * f.s, f.y0 + Math.floor(j / f.cols) * f.s, f.s * 0.84, D.side[i] ? C.buy : C.sell, 0.92));
      const buys = g.filter((i) => D.side[i] === 1).length;
      OV.text(ov, x0 + w / 2, R.y + R.h + 22, names[gi], 'ov', 'middle');
      OV.text(ov, x0 + w / 2, R.y + R.h + 40, `${lang === 'ko' ? '매수' : 'buys'} ${pct(buys / g.length)} · ${num(g.length)}`, 'ov-strong', 'middle');
      x0 += R.w * widths[gi];
    });
    OV.swatch(ov, R.x + 4, R.y - 20, C.buy, lang === 'ko' ? '매수' : 'buy');
    OV.swatch(ov, R.x + 84, R.y - 20, C.sell, lang === 'ko' ? '매도' : 'sell');
    const both = groups[0].filter((i) => D.euphoria[i] != null && D.euphoria[i] > 0.5).length;
    if (both) OV.text(ov, R.x + R.w, R.y - 16, lang === 'ko' ? `Jev가 둘 다라고 본 ${both}개는 패닉 쪽에 넣었다` : `${both} decisions Jev marked as both sit with panic selling`, 'ov-tick', 'end');
    return { unit: lang === 'ko' ? '점 하나 = 결정 하나, Jev가 본 시장 상태로 나눔' : '1 dot = 1 decision, grouped by the market Jev saw', overlay: OV.end(ov), tip: (i) => (i < D.t.length ? decisionTip(i) : null) };
  };

  SCENES['tilt-check'] = (T_, S) => {
    const R = inset(S, { l: 90, r: 30, t: 50, b: 56 });
    const lanes = [[], []];
    for (let i = 0; i < D.t.length; i++) {
      if (D.after_pain[i] == null || D.boldness[i] == null) continue;
      lanes[D.after_pain[i] > 0.5 ? 0 : 1].push(i);
    }
    const laneH = R.h / 2 - 16;
    const ov = OV.start();
    lanes.forEach((g, li) => {
      const box = { x: R.x, y: R.y + li * (R.h / 2) + 8, w: R.w, h: laneH };
      const pos = dotHist(g.map((i) => D.boldness[i]), 0, 4.0001, 40, box);
      g.forEach((i, k) => put(T_, OFF.decision + i, pos[k][0], pos[k][1], pos[k][2] * 0.86, li ? C.ink : C.btc, 0.85));
      const mean = g.reduce((s, i) => s + D.boldness[i], 0) / g.length;
      const x = lin(0, 4, R.x, R.x + R.w);
      OV.line(ov, x(mean), box.y, x(mean), box.y + box.h, 'ov-mark');
      OV.text(ov, x(mean) + 6, box.y + 12, `${lang === 'ko' ? '평균' : 'mean'} ${mean.toFixed(2)}`, 'ov-strong');
      OV.text(ov, R.x - 10, box.y + box.h / 2, li ? (lang === 'ko' ? '평소' : 'otherwise') : (lang === 'ko' ? '손실 직후' : 'after a loss'), 'ov', 'end');
    });
    const x = lin(0, 4, R.x, R.x + R.w);
    [0, 1, 2, 3, 4].forEach((v) => OV.text(ov, x(v), R.y + R.h + 22, String(v), 'ov-tick', 'middle'));
    OV.text(ov, R.x + R.w, R.y + R.h + 40, lang === 'ko' ? 'Jev의 과감함 점수 →' : "Jev's boldness score →", 'ov-tick', 'end');
    return { unit: lang === 'ko' ? '점 하나 = 결정 하나' : '1 dot = 1 decision', overlay: OV.end(ov), tip: (i) => (i < D.t.length ? decisionTip(i) + `<br>${lang === 'ko' ? '과감함' : 'boldness'} ${D.boldness[i]?.toFixed(2)}` : null) };
  };

  function afterDays(best) {
    return (T_, S) => {
      const R = inset(S, PLOT);
      const x = lin(-0.55, 0.45, R.x, R.x + R.w), y = logS(0.08, 12, R.y + R.h, R.y);
      const n = CARD['after-the-best-days'].numbers;
      const start = Date.parse(A.days.start + 'T00:00:00Z');
      const pick = new Set((best ? n.best_days : n.worst_days).map((ds) => Math.round((Date.parse(ds + 'T00:00:00Z') - start) / 864e5)));
      const y2019 = Math.round((Date.parse('2019-01-01T00:00:00Z') - start) / 864e5);
      for (let d = y2019; d < A.days.n; d++) {
        const r = A.days.r[d], a = A.days.act[d];
        if (r == null || a == null) continue;
        const on = pick.has(d);
        put(T_, OFF.day + d, x(clamp(r, -0.55, 0.45)), y(clamp(Math.max(a, 0.09), 0.08, 12)), on ? 6.5 : 2.6, on ? (best ? C.buy : C.loss) : C.ink, on ? 1 : 0.5);
      }
      const ov = OV.start();
      [0.1, 0.5, 1, 2, 5, 10].forEach((v) => { OV.line(ov, R.x, y(v), R.x + R.w, y(v), v === 1 ? 'ov-rule' : 'ov-grid'); OV.text(ov, R.x - 8, y(v) + 4, `${v}x`, 'ov-tick', 'end'); });
      [-0.5, -0.25, 0, 0.25].forEach((v) => OV.text(ov, x(v), R.y + R.h + 22, pct(v), 'ov-tick', 'middle'));
      OV.text(ov, R.x + R.w, R.y + R.h + 40, lang === 'ko' ? '그날 계좌 수익률(BTC 기준) →' : "the day's account return (BTC) →", 'ov-tick', 'end');
      OV.text(ov, R.x, R.y - 14, lang === 'ko' ? '다음 날 결정 수(평소 대비, 로그)' : 'decisions the next day, vs his usual (log)', 'ov-tick');
      OV.swatch(ov, R.x + R.w - Math.min(170, R.w * 0.32), R.y - 14, best ? C.buy : C.loss, best ? (lang === 'ko' ? '최고의 20일' : 'best 20 days') : (lang === 'ko' ? '최악의 20일' : 'worst 20 days'));
      return { unit: lang === 'ko' ? '점 하나 = 하루(2019~2021)' : '1 dot = 1 day, 2019-2021', overlay: OV.end(ov), tip: (i) => { const d = i - OFF.day; if (A.days.r[d] == null) return null; return dayTip(d, `${lang === 'ko' ? '수익률' : 'return'} ${pct(A.days.r[d], 1)} · ${lang === 'ko' ? '다음 날' : 'next day'} ${A.days.act[d]?.toFixed(2)}x`); } };
    };
  }
  SCENES['after-the-worst-days'] = afterDays(false);
  SCENES['after-the-best-days'] = afterDays(true);

  SCENES.footprint = (T_, S) => {
    const R = inset(S, PLOT);
    const x = dayX(R), y = logS(0.00005, 0.15, R.y + R.h, R.y);
    const top = CARD.footprint.numbers.max_day;
    A.days.share.forEach((v, d) => {
      if (v == null || v <= 0) return;
      const on = ymd(dayDate(d)) === top;
      put(T_, OFF.day + d, x(d), y(v), on ? 8 : 2.4, on ? C.bright : C.ink, on ? 1 : 0.7);
    });
    const ov = OV.start();
    [0.0001, 0.001, 0.01, 0.1].forEach((v) => { OV.line(ov, R.x, y(v), R.x + R.w, y(v), 'ov-grid'); OV.text(ov, R.x - 8, y(v) + 4, pct(v, v < 0.001 ? 2 : v < 0.01 ? 1 : 0), 'ov-tick', 'end'); });
    OV.yearAxis(ov, R, (m) => R.x + (m / T_END) * R.w);
    const med = CARD.footprint.numbers.median_share;
    Object.entries(med).forEach(([yr, v]) => {
      const a = Math.max(0, yearMin(+yr)), b = Math.min(T_END, yearMin(+yr + 1));
      OV.line(ov, R.x + (a / T_END) * R.w, y(v), R.x + (b / T_END) * R.w, y(v), 'ov-mark');
    });
    OV.text(ov, R.x + R.w, R.y - 14, lang === 'ko' ? `가장 큰 날 ${top}` : `biggest day ${top}`, 'ov-strong', 'end');
    return { unit: lang === 'ko' ? '점 하나 = 하루, BitMEX 전체 XBTUSD 거래량 중 그의 몫(로그). 가로선 = 연 중앙값' : "1 dot = 1 day, his share of all XBTUSD volume (log); bars = yearly median", overlay: OV.end(ov), tip: (i) => { const d = i - OFF.day; const v = A.days.share[d]; return v == null ? null : dayTip(d, pct(v, 2)); } };
  };

  SCENES.outro = (T_, S) => ({ ...SCENES.hero(T_, S), unit: t('heroUnit') });

  // ------------------------------------------------------------------ activation
  let activeId = null;
  function activate(id, instant) {
    if (!INS) return;
    const fn = SCENES[id];
    if (!fn) return;
    const fresh = id !== activeId;
    activeId = id; current = id;
    const full = id === 'hero';
    const S = full ? { x: 0, y: 0, w: view.w, h: view.h } : stage;
    document.body.classList.toggle('at-hero', full);
    const T_ = blank(S);
    const scene = fn(T_, full ? inset(S, { l: 0, r: 0, t: 60, b: 0 }) : S);
    target = T_;
    tipFn = scene.tip;
    // Plate label, unit, overlay.
    const n = ORDER.indexOf(id);
    $('.frame-plate').textContent = n >= 0 ? t('plate')(n + 1, ORDER.length) : '';
    $('.frame-unit').textContent = scene.unit || '';
    const ov = $('#overlay');
    ov.setAttribute('viewBox', `0 0 ${stage.w} ${stage.h}`);
    Object.assign(ov.style, { left: stage.x + 'px', top: stage.y + 'px', width: stage.w + 'px', height: stage.h + 'px' });
    if (full) {
      ov.setAttribute('viewBox', `0 0 ${view.w} ${view.h}`);
      Object.assign(ov.style, { left: '0px', top: '0px', width: view.w + 'px', height: view.h + 'px' });
    }
    const quick = instant || reduceMotion.matches || !fresh;
    clearTimeout(overlayTimer);
    ov.classList.remove('on');
    const showOverlay = () => {
      // Overlay coordinates are relative to the stage origin; the hero uses the whole viewport.
      const shift = full ? stage : { x: 0, y: 0 };
      ov.innerHTML = full ? `<g transform="translate(${shift.x},${shift.y})">${scene.overlay}</g>` : scene.overlay;
      ov.classList.add('on');
    };
    if (quick) showOverlay(); else overlayTimer = setTimeout(showOverlay, 650);
    $$('.plate').forEach((p) => p.classList.toggle('active', p.id === id));
    pickGrid = null;
    if (!gl) return;
    const first = !activate.started;
    activate.started = true;
    if (first && id === 'hero' && !reduceMotion.matches) {
      // The one orchestrated moment: the film develops as the beam crosses the page.
      const sweep = 2.4;
      const delays = new Float32Array(POOL);
      for (let i = 0; i < POOL; i++) delays[i] = (T_.x[i] / view.w) * sweep + hash(i, 11) * 0.08;
      beam(sweep, { x: 0, y: 0, w: view.w, h: view.h });
      gl.morph(T_, { duration: 0.9, delays, reveal: true });
      return;
    }
    if (quick) { gl.morph(T_, { duration: 0.001 }); return; }
    const sweep = 0.75;
    const delays = new Float32Array(POOL);
    const S0 = full ? { x: 0, y: 0, w: view.w, h: view.h } : stage;
    for (let i = 0; i < POOL; i++) delays[i] = clamp((T_.x[i] - S0.x) / S0.w, 0, 1) * sweep + hash(i, 12) * 0.12;
    beam(sweep, S0);
    gl.morph(T_, { duration: 1.05, delays });
  }

  // The scan line that crosses the plate while the dots move; their delays follow its position.
  function beam(sweep, R) {
    const b = $('.beam');
    if (reduceMotion.matches) return;
    b.style.transition = 'none';
    Object.assign(b.style, { top: R.y + 'px', height: R.h + 'px', opacity: '1', transform: `translateX(${R.x}px)` });
    void b.offsetWidth;
    b.style.transition = `transform ${sweep}s linear, opacity 0.35s ease ${sweep}s`;
    b.style.transform = `translateX(${R.x + R.w}px)`;
    b.style.opacity = '0';
  }

  // ------------------------------------------------------------------ DOM
  function verdictCounts() {
    const v = { holds: 0, nuance: 0, revised: 0 };
    INS.cards.forEach((c) => { if (c.review) v[c.review.verdict]++; });
    return v;
  }
  const ICON = {
    holds: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8.5l3 3 7-7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    nuance: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M8 7v4M8 4.6v.1" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
    revised: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 13l1-3.5L11 2.5l2.5 2.5L6.5 12 3 13z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>',
  };

  function build() {
    document.documentElement.lang = lang;
    $$('[data-t]').forEach((el) => { el.textContent = t(el.dataset.t); });
    $$('.lang button').forEach((b) => b.classList.toggle('on', b.dataset.lang === lang));
    $('#hero-title').textContent = t('heroTitle');
    $('#hero-sub').textContent = t('heroSub')(INS.meta);
    const v = verdictCounts();
    $('#hero-verdicts').innerHTML = `<span class="vsum">${esc(t('heroCheck'))}</span>` +
      ['holds', 'nuance', 'revised'].map((k) => `<span class="vchip ${k}">${ICON[k]}${esc(t('heroCount')(k, v[k]))}</span>`).join('');
    const plates = [];
    let n = 0;
    A.chapters.forEach((ch) => {
      ch.cards.forEach((id, k) => {
        const c = CARD[id];
        if (!c) return;
        n++;
        const head = k === 0 ? `<div class="chapter"><h2>${esc(L(ch.title))}</h2><p>${esc(L(ch.question))}</p></div>` : '';
        const r = c.review;
        const review = r ? `<div class="review ${r.verdict}"><p class="vchip ${r.verdict}">${ICON[r.verdict]}${esc(T[lang].verdict[r.verdict])}</p><p>${esc(L(r.note))}</p></div>` : '';
        const tag = c.new ? `<span class="new">${esc(t('isNew'))}</span>` : '';
        plates.push(`<section class="plate" id="${c.id}" data-chapter="${ch.key}">${head}
          <div class="plate-body">
            <p class="plate-no">${esc(t('plate')(n, ORDER.length))}${tag}</p>
            <h3>${esc(L(c.title))}</h3>
            <p class="stat"><b>${esc(c.stat.value)}</b><span>${esc(L(c.stat.label))}</span></p>
            <p class="text">${esc(L(c.body))}</p>
            ${review}
            <div class="fallback">${window.XCharts ? window.XCharts.render(c.chart, lang) : ''}</div>
            <nav class="step"><button type="button" data-step="-1">${esc(t('prev'))}</button><button type="button" data-step="1">${esc(t('next'))}</button></nav>
          </div>
        </section>`);
      });
    });
    $('#plates').innerHTML = plates.join('');
    $$('.step button').forEach((b) => b.addEventListener('click', () => step(+b.dataset.step, b.closest('.plate').id)));
    // Summary and index.
    $('#summary-title').textContent = t('summaryTitle');
    $('#summary-lead').textContent = t('summaryLead');
    const rows = A.chapters.map((ch) => `<div class="sum-ch"><h3>${esc(L(ch.title))}</h3><ul>` + ch.cards.filter((id) => CARD[id]).map((id) => {
      const c = CARD[id];
      const tag = c.review ? `<span class="vchip ${c.review.verdict}">${ICON[c.review.verdict]}${esc(T[lang].verdict[c.review.verdict].split(': ')[1] || '')}</span>` : `<span class="new">${esc(t('isNew'))}</span>`;
      return `<li><a href="#${id}">${esc(L(c.title))}</a>${tag}</li>`;
    }).join('') + '</ul></div>').join('');
    $('#summary-grid').innerHTML = rows;
    $('#index-list').innerHTML = rows;
    $('#about-title').textContent = t('aboutTitle');
    $('#about').innerHTML = T[lang].about.map(([h, p]) => `<div><h3>${esc(h)}</h3><p>${esc(p)}</p></div>`).join('');
    $('#no-gl').textContent = t('noGL');
    $$('#index-list a, #summary-grid a').forEach((a) => a.addEventListener('click', (e) => {
      e.preventDefault();
      closeIndex();
      const id = a.getAttribute('href').slice(1);
      document.getElementById(id)?.scrollIntoView({ behavior: reduceMotion.matches ? 'instant' : 'smooth', block: 'start' });
    }));
    if (observer) $$('.plate').forEach((p) => observer.observe(p));
  }

  $$('.lang button').forEach((b) => b.addEventListener('click', () => {
    lang = b.dataset.lang;
    try { localStorage.setItem('nyotti-lang', lang); } catch (e) { /* ignore */ }
    const keep = current;
    build();
    if (keep) activate(keep, true);
  }));

  // ------------------------------------------------------------------ scroll
  let observer = null;
  function bindScroll() {
    observer = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        const id = e.target.id;
        if (id === activeId) return;
        activate(id, false);
        if (id !== 'hero' && id !== 'outro') history.replaceState(null, '', '#' + id);
        else history.replaceState(null, '', location.pathname + location.search);
      });
    }, { rootMargin: '-48% 0px -48% 0px' });
    ['hero', 'outro'].forEach((id) => observer.observe(document.getElementById(id)));
    $$('.plate').forEach((p) => observer.observe(p));
  }

  function step(dir, from) {
    const i = ORDER.indexOf(from || activeId);
    const next = ORDER[clamp((i < 0 ? -1 : i) + dir, 0, ORDER.length - 1)];
    document.getElementById(next)?.scrollIntoView({ behavior: reduceMotion.matches ? 'instant' : 'smooth', block: 'start' });
  }

  function bindKeys() {
    document.addEventListener('keydown', (e) => {
      if (e.target.closest('input, textarea') || e.metaKey || e.ctrlKey || e.altKey) return;
      if ($('#index').open) { if (e.key === 'Escape') closeIndex(); return; }
      if (e.key === 'ArrowRight') { e.preventDefault(); step(1); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); step(-1); }
    });
    $('#open-index').addEventListener('click', () => { $('#index').showModal(); });
    $('#close-index').addEventListener('click', closeIndex);
    $('#index').addEventListener('click', (e) => { if (e.target.id === 'index') closeIndex(); });
  }
  function closeIndex() { if ($('#index').open) $('#index').close(); }

  // ------------------------------------------------------------------ pointer
  function buildPick() {
    pickGrid = new Map();
    if (!target) return;
    for (let i = 0; i < POOL; i++) {
      if (!target.used[i] || target.rgba[i * 4 + 3] < 0.12) continue;
      const key = `${Math.floor(target.x[i] / 10)},${Math.floor(target.y[i] / 10)}`;
      let cell = pickGrid.get(key);
      if (!cell) pickGrid.set(key, (cell = []));
      cell.push(i);
    }
  }
  function pick(px, py) {
    if (!pickGrid) buildPick();
    let best = null, bd = 144;
    const gx = Math.floor(px / 10), gy = Math.floor(py / 10);
    for (let x = gx - 1; x <= gx + 1; x++) {
      for (let y = gy - 1; y <= gy + 1; y++) {
        for (const i of pickGrid.get(`${x},${y}`) || []) {
          const d = (target.x[i] - px) ** 2 + (target.y[i] - py) ** 2;
          if (d < bd) { bd = d; best = i; }
        }
      }
    }
    return best;
  }
  function bindPointer() {
    const tip = $('#tip');
    let raf = 0, last = null;
    const show = (e) => {
      raf = 0;
      if (!tipFn || (gl && gl.busy())) { tip.hidden = true; return; }
      const full = current === 'hero';
      const inStage = full || (e.clientX >= stage.x && e.clientX <= stage.x + stage.w && e.clientY >= stage.y && e.clientY <= stage.y + stage.h);
      const overText = e.target.closest && e.target.closest('.plate-body, .hero-copy, .top, dialog, .summary, .about');
      if (!inStage || overText) { tip.hidden = true; return; }
      const i = pick(e.clientX, e.clientY);
      const html = i == null ? null : tipFn(i);
      if (!html) { tip.hidden = true; return; }
      tip.innerHTML = html;
      tip.hidden = false;
      const w = tip.offsetWidth, h = tip.offsetHeight;
      tip.style.left = Math.min(view.w - w - 10, e.clientX + 14) + 'px';
      tip.style.top = Math.min(view.h - h - 10, e.clientY + 14) + 'px';
    };
    window.addEventListener('pointermove', (e) => { last = e; if (!raf) raf = requestAnimationFrame(() => show(last)); }, { passive: true });
    window.addEventListener('scroll', () => { tip.hidden = true; }, { passive: true });
    $('.backdrop').addEventListener('click', (e) => show(e));
  }
})();
