# -*- coding: utf-8 -*-
r"""save_usage.py — 把「新文本缺字」「字库闲置字」两份清单写到文件"""
import csv
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
TXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
OUT = os.path.join(HERE, '字库用量核算.md')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
WRAP_RE = re.compile(r'\{\s*(?:WRAP|WARP)\s*\}', re.I)


def main():
    cs = json.load(io.open(CS, encoding='utf-8'))
    font = set(cs['codes']) | set(cs['pair_of'])
    rows = []
    for n in sorted(os.listdir(TXT)):
        if n.endswith('.csv'):
            rows += list(csv.DictReader(io.open(os.path.join(TXT, n), encoding='utf-8-sig')))

    def chars(s):
        return {c for c in WRAP_RE.sub('', s) if ord(c) >= 0x20}

    old, new = set(), set()
    for r in rows:
        old |= chars(r['text_zh'])
        new |= chars(r['text_edited'] if r['text_edited'].strip() else r['text_zh'])
    need = sorted(new - font)
    need_cjk = [c for c in need if ord(c) > 0x7F]
    need_ascii = [c for c in need if ord(c) <= 0x7F]
    idle = sorted(font - new)
    idle_new = sorted((font & old) - new)

    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('# 字库用量核算 (基于 GR_ZH92 的 text/ 多表)\n\n')
        f.write('- 字库字符集: **%d** 字 (单字节 %d + 对偶 %d)\n'
                % (len(font), len(cs['codes']), len(cs['pair_of'])))
        f.write('- 旧文本(盘上现文本)用到: **%d** 个不同字符\n' % len(old))
        f.write('- 新文本(应用编辑后)用到: **%d** 个不同字符\n\n' % len(new))
        f.write('## ① 新文本缺字: %d 个 (其中非 ASCII **%d** 个 = 真正要补)\n\n'
                % (len(need), len(need_cjk)))
        f.write('### 真正要补 (非 ASCII, %d 个)\n\n```\n%s\n```\n\n'
                % (len(need_cjk), ''.join(need_cjk)))
        f.write('### ASCII (%d 个, 引擎走单字节路径, 预检只提示不阻断)\n\n```\n%s\n```\n\n'
                % (len(need_ascii), ''.join(need_ascii)))
        f.write('## ② 字库闲置字: %d 个 (新文本用不到)\n\n' % len(idle))
        f.write('- 其中「旧文本也没用到」: **%d** 个 ⇒ 早就闲置\n' % len(font - old))
        f.write('- 其中「旧文本用到、改译后闲置」: **%d** 个 ⇒ 本次改译真正释放的\n\n'
                % len(idle_new))
        f.write('### 闲置字全表 (%d 个)\n\n```\n%s\n```\n\n'
                % (len(idle), ''.join(idle)))
        f.write('## ③ 容量\n\n')
        f.write('- 合法对偶空间 `lead 0xA1..0xAD` = 13 × 94 = **1222**，已用 1144 ⇒ **空位 78**\n')
        f.write('- 需补 **%d** 个 ⇒ 空位 %s\n'
                % (len(need_cjk), '够用(余 %d)' % (78 - len(need_cjk))
                   if 78 >= len(need_cjk) else '**不够**'))
        f.write('- 若回收全部闲置字: 78 + %d = %d (但闲置字可能被未覆盖资源用到, 有风险)\n'
                % (len(idle), 78 + len(idle)))
        f.write('\n> 覆盖范围: 本核算只扫了 `LANG`(语言表) + `SFXML`(特别收录) 两类资源;\n'
                '> `.ATR` 人名 / ELF 字符串 / `.MIS` 任务文本**未扫**, 所以「闲置」不等于「全盘未使用」。\n'
                '> 另: 用「在全盘字节里搜该字的编码」来验证是**无效方法** —— 2 字节序列在 1.6 GB 里\n'
                '> 随机命中期望就有数千次, 全部"找到"是必然。\n')
    print('已写', os.path.relpath(OUT, REPO))
    print('  要补(非ASCII) %d 个: %s' % (len(need_cjk), ''.join(need_cjk)[:80]))
    print('  闲置 %d 个 (其中本次改译释放 %d 个)' % (len(idle), len(idle_new)))


if __name__ == '__main__':
    main()
