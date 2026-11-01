"""Ask Jev every lens question about every decision, one request per decision, cached on disk."""
import hashlib
import json
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

from . import describe
from .jev import Jev, JevError, read_env
from .paths import CACHE, ROOT

UI_ONLY = ('label', 'label_ko', 'hint', 'check')
CHECKS = {
    'against_move': lambda d: ((d.side == 'Buy') & (d.r24h < -0.01)) | ((d.side == 'Sell') & (d.r24h > 0.01)),
    'adds_position': lambda d: d.pos_after.abs() > d.pos_before.abs(),
}


def load_lenses(path=None):
    return json.loads(Path(path or ROOT / 'lenses' / 'default.json').read_text(encoding='utf-8'))['lenses']


def question(lens):
    return {k: v for k, v in lens.items() if k not in UI_ONLY and k != 'key'}


class Cache:
    """Append-only JSONL keyed by model, question and state, so edits re-ask only what changed."""

    def __init__(self, path):
        self.path, self.lock, self.map = path, threading.Lock(), {}
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            for line in path.read_text(encoding='utf-8').splitlines():
                if line:
                    row = json.loads(line)
                    self.map[row['k']] = row['a']
        self.out = open(path, 'a', encoding='utf-8')

    @staticmethod
    def key(model, q, state):
        raw = json.dumps([model, q, state], sort_keys=True, separators=(',', ':'))
        return hashlib.sha1(raw.encode()).hexdigest()

    def put(self, k, answer):
        with self.lock:
            self.map[k] = answer
            self.out.write(json.dumps({'k': k, 'a': answer}, separators=(',', ':')) + '\n')
            self.out.flush()


def flatten(key, a):
    if a['type'] == 'noul':
        return {key: a['noul']}
    if a['type'] == 'choice':
        out = {key: a['choice'], f'{key}_conf': a.get('confidence')}
        out.update({f'{key}:{k}': v for k, v in a.get('probabilities', {}).items()})
        return out
    return {key: a['score'], f'{key}_conf': a.get('confidence')}


def run(env=None, lens_path=None, limit=None, log=print):
    cfg = read_env(env)
    lenses = load_lenses(lens_path)
    d = pd.read_parquet(CACHE / 'decisions_xbtusd.parquet')
    d = d.dropna(subset=['r30d', 'volume_ratio', 'volatility_ratio', 'range_pos']).reset_index(drop=True)
    if limit:
        d = d.sample(n=min(limit, len(d)), random_state=7).sort_values('start').reset_index(drop=True)
    jev = Jev(cfg.get('TYPESAFE_API_KEY'), model=cfg.get('JEV_MODEL') or 'jev-latest',
              base_url=cfg.get('TYPESAFE_BASE_URL') or 'https://api.typesafe.ai')
    cache = Cache(CACHE / 'jev' / 'answers.jsonl')
    qs = {l['key']: question(l) for l in lenses}
    states = [describe.state(row) for row in d.itertuples()]
    latencies, answers, models = [], [None] * len(d), set()
    log(f'judge: {len(d)} decisions x {len(lenses)} lenses on {jev.model}')

    def work(i):
        st = states[i]
        keys = {k: Cache.key(jev.model, q, st) for k, q in qs.items()}
        missing = {k: qs[k] for k, ck in keys.items() if ck not in cache.map}
        if missing:
            res = jev.ask(st, missing)
            latencies.append(res['latency_ms'])
            models.add(res.get('model'))
            for k, a in res['answers'].items():
                a = {kk: vv for kk, vv in a.items() if kk != 'legend'}
                cache.put(keys[k], a)
        answers[i] = {k: cache.map[ck] for k, ck in keys.items()}

    started, done = time.time(), 0
    with ThreadPoolExecutor(max_workers=24) as pool:
        jobs = [pool.submit(work, i) for i in range(len(d))]
        for job in as_completed(jobs):
            try:
                job.result()
            except JevError as e:
                if e.fatal:
                    pool.shutdown(cancel_futures=True)
                    raise SystemExit(str(e))
                log(f'judge: one decision failed: {e}')
            done += 1
            if done % 1000 == 0:
                log(f'judge: {done}/{len(d)} · {jev.requests} requests · ${jev.cost:.3f}', flush=True)
    wall = time.time() - started

    rows = []
    for i, a in enumerate(answers):
        row = {'id': int(d.id[i])}
        for k, ans in (a or {}).items():
            row.update(flatten(k, ans))
        rows.append(row)
    j = pd.DataFrame(rows)
    out = CACHE / ('judgments.parquet' if not limit else 'judgments_sample.parquet')
    j.to_parquet(out)
    (CACHE / 'jev' / 'states.jsonl').write_text(
        '\n'.join(json.dumps({'id': int(d.id[i]), 'state': s}) for i, s in enumerate(states)), encoding='utf-8')

    p50 = statistics.median(latencies) if latencies else 0
    if not limit:
        (CACHE / 'jev' / 'run.json').write_text(json.dumps({
            'model': ','.join(sorted(m for m in models if m)) or jev.model, 'decisions': len(d), 'lenses': len(lenses), 'requests': jev.requests,
            'input_tokens': jev.input_tokens, 'cost_usd': round(jev.cost, 4), 'p50_ms': round(p50),
            'wall_s': round(wall, 1)}))
    log(f'judge: {jev.requests} requests · {jev.input_tokens:,} input tokens · ${jev.cost:.3f} · '
        f'p50 {p50:.0f} ms · {wall:.1f}s · {len(d) - jev.requests} decisions from cache')
    m = d[['id']].merge(j, on='id')
    for lens in lenses:
        if lens.get('check') and lens['key'] in m:
            truth = CHECKS[lens['check']](d).to_numpy()
            p = m[lens['key']].to_numpy()
            agree = ((p > 0.5) == truth).mean()
            unsure = ((p > 0.3) & (p < 0.7)).mean()
            log(f"check {lens['key']}: Jev agrees with code on {agree:.2%} of {len(p)} decisions "
                f'({unsure:.1%} answered between 0.3 and 0.7)')
    return j
