# -*- coding: utf-8 -*-
r"""patch_zh51_sfxml_titles.py — 修 **SFXML 的 `name=` 标题属性**(陈旧码位)。

## 症状 (round51 由 `tools/iso_build/repack_leak_scan.py` 查出)

`EN_SPECIAL_FEATURE.XML` 里"特别收录"条目的**标题**存在 `<item name="…">` 属性里
(实机截图已证: 标题条画的就是它)。这些属性**不在可注入表里**
(`dump_text_csv` 只抓 `<text>` 元素) ⇒ 从来不会被"整体重编码"碰到。

而 charset 在 round39..49 之间改过多次 ⇒ **当年写下的码位现在指向别的字**。实测:

    旧 charset 解出 (当年写的)          现 charset 解出 (现在盘上画的)
    定向炸药 (M2)                       定向炸、 (M2)
    MP5 冲锋枪                          MP5 冲酿枪
    M4 短突击步枪                        M4 持突击步枪
    M249 班用机枪                        M249 灾用机枪
    测距望远镜 (AN/GVS-5)                测距昨远镜 (AN/GVS-5)
    沙漠风暴任务1..7                      沙漠短暴任务1..7
    银星勋章 / 优异服役十字勋章             堂星勋章 / 优帐服役渡字勋章
    奥萨泽 / 汉克尔 / 科汉 / 门兹 / 坦尼 / 海利 / 伊布拉伊姆
                                       奥那共 / 摩克营 / 科摩 / 门事 / 坦炼 / 油利 / 虏布拉虏姆
    ★ 何为幽灵？                         ★ 何为幽灵；      ← 实机标题条上那个奇怪的"；"

**104 个属性里 33 个是陈旧的**。这不是重排造成的, 是**盘上现存的既有缺陷**;
重排只是把它放大 (round50 看到的「何为**强知营**」)。

## 本补丁做什么

对 SFXML 里每一个 `name="…"` 属性:
  用**旧 charset** (`work/builds/GR_ZH92/font/charset_matching_this_disk.json`,
  与 GR_ZH92/93/94 盘配套的那份) 解码 ⇒ 得到当年写的正确文本;
  再用**现 charset** 重新编码 ⇒ 原位替换。

前提 (写盘前硬断言):
  · 新旧字节**长度完全相同** (对偶码↔对偶码、单字节↔单字节) ⇒ 容器解压总长不变;
  · 只改 `name=` 属性的字节, `<text>` 元素与其余字段逐字节不动;
  · 重新压缩后**帧长 ≤ 槽位** ⇒ IMG 条目表 off/stored/real **一个字节都不动**;
  · 产物回读: 33 个标题全部解出正确文本, 其余属性与 `<text>` 全部不变。

用法:
  python tools/iso_build/patch_zh51_sfxml_titles.py <src.iso> <dst.iso> [--dry-run]
"""
import argparse
import io
import json
import os
import re
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:                                                        # noqa: BLE001
    pass

import tcslib                                                            # noqa: E402
import inject_text_csv as inj                                            # noqa: E402

OLD_CHARSET = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'font',
                           'charset_matching_this_disk.json')
ITEM = re.compile(rb'<(studio|item|group)\b([^>]*)>')
NAME = re.compile(rb'name\s*=\s*"([^"]*)"')


def rel(p):
    try:
        r = os.path.relpath(p, REPO)
    except ValueError:
        return p.replace('\\', '/')
    return r.replace('\\', '/') if not r.startswith('..') else p.replace('\\', '/')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--old-charset', default=OLD_CHARSET)
    ap.add_argument('--report', default=None)
    a = ap.parse_args()
    src = a.src
    dst = a.dst or src
    print('=' * 78)
    print('修 SFXML 的 name= 标题属性 (陈旧码位 → 现 charset 原位重编码)')
    print('  src = %s' % rel(src))
    print('  旧 charset = %s' % rel(a.old_charset))
    print('=' * 78)

    old = tcslib.Charset(a.old_charset)
    new = tcslib.Charset()
    iso = tcslib.Iso(src)
    spec = tcslib.RES['SFXML']['copies'][0]
    c = inj.Container(iso, 'SFXML', spec, new)
    print('[载入] %s @%s#%d  槽 %d B / 解压 %d B / %d 个子流'
          % (c.tag, c.img, c.idx, c.slot, len(c.blob), len(c.subs)))

    edits, rows, same = [], [], 0
    for m in ITEM.finditer(c.blob):
        nm = NAME.search(m.group(2))
        if not nm:
            continue
        v = nm.group(1)
        o = old.decode(v)[0]
        n = new.decode(v)[0]
        if o == n:
            same += 1
            continue
        nb = new.encode_strict(o)
        if len(nb) != len(v):
            raise SystemExit('!! %r 重编码后长度变了 (%d→%d) —— 拒绝改写'
                             % (o[:16], len(v), len(nb)))
        off = m.start(2) + nm.start(1)
        edits.append((off, off + len(v), nb, None))
        rows.append(dict(tag=m.group(1).decode(), off=off, nbytes=len(v),
                         old_text=o, now_text=n, bytes_before=v.hex(' '), bytes_after=nb.hex(' ')))
    print('[找  ] name 属性: 正确 %d 个, **陈旧 %d 个** (要改)"' % (same, len(rows)))
    for r in rows:
        print('       %-28r → %r' % (r['now_text'][:26], r['old_text'][:26]))
    if not rows:
        raise SystemExit('!! 没有陈旧标题 —— 这张盘不需要本补丁 (或已经修过)')

    c.edits = edits
    new_blob, delta = c.build_blob()
    if delta != 0:
        raise SystemExit('!! 解压总长变了 %+d B' % delta)
    if new_blob == c.blob:
        raise SystemExit('!! 拼出来的 blob 与原件相同?')
    frame, n_rep = c.repack(new_blob)
    over = len(frame) - c.slot
    print('[压  ] 重压 %d 个子流; 帧 %d B / 槽 %d B (%s %d B)'
          % (n_rep, len(frame), c.slot, '余' if over <= 0 else '★超槽', abs(over)))
    if over > 0:
        raise SystemExit('!! 压缩后超出槽位 %d B —— 需要扩容条目 (会动 IMG 条目表, 本补丁拒绝)' % over)
    # 只允许改动落在这些属性区间内
    win = [(r['off'], r['nbytes']) for r in rows]
    diff = [i for i in range(len(new_blob)) if new_blob[i] != c.blob[i]]
    outside = [i for i in diff if not any(w0 <= i < w0 + wl for w0, wl in win)]
    print('[查  ] blob 改动 %d 字节, 落在属性区间之外 %d 字节' % (len(diff), len(outside)))
    if outside:
        raise SystemExit('!! 有改动落在 name 属性之外 (%s) —— 拒绝' % outside[:5])

    if a.dry_run:
        print('[dry ] 不写盘。')
        iso.close()
        return 0

    # ---- 写盘 (只写这一个条目的槽位; 条目表 off/stored/real 不动) ----
    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(c.entry['iso_off'])
        f.write(frame + b'\x00' * (c.slot - len(frame)))
    assert os.path.getsize(src) == os.path.getsize(dst), '!! ISO 尺寸变了'
    iso.close()

    # ---- 回读复核 ----
    iso2 = tcslib.Iso(dst)
    e2 = iso2.img_entry(c.lba, c.idx)
    if (e2['stored'], e2['off'], e2['real']) != (c.entry['stored'], c.entry['off'],
                                                 c.entry['real']):
        raise SystemExit('!! IMG 条目表 off/stored/real 被改动了')
    subs2 = tcslib.lzo_subs(iso2.read(e2['iso_off'], e2['stored']))
    blob2 = b''.join(s[0] for s in subs2)
    if len(blob2) != len(c.blob):
        raise SystemExit('!! 回读解压长度变化')
    # ① 33 个标题必须解出正确文本
    got = {}
    for m in ITEM.finditer(blob2):
        nm = NAME.search(m.group(2))
        if nm:
            got[m.start(2) + nm.start(1)] = new.decode(nm.group(1))[0]
    bad = [r for r in rows if got.get(r['off']) != r['old_text']]
    if bad:
        raise SystemExit('!! 回读: %d 个标题没修对 (%s)' % (len(bad), bad[0]['old_text']))
    # ② <text> 元素与其余字节: 只有属性区间变了
    d2 = [i for i in range(len(blob2)) if blob2[i] != c.blob[i]]
    out2 = [i for i in d2 if not any(w0 <= i < w0 + wl for w0, wl in win)]
    if out2:
        raise SystemExit('!! 回读: 有改动落在 name 属性之外 (%s)' % out2[:5])
    # ③ 盘上其它条目逐字节不变
    iso_a = tcslib.Iso(src)
    n_other = 0
    for lba in (spec[1],):
        for idx in range(0, 2048):
            try:
                x1, x2 = iso_a.img_entry(lba, idx), iso2.img_entry(lba, idx)
            except Exception:                                             # noqa: BLE001
                break
            if x1['stored'] <= 0:
                break
            if (x1['off'], x1['stored']) != (x2['off'], x2['stored']):
                raise SystemExit('!! 条目 #%d 的 off/stored 变了' % idx)
            if idx == c.idx:
                continue
            if iso_a.read(x1['iso_off'], x1['stored']) != iso2.read(x2['iso_off'], x2['stored']):
                raise SystemExit('!! 条目 #%d (%s) 被改动了' % (idx, x1['name']))
            n_other += 1
    iso_a.close()
    iso2.close()
    print('[验  ] 回读: %d 个标题全部解出正确文本 ✓; 改动只在属性区间内 ✓; '
          'MENU.IMG 其余 %d 个条目逐字节不变 ✓' % (len(rows), n_other))

    rep = dict(src=rel(src), dst=rel(dst),
               tool='tools/iso_build/patch_zh51_sfxml_titles.py',
               old_charset=rel(a.old_charset), container=c.tag,
               slot=c.slot, frame_bytes=len(frame), substreams_repacked=n_rep,
               n_attrs=len(rows) + same, n_fixed=len(rows), unchanged=same,
               why='SFXML 的 name= 标题属性**不在可注入表里** ⇒ 从来不会被"整体重编码"碰到; '
                   'charset 在 round39..49 改过多次 ⇒ 当年写下的码位现在指向别的字',
               fixed=rows, iso_sha256_after=tcslib.sha256_file(dst))
    rp = a.report or os.path.join(os.path.dirname(os.path.abspath(dst)), 'temp',
                                  'sfxml_title_fix.json')
    os.makedirs(os.path.dirname(rp), exist_ok=True)
    io.open(rp, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(rep, ensure_ascii=False, indent=1) + '\n')
    print('[报告] %s' % rel(rp))
    print('[完成] %s  sha256=%s' % (rel(dst), rep['iso_sha256_after']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
