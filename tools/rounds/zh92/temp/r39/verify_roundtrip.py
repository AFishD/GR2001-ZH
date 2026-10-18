# -*- coding: utf-8 -*-
r"""r39: 真·逐字节往返验证 (dump → 原样注入 ⇒ 与源盘 sha256 相同)。

做法: 在同一种字符集下
  ① 用 dump_text_csv.py 把源盘 dump 到临时目录 (--allow-roundtrip-diff 只为绕过
     **当前字符集**下按钮码位 0xAF/0xB0 的新口径冲突, 见报告「外部干扰」一节);
  ② 把 dump 出来的表**原样**交给 inject_text_csv.py 注入回同一种源盘;
  ③ 比较产物与源盘的 sha256 —— 相同即证明「dump 无损 + 未改动=零差异」成立。
只读源盘; 产物只写 work/builds/GR_ZH92/temp/r39/。
"""
import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
PY = sys.executable
SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
WORK = HERE
DUMPDIR = os.path.join(WORK, 'rt_dump')
OUT = os.path.join(WORK, 'rt_identity.iso')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def sha(p, buf=1 << 22):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        while True:
            b = f.read(buf)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def run(cmd, tag):
    print('\n$ %s' % ' '.join(os.path.basename(c) if i == 1 else c
                              for i, c in enumerate(cmd)))
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    tail = (p.stdout or '').rstrip().splitlines()[-14:]
    for ln in tail:
        print('   | %s' % ln)
    if p.returncode != 0:
        print('   !! %s exit=%d' % (tag, p.returncode))
        for ln in (p.stderr or '').rstrip().splitlines()[-10:]:
            print('   !! %s' % ln)
    return p.returncode


os.makedirs(DUMPDIR, exist_ok=True)
if os.path.isfile(OUT):
    os.remove(OUT)

h_src = sha(SRC)
print('源盘      : %s' % SRC)
print('源盘 sha256: %s' % h_src)

rc1 = run([PY, os.path.join(REPO, 'tools', 'text_csv', 'dump_text_csv.py'),
           '--iso', SRC, '--out', os.path.join(DUMPDIR, 'RT_text.csv'),
           '--allow-roundtrip-diff'], 'dump')
if rc1 != 0:
    sys.exit(1)
rc2 = run([PY, os.path.join(REPO, 'tools', 'text_csv', 'inject_text_csv.py'),
           '--csv', DUMPDIR, '--src', SRC, '--dst', OUT], 'inject')
if rc2 != 0:
    print('\n!! 注入失败 (exit=%d) —— 往返验证不成立' % rc2)
    sys.exit(1)
print('\n产物      : %s' % OUT)
print('产物 sha256: %s' % sha(OUT))
print('\n★ 结论: 产物与源盘 %s' % ('**逐字节相同** ✓' if sha(OUT) == h_src else '**不同** ✗'))
sys.exit(0 if sha(OUT) == h_src else 1)
