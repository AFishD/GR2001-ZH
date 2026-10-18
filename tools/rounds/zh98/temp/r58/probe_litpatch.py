# -*- coding: utf-8 -*-
r"""r58 探针9: 登记容器"改完还能不能塞回槽"—— ① 重压是否够小; ② 不够时改动的输出字节在
LZO 流里是不是**字面量**(可直接原位改, 帧长不变)。

自带一个带"来源标注"的 LZO1X 解码器 (结构逐句抄 tools/gr_tools/lz77_decode.py 的
lzo1x_decompress, 只多记一份 out[i] 的来源: ('lit', payload_off) / ('match', -1))。
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

G0P = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r46', 'charset_before_repack.json')
G1P = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r56', 'charset_before_r56.json')
G2P = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')


def lzo1x_decompress_trace(payload, out_size=None):
    """返回 (out, origin, err, ip); origin[i] = payload 内的**字面量**偏移, 或 -1 (匹配拷贝)。"""
    data, ip, n = payload, 0, len(payload)
    out, origin = bytearray(), []

    def GETB():
        nonlocal ip
        if ip >= n:
            raise IndexError('input depleted at ip=%d' % ip)
        b = data[ip]
        ip += 1
        return b

    def emit_lit(cnt):
        for k in range(cnt):
            out.append(data[ip + k])
            origin.append(ip + k)
        return cnt

    def emit_match(cnt, back):
        o = len(out)
        for i in range(cnt):
            out.append(out[o - back + i])
            origin.append(-1)

    state, err = 0, None
    try:
        x = GETB()
        if x > 17:
            ip += emit_lit(x - 17)
            x = GETB()
        while err is None:
            if out_size is not None and len(out) >= out_size:
                break
            if x > 15:
                if x > 63:
                    cnt = (x >> 5) - 1
                    back = (GETB() << 3) + ((x >> 2) & 7) + 1
                elif x > 31:
                    cnt = x & 31
                    if cnt == 0:
                        while True:
                            x = GETB()
                            if x:
                                cnt += 31 + x
                                break
                            cnt += 255
                    x = GETB()
                    back = (GETB() << 6) + (x >> 2) + 1
                else:
                    cnt = x & 7
                    if cnt == 0:
                        while True:
                            x = GETB()
                            if x:
                                cnt += 7 + x
                                break
                            cnt += 255
                    back = (1 << 14) + ((x & 8) << 11)
                    x = GETB()
                    back += (GETB() << 6) + (x >> 2)
                    if back == (1 << 14):
                        break
            elif not state:
                cnt = x & 15
                if cnt == 0:
                    while True:
                        x = GETB()
                        if x:
                            cnt += 15 + x
                            break
                        cnt += 255
                ip += emit_lit(cnt + 3)
                x = GETB()
                if x > 15:
                    continue
                cnt = 1
                back = (1 << 11) + (GETB() << 2) + (x >> 2) + 1
            else:
                cnt = 0
                back = (GETB() << 2) + (x >> 2) + 1
            o = len(out)
            if back > o:
                err = 'INVALID BACK %d at out=%d ip=%d' % (back, o, ip - 1)
                break
            emit_match(cnt + 2, back)
            state = cnt = x & 3
            ip += emit_lit(cnt)
            if out_size is not None and len(out) >= out_size:
                break
            if ip >= n:
                break
            x = GETB()
    except IndexError as e:
        err = str(e)
    return bytes(out), origin, err, ip


def remap_all(blob, src, dst):
    text, mp = src.decode(blob)
    n = len(blob)
    out = bytearray(blob)
    chg = []
    nfail = nlen = 0
    for i, ch in enumerate(text):
        a = mp[i]
        b = mp[i + 1] if i + 1 < len(text) else n
        try:
            nb = dst.encode_strict(ch)
        except tcslib.CharsetError:
            nfail += 1
            continue
        if len(nb) != b - a:
            nlen += 1
            continue
        if nb != blob[a:b]:
            out[a:b] = nb
            chg.append((a, b, blob[a:b], nb, ch))
    return bytes(out), chg, nfail, nlen


def payload_fit(slot, new_blob, sizes, orig_sizes):
    """逐子流重压, 返回 (总帧长, 每个变了子流的 (idx, 原长, 新长))。"""
    frame, reps = 0, []
    q = 0
    for k, S in enumerate(sizes):
        c = new_blob[q:q + S]
        q += S
        cc = tcslib.lzo_compress(c, level=7, use_m1=True, use_m4=True)
        if len(cc) != orig_sizes[k]:
            reps.append((k, orig_sizes[k], len(cc)))
        frame += 8 + len(cc)
    return frame, reps


iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH107', 'GR_ZH107.iso'))
G0, G1, G2 = (tcslib.Charset(p) for p in (G0P, G1P, G2P))
TARGETS = [('MENU.IMG', 30), ('MENU.IMG', 26), ('GR.IMG', 900), ('MENU.IMG', 27),
           ('GR.IMG', 904)]
print('%-32s %-7s %-9s %-9s %-8s %s' % ('container', 'src', '改字节', '重压帧', '槽', '字面量?'))
for (tag, idx) in TARGETS:
    lba = FC.MENU_LBA if tag == 'MENU.IMG' else FC.GR_LBA
    s = FC.Slot(iso, tag, lba, idx)
    for gn, src in (('G0', G0), ('G1', G1)):
        if gn == 'G1' and (tag, idx) in (('MENU.IMG', 30),):
            continue
        new, chg, nfail, nlen = remap_all(s.blob, src, G2)
        if not chg:
            print('%-32s %-7s %-9d %s' % ('%s#%d %s' % (tag, idx, s.name), gn, 0, '(0 改动)'))
            continue
        osz = [len(tcslib.lzo_compress(s.blob[sum(s.sizes[:k]):sum(s.sizes[:k]) + S],
                                       level=7, use_m1=True, use_m4=True))
               for k, S in enumerate(s.sizes)]
        frame, reps = payload_fit(s.slot, new, s.sizes, osz)
        # 逐子流: 改动的输出偏移落在哪个子流, 该子流的字面量可改性
        base = 0
        ok_lit, bad = True, []
        for k, S in enumerate(s.sizes):
            sub_chg = [(a - base, b - base, ob, nb, ch) for (a, b, ob, nb, ch) in chg
                       if base <= a < base + S]
            base += S
            if not sub_chg:
                continue
            pay = s.raws[k][8:]
            out, origin, err, ip1 = lzo1x_decompress_trace(pay, out_size=S)
            if err or out != s.blob[sum(s.sizes[:k]):sum(s.sizes[:k]) + S]:
                ok_lit = False
                bad.append('sub%d 解码不一致 (%s)' % (k, err))
                continue
            for (a, b, ob, nb, ch) in sub_chg:
                for j in range(a, b):
                    if origin[j] < 0:
                        ok_lit = False
                        bad.append('sub%d out@%d (%r) 是匹配拷贝' % (k, j, ch))
        print('%-32s %-7s %-9d %-9d %-8d %s%s'
              % ('%s#%d %s' % (tag, idx, s.name), gn,
                 sum(b - a for (a, b, _o, _n, _c) in chg), frame, s.slot,
                 '全部字面量 ✓' if ok_lit else ('✗ ' + '; '.join(bad[:2])),
                 '  复压: %s' % (reps or '无变化')))
iso.close()
