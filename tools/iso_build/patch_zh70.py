# -*- coding: utf-8 -*-
r"""patch_zh70.py — GR_ZH70 = ZH69 + 兵种比较键还原 (G58.I568-572 大写 EN 值)

问题 (2026-10-03 用户报障): 战术演习→练习1→小队设置右下角显示乱码「支组进项对」,
末字横向压缩。查实: 乱码实为「支组进向」+ TAB(0x09 越界取 FT 记录 223 的窄字形=「对」观感)。

根因 (全链实证): GetLocalizedClassName (0x2BFE40) 把 ATR ClassName 大写后与
GetString(id) 比较四路 (RIFLEMAN/DEMOLITIONS/SNIPER/SUPPORT), 命中返回显示串
(id-5 = G58.I563-567 的中文显示名)。zh7 时代把**比较键条目** G58.I568-572
(EN 大写 DEMO/DEMOLITIONS/RIFLEMAN/SNIPER/SUPPORT — 引擎内部键, 非用户可见文本)
也翻译成了中文 → "RIFLEMAN" != "突击队员" 四路全失配 → s0 未初始化 → GetString(垃圾 id)
→ 内存垃圾串「 支组进向\t」上屏 (含 0x09 TAB)。
显示名条目 I563-567 (爆破手/突击队员/狙击手/支援队员) 保持中文不变。

修复: MENU+GR 双份 RES 重编码 G58.I568-572 → EN 大写原值 (text_replace, 基底 ZH69 裁尾)。

用法: python patch_zh70.py <src_iso> <dst_iso>   (基底 = GR_ZH69)

状态 (2026-10-03 终盘定版, sha256 1fa547fa…): 仅比较键还原 (无 TXT 改动 —
尾空格实验因把字段挪回 ZH69 原残串而判死, PROGRESS §35)。
终盘字节级验证: 小队兵种字段 ZH69 ' 20 A4B1 C4D0 E1 09' (支族, 池 0x5DEA45) →
ZH70 ' 20 A2B6 B6E1 09' (突击族, 池 0x5D6F9F); EN 原版 (313,380) ' Rifleman'。
残留: 显示名 id 0x3902xx 在 RSStrMgr 表 3 (6 条脚本串, EN 同构) 越界 → GetString
返回池残留 (EN ' Rifleman' 系文件名派生串恰好占位) — 根治留待下一轮
gsrunner GetString 返回值钩子定点 (比较命中改 id vs 池布局挪移, 两说并立)。
"""
import hashlib
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MENU_LBA, GR_LBA = 776286, 19175
RES_WRITES = [
    ('MENU', MENU_LBA, 25, 47570, 'menu_res_classkeys.bin', '838634a73d89af06'),
    ('GR',   GR_LBA, 902, 47619, 'gr_res_classkeys.bin', '0a3fbcf7561c5bec'),
]


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
        for tag, lba, idx, slot, fname, sha16 in RES_WRITES:
            blob = open(os.path.join(HERE, 'assets_zh70', fname), 'rb').read()
            assert hashlib.sha256(blob).hexdigest()[:16] == sha16, fname
            assert len(blob) <= slot
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
            print(f'[{tag}] #{idx} 兵种比较键还原 {len(blob)}B+零填')
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
    print('[diff] 差异全部位于两 RES 窗口 ✓')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
