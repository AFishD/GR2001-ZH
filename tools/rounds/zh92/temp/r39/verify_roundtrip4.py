# -*- coding: utf-8 -*-
r"""r39: 逐字节往返验证 (排除**外部字符集冲突**的行)。

背景 (见报告「外部干扰」):
  外部正在做的字符集方案 C 把对偶 lead 区间从 0xA1..0xAD 扩到 0xA1..0xB0,
  而现役盘正文里仍然有**裸的 0xAF / 0xB0 字节** (老的手柄按键图标码, SFXML 789+315
  个, LANG 943+547 个) ⇒ 这批条目在当前字符集下**无法逐字节往返**
  (注入器按设计拒绝 {{BTN:E0AF}} / {{BTN:E0B0}})。
  这属于外部字符集变更引起的冲突, 不是本工具的问题, 但它会挡住"往返验证"。

本脚本: 把带这两种标记的行从表里剔掉, 其余**全部**参与验证:
    dump 出来的表 → 原样注入 → 产物 sha256 必须 == 源盘 sha256。
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
DUMP = os.path.join(HERE, 'rt4_dump')
CLEAN = os.path.join(HERE, 'rt4_clean')
MID = os.path.join(HERE, 'rt4_lang.iso')
FIN = os.path.join(HERE, 'rt4_final.iso')
CONFLICT = ('{{BTN:E0AF}}', '{{BTN:E0B0}}')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def sha(p, buf=1 << 22):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(buf), b''):
            h.update(b)
    return h.hexdigest()


def run(cmd, tag, keep=8):
    print('\n$ %s' % ' '.join(cmd[1:4] + ['…'] + cmd[-4:]))
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    for ln in (p.stdout or '').rstrip().splitlines()[-keep:]:
        print('   | %s' % ln)
    if p.returncode != 0:
        for ln in (p.stderr or '').rstrip().splitlines()[-5:]:
            print('   !! %s' % ln)
        print('   !! %s exit=%d' % (tag, p.returncode))
    return p.returncode


for d in (DUMP, CLEAN):
    os.makedirs(d, exist_ok=True)
for f in (MID, FIN):
    if os.path.isfile(f):
        os.remove(f)

h_src = sha(SRC)
print('源盘 sha256: %s' % h_src)
rc = run([PY, os.path.join(REPO, 'tools', 'text_csv', 'dump_text_csv.py'),
          '--iso', SRC, '--out', os.path.join(DUMP, 'RT4_text.csv'),
          '--allow-roundtrip-diff'], 'dump', keep=3)
if rc != 0:
    sys.exit(1)

# ── 剔掉含冲突标记的行; 按 resource 分表 ──
kept = conflicts = 0
for res in ('LANG', 'SFXML'):
    for fn in sorted(os.listdir(DUMP)):
        if not fn.endswith('.csv'):
            continue
        with io.open(os.path.join(DUMP, fn), 'r', encoding='utf-8-sig', newline='') as f:
            rows = list(csv.reader(f))
        ir, ie, it = (rows[0].index(x) for x in ('resource', 'text_edited', 'text_zh'))
        keep = [rows[0]]
        for r in rows[1:]:
            if (r[ir] or '').strip().upper() != res:
                continue
            if any(m in (r[ie] or '') or m in (r[it] or '') for m in CONFLICT):
                conflicts += 1
                continue
            keep.append(r)
            kept += 1
        out = os.path.join(CLEAN, '%s__%s' % (res, fn))
        with io.open(out, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f, lineterminator='\r\n')
            for r in keep:
                w.writerow(r)
        print('   %-26s %5d 行' % ('%s/%s' % (res, fn.replace('RT4_text_', '')), len(keep) - 1))
print('\n保留 %d 行; 因外部冲突剔除 %d 行' % (kept, conflicts))

rc = run([PY, os.path.join(REPO, 'tools', 'text_csv', 'inject_text_csv.py'),
          '--csv'] + [os.path.join(CLEAN, x) for x in sorted(os.listdir(CLEAN))
                      if x.startswith('LANG__')] + ['--src', SRC, '--dst', MID],
         'inject-LANG', keep=9)
if rc != 0:
    print('!! LANG 注入失败')
    sys.exit(1)
h_mid = sha(MID)
print('中间盘 sha256: %s → %s' % (h_mid, '与源盘相同 ✓' if h_mid == h_src else '不同 ✗'))

rc = run([PY, os.path.join(REPO, 'tools', 'text_csv', 'inject_text_csv.py'),
          '--csv'] + [os.path.join(CLEAN, x) for x in sorted(os.listdir(CLEAN))
                      if x.startswith('SFXML__')] + ['--src', MID, '--dst', FIN],
         'inject-SFXML', keep=9)
if rc != 0:
    print('!! SFXML 注入失败')
    sys.exit(1)
h_fin = sha(FIN)
print('最终盘 sha256: %s → %s' % (h_fin, '与源盘相同 ✓' if h_fin == h_src else '不同 ✗'))
print('\n★ 结论: 剔除 %d 条外部冲突行后, 其余 %d 条的 dump → 原样注入 = %s'
      % (conflicts, kept, '**逐字节零差异** ✓' if h_fin == h_src else '有差异 ✗'))
sys.exit(0 if h_fin == h_src else 1)
