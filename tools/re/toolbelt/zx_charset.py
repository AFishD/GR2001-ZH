# -*- coding: utf-8 -*-
r"""zx_charset.py — 为「零缺字成品盘」更新 charset JSON (round82)

改动面（只增 + 4 条迁移）:
  · `pair_of` 新增 368 条: slot 1504..1871（364 个缺字 + △/键/练/用 四个迁移字）
  · `codes`  删掉 0xB2/键 / 0xB3/练 / 0xB4/用（gate 抬到 0xB5 后 0xB1..0xB4 变成 lead,
    留在 codes 里会被引擎当对偶首字节吞掉 ⇒ tcslib.selfcheck_charset 的
    「lead 区间内的单字节码」那条也会直接判死）
  · 原 1504 条对偶码 / 其余 107 条单字节码 **一个字节都不动**（逐条比对原备份）

用法:
  python zx_charset.py --assignment <patch_font_report.json>   # 用补丁报告里的格子表
  python zx_charset.py --revert                                # 从 r82 备份还原
  python zx_charset.py --status                                # 只读: 现状 + 自检
"""
import argparse
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import zx_lib                                                        # noqa: E402  (先插 sys.path)
import tcslib                                                        # noqa: E402

REPO = zx_lib.REPO
CHARSET = tcslib.CHARSET
BACKUP = os.path.join(zx_lib.OUT, 'charset_before_r82.json')
MIGRATE_BYTES = {0xB2: '键', 0xB3: '练', 0xB4: '用'}
GATE = 0xB5                     # 新 gate: lead ∈ [0xA1, 0xB5)
LEAD_LO, TRAIL_LO, STRIDE = 0xA1, 0xA1, 94


def pair_from_slot(slot):
    assert 0 <= slot < (GATE - LEAD_LO) * STRIDE
    return [LEAD_LO + slot // STRIDE, TRAIL_LO + slot % STRIDE]


def status():
    cs = json.load(io.open(CHARSET, encoding='utf-8'))
    codes = {k: int(v) for k, v in cs['codes'].items()}
    pair = {k: tuple(v) for k, v in cs['pair_of'].items()}
    print('charset: codes %d, pair_of %d' % (len(codes), len(pair)))
    print('  codes 里落在新 lead 区间 [0xA1,0xB5) 的: %s'
          % [(hex(b), ch) for ch, b in sorted(codes.items(), key=lambda kv: kv[1])
             if 0xA1 <= b < GATE])
    print('  pair lead 直方图: %s'
          % sorted({l: sum(1 for p in pair.values() if p[0] == l) for l in
                    {p[0] for p in pair.values()}}.items()))
    print('  slot 上限: %d' % max((p[0] - LEAD_LO) * STRIDE + (p[1] - TRAIL_LO)
                                  for p in pair.values()))
    if not os.path.exists(BACKUP):
        print('  (无 r82 备份)')
        return
    old = json.load(io.open(BACKUP, encoding='utf-8'))
    drift = [ch for ch in old['pair_of'] if pair.get(ch) != tuple(old['pair_of'][ch])]
    print('  与原备份相比: 现役 pair 漂移 %d 条 ; codes 增减 %s'
          % (len(drift), sorted(set(codes) ^ set(old['codes']))))


def revert():
    assert os.path.exists(BACKUP), BACKUP
    shutil.copyfile(BACKUP, CHARSET)
    print('[revert] %s ← %s' % (CHARSET, BACKUP))
    status()
    return 0


def apply_assignment(assignment, dry=False):
    """assignment: [(char, slot)] 顺序即 slot 分配; 断言 slot 单调 = SLOT_LO.."""
    if not os.path.exists(BACKUP):
        shutil.copyfile(CHARSET, BACKUP)
        print('[json] 原 charset 备份 → %s' % BACKUP)
    old = json.load(io.open(BACKUP, encoding='utf-8'))
    # 幂等: 允许输入态 = 原备份 (1504) 或 已经是本工具的产物
    js = json.load(io.open(CHARSET, encoding='utf-8'))
    n_old_pair = len(old['pair_of'])
    assert n_old_pair == 1504, n_old_pair
    # 1) 现役 1504 条必须与备份逐条一致
    drift = [(ch, old['pair_of'][ch], js['pair_of'].get(ch)) for ch in old['pair_of']
             if js['pair_of'].get(ch) != list(old['pair_of'][ch])
             and js['pair_of'].get(ch) != old['pair_of'][ch]]
    assert not drift, '现役 pair_of 被改动 %d 条: %s' % (len(drift), drift[:3])
    # 2) 迁移字从 codes 里摘掉; 其余 codes 逐条不变（★ 幂等: 已经摘过就只校验）
    codes = dict(js['codes'])
    slot_of = {c: s for c, s in assignment}
    for b, ch in MIGRATE_BYTES.items():
        if ch in codes:
            assert codes[ch] == b, (ch, b, codes[ch])
            del codes[ch]
        else:
            assert ch in js['pair_of'], '%r 既不在 codes 也不在 pair_of' % ch
            assert js['pair_of'][ch] == list(pair_from_slot(slot_of[ch])), \
                '%r 已迁移但码位不符: %s' % (ch, js['pair_of'][ch])
    rest_old = {ch: b for ch, b in old['codes'].items() if ch not in MIGRATE_BYTES.values()}
    assert codes == rest_old, 'codes 除迁移 3 字外被动过'
    left = [hex(b) for b in (int(v) for v in codes.values()) if 0xA1 <= b < GATE]
    assert not left, 'codes 里仍有落在 lead 区间的字节: %s' % left
    # 3) 写 pair_of
    SLOT_LO = 1504
    assert [s for _c, s in assignment] == list(range(SLOT_LO, SLOT_LO + len(assignment))), \
        'slot 分配不是连续的 %d..' % SLOT_LO
    assert len({c for c, _s in assignment}) == len(assignment), '有重复字'
    have = set(codes) | set(js['pair_of'])
    for ch, slot in assignment:
        if ch in js['pair_of']:
            assert js['pair_of'][ch] == list(pair_from_slot(slot)), \
                '%r 已在 pair_of 且码位不同: %s vs %s' % (ch, js['pair_of'][ch],
                                                          pair_from_slot(slot))
            continue
        assert ch not in codes, '%r 仍在 codes 里' % ch
        js['pair_of'][ch] = pair_from_slot(slot)
    assert len(js['pair_of']) == 1504 + len(assignment), len(js['pair_of'])
    js['codes'] = codes
    js['_expand_zh121'] = dict(
        note='round82 「零缺字成品盘」: gate 0xB1→0xB5 (ELF 4 处 sltiu) ⇒ lead 0xA1..0xB4, '
             '对偶空间 1880 ; 图集 1024x512→1024x640 (10 段自闭合包), 新字落在 slot '
             '1504..1871 = 行 24 尾 / 行 25..29 / 行 30 头 ; 两条活带搬到 y594/610 ; '
             '键/练/用 由单字节码迁移成对偶码 (0xB1..0xB4 已是 lead) ; △ 也改对偶 '
             '(原 0xB1 图标码会被当成 lead 吞掉后一个字节)。',
        slot_lo=SLOT_LO, slot_hi=SLOT_LO + len(assignment) - 1,
        n_missing=364, n_migrated=4, n_total=len(assignment),
        migrated={ch: pair_from_slot(s) for ch, s in assignment if ch in
                  list(MIGRATE_BYTES.values()) + ['△']},
        chars={ch: pair_from_slot(s) for ch, s in assignment})
    if dry:
        print('[dry ] 不写 charset (会新增 %d 条)' % len(assignment))
        return js
    io.open(CHARSET, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(js, ensure_ascii=False, indent=1) + '\n')
    print('[json] charset 已更新: pair_of %d → %d, codes %d → %d'
          % (n_old_pair, len(js['pair_of']), len(old['codes']), len(codes)))
    # 4) 自检 (走 tcslib 自己的口径)
    cs = tcslib.Charset(CHARSET)
    ok, lines = tcslib.selfcheck_charset(cs)
    for ln in lines:
        if ln.startswith('[!!]'):
            print('   ' + ln)
    assert ok, 'tcslib.selfcheck_charset 未通过'
    print('[json] tcslib.selfcheck_charset: %d 条全 [ok] ✓' % len(lines))
    bad = [ch for ch, p in cs.enc_pair.items() if not (LEAD_LO <= p[0] < GATE)]
    assert not bad, '仍有 lead 越界的 pair: %s' % bad[:5]
    for ch, _s in assignment:
        p = cs.enc_pair[ch]
        assert cs.encode_strict(ch) == bytes(p), ch
        assert cs.decode(bytes(p))[0] == ch, ch
    print('[json] 368 条新码位「编码↔解码」逐字节自洽 ✓ ; pair_lead_bad = 0 ✓')
    return js


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--assignment', help='patch_font_report.json (含 cells)')
    ap.add_argument('--revert', action='store_true')
    ap.add_argument('--status', action='store_true')
    a = ap.parse_args()
    if a.revert:
        return revert()
    if a.status or not a.assignment:
        status()
        if not a.assignment:
            return 0
    rep = json.load(io.open(a.assignment, encoding='utf-8'))
    cells = rep.get('cells')
    assert cells, '报告里没有 cells'
    assignment = [(c[0], c[1]) for c in cells]
    print('[in ] 分配表 %d 条 (slot %d..%d)' % (len(assignment), assignment[0][1],
                                                assignment[-1][1]))
    apply_assignment(assignment)
    status()
    return 0


if __name__ == '__main__':
    sys.exit(main())
