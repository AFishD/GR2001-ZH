# -*- coding: utf-8 -*-
r"""migrate_defect_scan.py — ★ 非英文语言表的**容量可行性**与**已知缺陷**登记 (只读)

    python tools/re/toolbelt/migrate_defect_scan.py <iso> [--base-gate 0xB1] [--gate 0xBA]
        [--out DIR]

回答 LEAD_CAPACITY_2400 §15.3 的两个问题, 并把结论做成**可复核的账**:

  [1] **容量** —— 抬闸门到 `--gate` 后每份 `*_STRINGS.RES` 要迁移多少处 (每处 +1 B),
      能吃的"陈旧尾巴" (`parse_lang` 的 `used_end` 之后) 有多少 B, 装不装得下,
      以及 IMG 里相邻条目的间距 (扇区对齐余量, **不是**可用空间)。

      ★ 实测结论: EN 两份 + SF 装得下 (尾巴 58,874 / 58,997 / 36,385 B);
        **ES/FR 各两份装不下** —— 尾巴只有 8 B, 而增长 28 / 29 B (差 20 / 21 B)。
        原因是这两张表是**未汉化的原文**, 从未被编辑过 ⇒ 条目数据正好铺满整个 blob。
        IMG 相邻间距只有 10~13 B ⇒ 扩容必须改条目表的 `stored/real` 并搬移后续数据,
        与"最小差异 / 条目表未动"冲突 ⇒ **由 LEAD 重排, 本路不硬撑** (LEAD §13.4)。

  [2] **DE/IT 已知缺陷** —— `T.parse_lang` 解不动这两张表 (既存结构异常) ⇒ 载荷边界不可信
      ⇒ 不能安全改写。逐份给出: 全 blob 裸 `0xB1..0xB9` 计数、解析失败原因、
      `ngroups`/首条目的头字节、以及"若主机语言 = DE/IT 会怎样"的风险说明。

只读, 不改任何文件。产物: `<out>/defect_report.json` + 控制台账。
"""
import argparse
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                       # noqa: E402

LANGS = (('MENU.IMG', T.MENU_LBA), ('GR.IMG', T.GR_LBA))
NAME_FILTER = ('EN_STRINGS.RES', 'ES_STRINGS.RES', 'FR_STRINGS.RES',
               'DE_STRINGS.RES', 'IT_STRINGS.RES')
MIGRATED = ('EN_STRINGS.RES',)          # 本轮已迁移的表 (用于头条对账)
TARGET = ('ES_STRINGS.RES', 'FR_STRINGS.RES')     # §15.3 裁决要补的表
EXCLUDED = ('DE_STRINGS.RES', 'IT_STRINGS.RES')   # §15.3 裁决不动的表


def legacy_walk(data, base_gate, gate):
    """基底闸门语义下的裸 `[base_gate,gate)` 计数 (= legacy_singles / 载荷级口径)。"""
    n, per, i, m = 0, {}, 0, len(data)
    while i < m:
        c = data[i]
        if T.LEAD_LO <= c < base_gate:
            i += 2
            continue
        if base_gate <= c < gate:
            n += 1
            per[c] = per.get(c, 0) + 1
        i += 1
    return n, per


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('--base-gate', default='0xB1')
    ap.add_argument('--gate', default='0xBA')
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)
    base_gate, gate = int(a.base_gate, 16), int(a.gate, 16)
    out = os.path.abspath(a.out or os.path.join(REPO, 'work', 'builds', 'GR_TXMIG',
                                                'temp', 'capacity'))
    os.makedirs(out, exist_ok=True)
    iso = T.Iso(a.iso)
    rows = []
    for (img, lba) in LANGS:
        n_ent = 0
        for i in range(1000):
            e = iso.img_entry(lba, i)
            if not e['name'] or e['name'].startswith('?') or e['off'] == 0:
                break
            n_ent += 1
        for i in range(n_ent):
            e = iso.img_entry(lba, i)
            if e['name'] not in NAME_FILTER:
                continue
            nx = iso.img_entry(lba, i + 1) if i + 1 < n_ent else None
            raw = iso.read(e['iso_off'], e['stored'])
            subs = T.lzo_subs(raw)
            blob = b''.join(s[0] for s in subs) if subs else raw
            rec = dict(img=img, idx=i, name=e['name'], off=e['off'], stored=e['stored'],
                       real=e['real'], decomp=len(blob), n_sub=len(subs),
                       img_gap=((nx['off'] - e['off'] - e['stored'])
                                if (nx and nx['off'] > e['off']) else None),
                       verdict=('已迁移 (§1.4)' if e['name'] in MIGRATED else
                                ('要补 (§15.3)' if e['name'] in TARGET else '明确不动 (§15.3)')))
            rec['raw_n'], rec['raw_per'] = legacy_walk(blob, base_gate, gate)
            rec['ngroups'] = struct.unpack_from('<I', blob, 0)[0]
            rec['head64'] = blob[:64].hex()
            try:
                ents, used = T.parse_lang(blob)
                rec['lang_ok'] = True
                rec['entries'], rec['used'] = len(ents), used
                rec['tail_free'] = len(blob) - used
                pn, pp = 0, {}
                for x in ents:
                    k, p = legacy_walk(x.data, base_gate, gate)
                    pn += k
                    for kk, vv in p.items():
                        pp[kk] = pp.get(kk, 0) + vv
                rec['payload_n'], rec['payload_per'] = pn, pp
                rec['growth'] = pn
                rec['fits'] = bool(pn <= rec['tail_free'])
                rec['deficit'] = max(0, pn - rec['tail_free'])
                rec['tail_bytes'] = blob[used:used + 16].hex()
            except Exception as ex:                                      # noqa: BLE001
                rec['lang_ok'] = False
                rec['why'] = str(ex)[:160]
            rows.append(rec)
    iso.close()

    print('=' * 100)
    print('migrate_defect_scan.py — 非英文语言表: 容量可行性 + 已知缺陷登记 (只读)')
    print('  盘 = %s' % os.path.abspath(a.iso))
    print('  闸门 = 0x%02X → 0x%02X (前导区间 [0xA1,0x%02X))' % (base_gate, gate, gate))
    print('=' * 100)
    print()
    print('[1] 容量: 迁移增长 vs 可吃的"陈旧尾巴" (增长只能吃 used_end 之后的尾巴; 每处 +1 B)')
    print('  %-9s %-4s %-16s %9s %9s %8s %7s %6s %7s %8s %s'
          % ('IMG', '#', 'name', 'real', 'decomp', 'used', '尾巴B', '载荷', '增长', '装得下',
             'IMG间距'))
    for r in rows:
        if r['lang_ok']:
            print('  %-9s %-4d %-16s %9d %9d %8d %7d %6d %7d %8s %s'
                  % (r['img'], r['idx'], r['name'], r['real'], r['decomp'], r['used'],
                     r['tail_free'], r['payload_n'], r['growth'],
                     '✓' if r['fits'] else '✗ 差 %d' % r['deficit'], r['img_gap']))
        else:
            print('  %-9s %-4d %-16s %9d %9d %8s %7s %6s %7s %8s %s'
                  % (r['img'], r['idx'], r['name'], r['real'], r['decomp'], '-', '-', '-',
                     '-', 'LANG✗', r['img_gap']))
    print()
    agg = {}
    for r in rows:
        k = r['name']
        v = agg.setdefault(k, dict(copies=0, payload=0, raw=0, ok=0, fits=None, deficit=0))
        v['copies'] += 1
        v['payload'] += r.get('payload_n', 0)
        v['raw'] += r['raw_n']
        v['ok'] += 1 if r['lang_ok'] else 0
        if r['lang_ok']:
            v['fits'] = r['fits']
            v['deficit'] += r['deficit']
    print('  按表名汇总 (拷件数 / 载荷旧码 / 全 blob 裸码 / LANG 解析 / 槽内吸收):')
    for k in sorted(agg):
        v = agg[k]
        print('    %-18s %d 份 · 载荷 %4d 处 · 全 blob %4d 处 · LANG %s · %s'
              % (k, v['copies'], v['payload'], v['raw'],
                 'OK' if v['ok'] == v['copies'] else '失败 %d/%d' % (v['copies'] - v['ok'],
                                                                    v['copies']),
                 ('槽内吸收 ✓' if v['fits'] else
                  ('★ 装不下: 差 %d B/份 ⇒ 需改 IMG 条目表' % (v['deficit'] // max(1, v['copies']))
                   if v['fits'] is False else '—'))))
    tot_p = sum(r.get('payload_n', 0) for r in rows if r['name'] in TARGET)
    print('    ---- §15.3 要补的 ES+FR 合计 = **%d 处** (LEAD §15.3 估 ≈114); '
          '本轮可迁 = **0 处** (容量硬闸)' % tot_p)
    print()
    print('[2] DE/IT 已知缺陷 (LEAD §15.3: 明确不动)')
    print('  DWARF: `T.parse_lang` 的 `ngroups` 之后逐组读 `{u32 count}` —— 这两张表在组间/条目间')
    print('  失步 ⇒ 把 payload 字节当成了 count 去 unpack, 报"需要 19 亿字节的缓冲区"。')
    for r in rows:
        if r['name'] not in EXCLUDED:
            continue
        print('  --- %s %s #%d ---' % (r['img'], r['name'], r['idx']))
        print('      解压 %d B · ngroups=%d · 全 blob 裸 `0xB1..0x%02X` = **%d 处** %s'
              % (r['decomp'], r['ngroups'], gate - 1, r['raw_n'],
                 {('0x%02X' % k): v for k, v in sorted(r['raw_per'].items())}))
        print('      LANG 解析: **失败** — %s' % r.get('why', '?'))
        print('      head64 = %s' % r['head64'])
        print('      ⇒ 载荷边界不可信 ⇒ **不能**按载荷改写; 盲改有破坏结构/吞字节的风险。')
    print()
    print('  ⚠ 风险说明 (写进交付说明): 若主机语言 = DE/IT, 引擎会去读这两张表;')
    print('    抬闸门到 0x%02X 后表内的 `0xB1..0xB9` 会被当**对偶前导**吃掉后一字节'
          '(整串重配对) ⇒ 界面可能显示 `4 / 0 / ( / P / H` 之类 ASCII 乱码, 甚至更糟。' % gate)
    print('    **本路不修** (既存结构异常, 见上), 只登记; 由 LEAD 决定是否投入解析修复。')

    json.dump(dict(iso=os.path.abspath(a.iso), base_gate=base_gate, gate=gate,
                   tables=rows, summary=agg,
                   target_total=tot_p,
                   target_migratable=0,
                   note='ES/FR 装不下 ⇒ 0 处可迁; DE/IT LANG 解析失败 ⇒ 明确不动 (LEAD §15.3)'),
              io.open(os.path.join(out, 'defect_report.json'), 'w', encoding='utf-8',
                      newline='\n'), ensure_ascii=False, indent=1)
    print()
    print('[out] %s' % os.path.join(out, 'defect_report.json'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
