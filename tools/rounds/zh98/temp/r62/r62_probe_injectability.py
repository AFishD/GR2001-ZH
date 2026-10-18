# -*- coding: utf-8 -*-
r"""r62_probe_injectability.py — SFXML 标题"能不能改成可注入"的实测数据 (只读, 只在内存里试算)。

要回答的三个问题:
  ① 槽位还剩多少余量 (当前压缩帧 vs IMG 条目的 stored 槽);
  ② 等长原位改写 (round51 的做法) 会不会超槽;
  ③ 把标题**改长** (改字数) 要动什么 —— 解压总长必须不变, 增长只能吃
     `</SpecialFeatures>` 之后的陈旧尾巴 (tail_free); 吃不下就得让 blob 变长
     ⇒ 子流切分变 ⇒ 注入器的 repack 直接 assert 失败。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                    # noqa: E402
import inject_text_csv as inj                                          # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
iso = T.Iso(ISO)
cs = T.Charset()
spec = T.RES['SFXML']['copies'][0]
c = inj.Container(iso, 'SFXML', spec, cs)
print('容器      : %s (%s#%d)' % (c.tag, c.img, c.idx))
print('槽 stored : %d B      (IMG 条目表的 stored; 压缩帧必须 <= 它)' % c.slot)
print('解压 blob : %d B      (real=%d)' % (len(c.blob), c.entry['real']))
print('子流      : %d 条, 尺寸 %s' % (len(c.subs), c.sizes))
print('原压缩帧  : %d B  ⇒ 槽内余量 %+d B' % (c.frame_len, c.slot - c.frame_len))
print('有效结束  : used_end=%d (</SpecialFeatures> 之后 = %d B 陈旧尾巴可吸收增长)'
      % (c.used_end, len(c.blob) - c.used_end))

# ── ① 等长原位改写 (round51 口径): 标题字节数不变, 只换字 ──
CJK = '国会最高勋章'
try:
    cs.encode_strict('国会荣誉勋章')
    print('\n[注] 「国会荣誉勋章」在字符集里可编码')
except T.CharsetError as ex:
    print('\n[注] ★ 用户搜的「国会荣誉勋章」**当前字符集根本没有这个字**: %s' % ex)
other = '沙漠风暴任务1'                       # 同样是 11 B 的现成标题 (等长互换)
off = c.blob.find(cs.encode_strict(CJK))
ln0 = len(cs.encode_strict(CJK))
print('[①] 等长试算: %r (off=%d, %d B) ←→ %r (%d B)'
      % (CJK, off, ln0, other, len(cs.encode_strict(other))))

for label, newb in (('等长(只换字)', cs.encode_strict(other)),
                    ('+2 字节', cs.encode_strict(CJK) + cs.encode_strict('！')),
                    ('+30 字节', cs.encode_strict(CJK) + cs.encode_strict('！') * 15)):
    c.edits = [(off, off + ln0, newb, None)]
    try:
        blob2, delta = c.build_blob()
    except SystemExit as ex:
        print('    %-12s Δ=%+d  ⇒ 拒绝: %s' % (label, len(newb) - ln0, ex))
        continue
    frame, n_rep = c.repack(blob2)
    print('    %-12s Δ=%+d  重压子流 %d 条 ⇒ 帧 %d B (槽 %d, 余 %+d) %s'
          % (label, delta, n_rep, len(frame), c.slot, c.slot - len(frame),
             'OK' if len(frame) <= c.slot else '★超槽'))
c.edits = []

# ── ② 改字数到极限: 一次把所有 <item name> 都加长 N 字, 看什么时候吃不下尾巴/超槽 ──
ITEMRE = inj.__dict__.get('ITEM_RE', None)
NAME = __import__('re').compile(rb'name\s*=\s*"([^"]*)"')
TAG = __import__('re').compile(rb'<(item|group|studio)\b([^>]*)>')
spans = []
for m in TAG.finditer(c.blob):
    nm = NAME.search(m.group(2))
    if not nm:
        continue
    val = nm.group(1)
    txt = cs.decode(val)[0]
    if not any('\u4e00' <= ch <= '\u9fff' for ch in txt):
        continue
    spans.append((m.start(2) + nm.start(1), len(val), txt))
print('\n[②] 注入目标里含汉字的 name 属性: %d 个; 把它们每个都加长 N 个汉字 (2N 字节):'
      % len(spans))
for n_extra in (1, 5, 10, 20):
    add = cs.encode_strict('一') * n_extra
    c.edits = [(o, o + ln, add + c.blob[o:o + ln], None) for (o, ln, t) in spans]
    try:
        blob2, delta = c.build_blob()
    except SystemExit as ex:
        print('    +%2d 字/条 (共 %+d B): 拒绝 — %s' % (n_extra, 2 * n_extra * len(spans), ex))
        continue
    frame, n_rep = c.repack(blob2)
    print('    +%2d 字/条 (共 %+d B): 重压 %d 条子流 ⇒ 帧 %d B (槽 %d, 余 %+d) %s'
          % (n_extra, delta, n_rep, len(frame), c.slot, c.slot - len(frame),
             'OK' if len(frame) <= c.slot else '★超槽'))
c.edits = []
print('\n结论(数据见上): 等长原位改写 = 只重压含该属性的子流, 帧几乎不变 ⇒ 安全; '
      '改长 = 吃 tail_free, 且必须重新压缩到 <= 槽; 超了就要动 IMG 条目表 (relocate)。')
iso.close()
