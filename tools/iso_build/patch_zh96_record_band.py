# -*- coding: utf-8 -*-
r"""patch_zh96_record_band.py — round47: 清掉「单字节记录格」里上一代字形残留的**溢出墨**。

## 用户报障 (round47)

> 「中」「抖」字的左下方出现一条横条, 疑似被下方的文字污染; 这一行最右侧的一部分块下方都有
> 几个脏像素, 而且实机可见。

## 查实结果 (gr47, 见 docs/REPORT_record_band_fix.md)

* 「中」= **单字节码 0xD6**, FT 记录矩形 `(u0,v0,u1,v1) = (912,338,928,354)` ⇒ 引擎采样窗 =
  这一格 `(912..927, 338..353)` (记录矩形就是采样窗: ELF cave 0x21ADE0 的 `a1 < fld[17]` 分支 +
  盘上 108 个 16x16 记录格的 方正像素16 模板逐像素 0 误差命中, 见 §证据)。
* 这一格的**最后一行** (y=353) 在本盘里是 `.#######........`, 而 方正像素16 模板的这一行是
  `.......#........` ⇒ 多出 6 个墨点 (x=913..918) = **用户看到的「左下横条」**。
* 来源: round45 之前, 行 19..24 的对偶字形被写在 `yrow-1` (比引擎格高 1 行), 于是**每格的第 0 行
  溢出到上一行的记录格里**。「中」正下方那一格是槽位 (19,27)「聚」的字形 —— 它现在已被
  round45 搬到 (19,57) = `(912..927, 354..369)`, **但它上一代留在 y=353 的那一行没人清**
  (round45 清带范围 = `[yrow, yrow+16)`, 恰好少一行 `yrow-1`; 而"记录矩形原样贴回"又把这一行
  连同污染一起贴了回来)。
* 同一条带上一共 **20 个记录格**受影响 (全部差异**只在 y=353 这一行**):
  训火动习面务准可会出换下如以到**中斗**是任 (行 18 的单字节码 0xC2..0xDA)。
  其中「斗」多 10 个墨点 ⇒ 看上去像「抖」(用户报的第二个字)。

## 本补丁做什么 (只做这一件事)

对**全部 544 条 FT 记录矩形**(3 个 face):
1. 只看"溢出带行" `S = {yrow(r)-1 : r ∈ 19..24} = {353,369,385,401,417,433}` 里的像素;
2. 该格的字符 (charset 单字节表) 用 `方正像素16.ttf` 按 `gen_font16.py` 同法渲染 16x16 模板;
3. **只有**当"格内差异全部落在 S 行里"(= 这一格的字形就是模板, 只是被溢出墨盖了)时,
   才把这些像素改回模板值 (墨→0, 空→调色板空值)。

⇒ 「中」的 y=353 恢复到模板的 `.......#` (横条消失), 「斗」同理; 别的一律不碰。

## 硬约束 (全部自检)

* **不碰 48B 包头**: 逐像素走 `Atlas.set_px` (只写段数据区), 回读核对包头逐字节不变;
* **不碰行 19..24 的字形**: 变更像素必须全部落在 S 行 (S 行都不在 6 条引擎行带里);
* **幂等**: 对已修好的盘再跑 = 0 改动;
* 记录矩形里"非 S 行"的像素一个都不变;
* 不改 charset / 不改 FT 记录 / 不改文本。

用法:
  python tools/iso_build/patch_zh96_record_band.py <src.iso> <dst.iso> [--dry-run] [--check-only]
"""
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np                                     # noqa: E402
import tcslib                                          # noqa: E402
from patch_zh94_glyph_align import Atlas               # noqa: E402  (同一套封包解码/写像素口径)

W, H = 1024, 512
NCOL, CW, CH = tcslib.NCOL, tcslib.CW, tcslib.CH
ROWS = list(range(19, 25))
FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')


def yrow(r):
    return tcslib.GRID_Y0 + CH * (r + (tcslib.GRID_SKIP_ROWS if r >= tcslib.GRID_SKIP_ROW else 0))


SPILL = sorted(yrow(r) - 1 for r in ROWS)              # 上一代字形溢出的那一行
REPORT = os.path.join(REPO, 'work', 'builds', 'GR_ZH96_fix', 'temp',
                      'r47', 'record_band_report.json')


def render16(ch, fnt):
    """方正像素16 16px → 16x16 布尔墨窗 (与 tools/font_pipeline/gen_font16.py 同法)。"""
    from PIL import Image, ImageDraw
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    return np.asarray(img)[8:24, 8:24] < 128


def load_font():
    from PIL import ImageFont
    assert os.path.isfile(FZ16), FZ16
    return ImageFont.truetype(FZ16, 16)


def plan(eng, faces, enc_single, fnt, verbose=True):
    """算出要修的像素。返回 (repairs, skipped, stats)。

    repairs = [dict(char, rect=[u0,v0,u1,v1], pixels=[[y,x,ink(bool)], ...], face_hits=[...])]
    """
    rev = dict((b, c) for c, b in enc_single.items())          # 码 → 字符
    rects = {}
    for fname, _fld, rs in faces:
        for idx, r in enumerate(rs):
            _b0, _b1, u0, v0, u1, v1 = r
            if u1 <= u0 or v1 <= v0:
                continue
            key = (u0, v0, u1, v1)
            d = rects.setdefault(key, dict(faces=set(), codes=set()))
            d['faces'].add(fname)
            d['codes'].add(idx + 0x20)

    repairs, skipped, nochar, clean, on_spill = [], [], 0, 0, 0
    for (u0, v0, u1, v1) in sorted(rects):
        w, h = u1 - u0, v1 - v0
        rows_here = [s for s in SPILL if v0 <= s < v1]
        if not rows_here:
            continue
        on_spill += 1
        if (w, h) != (CW, CH) or u0 + w > W or v0 + h > H:
            skipped.append(dict(rect=[u0, v0, u1, v1], why='矩形不是 16x16 (图标/ASCII 小矩形), 不适用模板'))
            continue
        chars = sorted(set(rev[c] for c in rects[(u0, v0, u1, v1)]['codes'] if c in rev))
        if not chars:
            nochar += 1
            continue
        cur = eng[v0:v1, u0:u1]
        done = set()
        for ch in chars:
            tpl = render16(ch, fnt)
            d = (cur != tpl)
            if not d.any():
                clean += 1
                continue
            bad_rows = sorted(set(int(v0 + y) for y in np.where(d.any(axis=1))[0]))
            if any(r not in SPILL for r in bad_rows):
                skipped.append(dict(rect=[u0, v0, u1, v1], char=ch,
                                    why='差异不止在溢出带 (字形与模板本就不一致), 不动',
                                    rows=bad_rows, n=int(d.sum())))
                continue
            px = [[int(v0 + y), int(u0 + x), bool(tpl[y, x])] for y, x in zip(*np.where(d))]
            key = (u0, v0, tuple(sorted(chars)))
            if key in done:
                continue
            done.add(key)
            repairs.append(dict(char=ch, chars=chars, rect=[u0, v0, u1, v1],
                                faces=sorted(rects[(u0, v0, u1, v1)]['faces']),
                                codes=sorted('0x%02X' % c for c in rects[(u0, v0, u1, v1)]['codes']),
                                rows=bad_rows, pixels=px))
    stats = dict(rects=len(rects), rects_on_spill=on_spill, nochar=nochar, clean=clean,
                 repairs=len(repairs), skipped=len(skipped))
    if verbose:
        print('[plan ] 记录矩形 %d 个 (3 face 去重); 其中 **%d 个**的矩形压在溢出带行上'
              % (stats['rects'], on_spill))
        print('[plan ] 这些格里: %d 个格的字与 方正像素16 模板本来就一致 ⇒ 无需动; %d 个无量宽模板'
              % (clean, nochar))
        print('[plan ] 需要修的格: %d 个' % len(repairs))
        for r in repairs:
            print('        %s 矩形 (u=%d..%d, v=%d..%d) 行 %s 修 %d 像素: %s'
                  % (r['char'], r['rect'][0], r['rect'][2], r['rect'][1], r['rect'][3],
                     r['rows'], len(r['pixels']),
                     [(p[0], p[1]) for p in r['pixels']][:12]))
        print('[plan ] 跳过 %d 个:' % len(skipped))
        for s in skipped:
            print('        %s' % s)
    return repairs, skipped, stats


def main(src, dst, dry=False, check_only=False):
    print('=' * 78)
    print('GR_ZH96_fix: 记录格「上一代字形溢出墨」清理 (只改溢出带行 %s)' % SPILL)
    print('  src = %s' % src)
    print('=' * 78)
    iso = tcslib.Iso(src)
    pak_e = ft_e = None
    for i in range(24):
        e = iso.img_entry(tcslib.MENU_LBA, i)
        if e['name'] == 'COMMON.PAK':
            pak_e = e
        elif e['name'] == 'FONT.RES':
            ft_e = e
        if pak_e and ft_e:
            break
    assert pak_e and ft_e, '基盘里找不到 COMMON.PAK / FONT.RES'
    pak = bytearray(iso.read(pak_e['iso_off'], pak_e['stored']))
    ft_blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(ft_e['iso_off'], ft_e['stored'])))
    iso.close()
    rec = [r for r in tcslib.parse_pak_records(bytes(pak)) if r[0] == 'new_font_revised']
    assert len(rec) == 1
    _nm, psm, w, h, clut, px_size, PX = rec[0]
    assert (psm, w, h) == (0x14, W, H), (psm, w, h)
    A = Atlas(pak, PX, px_size)
    _he, faces = tcslib.parse_ft_faces(ft_blob)
    cs = tcslib.Charset()
    print('[atlas] psm=0x%02X %dx%d px_off=0x%X 段=%d 引擎图墨=%d'
          % (psm, w, h, PX, len(A.segs), int(A.eng.sum())))
    print('[ft   ] faces=%s' % [(f[0], len(f[2])) for f in faces])
    print('[chars] charset 单字节码 %d 个 (本补丁只用单字节表; 与 round46 重排无关)'
          % len(cs.enc_single))

    fnt = load_font()
    repairs, skipped, stats = plan(A.eng, faces, cs.enc_single, fnt)

    # ---------- 空值: 全体 nibble 直方图里最多的非零值 ----------
    nb = np.frombuffer(bytes(A.nib), dtype=np.uint8)
    tot = np.bincount(nb & 0x0F, minlength=16) + np.bincount(nb >> 4, minlength=16)
    tot[0] = 0
    empty_val = int(np.argmax(tot))
    assert 1 <= empty_val <= 15, empty_val
    print('[pack ] 「空」用调色板索引 %d' % empty_val)

    En = A.eng.copy()
    npx = 0
    for r in repairs:
        for (y, x, ink) in r['pixels']:
            En[y, x] = ink
            npx += 1
    print('[write] 共改 %d 像素 (只统计"不同才写")' % npx)

    # ---------- 自检 ----------
    diff = (En != A.eng)
    in_spill = np.zeros(H, dtype=bool)
    for s in SPILL:
        in_spill[s] = True
    outside = int((diff & ~in_spill[:, None]).sum())
    print('[self1] 变更 %d 像素; 溢出带内 %d; **带外 %d** (期望 0)'
          % (int(diff.sum()), int((diff & in_spill[:, None]).sum()), outside))
    assert outside == 0, '有像素改在溢出带之外!'

    bad_rect = 0
    for r in repairs:
        u0, v0, u1, v1 = r['rect']
        sub = diff[v0:v1, u0:u1]
        bad_rect += int(sub.sum()) - sum(1 for p in r['pixels'] if v0 <= p[0] < v1 and u0 <= p[1] < u1)
    print('[self2] 修好的格在"非溢出带行"里的变更: %d (期望 0)' % bad_rect)
    assert bad_rect == 0

    # 记录矩形逐条复核: 除溢出带行外与源盘逐像素相同
    n_rect = n_changed = 0
    for fname, _fld, rs in faces:
        for idx, rc in enumerate(rs):
            _b0, _b1, u0, v0, u1, v1 = rc
            if u1 <= u0 or v1 <= v0:
                continue
            x0, x1 = max(0, u0), min(W, u1)
            y0, y1 = max(0, v0), min(H, v1)
            if x0 >= x1 or y0 >= y1:
                continue
            n_rect += 1
            sel = [yy for yy in range(y0, y1) if yy not in SPILL]
            if sel and (En[sel, x0:x1] != A.eng[sel, x0:x1]).any():
                n_changed += 1
    print('[self3] 544 条记录矩形 (非溢出带行) 与源盘不同的: %d (期望 0)' % n_changed)
    assert n_changed == 0

    # 修好的格 == 模板
    ok = 0
    for r in repairs:
        u0, v0, u1, v1 = r['rect']
        tpl = render16(r['char'], fnt)
        if (En[v0:v1, u0:u1] == tpl).all():
            ok += 1
        else:
            print('  !! %s (%d,%d) 修完仍与模板不一致' % (r['char'], u0, v0))
    print('[self4] 修好的格与 方正像素16 模板逐像素相同: %d/%d' % (ok, len(repairs)))
    assert ok == len(repairs)

    if check_only:
        print('[check] --check-only: 不写盘。需要修的像素 = %d' % npx)
        return 0
    if dry:
        print('[dry  ] --dry-run: 不写盘。')
        return 0
    if npx == 0:
        print('[done ] 无需改动 (幂等: 已修好的盘再跑 = 0 改动)')

    # ---------- 回写容器 (逐像素, 只写段数据区, 不碰 48B 包头) ----------
    changed = np.where(En != A.eng)
    print('[pack ] 回写 %d 像素 (逐像素 set_px; 只落在段数据区)' % len(changed[0]))
    for y, x in zip(changed[0].tolist(), changed[1].tolist()):
        A.set_px(int(x), int(y), bool(En[y, x]), empty_val)
    back, _cov = A.decode_engine()
    if not (back == En).all():
        bd = np.where(back != En)
        print('[pack ] !! 回写后引擎图不一致 %d 处, 前 6 个: %s'
              % (len(bd[0]), [(int(y), int(x)) for y, x in list(zip(*bd))[:6]]))
    assert (back == En).all(), '回写后引擎图与目标图不一致'

    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(pak_e['iso_off'] + PX)          # ★ 只写像素容器 (别碰 48B 包头 / PAK 头)
        f.write(bytes(A.nib))
    assert os.path.getsize(src) == os.path.getsize(dst), 'ISO 尺寸变了!'
    print('[iso  ] → %s (尺寸不变 %d B)' % (dst, os.path.getsize(dst)))

    # ---------- 回读核对 ----------
    with open(dst, 'rb') as f:
        f.seek(pak_e['iso_off'])
        pak2 = f.read(pak_e['stored'])
    recs2 = [r for r in tcslib.parse_pak_records(pak2) if r[0] == 'new_font_revised']
    assert len(recs2) == 1 and recs2[0][6] == PX
    assert (bytes(pak2[:PX]) == bytes(pak[:PX])
            and bytes(pak2[PX + W * H // 2:]) == bytes(pak[PX + W * H // 2:])), \
        '回读: 像素容器以外的 PAK 字节被改动了!'
    A2 = Atlas(bytearray(pak2), PX, px_size)
    assert (A2.decode_engine()[0] == En).all(), '回读引擎图与目标图不一致'
    print('[ver  ] 回读: PAK 里除像素容器外逐字节不变 ✓; 盘上解出的引擎图 == 目标图 ✓')

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    io.open(REPORT, 'w', encoding='utf-8', newline='\n').write(json.dumps(dict(
        src=os.path.relpath(src, REPO), dst=os.path.relpath(dst, REPO),
        spill_rows=SPILL, pixels=npx, stats=stats,
        repairs=[dict(char=r['char'], rect=r['rect'], rows=r['rows'], codes=r['codes'],
                      faces=r['faces'], pixels=[[p[0], p[1], bool(p[2])] for p in r['pixels']])
                 for r in repairs],
        skipped=skipped), ensure_ascii=False, indent=1) + '\n')
    print('[rep  ] → %s' % os.path.relpath(REPORT, REPO))
    return 0


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    if '--check-only' in sys.argv:
        sys.exit(main(a[0], a[0], check_only=True))
    sys.exit(main(a[0], a[1], dry='--dry-run' in sys.argv))
