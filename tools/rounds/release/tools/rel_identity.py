# -*- coding: utf-8 -*-
r"""rel_identity.py -- GR_RELEASE 交付候选的**身份/差异窗口/ELF 指纹**独立核对

    python work\builds\GR_RELEASE\tools\rel_identity.py ^
        --final work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso ^
        --src   work\builds\GR_COMBFIX\COMBFIX_2400.iso ^
        --base  work\builds\GR_REBUILD\GR_REBUILD2400.iso ^
        --meta  work\builds\GR_COMBFIX\COMBFIX_2400.meta.json ^
        --out   work\builds\GR_RELEASE\temp

本脚本**不复用** combfix_apply.py 的 diff 实现 (第二套独立实现):
  * 全文件分块按字节比较 (numpy uint8 布尔面), 逐块取非零位置拼成 (offset,len)
  * ELF 从 ISO9660 根目录记录里按名字取, 不信任任何常量 LBA
  * xor-CRC 与 sha256 自行实现 (与 PCSX2 ElfObject::GetCRC 的"逐 u32 异或"同式)

判据:
  [I1] 最终盘 == 候选盘 COMBFIX_2400.iso  逐字节 (0 差异)
  [I2] ISO 尺寸不变 (与 meta.base_bytes 相同)
  [I3] 最终盘 vs 基底 GR_REBUILD2400.iso: 差异 100% 落在 meta 声明的窗口内 (窗口外 0 字节)
  [I4] ELF sha256 / xor-CRC 与 meta 相符
  [I5] meta.gates_readback 的 4 个闸门字在盘上逐字相符
"""
import argparse
import hashlib
import io
import json
import os
import struct
import sys

import numpy as np

SEC = 2048
BLK = 1 << 22                     # 4 MiB
ISO_OF_VA = 0x6C780               # 工程既有常量: ISO 绝对偏移 = VA - 0x6C780


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    return s


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(BLK), b''):
            h.update(b)
    return h.hexdigest()


def md5_file(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(BLK), b''):
            h.update(b)
    return h.hexdigest()


def xor_crc(data):
    c = 0
    for (w,) in struct.iter_unpack('<I', data[:len(data) // 4 * 4]):
        c ^= w
    return c & 0xFFFFFFFF


def diff_runs(p1, p2, limit_report=40):
    """返回 (runs[(off,len)], n_diff_bytes, size1, size2); 独立实现."""
    runs = []
    n_diff = 0
    cur = None
    off = 0
    with open(p1, 'rb') as f1, open(p2, 'rb') as f2:
        while True:
            b1 = f1.read(BLK)
            b2 = f2.read(BLK)
            if not b1 and not b2:
                break
            n = max(len(b1), len(b2))
            if len(b1) != len(b2):
                return None, -1, None, None       # 尺寸不同 -> 由调用方登记
            a = np.frombuffer(b1, dtype=np.uint8)
            b = np.frombuffer(b2, dtype=np.uint8)
            idx = np.nonzero(a != b)[0]
            if idx.size:
                n_diff += int(idx.size)
                # 把本块内的差异位置合成连续 run, 并与上一块尾部的 run 相接
                holes = np.nonzero(np.diff(idx) > 1)[0]
                starts = np.concatenate(([0], holes + 1))
                ends = np.concatenate((holes, [idx.size - 1]))
                for s, e in zip(starts, ends):
                    so = off + int(idx[s])
                    eo = off + int(idx[e]) + 1
                    if cur is not None and cur[0] + cur[1] == so:
                        cur = (cur[0], cur[1] + (eo - so))
                        runs[-1] = cur
                    else:
                        cur = (so, eo - so)
                        runs.append(cur)
            else:
                cur = None
            off += n
    return runs, n_diff, os.path.getsize(p1), os.path.getsize(p2)


def iso_root_entries(path):
    with open(path, 'rb') as f:
        f.seek(16 * SEC)
        pvd = f.read(SEC)
        assert pvd[1:6] == b'CD001', '不是 ISO9660 的 PVD'
        rlba = struct.unpack_from('<I', pvd, 158)[0]
        rsz = struct.unpack_from('<I', pvd, 166)[0]
        f.seek(rlba * SEC)
        d = f.read(rsz)
    ents, off = [], 0
    while off < len(d) and d[off]:
        rl = d[off]
        nm = d[off + 33:off + 33 + d[off + 32]].decode('latin-1').split(';')[0]
        ents.append((nm.upper(), struct.unpack_from('<I', d, off + 2)[0],
                     struct.unpack_from('<I', d, off + 10)[0]))
        off += rl
    return ents


def read_elf(path, name='SLUS_206.13'):
    for (nm, lba, sz) in iso_root_entries(path):
        if nm == name.upper():
            with open(path, 'rb') as f:
                f.seek(lba * SEC)
                return f.read(sz), lba, sz
    raise SystemExit('ISO 里找不到 %s' % name)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--final', required=True)
    ap.add_argument('--src', required=True)
    ap.add_argument('--base', required=True)
    ap.add_argument('--meta', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    os.makedirs(a.out, exist_ok=True)
    meta = json.load(io.open(a.meta, encoding='utf-8'))

    res = {}
    P('=' * 100)
    P('rel_identity.py -- 交付候选身份核对')
    P('  final = %s' % os.path.abspath(a.final))
    P('  src   = %s' % os.path.abspath(a.src))
    P('  base  = %s' % os.path.abspath(a.base))
    P('=' * 100)

    # ── 尺寸 ──
    sz_f, sz_s, sz_b = (os.path.getsize(a.final), os.path.getsize(a.src),
                        os.path.getsize(a.base))
    P('[I2] 尺寸: final %d / src %d / base %d ; meta.base_bytes %d'
      % (sz_f, sz_s, sz_b, meta['base_bytes']))
    ok_size = (sz_f == sz_s == sz_b == meta['base_bytes'])
    P('     ISO 尺寸不变: %s' % ('✓' if ok_size else '✗'))
    res['size'] = dict(final=sz_f, src=sz_s, base=sz_b, meta=meta['base_bytes'],
                       unchanged=bool(ok_size))

    # ── 哈希 ──
    h_f, h_s, h_b = sha256_file(a.final), sha256_file(a.src), sha256_file(a.base)
    P('[I1] sha256(final) = %s' % h_f)
    P('     sha256(src)   = %s  (meta.sha256 %s)' % (h_s, meta['sha256']))
    P('     sha256(base)  = %s  (meta.base_sha256 %s)' % (h_b, meta['base_sha256']))
    P('     final == src : %s ; src == meta.sha256 : %s ; base == meta.base_sha256 : %s'
      % ('✓' if h_f == h_s else '✗', '✓' if h_s == meta['sha256'] else '✗',
         '✓' if h_b == meta['base_sha256'] else '✗'))
    res['sha256'] = dict(final=h_f, src=h_s, base=h_b,
                         final_eq_src=bool(h_f == h_s),
                         src_eq_meta=bool(h_s == meta['sha256']),
                         base_eq_meta=bool(h_b == meta['base_sha256']),
                         md5_final=md5_file(a.final))

    # ── [I1] final vs src 逐字节 ──
    runs_fs, nd_fs, _x, _y = diff_runs(a.final, a.src)
    P('[I1] final vs src 逐字节: 差异字节 **%d** %s (run 数 %d)'
      % (nd_fs, '✓ 完全一致' if nd_fs == 0 else '✗', len(runs_fs or [])))
    res['final_vs_src'] = dict(diff_bytes=nd_fs, runs=len(runs_fs or []))

    # ── [I3] final vs base 差异窗口 ──
    runs, nd, _p, _q = diff_runs(a.final, a.base)
    P('[I3] final vs base 全盘差异: **%d** 字节 / **%d** 个 run' % (nd, len(runs)))
    win = []
    for s in meta['sites']:
        o = int(s['iso_off'], 16)
        win.append((o, 4, s['name'] + ' site'))
    for c in meta['caves']:
        o = int(c['iso_off'], 16)
        win.append((o, c['bytes'], c['name'] + ' cave'))

    def classify(off, ln):
        hits = []
        for (wo, wl, wn) in win:
            lo, hi = wo, wo + wl
            if off < hi and (off + ln) > lo:
                hits.append(wn)
        return hits

    outside = []
    for (off, ln) in runs:
        hits = classify(off, ln)
        if not hits:
            outside.append((off, ln))
        P('     run @ 0x%08X len %-4d -> %s' % (off, ln, ','.join(hits) if hits else '★窗口外'))
    n_in = sum(ln for (off, ln) in runs if classify(off, ln))
    P('     落在声明窗口内的字节 = %d / %d ; 窗口外 = %d 字节 %s'
      % (n_in, nd, sum(ln for _o, ln in outside), '✓' if not outside else '✗'))
    res['final_vs_base'] = dict(diff_bytes=nd, runs=[dict(off=o, len=l) for o, l in runs],
                                in_window_bytes=n_in,
                                outside=[dict(off=o, len=l) for o, l in outside],
                                declared_windows=[dict(off=o, len=l, name=n) for o, l, n in win])

    # ── [I4] ELF 指纹 ──
    elf, lba, esz = read_elf(a.final)
    eh = hashlib.sha256(elf).hexdigest()
    ecrc = xor_crc(elf)
    P('[I4] final 的 ELF: lba=%d bytes=%d sha256=%s xorCRC=%08X'
      % (lba, esz, eh, ecrc))
    P('     vs meta: sha256 %s ; xorCRC %s ; lba %d ; bytes %d'
      % (meta['elf_sha256'], meta['elf_crc32_xor'], meta['base_elf_lba'], meta['base_elf_bytes']))
    ok_elf = (eh == meta['elf_sha256'] and ('%08X' % ecrc) == meta['elf_crc32_xor']
              and lba == meta['base_elf_lba'] and esz == meta['base_elf_bytes'])
    P('     ELF 指纹相符: %s' % ('✓' if ok_elf else '✗'))
    res['elf'] = dict(lba=lba, bytes=esz, sha256=eh, xor_crc='%08X' % ecrc,
                      match_meta=bool(ok_elf),
                      savestate_name='SLUS-20613 (%08X).01.p2s' % ecrc)

    # ── [I5] 闸门字回读 (站点字也一并回读) ──
    P('[I5] 站点/闸门字回读 (final 的 ELF, 按 VA 索引):')
    # VA → ISO 绝对偏移 = va - 0x6C780 (工程既有常量, 由 F4 站点 0x102588↔0x95E08 反证);
    # 再减 ELF 起 LBA*2048 得到 ELF 内文件偏移
    def word_at_va(va):
        return struct.unpack_from('<I', elf, va - ISO_OF_VA - lba * SEC)[0]
    bad = []
    for s in meta['sites']:
        va = int(s['va'], 16)
        w = '0x%08X' % word_at_va(va)
        okk = (w.upper() == s['new_word'].upper())
        if not okk:
            bad.append((s['name'], s['va'], w, s['new_word']))
        P('     %-8s %s = %s (期望 %s) %s' % (s['name'], s['va'], w, s['new_word'],
                                              '✓' if okk else '✗'))
    gate_bad = []
    for g in meta['gates_readback']:
        va_s, exp = g.split('=')
        va = int(va_s, 16)
        w = '0x%08X' % word_at_va(va)
        okk = (w.upper() == exp.upper())
        if not okk:
            gate_bad.append((va_s, w, exp))
        P('     gate %s = %s (期望 %s) %s' % (va_s, w, exp, '✓' if okk else '✗'))
    res['readback'] = dict(sites_bad=bad, gates_bad=gate_bad,
                           sites_ok=not bad, gates_ok=not gate_bad)

    allok = (res['sha256']['final_eq_src'] and res['sha256']['src_eq_meta']
             and res['sha256']['base_eq_meta'] and ok_size and nd_fs == 0
             and not outside and ok_elf and not bad and not gate_bad)
    P('')
    P('=' * 100)
    P('[结论] 身份/差异窗口/ELF 指纹: %s' % ('全部通过 ✓' if allok else '★有未通过项'))
    P('=' * 100)
    res['all_ok'] = bool(allok)
    with io.open(os.path.join(a.out, 'rel_identity.json'), 'w', encoding='utf-8',
                 newline='\n') as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    with io.open(os.path.join(a.out, 'rel_identity.txt'), 'w', encoding='utf-8',
                 newline='\n') as fh:
        fh.write('final=%s\nsha256=%s\nxor_crc=%s\nsize=%d\ndiff_vs_base=%d\noutside=%d\n'
                 % (os.path.abspath(a.final), h_f, res['elf']['xor_crc'], sz_f, nd,
                    sum(l for _o, l in outside)))
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
