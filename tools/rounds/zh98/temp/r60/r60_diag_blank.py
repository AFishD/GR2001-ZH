# -*- coding: utf-8 -*-
r"""r60_diag_blank.py — 诊断: 为什么"开发访谈 1"测试页整页不显示

假设 H1: 测试文本里含引擎的标记字符 ({ } % 等) ⇒ 解析失败 ⇒ 整页空白
假设 H2: 文本太长/行数太多 ⇒ 超出渲染上限 ⇒ 整页空白
只读: 从 GR_TEST_FONT1 解出那篇 <text>, 统计字符构成 + 与原文对比。
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
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
c = json.load(io.open(CS, encoding='utf-8'))
M = {}
for ch, (b1, b2) in c['pair_of'].items():
    M[(b1, b2)] = ch
for ch, bb in c['codes'].items():
    if isinstance(bb, list):
        M[(bb[0], bb[1])] = ch
    else:
        M[('S', bb)] = ch


def dec(b):
    out = []
    i = 0
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


def get_text(iso_path):
    iso = tcslib.Iso(iso_path)
    spec = tcslib.RES['SFXML']['copies'][0]
    e = iso.img_entry(spec[1], spec[2])
    raw = iso.read(e['iso_off'], e['stored'])
    blob = b''.join(s[0] for s in tcslib.lzo_subs(raw))
    xml = dec(blob)
    texts = [(m.start(), m.group(1), m.group(2)) for m in
             re.finditer(r'<text([^>]*)>(.*?)</text>', xml, re.S)]
    return xml, texts


for tag, p in (('GR_ZH109(原版)', 'work/builds/GR_ZH109/GR_ZH109.iso'),
               ('GR_TEST_FONT1(测试页)', 'work/builds/GR_TEST_FONT1/GR_TEST_FONT1.iso')):
    xml, texts = get_text(p)
    # T0067 = 开发访谈 1: 按**内容**匹配 (解码后位置 ≠ blob 偏移)
    t = None
    for x in texts:
        if ('开发手记' in x[2]) or ('字库测试页' in x[2]) or ('开发访谈' in x[2]):
            t = x
            break
    if not t:
        print('%s: 找不到目标 text' % tag); continue
    body = t[2]
    print('=' * 76)
    print('%s : 开发访谈 1 正文 %d 字符' % (tag, len(body)))
    print('  前 120 字: %s' % body[:120].replace('\n', ' '))
    print('  末 60 字: ...%s' % body[-60:].replace('\n', ' '))
    print('  ★ 标记字符统计:')
    for ch in ('{', '}', '%', '\\', '|', '<', '>', '&', '\n', '\t', '\r'):
        n = body.count(ch)
        if n:
            print('     %-4r × %d' % (ch, n))
    print('  {br} × %d ; {p} × %d ; 其它 {...} 记号: %s'
          % (body.count('{br}'), body.count('{p}'),
             sorted(set(re.findall(r'\{[^{}]{0,12}\}', body)))[:12]))
    lines = body.split('{br}')
    print('  按 {br} 切分: %d 段; 最长段 %d 字符' % (len(lines), max(len(x) for x in lines)))
    print('  总字符 %d ; 视觉行(每行20字) ≈ %d' % (len(body), len(body) // 20 + len(lines)))
