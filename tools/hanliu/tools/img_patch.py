#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: gr_tools/img_patch.py (逐字复制 (IMG 安全补丁: 原地/空隙/追加))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""img_patch.py - Ghost Recon MENU.IMG/GR.IMG 安全补丁工具(空隙法+尾部追加法)

不重排任何现有条目(引擎依赖原始偏移), 仅:
  1. 优先把新内容放入档案尾部空隙(2048 对齐);
  2. 空隙不够时追加到档案末尾(需重建 ISO 以携带更大的 IMG);
  3. 目标条目以未压缩方式写回(stored==real, 引擎直接解析纯文本/XML);
  4. 其余条目一律不动。

用法:
  python img_patch.py <in.img> <out.img> NAME1=本地文件1 [NAME2=本地文件2 ...]
"""
import os, sys, struct

def align(n, a=2048):
    return (n + a - 1) // a * a

def parse_entries(data):
    tab_end   = struct.unpack_from('<I', data, 4)[0]
    names_off = struct.unpack_from('<I', data, 0x10)[0]
    names = [x.decode('latin-1') for x in data[names_off:tab_end].split(b'\x00') if x]
    ents = {}
    for i, nm in enumerate(names):
        r = struct.unpack_from('<12I', data, 0x830 + 48 * i)
        ents[nm] = {'i': i, 'name': nm, 'stored': r[6], 'real': r[7], 'off': r[8]}
    return ents

def patch(in_img, out_img, repl, framed=False, inplace=True):
    data = bytearray(open(in_img, 'rb').read())
    ents = parse_entries(bytes(data))
    missing = [n for n in repl if n not in ents]
    if missing:
        raise SystemExit('档案中不存在: %s' % missing)

    img_size = len(data)
    last_end = max(e['off'] + e['stored'] for e in ents.values())
    gap_start = align(last_end)
    # 空隙里可能已经放过的内容不计入(以原条目为准); 新写入从 gap_start 或 img_size 追加
    cursor = gap_start
    appended = False
    for name, local in repl.items():
        content = open(local, 'rb').read()
        e = ents[name]
        need = len(content)
        real = need
        if framed and need >= 8:
            # 框架式(压缩风格)写回: 文件头 {u32 payload_len}{u32 out_size},引擎解得 out_size
            plen, out = struct.unpack_from('<II', content, 0)
            if plen + 8 == need and 0 < out <= 4_000_000:
                real = out
        if inplace and need <= e['stored'] and e['off']:
            # 尺寸不超过原条目占地 → 原地覆写(最安全, 不动布局)
            off = e['off']
            data[off:off + need] = content
            how = 'inplace'
        elif cursor + need <= img_size:
            off = cursor
            data[off:off + need] = content
            cursor = align(off + need)
            how = 'gap'
        else:
            off = align(img_size)
            data.extend(b'\x00' * (off - img_size))
            data.extend(content)
            img_size = len(data)
            appended = True
            how = 'append'
        struct.pack_into('<I', data, 0x830 + 48 * e['i'] + 24, need)   # stored
        struct.pack_into('<I', data, 0x830 + 48 * e['i'] + 28, real)   # real
        struct.pack_into('<I', data, 0x830 + 48 * e['i'] + 32, off)    # off
        print('%-24s -> off=0x%08X stored=%6d real=%6d (%s)' % (name, off, need, real, how))
    struct.pack_into('<I', data, 0, img_size)  # 档案总大小
    open(out_img, 'wb').write(data)
    print('已写出 %s: %d 字节 (追加=%s)' % (out_img, img_size, appended))

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    args = sys.argv[3:]
    keep = '--framed' in args
    no_inplace = '--no-inplace' in args
    args = [a for a in args if a not in ('--framed', '--no-inplace')]
    repl = dict(x.split('=', 1) for x in args)
    patch(sys.argv[1], sys.argv[2], repl, framed=keep, inplace=not no_inplace)
