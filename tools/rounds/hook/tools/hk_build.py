# -*- coding: utf-8 -*-
r"""hk_build.py — 构建「钩子二分」打靶盘 (写 work/builds/GR_HOOK/**, 既有盘只读)

  HK_00_base        : 不占盘 —— 直接用 GR_ZH113b.iso (见 HK_00_base.meta.json)
  HK_01_all_text_off: 回退 G1+G2+G3+G4 = 49 处「指令级文字/UI 钩子」→ 钩子全部退出
  HK_02_g1_off      : 只回退 G1 更新/重绘路径 (13 处)
  HK_03_g2_off      : 只回退 G2 测量/排版路径 (10 处)
  HK_04_g3_off      : 只回退 G3 字形取址/绘制路径 (14 处, 含 DrawString 序言拦截器)
  HK_05_g4_off      : 只回退 G4 其它 (12 处)

回退 = 把该站点区间内的字节**逐字节写回英文原盘的字节**。
因为站点区间正是「EN≠ZH 的极大连续区段」，写回 EN 字节即精确还原原盘指令流，
区间外一个字节都不动。CAVE 代码体与 ELF 内 loading 字符串**不回退**。
"""
import hashlib
import io
import json
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hk_lib as H     # noqa: E402

EN = H.elf('EN')
ZH = H.elf('ZH')
CHUNK = 1 << 22


# ------------------------------------------------------------------ 差异/站点
def byte_runs(eb, zb):
    runs = []
    i, n = 0, min(len(eb), len(zb))
    while i < n:
        if eb[i] != zb[i]:
            j = i
            while j < n and eb[j] != zb[j]:
                j += 1
            runs.append((i, j - i))
            i = j
        else:
            i += 1
    return runs


def merge(runs, gap):
    out = []
    for (o, l) in runs:
        if out and o - (out[-1][0] + out[-1][1]) <= gap:
            out[-1][1] = o + l - out[-1][0]
        else:
            out.append([o, l])
    return [(a, b) for (a, b) in out]


def groups_from_sites():
    """按符号名把站点分组 (与 hk_sites.py 口径一致)"""
    import hk_sites as S
    runs = byte_runs(EN.b, ZH.b)
    sites = merge(runs, 4)
    out = []
    for (o, l) in sites:
        va = o + H.VA2FILE
        s = EN.sym_at(va)
        g = S.group_of(s['name'] if s else '?')
        out.append(dict(file_off=o, length=l, va=va, group=g,
                        symbol=(s['name'] if s else '?'),
                        iso_off=o + H.ELF_ISO_BASE))
    return out


# ------------------------------------------------------------------ 构建
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        while True:
            b = fh.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def diff_bytes(p1, p2):
    """→ [(off, len, a_bytes, b_bytes)] 逐字节差异 (numpy 向量化)"""
    import numpy as np
    runs = []
    with open(p1, 'rb') as f1, open(p2, 'rb') as f2:
        base = 0
        while True:
            a = f1.read(CHUNK)
            b = f2.read(CHUNK)
            if not a and not b:
                break
            assert len(a) == len(b), '尺寸不同'
            x = np.frombuffer(a, dtype=np.uint8)
            y = np.frombuffer(b, dtype=np.uint8)
            ne = np.nonzero(x != y)[0]
            if ne.size:
                s = int(ne[0])
                prev = s
                for i in ne[1:]:
                    i = int(i)
                    if i != prev + 1:
                        runs.append((base + s, prev + 1 - s, a[s:prev + 1], b[s:prev + 1]))
                        s = i
                    prev = i
                runs.append((base + s, prev + 1 - s, a[s:prev + 1], b[s:prev + 1]))
            base += len(a)
    return runs


def build(name, gsel, desc, sites):
    dst = os.path.join(H.OUT, name + '.iso')
    tgt = [s for s in sites if s['group'] in gsel]
    print('--- %s : %d 站点, 组=%s' % (name, len(tgt), ','.join(sorted(gsel))))
    if os.path.exists(dst):
        print('    已存在, 删除重建')
        os.remove(dst)
    shutil.copyfile(H.BASE_ZH, dst)
    patches = []
    with open(dst, 'r+b') as f:
        for s in tgt:
            o, l = s['file_off'], s['length']
            iso = s['iso_off']
            data = bytes(EN.b[o:o + l])
            f.seek(iso)
            old = f.read(l)
            assert old == bytes(ZH.b[o:o + l]), '基底字节与 ELF 不一致 @0x%X' % o
            f.seek(iso)
            f.write(data)
            patches.append(dict(iso_off=iso, va=s['va'], file_off=o, length=l,
                                symbol=s['symbol'], group=s['group'],
                                old_hex=old.hex(' '), new_hex=data.hex(' ')))
    # 自检
    runs = diff_bytes(H.BASE_ZH, dst)
    changed = sum(r[1] for r in runs)
    expect = sum(s['length'] for s in tgt)
    allowed = set()
    for s in tgt:
        allowed.update(range(s['iso_off'], s['iso_off'] + s['length']))
    bad = []
    for (o, l, a, b) in runs:
        for k in range(l):
            if (o + k) not in allowed:
                bad.append(o + k)
            if b[k] != EN.b[o + k - H.ELF_ISO_BASE]:
                bad.append(o + k)
    elf_ok = check_elf_head(dst)
    meta = dict(
        disk=name,
        file=os.path.relpath(dst, H.REPO).replace('\\', '/'),
        size=os.path.getsize(dst),
        sha256=sha256_file(dst),
        base=os.path.relpath(H.BASE_ZH, H.REPO).replace('\\', '/'),
        base_sha256=sha256_file(H.BASE_ZH),
        base_size=os.path.getsize(H.BASE_ZH),
        description=desc,
        groups=sorted(gsel),
        n_sites=len(tgt),
        reverted_bytes=expect,
        build_cmd='python work/builds/GR_HOOK/tools/hk_build.py %s' % name,
        byte_diff_runs=[dict(iso_off=r[0], len=r[1],
                             base_hex=r[2].hex(' '), new_hex=r[3].hex(' ')) for r in runs],
        byte_diff_total=changed,
        patch_list=patches,
        selfcheck=dict(
            size_unchanged=(os.path.getsize(dst) == os.path.getsize(H.BASE_ZH)),
            diff_bytes_total=changed,
            expected_revert_bytes=expect,
            changed_outside_reverted_sites=0 if not bad else len(bad),
            every_new_byte_equals_EN=True if not bad else False,
            bad_offsets=[hex(x) for x in bad],
            elf_header_and_phdrs_unchanged=elf_ok,
        ),
    )
    with io.open(os.path.join(H.OUT, name + '.meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print('    size=%d sha256=%s' % (meta['size'], meta['sha256']))
    print('    回退站点=%d 覆盖=%d B ; 实测差异=%d B ; 越界/非EN 字节=%d'
          % (len(tgt), expect, changed, len(bad)))
    print('    ELF 头/PH 未动: %s' % elf_ok)
    return meta


def check_elf_head(path):
    """ELF 头(0..0x80) 与两个 PH 条目 (0x34..0x54) 与基底逐字节相同"""
    with open(path, 'rb') as f:
        f.seek(H.ELF_ISO_BASE)
        blob = f.read(0x80)
    return blob == bytes(ZH.b[:0x80]) and blob[:4] == b'\x7fELF'


def main():
    only = [a for a in sys.argv[1:]] or None
    sites = groups_from_sites()
    gm = {}
    for s in sites:
        gm[s['group']] = gm.get(s['group'], 0) + 1
    print('站点总数 %d, 分组 %s' % (len(sites), gm))

    # HK_00 说明 (不占盘)
    meta0 = dict(
        disk='HK_00_base', file='work/builds/GR_ZH113b/GR_ZH113b.iso',
        note='按要求省 1.6 GB: 本盘不复制, 直接用 GR_ZH113b.iso 作对照。',
        size=os.path.getsize(H.BASE_ZH), sha256=sha256_file(H.BASE_ZH),
        base='work/builds/GR_ZH113b/GR_ZH113b.iso',
    )
    with io.open(os.path.join(H.OUT, 'HK_00_base.meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta0, f, ensure_ascii=False, indent=1)

    BUILDS = [
        ('HK_01_all_text_off', {'G1', 'G2', 'G3', 'G4'},
         '回退全部 49 处「指令级文字/UI 钩子」(G1+G2+G3+G4) ⇒ 直接判定钩子是否元凶'),
        ('HK_02_g1_off', {'G1'}, '只回退 A.1 更新/重绘路径 (DrawText/SetText/Flush/Draw/'
                                 'AddOneWord/DisplayMessages/DrawNN/ReadResource/DrawTheString)'),
        ('HK_03_g2_off', {'G2'}, '只回退 A.2 测量/排版路径 (StringWidth/CharWidth/DoWordWrap/ComputeDrawXY)'),
        ('HK_04_g3_off', {'G3'}, '只回退 A.3 字形取址/绘制路径 (DrawString 全部 12 处 + DrawLetters + '
                                 'ComputeCharTextureCoords) ⇒ 同时消除 DrawString 序言拦截器的 fp ABI 违例'),
        ('HK_05_g4_off', {'G4'}, '只回退 A.4 其它 (GetUISoldierAbbreviateName/GetActorNameAbbreviated/'
                                 'kShortcutDefaultSC/SetLinearSampling/kBtnExplanationMapMax/strlwr/strupr)'),
    ]
    out = []
    for (name, gsel, desc) in BUILDS:
        if only and name not in only:
            continue
        out.append(build(name, gsel, desc, sites))
    print('OK, %d 张盘' % len(out))


if __name__ == '__main__':
    main()
