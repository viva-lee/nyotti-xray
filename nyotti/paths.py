from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
RAW = DATA / 'raw' / 'aoa'          # the released CSVs, never committed
CACHE = DATA / 'cache'              # parquet copies and derived tables
TAPE = DATA / 'tape'                # one JSON per day from the public-tape pass
SITE_DATA = ROOT / 'site' / 'data'  # what the viewer loads; small, committed

for d in (RAW, CACHE, TAPE, SITE_DATA):
    d.mkdir(parents=True, exist_ok=True)
