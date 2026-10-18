# -*- coding: utf-8 -*-
r"""r61_page_bytes.py — 取出「开发访谈 1」(<text> 载荷) 的**盘上原始字节**, 对照两个盘找可疑字符。

为什么需要: 测试页整页空白。要么"引擎解析失败"(文本里有让它解析崩掉的字节), 要么
"渲染不出来"(解析出来了但画不出)。**解析失败**最典型的形态 = 载荷里混进了引擎的控制字节
(串终止符 / 标记引入符 / 非法单字节码), 使整段文本在很靠前的位置就被截断 ⇒ 整页空白。
本脚本离线就能看出"测试页比原版**多用了哪些字节**", 直接圈出嫌疑集。

用法: python work/builds/GR_ZH98/temp/r61/r61_page_bytes.py
"""
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
import tcslib as T                                                       # noqa: E402
import inject_text_csv as inj                                            # noqa: E402

ITEM = re.compile(rb'<item\b([^>]*)>')
NAME = re.compile(rb'name\s*=\s*"([^"]*)"')
cs = T.Charset()


def payload(iso_path, item_name='开发访谈 1'):
    iso = T.Iso(iso_path)
    spec = T.RES['SFXML']['copies'][0]
    c = inj.Container(iso, 'SFXML', spec, cs)
    hits = []
    for m in ITEM.finditer(c.blob):
        nm = NAME.search(m.group(1))
        if nm and cs.decode(nm.group(1))[0] == item_name:
            hits.append(m.start())
    assert len(hits) == 1, (item_name, hits)
    mo = re.compile(rb'<text>').search(c.blob, hits[0])
    mc = re.compile(rb'</text>').search(c.blob, mo.end())
    body = c.blob[mo.end():mc.start()]
    iso.close()
    return body, mo.end(), len(c.blob)


def report(tag, body):
    print('\n===== %s : <text> 载荷 %d B =====' % (tag, len(body)))
    print('  首 64 B (hex) = %s' % body[:64].hex(' '))
    txt = cs.decode(body)[0]
    segs = T.segments(txt)
    lines = [sg for (_s, _e, sg) in segs]
    print('  段数 = %d; 首段 = %r' % (len(lines), lines[0] if lines else None))
    print('  第 2 段 = %r' % (lines[1] if len(lines) > 1 else None))
    print('  末段 = %r' % (lines[-1][-40:] if lines else None))
    print('  标记计数: {br}=%d {p}=%d {=%d }=%d' %
          (txt.count('{br}'), txt.count('{p}'), txt.count('{'), txt.count('}')))
    bs = set(body)
    low = sorted(b for b in bs if b < 0x20)
    hi = sorted(b for b in bs if 0x7F <= b <= 0xA0)
    asc = sorted(b for b in bs if 0x20 <= b < 0x7F)
    print('  用到的字节数 = %d; <0x20 的 = %s; 0x7F..0xA0 的 = %s' %
          (len(bs), ['%02X' % b for b in low], ['%02X' % b for b in hi]))
    print('  可打印 ASCII = %r' % ''.join(chr(b) for b in asc))
    return set(body), txt


def main():
    ref_iso = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
    test_iso = os.path.join(REPO, 'work', 'builds', 'GR_TEST_FONT2', 'GR_TEST_FONT2.iso')
    b_ref, off_r, blob_r = payload(ref_iso)
    b_test, off_t, blob_t = payload(test_iso)
    s_ref, t_ref = report('GR_ZH109 (原版, 用户说这一页正常)', b_ref)
    s_test, t_test = report('GR_TEST_FONT2 (字库测试页, 用户说整页空白)', b_test)
    print('\n===== 差分 =====')
    print('  载荷偏移 = %d / %d ; blob 长度 = %d / %d' % (off_r, off_t, blob_r, blob_t))
    print('  长度 = %d / %d' % (len(b_ref), len(b_test)))
    new = sorted(s_test - s_ref)
    gone = sorted(s_ref - s_test)
    print('  ★ 测试页**新增**用到的字节 (%d 个): %s' % (len(new), ['%02X' % b for b in new]))
    print('    其中 <0x20 = %s ; 0x7F..0xA0 = %s' %
          (['%02X' % b for b in new if b < 0x20], ['%02X' % b for b in new if 0x7F <= b <= 0xA0]))
    print('    作为字符看: %r' % cs.decode(bytes(new))[0])
    print('  测试页不再用的字节 (%d 个): %s' % (len(gone), ['%02X' % b for b in gone]))
    # 每个"新增字节"在测试页文本里的位置 (前 3 处), 便于定位
    print('\n  新增字节在载荷里的位置 (前 3 处):')
    for b in new[:24]:
        pos = [i for i, x in enumerate(b_test) if x == b][:3]
        print('    %02X  %r  位置 %s' % (b, cs.decode(bytes([b]))[0] if b < 0x80 else '?', pos))
    return 0


if __name__ == '__main__':
    sys.exit(main())
