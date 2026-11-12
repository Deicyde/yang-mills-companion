#!/usr/bin/env python3
"""Compare every batch whose mapper and verifier files both exist and were not compared since,
and print the campaign's state: batches compared, records agreed, disagreements awaiting a judge.

Usage: python3 -I scycle.py <work dir>
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scompare  # noqa: E402


def main(work):
    S = f'{work}/scratch/steps2'
    bs = json.load(open(f'{work}/repo/data/steps-batches.json'))['batches']
    tot = agreed = 0
    waiting = []
    for B in bs:
        b = B['id']
        m, v, c = (f'{S}/{d}/{b}.json' for d in ('map', 'verify', 'compare'))
        if not (os.path.exists(m) and os.path.exists(v)):
            continue
        if not os.path.exists(c) or os.path.getmtime(c) < max(os.path.getmtime(m), os.path.getmtime(v)):
            scompare.compare(work, b)
        C = json.load(open(c))
        tot += len(C['records'])
        agreed += sum(r['agreed'] for r in C['records'].values())
        if (C['disagree'] or C['nomatch_check']) and not os.path.exists(f'{S}/judge/{b}.json'):
            waiting.append(f"{b}:{len(C['disagree'])}+{len(C['nomatch_check'])}")
    print(f'compared {tot} records, agreed {agreed}; awaiting judge: {" ".join(waiting)}')


if __name__ == '__main__':
    main(sys.argv[1])
