# -*- coding: utf-8 -*-
r"""patch_zh78.py — 特别收录分栏标题汉化 + GR/DS 前缀文案改"幽灵行动/沙漠风暴" (GR_ZH78)

用户报障 (第三、四条):
  ① 主菜单→特别收录→设定图/屏幕截图 里几个分栏标题 (Soldiers/Enemies 之类) 未翻译;
  ② "GR任务" 应译作 "幽灵行动®任务" (GR → 幽灵行动)。

修改面 (全部在 MENU.IMG, 纯数据, 零 ELF):
  A. EN_SPECIAL_FEATURE.XML (#283): 51 个 `<studio|group name="...">` 英文分栏名 → 中文,
     **等长原位覆写** (不足补空格; XML 属性值内补空格安全, 同 ATR 做法)。
     GR Mission N → 幽灵行动®任务N ; DS Mission N → 沙漠风暴任务N ; 其余见 assets_zh78。
  B. EN_STRINGS.RES (#25): 子流 3 里 4 条菜单短串 (GR任务/DS任务/GR联机/DS联机, 各 6 B)
     → 幽灵行动®任务(11B)/沙漠风暴任务(10B)/幽灵行动联机(11B)/沙漠风暴联机(12B)
     —— 超出原 6B 槽位, 故走 **RES 重编码** (8 子流框架重打包 + LZO), 槽长 47,570 B 不变。

  注: 两处的编码都是 zh16 字表 (汉字对偶/单字节码, ASCII 直通)。

用法: python patch_zh78.py <src_iso> <dst_iso>   (基底 = GR_ZH77)
"""
import json
import os
import re
import shutil
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'hanliu', 'tools'))
from lz77_decode import lzo1x_decompress                      # noqa: E402
from lzo1x_c import compress as lzo_compress                  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
MENU_LBA = 776286
TAB_OFF, TAB_STEP = 0x830, 48
XML_IDX = 283
RES_IDX = 25
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
ASSET = os.path.join(HERE, 'assets_zh78', 'sf_titles_zh78.json')

RE_GRP = re.compile(rb'<(studio|group)\s+name="([^"]*)"')
# RES 子流 3 里的四条菜单短串 (实际字节见 work/_dis/res_gr_bytes.py 实测):
#   "GR" + da c9 (任务) / "DS" + da c9 ; "GR"/"DS" + a5 ed a1 a5 (联机)
RES_PAIRS = [
    (b'GR\xda\xc9', 'GR任务', '幽灵行动®任务'),
    (b'DS\xda\xc9', 'DS任务', '沙漠风暴任务'),
    (b'GR\xa5\xed\xa1\xa5', 'GR联机', '幽灵行动联机'),
    (b'DS\xa5\xed\xa1\xa5', 'DS联机', '沙漠风暴联机'),
]


def load_charset():
    c = json.load(open(CHARSET, encoding='utf-8'))
    return dict(c['codes']), {k: list(v) for k, v in c['pair_of'].items()}


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


def dec(b, codes, pairs):
    inv_c = {v: k for k, v in codes.items()}
    inv_p = {tuple(v): k for k, v in pairs.items()}
    o, i = [], 0
    while i < len(b):
        if b[i] < 0x80:
            o.append(chr(b[i])); i += 1
        elif i + 1 < len(b) and (b[i], b[i + 1]) in inv_p:
            o.append(inv_p[(b[i], b[i + 1])]); i += 2
        elif b[i] in inv_c:
            o.append(inv_c[b[i]]); i += 1
        else:
            o.append('?'); i += 1
    return ''.join(o)


def read_entry(d, base, idx):
    r = struct.unpack_from('<12I', d, base + TAB_OFF + TAB_STEP * idx)
    return r[6], r[7], r[8]


def res_subs(raw):
    subs, p = [], 0
    while p + 8 <= len(raw):
        L, S = struct.unpack_from('<II', raw, p)
        if L == 0 or p + 8 + L > len(raw):
            break
        dd, err, _ = lzo1x_decompress(raw[p + 8:p + 8 + L], out_size=S)
        subs.append((bytes(dd), L, S))
        p += 8 + L
    return subs


def res_frame(subs):
    out = bytearray()
    for plain, _L, _S in subs:
        comp = lzo_compress(plain, level=5)
        out += struct.pack('<II', len(comp), len(plain)) + comp
    return bytes(out)


def main(src, dst):
    codes, pairs = load_charset()
    titles = json.load(open(ASSET, encoding='utf-8'))
    print('[asset] 分栏译名 %d 条' % len(titles))

    shutil.copyfile(src, dst)
    base = MENU_LBA * 2048
    with open(dst, 'r+b') as f:
        # ---------- A. XML ----------
        stored, real, off = read_entry(open(src, 'rb').read(), base, XML_IDX)
        f.seek(base + off)
        raw = f.read(stored)
        subs = res_subs(raw)
        assert len(subs) == 8, 'XML 子流数 %d != 8' % len(subs)
        plain = b''.join(s[0] for s in subs)
        assert len(plain) == real, 'XML 长度异常 %d != %d' % (len(plain), real)
        buf = bytearray(plain)
        n = 0
        for m in RE_GRP.finditer(bytes(buf)):
            en = m.group(2).decode()
            zh = titles.get(en)
            if zh is None:
                continue
            v0 = m.start(2)
            nb = enc(zh, codes, pairs)
            assert len(nb) <= len(en), '分栏名超长 %r: %r %dB > %dB' % (en, zh, len(nb), len(en))
            buf[v0:v0 + len(en)] = nb + b' ' * (len(en) - len(nb))
            n += 1
        assert n == 51, 'XML 分栏只改了 %d 个 (期望 51)' % n
        xnew = bytes(buf)
        assert len(xnew) == len(plain)
        # 按原 8 子流边界重新切分打包 (每子流 real 不变)
        sizes = [len(s[0]) for s in subs]
        news, q = [], 0
        for k, sz in enumerate(sizes):
            news.append((xnew[q:q + sz], subs[k][1], subs[k][2]))
            q += sz
        assert q == len(xnew)
        frame = res_frame(news)
        assert len(frame) <= stored, 'XML 重压超槽 %d > %d' % (len(frame), stored)
        f.seek(base + off)
        f.write(frame + b'\x00' * (stored - len(frame)))
        print('[xml] 分栏标题汉化 %d 条; 重压 %dB (槽 %dB) ✓' % (n, len(frame), stored))

        # ---------- B. RES (双库: 用官方 text_replace.py --mode res 产出的重编码 blob) ----------
        # GR任务/DS任务/GR联机/DS联机 (G58.I724-727) 原文 6B, 新译 10-12B → 必须重编码。
        # 重编码由 tools/hanliu/tools/text_replace.py 生成 (见 build_probe 注释), 资产:
        #   assets_zh78/res_menu_zh78.bin / res_gr_zh78.bin (均为完整 8 子流 blob)
        menu_blob = open(os.path.join(HERE, 'assets_zh78', 'res_menu_zh78.bin'), 'rb').read()
        gr_blob = open(os.path.join(HERE, 'assets_zh78', 'res_gr_zh78.bin'), 'rb').read()
        targets = [('MENU', MENU_LBA, RES_IDX, menu_blob, 'EN_STRINGS.RES'),
                   ('GR', 19175, None, gr_blob, 'EN_STRINGS.RES')]
        for tag, lba, idx, blob, nm_want in targets:
            b2 = lba * 2048
            src_data = open(src, 'rb').read()
            if idx is None:
                noff = struct.unpack_from('<I', src_data, b2 + 0x10)[0]
                nend = struct.unpack_from('<I', src_data, b2 + 4)[0]
                nms = [x.decode('latin-1') for x in
                       src_data[b2 + noff:b2 + nend].split(b'\x00') if x]
                idx = nms.index(nm_want)
            stored, real, off = read_entry(src_data, b2, idx)
            assert len(blob) <= stored, '%s RES blob %d > 槽 %d' % (tag, len(blob), stored)
            f.seek(b2 + off)
            f.write(blob + b'\x00' * (stored - len(blob)))
            # 回读
            f.seek(b2 + off)
            back = f.read(stored)
            subs_b = res_subs(back)
            assert len(subs_b) == 8, '%s 回读子流 %d' % (tag, len(subs_b))
            joined = b''.join(s[0] for s in subs_b)
            for _old, _label, zh in RES_PAIRS:
                assert enc(zh, codes, pairs) in joined, '%s 回读缺 %r' % (tag, zh)
            print('[res:%s] 8 子流 blob %dB (槽 %dB) 回读 4 条新串 ✓' % (tag, len(blob), stored))

    # 条目表 / 头部 未动
    a, b = open(src, 'rb').read(), open(dst, 'rb').read()
    assert len(a) == len(b), 'ISO 尺寸变了'
    for lba, tag in ((MENU_LBA, 'MENU'), (19175, 'GR')):
        bb = lba * 2048
        assert a[bb:bb + TAB_OFF] == b[bb:bb + TAB_OFF], '%s 头部被改' % tag
        assert a[bb + TAB_OFF:bb + TAB_OFF + TAB_STEP * 700] == \
            b[bb + TAB_OFF:bb + TAB_OFF + TAB_STEP * 700], '%s 条目表被改' % tag
    print('[verify] MENU/GR 头部 + 条目表 未动 ✓')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1], sys.argv[2])
