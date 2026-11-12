#!/usr/bin/env python3
"""Campaign numbers for the report: agents, disagreements, judge rulings, findings."""
import json, os, glob, collections

# The workspace holding repo/, src/, lean/, scratch/ and out/: $YM_WORK, else this repository's parent.
HOME = os.environ.get('YM_WORK') or os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
S = f'{HOME}/scratch'
bs = json.load(open(f'{HOME}/repo/data/batches.json'))['batches']
m = json.load(open(f'{HOME}/repo/data/mapping.json'))
log = [l.split() for l in open(f'{S}/agents.log') if l.strip()]

print('## agents launched (completed runs; stopped runs are in failures)')
c = collections.Counter((l[0], l[2]) for l in log)
for k, v in sorted(c.items()):
    print(f'- {k[0]} on {k[1]}: {v}')
print(f'- total: {len(log)}')
print('failures:', open(f'{S}/failures.log').read().strip().replace('\n', '; ') if os.path.exists(f'{S}/failures.log') else 'none')

done = [b['id'] for b in bs if os.path.exists(f'{S}/map/{b["id"]}.json') and os.path.exists(f'{S}/verify/{b["id"]}.json')]
print(f'\n## batches: {len(bs)} defined, {len(done)} mapped and verified')
agree = dis = 0
for b in done:
    p = f'{S}/compare/{b}.json'
    if not os.path.exists(p):
        continue
    for r in json.load(open(p)).values():
        agree += r['agree']; dis += not r['agree']
print(f'items compared: {agree + dis}; agreed {agree}; disagreed {dis}')

rul = collections.Counter()
for p in glob.glob(f'{S}/judge/*.json'):
    for i in json.load(open(p))['items']:
        rul[i.get('ruling', '?')] += 1
print('judge rulings:', dict(rul))

items = m['items']
print('\n## final statuses')
print(json.dumps(m['counts']))
src = collections.Counter(i['verification'].get('source') for i in items if i['status'])
print('sources:', dict(src))
print('\n## findings')
for i in items:
    v = i['verification']
    if v.get('claimed'):
        sk = ''.join('R' if s['refuted'] else 'U' for s in v.get('skeptics', []))
        print(f"{i['id']}\t{v['claimed']}\t->{i['status']}\t{v.get('finding')}\t{sk}")
