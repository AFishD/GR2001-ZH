# -*- coding: utf-8 -*-
r"""migrate_selfcheck_test.py — 闸门自检的**正/负/回归**三向测试 (只读, 不写盘)

    python tools/re/toolbelt/migrate_selfcheck_test.py

  [1] 正: GR_TXMIG (gate 0xBA, 已迁移) 三个容器  ⇒ 残留 0
  [2] 负: 合成载荷 "0xB6 + ASCII"                ⇒ **必须**抛 LegacyCodeError
  [3] 回归: GR_ZH113b (gate 0xB1) 窗口为空       ⇒ 一个字节都不查, 残留 0
  [4] 负: GR_F365 (gate 0xB5, 历史"文本未迁移"盘) ⇒ 必须拒绝 (exit 2 的那条路径)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                       # noqa: E402
import inject_text_csv as INJ                                            # noqa: E402

OK = []


def P(*a):
    print(*a, flush=True)


def scan(iso_path):
    cs = T.Charset()
    iso = T.Iso(iso_path)
    gate = T.read_decode_gate(iso)
    extra = T.load_gate_pairs()
    tot, res = 0, []
    for name, spec in T.RES.items():
        for cp in spec['copies']:
            c = INJ.Container(iso, name, cp, cs)
            try:
                r = T.legacy_selfcheck_container(c, c.blob, gate, extra, verbose=False)
                tot += r['n']
                res.append((c.tag, r['n'], 'ok'))
            except T.LegacyCodeError as ex:
                res.append((c.tag, str(ex).splitlines()[0], 'REFUSE'))
    iso.close()
    return gate, tot, res


P('=' * 84)
P('[1] 正例: work/builds/GR_TXMIG/GR_TXMIG.iso (gate 0xBA, 已全量迁移)')
P('=' * 84)
g, n, res = scan(os.path.join(REPO, 'work', 'builds', 'GR_TXMIG', 'GR_TXMIG.iso'))
for (tag, r, st) in res:
    P('    %-24s %s' % (tag, r))
P('    ⇒ 闸门 0x%02X · 残留合计 %d %s' % (g, n, '✓' if n == 0 else '✗'))
OK.append(('正例 GR_TXMIG', n == 0))

P('')
P('=' * 84)
P('[2] 负例: 合成载荷 —— gate 0xBA 下的裸 0xB6(击) 必须被拦下')
P('=' * 84)
cs = T.Charset()
pairs = dict(cs.pair_of)
pairs.update(T.load_gate_pairs())
bad = [b'\x41\x42\xb6\x20\x43', b'\xb9\x41']          # 裸 0xB6 + ASCII; 裸 0xB9 + ASCII
n_ok = 0
for i, pay in enumerate(bad):
    try:
        T.assert_no_legacy_residue(pay, 'synthetic#%d' % i, 0xBA, pairs, cs.codes)
        P('    synthetic#%d %s ⇒ **没拦下** ✗' % (i, pay.hex()))
    except T.LegacyCodeError as ex:
        n_ok += 1
        P('    synthetic#%d %s ⇒ 拦下 ✓  (%s)' % (i, pay.hex(), str(ex).splitlines()[0]))
good = bytes((0xB9, 0xFB)) + b'\x41'                  # 合法对偶码 (时) + ASCII ⇒ 应放行
try:
    T.assert_no_legacy_residue(good, 'synthetic#ok', 0xBA, pairs, cs.codes)
    P('    synthetic#ok %s (合法对偶码 0xB9FB) ⇒ 放行 ✓' % good.hex())
    OK.append(('负例 合成载荷', n_ok == len(bad)))
except T.LegacyCodeError as ex:
    P('    synthetic#ok 被误拦 ✗ %s' % ex)
    OK.append(('负例 合成载荷', False))

P('')
P('=' * 84)
P('[3] 回归: GR_ZH113b (gate 0xB1 ⇒ 检查窗口为空, 老盘必须零行为变化)')
P('=' * 84)
g3, n3, res3 = scan(os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso'))
P('    ⇒ 闸门 0x%02X · 窗口 = %s · 残留 %d %s'
  % (g3, list(T.legacy_window(g3)) or '(空)', n3, '✓' if n3 == 0 else '✗'))
OK.append(('回归 GR_ZH113b', g3 == 0xB1 and n3 == 0 and not list(T.legacy_window(g3))))

P('')
P('=' * 84)
P('[4] 负例(真实盘): GR_F365 (gate 0xB5, 文本未迁移的历史盘) 必须 REFUSE')
P('=' * 84)
g4, n4, res4 = scan(os.path.join(REPO, 'work', 'builds', 'GR_F365', 'GR_F365.iso'))
n_ref = sum(1 for (_t, _r, st) in res4 if st == 'REFUSE')
for (tag, r, st) in res4:
    P('    %-24s [%s] %s' % (tag, st, r))
P('    ⇒ 闸门 0x%02X · 拒绝容器 %d/3 %s' % (g4, n_ref, '✓' if n_ref else '✗'))
OK.append(('负例 GR_F365', n_ref > 0))

P('')
P('=' * 84)
for (name, o) in OK:
    P('  %-18s %s' % (name, '✓ PASS' if o else '✗ FAIL'))
P('  总计: %s' % ('**全部通过**' if all(o for _n, o in OK) else '**有失败项**'))
P('=' * 84)
sys.exit(0 if all(o for _n, o in OK) else 1)
