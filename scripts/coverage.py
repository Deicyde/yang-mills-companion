"""Write docs/coverage.md and data/coverage.json: how much of the manuscript [L] formalizes, by class.

Adapted from the ternary Goldbach companion's coverage script (tg-companion, scripts/coverage.py),
standard library only.  Everything is computed from the annotations as the viewer reads them
(manuscript/pdf-overlay/annotations.bundle.json, written by `cf overlay sync`) and from the data files:
data/items.json (sections), data/mapping.json (each item's status and confirmed finding),
data/corrections.json (each finding's one-line statement), data/manuscript-{displays,steps}.json
(sections, LaTeX) and data/manuscript-{displays,steps}-mapping.json (searches, how each verdict was
checked).  It also rewrites the README's "Coverage" section, between its two `coverage` comment lines.

Records and their class (the definitions are written into docs/coverage.md):
- a statement is a numbered or named theorem, lemma, proposition, corollary, definition or remark; a
  display is a numbered equation or an unnumbered display outside proofs; a step is a proof step;
- an item's key relation is the strongest relation of its key records, in the order of the classes; an
  item with a checked absence (`noMatch` record) is Absent, and one whose key links carry no relation
  (contested or unsettled) is Unjudged;
- an item with a confirmed finding is Deviates, whatever its relation; an item that [L] carries inside a
  proof (status `inlined`, key relation `relatedMatch`) is Partial;
- a display's or a step's class is that of its own relation; every `relatedMatch` step is Deviates
  (docs/steps-mapping.md: [L] does the step there by another argument or quantity).

Usage: python3 -I scripts/coverage.py [<repository root>]
"""
import collections
import json
import os
import re
import sys

NS = 'org.mathlib-initiative.formal-companion.overlay'
CLASSES = ('1-to-1', 'Faithful', 'Partial', 'Deviates', 'Absent', 'Unjudged')
CLASS_OF = {'exactMatch': '1-to-1', 'closeMatch': 'Faithful', 'broadMatch': 'Faithful', 'hasPart': 'Partial',
            'narrowMatch': 'Deviates', 'relatedMatch': 'Deviates', 'noMatch': 'Absent'}
RANK = ('exactMatch', 'closeMatch', 'broadMatch', 'hasPart', 'narrowMatch', 'relatedMatch', 'noMatch')
FORMALIZED = ('1-to-1', 'Faithful')
TYPES = ('statements', 'displays', 'steps')
TITLE = 'Armstrong, *The construction of four-dimensional quantum Yang–Mills theory* (`manuscript/`, draft {pin7})'
LONGEST = 20
CONTRAST = re.compile(r'\b(?:not|no|only|whereas|instead|rather|but|neither|nowhere|never|different|differs|'
                      r'weaker|stronger|without|less|more)\b', re.I)

DEFINITIONS = """| Class | Relations | Meaning |
|---|---|---|
| **1-to-1** | `exactMatch` | [L] states or establishes exactly this |
| **Faithful** | `closeMatch`, `broadMatch` | the same up to a named difference, or [L] proves more |
| **Partial** | `hasPart` | [L] carries part of it |
| **Deviates** | `narrowMatch`; a confirmed finding or erratum; `relatedMatch` where [L] argues differently | [L] proves less, or something else, or the text is wrong |
| **Absent** | `noMatch` | searched for, not in [L] |
| **Unjudged** | none | no completed verdict |

**"Formalized" means 1-to-1 + Faithful.** Report every percentage with its count, as
"41/52 (79%)". Never report a percentage without its denominator."""

METHOD = """AI agents judged every relation: for the numbered items a mapper and an independent verifier per batch, a judge on disagreement and an independent review with re-judging; for the displays and proof steps a mapper and an independent verifier per batch, a judge on every disagreement of the first batches and then only on those crossing the formalized boundary, and a judge's re-search of one agreed absence in five. A second pass, after an independent review, sent every remaining disagreement between classes to a judge (the 288 that differed only between exactMatch and a weaker formalized relation, or only in the declarations cited, keep the weaker or the mapper's verdict by rule), searched every absent step again through the key proofs' callees and across [L], and re-rated every relatedMatch, hasPart and narrowMatch verdict, with a judge wherever that changed the class. Verdicts were checked mechanically (every declaration against an index built from [L]'s source at the pin, every line range and snippet against that source) and by random samples read by the session leads, themselves agents: 23 of the 360 item verdicts then complete, and 74 of the 1,356 display and step verdicts then complete. A claim that the text is wrong counts only when two independent skeptics confirmed it. No person has reviewed any verdict."""


def frac(k, n):
    return f'{k}/{n} ({100 * k / n:.0f}%)' if n else '—'


def cell(text):
    return ' '.join(str(text).split()).replace('|', '\\|')


def sentences(text):
    text = ' '.join((text or '').split())
    parts = re.split(r'(?<!\b[A-Z])(?<!\be\.g)(?<!\bi\.e)(?<!\bcf)(?<!\bp)(?<!\bpp)(?<!\bvs)(?<!\bEq)(?<!\bSec)'
                     r'(?<=\.)\s+(?=[A-Z(`\[])', text)
    return [p for p in parts if p]


def one_sentence(text):
    """The note's sentence that states the difference: the first with a word of contrast, else the first."""
    s = sentences(text)
    return next((x for x in s if CONTRAST.search(x)), s[0] if s else '')


def section_key(s):
    return int(s) if s.isdigit() else 0


def load(root, name):
    return json.load(open(os.path.join(root, 'data', name), encoding='utf-8'))


def verification_words(v):
    if not v['complete']:
        return 'not yet judged'
    words = ['judge ruling' + (' on the search' if v.get('ruling', '').startswith('search-') else '')
             if v.get('judge') else 'mapper and verifier agreed']
    for k, what in (('lead_sample', 'sample check'), ('close_review', 'closeMatch re-check')):
        c = v.get(k)
        if c and c['ruling'] != c['was']:
            words.append(f"changed from `{c['was']}` in the {what}")
    return ', '.join(words)


def records(root):
    """[{id, type, kind, section, page, relation, class, ...}] of the overlay."""
    bundle = json.load(open(os.path.join(root, 'manuscript', 'pdf-overlay', 'annotations.bundle.json'), encoding='utf-8'))
    by_id = collections.defaultdict(list)
    for row in bundle['annotations']:
        by_id[row['annotation']['id']].append(row['annotation'])
    items = {i['id']: i for i in load(root, 'items.json')['items']}
    mapping = {r['id']: r for r in load(root, 'mapping.json')['items']}
    corrections = load(root, 'corrections.json')['items']
    texts = {d['id']: d for k in ('displays', 'steps') for d in load(root, f'manuscript-{k}.json')[k]}
    maps = {r['id']: r for k in ('displays', 'steps') for r in load(root, f'manuscript-{k}-mapping.json')['records']}
    missing = (set(items) | set(texts)) ^ set(by_id)
    if missing:
        sys.exit(f'the bundle and data/ disagree on {sorted(missing)[:5]}')

    out = []
    for rid, recs in by_id.items():
        kind = recs[0]['kind']
        page = recs[0]['extensions'][NS]['locator']['physical'][0]
        rec = {'id': rid, 'kind': kind, 'page': page}
        if kind in ('proof_step', 'display'):
            m, r = maps[rid], recs[0]
            rec.update(type='steps' if kind == 'proof_step' else 'displays', section=texts[rid]['section']['number'],
                       relation=r.get('relation'), note=r.get('note') or '', item=m.get('item'),
                       declarations=list(dict.fromkeys(o['location']['declaration'] for o in r['object'])),
                       verification=verification_words(m['verification']),
                       length=len(' '.join(texts[rid]['latex'].split())))
            if rec['relation'] == 'noMatch':
                rec['searched'] = m.get('searched', [])
            rec['class'] = CLASS_OF.get(rec['relation'], 'Unjudged')
        else:
            m = mapping[rid]
            rec.update(type='displays' if kind == 'equation' else 'statements', section=items[rid]['section']['number'],
                       status=m['status'], verification=recs[0]['extensions'][NS]['provenance']['method'])
            key = [r for r in recs if r.get('relation') and r.get('relation') != 'noMatch'
                   and any(o.get('role') == 'key' for o in r['object'])]
            absent = [r for r in recs if r.get('relation') == 'noMatch']
            if absent:
                rec['relation'], rec['declarations'], rec['note'] = 'noMatch', [], absent[0].get('note', '')
            elif key:
                best = min(key, key=lambda r: RANK.index(r['relation']))
                rec['relation'], rec['note'] = best['relation'], best.get('note', '')
                rec['declarations'] = [o['location']['declaration'] for o in best['object']]
            else:
                rec['relation'], rec['declarations'], rec['note'] = None, [], recs[0].get('note', '')
            f = m.get('finding') or {}
            if f.get('confirmed'):
                rec['finding'] = {'claim': f['claim'], 'said': corrections.get(rid, {}).get('readme', ''),
                                  'declarations': corrections.get(rid, {}).get('decls', [])}
                rec['class'] = 'Deviates'
            elif m['status'] == 'inlined':
                rec['class'] = 'Partial'
            else:
                rec['class'] = CLASS_OF.get(rec['relation'], 'Unjudged')
        out.append(rec)
    natural = lambda t: [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', t)]
    return sorted(out, key=lambda r: (section_key(r['section']), TYPES.index(r['type']), r['page'], natural(r['id'])))


def counts(recs):
    c = collections.Counter(r['class'] for r in recs)
    return {k: c[k] for k in CLASSES}


def summarize(recs):
    head = {}
    groups = [(t, lambda r, t=t: r['type'] == t) for t in TYPES] + [
        ('numbered displays', lambda r: r['kind'] == 'equation'), ('unnumbered displays', lambda r: r['kind'] == 'display')]
    for name, pred in groups:
        rs = [r for r in recs if pred(r)]
        judged = [r for r in rs if r['class'] != 'Unjudged']
        head[name] = {'total': len(rs), 'classes': counts(rs), 'formalized': sum(1 for r in rs if r['class'] in FORMALIZED),
                      'judged': len(judged)}
    sections = []
    for s in sorted({r['section'] for r in recs}, key=section_key):
        rs = [r for r in recs if r['section'] == s]
        row = {'section': s}
        for t in TYPES:
            ts = [r for r in rs if r['type'] == t]
            row[t] = [sum(1 for r in ts if r['class'] in FORMALIZED), len(ts)]
            row[f'{t}_1to1'] = [sum(1 for r in ts if r['class'] == '1-to-1'), len(ts)]
            row[f'{t}_absent'] = [sum(1 for r in ts if r['class'] == 'Absent'), len(ts)]
            row[f'{t}_unjudged'] = [sum(1 for r in ts if r['class'] == 'Unjudged'), len(ts)]
        row['deviations'] = [sum(1 for r in rs if r['class'] == 'Deviates'), len(rs)]
        sections.append(row)
    return head, sections


def extremes(sections, t):
    rows = [(r[t][0] / r[t][1], r) for r in sections if r[t][1]]
    hi, lo = max(s for s, _ in rows), min(s for s, _ in rows)

    def name(v):
        rs = [r for s, r in rows if s == v]
        if len(rs) == 1:
            return f"Section {rs[0]['section']}, {frac(*rs[0][t])}"
        return 'Sections ' + ', '.join(f"{r['section']} ({r[t][0]}/{r[t][1]})" for r in rs) + f', {100 * v:.0f}% each'
    return f'most formalized {name(hi)}; least {name(lo)}'


def headline_table(head, names=('statements', 'displays', 'numbered displays', 'unnumbered displays', 'steps')):
    lines = ['| | ' + ' | '.join(CLASSES) + ' | Formalized |', '|---|' + '---|' * (len(CLASSES) + 1)]
    for t in names:
        h = head[t]
        label = t.capitalize() if t in TYPES else f'&nbsp;&nbsp;of which {t}'
        lines.append(f'| {label} | ' + ' | '.join(frac(h['classes'][c], h['total']) for c in CLASSES)
                     + f" | **{frac(h['formalized'], h['total'])}** |")
    return lines


def section_table(sections):
    lines = ['| Section | Statements formalized | Displays formalized | Steps formalized | Steps absent | Deviations |',
             '|---|---|---|---|---|---|']
    for r in sections:
        lines.append(f"| {r['section']} | {frac(*r['statements'])} | {frac(*r['displays'])} | {frac(*r['steps'])} | "
                     f"{frac(*r['steps_absent'])} | {frac(*r['deviations'])} |")
    return lines


def extremes_line(sections):
    return (f"By statement share: {extremes(sections, 'statements')}. "
            f"By step share (sections with proofs): {extremes(sections, 'steps')}.")


def unjudged_line(head):
    h, d = head['steps'], head['unnumbered displays']
    return (f"Unjudged steps and unnumbered displays are those whose mapper and verifier disagreed and no judge "
            f"reached: {h['classes']['Unjudged']} of {h['total']} steps and {d['classes']['Unjudged']} of {d['total']} "
            f"displays. Of the judged steps, {frac(h['formalized'], h['judged'])} are formalized; of the judged "
            f"unnumbered displays, {frac(d['formalized'], d['judged'])}.")


def label_of(r):
    return r['id']


def decls_text(ds, cap=4):
    ds = [f'`{d}`' for d in ds]
    return ', '.join(ds[:cap]) + (f', … ({len(ds) - cap} more)' if len(ds) > cap else '') if ds else '—'


def evidence(r):
    if r.get('finding'):
        return f"confirmed finding ({r['finding']['claim']}): two skeptics"
    return f"judged `{r['relation']}` ({r['verification']})"


def write_doc(root, pin, src_pin, recs, head, sections):
    md = ['# Coverage', '',
          '> Unreviewed machine audit. AI agents produced every verdict; no mathematician has checked any of it.', '',
          f'How much of the manuscript [L] (yang-mills-group/OpenAI-YM-20261028 at `{pin}`) formalizes, by record and',
          'by class. Written by `scripts/coverage.py` from the annotations and `data/`; the numbers are in',
          '`data/coverage.json`. The manuscript has no chapters, so the rows are its 19 sections. Pages are pages of',
          '`main.pdf` (printed and physical pages agree).', '',
          'Contents: 1. Headline · 2. By section · 3. 1-to-1 · 4. Deviations · 5. Absent · 6. Definitions and method', '',
          '## 1. Headline', '', TITLE.format(pin7=src_pin[:7]) + ':', ''] + headline_table(head) + ['', unjudged_line(head), '']
    st = [r for r in recs if r['type'] == 'statements' and r['class'] == 'Deviates']
    md += [f"Statements are the {head['statements']['total']} numbered or named theorems, lemmas, propositions, corollaries,"
           f" definitions and remarks; displays the {head['numbered displays']['total']} numbered equations and the"
           f" {head['unnumbered displays']['total']} unnumbered displays outside proofs; steps the"
           f" {head['steps']['total']} steps of the {len({r['item'] for r in recs if r['type'] == 'steps'})} proofs."
           f" Of the {len(st)} statements that deviate, {sum(1 for r in st if r.get('finding'))} are confirmed findings.", '',
           '## 2. By section', ''] + section_table(sections) + ['', extremes_line(sections), '',
           'A proof step is counted in the section where its proof is printed. "Deviations" counts the Deviates records'
           " among the section's statements, displays and steps. Sections 1–7 and 9 have no proofs; Section 8 has one."
           ' A proof written for two items at once gives all its steps to the first: the steps of the joint deduction of'
           ' Theorems A and B are in Theorem A\'s folder, and Lemma 12.4, Theorem 3.6, Lemma 17.9 and the first part of'
           ' Lemma 17.10 have no steps of their own, their proofs being those of Lemma 12.3, Lemma 14.2, Lemma 17.8 and'
           ' Lemma 17.7; per-item step counts depend on this.', '']
    md += ['## 3. 1-to-1', '', 'Statements that [L] states exactly:', '']
    one = [r for r in recs if r['type'] == 'statements' and r['class'] == '1-to-1']
    md += [f"- {r['id']}: {decls_text(r['declarations'], 99)}, p. {r['page']}" for r in one] or ['- none']
    md += ['', 'Displays and steps, by section:', '', '| Section | Displays 1-to-1 | Steps 1-to-1 |', '|---|---|---|']
    md += [f"| {c['section']} | {frac(*c['displays_1to1'])} | {frac(*c['steps_1to1'])} |" for c in sections]
    md += ['', '## 4. Deviations', '',
           'Every Deviates record, by section; in each section the confirmed findings come first (there are no errata,'
           ' and no claim that a step or an unnumbered display is wrong was confirmed). "Text against [L]" is, for a'
           " finding, its line in the README; otherwise the sentence of the record's note that states the difference."
           ' Declarations: the record\'s key declarations, then those a finding names besides.'
           ' Evidence: the confirmed finding, or the judged relation and how it was judged.', '']
    dev = [r for r in recs if r['class'] == 'Deviates']
    for c in sections:
        rs = [r for r in dev if r['section'] == c['section']]
        if not rs:
            continue
        rs.sort(key=lambda r: (not r.get('finding'), TYPES.index(r['type']), r['page']))
        md += [f"### Section {c['section']} ({len(rs)})", '', '| Record | p. | Text against [L] | Declarations | Evidence |',
               '|---|---|---|---|---|']
        for r in rs:
            said = r['finding']['said'] if r.get('finding') else one_sentence(r['note'])
            # the record's key declarations, then any further ones the finding names
            ds = list(dict.fromkeys(r['declarations'] + ((r.get('finding') or {}).get('declarations') or [])))
            md.append(f"| {cell(label_of(r))} | {r['page']} | {cell(said) or '—'} | {cell(decls_text(ds, 6))} | "
                      f"{cell(evidence(r))} |")
        md.append('')
    md += ['## 5. Absent', '', 'Absent statements (a checked absence; the note says what was searched):', '']
    ab = [r for r in recs if r['type'] == 'statements' and r['class'] == 'Absent']
    md += [f"- {r['id']}, p. {r['page']}: {cell(r['note']) or 'no note'}" for r in ab] or ['- none']
    nf = [r for r in recs if r['type'] in ('statements', 'displays') and r.get('finding', {}).get('claim') == 'no-match']
    if nf:
        md += ['', f"{len(nf)} further items ({', '.join(r['id'] for r in nf)}) have no counterpart in [L] and are confirmed"
               ' findings, so they count as Deviates (section 4).']
    md += ['', 'Absent displays and steps, by section:', '', '| Section | Displays absent | Steps absent |', '|---|---|---|']
    md += [f"| {c['section']} | {frac(*c['displays_absent'])} | {frac(*c['steps_absent'])} |" for c in sections]
    md += ['', f"The {LONGEST} longest absent steps, the most text with no counterpart (length: characters of the step's"
           " LaTeX, whitespace collapsed); the last column is the record's note:", '',
           '| Step | p. | Length | Note |', '|---|---|---|---|']
    steps = sorted((r for r in recs if r['type'] == 'steps' and r['class'] == 'Absent'), key=lambda r: (-r['length'], r['id']))
    md += [f"| {r['id']} | {r['page']} | {r['length']} | {cell(r['note'])} |" for r in steps[:LONGEST]]
    md += ['', '## 6. Definitions and method', '',
           "For each record take its key relation: for an item, the strongest relation of its key links; for a step,"
           ' its own relation.', '', DEFINITIONS, '', METHOD, '',
           'How the class is taken here. An item with a checked absence is Absent. An item with a confirmed finding is'
           f" Deviates whatever its relation, including the no-match findings. The {sum(1 for r in recs if r.get('status') == 'inlined')}"
           ' items that [L] carries inside a proof (status `inlined`, key relation `relatedMatch`: [L] argues the same'
           " way but states no declaration of them) are Partial. The"
           f" {sum(1 for r in recs if r.get('status') == 'unclear')} items whose verdict was contested or left unsettled"
           ' (status `unclear`) carry no relation and are Unjudged. Every `relatedMatch` step or unnumbered display is Deviates: by `docs/steps-mapping.md` it'
           ' means [L] does the step there by another argument or with another quantity.', '']
    open(os.path.join(root, 'docs', 'coverage.md'), 'w', encoding='utf-8').write('\n'.join(md))


def write_readme(root, head, sections):
    path = os.path.join(root, 'README.md')
    text = open(path, encoding='utf-8').read()
    lines = ['<!-- coverage: written by scripts/coverage.py -->', '## Coverage', '',
             'Each statement, display and proof step has one class; "formalized" is 1-to-1 + Faithful. The',
             'definitions, the 1-to-1 list, every deviation and the absences: [`docs/coverage.md`](docs/coverage.md).', '']
    lines += headline_table(head, TYPES) + ['', unjudged_line(head), ''] + section_table(sections) + \
        ['', extremes_line(sections), '', '<!-- /coverage -->']
    block = '\n'.join(lines)
    rx = re.compile(r'<!-- coverage: written by scripts/coverage.py -->.*?<!-- /coverage -->', re.S)
    if rx.search(text):
        text = rx.sub(lambda m: block, text)
    else:
        anchor = '\n## What was checked and what was not'
        if anchor not in text:
            sys.exit('README.md: no "## What was checked and what was not" section to put the coverage before')
        text = text.replace(anchor, '\n' + block + '\n' + anchor, 1)
    open(path, 'w', encoding='utf-8').write(text)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pin = load(root, 'mapping.json')['lean']['version']
    recs = records(root)
    head, sections = summarize(recs)
    doc = {'about': 'Coverage of the manuscript overlay by class (docs/coverage.md), written by scripts/coverage.py.',
           'lean': pin, 'classes': list(CLASSES), 'formalized': list(FORMALIZED),
           'headline': head, 'sections': sections,
           'records': [{k: r[k] for k in ('id', 'type', 'kind', 'section', 'page', 'relation', 'class')} for r in recs]}
    with open(os.path.join(root, 'data', 'coverage.json'), 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write('\n')
    write_doc(root, pin, load(root, 'mapping.json')['source_pin'], recs, head, sections)
    write_readme(root, head, sections)
    print(json.dumps({t: {'formalized': frac(h['formalized'], h['total']), **h['classes']} for t, h in head.items()}, indent=1))


if __name__ == '__main__':
    main()
