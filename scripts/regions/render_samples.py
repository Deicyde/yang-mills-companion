"""Draw the regions of regions.json on rendered pages of main.pdf, for a visual check.

Copied from the ternary Goldbach companion's render_samples.py; standard library and poppler's
pdftoppm.  Each region is outlined, red for a theorem-like item and blue for a display.

Usage: python3 -I render_samples.py <main.pdf> <regions.json> <out dir> <page> [<page> ...]
"""
import json
import os
import struct
import subprocess
import sys
import tempfile
import zlib

DPI = 100
COLORS = {'Eq': (40, 90, 220)}


def read_ppm(path):
    data = open(path, 'rb').read()
    parts, pos = [], 0
    while len(parts) < 4:
        while data[pos:pos + 1].isspace():
            pos += 1
        end = pos
        while not data[end:end + 1].isspace():
            end += 1
        parts.append(data[pos:end])
        pos = end
    w, h = int(parts[1]), int(parts[2])
    return w, h, bytearray(data[pos + 1:pos + 1 + 3 * w * h])


def write_png(path, w, h, px):
    raw = b''.join(b'\x00' + bytes(px[3 * w * r:3 * w * (r + 1)]) for r in range(h))
    chunk = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def rect(px, w, h, x0, y0, x1, y1, color, t=2):
    for y in range(max(0, y0), min(h, y1 + 1)):
        for x in range(max(0, x0), min(w, x1 + 1)):
            if x - x0 < t or x1 - x < t or y - y0 < t or y1 - y < t:
                i = 3 * (w * y + x)
                px[i:i + 3] = bytes(color)


def main():
    pdf, reg_path, out, pages = sys.argv[1], sys.argv[2], sys.argv[3], [int(p) for p in sys.argv[4:]]
    items = json.load(open(reg_path))['items']
    os.makedirs(out, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        for p in pages:
            stem = os.path.join(t, f'p{p}')
            subprocess.run(['pdftoppm', '-r', str(DPI), '-f', str(p), '-l', str(p), '-singlefile', pdf, stem], check=True)
            w, h, px = read_ppm(stem + '.ppm')
            for iid, regs in items.items():
                color = COLORS.get(iid.split()[0], (210, 30, 30))
                for r in regs:
                    if r['page'] != p:
                        continue
                    x, y, rw, rh = r['rect']
                    rect(px, w, h, int(x * w), int(y * h), int((x + rw) * w), int((y + rh) * h), color)
            write_png(os.path.join(out, f'page-{p:03d}.png'), w, h, px)
            print('wrote', p)


main()
