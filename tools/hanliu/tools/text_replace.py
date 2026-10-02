#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""text_replace.py — 文本替换器: 翻译 CSV → RES blob / GR.IMG RES / TXT / ATR

编码规则 (与 GR_ZH7 实机 PASS 配方一致):
  字表内单字节字 → 该字码位 (1 字节);
  标记对字       → (lead,trail) 两字节 (lead ∈ {0xA1,0xA2,0xA3}, 配 SLUS_P_U ELF);
  其余           → ASCII 0x20-0x7E 原样;
  禁止           → 字表外汉字/全角符号(宁少勿错, 报错退出)、0x00、0x80-0x9F 毒区字节。

== 输入 CSV (utf-8-sig, 表头可省) ==
  key,en,zh
  G58.I003,Ok,确认          ← RES 条目 (组.条目号, 对应 texts\*_res_en.csv)
  WPN_FRAG,M4,爆裂手雷      ← TXT 键 (--mode txt)
  DXX.ATR:ActorName,Scott,斯科特   ← ATR 标签 (--mode atr)
en 列可留空; 非空且与库内原文不符 → 默认警告, --strict-en 时报错 (防串行)。

== 模式 ==
  --mode res  --base-res <8子流framed blob | 展开态> --target menu|gr
              输出: 复刻基底子流 osz 布局的 LZO1X 压缩 blob (menu ≤47,570B / gr ≤47,619B 槽检),
              内含解码回环自检; gr 侧超槽时同时产出展开态 (配 img_patch.py stored==real 重定位)。
  --mode txt  --base-txt <EN_STRINGS.TXT 解码态>  输出: 明文 .txt + framed .bin (配 img_patch --framed)
  --mode atr  --base-atr-dir <目录> --out-dir <目录>  重写 XML 标签 (默认仅允许 ASCII,
              中文需字表单字节码位并自负实机验证责任 — nav25 实证中文名可致指令面板挂死)

== 用法示例 ==
  python text_replace.py --mode res --charset charset_compiled.json \
      --input trans.csv --base-res en_strings_zh_8sub_v3.bin --target menu \
      --out en_strings_zh_8sub.bin
"""
import argparse
import csv
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lz77_decode import lzo1x_decompress, iter_substreams   # noqa: E402
from lzo1x_c import compress as lzo_compress                # noqa: E402

MENU_REAL, MENU_SLOT = 128545, 47570
GR_REAL, GR_SLOT = 128668, 47619


def die(msg):
    raise SystemExit('[text_replace] FAIL: ' + msg)


# ---------------------------------------------------------------- 编码

class Encoder:
    def __init__(self, charset_path):
        cs = json.load(open(charset_path, encoding='utf-8'))
        self.codes = {k: int(v) if not isinstance(v, int) else v
                      for k, v in cs.get('codes', {}).items()}
        self.pair_of = {k: tuple(v) for k, v in cs.get('pair_of', {}).items()}
        self.markers = set(cs.get('markers', []))
        self.mark_codes = set(int(c, 0) if isinstance(c, str) else c
                              for c in cs.get('mark_codes', ['0xA1', '0xA2', '0xA3']))

    def encode(self, text, where):
        b = bytearray()
        for ch in text:
            if ch in self.codes and ch not in self.markers:
                cd = self.codes[ch]
                if cd in self.mark_codes:
                    die('%s: 字符 %r 的码位 0x%02X 是标记码, 不得以单字节出现 '
                        '(该字应以对编码)' % (where, ch, cd))
                b.append(cd)
            elif ch in self.pair_of:
                l, t = self.pair_of[ch]
                b += bytes((l, t))
            else:
                v = ord(ch)
                if not (0x20 <= v < 0x7F):
                    die('%s: 字表外字符 %r (U+%04X) — 宁少勿错, 请扩充字表或改写文案'
                        % (where, ch, v))
                b.append(v)
        bad = [x for x in b if 0x80 <= x <= 0x9F]
        if bad:
            die('%s: 输出含毒区字节 0x%02X (0x80-0x9F 引擎毒)' % (where, bad[0]))
        if 0x00 in b:
            die('%s: 输出含 0x00' % where)
        return bytes(b)


# ---------------------------------------------------------------- RES

def decode_blob(fr):
    """framed blob → 展开态 (逐子流校验)。"""
    p, out = 0, []
    while p + 8 <= len(fr):
        plen, o = struct.unpack_from('<II', fr, p)
        dec, err, _ = lzo1x_decompress(fr[p + 8:p + 8 + plen], out_size=o)
        if err is not None or len(dec) != o:
            die('基底子流解码失败 @%d: %s' % (p, err))
        out.append(dec)
        p += 8 + plen
    return b''.join(out)


def parse_expanded_groups(data):
    """展开态 → (groups, attrs, consumed)。groups[g][i] = bytearray; attrs[g][i] = u16。"""
    p = 0
    ng = struct.unpack_from('<I', data, p)[0]
    p += 4
    groups, attrs = [], []
    for g in range(ng):
        if g > 0:
            p += 4                                    # sep u32 (恒 0, EN)
        cnt = struct.unpack_from('<I', data, p)[0]
        p += 4
        st, at = [], []
        for _i in range(cnt):
            ln = struct.unpack_from('<I', data, p)[0]
            p += 4
            st.append(bytearray(data[p:p + ln]))
            at.append(struct.unpack_from('<H', data, p + ln)[0])
            p += ln + 2
        groups.append(st)
        attrs.append(at)
    if data[p:p + 8] != b'\x00' * 8:
        die('展开态尾部缺 {0}{0} 终止符')
    return groups, attrs, p + 8


def serialize_exact(groups, attrs, total):
    out = bytearray()
    out += struct.pack('<I', len(groups))
    for gi, st in enumerate(groups):
        if gi:
            out += struct.pack('<I', 0)
        out += struct.pack('<I', len(st))
        for i, s in enumerate(st):
            out += struct.pack('<I', len(s)) + bytes(s)
            out += struct.pack('<H', attrs[gi][i])
    out += b'\x00' * 8
    if len(out) > total:
        die('译文展开态 %dB 超过槽容量 %dB — 宁少勿错, 请精简译文'
            % (len(out), total))
    out += b'\x00' * (total - len(out))
    return bytes(out)


def load_trans_csv(path):
    rows = []
    with open(path, 'r', encoding='utf-8-sig') as f:
        for ln_i, ln in enumerate(csv.reader(f), 1):
            if not ln or all(not x.strip() for x in ln):
                continue
            if ln_i == 1 and ln[0].strip().lower() == 'key':
                continue
            key = ln[0].strip()
            en = ln[1].strip() if len(ln) > 1 else ''
            zh = ln[2] if len(ln) > 2 else ''
            if not key or not zh:
                die('CSV 第 %d 行缺 key/zh: %r' % (ln_i, ln))
            rows.append((key, en, zh))
    if not rows:
        die('CSV 无有效翻译行')
    return rows


def parse_gi(key):
    m = re.fullmatch(r'G(\d+)\.I(\d+)', key)
    if not m:
        return None
    return int(m.group(1)) - 1, int(m.group(2))


def frame_chunks(base_expanded):
    """复刻基底的子流 osz 布局 (RES_AB_TEST 铁律: 不用单大子流)。"""
    osz = [o for (_pl, o, _f) in iter_substreams(base_expanded)]
    if not osz or sum(osz) < 16384:
        osz = [16384] * 7 + [13857]
    return osz


def do_res(a):
    enc = Encoder(a.charset)
    real = MENU_REAL if a.target == 'menu' else GR_REAL
    slot = MENU_SLOT if a.target == 'menu' else GR_SLOT
    base = open(a.base_res, 'rb').read()
    # 基底可为 framed 或展开态
    plen0, osz0 = struct.unpack_from('<II', base, 0) if len(base) >= 8 else (0, 0)
    if plen0 and 8 + plen0 <= len(base) and plen0 != osz0:
        expanded = decode_blob(base)
    elif len(base) == real:
        expanded = base
    else:
        die('基底既非 framed 也非 %d 字节展开态: %d 字节' % (real, len(base)))
    if len(expanded) != real:
        die('基底展开态 %d != 预期 %d (menu/gr 选错? --target)' % (len(expanded), real))
    groups, attrs, _ = parse_expanded_groups(expanded)
    chunks = frame_chunks(base)

    # 原文核对
    src_text = {}
    for gi, st in enumerate(groups):
        for ii, s in enumerate(st):
            src_text['G%02d.I%03d' % (gi + 1, ii)] = bytes(s)
    n = 0
    for key, en, zh in load_trans_csv(a.input):
        gi_i = parse_gi(key)
        if gi_i is None:
            die('RES 模式 key 须为 G组.I条 形式: %r' % key)
        gi, ii = gi_i
        if gi >= len(groups) or ii >= len(groups[gi]):
            die('key 越界: %s (共 %d 组, 该组 %d 条)'
                % (key, len(groups), len(groups[gi]) if gi < len(groups) else -1))
        if en:
            ref = src_text['G%02d.I%03d' % (gi + 1, ii)].decode('latin-1', 'replace')
            if en != ref:
                msg = ('%s 原文不符:\n  CSV: %r\n  库 : %r' % (key, en, ref))
                if a.strict_en:
                    die(msg)
                print('  警告(原文漂移): ' + msg.replace('\n', ' | '))
        groups[gi][ii] = bytearray(enc.encode(zh, key))
        n += 1
    cont = serialize_exact(groups, attrs, real)
    if parse_expanded_groups(cont)[0] != groups:
        die('容器序列化回环失败')
    pos, blob = 0, b''
    for csz in chunks:
        chunk = cont[pos:pos + csz]
        if len(chunk) != csz:
            die('容器 %d != 子流规划总长 %d — 子流布局与基底不一致' % (len(cont), sum(chunks)))
        pl = lzo_compress(chunk, level=7, use_m1=True, use_m4=True)
        back, err, _ = lzo1x_decompress(pl, out_size=csz)
        if err is not None or back != chunk:
            die('子流压缩自检失败')
        blob += struct.pack('<II', len(pl), csz) + pl
        pos += csz
    if decode_blob(blob) != cont:
        die('blob 解码回环失败')
    print('[res] 应用 %d 条 → 容器 %dB (=槽容量), blob %dB / 槽 %dB, 子流布局 %s'
          % (n, len(cont), len(blob), slot, chunks))
    open(a.out, 'wb').write(blob)
    if len(blob) > slot:
        open(a.out + '.expanded', 'wb').write(cont)
        print('  超槽 %d 字节: 另出展开态 %s.expanded (img_patch stored==real 重定位)'
              % (len(blob) - slot, a.out))
        return 2
    print('[res] PASS (%s, 余 %d 字节)' % (a.out, slot - len(blob)))
    return 0


# ---------------------------------------------------------------- TXT

def do_txt(a):
    enc = Encoder(a.charset)
    data = open(a.base_txt, 'rb').read()
    lines = data.replace(b'\r\n', b'\n').split(b'\n')
    out = []
    hit = {}
    for ln in lines:
        s = ln.decode('latin-1')
        m = re.match(r'^(\t"([^"]+)")\t+"(.*)"\s*$', s)
        if m:
            hit[m.group(2)] = len(out)
        out.append(ln)
    n = 0
    for key, en, zh in load_trans_csv(a.input):
        if key not in hit:
            die('TXT 中无键 %r — 宁少勿错' % key)
        i = hit[key]
        s = out[i].decode('latin-1')
        if '"' in zh:
            die('%s: TXT 值不得含双引号 (破坏 \\t"KEY"\\t"VALUE" 格式)' % key)
        tabs = re.match(r'^(\t"[^"]+"\t+)"(.*)"\s*$', s)
        if not tabs:
            die('TXT 行解析失败: %r' % s)
        raw = enc.encode(zh, key)
        out[i] = ('%s"%s"' % (tabs.group(1), raw.decode('latin-1'))).encode('latin-1')
        n += 1
    text = b'\n'.join(out)
    # framed = {plen}{osz}{LZO1X} 配 img_patch --framed
    pl = lzo_compress(text, level=7, use_m1=True, use_m4=True)
    back, err, _ = lzo1x_decompress(pl, out_size=len(text))
    if err is not None or back != text:
        die('TXT 压缩自检失败')
    framed = struct.pack('<II', len(pl), len(text)) + pl
    open(a.out + '.txt', 'wb').write(text)
    open(a.out + '.framed.bin', 'wb').write(framed)
    print('[txt] 应用 %d 键 → 明文 %dB (%s.txt) + framed %dB (%s.framed.bin, 配 img_patch --framed)'
          % (n, len(text), a.out, len(framed), a.out))
    return 0


# ---------------------------------------------------------------- ATR

def do_atr(a):
    enc = Encoder(a.charset)
    rows = load_trans_csv(a.input)
    by_file = {}
    for key, en, zh in rows:
        if ':' not in key:
            die('ATR 模式 key 须为 文件:标签 形式: %r' % key)
        fn, tag = key.split(':', 1)
        by_file.setdefault(fn.upper(), []).append((tag, en, zh, key))
    os.makedirs(a.out_dir, exist_ok=True)
    n = 0
    for fn in sorted(by_file):
        src = os.path.join(a.base_atr_dir, fn)
        if not os.path.exists(src):
            die('无 ATR 文件: %s' % src)
        xml = open(src, 'r', encoding='latin-1').read()
        for tag, en, zh, key in by_file[fn]:
            raw = enc.encode(zh, key)
            if any(b > 0x7E for b in raw):
                print('  警告: %s 含非 ASCII 字节 — ATR 中文实机未验证 (nav25 曾挂指令面板)!'
                      % key)
            pat = re.compile(r'(<%s>)(.*?)(</%s>)' % (re.escape(tag), re.escape(tag)), re.S)
            if not pat.search(xml):
                die('%s 无标签 <%s>' % (key, tag))
            xml = pat.sub(lambda mm: mm.group(1) + raw.decode('latin-1') + mm.group(3), xml)
            n += 1
        open(os.path.join(a.out_dir, fn), 'w', encoding='latin-1').write(xml)
    print('[atr] 重写 %d 标签 / %d 文件 → %s' % (n, len(by_file), a.out_dir))
    return 0


def main():
    ap = argparse.ArgumentParser(description='翻译 CSV → RES/TXT/ATR')
    ap.add_argument('--mode', choices=('res', 'txt', 'atr'), required=True)
    ap.add_argument('--charset', help='font_build 产出的 charset_compiled.json')
    ap.add_argument('--input', required=True, help='翻译 CSV (key,en,zh)')
    ap.add_argument('--base-res', help='MENU 8 子流 blob 或展开态')
    ap.add_argument('--target', choices=('menu', 'gr'), default='menu')
    ap.add_argument('--base-txt', help='EN_STRINGS.TXT 解码态')
    ap.add_argument('--base-atr-dir', help='ATR 目录')
    ap.add_argument('--out', help='输出文件 (res/txt)')
    ap.add_argument('--out-dir', help='输出目录 (atr)')
    ap.add_argument('--strict-en', action='store_true', help='原文漂移改为报错')
    a = ap.parse_args()
    if a.mode == 'res':
        if not (a.charset and a.base_res and a.out):
            die('res 模式需 --charset --base-res --out')
        sys.exit(do_res(a))
    if a.mode == 'txt':
        if not (a.charset and a.base_txt and a.out):
            die('txt 模式需 --charset --base-txt --out')
        sys.exit(do_txt(a))
    if not (a.charset and a.base_atr_dir and a.out_dir):
        die('atr 模式需 --charset --base-atr-dir --out-dir')
    sys.exit(do_atr(a))


if __name__ == '__main__':
    main()
