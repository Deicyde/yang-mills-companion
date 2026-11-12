#!/usr/bin/env python3
"""Compare mapper and verifier outputs of batches; list the items a judge must decide.

  compare.py <batch>...   prints one line per item: AGREE or DISAGREE with the reason,
                          and writes scratch/compare/<batch>.json

Two outputs agree on an item when they give the same status and their key declarations
overlap (or both have none). For `no-match` and `not-formalized-not-needed`, which have no key
declarations, the status alone decides.
"""
import json, os, sys

S = os.path.expanduser('~/ym-companion/scratch')


def load(kind, b):
    p = f'{S}/{kind}/{b}.json'
    if not os.path.exists(p):
        return None
    return {i['id']: i for i in json.load(open(p))['items']}


def keys(i):
    return sorted({l['decl'] for l in i.get('lean', []) if l.get('role') == 'key'})


def compare(b):
    m, v = load('map', b), load('verify', b)
    if m is None or v is None:
        print(f'{b}: missing ' + ' '.join(k for k, x in (('map', m), ('verify', v)) if x is None))
        return None
    ids = json.load(open(os.path.expanduser('~/ym-companion/repo/data/batches.json')))
    ids = next(x['items'] for x in ids['batches'] if x['id'] == b)
    res = {}
    for i in ids:
        a, c = m.get(i), v.get(i)
        if a is None or c is None:
            res[i] = {'agree': False, 'why': 'missing in ' + ('mapper' if a is None else 'verifier')}
            continue
        why = []
        if a['status'] != c['status']:
            why.append(f"status {a['status']} vs {c['status']}")
        ka, kc = set(keys(a)), set(keys(c))
        if (ka or kc) and not (ka & kc):
            why.append(f'keys {keys(a)} vs {keys(c)}')
        res[i] = {'agree': not why, 'why': '; '.join(why),
                  'mapper': {'status': a['status'], 'keys': keys(a)},
                  'verifier': {'status': c['status'], 'keys': keys(c)}}
    os.makedirs(f'{S}/compare', exist_ok=True)
    json.dump(res, open(f'{S}/compare/{b}.json', 'w'), indent=1, ensure_ascii=False)
    for i, r in res.items():
        print(f"{b}  {'AGREE   ' if r['agree'] else 'DISAGREE'}  {i}  {r['why']}")
    return res


if __name__ == '__main__':
    for b in sys.argv[1:]:
        compare(b)
