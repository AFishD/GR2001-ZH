# -*- coding: utf-8 -*-
r"""probe_words2_r63.py — 第二批候选改动 (含"改长"候选) 的字表体检。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T                                                    # noqa: E402
import inject_text_csv as inj                                         # noqa: E402

WORDS = ['FN-FAL 步枪 (短型)', 'FN-FAL 步枪 (伞兵型)', '伞兵型', '伞', '定向炸药 (M2)',
         '爆破装药 (M2)', '爆破装药', '爆', '破', '装', '药包 (M2)', '汉克尔', '亨克尔', '亨',
         '拉默雷斯', '拉米雷斯', '战役勋带', '战役勋表', '海利', '海尔', '门兹', '门茨', '茨',
         '步兵战斗章 (CIB)', '战斗步兵章 (CIB)', '优异服役十字勋章 (DSC)',
         '国会最高勋章', '国会荣誉勋章', 'M4 短突击步枪', 'M4 卡宾枪', 'M249 班用机枪',
         '测距望远镜 (AN/GVS-5)', '望远镜 (AN/GVS-5)', '双筒望远镜']
ARGS = sys.argv[1:]


def main():
    cs = T.Charset()
    for w in (ARGS or WORDS):
        parts, bad = [], []
        for ch in w:
            if ch in cs.enc_single:
                parts.append('%s:1B/%02X' % (ch, cs.enc_single[ch]))
            elif ch in cs.enc_pair:
                parts.append('%s:2B/%02X%02X' % (ch, cs.enc_pair[ch][0], cs.enc_pair[ch][1]))
            elif ord(ch) < 0x80:
                parts.append('%s:ascii' % ch)
            else:
                bad.append(ch)
        try:
            nb = len(cs.encode_strict(w))
            enc = '%2d B' % nb
        except T.CharsetError:
            enc = '★不可编码'
        print('%-24s %-10s %s%s' % (w, enc, ' '.join(parts),
                                    ('   ★不可用: %s' % ' '.join(bad)) if bad else ''))


if __name__ == '__main__':
    main()
