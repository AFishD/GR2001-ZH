# -*- coding: utf-8 -*-
r"""rb_missing.py -- 只读：把「K2 dump 未覆盖的汉化差异区」映射到 IMG 条目，
判定每一块是什么（文本容器 / 贴图 / 结构）。

用法: python rb_missing.py [--iso <K2 拼装盘>] [--out <txt>]
"""
import argparse
import io
import json
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
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_REBUILD',
                                                  '_probe_k2only.iso'))
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)

    iso = T.Iso(a.iso)
    men = zx_lib.entries(iso, zx_lib.MENU_LBA)
    men_base = zx_lib.MENU_LBA * SEC
    gr = zx_lib.entries(iso, zx_lib.GR_LBA)
    gr_base = zx_lib.GR_LBA * SEC
    P('探测盘 = %s' % a.iso)
    P('MENU 条目 %d ; GR 条目 %d' % (len(men), len(gr)))

    def who(off):
        out = []
        for e in men:
            if e['iso_off'] <= off < e['iso_off'] + e['stored']:
                out.append('MENU#%d %s +%d' % (e['idx'], e['name'], off - e['iso_off']))
        for e in gr:
            if e['iso_off'] <= off < e['iso_off'] + e['stored']:
                out.append('GR#%d %s +%d' % (e['idx'], e['name'], off - e['iso_off']))
        return out or ['<空隙/无归属>']

    j = os.path.join(REPO, 'work', 'builds', 'GR_CVAR', 'evidence_diff_en_vs_zh113b.json')
    d = json.load(open(j, encoding='utf-8'))
    runs = [tuple(x) for x in d['runs']]

    # K2 dump 的扇区集合
    DUMP = os.path.join(os.environ['LOCALAPPDATA'], 'PCSX2', 'cdvd-dump',
                        'GR_FA2400_K2 (2026-10-17 15-08-20).dump')
    n = os.path.getsize(DUMP)
    cnt, rem = divmod(n - 16, 4 + SEC)
    assert rem == 0
    idx = set()
    with open(DUMP, 'rb') as f:
        for i in range(cnt):
            f.seek(16 + i * (4 + SEC))
            idx.add(struct.unpack('<I', f.read(4))[0])

    # 只统计**真正不同的字节**落在未覆盖扇区的部分
    P('')
    P('=== 未被 K2 dump 覆盖的【真实差异字节】逐段（按归属条目聚合） ===')
    agg = {}
    tot_miss = 0
    for (s, e) in runs:
        l0, l1 = s // SEC, (e - 1) // SEC
        miss = [l for l in range(l0, l1 + 1) if l not in idx]
        if not miss:
            continue
        tot_miss += (e - s)
        for l in miss:
            # 该扇区内属于本 run 的字节
            b0, b1 = max(s, l * SEC), min(e, (l + 1) * SEC)
            if b1 <= b0:
                continue
            owners = who(b0)
            key = owners[0].split(' +')[0]
            agg.setdefault(key, dict(bytes=0, runs=0, lba=set()))
            agg[key]['bytes'] += b1 - b0
            agg[key]['runs'] += 1
            agg[key]['lba'].add(l)
    tot_all = sum(e - s for (s, e) in runs)
    P('[总计] 差异字节 %d ; 未覆盖 %d (%.2f%%)' % (tot_all, tot_miss, 100.0 * tot_miss / tot_all))
    P('')
    P('%-34s %10s %8s %8s' % ('归属条目', '差异字节', '段数', '扇区数'))
    for k in sorted(agg, key=lambda k: -agg[k]['bytes']):
        v = agg[k]
        P('%-34s %10d %8d %8d' % (k, v['bytes'], v['runs'], len(v['lba'])))
    P('')
    P('明细:')
    for k in sorted(agg, key=lambda k: -agg[k]['bytes']):
        lb = sorted(agg[k]['lba'])
        rr = []
        st = p = lb[0]
        for x in lb[1:]:
            if x == p + 1:
                p = x
            else:
                rr.append((st, p))
                st = p = x
        rr.append((st, p))
        P('   %-34s LBA %s' % (k, ['%d..%d' % r for r in rr]))
    iso.close()
    out = a.out or os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', 'temp', 'missing.txt')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(LOG) + '\n')
    print('[out] %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
