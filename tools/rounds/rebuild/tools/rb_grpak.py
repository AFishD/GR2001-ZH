# -*- coding: utf-8 -*-
r"""rb_grpak.py -- 只读：为 GR.IMG #3451 COMMON.PAK（原盘 400,659 B，K2 盘不可从转储取回）
找一个「旁证候选」并做决定性交叉校验：

* K2 转储本身覆盖了 GR#3451 的**前 9 个扇区**（PAK 头 + new_font_revised 头 + 若干像素），
  这段是 K2 的真字节 ⇒ 用来判定候选是否一致。
* 候选来源：其它汉化盘（GR_ZH113b / GR_F365 / SENT_* / TXT_02 等）在 **MENU#3 位置**
  （LBA 776460..776656）的扇区 —— 因为原盘里 MENU#3 与 GR#3451 逐字节相同，
  汉化链按惯例把同一份图集写两处。

用法: python rb_grpak.py --out <txt>
"""
import argparse
import glob
import hashlib
import io
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402

SEC = 2048
DUMPDIR = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'PCSX2', 'cdvd-dump')
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load_idx(path):
    n = os.path.getsize(path)
    with open(path, 'rb') as f:
        magic, bsz, total, zero = struct.unpack('<4sIII', f.read(16))
        if magic != b'BDV2':
            return None
        cnt, rem = divmod(n - 16, 4 + SEC)
        if rem:
            return None
        idx = {}
        for i in range(cnt):
            f.seek(16 + i * (4 + SEC))
            lba = struct.unpack('<I', f.read(4))[0]
            idx[lba] = 16 + i * (4 + SEC) + 4
    return idx


def read_at(path, idx, iso_off, size):
    """按 **字节偏移** 从转储读（摊平首尾两个扇区）。只读。"""
    l0 = iso_off // SEC
    l1 = (iso_off + size - 1) // SEC
    buf = bytearray()
    with open(path, 'rb') as f:
        for l in range(l0, l1 + 1):
            if l not in idx:
                return None, [x for x in range(l0, l1 + 1) if x not in idx]
            f.seek(idx[l])
            buf += f.read(SEC)
    a = iso_off - l0 * SEC
    return bytes(buf[a:a + size]), []


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)

    ORIG = os.path.join(REPO, 'third_party', 'orig', 'ps2',
                        "Tom Clancy's Ghost Recon (USA).iso")
    o = T.Iso(ORIG)
    men = zx_lib.entries(o, zx_lib.MENU_LBA)
    gr = zx_lib.entries(o, zx_lib.GR_LBA)
    e_m = [x for x in men if x['name'] == 'COMMON.PAK'][0]
    e_g = [x for x in gr if x['name'] == 'COMMON.PAK'][0]
    slot_m = bytes(o.read(e_m['iso_off'], e_m['stored']))
    slot_g = bytes(o.read(e_g['iso_off'], e_g['stored']))
    P('[原盘] MENU#%d COMMON.PAK off=0x%X stored=%d sha=%s' %
      (e_m['idx'], e_m['off'], e_m['stored'], sha(slot_m)[:16]))
    P('[原盘] GR#%d  COMMON.PAK off=0x%X stored=%d sha=%s' %
      (e_g['idx'], e_g['off'], e_g['stored'], sha(slot_g)[:16]))
    P('[原盘] MENU#3 与 GR#3451 逐字节相同 = %s' % (slot_m == slot_g))
    P('[原盘] MENU#3 记录: %s' % [(r[0], r[1], r[2], r[3], r[5]) for r in
                                  T.parse_pak_records(slot_m)])
    o.close()

    # K2 真字节：GR#3451 头若干扇区
    k2p = [d for d in glob.glob(os.path.join(DUMPDIR, '*.dump'))
           if 'GR_FA2400_K2' in os.path.basename(d)][0]
    kidx = load_idx(k2p)
    m_off, m_size = e_m['iso_off'], e_m['stored']
    g_off, g_size = e_g['iso_off'], e_g['stored']
    head_n = 9 * SEC
    k2head, miss = read_at(k2p, kidx, g_off, head_n)
    P('')
    P('[K2 转储] GR#3451 iso=0x%08X stored=%d ; 头部 %d B 是否齐 = %s (缺 %s)' %
      (g_off, g_size, head_n, k2head is not None, miss))
    if k2head:
        P('[K2 转储] 头部 sha=%s' % sha(k2head)[:16])
        P('[K2 转储] 与原盘 GR#3451 同段相同字节 %d / %d' %
          (sum(1 for x, y in zip(k2head, slot_g) if x == y), len(k2head)))
        P('[K2 转储] 头部前 32B: %s' % k2head[:32].hex())
        P('[K2 转储] 原盘同段前 32B: %s' % slot_g[:32].hex())
        # 记录表（只读头也能解析出计数/名字区）
        P('[K2 转储] 头部内记录表尝试: %s' %
          [(r[0], r[1], r[2], r[3], r[5]) for r in T.parse_pak_records(k2head)])

    # 候选：其它汉化盘在 MENU#3 槽的 PAK
    P('')
    P('[候选] 其它转储在 MENU#3 槽 (iso=0x%08X stored=%d) 的 PAK' % (m_off, m_size))
    cands = {}
    prov = {}
    for d in sorted(glob.glob(os.path.join(DUMPDIR, '*.dump'))):
        nm = os.path.basename(d)
        if 'GR_FA2400_K2' in nm:
            continue
        idx = load_idx(d)
        if not idx:
            continue
        pak, miss = read_at(d, idx, m_off, m_size)
        if pak is None:
            continue
        recs = T.parse_pak_records(pak)
        r = [x for x in recs if x[0] == 'new_font_revised']
        hdr = (r[0][1], r[0][2], r[0][3], r[0][5]) if r else None
        h = sha(pak)
        cands.setdefault(h, []).append((nm, hdr))
        prov.setdefault(h, d)
    P('[候选] 不同内容 %d 种:' % len(cands))
    for h, v in sorted(cands.items(), key=lambda kv: -len(kv[1])):
        P('   sha=%s  new_font_revised(psm,w,h,stored)=%s  提供者 %d 个: %s' %
          (h[:16], v[0][1], len(v), ', '.join(x[0] for x in v[:5])))

    if k2head:
        P('')
        P('[决定性] 候选 PAK 的头部 %d B 与 K2 转储 GR#3451 真字节比对:' % head_n)
        for h, v in sorted(cands.items(), key=lambda kv: -len(kv[1])):
            pak, _ = read_at(prov[h], load_idx(prov[h]), m_off, m_size)
            n = min(len(k2head), len(pak))
            same = sum(1 for i in range(n) if pak[i] == k2head[i])
            P('   sha=%-16s %-46s %6d / %d (%.2f%%)' %
              (h[:16], v[0][0], same, n, 100.0 * same / n))

    out = a.out or os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', 'temp', 'grpak.txt')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(LOG) + '\n')
    print('[out] %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
