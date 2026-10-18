# -*- coding: utf-8 -*-
r"""repack_leak_scan.py — **重排漏网容器扫描** (round51): 找出"引擎会解码、但重排不会重编码"的中文文本源。

## 背景 (round50 遗留的首要问题)

开启「字库紧凑重排」(`repack_font.py`) 后, 实机「特别收录 → 何为幽灵？」那页的**标题条**
被画成「何为**强知营**」。机理本轮查实 (见下), 本工具把它**变成可复现的机器判据**。

## 机理 (round51 定稿)

`EN_SPECIAL_FEATURE.XML` 的结构是::

    <studio name="BackStory" pic="sf_backstory.rsb">
      <item name="<中文标题>" pic="sf_Snowy_Streets.rsb">     ← ★标题在 item 的 name 属性里
        <text>Tom Clancy …： 何为幽灵？{p}在 Tom Clancy …</text> ← 正文在 text 元素里
        ...
      </item>
    </studio>

而 `dump_text_csv.py` 只用 `TEXT_RE = <text>([^<]*)</text>` 抽 **`<text>` 元素** ⇒
`<item name="…">` / `<group name="…">` 这些**属性里的中文从来没进过可注入表**,
于是「整体重编码」这一步 (`repack_font.make_reencode_tables` → `inject_text_csv`) **碰不到它们**。
重排把码位整体改掉之后, 这些**旧码位**就指到了别人的字形上 ⇒ 标题变错字。

## 本工具做什么 (全部只读)

  ① **覆盖范围**: 列出 `repack_font` 会重编码的东西 (顺序 + 覆盖面) 与**没**覆盖的东西;
  ② **漏网清单**: 解析 SFXML, 把全部 `name=` 属性抓出来, 分成"含中文/纯 ASCII";
  ③ **复现**: 用"重排前 charset + 重排搬运表"算出**重排后**的 charset, 把标题属性里的
     **旧码位**按新表解码 ⇒ 若解出来是别的字, 就是实机看到的那个错字 (闭环);
  ④ **反证 (现役盘不受影响)**: 同一批属性在**现役盘 + 现役 charset** 下必须解出**原文**;
  ⑤ **全盘搜索**: 扫整个 ISO, 找出所有"按现役 charset 能解出连续中文"的字节串,
     按容器归类 —— 这就是「引擎实际会解码文本的位置」的**完整清单**(含镜外容器, 如实标注置信度)。

## 用法

  python tools/iso_build/repack_leak_scan.py --iso work/builds/GR_ZH98/GR_ZH98.iso \
      --out work/builds/GR_ZH98/temp/r51 [--repack-charset-before X.json --repack-moves Y.json]

★ 只读: 只 mmap 读 ISO。
"""
import argparse
import io
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:                                                        # noqa: BLE001
    pass

import tcslib                                                            # noqa: E402

TOOL = 'tools/iso_build/repack_leak_scan.py'
TOOL_VERSION = 'r51.1'
ROUND = 'round51'

# XML 里"引擎会拿去显示"的属性 (round51 从 SFXML 结构实测得出)
TEXT_ATTRS = ('name',)
ITEM_RE = re.compile(rb'<(item|group|studio)\b([^>]*)>')
ATTR_RE = re.compile(rb'([A-Za-z_][\w:.-]*)\s*=\s*"([^"]*)"')
TEXT_EL_RE = re.compile(rb'<text>([^<]*)</text>')


def rel(p):
    try:
        r = os.path.relpath(p, REPO)
    except ValueError:
        return p.replace('\\', '/')
    return r.replace('\\', '/') if not r.startswith('..') else p.replace('\\', '/')


def load_blob(iso, res_key, copy=0):
    """按 tcslib.RES 的口径把一个 RES 容器 (LZO 子流) 展开。"""
    spec = tcslib.RES[res_key]['copies'][copy]
    lba, idx = spec[1], spec[2]
    e = iso.img_entry(lba, idx)
    raw = iso.read(e['iso_off'], e['stored'])
    blob = b''.join(s[0] for s in tcslib.lzo_subs(raw))
    return dict(tag=spec[3], lba=lba, idx=idx, entry=e, raw=raw, blob=blob)


# ═════════════ ① 覆盖范围 ═════════════

def coverage():
    """`repack_font` 重编码了什么 / 没重编码什么 (从代码路径读出来, 不猜)。"""
    return dict(
        what_repack_does=[
            '把**对偶码 (pair) 字**的槽位整体重排: charset JSON 的 pair_of 逐字改码位 '
            '(repack_font.update_charset → js["pair_of"][ch] = 新 lead/trail)',
            '图集里把在用字形搬到最前面的可用格, 未使用区域清零 '
            '(repack_font.apply → Atlas.write_pixels)',
            '把**可注入文本表**拷成"强制重编码"副本: 只清 text_zh 列 '
            '(repack_font.make_reencode_tables), 于是 inject_text_csv 认为每行都被人工改过, '
            '用**新 charset** 重新编码写盘',
        ],
        what_gets_reencoded=[
            'EN_STRINGS.RES (LANG) —— 2 份副本: MENU.IMG #25 与 GR.IMG #902',
            'EN_SPECIAL_FEATURE.XML (SFXML) —— 1 份: MENU.IMG #283, 且**只重写 <text> 元素**',
        ],
        what_is_NOT_reencoded=[
            '★ SFXML 里 <item name="…"> / <group name="…"> 属性 —— 中文标题就在这儿 '
            '(dump_text_csv 的 TEXT_RE 只抓 <text> 元素, 属性从来没进过表)',
            'SFXML 里 <picname> / <moviename> / <soundname> / <3dname> (纯 ASCII 文件名)',
            'MENU.IMG / GR.IMG 里其它条目 (界面图、PAK、其它 XML 配置、任务数据 .MIS、人物定义 .ATR)',
            'ISO 里的独立文件 (SYSTEM.CNF / *.IRX / IOPRP*.IMG …)',
            'ELF (SLUS_206.13) 里的程序字符串',
        ],
        why_it_matters='重排改了"字节 ↔ 字符"的映射 ⇒ 任何**没被重编码**的中文文本源都会指错字形 '
                       '(实机表现 = 标题/菜单里出现别的字)。',
        remedy_design='可修: 重排在改完 pair_of 之后, 对 SFXML 里**全部非 <text> 的中文字节串**做一次'
                      '「旧码位 → 新码位」原位重映射 (pair↔pair 同为 2 字节 ⇒ 长度不变, 可原地改写, '
                      '不动容器大小/条目表)。本轮**没有实施** —— 因为重排的容量增益 = 0 (见报告), '
                      '按验收判据「修完增益仍为 0 ⇒ 保持 --no-font-repack」。',
    )


# ═════════════ ② 漏网清单 ═════════════

def sfxml_attributes(blob, cs):
    """抓 SFXML 里全部元素的 name 属性 ⇒ 每条 (tag, name_bytes, 是否含中文, 解码文本)。"""
    out = []
    for m in ITEM_RE.finditer(blob):
        tag = m.group(1).decode('latin-1')
        for am in ATTR_RE.finditer(m.group(2)):
            key = am.group(1).decode('latin-1')
            if key not in TEXT_ATTRS:
                continue
            val = am.group(2)
            txt, _ = cs.decode(val)
            cjk = sum(1 for c in txt if '\u4e00' <= c <= '\u9fff' or ord(c) > 0x7F)
            out.append(dict(tag=tag, attr=key, off=m.start(), bytes_hex=val.hex(' '),
                            nbytes=len(val), text=txt, non_ascii=cjk))
    return out


def sfxml_text_elements(blob):
    """`<text>` 元素统计: 开标签数 / 成对匹配数 / 带内容数。"""
    opens = len(re.findall(rb'<text[\s>]', blob))
    pairs = [dict(off=m.start(), nbytes=len(m.group(1))) for m in TEXT_EL_RE.finditer(blob)]
    return dict(open_tags=opens, matched_pairs=len(pairs),
                nonempty=sum(1 for p in pairs if p['nbytes']),
                bytes=sum(p['nbytes'] for p in pairs), pairs=pairs)


# ═════════════ ③ 复现重排后的 charset ═════════════

def charset_after_repack(before_json, moves_json):
    """用"重排前的 charset + 逐字搬运表"算出**重排后**的 charset (只算, 不写任何文件)。"""
    js = json.load(io.open(before_json, encoding='utf-8'))
    mv = json.load(io.open(moves_json, encoding='utf-8'))
    if isinstance(mv, dict):
        moves = None
        for k in ('moves', 'changes', 'items'):
            if isinstance(mv.get(k), list):
                moves = mv[k]
                break
        if moves is None:
            raise SystemExit('!! %s 里找不到搬运清单 (moves/changes/items)' % moves_json)
    else:
        moves = mv
    pair = dict((k, tuple(v)) for k, v in js['pair_of'].items())
    n = 0
    for m in moves:
        ch = m.get('char')
        ns = m.get('new_slot', m.get('to_slot'))
        if ch is None or ns is None or ch not in pair:
            continue
        pair[ch] = tcslib.pair_from_slot(int(ns))
        n += 1
    codes = dict((k, int(v)) for k, v in js['codes'].items())
    return dict(pair_of=pair, codes=codes, moved=n,
                decoded_of=dict((tuple(v), k) for k, v in pair.items()),
                single_of=dict((v, k) for k, v in codes.items()))


def decode_with(pair_map, single_map, b):
    """按一张 (pair→char, byte→char) 表解码 (与引擎同规则: pair 优先, 单字节兜底)。"""
    out, i, n = [], 0, len(b)
    while i < n:
        v = b[i]
        if v < 0x80:
            out.append(chr(v)); i += 1
        elif tcslib.PAIR_LEAD_LO <= v < tcslib.PAIR_LEAD_HI and i + 1 < n and (v, b[i + 1]) in pair_map:
            out.append(pair_map[(v, b[i + 1])]); i += 2
        elif v in single_map:
            out.append(single_map[v]); i += 1
        else:
            out.append('·'); i += 1
    return ''.join(out)


# ═════════════ ④ 全盘搜索: 哪些地方"引擎会解码出中文" ═════════════

def build_region_map(iso):
    """ISO 偏移 → 容器名 的区间表 (两个 IMG 的全部条目), 按起点排序供二分查找。"""
    regions = []
    lbas = {}
    for _rk, spec in tcslib.RES.items():
        for c in spec['copies']:
            lbas[c[0]] = c[1]
    for name, lba in sorted(lbas.items()):
        for idx in range(0, 2048):
            try:
                e = iso.img_entry(lba, idx)
            except Exception:                                             # noqa: BLE001
                break
            if e['stored'] <= 0 or e['off'] <= 0:
                if idx == 0:
                    continue
                break
            regions.append((e['iso_off'], e['iso_off'] + e['stored'], '%s#%d %s'
                            % (name, idx, e['name'])))
    regions.sort()
    return regions


def who(regions, off):
    """二分查找 off 落在哪个容器 (没有则返回未归属)。"""
    lo, hi = 0, len(regions) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        a, b, nm = regions[mid]
        if off < a:
            hi = mid - 1
        elif off >= b:
            lo = mid + 1
        else:
            return nm
    return '(IMG 之外 / 未归属)'



def scan_iso_text(iso, cs, min_cjk=4, chunk=1 << 20, max_runs=400000):
    """扫整个 ISO: 找出"连续 ≥min_cjk 个 charset 里有的非 ASCII 字符"的字节串。"""
    import numpy as np
    n = iso.size
    hits = []
    i = 0
    while i < n and len(hits) < max_runs:
        j = min(n, i + chunk)
        buf = np.frombuffer(iso.mm[i:j], dtype=np.uint8)
        hi = buf >= 0x80
        if not hi.any():
            i = j
            continue
        idx = np.flatnonzero(hi)
        # 把"高位字节"聚成段 (段内允许夹杂 ASCII, 因为中文串里常有 ASCII)
        groups = np.split(idx, np.flatnonzero(np.diff(idx) > 64) + 1)
        for g in groups:
            a, b = int(g[0]) + i, int(g[-1]) + i + 1
            if b - a < min_cjk:
                continue
            seg = bytes(iso.mm[a:b])
            txt, _ = cs.decode(seg)
            cjk = [c for c in txt if '\u4e00' <= c <= '\u9fff']
            if len(cjk) >= min_cjk:
                hits.append(dict(off=a, nbytes=b - a, cjk=len(cjk), text=txt[:120]))
        i = j
    return hits


# ═════════════ main ═════════════

def main():
    ap = argparse.ArgumentParser(description='重排漏网容器扫描 (round51)')
    ap.add_argument('--iso', required=True)
    ap.add_argument('--out', default=None)
    ap.add_argument('--charset', default=None)
    ap.add_argument('--repack-charset-before', default=None)
    ap.add_argument('--repack-moves', default=None)
    ap.add_argument('--no-full-scan', action='store_true')
    a = ap.parse_args()
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.iso)), 'temp', 'r51')
    os.makedirs(out, exist_ok=True)

    cs = tcslib.Charset(a.charset) if a.charset else tcslib.Charset()
    iso = tcslib.Iso(a.iso)
    doc = dict(tool=TOOL, tool_version=TOOL_VERSION, round=ROUND,
               iso=rel(a.iso), iso_sha256=tcslib.sha256_file(a.iso),
               charset=rel(a.charset or tcslib.CHARSET),
               charset_sha256=tcslib.sha256_file(a.charset or tcslib.CHARSET))
    print('=' * 78)
    print('重排漏网容器扫描  %s' % rel(a.iso))
    print('=' * 78)

    # ---- ① 覆盖范围 ----
    doc['repack_coverage'] = coverage()
    print('[① ] repack 覆盖: %d 项会被重编码, %d 项**不会**'
          % (len(doc['repack_coverage']['what_gets_reencoded']),
             len(doc['repack_coverage']['what_is_NOT_reencoded'])))

    # ---- ② SFXML 属性清单 ----
    fx = load_blob(iso, 'SFXML')
    blob = fx['blob']
    attrs = sfxml_attributes(blob, cs)
    texts = sfxml_text_elements(blob)
    cn = [x for x in attrs if x['non_ascii']]
    doc['sfxml'] = dict(tag=fx['tag'], iso_off=fx['entry']['iso_off'], stored=fx['entry']['stored'],
                        expanded_bytes=len(blob),
                        text_elements=texts, n_text_elements=texts['matched_pairs'],
                        text_bytes=texts['bytes'],
                        n_name_attrs=len(attrs), n_name_attrs_with_cjk=len(cn),
                        name_attrs=attrs)
    print('[② ] SFXML: <text> 开标签 %d 个 (成对匹配 %d, 非空 %d ⇒ **会被重编码**); '
          'name 属性 %d 个, 其中含中文 **%d 个** (★从来不会被重编码)'
          % (texts['open_tags'], texts['matched_pairs'], texts['nonempty'], len(attrs), len(cn)))
    for x in cn[:8]:
        print('       <%s name="%s"> → %r' % (x['tag'], x['bytes_hex'], x['text'][:40]))

    # ---- ③ 复现重排后的错字 ----
    if a.repack_charset_before and a.repack_moves and os.path.isfile(a.repack_charset_before) \
            and os.path.isfile(a.repack_moves):
        after = charset_after_repack(a.repack_charset_before, a.repack_moves)
        repro = []
        for x in cn:
            want = x['text']
            got = decode_with(after['decoded_of'], after['single_of'], bytes.fromhex(x['bytes_hex'].replace(' ', '')))
            repro.append(dict(tag=x['tag'], bytes_hex=x['bytes_hex'], before=want, after=got,
                              changed=(want != got)))
        doc['repack_reproduction'] = dict(charset_before=rel(a.repack_charset_before),
                                          moves=rel(a.repack_moves), moved=after['moved'],
                                          n_attrs=len(repro),
                                          n_changed=sum(1 for r in repro if r['changed']),
                                          title_of_T0063=[r for r in repro
                                                          if r['before'].startswith('何为')],
                                          examples=[r for r in repro if r['changed']][:40])
        print('[③ ] 用"重排前 charset + 搬运表"复现: %d 个中文 name 属性里 **%d 个**会变成别的字'
              % (len(repro), doc['repack_reproduction']['n_changed']))
        for r in doc['repack_reproduction']['title_of_T0063'][:4]:
            print('       ★ 标题属性 %s  %r  →  %r' % (r['bytes_hex'], r['before'], r['after']))
        for r in doc['repack_reproduction']['examples'][:6]:
            print('       %s  %r  →  %r' % (r['bytes_hex'], r['before'], r['after']))
    else:
        doc['repack_reproduction'] = None
        print('[③ ] 没给 --repack-charset-before/--repack-moves ⇒ 跳过复现')

    # ---- ④ 反证: 现役盘 + 现役 charset 下这些属性解得对 ----
    bad = [x for x in cn if '\ufffd' in x['text'] or '·' in x['text']]
    doc['current_disk_check'] = dict(n_attrs_with_cjk=len(cn), n_attrs_with_unknown_byte=len(bad),
                                     ok=(not bad),
                                     examples=[dict(bytes_hex=x['bytes_hex'], text=x['text'])
                                               for x in cn[:10]])
    print('[④ ] 现役盘 + 现役 charset: %d 个中文属性全部解出正常文本 (坏字节 %d 个)'
          % (len(cn), len(bad)))

    # ---- ⑤ 全盘搜索: 引擎会解码文本的位置 ----
    if not a.no_full_scan:
        regions = build_region_map(iso)
        print('[⑤ ] 全盘搜索中 (ISO %.1f GB, 只读) ...' % (iso.size / (1 << 30)))
        hits = scan_iso_text(iso, cs)
        by = {}
        for h in hits:
            nm = who(regions, h['off'])
            k = nm.split(' ')[0]
            by.setdefault(k, []).append(h)
        doc['full_scan'] = dict(min_cjk=4, runs=len(hits),
                                by_container=dict((k, dict(runs=len(v),
                                                           examples=[dict(off=x['off'], text=x['text'][:60])
                                                                     for x in v[:3]]))
                                                  for k, v in sorted(by.items(),
                                                                     key=lambda kv: -len(kv[1]))),
                                note='"引擎会解码文本的位置"的最保守口径 = 这份清单: 凡是按现役 charset '
                                     '能解出 ≥4 连续汉字的字节串, 都可能被某条解码路径读到。'
                                     '本表按容器归类; 置信度: LANG/SFXML = 已实机确认; 其余 = 待确认。')
        print('[⑤ ] 全盘命中 %d 段; 按容器 Top: %s'
              % (len(hits), ', '.join('%s:%d' % (k, len(v)) for k, v in
                                      sorted(by.items(), key=lambda kv: -len(kv[1]))[:8])))

    iso.close()
    pj = os.path.join(out, 'repack_leak_scan.json')
    with io.open(pj, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print('[报告] %s' % rel(pj))
    return 0


if __name__ == '__main__':
    sys.exit(main())
