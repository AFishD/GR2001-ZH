# -*- coding: utf-8 -*-
r"""oomfix_analyze.py —— 读一个 GR_OOMFIX run 目录，出「Trap / 低端写入 / hook / watch」读数。

用法: python oomfix_analyze.py <rundir> [--json out.json]

判据（任务书 B）:
  * `Trap exception at 0x80000274` 行数与首次出现
  * `EE: Unrecognized op` 行数
  * `-grwatch` 各区的命中数（0x1300=4864 / 0x1000=4096）与首次命中
  * `-grhook` 每个 PC 的命中数与首条寄存器现场
"""
import argparse
import json
import os
import re
import sys

TRAP_RE = re.compile(r'Trap exception at (0x[0-9A-Fa-f]+)')
OP_RE = re.compile(r'Unrecognized op')
FRAME_RE = re.compile(r'\[\s*([0-9]+\.[0-9]+)\]')
WATCH_RE = re.compile(r'^hit (\d+) frame=(\d+) cycle=(\d+) addr=([0-9A-F]+) size=(\d+) '
                      r'writer_block=([0-9A-F]+) cur_block=([0-9A-F]+) old=(\S*) new=(\S*)')
HOOK_RE = re.compile(r'^hook pc=([0-9A-F]+) frame=(\d+) cycle=(\d+) a0=([0-9A-F]+) a1=([0-9A-F]+) '
                     r'a2=([0-9A-F]+) a3=([0-9A-F]+) v0=([0-9A-F]+) s0=([0-9A-F]+) '
                     r's1=([0-9A-F]+) ra=([0-9A-F]+) sp=([0-9A-F]+)')


def scan_emulog(path, cap_lines=None):
    traps, ops, first_trap_line, first_trap_frame = 0, 0, None, None
    frames = []
    n = 0
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for ln, line in enumerate(f, 1):
            n = ln
            if 'Trap exception' in line:
                traps += 1
                m = TRAP_RE.search(line)
                frames.append(m.group(1) if m else '?')
                if first_trap_line is None:
                    first_trap_line = ln
                    fm = FRAME_RE.search(line)
                    first_trap_frame = fm.group(1) if fm else None
            elif 'Unrecognized op' in line:
                ops += 1
            if cap_lines and ln >= cap_lines:
                break
    uniq = sorted(set(frames))
    return dict(lines_scanned=n, trap_lines=traps, unrecognized_op_lines=ops,
                first_trap_line=first_trap_line, first_trap_frame=first_trap_frame,
                trap_addr_unique=uniq)


def scan_watch(path):
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            m = WATCH_RE.match(line)
            if not m:
                continue
            hits, frame, cycle, addr, size, wblk, cblk, old, new = m.groups()
            r = out.setdefault(addr, dict(addr=addr, size=int(size), hits=0,
                                          first=None, last=None, writers=set(), frames=[]))
            r['hits'] += 1
            r['writers'].add(wblk)
            rec = dict(hit=int(hits), frame=int(frame), cycle=int(cycle),
                       writer_block=wblk, cur_block=cblk, old=old, new=new)
            if r['first'] is None:
                r['first'] = rec
            r['last'] = rec
            if len(r['frames']) < 80:
                r['frames'].append(int(frame))
    for r in out.values():
        r['writers'] = sorted(r['writers'])
    return out


def scan_hook(path):
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            m = HOOK_RE.match(line)
            if not m:
                continue
            pc = m.group(1)
            r = out.setdefault(pc, dict(pc=pc, hits=0, first=None, frames=[],
                                       v0_values={}, ra_values={}))
            r['hits'] += 1
            rec = dict(frame=int(m.group(2)), cycle=int(m.group(3)),
                       a0=m.group(4), a1=m.group(5), a2=m.group(6), a3=m.group(7),
                       v0=m.group(8), s0=m.group(9), s1=m.group(10), ra=m.group(11),
                       sp=m.group(12))
            if r['first'] is None:
                r['first'] = rec
            if len(r['frames']) < 60:
                r['frames'].append(rec['frame'])
            r['v0_values'][rec['v0']] = r['v0_values'].get(rec['v0'], 0) + 1
            r['ra_values'][rec['ra']] = r['ra_values'].get(rec['ra'], 0) + 1
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('rundir')
    ap.add_argument('--json', default=None)
    ap.add_argument('--caps', type=int, default=0)
    a = ap.parse_args()
    d = a.rundir
    rep = dict(rundir=os.path.abspath(d))
    el = os.path.join(d, 'emulog.txt')
    rep['emulog_bytes'] = os.path.getsize(el) if os.path.exists(el) else 0
    if rep['emulog_bytes']:
        rep['emulog'] = scan_emulog(el, a.caps or None)
    rep['watch'] = scan_watch(os.path.join(d, 'watch.txt'))
    rep['hook'] = scan_hook(os.path.join(d, 'hooklog.txt'))
    pc = os.path.join(d, 'pcsample.txt')
    if os.path.exists(pc):
        lines = open(pc, encoding='utf-8', errors='replace').read().splitlines()
        rep['pcsample'] = dict(n=len(lines), head=lines[:6], tail=lines[-6:])
    rep['ram_dumps'] = sorted(n for n in os.listdir(d) if n.endswith('_eeram.bin'))
    rep['snaps'] = sorted(n for n in os.listdir(d) if n.startswith('snap_f'))

    print('== %s' % rep['rundir'])
    if 'emulog' in rep:
        e = rep['emulog']
        print('   emulog %.1f MB / %d 行：Trap %d 行（首行 %s，首个 Trap 地址 %s）'
              % (rep['emulog_bytes'] / 1e6, e['lines_scanned'], e['trap_lines'],
                 e['first_trap_line'], e['trap_addr_unique']))
        print('   EE: Unrecognized op  %d 行' % e['unrecognized_op_lines'])
    for addr, r in sorted(rep['watch'].items()):
        print('   watch %s size=%d : %d 命中；首次 frame=%s old=%s new=%s writer=%s；写者 %s'
              % (addr, r['size'], r['hits'],
                 r['first']['frame'] if r['first'] else '-',
                 r['first']['old'] if r['first'] else '-',
                 r['first']['new'] if r['first'] else '-',
                 r['first']['writer_block'] if r['first'] else '-', r['writers']))
    for pc_, r in sorted(rep['hook'].items()):
        print('   hook %s : %d 次；v0 取值 %s；ra 取值 %s'
              % (pc_, r['hits'], r['v0_values'], r['ra_values']))
        if r['first']:
            print('        首条 frame=%d cycle=%d %s' % (r['first']['frame'], r['first']['cycle'],
                                                         {k: r['first'][k] for k in
                                                          ('a0', 'a1', 'a2', 'a3', 'v0', 's0', 's1', 'ra', 'sp')}))
    if 'pcsample' in rep:
        print('   pcsample %d 行；尾 %s' % (rep['pcsample']['n'], rep['pcsample']['tail'][-3:]))
    print('   RAM dump: %s' % rep['ram_dumps'])
    print('   snap: %d 张' % len(rep['snaps']))
    if a.json:
        json.dump(rep, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('[json] %s' % a.json)


if __name__ == '__main__':
    main()
