# -*- coding: utf-8 -*-
r"""ab_build.py — 构建最小 A/B 打靶盘 (写 work/builds/GR_AB/**，既有盘只读)

  AB_00_base.iso          = GR_ZH113b.iso 逐字节拷贝 (对照)
  AB_01_sp222.iso         = DrawString+0x33C `lbu v0,221(sp)` → `222(sp)`   (1 字节)
  AB_02_sp221_revert.iso  = DrawString+0x33C 整对改回英文原盘 `nop; addiu s0,s0,1` (8 字节)
  AB_03_fontres_real7k.iso= FONT.RES(MENU+GR) 内部头 real 5,942→7,222 + 明文补零到 7,222 (重压)
  AB_04_fontres_real5942.iso = FONT.RES(MENU+GR) IMG 条目 real 7,222→5,942

每张盘输出 AB_xx.meta.json (逐字节差异清单 / sha256 / 尺寸 / 构建命令)。
"""
import hashlib
import io
import json
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ab_lib as A     # noqa: E402
import nh_lib as N     # noqa: E402
import numpy as np     # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
OUTD = A.OUT
CHUNK = 1 << 22


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        while True:
            b = fh.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def diff_runs(p1, p2):
    """→ [(off, len, a_hex, b_hex)]  逐字节差异, 合并相邻 (间距 ≤ 8 也合并展示)"""
    runs = []
    with open(p1, 'rb') as f1, open(p2, 'rb') as f2:
        base = 0
        carry = b''
        while True:
            a = f1.read(CHUNK)
            b = f2.read(CHUNK)
            if not a and not b:
                break
            assert len(a) == len(b), 'size differs'
            x = np.frombuffer(a, dtype=np.uint8)
            y = np.frombuffer(b, dtype=np.uint8)
            ne = np.nonzero(x != y)[0]
            if ne.size:
                # 把 carry 拼到前面
                if carry:
                    x = np.concatenate([np.frombuffer(carry, dtype=np.uint8), x])
                    y = np.concatenate([np.frombuffer(carry, dtype=np.uint8), y])
                    for s, e in _runs(x, y):
                        runs.append((base - len(carry) + int(s), int(e - s),
                                     bytes(x[s:e]), bytes(y[s:e])))
                    carry = b''
                else:
                    for s, e in _runs(x, y):
                        runs.append((base + int(s), int(e - s),
                                     bytes(x[s:e]), bytes(y[s:e])))
            base += len(a)
    return runs


def _runs(x, y):
    ne = np.nonzero(x != y)[0]
    if ne.size == 0:
        return []
    out = []
    s = int(ne[0])
    p = s
    for i in ne[1:]:
        i = int(i)
        if i - p <= 8:
            p = i
            continue
        out.append((s, p + 1))
        s = i
        p = i
    out.append((s, p + 1))
    return out


def base_bytes(off, n):
    with open(A.BASE_ZH, 'rb') as f:
        f.seek(off)
        return f.read(n)


def patch_bytes(dst, off, data, note):
    with open(dst, 'r+b') as f:
        f.seek(off)
        old = f.read(len(data))
        f.seek(off)
        f.write(data)
    return dict(iso_off=off, len=len(data), old=old.hex(' '), new=data.hex(' '), note=note)


def new_iso(path):
    shutil.copyfile(A.BASE_ZH, path)
    return path


# ------------------------------------------------------------------ 各盘
def build_00():
    p = os.path.join(OUTD, 'AB_00_base.iso')
    shutil.copyfile(A.BASE_ZH, p)
    return p, []


def build_01():
    va = 0x219DAC
    off = A.va2iso(va)
    old = struct.unpack('<I', base_bytes(off, 4))[0]
    assert old == 0x93A200DD, 'VA 0x%X 期望 0x93A200DD, 实得 0x%08X' % (va, old)
    # 0x93A200DD 小端 = DD 00 A2 93 ⇒ imm 低字节在 off+0 ⇒ 0xDD → 0xDE 得 0x93A200DE
    new = A.dis1(0x93A200DE, va)
    assert new == 'lbu v0,222(sp)', new
    e_en, _ = A.load_elf('EN_ORIG')
    assert struct.unpack('<I', e_en.b[A.va2file(va):A.va2file(va) + 4])[0] == 0x00000000
    p = new_iso(os.path.join(OUTD, 'AB_01_sp222.iso'))
    ch = [patch_bytes(p, off, b'\xDE',
                      'lbu v0,221(sp) (0x93A200DD) → lbu v0,222(sp) (0x93A200DE)'
                      '  — imm 低字节 @ISO+0')]
    with open(p, 'rb') as fh:
        fh.seek(off)
        got = struct.unpack('<I', fh.read(4))[0]
    assert got == 0x93A200DE, '构建后校验失败: 0x%08X' % got
    return p, ch


def build_02():
    va = 0x219DAC
    off = A.va2iso(va)
    for k in range(2):
        w = struct.unpack('<I', base_bytes(off + 4 * k, 4))[0]
        assert w == (0x93A200DD if k == 0 else 0x02028021), 'VA+%d 不符: 0x%08X' % (4 * k, w)
    # 英文原盘同址字节 (自证)
    e_en, _ = A.load_elf('EN_ORIG')
    en = bytes(e_en.b[A.va2file(va):A.va2file(va) + 8])
    assert en == bytes.fromhex('0000000001001026'), en.hex()   # nop ; addiu s0,s0,1 (小端)
    p = new_iso(os.path.join(OUTD, 'AB_02_sp221_revert.iso'))
    ch = [patch_bytes(p, off, en,
                      'DrawString+0x33C 整对回退英文原盘: lbu v0,221(sp);addu s0,s0,v0 '
                      '→ nop;addiu s0,s0,1')]
    return p, ch


def load_fontres_full(tag, imgk):
    iso = N.Iso(A.ISO[tag])
    e, base, raw, ents = A.fontres_entry(iso, A.IMG[imgk])
    iso.close()
    return e, base, raw, ents


def build_03():
    import lzo1x_c
    import lz77_decode
    p = new_iso(os.path.join(OUTD, 'AB_03_fontres_real7k.iso'))
    ch = []
    for imgk in ('MENU', 'GR'):
        e, base, raw, ents = load_fontres_full('ZH113b', imgk)
        plain, comp, real, se = A.decompress_fontres(raw)
        assert real == 5942 and comp == (1489 if imgk == 'MENU' else 1332), (imgk, real, comp)
        assert len(plain) == 5942
        newplain = plain + b'\x00' * (7222 - 5942)
        assert len(newplain) == 7222
        stream = lzo1x_c.compress(newplain)
        dd, err, _ = lz77_decode.lzo1x_decompress(stream, 7222)
        assert dd == newplain, 'LZO 自检失败 %s' % imgk
        assert len(stream) <= e['stored'] - 8, '压缩流 %d > 槽余量 %d' % (len(stream), e['stored'] - 8)
        blob = struct.pack('<II', len(stream), 7222) + stream
        blob = blob + b'\x00' * (e['stored'] - len(blob))
        assert len(blob) == e['stored']
        rd = dict(diff_runs_ok=True)
        # 只改前 8+len(stream) 个字节里的实际变化 (尾部补零对比)
        ch.append(patch_bytes(p, base + e['off'], blob,
                              'FONT.RES@%s: 内部头 real 5942→7222 ; LZO 流重压 '
                              '(明文 = 原 5942 B + 1280 B 零) ; comp %d→%d ; stored 仍 %d'
                              % (imgk, comp, len(stream), e['stored'])))
    return p, ch


def build_04():
    p = new_iso(os.path.join(OUTD, 'AB_04_fontres_real5942.iso'))
    ch = []
    for imgk in ('MENU', 'GR'):
        e, base, raw, ents = load_fontres_full('ZH113b', imgk)
        assert e['real'] == 7222 and e['stored'] == 4421, (imgk, e['real'])
        # 条目表字段 u32[7] = real
        foff = base + N.TAB_OFF + N.TAB_STEP * e['idx'] + 4 * 7
        old = struct.unpack('<I', base_bytes(foff, 4))[0]
        assert old == 7222, 'FONT.RES@%s 条目 real 期望 7222, 实得 %d' % (imgk, old)
        ch.append(patch_bytes(p, foff, struct.pack('<I', 5942),
                              'IMG %s 条目表 #%d FONT.RES real 7222→5942 (与内部头一致)'
                              % (imgk, e['idx'])))
        ch[-1]['img'] = imgk
        ch[-1]['entry_idx'] = e['idx']
    return p, ch


BUILDERS = [
    ('AB_00_base', build_00, 'GR_ZH113b.iso 的逐字节拷贝（基准/对照）'),
    ('AB_01_sp222', build_01, 'DrawString+0x33C: lbu v0,221(sp) → 222(sp)'),
    ('AB_02_sp221_revert', build_02, 'DrawString+0x33C 整对回退英文原盘 nop;addiu s0,s0,1'),
    ('AB_03_fontres_real7k', build_03, 'FONT.RES 内部头 real 5942→7222 + 明文补零到 7222'),
    ('AB_04_fontres_real5942', build_04, 'FONT.RES 的 IMG 条目 real 7222→5942'),
]


def main():
    only = sys.argv[1:] or None
    base_sha = None
    for (name, fn, desc) in BUILDERS:
        if only and name not in only:
            continue
        p, ch = fn()
        size = os.path.getsize(p)
        if base_sha is None:
            base_sha = sha256_file(A.BASE_ZH)
        runs = diff_runs(A.BASE_ZH, p)
        meta = dict(
            disk=name, file=os.path.relpath(p, A.REPO).replace('\\', '/'),
            size=size, sha256=sha256_file(p),
            base=os.path.relpath(A.BASE_ZH, A.REPO).replace('\\', '/'),
            base_sha256=base_sha, base_size=os.path.getsize(A.BASE_ZH),
            description=desc,
            build_cmd='python work/builds/GR_AB/tools/ab_build.py %s' % name,
            patch_list=ch,
            byte_diff_runs=[dict(iso_off=r[0], len=r[1], from_hex=r[2].hex(' '),
                                 to_hex=r[3].hex(' ')) for r in runs],
            byte_diff_total=sum(r[1] for r in runs),
        )
        with open(os.path.join(OUTD, name + '.meta.json'), 'w', encoding='utf-8') as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=1)
        print('%-24s size=%d sha256=%s' % (name, size, meta['sha256']))
        print('   diff runs=%d bytes=%d' % (len(runs), meta['byte_diff_total']))
        for r in runs[:12]:
            print('     ISO 0x%08X (%d B)  %s → %s' % (r[0], r[1], r[2].hex(' '), r[3].hex(' ')))
        for c in ch:
            print('   patch: %s' % c['note'])


if __name__ == '__main__':
    main()
