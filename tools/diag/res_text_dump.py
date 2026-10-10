# -*- coding: utf-8 -*-
r"""zh_res_dump.py — 把现役 ISO 的 EN_STRINGS.RES 按 charset 解码成可读中文 (会话工具, 不入库)

用法:
  python work/_dis/zh_res_dump.py menu                # 全量列出 MENU 份
  python work/_dis/zh_res_dump.py gr G12.I011         # GR 份, 只列指定 key
  python work/_dis/zh_res_dump.py menu "*I797*"       # 通配
  python work/_dis/zh_res_dump.py menu --raw G58.I568 # 附带原始字节
ISO 缺省 = work/builds/GR_ZH72/GR_ZH72.iso (--iso 覆盖)
"""
import argparse
import fnmatch
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
from lz77_decode import lzo1x_decompress  # noqa: E402

MENU_LBA, GR_LBA = 776286, 19175
ENTRY = {'menu': (MENU_LBA, 25), 'gr': (GR_LBA, 902)}
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')


def entry_slot(f, lba, idx):
    f.seek(lba * 2048 + 0x830 + 48 * idx + 24)
    stored, real, off = struct.unpack('<III', f.read(12))
    return stored, real, off


def decode_blob(fr):
    p, out = 0, []
    while p + 8 <= len(fr):
        plen, o = struct.unpack_from('<II', fr, p)
        if plen == 0 and o == 0:
            break
        dec, err, _ = lzo1x_decompress(fr[p + 8:p + 8 + plen], out_size=o)
        if err is not None or len(dec) != o:
            break
        out.append(dec)
        p += 8 + plen
    return b''.join(out)


def parse_groups(data):
    p = 0
    ng = struct.unpack_from('<I', data, p)[0]
    p += 4
    groups = []
    for g in range(ng):
        if g > 0:
            p += 4
        cnt = struct.unpack_from('<I', data, p)[0]
        p += 4
        st = []
        for _ in range(cnt):
            ln = struct.unpack_from('<I', data, p)[0]
            p += 4
            st.append(bytes(data[p:p + ln]))
            p += ln + 2
        groups.append(st)
    return groups


class Dec:
    def __init__(self, path):
        cs = json.load(open(path, encoding='utf-8'))
        self.codes = {int(v): k for k, v in cs['codes'].items()}
        self.pairs = {tuple(v): k for k, v in cs['pair_of'].items()}
        self.leads = {v[0] for v in cs['pair_of'].values()}

    def text(self, raw):
        out, i = [], 0
        while i < len(raw):
            b = raw[i]
            if b in self.leads and i + 1 < len(raw) and (b, raw[i + 1]) in self.pairs:
                out.append(self.pairs[(b, raw[i + 1])])
                i += 2
            elif b in self.codes:
                out.append(self.codes[b])
                i += 1
            elif 0x20 <= b < 0x7F:
                out.append(chr(b))
                i += 1
            else:
                out.append('[%02X]' % b)
                i += 1
        return ''.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target', choices=('menu', 'gr'))
    ap.add_argument('pattern', nargs='?', default='*')
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH72', 'GR_ZH72.iso'))
    ap.add_argument('--raw', action='store_true')
    a = ap.parse_args()
    lba, idx = ENTRY[a.target]
    f = open(a.iso, 'rb')
    stored, real, off = entry_slot(f, lba, idx)
    f.seek(lba * 2048 + off)
    slot = f.read(stored)
    exp = decode_blob(slot)
    print('# %s #%d stored=%d real=%d off=0x%X 解码得 %d B (期望 %d)'
          % (a.target, idx, stored, real, off, len(exp), real), file=sys.stderr)
    if len(exp) < real:
        exp = exp + b'\x00' * (real - len(exp))
    groups = parse_groups(exp)
    dec = Dec(CHARSET)
    n = 0
    for gi, st in enumerate(groups):
        for ii, raw in enumerate(st):
            key = 'G%02d.I%03d' % (gi + 1, ii)
            if not fnmatch.fnmatch(key, a.pattern):
                continue
            t = dec.text(raw)
            if a.raw:
                print('%s len=%-4d %s\n    raw=%s' % (key, len(raw), t, raw.hex(' ')))
            else:
                print('%s len=%-4d %s' % (key, len(raw), t))
            n += 1
    print('# 命中 %d 条' % n, file=sys.stderr)


if __name__ == '__main__':
    main()
