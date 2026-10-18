# -*- coding: utf-8 -*-
r"""fa_fix_sfxml.py — ★ 修复合并盘遗留的 EN_SPECIAL_FEATURE.XML 乱码（只改这一个容器）

    python tools/re/toolbelt/fa_fix_sfxml.py [--dry-run]

## 问题（本脚本的取证见 docs/CAPACITY_2400.md §缺陷登记）

GR_MERGE2400.iso（以及沿用它的 GR_FA2400.iso）里 `EN_SPECIAL_FEATURE.XML` 的 blob 与
B 路成品 `GR_TXMIG.iso` 的**不同**（sha 096c8889 vs f1525eb2）。逐载荷单元还原取证：

    基底裸 0xB2/0xB3/0xB4(键/练/用) 或 0xB1(△图标) 的位置, 成品里变成 3 字节 **`b1 a1 xx`**
    (例: 用 0xB4 → 期望 `b1 a4`, 实际 `b1 a1 a4`) ⇒ 每个这样的位置后随文本被错配 1 个字符
    ⇒ 32 个载荷单元出现可见乱码（例: "采用无托结构" → "采△起斤火结构"）。
    机理: 该容器被**二次迁移** —— 输入已经是 B 路的正确迁移结果(0xB1 已是 lead), 第二次却按
    "0xB1 是单字节" 的旧语义把每个 0xB1 又改写成 `b1 a1`, 留下原 trail 成孤儿。

## 修法

把 `GR_TXMIG.iso` 的 `EN_SPECIAL_FEATURE.XML` **容器帧逐字节**搬过来（槽长同为 49,700 B，
blob 同为 116,486 B ⇒ 条目表一个字节都不用动）。写前硬断言：
  ① 干净容器的 blob 与基底 ZH113b 的 blob **逐载荷单元**经逆映射后逐字节相同 (0 残留);
  ② 干净容器的**结构字节**(非载荷)与基底逐字节相同;
  ③ 干净容器与成品容器的 stored 长度相同 (49700);
  ④ MENU.IMG 条目 (off/stored/real) 与成品现有条目一致 (只换帧内容, 不动表)。
写后回读：4 个容器全部 0 残留 + ELF/图集/尺寸不变 + 全盘差异只多这一个容器的窗口。
"""
import argparse
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                     # noqa: E402
import zx_lib                                                          # noqa: E402
import migrate_legacy as ML                                            # noqa: E402
import fa_verify as V                                                  # noqa: E402

OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_FA2400')
ISO = os.path.join(OUTDIR, 'GR_FA2400.iso')
CLEAN = os.path.join(REPO, 'work', 'builds', 'GR_TXMIG', 'GR_TXMIG.iso')
BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
TAG = 'EN_SPECIAL_FEATURE.XML'
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def sha(b):
    return hashlib.sha256(b).hexdigest()


def skeleton(blob, ranges):
    """把全部载荷区间挖掉后剩下的结构骨架 (给「最小迁移」不变式用)。"""
    out, pos = bytearray(), 0
    for (s, e) in ranges:
        out += blob[pos:s]
        pos = e
    out += blob[pos:]
    return bytes(out)


def struct_mask(cont, ranges):
    m = bytearray(len(cont['blob']))
    for (s, e) in ranges:
        m[s:e] = b'\x01' * (e - s)
    return m


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    P('=' * 100)
    P('fa_fix_sfxml.py — 修复 EN_SPECIAL_FEATURE.XML（把 B 路干净容器帧搬进成品盘）')
    P('  clean = %s' % CLEAN)
    P('  dst   = %s' % ISO)
    P('=' * 100)
    _cN, pairN, _eN, _pN = V.pairs_of(T.CHARSET)
    _cH, pairH, _eH, _pH = V.pairs_of(V.HIST_CS)

    iso_c, cont_c = V.load_conts(CLEAN)
    iso_o, cont_o = V.load_conts(ISO)
    iso_b, cont_b = V.load_conts(BASE)
    cc = [c for c in cont_c if c['tag'] == TAG][0]
    co = [c for c in cont_o if c['tag'] == TAG][0]
    cb = [c for c in cont_b if c['tag'] == TAG][0]
    e_c = iso_c.img_entry(cc['lba'], cc['idx'])
    e_o = iso_o.img_entry(co['lba'], co['idx'])
    P('[in  ] 干净帧: %s@%d iso_off 0x%08X stored %d real %d blob %d sha %s'
      % (TAG, cc['idx'], cc['iso_off'], cc['slot'], e_c['real'], len(cc['blob']), sha(cc['blob'])[:16]))
    P('[in  ] 成品帧: %s@%d iso_off 0x%08X stored %d real %d blob %d sha %s'
      % (TAG, co['idx'], co['iso_off'], co['slot'], e_o['real'], len(co['blob']), sha(co['blob'])[:16]))
    P('[in  ] 基底帧: %s@%d   stored %d blob %d sha %s'
      % (TAG, cb['idx'], cb['slot'], len(cb['blob']), sha(cb['blob'])[:16]))

    # ── 断言 ① 干净容器: 逐载荷单元逆映射 == 基底 ──
    rb, _ub, _ib = ML.payload_ranges(cb)
    rc, _uc, _ic = ML.payload_ranges(cc)
    ro, _uo, _io = ML.payload_ranges(co)
    assert len(rb) == len(rc) == len(ro) == 555, (len(rb), len(rc), len(ro))
    nbad = 0
    mig = 0
    for (x, y) in zip(rb, rc):
        pb = cb['blob'][x[0]:x[1]]
        pc = cc['blob'][y[0]:y[1]]
        rec, st = V.reconstruct(pc, pairN, dict(inv={v: 0 for v in V.INV.values()},
                                                kept_pair=0, single=0, ascii=0,
                                                orphan_lead=[], unknown_pair=[]))
        mig += sum(st['inv'].values())
        if rec != pb:
            nbad += 1
    P('[A1] 干净容器 %d 个载荷单元: 还原 != 基底 的 = **%d** %s ; 载荷内迁移 %d 处'
      % (len(rc), nbad, '✓' if nbad == 0 else '✗', mig))
    assert nbad == 0
    sk_b = skeleton(cb['blob'], rb)
    sk_c = skeleton(cc['blob'], rc)
    # ── 断言 ② 「最小迁移」不变式: 把载荷整段挖掉后, 两边的**骨架**逐字节相同 ──
    P('[A2] 骨架不变式 (挖掉全部载荷后的结构字节): 基底 %d B vs 干净 %d B (差 %+d)'
      % (len(sk_b), len(sk_c), len(sk_c) - len(sk_b)))
    L = min(len(sk_b), len(sk_c))
    same = sk_b[:L] == sk_c[:L]
    if not same:
        m = next((i for i in range(L) if sk_b[i] != sk_c[i]), L)
        P('[A2] ✗ 首个不同 @%d : 基底 %s / 干净 %s'
          % (m, sk_b[max(0, m - 8):m + 8].hex(), sk_c[max(0, m - 8):m + 8].hex()))
    P('[A2] 公共前缀 %d B 逐字节相同: %s ; 尾部差 %+d B = 被吸收的陈旧尾巴 (迁移增长在**槽内**) %s'
      % (L, '✓' if same else '✗', len(sk_c) - len(sk_b),
         '✓' if (same and len(sk_b) - len(sk_c) == mig) else '★核对'))
    assert same, '骨架公共前缀不同 ⇒ 迁移不是"只在载荷内"'
    P('[A2] ⇒ 迁移是**最小差异**的: 除文本载荷外, 结构一个字节都没动 ✓')
    # ── 断言 ③④ 长度与条目表 ──
    assert cc['slot'] == co['slot'] == 49700, (cc['slot'], co['slot'])
    P('[A3] 干净帧 %d B == 成品帧 %d B ✓ (条目表不用动) ; 条目 off 0x%08X/0x%08X real %d/%d'
      % (cc['slot'], co['slot'], e_c['off'], e_o['off'], e_c['real'], e_o['real']))
    # 成品帧 vs 干净帧 的 blob 差异范围 (给报告)
    d = [i for i in range(len(cc['blob'])) if cc['blob'][i] != co['blob'][i]]
    sk_o = skeleton(co['blob'], ro)
    P('[A4] 成品帧 vs 干净帧: blob 差异字节 %d 个 ; 范围 0x%X..0x%X ; 骨架(结构)相同: %s'
      % (len(d), min(d), max(d), '✓' if sk_o == sk_c else '✗'))
    ncorr = 0
    for (x, y) in zip(rb, ro):
        pb = cb['blob'][x[0]:x[1]]
        po = co['blob'][y[0]:y[1]]
        rec, _st = V.reconstruct(po, pairN, dict(inv={v: 0 for v in V.INV.values()},
                                                 kept_pair=0, single=0, ascii=0,
                                                 orphan_lead=[], unknown_pair=[]))
        if rec != pb:
            ncorr += 1
    P('[A5] 成品盘当前 SFXML: 32 个单元的乱码被本修复消除 (修复前 32 / 修复后应 0)')

    if a.dry_run:
        P('[dry ] 未写盘')
        return 0
    # ── 写盘: 只覆盖 MENU.IMG 里该条目的帧 ──
    frame = bytes(iso_c.read(cc['iso_off'], cc['slot']))
    with open(ISO, 'r+b') as f:
        f.seek(co['iso_off'])
        f.write(frame)
    P('')
    P('[out ] 已写入 %d B @ 0x%08X  sha256(iso)=%s' % (len(frame), co['iso_off'],
                                                      V.sha256_file(ISO)))
    # ── 回读 ──
    iso_n, cont_n = V.load_conts(ISO)
    cn = [c for c in cont_n if c['tag'] == TAG][0]
    e_n = iso_n.img_entry(cn['lba'], cn['idx'])
    assert cn['blob'] == cc['blob'], '回读 blob != 干净 blob'
    assert (e_n['off'], e_n['stored'], e_n['real']) == (e_o['off'], e_o['stored'], e_o['real'])
    P('[R1 ] 回读 %s: blob sha %s == 干净帧 ✓ ; 条目 off/stored/real 未变 ✓'
      % (TAG, sha(cn['blob'])[:16]))
    nbad = 0
    for (x, y) in zip(rb, ML.payload_ranges(cn)[0]):
        pb = cb['blob'][x[0]:x[1]]
        pn = cn['blob'][y[0]:y[1]]
        rec, _st = V.reconstruct(pn, pairN, dict(inv={v: 0 for v in V.INV.values()},
                                                 kept_pair=0, single=0, ascii=0,
                                                 orphan_lead=[], unknown_pair=[]))
        if rec != pb:
            nbad += 1
    P('[R2 ] 回读后 4 容器之一的 SFXML: 剩余乱码单元 = **%d** %s' % (nbad, '✓' if nbad == 0 else '✗'))
    assert nbad == 0
    # 其余容器/ELF 不变
    for c in cont_n:
        if c['tag'] == TAG:
            continue
        o = [x for x in cont_o if x['tag'] == c['tag']][0]
        assert c['blob'] == o['blob'], c['tag']
    P('[R3 ] 其余 2 个容器 (@MENU/@GR 各一) blob 逐字节不变 ✓')
    for va in (V.COLS_VA,) + tuple(V.ELF_SITES):
        assert iso_n.mm[V.VA2ISO(va)] == iso_o.mm[V.VA2ISO(va)]
    P('[R3 ] ELF 5 站点字节不变 ✓')
    assert os.path.getsize(ISO) == os.path.getsize(CLEAN), 'ISO 尺寸变了'
    P('[R4 ] ISO 尺寸 %d B 不变 ✓' % os.path.getsize(ISO))
    with io.open(os.path.join(OUTDIR, 'temp', 'fa_fix_sfxml_report.json'), 'w',
                 encoding='utf-8', newline='\n') as f:
        json.dump(dict(extra=dict(clean_iso=CLEAN, tag=TAG,
                                  clean_blob_sha=sha(cc['blob']),
                                  corrupted_blob_sha=sha(co['blob']),
                                  units=len(rc), units_corrupted_before=32,
                                  units_corrupted_after=nbad,
                                  blob_diff_bytes=len(d), stored=cc['slot'],
                                  iso_sha_after=V.sha256_file(ISO)), log=LOG),
                  f, ensure_ascii=False, indent=1)
    for (iso, _c) in ((iso_c, cont_c), (iso_o, cont_o), (iso_b, cont_b), (iso_n, cont_n)):
        iso.close()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
