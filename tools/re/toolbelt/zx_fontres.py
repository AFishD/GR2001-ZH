# -*- coding: utf-8 -*-
r"""zx_fontres.py — FONT.RES 结构解剖 + **压缩流原位字节替换**可行性试验（只读，不写盘）

目的（Route A 唯一的新风险点）:
  搬两条活带 ⇒ 必须把 332 条记录的 v0/v1 从 (452,468)/(482,498) 改成 (594,610)/(610,626)。
  若能在**压缩流里原位替换那几个字面量字节**，则 stored 长度不变（4421 B）、
  布局位移恰好 = +66,016，四条"必须一致的数"全部成立。

本工具做四件事:
  [1] FONT.RES 槽 (4421 B) 的完整结构解剖（头/名字/LZO 载荷/其它）
  [2] 解出 5942 B 展开态，定位 332 条目标记录 v0/v1 的**展开态偏移**
  [3] 带来源追踪的 LZO1X 解码 ⇒ 把每个"必须变的展开态字节"映射到**压缩流字节位置**
      （只允许字面量；匹配拷贝要能追到唯一字面量；冲突即判不可行）
  [4] 应用替换 → 重新解码 → 逐字节断言：只有那 332×4 个字节变了，长度仍 5942
"""
import os
import struct
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'gr_tools'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib                                                       # noqa: E402
from lz77_decode import decode_entry, lzo1x_decompress              # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82')
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
MENU_LBA = tcslib.MENU_LBA
LS = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LS.append(s)


iso = tcslib.Iso(ISO)
e4 = iso.img_entry(MENU_LBA, 4)
slot = iso.read(e4['iso_off'], e4['stored'])
P('FONT.RES #4 off=0x%X stored=%d real=%d' % (e4['off'], e4['stored'], e4['real']))
P('')
P('=' * 78)
P('[1] 槽结构解剖 (%d B)' % len(slot))
P('=' * 78)
hdr3 = struct.unpack_from('<3I', slot, 0)
P('  头 12 B = %s (= %s)' % (hdr3, ', '.join('%d' % v for v in hdr3)))
for off in range(0, 96, 16):
    P('   +0x%04X  %s' % (off, ' '.join('%02X' % b for b in slot[off:off + 16])))
P('  尾部 32 B:')
for off in range(len(slot) - 32, len(slot), 16):
    P('   +0x%04X  %s' % (off, ' '.join('%02X' % b for b in slot[off:off + 16])))

exp, _ = decode_entry(slot)
P('  decode_entry → %d B' % len(exp))

# 结构搜索: 所有 {u32 comp}{u32 real} 且 comp 字节能解出 real 字节的位置
P('')
P('  结构扫描 (找到的 {comp}{real}+payload):')
found = []
for off in range(0, min(len(slot) - 8, 2048)):
    a, b = struct.unpack_from('<II', slot, off)
    if not (0 < a < len(slot) - off - 8) or not (0 < b <= 1 << 20):
        continue
    try:
        dec, err, _ = lzo1x_decompress(slot[off + 8:off + 8 + a], out_size=b)
    except Exception:                                              # noqa: BLE001
        continue
    if err is None and len(dec) == b:
        found.append((off, a, b, dec))
        P('    +0x%04X  comp=%-6d real=%-6d  ⇒ 解出 %d B' % (off, a, b, len(dec)))
        if len(found) >= 4:
            break
if not found:
    P('    (无)')

P('')
P('=' * 78)
P('[2] 目标记录 v0/v1 的展开态偏移')
P('=' * 78)
he, faces = tcslib.parse_ft_faces(exp)
P('  faces 结束 @0x%X ; 展开态共 %d B' % (he, len(exp)))
# 重算记录偏移: parse_ft_faces 的顺序遍历
p = 28
targets = {}                    # out_off -> new_byte
n_v = 0
for (nm, fld, recs) in faces:
    l = struct.unpack_from('<I', exp, p)[0]
    p += 4 + l
    fldoff = p
    p += 56
    nrec = fld[4] * fld[5]
    for r in range(nrec):
        ro = p + 10 * r
        b0, b1, u0, v0, u1, v1 = struct.unpack_from('<BB4H', exp, ro)
        if (v0, v1) == (452, 468):
            nv0, nv1 = 594, 610
        elif (v0, v1) == (482, 498):
            nv0, nv1 = 610, 626
        else:
            continue
        assert u1 > u0
        n_v += 1
        # v0 在 ro+4 (u16 LE), v1 在 ro+8
        for fld_off, old, new in ((ro + 4, v0, nv0), (ro + 8, v1, nv1)):
            ob = exp[fld_off:fld_off + 2]
            nb = struct.pack('<H', new)
            for k in range(2):
                if ob[k] != nb[k]:
                    assert fld_off + k not in targets
                    targets[fld_off + k] = nb[k]
    p += nrec * 10
P('  目标记录 %d 条, 需要改的展开态字节 %d 个' % (n_v, len(targets)))
P('    face 名: %s' % [f[0] for f in faces])

# ---- 构建"目标展开态", 用于回读断言 ----
tgt = bytearray(exp)
for o, b in targets.items():
    tgt[o] = b
assert len(tgt) == len(exp)


# ═══════════ [3] 带来源追踪的 LZO1X 解码 ═══════════
def lzo_decode_traced(payload, out_size):
    """返回 (out(bytearray), src(list: 每个输出字节的来源), err)。
    src[i] = ('L', ip) 字面量来源 / ('M', i-back) 匹配来源。"""
    data = payload
    ip = 0
    n = len(data)
    out = bytearray()
    src = []

    def GETB():
        nonlocal ip
        if ip >= n:
            raise IndexError('input depleted at ip=%d' % ip)
        b = data[ip]
        ip += 1
        return b

    # ★ 逐行照抄 tools/gr_tools/lz77_decode.py::lzo1x_decompress, 只多记来源
    state = 0
    x = GETB()
    if x > 17:
        ln = x - 17
        for k in range(ln):
            out.append(data[ip + k])
            src.append(('L', ip + k))
        ip += ln
        x = GETB()
    while True:
        if out_size is not None and len(out) >= out_size:
            break
        if x > 15:
            if x > 63:
                cnt = (x >> 5) - 1
                back = (GETB() << 3) + ((x >> 2) & 7) + 1
            elif x > 31:
                cnt = x & 31
                if cnt == 0:
                    while True:
                        x = GETB()
                        if x:
                            cnt += 31 + x
                            break
                        cnt += 255
                x = GETB()
                back = (GETB() << 6) + (x >> 2) + 1
            else:
                cnt = x & 7
                if cnt == 0:
                    while True:
                        x = GETB()
                        if x:
                            cnt += 7 + x
                            break
                        cnt += 255
                back = (1 << 14) + ((x & 8) << 11)
                x = GETB()
                back += (GETB() << 6) + (x >> 2)
                if back == (1 << 14):
                    break
        elif not state:
            cnt = x & 15
            if cnt == 0:
                while True:
                    x = GETB()
                    if x:
                        cnt += 15 + x
                        break
                    cnt += 255
            ln = cnt + 3
            for k in range(ln):
                out.append(data[ip + k])
                src.append(('L', ip + k))
            ip += ln
            x = GETB()
            if x > 15:
                continue
            cnt = 1
            back = (1 << 11) + (GETB() << 2) + (x >> 2) + 1
        else:
            cnt = 0
            back = (GETB() << 2) + (x >> 2) + 1
        o = len(out)
        if back > o:
            return out, src, 'INVALID BACK %d at out=%d' % (back, o)
        for i in range(cnt + 2):
            out.append(out[o - back + i])
            src.append(('M', o - back + i))
        state = cnt = x & 3
        for k in range(cnt):
            out.append(data[ip + k])
            src.append(('L', ip + k))
        ip += cnt
        if out_size is not None and len(out) >= out_size:
            break
        if ip >= n:
            break
        x = GETB()
    return out, src, None


def resolve(i, src, depth=0):
    """输出下标 i 追到**字面量**源 (来源 ip)。"""
    seen = 0
    while True:
        k, v = src[i]
        if k == 'L':
            return v
        i = v
        seen += 1
        assert seen < 1 << 20, '来源链过长'


P('')
P('=' * 78)
P('[3] 压缩流原位替换可行性')
P('=' * 78)
# 找 LZO 载荷: 用 [1] 里找到的第一个 {comp}{real} 结构
if not found:
    P('  ✗ 没找到 LZO 载荷结构 ⇒ 不可原位替换')
    sys.exit(1)
pay_off, comp, real, dec0 = found[0]
P('  载荷 @槽+0x%X comp=%d real=%d' % (pay_off, comp, real))
assert bytes(dec0) == bytes(exp[:len(dec0)]), '解出的不是展开态前缀'
out, src, _ = lzo_decode_traced(slot[pay_off + 8:pay_off + 8 + comp], len(exp))
P('  追踪解码: %d B (期望 %d) %s' % (len(out), len(exp), '✓' if bytes(out) == bytes(exp) else '✗'))
if bytes(out) != bytes(exp):
    sys.exit(1)

patch = {}                      # payload 内偏移 -> 新字节
lit_users = {}                  # 字面量 ip -> [输出下标]
for i in range(len(src)):
    k, v = src[i]
    if k == 'L':
        lit_users.setdefault(v, []).append(i)
conflict = []
for o, nb in sorted(targets.items()):
    lip = resolve(o, src)
    if lip in patch and patch[lip] != nb:
        conflict.append((o, lip, patch[lip], nb))
        continue
    patch[lip] = nb
    # 该字面量的所有用户是否都必须变成同一个值?
    for u in lit_users.get(lip, []):
        if u in targets and targets[u] != nb:
            conflict.append(('用户冲突', o, u, nb, targets[u]))
P('  需要改的压缩字节 %d 个 ; 冲突 %d' % (len(patch), len(conflict)))
if conflict:
    P('  ✗ 冲突样例: %s' % conflict[:5])
n_lit_only = sum(1 for o in targets if src[o][0] == 'L')
P('  目标字节里"直接是字面量"的 = %d / %d ; 其余经匹配拷贝链' % (n_lit_only, len(targets)))

# 副产品: 有没有"不该变的输出字节"共用同一个字面量
bad_share = [(lip, [u for u in us if u not in targets][:3])
             for lip, us in lit_users.items()
             if lip in patch and any(u not in targets for u in us)]
P('  ⚠ 共用字面量(改了会连带影响未目标输出) 的个数 = %d %s'
  % (len(bad_share), bad_share[:3]))

P('')
P('=' * 78)
P('[3] 尾部区域 (%d..%d) 解剖' % (found[0][0] + 8 + found[0][1], len(slot)))
P('=' * 78)
t0 = found[0][0] + 8 + found[0][1]
tail = slot[t0:]
nz = sum(1 for b in tail if b)
P('  长度 %d B ; 非零字节 %d' % (len(tail), nz))
if nz:
    segs = []
    i = 0
    while i < len(tail):
        if tail[i]:
            j = i
            while j < len(tail) and tail[j]:
                j += 1
            segs.append((t0 + i, j - i))
            i = j
        else:
            i += 1
    P('  非零段 %d 个, 前 20: %s' % (len(segs), segs[:20]))
    P('  尾部前 64 B: %s' % ' '.join('%02X' % b for b in tail[:64]))

P('')
P('=' * 78)
P('[4] ★ 重压缩路径 (改 v0/v1 ⇒ 重压 LZO 子流, 槽内 2924 B 余量吸收帧长变化)')
P('=' * 78)
import tcslib as _T                                                  # noqa: E402
tgt2 = bytes(tgt)
cc = _T.lzo_compress(tgt2, level=7, use_m1=True, use_m4=True)
back, err, _ = _T.lzo1x_decompress(cc, out_size=len(tgt2))
P('  重压: %d B (原帧载荷 %d B) ; 回环 %s'
  % (len(cc), found[0][1], '✓' if (err is None and back == tgt2) else '✗ %s' % err))
newframe = struct.pack('<II', len(cc), len(tgt2)) + cc
P('  新帧 = 8 + %d = %d B ; 槽 %d B ⇒ %s'
  % (len(cc), len(newframe), len(slot),
     '✓ 装得下 (余 %d B)' % (len(slot) - 8 - len(newframe)) if 8 + len(newframe) <= len(slot)
     else '✗ 超槽'))
newslot2 = bytearray(slot)
newslot2[0:8] = newframe[0:8]
newslot2[8:8 + len(cc)] = cc
# 槽内 [8+len(cc), t0) 必须清零 (原来是旧载荷的尾部); [t0:] 原样保留
for i in range(8 + len(cc), t0):
    newslot2[i] = 0
exp3, stats3 = decode_entry(bytes(newslot2))
P('  写回后: 槽长 %d ; decode_entry → %d B ; stats=%s' % (len(newslot2), len(exp3), stats3))
ok = (len(exp3) == len(tgt2) and exp3 == tgt2)
P('  ⇒ 展开态 == 目标 (只差 332 条记录的 v0/v1): %s' % ('✓' if ok else '✗'))
if len(exp3) == len(exp):
    d2 = [i for i in range(len(exp)) if exp[i] != exp3[i]]
    P('  ⇒ 展开态差异字节 = %d (期望 %d, 全在目标集合: %s)'
      % (len(d2), len(targets), set(d2) <= set(targets)))
P('  ⇒ 槽内 [%d:] (旧尾区) 与基底逐字节一致: %s'
  % (t0, bytes(newslot2[t0:]) == bytes(slot[t0:])))
P('  ⇒ 记录数自检: %s'
  % [(f[0], f[1][4] * f[1][5]) for f in tcslib.parse_ft_faces(exp3)[1]])
iso.close()
with open(os.path.join(OUT, 'fontres.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(LS) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'fontres.txt'))
sys.exit(0)
