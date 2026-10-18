# -*- coding: utf-8 -*-
r"""font_face_audit.py — 只读审计: 每个 face 的 nrec / firstchar(code base) 与实际码位范围

审计目标 (任务书第 3 条):
  单字节码 idx = c - face[+0x20] 在每个 face 里是否越界 (idx >= nrec)?
  若越界 ⇒ GetGlyphUV 的 cave 会走"网格公式"分支, slot = idx - 224 (< 0) ⇒ 负 UV。

同时审计闸门 (gate):
  ELF 4 个 gate 站点的立即数 = 本盘"哪些字节是双字节前导"的唯一判据。
  若某盘文本里残留 [0xB1, gate) 的**裸单字节码** ⇒ 解码器会把它和后一字节吞成对偶码 ⇒
  整串重配对 + 长度字段与实际不符 (tcslib 的 assert_no_legacy_residue 注释明确写了
  "界面乱码、并可能内存损坏 (实机崩溃)")。

只读。输出到 stdout 与 work/builds/GR_MEMDRIFT/audit/*.json。
"""
import json
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib                                                          # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_MEMDRIFT', 'audit')
os.makedirs(OUT, exist_ok=True)

DISCS = [
    ('ZH113b',     os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')),
    ('ZH113b_fix', os.path.join(REPO, 'work', 'builds', 'GR_ZH113b_fix', 'GR_ZH113b_fix.iso')),
    ('EN_ORIG',    os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso')),
]

MENU_LBA = 776286


def u16(b, o):
    return struct.unpack_from('<H', b, o)[0]


def u32(b, o):
    return struct.unpack_from('<I', b, o)[0]


def gate_report(iso):
    """读 4 个 gate 站点的立即数 (与 tcslib.read_decode_gate 同口径, 但把每个站点都报出来)。"""
    rows = []
    for va in tcslib.ELF_GATE_SITES:
        off = tcslib.ELF_ISO_BASE + va - tcslib.ELF_VA_BASE
        w = u32(iso.mm, off)
        rows.append(dict(va='0x%08X' % va, iso_off='0x%X' % off,
                         word='0x%08X' % w, imm='0x%02X' % (w & 0xFFFF),
                         op='0x%02X' % (w >> 26)))
    imm = sorted({r['imm'] for r in rows})
    return rows, (rows[0]['imm'] if len(imm) == 1 else None), imm


def decode_walk(data, gate, pair_table):
    """按**引擎口径**走一遍: 返回 (单字节码出现直方图, 对偶码出现直方图, 解码后字符数)。

    判定与 ELF cave 完全一致:
      0xA1 <= b < gate  ⇒ 对偶 (吃下一字节, 要求 0xA1 <= trail < 0xFF)
      否则            ⇒ 单字节
    """
    singles, pairs, nch, i, n = {}, {}, 0, 0, len(data)
    while i < n:
        b = data[i]
        if 0xA1 <= b < gate and i + 1 < n and 0xA1 <= data[i + 1] < 0xFF:
            pairs[(b, data[i + 1])] = pairs.get((b, data[i + 1]), 0) + 1
            i += 2
        else:
            singles[b] = singles.get(b, 0) + 1
            i += 1
        nch += 1
    return singles, pairs, nch


def offrange_table(faces, atlas_w, atlas_h, gate):
    """对每个 face, 枚举 0x00..0xFF 的单字节码, 算 idx / 是否越界 / 网格分支的 UV。"""
    res = {}
    for (nm, fld, recs) in faces:
        nrec = fld[4] * fld[5]
        base = 0x20                                     # face[+0x20] = 码基址 (cave 里的 lb)
        rows = []
        for c in range(0x100):
            idx = (c - base) & 0xFF
            if idx < nrec:
                continue
            slot = idx - 224
            # MIPS div 向零截断
            row = int(slot / 62) if slot >= 0 else -int((-slot) / 62)
            col = slot - row * 62
            yy = row + (3 if row >= 12 else 0)
            u0, u1 = 16 * col, 16 * col + 16
            v0, v1 = 16 * yy + 2, 16 * yy + 18
            bad = (u0 < 0 or u1 > atlas_w or v0 < 0 or v1 > atlas_h)
            rows.append(dict(code='0x%02X' % c, is_pair_lead=(0xA1 <= c < gate),
                             idx=idx, slot=slot, row=row, col=col,
                             U0=u0, U1=u1, V0=v0, V1=v1, uv_out_of_atlas=bad))
        res[nm] = dict(nrec=nrec, fld4=fld[4], fld5=fld[5], code_base=base,
                       recs_present=len(recs), out_of_range=rows)
    return res


def main():
    report = {}
    for tag, path in DISCS:
        if not os.path.isfile(path):
            print('!! 缺盘 %s' % path)
            continue
        print('=' * 78)
        print('### %s  %s' % (tag, path))
        iso = tcslib.Iso(path)
        try:
            d = dict(iso=path, bytes=os.path.getsize(path))

            # ---- gate ----
            grows, gimm, gall = gate_report(iso)
            d['gate'] = dict(sites=grows, value=gimm, distinct=gall)
            print('  [gate] 站点立即数 %s ⇒ gate = %s' % (gall, gimm))

            # ---- FONT.RES ----
            fi = [i for i in range(64) if iso.img_entry(MENU_LBA, i)['name'] == 'FONT.RES']
            e = iso.img_entry(MENU_LBA, fi[0])
            raw = iso.read(e['iso_off'], e['stored'])
            subs = tcslib.lzo_subs(raw)
            ft = b''.join(s[0] for s in subs)
            d['font_res'] = dict(idx=fi[0], off='0x%X' % e['off'], stored=e['stored'],
                                 real=e['real'], expanded=len(ft),
                                 sha256=tcslib.sha256_file(path) if False else None)
            print('  [font] #%d off=0x%X stored=%d real=%d 展开=%d B'
                  % (fi[0], e['off'], e['stored'], e['real'], len(ft)))
            endp, faces = tcslib.parse_ft_faces(ft)
            d['font_res']['faces_end'] = '0x%X' % endp
            d['font_res']['file_len'] = len(ft)
            d['font_res']['tail_bytes_after_faces'] = len(ft) - endp

            # ---- COMMON.PAK atlas 尺寸 ----
            pi = [i for i in range(64) if iso.img_entry(MENU_LBA, i)['name'] == 'COMMON.PAK']
            pe = iso.img_entry(MENU_LBA, pi[0])
            pak = iso.read(pe['iso_off'], pe['stored'])
            precs = tcslib.parse_pak_records(pak)
            aw = ah = None
            for (pname, psm, w, h, clut, pxsz, pxoff) in precs:
                if pname == 'new_font_revised':
                    aw, ah = w, h
            d['common_pak'] = dict(idx=pi[0], off='0x%X' % pe['off'], stored=pe['stored'],
                                   real=pe['real'],
                                   records=[dict(name=p[0], psm=p[1], w=p[2], h=p[3],
                                                 clut=p[4], px_size=p[5], px_off='0x%X' % p[6])
                                            for p in precs])
            print('  [pak ] #%d off=0x%X stored=%d ; atlas %sx%s' % (pi[0], pe['off'], pe['stored'], aw, ah))

            # ---- face 表 + 越界 ----
            ftab = []
            for (nm, fld, recs) in faces:
                ftab.append(dict(name=nm, nrec=fld[4] * fld[5], fld=[int(x) for x in fld],
                                 recs=len(recs)))
            d['faces'] = ftab
            for f in ftab:
                print('  [face] %-8s nrec=%3d (fld[4]*fld[5]=%d*%d) 记录实存=%d fld=%s'
                      % (f['name'], f['nrec'], f['fld'][4], f['fld'][5], f['recs'], f['fld']))

            # 每个 face 的记录表声明的结束 vs 文件结束
            p = 28
            p = struct.unpack_from('<I', ft, 24)[0] and p
            off = 28
            for (nm, fld, recs) in faces:
                l = u32(ft, off)
                off += 4 + l + 56
                nrec = fld[4] * fld[5]
                # 实际存在的 10B 记录数: 从 off 开始按合法矩形数 (宽松: 直到文件尾)
                off += nrec * 10
            d['font_res']['records_end'] = '0x%X' % off
            print('  [font] 记录区结束 @0x%X ; 文件长 %d ; 其后 = 风格块 %d B'
                  % (off, len(ft), len(ft) - off))

            # ---- 越界码清单 ----
            gv = int(gimm, 16) if gimm else 0xA1
            ort = offrange_table(faces, aw or 1024, ah or 512, gv)
            d['out_of_range'] = ort
            for nm, r in ort.items():
                n = len(r['out_of_range'])
                codes = [x['code'] for x in r['out_of_range']]
                print('  [oob ] face %-8s nrec=%3d ⇒ 越界单字节码 %d 个: %s'
                      % (nm, r['nrec'], n, ' '.join(codes) if n else '(无)'))
                if n:
                    uvbad = [x['code'] for x in r['out_of_range'] if x['uv_out_of_atlas']]
                    print('        其中 UV 落到图集外(负值/超界): %s' % (' '.join(uvbad) or '(无)'))

            iso.close()
            report[tag] = d
        except Exception as ex:                                        # noqa: BLE001
            import traceback
            traceback.print_exc()
            report[tag] = dict(iso=path, error='%s: %s' % (type(ex).__name__, ex))
            try:
                iso.close()
            except Exception:                                          # noqa: BLE001
                pass

    # ---- charset 侧的 lead 使用范围 ----
    print('=' * 78)
    cs_path = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
    ch = json.load(open(cs_path, encoding='utf-8'))
    pairs = {tuple(v): k for k, v in ch['pair_of'].items()}
    leads = sorted({p[0] for p in pairs})
    trails = sorted({p[1] for p in pairs})
    singles = sorted({(v if isinstance(v, int) else v[0]) for v in ch['codes'].values()})
    print('### charset_compiled_zh16.json')
    print('  pair_of 条目 = %d ; lead 取值范围 = 0x%02X..0x%02X (%d 个) ; trail = 0x%02X..0x%02X (%d 个)'
          % (len(pairs), leads[0], leads[-1], len(leads), trails[0], trails[-1], len(trails)))
    print('  codes 单字节码 = %d 个, 范围 0x%02X..0x%02X' % (len(singles), singles[0], singles[-1]))
    report['charset'] = dict(pair_of=len(pairs),
                             leads=['0x%02X' % x for x in leads],
                             trails=['0x%02X' % x for x in trails],
                             single_count=len(singles),
                             single_min='0x%02X' % singles[0], single_max='0x%02X' % singles[-1])
    # 单字节码里落在 [0xA1,0xBA) 的 (可以是 lead 的) —— 与 tcslib 的表级预警同口径
    warn = [c for c in singles if 0xA1 <= c < 0xBA]
    print('  ★ codes 里落在 [0xA1,0xBA) 的单字节码 = %s' % (' '.join('0x%02X' % c for c in warn) or '(无)'))
    report['charset']['single_in_lead_window'] = ['0x%02X' % c for c in warn]

    with open(os.path.join(OUT, 'font_face_audit.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print('\n写出 %s' % os.path.join(OUT, 'font_face_audit.json'))


if __name__ == '__main__':
    main()
