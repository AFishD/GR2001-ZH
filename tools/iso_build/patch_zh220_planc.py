# -*- coding: utf-8 -*-
r"""c_patch_planc.py — 方案 C (修正版 v2): 扩 DBCS lead 到 0xB3, **长度守恒**

## 三条硬约束 (全部由实验确定)

1. **条目表 `off`/`stored`/`real` 三字段绝对不动**
   （`tools/hanliu/tools/lzo1x_c.py` 头部记录的原设计约束）
2. **解压长度必须守恒**: patch_zh110 把 4 个汉字 1B→2B, 展开 128545 → 130046,
   结果 **卡在记忆卡画面**（drawlog 0）。本补丁改为 **1B→1B** 重映射 ⇒ 长度不变。
3. **FONT.RES 的 FT 必须同步新码位的记录**（复制原记录的 10 字节 UV）

## 实测证据链

| 盘 | 改动 | 结果 |
|---|---|---|
| GR_ZH202 | 只改容器内容(2B 搬迁 + real 同步), 不改 ELF | ❌ 卡死 (drawlog 1 行) |
| GR_ZH203 | **只重压 + 写回, 内容逐字节不动** (8 子流布局、real 均不变) | ✅ **完全正常** (drawlog 23258 行 / strlog 2929 行, 截图与基线一致) |
| GR_ZH200 | 4 处 gate → 0xB4 + 2B 搬迁 | ❌ 卡死 |

⇒ 崩溃与"重压/写回"无关, 与"内容变长"有关 ⇒ **必须长度守恒**。

## 改动

1. ELF: 4 处 `sltiu ...,0xAE` → `0xB4` (lead 0xA1..0xB3)
2. 文本容器 1B→1B 重映射 (`off/stored/real` 不变, 子流布局不变):
```
   0xAF '的'  -> 0x80      0xB0 '你'  -> 0x81      0xB1 图标字 -> 0x7F
   0xB2 '键'  -> 0x82      0xB3 '练'  -> 0x83
```
3. MENU.IMG#4 FONT.RES 内 FT: 面记录 idx(src-0x20) → idx(dst-0x20)
   （`huge` face 只有 96 条记录, idx≥96 无记录 ⇒ 该 face 不复制, 走网格公式）

## 目标码位为何安全 (证据)

`tools/font_pipeline/data/charset_compiled_zh16.json`: 译文字表单字节码只用
`0xAF..0xFE`（76 个）；**`0x7F..0x91` 完全未被字表使用**。
EN_STRINGS.RES 内 `0x7F..0x8B` 出现 0 次（仅 0x8C/0x8E/0x91 各若干, 故避开它们）；
EN_SPECIAL_FEATURE.XML 内 `0x7F..0x91` 出现 0 次；.ATR/.MIS(任务文本) 内 0x7F..0x91 出现 0 次。

## 用法
  python c_patch_planc.py <src_iso> <dst_iso>
"""
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
from lz77_decode import lzo1x_decompress          # noqa: E402
from lzo1x_c import compress as lzo_compress      # noqa: E402

ELF_LBA, SEC_OFF, SEC_ADDR = 295, 0x80, 0x00100000
MENU_LBA, GR_LBA = 776286, 19175
TAB_OFF, TAB_STEP = 0x830, 48
E_STORED, E_REAL, E_OFF = 6, 7, 8
OFF_FT, FT_SLOT = 0xB9120, 4421          # = MENU.IMG 条目 #4 (FONT.RES) 的槽
FT_ENTRY_IDX = 4

GATES = [
    (0x416EE8, 0x2CA900AE, 0x2CA900B4, 'DrawString 取码 cave'),
    (0x417160, 0x2D0900AE, 0x2D0900B4, 'StringWidth 头 cave'),
    (0x41751C, 0x2D4B00AE, 0x2D4B00B4, 'DoWordWrap 逐字 cave'),
    (0x5656A4, 0x2D6C00AE, 0x2D6C00B4, 'StringWidth 尾 DBCS 计数'),
]

# 只改**有运行期证据**被绘制的容器 (见 work/_dis/c_mustmigrate.py)
TEXT_RES = [
    (MENU_LBA, 25,  'EN_STRINGS.RES'),
    (MENU_LBA, 283, 'EN_SPECIAL_FEATURE.XML'),
    (GR_LBA,   902, 'EN_STRINGS.RES'),
]

# 1 字节 -> 1 字节 (长度守恒)
SINGLE_MOVES = {
    0xAF: 0x80,     # 的
    0xB0: 0x81,     # 你
    0xB1: 0x7F,     # 未登记图标字
    0xB2: 0x82,     # 键
    0xB3: 0x83,     # 练
}
PARSE_HI = 0xAD


def elf_off(va):
    return ELF_LBA * 2048 + SEC_OFF + (va - SEC_ADDR)


def lz_records(blob):
    parts, q = [], 0
    while q + 8 <= len(blob):
        L, S = struct.unpack_from('<II', blob, q)
        if L == 0 or q + 8 + L > len(blob) or S > 16_000_000:
            break
        dd, err, _ = lzo1x_decompress(blob[q + 8:q + 8 + L], out_size=S)
        if err:
            break
        parts.append((L, S, bytes(dd)))
        q += 8 + L
    return parts


# ---------------------------------------------------------------- RES 结构
# tools/hanliu/tools/res_encode.py 记录的展开态格式:
#   u32 num_groups
#   组1:      u32 count1               count1 × 条目
#   组2..N:   u32 sep  sep×{u32 len}{bytes}  u32 count  count × 条目
#   末尾: u32 0, u32 0
#   条目 = {u32 len}{bytes(len)}{u16 attr}
# ★ 只有"条目字节"与"附加项字节"是文本; len/count/sep/attr 是二进制结构, **不得重编码**
#   (patch_zh110 与我的 v1 直接把整块当文本扫, 把长度字段 0xAF 改成 0x80 ⇒ 解析器错位 ⇒ 卡死)
def res_ranges(data):
    n = len(data)

    def u32(p):
        if p + 4 > n:
            raise ValueError('越界 @0x%X' % p)
        return struct.unpack_from('<I', data, p)[0]

    p = 0
    ng = u32(p)
    p += 4
    assert 1 <= ng <= 4096, 'num_groups=%d 异常' % ng
    ranges = []
    for gi in range(ng):
        if gi == 0:
            cnt = u32(p)
            p += 4
        else:
            sep = u32(p)
            p += 4
            for _ in range(sep):
                ln = u32(p)
                p += 4
                assert p + ln <= n
                if ln:
                    ranges.append((p, p + ln))
                p += ln
            cnt = u32(p)
            p += 4
        assert cnt <= 0x10000, '组 %d count=%d 异常' % (gi + 1, cnt)
        for _ in range(cnt):
            ln = u32(p)
            p += 4
            assert p + ln + 2 <= n, '条目越界 @0x%X (len=%d)' % (p, ln)
            if ln:
                ranges.append((p, p + ln))
            p += ln + 2
    assert p + 8 <= n, '尾字节不足: p=0x%X n=0x%X' % (p, n)
    assert data[p:p + 8] == b'\x00' * 8, '缺 {0}{0} 终止符 @0x%X' % p
    rest = data[p + 8:]
    assert rest.count(0) == len(rest), '终止符后存在 %d B 非零数据' % (
        len(rest) - rest.count(0))
    return ranges, ng


def remap_range(buf, a, b, st):
    """在 buf[a:b] 内按位置规则 1B->1B 重映射 (长度守恒)"""
    out = bytearray()
    i = a
    while i < b:
        c = buf[i]
        if 0xA1 <= c <= PARSE_HI and i + 1 < b and 0xA1 <= buf[i + 1] <= 0xFE:
            out += buf[i:i + 2]
            st['pairs'] += 1
            i += 2
            continue
        if c in SINGLE_MOVES:
            out.append(SINGLE_MOVES[c])
            st['moved'][c] = st['moved'].get(c, 0) + 1
        else:
            if 0xAE <= c <= 0xB3:
                st['bare_high'][c] = st['bare_high'].get(c, 0) + 1
            out.append(c)
        i += 1
    assert len(out) == b - a
    return out


def bare_scan(t, ranges):
    """用新 gate 语义 (0xA1..0xB3 为 lead) 扫裸码; 返回 (范围外, 范围内) 两本账。
    范围外的裸码都在结构字段 (u32 len/count) 里, 引擎按 u32 读, 不作文本 ⇒ 无影响。"""
    inr = [False] * len(t)
    for a, b in ranges:
        for k in range(a, b):
            inr[k] = True
    outside, inside = {}, {}
    i = 0
    while i < len(t):
        b0 = t[i]
        if 0xA1 <= b0 <= 0xB3 and i + 1 < len(t) and 0xA1 <= t[i + 1] <= 0xFE:
            i += 2
            continue
        if 0xAE <= b0 <= 0xB3:
            d = inside if inr[i] else outside
            d[b0] = d.get(b0, 0) + 1
        i += 1
    return outside, inside


def migrate_flat(t):
    st = {'moved': {}, 'bare_high': {}, 'pairs': 0}
    return bytes(remap_range(bytearray(t), 0, len(t), st)), st


def migrate_res(t):
    """结构感知: 只重映射 条目字节 / 附加项字节"""
    ranges, ng = res_ranges(t)
    buf = bytearray(t)
    st = {'moved': {}, 'bare_high': {}, 'pairs': 0, 'ng': ng, 'ranges': len(ranges)}
    for a, b in ranges:
        buf[a:b] = remap_range(bytearray(t), a, b, st)
    assert len(buf) == len(t)
    return bytes(buf), st


def migrate(t):
    out = bytearray()
    i = 0
    st = {'moved': {}, 'bare_high': {}, 'pairs': 0}
    while i < len(t):
        b0 = t[i]
        if 0xA1 <= b0 <= PARSE_HI and i + 1 < len(t) and 0xA1 <= t[i + 1] <= 0xFE:
            out += t[i:i + 2]                      # 现役对偶码, 原样
            st['pairs'] += 1
            i += 2
            continue
        if b0 in SINGLE_MOVES:
            out.append(SINGLE_MOVES[b0])
            st['moved'][b0] = st['moved'].get(b0, 0) + 1
        else:
            if 0xAE <= b0 <= 0xB3:
                st['bare_high'][b0] = st['bare_high'].get(b0, 0) + 1
            out.append(b0)
        i += 1
    assert len(out) == len(t), '长度不守恒 %d -> %d' % (len(t), len(out))
    return bytes(out), st


# ---------------------------------------------------------------- FT
def ft_faces(ft):
    p = 0
    l0 = struct.unpack_from('<I', ft, p)[0]
    p += 4 + l0
    n = struct.unpack_from('<I', ft, p)[0]
    p += 4
    faces = []
    for _ in range(n):
        l = struct.unpack_from('<I', ft, p)[0]
        p += 4
        nm = ft[p:p + l].decode('latin-1')
        p += l
        fld = list(struct.unpack_from('<14I', ft, p))
        p += 56
        nr = fld[4] * fld[5]
        faces.append(dict(name=nm, nrec=nr, off=p))
        p += nr * 10
    return faces


def main(src, dst):
    do_elf = os.environ.get('PLANC_ELF', '1') == '1'
    do_text = os.environ.get('PLANC_TEXT', '1') == '1'
    do_ft = os.environ.get('PLANC_FT', '1') == '1'
    sd = open(src, 'rb').read()
    for va, old, new, desc in GATES:
        cur = struct.unpack_from('<I', sd, elf_off(va))[0]
        assert cur == old, '0x%06X 原值 %08X != %08X' % (va, cur, old)
    print('[elf] 4 处 lead 判定均为 0xAE ✓  ELF=%s TEXT=%s FT=%s' % (do_elf, do_text, do_ft))
    print()

    # ---------------- 文本容器 ----------------
    plan = []
    for lba, idx, nm in (TEXT_RES if do_text else []):
        base = lba * 2048
        e = struct.unpack_from('<12I', sd, base + TAB_OFF + TAB_STEP * idx)
        stored, real, off = e[E_STORED], e[E_REAL], e[E_OFF]
        blob = sd[base + off:base + off + stored]
        recs = lz_records(blob)
        assert recs, '%s 解压失败' % nm
        t = b''.join(r[2] for r in recs)
        if nm.upper().endswith('.XML') or nm.upper().endswith('.TXT'):
            out, st = migrate_flat(t)          # 纯文本, 无二进制结构
            st['ng'] = st['ranges'] = 0
        else:
            out, st = migrate_res(t)           # RES: 只改条目/附加项字节
        assert not st['bare_high'], '%s 仍有裸码 %s' % (
            nm, {hex(k): v for k, v in st['bare_high'].items()})
        # 原样保留子流布局, 只换内容
        blk = bytearray()
        pos = 0
        for (L, S, d) in recs:
            chunk = out[pos:pos + S]
            pos += S
            c = lzo_compress(chunk)
            blk += struct.pack('<II', len(c), S) + c
        assert pos == len(out)
        assert len(blk) <= stored - 8, '%s 重压 %d 超槽 %d' % (nm, len(blk), stored - 8)
        plan.append(dict(lba=lba, idx=idx, name=nm, base=base, stored=stored,
                         real=real, off=off, blob=bytes(blk), st=st,
                         nrec=len(recs), exp=len(out)))
        print('[res] %-6s#%-5d %-24s 展开 %-8d (守恒 ✓) 子流 %d  重压 %-6d 槽 %-6d 余 %-6d'
              % ('MENU' if lba == MENU_LBA else 'GR', idx, nm, len(out), len(recs),
                 len(blk), stored, stored - 8 - len(blk)))
        print('        搬迁: %s ; 对偶对 %d ; 结构: %s'
              % ({hex(k): [v, hex(SINGLE_MOVES[k])] for k, v in sorted(st['moved'].items())},
                 st['pairs'],
                 ('%d 组 / %d 字段范围' % (st['ng'], st['ranges'])) if st['ng'] else '纯文本'))

    # ---------------- FT (MENU.IMG#4 FONT.RES) ----------------
    base = MENU_LBA * 2048
    e = struct.unpack_from('<12I', sd, base + TAB_OFF + TAB_STEP * FT_ENTRY_IDX)
    fstored, freal, foff = e[E_STORED], e[E_REAL], e[E_OFF]
    assert foff == OFF_FT and fstored == FT_SLOT, 'FONT.RES 位置异常 0x%X/%d' % (foff, fstored)
    fblob = sd[base + foff:base + foff + fstored]
    frecs = lz_records(fblob)
    ft = bytearray(frecs[0][2])
    faces = ft_faces(bytes(ft))
    print()
    print('[ft ] FT %d B, faces: %s' % (len(ft), [(f['name'], f['nrec']) for f in faces]))
    ft_changes = 0
    for f in (faces if do_ft else []):
        for src_c, dst_c in sorted(SINGLE_MOVES.items()):
            si, di = src_c - 0x20, dst_c - 0x20
            if si < f['nrec'] and di < f['nrec']:
                so = f['off'] + si * 10
                do = f['off'] + di * 10
                old = bytes(ft[do:do + 10])
                new = bytes(ft[so:so + 10])
                if old != new:
                    ft[do:do + 10] = new
                    ft_changes += 1
                    print('      %-8s idx %d(0x%02X) ← idx %d(0x%02X)  %s → %s'
                          % (f['name'], di, dst_c, si, src_c, old.hex(), new.hex()))
    print('      FT 记录改写 %d 处 (未改写的说明本就相同)' % ft_changes)
    assert len(ft) == len(frecs[0][2]), 'FT 长度变化'
    cf = lzo_compress(bytes(ft))
    consumed = sum(8 + r[0] for r in frecs)      # 真实占用 (不含槽尾补零)
    tail = fblob[8 + frecs[0][0]:consumed]
    new_fblob = struct.pack('<II', len(cf), len(ft)) + cf + tail
    assert len(new_fblob) <= fstored - 8, 'FONT.RES 重压 %d 超槽 %d' % (len(new_fblob), fstored)
    print('      FONT.RES 重压 %d B (槽 %d, 余 %d); 其余 %d 个子流原样保留'
          % (len(new_fblob), fstored, fstored - len(new_fblob), len(frecs) - 1))

    # ---------------- 写盘 ----------------
    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        if do_elf:
            for va, old, new, desc in GATES:
                f.seek(elf_off(va))
                f.write(struct.pack('<I', new))
        print()
        print('[elf] %s' % ('写入 4 处 → 0xB4' if do_elf else '未改动'))
        for p in plan:
            f.seek(p['base'] + p['off'])
            f.write(p['blob'])
            f.write(b'\x00' * (p['stored'] - len(p['blob'])))
        if do_ft:
            f.seek(base + foff)
            f.write(new_fblob)
            f.write(b'\x00' * (fstored - len(new_fblob)))
        print('[res] %d 个文本容器%s已写回 (off/stored/real 全未改动)'
              % (len(plan), ' + FONT.RES ' if do_ft else ' '))

    # ---------------- 校验 ----------------
    print()
    print('=== 回读校验 (新 gate 语义: 0xA1..0xB3 为 lead) ===')
    vd = open(dst, 'rb').read()
    ok = True
    for p in plan:
        e = struct.unpack_from('<12I', vd, p['base'] + TAB_OFF + TAB_STEP * p['idx'])
        recs = lz_records(vd[p['base'] + p['off']:p['base'] + p['off'] + e[E_STORED]])
        t = b''.join(r[2] for r in recs)
        if p['st']['ranges']:
            rg, _ng = res_ranges(t)
        else:
            rg = [(0, len(t))]
        outside, inside = bare_scan(t, rg)
        good = (e[E_REAL] == p['real'] and e[E_STORED] == p['stored']
                and e[E_OFF] == p['off'] and len(t) == p['exp'] and not inside)
        ok = ok and good
        print('  %-6s#%-5d %-24s real=%-8d tested=%-8d 展开=%-8d 文本区裸码=%-5s'
              ' 结构区裸码=%-14s %s'
              % ('MENU' if p['lba'] == MENU_LBA else 'GR', p['idx'], p['name'][:24],
                 e[E_REAL], p['real'], len(t), inside or '{}',
                 {hex(k): v for k, v in outside.items()} or '{}',
                 '✓' if good else '✗'))
    ef = struct.unpack_from('<12I', vd, base + TAB_OFF + TAB_STEP * FT_ENTRY_IDX)
    ft2 = lz_records(vd[base + ef[E_OFF]:base + ef[E_OFF] + ef[E_STORED]])[0][2]
    fok = (ef[E_STORED] == fstored and ef[E_REAL] == freal and ef[E_OFF] == foff
           and len(ft2) == len(frecs[0][2]))
    ok = ok and fok
    print('  MENU #4    FONT.RES(FT)              stored=%d real=%d FT=%d B %s'
          % (ef[E_STORED], ef[E_REAL], len(ft2), '✓' if fok else '✗'))
    assert ok, '回读校验失败'
    print('  全部 ✓')
    print()
    print('  ⇒ lead 0xA1..0xB3: 13×94=1222 → 19×94=1786 码位 (+564)')
    print('  ⇒ 文本长度守恒 ⇒ 条目表 off/stored/real 三字段与基线逐字节相同')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1], sys.argv[2])
