# -*- coding: utf-8 -*-
r"""find_session_kw.py — 解压 DSH 会话存档并搜索关键词

DSH 的会话存在 ~/.dsh/sessions/<workspace>/<session-uuid>/session.v4.jsonl.zstd
—— **zstd 压缩的 JSONL** ⇒ 明文搜索扫不到（这就是自带搜索搜不到的原因）。

用法: python find_session_kw.py <关键词1> [<关键词2> ...]
输出: 命中清单打印到 stdout（带上下文），完整结果写 work/temp/session_hits.txt
"""
import io
import json
import os
import re
import sys
import time

import zstandard as zstd

SESS = os.path.join(os.environ['USERPROFILE'], '.dsh', 'sessions')
OUT = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\temp\session_hits.txt'
KWS = [k.lower() for k in (sys.argv[1:] or ['cdvdgen', 'iml2iso'])]
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.makedirs(os.path.dirname(OUT), exist_ok=True)

files = []
for root, _dirs, names in os.walk(SESS):
    for n in names:
        if n.endswith('.jsonl.zstd'):
            files.append(os.path.join(root, n))
files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
print('会话存档共 %d 个 (.jsonl.zstd)' % len(files))
print('关键词: %s' % KWS)
print()

dctx = zstd.ZstdDecompressor()
out = io.open(OUT, 'w', encoding='utf-8')
out.write('关键词: %s\n\n' % KWS)
nhit_sessions = 0
nhit_total = 0

for p in files:
    try:
        raw = dctx.stream_reader(open(p, 'rb')).read()
    except Exception as e:
        print('  ✗ 解压失败 %s (%s)' % (os.path.basename(os.path.dirname(p)), e))
        continue
    try:
        text = raw.decode('utf-8', 'replace')
    except Exception:
        continue
    low = text.lower()
    hits = [k for k in KWS if k in low]
    if not hits:
        continue
    nhit_sessions += 1
    # 会话 id / 工作区 / 时间
    sid = os.path.basename(os.path.dirname(p))
    ws = os.path.basename(os.path.dirname(os.path.dirname(p)))
    mt = time.strftime('%m-%d %H:%M', time.localtime(os.path.getmtime(p)))
    print('=' * 78)
    print('★ 命中 %s' % hits)
    print('   工作区: %s' % ws)
    print('   会话:   %s   (改于 %s, 解压后 %.1f MB)' % (sid, mt, len(raw) / 1e6))
    print('   文件:   %s' % p)
    out.write('=' * 78 + '\n★ %s\n工作区 %s\n会话 %s (改于 %s)\n文件 %s\n' % (hits, ws, sid, mt, p))

    # 逐行 JSON 找命中所在的消息
    shown = 0
    for ln, line in enumerate(text.splitlines(), 1):
        l = line.lower()
        if not any(k in l for k in KWS):
            continue
        role = ''
        body = line
        try:
            o = json.loads(line)
            # 尽量取出角色与文本
            for key in ('role', 'type', 'kind', 'author'):
                if isinstance(o.get(key), str):
                    role = o[key]
                    break
            def dig(x):
                if isinstance(x, str):
                    return x
                if isinstance(x, list):
                    return ' '.join(dig(i) for i in x)
                if isinstance(x, dict):
                    return ' '.join(dig(v) for k, v in x.items() if k in ('text', 'content', 'message', 'parts', 'value'))
                return ''
            body = dig(o) or line
        except Exception:
            pass
        nhit_total += 1
        shown += 1
        if shown <= 6:            # 每个会话最多展示 6 条
            for k in KWS:
                if k in body.lower():
                    i = body.lower().find(k)
                    seg = body[max(0, i - 260):i + 260].replace('\n', ' ')
                    print('   [行%d %s] …%s…' % (ln, role or '?', seg))
                    out.write('[行%d %s] …%s…\n' % (ln, role or '?', seg))
                    break
    out.write('\n')

out.close()
print()
print('=== 汇总: %d 个会话命中, %d 条消息 ===' % (nhit_sessions, nhit_total))
print('完整结果: %s' % OUT)
