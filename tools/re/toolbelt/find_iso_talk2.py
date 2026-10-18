# -*- coding: utf-8 -*-
r"""find_iso_talk2.py — 稳健版: 直接对原始行做正则抽取, 不猜 JSON 结构

从 ~/.dsh/sessions/**/session.v4.jsonl.zstd 里找 ISO 结构相关的对话。
做法: 解压 → 逐行 → 命中关键词 → 用正则把该行里所有 "text":"..." 的文本抽出来并反转义。
输出: work/temp/iso_talk2.txt
"""
import io
import json
import os
import re
import sys
import time
import zstandard as zstd

SESS = os.path.join(os.environ['USERPROFILE'], '.dsh', 'sessions')
OUT = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\temp\iso_talk2.txt'
KWS = ['cdvdgen', 'iml2iso', '分区表', '分区', '表头', 'lba', '目录记录', '卷描述符', 'pvd',
       '解包', '封包', '重打包', 'apache', 'iso 结构', 'iso结构', '扇区']
TEXT_RE = re.compile(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.makedirs(os.path.dirname(OUT), exist_ok=True)


def unesc(s):
    try:
        return json.loads('"' + s + '"')
    except Exception:
        return s


files = []
for root, _d, names in os.walk(SESS):
    for n in names:
        if n.endswith('.jsonl.zstd'):
            files.append(os.path.join(root, n))
files.sort(key=lambda p: os.path.getmtime(p), reverse=True)

dctx = zstd.ZstdDecompressor()
out = io.open(OUT, 'w', encoding='utf-8')
sess_with = 0
total = 0

for p in files:
    try:
        raw = dctx.stream_reader(open(p, 'rb')).read().decode('utf-8', 'replace')
    except Exception:
        continue
    sid = os.path.basename(os.path.dirname(p))
    mt = time.strftime('%m-%d %H:%M', time.localtime(os.path.getmtime(p)))
    lines = raw.splitlines()
    picks = []
    for ln, line in enumerate(lines, 1):
        low = line.lower()
        if not any(k in low for k in KWS):
            continue
        txts = [unesc(m) for m in TEXT_RE.findall(line)]
        blob = ' '.join(t.replace('\r', ' ').replace('\n', ' ') for t in txts)
        blob = ' '.join(blob.split())
        if len(blob) < 60:
            continue
        isuser = ('"role":"user"' in line) or ('"role": "user"' in line)
        picks.append((ln, isuser, blob))
    if not picks:
        continue
    sess_with += 1
    total += len(picks)
    out.write('=' * 92 + '\n会话 %s (改于 %s) 命中 %d 行\n文件 %s\n\n' % (sid, mt, len(picks), p))
    print('')
    print('=' * 78)
    print('会话 %s (改于 %s) 命中 %d 行, 其中用户 %d 行' % (
        sid, mt, len(picks), sum(1 for _, u, _ in picks if u)))
    shown = 0
    for ln, isuser, blob in picks:
        tag = 'USER' if isuser else 'other'
        out.write('[行%d %s] %s\n\n' % (ln, tag, blob[:3000]))
        if isuser and shown < 8:
            print('   ★[USER 行%d] %s' % (ln, blob[:500]))
            shown += 1
            # 用户消息里最像"讨论 ISO 结构"的, 多印一点
            if any(k in blob.lower() for k in ('分区', '表头', 'cdvdgen', 'iml2iso', '封包', '解包')):
                print('      …%s' % blob[500:1100])
    out.write('\n')

out.close()
print('')
print('=== 汇总: %d 个会话命中, 共 %d 行 ===' % (sess_with, total))
print('全文: %s' % OUT)
