# -*- coding: utf-8 -*-
r"""txt_audit_xml.py —— EN_SPECIAL_FEATURE.XML 的**全口径**逐节点长度审计（补 txt_audit.py 的 69/94 缺口）。

口径（三个并列，全部逐条给出）：
  A. `<text>…</text>`   —— 用 DOTALL 非贪婪匹配，**含正文里嵌套标记的那 25 条**（txt_audit.py 的
                            `<text>([^<]*)</text>` 会漏掉它们 ⇒ 只有 69 条，本脚本补齐到 94 条）
  B. `name="…"`         —— 元素属性（界面标题/关卡名），已被汉化改写（如 name="Soldiers" → 中文）
  C. RE_NODE `>…<`      —— migrate_legacy / LEAD §14 使用的最宽口径（作为交叉核对）
写入 work\builds\GR_TXT\audit\A_xml_audit.json + A_xml_top_growth.csv
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
OUT = os.path.join(ROOT, 'work', 'builds', 'GR_TXT', 'audit')
sys.path.insert(0, os.path.join(ROOT, 'tools', 'text_csv'))
import tcslib as T                                                       # noqa: E402

ISOS = (('EN_TRUE', r"third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso"),
        ('ZH113b', r"work\builds\GR_ZH113b\GR_ZH113b.iso"),
        ('CVAR04', r"work\builds\GR_CVAR\CVAR_04_text.iso"))
TEXT_RE = re.compile(rb'<text>(.*?)</text>', re.S)
NAME_RE = re.compile(rb'name="([^"]*)"')
NODE_RE = re.compile(rb'>([^<>]{2,400})<')


def load(rel):
    iso = T.Iso(os.path.join(ROOT, rel))
    e = iso.img_entry(T.MENU_LBA, 283)
    raw = iso.read(e['iso_off'], e['stored'])
    blob = b''.join(s[0] for s in T.lzo_subs(raw))
    iso.close()
    return blob


def dec(b):
    try:
        return b.decode('gbk')
    except UnicodeDecodeError:
        return b.decode('gbk', 'replace')


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    blobs = {t: load(r) for (t, r) in ISOS}
    out = {}
    for label, rx in (('text', TEXT_RE), ('name', NAME_RE), ('node', NODE_RE)):
        en = [m.group(1) for m in rx.finditer(blobs['EN_TRUE'])]
        zh = [m.group(1) for m in rx.finditer(blobs['ZH113b'])]
        cv = [m.group(1) for m in rx.finditer(blobs['CVAR04'])]
        n = min(len(en), len(zh))
        rows = [dict(i=i, len_en=len(en[i]), len_zh=len(zh[i]), d=len(zh[i]) - len(en[i]),
                     en=dec(en[i])[:80].replace('\n', '\\n'),
                     zh=dec(zh[i])[:80].replace('\n', '\\n'))
                for i in range(n)]
        tot_en = sum(r['len_en'] for r in rows)
        tot_zh = sum(r['len_zh'] for r in rows)
        rec = dict(n_en=len(en), n_zh=len(zh), n_cvar=len(cv),
                   zh_eq_cvar=(len(zh) == len(cv) and
                               all(zh[i] == cv[i] for i in range(min(len(zh), len(cv))))),
                   n_grew=sum(1 for r in rows if r['d'] > 0),
                   n_shrunk=sum(1 for r in rows if r['d'] < 0),
                   n_equal=sum(1 for r in rows if r['d'] == 0),
                   max_grow=max([r['d'] for r in rows] or [0]),
                   max_grow_i=max(rows, key=lambda r: r['d'])['i'] if rows else None,
                   total_en=tot_en, total_zh=tot_zh,
                   glyph_naive_en=tot_en, glyph_naive_zh=tot_zh)
        if rows:
            mg = max(rows, key=lambda r: r['d'])
            rec['max_grow_row'] = mg
        out[label] = rec
        print('[%s] n_en=%d n_zh=%d grew=%d shrunk=%d equal=%d max_grow=%+d  total %d -> %d'
              % (label, len(en), len(zh), rec['n_grew'], rec['n_shrunk'],
                 rec['n_equal'], rec['max_grow'], tot_en, tot_zh))
        if rows:
            mg = max(rows, key=lambda r: r['d'])
            print('      最大增长 #%d: %d -> %d   en=%r  zh=%r'
                  % (mg['i'], mg['len_en'], mg['len_zh'], mg['en'], mg['zh']))
        top = sorted(rows, key=lambda r: -r['d'])[:20]
        with open(os.path.join(OUT, 'A_xml_top_growth_%s.csv' % label), 'w',
                  encoding='utf-8-sig', newline='') as f:
            f.write('idx,len_en,len_zh,grow,en,zh\n')
            for r in top:
                f.write('%d,%d,%d,%d,"%s","%s"\n' % (r['i'], r['len_en'], r['len_zh'],
                                                     r['d'], r['en'].replace('"', "'"),
                                                     r['zh'].replace('"', "'")))
    out['_blob'] = {k: len(v) for k, v in blobs.items()}
    with open(os.path.join(OUT, 'A_xml_audit.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print('[out] %s' % os.path.join(OUT, 'A_xml_audit.json'))


if __name__ == '__main__':
    main()
