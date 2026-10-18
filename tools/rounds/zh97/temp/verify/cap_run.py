# -*- coding: utf-8 -*-
r"""cap_run.py — round48 实机抓帧 (单实例守规 + 模板记忆卡复位 + drawlog 页面判定)。

铁律 (照做, 见 docs/REPORT_record_band_fix.md §4.5.7):
  · pcsx2-gsrunner **只能单实例** ⇒ 起跑前等"连续 2 次、间隔 30s 无任何实例";
  · 记忆卡**每轮从 third_party/emu/run/memcards 模板复位**到独占目录
    (自带 mc 目录 ⇒ 卡里没存档 ⇒ 走"新建档案" ⇒ 停在「输入名字」键盘屏);
  · `-grdrawwin 4000 <frames>`: 让模拟器把每帧绘制文本写进 <dump>/drawlog.txt
    (运行中被独占锁定, **只能进程结束后读**) ⇒ 跑完立刻判定"实际到了哪一页";
  · 跑完确认进程退出 (`rc`), 再起下一轮。

用法:
  python cap_run.py --iso <盘.iso> --dump <目录> --nav <nav.txt> --frames 13000
                    [--snap 100] [--require 战术演习] [--tag 名字]
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

GS = os.path.join(REPO, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
MC_TPL = os.path.join(REPO, 'third_party', 'emu', 'run', 'memcards')
LOG = os.path.join(HERE, 'cap_run.log')

import tcslib                                                       # noqa: E402

CS = tcslib.Charset()

PAGE_SIGS = [
    ('引导/载入屏', ['载入中', '快速载入中']),
    ('选择文件', ['选择你的档案', '新建档案', '新规']),
    ('输入名字(键盘屏)', ['输入', '名字', '决定']),
    ('主菜单', ['战术演习', '快速任务', '多人游戏', '制作组']),
    ('特别收录', ['影片', '设定图', '屏幕截图', '预告片']),
    ('武器页', ['武器', '手枪', '突击步枪']),
    ('勋章页', ['勋章', '国会最高勋章']),
    ('选项页', ['游戏玩法', '控制器', '灵敏度']),
    ('统计页', ['统计', '歼灭战']),
    ('DOC(何为幽灵)', ['何为幽灵', '幽灵行动中']),
]


def log(m):
    s = '%s  %s' % (time.strftime('%H:%M:%S'), m)
    print(s, flush=True)
    with io.open(LOG, 'a', encoding='utf-8', newline='\n') as f:
        f.write(s + '\n')


def emu_pids():
    out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq pcsx2-gsrunner.exe', '/NH'],
                         capture_output=True, text=True, errors='replace').stdout
    return [ln.split()[1] for ln in out.splitlines() if 'pcsx2-gsrunner' in ln]


def wait_free(tag, poll=30, need=2):
    ok = 0
    while ok < need:
        if emu_pids():
            log('%s: 检测到仿真器实例 %s ⇒ 等待' % (tag, emu_pids()))
            ok = 0
            time.sleep(poll)
            continue
        ok += 1
        log('%s: 空场确认 %d/%d' % (tag, ok, need))
        if ok < need:
            time.sleep(poll)


def dec(b):
    out, i = [], 0
    while i < len(b):
        v = b[i]
        if v < 0x80:
            out.append(chr(v)); i += 1
        elif i + 1 < len(b) and (v, b[i + 1]) in CS.pair_of:
            out.append(CS.pair_of[(v, b[i + 1])]); i += 2
        elif v in CS.codes:
            out.append(CS.codes[v]); i += 1
        else:
            i += 1
    return ''.join(out)


def read_drawlog(p):
    """返回 (末帧, [(帧, 文本)...]); 运行中被独占 ⇒ 读不到就返回 (0, [])。"""
    if not os.path.isfile(p):
        return 0, []
    try:
        with io.open(p, 'rb') as f:
            data = f.read().decode('utf-8', 'replace')
    except (PermissionError, OSError):
        return 0, []
    lastf, recs = 0, []
    for ln in data.splitlines():
        m = re.match(r'F(\d+) ', ln)
        if m:
            lastf = int(m.group(1))
        if '|' not in ln:
            continue
        try:
            b = bytes(int(x, 16) for x in ln.split('|', 1)[1].split()[:64])
        except Exception:                                          # noqa: BLE001
            continue
        t = dec(b)
        if t.strip():
            recs.append((lastf, t))
    return lastf, recs


def main():
    a = sys.argv[1:]
    iso = a[a.index('--iso') + 1]
    dump = a[a.index('--dump') + 1]
    nav = a[a.index('--nav') + 1]
    frames = int(a[a.index('--frames') + 1]) if '--frames' in a else 13000
    snap = a[a.index('--snap') + 1] if '--snap' in a else '100'
    require = a[a.index('--require') + 1] if '--require' in a else None
    tag = a[a.index('--tag') + 1] if '--tag' in a else os.path.basename(dump)
    if not os.path.isabs(dump):
        dump = os.path.abspath(dump) if os.path.isdir(os.path.dirname(os.path.abspath(dump))) \
            else os.path.join(HERE, dump)
    if not os.path.isabs(nav):
        nav = os.path.abspath(nav) if os.path.isfile(os.path.abspath(nav)) \
            else os.path.join(HERE, nav)
    iso = os.path.abspath(iso)
    assert os.path.isfile(iso), iso
    assert os.path.isfile(nav), nav

    wait_free(tag)
    if os.path.isdir(dump):
        shutil.rmtree(dump)
    os.makedirs(dump)
    mc = os.path.join(HERE, 'mc_%s' % os.path.basename(dump))
    if os.path.isdir(mc):
        shutil.rmtree(mc)
    os.makedirs(mc)
    for f in ('Mcd001.ps2', 'Mcd002.ps2'):
        shutil.copy2(os.path.join(MC_TPL, f), os.path.join(mc, f))
    log('%s: 记忆卡已从模板复位 (%s)' % (tag, mc))

    args = [GS, '-grdumpdir', dump, '-grdrawwin', '4000', str(frames),
            '-grscanframes', '2000', '-grsnap', snap, '-grmaxframes', str(frames),
            '-grmemcards', mc, '-grinput', nav, '-renderer', 'dx11', '--', iso]
    lf = io.open(os.path.join(HERE, 'run_%s.log' % tag), 'a',
                 encoding='utf-8', newline='\n')
    lf.write('--- %s iso=%s nav=%s frames=%d 启动 ---\n' % (tag, iso, nav, frames))
    lf.flush()
    log('%s: 启动 iso=%s nav=%s frames=%d snap=%s'
        % (tag, os.path.basename(iso), os.path.basename(nav), frames, snap))
    t0 = time.time()
    r = subprocess.run(args, cwd=os.path.dirname(GS), stdout=lf, stderr=subprocess.STDOUT)
    el = time.time() - t0
    lf.write('--- 结束 rc=%s 用时 %.0fs ---\n' % (r.returncode, el))
    lf.close()
    n = len([x for x in os.listdir(dump) if x.startswith('snap_')])
    lastf, recs = read_drawlog(os.path.join(dump, 'drawlog.txt'))
    blob = '\x00'.join(t for _f, t in recs)
    pages = [nm for nm, ks in PAGE_SIGS if any(k in blob for k in ks)]
    chars = [c for c in '中斗训习面务准可会出换下如以到定是任火动' if c in blob]
    log('%s: 结束 rc=%s 用时%.0fs 帧数=%d 末帧=%d' % (tag, r.returncode, el, n, lastf))
    log('%s: 页面判定=%s' % (tag, pages))
    log('%s: drawlog 里出现过的"受影响字"=%s' % (tag, chars))
    ok = (require in blob) if require else True
    log('%s: require=%r ⇒ %s' % (tag, require, '命中' if ok else '**未命中**'))
    doc = dict(tag=tag, iso=os.path.abspath(iso), iso_sha256=tcslib.sha256_file(iso),
               nav=nav, nav_sha256=tcslib.sha256_file(nav), frames=frames, snap=snap,
               rc=r.returncode, elapsed_s=round(el, 1), snaps=n, last_frame=lastf,
               pages=pages, chars_seen=chars, require=require, require_hit=bool(ok))
    io.open(os.path.join(HERE, 'cap_%s.json' % tag), 'w', encoding='utf-8',
            newline='\n').write(json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
    return 0 if (r.returncode == 0 or r.returncode is None) and ok else 1


if __name__ == '__main__':
    sys.exit(main())
