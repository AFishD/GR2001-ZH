# -*- coding: utf-8 -*-
r"""dump_sf_titles_csv.py — 把「特别收录」的**条目标题** dump 成**可注入表** (round63)

═══════════════════════════════════════════════════════════════════════════════
这是什么 / 为什么需要它
═══════════════════════════════════════════════════════════════════════════════

「特别收录」里每一条 (条目/组/工作室) 的名字**不是** `<text>` 正文, 而是 XML 的
**属性**: `<item name="…">` / `<group name="…">` / `<studio name="…">`。

* `tools/text_csv/dump_text_csv.py` 只导出 `<text>…</text>` 元素 (`tcslib.TEXT_RE`)
  ⇒ **标题从来没进过任何可注入表**;
* `tools/text_csv/dump_containers.py` 的通用串扫描按设计只认 ASCII ⇒ 汉字标题一条
  都进不去 (round62 的报告 `docs/REPORT_sf_titles_dump.md` 有完整根因); 它新加的
  `<版本>_view_sf_titles.csv` 能**看**标题, 但那张表是 **view-only** (injectable=no,
  注入器会明确拒绝)。

**本脚本补上最后一环**: 产出一张**命名落在注入器扫描空间里**的表
(``<版本>_text_sf_titles.csv`` ⇒ `--csv <目录>` 会被自动读入), 表里每一行都能
唯一定位一个属性 (容器 + tag + entry_index + offset + len_bytes), 用户只改
`text_edited` 一列, 由 `tools/text_csv/inject_text_csv.py` 的**属性级写入通道**
回写到 `MENU.IMG#283`。

配套:
  · 注入器: `tools/text_csv/inject_text_csv.py` (round63 新增属性通道, 见其 `--help`)
  · 只读普查表: `<版本>_view_sf_titles.csv` (dump_containers.py, 10 份副本全列)
  · 等长原位重映射的历史做法: `tools/iso_build/patch_zh51_sfxml_titles.py`
  · 报告: `docs/REPORT_sf_titles_inject.md`

═══════════════════════════════════════════════════════════════════════════════
表结构 (17 列; 前 6 列是注入器的定位列, 名字与其它文本表一致)
═══════════════════════════════════════════════════════════════════════════════

  id, resource, container, entry_index, offset, len_bytes, max_bytes, kind, tag,
  attr, copy_role, lang, dup_count, text_en, text_zh, text_edited, note

  `id`           = ``SFXML:A####`` —— A = attribute (与 `<text>` 的 ``SFXML:T####`` 区分开;
                   两者**永不会撞 id**, 所以标题表和正文表可以同时给 `--csv`)。
                   #### = 本容器内第几个被列出的属性 (1-based, blob 顺序) = `entry_index`。
  `entry_index`  = ``A####``; 注入器**按它定位** (改字数后 offset 会漂移, 序号不会)。
  `offset`/`len_bytes` = 属性**值**在**解压后 blob** 里的字节偏移与长度 —— 注入时用作
                   与源盘对表的**硬校验** (对不上就拒绝, 见注入器 `--help`)。
  `max_bytes`    = `len_bytes` + 该容器 `</SpecialFeatures>` 之后的**陈旧尾巴**字节数
                   (现役盘 = 38238 B)。这是"单条能长到多少"的**宽松提示**, 真正的硬门禁
                   是: 内容不得超出解压 blob 总长、重压后的帧不得超出槽位 (`stored`)。
  `tag`/`attr`   = `item`/`group`/`studio` / 恒为 `name` (与源盘逐行核对, 不符即拒绝注入)。
  `text_en`      = **只读参考列**: 同一张盘上英文原样副本 (`GR.IMG#4058`) 里同序号的
                   英文原名 (按 entry_index 对齐, tag 序列必须完全一致)。
                   ★ 注入器读表后**立刻整列丢掉** (IGNORED_COLS), 写什么都不影响产物。
  `text_zh`      = 盘上现值 (注入器拿它判断"你有没有改过")。
  `text_edited`  = **人类改这一列**。留空/与 text_zh 相同 ⇒ 这一条不动。
  `note`         = 怎么改、有什么坑 (每行都写)。

★ 只列**注入目标** `MENU.IMG#283` (= `tcslib.RES['SFXML']['copies'][0]`) 的 145 个
  `name=` 属性 —— 含纯 ASCII 的 (如 `Music`), 便于与英文原名对照。
  引擎画标题读的就是这一份 (round51/79/84 实机结论); 另外 9 份副本
  (DE/ES/FR/IT 西文原码 + `GR.IMG#4058` 英文原样) **一个字节都不许动**,
  它们只出现在 view 表 `_view_sf_titles.csv` 里供比对。

═══════════════════════════════════════════════════════════════════════════════
用法
═══════════════════════════════════════════════════════════════════════════════

  # ① 标准姿势: 给 --out 与 dump_text_csv.py 同一个基准名 ⇒ 表落在版本目录 text/ 里
  python tools/text_csv/dump_sf_titles_csv.py --iso work/builds/GR_ZH110/GR_ZH110.iso \
         --out work/builds/GR_ZH110/text/GR_ZH110_text.csv
  #   ⇒ 写出 work/builds/GR_ZH110/text/GR_ZH110_text_sf_titles.csv (145 行)

  # ② 顺带出一份「待校对清单」(按 tag 分组 + 英文原文, 便于逐条核对错译)
  python tools/text_csv/dump_sf_titles_csv.py --iso <盘> --out <基准> \
         --checklist work/builds/GR_ZH98/temp/r63/GR_ZH110_sf_titles_checklist.csv

  # ③ 只看统计, 不写文件
  python tools/text_csv/dump_sf_titles_csv.py --iso <盘> --stats

  # ④ 改完表注入 (注入器自动扫 *_text_*.csv ⇒ 给目录最省事)
  python tools/text_csv/inject_text_csv.py --csv work/builds/GR_ZH110/text \
         --src work/builds/GR_ZH110/GR_ZH110.iso --dst <新盘> --check-only

退出码: 0 正常 / 1 自证失败或往返不可逆 (拒绝写出表) / 2 参数错

★ 铁律: 本脚本**只读** ISO, 只写 CSV/JSON —— 不写任何 ISO / 字符集 / 字库。
"""
import argparse
import collections
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
try:
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:                                                       # noqa: BLE001
    pass

import tcslib as T                                                      # noqa: E402
import dump_containers as DC                                            # noqa: E402  (副本识别/属性正则: 同一口径)
import font_usage as FU                                                 # noqa: E402  (容器枚举/解压: 只 import, 不改)
import dump_text_csv as DT                                              # noqa: E402  (CSV 写出/不可见字符门槛: 复用)

FMT = 'text-csv/4'                     # 与注入器的表格式同一代
ATTR_KIND = 'sf_titles'                # kind 列的值 (注入器按它/按 id 识别属性行)
ID_FMT = 'SFXML:A%04d'
ENTRY_FMT = 'A%04d'

COLS = ['id', 'resource', 'container', 'entry_index', 'offset', 'len_bytes',
        'max_bytes', 'kind', 'tag', 'attr', 'copy_role', 'lang', 'dup_count',
        'text_en', 'text_zh', 'text_edited', 'note']
QUOTE = {'text_en', 'text_zh', 'text_edited', 'note'}
CELL_COLS = ('text_en', 'text_zh', 'text_edited', 'note')
CHECK_COLS = ['grp', 'order', 'id', 'entry_index', 'tag', 'offset', 'len_bytes',
              'text_zh', 'text_en', 'text_edited', 'dup_count', 'flag', 'note']
CHECK_QUOTE = {'text_zh', 'text_en', 'text_edited', 'note'}

# 标题画在固定栏宽里 (见 docs/REPORT_16px.md / REPORT_zh82t_title_center.md):
# 超过这个字数就有可能顶到栏边 —— 只**告警**, 不阻断 (版式必须实机验)。
LONG_WARN_CHARS = 14

NOTE_HEAD = (
    '★ 这是「特别收录」的**条目标题** (XML 属性 <{tag} name="…">, 不是 <text> 正文)。'
    '只改 **text_edited** 一列; text_zh 是盘上现值 (用来判断你有没有改过), '
    'text_en 是英文原名 (只读参考, 注入器整列丢掉)。'
)
NOTE_TAIL = (
    '★ 改字数**可以** (标题变长/变短都行): 注入器重压 SFXML 时把增长吃进 '
    '`</SpecialFeatures>` 之后的陈旧尾巴 (现役盘 %d B), 内容超出 blob 总长 或 '
    '重压后帧超出槽位 %d B 就**中止** (不截断、不静默丢字)。'
    '★ 每个字都必须在盘上字符集里**且盘上有字形**, 否则注入器会拦下并告诉你缺哪个字。'
    '★ 标题栏宽度固定 ⇒ 改长/改短都要**实机看版式** (可能溢出或被截断)。'
)


def rel(p):
    try:
        r = os.path.relpath(p, REPO)
    except ValueError:
        return p.replace('\\', '/')
    return r.replace('\\', '/') if not r.startswith('..') else p.replace('\\', '/')


def attr_list(blob):
    """按 blob 顺序列出 ``<studio|item|group … name="…">`` ⇒ ``[(idx, tag, off, val)]``。

    与 round62 的 view 表**完全同一口径** (同一批正则, 同样是 blob 顺序),
    所以本表的 `entry_index` 与 `_view_sf_titles.csv` 的 `entry_index` 一一对应。
    """
    out = []
    for m in DC.SFXML_TAG_RE.finditer(blob):
        tag = m.group(1).decode('latin-1')
        for am in DC.SFXML_ATTR_RE.finditer(m.group(2)):
            key = am.group(1).decode('latin-1')
            if key != DC.SFXML_TITLE_ATTR or tag.lower() not in DC.SFXML_TITLE_TAGS:
                continue
            val = am.group(2)
            out.append((len(out) + 1, tag, m.start(2) + am.start(2), val))
    return out


def nonascii_attrs(blob):
    """(全部含非 ASCII 的属性数, 其中名字是 name= 的个数) —— 覆盖自证用。"""
    n_all = n_named = 0
    for m in DC.SFXML_TAG_RE.finditer(blob):
        for am in DC.SFXML_ATTR_RE.finditer(m.group(2)):
            if DC.NONASCII_BYTE_RE.search(am.group(2)):
                n_all += 1
                if (m.group(1).decode('latin-1').lower() in DC.SFXML_TITLE_TAGS
                        and am.group(1).decode('latin-1') == DC.SFXML_TITLE_ATTR):
                    n_named += 1
    return n_all, n_named


def main():
    ap = argparse.ArgumentParser(
        description='dump「特别收录」条目标题 (SFXML 的 name= 属性) → **可注入表** '
                    '<版本>_text_sf_titles.csv (只列注入目标 MENU.IMG#283 的 145 条)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='示例:\n'
               '  python tools/text_csv/dump_sf_titles_csv.py --iso work/builds/GR_ZH110/'
               'GR_ZH110.iso --out work/builds/GR_ZH110/text/GR_ZH110_text.csv\n'
               '  python tools/text_csv/dump_sf_titles_csv.py --iso <盘> --stats\n'
               '  python tools/text_csv/dump_sf_titles_csv.py --iso <盘> --out <基准> '
               '--checklist <清单.csv>\n'
               '\n改完怎么注入:\n'
               '  python tools/text_csv/inject_text_csv.py --csv <本表> --src <盘> '
               '--dst <新盘> --check-only\n'
               '  (给目录更省事: --csv <版本>/text 会把该目录下所有 *_text_*.csv 一起读入)')
    ap.add_argument('--iso', required=True, help='要 dump 的 ISO (只读, 不会被修改)')
    ap.add_argument('--out', default=None, metavar='基准路径',
                    help='与 dump_text_csv.py 同一个基准名 (如 …/GR_ZH110_text.csv) ⇒ '
                         '写出 …/GR_ZH110_text_sf_titles.csv。缺省 = <ISO 同目录>/text/'
                         '<版本>_text.csv')
    ap.add_argument('--out-dir', default=None, help='直接指定输出目录 (配 --prefix)')
    ap.add_argument('--prefix', default=None, help='输出文件名前缀 (缺省 = <版本>)')
    ap.add_argument('--checklist', default=None, metavar='清单.csv',
                    help='★ 顺带导出「待校对清单」: 按 tag (studio/group/item) 分组、'
                         '带英文原文与 原/新 两列, 供人工逐条核对错译')
    ap.add_argument('--stats', action='store_true', help='只打印统计, 不写任何文件')
    ap.add_argument('--json', default=None, metavar='报告.json',
                    help='把本表的统计/自证结果写成 JSON (含容器余量数字)')
    ap.add_argument('--allow-roundtrip-diff', action='store_true',
                    help='★ 工程侧: 往返自检不通过时也写出表 (那些行不可安全编辑)')
    a = ap.parse_args()

    iso_sha = T.sha256_file(a.iso)
    iso = T.Iso(a.iso)
    cs = T.Charset()
    print('# dump_sf_titles_csv.py — 特别收录条目标题 (SFXML 的 name= 属性) → 可注入表')
    print('# ISO     : %s' % iso.path)
    print('# sha256  : %s' % iso_sha)
    print('# charset : %s (%d 单字节码 + %d 对偶码)'
          % (rel(T.CHARSET), len(cs.enc_single), len(cs.enc_pair)))

    # ── 找全部 *_SPECIAL_FEATURE.XML 副本 (与 round62 同一口径: 只按文件名认) ──
    conts = FU.build_container_list(iso)
    copies = DC.sfxml_copies_of(conts)
    if not copies:
        print('!! 一个 *_SPECIAL_FEATURE.XML 副本都没找到 —— 这张盘不对?')
        iso.close()
        sys.exit(1)
    target = [c for c in copies if c['role'] == 'zh-main']
    if len(target) != 1:
        print('!! 注入目标 (copy_role=zh-main) 不是唯一一份: %d 份 ⇒ 拒绝' % len(target))
        iso.close()
        sys.exit(1)
    tgt = target[0]
    print('\n== 副本清单 (共 %d 份) ==' % len(copies))
    print('# %-4s %-38s %-4s %-9s %10s %9s' %
          ('#', '容器', '语言', '角色', 'stored B', 'blob B'))
    for c in copies:
        print('# %-4d %-38s %-4s %-9s %10d %9d%s'
              % (c['copy_index'], DC.cont_name(c['c']), c['lang'], c['role'],
                 c['c']['stored'], len(FU.container_blob(iso, c['c'])[0]),
                 '  ← 注入目标 (copies[0], 本表只列这一份)' if c['role'] == 'zh-main' else ''))

    blob, _raw = FU.container_blob(iso, tgt['c'])
    used_end = T.xml_tail_start(blob)
    tail_free = len(blob) - used_end
    attrs = attr_list(blob)
    n_non, n_non_named = nonascii_attrs(blob)
    print('\n== 注入目标 %s ==' % DC.cont_name(tgt['c']))
    print('# 槽 stored   = %d B   (重压后的帧必须 <= 它)' % tgt['c']['stored'])
    print('# 解压 blob   = %d B   </SpecialFeatures> 有效结束 @%d' % (len(blob), used_end))
    print('# 陈旧尾巴    = %d B   (标题"改长"就吃这一块)' % tail_free)
    print('# name 属性   = %d 个 (本表逐条列出; 含纯 ASCII 的)' % len(attrs))
    print('# <text> 元素 = %d 个 (在 *_text_long/short.csv 里, 不在本表)'
          % len(T.TEXT_RE.findall(blob)))

    # ── 英文原名 (同盘 EN 原样副本, 按 entry_index 对齐) ──
    en_copies = [c for c in copies if c['lang'] == 'EN' and c['role'] != 'zh-main']
    en_text, en_note = {}, ''
    if en_copies:
        ec = en_copies[0]
        eblob, _r = FU.container_blob(iso, ec['c'])
        eattrs = attr_list(eblob)
        if [x[1] for x in eattrs] == [x[1] for x in attrs]:
            en_text = dict((x[0], cs.decode(x[3])[0]) for x in eattrs)
            en_note = DC.cont_name(ec['c'])
            print('# 英文原名    = 取自 %s (%d 条, tag 序列与注入目标**逐行一致** ✓)'
                  % (en_note, len(eattrs)))
        else:
            print('!! 英文副本 %s 的 tag 序列与注入目标不一致 ⇒ 不做对齐, text_en 留空'
                  % DC.cont_name(ec['c']))
    else:
        print('!! 没找到 EN 原样副本 ⇒ text_en 留空')

    # ── 逐条自证 ──
    # ── ★ 各语言副本里**逐字节相同**的属性 = **结构名** (不是给人看的文案) ──
    #   实测: studio 那一档 (`ConceptSketches`/`Background`/`Music`/`Weapon`/`Movies`/
    #   `GameTrailer`/`Awards`/`SpecialistProfile`/`BackStory`/`Interview`) 在 EN/DE/ES/FR/IT
    #   五份副本里**逐字节相同** ⇒ 它们更像菜单用来**找条目**的名字 (结构键), 不是本地化文案
    #   (同一批数据里, 真正给人看的 item/group 名字五份都是各语言自己的写法)。
    #   ★ 因而不建议汉化 studio 档 —— 菜单可能靠它找条目。表里逐行注明。
    _vals = {}
    for cp in copies:
        bi, _r = FU.container_blob(iso, cp['c'])
        for (k, _t, _o, v) in attr_list(bi):
            _vals.setdefault(k, set()).add(v)
    same_in_all = dict((k, next(iter(s))) for k, s in _vals.items() if len(s) == 1)
    rt_bad = []
    note = NOTE_HEAD.format(tag='{tag}')          # 每行的 {tag} 在下面替换
    note_tail = NOTE_TAIL % (tail_free, tgt['c']['stored'])
    rows = []
    dup = collections.Counter(cs.decode(x[3])[0] for x in attrs)
    for (k, tag, off, val) in attrs:
        if blob[off:off + len(val)] != val:
            raise SystemExit('!! 属性偏移自证失败: 第 %d 个 (%s) @%d 回读不上' % (k, tag, off))
        text = cs.decode(val)[0]
        if T.pua_to_marks(text) != text:          # 含按键图标占位 ⇒ 已经过 pua_to_marks
            pass
        text_disp = T.pua_to_marks(text)
        try:
            rt_ok = (cs.encode_strict(text) == val)
        except T.CharsetError:
            rt_ok = False
        if not rt_ok:
            rt_bad.append(k)
        full = (note.replace('{tag}', tag) + note_tail
                + ('  ★ 该条原文含手柄按键图标占位, 请原样保留 {{BTN:XXXX}}。'
                   if 0xE000 <= max([ord(c) for c in text] or [0]) <= 0xE0FF else ''))
        if tag.lower() == 'studio' and same_in_all.get(k) == val:
            full += ('  ★★ **这是 studio 档的结构名** (五份语言副本 EN/DE/ES/FR/IT 里'
                     '逐字节相同 ⇒ 更像菜单用来找条目的键, 不是给人看的文案): '
                     '**建议不要改**; 确要改请先实机确认菜单还能进得去。')
        rows.append(dict(
            id=ID_FMT % k, resource='SFXML', container=DC.cont_name(tgt['c']),
            entry_index=ENTRY_FMT % k, offset=off, len_bytes=len(val),
            max_bytes=len(val) + tail_free, kind=ATTR_KIND, tag=tag,
            attr=DC.SFXML_TITLE_ATTR, copy_role=tgt['role'], lang=tgt['lang'],
            dup_count=dup[text], text_en=en_text.get(k, ''), text_zh=text_disp,
            text_edited=text_disp, note=full))
    print('\n== 自证 ==')
    print('# 属性偏移回读      : %d/%d 条逐字节命中 ✓' % (len(attrs), len(attrs)))
    print('# 含非 ASCII 属性   : %d 个 ⇒ 全部落在 name= 上有 %d 个 %s'
          % (n_non, n_non_named, '✓' if n_non == n_non_named else '✗ (有属性没被本表覆盖!)'))
    if n_non != n_non_named:
        iso.close()
        raise SystemExit('!! 覆盖自证失败: 有含非 ASCII 的属性不是 name= --- 本表漏了东西')
    print('# 往返(现值→字节)   : %d/%d 条可逐字节还原 %s'
          % (len(attrs) - len(rt_bad), len(attrs), '✓' if not rt_bad else '✗ %s' % rt_bad[:5]))
    if rt_bad and not a.allow_roundtrip_diff:
        iso.close()
        raise SystemExit('!! 往返自检不通过 (%d 条) —— 拒绝写出可注入表; '
                         '确要导出加 --allow-roundtrip-diff' % len(rt_bad))
    DT.assert_cells_clean(rows, CELL_COLS)
    print('# 不可见字符        : 已扫描 %d 行的 %s 列 —— 0 处 ✓' % (len(rows), ','.join(CELL_COLS)))

    en_blob = None
    # ── ★ 各语言副本里**逐字节相同**的属性 = **结构名** (不是给人看的文案) ──
    #   实测: studio 那一档 (`ConceptSketches`/`Background`/`Music`/`Weapon`/`Movies`/
    #   `GameTrailer`/`Awards`/`SpecialistProfile`/`BackStory`/`Interview`) 在 EN/DE/ES/FR/IT
    #   五份副本里**逐字节相同** ⇒ 它们更像菜单用来**找条目**的名字 (结构键), 不是本地化文案。
    #   汉化它们既可能没有意义 (菜单不显示), 又可能让菜单找不到条目 ⇒ 清单里明确标注。
    _vals = {}
    for cp in copies:
        bi, _r = FU.container_blob(iso, cp['c'])
        for (k, _t, _o, v) in attr_list(bi):
            _vals.setdefault(k, set()).add(v)
    same_in_all = dict((k, next(iter(s))) for k, s in _vals.items() if len(s) == 1)
    # ── 「待校对清单」 ──
    if a.checklist:
        grp_order = {'studio': 0, 'group': 1, 'item': 2}
        crows = []
        for r in sorted(rows, key=lambda x: (grp_order.get(x['tag'], 9), x['offset'])):
            zh, en = r['text_zh'], r['text_en'] or ''
            k = int(r['entry_index'][1:])
            flag = []
            if not zh:
                flag.append('空标题')
            if not en:
                flag.append('无英文对照')
            if len(zh) > LONG_WARN_CHARS:
                flag.append('偏长(%d 字, 栏宽有限)' % len(zh))
            if zh and DC.cjk_run(zh) == 0:
                try:
                    _same = (same_in_all.get(k) == cs.encode_strict(zh))
                except T.CharsetError:
                    _same = False
                if _same and r['tag'] == 'studio':
                    flag.append('★结构名 (studio 档, 五份语言副本逐字节相同 ⇒ 菜单靠它找条目, '
                                '**建议不要译**)')
                elif _same:
                    flag.append('型号/代号 (五份语言副本相同: M16/M203、OICW、XIII 这类'
                                '本来就不译; 若要译请实机确认)')
                else:
                    flag.append('未译(全 ASCII)')
            crows.append(dict(
                grp=r['tag'], order='%s#%s' % (r['tag'], r['entry_index'][1:]), id=r['id'],
                entry_index=r['entry_index'], tag=r['tag'], offset=r['offset'],
                len_bytes=r['len_bytes'], text_zh=zh, text_en=en,
                text_edited=r['text_edited'], dup_count=r['dup_count'],
                flag=('; '.join(flag) if flag else ''),
                note=('盘上现值 = text_zh。要改就写在 **text_edited** 列 (留空 = 不改), '
                      '然后把这张表当普通文本表注入: 改完把 text_edited 贴回 '
                      '%s 的 text_edited 列 (或直接注入本清单所在目录里那张 *_text_sf_titles.csv)。'
                      '英文原名见 text_en (来自 %s)。' % ('<版本>_text_sf_titles.csv',
                                                          en_note or '(无)'))))
        DT.assert_cells_clean(crows, CELL_COLS)
        d = os.path.dirname(os.path.abspath(a.checklist))
        if d:
            os.makedirs(d, exist_ok=True)
        DC.write_csv(a.checklist, crows, CHECK_COLS, CHECK_QUOTE)
        n_flag = sum(1 for c in crows if c['flag'])
        print('\n== 待校对清单 ==')
        print('# 按 tag 分组 (studio → group → item), 同组按盘上顺序')
        for g in ('studio', 'group', 'item'):
            n = sum(1 for c in crows if c['grp'] == g)
            print('#   %-7s %3d 条' % (g, n))
        print('# 带标记的 %d 条 (空标题/无英文对照/偏长/全 ASCII=未译)' % n_flag)
        print('# → %s (%d 行)' % (rel(a.checklist), len(crows)))

    if a.stats:
        iso.close()
        return

    # ── 输出路径 (与 dump_text_csv.py 同一套规则) ──
    base = None
    if a.out:
        base = T.csv_stem(a.out)
    elif a.out_dir:
        base = os.path.join(a.out_dir, '%s_text' % (a.prefix or
                                                    os.path.splitext(os.path.basename(a.iso))[0]))
    else:
        ver = os.path.splitext(os.path.basename(a.iso))[0]
        base = os.path.join(os.path.dirname(os.path.abspath(a.iso)), 'text', '%s_text' % ver)
    base = os.path.abspath(base)
    path = T.table_path_for(base, ATTR_KIND)         # <base>_sf_titles.csv
    if '_view_' in os.path.basename(path):
        raise SystemExit('!! 命名隔离断言失败: 可注入表不许带 _view_: %s' % path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    DC.write_csv(path, rows, COLS, QUOTE)
    n_edit = sum(1 for r in rows if r['text_edited'] != r['text_zh'])
    print('\n== 写出可注入表 ==')
    print('# %-42s %4d 行  %7.1f KB  (kind=%s, resource=SFXML)'
          % (rel(path), len(rows), os.path.getsize(path) / 1024.0, ATTR_KIND))
    print('# 其中 text_edited != text_zh 的行: %d (新 dump 应为 0)' % n_edit)
    print('# id 形如 SFXML:A0116 (与正文表 SFXML:T0010 **不会撞 id**) ⇒ '
          '标题表和正文表可以一起给 --csv')

    rep = dict(format=FMT, tool='tools/text_csv/dump_sf_titles_csv.py',
               generated=datetime.datetime.now().isoformat(timespec='seconds'),
               iso=rel(a.iso), iso_sha256=iso_sha,
               charset=rel(T.CHARSET), table=rel(path), columns=COLS,
               rows=len(rows), copies=len(copies),
               inject_target=DC.cont_name(tgt['c']),
               copies_detail=[dict(copy_index=c['copy_index'], container=DC.cont_name(c['c']),
                                   lang=c['lang'], role=c['role'], kind=c['kind'])
                              for c in copies],
               container=dict(tag=DC.cont_name(tgt['c']), stored=tgt['c']['stored'],
                              blob_bytes=len(blob), used_end=used_end,
                              tail_free_bytes=tail_free,
                              substreams=_sub_sizes(iso, tgt['c'])),
               text_elements=len(T.TEXT_RE.findall(blob)),
               attrs_total=len(attrs), attrs_nonascii=n_non,
               roundtrip_failed=rt_bad,
               en_reference=en_note or None,
               ids=dict(first=rows[0]['id'], last=rows[-1]['id'],
                        note='SFXML:A#### 与正文表 SFXML:T#### 不会撞 id'),
               policy=('本表是**可注入表**: 只改 text_edited 一列; 注入器按 '
                       'entry_index (A####) 定位属性, 用 offset/len_bytes 与源盘对表, '
                       '并用 tag 列复核; 改字数由陈旧尾巴吸收 (超出即中止, 不截断)'))
    if a.json:
        d = os.path.dirname(os.path.abspath(a.json))
        if d:
            os.makedirs(d, exist_ok=True)
        json.dump(rep, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('# [报告] %s' % rel(a.json))

    print('\n下一步 (改错译的标准姿势):')
    print('  ① 用 Excel 打开上面那张表, 只改 **text_edited** 一列 (对照 text_en 英文原名);')
    print('  ② 先干跑一次预检 (不写盘, 缺字会直接告诉你缺哪个字):')
    print('     python tools/text_csv/inject_text_csv.py --csv %s \\' % rel(path))
    print('            --src %s --check-only' % rel(a.iso))
    print('  ③ 预检过了再真注入 (给 text/ 目录 ⇒ 标题表和正文表一起读):')
    print('     python tools/text_csv/inject_text_csv.py --csv %s \\'
          % rel(os.path.dirname(path)))
    print('            --src %s --dst <新盘.iso>' % rel(a.iso))
    print('  ★ 标题栏宽度固定 ⇒ 改完必须**实机**看版式 (见 docs/REPORT_sf_titles_inject.md)')
    iso.close()
    return 0


def _sub_sizes(iso, c):
    """该条目的 LZO 子流尺寸表 (给人看容器结构; 只读)。"""
    e = iso.img_entry(c['lba'], c['idx'])
    raw = iso.read(e['iso_off'], e['stored'])
    return [s[2] for s in T.lzo_subs(raw)]


if __name__ == '__main__':
    sys.exit(main())
