# -*- coding: utf-8 -*-
r"""probe_words_r63.py — 逐词/逐字可用性 (不跳过已见过的字), 供挑改动。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T                                                    # noqa: E402

WORDS = ['M4 短突击步枪', 'M4 卡宾枪', '卡宾枪', '卡', '宾', '枪', '冲锋枪', '突击步枪',
         '狙击步枪', '班用机枪', '通用机枪', '轻机枪', '机枪', '手枪', '火箭筒', '步枪',
         '微型冲锋枪', '微声冲锋枪', '精确射手步枪', '战役勋带', '战役勋表', '勋表', '勋带',
         '拉默雷斯', '拉米雷斯', '米', '海利', '海尔', '尔', '门兹', '蒙兹', '兹', '坦尼',
         '汤尼', '尼', '步兵战斗章 (CIB)', '步兵战斗徽章', '战斗步兵章', '战斗步兵徽章',
         '国会荣誉勋章', '国会最高勋章', '荣誉勋章', '最高勋章', '勋章', '奖章',
         '战功星章', '铜星勋章', '紫心勋章', '银星勋章', '优异服役十字勋章',
         '开发访谈 1', '开发访谈', '战争序幕 1', '兵种简介', '何为幽灵？', '极限危机']


def main():
    cs = T.Charset()
    for w in WORDS:
        parts, bad = [], []
        for ch in w:
            if ch in cs.enc_single:
                parts.append('%s:1B/%02X' % (ch, cs.enc_single[ch]))
            elif ch in cs.enc_pair:
                parts.append('%s:2B/%02X%02X' % (ch, cs.enc_pair[ch][0], cs.enc_pair[ch][1]))
            else:
                bad.append(ch)
        try:
            nb = len(cs.encode_strict(w))
            enc = '%2d B' % nb
        except T.CharsetError:
            enc = '★不可编码'
        print('%-20s %-10s %s%s' % (w, enc, ' '.join(parts),
                                    ('   ★不可用: %s' % ' '.join(bad)) if bad else ''))


if __name__ == '__main__':
    main()
