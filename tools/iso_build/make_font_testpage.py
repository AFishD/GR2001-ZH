# -*- coding: utf-8 -*-
r"""make_font_testpage.py — 「字库测试页」: 把码表里的**全部字符**塞进
「特别收录 → 访谈 → 开发访谈 1」的 `<text>` 里 (原位替换), 其余内容一字不动。

═══════════════════════════════════════════════════════════════════════════════
它解决什么问题
═══════════════════════════════════════════════════════════════════════════════
字库(码表)有 1285 个字符 (1175 个对偶码 + 110 个单字节码), 散落在全盘 2261 条
文本里 —— 想看"某个字的字形对不对 / 有没有墨 / 会不会画成别的字", 得先找到那个字
出现在哪一页。本工具**把所有字符一次性铺到一页上** (特别收录的第一篇访谈),
测试者翻到那一页就能一眼扫完整个字库。

目标页的定位依据 (只读侦察, 见 docs/REPORT_font_testpage.md §1):
  · 容器 = MENU.IMG#283 `EN_SPECIAL_FEATURE.XML` (LZO 帧, 展开 116486 B);
  · `<studio name="Interview">` 的**第一个** `<item name="开发访谈 1">`
    的 `<text>` 载荷 = blob `[0xE669, 0xF158)` 共 2799 B (解出 1720 字)。

═══════════════════════════════════════════════════════════════════════════════
文本格式
═══════════════════════════════════════════════════════════════════════════════
    字库测试页 全 1285 字 · 每行 24 字{br}<24 字>{br}<24 字>{br}…<余数>
  · 首行 = 统计 (`--title` + 总字数 + 每行字数);
  · 随后每 `--cols` 个字插一个 `{br}` (行内**不插空格**);
  · `--page-lines N>0` (默认 5) 时每 N 行把 `{br}` 换成 `{p}` —— ★ **`{p}` 是翻页符**
  (原版「开发访谈 1」1720 字用了 16 个 `{p}` ≈ 17 页, 每页约 107 字);
  **不分页(page_lines=0)会把上百行挤在一页 ⇒ 实机整页空白** (round60 用户实测)。
  · 字符顺序 = `--order code` (默认, 按**编码字节**升序 = 码表顺序) 或 `unicode`;
  · 结尾习惯跟随原文: 原文末尾是 `{br}`/`{p}` 就补一个同类的 (实测原文末尾是
    36 个空格、无标记 ⇒ 不补), 再把载荷用**空格补齐到原文长度**。

★ 为什么必须"补齐到原文长度": `<text>` 载荷长度一变, `dump_text_csv` 出的
  `len_bytes` 就对不上盘 ⇒ 后续 `inject_text_csv --check-only` 会判"表已过期"
  (exit 1)。补齐成等长 ⇒ 载荷偏移/长度都不变, 注入器的结构核对照常通过,
  而且 blob 总长不变 ⇒ 只有目标 `<text>` 那一段字节变, 其余**逐字节不动**。

═══════════════════════════════════════════════════════════════════════════════
硬门禁 (任何一条不过 ⇒ 非 0 退出, **不写盘** 或 报错)
═══════════════════════════════════════════════════════════════════════════════
  门禁① (写盘前): 除目标 `<text>` 区间外, blob **逐字节不变**
                  (前缀相同 + 后缀相同; 长度变化时按位移比较);
  门禁② (回读):   每一个码表字都能在新 `<text>` 里解出来 (逐个字符点名检查,
                  缺一个就报错), 且解出的文本与预期**逐字符相同**;
  门禁③ (回读):   其它 `<text>` / `<item>` / `<group>` / `<studio>` 与
                  MENU.IMG 其它条目**逐字节不变**; IMG 条目表 off/stored/real 不变;
  另外: LZO 重压**回环断言** (`lzo_subs(帧) == 新 blob` 逐字节) + 超槽即中止
        (绝不截断、绝不静默丢字) + ISO 尺寸不变。

用法:
  python tools/iso_build/make_font_testpage.py <src.iso> [<dst.iso>]
         [--cols N] [--title T] [--order code|unicode] [--page-lines N]
         [--charset PATH] [--item-name NAME] [--expect-prefix STR]
         [--dry-run] [--allow-grow] [--report PATH]

  · `<dst.iso>` 省略 = 原地改写 `<src.iso>`; src != dst 时先整盘复制再改那一段;
  · `--dry-run` 只跑到门禁①, 打印"会写什么"和帧/blob 摘要, 不写盘;
  · 同一源盘跑两次 ⇒ 产物字节完全相同 (无时间戳、无随机、无字典序依赖)。
"""
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, HERE)

try:                                                       # 中文输出在管道里也要可读
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:                                                          # noqa: BLE001
    pass

import tcslib                                                             # noqa: E402
import inject_text_csv as inj                                             # noqa: E402

CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
DEFAULT_TITLE = '字库测试页'
DEFAULT_COLS = 24
# ★ round60 实机订正: `{p}` 是**翻页符**; 不分页(page_lines=0)会把上百行挤在一页 ⇒ 实机整页空白
DEFAULT_PAGE_LINES = 5
DEFAULT_ITEM = '开发访谈 1'
DEFAULT_PREFIX = '开发手记：第一辑'

ITEM_RE = re.compile(rb'<item\b([^>]*)>')
NAME_RE = re.compile(rb'name\s*=\s*"([^"]*)"')
TEXT_OPEN_RE = re.compile(rb'<text>')
TEXT_CLOSE_RE = re.compile(rb'</text>')


def rel(p):
    try:
        r = os.path.relpath(p, REPO)
    except ValueError:
        return p.replace('\\', '/')
    return r.replace('\\', '/') if not r.startswith('..') else p.replace('\\', '/')


# ═════════════════════════════ 码表 → 字符清单 ═════════════════════════════

def load_chars(cs, order='code'):
    """码表里的**全部**字符, 去重, 确定性排序。

    返回 ``(chars, info)``; chars = [char...] (同一字只出现一次)。
      · pair_of 1175 条 (对偶码) + codes 110 条 (单字节码) —— 两张表**无交集**,
        合计 1285 个不同字符 (本函数仍做去重与断言, 不假设它俩一定不重叠);
      · order='code'    = 按**编码字节**升序 (单字节码按 (byte,), 对偶码按 (b1,b2),
                          两者混排 ⇒ 就是"码表顺序", 一眼能对上码位);
        order='unicode' = 按 Unicode 码位升序。
    """
    enc = {}
    for ch, (b1, b2) in cs.enc_pair.items():
        enc[ch] = bytes((b1, b2))
    for ch, b in cs.enc_single.items():
        if ch in enc and enc[ch] != bytes((b,)):
            raise SystemExit('!! 码表自相矛盾: %r 同时有对偶码与单字节码' % ch)
        enc[ch] = bytes((b,))
    if order == 'code':
        chars = sorted(enc, key=lambda c: (enc[c], c))
    elif order == 'unicode':
        chars = sorted(enc, key=ord)
    else:
        raise SystemExit('!! --order 只认 code / unicode: %r' % order)

    bad = []
    for ch in chars:
        if cs.is_placeholder(ch):
            bad.append((ch, '落在按键图标占位区 U+E080..U+E0FF'))
            continue
        try:
            b = cs.encode_strict(ch)                  # 内含 encode/decode 对称自检
        except Exception as e:                                             # noqa: BLE001
            bad.append((ch, 'encode_strict 失败: %s' % e))
            continue
        if b != enc[ch]:
            bad.append((ch, '编码字节与码表不一致: %s vs %s' % (b.hex(), enc[ch].hex())))
    if bad:
        for ch, why in bad[:8]:
            print('   ✗ %r: %s' % (ch, why))
        raise SystemExit('!! %d 个码表字**编不出去** —— 拒绝生成测试页' % len(bad))
    n_pair = sum(1 for c in chars if len(enc[c]) == 2)
    n_single = len(chars) - n_pair
    info = dict(n=len(chars), n_pair=n_pair, n_single=n_single,
                n_pair_table=len(cs.enc_pair), n_single_table=len(cs.enc_single),
                order=order, bytes=sum(len(enc[c]) for c in chars),
                dup_in_tables=len(cs.enc_pair) + len(cs.enc_single) - len(chars))
    return chars, info


# ═════════════════════════════ 测试文本 ═════════════════════════════

def build_text(chars, cols, title, page_lines, cs, tail_habit=None):
    """拼出测试文本 (str)。返回 ``(text, info)``。

    tail_habit = 原文末尾的收尾标记 ('{br}' / '{p}' / None) —— 有就补一个同类的。

    ★ round60 实机订正: **`{p}` 是翻页符, 不是段落分隔**。
    原版「开发访谈 1」1720 字里用了 **16 个 `{p}`**(≈17 页, 每页约 107 字)；
    而 `page_lines=0` 的初版一个 `{p}` 都没有 ⇒ 135 行全挤在一页 ⇒ **整页空白**
    (用户实机报告: "开发者访谈什么文字都不显示, 其它页正常")。
    ⇒ 默认 `page_lines=5` (5 行 × cols 字 ≈ 100~120 字/页, 与原版密度相当)。
    """
    if cols < 1:
        raise SystemExit('!! --cols 必须 >= 1')
    n = len(chars)
    head = '%s 全 %d 字 · 每行 %d 字' % (title, n, cols)
    miss = [c for c in head if ord(c) >= 0x80 and c not in cs.enc_pair and c not in cs.enc_single]
    if miss:
        raise SystemExit('!! --title 里有码表没有的字, 会写不出: %r\n'
                         '   换个标题 (用码表里有的字), 或 --title 用纯 ASCII。' % ''.join(miss))
    parts = [head, '{p}']                      # ★ 标题单独一页, 正文从第 2 页开始
    n_lines = 0
    for i, ch in enumerate(chars):
        parts.append(ch)
        if i == n - 1:
            break
        if (i + 1) % cols == 0:
            n_lines += 1
            parts.append('{p}' if (page_lines and n_lines % page_lines == 0) else '{br}')
    if tail_habit:
        parts.append(tail_habit)
    text = ''.join(parts)
    # ★ round61 实测守卫: 引擎对"连续 0x80..0x9F 段"有硬限制
    #   (全语料 94 个载荷里最长只出现过 3 连; 20 连 ⇒ 取文本失败 ⇒ 整页空白 + 无法翻页)
    enc = b''
    for ch in text:
        if ord(ch) < 0x80:
            enc += bytes([ord(ch)])
        elif ch in cs.enc_pair:
            enc += bytes(cs.enc_pair[ch])
        elif ch in cs.enc_single:
            enc += bytes([cs.enc_single[ch]])
        else:
            enc += b'?'
    run = best = 0
    for b in enc:
        run = run + 1 if 0x80 <= b <= 0x9F else 0
        best = max(best, run)
    if best > 3:
        raise SystemExit(
            '!! 编码后有 %d 个**连续 0x80..0x9F 字节** (安全上限 3) —— 引擎会取不到整段文本,\n'
            '   实机表现为"该页正文整块空白且无法翻页"(round61 用 GR_TEST_FONT2/3 实拍确认)。\n'
            '   ⇒ 换 --order unicode(默认), 或把单字节码打散后再排。' % best)
    info = dict(header=head, cols=cols, page_lines=page_lines,
                rows=(n + cols - 1) // cols, n_br=text.count('{br}'),
                n_p=text.count('{p}'), tail_marker=tail_habit, n_chars=n)
    return text, info


def tail_marker_of(text):
    """原文(去掉尾部空白后)末尾的收尾标记 —— '{br}' / '{p}' / None。"""
    t = (text or '').rstrip(' \t\r\n')
    for tag in ('{br}', '{p}'):
        if t.endswith(tag):
            return tag
    return None


# ═════════════════════════════ 目标定位 ═════════════════════════════

def find_target(blob, cs, item_name, expect_prefix):
    """在 SFXML blob 里定位目标 `<text>` 载荷区间。

    做法: 找**唯一**一个 `name="…"` 解出来 == item_name 的 `<item>`,
          取它后面第一个 `<text>…</text>` 的载荷。
    返回 dict(name, item_off, open_off, close_off, a, b, data, text)
    """
    hits = []
    for m in ITEM_RE.finditer(blob):
        nm = NAME_RE.search(m.group(1))
        if not nm:
            continue
        name = cs.decode(nm.group(1))[0]
        if name == item_name:
            hits.append((m.start(), name))
    if len(hits) != 1:
        raise SystemExit('!! 目标 <item name=%r> 命中 %d 个 (要求**恰好 1 个**) —— 拒绝改写'
                         % (item_name, len(hits)))
    item_off = hits[0][0]
    mo = TEXT_OPEN_RE.search(blob, item_off)
    if not mo:
        raise SystemExit('!! 目标 item 后面找不到 `<text>`')
    mc = TEXT_CLOSE_RE.search(blob, mo.end())
    if not mc:
        raise SystemExit('!! 目标 `<text>` 没有 `</text>`')
    a, b = mo.end(), mc.start()
    data = blob[a:b]
    text = cs.decode(data)[0]
    if expect_prefix and not text.startswith(expect_prefix):
        raise SystemExit('!! 目标 <text> 的内容不是预期的那一篇:\n'
                         '   期望开头 %r\n   实际开头 %r\n'
                         '   (源盘可能已经打过本补丁; 要强行改写用 --expect-prefix "")'
                         % (expect_prefix, text[:len(expect_prefix) + 12]))
    return dict(name=item_name, item_off=item_off, open_off=mo.start(), close_off=mc.start(),
                a=a, b=b, data=data, text=text)


# ═════════════════════════════ 门禁工具 ═════════════════════════════

def locality(blob, new, a, b):
    """门禁①: 除 [a,b) 外逐字节不变? 返回 dict。

    new = blob[:a] + <新载荷> + blob[b:] (长度可不同) ⇒ 判据 = 前缀逐字节相同
    且后缀逐字节相同 (按位移对齐)。再给出实际差异的字节数与区间 (给人看)。
    """
    delta = len(new) - len(blob)
    pre_ok = new[:a] == blob[:a]
    suf_ok = new[b + delta:] == blob[b:]
    if delta == 0:
        diff = [i for i in range(len(blob)) if new[i] != blob[i]]
        outside = [i for i in diff if not (a <= i < b)]
    else:                                   # 位移后逐下标比较没意义 ⇒ 只报前缀/后缀判据
        diff, outside = [], []
    return dict(delta=delta, prefix_ok=pre_ok, suffix_ok=suf_ok,
                n_diff=(len(diff) if delta == 0 else None),
                first_diff=(diff[0] if diff else None),
                last_diff=(diff[-1] if diff else None),
                n_outside=len(outside), outside=outside[:8])


def parse_entries(blob):
    return {k: bytes(d) for (k, _o, _l, d) in tcslib.parse_sfxml(blob)}


# ═════════════════════════════ main ═════════════════════════════

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--cols', type=int, default=DEFAULT_COLS, help='每行几个字 (默认 %d)' % DEFAULT_COLS)
    ap.add_argument('--title', default=DEFAULT_TITLE, help='首行统计的标题 (默认 %s)' % DEFAULT_TITLE)
    ap.add_argument('--order', default='unicode', choices=('code', 'unicode'),
                    help='字符顺序: **unicode(默认)** / code=按编码字节升序(码表顺序)。'
                         '★ round61 实测: code 序会把 110 个单字节码(0x80..0xFF)排成连续段, '
                         '而引擎对"连续 0x80..0x9F 段"有硬限制(全语料最长只见过 3 连) '
                         '⇒ 连续 20 连会让引擎**取文本失败、整页空白且无法翻页**。')
    ap.add_argument('--page-lines', type=int, default=DEFAULT_PAGE_LINES,
                    help='每 N 行用 {p} 翻页 (默认 %d; **0=不分页 —— 实机会整页空白**, 见 round60 订正)'
                         % DEFAULT_PAGE_LINES)
    ap.add_argument('--charset', default=CHARSET)
    ap.add_argument('--item-name', default=DEFAULT_ITEM)
    ap.add_argument('--expect-prefix', default=DEFAULT_PREFIX)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--allow-grow', action='store_true',
                    help='新文本比原文长时, 允许从容器尾部陈旧区吸收 (会位移后续字节, '
                         '并使 dump 出的 len_bytes 与盘不符 —— 默认拒绝)')
    ap.add_argument('--report', default=None)
    a = ap.parse_args()
    src = os.path.abspath(a.src)
    dst = os.path.abspath(a.dst or a.src)
    print('=' * 78)
    print('字库测试页: 把码表全部字符写进「特别收录 → %s」的 <text>' % a.item_name)
    print('  src = %s' % rel(src))
    print('  dst = %s' % rel(dst))
    print('=' * 78)

    cs = tcslib.Charset(a.charset)
    chars, cinfo = load_chars(cs, a.order)
    print('[码表] %s' % rel(a.charset))
    print('[码表] 对偶码 %d + 单字节码 %d = 表内 %d 条; 去重后**不同字符 %d 个**'
          ' (对偶 %d / 单字节 %d, 共 %d B)'
          % (cinfo['n_pair_table'], cinfo['n_single_table'],
             cinfo['n_pair_table'] + cinfo['n_single_table'], cinfo['n'],
             cinfo['n_pair'], cinfo['n_single'], cinfo['bytes']))
    if cinfo['dup_in_tables']:
        print('[码表] ⚠ 两张表有 %d 个重复字符 (已去重, 只出现一次)' % cinfo['dup_in_tables'])
    print('[码表] 顺序 = %s; 首 8 字 = %r … 末 8 字 = %r'
          % (a.order, ''.join(chars[:8]), ''.join(chars[-8:])))

    iso = tcslib.Iso(src)
    spec = tcslib.RES['SFXML']['copies'][0]
    c = inj.Container(iso, 'SFXML', spec, cs)
    print('[容器] %s = %s#%d  槽 %d B / 帧 %d B (余 %d B) / 展开 %d B / %d 个子流'
          % (c.tag, c.img, c.idx, c.slot, c.frame_len, c.slot - c.frame_len,
             len(c.blob), len(c.subs)))

    tgt = find_target(c.blob, cs, a.item_name, a.expect_prefix)
    print('[目标] <item name=%r> @blob 0x%X; <text> 载荷 [0x%X, 0x%X) = %d B, 解出 %d 字'
          % (tgt['name'], tgt['item_off'], tgt['a'], tgt['b'], len(tgt['data']),
             len(tgt['text'])))
    print('[目标] 原文开头 %r' % tgt['text'][:44])
    print('[目标] 原文结尾 %r' % tgt['text'][-44:])
    habit = tail_marker_of(tgt['text'])
    print('[目标] 原文收尾标记 = %s; 尾部空白 %d 个空格'
          % (habit or '(无)', len(tgt['text']) - len(tgt['text'].rstrip(' '))))

    text, tinfo = build_text(chars, a.cols, a.title, a.page_lines, cs, habit)
    new = cs.encode_strict(text)
    print('[文本] 首行 = %r' % tinfo['header'])
    print('[文本] %d 字 → %d B (%d 行 × %d 字, {br} × %d, {p} × %d)'
          % (tinfo['n_chars'], len(new), tinfo['rows'], a.cols, tinfo['n_br'], tinfo['n_p']))
    print('[文本] 开头 %r' % text[:40])
    print('[文本] 结尾 %r' % text[-40:])

    # ---- 与原文长度对齐 (等长 ⇒ 偏移/长度都不变, 注入器结构核对照过) ----
    pad = 0
    if len(new) < len(tgt['data']):
        pad = len(tgt['data']) - len(new)
        new = new + b' ' * pad
        text = text + ' ' * pad
        print('[长度] 比原文短 %d B ⇒ 用空格补齐到 %d B (偏移/长度不变, 零位移)'
              % (pad, len(new)))
    elif len(new) > len(tgt['data']):
        over = len(new) - len(tgt['data'])
        tail_free = len(c.blob) - c.used_end
        print('[长度] ★ 比原文**长 %d B** (容器尾部陈旧区 %d B)' % (over, tail_free))
        if not a.allow_grow:
            raise SystemExit('!! 拒绝改写: 载荷变长会位移后续字节, 且 dump 出的 len_bytes\n'
                             '   与盘不符 (注入器会判"表已过期")。\n'
                             '   怎么办: 把 --cols 调大 (每行多放几个字 ⇒ {br} 更少), 或\n'
                             '           确实要变长再加 --allow-grow。')
        if over > tail_free:
            raise SystemExit('!! 需要扩容 %d B, 容器尾部只有 %d B 陈旧区可吸收' % (over, tail_free))

    # ---- 拼新 blob + 门禁① (写盘前) ----
    new_blob = c.blob[:tgt['a']] + new + c.blob[tgt['b']:]
    loc = locality(c.blob, new_blob, tgt['a'], tgt['b'])
    print('[门禁①] blob %d → %d B (Δ%+d); 前缀相同=%s 后缀相同=%s; 差异字节 %s, '
          '区间外 %d 字节'
          % (len(c.blob), len(new_blob), loc['delta'], loc['prefix_ok'], loc['suffix_ok'],
             loc['n_diff'] if loc['n_diff'] is not None else '(位移)',
             loc['n_outside']))
    if not (loc['prefix_ok'] and loc['suffix_ok']) or loc['n_outside']:
        raise SystemExit('!! 门禁① 不过: 有改动落在目标 <text> 区间之外 (%s)' % loc['outside'])
    print('[门禁①] ✓ 除目标 <text> 区间外, blob 逐字节不变')

    # ---- LZO 重压 + 回环断言 ----
    frame, n_rep = c.repack(new_blob)
    back = b''.join(s[0] for s in tcslib.lzo_subs(frame))
    if back != new_blob:
        k = next(i for i in range(min(len(back), len(new_blob))) if back[i] != new_blob[i])
        raise SystemExit('!! LZO 回环断言失败 @%d (帧解出 %d B / 期望 %d B)'
                         % (k, len(back), len(new_blob)))
    print('[重压] %d 个子流重压 %d 个; 帧 %d → %d B; 回环断言 ✓ (帧解出 == 新 blob, 逐字节)'
          % (len(c.subs), n_rep, c.frame_len, len(frame)))
    over = len(frame) - c.slot
    print('[槽位] 槽 %d B, 帧 %d B (%s %d B)'
          % (c.slot, len(frame), '余' if over <= 0 else '★超槽', abs(over)))
    if over > 0:
        raise SystemExit('!! 压缩后超出槽位 %d B —— 中止 (绝不截断、绝不丢字)。\n'
                         '   怎么办: 调大 --cols 减少 {br} 数量, 或缩小 --title。' % over)
    print('[摘要] 新 blob %d B sha256=%s' % (len(new_blob), hashlib.sha256(new_blob).hexdigest()))
    print('[摘要] 帧 %d B sha256=%s' % (len(frame), hashlib.sha256(frame).hexdigest()))

    if a.dry_run:
        print('[dry ] 不写盘 (--dry-run)。')
        iso.close()
        return 0

    # ---- 写盘: 只写这一个条目的槽位 (条目表 off/stored/real 不动) ----
    if src != dst:
        shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(c.entry['iso_off'])
        f.write(frame + b'\x00' * (c.slot - len(frame)))
    if os.path.getsize(src) != os.path.getsize(dst):
        raise SystemExit('!! ISO 尺寸变了')
    iso.close()

    # ═══════════════════ 回读复核 (门禁②③) ═══════════════════
    iso2 = tcslib.Iso(dst)
    e2 = iso2.img_entry(c.lba, c.idx)
    if (e2['stored'], e2['off'], e2['real']) != (c.entry['stored'], c.entry['off'],
                                                 c.entry['real']):
        raise SystemExit('!! 回读: IMG 条目表 off/stored/real 被改动了')
    subs2 = tcslib.lzo_subs(iso2.read(e2['iso_off'], e2['stored']))
    blob2 = b''.join(s[0] for s in subs2)
    if blob2 != new_blob:
        raise SystemExit('!! 回读: 盘上解出的 blob 与要写的**不是同一份**')
    print('[回读] 盘上 blob %d B == 要写的新 blob (逐字节) ✓; 子流 %d 个' % (len(blob2), len(subs2)))

    # 门禁②: 每一个码表字都要能解出来
    t2 = find_target(blob2, cs, a.item_name, '')          # 回读不再查前缀 (内容已变)
    got = cs.decode(t2['data'])[0]
    if got != text:
        k = next((i for i in range(min(len(got), len(text))) if got[i] != text[i]),
                 min(len(got), len(text)))
        raise SystemExit('!! 门禁② 不过: 回读解出的文本与预期不同 @%d (%r vs %r)'
                         % (k, got[max(0, k - 6):k + 6], text[max(0, k - 6):k + 6]))
    if len(t2['data']) != len(tgt['data']):
        raise SystemExit('!! 门禁② 不过: 回读载荷长度 %d != 原文 %d'
                         % (len(t2['data']), len(tgt['data'])))
    missing = [ch for ch in chars if ch not in got]
    if missing:
        for ch in missing[:12]:
            print('   ✗ 缺 %r (U+%04X)' % (ch, ord(ch)))
        raise SystemExit('!! 门禁② 不过: %d 个码表字在新 <text> 里解不出来' % len(missing))
    seen = {}
    for ch in got:
        seen[ch] = seen.get(ch, 0) + 1
    extra_dup = {ch: n for ch, n in seen.items() if n > 1 and ch in set(chars)}
    print('[门禁②] ✓ %d/%d 个码表字**逐个**都能在新 <text> 里解出来 '
          '(1175 对偶 + 110 单字节; 回读文本与预期逐字符相同, 载荷仍 %d B)'
          % (len(chars), len(chars), len(t2['data'])))
    if extra_dup:
        print('[门禁②]   注: 有 %d 个字出现多次 (首行统计/标题里也有码表字): %s'
              % (len(extra_dup), ', '.join('%s×%d' % (c2, n) for c2, n in
                                           sorted(extra_dup.items())[:6])))

    # 门禁③: 其它 <text> / item / studio 与 blob 其余字节不变
    e_before, e_after = parse_entries(c.blob), parse_entries(blob2)
    if len(e_before) != len(e_after):
        raise SystemExit('!! 门禁③ 不过: <text> 条数变了 (%d → %d)'
                         % (len(e_before), len(e_after)))
    changed = []
    for k, v in e_before.items():
        if e_after[k] != v:
            changed.append(k)
    tgt_k = [k for (k, _o, _l, d) in tcslib.parse_sfxml(c.blob) if d == tgt['data']]
    if len(tgt_k) != 1:
        raise SystemExit('!! 门禁③ 定位失败: 目标 <text> 在 blob 里不唯一 (%s)' % tgt_k)
    tgt_k = tgt_k[0]
    if changed != [tgt_k]:
        raise SystemExit('!! 门禁③ 不过: 变动的 <text> = %s (只允许 %s)'
                         % (changed, tgt_k))
    # 标签/属性区: 除目标区间外逐字节不变 (门禁① 的位移版, 在回读数据上再验一次)
    loc2 = locality(c.blob, blob2, tgt['a'], tgt['b'])
    if not (loc2['prefix_ok'] and loc2['suffix_ok']) or loc2['n_outside']:
        raise SystemExit('!! 门禁③ 不过: 回读 blob 在目标区间外还有改动')
    n_attr = len(ITEM_RE.findall(blob2))
    print('[门禁③] ✓ 其它 %d 个 <text> 逐字节不变 (只有 T%04d 变); %d 个 <item> / '
          '<group> / <studio> 标签区逐字节不变' % (len(e_before) - 1, tgt_k, n_attr))

    # 盘上其它 IMG 条目逐字节不变
    iso_a = tcslib.Iso(src)
    n_other = 0
    for idx in range(0, 2048):
        try:
            x1, x2 = iso_a.img_entry(c.lba, idx), iso2.img_entry(c.lba, idx)
        except Exception:                                                  # noqa: BLE001
            break
        if x1['stored'] <= 0:
            break
        if (x1['off'], x1['stored'], x1['real']) != (x2['off'], x2['stored'], x2['real']):
            raise SystemExit('!! 门禁③ 不过: 条目 #%d 的 off/stored/real 变了' % idx)
        if idx == c.idx:
            continue
        if iso_a.read(x1['iso_off'], x1['stored']) != iso2.read(x2['iso_off'], x2['stored']):
            raise SystemExit('!! 门禁③ 不过: 条目 #%d (%s) 被改动了' % (idx, x1['name']))
        n_other += 1
    iso_a.close()
    iso2.close()
    sha = tcslib.sha256_file(dst)
    print('[门禁③] ✓ %s 其余 %d 个条目逐字节不变; IMG 条目表 off/stored/real 不变'
          % (c.img, n_other))

    rep = dict(
        tool='tools/iso_build/make_font_testpage.py',
        src=rel(src), dst=rel(dst), iso_sha256_after=sha,
        charset=rel(a.charset), order=a.order,
        charset_counts=cinfo, text=tinfo, text_bytes=len(new), pad_spaces=pad,
        container=dict(tag=c.tag, img=c.img, idx=c.idx, slot=c.slot,
                       blob=len(c.blob), subs=len(c.subs),
                       frame_before=c.frame_len, frame_after=len(frame),
                       headroom=c.slot - len(frame), substreams_repacked=n_rep),
        target=dict(item_name=tgt['name'], item_off=tgt['item_off'],
                    payload_off=tgt['a'], payload_end=tgt['b'], payload_len=len(tgt['data']),
                    text_k=tgt_k, old_text_head=tgt['text'][:80],
                    old_text_chars=len(tgt['text']), tail_marker=habit),
        gates=dict(g1_local=loc, g2_missing=len(missing), g2_chars_ok=len(chars),
                   g3_changed_texts=changed, g3_other_img_entries=n_other,
                   lzo_loopback=True, size_preserved=True),
        text_head=text[:120], text_tail=text[-60:],
        blob_sha256=hashlib.sha256(new_blob).hexdigest(),
        frame_sha256=hashlib.sha256(frame).hexdigest(),
    )
    rp = a.report or os.path.join(os.path.dirname(dst), 'temp', 'font_testpage.json')
    os.makedirs(os.path.dirname(rp), exist_ok=True)
    io.open(rp, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(rep, ensure_ascii=False, indent=1) + '\n')
    print('[报告] %s' % rel(rp))
    print('[完成] %s  sha256=%s' % (rel(dst), sha))
    return 0


if __name__ == '__main__':
    sys.exit(main())
