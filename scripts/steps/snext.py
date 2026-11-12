#!/usr/bin/env python3
"""Render the mapper and verifier prompts of the next batches not yet started.

Order: steps and display batches interleaved, three of steps to one of displays.  A batch is
started once listed in scratch/steps2/started.txt.

Usage: python3 -I snext.py <work dir> <n>   (prints the batch ids it rendered)
"""
import json
import os
import sys


def main(work, n):
    S = f'{work}/scratch/steps2'
    bs = json.load(open(f'{work}/repo/data/steps-batches.json'))['batches']
    P = [b['id'] for b in bs if b['kind'] == 'steps']
    D = [b['id'] for b in bs if b['kind'] == 'displays']
    order = []
    while P or D:
        order += P[:3] + D[:1]
        P, D = P[3:], D[1:]
    done = set(open(f'{S}/started.txt').read().split()) if os.path.exists(f'{S}/started.txt') else set()
    tpl = open(f'{S}/prompts/agent.md').read()
    picked = [b for b in order if b not in done][:int(n)]
    for b in picked:
        for role, d in (('mapper', 'map'), ('verifier', 'verify')):
            open(f'{S}/prompts/{d}-{b}.txt', 'w').write(tpl.replace('{ROLE}', role).replace('{BATCH}', b).replace('{DIR}', d))
    with open(f'{S}/started.txt', 'a') as fh:
        fh.write(''.join(b + '\n' for b in picked))
    print(' '.join(picked))


if __name__ == '__main__':
    main(*sys.argv[1:])
