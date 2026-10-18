# -*- coding: utf-8 -*-
r"""zx_r83_struct.py — round83 任务①：FONT.RES 权威结构 + 像素容器 10 区域清单（只读）

产出 work/builds/GR_ZH98/temp/r83/struct.txt
"""
import json
import os
import struct
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib      # noqa: E402
import zx_lib      # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r83')
os.makedirs(OUT, exist_ok=True)
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
MENU_LBA = tcslib.MENU_LBA
SEC = 2048
B = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    B.append(s)


iso = tcslib.Iso(ISO)
base = MENU_LBA * SEC
names = []
for i in range(2000):
    e = iso.img_entry(MENU_LBA, i)
    if e['name'].startswith('?'):
        break
    names.append(e['name'])
P('MENU.IMG 条目数 = %d' % len(names))

# ══════════════ [A] COMMON.PAK 记录链 ══════════════
P('')
P('=' * 78)
P('[A] COMMON.PAK 记录链（parse_pak_records 口径）')
P('=' * 78)
pak_i = names.index('COMMON.PAK')
pak_e = iso.img_entry(MENU_LBA, pak_i)
pak = bytes(iso.read(pak_e['iso_off'], pak_e['stored']))
P('COMMON.PAK #%d off=0x%X stored=%d real=%d' % (pak_i, pak_e['off'], pak_e['stored'], pak_e['real']))
recs = tcslib.parse_pak_records(pak)
# 重新精确算每条记录的起点
p = 0
info = []
while p + 8 <= len(pak):
    ty, nl = struct.unpack_from('<II', pak, p)
    if ty == 0x63 or nl > 64:
        P('  ★ 结束哨兵 @0x%X  type=0x%X nameLen=%d' % (p, ty, nl))
        break
    nm = pak[p + 8:p + 8 + nl].decode('latin-1')
    q = p + 8 + nl
    psm, w, h, clut = struct.unpack_from('<4I', pak, q)
    px = struct.unpack_from('<I', pak, q + 16 + clut)[0]
    pnoff = q + 20 + clut
    info.append(dict(idx=len(info), rec_off=p, namelen=nl, name=nm, psm=psm, w=w, h=h,
                     clut=clut, clut_off=q + 16, px_size=px, px_off=pnoff,
                     end=pnoff + px, hdr_raw=list(struct.unpack_from('<8I', pak, p))))
    p = pnoff + px
for r in info:
    P('  rec#%d @0x%-7X %-24s nameLen=%-3d psm=0x%02X %4dx%-4d clut_size=%-5d clut@0x%-7X '
      'px_size=%-8d (0x%X) px@0x%-7X end=0x%X'
      % (r['idx'], r['rec_off'], r['name'], r['namelen'], r['psm'], r['w'], r['h'],
         r['clut'], r['clut_off'], r['px_size'], r['px_size'], r['px_off'], r['end']))
P('  记录链结束 @0x%X ; PAK 长度 %d ; 尾料 %d B' % (p, len(pak), len(pak) - p))
P('  ★ 记录头 8 u32 (rec#1 new_font_revised @0x%X):' % info[1]['rec_off'])
for k in range(8):
    v = info[1]['hdr_raw'][k]
    P('      +0x%03X u32[%d] = %-12d 0x%08X' % (4 * k, k, v, v))
P('  ★ clut_size=%-d ⇒ 调色板 %d 色 (PSM 0x%X = PSMT4)' % (info[1]['clut'], info[1]['clut'] // 4,
                                                          info[1]['psm']))
P('  ★ clut 前 16 色: %s' % ' '.join('%02X%02X%02X%02X' % tuple(pak[info[1]['clut_off'] + 4 * k:
                                                                     info[1]['clut_off'] + 4 * k + 4])
                                     for k in range(16)))

# ══════════════ [B] 像素容器 10 区域清单 ══════════════
P('')
P('=' * 78)
P('[B] new_font_revised 像素容器 = 区域清单')
P('=' * 78)
R = info[1]
cont = pak[R['px_off']:R['px_off'] + R['px_size']]
P('容器 px_size=0x%X=%d ; 头部 48B = %s' % (R['px_size'], R['px_size'],
                                            ' '.join('%02X' % b for b in cont[:48])))
segs = tcslib.atlas_container_segments(cont, R['w'] // 2)
P('GIF 封包分段 %d 个 (atlas_container_segments):' % len(segs))
tot = 0
for k, (fr, doff, nb) in enumerate(segs):
    tot += nb
    pre = cont[doff - 48:doff]
    P('  seg%d 首行=%-4d 前导 48B@0x%-6X 数据@0x%-7X 字节=%-7d (%.3f 行) 段末@0x%X'
      % (k, fr, doff - 48, doff, nb, nb / (R['w'] // 2), doff + nb))
    P('        前导 hex = %s' % ' '.join('%02X' % b for b in pre))
P('  数据合计 = %d ; %d*48 + %d + 16 = %d (px_size %d)'
  % (tot, len(segs), tot, len(segs) * 48 + tot + 16, R['px_size']))
P('  容器尾部 16B = %s' % ' '.join('%02X' % b for b in cont[-16:]))

# 十区域: 把容器按"每段 [48B 前缀][0x8000 数据]"再补尾部 16B 切开
P('')
P('  ★ 10 区域视图（等价切法：9 段 + 末段 + 尾 16B）:')
done = 0
for k, (fr, doff, nb) in enumerate(segs):
    P('  区域%-2d  [0x%06X, 0x%06X)  %6d B  = GIF 前缀 48B + 段数据 %d B (首行 %d)'
      % (k, doff - 48, doff + nb, 48 + nb, nb, fr))
    done = doff + nb
P('  区域%-2d  [0x%06X, 0x%06X)  %6d B  = 容器尾 16B' % (len(segs), done, len(cont), len(cont) - done))
P('  ★ 容器前 0x%X 字节 = 记录链尾 … 容器起点' % R['px_off'])

# ══════════════ [C] FONT.RES 权威结构 ══════════════
P('')
P('=' * 78)
P('[C] FONT.RES 权威结构')
P('=' * 78)
ft_i = names.index('FONT.RES')
ft_e = iso.img_entry(MENU_LBA, ft_i)
slot = bytes(iso.read(ft_e['iso_off'], ft_e['stored']))
P('FONT.RES #%d off=0x%X stored=%d real=%d' % (ft_i, ft_e['off'], ft_e['stored'], ft_e['real']))
P('  槽头 12B: %s' % ' '.join('%02X' % b for b in slot[:12]))
P('  槽 0..96 :')
for off in range(0, 96, 16):
    P('    +0x%04X  %s' % (off, ' '.join('%02X' % b for b in slot[off:off + 16])))
subs = tcslib.lzo_subs(slot)
P('  LZO 子流 %d 个: %s' % (len(subs), [(s[1], s[2]) for s in subs]))
exp = b''.join(s[0] for s in subs)
sub_end = sum(s[1] for s in subs)
P('  展开态 %d B ; 子流末端 in-slot = 0x%X ; 槽 %d B ⇒ 尾部零区 %d B'
  % (len(exp), sub_end, len(slot), len(slot) - sub_end))
tz = slot[sub_end:]
nzruns = []
i = 0
while i < len(tz):
    if tz[i]:
        j = i
        while j < len(tz) and tz[j]:
            j += 1
        nzruns.append((sub_end + i, j - i))
        i = j
    else:
        i += 1
P('  尾部非零段 %d 个: %s' % (len(nzruns), nzruns))

P('')
P('  --- 展开态前 96 B ---')
for off in range(0, 96, 16):
    P('    +0x%04X  %s' % (off, ' '.join('%02X' % b for b in exp[off:off + 16])))
P('  展开态头 7 u32 = %s' % list(struct.unpack_from('<7I', exp, 0)))
P('  u32@24 = nfaces = %d' % struct.unpack_from('<I', exp, 24)[0])

P('')
P('  --- 逐 face ---')
p = 28
face_meta = []
for fi in range(struct.unpack_from('<I', exp, 24)[0]):
    nl = struct.unpack_from('<I', exp, p)[0]
    nm = exp[p + 4:p + 4 + nl].decode('latin-1')
    fldoff = p + 4 + nl
    fld = list(struct.unpack_from('<14I', exp, fldoff))
    recoff = fldoff + 56
    nrec = fld[4] * fld[5]
    P('  face %d %-8r @fld 0x%04X  记录 @0x%04X .. 0x%04X  nrec = fld[4]*fld[5] = %d*%d = %d'
      % (fi, nm, fldoff, recoff, recoff + 10 * nrec, fld[4], fld[5], nrec))
    for k, v in enumerate(fld):
        P('       fld[%2d] @0x%04X = %-12d 0x%08X %s'
          % (k, fldoff + 4 * k, v, v, ('%.6g' % struct.unpack('<f', struct.pack('<I', v))[0])
             if v else ''))
    face_meta.append((nm, fld, recoff, nrec))
    p = recoff + 10 * nrec
P('  记录区结束 = 0x%X' % p)
P('  其后剩余 %d B (0x%X..0x%X)' % (len(exp) - p, p, len(exp)))
P('  尾部原始字节:')
for off in range(p, len(exp), 16):
    P('    +0x%04X  %s' % (off, ' '.join('%02X' % b for b in exp[off:off + 16])))

P('')
P('  --- 尾部结构再解析（{u32 n}{u32 m}{name}… 序列）---')
q = p
while q + 8 <= len(exp):
    n, m = struct.unpack_from('<II', exp, q)
    nm = exp[q + 8:q + 8 + max(n, m)].decode('latin-1', 'replace')
    P('    @0x%04X  n=%-4d m=%-4d 后随字符串 %r' % (q, n, m, nm))
    q += 8
    break
# 逐字节按块 40 步进
P('    (完整 40 B 步进视图)')
for off in range(p, len(exp), 40):
    chunk = exp[off:off + 40]
    P('    @0x%04X  %s' % (off, ' '.join('%02X' % b for b in chunk)))

P('')
P('  --- 记录字段统计（逐 face）---')
for (nm, fld, recoff, nrec) in face_meta:
    rs = [struct.unpack_from('<BB4H', exp, recoff + 10 * r) for r in range(nrec)]
    nonempty = [r for r in rs if r[4] > r[2]]
    P('  face %-8s nrec=%d 非空(u1>u0)=%d' % (nm, nrec, len(nonempty)))
    hist = {}
    for r in rs:
        hist[(r[0], r[1])] = hist.get((r[0], r[1]), 0) + 1
    P('       (b0,b1) 直方图 = %s' % sorted(hist.items()))
    P('       u0 范围 %d..%d ; v0 范围 %d..%d ; u1 范围 %d..%d ; v1 范围 %d..%d'
      % (min(r[2] for r in rs), max(r[2] for r in rs), min(r[3] for r in rs),
         max(r[3] for r in rs), min(r[4] for r in rs), max(r[4] for r in rs),
         min(r[5] for r in rs), max(r[5] for r in rs)))
    # 宽度分布
    wh = {}
    for r in rs:
        wh[(r[4] - r[2], r[5] - r[3])] = wh.get((r[4] - r[2], r[5] - r[3]), 0) + 1
    P('       (w,h) 直方图 = %s' % sorted(wh.items()))
    P('       每条记录 (idx, b0, b1, u0,v0,u1,v1):')
    for r_i, r in enumerate(rs):
        P('         idx %3d  b0=%3d b1=%3d  rect=(%4d,%4d)-(%4d,%4d) w=%3d h=%3d %s'
          % (r_i, r[0], r[1], r[2], r[3], r[4], r[5], r[4] - r[2], r[5] - r[3],
             '' if r[4] > r[2] else '  ← 空'))

# ══════════════ [D] 码 → 记录 映射（单字节口径） ══════════════
P('')
P('=' * 78)
P('[D] 码 → 记录映射（单字节 idx = code-0x20，face default）')
P('=' * 78)
nm, fld, recoff, nrec = face_meta[1]
for code in range(0x20, 0x100):
    idx = code - 0x20
    r = struct.unpack_from('<BB4H', exp, recoff + 10 * idx)
    ch = chr(code) if 0x20 <= code < 0x7F else '.'
    P('  code 0x%02X %-2s → idx %3d  b0=%-3d b1=%-3d rect=(%4d,%4d)-(%4d,%4d) %s'
      % (code, ch, idx, r[0], r[1], r[2], r[3], r[4], r[5],
         '' if r[4] > r[2] else '空'))

# ══════════════ [E] charset JSON ══════════════
P('')
P('=' * 78)
P('[E] charset JSON（当前仓库状态）')
P('=' * 78)
cs = json.load(open(tcslib.CHARSET, encoding='utf-8'))
P('顶层键: %s' % list(cs.keys()))
for k, v in cs.items():
    if isinstance(v, (int, str)):
        P('  %s = %r' % (k, v))
    elif isinstance(v, list):
        P('  %s: list len=%d 前 8 = %r' % (k, len(v), v[:8]))
    elif isinstance(v, dict):
        P('  %s: dict len=%d 前 8 项 = %r' % (k, len(v), list(v.items())[:8]))

iso.close()
with open(os.path.join(OUT, 'struct.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'struct.txt'))
