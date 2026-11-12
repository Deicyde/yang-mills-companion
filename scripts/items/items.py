"""The items of [M]: every theorem-like statement and every numbered display, from its LaTeX.

New code.  Reads `main.tex` and the files it inputs, in document order, and simulates [M]'s
counters: theorem-like environments share the `theorem` counter numbered within sections
(`maintheorem` is A, B, ...), equations are numbered within sections, `\\tag{x}` prints x and steps
no counter.  A numbered row of `align` (or `multline`, `gather`, ...) is one display item; it covers
the unnumbered rows before it, back to the previous numbered row, and the last numbered row of an
environment also covers the unnumbered rows after it.  Labels are assigned to the innermost item
around them; numbers are checked against the `.aux` of a build when one is given.

A named principal statement is a theorem-like item whose name opens with a tag of the
introduction's table of principal results (`tab:principal-results`): "RG. One step" has tag RG.
The environment `principal` (`\\principalname`) is defined in `main.tex` and counted if used.

Usage: python3 -I items.py <manuscript dir> <source commit> <out json> [<aux file>]
"""
import json
import os
import re
import sys

THM = {'maintheorem': 'theorem', 'theorem': 'theorem', 'proposition': 'proposition', 'lemma': 'lemma',
       'corollary': 'corollary', 'definition': 'definition', 'remark': 'remark', 'principal': 'principal'}
PRINTED = {'maintheorem': 'Theorem', 'theorem': 'Theorem', 'proposition': 'Proposition', 'lemma': 'Lemma',
           'corollary': 'Corollary', 'definition': 'Definition', 'remark': 'Remark', 'principal': ''}
DISPLAY = {'equation'}
MULTI = {'align', 'gather', 'flalign', 'alignat', 'multline'}
NESTED = {'aligned', 'cases', 'split', 'pmatrix', 'array', 'gathered', 'alignedat', 'matrix', 'bmatrix', 'vmatrix',
          'smallmatrix', 'subarray'}


def strip_comment(line):
    m = re.search(r'(?<!\\)%', line)
    return line[:m.start()] if m else line


def stream(root, name, out):
    """Append (file, line number, text without comment) for `name` and its inputs, in order."""
    rel = name if name.endswith('.tex') else name + '.tex'
    for k, raw in enumerate(open(os.path.join(root, rel), encoding='utf-8').read().split('\n'), 1):
        t = strip_comment(raw)
        m = re.fullmatch(r'\s*\\input\{([^}]*)\}\s*', t)
        if m and m.group(1) != 'macros':
            stream(root, m.group(1), out)
        else:
            out.append((rel, k, t))


def balanced(s, i, open_='{', close='}'):
    """s[i] is `open_`; return the index after the matching `close`."""
    depth = 0
    j = i
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


TOKEN = re.compile(r'\\(begin|end)\{([A-Za-z*]+)\}|\\(section|subsection|subsubsection|part)\*?(?=[\[{])|'
                   r'\\label\{([^}]*)\}|\\\\|\\(notag|nonumber)\b|\\tag\*?(?=\{)')


def main():
    root, commit, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    aux = sys.argv[4] if len(sys.argv) > 4 else None
    lines = []
    stream(root, 'main', lines)
    text = ''
    starts = []
    for f, k, t in lines:
        starts.append(len(text))
        text += t + '\n'
    import bisect

    def where(pos):
        i = bisect.bisect_right(starts, pos) - 1
        return lines[i][0], lines[i][1]

    sec = {'number': None, 'title': None, 'label': None}
    subsec = None
    nsec = nthm = neq = nmain = 0
    items = []
    stack = []      # open environments: dict(env, pos, item or rows)
    last_thm = None
    labels = []     # (label, pos)
    pending_label_target = []
    for m in TOKEN.finditer(text):
        if stack and stack[-1].get('verbatim'):
            pass
        if m.group(1) == 'begin':
            env = m.group(2)
            e = dict(env=env, pos=m.start(), body=m.end())
            if env in THM:
                j = m.end()
                name = None
                if text[j:j + 1] == '[':
                    k = balanced(text, j, '[', ']')
                    name = text[j + 1:k - 1].strip()
                    e['body'] = k
                if env == 'maintheorem':
                    nmain += 1
                    num = chr(64 + nmain)
                elif env == 'principal':
                    num = None
                else:
                    nthm += 1
                    num = f'{sec["number"]}.{nthm}'
                it = dict(kind=THM[env], env=env, number=num, name=name, labels=[])
                e['item'] = it
            elif env == 'proof':
                j = m.end()
                opt = None
                if text[j:j + 1] == '[':
                    k = balanced(text, j, '[', ']')
                    opt = text[j + 1:k - 1]
                e['proves'] = opt
                e['last_thm'] = last_thm
            elif env in DISPLAY or env in MULTI:
                e['rows'] = [dict(start=m.end(), notag=False, tag=None, labels=[])]
            stack.append(e)
        elif m.group(1) == 'end':
            env = m.group(2)
            if not stack or stack[-1]['env'] != env:
                sys.exit(f'unbalanced \\end{{{env}}} at {where(m.start())}: open {[s["env"] for s in stack]}')
            e = stack.pop()
            if 'item' in e:
                it = e['item']
                f0, l0 = where(e['pos'])
                f1, l1 = where(m.start())
                it.update(file=f0, line=l0, end_line=l1, section=dict(sec), subsection=subsec,
                          statement=re.sub(r'\\label\{[^}]*\}', '', text[e['body']:m.start()]).strip('\n'),
                          _pos=(e['pos'], m.end()))
                it['enclosing'] = enclosing(stack)
                items.append(it)
                if it['kind'] != 'principal':
                    last_thm = it
            elif 'rows' in e:
                rows = e['rows']
                rows[-1]['end'] = m.start()
                if len(rows) > 1 and not text[rows[-1]['start']:rows[-1]['end']].strip():
                    rows[-1]['notag'] = True       # an empty row after a final \\
                if env in ('multline',):
                    rows = [dict(start=rows[0]['start'], end=rows[-1]['end'], notag=any(r['notag'] for r in rows),
                                 tag=next((r['tag'] for r in rows if r['tag']), None),
                                 labels=sum((r['labels'] for r in rows), []))]
                numbered = [i for i, r in enumerate(rows) if not r['notag']]
                groups = []
                prev = 0
                for n, i in enumerate(numbered):
                    hi = len(rows) - 1 if n == len(numbered) - 1 else i
                    groups.append((prev, i, hi))
                    prev = hi + 1
                f0, l0 = where(e['pos'])
                f1, l1 = where(m.start())
                for lo, i, hi in groups:
                    r = rows[i]
                    if r['tag'] is None:
                        neq += 1
                        num = f'{sec["number"]}.{neq}'
                    else:
                        num = r['tag']
                    body = '\\\\\n'.join(text[rows[q]['start']:rows[q]['end']].strip('\n') for q in range(lo, hi + 1))
                    body = re.sub(r'\\label\{[^}]*\}|\\notag|\\nonumber', '', body)
                    body = re.sub(r'\\tag\*?\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', '', body).strip()
                    labs = sum((rows[q]['labels'] for q in range(lo, hi + 1)), [])
                    gl0 = where(rows[lo]['start'])[1] if lo else l0
                    gl1 = where(rows[hi]['end'])[1] if hi < len(rows) - 1 else l1
                    it = dict(kind='equation', env=env, number=num, name=None, labels=labs,
                              file=f0, line=gl0, end_line=gl1, env_lines=[l0, l1], rows=[lo, hi, len(rows)],
                              tag_row=i, custom_tag=r['tag'] is not None,
                              section=dict(sec), subsection=subsec, statement=body, _pos=(e['pos'], m.end()))
                    it['enclosing'] = enclosing(stack)
                    items.append(it)
        elif m.group(3):
            j = m.end()
            star = text[m.start():j].endswith('*')
            if text[j] == '[':
                j = balanced(text, j, '[', ']')
            k = balanced(text, j)
            title = text[j + 1:k - 1]
            lab = re.match(r'\s*\\label\{([^}]*)\}', text[k:])
            if m.group(3) == 'section' and not star:
                nsec += 1
                nthm = neq = 0
                sec = dict(number=str(nsec), title=title, label=lab.group(1) if lab else None)
                subsec = None
            elif m.group(3) == 'subsection' and not star:
                subsec = dict(title=title, label=lab.group(1) if lab else None)
        elif m.group(4) is not None:
            target = innermost(stack)
            if target is not None:
                target.append(m.group(4))
            labels.append((m.group(4), m.start()))
        elif m.group(0) == '\\\\':
            e = stack[-1] if stack else None
            if e and 'rows' in e and e['env'] != 'equation' and depth(text, e['body'], m.start()) == 0 and not any('rows' not in s and s['env'] in NESTED
                                                                         for s in stack[stack.index(e):]):
                e['rows'][-1]['end'] = m.start()
                e['rows'].append(dict(start=m.end(), notag=False, tag=None, labels=[]))
        elif m.group(5):
            e = display_of(stack)
            if e:
                e['rows'][-1]['notag'] = True
        elif m.group(0).startswith('\\tag'):
            e = display_of(stack)
            k = balanced(text, m.end())
            if e:
                e['rows'][-1]['tag'] = text[m.end() + 1:k - 1]

    intro = open(os.path.join(root, 'part1', '01-introduction.tex'), encoding='utf-8').read()
    table = intro[intro.index('tab:principal-results'):]
    table = table[:table.index('\\end{longtable}')]
    principal_tags = set(re.findall(r'^([A-Z]{2}) & ', table, re.M))

    # proof targets: the item named in the proof's optional argument, else the last statement before it
    by_label = {}
    for it in items:
        for l in it['labels']:
            by_label[l] = it
    for it in items:
        enc = it.pop('enclosing')
        it['enclosing'] = None
        it['context'] = 'text'
        if enc is None:
            continue
        kind, e = enc
        if kind == 'statement':
            it['context'] = 'statement'
            it['enclosing'] = item_id(e['item'])
        else:
            it['context'] = 'proof'
            refs = re.findall(r'\\(?:ref|eqref)\{([^}]*)\}', e['proves'] or '')
            tgt = [by_label[r] for r in refs if r in by_label]
            it['enclosing'] = item_id(tgt[0]) if tgt else (item_id(e['last_thm']) if e['last_thm'] else None)
            if e['proves']:
                it['proof_of'] = e['proves']
    seen = {}
    for it in items:
        it['id'] = item_id(it)
        if it['id'] in seen:
            sys.exit(f'duplicate id {it["id"]}')
        seen[it['id']] = it
        it['label'] = it['labels'][0] if it['labels'] else None
        it.pop('_pos')
        it['printed'] = printed(it)
        tag = re.match(r'([A-Z][A-Z0-9]*(?:--[A-Z0-9]+)?)\. ', it['name'] or '')
        it['tag'] = tag.group(1) if tag else None
        it['principal'] = bool(tag and tag.group(1) in principal_tags) or it['kind'] == 'principal'

    # cross-check numbers with the .aux of a build
    mism = []
    if aux:
        auxlab = {}
        for f in [aux] + [os.path.join(os.path.dirname(aux), p) for p in re.findall(r'\\@input\{([^}]*)\}', open(aux).read())]:
            for lab, num in re.findall(r'\\newlabel\{([^}]*)\}\{\{([^}]*)\}', open(f, encoding='latin-1').read()):
                auxlab[lab] = num
        for it in items:
            for l in it['labels']:
                n = auxlab.get(l)
                want = it['number']
                if it['custom_tag'] if it['kind'] == 'equation' else False:
                    continue
                if n != want:
                    mism.append((it['id'], l, n))
    kinds = {}
    for it in items:
        kinds[it['kind']] = kinds.get(it['kind'], 0) + 1
    order = ['id', 'kind', 'env', 'number', 'printed', 'name', 'tag', 'principal', 'label', 'labels', 'section', 'subsection', 'context', 'enclosing',
             'proof_of', 'file', 'line', 'end_line', 'env_lines', 'rows', 'tag_row', 'custom_tag', 'statement']
    items = [{k: it[k] for k in order if k in it} for it in items]
    out = dict(source=dict(repository='https://github.com/scottnarmstrong/yang-mills-informalization',
                           commit=commit,
                           directory='manuscript'),
               principal_tags=sorted(principal_tags),
               counts=dict(items=len(items), principal=sum(it['principal'] for it in items), statements=sum(v for k, v in kinds.items() if k != 'equation'),
                           displays=kinds.get('equation', 0), by_kind=kinds),
               label_number_mismatches=mism, items=items)
    json.dump(out, open(out_path, 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(out['counts']), 'mismatches', mism)


def depth(s, a, b):
    """Brace depth of s[b] relative to s[a]."""
    t = re.sub(r'\\.', '', s[a:b])
    return t.count('{') - t.count('}')


def plain(num):
    """A number as pdftotext reads it: `$\\mathrm H_s$` is Hs."""
    return re.sub(r'\\[A-Za-z]+|[${}_^ ]', '', num)


def printed(it):
    if it['kind'] == 'equation':
        return f'({plain(it["number"])})'
    if it['kind'] == 'principal':
        return it['name']
    return f'{PRINTED[it["env"]]} {it["number"]}'


def item_id(it):
    if it['kind'] == 'equation':
        return f'Eq ({plain(it["number"])})'
    if it['kind'] == 'principal':
        return it['name']
    return f'{PRINTED[it["env"]]} {it["number"]}'


def innermost(stack):
    """The label list of the innermost item around the current point."""
    for e in reversed(stack):
        if 'rows' in e:
            return e['rows'][-1]['labels']
        if 'item' in e:
            return e['item']['labels']
    return None


def display_of(stack):
    for e in reversed(stack):
        if 'rows' in e:
            return e
    return None


def enclosing(stack):
    for e in reversed(stack):
        if 'item' in e:
            return ('statement', e)
        if e['env'] == 'proof':
            return ('proof', e)
    return None


main()
