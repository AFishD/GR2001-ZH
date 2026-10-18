# -*- coding: utf-8 -*-
r"""r58 探针11: 生成 font_compact.py 里 STALE_MIGRATIONS 清单的**源码片段** (证据哈希全 64 位)。
输出: manifest_block.py.txt (供人粘贴) + manifest_table.txt (验收表)
"""
import hashlib
import io
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
G2P = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
G0, G2 = tcslib.Charset(G0P), tcslib.Charset(G2P)
PAT = (r'^(?:EN|DE|ES|FR|IT)_STRINGS\.RES$', r'^(?:EN|DE|ES|FR|IT)_STRINGS\.TXT$',
       r'^(?:EN|DE|ES|FR|IT)_SPECIAL_FEATURE\.XML$', r'^IGORHELP\.TXT$')
SHA = lambda s: hashlib.sha256(s.encode('utf-8')).hexdigest()


def changed(blob, src, dst):
    text, mp = src.decode(blob)
    n = len(blob)
    out, nchg = [], 0
    for i, ch in enumerate(text):
        a = mp[i]
        b = mp[i + 1] if i + 1 < len(text) else n
        try:
            nb = dst.encode_strict(ch)
        except tcslib.CharsetError:
            continue
        if len(nb) != b - a:
            continue
        if nb != blob[a:b]:
            nchg += len(nb)
            out.append((a, ch, blob[a:b].hex(' '), nb.hex(' ')))
    return text, nchg, out


iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH107', 'GR_ZH107.iso'))
recs = []
for (tag, lba, idx, e) in FC.enumerate_containers(iso):
    if not any(re.match(p, e['name']) for p in PAT):
        continue
    s = FC.Slot(iso, tag, lba, idx)
    t0, chg, det = changed(s.blob, G0, G2)
    t2 = G2.decode(s.blob)[0]
    recs.append(dict(key='%s#%d %s' % (tag, idx, e['name']), name=e['name'], where='%s#%d' % (tag, idx),
                     slot_sha256=hashlib.sha256(s.raw).hexdigest(),
                     stale_sha256=SHA(t0), cur_sha256=SHA(t2),
                     eq=(t0 == t2), chg=chg, det=det, stale=t0, cur=t2))
iso.close()

lines = []
for r in recs:
    role = 'migrate' if r['chg'] else ('current' if not r['eq'] else 'independent')
    lines.append('%s %s chg=%d role=%s' % (r['key'], r['slot_sha256'][:12], r['chg'], role))
print('\n'.join(lines))

mig = [r for r in recs if r['chg']]
cur = [r for r in recs if not r['chg'] and not r['eq']]
print('\n--- migrate 明细 ---')
for r in mig:
    print('%s  (%s)  slot %s\n   stale %s\n   cur   %s\n   changed %d B' %
          (r['key'], r['name'], r['slot_sha256'], r['stale_sha256'], r['cur_sha256'], r['chg']))
    for (a, ch, ob, nb) in r['det'][:20]:
        print('      @%-7d %r %s → %s' % (a, ch, ob, nb))
print('\n--- current 明细 ---')
for r in cur:
    print('%s  slot %s cur %s' % (r['key'], r['slot_sha256'], r['cur_sha256']))

# 生成源码片段
buf = io.StringIO()
for r in mig:
    samp = [x for x in r['stale'].split('\r\n') if any('\u4e00' <= c <= '\u9fff' for c in x)]
    buf.write("            dict(role='migrate', name=%r, where=%r,\n" % (r['name'], r['where']))
    buf.write("                 slot_sha256='%s',\n" % r['slot_sha256'])
    buf.write("                 stale_text_sha256='%s',\n" % r['stale_sha256'])
    buf.write("                 current_text_sha256='%s',\n" % r['cur_sha256'])
    buf.write("                 changed_bytes=%d,\n" % r['chg'])
    buf.write("                 why=%r),\n" %
              ('陈旧码表解出的是**对的**中文/原字, 现役码表解出来已变味; 陈旧→现役 %d 字节'
               % r['chg'] if r['name'] == 'EN_STRINGS.TXT'
               else '陈旧/现役只差 1 个"假汉字"字符 (重音字节撞上对偶码); 重压超槽 ⇒ 走 '
                    'LZO 字面量原位改写'))
buf.write('\n')
for r in cur:
    buf.write("            dict(role='current', name=%r, where=%r,\n" % (r['name'], r['where']))
    buf.write("                 slot_sha256='%s',\n" % r['slot_sha256'])
    buf.write("                 current_text_sha256='%s',\n" % r['cur_sha256'])
    buf.write("                 why='注入器每轮整表重写的语言表/SFXML, 盘上已经是现役码表"), 
    buf.write("(陈旧解是乱码) ⇒ **不能**按陈旧码表重映射'),\n")
io.open(os.path.join(HERE, 'manifest_block.py.txt'), 'w', encoding='utf-8', newline='\n').write(
    buf.getvalue())
print('\n→ manifest_block.py.txt')
