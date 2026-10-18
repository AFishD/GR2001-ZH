# -*- coding: utf-8 -*-
r"""spinfix_state.py —— 【GR_SPINFIX / A】造「坏桶存档」：把用户真机的坏值注入可用即时存档的 eeMemory.bin。

三种注入粒度（都由同一份基底存档出发，单变量）：
  S3_base       : 原样复制（健康对照；桶 126 = 存档自带值 0xA73D37F0）
  S1_bin126     : 只改 8 字节 —— 0x0055BB98 / 0x0055BB9C = 用户真机**新 dump** 的坏值 0x6ED47823
  S2_win500     : 把用户新 dump 的 0x00500000..0x00580000（512KB）整段搬进来（任务书字面要求）

基底：work\builds\GR_LAYOUT\SLUS-20613 (7A761FCA).01.p2s（= 用户 sstates 里 CRC 7A761FCA 的那份，
      与 GR_OOMFIX\common\state_LAY_fix1_bytecount.p2s 逐字节相同，sha256 34939ABD…75F3）

READ-ONLY 打开基底与用户 dump；只写 --outdir。
自证：重写后逐条目回读一致（由 oomfix_zstd.rewrite 保证）+ 每个注入点独立回读 + 与基底逐字节 diff 统计。
"""
import argparse
import hashlib
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sf_common as C   # noqa: E402

ROOT = C.ROOT
BASE_STATE = os.path.join(ROOT, r'work\builds\GR_LAYOUT\SLUS-20613 (7A761FCA).01.p2s')
DUMP_NEW = os.path.join(ROOT, r'work\builds\GR_HOOKEMU_QT2\qt\hookdumps\hook_23444_hotkey_f10\ee_ram.bin')
DUMP_OLD = os.path.join(ROOT, r'work\builds\GR_HOOKEMU_QT2\qt\hookdumps\hook_19701_hotkey_f10\ee_ram.bin')
WIN_LO, WIN_HI = 0x00500000, 0x00580000
BIN126_FD, BIN126_BK = 0x0055BB98, 0x0055BB9C
ENTRY = 'eeMemory.bin'


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('--outdir', default=os.path.join(ROOT, r'work\builds\GR_SPINFIX\states'))
    a = ap.parse_args()
    z = C.load_zstd_tool()

    base_ram = z.decompress_entry(BASE_STATE, ENTRY)
    assert len(base_ram) == 32 << 20
    new_ram = open(DUMP_NEW, 'rb').read()
    old_ram = open(DUMP_OLD, 'rb').read()
    bad_fd, bad_bk = struct.unpack_from('<II', new_ram, BIN126_FD)
    assert bad_fd == bad_bk == 0x6ED47823, (hex(bad_fd), hex(bad_bk))
    base_fd, base_bk = struct.unpack_from('<II', base_ram, BIN126_FD)
    rep = dict(
        tool=r'work\builds\GR_SPINFIX\tools\spinfix_state.py',
        base_state=BASE_STATE, base_sha256=C.sha256_file(BASE_STATE),
        base_ee_sha256=hashlib.sha256(base_ram).hexdigest(),
        base_bin126=['0x%08X' % base_fd, '0x%08X' % base_bk],
        user_dump_new=DUMP_NEW, user_dump_new_sha256=C.sha256_file(DUMP_NEW),
        user_dump_old=DUMP_OLD, user_dump_old_sha256=C.sha256_file(DUMP_OLD),
        user_bin126=['0x%08X' % bad_fd, '0x%08X' % bad_bk],
        states=[])
    os.makedirs(a.outdir, exist_ok=True)

    variants = []
    # S3_base：原样
    variants.append(('S3_base', bytearray(base_ram), '原样复制（健康对照）'))
    # S1_bin126：只改 8 字节
    r1 = bytearray(base_ram)
    struct.pack_into('<II', r1, BIN126_FD, bad_fd, bad_bk)
    variants.append(('S1_bin126_user', r1,
                     '只改 0x0055BB98/0x0055BB9C = 用户真机坏值 0x6ED47823（分配器相关内存的最小注入）'))
    # S2_win500：整段 512KB 覆盖
    r2 = bytearray(base_ram)
    r2[WIN_LO:WIN_HI] = new_ram[WIN_LO:WIN_HI]
    variants.append(('S2_win500_580', r2,
                     '把用户新 dump 的 0x00500000..0x00580000（512KB）整段覆盖（任务书字面要求）'))

    for tag, ram, note in variants:
        out = os.path.join(a.outdir, tag + '.p2s')
        z.rewrite(BASE_STATE, out, ENTRY, bytes(ram))
        chk = z.decompress_entry(out, ENTRY)
        fd, bk = struct.unpack_from('<II', chk, BIN126_FD)
        # 与基底逐字节差异
        diffs = [i for i in range(len(chk)) if chk[i] != base_ram[i]]
        d = dict(tag=tag, path=out, bytes=os.path.getsize(out),
                 sha256=C.sha256_file(out), note=note,
                 ee_sha256=hashlib.sha256(chk).hexdigest(),
                 bin126_readback=['0x%08X' % fd, '0x%08X' % bk],
                 diff_bytes_vs_base=len(diffs),
                 diff_ranges_vs_base=_ranges(diffs),
                 binmap_readback='0x%016X' % struct.unpack_from('<Q', chk, 0x0055B7A0)[0],
                 top_readback='0x%08X' % struct.unpack_from('<I', chk, 0x0055B7A8)[0],
                 size32mb_ok=(len(chk) == 32 << 20))
        assert d['size32mb_ok']
        rep['states'].append(d)
        print('%-18s %s  %d B  sha256=%s' % (tag, out, d['bytes'], d['sha256']))
        print('    桶126 回读 = %s ; 与基底差异 %d B %s ; binmap=%s top=%s'
              % (d['bin126_readback'], d['diff_bytes_vs_base'], d['diff_ranges_vs_base'],
                 d['binmap_readback'], d['top_readback']))

    # 用户 dump 的旧值（对照说明用）
    ofd, obk = struct.unpack_from('<II', old_ram, BIN126_FD)
    rep['user_old_bin126'] = ['0x%08X' % ofd, '0x%08X' % obk]
    rep['note_kseg1'] = ('存档自带的 0xA73D37F0 落在 EE KSEG1(0xA0000000-0xBFFFFFFF)，'
                         '访存按 addr&0x1FFFFFFF 折算到 RAM 0x073D37F0 ⇒ 不 TLB Miss、只是读到垃圾；'
                         '用户真机的 0x6ED47823 属未映射 KUSEG ⇒ TLB Miss ⇒ 读回 0 ⇒ 自旋。')
    mp = os.path.join(a.outdir, 'states.meta.json')
    with open(mp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print('\n[meta] %s' % mp)
    return 0


def _ranges(diffs, maxrun=8):
    if not diffs:
        return []
    out, s, p = [], diffs[0], diffs[0]
    for i in diffs[1:]:
        if i != p + 1:
            out.append('0x%08X..0x%08X' % (s, p + 1))
            s = i
        p = i
    out.append('0x%08X..0x%08X' % (s, p + 1))
    return out[:maxrun] + (['...(%d runs)' % len(out)] if len(out) > maxrun else [])


if __name__ == '__main__':
    sys.exit(main())
