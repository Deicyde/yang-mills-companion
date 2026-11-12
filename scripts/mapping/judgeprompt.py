#!/usr/bin/env python3
"""Render the judge prompt of a batch from scratch/compare/<batch>.json."""
import json, os, sys
# The workspace holding repo/, src/, lean/, scratch/ and out/: $YM_WORK, else this repository's parent.
HOME = os.environ.get('YM_WORK') or os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
S = f'{HOME}/scratch'
b = sys.argv[1]
c = json.load(open(f'{S}/compare/{b}.json'))
items = '\n'.join(f'- {i}: {r["why"]}' for i, r in c.items() if not r['agree'])
if not items:
    print('NONE'); sys.exit(0)
t = open(f'{S}/prompts/judge.md').read().replace('{BATCH}', b).replace('{ITEMS}', items)
open(f'{S}/prompts/judge-{b}.txt', 'w').write(t)
print(f'{S}/prompts/judge-{b}.txt')
