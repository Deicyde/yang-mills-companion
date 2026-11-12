"""Write a pdfTeX map file that gives every EC/TC font (jknappen TFM metrics) a Latin Modern Type 1
outline in the same encoding.

New code.  [M] is set in T1 encoding with microtype's font expansion, which pdfTeX allows only for
fonts mapped to Type 1 files; this host has the EC metrics but not cm-super's outlines.  Line
breaking and glyph positions come from the TFM metrics alone, so the layout is that of a cm-super
build; only the drawn glyph shapes differ.

Usage: python3 -I ecmap.py <out map>
"""
import os
import subprocess
import sys

SHAPES = {'rm': 'lmr10', 'bx': 'lmbx10', 'ti': 'lmri10', 'sl': 'lmro10', 'it': 'lmtti10', 'tt': 'lmtt10',
          'cc': 'lmcsc10', 'sc': 'lmcsc10', 'bi': 'lmbxi10', 'ss': 'lmss10', 'si': 'lmsso10', 'sx': 'lmssbx10',
          'bl': 'lmbxo10', 'st': 'lmtt10', 'vt': 'lmvtt10', 'vi': 'lmvtto10'}
ENC = {'ec': ('lm-ec.enc', 'enclmec'), 'tc': ('lm-ts1.enc', 'enclmts1')}


def main():
    tfm = subprocess.run(['kpsewhich', 'ecrm1000.tfm'], capture_output=True, text=True).stdout.strip()
    lines = []
    for f in sorted(os.listdir(os.path.dirname(tfm))):
        name = f[:-4]
        if not f.endswith('.tfm') or name[:2] not in ENC or not name[4:].isdigit():
            continue
        pfb = SHAPES.get(name[2:4], 'lmr10')
        enc, vec = ENC[name[:2]]
        lines.append(f'{name} {pfb.upper()} "{vec} ReEncodeFont" <{enc} <{pfb}.pfb')
    open(sys.argv[1], 'w').write('\n'.join(lines) + '\n')


main()
