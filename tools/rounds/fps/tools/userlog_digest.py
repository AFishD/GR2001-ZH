# -*- coding: utf-8 -*-
r"""userlog_digest.py -- 把用户给的三份 emulog 折成一张表 (只读)。

三份 (全部只读, 一字不改):
  1. work\builds\GR_ZH113b\emulog.txt            (19:39 会话, GR_ZH113b.iso)
  2. work\builds\GR_ZH113b_fix\emulog.txt        (20:20 会话, GR_ZH113b_fix.iso)
  3. %LOCALAPPDATA%\PCSX2\logs\emulog.txt        (同上 20:20 会话的原件)
输出: work\builds\GR_FPS\out\userlog_digest.json + stdout 表
"""
import hashlib
import io
import json
import os
import re
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
OUT = os.path.join(REPO, 'work', 'builds', 'GR_FPS', 'out', 'userlog_digest.json')

FILES = [
    ('GR_ZH113b 19:39', os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'emulog.txt')),
    ('GR_ZH113b_fix 20:20', os.path.join(REPO, 'work', 'builds', 'GR_ZH113b_fix', 'emulog.txt')),
    ('LOCALAPPDATA 20:20', os.path.join(os.environ.get('LOCALAPPDATA', ''), 'PCSX2', 'logs', 'emulog.txt')),
]

TS = re.compile(r'^\[\s*([0-9.]+)\]\s*(.*)$')


def digest(path):
    d = {'path': path, 'exists': os.path.isfile(path)}
    if not d['exists']:
        return d
    b = open(path, 'rb').read()
    d['bytes'] = len(b)
    d['sha256_16'] = hashlib.sha256(b).hexdigest()[:16]
    d['lines'] = b.count(b'\n')
    d['tlb'] = []
    d['trap'] = 0
    d['unmapped'] = 0
    d['pausing'] = []
    d['bios'] = None
    d['iso'] = None
    d['crc'] = None
    d['modeline'] = []
    d['last_ts'] = 0.0
    for ln in io.open(path, encoding='utf-8', errors='replace'):
        m = TS.match(ln.rstrip('\r\n'))
        ts, body = (float(m.group(1)), m.group(2)) if m else (None, ln.strip())
        if ts:
            d['last_ts'] = max(d['last_ts'], ts)
        if 'TLB Miss' in body:
            d['tlb'].append(ts)
        if 'Trap exception' in body:
            d['trap'] += 1
        if 'unmapped' in body.lower():
            d['unmapped'] += 1
        if 'Pausing' in body:
            d['pausing'].append(ts)
        if 'BIOS Found' in body:
            d['bios'] = body.strip()
        if 'isoFile open ok' in body:
            d['iso'] = body.split('isoFile open ok:')[-1].strip()
        if 'Game CRC' in body:
            d['crc'] = body.strip()
        if 'PCSX2 v' in body:
            d['modeline'].append(body.strip())
    # TLB 簇 (>1 s 间隔切簇)
    cl = []
    for t in d['tlb']:
        if t is None:
            continue
        if cl and t - cl[-1][-1] <= 1.0:
            cl[-1].append(t)
        else:
            cl.append([t])
    d['tlb_clusters'] = [{'n': len(c), 't0': round(c[0], 3), 't1': round(c[-1], 3),
                          'span_ms': round((c[-1] - c[0]) * 1000, 2)} for c in cl]
    d['tlb_n'] = len(d['tlb'])
    return d


def main():
    res = [digest(p) for _, p in FILES]
    rows = []
    for (tag, _), d in zip(FILES, res):
        row = {'tag': tag, **{k: v for k, v in d.items() if k != 'tlb'}}
        row['tlb_ts'] = d.get('tlb', [])
        rows.append(row)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    for r in rows:
        print('=== %s ===' % r['tag'])
        if not r['exists']:
            print('   (缺)'); continue
        print('   bytes=%d lines=%d sha256[:16]=%s' % (r['bytes'], r['lines'], r['sha256_16']))
        print('   iso = %s' % r['iso'])
        print('   crc = %s' % r['crc'])
        print('   bios= %s' % r['bios'])
        print('   PCSX2 = %s' % r['modeline'][:2])
        print('   session_end_ts = %.1f s' % r['last_ts'])
        print('   TLB n=%d  trap=%d unmapped=%d' % (r['tlb_n'], r['trap'], r['unmapped']))
        for c in r['tlb_clusters']:
            print('      cluster n=%-3d  t=%8.3f..%8.3f s  span=%.2f ms'
                  % (c['n'], c['t0'], c['t1'], c['span_ms']))
        print('   Pausing at %s' % r['pausing'])
        print('')
    print('wrote %s' % OUT)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
