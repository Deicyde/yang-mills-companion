"""Write manuscript/annotations/: the Literature Links annotations of the manuscript overlay.

Adapted from the ternary Goldbach companion's producer (tg-companion, scripts/produce.py), standard
library only. formal-companion's route B: this producer writes the files and `cf overlay sync`
records them; formal-companion docs/overlay.md section 7 is the layout.

Reads data/items.json (the items of [M] at its pin), data/regions.json (their regions on main.pdf),
data/mapping.json (the item-to-Lean verdicts), data/notes-short.json (condensed notes) and
data/linked-decls.json (the linked declarations of [L] at its pin: module, file, line, kind,
statement), and writes

  manuscript/annotations/_defaults.json                 the PDF and the repository at the pin
  manuscript/annotations/<section>/<item>__<role>__<declaration>.json
  manuscript/annotations/<section>/<item>/<role>__<declaration>.json   (an item with several records)
  manuscript/annotations/<section>/<item>/key.json      (the record of several key declarations)

One record per item for its key declarations together, carrying the item's relation, and one per
other linked declaration (`relatedMatch`); one checked absence (`noMatch`) for an item judged
`no-match` or `not-formalized-not-needed`, whose search is recorded in the mapping; one record with
an empty object for an item that links nothing.  Every record names all the item's regions.

The unnumbered displays outside proofs are items of kind `display`, written like the numbered ones:
one record of their key declarations together, a checked absence, or for a display with no
completed verdict an empty object and the note "Not yet judged".  The steps of an item's proof are
records of kind `proof_step` in the item's folder, `<item>/step-001.json`, ...: each end names the
`lines` of a declaration with their snippet and `proof_context`, and a `noMatch` step names the
declarations it was checked against, with their lines and no snippet (formal-companion
docs/overlay.md section 7).  An item with a proof always has a folder.  The displays and steps come
from data/manuscript-{displays,steps}.json, their -mapping.json files and
data/manuscript-regions-steps.json.

With `--index <decls.json>` (the full declaration index, scripts/lean/decls.py), it first rewrites
data/linked-decls.json from the index, checked against data/decls.json.sha256.

Usage: python3 -I scripts/produce.py [--index <decls.json>] [<repository root>]
"""
import collections
import hashlib
import json
import os
import re
import shutil
import sys

NS = 'org.mathlib-initiative.formal-companion.overlay'
ROLES = ('key', 'attributed', 'support', 'example', 'helper')
UNSAFE = re.compile(r'[^A-Za-z0-9._-]')
RESERVED = re.compile(r'(?i)(con|prn|aux|nul|com[0-9]|lpt[0-9])')
MAX_NAME = 120
SOURCE_ID = 'ym-informalization-{pin7}'
PDF_URL = 'https://raw.githubusercontent.com/scottnarmstrong/yang-mills-informalization/{pin}/manuscript/main.pdf'
SRC_REPO = 'https://github.com/scottnarmstrong/yang-mills-informalization'

# The item's status (docs/taxonomy.md) -> the record's Literature Links status.  The relation of each
# link is the one data/mapping.json carries (scripts/mapping/merge.py, the table in out/REPORT-2.md).
STATUS = {
    'exact': 'formalized', 'definition-match': 'formalized', 'close': 'formalized',
    'definition-close': 'formalized', 'stronger': 'formalized', 'parts': 'formalized',
    'inlined': 'partial',  # carried inside a proof: no declaration states it
    'weaker': 'partial', 'missing-hypothesis': 'partial', 'differs': 'partial',
    'no-match': 'not_formalized', 'not-formalized-not-needed': 'not_formalized',
    'unclear': None,
}
FINDINGS = {'weaker', 'missing-hypothesis', 'differs', 'no-match'}
VERDICT_SUMMARY = {
    'weaker': '[L] proves less than [M] prints.',
    'missing-hypothesis': '[L] needs a hypothesis [M] does not print.',
    'differs': '[L] states a different form; neither implies the other.',
    'no-match': '[L] states no counterpart of what [M] prints.',
}
KIND_TITLE = {'definition': 'Definition', 'lemma': 'Lemma', 'theorem': 'Theorem', 'proposition': 'Proposition',
              'corollary': 'Corollary', 'remark': 'Remark'}
ACCENTS = {"\\'e": 'é', '\\"o': 'ö', '\\"u': 'ü', '\\`e': 'è', '---': '—', '--': '–'}
ABBREVIATION = re.compile(r'(?:\b(?:e\.g|i\.e|a\.e|cf|Prop|Thm|Lem|Cor|Sec|Eq|Eqs|pp?|resp|vs|approx|al|Fig|No)\.|'
                          r'\b[A-Z]\.)$')


def sentences(text):
    out, cur = [], ''
    for part in re.split(r'(?<=[.!?])\s+', ' '.join((text or '').split())):
        cur = f'{cur} {part}'.strip()
        if not ABBREVIATION.search(cur):
            out.append(cur)
            cur = ''
    return out + ([cur] if cur else [])


def file_name(key, suffix='', force_hash=False):
    """formal-companion's rule (scripts/overlay/shards.py): unsafe characters as `-`, and a name that is
    too long, reserved, `_defaults.json` or equal to another ignoring case ends in a hash of the key."""
    stem = UNSAFE.sub('-', key)
    if stem.startswith('.'):
        stem = '-' + stem[1:]
    if force_hash or len(stem) + len(suffix) > MAX_NAME or RESERVED.fullmatch(stem.split('.', 1)[0]) \
            or (stem + suffix).lower() == '_defaults.json':
        tail = '-' + hashlib.sha256(key.encode('utf-8')).hexdigest()[:10]
        stem = stem[:MAX_NAME - len(suffix) - len(tail)] + tail
    return stem + suffix


def title_of(item):
    if item['kind'] == 'equation':
        return f"Equation {item['printed']}"
    head = f"{KIND_TITLE[item['kind']]} {item['number']}"
    if item.get('name'):
        name = item['name']
        for tex, char in ACCENTS.items():
            name = name.replace(tex, char)
        head += f' ({name})'
    return head


def provenance(rec):
    v = rec['verification']
    method = 'mapper and verifier agents, agreed' if v['agreed'] else 'mapper and verifier agents, a judge ruled'
    f = rec.get('finding')
    c = v.get('corrected') if (v.get('corrected') or {}).get('kind') == 'rejudged' else None
    if f and c:
        method += '; claimed finding withdrawn on review' if f.get('withdrawn') else \
            '; finding re-confirmed by two new skeptics after review' if f.get('confirmed') else \
            '; revised finding not re-confirmed after review'
    elif f:
        method += '; finding confirmed by two skeptics' if f.get('confirmed') else \
            '; claimed finding contested by two skeptics' if f.get('refuted') else '; claimed finding refuted by two skeptics'
    if c:
        method += '; re-judged after an independent review'
    elif v.get('corrected'):
        method += '; note revised after an independent review'
    method += '; statements of [L] read at the pin, not built'
    return {'actor': 'agent', 'method': method, 'confirmed_by_human': False}


def note_of(rec, short):
    f = rec.get('finding') or {}
    if rec['id'] in short:
        note = short[rec['id']]
    elif rec['status'] == 'unclear':
        note = ('Contested: of two skeptics, one upheld and one refuted the claim that [L] does not prove this as '
                'printed, so no relation is claimed.')
    else:
        s = sentences(rec['note'])
        if len(s) > 2:
            sys.exit(f"{rec['id']}: note of {len(s)} sentences has no short form in data/notes-short.json")
        note = ' '.join(s)
    if f.get('confirmed'):
        note = 'Finding: ' + note
    return note


# A display's or a step's relation -> its record's status.
STEP_STATUS = {'exactMatch': 'formalized', 'closeMatch': 'formalized', 'broadMatch': 'formalized',
               'hasPart': 'partial', 'narrowMatch': 'partial', 'relatedMatch': 'partial', 'noMatch': 'not_formalized'}


def step_provenance(r):
    v = r['verification']
    if not v['complete']:
        method = 'mapper and verifier agents disagreed; not yet judged'
    elif v.get('judge'):
        method = 'mapper and verifier agents, a judge ruled'
        if v.get('ruling', '').startswith('search-'):
            method += ' on the search'
    else:
        method = 'mapper and verifier agents, agreed'
    for k, what in (('lead_sample', 'a sample check'), ('close_review', 'a re-check of closeMatch records')):
        c = v.get(k)
        if c:
            method += f"; {what} {'changed it from ' + c['was'] if c['ruling'] != c['was'] else 'kept it'}"
    method += '; lines of [L] read at the pin, not built'
    return {'actor': 'agent', 'method': method, 'confirmed_by_human': False}


def proof_kind(r, keys):
    """The `proof` extension's kind: `direct` for an excerpt of a declaration's proof, `helper` for one
    other declaration's statement, `chain` for several declarations, in the record's order."""
    names = list(dict.fromkeys(e['decl'] for e in r['ends']))
    if len(names) > 1:
        return 'chain'
    if names[0] not in keys and all(e['lines'][0] == e['proof_context']['lines'][0] for e in r['ends']):
        return 'helper'
    return 'direct'


def proof_overlay(root, pdf, lean, pin, key_decls):
    """The unnumbered displays outside proofs and the proof steps, from data/manuscript-{displays,steps}.json,
    their -mapping.json files and data/manuscript-regions-steps.json.  `key_decls` maps an item to its
    key declarations.  Returns ({path: record} of the display items, {item id: [step records in proof order]})."""
    data = lambda n: json.load(open(os.path.join(root, 'data', n), encoding='utf-8'))
    regions = data('manuscript-regions-steps.json')
    if regions['pdf'] != pdf:
        sys.exit('manuscript-regions-steps.json is of another PDF')
    segments = {k: {t['id']: t for t in data(f'manuscript-{k}.json')[k]} for k in ('displays', 'steps')}
    maps = {k: data(f'manuscript-{k}-mapping.json') for k in ('displays', 'steps')}
    for k, m in maps.items():
        if m['lean'] != lean or m['source_pin'] != pin or [r['id'] for r in m['records']] != list(segments[k]):
            sys.exit(f'manuscript-{k}-mapping.json is of another pin, or incomplete')
    texts = {**segments['displays'], **segments['steps']}

    def end(e, snippet):
        a, b = e['lines']
        ext = {'declaration': {'id': e['decl']}}
        if snippet:
            ext['snippet'] = {'text': e['snippet'], 'line': a, 'truncated': False}
        ext['destination'] = {'resolution': 'exact', 'href': f"{lean['repository']}/blob/{lean['version']}/{e['file']}",
                              'fragment': f'L{a}-L{b}'}
        if snippet:
            ext['proof_context'] = {k: e['proof_context'][k] for k in ('declaration', 'lines', 'conclusion')}
        location = {'declaration': e['decl'], 'module': e['file'][:-len('.lean')].replace('/', '.'), 'lines': [a, b]}
        out = {'type': 'lean', 'uri': lean['repository'], 'version': lean['version'], 'location': location}
        if snippet:  # the ends of a checked absence name where it looked, not a key declaration
            out['role'] = 'key'
        out['extensions'] = {NS: ext}
        return out

    def record(r, kind, title, extra=None):
        regs = regions['regions'][r['id']]
        subject = []
        for n, g in enumerate(regs):
            ext = {'region': f"{r['id']}#{n}" if len(regs) > 1 else r['id']}
            if g.get('quads'):
                ext['quads'] = g['quads']
            subject.append({'location': {'page': g['page'], 'rect': g['rect']}, 'title': title, 'extensions': {NS: ext}})
        ext = {'locator': {'physical': sorted({g['page'] for g in regs})}, 'provenance': step_provenance(r), **(extra or {})}
        out = {'id': r['id'], 'kind': kind}
        if r['relation']:
            out.update(status=STEP_STATUS[r['relation']], relation=r['relation'])
        note = ' '.join(sentences(r.get('note'))) if r['relation'] else 'Not yet judged.'
        if note:  # an agreed exactMatch may carry none
            out['note'] = note
        absent = r['relation'] == 'noMatch'
        out.update(subject=subject, object=[end(e, not absent) for e in r.get('ends', [])], extensions={NS: ext})
        return out

    displays = {}
    for r in maps['displays']['records']:
        d = texts[r['id']]
        rec = record(r, 'display', d['title'])
        key = 'noMatch' if r['relation'] == 'noMatch' else 'key' if len(rec['object']) > 1 else \
            f"key__{rec['object'][0]['location']['declaration']}" if rec['object'] else None
        name = file_name(f"{r['id']}__{key}" if key else r['id'], '.json')
        displays[f"{d['section']['number']}/{name}"] = rec

    steps = collections.defaultdict(list)
    for r in maps['steps']['records']:
        s = texts[r['id']]
        pages = sorted({g['page'] for g in regions['regions'][r['id']]})
        where = f'p. {pages[0]}' if len(pages) == 1 else f'pp. {pages[0]}–{pages[-1]}'
        title = f"{r['id']}: {'Display' if s['kind'] == 'display' else 'Text'}, {where}"
        if not r['relation']:  # a step prints its relation, and an exact one none: say that this one has none yet
            title += ', not yet judged'
        extra = {'proof': {'kind': proof_kind(r, key_decls[r['item']])}} \
            if r['relation'] and r['relation'] != 'noMatch' else None
        steps[r['item']].append((s['step'], record(r, 'proof_step', title, extra)))
    return displays, {k: [rec for _, rec in sorted(v, key=lambda x: x[0])] for k, v in steps.items()}


def step_files(folder, step_records):
    """`<item folder>/step-001.json`, ...: names that sort in the order of the proof."""
    return {f'{folder}/step-{n:03d}.json': r for n, r in enumerate(step_records, 1)}


def linked_decls(root, index_path):
    """Rewrite data/linked-decls.json: each declaration data/mapping.json names, from the full index."""
    want = open(os.path.join(root, 'data', 'decls.json.sha256')).read().split()[0]
    h = hashlib.sha256()
    with open(index_path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    if h.hexdigest() != want:
        sys.exit(f'{index_path} is not the index data/decls.json.sha256 names')
    index = json.load(open(index_path, encoding='utf-8'))
    rows = collections.defaultdict(list)
    for r in index['decls']:
        rows[r['name']].append(r)
    mapping = json.load(open(os.path.join(root, 'data', 'mapping.json'), encoding='utf-8'))
    out = {}
    for rec in mapping['items']:
        for l in rec['lean']:
            cands = rows.get(l['decl'])
            if not cands:
                sys.exit(f"{rec['id']}: {l['decl']} is not in the index")
            if len(cands) > 1:  # a name declared in two modules: the mapping's `where` names the file
                path = l['where'].split(':')[0]
                cands = [r for r in cands if r['file'] == path] or cands
            r = cands[0]
            out.setdefault(l['decl'], {})
            out[l['decl']][r['file']] = {k: r.get(k) for k in ('kind', 'module', 'file', 'line', 'private', 'snippet')}
    doc = {'about': 'The declarations of [L] that data/mapping.json links, from the declaration index '
                    '(scripts/lean/decls.py, sha256 in data/decls.json.sha256); keyed by name, then file.',
           'lean': index['lean'], 'decls': dict(sorted(out.items()))}
    with open(os.path.join(root, 'data', 'linked-decls.json'), 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write('\n')


def main():
    args = sys.argv[1:]
    index_path = None
    if args[:1] == ['--index']:
        index_path, args = args[1], args[2:]
    root = args[0] if args else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if index_path:
        linked_decls(root, index_path)
    data = lambda n: json.load(open(os.path.join(root, 'data', n), encoding='utf-8'))
    items = {it['id']: it for it in data('items.json')['items']}
    regions, mapping, decls = data('regions.json'), data('mapping.json'), data('linked-decls.json')
    short = data('notes-short.json')['notes']
    lean = mapping['lean']
    if decls['lean']['commit'] != lean['version'] or decls['lean']['repository'] != lean['repository']:
        sys.exit('linked-decls.json is of another Lean revision')
    pin = mapping['source_pin']
    pdf = regions['pdf']
    if pdf['url'] != PDF_URL.format(pin=pin):
        sys.exit('regions.json is of another PDF')
    source_id = SOURCE_ID.format(pin7=pin[:7])

    defaults = {
        'subject': {
            'type': 'pdf', 'uri': pdf['url'], 'sha256': pdf['sha256'],
            'citation': {'id': source_id, 'type': 'manuscript',
                         'title': 'The construction of four-dimensional quantum Yang–Mills theory',
                         'author': [{'family': 'Armstrong', 'given': 'Scott'}],
                         'issued': {'date-parts': [[2026, 11, 11]]}, 'version': f'draft, commit {pin}',
                         'URL': f'{SRC_REPO}/tree/{pin}/manuscript'},
            'extensions': {NS: {'source_id': source_id, 'bytes': pdf['bytes'], 'physical_page_count': pdf['pages']}}},
        'object': {'type': 'lean', 'uri': lean['repository'], 'version': lean['version']},
    }

    def lean_end(l, role):
        cands = decls['decls'][l['decl']]
        path = l['where'].split(':')[0]
        d = cands.get(path) or next(iter(cands.values()))
        ext = {'declaration': {'id': l['decl'], 'kind': d['kind']},
               'snippet': {'text': d['snippet'], 'line': d['line'], 'truncated': d['snippet'].endswith('…')},
               'destination': {'resolution': 'exact', 'href': f"{lean['repository']}/blob/{lean['version']}/{d['file']}",
                               'fragment': f"L{d['line']}"}}
        if d.get('private'):
            ext['declaration']['private'] = True
        # written whole: an end with its own `uri` takes nothing from the template
        return {'type': 'lean', 'uri': lean['repository'], 'version': lean['version'],
                'location': {'declaration': l['decl'], 'module': d['module']}, 'role': role, 'extensions': {NS: ext}}

    key_decls = {rec['id']: {l['decl'] for l in rec['lean'] if l['role'] == 'key'} for rec in mapping['items']}
    display_files, steps = proof_overlay(root, pdf, lean, pin, key_decls)
    out_dir = os.path.join(root, 'manuscript', 'annotations')
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    counts = collections.Counter()
    files = {}
    for rec in mapping['items']:
        it = items[rec['id']]
        regs = regions['items'][rec['id']]
        subject = [{'location': {'page': r['page'], 'rect': r['rect']}, 'title': title_of(it),
                    'extensions': {NS: {'region': f"{it['id']}#{n}" if len(regs) > 1 else it['id']}}}
                   for n, r in enumerate(regs)]
        pages = sorted({r['page'] for r in regs})
        complete = rec['verification'].get('complete')
        status = STATUS[rec['status']] if complete else None
        ext = {'locator': {'physical': pages}, 'provenance': provenance(rec)}
        f = rec.get('finding') or {}
        if f.get('confirmed'):
            summary = VERDICT_SUMMARY[f['claim']] + (f" [M] prints `{f['quote']}`." if f.get('quote') else '')
            ext['verdicts'] = [{'verdict': 'deviation', 'summary': summary,
                                'evidence': f.get('skeptic_notes', []),
                                'provenance': {'actor': 'agent', 'method': 'two skeptics, each reading the LaTeX of [M] '
                                               'and the source of [L], failed to refute it', 'confirmed_by_human': False}}]
            counts['confirmed_findings'] += 1
        base = {'id': it['id'], 'kind': it['kind']}
        if status:
            base['status'] = status
        base['note'] = note_of(rec, short) if complete else 'Not yet judged.'
        records = []
        seen = {}
        for l in rec['lean']:  # a declaration linked twice keeps its first, key-most link
            if l['decl'] not in seen or (l['role'] == 'key' and seen[l['decl']]['role'] != 'key'):
                seen[l['decl']] = l
        # the key links form one record: the item's relation holds between the item and all its key
        # declarations together; every other link is a record of its own
        keys = sorted((l for l in seen.values() if l['role'] == 'key'), key=lambda l: l['decl'])
        groups = ([keys] if keys else []) + [[l] for l in seen.values() if l['role'] != 'key']
        for g in groups:
            r = dict(base)
            if complete and g[0].get('relation'):
                r['relation'] = g[0]['relation']
            records.append(dict(r, subject=subject, object=[lean_end(l, l['role']) for l in g],
                                extensions={NS: dict(ext)}))
        if complete and rec['status'] in ('no-match', 'not-formalized-not-needed'):
            if not rec.get('searched'):
                sys.exit(f"{rec['id']}: a checked absence with no recorded search")
            records.insert(0, dict(base, relation='noMatch', subject=subject,
                                   object=[{'type': 'lean', 'uri': lean['repository'], 'version': lean['version']}],
                                   extensions={NS: dict(ext)}))
            counts['checked_absences'] += 1
        if not records:
            records.append(dict(base, subject=subject, object=[], extensions={NS: dict(ext)}))
            counts['unlinked'] += 1
        if not complete:
            counts['not_yet_judged'] += 1

        def key_of(r, in_item):
            if not r['object']:
                return 'unlinked' if in_item else it['id']
            if r.get('relation') == 'noMatch':
                return 'noMatch' if in_item else f"{it['id']}__noMatch"
            o = r['object'][0]
            rest = f"{o['role']}__{o['location']['declaration']}" if len(r['object']) == 1 else o['role']
            return rest if in_item else f"{it['id']}__{rest}"
        records.sort(key=lambda r: (r.get('relation') != 'noMatch',
                                    ROLES.index(r['object'][0]['role']) if r['object'] and 'role' in r['object'][0] else -1,
                                    r['object'][0]['location']['declaration'] if r['object'] and 'location' in r['object'][0] else ''))
        folder = it['section']['number']
        if len(records) == 1 and it['id'] not in steps:
            paths = [f"{folder}/{file_name(key_of(records[0], False), '.json')}"]
        else:
            sub = file_name(it['id'])
            keys = [key_of(r, True) for r in records]
            names = [file_name(k, '.json') for k in keys]
            clash = collections.Counter(n.lower() for n in names)
            names = [file_name(k, '.json', force_hash=clash[n.lower()] > 1) for k, n in zip(keys, names)]
            if len({n.lower() for n in names}) != len(names):
                sys.exit(f"{it['id']}: two records share a file name")
            paths = [f"{folder}/{sub}/{n}" for n in names]
        proof = step_files(f"{folder}/{file_name(it['id'])}", steps.pop(it['id'], []))
        counts['proof_steps'] += len(proof)
        for p, r in list(zip(paths, records)) + list(proof.items()):
            if p.lower() in {q.lower() for q in files}:
                sys.exit(f'two files named {p}')
            files[p] = r
            counts['records'] += 1
            counts[f"relation.{r.get('relation', 'none')}"] += 1
            counts[f"ends.{r.get('relation', 'none')}"] += len(r['object'])
        counts['items'] += 1
    if steps:
        sys.exit(f'steps of items not in the overlay: {sorted(steps)}')
    for p, r in display_files.items():
        if p.lower() in {q.lower() for q in files}:
            sys.exit(f'two files named {p}')
        files[p] = r
        counts['display_records'] += 1
        counts[f"relation.{r.get('relation', 'none')}"] += 1
    with open(os.path.join(out_dir, '_defaults.json'), 'w', encoding='utf-8') as f:
        json.dump(defaults, f, indent=2, ensure_ascii=False)
        f.write('\n')
    for p, r in sorted(files.items()):
        path = os.path.join(out_dir, *p.split('/'))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(r, f, indent=2, ensure_ascii=False)
            f.write('\n')
    print(json.dumps(dict(sorted(counts.items())), indent=1))


if __name__ == '__main__':
    main()
