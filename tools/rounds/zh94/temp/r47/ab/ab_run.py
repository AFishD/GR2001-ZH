# -*- coding: utf-8 -*-
r"""ab_run.py — round47 实机 A/B 的**自适应**抓帧器 (drawlog 实时判定 + 不对就掐掉重来)。

背景: "数按键次数"的 nav 会漂移 (同一份 nav 在不同轮落到「统计」/「选项」/「特别收录」)。
对策: 让模拟器把**每帧绘制文本**写进 drawlog (`-grdrawwin`), 我边跑边读:
  · 一旦 drawlog 里出现目标长文页特征 (「何为幽灵」/正文), 判定命中 ⇒ 让它跑满 --frames;
  · 跑到 --verify-after 帧还没命中 ⇒ 立刻掐掉, 换参数重试 (只损失 ~2-3 分钟)。

用法:
  python ab_run.py --iso <盘> --dump <名字> --k 3 --j 5 --frames 32000
                   [--verify-after 8000] [--keep] [--order 3,2,4,1,5]
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
LOG = os.path.join(AB, 'ab_run.log')

sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                       # noqa: E402

CS = tcslib.Charset()

TARGET = ['何为幽灵', '幽灵行动中', '顶级步兵部队', '特种部队群']
PAGE_SIGS = [
    ('DOC(目标长文页)', ['何为幽灵']),
    ('DOC_BODY(目标正文)', ['幽灵行动中', '顶级步兵部队']),
    ('特别收录列表', ['影片', '设定图', '屏幕截图', '预告片']),
    ('勋章/奖励页', ['勋章', '国会最高勋章', '优异服役十字']),
    ('武器页', ['武器', '手枪', '突击步枪']),
    ('选项页', ['游戏玩法', '控制器', '灵敏度']),
    ('主菜单', ['战术演习', '快速任务', '多人游戏', '制作组']),
    ('选择文件', ['选择你的档案', '新建档案', '新规']),
    ('统计页', ['统计', '歼灭战']),
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
        log('%s: 空场确认 %d/%d' % (tag, ok, need))
        if ok < need:
            time.sleep(30)


def mk_nav(path, k, j):
    L = ['# ab_run 生成: 主菜单 up×%d (环绕到特别收录), 特别收录列表 down×%d (到背景)' % (k, j)]

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
    short(t + 300, 'cross')
    t2 = t + 1800
    for _ in range(j):
        short(t2, 'down')
        t2 += 200
    short(t2 + 300, 'cross')
    t3 = t2 + 1300
    for _ in range(6):
        short(t3, 'down')
        t3 += 400
    io.open(path, 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
    return t3


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


def tail_texts(p, maxbytes=400000):
    """只读 drawlog 尾部, 返回 (最后帧号, 文本列表)。★ 运行中该文件被模拟器独占锁定,
    读不到就返回空 (实测: 只能在进程结束后读)。"""
    if not os.path.isfile(p):
        return 0, []
    try:
        sz = os.path.getsize(p)
        with io.open(p, 'rb') as f:
            if sz > maxbytes:
                f.seek(sz - maxbytes)
                f.readline()
            data = f.read().decode('utf-8', 'replace')
    except (PermissionError, OSError):
        return 0, []
    lastf, texts = 0, []
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
            texts.append(t)
    return lastf, texts


def classify(texts):
    blob = '\x00'.join(texts)
    return [n for n, ks in PAGE_SIGS if any(k in blob for k in ks)]


def hit(texts):
    blob = '\x00'.join(texts)
    return any(k in blob for k in TARGET)


def run_attempt(iso, dump, k, j, frames, verify_after, keep=False):
    os.makedirs(dump, exist_ok=True)
    for f in os.listdir(dump):
        p = os.path.join(dump, f)
        if f.startswith('snap_') or f in ('drawlog.txt', 'grlog.txt', 'cdvd.log'):
            os.remove(p)
    mc = os.path.join(AB, 'mc_%s' % os.path.basename(dump))
    os.makedirs(mc, exist_ok=True)
    for f in ('Mcd001.ps2', 'Mcd002.ps2'):
        shutil.copy2(os.path.join(MC_TPL, f), os.path.join(mc, f))
    nav = os.path.join(AB, 'nav_%s_k%d_j%d.txt' % (os.path.basename(dump), k, j))
    mk_nav(nav, k, j)
    args = [GS, '-grdumpdir', dump, '-grdrawwin', '4000', str(frames),
            '-grscanframes', '2000', '-grsnap', '100', '-grmaxframes', str(frames),
            '-grmemcards', mc, '-grinput', nav, '-renderer', 'dx11', '--', iso]
    logfile = io.open(os.path.join(AB, 'run_%s.log' % os.path.basename(dump)),
                      'a', encoding='utf-8', newline='\n')
    logfile.write('--- %s k=%d j=%d frames=%d 启动 ---\n' % (dump, k, j, frames))
    logfile.flush()
    log('启动: dump=%s k=%d j=%d frames=%d' % (os.path.basename(dump), k, j, frames))
    p = subprocess.Popen(args, cwd=os.path.dirname(GS), stdout=logfile,
                         stderr=subprocess.STDOUT)
    dl = os.path.join(dump, 'drawlog.txt')
    ok = False
    t0 = time.time()
    while p.poll() is None:
        time.sleep(10)
        lastf, texts = tail_texts(dl)
        if texts and hit(texts):
            if not ok:
                log('  ★ 命中目标长文页 (k=%d j=%d, 帧≈%d) ⇒ 让它跑完' % (k, j, lastf))
            ok = True
        elif not ok and lastf >= verify_after and not keep:
            pages = classify(texts)
            log('  ✗ 到 f%d 仍未命中; 当前页面判定=%s ⇒ 掐掉, 换参数' % (lastf, pages))
            try:
                p.kill()
            except Exception:                                      # noqa: BLE001
                pass
            logfile.write('--- 未命中, 已在 f%d 掐掉 ---\n' % lastf)
            logfile.close()
            return False, pages
    rc = p.wait()
    logfile.write('--- 结束 rc=%s 用时 %.0fs ---\n' % (rc, time.time() - t0))
    logfile.close()
    lastf, texts = tail_texts(dl)
    pages = classify(texts)
    n = len([x for x in os.listdir(dump) if x.startswith('snap_')])
    log('结束: dump=%s k=%d j=%d rc=%s 帧数=%d 末帧=%d 命中=%s 页面=%s'
        % (os.path.basename(dump), k, j, rc, n, lastf, ok or hit(texts), pages))
    return (ok or hit(texts)), pages


def main():
    a = sys.argv[1:]
    iso = a[a.index('--iso') + 1]
    dump = a[a.index('--dump') + 1]
    if not os.path.isabs(dump):
        dump = os.path.join(AB, dump)
    frames = int(a[a.index('--frames') + 1]) if '--frames' in a else 32000
    verify_after = int(a[a.index('--verify-after') + 1]) if '--verify-after' in a else 9000
    keep = '--keep' in a
    ks = [int(v) for v in (a[a.index('--order') + 1].split(',') if '--order' in a else ['3'])]
    js = [int(v) for v in (a[a.index('--js') + 1].split(',') if '--js' in a else ['5'])]
    log('=== ab_run: iso=%s dump=%s frames=%d k=%s j=%s ==='
        % (os.path.basename(iso), os.path.basename(dump), frames, ks, js))
    for k in ks:
        for j in js:
            wait_free('%s k%d j%d' % (os.path.basename(dump), k, j))
            ok, pages = run_attempt(iso, dump, k, j, frames, verify_after, keep)
            if ok:
                log('★★ 成功: dump=%s 用 k=%d j=%d (页面=%s)' % (dump, k, j, pages))
                return
    log('=== ab_run 结束: 全部候选都没命中 ===')


if __name__ == '__main__':
    main()
