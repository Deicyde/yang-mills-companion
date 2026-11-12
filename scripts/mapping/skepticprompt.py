#!/usr/bin/env python3
"""Render skeptic prompts for every claimed finding in data/mapping.json that lacks them.

Prints one line per rendered prompt: <item> <n> <prompt path>.
"""
import json, os, re, sys
# The workspace holding repo/, src/, lean/, scratch/ and out/: $YM_WORK, else this repository's parent.
HOME = os.environ.get('YM_WORK') or os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
S = f'{HOME}/scratch'
FINDINGS = {'weaker', 'missing-hypothesis', 'differs', 'no-match'}
t = open(f'{S}/prompts/skeptic.md').read()
m = json.load(open(f'{HOME}/repo/data/mapping.json'))
for r in m['items']:
    claim = r.get('verification', {}).get('claimed') or r.get('status')
    if claim not in FINDINGS:
        continue
    f = re.sub(r'[^A-Za-z0-9._-]', '', r['id'].replace(' ', '_'))
    for n in (1, 2):
        out = f'{S}/skeptic/{f}-{n}.json'
        p = f'{S}/prompts/skeptic-{f}-{n}.txt'
        if os.path.exists(out) or os.path.exists(p):
            continue
        decls = ', '.join(f"{l['decl']} ({l['role']})" for l in r['lean']) or 'none'
        s = (t.replace('{ITEM}', r['id']).replace('{STATUS}', claim).replace('{NOTE}', r['note'])
              .replace('{DECLS}', decls).replace('{OUT}', out).replace('{N}', str(n)))
        open(p, 'w').write(s)
        print(r['id'], n, p)
