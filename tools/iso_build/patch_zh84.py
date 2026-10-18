# -*- coding: utf-8 -*-
r"""patch_zh84.py — 特别收录条目介绍文本按语义插入空格, 修复折行错乱 (GR_ZH84)

## 用户报障
主菜单→特别收录→武器/奖章/背景/访谈: 左下方**条目介绍的换行有明显问题**。

## 根因 (drawlog 实证, work/_dis/wrap_cal.py)
引擎折行 = `RSTextComponent::DoWordWrap @0x21CC10`:
  按**空白 token 切分** + 像素宽贪心累加, 直到超过 wrapW;
  **单个 token 比整行还宽**时走"硬断"分支 (0x21CD28 起) —— 先把当前行输出,
  再从下一行开头按 CharWidth **逐字硬断**。
中文介绍被译成**整段无空格连续串**(最长 111 字节 ≈ 55 汉字), 远超一行容量(15 汉字/行):
    ⇒ 首行只放下 "M18 " (4 字节), 浪费整行;
    ⇒ 后续每行**恰好 15 汉字硬断**, 词被劈开 ("弹体"/"构成"/"小片"), 标点可落行首。
实测 ZH82 (M18 定向地雷) 折行结果:
    "M18 " / "定向反步兵地雷由曲面的方形硬质" / "弹体制成，内装约 340 克 C3 " /
    "炸药。其破片面由方形金属破片构" / "成，起爆时破片以扇形射出。由于" / …
EN 原盘按空格自然折行, 语义完整 → 中文需补回"语义边界"。

## 本补丁 (纯数据, 零 ELF 风险)
在 `MENU.IMG#283 EN_SPECIAL_FEATURE.XML` 的 `<text>` 条目里, 于**中文标点/语义边界后插入 0x20 空格**,
使每个"无空格连续串" ≤ **14 汉字**(=28 字节, 留 1 字余量; 一行容量实测 15 汉字)。
    - 断点优先级: `。` `，` `、` `；` `：` `）` `》` 之后; 其次按累计字数强制断;
    - **不动** `<studio name>`(引擎比较键, 禁改) / `<item name>` / `<group name>` / 其它元素;
    - 尾部补 0x20 或短串, 使新内容长度 **恰好等于原长度**(等长覆写, 不重排 XML);
      若某条无法等长, 允许变长并由整体重排 (8 子流重划) 兜底。

用法: python patch_zh84.py <src_iso> <dst_iso>   (基底 = GR_ZH83)
"""
import json
import os
import re
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
from lz77_decode import lzo1x_decompress                      # noqa: E402
from lzo1x_c import compress as lzo_compress                  # noqa: E402

MENU_LBA = 776286
TAB_OFF, TAB_STEP = 0x830, 48
XML_IDX = 283
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')

MAXCJK = 13                       # 正文保守上限 (汉字数); 一行容量 15, 留余量避免切词
# ── 实测标定常量 (REVERSE_GLYPH_PIPELINE.md Q3, RAM dump frame 11030) ──
WRAPW = 270                       # comp+0x40 − (u8)comp+0xB4, 组件 VA 0x012F4960
W_CJK, W_ASCII = 16, 8            # CharWidth: 汉字恒 16;  ASCII 恒 8
SPACE_W, TRACK = 3, 1             # RSFont+0x14 / +0x18 (style 0)
FP = SPACE_W + TRACK              # 4 = 分隔成本 (每 token 与每字面空格各收一次)
# ── 实测标定常量 (EE RAM 单帧转储, work/_dis/REPORT_wrap_and_title.md) ──
WRAPW = 270                       # 介绍框 wrapW = comp[0x40] − comp[0xB4]
W_CJK, W_ASCII, W_SPACE, TRACK = 16, 8, 3, 1
LINE_CAP = 255                    # 单行内容上限 (= 15 汉字 × 17)
LEAD_BASE = 260                   # 段首有短编号 D 时: 首行上限 = LEAD_BASE − cost(D)
FILL_MIN = 0.85                   # 语义边界至少填到 cap 的比例, 否则按 cap 断
BREAK_AFTER = '。，、；：！？）】》”…'
_CACHE = {}


def load_charset():
    c = json.load(open(CHARSET, encoding='utf-8'))
    return dict(c['codes']), {k: tuple(v) for k, v in c['pair_of'].items()}


def enc(zh, codes, pairs):
    o = bytearray()
    for ch in zh:
        if ord(ch) < 0x80:
            o.append(ord(ch))
        elif ch in codes:
            o.append(codes[ch])
        elif ch in pairs:
            o += bytes(pairs[ch])
        else:
            raise AssertionError('字表无此字: %r' % ch)
    return bytes(o)


def dec(b, dc, dp):
    o, i = [], 0
    while i < len(b):
        if b[i] < 0x80:
            o.append(chr(b[i])); i += 1
        elif i + 1 < len(b) and (b[i], b[i + 1]) in dp:
            o.append(dp[(b[i], b[i + 1])]); i += 2
        elif b[i] in dc:
            o.append(dc[b[i]]); i += 1
        else:
            o.append('.'); i += 1
    return ''.join(o)


def _str_width(s, codes, pairs):
    """引擎 StringWidth(tok) = Σ CharWidth(ch) + (nChars−1)·tracking

    实测口径 (REVERSE_GLYPH_PIPELINE.md Q3, RAM dump frame 11030):
      汉字 CharWidth = **16** (cave 0x416FB0 固定; 17 只出现在"token 自身超宽"的逐字兜底里)
      ASCII CharWidth = 8;  tracking(+0x18) = 1;  spaceW(+0x14) = 3
    """
    if not s:
        return 0
    return sum(W_ASCII if ord(c) < 0x80 else W_CJK for c in s) + (len(s) - 1) * TRACK


def _engine_wrap(text, codes, pairs, wrapw=None):
    """★ 忠实还原 DoWordWrap @0x21CC10 —— 用实绘 9 行校准, wrapW 区间唯一 [254,272]。

    汇编顺序 (0x21CC84..0x21CF10):
        s1 = wrapW = comp+0x40 − (u8)comp+0xB4            # 当前行剩余宽度
        每个 token:  s3 = StringWidth(tok); 非行首则 s3 += fp
                     s1 -= s3;  s1 -= tracking
                     s1 < 0 ⇒ 断行, s1 = wrapW − s3 + fp
        每个字面空格: s1 -= fp                             # ★ fp 被收两次
    仅当 wrapw < StringWidth(tok) 才进逐字兜底 (0x21CD28)。
    """
    W = wrapw or WRAPW
    toks = [t for t in text.split(' ') if t]
    if not toks:
        return [text]
    lines, cur, s1, first = [], '', W, True
    for ti, tk in enumerate(toks):
        tw = _str_width(tk, codes, pairs)
        if W < tw:
            for ch in tk:                                  # 逐字兜底
                c = (W_ASCII if ord(ch) < 0x80 else W_CJK) + TRACK
                s1 -= c
                if s1 < 0:
                    lines.append(cur); cur, s1 = ch, W - c
                else:
                    cur += ch
            first = False
        else:
            s3 = tw + (0 if first else FP)
            s1 -= s3
            s1 -= TRACK
            if s1 < 0:
                lines.append(cur); cur, s1 = tk, W - s3 + FP
            else:
                cur += tk
            first = False
        if ti + 1 < len(toks):
            s1 -= FP
            cur += ' '
    if cur:
        lines.append(cur)
    return lines


def reflow(text, codes, pairs):
    """按**引擎真实折行行为**插入空格, 使折行落在语义边界且首行充分利用。

    ★ 口径全部由实测标定 (REVERSE_GLYPH_PIPELINE.md Q3 / 本文件 _engine_wrap):
        wrapW = 270;  fp = spaceW(3) + tracking(1) = 4;  汉字宽 16;  ASCII 宽 8
        StringWidth(tok) = Σ CharWidth + (nChars−1)·tracking
      实测回归: 未插空格的 M18 条目 → 9 行, 与我们模型**逐行一致**;
                wrapW 唯一性区间 [254,272] (270 在其中)。
      'M18 ' 首行浪费的充要条件: str_width(M18) + 2·fp + track + str_width(tok2) > wrapW
        ⇒ tok2 预算 = 270 − 26 − 8 − 1 = **235**;  原 tok2 = 14 汉字 = 237 > 235 (只差 2!)
      ⇒ 在段首短编号之后的**第一个语义边界**切一刀, tok2 缩短后首行即可容纳。
        实测首行填充 11% → 88%, 总行数 9 → 8。

    规则:
      1. `{br}`/`{p}` = 引擎显式换行/分段标记 → 拆段各自重排, 标记原样保留;
      2. 段首短编号 (M18/M136/OICW…) 与后继内容共占首行 (预算法);
      3. 其余正文: 保守上限 maxcjk 汉字 + **标点优先吸附** (词边界友好);
      4. 原文空格只增不删。
    """
    if re.search(r'\{br\}|\{p\}', text):
        return ''.join(reflow(p, codes, pairs) if p not in ('{br}', '{p}') else p
                       for p in re.split(r'(\{br\}|\{p\})', text))
    m = re.match(r'^([0-9A-Za-z][0-9A-Za-z./\-]{0,9})[ ]+(.+)$', text, re.S)
    if m and _str_width(m.group(1), codes, pairs) <= 60:
        lead, body = m.group(1), m.group(2)
        budget = WRAPW - _str_width(lead, codes, pairs) - 2 * FP - TRACK
        cut, acc = 0, 0
        for k, ch in enumerate(body):
            acc = _str_width(body[:k + 1], codes, pairs)
            if acc > budget:
                break
            if ch in BREAK_AFTER:
                cut = k + 1
        if cut == 0:
            for k in range(len(body)):
                if _str_width(body[:k + 1], codes, pairs) > budget:
                    cut = max(1, k - 1)
                    break
            else:
                cut = len(body)
        head, rest = body[:cut].rstrip(), body[cut:].lstrip()
        out = lead + (' ' + head if head else '')
        if rest:
            out += ' ' + _reflow_body(rest, codes, pairs)
        return out
    return _reflow_body(text, codes, pairs)


def _reflow_body(text, codes, pairs, max_cjk=None):
    """正文: 保守上限 + 标点优先吸附 (词边界友好)"""
    mj = max_cjk or MAXCJK
    out, run, n, pend = [], [], 0, []

    def sp():
        if out and out[-1] != ' ':
            out.append(' ')

    def flush():
        nonlocal run, n, pend
        out.extend(run); out.extend(pend); pend = []
        sp(); run, n = [], 0

    for ch in text:
        if ch == ' ':
            if n >= mj and not pend:
                flush()
            else:
                run.append(ch)
            continue
        if pend:
            if ch in BREAK_AFTER:
                pend.append(ch); flush(); continue
            out.extend(run); sp()
            run = list(pend) + [ch]; pend = []
            n = sum(1 for c in run if '\u4e00' <= c <= '\u9fff')
            if ch in BREAK_AFTER and n >= 6:
                flush()
            continue
        run.append(ch)
        if '\u4e00' <= ch <= '\u9fff':
            n += 1
        if ch in BREAK_AFTER and n >= 6:
            flush()
        elif n > mj:
            pend = [run.pop()]
            flush()
    if run:
        out.extend(run)
    if pend:
        out.extend(pend)
    return re.sub(r'\s{2,}', ' ', ''.join(out)).strip()


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
        if err is not None:
            break
        subs.append((bytes(dd), L, S))
        p += 8 + L
    return subs


def entry(d, idx, lba=MENU_LBA):
    base = lba * 2048
    r = struct.unpack_from('<12I', d, base + TAB_OFF + TAB_STEP * idx)
    return base, r[6], r[7], r[8]


def main(src, dst):
    codes, pairs = load_charset()
    dc = {v: k for k, v in codes.items()}
    dp = {tuple(v): k for k, v in pairs.items()}
    sd = open(src, 'rb').read()
    base, stored, real, off = entry(sd, XML_IDX)
    subs = subs_of(sd[base + off:base + off + stored])
    assert len(subs) == 8, '子流 %d' % len(subs)
    xml = b''.join(s[0] for s in subs)
    print('[in] XML %d B (槽 %d)' % (len(xml), stored))

    n_ok = 0
    n_skip = 0
    longest_before = longest_after = 0
    chunks = []                      # 逐段构建, 避免"回退删除"的偏移错误
    pos = 0
    for m in re.finditer(rb'<text>([^<]*)</text>', xml):
        chunks.append(xml[pos:m.start(1)])           # 原样保留 '<text>' 及之前
        raw = m.group(1)
        pos = m.end(1)                               # 跳过原文, '</text>' 留待下轮
        if len(raw) < 12:
            chunks.append(raw)
            continue
        zh = dec(raw, dc, dp)
        if not any('\u4e00' <= c <= '\u9fff' for c in zh):
            chunks.append(raw)
            continue
        new = reflow(zh, codes, pairs)
        before = max((sum(1 for c in s if '\u4e00' <= c <= '\u9fff')
                      for s in re.split(r'[ ]|\{br\}|\{p\}', zh)), default=0)
        after = max((sum(1 for c in s if '\u4e00' <= c <= '\u9fff')
                     for s in re.split(r'[ ]|\{br\}|\{p\}', new)), default=0)
        # 新算法按行宽预算做最优切分, 对所有含中文的介绍都是改进 → 一律重排
        # (仅当重排后反而产生了更长的无空格串时才保留原文, 理论上不会发生)
        if after > before:
            chunks.append(raw)
            n_skip += 1
            continue
        chunks.append(enc(new, codes, pairs))
        longest_before = max(longest_before, before)
        longest_after = max(longest_after, after)
        n_ok += 1
    chunks.append(xml[pos:])
    new_xml = b''.join(chunks)
    print('[reflow] 重排 %d 条介绍 (保留原文 %d 条)' % (n_ok, n_skip))
    print('[check ] 最长无空格 CJK 串: %d → %d  (上限 %d, 标点吸附容差 +1)'
          % (longest_before, longest_after, MAXCJK))
    assert not n_ok or longest_after <= MAXCJK + 1, \
        '仍有超长无空格串: %d (上限 %d+1)' % (longest_after, MAXCJK)
    print('[size  ] XML %d → %d B (%+d)' % (len(xml), len(new_xml), len(new_xml) - len(xml)))

    # ★ 结构完整性断言 (防止"替换逻辑产生多余闭合标签"这类事故)
    for pat, want in ((rb'<text>', xml.count(rb'<text>')),
                      (rb'</text>', xml.count(rb'</text>')),
                      (rb'<studio', xml.count(rb'<studio')),
                      (rb'<group', xml.count(rb'<group')),
                      (rb'<item', xml.count(rb'<item')),
                      (rb'</SpecialFeatures>', xml.count(rb'</SpecialFeatures>'))):
        got = new_xml.count(pat)
        assert got == want, '结构破坏: %s 由 %d 变为 %d' % (pat.decode(), want, got)
    # name 属性必须逐字节不变 (studio 是引擎比较键)
    na = re.findall(rb'name="([^"]*)"', xml)
    nb2 = re.findall(rb'name="([^"]*)"', new_xml)
    assert na == nb2, 'name 属性被改动 (%d vs %d)' % (len(na), len(nb2))
    print('[struct] 元素计数 + 145 个 name 属性 逐字节不变 ✓')

    # ★ 关键: 用**尾部 CRLF 填充区**吸收新增字节, 保持 XML 总长不变。
    #   背景: zh7 时代的内容塌陷使 ZH 系 XML 尾部留有约 41,206 B 的纯 CRLF 填充
    #   (有效内容仅到 75,280 B, </SpecialFeatures> 已闭合, 其后全是无意义换行)。
    #   若不做补偿, 重排会让 XML 变长 (ZH84 首次尝试 +1311 B) → 与 GR_ZH83 的
    #   116,486 B 基线不一致, 实测触发"特别收录全部未解锁"回归。
    #   故: 变长多少, 就从尾部删除等量 CRLF (2 字节一组), 使总长严格不变。
    delta = len(new_xml) - len(xml)
    if delta > 0:
        # 找有效内容结束位置 (</SpecialFeatures> 之后)
        m = new_xml.find(b'</SpecialFeatures>')
        end = (m + len(b'</SpecialFeatures>')) if m >= 0 else (new_xml.rfind(b'>') + 1)
        tail = new_xml[end:]
        assert len(tail) >= delta, '尾部填充不足: %d < %d' % (len(tail), delta)
        assert tail.count(b'\r\n') * 2 == len(tail), '尾部含非 CRLF 内容, 拒改'
        # 删除量必须为偶数 (CRLF 成对); 若多删 1 字节, 在有效内容尾部补 1 个换行保持总长
        cut = delta + (delta % 2)
        removed = len(tail) - len(tail[cut:])
        pad = 0
        if removed > delta:
            pad = removed - delta
        new_xml = new_xml[:end] + tail[cut:]
        if pad:
            # 多删了 pad 字节: 在有效内容末尾 (</SpecialFeatures> 之前) 补 pad 个换行
            mm = new_xml.find(b'</SpecialFeatures>')
            new_xml = new_xml[:mm] + b'\r\n'[:pad] + new_xml[mm:]
        print('[pad   ] 尾部扣除 %d B (补 %d B) → XML %d B' % (removed, pad, len(new_xml)))
        assert len(new_xml) == len(xml), '扣除后长度 %d != %d' % (len(new_xml), len(xml))

    # 子流边界: XML 总长已被尾部扣除补偿为"与基线等长", 故沿用原布局 (FR 8 子流)
    sizes = [s[2] for s in subs]
    assert sum(sizes) == len(new_xml), '子流 real 合计 %d != XML %d' % (sum(sizes), len(new_xml))
    frame = bytearray()
    q = 0
    for k, S in enumerate(sizes):
        chunk = new_xml[q:q + S]
        q += S
        c = lzo_compress(chunk, level=7, use_m1=True, use_m4=True)
        back, err, _ = lzo1x_decompress(c, out_size=S)
        assert err is None and back == chunk, '子流 %d 回环失败' % k
        frame += struct.pack('<II', len(c), S) + c
    assert len(frame) <= stored, '超槽 %+d' % (len(frame) - stored)
    print('[pack] %d B (槽 %d, 余 %d)' % (len(frame), stored, stored - len(frame)))

    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(base + off)
        f.write(bytes(frame) + b'\x00' * (stored - len(frame)))
        f.seek(base + off)
        rb = subs_of(f.read(stored))
        assert b''.join(s[0] for s in rb) == new_xml, '回读不符'
    print('[verify] 回读 8 子流逐字节一致 ✓')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1], sys.argv[2])
