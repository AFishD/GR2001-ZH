# -*- coding: utf-8 -*-
r"""hashr_probe_odd.py — 查 `0xA1..gate` 里"配不出对偶码"的前导字节到底是什么 (只读)。

用法: python work/builds/GR_HASHR/tools/hashr_probe_odd.py
"""
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                       # noqa: E402
import migrate_legacy as ML                                              # noqa: E402

K2 = os.path.join(REPO, 'work', 'builds', 'GR_FA2400_K2', 'GR_FA2400_K2.iso')
BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
CS_BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82',
                       'charset_before_r82.json')


def cs_load(path):
    j = json.load(io.open(path, encoding='utf-8'))
    return ({ch: tuple(v) for ch, v in j['pair_of'].items()},
            {tuple(v): ch for ch, v in j['pair_of'].items()})


def probe(label, iso_path, cs_path):
    pair_of, pair_dec = cs_load(cs_path)
    iso = T.Iso(iso_path)
    gate = T.read_decode_gate(iso)
    print('=' * 100)
    print('%s  gate=0x%02X' % (label, gate))
    ctx = collections.Counter()
    firsts = {}
    for (kind, img, lba, idx, tag, why) in ML.CONTAINER_SPECS:
        e = iso.img_entry(lba, idx)
        raw = iso.read(e['iso_off'], e['stored'])
        blob = b''.join(s[0] for s in T.lzo_subs(raw))
        c = dict(name=kind, tag=tag, blob=blob)
        ranges, used, info = ML.payload_ranges(c)
        for (s, ee) in ranges:
            pay = blob[s:ee]
            i, n = 0, len(pay)
            while i < n:
                b = pay[i]
                if T.LEAD_LO <= b < gate:
                    t = pay[i + 1] if i + 1 < n else -1
                    if t is not None and (b, t) in pair_dec:
                        i += 2
                        continue
                    key = (tag, b)
                    ctx[key] += 1
                    if key not in firsts:
                        lo = max(0, i - 24)
                        hi = min(n, i + 24)
                        firsts[key] = (s + i, pay[lo:hi])
                    i += 1
                    continue
                i += 1
    for (tag, b), n in sorted(ctx.items(), key=lambda kv: (-kv[1], kv[0])):
        off, seg = firsts[(tag, b)]
        print('  %-24s 0x%02X x%-4d 首例 blob@0x%06X  …%s…'
              % (tag, b, n, off, seg.decode('latin-1').replace('\x00', '.')))
    iso.close()


if __name__ == '__main__':
    probe('GR_ZH113b', BASE, CS_BASE)
    probe('K2', K2, os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                 'charset_compiled_zh16.json'))
