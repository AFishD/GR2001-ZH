# -*- coding: utf-8 -*-
r"""battery.py -- run heapaudit over a list of RAM images and print a compact
comparison table (also dumps each full audit as JSON).

usage: python battery.py <outdir> <label>=<path>[=base_hex] ...
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = os.path.join(HERE, 'heapaudit.py')


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    outdir = sys.argv[1]
    os.makedirs(outdir, exist_ok=True)
    rows = []
    for spec in sys.argv[2:]:
        parts = spec.split('=')
        label, path = parts[0], parts[1]
        base = parts[2] if len(parts) > 2 else None
        cmd = [sys.executable, AUDIT, path, label] + ([base] if base else [])
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        if r.returncode != 0 or not r.stdout.strip():
            print('FAILED %s: %s' % (label, (r.stderr or '')[-400:]))
            continue
        try:
            d = json.loads(r.stdout)
        except Exception as exc:
            print('BADJSON %s: %s' % (label, exc))
            open(os.path.join(outdir, label + '.txt'), 'w', encoding='utf-8').write(r.stdout)
            continue
        with open(os.path.join(outdir, label + '.json'), 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        rows.append(d)
        print('%-22s base=%s top=%s topsz=%9d used=%9d (%5.1f%%) free=%9d bins=%2d broken=%d null=%d orphan=%d'
              % (label, d.get('heap_base'), d.get('top_ptr'), d.get('top_size', 0),
                 d.get('used_bytes', 0), d.get('used_pct', 0), d.get('free_bytes', 0),
                 d.get('bins_nonempty', 0), d.get('bins_broken', 0),
                 d.get('bin_null_slots', 0), d.get('free_chunks_not_in_any_bin', 0)))
        # highlight the biggest broken bin pointers
        for b in d.get('bin_detail', []):
            if b['problems']:
                print('        bin %3d fd=%s bk=%s sent=%s : %s'
                      % (b['bin'], b['fd'], b['bk'], b['sentinel'], '; '.join(b['problems'])[:150]))
    print('')
    print('%-22s %10s %10s %10s %10s %8s' % ('label', 'heap_total', 'used', 'free', 'top_free', 'used%'))
    for d in rows:
        print('%-22s %10d %10d %10d %10d %7.1f%%'
              % (d['label'], d.get('heap_total', 0), d.get('used_bytes', 0),
                 d.get('free_bytes', 0), d.get('top_size', 0), d.get('used_pct', 0)))


if __name__ == '__main__':
    main()
