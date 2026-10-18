# -*- coding: utf-8 -*-
r"""find_iso_talk.py — 从 DSH 会话存档里挖出"ISO 结构/分区/封包"相关的对话

背景: DSH 会话是 ~/.dsh/sessions/<ws>/<uuid>/session.v4.jsonl.zstd（zstd 压缩 JSONL）
      ⇒ 自带搜索扫不到明文。本脚本解压后按消息粒度搜索。

重点输出:
  ① **用户自己说的话**（role=user 且命中关键词）—— 这是最想找的"当年怎么讨论的"
  ② 助手给出的结论性片段
用法: python find_iso_talk.py
输出: work/temp/iso_talk.txt（全文）+ 控制台摘要
"""
import io
import json
import os
import sys
import time

import zstandard as zstd

SESS = os.path.join(os.environ['USERPROFILE'], '.dsh', 'sessions')
OUT = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\temp\iso_talk.txt'
KWS = ['cdvdgen', 'iml2iso', '分区', '表头', 'lba', '目录记录', '卷描述符', 'pvd',
       '解包', '封包', '重打包', 'apache', 'iso 结构', 'iso结构', '扇区', '体积描述']
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.makedirs(os.path.dirname(OUT), exist_ok=True)


def dig_text(x, depth=0):
    """从任意 JSON 结构里尽量抠出文本"""
    if depth > 6:
        return ''
    if isinstance(x, str):
        return x
    if isinstance(x, list):
        return ' '.join(dig_text(i, depth + 1) for i in x)
    if isinstance(x, dict):
        parts = []
        for k, v in x.items():
            if k in ('text', 'content', 'message', 'parts', 'value', 'arguments', 'input'):
                parts.append(dig_text(v, depth + 1))
        return ' '.join(parts)
    return ''


files = []
for root, _d, names in os.walk(SESS):
    for n in names:
        if n.endswith('.jsonl.zstd'):
            files.append(os.path.join(root, n))
files.sort(key=lambda p: os.path.getmtime(p), reverse=True)

dctx = zstd.ZstdDecompressor()
out = io.open(OUT, 'w', encoding='utf-8')
n_user = 0
n_asst = 0

print('扫描 %d 个会话存档 …' % len(files))
for p in files:
    try:
        raw = dctx.stream_reader(open(p, 'rb')).read().decode('utf-8', 'replace')
    except Exception:
        continue
    sid = os.path.basename(os.path.dirname(p))
    mt = time.strftime('%m-%d %H:%M', time.localtime(os.path.getmtime(p)))
    msgs = []
    for line in raw.splitlines():
        if not any(k in line.lower() for k in KWS):
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        role = ''
        for key in ('role', 'type', 'kind'):
            if isinstance(o.get(key), str):
                role = o[key]
                break
        body = dig_text(o)
        if not body or len(body) < 40:
            continue
        low = body.lower()
        if not any(k in low for k in KWS):
            continue
        msgs.append((role, body))
    if not msgs:
        continue
    us = [m for m in msgs if 'user' in m[0].lower()]
    aas = [m for m in msgs if 'assistant' in m[0].lower()]
    if not us and len(msgs) < 3:
        continue
    out.write('=' * 90 + '\n')
    out.write('会话 %s   (改于 %s)  命中 %d 条 (用户 %d / 助手 %d)\n' % (sid, mt, len(msgs), len(us), len(aas)))
    out.write('文件 %s\n\n' % p)
    print('')
    print('=' * 78)
    print('会话 %s (改于 %s) 用户命中 %d 条' % (sid, mt, len(us)))

    for role, body in (us + aas)[:14]:
        tag = 'USER' if 'user' in role.lower() else 'ASST'
        seg = body.strip().replace('\r', ' ').replace('\n', ' ')
        seg = ' '.join(seg.split())
        if tag == 'USER':
            n_user += 1
        else:
            n_asst += 1
        out.write('[%s] %s\n\n' % (tag, seg[:2600]))
        if tag == 'USER' and len(seg) > 20:
            print('   ★[USER] %s' % seg[:600])
    out.write('\n')

out.close()
print('')
print('=== 汇总: 用户命中 %d 条 / 助手命中 %d 条 ===' % (n_user, n_asst))
print('全文: %s' % OUT)
