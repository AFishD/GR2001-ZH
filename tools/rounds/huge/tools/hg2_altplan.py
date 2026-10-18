# -*- coding: utf-8 -*-
r"""hg2_altplan.py — 只读: 为「方案 B（用基底自己的 default 面补全 huge 面）」取证与备料。

产出:
  evidence/hg2_altplan.txt
  evidence/planB_huge_rec96_223_MENU.bin  (1,280 B)
  evidence/planB_huge_rec96_223_GR.bin    (1,280 B)
  evidence/planB_meta.json
"""
import hashlib
import json
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hg_lib as H      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def main():
    lines = []
    W = lines.append
    meta = {}
    for tag in ('EN_ORIG', 'ZH113b'):
        for imgk in ('MENU', 'GR'):
            d = H.fontres(tag, imgk)
            fs = {f['name']: f for f in d['faces']}
            W('=' * 100)
            W('%s/%s' % (tag, imgk))
            # huge[0..95] vs default[0..95]
            same = sum(1 for i in range(96)
                       if H.rec_at(fs['huge'], i) == H.rec_at(fs['default'], i))
            W('  huge.rec[0..95] vs default.rec[0..95] 相同条数 = %d / 96' % same)
            W('  huge.nrec=%d default.nrec=%d large.nrec=%d'
              % (fs['huge']['nr'], fs['default']['nr'], fs['large']['nr']))
            for nm in ('huge', 'default'):
                rs = [H.rec_at(fs[nm], i) for i in range(fs[nm]['nr'])]
                adv = Counter(r[1] for r in rs)
                W('  %-8s 记录数=%3d  推进(b1)分布=%s' % (nm, len(rs), adv.most_common(6)))
            if tag == 'ZH113b':
                blk = fs['default']['recs'][960:2240]
                assert len(blk) == 1280
                fn = os.path.join(H.EVID, 'planB_huge_rec96_223_%s.bin' % imgk)
                open(fn, 'wb').write(blk)
                meta[imgk] = dict(
                    source='ZH113b / %s.IMG entry #%d  FONT.RES 展开态 `default` 面 rec[96..223]'
                           % (imgk, d['entry']['idx']),
                    src_plain_off=fs['default']['rec_off'] + 960,
                    len=len(blk), sha256=hashlib.sha256(blk).hexdigest(),
                    first32=blk[:32].hex(' '), last32=blk[-32:].hex(' '),
                    file=os.path.basename(fn),
                    result='huge 面记录表将与 default 面**逐字节相同**（huge ≡ default）')
                W('  ★ 方案 B 备料: %s len=%d sha256=%s'
                  % (os.path.basename(fn), len(blk), meta[imgk]['sha256']))
            # EN huge[96..223] 的推进与矩形统计
            if tag == 'EN_ORIG':
                rs = [H.rec_at(fs['huge'], i) for i in range(96, 224)]
                W('  EN huge.rec[96..223] 推进(b1)分布=%s' % (Counter(r[1] for r in rs).most_common(8),))
                W('  EN huge.rec[96..223] 矩形(w×h)分布=%s'
                  % (Counter((r[4] - r[2], r[5] - r[3]) for r in rs).most_common(6),))
                W('  EN huge.rec[96..223] u 范围=[%d,%d] v 范围=[%d,%d]'
                  % (min(r[2] for r in rs), max(r[4] for r in rs),
                     min(r[3] for r in rs), max(r[5] for r in rs)))
            if tag == 'ZH113b':
                rs = [H.rec_at(fs['huge'], i) for i in range(96)]
                W('  ZH huge.rec[0..95]  推进(b1)分布=%s' % (Counter(r[1] for r in rs).most_common(6),))
                W('  ZH huge.rec[0..95]  矩形(w×h)分布=%s'
                  % (Counter((r[4] - r[2], r[5] - r[3]) for r in rs).most_common(6),))
                rs2 = [H.rec_at(fs['default'], i) for i in range(96, 224)]
                W('  ZH default.rec[96..223] 推进(b1)分布=%s'
                  % (Counter(r[1] for r in rs2).most_common(6),))
                W('  ZH default.rec[96..223] 矩形(w×h)分布=%s'
                  % (Counter((r[4] - r[2], r[5] - r[3]) for r in rs2).most_common(6),))
    meta['_note'] = ('方案 B 是"最接近单变量"的替代补全：因为汉化盘的 huge 面 rec[0..95] '
                     '与 default 面 rec[0..95] 逐字节相同 ⇒ 补上 default 的 96..223 后 '
                     'huge ≡ default（一个游戏本身就在用的合法状态）。')
    W('')
    W('方案 B 备料文件已写入 evidence/。')
    os.makedirs(H.EVID, exist_ok=True)
    open(os.path.join(H.EVID, 'hg2_altplan.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    open(os.path.join(H.EVID, 'planB_meta.json'), 'w', encoding='utf-8').write(
        json.dumps(meta, ensure_ascii=False, indent=1))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
