#!/usr/bin/env python3
"""Show which campaign steps exist per batch: map, verify, compare, judge (or none needed)."""
import json, os
# The workspace holding repo/, src/, lean/, scratch/ and out/: $YM_WORK, else this repository's parent.
HOME = os.environ.get('YM_WORK') or os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
S = f'{HOME}/scratch'
bs = json.load(open(f'{HOME}/repo/data/batches.json'))['batches']
for b in bs:
    i = b['id']
    st = [k for k in ('map', 'verify', 'judge') if os.path.exists(f'{S}/{k}/{i}.json')]
    c = f'{S}/compare/{i}.json'
    dis = None
    if os.path.exists(c):
        dis = sum(not r['agree'] for r in json.load(open(c)).values())
    print(f"{i:7s} {len(b['items']):3d}  {' '.join(st):20s} disagree={dis}")
