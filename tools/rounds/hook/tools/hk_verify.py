# -*- coding: utf-8 -*-
r"""hk_verify.py — 独立复核 5 张 HK 打靶盘 (只读).

对每张盘:
  1. 读 meta.json 拿 sha256 / 站点清单;
  2. 重新计算盘上 sha256 与尺寸;
  3. 逐字节与基底 GR_ZH113b.iso 对比 → 差异必须 **全部落在** meta 声明的回退区间内,
     且每个新字节必须等于英文原盘对应字节;
  4. ELF 头 (0..0x80 含 e_phoff/e_phnum) 与两个 PH 条目 (0x34..0x54) 与基底逐字节相同;
  5. 与英文原盘对比, 确认被回退区间在"新盘"上与 EN 逐字节相同;
  6. 确认区间外字节与基底相同 (即没有误伤)。
"""
import hashlib
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hk_lib as H     # noqa: E402
import numpy as np     # noqa: E402

EN_SLUS = os.path.join(H.REPO, 'third_party', 'orig', 'ps2', 'slus_out', 'SLUS_206.13')
CHUNK = 1 << 22
DISKS = ['HK_01_all_text_off', 'HK_02_g1_off', 'HK_03_g2_off',
         'HK_04_g3_off', 'HK_05_g4_off']


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        while True:
            b = fh.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def runs(p1, p2):
    out = []
    with open(p1, 'rb') as f1, open(p2, 'rb') as f2:
        base = 0
        while True:
            a = f1.read(CHUNK)
            b = f2.read(CHUNK)
            if not a and not b:
                break
            x = np.frombuffer(a, dtype=np.uint8)
            y = np.frombuffer(b, dtype=np.uint8)
            ne = np.nonzero(x != y)[0]
            if ne.size:
                s = int(ne[0])
                prev = s
                for i in ne[1:]:
                    i = int(i)
                    if i != prev + 1:
                        out.append((base + s, base + prev + 1))
                        s = i
                    prev = i
                out.append((base + s, base + prev + 1))
            base += len(a)
    return out


def main():
    en_elf = open(EN_SLUS, 'rb').read()
    base_elf = H.elf('ZH').b
    L = []
    L.append('# HK 打靶盘独立复核')
    L.append('')
    ok_all = True
    for d in DISKS:
        iso = os.path.join(H.OUT, d + '.iso')
        meta = json.load(io.open(os.path.join(H.OUT, d + '.meta.json'), encoding='utf-8'))
        L.append('## %s' % d)
        L.append('')
        res = {}
        res['exists'] = os.path.exists(iso)
        res['size'] = os.path.getsize(iso) if res['exists'] else 0
        res['size_ok'] = res['size'] == meta['size'] == os.path.getsize(H.BASE_ZH)
        res['sha256'] = sha256_file(iso) if res['exists'] else ''
        res['sha256_ok'] = res['sha256'] == meta['sha256']
        # 差异区间
        rr = runs(H.BASE_ZH, iso)
        allowed = set()
        for s in meta['patch_list']:
            allowed.update(range(s['iso_off'], s['iso_off'] + s['length']))
        outside = sum(1 for (a, b) in rr for k in range(a, b) if k not in allowed)
        res['diff_runs'] = len(rr)
        res['diff_bytes'] = sum(b - a for (a, b) in rr)
        res['outside_reverted_sites'] = outside
        # 每个新字节 == EN
        bad_en = 0
        with open(iso, 'rb') as f:
            for (a, b) in rr:
                f.seek(a)
                got = f.read(b - a)
                for k in range(len(got)):
                    iso_off = a + k
                    eo = iso_off - H.ELF_ISO_BASE
                    if eo < 0 or eo >= len(en_elf) or got[k] != en_elf[eo]:
                        bad_en += 1
        res['new_bytes_not_equal_EN'] = bad_en
        # 被回退区间 vs EN
        mism = 0
        with open(iso, 'rb') as f:
            for s in meta['patch_list']:
                o, l = s['file_off'], s['length']
                f.seek(s['iso_off'])
                got = f.read(l)
                if got != en_elf[o:o + l]:
                    mism += 1
        res['reverted_spans_neq_EN'] = mism
        # ELF 头 / PH
        with open(iso, 'rb') as f:
            f.seek(H.ELF_ISO_BASE)
            head = f.read(0x80)
        res['elf_head_ok'] = (head == base_elf[:0x80] and head[:4] == b'\x7fELF')
        (etype, machine, ver, entry, phoff, shoff, flags, ehsize, phentsize,
         phnum, shentsize, shnum, shstrndx) = struct.unpack_from('<HHIIIIIHHHHHH', head, 16)
        res['elf'] = dict(e_type=etype, e_machine=machine, e_entry=hex(entry),
                          e_phoff=hex(phoff), e_phnum=phnum, e_shnum=shnum)
        note = meta['description']
        L.append('* 尺寸 %s (%d) — %s' % (res['size'], res['size'], 'OK' if res['size_ok'] else '✗'))
        L.append('* sha256 `%s` — %s' % (res['sha256'], 'OK' if res['sha256_ok'] else '✗'))
        L.append('* 与基底差异 run=%d / %d B' % (res['diff_runs'], res['diff_bytes']))
        L.append('* 落在声明回退区间**外**的差异字节 = **%d** (应为 0)' % outside)
        L.append('* 新字节 ≠ 英文原盘字节 的个数 = **%d** (应为 0)' % bad_en)
        L.append('* 回退区间与英文原盘不一致的站点数 = **%d** (应为 0)' % mism)
        L.append('* ELF 头 + PH 未动 = %s (e_type=%d e_machine=%d e_phnum=%d)'
                 % (res['elf_head_ok'], etype, machine, phnum))
        L.append('* 站点数 %d ; 组 %s ; 回退字节 %d'
                 % (meta['n_sites'], ','.join(meta['groups']), meta['reverted_bytes']))
        L.append('* 说明: %s' % note)
        good = (res['size_ok'] and res['sha256_ok'] and outside == 0 and bad_en == 0
                and mism == 0 and res['elf_head_ok'])
        ok_all = ok_all and good
        L.append('* **判定: %s**' % ('✅ 全部自检通过' if good else '❌ 有未通过项'))
        L.append('')
    # HK_00
    m0 = json.load(io.open(os.path.join(H.OUT, 'HK_00_base.meta.json'), encoding='utf-8'))
    L.append('## HK_00_base (不占盘)')
    L.append('')
    L.append('* 指路 `%s` (尺寸 %d, sha256 `%s`)'
             % (m0['file'], m0['size'], m0['sha256']))
    L.append('* 实测基底 sha256 = `%s` — %s'
             % (sha256_file(H.BASE_ZH),
                'OK' if sha256_file(H.BASE_ZH) == m0['sha256'] else '✗'))
    L.append('')
    L.append('**总判定: %s**' % ('✅ 5 张盘全部自检通过' if ok_all else '❌ 存在未通过项'))
    txt = '\n'.join(L)
    with io.open(os.path.join(H.EVID, 'hk_verify.md'), 'w', encoding='utf-8') as f:
        f.write(txt)
    print(txt)


if __name__ == '__main__':
    main()
