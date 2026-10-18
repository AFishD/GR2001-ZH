# -*- coding: utf-8 -*-
r"""unused_chars.py — 字库「实际用量 / 可回收量」核算

背景: 译文改完后, 原先字库里有不少字不再被用到 ⇒ 它们的码位/图集格位理论上可以回收。
本脚本:
  1) 统计「改动前(盘上现文本)」与「改动后(应用用户编辑)」各自用到的字符集合
  2) 与字库(字符集)对比 ⇒ 新缺字 / 可回收字
  3) **逐个到整个 ISO 里做字节级搜索**验证「可回收」候选是否真的全盘未使用
"""
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import json  # noqa: E402

TXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text')
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
WRAP_RE = re.compile(r'\{\s*(?:WRAP|WARP)\s*\}', re.I)


def load_tables():
    out = {}
    for n in sorted(os.listdir(TXT)):
        if n.endswith('.csv'):
            out[n] = list(csv.DictReader(io.open(os.path.join(TXT, n), encoding='utf-8-sig')))
    return out


def main():
    cs = json.load(io.open(CS, encoding='utf-8'))
    font = set(cs['codes'].keys()) | set(cs['pair_of'].keys())
    tables = load_tables()
    rows = [r for t in tables.values() for r in t]

    def chars(s):
        s = WRAP_RE.sub('', s)
        return {c for c in s if ord(c) >= 0x20}

    old = set()
    new = set()
    for r in rows:
        old |= chars(r['text_zh'])
        new |= chars(r['text_edited'] if r['text_edited'].strip() else r['text_zh'])

    print('【字库】字符集共 %d 字 (单字节 %d + 对偶 %d)'
          % (len(font), len(cs['codes']), len(cs['pair_of'])))
    print('【旧文本】(盘上现文本) 用到 %d 个不同字符' % len(old))
    print('【新文本】(应用你的编辑后) 用到 %d 个不同字符' % len(new))
    print()
    need = sorted(new - font)
    unused = sorted(font - new)
    print('① 新文本里字库没有的 (要补): %d 个' % len(need))
    print('   ', ''.join(need))
    print()
    print('② 字库里有、但新文本里没出现的 (候选可回收): %d 个' % len(unused))
    print('   ', ''.join(unused[:120]), '…' if len(unused) > 120 else '')
    print()
    print('   其中「旧文本也没用到」的 (本来就没用): %d 个' % len(set(unused) & (font - old)))
    print('   其中「旧文本用到、新译文改掉了」的 (真正的"改译后闲置"): %d 个'
          % len(set(unused) & (font & old)))
    print()

    # ③ 字节级全盘验证: 对偶字按 (lead,trail) 搜索整个 ISO
    print('③ 全盘字节级验证 (对偶字在 1.6 GB ISO 里搜字节对; 单字节字跳过, 噪声太大):')
    data = open(ISO, 'rb').read()
    print('   已载入 ISO (%d MB)' % (len(data) // 1048576))
    truly = []
    maybe = []
    for ch in unused:
        if ch in cs['pair_of']:
            b = bytes(cs['pair_of'][ch])
            if data.find(b) < 0:
                truly.append(ch)
            else:
                maybe.append(ch)
        elif ch in cs['codes']:
            b = bytes([cs['codes'][ch]])
            if data.find(b) < 0:
                truly.append(ch)
            else:
                maybe.append(ch)
    print('   ⇒ 全盘找不到其字节编码 (可安全回收): %d 个' % len(truly))
    print('     ', ''.join(truly[:100]), '…' if len(truly) > 100 else '')
    print('   ⇒ 全盘仍能找到字节 (可能是别处用到/或随机命中, 不可回收): %d 个' % len(maybe))
    print('     ', ''.join(maybe[:80]), '…' if len(maybe) > 80 else '')
    print()
    print('【结论】')
    print('   合法对偶空位 78 个; 新缺字 %d 个' % len(need))
    print('   ⇒ 若回收「全盘确认未使用」的 %d 个字, 可用空间 = 78 + %d = %d'
          % (len(truly), len(truly), 78 + len(truly)))


if __name__ == '__main__':
    main()
