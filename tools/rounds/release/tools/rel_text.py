# -*- coding: utf-8 -*-
r"""rel_text.py -- 交付候选的**文本层**独立核对 (载荷级旧码扫描 + 逐字符一致)

    python work\builds\GR_RELEASE\tools\rel_text.py ^
        --iso  work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso ^
        --base work\builds\GR_REBUILD\GR_REBUILD2400.iso ^
        --out  work\builds\GR_RELEASE\temp

★ 为什么不用 `migrate_legacy_audit.py --ref-iso`:
  该工具的 [B] 段假设 `--ref-iso` 是**基底闸门 (0xB1) 时代**的盘。本轮的参照盘
  `GR_FA2400_K2_geom.iso`（迁移前、gate 0xB1）**已不在磁盘上**；盘上现存的每一张中文盘
  都已是 gate 0xBA（见 temp\gate_scan.txt）。拿一张已迁移的盘当"基底"去解，会得到
  385/41 处**假差异**（基底侧被解成乱码），所以本脚本改用三条独立判据:
    [1] 载荷字节**逐字节**相同 (产物盘 vs 直接基底) —— 比"解码后逐字符相同"更强
    [2] 载荷级裸旧码扫描 (§14.1 主判据), 自己实现一遍 (第二套实现)
    [3] 全量解码: 用**新闸门 + 权威 charset** 解 3 个容器, 统计"不可解析字节/字符" = 0
"""
import argparse
import collections
import importlib.util
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
MLA = None
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def load_mla():
    global MLA
    p = os.path.join(REPO, 'tools', 're', 'toolbelt', 'migrate_legacy_audit.py')
    spec = importlib.util.spec_from_file_location('mla', p)
    m = importlib.util.module_from_spec(spec)
    sys.modules['mla'] = m
    spec.loader.exec_module(m)
    MLA = m
    return m


def bare_scan(data, base_gate, gate, pair_set):
    """第二套独立实现: 按**新闸门**走, 数 [base_gate,gate) 里"不是合法对偶 lead"的字节。

    ≠ "0xB1..0xB9 出现次数为 0": 这些字节作为**对偶 lead** 出现是合法的。
    返回 (unpaired 数, 逐码明细, 总字节)。
    """
    i, n = 0, len(data)
    un = collections.Counter()
    while i < n:
        c = data[i]
        if 0xA1 <= c < gate:
            t = data[i + 1] if i + 1 < n else None
            if base_gate <= c < gate and (t is None or (c, t) not in pair_set):
                un[c] += 1
            i += 2
            continue
        i += 1
    return sum(un.values()), dict(sorted(un.items())), n


def full_decode(data, gate, pair_dec, codes, legacy=None):
    """用权威 charset 全量解码; 返回 (字符串, 未解析字节数, 逐类计数)。

    ★ 对偶判定与 tcslib 一致: lead ∈ [0xA1,gate) **且** trail ∈ [0xA1,0xFE]
      —— trail 落在区间外时该 lead 是**单字节码** (例如 0xA4 后面跟 ASCII 'M16'),
      这一点与 rb_verify_k2.py [2b] 的写法逐字一致。
    """
    out, i, n, bad = [], 0, len(data), collections.Counter()
    TRAIL_LO, TRAIL_HI = 0xA1, 0xFE
    while i < n:
        c = data[i]
        if 0xA1 <= c < gate and i + 1 < n and TRAIL_LO <= data[i + 1] <= TRAIL_HI:
            ch = pair_dec.get((c, data[i + 1]))
            if ch is not None:
                out.append(ch)
                i += 2
                continue
            bad['pair_miss'] += 1
            out.append('\ufffd')
            i += 2
            continue
        ch = codes.get(c)
        if ch is not None:
            out.append(ch)
        elif c in (0x0A, 0x0D, 0x09) or 0x20 <= c < 0x7F:
            out.append(chr(c))
        else:
            bad['byte_miss'] += 1
            out.append('\ufffd')
        i += 1
    return ''.join(out), sum(bad.values()), dict(bad)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--base', required=True)
    ap.add_argument('--charset', default=os.path.join(
        REPO, 'work', 'builds', 'GR_HASHR', 'backup',
        'charset_compiled_zh16.json.before_hashr'))
    ap.add_argument('--pairs', default=None)
    ap.add_argument('--out', required=True)
    ap.add_argument('--samples', type=int, default=6)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    m = load_mla()
    cs = json.load(io.open(a.charset, encoding='utf-8'))
    codes = {int(v): k for k, v in cs['codes'].items()}
    pair_dec = {tuple(v): k for k, v in cs['pair_of'].items()}
    if a.pairs and os.path.isfile(a.pairs):
        j = json.load(io.open(a.pairs, encoding='utf-8'))
        for ch, p in (j.get('pairs', j) or {}).items():
            pair_dec[tuple(p)] = ch
    pair_set = set(pair_dec)
    gate, base_gate = 0xBA, 0xB1
    P('=' * 100)
    P('rel_text.py -- 文本层独立核对 (载荷级)')
    P('  iso     = %s' % os.path.abspath(a.iso))
    P('  base    = %s' % os.path.abspath(a.base))
    P('  charset = %s (%d codes / %d pairs)' % (os.path.basename(a.charset),
                                                len(codes), len(pair_dec)))
    P('  闸门    = 0x%02X (基底 0x%02X)' % (gate, base_gate))
    P('=' * 100)
    ia, ib = m.Iso(a.iso), m.Iso(a.base)
    res = {}
    for (src, lba, idx, kind) in m.CONTAINERS:
        rows_a, body_a = m.payload_rows(ia, lba, idx, kind)
        rows_b, body_b = m.payload_rows(ib, lba, idx, kind)
        P('')
        P('[容器] %s  (LBA %d / idx %d / %s)' % (src, lba, idx, kind))
        P('  条目 %d (base %d) ; 解压 blob %d B (base %d)'
          % (len(rows_a), len(rows_b), len(body_a), len(body_b)))
        if len(rows_a) != len(rows_b):
            P('  ★ 条目数不同 ⇒ 未通过')
            res[src] = dict(rows=len(rows_a), rows_base=len(rows_b), ok=False)
            continue
        n_diff, first = 0, None
        for (ka, ba, _ra), (kb, bb, _rb) in zip(rows_a, rows_b):
            if ka != kb:
                n_diff += 1
                first = first or ('键序不一致 %s ≠ %s' % (kb, ka))
                continue
            if ba != bb:
                n_diff += 1
                if first is None:
                    k = next((j for j in range(min(len(ba), len(bb))) if ba[j] != bb[j]), 0)
                    first = ('%s: 基底 %s ≠ 产物 %s' % (ka, ba[max(0, k - 6):k + 6].hex(),
                                                      ba[max(0, k - 6):k + 6].hex()))
        P('  [1] 载荷**逐字节**相同: 不同条目 **%d** %s %s'
          % (n_diff, '✓' if not n_diff else '✗', first or ''))
        # 逐条全容器的裸码扫描 (把 body 也一起扫, 单列结构区)
        n_bare, per_bare, nb = bare_scan(body_a, base_gate, gate, pair_set)
        n_bare_rows = 0
        per_rows = collections.Counter()
        for (_k, ba, _r) in rows_a:
            k2, p2, _n2 = bare_scan(ba, base_gate, gate, pair_set)
            n_bare_rows += k2
            for kk, vv in p2.items():
                per_rows[kk] += vv
        P('  [2] ★ 载荷级裸旧码 (0xB1..0xB9 出现在**单字节位**): 条目口径 **%d 处** %s ; '
          '全 blob 口径 %d 处 (差 = 结构区/陈旧尾巴)'
          % (n_bare_rows, '✓ 达标' if not n_bare_rows else '✗', n_bare))
        P('      逐码明细 (条目口径): %s ; (全 blob): %s'
          % ({'0x%02X' % k: v for k, v in sorted(per_rows.items())},
             {'0x%02X' % k: v for k, v in per_bare.items()}))
        # [3] 全量解码
        s_body, nbad, kinds = full_decode(body_a, gate, pair_dec, codes)
        s_rows, nbad_r, kinds_r = full_decode(b''.join(ba for (_k, ba, _r) in rows_a),
                                              gate, pair_dec, codes)
        n_cjk = sum(1 for ch in s_rows if '\u4e00' <= ch <= '\u9fff')
        P('  [3] 全量解码 (新闸门 + 权威 charset): 未解析字节 **%d** %s (%s) ; '
          '解出字符 %d (CJK %d)'
          % (nbad_r, '✓' if not nbad_r else '✗', kinds_r or {}, len(s_rows), n_cjk))
        P('      样例 (前 %d 条非空):' % a.samples)
        shown = 0
        for (k3, ba, _r) in rows_a:
            if len(ba) < 6:
                continue
            t3, _nb, _kd = full_decode(ba, gate, pair_dec, codes)
            P('        %-12s %s' % (k3, t3[:70]))
            shown += 1
            if shown >= a.samples:
                break
        dup_pairs = collections.Counter()
        for (_k, ba, _r) in rows_a:
            i2, n2 = 0, len(ba)
            while i2 < n2:
                c = ba[i2]
                if 0xA1 <= c < gate and i2 + 1 < n2:
                    dup_pairs[ba[i2:i2 + 2].hex()] += 1
                    i2 += 2
                else:
                    i2 += 1
        P('      对偶码使用 top8: %s' % dup_pairs.most_common(8))
        res[src] = dict(rows=len(rows_a), rows_base=len(rows_b), row_bytes_diff=n_diff,
                        bare_rows=n_bare_rows, bare_rows_per={'0x%02X' % k: v for k, v in
                                                              sorted(per_rows.items())},
                        bare_blob=n_bare, unmapped=nbad_r, unmapped_kinds=kinds_r,
                        chars=len(s_rows), cjk=n_cjk,
                        ok=bool(n_diff == 0 and n_bare_rows == 0 and nbad_r == 0))
    ia.close(); ib.close()
    allok = all(v.get('ok') for v in res.values()) and len(res) == 3
    P('')
    P('=' * 100)
    P('[结论] 文本层: %s' % ('全部通过 ✓' if allok else '★有未通过项: %s'
                              % {k: v for k, v in res.items() if not v.get('ok')}))
    P('=' * 100)
    res['all_ok'] = bool(allok)
    with io.open(os.path.join(a.out, 'rel_text.json'), 'w', encoding='utf-8',
                 newline='\n') as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    with io.open(os.path.join(a.out, 'rel_text.txt'), 'w', encoding='utf-8',
                 newline='\n') as fh:
        fh.write('\n'.join(LOG) + '\n')
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
