(function () {
  'use strict';
  const { PALETTE: P, diverging, ramp, rgba } = window.XColor;
  const ACCENT = '#e752a7';
  const $ = (s) => document.querySelector(s);
  const DPR = Math.min(2, window.devicePixelRatio || 1);
  const params = new URLSearchParams(location.search);

  // ------------------------------------------------------------------ text
  const T = {
    en: {
      notAdvice: 'Unofficial · Past records only · Not investment advice', atlas: 'Atlas', atlasMore: ': 30 readings',
      headline: (m) => `${m.fills.toLocaleString('en-US')} fills. Four years. <em>Replayed, verified, x-rayed.</em>`,
      sub: 'In September 2026 the Korean trader known as Wonyotti (BitMEX account aoa) published his full 2018-2021 execution history. This page replays it, checks every fill against BitMEX\'s own public tape, and has Jev read each of his 10,169 Bitcoin decisions. It describes what happened. It does not say what anyone should do.',
      realised: 'realised PnL', withdrawn: 'withdrawn', fillsReplayed: 'fills replayed',
      lensTitle: 'Jev lenses',
      lensLead: 'Every dot is one decision: XBTUSD fills on the same side with no gap over 20 minutes. Code turns the market and his account at that moment into a short English description, and Jev answers eight typed questions about it with calibrated probabilities. Gray means Jev was unsure. Nothing after the decision is ever shown to Jev.',
      all: 'All', buys: 'Buys', sells: 'Sells',
      inspectEmpty: 'Hover or tap a dot to see the decision, what Jev was shown, and how it answered.',
      findings: 'Findings', aboutTitle: 'What this is, and is not',
      legendPrice: 'Bitcoin price (log)', legendBuy: 'his buys', legendSell: 'his sells', legendExposure: 'account Bitcoin exposure',
      panelFlow: 'his daily volume · buys ↑ sells ↓ · √ scale', panelExp: 'Bitcoin exposure, weekly median and 10-90% range · 1 = like holding BTC · 0 = dollars',
      yes: 'yes', no: 'no', unsure: 'unsure', jevSaw: 'What Jev was shown', answers: 'Jev\'s answers',
      buy: 'Bought', sell: 'Sold', kinds: { open: 'opened', add: 'added', reduce: 'reduced', flip: 'flipped', close: 'closed' },
      exposure: 'exposure', checkOf: (k, a, n) => `${k}: Jev agrees with code on ${a} of ${n} decisions`,
      cost: (j) => `${j.requests.toLocaleString('en-US')} Jev requests · ${(j.input_tokens / 1e6).toFixed(1)}M input tokens · $${j.cost_usd.toFixed(2)} · p50 ${j.p50_ms} ms · ${j.model}`,
      low: 'low', high: 'high',
    },
    ko: {
      notAdvice: '비공식 · 과거 기록만 · 투자 조언 아님', atlas: '아틀라스', atlasMore: ': 판독 30개',
      headline: (m) => `체결 ${m.fills.toLocaleString('ko-KR')}건. 4년. <em>재생하고, 검증하고, 투시한다.</em>`,
      sub: '2026년 9월, 워뇨띠(BitMEX 계정 aoa)가 2018~2021년 체결 내역 전체를 공개했다. 이 페이지는 그 기록을 재생하고, 모든 체결을 BitMEX가 직접 공개한 체결 테이프와 대조하고, 비트코인 매매 결정 10,169개를 Jev가 하나씩 읽게 한다. 일어난 일을 설명할 뿐, 누구에게도 무엇을 하라고 말하지 않는다.',
      realised: '실현손익', withdrawn: '출금', fillsReplayed: '재생된 체결',
      lensTitle: 'Jev 렌즈',
      lensLead: '점 하나가 결정 하나다. 같은 방향의 XBTUSD 체결이 20분 안에 이어지면 한 결정으로 묶었다. 코드가 그 순간의 시장과 계좌 상태를 짧은 영어 묘사로 바꾸고, Jev가 여덟 가지 질문에 보정된 확률로 답한다. 회색은 Jev가 확신하지 못한 답이다. 결정 이후의 정보는 Jev에게 보여주지 않는다.',
      all: '전체', buys: '매수', sells: '매도',
      inspectEmpty: '점에 마우스를 올리거나 탭하면 그 결정, Jev가 본 묘사, Jev의 답이 나온다.',
      findings: '발견한 것', aboutTitle: '이 프로젝트가 하는 것과 하지 않는 것',
      legendPrice: '비트코인 가격(로그)', legendBuy: '그의 매수', legendSell: '그의 매도', legendExposure: '계좌의 BTC 노출도',
      panelFlow: '일별 거래량 · 매수 ↑ 매도 ↓ · 제곱근 축', panelExp: 'BTC 노출도, 주간 중앙값과 10~90% 범위 · 1 = BTC 보유와 같음 · 0 = 달러',
      yes: '예', no: '아니오', unsure: '애매함', jevSaw: 'Jev가 본 묘사', answers: 'Jev의 답',
      buy: '매수', sell: '매도', kinds: { open: '신규 진입', add: '추가', reduce: '축소', flip: '반대 전환', close: '전량 청산' },
      exposure: '노출도', checkOf: (k, a, n) => `${k}: 결정 ${n}개 중 ${a} 코드와 일치`,
      cost: (j) => `Jev 요청 ${j.requests.toLocaleString('ko-KR')}건 · 입력 ${(j.input_tokens / 1e6).toFixed(1)}M 토큰 · $${j.cost_usd.toFixed(2)} · 중앙 지연 ${j.p50_ms}ms · ${j.model}`,
      low: '낮음', high: '높음',
    },
  };
  let lang = 'en';
  try {
    const saved = localStorage.getItem('nyotti-lang');
    lang = saved || ((navigator.language || '').startsWith('ko') ? 'ko' : 'en');
  } catch (e) { /* storage blocked: keep the default */ }
  if (params.get('lang')) lang = params.get('lang') === 'ko' ? 'ko' : 'en';
  const t = (k) => T[lang][k];

  // ------------------------------------------------------------------ data
  let INS, R, D;
  Promise.all(['data/insights.json', 'data/replay.json', 'data/decisions.json'].map((u) => fetch(u).then((r) => r.json())))
    .then(([ins, rep, dec]) => {
      INS = ins; R = rep; D = dec;
      prepReplay();
      prepLens();
      applyLang();
      window.addEventListener('resize', () => { sizeReplay(); sizeLens(); drawLens(); }, { passive: true });
      if (params.get('at') != null) {
        head = Math.max(0, Math.min(1, +params.get('at'))) * (R.n - 1);
        $('#scrub').value = Math.round((head / (R.n - 1)) * 1000);
        drawFrame(true);
      } else if (params.get('autoplay') !== '0') setTimeout(play, 600);
      window.__ready = true;
    });

  function applyLang() {
    document.documentElement.lang = lang;
    document.querySelectorAll('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
    $('#headline').innerHTML = t('headline')(INS.meta);
    document.querySelectorAll('.lang button').forEach((b) => b.classList.toggle('on', b.dataset.lang === lang));
    renderLegend();
    renderTabs();
    renderLensLegend();
    renderChecks();
    renderCards();
    renderAbout();
    if (pinned != null) inspect(pinned);
    drawFrame(true);
  }
  document.querySelectorAll('.lang button').forEach((b) => b.addEventListener('click', () => {
    lang = b.dataset.lang;
    try { localStorage.setItem('nyotti-lang', lang); } catch (e) { /* ignore */ }
    applyLang();
  }));

  // ------------------------------------------------------------------ replay
  const cv = $('#replay');
  const ctx = cv.getContext('2d');
  let W = 0, H = 0, L = {}, head = 0, playing = false, speed = 1, lastTs = 0, particles = [];
  let cumFills, flowBins, priceMin, priceMax, events = [];
  const DURATION = 30; // seconds for the whole history at 1x

  function prepReplay() {
    cumFills = new Float64Array(R.n);
    let s = 0;
    for (let i = 0; i < R.n; i++) { s += R.fills[i]; cumFills[i] = s; }
    const ps = R.price.filter((v) => v != null);
    priceMin = Math.min(...ps); priceMax = Math.max(...ps);
    events = (R.events || []).map((e) => ({ ...e, shown: false }));
    sizeReplay();
    $('#scrub').addEventListener('input', (e) => { head = (e.target.value / 1000) * (R.n - 1); particles = []; events.forEach((v) => { v.shown = v.i < head; }); drawFrame(true); });
    $('#play').addEventListener('click', () => (playing ? pause() : play()));
    document.querySelectorAll('.speed button').forEach((b) => b.addEventListener('click', () => {
      speed = +b.dataset.speed;
      document.querySelectorAll('.speed button').forEach((x) => x.classList.toggle('on', x === b));
    }));
    cv.addEventListener('mousemove', hoverReplay);
    cv.addEventListener('mouseleave', () => { $('#replay-tip').hidden = true; drawFrame(true); });
  }

  function sizeReplay() {
    const r = cv.getBoundingClientRect();
    W = r.width; H = r.height;
    cv.width = Math.round(W * DPR); cv.height = Math.round(H * DPR);
    const padL = 12, padR = 64, top = 16;
    const usable = H - top - 30;
    L = {
      x0: padL, x1: W - padR,
      price: [top, top + usable * 0.6],
      flow: [top + usable * 0.64, top + usable * 0.82],
      exp: [top + usable * 0.86, top + usable],
    };
    // Bin hours into pixel columns once per size.
    const cols = Math.max(50, Math.floor((L.x1 - L.x0) / 2));
    flowBins = { cols, buy: new Float64Array(cols), sell: new Float64Array(cols), start: new Int32Array(cols) };
    for (let i = 0; i < R.n; i++) {
      const c = Math.min(cols - 1, Math.floor((i / R.n) * cols));
      flowBins.buy[c] += R.buy[i] || 0; flowBins.sell[c] += R.sell[i] || 0;
    }
    for (let c = 0; c < cols; c++) flowBins.start[c] = Math.floor((c / cols) * R.n);
    flowBins.max = Math.sqrt(Math.max(...flowBins.buy, ...flowBins.sell));
    // Exposure per week: the 10-90% range as a faint band, the median as the line.
    const weeks = Math.ceil(R.n / 168);
    flowBins.weeks = weeks;
    flowBins.eLo = new Float64Array(weeks).fill(NaN); flowBins.eHi = new Float64Array(weeks).fill(NaN); flowBins.eMed = new Float64Array(weeks).fill(NaN);
    for (let c = 0; c < weeks; c++) {
      const a = c * 168, b = Math.min(R.n, a + 168);
      const vals = [];
      for (let i = a; i < b; i++) if (R.exposure[i] != null) vals.push(R.exposure[i]);
      if (!vals.length) continue;
      vals.sort((x, y) => x - y);
      flowBins.eLo[c] = vals[Math.floor(vals.length * 0.1)];
      flowBins.eHi[c] = vals[Math.floor(vals.length * 0.9)];
      flowBins.eMed[c] = vals[Math.floor(vals.length / 2)];
    }
    drawFrame(true);
  }

  const xAt = (i) => L.x0 + (i / (R.n - 1)) * (L.x1 - L.x0);
  const yPrice = (p) => {
    const a = Math.log(priceMin * 0.92), b = Math.log(priceMax * 1.05);
    return L.price[1] - ((Math.log(p) - a) / (b - a)) * (L.price[1] - L.price[0]);
  };
  const yExp = (e) => {
    const lo = -1.5, hi = 3;
    const v = Math.max(lo, Math.min(hi, e));
    return L.exp[1] - ((v - lo) / (hi - lo)) * (L.exp[1] - L.exp[0]);
  };
  const dateAt = (i) => new Date(Date.parse(R.t0 + 'Z') + i * 3600e3);
  const ymd = (d) => d.toISOString().slice(0, 10);

  function play() {
    if (head >= R.n - 1) { head = 0; particles = []; events.forEach((e) => { e.shown = false; }); }
    playing = true; lastTs = 0;
    $('#play').classList.add('playing');
    requestAnimationFrame(tick);
  }
  function pause() { playing = false; $('#play').classList.remove('playing'); }

  function tick(ts) {
    if (!playing) return;
    const dt = lastTs ? Math.min(0.05, (ts - lastTs) / 1000) : 0;
    lastTs = ts;
    if (!advance(dt)) { pause(); return; }
    requestAnimationFrame(tick);
  }

  // One step of the replay. Driven by requestAnimationFrame, or frame by frame by the capture script.
  function advance(dt) {
    const prev = head;
    head = Math.min(R.n - 1, head + (dt * speed * R.n) / DURATION);
    spawn(prev, head);
    events.forEach((e) => { if (!e.shown && e.i <= head) { e.shown = true; showEvent(e); } });
    particles = particles.filter((p) => (p.age += dt) < p.life);
    if (current) {
      current.age += dt;
      const el = $('#event');
      el.style.opacity = current.age < 2.4 / speed ? 1 : Math.max(0, 1 - (current.age - 2.4 / speed) / 0.4);
    }
    drawFrame(false);
    $('#scrub').value = Math.round((head / (R.n - 1)) * 1000);
    return !(head >= R.n - 1 && !particles.length);
  }

  window.__nyotti = {
    seek(f) { head = f * (R.n - 1); particles = []; events.forEach((e) => { e.shown = e.i < head; }); current = null; $('#event').style.opacity = 0; drawFrame(true); },
    step(dt) { pause(); advance(dt); return head / (R.n - 1); },
    lens(k) { document.querySelector(`#tabs button[data-key="${k}"]`)?.click(); },
    pick(i) { pinned = i; drawLens(); inspect(i); },
    find(key, min) { const v = D[key]; let best = null; for (let i = 0; i < v.length; i++) if (v[i] != null && v[i] >= min && (best == null || D.usd[i] > D.usd[best])) best = i; return best; },
  };

  function spawn(a, b) {
    let buy = 0, sell = 0;
    for (let i = Math.floor(a) + 1; i <= Math.floor(b); i++) { buy += R.buy[i] || 0; sell += R.sell[i] || 0; }
    const i = Math.floor(b);
    const px = R.price[i];
    if (px == null) return;
    const x = xAt(b), y = yPrice(px);
    const emit = (usd, side) => {
      if (usd <= 0) return;
      const n = Math.min(14, 1 + Math.round(Math.log10(1 + usd * 4) * 4));
      for (let k = 0; k < n; k++) {
        const r = 1.2 + Math.random() * 1.8 + Math.min(4, Math.sqrt(usd) * 0.25);
        const dist = 30 + Math.random() * 70;
        particles.push({ x: x + (Math.random() - 0.5) * 10, y, from: side === 'buy' ? y + dist : y - dist, r, side, age: 0, life: 0.9 + Math.random() * 0.5 });
      }
    };
    emit(buy, 'buy'); emit(sell, 'sell');
  }

  let current = null;
  function showEvent(e) {
    current = { e, age: 0 };
    const el = $('#event');
    el.innerHTML = `<b>${ymd(dateAt(e.i))}</b>${e.text[lang]}`;
    el.hidden = false; el.style.opacity = 1;
    const x = xAt(e.i), y = yPrice(R.price[e.i] || priceMin);
    const left = Math.min(W - 320, Math.max(10, x - 150));
    el.style.left = left + 'px';
    el.style.top = (y > H * 0.35 ? Math.max(70, y - 110) : y + 26) + 'px';
  }

  function drawFrame() {
    if (!R) return;
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const hi = Math.floor(head);
    // gridlines + price axis labels
    ctx.font = '10.5px JetBrains Mono, monospace';
    ctx.fillStyle = '#7d7d8c'; ctx.strokeStyle = '#1a1a21'; ctx.lineWidth = 1;
    [3000, 5000, 10000, 20000, 40000, 60000].forEach((p) => {
      if (p < priceMin * 0.92 || p > priceMax * 1.05) return;
      const y = Math.round(yPrice(p)) + 0.5;
      ctx.beginPath(); ctx.moveTo(L.x0, y); ctx.lineTo(L.x1, y); ctx.stroke();
      ctx.fillText(`$${p >= 1000 ? p / 1000 + 'k' : p}`, L.x1 + 8, y + 4);
    });
    // year ticks
    for (let yr = 2019; yr <= 2021; yr++) {
      const i = (Date.parse(`${yr}-01-01T00:00:00Z`) - Date.parse(R.t0 + 'Z')) / 3600e3;
      const x = Math.round(xAt(i)) + 0.5;
      ctx.strokeStyle = '#1a1a21'; ctx.beginPath(); ctx.moveTo(x, L.price[0]); ctx.lineTo(x, L.exp[1]); ctx.stroke();
      ctx.fillStyle = '#7d7d8c'; ctx.fillText(String(yr), x + 4, H - 10);
    }
    // panel labels
    ctx.fillStyle = '#7d7d8c';
    ctx.fillText(t('panelFlow'), L.x0 + 2, L.flow[0] - 4);
    ctx.fillText(t('panelExp'), L.x0 + 2, L.exp[0] - 4);

    // price: full history faint, played part bright
    pricePath(0, R.n - 1); ctx.strokeStyle = '#26262f'; ctx.lineWidth = 1.5; ctx.stroke();
    pricePath(0, hi); ctx.strokeStyle = '#d6d6de'; ctx.lineWidth = 1.6; ctx.stroke();

    // flow bars (mirrored)
    const mid = (L.flow[0] + L.flow[1]) / 2, half = (L.flow[1] - L.flow[0]) / 2;
    const bw = (L.x1 - L.x0) / flowBins.cols;
    for (let c = 0; c < flowBins.cols; c++) {
      if (flowBins.start[c] > hi) break;
      const x = L.x0 + c * bw;
      const hb = (Math.sqrt(flowBins.buy[c]) / flowBins.max) * half;
      const hs = (Math.sqrt(flowBins.sell[c]) / flowBins.max) * half;
      ctx.fillStyle = P.buy; ctx.fillRect(x, mid - hb, Math.max(1, bw - 0.6), hb);
      ctx.fillStyle = P.sell; ctx.fillRect(x, mid, Math.max(1, bw - 0.6), hs);
    }
    ctx.strokeStyle = '#2d2d38'; ctx.beginPath(); ctx.moveTo(L.x0, mid + 0.5); ctx.lineTo(L.x1, mid + 0.5); ctx.stroke();

    // exposure with reference lines at 1 and 0
    [[1, '1'], [0, '0']].forEach(([v, lab]) => {
      const y = Math.round(yExp(v)) + 0.5;
      ctx.strokeStyle = '#22222b'; ctx.beginPath(); ctx.moveTo(L.x0, y); ctx.lineTo(L.x1, y); ctx.stroke();
      ctx.fillStyle = '#7d7d8c'; ctx.fillText(lab + 'x', L.x1 + 8, y + 4);
    });
    ctx.fillStyle = 'rgba(231,82,167,0.16)';
    const ww = (168 / R.n) * (L.x1 - L.x0);
    for (let c = 0; c < flowBins.weeks && c * 168 <= hi; c++) {
      if (Number.isNaN(flowBins.eLo[c])) continue;
      const y0 = yExp(flowBins.eHi[c]), y1 = yExp(flowBins.eLo[c]);
      ctx.fillRect(xAt(c * 168), y0, Math.max(1, ww - 0.5), Math.max(1, y1 - y0));
    }
    ctx.beginPath();
    let started = false;
    for (let c = 0; c < flowBins.weeks && c * 168 <= hi; c++) {
      const e = flowBins.eMed[c];
      if (Number.isNaN(e)) { started = false; continue; }
      const x = xAt(c * 168) + ww / 2, y = yExp(e);
      if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = ACCENT; ctx.lineWidth = 1.4; ctx.stroke();

    // particles
    particles.forEach((p) => {
      const k = Math.min(1, p.age / (p.life * 0.55));
      const ease = 1 - (1 - k) ** 3;
      const y = p.from + (p.y - p.from) * ease;
      const a = p.age < p.life * 0.55 ? 0.95 : 0.95 * (1 - (p.age - p.life * 0.55) / (p.life * 0.45));
      ctx.fillStyle = rgba(p.side === 'buy' ? P.buy : P.sell, Math.max(0, a));
      ctx.beginPath(); ctx.arc(p.x, y, p.r, 0, Math.PI * 2); ctx.fill();
    });

    // playhead
    const px = R.price[hi];
    if (px != null && hi > 0) {
      const x = xAt(head), y = yPrice(px);
      const g = ctx.createRadialGradient(x, y, 0, x, y, 26);
      g.addColorStop(0, 'rgba(231,82,167,0.55)'); g.addColorStop(1, 'rgba(231,82,167,0)');
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, 26, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = 'rgba(231,82,167,0.25)'; ctx.beginPath(); ctx.moveTo(Math.round(x) + 0.5, L.price[0]); ctx.lineTo(Math.round(x) + 0.5, L.exp[1]); ctx.stroke();
    }
    // counters
    $('#c-date').textContent = ymd(dateAt(hi));
    $('#c-pnl').textContent = (R.realised[hi] || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    $('#c-out').textContent = (R.withdrawn[hi] || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    $('#c-fills').textContent = Math.round(cumFills[hi]).toLocaleString('en-US');
  }

  function pricePath(a, b) {
    ctx.beginPath();
    const step = Math.max(1, Math.floor(R.n / ((L.x1 - L.x0) * 2)));
    let started = false;
    for (let i = a; i <= b; i += step) {
      const p = R.price[i];
      if (p == null) continue;
      const x = xAt(i), y = yPrice(p);
      if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
    }
  }

  function hoverReplay(ev) {
    const r = cv.getBoundingClientRect();
    const x = ev.clientX - r.left;
    if (x < L.x0 || x > L.x1) { $('#replay-tip').hidden = true; return; }
    const i = Math.round(((x - L.x0) / (L.x1 - L.x0)) * (R.n - 1));
    const day0 = i - (i % 24);
    let buy = 0, sell = 0;
    for (let k = day0; k < Math.min(R.n, day0 + 24); k++) { buy += R.buy[k] || 0; sell += R.sell[k] || 0; }
    const tip = $('#replay-tip');
    const e = R.exposure[i];
    tip.innerHTML = `<b>${ymd(dateAt(i))}</b><br>BTC $${(R.price[i] || 0).toLocaleString('en-US')}<br>` +
      `<span style="color:${P.buy}">●</span> ${t('legendBuy')} $${buy.toFixed(1)}M &nbsp;<span style="color:${P.sell}">●</span> ${t('legendSell')} $${sell.toFixed(1)}M<br>` +
      `${t('exposure')} ${e == null ? '–' : e.toFixed(2) + 'x'} · equity ${(R.equity[i] || 0).toFixed(1)} BTC<br>` +
      `${t('realised')} ${(R.realised[i] || 0).toFixed(2)} BTC`;
    tip.hidden = false;
    tip.style.left = Math.min(W - 260, x + 14) + 'px';
    tip.style.top = (ev.clientY - r.top + 14) + 'px';
  }

  function renderLegend() {
    $('#replay-legend').innerHTML =
      `<span class="line"><i style="background:#d6d6de"></i>${t('legendPrice')}</span>` +
      `<span><i style="background:${P.buy}"></i>${t('legendBuy')}</span>` +
      `<span><i style="background:${P.sell}"></i>${t('legendSell')}</span>` +
      `<span class="line"><i style="background:${ACCENT}"></i>${t('legendExposure')}</span>`;
  }

  // ------------------------------------------------------------------ lenses
  const lc = $('#lens');
  const lx = lc.getContext('2d');
  let LW = 0, LH = 0, lensKey = 'panic', sideFilter = 'all', hovered = null, pinned = null, grid = null, order = [];
  const LP = { l: 46, r: 14, t: 10, b: 24 };
  const stateCache = {};

  function prepLens() {
    if (params.get('lens')) lensKey = params.get('lens');
    sizeLens();
    lc.addEventListener('mousemove', (e) => { const i = pick(e); if (i !== hovered) { hovered = i; drawLens(); if (i != null) inspect(i); } });
    lc.addEventListener('mouseleave', () => { hovered = null; drawLens(); if (pinned != null) inspect(pinned); });
    lc.addEventListener('click', (e) => { const i = pick(e); pinned = i; drawLens(); if (i != null) inspect(i); });
    document.querySelectorAll('.filter button').forEach((b) => b.addEventListener('click', () => {
      sideFilter = b.dataset.side;
      document.querySelectorAll('.filter button').forEach((x) => x.classList.toggle('on', x === b));
      drawLens();
    }));
  }

  function sizeLens() {
    const r = lc.getBoundingClientRect();
    LW = r.width; LH = r.height;
    lc.width = Math.round(LW * DPR); lc.height = Math.round(LH * DPR);
  }

  const lens = () => D.lenses.find((l) => l.key === lensKey) || D.lenses[0];
  const tMax = () => D.t[D.t.length - 1];
  const lxAt = (m) => LP.l + (m / tMax()) * (LW - LP.l - LP.r);
  function lyAt(i) {
    const l = lens();
    if (l.type === 'choice') {
      const k = D[l.key][i];
      const rows = l.options.length;
      const band = (LH - LP.t - LP.b) / rows;
      const jitter = ((i * 2654435761) % 1000) / 1000 - 0.5;
      return LP.t + band * (k + 0.5) + jitter * band * 0.7;
    }
    const a = Math.log(priceMin * 0.92), b = Math.log(priceMax * 1.05);
    return LH - LP.b - ((Math.log(D.px[i]) - a) / (b - a)) * (LH - LP.t - LP.b);
  }
  function colorOf(i) {
    const l = lens();
    const v = D[l.key][i];
    if (v == null) return P.pending;
    if (l.type === 'noul') return diverging(v);
    if (l.type === 'score') return ramp(P.heat, v / (l.levels - 1));
    const conf = D[l.key + '_conf'][i] || 0;
    return rgba(ACCENT, 0.25 + 0.75 * conf);
  }
  const visible = (i) => sideFilter === 'all' || String(D.side[i]) === sideFilter;

  function drawLens() {
    if (!D) return;
    lx.setTransform(DPR, 0, 0, DPR, 0, 0);
    lx.clearRect(0, 0, LW, LH);
    lx.font = '10.5px JetBrains Mono, monospace';
    const l = lens();
    lx.strokeStyle = '#1a1a21'; lx.fillStyle = '#7d7d8c'; lx.lineWidth = 1;
    if (l.type === 'choice') {
      const band = (LH - LP.t - LP.b) / l.options.length;
      l.options.forEach((o, k) => {
        const y = LP.t + band * k;
        if (k) { lx.beginPath(); lx.moveTo(LP.l, Math.round(y) + 0.5); lx.lineTo(LW - LP.r, Math.round(y) + 0.5); lx.stroke(); }
        lx.fillText(o, 2, y + band / 2 + 4);
      });
    } else {
      [3000, 5000, 10000, 20000, 40000, 60000].forEach((p) => {
        if (p < priceMin * 0.92 || p > priceMax * 1.05) return;
        const a = Math.log(priceMin * 0.92), b = Math.log(priceMax * 1.05);
        const y = Math.round(LH - LP.b - ((Math.log(p) - a) / (b - a)) * (LH - LP.t - LP.b)) + 0.5;
        lx.beginPath(); lx.moveTo(LP.l, y); lx.lineTo(LW - LP.r, y); lx.stroke();
        lx.fillText(`$${p / 1000}k`, 4, y + 4);
      });
    }
    for (let yr = 2019; yr <= 2021; yr++) {
      const m = (Date.parse(`${yr}-01-01T00:00:00Z`) - Date.parse(R.t0 + 'Z')) / 60e3;
      const x = Math.round(lxAt(m)) + 0.5;
      lx.strokeStyle = '#1a1a21'; lx.beginPath(); lx.moveTo(x, LP.t); lx.lineTo(x, LH - LP.b); lx.stroke();
      lx.fillStyle = '#7d7d8c'; lx.fillText(String(yr), x + 4, LH - 8);
    }
    // Draw the least certain first so strong answers sit on top.
    order = D.t.map((_, i) => i).filter(visible);
    const v = D[l.key];
    if (l.type === 'noul') order.sort((a, b) => Math.abs((v[a] ?? 0.5) - 0.5) - Math.abs((v[b] ?? 0.5) - 0.5));
    else if (l.type === 'score') order.sort((a, b) => (v[a] ?? 0) - (v[b] ?? 0));
    grid = new Map();
    const r = LW < 600 ? 1.6 : 2.2;
    for (const i of order) {
      const x = lxAt(D.t[i]), y = lyAt(i);
      lx.fillStyle = colorOf(i);
      lx.beginPath(); lx.arc(x, y, r, 0, Math.PI * 2); lx.fill();
      const key = `${Math.floor(x / 8)},${Math.floor(y / 8)}`;
      if (!grid.has(key)) grid.set(key, []);
      grid.get(key).push(i);
    }
    [hovered, pinned].forEach((i, k) => {
      if (i == null || !visible(i)) return;
      const x = lxAt(D.t[i]), y = lyAt(i);
      lx.strokeStyle = k ? '#ffffff' : 'rgba(255,255,255,0.7)'; lx.lineWidth = 2;
      lx.beginPath(); lx.arc(x, y, 6, 0, Math.PI * 2); lx.stroke();
    });
  }

  function pick(e) {
    const r = lc.getBoundingClientRect();
    const x = e.clientX - r.left, y = e.clientY - r.top;
    let best = null, bd = 100;
    for (let gx = Math.floor(x / 8) - 1; gx <= Math.floor(x / 8) + 1; gx++) {
      for (let gy = Math.floor(y / 8) - 1; gy <= Math.floor(y / 8) + 1; gy++) {
        for (const i of grid.get(`${gx},${gy}`) || []) {
          const d = (lxAt(D.t[i]) - x) ** 2 + (lyAt(i) - y) ** 2;
          if (d < bd) { bd = d; best = i; }
        }
      }
    }
    return best;
  }

  function answerRow(l, i) {
    const v = D[l.key][i];
    const label = lang === 'ko' ? l.label_ko : l.label;
    if (v == null) return '';
    if (l.type === 'noul') {
      const word = v > 0.7 ? t('yes') : v < 0.3 ? t('no') : t('unsure');
      return `<span>${label}</span><span class="bar"><span style="width:${v * 100}%;background:${diverging(v)}"></span></span><span class="v">${(v * 100).toFixed(0)}% ${word}</span>`;
    }
    if (l.type === 'score') {
      return `<span>${label}</span><span class="bar"><span style="width:${(v / (l.levels - 1)) * 100}%;background:${ramp(P.heat, v / (l.levels - 1))}"></span></span><span class="v">${v.toFixed(1)}/${l.levels - 1}</span>`;
    }
    const conf = D[l.key + '_conf'][i] || 0;
    return `<span>${label}</span><span class="bar"><span style="width:${conf * 100}%;background:${ACCENT}"></span></span><span class="v">${l.options[v]}</span>`;
  }

  function inspect(i) {
    const id = D.id[i];
    const when = new Date(Date.parse(R.t0 + 'Z') + D.t[i] * 60e3);
    const kind = ['open', 'add', 'reduce', 'flip', 'close'][D.kind[i]];
    const side = D.side[i] ? t('buy') : t('sell');
    const exp = D.exp0[i] == null ? '' : ` · ${t('exposure')} ${D.exp0[i].toFixed(2)}x → ${D.exp1[i].toFixed(2)}x`;
    let html = `<h3>${when.toISOString().slice(0, 16).replace('T', ' ')} UTC</h3>` +
      `<div class="act"><span style="color:${D.side[i] ? P.buy : P.sell}">●</span> ${side} $${D.usd[i].toFixed(2)}M XBTUSD @ ${D.px[i].toLocaleString('en-US')} · ${T[lang].kinds[kind]}${exp}</div>` +
      `<div class="label">${t('answers')}</div><div class="ans">${D.lenses.map((l) => answerRow(l, i)).join('')}</div>` +
      `<div class="saw" id="saw"><dt>${t('jevSaw')}</dt><dd>…</dd></div>`;
    $('#inspect').innerHTML = html;
    const chunk = String(Math.floor(id / 500)).padStart(3, '0');
    const done = (states) => {
      const st = states[id];
      if (!st || inspect.current !== id) return;
      const rows = [];
      const walk = (o, pre) => Object.entries(o).forEach(([k, v]) => (typeof v === 'object' ? walk(v, k) : rows.push([pre ? `${pre}.${k}` : k, v])));
      walk(st, '');
      $('#saw').innerHTML = `<dt style="color:var(--ink-2)">${t('jevSaw')}</dt>` + rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('');
    };
    inspect.current = id;
    if (stateCache[chunk]) done(stateCache[chunk]);
    else fetch(`data/states/${chunk}.json`).then((r) => r.json()).then((s) => { stateCache[chunk] = s; done(s); }).catch(() => {});
  }

  function renderTabs() {
    $('#tabs').innerHTML = D.lenses.map((l) => `<button role="tab" data-key="${l.key}" class="${l.key === lensKey ? 'on' : ''}" title="${l.hint || ''}">${lang === 'ko' ? l.label_ko : l.label}</button>`).join('');
    document.querySelectorAll('#tabs button').forEach((b) => b.addEventListener('click', () => {
      lensKey = b.dataset.key;
      document.querySelectorAll('#tabs button').forEach((x) => x.classList.toggle('on', x === b));
      renderLensLegend(); drawLens();
    }));
    drawLens();
  }

  function renderLensLegend() {
    const l = lens();
    let html = '';
    if (l.type === 'noul') {
      html = `<span>${t('no')}<span class="ramp" style="background:linear-gradient(90deg,${P.no},${P.unsure},${P.yes})"></span>${t('yes')}</span><span style="color:var(--muted)">${lang === 'ko' ? '세로축: 결정 당시 가격(로그)' : 'y: price at the decision (log)'}</span>`;
    } else if (l.type === 'score') {
      html = `<span>${t('low')}<span class="ramp" style="background:linear-gradient(90deg,${P.heat.join(',')})"></span>${t('high')}</span><span style="color:var(--muted)">${lang === 'ko' ? '세로축: 결정 당시 가격(로그)' : 'y: price at the decision (log)'}</span>`;
    } else {
      html = `<span style="color:var(--muted)">${lang === 'ko' ? '행: Jev가 고른 답 · 진할수록 확신이 높음' : 'rows: the answer Jev chose · brighter = more confident'}</span>`;
    }
    html += `<span style="color:var(--muted)">${l.hint || ''}</span>`;
    $('#lens-legend').innerHTML = html;
  }

  function renderChecks() {
    const c = INS.cards.find((x) => x.id === 'jev-check');
    let html = '';
    if (c) {
      Object.entries(c.numbers.checks).forEach(([k, v]) => {
        const l = D.lenses.find((x) => x.key === k);
        html += `<span class="chip">${T[lang].checkOf(lang === 'ko' ? l.label_ko : l.label, (v.agree * 100).toFixed(1) + '%', v.n.toLocaleString())}</span>`;
      });
    }
    if (INS.meta.jev) html += `<span class="chip">${t('cost')(INS.meta.jev)}</span>`;
    $('#checks').innerHTML = html;
  }

  // ------------------------------------------------------------------ cards
  function renderCards() {
    const verdict = {
      en: { holds: 'Re-checked: holds', nuance: 'Re-checked: holds, with a nuance', revised: 'Re-checked: revised' },
      ko: { holds: '재검증: 유지', nuance: '재검증: 유지, 단서 추가', revised: '재검증: 수정' },
    }[lang];
    const isNew = lang === 'ko' ? '새 판독' : 'New reading';
    $('#cards').innerHTML = INS.cards.filter((c) => c.id !== 'jev-check').map((c) =>
      `<article class="card" id="card-${c.id}">${c.new ? `<span class="tag new">${isNew}</span>` : ''}<h3>${c.title[lang]}</h3>` +
      `<div class="stat"><b>${c.stat.value}</b><span>${c.stat.label[lang]}</span></div>` +
      `<p>${c.body[lang]}</p>${window.XCharts.render(c.chart, lang)}` +
      (c.review ? `<details class="review ${c.review.verdict}"><summary>${verdict[c.review.verdict]}</summary><p>${c.review.note[lang]}</p></details>` : '') +
      `<a class="to-atlas" href="atlas.html#${c.id}">${lang === 'ko' ? '아틀라스에서 보기' : 'Open in the atlas'}</a></article>`).join('');
  }

  function renderAbout() {
    const m = INS.meta;
    const blocks = {
      en: [
        ['What it is', `<p>An independent, unofficial analysis of a trade history its owner chose to publish (${m.fills.toLocaleString()} fills, ${m.first_fill.slice(0, 10)} to ${m.last_fill.slice(0, 10)}). Every number on this page is computed from that release and from BitMEX's public data by the code in the repository.</p>`],
        ['What it is not', '<ul><li>Not investment advice, a signal, a strategy or a forecast.</li><li>No live data, no "what would he do now", no bot, no copy-trading, no backtest of following him.</li><li>No market outlook from his letter is repeated here.</li><li>No attempt to identify anyone; wallet details he removed stay removed.</li><li>Not affiliated with him, BitMEX or TypeSafe. Free and MIT-licensed, as he asked that nothing built on the data be sold.</li></ul>'],
        ['In his own words', '<blockquote>"If a trading bot looked like it would really make money, I already have the data, so I would have built it and run it first. Please don\'t be fooled, and don\'t buy one."<br><small>From the letter included in the release (translated)</small></blockquote>'],
        ['How it was checked', `<p>The release was downloaded from the original link and its SHA-256 pinned. A fill-level book rebuilt from the executions reproduces the wallet's realised PnL to within 0.03%. Fills were looked up by trade id on BitMEX's public tape. Jev only ever sees a description of the market and the account up to the moment of each decision; two of its eight questions have code-checkable answers and are scored above.</p>`],
      ],
      ko: [
        ['무엇인가', `<p>기록의 주인이 스스로 공개한 거래 내역(체결 ${m.fills.toLocaleString()}건, ${m.first_fill.slice(0, 10)} ~ ${m.last_fill.slice(0, 10)})에 대한 독립적인 비공식 분석이다. 이 페이지의 모든 숫자는 공개 자료와 BitMEX 공개 데이터로부터 레포의 코드가 계산했다.</p>`],
        ['무엇이 아닌가', '<ul><li>투자 조언, 신호, 전략, 예측이 아니다.</li><li>실시간 데이터, "지금 그라면?", 봇, 카피트레이딩, 그를 따라 했을 때의 백테스트가 없다.</li><li>서한에 담긴 시장 전망은 옮기지 않는다.</li><li>누구의 신원도 추정하지 않는다. 그가 지운 지갑 정보는 지운 채로 둔다.</li><li>그, BitMEX, TypeSafe와 무관하다. 이 데이터로 만든 것을 팔지 말아 달라는 요청에 따라 무료, MIT 라이선스다.</li></ul>'],
        ['그의 말', '<blockquote>"매매봇이 실제 수익이 날 것 같을 경우 이미 자료가 있는 제가 먼저 만들어서 돌리고 있었을 것입니다. 절대 속지 말고 구매도 하지 않으셨으면 좋겠습니다."<br><small>공개 자료에 포함된 서한 중</small></blockquote>'],
        ['어떻게 검증했나', '<p>원본 링크에서 내려받은 파일의 SHA-256을 고정했다. 체결로 재구성한 장부가 지갑의 실현손익을 0.03% 이내로 재현한다. 체결은 거래 ID로 BitMEX 공개 테이프에서 찾았다. Jev는 각 결정 시점까지의 시장과 계좌 묘사만 본다. 여덟 질문 중 두 개는 코드로 정답을 알 수 있어 위에 일치율을 적었다.</p>'],
      ],
    };
    $('#about').innerHTML = blocks[lang].map(([h, b]) => `<div><h3>${h}</h3>${b}</div>`).join('');
    $('#foot-meta').textContent = `aoa_public_2021-12-31_with_letter.zip · SHA-256 b6f1dc7a…d01b9a`;
  }
})();
