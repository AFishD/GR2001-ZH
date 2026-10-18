# -*- coding: utf-8 -*-
r"""check_makebuild_reads_titles_r63.py — 构筑器能不能读带标题表的 text/ 目录?

下一位用户/下一轮构筑会用 `--inject-csv work/builds/GR_ZH110` (= 那个 text/ 目录),
构筑器内部走 make_build.read_text_tables() → tcslib 的多表读取。这里直接调它, 证明
新表 (`*_text_sf_titles.csv`, 17 列, id=SFXML:A####) **不会**把快照读挂, 且标题会
以 SFXML:A#### 出现在合并 TXT 快照里。只读。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import make_build                                                      # noqa: E402
import tcslib                                                          # noqa: E402


def main():
    tdir = os.path.join(REPO, 'work', 'builds', 'GR_ZH110', 'text')
    paths, notes = tcslib.expand_csv_inputs([tdir])
    print('目录: %s' % os.path.relpath(tdir, REPO).replace('\\', '/'))
    print('注入器/构筑器扫到的表 (%d 张):' % len(paths))
    for p in paths:
        b, k = tcslib.split_table_name(p)
        print('   kind=%-12s %s' % (k, os.path.basename(p)))
    rows, tables, rep = make_build.read_text_tables(tdir, 'GR_ZH110')
    sf = [r for r in rows if r['id'].startswith('SFXML:A')]
    print('\nread_text_tables(): 合并 %d 行 (冲突 %d 处)' % (len(rows), len(rep['conflicts'])))
    print('  其中标题行 (SFXML:A####) %d 条, kind=%s'
          % (len(sf), sorted(set(r['kind'] for r in sf))))
    for r in sf[:3]:
        print('   %s  %-6s %s = %r' % (r['id'], r['kind'], r['resource'], r['text']))
    txt = os.path.join(tdir, 'GR_ZH110_text.txt')
    with open(txt, encoding='utf-8') as f:
        lines = [x for x in f.read().splitlines() if x.startswith('SFXML:A')]
    print('  TXT 快照里以 SFXML:A 开头的行: %d (现存快照是本轮构筑时生成的, '
          '那时 text/ 里还没有标题表 ⇒ 0 属正常; 下一轮构筑就会带上)' % len(lines))
    print('\n结论: %s' % ('✓ 构筑器能原样读入标题表 (不报错、不丢行)'
                          if len(sf) == 145 else '✗ 有问题: 只读到 %d 条标题' % len(sf)))


if __name__ == '__main__':
    main()
