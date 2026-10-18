# -*- coding: utf-8 -*-
r"""table.py -- 把 GR_FPSBISECT\quick\*.json 折成一张臂表（不碰 ISO、不跑模拟器）。

输出:
  * stdout: markdown 表 + 批内比值
  * work\builds\GR_FPSBISECT\ARM_TABLE.json   (全部原始字段 + 派生比值)
  * work\builds\GR_FPSBISECT\ARM_TABLE.md

派生量（这是本轮的判据）:
  eff_fps        = grlog 'run end, frames=' / RUN.txt elapsed_s      （前一位的定量信号，逐字同口径）
  cpu_ms         = @HWSTAT@ Average CPU Thread Time                    （EE 侧单帧 CPU 时间）
  vs_base / vs_en = 同批内 eff_fps 的比值                              （**跨批不可比**，所以只算批内）
"""
import io
import json
import os
import re
import sys

BIS = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_FPSBISECT'
QD = os.path.join(BIS, 'quick')


def lead_float(s):
    if not s:
        return None
    m = re.match(r'\s*(-?[0-9.]+)', str(s))
    return float(m.group(1)) if m else None


def int_lead(s):
    v = lead_float(s)
    return int(v) if v is not None else None


def is_base(arm):
    return arm.startswith('HK00_base')


def is_en(arm):
    return arm.startswith('EN_ORIG')


def load():
    recs = []
    for fn in sorted(os.listdir(QD)):
        if not fn.endswith('.json'):
            continue
        p = os.path.join(QD, fn)
        with io.open(p, encoding='utf-8') as f:
            r = json.load(f)
        e = r.get('emulog') or {}
        hw = e.get('hwstats') or {}
        run = r.get('run') or {}
        r['_'] = {
            'cpu_ms': lead_float(hw.get('Average CPU Thread Time')),
            'avg_frame_ms': lead_float(hw.get('Average Frame Time')),
            'max_frame_ms': lead_float(hw.get('Maximum Frame Time')),
            'min_frame_ms': lead_float(hw.get('Minimum Frame Time')),
            'draws': int_lead(hw.get('Draw Calls')),
            'passes': int_lead(hw.get('Render Passes')),
            'copies': int_lead(hw.get('Copies')),
            'uploads': int_lead(hw.get('Uploads')),
            'readbacks': int_lead(hw.get('Readbacks')),
            'cpu_usage': lead_float(hw.get('CPU Thread Usage')),
            'gs_usage': lead_float(hw.get('GS Thread Usage')),
            'gpu_usage': lead_float(hw.get('GPU Usage')),
            'gs_ms': lead_float(hw.get('Average GS Thread Time')),
            'tlb': e.get('tlb'), 'trap': e.get('trap'),
            'unmapped': e.get('unmapped'), 'pausing': e.get('pausing'),
            'crc': e.get('crc'), 'bios': e.get('bios'),
            'overlap': run.get('foreign_overlap_during_run'),
            'waited': run.get('waited_for_clear_s'),
            'exit': run.get('exit'),
        }
        recs.append(r)
    return recs


def main():
    recs = load()
    by_batch = {}
    for r in recs:
        by_batch.setdefault(r['batch'], []).append(r)
    for b in by_batch:
        # 按 RUN.txt 的 start 时间排 = 真实起跑顺序（不是按墙钟长度）
        by_batch[b].sort(key=lambda r: (r.get('run') or {}).get('start', ''))

    out = {'arms': recs, 'batches': {}}
    md = []
    md.append('| 批 | 顺序 | 臂 | ISO | eff fps | cpu_ms | avg_ms | max_ms | draws | copies | TLB/Trap/unmapped | 污染 | vs_base | vs_EN |')
    md.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')

    for b in sorted(by_batch):
        arms = by_batch[b]
        base = next((r for r in arms if is_base(r['arm'])), None)
        en = next((r for r in arms if is_en(r['arm'])), None)
        bf = base['eff_fps'] if base else None
        ef = en['eff_fps'] if en else None
        rows = []
        for i, r in enumerate(arms, 1):
            d = r['_']
            vs_b = (r['eff_fps'] / bf) if (bf and r['eff_fps']) else None
            vs_e = (r['eff_fps'] / ef) if (ef and r['eff_fps']) else None
            row = {
                'batch': b, 'order': i, 'arm': r['arm'], 'iso': os.path.basename(r['iso'] or ''),
                'eff_fps': r['eff_fps'], 'elapsed_s': r['elapsed_s'], 'frames': r['frames'],
                'vs_base': round(vs_b, 4) if vs_b else None,
                'vs_en': round(vs_e, 4) if vs_e else None,
                'rc': r['rc'],
            }
            row.update(d)
            rows.append(row)
            md.append('| %s | %d | `%s` | %s | **%s** | %s | %s | %s | %s | %s | %s/%s/%s | %s | %s | %s |' % (
                b, i, r['arm'], os.path.basename(r['iso'] or ''), r['eff_fps'],
                d['cpu_ms'], d['avg_frame_ms'], d['max_frame_ms'], d['draws'], d['copies'],
                d['tlb'], d['trap'], d['unmapped'], d['overlap'],
                ('%.3f' % vs_b) if vs_b else '-', ('%.3f' % vs_e) if vs_e else '-'))
        out['batches'][b] = {'rows': rows, 'base_fps': bf, 'en_fps': ef}
        md.append('')

    with io.open(os.path.join(BIS, 'ARM_TABLE.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with io.open(os.path.join(BIS, 'ARM_TABLE.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(md) + '\n')
    print('\n'.join(md))

    print('\n=== 批内排序（按 eff fps 从高到低）===')
    for b in sorted(by_batch):
        print('  批 %s: %s' % (b, '  '.join(
            '%s=%.2f' % (r['arm'], r['eff_fps'] or -1)
            for r in sorted(by_batch[b], key=lambda x: -(x['eff_fps'] or 0)))))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
