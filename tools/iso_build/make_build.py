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
    print('[text-snapshot] 都在版本文件夹内: %s/' % rel(tdir))
    return snap


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
    a = ap.parse_args()
    ver = a.version
    # 允许 GR_ZH<数字> 后接 _后缀 (如 GR_ZH82_G); latest_build()/run_opt.latest_iso()
    # 仍只认纯 GR_ZH<数字>, 故带后缀的盘不会被当成"最新盘"而影响他人。
    assert re.fullmatch(r'GR_ZH\d+(_[A-Za-z0-9]+)*', ver), '版本名须为 GR_ZH<数字>[_后缀]: %s' % ver
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

    # ---- ★ 文本注入 (--inject-csv, 可多次): patch 之后按顺序执行 ----
    #   每一步都是 tools/text_csv/inject_text_csv.py --src <当前产物> --dst <下一步产物>;
    #   注入器**写盘前**会做字库覆盖预检, 缺字时 exit=3 且不写任何文件
    #   ⇒ 这里必须让构筑失败 (非 0 退出) 并把它的报告原样留在日志里, 绝不静默继续。
    inject_done = []
    inject_sources = []                        # ★ 记录每步注入用的表/目录 ⇒ 快照时 --carry-edited
    for i, spec in enumerate(a.inject_csv, 1):
        csvp = resolve_inject_input(spec)      # 表文件 / 多表目录 / 版本名 都认
        inject_sources.append(csvp)
        if csvp is None:
            print('[!!] 找不到注入用的文本表: %s' % spec)
            print('     试过: 直接路径 (文件或目录) / work/builds/<版本>/text (多表目录) / '
                  'work/builds/<版本>/text/<版本>_text.csv / work/builds/<版本>/<版本>_text.csv / '
                  'work/text_versions/<版本>_text.csv')
            sys.exit(2)
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
            print('     注入用的表   : %s' % rel(csvp))
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
              % (i, len(a.inject_csv), rel(csvp), inject_done[-1]['iso_sha256'][:16]))

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
                text_table=textdump, text_snapshot=snap, font_dump=font)
    if snap_err:
        info['text_snapshot'] = None
        info['text_snapshot_error'] = snap_err
    if font_err:
        info['font_dump'] = None
        info['font_dump_error'] = font_err
    bi = write_build_info(out, info)
    print('[info] %s' % rel(bi))
    print('[done] %s — 测试产物放 %s/temp/' % (rel(out), rel(out)))
    if textdump:
        print('[done] 文本总表: %s' % rel(textdump))
    if snap:
        print('[done] 本版本文本副本: %d 张表 / %d 条 / %d 字符 (中文 %d)'
              % (len(snap['tables']), snap['entries'], snap['chars'], snap['cjk_chars']))
        print('[done] 目录: %s' % snap['tables_dir'])
        for f in snap['tables']:
            print('[done]   %-14s %5d 行  %s' % (f['kind'], f['rows'], f['path']))
        print('[done] 合并 TXT (便于 diff): %s' % snap['txt'])
    if font:
        print('[done] 本版本字库 dump: %s (face %d / 记录 %d / 字符 %d, 缺字形 %d)'
              % (font['dir'], font['faces'], font['ft_records'], font['chars'],
                 font['missing_glyph']))
        print('[done] 图集图(一眼看字形): %s' % font['atlas_png']['path'])
        print('[done] 字符集清单(看缺字): %s' % font['charset_csv']['path'])
    if snap or font:
        print('[done] 跨版本对比: %s tools/text_csv/diff_text_versions.py %s <另一个版本>'
              % (sys.executable, ver))
    if snap_err:
        sys.exit(1)


if __name__ == '__main__':
    main()
