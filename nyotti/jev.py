"""Minimal Jev client: paced, retried, thread-safe. Standard library only."""
import json
import os
import random
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = 'https://api.typesafe.ai'
PRICE_PER_MTOK = 0.042  # input only; output tokens are free
RETRYABLE = {408, 409, 425, 429, 500, 502, 503, 504, 529}


class JevError(Exception):
    def __init__(self, message, fatal=False):
        super().__init__(message)
        self.fatal = fatal


def read_env(path=None):
    """TYPESAFE_API_KEY and JEV_MODEL from the environment, else from a .env file."""
    env = {k: os.environ[k] for k in ('TYPESAFE_API_KEY', 'JEV_MODEL', 'TYPESAFE_BASE_URL') if k in os.environ}
    p = Path(path) if path else Path.cwd() / '.env'
    if p.exists():
        for line in p.read_text(encoding='utf-8').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k, v = line.split('=', 1)
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


class Limiter:
    """Spaces requests evenly; `pause` backs off the whole pipeline when the API asks."""

    def __init__(self, rps):
        self.interval = 1.0 / rps
        self.next_at = 0.0
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            now = time.monotonic()
            at = max(now, self.next_at)
            self.next_at = at + self.interval
        if at > now:
            time.sleep(at - now)

    def pause(self, seconds):
        with self.lock:
            self.next_at = max(self.next_at, time.monotonic() + seconds)


class Jev:
    def __init__(self, api_key, model='jev-latest', base_url=BASE_URL, rps=16, timeout=30, retries=6):
        if not api_key:
            raise JevError('TYPESAFE_API_KEY is not set (environment or .env).', fatal=True)
        self.key, self.model, self.url = api_key, model, base_url.rstrip('/') + '/v1/systemone'
        self.limiter, self.timeout, self.retries = Limiter(rps), timeout, retries
        self.lock = threading.Lock()
        self.input_tokens = 0
        self.requests = 0

    def ask(self, state, questions):
        body = json.dumps({'model': self.model, 'state': state, 'questions': questions}).encode()
        for attempt in range(self.retries + 1):
            self.limiter.wait()
            req = urllib.request.Request(self.url, data=body, method='POST', headers={
                'Authorization': f'Bearer {self.key}', 'Content-Type': 'application/json'})
            started = time.perf_counter()
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as res:
                    data = json.load(res)
                data['latency_ms'] = (time.perf_counter() - started) * 1000
                with self.lock:
                    self.requests += 1
                    self.input_tokens += data.get('usage', {}).get('input_tokens', 0)
                return data
            except urllib.error.HTTPError as e:
                text = e.read().decode('utf-8', 'replace')[:300]
                if e.code in (401, 403):
                    raise JevError(f'Jev rejected the API key ({e.code}).', fatal=True)
                if e.code not in RETRYABLE or attempt == self.retries:
                    raise JevError(f'Jev returned {e.code}: {text}')
                wait = float(e.headers.get('retry-after') or 0) or backoff(attempt)
                self.limiter.pause(wait)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if attempt == self.retries:
                    raise JevError(f'network error: {e}')
                time.sleep(backoff(attempt))

    @property
    def cost(self):
        return self.input_tokens * PRICE_PER_MTOK / 1e6


def backoff(attempt):
    return min(30.0, 0.5 * 2 ** attempt) * (0.75 + random.random() * 0.5)
