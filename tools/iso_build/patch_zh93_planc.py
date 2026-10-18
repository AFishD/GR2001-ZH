# -*- coding: utf-8 -*-
r"""patch_zh93_planc.py — GR_ZH93「方案 C」：把引擎 DBCS lead 空间从 0xA1..0xAD 扩到 0xA1..0xB0，
把用户初译里最后 16 个缺字（+ 让位的「荐」）写进**引擎格真的空**的图集位置。

## 和历史方案 C（提交 eebe52ef, lead→0xB3）的关系与差异

历史补丁 = 4 处 ELF `sltiu ...,0xAE` → `0xB4` + 把 5 个落在 0xAF..0xB3 的单字节码
（的 你 键 练 + 图标 0xB1）1B→1B 搬进 0x7F..0x83。本盘 0x80..0xA0/0x92/0xAE/0xFF 已被上一轮
57 字扩容占满 ⇒ **没有空闲单字节码可搬**，而且 0xB1/0xB5/0xE7/0xF1 是用户译文里的手柄图标码
（{{BTN:E0B1}} ×7 / E0B5 ×21 / E0E7 ×1 / E0F1 ×1），绝不能当 lead。

⇒ 本补丁把 gate 抬到 **0xB1**（lead 0xA1..0xB0，**恰好停在图标码 0xB1 之前**）：
   * 落在新 lead 区间里的单字节码只有 3 个：0xAE 荐(1 次) / 0xAF 的(1247 次) / 0xB0 你(420 次)
     → **全部改成对偶码**（1B→2B；语言表压缩余量 15127B，够用）；
   * 的/你 的新对偶槽**就是它们字形已经所在的那一格**（slot 683/684，图集零改动）；
   * 0xAE..0xB0 里另外 101 个"死 pair"（偶像/人名等闲置字，含用户译文里的 志 略）
     **自动变成合法码位**，且它们的字形本来就画在图集里（逐字模板匹配 0 误差）⇒ 免费收益；
   * 图标码 0xB1/0xB5/0xE7/0xF1、键 0xB2、练 0xB3 及其余全部单字节码**原样不动**。

## 引擎采样规则（全部实证/反汇编可证）

* **对偶（pair）**：slot = (lead-0xA1)*94 + (trail-0xA1)；row = slot/62, col = slot%62；
  引擎格 x = 16*((col + PHI[row]) % 64)，y = yrow(row)。
  证据：1297 个对偶字逐个用 `方正像素16.ttf` 16px 模板在现役图集上比对，
  该公式 **785 个 mismatch=0**（另一候选 x=16*col 为 **0/1297**）；
  ELF cctc cave (0x417050) 反汇编出的 U0=16*col/V0=2+16*(row+3*[row≥12]) 与 PHI 相位共同解释。
  PHI = 行0-3:6 4-7:12 8-11:18 12:24 13-16:30 17-18:36 19-23:2
* **单字节码**：记录 (u0,v0) → 引擎采样 ((u0 + 16*PHI[row(v0)]) % 1024, v0+1)
  （的 0xAF: (16+288,179) = (304,179) —— 与图集里 的 的字形位置 (304,178) 一致；
    务 0xC9 实机探针 (256,338) 生效 ✓ 与 row18 PHI=36 → +576 一致）
* 写入框（16x16）必须与**全部活字形窗口**零交叠（别人的采样窗里落下我的墨 = 那个字被污染）。

## 用法
  python tools/iso_build/patch_zh93_planc.py <src.iso> <dst.iso> [--no-json] [--dry-run]
  src = 已含上一轮 57 字修复的基盘（work/builds/GR_ZH93/temp/exp/FIXED.iso）
"""
import csv
import json
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
import numpy as np                                     # noqa: E402
from PIL import Image, ImageDraw, ImageFont            # noqa: E402
import tcslib                                          # noqa: E402

CHARSET = tcslib.CHARSET
FZ = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
USER_TEXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text')
REPORT = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'planc_patch_report.json')

ELF_LBA, SEC_OFF, SEC_ADDR = 295, 0x80, 0x00100000
NEW_GATE = 0xB1            # 新上界（exclusive）⇒ lead 0xA1..0xB0
GATES = [
    (0x416EE8, 0x2CA900AE, 0x2CA900B1, 'ds16 cave 字节→对偶判定 (DrawString 取码)'),
    (0x417160, 0x2D0900AE, 0x2D0900B1, 'sw cave StringWidth lead 判定'),
    (0x41751C, 0x2D4B00AE, 0x2D4B00B1, 'DoWordWrap cave 逐字 lead 判定'),
    (0x5656A4, 0x2D6C00AE, 0x2D6C00B1, 'SWKERN cave 字形计数 lead 判定'),
]
LEAD_LO = 0xA1
W, H, CW, CH = 1024, 512, 16, 16
Y0, SKIP_ROW, SKIP_ROWS, NCOL = 2, 12, 3, 62
PHI = {0: 6, 1: 6, 2: 6, 3: 6, 4: 12, 5: 12, 6: 12, 7: 12, 8: 18, 9: 18, 10: 18, 11: 18,
       12: 24, 13: 30, 14: 30, 15: 30, 16: 30, 17: 36, 18: 36, 19: 2, 20: 2, 21: 2, 22: 2, 23: 2}

MISSING = '虽螺衍衣裂誉贡轮迟造钢题额鼓（）'
# 新 lead 区间里必须让位的单字节码 → 改成对偶码；槽位选它们字形已经在的那一格
MOVES = {'的': (683, 0xAF), '你': (684, 0xB0), '荐': (None, 0xAE)}
TARGETS = MISSING + '荐'


def yrow(r):
    return Y0 + CH * (r + (SKIP_ROWS if r >= SKIP_ROW else 0))


def slot_of(lead, trail):
    return (lead - LEAD_LO) * 94 + (trail - LEAD_LO)


def code_of(slot):
    return LEAD_LO + slot // 94, LEAD_LO + slot % 94


def cell_of(slot):
    r, c = slot // NCOL, slot % NCOL
    return 16 * ((c + PHI[r]) % 64), yrow(r), c, r


def tcs_cell(slot):
    r, c = slot // NCOL, slot % NCOL
    return 4 + CW * c, yrow(r)


def user_chars():
    """用户当前译文（要注入的表）里出现过的字符集合。"""
    chars = set()
    for fn in sorted(os.listdir(USER_TEXT)):
        if not fn.endswith('.csv'):
            continue
        with open(os.path.join(USER_TEXT, fn), encoding='utf-8-sig', newline='') as fh:
            for row in csv.DictReader(fh):
                t = row.get('text_edited')
                if t:
                    chars.update(t)
    return chars


def main(src, dst, do_json=True, dry=False):
    print('=' * 78)
    print('方案 C: lead 0xA1..0xB0 (gate 0xAE→0xB1), 补 %d 字 (16 缺字 + 荐让位)' % len(TARGETS))
    print('  src = %s' % src)
    print('=' * 78)

    iso = tcslib.Iso(src)
    ft_e = pak_e = None
    for i in range(24):
        e = iso.img_entry(tcslib.MENU_LBA, i)
        if e['name'] == 'FONT.RES':
            ft_e = e
        elif e['name'] == 'COMMON.PAK':
            pak_e = e
        if ft_e and pak_e:
            break
    assert ft_e and pak_e, '基盘里找不到 FONT.RES / COMMON.PAK'
    pak = bytearray(iso.read(pak_e['iso_off'], pak_e['stored']))
    ft_blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(ft_e['iso_off'], ft_e['stored'])))
    iso.close()
    print('[in ] COMMON.PAK off=0x%X stored=%d ; FONT.RES off=0x%X stored=%d'
          % (pak_e['off'], pak_e['stored'], ft_e['off'], ft_e['stored']))

    recs = tcslib.parse_pak_records(bytes(pak))
    fa = [r for r in recs if r[0] == 'new_font_revised']
    assert len(fa) == 1
    _nm, psm, w, h, clut, px_size, PX = fa[0]
    assert (psm, w, h) == (0x14, W, H) and px_size == 0x40010, (psm, w, h, px_size)
    nb = np.frombuffer(bytes(pak[PX:PX + W * H // 2]), dtype=np.uint8).reshape(H, W // 2)
    A = np.empty((H, W), dtype=np.uint8)
    A[:, 0::2] = nb & 0x0F
    A[:, 1::2] = (nb >> 4) & 0x0F
    BASE_INK = (A == 0)
    print('[pak] 图集 %dx%d px_off=0x%X 墨=%d' % (W, H, PX, int(BASE_INK.sum())))

    _he, faces = tcslib.parse_ft_faces(ft_blob)
    fi = {f[0]: i for i, f in enumerate(faces)}
    print('[ft ] faces=%s' % [(f[0], len(f[2])) for f in faces])

    js = json.load(open(CHARSET, encoding='utf-8'))
    pair_of = {ch: tuple(v) for ch, v in js['pair_of'].items()}
    singles = {ch: int(v) for ch, v in js['codes'].items()}
    used_slots = {slot_of(*v) for v in pair_of.values()}
    used_codes = set(singles.values())
    txt = user_chars()
    print('[txt] 用户译文用到的字符 %d 个' % len(txt))

    # ---------- 活字形窗口 ----------
    LIVE = np.zeros((H, W), dtype=bool)

    def mark(x, y):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(W, x + CW), min(H, y + CH)
        if x0 < x1 and y0 < y1:
            LIVE[y0:y1, x0:x1] = True

    n_pair = n_rec = n_idle = 0
    for ch, (b0, b1) in pair_of.items():
        s = slot_of(b0, b1)
        r, c = s // NCOL, s % NCOL
        reachable = b0 < NEW_GATE          # 旧盘上引擎读得到的 lead
        in_text = ch in txt
        if not reachable and not in_text:
            n_idle += 1                    # 闲置死 pair（本盘不渲染）⇒ 其格可覆盖
            continue
        x = 16 * ((c + PHI[r]) % 64)
        mark(x, yrow(r) + (1 if c + PHI[r] >= 64 else 0))
        n_pair += 1
    for fname in ('large', 'default', 'huge'):
        for code, rec in enumerate(faces[fi[fname]][2]):
            _b0, _b1, u0, v0, u1, v1 = rec
            if u1 <= u0 or v1 <= v0:
                continue
            # 记录框（工具口径）+ 两种"引擎采样"候选（保守取并集）
            mark(u0, v0)
            mark((u0 + 576) % W, v0 + 1)
            for rr, ph in PHI.items():
                if yrow(rr) == v0:
                    mark((u0 + 16 * ph) % W, v0 + 1)
            n_rec += 1
    print('[win] 活字形窗口: 对偶 %d（其中闲置死 pair %d 不计） + 记录 %d'
          % (n_pair, n_idle, n_rec))

    def hits(x, y):
        if y + CH > H or x + CW > W or x < 0:
            return 10 ** 6
        return int(LIVE[y:y + CH, x:x + CW].sum())

    # ---------- 落点 ----------
    # 先给 的/你 找"字形已在"的对偶槽（不写图集）
    auto = []
    for ch, (slot_hint, old_code) in MOVES.items():
        if slot_hint is None:
            continue
        s = slot_hint
        x, y, c, r = cell_of(s)
        g = (BASE_INK[y:y + CH, x:x + CW])
        auto.append(dict(char=ch, slot=s, x=x, y=y, ink=int(g.sum()), old_code=old_code,
                         tcs_x=tcs_cell(s)[0], tcs_ink=int(
                             BASE_INK[y:y + CH, tcs_cell(s)[0]:tcs_cell(s)[0] + CW].sum())))
        print('[move] %s: 单字节 0x%02X → 对偶槽 %d (%02X%02X) 引擎格=(%4d,%3d) 现有墨=%d'
              '  tcs格=(%4d,%3d) 墨=%d'
              % (ch, old_code, s, *code_of(s), x, y, auto[-1]['ink'], auto[-1]['tcs_x'], y,
                 auto[-1]['tcs_ink']))
        assert auto[-1]['ink'] > 20, '%s 的目标格里没有它的字形（墨=%d）' % (ch, auto[-1]['ink'])
        assert s not in used_slots, '槽 %d 已被 charset 占用' % s

    # 其余（16 缺字 + 荐）在新空间里找干净格
    need = len(TARGETS)
    cand = []
    for s in range(slot_of(0xAE, 0xA1), slot_of(0xB0, 0xFE) + 1):
        if s in used_slots or s in {d['slot'] for d in auto}:
            continue
        r, c = s // NCOL, s % NCOL
        if r not in PHI:
            continue
        x, y = cell_of(s)[0], yrow(r)
        h = hits(x, y)
        ink = int(BASE_INK[y:y + CH, x:x + CW].sum())
        cand.append(dict(slot=s, lead=LEAD_LO + s // 94, trail=LEAD_LO + s % 94, row=r, col=c,
                         x=x, y=y, hits=h, ink=ink,
                         tcs_x=tcs_cell(s)[0], tcs_hits=hits(tcs_cell(s)[0], y)))
    clean = [d for d in cand if d['hits'] == 0]
    clean.sort(key=lambda d: (d['row'], d['ink'], d['slot']))
    print('[sel] 新 lead 空间空闲槽 %d 个（行 19..24），引擎格与活窗口零交叠的 %d 个'
          % (len(cand), len(clean)))
    assert len(clean) >= need, '干净落点不够: 需 %d 有 %d' % (need, len(clean))
    pick = clean[:need]
    for d in pick:
        print('        slot=%4d 码=%02X%02X 行%d 列%2d 引擎格=(%4d,%3d) 基盘墨=%3d'
              '  tcs格=(%4d,%3d) 交叠=%d'
              % (d['slot'], d['lead'], d['trail'], d['row'], d['col'], d['x'], d['y'],
                 d['ink'], d['tcs_x'], d['y'], d['tcs_hits']))

    # ---------- 渲染并写入 ----------
    fnt = ImageFont.truetype(FZ, 16)

    def render(ch):
        img = Image.new('L', (32, 32), 255)
        ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
        a = np.asarray(img)
        win = a[8:24, 8:24] < 128
        if not win.any():
            raise SystemExit('[FAIL] 方正像素16 缺字形 %r' % ch)
        fy, fx = np.where(a < 128)
        if fy.min() < 8 or fx.min() < 8 or fy.max() >= 24 or fx.max() >= 24:
            raise SystemExit('[FAIL] %r 墨越 16x16 em 窗' % ch)
        return win

    print()
    print('[tex] 写图集 (顺序: 先写 tcs 预检副本, 再写引擎格 —— 引擎格必须最后落定):')
    for ch, d in zip(TARGETS, pick):
        d['char'] = ch
        d['glyph'] = render(ch)
        d['copies'] = 1
    # ① tcs 预检副本 (仅当该格与活窗口零交叠)
    for d in pick:
        if d['tcs_hits'] == 0:
            A[d['y']:d['y'] + CH, d['tcs_x']:d['tcs_x'] + CW] = np.where(d['glyph'], 0, 1)
            d['copies'] = 2
    # ② 引擎格 (最后写, 保证逐像素 = 渲染结果)
    for d in pick:
        A[d['y']:d['y'] + CH, d['x']:d['x'] + CW] = np.where(d['glyph'], 0, 1)
    for d in pick:
        now = (A[d['y']:d['y'] + CH, d['x']:d['x'] + CW] == 0)
        assert (now == d['glyph']).all(), '引擎格被覆盖: %s' % d['char']
        print('        %s → %02X%02X slot=%4d 引擎格=(%4d,%3d) 墨=%2d %s'
              % (d['char'], d['lead'], d['trail'], d['slot'], d['x'], d['y'],
                 int(d['glyph'].sum()),
                 '(tcs 格也写)' if d['copies'] == 2 else '(tcs 格有活字, 不写)'))

    # ---------- 自检: 图集改动只落在授权格 ----------
    NEW_INK = (A == 0)
    diff = BASE_INK != NEW_INK
    ys, xs = np.where(diff)
    touched = {(int(x) // 16 * 16, int(y) // 16 * 16) for y, x in zip(ys, xs)}
    allowed = set()
    for d in pick:
        cells = [(d['x'], d['y'])] + ([(d['tcs_x'], d['y'])] if d['copies'] == 2 else [])
        for (x0, y0) in cells:
            for yy in range(y0 - 1, y0 + CH + 1):
                for xx in range(x0 - 1, x0 + CW + 1):
                    allowed.add((xx // 16 * 16, yy // 16 * 16))
    bad = sorted(touched - allowed)
    assert not bad, '图集改动越界: %s' % bad[:6]
    print('[self] 图集改动 %d 像素, 全落 %d 个授权格内 ✓' % (int(diff.sum()), len(touched)))

    # ---------- 打包回 PAK (4bpp: 偶数列=低半字节) ----------
    packed = ((A[:, 1::2] << 4) | A[:, 0::2]).astype(np.uint8)
    assert packed.shape == (H, W // 2) and packed.nbytes == W * H // 2
    pak[PX:PX + packed.nbytes] = packed.tobytes()
    assert (np.frombuffer(bytes(pak[PX:PX + packed.nbytes]), dtype=np.uint8)
            .reshape(H, W // 2) == packed).all(), 'PAK 回写自检失败'
    print('[pak] 4bpp 图集已回写 (px_off=0x%X, %d B)' % (PX, packed.nbytes))

    # ---------- ELF ----------
    with open(src, 'rb') as f:
        for va, old, new, desc in GATES:
            f.seek(ELF_LBA * 2048 + SEC_OFF + (va - SEC_ADDR))
            cur = struct.unpack('<I', f.read(4))[0]
            assert cur == old, '0x%06X 原值 %08X != 期望 %08X (%s)' % (va, cur, old, desc)
    print('[elf] 4 处 lead 上界均为 0xAE ✓ → 0xB1（lead 0xA1..0xB0；图标码 0xB1 起不受影响）')

    # ---------- 写盘 ----------
    if not dry:
        shutil.copyfile(src, dst)
        with open(dst, 'r+b') as f:
            f.seek(pak_e['iso_off'])
            f.write(bytes(pak))
            for va, old, new, desc in GATES:
                f.seek(ELF_LBA * 2048 + SEC_OFF + (va - SEC_ADDR))
                f.write(struct.pack('<I', new))
        print('[iso] → %s' % dst)

    # ---------- charset ----------
    placed_meta = {}
    for d in auto:
        placed_meta[d['char']] = '%02X%02X slot=%d cell=(%d,%d) [原单字节 0x%02X, 字形已在]' % (
            *code_of(d['slot']), d['slot'], d['x'], d['y'], d['old_code'])
    for d in pick:
        placed_meta[d['char']] = '%02X%02X slot=%d cell=(%d,%d) 新写字形' % (
            d['lead'], d['trail'], d['slot'], d['x'], d['y'])
    if do_json and not dry:
        js2 = json.load(open(CHARSET, encoding='utf-8'))
        for d in auto:
            old_ch = next((ch for ch, c in js2['codes'].items() if int(c) == d['old_code']), None)
            assert old_ch == d['char'], (old_ch, d['char'])
            js2['codes'].pop(d['char'])
            js2['pair_of'][d['char']] = list(code_of(d['slot']))
            print('[json] %s: 单字节 0x%02X 撤销 → 对偶 %02X%02X'
                  % (d['char'], d['old_code'], *code_of(d['slot'])))
        for d in pick:
            # ★ 关键: 新 lead 区间里的单字节码必须**彻底撤销**, 否则编码器仍会写出 1 字节的 lead,
            #   引擎会把它当对偶码首字节 ⇒ 吞掉后一个字 + 画错字。
            c = js2['codes'].get(d['char'])
            if c is not None:
                assert LEAD_LO <= int(c) < NEW_GATE, (
                    '%s 的单字节码 0x%02X 不在新 lead 区间 [0x%02X,0x%02X) —— 不该删'
                    % (d['char'], int(c), LEAD_LO, NEW_GATE))
                js2['codes'].pop(d['char'])
                print('[json] %s: 单字节 0x%02X 撤销（它会变成 lead）→ 对偶 %02X%02X'
                      % (d['char'], int(c), d['lead'], d['trail']))
            js2['pair_of'][d['char']] = [d['lead'], d['trail']]
        # ---- 不变量 ----
        both = [ch for ch in js2['codes'] if ch in js2['pair_of']]
        assert not both, '同时有单字节码和对偶码: %s' % both[:5]
        bad_code = sorted({int(c) for c in js2['codes'].values() if LEAD_LO <= int(c) < NEW_GATE})
        assert not bad_code, '新 lead 区间里还有单字节码: %s' % ['0x%02X' % c for c in bad_code]
        bad_lead = sorted({v[0] for v in js2['pair_of'].values() if not (LEAD_LO <= v[0] < NEW_GATE)})
        print('[json] 越界对偶 lead（仍为死 pair, 引擎读不到）: %s'
              % (' '.join('0x%02X' % c for c in bad_lead) or '无'))
        js2['_font_ext_planc_zh93'] = dict(
            note='方案 C: gate 0xAE→0xB1, lead 0xA1..0xB0 (+282 码位); 16 缺字 + 的/你/荐 转对偶码',
            gate_new=NEW_GATE,
            placed=placed_meta,
            pair_rule='x = 16*((slot%62 + PHI[row]) % 64), y = yrow(row)  [785 字点 0 误差]',
            single_rule='引擎采样 = ((u0 + 16*PHI[row]) % 1024, v0+1)',
            window_rule='写入框与 活对偶格 ∪ 记录采样窗 零交叠',
        )
        json.dump(js2, open(CHARSET, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('[json] charset: codes %d, pair_of %d' % (len(js2['codes']), len(js2['pair_of'])))

    # ---------- 回读 ----------
    if not dry:
        vd = open(dst, 'rb').read(ELF_LBA * 2048 + SEC_OFF + 0x600000)
        for va, old, new, desc in GATES:
            o = ELF_LBA * 2048 + SEC_OFF + (va - SEC_ADDR)
            assert struct.unpack_from('<I', vd, o)[0] == new, 'ELF 回读失败 0x%06X' % va
        with open(dst, 'rb') as f2:
            f2.seek(pak_e['iso_off'])
            pak2 = f2.read(pak_e['stored'])
        fa2 = [r for r in tcslib.parse_pak_records(pak2) if r[0] == 'new_font_revised'][0]
        nb2 = np.frombuffer(pak2[fa2[6]:fa2[6] + W * H // 2], dtype=np.uint8).reshape(H, W // 2)
        A2 = np.empty((H, W), dtype=np.uint8)
        A2[:, 0::2] = nb2 & 0x0F
        A2[:, 1::2] = (nb2 >> 4) & 0x0F
        INK2 = (A2 == 0)
        for d in pick:
            assert (INK2[d['y']:d['y'] + CH, d['x']:d['x'] + CW] == d['glyph']).all(), \
                '回读不一致 %s' % d['char']
        assert tcslib.PAIR_LEAD_HI == NEW_GATE, (
            'tcslib.PAIR_LEAD_HI=%#x != %#x —— 请先同步 tools/text_csv/tcslib.py 的 '
            'PAIR_LEAD_HI / LEAD_HI' % (tcslib.PAIR_LEAD_HI, NEW_GATE))
        cs2 = tcslib.Charset()
        for d in auto + pick:
            ch = d['char']
            assert ch in cs2.enc_pair, '%s 不在新 charset 的对偶表里' % ch
            assert ch not in cs2.enc_single, '%s 仍是单字节码（会写出 lead 字节！）' % ch
            b = cs2.encode_strict(ch)
            want = bytes(code_of(d['slot']))
            assert b == want, '%s 编码 %s != 期望 %s' % (ch, b.hex(), want.hex())
            back, _ = cs2.decode(b)
            assert back == ch, (ch, back)
        print('[ver] 回读: %d 个新字形格逐像素一致 ✓ ; ELF 4 处 ✓ ; %d 字 encode/decode 往返 ✓'
              % (len(pick), len(auto) + len(pick)))

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    json.dump(dict(gate_new=NEW_GATE, targets=list(TARGETS),
                   auto_moves=[dict(d) for d in auto],
                   placed=[{k: v for k, v in d.items() if k != 'glyph'} for d in pick],
                   live_pair_windows=n_pair, live_rec_windows=n_rec,
                   idle_pairs_ignored=n_idle),
              open(REPORT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('[rep] → %s' % REPORT)
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    sys.exit(main(a[0], a[1], do_json='--no-json' not in sys.argv,
                  dry='--dry-run' in sys.argv))
