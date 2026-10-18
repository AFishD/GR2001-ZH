# -*- coding: utf-8 -*-
r"""spinfix_analyze.py —— 【GR_SPINFIX】读一个 run 的产物：TLB Miss / Trap / 帧数 / 首个 TLB / 钩子摘要。

用法:
  python spinfix_analyze.py <rundir> [--json out.json] [--trim-mb 8]

--trim-mb：若 emulog.txt 大于该值，抽出「前 3000 行 + 后 200 行」写成 emulog_sample.txt、
          统计完就删掉原日志（磁盘纪律），并在 JSON 里记 trimmed=true。
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, OrderedDict

TLB_RE = re.compile(r'TLB Miss, pc=(0x[0-9a-fA-F]+) addr=(0x[0-9a-fA-F]+) \[(\w+)\]')
TS_RE = re.compile(r'^\s*\[\s*([0-9.]+)\](.*)$')


def analyze(rundir, trim_mb=8.0):
    el = os.path.join(rundir, 'emulog.txt')
    rep = dict(rundir=os.path.abspath(rundir), emulog=el)
    tlb = Counter()          # (pc, addr, kind) -> n
    tlb_lines = 0
    tlb_first = []
    trap = 0
    op = 0
    pausing = 0
    run_end = None
    first_tlb_ts = None
    last_tlb_ts = None
    lines = 0
    ts_of_first = {}
    big = os.path.exists(el) and os.path.getsize(el) > trim_mb * (1 << 20)
    head, tail = [], []
    with open(el, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            lines += 1
            if big:
                if lines <= 3000:
                    head.append(line)
                else:
                    tail.append(line)
                    if len(tail) > 200:
                        tail.pop(0)
            if 'TLB Miss' in line:
                tlb_lines += 1
                m = TLB_RE.search(line)
                if m:
                    key = (m.group(1).lower(), m.group(2).lower(), m.group(3))
                    tlb[key] += 1
                    if len(tlb_first) < 40:
                        tlb_first.append(dict(pc=m.group(1), addr=m.group(2),
                                              kind=m.group(3), line=line.rstrip()))
                        ts = TS_RE.match(line)
                        if ts:
                            ts_of_first[len(tlb_first)] = ts.group(1)
                if first_tlb_ts is None:
                    ts = TS_RE.match(line)
                    if ts:
                        first_tlb_ts = ts.group(1)
                ts = TS_RE.match(line)
                if ts:
                    last_tlb_ts = ts.group(1)
            elif 'Trap exception' in line:
                trap += 1
            elif 'Unrecognized op' in line or 'Unknown R5900' in line:
                op += 1
            elif 'Pausing' in line:
                pausing += 1
            elif '=== run end' in line:
                run_end = line.strip()
    rep.update(bytes=os.path.getsize(el) if os.path.exists(el) else 0, lines=lines,
               tlb_total=tlb_lines, trap=trap, unrecognized=op, pausing=pausing,
               run_end=run_end, first_tlb_ts=first_tlb_ts, last_tlb_ts=last_tlb_ts,
               tlb_unique=len(tlb),
               tlb_top=[dict(pc=k[0], addr=k[1], kind=k[2], n=v)
                        for k, v in tlb.most_common(24)],
               tlb_first=tlb_first)
    rep['trimmed'] = bool(big)
    if big:
        with open(os.path.join(rundir, 'emulog_sample.txt'), 'w',
                  encoding='utf-8', errors='replace', newline='\n') as fo:
            fo.writelines(head)
            fo.write('\n...[中略 %d 行]...\n\n' % max(0, lines - len(head) - len(tail)))
            fo.writelines(tail)
        os.remove(el)
        rep['emulog_deleted'] = True
    # 钩子摘要
    hl = os.path.join(rundir, 'hooklog.txt')
    if os.path.exists(hl):
        bypc = Counter()
        rows = []
        with open(hl, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                m = re.search(r'pc=(\w+) frame=(\d+) cycle=(\d+) .*? v0=(\w+)', line)
                if m:
                    bypc[m.group(1)] += 1
                    if len(rows) < 4000:
                        rows.append(line.rstrip())
        rep['hook_by_pc'] = dict(bypc)
        rep['hook_lines'] = sum(bypc.values())
        open(os.path.join(rundir, 'hooklog_sample.txt'), 'w', encoding='utf-8',
             newline='\n').write('\n'.join(rows) + '\n')
    # 截图
    snaps = [n for n in os.listdir(rundir) if n.startswith('snap_f') and n.endswith('.png')]
    rep['snaps'] = len(snaps)
    return rep


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('rundir')
    ap.add_argument('--json', default=None)
    ap.add_argument('--trim-mb', type=float, default=8.0)
    a = ap.parse_args()
    rep = analyze(a.rundir, a.trim_mb)
    print('rundir        %s' % rep['rundir'])
    print('emulog        %d B / %d 行%s' % (rep['bytes'], rep['lines'],
                                            '（已裁剪并删除原日志）' if rep.get('trimmed') else ''))
    print('TLB Miss      %d 行（唯一 (pc,addr) 组合 %d）' % (rep['tlb_total'], rep['tlb_unique']))
    print('Trap          %d 行' % rep['trap'])
    print('Unrecognized  %d 行' % rep['unrecognized'])
    print('Pausing       %d' % rep['pausing'])
    print('run_end       %s' % rep['run_end'])
    print('首条 TLB 时间戳 %s ；最后一条 %s' % (rep['first_tlb_ts'], rep['last_tlb_ts']))
    for k in rep['tlb_top'][:8]:
        print('   %-9s %-12s %-6s x%d' % (k['pc'], k['addr'], k['kind'], k['n']))
    if rep.get('hook_by_pc'):
        print('hook          %d 行 %s' % (rep['hook_lines'], rep['hook_by_pc']))
    print('截图          %d' % rep['snaps'])
    if a.json:
        json.dump(rep, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('[json] %s' % a.json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
