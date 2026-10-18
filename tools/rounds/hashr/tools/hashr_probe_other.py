# -*- coding: utf-8 -*-
r"""hashr_probe_other.py — 3 个中文容器**之外**是否还有这 42 个哨兵字 (只读)

判据 (严格): 命中点 ±24 字节用**旧 charset** 按 lead/trail 规则解码 ⇒ 解码结果里
CJK (U+4E00..U+9FFF) 个数 ≥ 3 且占比 ≥ 0.6 才算「真文本」。
另: 单列 IGORHELP.TXT / ELF 的读数。

输出: work/builds/GR_HASHR/audit/probe_other.txt
"""
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                       # noqa: E402
import zx_lib                                                            # noqa: E402
import migrate_legacy as ML                                              # noqa: E402

K2 = os.path.join(REPO, 'work', 'builds', 'GR_FA2400_K2', 'GR_FA2400_K2.iso')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
SENT = (0xB1, 0xB5)
OUT = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    OUT.append(s)


def decode_window(data, gate, pair_dec, lo, hi):
    """按 lead/trail 规则解码 [lo,hi) → (字符串, 无法解码字节数)。"""
    s, bad, i = [], 0, lo
    while i < hi:
        b = data[i]
        if T.LEAD_LO <= b < gate:
            t = data[i + 1] if i + 1 < hi else None
            if t is not None and (b, t) in pair_dec:
                s.append(pair_dec[(b, t)])
                i += 2
                continue
            bad += 1
            i += 1
            continue
        if 0x20 <= b < 0x7F:
            s.append(chr(b))
        else:
            bad += 1
        i += 1
    return ''.join(s), bad


def is_cjk(ch):
    return 0x4E00 <= ord(ch) <= 0x9FFF


def strict_hits(data, gate, pair_dec, patterns, where, win=24, mincjk=3, ratio=0.6):
    out = []
    for pat in patterns:
        pb = bytes(pat)
        start = 0
        while True:
            k = data.find(pb, start)
            if k < 0:
                break
            start = k + 1
            s, bad = decode_window(data, gate, pair_dec, max(0, k - win),
                                   min(len(data), k + 2 + win))
            nch = len(s)
            ncjk = sum(1 for c in s if is_cjk(c))
            if ncjk >= mincjk and nch and ncjk / nch >= ratio:
                out.append(dict(where=where, off=k, pair=list(pat), text=s, n_unmapped=bad))
    return out


def main():
    j = json.load(io.open(CS, encoding='utf-8'))
    pair_of = {ch: tuple(v) for ch, v in j['pair_of'].items()}
    pair_dec = {tuple(v): ch for ch, v in j['pair_of'].items()}
    iso = T.Iso(K2)
    gate = T.read_decode_gate(iso)
    P('gate = 0x%02X' % gate)
    sent = sorted([p for p in pair_dec if p[1] in SENT])
    P('哨兵对偶码 %d 个' % len(sent))
    # ── 7 个容器的用量 (确认「3 容器未用到」的那 10 个字在其他容器里的用量) ──
    used = collections.Counter()
    for (kind, img, lba, idx, tag, why) in ML.CONTAINER_SPECS:
        e = iso.img_entry(lba, idx)
        blob = b''.join(s[0] for s in T.lzo_subs(iso.read(e['iso_off'], e['stored'])))
        c = dict(name=kind, tag=tag, blob=blob)
        ranges, _u, _i = ML.payload_ranges(c)
        for (s, ee) in ranges:
            txt, _bad = decode_window(blob, gate, pair_dec, s, ee)
            for ch in txt:
                if ch in pair_of:
                    used[ch] += 1
    unused = sorted([ch for p, ch in pair_dec.items() if p[1] in SENT and used[ch] == 0],
                    key=lambda c: T.pair_slot(*pair_of[c]))
    P('哨兵字里「7 容器用量 = 0」的 %d 个: %s' % (len(unused), ' '.join(unused)))
    # ── 全 IMG (除 COMMON.PAK) + ELF 严格扫描 ──
    ents = []
    for lba, nm in ((zx_lib.MENU_LBA, 'MENU.IMG'), (zx_lib.GR_LBA, 'GR.IMG')):
        for e in zx_lib.entries(iso, lba):
            ents.append((nm, e))
    P('IMG 条目 %d 个' % len(ents))
    allhits = []
    per_where = collections.Counter()
    for (nm, e) in ents:
        data = iso.read(e['iso_off'], e['stored'])
        hs = strict_hits(data, gate, pair_dec, sent, '%s:%s' % (nm, e['name']))
        if hs:
            per_where['%s:%s' % (nm, e['name'])] = len(hs)
            allhits.extend(hs)
    elf = iso.read(295 * 2048, 37453732)
    hs = strict_hits(elf, gate, pair_dec, sent, 'SLUS_206.13(ELF)')
    if hs:
        per_where['SLUS_206.13(ELF)'] = len(hs)
        allhits.extend(hs)
    P('')
    P('=== 严格口径 (≥3 CJK 且占比 ≥0.6) 的容器外命中: %d 处 ===' % len(allhits))
    for w, n in per_where.most_common():
        P('   %-40s %d 处' % (w, n))
    for h in allhits[:40]:
        P('   %-32s @0x%06X %02X%02X  %r' % (h['where'], h['off'], h['pair'][0],
                                             h['pair'][1], h['text']))
    # ── 只关心那 10 个零用量字 ──
    P('')
    P('=== 零用量字在容器外的严格命中 ===')
    for ch in unused:
        pr = pair_of[ch]
        hit = [h for h in allhits if tuple(h['pair']) == pr]
        P('   %s %02X%02X slot=%-5d : %d 处 %s'
          % (ch, pr[0], pr[1], T.pair_slot(*pr), len(hit),
             ' '.join('%s@0x%X' % (h['where'], h['off']) for h in hit[:6])))
    # ── IGORHELP.TXT / *_STRINGS.TXT 单列 ──
    P('')
    P('=== IGORHELP.TXT / *_STRINGS.TXT 单列 ===')
    for (nm, e) in ents:
        if not e['name'].upper().endswith('.TXT'):
            continue
        data = iso.read(e['iso_off'], e['stored'])
        txt, bad = decode_window(data, gate, pair_dec, 0, len(data))
        ncjk = sum(1 for c in txt if is_cjk(c))
        nsent = sum(1 for p in sent if data.count(bytes(p)))
        P('   %-40s %8d B  CJK %5d  不可解 %6d  哨兵码模式命中 %d'
          % ('%s:%s' % (nm, e['name']), len(data), ncjk, bad, nsent))
    iso.close()
    with io.open(os.path.join(REPO, 'work', 'builds', 'GR_HASHR', 'audit',
                              'probe_other.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(OUT) + '\n')


if __name__ == '__main__':
    main()
