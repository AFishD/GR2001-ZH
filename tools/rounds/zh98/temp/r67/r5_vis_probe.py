# -*- coding: utf-8 -*-
r"""r5_vis_probe.py — round67 **实机取证盘**: 把「开发访谈 1」正文换成新字的对照页。

与 `tools/iso_build/probe_engine_limit.py` 的区别 (也是它**不需要**抄字形的原因):
  · 原探针要把"已知字的字形"抄到高 lead 空白格里, 因为那时那些格是空的;
  · **本轮 GR_ZH113 的 329 个新字本来就已经落在真实格位上、用真实对偶码** ⇒
    直接把它们的**真实码位**写进正文即可 ⇒ 测的就是交付物本身, 没有"搬运"这一层。

页面结构 (每行都带 ASCII 标签 ⇒ 初始滚动在哪一行都能认出来):

    R67EXPAND
    O:  我国山        ← 对照: 现役旧字 (码位未变, 证明盘没坏)
    AD: <6 个新字>    ← 新字, lead 0xAD
    AE: <6 个新字>    ← 新字, lead 0xAE
    AF: <6 个新字>    ← 新字, lead 0xAF
    B0: <6 个新字>    ← 新字, lead 0xB0 (gate 允许的最后一档)

硬门禁 (沿用原探针那套):
  ① 改动只落在目标 <text> 区间内 (前缀/后缀逐字节相同);
  ② LZO 重压回环 + 不超槽 + ISO 尺寸不变;
  ③ 回读: 盘上 blob == 要写的 blob, 只有目标 <text> 变了;
  ④ 载荷里连续 0x80..0x9F 字节 ≤ 3;
  ⑤ **不动图集**: 本脚本一个像素都不写 (只改正文), 故顺便证明"新字形已经在盘上、不需要再抄"。

用法:
  python work/builds/GR_ZH98/temp/r67/r5_vis_probe.py <src.iso> <dst.iso> [--dry-run]
"""
import argparse
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
for _p in (os.path.join(REPO, 'tools', 'iso_build'), os.path.join(REPO, 'tools', 'text_csv')):
    sys.path.insert(0, _p)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np                                                            # noqa: E402
import tcslib                                                                 # noqa: E402
import dump_font as D                                                         # noqa: E402
import inject_text_csv as inj                                                 # noqa: E402
import make_font_testpage as MTP                                              # noqa: E402

ITEM = '开发访谈 1'
LABEL = 'R67EXPAND'
GAP = 90
LEADS = (0xAD, 0xAE, 0xAF, 0xB0)
N_PER_LEAD = 6
CONTROL = '我国山'
SEL = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_expand_zh113.csv')
TTF = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')


def rel(p):
    r = os.path.relpath(p, REPO)
    return r.replace('\\', '/') if not r.startswith('..') else p.replace('\\', '/')


def pick():
    """每组挑 N_PER_LEAD 个字: 按出现频率降序, 且**要求字形有区分度**(墨量适中)。"""
    import csv
    rows = list(csv.DictReader(io.open(SEL, encoding='utf-8-sig', newline='')))
    by_lead = {}
    for r in rows:
        by_lead.setdefault(int(r['new_lead'], 16), []).append(r)
    from PIL import Image, ImageDraw, ImageFont
    fnt = ImageFont.truetype(TTF, 16)

    def tpl(ch):
        img = Image.new('L', (32, 32), 255)
        ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
        return np.asarray(img)[8:24, 8:24] < 128

    out = {}
    for lead in LEADS:
        lst = sorted(by_lead[lead], key=lambda r: (-int(r['count']), r['codepoint']))
        picks, seen = [], set()
        for r in lst:
            t = tpl(r['char'])
            sig = t.tobytes()
            if sig in seen:
                continue
            seen.add(sig)
            picks.append(r)
            if len(picks) >= N_PER_LEAD:
                break
        out[lead] = picks
    return out, tpl


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    src, dst = os.path.abspath(a.src), os.path.abspath(a.dst)

    print('=' * 78)
    print('R67 实机取证盘: 新字 (真实码位) 写进「%s」正文' % ITEM)
    print('  src = %s' % rel(src))
    print('  dst = %s' % rel(dst))
    print('=' * 78)

    cs = tcslib.Charset()
    assert len(cs.enc_pair) == 1504, len(cs.enc_pair)
    font = D.load_font(src)
    ai_gray = np.frombuffer(D.atlas_gray(font['atlas'], 'engine'),
                            dtype=np.uint8).reshape(font['atlas']['h'], font['atlas']['w'])

    picks, tpl = pick()

    def pair_of(ch):
        p = cs.enc_pair.get(ch)
        assert p, '%r 没有对偶码' % ch
        return p

    rows = [('O', [(ch, pair_of(ch), None) for ch in CONTROL])]
    flat = []
    for lead in LEADS:
        lst = [(r['char'], (lead, int(r['new_trail'], 16)), int(r['slot'])) for r in picks[lead]]
        rows.append(('%02X' % lead, lst))
        flat.extend(lst)
    print('[chk ] 对照 %s + 新字 %d 个' % (CONTROL, len(flat)))
    for tag, lst in rows:
        print('   %-4s %s' % (tag + ':', '  '.join(
            '%s=%02X%02X%s' % (ch, p[0], p[1], '' if s is None else '(slot%d)' % s)
            for ch, p, s in lst)))

    # 每个新字的格必须**有墨** (证明字形真的在盘上)
    bad = []
    for ch, p, slot in flat:
        row, col = slot // tcslib.NCOL, slot % tcslib.NCOL
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        ink = int((ai_gray[y:y + 16, x:x + 16] == 0).sum())
        tpl_ink = int(tpl(ch).sum())
        if ink != tpl_ink:
            bad.append((ch, slot, ink, tpl_ink))
    assert not bad, '新字格墨量与模板不符 (说明字形没写进盘): %s' % bad[:5]
    print('[chk ] %d 个新字的盘上格墨量 == 16px 模板墨量 ✓ (字形确实已在盘上)' % len(flat))

    # ---------- 拼正文 ----------
    def build_block():
        out = bytearray(LABEL.encode('ascii') + b'{br}')
        for tag, lst in rows:
            out.extend(tag.encode('ascii') + b': ')
            for i, (_ch, p, _s) in enumerate(lst):
                if i:
                    out.extend(b' ')
                out.extend(bytes(p))
            out.extend(b'{br}')
        out.extend(b' ' * GAP)
        return bytes(out)

    iso = tcslib.Iso(src)
    spec = tcslib.RES['SFXML']['copies'][0]
    c = inj.Container(iso, 'SFXML', spec, cs)
    tgt = MTP.find_target(c.blob, cs, ITEM, '')
    L = len(tgt['data'])
    block = build_block()
    n_rep = L // len(block)
    assert n_rep >= 1, (len(block), L)
    new = block * n_rep
    pad = L - len(new)
    if pad:
        tail = block[:pad]
        cut = tail.rfind(b'{br}')
        if cut > 0 and pad - (cut + 4) > 0:
            tail = tail[:cut + 4] + b' ' * (pad - cut - 4)
        new += tail
    assert len(new) == L, (len(new), L)
    print('[文本] 块 %d B × %d 遍 + 收尾 %d B = %d B (与原文等长 ⇒ 零位移)'
          % (len(block), n_rep, pad, L))
    run = best = 0
    for b in new:
        run = run + 1 if 0x80 <= b <= 0x9F else 0
        best = max(best, run)
    assert best <= 3, '连续 0x80..0x9F = %d (>3)' % best
    print('[守卫] 连续 0x80..0x9F 最长 %d 个 (≤3) ✓' % best)

    new_blob = c.blob[:tgt['a']] + new + c.blob[tgt['b']:]
    loc = MTP.locality(c.blob, new_blob, tgt['a'], tgt['b'])
    print('[门禁①] blob %d → %d B; 前缀相同=%s 后缀相同=%s; 区间外差异 %d'
          % (len(c.blob), len(new_blob), loc['prefix_ok'], loc['suffix_ok'], loc['n_outside']))
    assert loc['prefix_ok'] and loc['suffix_ok'] and loc['n_outside'] == 0
    frame, n_sub = c.repack(new_blob)
    assert b''.join(s[0] for s in tcslib.lzo_subs(frame)) == new_blob
    assert len(frame) <= c.slot, (len(frame), c.slot)
    print('[门禁②] 重压 %d 子流 → %d B (槽 %d B, 余 %d) + LZO 回环 ✓'
          % (n_sub, len(frame), c.slot, c.slot - len(frame)))

    if a.dry_run:
        print('[dry ] 不写盘。')
        iso.close()
        return 0

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(c.entry['iso_off'])
        f.write(frame + b'\x00' * (c.slot - len(frame)))
    assert os.path.getsize(src) == os.path.getsize(dst), 'ISO 尺寸变了'
    iso.close()

    # ---------- 回读 ----------
    iso2 = tcslib.Iso(dst)
    e2 = iso2.img_entry(c.lba, c.idx)
    assert (e2['stored'], e2['off'], e2['real']) == \
        (c.entry['stored'], c.entry['off'], c.entry['real']), 'IMG 条目表被改了'
    blob2 = b''.join(s[0] for s in tcslib.lzo_subs(iso2.read(e2['iso_off'], e2['stored'])))
    assert blob2 == new_blob, '回读 blob != 目标 blob'
    eb, ea = MTP.parse_entries(c.blob), MTP.parse_entries(blob2)
    ck = [k for k, v in eb.items() if ea[k] != v]
    tk = [k for (k, _o, _l, d) in tcslib.parse_sfxml(c.blob) if d == tgt['data']]
    assert ck == tk, (ck, tk)
    # 图集字节必须一个都没动
    f2 = D.load_font(dst)
    assert bytes(f2['atlas']['pak']) == bytes(font['atlas']['pak']), '图集被改动了!'
    iso2.close()
    print('[门禁③] 回读: blob 逐字节 ✓; 变动的 <text> 只有 %s ✓; **图集一个字节都没动** ✓' % ck)

    # ---------- 期望图 (给报告肉眼对照用) ----------
    from PIL import Image, ImageDraw, ImageFont
    SC = 6
    cols = N_PER_LEAD
    rowsn = len(rows)
    cw, chh = 16 * SC + 8, 16 * SC + 26
    im = Image.new('RGB', (cols * cw + 8, rowsn * chh + 8), (255, 255, 255))
    d = ImageDraw.Draw(im)
    f_lbl = ImageFont.truetype(TTF, 13)
    for ri, (tag, lst) in enumerate(rows):
        for ci in range(cols):
            ox, oy = 8 + ci * cw, 8 + ri * chh
            d.rectangle([ox - 1, oy - 1, ox + 16 * SC, oy + 16 * SC], outline=(200, 200, 200))
            if ci < len(lst):
                ch = lst[ci][0]
                t = tpl(ch)
                a = np.kron(t, np.ones((SC, SC), dtype=bool))
                sub = np.where(a, 0, 255).astype(np.uint8)
                im.paste(Image.fromarray(sub, 'L').convert('RGB'), (ox, oy))
                d.text((ox, oy + 16 * SC + 2), '%s %02X%02X' % (ch, lst[ci][1][0], lst[ci][1][1]),
                       fill=(0, 0, 0), font=f_lbl)
        d.text((2, 8 + ri * chh), tag[0], fill=(200, 0, 0))
    out = os.path.join(HERE, 'vis_expected.png')
    im.save(out)
    print('[png ] 期望字形图 → %s (%d x %d)' % (rel(out), im.width, im.height))

    rep = dict(src=rel(src), dst=rel(dst), item=ITEM, label=LABEL, payload=L,
               block=len(block), repeats=n_rep, pad=pad,
               control=[dict(char=ch, pair='%02X%02X' % pair_of(ch),
                             slot=tcslib.pair_slot(*pair_of(ch))) for ch in CONTROL],
               probed=[dict(char=ch, pair='%02X%02X' % p, slot=s) for ch, p, s in flat],
               changed_texts=ck, atlas_untouched=True)
    io.open(os.path.join(HERE, 'vis_probe.json'), 'w', encoding='utf-8', newline='\n').write(
        json.dumps(rep, ensure_ascii=False, indent=1) + '\n')
    print('[done] %s' % rel(dst))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
