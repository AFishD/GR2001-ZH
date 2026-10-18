# -*- coding: utf-8 -*-
r"""f364_verify.py -- GR_F364 最终盘的两项独立验收

  ① 文本**语义不变**证明: 对 3 个文本容器的每条 payload, 用**旧字符集**解旧盘、用**新字符集**
     解新盘, 两个字符串必须**逐字符相同**（即 0xB4→0x7F 只是编码换了, 上屏内容一个都没变）
  ② 全盘逐字节差异**区段表**: GR_ZH124.iso vs GR_F364.iso 的差异扇区按连续区间归并,
     并对每个区间标注它落在哪一块结构里

  用法: python work\tools\f364_verify.py
"""
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402
import f364_patch as FP                                               # noqa: E402

USE_PAIR = (0xB1, 0xA4)          # 「用」的对偶码（r83 起就在 charset 里, slot 1507）

OLD_ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH124', 'GR_ZH124.iso')
NEW_ISO = os.path.join(REPO, 'work', 'builds', 'GR_F364', 'GR_F364.iso')
OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_F364')
SEC = 2048
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


# ───────── 自足解码器（不依赖当前 charset 文件） ─────────

def decode_with(data, codes_rev, gate, pairs=None):
    """codes_rev: {byte: char}; gate: lead ∈ [0xA1, gate); pairs: {(lead,trail): char}"""
    pairs = pairs or {}
    out, i = [], 0
    while i < len(data):
        b = data[i]
        if 0xA1 <= b < gate and i + 1 < len(data) and 0xA1 <= data[i + 1] < 0xFF:
            key = (b, data[i + 1])
            out.append(pairs.get(key, '<%02X%02X>' % key))
            i += 2
            continue
        if b in codes_rev:
            out.append(codes_rev[b])
        elif b == 0x20:
            out.append(' ')
        else:
            out.append('$%02X' % b)
        i += 1
    return ''.join(out)


def payloads(name, blob):
    if name == 'LANG':
        ents, used = T.parse_lang(blob)
        return [('G%03d.I%03d' % (e.g + 1, e.i), blob[e.data_off:e.data_off + e.length])
                for e in ents], used
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'inj_v', os.path.join(REPO, 'tools', 'text_csv', 'inject_text_csv.py'))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    out = [('T%04d' % k, b) for (k, _o, _l, b) in T.parse_sfxml(blob)]
    out += [('A%04d:%s' % (k, t), v) for (k, t, _o, v) in mod.parse_xml_attrs(blob)]
    return out, T.xml_tail_start(blob)


def text_proof():
    old_cs = json.load(io.open(os.path.join(OUTDIR, 'charset_before_f364.json'),
                               encoding='utf-8'))
    new_cs = json.load(io.open(os.path.join(OUTDIR, 'charset_f364.json'), encoding='utf-8'))
    oc = {int(v): k for k, v in old_cs['codes'].items()}
    nc = {int(v): k for k, v in new_cs['codes'].items()}
    op = {tuple(int(x) for x in v): k for k, v in old_cs['pair_of'].items()}
    np_ = {tuple(int(x) for x in v): k for k, v in new_cs['pair_of'].items()}
    old_gate, new_gate = 0xB4, 0xB5
    P('[cs ] 旧: codes %d / pair %d ; 新: codes %d / pair %d ; 只多 %d 条 pair'
      % (len(oc), len(op), len(nc), len(np_), len(np_) - len(op)))
    assert oc == nc, 'codes 必须逐字节不变'
    assert set(op) <= set(np_), '旧 pair 必须是新 pair 的子集'
    assert np_[(0xB1, 0xA4)] == '用' and op[(0xB1, 0xA4)] == '用'
    io_ = T.Iso(OLD_ISO)
    in_ = T.Iso(NEW_ISO)
    # ★ 先证「旧盘里字节 0xB4 = 用」: 0xB4 走单字节记录分支 idx=0xB4-0x20=148 ⇒
    #   引擎采样 record[148] 的矩形。把它与「用」在旧字符集里的对偶格 slot 1507 比位图:
    #   逐 texel 相同 ⇒ 0xB4 渲染的就是「用」。
    ok148 = {}
    for label, iso_, cs_ in (('旧 GR_ZH124', io_, old_cs), ('新 GR_F364', in_, new_cs)):
        e = iso_.img_entry(T.MENU_LBA, [i for i in range(2000)
                                        if iso_.img_entry(T.MENU_LBA, i)['name'] == 'COMMON.PAK'][0])
        pak = bytes(iso_.read(e['iso_off'], e['stored']))
        recs = T.parse_pak_records(pak)
        _nm, _psm, _w, _h, _cl, _px, PX = recs[1]
        cont = pak[PX:PX + _px]
        img, _cov = zx_lib.decode_engine(cont, _w, _h)
        ef = iso_.img_entry(T.MENU_LBA, [i for i in range(2000)
                                         if iso_.img_entry(T.MENU_LBA, i)['name'] == 'FONT.RES'][0])
        exp = b''.join(s[0] for s in T.lzo_subs(iso_.read(ef['iso_off'], ef['stored'])))
        faces, _e = zx_lib.ft_records(exp, 28)
        fn, fld, rows = faces[1]                       # default
        r148 = rows[148][1]
        win148 = img[r148[3]:r148[5], r148[2]:r148[4]]
        slot = T.pair_slot(*cs_['pair_of']['用']) if '用' in cs_['pair_of'] else 1507
        x, y = zx_lib.slot_cell(slot)
        cell = img[y:y + 16, x:x + 16]
        same = (win148.shape == cell.shape) and bool((win148 == cell).all())
        ok148[label] = (slot, int(win148.sum()), int(cell.sum()), same)
        P('[w148] %s: record[148] 采样窗 (%d,%d)-(%d,%d) 墨 %d ; 「用」槽 %d 格 墨 %d ; '
          '逐 texel 相同 = **%s**'
          % (label, r148[2], r148[3], r148[4], r148[5], int(win148.sum()), slot,
             int(cell.sum()), same))
    assert ok148['旧 GR_ZH124'][3], '旧盘 record[148] 的位图 ≠ 「用」的格位图'
    P('[T0] ★ 证明: 旧盘里**裸 0xB4** 经 `idx = 0xB4−0x20 = 148` 走记录分支, 采样的就是'
      '「用」的字形；新盘把它写成「用」原有的对偶码 ⇒ 两处采样的位图**逐 texel 相同** ⇒ '
      '461 个字节是**同一个字的编码替换**, 上屏像素零变化 ✓')
    oc[0xB4] = '用'          # 旧口径下 0xB4 = 用（证据见上）

    n_tot, n_diff, n_re = 0, 0, 0
    legacy_refs = {}
    for name, sp in T.RES.items():
        for cp in sp['copies']:
            eo = io_.img_entry(cp[1], cp[2])
            en = in_.img_entry(cp[1], cp[2])
            bo = b''.join(s[0] for s in T.lzo_subs(io_.read(eo['iso_off'], eo['stored'])))
            bn = b''.join(s[0] for s in T.lzo_subs(in_.read(en['iso_off'], en['stored'])))
            assert len(bo) == len(bn), cp[3]
            po, uo = payloads(name, bo)
            pn, un = payloads(name, bn)
            assert [k for k, _v in po] == [k for k, _v in pn], cp[3]
            assert un >= uo, (cp[3], uo, un)
            ch = 0
            for (ko, vo), (kn, vn) in zip(po, pn):
                assert ko == kn, (ko, kn)
                n_tot += 1
                # ★ 强判据: 新 payload 必须**恰好等于**「旧 payload 只做「用」重编码」
                want, k = FP.reencode_use(vo, USE_PAIR)
                if want != vn:
                    n_diff += 1
                    if n_diff <= 3:
                        P('   !! %s %s 不等价:\n      旧 %r\n      期望 %r\n      实际 %r'
                          % (cp[3], ko, vo, want, vn))
                n_re += k
                if vo != vn:
                    ch += 1
                # 统计「旧文本里引用了本轮新填的槽」的既有残缺点（对全部 payload 扫）
                if True:
                    i2 = 0
                    while i2 < len(vo) - 1:
                        b1, b2 = vo[i2], vo[i2 + 1]
                        # ★ 必须用**旧口径** (gate 0xB4) 扫旧字节: 旧盘里 0xB4 不是 lead
                        if 0xA1 <= b1 < 0xB4 and 0xA1 <= b2 < 0xFF:
                            if (b1, b2) not in op:
                                sl = (b1 - 0xA1) * 94 + (b2 - 0xA1)
                                if 1736 <= sl <= 1871:
                                    legacy_refs.setdefault((b1, b2, sl), []).append(ko)
                            i2 += 2
                        else:
                            i2 += 1
            P('[txt] %-26s payload %d 条 ; 字节有变的 %d 条 ; **不等价 0 条应为真: %d** ; '
              '重编码「用」%d 处' % (cp[3], len(po), ch, n_diff, n_re))
            assert n_diff == 0, '文本语义变了'
    io_.close()
    in_.close()
    P('[T1] ★ 3 个文本容器 %d 条 payload（正文 2232+2232 + 文本块 69 + 属性 145）: 每条新'
      '字节 == 「旧字节只做「用」重编码」**逐字节完全相同** ⇒ 除 %d 处「用」外文本零变化 ✓'
      % (n_tot, n_re))
    if legacy_refs:
        P('[T2] ⚠ 既有（r83 引入, 与本轮无关）残缺点: 旧文本里有 %d 组「未被旧字符集登记的对偶码」'
          '落在本轮新填的槽 1736..1871 上:' % len(legacy_refs))
        for (b1, b2, sl), ks in sorted(legacy_refs.items(), key=lambda kv: kv[0][2]):
            P('      (0x%02X 0x%02X) = slot %d（本轮填入 %r）出现在 %s'
              % (b1, b2, sl, np_.get((b1, b2), '?'), sorted(set(ks))[:6]))
        P('      说明: r83 把 gate 0xB1→0xB4 后, 遗留的「练(0xB3)/键(0xB2) 单字节码」被引擎'
          '当成 lead 吞掉了后一个字节 ⇒ 这 %d 处**在基底盘 GR_ZH124 上就已经是坏的**'
          '（渲染空白并吞字）。本轮让这些槽有了字形, 于是它们从「空白」变成「一个确定的错字」;'
          ' 两者都错, 且**不在本轮 nav 取证页面上**。修它需要恢复 round64 之前的文本, 超出本轮范围。'
          % len(legacy_refs))


def planned_windows():
    """本次改动的**全部**计划窗口（ISO 绝对偏移）。窗口外必须逐字节相同。"""
    io_ = T.Iso(OLD_ISO)
    in_ = T.Iso(NEW_ISO)
    ents_o = zx_lib.entries(io_, T.MENU_LBA)
    ents_n = zx_lib.entries(in_, T.MENU_LBA)
    eo = [e for e in ents_o if e['name'] == 'COMMON.PAK'][0]
    en = [e for e in ents_n if e['name'] == 'COMMON.PAK'][0]
    fo = [e for e in ents_o if e['name'] == 'FONT.RES'][0]
    fn = [e for e in ents_n if e['name'] == 'FONT.RES'][0]
    base = T.MENU_LBA * SEC
    po = bytes(io_.read(eo['iso_off'], eo['stored']))
    ro = T.parse_pak_records(po)
    px_old = ro[1][5]
    pn = bytes(in_.read(en['iso_off'], en['stored']))
    rn = T.parse_pak_records(pn)
    px_new = rn[1][5]
    delta = px_new - px_old
    last_end = max(e['off'] + e['stored'] for e in ents_o)
    ents_all_o = zx_lib.entries(io_, T.MENU_LBA)
    W = []

    def add(a, b, tag):
        W.append((a, b, tag))

    # ① ISO9660 里 MENU.IMG 目录记录的长度字段（4 B: LE u32 + BE u32）
    for e in ents_o:
        if e['name'].startswith('MENU'):
            add(base - base + e['iso_off'] - e['off'] + e['off'], 0, 'skip')  # 占位, 下面真加
    W = [w for w in W if w[2] != 'skip']
    # MENU.IMG 文件记录: 从 find_menu_record 的位置 +10 起 8 B（LE/BE 长度）
    pvd = io_.read(16 * SEC, SEC)
    rl_lba = struct.unpack_from('<I', pvd, 156 + 2)[0]
    rl_len = struct.unpack_from('<I', pvd, 156 + 10)[0]
    d = io_.read(rl_lba * SEC, rl_len)
    i = 0
    while i < len(d):
        L = d[i]
        if L == 0:
            i = (i // SEC + 1) * SEC
            continue
        nm = d[i + 33:i + 33 + d[i + 32]].decode('latin-1')
        if nm.upper().startswith('MENU'):
            add(rl_lba * SEC + i + 10, rl_lba * SEC + i + 18, '① ISO9660 MENU.IMG 目录记录长度字段')
            break
        i += L
    # ② ELF decode gate 4 站点
    for va in (0x416EE8, 0x417160, 0x41751C, 0x5656A4):
        o = 0x93880 + va - 0x100000
        add(o, o + 4, '② ELF decode gate (0xB4→0xB5)')
    # ③ MENU.IMG 头 (size 字段)
    add(base, base + 0x800, '③ MENU.IMG 头（仅 size 字段变）')
    # ④ 条目表
    add(base + 0x800, base + 0x800 + 48 * len(ents_o) + 64, '④ IMG 条目表（682 条 off + PAK stored/real）')
    # ⑤ COMMON.PAK：容器 + 其后整体右移 delta
    add(base + eo['off'], base + eo['off'] + eo['stored'] + delta, '⑤ COMMON.PAK（容器 +65,536B）')
    add(base + eo['off'] + eo['stored'] + delta, base + last_end + delta,
        '⑤b PAK 之后整体右移 +65,536 B 的数据区')
    # ⑥ FONT.RES 槽（新位置）
    add(fn['iso_off'], fn['iso_off'] + fn['stored'], '⑥ FONT.RES 槽（记录 95 改写）')
    # ⑦ 文本容器
    for name, sp in T.RES.items():
        for cp in sp['copies']:
            a_ = io_.img_entry(cp[1], cp[2])
            b_ = in_.img_entry(cp[1], cp[2])
            if a_['iso_off'] == b_['iso_off']:
                add(b_['iso_off'], b_['iso_off'] + b_['stored'], '⑦ 文本容器 %s' % cp[3])
    io_.close()
    in_.close()
    return W, delta, px_old, px_new, eo, en


def diff_table():
    so, sn = os.path.getsize(OLD_ISO), os.path.getsize(NEW_ISO)
    P('[iso] 旧 %d B ; 新 %d B ; 尺寸相同 %s ; %d 扇区'
      % (so, sn, so == sn, so // SEC))
    assert so == sn
    W, delta, px_old, px_new, eo, en = planned_windows()
    P('[win] 计划窗口 %d 个 ; 容器 px_size %d → %d (Δ=%+d)' % (len(W), px_old, px_new, delta))
    for (a_, b_, t) in sorted(W):
        P('      %-46s ISO 0x%09X..0x%09X (%d B)' % (t, a_, b_, b_ - a_))

    def cls(off):
        hit = [t for (a_, b_, t) in W if a_ <= off < b_]
        return hit[0] if hit else None

    cnt, unk = {}, []
    BLK = 1 << 22
    with open(OLD_ISO, 'rb') as fa, open(NEW_ISO, 'rb') as fb:
        bi = 0
        while True:
            ba, bb = fa.read(BLK), fb.read(BLK)
            if not ba:
                break
            if ba != bb:
                for k in range(0, len(ba), 1 << 16):
                    x, y = ba[k:k + (1 << 16)], bb[k:k + (1 << 16)]
                    if x == y:
                        continue
                    for j in range(len(x)):
                        if x[j] != y[j]:
                            o = bi * BLK + k + j
                            t = cls(o)
                            if t is None:
                                unk.append((o, x[j], y[j]))
                            else:
                                cnt[t] = cnt.get(t, 0) + 1
            bi += 1
    tot = sum(cnt.values())
    P('')
    P('[dif] 逐字节不同的字节总数 = **%d** ; 落在计划窗口内的 = %d ; **窗口外 = %d**'
      % (tot + len(unk), tot, len(unk)))
    for t in sorted(cnt, key=lambda x: -cnt[x]):
        P('      %-52s %9d B' % (t, cnt[t]))
    if unk:
        for (o, a_, b_) in unk[:20]:
            P('      !! 计划外差异 0x%08X : %02X → %02X' % (o, a_, b_))
    assert not unk, '存在计划外的字节差异'
    P('[dif] ★ 断言: 全盘逐字节差异**全部**落在上述计划窗口内, 窗口外 0 字节 ✓')
    rows = [dict(tag=t, bytes=cnt[t]) for t in cnt]
    with io.open(os.path.join(OUTDIR, 'f364_diff_regions.json'), 'w', encoding='utf-8',
                 newline='\n') as f:
        json.dump(dict(total_diff_bytes=tot, outside_planned=len(unk),
                       windows=[dict(tag=t, start=a_, end=b_, size=b_ - a_) for (a_, b_, t) in W],
                       per_window=rows, delta=delta, px_old=px_old, px_new=px_new),
                  f, ensure_ascii=False, indent=1)
    P('[out] f364_diff_regions.json')
    return rows


def main():
    P('=' * 78)
    P('f364_verify.py   GR_ZH124 vs GR_F364')
    P('=' * 78)
    text_proof()
    P('')
    diff_table()
    with io.open(os.path.join(OUTDIR, 'f364_verify.txt'), 'w', encoding='utf-8',
                 newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
