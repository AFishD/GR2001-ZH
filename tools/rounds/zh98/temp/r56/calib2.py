# -*- coding: utf-8 -*-
r"""round56 侦察 ⑥: 全容器 "真文本" 判别标定 (pair/single 组成 + 多样性)。

对每个 IMG 条目 (LZO 展开) 与全盘原始段: 找最像文本的干净段, 算:
  n_cjk, distinct_cjk, pair_ratio (汉字里靠**对偶码**解出的比例), hi_maxrep, maxcjk
再按判别式打分排序, 看除真文本容器外还有谁会被选中。
"""
import io
import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                        # noqa: E402

cs = tcslib.Charset()
LEAD_LO, LEAD_HI = tcslib.LEAD_LO, tcslib.LEAD_HI
BAD = set(range(0x00, 0x20)) - {9, 10, 13}
BAD |= set(range(0x7F, 0xA0))

print('charset: 单字节码 %d 个; 其中非 ASCII: %s'
      % (len(cs.enc_single), ''.join(sorted(c for c in cs.enc_single if ord(c) > 0x7F))[:200]))
print('   非 ASCII 单字节码: %s'
      % ' '.join('%02X=%s' % (cs.enc_single[c], c)
                 for c in sorted((c for c in cs.enc_single if ord(c) > 0x7F),
                                 key=lambda c: cs.enc_single[c])))


def parse_units(buf):
    """greedy 解析 → [(byte_off, nbytes, char)] (遇到解不出的字节就断)。"""
    out = []
    i = 0
    n = len(buf)
    pair_of, codes = cs.pair_of, cs.codes
    while i < n:
        v = buf[i]
        if v < 0x80:
            out.append((i, 1, chr(v))); i += 1
        elif LEAD_LO <= v < LEAD_HI and i + 1 < n and (v, buf[i + 1]) in pair_of:
            out.append((i, 2, pair_of[(v, buf[i + 1])])); i += 2
        elif v in codes:
            out.append((i, 1, codes[v])); i += 1
        else:
            break
    return out


def best_run_stats(blob):
    """切控制字节 → 逐段 greedy 解析 → 找最像文本的连续汉字段。"""
    best = None
    n = len(blob)
    i = 0
    while i < n:
        if blob[i] in BAD:
            i += 1
            continue
        j = i
        while j < n and blob[j] not in BAD:
            j += 1
        seg = blob[i:j]
        i = j
        if len(seg) < 4:
            continue
        units = parse_units(seg)
        if not units:
            continue
        # 把解析结果按"汉字连续段"切 (非汉字断开)
        cur = []
        groups = []
        for u in units:
            if '\u4e00' <= u[2] <= '\u9fff':
                cur.append(u)
            else:
                if len(cur) >= 4:
                    groups.append(cur)
                cur = []
        if len(cur) >= 4:
            groups.append(cur)
        for g in groups:
            st = dict(off=blob_off_base + g[0][0], n_cjk=len(g),
                      distinct_cjk=len(set(u[2] for u in g)),
                      pair_ratio=sum(1 for u in g if u[1] == 2) / len(g),
                      maxcjk=len(g),
                      text=''.join(u[2] for u in g)[:60])
            if best is None or (st['n_cjk'], st['distinct_cjk']) > (best['n_cjk'],
                                                                    best['distinct_cjk']):
                best = st
    return best


def texty(st):
    """判别式 (待标定): 像真人写的中文吗?"""
    if not st:
        return False
    return (st['maxcjk'] >= 6 and st['n_cjk'] >= 16 and st['distinct_cjk'] >= 10
            and st['pair_ratio'] >= 0.5)


iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso'))
res = []
for tag, lba in (('MENU.IMG', 776286), ('GR.IMG', 19175)):
    for idx in range(4096):
        try:
            e = iso.img_entry(lba, idx)
        except Exception:                                            # noqa: BLE001
            break
        if e['stored'] <= 0 or e['stored'] > 0x7FFFFFFF:
            if idx == 0:
                continue
            break
        raw = iso.read(e['iso_off'], e['stored'])
        subs = tcslib.lzo_subs(raw)
        blob = b''.join(s[0] for s in subs) if subs else raw
        blob_off_base = 0
        st = best_run_stats(blob)
        if st:
            st.update(img=tag, idx=idx, name=e['name'], mode='lzo' if subs else 'raw',
                      texty=texty(st))
            res.append(st)
iso.close()
res.sort(key=lambda s: (-int(s['texty']), -s['n_cjk'], -s['distinct_cjk']))
print('\n=== texty=True 的容器 (%d 个) ===' % sum(1 for s in res if s['texty']))
for s in res:
    if s['texty']:
        print('  %-9s #%-5d %-28s n_cjk=%-5d dist=%-4d pair=%.2f maxcjk=%-4d %r'
              % (s['img'], s['idx'], s['name'], s['n_cjk'], s['distinct_cjk'],
                 s['pair_ratio'], s['maxcjk'], s['text'][:40]))
print('\n=== 最像文本但被判 False 的 top 15 (人工复核用) ===')
for s in res[:15]:
    if not s['texty']:
        print('  %-9s #%-5d %-28s n_cjk=%-5d dist=%-4d pair=%.2f maxcjk=%-4d %r'
              % (s['img'], s['idx'], s['name'], s['n_cjk'], s['distinct_cjk'],
                 s['pair_ratio'], s['maxcjk'], s['text'][:40]))
io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'calib2.json'),
        'w', encoding='utf-8', newline='\n').write(
    json.dumps(res[:400], ensure_ascii=False, indent=1) + '\n')
