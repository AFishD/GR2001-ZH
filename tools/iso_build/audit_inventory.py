# -*- coding: utf-8 -*-
r"""audit_inventory.py — 用 docs/PATCH_INVENTORY.md 逐条核对现役盘的 ELF

(原 work/_dis/r23_audit_inventory.py; round33 起 work/ 只保留 builds/, 故迁到 tools/iso_build/)

表格行格式: | VA | EN 词 | ZH 词 | 语义 | 引入 | 现状 |
判读:
  · 现役盘 == ZH 词  ⇒ 该补丁在役 ✓
  · 现役盘 == EN 词  ⇒ **该补丁缺失/被回退** ✗
  · 都不是            ⇒ 需要人工看 (可能是后续版本又改过)
用法: python tools/iso_build/audit_inventory.py <iso> [只列缺失]

铁律: 任何改 ELF 的补丁之后必须跑本脚本, 结果必须「缺失 0 条」。
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
ELF_LBA, SEC_OFF, SEC_ADDR = 295, 0x80, 0x00100000
DOC = os.path.join(REPO, 'docs', 'PATCH_INVENTORY.md')
ROW = re.compile(r'^\|\s*((?:0x[0-9A-Fa-f]{6}\s*(?:/\s*)?)+)\s*\|\s*((?:[0-9A-Fa-f]{8}\s*(?:/\s*)?)+)\s*\|\s*'
                 r'((?:[0-9A-Fa-f]{8}\s*(?:/\s*)?)+)\s*\|(.*)$')


def main():
    iso = sys.argv[1] if len(sys.argv) > 1 else 'work/builds/GR_ZH86R/GR_ZH86R.iso'
    only_missing = '--missing' in sys.argv
    d = open(os.path.join(REPO, iso), 'rb').read()
    rows = []
    for line in open(DOC, encoding='utf-8', errors='replace'):
        m = ROW.match(line.strip())
        if not m:
            continue
        vas = re.findall(r'0x[0-9A-Fa-f]{6}', m.group(1))
        ens = re.findall(r'[0-9A-Fa-f]{8}', m.group(2))
        zhs = re.findall(r'[0-9A-Fa-f]{8}', m.group(3))
        if len(vas) != len(ens) or len(ens) != len(zhs):
            continue
        for i, v in enumerate(vas):
            rows.append((int(v, 16), int(ens[i], 16), int(zhs[i], 16), m.group(4).strip()[:60]))
    print('PATCH_INVENTORY 解析出 %d 条字节级补丁' % len(rows))
    ok = miss = other = 0
    missing = []
    for (va, en, zh, note) in rows:
        if not (0x100000 <= va < 0x600000):
            continue
        off = ELF_LBA * 2048 + SEC_OFF + (va - SEC_ADDR)
        if off + 4 > len(d):
            continue
        cur = struct.unpack_from('<I', d, off)[0]
        if cur == zh:
            ok += 1
        elif cur == en:
            miss += 1
            missing.append((va, en, zh, note))
        else:
            other += 1
            if not only_missing:
                print('  ? 0x%06X 现役 %08X (EN %08X / ZH %08X) %s' % (va, cur, en, zh, note))
    print('\n在役 %d 条, **缺失(仍为 EN 词) %d 条**, 其它 %d 条' % (ok, miss, other))
    if missing:
        print('\n=== 缺失清单 (现役盘仍是 EN 原词 ⇒ 汉化补丁没生效) ===')
        for (va, en, zh, note) in missing:
            print('  0x%06X  EN %08X → 应 %08X   %s' % (va, en, zh, note))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
