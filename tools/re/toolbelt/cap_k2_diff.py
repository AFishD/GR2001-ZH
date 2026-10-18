# -*- coding: utf-8 -*-
r"""cap_k2_diff.py -- 判据 (g): 成品盘 vs 基底盘**全盘逐字节差异**, 分类"计划窗口内 / 窗口外"

    python tools/re/toolbelt/cap_k2_diff.py --final <成品> --base <基底> [--geom <几何盘>]

计划窗口 (本轮全部允许的改动落点):
  ① ELF 8 个字节站点: COLS / SKIP_ROWS / Y0 / V1 / GATE×4
  ② MENU.IMG 全体 (图集 px 容器 + 3 个中文文本容器的槽)
  ③ GR.IMG 里的 EN_STRINGS.RES@GR 槽
  ④ ISO9660 PVD 卷长 / 目录记录长度 (thr_patch_atlas 加高时改的)
判据: **窗口外必须 0 字节**; ISO 尺寸如实登记。
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402

VA2ISO = lambda va: va - 0x6C780                                       # noqa: E731
ELF_SITES = (0x4170AC, 0x4170E8, 0x4170F8, 0x4170FC,
             0x416EE8, 0x417160, 0x41751C, 0x5656A4)
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--final', required=True)
    ap.add_argument('--base', required=True)
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)
    iso = T.Iso(a.final)
    hdr = zx_lib.header(iso, zx_lib.MENU_LBA)
    img_size = hdr['size']
    eg = iso.img_entry(T.GR_LBA, T.LANG_GR_IDX)
    iso.close()
    MENU_BASE = zx_lib.MENU_LBA * 2048
    windows = [(VA2ISO(va), VA2ISO(va) + 4) for va in ELF_SITES]
    windows.append((MENU_BASE, MENU_BASE + img_size))
    windows.append((eg['iso_off'], eg['iso_off'] + eg['stored']))
    windows.append((0x828D8, 0x828E0))
    windows.append((0x8000 + 80, 0x8000 + 88))
    windows.sort()
    P('=' * 96)
    P('cap_k2_diff.py  成品 = %s' % os.path.abspath(a.final))
    P('                基底 = %s' % os.path.abspath(a.base))
    sf, sb = os.path.getsize(a.final), os.path.getsize(a.base)
    P('[size] 成品 %d B (%d sect) ; 基底 %d B (%d sect) ; Δ = %+d B'
      % (sf, sf // 2048, sb, sb // 2048, sf - sb))
    P('[win ] 计划窗口 %d 个:' % len(windows))
    for (lo, hi) in windows:
        P('        0x%09X..0x%09X  长 %d' % (lo, hi, hi - lo))
    n_in = n_out = 0
    runs = []
    with open(a.final, 'rb') as ff, open(a.base, 'rb') as fb:
        pos, CH = 0, 1 << 22
        in_run = False
        r0 = 0
        while pos < min(sf, sb):
            n = min(CH, min(sf, sb) - pos)
            bf, bb = ff.read(n), fb.read(n)
            if bf != bb:
                for i in range(n):
                    if bf[i] != bb[i]:
                        p = pos + i
                        if any(lo <= p < hi for (lo, hi) in windows):
                            n_in += 1
                            if not in_run:
                                r0, in_run = p, True
                        else:
                            n_out += 1
                            if in_run:
                                runs.append((r0, p))
                                in_run = False
                    else:
                        if in_run:
                            runs.append((r0, pos + i))
                            in_run = False
            pos += n
        if in_run:
            runs.append((r0, pos))
        if sf > sb:
            ff.seek(sb)
            extra = ff.read(sf - sb)
            nz = sum(1 for b in extra if b)
            P('[tail] 成品比基底多 %d B ; 其中非零 %d B' % (sf - sb, nz))
            n_out += nz
    P('[diff] 计划窗口内 **%d B** ; ★ **窗口外 %d B** %s'
      % (n_in, n_out, '✓' if n_out == 0 else '✗'))
    P('[diff] 差异连续区间数 (窗口内): %d ; 示例 %s'
      % (len(runs), [(hex(x), hex(y)) for (x, y) in runs[:6]]))
    out = a.out or os.path.join(REPO, 'work', 'builds', 'GR_FA2400_K2',
                                'cap_k2_diff.json')
    with io.open(out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dict(final=os.path.abspath(a.final), base=os.path.abspath(a.base),
                       size_final=sf, size_base=sb, windows=[list(w) for w in windows],
                       diff_in=n_in, diff_out=n_out, runs=len(runs)), f,
                  ensure_ascii=False, indent=1)
    with io.open(os.path.splitext(out)[0] + '.txt', 'w', encoding='utf-8',
                 newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    print('[out] %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
