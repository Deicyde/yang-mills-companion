"""Regions of the unnumbered displays and the proof steps of [M] on the committed `main.pdf`.

New code, on regions.py's method: `build-steps.sh` rebuilds [M] with the markers of
regionmarks-steps.tex and shows with layoutcheck.py that every word of the committed PDF is
printed at the same place, so the markers are positions on the committed PDF; the boxes are fitted
to the committed PDF's own word boxes (`pdftotext -bbox`).

- A display (outside a proof, or a display step) covers the ink between its `pre` marker (below
  the line before it; on a display that follows a display, the previous display's end; at the top
  of a page, the top of the text block) and its `end` marker.  `multline*` has no end marker: its
  bottom is the ink joined to it without a gap of more than a blank line's height.
- A prose step runs from its start marker to its end marker.  Both are on baselines and carry the
  x of the step's first and last character, so a step that starts or ends inside a line gets
  quads: the first line from its start, the full lines between, the last line to its end.  A
  first line is taken from the left margin when the step opens its paragraph, list item or the
  text after a display (so an item label is inside) or no word is left of the start; a last line
  to the right margin when the step closes it or no word but the end-of-proof mark is right of
  the end.  The region's rect is the quads' bounding box.
- One region per page; a step crossing a page is cut at the bottom and top of the text block.
- Top and bottom edges move off ink as in regions.py (288 dpi, within 8 pt).
- Overlaps: a new box gives way to a committed numbered display's box (data/regions.json); two new
  boxes that overlap are cut in the gap between their word boxes (a text line touching a display
  keeps its words whole), then off ink within 3 pt.

Checks (all on the committed PDF; `pdftotext -f p -l p -x -y -W -H` crops, in points):
- display: the crop holds the display's distinctive tokens: every word of 3 or more letters in its
  \\text, \\mathrm, \\operatorname, \\textup, \\rm and similar, and at least DISPLAY_COVER of the
  letters and digits its LaTeX prints literally (commands, labels and references removed);
- prose step: the crop holds its first and last words (letters and digits only, LaTeX commands
  removed; a step whose text has no word of 3 letters outside math uses its math, normalized the
  same way) anywhere, and its first and last EDGE letters or digits, math included, in the
  crops of its first two and last two printed lines;
- no word of the committed PDF lies in the quads of two steps, and no two steps of one proof
  overlap; every region holds a word.

Usage: python3 -I steps_regions.py lines <build dir> <committed PDF> <seg json> <out json>
       python3 -I steps_regions.py regions <build dir> <committed PDF> <steps json> <displays json>
           <items regions json> <items json> <out json> <commit>
"""
import collections
import concurrent.futures
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

SP_PER_BP = 65781.76
PAD = 2.0
DPI = 288
SNAP = 8.0
DISPLAY_COVER = 0.8
EDGE = 4


def bbox_words(pdf):
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
    marks, geo, afterdisp = {}, {}, set()
    for f in glob.glob(os.path.join(build, '**', '*.aux'), recursive=True):
        s = open(f, encoding='latin-1').read()
        for name, x, y, p in re.findall(r'\\zref@newlabel\{([^}]*)\}\{\\posx\{(\d+)\}\\posy\{(\d+)\}\\abspage\{(\d+)\}\}', s):
            marks[name] = (int(p), int(x) / SP_PER_BP, int(y) / SP_PER_BP)
        afterdisp |= set(re.findall(r'\\rmafterdisp\{([A-Z][^}]*)\}', s))
        for lab, num in re.findall(r'\\newlabel\{([^}]*)\}\{\{([^{}]*)\}', s):
            LABELS[lab] = num
        m = re.search(r'\\rmgeometry\{([^}]*)\}', s)
        if m:
            geo = {k: int(v) / SP_PER_BP for k, v in (kv.split('=') for kv in m.group(1).split(','))}
    return marks, geo, afterdisp


class Ink:
    """Dark pixels of the committed PDF's pages, rendered on demand (regions.py's)."""
    def __init__(self, pdf):
        self.pdf, self.pages, self.tmp = pdf, {}, tempfile.TemporaryDirectory()

    def page(self, pg):
        if pg not in self.pages:
            stem = os.path.join(self.tmp.name, f'p{pg}')
            subprocess.run(['pdftoppm', '-f', str(pg), '-l', str(pg), '-r', str(DPI), '-gray', '-singlefile',
                            self.pdf, stem], check=True)
            raw = open(stem + '.pgm', 'rb').read()
            magic, dims, maxval, px = raw.split(b'\n', 3)
            w, h = map(int, dims.split())
            self.pages[pg] = (w, h, px)
        return self.pages[pg]

    def blank(self, pg, y, x0, x1):
        w, h, px = self.page(pg)
        k = DPI / 72
        r = int(y * k)
        if not 0 <= r < h:
            return True
        row = px[r * w + max(0, int(x0 * k)):r * w + min(w, int(x1 * k) + 1)]
        return all(b >= 224 for b in row)

    def snap(self, pg, y, x0, x1, outward, lo=None, hi=None):
        """The nearest blank row within SNAP points, preferring `outward`, kept inside [lo, hi]."""
        if self.blank(pg, y, x0, x1):
            return y
        step = 72 / DPI / 2
        for n in range(1, int(SNAP / step) + 1):
            for d in (outward, -outward):
                z = y + d * n * step
                if (lo is not None and z < lo) or (hi is not None and z > hi):
                    continue
                if self.blank(pg, z, x0, x1):
                    return z
        return y


class Doc:
    def __init__(self, build, pdf):
        self.pdf = pdf
        self.marks, geo, self.afterdisp = read_aux(build)
        self.H = geo['pdfpageheight']
        self.top = geo['texttop']
        self.bottom = geo['texttop'] + geo['textheight']
        self.left = geo['textleft']
        self.right = self.left + geo['textwidth']
        self.pages = bbox_words(pdf)
        self.by_page = collections.defaultdict(list)
        for n, m in self.marks.items():
            self.by_page[m[0]].append((self.y(m), n))

    def y(self, m):
        return self.H - m[2]

    def words(self, pg, lo=None, hi=None):
        lo = self.top - 3 if lo is None else lo
        hi = self.bottom + 6 if hi is None else hi
        return [w for w in self.pages[pg - 1][2] if lo < (w[2] + w[4]) / 2 < hi
                and self.left - 30 < w[1] and w[3] < self.right + 30]

    def line_at(self, pg, base):
        """The words whose box holds the baseline `base` and ends within a descender below it (one
        printed line; a display's taller boxes reaching up to the baseline are not on it)."""
        return [w for w in self.words(pg) if w[2] - 0.5 < base < w[4] + 0.5 and w[4] < base + 6]

    def text_lines(self, pg, lo, hi):
        """Printed lines between lo and hi: the bottoms of the boxes of text words (two letters or
        more, of the text font's box height), clustered; math glyphs of other sizes would add lines."""
        ws = sorted((w for w in self.words(pg, lo, hi) if re.fullmatch(r'[A-Za-z,.;:()-]*[A-Za-z]{2,}[A-Za-z,.;:()-]*', w[0])
                     and 13.5 < w[4] - w[2] < 15), key=lambda w: w[4])
        out = []
        for w in ws:
            if out and w[4] - out[-1][-1] < 3.5:
                out[-1].append(w[4])
            else:
                out.append([w[4]])
        return len(out)

    # prose spans -------------------------------------------------------------------------
    def prose(self, s, e, opens=False, closes=False):
        """Regions [(page, quads)] of the span from start marker s to end marker e; quads in points.
        A span that opens its paragraph (or list item, or the text after a display) takes its
        first line from the margin, so that an item label is inside; one that closes it, its last
        line to the margin."""
        ms, me = self.marks[s], self.marks[e]
        out = []
        for pg in range(ms[0], me[0] + 1):
            first = pg == ms[0]
            last = pg == me[0]
            if first:
                b0 = self.y(ms)
                l0 = self.line_at(pg, b0)
                x0 = ms[1]
                if opens or not any(w[3] <= x0 + 0.5 for w in l0):
                    x0 = self.left
                top0 = min([w[2] for w in l0 if w[1] >= x0 - 0.5] or [b0 - 8])
                bot0 = max([w[4] for w in l0] or [b0 + 2])
            else:
                ws = self.words(pg, self.top - 3, (self.y(me) + 1) if last else None)
                if not ws:
                    continue
                top0 = min(w[2] for w in ws)
                b0 = None
                x0 = self.left
            if last:
                b1 = self.y(me)
                l1 = self.line_at(pg, b1)
                x1 = me[1]
                rest = [w for w in l1 if w[1] >= x1 - 0.5]
                if closes or not rest or all(re.fullmatch(r'[\u220e\u25a1\u25a0]', w[0]) for w in rest):
                    x1 = max([self.right] + [w[3] for w in rest])
                bot1 = max([w[4] for w in l1 if w[3] <= x1 + 0.5] or [b1 + 2])
                top1 = min([w[2] for w in l1] or [b1 - 8])
            else:
                ws = self.words(pg, (top0 - 0.5) if first else None, None)
                bot1 = max(w[4] for w in ws)
                b1 = None
                x1 = self.right
                top1 = max(w[2] for w in ws if w[4] >= bot1 - 0.5)
            one_line = first and last and abs(self.y(ms) - self.y(me)) < 3
            if one_line or (not first and not last):
                quads = [[x0, top0, x1, bot1]]
            else:
                f_partial = first and x0 > self.left + 0.5
                l_partial = last and x1 < self.right - 0.5
                if not first:
                    top0 = top0
                qs = []
                mid_top, mid_bot = top0, bot1
                if f_partial:
                    qs.append([x0, top0, self.right, bot0])
                    mid_top = bot0
                if l_partial:
                    mid_bot = top1
                if mid_bot > mid_top + 5:
                    # at least one full line between a partial first and a partial last line
                    qs.append([self.left, mid_top, self.right, mid_bot])
                elif f_partial and l_partial:
                    m = (mid_top + mid_bot) / 2
                    qs[0][3] = m
                    top1 = m
                elif f_partial:
                    qs[0][3] = max(qs[0][3], mid_bot)
                elif l_partial:
                    top1 = min(top1, mid_top)
                else:
                    qs.append([self.left, mid_top, self.right, mid_bot])
                if l_partial:
                    qs.append([self.left, top1, x1, bot1])
                quads = qs
            out.append((pg, quads))
        return out

    # displays ------------------------------------------------------------------------------
    def display(self, key, multline=False):
        pre, end = self.marks.get(f'{key}:pre'), self.marks.get(f'{key}:end')
        notes = []
        if end is None and not multline:
            return None, ['no end marker']
        if end is None:
            # multline*: from the line after the pre marker, the lines joined without a gap of
            # more than a blank line's height
            if pre is None:
                return None, ['no marker']
            pg, lo = pre[0], self.y(pre)
            ws = sorted(self.words(pg, lo, None), key=lambda w: w[2])
            hi = None
            for w in ws:
                if hi is not None and w[2] > hi + 6:
                    break
                hi = max(hi or 0, w[4] + 0.5)
            notes.append('display end taken from the ink below its start')
            return [(pg, lo, hi)], notes
        pe = end[0]
        hi = self.y(end) + 0.5
        if pre is not None and pre[0] == pe:
            spans = [(pe, self.y(pre), hi)]
        elif pre is not None and pre[0] < pe:
            spans = [(pre[0], self.y(pre), None)] + [(p, None, None) for p in range(pre[0] + 1, pe)] + [(pe, None, hi)]
            # a display does not break here unless it is an alignment: drop pages with no ink of it
        else:
            floors = [y for y, n in self.by_page[pe] if y < hi - 1.5 and (n.endswith(':end') or n.startswith('dend:')
                                                                          or n.endswith(':post') or n.endswith(':pre'))
                      and n != f'{key}:end']
            lo = max(floors) if floors else None
            spans = [(pe, lo, hi)]
            notes.append('after a display' if key in self.afterdisp else 'top of page')
        return spans, notes


def crop_text(pdf, page, q):
    x0, y0, x1, y1 = q
    return subprocess.run(['pdftotext', '-f', str(page), '-l', str(page), '-x', str(int(x0)), '-y', str(int(y0)),
                           '-W', str(int(x1 - x0 + 1)), '-H', str(int(y1 - y0 + 1)), pdf, '-'],
                          capture_output=True, text=True).stdout


def norm(s):
    return re.sub(r'[^A-Za-z0-9]', '', s)


LABELS = {}


def strip_latex(s, keep_math=True):
    s = re.sub(r'\\(ref|eqref)\{([^}]*)\}', lambda m: ' ' + LABELS.get(m.group(2), '') + ' ', s)
    s = re.sub(r'\\(label|cite|pageref|cref|Cref)\*?(\[[^]]*\])?\{[^}]*\}', ' ', s)
    if not keep_math:
        s = re.sub(r'\$[^$]*\$|\\\(.*?\\\)', ' ', s, flags=re.S)
    s = re.sub(r'\\begin\{[^}]*\}|\\end\{[^}]*\}', ' ', s)
    s = re.sub(r'\\[A-Za-z]+\*?', ' ', s)
    s = s.replace('~', ' ')
    return s


def edge_words(latex):
    """First and last words of a prose step: words of 3+ letters outside math, else its math."""
    t = strip_latex(latex, keep_math=False)
    ws = re.findall(r'[A-Za-z]{3,}', t)
    if ws:
        return ws[0], ws[-1]
    ws = [w for w in re.findall(r'[A-Za-z0-9]+', strip_latex(latex)) if w]
    return (ws[0], ws[-1]) if ws else (None, None)


def display_tokens(latex):
    words = []
    for m in re.finditer(r'\\(?:text|textup|textrm|textit|mathrm|operatorname|rm|mbox|textnormal)\*?\s*\{([^{}]*)\}', latex):
        words += re.findall(r'[A-Za-z]{3,}', m.group(1))
    words += re.findall(r'\\rm\s+([A-Za-z]{3,})', latex)
    chars = norm(strip_latex(latex))
    return words, chars


def coverage(want, have):
    c = collections.Counter(have)
    n = 0
    for ch in want:
        if c[ch] > 0:
            c[ch] -= 1
            n += 1
    return n / len(want) if want else 1.0


def lines_mode(build, pdf, seg_path, out_path):
    D = Doc(build, pdf)
    seg = json.load(open(seg_path))
    out = {}
    for s in seg['steps']:
        if s['kind'] != 'prose':
            continue
        k = s['key']
        regs = D.prose(f'{k}:s', f'{k}:e')
        n = 0
        for pg, quads in regs:
            lo = min(q[1] for q in quads)
            hi = max(q[3] for q in quads)
            n += D.text_lines(pg, lo - 0.1, hi + 0.1)
        out[k] = dict(item=s['item'], step=s['step'], printed_lines=n, sentences=len(s['sentences']),
                      pages=[r[0] for r in regs])
    json.dump(out, open(out_path, 'w'), indent=1)
    c = collections.Counter(v['printed_lines'] for v in out.values())
    print(sorted(c.items()))
    print('over 10 lines:', sum(1 for v in out.values() if v['printed_lines'] > 10))


def overlap(qa, qb):
    """Vertical overlap of two quads (points) that overlap horizontally by more than half a point."""
    if qa[0] < qb[2] - 0.5 and qb[0] < qa[2] - 0.5:
        return min(qa[3], qb[3]) - max(qa[1], qb[1])
    return 0.0


def inq(w, q):
    cx, cy = (w[1] + w[3]) / 2, (w[2] + w[4]) / 2
    return q[0] <= cx <= q[2] and q[1] <= cy <= q[3]


def regions_mode(build, pdf, steps_path, displays_path, items_regions_path, items_path, out_path, commit):
    D = Doc(build, pdf)
    ink = Ink(pdf)
    steps = json.load(open(steps_path))['steps']
    displays = json.load(open(displays_path))['displays']
    regions, notes, missing = {}, collections.defaultdict(list), {}

    def finish(pg, quads, kind, clip=(None, None)):
        """Pad and snap one page's quads (points); a display's box stays between its markers."""
        H = D.pages[pg - 1][1]
        qs = []
        for i, (x0, y0, x1, y1) in enumerate(quads):
            ws = [w for w in D.words(pg, y0 - 0.1, y1 + 0.1) if x0 - 0.5 <= (w[1] + w[3]) / 2 <= x1 + 0.5]
            # an edge at a marker (inside a line) is padded by half a point, to stay clear of the
            # neighbouring step on that line; an edge at the margin takes any ink beyond it
            px0 = px1 = PAD
            if x0 <= D.left + 0.5:
                x0 = min([D.left] + [w[1] for w in ws])
            else:
                px0 = 0.5
            if x1 >= D.right - 0.5:
                x1 = max([D.right] + [w[3] for w in ws])
            else:
                px1 = 0.5
            if clip[0] is not None:
                y0 = max(y0, clip[0])
            if clip[1] is not None:
                y1 = min(y1, clip[1])
            top = y0 - PAD if i == 0 else y0
            bot = y1 + PAD if i == len(quads) - 1 else y1
            if i == 0:
                top = ink.snap(pg, max(0.0, top), x0 - px0, x1 + px1, -1, hi=y0)
            if i == len(quads) - 1:
                bot = ink.snap(pg, min(H, bot), x0 - px0, x1 + px1, 1, lo=y1)
            qs.append([x0 - px0, top, x1 + px1, bot])
        return dict(page=pg, kind=kind, _pt=qs)

    def display_regions(rid, key, env):
        spans, nn = D.display(key, multline=env == 'multline*')
        notes[rid] += nn
        if spans is None:
            missing[rid] = '; '.join(nn)
            return
        regs = []
        for pg, lo, hi in spans:
            ws = D.words(pg, lo, hi)
            if not ws:
                continue
            regs.append(finish(pg, [[D.left, min(w[2] for w in ws), D.right, max(w[4] for w in ws)]], 'display',
                               clip=(lo, hi)))
        if regs:
            regions[rid] = regs
        else:
            missing[rid] = 'no ink between its markers'

    for d in displays:
        display_regions(d['id'], d['key'], d['env'])
    for s in steps:
        rid = s['id']
        if s['kind'] == 'display':
            display_regions(rid, s['key'], s['env'])
            continue
        a, b = s['markers']
        if a not in D.marks or b not in D.marks:
            missing[rid] = 'no marker'
            continue
        k = s['key']
        regions[rid] = [finish(pg, quads, 'prose') for pg, quads in D.prose(a, b, a == f'{k}:s', b == f'{k}:e')]

    # overlaps.  (1) Against the committed regions of numbered displays (data/regions.json), which
    # stay as they are: a new box that touches one gives way to it.  (2) Between two new boxes
    # (padding, font boxes taller than the ink): both are cut at the midpoint of the overlap.
    # Boxes nest only where a display sits inside a statement's box, which is not compared.
    old = json.load(open(items_regions_path))['items']
    kinds = {it['id']: it['kind'] for it in json.load(open(items_path))['items']}
    fixed = collections.defaultdict(list)
    for iid, regs in old.items():
        if kinds.get(iid) != 'equation':
            continue
        for r in regs:
            W, H = D.pages[r['page'] - 1][:2]
            x, y, w, h = r['rect']
            fixed[r['page']].append((iid, [x * W, y * H, (x + w) * W, (y + h) * H]))
    gave_way, cuts, big, nested = [], [], [], []
    for rid, regs in regions.items():
        for r in regs:
            for iid, f in fixed[r['page']]:
                for q in r['_pt']:
                    ov = overlap(q, f)
                    if ov <= 0:
                        continue
                    if (q[1] + q[3]) / 2 < (f[1] + f[3]) / 2:
                        q[3] = f[1] - 0.02
                    else:
                        q[1] = f[3] + 0.02
                    gave_way.append((rid, iid, r['page'], round(ov, 2)))
    on_page = collections.defaultdict(list)
    kind_of = {}
    for rid, regs in regions.items():
        for r in regs:
            for q in r['_pt']:
                on_page[r['page']].append((rid, q))
                kind_of[id(q)] = r['kind']
            kind_of[rid] = r['kind']
    for pg, lst in on_page.items():
        lst.sort(key=lambda t: t[1][1])
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                (a, qa), (b, qb) = lst[i], lst[j]
                if a == b:
                    continue
                ov = overlap(qa, qb)
                if ov <= 0:
                    continue
                upper, lower = (qa, qb) if qa[1] <= qb[1] else (qb, qa)
                if not (upper[1] < lower[1] and upper[3] < lower[3]):
                    nested.append((a, b, pg, round(ov, 2)))
                    continue
                # cut in the gap between the word boxes of the two, so that each keeps its words
                # whole; where the word boxes themselves overlap, at the middle of that overlap
                wu = [w for w in D.pages[pg - 1][2] if inq(w, upper)]
                wl = [w for w in D.pages[pg - 1][2] if inq(w, lower)]
                ub = max([w[4] for w in wu] or [upper[3] - PAD])
                lt = min([w[2] for w in wl] or [lower[1] + PAD])
                mid = (ub + lt) / 2
                if ub > lt and kind_of[a] != kind_of[b]:
                    # a text line touching a display: the text keeps its words whole
                    mid = ub if kind_of[id(upper)] == 'prose' else lt
                mid = min(max(mid, lower[1]), upper[3])
                # off ink, if a blank row is within 3 points
                x0, x1 = max(upper[0], lower[0]), min(upper[2], lower[2])
                step = 72 / DPI / 2
                for n in range(int(3 / step) + 1):
                    hit = next((z for z in (mid + n * step, mid - n * step) if lower[1] - 3 <= z <= upper[3] + 3
                                and ink.blank(pg, z, x0, x1)), None)
                    if hit is not None:
                        mid = hit
                        break
                upper[3], lower[1] = mid - 0.01, mid + 0.01
                cuts.append((a, b, pg, round(ov, 2)))
                if ub > lt:
                    big.append((a, b, pg, round(ub - lt, 2)))
    # a later cut can move an edge past an earlier neighbour: what overlaps now is cut at the
    # midpoint, without snapping
    for pg, lst in on_page.items():
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                (a, qa), (b, qb) = lst[i], lst[j]
                if a != b and overlap(qa, qb) > 0:
                    upper, lower = (qa, qb) if qa[1] <= qb[1] else (qb, qa)
                    if upper[1] < lower[1] and upper[3] < lower[3]:
                        mid = (lower[1] + upper[3]) / 2
                        upper[3], lower[1] = mid - 0.01, mid + 0.01
    for rid, regs in regions.items():
        for r in regs:
            r['_pt'] = [q for q in r['_pt'] if q[3] - q[1] > 0.5]

    # checks.  Words of the committed PDF in each region's quads
    words_in = {}
    for rid, regs in regions.items():
        got = []
        for r in regs:
            pg = r['page']
            for w in D.pages[pg - 1][2]:
                cx, cy = (w[1] + w[3]) / 2, (w[2] + w[4]) / 2
                if any(q[0] <= cx <= q[2] and q[1] <= cy <= q[3] for q in r['_pt']):
                    got.append((pg, w[1], w[2], w[0]))
        words_in[rid] = got
    owner = collections.defaultdict(list)
    for rid, got in words_in.items():
        for w in got:
            owner[w].append(rid)
    shared_pairs = collections.Counter()
    for w, rids in owner.items():
        rids = sorted(rids)
        for i in range(len(rids)):
            for j in range(i + 1, len(rids)):
                shared_pairs[(rids[i], rids[j])] += 1
    proof_of = {s['id']: (s['item'], s['proof_line']) for s in steps}
    overl = []
    for pg, lst in on_page.items():
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                (a, qa), (b, qb) = lst[i], lst[j]
                if a != b and overlap(qa, qb) > 0:
                    overl.append((a, b, pg, round(overlap(qa, qb), 2)))
    in_proof_overl = [o for o in overl if o[0] in proof_of and o[1] in proof_of and proof_of[o[0]] == proof_of[o[1]]]
    empty = [rid for rid, regs in regions.items() for r in regs
             if not any(w[0] == r['page'] for w in words_in[rid]) and r['_pt']]
    for regs in regions.values():
        regs[:] = [r for r in regs if r['_pt']]

    def check_step(s):
        regs = regions[s['id']]
        if s['kind'] == 'display':
            return check_display(s['id'], s['latex'], regs)
        fw, lw = edge_words(s['latex'])
        texts = [crop_text(pdf, r['page'], q) for r in regs for q in r['_pt']]
        allt = norm(''.join(t.replace('-\n', '') for t in texts))
        # its first two printed lines (a step may start with one word at the end of a line), and
        # its last two
        r0, r1 = regs[0], regs[-1]
        qs = r0['_pt']
        if len(qs) > 1 and qs[0][3] - qs[0][1] < 20:
            parts = [qs[0], [qs[1][0], qs[1][1], qs[1][2], min(qs[1][3], qs[1][1] + 15)]]
        else:
            parts = [[qs[0][0], qs[0][1], qs[0][2], min(qs[0][3], qs[0][1] + 29)]]
        first_line = norm(''.join(crop_text(pdf, r0['page'], q) for q in parts).replace('-\n', ''))
        qs = r1['_pt']
        if len(qs) > 1 and qs[-1][3] - qs[-1][1] < 20:
            parts = [[qs[-2][0], max(qs[-2][1], qs[-2][3] - 15), qs[-2][2], qs[-2][3]], qs[-1]]
        else:
            parts = [[qs[-1][0], max(qs[-1][1], qs[-1][3] - 29), qs[-1][2], qs[-1][3]]]
        last_line = norm(''.join(crop_text(pdf, r1['page'], q) for q in parts).replace('-\n', ''))
        bad = []
        if fw is None:
            bad.append('no word')
        elif norm(fw) not in allt or norm(lw) not in allt:
            bad.append(f'words {fw!r}, {lw!r} not in the crop')
        # the step's edges, math normalized: its first and last EDGE letters or digits, math
        # included, in the crops of its first and last lines
        t = norm(strip_latex(s['latex']))
        if coverage(t[:EDGE], first_line) < 1:
            bad.append(f'first {t[:EDGE]!r} not in its first line')
        if coverage(t[-EDGE:], last_line) < 1:
            bad.append(f'last {t[-EDGE:]!r} not in its last line')
        return s['id'], bad

    def check_display(rid, latex, regs):
        words, chars = display_tokens(latex)
        text = ''.join(crop_text(pdf, r['page'], q) for r in regs for q in r['_pt'])
        flat = text.replace('-\n', '').replace(' ', '').replace('\n', '')
        bad = [f'token {w!r}' for w in words if w not in flat]
        cov = coverage(chars, norm(text))
        if cov < DISPLAY_COVER:
            bad.append(f'coverage {cov:.2f}')
        return rid, bad, cov
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        res = list(ex.map(check_step, [s for s in steps if s['id'] in regions]))
        dres = list(ex.map(lambda d: check_display(d['id'], d['latex'], regions[d['id']]),
                           [d for d in displays if d['id'] in regions]))
    fails = {r[0]: r[1] for r in res if r[1]}
    dfails = {r[0]: r[1] for r in dres if r[1]}
    covs = {r[0]: round(r[2], 3) for r in res + dres if len(r) == 3}

    # normalized output: rect = bounding box of the quads; quads only where the box is not a
    # full-width rectangle
    for rid, regs in regions.items():
        for k, r in enumerate(regs):
            W, H = D.pages[r['page'] - 1][:2]
            qs = r.pop('_pt')
            X0, Y0 = min(q[0] for q in qs), min(q[1] for q in qs)
            X1, Y1 = max(q[2] for q in qs), max(q[3] for q in qs)
            r['rect'] = [round(X0 / W, 5), round(Y0 / H, 5), round((X1 - X0) / W, 5), round((Y1 - Y0) / H, 5)]
            if len(qs) > 1:
                r['quads'] = [[round(v / (W if j % 2 == 0 else H), 5)
                               for j, v in enumerate((q[0], q[1], q[2], q[1], q[2], q[3], q[0], q[3]))] for q in qs]
            r['continuation'] = k > 0
    sha = hashlib.sha256(open(pdf, 'rb').read()).hexdigest()
    layout = json.load(open(os.path.join(build, 'layoutcheck.json')))
    checks = dict(regions=sum(len(v) for v in regions.values()), displays=len(displays), steps=len(steps),
                  with_regions=len(regions), missing=missing, display_token_failures=dfails,
                  step_word_failures=fails, words_in_two_regions=[list(k) + [v] for k, v in sorted(shared_pairs.items())],
                  overlaps_left=overl, step_overlaps_in_proof=in_proof_overl, regions_without_words=empty,
                  multi_page=sorted(rid for rid, regs in regions.items() if len(regs) > 1),
                  cut_pairs=len(cuts), nested_quads_not_cut=nested, word_boxes_overlap_at_cut=big, gave_way_to_numbered=gave_way,
                  min_display_coverage=min(covs.values()) if covs else None)
    out = dict(pdf=dict(url=f'https://raw.githubusercontent.com/scottnarmstrong/yang-mills-informalization/{commit}/manuscript/main.pdf',
                        sha256=sha, bytes=os.path.getsize(pdf), pages=len(D.pages)),
               coordinates='fractions of the displayed page (MediaBox, no rotation), from the top left: rect [x, y, w, h], '
                           'the bounding box; quads [x0, y0, x1, y1, x2, y2, x3, y3] (top left, top right, bottom '
                           'right, bottom left) where a step starts or ends inside a line',
               method='pdfsavepos markers of a rebuild whose words sit where the committed PDF prints them '
                      '(layoutcheck), boxes fitted to the committed PDF\'s word boxes',
               layout_check=dict(pages=layout['pages'], mismatched_pages=layout['mismatched_pages'],
                                 words_compared=layout['words_compared']),
               regions=regions, notes={k: v for k, v in notes.items() if v}, display_coverage=covs, checks=checks)
    json.dump(out, open(out_path, 'w'), indent=1, ensure_ascii=False)
    summary = {k: (v if not isinstance(v, (dict, list)) else len(v)) for k, v in checks.items()}
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    if sys.argv[1] == 'lines':
        lines_mode(*sys.argv[2:6])
    else:
        regions_mode(*sys.argv[2:10])
