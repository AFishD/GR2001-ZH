# -*- coding: utf-8 -*-
r"""r64_fix_wrap.py — 把用户文本里 `{Warp}{Warp}`(两个断点标记紧挨) 修成"一个空行"

预检拦下的规则: 两个断点标记紧挨着 ⇒ 会写出连续换行 {br}{br}, 而 CSV 只能无损表示
1 个换行 ⇒ 必须拦。正确写法: **在 CSV 里敲一个空行(连续 2 个回车)**。
⇒ 本脚本把 `{WRAP}{WRAP}`(大小写不限) 替换为 `\n\n`。

安全: 先备份; 只改 `text_edited` 列; 只替换"紧挨的两个标记"; 改完重新统计。
"""
import csv
import io
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
TXT = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_ZH109\text'
BAK = os.path.join(os.path.dirname(TXT), 'text_backup_before_wrapfix')

PAIR = re.compile(r'(?:\{[Ww][Aa][Rr][Pp]\}){2,}')
DRY = '--dry-run' in sys.argv

print('文本目录:', TXT)
if not os.path.isdir(TXT):
    raise SystemExit('!! 目录不存在')
os.makedirs(BAK, exist_ok=True)

total = 0
for fn in sorted(os.listdir(TXT)):
    if not re.search(r'_text_[^/\\]*\.csv$', fn):      # 可注入表命名: <版本>_text_<kind>.csv
        continue
    p = os.path.join(TXT, fn)
    raw = io.open(p, encoding='utf-8-sig', newline='').read()
    rows = list(csv.DictReader(io.StringIO(raw)))
    if not rows or 'text_edited' not in rows[0]:
        continue
    n = 0
    for r in rows:
        t = r.get('text_edited') or ''
        if not t:
            continue
        m = PAIR.findall(t)
        if m:
            n += len(m)
            r['text_edited'] = PAIR.sub('\n\n', t)
    if not n:
        print('  %-40s 0 处' % fn)
        continue
    total += n
    print('  %-40s **%d 处** %s' % (fn, n, '(dry-run 未写)' if DRY else ''))
    if DRY:
        continue
    # 备份 + 写回 (保持原有列顺序/引号风格: csv 默认 QUOTE_MINIMAL)
    shutil.copyfile(p, os.path.join(BAK, fn))
    with io.open(p, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator='\r\n')
        w.writeheader()
        for r in rows:
            w.writerow(r)

print()
print('合计修复 %d 处' % total)
if not DRY and total:
    print('备份在:', BAK)
