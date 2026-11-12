#!/usr/bin/env python3
"""Merge the steps campaign's mapper, verifier, judge and skeptic files into the overlay's data.

A record's verdict is the judge's where the judge ruled on it, else the mapper's when mapper and
verifier agree (scompare.py); a record still without one is Unjudged (relation null).  The lead's
rulings from the sample check (scratch/steps2/lead/sample.json) override the relation and note last;
an opus re-check of closeMatch records whose notes name another route (lead/closecheck.json) next.  Each Lean end
gets its file, its snippet (exactly its lines, from the pinned source; none for noMatch) and its
`proof_context` (the enclosing declaration's full range and the end's conclusion).  A claim that
the text is wrong is kept under `text_error` with its skeptics' verdicts; only a claim both
skeptics confirm is `confirmed` and may reach a note.

Usage: python3 -I smerge.py <work dir>
Writes repo/data/manuscript-steps-mapping.json and repo/data/manuscript-displays-mapping.json.
"""
import collections
import json
import os
import re
import sys

PIN = '3456e5e75cf8d4cd558955a5c7638fba2d68f464'
REPO_URL = 'https://github.com/yang-mills-group/OpenAI-YM-20261028'
CLASS = {'exactMatch': '1-to-1', 'closeMatch': 'Faithful', 'broadMatch': 'Faithful', 'hasPart': 'Partial',
         'narrowMatch': 'Deviates', 'relatedMatch': 'Deviates', 'noMatch': 'Absent', None: 'Unjudged'}


def load(path):
    if not os.path.exists(path):
        return None
    return {r['id']: r for r in json.load(open(path)).get('records', [])}


def slug(rid):
    return re.sub(r'[^A-Za-z0-9.]+', '-', rid).strip('-')


def main(work):
    S = f'{work}/scratch/steps2'
    RJ = json.load(open(f'{S}/ranges.json'))
    R, D = RJ['ranges'], RJ['dups']
    src_cache = {}

    def src(f):
        if f not in src_cache:
            src_cache[f] = open(f'{work}/lean/{f}', encoding='utf-8').read().split('\n')
        return src_cache[f]

    def end(e, rel):
        f, a, b = R[e['decl']]
        if e.get('file') and e['file'] != f:
            f, a, b = next(d for d in D.get(e['decl'], []) if d[0] == e['file'])
        lines = e.get('lines') or [a, b]
        out = {'decl': e['decl'], 'file': f, 'lines': lines,
               'url': f'{REPO_URL}/blob/{PIN}/{f}#L{lines[0]}-L{lines[1]}'}
        if rel != 'noMatch':
            out['snippet'] = '\n'.join(src(f)[lines[0] - 1:lines[1]])
            out['conclusion'] = e.get('conclusion')
            if e.get('notation'):
                out['notation'] = e['notation']
            out['proof_context'] = {'declaration': e['decl'], 'lines': [a, b], 'conclusion': e.get('conclusion')}
        return out

    batches = json.load(open(f'{work}/repo/data/steps-batches.json'))['batches']
    steps = json.load(open(f'{work}/repo/data/manuscript-steps.json'))['steps']
    disp = json.load(open(f'{work}/repo/data/manuscript-displays.json'))['displays']
    meta = {r['id']: r for r in steps + disp}
    lp = f'{S}/lead/sample.json'
    lead = json.load(open(lp))['records'] if os.path.exists(lp) else {}
    # the opus re-check of closeMatch records whose notes name another route (prompted by the sample)
    cp = f'{S}/lead/closecheck.json'
    review = json.load(open(cp))['records'] if os.path.exists(cp) else {}
    final = {}
    stats = collections.Counter()
    for B in batches:
        b = B['id']
        M, V, J = (load(f'{S}/{d}/{b}.json') for d in ('map', 'verify', 'judge'))
        cmp_path = f'{S}/compare/{b}.json'
        C = json.load(open(cmp_path)) if os.path.exists(cmp_path) else None
        for rid in B['records']:
            m = (M or {}).get(rid)
            v = (V or {}).get(rid)
            j = (J or {}).get(rid)
            c = C['records'].get(rid) if C else None
            ver = {'batch': b, 'steps': [s for s, x in (('mapper', m), ('verifier', v), ('judge', j)) if x],
                   'mapper': m and m.get('relation'), 'verifier': v and v.get('relation')}
            if c:
                ver['agreed'] = c['agreed']
                if not c['agreed']:
                    ver['disagreement'] = c.get('why')
            pick = None
            if j:
                pick, ver['judge'] = j, j.get('relation')
                ver['ruling'] = j.get('ruling')
                ver['source'] = 'judge'
            elif c and c['agreed']:
                pick, ver['source'] = m, 'mapper+verifier'
            ver['complete'] = pick is not None
            if pick and rid in lead:
                ver['lead_sample'] = {'was': pick.get('relation'), 'ruling': lead[rid]['relation']}
                pick = dict(pick, relation=lead[rid]['relation'], note=lead[rid]['note'])
                ver['source'] += '+lead'
            elif pick and rid in review and pick.get('relation') == 'closeMatch':
                ver['close_review'] = {'was': 'closeMatch', 'ruling': review[rid]['relation']}
                pick = dict(pick, relation=review[rid]['relation'], note=review[rid]['note'])
                ver['source'] += '+review'
            rel = pick and pick.get('relation')
            rec = {'id': rid}
            mt = meta[rid]
            if mt.get('item'):
                rec['item'] = mt['item']
                rec['step'] = mt['step']
            else:
                rec['context'] = mt['context']
                rec['enclosing'] = mt.get('enclosing')
            rec.update({'kind': 'proof_step' if mt.get('item') else 'display', 'relation': rel, 'class': CLASS[rel]})
            if pick:
                rec['ends'] = [end(e, rel) for e in pick.get('ends', [])]
                rec['note'] = pick.get('note')
                if rel == 'noMatch':
                    rec['searched'] = pick.get('searched')
                rec['confidence'] = pick.get('confidence')
                # a judge keeps only the claims it checked; on agreement either agent's claim counts
                te = j.get('text_error') if j else (m.get('text_error') or (v or {}).get('text_error'))
                if te:
                    sk = []
                    for k in (1, 2):
                        p = f'{S}/skeptic/{slug(rid)}-{k}.json'
                        if os.path.exists(p):
                            sk.append(json.load(open(p)))
                    rec['text_error'] = {'claim': te.get('claim'), 'evidence': te.get('evidence'),
                                         'skeptics': [{'verdict': s.get('verdict'), 'why': s.get('why')} for s in sk],
                                         'confirmed': len(sk) == 2 and all(s.get('verdict') == 'confirmed' for s in sk)}
            rec['verification'] = ver
            final[rid] = rec
            stats[(rec['kind'], rec['class'])] += 1
    for kind, name in (('proof_step', 'steps'), ('display', 'displays')):
        recs = [r for r in final.values() if r['kind'] == kind]
        counts = collections.Counter(r['relation'] or 'unjudged' for r in recs)
        json.dump({'about': f'Lean ends of every {"proof step" if kind == "proof_step" else "display outside a proof"} of [M] '
                            '(data/manuscript-' + name + '.json), by docs/steps-mapping.md; classes by docs/coverage.md.',
                   'lean': {'repository': REPO_URL, 'version': PIN},
                   'source_pin': '1a47ac9007f80d37832291cc12d578874ff6bef9',
                   'provenance': 'machine: a sonnet mapper and a sonnet verifier per batch, independently; an opus judge on '
                                 'disagreement and on one in five agreed noMatch records; two opus skeptics per claim that '
                                 'the text is wrong; no person reviewed',
                   'counts': dict(sorted(counts.items())),
                   'records': recs},
                  open(f'{work}/repo/data/manuscript-{name}-mapping.json', 'w'), ensure_ascii=False, indent=1)
    for k, n in sorted(stats.items()):
        print(k, n)


if __name__ == '__main__':
    main(sys.argv[1])
