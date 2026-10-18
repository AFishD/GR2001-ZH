# -*- coding: utf-8 -*-
r"""sent_lib.py —— 候选 R（0xB1/0xB5 图标哨兵）对照盘的共享库。

只读既有 ISO（mmap / open('rb')）；写盘只允许 work\builds\GR_SENT\**。

口径（全部来自既有交付物，保持一致，可比）：
  · 容器/条目/解压/重压/差异：直接 import `work\builds\GR_TXT\tools\txt_build.py`
    （同一份 load_cont / lang_walk / rebuild_lang / repack / diff_runs），保证与
    `docs\REPORT_TEXT_OVERFLOW.md` 的读数同口径。
  · 「对偶码」形态判定 = `txt_capacity.py` 的规则：
        lead ∈ [0xA1,0xBA) 且 trail ∈ [0xA1,0xFE] ⇒ 2 字节对偶码
        （否则按单字节走）
    只有在“trail 是 0xB1/0xB5”时才登记为哨兵 trail；不在对偶码里的 0xB1/0xB5 登记为裸单字节。
"""
import hashlib
import importlib.util
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
OUTDIR = os.path.join(ROOT, 'work', 'builds', 'GR_SENT')
AUD = os.path.join(OUTDIR, 'audit')
sys.path.insert(0, os.path.join(ROOT, 'tools', 'text_csv'))
import tcslib as T                                                       # noqa: E402

# txt_build.py 里的同一套容器 I/O（同口径）
_s = importlib.util.spec_from_file_location(
    'txt_build', os.path.join(ROOT, 'work', 'builds', 'GR_TXT', 'tools', 'txt_build.py'))
TB = importlib.util.module_from_spec(_s)
_s.loader.exec_module(TB)

EN_ISO = os.path.join(ROOT, r"third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso")
BASE_CVAR = os.path.join(ROOT, r"work\builds\GR_CVAR\CVAR_04_text.iso")
ORIG_ELF = os.path.join(ROOT, r"third_party\orig\ps2\slus_out\SLUS_206.13")

# (lba, img 条目号, 类型, 名字) —— 与 txt_build.CONTS 逐字相同
CONTS = (('MENU', T.MENU_LBA, 25, 'LANG', 'EN_STRINGS.RES@MENU'),
         ('GR', T.GR_LBA, 902, 'LANG', 'EN_STRINGS.RES@GR'),
         ('MENU', T.MENU_LBA, 283, 'SFXML', 'EN_SPECIAL_FEATURE.XML'))

SENTINELS = (0xB1, 0xB5)
LEAD_LO, LEAD_HI = 0xA1, 0xBA            # 与 txt_capacity.py 的形态判定一致
TRAIL_LO, TRAIL_HI = 0xA1, 0xFE
PRESENT_LEAD_HI = 0xBA

# ── 原盘 ELF：图标特判的四个立即数站点（VA 与 ISO 偏移）────────────────────
#   VA 0x219C08  addiu v1,zero,-75 (0xFFB5)   0x219C14  addiu v1,zero,-79 (0xFFB1)
#   VA 0x219D24  addiu v0,zero,-75 (0xFFB5)   0x219D38  addiu v0,zero,-79 (0xFFB1)
ICON_SITES = (0x219C08, 0x219C14, 0x219D24, 0x219D38)
ISO_OF_VA = 0x6C780                      # ISO = VA − 0x6C780（REPORT_TEXT_OVERFLOW §3.1）
PAIR_STRIDE = T.PAIR_STRIDE              # 94


def iso_off_of_va(va):
    return va - ISO_OF_VA


def log(msg):
    print(msg)
    sys.stdout.flush()


# ───────────────────── 形态扫描（同 txt_capacity.py 口径）─────────────────────
def scan_payload(p):
    """返回 (trail_hits, bare_hits, pairs_present)

    trail_hits = [(off, lead, trail)]  off = 该 trail 字节在 p 内的偏移
    bare_hits  = [off, ...]
    pairs_present = {(lead,trail), ...}
    """
    trail, bare, pairs = [], [], set()
    i, n = 0, len(p)
    while i < n:
        b = p[i]
        if LEAD_LO <= b < PRESENT_LEAD_HI and i + 1 < n and TRAIL_LO <= p[i + 1] <= TRAIL_HI:
            pairs.add((b, p[i + 1]))
            if p[i + 1] in SENTINELS:
                trail.append((i + 1, b, p[i + 1]))
            i += 2
        else:
            if b in SENTINELS:
                bare.append(i)
            i += 1
    return trail, bare, pairs


def xml_text_spans(blob):
    """<text>…</text> 的 (start,end) 内容区间（不含标签本身）。"""
    import re
    return [(m.start(1), m.end(1)) for m in
            re.finditer(rb'<text>(.*?)</text>', blob, re.S)]


# ───────────────────── 容器读取 ─────────────────────
def load_all(iso_path=BASE_CVAR):
    """读基底盘的 3 个容器。返回 {tag: cont}（cont 额外带 tag/lba/idx/kind）。"""
    iso = T.Iso(iso_path)
    out = {}
    for (img, lba, idx, kind, tag) in CONTS:
        c = TB.load_cont(iso, lba, idx)
        c.update(tag=tag, lba=lba, idx=idx, kind=kind, img=img)
        out[tag] = c
    iso.close()
    return out


def entries_of(c):
    """LANG ⇒ [(g,i,length,data)]；XML ⇒ [(None,k,length,data)]（payload 区间）。"""
    if c['kind'] == 'LANG':
        ents, _used = T.parse_lang(c['blob'])
        return [(e.g, e.i, e.length, bytes(e.data)) for e in ents]
    sp = xml_text_spans(c['blob'])
    return [(None, k, e - s, c['blob'][s:e]) for k, (s, e) in enumerate(sp)]


# ───────────────────── 替代码选择 ─────────────────────
def build_alias_plan(used_pairs_by_tag):
    """为 charset 里每一个「trail ∈ 哨兵」的对偶码 (L,T) 选一个替代码 (L,T')。

    约束（全部断言）：
      ① T' ∈ [0xA1,0xFE]，T' ∉ {0xB1,0xB5}
      ② (L,T') 在**三个容器的原始载荷里都不出现**（不撞已有对偶码）
      ③ (L,T') ≠ (L,T)（显然，因为 T'≠T）
    选择规则（确定性、最小扰动）：先按 |T'−T| 升序，再按 T' 升序取第一个可行值。
    """
    used = set()
    for s in used_pairs_by_tag.values():
        used |= s
    cands = [t for t in range(TRAIL_LO, TRAIL_HI + 1) if t not in SENTINELS]
    alias = {}
    for lead in range(LEAD_LO, PRESENT_LEAD_HI):
        for t in SENTINELS:
            best = sorted(cands, key=lambda x: (abs(x - t), x))
            pick = None
            for x in best:
                if (lead, x) not in used:
                    pick = x
                    break
            assert pick is not None, 'lead 0x%02X 无可用 trail' % lead
            alias[(lead, t)] = (lead, pick)
    return alias


# ───────────────────── 应用替换 ─────────────────────
def apply_lang(blob, alias):
    """对 LANG blob 的每条载荷按同一规则替换；返回 (新 blob, 逐处清单, 统计)。

    ★ 替换的是**整个对偶码**：lead 与 trail 两个字节都写成替代表里的新对偶码
      （只改 trail 在数学上不可行 —— leads 0xA1..0xB0 的 94 个 trail 全被占用，
        没有同 lead 的空闲码；详见 audit\\A_sentinel_scan.json）。
    """
    hits = []

    def fn(g, i, data):
        trail, _bare, _pairs = scan_payload(data)
        if not trail:
            return data
        b = bytearray(data)
        for (off, lead, t) in trail:
            l2, t2 = alias[(lead, t)]
            assert b[off] == t and b[off - 1] == lead
            b[off - 1] = l2
            b[off] = t2
            hits.append(dict(g=g, i=i, off=off, off_lead=off - 1, lead=lead, trail=t,
                             new_lead=l2, new_trail=t2))
        return bytes(b)

    nb, n_edit, used = TB.rebuild_lang(blob, fn)
    assert len(nb) == len(blob)
    return nb, hits, dict(n_edit_entries=n_edit, rebuilt_used_end=used)


def apply_xml(blob, alias):
    """对 XML blob 里**所有** <text>…</text> 内容区间内的哨兵 trail 做同一替换。

    同样**整对**替换（lead + trail 两个字节）。
    """
    hits = []
    b = bytearray(blob)
    for (s, e) in xml_text_spans(blob):
        seg = blob[s:e]
        trail, _bare, _pairs = scan_payload(seg)
        for (off, lead, t) in trail:
            l2, t2 = alias[(lead, t)]
            assert b[s + off] == t and b[s + off - 1] == lead
            b[s + off - 1] = l2
            b[s + off] = t2
            hits.append(dict(node_start=s, off=s + off, rel=off, lead=lead, trail=t,
                             new_lead=l2, new_trail=t2))
    return bytes(b), hits, dict(n_edit_nodes=len(set(h['node_start'] for h in hits)))


# ───────────────────── 解码等价（替代表口径）─────────────────────
def decode_with_alias(data, cs, alias):
    """在**替代表扩展过的** charset 口径下解码。返回 (text, 与 cs.decode 相同的 mp)。

    规则与 tcslib.Charset.decode 逐字相同，唯一区别：**替代表优先**
      （新对偶码在 charset 里本来是别的字，必须由替代表覆盖），后再查 charset。
    """
    rev = {}
    for (l, t), (l2, t2) in alias.items():
        ch = cs.pair_of.get((l, t))
        if ch is not None:
            rev[(l2, t2)] = ch
    out, mp, i, n = [], [], 0, len(data)
    while i < n:
        v = data[i]
        if v < 0x80:
            out.append(chr(v)); mp.append(i); i += 1
        elif (T.LEAD_LO <= v < T.LEAD_HI and i + 1 < n and
              (v, data[i + 1]) in rev):                       # ★ 替代表优先
            out.append(rev[(v, data[i + 1])]); mp.append(i); i += 2
        elif (T.LEAD_LO <= v < T.LEAD_HI and i + 1 < n and
              (v, data[i + 1]) in cs.pair_of):
            out.append(cs.pair_of[(v, data[i + 1])]); mp.append(i); i += 2
        elif v in cs.codes:
            out.append(cs.codes[v]); mp.append(i); i += 1
        else:
            out.append(chr(cs.PUA_BASE + v)); mp.append(i); i += 1
    return ''.join(out), mp


def diff_byte_runs(path_a, path_b):
    return TB.diff_runs(path_a, path_b)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
