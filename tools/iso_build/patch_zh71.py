# -*- coding: utf-8 -*-
r"""patch_zh71.py — GR_ZH71 = ZH70 + 兵种显示名纯对偶编码 + 字库 5 字补格

问题 (ZH70 残留, PROGRESS §36 定案): 小队兵种字段 (右下, EN ' Rifleman') 画
' 突击向\t' (20 A2B6 B6E1 09) — zh7 绘层换行改道 (0x21C624→0x417590→DoWordWrap
拼接段→0x565900 伪造 RA) 的字节扫描器不识单字节汉字 (76 singles: 击=B6 队=C1
员=E9 …), 把 single 当对偶 lead 吞掉下一字节 → 字段串指针甩进资源池布局残留
(0x5D6F9F, 布局敏感: ZH69 画'支组进向', ZH70b TXT+0x20 又回支组进向)。

RES 条目本身从未损坏 (singles 解码 = 装备：/爆破/爆破手/突击队员/狙击手/支援队员),
字库也从未缺字 — 本轮"残片/缺字"初判为误 (只查了 pair_of 未查 codes 单字节层)。

修复:
  1) 字库: +5 对偶槽 ADF5-ADF9 (爆击手队员, 行19 空格, ELF cave 公式驱动免 FT),
     链: charset+5 → build_font(X0=4) → fld26 → make_pak → shift (vs 现役差
     89B 基线 + 245B 五字墨迹; ISO 侧只落行19 墨迹带, EN 带/FT/NLOOP 原样保留);
  2) RES (MENU#25+GR#902): G58.I562-567 六条改纯对偶编码 (零 single):
     装备：→军械： (装=单字节 E4 无对偶, 换军械), 爆破/爆破手/突击队员/狙击手/
     支援队员 — 击队手员爆走新对偶 ADF5-ADF9。比较键 I568-572 (ZH70 还原) 不动。

用法: python patch_zh71.py <src_iso> <dst_iso>   (基底 = GR_ZH70)

状态 (2026-10-03): **实验盘, 不入主线** — 字段实测 ' 突[坏]队员' (组装器把记录
第 4 字节 +0x20: ADF6→AD16), 未达干净显示; 真根因 = zh7 套件字段指针错 +
组装器坏字节, 见 PROGRESS §36。字库输入已回退 1136 (ZH70 重放基线), 本补丁
的 1141 字库产物快照存 assets_zh71/font_entry_zh71.bin。
"""
import hashlib
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MENU_LBA, GR_LBA = 776286, 19175
OFF_REC = 0x58431
REC_LEN = 0x4147D - 0x1031
FONT_ENTRY = os.path.join(HERE, 'assets_zh71', 'font_entry_zh71.bin')
RES_WRITES = [
    ('MENU', MENU_LBA, 25, 47570, 'menu_res_classnames.bin'),
    ('GR',   GR_LBA, 902, 47619, 'gr_res_classnames.bin'),
]
# 行19 五字格墨迹带 (atlas y 354-370, entry 内偏移), 其余差异 (89B 基线等) 不入盘
GLYPH_BAND = (0x2C000, 0x2F000)


def res_entry(f, lba, idx):
    f.seek(lba * 2048 + 0x10)
    names_off = struct.unpack('<I', f.read(4))[0]
    f.seek(lba * 2048 + 0x830 + 48 * idx + 24)
    stored, real, off = struct.unpack('<III', f.read(12))
    f.seek(lba * 2048 + names_off)
    return stored, real, off


def main(src, dst):
    shutil.copyfile(src, dst)
    win = []
    with open(dst, 'r+b') as f:
        # 1) 字库条目: 仅行19 墨迹带
        new_ent = open(FONT_ENTRY, 'rb').read()
        assert len(new_ent) == REC_LEN, (len(new_ent), REC_LEN)
        f.seek(MENU_LBA * 2048 + OFF_REC)
        cur_ent = bytearray(f.read(REC_LEN))
        diffs = [(i, new_ent[i]) for i in range(REC_LEN) if new_ent[i] != cur_ent[i]]
        band = [d for d in diffs if GLYPH_BAND[0] <= d[0] < GLYPH_BAND[1]]
        out_band = [d for d in diffs if not (GLYPH_BAND[0] <= d[0] < GLYPH_BAND[1])]
        # 带外差 = 重放基线 (1B NLOOP) + ZH65-69 EN 带手工标定 (现役盘较新, 原样保留)
        assert len(out_band) <= 2100, len(out_band)
        assert 32 <= len(band) <= 2048, len(band)
        for i, b in band:
            cur_ent[i] = b
        f.seek(MENU_LBA * 2048 + OFF_REC)
        f.write(cur_ent)
        iso_off = MENU_LBA * 2048 + OFF_REC
        win.append((iso_off, REC_LEN))
        print('[font] 行19 五字格墨迹 %dB 落盘 (带内差 %dB)' % (len(band), len(band)))
        # 2) 双 RES
        for tag, lba, idx, slot, fname in RES_WRITES:
            blob = open(os.path.join(HERE, 'assets_zh71', fname), 'rb').read()
            assert len(blob) <= slot, (tag, len(blob), slot)
            stored, real, off = res_entry(f, lba, idx)
            iso_off = lba * 2048 + off
            assert stored == slot, (tag, stored, slot)
            f.seek(iso_off)
            f.write(blob)
            f.write(b'\x00' * (slot - len(blob)))
            f.seek(iso_off)
            back = f.read(slot)
            assert back[:len(blob)] == blob and set(back[len(blob):]) == {0}
            win.append((iso_off, slot))
            print('[%s] #%d 兵种显示名纯对偶 %dB+零填' % (tag, idx, len(blob)))
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
    a.close(); b.close()
    assert not bad, f'窗口外差异 {[hex(x) for x in bad[:5]]}'
    print('[diff] 差异全部位于字库带 + 两 RES 窗口 ✓')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
