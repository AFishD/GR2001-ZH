# -*- coding: utf-8 -*-
r"""patch_zh_sf_text.py — 修「特别收录→武器→定向地雷（M18）」介绍文本词内空格 (round27)

## 用户报障
主菜单 → 特别收录 → 武器 → 定向地雷（M18），右下介绍框**第 2 行**显示
「形硬 质弹体制成，」—— 「硬」与「质」之间有一个明显的半角空格。

## 根因（字节级实证, 见 docs/REPORT_zh82w_text_space.md）
不是残留换行符, 而是 **zh84 轮"折行补空格"填入的 0x20 在后续一轮重排中变成了行内空格**:

| 世代 | 该处字节 | 该处渲染 |
|---|---|---|
| ZH83(补丁前, `work/_dis/_xml82.txt`) | 无 | 硬质 连续 |
| ZH84 一轮插空格 (`work/_dis/_xml84.txt`) | `AC D6 | 20 | A5 C4` | 空格落在**首行边界**(14 汉字满行) → 行末, 不可见 |
| 现役 (zh84 二轮 v4 重排) | 同上 | 首行被重切成 12 汉字 ⇒ 该空格落到**第 2 行行内** → 可见「硬 质」 |

即: 空格是"上一代行边界"的遗留物; 行边界一移动, 它就从行尾变成行内空格。
同一 `<text>` 内 0x0D/0x0A/0x09 = **0 个**（全 69 条均无）, 排除"换行符没去掉"。

## 本补丁（等长、只改 1 个子流、只挪 1 个字节）
    <text>#10 (M18) 内容字节 +27 的 0x20 → **删除**（硬质 合并成 1 个 token, 8 汉字,
    宽 152 « 270 ⇒ 不会触发硬断, 折行只会变好）
    同一 `<text>` 末尾（`</SpecialFeatures>` 之前、`</text>` 之前）**补 1 个 0x20**
    ⇒ XML 总长不变 (116486 B) ⇒ 8 子流尺寸不变 ⇒ 8 子流边界不变 ⇒ 其它 68 条
      `<text>` 与全盘其余部分**逐字节不变**；尾部空格在末行行尾, 不可见、不影响折行。

只重压**含该条目的子流 0**；其余 7 个子流直接沿用原压缩字节（零风险）。

用法: python patch_zh_sf_text.py <src_iso> <dst_iso>
"""
import hashlib
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
XML_LEN = 116486                    # 现役盘实测值 (断言用)
TEXT_IDX = 10                       # <text>#10 = M18 定向地雷介绍 (1-based)
BAD = b'\xac\xd6\xa5\xc4'           # 硬 质   (硬=AC D6, 质=A5 C4)
BADSP = b'\xac\xd6\x20\xa5\xc4'     # 硬 0x20 质 = 本次要修的词内空格
LEAD_MAX = 0xAE                     # 引擎 DBCS lead 上界 (ELF 4 处 sltiu imm 实测)
W_CJK, W_ASCII, TRACK, FP, WRAPW = 16, 8, 1, 4, 270


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
        subs.append({'raw': raw[p:p + 8 + L], 'dec': bytes(dd), 'L': L, 'S': S, 'hdr': p})
        p += 8 + L
    return subs


def entry(d, idx, lba=MENU_LBA):
    base = lba * 2048
    r = struct.unpack_from('<12I', d, base + TAB_OFF + TAB_STEP * idx)
    return base, r[6], r[7], r[8]


def load_charset():
    c = json.load(open(CHARSET, encoding='utf-8'))
    return dict(c['codes']), {tuple(v): k for k, v in c['pair_of'].items()}


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


def dec_engine(b, dc, dp):
    """引擎口径解码: 0xA1 <= b < 0xAE 才是双字节 (lead<0xAE), 0xAF..0xFE 单字节。

    贪心 pair-first 会把 `AF A1 BD`(的 方) 误拆成 `AF A1`=弗 + `BD`=开 —— 游戏里
    实际画的是"的方"(0xAF 是单字节"的", ELF 0x416EE8/0x417160/0x41751C/0x5656A4
    四处 `sltiu reg, lead, 0xAE` 确证)。本函数用于**如实显示玩家看到的文本**。
    """
    o, i = [], 0
    while i < len(b):
        v = b[i]
        if v < 0x80:
            o.append(chr(v)); i += 1
        elif 0xA1 <= v < LEAD_MAX and i + 1 < len(b) and (v, b[i + 1]) in dp:
            o.append(dp[(v, b[i + 1])]); i += 2
        else:
            o.append(dc.get(v, '.')); i += 1
    return ''.join(o)


def strlen(s):
    return 0 if not s else sum(W_ASCII if ord(c) < 0x80 else W_CJK for c in s) + (len(s) - 1) * TRACK


def engine_wrap(text):
    """忠实还原 RSTextComponent::DoWordWrap @0x21CC10 (口径见 docs/REPORT_wrap_and_title.md)"""
    toks = [t for t in text.split(' ') if t]
    if not toks:
        return [text]
    lines, cur, s1, first = [], '', WRAPW, True
    for ti, tk in enumerate(toks):
        tw = strlen(tk)
        if WRAPW < tw:                                     # 硬断兜底
            for ch in tk:
                c = (W_ASCII if ord(ch) < 0x80 else W_CJK) + TRACK
                s1 -= c
                if s1 < 0:
                    lines.append(cur); cur, s1 = ch, WRAPW - c
                else:
                    cur += ch
            first = False
        else:
            s3 = tw + (0 if first else FP)
            s1 -= s3
            s1 -= TRACK
            if s1 < 0:
                lines.append(cur); cur, s1 = tk, WRAPW - s3 + FP
            else:
                cur += tk
            first = False
        if ti + 1 < len(toks):
            s1 -= FP
            cur += ' '
    if cur:
        lines.append(cur)
    return lines


def wrap_report(zh):
    """返回 (折行, 超宽 token, 行内可见的"词内空格"(两侧皆汉字))"""
    toks = [t for t in zh.split(' ') if t]
    lines = engine_wrap(zh)
    hard = [t for t in toks if strlen(t) > WRAPW]
    tok_line, ci = {}, 0
    for li, line in enumerate(lines):
        for t in [x for x in line.split(' ') if x]:
            if ci < len(toks) and t == toks[ci]:
                tok_line[ci] = li
                ci += 1
    vis = []
    pos = 0
    for k in range(len(toks) - 1):
        sp = zh.find(' ', pos)
        pos = sp + 1
        if tok_line.get(k) == tok_line.get(k + 1) and k in tok_line:
            a, b = zh[sp - 1], zh[sp + 1]
            if '\u4e00' <= a <= '\u9fff' and '\u4e00' <= b <= '\u9fff':
                vis.append((k, zh[sp - 4:sp + 4]))
    return lines, hard, vis


def main(src, dst):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    codes, dp = load_charset()               # load_charset 返回 (codes, {bytes:字})
    dc = {v: k for k, v in codes.items()}
    sd = open(src, 'rb').read()
    base, stored, real, off = entry(sd, XML_IDX)
    print('[in ] %s' % src)
    print('[in ] MENU.IMG#283  base=0x%X stored=%d real=%d off=0x%X slot@0x%X'
          % (base, stored, real, off, base + off))
    subs = subs_of(sd[base + off:base + off + stored])
    assert len(subs) == 8, '子流 %d 个 (期望 8)' % len(subs)
    sizes = [s['S'] for s in subs]
    xml = b''.join(s['dec'] for s in subs)
    assert len(xml) == sum(sizes)
    print('[in ] XML %d B (子流解压尺寸 %s, 压缩后 %s, 帧 %d / 槽 %d)'
          % (len(xml), sizes, [s['L'] for s in subs],
             sum(s['L'] + 8 for s in subs), stored))
    assert len(xml) == XML_LEN, 'XML 长度 %d != 基线 %d (盘不对?)' % (len(xml), XML_LEN)

    # ── 定位 <text>#10 的 硬|质 空格 ──
    ms = list(re.finditer(rb'<text>([^<]*)</text>', xml))
    assert len(ms) == 69, '<text> 条数 %d != 69' % len(ms)
    m = ms[TEXT_IDX - 1]
    body_a, body_b = m.start(1), m.end(1)
    raw = xml[body_a:body_b]
    zh = dec_engine(raw, dc, dp)
    print('[tgt] <text>#%d @xml 0x%X..0x%X (len %d)' % (TEXT_IDX, body_a, body_b, len(raw)))
    print('[tgt] 修改前文本: %s' % zh)
    assert '定向反步兵地雷' in zh, '目标条目内容不符 (期望 M18 定向地雷介绍)'
    hits = [h for h in re.finditer(re.escape(BADSP), xml) if body_a <= h.start() < body_b]
    assert len(hits) == 1, '硬|质 词内空格命中 %d 次 (期望 1)' % len(hits)
    sp = hits[0].start() + 2                        # 0x20 的 XML 偏移
    assert xml[sp] == 0x20 and xml[sp - 2:sp] == BAD[:2] and xml[sp + 1:sp + 3] == BAD[2:], '字节上下文不符'
    print('[tgt] 空格 XML@0x%X (条目内 +%d), 前置字节 %s, 后置字节 %s'
          % (sp, sp - body_a, xml[sp - 6:sp].hex(), xml[sp + 1:sp + 7].hex()))

    # 必须整个条目落在**子流 0**内 ⇒ 8 子流尺寸不变
    bnd, q = [], 0
    for k, S in enumerate(sizes):
        bnd.append((q, q + S, k)); q += S

    def sub_of(p):
        for a, b, k in bnd:
            if a <= p < b:
                return k
        return -1
    assert sub_of(body_a) == sub_of(body_b - 1) == 0, \
        '目标条目跨子流 (sub %d..%d) — 本补丁要求不跨流' % (sub_of(body_a), sub_of(body_b - 1))
    assert sub_of(sp) == 0 and sub_of(body_b - 1) == 0

    # ── 等长改写: 删内嵌空格, 同一条目尾部补 1 个 0x20 ──
    end = xml.index(b'</text>', sp)
    assert end == body_b, '</text> 位置 %d != 条目尾 %d' % (end, body_b)
    new_xml = xml[:sp] + xml[sp + 1:end] + b'\x20' + xml[end:]
    assert len(new_xml) == len(xml), '等长断言失败: %d vs %d' % (len(new_xml), len(xml))
    assert new_xml[:sp] == xml[:sp]
    assert new_xml[sp:sp + 2] == BAD[2:], '删除后此处应是 质 的首字节'
    assert new_xml[end - 1] == 0x20 and new_xml[end:end + 7] == b'</text>'
    # 逐条目: 只有 #10 变
    for i, mm in enumerate(re.finditer(rb'<text>([^<]*)</text>', new_xml), start=1):
        if i == TEXT_IDX:
            continue
        assert mm.group(1) == ms[i - 1].group(1), '<text>#%d 意外变化' % i
    new_zh = dec_engine(new_xml[body_a:end], dc, dp)
    print('[tgt] 修改后文本: %s' % new_zh)
    assert new_zh == zh.replace('\u786c \u8d28', '\u786c\u8d28') + ' ', '文本改写结果不符预期'
    assert '\u786c\u8d28' in new_zh and '\u786c \u8d28' not in new_zh, '硬质 未合并'

    # ── 折行前后对照 (引擎模型) ──
    l0, h0, v0 = wrap_report(zh)
    l1, h1, v1 = wrap_report(new_zh)
    print('[wrap] 修改前 %d 行 / 超宽 token %d / 行内空格 %d 处: %s' % (len(l0), len(h0), len(v0), v0))
    for i, ln in enumerate(l0):
        print('   -L%d %r' % (i + 1, ln))
    print('[wrap] 修改后 %d 行 / 超宽 token %d / 行内空格 %d 处: %s' % (len(l1), len(h1), len(v1), v1))
    for i, ln in enumerate(l1):
        print('   +L%d %r' % (i + 1, ln))
    assert not h1, '修改后出现超宽 token(硬断): %r' % h1
    assert not v1, '修改后仍有行内可词内空格: %r' % v1

    # ── 结构断言 (与 zh84 同口径) ──
    for pat in (rb'<text>', rb'</text>', rb'<studio', rb'<group', rb'<item', rb'</SpecialFeatures>'):
        assert new_xml.count(pat) == xml.count(pat), '结构破坏: %s' % pat.decode()
    assert re.findall(rb'name="([^"]*)"', new_xml) == re.findall(rb'name="([^"]*)"', xml), 'name 属性被改'
    print('[struct] 元素计数 + %d 个 name 属性逐字节不变 OK'
          % len(re.findall(rb'name="([^"]*)"', xml)))

    # ── 重压: 只重压变了的子流, 其余沿用原压缩字节 ──
    frame = bytearray()
    n_repack = 0
    for k, S in enumerate(sizes):
        chunk = new_xml[sum(sizes[:k]):sum(sizes[:k]) + S]
        if chunk == subs[k]['dec']:
            frame += subs[k]['raw']                      # 原样沿用
            continue
        c = lzo_compress(chunk, level=7, use_m1=True, use_m4=True)
        back, err, _ = lzo1x_decompress(c, out_size=S)
        assert err is None and back == chunk, '子流 %d 回环失败' % k
        frame += struct.pack('<II', len(c), S) + c
        n_repack += 1
        print('[pack] 子流 %d 重压 %d → %d B' % (k, subs[k]['L'], len(c)))
    assert n_repack == 1, '应只重压 1 个子流, 实际 %d' % n_repack
    assert len(frame) <= stored, '超槽 %+d' % (len(frame) - stored)
    print('[pack] 帧 %d B / 槽 %d (余 %d)' % (len(frame), stored, stored - len(frame)))

    # ── 写盘 + 回读自验 ──
    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(base + off)
        f.write(bytes(frame) + b'\x00' * (stored - len(frame)))
        f.seek(base + off)
        rb = subs_of(f.read(stored))
        assert len(rb) == 8, '回读子流 %d 个' % len(rb)
        got = b''.join(x['dec'] for x in rb)
        assert got == new_xml, '回读不符'

    # 槽前区域逐块比较
    with open(src, 'rb') as f1, open(dst, 'rb') as f2:
        f1.seek(0); f2.seek(0)
        rest = base + off
        while rest > 0:
            n = min(8 << 20, rest)
            assert f1.read(n) == f2.read(n), '槽前区域被改'
            rest -= n
    print('[verify] 回读 8 子流逐字节一致; 槽前 %d B 逐字节不变' % (base + off))

    # 槽后区域
    same = True
    with open(src, 'rb') as f1, open(dst, 'rb') as f2:
        f1.seek(base + off + stored); f2.seek(base + off + stored)
        while True:
            x, y = f1.read(8 << 20), f2.read(8 << 20)
            if x != y:
                same = False
                break
            if not x:
                break
    if same:
        print('[verify] 槽后至盘尾逐字节一致 OK')
    else:
        print('[verify] !! 槽后区域存在差异')
        raise AssertionError('槽后区域被改动')

    h_src = hashlib.sha256(sd).hexdigest()
    h_dst = hashlib.sha256(open(dst, 'rb').read()).hexdigest()
    print('[hash] src sha256 %s' % h_src)
    print('[hash] dst sha256 %s' % h_dst)
    info = {
        'patch': 'tools/iso_build/patch_zh_sf_text.py',
        'src_iso': os.path.abspath(src), 'src_sha256': h_src,
        'dst_iso': os.path.abspath(dst), 'dst_sha256': h_dst,
        'target': 'MENU.IMG#283 EN_SPECIAL_FEATURE.XML <text>#10 (M18 定向地雷介绍)',
        'edit': 'delete 0x20 @xml 0x%X (硬|质 词内空格); append 0x20 @text end (equal length)'
                % sp,
        'xml_len_before': len(xml), 'xml_len_after': len(new_xml),
        'substream_sizes': sizes,
        'text_before': zh, 'text_after': new_zh,
        'wrap_before': l0, 'wrap_after': l1,
        'visible_intraword_spaces_before': v0, 'visible_intraword_spaces_after': v1,
    }
    return info


if __name__ == '__main__':
    info = main(sys.argv[1], sys.argv[2])
    if len(sys.argv) > 3:
        with open(sys.argv[3], 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        print('[json] -> %s' % sys.argv[3])
