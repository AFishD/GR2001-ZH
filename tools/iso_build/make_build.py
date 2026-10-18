# -*- coding: utf-8 -*-
r"""make_build.py — 一次性版本构筑器 (work/builds/<版本>/)

用法:
  python tools/iso_build/make_build.py GR_ZH63                                   # 基底=最新构筑, 原样继承
  python tools/iso_build/make_build.py GR_ZH63 --patch my_patch.py               # 继承后应用补丁 (python <patch> <src_iso> <dst_iso>)
  python tools/iso_build/make_build.py GR_ZH63 --from work/builds/GR_ZH62        # 指定基底
  python tools/iso_build/make_build.py GR_ZH63 --inject-csv work/builds/GR_ZH62/text/GR_ZH62_text.csv
  python tools/iso_build/make_build.py GR_ZH63 --inject-csv GR_ZH62              # 也可只给版本名 (自动找它的文本 CSV)
  python tools/iso_build/make_build.py GR_ZH63 --no-font-dump                    # 跳过「版本字库 dump」
  python tools/iso_build/make_build.py GR_ZH63 --no-text-snapshot                # 跳过「版本文本副本」
  python tools/iso_build/make_build.py GR_ZH63 --no-textdump                     # 跳过文本总表

基底解析顺序: --from > work/builds/ 下版本号最大者 > work/build/iso/GR_ZH*.iso (旧位置)。

★ 产物布局 (一切都在版本文件夹内; 构筑**不往 work/ 其它地方写任何东西**):
  work/builds/<版本>/
    <版本>.iso                   完整盘
    build_info.json              版本/基底/补丁/sha256/时间 + text_snapshot + font_dump
    text/                        本版本文本快照 (每次构筑自动产出; --no-text-snapshot 可关)
      <版本>_text_long.csv       ★ 长段 (可写 {WRAP} 控制断点) —— 人工在 Excel 里改这些表
      <版本>_text_long_nowrap.csv  语言表长段 (简报等; 折行宽度未标定)
      <版本>_text_short.csv      按钮 / 条目名 / 短提示
      <版本>_text.txt            合并的一份轻量副本: 每行 `id<TAB>正文` (换行 \n)
      <版本>_text.meta.json      各表的条数 / kind 列表 / 总条数 / sha256
      ★ round37: 文本表**按 kind 分类成多张** (每张 16 列, 表头不变); **不再产出合并的大 CSV**
    font/                        本版本字库 dump (每次构筑默认产出; --no-font-dump 可关)
      <版本>_font_atlas.png      图集可视化 (0=墨 / 非 0=空; 默认 2 倍最近邻放大)
      <版本>_font_ft.csv         FT 记录表 (face/码位/矩形/采样点/有没有墨)
      <版本>_font_charset.csv    字符集清单 (字符/编码/网格格/有没有字形)
      <版本>_font_summary.json   统计 + 各文件 sha256 (无时间戳 ⇒ 同盘两次 dump 完全相同)
    temp/                        注入报告 + 全量文本总表 + 模拟器测试都落这里
      inject<N>_report.json      --inject-csv 第 N 步的注入报告 (含「字库覆盖预检」)
      textdump/all_text.xlsx     全量文本总表 (每次构筑自动产出)
      textdump/all_text.csv      同上 CSV 版 (供脚本消费)
    extract/ft_font_res.bin      字表 (MENU.IMG @0xB9120, 4421B)
    extract/font_new_font_revised.bin  字库纹理 PAK 记录 (MENU.IMG @0x58431, 0x4044C)
    extract/MENU.IMG             文本/UI 容器全量 (58MB; 文本在压缩 RES 内, 用 hanliu 工具解码)

  ⚠ 本轮起**不再**写 work/text_versions/** (旧的文本归档目录) 与 work/tmp/** (旧临时目录):
    版本快照一律留在版本文件夹里, 版本之间对比用
    `python tools/text_csv/diff_text_versions.py <版本A> <版本B>` (它在版本文件夹里找快照)。

★ 版本文本副本 (每次构筑默认产出, --no-text-snapshot 可关):
  ① 对该**刚产出的 ISO 本身**跑一次 tools/text_csv/dump_text_csv.py (2261 条, 约 2 秒);
  ② 产出 text/<版本>_text_<kind>.csv —— ★ round37 起**按 kind 分类的多张表**
     (long / long_nowrap / short …, 每张仍是 16 列, 表头与原大表完全相同);
     不再产出合并的大 CSV (免得"改了一张、另一张没改");
  ③ 产出 text/<版本>_text.txt —— **合并成一份**的轻量单行副本 (`id<TAB>正文`, 便于 diff);
  ④ 结果写进 build_info.json 的 text_snapshot 字段 (各表路径/sha256 + 条目数/长段数/字符数)。

★ 版本字库 dump (每次构筑默认产出, --no-font-dump 可关; 实现在 tools/iso_build/dump_font.py):
  从**刚产出的 ISO 本身**只读导出 font/ 下四件套:
    _font_atlas.png     图集 1024×512 按 0=墨/非 0=空 二值化 (默认 2 倍最近邻放大)
    _font_ft.csv        FT 记录表 (3 个 face 全部记录; has_ink=0 ⇒ 该码位画不出来)
    _font_charset.csv   本盘字符集清单 (ascii/single/pair/icon; has_glyph=0 ⇒ 缺字形)
    _font_summary.json  统计 + 各文件 sha256 (不含时间戳 ⇒ 同一 ISO dump 两次字节相同)
  全部解析口径复用 tools/text_csv/tcslib.py (FT/PAK 解析、网格公式、字形检查), 不重新逆向。

★ 注入是构筑的一等步骤 (--inject-csv, 可多次):
  patch → 顺序执行每个 --inject-csv (inject_text_csv.py --src <上一步产物> --dst <下一步产物>)
  ⇒ 与 tools/text_csv/FORMAT.md 的「dump → 人工改 text_edited → 注入」完全同一条路径。
  ★ round37: 每个 --inject-csv 可以给**目录** (推荐 —— 会把该目录下所有 *_text_*.csv
    全部读入, 以后多了新的 kind 也不会漏), 也可以给**多个表文件** (--csv 可多次)。
  注入失败 (尤其**字库覆盖预检 exit=3 缺字**) ⇒ **构筑立即失败 (非 0 退出)**,
  注入器的完整报告原样打进构筑日志 (不静默继续, 不产出"像是成功"的最终盘)。
  改文案的标准姿势: 改本版本自动产出的 text/<版本>_text_<kind>.csv 的 text_edited 列
  → 下一轮 --inject-csv 那个 text/ 目录。

★ round46: **字库紧凑重排** 是构筑的自动步骤 (默认开启, `--no-font-repack` 关闭):
  位置 = patch/--expand-entry **之后**、文本注入**之前**; 实现在 tools/iso_build/repack_font.py。
  它把当前在用的字形按确定性顺序 (当前槽位升序 = 图集行主序) 紧凑搬到最前面的**可用格**,
  其余可用格一律清零 ("未使用区域置零"), 并同步 charset JSON + 顺手治"某字被别的
  图案污染"这类问题:
    · **可用格** = 1504 对偶槽 − 被单字节/手柄图标记录码占死的格 − 被 FT 记录矩形
      (单字节 / ASCII 的采样窗) 压着的格;  **剩余容量 = 可用格 − 在用字形**;
    · 重排改了「字节↔字符」映射 ⇒ 盘上所有旧编码文本必须**整体重编码**。做法: 把每份
      `--inject-csv` 表拷一份、**只清 `text_zh` 列**(用户译文 `text_edited` 一字不动)
      ⇒ 注入器认为每行都被人工改过 ⇒ 用新 charset 重编。这一步由本构筑器自动做,
      注入时自动换成那份副本 (用户命令行**不用改**)。
    · **0 改动时什么都不做** (不改 ISO / 不改 charset / 不出重编码表) ⇒ 产物 sha256 与基底
      完全相同 (幂等);
    · 有改动但**一个 `--inject-csv` 都没给** ⇒ 直接失败 (exit 4) 且**不改任何文件** ——
      否则盘上文本会整段乱码 (历史教训见 docs/REPORT_font_repack.md)。
    · 产物与日志: <版本>/temp/font_repack/{repack_report.json, repack_moves.json,
      repack.log, reencode/inject<N>/}; build_info.json 里有 font_repack 一段。

★ 全量文本总表 (每次构筑默认产出):
  调用 tools/diag/dump_all_text.py 遍历本盘六类文本来源, 与参考盘 (默认 GR_EN_ORIG) 逐条
  并列对照, 再经 tools/diag/text_table_xlsx.py 渲染成多 sheet Excel:
    总览 / 全部文本 / MENU:RES / GR:RES / MENU:SF / MENU:TXT / GR:ATR
  关闭: --no-textdump; 单独重跑: python tools/diag/dump_all_text.py <iso>

布局常数 (MENU.IMG 内, 全版本稳定, 见 docs/BUILD_MANIFEST.md):
  MENU_LBA=776286, 字库记录 @0x58431 (0x4044C), 字表槽 @0xB9120 (4421B)
"""
import argparse, hashlib, io, json, os, re, shutil, struct, subprocess, sys, time

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
BUILDS = os.path.join(REPO, 'work', 'builds')
LEGACY = os.path.join(REPO, 'work', 'build', 'iso')
DUMP_ALL_TEXT = os.path.join(REPO, 'tools', 'diag', 'dump_all_text.py')
TEXT_XLSX = os.path.join(REPO, 'tools', 'diag', 'text_table_xlsx.py')
# ★ 文本 dump / 注入 / 字库 dump 工具 (只调用/复用, 不修改文本工具本体)
DUMP_TEXT_CSV = os.path.join(REPO, 'tools', 'text_csv', 'dump_text_csv.py')
INJECT_TEXT_CSV = os.path.join(REPO, 'tools', 'text_csv', 'inject_text_csv.py')
# ★ round46: 字库紧凑重排 (每轮构筑自动跑; 文本注入**之前**)
REPACK_FONT = os.path.join(REPO, 'tools', 'iso_build', 'repack_font.py')
# ★ round56: 字库紧凑重排 + **全盘重编码** (取代 repack_font 成为默认; 旧工具保留)
FONT_COMPACT = os.path.join(REPO, 'tools', 'iso_build', 'font_compact.py')
MENU_LBA, MENU_SIZE = 776286, 58300882
GR_LBA, GR_SIZE = 19175, 1550563328
OFF_FT, OFF_REC = 0xB9120, 0x58431
REC_LEN = 0x4147D - 0x1031

try:                                        # 中文输出在重定向/管道下也要可读
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:                                                    # noqa: BLE001
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
from iso_tools import img_expand, img_entry, img_names, TAB_OFF, TAB_STEP  # noqa: E402
import dump_font                                                          # noqa: E402
import tcslib                                                             # noqa: E402
import repack_font                                                        # noqa: E402
import font_compact                                                       # noqa: E402


def verify_img(iso, lba, total, tag):
    """校验 IMG 条目表自洽性: 越界 / 重叠 / 对齐

    ★ IMG 条目只需 4 字节对齐 (实测 4070/4070 GR.IMG 条目都是 4 对齐,
      只有 4.8% 是 2048 对齐) ⇒ 不要用 2048 对齐去浪费 2044 B 的空隙。
    """
    d = open(iso, 'rb').read()
    base = lba * 2048
    names = img_names(d, lba)
    ents = []
    for i in range(len(names)):
        e = list(struct.unpack_from('<12I', d, base + TAB_OFF + TAB_STEP * i))
        ents.append((names[i], e[6], e[7], e[8]))
    bad_oob = [(n, o, s) for n, s, r, o in ents if o and (o + s > total or o % 4)]
    spans = sorted((o, o + s, n) for n, s, r, o in ents if o)
    ov = []
    for k in range(1, len(spans)):
        if spans[k][0] < spans[k - 1][1]:
            ov.append((spans[k - 1][2], spans[k][2]))
    nz = sum(1 for n, s, r, o in ents if o)
    print('[verify] %s: %d 条目 (%d 有数据), 越界/未对齐 %d, 重叠 %d'
          % (tag, len(ents), nz, len(bad_oob), len(ov)))
    for x in bad_oob[:5]:
        print('   越界/未对齐: %s off=%d stored=%d' % x)
    for x in ov[:5]:
        print('   重叠: %s ∩ %s' % x)
    return not bad_oob and not ov


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def latest_build():
    best = (-1, None)
    if os.path.isdir(BUILDS):
        for d in os.listdir(BUILDS):
            m = re.fullmatch(r'GR_ZH(\d+)', d)
            if m and os.path.isfile(os.path.join(BUILDS, d, d + '.iso')):
                best = max(best, (int(m.group(1)), os.path.join(BUILDS, d)))
    if best[1] is None and os.path.isdir(LEGACY):
        for d in os.listdir(LEGACY):
            m = re.fullmatch(r'GR_ZH(\d+)\.iso', d)
            if m:
                best = max(best, (int(m.group(1)), LEGACY))
    return best[1]


# ═════════════════ 版本文本副本 / 字库 dump / 注入 (产物只在版本文件夹内) ═════════════════

class SnapshotError(Exception):
    """版本文本副本产出失败 —— 构筑算失败 (但不影响已产出的 ISO)。"""


def rel(p):
    """仓库内相对路径 (正斜杠): 写进 json/md 给人看, 也便于跨机搬运。"""
    try:
        r = os.path.relpath(p, REPO)
    except ValueError:
        return p
    return r.replace('\\', '/') if not r.startswith('..') else p.replace('\\', '/')


def resolve_repo_path(p):
    """先把参数当 CWD 相对路径, 再当仓库相对路径。"""
    if os.path.isabs(p) and os.path.exists(p):
        return p
    if os.path.exists(p):
        return os.path.abspath(p)
    q = os.path.join(REPO, p)
    return q if os.path.exists(q) else os.path.abspath(p)


def _has_text_tables(d):
    """目录 d 里有没有可注入的文本表 (多表 `*_text_*.csv` 或老的合并大表 `*_text.csv`)。"""
    if not os.path.isdir(d):
        return False
    for f in os.listdir(d):
        if f.lower().endswith('.csv') and (
                tcslib.is_table_csv(f) or f.lower().endswith('_text.csv')):
            return True
    return False


def resolve_inject_input(spec):
    """把 `--inject-csv` 的参数解析成 inject_text_csv.py 能直接吃的**路径** (目录或文件)。

    依次尝试 (只读):
      ① 直接给的文件 / 目录 (CWD 相对 / 仓库相对 / 绝对); 目录里没表就再看它的 `text/`;
      ② `work/builds/<版本>/text`                  ← ★ 本轮正式位置 (**多表目录**, 推荐)
      ③ `work/builds/<版本>/text/<版本>_text.csv`   ← 老布局的合并大表 (兼容)
      ④ `work/builds/<版本>/<版本>_text.csv`        ← 更旧的布局
      ⑤ `work/text_versions/<版本>_text.csv`        ← 更早的归档 (只读兜底)
    ★ 多表目录优先: 这样以后 dump 又多出新的 kind, 也会被自动读进去 (不用改命令)。
    """
    p = resolve_repo_path(spec)
    if os.path.isdir(p):
        for cand in (p, os.path.join(p, 'text')):
            if _has_text_tables(cand):
                return cand
        return p                                   # 让注入器自己报"目录里没有多表"
    if os.path.isfile(p):
        return p
    name = os.path.basename(os.path.abspath(spec).rstrip('\\/'))
    tdir = os.path.join(BUILDS, name, 'text')
    for cand in (tdir,
                 os.path.join(tdir, name + '_text.csv'),
                 os.path.join(BUILDS, name, name + '_text.csv'),
                 os.path.join(REPO, 'work', 'text_versions', name + '_text.csv')):
        if os.path.isdir(cand) or os.path.isfile(cand):
            return cand
    return None


def run_live(cmd, tag):
    """跑子进程并把它**原样逐行转播**到构筑日志, 同时收集输出。

    ★ 注入器的「字库覆盖预检」报告必须原样出现在构筑日志里 (尤其是失败时),
      所以这里绝不能 capture 完就丢掉 —— 边跑边打, 最后再把全文返回。
    ★ 子进程一律加 `-u`: 否则它的 stdout 是管道 ⇒ 8 KB 块缓冲, 报告会憋到最后才出。
    返回 (returncode, 全部输出文本)。
    """
    cmd = cmd[:1] + ['-u'] + cmd[1:]                 # 子进程无缓冲 ⇒ 报告实时可见
    print('\n──── [%s] %s' % (tag, ' '.join('"%s"' % c if ' ' in c else c for c in cmd[1:])))
    sys.stdout.flush()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding='utf-8', errors='replace', bufsize=1)
    lines = []
    for line in p.stdout:
        line = line.rstrip('\r\n')
        lines.append(line)
        print(line)
    p.wait()
    return p.returncode, '\n'.join(lines)


def cjk_count(s):
    """中文字符数 (只算基本汉字区 U+4E00..U+9FFF, 与工程其它统计口径一致)。"""
    return sum(1 for c in s if '\u4e00' <= c <= '\u9fff')


def read_text_tables(tdir, ver):
    """读版本文件夹 text/ 里的**多张表**并合并成一份行表 (round37)。

    返回 ``(rows, tables, report)``; rows = [dict(id, resource, kind, container, text)]。
    ★ 多表口径全部复用 tcslib (与 dump / 注入器同一个实现):
       `expand_csv_inputs` → `read_table_rows` → `merge_table_rows`。
    """
    paths, notes = tcslib.expand_csv_inputs([tdir])
    errs = [n for n in notes if n['level'] == 'error']
    if errs or not paths:
        raise SnapshotError('text/ 里没有可读的多表: %s'
                            % ('; '.join(n['msg'] for n in errs) or tdir))
    tables = []
    for p in paths:
        rows, cols = tcslib.read_table_rows(p)
        if 'id' not in cols:
            raise SnapshotError('%s 缺 id 列 (dump 输出格式变了?): %s' % (p, cols))
        if 'text_edited' not in cols and 'text_zh' not in cols:
            raise SnapshotError('%s 既没有 text_edited 也没有 text_zh 列: %s' % (p, cols))
        tables.append((p, rows))
    merged, rep = tcslib.merge_table_rows(tables)
    if rep['conflicts']:
        raise SnapshotError('多张表里同一个 id 的 text_edited 不一致 (%d 处): %s'
                            % (len(rep['conflicts']),
                               ' '.join(c['id'] for c in rep['conflicts'][:8])))
    rows = [dict(id=(r.get('id') or '').strip(),
                 resource=(r.get('resource') or '').strip(),
                 kind=(r.get('kind') or '').strip(),
                 container=(r.get('container') or '').strip(),
                 text=tcslib.row_for_txt(r))
            for r in merged]
    return rows, tables, rep


def make_text_snapshot(dst_iso, out, ver, iso_sha=None, carry=()):
    """对**刚产出的 ISO 本身**跑一次 dump, 产出该版本的文本副本 (全在 <版本>/text/ 内)。

    ★ round37 产物:
        text/<VER>_text_long.csv / _long_nowrap.csv / _short.csv …  ← 按 kind 分表, 人工改这些
        text/<VER>_text.txt         ← **合并成一份**的轻量单行副本 (便于 git diff)
        text/<VER>_text.meta.json   ← 各表条数 / kind 列表 / 总条数 / sha256
      **不再产出合并的大 CSV** (避免"改了一张、另一张没改"的歧义)。
    返回写进 build_info.json 的 text_snapshot dict (含**每张表的路径与 sha256**)。
    """
    tdir = os.path.join(out, 'text')
    os.makedirs(tdir, exist_ok=True)
    csv_base = os.path.join(tdir, ver + '_text.csv')      # 只当"基准名"传给 dump
    txt_out = os.path.join(tdir, ver + '_text.txt')
    t0 = time.time()
    # ★ 把本轮注入用的表/目录交给 dump 当 --carry-edited:
    #   这样新版本的文本表会**保留人工写法** (例如长段里的 {WRAP} 断点标记),
    #   而不是只剩展开后的真换行 —— 否则用户下一轮编辑就得重新标记断点。
    dump_cmd = [sys.executable, DUMP_TEXT_CSV, '--iso', dst_iso, '--out', csv_base]
    for c in carry:
        if c:
            dump_cmd += ['--carry-edited', c]
    rc, _ = run_live(dump_cmd, 'text-snapshot/dump')
    if rc != 0:
        raise SnapshotError('dump_text_csv.py 失败 (exit=%d), 未产出 %s' % (rc, tdir))
    rows, tables, rep = read_text_tables(tdir, ver)
    summary = tcslib.table_set_summary(tables)
    secs = round(time.time() - t0, 1)

    meta_path = os.path.join(tdir, ver + '_text.meta.json')
    meta = {}
    if os.path.isfile(meta_path):
        try:
            meta = json.load(open(meta_path, encoding='utf-8'))
        except Exception as e:                                       # noqa: BLE001
            print('[text-snapshot] meta.json 读取失败 (不影响快照): %s' % e)

    # TXT 快照由 dump 写出 (同一口径); 万一没有就自己补一份
    if not os.path.isfile(txt_out):
        tcslib.write_txt_snapshot(txt_out, [(r['id'], r['text']) for r in rows])
    n_chars = n_cjk = 0
    for r in rows:
        t = tcslib.WRAP_RE.sub('\n', r['text'])
        n_chars += len(t)
        n_cjk += cjk_count(t)
    n_long = sum(1 for r in rows if r['kind'].startswith('long'))
    n_locked = sum(1 for r in rows if r['kind'] == 'locked')

    res = {k: dict(entries=v.get('entries'), long=v.get('long'), short=v.get('short'),
                   locked=v.get('locked'), bytes=v.get('bytes'), container=v.get('container'))
           for k, v in (meta.get('resources') or {}).items()}
    snap = dict(
        version=ver, iso_sha256=iso_sha or sha256(dst_iso),
        generated=time.strftime('%Y-%m-%d %H:%M:%S'),
        dump_seconds=secs, format=meta.get('format'),
        layout=('按 kind 分类的多张表: <版本>_text_<kind>.csv (每张 16 列, 表头与原大表相同); '
                '合并 TXT 一份; 不再产出合并的大 CSV'),
        tables_dir=rel(tdir),
        tables=summary['files'], kinds=summary['kinds'],
        tables_total_rows=summary['rows_total'],
        txt=rel(txt_out), txt_bytes=os.path.getsize(txt_out), txt_sha256=sha256(txt_out),
        meta=rel(meta_path) if os.path.isfile(meta_path) else None,
        entries=len(rows), long=n_long, locked=n_locked,
        short=len(rows) - n_long - n_locked, chars=n_chars, cjk_chars=n_cjk,
        resources=res,
        txt_format='每行 id<TAB>正文(单行); 换行=\\n 制表=\\t 反斜杠=\\\\',
        note=('版本文本副本只留在本版本文件夹的 text/ 里 (work/text_versions/ 归档已取消); '
              '{WRAP} 人工断点在 TXT 里渲染成真换行 (视图 = 盘上的换行)'),
    )
    print('[text-snapshot] %d 条 / 长段 %d / %d 字符 (中文 %d)  — 耗时 %.1fs'
          % (len(rows), n_long, n_chars, n_cjk, secs))
    for f in summary['files']:
        print('[text-snapshot] %-16s %5d 行  %s  sha %s…'
              % (f['kind'], f['rows'], f['path'], f['sha256'][:12]))
    print('[text-snapshot] TXT %s (%.0f KB)  sha %s…'
          % (rel(txt_out), os.path.getsize(txt_out) / 1024, snap['txt_sha256'][:12]))
    # ★ round39: 顺带产出「全容器文本普查」的 view-only 表 (只写 text/, 不参与注入)
    snap['containers'] = make_container_view(dst_iso, out, ver, tdir)
    print('[text-snapshot] 都在版本文件夹内: %s/' % rel(tdir))
    return snap


def make_container_view(dst_iso, out, ver, tdir):
    """★ round39: 对刚产出的 ISO 跑一次 dump_containers.py ⇒ text/<VER>_view_*.csv。

    这些表是**只能看/校对, 不能注入**的 (injectable=no): 除了 LANG/SFXML 之外的
    容器格式没被逆向, 做不到逐字节往返。它们**不进** --inject-csv 的路径
    (注入器扫描的是 ``*_text_*.csv``, view 表叫 ``*_view_*.csv``, 命名空间互斥;
    万一被显式喂给注入器, 注入器会报错拒绝并不写盘)。

    失败**不影响构筑** (只记进 build_info.json 的 text_snapshot.containers)。
    """
    script = os.path.join(REPO, 'tools', 'text_csv', 'dump_containers.py')
    if not os.path.isfile(script):
        return dict(skipped=True, reason='dump_containers.py 不存在')
    cmd = [sys.executable, script, '--iso', dst_iso,
           '--out-dir', tdir, '--prefix', ver, '--max-rows-per-category', '30000']
    try:
        rc, _ = run_live(cmd, 'text-snapshot/containers')
    except Exception as e:                                           # noqa: BLE001
        print('[containers] 异常 (不影响构筑): %s' % e)
        return dict(error=str(e))
    if rc != 0:
        print('[containers] dump_containers.py 失败 (exit=%d) —— 不影响构筑' % rc)
        return dict(error='exit=%d' % rc)
    meta_path = os.path.join(tdir, ver + '_view_containers.meta.json')
    info = dict(dir=rel(tdir), prefix=ver,
                tables=['%s_view_%s.csv' % (ver, c) for c in
                        ('xml', 'txt', 'missions', 'character_names', 'other_res',
                         'program_strings', 'iso_files', 'binary_assets', 'pending',
                         'sf_titles',            # round62: SFXML 标题属性 (view-only)
                         'containers_summary')],
                injectable='no',
                policy=('view-only: 只能看/校对, 不能注入 (格式未逆向)。'
                        '注入器 --csv <该目录> 只读 *_text_*.csv, 扫不到 _view_*.csv;'
                        '显式喂 view 表 ⇒ 报错退出 1, 不写盘'))
    if os.path.isfile(meta_path):
        try:
            m = json.load(open(meta_path, encoding='utf-8'))
            info['meta'] = rel(meta_path)
            info['format'] = m.get('format')
            info['containers'] = m.get('containers')
            info['totals'] = m.get('totals')
            info['tables_meta'] = [dict(category=t['category'], name=t['name'],
                                        rows=t['rows'], containers_kept=t['containers_kept'],
                                        containers_skipped=t['containers_skipped'],
                                        cjk_texts=t['cjk_texts'], sha256=t['sha256'])
                                   for t in (m.get('tables') or [])]
            print('[containers] %d 张 view 表 / 共 %s 行 / 容器 %s 个 (injectable=no)'
                  % (len(info['tables_meta']), (m.get('totals') or {}).get('rows'),
                     (m.get('containers') or {}).get('total')))
        except Exception as e:                                       # noqa: BLE001
            print('[containers] meta.json 读取失败 (不影响构筑): %s' % e)
    return info


def make_font_dump(dst_iso, out, ver, iso_sha=None):
    """对**刚产出的 ISO 本身** dump 字库 ⇒ <版本>/font/ 四件套 + build_info 摘要。

    实现在 tools/iso_build/dump_font.py (只读; 全部口径复用 tcslib, 不重新逆向);
    也可单跑: python tools/iso_build/dump_font.py --iso <iso> --out <版本>/font --prefix <版本>
    """
    fdir = os.path.join(out, 'font')
    print('')
    print('──── [font-dump] 字库 dump → %s/' % rel(fdir))
    summ = dump_font.dump_font(dst_iso, fdir, ver, scale=2, want_png=True,
                               iso_sha=iso_sha, verbose=True)
    c = summ['counts']
    return dict(
        dir=rel(fdir),
        generated=time.strftime('%Y-%m-%d %H:%M:%S'),
        deterministic='四件套不含时间戳; 同一 ISO 两次 dump 的 sha256 完全相同',
        atlas_png=summ['files'].get('atlas_png'),
        ft_csv=summ['files'].get('ft_csv'),
        charset_csv=summ['files'].get('charset_csv'),
        summary_json=summ['files'].get('summary_json'),
        atlas=dict(width=summ['atlas']['width'], height=summ['atlas']['height'],
                   psm=summ['atlas']['psm'], pixel_sha256=summ['atlas']['pixel_sha256']),
        faces=c['faces'], ft_records=c['ft_records'],
        chars=c['charset_rows'], by_kind=c['by_kind'],
        has_glyph=c['has_glyph'], missing_glyph=c['missing_glyph'],
        missing_glyph_chars=summ['missing_glyph_chars'],
        ft_records_with_ink=c['ft_records_with_ink'],
        ft_res_sha256=summ['font_res']['slot_sha256'],
    )


def write_build_info(out, info):
    with io.open(os.path.join(out, 'build_info.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    return os.path.join(out, 'build_info.json')


# ═════════════ ★ round46: 字库紧凑重排 (构筑的一等步骤, 在文本注入之前) ═════════════

# ★ 重排会改共享的 charset JSON (字节↔字符 映射)。若后续步骤失败, 盘没产出来, 但
#   charset 已经"提前"变成新映射 ⇒ 下一轮再构筑时 charset 与基底盘对不上 —— 会写坏。
#   所以重排前留一份备份, 构筑失败时**回滚**。 (round46 实测踩过这个坑。)
_CHARSET_ROLLBACK = []                 # [(备份路径, 目标 charset 路径)]


def rollback_charset(reason=''):
    """把 charset JSON 回滚到重排之前 (只在构筑失败时调)。"""
    out = []
    for (bak, tgt) in _CHARSET_ROLLBACK:
        if os.path.isfile(bak):
            shutil.copyfile(bak, tgt)
            out.append((rel(bak), rel(tgt)))
    if out:
        print('[font-repack] ⚠ 构筑失败 ⇒ 已把 charset 回滚到重排之前: %s'
              % '; '.join('%s → %s' % x for x in out))
        if reason:
            print('[font-repack]   原因: %s' % reason)
    del _CHARSET_ROLLBACK[:]
    return out

def run_font_repack(dst_iso, out, ver, inject_pairs, do_charset=True):
    """把在用字形紧凑重排到最前面的可用格, 未使用区域清零; 同步 charset + 出"强制重编码"表。

    位置: `--patch` / `--expand-entry` **之后**, 文本注入**之前**。
      · 重排改了"字节↔字符"映射 ⇒ 盘上所有旧编码文本必须**整体重编码** ——
        办法是把用户交给 `--inject-csv` 的每份表拷一份、**只清 `text_zh` 列**
        (译文 `text_edited` 一字不动) ⇒ 注入器认为每行都被人工改过 ⇒ 用新 charset 重编;
      · **0 改动时什么都不做**: 不改 ISO、不改 charset ⇒ 产物 sha256 与基底相同;
      · 有改动但**没有任何 `--inject-csv`** ⇒ 直接让构筑失败 (否则盘上文本会变乱码)。

    实现全部在 tools/iso_build/repack_font.py (可单跑, 见该文件的用法)。
    返回 `(info_dict, [替换后的注入输入路径...])`。
    """
    import contextlib
    rdir = os.path.join(out, 'temp', 'font_repack')
    os.makedirs(rdir, exist_ok=True)
    report_p = os.path.join(rdir, 'repack_report.json')
    moves_p = os.path.join(rdir, 'repack_moves.json')
    log_p = os.path.join(rdir, 'repack.log')
    print('')
    print('──── [font-repack] 字库紧凑重排 (在用字形压到最前 + 未使用区域置零)')
    buf = io.StringIO()

    def _emit(text):
        """既能进构筑日志, 也能进 temp/font_repack/repack.log。"""
        if text and not text.endswith('\n'):
            text += '\n'
        print(text, end='')
        buf.write(text)

    def _report(summ):
        b = io.StringIO()
        with contextlib.redirect_stdout(b):
            repack_font.print_report(summ)
        _emit(b.getvalue())

    def _finalize(summ, res, subs, status):
        """把报告 / 搬运明细 / 日志落进 temp/font_repack/。"""
        summ['status'] = status
        io.open(report_p, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(summ, ensure_ascii=False, indent=1) + '\n')
        io.open(moves_p, 'w', encoding='utf-8', newline='\n').write(json.dumps(dict(
            order_key=repack_font.ORDER_KEY, moved=summ['glyphs']['moved'],
            kept=summ['glyphs']['kept'], changes=res['code_changes'],
            layout=[dict(slot=s, char=ch, x=res['cells'][res['move'][ch]]['x'],
                         y=res['cells'][res['move'][ch]]['y']) for s, ch in res['items']],
        ), ensure_ascii=False, indent=1) + '\n')
        _emit('[font-repack] 报告 → %s' % rel(report_p))
        _emit('[font-repack] 逐字搬运明细 → %s' % rel(moves_p))
        io.open(log_p, 'w', encoding='utf-8', newline='\n').write(buf.getvalue())

    res = repack_font.plan(dst_iso)
    summ = res['summary']
    subs = [None] * len(inject_pairs)

    if not summ['changed']:
        _report(summ)
        _emit('[font-repack] 字库已经是紧凑的 ⇒ **无需重排** (0 改动): ISO / charset / 文本'
              '都不动 ⇒ 产物与基底同一个 sha256。')
        summ['wrote_iso'] = None
        summ['iso_sha256_after'] = summ['iso_sha256']
        _finalize(summ, res, subs, 'no-change')
    elif not inject_pairs:
        _report(summ)
        _emit('')
        _emit('!' * 78)
        _emit('[!!] 字库需要重排 (要搬运 %d 个字 / 改码位 %d 个 / 改 %d 个像素), '
              '但这次构筑**没有给 --inject-csv**。'
              % (summ['glyphs']['moved'], summ['code_changes'], summ['pixels_changed']))
        _emit('     重排会改「字节↔字符」映射 ⇒ 盘上所有旧编码文本必须整体重编码一次,')
        _emit('     否则旧字节会被新口径解成别的字 (整段乱码)。')
        _emit('     怎么办: 加上 `--inject-csv <上一版的 text/ 目录>` 再构筑;')
        _emit('             确实只想重排字库、不碰文本, 加 `--no-font-repack` 跳过本步。')
        _emit('     ★ 本轮**没有改动任何文件** (这项检查在写盘之前做)。')
        _emit('!' * 78)
        _finalize(summ, res, subs, 'aborted-no-inject')
        write_build_info(out, dict(
            version=ver, iso_sha256=None, built=time.strftime('%Y-%m-%d %H:%M'),
            failed_stage='font_repack',
            failed=('字库需要重排 (%d 个字改码位) 但缺少 --inject-csv 做整体重编码'
                    % summ['code_changes']),
            font_repack=summ))
        sys.exit(4)
    else:
        # ★ 改 charset 之前先留底 (构筑失败要回滚, 否则 charset 与基底盘对不上)
        bak = os.path.join(rdir, 'charset_before.json')
        shutil.copyfile(tcslib.CHARSET, bak)
        _CHARSET_ROLLBACK.append((bak, tcslib.CHARSET))
        try:
            repack_font.apply(dst_iso, dst_iso, res, do_charset=do_charset)
        except BaseException:
            rollback_charset('字库重排本身失败')     # 盘没用上, charset 也不能留着新映射
            raise
        _report(summ)
        summ['wrote_iso'] = rel(dst_iso)
        summ['iso_sha256_after'] = sha256(dst_iso)
        # ---- 每份注入表 → 一份"强制重编码"副本 (只清 text_zh) ----
        _emit('[font-repack] 生成"强制重编码"文本表 (只清 text_zh 列; 用户译文一字不动):')
        for i, (spec, csvp) in enumerate(inject_pairs, 1):
            if csvp is None:
                continue
            d = os.path.join(rdir, 'reencode', 'inject%d' % i)
            man = repack_font.make_reencode_tables(csvp, d, verbose=False)
            subs[i - 1] = d
            _emit('[font-repack]   inject%d: %s → %s (%d 行, 译文非空 %d)'
                  % (i, rel(csvp), rel(d), man['rows'], man['edited_nonempty']))
        summ['reencode'] = [dict(inject=i + 1, src=rel(p[1]) if p[1] else None,
                                 dst=rel(s) if s else None)
                            for i, (p, s) in enumerate(zip(inject_pairs, subs))]
        _finalize(summ, res, subs, 'repacked')
    info = dict(
        enabled=True, tool=rel(REPACK_FONT), order_key=repack_font.ORDER_KEY,
        changed=summ['changed'], moved=summ['glyphs']['moved'], kept=summ['glyphs']['kept'],
        codes_changed=summ['code_changes'], pixels_changed=summ['pixels_changed'],
        usable_cells=summ['cells']['usable'], used=summ['glyphs']['used'],
        blocked_record_cells=summ['cells']['record_cell'],
        blocked_ft_rect_cells=summ['cells']['ft_rect'],
        blank_usable_before=summ['capacity']['blank_usable_before'],
        remaining_capacity=summ['capacity']['remaining_capacity'],
        iso_sha256_before=summ['iso_sha256'], iso_sha256_after=summ['iso_sha256_after'],
        iso_unchanged=(summ['iso_sha256'] == summ['iso_sha256_after']),
        charset=summ['charset'], report=rel(report_p), moves=rel(moves_p), log=rel(log_p),
        reencode=summ.get('reencode'),
        one_line=summ['one_line'],
    )
    return info, subs


def run_font_compact(dst_iso, out, ver, inject_pairs, do_charset=True):
    """★ round56: 字库**紧凑重排 + 全盘重编码** —— 默认的字库步骤 (取代 round46 的 repack_font)。

    做的事:
      · 把在用字形按确定性顺序 (当前槽位升序) 压到 **slot 0..N-1**, 其余可用格清零
        ⇒ **可用空格从此整齐地待在末尾 slot N..1503** (用户本轮的核心诉求);
      · 码位整体变更 ⇒ 盘上**全部**旧编码文本整体重编码:
        ① 每份 `--inject-csv` 表 → 拷一份**只清 `text_zh` 列**的副本 (注入器据此整表重编,
           用户译文一字不动);
        ② **SFXML 的 `name=` 标题属性** + `<text>` 元素 (MENU.IMG#283) —— 原位逐字重映射 +
           重压回写 (★ 旧工具漏了 `name=`, 正是 round51「特别收录标题变成别的字」的根因);
        ③ `EN_STRINGS.RES` 的**两份副本** (MENU.IMG#25 / GR.IMG#902) —— 逐条目载荷重映射
           (注入器只重写"改过的行", 没改的行靠这一步才不会变成别的字);
        ④ **全盘兜底扫描**: 扫整个 ISO + 每个容器展开态, 找"旧 charset 能解出连续中文"的段;
           落在别的**真文本**容器里的就地重映射 (通用容器重写), 判为二进制巧合的逐项报告;
      · **★ 全盘一致性自检 (硬门禁)**: 门禁不过 ⇒ **回滚 charset + 把盘恢复成紧凑前**并中止。

    约定 (与 run_font_repack 完全一致, 用户命令行不用改):
      · 0 改动 ⇒ 什么都不做 (ISO / charset / 文本表都不动), 产物 sha256 与基底相同;
      · 有改动但**一个 `--inject-csv` 都没给** ⇒ 直接失败 (exit 4) 且不改任何文件;
      · 产物与日志: <版本>/temp/font_compact/{compact_report.json, compact_moves.json, compact.log,
        reencode/inject<N>/}; build_info.json 里有 font_compact 一段。

    返回 `(info_dict, [替换后的注入输入路径...])`。
    """
    rdir = os.path.join(out, 'temp', 'font_compact')
    os.makedirs(rdir, exist_ok=True)
    report_p = os.path.join(rdir, 'compact_report.json')
    moves_p = os.path.join(rdir, 'compact_moves.json')
    log_p = os.path.join(rdir, 'compact.log')
    print('')
    print('──── [font-compact] 字库紧凑重排 + 全盘重编码 (在用字形压到 slot 0..N-1, 空闲格全在末尾)')
    buf = io.StringIO()

    def _emit(text):
        if text and not text.endswith('\n'):
            text += '\n'
        print(text, end='')
        buf.write(text)

    def _finalize(summ, res, subs, status):
        summ['status'] = status
        io.open(report_p, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(summ, ensure_ascii=False, indent=1) + '\n')
        io.open(moves_p, 'w', encoding='utf-8', newline='\n').write(json.dumps(dict(
            order_key=font_compact.ORDER_KEY, moved=summ['glyphs']['moved'],
            kept=summ['glyphs']['kept'], changes=res['code_changes'],
            layout=[dict(slot=res['move'][ch], char=ch, x=res['cells'][res['move'][ch]]['x'],
                         y=res['cells'][res['move'][ch]]['y']) for _s, ch in res['items']],
        ), ensure_ascii=False, indent=1) + '\n')
        _emit('[font-compact] 报告 → %s' % rel(report_p))
        _emit('[font-compact] 逐字搬运明细 → %s' % rel(moves_p))
        io.open(log_p, 'w', encoding='utf-8', newline='\n').write(buf.getvalue())

    res = font_compact.plan_compact(dst_iso)
    res['charset_path'] = tcslib.CHARSET
    summ = res['summary']
    subs = [None] * len(inject_pairs)
    lay = summ['layout']
    _emit('[font-compact] 对偶槽位 %d = 在用 %d + 空闲 %d (可用格 %d, 记录码占死 %d)'
          % (summ['cells']['total'], summ['glyphs']['used'], lay['n_free'],
             lay['n_free_usable'], summ['cells']['record_cell']))
    _fu = lay['free_slots']
    # ★ round67: 扩容到 1504 = 网格上限时, 空闲格可以是空集 ⇒ 不能直接取 [0]/[1]
    _fs = ('slot %s..%s' % (_fu[0], _fu[1])) if _fu else '(无 — 网格已占满)'
    _emit('[font-compact] ★ 布局: 在用 = slot %s..%s ; 空闲 = %s (prefix_ok=%s tail_ok=%s)'
          % (lay['used_slots'][0], lay['used_slots'][1], _fs,
             lay['used_prefix_ok'], lay['free_tail_ok']))
    if summ.get('stale_migration'):
        _emit('[font-compact] ★ 陈旧码表追平: %s' % summ['stale_migration']['name'])
        _emit('[font-compact]   陈旧码表 = %s (%s); 清单 %d 条 (追平 %d / 已现役 %d)'
              % (summ['stale_migration']['stale_charset'], summ['stale_migration']['stale_label'],
                 summ['stale_migration']['n_entries'], summ['stale_migration']['roles']['migrate'],
                 summ['stale_migration']['roles']['current']))

    if not summ['changed']:
        _emit('[font-compact] 字库已经是紧凑的 ⇒ **无需重排 + 无需重编码** (0 改动): '
              'ISO / charset / 文本都不动 ⇒ 产物与基底同一个 sha256。')
        summ['wrote_iso'] = None
        summ['iso_sha256_after'] = summ['iso_sha256']
        _finalize(summ, res, subs, 'no-change')
    elif not inject_pairs:
        _emit('')
        _emit('!' * 78)
        _emit('[!!] 字库需要重排 (要搬运 %d 个字 / 改码位 %d 个 / 改 %d 个像素%s), '
              '但这次构筑**没有给 --inject-csv**。'
              % (summ['glyphs']['moved'], summ['code_changes'], summ['pixels_changed'],
                 ' / 有陈旧容器要追平' if summ.get('stale_migration') else ''))
        _emit('     重排会改「字节↔字符」映射 ⇒ 盘上所有旧编码文本必须整体重编码一次,')
        _emit('     否则旧字节会被新口径解成别的字 (整段乱码)。')
        _emit('     怎么办: 加上 `--inject-csv <上一版的 text/ 目录>` 再构筑;')
        _emit('             确实只想重排字库、不碰文本, 加 `--no-font-compact` 跳过本步。')
        _emit('     ★ 本轮**没有改动任何文件** (这项检查在写盘之前做)。')
        _emit('!' * 78)
        _finalize(summ, res, subs, 'aborted-no-inject')
        write_build_info(out, dict(
            version=ver, iso_sha256=None, built=time.strftime('%Y-%m-%d %H:%M'),
            failed_stage='font_compact',
            failed=('字库需要重排 (%d 个字改码位) 但缺少 --inject-csv 做整体重编码'
                    % summ['code_changes']),
            font_compact=summ))
        sys.exit(4)
    else:
        # ★ 改 charset 之前先留底 (门禁不过 / 后续失败要回滚)
        bak = os.path.join(rdir, 'charset_before.json')
        shutil.copyfile(tcslib.CHARSET, bak)
        _CHARSET_ROLLBACK.append((bak, tcslib.CHARSET))
        _emit('')
        _emit('──── [font-compact] 重编码方案 (文本容器 + 全盘兜底扫描)')
        iso = tcslib.Iso(dst_iso)
        re_ = font_compact.plan_reencode(iso, res)
        iso.close()
        summ['scan'] = re_['scan']
        _emit('[font-compact] 扫描: 全盘原始命中 %d 段 = IMG 条目内 %d (交给容器扫描) + '
              'IMG 之外 %d (判为真文本 %d); 容器 %d 个, 其中判为**真文本** %d 个 (= 要重写的容器)'
              % (re_['scan']['raw_runs'], re_['scan']['raw_runs_in_img'],
                 re_['scan']['raw_runs_outside_img'], re_['scan']['raw_texty_outside'],
                 re_['scan']['containers_scanned'], re_['scan']['containers_texty']))
        _emit('[font-compact] 重写容器: %s'
              % (', '.join('%s(%s, 改 %d B)' % (w['label'], w['detail']['kind'],
                                                w['detail'].get('changed_bytes', 0))
                           for w in re_['writes']) or '(无 —— 无需重编码)'))
        summ['reencode_writes'] = [dict(label=w['label'], kind=w['detail']['kind'],
                                        changed_bytes=w['detail'].get('changed_bytes', 0),
                                        diff_bytes=w['detail'].get('diff_bytes'),
                                        method=w.get('method'),
                                        frame_bytes=w['frame_bytes'], slot=w['stored'])
                                   for w in re_['writes']]
        _emit('')
        _emit('──── [font-compact] 写盘 (就地改 %s)' % rel(dst_iso))
        font_compact.apply(dst_iso, dst_iso, res, re_)
        _emit('[font-compact] 回写 %d 像素 + %d 个重编码容器 (%d 字节改动)'
              % (summ['pixels_changed'], len(re_['writes']),
                 summ['reencode']['changed_bytes']))
        _emit('')
        _emit('──── [font-compact] ★ 全盘一致性自检 (硬门禁)')
        try:
            g = font_compact.gate(dst_iso, res, re_, verbose=False)
        except BaseException as e:
            _emit('')
            _emit('!' * 78)
            _emit('[!!] ★ 全盘一致性自检**没过** ⇒ 中止; 正在把盘恢复成"紧凑前"并回滚 charset')
            _emit('     %s' % e)
            n = font_compact.restore(dst_iso, res, re_)
            _emit('     已把 %d 个改动区间写回原字节 (盘 = 基底逐字节相同)' % n)
            _emit('!' * 78)
            rollback_charset('字库门禁不过')
            _finalize(summ, res, subs, 'gate-failed')
            raise
        summ['gate'] = g
        for c in g['checks']:
            _emit('[font-compact] 门禁 ✓ %-46s %s' % (c['check'], c['detail']))
        summ['wrote_iso'] = rel(dst_iso)
        summ['iso_sha256_after'] = sha256(dst_iso)
        if do_charset:
            n = font_compact.commit_charset(tcslib.CHARSET, res, summ, verbose=False)
            _emit('[font-compact] charset 已更新 %d 个码位 (只改 pair_of, 其它字段逐字节不变)' % n)
        # ---- 每份注入表 → 一份"强制重编码"副本 (只清 text_zh) ----
        #   ★ r58: **只有真的改了码位**才需要这份副本。若是"陈旧容器追平"(布局 0 改动 /
        #     码位 0 变动), 注入仍用用户原表 —— 免得把语言表无谓地整表重写 (多余 diff)。
        if summ.get('reencode_only'):
            _emit('[font-compact] 本轮只做"陈旧容器追平"(布局与码位都没变) ⇒ '
                  '**不生成强制重编码表**, 注入仍用用户原表')
        else:
            _emit('[font-compact] 生成"强制重编码"文本表 (只清 text_zh 列; 用户译文一字不动):')
            for i, (spec, csvp) in enumerate(inject_pairs, 1):
                if csvp is None:
                    continue
                d = os.path.join(rdir, 'reencode', 'inject%d' % i)
                man = repack_font.make_reencode_tables(csvp, d, verbose=False)
                subs[i - 1] = d
                _emit('[font-compact]   inject%d: %s → %s (%d 行, 译文非空 %d)'
                      % (i, rel(csvp), rel(d), man['rows'], man['edited_nonempty']))
        summ['reencode_tables'] = [dict(inject=i + 1, src=rel(p[1]) if p[1] else None,
                                        dst=rel(s) if s else None)
                                   for i, (p, s) in enumerate(zip(inject_pairs, subs))]
        _finalize(summ, res, subs, 'compacted')
    info = dict(
        enabled=True, tool=rel(FONT_COMPACT), order_key=font_compact.ORDER_KEY,
        changed=summ['changed'], reencode_only=summ.get('reencode_only', False),
        stale_migration=summ.get('stale_migration'),
        moved=summ['glyphs']['moved'], kept=summ['glyphs']['kept'],
        codes_changed=summ['code_changes'], pixels_changed=summ['pixels_changed'],
        used=summ['glyphs']['used'], free_slots=[summ['glyphs']['used'],
                                                 summ['cells']['total'] - 1],
        used_prefix_ok=summ['layout']['used_prefix_ok'],
        free_tail_ok=summ['layout']['free_tail_ok'],
        usable_cells=summ['cells']['usable'], record_cells=summ['cells']['record_cell'],
        scan=summ.get('scan'),
        reencode_containers=[dict(label=w['label'], kind=w['kind'],
                                  changed_bytes=w.get('changed_bytes'),
                                  diff_bytes=w.get('diff_bytes'), method=w.get('method'),
                                  frame_bytes=w['frame_bytes'], slot=w['slot'])
                             for w in (summ.get('reencode_writes') or [])],
        gate_checks=([c['check'] for c in (summ.get('gate') or {}).get('checks', [])]
                     if summ.get('gate') else None),
        gate_ok=bool(summ.get('gate')),
        iso_sha256_before=summ['iso_sha256'], iso_sha256_after=summ.get('iso_sha256_after'),
        iso_unchanged=(summ['iso_sha256'] == summ.get('iso_sha256_after')),
        charset=summ['charset'], report=rel(report_p), moves=rel(moves_p), log=rel(log_p),
        reencode=summ.get('reencode_tables'),
        one_line=('在用字形 = slot 0..%d, %s (可用格 %d 个全在末尾); 搬运 %d 个字, '
                  '改码位 %d 个, 重编码 %d 个文本容器'
                  % (summ['glyphs']['used'] - 1,
                     ('空闲 = slot %d..%d' % (summ['glyphs']['used'], summ['cells']['total'] - 1))
                     if summ['layout']['n_free'] else '空闲 = 无 (网格已占满)',
                     summ['layout']['n_free_usable'],
                     summ['glyphs']['moved'], summ['code_changes'],
                     summ.get('reencode', {}).get('containers', 0))),
    )
    return info, subs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('version')
    ap.add_argument('--patch', help='补丁脚本: python <patch> <src_iso> <dst_iso>')
    ap.add_argument('--from', dest='base', help='基底构筑目录或 ISO 路径')
    ap.add_argument('--no-textdump', action='store_true',
                    help='跳过"全量文本总表"自动导出 (默认每次构筑都出)')
    ap.add_argument('--expand-entry', action='append', default=[], metavar='NAME=SIZE',
                    help='扩容 MENU.IMG 内某条目到指定 stored 大小 (可多次); '
                         '条目会被搬到 IMG 末尾, 只改它自己的 off/stored')
    ap.add_argument('--verify-img', action='store_true',
                    help='构筑后校验 MENU.IMG / GR.IMG 条目表自洽性 (越界/重叠/空洞)')
    ap.add_argument('--inject-csv', action='append', default=[], metavar='表/目录',
                    help='在 --patch 之后按顺序注入的文本表 (可多次)。★ 推荐给**目录** '
                         '(如 work/builds/GR_ZH92/text) ⇒ 该目录下所有 *_text_*.csv 全部读入, '
                         '以后多了新的 kind 也不会漏; 也可给单个表文件或只给版本名 '
                         '(如 GR_ZH92 ⇒ 自动找 work/builds/GR_ZH92/text/); '
                         '失败 (尤其字库覆盖预检 exit=3 缺字) 会让构筑直接失败')
    ap.add_argument('--inject-only', default='', metavar='IDS',
                    help='调试用: --inject-csv 只注入这些 id (逗号分隔, 支持前缀 *)')
    ap.add_argument('--no-text-snapshot', action='store_true',
                    help='跳过"版本文本副本"(<版本>/text/<版本>_text_<kind>.csv|.txt|.meta.json)')
    ap.add_argument('--no-font-dump', action='store_true',
                    help='跳过"版本字库 dump"(<版本>/font/ 的图集 PNG + FT 记录表 + '
                         '字符集清单 + summary.json)')
    ap.add_argument('--no-font-repack', action='store_true',
                    help='★ 旧名 (round46-55): 等价于 --no-font-compact —— 关闭字库步骤 '
                         '(默认**开启**)。保留只为让历史命令继续可用。')
    ap.add_argument('--no-font-compact', action='store_true',
                    help='★ 关闭"字库紧凑重排 + 全盘重编码"这一自动步骤 (默认**开启**, round56 起)。'
                         '默认行为: 在文本注入**之前**把在用字形紧凑重排到 **slot 0..N-1**、'
                         '空闲格全部落到**末尾 slot N..1503**, 并把盘上全部旧编码文本整体重编码 '
                         '(SFXML name= 标题属性 + <text> + EN_STRINGS.RES 两份副本 + 全盘兜底扫描), '
                         '同步 charset, 且每份 --inject-csv 表换成"只清 text_zh 列"的重编码副本; '
                         '写盘后跑**全盘一致性自检硬门禁** (不过就回滚并中止); 0 改动时什么都不做。')
    ap.add_argument('--font-repack-legacy', action='store_true',
                    help='用 round46 的旧工具 repack_font.py 跑字库步骤 (历史复现)。'
                         '⚠ 它**不会**重编码 SFXML 的 name= 标题属性 ⇒ 那些标题会变成别的字 '
                         '(round51 根因); 只在对旧产物做可复现对照时用。')
    a = ap.parse_args()
    ver = a.version
    # 允许 GR_ZH<数字> 后接 _后缀 (如 GR_ZH82_G); latest_build()/run_opt.latest_iso()
    # 仍只认纯 GR_ZH<数字>, 故带后缀的盘不会被当成"最新盘"而影响他人。
    # round60: 另允许 GR_TEST_* —— 测试盘 (如字库测试页 GR_TEST_FONT1); 同样不会被当成"最新盘"。
    # round71: 再允许**小写字母后缀**(GR_ZH113b) —— 以前只认 GR_ZH113_B, 逼得任务"先合法名构筑再改名"。
    assert re.fullmatch(r'(GR_ZH\d+[a-z]?(_[A-Za-z0-9]+)*|GR_TEST_[A-Za-z0-9_]+)', ver), \
        '版本名须为 GR_ZH<数字>[小写字母][_后缀] 或 GR_TEST_<名字>: %s' % ver
    out = os.path.join(BUILDS, ver)
    assert not os.path.exists(out), out + ' 已存在'

    if a.base:
        base = a.base
    else:
        base = latest_build()
        assert base, '找不到基底 (work/builds 为空且无旧位置 ISO)'
    base_iso = base if base.endswith('.iso') else os.path.join(base, os.path.basename(base) + '.iso')
    assert os.path.isfile(base_iso), base_iso
    print('[base] %s (sha %s...)' % (base_iso, sha256(base_iso)[:16]))
    base_rel = rel(base_iso)

    os.makedirs(out)
    os.makedirs(os.path.join(out, 'temp'))
    dst_iso = os.path.join(out, ver + '.iso')
    if a.patch:
        r = subprocess.run([sys.executable, a.patch, base_iso, dst_iso])
        assert r.returncode == 0, '补丁脚本失败'
    else:
        shutil.copyfile(base_iso, dst_iso)
    assert os.path.getsize(dst_iso) == os.path.getsize(base_iso), 'ISO 尺寸变化?'
    print('[iso] %s (%.2f GB)' % (dst_iso, os.path.getsize(dst_iso) / 1e9))

    # ---- MENU.IMG 条目扩容 (可选; 只改被点名条目的 off/stored) ----
    if a.expand_entry:
        d = bytearray(open(dst_iso, 'rb').read())
        for spec in a.expand_entry:
            assert '=' in spec, '格式须为 NAME=SIZE: %s' % spec
            nm, sz = spec.rsplit('=', 1)
            img_expand(d, MENU_LBA, MENU_SIZE, nm, int(sz, 0))
        open(dst_iso, 'wb').write(bytes(d))
        print('[img] 已扩容 %d 个条目' % len(a.expand_entry))

    # ---- 注入输入先解析出来 (字库重排要用它生成"强制重编码"副本; patch/expand 之后) ----
    inject_pairs = []                          # [(用户给的原样 spec, 解析出的路径)]
    for spec in a.inject_csv:
        csvp = resolve_inject_input(spec)      # 表文件 / 多表目录 / 版本名 都认
        if csvp is None:
            print('[!!] 找不到注入用的文本表: %s' % spec)
            print('     试过: 直接路径 (文件或目录) / work/builds/<版本>/text (多表目录) / '
                  'work/builds/<版本>/text/<版本>_text.csv / work/builds/<版本>/<版本>_text.csv / '
                  'work/text_versions/<版本>_text.csv')
            sys.exit(2)
        inject_pairs.append((spec, csvp))

    # ---- ★ round56: 字库紧凑重排 + 全盘重编码 (默认开启; --no-font-compact 关闭) ----
    #   位置 = patch/expand **之后**、文本注入**之前** (先重排字库 + 出重编码表, 再按用户表注入)。
    #   · 0 改动 ⇒ 什么都不做, 产物 sha256 与基底相同;
    #   · 有改动 ⇒ 同步 charset, 并把每份注入表换成"只清 text_zh 列"的副本
    #     (这样注入器会用**新** charset 把用户译文整体重编码写盘);
    #   · --font-repack-legacy ⇒ 退回 round46 的 repack_font (历史复现; 会漏 SFXML name=)。
    font_step, font_step_tool, repack_subs = None, None, [None] * len(inject_pairs)
    if a.no_font_compact or a.no_font_repack:
        print('\n──── [font-step] 已用 %s 关闭字库步骤'
              % ('--no-font-compact' if a.no_font_compact else '--no-font-repack (旧名)'))
    elif a.font_repack_legacy:
        font_step_tool = 'repack_font(legacy)'
        font_step, repack_subs = run_font_repack(dst_iso, out, ver, inject_pairs)
    else:
        font_step_tool = 'font_compact'
        font_step, repack_subs = run_font_compact(dst_iso, out, ver, inject_pairs)

    # ---- ★ 文本注入 (--inject-csv, 可多次): 按顺序执行 ----
    #   每一步都是 tools/text_csv/inject_text_csv.py --src <当前产物> --dst <下一步产物>;
    #   注入器**写盘前**会做字库覆盖预检, 缺字时 exit=3 且不写任何盘
    #   ⇒ 这里必须让构筑失败 (非 0 退出) 并把它的报告原样留在日志里, 绝不静默继续。
    inject_done = []
    inject_sources = []                        # ★ 记录每步注入用的表/目录 ⇒ 快照时 --carry-edited
    for i, (spec, csvp0) in enumerate(inject_pairs, 1):
        csvp = repack_subs[i - 1] or csvp0     # 重排过 ⇒ 用"强制重编码"副本
        if repack_subs[i - 1]:
            print('[inject] %d/%d 用重排后的重编码表: %s (用户表: %s)'
                  % (i, len(inject_pairs), rel(csvp), rel(csvp0)))
        inject_sources.append(csvp0)           # --carry-edited 仍指向**用户原表** (写法一致)
        tmp_iso = os.path.join(out, '%s.inject%d.iso.tmp' % (ver, i))
        report = os.path.join(out, 'temp', 'inject%d_report.json' % i)
        cmd = [sys.executable, INJECT_TEXT_CSV, '--csv', csvp,
               '--src', dst_iso, '--dst', tmp_iso, '--report', report]
        if a.inject_only:
            cmd += ['--only', a.inject_only]
        rc, tail = run_live(cmd, 'inject %d/%d' % (i, len(a.inject_csv)))
        if rc != 0:
            if os.path.exists(tmp_iso):
                os.remove(tmp_iso)                    # 注入器正常失败时不会写盘; 保险起见清掉
            print('\n' + '!' * 78)
            print('[!!] 文本注入失败 (exit=%d) —— 构筑中止, **未产出最终 ISO**。' % rc)
            print('     注入用的表   : %s%s'
                  % (rel(csvp), ('  (= 重排后的重编码副本; 用户原表 %s)' % rel(csvp0))
                     if repack_subs[i - 1] else ''))
            print('     当时的产物   : %s  (补丁后的中间态, 未注入任何文本)' % rel(dst_iso))
            print('     注入报告     : %s' % rel(report))
            if rc == 3:
                print('     原因 = 字库覆盖预检不通过 (有缺字), 缺字清单见上面 '
                      '「字库覆盖预检 (写盘前)」一节:')
                for ln in tail.splitlines():
                    if ln.startswith('  ──') or ln.startswith('     原因:'):
                        print('     %s' % ln.strip())
                print('     怎么办: 把缺字换成常用字 (最省事), 改完 CSV 再重跑构筑;')
                print('             确要写入盘上画不出来的字, 先扩字符集/字库 (见 '
                      'tools/text_csv/FORMAT.md §6)。')
            elif rc == 1:
                print('     原因 = 结构性错误 (表与源盘不符 / 超槽 / 回读不符 / 标记写错 / '
                      '多表里同一个 id 的 text_edited 不一致),')
                print('             详见上面的 [!!] 行与注入报告。')
            print('     ⚠ 要重跑请先删除 %s (构筑器不覆盖已存在的版本目录)。' % rel(out))
            print('!' * 78)
            rollback_charset('文本注入失败 (exit=%d)' % rc)
            write_build_info(out, dict(
                version=ver, base=base_rel, patch=a.patch or None, inject_csv=a.inject_csv,
                iso_sha256=None, built=time.strftime('%Y-%m-%d %H:%M'),
                failed='文本注入失败 (exit=%d): %s' % (rc, rel(csvp)),
                failed_stage='inject%d' % i, inject_report=rel(report)))
            sys.exit(rc or 1)
        assert os.path.getsize(tmp_iso) == os.path.getsize(dst_iso), '注入后 ISO 尺寸变化?'
        os.replace(tmp_iso, dst_iso)                  # 原子替换: 当前产物 = 下一步的基底
        inject_done.append(dict(csv=rel(csvp), report=rel(report),
                                iso_sha256=sha256(dst_iso)))
        print('[inject] %d/%d 完成: %s → ISO sha %s…'
              % (i, len(inject_pairs), rel(csvp), inject_done[-1]['iso_sha256'][:16]))

    del _CHARSET_ROLLBACK[:]        # 注入成功 ⇒ charset 的新映射已落到盘上, 不再回滚

    if a.verify_img:
        ok1 = verify_img(dst_iso, MENU_LBA, MENU_SIZE, 'MENU.IMG')
        ok2 = verify_img(dst_iso, GR_LBA, GR_SIZE, 'GR.IMG')
        assert ok1 and ok2, 'IMG 条目表校验未通过'

    ext = os.path.join(out, 'extract')
    os.makedirs(ext)
    with open(dst_iso, 'rb') as f:
        f.seek(MENU_LBA * 2048)
        menu = f.read(MENU_SIZE)
    assert len(menu) == MENU_SIZE
    open(os.path.join(ext, 'MENU.IMG'), 'wb').write(menu)
    open(os.path.join(ext, 'ft_font_res.bin'), 'wb').write(menu[OFF_FT:OFF_FT + 4421])
    open(os.path.join(ext, 'font_new_font_revised.bin'), 'wb').write(menu[OFF_REC:OFF_REC + REC_LEN])
    print('[extract] 字表 4421B + 字库记录 %dB + MENU.IMG %dMB → extract/' % (REC_LEN, MENU_SIZE // 1048576))

    # ---- 自动产出全量文本总表 (每次构筑必出; --no-textdump 可关) ----
    textdump = None
    if not a.no_textdump:
        td = os.path.join(out, 'temp', 'textdump')
        try:
            r = subprocess.run([sys.executable, DUMP_ALL_TEXT, dst_iso, '--out', td],
                               capture_output=True, text=True, encoding='utf-8', errors='replace')
            if r.returncode != 0:
                print('[textdump] 导出失败 (不影响构筑):')
                print((r.stderr or r.stdout or '')[-800:])
            else:
                tail = (r.stdout or '').strip().splitlines()
                print('[textdump] ' + (tail[-1] if tail else 'ok'))
                r2 = subprocess.run([sys.executable, TEXT_XLSX, td],
                                    capture_output=True, text=True, encoding='utf-8', errors='replace')
                if r2.returncode == 0:
                    print('[textdump] ' + (r2.stdout or '').strip().splitlines()[-1])
                    textdump = os.path.join(td, 'all_text.xlsx')
                else:
                    print('[textdump] xlsx 生成失败: %s' % (r2.stderr or '')[-400:])
        except Exception as e:                                   # noqa: BLE001
            print('[textdump] 异常 (不影响构筑): %s' % e)

    # ---- ★ 版本文本副本 (每次构筑默认产出; --no-text-snapshot 可关) ----
    #   dump 的对象是**刚产出的这个 ISO 本身** (补丁/扩容/注入全部完成之后的最终盘),
    #   所以快照反映的就是"这一版盘里真实的文本"。
    iso_sha = sha256(dst_iso)                     # 全盘 sha256 只算一次 (1.6 GB)
    snap, snap_err = None, None
    if not a.no_text_snapshot:
        try:
            snap = make_text_snapshot(dst_iso, out, ver, iso_sha=iso_sha,
                                      carry=inject_sources)
        except Exception as e:                                       # noqa: BLE001
            snap_err = (str(e) if isinstance(e, SnapshotError)
                        else '%s: %s' % (type(e).__name__, e))
            print('\n' + '!' * 78)
            print('[!!] 版本文本副本产出失败: %s' % e)
            print('     ISO 已产出且未受影响: %s' % rel(dst_iso))
            print('     单独重跑: %s tools/text_csv/dump_text_csv.py --iso %s --out %s'
                  % (sys.executable, rel(dst_iso),
                     rel(os.path.join(out, 'text', ver + '_text.csv'))))
            print('!' * 78)
            # ★ round39: 文本表 dump 失败**不**牵连 view 表 —— 全容器普查是只读旁证,
            #   与"能不能注入"无关, 照样产出 (失败也不会让构筑失败)。
            try:
                snap = dict(version=ver, iso_sha256=iso_sha, partial=True,
                            text_snapshot_error=snap_err,
                            containers=make_container_view(dst_iso, out, ver,
                                                           os.path.join(out, 'text')))
            except Exception as e2:                                  # noqa: BLE001
                print('[containers] 也失败了 (不影响构筑): %s' % e2)

    # ---- ★ 版本字库 dump (每次构筑默认产出; --no-font-dump 可关) ----
    #   同样 dump **刚产出的这个 ISO 本身** ⇒ 版本文件夹里就有这一版的字库快照。
    #   ⚠ 失败**不**让构筑失败: 字库 dump 是只读的旁证, 盘已经产出好了 (但会在
    #     build_info.json 里记 font_dump_error, 并把重跑命令打出来)。
    font, font_err = None, None
    if not a.no_font_dump:
        try:
            font = make_font_dump(dst_iso, out, ver, iso_sha=iso_sha)
        except Exception as e:                                       # noqa: BLE001
            font_err = '%s: %s' % (type(e).__name__, e)
            print('\n' + '!' * 78)
            print('[!!] 字库 dump 失败: %s' % e)
            print('     ISO 已产出且未受影响: %s' % rel(dst_iso))
            print('     单独重跑: %s tools/iso_build/dump_font.py --iso %s --out %s --prefix %s'
                  % (sys.executable, rel(dst_iso), rel(os.path.join(out, 'font')), ver))
            print('!' * 78)

    info = dict(version=ver, base=base_rel, patch=a.patch or None,
                inject_csv=inject_done or None,
                iso_sha256=iso_sha, iso_bytes=os.path.getsize(dst_iso),
                built=time.strftime('%Y-%m-%d %H:%M'),
                font_step_tool=font_step_tool,
                font_compact=(font_step if font_step_tool == 'font_compact' else None),
                font_repack=(font_step if font_step_tool == 'repack_font(legacy)' else None),
                text_table=textdump, text_snapshot=snap, font_dump=font)
    if snap_err:
        # ★ round39: 文本表 dump 失败时, snap 里可能仍有只读的 view 表信息 (containers) ——
        #   把 text_snapshot 标成 partial 并保留 containers, 不整个丢掉。
        if snap and snap.get('containers'):
            info['text_snapshot'] = snap
            info['text_snapshot']['partial'] = True
        else:
            info['text_snapshot'] = None
        info['text_snapshot_error'] = snap_err
    if font_err:
        info['font_dump'] = None
        info['font_dump_error'] = font_err
    bi = write_build_info(out, info)
    print('[info] %s' % rel(bi))
    # ★ 把"这份 charset 配的是哪张盘"记进 charset (旁证字段; 失败不影响构筑)。
    #   下一轮 plan 据此就能发现"charset 与输入盘不是同一版本"。
    if font_step_tool == 'font_compact':
        font_compact.stamp_charset(ver, iso_sha)
    elif font_step_tool == 'repack_font(legacy)':
        repack_font.stamp_charset(ver, iso_sha)
    print('[done] %s — 测试产物放 %s/temp/' % (rel(out), rel(out)))
    if textdump:
        print('[done] 文本总表: %s' % rel(textdump))
    if snap and snap.get('tables'):
        print('[done] 本版本文本副本: %d 张表 / %d 条 / %d 字符 (中文 %d)'
              % (len(snap['tables']), snap['entries'], snap['chars'], snap['cjk_chars']))
        print('[done] 目录: %s' % snap['tables_dir'])
        for f in snap['tables']:
            print('[done]   %-14s %5d 行  %s' % (f['kind'], f['rows'], f['path']))
        print('[done] 合并 TXT (便于 diff): %s' % snap['txt'])
    if snap and snap.get('containers'):
        c = snap['containers']
        tm = c.get('tables_meta') or []
        tt = c.get('totals') or {}
        print('[done] 全容器文本普查 (view-only, 不能注入): %d 张表 / %s 行 / 容器 %s 个'
              % (len(tm), tt.get('rows'), (c.get('containers') or {}).get('total')))
        print('[done]   %s' % rel(os.path.join(out, 'text',
                                               ver + '_view_containers_summary.csv')))
        print('[done]   ★ 这些表 injectable=no: 注入器只读 *_text_*.csv, 显式喂 view 表会报错')
    if font:
        print('[done] 本版本字库 dump: %s (face %d / 记录 %d / 字符 %d, 缺字形 %d)'
              % (font['dir'], font['faces'], font['ft_records'], font['chars'],
                 font['missing_glyph']))
        print('[done] 图集图(一眼看字形): %s' % font['atlas_png']['path'])
        print('[done] 字符集清单(看缺字): %s' % font['charset_csv']['path'])
    if font_step:
        fr = font_step
        print('[done] 字库步骤 (%s): %s'
              % (font_step_tool,
                 '**本轮重排 + 重编码了**' if fr['changed'] else '无需重排 (0 改动, 产物 sha256 未变)'))
        if font_step_tool == 'font_compact':
            lay = fr.get('free_slots')          # ★ round67: 网格占满时是空列表
            _fsd = ('slot %d..%d' % (lay[0], lay[1])) if lay else '无 (网格已占满)'
            print('[done]   ★ 在用字形 = slot 0..%d, 空闲格 = %s (可用格 %d 个全在末尾)'
                  % (fr['used'] - 1, _fsd, fr.get('usable_cells', 0) - fr['used']))
            print('[done]   搬运 %d 个字 / 改码位 %d 个; 重编码文本容器 %d 个; '
                  '★ 全盘一致性自检 %s'
                  % (fr['moved'], fr['codes_changed'],
                     len(fr.get('reencode_containers') or []),
                     ('%d 项全过' % len(fr.get('gate_checks') or [])) if fr['gate_ok']
                     else ('无需 (0 改动)' if not fr['changed'] else '未跑')))
        else:
            print('[done]   ★ 重排后还能再放 **%d** 个新字 (可用格 %d − 在用 %d); '
                  '重排前只有 %d 个位置是白的'
                  % (fr['remaining_capacity'], fr['usable_cells'], fr['used'],
                     fr['blank_usable_before']))
            print('[done]   搬运 %d 个字 / 改码位 %d 个; 死格: 记录码 %d + 被 FT 记录矩形压着 %d'
                  % (fr['moved'], fr['codes_changed'], fr['blocked_record_cells'],
                     fr['blocked_ft_rect_cells']))
        print('[done]   报告: %s' % fr['report'])
    if snap or font:
        print('[done] 跨版本对比: %s tools/text_csv/diff_text_versions.py %s <另一个版本>'
              % (sys.executable, ver))
    if snap_err:
        sys.exit(1)


if __name__ == '__main__':
    main()
