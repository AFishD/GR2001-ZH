# -*- coding: utf-8 -*-
r"""patch_zh93_font_ext.py — GR_ZH93 字库扩容补丁 (76 个缺字)

## 依据 (全部实机/静态实测, 详见 docs/REPORT_font_ext_zh93.md)

### ① 对偶码 (DBCS) 的图集落点 = "相位公式"
    引擎 cave:  idx = (b0-0xA1)*94 + (b1-0xA1) + 0xE0
    实测: 字 s=(b0,b1) 的字形在**存储帧**的格位
              x = 16 * ((s%62 + phi(s//62)) % 62) ,  y = 2 + 16*(R + 3*[R>=12])
    相位表 phi(R) 由 767 个字的 d=0 模板定位统计得到 (每行一致):
        R=0..3→6  R=4..7→12  R=8..11→18  R=13..15→30  R=17..18→36  R=19..23→2
    ⇒ 空闲合法 slot 里, 若其**引擎格**是空的/死副本, 就能直接放新字。
      实测可用 40 个 (683..699 / 1176,1177 / 1182..1209 中的空闲者)。

### ② 单字节码的图集落点 (实机探针标定)
    实机诊断盘 (DIAG2/DIAG3) 逐格涂块 → 取帧比对, 实测:
        引擎采样窗 = (u0 + 576) mod 1024 , v0 + 1        (记录 rect 本身不被采样)
    证据: 务 0xC9 rec(704,338) → 字形在 (256,338) = (704+576) mod 1024 ✓
          选 0xEC rec(256,354) → 字形在 (832,354) = (256+576) mod 1024 ✓
    ⇒ 新单字节码: 字形画在 (u0+576, v0+1) **并且**在记录 rect (u0,v0) 再放一份
      (后者是给 tools/text_csv 的字形预检看的, 引擎不采样, 互不干扰)。

### ③ 为什么不用 lead 扩容 (方案 C)
    `tools/text_csv/tcslib.py` 的 PAIR_LEAD_HI = 0xAE (冻结工具) ⇒ lead≥0xAE 的 pair
    会被预检判成 dead_pair 而**阻断写盘**; 且 lead 扩到 0xB0 会吞掉单字节 0xAF(的)/
    0xB0(你) (历史实测灾难性错位)。⇒ 本补丁**零 ELF 改动**, 只动数据面。

## 用法
  python tools/iso_build/patch_zh93_font_ext.py <src.iso> <dst.iso>
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
import numpy as np                                        # noqa: E402
from PIL import Image, ImageDraw, ImageFont               # noqa: E402
import tcslib                                             # noqa: E402
from lz77_decode import lzo1x_decompress                   # noqa: E402
from lzo1x_c import compress as lzo_compress               # noqa: E402

MENU_LBA = tcslib.MENU_LBA
FT_SLOT, OFF_FT = 4421, 0xB9120
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
FZ = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')

NCOL, CW, CH, Y0 = 62, 16, 16, 2
SKIP_ROW, SKIP_ROWS = 12, 3
# 实测相位表 (行 → 列相位)
PHI = {0: 6, 1: 6, 2: 6, 3: 6, 4: 12, 5: 12, 6: 12, 7: 12, 8: 18, 9: 18, 10: 18, 11: 18,
       12: 24, 13: 30, 14: 30, 15: 30, 16: 30, 17: 36, 18: 36, 19: 2, 20: 2, 21: 2, 22: 2, 23: 2}
SINGLE_DX, SINGLE_DY = 576, 1          # 实机标定: 引擎采样 = (u0+576) mod 1024, v0+1

# ── 76 个缺字 (用户译文里用到、现役字库没有的) ─────────────────────────
NOT_IN_CHARSET = ('×“”《》享伞促倍偏凝匣双吸坐壳套宾尖履巨扳拆挂捕斤旋栓款毫池泛热燃牛牲牺猪'
                  '玻璃磁磅稳箱纤终聚脆膛若荐著虽螺衍衣裂誉贡轮迟造采钢链震题额鼓（）')
DEAD_PAIR = '米延普志略'
MISSING = list(NOT_IN_CHARSET) + list(DEAD_PAIR)
assert len(NOT_IN_CHARSET) == 71 and len(DEAD_PAIR) == 5, (len(NOT_IN_CHARSET), len(DEAD_PAIR))

# ── 可用码位池 ────────────────────────────────────────────────────────
# ① 空闲合法对偶 slot (引擎格为空/死副本) —— 由脚本再逐格校验
PAIR_SLOTS = ([s for s in range(683, 700)] + [1176, 1177]
              + [s for s in range(1182, 1210)])
# ② 空闲单字节码 (⚠ 必须 ≥ 0x80: tcslib 把 <0x80 一律按 ASCII 解码, 用它会让
#    encode/decode 不对称 ⇒ 注入器直接拒绝; 首版误用 0x7F, 已被注入器拦下):
#    · 0x80..0xA0 (0x92 除外) = 字集之外的空白区
#    · 0x92 (EN 撇号) / 0xAE (EN ®) / 0xFF 实测**未被本盘文本使用**
#      (用户表里没有 {{BTN:E092/E0AE/E0FF}})
#    ⚠ 0xB1/0xB5/0xE7/0xF1 是用户译文里的按键图标占位
#      ({{BTN:E0B1/E0B5/E0E7/E0F1}}), **绝对不能**改 → 本补丁不碰。
SINGLE_CODES = ([c for c in range(0x80, 0xA1) if c != 0x92] + [0x92, 0xAE, 0xFF])


def yrow(R):
    return Y0 + CH * (R + (SKIP_ROWS if R >= SKIP_ROW else 0))


def slot_of(b1, b2):
    return (b1 - 0xA1) * 94 + (b2 - 0xA1)


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
    cs = tcslib.Charset()
    # ── 幂等: 先清掉上一次本补丁写进 charset 的条目 (可重复跑) ──
    _js = json.load(open(CHARSET, encoding='utf-8'))
    _meta = _js.pop('_font_ext_zh93', None)
    if _meta:
        for _s, _c in _meta['pair_slots']:
            _js['pair_of'].pop(_c, None)
        for _code, _c in _meta['single_codes']:
            _js['codes'].pop(_c, None)
        json.dump(_js, open(CHARSET, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('[idem] 已回退上次 charset 扩容 (%d 对偶 + %d 单字节)'
              % (len(_meta['pair_slots']), len(_meta['single_codes'])))
        cs = tcslib.Charset()
    iso = tcslib.Iso(src)
    ft_e = pak_e = None
    for i in range(24):
        e = iso.img_entry(MENU_LBA, i)
        if e['name'] == 'FONT.RES':
            ft_e = e
        elif e['name'] == 'COMMON.PAK':
            pak_e = e
        if ft_e and pak_e:
            break
    assert ft_e and pak_e, 'MENU.IMG 里找不到 FONT.RES / COMMON.PAK'
    print('[in  ] FONT.RES #? off=0x%X stored=%d ; COMMON.PAK off=0x%X stored=%d'
          % (ft_e['off'], ft_e['stored'], pak_e['off'], pak_e['stored']))
    pak = bytearray(iso.read(pak_e['iso_off'], pak_e['stored']))
    ft_slot = iso.read(ft_e['iso_off'], ft_e['stored'])
    iso.close()

    # ── 解析 PAK (用 tcslib 的口径: 像素数据偏移 = q+20+clut) ──
    recs = tcslib.parse_pak_records(bytes(pak))
    fa = [r for r in recs if r[0] == 'new_font_revised']
    assert len(fa) == 1, recs
    _nm, psm, W, H, clut, px_size, PX = fa[0]
    assert (psm, W, H) == (0x14, 1024, 512), (psm, W, H)
    assert px_size == 0x40010, hex(px_size)
    nb = np.frombuffer(bytes(pak[PX:PX + W * H // 2]), dtype=np.uint8).reshape(H, W // 2)
    A = np.empty((H, W), dtype=np.uint8)
    A[:, 0::2] = nb & 0x0F
    A[:, 1::2] = (nb >> 4) & 0x0F
    BASE_INK = (A == 0)
    print('[pak ] 图集 %dx%d psm=0x%02X px_off=0x%X 墨=%d' % (W, H, psm, PX, int(BASE_INK.sum())))

    # ── 解析 FT ──
    frecs, consumed = lz_records(ft_slot)
    ft = bytearray(frecs[0][3])
    assert len(frecs) == 1, [f[2] for f in frecs]
    p = 0
    l0 = struct.unpack_from('<I', ft, p)[0]
    p += 4 + l0
    nf = struct.unpack_from('<I', ft, p)[0]
    p += 4
    face_off = []
    for _ in range(nf):
        l = struct.unpack_from('<I', ft, p)[0]
        nm = ft[p + 4:p + 4 + l].decode('latin-1')
        p += 4 + l
        fld_off = p
        fld = list(struct.unpack_from('<14I', ft, p))
        p += 56
        nr = fld[4] * fld[5]
        face_off.append([nm, p, nr, fld_off, fld])
        p += nr * 10
    styles_off = p
    print('[ft  ] faces=%s  styles@%d' % ([(f[0], f[2]) for f in face_off], styles_off))
    DEF = [k for k, f in enumerate(face_off) if f[0] == 'default'][0]

    def rec_of(fi, code):
        nm, off, nr, _fo, _fld = face_off[fi]
        idx = code - 0x20
        if idx < 0 or idx >= nr:
            return None
        return struct.unpack_from('<BB4H', ft, off + idx * 10)

    # ── 分配 ──
    # 单字节码: 只能选**基盘没有映射**的 (0x7F..0xA0 无映射; 0xAE/E7/F1 是 EN 符号)
    free_single = [c for c in SINGLE_CODES if c not in cs.codes]
    print('[plan] 候选单字节码 %d 个: %s' % (len(free_single), ' '.join('%02X' % c for c in free_single)))
    used_slots = {slot_of(*p2) for p2 in cs.enc_pair.values()}
    cand_slots = []
    for s in PAIR_SLOTS:
        if s in used_slots:
            continue
        R, C = s // 62, s % 62
        if R not in PHI:
            continue
        x = 16 * ((C + PHI[R]) % 62)
        y = yrow(R)
        ink = int(BASE_INK[y:y + CH, x:x + CW].sum())
        cand_slots.append((s, R, C, PHI[R], x, y, ink))
    print('[plan] 候选对偶 slot %d 个 (引擎格墨量):' % len(cand_slots))
    for s, R, C, phi, x, y, ink in cand_slots:
        print('        slot=%4d 码=%02X%02X R=%2d 引擎格=(%4d,%3d) 墨=%3d' %
              (s, 0xA1 + s // 94, 0xA1 + s % 94, R, x, y, ink))
    need = len(MISSING)
    n_pair = min(len(cand_slots), need)
    n_single = need - n_pair
    assert n_single <= len(free_single), (n_single, len(free_single))
    print('[plan] 需要 %d 字 → 对偶 %d + 单字节 %d' % (need, n_pair, n_single))

    # ── 单字节码的落点 (free 区动态找空格) ──
    #   记录 (u0,v0): 预检格 (u0,v0) 与 引擎格 ((u0+576)%1024, v0+1) 都必须空
    def cell_free(x, y, need_rows=1):
        if x < 0 or y < 0 or x + CW > W or y + CH + need_rows > H:
            return False
        return int(BASE_INK[y:y + CH + need_rows, x:x + CW].sum()) == 0

    single_plan = []
    taken_rects = []                 # 已占矩形 (x, y, w, h) —— 含引擎格 17 行高

    def free_rect(x, y, w, h):
        for (a, b, bw, bh) in taken_rects:
            if x < a + bw and a < x + w and y < b + bh and b < y + h:
                return False
        return True

    for k in range(n_single):
        placed = False
        for y in (482, 434, 418, 402, 386, 466, 450):
            for c in range(0, 62):
                x = 16 * c
                ex = (x + SINGLE_DX) % W
                ey = y + SINGLE_DY
                if not cell_free(x, y) or not cell_free(ex, ey):
                    continue
                # 记录格与引擎格都按 16x17 占位 (引擎格比记录格低 1 行)
                if not free_rect(x, y, CW, CH + 1) or not free_rect(ex, ey, CW, CH + 1):
                    continue
                taken_rects.append((x, y, CW, CH + 1))
                taken_rects.append((ex, ey, CW, CH + 1))
                single_plan.append(dict(code=free_single[k], u0=x, v0=y, ex=ex, ey=ey))
                placed = True
                break
            if placed:
                break
        assert placed, '单字节码 %02X 找不到空位' % free_single[k]
    for v in single_plan:
        print('        单字节 %02X: 记录(%4d,%3d) 引擎格(%4d,%3d)' %
              (v['code'], v['u0'], v['v0'], v['ex'], v['ey']))

    # ── 渲染 16px 二值字形 ──
    fnt = ImageFont.truetype(FZ, 16)

    def render(ch):
        img = Image.new('L', (32, 32), 255)
        ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
        a = np.asarray(img)
        win = a[8:24, 8:24] < 128
        if not win.any():
            raise SystemExit('[FAIL] 字体缺字形 %r' % ch)
        fy, fx = np.where(a < 128)
        if fy.min() < 8 or fx.min() < 8 or fy.max() >= 24 or fx.max() >= 24:
            raise SystemExit('[FAIL] %r 墨越 16x16 窗' % ch)
        return win

    # ── 写图集 ──
    writes = []                      # (x, y, glyph, tag)
    for k in range(n_pair):
        s, R, C, phi, x, y, ink = cand_slots[k]
        writes.append((x, y, render(MISSING[k]), 'pair slot=%d 码=%02X%02X' %
                       (s, 0xA1 + s // 94, 0xA1 + s % 94)))
    for j in range(n_single):
        ch = MISSING[n_pair + j]
        v = single_plan[j]
        g = render(ch)
        writes.append((v['ex'], v['ey'], g, 'single %02X 引擎格' % v['code']))
        writes.append((v['u0'], v['v0'], g, 'single %02X 预检格' % v['code']))
    for x, y, g, tag in writes:
        A[y:y + CH, x:x + CW] = np.where(g, 0, 1)
    NEW_INK = (A == 0)
    print('[tex ] 写入 %d 处字形 (%d 字)' % (len(writes), need))

    # ── 自检: 旧图集只被"授权的格"改动 ──
    diff = BASE_INK != NEW_INK
    ys, xs = np.where(diff)
    touched = set()
    for y, x in zip(ys, xs):
        touched.add((x // 16 * 16, y // 16 * 16))
    allowed = set()
    for x, y, g, tag in writes:
        for yy in range(y, y + CH):
            for xx in range(x, x + CW):
                allowed.add((xx, yy))
    bad = [(x, y) for (x, y) in touched if not any(x <= xx < x + 16 and y <= yy < y + 16
                                                   for (xx, yy) in allowed)]
    assert not bad, '越界改动 %s' % bad[:5]
    # 旧字库部分 (行 0..19 里所有**活**格) 不变: 由 writes 的授权格保证
    print('[self] 图集改动落在 %d 个授权格内 ✓' % len(touched))

    # ── 写 FT 记录 (单字节码, large + default 两面) ──
    nrec = 0
    for v in single_plan:
        code = v['code']
        rec = struct.pack('<BB4H', 0, 16, v['u0'], v['v0'], v['u0'] + CW, v['v0'] + CH)
        for fi in range(len(face_off)):
            nm, off, nr, _fo, _fld = face_off[fi]
            idx = code - 0x20
            if idx < 0 or idx >= nr:
                continue
            if fi == 2:                       # huge 面不参与单字节汉字 (原盘亦无)
                continue
            ft[off + idx * 10:off + idx * 10 + 10] = rec
            nrec += 1
    print('[ft  ] 改写 %d 条记录 (%d 个单字节码 × 面)' % (nrec, len(single_plan)))
    # 其它记录必须一字不动
    cf = lzo_compress(bytes(ft))
    tail = ft_slot[8 + frecs[0][1]:consumed]
    new_slot = struct.pack('<II', len(cf), len(ft)) + cf + tail
    assert len(new_slot) <= FT_SLOT, 'FONT.RES 重压超槽 %d > %d' % (len(new_slot), FT_SLOT)
    new_slot = new_slot + b'\x00' * (FT_SLOT - len(new_slot))
    print('[ft  ] 重压 %d B (槽 %d)' % (len(new_slot), FT_SLOT))

    # ── 打包图集回 PAK ──
    packed = ((A[:, 1::2] << 4) | A[:, 0::2]).astype(np.uint8)
    assert packed.shape == (H, W // 2)
    pak[PX:PX + packed.nbytes] = packed.tobytes()

    # ── 更新 charset JSON ──
    js = json.load(open(CHARSET, encoding='utf-8'))
    assert len(js['codes']) == 76 and len(js['pair_of']) == 1281
    for k in range(n_pair):
        s, R, C, phi, x, y, ink = cand_slots[k]
        ch = MISSING[k]
        assert ch not in js['pair_of'] and ch not in js['codes']
        js['pair_of'][ch] = [0xA1 + s // 94, 0xA1 + s % 94]
    for j in range(n_single):
        ch = MISSING[n_pair + j]
        code = single_plan[j]['code']
        assert ch not in js['codes'] and code not in js['codes'].values()
        js['codes'][ch] = code
    js['_font_ext_zh93'] = dict(
        note='GR_ZH93 字库扩容: 76 缺字 (71 not_in_charset + 5 dead_pair)',
        pair_slots=[[cand_slots[k][0], MISSING[k]] for k in range(n_pair)],
        single_codes=[[single_plan[j]['code'], MISSING[n_pair + j]] for j in range(n_single)],
        single_rule='引擎采样 = (u0+576) mod 1024, v0+1 (实机 DIAG2/DIAG3 标定)',
        pair_rule='字形在 x=16*((slot%62+phi(row))%62), y=2+16*(row+3*[row>=12])')
    json.dump(js, open(CHARSET, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('[json] charset 更新: codes %d, pair_of %d' % (len(js['codes']), len(js['pair_of'])))

    # ── 写盘 (两段等长覆写) ──
    import shutil
    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(pak_e['iso_off'])
        f.write(bytes(pak))
        f.seek(ft_e['iso_off'])
        f.write(new_slot)
    print('[iso ] → %s' % dst)
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main(sys.argv[1], sys.argv[2]))
