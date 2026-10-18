# -*- coding: utf-8 -*-
r"""combfix_analyze.py -- read a GR_COMBFIX run dir: emulog counters + hooklog summary + pcsample.

Usage: python combfix_analyze.py <runDir> [...] [--json out.json]
"""
import collections
import json
import os
import re
import sys

PATTERNS = {
    'trap': 'Trap exception',
    'unrecog': 'Unrecognized op',
    'tlb': 'TLB Miss,',
    'pausing': 'Pausing...',
    'reporterr': 'ReportErrorAsync',
    'eefatal': 'EE FATAL',
    'eeexc': 'EE EXCEPTION',
    'runend': 'run end, frames=',
    'arm': 'HookWatch: armed',
    'hooksleep': 'hooklog: ',
}
HOOK_RE = re.compile(r'hook pc=([0-9A-Fa-f]{8})')
PC_RE = re.compile(r'^([0-9A-Fa-f]{8})$')


def analyze(d, verbose=True):
    d = os.path.abspath(d)
    name = os.path.basename(d)
    rec = {'run': name, 'dir': d}
    log = os.path.join(d, 'emulog.txt')
    counts = collections.Counter()
    frames_line = ''
    tlb_first = tlb_last = ''
    if os.path.exists(log):
        size = os.path.getsize(log)
        with open(log, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                for k, pat in PATTERNS.items():
                    if pat in line:
                        counts[k] += 1
                        if k == 'runend':
                            frames_line = line.strip()
                        if k == 'tlb':
                            if not tlb_first:
                                tlb_first = line.strip()
                            tlb_last = line.strip()
        rec['emulog_bytes'] = size
    rec['counts'] = dict(counts)
    rec['frames_line'] = frames_line
    rec['tlb_first'] = tlb_first
    rec['tlb_last'] = tlb_last

    hl = os.path.join(d, 'hooklog.txt')
    if os.path.exists(hl):
        per = collections.Counter()
        n = 0
        first, last = [], []
        with open(hl, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                n += 1
                m = HOOK_RE.search(line)
                if m:
                    per[m.group(1).upper()] += 1
                if n <= 3:
                    first.append(line.strip())
                last.append(line.strip())
                if len(last) > 3:
                    last.pop(0)
        rec['hooklog_lines'] = n
        rec['hooklog_bytes'] = os.path.getsize(hl)
        rec['hook_per_pc'] = dict(per.most_common(12))
        rec['hook_first'] = first
        rec['hook_last'] = last

    ps = os.path.join(d, 'pcsample.txt')
    if os.path.exists(ps):
        pcs = []
        for line in open(ps, encoding='utf-8', errors='replace'):
            parts = line.split()
            if len(parts) == 2 and re.fullmatch(r'[0-9A-Fa-f]{8}', parts[1]):
                pcs.append(parts[1].upper())
            elif len(parts) == 1 and PC_RE.match(parts[0]):
                pcs.append(parts[0].upper())
        rec['pcsample_n'] = len(pcs)
        rec['pcsample_unique'] = dict(collections.Counter(pcs).most_common(8))
        rec['pcsample_tail'] = pcs[-8:]
    wt = os.path.join(d, 'watch.txt')
    if os.path.exists(wt):
        txt = open(wt, encoding='utf-8', errors='replace').read()
        rec['watch_bytes'] = len(txt)
        m = re.findall(r'hits=(\d+) frame=(\d+)', txt)
        if m:
            rec['watch_hits_last'] = m[-1]
    gr = os.path.join(d, 'grlog.txt')
    if os.path.exists(gr):
        rec['grlog_bytes'] = os.path.getsize(gr)
    if verbose:
        print('== %s' % name)
        print('   frames: %s' % (rec.get('frames_line') or '(no run-end line)'))
        print('   counts: %s' % json.dumps(rec['counts']))
        if tlb_first:
            print('   TLB first: %s' % tlb_first)
            print('   TLB last : %s' % tlb_last)
        if 'hooklog_lines' in rec:
            print('   hooklog: %d lines / %d B  per-PC: %s' % (
                rec['hooklog_lines'], rec['hooklog_bytes'], json.dumps(rec['hook_per_pc'])))
            print('     first: %s' % (rec['hook_first'][:2],))
            print('     last : %s' % (rec['hook_last'],))
        if 'pcsample_unique' in rec:
            print('   pcsample: n=%d unique=%s' % (rec['pcsample_n'], json.dumps(rec['pcsample_unique'])))
        if 'watch_hits_last' in rec:
            print('   watch last: hits=%s frame=%s' % tuple(rec['watch_hits_last']))
    return rec


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    dirs = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = {}
    for d in dirs:
        out[os.path.basename(os.path.abspath(d))] = analyze(d)
    if '--json' in sys.argv:
        p = sys.argv[sys.argv.index('--json') + 1]
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(out, f, indent=1, ensure_ascii=False)
        print('wrote', p)


if __name__ == '__main__':
    main()
