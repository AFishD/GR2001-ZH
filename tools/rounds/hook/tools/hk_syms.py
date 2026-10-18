# -*- coding: utf-8 -*-
r"""hk_syms.py — 把两份 emulog 的故障 PC 归到函数, 并核对 EN/ZH 该 PC 的机器码是否相同.

只读: third_party\orig\ps2\slus_out\SLUS_206.13 (EN 原盘 ELF), GR_ZH113b.iso 内的 ELF.
"""
import io
import json
import os
import re
import struct
import sys

ROOT = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(ROOT, r'tools\rounds\nullhunt\tools'))
import nh_elf  # noqa: E402

ELF_ISO_OFF = 0x93800
ELF_LEN = 37453732
EN_ELF = os.path.join(ROOT, r'third_party\orig\ps2\slus_out\SLUS_206.13')

LOGS = {
    'ZH113b': os.path.join(ROOT, r'work\builds\GR_ZH113b\emulog.txt'),
    'CVAR_04': os.path.join(ROOT, r'work\builds\GR_CVAR\CVAR_04_emulog.txt'),
}


def load_zh_elf():
    p = os.path.join(ROOT, r'work\builds\GR_ZH113b\GR_ZH113b.iso')
    with open(p, 'rb') as f:
        f.seek(ELF_ISO_OFF)
        return f.read(ELF_LEN)


def parse_log(path):
    """→ list of dict(ts, kind, pc, addr, op)"""
    out = []
    rx_tlb = re.compile(r'\[\s*([\d.]+)\]\s+TLB Miss, pc=(0x[0-9a-fA-F]+)\s+addr=(0x[0-9a-fA-F]+)\s+\[(\w+)\]')
    rx_trap = re.compile(r'\[\s*([\d.]+)\]\s+Trap exception at (0x[0-9a-fA-F]+)')
    rx_unmap = re.compile(r'\[\s*([\d.]+)\]\s+ReportErrorAsync: R5900 Exception: (.+)$')
    with io.open(path, 'r', encoding='utf-8', errors='replace') as f:
        for ln in f:
            m = rx_tlb.search(ln)
            if m:
                out.append(dict(ts=float(m.group(1)), kind='tlb', pc=int(m.group(2), 16),
                                addr=int(m.group(3), 16), op=m.group(4)))
                continue
            m = rx_trap.search(ln)
            if m:
                out.append(dict(ts=float(m.group(1)), kind='trap', pc=int(m.group(2), 16)))
                continue
            m = rx_unmap.search(ln)
            if m:
                out.append(dict(ts=float(m.group(1)), kind='unmapped', msg=m.group(2).strip()))
    return out


def main():
    en = nh_elf.Elf(open(EN_ELF, 'rb').read(), 'EN')
    zh = nh_elf.Elf(load_zh_elf(), 'ZH')

    report = {'elf_phdrs': en.report_phdrs(), 'logs': {}}
    lines = []
    lines.append('ELF(EN) %s' % en.report_phdrs().replace('\n', '\n         '))
    lines.append('')

    allpc = {}
    for tag, path in LOGS.items():
        ev = parse_log(path)
        report['logs'][tag] = dict(
            n_tlb=sum(1 for e in ev if e['kind'] == 'tlb'),
            n_trap=sum(1 for e in ev if e['kind'] == 'trap'),
            n_unmapped=sum(1 for e in ev if e['kind'] == 'unmapped'),
            events=[dict(kind=e['kind'], ts=e['ts'],
                         pc=(hex(e['pc']) if 'pc' in e else None),
                         addr=(hex(e['addr']) if 'addr' in e else None),
                         op=e.get('op'), msg=e.get('msg')) for e in ev])
        pcs = {}
        for e in ev:
            if e['kind'] != 'tlb':
                continue
            pcs.setdefault(e['pc'], dict(n=0, addrs=set(), ops=set(), ts=[]))
            d = pcs[e['pc']]
            d['n'] += 1
            d['addrs'].add(e['addr'])
            d['ops'].add(e['op'])
            d['ts'].append(e['ts'])
        lines.append('=' * 78)
        lines.append('%s  (%s)' % (tag, os.path.basename(path)))
        lines.append('  TLB=%d Trap=%d unmapped=%d   distinct TLB pc=%d'
                     % (report['logs'][tag]['n_tlb'], report['logs'][tag]['n_trap'],
                        report['logs'][tag]['n_unmapped'], len(pcs)))
        for pc in sorted(pcs):
            d = pcs[pc]
            s = en.sym_at(pc)
            sym = ('%s +0x%X' % (s['name'], pc - s['value'])) if s else '?'
            off, ph = en.va2off(pc)
            enw = struct.unpack_from('<I', en.b, off)[0] if off is not None else None
            zoff, _ = zh.va2off(pc)
            zhw = struct.unpack_from('<I', zh.b, zoff)[0] if zoff is not None else None
            same = (enw == zhw)
            lines.append('  pc=0x%08X x%-3d %-58s EN/ZH %s' % (pc, d['n'], sym, 'SAME' if same else 'DIFF'))
            lines.append('        EN: %s' % (nh_elf.mips_dis1(enw, pc) if enw is not None else 'n/a'))
            if not same:
                lines.append('        ZH: %s' % (nh_elf.mips_dis1(zhw, pc) if zhw is not None else 'n/a'))
            lines.append('        addr: %s   op: %s   ts: %s'
                         % (', '.join(sorted(hex(a) for a in d['addrs'])), ','.join(sorted(d['ops'])),
                            ','.join('%.4f' % t for t in d['ts'][:6])))
            allpc[pc] = allpc.get(pc, 0) + d['n']
        lines.append('  terminal:')
        for e in ev:
            if e['kind'] != 'tlb':
                lines.append('    [%.4f] %s  %s' % (e['ts'], e['kind'],
                                                    e.get('msg') or hex(e['pc'])))
        lines.append('')

    # ---- 集合对比 ----
    sets = {}
    for tag in LOGS:
        sets[tag] = set(int(e['pc'], 16) for e in report['logs'][tag]['events'] if e['kind'] == 'tlb')
    inter = sets['ZH113b'] & sets['CVAR_04']
    lines.append('=' * 78)
    lines.append('## PC 集合对比')
    for tag in ('ZH113b', 'CVAR_04'):
        lines.append('  %-8s 唯一 TLB-fault PC = %s' % (tag, sorted(hex(p) for p in sets[tag])))
    lines.append('  交集 (ZH113b ∩ CVAR_04) = %s' % (sorted(hex(p) for p in inter) or '空集 ∅'))
    lines.append('  ZH113b 独有 = %s' % sorted(hex(p) for p in sets['ZH113b'] - sets['CVAR_04']))
    lines.append('  CVAR_04 独有 = %s' % sorted(hex(p) for p in sets['CVAR_04'] - sets['ZH113b']))
    lines.append('')
    lines.append('## 故障 PC 的函数归属 (EN 符号表)')
    for tag in ('ZH113b', 'CVAR_04'):
        lines.append('  -- %s' % tag)
        for pc in sorted(sets[tag]):
            s = en.sym_at(pc)
            lines.append('     0x%08X  %s' % (pc, ('%s +0x%X' % (s['name'], pc - s['value'])) if s else '?'))
    lines.append('')
    lines.append('## 终端形态')
    for tag in ('ZH113b', 'CVAR_04'):
        lines.append('  -- %s : Trap=%d  unmapped=%d'
                     % (tag, report['logs'][tag]['n_trap'], report['logs'][tag]['n_unmapped']))
        for e in report['logs'][tag]['events']:
            if e['kind'] != 'tlb':
                lines.append('     [%s] %s %s' % (e['ts'], e['kind'], e.get('msg') or e.get('pc')))

    txt = '\n'.join(lines)
    out = os.path.join(ROOT, r'work\builds\GR_HOOK\evidence\hk_pc_symbols.txt')
    with io.open(out, 'w', encoding='utf-8') as f:
        f.write(txt)
    with io.open(os.path.join(ROOT, r'work\builds\GR_HOOK\evidence\hk_pc_events.json'),
                 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1)
    print('wrote hk_pc_symbols.txt (%d chars) and hk_pc_events.json' % len(txt))
    print('INTERSECTION =', sorted(hex(p) for p in inter) or 'EMPTY')

if __name__ == '__main__':
    main()
