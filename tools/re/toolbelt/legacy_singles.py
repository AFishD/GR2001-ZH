# -*- coding: utf-8 -*-
r"""legacy_singles.py — 精确统计"旧单字节码"的落点 (**闸门口径**)

用法:
    python tools/re/toolbelt/legacy_singles.py <all_text.csv> [gate_hex] [--used N]

语义 (★ 2026-10-15 补齐 `[gate_hex]`, 之前 usage 写了但代码从不读第二个参数):

    引擎的 DBCS 判据是一条**无符号区间比较** `0xA1 <= byte < GATE` ⇒ `0xA1..GATE-1` 是
    **对偶前导** (无条件吃两字节, trail 值不检查), 其余才是单字节码。所以
    `gate_hex` = **前导上界**, 默认 `0xB1` (基底盘 = GR_ZH113b 的 4 处 sltiu 立即数实测值)。

        c ∈ [0xA1, gate)  ⇒ 对偶前导, i += 2   (原代码写死 0xA1..0xB0)
        c >= gate         ⇒ 以**单字节形式**出现 ⇒ 按闸门阶梯统计

    ⇒ 阶梯表回答的问题: "闸门抬到 0xG 时, `0xB1..0xG-1` 里有多少个字节需要迁移"。
      `0xB1..0xB9` 的合计就是 LEAD 表 §1.4 的"迁移量"。

## ★ 两个必须知道的口径陷阱 (本工具是**辅助**判据, 不是主判据)

### ① SF 盲点: 本工具读的是 `dump_all_text.py` 的 CSV, 而旧 dump 口径看不见两类 SF 正文

    `dump_all_text.extract_xml` 老口径的 `RE_NODE = >([^<>]{2,400})<` **上限 400 字节**,
    且只抓 `<(studio|group) name="…">` ⇒ **>400B 的 `<text>` 正文** 与 **`item` 的
    `name=` 属性** 全都看不见。实测 `EN_SPECIAL_FEATURE.XML`:

        真值 265 处 (<text> 正文 250 + name= 15) ; 旧 dump 口径只有 **59** ⇒ **少算 206**
        而这 206 正好是"迁移真值 **3,279** − 本工具旧口径 **3,073**"的差额 (LEAD §1.4 的
        3,073 因此是**下界**, 见 LEAD_CAPACITY_2400.md §14.1/§15.4)

    该盲点已在 `tools/diag/dump_all_text.py::extract_xml` 修好 (改用
    `tcslib.parse_sfxml + inject_text_csv.parse_xml_attrs`, 59 → 265)。**本工具本身没变** ——
    它只是如实反映喂给它的 CSV。若拿到旧 CSV, 报出来的就是 **3,073**; 拿到新 CSV 就是 **3,279**。
    ⇒ 结论里必须写明用的是哪一份 CSV。

### ② ★ 读**产物盘**的 CSV 必须用**闸门口径** (传 gate_hex), 否则必出假阳性

    产物盘上 `0xB1..0xB9` 已经是**对偶码的 lead** (△=`0xB1A1`、按=`0xB9FA` …)。若沿用
    基底口径 (`0xA1..0xB0` 才是前导) 去读产物 CSV, 每个对偶码都会被拆成
    "一个裸首字节 + 一个裸尾字节", 整条 payload 随之**错位**, 实测数出大量假阳性
    (真实残留 = **0** 处):
        · 旧 dump 口径的产物 CSV (`temp/after/all_text.csv`, LEAD §15.4 的口径) ⇒ **3,386 处**
        · 修好 SF 口径后的产物 CSV (`temp/r2/dump_after/all_text.csv`)      ⇒ **3,604 处**
      两个数都对, 差别只是后者多看见了 192 处长正文 + 14 处 `name=` 属性。
    正确用法: `python tools/re/toolbelt/legacy_singles.py <产物CSV> 0xBA`。

    ★ 但**即便传对闸门, 本工具也不是产物盘的主判据**: 它只有"闸门"没有"对偶码表",
    数不出"`0xB1..0xB9` 里哪些字节**不是合法对偶 lead**"。主判据是**载荷字节流**级的
    `tools/re/toolbelt/migrate_legacy_audit.py` `[A2]` (闸门口径裸字节 = 0) —— 它带完整对偶码表
    (charset ∪ 借条), 见 LEAD_CAPACITY_2400.md §14.1。
"""
import collections
import csv
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')


def _charset_used(default=1504):
    """charset 里 `pair_of` 已占的槽数 (阶梯表的"已用"基数)。读不到就退回默认值。"""
    try:
        with open(CHARSET, encoding='utf-8') as f:
            return len(json.load(f).get('pair_of') or {})
    except Exception:                                                    # noqa: BLE001
        return default


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    path = argv[0]
    gate, used = 0xB1, None
    rest = list(argv[1:])
    while rest:
        a = rest.pop(0)
        if a == '--used':
            used = int(rest.pop(0))
        elif a in ('-h', '--help'):
            print(__doc__)
            return 0
        else:
            gate = int(a, 16)
    if used is None:
        used = _charset_used()

    rows = list(csv.DictReader(open(path, encoding='utf-8-sig')))
    SK = next(k for k in rows[0].keys() if k.endswith('source'))

    per = collections.defaultdict(collections.Counter)   # source -> {code: count}
    tot = collections.Counter()
    strings_with = collections.defaultdict(set)
    nlines = 0
    for r in rows:
        h = (r.get('hex_zh') or '').strip()
        if not h:
            continue
        try:
            b = bytes.fromhex(h)
        except ValueError:
            continue
        nlines += 1
        i = 0
        while i < len(b):
            c = b[i]
            if 0xA1 <= c < gate:            # ★ 闸门口径: [0xA1, gate) = 对偶前导 (吃 2 字节)
                i += 2
                continue
            if c >= gate:                   # 以单字节形式出现 ⇒ 抬闸门后会被误判为 lead
                per[r.get(SK, '?')][c] += 1
                tot[c] += 1
                strings_with[c].add(r.get('key', '?'))
            i += 1

    print('  CSV = %s' % os.path.abspath(path))
    print('  口径: 对偶前导区间 = [0xA1, 0x%02X) ; "单字节码" = c >= 0x%02X' % (gate, gate))
    print('  参与统计的文本行 = %d' % nlines)
    print()
    print('  【以单字节形式出现的 >=0x%02X 码位】(= 闸门抬到该值后必须迁移的落点)' % gate)
    for c in sorted(tot):
        print('    0x%02X : %5d 处 · 涉及 %4d 条字符串' % (c, tot[c], len(strings_with[c])))
    s = sum(tot.values())
    print('    ---- 合计 %d 处' % s)
    new_codes = sum(v for k, v in tot.items() if gate <= k < 0xBA)
    print('    ---- 其中 `0xB1..0xB9` = %d 处 (这是抬闸门到 0xBA 真正要迁移的量;'
          ' 与迁移账目 3,279 对账时要看用的是哪份 CSV, 见文件头 ①)' % new_codes)
    print()
    print('  按来源:')
    for src in sorted(per):
        print('    %-12s %s' % (src, {('0x%02X' % k): v for k, v in sorted(per[src].items())}))
    if gate != 0xB1:
        print()
        print('  ★ 提醒: 你用了非默认闸门 0x%02X。读**产物盘**的 CSV 时必须这样传 (否则对偶' % gate)
        print('     lead 会被拆开, 实测产生 3,386 处假阳性); 但本工具没有对偶码表,')
        print('     产物盘的主判据请用 tools/re/toolbelt/migrate_legacy_audit.py 的 [A2] 段。')
    print()
    print('  闸门阶梯 ("已用" = charset.pair_of 现状; **高于该闸门容量时该闸门已不可用**):')
    for g in range(max(gate, 0xB1), 0xC1):
        slots = (g - 0xA1) * 94
        need_mig = sum(v for k, v in tot.items() if 0xB1 <= k < g)
        rest = slots - used
        print('  闸门 0x%02X ⇒ 对偶槽 %5d (已用 %d ⇒ %s) · 需迁移 %5d 处'
              % (g, slots, used, ('余 %5d' % rest) if rest >= 0
                 else '★ 超容 %d, 不可用' % (-rest), need_mig))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
