# -*- coding: utf-8 -*-
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..'))

r"""make_pak.py — 路线B：px blob 分段手术（盘侧拆传核心）
把 COMMON_PAK_V16.bin 的像素容器 (0x40010 = [16B GIFTAG][0x40000 图集]) 重写为
8 个自闭合 GIF 包, 每包:
  [PT: GIFTAG NLOOP=1 EOP=0 PACKED NREG=2 REGS={A+D,A+D}]   (16B)
  [A+D 对: TRXPOS value=(u64)(y_k<<32)][addr=0x52]           (32B)  ← VRAM 写入行重定位
  [IT: GIFTAG NLOOP=data/16 EOP=1 FLG=2 IMAGE]               (16B)  ← 段结束=EOP, 包交付
  [data: R 行图集]                                            (R*512B)
尾部: [GIFTAG NLOOP=0 EOP=1] (16B no-op)。
SEG0-6 各 64 行(0x8000), SEG7 63 行(0x7E00); 511 行图集保留, 原第 511 行丢弃
(布局实证: 最大使用行=370, 行 370-511 全为 0x11 透明填充, 零字形损失)。
总长恒 0x40010 (alloc 铁律不破); PAK 文件总长不变; 记录外零改动。
游戏侧零 ELF 改动: chunk=0x40000 → n=0x40000, npackets=1, REF QWC=0x4001
= 恰好搬运整个新 blob (字节搬运工), GIF 解析出 8+1 个 EOP 闭合小包。
"""
import os, struct

SRC = os.path.join(REPO_ROOT, 'work', 'builds', 'GR_ZH62', 'font_out', 'COMMON_PAK_V16X.bin')
DST = os.path.join(REPO_ROOT, 'work', 'builds', 'GR_ZH62', 'font_out', 'common_pak_seg_tmp.bin')

RECS = 0x1031          # new_font_revised 记录起点
OFF_ALLOC = RECS + 0x438
OFF_TAG = RECS + 0x43C
PX_LEN = 0x40000
BLOB_LEN = 0x40010     # tag + px

ROWS = 512
ROW = 512              # 1024px * 4bpp = 512B/行
# 段字节预算: 每段开销 48B (PT16+pair16+IT16), 8 段=384; 尾 no-op tag 16B
# data = 0x40010 - 384 - 16 = 0x3FE80 = 7*0x8000 + 0x7E80
# SEG0-6 = 原图集 [64k*512, +0x8000) 各 64 行; SEG7 = [0x38000, 0x3FE80)
#          = 63 整行 + 第511行前128B; 弃原图集尾 384B (行408-511 已证全空, 且每帧同址重传, VRAM 残留=同字节)
SEG_OFFS = [k * 0x8000 for k in range(7)] + [0x38000]
SEG_LENS = [0x8000] * 7 + [0x7E80]
SEG_Y = [64 * k for k in range(7)] + [448]
assert sum(SEG_LENS) == 0x3FE80
assert all(off // ROW == y for off, y in zip(SEG_OFFS, SEG_Y))

pak = bytearray(open(SRC, 'rb').read())
orig_len = len(pak)

# ---- 自检: 记录头 ----
psm = pak[RECS + 0x18]
alloc = struct.unpack_from('<I', pak, OFF_ALLOC)[0]
assert psm == 0x14 and alloc == 0x40010, (hex(psm), hex(alloc))
tag = bytes(pak[OFF_TAG:OFF_TAG + 16])
# 原 tag: NLOOP=0x4000 EOP=1 FLG=2 IMAGE
w0 = struct.unpack_from('<I', tag, 0)[0]
w1 = struct.unpack_from('<I', tag, 4)[0]
assert w0 == 0x0000c000 and w1 == 0x08000000, (hex(w0), hex(w1))

px = bytes(pak[OFF_TAG + 16: OFF_TAG + 16 + PX_LEN])

# ---- 尾部空白自检: 实测最后非空行=407 (EN带底部); 行 408-511 必须全为 0x11 填充 ----
# (SEG7 弃的原图集尾 384B ⊂ 空白区, 零字形损失)
tail = px[408 * ROW:]
assert tail == b'\x11' * len(tail), 'tail rows 408-511 not blank!'

# ---- GIF tag 构造工具 ----
def giftag(nloop, eop, flg, nreg_field, regs=None):
    w0 = (nloop & 0x7FFF) | (0x8000 if eop else 0)
    w1 = ((nreg_field & 0xF) << 28) | ((flg & 3) << 26)
    out = struct.pack('<II', w0, w1)
    out += regs if regs is not None else b'\x00' * 8
    return out

AD_REGS = bytes([0x0E]) + b'\x00' * 7   # REGS = {0xE}: 单 A+D qword

def seg_prefix(y_row):
    # PT: NLOOP=1, PACKED, NREG=1 (字段=1!), EOP=0 → 1 个数据 qword (16B)
    # 注意: PCSX2 nRegs=((field-1)&0xF)+1 → field=0 会变成 16 个寄存器!
    pt = giftag(1, 0, 0, 1, AD_REGS)
    # A+D qword: 低 8B = TRXPOS 值 (低u32=SSAX=0, 高u32=SSAY=y); 高 8B = 寄存器号 0x52
    q = struct.pack('<II', 0, y_row) + struct.pack('<Q', 0x52)
    return pt + q                                   # 16 + 16 = 32B

def img_tag(nloop):
    return giftag(nloop, 1, 2, 0)                  # NLOOP, EOP=1, IMAGE

# ---- 组装新 blob ----
out = bytearray()
for k in range(8):
    out += seg_prefix(SEG_Y[k])
    out += img_tag(SEG_LENS[k] // 16)
    out += px[SEG_OFFS[k]: SEG_OFFS[k] + SEG_LENS[k]]
out += giftag(0, 1, 2, 0)                          # 尾部 no-op: NLOOP=0 EOP=1
assert len(out) == BLOB_LEN, hex(len(out))

# ---- 回写 ----
pak[OFF_TAG:OFF_TAG + BLOB_LEN] = out
assert len(pak) == orig_len, (len(pak), orig_len)
open(DST, 'wb').write(bytes(pak))

# ---- 验证: 记录外零改动 ----
src = open(SRC, 'rb').read()
diff = [i for i in range(orig_len) if src[i] != pak[i]]
assert all(OFF_TAG <= i < OFF_TAG + BLOB_LEN for i in diff)
print('common_pak_seg_tmp.bin OK: size=%d (0x%x), blob-diff=%dB, seg-lens=%s'
      % (len(pak), len(pak), len(diff), SEG_LENS))

# ---- 验证: 按 GIF 语义解析新 blob, 列出包结构 (nRegs 语义与 PCSX2 一致) ----
o = 0; pkts = []
while o < BLOB_LEN:
    w0, w1 = struct.unpack_from('<II', out, o)
    nloop = w0 & 0x7FFF; eop = (w0 >> 15) & 1; flg = (w1 >> 26) & 3
    nregs = ((w1 >> 28) - 1 & 0xF) + 1
    if flg in (0, 1):
        ln = nloop * 16 * nregs
    else:
        ln = nloop * 16
    pkts.append((o, nloop, eop, flg, ln))
    o += 16 + ln
    if nloop == 0:
        break
for p in pkts:
    print('  off=0x%05x NLOOP=%-6d EOP=%d FLG=%d data=%d' % p)
eops = [p for p in pkts if p[2]]
print('  包数(有数据)=%d, EOP 段=%d, 最大包=%dB' % (len([p for p in pkts if p[1]]), len(eops), max(p[4] for p in pkts)))
