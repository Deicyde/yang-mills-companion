#!/usr/bin/env python3
"""Render one judge prompt for several batches: their disagreements and noMatch checks.

Usage: python3 -I sjudge.py <work dir> <name> [--only K,K] <batch>...   (writes scratch/steps2/prompts/judge-<name>.txt)

--only keeps the disagreements of the given kinds: `cross` (one relation formalized, 1-to-1 or
Faithful, and the other not), `nonformal` (two different classes, neither formalized), `formal`
(1-to-1 against Faithful), `declset` (same class, no shared declaration).  The judge rules on these
first when the budget cannot cover every disagreement.
"""
import json
import sys


CLASS = {'exactMatch': '1-to-1', 'closeMatch': 'Faithful', 'broadMatch': 'Faithful', 'hasPart': 'Partial',
         'narrowMatch': 'Deviates', 'relatedMatch': 'Deviates', 'noMatch': 'Absent'}
FORMAL = {'1-to-1', 'Faithful'}


def kind(row):
    m, v = CLASS.get(row['mapper']), CLASS.get(row['verifier'])
    if m == v:
        return 'declset'
    if (m in FORMAL) != (v in FORMAL):
        return 'cross'
    return 'formal' if m in FORMAL else 'nonformal'


def main(work, name, *batches):
    S = f'{work}/scratch/steps2'
    only = None
    if batches and batches[0] == '--only':
        only, batches = set(batches[1].split(',')), batches[2:]
    tpl = open(f'{S}/prompts/judge.md').read()
    parts = []
    n = 0
    for b in batches:
        C = json.load(open(f'{S}/compare/{b}.json'))
        if only:
            C['disagree'] = [r for r in C['disagree'] if kind(C['records'][r]) in only]
        dis = '\n'.join(f"  - {r} (mapper {C['records'][r]['mapper']}, verifier {C['records'][r]['verifier']}: "
                        f"{C['records'][r]['why']})" for r in C['disagree']) or '  (none)'
        nm = '\n'.join(f'  - {r}' for r in C['nomatch_check']) or '  (none)'
        n += len(C['disagree']) + len(C['nomatch_check'])
        parts.append(f'### Batch {b}\n\nDisagreements:\n{dis}\n\nnoMatch checks:\n{nm}\n')
    body = tpl.replace('{BATCHES}', ' '.join(batches)).replace('{LIST}', '\n'.join(parts))
    open(f'{S}/prompts/judge-{name}.txt', 'w').write(body)
    print(f'judge-{name}: {len(batches)} batches, {n} records')


if __name__ == '__main__':
    main(*sys.argv[1:])
