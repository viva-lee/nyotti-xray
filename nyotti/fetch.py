"""Download the release from the trader's own Google Drive link and check it byte for byte."""
import hashlib
import shutil
import urllib.request
import zipfile

from .paths import DATA, RAW

DRIVE_ID = '1XDwxbriz_kOq44iH-mHcjsYTBklMnMW3'
DRIVE_URL = f'https://drive.usercontent.google.com/download?id={DRIVE_ID}&export=download&confirm=t'
SHA256 = 'b6f1dc7aadf8209bf6c99fd516a06c0cabdc77c5f16f9fc8df92fdf1d8d01b9a'
SIZE = 113_381_570
ZIP = DATA / 'raw' / 'aoa_public.zip'
EXPECTED = [
    'aoa-execution-2018-03-01-2018-12-31.csv',
    'aoa-execution-2019-01-01-2020-12-31.csv',
    'aoa-execution-2021-01-01-2021-06-30.csv',
    'aoa-execution-2021-07-01-2021-12-31.csv',
    'aoa-wallet-2018-03-01-2021-12-31.csv',
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def fetch(log=print):
    if all((RAW / name).exists() for name in EXPECTED) and ZIP.exists() and sha256(ZIP) == SHA256:
        log(f'release already present and verified ({SHA256[:12]}...)')
        return
    if not ZIP.exists() or ZIP.stat().st_size != SIZE:
        log('downloading the release from the original Google Drive link (113 MB)...')
        tmp = ZIP.with_suffix('.part')
        with urllib.request.urlopen(DRIVE_URL, timeout=120) as res, open(tmp, 'wb') as out:
            shutil.copyfileobj(res, out, 1 << 20)
        tmp.replace(ZIP)
    digest = sha256(ZIP)
    if digest != SHA256:
        raise SystemExit(f'SHA-256 mismatch: got {digest}, expected {SHA256}. Refusing to use this file.')
    log(f'SHA-256 matches the published release ({SHA256[:12]}...)')
    with zipfile.ZipFile(ZIP) as z:
        for name in EXPECTED:  # extract only the known CSVs, by exact name
            with z.open(name) as src, open(RAW / name, 'wb') as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
    log(f'extracted {len(EXPECTED)} CSVs to {RAW}')
