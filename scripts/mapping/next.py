#!/usr/bin/env python3
"""List campaign tasks not yet launched (per scratch/agents.log), most urgent first:
judges, then skeptics, then mapper/verifier pairs in batch order."""
import json, os, glob, re, subprocess, sys
HOME = os.path.expanduser('~/ym-companion')
S = f'{HOME}/scratch'
launched = {tuple(l.split()[:2]) for l in open(f'{S}/agents.log') if l.strip()}
bs = [b['id'] for b in json.load(open(f'{HOME}/repo/data/batches.json'))['batches']]
out = []
for b in bs:
    if os.path.exists(f'{S}/map/{b}.json') and os.path.exists(f'{S}/verify/{b}.json') and ('judge', b) not in launched:
        r = subprocess.run([sys.executable, f'{HOME}/repo/scripts/mapping/compare.py', b], capture_output=True, text=True).stdout
        if 'DISAGREE' in r:
            out.append(('judge', b))
for p in sorted(glob.glob(f'{S}/prompts/skeptic-*.txt')):
    k = os.path.basename(p)[8:-4]
    if ('skeptic', k) not in launched:
        out.append(('skeptic', k))
for b in bs:
    for a in ('map', 'verify'):
        if (a, b) not in launched:
            out.append((a, b))
for a, b in out:
    print(a, b)
