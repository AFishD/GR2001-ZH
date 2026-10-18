# -*- coding: utf-8 -*-
r"""make_demo_tables_r63.py — 造两张演示用标题表 (只改 text_edited 一列)。

  A) work/builds/GR_ZH110/inject_titles/GR_ZH109_text_sf_titles.csv
     → 4 处**真错译**修正 (全部只用现有字), 用来真正落盘:
        SFXML:A0056  定向炸药 (M2)      → 爆破装药 (M2)      Δ=0 B
        SFXML:A0065  M4 短突击步枪      → M4 卡宾枪          Δ=-3 B
        SFXML:A0080  FN-FAL 步枪 (短型) → FN-FAL 步枪 (伞兵型) Δ=+1 B
        SFXML:A0129  拉默雷斯           → 拉米雷斯            Δ=0 B
  B) work/builds/GR_ZH98/temp/r63/demo_blocked_rong/GR_ZH110_text_sf_titles.csv
     → A 的四条 + 一条**缺字**改动 (给"缺字必须被拦下"做实测证据):
        SFXML:A0116  国会最高勋章       → 国会荣誉勋章        (荣 不在字符集里)

用法: python make_demo_tables_r63.py
"""
import csv
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH110', 'inject_titles',
                   'GR_ZH109_text_sf_titles.csv')
BLOCKED_DIR = os.path.join(HERE, 'demo_blocked_rong')

EDITS = [
    # (id, 新标题, 理由)  —— 理由同时写进 note 列, 报告里直接引用
    ('SFXML:A0056', '爆破装药 (M2)',
     '英文原名 "Demo Charge (M2 Demolitions Charge)" = **爆破装药** (攻城/爆破用的装药); '
     '原译"定向炸药"字面是"有方向性的炸药"(成型装药/定向爆破), 与 Demolitions Charge 不是一回事'),
    ('SFXML:A0065', 'M4 卡宾枪',
     '英文原名 "M4"; M4 的美军制式分类是 **卡宾枪 (carbine)**, 不是"短突击步枪" '
     '(后者对应 9A-91 这类真正的短突击步枪)'),
    ('SFXML:A0080', 'FN-FAL 步枪 (伞兵型)',
     '英文原名 "FN-FAL Para": "Para" = **伞兵型** (折叠枪托的伞兵型号), 不是"短型"; '
     '★ 这一条**改长 +1 B**, 用来证明"改字数(变长)"这条通道是通的'),
    ('SFXML:A0129', '拉米雷斯',
     '英文原名 "H. Ramirez": 通用译名是"拉**米**雷斯" (Ra-mi-rez), 原译"拉**默**雷斯"'
     ' 的"默"(mò) 与 mi 读音不符 —— 音译错误'),
]
RONG = ('SFXML:A0116', '国会荣誉勋章',
        '英文原名 "Congressional Medal of Honor" = **国会荣誉勋章** —— 这条**故意留着**做'
        '"缺字必须被拦下"的实测证据: 「荣」当前不在字符集里 ⇒ 预检应当 exit 3 并指名道姓')


def load(p):
    with open(p, 'r', encoding='utf-8-sig', newline='') as f:
        rd = csv.reader(f)
        cols = next(rd)
        rows = [dict(zip(cols, r)) for r in rd if r and any(x.strip() for x in r)]
    return cols, rows


def save(p, cols, rows):
    d = os.path.dirname(os.path.abspath(p))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(p, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write((','.join(csv_field(c, c) for c in cols) + '\r\n').encode('utf-8'))
        for r in rows:
            f.write((','.join(csv_field(c, r.get(c, '')) for c in cols)
                     + '\r\n').encode('utf-8'))


def csv_field(name, v):
    s = '' if v is None else str(v)
    if name in ('text_en', 'text_zh', 'text_edited', 'note') or any(c in s for c in ',"\r\n'):
        return '"' + s.replace('"', '""') + '"'
    return s


def apply(rows, edits):
    by = dict((r['id'], r) for r in rows)
    for (rid, new, why) in edits:
        r = by.get(rid)
        if r is None:
            raise SystemExit('!! 表里没有 %s' % rid)
        print('  %-13s %-22r → %-24r  (原 %d B)' % (rid, r['text_zh'], new, int(r['len_bytes'])))
        r['text_edited'] = new
        r['note'] = ('★ 本轮 round63 演示改动: %s。 (原注: %s)'
                     % (why, r['note'][:200]))
    return rows


def main():
    cols, rows = load(SRC)
    print('表: %s (%d 行)' % (os.path.relpath(SRC, REPO).replace('\\', '/'), len(rows)))
    print('== A) 真落盘的 4 处修正 ==')
    apply(rows, EDITS)
    save(SRC, cols, rows)
    print('→ 写回 %s' % os.path.relpath(SRC, REPO).replace('\\', '/'))

    cols2, rows2 = load(SRC)
    print('== B) 缺字演示表 (A 的 4 条 + 1 条缺字) ==')
    print('  %-13s %-22r → %-24r' % (RONG[0], '国会最高勋章', RONG[1]))
    apply(rows2, [RONG])
    p2 = os.path.join(BLOCKED_DIR, 'GR_ZH110_text_sf_titles.csv')
    save(p2, cols2, rows2)
    print('→ %s' % os.path.relpath(p2, REPO).replace('\\', '/'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
