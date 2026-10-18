# -*- coding: utf-8 -*-
r"""patch_zh93_font_ext_fix.py — GR_ZH93 字库扩容补丁 (安全版, 替代 patch_zh93_font_ext.py)

## 为什么要有这个"安全版" (故障定位结论, 证据见 docs/REPORT_font_ext_fix.md)

用实机隔离实验 (`work/builds/GR_ZH93/temp/exp/*`) 证明了:
  · **FONT.RES 记录改动本身无害** —— 只改 FONT.RES(记录/重压)的盘与现役盘 GR_ZH92 逐帧一致,
    正常进主菜单。
  · **触发不进主菜单的是图集写入的"某一个子集"**:
      q1  = 行19对偶(22格) + 单字节记录格 + 单字节引擎格   → 正常进主菜单 ✓
      q2  = q1 + **行11对偶(17格)**                        → 卡在过场动画 ✗
      c_live = 行11+行18+行19 (82格)                       → 通过 (但菜单字被毁)
      c_empty = 记录格+引擎格 (140格)                      → 通过
      atlas  = 全部 222 格                                 → 卡死 (可复现 2 次)
    ⇒ 行11 那 17 格 (x=304..560, y=178) 与底部带写入**同时存在**时会破坏 shell 初始化;
      而且这 17 格原本就是单字节 的 你 键 练 用 击 小 时 按 战 要 在 开 器 弹 射 队 的字形,
      **本来就绝对不能写** (毁掉它们会让菜单文字整片消失 —— DIAG4 已实证)。

## 本版做了什么

  1. **删掉 683..699 / 1176,1177 这两批对偶槽** (它们的格位是活字形), 只保留 1182..1209
     这 22 个"格位真的空"的行19槽。
  2. 单字节码仍用 0x80..0xA0(除0x92) + 0x92 + 0xAE + 0xFF 共 35 个,
     字形写在底部空区 (与 q1 实验完全相同, 已实测安全)。
  3. 76 个缺字里**只能容纳 22+35 = 57 个** ⇒ 按"在新译文里出现的次数"排序取前 57,
     其余 19 个字写入报告 `unplaced`, 由调用方决定 (改译文 / 等回收工具腾码位)。
  4. 对偶格公式修正为实测口径 **x = 16*((slot%62 + phi(row)) % 64)** (原版用 %62, 在
     C+phi>=62 的那 18 列上会写错位置; 本版只用的 1182..1209 恰好不受影响, 但公式已改正)。

## 用法
  python tools/iso_build/patch_zh93_font_ext_fix.py <src.iso> <dst.iso> [--csv-dir <text dir>]
  不传 --csv-dir 时用内置的 76 字顺序 (以保证可复现)。
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
FT_SLOT = 4421
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
FZ = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
REPORT = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'font_ext_fix_report.json')

NCOL, CW, CH, Y0 = 62, 16, 16, 2
SKIP_ROW, SKIP_ROWS = 12, 3
PHI = {0: 6, 1: 6, 2: 6, 3: 6, 4: 12, 5: 12, 6: 12, 7: 12, 8: 18, 9: 18, 10: 18, 11: 18,
       12: 24, 13: 30, 14: 30, 15: 30, 16: 30, 17: 36, 18: 36, 19: 2, 20: 2, 21: 2, 22: 2, 23: 2}
SINGLE_DX, SINGLE_DY = 576, 1

NOT_IN_CHARSET = ('×“”《》享伞促倍偏凝匣双吸坐壳套宾尖履巨扳拆挂捕斤旋栓款毫池泛热燃牛牲牺猪'
                  '玻璃磁磅稳箱纤终聚脆膛若荐著虽螺衍衣裂誉贡轮迟造采钢链震题额鼓（）')
DEAD_PAIR = '米延普志略'
MISSING_ALL = list(dict.fromkeys(NOT_IN_CHARSET + DEAD_PAIR))
assert len(MISSING_ALL) == 76, len(MISSING_ALL)

# ── 安全落点池 ────────────────────────────────────────────────────────
# 行19 的 1182..1209: 引擎格 (16*((C+2)%64), 354) 在基盘图集上是空的 (实测墨 1..17 的残墨)
PAIR_SLOTS = list(range(1182, 1210))          # 28 个候选; 其中 6 个已被 charset 占用, 实得 22
assert len(PAIR_SLOTS) == 28
SINGLE_CODES = ([c for c in range(0x80, 0xA1) if c != 0x92] + [0x92, 0xAE, 0xFF])
assert len(SINGLE_CODES) == 35
# ⚠ 0xB1/0xB5/0xE7/0xF1 绝不能动 (用户译文里的 {{BTN:...}} 手柄图标占位)


def yrow(R):
    return Y0 + CH * (R + (SKIP_ROWS if R >= SKIP_ROW else 0))


def engine_cell(slot):
    """实测口径: x = 16*((slot%62 + phi(row)) % 64), y = yrow(row)"""
    R, C = slot // NCOL, slot % NCOL
    return 16 * ((C + PHI[R]) % 64), yrow(R)


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


def pick_chars(csv_dir):
    """按"在新译文里出现的次数"降序取前 57 个字 (保证报告可复现)。"""
    import csv as _csv
    freq = {c: 0 for c in MISSING_ALL}
    if csv_dir and os.path.isdir(csv_dir):
        for fn in sorted(os.listdir(csv_dir)):
            if not fn.endswith('.csv'):
                continue
            with open(os.path.join(csv_dir, fn), encoding='utf-8-sig', newline='') as fh:
                for row in _csv.DictReader(fh):
                    t = row.get('text_edited') or ''
                    if not t:
                        continue
                    for c in MISSING_ALL:
                        if c in t:
                            freq[c] += t.count(c)
    keep = sorted(MISSING_ALL, key=lambda c: (-freq[c], MISSING_ALL.index(c)))
    return keep[:57], keep[57:], freq


def main(src, dst, csv_dir=None):
    keep, drop, freq = pick_chars(csv_dir)
    print('[pick] 可安置 57 字, 落选 %d 字: %s' % (len(drop), ''.join(drop)))
    for c in drop:
        print('        落选 %s (新译文出现 %d 次)' % (c, freq[c]))

    cs = tcslib.Charset()
    _js = json.load(open(CHARSET, encoding='utf-8'))
    for key in ('_font_ext_zh93', '_font_ext_zh93_fix'):
        _meta = _js.pop(key, None)
        if _meta:
            for _s, _c in _meta.get('pair_slots', []):
                _js['pair_of'].pop(_c, None)
            for _code, _c in _meta.get('single_codes', []):
                _js['codes'].pop(_c, None)
            json.dump(_js, open(CHARSET, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print('[idem] 回退上次扩容记录 (%s)' % key)
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
    assert ft_e and pak_e
    print('[in  ] FONT.RES off=0x%X stored=%d ; COMMON.PAK off=0x%X stored=%d'
          % (ft_e['off'], ft_e['stored'], pak_e['off'], pak_e['stored']))
    pak = bytearray(iso.read(pak_e['iso_off'], pak_e['stored']))
    ft_slot = iso.read(ft_e['iso_off'], ft_e['stored'])
    iso.close()

    recs = tcslib.parse_pak_records(bytes(pak))
    fa = [r for r in recs if r[0] == 'new_font_revised']
    assert len(fa) == 1
    _nm, psm, W, H, clut, px_size, PX = fa[0]
    assert (psm, W, H) == (0x14, 1024, 512) and px_size == 0x40010
    nb = np.frombuffer(bytes(pak[PX:PX + W * H // 2]), dtype=np.uint8).reshape(H, W // 2)
    A = np.empty((H, W), dtype=np.uint8)
    A[:, 0::2] = nb & 0x0F
    A[:, 1::2] = (nb >> 4) & 0x0F
    BASE_INK = (A == 0)
    print('[pak ] 图集 %dx%d px_off=0x%X 墨=%d' % (W, H, PX, int(BASE_INK.sum())))

    frecs, consumed = lz_records(ft_slot)
    ft = bytearray(frecs[0][3])
    assert len(frecs) == 1
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
    print('[ft  ] faces=%s' % [(f[0], f[2]) for f in face_off])

    # ── 对偶槽: 只保留 1182..1209, 并逐格自检"引擎格是空的" ──
    used_slots = {slot for slot in ((b0 - 0xA1) * 94 + (b1 - 0xA1)
                                    for b0, b1 in cs.enc_pair.values())}
    cand = []
    for s in PAIR_SLOTS:
        if s in used_slots:
            print('[skip] slot %d 已被 charset 占用' % s)
            continue
        x, y = engine_cell(s)
        ink = int(BASE_INK[y:y + CH, x:x + CW].sum())
        # 与"活字形"交叉检查: 该格若含真字形则不可用 (墨量阈值 40 由实测字形墨量 ~55-90 反推)
        ok = ink < 40
        print('        slot=%4d 码=%02X%02X 引擎格=(%4d,%3d) 基盘墨=%3d %s'
              % (s, 0xA1 + s // 94, 0xA1 + s % 94, x, y, ink, 'OK' if ok else 'SKIP(有活字形)'))
        if ok:
            cand.append((s, x, y, ink))
    n_pair = min(len(cand), len(keep))
    n_single = len(keep) - n_pair
    print('[plan] 需 %d 字 → 对偶 %d + 单字节 %d (单字节码池 %d)'
          % (len(keep), n_pair, n_single, len(SINGLE_CODES)))
    assert n_single <= len(SINGLE_CODES), '单字节码不够: 需 %d 有 %d' % (n_single, len(SINGLE_CODES))

    # ── 单字节落点: 底部空区 (与已实测安全的 q1 同款) ──
    def cell_free(x, y):
        if x < 0 or y < 0 or x + CW > W or y + CH + 1 > H:
            return False
        return int(BASE_INK[y:y + CH + 1, x:x + CW].sum()) == 0

    single_plan = []
    taken = []

    def free_rect(x, y, w, h):
        return all(not (x < a + bw and a < x + w and y < b + bh and b < y + h)
                   for (a, b, bw, bh) in taken)

    for k in range(n_single):
        placed = False
        for y in (482, 434, 418, 402, 386, 466, 450):
            for c in range(0, 62):
                x = 16 * c
                ex, ey = (x + SINGLE_DX) % W, y + SINGLE_DY
                if not cell_free(x, y) or not cell_free(ex, ey):
                    continue
                if not free_rect(x, y, CW, CH + 1) or not free_rect(ex, ey, CW, CH + 1):
                    continue
                taken.append((x, y, CW, CH + 1))
                taken.append((ex, ey, CW, CH + 1))
                single_plan.append(dict(code=SINGLE_CODES[k], u0=x, v0=y, ex=ex, ey=ey))
                placed = True
                break
            if placed:
                break
        assert placed, '单字节码 %02X 找不到空位' % SINGLE_CODES[k]
    for v in single_plan:
        print('        单字节 %02X: 记录(%4d,%3d) 引擎格(%4d,%3d)'
              % (v['code'], v['u0'], v['v0'], v['ex'], v['ey']))

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

    writes = []
    for k in range(n_pair):
        s, x, y, ink = cand[k]
        writes.append((x, y, render(keep[k]), 'pair slot=%d' % s))
    for j in range(n_single):
        ch = keep[n_pair + j]
        v = single_plan[j]
        g = render(ch)
        writes.append((v['ex'], v['ey'], g, 'single %02X 引擎格' % v['code']))
        writes.append((v['u0'], v['v0'], g, 'single %02X 预检格' % v['code']))
    for x, y, g, tag in writes:
        A[y:y + CH, x:x + CW] = np.where(g, 0, 1)
    NEW_INK = (A == 0)
    print('[tex ] 写入 %d 处字形 (%d 字)' % (len(writes), len(keep)))

    diff = BASE_INK != NEW_INK
    ys, xs = np.where(diff)
    touched = {(int(x) // 16 * 16, int(y) // 16 * 16) for y, x in zip(ys, xs)}
    allowed = set()
    for x, y, g, tag in writes:
        for yy in range(y - 1, y + CH + 1):
            for xx in range(x - 1, x + CW + 1):
                allowed.add((xx // 16 * 16, yy // 16 * 16))
    bad = sorted(touched - allowed)
    assert not bad, '越界改动 %s' % bad[:5]
    print('[self] 图集改动落在 %d 个授权格内 ✓' % len(touched))
    # 绝不允许碰到行 0..19 的活字形区 (y < 434 且非 1182..1209 的引擎行 354)
    for (cx, cy) in touched:
        assert cy >= 352, '改动落到上部活字形区: (%d,%d)' % (cx, cy)

    nrec = 0
    for v in single_plan:
        rec = struct.pack('<BB4H', 0, 16, v['u0'], v['v0'], v['u0'] + CW, v['v0'] + CH)
        for fi in range(len(face_off)):
            nm, off, nr, _fo, _fld = face_off[fi]
            idx = v['code'] - 0x20
            if idx < 0 or idx >= nr or fi == 2:
                continue
            ft[off + idx * 10:off + idx * 10 + 10] = rec
            nrec += 1
    print('[ft  ] 改写 %d 条记录' % nrec)
    cf = lzo_compress(bytes(ft))
    tail = ft_slot[8 + frecs[0][1]:consumed]
    new_slot = struct.pack('<II', len(cf), len(ft)) + cf + tail
    assert len(new_slot) <= FT_SLOT
    new_slot = new_slot + b'\x00' * (FT_SLOT - len(new_slot))
    print('[ft  ] 重压 %d B (槽 %d)' % (len(new_slot), FT_SLOT))

    packed = ((A[:, 1::2] << 4) | A[:, 0::2]).astype(np.uint8)
    pak[PX:PX + packed.nbytes] = packed.tobytes()

    js = json.load(open(CHARSET, encoding='utf-8'))
    # ★ 5 个 "dead_pair" 字 (米延普志略) 在 pair_of 里有一条 lead>=0xAE 的记录 —— 引擎永远读不出
    #   (tcslib 预检也判 dead_pair 阻断写盘), 这里先把它删掉, 再挂到新码位上。
    for ch in keep:
        v = js['pair_of'].get(ch)
        if v and not (tcslib.PAIR_LEAD_LO <= v[0] < tcslib.PAIR_LEAD_HI):
            print('[dead] 移除 %s 的死 pair %02X%02X (引擎不可达)' % (ch, v[0], v[1]))
            js['pair_of'].pop(ch)
        assert ch not in js['codes'], '%s 已在单字节表里' % ch
    for k in range(n_pair):
        s = cand[k][0]
        ch = keep[k]
        assert ch not in js['pair_of'], '%s 仍在 pair_of' % ch
        js['pair_of'][ch] = [0xA1 + s // 94, 0xA1 + s % 94]
    for j in range(n_single):
        ch = keep[n_pair + j]
        code = single_plan[j]['code']
        assert ch not in js['codes'] and code not in js['codes'].values()
        js['codes'][ch] = code
    js['_font_ext_zh93_fix'] = dict(
        note='GR_ZH93 安全扩容: 22 对偶 (行19空格) + 35 单字节 (底部空区) = 57 字',
        pair_slots=[[cand[k][0], keep[k]] for k in range(n_pair)],
        single_codes=[[single_plan[j]['code'], keep[n_pair + j]] for j in range(n_single)],
        unplaced=drop,
        pair_rule='x = 16*((slot%62 + phi(row)) % 64), y = yrow(row)  [实测 1000+ 字点拟合]',
        single_rule='引擎采样 = (u0+576) mod 1024, v0+1  [行18/19 实测]',
        removed='683..699 / 1176,1177 (那 19 格的活字形属于 的 你 键 练 用 击 小 时 按 战 要 在 开 器 弹 射 队 / 顽 饿)')
    json.dump(js, open(CHARSET, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('[json] charset: codes %d, pair_of %d' % (len(js['codes']), len(js['pair_of'])))

    import shutil
    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(pak_e['iso_off'])
        f.write(bytes(pak))
        f.seek(ft_e['iso_off'])
        f.write(new_slot)
    placed = {c: (('pair %02X%02X' % (0xA1 + cand[k][0] // 94, 0xA1 + cand[k][0] % 94))
                  if k < n_pair else ('single %02X' % single_plan[k - n_pair]['code']))
              for k, c in enumerate(keep)}
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    json.dump(dict(placed=placed, unplaced={c: freq[c] for c in drop},
                   n_pair=n_pair, n_single=n_single, writes=len(writes)),
              open(REPORT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('[iso ] → %s' % dst)
    print('[rep ] → %s  (已安置 %d 字, 未安置 %d 字: %s)'
          % (REPORT, len(keep), len(drop), ''.join(drop)))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    cd = None
    if '--csv-dir' in sys.argv:
        cd = sys.argv[sys.argv.index('--csv-dir') + 1]
    sys.exit(main(a[0], a[1], cd))
