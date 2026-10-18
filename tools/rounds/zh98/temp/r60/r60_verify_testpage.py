# -*- coding: utf-8 -*-
r"""r60_verify_testpage.py — **独立**复核最终测试盘 (不复用补丁脚本的门禁结论)。

对 work/builds/GR_TEST_FONT1/GR_TEST_FONT1.iso:
  ① 目标 <text> 仍在原偏移/原长度 (58985 / 2799), 首行 = 统计行;
  ② 码表 1285 个字**每一个**都在正文里出现, 且**恰好 1 次** (统计行里的重复另计);
  ③ 其余 68 个 <text> 与 GR_ZH109 **逐字节相同**;
  ④ 帧/槽 数字 + 引擎折行视觉行数 (wrap_w=270 模型)。
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                       # noqa: E402
import inject_text_csv as inj                                            # noqa: E402

TEST = os.path.join(REPO, 'work', 'builds', 'GR_TEST_FONT1', 'GR_TEST_FONT1.iso')
REF = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
ITEM = re.compile(rb'<item\b([^>]*)>')
NAME = re.compile(rb'name\s*=\s*"([^"]*)"')

cs = T.Charset()
enc = {}
for ch, bb in cs.enc_pair.items():
    enc[ch] = bytes(bb)
for ch, bb in cs.enc_single.items():
    enc[ch] = bytes((bb,))
chars = sorted(enc, key=lambda c: (enc[c], c))
assert len(chars) == 1285, len(chars)


def blob_of(path):
    iso = T.Iso(path)
    spec = T.RES['SFXML']['copies'][0]
    c = inj.Container(iso, 'SFXML', spec, cs)
    return iso, c


iso, c = blob_of(TEST)
print('=== 最终测试盘 %s' % os.path.basename(TEST))
print('sha256 = %s' % T.sha256_file(TEST))
print('容器 %s = %s#%d 槽 %d B / 帧 %d B (余 %d B) / blob %d B'
      % (c.tag, c.img, c.idx, c.slot, c.frame_len, c.slot - c.frame_len, len(c.blob)))
ok = True

# ① 目标定位
hits = []
for m in ITEM.finditer(c.blob):
    nm = NAME.search(m.group(1))
    if nm and cs.decode(nm.group(1))[0] == '开发访谈 1':
        hits.append(m.start())
assert len(hits) == 1, hits
mo = re.compile(rb'<text>').search(c.blob, hits[0])
mc = re.compile(rb'</text>').search(c.blob, mo.end())
a, b = mo.end(), mc.start()
body = c.blob[a:b]
text = cs.decode(body)[0]
print('① 目标 <text> = [0x%X, 0x%X) 长 %d B (期望 58985 / 2799) %s'
      % (a, b, len(body), '✓' if (a == 58985 and len(body) == 2799) else '✗'))
ok &= (a == 58985 and len(body) == 2799)
segs = T.segments(text)                      # 按 {br}/{p} 切段 (盘上是 ASCII 标记, 不是真换行)
lines = [sg for (_s, _e, sg) in segs]
print('   首行 = %r' % lines[0])
ok &= lines[0] == '字库测试页 全 1285 字 · 每行 24 字'
grid = ''.join(lines[1:])
print('   段落数 %d (首行统计 + %d 行正文); 正文总字符 %d (含尾部空格 %d 个)'
      % (len(lines), len(lines) - 1, len(grid), len(grid) - len(grid.rstrip(' '))))

# ② 逐字点名 (正文里恰好 1 次)
missing = [ch for ch in chars if ch not in grid]
dup = [(ch, grid.count(ch)) for ch in chars if grid.count(ch) > 1]
print('② 码表 1285 字: 正文里缺失 %d 个; 出现 >1 次 %d 个' % (len(missing), len(dup)))
if missing:
    print('   缺: %s' % ''.join(missing[:20]))
if dup:
    print('   多: %s' % ', '.join('%s×%d' % d for d in dup[:10]))
ok &= (not missing) and (not dup)
print('   正文里不同字符数 = %d (非空格 %d, 期望 1285); 多出来的字符 = %r'
      % (len(set(grid)), len(set(grid) - {' '}), sorted(set(grid) - set(chars))))
ok &= len(set(grid) - {' '}) == 1285 and set(grid) - set(chars) <= {' '}

# ③ 其它 <text> 与参考盘逐字节相同
iso2, c2 = blob_of(REF)
e1 = {k: d for (k, _o, _l, d) in T.parse_sfxml(c.blob)}
e2 = {k: d for (k, _o, _l, d) in T.parse_sfxml(c2.blob)}
diff = [k for k in e1 if e1[k] != e2[k]]
print('③ <text> 条数 %d/%d; 与 GR_ZH109 不同的条目 = %s (期望只有 67)'
      % (len(e1), len(e2), diff))
ok &= diff == [67]
# 目标区间外逐字节相同
pre = c.blob[:a] == c2.blob[:a]
suf = c.blob[b:] == c2.blob[b:]
print('   目标区间外: 前缀相同=%s 后缀相同=%s; blob 总长 %d vs %d'
      % (pre, suf, len(c.blob), len(c2.blob)))
ok &= pre and suf and len(c.blob) == len(c2.blob)

# ④ 引擎折行 (wrap_w=270 模型, SFXML 标定值)
nlines = 0
for (_s, _e, seg) in T.segments(text):
    nlines += len(T.wrap_seg(seg, 270)) if seg else 1
print('④ 引擎折行模型 (wrap_w=270): 视觉行 %d 行; 每行最多 %d 字'
      % (nlines, max(len(x) for x in
                     [l for (_s, _e, sg) in T.segments(text) if sg for l in T.wrap_seg(sg, 270)])))
print('   载荷 %d B ≤ 原文 2799 B (空格补齐) ⇒ 偏移/长度不变' % len(body))

iso.close()
iso2.close()
print('\n[独立复核] %s' % ('全部通过 ✓' if ok else '★ 有项目不过'))
sys.exit(0 if ok else 1)
