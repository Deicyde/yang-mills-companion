#!/usr/bin/env python3
"""Compare the mapper's and the verifier's records of a batch.

Two records disagree when their relations fall in different coverage classes (docs/coverage.md),
or, when neither is noMatch, on the declaration set: the two share no declaration.  Different lines
of one declaration (a statement and the line of the proof that applies it) are not a disagreement.  A record missing from
either file disagrees.  Of the records both call noMatch, every fifth (by a hash of the id) goes
to the judge for a search check.

Usage: python3 -I scompare.py <work dir> <batch>...   (writes scratch/steps2/compare/<batch>.json)
"""
import hashlib
import json
import os
import sys

CLASS = {'exactMatch': '1-to-1', 'closeMatch': 'Faithful', 'broadMatch': 'Faithful', 'hasPart': 'Partial',
         'narrowMatch': 'Deviates', 'relatedMatch': 'Deviates', 'noMatch': 'Absent'}


def load(path):
    if not os.path.exists(path):
        return {}
    return {r['id']: r for r in json.load(open(path)).get('records', [])}


def located(a, b):
    for x in a.get('ends', []):
        for y in b.get('ends', []):
            if x.get('decl') == y.get('decl'):
                return True
    return False


def compare(work, b):
    recs = json.load(open(f'{work}/repo/data/steps-batches.json'))
    want = next(x for x in recs['batches'] if x['id'] == b)['records']
    M = load(f'{work}/scratch/steps2/map/{b}.json')
    V = load(f'{work}/scratch/steps2/verify/{b}.json')
    out = {'batch': b, 'records': {}, 'disagree': [], 'nomatch_check': []}
    for rid in want:
        m, v = M.get(rid), V.get(rid)
        row = {'mapper': m and m.get('relation'), 'verifier': v and v.get('relation')}
        if not m or not v:
            row['why'] = 'missing'
        else:
            cm, cv = CLASS.get(m['relation']), CLASS.get(v['relation'])
            row['class_agreed'] = cm == cv
            if 'noMatch' in (m['relation'], v['relation']):
                row['location_agreed'] = None
            else:
                row['location_agreed'] = located(m, v)
            if not row['class_agreed']:
                row['why'] = f'class {cm} vs {cv}'
            elif row['location_agreed'] is False:
                row['why'] = 'declaration set'
        row['agreed'] = 'why' not in row
        out['records'][rid] = row
        if not row['agreed']:
            out['disagree'].append(rid)
        elif row['mapper'] == 'noMatch' and row['verifier'] == 'noMatch':
            if int(hashlib.sha256(rid.encode()).hexdigest(), 16) % 5 == 0:
                out['nomatch_check'].append(rid)
    os.makedirs(f'{work}/scratch/steps2/compare', exist_ok=True)
    json.dump(out, open(f'{work}/scratch/steps2/compare/{b}.json', 'w'), ensure_ascii=False, indent=1)
    print(f"{b}: {len(want)} records, {len(out['disagree'])} disagree, {len(out['nomatch_check'])} noMatch checks"
          f", mapper {len(M)}, verifier {len(V)}")
    return out


if __name__ == '__main__':
    for b in sys.argv[2:]:
        compare(sys.argv[1], b)
