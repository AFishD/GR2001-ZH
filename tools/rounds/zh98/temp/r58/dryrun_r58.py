# -*- coding: utf-8 -*-
r"""r58 试跑 (只读, 不写任何盘): 走一遍 make_build 的字库步骤逻辑 —— plan_compact + plan_reencode。

用来在真构筑之前看清:
  · 迁移清单是否命中 (输入盘 sha256 钉死);
  · 逐容器走了哪套映射 / 改多少字节 / 用哪种重压方式;
  · 门禁 A3 的登记容器清单。
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
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ISO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    REPO, 'work', 'builds', 'GR_ZH107', 'GR_ZH107.iso')
t0 = time.time()
res = FC.plan_compact(ISO, tcslib.CHARSET, verbose=True)
res['charset_path'] = tcslib.CHARSET
summ = res['summary']
print('\n[plan] changed=%s reencode_only=%s pixels=%d code_changes=%d 迁移=%s  (%.0fs)'
      % (summ['changed'], summ['reencode_only'], summ['pixels_changed'], summ['code_changes'],
         bool(summ['stale_migration']), time.time() - t0))
iso = tcslib.Iso(ISO)
re_ = FC.plan_reencode(iso, res, verbose=True)
iso.close()
print('\n[plan_reencode] 写盘动作 %d 个:' % len(re_['writes']))
for w in re_['writes']:
    d = w['detail']
    print('   %-38s %-9s role=%-9s 改 %5d 字节 / %4d 字, 段 %s (重映射 %s / 未变 %s), %s'
          % (w['label'], d['kind'], 'migrate' if '陈旧' in (w.get('src') or '') else 'forward',
             d.get('changed_bytes', 0), d.get('changed_units', 0), d.get('segments'),
             d.get('segments_changed'), d.get('segments_unchanged'), w.get('method')))
print('\n[scan.registry] 容器 %d 个 / 改动 %d 个 / 段 %d = 重映射 %d + 未变 %d / 改动 %d 字节'
      % (re_['scan']['registry']['containers_total'],
         re_['scan']['registry']['containers_changed'],
         re_['scan']['registry']['segments'],
         re_['scan']['registry']['segments_changed'],
         re_['scan']['registry']['segments_unchanged'],
         re_['scan']['registry']['changed_bytes']))
io.open(os.path.join(HERE, 'dryrun_r58.json'), 'w', encoding='utf-8', newline='\n').write(
    json.dumps(dict(summary=summ, scan=re_['scan'],
                    writes=[dict(label=w['label'], kind=w['detail']['kind'],
                                 changed_bytes=w['detail'].get('changed_bytes'),
                                 method=w.get('method'), slot=w['stored'],
                                 frame_bytes=w['frame_bytes'])
                            for w in re_['writes']]),
               ensure_ascii=False, indent=1, default=str) + '\n')
print('\n→ dryrun_r58.json  总耗时 %.0fs' % (time.time() - t0))
