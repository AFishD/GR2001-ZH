# -*- coding: utf-8 -*-
r"""patch_zh_fix_order_label.py — 修正「小队设置」页 A组/B组 ◀▶ 按钮错译「命令」→「顺序」(GR_ZH90)

## 用户报障
主菜单→战术演习→练习1→继续→**小队设置**页: A组 / B组 各有一个金色按钮, 文字是「命令」,
左右各有一个 ◀ ▶ 箭头; 页面底部帮助条写「左右键更换队员顺序。」
⇒ 该按钮是**队员排序选择器**, 不是"下达命令"。译作「命令」是字面直译, 与功能不符。

## 英文原盘取证 (work/builds/GR_EN_ORIG/GR_EN_ORIG.iso)
同屏文案全部在语言表 `EN_STRINGS.RES` 的 **G58 组**里, 英文原盘逐条为:
    G58.I190 BRIEFING        G58.I191 ROSTER         G58.I192 Alpha
    G58.I193 Bravo           G58.I194 Charlie        G58.I195 **Order**      ← 本补丁目标
    G58.I196 Select Soldier  G58.I197 PLATOON SELECTOR
    G58.I198 SQUAD SELECTOR  G58.I199 STATS/KIT      G58.I200 PICKS KIT
且同屏帮助条:
    G58.I091 EN "Left and right to select soldier."            ZH「左右键选择队员。」
    G58.I092 EN "Left and right to change soldiers **order**." ZH「左右键更换队员顺序。」
⇒ EN 按钮名 `Order` 与帮助条 `change soldiers order` 同词。中文帮助条已把该词译作**顺序**,
  故按钮名必须同样用「顺序」, 才与帮助条自洽。旧译「命令」= Order 的"下令/命令"义项, 属**词义选错**。

## 数据位置 (两处, 同一份逻辑表的副本)
  MENU.IMG #25  EN_STRINGS.RES : LBA 776286, 槽 47570B, 条目表 +0x830 步长 48
  GR.IMG   #902 EN_STRINGS.RES : LBA 19175,  槽 47619B
  结构: {u32 ngroups} + 每组 [{u32 id (第2组起)} {u32 count}] + 条目 {u32 len}{data}{u16 attr}
  容器: 8 条 LZO 子流 (16384×7 + 尾流), 每流前置 {u32 clen}{u32 olen}
  ZH 版明文实际仅用 68,615B, 其后 59,930B 全 0 (容量冗余) ⇒ 有充足的平移余量。

  目标条目 G58.I195: 长度字段 @0x00BE5E (=3), 数据 @0x00BE62, 旧字节 `e0 a1 ba` (=「命令」)
                     新字节 `a6 b8 a5 bd` (=「顺序」, 顺=pair(A6,B8) 序=pair(A5,BD))

## 做法 (纯数据, 零 ELF, 不动任何条目表/内部偏移)
  1. 明文里把长度 3→4, 数据 3B→4B (+1B);
  2. 为保持**每条子流 olen 与整体布局完全不变**, 从明文**末尾**扣掉 1B (尾部全 0 填充, 已断言);
  3. 按**原子流边界**重新切分 + 逐流 LZO 重压 + 回环校验;
  4. 整帧写回槽内 (余量补 0), 回读逐字节自验;
  5. MENU / GR 两份表都改 (同一逻辑表, 保证任何读取路径一致)。

用法: python patch_zh_fix_order_label.py <src_iso> <dst_iso>
      基底必须 = 现役盘 GR_ZH89 (sha256 见下); 另基底用环境变量 R29_ALLOW_ANY_BASE=1 放行。
"""
import hashlib
import json
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
from lz77_decode import lzo1x_decompress                      # noqa: E402
from lzo1x_c import compress as lzo_compress                  # noqa: E402

BASE_SHA256 = '6d2afd49a3d158253d9c9cfd2cd1678c57ed1ab39e6cc502938b7d37eca26cbf'  # GR_ZH89
BASE_NAME = 'GR_ZH89'

MENU_LBA, MENU_IDX = 776286, 25
GR_LBA, GR_IDX = 19175, 902
RES_NAME = 'EN_STRINGS.RES'
TAB_OFF, TAB_STEP = 0x830, 48
NSUB = 8

CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')

GROUP, ITEM = 57, 195          # G58.I195 (0-based)
OLD_RAW = bytes((0xE0, 0xA1, 0xBA))          # 「命令」
NEW_ZH = '顺序'
OLD_ZH = '命令'
DATA_OFF = 0x00BE62            # 明文内偏移 (断言用)
LEN_OFF = DATA_OFF - 4


# ─────────────────────────── 编解码 ───────────────────────────
def load_charset():
    c = json.load(open(CHARSET, encoding='utf-8'))
    return ({k: int(v) for k, v in c['codes'].items()},
            {k: tuple(v) for k, v in c['pair_of'].items()})


def enc(zh, codes, pairs):
    o = bytearray()
    for ch in zh:
        if ord(ch) < 0x80:
            o.append(ord(ch))
        elif ch in codes:                      # ★ 单字节码优先 (与 tools 下既有 enc() 同口径)
            o.append(codes[ch])
        elif ch in pairs:
            o += bytes(pairs[ch])
        else:
            raise AssertionError('字表无此字: %r' % ch)
    return bytes(o)


def dec(raw, codes, pairs):
    """单字节优先 —— 实测口径, 见 work/_dis/r29_res_scan.py 的注释。"""
    codes = {v: k for k, v in codes.items()}
    pairs = {tuple(v): k for k, v in pairs.items()}
    o, i = [], 0
    while i < len(raw):
        b = raw[i]
        if b in codes:
            o.append(codes[b]); i += 1
        elif i + 1 < len(raw) and (b, raw[i + 1]) in pairs:
            o.append(pairs[(b, raw[i + 1])]); i += 2
        elif 0x20 <= b < 0x7F:
            o.append(chr(b)); i += 1
        else:
            o.append('[%02X]' % b); i += 1
    return ''.join(o)


# ─────────────────────────── 容器读写 ───────────────────────────
def entry_slot(data, lba, idx):
    base = lba * 2048
    stored, real, off = struct.unpack_from('<III', data, base + TAB_OFF + TAB_STEP * idx + 24)
    return base, stored, real, off


def split_subs(slot):
    """返回 [(plain, clen, olen, comp_bytes), ...], 帧总长"""
    subs, p = [], 0
    while p + 8 <= len(slot):
        clen, olen = struct.unpack_from('<II', slot, p)
        if clen == 0 and olen == 0:
            break
        assert p + 8 + clen <= len(slot), '子流 %d 帧头越界' % len(subs)
        comp = bytes(slot[p + 8:p + 8 + clen])
        plain, err, _ = lzo1x_decompress(comp, out_size=olen)
        assert err is None, '子流 %d 解压失败' % len(subs)
        assert len(plain) == olen, '子流 %d 解压长度 %d != %d' % (len(subs), len(plain), olen)
        subs.append((bytes(plain), clen, olen, comp))
        p += 8 + clen
    return subs, p


def pack_subs(chunks):
    """chunks = [(new_plain, old_plain, old_clen, olen, old_comp), ...]

    ★ 明文未变的子流**原样复用原压缩字节** —— 本项目的 lzo1x_c(level=5) 与原盘产物流
      并不逐字节相同 (实测 sub1: 明文一致但 clen 8905→8906), 复用可把改动面压到最小。
    """
    out = bytearray()
    for k, (chunk, old, olen, old_comp) in enumerate(chunks):
        if chunk == old:
            out += struct.pack('<II', len(old_comp), olen) + old_comp
            continue
        comp = lzo_compress(chunk, level=5)
        back, err, _ = lzo1x_decompress(comp, out_size=olen)
        assert err is None and bytes(back) == bytes(chunk), '子流 %d 回环失败' % k
        out += struct.pack('<II', len(comp), olen) + comp
    return bytes(out)


def parse_entries(plain):
    """返回 [(data_off, len, raw)] 与 consumed; 结构与容器一致。"""
    p = 0
    ng = struct.unpack_from('<I', plain, p)[0]
    p += 4
    out = []
    for g in range(ng):
        if g > 0:
            p += 4
        cnt = struct.unpack_from('<I', plain, p)[0]
        p += 4
        for _ in range(cnt):
            ln = struct.unpack_from('<I', plain, p)[0]
            p += 4
            out.append((p, ln, bytes(plain[p:p + ln])))
            p += ln + 2
    return out, p, ng


# ─────────────────────────── 主流程 ───────────────────────────
def main(src, dst):
    codes, pairs = load_charset()
    new_raw = enc(NEW_ZH, codes, pairs)
    print('[译法 ] 「%s」->「%s」  %s -> %s  (%dB -> %dB)'
          % (OLD_ZH, NEW_ZH, OLD_RAW.hex(' '), new_raw.hex(' '), len(OLD_RAW), len(new_raw)))
    assert len(new_raw) == 4, '新译不是 4 字节 (%d)' % len(new_raw)
    assert dec(new_raw, codes, pairs) == NEW_ZH, '新字节回译不符'
    assert dec(OLD_RAW, codes, pairs) == OLD_ZH, '旧字节回译不符'

    sd = open(src, 'rb').read()
    sha = hashlib.sha256(sd).hexdigest()
    print('[src  ] %s  %d B  sha256=%s' % (src, len(sd), sha))
    if os.environ.get('R29_ALLOW_ANY_BASE') == '1':
        print('[base ] ★ R29_ALLOW_ANY_BASE=1 → 跳过基线 sha 断言')
    else:
        assert sha == BASE_SHA256, \
            '基底不是 %s (期望 sha256 %s, 实得 %s)\n本补丁只允许打在现役盘 %s 上。' \
            % (BASE_NAME, BASE_SHA256, sha, BASE_NAME)

    # GR 份的索引按名字表解析后再与常量核对 (防 LBA/索引漂移)
    gbase = GR_LBA * 2048
    noff = struct.unpack_from('<I', sd, gbase + 0x10)[0]
    nend = struct.unpack_from('<I', sd, gbase + 4)[0]
    names = [x.decode('latin-1') for x in sd[gbase + noff:gbase + nend].split(b'\x00') if x]
    assert names.count(RES_NAME) == 1, 'GR 名字表里 %s 出现 %d 次' % (RES_NAME, names.count(RES_NAME))
    gr_idx = names.index(RES_NAME)
    assert gr_idx == GR_IDX, 'GR 索引漂移: %d != %d' % (gr_idx, GR_IDX)

    shutil.copyfile(src, dst)
    touched = []
    with open(dst, 'r+b') as f:
        for tag, lba, idx in (('MENU#%d' % MENU_IDX, MENU_LBA, MENU_IDX),
                              ('GR#%d' % GR_IDX, GR_LBA, gr_idx)):
            base, stored, real, off = entry_slot(sd, lba, idx)
            slot = sd[base + off:base + off + stored]
            subs, framesz = split_subs(slot)
            assert len(subs) == NSUB, '%s 子流 %d != %d' % (tag, len(subs), NSUB)
            plain = b''.join(s[0] for s in subs)
            assert len(plain) == real, '%s 明文 %d != real %d' % (tag, len(plain), real)
            tail = slot[framesz:]
            assert tail.count(0) == len(tail), '%s 帧尾非零填充 (%d B)' % (tag, len(tail))

            ents, consumed, ng = parse_entries(plain)
            assert ng == 66, '%s ngroups %d' % (tag, ng)
            # 按 (组, 序) 精确定位目标条目
            p = 4
            found = None
            for g in range(ng):
                if g > 0:
                    p += 4
                cnt = struct.unpack_from('<I', plain, p)[0]
                p += 4
                for ii in range(cnt):
                    ln = struct.unpack_from('<I', plain, p)[0]
                    p += 4
                    if g == GROUP and ii == ITEM:
                        found = (p, ln)
                    p += ln + 2
            assert found is not None, '%s 未定位到 G%02d.I%03d' % (tag, GROUP + 1, ITEM)
            doff, dlen = found
            assert doff == DATA_OFF, '%s 数据偏移 %#X != %#X' % (tag, doff, DATA_OFF)
            assert dlen == len(OLD_RAW), '%s 旧长度 %d != %d' % (tag, dlen, len(OLD_RAW))
            assert plain[doff:doff + dlen] == OLD_RAW, \
                '%s 旧字节 %s != %s' % (tag, plain[doff:doff + dlen].hex(' '), OLD_RAW.hex(' '))
            assert dec(plain[doff:doff + dlen], codes, pairs) == OLD_ZH, '%s 旧文回译不符' % tag

            # ── 明文替换 (长度字段 3→4, 数据 +1B, 末尾扣 1B 零填充保持总长) ──
            new_plain = (plain[:LEN_OFF] + struct.pack('<I', len(new_raw)) +
                         new_raw + plain[doff + dlen:])
            assert len(new_plain) == len(plain) + 1
            assert new_plain[-1] == 0x00, '%s 明文末字节非 0 (%02X), 拒绝扣尾' % (tag, new_plain[-1])
            new_plain = new_plain[:-1]
            assert len(new_plain) == len(plain), '%s 扣尾后长度 %d != %d' % (tag, len(new_plain), len(plain))
            # 除目标条目外, 其余条目逐一相同 (结构完整性)
            ents2, consumed2, ng2 = parse_entries(new_plain)
            assert (ng2, consumed2) == (ng, consumed + 1), \
                '%s 结构漂移 ng=%d/%d consumed=%d/%d' % (tag, ng2, ng, consumed2, consumed + 1)
            assert len(ents2) == len(ents), '%s 条目数 %d != %d' % (tag, len(ents2), len(ents))
            n_diff = 0
            for k, ((o1, l1, r1), (o2, l2, r2)) in enumerate(zip(ents, ents2)):
                if o1 == doff:                           # 目标条目 (数据偏移即唯一键)
                    assert l2 == len(new_raw) and r2 == new_raw, '%s 目标条目未更新' % tag
                    n_diff += 1
                    continue
                assert (l1, r1) == (l2, r2), '%s 第 %d 条被误改 (len %d/%d)' % (tag, k, l1, l2)
            assert n_diff == 1, '%s 命中条目 %d 个' % (tag, n_diff)
            print('[find ] %s  G%02d.I%03d @ 明文 %#X  旧=%s (%dB)  其余 %d 条逐一不变 ✓'
                  % (tag, GROUP + 1, ITEM, doff, OLD_RAW.hex(' '), dlen, len(ents) - 1))

            # ── 原子流边界重切 + 重压 (明文未变的子流原样复用) ──
            sizes = [s[2] for s in subs]
            assert sum(sizes) == len(new_plain)
            chunks, q = [], 0
            for k, sz in enumerate(sizes):
                chunks.append((new_plain[q:q + sz], subs[k][0], subs[k][2], subs[k][3]))
                q += sz
            assert q == len(new_plain)
            frame = pack_subs(chunks)
            assert len(frame) <= stored, '%s 重压超槽 %d > %d' % (tag, len(frame), stored)
            n_re = sum(1 for c in chunks if c[0] != c[1])
            print('[pack ] %s  8 子流 (%d 条明文未变→原样复用, %d 条重压) = %dB '
                  '(槽 %dB, 余 %dB, olen 全不变)'
                  % (tag, len(chunks) - n_re, n_re, len(frame), stored, stored - len(frame)))

            f.seek(base + off)
            f.write(frame + b'\x00' * (stored - len(frame)))
            f.flush()
            # ── 回读自验 ──
            f.seek(base + off)
            back = f.read(stored)
            subs_b, _ = split_subs(back)
            assert len(subs_b) == NSUB
            assert [s[2] for s in subs_b] == sizes, '%s 回读 olen 变了' % tag
            pb = b''.join(s[0] for s in subs_b)
            assert pb == new_plain, '%s 回读明文不符' % tag
            eb, _, _ = parse_entries(pb)
            raw_b = next(r for (o, l, r) in eb if o == doff)
            assert raw_b == new_raw, '%s 回读目标条目 %s' % (tag, raw_b.hex(' '))
            assert dec(raw_b, codes, pairs) == NEW_ZH, '%s 回读译法不符' % tag
            touched.append((tag, base + off, stored))

    # ── 全局不变量 ──
    dd = open(dst, 'rb').read()
    assert len(dd) == len(sd), 'ISO 尺寸变了 %d -> %d' % (len(sd), len(dd))
    diff = [i for i in range(0, len(sd)) if sd[i] != dd[i]]
    assert diff, '没有任何字节变化'
    hit = {tag: 0 for tag, _o, _s in touched}
    for i in diff:
        inside = [tag for tag, o, s in touched if o <= i < o + s]
        assert inside, '差异字节 %#X 落在所有槽之外' % i
        for tag in inside:
            hit[tag] += 1
    for tag, o, s in touched:
        assert hit[tag] > 0, '%s 槽内无差异字节' % tag
        print('[scope] %s 槽 [%#X,%#X) 内差异 %d 字节' % (tag, o, o + s, hit[tag]))
    for lba, tag in ((MENU_LBA, 'MENU'), (GR_LBA, 'GR')):
        bb = lba * 2048
        assert sd[bb:bb + TAB_OFF] == dd[bb:bb + TAB_OFF], '%s 头部被改' % tag
        assert sd[bb + TAB_OFF:bb + TAB_OFF + TAB_STEP * 700] == \
            dd[bb + TAB_OFF:bb + TAB_OFF + TAB_STEP * 700], '%s 条目表被改' % tag
    print('[scope] 差异字节 %d 个, 全部落在 %d 个槽内 (MENU/GR 头部+条目表逐字节未动) ✓'
          % (len(diff), len(touched)))
    print('[filesz] ISO 尺寸 %d B 不变 ✓' % len(dd))
    print('[sha   ] dst sha256=%s' % hashlib.sha256(dd).hexdigest())
    print('[done  ] %s → %s' % (src, dst))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1], sys.argv[2])
