# -*- coding: utf-8 -*-
r"""round56 验收 C: **逐字复核** GR_ZH106 的文本与 GR_ZH105 **完全一致** (只读)。

三件事:
  ① SFXML 的 `name=` 属性 (含 123 个中文标题) + `<text>` 元素:
       旧 charset 解 GR_ZH105 的字节  vs  新 charset 解 GR_ZH106 的字节  ⇒ 必须逐字相同;
  ② LANG 两份副本的全部 2232 条正文: 同上;
  ③ 特别列出 round51 出过事的那些标题 (何为幽灵？/ 定向炸药 / MP5 冲锋枪 …) 作人眼证据。

用法: python verify_text_same.py <old.iso> <old_charset.json> <new.iso> <new_charset.json>
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                        # noqa: E402

NAME = re.compile(rb'name\s*=\s*"([^"]*)"')
ITEM = re.compile(rb'<(studio|item|group)\b([^>]*)>')
TEXTEL = re.compile(rb'<text>([^<]*)</text>')


def blob_of(iso, res_key, copy=0):
    spec = tcslib.RES[res_key]['copies'][copy]
    e = iso.img_entry(spec[1], spec[2])
    raw = iso.read(e['iso_off'], e['stored'])
    return b''.join(s[0] for s in tcslib.lzo_subs(raw))


def sfxml_attrs(blob, cs):
    out = []
    for m in ITEM.finditer(blob):
        nm = NAME.search(m.group(2))
        if nm:
            out.append((m.start(2) + nm.start(1), cs.decode(nm.group(1))[0]))
    return out


def sfxml_texts(blob, cs):
    return [cs.decode(m.group(1))[0] for m in TEXTEL.finditer(blob)]


def lang_texts(blob, cs):
    ents, _ = tcslib.parse_lang(blob)
    return [(e.g, e.i, cs.decode(e.data)[0]) for e in ents]


def main():
    old_iso_p, old_cs_p, new_iso_p, new_cs_p = sys.argv[1:5]
    cs_old, cs_new = tcslib.Charset(old_cs_p), tcslib.Charset(new_cs_p)
    io_, in_ = tcslib.Iso(old_iso_p), tcslib.Iso(new_iso_p)
    bad = 0

    print('=' * 78)
    print('逐字复核  %s (旧 charset %s)' % (os.path.basename(old_iso_p),
                                            os.path.basename(old_cs_p)))
    print('      vs  %s (新 charset %s)' % (os.path.basename(new_iso_p),
                                            os.path.basename(new_cs_p)))
    print('=' * 78)
    # ---- ① SFXML ----
    b1, b2 = blob_of(io_, 'SFXML'), blob_of(in_, 'SFXML')
    a1, a2 = sfxml_attrs(b1, cs_old), sfxml_attrs(b2, cs_new)
    print('SFXML: %d 字节 → %d 字节; name 属性 %d → %d' % (len(b1), len(b2), len(a1), len(a2)))
    if len(a1) != len(a2):
        print('  ✗ name 属性个数不同'); bad += 1
    diff = [(x, y) for (o1, x), (o2, y) in zip(a1, a2) if x != y]
    cn1 = [x for _o, x in a1 if any('\u4e00' <= c <= '\u9fff' for c in x)]
    print('  含中文属性 %d 个 (旧) ; 逐字不同的 %d 个' % (len(cn1), len(diff)))
    for (x, y) in diff[:10]:
        print('    ✗ %r → %r' % (x, y))
    bad += len(diff)
    t1, t2 = sfxml_texts(b1, cs_old), sfxml_texts(b2, cs_new)
    dt = [(x, y) for x, y in zip(t1, t2) if x != y]
    print('  <text> 元素 %d → %d; 逐字不同的 %d 个' % (len(t1), len(t2), len(dt)))
    for (x, y) in dt[:5]:
        print('    ✗ %r → %r' % (x[:40], y[:40]))
    bad += len(dt)
    print('  ★ round51 出过事的标题 (人眼证据):')
    for key in ('何为幽灵', '定向炸药', 'MP5 冲锋枪', 'M249 班用机枪', '银星勋章',
                '奥萨泽', '沙漠风暴', '士兵', '专家1'):
        olds = [x for _o, x in a1 if key in x]
        news = [x for _o, x in a2 if key in x]
        flag = '✓' if olds == news and olds else ('✗' if olds else '·')
        print('    %s %-14s %r' % (flag, key, (news[0] if news else '(无)')))
        if olds != news:
            bad += 1
    # ---- ② LANG ×2 ----
    for copy in (0, 1):
        l1, l2 = blob_of(io_, 'LANG', copy), blob_of(in_, 'LANG', copy)
        e1, e2 = lang_texts(l1, cs_old), lang_texts(l2, cs_new)
        d = [(a, b) for a, b in zip(e1, e2) if a != b]
        print('LANG 副本 %d: %d 字节 → %d 字节; 条目 %d → %d; 正文不同的 **%d** 条'
              % (copy, len(l1), len(l2), len(e1), len(e2), len(d)))
        for (a, b) in d[:5]:
            print('    ✗ G%03d.I%03d %r → %r' % (a[0] + 1, a[1], a[2][:30], b[2][:30]))
        bad += len(d)
    io_.close(); in_.close()
    print('')
    print('结论: %s (差异 %d 处)' % ('★ 全部逐字相同 ✓' if bad == 0 else '✗ 有差异', bad))
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
