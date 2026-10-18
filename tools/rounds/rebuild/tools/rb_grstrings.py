# -*- coding: utf-8 -*-
r"""rb_grstrings.py -- 把 MENU.IMG 侧 EN_STRINGS.RES 的「EN→K2 中文」逐条对应关系，
搬到 GR.IMG 侧同名容器上（两份容器装的是**同一批逻辑字符串**，已由 8-gram 重合度
99.7% + 迁移统计逐项相同实证）。

只读输入：原盘 ISO、K2 拼装盘。输出：GR 侧新容器 slot 字节 + 报告（供写盘步骤使用）。

用法:
  python rb_grstrings.py --dry                       # 只分析 + 报告
  python rb_grstrings.py --write <out.iso>           # 在拼装盘副本上写入 GR#902 新容器
"""
import argparse
import io
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402
import hashlib                                                        # noqa: E402

LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load_cont(iso, lba, name):
    e = [x for x in zx_lib.entries(iso, lba) if x['name'] == name][0]
    slot = bytes(iso.read(e['iso_off'], e['stored']))
    subs = T.lzo_subs(slot)
    blob = b''.join(s[0] for s in subs)
    return dict(entry=e, slot=slot, subs=subs, blob=blob)


def repack(cont, new_blob):
    """照搬 migrate_legacy.py::repack 的口径（未变子流照搬原压缩字节）。"""
    assert len(new_blob) == len(cont['blob'])
    frame, q, n_rep = bytearray(), 0, 0
    for k, s in enumerate(cont['subs']):
        orig, comp, real, sslot = s[0], s[1], s[2], s[3]
        part = new_blob[q:q + real]
        q += real
        if part == orig:
            frame += cont['slot'][sslot:sslot + 8 + comp]
            continue
        cc = T.lzo_compress(part, level=7, use_m1=True, use_m4=True)
        back, err, _ = T.lzo1x_decompress(cc, out_size=real)
        assert err is None and back == part, '子流 %d 回环失败' % k
        frame += struct.pack('<II', len(cc), real) + cc
        n_rep += 1
    assert q == len(new_blob)
    return bytes(frame), q, n_rep


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--orig', default=os.path.join(
        REPO, 'third_party', 'orig', 'ps2', "Tom Clancy's Ghost Recon (USA).iso"))
    ap.add_argument('--probe', default=os.path.join(REPO, 'work', 'builds', 'GR_REBUILD',
                                                    '_probe_k2only.iso'))
    ap.add_argument('--write', default=None)
    ap.add_argument('--report', default=None)
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args(argv)

    o = T.Iso(a.orig)
    k = T.Iso(a.probe)
    m_en = load_cont(o, zx_lib.MENU_LBA, 'EN_STRINGS.RES')
    m_k2 = load_cont(k, zx_lib.MENU_LBA, 'EN_STRINGS.RES')
    g_en = load_cont(o, zx_lib.GR_LBA, 'EN_STRINGS.RES')
    for t, c in (('MENU_EN', m_en), ('MENU_K2', m_k2), ('GR_EN', g_en)):
        P('%-8s idx=%-5d off=0x%X stored=%-7d real=%-7d 子流=%-2d 展开=%-7d sha=%s' %
          (t, c['entry']['idx'], c['entry']['off'], c['entry']['stored'],
           c['entry']['real'], len(c['subs']), len(c['blob']), sha(c['blob'])[:16]))

    eM, uM = T.parse_lang(m_en['blob'])
    eK, uK = T.parse_lang(m_k2['blob'])
    eG, uG = T.parse_lang(g_en['blob'])
    P('')
    P('条目数: MENU_EN=%d MENU_K2=%d GR_EN=%d' % (len(eM), len(eK), len(eG)))
    P('used_end: MENU_EN=0x%X MENU_K2=0x%X GR_EN=0x%X ; blob=%d/%d/%d' %
      (uM, uK, uG, len(m_en['blob']), len(m_k2['blob']), len(g_en['blob'])))
    assert len(eM) == len(eK) == len(eG), '条目数不一致'

    # (g,i) 序列一致性
    seq_m = [(x.g, x.i) for x in eM]
    seq_k = [(x.g, x.i) for x in eK]
    seq_g = [(x.g, x.i) for x in eG]
    P('[seq] MENU_EN==MENU_K2 %s ; MENU_EN==GR_EN %s' %
      (seq_m == seq_k, seq_m == seq_g))
    assert seq_m == seq_k, '(g,i) 序列 MENU_EN vs MENU_K2 不一致'

    same_en = sum(1 for x, y in zip(eM, eG) if x.data == y.data)
    P('[cmp] MENU_EN 与 GR_EN 逐条载荷相同: %d / %d (%.1f%%)' %
      (same_en, len(eM), 100.0 * same_en / len(eM)))
    diffs = [(i, eM[i], eG[i]) for i in range(len(eM)) if eM[i].data != eG[i].data]
    P('[cmp] 不同 %d 条' % len(diffs))
    for i, x, y in diffs[:30]:
        P('      #%-5d G%d.I%-4d MENU_EN %r  vs  GR_EN %r' %
          (i, x.g, x.i, x.data[:40], y.data[:40]))
    if len(diffs) > 30:
        P('      ... 另 %d 条' % (len(diffs) - 30))

    # 换掉多少条
    changed = sum(1 for i in range(len(eM)) if eK[i].data != eM[i].data)
    P('[mig] MENU_EN→MENU_K2 载荷不同 %d / %d 条' % (changed, len(eM)))

    # ── 构造 GR 新 blob：逐条用 MENU_K2 的载荷替换 ──
    edits = []
    n_sub = 0
    for i in range(len(eG)):
        span = T.lang_entry_span(g_en['blob'], eG[i])
        newdata = eK[i].data
        attr = g_en['blob'][eG[i].attr_off:eG[i].attr_off + 2]
        newrec = struct.pack('<I', len(newdata)) + newdata + attr
        if newrec != g_en['blob'][span[0]:span[1]]:
            n_sub += 1
        edits.append((span[0], span[1], newrec))
    spliced = T.splice(g_en['blob'], edits)
    growth = len(spliced) - len(g_en['blob'])
    P('')
    P('[sub] 替换 %d 条 ; 新 blob %d B (Δ%+d) ; used_end 0x%X ⇒ 尾巴可用 %d B' %
      (n_sub, len(spliced), growth, uG, len(g_en['blob']) - uG))

    # ── [S2] 反向重建自检（在填充/裁剪**之前**做；口径同 migrate_legacy.rebuild_container）──
    shift, undo = 0, []
    for (s0, s1, nb) in sorted(edits, key=lambda x: x[0]):
        undo.append((s0 + shift, s0 + shift + len(nb), g_en['blob'][s0:s1]))
        shift += len(nb) - (s1 - s0)
    assert T.splice(spliced, undo) == g_en['blob'], '反向重建失败'
    P('[S2] 反向重建 == 源 GR_EN blob ✓')

    if growth > 0:
        assert growth <= len(g_en['blob']) - uG, 'GR 容器装不下: 增长 %d > 尾巴 %d' % (
            growth, len(g_en['blob']) - uG)
        new_blob = spliced[:len(g_en['blob'])]
        trimmed = spliced[len(g_en['blob']):]
        P('[tail] 裁掉 %d B（非零 %d）' % (len(trimmed), sum(1 for x in trimmed if x)))
    elif growth < 0:
        new_blob = spliced + b'\x00' * (-growth)
        P('[tail] 补 %d B 零（口径同 migrate_legacy：增长吃尾巴 / 缩短补零）' % (-growth))
    else:
        new_blob = spliced
    assert len(new_blob) == len(g_en['blob'])
    nG, uG2 = T.parse_lang(new_blob)
    P('[S4] 新 blob 可解析: 条目 %d ; used_end 0x%X (=%d) ; blob %d' %
      (len(nG), uG2, uG2, len(new_blob)))
    assert len(nG) == len(eG)
    assert [(x.g, x.i) for x in nG] == seq_g
    # 逐条 == MENU_K2 载荷
    bad = [i for i in range(len(nG)) if nG[i].data != eK[i].data]
    P('[S5] 逐条载荷 == MENU_K2 载荷: 不同 %d 条' % len(bad))
    assert not bad, bad[:5]

    frame, tot, nrep = repack(g_en, new_blob)
    P('[pack] 重压 %d 子流 ; 帧 %d B (原 %d) ; 槽 %d B ⇒ 余 %d B' %
      (nrep, len(frame), len(g_en['slot']), g_en['entry']['stored'],
       g_en['entry']['stored'] - len(frame)))
    assert len(frame) <= g_en['entry']['stored'], '重压后超出槽'

    # 回读自检
    subs2 = T.lzo_subs(frame + b'\x00' * (g_en['entry']['stored'] - len(frame)))
    blob2 = b''.join(s[0] for s in subs2)
    assert blob2 == new_blob, '回读不一致'
    P('[S7] 回读 blob %d B == 新 blob ✓' % len(blob2))

    # 逐字符一致性（用 charset 的 pair_of/codes 解码两侧）
    try:
        cs = T.Charset(T.CHARSET)
        pair_dec = {tuple(p): ch for ch, p in cs.pair_of.items()} if hasattr(
            cs, 'pair_of') else {}
    except Exception as ex:                                          # noqa: BLE001
        P('[warn] charset 载入失败: %s' % ex)

    rep = dict(menu_en_sha=sha(m_en['blob']), menu_k2_sha=sha(m_k2['blob']),
               gr_en_sha=sha(g_en['blob']), gr_new_sha=sha(new_blob),
               entries=len(eM), same_en=same_en, mig_changed=changed,
               n_sub=n_sub, growth=growth, frame=len(frame),
               slot=g_en['entry']['stored'], n_repack=nrep,
               gr_entry=dict(idx=g_en['entry']['idx'], off=g_en['entry']['off'],
                             stored=g_en['entry']['stored'], real=g_en['entry']['real'],
                             iso_off=g_en['entry']['iso_off']))
    if not a.dry and a.write:
        import shutil
        if os.path.exists(a.write):
            raise SystemExit('输出已存在: %s' % a.write)
        os.makedirs(os.path.dirname(os.path.abspath(a.write)), exist_ok=True)
        shutil.copyfile(a.probe, a.write)
        with open(a.write, 'r+b') as f:
            f.seek(g_en['entry']['iso_off'])
            f.write(frame)
            f.write(b'\x00' * (g_en['entry']['stored'] - len(frame)))
        P('[out] %s 写入 GR#%d @0x%X (%d B + %d B 零填充)' %
          (a.write, g_en['entry']['idx'], g_en['entry']['iso_off'], len(frame),
           g_en['entry']['stored'] - len(frame)))
        # 写后回读
        v = T.Iso(a.write)
        e2 = [x for x in zx_lib.entries(v, zx_lib.GR_LBA)
              if x['name'] == 'EN_STRINGS.RES'][0]
        slot2 = bytes(v.read(e2['iso_off'], e2['stored']))
        b2 = b''.join(s[0] for s in T.lzo_subs(slot2))
        P('[R ] 写后回读 blob %d B ; == 新 blob %s' % (len(b2), b2 == new_blob))
        v.close()

    o.close()
    k.close()
    rp = a.report or os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', 'temp',
                                  'grstrings.json')
    os.makedirs(os.path.dirname(rp), exist_ok=True)
    import json
    json.dump(rep, open(rp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with io.open(rp.replace('.json', '.log'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(LOG) + '\n')
    P('[report] %s' % rp)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
