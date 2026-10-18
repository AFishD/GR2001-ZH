# -*- coding: utf-8 -*-
r"""verify_r71.py — round71 交付硬门禁 (只读, 报告写 r71/).

门禁 (与任务书 §硬门禁 ①..⑧ 一一对应):
  ① `inject_text_csv.py --check-only` = exit 0
  ② 写盘后**重新 load 回读**: 每条被改标题解出来 == text_edited
  ③ 其余未改标题 + 69 个 <text> **逐字节不变**
  ④ 另外 9 份副本 (DE/ES/FR/IT × MENU/GR) 帧与 blob **逐字节相同**
  ⑤ 两个 IMG 条目表 off/stored/real 全条目一致
  ⑥ 幂等 (同表再注入 => exit 0 且产物 sha256 == 本盘)
  ⑦ 全盘差异只落在 MENU.IMG#283 真实容器窗口
     (ELF / PVD / 两个 IMG 条目表 / GR.IMG#551..#565 / FONT.RES / 字库像素 = 0)
  ⑧ audit_inventory 缺失 0
  ★ 旁证 A: 新盘重新 dump 的标题表 145/145 == 本表 text_edited
  ★ 旁证 B: 三张正文表 (long/long_nowrap/short) 与基底逐行 text_zh 相同

用法: python verify_r71.py --src <基底.iso> --dst <新盘.iso> --csv <编辑表> [--json out.json]
"""
import argparse
import csv
import io
import json
import os
import re
import struct
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import tcslib as T                                               # noqa: E402
import dump_containers as DC                                     # noqa: E402
import font_usage as FU                                          # noqa: E402
import font_compact as FC                                        # noqa: E402
import dump_font as DF                                           # noqa: E402
from inject_text_csv import parse_xml_attrs                      # noqa: E402

SEC = 2048
CHUNK = 1 << 24
MENU_LBA, GR_LBA = 776286, 19175
TAB_OFF, TAB_STEP = 0x830, 48
INJECTOR = os.path.join(REPO, 'tools', 'text_csv', 'inject_text_csv.py')
AUDIT = os.path.join(REPO, 'tools', 'iso_build', 'audit_inventory.py')


def sha(p):
    return T.sha256_file(p)


def diff_ranges(pa, pb):
    sa, sb = os.path.getsize(pa), os.path.getsize(pb)
    assert sa == sb, 'size differs: %d vs %d' % (sa, sb)
    out = []
    with open(pa, 'rb') as fa, open(pb, 'rb') as fb:
        off = 0
        while off < sa:
            n = min(CHUNK, sa - off)
            ba, bb = fa.read(n), fb.read(n)
            if ba == bb:
                off += n
                continue
            i = 0
            while i < n:
                if ba[i] == bb[i]:
                    i += 1
                    continue
                j = i
                while j < n and ba[j] != bb[j]:
                    j += 1
                out.append((off + i, j - i))
                i = j
            off += n
    return out


def read_rows(p):
    with io.open(p, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--dst', required=True)
    ap.add_argument('--csv', required=True)
    ap.add_argument('--json', default=os.path.join(HERE, 'verify_r71.json'))
    a = ap.parse_args()
    rep = dict(src=a.src, dst=a.dst, csv=a.csv, sha_src=sha(a.src), sha_dst=sha(a.dst))
    gates = []

    def gate(name, ok, detail):
        gates.append((name, bool(ok), detail))
        print(u'%s %-46s %s' % ('[OK]' if ok else '[!!]', name, detail))
        sys.stdout.flush()

    rows = read_rows(a.csv)
    edits = dict((r['id'], r['text_edited']) for r in rows
                 if r['text_edited'] != r['text_zh'])
    rep['n_rows'], rep['n_edits'] = len(rows), len(edits)
    print(u'# 表 %d 行, text_edited != text_zh 的 %d 行' % (len(rows), len(edits)))

    # ① ──
    r = subprocess.run([sys.executable, INJECTOR, '--csv', a.csv, '--src', a.src,
                        '--check-only'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    io.open(os.path.join(HERE, 'log_checkonly_r71.txt'), 'wb').write(r.stdout)
    gate(u'① 字库/写法预检 --check-only exit 0', r.returncode == 0,
         u'exit=%d' % r.returncode)

    iso_s, iso_d = T.Iso(a.src), T.Iso(a.dst)
    cs = T.Charset()
    cs_s = DC.sfxml_copies_of(FU.build_container_list(iso_s))
    cs_d = DC.sfxml_copies_of(FU.build_container_list(iso_d))
    tgt_s = [c for c in cs_s if c['role'] == 'zh-main'][0]
    tgt_d = [c for c in cs_d if c['role'] == 'zh-main'][0]
    blob_s = FU.container_blob(iso_s, tgt_s['c'])[0]
    blob_d = FU.container_blob(iso_d, tgt_d['c'])[0]
    at_s, at_d = parse_xml_attrs(blob_s), parse_xml_attrs(blob_d)
    print(u'# 副本 %d/%d, 注入目标 %s, name 属性 %d/%d'
          % (len(cs_s), len(cs_d), DC.cont_name(tgt_s['c']), len(at_s), len(at_d)))

    # ② ──
    bad = []
    for i, (k, tag, off, val) in enumerate(at_d):
        rid = 'SFXML:A%04d' % k
        if rid in edits and cs.decode(val)[0] != edits[rid]:
            bad.append((rid, edits[rid], cs.decode(val)[0]))
    gate(u'② 回读: 每条被改标题 == text_edited', not bad,
         u'%d/%d 命中%s' % (len(edits) - len(bad), len(edits),
                            (u'  不符 %s' % bad[:4]) if bad else u' ✓'))

    # ③ ──
    n_same = n_diff = 0
    diff_ids = []
    for i in range(len(at_s)):
        rid = 'SFXML:A%04d' % (i + 1)
        if rid in edits:
            continue
        s = blob_s[at_s[i][2]:at_s[i][2] + len(at_s[i][3])]
        d = blob_d[at_d[i][2]:at_d[i][2] + len(at_d[i][3])]
        if s == d:
            n_same += 1
        else:
            n_diff += 1
            diff_ids.append(rid)
    t_s = T.parse_sfxml(blob_s)
    t_d = dict((x[0], x[3]) for x in T.parse_sfxml(blob_d))
    txt_same = txt_diff = 0
    txt_bad = []
    for (k, o, ln, b) in t_s:
        if k not in t_d:
            txt_bad.append('T%04d missing' % k)
        elif t_d[k] == b:
            txt_same += 1
        else:
            txt_diff += 1
            txt_bad.append('T%04d changed' % k)
    gate(u'③ 其余 %d 条标题 + %d 个 <text> 逐字节不变' % (n_same, len(t_s)),
         n_diff == 0 and txt_diff == 0 and not txt_bad,
         u'未改标题 %d 同 / %d 异; <text> %d 同 / %d 异 %s'
         % (n_same, n_diff, txt_same, txt_diff, txt_bad[:4]))
    rep['attr_unchanged'] = n_same
    rep['attr_changed_unexpected'] = diff_ids
    rep['text_total'] = len(t_s)
    rep['text_changed'] = txt_diff

    # ④ ──
    nine = []
    for (c_s, c_d) in zip(cs_s, cs_d):
        if c_s['role'] == 'zh-main':
            continue
        e_s = iso_s.img_entry(c_s['c']['lba'], c_s['idx'])
        e_d = iso_d.img_entry(c_d['c']['lba'], c_d['idx'])
        ok = ((e_s['stored'] == e_d['stored']) and (e_s['real'] == e_d['real'])
              and iso_s.read(e_s['iso_off'], e_s['stored'])
              == iso_d.read(e_d['iso_off'], e_d['stored'])
              and FU.container_blob(iso_s, c_s['c'])[0]
              == FU.container_blob(iso_d, c_d['c'])[0])
        nine.append((c_s['name'], ok))
    ok9 = all(x[1] for x in nine)
    gate(u'④ 另外 9 份语言副本 帧+blob 逐字节相同', ok9,
         (u'9/9 份一致 ✓' if ok9 else u'不一致: %s' % [x[0] for x in nine if not x[1]]))
    rep['nine_copies'] = dict(nine)
    rep['nine_checked'] = len(nine)

    # ⑤ ──
    ent_bad = []
    for tag, lba in (('MENU.IMG', MENU_LBA), ('GR.IMG', GR_LBA)):
        n = FC.img_entry_count(iso_s, lba)
        for idx in range(n):
            e_s = iso_s.img_entry(lba, idx)
            e_d = iso_d.img_entry(lba, idx)
            for f in ('iso_off', 'stored', 'real', 'name'):
                if e_s.get(f) != e_d.get(f):
                    ent_bad.append('%s#%d.%s %r->%r' % (tag, idx, f, e_s.get(f), e_d.get(f)))
    gate(u'⑤ 两个 IMG 条目表 off/stored/real 不变', not ent_bad,
         (u'全部条目逐字段一致 ✓ (%d+%d 条)'
          % (FC.img_entry_count(iso_s, MENU_LBA), FC.img_entry_count(iso_s, GR_LBA)))
         if not ent_bad else str(ent_bad[:4]))
    rep['img_entries'] = dict(menu=FC.img_entry_count(iso_s, MENU_LBA),
                              gr=FC.img_entry_count(iso_s, GR_LBA))

    # ⑥ ──
    tmp = os.path.join(HERE, '_idem_tmp.iso')
    if os.path.exists(tmp):
        os.remove(tmp)
    r = subprocess.run([sys.executable, INJECTOR, '--csv', a.csv, '--src', a.dst,
                        '--dst', tmp], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    io.open(os.path.join(HERE, 'log_idem_r71.txt'), 'wb').write(r.stdout)
    idem = (r.returncode == 0) and os.path.isfile(tmp) and sha(tmp) == sha(a.dst)
    gate(u'⑥ 幂等: 同表再注入 => 产物 sha256 == 本盘', idem,
         u'exit=%d, sha %s' % (r.returncode,
                               sha(tmp)[:16] if os.path.isfile(tmp) else u'-'))
    if os.path.isfile(tmp):
        os.remove(tmp)
    rep['idempotent'] = idem

    # ⑦ ──
    raw = diff_ranges(a.src, a.dst)
    tot = sum(n for _o, n in raw)
    e_tgt = iso_s.img_entry(tgt_s['c']['lba'], tgt_s['idx'])
    lo = e_tgt['iso_off']
    hi = lo + e_tgt['stored']
    outside = [(o, n) for (o, n) in raw if not (o >= lo and o + n <= hi)]
    tabs = [(MENU_LBA * SEC + TAB_OFF, MENU_LBA * SEC + TAB_OFF + TAB_STEP * 1000),
            (GR_LBA * SEC + TAB_OFF, GR_LBA * SEC + TAB_OFF + TAB_STEP * 600)]
    n551 = [(iso_s.img_entry(GR_LBA, i)['iso_off'],
             iso_s.img_entry(GR_LBA, i)['iso_off'] + iso_s.img_entry(GR_LBA, i)['stored'])
            for i in range(551, 566)
            if 0 < iso_s.img_entry(GR_LBA, i)['stored'] < 0x7FFFFFFF]
    base = FC.find_elf_base(iso_s)
    hdr = bytes(iso_s.mm[base:base + 64])
    e_shoff = struct.unpack_from('<I', hdr, 0x20)[0]
    e_shentsize, e_shnum = struct.unpack_from('<HH', hdr, 0x2E)
    elf = (base, base + e_shoff + e_shentsize * e_shnum)
    f = DF.load_font(a.src)
    px = (f['pak_e']['iso_off'] + f['atlas']['px_off'],
          f['pak_e']['iso_off'] + f['atlas']['px_off'] + f['atlas']['px_size'])
    ft = (f['ft_e']['iso_off'], f['ft_e']['iso_off'] + f['ft_e']['stored'])
    f_d = DF.load_font(a.dst)
    rep['font_same'] = dict(ft_res_sha=(f['ft_res_sha256'] if 'ft_res_sha256' in f else None),
                            px_sha_src=f['atlas'].get('px_sha256'),
                            px_sha_dst=f_d['atlas'].get('px_sha256'))

    def cnt(reg):
        return sum(n for (o, n) in raw if o >= reg[0] and o + n <= reg[1])

    parts = dict(in_MENU_283=cnt((lo, hi)), ELF=cnt(elf), PVD=cnt((16 * SEC, 18 * SEC)),
                 img_entry_tables=cnt(tabs[0]) + cnt(tabs[1]),
                 GR_551_565=sum(n for (o, n) in raw
                                if any(o >= s and o + n <= t for (s, t) in n551)),
                 FONT_RES=cnt(ft), font_atlas_pixels=cnt(px))
    rep.update(diff_bytes=tot, diff_spans=len(raw), diff_buckets=parts,
               target_window=[lo, hi],
               diff_outside_target=sum(n for _o, n in outside))
    gate(u'⑦ 差异只落在 MENU.IMG#283 真实容器窗口内', not outside,
         u'总差异 %d B / %d 段; 窗口外 %d B; %s'
         % (tot, len(raw), sum(n for _o, n in outside),
            u' '.join(u'%s=%d' % (k, v) for k, v in sorted(parts.items())
                      if k != 'in_MENU_283')))

    # ⑧ ──
    r = subprocess.run([sys.executable, AUDIT, os.path.relpath(a.dst, REPO)],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=REPO)
    txt = r.stdout.decode('utf-8', 'replace')
    io.open(os.path.join(HERE, 'log_audit_inventory_r71.txt'), 'w', encoding='utf-8',
            newline='\n').write(txt)
    m = re.search(r'缺失\(仍为 EN 词\) (\d+) 条', txt)
    n_miss = int(m.group(1)) if m else -1
    gate(u'⑧ audit_inventory 缺失 0', r.returncode == 0 and n_miss == 0,
         u'exit=%d, 缺失 %d 条' % (r.returncode, n_miss))
    rep['audit_missing'] = n_miss

    # 旁证 A ── 新盘重新 dump 的标题表 145/145
    dump_csv = None
    for cand in (os.path.join(REPO, 'work', 'builds', 'GR_ZH117', 'text',
                              'GR_ZH117_text_sf_titles.csv'),):
        if os.path.isfile(cand):
            dump_csv = cand
    pa_ok, pa_detail = False, u'未找到新盘的标题 dump'
    if dump_csv:
        d_rows = read_rows(dump_csv)
        mine = dict((r['id'], r['text_edited']) for r in rows)
        nmis = [(r['id'], mine.get(r['id']), r['text_zh']) for r in d_rows
                if mine.get(r['id']) != r['text_zh']]
        pa_ok = (len(d_rows) == len(rows) and not nmis)
        pa_detail = (u'新盘 dump %d 行 == 本表 %d 行 且 145/145 == text_edited ✓'
                     % (len(d_rows), len(rows))) if pa_ok else u'%d 处不符 %s' % (len(nmis), nmis[:4])
    gate(u'★A 新盘重新 dump 标题表 == 本表 text_edited', pa_ok, pa_detail)

    # 旁证 B ── 三张正文表逐行 text_zh 相同
    pb_ok, pb_detail = True, []
    for kind, fn in (('long', 'text_long.csv'), ('long_nowrap', 'text_long_nowrap.csv'),
                     ('short', 'text_short.csv')):
        p1 = os.path.join(REPO, 'work', 'builds', 'GR_ZH114', 'text', 'GR_ZH114_' + fn)
        p2 = os.path.join(REPO, 'work', 'builds', 'GR_ZH117', 'text', 'GR_ZH117_' + fn)
        if not (os.path.isfile(p1) and os.path.isfile(p2)):
            pb_ok = False
            pb_detail.append(u'%s: 缺文件' % kind)
            continue
        r1, r2 = read_rows(p1), read_rows(p2)
        same = sum(1 for x, y in zip(r1, r2) if x['text_zh'] == y['text_zh'])
        ok = (len(r1) == len(r2) and same == len(r1))
        pb_ok = pb_ok and ok
        pb_detail.append(u'%s %d/%d' % (kind, same, len(r1)))
    gate(u'★B 三张正文表逐行 text_zh == 基底', pb_ok,
         u' / '.join(pb_detail) + (u'  ⇒ 正文一个字没动 ✓' if pb_ok else u''))

    rep['gates'] = [dict(name=n, ok=o, detail=d) for (n, o, d) in gates]
    rep['all_ok'] = all(o for (_n, o, _d) in gates)
    with io.open(a.json, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(rep, ensure_ascii=False, indent=1) + '\n')
    print(u'\n# 全部门禁: %s' % (u'通过 ✓' if rep['all_ok'] else u'有不通过项 ✗'))
    print(u'# -> %s' % a.json)
    iso_s.close()
    iso_d.close()
    return 0 if rep['all_ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
