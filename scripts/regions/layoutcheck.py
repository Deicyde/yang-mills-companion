"""Compare the layout of a rebuilt PDF with the committed one, page by page.

New code; poppler's pdftotext.  A page matches when both PDFs print the same words on it, each
word of one at the same left and right edge and on the same line (to TOL points) as a word of the
same text on the other; the order of extraction is not compared.  Word heights are not
compared: they come from the font files, and the rebuild draws Latin Modern outlines on the same
metrics (ecmap.py).

Usage: python3 -I layoutcheck.py <committed PDF> <rebuilt PDF> [<out json>]
"""
import json
import re
import subprocess
import sys

TOL = 0.6


def words(pdf):
    out = subprocess.run(['pdftotext', '-bbox', pdf, '-'], capture_output=True, text=True).stdout
    pages = []
    for line in out.splitlines():
        if '<page ' in line:
            pages.append([])
        m = re.search(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', line)
        if m:
            pages[-1].append((m.group(5), float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))))
    return pages


def lines(ws):
    """Words grouped into lines by vertical overlap of the word centre with the line's first word."""
    out = []
    for w in ws:
        c = (w[2] + w[4]) / 2
        if out and abs(out[-1][0] - c) < 3:
            out[-1][1].append(w)
        else:
            out.append([c, [w]])
    return out


def main():
    a, b = words(sys.argv[1]), words(sys.argv[2])
    res = dict(pages=[len(a), len(b)], mismatched_pages={}, words_compared=0)
    for p, (wa, wb) in enumerate(zip(a, b), 1):
        res['words_compared'] += len(wa)
        bad = None
        if len(wa) != len(wb):
            bad = f'{len(wa)} words vs {len(wb)}'
        else:
            pool = {}
            for y in wb:
                pool.setdefault(y[0], []).append(y)
            for x in wa:
                hit = [y for y in pool.get(x[0], []) if abs(x[1] - y[1]) <= TOL and abs(x[3] - y[3]) <= TOL
                       and abs((x[2] + x[4]) / 2 - (y[2] + y[4]) / 2) <= 2.5]
                if not hit:
                    bad = f'word {x[0]!r} at x={x[1]:.1f},y={x[4]:.1f} has no counterpart'
                    break
                pool[x[0]].remove(hit[0])
        if bad:
            res['mismatched_pages'][p] = bad
    res['lines_on_committed'] = sum(len(lines(w)) for w in a)
    print(json.dumps(res, indent=1))
    if len(sys.argv) > 3:
        json.dump(res, open(sys.argv[3], 'w'), indent=1)


main()
