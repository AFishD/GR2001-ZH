# -*- coding: utf-8 -*-
r"""round56 侦察 ④: 容器普查 —— 哪些容器真的装文本 (只读)。

对两个 IMG 的全部条目:
  · 按扩展名分类 (text-kind: .XML/.TXT/.MIS/.ATR/.RES/... vs 二进制资产);
  · LZO 展开后跑"干净文本段"检测 (与 font_compact 同一口径);
  · 报告: 文本类容器里的中文段 (真文本嫌疑) vs 二进制容器里的巧合段。
"""
import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))

import tcslib                                                        # noqa: E402
from scan2 import clean_runs                                          # noqa: E402

TEXTY_EXT = {'.XML', '.TXT', '.MIS', '.ATR', '.RES', '.CFG', '.INI', '.CSV', '.DAT'}
REGIONS = [('MENU.IMG', 776286), ('GR.IMG', 19175)]


def expand_entry(iso, lba, idx):
    """返回 (entry, blob, mode) —— LZO 展开; 展开失败则 blob=raw。"""
    e = iso.img_entry(lba, idx)
    raw = iso.read(e['iso_off'], e['stored'])
    subs = tcslib.lzo_subs(raw)
    if subs:
        return e, b''.join(s[0] for s in subs), 'lzo(%d)' % len(subs)
    return e, raw, 'raw'


def main():
    cs = tcslib.Charset()
    iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso'))
    t0 = time.time()
    rows = []
    by_ext = {}
    for tag, lba in REGIONS:
        for idx in range(4096):
            try:
                e = iso.img_entry(lba, idx)
            except Exception:                                        # noqa: BLE001
                break
            if e['stored'] <= 0 or e['stored'] > 0x7FFFFFFF:
                if idx == 0:
                    continue
                break
            name = e['name']
            ext = os.path.splitext(name)[1].upper()
            by_ext.setdefault((tag, ext), [0, 0])
            by_ext[(tag, ext)][0] += 1
            by_ext[(tag, ext)][1] += e['stored']
            _, blob, mode = expand_entry(iso, lba, idx)
            runs = clean_runs(blob, cs, min_cjk=4)
            if runs:
                best = max(r[3] for r in runs)
                rows.append(dict(img=tag, idx=idx, name=name, ext=ext, mode=mode,
                                 stored=e['stored'], real=e['real'], blob=len(blob),
                                 runs=len(runs), maxcjk=best,
                                 texty=ext in TEXTY_EXT,
                                 samples=[dict(off=r[0], text=r[2][:60]) for r in runs[:3]]))
    iso.close()
    print('容器扫描 %.1fs; %d 个容器含"干净 ≥4 连续汉字"段' % (time.time() - t0, len(rows)))
    txt = [r for r in rows if r['texty']]
    bin_ = [r for r in rows if not r['texty']]
    print('★ 文本类容器 (扩展名 .XML/.TXT/.MIS/.ATR/.RES/...): %d 个有中文段' % len(txt))
    for r in sorted(txt, key=lambda x: -x['maxcjk'])[:40]:
        print('   %-9s #%-5d %-30s %-10s runs=%-5d maxcjk=%-5d 例 %r'
              % (r['img'], r['idx'], r['name'], r['mode'], r['runs'], r['maxcjk'],
                 r['samples'][0]['text'][:50]))
    print('   二进制类容器: %d 个有中文段 (巧合嫌疑)' % len(bin_))
    for r in sorted(bin_, key=lambda x: -x['maxcjk'])[:10]:
        print('   %-9s #%-5d %-30s runs=%-5d maxcjk=%-5d' % (r['img'], r['idx'], r['name'],
                                                             r['runs'], r['maxcjk']))
    print('按 (IMG,扩展名) 汇总:')
    for k, v in sorted(by_ext.items(), key=lambda kv: -kv[1][1])[:40]:
        print('   %-6s %-8s %5d 个  %10d B' % (k[0], k[1] or '(无)', v[0], v[1]))
    io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'container_census.json'),
            'w', encoding='utf-8', newline='\n').write(
        json.dumps(dict(rows=rows, by_ext=dict(('%s%s' % k, v) for k, v in by_ext.items())),
                   ensure_ascii=False, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
