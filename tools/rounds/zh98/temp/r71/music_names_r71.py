# -*- coding: utf-8 -*-
r"""music_names_r71.py — A 类证据: 9 条空标题在 **GR_ZH114** 的 10 份 SFXML 副本里到底是什么。

独立重跑 (不引用 round68 的结论): 逐条打印
  · 10 份副本里该 item 的 name 属性原始字节 + zh 字符集解码
  · 注入目标 (MENU.IMG#283) 里这 9 个 item 的 pic= / <text> / <soundname>
⇒ 判据: 是不是"音乐"分组 + 原版 EN/IT 到底是不是空的。
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import tcslib as T                                               # noqa: E402
import dump_containers as DC                                     # noqa: E402
import font_usage as FU                                          # noqa: E402
from inject_text_csv import parse_xml_attrs                      # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH114', 'GR_ZH114.iso')
OUT = os.path.join(HERE, 'music_names_r71.txt')
IDX = list(range(45, 54))          # A0045..A0053


def main():
    iso = T.Iso(ISO)
    cs = T.Charset()
    copies = DC.sfxml_copies_of(FU.build_container_list(iso))
    got = []
    for c in copies:
        blob, _raw = FU.container_blob(iso, c['c'])
        got.append((DC.cont_name(c['c']), c['lang'], c['role'], parse_xml_attrs(blob)))
    L = ['# 源盘 = GR_ZH114.iso (sha %s)' % T.sha256_file(ISO)[:16],
         '# A0045..A0053 (9 条空标题) 在 10 份 SFXML 副本里的 name 属性',
         '']
    for k in IDX:
        L.append('A%04d' % k)
        for (name, lang, role, attrs) in got:
            v = attrs[k - 1][3]
            L.append('   %-40s lang=%-6s role=%-8s raw=%-30s latin1=%-14r zh=%r'
                     % (name, lang, role, v.hex() or '(空)', v.decode('latin-1'),
                        cs.decode(v)[0]))
    # 注入目标那份的 XML 窗口 + 所属 studio + 前后邻里
    tgt = [c for c in copies if c['role'] == 'zh-main'][0]
    blob, _raw = FU.container_blob(iso, tgt['c'])
    at = parse_xml_attrs(blob)
    off = at[44][2]
    L.append('')
    L.append('# 注入目标 %s 里 A0044..A0053 的原始窗口 (latin-1) —— '
             '看 studio / group / item 的 pic= 与 <soundname>' % DC.cont_name(tgt['c']))
    L.append(blob[off - 60:off + 1560].decode('latin-1'))
    L.append('')
    L.append('# 全表里 text_zh 为空的条目 (自证: 只有这 9 条)')
    import csv
    p = os.path.join(REPO, 'work', 'builds', 'GR_ZH114', 'text',
                     'GR_ZH114_text_sf_titles.csv')
    with io.open(p, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    empty = [r['id'] for r in rows if r['text_zh'] == '']
    L.append('   空 text_zh 的 id: %s  (共 %d 条 / 全表 %d 条)'
             % (', '.join(empty), len(empty), len(rows)))
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(L) + '\n')
    print('wrote', OUT)
    iso.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
