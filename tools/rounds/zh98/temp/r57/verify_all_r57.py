# -*- coding: utf-8 -*-
r"""round57 静态验收 (只读): GR_ZH107 的 ELF 换码 / 巧合零改动 / 受保护区 / 紧凑布局 / charset。

用法: python verify_all_r57.py [--iso107 <path>]
"""
import argparse
import hashlib
import io
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
R56 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56')
ISO105 = os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso')
ISO106 = os.path.join(REPO, 'work', 'builds', 'GR_ZH106', 'GR_ZH106.iso')
CS_OLD = os.path.join(R56, 'charset_before_r56.json')
CS_NEW_R56 = os.path.join(R56, 'charset_after_r56.json')
CS_CUR = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
OLD_QI = bytes.fromhex('a3d6a1f8a2df')          # 旧码「请等待」
NEW_QI = bytes.fromhex('a3d5a1f8a2de')          # 新码「请等待」(r56 紧凑后的口径)
ZR = bytes.fromhex('a2a9a1a7d6')                # 「载入中」(码位未变)
QI_OFFS = [0x50B840, 0x50B860, 0x50B890, 0x50B8C0, 0x50B8E8]
ZR_OFFS = [0x50B820, 0x50B858, 0x50B870, 0x50B8A8, 0x50B8D8]

FAIL = []


def check(name, ok, detail=''):
    print('  [%s] %-56s %s' % ('✓' if ok else '✗', name, detail))
    if not ok:
        FAIL.append(name)


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def count(data, pat):
    n, s = 0, 0
    pos = []
    while True:
        k = data.find(pat, s)
        if k < 0:
            return n, pos
        n += 1
        pos.append(k)
        s = k + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso107', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH107',
                                                     'GR_ZH107.iso'))
    a = ap.parse_args()
    iso107 = a.iso107
    print('=' * 100)
    print('round57 静态验收')
    print('=' * 100)
    shas = {}
    for k, p in (('GR_ZH105', ISO105), ('GR_ZH106', ISO106), ('GR_ZH107', iso107)):
        shas[k] = sha(p)
        print('  %-9s sha256 %s  %d B  %s' % (k, shas[k], os.path.getsize(p), p))
    d105 = open(ISO105, 'rb').read()
    d106 = open(ISO106, 'rb').read()
    d107 = open(iso107, 'rb').read()
    old = tcslib.Charset(CS_OLD)
    new = tcslib.Charset(CS_CUR)

    print('\n── 1. ELF 5 段载入提示条: 旧码 → 新码 ──')
    n105o, p105o = count(d105, OLD_QI)
    n106o, _ = count(d106, OLD_QI)
    n107o, _ = count(d107, OLD_QI)
    n105n, _ = count(d105, NEW_QI)
    n106n, _ = count(d106, NEW_QI)
    n107n, p107n = count(d107, NEW_QI)
    print('   旧码串 a3 d6 a1 f8 a2 df (请等待):  105=%d  106=%d  **107=%d**' % (n105o, n106o, n107o))
    print('   新码串 a3 d5 a1 f8 a2 de (请等待):  105=%d  106=%d  **107=%d**' % (n105n, n106n, n107n))
    check('ELF 旧码串命中 0 (107)', n107o == 0, '105/106 都是 %d 处' % n105o)
    check('ELF 新码串命中 5 (107)', n107n == 5, '位置 %s' % ', '.join('0x%X' % x for x in p107n))
    check('新码串位置与旧码串位置逐一对应 (长度不变)', p107n == p105o,
          '%s vs %s' % ([hex(x) for x in p107n[:2]], [hex(x) for x in p105o[:2]]))
    same_text = True
    for off in QI_OFFS:
        b105 = d105[off:off + 6]
        b107 = d107[off:off + 6]
        t1 = old.decode(b105)[0]
        t2 = new.decode(b107)[0]
        if t1 != t2 or len(b105) != len(b107):
            same_text = False
        print('   @0x%X  105 %s → 107 %s   旧解 %r == 新解 %r'
              % (off, b105.hex(' '), b107.hex(' '), t1, t2))
    check('新 charset 解 107 的 5 段 == 旧 charset 解 105 的原文', same_text)
    zr_same = all(d105[o:o + 5] == d107[o:o + 5] for o in ZR_OFFS)
    check('「载入中」(码位未变) 5 处字节 105 == 107', zr_same,
          '旧 %s / 新 %s' % (ZR.hex(' '), new.encode_strict('载入中').hex(' ')))

    print('\n── 2. 二进制巧合零改动 ──')
    named = [('概起', 0x33C1A2), ('概起', 0x33C1B6), ('接齿', 0x34871A), ('接齿', 0x37924A),
             ('治飞', 0x3C1866), ('能集', 0x43F18A), ('能集', 0x43FABE)]
    ok_named = True
    for (txt, off) in named:
        b105 = d105[off:off + 4]
        b106 = d106[off:off + 4]
        b107 = d107[off:off + 4]
        same = (b105 == b106 == b107)
        ok_named &= same
        print('   @0x%-8X %-6r 105=%s 106=%s 107=%s %s'
              % (off, txt, b105.hex(' '), b106.hex(' '), b107.hex(' '),
                 '✓ 0 改动' if same else '✗ 变了'))
    check('Lead 点名的 7 段二进制巧合: 105/106/107 逐字节相同', ok_named)
    # 全部"段内汉字全是 2 字节对偶码"的 IMG 之外段 (细扫留证) 也一律 0 改动
    ev = None
    rep = os.path.join(HERE, 'compact_report.json')
    if os.path.exists(rep):
        ev = (json.load(io.open(rep, encoding='utf-8')).get('scan') or {}).get('short') or {}
    if ev:
        pr = ev.get('pair_runs_evidence') or []
        bad = [e for e in pr if d105[e['off']:e['off'] + e['nbytes']]
               != d107[e['off']:e['off'] + e['nbytes']]]
        check('细扫留证的"全对偶码"段 %d 个: 105 == 107' % len(pr), not bad,
              ('全部 0 改动' if not bad else '变了 %d 个: %s'
               % (len(bad), [hex(x['off']) for x in bad[:5]])))

    print('\n── 3. 受保护区: GR_ZH107 vs GR_ZH106 差异 0 ──')
    iso = tcslib.Iso(iso107)
    f = __import__('dump_font').load_font(iso107)
    regions = []
    for tag, lba in (('MENU.IMG', FC.MENU_LBA), ('GR.IMG', FC.GR_LBA)):
        for idx in range(FC.img_entry_count(iso, lba)):
            e = iso.img_entry(lba, idx)
            if 0 < e['stored'] < 0x7FFFFFFF:
                regions.append((e['iso_off'], e['iso_off'] + e['stored'],
                                '%s#%d %s' % (tag, idx, e['name'])))
    px0 = f['pak_e']['iso_off'] + f['atlas']['px_off']
    px1 = px0 + f['atlas']['px_size']
    ft0 = f['ft_e']['iso_off']
    ft1 = ft0 + f['ft_e']['stored']

    def ndiff(x0, x1):
        n = 0
        for i in range(x0, x1, 1 << 20):
            j = min(x1, i + (1 << 20))
            if d106[i:j] != d107[i:j]:
                n += sum(1 for k in range(i, j) if d106[k] != d107[k])
        return n

    n_pvd = ndiff(16 * 2048, 18 * 2048)
    check('PVD (LBA16..17) 差异 0', n_pvd == 0, '%d B' % n_pvd)
    from iso_tools import TAB_OFF, TAB_STEP                            # noqa: E402
    tabs = [(FC.MENU_LBA * 2048 + TAB_OFF,
             FC.MENU_LBA * 2048 + TAB_OFF + TAB_STEP * FC.img_entry_count(iso, FC.MENU_LBA)),
            (FC.GR_LBA * 2048 + TAB_OFF,
             FC.GR_LBA * 2048 + TAB_OFF + TAB_STEP * FC.img_entry_count(iso, FC.GR_LBA))]
    n_tab = sum(ndiff(x0, x1) for (x0, x1) in tabs)
    check('两个 IMG 条目表差异 0', n_tab == 0, '%d B' % n_tab)
    n551 = 0
    for idx in range(551, 566):
        e = iso.img_entry(FC.GR_LBA, idx)
        if 0 < e['stored'] < 0x7FFFFFFF:
            n551 += ndiff(e['iso_off'], e['iso_off'] + e['stored'])
    check('GR.IMG#551..#565 (制作组名单) 差异 0', n551 == 0, '%d B' % n551)
    n_font = ndiff(ft0, ft1)
    check('FONT.RES 槽差异 0', n_font == 0, '%d B (%d..%d)' % (n_font, ft0, ft1))
    # 字库像素容器 (允许改)
    n_px = ndiff(px0, px1)
    print('   (参考) 字库像素容器差异 %d B —— 这是搬字的结果, 允许' % n_px)
    iso.close()

    print('\n── 4. 紧凑布局 (charset 口径) ──')
    js = json.load(io.open(CS_CUR, encoding='utf-8'))
    used = sorted(set(tcslib.pair_slot(*v) for v in js['pair_of'].values()
                      if tcslib.LEAD_LO <= v[0] < tcslib.LEAD_HI))
    cap = tcslib.pair_capacity()
    free = sorted(set(range(cap)) - set(used))
    print('   在用 %d = slot %d..%d 连续=%s' % (len(used), used[0], used[-1],
                                                used == list(range(len(used)))))
    print('   空闲 %d = slot %d..%d 连续=%s' % (len(free), free[0], free[-1],
                                                free == list(range(len(used), cap))))
    check('在用 1175 = slot 0..1174 连续', used == list(range(1175)), '%d..%d' % (used[0], used[-1]))
    check('空闲 329 = slot 1175..1503 连续', free == list(range(1175, 1504)),
          '%d..%d' % (free[0], free[-1]))

    print('\n── 5. charset: 与 r56 紧凑后的映射一致 (只差 _font_compact 元信息) ──')
    j56 = json.load(io.open(CS_NEW_R56, encoding='utf-8'))
    same_pairs = (js['pair_of'] == j56['pair_of'])
    check('pair_of 与 charset_after_r56 逐条相同', same_pairs)
    diffkeys = [k for k in set(js) | set(j56)
                if k not in ('pair_of', '_font_compact') and js.get(k) != j56.get(k)]
    check('其它字段 (codes/markers/...) 逐字节不变', not diffkeys, str(diffkeys))
    fc = js.get('_font_compact') or {}
    print('   _font_compact: tool_version=%s used=%s moved_last=%s reencode=%s'
          % (fc.get('tool_version'), fc.get('used'), fc.get('moved_last'), fc.get('reencode')))
    print('\n' + '=' * 100)
    print('失败项: %d %s' % (len(FAIL), FAIL if FAIL else '—— 全绿'))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
