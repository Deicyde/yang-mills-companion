#!/usr/bin/env python3
"""Lookup and check tool for mapping proof steps and displays outside proofs to [L].

  stool.py batch <B>             the batch's records (LaTeX, location) and, per enclosing item,
                                 its verdict and key declarations with their line ranges
  stool.py src <name> [a b]      a declaration's full source with line numbers (or lines a..b of
                                 its file), headed by its range
  stool.py range <name>...       file and line range of declarations
  stool.py ids <json>            the same for the record ids listed in a file {"id", "kind", "records"}
  stool.py check <json>          validate a mapper/verifier/judge output file

For text and declaration search use ../mapping/tool.py (tex, search, keys, exists) and grep -rn.
"""
import json
import os
import re
import sys

HOME = os.environ.get('YM_WORK') or os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
REPO = f'{HOME}/repo'
LEAN = f'{HOME}/lean'
SRC = f'{HOME}/src/manuscript'
RANGES = f'{HOME}/scratch/steps2/ranges.json'
RELATIONS = ['exactMatch', 'closeMatch', 'broadMatch', 'narrowMatch', 'hasPart', 'relatedMatch', 'noMatch']
MAXSRC = 400

_r = None


def ranges():
    global _r
    if _r is None:
        _r = json.load(open(RANGES))
    return _r


def resolve(name):
    R = ranges()['ranges']
    if name in R:
        return name, R[name]
    c = [k for k in R if k.endswith('.' + name)]
    if len(c) == 1:
        return c[0], R[c[0]]
    return None, c


def records():
    st = json.load(open(f'{REPO}/data/manuscript-steps.json'))['steps']
    di = json.load(open(f'{REPO}/data/manuscript-displays.json'))['displays']
    return {r['id']: r for r in st + di}


def batch(b):
    bs = json.load(open(f'{REPO}/data/steps-batches.json'))['batches']
    return next(x for x in bs if x['id'] == b)


def mapping():
    return {i['id']: i for i in json.load(open(f'{REPO}/data/mapping.json'))['items']}


def items_near(rec):
    """Items around a display outside a statement: the last item before it and the first after."""
    its = json.load(open(f'{REPO}/data/items.json'))['items']
    same = [i for i in its if i['file'] == rec['file']]
    before = [i for i in same if int(i['line']) <= rec['line']]
    after = [i for i in same if int(i['line']) > rec['end_line']]
    return [x['id'] for x in (before[-1:] + after[:1])]


def show_item(iid, M, label):
    it = M.get(iid)
    if not it:
        print(f'--- {label} {iid}: not in data/mapping.json')
        return
    print(f"--- {label} {iid}: verdict {it['status']} ({it.get('relation')})")
    print(f"    note: {it.get('note', '')}")
    for l in it.get('lean', []):
        if l['role'] in ('key', 'helper', 'attributed'):
            n, r = resolve(l['decl'])
            where = f'{r[0]}:{r[1]}-{r[2]}' if n else l.get('where')
            print(f"    {l['role']:10s} {l['decl']}  {where}" + (f"  ({l['note']})" if l.get('note') else ''))
    sup = [l['decl'] for l in it.get('lean', []) if l['role'] == 'support']
    if sup:
        print('    support: ' + ', '.join(sup))
    if it.get('step'):
        print(f"    step: {it['step']}")


def cmd_ids(path):
    """Like `batch`, for the records listed in a JSON file {"id": ..., "records": [ids]}."""
    return cmd_batch(None, json.load(open(path)))


def cmd_batch(b, B=None):
    B = B or batch(b)
    b = b or B['id']
    R = records()
    M = mapping()
    print(f"batch {b}: {len(B['records'])} records ({B['kind']})")
    shown = set()
    for rid in B['records']:
        r = R[rid]
        enc = r.get('item') or r.get('enclosing')
        ctx = [enc] if enc else items_near(r)
        for iid in ctx:
            if iid not in shown:
                shown.add(iid)
                show_item(iid, M, 'item' if r.get('item') else ('enclosing statement' if enc else 'nearby item'))
                print()
        print(f"=== {rid}  [{r['kind']}{', ' + r['env'] if r.get('env') else ''}]  {r['file']}:{r['line']}-{r['end_line']}  p. {r['pages'][0]}")
        print('    ' + r['latex'].replace('\n', '\n    '))
        print()


def cmd_src(name, a=None, b=None):
    n, r = resolve(name)
    if not n:
        print(f'{name}: no range' + (f'; candidates {r[:20]}' if r else ''))
        return 1
    f, x, y = r
    print(f'{n}  {f}:{x}-{y}')
    dups = ranges()['dups'].get(n)
    if dups:
        print('  also declared at ' + ', '.join(f'{d[0]}:{d[1]}-{d[2]}' for d in dups))
    lines = open(f'{LEAN}/{f}', encoding='utf-8').read().split('\n')
    lo, hi = (int(a), int(b)) if a else (x, y)
    if not a and y - x + 1 > MAXSRC:
        hi = x + MAXSRC - 1
        print(f'  (first {MAXSRC} lines; pass a b for more)')
    for i in range(lo, min(hi, len(lines)) + 1):
        print(f'{i:5d}| {lines[i-1]}')


def cmd_range(*names):
    for name in names:
        n, r = resolve(name)
        print(f'{n}  {r[0]}:{r[1]}-{r[2]}' if n else f'MISSING {name}')


def cmd_check(path):
    d = json.load(open(path))
    errs = []
    R = ranges()['ranges']
    recs = d.get('records', [])
    judge = d.get('agent') == 'judge' or '/judge/' in path
    if not judge:
        want = (json.load(open(d['ids_file']))['records'] if d.get('ids_file')
                else batch(d.get('batch'))['records'])
        got = [x.get('id') for x in recs]
        if got != want:
            errs.append(f'record ids differ from the batch: missing {[w for w in want if w not in got]}, '
                        f'extra {[g for g in got if g not in want]}' if sorted(got) != sorted(want) else 'records out of order')
    for x in recs:
        rid = x.get('id')
        rel = x.get('relation')
        if rel not in RELATIONS:
            errs.append(f'{rid}: bad relation {rel}')
        if rel != 'exactMatch' and not x.get('note'):
            errs.append(f'{rid}: no note')
        ends = x.get('ends') or []
        if not ends:
            errs.append(f'{rid}: no ends')
        if rel == 'noMatch' and not x.get('searched'):
            errs.append(f'{rid}: noMatch without searched')
        for e in ends:
            n = e.get('decl')
            if n not in R:
                errs.append(f'{rid}: no such declaration (fully qualified, from stool.py range): {n}')
                continue
            f, a, b = R[n]
            if e.get('file') and e['file'] != f:
                alt = [d for d in ranges()['dups'].get(n, []) if d[0] == e['file']]
                if not alt:
                    errs.append(f'{rid}: {n} is not declared in {e["file"]}')
                    continue
                f, a, b = alt[0]
            ln = e.get('lines')
            if rel == 'noMatch' and ln is None:
                continue
            if not (isinstance(ln, list) and len(ln) == 2 and all(isinstance(v, int) for v in ln) and a <= ln[0] <= ln[1] <= b):
                errs.append(f'{rid}: lines {ln} of {n} not inside its range {a}-{b}')
            if rel != 'noMatch' and not e.get('conclusion'):
                errs.append(f'{rid}: end {n} has no conclusion')
        if x.get('text_error') and not (isinstance(x['text_error'], dict) and x['text_error'].get('claim')):
            errs.append(f'{rid}: text_error needs a claim')
        if judge and x.get('ruling') not in ('mapper', 'verifier', 'combined', 'neither', 'search-confirmed', 'search-rejected'):
            errs.append(f'{rid}: bad ruling {x.get("ruling")}')
    print('\n'.join(errs) if errs else f'OK {path}: {len(recs)} records')
    return 1 if errs else 0


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', 'help', '--help'):
        print(__doc__)
        sys.exit(0)
    sys.exit(globals()['cmd_' + sys.argv[1]](*sys.argv[2:]) or 0)
