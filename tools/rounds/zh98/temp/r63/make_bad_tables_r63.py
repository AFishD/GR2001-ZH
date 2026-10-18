# -*- coding: utf-8 -*-
r"""make_bad_tables_r63.py — 造 4 张"写法/定位有问题"的表, 用来实测门禁会不会真的拦。

  ① bad_format : 换行 / 双引号 / [[empty]]      (写法错 ⇒ --force 也不能绕过)
  ② bad_tag    : 把某一行的 tag 改成别的值       (与源盘不同步 ⇒ --force 可绕过)
  ③ bad_stale  : 把某一行的 text_zh 改成盘上没有的文本 (现值既不是 text_zh 也不是 text_edited)
  ④ bad_grow   : 一条标题塞 40000 个汉字 ⇒ 内容变长超过陈旧尾巴 38238 B ⇒ 应当中止
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
SRC = os.path.join(HERE, 'inject_titles', 'GR_ZH110_text_sf_titles.csv')
CELLS = ('text_en', 'text_zh', 'text_edited', 'note')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def load(p):
    with open(p, encoding='utf-8-sig', newline='') as f:
        rd = csv.reader(f)
        cols = next(rd)
        return cols, [dict(zip(cols, r)) for r in rd if r and any(x.strip() for x in r)]


def save(p, cols, rows):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with open(p, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        for r in [dict(zip(cols, cols))] + rows:
            line = ','.join(csv_field(c, r.get(c, '')) for c in cols)
            f.write((line + '\r\n').encode('utf-8'))


def csv_field(name, v):
    s = '' if v is None else str(v)
    if name in CELLS or any(c in s for c in ',"\r\n'):
        return '"' + s.replace('"', '""') + '"'
    return s


def one(cols, rid):
    _c, rows = load(SRC)
    for r in rows:
        if r['id'] == rid:
            return r
    raise SystemExit('没有 %s' % rid)


def main():
    cols, base = load(SRC)
    print('源表 %d 行' % len(base))

    # ① 写法错
    cols1, r1 = cols, load(SRC)[1]
    d = dict((r['id'], r) for r in r1)
    d['SFXML:A0002']['text_edited'] = '士\n兵'
    d['SFXML:A0005']['text_edited'] = '敌"人'
    d['SFXML:A0010']['text_edited'] = '[[empty]]'
    d['SFXML:A0013']['text_edited'] = '幽灵任务{WRAP}1'
    save(os.path.join(HERE, 'bad_format', 'GR_ZH110_text_sf_titles.csv'), cols1, r1)
    print('① bad_format: A0002 含换行 / A0005 含双引号 / A0010 清空 / A0013 含 {WRAP}')

    # ② tag 不符
    cols2, r2 = cols, load(SRC)[1]
    for r in r2:
        if r['id'] == 'SFXML:A0100' and r['text_edited'] != r['text_zh']:
            break
    d = dict((r['id'], r) for r in r2)
    d['SFXML:A0100']['text_edited'] = '测试标题甲'
    d['SFXML:A0100']['tag'] = 'studio' if d['SFXML:A0100']['tag'] != 'studio' else 'item'
    save(os.path.join(HERE, 'bad_tag', 'GR_ZH110_text_sf_titles.csv'), cols2, r2)
    print('② bad_tag: A0100 的 tag 改成 %r (盘上是 %r)'
          % (d['SFXML:A0100']['tag'], one(cols, 'SFXML:A0100')['tag']))

    # ③ 表与源盘不同步 (text_zh 对不上盘上现值, text_edited 又是第三个值)
    cols3, r3 = cols, load(SRC)[1]
    d = dict((r['id'], r) for r in r3)
    d['SFXML:A0120']['text_edited'] = '兵种简介'
    d['SFXML:A0120']['text_zh'] = '何为幽灵？'
    save(os.path.join(HERE, 'bad_stale', 'GR_ZH110_text_sf_titles.csv'), cols3, r3)
    print('③ bad_stale: A0120 的 text_zh 改成盘上没有的文本 (用盘上确实存在的另一条标题, '
          '免得先被"缺字"拦下)')

    # ④ 改长超过陈旧尾巴
    cols4, r4 = cols, load(SRC)[1]
    d = dict((r['id'], r) for r in r4)
    d['SFXML:A0002']['text_edited'] = '大字' * 20000          # 40000 汉字
    save(os.path.join(HERE, 'bad_grow', 'GR_ZH110_text_sf_titles.csv'), cols4, r4)
    print('④ bad_grow: A0002 改成 40000 个汉字 (约 80000 B) ⇒ 远超尾巴 38238 B')
    return 0


if __name__ == '__main__':
    sys.exit(main())
