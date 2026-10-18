# -*- coding: utf-8 -*-
r"""cap_charset.py -- Step 5: 把 charset 的 pair_of 扩到 2,350 条 (受保护路径, 先备份)

    python tools/re/toolbelt/cap_charset.py [--apply]

★ 基线说明 (2026-10-15 实测): 受保护路径已被 **另一路 (round-FA2400)** 写过一次:
    pair_of = 1,877 条 (0..1871 既有 + 2345..2349 的 击/小/时/按/✕)
    codes   = 103 条  (已删 0xB6..0xB9 四条 —— pair_of 用到 lead 0xB9 时的硬不变式)
  它的元数据里明确写着 `reserved_slots = [1872, 2344]` (留空, 无字形) ⇒ **本轮补的就是这 473 个槽**。

本工具做且只做:
  · 1872..1935 : 64 个**真实备选字** —— PC 官方中文文本 (tools/hanliu/texts/pc_official_zh.csv)
                 里本工程还没有的 CJK 字; 排序 = 频次降序, 再按码位升序 (确定性)
  · 1936..2344 : 409 个**预留槽占位** U+E200.. (字符/字形待补; 不进 U+E080..U+E0FF, 以免被
                 tcslib 当"按键图标占位"按单字节编码)
  · 0..1871 与 2345..2349 的既有 1,877 条: **逐条不动**; codes: **一个条目都不动**
自检: 2350 条 / slot 连续 0..2349 / lead ∈ [0xA1,0xBA) / trail ∈ [0xA1,0xFE) /
      既有条目逐条相同 / selfcheck_charset == True / encode-decode 对称。
"""
import argparse
import collections
import hashlib
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                    # noqa: E402

OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_CAP2400')
CHARSET = T.CHARSET
PC_ZH = os.path.join(REPO, 'tools', 'hanliu', 'texts', 'pc_official_zh.csv')
N_TARGET = 2350
PUA_RESERVE = 0xE200
FILL_LO, FILL_HI = 1872, 2344
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def slot_of(p):
    return (int(p[0]) - T.LEAD_LO) * T.PAIR_STRIDE + (int(p[1]) - T.PAIR_TRAIL_LO)


def sha_file(p):
    return hashlib.sha256(io.open(p, 'rb').read()).hexdigest()


def reserve_pool(have):
    raw = io.open(PC_ZH, encoding='utf-8-sig', errors='replace').read()
    cnt = collections.Counter(ch for ch in raw
                              if 0x4E00 <= ord(ch) <= 0x9FFF and ch not in have)
    return sorted(cnt.items(), key=lambda kv: (-kv[1], ord(kv[0])))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args(argv)
    P('=' * 96)
    P('cap_charset.py  pair_of → %d 条 (补 slot %d..%d)' % (N_TARGET, FILL_LO, FILL_HI))
    P('  charset = %s' % CHARSET)
    base_sha = sha_file(CHARSET)
    P('  基线 sha256 = %s' % base_sha)
    raw = json.load(io.open(CHARSET, encoding='utf-8'))
    codes = {k: int(v) for k, v in raw['codes'].items()}
    pairs = {k: [int(x) for x in v] for k, v in raw['pair_of'].items()}
    slots0 = sorted(slot_of(v) for v in pairs.values())
    P('[base] codes %d 条 ; pair_of %d 条 ; slot %s' % (len(codes), len(pairs),
                                                         '%d..%d (+%d..%d)' % (
                                                             slots0[0], slots0[1871],
                                                             slots0[1872], slots0[-1])))
    assert len(pairs) == 1877 and len(codes) == 103, (len(pairs), len(codes))
    assert slots0[:1872] == list(range(1872)) and slots0[1872:] == list(range(2345, 2350))
    assert all(k in pairs for k in ('击', '小', '时', '按'))
    bak = os.path.join(OUTDIR, 'charset_before_cap2400.json')
    os.makedirs(OUTDIR, exist_ok=True)
    if not os.path.exists(bak):
        shutil.copy2(CHARSET, bak)
        P('[bak ] 备份基线 → %s (sha256=%s)' % (bak, sha_file(bak)))
    else:
        P('[bak ] 备份已存在 → %s (sha256=%s)' % (bak, sha_file(bak)))

    have = set(codes) | set(pairs)
    pua = [ch for ch in have if 0xE000 <= ord(ch) <= 0xF8FF]
    assert not pua, '基线里已有私有区字 %r, 需人工确认' % pua
    P('[base] 基线无私有区 (U+E000..U+F8FF) 字符 ✓ (全角标点 U+FFxx 不算)' )
    pool = reserve_pool(have)
    P('[pool] PC 官方中文 (%s) 未登记 CJK 字 %d 个' % (
        os.path.relpath(PC_ZH, REPO).replace('\\', '/'), len(pool)))
    new, info_real, info_ph = {}, [], []
    cur = FILL_LO
    for ch, n in pool[:64]:
        assert cur <= FILL_HI
        new[ch] = list(T.pair_from_slot(cur))
        info_real.append((cur, ch, n))
        cur += 1
    while cur <= FILL_HI:
        ch = chr(PUA_RESERVE + len(info_ph))
        assert ch not in have and ch not in new
        new[ch] = list(T.pair_from_slot(cur))
        info_ph.append((cur, ch))
        cur += 1
    P('[fill] 真实备选 %d 个 (slot %d..%d) + 预留占位 %d 个 (U+%04X..U+%04X ⇒ slot %d..%d)'
      % (len(info_real), info_real[0][0], info_real[-1][0], len(info_ph),
         PUA_RESERVE, PUA_RESERVE + len(info_ph) - 1, info_ph[0][0], info_ph[-1][0]))
    for (s, ch, n) in info_real[:10]:
        P('       slot %-5d %s  (PC 官方文本 %d 次)' % (s, ch, n))
    P('       ... 共 %d 个 (完整清单见 json 的 _expand_cap2400.real_chars)' % len(info_real))

    merged = dict(pairs)
    merged.update(new)
    slots = sorted(slot_of(v) for v in merged.values())
    assert slots == list(range(N_TARGET)), (len(slots), slots[:3], slots[-3:])
    assert len(merged) == N_TARGET and len(set(map(tuple, merged.values()))) == N_TARGET
    for ch, (b1, b2) in merged.items():
        assert T.LEAD_LO <= b1 < 0xBA and T.PAIR_TRAIL_LO <= b2 < 0xFF, (ch, b1, b2)
    for ch, p in pairs.items():
        assert merged[ch] == p, '既有条目被改动: %r' % ch
    P('[chk1] pair_of %d 条 / slot 连续 0..%d / lead ∈ [0xA1,0xBA) / trail ∈ [0xA1,0xFE) ✓'
      % (len(merged), N_TARGET - 1))
    P('[chk2] 既有 1,877 条逐条不动 ✓ ; codes %d 条逐条不动 ✓' % len(codes))

    out = dict(raw)
    out['pair_of'] = {k: list(v) for k, v in merged.items()}
    out['_expand_cap2400'] = dict(
        note='geom2400: 把 round-FA2400 预留的 slot 1872..2344 登记满 ⇒ pair_of 1,877 → 2,350; '
             '既有 1,877 条与 codes %d 条一个字段未动' % len(codes),
        atlas=dict(w=1024, h=644, ncol=64, nrow=37, cells=2368, px_size=329744, nseg=11),
        gate=0xBA, slot_space=2350,
        fill_range=[FILL_LO, FILL_HI],
        real_chars={str(s): [ch, n] for (s, ch, n) in info_real},
        real_source=os.path.relpath(PC_ZH, REPO).replace('\\', '/'),
        placeholder_pua=['U+%04X' % PUA_RESERVE, 'U+%04X' % (PUA_RESERVE + len(info_ph) - 1)],
        placeholder_note='预留槽: **只有槽位与码位, 无字符、无字形**; 文本团队给字后只需把键换掉, '
                         '码位/槽位不变。刻意不用 U+E080..U+E0FF (那段会被 tcslib 当按键图标占位, '
                         '按单字节 0xXX 编码 ⇒ 破坏 encode/decode 互逆)。',
        probe='work/builds/GR_CAP2400/GR_CAP2400.iso (h=644/64列/GATE 0xBA, 槽 0..2349 全可寻址)',
        baseline_sha256=base_sha, proof='work/builds/GR_CAP2400/cap_charset.log + docs/CAPACITY_2400.md')
    tmp = os.path.join(OUTDIR, 'charset_after_cap2400.json')
    with io.open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    cs = T.Charset(tmp)
    sc = T.selfcheck_charset(cs)
    ok_raw, detail_raw = sc if isinstance(sc, tuple) else (sc, [])
    bad_raw = [l for l in (detail_raw or []) if str(l).startswith('[!!]')]
    P('[chk3-pre] 用**未更新**的 tcslib 常量 (LEAD_HI=0x%02X) 自检 = %s (失败项 %d): %s'
      % (T.LEAD_HI, ok_raw, len(bad_raw), [str(x)[:60] for x in bad_raw]))
    P('          ★ 这是**基线就有的**工具链缺口 (round-FA2400 的 lead 0xB9 pair 已经踩到),')
    P('            不是本轮引入: 修法 = tools/text_csv/tcslib.py L58-59 的')
    P('            LEAD_LO, LEAD_HI = 0xA1, 0xB5 / PAIR_LEAD_LO, PAIR_LEAD_HI = 0xA1, 0xB5')
    P('            → 0xBA (gate 0xBA 的真实上界)。该文件属**文本迁移路**写入范围, 本轮不改。')
    T.LEAD_HI = T.PAIR_LEAD_HI = 0xBA            # 运行时对齐 (不写盘)
    sc2 = T.selfcheck_charset(cs)
    ok, detail = sc2 if isinstance(sc2, tuple) else (sc2, [])
    bad = [l for l in (detail or []) if str(l).startswith('[!!]')]
    P('[chk3] 把 lead 上界按 gate 0xBA 对齐后 (运行时) = **%s** (失败项 %d)' % (ok, len(bad)))
    for l in bad:
        P('       %s' % l)
    assert ok, bad
    probe_txt = ''.join(ch for ch, _n in pool[:64]) + ''.join(list(pairs)[:80]) + '击小时按'
    b, issues = cs.encode(probe_txt)
    assert not [x for x in issues if x[2]], issues[:4]
    back, _ = cs.decode(b)
    assert back == probe_txt, 'encode/decode 不对称'
    P('[chk4] encode/decode 对称: %d 个新备选字 + 80 个既有字 + 击/小/时/按 ✓'
      % len(pool[:64]))
    for ch in ('击', '小', '时', '按'):
        bb, _ = cs.encode(ch)
        P('[chk5] %s → 0x%s (对偶码; codes 里已无 0x%02X) ✓'
          % (ch, bb.hex().upper(), codes.get(ch, -1)))
    # 预留占位自检: 编码 → 解码 → 同一个占位字符
    ph = info_ph[0][1]
    bb, _ = cs.encode(ph)
    back2, _ = cs.decode(bb)
    assert back2 == ph, (back2, ph)
    P('[chk6] 占位 %r → 0x%s → 回读一致 ✓' % (ph, bb.hex().upper()))

    if a.apply:
        if sha_file(CHARSET) != base_sha:
            raise SystemExit('!! charset 在本次运行期间被别的进程改了 (sha 变了), 中止不写')
        with io.open(CHARSET, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        P('[apply] ★ 已写受保护路径 %s' % CHARSET)
        P('[apply] pair_of 1,877 → **%d** ; codes 仍 **%d** 条 (未动)'
          % (len(merged), len(codes)))
        P('[apply] 新 sha256 = %s' % sha_file(CHARSET))
        P('[apply] 一键还原: Copy-Item %s %s -Force' % (bak, CHARSET))
    else:
        P('[dry  ] 未写受保护路径 (加 --apply); 变体见 %s' % tmp)
    with io.open(os.path.join(OUTDIR, 'cap_charset.log'), 'w', encoding='utf-8',
                 newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
