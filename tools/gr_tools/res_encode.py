#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""res_encode.py - Ghost Recon PS2 (ike 引擎) *_STRINGS.RES 解析/重编码器 (2026-09-12)

== 格式结论 (EN/DE/ES/FR/IT 五语言 RES 全量验证, 见 han_v2\RES_FORMAT.md) ==

MENU.IMG 里的 EN_STRINGS.RES 条目是 LZ 压缩态: 子流串联
    {u32 plen}{u32 osz}{LZO1X payload} × N          (用同目录 lz77_decode.py 解码)
全部子流 osz 之和 = 条目表 real 字段 (EN: 8 子流, real=128545)。

解压后的"展开态"(引擎 strings 解析器实际消费, 也即 stored==real 未压缩写回
时直接提供的形式):

    u32  num_groups (=66)
    ---- 组 1 (无 sep 字段) ----
    u32  count1
    count1 × 条目
    ---- 组 2..num_groups ----
    u32  sep                       -- 恒为 0 (DE/IT 偶见 1)
    sep  × 附加串 {u32 len}{bytes} -- 注意: 无 00 00 终止符 (本地化残留碎片)
    u32  count
    count × 条目
    ---- 结束 ----
    u32 0, u32 0                   -- 终止符

    条目 = {u32 len}{bytes(len)}{u16 attr}   -- attr 恒 0x0000 (EN 全部为 0;
           DE/IT 极个别 0x8000, 出现在含 {p} 分页标记的条目)
    字节内容 = Latin-1 区字节, 0x00-0xFF 任意(EN 原文含 0x92/0xAE/0xB1/0xB5/0xE7/0xF1),
    无转义、无对齐、无偏移表; 组与字符串全部顺序排列, 长度自描述。

轮转验证: parse->build 与展开态原文逐字节一致 (encode(parse(x)) == x)。
存储态(LZO1X)不做字节级再压缩 (压缩器选点无法复现), 写回走未压缩
stored==real 路径 (img_patch.py 默认), 引擎可解析; 或用 --framed-lzo 输出
单子流贪心 LZO1X 压缩框架文件 (内含解码自检) 配 img_patch.py --framed。

== 文本同构格式 (与 GR_EN_STRINGS_RES_decoded.bin 同构的文本形式) ==

    # 注释行/空行忽略
    [G01] sep=0          <- 组头, sep=N (组 1 恒 sep=0 且不写入文件)
    E0=...               <- 附加串 (仅 sep>0 时, 放在 I 行之前)
    I000=Victory!        <- 字符串, I 序号必须连续
    I008[8000]=...       <- attr 非 0 的条目 (少见, 保真用)
    ...
    [G66] sep=0
    ...

转义: `\\\\` `\\n` `\\r` `\\t` `\\xNN`(任意字节), 其余 0x20-0x7E 原样。

== 用法 ==
  python res_encode.py parse  <in.res|展开态> <out.txt>
  python res_encode.py build  <in.txt> <out.res> [--framed-lzo out.framed]
  python res_encode.py round  <in.res>              # parse->build 与展开态逐字节比对
  python res_encode.py mod    <in.res> <out.res> <G> <I> <oldchar> <newbyte_hex>
  python res_encode.py probe  <in.res>              # 结构摘要
"""
import struct
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from lz77_decode import decode_entry
except ImportError:
    decode_entry = None


# ---------------------------------------------------------------- 基础结构

class Group:
    __slots__ = ('sep', 'extras', 'strings')

    def __init__(self, sep=0, extras=None, strings=None):
        self.sep = sep            # 组 1 为 None (文件中无此字段)
        self.extras = extras or []  # list[bytes], 无 00 00 终止符
        self.strings = strings or []  # list[bytes]

    def __repr__(self):
        return 'Group(sep=%r, extras=%d, strings=%d)' % (
            self.sep, len(self.extras), len(self.strings))


def is_lzo_stored(data):
    """粗判: 是否 LZO 子流框架 (首子流 plen+8 落在文件内且 plen != osz)。"""
    if len(data) < 16:
        return False
    plen, osz = struct.unpack_from('<II', data, 0)
    return 0 < plen and 8 + plen <= len(data) and plen != osz


def expand_entry(data):
    """存储态 -> 展开态。已是展开态则原样返回。"""
    if not is_lzo_stored(data):
        return data
    if decode_entry is None:
        raise RuntimeError('存储态条目需要 lz77_decode.py (同目录)')
    out, stats = decode_entry(data)
    bad = [s for s in stats if s[3]]
    if bad:
        raise RuntimeError('LZO 子流解码失败: %s' % bad)
    return out


def parse_expanded(data):
    """展开态 -> [Group]。任何字段不符即抛异常 (严格模式)。"""
    n = len(data)

    def u32(p):
        if p + 4 > n:
            raise ValueError('越界 @0x%X' % p)
        return struct.unpack_from('<I', data, p)[0]

    p = 0
    ng = u32(p)
    p += 4
    if not 1 <= ng <= 4096:
        raise ValueError('num_groups=%d 可疑' % ng)
    groups = []
    for gi in range(ng):
        if gi == 0:
            sep = None
            cnt = u32(p)
            p += 4
            extras = []
        else:
            sep = u32(p)
            p += 4
            extras = []
            for _ in range(sep):
                ln = u32(p)
                p += 4
                if p + ln > n:
                    raise ValueError('附加串越界 @0x%X' % p)
                extras.append(data[p:p + ln])
                p += ln                  # 无 00 00 终止符
            cnt = u32(p)
            p += 4
        if cnt > 0x10000:
            raise ValueError('组 %d count=%d 可疑 @0x%X' % (gi + 1, cnt, p))
        grp = Group(sep, extras, [])
        for _ in range(cnt):
            ln = u32(p)
            p += 4
            if p + ln + 2 > n:
                raise ValueError('条目越界 @0x%X (len=%d)' % (p, ln))
            attr = struct.unpack_from('<H', data, p + ln)[0]   # u16 属性字段
            grp.strings.append((data[p:p + ln], attr))
            p += ln + 2
        groups.append(grp)
    if p + 8 > n or data[p:p + 8] != b'\x00\x00\x00\x00\x00\x00\x00\x00':
        raise ValueError('尾部缺 {0}{0} 终止符 @0x%X' % p)
    p += 8
    if p != n:
        raise ValueError('多余尾字节 %d @0x%X' % (n - p, p))
    return groups


def build_expanded(groups):
    """[Group] -> 展开态 bytes (与原文件逐字节一致的规范序列化)。"""
    out = bytearray()
    out += struct.pack('<I', len(groups))
    for gi, g in enumerate(groups):
        if gi > 0:
            out += struct.pack('<I', g.sep)
            for e in g.extras:
                out += struct.pack('<I', len(e)) + e
        out += struct.pack('<I', len(g.strings))
        for s, attr in g.strings:
            out += struct.pack('<I', len(s)) + s
            out += struct.pack('<H', attr)
    out += struct.pack('<II', 0, 0)
    return bytes(out)


# ---------------------------------------------------------------- 文本同构

_ESC = {'\\': '\\\\', '\n': '\\n', '\r': '\\r', '\t': '\\t'}


def esc(raw):
    out = []
    for b in raw:
        c = chr(b)
        if c in _ESC:
            out.append(_ESC[c])
        elif 0x20 <= b <= 0x7E:
            out.append(c)
        else:
            out.append('\\x%02x' % b)
    return ''.join(out)


def unesc(line):
    out = bytearray()
    i = 0
    while i < len(line):
        c = line[i]
        if c != '\\':
            o = ord(c)
            if o > 0x7E:
                raise ValueError('未转义高位字符 %r' % c)
            out.append(o)
            i += 1
            continue
        nxt = line[i + 1]
        if nxt == '\\':
            out.append(0x5C)
            i += 2
        elif nxt == 'n':
            out.append(0x0A)
            i += 2
        elif nxt == 'r':
            out.append(0x0D)
            i += 2
        elif nxt == 't':
            out.append(0x09)
            i += 2
        elif nxt in 'xX':
            out.append(int(line[i + 2:i + 4], 16))
            i += 4
        else:
            raise ValueError('未知转义 \\%s' % nxt)
    return bytes(out)


def save_text(groups, path):
    with open(path, 'w', encoding='ascii', newline='\n') as f:
        f.write('# RES_TEXT v1 -- *_STRINGS.RES text-isomorphic format (res_encode.py)\n')
        f.write('# syntax: [Gnn] sep=N | Ek=<esc> | Innov=<esc>\n')
        f.write('# escapes: \\\\ \\n \\r \\t \\xNN ; other 0x20-0x7E literal\n')
        for gi, g in enumerate(groups, 1):
            f.write('[G%02d] sep=%d\n' % (gi, g.sep or 0))
            for k, e in enumerate(g.extras):
                f.write('E%d=%s\n' % (k, esc(e)))
            for si, (s, attr) in enumerate(g.strings):
                key = 'I%03d' % si if attr == 0 else 'I%03d[%04X]' % (si, attr)
                f.write('%s=%s\n' % (key, esc(s)))


def load_text(path):
    groups = []
    cur = None
    with open(path, 'r', encoding='ascii') as f:
        for no, ln in enumerate(f, 1):
            ln = ln.rstrip('\r\n')
            if not ln or ln.startswith('#'):
                continue
            if ln.startswith('[G'):
                tail = ln[ln.index(']') + 1:].strip()
                sep = int(tail.split('=')[1])
                cur = Group(sep if len(groups) > 0 else None)
                groups.append(cur)
                continue
            if '=' not in ln:
                raise ValueError('第 %d 行缺少 "=": %r' % (no, ln))
            key, val = ln.split('=', 1)
            raw = unesc(val)
            if key.startswith('E'):
                cur.extras.append(raw)
            elif key.startswith('I'):
                m = re.fullmatch(r'I(\d{3,})(?:\[([0-9A-Fa-f]{1,4})\])?', key)
                if not m:
                    raise ValueError('第 %d 行键名非法: %r' % (no, key))
                idx = int(m.group(1))
                attr = int(m.group(2), 16) if m.group(2) else 0
                if idx != len(cur.strings):
                    raise ValueError('第 %d 行序号 %s 不连续 (应为 I%03d)'
                                     % (no, key, len(cur.strings)))
                cur.strings.append((raw, attr))
            else:
                raise ValueError('第 %d 行键名非法: %r' % (no, key))
    return groups


# ------------------------------------------------- LZO1X 压缩 (可选写回)

def lzo1x_compress(data, max_back=16384):
    """贪心 LZO1X 压缩器 (仅 M3 匹配 + 长字面量段, 均为解码器已验证语法):
      - 首令牌 x>17 -> x-17 字面量 (1..238)
      - 长字面量段: x in 1..15 -> (x&15)+3 (4..18 字节); x=0+扩展字节 -> 19..273
        (连续两个长字面量段不合法, 字面量段之间必须有匹配令牌)
      - M3 匹配: [32|cnt][b1][b2]: len = cnt+2 (cnt=0 走扩展), back = (b2<<6)+(b1>>2)+1,
        b1&3 = 匹配后置字面量数
    输出必须经 lzo1x_decompress 自检 (cmd_build 已做, 失败则拒绝)。"""
    from lz77_decode import lzo1x_decompress
    n = len(data)
    out = bytearray()
    pos = {}                       # 3-gram -> 最近出现位置
    first = min(238, n)
    out.append(first + 17)
    out += data[:first]
    i = first
    for k in range(min(i, max(0, n - 2))):
        pos[data[k:k + 3]] = k
    pending = i                    # 待编码字面量起点

    def find_match(p):
        if p + 3 > n:
            return 0, 0
        j = pos.get(bytes(data[p:p + 3]), -1)
        if j < 0:
            return 0, 0
        back = p - j
        if back > max_back:
            return 0, 0
        l = 3
        while l < 288 and p + l < n and data[j + l] == data[p + l]:
            l += 1
        return l, back

    def flush_literals(end, last_match_done):
        """把 pending..end 的字面量编码出去 (要求长度>=4, 或并入尾令牌)。"""
        nonlocal pending
        r = end - pending
        if r == 0:
            return
        assert r >= 4, '字面量段 %d 字节无法编码 (1..3 需并入匹配后置字段)' % r
        assert r <= 273, '字面量段 %d 字节超长 (>273)' % r
        if r <= 18:
            out.append(r - 3)
        else:
            out.append(0)
            rem = r - 3
            while rem > 270:       # 扩展: cnt = 255*k + 15 + b, len = cnt+3
                out.append(0)
                rem -= 255
            assert 16 <= rem <= 270
            out.append(rem - 15)
        out.extend(data[pending:end])
        pending = end

    while i < n:
        l, back = find_match(i)
        if l >= 3 and i - pending < 4 and pending < i:
            # 字面量残留 1..3 字节无法单独成段 -> 匹配起点后移补足到 4
            shift = 4 - (i - pending)
            l2, back2 = find_match(i + shift)
            if l2 >= 3:
                flush_literals(i + shift, False)
                l, back = l2, back2
                i += shift
                shift_used = True
            else:
                # 放弃在 i 的匹配, 当前字节并入字面量
                if i + 3 <= n:
                    pos[data[i:i + 3]] = i
                i += 1
                continue
        elif l >= 3:
            flush_literals(i, False)
        if l >= 3:
            # M3 令牌
            if l <= 33:
                out.append(32 | (l - 2))
            else:
                out.append(32)
                rem = l - 2
                while rem > 286:   # cnt = 255*k + 31 + b, len = cnt+2
                    out.append(0)
                    rem -= 255
                assert 32 <= rem <= 286
                out.append(rem - 31)
            out.append(((back - 1) & 0x3F) << 2)   # b1, 后置字面量 = 0
            out.append((back - 1) >> 6)            # b2
            for k in range(i, i + l):
                if k + 3 <= n:
                    pos[data[k:k + 3]] = k
            i += l
            pending = i
        else:
            if i + 3 <= n:
                pos[data[i:i + 3]] = i
            i += 1
    # 尾部字面量: 1..3 -> 并入最后匹配的后置字段不可能 (已在中间), 直接要求 >=4;
    # 不足时回退: 截断最后 1 个匹配让它后移?? — 实际文本不会发生, 报错即可
    if n - pending:
        tail = n - pending
        if tail <= 3:
            raise RuntimeError('尾部残留 %d 字节无法编码, 请用未压缩写回' % tail)
        flush_literals(n, True)
    out += b'\x10\x00\x00'         # M1 back==1<<14 流结束标记 (3 字节尾域)
    payload = bytes(out)
    back2, err, _ = lzo1x_decompress(payload, out_size=n)
    if err is not None or back2 != data:
        raise RuntimeError('LZO1X 自检失败: %s' % err)
    return payload


def frame_literal_lzo(data):
    """单子流框架 {u32 plen}{u32 osz}{LZO1X payload}, plen+8 = 文件长,
    配合 img_patch.py --framed (real 字段 = osz)。内含解码自检。"""
    payload = lzo1x_compress(data)
    return struct.pack('<II', len(payload), len(data)) + payload


# ---------------------------------------------------------------- 命令行

def _load_any(path):
    """读入文件: 优先按展开态严格解析, 失败再按 LZO 存储态解码。"""
    data = open(path, 'rb').read()
    try:
        return data, data, parse_expanded(data)
    except ValueError:
        pass
    exp = expand_entry(data)
    return data, exp, parse_expanded(exp)


def cmd_parse(argv):
    _, exp, groups = _load_any(argv[0])
    save_text(groups, argv[1])
    print('%s -> %s: %d 组 %d 条' % (argv[0], argv[1], len(groups),
                                     sum(len(g.strings) for g in groups)))


def cmd_build(argv):
    framed_out = None
    if '--framed-lzo' in argv:
        k = argv.index('--framed-lzo')
        framed_out = argv[k + 1]
        argv = argv[:k] + argv[k + 2:]
    groups = load_text(argv[0])
    blob = build_expanded(groups)
    open(argv[1], 'wb').write(blob)
    print('%s -> %s: %d 字节 (展开态, stored==real 未压缩写回)'
          % (argv[0], argv[1], len(blob)))
    if framed_out:
        fr = frame_literal_lzo(blob)
        open(framed_out, 'wb').write(fr)
        back, err, _ = __import__('lz77_decode').lzo1x_decompress(
            fr[8:], out_size=len(blob))
        assert err is None and back == blob, '框架自检失败'
        print('  %s: %d 字节 (纯字面量 LZO1X 单子流, 解码自检 ✓, '
              '配 img_patch.py --framed)' % (framed_out, len(fr)))


def cmd_round(argv):
    stored, exp, groups = _load_any(argv[0])
    rebuilt = build_expanded(groups)
    ok = rebuilt == exp
    print('源文件          : %s (%d 字节, %s)'
          % (argv[0], len(stored),
             'LZO 存储态' if stored is not exp else '展开态'))
    print('展开态          : %d 字节' % len(exp))
    print('parse -> build  : %d 字节' % len(rebuilt))
    print('逐字节一致      : %s' % ('PASS ✓' if ok else 'FAIL ✗'))
    if not ok:
        d = next(i for i in range(min(len(rebuilt), len(exp)))
                 if rebuilt[i] != exp[i])
        print('首个差异 @0x%X: %s != %s' % (d, rebuilt[d - 8:d + 8].hex(' '),
                                            exp[d - 8:d + 8].hex(' ')))
    # 文本轮转
    save_text(groups, '__round__.txt')
    groups2 = load_text('__round__.txt')
    t_ok = build_expanded(groups2) == exp
    print('文本往返一致    : %s' % ('PASS ✓' if t_ok else 'FAIL ✗'))
    os.remove('__round__.txt')
    if not (ok and t_ok):
        return 2
    return 0


def cmd_mod(argv):
    res, out, G, I, oldc, newb = argv[0], argv[1], int(argv[2]), int(argv[3]), \
        argv[4], int(argv[5], 16)
    stored, exp, groups = _load_any(res)
    s = groups[G - 1].strings[I][0]
    pos = s.index(ord(oldc))
    groups[G - 1].strings[I] = (s[:pos] + bytes([newb]) + s[pos + 1:],
                                groups[G - 1].strings[I][1])
    blob = build_expanded(groups)
    open(out, 'wb').write(blob)
    # 自检: 重解析 + 与原文逐字节 diff
    groups2 = parse_expanded(blob)
    assert groups2[G - 1].strings[I] == groups[G - 1].strings[I]
    diff = [i for i in range(min(len(blob), len(exp)))
            if blob[i] != exp[i]] + list(range(min(len(blob), len(exp)),
                                               max(len(blob), len(exp))))
    print('G%02d.I%03d: %r -> 已把 0x%02X (@串内偏移 %d) 改为 0x%02X'
          % (G, I, s[:40], ord(oldc), pos, newb))
    print('原文 %d 字节 -> 新 %d 字节 (Δ=%+d); 重解析 ✓; 与原文差异字节数 = %d'
          % (len(exp), len(blob), len(blob) - len(exp), len(diff)))
    print('差异位置: %s' % [hex(x) for x in diff[:8]])
    print('写回: %s (stored=real=%d, 用 img_patch.py 直接替换)' % (out, len(blob)))
    return 0


def cmd_probe(argv):
    _, exp, groups = _load_any(argv[0])
    print('展开态 %d 字节, %d 组, %d 条字符串' %
          (len(exp), len(groups), sum(len(g.strings) for g in groups)))
    for gi, g in enumerate(groups, 1):
        mark = ''
        if g.sep:
            mark = '  sep=%d extras=%s' % (g.sep, [esc(e) for e in g.extras])
        head = ' | '.join(x[0][:28].decode('latin-1') for x in g.strings[:2])
        print('G%02d n=%-4d %s%s' % (gi, len(g.strings), head, mark))
    hi = {}
    for g in groups:
        for s, _attr in g.strings:
            for b in s:
                if b > 0x7E:
                    hi.setdefault(b, 0)
                    hi[b] += 1
    print('高位字节: %s' % {'0x%02X' % b: c for b, c in sorted(hi.items())})


def main(argv):
    cmds = {'parse': (cmd_parse, 2), 'build': (cmd_build, 2),
            'round': (cmd_round, 1), 'mod': (cmd_mod, 6),
            'probe': (cmd_probe, 1)}
    if len(argv) < 2 or argv[0] not in cmds:
        print(__doc__)
        return 1
    fn, need = cmds[argv[0]]
    args = argv[1:]
    # build 的 --framed-lzo 带附加参数
    if argv[0] == 'build':
        return fn(args)
    if len(args) < need:
        print(__doc__)
        return 1
    return fn(args)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
