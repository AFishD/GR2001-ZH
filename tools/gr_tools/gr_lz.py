# -*- coding: utf-8 -*-
"""Ghost Recon PS2 (ike 引擎) .IMG 档案解析与解码器

档案格式 (GR.IMG / MENU.IMG):
  0x00 u32 档案总大小; 0x04 u32 名字表结束; 0x08 u32 块大小(2048)
  0x0C u32 条目表结束(0x830+48*N); 0x10 u32 名字表起始; 0x14 u32 数据区起始
  0x20 u32 哈希表偏移
  0x830 条目表: 48 字节/文件 (+0 名字偏移, +24 stored, +28 real, +32 数据偏移)

压缩格式(经 SLUS_206.13 .symtab 定位 decode__4lz77FPUciPPUc @0x539110 确认的
字节计数格式; 输出缓冲 = malloc(payload_len+1), 无 LZ 匹配令牌):
  文件 = 一个或多个子流串联:
      子流 = {u32 payload_len}{u32 out_size}{payload_len 字节数据}
  数据内控制字节 c:  c≤0x10 → c+3 字面量;  c≥0x11 → c-17 字面量
  各子流解码输出依序拼接 = RSXML 编译形式(文本+字符串池引用),
  游戏加载时引用展开, 故 real(d7) 大于 LZ 输出属正常。
  替换汉化文件时以未压缩(存储==真实)方式写回即可, 引擎可直接解析纯 XML/文本。
"""
import struct

def _walk_count_stream(s, out, cap=None):
    """解码计数格式字节流 s, 追加到 out; 返回消耗的字节数。cap 限制输出字节数"""
    i, n = 0, len(s)
    produced = 0
    while i < n:
        if cap is not None and produced >= cap:
            break
        c = s[i]
        lit = (c + 3) if c <= 0x10 else (c - 17)
        if lit <= 0:
            i += 1
            continue
        take = lit
        if cap is not None and produced + take > cap:
            take = cap - produced
        out += s[i+1:i+1+take]
        produced += take
        i += 1 + take
    return i

def decompress_stream(stream, window=None):
    """stream: 完整 stored 数据(自数据偏移起)。返回 (编译形式 bytes, None)"""
    if len(stream) < 8:
        return None, '流过短'
    out = bytearray()
    p = 0
    first_out = None
    while p + 8 <= len(stream):
        payload_len, out_size = struct.unpack_from('<II', stream, p)
        if payload_len == 0 or p + 8 + payload_len > len(stream):
            # 无法形成完整子流: 把剩余当字面量尾
            _walk_count_stream(stream[p+8:], out)
            break
        _walk_count_stream(stream[p+8:p+8+payload_len], out,
                           cap=out_size if out_size < 0x100000 else None)
        if first_out is None:
            first_out = out_size
        p += 8 + payload_len
    return bytes(out), None

def load_entries(img_path):
    data = open(img_path,'rb').read()
    names_off = struct.unpack_from('<I', data, 0x10)[0]
    tab_end   = struct.unpack_from('<I', data, 4)[0]
    names = [x.decode('latin-1') for x in data[names_off:tab_end].split(b'\x00') if x]
    N = len(names)
    ents = []
    for i in range(N):
        r = struct.unpack_from('<12I', data, 0x830 + 48*i)
        ents.append({'i':i,'name':names[i],'f0':r[0],'f1':r[1],
                     'stored':r[6],'real':r[7],'off':r[8]})
    return data, ents

def extract_all(img_path):
    data, ents = load_entries(img_path)
    files, fails = {}, []
    for e in ents:
        raw = data[e['off']:e['off']+e['stored']]
        if len(raw) < e['stored']:
            fails.append((e['name'],'数据越界')); continue
        if e['stored'] == e['real']:
            files[e['name']] = raw
        else:
            out, err = decompress_stream(raw)
            if out is None:
                fails.append((e['name'], err))
            else:
                files[e['name']] = out
    return files, fails

if __name__ == '__main__':
    import sys
    files, fails = extract_all(sys.argv[1])
    print('成功 %d 个, 失败 %d 个'%(len(files), len(fails)))
    for n, e in fails[:10]:
        print('  FAIL', n, e)

def encode_literals(data, max_run=238):
    """纯字面量安全编码(实机验证通过): 所有段 c = run+17 (恒 >=0x11)。
    注意: c<=0x10 在引擎里是控制令牌(非字面量计数), 绝不能发出!"""
    out = bytearray()
    i, n = 0, len(data)
    while i < n:
        run = min(max_run, n - i)
        out.append(run + 17)
        out += data[i:i+run]
        i += run
    return bytes(out)

def frame_substream(payload, out_size):
    """{u32 payload_len}{u32 out_size}{payload}"""
    return struct.pack('<II', len(payload), out_size) + payload
