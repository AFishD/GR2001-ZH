# -*- coding: utf-8 -*-
r"""r39: 逐字节往返验证 —— 在**英文基线盘**上做 (不受当前字符集 DBCS 区间变更影响)。

为什么换盘: 现役中文盘 (GR_ZH92) 里有 31 条老按钮码 0xAF / 0xB0 的条目, 而**外部**
正在进行的字符集改动把这些字节划成了 DBCS lead 区间 ⇒ 注入器按设计拒绝写入。
那是与本工具无关的冲突 (见报告「外部干扰」), 但会挡住"逐字节往返"的验收。
英文基线盘 GR_EN_ORIG 的按钮码是 0xB1 / 0xB5 (仍然合法), 且它是一份**真实的
PS2 盘**——用来验证「dump 出来的表一个字不改, 原样注入回去 = 零差异」同样有效。

流程: dump EN 盘 → 原样注入 → 产物 sha256 必须 == EN 盘 sha256。
只读 EN 盘; 产物只写 work/builds/GR_ZH92/temp/r39/。
"""
import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
PY = sys.executable
EN = os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso')
DUMPDIR = os.path.join(HERE, 'en_rt')
OUT = os.path.join(HERE, 'en_rt_identity.iso')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def sha(p, buf=1 << 22):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(buf), b''):
            h.update(b)
    return h.hexdigest()


def run(cmd, tag, keep=9):
    print('\n$ %s' % ' '.join(cmd[1:]))
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    for ln in (p.stdout or '').rstrip().splitlines()[-keep:]:
        print('   | %s' % ln)
    if p.returncode != 0:
        for ln in (p.stderr or '').rstrip().splitlines()[-6:]:
            print('   !! %s' % ln)
        print('   !! %s exit=%d' % (tag, p.returncode))
    return p.returncode


os.makedirs(DUMPDIR, exist_ok=True)
if os.path.isfile(OUT):
    os.remove(OUT)
h_en = sha(EN)
print('英文基线盘 : %s' % EN)
print('sha256     : %s' % h_en)

rc = run([PY, os.path.join(REPO, 'tools', 'text_csv', 'dump_text_csv.py'),
          '--iso', EN, '--out', os.path.join(DUMPDIR, 'ENRT_text.csv'),
          '--no-en', '--allow-roundtrip-diff'], 'dump')
if rc != 0:
    print('!! dump 失败')
    sys.exit(1)
rc = run([PY, os.path.join(REPO, 'tools', 'text_csv', 'inject_text_csv.py'),
          '--csv', DUMPDIR, '--src', EN, '--dst', OUT], 'inject', keep=14)
if rc != 0:
    print('!! 注入失败 (exit=%d)' % rc)
    sys.exit(1)
h = sha(OUT)
print('\n产物       : %s' % OUT)
print('产物 sha256: %s' % h)
same = (h == h_en)
print('\n★ 结论: dump → 原样注入 ⇒ 产物与源盘 %s' % ('**逐字节相同** ✓' if same else '**不同** ✗'))
sys.exit(0 if same else 1)
