# -*- coding: utf-8 -*-
r"""patch_zh98_font_cleanup.py — round49 前置补丁: **清真残墨 + 回收死字**。

由 `make_build.py --patch` 在"字库重排 / 文本注入"**之前**调用:

    python tools/iso_build/patch_zh98_font_cleanup.py <src.iso> <dst.iso>
    # 完整构筑 (本轮实际用的命令行):
    python tools/iso_build/make_build.py GR_ZH98 \
        --from work/builds/GR_ZH97/GR_ZH97.iso \
        --patch tools/iso_build/patch_zh98_font_cleanup.py \
        --inject-csv work/builds/GR_ZH97/text \
        --no-font-repack

## 这一步做两件事 (都只动"字库", 一个字都不碰文本)

① **清真残墨** —— 用 `tools/iso_build/font_residue.py` 的判据
   `残墨 = 墨 ∧ ¬(charset 已用对偶格) ∧ ¬(全部 FT 记录窗, 膨胀 ±(4,2))`,
   把这些像素写成"空色"。**只写像素容器的数据区**, 48B 包头逐字节核对 + 回读校验。

② **回收死字** —— 扫**全部注入表** (`*_text_*.csv`, 所有列) 统计每个字符出现次数,
   `0 次` 的对偶字 ⇒ 从 `charset_compiled_zh16.json` 的 `pair_of` 里删掉那一条映射
   ⇒ 它的码位空出来, 同时把它那一格的**字形像素**擦掉 (⇒ 格变白, 立刻能写新字)。

## ★ 为什么本轮**关掉**了"字库紧凑重排" (`make_build --no-font-repack`)

重排会把在用字形按槽位顺序重新压到**最前面的可用格** ⇒ 凡是前面有洞, 后面的字整体挪一格
⇒ **码位全变** ⇒ 盘上所有旧编码文本必须整体重编码一次。本轮的取舍 (实测, 见
`docs/REPORT_font_cleanup.md` §四):

  · 重排能换来的"可直接写新字的空格数" = **0**:
      重排口径   可用格 1409 − 在用 1175 = 234;
      不重排口径 原本就白的 90 + 本轮擦白的 144 = **234** —— 一模一样;
  · 代价却很大 (实测那一轮): **1039 个字改了码位**, 而且把 tcslib 里那条**字节级锚点**
    `AF A1 BD` 弄失效了 —— 锚点要求 (0xAF,0xA1) 必须是个合法对偶码, 重排后 1175 个字
    只用到 lead 0xAD ⇒ 0xAF 段全空 ⇒ `dump_text_csv.py` 直接**拒绝出表**
    (见 `work/builds/GR_ZH97/temp/r49/build_zh98_attempt1_with_repack.log`)。
    tcslib 是受保护文件, 不该为了让它过而改它。
  · 不重排 ⇒ **一个字位都不变**, 盘上文本逐字节原样 ⇒ "文本逐字符不变" 从
    "重编码之后再验证" 变成 **"根本没动过"** (更强的保证, 也正是工单期望的
    「回收只动 charset 与图集, 不动文本」)。

⇒ 回收死字 + 擦残墨 + 擦死字字形 **全部在本补丁里完成** (不依赖重排)。
  将来谁要重排 (比如又要加一批字), 照常跑标准流程即可 —— 那时才需要整体重编码。

## 安全措施

* charset 改之前**留底**到 `<构筑目录>/temp/charset_before_font_cleanup.json`
  (`make_build` 自己还会在重排前再留一份 `charset_before.json`);
* 被删字的**码位 + 16x16 字形位图**一起存进
  `<构筑目录>/temp/font_recycle_backup.json` ⇒ **可还原** (见文件末 `--restore-help`);
* 任何一个"死字"只要在 view 表 (`*_view_*.csv`) 的 `has_cjk=yes` 行里出现过, 就**不删**,
  只报告 (那种场合可能是盘上别处的真文本, 不冒险);
* 全程不碰 ELF / PVD / IMG 条目表 / PAK 包头 / FONT.RES / 文本容器。

## 用法补充

    --list-only      只算不写 (看这次会回收哪些字、清多少残墨)
    --keep CHARS     额外指定"不许回收"的字 (字符串)
    --no-residue     只回收死字, 不清残墨
    --no-recycle     只清残墨, 不回收死字
"""
import argparse
import base64
import csv
import io
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:                                                        # noqa: BLE001
    pass

import numpy as np                                                       # noqa: E402
import tcslib                                                            # noqa: E402
import dump_font                                                         # noqa: E402
import repack_font                                                       # noqa: E402
import font_residue                                                      # noqa: E402

TOOL = 'tools/iso_build/patch_zh98_font_cleanup.py'
TOOL_VERSION = 'r49.1'
ROUND = 'round49'
# 用户点名的 20 个人名字 (round49 工单原话) —— 只用于报告时单独点名
NAMED_20 = '珍琳费贾赖辉辛迈郑闫阮阳陈隆雅韦魏鲍鹏麦'


def rel(p):
    try:
        r = os.path.relpath(p, REPO)
    except ValueError:
        return p.replace('\\', '/')
    return r.replace('\\', '/') if not r.startswith('..') else p.replace('\\', '/')


# ═══════════════════════ ① 用量统计 (回收死字的判据) ═══════════════════════

def list_tables(text_dir):
    inj, view = [], []
    for fn in sorted(os.listdir(text_dir)):
        if not fn.endswith('.csv'):
            continue
        if '_text_' in fn:
            inj.append(fn)
        elif '_view_' in fn and not fn.endswith('containers_summary.csv'):
            view.append(fn)
    return inj, view


def usage_counts(text_dir):
    """扫全部注入表 (所有列, 所有单元格) → {char: 次数} 与逐文件明细。"""
    inj, view = list_tables(text_dir)
    if not inj:
        raise SystemExit('!! %s 里找不到任何 *_text_*.csv (注入表)' % text_dir)
    counts, per_file, rows = {}, {}, 0
    for fn in inj:
        c = {}
        with io.open(os.path.join(text_dir, fn), encoding='utf-8-sig', newline='') as f:
            rd = csv.reader(f)
            next(rd, None)
            for row in rd:
                rows += 1
                for cell in row:
                    for ch in cell:
                        counts[ch] = counts.get(ch, 0) + 1
                        c[ch] = c.get(ch, 0) + 1
        per_file[fn] = c
    return dict(counts=counts, per_file=per_file, rows=rows, inj=inj, view=view)


def view_cjk_chars(text_dir, view_files):
    """view 表里出现在 `has_cjk=yes` 行的字符 → {char: 次数} (判定"盘上真中文"的风险面)。"""
    out = {}
    for fn in view_files:
        try:
            with io.open(os.path.join(text_dir, fn), encoding='utf-8-sig', newline='') as f:
                for row in csv.DictReader(f):
                    if (row.get('has_cjk') or '').strip().lower() != 'yes':
                        continue
                    for ch in (row.get('text') or ''):
                        out[ch] = out.get(ch, 0) + 1
        except Exception:                                                # noqa: BLE001
            continue
    return out


def pick_dead(cs, counts, view_cjk, keep=''):
    """charset 的合法对偶字里, 注入表 0 次 ⇒ 死字。返回 (可回收, 因风险保留, 明细)。"""
    dead, blocked, detail = [], [], {}
    for ch, (b1, b2) in sorted(cs.enc_pair.items()):
        if not (tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI):
            continue                     # lead 越界的本来就不在本盘字库里
        n = counts.get(ch, 0)
        detail[ch] = dict(pair=[b1, b2], slot=tcslib.pair_slot(b1, b2), uses=n,
                          view_cjk=view_cjk.get(ch, 0))
        if n:
            continue
        if ch in keep:
            blocked.append((ch, '在 --keep 名单里'))
            continue
        if view_cjk.get(ch, 0):
            blocked.append((ch, '在 view 表的 has_cjk=yes 行里出现过 %d 次'
                            % view_cjk[ch]))
            continue
        dead.append(ch)
    return dead, blocked, detail


# ═══════════════════════ ② charset 改写 + 备份 ═══════════════════════

def snapshot_glyphs(atlas, chars, cs):
    """把要删的字的 16x16 字形位图与码位打包 (可还原)。"""
    out = {}
    for ch in chars:
        b1, b2 = cs.enc_pair[ch]
        slot = tcslib.pair_slot(b1, b2)
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        cell = atlas.eng[y:y + 16, x:x + 16]
        out[ch] = dict(pair=[int(b1), int(b2)], slot=int(slot), cell=[int(x), int(y)],
                       ink_px=int(cell.sum()),
                       bits=base64.b64encode(np.packbits(cell.reshape(-1)).tobytes()
                                             ).decode('ascii'))
    return out


def edit_charset(charset_path, dead, meta):
    """从 pair_of 里删掉死字 (只做这一种改动)。先写临时文件再原子替换。"""
    js = json.load(io.open(charset_path, encoding='utf-8'))
    before = len(js['pair_of'])
    for ch in dead:
        if ch not in js['pair_of']:
            raise SystemExit('!! charset 里没有 %r 的 pair_of' % ch)
        del js['pair_of'][ch]
    js['_font_recycle_zh98'] = meta
    tmp = charset_path + '.tmp_r49'
    io.open(tmp, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(js, ensure_ascii=False, indent=1) + '\n')
    os.replace(tmp, charset_path)
    return before, len(js['pair_of'])


# ═══════════════════════ 主流程 ═══════════════════════

def main():
    ap = argparse.ArgumentParser(description='round49 前置补丁: 清残墨 + 回收死字')
    ap.add_argument('src_iso')
    ap.add_argument('dst_iso')
    ap.add_argument('--charset', default=tcslib.CHARSET)
    ap.add_argument('--text-dir', default=None,
                    help='注入表目录 (默认 <src 盘目录>/text, 否则 GR_ZH97/text)')
    ap.add_argument('--build-dir', default=None, help='留底/报告目录 (默认 <dst 盘目录>)')
    ap.add_argument('--keep', default='', help='额外"不许回收"的字')
    ap.add_argument('--no-residue', action='store_true')
    ap.add_argument('--no-recycle', action='store_true')
    ap.add_argument('--no-wipe-dead-glyphs', action='store_true',
                    help='不擦死字的字形像素 (默认擦: 本轮不跑紧凑重排, 靠补丁自己擦)')
    ap.add_argument('--list-only', action='store_true')
    a = ap.parse_args()

    t0 = time.time()
    src = os.path.abspath(a.src_iso)
    dst = os.path.abspath(a.dst_iso)
    bdir = os.path.abspath(a.build_dir or os.path.dirname(dst))
    tmpdir = os.path.join(bdir, 'temp')
    os.makedirs(tmpdir, exist_ok=True)
    charset = os.path.abspath(a.charset)
    text_dir = a.text_dir
    if not text_dir:
        cand = [os.path.join(os.path.dirname(src), 'text'),
                os.path.join(REPO, 'work', 'builds', 'GR_ZH97', 'text')]
        text_dir = next((c for c in cand if os.path.isdir(c)), cand[-1])
    text_dir = os.path.abspath(text_dir)
    for p in (src, charset):
        if not os.path.isfile(p):
            raise SystemExit('!! 找不到 %s' % p)
    if not os.path.isdir(text_dir):
        raise SystemExit('!! 找不到注入表目录 %s' % text_dir)

    print('=' * 78)
    print('[font-cleanup] %s %s' % (TOOL, TOOL_VERSION))
    print('  源盘   : %s' % rel(src))
    print('  产出盘 : %s' % rel(dst))
    print('  charset: %s' % rel(charset))
    print('  注入表 : %s' % rel(text_dir))
    print('=' * 78)

    iso_sha = tcslib.sha256_file(src)
    cs = tcslib.Charset(charset)

    # ---------- ① 用量统计 ----------
    u = usage_counts(text_dir)
    vc = view_cjk_chars(text_dir, u['view'])
    dead, blocked, detail = pick_dead(cs, u['counts'], vc, a.keep)
    named_hit = [ch for ch in NAMED_20 if ch in dead]
    named_use = {ch: u['counts'].get(ch, 0) for ch in NAMED_20 if u['counts'].get(ch, 0)}
    print('[recycle] 注入表 %d 张 / %d 行; 扫到不同字符 %d 个'
          % (len(u['inj']), u['rows'], len(u['counts'])))
    print('[recycle] charset 合法对偶字 %d 个 → 注入表 0 次(=死字) **%d 个**'
          % (len([1 for _c, (b, _t) in cs.enc_pair.items()
                  if tcslib.PAIR_LEAD_LO <= b < tcslib.PAIR_LEAD_HI]), len(dead)))
    print('[recycle] 死字清单: %s' % ''.join(dead))
    print('[recycle] 用户点名的 20 个人名字: 命中 %d/20, 其中注入表出现过的: %s'
          % (len(named_hit), named_use or '无 (全部 0 次)'))
    if blocked:
        print('[recycle] 因风险**不回收**的: %s'
              % '; '.join('%s(%s)' % (c, w) for c, w in blocked))
    if u['rows'] == 0:
        raise SystemExit('!! 注入表 0 行 —— 空的表不能用来判死字, 拒绝回收')

    # ---------- ② 残墨 ----------
    res = None
    if not a.no_residue:
        # 用"改 charset 之前"的映射算残墨 (纯几何口径, 与回收决策解耦)
        pre_cs = os.path.join(tmpdir, 'charset_for_residue.json')
        shutil.copyfile(charset, pre_cs)
        res = font_residue.compute(src, pre_cs, verbose=True)
        r = res['doc']['residue']
        print('[residue] 残墨 **%d px** / 全图墨 %d (%.2f%%); 块 %d 个'
              % (r['total_px'], res['doc']['atlas']['ink_total'], r['ratio_pct'],
                 r['residue_regions']))
    if a.list_only:
        print('[list-only] 到此为止 (没有写任何文件)')
        return 0

    # ---------- ③ 留底 + 清残墨(+死字字形) + 改 charset ----------
    cs_before = os.path.join(tmpdir, 'charset_before_font_cleanup.json')
    if not os.path.isfile(cs_before):
        shutil.copyfile(charset, cs_before)
    print('[backup] charset 改前留底 → %s' % rel(cs_before))

    # 死字的格子 (按"改 charset 之前"的映射算; 本轮不跑重排 ⇒ 必须自己擦干净)
    #   ★ 口径 (round49 实测, 见 font_residue.ft_window_alignment): **FT 矩形本身就是采样窗**
    #     ⇒ 与 `repack_font.classify()` 同口径: 只要格子不与**原矩形**相交, 就整格擦白。
    #     (±(4,2) 的膨胀只用来当"清理保护罩"的保守上界; 用它否决会让 40 个格子白留 32 px。)
    dead_mask, dead_info, dil_hits = None, [], []
    dead_ink_px = 0
    if dead and not a.no_recycle and not a.no_wipe_dead_glyphs:
        atlas_src = res['atlas'] if res else None
        ft_raw = res['sampler']['ft_raw'] if res else None
        ft_dil = res['sampler']['ft_dil'] if res else None
        if ft_raw is None:
            f0 = dump_font.load_font(src)
            S0 = font_residue.enumerate_sampler(cs, f0['faces'], f0['atlas']['w'],
                                                f0['atlas']['h'])
            ft_raw, ft_dil = S0['ft_raw'], S0['ft_dil']
        if atlas_src is not None:
            dead_mask = np.zeros((atlas_src.h, atlas_src.w), bool)
        else:
            f0 = dump_font.load_font(src)
            dead_mask = np.zeros((f0['atlas']['h'], f0['atlas']['w']), bool)
        for ch in dead:
            b1, b2 = cs.enc_pair[ch]
            slot = tcslib.pair_slot(b1, b2)
            x, y = tcslib.atlas_cell_xy_engine_view(slot)
            if ft_raw[y:y + 16, x:x + 16].any():
                raise SystemExit('!! 死字 %r 的格子与 FT 记录矩形(原矩形)相交 (slot=%d) —— '
                                 '这与 repack 的"可用格"口径矛盾, 拒绝擦, 人工看' % (ch, slot))
            n_dil = int(ft_dil[y:y + 16, x:x + 16].sum())
            if n_dil:
                dil_hits.append(dict(char=ch, slot=slot, cell=[int(x), int(y)], px=n_dil))
            dead_mask[y:y + 16, x:x + 16] = True
            dead_info.append(dict(char=ch, slot=slot, cell=[int(x), int(y)]))
        n_dead_ink = int((atlas_src.eng & dead_mask).sum()) if atlas_src is not None else -1
        dead_ink_px = max(0, n_dead_ink)
        print('[wipe] 死字字形: %d 个字 / %d 格 / **%d px** 墨 ⇒ 全部擦白'
              % (len(dead), len(dead_info), n_dead_ink))
        if dil_hits:
            print('[wipe] 说明: 其中 %d 个格与 **膨胀 ±(%d,%d) 的邻格采样窗** 有 %d px 重叠 —— '
                  '按实测口径(矩形=采样窗)这与"可用格"不矛盾, 且 round46 重排本来就把所有可用格'
                  '整格清零过 ⇒ 照擦。明细见报告 dead_glyphs.dilated_neighbour_overlap'
                  % (len(dil_hits), tcslib.GLYPH_TOL_X, tcslib.GLYPH_TOL_Y,
                     sum(d['px'] for d in dil_hits)))

    clear_mask = None
    if res is not None:
        clear_mask = res['residue'].copy()
        if dead_mask is not None:
            clear_mask |= dead_mask
        cleared = font_residue.clear_on_iso(src, dst, clear_mask, res['atlas'],
                                            res['font'], verbose=True)
    else:
        shutil.copyfile(src, dst)
        print('  [copy] --no-residue: 只拷盘, 不动像素')

    n_before = n_after = None
    if dead and not a.no_recycle:
        atlas = res['atlas'] if res else None
        if atlas is None:                       # --no-residue: 现装一次图集 (只为留底)
            f0 = dump_font.load_font(dst)
            am = f0['atlas']
            atlas = repack_font.Atlas(am['pak'], am['px_off'], am['px_size'],
                                      am['w'], am['h'], am['psm'])
        snap = snapshot_glyphs(atlas, dead, cs)
        bak = os.path.join(tmpdir, 'font_recycle_backup.json')
        io.open(bak, 'w', encoding='utf-8', newline='\n').write(json.dumps(dict(
            tool=TOOL, tool_version=TOOL_VERSION, round=ROUND,
            generated=time.strftime('%Y-%m-%d %H:%M:%S'),
            src_iso=rel(src), src_iso_sha256=iso_sha,
            charset=rel(charset), charset_before=rel(cs_before),
            count=len(dead), chars=''.join(dead),
            restore_help=('把 glyphs[ch] 的 bits 用 np.unpackbits 还原成 16x16 布尔图, '
                          '写回 cs.pair_of[ch] 指定的槽位, 再写回 charset 的 pair_of 即可; '
                          '但槽位可能已被别人占用 —— 建议改派到一个空闲槽。'),
            glyphs=snap), ensure_ascii=False, indent=1) + '\n')
        print('[backup] 被删字的码位 + 字形位图 → %s (%d 个字)'
              % (rel(bak), len(dead)))
        meta = dict(
            note=('round49: 这些人名用字在**全部注入表**里出现 0 次 (人名已改回英文) '
                  '⇒ 回收其码位, 释放字位; 字形像素由同一补丁擦白 '
                  '(本轮不跑紧凑重排, 故不依赖它)。'),
            tool=TOOL, tool_version=TOOL_VERSION, applied=time.strftime('%Y-%m-%d %H:%M:%S'),
            removed=len(dead), chars=''.join(dead),
            scanned_tables=u['inj'], scanned_rows=u['rows'],
            criteria='出现 0 次 (注入表全部列) 且 未出现在任何 view 表的 has_cjk=yes 行',
            backup=rel(bak), charset_before=rel(cs_before),
            user_named_20=NAMED_20,
            user_named_20_all_dead=bool(len(named_hit) == len(NAMED_20)),
        )
        n_before, n_after = edit_charset(charset, dead, meta)
        print('[charset] pair_of %d → %d (−%d); 已写入 %s'
              % (n_before, n_after, n_before - n_after, rel(charset)))
    elif dead:
        print('[charset] --no-recycle: 死字一个都没删')
    else:
        print('[charset] 没有死字可回收')

    # ---------- ④ 报告 ----------
    doc = dict(
        tool=TOOL, tool_version=TOOL_VERSION, round=ROUND,
        generated=time.strftime('%Y-%m-%d %H:%M:%S'),
        src_iso=rel(src), src_iso_sha256=iso_sha,
        dst_iso=rel(dst), dst_iso_sha256=tcslib.sha256_file(dst),
        charset=rel(charset), charset_before=rel(cs_before),
        text_dir=rel(text_dir),
        usage=dict(tables=u['inj'], rows=u['rows'], distinct_chars=len(u['counts']),
                   per_file_rows={k: len(v) for k, v in u['per_file'].items()}),
        recycle=dict(dead_count=len(dead), dead=''.join(dead),
                     blocked=[dict(char=c, why=w) for c, w in blocked],
                     pair_of_before=n_before, pair_of_after=n_after,
                     named20_in_dead=''.join(named_hit),
                     named20_used=named_use,
                     per_char=dict((c, detail[c]) for c in dead),
                     backup=rel(os.path.join(tmpdir, 'font_recycle_backup.json'))
                     if dead and not a.no_recycle else None),
        residue=dict(total_px=res['doc']['residue']['total_px'],
                     by_kind=res['doc']['residue']['by_kind'],
                     regions=res['doc']['residue']['residue_regions'],
                     slots=res['doc']['residue']['residue_slots'],
                     cleared_px=(cleared or {}).get('pixels_cleared', 0),
                     empty_index=(cleared or {}).get('empty_index'),
                     report=rel(os.path.join(tmpdir, 'font_residue', 'residue_report.md')))
        if res else None,
        dead_glyphs=dict(count=len(dead), cells=len(dead_info), detail=dead_info,
                         wiped=bool(dead_mask is not None),
                         dilated_neighbour_overlap=dil_hits,
                         wiped_cell_area_px=int(dead_mask.sum()) if dead_mask is not None else 0,
                         wiped_ink_px=dead_ink_px,
                         cleared_with_residue_px=(cleared or {}).get('pixels_cleared', 0)
                         - (res['doc']['residue']['total_px'] if res else 0),
                         note=('wiped_cell_area_px = %d 格 × 256 px 的**区域**; wiped_ink_px = '
                               '这些区域里真正的墨 (== 图集墨量下降的另一半); '
                               'cleared_with_residue_px 是"同一次写入里, 除残墨之外那部分区域"'
                               '(== wiped_cell_area_px)'
                               % len(dead_info))),
        atlas=dict(ink_before=(res['doc']['atlas']['ink_total'] if res else None),
                   ink_after=None),
        seconds=round(time.time() - t0, 1),
    )
    # 擦完之后的图集墨量 (回读现算, 不写死)
    try:
        f2 = dump_font.load_font(dst)
        a2 = f2['atlas']
        A2 = repack_font.Atlas(a2['pak'], a2['px_off'], a2['px_size'],
                               a2['w'], a2['h'], a2['psm'])
        doc['atlas']['ink_after'] = int(A2.eng.sum())
    except Exception as e:                                               # noqa: BLE001
        doc['atlas']['ink_after'] = 'error: %s' % e
    rp = os.path.join(tmpdir, 'font_cleanup_report.json')
    io.open(rp, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
    print('')
    print('-' * 78)
    print('  清真残墨        : %s px'
          % (doc['residue']['total_px'] if doc['residue'] else '—'))
    print('  擦死字字形      : %d 格 × 256 px = %d px 区域 (其中墨 %d px)'
          % (doc['dead_glyphs']['cells'], doc['dead_glyphs']['wiped_cell_area_px'],
             doc['dead_glyphs']['wiped_ink_px']))
    print('  图集墨量        : %s → %s texel' % (doc['atlas']['ink_before'],
                                                doc['atlas']['ink_after']))
    print('  回收死字        : %d 个 → charset pair_of %s → %s'
          % (len(dead), n_before, n_after))
    print('  产出盘 sha      : %s' % doc['dst_iso_sha256'][:16])
    print('  报告            : %s' % rel(rp))
    print('-' * 78)
    return 0


if __name__ == '__main__':
    sys.exit(main())
