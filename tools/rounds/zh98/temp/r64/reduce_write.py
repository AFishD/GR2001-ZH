# -*- coding: utf-8 -*-
r"""reduce_write.py — 把 new/<id>.txt 的改写稿写回 CSV 的 text_edited 列 (只动这一列)

★ 写盘口径**逐字节复刻** dump_text_csv.write_csv / csv_field:
    · UTF-8 **带 BOM**;
    · 每行 `,`.join(csv_field(col, val)) + `\r\n`;
    · csv_field: 列名在 ALWAYS_QUOTE 里、或值里含 `,` `"` `\r` `\n` ⇒ 加双引号 + `""` 转义。
  ⇒ `--verify` 会先做一次「读了不改、原样写回」的**字节级回环**: sha256 必须与源文件相同,
     否则说明本脚本的写盘口径与 dump 不一致, 直接中止 (绝不带着口径偏差改盘)。

用法:
  python reduce_write.py --verify        # 只做字节级回环自检 (不写正式文件)
  python reduce_write.py --dry           # 打印将要改的条目与长度差, 不写盘
  python reduce_write.py --write         # 真正写盘 (先备份到 text_backup_before_reduce2/)
只写 work/builds/GR_ZH109/text/GR_ZH109_text_long.csv 这一个文件。
"""
import csv
import hashlib
import io
import json
import os
import shutil
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
TXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text')
TARGET = os.path.join(TXT, 'GR_ZH109_text_long.csv')
HERE = os.path.dirname(os.path.abspath(__file__))
NEW = os.path.join(HERE, 'new')
TGT = os.path.join(HERE, 'reduce_targets.json')
BACKUP = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text_backup_before_reduce2')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ALWAYS_QUOTE = {'text_zh', 'text_en', 'text_edited', 'note', 'wrap_preview'}


def csv_field(name, value):
    """与**现役 CSV 的实际口径**逐字节一致 = csv.QUOTE_MINIMAL:

        · 值里含 `,` / `"` / `\\r` / `\\n` ⇒ 加双引号并把 `"` 写成 `""`;
        · 其余 (含**空值**) 一律裸写。

    ★ 注意: 这与 dump_text_csv.py::csv_field 的 ALWAYS_QUOTE 规则**不同** —— 后者会把
      text_zh/text_en/text_edited/note/wrap_preview 里的**空值**写成 `""`, 而现役
      GR_ZH109_text_long.csv 里这些列的空值是裸写的 (`8,,,"M18…`)。
      以**现役文件**为准 (它是注入器的输入); `--verify` 的字节级回环就是这条口径的守门人。
    """
    s = '' if value is None else str(value)
    if any(c in s for c in ',"\r\n'):
        return '"' + s.replace('"', '""') + '"'
    return s


def write_csv(path, rows, cols):
    """与现役 CSV 逐字节一致 (BOM + CRLF)。

    ★ 表头**不加引号** —— 现役盘的表头是 `...,wrap_preview,text_zh,text_en,text_edited,note`
      (裸列名); dump_text_csv.write_csv 会把表头当普通行走 csv_field (⇒ ALWAYS_QUOTE 的列名
      会被加引号), 那与现役文件不符。实测以**现役文件**为准: 表头裸写, 数据行按 csv_field。
      `--verify` 的字节级回环就是这条口径的守门人。
    """
    with open(path, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(','.join(cols).encode('utf-8') + b'\r\n')
        for r in rows:
            line = ','.join(csv_field(c, r.get(c, '')) for c in cols)
            f.write(line.encode('utf-8') + b'\r\n')


def read_rows(path):
    with io.open(path, 'r', encoding='utf-8-sig', newline='') as f:
        rd = csv.reader(f)
        cols, rows = None, []
        for rec in rd:
            if cols is None:
                cols = [c.strip() for c in rec]
                continue
            if not rec or all(not c.strip() for c in rec):
                continue
            r = {}
            for i, c in enumerate(cols):
                v = rec[i] if i < len(rec) else ''
                if v and '\r' in v:
                    v = v.replace('\r\n', '\n').replace('\r', '\n')
                r[c] = v
            rows.append(r)
    return rows, cols


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def load_new(rid):
    t = io.open(os.path.join(NEW, rid.replace(':', '_') + '.txt'),
                encoding='utf-8', newline='').read()
    t = t.replace('\r\n', '\n')
    return t[:-1] if t.endswith('\n') else t


def main():
    a = sys.argv[1:]
    rows, cols = read_rows(TARGET)
    if '--verify' in a:
        tmp = TARGET + '.roundtrip.tmp'
        write_csv(tmp, rows, cols)
        s1, s2 = sha(TARGET), sha(tmp)
        print('回环自检: 源 %s' % s1)
        print('          写 %s' % s2)
        print('  ⇒ %s' % ('**逐字节一致 ✓** (写盘口径与 dump 完全相同)'
                          if s1 == s2 else '!! 不一致 —— 口径有偏差, 不许改盘'))
        os.remove(tmp)
        return 0 if s1 == s2 else 1

    d = json.load(io.open(TGT, encoding='utf-8'))
    idx = dict((r['id'].strip(), r) for r in rows)
    changed, deltas = [], []
    for rid in sorted(d):
        if rid not in idx:
            print('!! CSV 里找不到 %s' % rid)
            return 1
        new = load_new(rid)
        old = idx[rid].get('text_edited') or ''
        if new == old:
            print('   %-14s 无变化' % rid)
            continue
        deltas.append((rid, len(old), len(new), len(new) - len(old)))
        changed.append(rid)
        idx[rid]['text_edited'] = new
    print('将改写 %d 条 (长度差合计 %+d 字符):' % (len(changed), sum(x[3] for x in deltas)))
    for rid, a0, b0, dl in deltas:
        print('   %-14s %5d → %5d  (%+d)' % (rid, a0, b0, dl))
    if '--write' not in a:
        print('[dry] 未写盘。加 --write 真正写入。')
        return 0
    os.makedirs(BACKUP, exist_ok=True)
    shutil.copy2(TARGET, os.path.join(BACKUP, os.path.basename(TARGET)))
    print('备份 → %s' % os.path.join(BACKUP, os.path.basename(TARGET)))
    write_csv(TARGET, rows, cols)
    print('已写盘: %s' % TARGET)
    print('  sha256 %s → %s' % ('(改前)', sha(TARGET)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
