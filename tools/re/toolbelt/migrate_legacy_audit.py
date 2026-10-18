# -*- coding: utf-8 -*-
r"""migrate_legacy_audit.py — ★ 迁移验收: 闸门感知的旧码复测 + 逐字符一致性 (独立实现)

    python tools/re/toolbelt/migrate_legacy_audit.py <iso> [--ref-iso <base.iso>]
        [--csv <all_text.csv>] [--ref-csv <base_all_text.csv>]
        [--gate 0xBA] [--base-gate 0xB1] [--charset P] [--pairs P] [--out DIR]

## 本工具**独立于** migrate_legacy.py

  · 容器/条目表: 自己 mmap 走 IMG 表 (与方法无关);
  · LANG 解析: 直接调 `tools/hanliu/tools/text_replace.parse_expanded_groups`
    —— **dump_all_text.py 用的就是它**, 所以载荷口径与官方 dump 完全一致;
  · LZO: 直接调 `tools/hanliu/tools/lz77_decode.lzo1x_decompress`;
  · SFXML: 用与 dump_all_text 完全相同的三条正则 (RE_GRP / RE_NODE) 复现它的行键。
  ⇒ 它是"另一个人用另一套代码重新验一遍", 不是自己验自己。

## 四段验收

  [A] `legacy_singles` 口径复现 + 闸门感知复测
      · `--gate 0xB1` 时**逐字节复现** tools/re/toolbelt/legacy_singles.py 的输出 (口径等价性锚点);
      · `--gate 0xBA` 时按**新闸门**解析: 报 `0xB1..0xB9` 里"不是合法对偶 lead 的裸字节" ——
        本轮核心判据, 目标 **0 处**。
        ★ 为什么必须带闸门: 迁移后文本里 `0xB1..0xB9` 是**对偶码的 lead** (例如 △=0xB1A1),
          拿旧闸门的解析去数它们必然数出一堆 —— 那是"把对偶码拆成两半"的假阳性。
          legacy_singles.py 的 usage 里本来就写了 `[gate_hex]`, 只是**没实现** (见报告)。

  [B] 逐字符一致 (ISO 级, 与 dump 无关)
      基底盘按**基底闸门语义**解出的字序列  ==  产物盘按**新闸门语义**解出的字序列
      (逐容器 · 逐条目 · 逐字符; 0 处不同才算过)

  [C] CSV ↔ ISO 对账
      每个 CSV 行 (`zh` 列) 与"该行对应的盘上载荷"用**同一闸门**解出的文本必须一致:
      · 产物 CSV: 不一致应为 **0** (证明官方 dump 在产物盘上与本工具口径一致);
      · 基底 CSV: 不一致 = **stock dump 在旧盘上解错的处数** (抬闸门后乱码的根因取证)。

  [D] 汇总 + JSON
"""
import argparse
import csv
import io
import json
import mmap
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from lz77_decode import lzo1x_decompress                               # noqa: E402
from text_replace import parse_expanded_groups                         # noqa: E402

SEC = 2048
TAB_OFF, TAB_STEP = 0x830, 48
MENU_LBA, GR_LBA = 776286, 19175
LANG_MENU_IDX, LANG_GR_IDX, XML_IDX = 25, 902, 283
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
LEAD_LO, TRAIL_LO, TRAIL_HI, STRIDE = 0xA1, 0xA1, 0xFE, 94
CONTAINERS = (('MENU:RES', MENU_LBA, LANG_MENU_IDX, 'LANG'),
              ('GR:RES', GR_LBA, LANG_GR_IDX, 'LANG'),
              ('MENU:SF', MENU_LBA, XML_IDX, 'SFXML'))
# ★ 非英文语言表 (LEAD §15.3): ES/FR = 本轮**应补但装不下** (容量硬闸); DE/IT = **明确不动**
#   (既存结构异常, LANG 解析失步)。两者都**不是** [B] 的阻断判据 —— 它们在本轮的产物上
#   一个字节都没变, 按新闸门语义解就会"吞字"。这里单列一段 [E] **如实登记** (不阻断),
#   并给出独立于迁移工具的残留计数 (账要能被别人复核)。逐表细节见
#   tools/re/toolbelt/migrate_defect_scan.py → temp/capacity/defect_report.json。
NONEN = (('ES:MENU', MENU_LBA, 27, 'ES_STRINGS.RES', '§15.3 要补 · 装不下'),
         ('ES:GR', GR_LBA, 904, 'ES_STRINGS.RES', '§15.3 要补 · 装不下'),
         ('FR:MENU', MENU_LBA, 28, 'FR_STRINGS.RES', '§15.3 要补 · 装不下'),
         ('FR:GR', GR_LBA, 907, 'FR_STRINGS.RES', '§15.3 要补 · 装不下'),
         ('DE:MENU', MENU_LBA, 26, 'DE_STRINGS.RES', '§15.3 明确不动 · 解析失步'),
         ('DE:GR', GR_LBA, 900, 'DE_STRINGS.RES', '§15.3 明确不动 · 解析失步'),
         ('IT:MENU', MENU_LBA, 29, 'IT_STRINGS.RES', '§15.3 明确不动 · 解析失步'),
         ('IT:GR', GR_LBA, 910, 'IT_STRINGS.RES', '§15.3 明确不动 · 解析失步'))
# 旧单字节码 → 字。0xB2/0xB3/0xB4 出自 r82 抬闸门**之前**的 charset
# (work/builds/GR_ZH98/temp/r82/charset_before_r82.json), 0xB6..0xB9 出自现行 charset 的 codes,
# 0xB1/0xB5 是引擎图标码 (tools/text_csv/icon_table.py; U+E0XX 是 tcslib 的 PUA 回落口径)。
#   ★ 0xB5 (✕) 的**字符名有两种口径** (2026-10-15 实测): 补丁/借条文件写 `\ue0b5` (U+E0B5,
#     tcslib 的 PUA 回落名), 而几何执行者合并后的 charset 用的是 `\u2715` (U+2715 真字形,
#     slot 2349)。这两个名字指的是**同一个字** ⇒ 必须按"对偶码表里实际用的是哪个"对齐,
#     否则 [B] 会把同一个字判成差异 (假阳性)。`align_legacy_tab()` 在 main 里做这件事。
LEGACY_TAB = {0xB1: '\u25b3', 0xB2: '\u952e', 0xB3: '\u7ec3', 0xB4: '\u7528',
              0xB5: '\ue0b5', 0xB6: '\u51fb', 0xB7: '\u5c0f', 0xB8: '\u65f6',
              0xB9: '\u6309'}
ICON_B5_ALIASES = ('\u2715', '\ue0b5', '\u00d7')


def align_legacy_tab(pair_dec):
    """把 `LEGACY_TAB[0xB5]` 对齐到**对偶码表里实际用的那个名字** (charset 优先)。"""
    vals = set(pair_dec.values())
    for cand in ICON_B5_ALIASES:
        if cand in vals:
            if LEGACY_TAB[0xB5] != cand:
                P('  [align] 0xB5 (✕) 的字符名以对偶码表为准: %r → %r'
                  % (LEGACY_TAB[0xB5], cand))
            LEGACY_TAB[0xB5] = cand
            return cand
    return LEGACY_TAB[0xB5]
RE_GRP = re.compile(rb'<(studio|group)\s+name="([^"]*)"')
RE_NODE = re.compile(rb'>([^<>]{2,400})<')

LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


# ───────────────────────── ISO / 容器 (独立实现) ─────────────────────────
class Iso:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.size = os.path.getsize(self.path)
        self.f = open(self.path, 'rb')
        self.mm = mmap.mmap(self.f.fileno(), 0, access=mmap.ACCESS_READ)

    def names(self, lba):
        base = lba * SEC
        noff = struct.unpack_from('<I', self.mm, base + 0x10)[0]
        nend = struct.unpack_from('<I', self.mm, base + 4)[0]
        return [x.decode('latin-1') for x in
                bytes(self.mm[base + noff:base + nend]).split(b'\x00') if x]

    def entry(self, lba, idx):
        base = lba * SEC
        r = struct.unpack_from('<12I', self.mm, base + TAB_OFF + TAB_STEP * idx)
        return dict(stored=r[6], real=r[7], off=r[8], iso_off=base + r[8])

    def body(self, lba, idx):
        e = self.entry(lba, idx)
        raw = bytes(self.mm[e['iso_off']:e['iso_off'] + e['stored']])
        subs, p = [], 0
        while p + 8 <= len(raw):
            L, S = struct.unpack_from('<II', raw, p)
            if L == 0 or p + 8 + L > len(raw):
                break
            try:
                dd, err, _ = lzo1x_decompress(raw[p + 8:p + 8 + L], out_size=S)
            except Exception:                                        # noqa: BLE001
                break
            if err is not None or len(dd) != S:
                break
            subs.append(bytes(dd))
            p += 8 + L
        return b''.join(subs), e

    def close(self):
        self.mm.close()
        self.f.close()


def payload_rows(iso, lba, idx, kind):
    """→ [(**稳定序键**, 载荷字节, 区域)] —— 键必须**与文本内容/偏移无关**, 否则迁移后对不上。

    LANG  : `G%02d.I%03d` (与 dump 的 extract_res 同构, 天然稳定)
    SFXML : `grp#n` / `node#n` / `attr#n` —— **按出现次序编号**。
            ★ 不可以用 `section:<名>` / `node@0x<偏移>`: 迁移后**名字本身变了、偏移也漂了**
              (官方 dump 的 SF 行键正是这两种, 所以它的 SF 行键在迁移后必然全变, 见报告)。
    """
    body, _e = iso.body(lba, idx)
    rows = []
    if kind == 'LANG':
        groups, _attrs, _used = parse_expanded_groups(body)
        for gi, st in enumerate(groups):
            for ii, s in enumerate(st):
                rows.append(('G%02d.I%03d' % (gi + 1, ii), bytes(s), 'lang'))
        return rows, body
    for n, m in enumerate(RE_GRP.finditer(body), 1):
        rows.append(('grp#%d' % n, bytes(m.group(2)), 'grp'))
    for n, m in enumerate(RE_NODE.finditer(body), 1):
        if m.group(1).strip():
            rows.append(('node#%d' % n, bytes(m.group(1)), 'node'))
    n_attr = 0
    for m in re.finditer(rb'<([A-Za-z_][\w:.-]*)\b([^>]*)>', body):
        tag = m.group(1).decode('latin-1')
        if tag.lower() not in ('item', 'group', 'studio'):
            continue
        for am in re.finditer(rb'([A-Za-z_][\w:.-]*)\s*=\s*"([^"]*)"', m.group(2)):
            if am.group(1).decode('latin-1') == 'name':
                n_attr += 1
                rows.append(('attr#%d' % n_attr, bytes(am.group(2)), 'attr'))
    return rows, body


# ───────────────────────── 解码器 (两种口径) ─────────────────────────
def decode_gate(data, gate, pair_dec, codes, legacy=None, pua=0xE000):
    """闸门语义解码: `LEAD_LO <= b < gate` ⇒ 无条件吃两字节 (引擎口径)。"""
    out, i, n = [], 0, len(data)
    while i < n:
        v = data[i]
        if v < 0x80:
            out.append(chr(v)); i += 1
        elif LEAD_LO <= v < gate:
            if i + 1 >= n:
                out.append('\uFFFD<孤lead %02X>' % v); i += 1
                continue
            pair = (v, data[i + 1])
            ch = pair_dec.get(pair)
            if ch is None and legacy and v in legacy:
                ch = None
            out.append(ch if ch is not None else '\uFFFD<pair %02X%02X>' % pair)
            i += 2
        else:
            ch = codes.get(v) or (legacy or {}).get(v)
            out.append(ch if ch is not None else chr(pua + v))
            i += 1
    return ''.join(out)


def decode_stock(data, pair_dec, codes):
    """**完全复现** tools/diag/dump_all_text.py::decode_zh 的口径 (pairs-first, 无闸门)。

    它把所有"能凑成表的对偶码"都优先吃掉 ⇒ 基底盘上的裸 0xB1..0xB9 会被它误读成对偶码,
    这就是"重配对"在 dump 层的表现; 未映射字节它写成**字面量 `\\xNN`**(不是 U+E0XX 占位)。
    """
    o, i, n = [], 0, len(data)
    while i < n:
        if data[i] < 0x80:
            o.append(chr(data[i])); i += 1
        elif i + 1 < n and (data[i], data[i + 1]) in pair_dec:
            o.append(pair_dec[(data[i], data[i + 1])]); i += 2
        elif data[i] in codes:
            o.append(codes[data[i]]); i += 1
        else:
            o.append('\\x%02X' % data[i]); i += 1
    return ''.join(o)


ESC_RE = re.compile(r'\\x([0-9A-Fa-f]{2})')


def norm_pres(t):
    """把 dump 的 `\\xNN` 字面量还原成 U+E0NN 占位, 便于与"闸门真值"逐字符比。"""
    return ESC_RE.sub(lambda m: chr(0xE000 + int(m.group(1), 16)), t)


# ───────────────────────── [A] legacy_singles 口径 ─────────────────────────
def legacy_scan(data, base_gate, gate, stat):
    """按**基底闸门**走一遍, 数出裸的 [base_gate, gate) 字节 (= legacy_singles.py 口径)。

    ★ 与 legacy_singles.py 逐行等价: `0xA1 <= c <= base_gate-1` ⇒ i += 2; `c >= base_gate` ⇒ 计数。
    """
    i, n = 0, len(data)
    while i < n:
        c = data[i]
        if LEAD_LO <= c < base_gate:
            i += 2
            continue
        if c >= base_gate:
            stat['per_code'][c] = stat['per_code'].get(c, 0) + 1
            if c < gate:
                stat['legacy_in_range'][c] = stat['legacy_in_range'].get(c, 0) + 1
        i += 1


def gate_scan(data, base_gate, gate, pair_set, stat):
    """按**新闸门**走一遍: [base_gate,gate) 里的字节必须是合法对偶 lead, 否则记一笔。"""
    i, n = 0, len(data)
    while i < n:
        c = data[i]
        if LEAD_LO <= c < gate:
            t = data[i + 1] if i + 1 < n else None
            if base_gate <= c < gate and (t is None or (c, t) not in pair_set):
                stat['unpaired'].append((c, t))
            i += 2
            continue
        if base_gate <= c < gate:                    # 到不了这里 (上面的分支吃掉), 保底
            stat['unpaired'].append((c, None))
        i += 1


def stock_misread(data, base_gate, gate, pair_set, stat):
    """基底闸门走一遍, 数出**会被 stock dump 误读成对偶码**的旧单字节码位置。

    `dump_all_text.decode_zh` 是"pairs-first": 只要 (b, 下一个字节) 凑得出表里的对偶码,
    它就把两个字节吃成一个字 —— 基底盘上这些位置**现在就是错的** (重配对)。
    """
    i, n = 0, len(data)
    while i < n:
        c = data[i]
        if LEAD_LO <= c < base_gate:
            i += 2
            continue
        if base_gate <= c < gate and i + 1 < n and (c, data[i + 1]) in pair_set:
            stat['stock_misread'] += 1
        i += 1


def audit_csv(path, base_gate, gate, pair_set, label):
    rows = list(csv.DictReader(io.open(path, encoding='utf-8-sig')))
    SK = next(k for k in rows[0].keys() if k.endswith('source'))
    st = {'lines': 0, 'per_code': {}, 'legacy_in_range': {}, 'unpaired': [],
          'by_source': {}, 'stock_misread': 0}
    for r in rows:
        h = (r.get('hex_zh') or '').strip()
        if not h:
            continue
        try:
            b = bytes.fromhex(h)
        except ValueError:
            continue
        st['lines'] += 1
        src = r.get(SK, '?')
        sub = st['by_source'].setdefault(src, {'per_code': {}, 'unpaired': 0, 'lines': 0,
                                               'stock_misread': 0})
        sub['lines'] += 1
        before = dict(st['per_code'])
        legacy_scan(b, base_gate, gate, st)
        for k, v in st['per_code'].items():
            sub['per_code'][k] = sub['per_code'].get(k, 0) + (v - before.get(k, 0))
        n0 = len(st['unpaired'])
        gate_scan(b, base_gate, gate, pair_set, st)
        sub['unpaired'] += len(st['unpaired']) - n0
        m0 = st['stock_misread']
        stock_misread(b, base_gate, gate, pair_set, st)
        sub['stock_misread'] += st['stock_misread'] - m0
    P('')
    P('=' * 84)
    P('[A] legacy-singles 复测 · %s   (%s)' % (label, os.path.basename(path)))
    P('    闸门语义 = 0x%02X (前导区间 [0x%02X,0x%02X)) · 参与统计 %d 行'
      % (gate, LEAD_LO, gate, st['lines']))
    P('=' * 84)
    P('  (A1) 基底闸门解析 (≡ legacy_singles.py 口径, 前导区间 [0xA1,0x%02X)):' % base_gate)
    for c in sorted(st['legacy_in_range']):
        P('       0x%02X : %5d 处   (%r)' % (c, st['legacy_in_range'][c],
                                              LEGACY_TAB.get(c, '?')))
    tot_in = sum(st['legacy_in_range'].values())
    P('       ---- `0xB1..0x%02X` 合计 **%d 处**' % (gate - 1, tot_in))
    P('  (A2) 新闸门解析 (前导区间 [0xA1,0x%02X)): `0xB1..0x%02X` 里**不是合法对偶 lead** 的裸字节'
      % (gate, gate - 1))
    unp = st['unpaired']
    P('       = **%d 处**%s' % (len(unp), ('   ← ★ 判据: 必须 0' if unp else '   ✓ 达标 (0 处)')))
    if unp:
        from collections import Counter
        cc = Counter(c for (c, _t) in unp)
        P('       明细: %s' % ', '.join('0x%02X:%d' % (k, v) for k, v in sorted(cc.items())))
        P('       前 5 例: %s' % ['0x%02X%s' % (c, ('%02X' % t) if t is not None else '??')
                                  for (c, t) in unp[:5]])
    P('  按来源:')
    for src in sorted(st['by_source']):
        d = st['by_source'][src]
        lr = sum(v for k, v in d['per_code'].items() if k < gate)
        P('    %-12s 行 %4d · 基底口径 `0xB1..0x%02X` = %5d 处 · 未配对裸字节 = %d · '
          'stock dump 误读成对偶码 = %d'
          % (src, d['lines'], gate - 1, lr, d['unpaired'], d['stock_misread']))
    P('  (A3) stock dump 误读处数 (pairs-first 把裸字节+后一字节吃成一个字) = **%d 处**'
      % st['stock_misread'])
    return st


# ───────────────────────── [C] CSV ↔ CSV: 逐行"真值"比对 ─────────────────────────
OFF_RE = re.compile(r'@0x([0-9A-Fa-f]+)')


def _row_order(key):
    """行排序键: 有 `@0x…` 偏移就用**数值**偏移 (两边都是 blob 序 ⇒ 可比), 否则用键本身。"""
    m = OFF_RE.search(key or '')
    return (0, int(m.group(1), 16)) if m else (1, 0)


def csv_text_rows(path):
    """→ {source: [(键, CSV 的 zh, 原始 hex)]}, 按 (偏移, 键) 排序。"""
    rows = list(csv.DictReader(io.open(path, encoding='utf-8-sig')))
    SK = next(k for k in rows[0].keys() if k.endswith('source'))
    out = {}
    for r in rows:
        h = (r.get('hex_zh') or '').strip()
        if not h:
            continue
        out.setdefault(r.get(SK, '?'), []).append((r.get('key', ''), r.get('zh', ''), h))
    for k in out:
        out[k].sort(key=lambda x: (_row_order(x[0]), x[0]))
    return out


def compare_csv_text(before, after, base_gate, gate, pair_dec, codes, pair_charset):
    """[C] 逐行比对 —— 三方口径, 每个差异都能归因:

      truth   = 用**闸门语义 + 完整字表**解这份字节 (引擎真值)
      stock   = dump_all_text.decode_zh 的 pairs-first 口径 (官方 CSV 的 zh 列)

      [C0] stock(hex) == CSV 的 zh 列            → 证明我对官方口径的复现是对的
      [C1] 基底 CSV 的 zh ≠ 基底真值             → **官方 dump 在基底盘上就解错的行数**
      [C2] 产物 CSV 的 zh ≠ 产物真值             → charset 还没登记借槽对偶码的行数 (工具链依赖)
      [C3] 基底真值 vs 产物真值 (逐行)           → ★ 判据 (a) 的行级形式, 必须 0
    """
    A, B = csv_text_rows(before), csv_text_rows(after)
    P('')
    P('=' * 84)
    P('[C] 逐行比对 (CSV 的 zh 列 / 闸门真值 / stock dump 口径 三方对账)')
    P('=' * 84)
    out = {}
    for src in sorted(set(A) | set(B)):
        ra, rb = A.get(src, []), B.get(src, [])
        n = min(len(ra), len(rb))
        diff_pair, c0, c1, c2, ex = 0, 0, 0, 0, []
        skipped = 0
        for i in range(n):
            (k1, z1, h1), (k2, z2, h2) = ra[i], rb[i]
            if not (k1.startswith('node@') and k2.startswith('node@')) and \
                    k1.split('@')[0] != k2.split('@')[0]:
                skipped += 1                        # 两侧行类型不同 ⇒ 无法按序配对
                continue
            b1, b2 = bytes.fromhex(h1), bytes.fromhex(h2)
            # [C0] 复现官方 dump 口径
            if decode_stock(b1, pair_charset, codes) != z1 or \
                    decode_stock(b2, pair_charset, codes) != z2:
                c0 += 1
            t1 = decode_gate(b1, base_gate, pair_dec, codes, LEGACY_TAB)
            t2 = decode_gate(b2, gate, pair_dec, codes, LEGACY_TAB)
            if norm_pres(z1) != t1:
                c1 += 1
            if norm_pres(z2) != t2:
                c2 += 1
            if t1 != t2:
                diff_pair += 1
                if len(ex) < 3:
                    ex.append('%s: 基底真值 %r ≠ 产物真值 %r' % (k1, t1[:44], t2[:44]))
        out[src] = dict(rows_before=len(ra), rows_after=len(rb), compared=n - skipped,
                        skipped=skipped, c0_stock_repro_mismatch=c0,
                        c1_base_csv_vs_truth=c1, c2_after_csv_vs_truth=c2,
                        c3_truth_diff=diff_pair, examples=ex)
        P('  %-12s 行 %4d → %4d · 可配对 %4d (跳过 %d)'
          % (src, len(ra), len(rb), n - skipped, skipped))
        P('      [C0] 我复现的 stock 口径 ≠ CSV 的 zh 列 : %d  %s'
          % (c0, '✓' if not c0 else '✗ (复现失败, 下面的数不可信)'))
        P('      [C1] 基底 CSV 的 zh ≠ 基底真值 (官方 dump 在旧盘上就解错) : %d 行' % c1)
        P('      [C2] 产物 CSV 的 zh ≠ 产物真值 (charset 未登记借槽对偶码所致) : %d 行' % c2)
        P('      [C3] ★ 基底真值 vs 产物真值 逐行不同 : **%d**  %s'
          % (diff_pair, '✓ 达标' if not diff_pair else '✗'))
        for e in ex:
            P('          %s' % e)
    return out


def _count_legacy(data, base_gate, gate):
    """基底闸门语义下的裸 `[base_gate,gate)` 计数 + 逐码 (与 legacy_scan 同口径, 只回计数)。"""
    n, per, i, m = 0, {}, 0, len(data)
    while i < m:
        c = data[i]
        if LEAD_LO <= c < base_gate:
            i += 2
            continue
        if base_gate <= c < gate:
            n += 1
            per[c] = per.get(c, 0) + 1
        i += 1
    return n, per


def _unpaired_count(data, base_gate, gate, pair_set):
    """★ 主判据 (LEAD §14.1) 的**实现口径** —— 产物载荷里 `0xB1..0xB9` "出现在单字节位"的处数。

    怎么算"单字节位": 按**新闸门**走 (`[0xA1,gate)` 一律吃两字节 = 引擎口径), 落在
    `[base_gate,gate)` 的那个字节**只有在它凑不出合法对偶码**时才算"裸字节/单字节位"。
    ⇒ 数字必须 **0**: 每个 `0xB1..0xB9` 都必须是本次插入的对偶 lead。

    ★ 为什么不按"基底语义"数: 迁移后 `0xB1..0xB9` 本来就是**对偶 lead** (△=0xB1A1),
      拿基底语义 (只认 `0xA1..0xB0` 是前导) 去数产物盘, 必然把每个对偶码拆成两半 ——
      实测产物载荷上数出 1,660 / 1,660 / 81 处, **全是假阳性** (与 CSV 层的 3,386 /
      3,604 是同一个现象)。判据要的是"没有**裸**字节", 不是"没有这些字节"。
    """
    n, per, i, m = 0, {}, 0, len(data)
    while i < m:
        c = data[i]
        if LEAD_LO <= c < gate:
            t = data[i + 1] if i + 1 < m else None
            if c >= base_gate and (t is None or (c, t) not in pair_set):
                n += 1
                per[c] = per.get(c, 0) + 1
            i += 2
            continue
        i += 1
    return n, per


def defect_section(iso, base_gate, gate):
    """[E] 非英文语言表残留登记 —— **非阻断**, 只如实记账 (LEAD §15.3)。

    这些表在产物盘上**一个字节都没变**: ES/FR 是"应补但装不下", DE/IT 是"明确不动"。
    按新闸门 0x%02X 解, 表内每个裸 `0xB1..0xB9` 都会吃掉后一字节 ⇒ 记的就是"待 LEAD 决策的
    未达成量", 不是迁移缺陷。
    """
    P('')
    P('=' * 84)
    P('[E] 非英文语言表: 已知缺陷登记 (**非阻断** — 本轮产物里这些表一个字节都没动)')
    P('=' * 84)
    P('  %-9s %-16s %8s %8s %8s %-6s %s'
      % ('入口', 'name', '解压B', '全blob', '载荷', 'LANG', '处置'))
    out = {}
    for (tag, lba, idx, nm, why) in NONEN:
        body, _e = iso.body(lba, idx)
        n_all, per_all = _count_legacy(body, base_gate, gate)
        pay, why2 = None, ''
        try:
            groups, _attrs, _used = parse_expanded_groups(body)
            pay = 0
            for st in groups:
                for s in st:
                    pay += _count_legacy(bytes(s), base_gate, gate)[0]
        except Exception as ex:                                          # noqa: BLE001
            why2 = str(ex)[:44]
        out[tag] = dict(name=nm, lba=lba, idx=idx, decomp=len(body), raw_n=n_all,
                        raw_per={('0x%02X' % k): v for k, v in sorted(per_all.items())},
                        payload_n=pay, why=why, parse_err=why2)
        P('  %-9s %-16s %8d %8d %8s %-6s %s'
          % (tag, nm, len(body), n_all, (pay if pay is not None else '-'),
             ('OK' if pay is not None else '失败'), why))
        P('       逐码 (全 blob): %s%s'
          % (out[tag]['raw_per'], ('  载荷 = %d 处' % pay) if pay is not None
             else ('  解析失败: %s' % why2)))
    tot = sum(v['raw_n'] for v in out.values())
    P('  ---- 8 份拷件合计残留 (全 blob 口径) = **%d 处** —— ES/FR 56+58 = 114 (装不下), '
      'DE/IT 74+76 = 150 (解析失步, 明确不动)' % tot)
    P('  ⚠ 风险: 若主机语言 = ES/FR/DE/IT, 引擎会渲染这些表 ⇒ 抬闸门后上述字节会**吞后一字节**')
    P('     (整串重配对, 界面出 ASCII 乱码)。ES/FR 的处置是"等 LEAD 批容量方案";')
    P('     DE/IT 的处置是"先修解析再谈迁移"。逐表证据: migrate_defect_scan.py 的 defect_report.json')
    return out


# ───────────────────────── 主流程 ─────────────────────────
def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('--ref-iso', default=None)
    ap.add_argument('--csv', default=None)
    ap.add_argument('--ref-csv', default=None)
    ap.add_argument('--gate', default='0xBA')
    ap.add_argument('--base-gate', default='0xB1')
    ap.add_argument('--charset', default=CHARSET)
    ap.add_argument('--pairs', default=None, help='migrate_legacy.py 的借条 JSON (产物盘用)')
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)
    gate, base_gate = int(a.gate, 16), int(a.base_gate, 16)
    out = os.path.abspath(a.out or os.path.join(os.path.dirname(os.path.abspath(a.iso)),
                                                'temp'))
    os.makedirs(out, exist_ok=True)

    cs = json.load(io.open(a.charset, encoding='utf-8'))
    codes = {int(v): k for k, v in cs['codes'].items()}            # byte → 字
    pair_dec = {tuple(v): k for k, v in cs['pair_of'].items()}     # (b1,b2) → 字
    if a.pairs and os.path.isfile(a.pairs):
        j = json.load(io.open(a.pairs, encoding='utf-8'))
        for ch, p in (j.get('pairs', j) or {}).items():
            pair_dec[tuple(p)] = ch
    pair_set = set(pair_dec)
    pair_charset = {tuple(v): k for k, v in cs['pair_of'].items()}   # 只含 charset 本身 → 复现 dump
    align_legacy_tab(pair_dec)

    P('=' * 84)
    P('migrate_legacy_audit.py — 独立验收 (闸门感知)')
    P('  产物盘 = %s' % a.iso)
    P('  基底盘 = %s' % (a.ref_iso or '(未给, 跳过 [B])'))
    P('  闸门   = 0x%02X (基底 0x%02X) ; 对偶码表 %d 条 (含借条 %s)'
      % (gate, base_gate, len(pair_dec), a.pairs or '无'))
    P('=' * 84)

    res = {}
    if a.csv:
        res['A_after'] = audit_csv(a.csv, base_gate, gate, pair_set, '产物 CSV')
        # 口径等价性锚点: 拿**同一份** CSV 用基底闸门再跑一遍 ⇒ 应与 legacy_singles.py 逐字一致
        res['A_same_csv_base_gate'] = audit_csv(a.csv, base_gate, base_gate, pair_set,
                                                '同一 CSV · 基底闸门口径 (等价性锚点)')
    if a.ref_csv:
        res['A_before'] = audit_csv(a.ref_csv, base_gate, gate, pair_set, '基底 CSV')
    if a.ref_csv and a.csv:
        res['C'] = compare_csv_text(a.ref_csv, a.csv, base_gate, gate, pair_dec, codes,
                                    pair_charset)

    if a.ref_iso:
        iso_a, iso_b = Iso(a.iso), Iso(a.ref_iso)
        P('')
        P('=' * 84)
        P('[B] ISO 级逐字符一致 (基底闸门语义 vs 新闸门语义)')
        P('=' * 84)
        res['B'] = {}
        for (src, lba, idx, kind) in CONTAINERS:
            rows_a, body_a = payload_rows(iso_a, lba, idx, kind)
            rows_b, body_b = payload_rows(iso_b, lba, idx, kind)
            assert len(rows_a) == len(rows_b), (src, len(rows_a), len(rows_b))
            n_diff, first = 0, None
            # ★ 主判据 (LEAD §14.1): 对**产物盘的载荷字节流**直接按基底闸门语义扫描 ⇒
            #   `0xB1..0xB9` 出现在**单字节位**的数量必须为 **0**。这是独立于构建器 [S3] 的
            #   第二套实现 (本工具自己的 IMG/LZO 读取 + 自己的扫描), 也是本轮唯一的硬主判据。
            n_bare, per_bare = 0, {}
            n_fp, _fp = 0, {}
            for (_kb, ba, _ra) in rows_a:
                k, p = _unpaired_count(ba, base_gate, gate, pair_set)
                n_bare += k
                for kk, vv in p.items():
                    per_bare[kk] = per_bare.get(kk, 0) + vv
                n_fp += _count_legacy(ba, base_gate, gate)[0]      # 旧口径的假阳性 (登记用)
            for (kb, _bb, _r), (ka, ba, _ra) in zip(rows_b, rows_a):
                if kb != ka:
                    n_diff += 1
                    if first is None:
                        first = ('键序不一致 %s ≠ %s' % (kb, ka))
                    continue
                t_b = decode_gate(_bb, base_gate, pair_dec, codes, LEGACY_TAB)
                t_a = decode_gate(ba, gate, pair_dec, codes, LEGACY_TAB)
                if t_b != t_a:
                    n_diff += 1
                    if first is None:
                        k = next((j for j in range(min(len(t_b), len(t_a)))
                                  if t_b[j] != t_a[j]), 0)
                        first = ('%s: 基底 %r ≠ 产物 %r' % (kb, t_b[max(0, k - 10):k + 10],
                                                          t_a[max(0, k - 10):k + 10]))
            st = dict(rows=len(rows_a), diff=n_diff, blob_a=len(body_a), blob_b=len(body_b),
                      first=first, bare_after=n_bare, bare_falsepos_base_semantics=n_fp,
                      bare_per={('0x%02X' % k): v for k, v in sorted(per_bare.items())})
            res['B'][src] = st
            P('  %-9s 条目 %5d · 解压长 %d/%d %s · 逐字符不同 = **%d** %s'
              % (src, st['rows'], st['blob_b'], st['blob_a'],
                 '✓' if st['blob_b'] == st['blob_a'] else '✗', n_diff,
                 ('' if not n_diff else ('← ' + str(first)))))
            P('  %-9s ★ 主判据 (§14.1 载荷级) `0xB1..0x%02X` "出现在单字节位" = **%d 处** %s%s'
              % ('', gate - 1, n_bare, '✓ 达标' if not n_bare else '✗ 未达标',
                 ('' if not n_bare else ' 明细 %s' % st['bare_per'])))
            P('  %-9s   (同口径若误用**基底语义**去数产物盘 ⇒ %d 处, 全是对偶码被拆开的假阳性;'
              % ('', n_fp))
            P('  %-9s    正确判据是"没有**裸**字节", 不是"没有这些字节" —— 见 _unpaired_count 注释)'
              % '')
        res['E'] = defect_section(iso_a, base_gate, gate)
        iso_a.close(); iso_b.close()

    # ── 汇总 + JSON ──
    P('')
    P('=' * 84)
    ok = True
    if 'A_after' in res:
        n = len(res['A_after']['unpaired'])
        P('  [结论] 产物盘 `0xB1..0x%02X` 未配对裸字节 = %d %s' % (gate - 1, n, '✓' if not n else '✗'))
        ok &= (n == 0)
    if 'A_before' in res:
        P('  [结论] 基底盘 legacy_singles 口径 = %d 处 (与 LEAD 表的 3073 对账见报告)'
          % sum(res['A_before']['legacy_in_range'].values()))
    if 'B' in res:
        for src, st in res['B'].items():
            P('  [结论] %-9s 逐字符不同 = %d %s ; ★载荷级裸旧码 = %d %s'
              % (src, st['diff'], '✓' if not st['diff'] else '✗', st['bare_after'],
                 '✓' if not st['bare_after'] else '✗'))
            ok &= (st['diff'] == 0 and st['bare_after'] == 0)
    if 'C' in res:
        for src, st in res['C'].items():
            P('  [结论] %-9s [C0] 口径复现失败 %d · [C1] 基底 CSV 解错 %d 行 · '
              '[C2] charset 未登记借槽所致 %d 行 · [C3] ★真值逐行不同 = %d %s'
              % (src, st['c0_stock_repro_mismatch'], st['c1_base_csv_vs_truth'],
                 st['c2_after_csv_vs_truth'], st['c3_truth_diff'],
                 '✓' if not st['c3_truth_diff'] else '✗'))
            ok &= (st['c3_truth_diff'] == 0 and st['c0_stock_repro_mismatch'] == 0)
    P('  ⇒ 总判据 (C0 复现 + A2 未配对 + B 逐字符 + C3 真值逐行): %s'
      % ('**全部通过**' if ok else '**有未通过项, 见上**'))
    with io.open(os.path.join(out, 'audit_report.json'), 'w', encoding='utf-8',
                 newline='\n') as f:
        json.dump(dict(iso=a.iso, ref_iso=a.ref_iso, gate=gate, base_gate=base_gate,
                       csv=a.csv, ref_csv=a.ref_csv, pass_=bool(ok), result=res, log=LOG),
                  f, ensure_ascii=False, indent=1)
    with io.open(os.path.join(out, 'audit.log'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    P('  [out] %s' % os.path.join(out, 'audit_report.json'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
