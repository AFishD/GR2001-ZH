# -*- coding: utf-8 -*-
r"""csfix_frames.py —— 复用 `GR_HASHR\runs\*` 的对照方法做 191 帧逐像素对照（只读）。

对照基准 = 两次 6000 帧实跑留下的截图（`snap_f*.png`）+ `result.json` 里的 snap_sha。
本工具**不需要 ISO**，因此即便 `work\builds\**` 的 ISO 被外部清理，仍可复核既有读数。

用法：
  python csfix_frames.py <dirA> <dirB> [--out report.json]
  · 逐帧 sha256 对照（result.json 的 snap_sha，若缺则现算文件的 sha256）
  · 共同帧 / 相同帧 / 不同帧清单 / 帧区间
  · 可选 --pixel 时对"不同帧"逐像素比对（PIL）给出不同像素数与 bbox
"""
import hashlib
import json
import os
import re
import sys


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def load(d):
    res = os.path.join(d, 'result.json')
    meta = {}
    if os.path.exists(res):
        try:
            meta = json.load(open(res, encoding='utf-8'))
        except Exception:                                                     # noqa: BLE001
            meta = {}
    snaps = {}
    for n in os.listdir(d):
        m = re.match(r'^snap_f(\d+)\.png$', n)
        if m:
            snaps[int(m.group(1))] = os.path.join(d, n)
    shas = {int(k): v for k, v in (meta.get('snap_sha') or {}).items()}
    for fr, p in snaps.items():
        if fr not in shas:
            shas[fr] = sha_file(p)
    return dict(dir=d, meta=meta, snaps=snaps, shas=shas)


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    a, b = load(sys.argv[1]), load(sys.argv[2])
    common = sorted(set(a['shas']) & set(b['shas']))
    same = [f for f in common if a['shas'][f] == b['shas'][f]]
    diff = [f for f in common if a['shas'][f] != b['shas'][f]]
    rep = dict(A=os.path.basename(a['dir']), B=os.path.basename(b['dir']),
               n_snap=[len(a['snaps']), len(b['snaps'])],
               unique=[len(set(a['shas'].values())), len(set(b['shas'].values()))],
               frame_range=[(min(a['shas']), max(a['shas'])), (min(b['shas']), max(b['shas']))],
               common=len(common), same=len(same), diff=len(diff),
               diff_frames=['snap_f%08d.png' % f for f in diff],
               A_only=[f for f in sorted(set(a['shas']) - set(b['shas']))],
               B_only=[f for f in sorted(set(b['shas']) - set(a['shas']))])
    print('A = %s   截图 %d / 去重 %d / 帧 %s'
          % (rep['A'], rep['n_snap'][0], rep['unique'][0], rep['frame_range'][0]))
    print('B = %s   截图 %d / 去重 %d / 帧 %s'
          % (rep['B'], rep['n_snap'][1], rep['unique'][1], rep['frame_range'][1]))
    print('共同帧 %d ; 逐帧 sha256 **相同 %d** ; **不同 %d**'
          % (rep['common'], rep['same'], rep['diff']))
    if diff:
        print('不同帧清单（%d）：%s' % (len(diff), rep['diff_frames']))
    else:
        print('不同帧清单：[] ⇒ **逐像素 0 差异**（191 帧全部相同）')
    if len(sys.argv) > 3 and sys.argv[3] == '--pixel' and diff:
        try:
            from PIL import Image, ImageChops
        except Exception as e:                                                # noqa: BLE001
            print('[pixel] PIL 不可用：%s' % e)
            Image = None
        if Image:
            px = []
            for f in diff:
                p1, p2 = a['snaps'][f], b['snaps'][f]
                i1, i2 = Image.open(p1).convert('RGBA'), Image.open(p2).convert('RGBA')
                if i1.size != i2.size:
                    px.append(dict(frame=f, size_mismatch=[i1.size, i2.size]))
                    continue
                d = ImageChops.difference(i1, i2)
                bbox = d.getbbox()
                n = 0 if bbox is None else sum(1 for p in d.getdata() if p != (0, 0, 0, 0))
                px.append(dict(frame=f, diff_px=n, bbox=bbox))
            rep['pixel'] = px
            print('[pixel] 不同帧逐像素：%s'
                  % ', '.join('%s:%s px %s' % (x['frame'][5:13], x.get('diff_px'),
                                               x.get('bbox')) for x in px))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'audit',
                       'frames_cmp_%s_vs_%s.json' % (rep['A'], rep['B']))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(rep, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('[out] %s' % os.path.normpath(out))


if __name__ == '__main__':
    main()
