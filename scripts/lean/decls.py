"""Declaration index of [L] (yang-mills-group/OpenAI-YM-20261028) from its source text.

New code over formal-companion's adapters: `leanparse.parse_file` gives every declaration with its
keyword, namespace, modifiers and docstring; `leansnippets.index_text` gives the statement snippet
(a theorem's statement through the `:=` of its proof, a definition whole, capped) and the
auto-generated projections of structure fields.  A name both give is one row; a field projection
only `leansnippets` gives is a row of kind `field`; an anonymous `example` or `instance` gets
`leanparse`'s synthetic id `<kind>@<file>:<line>`.  The source is read, not built.

Both parsers read a command only at the start of a line.  [L] also starts commands after one space
(16 declarations, 5 `end`s) and after a same-line `omit ... in` (or `include`, `open`,
`set_option`, `variable`) prefix (99 declarations); outside comments, such a line is given to the
parsers with the space or prefix removed, so line numbers are kept and the snippet lacks the
prefix.  Two declarations of one name (private ones in different files) are both kept.

The names Lean generates from a structure, class or inductive are added as rows with
`generated: true`: the constructor (`mk`, or the name before `::`), the parent projections
`toB` of `extends B`, the fields `leansnippets` skips (several in parentheses, `(i j : ℕ)`, one with
binders, `f x (h : p x) : T`, or a name outside ASCII, `cε : C`), and the constructors `| c` of an inductive.  `where`-clause auxiliaries of theorems and
definitions are not added.

Then the index is cross-checked with [M]'s `data/declaration-units.tsv` and with [L]'s compiled
inventory `verification/declaration-usage.tsv` (whose status, used, headline or outside, is
joined as `usage`), and [M]'s `data/key-statements.tsv` is joined onto it by name.

Usage: python3 -I decls.py <fc dir> <lean dir> <lean commit> <yang-mills-informalization dir> <out json> <out check json>
"""
import collections
import csv
import hashlib
import json
import os
import re
import sys


KW = r'(?:theorem|lemma|def|abbrev|structure|class|inductive|instance|example|opaque|axiom|namespace|end|section|mutual)'
MOD = r'(?:@\[[^\]]*\]\s*|(?:private|protected|noncomputable|nonrec|partial|unsafe|scoped|local)\s+)*'
PREFIX = re.compile(r'^(?:\s*(?:omit|include|open|set_option|variable)\b[^\n]*?\bin\s+)+(?=' + MOD + KW + r'\b)')
INDENT = re.compile(r'^[ \t]+(?=' + MOD + KW + r'\b)')


ID = r"[^\W\d][\w'!?]*"
# `(i j : T)` (or `[i : T]`, `{i j : T}`) declares fields i and j; `f x (h : p x) : T` declares f,
# with binders
FIELDS = re.compile(r'^([ \t]+)[(\[{⦃]((?:' + ID + r'\s+)*' + ID + r')\s*:(?!=)')
FIELD1 = re.compile(r'^([ \t]+)(' + ID + r')(?![\w\'!?.])(?!\s*::)(?!\s*:=)[^\n]*?:(?![:=])')


def normalize(text, depths_of):
    lines = text.split('\n')
    depths = depths_of(lines)
    changed = 0
    for i, line in enumerate(lines):
        if depths[i]:
            continue
        new = INDENT.sub('', PREFIX.sub('', line))
        if new != line:
            lines[i] = new
            changed += 1
    return '\n'.join(lines), changed


def module_of(rel):
    return rel[:-5].replace('/', '.')


def main():
    fc, lean, commit, src, out_path, check_path = sys.argv[1:7]
    sys.path.insert(0, os.path.join(fc, 'scripts'))
    from adapters import leanparse, leansnippets

    files = []
    for d, dirs, fs in os.walk(lean):
        dirs[:] = sorted(x for x in dirs if x not in ('.lake', '.git'))
        files += [os.path.relpath(os.path.join(d, f), lean) for f in sorted(fs) if f.endswith('.lean')]
    files.sort()
    rows, dup, normalized = {}, collections.Counter(), 0
    tmp = out_path + '.tmp.lean'
    extra = []
    for rel in files:
        text, changed = normalize(open(os.path.join(lean, rel), encoding='utf-8').read(), leanparse.comment_depths)
        normalized += changed
        open(tmp, 'w', encoding='utf-8').write(text)
        snips = leansnippets.index_text(text)
        decls = leanparse.parse_file(tmp, rel=rel)
        seen = set()
        for d in decls:
            name = d.full_name
            if name in rows:
                dup[name] += 1
                if (rows[name]['file'], rows[name]['line']) != (rel, d.line):
                    extra.append(dict(name=name, kind=d.kind, module=module_of(rel), file=rel, line=d.line,
                                      private=d.private, anonymous=d.anonymous,
                                      snippet=leanparse.signature(d.body)[:2000], duplicate=True))
                continue
            sn = snips.get(name)
            snippet = sn[1] if sn and sn[0] == d.line else leanparse.signature(d.body)[:2000]
            rows[name] = dict(name=name, kind=d.kind, module=module_of(rel), file=rel, line=d.line,
                              private=d.private, anonymous=d.anonymous, snippet=snippet)
            seen.add(name)
        for name, (line, snippet) in snips.items():
            if name in seen or name in rows:
                continue
            # a structure field's projection (or a declaration leanparse did not open)
            rows[name] = dict(name=name, kind='field' if snippet.startswith('structure ') and '\n  …\n' in snippet
                              else 'decl', module=module_of(rel), file=rel, line=line, private=False,
                              anonymous=False, snippet=snippet)

    os.remove(tmp)

    # generated names of structures, classes and inductives
    gen = 0
    struct_text = {}
    by_file = collections.defaultdict(list)
    for r in rows.values():
        if r['kind'] in ('structure', 'class', 'inductive'):
            by_file[r['file']].append(r)
    for rel, rs in by_file.items():
        lines = open(os.path.join(lean, rel), encoding='utf-8').read().split('\n')
        depths = leanparse.comment_depths(lines)
        for r in rs:
            i = r['line'] - 1
            end = leansnippets.declaration_end(lines, i)
            head = ' '.join(lines[i:end])
            struct_text[r['name']] = lines[i + 1:end]
            names = []
            if r['kind'] == 'inductive':
                for k in range(i, end):
                    m = re.match(r'^\s*\|\s*([A-Za-z_][\w\'!?]*)', lines[k])
                    if m and not depths[k]:
                        names.append((m.group(1), k))
            else:
                ctor = None
                for k in range(i + 1, end):
                    m = re.match(r'^\s+([A-Za-z_][\w\'!?]*)\s*::', lines[k])
                    if m and not depths[k]:
                        ctor = (m.group(1), k)
                names.append(ctor or ('mk', i))
                ext = re.search(r'\bextends\b(.*?)(?:\bwhere\b|:=|$)', head)
                if ext:
                    for part in re.split(r',(?![^()\[\]{}]*[)\]}])', ext.group(1)):
                        m = re.match(r'\s*(?:\w+\s*:\s*)?@?([A-Z][\w\'.]*)', part)
                        if m:
                            names.append(('to' + m.group(1).split('.')[-1], i))
                fields = []
                for k in range(i + 1, end):
                    m = FIELDS.match(lines[k]) or FIELD1.match(lines[k])
                    if m and not depths[k] and m.group(2) not in ('where', 'extends', 'deriving'):
                        fields.append((len(m.group(1)), k, m.group(2).split()))
                level = min((f[0] for f in fields), default=0)
                names += [(n, k) for ind, k, ns in fields if ind == level for n in ns]
            for n, k in names:
                full = r['name'] + '.' + n
                if full not in rows:
                    rows[full] = dict(name=full, kind='generated', module=r['module'], file=rel, line=k + 1,
                                      private=r['private'], anonymous=False,
                                      snippet=lines[k].strip()[:400], generated=True)
                    gen += 1

    # [M]'s tables
    units = {}
    with open(os.path.join(src, 'data', 'declaration-units.tsv'), encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE):
            units[r['declaration']] = r['unit']
    keys = collections.defaultdict(list)
    with open(os.path.join(src, 'data', 'key-statements.tsv'), encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE):
            keys[r['lean_name']].append(r)
    for name, r in rows.items():
        if name in units:
            r['unit'] = units[name]
        if name in keys:
            r['key_statements'] = [dict(number=k['number'], unit=k['unit'], importance=k['importance'],
                                        summary=k['summary'], link=k['link']) for k in keys[name]]

    # cross-check
    ours = set(rows)
    named = {n for n, r in rows.items() if not r['anonymous']}
    only_units = sorted(set(units) - ours)
    only_ours = sorted(named - set(units))

    def why_missing(n):
        last = n.split('.')[-1]
        if re.search(r'\._(?:proof|aux|lambda|unary|binary|eq|cstage|closed|spec|match|sunfold|unfold)', n) or \
                re.search(r'\.(?:match_|proof_|eq_|_private|_cstage|_unsafe_rec)\d*', n):
            return 'auxiliary (compiler or elaborator constant)'
        if last in ('have', 'let', 'exact', 'rw', 'apply', 'refine', 'change', 'filter_upwards', 'simp', 'intro',
                    'obtain', 'show', 'calc', 'by', 'fun', 'use', 'linarith', 'positivity', 'gcongr', 'constructor'):
            return 'a tactic word under a declaration (an artifact of the allocation\'s text parser)'
        if last in ('mk', 'rec', 'recOn', 'casesOn', 'noConfusion', 'noConfusionType', 'below', 'brecOn', 'binductionOn',
                    'ibelow', 'mk.injEq', 'injEq', 'inj', 'sizeOf_spec', 'ext', 'ext_iff', 'induct', 'eq_def'):
            return 'generated by a structure or inductive'
        if re.match(r'^(inst|instDecidable|instRepr|instInhabited|instBEq|instHashable)[A-Z]', last):
            return 'auto-named instance'
        parent = n.rsplit('.', 1)[0] if '.' in n else ''
        if parent in struct_text:
            binder = re.compile(r'^[ \t]+' + ID + r'\s[^:\n]*(?<![\w\'!?])' + re.escape(last) + r'(?![\w\'!?])')
            if any(binder.match(l) for l in struct_text[parent]):
                return 'a binder of a structure field, not a field (an artifact of the allocation\'s text parser)'
            return 'generated by a structure or inductive, not found by this index'
        if parent in rows:
            return 'under a declaration: a where-clause auxiliary'
        return 'not found in the source text'
    reasons = collections.Counter(why_missing(n) for n in only_units)
    samples = collections.defaultdict(list)
    for n in only_units:
        r = why_missing(n)
        if len(samples[r]) < 12:
            samples[r].append(n)
    ours_kinds = collections.Counter(rows[n]['kind'] for n in only_ours)
    ours_samples = collections.defaultdict(list)
    for n in only_ours:
        k = rows[n]['kind'] + (' private' if rows[n]['private'] else '')
        if len(ours_samples[k]) < 8:
            ours_samples[k].append(n)
    key_missing = sorted(n for n in keys if n not in rows)
    key_line_mismatch = []
    for n, ks in keys.items():
        if n in rows:
            for k in ks:
                m = re.search(r'/blob/[0-9a-f]+/(.*)#L(\d+)$', k['link'])
                if m and (m.group(1) != rows[n]['file'] or int(m.group(2)) != rows[n]['line']):
                    key_line_mismatch.append((n, k['link'], rows[n]['file'], rows[n]['line']))
    # [L]'s own compiled inventory: verification/declaration-usage.tsv (private names mangled as
    # _private.<module>.0.<name>), with the status of each declaration and its source line
    usage = {}
    modules = set()
    with open(os.path.join(lean, 'verification', 'declaration-usage.tsv'), encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE):
            n = r['declaration']
            m = re.match(r'_private\.' + re.escape(r['module']) + r'\.0\.(.*)$', n)
            usage[(m.group(1) if m else n, r['module'])] = r
            modules.add(r['module'])
    names_in_usage = {n for n, _ in usage}
    for r in list(rows.values()) + extra:
        u = usage.get((r['name'], r['module']))
        if u:
            r['usage'] = u['status']
        if r['module'] not in modules:
            r['compiled'] = False

    def usage_kind(n):
        last = n.split('.')[-1]
        if re.search(r'\._proof_\d|\._aux_|_macroRules_|_unexpand_|\.match_\d|\._unsafe_rec|\._cstage|\.eq_\d|'
                     r'\._sunfold|\.proof_\d|_flat_ctor|\._lambda|\._private\.|\.term|«|\._simp_|\._closed|_spec_\d|'
                     r'\.eq_def$|\.eq_unfold$|\._arg_|\.induct$|\._f$|\.fun_cases$|_auxLemma', n):
            return 'compiler or elaborator auxiliary'
        if last in ('mk', 'rec', 'recOn', 'casesOn', 'noConfusion', 'noConfusionType', 'below', 'brecOn', 'binductionOn',
                    'ibelow', 'injEq', 'inj', 'sizeOf_spec', 'ext', 'ext_iff', 'ctorIdx', 'toCtorIdx', 'ofNat',
                    'toNat', 'elim', 'ctorElim', 'ctorElimType') or re.search(r'\.mk\.\w+$', n):
            return 'generated by a structure or inductive'
        if last.startswith('inst'):
            return 'auto-named instance'
        if n.startswith('Vintage.'):
            return 'declared by the vintage command (YM/UVExtension/Orchard/Barrel.lean), no source text'
        if n.split('.')[0] in ('Mathlib', 'Lean', 'Std', 'Init'):
            return 'outside the project'
        parent = n.rsplit('.', 1)[0]
        if parent in struct_text:
            return 'a structure field or constructor not found by this index'
        if parent in rows:
            return 'under a declaration: a where-clause auxiliary'
        return 'other'
    ours_keys = {(r['name'], r['module']) for r in list(rows.values()) + extra}
    u_only = sorted({n for (n, m) in set(usage) - ours_keys})
    u_only_set = set(u_only)
    u_reasons = collections.Counter(usage_kind(n) for n in u_only)
    u_samples = collections.defaultdict(list)
    for n in u_only:
        k = usage_kind(n)
        if len(u_samples[k]) < 12:
            u_samples[k].append(n)
    o_only = [n for n in ours if n not in names_in_usage]
    o_kinds = collections.Counter(rows[n]['kind'] + (' anonymous' if rows[n]['anonymous'] else '') for n in o_only)
    o_samples = collections.defaultdict(list)
    for n in sorted(o_only):
        k = rows[n]['kind'] + (' anonymous' if rows[n]['anonymous'] else '')
        if len(o_samples[k]) < 8:
            o_samples[k].append(n)
    line_same = line_doc = line_other = 0
    line_other_samples = []
    for r in list(rows.values()) + extra:
        u = usage.get((r['name'], r['module']))
        if not u or not u['source_line']:
            continue
        if int(u['source_line']) == r['line']:
            line_same += 1
        elif 0 < r['line'] - int(u['source_line']) <= 40:
            line_doc += 1       # the inventory gives the line of a docstring or attribute above
        else:
            line_other += 1
            if len(line_other_samples) < 12:
                line_other_samples.append((r['name'], r['file'], r['line'], u['source_line']))
    usage_check = dict(rows=len(usage), modules=len(modules),
                       files_not_compiled=sorted(rl for rl in files if module_of(rl) not in modules),
                       by_status=dict(collections.Counter(u['status'] for u in usage.values())),
                       in_both=len(ours_keys & set(usage)), only_in_usage=len(u_only), only_in_usage_by_kind=dict(u_reasons),
                       only_in_usage_samples=u_samples, only_in_index=len(o_only), only_in_index_by_kind=dict(o_kinds),
                       only_in_index_samples=o_samples,
                       used_or_headline_other=sorted({n for (n, m), u in usage.items() if n in u_only_set
                                                      and u['status'] != 'outside' and usage_kind(n) == 'other'}),
                       line_same=line_same, line_within_40_below=line_doc, line_other=line_other,
                       line_other_samples=line_other_samples)
    check = dict(lean_commit=commit, files=len(files), rows=len(rows) + len(extra), names=len(rows),
                 lines_normalized=normalized, duplicate_rows=len(extra), generated_rows=gen,
                 by_kind=dict(collections.Counter(r['kind'] for r in rows.values())),
                 anonymous=sum(r['anonymous'] for r in rows.values()),
                 private=sum(r['private'] for r in rows.values()),
                 duplicate_names_skipped=dict(dup.most_common(20)), duplicate_names_total=sum(dup.values()),
                 units_rows=len(units), in_both=len(set(units) & ours),
                 only_in_units=len(only_units), only_in_units_by_reason=dict(reasons), only_in_units_samples=samples,
                 only_in_index=len(only_ours), only_in_index_by_kind=dict(ours_kinds), only_in_index_samples=ours_samples,
                 key_statements=sum(len(v) for v in keys.values()), key_names=len(keys),
                 key_names_missing=key_missing, key_link_mismatches=len(key_line_mismatch),
                 key_link_mismatch_samples=key_line_mismatch[:20], usage=usage_check)
    out = dict(lean=dict(repository='https://github.com/yang-mills-group/OpenAI-YM-20261028', commit=commit),
               method='source text, formal-companion adapters leanparse and leansnippets; not built',
               fields=['name', 'kind', 'module', 'file', 'line', 'private', 'anonymous', 'snippet', 'unit',
                       'key_statements', 'usage', 'compiled', 'duplicate', 'generated'],
               decls=sorted(list(rows.values()) + extra, key=lambda r: (r['file'], r['line'], r['name'])))
    s = json.dumps(out, ensure_ascii=False, indent=0)
    open(out_path, 'w', encoding='utf-8').write(s)
    check['bytes'] = len(s.encode())
    check['sha256'] = hashlib.sha256(s.encode()).hexdigest()
    json.dump(check, open(check_path, 'w'), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in check.items() if 'samples' not in k and k not in ('key_names_missing', 'usage')},
                     indent=1))
    print(json.dumps({k: v for k, v in usage_check.items() if 'samples' not in k}, indent=1))
    print('key names missing', key_missing[:20])


main()
