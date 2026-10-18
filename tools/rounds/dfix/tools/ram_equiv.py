# -*- coding: utf-8 -*-
r"""ram_equiv.py —— 用模拟器导出的 EE/IOP RAM 转储做「字节级等价」对照。

为什么这比截图更硬
------------------
`pcsx2-gsrunner` 在命中 `GR: dumped RAM (<容器名>) frame N` 时会把 **整块 32 MiB EE RAM**
（以及 2 MiB IOP RAM）落盘。EE RAM 里包含载入后的 ELF 镜像（VA 0x100000 起，与本 ELF 的
VA 一一对应 ⇒ **RAM 偏移 == VA**）。于是：

  同 ISO 跑两次  ⇒ 0 字节差异（本轮已用 base vs `GR_REBUILD\temp\dump_final` 验证）
  打了补丁的盘    ⇒ **只应**在补丁声明的 VA 上有差异

判据：
  * `differing_bytes` 必须等于该盘「逐站点差异字节数」之和（例如 `fp` = 1、`pkt` = 6）；
  * 差异偏移集合必须是声明站点 VA 的子集（越界即有未声明的副作用）。

用法:
  python work\builds\GR_DFIX\tools\ram_equiv.py [--ref base] [--tag DFIX_pkt ...]
"""
import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
RUNS = os.path.join(ROOT, 'runs')
KIND = ('_eeram.bin', '_iopram.bin')


def diff_bytes(a, b):
    """返回 (差异字节数, [偏移...])，流式。"""
    n, offs = 0, []
    off = 0
    with open(a, 'rb') as fa, open(b, 'rb') as fb:
        while True:
            x, y = fa.read(1 << 20), fb.read(1 << 20)
            if not x and not y:
                break
            if len(x) != len(y):
                return -1, []
            if x != y:
                for i in range(len(x)):
                    if x[i] != y[i]:
                        n += 1
                        if len(offs) < 64:
                            offs.append(off + i)
            off += len(x)
    return n, offs


def dumps(d):
    out = {}
    for f in sorted(os.listdir(d)):
        for k in KIND:
            if f.endswith(k):
                out[f] = os.path.join(d, f)
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('--ref', default='base')
    ap.add_argument('--tags', nargs='*', default=None)
    ap.add_argument('--control-dir', default=r'work\builds\GR_REBUILD\temp\dump_final',
                    help='**同一个 ISO** 的另一轮转储，用来标定运行间噪声基线')
    a = ap.parse_args()

    tags = a.tags or ['DFIX_pkt', 'DFIX_fp', 'DFIX_icon', 'DFIX_pkt_fp']
    tags = [t for t in tags if os.path.isdir(os.path.join(RUNS, t))]
    ref = os.path.join(RUNS, a.ref)
    rd = dumps(ref)
    print('=== RAM 等价对照（参照 = %s，%d 个转储） ===' % (a.ref, len(rd)))
    lines = ['=== RAM equivalence vs %s (%d dumps) ===' % (a.ref, len(rd))]

    # ── 用「同一个 ISO 的另一轮」标定噪声：EE 应 0；IOP 有固定的 2 字节漂移 ──
    noise = {}
    ctl = os.path.abspath(a.control_dir)
    if os.path.isdir(ctl):
        cd = dumps(ctl)
        for name in sorted(set(cd) & set(rd)):
            n, offs = diff_bytes(rd[name], cd[name])
            noise[name] = (n, set(offs))
        print('[control] 同 ISO 两轮（%s）噪声基线：' % a.control_dir)
        lines.append('[control] same-ISO noise floor (%s):' % a.control_dir)
        for name in sorted(noise):
            n, offs = noise[name]
            print('  %-42s %d 字节 @ %s' % (name, n, ', '.join('0x%X' % o for o in sorted(offs)) or '-'))
            lines.append('  %-42s %d bytes @ %s' % (name, n, ', '.join('0x%X' % o for o in sorted(offs)) or '-'))
    else:
        print('[control] 找不到 %s ⇒ 只对 EE 做严格判定' % ctl)

    for t in tags:
        meta_p = os.path.join(ROOT, t + '.meta.json')
        sites = []
        if os.path.exists(meta_p):
            m = json.load(open(meta_p, encoding='utf-8'))
            sites = [(int(s['va'], 16), 4) for s in m['sites']]
        want_bytes = sum(4 for _v, _l in sites)  # 上界；实际按 meta.diff_bytes
        if os.path.exists(meta_p):
            want_bytes = m['diff_bytes']
        o = dumps(os.path.join(RUNS, t))
        common = sorted(set(rd) & set(o))
        print('\n## %s（声明站点 %d 处 / 预期差异字节 %d）' % (t, len(sites), want_bytes))
        lines.append('\n## %s (sites=%d expect_diff_bytes=%d)' % (t, len(sites), want_bytes))
        bad = 0
        for name in common:
            n, offs = diff_bytes(rd[name], o[name])
            nnoise, noffs = noise.get(name, (0, set()))
            extra = [x for x in offs if x not in noffs]
            if name.endswith('_eeram.bin'):
                ok = (n == want_bytes and all(any(v <= x < v + 4 for (v, _l) in sites) for x in offs))
            else:
                # IOP 转储不含 EE ELF ⇒ 只允许标定出来的运行间噪声偏移
                ok = (n == nnoise and len(extra) == 0)
            if not ok:
                bad += 1
            print('  %-42s 差异字节 %-4d %s  %s' % (name, n, 'OK' if ok else 'CHECK',
                                                   ('@ ' + ', '.join('0x%X' % x for x in offs[:6])) if offs else ''))
            lines.append('  %-42s diff_bytes=%d %s %s'
                         % (name, n, 'OK' if ok else 'CHECK',
                            ('@ ' + ', '.join('0x%X' % x for x in offs[:6])) if offs else ''))
        only = sorted(set(rd) ^ set(o))
        if only:
            print('  只在一侧出现的转储: %s' % only)
            lines.append('  one-sided dumps: %s' % only)
        print('  ⇒ %s' % ('全部符合「差异 == 声明补丁」✓' if bad == 0 else '有 %d 个转储不符 ✗' % bad))
        lines.append('  => %s' % ('all match declared patch OK' if bad == 0 else '%d dumps mismatch' % bad))

    dst = os.path.join(ROOT, 'audit', 'ram_equiv.txt')
    with open(dst, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('\n写出: %s' % dst)


if __name__ == '__main__':
    main()
