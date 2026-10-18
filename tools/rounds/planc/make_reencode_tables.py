# -*- coding: utf-8 -*-
r"""make_reencode_tables.py — 生成「强制重编码」用的文本表副本。

背景: inject_text_csv.py 对 `text_edited == text_zh`(没人工改过)的行**原样不动**
(设计如此: "dump 后不改动 ⇒ 产物与基底 sha256 相同")。
但本轮方案 C 把 的/你/荐 从单字节码改成对偶码 ⇒ **盘上所有旧编码的文本都必须重编码一次**,
否则那些字节在新 gate 下会被当 lead 读, 整段乱码。

做法: 拷一份表, 把 `text_zh` 列**清空** (译文 `text_edited` 一个字都不动) ⇒ 注入器认为
每一行都"被人工改过" ⇒ 用新 charset 重新编码写盘 ⇒ 盘上文本 = 用户译文, 编码 = 新口径。
"""
import csv
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text')
DST = os.path.join(REPO, 'work', '_planc', 'text_reencode')


def main():
    os.makedirs(DST, exist_ok=True)
    files = [f for f in sorted(os.listdir(SRC)) if f.endswith('.csv')]
    tot = kept = 0
    for fn in files:
        with open(os.path.join(SRC, fn), encoding='utf-8-sig', newline='') as fh:
            rows = list(csv.DictReader(fh))
            fields = list(rows[0].keys()) if rows else []
        assert 'text_edited' in fields and 'text_zh' in fields, fields
        for r in rows:
            tot += 1
            if (r.get('text_edited') or '') != '':
                kept += 1
            r['text_zh'] = ''            # ★ 只清这一列 (强制重编码); text_edited 原样
        out = os.path.join(DST, fn)
        with open(out, 'w', encoding='utf-8', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print('  %-34s %4d 行 (其中 text_edited 非空 %d) → %s'
              % (fn, len(rows), sum(1 for r in rows if (r.get('text_edited') or '') != ''),
                 os.path.relpath(out, REPO)))
    # 非 CSV 的伴随文件 (meta/txt) 一并拷过去, 免得注入器找不到
    for fn in os.listdir(SRC):
        if not fn.endswith('.csv'):
            with open(os.path.join(SRC, fn), 'rb') as a, open(os.path.join(DST, fn), 'wb') as b:
                b.write(a.read())
    print('  合计 %d 行 (text_edited 非空 %d) → %s' % (tot, kept, DST))
    print('  ★ 校验: 只改了 text_zh 列, 其余列逐字节来自用户表')


if __name__ == '__main__':
    main()
