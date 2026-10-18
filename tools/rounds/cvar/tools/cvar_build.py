# -*- coding: utf-8 -*-
r"""cvar_build.py — 用"字节区间拼接"构造单变量盘 + 自我一致性检查 + meta.json

构造原理: 两张盘**尺寸完全相同** (1648164864 B), 且汉化的全部变化都是**同偏移等长替换**
⇒ 单变量盘 = 原盘副本, 再把选中部件的差异区间从汉化盘拷过来。没有 LBA 平移、没有长度变化。

用法:
  python cvar_build.py --orig <EN.iso> --zh <ZH.iso> --components <components.json>
                       --name CVAR_01_elf --parts P1_elf [--outdir work/builds/GR_CVAR]
                       [--desc "..."]

自我检查:
  [1] 尺寸 == 原盘尺寸
  [2] MENU.IMG 的 ISO9660 声明长度 (值 / 是否扇区对齐 / 是否与原盘一致)
  [3] IMG 条目: stored==real 违反数 ; off+stored 越界数 ; 条目区间重叠对数
  [4] COMMON.PAK 字库容器两条不变式 px_size == w*h/2+16 ; (w*h/2)%2048 == 0
  [5] ★ 最强证明: 造出来的盘与原盘的差异区间集合 == 选中部件的区间集合 (严格相等)
"""
import argparse
import hashlib
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SEC = 2048
TAB_OFF, TAB_STEP = 0x830, 48
IMG_LBA = {'MENU.IMG': 776286, 'GR.IMG': 19175}
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))


def sha256_file(p, bufsize=1 << 22):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        while True:
            b = f.read(bufsize)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def read_runs_stream(path, chunk=1 << 22):
    """流式读全文件, 不常驻内存"""
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            yield b


def diff_runs(path_a, path_b):
    """流式求精确差异游程"""
    runs = []
    off = 0
    ia, ib = read_runs_stream(path_a), read_runs_stream(path_b)
    for da, db in zip(ia, ib):
        if da != db:
            i = 0
            k = len(da)
            while i < k:
                if da[i] == db[i]:
                    i += 1
                    continue
                j = i + 1
                while j < k and da[j] != db[j]:
                    j += 1
                s, e = off + i, off + j
                if runs and runs[-1][1] >= s:
                    runs[-1][1] = max(runs[-1][1], e)
                else:
                    runs.append([s, e])
                i = j
        off += len(da)
    return runs


def iso_files(d):
    pvd = 16 * SEC
    root_lba = struct.unpack_from('<I', d, pvd + 158)[0]
    root_size = struct.unpack_from('<I', d, pvd + 166)[0]
    out = []

    def readdir(lba, size):
        r = []
        data = d[lba * SEC:lba * SEC + size]
        i = 0
        while i < len(data):
            Ln = data[i]
            if Ln == 0:
                i = (i // SEC + 1) * SEC
                if i >= len(data):
                    break
                continue
            if i + Ln > len(data) or Ln < 34:
                break
            rec = data[i:i + Ln]
            r.append((rec[33:33 + rec[32]],
                      struct.unpack_from('<I', rec, 2)[0],
                      struct.unpack_from('<I', rec, 10)[0], rec[25],
                      lba * SEC + i, Ln))
            i += Ln
        return r

    def walk(lba, size, prefix):
        for nm, ext, sz, fl, ao, Ln in readdir(lba, size):
            if nm in (b'\x00', b'\x01'):
                continue
            name = nm.decode('latin-1')
            p = (prefix + '/' + name) if prefix else name
            if fl & 2:
                walk(ext, sz, p)
            else:
                out.append({'path': p, 'lba': ext, 'size': sz,
                            'iso_off': ext * SEC, 'iso_end': ext * SEC + sz,
                            'dirrec_off': ao, 'dirrec_len': Ln})
    walk(root_lba, root_size, '')
    return out


def img_entries(d, lba):
    b = lba * SEC
    noff = struct.unpack_from('<I', d, b + 0x10)[0]
    nend = struct.unpack_from('<I', d, b + 0x04)[0]
    names = [x.decode('latin-1') for x in d[b + noff:b + nend].split(b'\x00') if x]
    return [(nm, list(struct.unpack_from('<12I', d, b + TAB_OFF + TAB_STEP * i)))
            for i, nm in enumerate(names)], b


def check_img(d, nm, lba, tot):
    E, b = img_entries(d, lba)
    ne = nq = 0
    bad_bounds = []
    spans = []
    for i, (n2, f) in enumerate(E):
        if f[6] == 0 and f[7] == 0:
            continue
        if f[6] != f[7]:
            ne += 1
        if f[8] + f[6] > tot:
            nq += 1
            bad_bounds.append((i, n2, f[8], f[6], f[8] + f[6], tot))
        spans.append((f[8], f[8] + f[6], i, n2))
    spans.sort()
    ov = 0
    ovlist = []
    for k in range(1, len(spans)):
        if spans[k][0] < spans[k - 1][1]:
            ov += 1
            if len(ovlist) < 8:
                ovlist.append((spans[k - 1][3], spans[k - 1][0], spans[k - 1][1],
                               spans[k][3], spans[k][0]))
    return {'entries': len(E), 'stored_ne_real': ne, 'out_of_bounds': nq,
            'bad_bounds_sample': bad_bounds[:5], 'overlaps': ov,
            'overlap_sample': ovlist}


def check_pak(d, nm, lba):
    """COMMON.PAK 里字库容器的两条不变式"""
    import tcslib
    E, b = img_entries(d, lba)
    hit = [(i, f) for i, (n2, f) in enumerate(E) if n2 == 'COMMON.PAK']
    if not hit:
        return {'found': False}
    i, f = hit[0]
    pak = bytes(d[b + f[8]: b + f[8] + f[6]])
    recs = tcslib.parse_pak_records(pak)
    out = {'found': True, 'pak_off': f[8], 'pak_stored': f[6], 'pak_real': f[7],
           'pak_size': len(pak), 'records': []}
    for r in recs:
        name, psm, w, h, clut, px_size, PX = r
        half = w * h // 2
        out['records'].append({
            'name': name, 'psm': psm, 'w': w, 'h': h, 'clut': clut,
            'px_size': px_size, 'px_off': PX,
            'w*h/2': half,
            'inv1_px_size_eq_half_plus16': (px_size == half + 16),
            'inv2_half_mod2048_eq0': (half % 2048 == 0),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--orig', required=True)
    ap.add_argument('--zh', required=True)
    ap.add_argument('--components', required=True)
    ap.add_argument('--name', required=True)
    ap.add_argument('--parts', nargs='+', required=True)
    ap.add_argument('--outdir', default=os.path.join(REPO, 'work', 'builds', 'GR_CVAR'))
    ap.add_argument('--desc', default='')
    ap.add_argument('--force', action='store_true')
    x = ap.parse_args()

    C = json.load(open(x.components, encoding='utf-8'))
    parts = list(x.parts)
    if parts == ['ALL_EXCEPT']:
        raise SystemExit('use --parts with explicit names')
    allc = ['P1_elf', 'P2_atlas', 'P3_ft', 'P4_text', 'P5_book', 'P6_other']
    if 'REST' in parts:
        parts = [p for p in allc if p not in
                 ('P1_elf', 'P2_atlas', 'P3_ft', 'P4_text')]
        parts = sorted(set(parts) | set(x.parts) - {'REST'}) if False else parts
    sel = []
    for p in parts:
        if p not in C['components']:
            print('  !! 部件 %s 无差异, 跳过' % p)
            continue
        sel.extend(tuple(r) for r in C['components'][p]['runs'])
    sel.sort()
    exp_runs = []
    for s, e in sel:
        if exp_runs and s <= exp_runs[-1][1]:
            exp_runs[-1][1] = max(exp_runs[-1][1], e)
        else:
            exp_runs.append([s, e])
    exp_bytes = sum(e - s for s, e in exp_runs)

    dst = os.path.join(x.outdir, '%s.iso' % x.name)
    os.makedirs(x.outdir, exist_ok=True)
    print('== 构造 %s ==' % x.name)
    print('   部件: %s' % ', '.join(parts))
    print('   期望差异区间 %d 个, %d B' % (len(exp_runs), exp_bytes))

    # ---- 流式拷贝原盘, 再把选中区间从汉化盘写进去
    if os.path.exists(dst) and not x.force:
        print('   %s 已存在, 跳过构造 (--force 覆盖)' % dst)
    else:
        with open(x.orig, 'rb') as fi, open(dst, 'wb') as fo:
            while True:
                b = fi.read(1 << 22)
                if not b:
                    break
                fo.write(b)
        with open(x.zh, 'rb') as fz, open(dst, 'r+b') as fo:
            for (s, e) in exp_runs:
                fz.seek(s)
                fo.seek(s)
                fo.write(fz.read(e - s))
        print('   写入完成: %s (%d B)' % (dst, os.path.getsize(dst)))

    # ---- 自我检查
    res = {'name': x.name, 'iso': dst, 'path': dst, 'desc': x.desc,
           'parts': parts,
           'built_from': {'orig': x.orig, 'zh': x.zh,
                          'orig_sha256': C['sha256_a'], 'zh_sha256': C['sha256_b']},
           'size': os.path.getsize(dst),
           'sha256': sha256_file(dst),
           'expected_runs': len(exp_runs), 'expected_bytes': exp_bytes,
           'build_command': ('python work/builds/GR_CVAR/tools/cvar_build.py '
                             '--orig %s --zh %s --components %s --name %s --parts %s'
                             % (x.orig, x.zh, x.components, x.name, ' '.join(parts))),
           'checks': {}}
    chk = res['checks']
    sz_o = os.path.getsize(x.orig)
    chk['1_size_eq_orig'] = (res['size'] == sz_o, '%d vs %d' % (res['size'], sz_o))

    d = open(dst, 'rb').read()
    fa = iso_files(d)
    menu = [f for f in fa if f['path'].startswith('MENU.IMG')][0]
    menu_sz = menu['size']
    chk['2_menu_img_declared'] = {
        'value': menu_sz, 'hex': hex(menu_sz),
        'mod2048': menu_sz % 2048,
        'sector_aligned': menu_sz % 2048 == 0,
        'orig_value': 58300882,
        'equals_orig': menu_sz == 58300882,
        'note': '原盘该值也不是 2048 的倍数 ⇒ 本项对齐要求在本盘上本来就不成立'}
    chk['3_img_entries'] = {}
    for nm, lba in IMG_LBA.items():
        tot = [f for f in fa if f['path'].startswith(nm)][0]['size']
        chk['3_img_entries'][nm] = check_img(d, nm, lba, tot)
    if 'P2_atlas' in parts:
        chk['4_pak_invariants'] = {}
        for nm, lba in IMG_LBA.items():
            chk['4_pak_invariants'][nm] = check_pak(d, nm, lba)
    else:
        chk['4_pak_invariants'] = {'skipped': '本盘不含 P2 (字库容器未被替换)'}
    del d

    # ---- [5] 实际差异 vs 期望差异
    print('   [5] 实际对比原盘 (流式)...')
    got = diff_runs(x.orig, dst)
    same = (got == exp_runs)
    chk['5_exact_single_variable'] = {
        'pass': same, 'actual_runs': len(got),
        'actual_bytes': sum(e - s for s, e in got),
        'expected_runs': len(exp_runs), 'expected_bytes': exp_bytes,
        'runs_identical': same}
    if not same:
        gs, es = set(map(tuple, got)), set(map(tuple, exp_runs))
        chk['5_exact_single_variable']['extra'] = sorted(gs - es)[:20]
        chk['5_exact_single_variable']['missing'] = sorted(es - gs)[:20]
    # 与汉化盘的差异 (缺多少)
    print('   [~] 与汉化基底盘的差异 (流式)...')
    miss = diff_runs(dst, x.zh)
    chk['6_diff_vs_zh113b'] = {'runs': len(miss),
                               'bytes': sum(e - s for s, e in miss)}
    res['actual_runs'] = len(got)
    res['actual_bytes'] = sum(e - s for s, e in got)
    res['iso_range'] = [min(r[0] for r in got), max(r[1] for r in got)] if got else None

    with open(os.path.join(x.outdir, '%s.meta.json' % x.name), 'w',
              encoding='utf-8', newline='\n') as f:
        json.dump(res, f, indent=1, ensure_ascii=False)

    print('   sha256 = %s' % res['sha256'])
    print('   实际差异 %d 个区间 / %d B ; 单变量严格相等 = %s'
          % (res['actual_runs'], res['actual_bytes'], same))
    print('   与汉化盘还差 %d 个区间 / %d B'
          % (chk['6_diff_vs_zh113b']['runs'], chk['6_diff_vs_zh113b']['bytes']))
    print('   检查: 尺寸=%s  MENU.IMG=%d (mod2048=%d)  stored!=real=%s  越界=%s  重叠=%s'
          % (chk['1_size_eq_orig'][0], menu_sz, menu_sz % 2048,
             [v['stored_ne_real'] for v in chk['3_img_entries'].values()],
             [v['out_of_bounds'] for v in chk['3_img_entries'].values()],
             [v['overlaps'] for v in chk['3_img_entries'].values()]))
    if 'P2_atlas' in parts:
        for nm, pk in chk['4_pak_invariants'].items():
            if pk.get('found'):
                r1 = pk['records'][1]
                print('   PAK %s::%s  w=%d h=%d px_size=0x%X  w*h/2=%d  '
                      'inv1=%s inv2=%s'
                      % (nm, r1['name'], r1['w'], r1['h'], r1['px_size'],
                         r1['w*h/2'], r1['inv1_px_size_eq_half_plus16'],
                         r1['inv2_half_mod2048_eq0']))
    return 0 if same else 2


if __name__ == '__main__':
    sys.exit(main())
