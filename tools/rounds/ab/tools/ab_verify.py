# -*- coding: utf-8 -*-
r"""ab_verify.py — 成品盘自检 (只读成品, 不写任何盘)

  ① 5 张盘 sha256 / 尺寸 与 meta.json 一致
  ② AB_01 / AB_02 在成品盘上**反汇编回读**
  ③ AB_03: 从成品盘解 FONT.RES → 内部头 real=7222 / 明文 7222 B / 前 5942 B 与基底逐字节相同
  ④ AB_04: 从成品盘读 IMG 条目表 → FONT.RES real=5942
  ⑤ AB_00: 与基底 sha256 相同；基底 sha256 未变（= 源盘一字未改的旁证）
"""
import hashlib
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ab_lib as A     # noqa: E402
import nh_lib as N     # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
OUT = []
W = OUT.append
OK = True


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        while True:
            b = f.read(1 << 22)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    global OK
    names = ['AB_00_base', 'AB_01_sp222', 'AB_02_sp221_revert',
             'AB_03_fontres_real7k', 'AB_04_fontres_real5942']
    W('# GR_AB 成品盘自检\n')
    W('| 盘 | 尺寸 | sha256 | meta 一致 | 差异 run / B |')
    W('|---|---|---|---|---|')
    for n in names:
        p = os.path.join(A.OUT, n + '.iso')
        m = json.load(open(os.path.join(A.OUT, n + '.meta.json'), encoding='utf-8'))
        s = sha(p)
        good = (s == m['sha256'] and os.path.getsize(p) == m['size'])
        OK &= good
        W('| `%s.iso` | %d | `%s` | %s | %d / %d |'
          % (n, os.path.getsize(p), s, '✅' if good else '❌',
             len(m['byte_diff_runs']), m['byte_diff_total']))
    W('')
    W('基底 `GR_ZH113b.iso` sha256 = `%s`' % sha(A.BASE_ZH))
    W('')

    # ② 指令回读
    off = A.va2iso(0x219DAC)
    W('## ② AB_00/01/02 站点反汇编回读 (VA 0x219DAC, ISO 0x%X)\n' % off)
    W('```')
    for n in ('AB_00_base', 'AB_01_sp222', 'AB_02_sp221_revert'):
        with open(os.path.join(A.OUT, n + '.iso'), 'rb') as f:
            f.seek(off)
            b = f.read(8)
        w0, w1 = struct.unpack('<I', b[:4])[0], struct.unpack('<I', b[4:])[0]
        W('%-22s 0x%08X %-22s | 0x%08X %s'
          % (n, w0, A.dis1(w0, 0x219DAC), w1, A.dis1(w1, 0x219DB0)))
    W('```')
    with open(os.path.join(A.OUT, 'AB_01_sp222.iso'), 'rb') as f:
        f.seek(off)
        w = struct.unpack('<I', f.read(4))[0]
    if w != 0x93A200DE:
        OK = False
        W('\n❌ AB_01 不是 0x93A200DE')
    with open(os.path.join(A.OUT, 'AB_02_sp221_revert.iso'), 'rb') as f:
        f.seek(off)
        b = f.read(8)
    if b != bytes.fromhex('0000000001001026'):
        OK = False
        W('\n❌ AB_02 不是英文原盘字节')
    W('')

    # ③ AB_03
    W('## ③ AB_03 FONT.RES 回读（内部头 / 明文 / 前缀一致性）\n')
    W('| IMG | 条目 stored/real | 内部 comp/real | 明文长度 | 前 5,942 B == 基底 | 尾部 1,280 B 全零 |')
    W('|---|---|---|---|---|---|')
    base_plain = {}
    iso0 = N.Iso(A.BASE_ZH)
    for imgk in ('MENU', 'GR'):
        e, base, raw, ents = A.fontres_entry(iso0, A.IMG[imgk])
        pl, comp, real, se = A.decompress_fontres(raw)
        base_plain[imgk] = (pl, e['idx'], e['off'])
    iso0.close()
    iso3 = N.Iso(os.path.join(A.OUT, 'AB_03_fontres_real7k.iso'))
    for imgk in ('MENU', 'GR'):
        e, base, raw, ents = A.fontres_entry(iso3, A.IMG[imgk])
        pl, comp, real, se = A.decompress_fontres(raw)
        bpl, bidx, boff = base_plain[imgk]
        pre_ok = pl[:len(bpl)] == bpl
        tail_ok = all(x == 0 for x in pl[len(bpl):]) and len(pl) == 7222
        OK &= (real == 7222 and pre_ok and tail_ok and e['real'] == 7222
               and e['stored'] == 4421 and e['off'] == boff and e['idx'] == bidx)
        W('| %s | %d / %d | %d / **%d** | %d | %s | %s |'
          % (imgk, e['stored'], e['real'], comp, real, len(pl),
             '✅' if pre_ok else '❌', '✅' if tail_ok else '❌'))
    iso3.close()
    W('')

    # ④ AB_04
    W('## ④ AB_04 IMG 条目表回读（FONT.RES real）\n')
    W('| IMG | 条目 # | 基底 real | AB_04 real | 内部头 real |')
    W('|---|---|---|---|---|')
    iso4 = N.Iso(os.path.join(A.OUT, 'AB_04_fontres_real5942.iso'))
    for imgk in ('MENU', 'GR'):
        e, base, raw, ents = A.fontres_entry(iso4, A.IMG[imgk])
        pl, comp, real, se = A.decompress_fontres(raw)
        bpl, bidx, boff = base_plain[imgk]
        good = (e['real'] == 5942 and real == 5942 and e['stored'] == 4421
                and e['off'] == boff and e['idx'] == bidx and pl == bpl)
        OK &= good
        W('| %s | %d | 7222 | **%d** | %d | %s'
          % (imgk, e['idx'], e['real'], real, '✅' if good else '❌'))
    iso4.close()
    W('')

    # ⑤ AB_00
    W('## ⑤ AB_00 == 基底 ?\n')
    same = sha(os.path.join(A.OUT, 'AB_00_base.iso')) == sha(A.BASE_ZH)
    OK &= same
    W('`AB_00_base.iso` sha256 == `GR_ZH113b.iso` sha256 : **%s**\n' % ('✅ 是' if same else '❌ 否'))
    W('\n## 总判定: **%s**\n' % ('✅ 全部通过' if OK else '❌ 有不通过项'))
    txt = '\n'.join(OUT)
    open(os.path.join(A.EVID, 'VERIFY_BUILDS.md'), 'w', encoding='utf-8').write(txt)
    print(txt)


if __name__ == '__main__':
    main()
