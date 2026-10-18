# -*- coding: utf-8 -*-
r"""migrate_legacy.py — ★ 旧单字节码**全量迁移** + ELF decode gate 抬升 (可复用工具)

    python tools/re/toolbelt/migrate_legacy.py <src.iso> <dst.iso> [options]

## 为什么需要它 (已确诊的 bug: docs/PROGRESS.md + LEAD_CAPACITY_2400.md §1.4)

引擎的 DBCS 判据是一条**无符号区间比较** `0xA1 <= byte < GATE` (ELF 4 处 `sltiu`):

    0x416EE8  sltiu t1,a1,GATE    ds16 cave: 字节 → 对偶码判定
    0x417160  sltiu t1,t0,GATE    StringWidth: lead 判定
    0x41751C  sltiu t3,t2,GATE    DrawString 主循环
    0x5656A4  sltiu t4,t3,GATE    SWKERN cave
    反汇编出处: docs/REPORT_cave_count_vs_bytes.md:183-198 / docs/REPORT_probe_lead_limit.md:36-48

GATE 从 0xB1 抬到 0xBA 之后, `0xB1..0xB9` 这些**原本是单字节字**的字节会变成对偶前导:
文本里每个遗留的裸字节都"吃掉"后一个字节 (trail ∈ [0xA1,0xFE] 时整串重配对) ⇒
界面出 `4 / 0 / ( / P / H` 之类 ASCII 乱码, 并可能引发内存损坏 (用户实机崩溃)。

所以抬闸门**必须**配套文本迁移: 把文本里"以单字节形式出现"的 `0xB1..GATE-1` 改写成
对应字的**新对偶码**。本工具就是这一步, 且**只做这一步**。

## 本工具做的事 (逐条列出, 其它一个字节都不动)

  ① **7 个容器**的**文本载荷区间**里, 把裸 `0xB1..GATE-1` 改写成该字在 charset 里的对偶码
     (2 字节); 容器清单见 `CONTAINER_SPECS` (3 个中文容器 + §15.3 补的 ES/FR 各 2 份);
     其余容器逐一 `--skip`, DE/IT 见 `EXCLUDED_SPECS` (**明确不动**, 原因见文件内注释);
  ② 维护长度前缀 / 偏移 / 结构 —— 用"反向重建"硬门禁证明"除载荷区间外一个字节都没变";
     增长吃容器 `used_end` 之后的**陈旧尾巴** ⇒ 解压总长严格不变 ⇒
     IMG 条目表 (off/stored/real) **一个字节都不用改**;
     ★ **装不下就中止** (不截断、不丢字、不改条目表): ES/FR 实测**装不下**, 见 §"容量"注释;
  ③ ELF 4 处 gate 立即数 `0xB1` → `0xBA` (`--no-elf` 可关; 见下);
  ④ 全盘逐字节 diff: 差异 100% 落在「容器区域 + 4 个 ELF 站点」窗口内。

## 容器选择

    --containers all|core|esfr|<tag,tag,…>     (默认 all = 7 个)
    --skip <tag>                               (可重复; 显式不动某个容器)

  `core` = 3 个中文容器 (§1.4 / §13) ; `esfr` = ES/FR 各 2 份 (§15.3)。

## 容量 (★ 2026-10-15 实测: ES/FR **装不下**, 不是 bug 而是盘上没有空间)

  迁移每处 +1 B, 只能吃 `used_end` 之后的陈旧尾巴:

    | 容器 | 解压长 | 陈旧尾巴 | 增长 | 结论 |
    |---|---|---|---|---|
    | EN_STRINGS.RES@MENU/GR | 128,545 / 128,668 | 58,874 / 58,997 | 1,507 | ✓ 槽内吸收 |
    | EN_SPECIAL_FEATURE.XML | 116,486 | 36,385 (CRLF 填充) | 265 | ✓ 槽内吸收 |
    | **ES_STRINGS.RES ×2** | 142,148 | **8** | **28** | ✗ 差 20 B |
    | **FR_STRINGS.RES ×2** | 149,664 | **8** | **29** | ✗ 差 21 B |

  ES/FR 表是**未汉化的原文**, 从来没有被编辑过 ⇒ 条目数据正好铺满整个 blob, 没有陈旧尾巴;
  IMG 里相邻条目的间距只有 10~13 B (扇区对齐余量) ⇒ **扩容必须改 IMG 条目表 (stored/real)
  并搬移后续数据**, 与"最小差异 / 条目表未动"直接冲突 ⇒ 本工具**拒绝写盘**并报容量账,
  由 LEAD 重排 (见 `work/builds/GR_TXMIG/temp/capacity/capacity_report.json`)。

## `--no-elf` 的语义 (几何先行的合并流程要用)

  LEAD §13 的合并顺序是「几何盘(闸门已设 0xBA) → 文本迁移」⇒ 迁移时**不能再打 ELF**。
  此时源盘的闸门立即数**已经等于** `--gate`: `--no-elf` 就要求 `imm == gate`, 并且
  `[S7]` 回读也按 `gate` 校验。若源盘 `imm == --base-gate` (还没抬闸门) 却传了 `--no-elf`,
  报错中止 —— 免得把"没抬闸门"的盘当成"抬好了"。

## 内置自检 (任一条失败 ⇒ 打 `[!!]` 并**中止, 不写盘**)

  [S1] 每个待迁移字节都能查到字, 每个字都能查到合法对偶码 (lead < GATE, trail ∈ [A1,FE])
  [S2] 反向重建: 新载荷换回盘上原字节 ⇒ 逐字节 == 源 blob (证明结构 0 改动)
  [S3] 迁移后按**基底闸门语义**重扫 ⇒ `0xB1..GATE-1` 的裸字节 = 0 处
  [S4] 新 blob 里每个 `0xB1..GATE-1` 字节**必须**是本次插入的对偶 lead (自洽计数)
  [S5] 逐载荷: 基底语义解出的字序列 == 新闸门语义解出的字序列 (逐字符一致)
  [S6] 新载荷 == 解码文本的**规范编码** (排除非规范写法)
  [S7] 回读产物盘: 3 容器 blob 逐字节 == 目标; 条目表字段不变; ELF 4/4 == GATE
  [S8] ISO 尺寸不变; 窗口外差异 0 字节

## 与 charset 的关系 (关键, 别踩)

  · 本工具**不改** `tools/font_pipeline/data/charset_compiled_zh16.json` (几何路 geom2400 的
    受保护路径)。缺对偶码的字 ⇒ 默认 `[!!] 中止`; 显式 `--reserve-slots` 才从闸门容量
    **顶部**往下借空槽, 并把借条写成 sidecar JSON (`--pairs-out`)。
  · 几何路把新字落进 charset 之后**重跑本工具**即可: 它优先用 charset 里的对偶码,
    sidecar 只是"charset 还没写到时的过渡借条"。
"""
import argparse
import importlib.util
import io
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                      # noqa: E402

# ─────────────────────────────── 常量 (全部有出处) ───────────────────────────────
BASE_GATE_DEFAULT = 0xB1        # 基底盘闸门 (GR_ZH113b: 4 处 sltiu 立即数实测 0xB1)
GATE_DEFAULT = 0xBA             # 本轮目标闸门 (LEAD_CAPACITY_2400 §2)
ELF_SITES = (0x416EE8, 0x417160, 0x41751C, 0x5656A4)   # VA; docs/REPORT_probe_lead_limit.md:36-39
ELF_ISO_BASE, ELF_VA_BASE = 0x93880, 0x100000          # VA → ISO 偏移 = VA − 0x6C780
CHARSET = T.CHARSET
OUT_DEFAULT = os.path.join(REPO, 'work', 'builds', 'GR_TXMIG')

# ─────────────────── 容器清单 (kind, img, lba, idx, tag, 出处) ───────────────────
# 前 3 条 = LEAD §1.4/§13 的中文容器; 后 4 条 = LEAD §15.3 裁决「只补 ES + FR」。
# idx 出处: tools/re/toolbelt/migrate_scan_lang_tables.py 的实测输出
#           (work/builds/GR_TXMIG/temp/scan_lang_tables.json)。
CONTAINER_SPECS = (
    ('LANG',  'MENU.IMG', T.MENU_LBA, 25,  'EN_STRINGS.RES@MENU',    '§1.4 中文主表'),
    ('LANG',  'GR.IMG',   T.GR_LBA,   902, 'EN_STRINGS.RES@GR',      '§1.4 中文主表'),
    ('SFXML', 'MENU.IMG', T.MENU_LBA, 283, 'EN_SPECIAL_FEATURE.XML', '§1.4 中文特别收录'),
    ('LANG',  'MENU.IMG', T.MENU_LBA, 27,  'ES_STRINGS.RES@MENU',    '§15.3 西语原文'),
    ('LANG',  'GR.IMG',   T.GR_LBA,   904, 'ES_STRINGS.RES@GR',      '§15.3 西语原文'),
    ('LANG',  'MENU.IMG', T.MENU_LBA, 28,  'FR_STRINGS.RES@MENU',    '§15.3 法语原文'),
    ('LANG',  'GR.IMG',   T.GR_LBA,   907, 'FR_STRINGS.RES@GR',      '§15.3 法语原文'),
)
CORE_TAGS = ('EN_STRINGS.RES@MENU', 'EN_STRINGS.RES@GR', 'EN_SPECIAL_FEATURE.XML')
ESFR_TAGS = ('ES_STRINGS.RES@MENU', 'ES_STRINGS.RES@GR',
             'FR_STRINGS.RES@MENU', 'FR_STRINGS.RES@GR')

# ★ **明确不动**的 4 份非英文语言表 (LEAD §15.3 裁决):
#   `T.parse_lang` / `parse_expanded_groups` 都解不动它们 (既存结构异常) ⇒ 盲改有破坏风险。
#   实测证据 (scan_lang_tables.json): DE 全 blob 裸 `0xB1..0xB9` 37 处/份、IT 38 处/份,
#   LANG 解析在第 60 组 / 第 ~369 条处失步 ⇒ 载荷边界不可信 ⇒ 不能安全改写。
#   登记为**已知缺陷**, 由报告交付 (tools/re/toolbelt/migrate_defect_scan.py 出逐表证据)。
EXCLUDED_SPECS = (
    ('LANG', 'MENU.IMG', T.MENU_LBA, 26,  'DE_STRINGS.RES@MENU', '结构异常: LANG 解析失步'),
    ('LANG', 'GR.IMG',   T.GR_LBA,   900, 'DE_STRINGS.RES@GR',   '结构异常: LANG 解析失步'),
    ('LANG', 'MENU.IMG', T.MENU_LBA, 29,  'IT_STRINGS.RES@MENU', '结构异常: LANG 解析失步'),
    ('LANG', 'GR.IMG',   T.GR_LBA,   910, 'IT_STRINGS.RES@GR',   '结构异常: LANG 解析失步'),
)

# 引擎**图标码** → 字。这两个字节不在 charset 的 `codes` 里 (引擎直接画图标, 不吃字库),
# 但抬闸门后同样会被当 lead 吃掉 ⇒ 必须一起迁 (LEAD_CAPACITY_2400 §1.4: 0xB1=△ 14 处,
# 0xB5=图标 42 处)。△ 在 charset 里**已有**对偶码 (0xB1A1 = slot 1504); 0xB5 = slot 2349。
#   出处: tools/text_csv/icon_table.py (0xB1=△三角键 / 0xB5=✕叉键) + tcslib 的 PUA 回落口径
#   (decode 对未映射字节产出 U+E0XX ⇒ 0xB5 ↔ U+E0B5)。
ICON_CHARS = {0xB1: '\u25b3', 0xB5: '\u2715'}
#   ★ ✕ 的**字符名有两种口径**, 必须都能认 (2026-10-15 实测):
#     · `\ue0b5` (U+E0B5) = tcslib 对未映射字节的 PUA 回落名 —— `charset_pairs_patch.json`
#       与 `migration_pairs.json` 里写的就是它;
#     · `\u2715` (U+2715 MULTIPLICATION X) = **几何执行者合并后的 charset 实际用的名字**
#       (`tools/font_pipeline/data/charset_compiled_zh16.json` slot 2349)。
#   两边不一致时**以 charset 为准** (gate_pairs.json 的 `_must_merge` 就是这么写的):
#   下面的 `_icon_char()` 按"先 charset 实际名, 再别名"的顺序解析, 免得又去借一个空槽,
#   把文本指到**没有字形**的 slot 上。
ICON_CHARS_ALIASES = {0xB5: ('\u2715', '\ue0b5', '\u00d7')}


def _icon_char(b, pair_of):
    """解析图标码 `b` 对应的**字符名**: 优先 charset 里真有对偶码的那个别名。"""
    for cand in (ICON_CHARS.get(b),) + ICON_CHARS_ALIASES.get(b, ()):
        if cand and cand in pair_of:
            return cand
    return ICON_CHARS.get(b)
# 旧单字节码 → 字 的**兜底补表** (charset 的 `codes` 里查不到时用)。
#   · 0xB2/0xB3/0xB4 = 键/练/用: 出自 r82 抬闸门**之前**的 charset
#     (`work/builds/GR_ZH98/temp/r82/charset_before_r82.json`), 之后它们进了对偶空间。
#   · 0xB6..0xB9 = 击/小/时/按: LEAD §15.1 合并 (2026-10-15) 把这 4 条**从 charset.codes
#     摘掉**了 (抬闸门后它们是前导, 留着会被编码器写成裸前导字节) ⇒ 合并后的 charset 查不到,
#     必须在这里兜底, 否则工具会以为它们"没有字"而去借空槽 —— 那会把文本指到**没有字形**
#     的 slot 上 (实测 charset 的 2340..2344 是 PUA 占位 U+E394..U+E398)。
#     字名出处: charset_pairs_patch.json / migrate_legacy_audit.LEGACY_TAB / 盘上字形辨认。
#   ★ 顺序不变: `charset.codes` 优先, 这里只在查不到时兜底 ⇒ 合并前后行为一致。
LEGACY_CHARS = {0xB2: '\u952e', 0xB3: '\u7ec3', 0xB4: '\u7528',     # 键 / 练 / 用
                0xB6: '\u51fb', 0xB7: '\u5c0f', 0xB8: '\u65f6', 0xB9: '\u6309'}  # 击/小/时/按

XML_NODE_RE = re.compile(rb'>([^<>]{1,400})<')      # 与 dump_all_text.RE_NODE 同口径
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


class MigrationError(SystemExit):
    """自检失败 —— 一律 `[!!]` 前缀报出并中止 (不写盘)。"""


def BOOM(msg):
    raise MigrationError('[!!] %s' % msg)


# ═══════════════════════ 载荷区间 (与 dump_all_text 同口径) ═══════════════════════
def _xml_attrs(blob):
    """SFXML `<item|group|studio name="…">` 标题属性值区间。

    ★ 复用回写链的 `inject_text_csv.parse_xml_attrs` (importlib 隔离加载, 与
      tools/re/toolbelt/f364_patch.py 同一手法) —— 保证"迁移"与"回写"认的是同一批属性。
    """
    if not hasattr(_xml_attrs, 'fn'):
        p = os.path.join(REPO, 'tools', 'text_csv', 'inject_text_csv.py')
        spec = importlib.util.spec_from_file_location('inj_attrs_for_migrate', p)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except SystemExit:
            pass
        _xml_attrs.fn = mod.parse_xml_attrs
    return _xml_attrs.fn(blob)


def merge_ranges(rng):
    """区间并集 (排序 + 合并重叠/相邻)。返回 [start, end) 列表。"""
    out = []
    for (s, e) in sorted(rng):
        if e <= s:
            continue
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(s, e) for (s, e) in out]


def sf_region_counts(blob, used, mp, base_gate, gate):
    """SFXML 的迁移落点按区域拆解 (取证用)。

    ★ 为什么需要: `dump_all_text.py` 对 SFXML 只用 `>([^<>]{2,400})<` 抽文本节点 ——
      **长度 > 400 字节的 `<text>` 正文**它一个都看不见, `name="…"` 标题属性也看不见;
      而这两类都是**上屏文本** (标题通道见 docs/REPORT_final_364.md)。所以 dump 口径
      统计出来的迁移量是**下界**, 不是真值。本函数给出真值的拆解。
    """
    texts = [(o, o + ln) for (_k, o, ln, _b) in T.parse_sfxml(blob) if o < used]
    attrs = [(o, o + len(v)) for (_k, _t, o, v) in _xml_attrs(blob) if o < used]
    dump_rng = merge_ranges(
        [(m.start(1), m.end(1)) for m in XML_NODE_RE.finditer(blob) if blob[m.start(1):m.end(1)].strip()]
        + [(m.start(2), m.end(2)) for m in
           re.finditer(rb'<(studio|group)\s+name="([^"]*)"', blob)])
    dump_rng = [(s, min(e, used)) for (s, e) in dump_rng if s < used and e - s >= 2]

    def count(rngs):
        tot = 0
        for (s, e) in merge_ranges([(a, min(b, used)) for (a, b) in rngs if a < used]):
            d, j, k = blob[s:e], 0, 0
            while j < len(d):
                x = d[j]
                if T.LEAD_LO <= x < base_gate:
                    j += 2
                    continue
                if base_gate <= x < gate:
                    k += 1
                j += 1
            tot += k
        return tot

    # <text> 正文按长度分档 (dump 的 RE_NODE 只看得到 ≤400 的)
    short = count([r for r in texts if r[1] - r[0] <= 400])
    long_ = count([r for r in texts if r[1] - r[0] > 400])
    return dict(text_total=count(texts), text_le400=short, text_gt400=long_,
                attr_name=count(attrs), dump_scope=dump_rng and count(dump_rng) or 0,
                n_text=len(texts), n_text_gt400=len([r for r in texts if r[1] - r[0] > 400]),
                n_attr=len(attrs))


def payload_ranges(cont):
    """容器里**会被引擎当文本渲染**的字节区间 (迁移只允许落在这些区间内)。

    LANG  : 每条目的 payload (4B len 前缀 / 2B attr / 组分隔 是结构, 不算 payload)
    SFXML : `<text>` 正文 ∪ `name="…"` 标题属性 ∪ 其它文本节点 (≡ dump_all_text 的 RE_NODE)
            —— 取并集是为了让"重跑 dump_all_text"看到 0 残留。
    """
    blob = cont['blob']
    if cont['name'] == 'LANG':
        ents, used = T.parse_lang(blob)
        return ([(e.data_off, e.data_off + e.length) for e in ents], used,
                {'lang_entries': len(ents)})
    rng = [(o, o + ln) for (_k, o, ln, _b) in T.parse_sfxml(blob)]
    attrs = [(o, o + len(v)) for (_k, _t, o, v) in _xml_attrs(blob)]
    nodes = [(m.start(1), m.end(1)) for m in XML_NODE_RE.finditer(blob)]
    nodes = [(s, e) for (s, e) in nodes if blob[s:e].strip()]
    used = T.xml_tail_start(blob)
    rng = [(s, min(e, used)) for (s, e) in (rng + attrs + nodes) if s < used]
    return (merge_ranges(rng), used,
            {'xml_text': len(rng), 'xml_attrs': len(attrs), 'xml_nodes': len(nodes)})


# ═══════════════════════ 迁移映射 ═══════════════════════
def build_map(cs, base_gate, gate, pairs_in, reserve, gate_cap):
    """构造 {byte: (char, (b1,b2), 来源)} —— 待迁移字节 → 字 → 对偶码。

    `cs` = tcslib.Charset (char → 单字节码 / char → 对偶码)
    `pairs_in` = sidecar 借条 {char: [b1,b2]} (charset 里还没有时用)
    `reserve` = True 时允许从容量顶部借空槽
    """
    pair_of = {ch: tuple(p) for ch, p in cs.enc_pair.items()}
    codes = dict(cs.enc_single)
    byte2ch = dict(cs.codes)
    used_slots = set()
    for p in pair_of.values():
        used_slots.add((p[0] - T.LEAD_LO) * T.PAIR_STRIDE + (p[1] - T.PAIR_TRAIL_LO))

    out, need = {}, []
    for b in range(base_gate, gate):
        ch, src = byte2ch.get(b), 'charset.codes'
        if ch is None and b in LEGACY_CHARS:
            ch, src = LEGACY_CHARS[b], ('兜底补表 LEGACY_CHARS (r82 前的 charset / §15.1 合并后'
                                        ' charset.codes 已摘除)')
        if ch is None and b in ICON_CHARS:
            ch = _icon_char(b, pair_of)
            src = ('引擎图标码 (icon_table.py; charset 里的名字 = %r%s)'
                   % (ch, '' if ch == ICON_CHARS[b] else
                      ' ← 与工具默认名 %r 不同, 已按 charset 对齐' % ICON_CHARS[b]))
        if ch is None:
            out[b] = (None, None, '未登记字节 (既不在 charset.codes, 也不是引擎图标码)')
            continue
        if ch in codes and codes[ch] < base_gate:
            out[b] = (ch, None, '字 %r 的单字节码 0x%02X 在闸门之外 —— 无需迁移'
                      % (ch, codes[ch]))
            continue
        pair = pair_of.get(ch)
        if pair is None and ch in pairs_in:
            pair, src = tuple(pairs_in[ch]), src + ' + sidecar 借条'
        if pair is None:
            need.append((b, ch, src))
            continue
        out[b] = (ch, pair, src)

    extra_pairs = {}
    if need:
        if not reserve:
            BOOM('以下 %d 个字节要迁移, 但它们的字在 charset 里**没有对偶码**:\n%s\n'
                 '   闸门 0x%02X 容量 = %d 槽, charset 已占 %d, 空 %d\n'
                 '   处置: ① 让几何路把新字落进 charset 后重跑本工具; 或\n'
                 '         ② 显式 --reserve-slots (从容量**顶部**往下借, 借条写 --pairs-out)'
                 % (len(need),
                    '\n'.join('     0x%02X → %r   [%s]' % (b, ch, s) for (b, ch, s) in need),
                    gate, gate_cap, len(used_slots), gate_cap - len(used_slots)))
        free = [s for s in range(gate_cap - 1, -1, -1) if s not in used_slots]
        if len(free) < len(need):
            BOOM('空槽不足: 需要 %d, 只剩 %d' % (len(need), len(free)))
        for k, (b, ch, src) in enumerate(need):
            slot = free[k]
            pair = T.pair_from_slot(slot)
            extra_pairs[ch] = pair
            out[b] = (ch, pair, '%s + ★借槽 slot %d = 0x%02X%02X'
                      % (src, slot, pair[0], pair[1]))
    return out, extra_pairs


def check_map(mp, base_gate, gate):
    """[S1] 映射自洽: 每个待迁移字节都有字 + 合法对偶码。"""
    bad = []
    for b in range(base_gate, gate):
        ch, pair, src = mp.get(b, (None, None, '缺少映射项'))
        if ch is None or pair is None:
            bad.append('0x%02X: %s' % (b, src))
            continue
        if not (T.LEAD_LO <= pair[0] < gate):
            bad.append('0x%02X (%r): lead 0x%02X ∉ [0x%02X,0x%02X)'
                       % (b, ch, pair[0], T.LEAD_LO, gate))
        if not (T.PAIR_TRAIL_LO <= pair[1] <= T.PAIR_TRAIL_HI):
            bad.append('0x%02X (%r): trail 0x%02X ∉ [0x%02X,0x%02X]'
                       % (b, ch, pair[1], T.PAIR_TRAIL_LO, T.PAIR_TRAIL_HI))
    if bad:
        BOOM('[S1] 迁移映射不完整/不合法 (%d 条):\n     %s' % (len(bad), '\n     '.join(bad)))


# ═══════════════════════ 解码 / 编码 (闸门显式传入) ═══════════════════════
def decode_with(data, gate, pair_of, codes, pua_base=0xE000):
    """按**给定闸门**解码 (引擎口径: `0xA1 <= b < gate` ⇒ 无条件吃两字节)。

    gate = 0xB1 ⇒ 基底语义 (0xB1..0xB9 是单字节字)
    gate = 0xBA ⇒ 新语义 (0xB1..0xB9 是 lead)
    返回 (文本, [(字符序, 起点偏移, 消费字节数)])。
    """
    out, mp, i, n = [], [], 0, len(data)
    while i < n:
        v = data[i]
        if v < 0x80:
            out.append(chr(v)); mp.append((i, 1)); i += 1
        elif T.LEAD_LO <= v < gate:
            if i + 1 >= n:
                out.append('\uFFFD<孤 lead 0x%02X>' % v); mp.append((i, 1)); i += 1
                continue
            pair = (v, data[i + 1])
            out.append(pair_of.get(pair, '\uFFFD<pair 0x%02X%02X>' % pair))
            mp.append((i, 2)); i += 2
        else:
            out.append(codes.get(v, chr(pua_base + v))); mp.append((i, 1)); i += 1
    return ''.join(out), mp


def canonical_encode(text, pair_of, codes, single_pref, gate):
    """文本 → **规范字节** (与 decode_with(gate) 互逆)。

    优先级: ASCII 直通 → 对偶码 (charset ∪ 本次迁移映射) → 单字节码 → 引擎图标单字节码。
    ★ 与 tcslib.Charset.encode 的差别: 那里"占位/单字节码优先"; 这里**对偶码优先** ——
      抬闸门后落进 `[0xA1,gate)` 的单字节码会被当 lead 吃掉, 只有对偶码能表达它。
    `pair_of` 由调用方合并 charset 与迁移映射后传入。
    """
    pair_of_ch = {}
    for ch, p in pair_of.items():
        pair_of_ch.setdefault(ch, tuple(p))
    out = bytearray()
    for ch in text:
        o = ord(ch)
        if o < 0x80:
            out.append(o); continue
        if ch in pair_of_ch:
            out += bytes(pair_of_ch[ch]); continue
        if ch in codes:
            if T.LEAD_LO <= codes[ch] < gate:
                raise KeyError('字 %r 的单字节码 0x%02X 落在闸门区间 [0x%02X,0x%02X) 内, '
                               '但它没有对偶码 ⇒ 无法规范编码' % (ch, codes[ch], T.LEAD_LO, gate))
            out.append(codes[ch]); continue
        if ch in single_pref:
            sb = single_pref[ch]
            # ★ 引擎图标单字节码 (0xB1/0xB5) 落在闸门区间内 ⇒ 抬闸门后写它=写一个会吞字节的
            #   lead。必须报错, 不许"能用就用" (否则 S6 会静默放行一个实机必崩的写法)。
            if T.LEAD_LO <= sb < gate:
                raise KeyError('字 %r (U+%04X) 只有引擎图标单字节码 0x%02X, 而它落在闸门区间 '
                               '[0x%02X,0x%02X) 内 ⇒ 抬闸门后不可按单字节写; 需要 charset 里的对偶码'
                               % (ch, o, sb, T.LEAD_LO, gate))
            out.append(sb); continue
        raise KeyError('字 %r (U+%04X) 既无对偶码也无单字节码' % (ch, o))
    return bytes(out)


# ═══════════════════════ 迁移一个载荷 ═══════════════════════
def migrate_payload(data, mp, base_gate, gate, stat):
    """把载荷里裸的 `base_gate..gate-1` 改写成对偶码。**只动这些字节, 其余逐字节照搬。**"""
    out, i, n, k = bytearray(), 0, len(data), 0
    while i < n:
        v = data[i]
        if T.LEAD_LO <= v < base_gate:          # 基底语义: 合法对偶 lead (吃 2 字节)
            out += data[i:i + 2]
            i += 2
            continue
        if base_gate <= v < gate:               # ★ 待迁移的旧单字节码
            ch, pair, _src = mp[v]
            out += bytes(pair)
            stat['per_code'][v] = stat['per_code'].get(v, 0) + 1
            stat['per_char'][ch] = stat['per_char'].get(ch, 0) + 1
            k += 1
            i += 1
            continue
        out.append(v)
        i += 1
    return bytes(out), k


def rebuild_container(cont, ranges, mp, base_gate, gate):
    """重建容器 blob: 只改载荷区间 (长度前缀一起改写); 增长吃陈旧尾巴 ⇒ 总长不变。

    返回 (new_blob, stat, growth, 新载荷表)。
    """
    blob = cont['blob']
    used = cont['used_end']
    stat = {'per_code': {}, 'per_char': {}, 'n': 0, 'ranges': len(ranges), 'changed': 0}
    edits, new_pays = [], {}
    for (s, e) in ranges:
        seg = blob[s:e]
        new, k = migrate_payload(seg, mp, base_gate, gate, stat)
        stat['n'] += k
        new_pays[(s, e)] = new
        if new == seg:
            continue
        stat['changed'] += 1
        if cont['name'] == 'LANG':
            assert struct.unpack_from('<I', blob, s - 4)[0] == e - s, (cont['tag'], s)
            edits.append((s - 4, e, struct.pack('<I', len(new)) + new))
        else:
            edits.append((s, e, new))
    if not edits:
        return blob, stat, 0, new_pays

    # ── [S2] 反向重建 (等价于"除载荷区间外逐字节不变"; 改长时后面的字节整体平移也成立) ──
    spliced = T.splice(blob, edits)
    shift, undo = 0, []
    for (a, b, nb) in sorted(edits, key=lambda x: x[0]):
        undo.append((a + shift, a + shift + len(nb), blob[a:b]))
        shift += len(nb) - (b - a)
    if T.splice(spliced, undo) != blob:
        BOOM('[S2] %s 反向重建与源 blob 不符 —— 有改动落在载荷区间之外, 拒绝写盘'
             % cont['tag'])

    growth = len(spliced) - len(blob)
    if growth > 0:
        tail_free = len(blob) - used
        if growth > tail_free:
            BOOM('%s 装不下: 内容变长 %+d B, 而 used_end(0x%X) 之后的陈旧尾巴只有 %d B '
                 '(差 %d B)。\n'
                 '   解压总长被 IMG 条目表的 real 字段钉死 (不许动条目表), 增长只能吃陈旧尾巴;\n'
                 '   本工具**不截断、不静默丢字、也不改条目表**。\n'
                 '   本容器: blob %d B / 载荷 %d 区间 / 每处 +1 B ; '
                 'IMG 相邻条目间距 = %s B (扇区对齐余量, 不是可用空间)。\n'
                 '   处置: 由 LEAD 重排 (扩容需改 IMG 的 stored/real 并搬移后续数据, 属结构性改动),'
                 ' 或把本容器放进 --skip 列表。'
                 % (cont['tag'], growth, used, tail_free, growth - tail_free,
                    len(blob), len(ranges), cont.get('img_gap', '?')))
        trimmed = spliced[len(blob):]
        nz = sum(1 for x in trimmed if x)
        stat['tail_trimmed'] = len(trimmed)
        stat['tail_trimmed_nonzero'] = nz
        new_blob = spliced[:len(blob)]
    elif growth < 0:
        new_blob = spliced + b'\x00' * (-growth)
        stat['tail_trimmed'] = 0
        stat['tail_trimmed_nonzero'] = 0
    else:
        new_blob = spliced
        stat['tail_trimmed'] = 0
        stat['tail_trimmed_nonzero'] = 0
    assert len(new_blob) == len(blob), (cont['tag'], len(new_blob), len(blob))
    return new_blob, stat, growth, new_pays


def repack(cont, new_blob):
    """按子流重压: 未变子流照搬原压缩字节, 变了的重压并回环自检。"""
    assert len(new_blob) == len(cont['blob']), '解压总长必须不变'
    frame, q, n_rep = bytearray(), 0, 0
    for k, S in enumerate(cont['sizes']):
        part = new_blob[q:q + S]
        q += S
        if part == cont['subs'][k][0]:
            frame += cont['raws'][k]
            continue
        cc = T.lzo_compress(part, level=7, use_m1=True, use_m4=True)
        back, err, _ = T.lzo1x_decompress(cc, out_size=S)
        assert err is None and back == part, '%s 子流 %d 回环失败' % (cont['tag'], k)
        frame += struct.pack('<II', len(cc), S) + cc
        n_rep += 1
    assert q == len(new_blob)
    return bytes(frame), n_rep


# ═══════════════════════ 自检: 迁移后重扫 ═══════════════════════
def selfcheck_blob(cont, old_blob, new_blob, ranges, mp, base_gate, gate, old_pays,
                   new_pays, cs, stat, used_end):
    """[S3][S4][S5][S6] —— 迁移后的四道硬自检。返回 (迁移 lead 计数, 既存缺陷条数)。"""
    # ★ 两张方向相反的表, 别弄混:
    #   pair_dec : (b1,b2) → 字   —— 给 decode_with 用
    #   pair_of  : 字 → (b1,b2)   —— 给 canonical_encode 用
    pair_dec = dict(cs.pair_of)
    pair_of = {ch: tuple(p) for ch, p in cs.enc_pair.items()}
    for _b, (ch, pair, _s) in mp.items():          # 本次迁移写入的对偶码也进两张表
        if pair is not None:
            pair_dec.setdefault(tuple(pair), ch)
            pair_of.setdefault(ch, tuple(pair))
    codes = dict(cs.codes)                  # byte → 字    (给 decode_with)
    enc = dict(cs.enc_single)               # 字   → byte  (给 canonical_encode)
    # ★ 基底语义的"字表"必须补上**旧单字节码 → 字**那一层: 现行 charset 早已把
    #   键/练/用 (0xB2/0xB3/0xB4) 从 codes 里摘掉 (它们已在对偶空间), 0xB1/0xB5 从来
    #   只是引擎图标码。不补这一层, 基底解码会得出 U+E0B2 这种占位, 与迁移后的真字
    #   没法逐字符比对 (那是"表缺", 不是"迁移错")。
    codes_base = dict(codes)
    for b, (ch, _pair, _s) in mp.items():
        if ch is not None:
            codes_base.setdefault(b, ch)
    single_pref = {}
    for b, ch in ICON_CHARS.items():
        single_pref[ch] = b
        for alt in ICON_CHARS_ALIASES.get(b, ()):
            single_pref.setdefault(alt, b)
    allowed_pairs = set(tuple(v[1]) for v in mp.values() if v[1])

    # ── [S3] 逐载荷·基底语义重扫: 裸 `0xB1..GATE-1` 必须 0 处 ──
    #    ★ 只扫**载荷区间** (逐区间独立扫, 不跨区间连读): LANG 的 4B 长度前缀 / u16 attr /
    #      组分隔 都是**数字字段**, 里面出现 0xB2 这种字节是合法的 (实测 7 处 0xB5),
    #      引擎只按数字读它们, 从不渲染 ⇒ 不参与文本语义。dump 口径同样只看条目 payload。
    res, n_ok = [], 0
    for (s, e) in ranges:
        d = new_pays[(s, e)]
        i, n = 0, len(d)
        while i < n:
            v = d[i]
            if T.LEAD_LO <= v < base_gate:          # 基底语义的合法对偶 lead
                i += 2
                continue
            if base_gate <= v < gate:
                t = d[i + 1] if i + 1 < n else None
                if t is not None and (v, t) in allowed_pairs:
                    n_ok += 1
                    i += 2
                    continue
                res.append((s + i, v, t))
            i += 1
    if res:
        BOOM('[S3] %s 迁移后载荷里仍有 %d 处裸 `0xB1..0x%02X` (前 5: %s)'
             % (cont['tag'], len(res), gate - 1,
                ['@0x%X 0x%02X%s' % (o, b, '%02X' % t if t is not None else '??')
                 for (o, b, t) in res[:5]]))
    if n_ok != stat['n']:
        BOOM('[S3] %s 自洽计数不符: 重扫到 %d 个迁移对偶 lead, 迁移时写入 %d 个'
             % (cont['tag'], n_ok, stat['n']))

    # ── [S4] (登记项, 不阻断) 载荷之外还有多少 `0xB1..GATE-1` 的裸字节 ──
    #    结构区 = 数字字段 (长度/属性/计数), 陈旧尾巴 = used_end 之后引擎不读的旧数据。
    #    两者都**不是文本**, 按纪律一个字节都不动 —— 这里只如实登记数量, 便于日后复核。
    mask = bytearray(len(new_blob))
    for (s, e) in ranges:
        mask[s:e] = b'\x01' * (e - s)
    struct_n = tail_n = 0
    for i in range(len(new_blob)):
        v = new_blob[i]
        if not (base_gate <= v < gate) or mask[i]:
            continue
        if i >= used_end:
            tail_n += 1
        else:
            struct_n += 1
    stat['struct_legacy_bytes'] = struct_n

    # ── [S5] 逐载荷: 基底语义解出的字序列 == 新闸门语义解出的字序列 ──
    bad, preexisting = [], []
    for (s, e) in ranges:
        raw_old, raw_new = old_pays[(s, e)], new_pays[(s, e)]
        t_old, _ = decode_with(raw_old, base_gate, pair_dec, codes_base)
        t_new, _ = decode_with(raw_new, gate, pair_dec, codes)
        if t_old != t_new:
            k = next((j for j in range(min(len(t_old), len(t_new))) if t_old[j] != t_new[j]),
                     min(len(t_old), len(t_new)))
            bad.append('@0x%X: 基底 %r ≠ 新闸门 %r (首差 @%d)'
                       % (s, t_old[max(0, k - 8):k + 8], t_new[max(0, k - 8):k + 8], k))
            if len(bad) > 4:
                break
    if bad:
        BOOM('[S5] %s 逐字符一致**不成立**:\n     %s' % (cont['tag'], '\n     '.join(bad)))

    # ── [S6] 新载荷 == "解码文本的规范编码"; 既存非法对偶码只登记不阻断 ──
    for (s, e) in ranges:
        raw_old, new = old_pays[(s, e)], new_pays[(s, e)]
        t_old, _ = decode_with(raw_old, base_gate, pair_dec, codes_base)
        t_new, _ = decode_with(new, gate, pair_dec, codes)
        try:
            want = canonical_encode(t_new, pair_of, enc, single_pref, gate)
        except KeyError as ex:
            # 源盘里就有"闸门区间内但谁也解不出"的字节 (既存缺陷) —— 迁移不负责造字,
            # 但**必须**如实登记: 这类位置在实机上画的是空白/错字。
            if '\uFFFD<' in t_old or '\uFFFD<' in t_new:
                preexisting.append((s, e, str(ex)))
                continue
            BOOM('[S6] %s @0x%X 规范编码失败: %s' % (cont['tag'], s, ex))
        if want != new:
            k = next((j for j in range(min(len(want), len(new))) if want[j] != new[j]),
                     min(len(want), len(new)))
            BOOM('[S6] %s @0x%X 非规范写法 (首差 @%d): 盘上 %s ≠ 规范 %s'
                 % (cont['tag'], s, k, new[max(0, k - 4):k + 6].hex(),
                    want[max(0, k - 4):k + 6].hex()))
    if tail_n:
        stat['tail_legacy_bytes'] = tail_n
    return n_ok, preexisting


# ═══════════════════════ 全盘 diff 窗口 ═══════════════════════
def diff_windows(src, dst, windows, chunk=1 << 22):
    """逐块比对两个文件, 返回 (差异字节数, 窗口外差异位置列表, 差异区间列表)。"""
    win = sorted(windows)
    n, outside, spans = 0, [], []
    with open(src, 'rb') as f1, open(dst, 'rb') as f2:
        pos = 0
        while True:
            a = f1.read(chunk)
            b = f2.read(chunk)
            if not a:
                break
            if a != b:
                i = 0
                while i < len(a):
                    if a[i] != b[i]:
                        j = i
                        while j < len(a) and a[j] != b[j]:
                            j += 1
                        p = pos + i
                        n += j - i
                        spans.append((p, pos + j))
                        if not any(w0 <= p < w0 + wl for (w0, wl) in win):
                            outside.append(p)
                        i = j
                    else:
                        i += 1
            pos += len(a)
    return n, outside, spans


# ═══════════════════════ 主流程 ═══════════════════════
def _select_containers(sel, skips, P):
    """按 `--containers` / `--skip` 从 `CONTAINER_SPECS` 里挑出本轮要动的容器。

    `--containers` 接受: `all` (默认, 7 个) / `core` (3 个中文) / `esfr` (ES+FR) /
    逗号分隔的 tag 列表 (支持子串匹配, 大小写不敏感) —— tag 形如
    `ES_STRINGS.RES@MENU` 或省略 `@` 后的部分。
    `--skip` 可重复, 语义与 `--containers` 的 tag 相同 (先选后剔)。
    """
    s = (sel or 'all').strip()
    low = s.lower()
    if low == 'all':
        picked = list(CONTAINER_SPECS)
    elif low == 'core':
        picked = [x for x in CONTAINER_SPECS if x[4] in CORE_TAGS]
    elif low == 'esfr':
        picked = [x for x in CONTAINER_SPECS if x[4] in ESFR_TAGS]
    else:
        want = [t.strip().lower() for t in s.split(',') if t.strip()]
        picked = [x for x in CONTAINER_SPECS
                  if any(w == x[4].lower() or w in x[4].lower() or w == x[5] for w in want)]
        miss = [w for w in want if not any(w == x[4].lower() or w in x[4].lower() or w == x[5]
                                           for x in CONTAINER_SPECS)]
        if miss:
            BOOM('--containers 里有认不出的容器: %s\n   可选: all / core / esfr / %s'
                 % (miss, ', '.join(x[4] for x in CONTAINER_SPECS)))
    for t in (skips or []):
        tl = t.strip().lower()
        kept = [x for x in picked if not (tl == x[4].lower() or tl in x[4].lower())]
        if len(kept) == len(picked):
            BOOM('--skip %s 没有匹配到任何容器 (它可能本来就不在清单里, 或已被 --containers 排除)'
                 % t)
        picked = kept
    if not picked:
        BOOM('容器选择结果为空 —— 没什么可迁移的')
    return picked


def main(argv):
    ap = argparse.ArgumentParser(description='旧单字节码全量迁移 + ELF gate 抬升')
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--base-gate', default='0x%02X' % BASE_GATE_DEFAULT,
                    help='源盘 ELF 闸门 (默认 0xB1)')
    ap.add_argument('--gate', default='0x%02X' % GATE_DEFAULT,
                    help='目标闸门 (默认 0xBA)')
    ap.add_argument('--charset', default=CHARSET)
    ap.add_argument('--pairs-in', default=None, help='sidecar 借条 (读)')
    ap.add_argument('--pairs-out', default=None, help='sidecar 借条 (写; 默认 <out>/migration_pairs.json)')
    ap.add_argument('--reserve-slots', action='store_true',
                    help='charset 缺对偶码时, 从闸门容量顶部借空槽 (默认拒绝)')
    ap.add_argument('--no-elf', action='store_true',
                    help='不打 ELF 闸门 (几何先行流程: 源盘闸门已 == --gate)')
    ap.add_argument('--containers', default='all',
                    help="容器选择: all(默认 7 个) / core(3 个中文) / esfr(ES+FR) / tag,tag,…")
    ap.add_argument('--skip', action='append', default=[], metavar='TAG',
                    help='显式不动的容器 tag (可重复)')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--out', default=None, help='报告输出目录 (默认 %s)' % OUT_DEFAULT)
    ap.add_argument('--skip-diff', action='store_true', help='跳过全盘 diff (省时间)')
    a = ap.parse_args(argv)

    base_gate = int(a.base_gate, 16)
    gate = int(a.gate, 16)
    out = os.path.abspath(a.out or OUT_DEFAULT)
    os.makedirs(out, exist_ok=True)
    gate_cap = (gate - T.LEAD_LO) * T.PAIR_STRIDE

    P('=' * 82)
    P('migrate_legacy.py — 旧单字节码全量迁移 + ELF gate 抬升')
    P('  src       = %s' % a.src)
    P('  dst       = %s' % (a.dst or '(dry-run)'))
    P('  base_gate = 0x%02X   gate = 0x%02X   (闸门容量 %d 槽)'
      % (base_gate, gate, gate_cap))
    P('  charset   = %s' % a.charset)
    P('=' * 82)

    cs = T.Charset(a.charset)
    P('[cs ] charset: 单字节码 %d 个 / 对偶码 %d 个 ; 已占槽 %s'
      % (len(cs.enc_single), len(cs.enc_pair),
         sorted(set((p[0] - T.LEAD_LO) * T.PAIR_STRIDE + (p[1] - T.PAIR_TRAIL_LO)
                    for p in cs.enc_pair.values()))[-1:] or '—'))

    pairs_in = {}
    if a.pairs_in and os.path.isfile(a.pairs_in):
        j = json.load(io.open(a.pairs_in, encoding='utf-8'))
        pairs_in = {k: v for k, v in j.get('pairs', j).items()}
        P('[cs ] sidecar 借条 %s: %d 条' % (a.pairs_in, len(pairs_in)))

    mp, extra = build_map(cs, base_gate, gate, pairs_in, a.reserve_slots, gate_cap)
    check_map(mp, base_gate, gate)
    P('[S1] 迁移映射 ✓  共 %d 个字节档:' % (gate - base_gate))
    for b in range(base_gate, gate):
        ch, pair, src = mp[b]
        P('     0x%02X → %-4s 对偶 0x%02X%02X (slot %4d)   [%s]'
          % (b, ch if ch else '—', pair[0], pair[1],
             (pair[0] - T.LEAD_LO) * T.PAIR_STRIDE + (pair[1] - T.PAIR_TRAIL_LO), src))
    if extra:
        P('[cs ] ★ 借槽 %d 个 (charset 未写, 需几何路并入):' % len(extra))
        for ch, p in extra.items():
            P('     %r → 0x%02X%02X (slot %d)'
              % (ch, p[0], p[1], (p[0] - T.LEAD_LO) * T.PAIR_STRIDE + (p[1] - T.PAIR_TRAIL_LO)))
    pairs_out = a.pairs_out or os.path.join(out, 'migration_pairs.json')
    if extra and not a.dry_run:
        with io.open(pairs_out, 'w', encoding='utf-8', newline='\n') as f:
            json.dump({'note': 'migrate_legacy.py 借槽借条: charset 里还没有这些对偶码; '
                               '几何路必须把它们写进 charset 并在图集对应格画上字形',
                       'base_gate': base_gate, 'gate': gate,
                       'pairs': {ch: list(p) for ch, p in extra.items()}},
                      f, ensure_ascii=False, indent=1)
        P('[cs ] 借条已写 %s' % pairs_out)

    # ── 装载容器 (清单见 CONTAINER_SPECS; --containers/--skip 选择) ──
    sel = _select_containers(a.containers, a.skip, P)
    iso = T.Iso(a.src)
    conts = []
    for (kind, img, lba, idx, tag, why) in sel:
        e = iso.img_entry(lba, idx)
        raw = iso.read(e['iso_off'], e['stored'])
        subs = T.lzo_subs(raw)
        nx = iso.img_entry(lba, idx + 1)
        gap = (nx['off'] - e['off'] - e['stored']) if nx['off'] > e['off'] else None
        conts.append(dict(name=kind, tag=tag, img=img, lba=lba, idx=idx, entry=e,
                          why=why, img_gap=gap,
                          raw=bytes(raw), subs=subs,
                          blob=b''.join(s[0] for s in subs),
                          sizes=[s[2] for s in subs],
                          raws=[bytes(raw[s[3]:s[3] + 8 + s[1]]) for s in subs],
                          slot=e['stored'],
                          frame_len=sum(8 + s[1] for s in subs),
                          iso_off=e['iso_off'], iso_size=e['stored']))
    P('[sel] 本轮容器 %d 个 (--containers %s%s):' % (len(conts), a.containers,
                                                     '' if not a.skip else
                                                     ' --skip ' + ','.join(a.skip)))
    for c in conts:
        P('      %-24s IMG %-8s #%-4d %s' % (c['tag'], c['img'], c['idx'], c['why']))
    for (kind, img, lba, idx, tag, why) in EXCLUDED_SPECS:
        P('      %-24s ★ 明确不动 (%s)' % (tag, why))

    # ── ELF gate 校验 + 目标值 ──
    elf_patch, elf_seen = [], []
    for va in ELF_SITES:
        off = ELF_ISO_BASE + va - ELF_VA_BASE
        w0 = struct.unpack_from('<I', iso.mm, off)[0]
        imm = w0 & 0xFFFF
        elf_seen.append((va, off, w0, imm))
        if not a.no_elf and imm != gate:
            elf_patch.append((off, (w0 & 0xFFFF0000) | gate, imm, w0))
    P('[elf] 4 站点:', ' '.join('%s@0x%X imm=0x%02X' % (hex(va), off, imm)
                               for (va, off, _w, imm) in elf_seen))
    if a.no_elf:
        # 几何先行流程: 闸门已由几何路设好 ⇒ 源盘 imm 必须**已经等于** gate, 回读也按 gate 校验
        wrong = [x for x in elf_seen if x[3] != gate]
        if wrong:
            BOOM('[elf] --no-elf 要求源盘闸门立即数**已经等于** 0x%02X, 实测: %s\n'
                 '   源盘 imm == 0x%02X ⇒ 它还没抬闸门, 请去掉 --no-elf (让本工具打闸门)。'
                 % (gate, ['%s imm=0x%02X' % (hex(va), imm)
                           for (va, _o, _w, imm) in wrong], base_gate))
        P('[elf] --no-elf: 源盘 4/4 站点已 == 0x%02X ✓ ⇒ 本轮不动 ELF (几何路已设好)' % gate)
    else:
        wrong = [x for x in elf_seen if x[3] != base_gate]
        if wrong:
            BOOM('[elf] 源盘 gate 立即数 ≠ 0x%02X: %s —— 源盘闸门不对, 拒绝按 0x%02X 语义解析'
                 % (base_gate, ['%s imm=0x%02X' % (hex(va), imm) for (va, _o, _w, imm) in wrong],
                    base_gate))
        P('[elf] 4/4 站点 == 0x%02X ✓ ⇒ 将改成 0x%02X (每站点只动低 2 字节)' % (base_gate, gate))

    # ── 逐容器迁移 ──
    totals = {'n': 0}
    per_tag = {}
    pre_all = []
    plans = []
    for cont in conts:
        ranges, used, info = payload_ranges(cont)
        cont['used_end'] = used
        old_pays = {r: cont['blob'][r[0]:r[1]] for r in ranges}
        new_blob, stat, growth, new_pays = rebuild_container(cont, ranges, mp,
                                                            base_gate, gate)
        n_ok, pre = selfcheck_blob(cont, cont['blob'], new_blob, ranges, mp, base_gate, gate,
                                   old_pays, new_pays, cs, stat, used)
        pre_all.extend([(cont['tag'], s, e, why) for (s, e, why) in pre])
        frame, n_rep = (cont['raw'], 0)
        if new_blob != cont['blob']:
            frame, n_rep = repack(cont, new_blob)
            if len(frame) > cont['slot']:
                BOOM('%s 重压后帧 %d B > 槽 %d B (超 %d B) —— 不许改条目表, 拒绝写盘。\n'
                     '   处置: 减少本容器改动量, 或与几何路协调条目表空间。'
                     % (cont['tag'], len(frame), cont['slot'], len(frame) - cont['slot']))
        per_tag[cont['tag']] = dict(
            n=stat['n'], growth=growth, ranges=stat['ranges'], changed=stat['changed'],
            per_code={('0x%02X' % k): v for k, v in sorted(stat['per_code'].items())},
            per_char=stat['per_char'], frame=len(frame), slot=cont['slot'],
            frame_slack=cont['slot'] - len(frame), n_repack=n_rep,
            tail_trimmed=stat.get('tail_trimmed', 0),
            tail_trimmed_nonzero=stat.get('tail_trimmed_nonzero', 0),
            tail_legacy_bytes=stat.get('tail_legacy_bytes', 0),
            used_end=used, blob=len(cont['blob']), info=info, selfcheck_ok=n_ok,
            preexisting=[dict(off=s, end=e, why=w) for (s, e, w) in pre])
        totals['n'] += stat['n']
        plans.append((cont, frame, new_blob))
        P('[mig] %-24s 载荷 %5d 区间 / 改 %5d 个 / 命中 %4d 个字符串 / 解压 %+d B ; '
          '帧 %d→%d B (槽 %d, 余 %d) ; 重压 %d 子流'
          % (cont['tag'], stat['ranges'], stat['n'], stat['changed'], growth,
             cont['frame_len'], len(frame), cont['slot'], cont['slot'] - len(frame), n_rep))
        P('      逐码: %s' % ' '.join('0x%02X:%d' % (k, v)
                                      for k, v in sorted(stat['per_code'].items())))
        if stat.get('tail_trimmed'):
            P('      陈旧尾巴裁掉 %d B (其中非零 %d B, 全部在 used_end=0x%X 之后)'
              % (stat['tail_trimmed'], stat.get('tail_trimmed_nonzero', 0), used))
        if stat.get('tail_legacy_bytes') or stat.get('struct_legacy_bytes'):
            P('      载荷之外另有 `0xB1..0x%02X` 裸字节: 结构区(数字字段) %d 处 + '
              '陈旧尾巴 %d 处 —— 都不是文本, 引擎不渲染, 按纪律不动 ✓'
              % (gate - 1, stat.get('struct_legacy_bytes', 0),
                 stat.get('tail_legacy_bytes', 0)))
        if cont['name'] == 'SFXML':
            rc = sf_region_counts(cont['blob'], used, mp, base_gate, gate)
            per_tag[cont['tag']]['sf_regions'] = rc
            P('      按区域: <text> 正文 %d 处 (=≤400B 的 %d + **>400B 的 %d**) ; '
              'name= 标题属性 %d 处' % (rc['text_total'], rc['text_le400'],
                                        rc['text_gt400'], rc['attr_name']))
            P('      ★ 旧 dump 口径 (RE_NODE `>…<` 2..400 字节) 只看得到 %d 处 '
              '(**>400B 正文与 item 的 name= 属性都看不见**) ⇒ 真值 %d > 旧 dump 口径 %d, 差 %d'
              % (rc['dump_scope'], rc['text_total'] + rc['attr_name'],
                 rc['dump_scope'], rc['text_total'] + rc['attr_name'] - rc['dump_scope']))
            P('      ★ 该盲点已修 (LEAD §15.4): tools/diag/dump_all_text.py::extract_xml 改用 '
              'parse_sfxml + parse_xml_attrs ⇒ CSV 口径 = %d + %d = %d'
              % (rc['text_total'], rc['attr_name'], rc['text_total'] + rc['attr_name']))

    agg = {}
    for _tag, d in per_tag.items():
        for k, v in d['per_code'].items():
            agg[k] = agg.get(k, 0) + v
    P('[sum] 迁移合计 **%d** 处' % totals['n'])
    P('[sum] 逐码合计: %s' % ' '.join('%s:%d' % (k, agg[k]) for k in sorted(agg)))
    for b in range(base_gate, gate):
        k = '0x%02X' % b
        if k not in agg:
            P('[sum]   0x%02X: 0 处 (源盘里该码位的裸字节数 = 0)' % b)
    if sum(agg.values()) != totals['n']:
        BOOM('[sum] 逐码合计 %d ≠ 总数 %d' % (sum(agg.values()), totals['n']))
    if pre_all:
        P('[S6] 既存缺陷 %d 条 (源盘上就有"闸门区间内解不出的字节", 迁移不负责造字):'
          % len(pre_all))
        for (tag, s, e, why) in pre_all[:10]:
            P('     %s @0x%X..0x%X  %s' % (tag, s, e, why))

    if a.dry_run:
        P('[dry-run] 未写盘。报告: %s' % _save(out, a, base_gate, gate, per_tag, agg,
                                              elf_seen, elf_patch, None, totals['n'], extra,
                                              pre_all))
        iso.close()
        return 0

    # ── 写盘 ──
    if not a.dst:
        BOOM('缺 dst (非 dry-run 必须给产物路径)')
    os.makedirs(os.path.dirname(os.path.abspath(a.dst)), exist_ok=True)
    with open(a.src, 'rb') as fi, open(a.dst, 'wb') as fo:
        while True:
            blk = fi.read(1 << 22)
            if not blk:
                break
            fo.write(blk)
    with open(a.dst, 'r+b') as f:
        for (cont, frame, _nb) in plans:
            if frame == cont['raw']:
                continue
            f.seek(cont['iso_off'])
            f.write(frame + b'\x00' * (cont['slot'] - len(frame)))
        for (off, want, _imm, _w0) in elf_patch:
            f.seek(off)
            f.write(struct.pack('<I', want))
    P('[wr ] 已写 %s' % a.dst)

    # ── [S7] 回读产物盘 ──
    iso2 = T.Iso(a.dst)
    for (cont, frame, new_blob) in plans:
        e2 = iso2.img_entry(cont['lba'], cont['idx'])
        if (e2['stored'], e2['off'], e2['real']) != (cont['entry']['stored'],
                                                     cont['entry']['off'],
                                                     cont['entry']['real']):
            BOOM('[S7] %s IMG 条目表字段被改动' % cont['tag'])
        blob2 = b''.join(s[0] for s in T.lzo_subs(iso2.read(e2['iso_off'], e2['stored'])))
        if len(blob2) != len(cont['blob']):
            BOOM('[S7] %s 解压长度 %d ≠ %d' % (cont['tag'], len(blob2), len(cont['blob'])))
        if blob2 != new_blob:
            k = next((i for i in range(len(blob2)) if blob2[i] != new_blob[i]), 0)
            BOOM('[S7] %s 回读 blob ≠ 目标 (首差 @0x%X)' % (cont['tag'], k))
        P('[S7] %-24s 回读 blob %d B ✓ ; 条目表 (off=0x%X stored=%d real=%d) 未动 ✓'
          % (cont['tag'], len(blob2), e2['off'], e2['stored'], e2['real']))
    for (va, off, _w, _imm) in elf_seen:
        got = struct.unpack_from('<I', iso2.mm, off)[0]
        # 两条路径的终态都是 `gate`: 正常路径是本工具刚打上去的; `--no-elf` 路径是几何路
        # 已经设好的 (前面已断言源盘 imm == gate), 回读同样必须等于 gate。
        if (got & 0xFFFF) != gate:
            BOOM('[S7] ELF %s 回读 imm=0x%02X ≠ 0x%02X' % (hex(va), got & 0xFFFF, gate))
    P('[S7] ELF 4/4 站点回读 imm == 0x%02X ✓%s'
      % (gate, ' (--no-elf, 未改动)' if a.no_elf else ''))
    iso2.close()
    iso.close()

    # ── [S8] 尺寸 + 全盘 diff 窗口 ──
    s_src, s_dst = os.path.getsize(a.src), os.path.getsize(a.dst)
    if s_src != s_dst:
        BOOM('[S8] ISO 尺寸变了: %d → %d' % (s_src, s_dst))
    wins = []
    for (cont, _f, _nb) in plans:
        wins.append((cont['iso_off'], cont['slot']))
    for (off, _w, _i, _w0) in elf_patch:
        wins.append((off, 4))
    n, outside, spans = diff_windows(a.src, a.dst, wins)
    P('[S8] ISO 尺寸 %d == 源盘 ✓' % s_src)
    P('[S8] 全盘差异 = %d 字节, 落在 %d 个连续区间; 计划窗口 %d 个:'
      % (n, len(spans), len(wins)))
    for (o, l) in sorted(wins):
        k = [sp for sp in spans if o <= sp[0] < o + l]
        nb = sum(e - s2 for (s2, e) in k)
        P('      [0x%09X, 0x%09X) 长 %7d  差异 %7d B / %4d 区间  %s'
          % (o, o + l, l, nb, len(k), '★空 (无差异)' if not k else ''))
    ex = [sp for sp in spans][:6] + ([('...', '...')] if len(spans) > 6 else [])
    P('      差异区间示例: %s' % ' '.join('[0x%X,%d)' % (s2, e - s2) if isinstance(s2, int)
                                          else '...' for (s2, e) in ex))
    if outside:
        BOOM('[S8] **窗口外**有 %d 处差异 (前几个: %s) —— 拒绝接受本产物'
             % (len(outside), [hex(x) for x in outside[:8]]))
    if not spans:
        BOOM('[S8] 产物与源盘逐字节相同 —— 迁移**一处都没发生**, 请检查源盘/映射')

    rep = _save(out, a, base_gate, gate, per_tag, agg, elf_seen, elf_patch,
                dict(n=n, spans=spans, windows=wins, size=s_dst), totals['n'], extra,
                pre_all)
    P('[out] 报告: %s' % rep)
    return 0


def _save(out, a, base_gate, gate, per_tag, agg, elf_seen, elf_patch, diff, total, extra,
          pre_all=None):
    os.makedirs(out, exist_ok=True)
    p = os.path.join(out, 'migrate_report.json')
    with io.open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dict(src=a.src, dst=a.dst, base_gate=base_gate, gate=gate,
                       dry_run=bool(a.dry_run), charset=a.charset,
                       reserve_slots=bool(a.reserve_slots),
                       total_migrated=total, per_code=agg, per_container=per_tag,
                       reserved_pairs={ch: list(v) for ch, v in extra.items()},
                       preexisting_defects=[dict(tag=t, off=s, end=e, why=w)
                                            for (t, s, e, w) in (pre_all or [])],
                       elf_seen=[dict(va=hex(va), off=hex(off), word=hex(w), imm=hex(imm))
                                 for (va, off, w, imm) in elf_seen],
                       elf_patch=[dict(off=hex(off), from_=hex(imm), to=hex(_w & 0xFFFF))
                                  for (off, _w, imm, _w0) in elf_patch],
                       diff=diff, log=LOG),
                  f, ensure_ascii=False, indent=1)
    with io.open(os.path.join(out, 'migrate.log'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    return p


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
