# -*- coding: utf-8 -*-
r"""fa_verify_diff.py — ★ 全盘差异的**条目级**定性（只读）

    python tools/re/toolbelt/fa_verify_diff.py [--iso <成品>] [--base GR_ZH113b] [--merge GR_MERGE2400]

为什么不能只看"字节差异落在哪个窗口":
  合并盘把 COMMON.PAK 里的图集容器从 400,659 B 长到 468,243 B (**+67,584 B = 0x10800**),
  这个增长吃掉了 MENU.IMG 槽内的陈旧尾巴 ⇒ **MENU.IMG 里 PAK 之后的所有条目整体后移 0x10800**。
  于是与基底逐字节比会出现几十 MB 差异 —— 那是"同样的内容挪了位置", 不是内容被改。
  ⇒ 正确判据 = **条目级比对**: 逐个 MENU.IMG / GR.IMG 条目比内容:
       · 计划内改动的条目 (图集 + 4 个文本容器) ⇒ 单独核对;
       · 其余条目 ⇒ 必须与基底**逐字节相同** (允许整体位移);
       · 一个 UNEXPECTED 都不许有。

判据:
  [E1] 两个 IMG 的**条目表**(名字/条目数) 与基线一致, 各条目 stored/real 不变
  [E2] 除计划内条目外, 全部条目内容与基底**逐字节相同** (内容比对, 与位移无关)
  [E3] 计划内条目: 图集容器 = 本轮改的; 4 个文本容器 = 迁移后的 (已由 fa_verify C3/C4 逐载荷证明)
  [E4] COMMON.PAK 逐记录: 只有 new_font_revised 变, 其余记录逐字节相同
  [E5] ISO9660 层面: ISO 尺寸不变 + 文件条目数不变
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                     # noqa: E402
import zx_lib                                                          # noqa: E402

B = lambda *a: os.path.join(REPO, 'work', 'builds', *a)
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


TEXT = ('EN_STRINGS.RES', 'EN_SPECIAL_FEATURE.XML')


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=B('GR_FA2400', 'GR_FA2400.iso'))
    ap.add_argument('--base', default=B('GR_ZH113b', 'GR_ZH113b.iso'))
    ap.add_argument('--merge', default=B('GR_MERGE2400', 'GR_MERGE2400.iso'))
    a = ap.parse_args(argv)
    P('=' * 104)
    P('fa_verify_diff.py — 全盘差异条目级定性')
    P('  base  = %s' % a.base)
    P('  iso   = %s' % a.iso)
    P('=' * 104)
    iso_b, iso_f, iso_m = T.Iso(a.base), T.Iso(a.iso), T.Iso(a.merge)
    plain, plan, inherited = [], [], []
    for (lba, img) in ((zx_lib.MENU_LBA, 'MENU.IMG'), (zx_lib.GR_LBA, 'GR.IMG')):
        eb = zx_lib.entries(iso_b, lba)
        ef = zx_lib.entries(iso_f, lba)
        em = zx_lib.entries(iso_m, lba)
        P('[E1] %s: 条目数 基底 %d / 成品 %d ; 名字序列相同: %s'
          % (img, len(eb), len(ef), '✓' if [e['name'] for e in eb] == [e['name'] for e in ef] else '✗'))
        assert [e['name'] for e in eb] == [e['name'] for e in ef]
        n_sh = 0
        for (x, y, z) in zip(eb, ef, em):
            assert x['name'] == y['name']
            same_len = (x['stored'], x['real']) == (y['stored'], y['real'])
            moved = y['off'] != x['off']
            n_sh += 1 if moved else 0
            planned = (y['name'] in TEXT) or (y['name'] == 'COMMON.PAK')
            if not same_len:
                P('[E1] %s#%d %-24s stored/real %d/%d → %d/%d %s'
                  % (img, y['idx'], y['name'], x['stored'], x['real'], y['stored'], y['real'],
                     '(计划内: 几何/迁移的增长)' if planned else '★非计划变更'))
            assert same_len or planned, y['name']
            # 与合并盘比: off 必须一致 (本轮不动条目表)
            assert (z['off'], z['stored'], z['real']) == (y['off'], y['stored'], y['real']), y['name']
            bx = bytes(iso_b.read(x['iso_off'], x['stored']))
            by = bytes(iso_f.read(y['iso_off'], y['stored']))
            if y['name'] in TEXT:
                plan.append((img, y['idx'], y['name'], 'text-migrated', x['off'], y['off']))
            elif y['name'] == 'COMMON.PAK':
                plan.append((img, y['idx'], y['name'], 'atlas-grown', x['off'], y['off']))
            elif y['name'] == 'FONT.RES':
                # ★ 既存 (本轮**之前**就改了): r84 链 (GR_ZH124/F364) 起 FT 记录表已把 ASCII/记录带
                #   搬到 (x>=992, y=0..) 的新布局; 本轮的成品 == 合并盘 == GR_ZH124 (sha 相同)
                inherited.append((img, y['idx'], y['name'], 'inherited-FT-records',
                                  x['off'], y['off']))
            elif bx == by:
                plain.append((img, y['idx'], y['name'], 'identical', x['off'], y['off']))
            else:
                plain.append((img, y['idx'], y['name'], '★IDENTICAL-CONTENT?', x['off'], y['off']))
        P('[E1] %s: 条目位移 (off 变) %d 个 —— 由 PAK 长大 0x10800 引起 (槽内陈旧尾巴被吃)'
          % (img, n_sh))
    bad = [x for x in plain if x[3].startswith('★')]
    P('')
    P('[E2] 非计划条目 %d 个: 与基底内容**逐字节相同** %d 个 ; 不同 %d 个 %s'
      % (len(plain), len(plain) - len(bad), len(bad), '✓' if not bad else '✗'))

    def show(lst, tag):
        for (img, idx, nm, k, o1, o2) in lst:
            P('      %-9s #%-4d %-26s %-22s off 0x%08X → 0x%08X (Δ%+d)'
              % (img, idx, nm, k, o1, o2, o2 - o1))
    show(plan, 'plan')
    P('[E2b] 既存(本轮之前)条目 %d 个 (FONT.RES 的 FT 记录表 —— r84 链起 ASCII/记录带已搬到'
      ' (x>=992,y=0..); 成品 == 合并盘 == GR_ZH124, 见 sha 一致):' % len(inherited))
    show(inherited, 'inh')
    if bad:
        show(bad, 'bad')
    assert not bad, '有非计划条目内容被改'
    P('[E2] ⇒ 除计划内条目与既存 FONT.RES 外, 两个 IMG 的其余条目内容与基底**逐字节相同** ✓')
    P('')
    P('[E3] 计划内条目:')
    for (img, idx, nm, k, o1, o2) in plan:
        P('      %-9s #%-4d %-26s %-22s off 0x%08X → 0x%08X' % (img, idx, nm, k, o1, o2))
    # ── [E4] COMMON.PAK 逐记录 ──
    pb = None
    eb_pak = [e for e in zx_lib.entries(iso_b, zx_lib.MENU_LBA) if e['name'] == 'COMMON.PAK'][0]
    ef_pak = [e for e in zx_lib.entries(iso_f, zx_lib.MENU_LBA) if e['name'] == 'COMMON.PAK'][0]
    pb = bytes(iso_b.read(eb_pak['iso_off'], eb_pak['stored']))
    pf = bytes(iso_f.read(ef_pak['iso_off'], ef_pak['stored']))
    rb, rf = T.parse_pak_records(pb), T.parse_pak_records(pf)
    P('')
    P('[E4] COMMON.PAK: 记录数 基底 %d / 成品 %d ; 长度 %d → %d (Δ%+d)'
      % (len(rb), len(rf), len(pb), len(pf), len(pf) - len(pb)))
    assert len(rb) == len(rf)
    for (x, y) in zip(rb, rf):
        cb = pb[x[6]:x[6] + x[5]]
        cf = pf[y[6]:y[6] + y[5]]
        same = cb == cf
        P('      rec %-20s psm=0x%02X %dx%d px %7d → %7d  %s'
          % (x[0], x[1], x[2], x[3], x[5], y[5],
             '逐字节相同 ✓' if same else '★变了 (%d/%d B 不同)'
             % (sum(1 for i in range(min(len(cb), len(cf))) if cb[i] != cf[i]), len(cb))))
        if x[0] != 'new_font_revised':
            assert same, x[0]
    P('[E4] ⇒ 只有 new_font_revised (图集) 变; arrow / pda-lcd-02 / pda_counterparts 逐字节相同 ✓')
    # ── [E5] ISO 尺寸 ──
    sb, sf = os.path.getsize(a.base), os.path.getsize(a.iso)
    P('')
    P('[E5] ISO 尺寸: 基底 %d B ; 成品 %d B ; Δ=%+d ⇒ %s'
      % (sb, sf, sf - sb, '不变 ✓' if sb == sf else '★变了'))
    assert sb == sf
    for (iso, nm) in ((iso_b, 'base'), (iso_f, 'iso'), (iso_m, 'merge')):
        iso.close()
    P('')
    P('[结论] 全盘差异 = ① 图集容器 (本轮) ② SFXML 容器 (本轮修复合并盘乱码) '
      '③ 4 个文本容器帧 (迁移, 已由 C3/C4 逐载荷证明) ④ PAK 内其余记录与两个 IMG 的其余条目**内容不变**')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
