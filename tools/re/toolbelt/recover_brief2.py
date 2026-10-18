# -*- coding: utf-8 -*-
r"""recover_brief2.py — 从 DSH 会话里恢复被删除的 work/_briefs/*.md（修正版）

上一版失败原因: 会话 JSONL 里工具调用的 "arguments" 是**一个 JSON 字符串**，
必须先 json.loads 才能拿到 file_path/content。

本版策略（三重兜底）:
  ① 逐行 json.loads → 递归找 "arguments" 字符串 → 再 json.loads → 取 file_path/content
  ② 抓 name == 'write'/'create' 的 tool-call
  ③ 抓超长 assistant 正文里以 '# ' 开头的 markdown（简报正文可能作为最终答复发出）
输出: work/_briefs_recovered/
"""
import io
import json
import os
import sys
import zstandard as zstd

SESS = os.path.join(os.environ['USERPROFILE'], '.dsh', 'sessions')
OUTDIR = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\_briefs_recovered'
WANT_SIZE = {'tooling.md': 80530, 'han_v2_engine.md': 152068,
             'han_v2_method.md': 143663, 'res_ab_16px.md': 60547}
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.makedirs(OUTDIR, exist_ok=True)

files = []
for root, _d, names in os.walk(SESS):
    for n in names:
        if n.endswith('.jsonl.zstd'):
            files.append(os.path.join(root, n))
files.sort(key=lambda p: os.path.getmtime(p), reverse=True)

dctx = zstd.ZstdDecompressor()
best = {}          # name -> (len, content)
cand_msgs = []     # ③ 兜底


def consider(fp, ct, where):
    if not (isinstance(fp, str) and isinstance(ct, str)):
        return
    if '_briefs' not in fp or len(ct) < 800:
        return
    name = os.path.basename(fp.replace('\\', '/'))
    if name not in best or len(ct) > best[name][0]:
        best[name] = (len(ct), ct, where)


def walk(x, where):
    if isinstance(x, dict):
        a = x.get('arguments')
        if isinstance(a, str) and a.lstrip().startswith('{'):
            try:
                o2 = json.loads(a)
                for v in o2.values():
                    walk(v, where)
            except Exception:
                pass
        elif isinstance(a, dict):
            walk(a, where)
        fp = x.get('file_path') or x.get('path')
        ct = x.get('content') or x.get('contents') or x.get('text')
        if fp and isinstance(ct, str):
            consider(fp, ct, where)
        for v in x.values():
            walk(v, where)
    elif isinstance(x, list):
        for v in x:
            walk(v, where)


for p in files:
    try:
        text = dctx.stream_reader(open(p, 'rb')).read().decode('utf-8', 'replace')
    except Exception:
        continue
    sid = os.path.basename(os.path.dirname(p))
    for line in text.splitlines():
        if '_briefs' not in line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        walk(o, sid)
        # ③ 兜底: 行里有超长 markdown 正文
        for m in json.loads('[]') if False else []:
            pass
        if len(line) > 40000:
            for key in ('"text"', '"content"'):
                pass
            try:
                def grab(y):
                    if isinstance(y, str):
                        if len(y) > 40000 and y.lstrip().startswith('# '):
                            cand_msgs.append((sid, y))
                    elif isinstance(y, dict):
                        for v in y.values():
                            grab(v)
                    elif isinstance(y, list):
                        for v in y:
                            grab(v)
                grab(o)
            except Exception:
                pass

print('=' * 70)
print('① / ② 通过 file_path+content 恢复:')
for name, (n, ct, where) in sorted(best.items(), key=lambda kv: -kv[1][0]):
    dst = os.path.join(OUTDIR, name)
    io.open(dst, 'w', encoding='utf-8').write(ct)
    tag = '★大小吻合' if WANT_SIZE.get(name) == n else ('(期望 %s)' % WANT_SIZE.get(name, '?'))
    print('  ✓ %-28s %8d B %-12s 会话 %s' % (name, n, tag, where))

if cand_msgs:
    print('')
    print('③ 通过超长 markdown 正文抓到 %d 段:' % len(cand_msgs))
    for i, (sid, y) in enumerate(sorted(cand_msgs, key=lambda t: -len(t[1]))[:8]):
        head = y.strip().splitlines()[0][:80]
        print('  #%d %8d B  会话 %s  「%s」' % (i, len(y), sid, head))
        io.open(os.path.join(OUTDIR, 'cand_%02d_%s.md' % (i, sid[:8])), 'w', encoding='utf-8').write(y)
print('')
print('输出目录: %s' % OUTDIR)
