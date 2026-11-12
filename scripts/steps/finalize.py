"""The displays and proof steps of [M], after long paragraphs are split.

New code.  A prose step of more than LONG printed lines (`steps_regions.py lines`, counted on the
committed PDF) is split at sentence boundaries: a split file groups its sentences, in order, into
steps of one claim each.  Every other step is one step.  Steps are renumbered within their item, in
the order of the proofs; each records the markers of its edges (`<paragraph key>:s`, `.i:s`, `.j:e`,
`:e`) and, when split, its sentence numbers.

The regions json (or -) gives each display its title, "Display, p. <page of its first region>",
and each record its pages.

Usage: python3 -I finalize.py <seg json> <lines json> <regions json or -> <out displays json> <out steps json> <splits json> ...
(data/manuscript-step-splits.json)
"""
import json
import sys

LONG = 10


def main():
    seg, lines = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
    regions = json.load(open(sys.argv[3]))['regions'] if sys.argv[3] != '-' else {}
    out_d, out_s = sys.argv[4], sys.argv[5]
    groups = {}
    for p in sys.argv[6:]:
        d = json.load(open(p))
        groups.update({k: v['groups'] for k, v in d['paragraphs'].items()} if 'paragraphs' in d else d)
    steps, n = [], {}
    split_paras = 0
    for s in seg['steps']:
        base = {k: s[k] for k in ('item', 'kind', 'section', 'proof_line')}
        if s['kind'] == 'display':
            n[s['item']] = n.get(s['item'], 0) + 1
            steps.append(dict(base, step=n[s['item']], env=s['env'], file=s['file'], line=s['line'],
                              end_line=s['end_line'], latex=s['latex'], key=s['key'], printed_lines=None,
                              paragraph=None, sentences=None, split=None))
            continue
        k, sents = s['key'], s['sentences']
        pl = lines[k]['printed_lines']
        if pl > LONG:
            g = groups[k]
            flat = [i for grp in g for i in grp]
            if flat != list(range(1, len(sents) + 1)) or any(grp != list(range(grp[0], grp[-1] + 1)) for grp in g):
                sys.exit(f'bad split of {k}: {g}')
            split_paras += 1
        else:
            g = [list(range(1, len(sents) + 1))]
        for grp in g:
            i, j = grp[0], grp[-1]
            a = f'{k}:s' if i == 1 else f'{k}.{i}:s'
            b = f'{k}:e' if j == len(sents) else f'{k}.{j}:e'
            lat = s['latex'] if len(g) == 1 else ' '.join(sents[q - 1]['latex'] for q in grp)
            n[s['item']] = n.get(s['item'], 0) + 1
            steps.append(dict(base, step=n[s['item']], file=sents[i - 1]['start']['file'],
                              line=sents[i - 1]['start']['line'], end_line=sents[j - 1]['end']['line'],
                              latex=lat, key=k, markers=[a, b], printed_lines=pl if len(g) == 1 else None,
                              paragraph=k, sentences=[i, j] if len(g) > 1 else None,
                              split='sentence groups by a sonnet subagent' if len(g) > 1 else None))
    for s in steps:
        s['id'] = f'{s["item"]} step {s["step"]}'
        regs = regions.get(s['id'])
        s['pages'] = sorted({r['page'] for r in regs}) if regs else None
    order = ['id', 'item', 'step', 'kind', 'env', 'section', 'file', 'line', 'end_line', 'pages', 'printed_lines',
             'paragraph', 'sentences', 'split', 'key', 'markers', 'proof_line', 'latex']
    steps = [{k: s[k] for k in order if k in s} for s in steps]
    proofs = seg['proofs']
    for pr in proofs:
        pr['steps'] = [s['step'] for s in steps if s['item'] == pr['item'] and s['proof_line'] == pr['line']]
    src = seg['source']
    json.dump(dict(source=src, long_paragraph_lines=LONG, split_paragraphs=split_paras, proofs=proofs, steps=steps,
                   dropped_pieces=seg['dropped_pieces']),
              open(out_s, 'w'), indent=1, ensure_ascii=False)
    displays = []
    for d in seg['displays']:
        regs = regions.get(d['id'])
        page = regs[0]['page'] if regs else None
        displays.append(dict(id=d['id'], kind='display', title=f'Display, p. {page}' if page else 'Display',
                             env=d['env'], section=d['section'], context=d['context'], enclosing=d['enclosing'],
                             file=d['file'], line=d['line'], end_line=d['end_line'],
                             pages=sorted({r['page'] for r in regs}) if regs else None, key=d['key'], latex=d['latex']))
    json.dump(dict(source=src, prose_outside_proofs=seg['prose_outside_proofs'], displays=displays),
              open(out_d, 'w'), indent=1, ensure_ascii=False)
    print(len(displays), 'displays;', len(steps), 'steps;', split_paras, 'paragraphs split')


main()
