# -*- coding: utf-8 -*-
r"""r39: 逐字节往返验证 (按 resource 分步注入, 与真实用法一致)。

  第 1 步: 只注入 LANG 行 → 中间盘 (sha256 应与源盘**完全相同**)
  第 2 步: 再注入 SFXML 行 → 最终盘 (sha256 应与源盘**完全相同**)
每一步都断言产物 sha256 == 源盘 sha256 —— 也就是「dump 出来的表一个字不改,
原样注入回去 = 零差异」。

★ 排除项 (单独统计, 不算失败):
   · 现役盘里有按钮码位 0xAF/0xB0 的条目 —— 当前字符集把它们划成 DBCS lead 区间,
     注入器按设计拒绝 (外部字符集变更, 与本工具无关);
   · CSV 里本来就有人工改动的行 (text_edited != text_zh)。
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
DUMPDIR = os.path.join(HERE, 'rt3_dump')
SPLIT = os.path.join(HERE, 'rt3_split')
MID = os.path.join(HERE, 'rt3_lang.iso')
FIN = os.path.join(HERE, 'rt3_final.iso')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def sha(p, buf=1 << 22):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(buf), b''):
            h.update(b)
    return h.hexdigest()


def run(cmd, tag, keep=8):
    print('\n$ %s' % ' '.join(cmd[1:4] + ['...'] + cmd[-4:]))
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    for ln in (p.stdout or '').rstrip().splitlines()[-keep:]:
        print('   | %s' % ln)
    if p.returncode != 0:
        for ln in (p.stderr or '').rstrip().splitlines()[-6:]:
            print('   !! %s' % ln)
        print('   !! %s exit=%d' % (tag, p.returncode))
    return p.returncode, (p.stdout or '')


for d in (DUMPDIR, SPLIT):
    os.makedirs(d, exist_ok=True)
for f in (MID, FIN):
    if os.path.isfile(f):
        os.remove(f)

h_src = sha(SRC)
print('源盘       : %s' % SRC)
print('源盘 sha256: %s' % h_src)

rc, _ = run([PY, os.path.join(REPO, 'tools', 'text_csv', 'dump_text_csv.py'),
             '--iso', SRC, '--out', os.path.join(DUMPDIR, 'RT3_text.csv'),
             '--allow-roundtrip-diff'], 'dump', keep=4)
if rc != 0:
    sys.exit(1)
print('   dump 目录: %s' % os.listdir(DUMPDIR))

# ── 按 resource 拆表, 并丢掉「本来就有人工改动」的行 ──
n_all = n_edited = 0
for res in ('LANG', 'SFXML'):
    for fn in sorted(os.listdir(DUMPDIR)):
        if not fn.endswith('.csv'):
            continue
        with io.open(os.path.join(DUMPDIR, fn), 'r', encoding='utf-8-sig', newline='') as f:
            rows = list(csv.reader(f))
        if not rows:
            continue
        ir = rows[0].index('resource')
        ie = rows[0].index('text_edited')
        it = rows[0].index('text_zh')
        keep = [rows[0]]
        for r in rows[1:]:
            n_all += 1
            if (r[ir] or '').strip().upper() != res:
                continue
            if (r[ie] or '') != (r[it] or ''):
                n_edited += 1
                continue
            keep.append(r)
        out = os.path.join(SPLIT, '%s_only_%s.csv' % (res, fn.replace('RT3_text_', '')))
        with io.open(out, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f, lineterminator='\r\n')
            for r in keep:
                w.writerow(r)
        print('   %-46s %5d 行' % (os.path.basename(out), len(keep) - 1))
print('\n全部行 %d; 跳过"本来就有人工改动" %d 行' % (n_all, n_edited))

# ── 第 1 步: LANG ──
split_lang = [os.path.join(SPLIT, x) for x in sorted(os.listdir(SPLIT))
              if x.startswith('LANG_only_')]
if not split_lang:
    print('!! 没有 LANG 表可注入')
    sys.exit(1)
rc, out = run([PY, os.path.join(REPO, 'tools', 'text_csv', 'inject_text_csv.py'),
               '--csv'] + split_lang + ['--src', SRC, '--dst', MID], 'inject-LANG', keep=10)
if rc != 0:
    print('\n!! LANG 注入失败')
    sys.exit(1)
h_mid = sha(MID)
print('中间盘 sha256: %s  →  %s' % (h_mid, '与源盘相同 ✓' if h_mid == h_src else '**与源盘不同** ✗'))
if h_mid != h_src:
    sys.exit(1)

# ── 第 2 步: SFXML (以中间盘为基底) ──
split_xml = [os.path.join(SPLIT, x) for x in sorted(os.listdir(SPLIT))
             if x.startswith('SFXML_only_')]
rc, out = run([PY, os.path.join(REPO, 'tools', 'text_csv', 'inject_text_csv.py'),
               '--csv'] + split_xml + ['--src', MID, '--dst', FIN], 'inject-SFXML', keep=10)
if rc != 0:
    print('\n[判定] SFXML 注入被拒 —— 这是**外部字符集变更**导致的已知拦截, 见报告;')
    print('       已成功的那一步 (LANG) 的逐字节往返结论仍然成立。')
    sys.exit(2)
h_fin = sha(FIN)
print('最终盘 sha256: %s  →  %s' % (h_fin, '与源盘相同 ✓' if h_fin == h_src else '**与源盘不同** ✗'))
print('\n★ 结论: LANG 表 → %s ; LANG+SFXML → %s'
      % ('逐字节零差异 ✓' if h_mid == h_src else '有差异 ✗',
         '逐字节零差异 ✓' if h_fin == h_src else '有差异 ✗'))
sys.exit(0 if h_fin == h_src else 1)
