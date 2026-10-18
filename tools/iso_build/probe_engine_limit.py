# -*- coding: utf-8 -*-
r"""probe_engine_limit.py — **实机探针**: 量引擎的对偶码 lead 上界 (= 字库真实可用容量)。

═══════════════════════════════════════════════════════════════════════════════
它回答什么问题
═══════════════════════════════════════════════════════════════════════════════
引擎对偶码寻址: `slot = (lead-0xA1)*94 + (trail-0xA1)`; 图集 62x28 = 1736 格。
**但一个 slot 能不能被画出来, 取决于引擎把不把那个 lead 当"双字节首字节"。**
本工具把同一个汉字的字形**额外抄一份**到高 lead 的空白格里, 再在同屏写一行对照串:

    PROBE
    O: 我国山          ← 对照: 现役码位 (lead 0xA5/0xA6/0xA7), 本来就能显示
    AD: 我国山         ← 新格 + 一个**已知可用**的 lead (写盘法对照: 证明"新写的字形真的生效")
    AE: 我国山         ← 试探 lead 0xAE (方案 C 扩出来的第一档)
    B0: 我国山         ← 试探 lead 0xB0 (gate `sltiu lead,0xB1` 允许的**最后一档**)
    B1: 我国山         ← 试探 lead 0xB1 (预期**不可用**: gate 之外的第一个字节)
    S: B2 B1 B5        ← 单字节码带: 0xB2 = 正常汉字; 0xB1/0xB5 = 手柄图标码?

判据 (实拍):
  · `O:` 正常  ⇒ 探针本身有效 (现役字形确实能显示);
  · `AD:` 正常 ⇒ **写盘法有效** (新格 + 新字形真的被引擎采样) ⇒ 后面几行的失败只可能是 lead 被拒;
  · `AE:`/`B0:` 正常 ⇒ 该 lead 可用; 渲染成别的字/空白 ⇒ 该 lead 被引擎当单字节;
  · `B1:` 只要能看出与 `O:` 不同 ⇒ 上界 = 0xB1 (与 ELF gate 一致)。
每行都带 ASCII 标签, 故**无论页面初始滚动在哪一行**都能认出来。

═══════════════════════════════════════════════════════════════════════════════
为什么 payload 要"探针块 + 空格"反复交错
═══════════════════════════════════════════════════════════════════════════════
`<text>` 载荷长度**必须一字不差** (注入器/回读都按等长校验; blobl 变长会位移后续字节)。
而 round61/63 实拍发现: 该正文框**初始滚动不在开头**(实拍窗口落在全文第 52/65 行,
见 work/builds/GR_ZH98/temp/r63/tp_unicode_report.json + drawlog) —— 所以不能只把探针写在开头。
⇒ 本工具把"探针块 + 90 个空格"**反复铺满整个载荷**:
     · 空格只有 3px 宽 (64 个/行) ⇒ 每个周期只多 1.4 个视觉行;
     · 任何 ~10 行的可视窗口里都必然包含**一整块**探针;
     · 总视觉行数 ≈ 原来的 1.1 倍 (不会触发 round60 的"文字太多 ⇒ 整页空白")。

═══════════════════════════════════════════════════════════════════════════════
硬门禁 (任何一条不过 ⇒ 非 0 退出 / 不写盘)
═══════════════════════════════════════════════════════════════════════════════
  ① 目标格**零墨** + 不被**任何** FT 记录矩形 (3 个 face) 覆盖 + 不在 ATLAS_ENGINE_SINGLE_CELLS;
  ② 目标 slot 不被现役 charset 的任何对偶码占用;
  ③ 除目标 `<text>` 区间外 blob 逐字节不变 (前缀相同 + 后缀相同);
  ④ LZO 重压回环 (`lzo_subs(帧) == 新 blob` 逐字节) + 压缩后不超槽 + ISO 尺寸不变;
  ⑤ 回读: 盘上解出的 blob == 要写的 blob; 图集像素 == 目标图; 其它 `<text>`/条目逐字节不变。

═══════════════════════════════════════════════════════════════════════════════
用法
═══════════════════════════════════════════════════════════════════════════════
  python tools/iso_build/probe_engine_limit.py <src.iso> <dst.iso>
         [--chars 我国山] [--leads AD,AE,B0,B1] [--singles B2,B1,B5]
         [--item-name 开发访谈 1] [--charset PATH] [--report R.json]
         [--dry-run] [--label PROBE]

  · 版本名请用 `GR_TEST_*` (make_build.py 的断言只认 `GR_ZH<数字>` / `GR_TEST_*`),
    推荐构筑命令 (★ 必须关掉自动字库重排, 否则它会把字形搬回 slot 0..N-1):
      python tools/iso_build/make_build.py GR_TEST_PROBE_LEAD --from work/builds/GR_ZH109 \
             --patch tools/iso_build/probe_engine_limit.py \
             --no-font-compact --no-textdump --no-text-snapshot --no-font-dump
    然后实机:
      python tools/capture/nav_hook.py GR_TEST_PROBE_LEAD --tag probe

  · 本工具**只读**现役 charset (tools/font_pipeline/data/charset_compiled_zh16.json),
    绝不写它 (实验用的映射全在内存里)。
"""
import argparse
import hashlib
import io
import json
import os
import shutil
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
for _p in (HERE, os.path.join(REPO, 'tools', 'text_csv')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:                                                            # noqa: BLE001
    pass

import tcslib                                                              # noqa: E402
import dump_font as D                                                      # noqa: E402
import inject_text_csv as inj                                              # noqa: E402
import make_font_testpage as MTP                                           # noqa: E402
import patch_zh94_glyph_align as A94                                       # noqa: E402

CHARSET = tcslib.CHARSET
DEFAULT_SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
DEFAULT_CHARS = '我国山'
DEFAULT_LEADS = 'AD,AE,B0,B1'
DEFAULT_SINGLES = 'B2,B1,B5'
DEFAULT_ITEM = '开发访谈 1'
DEFAULT_LABEL = 'PROBE'
GAP_SPACES = 90            # 每个探针块后面的空格数 (≈1.4 个视觉行)
SAFE_TRAIL_LO = 0xB1       # trail 只从 0xB1 起挑: 万一 lead 被当单字节, 也不会吞掉下一个字
SAFE_TRAIL_HI = 0xFE


def rel(p):
    try:
        r = os.path.relpath(p, REPO)
    except ValueError:
        return p.replace('\\', '/')
    return r.replace('\\', '/') if not r.startswith('..') else p.replace('\\', '/')


def parse_hexlist(s):
    out = []
    for x in str(s or '').replace(' ', ',').split(','):
        x = x.strip()
        if x:
            out.append(int(x, 16))
    return out


# ═════════════════════════ 图集: 墨量 + FT 记录矩形掩膜 ═════════════════════════

class AtlasInk:
    """只读的图集视图: 引擎口径灰度 + 全部 face 的 FT 记录矩形掩膜。"""

    def __init__(self, font):
        self.atlas = font['atlas']
        self.faces = font['faces']
        self.W, self.H = self.atlas['w'], self.atlas['h']
        self.gray = np.frombuffer(D.atlas_gray(self.atlas, 'engine'),
                                  dtype=np.uint8).reshape(self.H, self.W)
        self.ink = self.gray == 0
        self.rect = np.zeros((self.H, self.W), dtype=bool)
        self.n_rect = 0
        for (_nm, _fld, recs) in self.faces:
            for r in recs:
                _b0, _b1, u0, v0, u1, v1 = r
                if u1 <= u0 or v1 <= v0:
                    continue
                self.n_rect += 1
                self.rect[max(0, v0):min(self.H, v1), max(0, u0):min(self.W, u1)] = True

    def cell(self, row, col):
        x = tcslib.CW * col
        y = tcslib.GRID_Y0 + tcslib.CH * (row + (tcslib.GRID_SKIP_ROWS
                                                if row >= tcslib.GRID_SKIP_ROW else 0))
        return x, y

    def cell_status(self, row, col):
        """返回 (x, y, 墨量, 被记录压的像素数, 冲突说明 或 None); 越界时墨量/压 = -1。"""
        x, y = self.cell(row, col)
        if x + tcslib.CW > self.W or y + tcslib.CH > self.H:
            return x, y, -1, -1, '越出图集下沿/右沿'
        return (x, y, int(self.ink[y:y + tcslib.CH, x:x + tcslib.CW].sum()),
                int(self.rect[y:y + tcslib.CH, x:x + tcslib.CW].sum()),
                tcslib.ATLAS_ENGINE_SINGLE_CELLS.get((row, col)))


# ═════════════════════════ 挑目标格 ═════════════════════════

def pick_free_slot(ai, used_slots, lead, prefer_trails=None, n_want=1):
    """给 lead 挑 n_want 个"干净"的 trail (engine 格零墨 + 无记录矩形 + 无冲突 + slot 未占用)。

    安全约束 (缺一不可):
      · trail ∈ [0xB1, 0xFE]  ⇒ 万一 lead 被引擎当**单字节**, trail 也不会被当新 lead 吞掉后一个字;
      · 16x16 格完全在图集内 (col ≤ 61 ⇒ x ≤ 976, 永不落在"回绕列" x ≥ 992);
      · 格子里零墨、没有 FT 记录矩形压着、不在 ATLAS_ENGINE_SINGLE_CELLS;
      · 该 slot 没有被现役 charset 的对偶码占用。
    """
    out = []
    cands = list(prefer_trails or range(SAFE_TRAIL_LO, SAFE_TRAIL_HI + 1))
    for trail in cands:
        if not (SAFE_TRAIL_LO <= trail <= SAFE_TRAIL_HI):
            continue
        slot = tcslib.pair_slot(lead, trail)
        if slot in used_slots:
            continue
        row, col = slot // tcslib.NCOL, slot % tcslib.NCOL
        x, y, n_ink, n_rec, conflict = ai.cell_status(row, col)
        if n_ink != 0 or n_rec != 0 or conflict:
            continue
        out.append(dict(lead=lead, trail=trail, slot=slot, row=row, col=col, x=x, y=y))
        if len(out) >= n_want:
            break
    return out


# ═════════════════════════ 探针文本 ═════════════════════════

def build_probe_text(rows, singles, label, nbytes_default):
    """拼出探针文本 (bytes)。rows = [(标签, [(char, (lead,trail)), ...]), ...]。

    结构: `<label>{br}` + 每组一行 `XX: 我国山{br}` + 单字节行 `S: B2 B1 B5{p}` + 90 个空格。
    返回 (payload, 需替换的 info)。
    """
    out = bytearray()
    out += label.encode('ascii') + b'{br}'

    def one_line(tag, pairs):
        out.extend(tag.encode('ascii') + b': ')
        for i, (_ch, pr) in enumerate(pairs):
            if i:
                out.extend(b' ')
            out.extend(bytes(pr))
        out.extend(b'{br}')

    for tag, pairs in rows:
        one_line(tag, pairs)
    out.extend(b'S: ')
    for i, b in enumerate(singles):
        if i:
            out.extend(b' ')
        out.append(b)
    out.extend(b'{p}')
    return bytes(out)


# ═════════════════════════ main ═════════════════════════

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src', nargs='?', default=DEFAULT_SRC)
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--chars', default=DEFAULT_CHARS, help='对照字 (现役 charset 里的对偶字), 默认 %s'
                    % DEFAULT_CHARS)
    ap.add_argument('--leads', default=DEFAULT_LEADS,
                    help='要试探的 lead (逗号分隔十六进制), 默认 %s' % DEFAULT_LEADS)
    ap.add_argument('--singles', default=DEFAULT_SINGLES,
                    help='单字节码带一行要试的字节, 默认 %s' % DEFAULT_SINGLES)
    ap.add_argument('--item-name', default=DEFAULT_ITEM)
    ap.add_argument('--charset', default=CHARSET)
    ap.add_argument('--label', default=DEFAULT_LABEL)
    ap.add_argument('--gap', type=int, default=GAP_SPACES, help='每块后的空格数 (默认 %d)' % GAP_SPACES)
    ap.add_argument('--report', default=None)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    src = os.path.abspath(a.src)
    if not os.path.isfile(src):
        raise SystemExit('!! 基盘不存在: %s' % src)
    dst = os.path.abspath(a.dst or src)
    chars = [ch for ch in a.chars if ch.strip()]
    leads = parse_hexlist(a.leads)
    singles = parse_hexlist(a.singles)
    print('=' * 78)
    print('引擎 lead 上限探针: 同一批字形抄到高 lead 格, 同屏对照')
    print('  src = %s' % rel(src))
    print('  dst = %s' % rel(dst))
    print('  对照字 = %s; 试探 lead = %s; 单字节 = %s'
          % (''.join(chars), ' '.join('%02X' % x for x in leads),
             ' '.join('%02X' % x for x in singles)))
    print('=' * 78)

    # ---------- ① 只读装载: 图集 / FT / charset ----------
    font = D.load_font(src)
    ai = AtlasInk(font)
    _nm, psm, aw, ah, _clut, px_size, PX = next(
        (r for r in tcslib.parse_pak_records(font['atlas']['pak'])
         if r[0] == 'new_font_revised'))
    print('[atlas] psm=0x%02X %dx%d px_off=0x%X; 引擎图墨 %d px; FT 记录矩形 %d 条 (3 个 face)'
          % (psm, aw, ah, PX, int(ai.ink.sum()), ai.n_rect))

    cs = tcslib.Charset(a.charset)
    used_slots = set()
    for _ch, pr in cs.enc_pair.items():
        used_slots.add(tcslib.pair_slot(*pr))
    n_dual = tcslib.pair_capacity()
    print('[charset] %s: 对偶 %d 条 (占 %d 个 slot) + 单字节 %d 条; 合法对偶空间 %d'
          % (rel(a.charset), len(cs.enc_pair), len(used_slots), len(cs.enc_single), n_dual))

    # ---------- ② 对照组: 现役码位 (只读, 不写格) ----------
    rows = []
    orig = []
    glyphs = {}
    for ch in chars:
        pr = cs.enc_pair.get(ch)
        if pr is None:
            raise SystemExit('!! 对照字 %r 在 charset 里没有**对偶码** (本探针只探对偶路径)' % ch)
        slot = tcslib.pair_slot(*pr)
        row, col = slot // tcslib.NCOL, slot % tcslib.NCOL
        x, y, n_ink, _n_rec, _cf = ai.cell_status(row, col)
        if n_ink <= 0:
            raise SystemExit('!! 对照字 %r 的现役格 slot=%d (row=%d col=%d) 没有墨 (墨=%d) —— '
                             '它本来就显示不出来, 不能当对照' % (ch, slot, row, col, n_ink))
        print('[对照] %s 现役 pair=%02X%02X slot=%4d (row=%2d col=%2d) cell=(%4d,%3d) 墨=%3d'
              % (ch, pr[0], pr[1], slot, row, col, x, y, n_ink))
        orig.append((ch, pr))
        glyphs[ch] = ai.gray[y:y + tcslib.CH, x:x + tcslib.CW].copy()
    rows.append(('O', orig))

    # ---------- ③ 每个 lead 一行: 挑干净格 + 记录要抄的字形 ----------
    plan = []
    for lead in leads:
        got = pick_free_slot(ai, used_slots, lead, n_want=len(chars))
        if len(got) < len(chars):
            raise SystemExit('!! lead=0x%02X 只找到 %d 个干净格 (要 %d 个) —— 图集里没有足够空位'
                             % (lead, len(got), len(chars)))
        pairs = []
        for ch, t in zip(chars, got):
            used_slots.add(t['slot'])                 # 同一轮内不复用
            print('[新格] %s ← lead=%02X trail=%02X slot=%4d (row=%2d col=%2d) cell=(%4d,%3d)'
                  % (ch, t['lead'], t['trail'], t['slot'], t['row'], t['col'], t['x'], t['y']))
            t['char'] = ch
            plan.append(t)
            pairs.append((ch, (t['lead'], t['trail'])))
        rows.append(('%02X' % lead, pairs))

    # ---------- ④ 拼探针文本, 交错铺满原载荷长度 ----------
    iso = tcslib.Iso(src)
    spec = tcslib.RES['SFXML']['copies'][0]
    c = inj.Container(iso, 'SFXML', spec, cs)
    tgt = MTP.find_target(c.blob, cs, a.item_name, '')
    L = len(tgt['data'])
    print('[容器] %s = %s#%d 槽 %d B / 帧 %d B (余 %d) / 展开 %d B / %d 子流'
          % (c.tag, c.img, c.idx, c.slot, c.frame_len, c.slot - c.frame_len,
             len(c.blob), len(c.subs)))
    print('[目标] <item name=%r> <text> 载荷 [0x%X, 0x%X) = %d B'
          % (a.item_name, tgt['a'], tgt['b'], L))

    block = build_probe_text(rows, singles, a.label, L) + b' ' * a.gap
    n_rep = L // len(block)
    if n_rep < 1:
        raise SystemExit('!! 探针块 %d B > 载荷 %d B' % (len(block), L))
    new = block * n_rep
    pad = L - len(new)
    if pad:
        # 收尾用"空格 + 一个截到行边界的碎块", 保证不切断 {br}/{p}
        tail = block[:pad]
        cut = tail.rfind(b'{br}')
        if cut > 0 and pad - (cut + 4) > 0:
            tail = tail[:cut + 4] + b' ' * (pad - cut - 4)
        new += tail
    assert len(new) == L, (len(new), L)
    print('[文本] 探针块 %d B × %d 遍 + 收尾 %d B = %d B (与原文等长, 零位移)'
          % (len(block), n_rep, pad, len(new)))
    print('[文本] 每块 = %r … %r' % (block[:88], block[-40:]))

    # 守卫: 连续 0x80..0x9F > 3 会让引擎取不到整段文本 (round61 实拍)
    run = best = 0
    for b in new:
        run = run + 1 if 0x80 <= b <= 0x9F else 0
        best = max(best, run)
    if best > 3:
        raise SystemExit('!! 载荷里有 %d 个连续 0x80..0x9F 字节 (上限 3)' % best)
    print('[守卫] 连续 0x80..0x9F 最长 %d 个 (≤3) ✓' % best)

    # ---------- ⑤ 改图集像素 ----------
    A = A94.Atlas(bytearray(font['atlas']['pak']), PX, px_size)
    nb = np.frombuffer(bytes(A.nib), dtype=np.uint8)
    tot = np.bincount(nb & 0x0F, minlength=16) + np.bincount(nb >> 4, minlength=16)
    tot[0] = 0
    empty_val = int(np.argmax(tot))
    assert 1 <= empty_val <= 15, empty_val
    print('[像素] 「空」= 调色板索引 %d' % empty_val)

    before = A.eng.copy()
    for t in plan:
        g = glyphs[t['char']]
        y0, x0 = t['y'], t['x']
        assert not before[y0:y0 + tcslib.CH, x0:x0 + tcslib.CW].any(), ('目标格不空!', t)
        A.eng[y0:y0 + tcslib.CH, x0:x0 + tcslib.CW] = (g == 0)
    changed = np.where(A.eng != before)
    print('[像素] 抄 %d 个字形, 变更 %d px' % (len(plan), len(changed[0])))
    # 只允许动"计划内的格"
    allowed = np.zeros((ai.H, ai.W), dtype=bool)
    for t in plan:
        allowed[t['y']:t['y'] + tcslib.CH, t['x']:t['x'] + tcslib.CW] = True
    outside = int((changed[0][~allowed[changed]]).size)
    assert outside == 0, '有像素改在计划格之外'
    for y, x in zip(changed[0].tolist(), changed[1].tolist()):
        A.set_px(int(x), int(y), bool(A.eng[y, x]), empty_val)
    back, _cov = A.decode_engine()
    assert (back == A.eng).all(), '回写后引擎图不一致'
    print('[像素] 回写完成, 重新解出引擎图核对一致 ✓')

    # ---------- ⑥ 改 blob + 门禁①/④ ----------
    new_blob = c.blob[:tgt['a']] + new + c.blob[tgt['b']:]
    loc = MTP.locality(c.blob, new_blob, tgt['a'], tgt['b'])
    print('[门禁①] blob %d → %d B (Δ%+d); 前缀相同=%s 后缀相同=%s; 区间外差异 %d 字节'
          % (len(c.blob), len(new_blob), loc['delta'], loc['prefix_ok'], loc['suffix_ok'],
             loc['n_outside']))
    if not (loc['prefix_ok'] and loc['suffix_ok']) or loc['n_outside']:
        raise SystemExit('!! 门禁① 不过: 改动落在目标 <text> 之外')
    frame, n_rep2 = c.repack(new_blob)
    back2 = b''.join(s[0] for s in tcslib.lzo_subs(frame))
    if back2 != new_blob:
        raise SystemExit('!! LZO 回环断言失败')
    print('[门禁④] 重压 %d 子流 → 帧 %d B (槽 %d B, 余 %d) + 回环 ✓'
          % (n_rep2, len(frame), c.slot, c.slot - len(frame)))
    if len(frame) > c.slot:
        raise SystemExit('!! 压缩后超出槽位')
    if a.dry_run:
        print('[dry ] 不写盘。')
        iso.close()
        return 0

    # ---------- ⑦ 写盘 ----------
    if src != dst:
        shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(c.entry['iso_off'])
        f.write(frame + b'\x00' * (c.slot - len(frame)))
        f.seek(font['pak_e']['iso_off'] + PX)
        f.write(bytes(A.nib))
    if os.path.getsize(src) != os.path.getsize(dst):
        raise SystemExit('!! ISO 尺寸变了')
    iso.close()

    # ---------- ⑧ 回读复核 ----------
    iso2 = tcslib.Iso(dst)
    e2 = iso2.img_entry(c.lba, c.idx)
    if (e2['stored'], e2['off'], e2['real']) != (c.entry['stored'], c.entry['off'], c.entry['real']):
        raise SystemExit('!! 回读: IMG 条目表被改了')
    blob2 = b''.join(s[0] for s in tcslib.lzo_subs(iso2.read(e2['iso_off'], e2['stored'])))
    if blob2 != new_blob:
        raise SystemExit('!! 回读: 盘上 blob != 要写的 blob')
    tgt2 = MTP.find_target(blob2, cs, a.item_name, '')
    if tgt2['data'] != new:
        raise SystemExit('!! 回读: <text> 载荷不逐字节相同')
    eb, ea = MTP.parse_entries(c.blob), MTP.parse_entries(blob2)
    changed_k = [k for k, v in eb.items() if ea[k] != v]
    tk = [k for (k, _o, _l, d) in tcslib.parse_sfxml(c.blob) if d == tgt['data']]
    if len(changed_k) != 1 or changed_k != tk:
        raise SystemExit('!! 回读: 变动的 <text> = %s (只允许 %s)' % (changed_k, tk))
    # 图集回读
    font2 = D.load_font(dst)
    _n2, _p2, _w2, _h2, _c2, px2, PX2 = next(
        (r for r in tcslib.parse_pak_records(font2['atlas']['pak'])
         if r[0] == 'new_font_revised'))
    if PX2 != PX:
        raise SystemExit('!! 回读: 像素容器偏移变了')
    A2 = A94.Atlas(bytearray(font2['atlas']['pak']), PX2, px2)
    if not (A2.decode_engine()[0] == A.eng).all():
        raise SystemExit('!! 回读: 盘上引擎图 != 目标图')
    print('[回读] blob 逐字节 ✓; <text> 载荷载荷 %d B 相同 ✓; 只有 %s 变 ✓; 图集引擎图一致 ✓'
          % (len(new), tk))
    sha = tcslib.sha256_file(dst)
    iso2.close()

    # ---------- ⑨ 报告 + 导航命令 ----------
    rep = dict(
        tool='tools/iso_build/probe_engine_limit.py', src=rel(src), dst=rel(dst),
        iso_sha256=sha, chars=''.join(chars), leads=['0x%02X' % x for x in leads],
        singles=['0x%02X' % x for x in singles],
        orig=[dict(char=ch, pair='%02X%02X' % pr, slot=tcslib.pair_slot(*pr)) for ch, pr in orig],
        placed=[dict(char=t['char'], lead='0x%02X' % t['lead'], trail='0x%02X' % t['trail'],
                     slot=t['slot'], row=t['row'], col=t['col'], x=t['x'], y=t['y']) for t in plan],
        text_bytes=len(new), block_bytes=len(block), block_repeats=n_rep, tail_pad=pad,
        container=dict(img=c.img, idx=c.idx, slot=c.slot, blob=len(c.blob),
                       payload_off=tgt['a'], payload_len=L, frame_after=len(frame),
                       headroom=c.slot - len(frame), substreams=n_rep2),
        elite=dict(gate=['0x%02X' % x for x in leads]),
        gates=dict(g1_ok=bool(loc['prefix_ok'] and loc['suffix_ok'] and not loc['n_outside']),
                   lzo_loopback=True, size_preserved=True, g5_changed_texts=changed_k),
    )
    rp = a.report or os.path.join(os.path.dirname(dst), 'temp', 'probe_engine_limit.json')
    os.makedirs(os.path.dirname(rp), exist_ok=True)
    io.open(rp, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(rep, ensure_ascii=False, indent=1) + '\n')
    ver = os.path.basename(os.path.dirname(dst))
    print('\n[报告] %s' % rel(rp))
    print('[完成] %s  sha256=%s' % (rel(dst), sha))
    print('\n下一步 (实机取证, 约 6 分钟):')
    print('  python tools/capture/nav_hook.py %s --tag probe' % ver)
    print('  → 看 %s/temp/dump_probe/probe_page.png' % rel(os.path.dirname(dst)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
