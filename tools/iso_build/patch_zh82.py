# -*- coding: utf-8 -*-
r"""patch_zh82.py — 特别收录 item/group 名按现行规范重译, 且**不补空格** (GR_ZH82)

用户报障 (GR_ZH81 实机):
  1. 特别收录→影片: 仍显示 "GR 任务 1"、"GR 片头" —— 未按规范译为"幽灵行动®任务N";
     目测名称中间多了空格 (导致搜索/居中异常)。
  2. 特别收录→设定图: 文字已汉化但**未居中**, 后面跟了几个空格。

根因 (字节级定位, work/_dis/sf_items_full.py + sf_node_audit.py):
  - 问题 1 = 我上一版**只改了 `<studio|group>` 的 name, 漏了 `<item name=...>`**;
    而这些 item name 是 **zh7 时代用"缩写+中文+空格"格式**译的:
        <item name="GR Opening">   → "GR 片头"
        <item name="GR Mission 1"> → "GR 任务 1"     ("GR" 未译 + 多余空格)
    与现行规范 (幽灵行动®任务N) 不符。
  - 问题 2 = 我上一版为保持槽内等长, **给译名补了 0x20 空格** (如 "士兵    ");
    游戏把尾随空格**计入文本宽度** → 视觉左偏, 看起来没居中。

本补丁 (按现行规范重译, **零空格填充**):
  - `<item name>`: GR/DS 前缀类 20 条 → "幽灵行动®任务N" / "沙漠风暴任务N" /
    "幽灵行动片头" / "幽灵行动片尾" / "沙漠风暴片头" / "沙漠风暴片尾";
  - `<group name>`: 41 条全部重译, 不再补空格;
  - `<studio name>`: **保持英文** (引擎内部标识, 改了会断链 — 见 PROGRESS §47);
  - 译名变长 → **XML 内容整体重排**, 8 子流边界重划, 重压回槽 (槽 49,700 余量充足)。

用法: python patch_zh82.py <src_iso> <dst_iso>   (基底 = GR_ZH79, XML 为 ZH77 原样)
"""
import json
import os
import re
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
from lz77_decode import lzo1x_decompress                      # noqa: E402
from lzo1x_c import compress as lzo_compress                  # noqa: E402

MENU_LBA = 776286
TAB_OFF, TAB_STEP = 0x830, 48
XML_IDX = 283
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')

# ── item 名 (GR/DS 前缀类; 其余条目 zh7 已译且格式正确, 不动) ──
ITEM_ZH = {
    'GR Opening': '幽灵行动片头',
    'GR Ending': '幽灵行动片尾',
    'DS Opening': '沙漠风暴片头',
    'DS Ending': '沙漠风暴片尾',
}
for _i in range(1, 16):
    ITEM_ZH['GR Mission %d' % _i] = '幽灵行动®任务%d' % _i
for _i in range(1, 9):
    ITEM_ZH['DS Mission %d' % _i] = '沙漠风暴任务%d' % _i

# ── group 名 (全部重译, 无尾随空格) ──
GROUP_ZH = {
    'Soldiers': '士兵',
    'Specialists 1': '专家1',
    'Specialists 2': '专家2',
    'Enemies': '敌人',
    'Training': '训练',
    'DS Soldiers': '沙漠士兵',
    'GR vehicles': '幽灵行动车辆',
    'DS vehicles': '沙漠车辆',
    'Ghost Recon': '幽灵行动',
}
for _i in range(1, 16):
    GROUP_ZH['GR Mission %d' % _i] = '幽灵行动®任务%d' % _i
for _i in range(1, 9):
    GROUP_ZH['DS Mission %d' % _i] = '沙漠风暴任务%d' % _i
    GROUP_ZH['DS mission %d' % _i] = '沙漠风暴任务%d' % _i


def load_charset():
    c = json.load(open(CHARSET, encoding='utf-8'))
    return dict(c['codes']), {k: tuple(v) for k, v in c['pair_of'].items()}


def enc(zh, codes, pairs):
    o = bytearray()
    for ch in zh:
        if ord(ch) < 0x80:
            o.append(ord(ch))
        elif ch in codes:
            o.append(codes[ch])
        elif ch in pairs:
            o += bytes(pairs[ch])
        else:
            raise AssertionError('字表无此字: %r' % ch)
    return bytes(o)


def subs_of(raw):
    subs, p = [], 0
    while p + 8 <= len(raw):
        L, S = struct.unpack_from('<II', raw, p)
        if L == 0 or p + 8 + L > len(raw):
            break
        try:
            dd, err, _ = lzo1x_decompress(raw[p + 8:p + 8 + L], out_size=S)
        except Exception:
            break
        if err is not None:
            break
        subs.append((bytes(dd), L, S))
        p += 8 + L
    return subs


def entry(d, idx, lba=MENU_LBA):
    base = lba * 2048
    r = struct.unpack_from('<12I', d, base + TAB_OFF + TAB_STEP * idx)
    return base, r[6], r[7], r[8]


def main(src, dst):
    codes, pairs = load_charset()
    sd = open(src, 'rb').read()
    base, stored, real, off = entry(sd, XML_IDX)
    subs = subs_of(sd[base + off:base + off + stored])
    assert len(subs) == 8, '子流 %d' % len(subs)
    xml = b''.join(s[0] for s in subs)
    assert len(xml) == real, 'XML %d != real %d' % (len(xml), real)
    print('[in] XML %d B (槽 %d)' % (len(xml), stored))

    # 键: 英文原名 或 现有中文 (zh7 遗留格式) —— 统一用**字节**做键
    ITEM_LOOKUP = {}     # bytes -> 中文
    GROUP_LOOKUP = {}
    for en, zh in ITEM_ZH.items():
        ITEM_LOOKUP[en.encode('latin-1')] = zh
    for legacy_en, legacy_zh in (('GR Opening', 'GR 片头'), ('GR Ending', 'GR 片尾'),
                                 ('DS Opening', 'DS 片头'), ('DS Ending', 'DS 片尾')):
        ITEM_LOOKUP[legacy_zh.encode('utf-8')] = ITEM_ZH[legacy_en]
        ITEM_LOOKUP[enc(legacy_zh, codes, pairs)] = ITEM_ZH[legacy_en]
    for _i in range(1, 16):
        for _p in ('GR',):
            ITEM_LOOKUP[('%s 任务 %d' % (_p, _i)).encode('utf-8')] = '幽灵行动®任务%d' % _i
            ITEM_LOOKUP[('%s 任务 %d' % (_p, _i)).encode('utf-8')] = \
                ITEM_LOOKUP[('%s 任务 %d' % (_p, _i)).encode('utf-8')]
            ITEM_LOOKUP[enc('%s 任务 %d' % (_p, _i), codes, pairs)] = '幽灵行动®任务%d' % _i
    for _i in range(1, 9):
        ITEM_LOOKUP[enc('DS 任务 %d' % _i, codes, pairs)] = '沙漠风暴任务%d' % _i
    for en, zh in GROUP_ZH.items():
        GROUP_LOOKUP[en.encode('latin-1')] = zh
        GROUP_LOOKUP[enc(zh, codes, pairs)] = zh          # 上一版补过空格/已中文的情况
        GROUP_LOOKUP[enc(zh, codes, pairs) + b' ' * 8] = zh

    pat = re.compile(rb'<(item|group|studio)(\s[^>]*?)name="([^"]*)"')
    out = bytearray()
    pos = 0
    cnt = {'item': 0, 'group': 0, 'studio': 0}
    miss = []
    for m in pat.finditer(xml):
        kind = m.group(1).decode()
        raw = m.group(3)
        if kind == 'studio':
            continue                                   # studio 保持英文 (引擎内部标识)
        if kind == 'item':
            zh = ITEM_LOOKUP.get(raw)
            if zh is None:
                zh = ITEM_LOOKUP.get(raw.rstrip(b' '))
            if zh is None and (raw.startswith(b'GR ') or raw.startswith(b'DS ')):
                miss.append(raw)
                continue
        else:
            zh = GROUP_LOOKUP.get(raw)
            if zh is None:
                zh = GROUP_LOOKUP.get(raw.rstrip(b' '))
        if zh is None:
            continue
        nb = enc(zh, codes, pairs)
        out += xml[pos:m.start(3)] + nb               # **零填充**
        pos = m.end(3)
        cnt[kind] += 1
    out += xml[pos:]
    new_xml = bytes(out)
    print('[xml] item %d 处 + group %d 处已重译 (零空格); studio 保持英文'
          % (cnt['item'], cnt['group']))
    if miss:
        print('[warn] 未覆盖的 GR/DS item (%d): %r' % (len(miss), sorted(set(miss))[:8]))
    assert cnt['item'] == 25, 'item 仅改 %d 处 (期望 25)' % cnt['item']
    assert cnt['group'] == 41, 'group 仅改 %d 处 (期望 41)' % cnt['group']
    assert not miss, '仍有未覆盖的 GR/DS item: %r' % sorted(set(miss))[:8]
    # 断言: 新 XML 里 GR/DS 开头的 name 已清零
    left = [m.group(1) for m in re.finditer(rb'name="((?:GR|DS) [^"]*)"', new_xml)]
    assert not left, '仍有未译 GR/DS name: %s' % left[:5]
    # 断言: 无 0x20 填充尾巴
    for m in re.finditer(rb'name="([^"]*)"', new_xml):
        v = m.group(1)
        assert not v.endswith(b' '), '仍有尾随空格: %r' % v
    print('[check] 无 GR/DS 残留 name; 无尾随空格 ✓')
    print('[size] XML %d → %d B (%+d)' % (len(xml), len(new_xml), len(new_xml) - len(xml)))

    # ── 重划 8 子流 (前 7×16384 + 余数) 并重压 ──
    sizes = [16384] * 7
    rem = len(new_xml) - 16384 * 7
    assert rem > 0, '内容不足以切 8 子流'
    sizes.append(rem)
    frame = bytearray()
    q = 0
    for k, S in enumerate(sizes):
        chunk = new_xml[q:q + S]
        q += S
        c = lzo_compress(chunk, level=7, use_m1=True, use_m4=True)
        back, err, _ = lzo1x_decompress(c, out_size=S)
        assert err is None and back == chunk, '子流 %d 回环失败' % k
        frame += struct.pack('<II', len(c), S) + c
    assert len(frame) <= stored, '超槽 %+d' % (len(frame) - stored)
    print('[pack] %d B (槽 %d, 余 %d)' % (len(frame), stored, stored - len(frame)))

    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(base + off)
        f.write(bytes(frame) + b'\x00' * (stored - len(frame)))
        f.seek(base + off)
        rb = subs_of(f.read(stored))
        joined = b''.join(s[0] for s in rb)
        assert joined == new_xml, '回读不符'
    print('[verify] 回读 8 子流逐字节一致 ✓')

    a, b = open(src, 'rb').read(), open(dst, 'rb').read()
    assert len(a) == len(b), 'ISO 尺寸变化'
    mbase = MENU_LBA * 2048
    assert a[mbase:mbase + TAB_OFF] == b[mbase:mbase + TAB_OFF], 'MENU 头部被改'
    assert a[mbase + TAB_OFF:mbase + TAB_OFF + TAB_STEP * 700] == \
        b[mbase + TAB_OFF:mbase + TAB_OFF + TAB_STEP * 700], '条目表被改'
    print('[verify] 尺寸/头部/条目表 未动 ✓')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1], sys.argv[2])
