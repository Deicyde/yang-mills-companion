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

One record per (item, linked declaration); one checked absence (`noMatch`) for an item judged
`no-match` or `not-formalized-not-needed`, whose search is recorded in the mapping; one record with
an empty object for an item that links nothing.  Every record names all the item's regions.

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
    if f:
        method += '; finding confirmed by two skeptics' if f.get('confirmed') else \
            '; claimed finding contested by two skeptics' if f.get('refuted') else '; claimed finding refuted by two skeptics'
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
            ext['verdicts'] = [{'verdict': 'deviation', 'summary': VERDICT_SUMMARY[f['claim']],
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
        for l in seen.values():
            r = dict(base)
            if complete and l.get('relation'):
                r['relation'] = l['relation']
            records.append(dict(r, subject=subject, object=[lean_end(l, l['role'])], extensions={NS: dict(ext)}))
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
            rest = f"{o['role']}__{o['location']['declaration']}"
            return rest if in_item else f"{it['id']}__{rest}"
        records.sort(key=lambda r: (r.get('relation') != 'noMatch',
                                    ROLES.index(r['object'][0]['role']) if r['object'] and 'role' in r['object'][0] else -1,
                                    r['object'][0]['location']['declaration'] if r['object'] and 'location' in r['object'][0] else ''))
        folder = it['section']['number']
        if len(records) == 1:
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
        for p, r in zip(paths, records):
            if p.lower() in {q.lower() for q in files}:
                sys.exit(f'two files named {p}')
            files[p] = r
            counts['records'] += 1
            counts[f"relation.{r.get('relation', 'none')}"] += 1
        counts['items'] += 1
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
