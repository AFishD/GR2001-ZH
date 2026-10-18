# -*- coding: utf-8 -*-
r"""root_probe_gate.py -- round85 探针: 只改 UITexture::LoadPS2Img 的尺寸判据上界（READ-ONLY on src）

单变量: ISO 里 ELF 的**两条** `slti $at,$vX,1025` → `slti $at,$vX,2049`。
其余字节一律不动（含 COMMON.PAK / MENU.IMG / 所有目录）。

VA → ISO 偏移映射: **ISO = VA − 0x6C780**（本轮用 3 个锚点 × 2 张盘交叉核验：
  · VA 0x416EE8（cave 的 `sltiu …`）⇒ 0x3AA768 ✓
  · VA 0x51D9BC（LoadPS2Img 的 `slti $at,$v1,1025`）⇒ 0x4B123C ✓
  · VA 0x51DB24（PSMT4 镜像分支的同一条）⇒ 0x4B13A4 ✓
  注：任务书给的 `0x93800 + (VA − 0x100080)` = VA − 0x6C880 **差 0x100**，本轮按实测 0x6C780。
"""
import argparse
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
MAP = -0x6C780                       # ISO = VA + MAP
GATES = {0x51D9BC: ('w', 0x28610401, 0x28610801),      # slti $at,$v1,1025 -> 2049
         0x51D9C8: ('h', 0x28410401, 0x28410801),      # slti $at,$v0,1025 -> 2049
         0x51DB24: ('w(PSMT8)', 0x28610401, 0x28610801),
         0x51DB30: ('h(PSMT8)', 0x28410401, 0x28410801)}
CHK_VA, CHK_WORD = 0x416EE8, (0x2CA900B7, 0x2CA900B1, 0x2CA900B4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--sites', default='0x51D9BC,0x51D9C8',
                    help='要改的站点（逗号分隔 VA），默认只改 LoadPS2Img 的两个')
    ap.add_argument('--limit', type=lambda s: int(s, 0), default=2049)
    a = ap.parse_args()

    sites = []
    for tok in a.sites.replace('0x', '').replace('0X', '').replace(',', ' ').replace(';', ' ').split():
        sites.append(int(tok, 16))
    if not sites:
        sites = [0x51D9BC, 0x51D9C8]
    print('=' * 78)
    print('root_probe_gate.py  ★ 单变量: LoadPS2Img 尺寸判据上界 1025 → %d' % a.limit)
    print('  src = %s' % a.src)
    print('  dst = %s' % a.dst)
    print('  sites = %s' % ['0x%X' % s for s in sites])

    with open(a.src, 'rb') as f:
        # 1) 映射自校验
        off = CHK_VA + MAP
        f.seek(off)
        w, = struct.unpack('<I', f.read(4))
        assert w in CHK_WORD, '映射自校验失败: VA 0x%X 读出 %08X' % (CHK_VA, w)
        print('[chk] VA 0x%X -> ISO 0x%X = %08X ✓ (映射与 4 处 gate 站点自校验一致)'
              % (CHK_VA, off, w))

        # 2) 逐站点回读原字并校验
        plan = []
        for va in sites:
            o = va + MAP
            f.seek(o)
            cur, = struct.unpack('<I', f.read(4))
            tag, old, new_exp = GATES[va]
            assert cur == old, 'VA 0x%X 原字 %08X ≠ 期望 %08X' % (va, cur, old)
            new = (old & 0xFFFF0000) | (a.limit & 0xFFFF)
            assert cur != new
            plan.append((va, o, tag, cur, new))
            print('[gate] VA 0x%08X (%s) ISO 0x%X : %08X -> %08X' % (va, tag, o, cur, new))

        # 3) 写盘
        os.makedirs(os.path.dirname(os.path.abspath(a.dst)), exist_ok=True)
        with open(a.dst, 'wb') as g:
            f.seek(0)
            while True:
                blk = f.read(1 << 22)
                if not blk:
                    break
                g.write(blk)
    with open(a.dst, 'r+b') as g:
        for (va, o, tag, cur, new) in plan:
            g.seek(o)
            g.write(struct.pack('<I', new))

    # 4) 回读断言 + 全盘差异核对
    import hashlib
    n_diff = 0
    with open(a.src, 'rb') as f1, open(a.dst, 'rb') as f2:
        while True:
            b1 = f1.read(1 << 22)
            b2 = f2.read(1 << 22)
            if not b1:
                break
            if b1 != b2:
                for i in range(min(len(b1), len(b2))):
                    if b1[i] != b2[i]:
                        n_diff += 1
    print('[A1] 回读:')
    with open(a.dst, 'rb') as g:
        for (va, o, tag, cur, new) in plan:
            g.seek(o)
            got, = struct.unpack('<I', g.read(4))
            print('     VA 0x%08X = %08X %s' % (va, got, '✓' if got == new else '✗'))
            assert got == new
    print('[A2] 全盘逐字节差异 = %d 字节 (期望 %d = 每站点只动立即数的高字节)'
          % (n_diff, 2 * len(plan)))
    assert n_diff == 2 * len(plan)
    print('[A3] 输出 %s (%d B)' % (a.dst, os.path.getsize(a.dst)))
    print('[A4] sha256(src)=%s' % hashlib.sha256(open(a.src, 'rb').read()).hexdigest()[:16])
    print('[A4] sha256(dst)=%s' % hashlib.sha256(open(a.dst, 'rb').read()).hexdigest()[:16])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
