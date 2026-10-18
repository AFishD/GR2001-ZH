# -*- coding: utf-8 -*-
r"""space_probe_pak.py -- 探针 B: 为 COMMON.PAK 原地长大腾地（字库记录一字不动）。

单变量 = "COMMON.PAK 的声明长度 +G 字节"。做法（MENU.IMG 内部）：
  1. ISO 目录记录 MENU.IMG;1 data length  +ADD  (0x828D8/0x828DC)  ← 把容器尾从 61236 扩到 91490
  2. 把挡在 PAK 身后的 2 个条目搬进新的容器尾（只改表里的 off）:
        FONT.RES              stored 4421  real 7222  off 0x0B9120 -> 0x378AAA0
        EN_MESSAGE_MC_4.RSB   stored 69404             off 0x0BA270 -> 0x378BBF0
  3. 旧位置清零, COMMON.PAK 的 stored += G

**不动**: 字库记录(px_size/h/像素) / FONT.RES 内容 / ELF / 文本 / 任何 glyph。
判据: 与探针 A 同样的实机判据（进主菜单 + 特别收录 + 文本逐像素一致）。

用法: python tools/re/toolbelt/space_probe_pak.py <src_iso> <dst_iso> [--add 30254] [--grow 41440]
"""
import argparse
import hashlib
import os
import shutil
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SEC = 2048
MENU_LBA = 776286
MENU_SIZE = 58300882
ISO_SECTORS = 804768
REC_LE, REC_BE = 0x828D8, 0x828DC
TAB_OFF, TAB_STEP = 0x830, 48
PAK_END_OLD = 0x57400 + 400659            # 0xB9113


def a16(x):
    return (x + 15) & ~15


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--add', type=int, default=30254)
    ap.add_argument('--grow', type=int, default=41440)
    a = ap.parse_args()
    assert os.path.isfile(a.src)
    assert not os.path.exists(a.dst), '拒绝覆盖: %s' % a.dst
    maxadd = ISO_SECTORS * SEC - MENU_LBA * SEC - MENU_SIZE
    assert 0 < a.add <= maxadd, 'add 超限 (%d > %d)' % (a.add, maxadd)

    print('[copy] -> %s' % a.dst)
    os.makedirs(os.path.dirname(os.path.abspath(a.dst)), exist_ok=True)
    shutil.copyfile(a.src, a.dst)
    base = MENU_LBA * SEC
    new_size = MENU_SIZE + a.add

    with open(a.dst, 'r+b') as f:
        # ---- 0) 读旧表, 严格校验 ----
        def ent(i):
            f.seek(base + TAB_OFF + TAB_STEP * i)
            r = struct.unpack('<12I', f.read(48))
            return dict(idx=i, stored=r[6], real=r[7], off=r[8])

        p, ft, mc = ent(3), ent(4), ent(5)
        print('[chk ] #3 PAK off=0x%X stored=%d | #4 FONT.RES off=0x%X stored=%d real=%d | '
              '#5 MC_4 off=0x%X stored=%d' %
              (p['off'], p['stored'], ft['off'], ft['stored'], ft['real'],
               mc['off'], mc['stored']))
        assert p['off'] == 0x57400 and p['stored'] == 400659, 'COMMON.PAK 位置/长度不符'
        assert ft['off'] == 0xB9120 and ft['stored'] == 4421 and ft['real'] == 7222, 'FONT.RES 不符'
        assert mc['off'] == 0xBA270 and mc['stored'] == 69404, 'EN_MESSAGE_MC_4.RSB 不符'
        assert p['off'] + p['stored'] == PAK_END_OLD

        # ---- 1) ISO 目录记录长度 ----
        f.seek(REC_LE)
        le, be = struct.unpack('<I', f.read(4))[0], struct.unpack('>I', f.read(4))[0]
        assert le == MENU_SIZE and be == MENU_SIZE, '目录记录初值不符'
        f.seek(REC_LE)
        f.write(struct.pack('<I', new_size) + struct.pack('>I', new_size))
        print('[len ] MENU.IMG 声明长度 %d -> %d (+%d)' % (MENU_SIZE, new_size, a.add))

        # 容器尾起点 = 所有存活条目 (off+stored) 的最大值  ★ 不是 PAK 身后！
        last_end = 0
        n_ent = 0
        for i in range(2000):
            f.seek(base + TAB_OFF + TAB_STEP * i)
            raw = struct.unpack('<12I', f.read(48))
            if raw[6] == 0 and raw[8] == 0:
                break
            n_ent = i + 1
            if 0 < raw[8] < MENU_SIZE and raw[6] > 0:
                last_end = max(last_end, raw[8] + raw[6])
        print('[tail] 条目数=%d, 容器尾起点 = 0x%X, 容器内尾长 = %d, 扩展后总尾长 = %d'
              % (n_ent, last_end, MENU_SIZE - last_end, new_size - last_end))
        assert last_end > PAK_END_OLD
        room = new_size - last_end

        # ---- 2) 新落点 ----
        ft_new = a16(last_end)
        mc_new = a16(ft_new + ft['stored'])
        assert mc_new + mc['stored'] <= new_size, ('尾部装不下: %d > %d' %
                                                   (mc_new + mc['stored'], new_size))
        print('[move] FONT.RES  0x%X -> 0x%X (%d B)' % (ft['off'], ft_new, ft['stored']))
        print('[move] MC_4      0x%X -> 0x%X (%d B)' % (mc['off'], mc_new, mc['stored']))
        print('[room] 尾部可用 = %d, 需要 %d, 余 %d' %
              (room, (mc_new + mc['stored']) - ft_new,
               new_size - (mc_new + mc['stored'])))

        def copy(dst_off, src_off, n, name):
            f.seek(base + src_off)
            d = f.read(n)
            assert len(d) == n
            f.seek(base + dst_off)
            f.write(d)
            f.seek(base + dst_off)
            back = f.read(n)
            assert back == d, '%s 回读不符' % name
            print('       %s 搬运回读 OK (sha %s)' % (name, hashlib.sha256(d).hexdigest()[:16]))

        copy(ft_new, ft['off'], ft['stored'], 'FONT.RES')
        copy(mc_new, mc['off'], mc['stored'], 'EN_MESSAGE_MC_4.RSB')

        # ---- 3) 旧位置清零 + PAK 声明变长 ----
        pak_new_stored = p['stored'] + a.grow
        pak_new_end = p['off'] + pak_new_stored
        f.seek(base + PAK_END_OLD)
        f.write(b'\x00' * (pak_new_end - PAK_END_OLD))
        print('[zero] [0x%X, 0x%X) 清零 (%d B)' % (PAK_END_OLD, pak_new_end,
                                                   pak_new_end - PAK_END_OLD))

        # ---- 4) 写回表项 ----
        def setent(i, stored=None, real=None, off=None):
            f.seek(base + TAB_OFF + TAB_STEP * i)
            raw = list(struct.unpack('<12I', f.read(48)))
            if stored is not None:
                raw[6] = stored
            if real is not None:
                raw[7] = real
            if off is not None:
                raw[8] = off
            f.seek(base + TAB_OFF + TAB_STEP * i)
            f.write(struct.pack('<12I', *raw))
            # LE/BE 镜像 (前 8 个 u32 是 4 对 LE/BE; +24/+28/+32 只有 LE)
            f.seek(base + TAB_OFF + TAB_STEP * i + 24)
            f.write(struct.pack('<I', raw[6]) + struct.pack('<I', raw[7]) +
                    struct.pack('<I', raw[8]))

        setent(3, stored=pak_new_stored)
        setent(4, off=ft_new)
        setent(5, off=mc_new)
        print('[tab ] #3 stored=%d  #4 off=0x%X  #5 off=0x%X' %
              (pak_new_stored, ft_new, mc_new))

        # ---- 5) 回读校验 ----
        f.seek(base + 0x830 + 48 * 3 + 24)
        r3 = struct.unpack('<3I', f.read(12))
        f.seek(base + 0x830 + 48 * 4 + 24)
        r4 = struct.unpack('<3I', f.read(12))
        f.seek(base + 0x830 + 48 * 5 + 24)
        r5 = struct.unpack('<3I', f.read(12))
        print('[veri] #3 stored=%d(real=%d off=0x%X) #4 off=0x%X #5 off=0x%X' %
              (r3[0], r3[1], r3[2], r4[2], r5[2]))
        assert r3[0] == pak_new_stored and r4[2] == ft_new and r5[2] == mc_new
        # FONT.RES / MC_4 内容在新位置逐字节验证（与基底同偏移比 sha256）
        f.seek(base + ft_new)
        got = hashlib.sha256(f.read(ft['stored'])).hexdigest()
        want = _sha_at(a.src, base + ft['off'], ft['stored'])
        assert got == want, 'FONT.RES 内容不符'
        f.seek(base + mc_new)
        got = hashlib.sha256(f.read(mc['stored'])).hexdigest()
        want = _sha_at(a.src, base + mc['off'], mc['stored'])
        assert got == want, 'MC_4 内容不符'
        print('[veri] FONT.RES / MC_4 新位置内容 sha256 与基底一致')
        # COMMON.PAK 前 400659 字节必须与基底逐字节一致
        f.seek(base + p['off'])
        got = hashlib.sha256(f.read(p['stored'])).hexdigest()
        want = _sha_at(a.src, base + p['off'], p['stored'])
        assert got == want, 'COMMON.PAK 原有内容被动了'
        print('[veri] COMMON.PAK 原 400659 B 逐字节未变')

    assert os.path.getsize(a.dst) == ISO_SECTORS * SEC, 'ISO 尺寸变了'
    print('[done] %s  (ISO 尺寸不变 = %d)' % (a.dst, os.path.getsize(a.dst)))


def _sha_at(path, off, n):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        f.seek(off)
        left = n
        while left > 0:
            b = f.read(min(1 << 20, left))
            if not b:
                break
            h.update(b)
            left -= len(b)
    return h.hexdigest()


main()
