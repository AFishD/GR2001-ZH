# -*- coding: utf-8 -*-
r"""rb_textaudit.py -- 载荷级文本验收（gate 0xBA 语义），逐条给数字与证据。

判据:
  [1] 3 个中文容器（EN_STRINGS.RES@MENU / EN_STRINGS.RES@GR / EN_SPECIAL_FEATURE.XML）
      的**载荷字节流**里，`0xB1..0xB9` 出现在**单字节位**的数量 = 0
      （口径同 LEAD_CAPACITY_2400.md §14：lead ∈ [0xA1, gate) 为前导，其余为单字节位）
  [2] MENU 侧与 GR 侧两份语言表**逐条 payload 逐字节相同**（工程惯例=两份同步, 见
      docs/REPORT_csv_text_tool.md:98 / docs/REPORT_zh90_order_label.md:164）
  [3] 用 charset 解码后的**字符序列**逐条相同（不符 0）
  [4] 单字节位上的 `0xB1` / `0xB5`（引擎图标占位）计数（迁移前 14 / 42 的登记口径）

用法: python rb_textaudit.py [--iso <盘>] [--charset <json>] [--out <txt>]
"""
import argparse
import hashlib
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402

GATE = 0xBA
LEAD_LO = 0xA1
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def load_iso_containers(iso):
    """→ [(tag, blob, kind)]  kind ∈ {'LANG','SFXML'}"""
    out = []
    for (tag, lba, name, kind) in (
            ('EN_STRINGS.RES@MENU', zx_lib.MENU_LBA, 'EN_STRINGS.RES', 'LANG'),
            ('EN_STRINGS.RES@GR', zx_lib.GR_LBA, 'EN_STRINGS.RES', 'LANG'),
            ('EN_SPECIAL_FEATURE.XML', zx_lib.MENU_LBA, 'EN_SPECIAL_FEATURE.XML', 'SFXML')):
        e = [x for x in zx_lib.entries(iso, lba) if x['name'] == name][0]
        slot = bytes(iso.read(e['iso_off'], e['stored']))
        blob = b''.join(s[0] for s in T.lzo_subs(slot))
        out.append((tag, blob, kind))
    return out


def payloads(blob, kind):
    """→ [(off, len, bytes)]（载荷区间；SFXML 取 <text> 正文 + name= 属性, 口径同 §14）"""
    if kind == 'LANG':
        ents, used = T.parse_lang(blob)
        return [(e.data_off, e.length, e.data) for e in ents], used
    out = []
    for (k, off, ln, body) in T.parse_sfxml(blob):
        out.append((off, ln, body))
    # name= 属性
    import re
    for m in re.finditer(rb'name="([^"]*)"', blob):
        out.append((m.start(1), m.end(1) - m.start(1), bytes(m.group(1))))
    return out, T.xml_tail_start(blob)


def scan_singles(data, gate=GATE, lo=LEAD_LO):
    """按闸门口径走字节流，返回 (单字节位计数 dict, 总单字节位)"""
    cnt = {}
    i, n = 0, len(data)
    while i < n:
        c = data[i]
        if lo <= c < gate:
            i += 2
            continue
        cnt[c] = cnt.get(c, 0) + 1
        i += 1
    return cnt


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_REBUILD',
                                                  'GR_REBUILD2400.iso'))
    ap.add_argument('--charset', default=None)
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)
    if a.charset:
        T.CHARSET = os.path.abspath(a.charset)
        T.Charset.__init__.__defaults__ = (T.CHARSET,)   # 默认参数是 def 期绑定的
    P('rb_textaudit.py  iso = %s' % os.path.abspath(a.iso))
    P('  gate = 0x%02X ; lead 区间 = [0x%02X, 0x%02X) ; charset = %s' %
      (GATE, LEAD_LO, GATE, T.CHARSET))

    iso = T.Iso(a.iso)
    conts = load_iso_containers(iso)
    iso.close()

    P('')
    P('=' * 96)
    P('[1] 载荷级旧码扫描（单字节位上的 0xB1..0xB9 必须为 0）')
    tot_legacy = 0
    per = {}
    for (tag, blob, kind) in conts:
        pays, used = payloads(blob, kind)
        nbytes = sum(l for (_o, l, _b) in pays)
        legacy, icon = {}, {}
        for (_o, _l, b) in pays:
            c = scan_singles(b)
            for k, v in c.items():
                if 0xB1 <= k <= 0xB9:
                    legacy[k] = legacy.get(k, 0) + v
            for k in (0xB1, 0xB5):
                if k in c:
                    icon[k] = icon.get(k, 0) + c[k]
        n_legacy = sum(legacy.values())
        tot_legacy += n_legacy
        per[tag] = dict(payloads=len(pays), payload_bytes=nbytes, used_end=used,
                        legacy=n_legacy, legacy_per_code=legacy, icon=icon)
        P('  %-26s 载荷 %5d 区间 / %8d B ; used_end=0x%X' % (tag, len(pays), nbytes, used))
        P('        ★ 单字节位 0xB1..0xB9 = **%d** %s' %
          (n_legacy, legacy if legacy else '✓'))
        P('        其中 0xB1/0xB5（引擎图标占位）: %s' % (icon if icon else '无'))
    P('  ----------------------------------------------------------------')
    P('  ★ 三个中文容器合计 单字节位旧码 = **%d**（判据 = 0）%s' %
      (tot_legacy, '✓ 通过' if tot_legacy == 0 else '✗ 未通过'))

    P('')
    P('=' * 96)
    P('[2][3] 两份语言表逐条 payload 逐字节 / 逐字符 一致')
    m = [c for c in conts if c[0] == 'EN_STRINGS.RES@MENU'][0][1]
    g = [c for c in conts if c[0] == 'EN_STRINGS.RES@GR'][0][1]
    pm, um = payloads(m, 'LANG')
    pg, ug = payloads(g, 'LANG')
    P('  MENU 条目 %d / GR 条目 %d ; used_end 0x%X / 0x%X' %
      (len(pm), len(pg), um, ug))
    assert len(pm) == len(pg)
    nb = sum(1 for x, y in zip(pm, pg) if x[2] != y[2])
    P('  ★ 逐条 payload 逐字节相同: %d/%d ; 不同 **%d** %s' %
      (len(pm) - nb, len(pm), nb, '✓' if nb == 0 else '✗'))
    # 逐字符（用 charset）
    cs = T.Charset()
    pair_dec = {tuple(k): v for k, v in cs.pair_of.items()}   # cs.pair_of 本身即 (b1,b2)→字
    enc = dict(cs.codes)

    def decode(data):
        out, i, n = [], 0, len(data)
        while i < n:
            c = data[i]
            if LEAD_LO <= c < GATE and i + 1 < n:
                out.append(pair_dec.get((c, data[i + 1]), '\uFFFD'))
                i += 2
            else:
                out.append(enc.get(c, chr(c) if c < 0x80 else '\uFFFD'))
                i += 1
        return ''.join(out)

    nch = 0
    for x, y in zip(pm, pg):
        if decode(x[2]) != decode(y[2]):
            nch += 1
    P('  ★ 逐条**字符序列**相同: %d/%d ; 不同 **%d** %s' %
      (len(pm) - nch, len(pm), nch, '✓' if nch == 0 else '✗'))
    # 参考口径：与 MENU 侧权威文本（本盘组）一致
    blob_sha = hashlib.sha256(m).hexdigest()
    blob_sha_g = hashlib.sha256(g).hexdigest()
    P('  MENU blob sha256 = %s' % blob_sha)
    P('  GR   blob sha256 = %s' % blob_sha_g)

    P('')
    P('=' * 96)
    P('[4] SF XML')
    sf = [c for c in conts if 'SPECIAL_FEATURE' in c[0]][0][1]
    sp, su = payloads(sf, 'SFXML')
    P('  载荷区间 %d ; 正文/属性字节 %d ; 结束标记后尾部 %d B' %
      (len(sp), sum(l for (_o, l, _b) in sp), len(sf) - su))
    u = sum(1 for (_o, _l, b) in sp if '\uFFFD' in decode(b))
    P('  ★ 载荷可用 charset 解出、含 \\uFFFD 的区间 = %d（源盘既有缺陷, 见 §12.7 #6）' % u)

    out = a.out or os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', 'temp',
                                'textaudit.txt')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(LOG) + '\n')
    P('')
    P('[out] %s' % out)
    return 0 if tot_legacy == 0 and nb == 0 and nch == 0 else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
