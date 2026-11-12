"""Print the README's list of confirmed findings, and check it.

Reads data/mapping.json (the confirmed findings), data/corrections.json (per finding: `quote`, the
printed part of [M] that [L] does not prove, `decls`, the closest declarations of [L], and `readme`,
the line), data/items.json and data/linked-decls.json.  Checks that each quote is a contiguous
substring of the item's LaTeX statement and that each declaration is linked from the item and is in
the declaration index; exits non-zero otherwise.

Usage: python3 -I scripts/findings.py [<repository root>]
"""
import json
import os
import sys


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data = lambda n: json.load(open(os.path.join(root, 'data', n), encoding='utf-8'))
    items = {it['id']: it for it in data('items.json')['items']}
    corr, decls = data('corrections.json')['items'], data('linked-decls.json')['decls']
    errors, lines = [], []
    for rec in data('mapping.json')['items']:
        if not (rec.get('finding') or {}).get('confirmed'):
            continue
        c = corr.get(rec['id'], {})
        if not all(k in c for k in ('quote', 'decls', 'readme')):
            errors.append(f"{rec['id']}: no quote, decls or readme line in data/corrections.json")
            continue
        if c['quote'] not in items[rec['id']]['statement']:
            errors.append(f"{rec['id']}: the quote is not in the printed statement")
        linked = {l['decl'] for l in rec['lean']}
        for d in c['decls']:
            if d not in decls or d not in linked:
                errors.append(f"{rec['id']}: {d} is not a linked declaration")
        lines.append(f"- **{rec['id']}**: `{' '.join(c['quote'].split())}`. {c['readme']}")
    print('\n'.join(lines))
    if errors:
        sys.exit('\n'.join(errors))


if __name__ == '__main__':
    main()
