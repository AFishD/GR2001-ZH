# -*- coding: utf-8 -*-
"""Baseline sanity: can the CURRENT charset JSON reproduce every on-disc text byte?

Why this matters for round68: the charset JSON (tools/font_pipeline/data/
charset_compiled_zh16.json) is being rewritten **right now** by the parallel
GR_ZH113 font-expansion task (pair count went 1175 -> 1504 while this round ran).
The titles I rewrite reuse characters that already exist in the on-disc corpus, so
if the JSON still round-trips the whole corpus byte-for-byte, then reusing those
characters cannot silently change their glyph.

Usage: python corpus_roundtrip.py [ISO]
"""
import csv
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                               # noqa: E402

ISO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    REPO, 'work', 'builds', 'GR_ZH111', 'GR_ZH111.iso')
TABLES = os.path.join(REPO, 'work', 'builds', 'GR_ZH111', 'text')
OUT = os.path.join(HERE, 'corpus_roundtrip.txt')


def main():
    cs = T.Charset()
    iso = T.Iso(ISO)
    # ── blobs ──
    blobs = {}
    for key, spec in (('SFXML', T.RES['SFXML']['copies'][0]),
                      ('LANG', T.RES['LANG']['copies'][0])):
        img, lba, idx, tag = spec[:4]
        e = iso.img_entry(lba, idx)
        raw = iso.read(e['iso_off'], e['stored'])
        blobs[key] = (tag, b''.join(s[0] for s in T.lzo_subs(raw)))
    lines = ['# charset JSON: single=%d pair=%d' % (len(cs.enc_single), len(cs.enc_pair))]
    lines.append('# ISO: %s' % os.path.relpath(ISO, REPO).replace('\\', '/'))
    n_ok = n_bad = n_skip = 0
    bad = []
    for fn in ('GR_ZH111_text_long.csv', 'GR_ZH111_text_long_nowrap.csv',
               'GR_ZH111_text_short.csv'):
        p = os.path.join(TABLES, fn)
        with io.open(p, 'r', encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            res = (r.get('resource') or '').strip()
            tag, blob = blobs.get(res, (None, None))
            if tag is None:
                n_skip += 1
                continue
            off = int(r['offset'])
            ln = int(r['len_bytes'])
            want = blob[off:off + ln]
            try:
                got = T.cell_to_bytes_text(r['text_zh'] or '', cs, {})
            except Exception as ex:                                   # noqa: BLE001
                n_bad += 1
                bad.append((r['id'], 'EXC %s' % ex))
                continue
            if got == want:
                n_ok += 1
            else:
                n_bad += 1
                if len(bad) < 20:
                    bad.append((r['id'], 'bytes differ: disc=%s json=%s'
                                % (want[:24].hex(), got[:24].hex())))
    lines.append('# rows round-tripped OK : %d' % n_ok)
    lines.append('# rows MISMATCH          : %d' % n_bad)
    lines.append('# rows skipped (unknown resource): %d' % n_skip)
    for (rid, why) in bad:
        lines.append('   %s  %s' % (rid, why))
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('\n'.join(lines[:6]))
    print('wrote', OUT)
    return 0 if n_bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
