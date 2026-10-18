# -*- coding: utf-8 -*-
"""round56: 只算不写地验证 font_compact 的重编码方案 (LANG/SFXML 逐字重映射 + 重压)。"""
import io
import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                        # noqa: E402
import font_compact as FC                                            # noqa: E402

iso_p = os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso')
res = FC.plan_compact(iso_p, verbose=False)
res['charset_path'] = tcslib.CHARSET
print('搬字: 在用 %d, 搬 %d, 改码位 %d, 空闲 %s'
      % (res['summary']['glyphs']['used'], res['summary']['glyphs']['moved'],
         res['summary']['code_changes'], res['summary']['layout']['free_slots']))
iso = tcslib.Iso(iso_p)
re_ = FC.plan_reencode(iso, res)
iso.close()
print('\n== writes 明细 ==')
for w in re_['writes']:
    d = dict(w['detail'])
    print('%-34s kind=%-8s frame=%d/%d slot=%d 子流重压 %d' % (w['label'], d.pop('kind'),
                                                              w['frame_bytes'], w['stored'],
                                                              w['stored'], w['substreams_repacked']))
    print('   ', json.dumps(d, ensure_ascii=False))
print('\n== scan 摘要 ==')
s = re_['scan']
print(json.dumps({k: v for k, v in s.items() if k not in ('by_container',)},
                 ensure_ascii=False, indent=1)[:4000])
print('\n== by_container (前 12) ==')
for k, v in list(s['by_container'].items())[:12]:
    print('   %-42s runs=%-6d texty=%-5s %s' % (k, v['runs'], v['texty'],
                                                json.dumps(v['best'], ensure_ascii=False)[:110]))
io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reencode_plan.json'),
        'w', encoding='utf-8', newline='\n').write(
    json.dumps(dict(scan=re_['scan'],
                    writes=[dict(label=w['label'], kind=w['detail']['kind'],
                                 frame_bytes=w['frame_bytes'], stored=w['stored'],
                                 detail=w['detail']) for w in re_['writes']],
                    layout=res['summary']['layout'], glyphs=res['summary']['glyphs'],
                    code_changes=res['summary']['code_changes']),
               ensure_ascii=False, indent=1) + '\n')
print('\n→ reencode_plan.json')
