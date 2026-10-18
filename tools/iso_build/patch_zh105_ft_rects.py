# -*- coding: utf-8 -*-
r"""patch_zh105_ft_rects.py — round55: 把那 7 个"被记录压住"的可用格解放出来

## 问题（用户发现）
有 7 个空白对偶槽位被 FT 记录矩形压着 ⇒ 往里面写新字, 像素就会落进那条记录的采样窗
⇒ 凡是渲染对应码位的地方都会把那个字画出来。压住它们的记录:
  · 0xAE / 0xAF / 0xB0            —— 各压 1 个格子(全覆盖)
  · 0x20(空格) / 0x7F / 0xA1..0xAD / 0xB1 / 0xB5(图标) —— 17 条**共用同一个矩形**
    (136,420,146,436), 压住 4 个格子

## 修法
这些码位引擎要么不画、要么从**另一张贴图**画图标、要么画空格 —— 它们指哪儿都是**空白**。
⇒ 把它们的记录矩形改指到一片**没人用的空白区**: 回绕列 `x=992..1007`(对偶格公式永不采样、
且没有任何槽位/记录) ⇒
  · 那 7 个格子变成**真正安全可用** (322 → 329)
  · 画面**完全不变** (空白 → 空白)
  · 本补丁**一个像素都不改**, 只改 FONT.RES 的记录表

## 安全性
· 只改这些记录的 u0/v0/u1/v1; `pad`/`advance` 逐条原值核对;
· 硬断言: 目标矩形必须**无墨、不被任何对偶槽位覆盖、不被任何其它记录覆盖**;
· 写后回读: 记录表逐字节核对(只许 u/v 变); 图集像素**零改动**; 重新分析后
  "空白但被记录压" 必须为 0。

用法:
  python tools/iso_build/patch_zh105_ft_rects.py <src.iso> <dst.iso> [--dry-run]
"""
import argparse
import io
import json
import os
import shutil
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import dump_font as D                                   # noqa: E402
import tcslib                                           # noqa: E402
import patch_zh104_relocate as R                        # noqa: E402  (复用 face_tables)

CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
FACE_ORDER = ['large', 'default', 'huge']


def load(iso):
    w = D.load_font(iso)
    ad = w['atlas']
    W, H = ad['w'], ad['h']
    g = np.frombuffer(D.atlas_gray(ad, view='engine'), dtype=np.uint8).reshape(H, W)
    tables, _end = R.face_tables(w['ft_blob'])
    return dict(w=w, ad=ad, W=W, H=H, ink=g < 128, tables=tables,
                off={nm: off for nm, fld, off, nrec in tables},
                nrec={nm: nrec for nm, fld, off, nrec in tables})


def status(M):
    """每个对偶槽位的状态 + 每条记录矩形。"""
    cs = json.load(io.open(CHARSET, encoding='utf-8'))
    used = {}
    for ch, (b1, b2) in cs['pair_of'].items():
        if tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI:
            used[tcslib.pair_slot(b1, b2)] = ch
    # large 面的记录矩形 (各 face 一致; 后面逐 face 核对)
    rec = {}
    off = M['off']['large']
    for idx in range(M['nrec']['large']):
        b0, b1, u0, v0, u1, v1 = struct.unpack_from('<BB4H', M['w']['ft_blob'], off + idx * 10)
        if u1 > u0 and v1 > v0:
            rec[idx + 0x20] = (u0, v0, u1, v1)
    st = {}
    for slot in range(1504):
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        if not (0 <= x and x + 16 <= M['W'] and 0 <= y and y + 16 <= M['H']):
            st[slot] = 'unaddressable'; continue
        cell = M['ink'][y:y + 16, x:x + 16]
        if slot in used:
            st[slot] = 'used'
        elif not cell.any():
            covered = [c for c, (u0, v0, u1, v1) in rec.items()
                       if x < u1 and x + 16 > u0 and y < v1 and y + 16 > v0]
            st[slot] = ('free_ft', covered) if covered else ('free_blank', [])
        else:
            st[slot] = 'inked'
    return used, rec, st


def find_target(M, w_, h_):
    """找一块 w_ x h_ 的空白目标: 无墨 + 不被任何对偶槽位覆盖 + 不被任何记录覆盖。"""
    used_mask = np.zeros((M['H'], M['W']), dtype=bool)
    cs = json.load(io.open(CHARSET, encoding='utf-8'))
    for ch, (b1, b2) in cs['pair_of'].items():
        if tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI:
            x, y = tcslib.atlas_cell_xy_engine_view(tcslib.pair_slot(b1, b2))
            used_mask[y:y + 16, x:x + 16] = True
    rec_mask = np.zeros((M['H'], M['W']), dtype=bool)
    off = M['off']['large']
    for idx in range(M['nrec']['large']):
        _b0, _b1, u0, v0, u1, v1 = struct.unpack_from('<BB4H', M['w']['ft_blob'], off + idx * 10)
        if u1 > u0 and v1 > v0:
            rec_mask[v0:v1, u0:u1] = True
    # round59 硬化: 目标矩形右缘**不许超过 992** —— 对偶网格只用 x<=976(col=slot%62<=61),
    # 而 x+w_>992 会压到贴图右缘(x+16=1024=宽度) ⇒ 引擎取样取不到, 实机渲染成乱码
    # (round54 搬字就是这么把「个」0xEE 停到 x=1008 的; 见 docs/REPORT_edge_fix_zh109.md)
    for x in range(min(M['W'] - w_, 992 - w_), -1, -1):   # 从 x=992 左缘往左找
        for y in range(0, M['H'] - h_ + 1):
            if M['ink'][y:y + h_, x:x + w_].any():
                continue
            if used_mask[y:y + h_, x:x + w_].any():
                continue
            if rec_mask[y:y + h_, x:x + w_].any():
                continue
            return (x, y, x + w_, y + h_)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    M = load(a.src)
    used, rec, st = status(M)
    blocked = {s: v[1] for s, v in st.items() if v[0] == 'free_ft'}
    n_blank = sum(1 for v in st.values() if v[0] == 'free_blank')
    print('[量] 对偶槽位 1504 = 在用 %d + 可用(空白且不被记录压) %d + **空白但被记录压 %d** + 其它'
          % (len(used), n_blank, len(blocked)))
    targets = sorted({c for cs_ in blocked.values() for c in cs_})
    print('[量] 压住它们的记录 %d 条: %s' % (len(targets), ' '.join('0x%02X' % c for c in targets)))
    if not targets:
        print('[done] 没有"被记录压住的可用格" (幂等)')
        return 0
    # 每条记录的目标矩形 (保尺寸, 都放在回绕列空白区; 目标之间可以重叠 —— 都是空白)
    plan = {}
    for c in targets:
        u0, v0, u1, v1 = rec[c]
        t = find_target(M, u1 - u0, v1 - v0)
        assert t, '0x%02X 找不到合适的空白目标' % c
        plan[c] = t
        print('   0x%02X 旧(%4d,%3d,%4d,%4d) → 新(%4d,%3d,%4d,%4d)  %dx%d'
              % (c, u0, v0, u1, v1, *t, u1 - u0, v1 - v0))
    if a.dry_run or not a.dst:
        print('[dry ] 未写盘')
        return 0

    # ---- 改记录表 ----
    ft = bytearray(M['w']['ft_blob'])
    uv_span, n_upd = [], 0
    for c, t in plan.items():
        idx = c - 0x20
        for nm in FACE_ORDER:
            if nm not in M['off'] or idx >= M['nrec'][nm]:
                continue
            o = M['off'][nm] + idx * 10
            b0, b1, u0, v0, u1, v1 = struct.unpack_from('<BB4H', ft, o)
            if (u0, v0, u1, v1) != tuple(rec[c]):
                continue                     # 该 face 的矩形不同 ⇒ 不动它 (逐 face 核对)
            struct.pack_into('<BB4H', ft, o, b0, b1, *t)
            uv_span.append((o + 2, o + 10))
            assert ft[o] == M['w']['ft_blob'][o] and ft[o + 1] == M['w']['ft_blob'][o + 1], \
                'pad/advance 被改'
            n_upd += 1
    chg = [i for i in range(len(ft)) if ft[i] != M['w']['ft_blob'][i]]
    assert chg, '一个字节都没改?'
    assert all(any(lo <= i < hi for lo, hi in uv_span) for i in chg), '改动落在 pad/advance 区'
    print('[写] 改写 %d 条记录 (3 face 合计), 共 %d 字节; pad/advance 零改动 ✓' % (len(plan), len(chg)))

    ft_slot = M['w']['ft_slot']
    subs = tcslib.lzo_subs(ft_slot)
    assert len(subs) == 1, 'FONT.RES 槽不是单帧'
    olen = subs[0][1]
    tail = ft_slot[8 + olen:]
    assert all(b == 0 for b in tail), 'FONT.RES 槽尾部不是零填充'
    new_frame = tcslib.lzo_pack([(bytes(ft), len(ft))])
    new_slot = new_frame + tail
    assert len(new_slot) <= len(ft_slot), '重压超槽: %d > %d' % (len(new_slot), len(ft_slot))
    new_slot = new_slot + b'\x00' * (len(ft_slot) - len(new_slot))
    assert b''.join(s[0] for s in tcslib.lzo_subs(new_slot)) == bytes(ft), '重压回环失败'
    print('[写] FONT.RES 重压 %d → %d B (槽 %d) 回环一致 ✓' % (olen, len(new_frame), len(ft_slot)))

    if os.path.abspath(a.src) != os.path.abspath(a.dst):
        shutil.copyfile(a.src, a.dst)
    ft_e = M['w']['ft_e']
    with open(a.dst, 'r+b') as f:
        f.seek(ft_e['iso_off'])
        f.write(new_slot)
    assert os.path.getsize(a.src) == os.path.getsize(a.dst), 'ISO 尺寸变了'

    # ---- 回读自检 ----
    M2 = load(a.dst)
    assert np.array_equal(M2['ink'], M['ink']), '回读: 图集像素被改动了 (本补丁不该动像素)'
    _u2, _r2, st2 = status(M2)
    blocked2 = {s: v[1] for s, v in st2.items() if v[0] == 'free_ft'}
    blank2 = sum(1 for v in st2.values() if v[0] == 'free_blank')
    for c, t in plan.items():
        u0, v0, u1, v1 = rec[c]
        assert M2['ink'][v0:v1, u0:u1].sum() == 0, '0x%02X 旧矩形出现墨?' % c
    print('[验] 回读: 图集像素**零改动** ✓ ; 可用格 %d → **%d** ; 空白但被记录压 %d → **%d** %s'
          % (n_blank, blank2, len(blocked), len(blocked2), '✓' if not blocked2 else '✗'))
    return 0 if not blocked2 else 3


if __name__ == '__main__':
    sys.exit(main())
