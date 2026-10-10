# -*- coding: utf-8 -*-
r"""patch_zh12px.py — 关卡名 12px 兼容 (换码位方案)

## 目标 (用户要求)
  "做一个符号和大写字母、数字的 12px 字库, 然后只让这部分进入 12px, 不污染其它地方"
  "12px 用 16px 居中, 不再进行单独处理"
  ⇒ **只有关卡名**用 12px, 其它文本完全不变

## 关键事实 (前 5 轮实证)
  1. 引擎采样 **u = 记录 u0 − 288** (10 组二元消失实验 + 画点实验 + 12px 概念验证)
  2. 关卡名 = ELF 静态串 `GR-` (VA 0x57ED20) + `<MapName>` 首词
     `<MapName>M01 Caves</MapName>` 在 **MENU.IMG 条目 #170 子流@0** (LZO, 裸搜找不到)
  3. 关卡名走 **`default` 字体面**; 文件列表走 `large`; 日期/目标/提示条也走 `default`
     ⇒ 直接改 `default` 的记录会污染 ⇒ **必须换码位**
  4. 字库表 **v=480..495 完全空白** (实测墨量 0) ⇒ 12px 字形落点

## 方案
  · 14 个占位码位 0x84..0x91 → '0'-'9','G','R','M','-'
    (均在字表/lead/文本中出现 0 次, 且 < 0xA1 不会触发 DBCS 解析)
  · 12px 字形 (fusion12 BDF, 5×8) **居中放进 16×16 格** → 画到字库表 v=480 起的空带
  · FT 三个面的 idx 100..113 记录 → 指向这些字形
  · ELF `GR-` → 0x8E 0x8F 0x91
  · MENU.IMG #170 子流@0 的 `<MapName>M01 Caves` → 占位码位
  ⇒ 关卡名 6 个字符全部 12px, 其它文本零影响

## 用法
  python patch_zh12px.py <src_iso> <dst_iso>

  ⚠ **基底必须是布局正常的盘**（推荐 `work/builds/GR_ZH256`）:
  ```
  make_build.py GR_ZHxxx --from work/builds/GR_ZH256 --patch tools/iso_build/patch_zh12px.py
  ```

## ⚠ 基底选择 (2026-10-06 实测教训)
  **`GR_ZH253` 不能作为基底** —— 它由实验性补丁 `work/_dis/atr_expand_v3.py` 构建
  (ATR 条目**扩展**), 导致 GR.IMG **199 个条目搬迁**, 最高位置超原盘 6.3 MB
  (`0x5C6ACA80` vs 原盘 `0x5C0AB658`)。

  **后果**: 游戏对 GR.IMG 某些条目有**硬编码偏移访问** ⇒ 搬迁后读档失败 ⇒
  **在 "Press START" 后的"正在读取数据"屏卡死** (BGM 在一小节内循环)。

  实测矩阵 (同一张用户存档卡):
  | 盘 | 搬迁条目 | 读档 |
  |---|---|---|
  | `GR_ZH253` | 199 (max 0x5C6ACA80) | **卡死** |
  | `GR_ZH353` (= ZH253 + 本补丁) | 199 | **卡死** |
  | `GR_ZH256` | 14 (max 0x5C0AB658) | 正常 |
  | **`GR_ZH360`** (= ZH256 + 本补丁) | **14 (与原盘一致)** | **正常** ✓ |

  `GR_ZH256` 用**最终方案** `work/_dis/atr_dot_patch2.py` (ATR 人名间隔号 `·`, **原位等长**),
  布局与原盘一致 ⇒ 安全。
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
sys.path.insert(0, os.path.join(REPO, 'work', '_dis'))
import numpy as np                                       # noqa: E402
import x12_lib as L                                      # noqa: E402
from lz77_decode import lzo1x_decompress                 # noqa: E402
from lzo1x_c import compress as lzo_compress             # noqa: E402
from x12_bdf import parse_bdf                            # noqa: E402

ELF_LBA, SEC_OFF = 295, 0x80
MENU_LBA = 776286
MENU_SIZE = 58300882
GR_LBA = 19175
GR_SIZE = 1550563328
TAB_OFF, TAB_STEP = 0x830, 48
E_STORED, E_REAL, E_OFF = 6, 7, 8
OFF_FT, FT_SLOT = 0xB9120, 4421
OFF_PAK_REC, PIX_OFF = 0x58431, 0x44C

# 14 个占位码位 → 字符
CODES = {}
for i in range(10):
    CODES[str(i)] = 0x84 + i
CODES['G'] = 0x8E
CODES['R'] = 0x8F
CODES['M'] = 0x90
CODES['-'] = 0x91
ORDER = '0123456789GRM-'

BDF = os.path.join(REPO, 'third_party/fonts/fusion12',
                   'fusion-pixel-12px-monospaced-latin.bdf')

# 12px 字形带: v=480..495 (实测全空), 每字 14 texel 步进
BAND_V = 480
STEP = 14
CELL_W, CELL_H = 8, 16          # 引擎采样窗口 (= 记录矩形)
GLYPH_OFF_X = (CELL_W - 5) // 2  # 5 宽字形水平居中 → 1
GLYPH_OFF_Y = (CELL_H - 8) // 2  # 8 高字形垂直居中 → 4  (用户要求 "12px 用 16px 居中")

MENU_ENTRY_170 = 170
GR_ENTRY_661 = 661
OLD_MAPNAME = b'<MapName>M01 Caves</MapName>'
ELF_GR_VA = 0x57ED20

# ★ 字符宽度表 (ELF off 0x4891C4, VA 0x589144)
#   0x00..0x83 有值 (7/8), 0x84..0x9B 为 0
#   表值 0 的码位会被当成**全宽(24)** ⇒ 关卡名文本宽度算成 96 而非 48
#   ⇒ 居中定位左移 24 px (实测 F12 554 → 530)
#   Plan C 已把 0x80..0x83 设为 8, 本补丁同样把 0x84..0x91 设为 8
WIDTH_TAB_OFF = 0x4891C4
WIDTH_VALUE = 8

# ★ 日期/时间 16px 占位 (消除 '0','1' 借到 12px 后的污染)
#   MENU.IMG #25 / GR.IMG #902 是日期/时间的字符串资源表 (实测: 改 'Apr'→'Xpr'
#   后日期区差异 19 px + 时间区 13 px ⇒ 确认来源)
PH0, PH1 = 0x5E, 0x60                  # '^' 代替 '0', '`' 代替 '1'
DATE_ENTRIES = ((MENU_LBA, MENU_SIZE, 25, 'MENU.IMG'),
                (GR_LBA, GR_SIZE, 902, 'GR.IMG'))
DATES = [(b'Apr 16, 2008',
          b'Apr ' + bytes([PH1]) + b'6, 2' + bytes([PH0, PH0]) + b'8'),
         (b'05:45', bytes([PH0]) + b'5:45')]


def elf_off(va):
    return SEC_OFF + (va - 0x00100000)


def lz_records(blob):
    parts, q = [], 0
    while q + 8 <= len(blob):
        L2, S = struct.unpack_from('<II', blob, q)
        if L2 == 0 or q + 8 + L2 > len(blob) or S > 16_000_000:
            break
        dd, err, _ = lzo1x_decompress(blob[q + 8:q + 8 + L2], out_size=S)
        if err:
            break
        parts.append((q, L2, S, bytes(dd)))
        q += 8 + L2
    return parts, q


def main(src, dst):
    d = bytearray(open(src, 'rb').read())
    MENU = MENU_LBA * 2048
    A, _ = L.read_atlas(src)
    A2 = A.copy()

    # ---------------- 1. 12px 字形 ----------------
    g = parse_bdf(BDF, want=set(ord(c) for c in ORDER))
    print('[bdf ] 取到 %d / %d 个字形' % (len(g), len(ORDER)))
    assert len(g) == len(ORDER)
    assign = {}
    for k, ch in enumerate(ORDER):
        u = k * STEP
        code = CODES[ch]
        # 目标字形窗口 (引擎采样位置) = (u, BAND_V) .. (u+8, BAND_V+16)
        # 引擎采样 u = 记录u0 − 288 ⇒ 记录 u0 = u + 288
        ru0, rv0 = u + 288, BAND_V
        # 清整格为背景, 再画 12px 字形 (居中)
        A2[BAND_V:BAND_V + CELL_H, u:u + CELL_W] = 1
        bits = g[ord(ch)]['bits']
        h, w = bits.shape
        for yy in range(h):
            for xx in range(w):
                if bits[yy, xx]:
                    A2[BAND_V + GLYPH_OFF_Y + yy, u + GLYPH_OFF_X + xx] = 0
        assign[ch] = dict(code=code, idx=code - 0x20, u=u,
                          rec=(0, 8, ru0, rv0, ru0 + CELL_W, rv0 + CELL_H))
        print('  %r → code 0x%02X idx %-3d  字形窗 (%d,%d)  记录 %s'
              % (ch, code, code - 0x20, u, BAND_V, assign[ch]['rec']))

    # ---------------- 2. FT 三个面 ----------------
    base = MENU
    e = struct.unpack_from('<12I', d, base + TAB_OFF + TAB_STEP * 4)
    fstored, foff = e[E_STORED], e[E_OFF]
    assert foff == OFF_FT and fstored == FT_SLOT, 'FONT.RES 位置异常 0x%X/%d' % (foff, fstored)
    fblob = bytes(d[base + foff:base + foff + fstored])
    frecs, consumed = lz_records(fblob)
    ft = bytearray(frecs[0][3])
    meta = L.parse_ft(bytes(ft))
    print('[ft  ] FT %d B, faces: %s' % (len(ft), [(f['name'], len(f['recs'])) for f in meta['faces']]))

    # 找每个面的记录基址 (按解析顺序重算)
    p = 0
    l0 = struct.unpack_from('<I', ft, p)[0]
    p += 4 + l0
    nf = struct.unpack_from('<I', ft, p)[0]
    p += 4
    face_off = []
    for _ in range(nf):
        l = struct.unpack_from('<I', ft, p)[0]
        p += 4
        p += l
        fld = list(struct.unpack_from('<14I', ft, p))
        p += 56
        nr = fld[4] * fld[5]
        face_off.append((p, nr))
        p += nr * 10

    nch = 0
    for ch in ORDER:
        v = assign[ch]
        packed = struct.pack('<BB4H', *v['rec'])
        for (fo, nr) in face_off:
            if v['idx'] < nr:
                o = fo + v['idx'] * 10
                ft[o:o + 10] = packed
                nch += 1
    print('      FT 记录改写 %d 处 (3 面 × 14 码位)' % nch)

    # ---------------- 2b. 16px 占位码位 + M/0/1 借到 12px ----------------
    #   关卡名 'GR-M01' 的 'M','0','1' 码位由**代码生成**, 无法换码位
    #   ⇒ 把 default 面 idx 45(M)/16(0)/17(1) 的 UV 借到 12px 字形
    #   ⇒ 但 default 面被**日期/时间共用** ⇒ 新增**罕见 ASCII 占位码位**
    #      0x5E('^') 代替 '0', 0x60('`') 代替 '1' (FT 记录 = 原 16px 字形)
    #      并把日期/时间字符串里的 '0','1' 换成占位码位
    #   ★ 占位码位必须 < 0x80: 实测码位 >= 0x80 在宽度计算里被当成**全宽**,
    #     会让日期文本左移 ~7 px (GR_ZH351 实测 427 px 差异; 改用 ASCII 后 0 px)
    do_ = face_off[1][0]                 # 面顺序: large, default, huge
    for ph_idx, src_idx in ((PH0 - 0x20, 16), (PH1 - 0x20, 17)):
        ft[do_ + ph_idx * 10:do_ + ph_idx * 10 + 10] = \
            ft[do_ + src_idx * 10:do_ + src_idx * 10 + 10]
    for dst_idx, src_idx in ((45, 112), (16, 100), (17, 101)):
        f0, f1, u0, v0, u1, v1 = struct.unpack(
            '<BB4H', ft[do_ + src_idx * 10:do_ + src_idx * 10 + 10])
        keep1 = ft[do_ + dst_idx * 10 + 1]      # 保留原推进, 免字距变化
        struct.pack_into('<BB4H', ft, do_ + dst_idx * 10, f0, keep1, u0, v0, u1, v1)
    print('[12px] default 面: 占位码位 0x%02X/0x%02X ← idx 16/17 原 16px 字形;'
          ' idx 45(M)/16(0)/17(1) → 12px 字形' % (PH0, PH1))
    assert len(ft) == len(frecs[0][3])
    cf = lzo_compress(bytes(ft))
    tail = fblob[8 + frecs[0][1]:consumed]
    new_fblob = struct.pack('<II', len(cf), len(ft)) + cf + tail
    assert len(new_fblob) <= fstored - 8, 'FONT.RES 重压 %d 超槽 %d' % (len(new_fblob), fstored)
    print('      FONT.RES 重压 %d B (槽 %d, 余 %d)' % (len(new_fblob), fstored, fstored - len(new_fblob)))
    d[base + foff:base + foff + len(new_fblob)] = new_fblob

    # ---------------- 3. ELF `GR-` ----------------
    eo = ELF_LBA * 2048 + elf_off(ELF_GR_VA)
    old = bytes(d[eo:eo + 3])
    assert old == b'GR-', 'ELF GR- 位置异常: %r' % old
    new = bytes([CODES['G'], CODES['R'], CODES['-']])
    d[eo:eo + 3] = new
    print('[elf ] VA 0x%X  %r → %s' % (ELF_GR_VA, old, ' '.join('%02X' % b for b in new)))

    # ---------------- 3b. 字符宽度表 (修复居中定位) ----------------
    to = ELF_LBA * 2048 + WIDTH_TAB_OFF
    for ch in ORDER:
        c = CODES[ch]
        cur = d[to + c]
        d[to + c] = WIDTH_VALUE
    print('[tab ] ELF off 0x%X 码位 %s → 宽度 %d (修 F12 左移)'
          % (WIDTH_TAB_OFF, ' '.join('%02X' % CODES[ch] for ch in ORDER), WIDTH_VALUE))

    # ---------------- 4. <MapName> (MENU.IMG #170 与 GR.IMG #661 两份副本) ----------------
    #   ★ 实测: GR.IMG #661 与 MENU.IMG #170 内容完全相同 (stored=23182, real=90910,
    #     子流@0 plen=4443)。只改 MENU 副本时 drawlog 仍显示 'M01'
    #     ⇒ 游戏从 GR.IMG 读关卡数据 ⇒ **两份都要改**
    newname = (b'<MapName>' + bytes([CODES['M'], CODES['0'], CODES['1']]) + b' Caves</MapName>')

    def patch_mapname(lba, total, entry_idx, tag):
        b0 = lba * 2048
        e0 = struct.unpack_from('<12I', d, b0 + TAB_OFF + TAB_STEP * entry_idx)
        st0, off0, real0 = e0[E_STORED], e0[E_OFF], e0[E_REAL]
        raw0 = bytes(d[b0 + off0:b0 + off0 + st0])
        recs0, cons0 = lz_records(raw0)
        hit0 = None
        for (q0, plen0, osz0, dd0) in recs0:
            if OLD_MAPNAME in dd0:
                hit0 = (q0, plen0, osz0, dd0)
                break
        assert hit0, '%s #%d 未找到 <MapName>' % (tag, entry_idx)
        q0, plen0, osz0, dd0 = hit0
        i0 = dd0.index(OLD_MAPNAME)
        assert len(newname) == len(OLD_MAPNAME)
        dd2 = dd0[:i0] + newname + dd0[i0 + len(OLD_MAPNAME):]
        assert len(dd2) == len(dd0) == osz0
        print('[mis ] %s #%d 子流@%d: %r → %r'
              % (tag, entry_idx, q0, OLD_MAPNAME, newname))
        c2 = lzo_compress(dd2)
        parts0 = []
        for (qq, pplen, oosz, ddd) in recs0:
            payload = c2 if qq == q0 else raw0[qq + 8:qq + 8 + pplen]
            parts0.append(struct.pack('<II', len(payload), oosz) + payload)
        newraw = b''.join(parts0)
        print('      子流重压 %d → %d; 条目 %d → %d (槽 %d)'
              % (plen0, len(c2), st0, len(newraw), st0))
        if len(newraw) > st0:
            n_ent = struct.unpack_from('<I', d, b0 + 8)[0]
            end = 0
            for i2 in range(n_ent):
                e2 = struct.unpack_from('<12I', d, b0 + TAB_OFF + TAB_STEP * i2)
                if e2[E_OFF] and e2[E_STORED] and e2[E_OFF] + e2[E_STORED] <= total:
                    end = max(end, e2[E_OFF] + e2[E_STORED])
            no = ((end + 2047) // 2048) * 2048
            assert no + len(newraw) <= total, '%s 空间不足' % tag
            assert all(b == 0 for b in d[b0 + no:b0 + no + len(newraw)]), '目标区非零'
            d[b0 + no:b0 + no + len(newraw)] = newraw
            to0 = b0 + TAB_OFF + TAB_STEP * entry_idx
            struct.pack_into('<I', d, to0 + 32, no)
            struct.pack_into('<I', d, to0 + 24, len(newraw))
            print('      ⇒ 搬到末尾: off 0x%X → 0x%X, stored %d → %d (real 不变 %d)'
                  % (off0, no, st0, len(newraw), real0))
        else:
            d[b0 + off0:b0 + off0 + len(newraw)] = newraw

    patch_mapname(MENU_LBA, MENU_SIZE, MENU_ENTRY_170, 'MENU.IMG')
    # ⚠️ GR.IMG #661 是同一 XML 的**副本**，但实测:
    #    · 改它**不能**让关卡名的 'M01' 换码位 (drawlog 仍 'M01')
    #    · 且会让**底部提示栏**产生 763 px 差异 (K320 vs 基线 = 0, R330 = 763)
    #   ⇒ 默认**不启用**; 需要时用环境变量 GR_MAPNAME=1 打开
    if os.environ.get('GR_MAPNAME') == '1':
        patch_mapname(GR_LBA, GR_SIZE, GR_ENTRY_661, 'GR.IMG')
    else:
        print('[mis ] GR.IMG #661 副本未改 (实测无效且有副作用, 见注释)')

    # ---------------- 4b. 日期/时间 → 16px 占位码位 ----------------
    def patch_dates(lba, total, ent, tag):
        b0 = lba * 2048
        e0 = struct.unpack_from('<12I', d, b0 + TAB_OFF + TAB_STEP * ent)
        st0, off0, real0 = e0[E_STORED], e0[E_OFF], e0[E_REAL]
        raw0 = bytes(d[b0 + off0:b0 + off0 + st0])
        recs0, _ = lz_records(raw0)
        parts0, n = [], 0
        for (q0, plen0, osz0, dd0) in recs0:
            for a, bb in DATES:
                k = dd0.count(a)
                if k:
                    dd0 = dd0.replace(a, bb)
                    n += k
            c = lzo_compress(dd0)
            parts0.append(struct.pack('<II', len(c), osz0) + c)
        if not n:
            print('[date] %s #%d 未找到日期串' % (tag, ent))
            return
        newraw = b''.join(parts0)
        print('[date] %s #%d: 替换 %d 处, 条目 %d → %d (槽 %d)'
              % (tag, ent, n, st0, len(newraw), st0))
        if len(newraw) > st0:
            n_ent = struct.unpack_from('<I', d, b0 + 8)[0]
            end = 0
            for i2 in range(n_ent):
                e2 = struct.unpack_from('<12I', d, b0 + TAB_OFF + TAB_STEP * i2)
                if e2[E_OFF] and e2[E_STORED] and e2[E_OFF] + e2[E_STORED] <= total:
                    end = max(end, e2[E_OFF] + e2[E_STORED])
            no = ((end + 2047) // 2048) * 2048
            assert no + len(newraw) <= total, '%s 空间不足' % tag
            assert all(b == 0 for b in d[b0 + no:b0 + no + len(newraw)]), '目标区非零'
            d[b0 + no:b0 + no + len(newraw)] = newraw
            to0 = b0 + TAB_OFF + TAB_STEP * ent
            struct.pack_into('<I', d, to0 + 32, no)
            struct.pack_into('<I', d, to0 + 24, len(newraw))
            print('       ⇒ 搬到末尾 0x%X (real 不变 %d)' % (no, real0))
        else:
            d[b0 + off0:b0 + off0 + len(newraw)] = newraw

    for (lba, total, ent, tag) in DATE_ENTRIES:
        patch_dates(lba, total, ent, tag)

    # ---------------- 5. 字库表 ----------------
    px = L.pack_atlas(A2)
    d[base + OFF_PAK_REC + PIX_OFF:base + OFF_PAK_REC + PIX_OFF + len(px)] = px
    print('[tex ] 12px 字形带 v=%d..%d, u=0..%d' % (BAND_V, BAND_V + CELL_H - 1, (len(ORDER) - 1) * STEP + CELL_W - 1))

    open(dst, 'wb').write(bytes(d))
    print('[iso ] %s' % dst)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1], sys.argv[2])
