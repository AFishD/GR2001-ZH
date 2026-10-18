# -*- coding: utf-8 -*-
r"""esfr_capacity_probe.py — ★ ES/FR 装不下的**精确账** (只读, 不写盘)

回答: "到底差多少? 有没有不改条目表也能塞进去的路?"

三条口径分别算:
  (1) **解压层**: 迁移每处 +1 B, 能吃的陈旧尾巴 = `blob − used_end`;
      ES/FR 的尾巴只有 8 B, 增长 28/29 B ⇒ 解压层**必须变长** 20/21 B。
  (2) **压缩层**: 若允许该容器的**最后一条 LZO 子流**声明长度 +Δ (即解压总长变长 Δ),
      重压后帧长 = ? 与 IMG 里"本条目 stored 到下一入口 off"的**扇区对齐余量**比 ——
      余量够 ⇒ 只需改本条目自己的 `stored`/`real` 两个字段 (不搬移任何数据);
      余量不够 ⇒ 必须搬移后续条目 (级联改 off) ⇒ 结构性改动。
  (3) `real` 字段: IMG 条目里 `real` 是不是"引擎真正用的解压长度"(见 [S7] 的 SF: real=116430
      而 blob=116486 —— 说明两者不必相等)。本条只登记观察, 不下结论。

只读; 产物写 temp/capacity/esfr_capacity_probe.json。
"""
import argparse
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                       # noqa: E402
import importlib.util                                                    # noqa: E402

_spec = importlib.util.spec_from_file_location(
    'mig', os.path.join(REPO, 'tools', 're', 'toolbelt', 'migrate_legacy.py'))
mig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mig)

TARGETS = (('ES_STRINGS.RES@MENU', T.MENU_LBA, 27),
           ('ES_STRINGS.RES@GR', T.GR_LBA, 904),
           ('FR_STRINGS.RES@MENU', T.MENU_LBA, 28),
           ('FR_STRINGS.RES@GR', T.GR_LBA, 907))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('--gate', default='0xBA')
    ap.add_argument('--out', default=os.path.join(HERE, 'capacity'))
    a = ap.parse_args(argv)
    gate = int(a.gate, 16)
    base_gate = 0xB1
    os.makedirs(a.out, exist_ok=True)
    cs = T.Charset()
    mp, extra = mig.build_map(cs, base_gate, gate, {}, False, (gate - T.LEAD_LO) * T.PAIR_STRIDE)
    assert not extra, extra
    iso = T.Iso(a.iso)
    rows = []
    for (tag, lba, idx) in TARGETS:
        e = iso.img_entry(lba, idx)
        raw = iso.read(e['iso_off'], e['stored'])
        subs = T.lzo_subs(raw)
        blob = b''.join(s[0] for s in subs)
        sizes = [s[2] for s in subs]
        raws = [bytes(raw[s[3]:s[3] + 8 + s[1]]) for s in subs]
        cont = dict(name='LANG', tag=tag, blob=blob, sizes=sizes, raws=raws)
        ranges, used, info = mig.payload_ranges(cont)
        cont['used_end'] = used
        old_pays = {r: blob[r[0]:r[1]] for r in ranges}
        stat = {'per_code': {}, 'per_char': {}, 'n': 0, 'ranges': len(ranges), 'changed': 0}
        edits = []
        for (s, en) in ranges:
            new, k = mig.migrate_payload(blob[s:en], mp, base_gate, gate, stat)
            stat['n'] += k
            if new != blob[s:en]:
                stat['changed'] += 1
                assert struct.unpack_from('<I', blob, s - 4)[0] == en - s
                edits.append((s - 4, en, struct.pack('<I', len(new)) + new))
        grown = T.splice(blob, edits)
        delta = len(grown) - len(blob)
        # 把全部增长放进**最后一条**子流 (与 EN 容器"吃尾巴"的位置一致)
        new_sizes = list(sizes[:-1]) + [sizes[-1] + delta]
        # 回环自检: 最后一条子流必须能装下 (用零补齐尾部)
        pad = b'\x00' * delta
        parts = []
        q = 0
        for k, S in enumerate(new_sizes[:-1]):
            parts.append(grown[q:q + S]); q += S
        parts.append(grown[q:] + pad)
        assert sum(len(p) for p in parts) == len(grown) + delta
        frame, n_rep, newlen = bytearray(), 0, 0
        for k, part in enumerate(parts):
            if part == subs[k][0]:
                frame += raws[k]
                continue
            cc = T.lzo_compress(part, level=7, use_m1=True, use_m4=True)
            back, err, _ = T.lzo1x_decompress(cc, out_size=len(part))
            assert err is None and back == part, 'sub %d 回环失败' % k
            frame += struct.pack('<II', len(cc), len(part)) + cc
            n_rep += 1
        floor = T.splice(blob, edits)          # 仅供长度参考
        rows.append(dict(tag=tag, lba=lba, idx=idx, stored=e['stored'], real=e['real'],
                         blob=len(blob), used=used, tail_free=len(blob) - used,
                         payload_n=stat['n'], changed=stat['changed'], delta=delta,
                         n_sub=len(subs), n_repack=n_rep,
                         frame_old=sum(8 + s[1] for s in subs), frame_new=len(frame),
                         stored_growth=len(frame) - e['stored'],
                         img_slot=e['stored'], iso_off=e['iso_off'],
                         pad_floor=len(floor)))
    # IMG 扇区对齐余量 (按 **off 顺序**找真正的下一个条目)
    for r in rows:
        nxt = None
        for i in range(2000):
            try:
                x = iso.img_entry(r['lba'], i)
            except Exception:                                            # noqa: BLE001
                break
            if not x['name'] or x['off'] == 0:
                break
            if x['off'] > r['iso_off'] - r['lba'] * 2048 and \
                    (nxt is None or x['off'] < nxt['off']):
                nxt = x
        r['next_off'] = nxt['off'] if nxt else None
        r['next_name'] = nxt['name'] if nxt else None
        r['sector_pad'] = (nxt['off'] - (r['iso_off'] - r['lba'] * 2048) - r['stored']
                           if nxt else None)
        r['fits_decomp'] = bool(r['payload_n'] <= r['tail_free'])
        r['fits_frame_in_pad'] = bool(r['sector_pad'] is not None
                                      and r['stored_growth'] <= r['sector_pad'])
    iso.close()

    print('=' * 104)
    print('ES/FR 容量精确账 (只读; 闸门 0x%02X)' % gate)
    print('=' * 104)
    print('  %-20s %7s %7s %7s %6s %7s %7s %8s %8s %8s %9s'
          % ('容器', '解压B', 'used', '尾巴B', '载荷', 'Δ解压', 'Δ压缩', '帧旧', '帧新', '扇区余量',
             '压缩层可塞'))
    for r in rows:
        print('  %-20s %7d %7d %7d %6d %+7d %+7d %8d %8d %8s %9s'
              % (r['tag'], r['blob'], r['used'], r['tail_free'], r['payload_n'], r['delta'],
                 r['stored_growth'], r['frame_old'], r['frame_new'], r['sector_pad'],
                 '✓' if r['fits_frame_in_pad'] else '✗'))
    print()
    for r in rows:
        print('  --- %s ---' % r['tag'])
        print('      解压层: 增长 %+d B vs 陈旧尾巴 %d B ⇒ %s'
              % (r['delta'], r['tail_free'],
                 '装得下' if r['fits_decomp'] else '★ 差 %d B (解压总长必须变长)'
                 % (r['delta'] - r['tail_free'])))
        print('      压缩层: 重压后帧 %d → %d B (%+d) ; IMG 里本条目到下一入口 (%s) 的扇区余量 = %s B'
              % (r['frame_old'], r['frame_new'], r['stored_growth'], r['next_name'],
                 r['sector_pad']))
        print('      ⇒ 若 LEAD 批准"只改本条目 stored/real、不搬移数据": %s'
              % ('**可行** (压缩增长塞得进扇区余量)' if r['fits_frame_in_pad'] else
                 '**不可行** (压缩增长 %+d > 余量 %d ⇒ 必须搬移后续条目 = 级联改 off)'
                 % (r['stored_growth'], r['sector_pad'])))
    json.dump(dict(iso=os.path.abspath(a.iso), gate=gate, rows=rows),
              io.open(os.path.join(a.out, 'esfr_capacity_probe.json'), 'w', encoding='utf-8',
                      newline='\n'), ensure_ascii=False, indent=1)
    print()
    print('[out] %s' % os.path.join(a.out, 'esfr_capacity_probe.json'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
