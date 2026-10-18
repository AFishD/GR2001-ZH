# -*- coding: utf-8 -*-
r"""fix_zh116_state_probe.py — 从用户即时存档的 eeMemory.bin 反推"盘代"

判据: 各代盘上的 LANG/SFXML 文本在**编码后**是不同的字节序列。
把每一代 `work/builds/<VER>/text/*_text_*.csv` 的 text_edited 编码成盘上字节,
在即时存档的 32 MB EE RAM 里搜 —— 命中最多的那一代就是用户当时在跑的盘。

用法:
  python tools/iso_build/fix_zh116_state_probe.py [--state <p2s>] [--versions GR_ZH98,...]
"""
import argparse
import io
import os
import sys
import zipfile

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib  # noqa: E402

DEFAULT_STATE = os.path.join(REPO, 'work', 'temp', 'SLUS-20613 (7A361FB5).01.p2s')
BUILDS = os.path.join(REPO, 'work', 'builds')
KINDS = ('long', 'long_nowrap', 'short')


def load_state_ram(path):
    if path.lower().endswith('.bin'):
        with open(path, 'rb') as f:
            return f.read()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fix_zh116_p2s
    return fix_zh116_p2s.read_entry(path, 'eeMemory.bin')


def load_version_rows(ver):
    """→ {id: (text, kind)} (只读 3 张可注入表)"""
    out = {}
    tdir = os.path.join(BUILDS, ver, 'text')
    for kind in KINDS:
        p = os.path.join(tdir, '%s_text_%s.csv' % (ver, kind))
        if not os.path.isfile(p):
            continue
        rows, _cols = tcslib.read_table_rows(p)
        for r in rows:
            rid = (r.get('id') or '').strip()
            txt = r.get('text_edited') or ''
            if rid and txt:
                out[rid] = (txt, kind)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--state', default=DEFAULT_STATE)
    ap.add_argument('--versions', default=None)
    ap.add_argument('--min-bytes', type=int, default=6)
    ap.add_argument('--top', type=int, default=40)
    a = ap.parse_args()

    ram = load_state_ram(a.state)
    print('state = %s' % a.state)
    print('eeMemory.bin = %d B' % len(ram))

    if a.versions:
        vers = [v.strip() for v in a.versions.split(',') if v.strip()]
    else:
        vers = sorted([d for d in os.listdir(BUILDS)
                       if d.startswith('GR_') and os.path.isdir(os.path.join(BUILDS, d, 'text'))],
                      key=lambda s: (len(s), s))

    cs = tcslib.Charset()
    enc_cache = {}

    def enc(txt):
        if txt in enc_cache:
            return enc_cache[txt]
        try:
            b = cs.encode_strict(txt)
        except Exception:
            b = None
        enc_cache[txt] = b
        return b

    per_ver = {}
    id_text = {}
    for v in vers:
        rows = load_version_rows(v)
        id_text[v] = rows
        hit = 0
        tot = 0
        hitbytes = 0
        for rid, (txt, kind) in rows.items():
            b = enc(txt)
            if not b or len(b) < a.min_bytes:
                continue
            tot += 1
            if ram.find(b) >= 0:
                hit += 1
                hitbytes += len(b)
        per_ver[v] = (hit, tot, hitbytes)

    print('\n%-12s %8s %8s %10s %8s' % ('version', 'hit', 'tested', 'hitbytes', 'rate'))
    for v in vers:
        hit, tot, hb = per_ver[v]
        print('%-12s %8d %8d %10d %7.1f%%' % (v, hit, tot, hb, (100.0 * hit / tot) if tot else 0.0))

    # 逐 id 判别: 只挑"各代文本不同、且有字节可在 RAM 找到"的 id
    print('\n=== 判别性 id (各代文本不同) ===')
    allids = set()
    for v in vers:
        allids |= set(id_text[v].keys())
    rows_diff = []
    for rid in sorted(allids):
        texts = {}
        for v in vers:
            t = id_text[v].get(rid)
            if t:
                texts[v] = t[0]
        if len(set(texts.values())) < 2:
            continue
        present = []
        for v, t in texts.items():
            b = enc(t)
            if b and len(b) >= 4 and ram.find(b) >= 0:
                present.append(v)
        if present:
            rows_diff.append((rid, present, texts))
    print('各代文本不同、且至少有 1 代字节在 RAM 里命中: %d 条' % len(rows_diff))
    for rid, present, texts in rows_diff[:a.top]:
        who = ','.join(present)
        uniq = sorted(set(texts.values()))
        print('  %-22s RAM命中: %-40s 变体: %s' % (rid, who, ' | '.join(uniq)))

    # 汇总: 每条判别性 id "支持" 哪些代
    from collections import Counter
    c = Counter()
    for rid, present, texts in rows_diff:
        for p in present:
            c[p] += 1
    print('\n判别性 id 支持计数: %s' % dict(c.most_common()))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
