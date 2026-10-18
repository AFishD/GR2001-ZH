# -*- coding: utf-8 -*-
r"""lead_sfxml_title.py — 决定性实验: 解压各盘的 SFXML, 看标题字节是新编码还是旧编码

结论用途:
  · GR_ZH95 是"开重排 + 带 --inject-csv"构筑的 ⇒ 若它的标题字节 == 它那份 charset 的编码 ⇒ 重排本身没问题,
    round50 的错字是"构筑时没做完整注入/顺序不对"造成的;
  · 若标题字节是旧编码 ⇒ 压缩子流没被重编码 ⇒ 重排路径有漏网。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'diag'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import dump_all_text as DAT  # noqa: E402

TITLE = '何为幽灵'


def enc(cs, s):
    out = bytearray()
    for ch in s:
        if ch in cs['pair_of']:
            out += bytes(cs['pair_of'][ch])
        elif ch in cs.get('codes', {}):
            out.append(cs['codes'][ch])
        else:
            return None
    return bytes(out)


CUR = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                     'charset_compiled_zh16.json'), encoding='utf-8'))
OLD = json.load(io.open(os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r46',
                                     'charset_before_repack.json'), encoding='utf-8'))
pat_cur, pat_old = enc(CUR, TITLE), enc(OLD, TITLE)
print('标题「%s」: 当前编码 %s ; 重排前编码 %s ; 相同? %s'
      % (TITLE, pat_cur.hex(' '), pat_old.hex(' '), pat_cur == pat_old))

DISKS = [('GR_ZH94(重排前)', 'work/builds/GR_ZH94/GR_ZH94.iso'),
         ('GR_ZH95(重排ON)', 'work/builds/GR_ZH95/GR_ZH95.iso'),
         ('GR_ZH97', 'work/builds/GR_ZH97/GR_ZH97.iso'),
         ('GR_ZH98(现役)', 'work/builds/GR_ZH98/GR_ZH98.iso')]
for tag, rel in DISKS:
    p = os.path.join(REPO, rel)
    if not os.path.isfile(p):
        print('  %-16s (缺)' % tag)
        continue
    try:
        d = DAT.gather(p)
    except Exception as e:
        print('  %-16s 提取失败: %s' % (tag, e))
        continue
    blobs = {k: v for k, v in d.items() if isinstance(v, (bytes, bytearray))}
    tot = sum(len(v) for v in blobs.values())
    hit_cur = {k: bytes(v).count(pat_cur) for k, v in blobs.items() if bytes(v).count(pat_cur)}
    hit_old = ({k: bytes(v).count(pat_old) for k, v in blobs.items() if bytes(v).count(pat_old)}
               if pat_old != pat_cur else {})
    print('  %-16s 资源 %d 个 / %d 字节 ; 当前编码命中 %s ; 重排前编码命中 %s'
          % (tag, len(blobs), tot,
             ('%d 个 %s' % (len(hit_cur), list(hit_cur)[:3])) if hit_cur else '0',
             ('%d 个 %s' % (len(hit_old), list(hit_old)[:3])) if hit_old else '0'))
    for k in list(hit_cur)[:2]:
        v = bytes(blobs[k]); i = v.find(pat_cur)
        print('        %s 命中处上下文: %s' % (k, v[max(0, i - 24):i + 24].hex(' ')))
