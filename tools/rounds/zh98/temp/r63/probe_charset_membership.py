# -*- coding: utf-8 -*-
r"""probe_charset_membership.py — 候选汉字/词在本盘字符集里的可用性一览。

只读 charset JSON (不需要 ISO)。输出: 可用(单字节/对偶) / 不可用。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T                                                    # noqa: E402

# 候选改动里会用到的字 (按词分组)
WORDS = ['荣誉勋章', '国会荣誉勋章', '铜星勋章', '青铜星章', '紫心勋章', '战伤勋章',
         '步兵战斗徽章', '战役勋表', '战役勋带', '拉米雷斯', '拉默雷斯', '易卜拉欣',
         '伊布拉伊姆', '戈登', '高登', '雅各布斯', '亚各布斯', '科恩', '科汉',
         '海尔', '海利', '蒙兹', '门兹', '汤尼', '坦尼', '兹', '罕', '谓', '何为幽灵',
         '何谓幽灵', '纪念', '附加', '勋章', '奖章', '奖', '勋', '章', '银星勋章',
         '优异服役十字勋章', '杰出服役十字勋章', '战斗步兵徽章', '开发访谈', '访谈',
         '序幕', '简介', '兵种', '特种部队', '专家', '敌人', '训练', '士兵', '车辆']
EXTRA = ('誉铜紫徽卜欣戈雅恩恐惧米表青蒙汤谓纪兹罕杰伯森德斯坦克里维斯通各布'
         '拉默雷海利科汉门尼伊姆易欣卜鲁克劳约翰逊')


def main():
    cs = T.Charset()
    print('# 字符集: %d 个单字节码 + %d 个对偶码 (共 %d 字)'
          % (len(cs.enc_single), len(cs.enc_pair),
             len(set(cs.enc_single) | set(cs.enc_pair))))
    seen = set()
    for w in WORDS:
        ok, bad = [], []
        for ch in w:
            if ch in seen:
                continue
            seen.add(ch)
            if ch in cs.enc_single:
                ok.append('%s(1B 0x%02X)' % (ch, cs.enc_single[ch]))
            elif ch in cs.enc_pair:
                ok.append('%s(2B %02X%02X)' % (ch, cs.enc_pair[ch][0], cs.enc_pair[ch][1]))
            else:
                bad.append(ch)
        print('%-22s 可用 %-46s %s'
              % (w, ' '.join(ok) or '-', ('★不可用: %s' % ' '.join(bad)) if bad else '✓ 全可用'))
    # 单个字粗查
    print('\n# 单字粗查 (在字符集里? )')
    for ch in '荣誉铜紫徽卜欣戈雅恩恐惧米表青蒙汤谓纪兹罕杰伯森斯坦克里维斯通布':
        if ch in seen:
            continue
        v = ('单字节 0x%02X' % cs.enc_single[ch]) if ch in cs.enc_single else (
            ('对偶 %02X%02X' % cs.enc_pair[ch]) if ch in cs.enc_pair else '★没有')
        print('   %s  %s' % (ch, v))


if __name__ == '__main__':
    main()
