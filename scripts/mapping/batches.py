#!/usr/bin/env python3
"""Split the items into mapping batches of about 12, in document order.

A statement, the displays inside it and the displays of its proof form one group, and a group
is never split. Batches do not cross a section; a section is cut into ceil(n/12) batches of
nearly equal size at group boundaries.
"""
import json, math, os

REPO = os.path.expanduser('~/ym-companion/repo')
TARGET = 12

items = json.load(open(f'{REPO}/data/items.json'))['items']
pos = {it['id']: k for k, it in enumerate(items)}

groups = {}
for it in items:
    root = it.get('enclosing') or it['id']
    groups.setdefault(root, []).append(it['id'])
ordered = sorted(groups.values(), key=lambda g: min(pos[i] for i in g))
for g in ordered:
    g.sort(key=lambda i: pos[i])

by_section = {}
for g in ordered:
    sec = items[pos[g[0]]]['section']['number']
    by_section.setdefault(sec, []).append(g)

batches = []
for sec, gs in by_section.items():
    n = sum(len(g) for g in gs)
    k = max(1, math.ceil(n / TARGET))
    size = n / k
    cur, acc, part = [], 0, 1
    for g in gs:
        if cur and acc + len(g) / 2 > size * part and part < k:
            batches.append((sec, part, cur))
            cur, part = [], part + 1
        cur += g
        acc += len(g)
    batches.append((sec, part, cur))

out = {'note': 'mapping batches: statements kept with their displays and proof displays',
       'batches': [{'id': f'S{int(sec):02d}-{p}', 'section': sec, 'items': ids} for sec, p, ids in batches]}
json.dump(out, open(f'{REPO}/data/batches.json', 'w'), indent=1, ensure_ascii=False)
print(len(batches), 'batches;', ' '.join(f"{b['id']}:{len(b['items'])}" for b in out['batches']))
