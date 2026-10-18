# -*- coding: utf-8 -*-
r"""r61_ram_probe.py — 页面 EE RAM dump 里到底有没有"这一页的正文"?

判据链 (决定"解析失败" vs "渲染不出"):
  · 若**正文编码字节在 RAM 里存在**, 但 drawlog 里从没被交给 DrawString ⇒ 渲染/取用阶段的问题。
  · 若**正文编码字节在 RAM 里根本不存在** ⇒ 容器/解析阶段就没把这段文本交出来 (解析失败)。

同时对两个盘做, 互为对照。用法: python work/builds/GR_ZH98/temp/r61/r61_ram_probe.py
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                       # noqa: E402

cs = T.Charset()
enc = {}
for ch, bb in cs.enc_pair.items():
    enc[ch] = bytes(bb)
for ch, bb in cs.enc_single.items():
    enc[ch] = bytes((bb,))


def eb(s):
    return b''.join(enc[c] for c in s if c in enc)


def one(dump, label, pats):
    b = open(dump, 'rb').read()
    print('\n--- %s  (%s, %d B) ---' % (label, os.path.basename(dump), len(b)))
    for name, pat in pats:
        print('   %-34s %-24s 出现 %d 次' % (name, pat.hex(' '), b.count(pat)))


def main():
    z109 = glob.glob(os.path.join(REPO, 'work/builds/GR_ZH98/temp/r61/dump_recon2',
                                  'page_interview_f*_eeram.bin'))
    tst = glob.glob(os.path.join(REPO, 'work/builds/GR_TEST_FONT2/temp/dump_hook3',
                                 'hook3_page_f*_eeram.bin'))
    assert z109 and tst, (z109, tst)
    pats = [
        ('<text> 标签', b'<text>'),
        ('item 名 开发访谈 1', eb('开发访谈 1')),
        ('★原版正文 头2字(开发)', eb('开发')),
        ('★原版正文 头8字(开发手记：第一辑)', eb('开发手记：第一辑')),
        ('★测试页正文 头2字(字库)', eb('字库')),
        ('★测试页正文 头8字(字库测试页全)', eb('字库测试页 全')),
        ('测试页正文 第3行头4字(牛牲牺猪)', eb('牛牲牺猪')),
        ('测试页正文 末行头4字(障需充口)', eb('障需充口')),
        ('{p} 标记', b'{p}'),
        ('{br} 标记', b'{br}'),
    ]
    one(z109[0], 'GR_ZH109 原版页 (正文正常显示)', pats)
    one(tst[0], 'GR_TEST_FONT2 测试页 (正文空白)', pats)
    return 0


if __name__ == '__main__':
    sys.exit(main())
