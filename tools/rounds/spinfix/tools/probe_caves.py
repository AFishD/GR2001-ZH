# -*- coding: utf-8 -*-
r"""probe_caves.py —— 候选 cave 落点是否「运行期从未被写过」：在全部可得 RAM 快照上逐字节核对。

快照来源（全部只读）：
  * 用户真机 dump ×2（帧 19701 / 23444）
  * GR_OOMFIX u1 基线 run 的帧 43/44/45/46 全 RAM 快照
  * GR_SPINFIX states\S1_bin126_user.p2s 的 eeMemory 原像
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sf_common as C   # noqa: E402

ROOT = C.ROOT
CAND = [
    (0x0055B730, 0x0055B780, '候选 A：80 B（OOMFIX 曾以「堆管理数据区」为由拒绝）'),
    (0x005DECC4, 0x005DED00, '候选 B：60 B（段尾填充）'),
    (0x0041A35C, 0x0041A380, '候选 C：36 B（iomanX 尾 / 零填充，审计 prob=0）'),
    (0x0056F160, 0x0056F180, '候选 D：32 B（审计 raw=1）'),
]


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    srcs = []
    for tag, p in (
            ('dump19701', os.path.join(ROOT, r'work\builds\GR_HOOKEMU_QT2\qt\hookdumps\hook_19701_hotkey_f10\ee_ram.bin')),
            ('dump23444', os.path.join(ROOT, r'work\builds\GR_HOOKEMU_QT2\qt\hookdumps\hook_23444_hotkey_f10\ee_ram.bin')),
            ('u1_f43', os.path.join(ROOT, r'work\builds\GR_OOMFIX\runs\u1_base_l1\win_f00000043_eeram.bin')),
            ('u1_f44', os.path.join(ROOT, r'work\builds\GR_OOMFIX\runs\u1_base_l1\win_f00000044_eeram.bin')),
            ('u1_f45', os.path.join(ROOT, r'work\builds\GR_OOMFIX\runs\u1_base_l1\win_f00000045_eeram.bin')),
            ('u1_f46', os.path.join(ROOT, r'work\builds\GR_OOMFIX\runs\u1_base_l1\win_f00000046_eeram.bin')),
            ('a1_f2', os.path.join(ROOT, r'work\builds\GR_OOMFIX\runs\u1_base_l1\WPNRPK74_f00000002_eeram.bin')),
    ):
        if os.path.exists(p):
            srcs.append((tag, open(p, 'rb').read()))
    z = C.load_zstd_tool()
    st = os.path.join(ROOT, r'work\builds\GR_SPINFIX\states\S1_bin126_user.p2s')
    srcs.append(('state_S1', z.decompress_entry(st, 'eeMemory.bin')))

    for lo, hi, why in CAND:
        print('%s\n  0x%08X..0x%08X (%d B)' % (why, lo, hi, hi - lo))
        allzero = True
        for tag, ram in srcs:
            seg = ram[lo:hi]
            nz = sum(1 for b in seg if b)
            allzero = allzero and (nz == 0)
            print('    %-10s 非零字节 %3d / %d  %s' % (tag, nz, len(seg),
                                                       (seg[:16].hex() if nz else '')))
        print('    ⇒ 全部快照都是零：%s\n' % allzero)
    return 0


if __name__ == '__main__':
    sys.exit(main())
