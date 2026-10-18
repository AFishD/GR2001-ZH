# -*- coding: utf-8 -*-
r"""s3_recon.py (round44 实验) — ① 按 GIF 封包重建"引擎真正看到的图集"
                             ② 用 TTF 模板全图穷举定位, 判定字形到底在哪

背景 (本轮查实): COMMON.PAK 的 new_font_revised 像素容器 = **GIF 封包流**, 不是裸图:
  原版 : [16B GIFTAG][0x40000 像素]                        (单包, 无 A+D => 行 0 起)
  现役 : 8 段, 每段 [PT tag 16B][A+D TRXPOS 16B][IMAGE tag 16B][数据]
         写入侧 (patch_zh64/65/68/93) 一律按 segs[k] + (ay - SEG_Y[k]) * 512 定位
         => **引擎口径 = 段内行 (payload 行)**
  => dump_font.atlas_gray() 把整个容器当 1024x512 裸图逐行读 => 包头被当像素 + 每段错位。

本脚本只读。产物写 temp/r44/。
"""
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_repo(p):
    while True:
        if os.path.isfile(os.path.join(p, 'tools', 'text_csv', 'tcslib.py')):
            return p
        q = os.path.dirname(p)
        if q == p:
            raise SystemExit('!! 找不到仓库根')
        p = q


REPO = find_repo(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np                                                # noqa: E402
from PIL import Image, ImageFont, ImageDraw                       # noqa: E402
import tcslib                                                     # noqa: E402
import dump_font                                                  # noqa: E402

FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
FALLBACK16 = set(u'\u00ae\u00b5\u8e5a')          # TTF 缺字的 3 个回退字
ISOS = dict(
    EN_ORIG=os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso'),
    ZH93=os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso'),
)
LOG = []


def log(s):
    print(s)
    LOG.append(s)


# ───────────────────────── GIF 封包 → 引擎看到的行 ─────────────────────────

def parse_packets(blob):
    """走一遍像素容器的 GIF 语法。返回 (segs, noop_off)。不认识的包直接抛。"""
    segs, o, trx = [], 0, None
    while o + 16 <= len(blob):
        w0, w1 = struct.unpack_from('<II', blob, o)
        nloop, eop, flg = w0 & 0x7FFF, (w0 >> 15) & 1, (w1 >> 26) & 3
        nreg = (((w1 >> 28) - 1) & 0xF) + 1
        ln = nloop * (16 * nreg if flg in (0, 1) else 16)
        if flg in (0, 1):
            if nloop == 0:
                return segs, o
            if nloop == 1 and nreg == 1:
                trx = struct.unpack_from('<I', blob, o + 20)[0]
                o += 16 + ln
                continue
            raise SystemExit('!! 不认识的 PT 包 nloop=%d nreg=%d @0x%X' % (nloop, nreg, o))
        segs.append(dict(pkt=o, y=trx, data=o + 16, ln=ln, nloop=nloop))
        o += 16 + ln
        if eop and nloop == 0:
            return segs, o
    return segs, o


def payload_from_packets(blob, w, h, stride=None, fill=0x11):
    """按封包把数据搬到引擎看到的行; 返回 (payload bytes, segs, meta)。

    stride = 每行字节数 (4bpp: w//2; 8bpp: w)。trxpos 缺省 (原版单包无 A+D) 视为行 0。
    """
    if stride is None:
        stride = w // 2
    segs, end = parse_packets(blob)
    out = bytearray(bytes([fill]) * (stride * h))
    leftover = 0
    for s in segs:
        if s['y'] is None:
            s['y'] = 0
        nr = s['ln'] // stride
        for r in range(nr):
            out[(s['y'] + r) * stride: (s['y'] + r) * stride + stride] = \
                blob[s['data'] + r * stride: s['data'] + (r + 1) * stride]
        if s['ln'] % stride:
            leftover = s['ln'] % stride
            d = (s['y'] + nr) * stride
            out[d:d + leftover] = blob[s['data'] + nr * stride: s['data'] + nr * stride + leftover]
    return bytes(out), segs, dict(noop_off=end, leftover=leftover)


def ink4(buf, w, h):
    """4bpp -> bool 图 (True = 墨 texel)。偶 x = 低 nibble。"""
    a = np.frombuffer(buf[: (w // 2) * h], dtype=np.uint8).reshape(h, w // 2)
    out = np.empty((h, w), dtype=bool)
    out[:, 0::2] = (a & 0x0F) == 0
    out[:, 1::2] = (a >> 4) == 0
    return out


def ink8(buf, w, h):
    """8bpp -> bool 图 (True = 墨)。原版字库: 0 = 墨, 0x1f = 底 (<24 与 patch_zh64 同口径)。"""
    a = np.frombuffer(buf[:w * h], dtype=np.uint8).reshape(h, w)
    return a < 24


def ink_gray(gray, w, h):
    """dump 口径的灰度缓冲 (0=墨 255=空) -> bool 图。"""
    return np.frombuffer(gray[:w * h], dtype=np.uint8).reshape(h, w) == 0


# ───────────────────────── TTF 模板 + 穷举定位 ─────────────────────────

_FONT = None


def render16(ch):
    """与 gen_font16.render16 同款: 32x32 画布 (8,8) 起, 取 [8:24,8:24], <128 = 墨。"""
    global _FONT
    if _FONT is None:
        _FONT = ImageFont.truetype(FZ16, 16)
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=_FONT, fill=0)
    return (np.asarray(img)[8:24, 8:24] < 128)


def best_match(inkimg, tpl, topk=4):
    """全图穷举: [(mismatch, y, x), ...] 升序。mismatch = 逐像素 XOR 计数 (精确)。"""
    H, W = inkimg.shape
    th, tw = tpl.shape
    oh, ow = H - th + 1, W - tw + 1
    f = inkimg.astype(np.int32)
    C = np.zeros((oh, ow), np.int32)
    for i in range(th):
        for j in range(tw):
            if tpl[i, j]:
                C += f[i:i + oh, j:j + ow]
    ii = np.zeros((H + 1, W + 1), np.int32)
    ii[1:, 1:] = np.cumsum(np.cumsum(f, 0), 1)
    S = ii[th:, tw:] - ii[:-th, tw:] - ii[th:, :-tw] + ii[:-th, :-tw]
    mism = int(tpl.sum()) + S - 2 * C
    flat = np.argsort(mism, axis=None)[:400]
    out = []
    for k in flat:
        y, x = divmod(int(k), ow)
        out.append((int(mism[y, x]), y, x))
        if len(out) >= topk:
            break
    return out


# ───────────────────────── 主流程 ─────────────────────────

def analyze(tag, iso_path, chars):
    log('=' * 78)
    log('[%s] %s' % (tag, os.path.relpath(iso_path, REPO)))
    font = dump_font.load_font(iso_path)
    at = font['atlas']
    w, h, psm = at['w'], at['h'], at['psm']
    is4 = (psm == 0x14)
    stride = w // 2 if is4 else w
    blob = at['pak'][at['px_off']:at['px_off'] + at['px_size']]
    log('[%s] 记录: psm=0x%02X %dx%d clut=%d px_size=0x%X px_off=0x%X'
        % (tag, psm, w, h, at['clut'], at['px_size'], at['px_off']))
    log('[%s] 像素容器前 64 字节: %s' % (tag, blob[:64].hex(' ')))

    segs, _end = parse_packets(blob)
    log('[%s] GIF 封包: %d 个数据段' % (tag, len(segs)))
    for i, s in enumerate(segs):
        log('[%s]   #%d PT@0x%-6X TRXPOS.y=%-4s IMAGE@0x%-6X NLOOP=%-6d 数据 %6d B = %d 行'
            % (tag, i, s['pkt'], s['y'], s['data'], s['nloop'], s['ln'], s['ln'] // stride))

    payload, segs, meta = payload_from_packets(blob, w, h, stride=stride,
                                              fill=(0x11 if is4 else 0x1f))
    gray_dump = dump_font.atlas_gray(at)                      # 现役 dump 口径 (有 bug)
    ink_pay = ink4(payload, w, h) if is4 else ink8(payload, w, h)
    ink_dmp = ink_gray(gray_dump, w, h)

    rp, rd = ink_pay.sum(axis=1), ink_dmp.sum(axis=1)
    log('[%s] 逐行墨点 (前 20 行)  payload / dump:' % tag)
    log('        y   payload    dump')
    for y in range(20):
        log('      %4d %8d %7d' % (y, rp[y], rd[y]))
    log('[%s] payload 行 0/1 墨点 = %d / %d;  dump 行 0 墨点 = %d'
        % (tag, rp[0], rp[1], rd[0]))
    log('[%s] payload 总墨点 %d; dump 总墨点 %d' % (tag, int(rp.sum()), int(rd.sum())))

    log('[%s] 各段包头 (48B) 落在 dump 的哪一行:' % tag)
    for i, s in enumerate(segs):
        row_d = s['pkt'] // stride
        col_d = (s['pkt'] % stride) * (2 if is4 else 1)
        log('[%s]   段#%d IMAGE 包@blob 0x%-6X => dump 行 %-4d x=%-4d (该行墨点 %s); 数据首行 = payload 行 %s'
            % (tag, i, s['pkt'], row_d, col_d,
               (rd[row_d] if row_d < h else 'n/a'), s['y']))

    for k, s in enumerate(segs):
        sh = (-(s['pkt'] - s['y'] * stride)) % stride
        log('[%s]   段#%d: dump 里这一段像素相对引擎位置 水平错位 %d 字节 = %d texel = %d 格'
            % (tag, k, sh, sh * (2 if is4 else 1), sh * (2 if is4 else 1) // 16))

    def period(seq, name):
        seq = seq[:450].astype(np.float64)
        seq = seq - seq.mean()
        d = float((seq * seq).sum())
        ac = [float((seq[:-L] * seq[L:]).sum() / d) if d else 0.0 for L in range(1, 33)]
        top = sorted(range(1, 33), key=lambda L: -ac[L - 1])[:5]
        log('[%s] %s 行墨点自相关 top5 周期: %s'
            % (tag, name, ', '.join('滞后%d行=%.3f' % (L, ac[L - 1]) for L in top)))
    period(rp, 'payload')
    period(rd, 'dump   ')

    log('[%s] TTF 模板全图穷举 (FZ16 16px, %d 个字)%s:'
        % (tag, len(chars),
           '  ← **反面对照**: 原版盘没有汉字, 预期全部无命中' if psm != 0x14 else ''))
    log('      字   slot  row col | 引擎式格(payload) | payload 命中            | dump 命中')
    res = []
    for ch, slot in chars:
        tpl = render16(ch)
        bp, bd = best_match(ink_pay, tpl), best_match(ink_dmp, tpl)
        row, col = slot // tcslib.NCOL, slot % tcslib.NCOL
        ex, ey = tcslib.atlas_cell_xy_engine(slot)
        m, y, x = bp[0]
        md, yd, xd = bd[0]
        ph_pay, ph_dmp = (x // 16 - col) % 64, (xd // 16 - col) % 64
        res.append(dict(char=ch, slot=slot, row=row, col=col, engine_x=ex, engine_y=ey,
                        pay_mism=m, pay_x=x, pay_y=y, pay_phase=ph_pay,
                        dump_mism=md, dump_x=xd, dump_y=yd, dump_phase=ph_dmp,
                        tpl_ink=int(tpl.sum())))
        log('[%s]  %s %5d %4d %3d | (%4d,%3d)          | (%4d,%3d) err=%-3d phi=%2d | (%4d,%3d) err=%-3d phi=%2d'
            % (tag, ch, slot, row, col, ex, ey, x, y, m, ph_pay, xd, yd, md, ph_dmp))

    by_row = {}
    for r in res:
        if r['pay_mism'] <= 6:
            by_row.setdefault(r['row'], []).append(r['pay_phase'])
    log('[%s] payload 低误差命中按行聚合的相位 (相位 = 字形实际列 - col):' % tag)
    for row in sorted(by_row):
        log('[%s]   row %2d: 相位 %s (n=%d)' % (tag, row, sorted(set(by_row[row])), len(by_row[row])))
    log('[%s] payload 逐像素 0 误差命中: %d/%d; dump 0 误差命中: %d/%d'
        % (tag, sum(1 for r in res if r['pay_mism'] == 0), len(res),
           sum(1 for r in res if r['dump_mism'] == 0), len(res)))
    return dict(tag=tag, psm=psm, w=w, h=h, px_off=at['px_off'], px_size=at['px_size'],
                blob_head64=blob[:64].hex(),
                segs=[dict(pkt=s['pkt'], y=s['y'], data=s['data'], ln=s['ln'], nloop=s['nloop'])
                      for s in segs],
                meta=meta, ink_payload=int(rp.sum()), ink_dump=int(rd.sum()),
                row_ink_payload=[int(v) for v in rp[:64]], row_ink_dump=[int(v) for v in rd[:64]],
                matches=res, payload_phase_by_row=dict((str(k), sorted(set(v)))
                                                       for k, v in by_row.items()))


def main():
    cs = tcslib.Charset()
    pairs = sorted(cs.enc_pair.items(), key=lambda kv: tcslib.pair_slot(*kv[1]))
    chars, per_row = [], {}
    for ch, (b1, b2) in pairs:
        if ch in FALLBACK16:
            continue
        slot = tcslib.pair_slot(b1, b2)
        row = slot // tcslib.NCOL
        if per_row.get(row, 0) >= 2:
            continue
        per_row[row] = per_row.get(row, 0) + 1
        chars.append((ch, slot))
    log('[主] TTF 模板抽样 %d 个字, 覆盖 %d 个网格行' % (len(chars), len(per_row)))

    out = []
    for tag, p in ISOS.items():
        if os.path.isfile(p):
            out.append(analyze(tag, p, chars))
    jp = os.path.join(HERE, 's3_recon.json')
    with io.open(jp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    for tag, p in ISOS.items():
        font = dump_font.load_font(p)
        at = font['atlas']
        w, h = at['w'], at['h']
        is4 = (at['psm'] == 0x14)
        stride = w // 2 if is4 else w
        blob = at['pak'][at['px_off']:at['px_off'] + at['px_size']]
        payload, _s, _m = payload_from_packets(blob, w, h, stride=stride,
                                              fill=(0x11 if is4 else 0x1f))
        i_pay = ink4(payload, w, h) if is4 else ink8(payload, w, h)
        i_dmp = ink_gray(dump_font.atlas_gray(at), w, h)
        for nm, arr in (('payload', i_pay), ('dump', i_dmp)):
            im = Image.fromarray(np.where(arr, 0, 255).astype(np.uint8), 'L')
            im.crop((0, 0, 256, 64)).resize((256 * 4, 64 * 4), Image.NEAREST).save(
                os.path.join(HERE, 'c_%s_%s_top256x64_z4.png' % (tag, nm)))
            im.save(os.path.join(HERE, '%s_%s_1x.png' % (tag, nm)))
        log('[图] %s: %s_payload_1x.png / %s_dump_1x.png / c_%s_{payload,dump}_top256x64_z4.png'
            % (tag, tag, tag, tag))
    with io.open(os.path.join(HERE, 's3_recon.log'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    log('[s3] JSON -> %s' % os.path.relpath(jp, REPO))
    return 0


if __name__ == '__main__':
    sys.exit(main())
