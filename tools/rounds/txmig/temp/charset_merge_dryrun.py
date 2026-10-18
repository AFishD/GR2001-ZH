# -*- coding: utf-8 -*-
r"""charset_merge_dryrun.py — ★ **只在内存里**合并 charset 补丁, 供 dry-run 验证补丁自洽

    python work/builds/GR_TXMIG/temp/charset_merge_dryrun.py [--write-sidecar]

做两件事:
  1. 读 `tools/font_pipeline/data/charset_compiled_zh16.json` (受保护路径, **只读**) 与
     `work/builds/GR_TXMIG/charset_pairs_patch.json`, 按 LEAD §15.1 合并:
        · `pair_of` 增加 5 条 (按/时/小/击/✕ ⇒ 0xB9FA..0xB9FE = slot 2345..2349)
        · `codes`  摘掉 4 条 (击 0xB6 / 小 0xB7 / 时 0xB8 / 按 0xB9 —— 抬闸门后它们是前导)
     并断言 `len(pair_of) == 2350` (LEAD §7/§15.1 的目标)。任何一条不满足 ⇒ 非 0 退出。
  2. 把合并结果**另存**到本轮自己的目录 (`temp/charset_merged_pretend.json`) —— 这只是
     "如果几何执行者照补丁合并, charset 应该长这样"的**验证副本**, 给
     `migrate_legacy.py --charset <它> --dry-run` 用。

★ 本脚本**绝不写** `tools/font_pipeline/data/charset_compiled_zh16.json` (几何路 geom2400 的
  受保护路径)。
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
PATCH = os.path.join(REPO, 'work', 'builds', 'GR_TXMIG', 'charset_pairs_patch.json')
OUT = os.path.join(HERE, 'charset_merged_pretend.json')
PAIR_STRIDE, TRAIL_LO, LEAD_LO = 94, 0xA1, 0xA1


def slot(p):
    return (p[0] - LEAD_LO) * PAIR_STRIDE + (p[1] - TRAIL_LO)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--write-sidecar', action='store_true',
                    help='把合并结果写到 temp/charset_merged_pretend.json')
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    cs = json.load(io.open(CHARSET, encoding='utf-8'))
    pt = json.load(io.open(PATCH, encoding='utf-8'))
    po, co = cs['pair_of'], cs['codes']

    # 反查: char → 单字节码 (codes 的键是字, 值是码)
    print('[in ] charset %s' % CHARSET)
    print('      pair_of %d 条 (slot 0..%d) ; codes %d 条'
          % (len(po), max(slot(v) for v in po.values()), len(co)))
    print('      sha256(前) 见报告; 本脚本对它是**只读**')
    before_po, before_co = dict(po), dict(co)

    # ── ① pair_of 增 5 条 ──
    #   ★ ✕ (0xB5) 的**字符名有两种口径**: 补丁文件写 `\ue0b5` (U+E0B5, tcslib 的 PUA 回落名),
    #     而几何执行者合并后的 charset 用的是 `\u2715` (U+2715 MULTIPLICATION X, 真字形)。
    #     同一个逻辑字 ⇒ 只要**该 slot 已被任一别名占据**就算"已合并", 两边不一致时以 charset 为准。
    ALIAS = {'\ue0b5': ('\u2715', '\ue0b5', '\u00d7')}
    add = pt['pair_of_add']
    for ch, p in add.items():
        p = list(p)
        if ch in po:
            if list(po[ch]) != p:
                print('[!!] %r 已在 pair_of 里但值不同: %s ≠ %s' % (ch, po[ch], p))
                return 1
            print('[ok ] %r 已在 pair_of (%s, slot %d) —— 幂等' % (ch, p, slot(p)))
            continue
        hit = next(((al, po[al]) for al in ALIAS.get(ch, ()) if al in po), None)
        if hit:
            al, pal = hit
            if list(pal) != p:
                print('[!!] %r 的别名 %r 已在 pair_of 但 slot 不同: %s ≠ %s'
                      % (ch, al, pal, p))
                return 1
            print('[ok ] %r 的**等价别名** %r 已在 pair_of (%s, slot %d) —— 已合并, 跳过'
                  ' (字符名以 charset 为准)' % (ch, al, pal, slot(pal)))
            continue
        po[ch] = p
        print('[add] pair_of[%r] = %s  ⇒ slot %d  (= 0x%02X%02X)'
              % (ch, p, slot(p), p[0], p[1]))

    # ── ② codes 摘 4 条 ──
    rm = pt['codes_remove']
    by_code = {v: k for k, v in co.items()}
    for ch, code in rm.items():
        if ch in co:
            if co[ch] != code:
                print('[!!] codes[%r] = 0x%02X ≠ 补丁写的 0x%02X' % (ch, co[ch], code))
                return 1
            del co[ch]
            print('[del] codes 摘掉 %r (0x%02X) —— 抬闸门后它是前导, 留着会被编码器写成裸前导'
                  % (ch, code))
        elif code in by_code:
            print('[!!] 0x%02X 在 codes 里挂的是 %r, 不是补丁要摘的 %r'
                  % (code, by_code[code], ch))
            return 1
        else:
            print('[ok ] %r / 0x%02X 已不在 codes 里 —— 幂等' % (ch, code))

    # ── ③ 断言 ──
    bad = []
    if len(po) != 2350:
        bad.append('pair_of = %d ≠ 2350 (LEAD §7/§15.1)' % len(po))
    sl = [slot(v) for v in po.values()]
    if sorted(sl) != list(range(2350)):
        dup = [s for s in set(sl) if sl.count(s) > 1]
        bad.append('slot 不是 0..2349 的一一映射 (重号 %s, min %d max %d, 唯一 %d)'
                   % (dup[:5], min(sl), max(sl), len(set(sl))))
    for ch, p in add.items():
        got = po.get(ch)
        if got is None:
            got = next((po[a] for a in ALIAS.get(ch, ()) if a in po), None)
        if got is None or list(got) != list(p):
            bad.append('pair_of[%r] = %s ≠ 补丁的 %s' % (ch, got, p))
    for ch in rm:
        if ch in co:
            bad.append('codes 里还有 %r' % ch)
    for b in range(0xB6, 0xBA):
        if b in by_code:
            bad.append('codes 里还有 0x%02X = %r' % (b, by_code[b]))
    if bad:
        print('[!!] 合并后不自洽:')
        for x in bad:
            print('     ' + x)
        return 1

    print()
    print('[ok ] 合并自洽: pair_of = %d (slot 0..2349 一一映射) ; codes = %d 条'
          % (len(po), len(co)))
    print('     借槽 5 个: %s' % ', '.join(
        '%s=slot%d' % (ch, slot(p)) for ch, p in sorted(add.items(), key=lambda kv: slot(kv[1]))))
    print('     0..1871 既有条目一个字段都没动: %s'
          % all(list(po[k]) == list(before_po[k]) for k in before_po))
    gone = set(before_co) - set(co)
    if gone == set(rm):
        print('     codes 只少了补丁点名的 4 条: True')
    elif not gone and set(rm) & set(before_co) == set():
        print('     codes 的合并**本脚本读到的快照之前就已完成** (补丁点名的 4 条早已不在) '
              '⇒ 幂等; `codes 0xB6..0xB9 == {}` 已由上面的断言覆盖 ✓')
    else:
        print('     [!!] codes 的变化不是补丁点名的 4 条: 少了 %s / 补丁要摘 %s'
              % (sorted(gone), sorted(rm)))
        return 1
    if a.write_sidecar:
        cs['pair_of'], cs['codes'] = po, co
        cs['_dryrun_merge_note'] = (
            '★ 这是 work/builds/GR_TXMIG/temp/charset_merge_dryrun.py 生成的**验证副本** —— '
            '按 charset_pairs_patch.json (LEAD §15.1) 在内存里合并后的样子。'
            '真正的 charset 由几何执行者写入 tools/font_pipeline/data/charset_compiled_zh16.json; '
            '本文件只用于 migrate_legacy.py --dry-run 的自检。')
        with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(cs, f, ensure_ascii=False, indent=1)
        print('     [out] %s (%d B)' % (OUT, os.path.getsize(OUT)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
