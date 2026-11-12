"""Candidate declarations for each item of [M]: hints for the item-to-Lean mapping, not judgments.

New code.  For each item of items.json:
- `units`: the units of [M]'s outline (`outline/units.md`) for the item's section or subsection,
  from SECTION_UNITS below.  [M] publishes no such map; this one was written by reading the section
  titles of the manuscript against the unit titles of `data/units.tsv`.
- `key_statements`: the statements of those units in `data/key-statements.tsv` whose one-line
  summary shares words with the item's prose (its name and statement with the mathematics removed;
  for a display, the CONTEXT source lines before it and the name of the item around it),
  ranked by the sum of the shared words' inverse document frequency over all summaries; at most
  KEYS, and only with a score of at least MIN_SCORE.
- `glossary`: the entries of `glossary.md` whose description contains one of the item's defined
  terms (its name, and the `\\emph{...}` terms of its statement) as a phrase, after the same word
  normalization; a one-word term found in more than GLOSSARY_MAX entries is dropped.
Every name is checked against the declaration index (decls.json).

Usage: python3 -I seeds.py <yang-mills-informalization dir> <items json> <decls json> <out json>
"""
import collections
import csv
import json
import math
import os
import re
import sys

KEYS = 8
MIN_SCORE = 6.0
CONTEXT = 4
GLOSSARY_MAX = 5

SECTION_UNITS = {
    ('1', None): ['VIII.1'],
    ('2', None): ['I.1'],
    ('3', 'Scales and the block map'): ['III.1', 'III.2'],
    ('3', 'The density and its norms'): ['II.2', 'III.10'],
    ('3', 'The inductive step'): ['III.10', 'III.9'],
    ('3', 'Multiscale trajectories'): ['III.2', 'III.9', 'VII.5'],
    ('3', 'Local fields'): ['II.1', 'III.15'],
    ('4', None): ['III.12', 'IV.1', 'II.1', 'VII.1'],
    ('5', None): ['VI.1', 'VI.2', 'VII.1', 'III.11'],
    ('6', None): ['V.1', 'V.2', 'V.3'],
    ('7', None): ['VII.2', 'VII.3', 'VII.4'],
    ('8', None): ['VIII.1'],
    ('9', None): ['III.2'],
    ('10', None): ['II.1'],
    ('11', None): ['III.1', 'III.3', 'III.4', 'III.6'],
    ('12', None): ['III.7', 'III.9'],
    ('13', None): ['III.10', 'III.5', 'III.8', 'II.2', 'III.16'],
    ('14', 'Trajectories and tuning'): ['III.2', 'III.9', 'III.14'],
    ('14', 'Marked fields and volume-uniform estimates'): ['III.15', 'III.11', 'III.12', 'III.4'],
    ('14', 'Full ultraviolet convergence'): ['III.12', 'III.14', 'III.13'],
    ('15', None): ['IV.1', 'II.1'],
    ('16', None): ['VI.1', 'VI.2', 'VII.1', 'III.11'],
    ('17', None): ['V.1', 'V.2', 'V.3'],
    ('18', None): ['VII.2', 'VII.3', 'VII.6'],
    ('19', None): ['VII.4'],
}

STOP = set('''a an the of and or to in on for by with as at from is are be this that these those its it their
which where when then than there here such each every all any some no not one two three into onto over under
between through after before only also both either other same given let put define defined write we our us
use used using holds hold has have gives give given whose so if iff while about above below up down via per
lemma theorem proposition definition corollary remark section equation part fixed finite set sets value values
statement function functions number numbers'''.split())


def words(text):
    text = re.sub(r'\$\$.*?\$\$|\$[^$]*\$|\\\[.*?\\\]|\\\(.*?\\\)', ' ', text, flags=re.S)
    text = re.sub(r'\\begin\{(equation|align|gather|multline)\*?\}.*?\\end\{\1\*?\}', ' ', text, flags=re.S)
    text = re.sub(r'\\(?:ref|eqref|label|cite)\{[^}]*\}', ' ', text)
    text = re.sub(r'\\[A-Za-z]+', ' ', text)
    return [norm(w) for w in re.findall(r"[A-Za-z][A-Za-z'-]+", text) if w.lower() not in STOP and len(w) > 2]


def norm(w):
    w = w.lower().strip("'-")
    for suf in ('ies', 'es', 's'):
        if w.endswith(suf) and len(w) > len(suf) + 3:
            return w[:-len(suf)] + ('y' if suf == 'ies' else '')
    return w


def glossary(path):
    out = []
    lines = open(path, encoding='utf-8').read().split('\n')
    for k, line in enumerate(lines):
        m = re.match(r'\*\*\[`([^`]+)`\]\(([^)]+)\)\*\*', line)
        if m and k + 1 < len(lines):
            out.append(dict(name=m.group(1), link=m.group(2), description=lines[k + 1].strip()))
    return out


def defined_terms(it):
    terms = []
    if it['name']:
        name = re.sub(r'^[A-Z][A-Z0-9]*(?:--[A-Z0-9]+)?\.\s*', '', it['name'])
        terms.append(name)
    terms += re.findall(r'\\emph\{([^{}$]+)\}', it['statement'])
    out = []
    for t in terms:
        ws = [norm(w) for w in re.findall(r"[A-Za-z][A-Za-z'-]+", t)]
        ws = [w for w in ws if w not in STOP]
        if ws and ws not in out:
            out.append(ws)
    return out


def main():
    src, items_path, decls_path, out_path = sys.argv[1:5]
    items = json.load(open(items_path))['items']
    decl_names = {d['name'] for d in json.load(open(decls_path))['decls']}
    keys = list(csv.DictReader(open(os.path.join(src, 'data', 'key-statements.tsv'), encoding='utf-8'),
                               delimiter='\t', quoting=csv.QUOTE_NONE))
    units = {r['unit']: r['title'] for r in csv.DictReader(open(os.path.join(src, 'data', 'units.tsv'), encoding='utf-8'),
                                                         delimiter='\t', quoting=csv.QUOTE_NONE)}
    for us in SECTION_UNITS.values():
        for u in us:
            assert u in units, u
    df = collections.Counter()
    kw = []
    for k in keys:
        ws = set(words(k['summary']))
        kw.append(ws)
        df.update(ws)
    idf = {w: math.log(len(keys) / c) for w, c in df.items()}
    gl = glossary(os.path.join(src, 'glossary.md'))
    gl_words = [' ' + ' '.join(norm(w) for w in re.findall(r"[A-Za-z][A-Za-z'-]+", g['description'])) + ' ' for g in gl]
    out, unmapped, missing = {}, [], set()
    sources, by_id = {}, {it['id']: it for it in items}
    for it in items:
        sub = (it['subsection'] or {}).get('title')
        us = SECTION_UNITS.get((it['section']['number'], sub)) or SECTION_UNITS.get((it['section']['number'], None))
        if us is None:
            unmapped.append(it['id'])
            us = []
        text = (it['name'] or '') + ' ' + it['statement']
        if it['kind'] == 'equation':
            lines = sources.setdefault(it['file'], open(os.path.join(src, 'manuscript', it['file']),
                                                        encoding='utf-8').read().split('\n'))
            text += ' ' + ' '.join(lines[max(0, it['env_lines'][0] - 1 - CONTEXT):it['env_lines'][0] - 1])
            enc = by_id.get(it['enclosing'])
            if enc and enc['name']:
                text += ' ' + enc['name']
        prose = set(words(text))
        scored = []
        for k, ws in zip(keys, kw):
            if k['unit'] not in us:
                continue
            shared = prose & ws
            sc = sum(idf[w] for w in shared)
            if sc >= MIN_SCORE:
                scored.append((round(sc, 2), k, sorted(shared)))
        scored.sort(key=lambda t: -t[0])
        ks = [dict(name=k['lean_name'], number=k['number'], unit=k['unit'], score=sc, shared=sh, summary=k['summary'])
              for sc, k, sh in scored[:KEYS]]
        terms = defined_terms(it)
        gs = []
        for t in terms:
            hits = [g for g, gw in zip(gl, gl_words) if ' ' + ' '.join(t) + ' ' in gw]
            if len(t) == 1 and len(hits) > GLOSSARY_MAX:
                continue
            for g in hits:
                prev = next((x for x in gs if x['name'] == g['name']), None)
                if prev:
                    prev['terms'].append(' '.join(t))
                else:
                    gs.append(dict(name=g['name'], terms=[' '.join(t)], description=g['description']))
        for x in ks + gs:
            if x['name'] not in decl_names:
                missing.add(x['name'])
        out[it['id']] = dict(units=[dict(unit=u, title=units[u]) for u in us], defined_terms=[' '.join(t) for t in terms],
                             key_statements=ks, glossary=gs)
    stats = dict(items=len(items), with_key_statements=sum(1 for v in out.values() if v['key_statements']),
                 with_glossary=sum(1 for v in out.values() if v['glossary']), unmapped_sections=unmapped,
                 names_not_in_index=sorted(missing))
    json.dump(dict(note='hints for the mapping session; no relation is claimed', section_units=
                   {f'{s}' + (f' / {t}' if t else ''): u for (s, t), u in SECTION_UNITS.items()},
                   key_count=KEYS, min_score=MIN_SCORE, stats=stats, items=out),
              open(out_path, 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(stats, indent=1))


main()
