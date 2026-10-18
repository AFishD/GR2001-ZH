# -*- coding: utf-8 -*-
r"""fa_charset.py — 任务 B: charset 落盘 (pair_of 扩到 2,350 槽空间)

    python tools/re/toolbelt/fa_charset.py [--dry-run]

改动（**只这 3 处**, 其余逐字节不动 —— 用「文本级最小编辑」而不是整体重写）:
  ① codes: 删除 击(0xB6) / 小(0xB7) / 时(0xB8) / 按(0xB9) 这 4 个单字节码
     —— 抬闸门到 0xBA 后 0xB6..0xB9 落在**前导区间**, 不再是合法单字节码 (LEAD_CAPACITY_2400 §8)
  ② pair_of: 追加 5 条 —— 按 0xB9FA / 时 0xB9FB / 小 0xB9FC / 击 0xB9FD / ✕ 0xB9FE
     ⇒ slot = (lead-0xA1)*94 + (trail-0xA1) = 2345 / 2346 / 2347 / 2348 / 2349
  ③ 追加 metadata 块 `_expand_fa2400` (与本文件既有的 _expand_zh113/zh121/r83/f364 同款)

备份: work/builds/GR_FA2400/charset_before_fa2400.json (改前)

自查:
  [C1] 0..1871 的既有 1872 条 pair_of 条目**逐字段相同**
  [C2] codes 只少这 4 个键, 其余 103 个键值不变
  [C3] pair_of 新条目恰好 5 条, slot 恰为 2345..2349, 且 1872..2344 仍为空
  [C4] 新 5 条的 pair 在 **gate 0xBA 语义**下 编码/解码互逆
  [C5] 新 5 个槽在 GR_FA2400.iso 图集里**有墨**
  [C6] 全表在 gate 0xBA 下 encode(decode(x)) == x (逐条)
"""
import argparse
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                     # noqa: E402
import fa_recon as R                                                   # noqa: E402
import fa_build as FB                                                  # noqa: E402

CS = T.CHARSET
BK = os.path.join(REPO, 'work', 'builds', 'GR_FA2400', 'charset_before_fa2400.json')
NEW_ISO = os.path.join(REPO, 'work', 'builds', 'GR_FA2400', 'GR_FA2400.iso')
NEW_PAIRS = [('\u6309', 0xB9, 0xFA), ('\u65f6', 0xB9, 0xFB), ('\u5c0f', 0xB9, 0xFC),
             ('\u51fb', 0xB9, 0xFD), ('\u2715', 0xB9, 0xFE)]
DROP_CODES = [('击', 0xB6), ('小', 0xB7), ('时', 0xB8), ('按', 0xB9)]
LEAD_LO, LEAD_HI = 0xA1, 0xBA          # gate 0xBA 的 lead 区间 [0xA1, 0xBA)
GATE = 0xBA
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def slot_of(pr):
    return (pr[0] - 0xA1) * 94 + (pr[1] - 0xA1)


def ent_text(ch, b1, b2):
    """与 json.dump(indent=1) 完全一致的条目排版 (实测原文件排版)。"""
    return '  %s: [\n   %d,\n   %d\n  ],\n' % (json.dumps(ch, ensure_ascii=False), b1, b2)


def decode_ba(raw, codes, pair_of):
    """gate 0xBA 语义解码 (lead ∈ [0xA1,0xBA)): 返回 (text, 每字符起始偏移)。"""
    out, mp, i, n = [], [], 0, len(raw)
    while i < n:
        v = raw[i]
        if v < 0x80:
            out.append(chr(v)); mp.append(i); i += 1
        elif LEAD_LO <= v < LEAD_HI and i + 1 < n and (v, raw[i + 1]) in pair_of:
            out.append(pair_of[(v, raw[i + 1])]); mp.append(i); i += 2
        elif v in codes:
            out.append(codes[v]); mp.append(i); i += 1
        else:
            out.append(chr(0xE000 + v)); mp.append(i); i += 1
    return ''.join(out), mp


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    raw = open(CS, 'rb').read()
    P('=' * 100)
    P('fa_charset.py  任务 B: charset → pair_of 扩到 2,350 槽空间')
    P('  charset = %s (%d B)' % (CS, len(raw)))
    P('  backup  = %s' % BK)
    P('=' * 100)
    d0 = json.loads(raw.decode('utf-8'))
    P('[before] codes %d 条 ; pair_of %d 条 ; mode=%s' % (len(d0['codes']), len(d0['pair_of']),
                                                         d0['mode']))
    assert len(d0['pair_of']) == 1872 and len(d0['codes']) == 107
    slots0 = sorted(slot_of(v) for v in d0['pair_of'].values())
    assert slots0 == list(range(1872)), '既有 pair_of 不是 0..1871 无缺口'
    for ch, b in DROP_CODES:
        assert d0['codes'].get(ch) == b, (ch, b, d0['codes'].get(ch))
        assert ch not in d0['pair_of']

    # ── 文本级最小编辑 ──
    txt = raw.decode('utf-8')
    # ① 删 4 个单字节码 (它们在 codes 块开头且连续)
    drop_txt = ''.join('  %s: %d,\n' % (json.dumps(ch, ensure_ascii=False), b)
                       for ch, b in DROP_CODES)
    assert txt.count(drop_txt) == 1, '待删 4 行不是唯一出现 (count=%d)' % txt.count(drop_txt)
    txt1 = txt.replace(drop_txt, '', 1)
    # ② pair_of 末尾追加 5 条
    add_txt = ''.join(ent_text(ch, b1, b2) for ch, b1, b2 in NEW_PAIRS)
    anchor = '\n },\n "trim19"'
    assert txt1.count(anchor) == 1, 'pair_of 结束锚点不唯一'
    txt2 = txt1.replace(anchor, ',\n' + add_txt.rstrip('\n').rstrip(',') + anchor, 1)
    # ③ 追加 metadata 块
    meta = {
        "note": ("round-FA2400: 图集 h 640→644 / 网格 62→64 列 / decode gate 0xB1..0xB5→0xBA "
                 "(对偶槽 2,350); 击/小/时/按 由单字节码 0xB6..0xB9 迁移成对偶码 "
                 "0xB9FD/FE0xB9FC/0xB9FB/0xB9FA (slot 2348/2347/2346/2345), "
                 "✕ 图标占位 (引擎 0xB5, 原走 pda_counterparts 贴图) 也改写成对偶码 0xB9FE "
                 "(slot 2349, 字形 = render16(方正像素16.ttf,'×'), 见 docs/CAPACITY_2400.md 的来源判定); "
                 "0..1871 的既有条目一个字段未动; slot 1872..2344 保留空 (无字形); "
                 "图集里 slot 1736..1871 的 r84 字形由 GR_F364/F365 恢复 (合并盘曾被写成探针图案)"),
        "gate_old": 0xB5, "gate_new": 0xBA, "atlas_wh": [1024, 644], "ncol": 64,
        "px_size": 329744, "nseg": 11, "slot_space": 2350,
        "n_pair_before": 1872, "n_pair_after": 1877,
        "reserved_slots": [1872, 2344], "borrowed_slots": [2345, 2349],
        "migrated_codes": {ch: {'code_old': b, 'pair_new': [b1, b2], 'slot': slot_of((b1, b2))}
                           for (ch, b), (_c, b1, b2) in zip(DROP_CODES, NEW_PAIRS)},
        "icon_pair": {"char": "\u2715", "pair": [0xB9, 0xFE], "slot": 2349,
                      "note": ("图标不是字: 引擎只在字符值 0xB1/0xB5 上特判, 且图标美术来自"
                               " pda_counterparts.rsb (不吃字库)。抬闸门后文本里的裸 0xB5 会被当前导"
                               " ⇒ 迁移成对偶码 0xB9FE, 因此本表必须给它一个**非占位**字符名"
                               " (U+2715) —— 用私有区 U+E0B5 会破坏 tcslib 的 encode/decode 互逆"
                               " (U+E080..U+E0FF 一律按单字节 0xXX 编码)")}}
    mtxt = json.dumps(meta, ensure_ascii=False, indent=1)
    mtxt = '\n "_expand_fa2400": ' + mtxt.replace('\n', '\n ') + '\n}'
    assert txt2.endswith('\n}')
    txt3 = txt2[:-2] + ',' + mtxt
    d1 = json.loads(txt3)
    P('[edit ] 文本级最小编辑完成: %d B → %d B (Δ=%+d)' % (len(raw), len(txt3.encode('utf-8')),
                                                          len(txt3.encode('utf-8')) - len(raw)))

    # ── 自查 ──
    P('')
    nbad = [ch for ch, v in d0['pair_of'].items() if d1['pair_of'].get(ch) != v]
    P('[C1] 既有 1872 条 pair_of 逐字段相同: %s (不同 %d)' % ('✓' if not nbad else '✗', len(nbad)))
    assert not nbad
    assert len(d1['pair_of']) == 1872 + 5
    lost = set(d0['codes']) - set(d1['codes'])
    chg = [k for k in d1['codes'] if d0['codes'].get(k) != d1['codes'][k]]
    P('[C2] codes: %d → %d 条 ; 少的键 = %s (期望 %s) ; 其余键值变化 %d'
      % (len(d0['codes']), len(d1['codes']), sorted(lost), sorted(c for c, _b in DROP_CODES),
         len(chg)))
    assert lost == set(c for c, _b in DROP_CODES) and not chg
    newp = {ch: v for ch, v in d1['pair_of'].items() if ch not in d0['pair_of']}
    P('[C3] 新增 pair_of 条目 %d 条: %s' % (len(newp),
                                           {c: v for c, v in newp.items()}))
    s1 = sorted(slot_of(v) for v in d0['pair_of'].values())
    s2 = sorted(slot_of(v) for v in d1['pair_of'].values())
    assert sorted(slot_of(v) for v in newp.values()) == [2345, 2346, 2347, 2348, 2349]
    P('[C3] 新条目 slot = %s ✓ ; 1872..2344 仍 0 条 ✓ ; 槽空间上界 = %d'
      % (sorted(slot_of(v) for v in newp.values()), max(s2)))
    assert not [x for x in s2 if 1872 <= x <= 2344]
    # C4/C6: gate 0xBA 语义的编解码互逆
    codes1 = {v: k for k, v in d1['codes'].items()}
    pair1 = {tuple(v): k for k, v in d1['pair_of'].items()}
    enc1 = {k: v for k, v in d1['codes'].items()}
    okc = []
    for ch, (b1, b2) in newp.items():
        t, mp = decode_ba(bytes((b1, b2)), codes1, pair1)
        okc.append((ch, t == ch, t))
    P('[C4] gate 0xBA 解码新对偶码: %s' % ', '.join('%s→%r %s' % (c, t, '✓' if o else '✗')
                                                    for c, o, t in okc))
    assert all(o for _c, o, _t in okc)
    bad = []
    for ch, pr in d1['pair_of'].items():
        b = bytes(pr)
        t, _ = decode_ba(b, codes1, pair1)
        if t != ch:
            bad.append((ch, pr, t))
    P('[C6] 全表 %d 条对偶码 decode 回自己: %s (反例 %d)' % (len(d1['pair_of']),
                                                            '✓' if not bad else '✗', len(bad)))
    assert not bad, bad[:5]
    # C5: 图集里有墨
    F = FB.read_font(NEW_ISO)
    for ch, pr in newp.items():
        s = slot_of(pr)
        cx, cy = FB.cell(s, 64)
        g = FB.cell_read(F['plane'], cx, cy, 1024)
        P('[C5] %r pair=0x%02X%02X slot=%-4d 引擎格 (%3d,%3d) 回读墨 = %3d %s'
          % (ch, pr[0], pr[1], s, cx, cy, int(g.sum()), '✓' if g.any() else '✗'))
        assert g.any(), ch
    F['iso'].close()

    if a.dry_run:
        P('')
        P('[dry ] 未写盘')
        return 0
    # ── 备份 + 写盘 ──
    if not os.path.exists(BK):
        with open(BK, 'wb') as f:
            f.write(raw)
        P('[bk  ] 改前备份 → %s (%d B)' % (BK, len(raw)))
    else:
        same = open(BK, 'rb').read() == raw
        P('[bk  ] 备份已存在 ✓ ; 与当前 charset 逐字节相同: %s' % ('✓' if same else '✗ (保留最先的备份)'))
    with io.open(CS, 'w', encoding='utf-8', newline='\n') as f:
        f.write(txt3)
    back = open(CS, 'rb').read()
    db = json.loads(back.decode('utf-8'))
    assert len(db['pair_of']) == 1877 and len(db['codes']) == 103
    P('[out ] 写盘 %s (%d B) ; 回读 codes %d / pair_of %d ✓'
      % (CS, len(back), len(db['codes']), len(db['pair_of'])))
    # 文本级 diff (给报告)
    import difflib
    dl = list(difflib.unified_diff(raw.decode('utf-8').splitlines(),
                                   back.decode('utf-8').splitlines(),
                                   'charset_before_fa2400.json',
                                   'charset_compiled_zh16.json', lineterm='', n=1))
    with io.open(os.path.join(REPO, 'work', 'builds', 'GR_FA2400', 'temp', 'charset_diff.txt'),
                 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(dl) + '\n')
    nadd = sum(1 for x in dl if x.startswith('+') and not x.startswith('+++'))
    ndel = sum(1 for x in dl if x.startswith('-') and not x.startswith('---'))
    P('[diff] 文本级 diff: +%d 行 / -%d 行 → work/builds/GR_FA2400/temp/charset_diff.txt'
      % (nadd, ndel))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
