# -*- coding: utf-8 -*-
r"""f364_recon.py -- 只读侦察: 「364 缺字」目标 vs 基底 GR_ZH124 的现状

输出:
  · charset pair_of / codes 现状 (槽占用, lead 字节占用)
  · 364 缺字里 已落盘 / 未落盘 的精确数字与清单
  · 基底盘 FONT.RES nrec / 记录 / 两条活带 / 图集墨量
用法: python work\tools\f364_recon.py
"""
import csv
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                    # noqa: E402
import zx_lib                                                         # noqa: E402
import tcslib                                                         # noqa: E402

REPO = zx_lib.REPO
R81 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r81')
R82 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82')
OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82')
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH124', 'GR_ZH124.iso')
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def main():
    P('=' * 78)
    P('f364_recon.py  基底 = GR_ZH124')
    P('=' * 78)

    # ---------- charset ----------
    cs = json.load(io.open(CHARSET, encoding='utf-8'))
    codes = {k: int(v) for k, v in cs['codes'].items()}
    pair_raw = {k: (int(v[0]), int(v[1])) for k, v in cs['pair_of'].items()}
    pair_of = {k: (l - 0xA1) * 94 + (t - 0xA1) for k, (l, t) in pair_raw.items()}
    P('[cs ] codes %d ; pair_of %d ; protected %s ; mark_codes %s'
      % (len(codes), len(pair_of), cs['protected'], cs['mark_codes']))
    slots = sorted(pair_of.values())
    P('[cs ] pair slot: min %d max %d ; 唯一 %d ; 重复 %d'
      % (min(slots), max(slots), len(set(slots)), len(slots) - len(set(slots))))
    # 槽占用直方（按 94 的 lead 分块）
    used = set(slots)
    P('[cs ] slot 连续性: 0..%d 里缺 %d 个' % (max(slots), sum(1 for s in range(max(slots) + 1)
                                                             if s not in used)))
    missing_slots = [s for s in range(max(slots) + 1) if s not in used]
    if missing_slots:
        P('[cs ] 缺槽 (前 40): %s' % missing_slots[:40])
    P('[cs ] >=1736 的已登记槽: %s' % sorted(s for s in used if s >= 1736)[:80])
    # lead 占用
    lead_used = sorted({0xA1 + s // 94 for s in used})
    P('[cs ] 用到的 lead 字节: %s (共 %d)'
      % (['0x%02X' % b for b in lead_used], len(lead_used)))
    cs_used = sorted(set(codes.values()))
    P('[cs ] 单字节 codes: %d 个, 范围 0x%02X..0x%02X' % (len(cs_used), cs_used[0], cs_used[-1]))
    free_sb = [b for b in range(0x80, 0x100) if b not in set(cs_used)]
    P('[cs ] 0x80..0xFF 里未登记为 codes 的字节: %s'
      % ['0x%02X' % b for b in free_sb])
    # 键/练/用 在 codes 里吗
    for ch in ('键', '练', '用', '△'):
        P('[cs ] %r: codes=%s pair_of=%s' % (ch, codes.get(ch), pair_of.get(ch)))

    # ---------- 364 缺字 ----------
    rich = []
    with io.open(os.path.join(R82, 'rich_missing_chars.csv'), encoding='utf-8-sig',
                 newline='') as f:
        for r in csv.DictReader(f):
            rich.append((r['char'], r['codepoint']))
    old = []
    with io.open(os.path.join(R81, 'missing_chars.csv'), encoding='utf-8-sig',
                 newline='') as f:
        for r in csv.DictReader(f):
            old.append((r['char'], r['codepoint']))
    P('[364] rich_missing_chars.csv %d 条 ; missing_chars.csv %d 条 ; 集合相同=%s'
      % (len(rich), len(old), {c for c, _ in rich} == {c for c, _ in old}))
    have = [(c, cp) for (c, cp) in rich if c in pair_of]
    nothave = [(c, cp) for (c, cp) in rich if c not in pair_of]
    P('[364] 已在 pair_of: %d ; 不在: %d' % (len(have), len(nothave)))
    P('[364] 不在 pair_of 的清单 (%d):' % len(nothave))
    P('      %s' % ''.join(c for c, _ in nothave))
    P('[364] 不在 pair_of 的码位: %s' % ' '.join(cp for _, cp in nothave))
    P('[364] 已在 pair_of 且槽 <1504: %s'
      % [(c, pair_of[c]) for c, _ in have if pair_of[c] < 1504])
    # 名字/风格
    P('[364] 含嘚 U+561A? %s' % any(cp == 'U+561A' for _, cp in rich))

    # ---------- 图集 ----------
    iso = tcslib.Iso(BASE)
    names = []
    for i in range(2000):
        e = iso.img_entry(zx_lib.MENU_LBA, i)
        if e['name'].startswith('?'):
            break
        names.append(e['name'])
    e_pak = iso.img_entry(zx_lib.MENU_LBA, names.index('COMMON.PAK'))
    e_ft = iso.img_entry(zx_lib.MENU_LBA, names.index('FONT.RES'))
    P('[iso] COMMON.PAK off=0x%X stored=%d real=%d ; FONT.RES off=0x%X stored=%d real=%d'
      % (e_pak['off'], e_pak['stored'], e_pak['real'], e_ft['off'], e_ft['stored'], e_ft['real']))
    pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
    recs = tcslib.parse_pak_records(pak)
    nm, psm, W, H, clut, px, PX = recs[1]
    P('[pak] rec#1 %s psm=0x%02X %dx%d clut=%d px_size=0x%X px@0x%X ; 链条 %d 条'
      % (nm, psm, W, H, clut, px, PX, len(recs)))
    cont = pak[PX:PX + px]
    img, cov = zx_lib.decode_engine(cont, W, H)
    P('[at ] 容器 %d B ; %d 段 ; 墨 %d / 覆盖 %d / 总 %d'
      % (px, len(zx_lib.seg_table(cont, W)), int(img.sum()), int(cov.sum()), W * H))

    # 每个已登记槽的墨量
    def cell_ink(s):
        x, y = zx_lib.slot_cell(s)
        if y + 16 > H:
            return -1
        return int(img[y:y + 16, x:x + 16].sum())

    ink_lt = [(s, cell_ink(s)) for s in sorted(used)]
    blank = [(s, v) for s, v in ink_lt if v == 0]
    P('[at ] 已登记槽里空格(=无墨) %d 个: %s' % (len(blank), blank[:40]))
    if have:
        vals = [cell_ink(pair_of[c]) for c, _ in have]
        P('[at ] 已登记缺字槽墨量: 0 墨 %d / >0 墨 %d'
          % (sum(1 for v in vals if v == 0), sum(1 for v in vals if v > 0)))
    # 未登记槽里有没有墨（说明盘上已经画了但没登记）
    free_inked = [(s, cell_ink(s)) for s in range(0, 1868) if s not in used and cell_ink(s) > 0]
    P('[at ] 槽 0..1867 中「未登记但有墨」= %d 个: %s'
      % (len(free_inked), free_inked[:60]))

    # ---------- FONT.RES ----------
    ft_slot = iso.read(e_ft['iso_off'], e_ft['stored'])
    exp = b''.join(s[0] for s in tcslib.lzo_subs(ft_slot))
    faces, endp = zx_lib.ft_records(exp, 28)
    P('[ft ] 槽 %d B ; 展开 %d B ; endp 0x%X' % (e_ft['stored'], len(exp), endp))
    for (fn, fld, rows) in faces:
        vs = sorted({(r[1][3], r[1][5]) for r in rows})
        P('[ft ] face %-8s nrec=%3d (fld4=%d fld5=%d) ; v 带 %s'
          % (fn, fld[4] * fld[5], fld[4], fld[5], vs[:12]))
    allr = [(fn, r[1]) for (fn, fld, rows) in faces for r in rows]
    bands = {}
    for fn, r in allr:
        bands.setdefault((r[3], r[5]), 0)
        bands[(r[3], r[5])] += 1
    P('[ft ] 记录 v 带分布 %s' % sorted(bands.items()))
    P('[ft ] 非空矩形记录数 %d ; 空矩形 %d'
      % (sum(1 for _, r in allr if r[4] > r[2]),
         sum(1 for _, r in allr if r[4] <= r[2])))

    # ---------- ELF gate ----------
    ELF_ISO_BASE, ELF_VA_BASE = 0x93880, 0x100000
    for va in (0x416EE8, 0x417160, 0x41751C, 0x5656A4):
        off = ELF_ISO_BASE + va - ELF_VA_BASE
        w0 = struct.unpack_from('<I', iso.mm, off)[0]
        P('[elf] VA 0x%06X → imm 0x%X' % (va, w0 & 0xFFFF))
    iso.close()

    # ---------- 字体可用性 ----------
    gj = json.load(io.open(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r81',
                                        'glyphs_zh120.json'), encoding='utf-8'))
    gset = {it['char']: bool(it.get('hex')) for it in gj['items']}
    P('[gly] glyphs_zh120.json 条目 %d ; 有 hex %d' % (len(gset), sum(gset.values())))
    nofz = [c for c, _ in nothave if not gset.get(c)]
    P('[gly] 未落盘里 fz16 无 hex 的: %d 个: %s' % (len(nofz), nofz))
    P('[gly] 未落盘里 fz16 有 hex 的: %d 个' % (len(nothave) - len(nofz)))
    return 0


if __name__ == '__main__':
    rc = main()
    with io.open(os.path.join(OUTDIR, 'f364_recon.txt'), 'w', encoding='utf-8',
                 newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    sys.exit(rc)
