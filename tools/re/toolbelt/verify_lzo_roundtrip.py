# -*- coding: utf-8 -*-
r"""verify_lzo_roundtrip.py — FONT.RES 的「解压 → 原样重压」是否字节稳定

为什么要做: 方案必须改 FONT.RES 的两条活带记录 ⇒ 必须重新 LZO 压缩。
  · 若原样重压 == 原字节 ⇒ 压缩器是确定性的，改动引入的差异可控 ✓
  · 若不等于      ⇒ 即使逻辑不变，stored 长度也会变 ⇒ 条目重排是必然步骤（不是偶发）✓
另外核对: lzo_subs 解出的总长是否 == 条目记录的 real（FONT.RES = 7222）✓
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

MENU_LBA = 776286
iso = tcslib.Iso(ISO)

for idx in (4,):   # FONT.RES = MENU #4
    e = iso.img_entry(MENU_LBA, idx)
    print('条目 #%d %s  stored=%d real=%d off=0x%X' % (idx, e['name'], e['stored'], e['real'], e['off']))
    raw = iso.read(e['iso_off'], e['stored'])
    print('  读出 %d B ; 头 32 字节: %s' % (len(raw), raw[:32].hex(' ')))

    subs = tcslib.lzo_subs(raw)
    tot = sum(len(d) for (d, cl, rl, ho) in subs)
    print('  lzo_subs: %d 个子流 ; 解出总长 %d (期望 real=%d) ⇒ %s'
          % (len(subs), tot, e['real'], '一致 ✓' if tot == e['real'] else '不一致 ✗'))
    for i, (d, cl, rl, ho) in enumerate(subs[:12]):
        print('     #%-2d hdr@0x%-5X comp=%-7d real=%-7d' % (i, ho, cl, rl))

    # 原样重压
    chunks = [d for (d, cl, rl, ho) in subs]
    pairs = [(d, rl) for (d, cl, rl, ho) in subs]      # ★ lzo_pack 需要 (chunk, out_size) 对
    try:
        repacked = tcslib.lzo_pack(pairs)
    except Exception as ex:
        print('  ✗ lzo_pack 抛异常: %s' % ex)
        raise
    print('  重压后 %d B (原始 %d B) ⇒ 长度%s' % (len(repacked), len(raw),
          '相同' if len(repacked) == len(raw) else '**不同** Δ=%+d' % (len(repacked) - len(raw))))
    if len(repacked) == len(raw):
        same = repacked == raw
        print('  ★ 字节级: %s' % ('**完全相同 ⇒ 压缩器确定性 ✓**' if same else '**内容不同 ⇒ 压缩器非确定性 ✗**'))
        if not same:
            diff = [i for i in range(len(raw)) if raw[i] != repacked[i]]
            print('     差异字节 %d 个，前 8 处: %s' % (len(diff), ['0x%X' % d for d in diff[:8]]))
    else:
        # 回读自检
        back = b''.join(tcslib.lzo_subs(repacked)[i][0] for i in range(len(subs)))
        print('  ★ 回读校验: 解出 %d B ⇒ %s' % (len(back), '与原内容一致 ✓（长度不同但内容等价）' if back == b''.join(chunks) else '内容不一致 ✗'))
    print()
    print('  ⇒ 结论: 改记录后 **无论压缩器是否确定性，都必须按新 stored 重排后续条目** '
          if len(repacked) != len(raw) else
          '  ⇒ 结论: 压缩器长度稳定，但内容是否逐字节相同见上（若非确定性 ⇒ 重排仍必须做）')
iso.close()
