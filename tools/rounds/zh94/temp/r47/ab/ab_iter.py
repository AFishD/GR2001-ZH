# -*- coding: utf-8 -*-
r"""ab_iter.py — round47 导航标定: 用 -grdrawwin 的 drawlog **读出实际到达的界面**, 迭代收敛到
「特别收录 → 背景 → 何为幽灵？」长文页。

为什么需要它:
  · `nav_r47.txt` 那种"数按键次数"的导航**会漂移** —— 同一个 nav 在不同轮里 5 次下移
    分别落到了「统计」(少登记 1 次) 和「选项」(多登记 1 次)。光靠猜次数到不了目标页。
  · 本脚本用模拟器自带的运行时观测钩子 (drawlog = 每帧绘制文本) 判定"到底到了哪一页",
    再用外层状态机逐个试 (主菜单上移 k 次 × 列表下移 j 次)。
  · 命中 (drawlog 里出现「何为幽灵」/正文特征) 就把这份 nav 存成标定导航, 供两轮 A/B 复用。

用法:
  python ab_iter.py <ISO路径 或 版本名> <tag前缀> [--frames 12000]
                    [--k 3,4,2] [--j 5,4,6] [--keep-going]
"""
import io
import os
import re
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
AB = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r47', 'ab')
GS = os.path.join(REPO, 'third_party', 'emu', 'pcsx2', 'pcsx2-gsrunner', 'pcsx2-gsrunner.exe')
MC_TPL = os.path.join(REPO, 'third_party', 'emu', 'run', 'memcards')
LOG = os.path.join(AB, 'ab_iter.log')

# 图集字符集 (只读) —— 用来把 drawlog 里的字节解回中文
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                       # noqa: E402

CS = tcslib.Charset()

SIGS = [
    ('DOC_WHAT_IS_GHOST', ['何为幽灵']),
    ('DOC_BODY', ['幽灵行动中', '顶级步兵部队', '特种部队群']),
    ('SPECIAL_FEATURES', ['影片', '设定图', '屏幕截图', '预告片']),
    ('MEDALS', ['勋章', '国会最高勋章']),
    ('WEAPONS', ['武器', '手枪', '步枪']),
    ('OPTIONS', ['游戏玩法', '控制器', '灵敏度']),
    ('MAIN_MENU', ['战术演习', '快速任务', '多人游戏', '制作组']),
    ('FILE_SELECT', ['选择你的档案', '新建档案', '新规']),
    ('STATS', ['统计', '任务', '歼灭战']),
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


def wait_free(tag, poll=5, need=2):
    ok = 0
    while ok < need:
        if emu_pids():
            ok = 0
            time.sleep(poll)
            continue
        ok += 1
        log('%s: 空场 %d/%d' % (tag, ok, need))
        if ok < need:
            time.sleep(30)


def mk_nav(path, k, j, frames):
    """主菜单上移 k 次 (9 项首尾环绕) → cross; 列表下移 j 次 → cross 打开条目; 页内滚动。"""
    L = ['# ab_iter 生成: 主菜单 up×%d, 特别收录列表 down×%d, maxframes=%d' % (k, j, frames)]

    def short(fr, btn):
        L.append('%d %s tap' % (fr, btn))
        L.append('%d %s release' % (fr + 2, btn))

    for f in range(800, 2700, 200):
        L.append('%d start tap' % f)
    short(2850, 'up')
    short(2950, 'up')
    short(3050, 'up')
    L.append('3250 cross tap')
    L.append('3272 cross release')
    t = 3700
    for _ in range(k):
        short(t, 'up')
        t += 300
    short(t + 300, 'cross')            # 进入「特别收录」
    t2 = t + 1800                      # 列表加载
    for _ in range(j):
        short(t2, 'down')
        t2 += 200
    short(t2 + 300, 'cross')           # 打开第 j+1 条
    t3 = t2 + 1300
    for _ in range(5):                 # 页内下移看正文
        short(t3, 'down')
        t3 += 500
    io.open(path, 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
    return t3


def dec(b):
    """与 nav_state.py 同一口径的字节→文本 (引擎 DBCS: lead 0xA1..0xB0 吞后一字节)"""
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


def parse_drawlog(p):
    texts, lastf = [], 0
    for ln in io.open(p, encoding='utf-8', errors='replace'):
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
        if t:
            texts.append((lastf, t))
    blob = '\x00'.join(t for _f, t in texts)
    hits = {n: [k for k in ks if k in blob] for n, ks in SIGS}
    hits = {n: v for n, v in hits.items() if v}
    return texts, hits, lastf


def run_one(iso, tag, nav, frames):
    dump = os.path.join(AB, 'iter_%s' % tag)
    mc = os.path.join(AB, 'iter_mc')
    if os.path.isdir(dump):
        shutil.rmtree(dump)
    os.makedirs(dump)
    os.makedirs(mc, exist_ok=True)
    for f in ('Mcd001.ps2', 'Mcd002.ps2'):
        shutil.copy2(os.path.join(MC_TPL, f), os.path.join(mc, f))
    args = [GS, '-grdumpdir', dump, '-grdrawwin', '4000', str(frames),
            '-grscanframes', '2000', '-grsnap', '100', '-grmaxframes', str(frames),
            '-grmemcards', mc, '-grinput', nav, '-renderer', 'dx11', '--', iso]
    t0 = time.time()
    with io.open(LOG, 'a', encoding='utf-8', newline='\n') as f:
        f.write('--- %s 启动 (frames=%d) ---\n' % (tag, frames))
        f.flush()
        subprocess.run(args, cwd=os.path.dirname(GS), stdout=f, stderr=subprocess.STDOUT)
    log('%s: 结束 用时 %.0fs' % (tag, time.time() - t0))
    dl = os.path.join(dump, 'drawlog.txt')
    return dl if os.path.isfile(dl) else None


def main():
    a = sys.argv[1:]
    ver_or_iso = a[0]
    tagp = a[1]
    frames = int(a[a.index('--frames') + 1]) if '--frames' in a else 12000
    ks = [int(v) for v in (a[a.index('--k') + 1].split(',') if '--k' in a else ['3'])]
    js = [int(v) for v in (a[a.index('--j') + 1].split(',') if '--j' in a else ['5'])]
    keep = '--keep-going' in a
    iso = ver_or_iso if os.path.isfile(ver_or_iso) else os.path.join(
        REPO, 'work', 'builds', ver_or_iso, '%s.iso' % ver_or_iso)
    assert os.path.isfile(iso), iso
    log('=== ab_iter start: iso=%s frames=%d k=%s j=%s ===' % (iso, frames, ks, js))
    for k in ks:
        for j in js:
            tag = '%s_k%d_j%d' % (tagp, k, j)
            nav = os.path.join(AB, 'nav_iter_%s.txt' % tag)
            mk_nav(nav, k, j, frames)
            wait_free(tag)
            dl = run_one(iso, tag, nav, frames)
            if not dl:
                log('%s: 没有 drawlog ⇒ 跳过' % tag)
                continue
            texts, hits, lastf = parse_drawlog(dl)
            log('%s: 判定 hits=%s 末帧=%d 绘制文本数=%d' % (tag, hits, lastf, len(texts)))
            uniq = []
            for _f, t in texts:
                t = t.strip()
                if t and t not in uniq:
                    uniq.append(t)
            log('   出现的文本(前 40 条): %s' % ' / '.join(uniq[:40]))
            if 'DOC_WHAT_IS_GHOST' in hits or 'DOC_BODY' in hits:
                dst = os.path.join(AB, 'nav_r47_doc_OK.txt')
                shutil.copyfile(nav, dst)
                log('★★ 命中目标长文页! 标定导航 → %s (k=%d j=%d)' % (dst, k, j))
                log('   drawlog=%s' % dl)
                return
            if not keep:
                continue
    log('=== ab_iter 结束: 未命中, 需换 k/j 再试 ===')


if __name__ == '__main__':
    main()
