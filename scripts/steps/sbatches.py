#!/usr/bin/env python3
"""Batches for mapping proof steps and displays outside proofs to [L].

Steps: whole proofs in document order, packed while a batch stays at most 30 records; a proof of
more than 30 steps is a batch of its own, and a proof of at most 5 steps may bring a batch to 35.  Displays: by section, consecutive sections joined while
the batch stays at most 25 records, a section of more than 30 displays cut into nearly equal
consecutive chunks of at most 25.

Usage: python3 -I sbatches.py <repo dir>   (writes data/steps-batches.json)
"""
import json
import math
import sys

MAX = 25
PACK = 30


def main(repo):
    steps = json.load(open(f'{repo}/data/manuscript-steps.json'))
    disp = json.load(open(f'{repo}/data/manuscript-displays.json'))['displays']
    by_item = {}
    for s in steps['steps']:
        by_item.setdefault(s['item'], []).append(s['id'])
    batches = []
    cur, cur_items = [], []

    def flush():
        nonlocal cur, cur_items
        if cur:
            batches.append({'id': f'P{len([b for b in batches if b["kind"] == "steps"]) + 1:02d}',
                            'kind': 'steps', 'items': cur_items, 'records': cur})
        cur, cur_items = [], []

    for p in steps['proofs']:
        ids = [f"{p['item']} step {n}" for n in p['steps']]
        if cur and len(cur) + len(ids) > (PACK + 5 if len(ids) <= 5 else PACK):
            flush()
        cur = cur + ids
        cur_items.append(p['item'])
    flush()
    secs = {}
    for d in disp:
        secs.setdefault(d['section']['number'], []).append(d['id'])
    groups = []
    for sec, ids in secs.items():
        if groups and len(groups[-1][1]) + len(ids) <= MAX:
            groups[-1][0].append(sec)
            groups[-1][1].extend(ids)
        else:
            groups.append(([sec], list(ids)))
    for secs_, ids in groups:
        k = 1 if len(ids) <= 30 else math.ceil(len(ids) / MAX)
        size = math.ceil(len(ids) / k)
        for j in range(k):
            chunk = ids[j * size:(j + 1) * size]
            batches.append({'id': f'D{int(secs_[0]):02d}' + (f'-{j + 1}' if k > 1 else ''), 'kind': 'displays',
                            'sections': secs_, 'records': chunk})
    json.dump({'about': __doc__.split('\n\n')[1], 'batches': batches},
              open(f'{repo}/data/steps-batches.json', 'w'), ensure_ascii=False, indent=1)
    n = [len(b['records']) for b in batches]
    print(f'{len(batches)} batches ({sum(b["kind"] == "steps" for b in batches)} of steps), '
          f'{sum(n)} records, sizes {min(n)}-{max(n)}')


if __name__ == '__main__':
    main(sys.argv[1])
