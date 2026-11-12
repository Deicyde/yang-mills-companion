#!/usr/bin/env python3
"""Show which campaign steps exist per batch: map, verify, compare, judge (or none needed)."""
import json, os
S = os.path.expanduser('~/ym-companion/scratch')
bs = json.load(open(os.path.expanduser('~/ym-companion/repo/data/batches.json')))['batches']
for b in bs:
    i = b['id']
    st = [k for k in ('map', 'verify', 'judge') if os.path.exists(f'{S}/{k}/{i}.json')]
    c = f'{S}/compare/{i}.json'
    dis = None
    if os.path.exists(c):
        dis = sum(not r['agree'] for r in json.load(open(c)).values())
    print(f"{i:7s} {len(b['items']):3d}  {' '.join(st):20s} disagree={dis}")
