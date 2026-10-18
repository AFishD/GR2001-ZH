# -*- coding: utf-8 -*-
r"""dump_containers.py — 全容器文本普查 (round39): 把**全盘所有容器**里的文本扫出来,
按「容器类型 × 文本形态」自动分类成多张 **view-only(只能看/校对, 不能注入)** 的 CSV。

═══════════════════════════════════════════════════════════════════════════════
为什么要有这个工具 (和 dump_text_csv.py 的分工)
═══════════════════════════════════════════════════════════════════════════════

  dump_text_csv.py  只管**两类**资源 (引擎真正会画到屏幕上的游戏文本):
      LANG  = EN_STRINGS.RES 语言表      → <版本>_text_long / _long_nowrap / _short.csv
      SFXML = EN_SPECIAL_FEATURE.XML     → 同上三张表的一部分
    这三张表**格式被完全理解、能逐字节往返** ⇒ 标 **injectable=yes**, 改完能注入回盘。

  dump_containers.py (本文件) 把**其余全部 4700+ 个容器**也扫一遍, 让用户
  「一张表看全游戏里所有文本」, 但**一律标 view-only**:
      .ATR 人物/队伍定义 (其实是 XML 文本)   .MIS 任务数据 (其实是 XML 文本)
      .XML 其它配置     .TXT 纯文本     .RES 其它语言表/资源表
      ELF 主程序字符串  其它 ISO 文件
      .RSB/.PAK/.SHT/.PSS/.SS/.TM/... 等二进制容器里的可读串
  ⇒ **不是为了注入** (这些格式没被逆向, 写回去会毁盘), 而是为了:
      ① 校对时能查到「这个名字在别处怎么写的」;
      ② 确认全盘到底有没有别的地方藏着中文;
      ③ 给未来的逆向留一份**有据可查**的清单。

═══════════════════════════════════════════════════════════════════════════════
★ 安全红线: view-only 的表**绝不允许**被注入器吃进去
═══════════════════════════════════════════════════════════════════════════════

  1. 命名隔离: view 表叫 ``<版本>_view_<类别>.csv``, **不叫** ``*_text_*.csv``
     ⇒ 注入器 ``--csv <目录>`` 自动扫描的是 ``*_text_*.csv``, 天然扫不到它们。
  2. 显式拒绝: 万一有人把 view 表直接喂给注入器 (``--csv x_view_xml.csv``),
     inject_text_csv.py 会**认出来并报错退出 (退出码 1), 一个字都不写盘**。
     本模块写盘时也会硬断言文件名不含 ``_text_``, 且表头带 ``injectable`` 列
     (值恒为 ``no``) —— 双保险。
  3. 表内自述: 每一行的 ``injectable`` 列都是 ``no``, ``note`` 列写清"为什么不能改"。

═══════════════════════════════════════════════════════════════════════════════
★ 分类方案 (8 个类别 = 表名后缀)
═══════════════════════════════════════════════════════════════════════════════

  cat                     容器 kind            为什么单独一类
  ----------------------  ------------------  --------------------------------------
  xml                     其它 .XML           结构化 XML, 高覆盖
  sf_titles               (按文件名专项)      ★ round62 新增: SFXML 的 XML **属性值**
                                              (= 特别收录的条目标题/组名/工作室名)
  txt                     .TXT                纯文本清单
  missions                .MIS                任务/简报数据 (实为 XML 文本)
  character_names         .ATR                人物/队伍定义 (实为 XML 文本)
  other_res               .RES                德/西/法/意语言表 + FONT/IKE 资源表
  program_strings         ELF (SLUS_206.13)   主程序里的调试串/带符号名
  iso_files               ISO 里的独立文件      SYSTEM.CNF / *.IRX / IOPRP*.IMG ...
  binary_assets           RSB/PAK/MEDIA/OTHER 贴图/打包/视频音频/其它二进制

  (LANG 与 SFXML 不在这里重复 dump —— 它们由 dump_text_csv.py 产出可注入的
   ``*_text_*.csv``; 本工具的 ``_view_containers_summary.csv`` 会指路。
   ★ 例外: SFXML 的**属性**不在可注入表里, 所以 round62 起由本工具的
   ``_view_sf_titles.csv`` 专门列出, 见下一节。)

═══════════════════════════════════════════════════════════════════════════════
★ round62: 为什么必须单列一张 ``_view_sf_titles.csv`` (用户报告: "标题搜不到")
═══════════════════════════════════════════════════════════════════════════════

  「特别收录」的**条目名 / 组名 / 工作室名**存在 ``EN_SPECIAL_FEATURE.XML`` 的
  ``<item name="…">`` / ``<group name="…">`` / ``<studio name="…">`` **属性**里,
  **不是** ``<text>`` 正文。而:

    · dump_text_csv.py 只导出 ``<text>…</text>`` 元素 (TEXT_RE) ⇒ 标题从来没进过
      任何 ``*_text_*.csv``（可注入表）;
    · 本工具的**通用串扫描**也看不见它们: 第 2 关「像文本」判据里的可见字符表
      (OKVIS_RE) 与字母数字表 (WORD_RE) **只含 ASCII** ⇒ 一个"以汉字为主"的串
      (如 ``国会最高勋章``) 必然被判成"不像文本"而丢掉。

  ⇒ 实测 (现役盘 GR_ZH109, 全部可复现; 见 docs/REPORT_sf_titles_dump.md):
    注入目标 MENU.IMG#283 里有 **123 个**含中文的 ``name=`` 属性 (= **93 个不同标题串**,
    有些标题在 group 与 item 下各写一遍)。改动前的**全部 13 张 CSV**:
      · 按出现次数: 只有 **28/123** 能搜到 (= 标题**恰好**也在某篇 ``<text>`` 正文里出现过);
      · 按不同串:   只有 **27/93**, 其余 **66 个标题一个字都搜不到** —— 用户报的就是这个。

  所以本工具新增一个**专项通道**: 凡是文件名以 ``_SPECIAL_FEATURE.XML`` 结尾的容器
  (现役盘共 10 份 = EN/DE/ES/FR/IT × MENU/GR 两侧), 都把

    ① ``<item|group|studio>`` 的 ``name=`` 属性 (**全部**, 含纯 ASCII 的英文标题), 与
    ② **任何**标签上**含非 ASCII 字节**的属性值 (兜底: 万一别处也有中文属性)

  逐条列进 ``<版本>_view_sf_titles.csv`` —— 带**容器 + 字节偏移**, 可定位、可按 text 搜索。
  ★ 它仍然是 **view-only**: 属性不在任何可注入表里, 格式也没走到"逐字节往返"那一层;
  想真改标题请看报告 `docs/REPORT_sf_titles_dump.md` 的「可注入性」一节
  (round51 的 `tools/iso_build/patch_zh51_sfxml_titles.py` 是**等长原位重映射**的现成做法)。

  ★ 与 ``_view_xml.csv`` 的关系: 那 8 份**非注入目标**的副本 (kind=XML) 也会被通用扫描
  再过一遍, 但受上面第 2 条限制, **汉字为主的串一条都进不去** ⇒ 想找标题只看
  ``_view_sf_titles.csv``; ``_view_xml.csv`` 的列结构与内容**保持原样不动** (下游有工具读)。

═══════════════════════════════════════════════════════════════════════════════
★ 文本判据 (全部可复现; 阈值写进 meta.json 与报告)
═══════════════════════════════════════════════════════════════════════════════

  第 1 关 「可读串」   连续 >= min_run 个字节都落在扫描字母表 (ASCII 可打印 +
                       本盘字符集的单字节码/对偶 lead/trail + 按键字节) 里。
                       min_run: 结构化容器 6 B, 二进制容器 8 B。
  第 2 关 「像文本」   ① 全是 ASCII 可打印 ⇒ 字母数字占比 >= 0.70;
                       ② 含高位字节 ⇒ 用**本盘字符集单字节优先**解码后:
                          可见字符占比 >= 0.85 且 字母数字占比 >= 0.55 且 至少要有一个汉字;
                       ③ 无私有区回落字符 (有 ⇒ 那是未映射字节, 不是文本);
                       ④ 同一字符连续重复 <= 8; ⑤ 长度 >= 16 时至少要有一个标点/空格;
                       ⑥ 没有长度 4 的子串在同一个串里出现两次 (压缩数据/贴图噪声的典型特征)。
  第 3 关 「容器级闸门」(只对高风险二进制类 RSB/PAK/MEDIA/OTHER 生效)
       一个容器要整体放行, 必须同时满足:
           ① distinct     >= min_distinct    (默认 10)      —— 去重后不同串数;
           ② score        >= min_text_score  (默认 10.0 /MB) —— 不同串数 / 解压后 MB;
           ③ clean_ratio  >= min_clean_ratio (默认 0.002)  **或**
              text_ratio   >= min_text_ratio  (默认 0.15):
                clean_ratio = 「纯 ASCII 且无空白的干净串」总字节 / 容器字节
                              —— 真文本容器这一项远高于压缩噪声;
                text_ratio  = 去重串里「像文本」的占比: 含「词(>=3 字母) 空格 词」
                              或「连续 2 个汉字」, 或 长度>=6 且字母数字占比>=0.70 的词形串。
       不满足 ⇒ **一条都不 dump**, 只在 ``_view_pending.csv`` 里留一行判定依据。
       ★ 阈值依据 (现役盘实测, 全部可复现; 详见 docs/REPORT_dump_all_containers.md):
         · 纯随机数据 1 / 4 / 16 MB 在**第 1~2 关全开**下的 score 只有 1.0 / 0.2 / 0.6 /MB;
         · 压缩/流式容器: PSS 视频流 (ZZZ.PSS 143 MB) clean_ratio 0.000002 / score 14.6;
           MUSIC.TM (50 MB) 0.0004; BNK_*.SS 0.0009; 压缩贴图 .BMZ 0.003~0.008;
         · 真文本容器: .MIS clean_ratio 0.0047 text_ratio 1.00; 名字表 .DIR 0.94;
           .TXT 0.31; .RES 1398 串/MB; .XML 0.92。
       ★ 为什么**不**用「容器里出现了汉字」当判据: 本盘字符集有 1319 个对偶码,
         一个字节落在 0xA1..0xAD 时约 28% 概率撞上真对偶 ⇒ 压缩数据里"解出汉字"
         是**噪声巧合**。实测: 中文盘与英文原盘逐容器做命中集合减法, 除 LANG/SFXML/ELF 外
         **一个新字都不剩** (4713 个容器里 4700 个命中集合逐元素相同)。
         所以 view 表里二进制容器的「汉字」行**不是翻译残留**, 是本工具标注的噪声证据。

  第 4 关 「每容器上限」 默认 2000 条去重串 (超了截断并在 meta 里记数) ——
                       典型值: .ATR 中位 2 条、.MIS 中位 24 条、.RSB 中位 18 条。

═══════════════════════════════════════════════════════════════════════════════
用法
═══════════════════════════════════════════════════════════════════════════════

  # ① 默认: 写到 <ISO 同目录>/text/<版本>_view_*.csv
  python tools/text_csv/dump_containers.py --iso work/builds/GR_ZH92/GR_ZH92.iso

  # ② 跟 dump_text_csv.py 同一个基准名 (构筑器就是这么调的)
  python tools/text_csv/dump_containers.py --iso <盘> \
         --out-base work/builds/GR_ZH92/text/GR_ZH92_text.csv

  # ③ 只看统计, 不写文件
  python tools/text_csv/dump_containers.py --iso <盘> --stats

  # ④ 放宽闸门 (想连噪声一起看的时候)
  python tools/text_csv/dump_containers.py --iso <盘> --no-gate

退出码: 0 正常 / 2 参数错 / 3 覆盖自证不一致 (容器数与 font_usage.py 对不上)

★ 铁律: 本脚本**只读** ISO。它不写任何 ISO / 字符集 / 字库图集, 只写 CSV/JSON。
"""
import argparse
import collections
import csv
import datetime
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T                                                # noqa: E402
import font_usage as FU                                           # noqa: E402  (只 import, 不改)

FMT_VIEW = 'text-csv/view/1'
VIEW_MARK = '_view_'                       # ★ 与注入器自动扫描的 '_text_' 命名空间**互相排斥**

# ─────────────────────────── 类别定义 ───────────────────────────
#   cat -> dict(order, title, kinds, risk, injectable, note)
CATEGORIES = [
    dict(cat='xml', order=10, title='其它 XML 配置', kinds=('XML',), risk=False,
         note='结构化 XML; 本工具只做可读串扫描, 未解析元素结构 ⇒ 不改'),
    # ★ round62: SFXML 的 XML **属性**专项 (条目标题/组名/工作室名) —— 按文件名走专项通道,
    #   与 kind 无关 (注入目标 kind=SFXML; 其余语言副本 kind=XML)。
    dict(cat='sf_titles', order=15,
         title='特别收录 条目标题/组名 (SFXML 的 name= 属性)', kinds=(),
         kind_label='SFXML 属性', risk=False,
         note='★ 引擎会画到屏幕上的「特别收录」条目名/组名/工作室名 —— 它们在 '
              'EN_SPECIAL_FEATURE.XML 的 <item|group|studio name="…"> **属性**里, '
              '不是 <text> 正文。dump_text_csv.py 只导出 <text> ⇒ 标题从来没进过任何'
              '可注入表; 本工具的通用串扫描也看不见(判据只认 ASCII) ⇒ round62 单列本表。'
              '覆盖**全部副本**, 每行带容器 + 字节偏移 ⇒ 可按 text 搜索/定位。'),
    dict(cat='txt', order=20, title='纯文本 .TXT', kinds=('TXT',), risk=False,
         note='纯文本清单; 未确认引擎读取口径与校验 ⇒ 不改'),
    dict(cat='missions', order=30, title='任务数据 .MIS', kinds=('MIS',), risk=False,
         note='任务/简报数据 (内容实为 XML 文本); 未逆向任务结构 ⇒ 不改'),
    dict(cat='character_names', order=40, title='人物/队伍定义 .ATR',
         kinds=('ATR',), risk=False,
         note='人物/队伍定义 (内容实为 XML 文本, 人名全英文); 未逆向 ⇒ 不改'),
    dict(cat='other_res', order=50, title='其它 .RES 资源表', kinds=('RES',), risk=False,
         note='德/西/法/意语言表 + FONT/IKE 资源表; 非引擎当前读取的那两份 ⇒ 不改'),
    dict(cat='program_strings', order=60, title='主程序字符串 (ELF)', kinds=('ELF',),
         risk=False, note='主程序里的调试串/C++ 带符号名; 改它 = 改代码 ⇒ 绝不改'),
    dict(cat='iso_files', order=70, title='ISO 独立文件',
         kinds=('ISO_FILE',), risk=False,
         note='SYSTEM.CNF / *.IRX / IOPRP*.IMG 等 ISO 独立文件; 未逆向 ⇒ 不改'),
    dict(cat='binary_assets', order=80, title='二进制容器里的可读串',
         kinds=('RSB', 'PAK', 'MEDIA', 'OTHER'), risk=True,
         note='贴图/打包/精灵图/其它二进制容器; 不过容器级闸门就一条都不 dump '
              '(视频音频流单独排除, 见 pending 表) ⇒ 绝不改'),
    dict(cat='pending', order=90, title='未 dump 的容器 (闸门依据)', kinds=(), risk=False,
         note='这些容器**一条串都没 dump** —— 判定依据见本表各列; 不是漏了'),
]
CAT_BY_KIND = {}
for _c in CATEGORIES:
    for _k in _c['kinds']:
        CAT_BY_KIND[_k] = _c['cat']
CAT_INFO = dict((c['cat'], c) for c in CATEGORIES)

# ─────────────────────── 文本判据阈值 (第 1~4 关) ───────────────────────
STRUCT_KINDS = ('XML', 'TXT', 'MIS', 'ATR', 'RES')     # 结构化容器: 串可以短一些
MIN_RUN_STRUCT = 6          # 第 1 关: 结构化容器最短可读串 (字节)
MIN_RUN_BIN = 8             # 第 1 关: 二进制容器最短可读串 (字节)
WORD_MIN_ASCII = 0.70       # 第 2 关①: 纯 ASCII 串的字母数字占比下限
VIS_MIN = 0.85              # 第 2 关②: 含高位字节串的可见字符占比下限
WORD_MIN_CJK = 0.55         # 第 2 关②: 含高位字节串的字母数字占比下限
MAX_CHAR_RUN = 8            # 第 2 关④: 同一字符连续重复上限
PUNCT_MIN_LEN = 16          # 第 2 关⑤: 长度达到这个值就要求至少一个标点/空格
REPEAT_SUB = 4              # 第 2 关⑥: 重复子串长度
MIN_DISTINCT = 10           # 第 3 关①: 容器放行所需的最少不同串数
MIN_TEXT_SCORE = 10.0       # 第 3 关②: 文本分 (= 不同串数 / MB) 下限
MIN_CLEAN_RATIO = 0.002     # 第 3 关③: 「干净 ASCII 串字节 / 容器字节」下限
MAX_PER_CONTAINER = 2000    # 第 4 关: 每容器最多写出的不同串数
CHUNK = 1 << 22             # 大容器分块扫描 (含重叠, 保证跨块串不丢)

# ★ 视频/音频流: **不做**原始串扫描 (实测里面没有一个真词, 全是压缩噪声)
#   扩展名取自 font_usage.MEDIA_EXT。
STREAM_EXT = {'.PSS', '.SS', '.TM', '.MPG', '.M2V'}

WORD_MIN_SPACE_WORD = 3     # 「词 空格 词」里每个词的最少字母数 (>=3 才算真词, 挡碎片)
WORDISH_MIN_LEN = 6         # 「词形串」判据: 长度下限
WORDISH_ALNUM_RATIO = 0.70  # 「词形串」判据: 字母数字占比下限

PRINTABLE = frozenset(range(0x20, 0x7F)) | {0x09}
WORD_RE = re.compile(r'[0-9A-Za-z]')
PUNCT_RE = re.compile(r"[ \t\.\-_/\\:;,'\"!?()\[\]<>+=*&%$#@~`^{}|]")
OKVIS_RE = re.compile(r"[0-9A-Za-z \t\.\-_/\\:;,'\"!?()\[\]<>+=*&%$#@~`^{}|]")
CJK_RUN_RE = re.compile(r'[\u4e00-\u9fff]+')


def cjk_run(t):
    """最长连续汉字个数 —— **唯一**可信的「这里真有中文」判据。

    单个汉字不算: 本盘字符集有 1319 个对偶码, 压缩数据里两个字节撞上真对偶是常事
    (实测中文盘/英文原盘逐容器集合减法后, 除 LANG/SFXML/ELF 外一个新字都不剩)。
    """
    m = CJK_RUN_RE.search(t)
    return len(m.group(0)) if m else 0
MSG_RE = re.compile(r'[0-9A-Za-z]{%d,}[ \t][0-9A-Za-z]{%d,}'
                    % (WORD_MIN_SPACE_WORD, WORD_MIN_SPACE_WORD))
CJK2_RE = re.compile(r'[\u4e00-\u9fff]{2,}')
PUA_RE = re.compile(r'[\ue000-\uf8ff]')
# ★ Excel 显示不出来的字符: PUA / 裸控制字符 / 零宽 / 双向控制 —— view 表同样不许有
FORBIDDEN_RE = re.compile(
    '[\u0000-\u0008\u000b-\u001f\u007f-\u009f'
    '\ue000-\uf8ff'
    '\u200b-\u200f\u2028\u2029\u202a-\u202e'
    '\u2060-\u2069\ufeff\u00ad]')

COLS = ['category', 'source_kind', 'container', 'entry_index', 'offset', 'len_bytes',
        'text', 'text_preview', 'dup_count', 'text_kind', 'confidence', 'has_cjk',
        'cjk_run', 'injectable', 'note']
ALWAYS_QUOTE = {'text', 'text_preview', 'note'}
# ★ round62: 特别收录标题表 (SFXML 属性) —— 与 COLS **不同**的列集 (下游没有工具读它,
#   且这张表要能"按 text 搜、按 容器+偏移 定位"), 所以单列一套; 见 SF_TITLE_COLS_NOTE。
SF_TITLE_COLS = ['category', 'source_kind', 'container', 'lang', 'copy_role', 'copy_index',
                 'tag', 'attr', 'entry_index', 'tag_offset', 'offset', 'len_bytes',
                 'text', 'text_preview', 'dup_count', 'is_title', 'has_cjk', 'cjk_run',
                 'injectable', 'note']
SF_TITLE_QUOTE = {'text', 'text_preview', 'note'}
SF_TITLE_COLS_NOTE = {
    'category': '恒为 sf_titles (本表专有)',
    'source_kind': "容器类型: 注入目标=SFXML; 其余语言副本=XML (classify() 只认 "
                   "EN_SPECIAL_FEATURE.XML 这一个文件名)",
    'container': "容器 (IMG#条目号 文件名), 与其它 view 表同一写法",
    'lang': '副本语言 (文件名前缀 EN/DE/ES/FR/IT; 认不出给 ?)',
    'copy_role': "zh-main = 注入目标 (= tcslib.RES['SFXML']['copies'][0], MENU.IMG#283, "
                 "当前中文标题就在这份里); lang-copy = 其它语言副本",
    'copy_index': '副本序号 (1-based, 按 IMG/条目号排序)',
    'tag': 'XML 标签名 (item / group / studio / …)',
    'attr': '属性名 (标题恒为 name)',
    'entry_index': '本容器内第几个被列出的属性 (1-based, 顺序 = blob 顺序)',
    'tag_offset': '标签 "<" 在**解压后 blob** 里的字节偏移',
    'offset': '★ 属性**值**在**解压后 blob** 里的字节偏移 (长度 = len_bytes) ⇒ 可定位',
    'len_bytes': '属性值在盘上的字节数 (= 引擎读到的字节长度)',
    'text': '解码后的属性值 (= 引擎画出来的标题); 按键图标占位写成 {{BTN:XXXX}}',
    'text_preview': '同上, 截断到 120 字符',
    'dup_count': '同一个 text 在本容器里出现了几次',
    'is_title': "yes = 就是「特别收录」的条目标题 (tag∈item/group/studio 且 attr=name); "
                "no = 其它含非 ASCII 的属性 (兜底)",
    'has_cjk': 'text 里有 >=2 个连续汉字 ⇒ yes',
    'cjk_run': '最长连续汉字个数',
    'injectable': '★ 恒为 no: 本表 **view-only**, 注入器不认 (属性不在任何可注入表里)',
    'note': '为什么不能直接改 —— 以及想改该走哪条路',
}
PENDING_COLS = ['category', 'source_kind', 'container', 'blob_bytes', 'stored_bytes',
                'n_runs_scanned', 'distinct_kept', 'text_score', 'text_ratio',
                'clean_ratio', 'injectable', 'reason', 'note']
PENDING_QUOTE = {'note', 'reason'}
SUMMARY_COLS = ['category', 'table', 'title', 'kind', 'containers_total', 'containers_kept',
                'containers_skipped', 'rows', 'distinct_texts', 'cjk_texts',
                'injectable', 'note']
SUMMARY_QUOTE = {'note', 'title', 'table', 'kind'}

VIEW_NOTE = ('★ 只能看/校对, **不能注入**: 本表是 %s 的原始字符串扫描结果, '
             '格式未被逆向, 写回去会毁盘。想改游戏文本请改 %s')
REF_LANG = '<版本>_text_long.csv / _long_nowrap.csv / _short.csv (语言表, 可注入)'

# 置信度 (只对二进制容器有意义; 结构化容器的串一律 high)
CONF_HIGH = 0.05            # clean_ratio >= 0.05
CONF_MED = 0.005            # clean_ratio >= 0.005
CONF_TEXT = ('high = 该容器里干净 ASCII 串占字节 >=5% (名字表/元数据, 几乎不可能碰巧); '
             'medium = >=0.5%; low = 仅过闸门 —— 这类容器里可能混有压缩数据的巧合碎片, '
             '核对时优先信 high/medium, low 请看 text 列自己判断')
CONF_RANK = {'high': 0, 'medium': 1, 'low': 2}


# ═════════════════════════ 文本判定 (第 1~2 关) ═════════════════════════

def min_run_for(kind):
    return MIN_RUN_STRUCT if kind in STRUCT_KINDS else MIN_RUN_BIN


def _repeat_sub(t, k=REPEAT_SUB):
    """同一个长度 k 的子串在**同一个串里**出现 >=2 次? (压缩数据/贴图噪声的典型特征)"""
    if len(t) < 2 * k:
        return False
    seen = set()
    for i in range(len(t) - k + 1):
        s = t[i:i + k]
        if s in seen:
            return True
        seen.add(s)
    return False


def judge(raw, kind, cs):
    """一个可读串像不像文本。返回 ``(是否保留, text, is_exact, is_text)``。

    is_exact = 纯 ASCII 且无空白 ⇒ 可以直接拿去别处查找/比对的**标识符/文件名**
    is_text  = 含「词(>=3字母) 空格 词」或「连续 2 个汉字」, 或
               「长度 >= 6 且字母数字占比 >= 0.70」的词形串 ⇒ 用于第 3 关的 text_ratio
    """
    if len(raw) < min_run_for(kind):
        return False, None, False, False
    exact = False
    if all(b in PRINTABLE for b in raw):
        t = raw.decode('ascii')
        if sum(1 for c in t if WORD_RE.match(c)) / len(t) < WORD_MIN_ASCII:
            return False, None, False, False
        exact = (' ' not in t and '\t' not in t)
    else:
        t = cs.decode(raw)[0]
        if PUA_RE.search(t):
            return False, None, False, False      # 未映射字节的私有区回落 ⇒ 不是文本
        if sum(1 for c in t if OKVIS_RE.match(c)) / len(t) < VIS_MIN:
            return False, None, False, False
        if sum(1 for c in t if WORD_RE.match(c)) / len(t) < WORD_MIN_CJK:
            return False, None, False, False
        if not CJK_RUN_RE.search(t):
            return False, None, False, False
    run = best = 1
    for i in range(1, len(t)):
        run = run + 1 if t[i] == t[i - 1] else 1
        best = max(best, run)
    if best > MAX_CHAR_RUN:
        return False, None, False, False
    if len(t) >= PUNCT_MIN_LEN and not PUNCT_RE.search(t):
        return False, None, False, False
    if _repeat_sub(t):
        return False, None, False, False
    n_word = sum(1 for c in t if WORD_RE.match(c))
    is_text = bool(MSG_RE.search(t) or CJK2_RE.search(t)
                   or (len(t) >= WORDISH_MIN_LEN
                       and n_word / float(len(t)) >= WORDISH_ALNUM_RATIO))
    return True, t, exact, is_text


# ═════════════════════════ 单个容器的扫描 ═════════════════════════

_IDX = None                                    # 主流程里赋成 FU.CharsetIndex()


class _Run(object):
    """轻量匹配对象 (只有 start / group(0))。"""
    __slots__ = ('start', 'data')

    def __init__(self, start, data):
        self.start, self.data = start, data

    def group(self, _n=0):
        return self.data


def iter_runs(blob, min_run):
    """扫描可读串。小容器一把梭; 大容器分块 (块间留 ``min_run`` 字节尾部重叠,
    跨块的长串不会断), 重叠区里**完全落在上一块**的匹配直接跳过 ⇒ 不重复计数。"""
    rx = _IDX.run_re(min_run)
    if len(blob) <= CHUNK:
        for m in rx.finditer(blob):
            yield _Run(m.start(), m.group(0))
        return
    step = CHUNK - min_run
    off = 0
    while off < len(blob):
        end = min(len(blob), off + CHUNK)
        seg = blob[off:end]
        base = off
        prev_base = off - step
        for m in rx.finditer(seg):
            if base > 0 and base + m.start() < prev_base + CHUNK:
                continue                       # 已在上一块里报过 (重叠区)
            yield _Run(base + m.start(), m.group(0))
        if end >= len(blob):
            break
        off += step


def scan_container(blob, kind, cs, cap=MAX_PER_CONTAINER):
    """扫一个容器 → ``dict(rows, distinct, text, exact, clean, raw, capped)``。

    rows 里每条 = ``dict(text, off, dup, exact, is_text)``, 按**首次出现顺序**。
    ``dup``   = 同一条串在本容器里出现了几次 (只写一行)。
    ``clean`` = 「干净 ASCII 串」的**总字节数** (含重复出现), 用于第 3 关的
                clean_ratio —— 真文本容器这一项占容器字节的比例远高于压缩噪声。
    """
    mr = min_run_for(kind)
    order, rowmap = [], {}
    raw_n = 0
    clean = 0
    for m in iter_runs(blob, mr):
        raw_n += 1
        ok, t, exact, is_text = judge(m.group(0), kind, cs)
        if not ok:
            continue
        if exact:
            clean += len(t)
        r = rowmap.get(t)
        if r is None:
            if len(order) >= cap:
                continue                       # 第 4 关: 每容器上限 (只保留先出现的)
            r = dict(text=t, off=m.start, dup=1, exact=exact, is_text=is_text)
            rowmap[t] = r
            order.append(t)
        else:
            r['dup'] += 1
    return dict(rows=[rowmap[t] for t in order], raw=raw_n, distinct=len(order),
                capped=len(order) >= cap, clean=clean,
                text=sum(1 for t in order if rowmap[t]['is_text']),
                exact=sum(1 for t in order if rowmap[t]['exact']))


def text_score(n_distinct, blob_len):
    """第 3 关的「文本分」= 去重后不同串数 / MB (实测噪声本底 < 1.0/MB)。"""
    return n_distinct / max(1.0, blob_len / 1048576.0)


# ═════════════════════════ CSV 写出 (Excel 友好) ═════════════════════════

def csv_field(name, value, quote_set):
    s = '' if value is None else str(value)
    if name in quote_set or any(c in s for c in ',"\r\n'):
        return '"' + s.replace('"', '""') + '"'
    return s


def write_csv(path, rows, cols, quote_set, counters=None):
    """UTF-8 BOM + CRLF (与现有多表完全同一口径, Excel 双击可开)。"""
    n_cell = 0
    with open(path, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        for r in [dict(zip(cols, cols))] + rows:
            line = ','.join(csv_field(c, r.get(c, ''), quote_set) for c in cols)
            for c in cols:
                n_cell += len(str(r.get(c, '')))
            f.write(line.encode('utf-8') + b'\r\n')
    if counters is not None:
        counters['cells'] = counters.get('cells', 0) + n_cell
    return len(rows)


def esc1(s, limit=None):
    """单行转义 (可逆): 换行/回车/制表/反斜杠。"""
    out = (s.replace('\\', '\\\\').replace('\r', '\\r')
            .replace('\n', '\\n').replace('\t', '\\t'))
    if limit and len(out) > limit:
        out = out[:limit] + '…'
    return out


def assert_cells_clean(rows, cols):
    """★ view 表也不许出现「Excel 显示不出来」的字符。返回扫描字符数。"""
    bad = []
    n = 0
    for r in rows:
        for c in cols:
            v = str(r.get(c) or '')
            n += len(v)
            m = FORBIDDEN_RE.search(v)
            if m:
                bad.append('%s 的 %s 列: U+%04X'
                           % (r.get('container') or r.get('category'), c, ord(m.group(0))))
    if bad:
        raise SystemExit('!! 拒绝写出 view 表: 还有 %d 处不可见字符:\n   %s'
                         % (len(bad), '\n   '.join(bad[:10])))
    return n


# ═════════════════════════ 特别收录标题 (SFXML 属性) — round62 ═════════════════════════
#   为什么单开一条通道: 见文件头 §round62。一句话 —— 标题在 XML **属性**里, 而
#   ① dump_text_csv.py 只导出 <text> 元素; ② 本工具的通用串扫描判据只认 ASCII,
#   汉字为主的串必然被丢。⇒ 只有"直接解析属性"才看得见它们。
#
#   ★ 只用**文件名**识别副本 (不靠 kind): 现役盘 10 份 = EN/DE/ES/FR/IT × MENU/GR,
#     其中只有 MENU.IMG#283 是 kind=SFXML (classify() 只认 EN_SPECIAL_FEATURE.XML),
#     其余 9 份是 kind=XML。多语言后缀都覆盖: XX_SPECIAL_FEATURE.XML。
SFXML_NAME_RE = re.compile(r'(?:^|_)SPECIAL_FEATURE\.XML$', re.I)
SFXML_TAG_RE = re.compile(rb'<([A-Za-z_][\w:.-]*)\b([^>]*)>')
SFXML_ATTR_RE = re.compile(rb'([A-Za-z_][\w:.-]*)\s*=\s*"([^"]*)"')
SFXML_TITLE_TAGS = ('item', 'group', 'studio')     # 引擎拿去显示的标签 (round51 实测)
SFXML_TITLE_ATTR = 'name'                          # ★ 标题就在这个属性里
NONASCII_BYTE_RE = re.compile(rb'[\x80-\xff]')
LANG_PREFIX_RE = re.compile(r'^([A-Za-z]{2})_')

SF_TITLE_NOTE = (
    '★ 只能看/校对 —— 本表 view-only, **注入器不认** (属性从来不在任何可注入表里)。'
    '这是「特别收录」条目名的**真身**: <item|group|studio name="…"> 属性, '
    '不是 <text> 正文 (正文才在 <版本>_text_long.csv / _short.csv, 那两张可注入)。'
    '★ 想改标题: 走容器级重写 (tools/iso_build/patch_zh51_sfxml_titles.py 的'
)
SF_TITLE_NOTE_TAIL = (
    '「等长原位重映射」; 改字数会动 XML 长度 ⇒ 需重压 SFXML 并确认槽位装得下, '
    '见 docs/REPORT_sf_titles_dump.md)。offset/len_bytes 就是 blob 里的定位。'
)


def sfxml_copies_of(conts):
    """从容器表里挑出全部 ``*_SPECIAL_FEATURE.XML`` 副本 (按 IMG/条目号排序)。

    ``role='zh-main'`` 的那份 = ``tcslib.RES['SFXML']['copies'][0]`` (注入器只写它);
    现役盘 = MENU.IMG#283。文件名认不出语言的给 ``?``。
    """
    target = frozenset((c[0], c[2]) for c in T.RES['SFXML']['copies'])
    out = []
    for c in conts:
        if not SFXML_NAME_RE.search(os.path.basename(c['name'])):
            continue
        img, idx = c['img'], c['idx']
        base = os.path.basename(c['name'])
        m = LANG_PREFIX_RE.match(base)
        out.append(dict(c=c, img=img, idx=idx, name=base, kind=c['kind'],
                        lang=(m.group(1).upper() if m else '?'),
                        role=('zh-main' if (img, idx) in target else 'lang-copy')))
    out.sort(key=lambda x: (x['img'], x['idx']))
    for n, x in enumerate(out, 1):
        x['copy_index'] = n
    return out


def scan_sfxml_titles(iso, cs, conts, max_rows=0):
    """扫全部 SFXML 副本的属性 ⇒ ``(rows, copies, dropped)``。

    收两档 (都按 blob 顺序, 不排序 —— 顺序 = 盘上顺序, 便于人肉对照):
      ① ``<item|group|studio>`` 的 ``name=`` (★ 全部, 含纯 ASCII 的英文原名);
      ② **任何**标签上**含非 ASCII 字节**的属性值 (兜底: 别处可能也藏中文)。
    ⇒ ①∪② 必然覆盖全部含中文的属性名 (硬自证: ``n_nonascii_written ==
      n_nonascii_scanned``, 不等就 SystemExit)。
    """
    rows, copies = [], []
    n_dropped = 0
    note = SF_TITLE_NOTE + SF_TITLE_NOTE_TAIL
    for cp in sfxml_copies_of(conts):
        c = cp['c']
        blob, _raw = FU.container_blob(iso, c)
        found, n_nonascii = [], 0
        for m in SFXML_TAG_RE.finditer(blob):
            tag = m.group(1).decode('latin-1')
            for am in SFXML_ATTR_RE.finditer(m.group(2)):
                key = am.group(1).decode('latin-1')
                val = am.group(2)
                nonascii = bool(NONASCII_BYTE_RE.search(val))
                if nonascii:
                    n_nonascii += 1
                is_title = (tag.lower() in SFXML_TITLE_TAGS and key == SFXML_TITLE_ATTR)
                if not (is_title or nonascii):
                    continue                     # pic= / unlock= 这类纯 ASCII 非标题属性
                off = m.start(2) + am.start(2)   # 属性**值**的 blob 偏移
                if blob[off:off + len(val)] != val:
                    raise SystemExit('!! 属性偏移自证失败: %s <%s %s=> 偏移 %d 回读不上'
                                     % (cont_name(c), tag, key, off))
                found.append(dict(tag=tag, attr=key, off=off, tag_off=m.start(),
                                  val=val, is_title=is_title, nonascii=nonascii,
                                  text=T.pua_to_marks(cs.decode(val)[0])))
        n_nonascii_written = sum(1 for x in found if x['nonascii'])
        if n_nonascii_written != n_nonascii:
            raise SystemExit('!! %s: 含非 ASCII 的属性扫到 %d 个, 只写出 %d 个 —— 漏了'
                             % (cont_name(c), n_nonascii, n_nonascii_written))
        dup = collections.Counter(x['text'] for x in found)
        n_skipped = 0
        for n, x in enumerate(found, 1):
            if max_rows and len(rows) >= max_rows:
                n_skipped += 1
                continue
            rows.append(dict(
                category='sf_titles', source_kind=c['kind'], container=cont_name(c),
                lang=cp['lang'], copy_role=cp['role'], copy_index=cp['copy_index'],
                tag=x['tag'], attr=x['attr'], entry_index=n,
                tag_offset=x['tag_off'], offset=x['off'], len_bytes=len(x['val']),
                text=esc1(x['text']), text_preview=esc1(x['text'], 120),
                dup_count=dup[x['text']],
                is_title=('yes' if x['is_title'] else 'no'),
                has_cjk=('yes' if cjk_run(x['text']) >= 2 else 'no'),
                cjk_run=cjk_run(x['text']), injectable='no', note=note))
        n_dropped += n_skipped
        copies.append(dict(
            copy_index=cp['copy_index'], container=cont_name(c), img=cp['img'], idx=cp['idx'],
            name=cp['name'], kind=cp['kind'], lang=cp['lang'], role=cp['role'],
            is_inject_target=(cp['role'] == 'zh-main'),
            stored_bytes=c['stored'], blob_bytes=len(blob),
            text_elements=len(T.TEXT_RE.findall(blob)),
            attrs_scanned=sum(1 for _m in SFXML_TAG_RE.finditer(blob)
                              for _a in SFXML_ATTR_RE.finditer(_m.group(2))),
            name_attrs=sum(1 for _m in SFXML_TAG_RE.finditer(blob)
                           for _a in SFXML_ATTR_RE.finditer(_m.group(2))
                           if _m.group(1).decode('latin-1').lower() in SFXML_TITLE_TAGS
                           and _a.group(1).decode('latin-1') == SFXML_TITLE_ATTR),
            rows=len(found), rows_written=len(found) - n_skipped,
            title_rows=sum(1 for x in found if x['is_title']),
            nonascii_attrs=n_nonascii,
            cjk_rows=sum(1 for x in found if cjk_run(x['text']) >= 2),
            skipped_by_max_rows=n_skipped))
    return rows, copies, n_dropped


# ═════════════════════════ 主流程 ═════════════════════════

def out_base_of(iso, out_base, prefix):
    """算出表集基准路径 ``<dir>/<prefix>`` 与"合并基准名"。"""
    if out_base:
        b = T.csv_stem(out_base)                        # …/\<版本>_text
        if prefix:
            b = os.path.join(os.path.dirname(os.path.abspath(b)), prefix)
        return os.path.abspath(b)
    ver = os.path.splitext(os.path.basename(iso))[0]
    if prefix:
        return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(iso)),
                                            prefix))
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(iso)), 'text', ver))


def check_names(base, cats):
    """★ 命名隔离硬断言: view 表名绝不能落在注入器的 ``*_text_*.csv`` 命名空间里。"""
    bad = []
    for c in cats:
        p = '%s%s%s.csv' % (base, VIEW_MARK, c)
        if '_text_' in os.path.basename(p):
            bad.append(os.path.basename(p))
        if not os.path.basename(p).endswith('_view_%s.csv' % c):
            bad.append(os.path.basename(p))
    return bad


def main():
    ap = argparse.ArgumentParser(
        description='全容器文本普查 → 多张 **view-only** CSV (只能看/校对, 不能注入)')
    ap.add_argument('--iso', required=True, help='要普查的 ISO (只读, 不会被修改)')
    ap.add_argument('--out-base', default=None, metavar='基准路径',
                    help='与 dump_text_csv.py 同一个基准名 (如 …/GR_ZH92_text.csv) ⇒ '
                         'view 表写在同一目录, 前缀取该基准的 <版本> (去掉 _text)')
    ap.add_argument('--out-dir', default=None, help='直接指定 view 表输出目录')
    ap.add_argument('--prefix', default=None, help='view 表文件名前缀 (缺省由 --out-base/--iso 推)')
    ap.add_argument('--only-category', default='', metavar='CATS',
                    help='只产出这几个类别 (逗号分隔, 如 xml,missions)')
    ap.add_argument('--max-per-container', type=int, default=MAX_PER_CONTAINER,
                    help='每容器最多写出的不同串数 (默认 %d)' % MAX_PER_CONTAINER)
    ap.add_argument('--max-rows-per-category', type=int, default=0, metavar='N',
                    help='★ 每张 view 表最多写多少行 (0=不限, 默认)。给了 N 时按 '
                         'confidence 高→低、重复次数多→少排序后截断 —— '
                         '二进制表建议 30000 以内, Excel 更好翻')
    ap.add_argument('--min-distinct', type=int, default=MIN_DISTINCT,
                    help='高风险容器放行所需最少不同串数 (默认 %d)' % MIN_DISTINCT)
    ap.add_argument('--min-text-score', type=float, default=MIN_TEXT_SCORE,
                    help='高风险容器放行的文本分下限 (默认 %.0f /MB)' % MIN_TEXT_SCORE)
    ap.add_argument('--min-clean-ratio', type=float, default=MIN_CLEAN_RATIO,
                    help='高风险容器放行的「干净 ASCII 串字节占比」下限 (默认 %.4f)'
                         % MIN_CLEAN_RATIO)
    ap.add_argument('--scan-streams', action='store_true',
                    help='★ 也扫描视频/音频流 (%s) —— 默认不扫, 因为它们不含可本地化文本'
                         % ','.join(sorted(STREAM_EXT)))
    ap.add_argument('--no-gate', action='store_true',
                    help='★ 关掉第 3 关容器级闸门 (会产出大量噪声; 只用于排查)')
    ap.add_argument('--stats', action='store_true', help='只打印统计, 不写 CSV')
    ap.add_argument('--expect-containers', type=int, default=0,
                    help='覆盖自证: 期望容器总数 (与 font_usage.py 的 4713 对表; 0=不校验)')
    ap.add_argument('--debug-stats', default=None, metavar='JSON',
                    help='★ 工程侧: 把**每个容器**的判定统计写成 JSON (调阈值用)')
    a = ap.parse_args()

    global _IDX
    _IDX = FU.CharsetIndex()
    cs = T.Charset()

    iso_sha = T.sha256_file(a.iso)
    iso = T.Iso(a.iso)
    conts = FU.build_container_list(iso)
    print('# dump_containers.py — %s (全容器文本普查, view-only)' % FMT_VIEW)
    print('# ISO     : %s' % iso.path)
    print('# sha256  : %s' % iso_sha)
    print('# charset : %s (%d 单字节码 + %d 双字节码)'
          % (os.path.relpath(T.CHARSET, T.REPO), len(cs.enc_single), len(cs.enc_pair)))

    n_by_img = collections.Counter(c['img'] for c in conts)
    n_by_kind = collections.Counter(c['kind'] for c in conts)
    print('\n== 覆盖自证 ==')
    print('# 容器总数 %d  (GR.IMG %d + MENU.IMG %d + ISO 独立文件 %d)'
          % (len(conts), n_by_img['GR.IMG'], n_by_img['MENU.IMG'], n_by_img['ISO_FILE']))
    print('# 按类型: %s' % ', '.join('%s=%d' % kv for kv in sorted(n_by_kind.items())))
    n_use = sum(n_by_img.values())
    if a.expect_containers and len(conts) != a.expect_containers:
        print('!! 覆盖自证失败: 容器总数 %d != 期望 %d' % (len(conts), a.expect_containers))
        iso.close()
        sys.exit(3)
    print('#   与 font_usage.py 的 4713 / 1583.7 MB 对表: %s'
          % ('一致 ✓' if len(conts) == 4713 else '**不一致** (见上)'))
    if n_use != len(conts):
        print('!! 内部错误: 容器计数不自洽')
        iso.close()
        sys.exit(3)

    want = [x.strip() for x in a.only_category.split(',') if x.strip()]
    known_cats = [c['cat'] for c in CATEGORIES]
    for w in want:
        if w not in known_cats:
            print('!! 未知类别 %s (可用: %s)' % (w, ','.join(known_cats)))
            iso.close()
            sys.exit(2)
    want_sf = 'sf_titles' in known_cats and (not want or 'sf_titles' in want)

    # ── 阈值快照 (写进 meta.json) ──
    thresh = dict(
        min_run_struct=MIN_RUN_STRUCT, min_run_bin=MIN_RUN_BIN,
        word_min_ascii=WORD_MIN_ASCII, vis_min=VIS_MIN, word_min_cjk=WORD_MIN_CJK,
        max_char_run=MAX_CHAR_RUN, punct_min_len=PUNCT_MIN_LEN, repeat_sub=REPEAT_SUB,
        word_min_space_word=WORD_MIN_SPACE_WORD, wordish_min_len=WORDISH_MIN_LEN,
        wordish_alnum_ratio=WORDISH_ALNUM_RATIO,
        min_distinct=0 if a.no_gate else a.min_distinct,
        min_text_score=0.0 if a.no_gate else a.min_text_score,
        min_clean_ratio=0.0 if a.no_gate else a.min_clean_ratio,
        max_per_container=a.max_per_container,
        max_rows_per_category=a.max_rows_per_category,
        confidence=dict(high='clean_ratio>=%.3f' % CONF_HIGH,
                        medium='clean_ratio>=%.3f' % CONF_MED,
                        low='仅过闸门', text=CONF_TEXT),
        gate_rule=('通过 = distinct>=min_distinct 且 score>=min_text_score 且 '
                   'clean_ratio>=min_clean_ratio; 只对高风险类 (RSB/PAK/MEDIA/OTHER) 生效'),
        gate_enabled=not a.no_gate,
        stream_ext=sorted(STREAM_EXT), scan_streams=bool(a.scan_streams),
        stream_policy=('视频/音频流默认**不扫**(--scan-streams 可开): 实测这类容器里的"候选串"'
                       '全部只出现 1 次, 是本盘字符集里的字节巧合, 不含可本地化文本'),
        chunk=CHUNK,
        scan_alphabet='ASCII 0x20..0x7E + 本盘字符集单字节码 + 对偶 lead/trail + 按键字节 '
                      '(与 font_usage.CharsetIndex.alphabet 同一份)')

    # ── 逐容器扫描 ──
    per_cat = collections.defaultdict(list)         # cat -> [row]
    stat = collections.defaultdict(lambda: dict(
        containers=0, kept=0, skipped=0, rows=0, distinct=0, cjk=0, truncated_cat=0,
        kinds=collections.Counter()))
    pending = []
    dbg = []
    n_blob = 0
    zero_byte_iso = []
    print('\n== 扫描 %d 个容器 ==' % len(conts))
    for i, c in enumerate(conts):
        kind = c['kind']
        cat = CAT_BY_KIND.get(kind)
        if cat is None:
            continue                       # LANG / SFXML: 由 dump_text_csv.py 负责
        info = CAT_INFO[cat]
        st = stat[cat]
        st['containers'] += 1
        st['kinds'][kind] += 1
        blob, _raw = FU.container_blob(iso, c)
        if len(blob) == 0:
            zero_byte_iso.append((c['img'], c['name']))
            st['skipped'] += 1
            pending.append(dict(category=cat, source_kind=kind,
                                container=cont_name(c), blob_bytes=0, stored_bytes=c['stored'],
                                n_runs_scanned=0, distinct_kept=0, text_score='0',
                                msg_ratio='0', injectable='no', reason='zero-byte',
                                note='解压后 0 字节 (ISO 里的空文件/占位条目) ⇒ 本来就没有文本'))
            continue
        n_blob += len(blob)
        extok = os.path.splitext(c['name'].upper())[1] in STREAM_EXT
        if extok and not a.scan_streams:
            st['skipped'] += 1
            pending.append(dict(
                category=cat, source_kind=kind, container=cont_name(c),
                blob_bytes=len(blob), stored_bytes=c['stored'],
                n_runs_scanned=0, distinct_kept=0, text_score='-', text_ratio='-',
                clean_ratio='-', injectable='no', reason='stream-container',
                note='视频/音频流 (%s): **不做**原始串扫描 —— 实测这类容器里没有一个真词 '
                     '(ZZZ.PSS 143 MB: 2910 条候选***全部***只出现 1 次, 是本盘字符集里的'
                     '字节巧合; MUSIC.TM 50 MB 同理)。它们不含可本地化文本。'
                     % os.path.splitext(c['name'].upper())[1]))
            continue
        r = scan_container(blob, kind, cs, cap=a.max_per_container)
        score = text_score(r['distinct'], len(blob))
        tratio = r['text'] / max(1, r['distinct']) if r['distinct'] else 0.0
        cratio = r['clean'] / float(len(blob))
        capped = r['capped']
        n_cjk2 = sum(1 for x in r['rows'] if CJK2_RE.search(x['text']))
        if a.debug_stats:
            dbg.append(dict(kind=kind, cat=cat, name=c['name'], img=c['img'], idx=c['idx'],
                            blob=len(blob), stored=c['stored'], risk=info['risk'],
                            raw=r['raw'], distinct=r['distinct'], text=r['text'],
                            exact=r['exact'], clean=r['clean'], cjk2=n_cjk2, capped=capped,
                            score=round(score, 3), text_ratio=round(tratio, 4),
                            clean_ratio=round(cratio, 6)))
        if info['risk'] and not a.no_gate:
            why = []
            if r['distinct'] < a.min_distinct:
                why.append('不同串 %d < %d' % (r['distinct'], a.min_distinct))
            if score < a.min_text_score:
                why.append('文本分 %.2f < %.1f' % (score, a.min_text_score))
            if cratio < a.min_clean_ratio:
                why.append('干净 ASCII 串占比 %.5f < %.4f' % (cratio, a.min_clean_ratio))
            if why or r['distinct'] == 0:
                st['skipped'] += 1
                pending.append(dict(
                    category=cat, source_kind=kind, container=cont_name(c),
                    blob_bytes=len(blob), stored_bytes=c['stored'],
                    n_runs_scanned=r['raw'], distinct_kept=r['distinct'],
                    text_score='%.2f' % score, text_ratio='%.3f' % tratio,
                    clean_ratio='%.5f' % cratio, injectable='no',
                    reason=('no-text' if r['distinct'] == 0 else 'below-gate'),
                    note='未通过容器级闸门 (%s) ⇒ 一条都没 dump'
                         % ('; '.join(why) if why else '不同串 0')))
                continue
        st['kept'] += 1
        st['rows'] += sum(x['dup'] for x in r['rows'])
        st['distinct'] += r['distinct']
        st['cjk'] += sum(1 for x in r['rows'] if cjk_run(x['text']) >= 2)
        note = VIEW_NOTE % (info['title'], REF_LANG)
        if capped:
            note += ('; ⚠ 本容器超过每容器上限 %d 条, 已截断 (只保留先出现的)'
                     % a.max_per_container)
        if info['risk']:
            conf = ('high' if cratio >= CONF_HIGH else
                    ('medium' if cratio >= CONF_MED else 'low'))
        else:
            conf = 'high'
        rows_new = []
        for n, x in enumerate(r['rows'], 1):
            rows_new.append(dict(
                category=cat, source_kind=kind, container=cont_name(c),
                entry_index=n, offset=x['off'], len_bytes=len(x['text'].encode('utf-8')),
                text=esc1(x['text']), text_preview=esc1(x['text'], 120),
                dup_count=x['dup'],
                text_kind=('exact' if x['exact'] else
                           ('text' if x['is_text'] else 'fragment')),
                confidence=conf,
                has_cjk=('yes' if cjk_run(x['text']) >= 2 else 'no'),
                cjk_run=cjk_run(x['text']),
                injectable='no', note=note))
        rows_new.sort(key=lambda y: (CONF_RANK[y['confidence']], -y['dup_count']))
        room = (a.max_rows_per_category - len(per_cat[cat])
                if a.max_rows_per_category else len(rows_new))
        if room <= 0:
            continue
        if len(rows_new) > room:
            st['truncated_cat'] += len(rows_new) - room
            rows_new = rows_new[:room]
        per_cat[cat] += rows_new
        if (i + 1) % 500 == 0 or i + 1 == len(conts):
            print('#   … %d/%d 容器' % (i + 1, len(conts)))

    # ── ★ round62: SFXML 属性 (特别收录的条目标题/组名) 专项通道 ──
    #   为什么不能靠上面的通用扫描: 第 2 关判据的可见字符表/字母数字表**只含 ASCII**,
    #   汉字为主的串必然被判"不像文本" ⇒ 标题一个都进不来 (见文件头 §round62)。
    sf_rows, sf_copies, sf_dropped = [], [], 0
    if want_sf:
        print('\n== 特别收录标题 (SFXML 的 name= 属性; 专项解析, 不靠通用串扫描) ==')
        sf_rows, sf_copies, sf_dropped = scan_sfxml_titles(
            iso, cs, conts, max_rows=a.max_rows_per_category)
        per_cat['sf_titles'] = sf_rows
        st = stat['sf_titles']
        st['containers'] = len(sf_copies)
        st['kept'] = sum(1 for x in sf_copies if x['rows'])
        st['skipped'] = st['containers'] - st['kept']
        st['rows'] = len(sf_rows)
        st['distinct'] = len(set(x['text'] for x in sf_rows))
        st['cjk'] = sum(1 for x in sf_rows if x['has_cjk'] == 'yes')
        st['truncated_cat'] = sf_dropped
        for x in sf_copies:
            st['kinds'][x['kind']] += 1
        if not sf_copies:
            print('!! 一个 *_SPECIAL_FEATURE.XML 副本都没找到 —— 这张盘不对? (本通道无输出)')
        print('# %-36s %-4s %-9s %5s %8s %8s %7s %7s' %
              ('容器', '语言', '角色', 'name', '非ASCII', '汉字>=2', '写出', '<text>'))
        for x in sf_copies:
            print('# %-36s %-4s %-9s %5d %8d %8d %7d %7d%s'
                  % (x['container'], x['lang'], x['role'], x['name_attrs'],
                     x['nonascii_attrs'], x['cjk_rows'], x['rows_written'],
                     x['text_elements'],
                     '  ← 注入目标 (copies[0])' if x['is_inject_target'] else ''))
        print('# ★ 「非ASCII」= 该副本里含 >=0x80 字节的 name 属性; 「汉字>=2」= 其中**真的有**'
              '连续 2 个汉字。')
        print('#   DE/ES/FR/IT 四份副本是**西文原码**(未汉化): 用本盘中文码表解码会把 í/ü/é 这类'
              '字节解成**孤立**汉字 (实测 "GR Misi视n 1") ⇒ 判据要求连续 >=2 个汉字, '
              '孤立汉字是解码噪声, 不是中文标题 (见 cjk_run 列)。')
        print('# 合计: 副本 %d 份 / 写出 %d 行 (标题 %d) / 含中文 %d / 含非 ASCII 属性 %d'
              % (len(sf_copies), len(sf_rows),
                 sum(1 for x in sf_rows if x['is_title'] == 'yes'), st['cjk'],
                 sum(x['nonascii_attrs'] for x in sf_copies)))
        print('# ★ 与 _view_xml.csv 的关系: 那 8 份非注入目标副本 (kind=XML) 仍会被通用扫描'
              '过一遍, 但判据只认 ASCII ⇒ **汉字为主的串一条都进不去**。')
        print('  找「特别收录」的条目标题请只看 _view_sf_titles.csv (本表); '
              '_view_xml.csv 的列结构与内容**保持原样**。')

    print('\n== 每类结果 (第 3 关容器级闸门%s) =='
          % ('已关闭 --no-gate' if a.no_gate else '开启'))
    print('# %-18s %6s %6s %6s %8s %9s %7s %9s' %
          ('类别', '容器', '放行', '未dump', '行数', '不同串', '含中文', '超类上限'))
    for c in CATEGORIES:
        if c['cat'] == 'pending' or stat[c['cat']]['containers'] == 0:
            continue
        s = stat[c['cat']]
        print('# %-18s %6d %6d %6d %8d %9d %7d %9d'
              % (c['cat'], s['containers'], s['kept'], s['skipped'], s['rows'],
                 s['distinct'], s['cjk'], s.get('truncated_cat', 0)))
    print('# 解压后合计 %.1f MB' % (n_blob / 1048576.0))
    if zero_byte_iso:
        print('# 解压后 0 字节的容器 %d 个: %s'
              % (len(zero_byte_iso), ', '.join(n for (_i, n) in zero_byte_iso[:6])))

    if a.debug_stats:
        json.dump(dbg, open(a.debug_stats, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=0)
        print('# [debug] 每容器判定统计 → %s (%d 条)' % (a.debug_stats, len(dbg)))

    if a.stats:
        iso.close()
        return

    # ── 输出路径 ──
    odir = a.out_dir
    prefix = a.prefix
    if a.out_base and not odir:
        b = T.csv_stem(a.out_base)
        odir = os.path.dirname(os.path.abspath(b))
        if not prefix:
            base_name = os.path.basename(b)
            prefix = base_name[:-5] if base_name.endswith('_text') else base_name
    if not odir:
        odir = os.path.join(os.path.dirname(os.path.abspath(a.iso)), 'text')
    if not prefix:
        prefix = os.path.splitext(os.path.basename(a.iso))[0]
    os.makedirs(odir, exist_ok=True)

    cats = [c['cat'] for c in CATEGORIES]
    if want:
        cats = [c for c in cats if c in want]
    bad = check_names(os.path.join(odir, prefix), cats)
    if bad:
        raise SystemExit('!! 命名隔离断言失败 (view 表不许落在 *_text_*.csv 命名空间): %s' % bad)

    print('\n== 写出 view 表 (UTF-8 BOM + CRLF; 一律 injectable=no) ==')
    tables, total_rows = [], 0
    for c in CATEGORIES:
        cat = c['cat']
        if cat not in cats:
            continue
        p = os.path.join(odir, '%s%s%s.csv' % (prefix, VIEW_MARK, cat))
        if cat == 'pending':
            rows = [dict(x, note=x['note']) for x in pending]
            assert_cells_clean(rows, PENDING_COLS)
            write_csv(p, rows, PENDING_COLS, PENDING_QUOTE)
        elif cat == 'sf_titles':
            # ★ round62: 列集与 COLS 不同 (带 tag/attr/偏移/lang/copy_role), 见 SF_TITLE_COLS
            rows = per_cat.get(cat, [])
            assert_cells_clean(rows, SF_TITLE_COLS)
            write_csv(p, rows, SF_TITLE_COLS, SF_TITLE_QUOTE)
        else:
            rows = per_cat.get(cat, [])
            assert_cells_clean(rows, COLS)
            write_csv(p, rows, COLS, ALWAYS_QUOTE)
        tables.append(dict(category=cat, path=p.replace('\\', '/'), name=os.path.basename(p),
                           title=c['title'],
                           kind=(c.get('kind_label') or '/'.join(c['kinds']) or '(闸门依据)'),
                           rows=len(rows), injectable='no',
                           bytes=os.path.getsize(p), sha256=T.sha256_file(p),
                           containers_total=stat[cat]['containers'],
                           containers_kept=stat[cat]['kept'],
                           containers_skipped=stat[cat]['skipped'],
                           distinct_texts=stat[cat]['distinct'],
                           cjk_texts=stat[cat]['cjk'], note=c['note']))
        total_rows += len(rows)
        print('#   %-18s %7d 行  %8.1f KB  %s'
              % (cat, len(rows), os.path.getsize(p) / 1024.0,
                 os.path.relpath(p, T.REPO).replace('\\', '/') if p.startswith(T.REPO) else p))

    # ── 分类总表 (给用户"一张表看全") ──
    summ_path = os.path.join(odir, '%s%scontainers_summary.csv' % (prefix, VIEW_MARK))
    srows = []
    for t in sorted(tables, key=lambda x: CAT_INFO[x['category']]['order']):
        srows.append(dict(category=t['category'], table=t['name'], title=t['title'],
                          kind=t['kind'], containers_total=t['containers_total'],
                          containers_kept=t['containers_kept'],
                          containers_skipped=t['containers_skipped'],
                          rows=t['rows'], distinct_texts=t['distinct_texts'],
                          cjk_texts=t['cjk_texts'], injectable='no', note=t['note']))
    extra = [
        dict(category='LANG', table='%s_text_long.csv / _long_nowrap.csv / _short.csv' % prefix,
             title='语言表 EN_STRINGS.RES (游戏正文)', kind='LANG',
             containers_total=2, containers_kept=2, containers_skipped=0,
             rows='-', distinct_texts='-', cjk_texts='-', injectable='yes',
             note='★ 这三张表**可以注入**: 只改 text_edited 列。由 dump_text_csv.py 产出'),
        dict(category='SFXML', table='同上三张表 (kind=long/short 里) + %s_view_sf_titles.csv'
             % prefix,
             title='特别收录 EN_SPECIAL_FEATURE.XML', kind='SFXML',
             containers_total=len(sf_copies) or 2, containers_kept=len(sf_copies) or 2,
             containers_skipped=0,
             rows='-', distinct_texts='-', cjk_texts='-', injectable='yes',
             note='★ <text> **正文**混在 long / short 表里 (可注入)。'
                  '★ 但**条目标题/组名/工作室名**是 XML **属性** (item|group|studio name=…), '
                  '从来没进过可注入表 —— 它在 %s_view_sf_titles.csv (view-only, 按 text 可搜, '
                  '带容器+偏移)' % prefix),
    ]
    assert_cells_clean(srows + extra, SUMMARY_COLS)
    write_csv(summ_path, srows + extra, SUMMARY_COLS, SUMMARY_QUOTE)
    print('#   %-18s %7d 行  %8.1f KB  %s'
          % ('containers_summary', len(srows) + len(extra),
             os.path.getsize(summ_path) / 1024.0,
             os.path.relpath(summ_path, T.REPO).replace('\\', '/')))

    # ── meta.json ──
    meta = dict(
        format=FMT_VIEW, generated=datetime.datetime.now().isoformat(timespec='seconds'),
        iso=iso.path, iso_sha256=iso_sha,
        charset=os.path.relpath(T.CHARSET, T.REPO),
        tool='tools/text_csv/dump_containers.py',
        engine='tools/font_pipeline/font_usage.py (容器枚举/解码口径; 只 import)',
        naming=('<版本>_view_<类别>.csv —— ★ 与注入器的 *_text_*.csv 命名空间互斥: '
                'view 表只能看/校对, 注入器会明确拒绝'),
        injectable_policy=('本文件产出的**每一张表都是 view-only (injectable=no)**。'
                           '理由: 这些容器的格式未被逆向, 无法保证逐字节往返 ⇒ 写回去会毁盘。'
                           '唯一可注入的是 dump_text_csv.py 的 *_text_*.csv (LANG/SFXML)。'),
        categories=[dict(cat=c['cat'], title=c['title'], kinds=list(c['kinds']),
                         kind_label=c.get('kind_label') or '/'.join(c['kinds']) or '(闸门依据)',
                         risk=c['risk'], note=c['note']) for c in CATEGORIES],
        thresholds=thresh,
        containers=dict(total=len(conts), by_img=dict(n_by_img),
                        by_kind=dict(n_by_kind),
                        blob_total_bytes=n_blob,
                        blob_total_mb=round(n_blob / 1048576.0, 1),
                        zero_byte=len(zero_byte_iso),
                        cross_check='与 font_usage.py round38 报告的 4713 个容器 / 1583.7 MB 对表'),
        tables=tables,
        summary=dict(path=summ_path.replace('\\', '/'), rows=len(srows) + len(extra),
                     sha256=T.sha256_file(summ_path)),
        totals=dict(tables=len(tables), rows=total_rows + len(srows) + len(extra),
                    distinct_texts=sum(t['distinct_texts'] for t in tables),
                    containers_kept=sum(t['containers_kept'] for t in tables),
                    containers_skipped=sum(t['containers_skipped'] for t in tables),
                    truncated_by_category=dict((c, stat[c]['truncated_cat'])
                                               for c in stat if stat[c].get('truncated_cat')),
                    truncation_policy=('--max-rows-per-category=N 时按 confidence 高→低、'
                                       'dup_count 多→少排序后截断; 截掉的行数记在这里')),
        confidence_note=CONF_TEXT,
        # ── ★ round62: 特别收录标题 (SFXML 属性) ──
        sf_titles=dict(
            table='%s%s%s.csv' % (prefix, VIEW_MARK, 'sf_titles'),
            columns=SF_TITLE_COLS_NOTE,
            why=('「特别收录」的条目名/组名/工作室名存在 EN_SPECIAL_FEATURE.XML 的 '
                 '<item|group|studio name="…"> **属性**里, 不是 <text> 正文。'
                 'dump_text_csv.py 只导出 <text> (TEXT_RE) ⇒ 标题从来没进过任何可注入表; '
                 '本工具的通用串扫描也看不见它们 —— 第 2 关判据的可见字符表/字母数字表'
                 '**只含 ASCII**, 汉字为主的串 (如 国会最高勋章) 必然被判"不像文本"。'
                 '⇒ round62 起单开这条专项通道 (只按文件名认副本, 与 kind 无关)。'),
            coverage=('每个副本的「含非 ASCII 属性」与「写出行」逐份自证相等 '
                      '(n_nonascii_written == n_nonascii_scanned, 不等就退出); '
                      'name= 属性额外**全量**列出 (含纯 ASCII 的英文原名)'),
            decode_policy=('属性值用**本盘字符集** (charset_compiled_zh16.json) 解码 —— 这正是引擎'
                           '读标题的口径。★ DE/ES/FR/IT 四份副本是**西文原码** (没被汉化): 用中文'
                           '码表解出来会把 í/ü/é 这类字节解成**孤立**汉字 (实测 "GR Misi视n 1") '
                           '⇒ 判据要求**连续 >=2 个汉字**才算中文, 孤立汉字只是解码噪声 '
                           '(cjk_run=1, has_cjk=no); 认标题请看 lang / copy_role 列。'),
            relation_to_view_xml=('_view_xml.csv 的列结构与内容**保持原样不变** (下游有工具读它): '
                                  '那 8 份非注入目标副本 (kind=XML) 仍会被通用扫描过一遍, 但受'
                                  '上面的 ASCII 判据限制, **汉字为主的串一条都进不去** ⇒ '
                                  '找标题只看 _view_sf_titles.csv'),
            injectable='no (view-only; 属性不在任何可注入表里)',
            how_to_edit=('想真改标题: 容器级重写。等长原位重映射的现成做法 = '
                         'tools/iso_build/patch_zh51_sfxml_titles.py (round51 用它修了 49 个'
                         '陈旧标题, 长度不变 ⇒ 不动容器大小); 要**改字数**就得重压 SFXML 并'
                         '确认槽位装得下 (patch_zh51 会显式拒绝超槽)。'),
            copies=sf_copies,
            totals=dict(copies=len(sf_copies), rows=len(sf_rows),
                        title_rows=sum(1 for x in sf_rows if x['is_title'] == 'yes'),
                        cjk_rows=stat['sf_titles']['cjk'] if 'sf_titles' in stat else 0,
                        nonascii_attrs=sum(x['nonascii_attrs'] for x in sf_copies),
                        text_elements=sum(x['text_elements'] for x in sf_copies),
                        skipped_by_max_rows=sf_dropped)),
        cjk_note=('含中文的行 = has_cjk=yes (text 里有 >=2 个**连续**汉字; cjk_run 列给出最长'
                  '连续汉字数)。真正的游戏中文文本只有 LANG/SFXML (由 dump_text_csv.py 产出) '
                  '与本工具在 ELF 里扫到的极少数调试串; 二进制容器里的"汉字"绝大多数是'
                  '**噪声巧合** —— 实测: 与英文原盘逐容器做命中集合减法后, '
                  '除 LANG/SFXML/ELF 外一个新字都不剩 (4713 个容器里 4700 个命中集合逐元素相同)。'),
    )
    meta_path = os.path.join(odir, '%s%scontainers.meta.json' % (prefix, VIEW_MARK))
    json.dump(meta, open(meta_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('#   %-18s %s' % ('meta.json',
                            os.path.relpath(meta_path, T.REPO).replace('\\', '/')))

    print('\n[check] 命名隔离: %d 张 view 表**没有**一张叫 *_text_*.csv ✓ '
          '(注入器 --csv <目录> 自动扫描的是 *_text_*.csv, 扫不到它们)' % len(tables))
    print('[check] 表内 injectable 列: %d 行全部 = no ✓' % (total_rows + len(srows) + len(extra)))
    if 'sf_titles' in cats:
        print('[check] 特别收录标题 (SFXML 的 name= 属性): %d 行 / 含中文 %d 行 / 副本 %d 份 '
              '⇒ 在 %s 里直接搜 text 列 ✓'
              % (len(sf_rows), stat['sf_titles']['cjk'], len(sf_copies),
                 os.path.basename('%s%s%s.csv' % (prefix, VIEW_MARK, 'sf_titles'))))
        print('        (通用表搜不到它们: 第 2 关判据只认 ASCII ⇒ 汉字为主的串一律被判非文本)')
    print('[check] 未 dump 的容器: %d 个, 判定依据逐行写在 %s'
          % (len(pending), os.path.basename('%s%s%s.csv' % (prefix, VIEW_MARK, 'pending'))))
    print('\n下一步: 用 Excel 打开 %s' % (os.path.relpath(odir, T.REPO).replace('\\', '/')))
    print('        ★ %s —— 先看这张: 一行一个类别, 告诉你有多少文本、能不能改'
          % os.path.basename(summ_path))
    print('        ★ 搜「特别收录」的**条目标题/组名/工作室名**: %s_view_sf_titles.csv'
          % prefix)
    print('          (标题在 XML 属性里; %s_text_*.csv 里只有 <text> 正文)'
          % prefix)
    print('        ★ 要改游戏正文: 改 %s_text_long.csv / %s_text_short.csv 的 text_edited 列'
          % (prefix, prefix))
    print('          (那些表 injectable=yes; 本工具的 %s_view_*.csv **改了没用**, 注入器会拒绝)'
          % prefix)
    iso.close()


def cont_name(c):
    """容器在人话里的名字 (IMG 条目带 #号; ISO 文件给路径)。"""
    if c['img'] == 'ISO_FILE':
        return c['name']
    return '%s#%d %s' % (c['img'], c['idx'], c['name'])


if __name__ == '__main__':
    main()
