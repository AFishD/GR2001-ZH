# -*- coding: utf-8 -*-
r"""img_add_entry.py — 往 PS2 IMG 容器里**新增一个条目**（落地方案第 1 步）

配方（round 5 实测得出）:
  · 条目数 = (u32[+0x0C] − 0x830) / 48          ← 无独立字段
  · 头/表/名字全在前 64 KB 内；数据区从 min(off) 起
  · 表尾与名字区之间有空隙 ⇒ 把**名字区整体前移**到新表尾之后，即可容纳新名字
  · 新条目的数据写在**容器尾料**里 ⇒ 容器不长大 ⇒ **ISO 完全不用改**

用法:
  python img_add_entry.py <输入ISO> <输出ISO> <IMG名> <新条目名> <数据文件> [--lba N] [--dry-run]
例:
  python img_add_entry.py src.iso out.iso MENU.IMG NEWFONT.RSB data.bin --dry-run
"""
import argparse
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

TAB_OFF, TAB_STEP = 0x830, 48
IMG_LBA = {'GR.IMG': 19175, 'MENU.IMG': 776286}
IMG_SIZE = {'GR.IMG': 1550563328, 'MENU.IMG': 58300882}


def parse(img):
    """返回 dict(count, tbl_end, names_start, names_end, data_start, names[], entries[])"""
    tbl_end = struct.unpack_from('<I', img, 0x0C)[0]
    names_start = struct.unpack_from('<I', img, 0x10)[0]
    names_end = struct.unpack_from('<I', img, 0x04)[0]
    count = (tbl_end - TAB_OFF) // TAB_STEP
    names = [x.decode('latin-1') for x in bytes(img[names_start:names_end]).split(b'\x00') if x]
    entries = []
    for i in range(count):
        r = struct.unpack_from('<12I', img, TAB_OFF + TAB_STEP * i)
        entries.append(dict(stored=r[6], real=r[7], off=r[8], raw=list(r)))
    data_start = min(e['off'] for e in entries) if entries else names_end
    return dict(count=count, tbl_end=tbl_end, names_start=names_start, names_end=names_end,
                data_start=data_start, names=names, entries=entries)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('img', choices=list(IMG_LBA))
    ap.add_argument('name', help='新条目名（不带路径）')
    ap.add_argument('data', help='新条目的数据文件')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    blob = open(a.data, 'rb').read()
    base = IMG_LBA[a.img] * 2048
    size = IMG_SIZE[a.img]
    src = bytearray(open(a.src, 'rb').read())
    img = src[base:base + size]
    info = parse(img)

    print('容器 %s  条目 %d  表结束 0x%X  名字区 [0x%X,0x%X)  数据起 0x%X'
          % (a.img, info['count'], info['tbl_end'], info['names_start'], info['names_end'], info['data_start']))
    gap = info['names_start'] - info['tbl_end']
    print('  表后空隙 %d B ⇒ 够放 391 条表记录' % gap)

    # 新数据放在容器尾料里（末尾对齐 4）
    last_end = max(e['off'] + e['stored'] for e in info['entries'])
    tail = size - last_end
    new_off = (last_end + 3) & ~3
    need = len(blob) + (new_off - last_end)
    print('  尾料 %d B ; 新数据 %d B ⇒ 需要 %d B  %s' % (tail, len(blob), need, '✓ 放得下' if need <= tail else '✗ 放不下'))
    if need > tail:
        print('  ⇒ 需要容器长大 ⇒ 会牵动 ISO9660 目录（本脚本不做）')
        return 2

    # ★ round 14 修正：**不动名字区**（条目记录里存的是指向名字区的索引/偏移，
    #   一旦移动名字区就会全部失效 —— 实测：移动后字库名 needle 从 1173 掉到 0、TLB Miss 4）
    #   正确做法：把新名字**追加在名字区末尾之后**（那里到数据区起点还有空隙）
    #   1) 求名字区真实末尾（越过它自身的结束字段，取最后一个非零字节之后）
    names_true_end = info['names_start']
    for i in range(info['names_end'], info['data_start']):
        if img[i] != 0:
            names_true_end = i + 1
    names_true_end = max(names_true_end, info['names_end'])
    add_blob = a.name.encode('latin-1') + b'\x00'
    if names_true_end + len(add_blob) > info['data_start']:
        print('  ✗ 名字区末尾到数据区间隙不足（需 %d B，只有 %d B）'
              % (len(add_blob), info['data_start'] - names_true_end))
        return 3
    print('  名字追加位置 0x%X（名字区声明末尾 0x%X / 数据起 0x%X）'
          % (names_true_end, info['names_end'], info['data_start']))

    if a.dry_run:
        print('  (dry-run：只报告，不写盘)')
        return 0

    out = bytearray(src)
    oi = base
    # 1) 写新数据到容器尾料
    out[oi + new_off: oi + new_off + len(blob)] = blob
    # 2) 写新表（原条目 + 新条目）
    newrec = list(info['entries'][0]['raw']) if info['entries'] else [0] * 12
    newrec[6] = len(blob)          # stored
    newrec[7] = len(blob)          # real
    newrec[8] = new_off            # off
    newrec[9] = 0
    for i, e in enumerate(info['entries']):
        struct.pack_into('<12I', out, oi + TAB_OFF + TAB_STEP * i, *e['raw'])
    struct.pack_into('<12I', out, oi + TAB_OFF + TAB_STEP * info['count'], *newrec)
    # 3) 名字追加（不动名字区本体，只把它的结束字段往后延）
    out[oi + names_true_end: oi + names_true_end + len(add_blob)] = add_blob
    # 4) 更新头：表结束 + 名字区结束（★ 名字区起始 u32[+0x10] 不动）
    struct.pack_into('<I', out, oi + 0x0C, info['tbl_end'] + TAB_STEP)
    struct.pack_into('<I', out, oi + 0x04, names_true_end + len(add_blob))
    open(a.dst, 'wb').write(bytes(out))
    print('  ✅ 已写出 %s' % a.dst)

    # 5) 自检：重新解析输出
    chk = parse(bytes(out[base:base + size]))
    print('  自检: 条目 %d（原 %d）; 名字 %d（原 %d）; 新条目 = %s'
          % (chk['count'], info['count'], len(chk['names']), len(info['names']),
             chk['names'][-1] if chk['names'] else '?'))
    e = chk['entries'][-1]
    print('        新条目 off=0x%X stored=%d real=%d' % (e['off'], e['stored'], e['real']))
    ok = (chk['count'] == info['count'] + 1 and len(chk['names']) == len(info['names']) + 1
          and chk['names'][-1] == a.name and e['off'] == new_off and e['stored'] == len(blob))
    print('        结构自检: %s' % ('✅ 通过' if ok else '✗ 失败'))
    return 0 if ok else 4


if __name__ == '__main__':
    sys.exit(main())
