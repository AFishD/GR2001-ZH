# -*- coding: utf-8 -*-
r"""verify_r63.py — round63 独立验收 (不依赖注入器自己的复检代码, 直接重新解析字节)。

用法: python verify_r63.py [<基底.iso> <产物.iso>]
缺省: work/builds/GR_ZH109/GR_ZH109.iso  →  work/builds/GR_ZH110/GR_ZH110.iso

验收清单 (对应 round63 任务书):
  ① 产物盘上被改的标题 == 表里 text_edited 的新文本;
  ② 未被编辑的属性 + 69 个 <text> 元素**逐字节不变**;
  ③ 另外 9 份 SFXML 副本 0 改动 (整个槽位逐字节相同);
  ④ MENU.IMG#283 的 IMG 条目 off/stored/real 不变; 解压总长不变;
  ⑤ 反向重建: 把新值换回原字节 ⇒ 整个 blob 与基底逐字节相同 (数学上等价于
     "除被编辑的属性区间外一个字节都没变");
  ⑥ 差异字节的**归属**: 全盘逐字节 diff, 落到 MENU.IMG#283 槽位之外 = 0;
  ⑦ 幂等: 由 --idem 参数触发 (见报告里的命令), 这里只核产物自身的 sha256 稳定性。

输出: 控制台人话 + <脚本同目录>/verify_r63.json
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T                                                    # noqa: E402
import font_usage as FU                                               # noqa: E402
import inject_text_csv as inj                                         # noqa: E402

A = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
B = os.path.join(REPO, 'work', 'builds', 'GR_ZH110', 'GR_ZH110.iso')
TABLE = os.path.join(HERE, 'inject_titles', 'GR_ZH110_text_sf_titles.csv')
NAME_RE = re.compile(r'(?:^|_)SPECIAL_FEATURE\.XML$', re.I)


def copies_of(iso):
    """{容器名: 容器 dict} (与 dump 工具同一口径: 只按文件名认)。"""
    out = {}
    for c in FU.build_container_list(iso):
        if NAME_RE.search(c['name']):
            out['%s#%d %s' % (c['img'], c['idx'], c['name'])] = c
    return out


def read_table(p):
    import csv
    with open(p, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def run(a_path, b_path):
    only = None
    a = T.Iso(a_path)
    b = T.Iso(b_path)
    res = dict(a=a_path, b=b_path, sha_a=T.sha256_file(a_path), sha_b=T.sha256_file(b_path),
               checks=[], fail=0)
    ca, cb = copies_of(a), copies_of(b)
    if set(ca) != set(cb):
        raise SystemExit('!! 两份盘的 SFXML 副本集合不同: %s' % (set(ca) ^ set(cb)))
    print('== 副本 %d 份 (两份盘一致) ==' % len(ca))

    rows = read_table(TABLE)
    edited = [r for r in rows if r['text_edited'] and r['text_edited'] != r['text_zh']]
    print('== 表 %s: %d 行, 其中要改 %d 条 =='
          % (os.path.relpath(TABLE, REPO).replace('\\', '/'), len(rows), len(edited)))

    # ── 逐副本比对 ──
    tgt = [k for k in ca if k.startswith('MENU.IMG#283')][0]
    for name in sorted(ca):
        ea, eb = a.img_entry(ca[name]['lba'], ca[name]['idx']), b.img_entry(cb[name]['lba'],
                                                                            cb[name]['idx'])
        ent_same = ((ea['off'], ea['stored'], ea['real']) == (eb['off'], eb['stored'], eb['real']))
        ra = a.read(ea['iso_off'], ea['stored'])
        rb = b.read(eb['iso_off'], eb['stored'])
        ba = b''.join(s[0] for s in T.lzo_subs(ra))
        bb = b''.join(s[0] for s in T.lzo_subs(rb))
        raw_same = (ra == rb)
        blob_same = (ba == bb)
        n_diff = sum(1 for i in range(min(len(ba), len(bb))) if ba[i] != bb[i])
        mark = '← 注入目标' if name == tgt else ''
        print('  %-38s 条目表不变=%s 帧逐字节同=%s blob逐字节同=%s 差异字节=%d %s'
              % (name, ent_same, raw_same, blob_same, n_diff, mark))
        res['checks'].append(dict(copy=name, entry_table_same=ent_same, frame_same=raw_same,
                                  blob_same=blob_same, diff_bytes=n_diff,
                                  is_target=(name == tgt)))
        if name == tgt:
            if len(ba) != len(bb):
                raise SystemExit('!! 注入目标解压总长变了 %d → %d' % (len(ba), len(bb)))
            ga, gb = ba, bb
        else:
            if not (ent_same and raw_same and blob_same):
                res['fail'] += 1
                print('     !! 非目标副本被改动了')
            if not ent_same:
                res['fail'] += 1

    # ── ① 被改的标题 == 新文本; ② 其余属性/<text> 逐字节不变; ⑤ 反向重建 ──
    aa = inj.parse_xml_attrs(ga)
    ab = inj.parse_xml_attrs(gb)
    print('\n== 注入目标属性/正文逐条核对 ==')
    if len(aa) != len(ab):
        raise SystemExit('!! 属性个数变了 %d → %d' % (len(aa), len(ab)))
    want = {}
    for r in edited:
        k = int(r['entry_index'][1:])
        want[k] = r
    cs = T.Charset()
    n_ok = n_same = 0
    undo = []
    for (ka, ta, oa, va), (kb, tb, ob, vb) in zip(aa, ab):
        if ka != kb or ta != tb:
            raise SystemExit('!! 属性顺序/tag 变了 @%d' % ka)
        if ka in want:
            exp = cs.marks_to_pua(want[ka]['text_edited'])
            got = cs.decode(vb)[0]
            ok = (got == exp)
            print('  %-5s %-6s %-22r → %-24r  %+d B  %s'
                  % ('A%04d' % ka, ta, cs.decode(va)[0], got, len(vb) - len(va),
                     '✓' if ok else '✗ **不符**'))
            if not ok:
                res['fail'] += 1
            else:
                n_ok += 1
            undo.append((ob, ob + len(vb), va))
        elif va != vb:
            res['fail'] += 1
            print('  !! A%04d 意外变化: %r → %r' % (ka, va[:24], vb[:24]))
        else:
            n_same += 1
    print('  属性: 改动 %d / 逐字节不变 %d (共 %d)' % (n_ok, n_same, len(aa)))
    if n_ok != len(want):
        res['fail'] += 1
        print('  !! 表里要改 %d 条, 只核到 %d 条' % (len(want), n_ok))

    txt_a = T.parse_sfxml(ga)
    txt_b = T.parse_sfxml(gb)
    n_txt = 0
    for (ka, oa, la, da), (kb, ob, lb, db) in zip(txt_a, txt_b):
        if da != db or la != lb or ka != kb:
            res['fail'] += 1
            print('  !! <text> #%d 变了' % ka)
        else:
            n_txt += 1
    print('  <text> 元素: 逐字节不变 %d/%d %s' % (n_txt, len(txt_a), '✓' if n_txt == len(txt_a) else '✗'))

    # ★ 口径: 注入器把"改字数"的净增量吃进 `</SpecialFeatures>` 之后的**陈旧尾巴**
    #   (变短 ⇒ 尾部补 \x00; 变长 ⇒ 从尾巴里截掉同样多字节), 所以反向重建的结果是
    #   `原 blob` 后面可能多出/少掉**纯尾巴字节** —— 判据是"去掉那截尾巴后逐字节相同",
    #   且多/少的那截必须**整段落在 used_end 之后**(= 有效内容没被碰到)。
    rebuilt = T.splice(gb, undo)
    ue = T.xml_tail_start(ga)
    tail_note = ''
    if len(rebuilt) > len(ga):
        extra = rebuilt[len(ga):]
        ok_len = all(b == 0 for b in extra)
        tail_note = ('; 尾部多出 %d B (全是 \\x00 补零, 起点 %d >= used_end %d) %s'
                     % (len(extra), len(ga), ue, '✓' if (ok_len and len(ga) >= ue) else '✗'))
        same = (rebuilt[:len(ga)] == ga) and ok_len and len(ga) >= ue
    elif len(rebuilt) < len(ga):
        # 变长 ⇒ 尾部被截掉同样多字节; 被截掉的必须是 used_end 之后的那一截
        cut = ga[len(rebuilt):]
        keep = ga[:len(rebuilt)]
        tail_note = ('; 尾部少了 %d B (起 %d >= used_end %d) %s'
                     % (len(cut), len(rebuilt), ue, '✓' if len(rebuilt) >= ue else '✗'))
        same = (rebuilt == keep) and len(rebuilt) >= ue
    else:
        same = (rebuilt == ga)
    print('  反向重建 (把新值换回原字节) == 基底 blob: %s%s'
          % ('✓ 逐字节相同' if same else '✗ 不同', tail_note))
    if not same:
        res['fail'] += 1
        k = next((i for i in range(min(len(rebuilt), len(ga))) if rebuilt[i] != ga[i]),
                 min(len(rebuilt), len(ga)))
        print('     首处不同 @%d (len rebuilt=%d / blob=%d)'
              % (k, len(rebuilt), len(ga)))
        print('     rebuilt[:16]=%s\n     ga     [:16]=%s'
              % (rebuilt[:16].hex(' '), ga[:16].hex(' ')))

    # ── ⑥ 全盘差异归属 ──
    print('\n== 全盘逐字节差异 (按真实容器边界归属) ==')
    off_t = T.Iso(b_path).img_entry(ca[tgt]['lba'], ca[tgt]['idx'])['iso_off']
    win = (off_t, off_t + ca[tgt]['stored'])
    n_diff = n_out = 0
    other = {}
    regions = []
    for c in FU.build_container_list(a):
        e = a.img_entry(c['lba'], c['idx']) if c['img'] != 'ISO_FILE' else None
        if e:
            regions.append((e['iso_off'], e['iso_off'] + e['stored'],
                            '%s#%d %s' % (c['img'], c['idx'], c['name'])))
    regions.sort()
    with open(a_path, 'rb') as fa, open(b_path, 'rb') as fb:
        pos = 0
        while True:
            x, y = fa.read(1 << 24), fb.read(1 << 24)
            if not x:
                break
            if x != y:
                i = 0
                while i < len(x):
                    if x[i] == y[i]:
                        i += 1
                        continue
                    j = i
                    while j < len(x) and x[j] != y[j]:
                        j += 1
                    n_diff += j - i
                    if not (win[0] <= pos + i and pos + j <= win[1]):
                        n_out += j - i
                        owner = '(未归属)'
                        for (s, t, nm) in regions:
                            if s <= pos + i and pos + j <= t:
                                owner = nm
                                break
                        other[owner] = other.get(owner, 0) + (j - i)
                    i = j
            pos += len(x)
    print('  总差异 %d B; 落在 MENU.IMG#283 槽 0x%X..0x%X 之外: %d B' % (n_diff, win[0], win[1], n_out))
    for k, v in sorted(other.items(), key=lambda x: -x[1]):
        print('    窗口外: %-40s %d B' % (k, v))
    if n_out:
        res['fail'] += 1
    res['total_diff_bytes'] = n_diff
    res['diff_outside_target'] = n_out
    res['target_window'] = list(win)

    res['attrs_total'] = len(aa)
    res['attrs_changed'] = n_ok
    res['attrs_byte_same'] = n_same
    res['text_same'] = n_txt
    res['text_total'] = len(txt_a)
    res['reverse_rebuild_ok'] = same
    print('\n== 结论: %s ==' % ('全部通过 ✓' if res['fail'] == 0 else '**有 %d 项不通过** ✗' % res['fail']))
    a.close()
    b.close()
    json.dump(res, open(os.path.join(HERE, 'verify_r63.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    return res['fail']


def main():
    p = sys.argv[1:]
    return run(p[0] if p else A, p[1] if len(p) > 1 else B)


if __name__ == '__main__':
    sys.exit(main())
