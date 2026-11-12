"""Displays outside proofs and proof steps of [M], from its LaTeX.

New code; the source stream and its comment rule are items.py's.  Reads `main.tex` and its inputs
in document order and lists:

- every unnumbered display (`equation*`, `align*`, `gather*`, `multline*`, `\\[...\\]`, `$$...$$`)
  that is not inside a proof: an item of kind `display`, id `Section <s> display <n>`, numbered in
  order within its section;
- every `proof` environment, cut into steps in order: an unnumbered display is one step; the
  prose between displays is cut at paragraph breaks (a blank line, `\\par`), at list items and at
  the edges of lists, and each nonempty piece is one step.  A numbered display is an item of its
  own (items.json) and no step.  A piece with no letter and no math (a lone "." after a
  display) is no step; it is counted.

A proof belongs to the item named first in its optional argument (`\\ref`, `\\eqref`), else to
the last theorem-like statement before it (items.py's rule).  Every prose step lists its
sentences: boundaries are ".", "?" or "!" (closing `)` or `''` included) at brace depth 0 outside
math, followed by space and a capital letter, a digit, `$`, `(` or a command, and not ending an
abbreviation.  `split.py` groups the sentences of long paragraphs into steps; `marks.py` places a
position marker at every step edge and sentence boundary.

Usage: python3 -I segment.py <manuscript dir> <items json> <source commit> <out json>
"""
import bisect
import json
import os
import re
import sys

UNNUM = {'equation*', 'align*', 'gather*', 'multline*', 'flalign*', 'alignat*'}
NUM = {'equation', 'align', 'gather', 'multline', 'flalign', 'alignat'}
THM = {'maintheorem', 'theorem', 'proposition', 'lemma', 'corollary', 'definition', 'remark', 'principal'}
LISTS = {'enumerate', 'itemize', 'description'}
ABBREV = {'e.g', 'i.e', 'cf', 'resp', 'etc', 'vs', 'Eq', 'Eqs', 'Fig', 'Sec', 'Thm', 'Prop', 'Lem', 'Def', 'No', 'al',
          'Ch', 'p', 'pp'}


def strip_comment(line):
    m = re.search(r'(?<!\\)%', line)
    return line[:m.start()] if m else line


def stream(root, name, out):
    rel = name if name.endswith('.tex') else name + '.tex'
    for k, raw in enumerate(open(os.path.join(root, rel), encoding='utf-8').read().split('\n'), 1):
        t = strip_comment(raw)
        m = re.fullmatch(r'\s*\\input\{([^}]*)\}\s*', t)
        if m and m.group(1) != 'macros':
            stream(root, m.group(1), out)
        else:
            out.append((rel, k, t))


def balanced(s, i, open_='{', close='}'):
    depth, j = 0, i
    while j < len(s):
        c = s[j]
        if c == '\\':
            j += 2
            continue
        if c == open_:
            depth += 1
        elif c == close:
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    raise ValueError(f'unbalanced at {i}')


TOKEN = re.compile(r'\\\\|\\(begin|end)\{([A-Za-z*]+)\}|\\section\*?(?=[\[{])|\\\[|\\\]|\$\$|'
                   r'\n[ \t]*\n\s*|\\par\b|\\item\b')


def math_spans(s):
    """Inline math spans of a prose piece: $...$ and \\(...\\), as (start, end)."""
    out, i = [], 0
    while i < len(s):
        if s[i] == '\\':
            if s[i + 1:i + 2] == '(':
                j = s.find('\\)', i + 2)
                j = len(s) if j < 0 else j + 2
                out.append((i, j))
                i = j
                continue
            i += 2
            continue
        if s[i] == '$':
            j = i + 1
            while j < len(s) and s[j] != '$':
                j += 2 if s[j] == '\\' else 1
            out.append((i, j + 1))
            i = j + 1
            continue
        i += 1
    return out


def sentences(s):
    """Sentence spans [(start, end)] of a prose piece (end after the closing punctuation)."""
    ms = math_spans(s)
    inmath = bytearray(len(s) + 1)
    for a, b in ms:
        for q in range(a, min(b, len(s))):
            inmath[q] = 1
    depth, cuts, i = 0, [], 0
    while i < len(s):
        c = s[i]
        if c == '\\':
            i += 2
            continue
        if inmath[i]:
            i += 1
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        elif c in '.?!' and depth == 0:
            j = i + 1
            while s[j:j + 2] == "''" or s[j:j + 1] == ')':
                j += 2 if s[j:j + 2] == "''" else 1
            m = re.match(r'\s+', s[j:])
            if m and j + m.end() < len(s) and re.match(r"[A-Z0-9$(\\`]", s[j + m.end()]):
                w = re.search(r'([A-Za-z.]+)$', s[:i])
                word = w.group(1) if w else ''
                if word not in ABBREV and not re.fullmatch(r'[A-Z]', word) and s[j + m.end():j + m.end() + 2] != '\\\\':
                    cuts.append((j, j + m.end()))
        i += 1
    spans, start = [], 0
    for e, nxt in cuts:
        spans.append((start, e))
        start = nxt
    spans.append((start, len(s.rstrip())))
    # a piece with no text of its own (a trailing \label) joins the sentence before it
    out = []
    for a, b in spans:
        if out and not contentful(s[a:b]):
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out


def contentful(s):
    t = re.sub(r'\\(qedhere|noindent|label\{[^}]*\}|samepage|nopagebreak|medskip|smallskip|bigskip)', '', s)
    return bool(re.search(r'[A-Za-z0-9$]', t))


def plain(num):
    return re.sub(r'\\[A-Za-z]+|[${}_^ ]', '', num)


def main():
    root, items_path, commit, out_path = sys.argv[1:5]
    items = json.load(open(items_path))['items']
    lines = []
    stream(root, 'main', lines)
    text, starts = '', []
    for f, k, t in lines:
        starts.append(len(text))
        text += t + '\n'

    def where(pos):
        i = bisect.bisect_right(starts, pos) - 1
        return dict(file=lines[i][0], line=lines[i][1], col=pos - starts[i])

    # global position of every item (file, line) -> its first position, for "last statement before"
    line_pos = {(f, k): starts[i] for i, (f, k, _) in enumerate(lines)}
    by_label = {l: it['id'] for it in items for l in it['labels']}
    stmt_pos = sorted((line_pos[(it['file'], it['line'])], it['id']) for it in items if it['kind'] != 'equation')

    # pass 1: environments, sections, displays, proofs
    sec = None
    stack = []
    displays, proofs, numbered = [], [], []   # numbered: (start, end) of numbered display environments
    boundaries = []                            # (pos, end, kind) prose breaks
    nsec = 0
    pos_section = []                           # (pos, section number, title)
    for m in TOKEN.finditer(text):
        g = m.group(0)
        if g == '\\\\':
            continue
        if g.startswith('\\section'):
            j = m.end()
            if text[j] == '[':
                j = balanced(text, j, '[', ']')
            k = balanced(text, j)
            if not g.endswith('*'):
                nsec += 1
                pos_section.append((m.start(), str(nsec), text[j + 1:k - 1]))
            continue
        if m.group(1) == 'begin' or g in ('\\[', '$$') and not (g == '$$' and stack and stack[-1]['env'] == '$$'):
            env = m.group(2) if m.group(1) else g
            if any(e['env'] in UNNUM | NUM | {'\\[', '$$'} for e in stack):
                stack.append(dict(env=env, pos=m.start(), inner=True))
                continue
            e = dict(env=env, pos=m.start(), body=m.end())
            if env == 'proof':
                j = m.end()
                opt = None
                if text[j:j + 1] == '[':
                    k = balanced(text, j, '[', ']')
                    opt = text[j + 1:k - 1]
                    e['body'] = k
                e['opt'] = opt
            if env in LISTS:
                j = m.end()
                if text[j:j + 1] == '[':
                    j = balanced(text, j, '[', ']')
                boundaries.append((m.start(), j, 'list'))
            stack.append(e)
            continue
        if m.group(1) == 'end' or g in ('\\]', '$$'):
            env = m.group(2) if m.group(1) else ('\\[' if g == '\\]' else '$$')
            if not stack or stack[-1]['env'] != env:
                sys.exit(f'unbalanced {g} {env} at {where(m.start())}: open {[s["env"] for s in stack]}')
            e = stack.pop()
            if e.get('inner'):
                continue
            e['end'] = m.end()
            e['body_end'] = m.start()
            ctx = next((s for s in reversed(stack) if s['env'] == 'proof' or s['env'] in THM), None)
            if env in UNNUM or env in ('\\[', '$$'):
                e['ctx'] = ctx
                displays.append(e)
            elif env in NUM:
                numbered.append(e)
            elif env == 'proof':
                e['nested_in'] = ctx['env'] if ctx else None
                proofs.append(e)
            if env in LISTS:
                boundaries.append((m.start(), m.end(), 'list'))
            continue
        if g == '\\item':
            j = m.end()
            if text[j:j + 1] == '[':
                j = balanced(text, j, '[', ']')
            boundaries.append((m.start(), j, 'item'))
            continue
        boundaries.append((m.start(), m.end(), 'par'))
    if stack:
        sys.exit(f'open at end: {[s["env"] for s in stack]}')

    def section_at(pos):
        i = bisect.bisect_right([p for p, _, _ in pos_section], pos) - 1
        return pos_section[i][1:] if i >= 0 else (None, None)

    def latex(a, b):
        return text[a:b]

    # displays outside proofs
    out_displays, per_sec = [], {}
    for e in displays:
        if e['ctx'] and e['ctx']['env'] == 'proof':
            continue
        s, title = section_at(e['pos'])
        per_sec[s] = per_sec.get(s, 0) + 1
        a, b = where(e['pos']), where(e['end'] - 1)
        ctx = e['ctx']
        enc = None
        if ctx:
            p = line_pos[(where(ctx['pos'])['file'], where(ctx['pos'])['line'])]
            enc = next(i for q, i in stmt_pos if q == p)
        body = re.sub(r'\\label\{[^}]*\}', '', latex(e['body'], e['body_end'])).strip('\n')
        out_displays.append(dict(id=f'Section {s} display {per_sec[s]}', kind='display', env=e['env'],
                                 section=dict(number=s, title=title), context='statement' if ctx else 'text',
                                 enclosing=enc, file=a['file'], line=a['line'], end_line=b['line'],
                                 start=a, end=where(e['end']), latex=body, key=f'D{len(out_displays) + 1}'))

    # proofs and their steps
    out_proofs, steps = [], []
    dropped = []
    nproof_item = {}
    for pr in sorted(proofs, key=lambda e: e['pos']):
        refs = re.findall(r'\\(?:ref|eqref)\{([^}]*)\}', pr['opt'] or '')
        tgt = [by_label[r] for r in refs if r in by_label]
        if tgt:
            item = tgt[0]
            how = 'optional argument'
        else:
            prev = [i for q, i in stmt_pos if q < pr['pos']]
            item = prev[-1]
            how = 'last statement before the proof'
        a, b = pr['body'], pr['body_end']
        blocks = []          # (start, end, kind, extra)
        for e in displays:
            if a <= e['pos'] < b:
                blocks.append((e['pos'], e['end'], 'display', e))
        for e in numbered:
            if a <= e['pos'] < b:
                blocks.append((e['pos'], e['end'], 'numbered', e))
        for p, q, k in boundaries:
            if a <= p < b and not any(x <= p < y for x, y, kk, _ in blocks if kk != 'break'):
                blocks.append((p, q, 'break', k))
        blocks.sort()
        pieces, cur = [], a
        for p, q, k, e in blocks:
            if p < cur:
                continue
            pieces.append(('prose', cur, p))
            if k != 'break':
                pieces.append((k, p, q, e))
            cur = q
        pieces.append(('prose', cur, b))
        sec_num, sec_title = section_at(pr['pos'])
        nproof_item[item] = nproof_item.get(item, 0) + 1
        prec = dict(item=item, item_by=how, proof_of=pr['opt'], file=where(pr['pos'])['file'],
                    line=where(pr['pos'])['line'], end_line=where(pr['end'] - 1)['line'],
                    section=dict(number=sec_num, title=sec_title), proof_index=nproof_item[item],
                    steps=[], numbered_displays=[])
        for pc in pieces:
            if pc[0] == 'prose':
                s0, s1 = pc[1], pc[2]
                seg = text[s0:s1]
                lead = len(seg) - len(seg.lstrip())
                seg = seg.strip()
                if not seg:
                    continue
                s0 += lead
                s1 = s0 + len(seg)
                if not contentful(seg):
                    dropped.append(dict(item=item, file=where(s0)['file'], line=where(s0)['line'], latex=seg))
                    continue
                sents = [dict(start=where(s0 + x), end=where(s0 + y), latex=seg[x:y]) for x, y in sentences(seg)]
                steps.append(dict(item=item, kind='prose', file=where(s0)['file'], line=where(s0)['line'],
                                  end_line=where(s1 - 1)['line'], start=where(s0), end=where(s1), latex=seg,
                                  sentences=sents, section=dict(number=sec_num, title=sec_title),
                                  proof_line=prec['line']))
            elif pc[0] == 'display':
                e = pc[3]
                body = re.sub(r'\\label\{[^}]*\}', '', latex(e['body'], e['body_end'])).strip('\n')
                steps.append(dict(item=item, kind='display', env=e['env'], file=where(e['pos'])['file'],
                                  line=where(e['pos'])['line'], end_line=where(e['end'] - 1)['line'],
                                  start=where(e['pos']), end=where(e['end']), latex=body,
                                  section=dict(number=sec_num, title=sec_title), proof_line=prec['line']))
            else:
                e = pc[3]
                f, l0 = where(e['pos'])['file'], where(e['pos'])['line']
                ids = [it['id'] for it in items if it['kind'] == 'equation' and it['file'] == f and it['env_lines'][0] == l0]
                prec['numbered_displays'] += ids
                steps.append(dict(item=item, kind='numbered', items=ids, file=f, line=l0, proof_line=prec['line']))
        out_proofs.append(prec)

    # number the steps of each item, in order of its proofs; numbered displays are no step
    n = {}
    final = []
    for s in steps:
        if s['kind'] == 'numbered':
            continue
        n[s['item']] = n.get(s['item'], 0) + 1
        s['step'] = n[s['item']]
        s['paragraph'] = f'{s["item"]} paragraph {s["step"]}' if s['kind'] == 'prose' else None
        final.append(s)
    for pr in out_proofs:
        pr['steps'] = [s['step'] for s in final if s['item'] == pr['item'] and s['proof_line'] == pr['line']]
    for k, s in enumerate(final, 1):
        s['key'] = f'P{k}'

    # prose outside proofs (out of scope; counted)
    in_proof = [(p['body'], p['body_end']) for p in proofs]
    blocked = sorted([(e['pos'], e['end']) for e in displays + numbered] + in_proof)
    paras = []
    cuts = sorted([(p, q) for p, q, k in boundaries] + blocked)
    cur = text.index('\\begin{document}')
    for p, q in cuts + [(len(text), len(text))]:
        if p >= cur:
            seg = text[cur:p]
            if not any(x <= cur < y for x, y in blocked):
                t = re.sub(r'\\(begin|end)\{[^}]*\}|\\(section|subsection|part|label|input)\*?(\[[^]]*\])?\{[^}]*\}', '', seg)
                if re.search(r'[A-Za-z]{3}', re.sub(r'\$[^$]*\$|\\[A-Za-z]+', '', t)):
                    paras.append((cur, len(re.findall(r'\S+', t))))
        cur = max(cur, q)
    prose_out = {}
    for p, w in paras:
        s, _ = section_at(p)
        d = prose_out.setdefault(s, dict(paragraphs=0, words=0))
        d['paragraphs'] += 1
        d['words'] += w

    out = dict(source=dict(repository='https://github.com/scottnarmstrong/yang-mills-informalization', commit=commit,
                           directory='manuscript'),
               displays=out_displays, proofs=out_proofs, steps=final, dropped_pieces=dropped,
               prose_outside_proofs=prose_out)
    json.dump(out, open(out_path, 'w'), indent=1, ensure_ascii=False)
    print(len(out_displays), 'displays outside proofs;', len(out_proofs), 'proofs;', len(final), 'steps',
          sum(s['kind'] == 'display' for s in final), 'display', sum(s['kind'] == 'prose' for s in final), 'prose;',
          len(dropped), 'dropped pieces')


main()
