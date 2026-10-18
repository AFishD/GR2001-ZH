# -*- coding: utf-8 -*-
r"""p25_testtext.py — 造"测试文案盘"用的表: 把 特别收录 菜单前 6 个分类名各换 1 个字,
让 6 个"本轮补回字形"的字 (若纤终脆膛著) 出现在**一进特别收录就能看到**的位置。

★ 只写 work/builds/GR_ZH95/temp/r46/ 下的副本; 交付盘 GR_ZH95/text 一个字都不动。
"""
import csv
import io
import os
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
SRC = os.path.join(REPO, 'work', 'builds', sys.argv[1] if len(sys.argv) > 1 else 'GR_ZH95', 'text')
DST = os.path.join(HERE, 'test_text' + (('_' + sys.argv[1][-2:]) if len(sys.argv) > 1 else ''))

# id -> (原文, 测试文)  —— 长度一致 (都是 2 个汉字 = 4 字节), 不改变槽位占用
PATCH = {
    'LANG:G058.I739': ('影片', '若片'),
    'LANG:G058.I740': ('设定图', '纤定图'),
    'LANG:G058.I741': ('音乐', '终乐'),
    'LANG:G058.I742': ('武器', '脆器'),
    'LANG:G058.I743': ('奖章', '膛章'),
    'LANG:G058.I744': ('背景', '著景'),
}


def main():
    if os.path.isdir(DST):
        shutil.rmtree(DST)
    os.makedirs(DST)
    seen = set()
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith('.csv') or '_view_' in fn:
            continue
        with io.open(os.path.join(SRC, fn), encoding='utf-8-sig', newline='') as fh:
            recs = list(csv.reader(fh))
        cols = [c.strip() for c in recs[0]]
        i_id, i_ed = cols.index('id'), cols.index('text_edited')
        n = 0
        for r in recs[1:]:
            if not r:
                continue
            rid = r[i_id].strip()
            if rid in PATCH:
                old, new = PATCH[rid]
                assert (r[i_ed] or '').strip() == old, (rid, r[i_ed], old)
                assert len(old.encode()) == len(new.encode()), (rid, old, new)
                r[i_ed] = new
                n += 1
                seen.add(rid)
        with io.open(os.path.join(DST, fn), 'w', encoding='utf-8', newline='') as fh:
            csv.writer(fh, lineterminator='\n').writerows(recs)
        print('  %-34s 改了 %d 行' % (fn, n))
    for fn in os.listdir(SRC):                       # 伴随文件照拷 (注入器要 meta)
        if not fn.endswith('.csv'):
            shutil.copyfile(os.path.join(SRC, fn), os.path.join(DST, fn))
    miss = set(PATCH) - seen
    assert not miss, '这些 id 没找到: %s' % miss
    print('[test-text] 6 个分类名已替换 → %s' % os.path.relpath(DST, REPO))
    print('[test-text] ★ 交付盘 %s 一个字都没动' % os.path.relpath(SRC, REPO))


if __name__ == '__main__':
    main()
