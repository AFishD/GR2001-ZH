# -*- coding: utf-8 -*-
r"""fix_zh116_elf_fp.py — 用 ELF 字节给即时存档的 EE RAM 做"盘代指纹"

原理: PS2 ELF 的主段被原样搬进 EE RAM (VA 0x100000 ⇒ 物理 0x00100000)。
各代盘的 `SLUS_206.13` 在补丁点(ELF cave / 字库表 / 重编码)上**字节不同**,
所以拿"各代互相不同的那些偏移"去问 RAM: 哪一代的字节与 RAM 一致 ⇒ 用户跑的就是那一代。

用法:
  python tools/iso_build/fix_zh116_elf_fp.py --ram work/builds/GR_ZH116/tmp/eeMemory.bin [--versions ...]
"""
import argparse
import os
import struct
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib  # noqa: E402

BUILDS = os.path.join(REPO, 'work', 'builds')
ELF_LBA = 295
ELF_SIZE = 37453732
RAM_BASE_VA = 0x00100000


def elf_bytes(ver):
    iso = os.path.join(BUILDS, ver, '%s.iso' % ver)
    if not os.path.isfile(iso):
        return None
    f = tcslib.Iso(iso)
    try:
        return f.read(ELF_LBA * 2048, ELF_SIZE)
    finally:
        f.close()


def prog_headers(elf):
    e_phoff = struct.unpack_from('<I', elf, 0x1C)[0]
    e_phnum = struct.unpack_from('<H', elf, 0x2C)[0]
    out = []
    for i in range(e_phnum):
        o = e_phoff + i * 32
        p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz = struct.unpack_from('<IIIIII', elf, o)
        out.append(dict(type=p_type, off=p_offset, vaddr=p_vaddr, paddr=p_paddr,
                        filesz=p_filesz, memsz=p_memsz))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ram', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH116', 'tmp', 'eeMemory.bin'))
    ap.add_argument('--versions', default='GR_ZH98,GR_ZH101,GR_ZH105,GR_ZH109,GR_ZH111,GR_ZH112,GR_ZH113,GR_ZH114,GR_ZH115')
    ap.add_argument('--control', default='GR_EN_ORIG')
    ap.add_argument('--max-report', type=int, default=12)
    a = ap.parse_args()

    ram = open(a.ram, 'rb').read()
    print('RAM = %s (%d B)' % (a.ram, len(ram)))

    vers = [v.strip() for v in a.versions.split(',') if v.strip()]
    if a.control:
        vers.append(a.control)

    elfs = {}
    for v in vers:
        b = elf_bytes(v)
        if b is None:
            print('!! 缺 ISO: %s' % v)
            continue
        elfs[v] = b

    base_v = 'GR_ZH111' if 'GR_ZH111' in elfs else list(elfs)[0]
    ph = prog_headers(elfs[base_v])
    print('\n%s program headers:' % base_v)
    for p in ph:
        print('   type=%d off=%08X vaddr=%08X paddr=%08X filesz=%d' %
              (p['type'], p['off'], p['vaddr'], p['paddr'], p['filesz']))

    seg = next((p for p in ph if p['type'] == 1 and p['filesz'] > 0x100000), ph[0])
    off0, va0, sz = seg['off'], seg['vaddr'], seg['filesz']
    # EE RAM 索引 = 段的 p_paddr (实测: ELF[0x80] == RAM[0x00100000], 逐字节 100%)
    map_off = seg['paddr']
    print('主段: ELF[%d:%d] <-> RAM[%08X:]  (paddr=%08X)' % (off0, off0 + sz, map_off, seg['paddr']))

    # 1) 整体一致率 (以 GR_ZH111 为参照)
    for v in elfs:
        b = elfs[v]
        n = min(sz, len(ram) - map_off, len(b) - off0)
        step = 1
        eq = 0
        tot = 0
        for i in range(0, n, step):
            tot += 1
            if ram[map_off + i] == b[off0 + i]:
                eq += 1
        print('  %-12s 与 RAM 逐字节相同: %6d/%6d = %5.2f%%' % (v, eq, tot, 100.0 * eq / tot))

    # 2) 判别性偏移: 各代互相不同的位置
    vs = sorted(elfs)
    diff_off = []
    n = min(sz, len(ram) - map_off)
    for i in range(n):
        s = {elfs[v][off0 + i] for v in vs}
        if len(s) > 1:
            diff_off.append(i)
    print('\n各代 ELF 互相不同的偏移: %d 个' % len(diff_off))
    if diff_off:
        print('  前 20 个: %s' % ['%08X' % (off0 + i) for i in diff_off[:20]])
        print('  末 20 个: %s' % ['%08X' % (off0 + i) for i in diff_off[-20:]])

    score = {}
    for v in vs:
        m = 0
        for i in diff_off:
            if ram[map_off + i] == elfs[v][off0 + i]:
                m += 1
        score[v] = m
    print('\n=== 判别性偏移命中 (越高越是用户那一代) ===')
    for v, m in sorted(score.items(), key=lambda kv: -kv[1]):
        pct = (100.0 * m / len(diff_off)) if diff_off else 0.0
        print('  %-12s %7d / %d = %5.1f%%' % (v, m, len(diff_off), pct))

    # 3) 逐 64KB 块: 每个块里 RAM 最像哪一代
    print('\n=== 逐 64KB 块归属 (只列有分歧的块) ===')
    B = 1 << 16
    blocks = {}
    for i in diff_off:
        blocks.setdefault(i // B, []).append(i)
    rows = []
    for blk, offs in sorted(blocks.items()):
        best = None
        for v in vs:
            m = sum(1 for i in offs if ram[map_off + i] == elfs[v][off0 + i])
            if best is None or m > best[1]:
                best = (v, m)
        # 该块里所有代是否都给同一答案
        scores = {v: sum(1 for i in offs if ram[map_off + i] == elfs[v][off0 + i]) for v in vs}
        top = sorted(scores.items(), key=lambda kv: -kv[1])
        rows.append((blk, len(offs), top))
    for blk, cnt, top in rows[:a.max_report]:
        print('  RAM[%08X] 分歧%6d 字节: %s' %
              (map_off + blk * B, cnt, ', '.join('%s=%d' % (v, m) for v, m in top[:4])))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
