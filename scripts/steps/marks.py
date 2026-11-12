"""Insert the position markers of regionmarks-steps.tex into a scratch copy of [M]'s source.

New code.  For every unnumbered display (`seg.json` displays and display steps) it writes
`\\rmnext{<key>}` right before the environment, which names the display's begin and end markers;
the macro adds no node.  For every prose step it writes `\\rmS{<key>}` before its first character
and `\\rmE{<key>}` after its last, and at every sentence boundary inside it
`\\rmE{<key>.<i>}` after sentence i's closing punctuation and `\\rmS{<key>.<i+1>}` before the next
sentence's first character, so that any grouping of sentences into steps has its edges marked.
Columns are those of the source line (comments only ever cut a line's end).

Usage: python3 -I marks.py <seg json> <copy of manuscript dir>   (edits the copy in place)
"""
import collections
import json
import os
import sys


def main():
    seg, root = json.load(open(sys.argv[1])), sys.argv[2]
    ins = collections.defaultdict(list)     # file -> [(line, col, order, text)]

    def put(p, s, order):
        ins[p['file']].append((p['line'], p['col'], order, s))
    for d in seg['displays']:
        put(d['start'], f'\\rmnext{{{d["key"]}}}', 1)
    for s in seg['steps']:
        k = s['key']
        if s['kind'] == 'display':
            put(s['start'], f'\\rmnext{{{k}}}', 1)
            continue
        put(s['start'], f'\\rmS{{{k}}}', 1)
        sents = s['sentences']
        for i in range(len(sents) - 1):
            put(sents[i]['end'], f'\\rmE{{{k}.{i + 1}}}', 0)
            put(sents[i + 1]['start'], f'\\rmS{{{k}.{i + 2}}}', 1)
        put(s['end'], f'\\rmE{{{k}}}', 0)
    n = 0
    for f, lst in ins.items():
        p = os.path.join(root, f)
        lines = open(p, encoding='utf-8').read().split('\n')
        # right to left, so earlier columns stay valid; at one column an end goes before a start
        for line, col, order, s in sorted(lst, key=lambda t: (t[0], -t[1], -t[2])):
            t = lines[line - 1]
            lines[line - 1] = t[:col] + s + t[col:]
            n += 1
        open(p, 'w', encoding='utf-8').write('\n'.join(lines))
    print(n, 'markers in', len(ins), 'files')


main()
