# -*- coding: utf-8 -*-
r"""r50_finish.py — round50 收尾三件 (幂等, 只读 ISO):
  ① 给 GR_ZH99 资料包补: 引擎采样格紧凑图 (sampled) + 字形几何体检报告 + 字库汇总 + 证据图
  ② 把 README.md / 证据图 / 文本对比报告登记进 MANIFEST.json
  ③ 输出"资料包清单"供报告引用
"""
import io
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib                                              # noqa: E402

BUILD = 'GR_ZH99'
B = os.path.join(REPO, 'work', 'builds', BUILD)
ISO = os.path.join(B, BUILD + '.iso')
FONT = os.path.join(B, 'font')
REL = os.path.join(B, 'release')
RF = os.path.join(REL, 'font')
SAMPLED = os.path.join(B, 'temp', 'release_pack', 'font_sampled')
os.makedirs(RF, exist_ok=True)

sha = tcslib.sha256_file(ISO)
cmd = [sys.executable, os.path.join(REPO, 'tools', 'iso_build', 'dump_font.py'),
       '--iso', ISO, '--out', SAMPLED, '--prefix', BUILD,
       '--scale', '3', '--only-sampled', '--iso-sha', sha]
r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                   encoding='utf-8', errors='replace')
print('[sampled] exit=%d' % r.returncode)

added = []


def put(src, dstname, note):
    if not os.path.isfile(src):
        print('  !! 缺 %s' % src)
        return
    dst = os.path.join(RF, dstname)
    shutil.copy2(src, dst)
    added.append(dict(path=os.path.relpath(dst, REPO).replace('\\', '/'),
                      name=dstname, bytes=os.path.getsize(dst),
                      sha256=tcslib.sha256_file(dst),
                      source=os.path.relpath(src, REPO).replace('\\', '/'), note=note))
    print('  + font/%s' % dstname)


put(os.path.join(SAMPLED, '%s_font_atlas_sampled.png' % BUILD),
    '%s_font_atlas_sampled.png' % BUILD,
    '★ 只拼"引擎会采样的格"(对偶格 + FT 记录带) 的紧凑图, 3 倍放大 —— 看字形最直观')
put(os.path.join(FONT, '%s_font_atlas_README.txt' % BUILD),
    '%s_font_atlas_README.txt' % BUILD, '图集看图须知 (人话)')
put(os.path.join(FONT, '%s_truncation_report.json' % BUILD),
    '%s_truncation_report.json' % BUILD,
    '★ round50 字形几何体检 (结构化判据: 截断/空白/越窗/错位) 机器可读版')
put(os.path.join(FONT, '%s_truncation_report.md' % BUILD),
    '%s_truncation_report.md' % BUILD, '★ round50 字形几何体检 (人话版)')
put(os.path.join(FONT, '%s_font_summary.json' % BUILD),
    '%s_font_summary.json' % BUILD, '字库汇总 (含 glyph_geometry 段)')

# 证据图 + 文本对比报告 (由 r50_zoom.py / diff_text_versions 产出)
put(os.path.join(HERE, 'zoom_truncation.png'), '%s_truncation_evidence.png' % BUILD,
    '★ 证据图: 旧盘那一行的「盘上像素 vs 16px 模板 vs 缺失像素(红) vs 现役盘」')
put(os.path.join(HERE, 'diff_text_99_vs_98.log'), '%s_diff_text_vs_zh98.log' % BUILD,
    '★ 与 GR_ZH98 的文本对比: 修改 0 条')
put(os.path.join(HERE, 'repackON', 'ab_zoom_doc_wide.png'),
    '%s_repackON_regression_evidence.png' % BUILD,
    '★ 反例证据: 开紧凑重排后「何为幽灵？」被画成「何为强知营」(doc 页标题) —— 所以本轮不重排')

MP = os.path.join(REL, 'MANIFEST.json')
doc = json.load(io.open(MP, encoding='utf-8'))
have = set(x['name'] for x in doc.get('files', []))
newrows = [x for x in added if x['name'] not in have]
manual = [
    ('README.md', '(人话) 资料包总说明'),
    ('text/README_文本表.md', '(人话) 文本表怎么用'),
]
for name, note in manual:
    p = os.path.join(REL, name.replace('/', os.sep))
    if os.path.isfile(p) and os.path.basename(name) not in have:
        newrows.append(dict(path=os.path.relpath(p, REPO).replace('\\', '/'),
                            name=os.path.basename(name), bytes=os.path.getsize(p),
                            sha256=tcslib.sha256_file(p), source='(人工维护)', note=note))
doc.setdefault('files', []).extend(newrows)
doc['files'].sort(key=lambda x: x['path'])
doc['round50'] = dict(
    tool='work/builds/GR_ZH99/temp/verify/r50_finish.py',
    note='round50 资料包: 新增 字形几何体检报告 / 引擎采样格紧凑图 / 截断证据图 / 重排反例证据 / 文本对比报告',
    added=sorted(x['name'] for x in newrows))
io.open(MP, 'w', encoding='utf-8', newline='\n').write(
    json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
print('[manifest] 追加 %d 条, 共 %d 条' % (len(newrows), len(doc['files'])))
for x in doc['files']:
    print('   %-52s %9d B  %s' % (x['path'], x['bytes'], x['sha256'][:16]))
