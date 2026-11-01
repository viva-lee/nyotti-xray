// Small SVG charts for the finding cards. Each returns markup; every mark carries a <title> for hover.
(function (root) {
  'use strict';
  const P = root.XColor.PALETTE;
  const ACCENT = '#e752a7';
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const fmt = (v, unit) => {
    const a = Math.abs(v);
    const n = Number.isInteger(v) || a >= 1000 ? v.toLocaleString('en-US', { maximumFractionDigits: 0 })
      : a >= 10 ? v.toFixed(1) : a >= 1 ? v.toFixed(2) : v.toFixed(3);
    return unit === '%' ? `${n}%` : unit === 'x' ? `${n}x` : unit && unit !== 'events' ? `${n} ${unit}` : n;
  };

  function bars(c, lang) {
    const labels = c.labels[lang];
    const vals = c.values;
    const W = 360, rowH = 22, H = labels.length * rowH + 6, L = 96, R = 70;
    const tr = (v) => (c.log ? Math.log10(1 + Math.abs(v)) : Math.abs(v));
    const neg = Math.max(0, ...vals.filter((v) => v < 0).map(tr));
    const pos = Math.max(0, ...vals.filter((v) => v >= 0).map(tr));
    const signed = c.signed && neg > 0;
    const span = W - L - R;
    // Signed charts split the width in proportion to the largest bar on each side of zero.
    const zero = signed ? L + span * (neg / (neg + pos || 1)) : L;
    const scale = signed ? span / (neg + pos || 1) : span / (pos || 1);
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img">`;
    labels.forEach((lab, i) => {
      const v = vals[i];
      const w = Math.max(v === 0 ? 0 : 2, tr(v) * scale);
      const x = v < 0 ? zero - w : zero;
      const y = i * rowH + 4;
      const color = signed && v < 0 ? P.no : ACCENT;
      s += `<text x="${L - 8}" y="${y + 12}" text-anchor="end">${esc(lab)}</text>`;
      s += `<rect x="${x}" y="${y + 3}" width="${w}" height="12" rx="3" fill="${color}"><title>${esc(lab)}: ${fmt(v, c.unit)}</title></rect>`;
      s += `<text class="v" x="${(v < 0 ? zero : x + w) + 6}" y="${y + 13}">${fmt(v, c.unit)}</text>`;
    });
    if (signed) s += `<line x1="${zero}" x2="${zero}" y1="0" y2="${H}" stroke="${P.unsure}" stroke-width="1"/>`;
    return s + '</svg>';
  }

  // Two series per year, side by side (grouped bars), with a legend. Values are shares unless `unit` says otherwise.
  function pairLabel(v, unit) {
    if (!unit || unit === '%') return `${(v * 100).toFixed(0)}%`;
    if (unit === 'h') return v < 1 ? `${Math.round(v * 60)}m` : `${v.toFixed(1)}h`;
    return fmt(v, unit);
  }
  function pair(c, lang) {
    const names = c.labels[lang];
    const colors = [P.no, ACCENT];
    const W = 360, H = 150, B = 120, L = 8;
    const n = c.years.length;
    const gw = (W - L * 2) / n;
    const tr = (v) => (c.log ? Math.log10(1 + v * 60) : v);
    const max = Math.max(...c.values.flat().map(tr)) || 1;
    let s = `<svg viewBox="0 0 ${W} ${H + 22}" role="img">`;
    c.years.forEach((y, i) => {
      [0, 1].forEach((k) => {
        const v = c.values[k][i];
        const h = (tr(v) / max) * (B - 18);
        const x = L + i * gw + gw * 0.18 + k * (gw * 0.32 + 2);
        const lab = pairLabel(v, c.unit);
        s += `<rect x="${x}" y="${B - h}" width="${gw * 0.32}" height="${h}" rx="3" fill="${colors[k]}"><title>${esc(names[k])} ${y}: ${lab}</title></rect>`;
        s += `<text class="v" x="${x + gw * 0.16}" y="${B - h - 4}" text-anchor="middle">${lab}</text>`;
      });
      s += `<text x="${L + i * gw + gw / 2}" y="${B + 14}" text-anchor="middle">${y}</text>`;
    });
    s += `<line x1="${L}" x2="${W - L}" y1="${B}" y2="${B}" stroke="${P.unsure}"/>`;
    names.forEach((nm, k) => {
      const x = L + k * 170;
      s += `<rect x="${x}" y="${H + 8}" width="10" height="10" rx="2" fill="${colors[k]}"/><text x="${x + 16}" y="${H + 17}">${esc(nm)}</text>`;
    });
    return s + '</svg>';
  }

  function heat(c, lang) {
    const rows = c.rows[lang];
    const W = 360, L = 26, T = 4, cw = (W - L) / 24, ch = 14;
    const max = Math.max(...c.values.flat()) || 1;
    let s = `<svg viewBox="0 0 ${W} ${T + rows.length * (ch + 2) + 16}" role="img">`;
    rows.forEach((r, i) => {
      s += `<text x="0" y="${T + i * (ch + 2) + 11}">${esc(r)}</text>`;
      c.values[i].forEach((v, h) => {
        const col = root.XColor.ramp(P.glow, v / max);
        s += `<rect x="${L + h * cw}" y="${T + i * (ch + 2)}" width="${cw - 2}" height="${ch}" rx="2" fill="${col}"><title>${esc(r)} ${c.cols[h]}:00 KST: ${v}</title></rect>`;
      });
    });
    [0, 6, 12, 18, 23].forEach((h) => {
      s += `<text x="${L + h * cw + cw / 2}" y="${T + rows.length * (ch + 2) + 12}" text-anchor="middle">${c.cols[h]}</text>`;
    });
    return s + '</svg>';
  }

  function curve(c, lang) {
    const W = 360, H = 150, L = 34, B = 128, R = 10;
    const v = c.values;
    const x = (i) => L + (i / (v.length - 1)) * (W - L - R);
    const y = (p) => B - Math.min(1.05, p) * (B - 10);
    let path = v.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p).toFixed(1)}`).join('');
    const hit = v.findIndex((p) => p >= c.mark);
    let s = `<svg viewBox="0 0 ${W} ${H + 6}" role="img">`;
    [0, 0.5, 1].forEach((g) => {
      s += `<line x1="${L}" x2="${W - R}" y1="${y(g)}" y2="${y(g)}" stroke="${P.pending}"/><text x="${L - 6}" y="${y(g) + 4}" text-anchor="end">${g * 100}%</text>`;
    });
    s += `<path d="${path}" fill="none" stroke="${ACCENT}" stroke-width="2"/>`;
    if (hit >= 0) {
      s += `<circle cx="${x(hit)}" cy="${y(v[hit])}" r="4" fill="${ACCENT}" stroke="${P.surface}" stroke-width="2"><title>${hit + 1} days: ${(v[hit] * 100).toFixed(0)}%</title></circle>`;
      s += `<text class="v" x="${x(hit) + 8}" y="${y(v[hit]) + 14}">${hit + 1} ${lang === 'ko' ? '일' : 'days'}</text>`;
    }
    s += `<text x="${W - R}" y="${H + 2}" text-anchor="end">${esc(c.x[lang])} →</text>`;
    return s + '</svg>';
  }

  // One square per day with fills: bright when every fill that day matched the tape.
  function calendar(c, lang) {
    const days = c.days;
    if (!days.length) return '';
    const first = new Date(days[0] + 'T00:00:00Z');
    const W = 360, cols = 61, cell = W / cols;
    const idx = days.map((d) => Math.round((new Date(d + 'T00:00:00Z') - first) / 864e5));
    const rows = Math.ceil((idx[idx.length - 1] + 1) / cols);
    let s = `<svg viewBox="0 0 ${W} ${rows * cell + 18}" role="img">`;
    days.forEach((d, i) => {
      const k = idx[i];
      const ok = c.ok[i] === c.total[i];
      const col = ok ? '#2bd38a' : '#f5b014';
      s += `<rect x="${(k % cols) * cell}" y="${Math.floor(k / cols) * cell}" width="${cell - 1}" height="${cell - 1}" rx="1" fill="${col}" opacity="${ok ? 0.85 : 1}"><title>${d}: ${c.ok[i]}/${c.total[i]}</title></rect>`;
    });
    const y = rows * cell + 13;
    s += `<rect x="0" y="${y - 8}" width="8" height="8" rx="1" fill="#2bd38a"/><text x="12" y="${y}">${esc(c.legend[lang][0])}</text>`;
    s += `<rect x="150" y="${y - 8}" width="8" height="8" rx="1" fill="#f5b014"/><text x="162" y="${y}">${esc(c.legend[lang][1])}</text>`;
    return s + '</svg>';
  }

  // Minute bars from the tape with his buys and sells as ticks under the price.
  function tape(c, lang) {
    const W = 360, H = 170, T = 8, PB = 112, VB = 150, L = 4, R = 4;
    const n = c.price.length;
    const lo = Math.min(...c.price), hi = Math.max(...c.price);
    const x = (i) => L + (i / (n - 1)) * (W - L - R);
    const y = (p) => PB - ((p - lo) / (hi - lo || 1)) * (PB - T);
    const vmax = Math.max(...c.buy, ...c.sell) || 1;
    let s = `<svg viewBox="0 0 ${W} ${H + 18}" role="img">`;
    const mid = (PB + VB) / 2 + 6;
    c.price.forEach((_, i) => {
      const hb = Math.sqrt(c.buy[i] / vmax) * (mid - PB - 6);
      const hs = Math.sqrt(c.sell[i] / vmax) * (VB - mid);
      if (hb > 0.3) s += `<rect x="${x(i) - 0.6}" y="${mid - hb}" width="1.2" height="${hb}" fill="${P.buy}"><title>+${c.buy[i]}M</title></rect>`;
      if (hs > 0.3) s += `<rect x="${x(i) - 0.6}" y="${mid}" width="1.2" height="${hs}" fill="${P.sell}"><title>-${c.sell[i]}M</title></rect>`;
    });
    s += `<line x1="${L}" x2="${W - R}" y1="${mid}" y2="${mid}" stroke="${P.unsure}"/>`;
    s += `<path d="${c.price.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p).toFixed(1)}`).join('')}" fill="none" stroke="#d6d6de" stroke-width="1.4"/>`;
    const li = c.price.indexOf(lo);
    s += `<circle cx="${x(li)}" cy="${y(lo)}" r="3.5" fill="${ACCENT}" stroke="${P.surface}" stroke-width="2"/><text class="v" x="${x(li) + 7}" y="${y(lo) + 3}">$${lo.toLocaleString('en-US')}</text>`;
    s += `<text x="${L}" y="${T + 8}">$${hi.toLocaleString('en-US')}</text>`;
    s += `<text x="${x(n / 2)}" y="${VB + 12}" text-anchor="middle">${esc(c.days[1])}</text><text x="${L}" y="${VB + 12}">${esc(c.days[0])}</text>`;
    const lg = c.legend[lang];
    [['#d6d6de', lg[0]], [P.buy, lg[1]], [P.sell, lg[2]]].forEach(([col, name], k) => {
      s += `<rect x="${L + k * 120}" y="${H + 6}" width="9" height="9" rx="2" fill="${col}"/><text x="${L + k * 120 + 14}" y="${H + 14}">${esc(name)}</text>`;
    });
    return s + '</svg>';
  }

  // One 100% column per period, split into ordered categories (the account's exposure buckets).
  function stack(c, lang) {
    const names = c.labels[lang];
    const colors = P.exposure;
    const W = 360, H = 150, B = 128, L = 4;
    const n = c.periods.length;
    const gw = (W - L * 2) / n;
    let s = `<svg viewBox="0 0 ${W} ${H + 40}" role="img">`;
    c.periods.forEach((p, i) => {
      let y = B;
      c.values[i].forEach((v, k) => {
        const h = v * (B - 6);
        if (h <= 0) return;
        y -= h;
        s += `<rect x="${L + i * gw + 1}" y="${y}" width="${gw - 2}" height="${Math.max(0, h - 1)}" fill="${colors[k]}"><title>${esc(p)} ${esc(names[k])}: ${(v * 100).toFixed(0)}%</title></rect>`;
      });
      if (p.endsWith('Q1') || i === 0) s += `<text x="${L + i * gw}" y="${B + 13}">${esc(p.slice(0, 4))}</text>`;
    });
    names.forEach((nm, k) => {
      const x = L + (k % 3) * 120, y = B + 28 + Math.floor(k / 3) * 14;
      s += `<rect x="${x}" y="${y - 8}" width="9" height="9" rx="2" fill="${colors[k]}"/><text x="${x + 13}" y="${y}">${esc(nm)}</text>`;
    });
    return s + '</svg>';
  }

  root.XCharts = { bars, pair, heat, curve, calendar, tape, stack, render: (c, lang) => (c && root.XCharts[c.type] ? root.XCharts[c.type](c, lang) : '') };
})(window);
