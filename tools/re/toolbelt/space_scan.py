# -*- coding: utf-8 -*-
r"""space_scan.py -- round78 ISO 空位盘点（只读）。

盘出 MENU.IMG / GR.IMG 两个 PS2 IMG 容器里**所有**可用字节，分五类：

  A. gap        = [entry.off+entry.stored, next_entry.off)  条目之间未分配区（表里没有任何条目覆盖）
  B. tail       = [last_end, file_size)                      容器尾部未分配区
  C. head       = [0, first_off)                             容器头部（表/名字区，通常不可动，只列）
  D. entry_tail_zeros = 条目 stored 区**末尾**的全零段（要缩短 stored 才能用 → 探针类）
  E. dead_entry = 整条 stored 区 100% 全零（表项还指向它 → 可整条回收）

另测 stored>real（声明长度大于解压长度 = 条目内余量）与 all-zero entry。

用法:
  python tools/re/toolbelt/space_scan.py --iso <iso> --target menu|gr --json <out.json>
"""
import argparse
import json
import os
import struct
import sys
import time

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib  # noqa: E402

SEC = 2048
MENU_LBA = 776286
GR_LBA = 19175
MENU_SIZE = 58300882
GR_SIZE = 1550563328
CHUNK = 1 << 24


def scan_zeros(path, base, size, ranges, min_run=64):
    """在 [base, base+size) 里找全零 run。ranges = [(tag, a, b)] (相对 off)。

    返回 {tag: [(a, b, run_len_>=min_run)]}。用 numpy 一遍扫描所有 range 的并集。
    做法: 逐 chunk 读, 对 chunk 内求 nonzero 位置, 反推零 run 边界。
    """
    out = {t: [] for t, _a, _b in ranges}
    # per-range cursor: 该 range 内"尚未闭合的零 run 起点"
    open_run = {t: None for t, _a, _b in ranges}
    # 排序 ranges 便于定位
    rs = sorted(ranges, key=lambda r: r[1])
    f = open(path, 'rb')
    for rng_tag, ra, rb in rs:
        if rb <= ra:
            continue
        p = ra
        cur = None
        while p < rb:
            n = min(CHUNK, rb - p)
            f.seek(base + p)
            buf = f.read(n)
            if not buf:
                break
            arr = np.frombuffer(buf, dtype=np.uint8)
            nz = np.flatnonzero(arr)
            if nz.size == 0:
                if cur is None:
                    cur = p
                p += n
                continue
            # 逐段: 零段与 nz 交替
            prev = 0
            for k in nz:
                k = int(k)
                if k > prev:
                    zs, ze = p + prev, p + k
                    if cur is not None:
                        zs = cur
                        cur = None
                    if ze - zs >= min_run:
                        out[rng_tag].append((zs, ze, ze - zs))
                prev = k + 1
            if prev < n:
                zs = p + prev
                if cur is None:
                    cur = zs
            p += n
        if cur is not None:
            ze = rb
            if ze - cur >= min_run:
                out[rng_tag].append((cur, ze, ze - cur))
    f.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--target', required=True, choices=['menu', 'gr'])
    ap.add_argument('--json', required=True)
    ap.add_argument('--maxent', type=int, default=8000)
    a = ap.parse_args()

    lba = MENU_LBA if a.target == 'menu' else GR_LBA
    base = lba * SEC
    size = MENU_SIZE if a.target == 'menu' else GR_SIZE
    t0 = time.time()

    iso = tcslib.Iso(a.iso)
    ents = []
    for i in range(a.maxent):
        e = iso.img_entry(lba, i)
        nm = e['name']
        if nm.startswith('?') and e['off'] == 0 and e['stored'] == 0:
            break
        e['idx'] = i
        ents.append(e)
    # 统计表头
    hdr = struct.unpack_from('<8I', iso.mm, base)
    names_noff = struct.unpack_from('<I', iso.mm, base + 0x10)[0]
    names_nend = struct.unpack_from('<I', iso.mm, base + 4)[0]
    nnames = len([x for x in bytes(iso.mm[base + names_noff:base + names_nend]).split(b'\x00') if x])

    # 有效条目 = off>0 且 off < size
    live = [e for e in ents if e['off'] > 0 and e['off'] < size]
    # 按 off 排序, 检测重叠
    byoff = sorted(live, key=lambda e: e['off'])
    overlaps = []
    ends = []
    for k, e in enumerate(byoff):
        end = e['off'] + e['stored']
        if k + 1 < len(byoff):
            nxt = byoff[k + 1]
            if end > nxt['off']:
                overlaps.append((e['name'], nxt['name'], e['off'], end, nxt['off']))
            g = nxt['off'] - end
        else:
            g = None
        e['end'] = end
        e['gap_to_next'] = g
        e['next_name'] = byoff[k + 1]['name'] if k + 1 < len(byoff) else None
        ends.append(end)

    first_off = byoff[0]['off'] if byoff else 0
    last_end = max(ends) if ends else 0

    # 分类区间
    gaps = []           # A  (off, end, prev_name, next_name)
    for k, e in enumerate(byoff):
        if e['gap_to_next'] and e['gap_to_next'] > 0:
            gaps.append((e['off'] + e['stored'], e['off'] + e['stored'] + e['gap_to_next'],
                         e['name'], e['next_name']))
    tail = [(last_end, size)] if size > last_end else []      # B
    head = [(0, first_off)] if first_off > 0 else []          # C

    ranges = []
    for i, (x, y, _p, _n) in enumerate(gaps):
        ranges.append(('gap#%d' % i, x, y))
    for i, (x, y) in enumerate(tail):
        ranges.append(('tail#%d' % i, x, y))
    for i, (x, y) in enumerate(head):
        ranges.append(('head#%d' % i, x, y))
    # D: 条目尾部零
    for k, e in enumerate(byoff):
        if e['stored'] > 0:
            ranges.append(('ent#%d' % e['idx'], e['off'], e['off'] + e['stored']))

    zr = scan_zeros(a.iso, base, size, ranges, min_run=64)

    def sumruns(key):
        return sum(r[2] for r in zr.get(key, []))

    # gap 明细
    gapdet = []
    for i, (x, y, prv, nxt) in enumerate(gaps):
        gapdet.append(dict(off=x, end=y, len=y - x, zero=sumruns('gap#%d' % i),
                           prev=prv, next=nxt, runs=zr.get('gap#%d' % i, [])[:200]))
    taildet = [dict(off=x, end=y, len=y - x, zero=sumruns('tail#%d' % i),
                    runs=zr.get('tail#%d' % i, [])[:200]) for i, (x, y) in enumerate(tail)]
    headdet = [dict(off=x, end=y, len=y - x, zero=sumruns('head#%d' % i),
                    runs=zr.get('head#%d' % i, [])[:200]) for i, (x, y) in enumerate(head)]

    # 条目明细 (只保留有意义的: stored!=real / 全零 / 尾零>=1024)
    entdet = []
    dead = []
    for e in byoff:
        runs = zr.get('ent#%d' % e['idx'], [])
        tailzero = 0
        if runs:
            last = runs[-1]
            if last[1] == e['off'] + e['stored']:
                # 合并连续贴尾的 run
                j = len(runs) - 1
                while j >= 1 and runs[j - 1][1] == runs[j][0]:
                    j -= 1
                tailzero = e['off'] + e['stored'] - runs[j][0]
        nonzero = e['stored'] - sum(r[2] for r in runs)
        d = dict(idx=e['idx'], name=e['name'], off=e['off'], stored=e['stored'],
                 real=e['real'], end=e['off'] + e['stored'],
                 gap_to_next=e['gap_to_next'], next_name=e['next_name'],
                 tail_zeros=tailzero, all_zero_bytes=sum(r[2] for r in runs),
                 nonzero_bytes=nonzero, n_zero_runs=len(runs))
        if nonzero == 0 and e['stored'] > 0:
            dead.append(d)
        if e['stored'] != e['real'] or tailzero >= 1024:
            entdet.append(d)

    rep = dict(iso=os.path.abspath(a.iso), target=a.target, lba=lba, base=base,
               size=size, hdr=list(hdr), names_noff=names_noff, names_nend=names_nend,
               n_names=nnames, n_entries=len(ents), n_live=len(live),
               first_off=first_off, last_end=last_end, overlaps=overlaps[:50],
               gaps=gapdet, tail=taildet, head=headdet,
               dead_entries=[dict(idx=d['idx'], name=d['name'], off=d['off'],
                                  stored=d['stored'], real=d['real']) for d in dead],
               entries=entdet,
               totals=dict(
                   gap_bytes=sum(g['len'] for g in gapdet),
                   gap_zero=sum(g['zero'] for g in gapdet),
                   tail_bytes=sum(t['len'] for t in taildet),
                   tail_zero=sum(t['zero'] for t in taildet),
                   dead_bytes=sum(d['stored'] for d in dead),
                   ent_tail_zero=sum(d['tail_zeros'] for d in entdet),
                   stored_minus_real=sum(max(0, e['stored'] - e['real']) for e in byoff),
               ),
               elapsed=round(time.time() - t0, 1))
    iso.close()
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    with open(a.json, 'w', encoding='utf-8') as f:
        json.dump(rep, f, indent=1, ensure_ascii=False)
    print('[%s] entries=%d live=%d first_off=0x%X last_end=0x%X size=0x%X (%.1fs)'
          % (a.target, len(ents), len(live), first_off, last_end, size, rep['elapsed']))
    print('  gaps      : n=%d bytes=%d (zero=%d)' % (len(gapdet), rep['totals']['gap_bytes'],
                                                     rep['totals']['gap_zero']))
    print('  tail      : n=%d bytes=%d (zero=%d)' % (len(taildet), rep['totals']['tail_bytes'],
                                                     rep['totals']['tail_zero']))
    print('  head      : n=%d bytes=%d' % (len(headdet), sum(h['len'] for h in headdet)))
    print('  dead ents : n=%d bytes=%d' % (len(rep['dead_entries']), rep['totals']['dead_bytes']))
    print('  ent tail0 : %d bytes (over %d entries listed)' % (rep['totals']['ent_tail_zero'],
                                                               len(entdet)))
    print('  stored-real: %d bytes' % rep['totals']['stored_minus_real'])
    print('  overlaps  : %d' % len(overlaps))
    print('  -> %s' % a.json)


main()
