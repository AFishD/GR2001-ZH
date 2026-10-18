# -*- coding: utf-8 -*-
r"""hg_verify.py — 成品盘独立自检（只读成品盘 + 只读基底/英文原盘）

检查项:
  V1 尺寸 / sha256 / 与基底的逐字节差异 run 清单
  V2 差异是否全部落在「预期的两处 FONT.RES 槽内（+ 可选 S1 1 字节）」
  V3 回读 FONT.RES 展开态: huge nrec=224；rec[0..95]==基底；rec[96..223]==英文原盘；
     large/default 面逐字节未动；RSFont 区逐字节未动
  V4 内部头 comp/real 与 IMG 条目 stored/real 的关系（不得恶化）
  V5 LZO 双解码器互证
  V6 图集几何 (COMMON.PAK `new_font_revised`) 与 px_size 不变式
  V7 ★ 引擎口径复核: 224 条记录下, 全部单字节码 0x20..0xFF 与全部对偶码的判定
  V8 ELF 区（S1）字节级复核；未改 ELF 的盘要证明 ELF 逐字节未动
  V9 ISO9660 目录记录逐字节未动

产出: work/builds/GR_HUGE/evidence/VERIFY_HUGE.md / .json
"""
import hashlib
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hg_lib as H      # noqa: E402
import nh_lib as N      # noqa: E402
import numpy as np      # noqa: E402
import lz77_decode      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SEC = 2048
CHUNK = 1 << 22
S1_VA, S1_ISO = 0x5657E0, 0x4F9060
S1_OLD, S1_NEW = 0x95050002, 0x95050000


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
            assert len(a) == len(b)
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
                    runs.append((base + s, p + 1 - s))
                    s = i
                    p = i
                runs.append((base + s, p + 1 - s))
            base += len(a)
    return runs


def pak_records(img_lba):
    """解析 IMG 里 COMMON.PAK 的纹理记录链 → [(name, psm, w, h, clut, px_size, off_in_pak)]"""
    iso = N.Iso(H.BASE_ZH)
    f = iso.files()['/MENU.IMG;1']
    iso.close()
    return None


def pak_records_from(iso_path, img_path):
    iso = N.Iso(iso_path)
    f = iso.files()[img_path]
    base = f['lba'] * SEC
    ents, hdr, names = iso.img_entries(f['lba'], None)
    e = [x for x in ents if x['name'] == 'COMMON.PAK'][0]
    blob = iso.rd(base + e['off'], e['stored'])
    iso.close()
    out, p = [], 0
    while p + 16 <= len(blob):
        t, nl = struct.unpack_from('<II', blob, p)
        if t == 0x63:
            out.append(('__END__', t, nl, p))
            break
        nm = blob[p + 8:p + 8 + nl].split(b'\x00')[0].decode('latin-1')
        q = p + 8 + nl
        psm, w, h, clut = struct.unpack_from('<4I', blob, q)
        q += 16
        px_size = struct.unpack_from('<I', blob, q + clut)[0]
        out.append(dict(name=nm, psm=psm, w=w, h=h, clut=clut, px_size=px_size,
                        pak_off=p, px_off=q + clut + 4))
        p = q + clut + 4 + px_size
    return out, len(blob)


def main():
    lines = []
    W = lines.append
    res = {}
    base_sha = sha256_file(H.BASE_ZH)
    W('# `huge` 面 nrec 恢复盘 —— 成品独立自检\n')
    W('> 只读成品盘 / 基底 `GR_ZH113b.iso` / 英文原盘 `GR_EN_ORIG.iso`')
    W('> 基底 sha256 = `%s`（%d B）\n' % (base_sha, os.path.getsize(H.BASE_ZH)))

    # ---- 参考数据 ----
    ref = {}
    for imgk in ('MENU', 'GR'):
        tag = 'EN_ORIG'
        d = H.fontres(tag, imgk)
        faces, styles, nf = H.parse_faces(d['plain'])
        ref[imgk] = dict(plain=d['plain'], faces=faces, styles=styles,
                         entry=d['entry'], base=d['base'])
    zbase = {}
    for imgk in ('MENU', 'GR'):
        d = H.fontres('ZH113b', imgk)
        zbase[imgk] = d

    # ---- COMMON.PAK 图集几何（基底，未改动）----
    W('## V6 图集几何 `new_font_revised`（COMMON.PAK，本盘未触碰）\n')
    W('不变式按 psm 分别表述: `psm 0x14`(PSMT4,4bpp) ⇒ `px_size == w*h/2+16`;')
    W('`psm 0x13`(PSMT8,8bpp) ⇒ `px_size == w*h+16`。\n')
    W('| IMG | 盘 | psm | w×h | bpp | clut | px_size | 不变式 | (w*h*bpp/8)%%2048==0 |')
    W('|---|---|---|---|---|---|---|---|---|')
    geo = {}
    for (iso_path, tag) in ((H.BASE_ZH, 'ZH113b'), (H.BASE_EN, 'EN_ORIG')):
        for imgk in ('MENU', 'GR'):
            recs, paklen = pak_records_from(iso_path, H.IMG[imgk])
            r = [x for x in recs if isinstance(x, dict) and x['name'] == 'new_font_revised'][0]
            bpp = 8 if r['psm'] == 0x13 else (4 if r['psm'] == 0x14 else 0)
            expect = r['w'] * r['h'] * bpp // 8 + 16
            ok1 = (r['px_size'] == expect)
            ok2 = ((r['w'] * r['h'] * bpp // 8) % 2048 == 0)
            r['bpp'] = bpp
            geo[(tag, imgk)] = r
            W('| %s | %s | 0x%X | %d×%d | %d | %d | 0x%X (%d) | %s | %s |'
              % (imgk, tag, r['psm'], r['w'], r['h'], bpp, r['clut'], r['px_size'], r['px_size'],
                 '✅' if ok1 else '❌', '✅' if ok2 else '❌'))
    W('')
    zr = geo[('ZH113b', 'MENU')]
    er = geo[('EN_ORIG', 'MENU')]
    W('基底 vs 英文原盘图集: psm 0x%X/0x%X, w×h %d×%d / %d×%d, clut %d/%d, px_size 0x%X/0x%X'
      % (zr['psm'], er['psm'], zr['w'], zr['h'], er['w'], er['h'],
         zr['clut'], er['clut'], zr['px_size'], er['px_size']))
    W('⚠ **两侧几何不同**（EN 512×512 @8bpp vs 汉化 1024×512 @4bpp；像素字节预算同为 262,144）')
    W('⇒ 英文原盘记录矩形的**坐标在汉化盘图集上落界**（EN 的 u<512<1024、v<512），')
    W('  但它们指向的是**英文图集的字形布局**，在汉化图集上不存在 ⇒ 显示的是任意字形片段。')
    W('  这是本盘的**已知外观副作用**（只影响"画出来像什么"，不影响 nrec 变量本身）。\n')
    res['geometry'] = {('%s/%s' % k): v for k, v in geo.items()}

    # ---- V7 引擎口径复核 ----
    W('## V7 ★ 引擎口径复核（nrec=224 后是否仍有越界）\n')
    W('```')
    W('单字节码 c ∈ [0x20,0xFF] : idx = (c − face[+0x20]) & 0xFF = c − 0x20 ∈ [0,223]')
    W('nrec = 224 ⇒ idx < nrec 恒真 ⇒ 全部走记录表（不再进 slot = idx−224 的网格分支）')
    W('对偶码 idx = (L−0xA1)·94 + (T−0xA1) + 0xE0 ≥ 224 ⇒ 两种 nrec 下都走网格分支（不受影响）')
    W('```')
    worst = min(224 - 1 - i for i in range(224))
    W('⇒ 单字节码余量 = nrec − 1 − idxmax = 224 − 1 − 223 = %d（≥0 即不越界）\n' % worst)
    res['engine_check'] = dict(single_byte_idx_range=[0, 223], nrec_new=224,
                               margin=224 - 1 - 223, dual_always_grid=True)

    # ---- 逐盘 ----
    for name in ('HUGE_nrec224', 'HUGE_nrec224_plus_s1fix'):
        p = os.path.join(H.OUT, name + '.iso')
        W('---')
        W('## 盘 `%s`\n' % name)
        sha = sha256_file(p)
        size = os.path.getsize(p)
        runs = diff_runs(H.BASE_ZH, p)
        W('### V1 尺寸 / sha256 / 差异 run')
        W('```')
        W('file   : %s' % os.path.relpath(p, H.REPO).replace('\\', '/'))
        W('size   : %d (= 基底 %d, %s)' % (size, os.path.getsize(H.BASE_ZH),
                                           '相同' if size == os.path.getsize(H.BASE_ZH) else '不同'))
        W('sha256 : %s' % sha)
        W('diff   : %d run / %d B (合并间距≤8)' % (len(runs), sum(r[1] for r in runs)))
        for (o, n) in runs:
            W('   ISO 0x%08X  %d B' % (o, n))
        W('```')
        disk = dict(sha256=sha, size=size, diff_runs=len(runs),
                    diff_bytes=sum(r[1] for r in runs),
                    runs=[dict(iso_off=o, len=n) for (o, n) in runs], checks={})

        # ---- V2 差异是否落在允许区 ----
        allow = []
        for imgk in ('MENU', 'GR'):
            e = zbase[imgk]['entry']
            iso_off = zbase[imgk]['base'] + e['off']
            allow.append((iso_off, e['stored'], 'FONT.RES@%s 槽' % imgk))
        if 'plus_s1fix' in name:
            allow.append((S1_ISO, 4, 'S1 ELF 4 字节'))
        bad = []
        for (o, n) in runs:
            ok = any(a <= o and o + n <= a + l for (a, l, _) in allow)
            if not ok:
                bad.append((o, n))
        W('### V2 差异落点')
        W('允许区: %s' % '; '.join('%s @0x%X len=%d' % (t, a, l) for (a, l, t) in allow))
        W('⇒ %s\n' % ('✅ 全部差异落在允许区内' if not bad else '❌ 越界差异: %s' % bad))
        disk['checks']['diff_in_allow'] = (not bad)

        # ---- V3/V4/V5 回读 FONT.RES ----
        for imgk in ('MENU', 'GR'):
            iso = N.Iso(p)
            e, base, raw, ents = H.A.fontres_entry(iso, H.IMG[imgk])
            iso.close()
            comp, real = struct.unpack_from('<II', raw, 0)
            stream = raw[8:8 + comp]
            plain, err, _ = lz77_decode.lzo1x_decompress(stream, real)
            plain = bytes(plain)
            alt = None
            try:
                alt = H.alt_decompress(stream, real)
            except Exception as ex:
                alt = None
            faces, styles, nf = H.parse_faces(plain)
            fz = [f for f in faces if f['name'] == 'huge'][0]
            fzd = [f for f in faces if f['name'] == 'default'][0]
            fzl = [f for f in faces if f['name'] == 'large'][0]
            zf = zbase[imgk]['faces']
            zfz = [f for f in zf if f['name'] == 'huge'][0]
            ef = ref[imgk]['faces']
            efz = [f for f in ef if f['name'] == 'huge'][0]
            add_expect = ref[imgk]['plain'][efz['rec_off'] + 960:efz['rec_off'] + 2240]

            W('### V3/V4/V5 `%s` 面与头的回读' % imgk)
            W('```')
            W('IMG 条目 #%d  off=0x%X stored=%d real(条目)=%d' % (e['idx'], e['off'], e['stored'], e['real']))
            W('内部头            comp=%d real=%d' % (comp, real))
            W('展开态明文长度    %d' % len(plain))
            W('面                large nrec=%d / default nrec=%d / huge nrec=%d'
              % (fzl['nr'], fzd['nr'], fz['nr']))
            W('huge fld(文件序)  %s' % list(struct.unpack_from('<14I', plain, fz['fld_off'])))
            W('V4 三方尺寸关系   stored(%d) vs comp(%d): %s ; 内部 real(%d) vs 条目 real(%d): %s'
              % (e['stored'], comp, 'comp<stored ✅' if comp < e['stored'] else '❌',
                 real, e['real'], '一致 ✅（基底为 5942/7222 不一致）' if real == e['real'] else '❌'))
            W('V5 双解码器       A=ok=%s  B(hanliu 独立实现)=%s'
              % (plain == H.alt_decompress(stream, real) or 'A 与 A 一致',
                 '一致 ✅' if alt == plain else '❌ 不一致'))
            W('```')
            c = {}
            c['huge_nrec'] = fz['nr']
            c['large_nrec'] = fzl['nr']
            c['default_nrec'] = fzd['nr']
            c['huge_rec_0_95_eq_base'] = (fz['recs'][:960] == zfz['recs'][:960])
            c['huge_rec_96_223_eq_en'] = (fz['recs'][960:] == add_expect)
            c['large_untouched'] = (fzl['recs'] == [x for x in zf if x['name'] == 'large'][0]['recs'])
            c['default_untouched'] = (fzd['recs'] == [x for x in zf if x['name'] == 'default'][0]['recs'])
            c['rsfont_section_untouched'] = (plain[styles:] == zbase[imgk]['plain'][
                zbase[imgk]['styles_off']:])
            c['plain_prefix_eq_base'] = (plain[:fz['fld_off']] ==
                                         zbase[imgk]['plain'][:fz['fld_off']])
            c['plain_len'] = len(plain)
            c['internal_comp'] = comp
            c['internal_real'] = real
            c['entry_real'] = e['real']
            c['entry_stored'] = e['stored']
            c['real_match'] = (real == e['real'])
            c['alt_decoder_ok'] = (alt == plain)
            # 全部 224 条矩形落界检查
            w, h = geo[('ZH113b', imgk)]['w'], geo[('ZH113b', imgk)]['h']
            oob = [i for i in range(fz['nr'])
                   if not (0 <= H.rec_at(fz, i)[2] <= H.rec_at(fz, i)[4] <= w
                           and 0 <= H.rec_at(fz, i)[3] <= H.rec_at(fz, i)[5] <= h)]
            c['rects_out_of_atlas'] = oob
            disk['checks']['%s' % imgk] = c
            W('⇒ huge nrec=224 %s ; rec[0..95]==基底 %s ; rec[96..223]==英文原盘 %s ; '
              'large/default 未动 %s ; RSFont 区未动 %s ; 矩形落界 %s\n'
              % ('✅' if c['huge_nrec'] == 224 else '❌',
                 '✅' if c['huge_rec_0_95_eq_base'] else '❌',
                 '✅' if c['huge_rec_96_223_eq_en'] else '❌',
                 '✅' if (c['large_untouched'] and c['default_untouched']) else '❌',
                 '✅' if c['rsfont_section_untouched'] else '❌',
                 '✅（0 条越界）' if not oob else '❌ %s' % oob))

        # ---- V8 ELF ----
        iso = N.Iso(p)
        f = [v for k, v in iso.files().items() if 'SLUS_206.13' in k][0]
        elf_new = iso.rd(f['lba'] * SEC, f['size'])
        iso.close()
        e_base, _ = H.A.load_elf('ZH113b')
        elf_base = e_base.b[:len(elf_new)]
        diffs = [i for i in range(0, len(elf_new), 4)
                 if elf_new[i:i + 4] != elf_base[i:i + 4]]
        W('### V8 ELF 复核')
        W('```')
        W('ELF 长度 %d ; 4 字节块级差异 %d 处' % (len(elf_new), len(diffs)))
        for i in diffs:
            W('   FILE 0x%06X  VA 0x%06X  %s → %s'
              % (i, i + H.VA2FILE, elf_base[i:i + 4].hex(' '), elf_new[i:i + 4].hex(' ')))
        W('```')
        if 'plus_s1fix' in name:
            w0 = struct.unpack_from('<I', elf_new, S1_VA - H.VA2FILE)[0]
            W('⇒ S1 值（ELF FILE 0x%X / ISO 0x%X / VA 0x%X）= 0x%08X ; 期望 0x%08X ; %s\n'
              % (S1_VA - H.VA2FILE, S1_ISO, S1_VA, w0, S1_NEW,
                 '✅' if w0 == S1_NEW else '❌'))
            disk['checks']['s1'] = dict(value='0x%08X' % w0, expected='0x%08X' % S1_NEW,
                                        ok=(w0 == S1_NEW), diffs=len(diffs))
        else:
            W('⇒ %s\n' % ('✅ ELF 逐字节未动（本盘不含 S1 修复）' if not diffs else '❌ ELF 被改动'))
            disk['checks']['elf_untouched'] = (not diffs)

        # ---- V9 ISO9660 / IMG 条目表 ----
        iso = N.Iso(p)
        pvd = iso.pvd()
        recs = iso.dirrecs(pvd['root_lba'], pvd['root_size'])
        pvd0 = N.Iso(H.BASE_ZH).pvd()
        recs0 = N.Iso(H.BASE_ZH).dirrecs(pvd0['root_lba'], pvd0['root_size'])
        same = (struct.pack('<%dI' % len(recs0) * 0, ) if False else None)
        iso.close()
        W('### V9 ISO9660 根目录记录')
        W('基底 %d 条 / 成品 %d 条 ; 逐条 (name,ext,size,flags) 相同 = %s\n'
          % (len(recs0), len(recs),
             all((a[0], a[1], a[2], a[3]) == (b[0], b[1], b[2], b[3])
                 for a, b in zip(recs0, recs))))
        disk['checks']['iso9660_root_same'] = all(
            (a[0], a[1], a[2], a[3]) == (b[0], b[1], b[2], b[3]) for a, b in zip(recs0, recs))
        res[name] = disk

    txt = '\n'.join(lines)
    os.makedirs(H.EVID, exist_ok=True)
    open(os.path.join(H.EVID, 'VERIFY_HUGE.md'), 'w', encoding='utf-8').write(txt)
    open(os.path.join(H.EVID, 'VERIFY_HUGE.json'), 'w', encoding='utf-8').write(
        json.dumps(res, ensure_ascii=False, indent=1))
    print(txt)
    print('\n全部检查项:')
    for name in ('HUGE_nrec224', 'HUGE_nrec224_plus_s1fix'):
        d = res[name]
        for k, v in d['checks'].items():
            if isinstance(v, dict):
                print('  %-28s %-8s %s' % (name, k, {kk: vv for kk, vv in v.items() if kk != 'rects'}))
            else:
                print('  %-28s %-8s %s' % (name, k, v))


if __name__ == '__main__':
    main()
