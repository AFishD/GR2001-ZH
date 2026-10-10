# -*- coding: utf-8 -*-
r"""patch_zh68.py — GR_ZH68 = ZH67 + 帮助条手术常量 +3→+5 (1 词)

用户复测 (2026-10-03): GR_ZH67 (+2) 有改善但仍偏上一点点, 疑 j/g 式字体上抬。
复查: (1) CJK 格内墨迹全跨 [0,15], 无头空 (该因素不成立);
(2) 条带上边框 @378-379 此前漏检 → 条带实为 [379,404], 几何中心 391.5;
(3) ZH67 墨心 391.5 已几何居中, 但 EN 墨心 392.5 自带 1px 下沉
    (26px 行盒 descender 空间使可见墨团偏下) → 光栅对 float y 有亚像素舍入 (+1 被吸收, +3 才 +2px);
终测 (双盘差分抠文字): EN [389,396] 心 392.5; +2→390.5, +5→393.5 (线性) → +4 (F13 423) 恰中。

修改: cave 0x565750 (= 0x565730+0x20, 第 9 词): addiu t0,t0,2 → addiu t0,t0,4
     (0x25080002 → 0x25080004), 其余不动。

用法: python patch_zh68.py <src_iso> <dst_iso>   (基底 = GR_ZH67)
"""
import shutil
import struct
import sys

ELF_LBA = 295
VA, OLD, NEW = 0x565750, 0x25080002, 0x25080004


def main(src, dst):
    shutil.copyfile(src, dst)
    off = ELF_LBA * 2048 + 0x80 + (VA - 0x100000)
    with open(dst, 'r+b') as f:
        f.seek(off)
        cur = struct.unpack('<I', f.read(4))[0]
        assert cur == OLD, f'0x{VA:X} 现值 0x{cur:08X} != 0x{OLD:08X} (非 ZH67 基底?)'
        f.seek(off)
        f.write(struct.pack('<I', NEW))
        f.seek(off)
        assert struct.unpack('<I', f.read(4))[0] == NEW
    a = open(src, 'rb')
    b = open(dst, 'rb')
    pos, words = 0, set()
    while True:
        x, y = a.read(1 << 20), b.read(1 << 20)
        if not x:
            break
        for i in range(len(x)):
            if x[i] != y[i]:
                words.add((pos + i) & ~3)
        pos += len(x)
    a.close(); b.close()
    assert words == {off}, [hex(w) for w in words]
    print(f'[patch] 0x{VA:X}: 0x{OLD:08X} -> 0x{NEW:08X} (addiu +2->+4); 差异词集精确吻合')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
