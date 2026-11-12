#!/usr/bin/env python3
"""Statistics of the steps campaign's mapping, for the session report.

Usage: python3 -I sstats.py <work dir>   (prints markdown)
"""
import collections
import json
import os
import sys

CLASSES = ['1-to-1', 'Faithful', 'Partial', 'Deviates', 'Absent', 'Unjudged']
RELS = ['exactMatch', 'closeMatch', 'broadMatch', 'narrowMatch', 'hasPart', 'relatedMatch', 'noMatch', None]


def pct(a, b):
    return f'{a}/{b} ({100 * a / b:.0f}%)' if b else f'{a}/0'


def main(work):
    S = f'{work}/scratch/steps2'
    bs = json.load(open(f'{work}/repo/data/steps-batches.json'))['batches']
    tot = agreed = 0
    why = collections.Counter()
    nomatch_checks = 0
    for B in bs:
        p = f'{S}/compare/{B["id"]}.json'
        if not os.path.exists(p):
            continue
        C = json.load(open(p))
        for r in C['records'].values():
            tot += 1
            agreed += r['agreed']
            if not r['agreed']:
                why[r['why'].split(' ')[0] if r['why'] != 'declaration set' else 'declaration set'] += 1
        nomatch_checks += len(C['nomatch_check'])
    rulings = collections.Counter()
    judged = 0
    for f in os.listdir(f'{S}/judge'):
        for r in json.load(open(f'{S}/judge/{f}'))['records']:
            rulings[r.get('ruling')] += 1
            judged += 1
    print(f'- records compared: {tot}; agreed {pct(agreed, tot)}; disagreed {pct(tot - agreed, tot)} '
          f'(class {why["class"]}, declaration set only {why["declaration set"]})')
    print(f'- judged: {judged} records; rulings: ' + ', '.join(f'{k} {v}' for k, v in rulings.most_common()))
    print(f'- noMatch checks assigned to judges (one in five of agreed noMatch, plus 4 added): {nomatch_checks}')
    for name in ('steps', 'displays'):
        d = json.load(open(f'{work}/repo/data/manuscript-{name}-mapping.json'))
        recs = d['records']
        n = len(recs)
        rc = collections.Counter(r['relation'] for r in recs)
        cc = collections.Counter(r['class'] for r in recs)
        print(f'\n**{name}** ({n} records)\n')
        print('| relation | count |\n|---|---:|')
        for k in RELS:
            print(f'| {k or "none (Unjudged)"} | {pct(rc[k], n)} |')
        print('\n| class | count |\n|---|---:|')
        for k in CLASSES:
            print(f'| {k} | {pct(cc[k], n)} |')
        print(f'\nFormalized (1-to-1 + Faithful): {pct(cc["1-to-1"] + cc["Faithful"], n)}; '
              f'of judged records: {pct(cc["1-to-1"] + cc["Faithful"], n - cc["Unjudged"])}')


if __name__ == '__main__':
    main(sys.argv[1])
