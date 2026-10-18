# -*- coding: utf-8 -*-
r"""rb_keycov.py -- 只读：对 K2 拼装盘里**关键条目**逐条给「K2 dump / 全 dump 并集」覆盖率，
并列出可提供该区间的其它转储名（判断缺件能否旁证取回）。

用法: python rb_keycov.py [--iso <K2 拼装盘>] [--out <txt>]
"""
import argparse
import glob
import io
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402

SEC = 2048
DUMPDIR = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'PCSX2', 'cdvd-dump')
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def load_idx(path):
    n = os.path.getsize(path)
    with open(path, 'rb') as f:
        magic, bsz, total, zero = struct.unpack('<4sIII', f.read(16))
        if magic != b'BDV2':
            return None
        cnt, rem = divmod(n - 16, 4 + SEC)
        if rem:
            return None
        idx = set()
        for i in range(cnt):
            f.seek(16 + i * (4 + SEC))
            idx.add(struct.unpack('<I', f.read(4))[0])
    return idx


KEYS_MENU = ('COMMON.PAK', 'FONT.RES', 'EN_STRINGS.RES', 'EN_SPECIAL_FEATURE.XML',
             'MENU.PAK', 'LOADING.PAK')
KEYS_GR = ('COMMON.PAK', 'FONT.RES', 'EN_STRINGS.RES')


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_REBUILD',
                                                  '_probe_k2only.iso'))
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)

    dumps = {}
    for d in sorted(glob.glob(os.path.join(DUMPDIR, '*.dump'))):
        i = load_idx(d)
        if i:
            dumps[os.path.basename(d)] = i
    union = set()
    for i in dumps.values():
        union |= i
    k2name = [k for k in dumps if 'GR_FA2400_K2' in k]
    k2 = dumps[k2name[0]] if k2name else set()
    P('转储 %d 个 ; 并集扇区 %d' % (len(dumps), len(union)))
    P('K2 dump = %s (%d 扇区)' % (k2name, len(k2)))

    iso = T.Iso(a.iso)
    P('')
    P('MENU_LBA(tcslib) = %d ; GR_LBA(tcslib) = %d' % (zx_lib.MENU_LBA, zx_lib.GR_LBA))
    for tag, lba, keys in (('MENU', zx_lib.MENU_LBA, KEYS_MENU),
                           ('GR', zx_lib.GR_LBA, KEYS_GR)):
        ent = zx_lib.entries(iso, lba)
        P('')
        P('==== %s.IMG 条目 %d 个 ; 关键条目覆盖 ====' % (tag, len(ent)))
        for e in ent:
            if e['name'] not in keys:
                continue
            l0 = e['iso_off'] // SEC
            l1 = (e['iso_off'] + e['stored'] - 1) // SEC
            rng = range(l0, l1 + 1)
            hk = sum(1 for l in rng if l in k2)
            hu = sum(1 for l in rng if l in union)
            prov = sorted({nm for nm, i in dumps.items()
                           if any(l in i for l in rng)})
            P('%-4d %-24s idx=%-5d iso=0x%08X stored=%-9d real=%-9d LBA %d..%d' %
              (e['idx'], e['name'], e['idx'], e['iso_off'], e['stored'], e['real'], l0, l1))
            P('        K2覆盖 %d/%d (%.0f%%) ; 并集覆盖 %d/%d (%.0f%%)' %
              (hk, l1 - l0 + 1, 100.0 * hk / (l1 - l0 + 1),
               hu, l1 - l0 + 1, 100.0 * hu / (l1 - l0 + 1)))
            if hu:
                P('        提供者: %s' % ', '.join(prov))
    # GR.IMG 里 COMMON.PAK / FONT.RES / EN_STRINGS.RES 全找一遍（可能有多个同名）
    ent = zx_lib.entries(iso, zx_lib.GR_LBA)
    P('')
    P('==== GR.IMG 同名多份普查 ====')
    for e in ent:
        if e['name'] in ('COMMON.PAK', 'FONT.RES', 'EN_STRINGS.RES',
                         'EN_SPECIAL_FEATURE.XML'):
            l0 = e['iso_off'] // SEC
            l1 = (e['iso_off'] + e['stored'] - 1) // SEC
            rng = range(l0, l1 + 1)
            hk = sum(1 for l in rng if l in k2)
            hu = sum(1 for l in rng if l in union)
            P('GR#%-5d %-24s iso=0x%08X stored=%-9d LBA %d..%d K2 %d%% 并集 %d%%' %
              (e['idx'], e['name'], e['iso_off'], e['stored'], l0, l1,
               100 * hk // (l1 - l0 + 1), 100 * hu // (l1 - l0 + 1)))
    iso.close()
    out = a.out or os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', 'temp', 'keycov.txt')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(LOG) + '\n')
    print('[out] %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
