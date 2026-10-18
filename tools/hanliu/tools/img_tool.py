#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: gr_tools/img_tool.py (逐字复制 (IMG 列表/解包/重建))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""
img_tool.py - Ghost Recon PS2 (ike引擎) .IMG 档案工具

已破解的档案结构 (GR.IMG / MENU.IMG):
  偏移0   u32  档案总大小
  偏移4   u32  名字表结束偏移 (也是条目表/名字区界线)
  偏移8   u32  块大小 2048
  偏移C   u32  条目表结束偏移 (0x830 + 48*文件数)
  偏移10  u32  名字表起始偏移
  偏移14  u32  数据区起始偏移 (2048对齐)
  偏移18  u32  1
  偏移20  u32  哈希表偏移 (4096项×4字节, 0xFFFFFFFF=空, 值=文件索引)
  0x800   48字节 头部块
  0x830   条目表: 每文件48字节×12个u32:
          +0   名字表内偏移
          +1   类型/校验相关
          +24  存储大小 (stored)
          +28  解压大小 (real, ==stored 则未压缩)
          +32  数据偏移
  名字表  \0 结尾的名字串, 顺序=条目顺序
  数据区  2048对齐, 文件按偏移排列, 16字节对齐

用法:
  python img_tool.py list    <img>
  python img_tool.py extract <img> <outdir>          解包(未压缩文件全部成功; 压缩文件按字面量层尽力解码)
  python img_tool.py replace <img> <outfile> <名称=新文件> [...]
          替换文件内容(以未压缩方式存回), 重建条目表与偏移; 名字/顺序不变故哈希表可原样保留
  python img_tool.py rebuild <img> <outfile> <repldir>
          同上, 但从目录读取替换 (目录内文件名 = 档案内名字)
"""
import os, re, sys, struct

def parse_entries(data):
    tab_end  = struct.unpack_from('<I', data, 4)[0]
    et_end   = struct.unpack_from('<I', data, 0x0C)[0]
    names_off= struct.unpack_from('<I', data, 0x10)[0]
    dat_off  = struct.unpack_from('<I', data, 0x14)[0]
    hash_off = struct.unpack_from('<I', data, 0x20)[0]
    names = [x.decode('latin-1') for x in data[names_off:tab_end].split(b'\x00') if x]
    N = len(names)
    ents = []
    for i in range(N):
        r = struct.unpack_from('<12I', data, 0x830 + 48*i)
        ents.append({'i':i,'name':names[i],'f0':r[0],'f1':r[1],
                     'stored':r[6],'real':r[7],'off':r[8],'f9':r[9]})
    return {'tab_end':tab_end,'et_end':et_end,'names_off':names_off,
            'dat_off':dat_off,'hash_off':hash_off,'N':N}, ents

def cmd_list(path):
    data = open(path,'rb').read()
    hdr, ents = parse_entries(data)
    for e in sorted(ents, key=lambda x:x['off']):
        tag = 'RAW ' if e['stored']==e['real'] else 'LZ77'
        print('%-9s off=0x%08X stored=%8d real=%8d  %s'%(
            tag, e['off'], e['stored'], e['real'], e['name']))
    print('共 %d 个文件'%hdr['N'])

def extract(path, outdir):
    data = open(path,'rb').read()
    hdr, ents = parse_entries(data)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gr_lz import decompress_stream
    okr=okc=fail=0
    for e in sorted(ents, key=lambda x:x['off']):
        raw = data[e['off']:e['off']+e['stored']]
        if e['stored']==e['real']:
            content, note = raw, ''
            okr+=1
        else:
            content, err = decompress_stream(raw)
            if content is None:
                content, note = raw, ' (解码失败: %s, 原样导出)'%err
                fail+=1
            else:
                note=''; okc+=1
        dst = os.path.join(outdir, e['name'].replace('..','__'))
        os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
        open(dst,'wb').write(content)
        print('%-40s %8d %s'%(e['name'], len(content), note))
    print('完成: 未压缩=%d 解码=%d 失败=%d'%(okr,okc,fail))

def align(n, a): return (n + a - 1)//a*a

def rebuild(path, outfile, repl):
    """repl: {档案内名字: 本地文件路径}  全部以未压缩方式写回"""
    data = bytearray(open(path,'rb').read())
    hdr, ents = parse_entries(bytes(data))
    missing = [n for n in repl if n not in {e['name'] for e in ents}]
    if missing:
        raise SystemExit('档案中不存在: %s'%missing)
    # 新内容
    newdata = {}
    for name, local in repl.items():
        newdata[name] = open(local,'rb').read()
    # 名字表保持不变(名字与顺序不动) => 哈希表/名字偏移不变
    names_off = hdr['names_off']
    out = bytearray()
    out += data[:hdr['dat_off']]           # 头部+条目表占位(稍后回填)+名字表+哈希表
    # 数据区按原偏移顺序重排
    cur = hdr['dat_off']
    body = bytearray()
    newents = {}
    for e in sorted(ents, key=lambda x:x['off']):
        content = newdata.get(e['name']) or data[e['off']:e['off']+e['stored']]
        off = hdr['dat_off'] + len(body)
        body += content
        pad = align(len(body),16) - len(body)
        body += b'\x00'*pad
        newents[e['i']] = (off, len(content), len(content))
    # 回填条目表
    for e in ents:
        off, stored, real = newents[e['i']]
        struct.pack_into('<I', out, 0x830 + 48*e['i'] + 24, stored)
        struct.pack_into('<I', out, 0x830 + 48*e['i'] + 28, real)
        struct.pack_into('<I', out, 0x830 + 48*e['i'] + 32, off)
    # 回填总大小
    total = hdr['dat_off'] + len(body)
    struct.pack_into('<I', out, 0, total)
    out += body
    open(outfile,'wb').write(out)
    print('已重建 %s: %d 文件, %d 字节, 替换 %d 个'%(outfile, hdr['N'], total, len(repl)))

def main():
    if len(sys.argv)<3:
        print(__doc__); return
    cmd = sys.argv[1]
    if cmd=='list': cmd_list(sys.argv[2])
    elif cmd=='extract': extract(sys.argv[2], sys.argv[3])
    elif cmd=='replace':
        repl = dict(x.split('=',1) for x in sys.argv[4:])
        rebuild(sys.argv[2], sys.argv[3], repl)
    elif cmd=='rebuild':
        d = sys.argv[4]
        repl = {n: os.path.join(d,n) for n in os.listdir(d)}
        rebuild(sys.argv[2], sys.argv[3], repl)
    else: print(__doc__)

if __name__=='__main__':
    main()
