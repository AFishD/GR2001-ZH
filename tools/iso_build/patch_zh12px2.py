# -*- coding: utf-8 -*-
r"""patch_zh12px2.py — 关卡名 12px 兼容 (换码位方案 v2 · 修正版)

## 相对 v1 (patch_zh12px.py) 的修正 (第 10 轮, 用户报障)
  1. **不再借用 default 面的 'M','0','1' 记录** —— 那会让菜单/标题/任务目标里的
     数字与 M 全部变成 12px (用户报障 ①"菜单标题错位" ②"任务目标的 1 变 12px")
  2. **不再改日期/时间字符串** (v1 的占位方案 0x5E/0x60 随之删除)
  3. **不再改 MENU.IMG #170 的 XML `<MapName>`** (实测不是显示来源)
  4. **真正的来源 = EN_STRINGS.RES 字符串表** (MENU.IMG #25 / GR.IMG #902):
     右上角关卡名 = 「该任务 MapName 条目截断到第一个空格」;
     战役再在前面拼 ELF 静态串 "GR-"。
     ⇒ 把 MapName 条目的首个 token 换成**占位码位**即可, 只影响关卡名 ✓

## 占位码位 (25 个, 全部 < 0xA1 且 ≤ 0x9B)
  0x7F..0x91 + 0x93..0x98  (跳过 0x92: 基盘里它有独立字形)
  对应字形: 0-9 M D P G R T A C a c r i n g -
  · 0x7F..0xAE 是字集 (单字节码 0xAF..0xFE / DBCS lead 0xA1..0xB0) 之外的空白区
  · 宽度表 (ELF 0x4891C4) 覆盖 0x00..0x9B ⇒ 这些码位宽度设为 8 (半宽)

## 用法
  make_build.py GR_ZHxxx --from work/builds/GR_ZH256 --patch tools/iso_build/patch_zh12px2.py
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
import iso_tools as T                                    # noqa: E402
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
ELF_GR_VA = 0x57ED20
WIDTH_TAB_OFF = 0x4891C4
WIDTH_VALUE = 8
RES_ENTRIES = ((MENU_LBA, MENU_SIZE, 25, 'MENU.IMG'),
               (GR_LBA, GR_SIZE, 902, 'GR.IMG'))

# 25 个占位码位 (0x7F..0x9B 去掉 0x92)
ORDER = '0123456789' 'MDPGRTAC' 'acring' '-'
_POOL = [c for c in range(0x7F, 0x9C) if c != 0x92]
assert len(_POOL) >= len(ORDER), (len(_POOL), len(ORDER))
CODES = {ch: _POOL[k] for k, ch in enumerate(ORDER)}
assert len(set(CODES.values())) == len(ORDER) == 25, (len(CODES), len(ORDER))

BDF = os.path.join(REPO, 'third_party/fonts/fusion12',
                   'fusion-pixel-12px-monospaced-latin.bdf')
BAND_V = 480
STEP = 14
CELL_W, CELL_H = 8, 16
GLYPH_OFF_X = (CELL_W - 5) // 2
GLYPH_OFF_Y = (CELL_H - 8) // 2


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


def parse_res(blob):
    """EN_STRINGS.RES: {u32 组数} + 每组 {u32 条目数} + 条目 {u32 len}{data}{u16 attr}"""
    ng = struct.unpack_from('<I', blob, 0)[0]
    p, out = 4, []
    for g in range(ng):
        cnt = struct.unpack_from('<I', blob, p)[0]
        p += 4
        for i in range(cnt):
            ln = struct.unpack_from('<I', blob, p)[0]
            out.append((g, i, p, p + 4, ln, blob[p + 4:p + 4 + ln]))
            p += 4 + ln + 2
    return out


def ph_bytes(s):
    if isinstance(s, (bytes, bytearray)):
        s = bytes(s).decode('latin-1')
    return bytes(CODES[c] for c in s)


def is_ascii_tok(b):
    return b and all(0x30 <= c <= 0x39 or 0x41 <= c <= 0x5A or 0x61 <= c <= 0x7A
                     for c in b)


NAME_RE = None


CODE_RE = None


def en_token_of(tok):
    """把汉化表里的 MapName token 映射为英文 token (仅接受任务代号形态)"""
    global CODE_RE
    import re
    if CODE_RE is None:
        CODE_RE = re.compile(rb'^(M\d\d|D\d\d|DP\d\d|MP\d\d|T\d\d|TAC\d\d)$')
    if CODE_RE.match(tok):
        return tok.decode('latin-1')
    if tok[:3] == b'\xba\xa4\xf0' and len(tok) >= 4 and 0x30 <= tok[3] <= 0x39:
        return 'TAC0' + chr(tok[3])
    if tok == b'Training':
        return 'Training'
    return None


MISSION_TOKENS = (['M%02d' % i for i in range(1, 16)]
                  + ['D%02d' % i for i in range(1, 9)]
                  + ['DP%02d' % i for i in range(1, 6)]
                  + ['MP%02d' % i for i in range(1, 6)]
                  + ['T%02d' % i for i in range(1, 8)]
                  + ['TAC%02d' % i for i in range(1, 6)])


def fix_mapnames(blob, diag=False):
    """把语言表里每个任务 **Name** 条目的首个 token 换成占位码位

    ⚠ 第 11 轮教训 (用户报「所有战术演习任务进入游戏后卡死」):
      · 关卡名 token 取自 **Name** 条目 ⇒ 只改 Name, **MapName 一律不动**
        (MapName 可能被载入流程使用; 且它对显示无影响, 实测过)
      · 替换必须**保持字符串结构**: " - " 分隔符、后半段描述文字**原样保留**,
        只把 token 本身的字节数换成等长的占位码位
      · 战术演习 token = "战术N" (ba a4 f0 + 数字, 4 B) → 占位 "TAC" + 数字占位 (4 B)
        ⇒ 显示 "TAC1".."TAC5" (等长, 不能写 "TAC01": 那是 5 B, 会破坏结构)
    """
    n = 0
    # 战役 Name: "M01 - 铁龙" → token 换占位, " - 铁龙" 原样
    for tk in MISSION_TOKENS:
        pat = tk.encode() + b' - '
        p = 0
        while True:
            k = blob.find(pat, p)
            if k < 0:
                break
            p = k + 1
            if k < 4:
                continue
            ln = struct.unpack_from('<I', blob, k - 4)[0]
            if ln < len(pat) or k + ln > len(blob):
                continue
            blob[k:k + len(tk)] = ph_bytes(tk)
            n += 1
            if diag:
                print('      Name %s - @0x%-6X len %d' % (tk, k, ln))
    # 训练关 Name: "训练N - 越野训练" → token "训练N" (c2 b3 + 数字, 3 B) → 占位 "T0N"
    for d in b'1234567':
        pat = b'\xc2\xb3' + bytes([d]) + b' - '
        p = 0
        while True:
            k = blob.find(pat, p)
            if k < 0:
                break
            p = k + 1
            if k < 4:
                continue
            ln = struct.unpack_from('<I', blob, k - 4)[0]
            if ln < len(pat) or k + ln > len(blob):
                continue
            blob[k:k + 3] = ph_bytes('T0' + chr(d))
            n += 1
            if diag:
                print('      训练%s - @0x%-6X len %d → T0%s' % (chr(d), k, ln, chr(d)))
    # 战术演习 Name: "战术N - 射击" → token "战术N" (4 B) → 占位 "TAC"+数字 (4 B)
    for d in b'12345':
        pat = b'\xba\xa4\xf0' + bytes([d]) + b' - '
        p = 0
        while True:
            k = blob.find(pat, p)
            if k < 0:
                break
            p = k + 1
            if k < 4:
                continue
            ln = struct.unpack_from('<I', blob, k - 4)[0]
            if ln < len(pat) or k + ln > len(blob):
                continue
            blob[k:k + 4] = ph_bytes('TAC' + chr(d))
            n += 1
            if diag:
                print('      战术%s - @0x%-6X len %d → TAC%s' % (chr(d), k, ln, chr(d)))
    return n


def main(src, dst, diag=False):
    d = bytearray(open(src, 'rb').read())
    MENU = MENU_LBA * 2048
    A, _ = L.read_atlas(src)
    A2 = A.copy()

    # ---------------- 1. 12px 字形带 ----------------
    g = parse_bdf(BDF, want=set(ord(c) for c in ORDER))
    assert len(g) == len(ORDER), 'BDF 缺字形 %s' % (set(ORDER) - set(chr(k) for k in g))
    assign = {}
    for k, ch in enumerate(ORDER):
        u = k * STEP
        code = CODES[ch]
        ru0, rv0 = u + 288, BAND_V
        A2[BAND_V:BAND_V + CELL_H, u:u + CELL_W] = 1
        bits = g[ord(ch)]['bits']
        h, w = bits.shape
        for yy in range(h):
            for xx in range(w):
                if bits[yy, xx]:
                    A2[BAND_V + GLYPH_OFF_Y + yy, u + GLYPH_OFF_X + xx] = 0
        assign[ch] = dict(code=code, idx=code - 0x20, u=u,
                          rec=(0, 8, ru0, rv0, ru0 + CELL_W, rv0 + CELL_H))
    print('[bdf ] %d 字形 → 码位 %s' % (len(g), ' '.join('%02X' % CODES[c] for c in ORDER)))

    # ---------------- 1b. 16px 间隔号 '·' (码位 0x99) ----------------
    #   第 12 轮: ATR 人名补丁原来把 '·' 编成单字节 0xB7 (latin-1 回退), 而 0xB7 不是
    #   字集里的合法单字节码 (单字节码 0xAF..0xFE / DBCS lead 0xA1..0xB0) ⇒ 引擎把它当
    #   DBCS 首字节 ⇒ **其后所有字节错位** ⇒ 用户看到的「的前的运火你动卡你」乱码。
    #   ⇒ 改用合法空闲码位 0x99, 并在图集里画一个真正的 16px 中点。
    DOT_CODE = 0x99
    dot_u = len(ORDER) * STEP + 4          # 12px 字形带右侧的空白区
    A2[BAND_V:BAND_V + CELL_H, dot_u:dot_u + CELL_W] = 1
    for yy in range(3):                    # 3×3 中点, 垂直居中
        for xx in range(3):
            A2[BAND_V + 6 + yy, dot_u + 2 + xx] = 0
    dot_rec = (0, 8, dot_u + 288, BAND_V, dot_u + 288 + CELL_W, BAND_V + CELL_H)
    print('[dot ] 码位 0x99 = 16px 中点, 图集 u=%d..%d v=%d..%d'
          % (dot_u, dot_u + CELL_W - 1, BAND_V, BAND_V + CELL_H - 1))

    # ---------------- 2. FT 三个面 ----------------
    base = MENU
    e = struct.unpack_from('<12I', d, base + TAB_OFF + TAB_STEP * 4)
    fstored, foff = e[E_STORED], e[E_OFF]
    assert foff == OFF_FT and fstored == FT_SLOT, 'FONT.RES 位置异常'
    fblob = bytes(d[base + foff:base + foff + fstored])
    frecs, consumed = lz_records(fblob)
    ft = bytearray(frecs[0][3])
    meta = L.parse_ft(bytes(ft))
    p = 0
    l0 = struct.unpack_from('<I', ft, p)[0]
    p += 4 + l0
    nf = struct.unpack_from('<I', ft, p)[0]
    p += 4
    face_off = []
    for _ in range(nf):
        l = struct.unpack_from('<I', ft, p)[0]
        p += 4 + l
        fld_off = p                                   # ← 描述符起点 (14×u32)
        fld = list(struct.unpack_from('<14I', ft, p))
        p += 56
        nr = fld[4] * fld[5]
        face_off.append((p, nr, fld_off, fld))
        p += nr * 10
    styles_off = p

    # ---- 2a. ★★ 修复汉化字库 huge 面被截断 (96 → 224 记录) ★★
    #   英文原盘 huge 面 fld=[10,42,52,42,16,14] = 16×14 = 224 记录;
    #   汉化盘被改成 16×6 = 96 ⇒ 引擎渲染任何码位 ≥ 0x80 (idx ≥ 96) 时**读到面外**,
    #   面外正是 {u32 nstyles}=8 ⇒ 记录 = {f0=8, f1=0, ...} ⇒ **推进 = 0**
    #   ⇒ 文本布局死循环 = 用户报的「战术演习进入游戏后卡死」。
    #   修法: 把记录数恢复成 224, 新增的 128 条**复制 default 面同 idx 的记录**
    #   (字形正确、推进正常), 再让下面的 12px 记录写入覆盖占位码位。
    EN_HUGE_FLD45 = (16, 14)
    huge = face_off[-1]
    fixed_huge = False
    if huge[1] < EN_HUGE_FLD45[0] * EN_HUGE_FLD45[1]:
        want = EN_HUGE_FLD45[0] * EN_HUGE_FLD45[1]
        cur = huge[1]
        add = want - cur
        src_off, src_nr = face_off[1][0], face_off[1][1]     # default 面
        assert src_nr >= want, ('default 面记录不足', src_nr)
        newrecs = bytearray()
        for k in range(add):
            newrecs += ft[src_off + (cur + k) * 10:src_off + (cur + k) * 10 + 10]
        fld = list(huge[3])
        fld[4], fld[5] = EN_HUGE_FLD45
        ft[huge[2]:huge[2] + 56] = struct.pack('<14I', *fld)
        ft = ft[:styles_off] + newrecs + ft[styles_off:]
        face_off[-1] = (huge[0], want, huge[2], fld)
        fixed_huge = True
        print('[ft  ] ★ huge 面记录数 %d → %d (补齐 %d 条, 复制 default 面同 idx)'
              % (cur, want, add))
    meta = L.parse_ft(bytes(ft))
    nch = 0
    # ★ 12px 记录**只写进 default 面**:
    #   · 简报页右上角关卡名用的是 default 面 (v1 借的正是 default 面 idx 16/17/45 ⇒ 关卡名随之变 12px)
    #   · 载入界面「信息 / TAC1 - 射击」用的是 large/huge 面 ⇒ 那两面改写成对应 ASCII 记录 (16px),
    #     满足用户「这里 TAC1 应该是 16px」的要求
    DEF_FACE = 1
    for fi, (fo, nr, _dsc, _fld) in enumerate(face_off):
        if fi == DEF_FACE:
            for ch in ORDER:
                v = assign[ch]
                if v['idx'] < nr:
                    ft[fo + v['idx'] * 10:fo + v['idx'] * 10 + 10] = struct.pack('<BB4H', *v['rec'])
                    nch += 1
        else:
            for ch in ORDER:
                v = assign[ch]
                a_idx = ord(ch) - 0x20
                if a_idx < nr:
                    ft[fo + v['idx'] * 10:fo + v['idx'] * 10 + 10] = \
                        ft[fo + a_idx * 10:fo + a_idx * 10 + 10]
                    nch += 1
        if DOT_CODE - 0x20 < nr:                      # 间隔号三面都用 16px 中点
            ft[fo + (DOT_CODE - 0x20) * 10:fo + (DOT_CODE - 0x20) * 10 + 10] = \
                struct.pack('<BB4H', *dot_rec)
            nch += 1
    print('[ft  ] FT %d B, 面 %s, 改写 %d 处 (仅 default 面 12px; large/huge 用 ASCII 记录保 16px)'
          % (len(ft), [(f['name'], len(f['recs'])) for f in meta['faces']], nch))
    cf = lzo_compress(bytes(ft))
    tail = fblob[8 + frecs[0][1]:consumed]
    new_fblob = struct.pack('<II', len(cf), len(ft)) + cf + tail
    assert len(new_fblob) <= fstored - 8, 'FONT.RES 重压超槽'
    d[base + foff:base + foff + len(new_fblob)] = new_fblob
    print('      FONT.RES 重压 %d B (槽 %d, 余 %d)' % (len(new_fblob), fstored, fstored - len(new_fblob)))

    # ---------------- 3. ELF `GR-` ----------------
    eo = ELF_LBA * 2048 + elf_off(ELF_GR_VA)
    old = bytes(d[eo:eo + 3])
    assert old == b'GR-', 'ELF GR- 位置异常: %r' % old
    d[eo:eo + 3] = ph_bytes('GR-')
    print('[elf ] VA 0x%X GR- → %s' % (ELF_GR_VA, ' '.join('%02X' % b for b in ph_bytes('GR-'))))

    # ---------------- 3b. 宽度表 ----------------
    to = ELF_LBA * 2048 + WIDTH_TAB_OFF
    for ch in ORDER:
        d[to + CODES[ch]] = WIDTH_VALUE
    d[to + DOT_CODE] = WIDTH_VALUE
    print('[tab ] 宽度表码位 %s + 0x99 → %d'
          % (' '.join('%02X' % CODES[c] for c in ORDER), WIDTH_VALUE))

    # ---------------- 3c. ★ ATR 人名的非法间隔号 0xB7 → 合法码位 0x99 ----------------
    #   atr_dot_patch2.py 把 '·' 编成 0xB7 (latin-1 回退), 0xB7 不是合法单字节码
    #   ⇒ 引擎当 DBCS 首字节 ⇒ 名字后半段整体错位/乱码。这里只做 1 字节→1 字节替换,
    #   不改变任何条目尺寸/位置。
    names = T.img_names(d, GR_LBA)
    nfix = 0
    for i, nm in enumerate(names):
        if not nm.upper().endswith('.ATR'):
            continue
        e = struct.unpack_from('<12I', d, GR_LBA * 2048 + TAB_OFF + TAB_STEP * i)
        off, stored = e[E_OFF], e[E_STORED]
        if not off or not stored:
            continue
        b = GR_LBA * 2048 + off
        seg = bytes(d[b:b + stored])
        if b'\xb7' not in seg:
            continue
        d[b:b + stored] = seg.replace(b'\xb7', bytes([DOT_CODE]))
        nfix += 1
    print('[atr ] 间隔号 0xB7 → 0x%02X: 修正 %d 个 .ATR' % (DOT_CODE, nfix))

    # ---------------- 4. 语言字符串表: MapName token → 占位码位 ----------------
    for (lba, total, ent, tag) in RES_ENTRIES:
        b0 = lba * 2048
        e0 = struct.unpack_from('<12I', d, b0 + TAB_OFF + TAB_STEP * ent)
        st0, off0, real0 = e0[E_STORED], e0[E_OFF], e0[E_REAL]
        raw0 = bytes(d[b0 + off0:b0 + off0 + st0])
        recs0, _ = lz_records(raw0)
        blob = bytearray(b''.join(dd for (_q, _l, _s, dd) in recs0))
        if diag:
            n0 = fix_mapnames(blob, diag=True)
            blob = bytearray(b''.join(dd for (_q, _l, _s, dd) in recs0))
        n = fix_mapnames(blob)
        print('[res ] %s #%d: 改写 %d 个 MapName 条目' % (tag, ent, n))
        parts = []
        pos = 0
        for (q, plen, osz, dd) in recs0:
            chunk = bytes(blob[pos:pos + osz])
            assert len(chunk) == osz, (len(chunk), osz)
            c = lzo_compress(chunk)
            parts.append(struct.pack('<II', len(c), osz) + c)
            pos += osz
        assert pos == len(blob), (pos, len(blob))
        newraw = b''.join(parts)
        print('      条目 %d → %d (槽 %d, 余 %d)' % (st0, len(newraw), st0, st0 - len(newraw)))
        if len(newraw) > st0:
            raise SystemExit('★ %s #%d 溢出槽位, 需搬移 (危险) — 中止' % (tag, ent))
        d[b0 + off0:b0 + off0 + st0] = newraw + b'\x00' * (st0 - len(newraw))

    # ---------------- 5. 字库表 ----------------
    px = L.pack_atlas(A2)
    d[base + OFF_PAK_REC + PIX_OFF:base + OFF_PAK_REC + PIX_OFF + len(px)] = px
    print('[tex ] 12px 字形带 v=%d..%d, u=0..%d'
          % (BAND_V, BAND_V + CELL_H - 1, (len(ORDER) - 1) * STEP + CELL_W - 1))

    open(dst, 'wb').write(bytes(d))
    print('[iso ] %s' % dst)


def read_res(iso, lba, idx):
    d = open(iso, 'rb').read()
    b0 = lba * 2048
    e = struct.unpack_from('<12I', d, b0 + TAB_OFF + TAB_STEP * idx)
    raw = d[b0 + e[E_OFF]:b0 + e[E_OFF] + e[E_STORED]]
    recs, _ = lz_records(raw)
    return b''.join(dd for (_q, _l, _s, dd) in recs), e


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if '--plan' in sys.argv:
        src = sys.argv[sys.argv.index('--plan') + 1]
        for (lba, total, ent, tag) in RES_ENTRIES:
            blob, _ = read_res(src, lba, ent)
            print('== %s #%d  MapName 条目 ==' % (tag, ent))
            b2 = bytearray(blob)
            n = fix_mapnames(b2, diag=True)
            print('  ⇒ 共 %d 处' % n)
        raise SystemExit(0)
    main(sys.argv[1], sys.argv[2], '--diag' in sys.argv)
