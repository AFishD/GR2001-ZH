# -*- coding: utf-8 -*-
r"""r62_diff_decoders.py — 为什么 lead 的 recon 数出 28, 本轮的验收数出 27?

两处口径差 (只影响**个别**标题):
  · lead 的 r62_recon_titles.py: 在**整块解出的文本**上跑正则, 解码器 ``dec()``
    **先试单字节码** ``('S', x)``, 再试对偶 ⇒ 0xA1..0xB0 里"既是单字节码又是对偶 lead"
    的字节会被读成单字节;
  · tcslib.Charset.decode (= 引擎口径, 注入器/表口径): **对偶优先** (LEAD_LO..LEAD_HI)。
本脚本把两边的标题串逐个比出来, 并各自去旧 13 张表里搜 ⇒ 指出差的那 1 个是哪个。
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                    # noqa: E402
import font_usage as FU                                               # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
TXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')

# ── lead 的解码器 (原样照抄 r62_recon_titles.py) ──
c = json.load(io.open(CS, encoding='utf-8'))
M = {}
for ch, (b1, b2) in c['pair_of'].items():
    M[(b1, b2)] = ch
for ch, bb in c['codes'].items():
    if isinstance(bb, list):
        M[(bb[0], bb[1])] = ch
    else:
        M[('S', bb)] = ch


def dec_lead(b):
    out, i = [], 0
    while i < len(b):
        x = b[i]
        if x < 0x80:
            out.append(chr(x)); i += 1
        elif ('S', x) in M:
            out.append(M[('S', x)]); i += 1
        elif i + 1 < len(b) and (b[i], b[i + 1]) in M:
            out.append(M[(b[i], b[i + 1])]); i += 2
        else:
            out.append('\u00b7'); i += 1
    return ''.join(out)


cs = T.Charset()
iso = T.Iso(ISO)
spec = T.RES['SFXML']['copies'][0]
e = iso.img_entry(spec[1], spec[2])
blob = b''.join(s[0] for s in T.lzo_subs(iso.read(e['iso_off'], e['stored'])))

# 同一批属性: 两边都按 <(item|group|studio) … name="…"> 抓
ITEM = re.compile(rb'<(item|group|studio)\b([^>]*)>')
NAME = re.compile(rb'name\s*=\s*"([^"]*)"')
lead_titles, mine = [], []
for m in ITEM.finditer(blob):
    nm = NAME.search(m.group(2))
    if not nm:
        continue
    val = nm.group(1)
    a = dec_lead(val)
    b = cs.decode(val)[0]
    if not re.search(r'[\u4e00-\u9fff]', a) and not re.search(r'[\u4e00-\u9fff]', b):
        continue
    lead_titles.append(dict(tag=m.group(1).decode(), attr='name', n=len(val),
                            off=m.start(2) + nm.start(1), lead=a, mine=b))
# lead 的 recon 先把**整块**解成文本再正则 ⇒ 偏移/串可能再差一点, 这里也照做一遍
xml_lead = dec_lead(blob)
lead_titles2 = [t for t in (m.group(2) for m in
                            re.finditer(r'<(item|group|studio)\b[^>]*?name="([^"]*)"', xml_lead))
                if re.search(r'[\u4e00-\u9fff]', t)]
print('# 属性数 (字节正则, 含汉字): %d / lead 写法 (整块解文本再正则): %d'
      % (len(lead_titles), len(lead_titles2)))

blobs = dict((f, io.open(os.path.join(TXT, f), encoding='utf-8-sig', errors='replace').read())
             for f in sorted(os.listdir(TXT)) if f.endswith('.csv'))
dl = [t for t in lead_titles if t['lead'] != t['mine']]
print('# 两种解码结果**不同**的标题: %d 个' % len(dl))
for t in dl:
    hl = [f for f, b in blobs.items() if t['lead'] in b]
    hm = [f for f, b in blobs.items() if t['mine'] in b]
    print('   off=%-7d n=%2d lead=%r  →  在旧表: %s' % (t['off'], t['n'], t['lead'], hl))
    print('   %-18s tcslib=%r  →  在旧表: %s' % ('', t['mine'], hm))
    print('    字节: %s' % blob[t['off']:t['off'] + t['n']].hex(' '))

n_lead = sum(1 for t in lead_titles if any(t['lead'] in b for b in blobs.values()))
n_mine = sum(1 for t in lead_titles if any(t['mine'] in b for b in blobs.values()))
print('\n# 旧 13 张表的命中数: lead 口径 %d / tcslib(引擎) 口径 %d   (总 %d)'
      % (n_lead, n_mine, len(lead_titles)))
iso.close()
