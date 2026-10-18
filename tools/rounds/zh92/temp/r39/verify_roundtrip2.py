# -*- coding: utf-8 -*-
r"""r39: 真·逐字节往返验证 (dump → 原样注入 ⇒ 与源盘 sha256 相同)。

口径要点:
  · dump_text_csv.py 的 text_edited 预填与 text_zh 相同 ⇒ "什么都没改" 的 dump
    注入回去必须**逐字节零差异** (这是 dump/inject 互逆的核心不变式);
  · 本盘有两类**已知**会让"原样注入"产生差异的条目, 本脚本把它们**排除**开单独统计,
    其余全部参与验证:
      ① 按钮码位冲突: 当前字符集把 0xA1..0xB0 划成 DBCS lead 区间, 而现役盘里有
         31 条老按钮码 0xAF/0xB0 ⇒ 注入器按设计拒绝 (外部字符集变更, 与本工具无关);
      ② 现役盘 CSV 里**本来就有人工改动**的行 (text_edited != text_zh) —— 那 29 条
         是用户/前几轮真的改过的译文, 注入就该改盘, 不属于"原样注入"。
只读源盘; 产物只写 work/builds/GR_ZH92/temp/r39/。
"""
import csv
import hashlib
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
PY = sys.executable
SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
DUMPDIR = os.path.join(HERE, 'rt_dump2')
ONLYDIR = os.path.join(HERE, 'rt_only')
OUT = os.path.join(HERE, 'rt_identity_final.iso')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def sha(p, buf=1 << 22):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(buf), b''):
            h.update(b)
    return h.hexdigest()


def run(cmd, tag, keep=12):
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
os.makedirs(ONLYDIR, exist_ok=True)
for f in (OUT,):
    if os.path.isfile(f):
        os.remove(f)

print('源盘       : %s' % SRC)
print('源盘 sha256: %s' % sha(SRC))

rc = run([PY, os.path.join(REPO, 'tools', 'text_csv', 'dump_text_csv.py'),
          '--iso', SRC, '--out', os.path.join(DUMPDIR, 'RT2_text.csv'),
          '--allow-roundtrip-diff'], 'dump')
if rc != 0:
    sys.exit(1)

# ── 挑出「本来就没改动」的行, 单独组一份只有它们的表 (表头/列原样保留) ──
ids, n_edited, n_total = [], 0, 0
for fn in sorted(os.listdir(DUMPDIR)):
    if not fn.endswith('.csv'):
        continue
    with io.open(os.path.join(DUMPDIR, fn), 'r', encoding='utf-8-sig', newline='') as f:
        rows = list(csv.reader(f))
    keep = [rows[0]]
    ie = rows[0].index('text_edited')
    it = rows[0].index('text_zh')
    for r in rows[1:]:
        n_total += 1
        if len(r) > max(ie, it) and (r[ie] or '') == (r[it] or ''):
            keep.append(r)
            ids.append(r[0])
        else:
            n_edited += 1
    with io.open(os.path.join(ONLYDIR, fn), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, lineterminator='\r\n')
        for r in keep:
            w.writerow(r)
    print('   %-30s 取 %d 行 (原表 %d 行)' % (fn, len(keep) - 1, len(rows) - 1))
print('\n原样行 %d / 有人工改动 %d / 合计 %d' % (len(ids), n_edited, n_total))

only = ','.join(ids)
print('--only 列表长度 = %d 字符' % len(only))
rc = run([PY, os.path.join(REPO, 'tools', 'text_csv', 'inject_text_csv.py'),
          '--csv', ONLYDIR, '--src', SRC, '--dst', OUT, '--only', only], 'inject', keep=26)
if rc != 0:
    print('\n!! 注入失败 (exit=%d) —— 往返验证不成立' % rc)
    sys.exit(1)
h = sha(OUT)
print('\n产物       : %s' % OUT)
print('产物 sha256: %s' % h)
same = (h == sha(SRC))
print('\n★ 结论: %d 条「原样注入」的行 → 产物与源盘 %s'
      % (len(ids), '**逐字节相同** ✓' if same else '**不同** ✗'))
sys.exit(0 if same else 1)
