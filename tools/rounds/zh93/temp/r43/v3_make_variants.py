# -*- coding: utf-8 -*-
r"""v3_make_variants.py — round43 验证用的 CSV 变体生成器 (只写 temp/r43/, 不碰官方表)

★ 注入器的判定规则 (FORMAT.md §3.5): 只有 `text_edited != text_zh` 的行才会被重写 ——
  `text_zh` 是"盘上现值"的只读参考。所以本脚本**只改 text_edited**, 必要时也按需
  改 text_zh (仅 `csv_old_full`, 它要 100% 复刻 round42 那种"两列都是旧写法"的老表)。

产出四个表目录 (每个都是 GR_ZH93 的三张表逐行拷贝, 只动被点名的两行):

  csv_legacy_edit   text_edited = "Fran{{BTN:E0E7}}ais" / "Espa{{BTN:E0F1}}ol"   ← 旧写法
                    (text_zh 保持新 dump 的真字母) ⇒ 这一行**会进入写入集**,
                    编码出来的字节必须与盘上一模一样 (⇒ 全盘 0 差异, sha 不变)
  csv_old_full      text_zh = text_edited = 旧写法 (复刻 round42 的老表) ⇒ 同样 sha 不变
  csv_probe_new     text_edited = "Français!" / "Español!"      ← 真字母 + 一个真改动
  csv_probe_old     text_edited = "Fran{{BTN:E0E7}}ais!" / "Espa{{BTN:E0F1}}ol!"  ← 旧写法 + 同一个改动
                    ⇒ probe_new 与 probe_old 必须注入出**逐字节相同的盘**
"""
import csv
import io
import os
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'text')
KINDS = ('long', 'long_nowrap', 'short')
NEW = {'LANG:G059.I028': 'Français', 'LANG:G059.I031': 'Español'}
OLD = {'LANG:G059.I028': 'Fran{{BTN:E0E7}}ais', 'LANG:G059.I031': 'Espa{{BTN:E0F1}}ol'}
NEW_BANG = {'LANG:G059.I028': 'Français!', 'LANG:G059.I031': 'Español!'}
OLD_BANG = {'LANG:G059.I028': 'Fran{{BTN:E0E7}}ais!', 'LANG:G059.I031': 'Espa{{BTN:E0F1}}ol!'}


def emit(name, edits, tail, also_zh=False):
    """拷三张表到 temp/r43/<name>/; edits 只写进 text_edited (also_zh=True 时也写 text_zh)。"""
    out = os.path.join(HERE, name)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    n_hit = 0
    for k in KINDS:
        src = os.path.join(SRC, 'GR_ZH93_text_%s.csv' % k)
        dst = os.path.join(out, 'GR_ZH93_text_%s.csv' % k)
        with io.open(src, encoding='utf-8-sig', newline='') as f:
            rd = csv.DictReader(f)
            cols = rd.fieldnames
            rows = list(rd)
        for r in rows:
            rid = r['id']
            if rid in edits:
                n_hit += 1
                if also_zh:
                    r['text_zh'] = edits[rid]
                r['text_edited'] = edits[rid]
                r['note'] = ('★round43 验证变体 (%s); 原 note: %s' % (tail, r['note']))
        with io.open(dst, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator='\r\n', quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerows(rows)
        print('  %-56s %d 行' % (os.path.relpath(dst, REPO).replace('\\', '/'), len(rows)))
    assert n_hit == len(edits), '只该命中 %d 行, 实际 %d' % (len(edits), n_hit)
    print('  ⇒ %s: 改写 %d 行' % (name, n_hit))
    return out


print('# --- 生成验证变体 (text_zh 现值 = 新 dump 真字母: %s) ---' % NEW['LANG:G059.I028'])
for nm, ed, tail, az in (
        ('csv_legacy_edit', OLD, '旧写法只写 text_edited (该行会进写入集)', False),
        ('csv_old_full', OLD, '旧写法 text_zh+text_edited (复刻 round42 老表)', True),
        ('csv_probe_new', NEW_BANG, '真字母 ç/ñ + 追加强制重写', False),
        ('csv_probe_old', OLD_BANG, '旧写法 {{BTN:E0E7}} + 同一个强制重写', False)):
    emit(nm, ed, tail, az)
print('# [ok] 四个变体目录就绪 (都在 work/builds/GR_ZH93/temp/r43/ 下)')
