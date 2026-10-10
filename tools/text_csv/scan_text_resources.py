# -*- coding: utf-8 -*-
r"""scan_text_resources.py — 盘点盘里「含可本地化文本」的容器 (round29 覆盖范围调查)

做法: 遍历 MENU.IMG / GR.IMG 的每个条目 → 解 LZO 子流 → 用引擎字符集解码 →
      统计 CJK 字数与密度, 输出按文本量排序的清单。

用法: python tools/text_csv/scan_text_resources.py --iso <iso> [--top 40] [--json out.json]
"""
import argparse
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                # noqa: E402


def text_stats(txt):
    """只统计「连续可读串」(>=8 字符) 里的字 —— 二进制数据解出来的是散字, 会被滤掉"""
    runs, cur = [], []
    for ch in txt:
        o = ord(ch)
        ok = ch >= ' ' and o != 0x7F and not (0xE000 <= o <= 0xE0FF)
        if ok:
            cur.append(ch)
        else:
            if len(cur) >= 8:
                runs.append(''.join(cur))
            cur = []
    if len(cur) >= 8:
        runs.append(''.join(cur))
    chars = sum(len(r) for r in runs)
    cjk = sum(1 for r in runs for c in r if '\u4e00' <= c <= '\u9fff')
    return chars, cjk, len(runs)


def scan_img(iso, lba, tag, cs, min_cjk=20):
    base = lba * T.SEC
    noff = struct.unpack_from('<I', iso.mm, base + 0x10)[0]
    nend = struct.unpack_from('<I', iso.mm, base + 4)[0]
    names = [x.decode('latin-1') for x in
             bytes(iso.mm[base + noff:base + nend]).split(b'\x00') if x]
    rows = []
    for i, nm in enumerate(names):
        r = struct.unpack_from('<12I', iso.mm, base + T.TAB_OFF + T.TAB_STEP * i)
        stored, real, off = r[6], r[7], r[8]
        if not stored or not off:
            continue
        try:
            subs = T.lzo_subs(iso.read(base + off, stored))
        except Exception:                                         # noqa: BLE001
            continue
        if not subs:
            continue
        blob = b''.join(s[0] for s in subs)
        txt, _ = cs.decode(blob)
        chars, cjk, nruns = text_stats(txt)
        if cjk < min_cjk:
            continue
        rows.append(dict(img=tag, idx=i, name=nm, stored=stored, real=real,
                         subs=len(subs), blob=len(blob), run_chars=chars, cjk=cjk,
                         runs=nruns, density=round(chars / max(1, len(blob)), 4)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--top', type=int, default=40)
    ap.add_argument('--min-cjk', type=int, default=20)
    ap.add_argument('--json', default=None)
    a = ap.parse_args()
    cs = T.Charset()
    iso = T.Iso(a.iso)
    allrows = []
    for lba, tag in ((T.MENU_LBA, 'MENU.IMG'), (T.GR_LBA, 'GR.IMG')):
        rows = scan_img(iso, lba, tag, cs, a.min_cjk)
        print('== %s: %d 个含文本的条目 (CJK >= %d) ==' % (tag, len(rows), a.min_cjk))
        allrows += rows
    allrows.sort(key=lambda r: -r['run_chars'])
    print('\n%-10s %-6s %-22s %9s %9s %7s %7s %7s' %
          ('img', 'idx', 'name', 'stored', 'blob', 'runs', 'run_ch', 'cjk'))
    for r in allrows[:a.top]:
        mark = ''
        if r['img'] == 'MENU.IMG' and r['idx'] == T.LANG_MENU_IDX:
            mark = '  ← LANG (已覆盖)'
        elif r['img'] == 'GR.IMG' and r['idx'] == T.LANG_GR_IDX:
            mark = '  ← LANG 副本 (已覆盖)'
        elif r['img'] == 'MENU.IMG' and r['idx'] == T.XML_IDX:
            mark = '  ← SFXML (已覆盖)'
        print('%-10s %-6d %-22s %9d %9d %7d %7d %7d%s'
              % (r['img'], r['idx'], r['name'][:22], r['stored'], r['blob'],
                 r['runs'], r['run_chars'], r['cjk'], mark))
    print('\n合计: %d 个含文本容器, 已覆盖 3 个实例 (LANG×2 + SFXML×1)' % len(allrows))
    if a.json:
        json.dump(allrows, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('-> %s' % a.json)
    iso.close()


main()
