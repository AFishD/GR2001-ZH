# -*- coding: utf-8 -*-
r"""post_all.py -- 全部手臂跑完后的一次性后处理（优先复用 GR_FPS\tools 的既有脚本）。

对每条手臂（out\<arm>_fpsbisect）依次调用：
  screens.py    <dir> 60                 -> <dir>\SCREENS.txt      （画面段骨架 + 最长同画面段）
  analyze.py    <dir> 60                 -> <dir>\ANALYSIS.json    （同画面段 / 局部 fps 时间线 / TLB）
  bands.py      <dir>                    -> <dir>\BANDS.json       （按游戏阶段拆墙钟）
  subband.py    <dir> "f300-540" "f660-2460"  （固定内容子区间，前一位的最干净判据）
再把 cdvd_bands.py 一次性跑在全部 dir 上 -> work\builds\GR_FPSBISECT\CDVD_BANDS.json
最后 cross_arm.py 逐对跑（轨迹可比性证据）-> evidence\post\cross_*.txt

产物：
  evidence\post\<arm>.<tool>.txt   各脚本的原始 stdout
  POST_SUMMARY.json                折好的总表（含 f300-540 局部 fps 与 CDVD 读数）
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
BIS = os.path.join(REPO, 'work', 'builds', 'GR_FPSBISECT')
TOOLS = os.path.join(REPO, 'work', 'builds', 'GR_FPS', 'tools')
OUT = os.path.join(BIS, 'out')
EVID = os.path.join(BIS, 'evidence', 'post')
PY = sys.executable

SUB = ['f300-540', 'f660-2460']


def run(tool, args, tag):
    cmd = [PY, os.path.join(TOOLS, tool)] + args
    p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    txt = (p.stdout or '') + (('\n[stderr]\n' + p.stderr) if p.stderr else '')
    with io.open(os.path.join(EVID, tag + '.txt'), 'w', encoding='utf-8') as f:
        f.write('$ %s\n' % ' '.join(cmd))
        f.write(txt)
    return txt


def parse_subband(txt):
    out = {}
    for ln in txt.splitlines():
        m = re.search(r'(f\d+-\d+)\s+n=\s*(\d+).*?frames=\s*(\d+)\s+span=\s*([0-9.]+)\s*s\s+fps=\s*([0-9.]+)', ln)
        if m:
            out[m.group(1)] = {'n': int(m.group(2)), 'frames': int(m.group(3)),
                               'span_s': float(m.group(4)), 'fps': float(m.group(5))}
    return out


def main():
    if not os.path.isdir(EVID):
        os.makedirs(EVID)
    dirs = []
    for fn in sorted(os.listdir(OUT)):
        d = os.path.join(OUT, fn)
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, 'RUN.txt')) and not fn.startswith('_'):
            dirs.append(d)

    summary = {}
    for d in dirs:
        name = os.path.basename(d)
        print('=== %s ===' % name, flush=True)
        rec = {}
        run('screens.py', [d, '60'], name + '.screens')
        run('analyze.py', [d, '60'], name + '.analyze')
        run('bands.py', [d], name + '.bands')
        sub_txt = run('subband.py', [d] + SUB, name + '.subband')
        rec['subbands'] = parse_subband(sub_txt)
        for fn, key in (('ANALYSIS.json', 'analysis'), ('BANDS.json', 'bands'),
                        ('SCREENS.txt', 'screens_txt')):
            p = os.path.join(d, fn)
            if os.path.isfile(p):
                if fn.endswith('.json'):
                    with io.open(p, encoding='utf-8') as f:
                        rec[key] = json.load(f)
                else:
                    with io.open(p, encoding='utf-8', errors='replace') as f:
                        rec[key] = f.read()[:400]
        summary[name] = rec

    # CDVD: 一次性比全部手臂
    if dirs:
        cdvd_txt = run('cdvd_bands.py', dirs, '_all.cdvd_bands')
        print(cdvd_txt[:2000])
        p = os.path.join(BIS, 'CDVD_BANDS.json')
        if os.path.isfile(p):
            with io.open(p, encoding='utf-8') as f:
                summary['_cdvd'] = json.load(f)

    # 跨臂轨迹可比性
    pairs = [
        ('HK00_base_fpsbisect', 'EN_ORIG_fpsbisect'),
        ('HK00_base_fpsbisect', 'HK01_all_fpsbisect'),
        ('HK00_base_fpsbisect', 'HK04_g3_fpsbisect'),
        ('HK00_base_fpsbisect', 'HK04_g3_r2_fpsbisect'),
        ('HK00_base_fpsbisect', 'HK05_g4_fpsbisect'),
        ('HK00_base_fpsbisect', 'HK02_g1_fpsbisect'),
        ('HK00_base_fpsbisect', 'HK03_g2_fpsbisect'),
        ('HK00_base_fpsbisect', 'HK00_base_b_fpsbisect'),
        ('HK00_base_fpsbisect', 'HK00_base_c_fpsbisect'),
        ('EN_ORIG_fpsbisect', 'EN_ORIG_b_fpsbisect'),
        # 数据侧的对照组：与 EN / base 逐帧比，证明"同一条轨迹上只换了数据"
        ('EN_ORIG_fpsbisect', 'CVAR01_elf_fpsbisect'),
        ('EN_ORIG_fpsbisect', 'CVAR02_atlas_fpsbisect'),
        ('EN_ORIG_fpsbisect', 'CVAR04_text_fpsbisect'),
        ('EN_ORIG_fpsbisect', 'CVAR05_elf_atlas_fpsbisect'),
        ('EN_ORIG_fpsbisect', 'TXT02_no_text_fpsbisect'),
        ('HK00_base_fpsbisect', 'TXT02_no_text_fpsbisect'),
        # 跨轮（与本仓库上一轮 GR_FPS\out 的同一张盘同一条导航比）
        ('HK00_base_fpsbisect', os.path.join('..', '..', 'GR_FPS', 'out', 'GR_ZH113b_v4')),
        ('EN_ORIG_fpsbisect', os.path.join('..', '..', 'GR_FPS', 'out', 'GR_EN_ORIG_v4')),
    ]
    cross = {}
    for a, b in pairs:
        pa = os.path.join(OUT, a) if not os.path.isabs(a) else a
        pb = os.path.join(OUT, b) if not os.path.isabs(b) else b
        pb = os.path.normpath(pb)
        if not (os.path.isdir(pa) and os.path.isdir(pb)):
            continue
        tag = 'cross_%s__VS__%s' % (os.path.basename(pa), os.path.basename(pb))
        txt = run('cross_arm.py', [pa, pb], tag.replace('/', '_'))
        cross[tag] = txt
        print(txt, flush=True)
    summary['_cross'] = cross

    with io.open(os.path.join(BIS, 'POST_SUMMARY.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print('\nwrote POST_SUMMARY.json')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
