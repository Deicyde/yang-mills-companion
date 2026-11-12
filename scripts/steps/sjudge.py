#!/usr/bin/env python3
"""Render one judge prompt for several batches: their disagreements and noMatch checks.

Usage: python3 -I sjudge.py <work dir> <name> <batch>...   (writes scratch/steps2/prompts/judge-<name>.txt)
"""
import json
import sys


def main(work, name, *batches):
    S = f'{work}/scratch/steps2'
    tpl = open(f'{S}/prompts/judge.md').read()
    parts = []
    n = 0
    for b in batches:
        C = json.load(open(f'{S}/compare/{b}.json'))
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
