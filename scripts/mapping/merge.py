#!/usr/bin/env python3
"""Merge the campaign's outputs into data/mapping.json.

Per item, in order of precedence:
- the judge's record, when the mapper and verifier disagreed and a judge ruled;
- the mapper's record, when mapper and verifier agree (their non-key links are united);
- no verdict, when a step is missing.
A final status that is a finding (weaker, missing-hypothesis, differs, no-match) is
`confirmed` only when both skeptics ran and neither refuted it. When both refute it and
propose non-finding statuses, the weaker of the two replaces it. When one refutes it, the status
becomes `unclear` (contested). The finding is then `unconfirmed`.

Last, data/corrections.json applies the re-judgments made after an independent review (session 5):
per item a new status, note, links or roles. A finding it keeps or revises is `confirmed` only with two
new skeptic verdicts that neither refutes; a finding whose item it re-judges as a non-finding is
`withdrawn`.
"""
import json, os, re

# The workspace holding repo/, src/, lean/, scratch/ and out/: $YM_WORK, else this repository's parent.
HOME = os.environ.get('YM_WORK') or os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
S = f'{HOME}/scratch'
REPO = f'{HOME}/repo'
LEAN_PIN = open(f'{HOME}/out/LEAN_PIN').read().split()[0]
FINDINGS = {'weaker', 'missing-hypothesis', 'differs', 'no-match'}
# non-finding statuses from the least to the most a relation claims
WEAKEST = ['not-formalized-not-needed', 'inlined', 'parts', 'definition-close', 'close',
           'definition-match', 'exact', 'stronger']
KEY_REL = {
    'exact': 'exactMatch', 'definition-match': 'exactMatch',
    'close': 'closeMatch', 'definition-close': 'closeMatch',
    'stronger': 'broadMatch', 'weaker': 'narrowMatch', 'missing-hypothesis': 'narrowMatch',
    'parts': 'hasPart', 'inlined': 'relatedMatch', 'differs': 'relatedMatch',
    'no-match': 'noMatch', 'not-formalized-not-needed': 'noMatch',
}


def fname(item):
    return re.sub(r'[^A-Za-z0-9._-]', '', item.replace(' ', '_'))


def load(kind, b):
    p = f'{S}/{kind}/{b}.json'
    if not os.path.exists(p):
        return None
    try:
        return {i['id']: i for i in json.load(open(p))['items']}
    except Exception:
        return None


NORM = {'definition-match': 'exact', 'definition-close': 'close'}


def same_status(a, c):
    return NORM.get(a['status'], a['status']) == NORM.get(c['status'], c['status'])


def keys(i):
    return sorted({l['decl'] for l in i.get('lean', []) if l.get('role') == 'key'})


def agree(a, c):
    ka, kc = set(keys(a)), set(keys(c))
    return same_status(a, c) and (not (ka or kc) or bool(ka & kc))


def unite(a, c):
    seen = {(l['decl'], l['role']) for l in a.get('lean', [])}
    lean = list(a.get('lean', []))
    for l in c.get('lean', []):
        if l['decl'] not in {x['decl'] for x in lean}:
            lean.append(dict(l, from_verifier=True))
    return lean


def relations(rec):
    st = rec['status']
    for l in rec['lean']:
        if st == 'unclear':
            l.pop('relation', None)
        elif l['role'] == 'key' and st not in ('no-match', 'not-formalized-not-needed'):
            l['relation'] = KEY_REL[st]
        else:
            l['relation'] = 'relatedMatch'
    rec['relation'] = KEY_REL.get(st)


def correct(rec, ver, c):
    """Apply one entry of data/corrections.json to a merged record."""
    old = rec['status']
    if 'status' in c:
        rec['status'] = c['status']
    if 'note' in c:
        rec['note'] = c['note']
    drop = set(c.get('drop_links', []))
    rec['lean'] = [l for l in rec['lean'] if l['decl'] not in drop]
    for l in rec['lean']:
        if l['decl'] in c.get('roles', {}):
            l['role'] = c['roles'][l['decl']]
    have = {l['decl'] for l in rec['lean']}
    for l in c.get('add_links', []):
        if l['decl'] in have:
            next(x for x in rec['lean'] if x['decl'] == l['decl'])['role'] = l['role']
        else:
            rec['lean'].append({k: l[k] for k in ('decl', 'role', 'where', 'note') if k in l})
    ver['corrected'] = {'kind': c['kind'], 'from': old, 'source': c['source'], 'why': c['why']}
    if 'skeptics' not in c and rec['status'] == old:
        pass  # the verdict stands: only its note or links change
    elif rec['status'] in FINDINGS:
        sk = c.get('skeptics', [])
        ok = len(sk) == 2 and not any(s.get('refuted') for s in sk)
        rec['finding'] = {'claim': rec['status'], 'confirmed': ok}
        if ok:
            rec['finding']['skeptic_notes'] = [s['reason'] for s in sk]
        ver['claimed'] = rec['status']
        ver['finding'] = 'confirmed' if ok else 'unconfirmed'
        ver['skeptics'] = [{'refuted': bool(s.get('refuted')), 'status': s.get('status'), 'reason': s.get('reason')}
                           for s in sk] or ver.get('skeptics', [])
    elif rec.get('finding'):
        rec['finding'] = {'claim': rec['finding']['claim'], 'confirmed': False, 'withdrawn': True}
        ver['finding'] = 'withdrawn'
    if (rec.get('finding') or {}).get('confirmed') and 'quote' in c:
        rec['finding']['quote'] = ' '.join(c['quote'].split())


def main():
    corrections = json.load(open(f'{REPO}/data/corrections.json'))['items']
    items = json.load(open(f'{REPO}/data/items.json'))['items']
    batches = json.load(open(f'{REPO}/data/batches.json'))['batches']
    batch_of = {i: b['id'] for b in batches for i in b['items']}
    cache = {}
    out = []
    for it in items:
        iid = it['id']
        b = batch_of[iid]
        if b not in cache:
            cache[b] = {k: load(k, b) for k in ('map', 'verify', 'judge')}
        m, v, j = (cache[b][k] and cache[b][k].get(iid) for k in ('map', 'verify', 'judge'))
        ver = {'batch': b, 'mapper': m['status'] if m else None, 'verifier': v['status'] if v else None}
        rec = None
        if m and v:
            ver['agreed'] = agree(m, v)
            if ver['agreed']:
                rec = dict(m, lean=unite(m, v))
                ver['source'] = 'mapper+verifier'
            elif j:
                rec = dict(j)
                ver['judge'] = j['status']
                ver['source'] = 'judge'
        if rec is None:
            out.append({'id': iid, 'status': None, 'relation': None, 'lean': [],
                        'note': 'Not yet judged', 'verification': dict(ver, complete=False)})
            continue
        rec = {k: rec[k] for k in ('status', 'lean', 'note', 'step', 'searched', 'confidence') if k in rec}
        rec['lean'] = [{k: l[k] for k in ('decl', 'role', 'where', 'note', 'from_verifier') if k in l}
                       for l in rec.get('lean', [])]
        if rec['status'] in FINDINGS:
            sk = []
            for n in (1, 2):
                p = f'{S}/skeptic/{fname(iid)}-{n}.json'
                if os.path.exists(p):
                    try:
                        sk.append(json.load(open(p)))
                    except Exception:
                        pass
            ver['skeptics'] = [{'refuted': bool(s.get('refuted')), 'status': s.get('status'),
                                'reason': s.get('reason')} for s in sk]
            ver['claimed'] = rec['status']
            if len(sk) == 2 and not any(s.get('refuted') for s in sk):
                ver['finding'] = 'confirmed'
                rec['finding'] = {'claim': rec['status'], 'confirmed': True,
                                  'skeptic_notes': [s.get('reason') for s in sk]}
            else:
                ver['finding'] = 'unconfirmed' if len(sk) == 2 else 'skeptics pending'
                rec['finding'] = {'claim': rec['status'], 'confirmed': False}
                ref = [s for s in sk if s.get('refuted')]
                if len(sk) == 2 and len(ref) == 2 and all(s.get('status') in WEAKEST for s in ref):
                    # both refute: take the weaker of the two proposed statuses
                    pick = min(ref, key=lambda s: WEAKEST.index(s['status']))
                    rec['status'] = pick['status']
                    if pick.get('lean'):
                        rec['lean'] = [l for l in pick['lean'] if l.get('role') in ('key', 'attributed', 'support', 'helper')]
                    sent = re.split(r'(?<=\.)\s+', (pick.get('reason') or '').strip())
                    rec['note'] = ' '.join(sent[:2]) or rec['note']
                    ver['source'] += '+skeptics'
                elif len(sk) == 2 and len(ref) == 1:
                    # contested: one skeptic refutes; claim neither the finding nor the refutation
                    rec['status'] = 'unclear'
                    sent = re.split(r'(?<=\.)\s+', (ref[0].get('reason') or '').strip())
                    rec['note'] = ('Contested: one skeptic upholds the claimed ' + ver['claimed'] +
                                   ', the other refutes it: ' + ' '.join(sent[:1]))
                    rec['lean'] = rec['lean'] + [l for l in (ref[0].get('lean') or [])
                                                 if l.get('decl') not in {x['decl'] for x in rec['lean']}
                                                 and l.get('role') in ('key', 'attributed', 'support', 'helper')]
                    ver['source'] += '+skeptics'
                    rec['finding']['refuted'] = True
        if iid in corrections:
            correct(rec, ver, corrections[iid])
        relations(rec)
        ver['complete'] = rec['status'] not in FINDINGS or ver.get('finding') in ('confirmed', 'unconfirmed')
        rec['verification'] = ver
        out.append({'id': iid, **rec})
    meta = {'lean': {'repository': 'https://github.com/yang-mills-group/OpenAI-YM-20261028', 'version': LEAN_PIN},
            'source_pin': open(f'{HOME}/out/SRC_PIN').read().split()[0],
            'taxonomy': 'docs/taxonomy.md',
            'provenance': 'machine: mapper and verifier agents per batch, a judge on disagreement, two skeptics per claimed finding; no person reviewed',
            'counts': {}}
    for r in out:
        meta['counts'][r['status'] or 'not yet judged'] = meta['counts'].get(r['status'] or 'not yet judged', 0) + 1
    json.dump({**meta, 'items': out}, open(f'{REPO}/data/mapping.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(meta['counts']))


if __name__ == '__main__':
    main()
