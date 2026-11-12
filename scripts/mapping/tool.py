#!/usr/bin/env python3
"""Lookup tool for the mapping campaign: items, batches, Lean declarations, checks.

  tool.py batch <B>            items of a batch: LaTeX, location, context, seeds
  tool.py item <id> [ctx]      one item, with <ctx> source lines around it (default 6)
  tool.py tex <file> <a> <b>   lines a..b of a manuscript file (part1/..., part2/...)
  tool.py decl <name> [n]      index row of a declaration and n source lines (default 40)
  tool.py search <regex> [--snippet] [--limit N]
                               declarations whose name (or statement snippet) matches
  tool.py keys <regex>         key statements (src/data/key-statements.tsv) matching
  tool.py exists <name>...     check names against the index and the compiled inventory
  tool.py check <json>         validate a mapper/verifier/judge output file
"""
import json, os, re, sys

HOME = os.path.expanduser('~/ym-companion')
REPO = f'{HOME}/repo'
LEAN = f'{HOME}/lean'
SRC = f'{HOME}/src/manuscript'
DECLS = f'{HOME}/scratch/decls.json'
INVENTORY = f'{LEAN}/verification/declaration-usage.tsv'
BATCHES = f'{REPO}/data/batches.json'

STATUSES = {
    'exact', 'close', 'stronger', 'weaker', 'differs', 'missing-hypothesis', 'parts',
    'inlined', 'definition-match', 'definition-close', 'definition-differs',
    'not-formalized-not-needed', 'no-match', 'unclear',
}
ROLES = {'key', 'attributed', 'support', 'helper'}

_decls = None


def decls():
    global _decls
    if _decls is None:
        d = json.load(open(DECLS))
        f = d['fields']
        _decls = {}
        for r in d['decls']:
            row = dict(zip(f, r)) if isinstance(r, list) else r
            if row.get('duplicate'):
                _decls.setdefault(row['name'] + '@dup', []).append(row)
                continue
            _decls.setdefault(row['name'], row)
    return _decls


def inventory():
    names = {}
    with open(INVENTORY) as fh:
        next(fh)
        for line in fh:
            p = line.rstrip('\n').split('\t')
            names.setdefault(p[1], (p[0], p[2], p[5]))
    return names


def items():
    return json.load(open(f'{REPO}/data/items.json'))['items']


def seeds():
    return json.load(open(f'{REPO}/data/seeds.json'))['items']


def show_item(it, sd, ctx=None):
    print(f"=== {it['id']}  ({it['kind']}{', ' + it['name'] if it.get('name') else ''}"
          f"{', principal ' + it['tag'] if it.get('principal') else ''})")
    print(f"    {it['file']}:{it['line']}-{it['end_line']}  section {it['section']['number']} "
          f"{it['section']['title']}" + (f" / {it['subsection']['title']}" if it.get('subsection') else ''))
    print(f"    context: {it['context']}" + (f", enclosing: {it['enclosing']}" if it.get('enclosing') else ''))
    if ctx:
        lines = open(f"{SRC}/{it['file']}").read().split('\n')
        a, b = max(1, it['line'] - ctx), min(len(lines), it['end_line'] + ctx)
        for i in range(a, b + 1):
            print(f'    {i:5d}| {lines[i-1]}')
    else:
        print('    statement:')
        for l in it['statement'].split('\n'):
            print('      ' + l)
    s = sd.get(it['id'], {})
    if s.get('units'):
        print('    units: ' + ', '.join(f"{u['unit']} ({u['title']}) -> src/outline/units/{u['unit'].replace('.', '-')}.md"
                                        for u in s['units']))
    for k in s.get('key_statements', []):
        print(f"    seed: {k['name']}  [{k['number']}] {k['summary']}")
    for g in s.get('glossary', []):
        print(f"    glossary: {json.dumps(g, ensure_ascii=False)[:200]}")


def cmd_batch(b):
    bs = json.load(open(BATCHES))['batches']
    ids = next(x['items'] for x in bs if x['id'] == b)
    by = {i['id']: i for i in items()}
    sd = seeds()
    print(f'batch {b}: {len(ids)} items: ' + ', '.join(ids))
    for i in ids:
        show_item(by[i], sd)
        print()


def cmd_item(i, ctx=6):
    by = {x['id']: x for x in items()}
    show_item(by[i], seeds(), ctx=int(ctx))


def cmd_tex(f, a, b):
    lines = open(f'{SRC}/{f}').read().split('\n')
    for i in range(int(a), min(int(b), len(lines)) + 1):
        print(f'{i:5d}| {lines[i-1]}')


def cmd_decl(name, n=40):
    D = decls()
    row = D.get(name)
    if row is None:
        cands = [k for k in D if k.endswith('.' + name)]
        if len(cands) == 1:
            row = D[cands[0]]
            print(f'(resolved {name} -> {cands[0]})')
        else:
            inv = inventory().get(name)
            if inv:
                print(f'{name}: not in the source index; in the compiled inventory: module {inv[0]}, status {inv[1]}, line {inv[2]}')
                return
            print(f'{name}: NOT FOUND' + (f'; candidates: {cands[:20]}' if cands else ''))
            return
    print(f"{row['name']}  [{row['kind']}]  {row['file']}:{row['line']}  module {row['module']}  unit {row.get('unit')}"
          f"  usage {row.get('usage')}" + ('  PRIVATE' if row.get('private') else ''))
    for k in row.get('key_statements') or []:
        print(f"  key statement {k['number']}: {k['summary']}")
    lines = open(f"{LEAN}/{row['file']}").read().split('\n')
    a = row['line']
    # include docstring above
    s = a - 1
    while s > 1 and (lines[s-2].strip().startswith(('/--', '-/', '--')) or (s > 1 and '/--' in ''.join(lines[max(0, s-15):s-1]) and not lines[s-2].strip() == '')):
        s -= 1
        if a - s > 25:
            break
    for i in range(s, min(len(lines), a + int(n)) + 1):
        print(f'{i:5d}| {lines[i-1]}')
    dups = D.get(row['name'] + '@dup')
    if dups:
        print('  also declared in: ' + ', '.join(f"{d['file']}:{d['line']}" for d in dups))


def cmd_search(*args):
    snip = '--snippet' in args
    lim = 60
    args = list(args)
    if '--limit' in args:
        j = args.index('--limit'); lim = int(args[j+1]); del args[j:j+2]
    args = [a for a in args if a != '--snippet']
    rx = re.compile(args[0])
    n = 0
    for k, r in decls().items():
        if k.endswith('@dup'):
            continue
        if rx.search(k) or (snip and r.get('snippet') and rx.search(r['snippet'])):
            print(f"{k}  [{r['kind']}]  {r['file']}:{r['line']}  unit {r.get('unit')}")
            n += 1
            if n >= lim:
                print(f'... (limit {lim})'); break


def cmd_keys(rx):
    rx = re.compile(rx, re.I)
    for line in open(f'{HOME}/src/data/key-statements.tsv'):
        if rx.search(line):
            p = line.rstrip('\n').split('\t')
            print(f'{p[0]}  {p[2]}  {p[5]}')


def cmd_exists(*names):
    D = decls()
    inv = None
    for n in names:
        if n in D:
            print(f'OK  {n}  {D[n]["file"]}:{D[n]["line"]}')
        else:
            inv = inv or inventory()
            print(('INV ' if n in inv else 'MISSING ') + n)


def cmd_check(path):
    d = json.load(open(path))
    errs = []
    D = decls()
    inv = None
    its = d.get('items', [])
    if not its:
        errs.append('no items')
    for it in its:
        iid = it.get('id')
        if it.get('status') not in STATUSES:
            errs.append(f'{iid}: bad status {it.get("status")}')
        if not it.get('note'):
            errs.append(f'{iid}: no note')
        for l in it.get('lean', []):
            if l.get('role') not in ROLES:
                errs.append(f'{iid}: bad role {l.get("role")} for {l.get("decl")}')
            n = l.get('decl')
            if n not in D:
                inv = inv or inventory()
                if n not in inv:
                    errs.append(f'{iid}: declaration not found: {n}')
        if it.get('status') in ('no-match', 'not-formalized-not-needed') and not it.get('searched'):
            errs.append(f'{iid}: status {it.get("status")} without searched')
        if it.get('status') not in ('no-match', 'not-formalized-not-needed', 'unclear') and not any(
                l.get('role') == 'key' for l in it.get('lean', [])):
            errs.append(f'{iid}: status {it.get("status")} without a key declaration')
    want = None
    if 'batch' in d and os.path.exists(BATCHES):
        bs = json.load(open(BATCHES))['batches']
        want = next((x['items'] for x in bs if x['id'] == d['batch']), None)
    if want is not None and d.get('agent') != 'judge' and 'judge' not in path:
        got = [i.get('id') for i in its]
        if sorted(got) != sorted(want):
            errs.append(f'items {got} != batch {want}')
    print('\n'.join(errs) if errs else f'OK {path}: {len(its)} items')
    return 1 if errs else 0


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', 'help', '--help'):
        print(__doc__); sys.exit(0)
    sys.exit(globals()['cmd_' + sys.argv[1]](*sys.argv[2:]) or 0)
