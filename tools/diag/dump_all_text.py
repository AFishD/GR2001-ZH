# -*- coding: utf-8 -*-
r"""dump_all_text.py — 从任意 ISO 导出**全部文本**为统一表格 (汉化工程通用工具)

用途: 每次构筑后自动产出"这份盘里所有文本"的总表, 并与参考盘 (默认 EN 原盘) 并列对照。
与 tools/hanliu/texts/*.csv (只有 EN 原盘导出) 的区别 = **双列对照 + 覆盖率统计**,
直接回答"哪些还没汉化", 可用于逐轮回归与验收。

输出列: source, key, en (参考盘), zh (本盘), changed, len_en, len_zh, hex_zh, offset
  · changed = 本盘与参考盘不同 (汉化/改动标记)
  · zh 为游戏码页解码结果; ASCII 直通, 中文字符正常显示

覆盖来源:
  1. MENU.IMG > EN_STRINGS.RES    (66 组 2232 条 UI/任务/培训文案)
  2. GR.IMG   > EN_STRINGS.RES    (任务内文案)
  3. MENU.IMG > EN_SPECIAL_FEATURE.XML (特别收录: 分栏名 + 条目文本)
  4. MENU.IMG > EN_STRINGS.TXT    (武器/装备/规则键值)
  5. GR.IMG   > *.ATR             (1193 角色档案 ActorName/ClassName)
  6. GR.IMG   > *.MIS             (任务简报: 地点/日期/正文, 已由 mis_briefings.csv 单独导出)

用法:
  python tools/diag/dump_all_text.py <iso> [--ref <iso>] [--out DIR]
输出 (默认 DIR = <iso同级>/temp/textdump/): all_text.csv / summary.txt / summary.json
"""
import argparse
import csv
import importlib.util
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))

from lz77_decode import lzo1x_decompress                      # noqa: E402
from text_replace import parse_expanded_groups                 # noqa: E402
import tcslib as T                                             # noqa: E402

MENU_LBA, GR_LBA = 776286, 19175
TAB_OFF, TAB_STEP = 0x830, 48
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
RE_ACTOR = re.compile(rb'<ActorName>(.*?)</ActorName>', re.S)
RE_CLASS = re.compile(rb'<ClassName>(.*?)</ClassName>', re.S)
RE_GRP = re.compile(rb'<(studio|group)\s+name="([^"]*)"')
RE_NODE = re.compile(rb'>([^<>]{2,400})<')

_C = json.load(open(CHARSET, encoding='utf-8'))
CODES = dict(_C['codes'])
PAIRS = {k: tuple(v) for k, v in _C['pair_of'].items()}
INV_C = {v: k for k, v in CODES.items()}
INV_P = {v: k for k, v in PAIRS.items()}


def decode_zh(b):
    """游戏码页 → 文本 (ASCII 直通; 无法解码的字节显示 \\xNN)"""
    o, i = [], 0
    while i < len(b):
        if b[i] < 0x80:
            o.append(chr(b[i])); i += 1
        elif i + 1 < len(b) and (b[i], b[i + 1]) in INV_P:
            o.append(INV_P[(b[i], b[i + 1])]); i += 2
        elif b[i] in INV_C:
            o.append(INV_C[b[i]]); i += 1
        else:
            o.append('\\x%02X' % b[i]); i += 1
    return ''.join(o)


def open_container(iso, lba):
    d = open(iso, 'rb').read()
    base = lba * 2048
    noff = struct.unpack_from('<I', d, base + 0x10)[0]
    nend = struct.unpack_from('<I', d, base + 4)[0]
    names = [x.decode('latin-1') for x in d[base + noff:base + nend].split(b'\x00') if x]
    ents = {}
    for i, nm in enumerate(names):
        r = struct.unpack_from('<12I', d, base + TAB_OFF + TAB_STEP * i)
        ents[nm] = (r[6], r[7], r[8])
    return d, base, ents


def subs_of(raw):
    subs, p = [], 0
    while p + 8 <= len(raw):
        L, S = struct.unpack_from('<II', raw, p)
        if L == 0 or p + 8 + L > len(raw):
            break
        try:
            dd, err, _ = lzo1x_decompress(raw[p + 8:p + 8 + L], out_size=S)
        except Exception:
            break
        if err is not None or len(dd) != S:
            break
        subs.append(bytes(dd))
        p += 8 + L
    return subs


def load_entry(d, base, ent):
    stored, real, off = ent
    raw = d[base + off:base + off + stored]
    subs = subs_of(raw)
    body = b''.join(subs) if subs else raw
    return body, base + off


def extract_res(d, base, ents, tag):
    out = {}
    if 'EN_STRINGS.RES' not in ents:
        return out
    body, at = load_entry(d, base, ents['EN_STRINGS.RES'])
    try:
        g, attrs, _ = parse_expanded_groups(body)
    except Exception:
        return out
    for gi, st in enumerate(g):
        for ii, s in enumerate(st):
            out['%s|G%02d.I%03d' % (tag, gi + 1, ii)] = (bytes(s), at)
    return out


def _xml_attrs(blob):
    """`<item|group|studio name="…">` 标题属性 —— ★ 复用**回写链**的 `parse_xml_attrs`。

    importlib 隔离加载 `tools/text_csv/inject_text_csv.py` (与
    `work/tools/migrate_legacy.py::_xml_attrs` 同一手法): 保证"dump 看得到什么"与
    "回写能改什么"认的是**同一批属性**, 一边改了另一边会在写盘前报错。
    """
    if not hasattr(_xml_attrs, 'fn'):
        p = os.path.join(REPO, 'tools', 'text_csv', 'inject_text_csv.py')
        spec = importlib.util.spec_from_file_location('inj_attrs_for_dump', p)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except SystemExit:
            pass
        _xml_attrs.fn = mod.parse_xml_attrs
    return _xml_attrs.fn(blob)


def extract_xml(d, base, ents, tag):
    """SFXML 文本抽取 —— ★ 口径修正 (LEAD_CAPACITY_2400 §14 / §15.4, 2026-10-15)。

    **旧口径的盲点** (只有两条正则, 见本文件 RE_GRP / RE_NODE):
        RE_GRP  = `<(studio|group)\\s+name="…"`   ⇒ 只抓 studio/group 的 name
        RE_NODE = `>([^<>]{2,400})<`              ⇒ 正文**上限 400 字节**, 且正文里不许有 `<>`
    ⇒ **>400 字节的 `<text>` 正文** 与 **`item` 的 `name=` 属性** 一个都看不见。
    实测 EN_SPECIAL_FEATURE.XML: 真值 **265** 处 (正文 250 + `name=` 15), dump 口径只有 **59**
    ⇒ 少算 **206** —— 这 206 正好是"迁移真值 3,279 − `legacy_singles.py` 口径 3,073"的差额。

    **新口径** = 旧口径 ∪ 回写链的现成函数:
        ① 旧口径两条正则**原样保留** (既有行键/行数一个都不少; 短正文的 `node@0x…` 与 ② 逐字节重合,
           字典自然去重);
        ② `tcslib.parse_sfxml`  ⇒ 全部 `<text>` 正文, **不限长度**;
        ③ `inject_text_csv.parse_xml_attrs` ⇒ `name="…"` 标题属性 (只补 `item` 的: studio/group
           已被 ① 的 `section:` 行覆盖, 不重复计)。
    ⇒ 59 + 192 (长正文) + 14 (item name=) = **265** ✓ 与迁移真值一致。
    """
    out = {}
    key = 'EN_SPECIAL_FEATURE.XML'
    if key not in ents:
        return out
    body, at = load_entry(d, base, ents[key])
    # ① 旧口径 (原样, 保证连续性)
    for m in RE_GRP.finditer(body):
        out['%s|section:%s' % (tag, m.group(2).decode('latin-1'))] = (m.group(2), at + m.start(2))
    for m in RE_NODE.finditer(body):
        v = m.group(1).strip()
        if not v:
            continue
        out['%s|node@0x%X' % (tag, m.start(1))] = (v, at + m.start(1))
    # ② <text> 正文全文 (补 >400B 的 192 处)
    for (_k, off, _ln, data) in T.parse_sfxml(body):
        v = data.strip()
        if not v:
            continue
        k = '%s|node@0x%X' % (tag, off)
        if k not in out:
            out[k] = (v, at + off)
    # ③ name= 标题属性 (补 item 的 14 处; studio/group 已由 ① 覆盖)
    for (_ord, tname, off, val) in _xml_attrs(body):
        if tname.lower() in ('studio', 'group'):
            continue
        if not val.strip():
            continue
        out['%s|attr@0x%X' % (tag, off)] = (val, at + off)
    return out


def extract_txt(d, base, ents, tag):
    """EN_STRINGS.TXT: 明文直读, DP 压缩态则标注 (该表值从不被游戏显示, 见 PATCH_INVENTORY §三.10)"""
    out = {}
    key = 'EN_STRINGS.TXT'
    if key not in ents:
        return out
    body, at = load_entry(d, base, ents[key])
    if body[:1] not in (b'\t', b'/', b'#', b'0', b'1', b'2', b'3') or b'\x00' in body[:16]:
        out['%s|__note__' % tag] = ('[DP 压缩态, 未解码; 值不参与显示]'.encode('latin-1'), at)
        return out
    for m in re.finditer(rb'([A-Za-z_][A-Za-z0-9_]{1,40})=([^\x00\r\n]{0,300})', body):
        out['%s|%s' % (tag, m.group(1).decode('latin-1'))] = (m.group(2), at + m.start(2))
    return out


def extract_atr(d, base, ents, tag):
    out = {}
    for nm, ent in ents.items():
        if not nm.upper().endswith('.ATR'):
            continue
        stored, real, off = ent
        raw = d[base + off:base + off + real] if stored == real else b''.join(
            subs_of(d[base + off:base + off + stored]))
        if not raw:
            continue
        for rex, field in ((RE_ACTOR, 'ActorName'), (RE_CLASS, 'ClassName')):
            m = rex.search(raw)
            if m:
                out['%s|%s:%s' % (tag, nm, field)] = (bytes(m.group(1)), base + off + m.start(1))
    return out


def gather(iso):
    """→ {source|key: (bytes, offset)}"""
    menu_d, menu_b, menu_e = open_container(iso, MENU_LBA)
    gr_d, gr_b, gr_e = open_container(iso, GR_LBA)
    res = {}
    res.update(extract_res(menu_d, menu_b, menu_e, 'MENU:RES'))
    res.update(extract_xml(menu_d, menu_b, menu_e, 'MENU:SF'))
    res.update(extract_txt(menu_d, menu_b, menu_e, 'MENU:TXT'))
    res.update(extract_res(gr_d, gr_b, gr_e, 'GR:RES'))
    res.update(extract_atr(gr_d, gr_b, gr_e, 'GR:ATR'))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('--ref', default=os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso'))
    ap.add_argument('--out', default=None)
    args = ap.parse_args()
    iso = os.path.abspath(args.iso)
    out = args.out or os.path.join(os.path.dirname(iso), 'temp', 'textdump')
    os.makedirs(out, exist_ok=True)

    cur = gather(iso)
    ref = gather(args.ref) if args.ref and os.path.isfile(args.ref) else {}
    print('[dump] 本盘 %d 条; 参考盘 %d 条 (%s)'
          % (len(cur), len(ref), os.path.basename(args.ref) if ref else '无'))

    rows = []
    for k in sorted(set(cur) | set(ref)):
        src, key = k.split('|', 1)
        cb = cur.get(k, (b'', 0))[0]
        rb = ref.get(k, (b'', 0))[0]
        rows.append(dict(source=src, key=key, en=decode_zh(rb), zh=decode_zh(cb),
                         changed='1' if cb != rb else '',
                         len_en=len(rb), len_zh=len(cb),
                         hex_zh=cb.hex(), offset='0x%X' % cur.get(k, (b'', 0))[1]))

    csv_p = os.path.join(out, 'all_text.csv')
    with open(csv_p, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['source', 'key', 'en', 'zh', 'changed', 'len_en', 'len_zh', 'hex_zh', 'offset'])
        for r in rows:
            w.writerow([r['source'], r['key'], r['en'], r['zh'], r['changed'],
                        r['len_en'], r['len_zh'], r['hex_zh'], r['offset']])

    # 统计: "含中文" = 文本里出现 CJK 字符
    def has_cjk(s):
        return any('\u4e00' <= ch <= '\u9fff' or ch == '®' for ch in s)

    by = {}
    for r in rows:
        s = by.setdefault(r['source'], [0, 0, 0])
        s[0] += 1
        if has_cjk(r['zh']):
            s[1] += 1
        if r['changed']:
            s[2] += 1
    lines = ['# %s 全量文本导出' % os.path.basename(iso),
             '# 参考盘: %s' % os.path.basename(args.ref),
             '#',
             '# %-16s %7s %8s %8s %8s' % ('来源', '条数', '含中文', '与本盘差异', '中文率'),
             '#' + '-' * 56]
    tot = mt = ct = 0
    for s in sorted(by):
        n, m, c = by[s]
        tot += n; mt += m; ct += c
        lines.append('  %-16s %7d %8d %8d %7.1f%%' % (s, n, m, c, 100.0 * m / n if n else 0))
    lines.append('#' + '-' * 56)
    lines.append('  %-16s %7d %8d %8d %7.1f%%'
                 % ('合计', tot, mt, ct, 100.0 * mt / tot if tot else 0))
    lines.append('')
    lines.append('CSV: %s (%d 行)' % (csv_p, len(rows)))
    txt = '\n'.join(lines)
    open(os.path.join(out, 'summary.txt'), 'w', encoding='utf-8').write(txt + '\n')
    json.dump(dict(iso=os.path.basename(iso), ref=os.path.basename(args.ref),
                   total=tot, chinese=mt, changed=ct, by_source=by),
              open(os.path.join(out, 'summary.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(txt)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
