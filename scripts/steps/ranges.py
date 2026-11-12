#!/usr/bin/env python3
"""Line ranges of [L]'s declarations, from the declaration index and the pinned source.

A declaration runs from its keyword line (the index's `line`) to the last line of code before the
next declaration of its file, its docstring and attributes, or an `end`/`namespace`/`section` or
`/-!` header at column 0, whichever comes first; trailing blank and comment lines are dropped.

Usage: python3 -I ranges.py <decls.json> <lean dir> <out json>
Output: {"fields": [...], "ranges": {name: [file, first, last], ...}, "dups": {name: [[file, first, last], ...]}}
"""
import collections
import json
import re
import sys

BOUNDARY = re.compile(r'^(end\b|namespace\b|section\b|/-!|noncomputable section\b|mutual\b|open\b|variable\b|universe\b|set_option\b|attribute\b|#)')
KEYWORD = re.compile(r'^\s*(?:@\[[^\]]*\]\s*|(?:private|protected|noncomputable|nonrec|partial|unsafe|scoped|local)\s+)*'
                     r'(?:theorem|lemma|def|abbrev|structure|class|inductive|instance|example|opaque|axiom)\b')


def head_start(lines, i):
    """First line (0-based) of the docstring and attributes above the keyword line i."""
    j = i
    while j > 0:
        prev = lines[j - 1].strip()
        if (prev.startswith('@[') and not KEYWORD.match(prev)) or prev.startswith('--'):
            j -= 1
        elif prev.endswith('-/'):
            k = j - 1
            while k > 0 and '/-' not in lines[k]:
                k -= 1
            j = k
        else:
            break
    return j


def main(decls_path, lean, out):
    d = json.load(open(decls_path))
    f = d['fields']
    by_file = collections.defaultdict(list)
    for r in d['decls']:
        row = dict(zip(f, r)) if isinstance(r, list) else r
        if row.get('generated') or row['kind'] == 'field':
            continue
        by_file[row['file']].append(row)
    ranges, dups = {}, collections.defaultdict(list)
    for file, rows in by_file.items():
        lines = open(f'{lean}/{file}', encoding='utf-8').read().split('\n')
        starts = sorted({r['line'] for r in rows})
        nxt = {a: b for a, b in zip(starts, starts[1:] + [len(lines) + 1])}
        for r in rows:
            a = r['line']
            stop = head_start(lines, nxt[a] - 1) if nxt[a] <= len(lines) else len(lines)
            for j in range(a, stop):  # 0-based j is line j+1
                if BOUNDARY.match(lines[j]) or (j > a - 1 and KEYWORD.match(lines[j]) and not lines[j].startswith(' ')):
                    stop = j
                    break
            b = stop  # 1-based last candidate line
            while b > a and (not lines[b - 1].strip() or lines[b - 1].strip().startswith('--')):
                b -= 1
            b = max(a, b)
            rng = [file, a, b]
            if r.get('duplicate') or r['name'] in ranges:
                dups[r['name']].append(rng)
            else:
                ranges[r['name']] = rng
    json.dump({'fields': ['file', 'first', 'last'], 'ranges': ranges, 'dups': dups},
              open(out, 'w'), ensure_ascii=False)
    print(f'{len(ranges)} ranges, {len(dups)} duplicated names')


if __name__ == '__main__':
    main(*sys.argv[1:])
