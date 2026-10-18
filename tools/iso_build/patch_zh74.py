# -*- coding: utf-8 -*-
r"""patch_zh74.py — GR_ZH74 = ZH72 + 任务内 HUD 指示条文字下移 2.5px (纯 ELF 补丁 1 词)

分支: gr-zh74-hudfeed (与 ZH73 人名缩写轮同为 ZH72 的兄弟增量, 字节零交集;
      合并时后到者以先到盘为基底重出)。

问题 (用户 2026-10-03 报障): 任务中击杀/操作后左上角黑底指示条 ("A/B组：XXXX")
文字显示位置靠上——CJK 字墨顶到框沿并捅出 1px。
复现: 主菜单→战术演习→练习2→进图后按 R3 → "B组：前进" (用户实测路径)。

定量 (gsrunner nav_mission.txt, R3@18500/19500, ZH72 vs EN 原版同 nav 同帧):
  黑框两盘同位 (snap y24-40, 17 行 — 引擎按 Latin 度量加边距);
  EN 字墨 y29-36 (上距 5/下距 4, 居中; pen y=24 时 Latin caps 墨自 pen+5.4 起);
  ZH 字墨 y23-35 (上距 -1 捅出框 / 下距 5, 整体比 EN 高 ~3.5px —
  zh7 套件 CJK 字形墨迹自 pen+0 起画, 无 Latin 基线留空)。
  引擎侧绘制坐标两盘相同 (219A70, RA=22E274, F12=30.0 F13=24.0) → 偏移全在
  墨迹相对笔位的排布, 与指针/坐标无关。

修复: 指示条渲染函数 (0x22DE7C-0x22E2B0) 文本 Y 的减法常数
  0x22E218: lui v0, 0x3F80 (1.0f) → lui v0, 0xBFC0 (-1.5f)。
  文本 Y 在 0x22E224 = sub.s f20, f1, f0 (f1 = 25 + 行×行高, f0 = 1.0) → Y = 24;
  改减数为 -1.5 → Y = 26.5 = 文本整体 +2.5px (游戏空间, gsrunner 亮度加权质心校准)。
  黑框几何由 quad 段 ([obj+0x64]+20.0 系) 构成, 不受影响 → 框不动、字墨在框内
  对称居中 (上/下距 ≈3/2.5, 原为 0/5 顶死上沿)。f20 全函数仅此一写一读
  (0x22E254 mov.s f13, f20), 无旁及。
  EN 对齐与几何居中两口径在此重合 (框即 EN 尺寸、框心=EN字心), 无 K 口径分歧。
  原词与 EN 逐字节同 (0x3C0241A0, 原版引擎常数); 多行提示逐行同移; 仅任务内
  HUD 路径, 菜单零涉及。

用法: python patch_zh74.py <src_iso> <dst_iso>   (基底 = GR_ZH72)
"""
import os
import shutil
import struct
import sys

ELF_LBA = 295
SEC_OFF, SEC_ADDR = 0x80, 0x00100000  # phdr0: vaddr 0x100000 @ file 0x80

WORDS = [
    # (VA, 期望原始词, 新词) — 0x22E218: lui v0,0x3F80 (1.0f) → 0xBFC0 (-1.5f)
    # 0x22E224 sub.s f20, f1, f0: 文本 Y = s2 - 1.0 (=24) → s2 + 1.5 (=26.5) = +2.5px 下移。
    # 校准记录: 常数 -2.0 实测字墨质心 +3.7px (框内下距归零, 过冲); -1.5 = 墨迹对称居中。
    # 注: 首版误改 0x22E1C8 (20.0f) — 该常数经 f21→f12 喂的是 X 坐标 (实测 F12 30→33,
    # F13/Y 不动), 已回退不改; Y 的真正杠杆是 0x22E218 的减数。
    (0x22E218, 0x3C023F80, 0x3C02BFC0),
]


def main(src, dst):
    shutil.copyfile(src, dst)
    base = ELF_LBA * 2048
    with open(dst, 'r+b') as f:
        f.seek(base)
        assert f.read(4) == b'\x7fELF', 'SLUS ELF 魔数错位 (LBA=%d?)' % ELF_LBA
        f.seek(base + 0x1C)
        phoff = struct.unpack('<I', f.read(4))[0]
        f.seek(base + phoff)
        p_type, p_offset, p_vaddr = struct.unpack('<III', f.read(12))
        assert (p_type, p_offset, p_vaddr) == (1, SEC_OFF, SEC_ADDR), \
            'phdr0 与 ZH72 不符: %r' % ((p_type, p_offset, p_vaddr),)
        for va, orig, new in WORDS:
            f.seek(base + SEC_OFF + (va - SEC_ADDR))
            cur = struct.unpack('<I', f.read(4))[0]
            assert cur == orig, '%06X: %08X != 原始 %08X (基底不是 ZH72?)' % (va, cur, orig)
            f.seek(base + SEC_OFF + (va - SEC_ADDR))
            f.write(struct.pack('<I', new))
        print('[elf] HUD 指示条文本 Y 减数 1.0f→-1.5f (1 词) 落盘')
    win = [(base + SEC_OFF + (va - SEC_ADDR), 4) for va, _, _ in WORDS]
    a = open(src, 'rb')
    b = open(dst, 'rb')
    pos, bad = 0, []
    while True:
        ca, cb = a.read(1 << 20), b.read(1 << 20)
        if not ca:
            break
        for i in range(len(ca)):
            if ca[i] != cb[i]:
                p = pos + i
                if not any(o <= p < o + l for o, l in win):
                    bad.append(p)
        pos += len(ca)
    a.close()
    b.close()
    assert not bad, '窗口外差异 ' + repr([hex(x) for x in bad[:5]])
    print('[diff] 差异全部位于 1 词窗口 ✓ (纯 ELF 补丁, 4B)')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
