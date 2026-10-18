# -*- coding: utf-8 -*-
r"""sent_fix_meta56.py —— 只修 SENT_06 的 meta.json 里一个**文字表述**字段（不动 ISO）。

原因：sent_build56.py 原先那句 `charwidth_entry_trampoline` 的格式串少了一个参数，
打印成 `0x27BDFFF0 0xFFBF0000`（值本身对，但表述含糊）。脚本已改；
本脚本把**已落盘**的 meta.json 里这一条改成与修好后脚本**逐字相同**的措辞。
ISO 产物**一字未动**（改完再复核 sha256 与站点回读）。
"""
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
OUTDIR = os.path.join(ROOT, 'work', 'builds', 'GR_SENT')
ISO_OF_VA = 0x6C780

name = 'SENT_06_icon_all_off_zh113b'
iso = os.path.join(OUTDIR, name + '.iso')
mp = os.path.join(OUTDIR, name + '.meta.json')


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


before = sha256_file(iso)
chk = open(iso, 'rb')
chk.seek(0x21AD10 - ISO_OF_VA)
w1, w2, w3 = struct.unpack('<3I', chk.read(12))
chk.close()
txt = ('VA 0x21AD10/0x21AD14/0x21AD18 = 0x%08X / 0x%08X / 0x%08X  '
       '（应 = `addiu sp,sp,-16` / `sd ra,0(sp)` / `j 0x416F40`）' % (w1, w2, w3))

m = json.load(open(mp, encoding='utf-8'))
old = m['extra_checks']['charwidth_entry_trampoline']
m['extra_checks']['charwidth_entry_trampoline'] = txt
with open(mp, 'w', encoding='utf-8') as f:
    json.dump(m, f, ensure_ascii=False, indent=1)

after = sha256_file(iso)
print('旧表述: %s' % old)
print('新表述: %s' % txt)
print('ISO sha256 改前 = %s' % before)
print('ISO sha256 改后 = %s  ⇒ %s' % (after, '未变 ✓' if before == after else '变了 ✗'))
print('meta 声明  sha256 = %s  ⇒ %s' % (m['sha256'],
                                        '一致 ✓' if m['sha256'] == after else '不符 ✗'))
