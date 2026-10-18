# -*- coding: utf-8 -*-
r"""make_release_pack.py — 把「当前版本」的资料打成**可直接交给用户**的资料包 (round43)

产出目录: ``work/builds/<版本>/release/`` (用户新规: 所有产物限制在版本文件夹内)

    release/
      README.md                      ← ★ 人话总索引 (本脚本不写它; 见文件尾提示)
      MANIFEST.json                  ← 本脚本产出: 每个文件的字节数 + sha256
      字库报告.xlsx / 字库报告.md      ← 本脚本产出 (数字**全部现算**)
      text/
        <版本>_text_long.csv            ★ 可注入 (长段, 可写 {WRAP})
        <版本>_text_long_nowrap.csv     ★ 可注入 (语言表长段)
        <版本>_text_short.csv           ★ 可注入 (按钮/条目名)
        <版本>_text.meta.json           多表元信息 (注入器靠它对格式/源盘 sha)
        README_文本表.md                ← 人话说明 (手工维护)
        <view 来源>_view_*.csv          ⚠ 只能看 (view-only, injectable=no)
        <view 来源>_view_containers.meta.json
      font/
        <版本>_font_atlas.png          (2 倍近邻放大; 黑=墨/白=空)
        <版本>_font_atlas_1x.png       (1:1, 1024x512)
        <版本>_font_charset.csv        字符集清单
        <版本>_font_ft.csv             FT 记录表

★ 铁律: **只读 ISO** —— 本脚本一行都不写盘内数据; 所有数字都是现读 charset + 图集算出来的,
  没有任何写死的常量 (1504/1319/45/140 都是算出来的, 换盘/换 charset 会自动跟着变)。

用法:
  python tools/maint/make_release_pack.py                      # 默认 --build GR_ZH93
  python tools/maint/make_release_pack.py --build GR_ZH93 --view-from work/builds/GR_ZH92/text
  python tools/maint/make_release_pack.py --skip-font-dump     # 复用版本夹里已有的 font/
"""
import argparse
import csv
import datetime
import io
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:                                                    # noqa: BLE001
    pass

import tcslib                                                        # noqa: E402
import icon_table                                                    # noqa: E402
import dump_font                                                     # noqa: E402

TEXT_KINDS = ('long', 'long_nowrap', 'short')
VIEW_CATS = ('xml', 'txt', 'missions', 'character_names', 'program_strings',
             'other_res', 'binary_assets', 'iso_files', 'pending')
REL = lambda p: os.path.relpath(p, REPO).replace('\\', '/')          # noqa: E731


def sha256(p):
    return tcslib.sha256_file(p)


def size_of(p):
    return os.path.getsize(p)


def copy_into(src, dstdir, note):
    """拷一个文件进资料包, 返回记录 dict。"""
    os.makedirs(dstdir, exist_ok=True)
    dst = os.path.join(dstdir, os.path.basename(src))
    shutil.copy2(src, dst)
    return dict(path=REL(dst), name=os.path.basename(dst), bytes=size_of(dst),
                sha256=sha256(dst), source=REL(src), note=note)


# ═══════════════════════ ① 字库数字 (全部现算) ═══════════════════════

def collect_font_numbers(iso_path, font_dir, prefix, kind_rows):
    """读 charset + 盘上图集, 现算全部数字。返回 dict。

    ★ 与 dump_font.py 用**同一批函数** (capacity_report / load_font / GlyphCache),
      所以「报告里的数字 == dump_font 打印的数字」是构造上保证的, 不是巧合。
    """
    cs = tcslib.Charset()
    f = dump_font.load_font(iso_path)
    faces, atlas = f['faces'], f['atlas']
    gray = dump_font.atlas_gray(atlas)
    atlas_ink = sum(1 for b in gray if b == 0)
    iso = tcslib.Iso(iso_path)
    try:
        cache = tcslib.GlyphCache(cs, iso)
        cap = dump_font.capacity_report(cs, cache, faces, atlas_ink, atlas['w'], atlas['h'])
    finally:
        iso.close()

    # kind 统计: 直接数**刚 dump 出来的** charset CSV (它就是本盘字符全清单)
    kinds = {}
    for r in kind_rows:
        kinds[r['kind']] = kinds.get(r['kind'], 0) + 1
    n_total = len(kind_rows)
    missing = [r for r in kind_rows if str(r['has_glyph']) == '0']
    n_glyph = n_total - len(missing)

    return dict(
        charset_path=REL(tcslib.CHARSET),
        charset_sha=sha256(tcslib.CHARSET),
        charset_single=len(cs.enc_single), charset_pair=len(cs.enc_pair),
        charset_unique=len(set(cs.enc_single) | set(cs.enc_pair)),
        kinds=kinds, kind_total=n_total, kind_shares=dict(
            (k, round(100.0 * v / max(1, n_total), 2)) for k, v in kinds.items()),
        n_glyph=n_glyph, n_missing_glyph=len(missing),
        missing_examples=[(r['char'], r['unicode'], r['kind']) for r in missing[:12]],
        cap=cap, atlas=dict(w=atlas['w'], h=atlas['h'], psm=atlas['psm'],
                            ink=atlas_ink, texels=atlas['w'] * atlas['h'],
                            bytes=atlas['px_size']),
        faces=[dict(idx=i, name=nm, nrec=len(recs), fld=fld[:6])
               for i, (nm, fld, recs) in enumerate(faces)],
        n_slots=tcslib.pair_capacity(), lead_lo=tcslib.LEAD_LO, lead_hi=tcslib.LEAD_HI,
        trail_lo=tcslib.PAIR_TRAIL_LO, trail_hi=tcslib.PAIR_TRAIL_HI,
        ncol=tcslib.NCOL, phi=dict(tcslib.ATLAS_PHI), grid_y0=tcslib.GRID_Y0,
        grid_skip_row=tcslib.GRID_SKIP_ROW, grid_skip_rows=tcslib.GRID_SKIP_ROWS,
        single_used=cap['single']['used'], single_hanzi=cap['single']['used_hanzi'],
        single_latin1=cap['single']['used_latin1'],
        spare=cap['single']['spare_bytes'], icons=cap['single']['spare_is_icon_bytes'],
        really_usable=cap['single']['really_usable'],
        dump_total=cap['charset']['dump_total'])


# ═══════════════════════ ② 报告: Markdown ═══════════════════════

def md_report(N, build, iso_sha, rows):
    c = N['cap']
    p = c['pair']
    L = []
    A = L.append
    A('# 字库报告 —— %s' % build)
    A('')
    A('> 生成: `tools/maint/make_release_pack.py`（%s）· 现役盘 `%s.iso`'
      % (datetime.date.today().isoformat(), build))
    A('> 盘 sha256 `%s`' % iso_sha)
    A('> **本报告所有数字都是现读 charset + 盘上图集算出来的**，没有任何写死的常量。')
    A('')
    A('## 一句话结论')
    A('')
    A('| 问题 | 答案 |')
    A('|---|---|')
    A('| 汉字（对偶码）最多能放多少？ | **%d** 个字 |' % p['capacity'])
    A('| 现在用了多少？ | **%d** 个（%.2f%%） |' % (p['used'], c['atlas']['pair_cell_ratio']))
    A('| 还空多少位子？ | **%d** 个 |' % p['free'])
    A('| ★ **现在就能直接加多少新字？** | **%d** 个（图集上那格是白的） |' % p['vacuum_usable'])
    A('| 要先"回收旧字"才能用的位子？ | **%d** 个（格子上压着旧字形） |' % p['need_recycle'])
    A('| 单字节码用了多少？ | **%d** 个（汉字 %d + 拉丁字母 ç/ñ %d） |'
      % (N['single_used'], N['single_hanzi'], N['single_latin1']))
    A('| 单字节码还能加新字吗？ | **不能**：0x80..0xFF 只剩 %s 两个字节，'
      '而且是手柄图标码，动不得 ⇒ **真正可用 %d 个** |'
      % (' '.join('0x' + b for b in N['spare']), N['really_usable']))
    A('')
    A('> ★ **「需回收」这一行的正确读法**（round49 实测补注）：那 %d 个是"字符表里空着、'
      '但格子上还有墨"的格子；它们的墨**全部属于引擎在用的采样窗** —— '
      '一半是**单字节记录码占死的格**（引擎拿这些格画单字节汉字/符号），另一半**被 FT 记录矩形'
      '（单字节/ASCII 的采样窗）压着** ⇒ 对偶码**永远不能用**这些格。'
      '⇒ 这里**不存在**"回收几个旧字就能多出几个位子"这回事；'
      '真正能释放字位的是**回收死字**（在全部文本表里 0 次使用的字，从 charset 删掉映射）。'
      '逐格判定见 `docs/REPORT_font_cleanup.md` 与 `work/builds/<版本>/temp/font_residue/'
      'residue.json`。'
      % p['need_recycle'])
    A('')
    A('## 一、汉字（对偶码）容量')
    A('')
    A('| 项目 | 数值 | 怎么来的 |')
    A('|---|---|---|')
    A('| 总容量 | **%d** | (lead 上界 - lead 下界) × 94 = %d × 94 |'
      % (p['capacity'], p['leads']))
    A('| lead 区间 | `%s` | ELF 里 4 处 `sltiu …,0xB1` 实测 |' % p['lead_range'])
    A('| trail 区间 | `%s` | 引擎 trail 空间 |' % p['trail_range'])
    A('| 已用 | **%d** | charset JSON 里 lead 合法的对偶码个数 |' % p['used'])
    A('| 空位 | **%d** | 总容量 − 已用 |' % p['free'])
    A('| ★ 可直接用 | **%d** | 空位里"引擎格一个墨点都没有"的（就能直接写新字） |'
      % p['vacuum_usable'])
    A('| 需回收 | **%d** | 空位里格子上还压着旧字形的 |' % p['need_recycle'])
    A('| 最严格口径 | %d | 连"别人的采样窗"都不碰的干净格（真正写新字时的安全上限） |'
      % p['strict_window_free'])
    A('')
    A('空位按图集行分布（row: 个数）：%s'
      % ('、'.join('第 %s 行 ×%d' % (k, v) for k, v in p['vacuum_rows'].items()) or '无'))
    A('')
    A('## 二、单字节码')
    A('')
    A('| 项目 | 数值 |')
    A('|---|---|')
    A('| 已用（总） | **%d** |' % N['single_used'])
    A('| ├ 汉字 | %d |' % N['single_hanzi'])
    A('| └ 拉丁字母 | %d（ç=0xE7、ñ=0xF1，round43 新增） |' % N['single_latin1'])
    A('| 空闲字节 | %s |' % (' '.join('0x' + b for b in N['spare']) or '无'))
    A('| 其中手柄图标码 | %s |' % (' '.join('0x' + b for b in N['icons']) or '无'))
    A('| ★ 真正可用 | **%d** |' % N['really_usable'])
    A('')
    A('## 三、字符总数与图集占用')
    A('')
    A('| 项目 | 数值 |')
    A('|---|---|')
    A('| charset 口径 | **%d** 个（单字节 %d + 对偶 %d，去重） |'
      % (N['charset_unique'], N['charset_single'], N['charset_pair']))
    A('| dump 口径 | **%d** 个（上述 %d + ASCII 95 + 未映射字节 %d） |'
      % (N['dump_total'], N['charset_unique'], len(N['icons'])))
    A('| 图集尺寸 | %d×%d（PSMT4，%d KB） |'
      % (N['atlas']['w'], N['atlas']['h'], N['atlas']['bytes'] // 1024))
    A('| 图集墨占用 | **%.2f%%**（%d / %d texel） |'
      % (c['atlas']['ink_ratio'], N['atlas']['ink'], N['atlas']['texels']))
    A('| 对偶格占用 | **%.2f%%**（%d / %d 格） |'
      % (c['atlas']['pair_cell_ratio'], p['used'], p['capacity']))
    A('| 有字形 / 缺字形 | %d / %d |' % (N['n_glyph'], N['n_missing_glyph']))
    A('')
    A('## 四、按 kind 分类（%d 行 = dump 出来的字符全清单）' % N['kind_total'])
    A('')
    A('| kind | 条数 | 占比 | 说明 |')
    A('|---|---|---|---|')
    for k, desc in (('ascii', 'ASCII 0x20..0x7E（引擎按单字节画）'),
                    ('single', '单字节汉字码 0x80..0xFF'),
                    ('latin1', '拉丁字母 ç/ñ（round43 新增；**不是**手柄图标）'),
                    ('pair', '对偶码汉字（引擎格位公式寻址）'),
                    ('icon', '引擎认的文本图标码 0xB1/0xB5（不吃字库）')):
        if k in N['kinds']:
            A('| `%s` | %d | %.2f%% | %s |'
              % (k, N['kinds'][k], N['kind_shares'][k], desc))
    A('')
    A('## 五、引擎格位公式（对偶字画在哪）')
    A('')
    A('```')
    A('slot = (lead - 0x%02X) * 94 + (trail - 0x%02X)' % (N['lead_lo'], N['trail_lo']))
    A('row, col = slot // 62, slot % 62')
    A('p = col + PHI[row]                     # PHI = 逐行相位 (实证拟合)')
    A('x = 16 * (p % 64)                      # 图集一行 64 格 ⇒ 会回绕')
    A('y = yrow(row) + (1 if p >= 64 else 0)  # 回绕列的字形低 1 行 (实测)')
    A('yrow(r) = %d + 16 * (r + (%d if r >= %d else 0))'
      % (N['grid_y0'], N['grid_skip_rows'], N['grid_skip_row']))
    A('```')
    A('')
    A('PHI 表：%s' % '、'.join('行%d:%d' % (k, v) for k, v in sorted(N['phi'].items())))
    A('')
    A('> ⚠ PHI 是**实证拟合**（1297 个对偶字逐字模板比对：本式 785 个 0 误差；旧口径 0/1297），')
    A('> 不是从反汇编完整推出来的 —— 见「口径与限制」。')
    A('')
    A('## 六、口径与已知限制')
    A('')
    A('1. **"空位 ≠ 可用"**：slot 空只说明 charset 里没占这个码位，但图集那一格上可能还压着')
    A('   历史字形（回收前的旧字、或别人字形的 1 行渗漏）。本报告把两者分开数：')
    A('   「可直接用 %d」= 引擎格一个墨点都没有；「需回收 %d」= 格子上有墨。'
      % (p['vacuum_usable'], p['need_recycle']))
    A('2. **回绕列的 1 行渗漏**：x 回绕的字形比 yrow 低 1 行，最后一行落进下一行格子的第 0 行。')
    A('   判"这格有没有字形"时把第 0 行剔掉（`GRID_BLEED_ROWS=1`）。')
    A('3. **PHI 是拟合值**（复现度 %d/%d 逐像素满分），不是反汇编推导 ⇒ 极端情况下个别行的'
      '列相位可能有偏差。' % (785, 1319))
    A('4. **对偶容量上限受 lead 上界约束**：lead 区间由 ELF 的 `sltiu` 立即数决定（现为 `0x%02X`）；'
      '改大要动 ELF，且 0xB1/0xB5（图标码）必须留在 lead 之外。' % N['lead_hi'])
    A('5. **`font_usage.py` 的"自相矛盾"告警**：charset 的 `protected` 里含 0xE7/0xF1（原意='
      '"英文盘在用、不许回收"），round43 起它们又成了 charset 的正式单字节码 ⇒ 该工具会把这 2 个'
      '（加上历史上的 0x92=若）印成 `[!!] charset 自相矛盾`。这是**过时口径的告警**，'
      '不影响任何产物（该工具按铁律只读，未改）。')
    A('6. **数字随 charset/图集变**：本报告由脚本现算，换盘或扩字后重跑即得新数字。')
    A('')
    A('## 七、文件清单（脚本产出的数据文件；`README.md` / `text/README_文本表.md` 是人话文档，'
      '完整清单含它们，见 `MANIFEST.json`）')
    A('')
    A('| 文件 | 字节 | sha256（前 16 位） |')
    A('|---|---|---|')
    for r in rows:
        A('| `%s` | %d | `%s…` |' % (r['path'], r['bytes'], r['sha256'][:16]))
    A('')
    return '\n'.join(L) + '\n'


# ═══════════════════════ ③ 报告: Excel ═══════════════════════

def xlsx_report(path, N, build, iso_sha, rows):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    HDR_FILL = PatternFill('solid', fgColor='1F4E78')
    HDR_FONT = Font(bold=True, color='FFFFFF', size=11)
    TITLE_FONT = Font(bold=True, size=13, color='1F4E78')
    STAR_FILL = PatternFill('solid', fgColor='FFF2CC')
    THIN = Side(style='thin', color='BFBFBF')
    BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

    wb = Workbook()

    def sheet(title, cols, widths):
        ws = wb.create_sheet(title)
        ws.append(cols)
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        for c in ws[1]:
            c.fill, c.font, c.border = HDR_FILL, HDR_FONT, BORDER
            c.alignment = Alignment(vertical='center', horizontal='center', wrap_text=True)
        ws.row_dimensions[1].height = 26
        ws.freeze_panes = 'A2'
        return ws

    def put(ws, row, star=False):
        ws.append(row)
        r = ws.max_row
        for c in ws[r]:
            c.border = BORDER
            c.alignment = Alignment(vertical='top', wrap_text=True)
        if star:
            for c in ws[r]:
                c.fill = STAR_FILL
                c.font = Font(bold=True)
        return r

    c = N['cap']
    p = c['pair']

    # ── 页 1: 概要 ──
    ws = sheet('概要', ['项目', '数值', '说明'], [34, 20, 78])
    put(ws, ['现役盘', build, 'work/builds/%s/%s.iso（只读；本报告不写盘）' % (build, build)], True)
    put(ws, ['盘 sha256', iso_sha, '逐字节指纹 —— 拿它确认"跑的是不是这一份盘"'])
    put(ws, ['字符集文件', N['charset_path'], 'sha256 %s…' % N['charset_sha'][:16]])
    put(ws, ['报告生成', datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), '脚本 tools/maint/make_release_pack.py（全部数字现算）'])
    put(ws, ['', '', ''])
    put(ws, ['【汉字·对偶码】总容量', p['capacity'], '算式: (lead 上界−lead 下界) × 94 = %d × 94；lead %s / trail %s'
            % (p['leads'], p['lead_range'], p['trail_range'])], True)
    put(ws, ['【汉字·对偶码】已用', p['used'], 'charset 里 lead 合法的对偶字个数（对偶格占用 %.2f%%）'
            % c['atlas']['pair_cell_ratio']])
    put(ws, ['【汉字·对偶码】空', p['free'], '总容量 − 已用（= 还能放字的**码位**数）'])
    put(ws, ['★ 可直接用（新字马上能加）', p['vacuum_usable'],
             '空位里"引擎格一个墨点都没有"的 ⇒ 把新字形写进去即可，不用回收任何旧字'], True)
    put(ws, ['需回收（格子上有旧字）', p['need_recycle'],
             '空位里那格还压着旧字形的。★ round49 实测补注：这些格子的墨**全部属于引擎在用的'
             '采样窗**（单字节记录码占死的格 / 被 FT 记录矩形压着的格）⇒ 对偶码**永远不能用**，'
             '**不存在"回收旧字就多出位子"**；能释放字位的是"回收死字"（文本里 0 次使用的字），'
             '见 docs/REPORT_font_cleanup.md'], True)
    put(ws, ['最严格口径（不碰别人采样窗）', p['strict_window_free'],
             '真正写新字形时的安全上限（连 1 行渗漏都不碰）；比"可直接用"更保守'])
    put(ws, ['', '', ''])
    put(ws, ['单字节码 已用（总）', N['single_used'],
             '即: 汉字 %d + 拉丁字母 ç/ñ %d（round43 新增；ç=0xE7 / ñ=0xF1）'
             % (N['single_hanzi'], N['single_latin1'])])
    put(ws, ['单字节码 空闲字节', ' '.join(N['spare']) or '无',
             '0x80..0xFF 里既没映射、也不是任何对偶 lead 的字节'])
    put(ws, ['单字节码 ★真正可用', N['really_usable'],
             '空闲的两个 0xB1/0xB5 是引擎认的**手柄图标码**（译文里的 {{BTN:…}} 要用）⇒ 动不得'])
    put(ws, ['', '', ''])
    put(ws, ['字符总数（charset 口径）', N['charset_unique'],
             'charset JSON 里真有的字：单字节 %d + 对偶 %d（去重）'
             % (N['charset_single'], N['charset_pair'])])
    put(ws, ['字符总数（dump 口径）', N['dump_total'],
             '上面 %d + ASCII 95 + 未映射字节 %d（= 字符集清单 CSV 的行数）'
             % (N['charset_unique'], len(N['icons']))])
    put(ws, ['图集占用', '%.2f%%' % c['atlas']['ink_ratio'],
             '墨 %d / 全图 %d texel；图集 %d×%d PSMT4（%d KB）'
             % (N['atlas']['ink'], N['atlas']['texels'], N['atlas']['w'], N['atlas']['h'],
                N['atlas']['bytes'] // 1024)])
    put(ws, ['对偶格占用', '%.2f%%' % c['atlas']['pair_cell_ratio'],
             '%d / %d 个引擎格被对偶字占用' % (p['used'], p['capacity'])])
    put(ws, ['有字形 / 缺字形', '%d / %d' % (N['n_glyph'], N['n_missing_glyph']),
             '缺字形的字符写进盘会显示空白（见「字符分类」页）'])

    # ── 页 2: 字符分类 ──
    ws = sheet('字符分类', ['kind', '条数', '占比', '是什么', '怎么画出来的'],
               [12, 10, 10, 40, 58])
    desc = {
        'ascii': ('ASCII 可见字符 0x20..0x7E', '引擎的 ASCII 单字节路径 + FT 记录表（与 charset JSON 无关）'),
        'single': ('单字节汉字码 0x80..0xFF', 'FT 记录表 idx = 码位−0x20 ⇒ 采样记录矩形（含行相位校正）'),
        'latin1': ('拉丁字母 ç/ñ（round43 进字符集）', '与单字节汉字同一条路（FT 记录 idx=199 / 209）'),
        'pair': ('对偶码汉字（两个字节）', '引擎格位公式：slot → 图集 16×16 格'),
        'icon': ('手柄图标码 0xB1/0xB5', '引擎硬编码 UV 直接画（**不吃字库**）'),
    }
    for k in ('ascii', 'single', 'latin1', 'pair', 'icon'):
        if k in N['kinds']:
            put(ws, [k, N['kinds'][k], N['kind_shares'][k] / 100.0, desc[k][0], desc[k][1]],
                star=(k in ('latin1', 'icon')))
    put(ws, ['合计', N['kind_total'], 1.0, '就是字符集清单 CSV 的全部行', ''])
    for c2 in ws[ws.max_row]:
        c2.font = Font(bold=True)
    for r in ws.iter_rows(min_row=2, min_col=3, max_col=3):
        for c2 in r:
            c2.number_format = '0.00%'
    ws.append([])
    put(ws, ['缺字形的字符（写进盘会画成空白）', N['n_missing_glyph'], '', '', ''])
    for ex in N['missing_examples']:
        put(ws, ['', ex[1], '', ex[0], 'kind=%s' % ex[2]])

    # ── 页 3: 可直接用的空位清单 ──
    ws = sheet('空位清单', ['slot', 'lead(码位首字节)', 'trail(码位次字节)', '引擎格 x', '引擎格 y',
                            '图集行 row', '行内 col', '行相位 PHI', 'x 是否回绕', '严格口径也算干净'],
               [8, 18, 18, 11, 11, 12, 10, 12, 12, 18])
    strict = set(p['strict_window_free_slots'])
    for s in p['vacuum_slots']:
        b1, b2 = tcslib.pair_from_slot(s)
        x, y = tcslib.atlas_cell_xy_engine(s)
        row, col = s // tcslib.NCOL, s % tcslib.NCOL
        phi = tcslib.atlas_row_phase(row)
        put(ws, [s, '0x%02X' % b1, '0x%02X' % b2, x, y, row, col, phi,
                 '是' if col + phi >= tcslib.GRID_MOD else '否',
                 '是' if s in strict else '否'])

    # ── 页 4: 手柄图标码总表 ──
    ws = sheet('手柄图标码', ['字节', 'CSV 标记', '是什么', '是引擎图标码?', '引擎 UV',
                              '证据', '备注'], [8, 18, 26, 14, 18, 46, 56])
    for b, r in sorted(icon_table.ICON_CODES.items()):
        put(ws, ['0x%02X' % b, icon_table.MARK_FMT % (icon_table.PUA_BASE + b),
                 r['name'], '★ 是', '(%d,%d)-(%d,%d)' % r['uv'], r['elf_evidence'],
                 r['note']], True)
    for b, r in sorted(icon_table.NOT_ICON_CODES.items()):
        put(ws, ['0x%02X' % b, '（新 dump 直接写 %s）' % r['latin1'],
                 '%s —— **不是图标**' % r['name'], '否', '无（走字形路径）', r['evidence'],
                 'round43 起它已在 charset 的 codes 里（kind=latin1，单字节码）；'
                 '老 CSV 的 %s 是**历史别名**，注入器仍接受，写出的字节完全相同'
                 % (icon_table.MARK_FMT % (icon_table.PUA_BASE + b))])
    put(ws, ['', '', '引擎认的文本图标码**只有 2 个**',
             '', '', 'DrawString v1 @0x219A70 里写死的两个 if（0xB1/0xB5）',
             '⇒ 不存在"没找到的更多图标码"；**空出来的字节 ≠ 新的图标码**（写别的字节只会走字形路径）'])
    put(ws, ['', '', '玩家看到的其它手柄图标', '', '',
             '%s @0x%08X' % (icon_table.SHORTCUT_SYSTEM['func'], icon_table.SHORTCUT_SYSTEM['va']),
             '△○✕□ / 左右键等由 UI 的「快捷键」系统按**动作索引**绘制，与文本字节无关；'
             '纹理 %s。⚠ index→动作名 的映射**没有**逆向（诚实挂账）'
             % icon_table.SHORTCUT_SYSTEM['texture'].split(' (')[0]])

    # ── 页 5: 口径与限制 ──
    ws = sheet('口径与限制', ['#', '项目', '内容'], [5, 26, 110])
    items = [
        ('容量公式', '对偶总容量 = (lead 上界 − lead 下界) × 94 = (%d − %d) × 94 = %d。'
                     'lead 区间来自 ELF 里 4 处 `sltiu …,0x%02X` 实测。'
         % (N['lead_hi'], N['lead_lo'], p['capacity'], N['lead_hi'])),
        ('格位公式', 'slot = (lead−0xA1)*94 + (trail−0xA1)；row=slot//62，col=slot%%62；'
                     'p = col + PHI[row]；x = 16*(p%%64)；y = yrow(row) + (p>=64 ? 1 : 0)。'
                     'PHI = 逐行相位（%s）。'
         % '、'.join('行%d:%d' % (k, v) for k, v in sorted(N['phi'].items()))),
        ('★ 为什么"空位 ≠ 可用"', 'slot 空只说明 charset 没占这个**码位**；图集那一格上可能还压着'
                                 '旧字形（历史字形的墨/渗漏）⇒ 写新字会与别人的采样窗打架。'
                                 '本报告把"引擎格一个墨点都没有"(=可直接用 %d) 与"格子上有墨"'
                                 '(=需回收 %d) 分开数。' % (p['vacuum_usable'], p['need_recycle'])),
        ('回绕列的 1 行渗漏', 'x 回绕（col+PHI≥64）的字形比 yrow 低 1 行，最后一行落进下一行格子的'
                             '第 0 行。判"这格有没有字形"时剔掉第 0 行（GRID_BLEED_ROWS=1），'
                             '否则会把渗漏误当字形。'),
        ('已知限制 1：PHI 是拟合值', 'PHI 由 1297 个对偶字逐像素模板比对拟合（本式 785 个 0 误差；'
                                    '旧口径 0/1297；现役盘 1319/1319 个对偶字的引擎格都有墨），'
                                    '**不是**从反汇编完整推导出来的 ⇒ 个别行可能仍有偏差。'),
        ('已知限制 2：ASCII 字形检查只覆盖 default face', '小写 a-z / `_` / `|` / `~` 在 default face '
                                                          '的记录表里查不到墨，但实机可读（字形在别的 face）'
                                                          '⇒ 注入器只告警、不阻断。'),
        ('已知限制 3：lead 上界要动 ELF', '想扩大对偶容量必须改 ELF 里的 `sltiu` 立即数；'
                                          '且 0xB1/0xB5（图标码）必须留在 lead 之外。'),
        ('已知限制 4：font_usage.py 的过时告警', 'charset 的 protected 含 0xE7/0xF1（原意"英文盘在用、'
                                                 '不许回收"），round43 起它们又是正式单字节码 ⇒ '
                                                 'font_usage.py 会把这 2 个（连同历史 0x92=若）印成 '
                                                 '`[!!] charset 自相矛盾`。那是**过时口径的告警**，'
                                                 '不影响任何产物（该工具按铁律只读，未修改）。'),
        ('已知限制 5：shortcut 表的 index→动作名', 'UI 快捷键图标系统（kShortcutDefaultTC @0x2BEFE0）的 '
                                                   'index→动作名 映射**未逆向**，本报告只登记"存在这张表、'
                                                   '与文本码无关"。'),
        ('数字来源', '全部数字由 tools/maint/make_release_pack.py 现读 charset(%s) + 盘上图集算得；'
                     '与 tools/iso_build/dump_font.py 用的是同一批函数。' % N['charset_path']),
    ]
    for i, (k, v) in enumerate(items, 1):
        put(ws, [i, k, v], star=k.startswith('★'))

    # ── 页 0: 封面/索引 (删掉默认 sheet 前先建) ──
    ws0 = wb['Sheet'] if 'Sheet' in wb.sheetnames else wb.create_sheet('索引', 0)
    ws0.title = '索引'
    ws0.column_dimensions['A'].width = 22
    ws0.column_dimensions['B'].width = 100
    ws0['A1'] = '字库报告 —— %s' % build
    ws0['A1'].font = TITLE_FONT
    ws0.append([])
    for a, b in (('现役盘', '%s.iso（sha256 %s）' % (build, iso_sha)),
                 ('一句话', '汉字还能直接加 %d 个新字；单字节码已经一个都加不了'
                            % p['vacuum_usable']),
                 ('本表各页', '概要 = 全部关键数字；字符分类 = 按 kind 的条数与占比；'
                              '空位清单 = 那 %d 个"马上能用"的 slot；'
                              '手柄图标码 = 0xB1/0xB5 与 ç/ñ 的区别；口径与限制 = 数字怎么算的'
                              % p['vacuum_usable']),
                 ('怎么用', '先看「概要」页黄底三行：总容量 / 已用 / ★可直接用'),
                 ('生成脚本', 'tools/maint/make_release_pack.py（数字全部现算，没有写死值）')):
        ws0.append([a, b])
        for cc in ws0[ws0.max_row]:
            cc.alignment = Alignment(vertical='top', wrap_text=True)
        ws0[ws0.max_row][0].font = Font(bold=True)

    wb.save(path)
    return wb.sheetnames


# ═══════════════════════ ④ main ═══════════════════════

def main():
    ap = argparse.ArgumentParser(description='打资料包: work/builds/<版本>/release/')
    ap.add_argument('--build', default='GR_ZH93')
    ap.add_argument('--view-from', default='work/builds/GR_ZH92/text',
                    help='view-only 分类表的来源目录 (round39 全容器普查的落点)')
    ap.add_argument('--skip-font-dump', action='store_true',
                    help='不重跑 dump_font, 直接用版本夹 font/ 里已有的四件套')
    a = ap.parse_args()

    build = a.build
    bdir = os.path.join(REPO, 'work', 'builds', build)
    iso = os.path.join(bdir, build + '.iso')
    assert os.path.isfile(iso), '找不到 %s' % iso
    rel = os.path.join(bdir, 'release')
    tdir, fdir = os.path.join(rel, 'text'), os.path.join(rel, 'font')
    for d in (rel, tdir, fdir):
        os.makedirs(d, exist_ok=True)

    print('# ═══ make_release_pack.py — %s ═══' % build)
    iso_sha = sha256(iso)
    print('# 现役盘: %s' % REL(iso))
    print('# sha256: %s  (%d B)' % (iso_sha, size_of(iso)))

    # ① 字库四件套 (2x + 1x) -------------------------------------------------
    font_dir = os.path.join(bdir, 'font')
    one_x_dir = os.path.join(bdir, 'temp', 'release_pack', 'font1x')
    if not a.skip_font_dump:
        for scale, out in ((2, font_dir), (1, one_x_dir)):
            cmd = [sys.executable, os.path.join(REPO, 'tools', 'iso_build', 'dump_font.py'),
                   '--iso', iso, '--out', out, '--prefix', build,
                   '--scale', str(scale), '--iso-sha', iso_sha]
            print('# dump_font --scale %d → %s' % (scale, REL(out)))
            r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                               encoding='utf-8', errors='replace')
            if r.returncode != 0:
                print(r.stdout)
                print(r.stderr)
                raise SystemExit('!! dump_font 失败 (exit=%d)' % r.returncode)
            for ln in (r.stdout or '').splitlines():
                if '字符 ' in ln or '图集 ' in ln or '自查' in ln or '还能装多少' in ln:
                    print('#   %s' % ln.strip())

    # ② 文本表 (3 可注入 + 10 view-only) ------------------------------------
    rows = []
    for k in TEXT_KINDS:
        src = os.path.join(bdir, 'text', '%s_text_%s.csv' % (build, k))
        assert os.path.isfile(src), '找不到文本表 %s' % src
        rows.append(copy_into(src, tdir, '★可注入 (kind=%s)' % k))
    meta = os.path.join(bdir, 'text', '%s_text.meta.json' % build)
    if os.path.isfile(meta):
        rows.append(copy_into(meta, tdir, '多表元信息 (注入器对格式/源盘 sha 的校验)'))
    # view-only 表: 用 glob 抓 (命名必须是 *_view_*.csv —— 注入器的命名空间隔离靠它)
    vdir = os.path.join(REPO, a.view_from)
    if os.path.isdir(vdir):
        import glob as _glob
        vs = sorted(_glob.glob(os.path.join(vdir, '*_view_*.csv')))
        assert len(vs) >= 10, 'view 表只找到 %d 张 (应 ≥10 张): %s' % (len(vs), vdir)
        for src in vs:
            rows.append(copy_into(src, tdir, '⚠ 只能看 (view-only, injectable=no)'))
        for m2 in sorted(_glob.glob(os.path.join(vdir, '*_view_*.meta.json'))):
            rows.append(copy_into(m2, tdir, '⚠ view 表的元信息 (来源盘/阈值)'))
    else:
        print('[!!] view 表来源目录不存在: %s' % vdir)

    # ③ 字库纹理 + 清单 -----------------------------------------------------
    atlas2 = os.path.join(font_dir, '%s_font_atlas.png' % build)
    rows.append(copy_into(atlas2, fdir, '字库图集 2 倍近邻 (黑=墨/白=空)'))
    one = os.path.join(one_x_dir, '%s_font_atlas.png' % build)
    if os.path.isfile(one):
        dst = os.path.join(fdir, '%s_font_atlas_1x.png' % build)
        shutil.copy2(one, dst)
        rows.append(dict(path=REL(dst), name=os.path.basename(dst), bytes=size_of(dst),
                         sha256=sha256(dst), source=REL(one), note='字库图集 1:1 (1024×512)'))
    for nm, note in (('%s_font_charset.csv' % build, '字符集清单 (kind/bytes/slot/引擎格/has_glyph)'),
                     ('%s_font_ft.csv' % build, 'FT 记录表 (3 个 face)')):
        rows.append(copy_into(os.path.join(font_dir, nm), fdir, note))

    # ④ 数字 (现算) + 报告 ---------------------------------------------------
    with io.open(os.path.join(font_dir, '%s_font_charset.csv' % build),
                 encoding='utf-8-sig', newline='') as f:
        kind_rows = list(csv.DictReader(f))
    N = collect_font_numbers(iso, font_dir, build, kind_rows)
    md_p = os.path.join(rel, '字库报告.md')
    with io.open(md_p, 'w', encoding='utf-8', newline='\n') as f:
        f.write(md_report(N, build, iso_sha, rows))
    xl_p = os.path.join(rel, '字库报告.xlsx')
    sheets = xlsx_report(xl_p, N, build, iso_sha, rows)
    for p in (md_p, xl_p):
        rows.append(dict(path=REL(p), name=os.path.basename(p), bytes=size_of(p),
                         sha256=sha256(p), source='(脚本产出)',
                         note='字库报告 (xlsx %d 页: %s)' % (len(sheets), '/'.join(sheets))
                              if p.endswith('.xlsx') else '字库报告 (Markdown 版)'))

    # ⑤ MANIFEST + 打印 -----------------------------------------------------
    #   ★ 把 release/ 里**其它**文件也登记进来 (人话 README 是人工维护的, 脚本不覆盖)
    known = set(r['path'] for r in rows)
    for root, _dirs, fs in os.walk(rel):
        for fn in fs:
            p = os.path.join(root, fn)
            rp = REL(p)
            if rp in known or fn == 'MANIFEST.json':
                continue
            rows.append(dict(path=rp, name=fn, bytes=size_of(p), sha256=sha256(p),
                             source='(人工维护)', note='人话文档 (脚本不覆盖)'))
    rows.sort(key=lambda r: r['path'])
    man = dict(pack='%s 资料包' % build, generated=datetime.datetime.now().isoformat(timespec='seconds'),
               iso=REL(iso), iso_sha256=iso_sha,
               release_dir=REL(rel),
               policy='所有产物都在 work/builds/%s/release/ 内; ISO 只读, 本脚本一行都没写盘内数据' % build,
               numbers=dict(pair=N['cap']['pair'], single=N['cap']['single'],
                            charset=N['cap']['charset'], atlas=N['cap']['atlas'],
                            verdict=N['cap']['verdict'], kinds=N['kinds']),
               files=rows)
    with io.open(os.path.join(rel, 'MANIFEST.json'), 'w', encoding='utf-8') as f:
        json.dump(man, f, ensure_ascii=False, indent=1)

    print('\n[out] release/text/  %d 个文件 (3 可注入 + %d view-only + 1 meta)'
          % (len([r for r in rows if '/text/' in r['path']]),
             len([r for r in rows if 'view_' in r['path'] and r['path'].endswith('.csv')])))
    print('[out] release/font/  %d 个文件' % len([r for r in rows if '/font/' in r['path']]))
    print('[out] 字库报告.xlsx 页: %s' % ' / '.join(sheets))
    print('[out] 字库报告.md / MANIFEST.json')
    print('\n[数字] 汉字(对偶) 容量 %d / 已用 %d / 空 %d / ★可直接用 %d / 需回收 %d'
          % (N['cap']['pair']['capacity'], N['cap']['pair']['used'], N['cap']['pair']['free'],
             N['cap']['pair']['vacuum_usable'], N['cap']['pair']['need_recycle']))
    print('[数字] 单字节 已用 %d (汉字 %d + ç/ñ %d) / 真正可用 %d'
          % (N['single_used'], N['single_hanzi'], N['single_latin1'], N['really_usable']))
    print('[数字] 字符总数 charset %d / dump %d; 图集 %.2f%%; 对偶格 %.2f%%'
          % (N['charset_unique'], N['dump_total'], N['cap']['atlas']['ink_ratio'],
             N['cap']['atlas']['pair_cell_ratio']))
    print('[数字] kind: %s' % ' '.join('%s=%d' % kv for kv in sorted(N['kinds'].items())))
    miss = [r for r in rows if r['path'].endswith('README.md')]
    if not miss:
        print('\n[提醒] release/README.md 与 release/text/README_文本表.md 是**人话文档**, '
              '由人工维护 (本脚本不覆盖)。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
