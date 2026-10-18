# -*- coding: utf-8 -*-
r"""recover_brief.py — 从 DSH 会话存档里把"已被删除的文件内容"捞回来

原理: Agent 写文件是通过工具的 arguments 传的 ⇒ 文件正文就在会话 JSONL 的
      tool/call 行里（作为 arguments.content）。会话是 zstd 压缩，所以明文搜索看不到。

本轮目标: 恢复已被清理的
  · work/_briefs/tooling.md        （1080 行工具链简报）
  · 其它 work/_briefs/*.md
输出: 恢复到 work/_briefs_recovered/<文件名>
"""
import io
import json
import os
import re
import sys
import zstandard as zstd

SESS = os.path.join(os.environ['USERPROFILE'], '.dsh', 'sessions')
OUTDIR = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\_briefs_recovered'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.makedirs(OUTDIR, exist_ok=True)

# 想恢复的文件名（出现在 write 的 file_path 里）
WANT = ['_briefs', '.md']

files = []
for root, _d, names in os.walk(SESS):
    for n in names:
        if n.endswith('.jsonl.zstd'):
            files.append(os.path.join(root, n))
files.sort(key=lambda p: os.path.getmtime(p), reverse=True)

dctx = zstd.ZstdDecompressor()
recovered = {}
scanned = 0

for p in files:
    try:
        raw = dctx.stream_reader(open(p, 'rb')).read()
    except Exception:
        continue
    text = raw.decode('utf-8', 'replace')
    scanned += 1
    for line in text.splitlines():
        if '_briefs' not in line or '.md' not in line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        # 深挖找出所有 write 调用的 file_path + content
        def walk(x):
            if isinstance(x, dict):
                fp = x.get('file_path') or x.get('path')
                ct = x.get('content')
                if isinstance(fp, str) and isinstance(ct, str) and '_briefs' in fp and len(ct) > 500:
                    name = os.path.basename(fp.replace('\\', '/'))
                    if name not in recovered or len(ct) > len(recovered[name]):
                        recovered[name] = ct
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(o)

print('扫描 %d 个会话' % scanned)
print('恢复出 %d 个 _briefs 文件:' % len(recovered))
for name, ct in sorted(recovered.items(), key=lambda kv: -len(kv[1])):
    dst = os.path.join(OUTDIR, name)
    io.open(dst, 'w', encoding='utf-8').write(ct)
    print('  ✓ %-42s %8d B  → %s' % (name, len(ct), dst))
if not recovered:
    print('  ✗ 没找到（可能内容不在会话里，或键名不同）')
