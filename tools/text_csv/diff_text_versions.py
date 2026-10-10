# -*- coding: utf-8 -*-
r"""diff_text_versions.py — 对比两个版本的「盘内文本」(只读; 不写任何 ISO)

配套: tools/iso_build/make_build.py 每次构筑成功都会把该版本的文本副本写进
      **版本文件夹内** `work/builds/<版本>/text/` ——
      round37 起是**按 kind 分类的多张表** `<版本>_text_<kind>.csv` + 合并的
      `<版本>_text.txt`; 本工具就是拿这些副本互相对比。

用法:
  python tools/text_csv/diff_text_versions.py GR_ZH92 GR_ZH93
  python tools/text_csv/diff_text_versions.py GR_ZH92 GR_ZH93 --out temp/diff.txt
  python tools/text_csv/diff_text_versions.py --list                       # 看有哪些版本可比
  python tools/text_csv/diff_text_versions.py work/builds/GR_ZH93 work/builds/GR_ZH92

参数可以是:
  · 版本名 (GR_ZH92)          → 依次找 work/builds/<版本>/text/ 、work/builds/<版本>/ 、
                                work/text_versions/ (旧归档, 只读兜底)
  · 快照文件 (*_text.txt / *.csv / *_text_<kind>.csv)
  · 构筑目录 (work/builds/GR_ZH92) 或 text/ 目录 (会自动读里面的多表)
  · ISO 路径 (会临时 dump 到**系统临时目录**, 用完删掉; **绝不改动 ISO**)

★ round37 多表支持:
  · 一版的快照是**多张表**时 (text/<版本>_text_<kind>.csv), 本工具先按 `id` **合并**,
    再按 `id` 与另一版比对 ⇒ **输出格式与以前完全一样** (改/增/删三类)。
  · 优先用合并 TXT (`<版本>_text.txt`); 没有 TXT 就用多表合并 (两者视图一致, 见 §"口径")。
  · 同一个 id 在两张表里 text_edited 不一致 ⇒ 打显著告警并按**先给的那张**为准
    (本工具只读; 注入器遇到同样情况会直接拒绝注入)。

对齐与比较口径:
  · 按 `id` 对齐 (LANG:Gxxx.Ixxx / SFXML:Txxxx) —— 换行/长度变化都不会错位;
  · 文本按「转义单行形式」逐字符比较 (换行=\n 制表=\t 反斜杠=\\);
  · 差异按 修改 / 只在 B 新增 / 只在 A 消失 三类列出, 修改条目用行级 +/- 展示。

★ 本工具**只读**: 不写 ISO、不改任何 CSV, 临时文件也只落在系统临时目录 (不在仓库的 work/ 里)。

退出码: 0 = 对比完成 (有无差异都是 0); 1 = 参数错; 2 = 找不到/读不了版本。
"""
import argparse
import csv
import difflib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
BUILDS = os.path.join(REPO, 'work', 'builds')
TEXT_VERSIONS = os.path.join(REPO, 'work', 'text_versions')   # 旧归档位: **只读兜底**
LEGACY_CSV = os.path.join(REPO, 'work', 'text_csv')
DUMP = os.path.join(HERE, 'dump_text_csv.py')

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:                                                    # noqa: BLE001
    pass

import tcslib as T                                               # noqa: E402


def rel(p):
    try:
        r = os.path.relpath(p, REPO)
    except ValueError:
        return p
    return r.replace('\\', '/') if not r.startswith('..') else p.replace('\\', '/')


def esc_text(s):
    """正文 → 单行转义形式 (与 make_build.py 的 TXT 快照完全同一口径)。"""
    return (s.replace('\\', '\\\\').replace('\r', '\\r')
             .replace('\n', '\\n').replace('\t', '\\t'))


def unesc_text(s):
    """单行转义形式 → 正文 (esc_text 的逆运算)。"""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == '\\' and i + 1 < n:
            nxt = s[i + 1]
            m = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\'}.get(nxt)
            if m is not None:
                out.append(m)
                i += 2
                continue
        out.append(c)
        i += 1
    return ''.join(out)


def cjk_count(s):
    return sum(1 for c in s if '\u4e00' <= c <= '\u9fff')


def sha256_short(path, n=12):
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 22), b''):
            h.update(chunk)
    return h.hexdigest()[:n]


# ───────────────────────── 装载 ─────────────────────────

class Side:
    def __init__(self, label, path, rows, note=''):
        self.label, self.path, self.note = label, path, note
        self.rows = rows                                     # [dict(id, text, key, container)]
        self.chars = sum(len(r['text']) for r in rows)
        self.cjk = sum(cjk_count(r['text']) for r in rows)
        self.ids = [r['id'] for r in rows]


def load_txt(path, label):
    rows = []
    with io.open(path, 'r', encoding='utf-8-sig', newline='') as f:
        for ln in f:
            ln = ln.rstrip('\r\n')
            if not ln or ln.startswith('#'):
                continue
            parts = ln.split('\t', 1)
            if len(parts) != 2:
                raise SystemExit('!! %s: 第 %d 行不是 `id<TAB>正文` 格式' % (path, len(rows) + 1))
            text = unesc_text(parts[1])
            rows.append(dict(id=parts[0].strip(), text=text,
                             key=esc_text(text), container=''))
    return Side(label, path, rows)


def load_csv(path, label):
    rows = []
    with io.open(path, 'r', encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            rid = (r.get('id') or '').strip()
            if not rid:
                continue
            t = r.get('text_edited')
            if t is None or t == '':
                t = r.get('text_zh') or ''
            rows.append(dict(id=rid, text=t, key=esc_text(t),
                             container=(r.get('container') or '').strip()))
    return Side(label, path, rows)


def table_set_paths(d):
    """目录里的**多表** (``*_text_<kind>.csv``), 按文件名排序; 没有就返回 []。"""
    if not os.path.isdir(d):
        return []
    return sorted(os.path.join(d, f) for f in os.listdir(d)
                  if f.lower().endswith('.csv') and T.is_table_csv(f))


def load_tables(paths, label):
    """**多张表**按 `id` 合并成一份 (与注入器同一口径: text_edited 优先, 缺则 text_zh)。

    同一个 id 在两张表里 text_edited 不一致 ⇒ 打显著告警并按**先给的那张**为准
    (本工具只读; 注入器遇到同样情况会直接拒绝注入 —— 见 FORMAT.md §0)。
    """
    rows, seen, kinds, bad = [], {}, [], []
    for p in paths:
        try:
            rs, _cols = T.read_table_rows(p)
        except Exception as ex:                                      # noqa: BLE001
            raise SystemExit('!! 读不了表 %s: %s' % (rel(p), ex))
        _base, kind = T.split_table_name(p)
        if kind and kind not in kinds:
            kinds.append(kind)
        for r in rs:
            rid = (r.get('id') or '').strip()
            if not rid:
                continue
            t = r.get('text_edited')
            if t is None or t == '':
                t = r.get('text_zh') or ''
            if rid in seen:
                if seen[rid]['text'] != t:
                    bad.append((rid, seen[rid]['src'], p))
                continue
            row = dict(id=rid, text=t, key=esc_text(t),
                       container=(r.get('container') or '').strip(), src=p)
            seen[rid] = row
            rows.append(row)
    if bad:
        sys.stderr.write('!! 注意: %d 处「同一个 id 在两张表里 text_edited 不一致」'
                         '(已按先给的那张为准): %s\n'
                         % (len(bad), ' '.join('%s(%s vs %s)' % (i, rel(a).split('/')[-1],
                                                                 rel(b).split('/')[-1])
                                               for (i, a, b) in bad[:6])))
    label_dir = os.path.dirname(os.path.abspath(paths[0]))
    base = os.path.basename(T.table_base(paths[0]))          # 例: GR_ZH92_text
    s = Side(label, os.path.join(label_dir, base + '_*.csv'), rows)
    s.note = ('多表合并: %d 张 (%s)' % (len(paths), '/'.join(kinds) or '?'))
    return s


def load_iso(path, label):
    """临时 dump 一份出来对比 (只读 ISO; 临时文件落在系统临时目录, 用完即删)。"""
    d = tempfile.mkdtemp(prefix='gr_difftext_')      # ★ 系统临时目录 (不再写 work/tmp/)
    out = os.path.join(d, 'text.csv')
    try:
        print('# (临时 dump %s → %s; 不动 ISO)' % (rel(path), out))
        r = subprocess.run([sys.executable, DUMP, '--iso', path, '--out', out],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        tp = table_set_paths(d)
        if r.returncode != 0 or (not tp and not os.path.isfile(out)):
            sys.stderr.write((r.stdout or '')[-1500:] + (r.stderr or '')[-1500:])
            raise SystemExit('!! 临时 dump 失败 (exit=%d): %s' % (r.returncode, path))
        s = load_tables(tp, label) if tp else load_csv(out, label)
        s.note = '由 ISO 临时 dump (sha %s)' % sha256_short(path)
        return s
    finally:
        shutil.rmtree(d, ignore_errors=True)


def snapshot_candidates(name):
    """版本名 → 候选快照 (按优先级)。

    ★ 版本文件夹内的位置 (`work/builds/<版本>/text/`) 排最前;
      旧的 `work/text_versions/` 归档位保留在最后 **只读兜底** (新构筑不再往里写)。
    ★ round37: 多表 (`<版本>_text_<kind>.csv`) 与合并 TXT (`.txt`) 都在正式位置;
      TXT 优先 (视图与多表一致, 且是一份), 其次是多表 (合并后比对)。
    返回 ``[(kind, path)]``; kind ∈ ``txt`` / ``tables`` / ``csv`` / ``iso``。
    """
    tdir = os.path.join(BUILDS, name, 'text')
    out = []
    txt = os.path.join(tdir, name + '_text.txt')
    if os.path.isfile(txt):
        out.append(('txt', txt))
    out += [('tables', p) for p in table_set_paths(tdir)]
    for p in (os.path.join(tdir, name + '_text.csv'),          # 老布局: 合并大表
              os.path.join(BUILDS, name, name + '_text.txt'),  # 旧位置 (版本文件夹根)
              os.path.join(BUILDS, name, name + '_text.csv'),
              os.path.join(TEXT_VERSIONS, name + '_text.txt'),  # 更早的归档 (只读兜底)
              os.path.join(TEXT_VERSIONS, name + '_text.csv'),
              os.path.join(LEGACY_CSV, name + '_text.csv')):
        if os.path.isfile(p):
            out.append(('csv' if p.lower().endswith('.csv') else 'txt', p))
    for p in (os.path.join(BUILDS, name, name + '.iso'),
              os.path.join(TEXT_VERSIONS, name + '.iso')):
        if os.path.isfile(p):
            out.append(('iso', p))
    out += [('txt', p) for p in (os.path.join(TEXT_VERSIONS, name + '.txt'),
                                 os.path.join(TEXT_VERSIONS, name + '.csv'))
            if os.path.isfile(p)]
    return out


def resolve(spec):
    """把用户给的东西解析成 ``[(kind, path)]`` (找不到返回 [])。

    kind ∈ ``txt`` (合并 TXT) / ``tables`` (多表里的一张, 会读同组全部) /
    ``csv`` (一张表/老的大表) / ``iso`` (临时 dump)。
    """
    cands = []
    if os.path.exists(spec):
        if os.path.isdir(spec):
            b = os.path.basename(os.path.abspath(spec))
            inner = os.path.join(spec, 'text') if os.path.isdir(os.path.join(spec, 'text')) else spec
            cands.append(('txt', os.path.join(inner, b + '_text.txt')))
            cands += [('tables', p) for p in table_set_paths(inner)]
            cands += [('txt', os.path.join(spec, b + '_text.txt')),
                      ('csv', os.path.join(inner, b + '_text.csv')),
                      ('csv', os.path.join(spec, b + '_text.csv')),
                      ('iso', os.path.join(spec, b + '.iso'))]
        else:
            low = spec.lower()
            if low.endswith('.iso'):
                cands.append(('iso', spec))
            elif T.is_table_csv(spec):                 # 给的是多表里的一张 ⇒ 读同组全部
                cands.append(('tables', spec))
            elif low.endswith('.csv'):
                cands.append(('csv', spec))
            else:
                cands.append(('txt', spec))
    b = os.path.basename(spec.replace('\\', '/'))
    cands += snapshot_candidates(b)
    found, seen = [], set()
    for kind, p in cands:
        ap = os.path.abspath(p)
        if os.path.isfile(ap) and ap not in seen:
            seen.add(ap)
            found.append((kind, ap))
    return found


def load_side(spec):
    cands = resolve(spec)
    if not cands:
        raise SystemExit(
            '!! 找不到版本 %r —— 试过这些位置:\n'
            '     work/builds/<名>/text/<名>_text.txt            ← 合并 TXT (本轮正式位置)\n'
            '     work/builds/<名>/text/<名>_text_<kind>.csv     ← ★ 多表 (会合并后比对)\n'
            '     work/builds/<名>/text/<名>_text.csv            ← round36 的合并大表\n'
            '     work/builds/<名>/<名>_text.txt|.csv            ← 旧布局\n'
            '     work/builds/<名>/<名>.iso                      ← 给 ISO 会临时 dump\n'
            '     work/text_versions/<名>_text.txt|.csv          ← 更早的归档 (只读兜底)\n'
            '   现有快照可用 --list 列出。' % spec)
    kind, p = cands[0]
    if kind == 'tables':
        base = os.path.basename(T.table_base(p))                 # 例: GR_ZH92_text
        label = base[:-len('_text')] if base.endswith('_text') else base
    else:
        label = os.path.basename(p)
        for pat in ('_text.txt', '_text.csv', '.iso'):
            if label.lower().endswith(pat):
                label = label[:-len(pat)]
                break
    if not label:
        label = os.path.basename(p)
    if kind == 'iso':
        return load_iso(p, label)
    if kind == 'tables':
        paths = [q for (k, q) in cands if k == 'tables']
        return load_tables(paths, label)
    if kind == 'csv':
        return load_csv(p, label)
    s = load_txt(p, label)
    # ★ round37: 这一版同时有多表 CSV 时, 提示"表可能比 TXT 更新"(有人改过表还没重新构筑)
    tp = table_set_paths(os.path.dirname(p))
    newer = [q for q in tp if os.path.getmtime(q) > os.path.getmtime(p) + 1]
    if newer:
        print('# [提示] %s 的多表 CSV 比合并 TXT **更新** (%d 张) ⇒ 本次仍按 TXT 比对;'
              % (label, len(newer)))
        print('#        想看表里**待注入的编辑**, 请直接把表目录或表文件当参数给它: %s'
              % rel(os.path.dirname(p)))
    return s


def list_snapshots():
    """列出所有可对比的文本快照 (版本文件夹内优先, 旧归档目录殿后并标注)。"""
    lines = []
    if os.path.isdir(BUILDS):
        for d in sorted(os.listdir(BUILDS)):
            tp = table_set_paths(os.path.join(BUILDS, d, 'text'))
            if tp:
                kinds = [T.split_table_name(p)[1] for p in tp]
                lines.append('%s   (★ 多表 %d 张: %s)' % (rel(tp[0]), len(tp), '/'.join(kinds)))
            for rel_p in (os.path.join('text', d + '_text.txt'),
                          os.path.join('text', d + '_text.csv'),
                          d + '_text.txt', d + '_text.csv'):
                p = os.path.join(BUILDS, d, rel_p)
                if os.path.isfile(p):
                    lines.append(rel(p))
    if os.path.isdir(TEXT_VERSIONS):                       # 旧归档: 只读兜底
        for fn in sorted(os.listdir(TEXT_VERSIONS)):
            if fn.endswith('_text.txt') or fn.endswith('_text.csv'):
                lines.append(rel(os.path.join(TEXT_VERSIONS, fn)) + '   (旧归档, 只读)')
    return lines


# ───────────────────────── 对比 ─────────────────────────

def shorten(s, n):
    return s if n <= 0 or len(s) <= n else s[:n] + '…(共 %d 字)' % len(s)


def show(s, n):
    """差异行的人话显示: 空行标出来 (长段里 {br}/{p} 的渲染视图会出现空行)。"""
    return '(空行)' if s == '' else shorten(s, n)


def render(A, B, limit=0, max_chars=120):
    L = []
    add = L.append
    add('# diff_text_versions.py — 两个版本的「盘内文本」对比 (只读, 不动任何 ISO/CSV)')
    add('# 生成时间 : %s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    for tag, s in (('A', A), ('B', B)):
        add('# %s = %-16s ← %s' % (tag, s.label, rel(s.path)))
        add('#     %d 条 / %d 字符 / 其中中文 %d%s'
            % (len(s.rows), s.chars, s.cjk, ('  · ' + s.note) if s.note else ''))
    add('# 对齐口径 : 按 id; 文本按「转义单行形式」比较 (换行=\\n 制表=\\t 反斜杠=\\\\)')
    if any('多表合并' in (s.note or '') for s in (A, B)):
        add('# 多表口径 : 一版的多张表 (text/<版本>_text_<kind>.csv) 已**按 id 合并**后再比对'
            ' (round37) —— 输出格式与单表时完全一致')
    add('')

    ma = {r['id']: r for r in A.rows}
    mb = {r['id']: r for r in B.rows}
    only_a = [r for r in A.rows if r['id'] not in mb]
    only_b = [r for r in B.rows if r['id'] not in ma]
    changed = [r for r in A.rows if r['id'] in mb and mb[r['id']]['key'] != r['key']]
    same = len(A.rows) - len(only_a) - len(changed)

    add('=' * 22 + ' 汇总 ' + '=' * 22)
    add('只在 A (%s) 消失 : %d 条' % (A.label, len(only_a)))
    add('只在 B (%s) 新增 : %d 条' % (B.label, len(only_b)))
    add('两边都有、内容不同 : %d 条' % len(changed))
    add('两边都有、内容相同 : %d 条' % same)
    add('条目数   %d → %d (%+d)' % (len(A.rows), len(B.rows), len(B.rows) - len(A.rows)))
    add('字符数   %d → %d (%+d)' % (A.chars, B.chars, B.chars - A.chars))
    add('中文字   %d → %d (%+d)' % (A.cjk, B.cjk, B.cjk - A.cjk))
    add('')

    def head(title, n):
        add('=' * 22 + ' %s (%d 条) ' % (title, n) + '=' * 22)

    head('修改', len(changed))
    for k, r in enumerate(changed):
        if limit and k >= limit:
            add('…(还有 %d 条, 用 --out <文件> 导出完整清单)' % (len(changed) - limit))
            break
        b = mb[r['id']]
        a_lines = [show(x, max_chars) for x in r['text'].split('\n')]
        b_lines = [show(x, max_chars) for x in b['text'].split('\n')]
        add('[~] %s%s   (A %d 行 → B %d 行)'
            % (r['id'], ('   @' + r['container']) if r['container'] else '',
               len(a_lines), len(b_lines)))
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
                None, a_lines, b_lines, autojunk=False).get_opcodes():
            if tag == 'equal':
                continue
            for x in a_lines[i1:i2]:                 # 先列 A 的旧行, 再列 B 的新行
                add('    - ' + x)
            for x in b_lines[j1:j2]:
                add('    + ' + x)
    add('')

    head('只在 B 新增', len(only_b))
    for k, r in enumerate(only_b):
        if limit and k >= limit:
            add('…(还有 %d 条)' % (len(only_b) - limit))
            break
        add('[+] %s%s' % (r['id'], ('   @' + r['container']) if r['container'] else ''))
        for x in r['text'].split('\n'):
            add('    + ' + show(x, max_chars))
    add('')

    head('只在 A 消失', len(only_a))
    for k, r in enumerate(only_a):
        if limit and k >= limit:
            add('…(还有 %d 条)' % (len(only_a) - limit))
            break
        add('[-] %s%s' % (r['id'], ('   @' + r['container']) if r['container'] else ''))
        for x in r['text'].split('\n'):
            add('    - ' + show(x, max_chars))
    add('')
    add('# 说明: [~] 修改 / [+] 只在 B / [-] 只在 A; 行首 - 是 A 的原文, + 是 B 的新文。')
    add('#       空行显示为 (空行) —— 长段文本的 dump 视图里, {br}/{p} 会渲染成空行。')
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser(description='对比两个版本的盘内文本 (只读)')
    ap.add_argument('a', nargs='?', help='版本 A: 版本名 / 快照文件 / 构筑目录 / ISO')
    ap.add_argument('b', nargs='?', help='版本 B (同 A)')
    ap.add_argument('--out', default=None, help='把完整差异报告写到这个文件 (控制台受 --limit 限制)')
    ap.add_argument('--limit', type=int, default=60,
                    help='控制台每节最多打印多少条 (0=不限; 默认 60)')
    ap.add_argument('--max-chars', type=int, default=120, help='每条最多显示多少字符 (默认 120)')
    ap.add_argument('--list', action='store_true', help='列出所有可对比的文本快照, 然后退出')
    a = ap.parse_args()

    if a.list or not a.a or not a.b:
        print('# 可对比的文本快照 (由 make_build.py 每次构筑自动产出):')
        for ln in list_snapshots():
            print('  %s' % ln)
        print('\n用法: python tools/text_csv/diff_text_versions.py <版本A> <版本B> [--out 文件]')
        return 0 if a.list else 1

    A = load_side(a.a)
    B = load_side(a.b)
    text = render(A, B, limit=a.limit, max_chars=a.max_chars)
    print(text, end='')
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        full = render(A, B, limit=0, max_chars=a.max_chars)
        with io.open(a.out, 'w', encoding='utf-8', newline='\n') as f:
            f.write(full)
        print('\n[out] 完整差异报告: %s (%d 行)' % (rel(a.out), full.count('\n')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
