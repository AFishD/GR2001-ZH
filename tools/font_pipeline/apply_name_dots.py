# -*- coding: utf-8 -*-
r"""apply_name_dots.py — ATR 人名加「·」分界点 (GR.IMG 内原地增长)

## 用途
  把角色档案 (.ATR) 的 <ActorName> 换成「理想标准译名 + 名·姓 分界点」。

## 输入
  tools/font_pipeline/data/name_dot_plan.csv
    表头: 文件/键,理想译名,加点后,段数,备注
    · 间隔号 = U+00B7 (对偶码 0xABC3, 已在码表中)
    · 逐行校验: 加点后.replace('·','') == 理想译名   (413/413 通过)

## 关键设计: **原地增长, 不搬移**
  · .ATR 条目在 GR.IMG 内紧密排列, 每条后有 11~15 B 全零间隙
  · 加一个「·」只增 2 字节 (两字节对偶码)
  · ⇒ 只要 `新长度 ≤ 原长度 + 后随余量` 就**原地写回**, 只更新 stored/real
  · 实测: 253 条中 240 条原地、13 条搬移, **净增长仅 177 B**

  对比早期做法 (把条目整体搬到空闲间隙) 需要 133 KB —— 本做法省 750 倍空间。

## 用法
  python apply_name_dots.py <src_iso> <dst_iso> [plan_csv]
"""
import csv
import io
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
from iso_tools import img_names, SEC, TAB_OFF, TAB_STEP  # noqa: E402

GR_LBA, GR_SIZE = 19175, 1550563328
CHARSET = os.path.join(HERE, 'data', 'charset_compiled_zh16.json')
PLAN = os.path.join(HERE, 'data', 'name_dot_plan.csv')
RE_NAME = re.compile(rb'<ActorName>(.*?)</ActorName>', re.S)


def load_cs():
    c = json.load(io.open(CHARSET, encoding='utf-8'))
    return dict(c['codes']), {k: list(v) for k, v in c['pair_of'].items()}


def enc(zh, codes, pairs):
    out = bytearray()
    for ch in zh:
        if ch in codes:
            out.append(codes[ch])
        elif ch in pairs:
            out += bytes(pairs[ch])
        else:
            out += ch.encode('latin-1')
    return bytes(out)


def dec(buf, codes, pairs):
    r1 = {v: k for k, v in codes.items()}
    r2 = {tuple(v): k for k, v in pairs.items()}
    o, i = [], 0
    while i < len(buf):
        if buf[i] < 0x80:
            o.append(chr(buf[i])); i += 1
        elif i + 1 < len(buf) and (buf[i], buf[i + 1]) in r2:
            o.append(r2[(buf[i], buf[i + 1])]); i += 2
        elif buf[i] in r1:
            o.append(r1[buf[i]]); i += 1
        else:
            o.append('{%02X}' % buf[i]); i += 1
    return ''.join(o)


def find_zero_gaps(d, base, ents):
    byoff = sorted((x[8], x[8] + x[6]) for x in ents if x[8])
    gaps = []
    for k in range(len(byoff) - 1):
        e1, o2 = byoff[k][1], byoff[k + 1][0]
        if o2 > e1 and not any(d[base + e1:base + o2]):
            gaps.append([e1, o2])
    end = max(x[8] + x[6] for x in ents if x[8])
    if GR_SIZE - end > 0 and not any(d[base + end:base + GR_SIZE]):
        gaps.append([end, GR_SIZE])
    return gaps


def main(src, dst, plan_path=PLAN):
    codes, pairs = load_cs()
    plan = {}
    for r in csv.DictReader(io.open(plan_path, encoding='utf-8')):
        k = (r.get('文件/键') or '').strip()
        v = (r.get('加点后') or '').strip()
        if k and v:
            plan[k] = v
            plan[k.replace('.ATR', '')] = v
    print('[plan] %d 键  (%s)' % (len(plan), os.path.basename(plan_path)))

    d = bytearray(open(src, 'rb').read())
    base = GR_LBA * SEC
    names = img_names(d, GR_LBA)
    ents = [list(struct.unpack_from('<12I', d, base + TAB_OFF + TAB_STEP * i))
            for i in range(len(names))]

    used = sorted((x[8], x[8] + x[6]) for x in ents if x[8])
    slack = {}
    for k in range(len(used) - 1):
        slack[used[k][1]] = used[k + 1][0] - used[k][1]
    e0 = max(x[8] + x[6] for x in ents if x[8])
    slack[e0] = GR_SIZE - e0

    gaps = find_zero_gaps(d, base, ents)
    gaps.sort(key=lambda g: g[1] - g[0])
    free = [list(g) for g in gaps]
    print('[space] 条目后余量 %d B, 全零间隙 %d 个 / %d B'
          % (sum(v for v in slack.values() if 0 < v < 4096),
             len(gaps), sum(b - a for a, b in gaps)))

    n_ip = n_mv = n_fail = n_skip = 0
    grow = 0
    for i, nm in enumerate(names):
        if not nm.upper().endswith('.ATR'):
            continue
        e = ents[i]
        stored, real, off = e[6], e[7], e[8]
        if stored != real or not stored:
            continue
        blob = bytes(d[base + off:base + off + stored])
        m = RE_NAME.search(blob)
        if not m:
            continue
        cur = dec(m.group(1).strip(), codes, pairs)
        want = plan.get(nm) or plan.get(nm.replace('.ATR', ''))
        if not want or want == cur:
            n_skip += 1
            continue
        try:
            nb = enc(want, codes, pairs)
        except Exception:
            n_skip += 1
            continue
        inner = m.end(1) - m.start(1)
        newlen = max(inner, len(nb))
        content = blob[:m.start(1)] + nb + b' ' * (newlen - len(nb)) + blob[m.end(1):]
        need = len(content)
        to = base + TAB_OFF + TAB_STEP * i
        if need <= stored + slack.get(off + stored, 0):
            d[base + off:base + off + need] = content
            struct.pack_into('<I', d, to + 24, need)
            struct.pack_into('<I', d, to + 28, need)
            grow += need - stored
            n_ip += 1
            continue
        placed = None
        for gi, (a, b) in enumerate(free):
            pos = ((a + 3) // 4) * 4
            if pos + need <= b:
                placed = (gi, pos)
                break
        if placed is None:
            n_fail += 1
            print('  [FAIL] %-26s 需 %d' % (nm[:26], need))
            continue
        gi, pos = placed
        d[base + pos:base + pos + need] = content
        free[gi][0] = pos + need
        struct.pack_into('<I', d, to + 32, pos)
        struct.pack_into('<I', d, to + 24, need)
        struct.pack_into('<I', d, to + 28, need)
        n_mv += 1

    open(dst, 'wb').write(bytes(d))
    print('[done] 原地 %d, 搬移 %d, 跳过 %d, 失败 %d, 净增长 %d B'
          % (n_ip, n_mv, n_skip, n_fail, grow))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1], sys.argv[2],
         sys.argv[3] if len(sys.argv) > 3 else PLAN)
