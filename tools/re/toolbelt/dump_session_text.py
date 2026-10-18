# -*- coding: utf-8 -*-
r"""dump_session_text.py — 把一个会话里所有长文本字段倒出来（最笨但最可靠）

用法: python dump_session_text.py <会话id前缀> [最小长度]
　　　python dump_session_text.py 8721003e
输出: work/temp/sessdump/<id>/NNN_len.txt + 控制台清单
"""
import io
import json
import os
import re
import sys
import zstandard as zstd

SESS = os.path.join(os.environ['USERPROFILE'], '.dsh', 'sessions')
OUTROOT = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\temp\sessdump'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

pref = sys.argv[1] if len(sys.argv) > 1 else '8721003e'
minlen = int(sys.argv[2]) if len(sys.argv) > 2 else 3000

# 找会话文件
target = None
for root, _d, names in os.walk(SESS):
    if pref in root:
        for n in names:
            if n.endswith('.jsonl.zstd'):
                target = os.path.join(root, n)
if not target:
    print('✗ 找不到会话 %s' % pref)
    sys.exit(1)
print('会话文件: %s' % target)

dctx = zstd.ZstdDecompressor()
raw = dctx.stream_reader(open(target, 'rb')).read().decode('utf-8', 'replace')
print('解压后 %.1f MB, %d 行' % (len(raw) / 1e6, len(raw.splitlines())))

# 正则抠所有 "text":"..."
TEXT_RE = re.compile(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"')
chunks = []
for m in TEXT_RE.finditer(raw):
    s = m.group(1)
    try:
        s = json.loads('"' + s + '"')
    except Exception:
        pass
    if len(s) >= minlen:
        chunks.append(s)

# 也抠 arguments 字符串里的 content
ARG_RE = re.compile(r'"arguments"\s*:\s*"((?:[^"\\]|\\.)*)"')
for m in ARG_RE.finditer(raw):
    try:
        o = json.loads(json.loads('"' + m.group(1) + '"'))
    except Exception:
        continue
    if isinstance(o, dict):
        for k in ('content', 'contents', 'text'):
            v = o.get(k)
            if isinstance(v, str) and len(v) >= minlen:
                chunks.append(v)

# 去重 + 排序
seen = set()
uniq = []
for c in chunks:
    h = hash(c)
    if h in seen:
        continue
    seen.add(h)
    uniq.append(c)
uniq.sort(key=len, reverse=True)

out = os.path.join(OUTROOT, pref)
os.makedirs(out, exist_ok=True)
print('')
print('=== 长文本 %d 段（≥%d 字符）===' % (len(uniq), minlen))
for i, c in enumerate(uniq[:25]):
    head = c.strip().splitlines()[0][:90] if c.strip() else ''
    p = os.path.join(out, '%03d_%d.txt' % (i, len(c)))
    io.open(p, 'w', encoding='utf-8').write(c)
    print('  #%-2d %8d 字符  %-4s 「%s」' % (i, len(c), 'md' if c.lstrip().startswith('#') else '?', head))
print('')
print('输出: %s' % out)
