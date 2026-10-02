#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

r"""gr_build.py — GR.IMG 侧汉化一键构建 (教程句 + 武器名/动作名 + 队友名 + 字库)

配方 (与 MENU 侧 ZH8 完全同源, 见 han_v2\FONT_CAPACITY.md §九 与 han_v2\GR_SIDE.md):
  字库   GR.IMG 的 FONT.RES (stored=4421/real=7222) 与 COMMON.PAK (stored==real=400659)
         与 MENU.IMG 原版逐字节一致 (本脚本强制对账后) → 直接复用 ZH8 产物:
         ft_slot_zh8.bin (4421B DP 帧, 展开 5302B) + COMMON_PAK_ZH8.bin (atlas 仅
         0x1069..+262144 表面变化, 其余字节与原版一致, 本脚本复验)。
  教程句 GR.IMG EN_STRINGS.RES (off/stored/real = 212604752/47619/128668, 8 子流
         [16384]×7+[13980]) 原位覆写压缩帧; 译文 = trans_zh8.csv 的 G12-G18 (232 条,
         MENU 侧已上屏配方) + G13-G18.I030 训练标题 6 条; 其余条目做 v6 装饰修复
         ([0xA4..0xAD] 后随 ≥0xA1 时插 0x20)。
  武器名 GR.IMG STRINGS.TXT (stored=2587 < real=6561, 单子流 LZO) — 解码→明文换值→
         **空隙重定位** (MENU 侧 EN_STRINGS.TXT 同款实证工艺): 未压缩写到 BNK 空隙
         481042432 (6MB), 条目表仅动该行 stored/real/off。
  队友名 训练 TOE 5 名 Ghost 的 .ATR (纯 XML, stored==real): ActorName 换 ZH8 单字节
         码 (0xAF-0xFE 非保留, 不经 lead/cave 路径, 规避 nav25 指令面板挂死风险),
         尾部空格补齐原字节长。
  自检   容器/子流/槽回环 + 差异白名单 (FONT 槽+PAK+RES 槽+TXT 表行+空隙+5×ATR)
         + 条目表其余 4069 行逐字节不动 + 补丁副本尺寸不变 (ISO LBA 不变)。
  组装   GR_ZH9.iso = ZH8b 终盘 ISO（SLUS_P_V7.elf，默认）原样拷贝 + 上述白名单字节
         @LBA 19175 原位写入。

用法: python gr_build.py [--work DIR] [--base-iso ISO] [--out-iso ISO] [--skip-iso]
输入依赖:
  hanliu\texts\{gr_res_en.csv(对账用), pc_official_zh.csv, txt_family.csv}
  C:\gr_build\tmp\zh8\{trans_zh8.csv, ft_slot_zh8.bin, COMMON_PAK_ZH8.bin, charset_zh8.json}
  C:\gr_build\tmp\gr_zh\GR_base.img (干净 GR.IMG, 与 ISO LBA19175 区哈希对账)
  C:\gr_build\iso\GR_ZH8.iso (ZH9 基底; 可 --base-iso 换 ZH8b)
"""
import argparse
import csv
import json
import os
import re
import struct
import sys
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lz77_decode import lzo1x_decompress, decode_entry      # noqa: E402
from lzo1x_c import compress as lzo_compress                # noqa: E402

HAN = os.path.join(REPO_ROOT, 'docs', 'han_v2')
HANLIU = os.path.dirname(os.path.abspath(__file__))
ZH8 = os.path.join(REPO_ROOT, 'work', 'tmp', 'zh8')
GRZH = os.path.join(REPO_ROOT, 'work', 'tmp', 'gr_zh')
GR_LBA = 19175
SECTOR = 2048

# ---- GR.IMG 关键槽位 (构建时逐项与档案对账) ----
SLOT = {
    'EN_STRINGS.RES': dict(off=212604752, stored=47619, real=128668),
    'FONT.RES':       dict(off=212710976, stored=4421,  real=7222),
    'COMMON.PAK':     dict(off=236797520, stored=400659, real=400659),
    'STRINGS.TXT':    dict(off=213086608, stored=2587,  real=6561),
}
GR_REAL, GR_SLOT = 128668, 47619
CHUNKS = [16384] * 7 + [13980]
TXT_GAP = 481042432          # BNK_95_05 与 BNK_96_01 间 6MB 空隙起点 (音频库间垫, 引擎不读)
ATR_NAMES = {                # 训练 TOE 5 名 Ghost (rifleman-01 为首选队员/玩家池)
    'RIFLEMAN-01.ATR': '何斗',   # Corey Moss
    'RIFLEMAN-11.ATR': '小雷',   # Samuel Beard
    'RIFLEMAN-48.ATR': '雷一枪',  # Horace Dominguez (Alpha 组长)
    'RIFLEMAN-58.ATR': '火枪',   # Garner Maxwell
    'RIFLEMAN-59.ATR': '向前',   # Trent Norris
}


def log(msg):
    print(msg, flush=True)


def rd(f, off, n):
    f.seek(off)
    return f.read(n)


def load_entries(data):
    names_off = struct.unpack_from('<I', data, 0x10)[0]
    tab_end = struct.unpack_from('<I', data, 4)[0]
    names = [x.decode('latin-1') for x in data[names_off:tab_end].split(b'\x00') if x]
    ents = {}
    for i, nm in enumerate(names):
        r = struct.unpack_from('<12I', data, 0x830 + 48 * i)
        ents[nm] = {'i': i, 'name': nm, 'stored': r[6], 'real': r[7], 'off': r[8]}
    return ents


# ---------------------------------------------------------------- 译文集

def build_trans(charset):
    """GR 侧 RES 译文 = trans_zh8 G12-G18 + G13-G18.I030 训练标题 (字表校验)。"""
    known = set(charset['singles']) | set(charset['pair_of'])
    titles = {
        'G13.I030': '训练2 - 轻型武器',
        'G14.I030': '训练3 - 榴弹',
        'G15.I030': '训练4 - 重武器',
        'G16.I030': '训练5 - 机枪',
        'G17.I030': '训练6 - 爆破',
        'G18.I030': '训练7 - 指挥',
    }
    trans = {}
    for r in csv.DictReader(open(ZH8 + r'\trans_zh8.csv', encoding='utf-8-sig')):
        g = r['key'].split('.')[0]
        if g in ('G12', 'G13', 'G14', 'G15', 'G16', 'G17', 'G18') and r['zh']:
            trans[r['key']] = r['zh']
    n_zh8 = len(trans)
    for k, v in titles.items():
        assert k not in trans
        trans[k] = v
    for k, v in trans.items():
        bad = [c for c in v if ord(c) > 0x7E and c not in known]
        assert not bad, (k, bad)
    log('[TRANS] trans_zh8 复用 %d 条 + 新增训练标题 %d 条 = %d 条'
        % (n_zh8, len(titles), len(trans)))
    return trans


def encode_text(text, charset, key):
    """ZH8 v6 编码: 单字节 0xAF-0xFE 非保留 / 对 (0xA1..0xAD)+(0xA1..0xFE) / ASCII。"""
    codes = {k: int(v) for k, v in charset['singles'].items()}
    pair_of = {k: tuple(v) for k, v in charset['pair_of'].items()}
    b = bytearray()
    for ch in text:
        if ch in codes:
            assert codes[ch] not in (0xA1, 0xA2, 0xA3), (key, ch)
            b.append(codes[ch])
        elif ch in pair_of:
            b += bytes(pair_of[ch])
        else:
            v = ord(ch)
            assert 0x20 <= v < 0x7F, '%s: 字表外字符 %r' % (key, ch)
            b.append(v)
    assert not any(0x80 <= x <= 0x9F for x in b), key
    return bytes(b)


# ---------------------------------------------------------------- RES

def decode_blob(fr):
    p, out = 0, []
    while p + 8 <= len(fr):
        plen, o = struct.unpack_from('<II', fr, p)
        dec, err, _ = lzo1x_decompress(fr[p + 8:p + 8 + plen], out_size=o)
        assert err is None and len(dec) == o
        out.append(dec)
        p += 8 + plen
    return b''.join(out)


def walk_container(data):
    p = 0
    ng = struct.unpack_from('<I', data, p)[0]
    p += 4
    groups, attrs = [], []
    for g in range(ng):
        if g > 0:
            p += 4
        cnt = struct.unpack_from('<I', data, p)[0]
        p += 4
        st, at = [], []
        for _ in range(cnt):
            ln = struct.unpack_from('<I', data, p)[0]
            p += 4
            st.append(bytearray(data[p:p + ln]))
            at.append(struct.unpack_from('<H', data, p + ln)[0])
            p += ln + 2
        groups.append(st)
        attrs.append(at)
    assert data[p:p + 8] == b'\x00' * 8
    return groups, attrs, p + 8


def serialize_container(groups, attrs, total):
    o = bytearray()
    o += struct.pack('<I', len(groups))
    for gi, st in enumerate(groups):
        if gi:
            o += struct.pack('<I', 0)
        o += struct.pack('<I', len(st))
        for i, s in enumerate(st):
            o += struct.pack('<I', len(s)) + bytes(s) + struct.pack('<H', attrs[gi][i])
    o += b'\x00' * 8
    assert len(o) <= total, (len(o), total)
    o += b'\x00' * (total - len(o))
    return bytes(o)


def decor_fix(b):
    """v6 装饰修复: [0xA4..0xAD] 后随 >=0xA1 → 插 0x20 (防 13-lead 合并)。"""
    out = bytearray()
    i, ch = 0, False
    while i < len(b):
        v = b[i]
        if 0xA4 <= v <= 0xAD and i + 1 < len(b) and b[i + 1] >= 0xA1:
            out += bytes((v, 0x20))
            ch = True
            i += 1
        else:
            out.append(v)
            i += 1
    return bytes(out), ch


def build_res_blob(base_res_frame, trans, charset):
    """解码 GR RES 容器 → 换译文 → 复刻 8 子流布局重压缩; 返回 (blob, 容器)。"""
    cont = decode_blob(base_res_frame)
    assert len(cont) == GR_REAL, len(cont)
    groups, attrs, _ = walk_container(cont)
    n_tr = n_fx = 0
    for gi, st in enumerate(groups):
        for ii in range(len(st)):
            key = 'G%02d.I%03d' % (gi + 1, ii)
            if key in trans:
                st[ii] = bytearray(encode_text(trans[key], charset, key))
                n_tr += 1
            else:
                fx, ch = decor_fix(bytes(st[ii]))
                if ch:
                    st[ii] = bytearray(fx)
                    n_fx += 1
    log('[RES] 翻译 %d 条 + 装饰修复 %d 条' % (n_tr, n_fx))
    cont2 = serialize_container(groups, attrs, GR_REAL)
    assert walk_container(cont2)[0] == groups
    pos, frames = 0, []
    for csz in CHUNKS:
        chunk = cont2[pos:pos + csz]
        assert len(chunk) == csz
        pl = lzo_compress(chunk, level=7, use_m1=True, use_m4=True)
        back, err, _ = lzo1x_decompress(pl, out_size=csz)
        assert err is None and back == chunk
        frames.append(struct.pack('<II', len(pl), csz) + pl)
        pos += csz
    blob = b''.join(frames)
    assert decode_blob(blob) == cont2
    log('[RES] blob %dB (槽限 %d, 余 %d)' % (len(blob), GR_SLOT, GR_SLOT - len(blob)))
    assert len(blob) <= GR_SLOT
    return blob, cont2


# ---------------------------------------------------------------- TXT

def build_txt(decoded_txt, pc_official, family_gr, charset):
    """STRINGS.TXT 明文换值 (Token→显示名); 返回新明文 bytes + 替换清单。"""
    known = set(charset['singles']) | set(charset['pair_of'])
    # 官方中文名 (pc_official source=strings.txt), 仅取与 EN 值不同且含汉字的
    zh_of = {}
    for r in pc_official:
        if r['source'] != 'strings.txt':
            continue
        v = r['value']
        if v == r.get('_en', '') or not any('\u4e00' <= c <= '\u9fff' for c in v):
            continue
        bad = [c for c in v if ord(c) > 0x7E and c not in known]
        if not bad:
            zh_of[r['key']] = v
    # 字表外官方名的人工适配 (宁少勿错: 只做纯字表内字的保守替换)
    adapt = {'WPN_FRAG': '手雷', 'WPN_M9SD': 'M9-消音', 'WPN_MP5SD': 'MP5-消音',
             'WPN_EXTRAAMMO': '备用弹', 'ITM_BINOCULARS': '观测镜',
             'all_teams_engage': '所有小组攻击'}
    for k, v in adapt.items():
        bad = [c for c in v if ord(c) > 0x7E and c not in known]
        if not bad:
            zh_of.setdefault(k, v)
    txt = decoded_txt.decode('latin-1')
    out_lines, hits = [], []
    for line in txt.split('\r\n'):
        m = re.match(r'^(\t"([^"]+)"\t+)"([^"]*)"(\s*)$', line)
        if m and m.group(2) in zh_of:
            key = m.group(2)
            enc = encode_text(zh_of[key], charset, key)
            assert not any(c in '"\t\r\n' for c in zh_of[key])
            out_lines.append('%s"%s"' % (m.group(1), enc.decode('latin-1')))
            hits.append((key, m.group(3), zh_of[key]))
        else:
            out_lines.append(line)
    log('[TXT] 官方中文名可用 %d 键, 实际替换 %d 行' % (len(zh_of), len(hits)))
    for k, en, zh in hits[:12]:
        log('   %-18s %-14s -> %s' % (k, en, zh))
    new = '\r\n'.join(out_lines)
    assert len(new) >= len(decoded_txt) - 4096  # 防灾难性丢失; 中文 2B/字常比 EN 短属正常
    return new.encode('latin-1'), hits


# ---------------------------------------------------------------- 主流程

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=HAN + r'\tmp\gr_side')
    ap.add_argument('--base-img', default=GRZH + r'\GR_base.img')
    ap.add_argument('--base-iso', default=os.path.join(REPO_ROOT, 'build', 'iso', 'GR_ZH8b.iso'))
    ap.add_argument('--out-iso', default=os.path.join(REPO_ROOT, 'build', 'iso', 'GR_ZH9.iso'))
    ap.add_argument('--skip-iso', action='store_true')
    ap.add_argument('--no-atr', action='store_true',
                    help='跳过 5×ATR 队友名补丁 (判别实验用)')
    args = ap.parse_args(argv)
    os.makedirs(args.work, exist_ok=True)

    # ========== 0. 基底对账: GR_base.img 必须与干净档案一致 ==========
    log('== [0] 基底对账 ==')
    img_path = args.work + r'\GR.img'
    if not os.path.exists(img_path):
        shutil.copyfile(args.base_img, img_path)
        log('   复制干净基底 → %s (%d B)' % (img_path, os.path.getsize(img_path)))
    img = open(img_path, 'rb').read()
    assert len(img) == 1550563328, len(img)
    ents = load_entries(img)
    for nm, want in SLOT.items():
        e = ents[nm]
        assert (e['off'], e['stored'], e['real']) == (want['off'], want['stored'], want['real']), \
            (nm, e, want)
    log('   条目表槽位对账 PASS (RES/FONT/PAK/TXT off-stored-real 与已确证值一致)')
    # FONT/PAK 与 MENU 原版一致性 (ZH8 产物可复用的前提)
    menu_orig = open(HAN + r'\menu_orig\MENU.IMG', 'rb').read()
    m_ents = load_entries(menu_orig)
    gr_font = decode_entry(img[SLOT['FONT.RES']['off']:SLOT['FONT.RES']['off'] + 4421])[0]
    me_font = decode_entry(menu_orig[m_ents['FONT.RES']['off']:m_ents['FONT.RES']['off'] + 4421])[0]
    assert gr_font == me_font and len(gr_font) == 7222, 'GR/MENU FONT.RES 展开态不一致'
    gr_pak = img[SLOT['COMMON.PAK']['off']:SLOT['COMMON.PAK']['off'] + 400659]
    me_pak = menu_orig[m_ents['COMMON.PAK']['off']:m_ents['COMMON.PAK']['off'] + 400659]
    assert gr_pak == me_pak, 'GR/MENU COMMON.PAK 不一致'
    log('   GR FONT.RES 展开 7222B == MENU 原版; GR COMMON.PAK 400659B == MENU 原版 PASS')

    charset = json.load(open(ZH8 + r'\charset_zh8.json', encoding='utf-8'))

    # ========== 1. 字库: ZH8 槽帧 + atlas 写入 GR 槽位 ==========
    log('== [1] 字库 (ZH8 同源独立写回) ==')
    ft_slot = open(ZH8 + r'\ft_slot_zh8.bin', 'rb').read()
    assert len(ft_slot) == 4421
    ft_back, ft_stats = decode_entry(ft_slot)
    assert len(ft_back) == 5302 and all(not s[3] for s in ft_stats), 'ft_slot 回环失败'
    pak8 = open(ZH8 + r'\COMMON_PAK_ZH8.bin', 'rb').read()
    assert len(pak8) == 400659
    SURF, N = 0x1069, 512 * 512
    out_of_atlas = [i for i in range(400659)
                    if pak8[i] != me_pak[i] and not (SURF <= i < SURF + N)]
    assert not out_of_atlas, 'ZH8 PAK 差异越出 atlas 表面: %d' % len(out_of_atlas)
    log('   ft_slot 4421B 回环 PASS (展开 5302B); PAK 差异全部在 atlas 表面内 PASS')

    out = bytearray(img)
    e = ents['FONT.RES']
    out[e['off']:e['off'] + 4421] = ft_slot
    e = ents['COMMON.PAK']
    out[e['off']:e['off'] + 400659] = pak8

    # ========== 2. 教程句 (EN_STRINGS.RES 8 子流原位覆写) ==========
    log('== [2] 教程句 G12-G18 ==')
    trans = build_trans(charset)
    e = ents['EN_STRINGS.RES']
    base_frame = img[e['off']:e['off'] + e['stored']]
    blob, cont2 = build_res_blob(base_frame, trans, charset)
    out[e['off']:e['off'] + len(blob)] = blob
    open(args.work + r'\gr_res_zh_blob.bin', 'wb').write(blob)
    open(args.work + r'\gr_res_container.bin', 'wb').write(cont2)

    # ========== 3. 武器/动作名 (STRINGS.TXT 解码→换值→空隙重定位) ==========
    log('== [3] 武器/动作名 STRINGS.TXT ==')
    e = ents['STRINGS.TXT']
    txt_dec, st = decode_entry(img[e['off']:e['off'] + e['stored']])
    assert not any(s[3] for s in st) and len(txt_dec) == e['real']
    texts_dir = os.path.join(os.path.dirname(HANLIU), 'texts')
    pc_official = list(csv.DictReader(
        open(os.path.join(texts_dir, 'pc_official_zh.csv'), encoding='utf-8-sig')))
    family_gr = [r for r in csv.DictReader(
        open(os.path.join(texts_dir, 'txt_family.csv'), encoding='utf-8-sig'))
        if r['source'] == 'GR' and r['lang'] == 'EN']
    fam_en = {r['key']: r['value'] for r in family_gr}
    for r in pc_official:
        r['_en'] = fam_en.get(r['key'], '\x00')
    txt_new, hits = build_txt(txt_dec, pc_official, family_gr, charset)
    # 自检: token 键集不变 (仅取行首第一个引号字段)
    keypat = re.compile(r'^\t"([^"]+)"\t+', re.M)
    toks0 = set(keypat.findall(txt_dec.decode('latin-1')))
    toks1 = set(keypat.findall(txt_new.decode('latin-1')))
    assert toks0 == toks1, ('token 集变化', list(toks0 ^ toks1)[:5])
    # 空隙区=BNK_95_05.SS 与 BNK_96_01.SS 间 6MB 垫区, 不与任何条目重叠
    gap_end = TXT_GAP + 6291456
    assert TXT_GAP + len(txt_new) <= gap_end
    out[TXT_GAP:TXT_GAP + len(txt_new)] = txt_new
    # 条目表仅动 STRINGS.TXT 行的 stored/real/off
    row = 0x830 + 48 * e['i']
    assert out[row:row + 48] == img[row:row + 48]
    struct.pack_into('<I', out, row + 24, len(txt_new))
    struct.pack_into('<I', out, row + 28, len(txt_new))
    struct.pack_into('<I', out, row + 32, TXT_GAP)
    open(args.work + r'\gr_strings_zh.txt', 'wb').write(txt_new)
    json.dump([{'key': k, 'en': a, 'zh': b} for k, a, b in hits],
              open(args.work + r'\txt_hits.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    log('[TXT] 新明文 %dB (原 6561B) → 空隙 @%d, 条目表行 %d 更新' % (len(txt_new), TXT_GAP, e['i']))

    # ========== 4. 队友名 (5×ATR ActorName 单字节码 + 空格补齐) ==========
    log('== [4] 队友名 ATR ==')
    atr_patches = {}
    for nm, zh in ([] if args.no_atr else ATR_NAMES).items():
        e = ents[nm]
        assert e['stored'] == e['real']
        raw = img[e['off']:e['off'] + e['stored']].decode('latin-1')
        m = re.search(r'<ActorName>([^<]*)</ActorName>', raw)
        assert m, nm
        old, new = m.group(1), encode_text(zh, charset, nm).decode('latin-1')
        assert len(new) <= len(old), (nm, len(new), len(old))
        padded = new + ' ' * (len(old) - len(new))
        raw2 = raw[:m.start(1)] + padded + raw[m.end(1):]
        assert len(raw2) == len(raw)
        out[e['off']:e['off'] + e['stored']] = raw2.encode('latin-1')
        atr_patches[nm] = {'old': old, 'zh': zh, 'bytes': padded.encode('latin-1').hex(),
                           'off': e['off'], 'len': e['stored']}
        log('   %-18s %-16s -> %s' % (nm, old, zh))
    json.dump(atr_patches, open(args.work + r'\atr_patch.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    # ========== 5. 差异白名单自检 + 写补丁副本 ==========
    log('== [5] 差异白名单自检 ==')
    white = [(ents['FONT.RES']['off'], ents['FONT.RES']['off'] + 4421),
             (ents['COMMON.PAK']['off'], ents['COMMON.PAK']['off'] + 400659),
             (ents['EN_STRINGS.RES']['off'], ents['EN_STRINGS.RES']['off'] + len(blob)),
             (TXT_GAP, TXT_GAP + len(txt_new))]
    for nm in ([] if args.no_atr else ATR_NAMES):
        e = ents[nm]
        white.append((e['off'], e['off'] + e['stored']))
    row = 0x830 + 48 * ents['STRINGS.TXT']['i']
    white.append((row + 24, row + 36))
    assert len(out) == len(img)
    ranges, badn, i, n = [], 0, 0, len(img)
    CH = 1 << 22
    while i < n:
        j = 0
        a = out[i:i + CH]
        b = img[i:i + CH]
        if a != b:
            for k in range(len(a)):
                if a[k] != b[k]:
                    if ranges and ranges[-1][1] == i + k:
                        ranges[-1][1] = i + k + 1
                    else:
                        ranges.append([i + k, i + k + 1])
                    badn += 1
        i += CH
    bad = [r for r in ranges if not any(r[0] >= lo and r[1] <= hi for lo, hi in white)]
    log('   差异 %d 字节 / %d 区段; 白名单外区段 %d' % (badn, len(ranges), len(bad)))
    for r in bad[:10]:
        log('   BAD %s' % (r,))
    assert not bad and badn > 1000
    # 条目表全量复验: 除 TXT 行 stored/real/off 12B 外逐字节不动 (k 为表内相对偏移)
    tab_a = out[0x830:0x830 + 48 * len(ents)]
    tab_b = img[0x830:0x830 + 48 * len(ents)]
    rel = 48 * ents['STRINGS.TXT']['i']
    d = [k for k in range(len(tab_a)) if tab_a[k] != tab_b[k]]
    assert d and all(rel + 24 <= k < rel + 36 for k in d), '条目表被越权改动 %s' % (d[:8],)
    open(args.work + r'\GR_patched.img', 'wb').write(bytes(out))
    log('   条目表差异仅 STRINGS.TXT 行 PASS; 补丁副本 → GR_patched.img')

    # ========== 6. 组装 GR_ZH9.iso ==========
    if args.skip_iso:
        log('== [6] 跳过 ISO 组装 ==')
        return
    log('== [6] 组装 %s ==' % args.out_iso)
    assert os.path.exists(args.base_iso), args.base_iso
    if os.path.abspath(args.out_iso) != os.path.abspath(args.base_iso):
        shutil.copyfile(args.base_iso, args.out_iso)
    with open(args.out_iso, 'r+b') as f:
        for lo, hi in sorted(white):
            f.seek(GR_LBA * SECTOR + lo)
            f.write(out[lo:hi])
    log('   白名单 %d 区段已写入 LBA %d; 尺寸 %d B' %
        (len(white), GR_LBA, os.path.getsize(args.out_iso)))
    log('[BUILD] GR_ZH9 PASS')


if __name__ == '__main__':
    main()
