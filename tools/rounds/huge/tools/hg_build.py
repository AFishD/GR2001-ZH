# -*- coding: utf-8 -*-
r"""hg_build.py — 构建 `huge` 面 nrec 恢复打靶盘（源盘全部只读）

产物（写 work/builds/GR_HUGE/**）:
  HUGE_nrec224.iso            : FONT.RES(MENU #4 + GR #906) 的 `huge` 面 nrec 96→224，
                                新增 128 条记录逐条取自英文原盘（EN_ORIG.iso 同位置）
  HUGE_nrec224_plus_s1fix.iso : 同上 + S1 单字节修复 (VA 0x5657E0 / ISO 0x4F9060
                                `lhu a1,2(t0)` → `lhu a1,0(t0)`)

改动口径（为何不是"1 字节"）见 evidence/HUGE_BUILD_REPORT.md §2：
  huge 面 nrec = 文件序 u32#4 × u32#5；把 #5 由 6 改成 14 ⇒ nrec=224
  ⇒ 记录表必须真的多出 128 条 (=1,280 B) ⇒ 展开态明文 5,942 → 7,222 B
  ⇒ 内部头 `real` 只能写 7,222（= IMG 条目 real，= 明文实际长度）
"""
import hashlib
import json
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hg_lib as H      # noqa: E402
import lzo1x_c          # noqa: E402
import lz77_decode      # noqa: E402
import numpy as np      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

OUTD = H.OUT
SEC = H.SEC
CHUNK = 1 << 22
CHECK_ONLY = False      # --check: 跑完全部断言但不写盘（用于验证 --planB 等分支）

# FONT.RES 展开态里 `huge` 面的位置（EN 与 ZH 相同：三面顺序 large/default/huge）
HUGE_FLD_OFF = 0x1228          # 面描述块起始（14×u32）
HUGE_NREC_SER = 5              # 文件序 u32#5 = fld[1] = nrec 的第二个乘数
HUGE_REC_OFF = 0x1260          # huge 记录表起始
HUGE_NREC_OLD = 96
HUGE_NREC_NEW = 224
EN_HUGE_SER5 = 14

S1_VA = 0x5657E0
S1_ISO = S1_VA - H.VA2ISO      # 0x4F9060
S1_OLD = 0x95050002            # lhu a1,2(t0)
S1_NEW = 0x95050000            # lhu a1,0(t0)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        while True:
            b = fh.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def diff_runs(p1, p2, gap=8):
    runs = []
    with open(p1, 'rb') as f1, open(p2, 'rb') as f2:
        base = 0
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
                s = int(ne[0])
                p = s
                for i in ne[1:]:
                    i = int(i)
                    if i - p <= gap:
                        p = i
                        continue
                    runs.append((base + s, p + 1 - s, bytes(x[s:p + 1]), bytes(y[s:p + 1])))
                    s = i
                    p = i
                runs.append((base + s, p + 1 - s, bytes(x[s:p + 1]), bytes(y[s:p + 1])))
            base += len(a)
    return runs


def load_fontres(iso_path, img_path):
    import nh_lib as N
    iso = N.Iso(iso_path)
    e, base, raw, ents = H.A.fontres_entry(iso, img_path)
    plain, comp, real, se = H.A.decompress_fontres(raw)
    iso.close()
    return e, base, raw, plain, comp, real


def build(name, with_s1, plan_b=False):
    dst = os.path.join(OUTD, name + '.iso')
    if not CHECK_ONLY:
        shutil.copyfile(H.BASE_ZH, dst)
    changes = []

    # ---------------- FONT.RES: MENU #4 与 GR #906 ----------------
    en_fonts = {}
    for imgk in ('MENU', 'GR'):
        e, base, raw, plain, comp, real = load_fontres(H.BASE_EN, H.IMG[imgk])
        faces, styles_off, nf = H.parse_faces(plain)
        en_fonts[imgk] = dict(e=e, base=base, plain=plain, faces=faces, styles=styles_off)
    for imgk in ('MENU', 'GR'):
        e, base, raw, plain, comp, real = load_fontres(H.BASE_ZH, H.IMG[imgk])
        faces, styles_off, nf = H.parse_faces(plain)
        assert nf == 3, '面数 %d' % nf
        fz = [f for f in faces if f['name'] == 'huge'][0]
        assert fz['rec_off'] == HUGE_REC_OFF and fz['fld_off'] == HUGE_FLD_OFF, \
            'huge 面位置变了: fld_off=0x%X rec_off=0x%X' % (fz['fld_off'], fz['rec_off'])
        assert fz['nr'] == HUGE_NREC_OLD, 'huge nrec=%d 期望 %d' % (fz['nr'], HUGE_NREC_OLD)
        assert real == 5942 and len(plain) == 5942, 'real=%d len=%d' % (real, len(plain))
        assert comp == (1489 if imgk == 'MENU' else 1332), 'comp=%d' % comp

        # --- 英文原盘同位置记录（逐条取回）---
        ef = en_fonts[imgk]
        fze = [f for f in ef['faces'] if f['name'] == 'huge'][0]
        assert fze['nr'] == 224, 'EN huge nrec=%d' % fze['nr']
        assert ef['plain'][HUGE_FLD_OFF:HUGE_FLD_OFF + 56] is not None
        en_ser = list(struct.unpack_from('<14I', ef['plain'], HUGE_FLD_OFF))
        zh_ser = list(struct.unpack_from('<14I', plain, HUGE_FLD_OFF))
        assert en_ser[HUGE_NREC_SER] == EN_HUGE_SER5, 'EN ser[5]=%d' % en_ser[HUGE_NREC_SER]
        assert zh_ser[HUGE_NREC_SER] == 6, 'ZH ser[5]=%d' % zh_ser[HUGE_NREC_SER]
        assert zh_ser[4] == 16 and en_ser[4] == 16, 'ser[4] %d/%d' % (zh_ser[4], en_ser[4])
        add = ef['plain'][fze['rec_off'] + 96 * 10:fze['rec_off'] + 224 * 10]
        assert len(add) == 128 * 10 == 1280
        take_from = 0x1620       # = 0x1260 + 96*10，英文原盘 huge 记录表里的第 96 条
        add_src = ('英文原盘 EN_ORIG.iso / %s.IMG 条目 #%d FONT.RES 展开态 `huge` 面 rec[96..223]'
                   % (imgk, ef['e']['idx']))
        add_iso_off = ef['base'] + ef['e']['off'] + 8 + fze['rec_off'] + 96 * 10
        if plan_b:
            fzd = [f for f in faces if f['name'] == 'default'][0]
            add = fzd['recs'][960:2240]
            assert len(add) == 1280
            add_src = ('基底 GR_ZH113b.iso / %s.IMG 条目 #%d FONT.RES 展开态 `default` 面 '
                       'rec[96..223]（方案 B：huge ≡ default）' % (imgk, e['idx']))
            add_iso_off = base + e['off'] + 8 + fzd['rec_off'] + 960

        # --- 组装新明文 ---
        newplain = bytearray(plain)
        # (1) nrec 乘数 6 -> 14
        struct.pack_into('<I', newplain, HUGE_FLD_OFF + 4 * HUGE_NREC_SER, EN_HUGE_SER5)
        # (2) 插入 128 条记录（位置 = 记录表第 96 条处，即 styles/RSFont 区之前）
        ins = HUGE_REC_OFF + 96 * 10
        newplain[ins:ins] = add
        assert len(newplain) == 7222, len(newplain)
        # 前缀应逐字节等于基底（唯一例外 = 我们有意改的那 4 字节 nrec 乘数）
        fld_at = HUGE_FLD_OFF + 4 * HUGE_NREC_SER
        assert bytes(newplain[:fld_at]) == plain[:fld_at], '前缀(≤fld)被改动'
        assert bytes(newplain[fld_at + 4:ins]) == plain[fld_at + 4:ins], '前缀(fld 之后)被改动'
        assert struct.unpack_from('<I', newplain, fld_at)[0] == EN_HUGE_SER5
        assert bytes(newplain[ins + 1280:]) == plain[ins:], '后缀被改动'

        # --- 不变式: 新 huge 记录 96..223 与英文原盘逐条相同 ---
        fs2, styles2, nf2 = H.parse_faces(bytes(newplain))
        fz2 = [f for f in fs2 if f['name'] == 'huge'][0]
        assert fz2['nr'] == 224, fz2['nr']
        assert fz2['recs'][960:] == add, '记录 96..223 与取回字节不一致'
        for i in range(96):
            assert H.rec_at(fz2, i) == H.rec_at(fz, i), '记录 %d 被改动' % i
        # 其它两面未动
        for nm in ('large', 'default'):
            a = [x for x in faces if x['name'] == nm][0]
            b = [x for x in fs2 if x['name'] == nm][0]
            assert a['recs'] == b['recs'] and a['fld'] == b['fld'], '%s 面被改动' % nm
            assert a['fld_off'] == b['fld_off'] and a['rec_off'] == b['rec_off']
        # RSFont 区（含 nFonts=8 与 8 个 RSFont）逐字节未动
        assert styles2 == styles_off + 1280, (styles2, styles_off)
        assert bytes(newplain[styles2:]) == plain[styles_off:], 'RSFont 区被改动'

        # --- 重压 ---
        stream = lzo1x_c.compress(bytes(newplain))
        dd, err, _ = lz77_decode.lzo1x_decompress(stream, 7222)
        assert dd == bytes(newplain), 'LZO 自检(解码器 A = tools/gr_tools)失败 %s' % imgk
        dd2 = H.alt_decompress(stream, 7222)
        assert dd2 == bytes(newplain), 'LZO 自检(解码器 B = tools/hanliu)失败 %s' % imgk
        decoders = 'tools/gr_tools/lz77_decode + tools/hanliu/tools/lz77_decode (两个不同实现)'
        assert len(stream) <= e['stored'] - 8, '压缩流 %d > 槽余量 %d' % (len(stream), e['stored'] - 8)

        blob = struct.pack('<II', len(stream), 7222) + stream
        blob = blob + b'\x00' * (e['stored'] - len(blob))
        assert len(blob) == e['stored']

        iso_off = base + e['off']
        if not CHECK_ONLY:
            with open(dst, 'r+b') as fh:
                fh.seek(iso_off)
                old = fh.read(len(blob))
                fh.seek(iso_off)
                fh.write(blob)
        changes.append(dict(
            img=imgk, entry_idx=e['idx'], iso_off=iso_off,
            stored=e['stored'], off=e['off'],
            old_comp=comp, old_real=real,
            new_comp=len(stream), new_real=7222, new_plain=len(newplain),
            take_src=add_src,
            take_from_en_iso_off=add_iso_off,
            take_from_en_plain_off=take_from,
            take_from_len=1280,
            take_bytes_sha256=hashlib.sha256(add).hexdigest(),
            take_first32=add[:32].hex(' '), take_last32=add[-32:].hex(' '),
            note=('FONT.RES@%s: huge 面 nrec 96→224（文件序 u32#5 6→14）+ 从英文原盘逐条取回 '
                  'rec[96..223]（1,280 B）; 内部头 comp %d→%d, real 5942→7222' %
                  (imgk, comp, len(stream)))))

    # ---------------- 可选 S1 修复 ----------------
    if with_s1:
        with open(H.BASE_ZH, 'rb') as fh:          # 期望值只从**基底**读（成品盘还没写）
            fh.seek(S1_ISO)
            old = struct.unpack('<I', fh.read(4))[0]
        assert old == S1_OLD, 'S1 期望 0x%08X 实得 0x%08X' % (S1_OLD, old)
        if not CHECK_ONLY:
            with open(dst, 'r+b') as fh:
                fh.seek(S1_ISO)
                fh.write(struct.pack('<I', S1_NEW))
            with open(dst, 'rb') as fh:
                fh.seek(S1_ISO)
                got = struct.unpack('<I', fh.read(4))[0]
            assert got == S1_NEW
        changes.append(dict(kind='ELF', va='0x%X' % S1_VA, iso_off=S1_ISO,
                            old='0x%08X' % S1_OLD, new='0x%08X' % S1_NEW,
                            note='S1: GetActorNameAbbreviated cave `lhu a1,2(t0)` → `lhu a1,0(t0)`'
                                 '（对象布局 {u16 len @+0, char* data @+4}）'))

    if CHECK_ONLY:
        print('[check] %-30s planB=%-5s s1=%-5s 全部断言通过；未写盘' % (name, plan_b, with_s1))
        for c in changes:
            if 'img' in c:
                print('        %-4s comp %d→%d ; real %d→7222 ; 前缀+后缀逐字节未变 ; '
                      '取回块 sha256=%s' % (c['img'], c['old_comp'], c['new_comp'],
                                          c['old_real'], c['take_bytes_sha256']))
        return dict(disk=name, check_only=True, patch_list=changes)

    size = os.path.getsize(dst)
    runs = diff_runs(H.BASE_ZH, dst)
    meta = dict(
        disk=name, file=os.path.relpath(dst, H.REPO).replace('\\', '/'),
        size=size, sha256=sha256_file(dst),
        base=os.path.relpath(H.BASE_ZH, H.REPO).replace('\\', '/'),
        base_sha256=sha256_file(H.BASE_ZH), base_size=os.path.getsize(H.BASE_ZH),
        en_ref=os.path.relpath(H.BASE_EN, H.REPO).replace('\\', '/'),
        en_ref_sha256=sha256_file(H.BASE_EN),
        build_cmd=('python work/builds/GR_HUGE/tools/hg_build.py %s%s'
                   % ('' if not plan_b else '--planB ', name)),
        record_source=('方案B: 基底 `default` 面 rec[96..223]（huge ≡ default）' if plan_b
                       else '英文原盘 `huge` 面 rec[96..223]（逐条取回）'),
        single_variable_note=('本盘唯一的"逻辑"变量 = `huge` 面记录表恢复成英文原盘形态'
                              '(nrec 96→224)。随之必然发生：展开态明文 5,942→7,222 B、'
                              '内部头 real 5,942→7,222（= IMG 条目 real，= 明文实际长度）、'
                              'comp 因重压而改变。这三项都不可分离：nrec 变了就必须有 224 条记录，'
                              '有记录就必须声明真实长度。'),
        patch_list=changes,
        byte_diff_runs=[dict(iso_off=r[0], len=r[1], from_hex=r[2].hex(' '),
                             to_hex=r[3].hex(' ')) for r in runs],
        byte_diff_total=sum(r[1] for r in runs),
        elf_untouched=(not with_s1),
    )
    with open(os.path.join(OUTD, name + '.meta.json'), 'w', encoding='utf-8') as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print('%-30s size=%d' % (name, size))
    print('   sha256 = %s' % meta['sha256'])
    print('   diff runs=%d  bytes=%d' % (len(runs), meta['byte_diff_total']))
    for r in runs:
        print('     ISO 0x%08X (%d B)' % (r[0], r[1]))
    return meta


def main():
    argv = sys.argv[1:]
    global CHECK_ONLY
    plan_b = '--planB' in argv
    CHECK_ONLY = '--check' in argv
    only = [a for a in argv if not a.startswith('--')] or None
    suffix = '_planB' if plan_b else ''
    todo = [('HUGE_nrec224' + suffix, False), ('HUGE_nrec224_plus_s1fix' + suffix, True)]
    for (n, s1) in todo:
        if only and n not in only:
            continue
        build(n, s1, plan_b=plan_b)


if __name__ == '__main__':
    main()
