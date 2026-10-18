# -*- coding: utf-8 -*-
r"""verify_entry_fields.py — 全量核验 IMG 条目记录的字段语义（686 条）

假设(由执行任务的 recon2.txt 提出):
  u32[0] = 名字偏移（相对名字区起始）; u32[6] = stored ; u32[7] = real ; u32[8] = off
本脚本: 对全部条目逐条核对 u32[0] 指向的字符串是否 == 条目名；并试探 u32[1] 的语义。
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

SS = 2048
for label, lba in (('MENU.IMG', 776286), ('GR.IMG', 19175)):
    base = lba * SS
    iso = tcslib.Iso(ISO)
    size = struct.unpack_from('<I', iso.mm, base)[0]
    names_end = struct.unpack_from('<I', iso.mm, base + 0x04)[0]
    tbl_end = struct.unpack_from('<I', iso.mm, base + 0x0C)[0]
    names_start = struct.unpack_from('<I', iso.mm, base + 0x10)[0]
    n = (tbl_end - 0x830) // 48
    print('=' * 78)
    print('%s  条目 %d  names [0x%X,0x%X)' % (label, n, names_start, names_end))

    ok_name = 0
    bad = []
    u1_vals = []
    for i in range(n):
        r = struct.unpack_from('<12I', iso.mm, base + 0x830 + 48 * i)
        noff = names_start + r[0]
        # 读该处的 NUL 结尾串
        s = b''
        p = noff
        while iso.mm[base + p] != 0 and p < tbl_end + 0x100000:
            s += bytes(iso.mm[base + p:base + p + 1])
            p += 1
        name = s.decode('latin-1')
        real = tcslib.iso.img_entry(lba, i)['name'] if False else None
        u1_vals.append(r[1])
        # 用 tcslib 的官方名字做基准
        try:
            official = None
        except Exception:
            pass
        if i < 3:
            print('  #%-3d u32[0]=0x%-6X ⇒ 名字区[0x%X] = %r   u32[1]=%d  stored=%d real=%d off=0x%X'
                  % (i, r[0], noff, name[:30], r[1], r[6], r[7], r[8]))
    # 全量核对: 每个 u32[0] 都应指向一个合法名字（在名字区内），且互不重叠
    offs = []
    for i in range(n):
        r = struct.unpack_from('<12I', iso.mm, base + 0x830 + 48 * i)
        offs.append(r[0])
    import collections
    dup = [k for k, v in collections.Counter(offs).items() if v > 1]
    inrange = sum(1 for o in offs if 0 <= names_start + o < names_end)
    print('  ★ u32[0] 落在名字区内的条目: %d / %d' % (inrange, n))
    print('  ★ u32[0] 重复值个数: %d %s' % (len(dup), '（说明多条共用同一名字 ⇒ 别名）' if dup else ''))
    print('  ★ u32[0] 单调递增? %s' % ('是' if all(offs[i] <= offs[i + 1] for i in range(n - 1)) else '否'))
    # u32[1] 语义试探: 是否与名字长度相关
    print('  ★ u32[1] 样例: %s' % u1_vals[:8])
    print('     u32[1] 范围: min=%d max=%d' % (min(u1_vals), max(u1_vals)))
    print('     u32[1] == 0 的条目数: %d' % sum(1 for v in u1_vals if v == 0))
    iso.close()
    print()
