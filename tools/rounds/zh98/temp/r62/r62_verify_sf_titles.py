# -*- coding: utf-8 -*-
r"""r62_verify_sf_titles.py — round62 验收: 新表 *_view_sf_titles.csv 的搜到率 + 13 张表对照。

判据 (全部独立于 dump_containers.py 的代码路径, 自己按盘上字节重新解析):
  ① 注入目标 MENU.IMG#283 里**含中文的** <item|group|studio name="…"> 属性 (期望 123 个)
     逐个点名, 必须能在新表里按 **text 单元格精确匹配**搜到 ⇒ 期望 123/123;
  ② 全部副本里含非 ASCII 的属性 (期望 297 个) 也逐个点名 ⇒ 期望 297/297;
  ③ 用户点名的串在新表里必须是 **is_title=yes 的标题行**;
  ④ 13 张表逐表对照基线 (work/builds/GR_ZH109/text/) 的行数 + sha256;
  ⑤ 新表自查: injectable 全 no / 偏移回读自证 / 无不可见字符。

只读 ISO 与 CSV; 输出 JSON + 人话报告到 stdout。
"""
import collections
import csv
import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T                                                    # noqa: E402
import font_usage as FU                                               # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text')       # 基线 (别动)
NEW = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text_r62')    # 本轮产出
NEW_TABLE = 'GR_ZH109_view_sf_titles.csv'
OUT = os.path.join(HERE, 'r62_verify_sf_titles.json')

ITEM_RE = re.compile(rb'<(item|group|studio)\b([^>]*)>')
ANYTAG_RE = re.compile(rb'<([A-Za-z_][\w:.-]*)\b([^>]*)>')
ATTR_RE = re.compile(rb'([A-Za-z_][\w:.-]*)\s*=\s*"([^"]*)"')
NAME_RE = re.compile(rb'name\s*=\s*"([^"]*)"')
CJK_RE = re.compile(r'[\u4e00-\u9fff]')
CJK2_RE = re.compile(r'[\u4e00-\u9fff]{2,}')
NONASCII_RE = re.compile(r'[^\x00-\x7f]')
FORBIDDEN_RE = re.compile(                                                   # 与工具同一份
    '[\u0000-\u0008\u000b-\u001f\u007f-\u009f'
    '\ue000-\uf8ff'
    '\u200b-\u200f\u2028\u2029\u202a-\u202e'
    '\u2060-\u2069\ufeff\u00ad]')

res = dict(checks=[], fail=0)


def check(name, ok, detail=''):
    res['checks'].append(dict(name=name, ok=bool(ok), detail=detail))
    if not ok:
        res['fail'] += 1
    print('  [%s] %s%s' % ('ok' if ok else '!!', name, ('  — %s' % detail) if detail else ''))
    return bool(ok)


def sha(path):
    h = hashlib.sha256()
    h.update(io.open(path, 'rb').read())
    return h.hexdigest()


def ncols(path):
    """CSV 的逻辑行数 (不含表头) —— 单元格里可能有换行, 所以不能用行数数。"""
    with io.open(path, encoding='utf-8-sig', newline='') as f:
        return sum(1 for _ in csv.reader(f)) - 1


# ═════════════ 1. 从盘上独立重新解析出全部属性 (与 dump_containers.py 不同写法) ═════════════
print('=' * 78)
print('round62 验收 — SFXML 标题表 (*_view_sf_titles.csv)')
print('=' * 78)
iso = T.Iso(ISO)
cs = T.Charset()
conts = FU.build_container_list(iso)
sf = [c for c in conts if re.search(r'(?:^|_)SPECIAL_FEATURE\.XML$', c['name'], re.I)]
sf.sort(key=lambda c: (c['img'], c['idx']))

want_title, want_nonascii, copies = {}, {}, []
for c in sf:
    blob, _raw = FU.container_blob(iso, c)
    key = '%s#%d %s' % (c['img'], c['idx'], c['name'])
    base = os.path.basename(c['name'])
    m = re.match(r'^([A-Za-z]{2})_', base)
    lang = m.group(1).upper() if m else '?'
    # copies[i] = (img, lba, idx, tag) ⇒ 注入目标键 = (img, idx) = (copies[0][0], copies[0][2])
    role = 'zh-main' if (c['img'], c['idx']) == (T.RES['SFXML']['copies'][0][0],
                                                 T.RES['SFXML']['copies'][0][2]) else 'lang-copy'
    # ① 只用 <item|group|studio ... name="…"> (与 lead 的 123 口径一致)
    for mm in ITEM_RE.finditer(blob):
        nm = NAME_RE.search(mm.group(2))
        if not nm:
            continue
        txt = cs.decode(nm.group(1))[0]
        if NONASCII_RE.search(txt):
            want_title.setdefault(txt, []).append((key, lang, role))
    # ② 任何标签上含非 ASCII 的属性 (兜底口径)
    for mm in ANYTAG_RE.finditer(blob):
        for am in ATTR_RE.finditer(mm.group(2)):
            txt = cs.decode(am.group(2))[0]
            if NONASCII_RE.search(txt):
                want_nonascii.setdefault(txt, []).append(
                    (key, mm.group(1).decode('latin-1'), am.group(1).decode('latin-1')))
    copies.append(dict(container=key, lang=lang, role=role, blob=len(blob),
                       name_attrs=sum(1 for mm in ITEM_RE.finditer(blob)
                                      if NAME_RE.search(mm.group(2))),
                       text_elements=len(T.TEXT_RE.findall(blob))))
print('\n# 盘上副本 %d 份; 含非 ASCII 的 item/group/studio name 属性 "%s" 个 (去重后 %d); '
      '任何标签非 ASCII 属性 "%s" 个 (去重后 %d)'
      % (len(copies), sum(len(v) for v in want_title.values()), len(want_title),
         sum(len(v) for v in want_nonascii.values()), len(want_nonascii)))
n_title_attr = sum(len(v) for v in want_title.values())
n_nonascii_attr = sum(len(v) for v in want_nonascii.values())
c0 = [x for x in copies if x['role'] == 'zh-main']
n_title_c0 = sum(len(v) for v in want_title.values() if any(x[2] == 'zh-main' for x in v))
print('# 其中注入目标 %s: 含非 ASCII 的 name 属性 %d 个'
      % (c0[0]['container'] if c0 else '(无)', n_title_c0))

# ═════════════ 2. 读新表 ═════════════
new_path = os.path.join(NEW, NEW_TABLE)
if not os.path.isfile(new_path):
    print('\n!! 新表不存在: %s' % new_path)
    sys.exit(2)
with io.open(new_path, encoding='utf-8-sig', newline='') as f:
    rd = csv.DictReader(f)
    cols = rd.fieldnames
    rows = list(rd)
print('\n# 新表 %s: %d 行, %d 列' % (NEW_TABLE, len(rows), len(cols)))
print('# 列: %s' % ','.join(cols))

title_cells = collections.defaultdict(list)
for r in rows:
    title_cells[r['text']].append(r)

print('\n== ① 注入目标 (MENU.IMG#283) 的含中文属性名, 逐个点名 ==')
zh = [t for t in want_title if any(x[2] == 'zh-main' for x in want_title[t])]
n_occ = sum(len(want_title[t]) for t in zh)
miss = [t for t in zh if t not in title_cells]
check('注入目标含中文属性名 %d 次出现 / %d 个**不同**标题串 100%% 在新表里 (精确 text 单元格)'
      % (n_occ, len(zh)), not miss,
      '搜到 %d/%d 个不同串%s' % (len(zh) - len(miss), len(zh),
                                ('; 漏: %s' % miss[:5]) if miss else ''))
# 且必须是 is_title=yes 的行
not_title = [t for t in title_cells
             if any(x[2] == 'zh-main' for x in want_title.get(t, []))
             and all(r['is_title'] != 'yes' for r in title_cells[t])]
check('这些命中行全都 is_title=yes (不是正文巧合)', not not_title, '异常 %d' % len(not_title))

print('\n== ② 全部副本的含非 ASCII 属性 (兜底口径) %d 个, 逐个点名 ==' % n_nonascii_attr)
miss2 = [t for t in want_nonascii if t not in title_cells]
check('全部副本含非 ASCII 属性 %d 个都在新表里' % n_nonascii_attr, not miss2,
      '搜到 %d/%d%s' % (n_nonascii_attr - len(miss2), n_nonascii_attr,
                        ('; 漏: %s' % miss2[:5]) if miss2 else ''))

print('\n== ②b 每份副本的 name 属性全量覆盖 (145 × 副本数) ==')
per_copy = collections.Counter(r['container'] for r in rows if r['is_title'] == 'yes')
bad_cp = [(c['container'], per_copy.get(c['container'], 0), c['name_attrs'])
          for c in copies if per_copy.get(c['container'], 0) != c['name_attrs']]
check('每份副本的 name 属性行数 = 盘上 name 属性数', not bad_cp,
      '副本 %d 份, 每份 %s 行' % (len(copies), sorted(set(x[2] for x in bad_cp)) or '145'))

print('\n== ③ 用户点名的串 (必须是**标题行**, 不只是正文) ==')
named = ['国会荣誉勋章', '国会最高勋章', '优异服役十字勋章', '何为幽灵']
named_rep = {}
for w in named:
    hits = [r for r in rows if w in r['text']]
    t_hits = [r for r in hits if r['is_title'] == 'yes']
    named_rep[w] = dict(rows=len(hits), title_rows=len(t_hits),
                        where=[dict(container=r['container'], lang=r['lang'],
                                    role=r['copy_role'], tag=r['tag'], attr=r['attr'],
                                    entry_index=r['entry_index'],
                                    tag_offset=r['tag_offset'], offset=r['offset'],
                                    len_bytes=r['len_bytes'], text=r['text'],
                                    cjk_run=r['cjk_run']) for r in t_hits[:3]])
    print('  「%s」: 新表 %d 行, 其中标题行 %d' % (w, len(hits), len(t_hits)))
    for x in named_rep[w]['where']:
        print('        %s <%s %s="…"> 第%s个属性 tag@%s 值@%s (%s B) = %r'
              % (x['container'], x['tag'], x['attr'], x['entry_index'],
                 x['tag_offset'], x['offset'], x['len_bytes'], x['text']))
for w in ('国会最高勋章', '优异服役十字勋章', '何为幽灵'):
    check('「%s」在新表里是标题行' % w, named_rep[w]['title_rows'] >= 1,
          '标题行 %d 行' % named_rep[w]['title_rows'])

print('\n== ③b 老口径对照: 这些标题在**改动前的 13 张表**里能搜到几个 ==')
old_files = sorted(f for f in os.listdir(BASE) if f.endswith('.csv'))
old_blob = {}
for f in old_files:
    old_blob[f] = io.open(os.path.join(BASE, f), encoding='utf-8-sig', errors='replace').read()
old_hit, old_where = 0, collections.Counter()
for t in zh:
    who = [f for f, b in old_blob.items() if t in b]
    if who:
        old_hit += 1
        for f in who:
            old_where[f] += 1
old_hit_occ = sum(len(want_title[t]) for t in zh if any(t in b for b in old_blob.values()))
print('# 旧 13 张表: **不同标题串** %d/%d 能搜到 (其余 %d 个一个字都搜不到); '
      '按出现次数算 %d/%d'
      % (old_hit, len(zh), len(zh) - old_hit, old_hit_occ, n_occ))
print('#   命中分布 (表 → 命中几个不同串): %s' % dict(old_where))
res['old_tables_hit'] = dict(unique_hit=old_hit, unique_total=len(zh),
                             occ_hit=old_hit_occ, occ_total=n_occ,
                             by_table=dict(old_where))
check('新表搜到率 100%% (不同串 %d/%d) > 旧表 %d/%d'
      % (len(zh) - len(miss), len(zh), old_hit, len(zh)), not miss)

print('\n== ④ 13 张表逐表对照 (基线 %s → 本轮 %s) =='
      % (os.path.relpath(BASE, REPO).replace('\\', '/'),
         os.path.relpath(NEW, REPO).replace('\\', '/')))
base_meta = json.load(io.open(os.path.join(BASE, 'GR_ZH109_view_containers.meta.json'),
                              encoding='utf-8'))
text_meta = json.load(io.open(os.path.join(BASE, 'GR_ZH109_text.meta.json'), encoding='utf-8'))
base_sha = dict((t['name'], (t['rows'], t['sha256'])) for t in base_meta['tables'])
base_sha[os.path.basename(base_meta['summary']['path'])] = (base_meta['summary']['rows'], None)
for f in text_meta['tables']['files']:
    base_sha[f['name']] = (f['rows'], f['sha256'])
base_sha['GR_ZH109_text_long.csv'] = (text_meta['tables']['files'][0]['rows'], None)  # 用户改过
cmp_rows = []
for name in sorted(os.listdir(BASE)):
    if not name.endswith('.csv'):
        continue
    bp = os.path.join(BASE, name)
    np_ = os.path.join(NEW, name)
    b_rows, b_sha = base_sha.get(name, (ncols(bp), sha(bp)))
    b_disk_rows, b_disk_sha = ncols(bp), sha(bp)
    if os.path.isfile(np_):
        n_rows, n_sha = ncols(np_), sha(np_)
        same = (n_sha == b_sha) if b_sha else None
        cmp_rows.append(dict(table=name, base_rows=b_rows, new_rows=n_rows, delta=n_rows - b_rows,
                             base_sha=b_sha, new_sha=n_sha, identical=same,
                             base_disk_rows=b_disk_rows,
                             base_disk_sha_match=(b_disk_sha == b_sha) if b_sha else None))
    else:
        cmp_rows.append(dict(table=name, base_rows=b_rows, new_rows=None, delta=None,
                             base_sha=b_sha, new_sha=None, identical=None,
                             base_disk_rows=b_disk_rows,
                             base_disk_sha_match=(b_disk_sha == b_sha) if b_sha else None))
print('# %-38s %8s %8s %7s %s' % ('表', '基线行', '本轮行', 'Δ', '字节相同'))
for x in cmp_rows:
    print('# %-38s %8s %8s %7s %s' % (x['table'], x['base_rows'],
                                      x['new_rows'] if x['new_rows'] is not None else '(本工具不产出)',
                                      x['delta'] if x['delta'] is not None else '-',
                                      {True: 'yes ✓', False: '**no**', None: '-'}[x['identical']]))
new_extra = sorted(set(os.listdir(NEW)) - set(os.listdir(BASE)))
print('# 本轮**新增**的文件: %s' % new_extra)
unexpected = [x for x in cmp_rows if x['identical'] is False]
check('9 张 view 数据表逐字节与基线相同', not unexpected,
      '不同: %s' % [x['table'] for x in unexpected])
check('3 张 text 表本轮没被本工具重写 (sha 与建盘时一致除外: 用户改过的 long)',
      all((x['identical'] is None) for x in cmp_rows if '_text_' in x['table']))
check('新增文件恰好是 1 张新表 (+ summary/meta 重生成)',
      sorted(x for x in new_extra if x.endswith('.csv')) == [NEW_TABLE],
      '新增: %s' % new_extra)

print('\n== ⑤ 新表自查 ==')
check('injectable 列全 = no', all(r['injectable'] == 'no' for r in rows))
check('has_cjk=yes 的行都真的有 >=2 连续汉字',
      all(CJK2_RE.search(r['text']) for r in rows if r['has_cjk'] == 'yes'))
check('没有不可见字符 (PUA/控制符/零宽)', not any(FORBIDDEN_RE.search(r[c]) for r in rows
                                              for c in cols))
# 偏移回读自证: 拿新表的 container+offset+len 去盘上回读, 必须解出同一 text
by_c = dict(('%s#%d %s' % (c['img'], c['idx'], c['name']), c) for c in sf)
reread_bad, reread_n = [], 0
for r in rows:
    c = by_c.get(r['container'])
    if c is None:
        reread_bad.append((r['container'], 'container?'))
        continue
    blob, _raw = FU.container_blob(iso, c)
    off, ln = int(r['offset']), int(r['len_bytes'])
    val = blob[off:off + ln]
    txt = T.pua_to_marks(cs.decode(val)[0]).replace('\\', '\\\\').replace('\r', '\\r') \
        .replace('\n', '\\n').replace('\t', '\\t')
    reread_n += 1
    if txt != r['text']:
        reread_bad.append((r['container'], off, txt[:20], r['text'][:20]))
check('%d 行的 offset/len 能回读解出同一 text' % reread_n, not reread_bad,
      '异常 %d %s' % (len(reread_bad), reread_bad[:2]))

print('\n== ⑥ 副本清单 ==')
for c in copies:
    print('# %-36s %-3s %-9s name属性=%3d <text>=%d blob=%d'
          % (c['container'], c['lang'], c['role'], c['name_attrs'], c['text_elements'], c['blob']))

res.update(copies=copies, named=named_rep,
           new_table=dict(path=os.path.relpath(new_path, REPO).replace('\\', '/'),
                          rows=len(rows), cols=cols, sha256=sha(new_path),
                          bytes=os.path.getsize(new_path)),
           n_title_attr=n_title_attr, n_nonascii_attr=n_nonascii_attr,
           n_title_c0=n_title_c0, table_compare=cmp_rows, new_files=new_extra)
json.dump(res, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n%s' % ('=' * 78))
print('结论: %s (失败 %d 项)' % ('全部通过 ✓' if res['fail'] == 0 else '**有失败项**', res['fail']))
print('# → %s' % os.path.relpath(OUT, REPO).replace('\\', '/'))
iso.close()
sys.exit(1 if res['fail'] else 0)
