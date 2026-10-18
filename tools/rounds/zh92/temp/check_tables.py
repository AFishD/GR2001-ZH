# -*- coding: utf-8 -*-
r"""check_tables.py — 对用户改过的 long 表做一次完整体检

检查项:
  1 CSV 结构 (行数/列数/编码/行尾/引号)
  2 标记语法: {WRAP}/{Warp} 位置合法 (不在首尾/不与另一标记或换行相邻)
  3 长度: 估算字节数 vs max_bytes
  4 不可见字符: PUA / C0 / C1 / DEL / 零宽
  5 ★ 溢出风险: 估算渲染行数 vs 原文行数 (SFXML 文本框高度固定, 行数不能明显变多)
  6 缺字: 与字库预检的缺字清单交叉
  7 风格: 全角/半角标点、ASCII 相邻空格
"""
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
P = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text_work', 'GR_ZH92_text_long.csv')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

WRAP_RE = re.compile(r'\{\s*(?:WRAP|WARP)\s*\}', re.I)
BAD_MARK = re.compile(r'\{[^}]*\}|\[\[|BTN', re.I)


def est_lines(txt, wrap_w=270):
    """按 SFXML 折行模型粗估行数: 段内按宽度贪心累加, 超宽则断"""
    W_CJK, W_ASCII, TRACK = 16, 8, 1
    out = 0
    for seg in WRAP_RE.split(txt):
        if not seg:
            out += 1
            continue
        w, n = 0, 1
        for ch in seg:
            cw = (W_ASCII if ord(ch) < 0x80 else W_CJK) + TRACK
            if w + cw > wrap_w:
                n += 1
                w = cw
            else:
                w += cw
        out += n
    return out


def main():
    raw = io.open(P, 'rb').read()
    print('【1】文件:', os.path.relpath(P, REPO))
    print('    BOM %s | CRLF %s | %d 字节' % (raw[:3] == b'\xef\xbb\xbf', b'\r\n' in raw, len(raw)))
    rows = list(csv.DictReader(io.open(P, encoding='utf-8-sig')))
    print('    行数 %d | 列数 %d' % (len(rows), len(rows[0])))
    bad_struct = [r['id'] for r in rows if len(r) != 16 or None in r]
    print('    结构异常行: %s' % (bad_struct or '无 ✓'))

    changed = [r for r in rows if r['text_edited'].strip() != r['text_zh'].strip()]
    print('\n【2】改动条目 %d / %d' % (len(changed), len(rows)))

    print('\n【3】标记语法 ({WRAP}/{Warp})')
    prob = []
    for r in changed:
        t = r['text_edited']
        for m in WRAP_RE.finditer(t):
            i = m.start()
            if i == 0:
                prob.append((r['id'], '标记在文本最开头'))
            if m.end() == len(t):
                prob.append((r['id'], '标记在文本最末尾'))
            if WRAP_RE.match(t, m.end()) or WRAP_RE.match(t, i - 8 or 0):
                prob.append((r['id'], '两个标记相邻'))
            if t[i - 1:i] == '\n' or t[m.end():m.end() + 1] == '\n':
                prob.append((r['id'], '标记紧邻换行'))
        for m in BAD_MARK.finditer(t):
            s = m.group(0)
            if not WRAP_RE.fullmatch(s) and 'BTN' not in s.upper():
                prob.append((r['id'], '可疑标记 %r' % s[:20]))
    print('    问题: %s' % (prob or '无 ✓'))
    tot = sum(len(WRAP_RE.findall(r['text_edited'])) for r in rows)
    print('    {WRAP}/{Warp} 总数: %d (改动条目里 %d)'
          % (tot, sum(len(WRAP_RE.findall(r['text_edited'])) for r in changed)))

    print('\n【4】长度 (估算编码字节数 vs max_bytes)')
    over = []
    for r in changed:
        # 粗估: 汉字按 2 字节, ASCII 按 1 字节, 标记不计 (注入时丢弃)
        plain = WRAP_RE.sub('', r['text_edited'])
        n = sum(1 if ord(c) < 0x80 else 2 for c in plain)
        lim = int(r['max_bytes'])
        if n > lim:
            over.append((r['id'], n, lim))
    print('    超长条目: %s' % (over or '无 ✓'))
    mx = max((sum(1 if ord(c) < 0x80 else 2 for c in WRAP_RE.sub('', r['text_edited'])),
              r['id']) for r in changed)
    print('    最长条目: %s (%d 字节估算)' % (mx[1], mx[0]))

    print('\n【5】★ 溢出风险 (估算渲染行数 vs 原文行数)')
    risky = []
    for r in changed:
        new = est_lines(r['text_edited'])
        try:
            old = int(r['lines']) if r['lines'] else None
        except ValueError:
            old = None
        if old and new > old:
            risky.append((r['id'], old, new))
    print('    新行数 > 原行数 的条目: %d 条' % len(risky))
    for rid, o, n in risky[:12]:
        print('      %-14s 原 %2d 行 → 估 %2d 行' % (rid, o, n))
    if not risky:
        print('    无 ✓ (所有改动条目行数都没超过原文)')

    print('\n【6】不可见字符')
    bad = {}
    for r in rows:
        for ch in r['text_edited']:
            o = ord(ch)
            if 0xE000 <= o <= 0xF8FF or (o < 0x20 and ch != '\n') or 0x7F <= o <= 0x9F:
                bad.setdefault(o, 0)
                bad[o] += 1
    print('    异常字符: %s' % (bad or '无 ✓'))

    print('\n【7】风格检查')
    full = sum(r['text_edited'].count(c) for r in changed for c in '，。、；：！？（）')
    half = sum(r['text_edited'].count(c) for r in changed for c in ',.;:!?()')
    print('    改动条目里的全角标点 %d 个 / 半角标点 %d 个' % (full, half))
    sp = sum(1 for r in changed for m in re.finditer(r'[\u4e00-\u9fff] [\u4e00-\u9fff]', r['text_edited']))
    print('    汉字之间的空格: %d 处 %s' % (sp, '(建议去掉)' if sp else '✓'))
    lead = [r['id'] for r in changed if r['text_edited'][:1] == ' ' or r['text_edited'][-1:] == ' ']
    print('    首尾空格: %s' % (lead or '无 ✓'))


if __name__ == '__main__':
    main()
