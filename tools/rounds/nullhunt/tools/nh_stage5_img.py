# -*- coding: utf-8 -*-
r"""nh_stage5_img.py — IMG 条目表全量审计 (MENU.IMG + GR.IMG, EN_ORIG vs ZH113b vs ZH113b_fix)

检查项:
  A. 头部字段 + 名字区 + 条目数自证
  B. stored != real 的条目 (引擎读流上界 = min(stored,real) ⇒ stored>real 必截断)
  C. off+stored 越界 / 与下一入口重叠 / 扇区对齐
  D. off==0 / stored==0 / real==0 的空条目
  E. ZH vs EN 逐字段差异 (name/off/stored/real/其它 8 个 u32), 分类
  F. 目录/名字区/哈希表是否被动过
输出 evidence/stage5_img_audit.txt + stage5_img_fields.json
"""
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nh_lib as N   # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
TAGS = ('EN_ORIG', 'ZH113b', 'ZH113b_fix')


def sort_sector(x):
    return (x + N.SEC - 1) // N.SEC * N.SEC


def load(tag):
    iso = N.Iso(N.ISO[tag])
    out = {}
    for path, f in iso.files().items():
        if path not in ('/GR.IMG;1', '/MENU.IMG;1'):
            continue                       # 排除 /MODULES/IOPRP242.IMG;1 (不是本类容器)
        ents, hdr, names = iso.img_entries(f['lba'], None)
        out[path] = dict(iso=iso, lba=f['lba'], size=f['size'], hdr=hdr,
                         names=names, ents=ents, file=f)
    return iso, out


def main():
    buf = io.StringIO()
    js = {}
    data = {}
    for tag in TAGS:
        iso, imgs = load(tag)
        data[tag] = imgs
        for path, d in imgs.items():
            buf.write('=' * 110 + '\n')
            buf.write('%s  %s  ISO LBA=%d  声明 size=%s\n'
                      % (tag, path, d['lba'], N.fmt(d['size'])))
            h = d['hdr']
            buf.write('  头 12 u32: %s\n' % h['raw'])
            buf.write('  名字区 0x%X..0x%X (len=%s), 条目数=%d, 表末尾推算=0x%X (头 h3=0x%X)\n'
                      % (h['names_start'], h['names_end'],
                         N.fmt(h['names_end'] - h['names_start']), len(d['names']),
                         N.TAB_OFF + N.TAB_STEP * len(d['names']), h['tbl_end']))
            ents = d['ents']
            # --- 条目表是否在名字区之前结束 (表末尾不能盖住名字区) ---
            tbl_end = N.TAB_OFF + N.TAB_STEP * len(ents)
            buf.write('  [不变量] 表末尾 0x%X %s 名字区起点 0x%X\n'
                      % (tbl_end, '<=' if tbl_end <= h['names_start'] else '!! >',
                         h['names_start']))
            # --- 条目表之后是否还有"零记录" (说明真实条目数更多) ---
            zero_run = 0
            for k in range(len(ents), len(ents) + 64):
                r = list(struct.unpack_from('<12I', iso.mm, h['base'] + N.TAB_OFF
                                            + N.TAB_STEP * k))
                if r == [0] * 12:
                    zero_run += 1
                else:
                    break
            buf.write('  条目表后的全零 48B 记录数 = %d (若>0 说明表尾对齐)\n' % zero_run)

            # ---------------- B/C/D ----------------
            sr, rr, bad_sr, ovf, misalign, empty, overlap = [], [], [], [], [], [], []
            byoff = sorted([e for e in ents if e['off']], key=lambda e: e['off'])
            for e in ents:
                if e['off'] == 0 and e['stored'] == 0 and e['real'] == 0:
                    empty.append(e)
                    continue
                if e['stored'] != e['real']:
                    sr.append(e)
                    if e['stored'] > e['real']:
                        bad_sr.append(e)
                if e['stored'] == 0 or e['real'] == 0:
                    rr.append(e)
                if e['off'] + max(e['stored'], e['real']) > d['size']:
                    ovf.append(e)
                if e['off'] % N.SEC:
                    misalign.append(e)
            for i in range(len(byoff) - 1):
                a, b = byoff[i], byoff[i + 1]
                if a['off'] + a['stored'] > b['off']:
                    overlap.append((a, b, a['off'] + a['stored'] - b['off']))
            buf.write('  条目总数=%d  空条目(off=stored=real=0)=%d\n'
                      % (len(ents), len(empty)))
            buf.write('  stored != real 的条目 = %d (其中 stored > real(读流截断) = %d)\n'
                      % (len(sr), len(bad_sr)))
            buf.write('  stored==0 或 real==0 = %d\n' % len(rr))
            buf.write('  off+max(stored,real) 超出 ISO 声明 size 的 = %d\n' % len(ovf))
            buf.write('  off 未按 2048 对齐的 = %d\n' % len(misalign))
            buf.write('  与下一入口重叠的 = %d\n' % len(overlap))
            buf.write('\n  --- [B] stored != real 明细 ---\n')
            for e in sr:
                tag2 = 'STORE>REAL 截断风险' if e['stored'] > e['real'] else 'stored<real (压缩, 正常)'
                buf.write('    #%-5d %-28s off=%-10s stored=%-10s real=%-10s d=%-8d %s\n'
                          % (e['idx'], e['name'], N.fmt(e['off']), N.fmt(e['stored']),
                             N.fmt(e['real']), e['real'] - e['stored'], tag2))
            buf.write('\n  --- [D] 空条目 ---\n')
            for e in empty:
                buf.write('    #%-5d %-28s raw=%s\n' % (e['idx'], e['name'], e['raw']))
            buf.write('\n  --- [C] 越界/未对齐/重叠 明细 ---\n')
            for e in ovf:
                buf.write('    OVF   #%-5d %-28s off=%-10s stored=%-10s end=%-12s size=%s\n'
                          % (e['idx'], e['name'], N.fmt(e['off']), N.fmt(e['stored']),
                             N.fmt(e['off'] + e['stored']), N.fmt(d['size'])))
            for e in misalign:
                buf.write('    MISA  #%-5d %-28s off=%-10s off%%2048=%d\n'
                          % (e['idx'], e['name'], N.fmt(e['off']), e['off'] % N.SEC))
            for (a, b, dl) in overlap:
                buf.write('    OVLP  #%-5d %-24s (end %s) > #%-5d %-24s (off %s)  overlap=%s\n'
                          % (a['idx'], a['name'], N.fmt(a['off'] + a['stored']),
                             b['idx'], b['name'], N.fmt(b['off']), N.fmt(dl)))
            # 数据区尾部
            maxend = max(e['off'] + e['stored'] for e in ents if e['off'])
            buf.write('\n  数据区最大 (off+stored) = %s ; ISO 声明 size = %s ; 余量 = %s B\n'
                      % (N.fmt(maxend), N.fmt(d['size']), N.fmt(d['size'] - maxend)))
            buf.write('  物理可用 = %s B(到盘尾) ; 余量 = %s B\n'
                      % (N.fmt(iso.size - d['lba'] * N.SEC),
                         N.fmt(iso.size - d['lba'] * N.SEC - d['size'])))
            buf.write('  名字区/哈希表是否被改: 见 stage5_fields_diff\n')

    # ---------------- E. ZH vs EN 逐字段差异 ----------------
    dif = io.StringIO()
    dif.write('IMG 条目逐字段差异 (EN_ORIG 为基准)\n')
    for path in sorted(data['EN_ORIG']):
        en = data['EN_ORIG'][path]
        for tag in ('ZH113b', 'ZH113b_fix'):
            zh = data[tag][path]
            dif.write('=' * 110 + '\n%s : %s  →  %s\n' % (path, 'EN_ORIG', tag))
            dif.write('  名字数 EN=%d ZH=%d\n' % (len(en['names']), len(zh['names'])))
            seten, setzh = set(en['names']), set(zh['names'])
            only_en = [n for n in en['names'] if n not in setzh]
            only_zh = [n for n in zh['names'] if n not in seten]
            dif.write('  仅 EN 有的名字 (%d): %s\n' % (len(only_en), only_en))
            dif.write('  仅 ZH 有的名字 (%d): %s\n' % (len(only_zh), only_zh))
            n = min(len(en['ents']), len(zh['ents']))
            fld_names = ['f0_nameoff', 'f1', 'f2', 'f3', 'f4', 'f5',
                         'stored', 'real', 'off', 'f9', 'f10', 'f11']
            cnt = {}
            rows = []
            for i in range(n):
                a, b = en['ents'][i], zh['ents'][i]
                df = [j for j in range(12) if a['raw'][j] != b['raw'][j]]
                if a['name'] != b['name']:
                    dif.write('  !! 同索引名字不同: #%d EN=%r ZH=%r\n'
                              % (i, a['name'], b['name']))
                if not df:
                    continue
                for j in df:
                    cnt[fld_names[j]] = cnt.get(fld_names[j], 0) + 1
                rows.append((i, a, b, df))
            dif.write('  字段不同的条目数 = %d / %d\n' % (len(rows), n))
            dif.write('  按字段统计: %s\n' % cnt)
            # off 是否整体平移
            deltas = {}
            for (i, a, b, df) in rows:
                if 8 in df and a['stored'] == b['stored'] and a['real'] == b['real']:
                    deltas[b['off'] - a['off']] = deltas.get(b['off'] - a['off'], 0) + 1
            dif.write('  仅 off 变、stored/real 不变 的条目数 = %d, off 差值直方图 = %s\n'
                      % (sum(deltas.values()), deltas))
            # 分类
            plan, unplan = [], []
            for (i, a, b, df) in rows:
                kinds = set(fld_names[j] for j in df)
                interesting = kinds - {'off', 'stored', 'real'}
                nm = (a['name'], b['name'])
                rec = 'EN#%d %r stored=%s real=%s off=%s  ->  ZH stored=%s real=%s off=%s  改动字段=%s' \
                      % (a['idx'], nm[0], N.fmt(a['stored']), N.fmt(a['real']),
                         N.fmt(a['off']), N.fmt(b['stored']), N.fmt(b['real']),
                         N.fmt(b['off']), sorted(kinds))
                (unplan if interesting else plan).append(rec)
            dif.write('\n  --- 计划内 (只动了 stored/real/off) : %d 条 ---\n' % len(plan))
            for r in plan:
                dif.write('    %s\n' % r)
            dif.write('\n  --- ★计划外 (动了名字偏移或其它 u32) : %d 条 ---\n' % len(unplan))
            for r in unplan:
                dif.write('    %s\n' % r)

    # ---------------- F. 头部/名字区/哈希表 是否被改 ----------------
    fsec = io.StringIO()
    fsec.write('IMG 头部 / 名字区 / 哈希区 字节级对比\n')
    for path in sorted(data['EN_ORIG']):
        en = data['EN_ORIG'][path]
        for tag in ('ZH113b', 'ZH113b_fix'):
            zh = data[tag][path]
            h = en['hdr']
            for label, off, ln in (
                    ('头部 0x000..0x830', 0, N.TAB_OFF),
                    ('条目表 0x830..0x%X' % (N.TAB_OFF + N.TAB_STEP * len(en['ents'])),
                     N.TAB_OFF, N.TAB_STEP * len(en['ents'])),
                    ('名字区 0x%X..0x%X' % (h['names_start'], h['names_end']),
                     h['names_start'], h['names_end'] - h['names_start']),
                    ('哈希区 0x%X 起 16384 B' % h['h8'], h['h8'], 16384)):
                base = en['lba'] * N.SEC
                a = data['EN_ORIG'][path]['iso'].rd(base + off, ln)
                b = data[tag][path]['iso'].rd(base + off, ln)
                neq = sum(1 for x, y in zip(a, b) if x != y)
                fsec.write('  %-28s %-14s vs %-14s : 不同字节 %d / %d %s\n'
                           % (path, 'EN_ORIG', tag, neq, ln,
                              'SAME' if neq == 0 else '★DIFF'))
                if neq and label.startswith('头部'):
                    for k in range(0, ln, 4):
                        if a[k:k + 4] != b[k:k + 4]:
                            fsec.write('        +0x%03X EN %s ZH %s\n'
                                       % (k, a[k:k + 4].hex(' '), b[k:k + 4].hex(' ')))
                if neq and label.startswith('哈希'):
                    # 找出哈希区前若干处差异
                    shown = 0
                    for k in range(ln):
                        if a[k] != b[k]:
                            fsec.write('        +0x%04X EN %02X ZH %02X\n' % (k, a[k], b[k]))
                            shown += 1
                            if shown >= 40:
                                fsec.write('        ... (仅示前 40 处)\n')
                                break

    # ---------------- 关键锚点 ----------------
    anc = io.StringIO()
    anc.write('锚点自证 (任务书给定: COMMON.PAK stored==real==400659 ; FONT.RES stored=4421 real=7222)\n')
    for tag in TAGS:
        for path in sorted(data[tag]):
            d = data[tag][path]
            for want in ('COMMON.PAK', 'FONT.RES'):
                for e in d['ents']:
                    if e['name'].upper() == want:
                        anc.write('  %-12s %-14s #%-5d %-12s stored=%-10s real=%-10s off=%-10s\n'
                                  % (tag, path, e['idx'], want, N.fmt(e['stored']),
                                     N.fmt(e['real']), N.fmt(e['off'])))
    anc.write('\n[自证] 条目 u32[0] = 名字偏移 (相对 IMG 起点)\n')
    for tag in TAGS:
        d = data[tag]['/MENU.IMG;1']
        e0 = d['ents'][0]
        base = d['lba'] * N.SEC
        anc.write('  %-12s 条目0 name=%-20r u32[0]=0x%X ; 容器内 0x%X 处 = %r\n'
                  % (tag, e0['name'], e0['nameoff'], e0['nameoff'],
                     d['iso'].rd(base + e0['nameoff'], 24)))
        anc.write('               names_start=0x%X + u32[0]=0x%X -> %r\n'
                  % (d['hdr']['names_start'], d['hdr']['names_start'] + e0['nameoff'],
                     d['iso'].rd(base + d['hdr']['names_start'] + e0['nameoff'], 24)))

    txt = buf.getvalue() + '\n\n' + fsec.getvalue() + '\n\n' + anc.getvalue() + '\n\n' + dif.getvalue()
    with open(os.path.join(N.EVID, 'stage5_img_audit.txt'), 'w', encoding='utf-8') as f:
        f.write(txt)
    # JSON: 只存 ZH113b_fix 的全部条目
    for tag in TAGS:
        for path, d in data[tag].items():
            js['%s|%s' % (tag, path)] = [dict(idx=e['idx'], name=e['name'], off=e['off'],
                                              stored=e['stored'], real=e['real'],
                                              raw=e['raw']) for e in d['ents']]
    with open(os.path.join(N.EVID, 'stage5_img_fields.json'), 'w', encoding='utf-8') as f:
        json.dump(js, f, indent=0)
    print(txt)


if __name__ == '__main__':
    main()
