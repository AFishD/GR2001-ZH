# -*- coding: utf-8 -*-
r"""reduce_lib.py — 「受限字表文案改写」的公共口径 (round64)

只读仓库里的字符集 JSON 与 GR_ZH109 的三张文本表; 提供:
  · available_chars()  现役可用字集 = charset JSON 的 pair_of + codes, 再并上 ASCII 可打印
  · load_targets()     读 GR_ZH109 的表, 返回 {id: row} (只含 *_text_*.csv)
  · missing_of(text)   列出 text 里不在可用集里的字 (按首次出现顺序, 去重)
  · check_cell()       给一条 id + 文本, 做「可用集」自查 + {WRAP} 位置自查

★ 与 inject_text_csv.py 的**字库覆盖预检**口径对齐:
  可用集 = charset JSON 能编码的字; ASCII(<0x80) 引擎走单字节路径, 盘上有字形 ⇒ 一律放行。
  真正的权威仍是 inject 的 --check-only (它还查盘上字形), 本模块只是**快速自查**。
"""
import csv
import io
import json
import os
import re
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
TXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                                   # noqa: E402

TABLES = ('GR_ZH109_text_long.csv', 'GR_ZH109_text_long_nowrap.csv',
          'GR_ZH109_text_short.csv')


def available_chars():
    """现役可用字集 (set of 1-char str)。

    来源 = charset_compiled_zh16.json 的 ``pair_of`` (1175 汉字) + ``codes`` (110 单字节字),
    外加 ASCII 可打印区间 (0x20..0x7E) —— 后者不在 JSON 里, 但引擎走 ASCII 单字节路径,
    盘上也有字形 (预检只告警不阻断, 见 inject_text_csv.KIND_ADVICE['ascii_no_glyph'])。
    """
    c = json.load(io.open(CS, encoding='utf-8'))
    have = set(c['pair_of']) | set(c['codes'])
    have |= set(chr(i) for i in range(0x20, 0x7F))
    return have


AVAIL = available_chars()
JSON_ONLY = AVAIL - set(chr(i) for i in range(0x20, 0x7F))


def encodable(ch):
    """这个字符写盘时**引擎能不能编码**? 与 tcslib.GlyphCache.check_text 同一口径:

      · ``ord < 0x80`` (ASCII + 控制字符): 引擎走单字节路径, 与 charset JSON 无关 ⇒ 可以;
        (``\\n`` 由 cell_to_bytes_text 变成 {br}/{p}, 控制字符 <0x20 直接跳过)
      · 否则必须在 charset JSON 里 (``pair_of`` / ``codes``)。
    """
    return ord(ch) < 0x80 or ch in AVAIL


def missing_of(text):
    """text 里**不在可用集**的字 (按首次出现顺序去重; 跳过 {WRAP}/{Warp} 标记本身)。

    ★ 与 inject 预检同口径: ASCII(<0x80) 一律放行, 只报 charset JSON 里没有的**非 ASCII** 字。
    """
    t = T.WRAP_RE.sub('', text or '')
    seen, out = set(), []
    for ch in t:
        if encodable(ch) or ch in seen:
            continue
        seen.add(ch)
        out.append(ch)
    return out


def missing_count(text):
    """text 里超范围字的**出现次数** (不去重)。"""
    t = T.WRAP_RE.sub('', text or '')
    return sum(1 for ch in t if not encodable(ch))


def load_targets():
    """读三张可注入表 → {id: row dict}; 同时返回 {id: 表名}。"""
    rows_by_id, tbl_of = {}, {}
    for fn in TABLES:
        p = os.path.join(TXT, fn)
        with io.open(p, encoding='utf-8-sig', newline='') as f:
            for r in csv.DictReader(f):
                rid = (r.get('id') or '').strip()
                if not rid or rid in rows_by_id:
                    continue
                rows_by_id[rid] = r
                tbl_of[rid] = fn
    return rows_by_id, tbl_of


def wrap_pos_problems(cell):
    """复用工具链口径自查 {WRAP} 写法 + 位置 (返回人话问题清单)。"""
    _clean, bad = T.scan_wrap_marks(cell)
    probs = [('写法', p, f, w) for (p, f, w) in bad]
    probs += [('位置', p, f, w) for (p, f, w) in T.scan_wrap_placement(cell)]
    return probs


def check_cells(cells, label=''):
    """cells = {id: text} → (总超范围字数种数, 总出现次数, {id: [缺字]})。"""
    kinds, total, per = set(), 0, {}
    for rid, cell in sorted(cells.items()):
        m = missing_of(cell)
        n = missing_count(cell)
        if m:
            per[rid] = m
            kinds |= set(m)
            total += n
    return kinds, total, per


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--ids', nargs='*', default=[])
    ap.add_argument('--json', default=os.path.join(HERE, 'reduce_targets.json'))
    a = ap.parse_args()
    rows, tbl = load_targets()
    ids = a.ids or [r['id'] for r in csv.DictReader(
        io.open(os.path.join(HERE, 'missing_entries.csv'), encoding='utf-8-sig'))
        if r['table'] == 'GR_ZH109_text_long.csv']
    out = {}
    for rid in ids:
        r = rows.get(rid)
        if r is None:
            print('!! 找不到条目 %s' % rid)
            continue
        cell = r.get('text_edited') or ''
        out[rid] = dict(table=tbl[rid], text=cell, en=r.get('text_en') or '',
                        zh=r.get('text_zh') or '',
                        n_missing=len(missing_of(cell)),
                        n_missing_hits=missing_count(cell),
                        missing=''.join(missing_of(cell)),
                        has_cr='\r' in cell, has_bs='\\' in cell)
    json.dump(out, io.open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('可用字集: %d 个 (JSON %d + ASCII 可打印)' % (len(AVAIL), len(JSON_ONLY)))
    print('导出 %d 条 → %s' % (len(out), a.json))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
