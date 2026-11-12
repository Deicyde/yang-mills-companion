#!/usr/bin/env python3
"""Render the judge prompt of a batch from scratch/compare/<batch>.json."""
import json, os, sys
S = os.path.expanduser('~/ym-companion/scratch')
b = sys.argv[1]
c = json.load(open(f'{S}/compare/{b}.json'))
items = '\n'.join(f'- {i}: {r["why"]}' for i, r in c.items() if not r['agree'])
if not items:
    print('NONE'); sys.exit(0)
t = open(f'{S}/prompts/judge.md').read().replace('{BATCH}', b).replace('{ITEMS}', items)
open(f'{S}/prompts/judge-{b}.txt', 'w').write(t)
print(f'{S}/prompts/judge-{b}.txt')
