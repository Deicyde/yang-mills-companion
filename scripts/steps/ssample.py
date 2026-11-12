#!/usr/bin/env python3
"""Draw the lead's 5% sample of final verdicts and print each record compactly for checking.

Usage: python3 -I ssample.py <work dir> <n> <seed> <exclude-batches,comma> [chunk k of m]
"""
import json
import random
import sys


def main(work, n, seed, exclude, k=None, m=None):
    S = f'{work}/scratch/steps2'
    ex = set(exclude.split(','))
    pending = set()
    for b in ex:
        C = json.load(open(f'{S}/compare/{b}.json'))
        pending |= set(C['disagree']) | set(C['nomatch_check'])
    recs = []
    for name in ('steps', 'displays'):
        recs += json.load(open(f'{work}/repo/data/manuscript-{name}-mapping.json'))['records']
    meta = {r['id']: r for name in ('steps', 'displays') for r in json.load(open(f'{work}/repo/data/manuscript-{name}.json'))[name]}
    pool = sorted(r['id'] for r in recs if r['verification']['complete'] and r['id'] not in pending)
    pick = sorted(random.Random(int(seed)).sample(pool, int(n)))
    json.dump({'seed': int(seed), 'pool': len(pool), 'sample': pick}, open(f'{S}/sample.json', 'w'), indent=1)
    if k:
        size = -(-len(pick) // int(m))
        pick = pick[(int(k) - 1) * size:int(k) * size]
    by = {r['id']: r for r in recs}
    for rid in pick:
        r, mt = by[rid], meta[rid]
        print(f"#### {rid} [{r['relation']}] via {r['verification']['source']}  {mt['file']}:{mt['line']}")
        print('  M: ' + mt['latex'][:500].replace('\n', ' '))
        print('  note: ' + (r.get('note') or ''))
        for e in r.get('ends', []):
            sn = (e.get('snippet') or '').split('\n')
            print(f"  L: {e['decl']} {e['lines']} :: {e.get('conclusion') or ''}")
            for l in sn[:4]:
                print('     | ' + l[:200])
    print(f'pool {len(pool)}')


if __name__ == '__main__':
    main(*sys.argv[1:])
