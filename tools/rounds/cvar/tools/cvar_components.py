# -*- coding: utf-8 -*-
r"""cvar_components.py — 把 EN→ZH113b 的**全部**字节差异分类归入 P1..P6

用法:
  python cvar_components.py --a <EN.iso> --b <ZH.iso> --diff <runs.json>
                            --out <components.json> [--report <txt>]

部件定义 (本工程口径, 与仓库旧工具里的 "--p1/P1" 命名**不是**同一个东西):
  P1_elf        SLUS_206.13 内的全部差异 (字库解码 cave / 闸门常量 / 其它指令 / 字符串表)
  P2_atlas      MENU.IMG::COMMON.PAK 与 GR.IMG::COMMON.PAK (字库容器 + 图集)
  P3_ft         MENU.IMG::FONT.RES 与 GR.IMG::FONT.RES
  P4_text       MENU/GR IMG 的 EN_STRINGS.RES 与 EN_SPECIAL_FEATURE.XML
  P5_book       IMG 条目表 (off/stored/real 记录) 字节
  P6_other      其余全部, 逐项列出

磁盘上的占用区间一律用条目字段 **stored(+0x18)** 计算 (real 是解压后大小,
不是盘上长度; 用 max(stored,real) 会造出假重叠)。
"""
import argparse
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SEC = 2048
TAB_OFF, TAB_STEP = 0x830, 48
IMG_LBA = {'MENU.IMG': 776286, 'GR.IMG': 19175}

# ---- 部件 -> [(IMG 名, 条目名)] 映射
P2_ITEMS = [('MENU.IMG', 'COMMON.PAK'), ('GR.IMG', 'COMMON.PAK')]
P3_ITEMS = [('MENU.IMG', 'FONT.RES'), ('GR.IMG', 'FONT.RES')]
P4_ITEMS = [('MENU.IMG', 'EN_STRINGS.RES'), ('GR.IMG', 'EN_STRINGS.RES'),
            ('MENU.IMG', 'EN_SPECIAL_FEATURE.XML'),
            ('GR.IMG', 'EN_SPECIAL_FEATURE.XML')]


def iso_files(d):
    pvd = 16 * SEC
    root_lba = struct.unpack_from('<I', d, pvd + 158)[0]
    root_size = struct.unpack_from('<I', d, pvd + 166)[0]
    out, dirrecs = [], []

    def readdir(lba, size):
        r = []
        data = d[lba * SEC:lba * SEC + size]
        i = 0
        while i < len(data):
            Ln = data[i]
            if Ln == 0:
                i = (i // SEC + 1) * SEC
                if i >= len(data):
                    break
                continue
            if i + Ln > len(data) or Ln < 34:
                break
            rec = data[i:i + Ln]
            r.append((rec[33:33 + rec[32]],
                      struct.unpack_from('<I', rec, 2)[0],
                      struct.unpack_from('<I', rec, 10)[0], rec[25],
                      lba * SEC + i, Ln))
            i += Ln
        return r

    def walk(lba, size, prefix):
        for nm, ext, sz, fl, ao, Ln in readdir(lba, size):
            if nm in (b'\x00', b'\x01'):
                continue
            name = nm.decode('latin-1')
            p = (prefix + '/' + name) if prefix else name
            dirrecs.append({'path': p, 'off': ao, 'len': Ln})
            if fl & 2:
                walk(ext, sz, p)
            else:
                out.append({'path': p, 'lba': ext, 'size': sz,
                            'iso_off': ext * SEC, 'iso_end': ext * SEC + sz})
    walk(root_lba, root_size, '')
    return out, dirrecs, {'root_lba': root_lba, 'root_size': root_size}


def img_entries(d, lba):
    b = lba * SEC
    noff = struct.unpack_from('<I', d, b + 0x10)[0]
    nend = struct.unpack_from('<I', d, b + 0x04)[0]
    names = [x.decode('latin-1') for x in d[b + noff:b + nend].split(b'\x00') if x]
    return [(nm, list(struct.unpack_from('<12I', d, b + TAB_OFF + TAB_STEP * i)))
            for i, nm in enumerate(names)], noff, nend


def build_intervals(d, tag=''):
    """返回 (intervals, files, dirrecs, info); intervals = (start, end, label, comp, kind)

    tag = 'A' (原盘) / 'B' (汉化盘): 两边的 off 可能不同 (本盘有 1 个条目被搬走),
    所以两边都要建区间表, 分类时优先取"能给出具名条目"的那一边。
    """
    files, dirrecs, info = iso_files(d)
    iv = []
    # ISO9660 层
    iv.append((16 * SEC, 17 * SEC, 'ISO9660 PVD', 'P5_book', 'iso-pvd'))
    for r in dirrecs:
        iv.append((r['off'], r['off'] + r['len'], 'ISO9660 目录记录 %s' % r['path'],
                   'P5_book', 'iso-dirrec'))
    for f in files:
        iv.append((f['iso_off'], f['iso_end'], f['path'], None, 'iso-file'))
    # IMG 层
    ent_map = {}
    for nm, lba in IMG_LBA.items():
        b = lba * SEC
        E, noff, nend = img_entries(d, lba)
        ent_map[nm] = (E, b, noff, nend)
        iv.append((b, b + TAB_OFF, '%s 头' % nm, 'P5_book', 'img-header'))
        iv.append((b + noff, b + nend, '%s 名字表' % nm, 'P5_book', 'img-names'))
        iv.append((b + TAB_OFF, b + TAB_OFF + TAB_STEP * len(E),
                   '%s 条目表' % nm, 'P5_book', 'img-table'))
        for i, (n2, f) in enumerate(E):
            if f[8] and f[6]:
                iv.append((b + f[8], b + f[8] + f[6],
                           '%s::%s [#%d]' % (nm, n2, i), None, 'img-entry'))
    # 部件映射
    comp_of = {}
    for comp, items in (('P2_atlas', P2_ITEMS), ('P3_ft', P3_ITEMS),
                        ('P4_text', P4_ITEMS)):
        for nm, name in items:
            E, b, _n, _e = ent_map[nm]
            hit = [(i, f) for i, (n2, f) in enumerate(E) if n2 == name]
            if not hit:
                print('  !! 未找到 [%s] %s::%s' % (tag, nm, name))
                continue
            for i, f in hit:
                comp_of[(b + f[8], b + f[8] + f[6])] = comp
    iv2 = []
    for (s, e, lb, cp, kd) in iv:
        iv2.append((s, e, lb, comp_of.get((s, e), cp), kd, tag))
    iv2.sort(key=lambda z: (z[1] - z[0]))
    # 每个 IMG 的条目按 off 排序, 便于给"空隙"定位紧邻条目
    gaps = {}
    for nm in IMG_LBA:
        E, b, _n, _e = ent_map[nm]
        lst = sorted(((f[8], f[8] + f[6], n2) for n2, f in E if f[8] and f[6]))
        gaps[nm] = (b, b + (iso_size_of(files, nm) or 0), lst)
    return iv2, files, dirrecs, ent_map, gaps


def iso_size_of(files, name):
    for f in files:
        if f['path'].rsplit('/', 1)[-1].startswith(name):
            return f['size']
    return None


def nearest_entry(gaps, mid):
    for nm, (b, e, lst) in gaps.items():
        if b <= mid < e:
            rel = mid - b
            nxt = prv = None
            for (o, en, name) in lst:
                if o > rel:
                    nxt = '%s(+0x%X)' % (name, o)
                    break
                prv = '%s(+0x%X..+0x%X)' % (name, o, en)
            return '<%s 空隙: 紧邻前条目=%s, 紧邻后条目=%s>' % (nm, prv, nxt)
    return None


def classify(mid, ivs, gaps=None):
    """ivs = [B 的区间表, A 的区间表]; 先找具名条目, 再退回 ISO 文件, 再退回任意"""
    for pref in ('img-entry', 'img-table', 'img-names', 'img-header',
                 'iso-dirrec', 'iso-pvd'):
        for iv in ivs:
            for t in iv:
                if t[4] == pref and t[0] <= mid < t[1]:
                    return t
    if gaps:
        g = nearest_entry(gaps, mid)
        if g:
            return (0, 0, g, 'P6_other', 'img-gap', 'A')
    for iv in ivs:
        for t in iv:
            if t[4] == 'iso-file' and t[0] <= mid < t[1]:
                return t
    for iv in ivs:
        for t in iv:
            if t[0] <= mid < t[1]:
                return t
    return (0, 0, '<结构外>', None, 'none', '?')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a', required=True)
    ap.add_argument('--b', required=True)
    ap.add_argument('--diff', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--report', default=None)
    x = ap.parse_args()
    A = open(x.a, 'rb').read()
    B = open(x.b, 'rb').read()
    D = json.load(open(x.diff, encoding='utf-8'))
    runs = [(a, b) for a, b in D['runs']]
    ivA, files, dirrecs, ent_map, gaps = build_intervals(A, 'A')
    ivB, filesB, _dr, _em, _g = build_intervals(B, 'B')
    ivs = [ivB, ivA]

    elf = [f for f in files if f['path'].startswith('SLUS_206.13')][0]
    comps = {}
    L = []
    P = lambda s: (print(s), L.append(s))
    P('总差异游程 %d 个, 合计 %d B' % (len(runs), sum(e - s for s, e in runs)))
    P('')
    for (s, e) in runs:
        mid = (s + e) // 2
        if elf['iso_off'] <= mid < elf['iso_end']:
            comp, label, kind = 'P1_elf', 'SLUS_206.13', 'elf'
        else:
            t = classify(mid, ivs, gaps)
            comp = t[3] or 'P6_other'
            label, kind = t[2], t[4]
        c = comps.setdefault(comp, {'runs': [], 'bytes': 0, 'items': {}})
        c['runs'].append([s, e])
        c['bytes'] += e - s
        it = c['items'].setdefault(label, {'runs': 0, 'bytes': 0,
                                          'iso_lo': s, 'iso_hi': e, 'kind': kind})
        it['runs'] += 1
        it['bytes'] += e - s
        it['iso_lo'] = min(it['iso_lo'], s)
        it['iso_hi'] = max(it['iso_hi'], e)

    order = ['P1_elf', 'P2_atlas', 'P3_ft', 'P4_text', 'P5_book', 'P6_other']
    for comp in order:
        if comp not in comps:
            P('%-10s : 无差异' % comp)
            continue
        c = comps[comp]
        lo = min(r[0] for r in c['runs'])
        hi = max(r[1] for r in c['runs'])
        P('%-10s : 差异区间 %-6d 个, 总字节 %-9d ISO 0x%09X..0x%09X'
          % (comp, len(c['runs']), c['bytes'], lo, hi))
        P('             涉及结构 %d 个:' % len(c['items']))
        for k in sorted(c['items'], key=lambda z: -c['items'][z]['bytes']):
            it = c['items'][k]
            P('               %-40s runs=%-6d bytes=%-9d 0x%09X..0x%09X [%s]'
              % (k, it['runs'], it['bytes'], it['iso_lo'], it['iso_hi'], it['kind']))
    tot = sum(c['bytes'] for c in comps.values())
    P('')
    P('★ 分类覆盖 %d B / 总差异 %d B  (覆盖 %s)'
      % (tot, sum(e - s for s, e in runs),
         'YES' if tot == sum(e - s for s, e in runs) else 'NO — 有遗漏!'))

    res = {'a': x.a, 'b': x.b, 'sha256_a': D['sha256_a'], 'sha256_b': D['sha256_b'],
           'size_a': D['size_a'], 'size_b': D['size_b'],
           'total_runs': len(runs), 'total_bytes': sum(e - s for s, e in runs),
           'components': comps,
           'elf_range': [elf['iso_off'], elf['iso_end']],
           'intervals_hint': {'P2_atlas': P2_ITEMS, 'P3_ft': P3_ITEMS,
                              'P4_text': P4_ITEMS},
           'entry_table_MENU': [IMG_LBA['MENU.IMG'] * SEC + TAB_OFF,
                                IMG_LBA['MENU.IMG'] * SEC + TAB_OFF
                                + TAB_STEP * len(ent_map['MENU.IMG'][0])],
           'entry_table_GR': [IMG_LBA['GR.IMG'] * SEC + TAB_OFF,
                              IMG_LBA['GR.IMG'] * SEC + TAB_OFF
                              + TAB_STEP * len(ent_map['GR.IMG'][0])],
           }
    with open(x.out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(res, f, indent=1)
    P('→ %s' % x.out)
    if x.report:
        with open(x.report, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(L) + '\n')
        print('→ %s' % x.report)
    return 0


if __name__ == '__main__':
    sys.exit(main())
