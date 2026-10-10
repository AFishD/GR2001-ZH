# -*- coding: utf-8 -*-
r"""patch_zh69.py — EN 带采样窗回正: (450,466) → (452,468) 【补录脚本, 2026-10-04】

## 为什么会有这个文件
2026-10-04 的「历史断言正确性审查」(`work/_dis/ASSERT_AUDIT.md` A10/§6-6) 发现:
**`patch_zh69.py` 与 `patch_zh75.py` 在整个仓库不存在**, 而 ZH69 恰恰是把字库 EN 带
采样窗从 ZH66 的 (450,466) **回正为 (452,468)** 的那一步。

后果: **现役盘 (GR_ZH82..86) 的 EN 带几何没有对应脚本可复现** —— 这直接解释了
为什么 `gen_font16.py` 从未回头更新 (它产出的 EN 带在 380/395, 与现役差 1723 B)。

本脚本为**补录**: 依据 `patch_zh68_all.py` L44 的
    `BAND_V, REC_V0, ADV = 452, 452, 0x0800   # ZH69: 窗=带 (452,468) 撤销 ZH66 窗偏移`
与现役盘实测 (ASCII 记录 v0=452, v1=468), 以**声明式 + 幂等**方式重建这一步。

## 语义 (只做一件事)
把 `FONT.RES` 里 **ASCII 码位** (0x21..0x7E, 去掉 0x7B/0x7D) 的**采样窗**
从 (450,466) 回正到 (452,468)。

- **仅改记录里的 v0/v1 字段** (记录 = 10 字节, 布局见下), 不动像素、不动其它字段。
- **幂等**: 若已是 452/468 则跳过 (可对现役盘安全重放)。
- **该步不含像素重铺** (那是 ZH66 做的); 本步只回正采样窗几何。

## 记录布局 (FT 展开态内, 实测确认)
```
FT wire 头 28 B, 后依次 3 个 face:
  face := {u32 nameLen}{name}{14 x i32 flds}{nrec 条记录, 每条 10 B}
  nrec = flds[4] * flds[5]         # 现役 large/default=224, huge=96
  记录 := {u16 x0}{u16 u0}{u16 v0}{u16 u1}{u16 v1}   ← **5 个 u16**
      实测 rec[1] = (2048, 0, 452, 8, 468) → x0=2048, u0=0, v0=452, u1=8, v1=468
```
**注意**: 早先版本把记录当成 `{x0,y0,x1,y1,adv}` 读, 会在 `o+2` 读到 `u0` 而非 `v0` —— 已修正为**按 `o+4`(v0) / `o+8`(v1)** 定位。

## 用法
  python patch_zh69.py <src_iso> <dst_iso>
  # 基底应为 ZH68 产物 (EN 带窗 = 450/466)。若已是 452/468 则本脚本为 no-op(幂等)。
"""
import hashlib
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ELF_LBA, MENU_LBA, GR_LBA = 295, 776286, 19175
FT_OFF, FT_LEN = 0xB9120, 4421

# 目标: EN 带采样窗回正 (ZH69)
BAND_V_OLD, REC_V0_OLD = 450, 450        # ZH66 的窗偏移状态
BAND_V, REC_V0 = 452, 452                # ZH69 目标 (现役实测值)
REC_V1_OLD, REC_V1 = 466, 468            # 窗高 16 → 带底
ASCII_RANGE = [c for c in range(0x21, 0x7F) if c not in (0x7B, 0x7D)]


def decode_entry(frame, out_size):
    """FT 槽 = {u32 plen}{u32 osz}{payload}; payload 是 DP 压缩流"""
    import io
    sys.path.insert(0, os.path.join(HERE, '..', 'hanliu', 'tools'))
    from lz77_decode import lzo1x_decompress  # noqa: E402
    plen, osz = struct.unpack_from('<II', frame, 0)
    data, err, _ = lzo1x_decompress(frame[8:8 + plen], out_size=osz)
    assert err is None, 'FT 解压失败'
    return bytes(data)


def parse_faces(ft):
    """返回 [{'name','flds','nrec','rec_off'}], 依据 patch_zh68_all.py::parse_ft"""
    p, faces = 28, []
    for _ in range(3):
        l = struct.unpack_from('<I', ft, p)[0]
        name = ft[p + 4:p + 4 + l].rstrip(b'\x0a').decode('latin-1')
        flds = struct.unpack_from('<14i', ft, p + 4 + l)
        nrec = flds[4] * flds[5]
        q = p + 4 + l + 56
        faces.append({'name': name, 'flds': flds, 'nrec': nrec, 'rec_off': q})
        p = q + nrec * 10
    return faces


def main(src, dst):
    sd = open(src, 'rb').read()
    base = MENU_LBA * 2048
    slot = sd[base + FT_OFF:base + FT_OFF + FT_LEN]
    ft = bytearray(decode_entry(slot, 5942))
    print('[in ] FT 展开 %d B' % len(ft))

    faces = parse_faces(ft)
    for f in faces:
        print('      face %-8s nrec=%-4d rec@0x%X' % (f['name'], f['nrec'], f['rec_off']))

    # ── 统计当前 ASCII 记录的窗值 (记录 = 5 x u16: x0,u0,v0,u1,v1) ──
    from collections import Counter

    def win_of(o):
        # 记录 = 5 x u16 {x0, u0, v0, u1, v1}; v0 @+4, v1 @+8
        return (struct.unpack_from('<H', ft, o + 4)[0],
                struct.unpack_from('<H', ft, o + 8)[0])

    cur = Counter()
    for f in faces:
        for i in range(f['nrec']):
            cur[win_of(f['rec_off'] + i * 10)] += 1
    print('[cur] 记录窗 (v0,v1) 分布 (前 6): %s' % cur.most_common(6))

    # ── 幂等: 若已无 (450,466) 可改 → 本步已生效, 直接跳过 ──
    n_todo = sum(1 for f in faces for i in range(f['nrec'])
                 if win_of(f['rec_off'] + i * 10) == (REC_V0_OLD, REC_V1_OLD))
    n_done = sum(1 for f in faces for i in range(f['nrec'])
                 if win_of(f['rec_off'] + i * 10) == (BAND_V, REC_V1))
    print('[state] (450,466) 记录 %d 条 / (452,468) 记录 %d 条' % (n_todo, n_done))
    if n_todo == 0:
        print('[skip] 已无 (450,466) 记录 → 本步已生效 (幂等, 不改动)')
        shutil.copyfile(src, dst)
        return

    # ── 回正: 扫描 (450,466) 的记录 ──
    n_fix = 0
    for f in faces:
        for i in range(f['nrec']):
            o = f['rec_off'] + i * 10
            if win_of(o) == (REC_V0_OLD, REC_V1_OLD):
                struct.pack_into('<HH', ft, o + 4, BAND_V, REC_V1)
                n_fix += 1
    print('[fix ] 回正 %d 条记录窗 (%d,%d) → (%d,%d)'
          % (n_fix, REC_V0_OLD, REC_V1_OLD, BAND_V, REC_V1))
    assert n_fix > 0, '未找到 (%d,%d) 的记录 — 基底可能不是 ZH68 产物' % (REC_V0_OLD, REC_V1_OLD)

    # ── 重压回槽 (保持 stored 不变) ──
    sys.path.insert(0, os.path.join(HERE, '..', 'hanliu', 'tools'))
    from lzo1x_c import compress as lzo_compress  # noqa: E402
    plen_old = struct.unpack_from('<I', slot, 0)[0]
    c = lzo_compress(bytes(ft), level=7, use_m1=True, use_m4=True)
    back = decode_entry(struct.pack('<II', len(c), len(ft)) + c, len(ft))
    assert back == bytes(ft), '回环失败'
    assert len(c) <= plen_old, '压缩后 %d > 原 %d, 超槽' % (len(c), plen_old)
    new_slot = struct.pack('<II', len(c), len(ft)) + c + b'\x00' * (FT_LEN - 8 - len(c))
    print('[pack] FT 槽 %d B (原 payload %d → %d)' % (len(new_slot), plen_old, len(c)))

    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(base + FT_OFF)
        f.write(new_slot)

    # ── 回读校验 ──
    chk = open(dst, 'rb').read()
    ft2 = decode_entry(chk[base + FT_OFF:base + FT_OFF + FT_LEN], 5942)
    assert ft2 == bytes(ft), '回读不符'
    f2 = parse_faces(ft2)
    n_new = sum(1 for f in f2 for i in range(f['nrec'])
                if struct.unpack_from('<HH', ft2, f['rec_off'] + i * 10 + 2)
                == (BAND_V, REC_V1))
    print('[verify] 回读 OK; 目标窗记录数 = %d (原 %d 条 (450,466))' % (n_new, n_fix))

    a, b = open(src, 'rb').read(), open(dst, 'rb').read()
    diffs = [i for i in range(0, len(a)) if a[i] != b[i]]
    lo, hi = min(diffs), max(diffs)
    print('[chk ] 全盘差异 %d 字节, 范围 0x%X..0x%X (期望落在 FT 槽 0x%X..0x%X)'
          % (len(diffs), lo, hi, base + FT_OFF, base + FT_OFF + FT_LEN))
    assert base + FT_OFF <= lo and hi < base + FT_OFF + FT_LEN, '改动越出 FT 槽!'


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1], sys.argv[2])
