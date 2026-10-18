# -*- coding: utf-8 -*-
r"""probe_inputs.py —— 【GR_SPINFIX / A】开工前对全部输入做只读取证 + 交叉核对。

读取（全部只读）：
  * 用户真机新 dump 的 ee_ram.bin（帧 23444，桶 126 已坏）
  * 用户真机旧 dump 的 ee_ram.bin（帧 19701，健康）—— 作为对照
  * 两份可用即时存档（CRC 7A761FCA）
  * 两个基底 ISO

输出：out/probe_inputs.txt / .json
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sf_common as C   # noqa: E402

ROOT = C.ROOT
DUMP_NEW = os.path.join(ROOT, r'work\builds\GR_HOOKEMU_QT2\qt\hookdumps\hook_23444_hotkey_f10')
DUMP_OLD = os.path.join(ROOT, r'work\builds\GR_HOOKEMU_QT2\qt\hookdumps\hook_19701_hotkey_f10')
STATE_USER = os.path.join(ROOT, r'work\builds\GR_LAYOUT\SLUS-20613 (7A761FCA).01.p2s')
STATE_OOM = os.path.join(ROOT, r'work\builds\GR_OOMFIX\common\state_LAY_fix1_bytecount.p2s')
BASES = {
    'lay1': os.path.join(ROOT, r'work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso'),
    '2400': os.path.join(ROOT, r'work\builds\GR_REBUILD\GR_REBUILD2400.iso'),
}
HEAP_BASE, HEAP_END = 0x0065AEA0, 0x01F98020
MSTATE = 0x0055B7A0


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    out = []

    def p(s=''):
        print(s)
        out.append(s)

    rep = {}

    # ── 1) 两份 dump 的 ee_ram.bin ──────────────────────────────────────────
    for tag, d in (('NEW_f23444', DUMP_NEW), ('OLD_f19701', DUMP_OLD)):
        f = os.path.join(d, 'ee_ram.bin')
        if not os.path.exists(f):
            p('[缺失] %s' % f)
            continue
        ram = open(f, 'rb').read()
        assert len(ram) == 32 << 20, len(ram)
        fd, bk = struct.unpack_from('<II', ram, 0x0055BB98)
        top, = struct.unpack_from('<I', ram, MSTATE + 8)
        rep[tag] = dict(path=f, bytes=len(ram), sha256=C.sha256_file(f),
                        bin126_fd='0x%08X' % fd, bin126_bk='0x%08X' % bk,
                        bin126_pseudo='0x%08X' % (0x0055B798 + 8 * 126),
                        top='0x%08X' % top)
        p('%-12s %s' % (tag, f))
        p('   sha256      = %s' % rep[tag]['sha256'])
        p('   桶126 伪chunk= 0x%08X   fd@0x0055BB98 = 0x%08X   bk@0x0055BB9C = 0x%08X  %s'
          % (0x0055B798 + 8 * 126, fd, bk,
             '健康(空桶自指)' if (fd == bk == 0x0055B798 + 8 * 126) else '★已坏'))
        p('   mstate->top = 0x%08X' % top)

        # 0x00500000..0x00580000 摘要（本项目要注入的窗口）
        win = ram[0x00500000:0x00580000]
        rep[tag]['win500_580_sha256'] = C.__dict__ and __import__('hashlib').sha256(win).hexdigest()
        rep[tag]['win500_580_nonzero'] = sum(1 for b in win if b)
        rep[tag]['binarray_sha256'] = __import__('hashlib').sha256(
            ram[0x0055B7A0:0x0055BBA8]).hexdigest()

    # ── 2) 两份 dump 的桶数组差异 ──────────────────────────────────────────
    if 'NEW_f23444' in rep and 'OLD_f19701' in rep:
        a = open(os.path.join(DUMP_OLD, 'ee_ram.bin'), 'rb').read()
        b = open(os.path.join(DUMP_NEW, 'ee_ram.bin'), 'rb').read()
        lo, hi = 0x0055B7A0, 0x0055BBA8
        diffs = [i for i in range(lo, hi) if a[i] != b[i]]
        p('\n[桶数组/mstate 0x0055B7A0..0x0055BBA8] 两 dump 不同字节数 = %d' % len(diffs))
        p('   不同偏移: %s' % ', '.join('0x%08X(old %02X -> new %02X)' % (i, a[i], b[i])
                                        for i in diffs[:32]))
        rep['binarray_diff_bytes'] = len(diffs)
        rep['binarray_diff_offsets'] = ['0x%08X' % i for i in diffs[:64]]

    # ── 3) 存档（p2s）里的 EE 主存原像 ──────────────────────────────────────
    z = C.load_zstd_tool()
    for tag, f in (('STATE_user_7A761FCA', STATE_USER), ('STATE_oomfix_copy', STATE_OOM)):
        if not os.path.exists(f):
            p('[缺失] %s' % f)
            continue
        ents = z.zip_entries(f)
        ee = [e for e in ents if e['name'] == 'eeMemory.bin']
        info = dict(path=f, bytes=os.path.getsize(f), sha256=C.sha256_file(f),
                    entries=len(ents),
                    ee_usize=(ee[0]['usize'] if ee else None))
        if ee:
            ram = z.decompress_entry(f, 'eeMemory.bin')
            fd, bk = struct.unpack_from('<II', ram, 0x0055BB98)
            top, = struct.unpack_from('<I', ram, MSTATE + 8)
            info.update(ee_sha256=__import__('hashlib').sha256(ram).hexdigest(),
                        bin126_fd='0x%08X' % fd, bin126_bk='0x%08X' % bk,
                        top='0x%08X' % top)
        rep[tag] = info
        p('\n%-22s %s' % (tag, f))
        p('   %d B  sha256=%s  zip 条目 %d' % (info['bytes'], info['sha256'], info['entries']))
        if ee:
            p('   eeMemory.bin %d B  sha256=%s' % (info['ee_usize'], info['ee_sha256']))
            p('   桶126 fd=%s bk=%s  top=%s  %s'
              % (info['bin126_fd'], info['bin126_bk'], info['top'],
                 '健康' if info['bin126_fd'] == info['bin126_bk'] == '0x0055BB88' else '★异常'))

    # ── 4) 基底 ISO + 站点原字 ────────────────────────────────────────────
    SITES = {
        'F1 0x00101DC0': (0x00101DC0, 0x00AA2823),
        'F1b 0x00101D60': (0x00101D60, 0x00A42823),
        'F2a 0x00101D38': (0x00101D38, 0xDCC90008),
        'F2b 0x00101D40': (0x00101D40, 0x14C70017),
        'F4 0x00102588': (0x00102588, 0x1459FFD1),
        'F5a 0x00101DC4': (0x00101DC4, 0x8CAA0010),
        'F5b 0x00101DC8': (0x00101DC8, 0x15490003),
        'F6a 0x00102010': (0x00102010, 0xACE50010),
        'F6b 0x00102014': (0x00102014, 0xAD250014),
    }
    for tag, f in BASES.items():
        elf, lba, size = C.read_elf_from_iso(f)
        info = dict(path=f, iso_sha256=C.sha256_file(f), bytes=os.path.getsize(f),
                    elf_lba=lba, elf_bytes=size,
                    elf_sha256=__import__('hashlib').sha256(elf).hexdigest(), sites={})
        p('\n%-6s %s' % (tag, f))
        p('   ISO %d B sha256=%s' % (info['bytes'], info['iso_sha256']))
        p('   ELF @LBA %d %d B sha256=%s' % (lba, size, info['elf_sha256']))
        for k, (va, want) in sorted(SITES.items()):
            got = C.word_at(elf, va, lba)
            ok = (got == want)
            info['sites'][k] = dict(va='0x%08X' % va, iso_off='0x%08X' % (va - C.ISO_OF_VA),
                                    elf_off='0x%07X' % C.elf_off(va, lba),
                                    word='0x%08X' % got, expect='0x%08X' % want, ok=bool(ok))
            p('   %-16s ISO 0x%08X  ELF 0x%07X  %08X  %s'
              % (k, va - C.ISO_OF_VA, C.elf_off(va, lba), got, 'OK' if ok else '★不符(期望 %08X)' % want))
        rep['base_' + tag] = info

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out',
                           'probe_inputs.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out',
                           'probe_inputs.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print('\n[out] out/probe_inputs.txt / .json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
