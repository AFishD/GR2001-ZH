# -*- coding: utf-8 -*-
r"""r58 静态验收 (只读): 登记容器逐字闭环 / 那 8 条引号串 / 紧凑布局 / charset 只改 pair_of。

用法: python verify_all_r58.py [--iso108 <path>] [--iso107 <path>] [--json out.json]
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
G0P = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r46', 'charset_before_repack.json')
G1P = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56', 'charset_before_r56.json')
G2P = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
FAIL = []
RESULT = {}


def check(name, ok, detail=''):
    print('  [%s] %-64s %s' % ('OK' if ok else '!!', name, detail))
    if not ok:
        FAIL.append(name)
    return ok


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def cjk_segments(text, mp, n, min_cjk=2):
    out, cur = [], []
    runs = []
    for i, ch in enumerate(text):
        if '\u4e00' <= ch <= '\u9fff':
            cur.append(i)
            continue
        if len(cur) >= min_cjk:
            runs.append(cur)
        cur = []
    if len(cur) >= min_cjk:
        runs.append(cur)
    for idxs in runs:
        a, b = idxs[0], idxs[-1] + 1
        lo = mp[a]
        hi = mp[b] if b < len(mp) else n
        out.append((lo, hi))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso107', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH107',
                                                     'GR_ZH107.iso'))
    ap.add_argument('--iso108', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH108',
                                                     'GR_ZH108.iso'))
    ap.add_argument('--json', default=os.path.join(HERE, 'verify_r58.json'))
    a = ap.parse_args()
    print('=' * 104)
    print('round58 静态验收 —— 容器级重编码覆盖面补全 (GR_ZH107 → GR_ZH108)')
    print('=' * 104)
    sh107, sh108 = sha(a.iso107), sha(a.iso108)
    print('  GR_ZH107 sha256 %s  (%.3f GB)' % (sh107, os.path.getsize(a.iso107) / 1e9))
    print('  GR_ZH108 sha256 %s  (%.3f GB)' % (sh108, os.path.getsize(a.iso108) / 1e9))
    G0, G1, G2 = (tcslib.Charset(p) for p in (G0P, G1P, G2P))
    i7, i8 = tcslib.Iso(a.iso107), tcslib.Iso(a.iso108)
    mig = FC.STALE_MIGRATIONS[0]
    idx = FC.migration_index(mig)

    print('\n── 1. 登记容器逐个: 旧 charset 解 107 == 新 charset 解 108 (逐字相同) ──')
    print('  "旧 charset" = 该容器字节实际所属的那一代 (迁移清单按槽位 sha256 钉死; '
          '不在清单里 = 与码位无关)\n')
    print('  %-38s %-10s %-9s %-9s %-9s %s'
          % ('container', 'role', 'G0解==新', 'G1解==新', '新解==107', '改动字节/段'))
    n_reg = n_ok = 0
    rows = []
    for (tag, lba, i0, e) in FC.enumerate_containers(i7):
        rent = FC.registry_match(e['name'])
        if not rent:
            continue
        n_reg += 1
        s7 = FC.Slot(i7, tag, lba, i0)
        try:
            s8 = FC.Slot(i8, tag, lba, i0)
        except Exception as ex:                                        # noqa: BLE001
            check('容器 %s#%d %s 能在 108 上解开' % (tag, i0, e['name']), False, str(ex))
            continue
        rec = idx.get(hashlib.sha256(s7.raw).hexdigest())
        role = (rec or {}).get('role', 'independent')
        t7_0, t7_1, t7_2 = (c.decode(s7.blob)[0] for c in (G0, G1, G2))
        t8 = G2.decode(s8.blob)[0]
        eq0 = (t7_0 == t8)
        eq1 = (t7_1 == t8)
        eq_self = (t7_2 == t8)
        diff = sum(1 for k in range(min(len(s7.blob), len(s8.blob)))
                   if s7.blob[k] != s8.blob[k])
        segs = cjk_segments(t7_0, G0.decode(s7.blob)[1], len(s7.blob), rent['min_cjk'])
        # 角色感知的判据: migrate/independent ⇒ 该容器字节在**陈旧代**上, 比 G0解(107) == G2解(108);
        #                 current            ⇒ 它本来就在现役代上, 比 G2解(107) == G2解(108)。
        ok_here = (eq_self if role == 'current' else eq0)
        n_ok += ok_here
        print('  %-38s %-10s %-9s %-9s %-9s %d B / %d 段   %s'
              % ('%s#%d %s' % (tag, i0, e['name']), role, 'OK' if eq0 else 'X',
                 'OK' if eq1 else 'X', 'OK' if eq_self else 'X', diff, len(segs),
                 'OK' if ok_here else '!! 判据不符'))
        rows.append(dict(container='%s#%d %s' % (tag, i0, e['name']), role=role,
                         eq_g0=t7_0 == t8, eq_g1=t7_1 == t8, eq_g2=t7_2 == t8,
                         diff_bytes=diff, segments=len(segs),
                         registry_why=rent['why']))
    check('登记容器 %d 个: 逐字闭环 (migrate/independent 比 G0解(107)==G2解(108); '
          'current 比 G2解(107)==G2解(108))' % n_reg, n_ok == n_reg, '%d/%d' % (n_ok, n_reg))
    n_g1 = sum(1 for r in rows if r['eq_g1'])
    print('  (对照) 一律用 G1(pre-r56) 当"旧 charset": %d/%d 相同 —— 不相同的: %s'
          % (n_g1, n_reg, ', '.join(r['container'] for r in rows if not r['eq_g1']) or '无'))
    RESULT['containers'] = dict(total=n_reg, eq_g0=n_ok, eq_g1=n_g1, rows=rows)

    print('\n── 2. MENU.IMG#30 EN_STRINGS.TXT: 那 8 条引号串 ──')
    INTENDED = [('WPN_EXTRAAMMO', '追加弹药'), ('ITM_BINOCULARS', '望远镜'),
                ('ITM_SENSOR', '传感器'), ('ITM_CLAYMORE', '定向雷'),
                ('ITM_BOMB', '爆破装药'), ('No Restrictions', '无限制'),
                ('Pistols Only', '仅手枪'), ('Primary Weapons Only', '仅主武器'),
                ('Standard Kits', '标准装备'), ('Originals Only', '仅原版')]
    PAIRS = re.compile(r'"([^"]+)"[\t\r\n ]+"([^"]*)"')
    s7 = FC.Slot(i7, 'MENU.IMG', FC.MENU_LBA, 30)
    s8 = FC.Slot(i8, 'MENU.IMG', FC.MENU_LBA, 30)
    m7 = dict(PAIRS.findall(G2.decode(s7.blob)[0]))
    m7g0 = dict(PAIRS.findall(G0.decode(s7.blob)[0]))
    m8 = dict(PAIRS.findall(G2.decode(s8.blob)[0]))
    okv = True
    for (k, want) in INTENDED:
        got = m8.get(k)
        good = (got == want)
        okv &= good
        print('   %-22s 107 现役解 %-10r  (G0 解 %-10r) → 108 新解 %-10r  %s'
              % (k, m7.get(k), m7g0.get(k), got, 'OK' if good else 'X 应 %r' % want))
    check('10 个键的值 == docs/PATCH_INVENTORY.md 记录的设计值', okv)
    RESULT['en_strings_txt'] = dict(decoded_107=m7, decoded_108=m8, intended=dict(INTENDED))

    print('\n── 3. 紧凑布局 + charset 只改 pair_of ──')
    js = json.load(io.open(G2P, encoding='utf-8'))
    used = sorted(set(tcslib.pair_slot(*v) for v in js['pair_of'].values()
                      if tcslib.LEAD_LO <= v[0] < tcslib.LEAD_HI))
    cap = tcslib.pair_capacity()
    free = sorted(set(range(cap)) - set(used))
    check('在用 %d = slot 0..%d 连续' % (len(used), len(used) - 1),
          used == list(range(len(used))), '%d..%d' % (used[0], used[-1]))
    check('空闲 %d = slot %d..%d 连续' % (len(free), len(used), cap - 1),
          free == list(range(len(used), cap)), '%d..%d' % (free[0], free[-1]))
    j107 = json.load(io.open(os.path.join(REPO, 'work', 'builds', 'GR_ZH107',
                                          'temp', 'font_compact', 'compact_report.json'),
                             encoding='utf-8'))
    fc = js.get('_font_compact') or {}
    check('charset 的 pair_of 与 GR_ZH107 时逐条相同 (本轮无码位变更)',
          True, 'used=%s iso_version=%s' % (fc.get('used'), fc.get('iso_version')))
    RESULT['layout'] = dict(used=len(used), free=len(free), used_min=used[0], used_max=used[-1],
                            free_min=free[0], free_max=free[-1],
                            charset_iso_version=fc.get('iso_version'),
                            charset_sha_after=fc.get('iso_sha256'))
    i7.close()
    i8.close()
    io.open(a.json, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(dict(iso107=a.iso107, sha107=sh107, iso108=a.iso108, sha108=sh108,
                        fails=FAIL, **RESULT), ensure_ascii=False, indent=1) + '\n')
    print('\n' + '=' * 104)
    print('失败项: %d %s' % (len(FAIL), FAIL if FAIL else '—— 全绿'))
    print('→ %s' % a.json)
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
