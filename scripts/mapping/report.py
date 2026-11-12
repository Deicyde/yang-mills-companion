#!/usr/bin/env python3
"""Write the computed parts of out/REPORT-2.md (numbers, finding lists) to stdout as markdown."""
import json, os, glob, collections

HOME = os.path.expanduser('~/ym-companion')
S = f'{HOME}/scratch'
m = json.load(open(f'{HOME}/repo/data/mapping.json'))
items = m['items']
bs = json.load(open(f'{HOME}/repo/data/batches.json'))['batches']
log = [l.split() for l in open(f'{S}/agents.log') if l.strip()]

c = collections.Counter((l[0], l[2]) for l in log)
role = {'map': 'mapper', 'verify': 'verifier', 'judge': 'judge', 'skeptic': 'skeptic'}
print('| agent | Opus | Sonnet | total |\n|---|---:|---:|---:|')
for k in ('map', 'verify', 'judge', 'skeptic'):
    o, s = c[(k, 'opus')], c[(k, 'sonnet')]
    print(f'| {role[k]} | {o} | {s} | {o + s} |')
print(f'| all | {sum(v for (k, mm), v in c.items() if mm == "opus")} | '
      f'{sum(v for (k, mm), v in c.items() if mm == "sonnet")} | {len(log)} |')

done = [b['id'] for b in bs if os.path.exists(f'{S}/map/{b["id"]}.json') and os.path.exists(f'{S}/verify/{b["id"]}.json')]
agree = dis = 0
whys = collections.Counter()
for b in done:
    for r in json.load(open(f'{S}/compare/{b}.json')).values():
        agree += r['agree']; dis += not r['agree']
        if not r['agree']:
            w = r['why']
            whys['status and keys' if ('status' in w and 'keys' in w) else ('status' if 'status' in w else 'keys')] += 1
nj = len(glob.glob(f'{S}/judge/*.json'))
rul = collections.Counter()
for p in glob.glob(f'{S}/judge/*.json'):
    for i in json.load(open(p))['items']:
        rul[i.get('ruling', '?')] += 1
print(f'\nBatches: {len(bs)} defined, {len(done)} mapped and verified. Items compared: {agree + dis}; '
      f'agreed {agree}, disagreed {dis} (status only {whys["status"]}, keys only {whys["keys"]}, both {whys["status and keys"]}). '
      f'Batches with a judge: {nj}. Judge rulings: ' + ', '.join(f'{k} {v}' for k, v in rul.most_common()) + '.')

print('\nFinal statuses: ' + ', '.join(f'{k} {v}' for k, v in sorted(m['counts'].items(), key=lambda x: -x[1])) + '.')

claimed = [i for i in items if i['verification'].get('claimed')]
conf = [i for i in claimed if i['verification'].get('finding') == 'confirmed']
unconf = [i for i in claimed if i['verification'].get('finding') != 'confirmed']
print(f'\nClaimed findings (final status after the judge was a finding): {len(claimed)}; confirmed {len(conf)}; '
      f'unconfirmed {len(unconf)}.')

print('\n### Confirmed findings\n')
print('| item | status | [L] declarations compared | what [M] prints that [L] does not state |\n|---|---|---|---|')
for i in conf:
    ks = ', '.join(f'`{l["decl"]}`' for l in i['lean'] if l['role'] == 'key')[:200] or '(none states it)'
    note = i['note'].replace('|', '\\|').replace('\n', ' ')
    print(f'| {i["id"]} | {i["status"]} | {ks} | {note} |')

print('\n### Unconfirmed findings\n')
print('| item | claimed | final status | skeptics | reason |\n|---|---|---|---|---|')
for i in unconf:
    v = i['verification']
    sk = ', '.join('refuted' if s['refuted'] else 'upheld' for s in v.get('skeptics', [])) or 'not run'
    why = (next((s['reason'] for s in v.get('skeptics', []) if s['refuted']), None) or i['note'])
    why = why.replace('|', '\\|').replace('\n', ' ')[:300]
    print(f'| {i["id"]} | {v["claimed"]} | {i["status"]} | {sk} | {why} |')

nj_items = [i['id'] for i in items if not i['status']]
print(f'\nItems without a completed verdict: {len(nj_items)}' + (': ' + ', '.join(nj_items) if nj_items else '') + '.')
