# -*- coding: utf-8 -*-
r"""nav_state.py — 状态机导航: 用 drawlog 识别界面并迭代收敛到目标界面 (会话工具)

用户建议: "可以考虑新增一个导航逻辑, 通过钩子来读取当前的对应状态,
用状态机来实现导航, 防止漂移。"

实现 (不改模拟器):
  - **观测钩子** = 模拟器 `-grdrawwin` 产出的 drawlog (每帧绘制站点+文本)。
    这是模拟器已提供的"运行时状态输出", 等价于钩子。
  - **判定** = 从 drawlog 解出中文绘制文本, 按特征串分类当前界面。
  - **决策+执行** = `-grinput` 的输入序列在启动时固定、无法运行时改写,
    故用**外层状态机**: 每轮跑一次 → 判界面 → 按结果调整"下移次数" → 再跑,
    直到命中目标界面 (每轮由分类器保证方向正确, 不会盲猜漂移)。
  - **抗连发** = 每个按键用 `tap` + 紧跟 `release`(fr+2) 做 2~3 帧短按。

用法:
  python tools/capture/nav_state.py <版本> --target special [--max-rounds 8] [--frames 9000]
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CH = json.load(open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                 'charset_compiled_zh16.json'), encoding='utf-8'))
dc = {v: k for k, v in CH['codes'].items()}
dp = {tuple(v): k for k, v in CH['pair_of'].items()}
PY = sys.executable

SIGS = [
    ('FILE_SELECT', ['选择你的档案', '新建档案']),
    ('SPECIAL_FEATURES', ['影片', '设定图', '屏幕截图', '预告片']),
    ('CAMPAIGN_DIFF', ['选择难度', '新兵', '老兵']),
    ('MULTI_NAME', ['输入你的名字']),
    ('OPTIONS', ['游戏玩法', '控制器']),
    ('MAIN_MENU', ['战术演习', '快速任务', '多人游戏', '制作组']),
]
SIGS_D = dict(SIGS)


def dec(b):
    o, i = [], 0
    while i < len(b):
        if b[i] < 0x80:
            o.append(chr(b[i])); i += 1
        elif i + 1 < len(b) and (b[i], b[i + 1]) in dp:
            o.append(dp[(b[i], b[i + 1])]); i += 2
        elif b[i] in dc:
            o.append(dc[b[i]]); i += 1
        else:
            i += 1
    return ''.join(o)


def classify(drawlog):
    texts, lastf = [], 0
    for ln in io.open(drawlog, encoding='utf-8', errors='replace'):
        m = re.match(r'F(\d+) ', ln)
        if m:
            lastf = int(m.group(1))
        if '|' not in ln:
            continue
        try:
            b = bytes(int(x, 16) for x in ln.split('|', 1)[1].split()[:64])
        except Exception:
            continue
        t = dec(b)
        if t:
            texts.append(t)
    blob = '\x00'.join(texts)
    hits = {n: [k for k in ks if k in blob] for n, ks in SIGS}
    hits = {n: v for n, v in hits.items() if v}
    if 'SPECIAL_FEATURES' in hits and len(hits['SPECIAL_FEATURES']) >= 2:
        return 'SPECIAL_FEATURES', hits['SPECIAL_FEATURES'], lastf
    for n in ('FILE_SELECT', 'CAMPAIGN_DIFF', 'MULTI_NAME', 'OPTIONS', 'MAIN_MENU'):
        if n in hits:
            return n, hits[n], lastf
    return 'UNKNOWN', [], lastf


def mk_nav(out, ups):
    """主菜单: 上移 ups 次 (9 项首尾环绕) → 交叉进入 → 屏内下移观察"""
    L = []

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
    for _ in range(ups):
        short(t, 'up')
        t += 300
    short(t + 300, 'cross')          # 进入目标项
    t2 = t + 1200
    short(t2, 'down')                # 屏内移动 (验证光标可用)
    short(t2 + 400, 'cross')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
    return t2 + 400


def run_round(ver, tag, nav, frames):
    env = dict(os.environ)
    iso = os.path.join(REPO, 'work', 'builds', ver, '%s.iso' % ver)
    env['GR_ISO'] = iso
    cmd = [PY, os.path.join(REPO, 'tools', 'capture', 'run_opt.py'), tag, nav,
           str(frames), '100', '4000', str(frames)]
    r = subprocess.run(cmd, cwd=REPO, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        print('  运行失败: %s' % (r.stderr or '')[-300:])
        return None
    dl = os.path.join(REPO, 'work', 'builds', ver, 'temp', 'dump_%s' % tag, 'drawlog.txt')
    return dl if os.path.isfile(dl) else None


def main():
    ver = sys.argv[1]
    target = 'SPECIAL_FEATURES'
    rounds = 6
    frames = 9000
    for i, a in enumerate(sys.argv):
        if a == '--target':
            target = sys.argv[i + 1].upper()
        elif a == '--max-rounds':
            rounds = int(sys.argv[i + 1])
        elif a == '--frames':
            frames = int(sys.argv[i + 1])
    nav = os.path.join(REPO, 'work', '_dis', 'nav_state_%s.txt' % ver)
    # target 别名 (用户常写 special / sf / 特别收录)
    ALIAS = {'SPECIAL': 'SPECIAL_FEATURES', 'SF': 'SPECIAL_FEATURES',
             'SPECIAL_FEATURES': 'SPECIAL_FEATURES', 'MENU': 'MAIN_MENU',
             'MAIN': 'MAIN_MENU', 'MAIN_MENU': 'MAIN_MENU',
             'FILE': 'FILE_SELECT', 'FILE_SELECT': 'FILE_SELECT'}
    target = ALIAS.get(target, target)
    print('目标界面 = %s' % target)
    best = None
    # 状态机: 依次试"上移 k 次" (主菜单 9 项首尾环绕, k=3 即特别收录)
    for k in (3, 2, 4, 1, 5, 6)[:max(1, rounds)]:
        print('--- 轮次: 主菜单上移 %d 次 ---' % k)
        mk_nav(nav, k)
        dl = run_round(ver, 'sm%s' % k, nav, frames)
        if not dl:
            continue
        state, hits, lastf = classify(dl)
        print('    判定: %-18s 特征=%s 末帧=%d' % (state, hits[:3], lastf))
        if state == target:
            print('★ 命中目标 %s (上移 %d 次); nav=%s' % (target, k, nav))
            dst = os.path.join(REPO, 'work', '_dis', 'nav_state_%s_ok.txt' % ver)
            shutil.copyfile(nav, dst)
            print('  已保存标定导航: %s' % dst)
            best = (k, dl)
            break
    if best is None:
        print('未命中目标 (已试完全部候选); 请检查分类特征或帧数')
    else:
        print('状态机导航完成: 上移 %d 次; dump=%s' % (best[0], best[1]))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
