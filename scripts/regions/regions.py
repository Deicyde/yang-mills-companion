"""Regions of the items of [M] on the committed `manuscript/main.pdf`.

Adapted from the ternary Goldbach companion's regions.py.  Pipeline:

1. `build.sh` recompiles [M] with `regionmarks.tex`, which records `\\pdfsavepos` markers
   (formal-companion's informalize marker mechanism) at every theorem-like head and end and at
   every numbered display; `layoutcheck.py` shows that the rebuilt PDF prints every word of the
   committed PDF at the same place, so the markers are positions on the committed PDF.
2. This script turns the markers into boxes, spanning the text width, from the first to the last
   ink (the committed PDF's word boxes, `pdftotext -bbox`) between the markers:
   - a theorem-like item covers its statement, from its head line to its last line, closing
     display or closing list, one region per page;
   - a numbered display covers its display, from below the line before it to its end; in an
     alignment with several numbers, a numbered row covers the unnumbered rows above it (back to
     the previous numbered row), and the last numbered row also covers the unnumbered rows below
     it, as in items.json.
3. Checks on the committed PDF: the crop of each item's first region (`pdftotext -f p -l p -x -y
   -W -H`, in points) holds the item's printed number; the crop of a statement's last region holds
   the last word of its text outside math, and no proof; regions of two items overlap only where one
   item holds the other.  Where two boxes of items that do not nest overlap, both are cut at the
   midpoint of the overlap.

Usage: python3 -I regions.py <build dir> <committed PDF> <items json> <out regions json> <source commit>
"""
import collections
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

SP_PER_BP = 65781.76
PAD = 2.0


def bbox_words(pdf):
    """Per physical page: (width, height, [(text, x0, y0, x1, y1)]) from pdftotext -bbox."""
    out = subprocess.run(['pdftotext', '-bbox', pdf, '-'], capture_output=True, text=True).stdout
    pages, cur = [], None
    for line in out.splitlines():
        m = re.search(r'<page width="([\d.]+)" height="([\d.]+)">', line)
        if m:
            cur = (float(m.group(1)), float(m.group(2)), [])
            pages.append(cur)
            continue
        m = re.search(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', line)
        if m and cur is not None:
            t = m.group(5).replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
            cur[2].append((t, float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))))
    return pages


def read_aux(build):
    marks, enddisp, geo, afterdisp = {}, {}, {}, set()
    for f in glob.glob(os.path.join(build, '*.aux')):
        s = open(f, encoding='latin-1').read()
        for name, x, y, p in re.findall(r'\\zref@newlabel\{([^}]*)\}\{\\posx\{(\d+)\}\\posy\{(\d+)\}\\abspage\{(\d+)\}\}', s):
            marks[name] = (int(p), int(x) / SP_PER_BP, int(y) / SP_PER_BP)
        for n, k in re.findall(r'\\rmenddisp\{([^}]*)\}\{(\d+)\}', s):
            enddisp[n] = f'dend:{k}'
        for n, k in re.findall(r'\\rmendlist\{([^}]*)\}\{(\d+)\}', s):
            enddisp[n] = f'list:{k}:below'
        afterdisp |= {int(k) for k in re.findall(r'\\rmafterdisp\{(\d+)\}', s)}
        m = re.search(r'\\rmgeometry\{([^}]*)\}', s)
        if m:
            geo = {k: int(v) / SP_PER_BP for k, v in (kv.split('=') for kv in m.group(1).split(','))}
    return marks, enddisp, geo, afterdisp


class Layout:
    def __init__(self, geo):
        self.H = geo['pdfpageheight']
        self.top = geo['texttop']
        self.bottom = geo['texttop'] + geo['textheight']
        self.width = geo['textwidth']
        self.left = geo['textleft']
        self.right = self.left + self.width

    def y(self, mark):
        return self.H - mark[2]


def lines_of(ws):
    """Words grouped into visual lines (by vertical overlap), top to bottom: [(y0, y1, words)]."""
    out = []
    for w in sorted(ws, key=lambda w: (w[2] + w[4]) / 2):
        c = (w[2] + w[4]) / 2
        if out and c - (out[-1][0] + out[-1][1]) / 2 < 3.5:
            out[-1] = (min(out[-1][0], w[2]), max(out[-1][1], w[4]), out[-1][2] + [w])
        else:
            out.append((w[2], w[4], [w]))
    return out


def crop_text(pdf, page, rect, size):
    W, H = size
    x, y, w, h = rect[0] * W, rect[1] * H, rect[2] * W, rect[3] * H
    return subprocess.run(['pdftotext', '-f', str(page), '-l', str(page), '-x', str(int(x)), '-y', str(int(y)),
                           '-W', str(int(w + 1)), '-H', str(int(h + 1)), pdf, '-'], capture_output=True, text=True).stdout


def main():
    build, pdf, items_path, out_path, commit = sys.argv[1:6]
    items = json.load(open(items_path))['items']
    marks, enddisp, geo, afterdisp = read_aux(build)
    L = Layout(geo)
    pages = bbox_words(pdf)

    def inside(page, lo, hi):
        return [w for w in pages[page - 1][2] if lo < (w[2] + w[4]) / 2 < hi and L.left - 30 < w[1] and w[3] < L.right + 30]

    def span(page, lo, hi):
        ws = inside(page, lo, hi)
        if not ws:
            return None
        return (page, min(w[2] for w in ws), max(w[4] for w in ws))

    # every marker by page, top to bottom: floors for a display with no marker right above it
    by_page = collections.defaultdict(list)
    for n, m in marks.items():
        by_page[m[0]].append((L.y(m), n))
    boxes, notes = {}, collections.defaultdict(list)

    # theorem-like items, by number
    for it in items:
        if it['kind'] == 'equation':
            continue
        num = it['number'] or ''
        head = marks.get(f'thm:{num}:head')
        if head is None:
            notes[it['id']].append('no head marker')
            continue
        if f'thm:{num}:below' in marks:
            end = marks[f'thm:{num}:below']
        elif num in enddisp and enddisp[num] in marks:
            end = marks[enddisp[num]]
        else:
            notes[it['id']].append('no end marker')
            continue
        p, q = head[0], end[0]
        out = []
        for page in range(p, q + 1):
            lo = L.y(head) - 9 if page == p else L.top - 3
            hi = L.y(end) + 0.5 if page == q else L.bottom + 6
            s = span(page, lo, hi)
            if s:
                out.append(s)
        boxes[it['id']] = out

    # numbered display environments, in document order, matched with the k-th environment's markers
    envs = []
    for it in items:
        if it['kind'] != 'equation':
            continue
        key = (it['file'], tuple(it['env_lines']))
        if not envs or envs[-1][0] != key:
            envs.append((key, []))
        envs[-1][1].append(it)
    for k, (key, its) in enumerate(envs, 1):
        tags = [marks.get(f'eq:{k}:tag:{r}') for r in range(1, len(its) + 1)]
        if None in tags or f'eq:{k}:tag:{len(its) + 1}' in marks:
            for it in its:
                notes[it['id']].append(f'environment {k}: {sum(1 for t in tags if t)} number markers for {len(its)} items')
            continue
        page = tags[0][0]
        if any(t[0] != page for t in tags):
            for it in its:
                notes[it['id']].append('numbers of one environment on two pages')
            continue
        pre, post = marks.get(f'eq:{k}:pre'), marks.get(f'eq:{k}:post')
        ty = [L.y(t) for t in tags]
        floors = [y for y, n in by_page[page] if y < ty[0] - 1 and (n.startswith('dend:') or n.endswith(':head')
                                                                    or n.endswith(':below') or n.endswith(':pre'))]
        if pre and pre[0] == page:
            lo = L.y(pre)
        elif pre or k in afterdisp or not floors:
            lo = max(floors) if floors and (not pre or pre[0] == page) else L.top - 3
        else:
            lo = max(floors)
        # a head marker is on the head's baseline: the display starts below that line
        lo = max([lo] + [y + 3 for y, n in by_page[page] if n.endswith(':head') and lo - 1 < y < ty[0] - 1])
        if post and post[0] == page:
            hi = L.y(post) + 0.5
        else:
            # no end marker (multline; an equation holding a split): the lines that join the
            # numbered rows without a gap of more than a blank line's height
            hi = max(ty) + 4
            for y0, y1, _ in lines_of(inside(page, max(ty) - 1, L.bottom + 6)):
                if y0 > hi + 6:
                    break
                hi = max(hi, y1 + 0.5)
            notes[its[0]['id']].append('display end taken from the ink below its number')
        lines = lines_of(inside(page, lo, hi))
        groups = [[] for _ in its]
        for y0, y1, ws in lines:
            mid = (y0 + y1) / 2
            g = next((i for i, t in enumerate(ty) if mid <= t + 2.5), len(its) - 1)
            groups[g] += ws
        for it, ws in zip(its, groups):
            if not ws:
                notes[it['id']].append('no ink in its rows')
                continue
            boxes[it['id']] = [(page, min(w[2] for w in ws), max(w[4] for w in ws))]

    regions = {}
    for it in items:
        if it['id'] not in boxes or not boxes[it['id']]:
            continue
        regs = []
        for pg, y0, y1 in boxes[it['id']]:
            W, H = pages[pg - 1][0], pages[pg - 1][1]
            ws = inside(pg, y0 - 0.1, y1 + 0.1)
            x0 = min([L.left] + [w[1] for w in ws]) - PAD
            x1 = max([L.right] + [w[3] for w in ws]) + PAD
            top, bot = max(0.0, y0 - PAD), min(H, y1 + PAD)
            regs.append(dict(page=pg, rect=[round(x0 / W, 5), round(top / H, 5), round((x1 - x0) / W, 5),
                                            round((bot - top) / H, 5)]))
        regions[it['id']] = regs

    # overlaps: cut neighbouring boxes of items that do not nest at the midpoint between them
    src = {it['id']: it for it in items}

    def holds(a, b):
        """a's statement holds b (a display in a statement, or a statement inside another)."""
        A, B = src[a], src[b]
        return (B.get('enclosing') == a and B['context'] == 'statement') or (
            A['file'] == B['file'] and A['line'] <= B['line'] <= B['end_line'] <= A['end_line'] and A['kind'] != 'equation')

    def nests(a, b):
        return holds(a, b) or holds(b, a)
    on_page = collections.defaultdict(list)
    for iid, regs in regions.items():
        for r in regs:
            on_page[r['page']].append((iid, r))
    overlaps = []
    for pg, lst in sorted(on_page.items()):
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                (a, ra), (b, rb) = lst[i], lst[j]
                if nests(a, b):
                    continue
                ta, ba = ra['rect'][1], ra['rect'][1] + ra['rect'][3]
                tb, bb = rb['rect'][1], rb['rect'][1] + rb['rect'][3]
                if ta < bb and tb < ba:
                    upper, lower = (ra, rb) if ta <= tb else (rb, ra)
                    ub, lt = upper['rect'][1] + upper['rect'][3], lower['rect'][1]
                    mid = (ub + lt) / 2
                    if mid - upper['rect'][1] > 0.004 and lower['rect'][1] + lower['rect'][3] - mid > 0.004:
                        upper['rect'][3] = round(mid - upper['rect'][1] - 0.0002, 5)
                        lower['rect'][3] = round(lower['rect'][1] + lower['rect'][3] - mid - 0.0002, 5)
                        lower['rect'][1] = round(mid + 0.0002, 5)
                        notes[a].append(f'cut against {b} on page {pg}')
                        notes[b].append(f'cut against {a} on page {pg}')
                    else:
                        overlaps.append((pg, a, b))
    # what remains after the cuts
    left = []
    for pg, lst in sorted(on_page.items()):
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                (a, ra), (b, rb) = lst[i], lst[j]
                if nests(a, b):
                    continue
                if ra['rect'][1] < rb['rect'][1] + rb['rect'][3] and rb['rect'][1] < ra['rect'][1] + ra['rect'][3]:
                    left.append((pg, a, b))

    # acceptance: the crop of the first region holds the printed number (a continuation region on a
    # later page cannot: it is marked as such)
    fails, cont = [], 0
    for it in items:
        regs = regions.get(it['id'])
        if not regs:
            continue
        want = it['printed']
        for k, r in enumerate(regs):
            W, H = pages[r['page'] - 1][0], pages[r['page'] - 1][1]
            text = ' '.join(crop_text(pdf, r['page'], r['rect'], (W, H)).split())
            r['holds_number'] = want.replace(' ', '') in text.replace(' ', '')
            r['continuation'] = k > 0
            if k == 0 and not r['holds_number']:
                fails.append((it['id'], r['page']))
            if k > 0:
                cont += 1
    # and the crop of a statement's last region holds the last word of its text outside math, and
    # no proof
    ends = []
    for it in items:
        regs = regions.get(it['id'])
        if not regs or it['kind'] == 'equation':
            continue
        t = re.sub(r'\$[^$]*\$|\\\[.*?\\\]|\\begin\{(equation|align|gather|multline)\*?\}.*?\\end\{\1\*?\}', '',
                   it['statement'], flags=re.S)
        words = re.findall(r'[A-Za-z]{3,}', re.sub(r'\\[A-Za-z]+(\[[^]]*\])?(\{[^}]*\})?', '', t))
        r = regs[-1]
        text = crop_text(pdf, r['page'], r['rect'], pages[r['page'] - 1][:2]).replace('-\n', '')
        if (words and words[-1] not in text) or re.search(r'^\s*Proof\.', text, re.M):
            ends.append(it['id'])
    missing = {it['id']:'; '.join(notes[it['id']]) or 'no box' for it in items if it['id'] not in regions}
    sha = hashlib.sha256(open(pdf, 'rb').read()).hexdigest()
    layout = json.load(open(os.path.join(build, 'layoutcheck.json'))) if os.path.exists(
        os.path.join(build, 'layoutcheck.json')) else None
    out = dict(pdf=dict(url=f'https://raw.githubusercontent.com/scottnarmstrong/yang-mills-informalization/{commit}/manuscript/main.pdf',
                        sha256=sha, bytes=os.path.getsize(pdf), pages=len(pages)),
               coordinates='fractions of the displayed page (MediaBox, no rotation), from the top left: [x, y, w, h]',
               method='pdfsavepos markers of a rebuild whose words sit where the committed PDF prints them '
                      '(layoutcheck), boxes fitted to the committed PDF\'s word boxes',
               layout_check=layout and dict(pages=layout['pages'], mismatched_pages=layout['mismatched_pages'],
                                            words_compared=layout['words_compared']),
               items=regions, missing=missing, notes={k: v for k, v in notes.items() if v},
               checks=dict(regions=sum(len(v) for v in regions.values()), items_with_regions=len(regions),
                           items=len(items), first_region_number_failures=fails, statement_end_failures=ends,
                           continuation_regions=cont,
                           cut_pairs=sum(1 for v in notes.values() for n in v if n.startswith('cut')) // 2,
                           overlaps_not_nested=left))
    json.dump(out, open(out_path, 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(out['checks'], indent=1))
    print('missing', missing)


main()
