# -*- coding: utf-8 -*-
r"""hashr_build.py — ★ 哨兵 trail 重排 (数据侧修复)

交付 A:  GR_HASHR2400.iso   ← 基线 work/builds/GR_FA2400_K2/GR_FA2400_K2.iso
交付 B:  GR_HASHR_base.iso  ← 基线 work/builds/GR_ZH113b/GR_ZH113b.iso  (另见 --mode base 的容量证明)

根因 (Lead 定案): 汉化把汉字对偶码的 **trail** 做成了 0xB1/0xB5, 而引擎的 DrawString/CharWidth
对 0xB1/0xB5 有硬编码图标特判 (原盘 0x219C08..0x219D38 / 0x21AD38,0x21AD4C) ⇒ 命中后走
AddOneWord(...,flag=1) 的**容量 2 副包** ⇒ 逐字符写坏内存。

本工具做的事 (三处, 互为闭环):
  ① charset: 把 trail ∈ {B1,B5} 的对偶码**全部注销** (含占位字), 把受影响的**真字**搬到
     trail ∉ {B1,B5} 的空槽 (从「保留段」自低位起压缩让出), 逐个登记 old→new;
  ② 图集: 把被搬字的字形**逐 texel 搬到新槽**, 旧槽清零 (确定性空模板 0x11);
  ③ 文本: 3 个中文容器的载荷里这些对偶码**就地 2 字节换 2 字节** (长度/结构/条目表全不动),
     并在全盘其它位置按「上下文法」找同码并同样改写。

硬断言 (任一失败即中止, 不写盘) —— 见代码里的 [A1..A9]。

用法:
    python work/builds/GR_HASHR/tools/hashr_build.py --mode k2 --dry-run
    python work/builds/GR_HASHR/tools/hashr_build.py --mode k2
    python work/builds/GR_HASHR/tools/hashr_build.py --mode base          # 打印容量证明
"""
import argparse
import collections
import hashlib
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                       # noqa: E402
import tcslib as T                                                       # noqa: E402
import zx_lib                                                            # noqa: E402
import migrate_legacy as ML                                              # noqa: E402

OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', 'temp', 'hashr_probe')
K2_ISO = os.path.join(REPO, 'work', 'builds', 'GR_FA2400_K2', 'GR_FA2400_K2.iso')
BASE_ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
CS_REPO = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
CS_BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82',
                       'charset_before_r82.json')
GATE_PAIRS = os.path.join(REPO, 'tools', 'text_csv', 'gate_pairs.json')
MENU_BASE = zx_lib.MENU_LBA * 2048
W = 1024
EMPTY_NIB = 1
SENT = (0xB1, 0xB5)
CORE = ('EN_STRINGS.RES@MENU', 'EN_STRINGS.RES@GR', 'EN_SPECIAL_FEATURE.XML')
GEOM = {
    'k2':   dict(h=644, ncol=64, skip=2, y0=3),
    'base': dict(h=512, ncol=62, skip=3, y0=2),
}
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def yrow(row, skip, y0):
    return y0 + 16 * (row + (skip if row >= 12 else 0))


def cell(slot, ncol, skip, y0):
    return 16 * (slot % ncol), yrow(slot // ncol, skip, y0)


def slot_of_pair(b1, b2):
    return (b1 - 0xA1) * 94 + (b2 - 0xA1)


def pair_from_slot(slot):
    return 0xA1 + slot // 94, 0xA1 + slot % 94


# ───────────────────────── 图集 (nibble 平面) ─────────────────────────
def container_to_plane(cont, w, h):
    stride = w // 2
    segs = [s for s in T.atlas_container_segments(bytes(cont), stride) if s[2] > 0]
    plane = bytearray(b'\x11' * (stride * h))
    for (row0, doff, nb) in segs:
        nfull, rest = nb // stride, nb % stride
        for i in range(nfull):
            if row0 + i < h:
                plane[(row0 + i) * stride:(row0 + i + 1) * stride] = \
                    cont[doff + i * stride:doff + (i + 1) * stride]
        if rest and row0 + nfull < h:
            d = (row0 + nfull) * stride
            plane[d:d + rest] = cont[doff + nfull * stride:doff + nfull * stride + rest]
    return bytes(plane)


def plane_to_container(stage_cont, plane, w):
    stride = w // 2
    out = bytearray(stage_cont)
    segs = [s for s in T.atlas_container_segments(bytes(stage_cont), stride) if s[2] > 0]
    covered = 0
    for (row0, doff, nb) in segs:
        nfull, rest = nb // stride, nb % stride
        for i in range(nfull):
            out[doff + i * stride:doff + (i + 1) * stride] = \
                plane[(row0 + i) * stride:(row0 + i + 1) * stride]
        if rest:
            d = (row0 + nfull) * stride
            out[doff + nfull * stride:doff + nfull * stride + rest] = plane[d:d + rest]
        covered += nb
    return bytes(out), segs, covered


def cell_read(plane, x, y, w=W):
    stride = w // 2
    g = np.zeros((16, 16), dtype=bool)
    for i in range(16):
        r = plane[(y + i) * stride + x // 2:(y + i) * stride + x // 2 + 8]
        g[i, 0::2] = [(b & 0x0F) == 0 for b in r]
        g[i, 1::2] = [(b >> 4) == 0 for b in r]
    return g


def cell_write(plane, x, y, g, w=W):
    stride = w // 2
    for i in range(16):
        row = bytearray(8)
        for k in range(8):
            lo = EMPTY_NIB if not g[i, 2 * k] else 0
            hi = EMPTY_NIB if not g[i, 2 * k + 1] else 0
            row[k] = (hi << 4) | lo
        plane[(y + i) * stride + x // 2:(y + i) * stride + x // 2 + 8] = row


def read_font(iso_path):
    iso = T.Iso(iso_path)
    ents = zx_lib.entries(iso, zx_lib.MENU_LBA)
    e_pak = [e for e in ents if e['name'] == 'COMMON.PAK'][0]
    e_ft = [e for e in ents if e['name'] == 'FONT.RES'][0]
    pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
    recs = T.parse_pak_records(pak)
    nm, psm, w, h, clut, px_size, PX = recs[1]
    ct = pak[PX:PX + px_size]
    ft_slot = bytes(iso.read(e_ft['iso_off'], e_ft['stored']))
    ft_blob = b''.join(s[0] for s in T.lzo_subs(ft_slot))
    faces, ft_end = zx_lib.ft_records(ft_blob, 28)
    return dict(iso=iso, path=iso_path, e_pak=e_pak, e_ft=e_ft, pak=pak, recs=recs,
                name=nm, psm=psm, w=w, h=h, clut=clut, px_size=px_size, PX=PX, ct=ct,
                plane=container_to_plane(ct, w, h), faces=faces,
                ft_slot=ft_slot, ft_blob=ft_blob, ft_end=ft_end)


def nonempty_rects(faces):
    out = []
    for (fn, fld, rows) in faces:
        for k, (_o, r) in enumerate(rows):
            if r[4] > r[2] and r[5] > r[3]:
                out.append((fn, k, int(r[2]), int(r[3]), int(r[4]), int(r[5])))
    return out


def rect_hits_cell(rect, cx, cy):
    (_fn, _k, u0, v0, u1, v1) = rect
    return not (u1 <= cx or u0 >= cx + 16 or v1 <= cy or v0 >= cy + 16)


# ───────────────────────── 容器读写 ─────────────────────────
def load_containers(iso, tags=None):
    out = []
    for (kind, img, lba, idx, tag, why) in ML.CONTAINER_SPECS:
        if tags and tag not in tags:
            continue
        e = iso.img_entry(lba, idx)
        raw = iso.read(e['iso_off'], e['stored'])
        subs = T.lzo_subs(raw)
        c = dict(name=kind, tag=tag, img=img, lba=lba, idx=idx, entry=e, why=why,
                 raw=bytes(raw), subs=subs, blob=b''.join(s[0] for s in subs),
                 sizes=[s[2] for s in subs],
                 raws=[bytes(raw[s[3]:s[3] + 8 + s[1]]) for s in subs],
                 slot=e['stored'], frame_len=sum(8 + s[1] for s in subs),
                 iso_off=e['iso_off'])
        ranges, used, info = ML.payload_ranges(c)
        c['ranges'] = ranges
        c['used_end'] = used
        c['info'] = info
        out.append(c)
    return out


def repack(cont, new_blob):
    assert len(new_blob) == len(cont['blob']), '解压总长必须不变'
    frame, q, n_rep = bytearray(), 0, 0
    for k, S in enumerate(cont['sizes']):
        part = new_blob[q:q + S]
        q += S
        if part == cont['subs'][k][0]:
            frame += cont['raws'][k]
            continue
        cc = T.lzo_compress(part, level=7, use_m1=True, use_m4=True)
        back, err, _ = T.lzo1x_decompress(cc, out_size=S)
        assert err is None and back == part, '%s 子流 %d 回环失败' % (cont['tag'], k)
        frame += struct.pack('<II', len(cc), S) + cc
        n_rep += 1
    assert q == len(new_blob)
    return bytes(frame), n_rep


def remap_payload(data, gate, pair_dec, remap, stat):
    """按字节流走: 只改**合法对偶码**起点上的 2 字节; 其余逐字节不变 (长度恒定)。"""
    out, i, n = bytearray(), 0, len(data)
    while i < n:
        b = data[i]
        if T.LEAD_LO <= b < gate:
            t = data[i + 1] if i + 1 < n else None
            if t is not None and (b, t) in pair_dec:
                p = (b, t)
                if p in remap:
                    out += bytes(remap[p])
                    stat['n'] += 1
                    stat['per'][p] = stat['per'].get(p, 0) + 1
                    stat.setdefault('chars', collections.Counter())[pair_dec[p]] += 1
                else:
                    out += data[i:i + 2]
                i += 2
                continue
        out.append(b)
        i += 1
    return bytes(out)


def rebuild_container(cont, gate, pair_dec, remap, stat):
    blob = bytearray(cont['blob'])
    for (s, e) in cont['ranges']:
        new = remap_payload(bytes(blob[s:e]), gate, pair_dec, remap, stat)
        assert len(new) == e - s, '就地改写必须等长'
        if new != bytes(blob[s:e]):
            blob[s:e] = new
            stat['changed'] += 1
    return bytes(blob)


# ───────────────────────── 全盘「同码」粗查 (上下文法) ─────────────────────────
def find_text_contexts(data, patterns, win=8):
    """在任意字节块里找 patterns (2 字节) 的**像文本**的出现。

    判据: 命中点前后 win 字节里, 用「lead∈[0xA1,gate) 且下一字节∈[0xA1,0xFF)」规则
    能解出 ≥2 个合法对偶码 ⇒ 认为它处在文本对偶流里 (排除随手撞上的随机 2 字节)。
    返回 [(off, pair)]。
    """
    hits = []
    pats = [bytes(p) for p in patterns]
    for pat in pats:
        start = 0
        while True:
            k = data.find(pat, start)
            if k < 0:
                break
            start = k + 1
            lo, hi = max(0, k - win), min(len(data), k + 2 + win)
            seg = data[lo:hi]
            npair = 0
            j = 0
            m = len(seg)
            while j < m - 1:
                b = seg[j]
                if 0xA1 <= b < 0xBA and 0xA1 <= seg[j + 1] <= 0xFE:
                    npair += 1
                    j += 2
                else:
                    j += 1
            if npair >= 2:
                hits.append((k, pat))
    return hits


# ───────────────────────── 计划 ─────────────────────────
def make_plan(L, mode, cs_json, gate):
    ncol, skip, y0 = GEOM[mode]['ncol'], GEOM[mode]['skip'], GEOM[mode]['y0']
    h = GEOM[mode]['h']
    pair_of = {ch: tuple(v) for ch, v in cs_json['pair_of'].items()}
    codes = {ch: int(b) for ch, b in cs_json['codes'].items()}
    pair_dec = {tuple(v): ch for ch, v in pair_of.items()}
    cap = (gate - 0xA1) * 94
    sent_slots = sorted((Lg - 0xA1) * 94 + (t - 0xA1)
                        for Lg in range(0xA1, gate) for t in SENT)
    sent_set = set(sent_slots)
    P('[plan] gate 0x%02X ⇒ 对偶空间 %d 槽 ; 哨兵槽 (trail∈{B1,B5}) %d 个'
      % (gate, cap, len(sent_slots)))
    # ① 哨兵槽上的登记
    at_sent = {}
    for s in sent_slots:
        pr = pair_from_slot(s)
        if pr in pair_dec:
            at_sent[s] = (pr, pair_dec[pr])
    P('[plan] 哨兵槽上有登记的: %d / %d' % (len(at_sent), len(sent_slots)))
    moves = [(s, pr, ch) for s, (pr, ch) in sorted(at_sent.items())
             if not (0xE000 <= ord(ch) <= 0xF8FF)]
    dead = [(s, pr, ch) for s, (pr, ch) in sorted(at_sent.items())
            if 0xE000 <= ord(ch) <= 0xF8FF]
    P('[plan]   其中真字 %d 个 (需要搬家) ; 私有区占位字 %d 个 (直接注销)' % (len(moves), len(dead)))
    # ② 可让位的目标槽 = 私有区占位字所在的槽 (保留段), trail 非哨兵
    rects = nonempty_rects(L['faces'])
    targets, skipped = [], []
    for cand in range(cap):
        if len(targets) >= len(moves):
            break
        if cand in sent_set:
            continue
        pr = pair_from_slot(cand)
        ch = pair_dec.get(pr)
        if ch is None or not (0xE000 <= ord(ch) <= 0xF8FF):
            continue
        cx, cy = cell(cand, ncol, skip, y0)
        if cx + 16 > W or cy + 16 > h:
            skipped.append((cand, 'cell 越界'))
            continue
        hit = [r for r in rects if rect_hits_cell(r, cx, cy)]
        if hit:
            skipped.append((cand, '被 %d 条非空 FT 记录矩形压着: %s'
                            % (len(hit), [(x[0], x[1], x[2:]) for x in hit[:3]])))
            continue
        if cell_read(L['plane'], cx, cy).any():
            skipped.append((cand, '目标格已有墨'))
            continue
        targets.append((cand, ch))
    P('[plan] 目标槽 (从保留段低位起, 跳过被 FT 矩形压着的格): %d 个' % len(targets))
    for (cand, why) in skipped:
        P('[plan]   ★ 跳过槽 %d: %s' % (cand, why))
    if len(targets) < len(moves):
        P('')
        P('[plan] ✗✗ **容量不足**: 需要 %d 个「trail 非哨兵」的空槽, 只有 %d 个。'
          % (len(moves), len(targets)))
        P('       对偶空间 %d 槽 ; 已登记 %d ; 哨兵槽 %d ; 可让位占位槽 %d'
          % (cap, len(pair_of), len(sent_slots), len(targets)))
        P('       ★ 鸽笼证明: 汉字数 %d > 安全槽数 %d ⇒ 在**不抬闸门、不丢字**的前提下无解。'
          % (len(moves) + (len(pair_of) - len(at_sent)), cap - len(sent_slots)))
        return None
    assign = []
    for (m, t) in zip(moves, targets):
        assign.append(dict(char=m[2], old_pair=list(m[1]), old_slot=m[0],
                           new_pair=list(pair_from_slot(t[0])), new_slot=t[0],
                           evicted_placeholder=t[1]))
    return dict(gate=gate, cap=cap, sent_slots=sent_slots, moves=assign,
                dead=[dict(char=d[2], pair=list(d[1]), slot=d[0]) for d in dead],
                targets=[t[0] for t in targets], skipped=skipped,
                pair_of=pair_of, codes=codes, pair_dec=pair_dec)


def patch_charset(cs_json, plan):
    out = json.loads(json.dumps(cs_json, ensure_ascii=False))
    po = out['pair_of']
    # ① 注销**全部** trail ∈ {B1,B5} 的登记 (真字 + 私有区占位字)
    rem = sorted(ch for ch, p in po.items() if p[1] in SENT)
    assert len(rem) == len(plan['moves']) + len(plan['dead']), (len(rem), len(plan['moves']))
    for ch in rem:
        del po[ch]
    P('[cs  ] ① 注销哨兵 trail 登记 %d 条 (真字 %d + 占位 %d)'
      % (len(rem), len(plan['moves']), len(plan['dead'])))
    # ② 目标槽上的占位字让位
    for a in plan['moves']:
        ev = [ch for ch, p in po.items() if tuple(p) == tuple(a['new_pair'])]
        assert len(ev) == 1, ('目标槽登记不唯一', a, ev)
        assert 0xE000 <= ord(ev[0]) <= 0xF8FF, ('目标不是占位字', ev[0], a)
        del po[ev[0]]
    P('[cs  ] ② 目标槽上的占位字让位 %d 条' % len(plan['moves']))
    # ③ 真字登记新码
    for a in plan['moves']:
        assert a['char'] not in po, ('字仍在表里', a['char'])
        po[a['char']] = list(a['new_pair'])
    P('[cs  ] ③ 真字登记新码 %d 条' % len(plan['moves']))
    out['_trail_fix_hashr'] = dict(
        note='★ GR_HASHR: 对偶码 **trail 不得落在 0xB1/0xB5** —— 引擎 DrawString/CharWidth 对 '
             '0xB1/0xB5 有硬编码图标特判 (命中走 AddOneWord flag=1 的容量 2 副包) ⇒ 逐字符写坏内存。',
        tool='work/builds/GR_HASHR/tools/hashr_build.py',
        gate=plan['gate'], slot_space=plan['cap'],
        n_pair_before=len(plan['pair_of']), n_pair_after=len(out['pair_of']),
        n_moved=len(plan['moves']), n_retired=len(plan['dead']),
        sentinel_slots=plan['sent_slots'],
        table={a['char']: dict(old='%02X%02X' % tuple(a['old_pair']),
                               new='%02X%02X' % tuple(a['new_pair']),
                               old_slot=a['old_slot'], new_slot=a['new_slot'])
               for a in plan['moves']},
        retired={d['char']: dict(pair='%02X%02X' % tuple(d['pair']), slot=d['slot'])
                 for d in plan['dead']},
        evidence='docs/REPORT_SENTINEL_FIX.md')
    return out


# ───────────────────────── 主流程 ─────────────────────────
def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=('k2', 'base'), default='k2')
    ap.add_argument('--base', default=None)
    ap.add_argument('--out', default=None)
    ap.add_argument('--charset-in', default=None)
    ap.add_argument('--charset-out', default=None,
                    help='写回仓库 charset 的路径 (默认 tools/font_pipeline/data/...)')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--skip-diff', action='store_true')
    a = ap.parse_args(argv)
    mode = a.mode
    base = a.base or (K2_ISO if mode == 'k2' else BASE_ISO)
    out = a.out or os.path.join(OUTDIR, 'GR_HASHR2400.iso' if mode == 'k2'
                                else 'GR_HASHR_base.iso')
    cs_in = a.charset_in or (CS_REPO if mode == 'k2' else CS_BASE)
    tag = 'GR_HASHR2400' if mode == 'k2' else 'GR_HASHR_base'
    os.makedirs(os.path.join(OUTDIR, 'temp'), exist_ok=True)
    P('=' * 100)
    P('hashr_build.py  哨兵 trail 重排   mode=%s' % mode)
    P('  base       = %s' % base)
    P('  out        = %s' % out)
    P('  charset in = %s' % cs_in)
    P('=' * 100)

    L = read_font(base)
    w, h, px_size = L['w'], L['h'], L['px_size']
    P('[gate1] w=%d ; h=%d ; psm=0x%X ; name=%s' % (w, h, L['psm'], L['name']))
    assert (w, h) == (W, GEOM[mode]['h']), (w, h)
    assert px_size == w * h // 2 + 16, (px_size, w * h // 2 + 16)
    P('[gate2] px_size = %d == w*h/2+16 ✓' % px_size)
    assert (w * h // 2) % 2048 == 0
    P('[gate3] (w*h/2) %% 2048 = %d ✓' % ((w * h // 2) % 2048))
    ncol, skip, y0 = GEOM[mode]['ncol'], GEOM[mode]['skip'], GEOM[mode]['y0']
    nrow = 0
    while yrow(nrow, skip, y0) + 16 <= h:
        nrow += 1
    P('[gate4] 网格 %d 列 × %d 行 = %d 格 (yrow=%d+16*(row+%d))'
      % (ncol, nrow, ncol * nrow, y0, skip))
    iso = L['iso']
    gate = T.read_decode_gate(iso)
    P('[gate5] 盘上 ELF 解码闸门 = 0x%02X' % gate)
    assert (gate - 0xA1) * 94 <= ncol * nrow, '对偶空间 > 网格格数'

    cs_json = json.load(io.open(cs_in, encoding='utf-8'))
    plan = make_plan(L, mode, cs_json, gate)
    if plan is None:
        P('')
        P('[out] ★ 结论: **本盘在「不抬闸门 + 不丢字 + 字符不变」约束下无解** —— 未写盘。')
        _save(tag, dict(mode=mode, base=base, achievable=False, gate=gate,
                        pair_of=len(cs_json['pair_of']), cap=(gate - 0xA1) * 94), dry=True)
        L['iso'].close()
        return 2
    cs_new = patch_charset(cs_json, plan)
    P('[plan] charset: pair_of %d → %d (搬 %d 字, 注销 %d 占位/哨兵码)'
      % (len(cs_json['pair_of']), len(cs_new['pair_of']),
         len(plan['moves']), len(plan['dead'])))
    # ── 断言: 新 charset 里 trail ∈ {B1,B5} = 0 ──
    bad = [(ch, tuple(p)) for ch, p in cs_new['pair_of'].items() if p[1] in SENT]
    P('[A1] 新 charset 里 trail ∈ {B1,B5} 的登记: %d %s' % (len(bad), bad[:5]))
    assert not bad
    # ── 断言: 真字一个不丢 ──
    old_real = {ch for ch in cs_json['pair_of'] if not (0xE000 <= ord(ch) <= 0xF8FF)}
    new_real = {ch for ch in cs_new['pair_of'] if not (0xE000 <= ord(ch) <= 0xF8FF)}
    P('[A2] 真字 (非私有区) 数: %d → %d ; 丢失 %d ; 新增 %d'
      % (len(old_real), len(new_real), len(old_real - new_real), len(new_real - old_real)))
    assert old_real <= new_real, old_real - new_real
    # ── 断言: 编解码互逆 + 单射 + lead/trail 合法 ──
    inv_bad, seen_pairs = [], {}
    for ch, p in cs_new['pair_of'].items():
        tp = tuple(p)
        if tp in seen_pairs:
            inv_bad.append(('dup', ch, seen_pairs[tp]))
        seen_pairs[tp] = ch
        if not (0xA1 <= tp[0] < gate):
            inv_bad.append(('lead', ch, tp))
        if not (0xA1 <= tp[1] <= 0xFE):
            inv_bad.append(('trail', ch, tp))
        if tp[1] in SENT:
            inv_bad.append(('sentinel-trail', ch, tp))
    P('[A3] 新 charset: %d 条对偶码 —— 单射/lead/trail 全部合法: 违规 %d %s'
      % (len(cs_new['pair_of']), len(inv_bad), inv_bad[:4]))
    assert not inv_bad, inv_bad[:4]
    # 单字节码不得落在 lead 区间
    bads = sorted(b for b in cs_new['codes'].values() if 0xA1 <= b < gate)
    P('[A3b] 单字节码落在 lead 区间 [0xA1,0x%02X) 的: %d %s' % (gate, len(bads), bads[:8]))
    assert not bads

    conts = load_containers(iso)
    remap = {tuple(x['old_pair']): tuple(x['new_pair']) for x in plan['moves']}
    stat = dict(n=0, per={}, changed=0)
    plans = []
    for c in conts:
        nb = rebuild_container(c, gate, plan['pair_dec'], remap, stat)
        frame = c['raw']
        n_rep = 0
        if nb != c['blob']:
            frame, n_rep = repack(c, nb)
            assert len(frame) <= c['slot'], ('重压后超槽', c['tag'], len(frame), c['slot'])
        plans.append((c, frame, nb, n_rep))
    P('[A4] 文本改写: 命中 %d 处 (逐码: %s) ; 改动的区间 %d'
      % (stat['n'], ' '.join('%02X%02X:%d' % (k[0], k[1], v)
                             for k, v in sorted(stat['per'].items())), stat['changed']))
    n_core = sum(v for k, v in stat['per'].items())
    P('[A4b] 3 个中文容器命中 %d 处 (期望 = 哨兵 trail 站点总数)' % n_core)
    stat_char_seen = stat.get('chars', collections.Counter())
    # ── 覆盖范围: 3 容器之外还有没有真文本用到这些旧码 (权威口径 = 项目文本 CSV) ──
    L['charset_pair_of'] = plan['pair_of']
    other, rawhits = scan_other_locations(L, set(remap), gate)
    P('[A5] 3 容器之外「旧哨兵码 + 像文本」的从宽命中: %d 处 (CJK≥8 且占比≥0.9 且对偶码≥10; '
      '二进制美术资源会假阳性, 只登记)' % len(other))
    for o in other[:8]:
        P('[A5]   %s @0x%X  %02X%02X  %r' % (o['where'], o['off'], o['pair'][0],
                                              o['pair'][1], o['text']))
    P('[A5b] 全盘有原始旧码命中的条目 %d 个 (前 6: %s)'
      % (len(rawhits), ' '.join('%s×%d' % (r['where'].split(':')[-1], r['raw'])
                                for r in rawhits[:6])))
    chars_moved = [a['char'] for a in plan['moves']]
    csv_files, csv_cnt, n_csv = csv_char_usage(chars_moved)
    in_core = {ch for ch in stat_char_seen if ch}
    P('[A5c] ★ 权威口径: %d 份文本 CSV 里, 被搬的 %d 个字 —— 在 3 容器出现过 %d 个 ; '
      '在 CSV 里 0 次的 %d 个'
      % (n_csv, len(chars_moved), len(in_core & set(chars_moved)),
         len([ch for ch in chars_moved if csv_cnt[ch] == 0])))
    for ch in chars_moved:
        if ch not in in_core and csv_cnt[ch] == 0:
            continue
        if ch not in in_core:
            P('[A5c]   ★ %r 不在 3 容器里但 CSV 里有 %d 次 ⇒ 需人工确认' % (ch, csv_cnt[ch]))
    assert all((ch in in_core) or csv_cnt[ch] == 0 for ch in chars_moved), \
        '★ 有字既不在 3 容器、又在文本 CSV 里出现 ⇒ 必须先补进重编码范围'
    # ── 图集搬家 (内存像素面) ──
    plane_new = bytearray(L['plane'])
    rects = nonempty_rects(L['faces'])
    touch = []
    for a2 in plan['moves']:
        s, t = a2['old_slot'], a2['new_slot']
        csx, csy = cell(s, ncol, skip, y0)
        ctx_, cty = cell(t, ncol, skip, y0)
        g = cell_read(bytes(L['plane']), csx, csy)
        cell_write(plane_new, ctx_, cty, g)
        cell_write(plane_new, csx, csy, np.zeros((16, 16), dtype=bool))
        rt = cell_read(bytes(plane_new), ctx_, cty)
        assert (rt == g).all(), ('回读不等', a2['char'], t)
        touch.append(dict(char=a2['char'], old_slot=s, new_slot=t,
                          old_xy=[csx, csy], new_xy=[ctx_, cty], ink=int(g.sum()),
                          window=g.astype(int).tolist()))
    P('[A6] 字形搬家 %d 个: 每个「新格回读 == 源格」逐 texel ✓ (墨合计 %d)'
      % (len(touch), sum(t['ink'] for t in touch)))
    # 记录矩形内容逐像素不变 (旧格清零/新格写墨都不得落在任何非空记录窗内)
    badr = []
    for a2 in plan['moves']:
        cx, cy = cell(a2['new_slot'], ncol, skip, y0)
        hit = [r for r in rects if rect_hits_cell(r, cx, cy)]
        if hit:
            badr.append((a2['char'], a2['new_slot'], [(x[0], x[1]) for x in hit]))
    P('[A7] 目标格被非空 FT 记录矩形压着的: %d (必须 0) %s' % (len(badr), badr[:3]))
    assert not badr
    # 记录窗像素不变 (硬)
    nchg_rect = 0
    for r in rects:
        (_fn, _k, u0, v0, u1, v1) = r
        for yy in range(v0, v1):
            for xx in range(u0, u1):
                o = yy * (W // 2) + xx // 2
                if (L['plane'][o] & (0xF0 if (xx & 1) else 0x0F)) != \
                   (plane_new[o] & (0xF0 if (xx & 1) else 0x0F)):
                    nchg_rect += 1
    P('[A8] 全部 %d 条非空 FT 记录窗内的像素: 改变 %d 个 (必须 0)' % (len(rects), nchg_rect))
    assert nchg_rect == 0
    # 槽 0..2349 互不重叠 / 不越界
    seen = {}
    for s in range((gate - 0xA1) * 94):
        cx, cy = cell(s, ncol, skip, y0)
        assert 0 <= cx and cx + 16 <= w and 0 <= cy and cy + 16 <= h, (s, cx, cy)
        assert (cx, cy) not in seen, ('格位重复', s, seen[(cx, cy)])
        seen[(cx, cy)] = s
    P('[A9] 槽 0..%d 全部映到图集内互不重复的 16x16 格 ✓' % ((gate - 0xA1) * 94 - 1))
    ct_new, segs, covered = plane_to_container(L['ct'], bytes(plane_new), w)
    assert len(ct_new) == len(L['ct'])
    assert container_to_plane(ct_new, w, h) == bytes(plane_new), '容器回环不一致'
    P('[A10] 图集容器 %d B (同长) ; 回环逐字节相同 ✓' % len(ct_new))
    rep = dict(mode=mode, tag=tag, base=base, out=out, base_sha=sha256_file(base),
               base_size=os.path.getsize(base), charset_in=cs_in, gate=gate,
               atlas=dict(w=w, h=h, ncol=ncol, nrow=nrow, skip=skip, y0=y0,
                          px_size=px_size, cells=ncol * nrow),
               pair_of_before=len(cs_json['pair_of']), pair_of_after=len(cs_new['pair_of']),
               slot_space=(gate - 0xA1) * 94,
               n_moved=len(plan['moves']), n_retired=len(plan['dead']),
               moves=plan['moves'], retired=plan['dead'], skipped=plan['skipped'],
               text_hits=stat['n'], text_per_code={('%02X%02X' % k): v
                                                   for k, v in sorted(stat['per'].items())},
               text_changed_ranges=stat['changed'],
               other_locations=other, rects=len(rects),
               touch=touch)
    if a.dry_run:
        P('')
        P('[dry ] --dry-run: 全部断言通过, 未写盘')
        _save(tag, rep, dry=True)
        L['iso'].close()
        return 0

    # ── 写盘 ──
    with open(base, 'rb') as fi, open(out, 'wb') as fo:
        for blk in iter(lambda: fi.read(1 << 22), b''):
            fo.write(blk)
    with open(out, 'r+b') as f:
        f.seek(MENU_BASE + L['e_pak']['off'] + L['PX'])
        f.write(ct_new)
        for (c, frame, nb, n_rep) in plans:
            if frame == c['raw']:
                continue
            f.seek(c['iso_off'])
            f.write(frame + b'\x00' * (c['slot'] - len(frame)))
    P('[out ] %s  %d B  sha256=%s' % (out, os.path.getsize(out), sha256_file(out)))

    # ── 回读 ──
    Z = read_font(out)
    assert Z['ct'] == ct_new
    assert cell_read(Z['plane'], *(cell(0, ncol, skip, y0))) is not None
    nb_ok = sum(1 for t in touch
                if (cell_read(Z['plane'], *cell(t['new_slot'], ncol, skip, y0))
                    == np.array(t['window'], dtype=bool)).all())
    assert nb_ok == len(touch)
    P('[R1] 回读图集: %d/%d 个新格逐 texel == 源格 ✓' % (nb_ok, len(touch)))
    iso2 = T.Iso(out)
    okc = 0
    for (c, frame, nb, n_rep) in plans:
        e2 = iso2.img_entry(c['lba'], c['idx'])
        assert (e2['stored'], e2['off'], e2['real']) == (c['entry']['stored'],
                                                         c['entry']['off'],
                                                         c['entry']['real'])
        blob2 = b''.join(s[0] for s in T.lzo_subs(iso2.read(e2['iso_off'], e2['stored'])))
        assert blob2 == nb, c['tag']
        okc += 1
    P('[R2] 回读 %d 个容器 blob == 目标 ; IMG 条目表未动 ✓' % okc)
    iso2.close()
    # charset 落盘 (先备份)
    if mode == 'k2':
        cs_out = a.charset_out or CS_REPO
        bak = os.path.join(OUTDIR, 'backup',
                           os.path.basename(cs_out) + '.before_hashr')
        os.makedirs(os.path.dirname(bak), exist_ok=True)
        if not os.path.exists(bak):
            with open(cs_in, 'rb') as fi, open(bak, 'wb') as fo:
                fo.write(fi.read())
            P('[cs  ] 备份 %s → %s' % (cs_in, bak))
        with io.open(cs_out, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(cs_new, f, ensure_ascii=False, indent=1)
        P('[cs  ] 写入 %s (pair_of %d)' % (cs_out, len(cs_new['pair_of'])))
    rep['out_sha'] = sha256_file(out)
    rep['out_size'] = os.path.getsize(out)
    rep['cs_out'] = (a.charset_out or CS_REPO) if mode == 'k2' else None
    if not a.skip_diff:
        rep['diff'] = diff_report(out, base, L, plans)
    _save(tag, rep, dry=False)
    L['iso'].close()
    return 0


def csv_char_usage(chars):
    """项目**文本清单** (dump 出的 CSV) 里这些字各出现多少次 —— 权威口径。

    覆盖: 全部 `work/builds/*/text/*.csv` (注入表 *_text_*.csv + view_* 清单) +
    `temp/textdump*/*.csv` 全量表。
    """
    import glob
    pats = ['work/builds/*/text/*.csv', 'work/builds/*/temp/textdump*/*.csv',
            'work/builds/*/temp/textdump/*.csv']
    files = set()
    for p in pats:
        files.update(glob.glob(os.path.join(REPO, p)))
    cnt = collections.Counter()
    for f in sorted(files):
        try:
            t = io.open(f, encoding='utf-8', errors='replace').read()
        except Exception:                                                # noqa: BLE001
            continue
        for c in chars:
            cnt[c] += t.count(c)
    return sorted(files), cnt, len(files)


def scan_other_locations(L, patterns, gate, limit=60):
    """3 个中文容器之外「旧哨兵码 + 像文本」的命中 (**从宽**口径, 只登记不断言)。

    每个 IMG 条目先试 LZO 帧解析 (能解就用解压后的内容), 否则用原始字节;
    命中点 ±24 字节按旧 charset 解码, CJK ≥ 8 且占比 ≥ 0.9 且对偶码 ≥ 10 才算候选。
    ★ 二进制美术资源 (BMZ/RSB/SB) 会大量假阳性 (字节分布恰好落在 CJK 对偶空间里) ⇒
      本函数只用于登记; **权威口径是项目的文本 CSV** (见 csv_char_usage)。
    """
    iso = L['iso']
    out, raw = [], []
    ents = []
    for lba, nm in ((zx_lib.MENU_LBA, 'MENU.IMG'), (zx_lib.GR_LBA, 'GR.IMG')):
        for e in zx_lib.entries(iso, lba):
            ents.append((nm, e))
    pair_dec = {tuple(v): ch for ch, v in L['charset_pair_of'].items()}
    for (nm, e) in ents:
        if e['name'] == 'COMMON.PAK':
            continue
        data = iso.read(e['iso_off'], e['stored'])
        subs = T.lzo_subs(data)
        if subs and sum(s[2] for s in subs) >= 0.5 * len(data):
            data = b''.join(s[0] for s in subs)
        n_raw = 0
        for pat in patterns:
            pb = bytes(pat)
            start = 0
            while True:
                k = data.find(pb, start)
                if k < 0:
                    break
                start = k + 1
                n_raw += 1
                txt, npair = decode_window(data, gate, pair_dec,
                                           max(0, k - 24), min(len(data), k + 26))
                nch, ncjk = len(txt), sum(1 for c in txt if 0x4E00 <= ord(c) <= 0x9FFF)
                if ncjk >= 8 and nch and ncjk / nch >= 0.9 and npair >= 10 and len(out) < limit:
                    out.append(dict(where='%s:%s' % (nm, e['name']), off=k, pair=list(pat),
                                    text=txt))
        if n_raw:
            raw.append(dict(where='%s:%s' % (nm, e['name']), raw=n_raw))
    elf = iso.read(295 * 2048, 37453732)
    for pat in patterns:
        pb = bytes(pat)
        start = 0
        while True:
            k = elf.find(pb, start)
            if k < 0:
                break
            start = k + 1
            txt, npair = decode_window(elf, gate, pair_dec, max(0, k - 24), min(len(elf), k + 26))
            nch, ncjk = len(txt), sum(1 for c in txt if 0x4E00 <= ord(c) <= 0x9FFF)
            if ncjk >= 8 and nch and ncjk / nch >= 0.9 and npair >= 10 and len(out) < limit:
                out.append(dict(where='SLUS_206.13(ELF)', off=k, pair=list(pat), text=txt))
    return out, sorted(raw, key=lambda r: -r['raw'])


def decode_window(data, gate, pair_dec, lo, hi):
    """按 lead/trail 规则解码 [lo,hi) → (文本, 合法对偶码个数)。"""
    s, npair, i = [], 0, lo
    while i < hi:
        b = data[i]
        if T.LEAD_LO <= b < gate:
            t = data[i + 1] if i + 1 < hi else None
            if t is not None and (b, t) in pair_dec:
                s.append(pair_dec[(b, t)])
                npair += 1
                i += 2
                continue
            s.append('\ufffd')
            i += 1
            continue
        s.append(chr(b) if 0x20 <= b < 0x7F else '\ufffd')
        i += 1
    return ''.join(s), npair


def diff_report(out, base, L, plans):
    win = [(MENU_BASE + L['e_pak']['off'] + L['PX'],
            MENU_BASE + L['e_pak']['off'] + L['PX'] + L['px_size'])]
    for (c, frame, nb, n_rep) in plans:
        if frame != c['raw']:
            win.append((c['iso_off'], c['iso_off'] + c['slot']))
    sz = os.path.getsize(base)
    n_in = n_out = 0
    ex = []
    spans = []
    with open(out, 'rb') as fo, open(base, 'rb') as fb:
        pos = 0
        while pos < sz:
            n = min(1 << 22, sz - pos)
            bo, bb = fo.read(n), fb.read(n)
            if bo != bb:
                i = 0
                while i < n:
                    if bo[i] != bb[i]:
                        j = i
                        while j < n and bo[j] != bb[j]:
                            j += 1
                        p = pos + i
                        spans.append((p, pos + j))
                        if any(lo <= p < hi for (lo, hi) in win):
                            n_in += j - i
                        else:
                            n_out += j - i
                            if len(ex) < 8:
                                ex.append((p, bb[i], bo[i]))
                        i = j
                    else:
                        i += 1
            pos += n
    P('[D  ] 全盘差异: 计划窗口内 %d B ; **窗口外 %d B** %s' % (n_in, n_out, ex))
    P('[D  ] 差异区间 %d 段 ; 窗口 %s' % (len(spans), [(hex(a), hex(b)) for (a, b) in win]))
    assert n_out == 0, ex
    return dict(in_window=n_in, out_window=n_out, spans=len(spans),
                windows=[[a, b] for (a, b) in win])


def _save(tag, rep, dry):
    name = '%s_%s.json' % (tag, 'dry' if dry else 'build')
    with io.open(os.path.join(OUTDIR, 'temp', name), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dict(extra=rep, log=LOG), f, ensure_ascii=False, indent=1)
    with io.open(os.path.join(OUTDIR, 'temp', '%s_%s.log' % (tag, 'dry' if dry else 'build')),
                 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    P('[out] %s' % os.path.join(OUTDIR, 'temp', name))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
