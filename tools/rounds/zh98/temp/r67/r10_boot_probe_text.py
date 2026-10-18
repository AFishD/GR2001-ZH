# -*- coding: utf-8 -*-
r"""r10_boot_probe_text.py — 造一份"主菜单探针"文本表 (给 inject_text_csv 用)。

为什么要有它
------------
`nav_hook.py` 的**引导段**是固定帧时序 (start×10 → up×3 → cross@3250), 而它在
"主菜单还没开始吃按键"的窗口里就把 up/cross 发完了 (round67 实拍: hook 一直 =1, 三次 up
一动不动) ⇒ 那条路径依赖"机器很闲、启动时序不漂"。本轮模拟器被并行任务反复抢占,
需要一条**完全不依赖按键**的取证路径。

做法: 把主菜单 9 个条目名 + 1 行条目说明**换成本轮新字**(字数与原串逐字相同),
      ⇒ 只要**开机到主菜单**截一张图, 就能同时看到 lead 0xAD/0xAE/0xAF/0xB0 四档新字。

★ 替换字**一律从 `charset_expand_zh113.csv` 按 slot 取**, 绝不手写字面量 ——
  手写的字可能不在字符集里 (第一版写了个"屠", 被注入器预检当场拦下)。

用法: python r10_boot_probe_text.py <src_text_dir> <dst_text_dir>
"""
import csv
import io
import os
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
SEL = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_expand_zh113.csv')

# (ids, 原串, 起 slot, 取几个新字, 结尾追加)
#   A 组 = 主菜单 9 个条目名 + 1 行说明 (走到主菜单才看得到)
#   B 组 = **「输入名字」页**的标题/说明/底部提示 —— 这页在**无存盘时开局自动弹出**,
#          所以 B 组是一条**完全不需要导航**就能看到的取证路径 (round67 实测最稳)
PLAN = [
    # ---- A 组: 主菜单 ----
    (['LANG:G058.I008'], '训练', 1175, 2, ''),          # AD  她父
    (['LANG:G058.I009'], '战术演习', 1222, 4, ''),        # AE
    (['LANG:G058.I011'], '快速任务', 1410, 4, ''),        # B0
    (['LANG:G058.I012'], '战役', 1316, 2, ''),          # AF
    (['LANG:G058.I013'], '多人游戏', 1318, 4, ''),        # AF
    (['LANG:G059.I036'], '统计', 1414, 2, ''),          # B0
    (['LANG:G059.I037'], '特别收录', 1178, 4, ''),        # AD  女历业狂
    (['LANG:G058.I015'], '选项', 1182, 2, ''),          # AD  刺厘
    (['LANG:G058.I017'], '制作组', 1184, 3, ''),         # AD  阶寸尺
    (['LANG:G058.I034'], '学习游戏的基本操作。', 1187, 9, '。'),   # AD
    # ---- B 组: 「输入名字」页 (自动出现, 零导航) ----
    (['LANG:G059.I019'], '输入名字', 1226, 4, ''),        # AE  标题
    (['LANG:G058.I044'], '输入你的名字。', 1230, 6, '。'),   # AE  底部说明 (6 汉字 + 。)
    (['LANG:G058.I005', 'LANG:G058.I330', 'LANG:G058.I730'], '删除', 1416, 2, ''),   # B0
    (['LANG:G058.I098', 'LANG:G058.I144', 'LANG:G058.I729', 'LANG:G058.I768'],
     '返回', 1418, 2, ''),                                                        # B0
    (['LANG:G058.I169', 'LANG:G058.I728'], '接受', 1420, 2, ''),                     # B0
    (['LANG:G058.I003', 'LANG:G058.I004'], '确认', 1422, 2, ''),                     # B0
]


def main(src_dir, dst_dir):
    sl = {}
    for r in csv.DictReader(io.open(SEL, encoding='utf-8-sig', newline='')):
        sl[int(r['slot'])] = r
    assert len(sl) == 329
    plan, shown, used_slots = {}, [], set()
    for (kids, old, lo, n, tail) in PLAN:
        chars = [sl[lo + i]['char'] for i in range(n)]
        new = ''.join(chars) + tail
        assert len(new) == len(old), (kids, new, old, len(new), len(old))
        for kid in kids:
            assert kid not in plan, '重复 id: %s' % kid
            plan[kid] = (old, new)
        for i in range(n):
            assert lo + i not in used_slots, 'slot %d 被两组计划重复使用' % (lo + i)
            used_slots.add(lo + i)
        shown.append((kids[0] + (' 等%d条' % len(kids) if len(kids) > 1 else ''),
                      old, new, lo, n))
    os.makedirs(dst_dir, exist_ok=True)
    for fn in sorted(os.listdir(src_dir)):                  # 先整体复制, 再只改 text_edited
        if fn.endswith('.csv') and '_text_' in fn:
            shutil.copyfile(os.path.join(src_dir, fn), os.path.join(dst_dir, fn))
    hit, missed = {}, set(plan)
    for fn in sorted(os.listdir(dst_dir)):
        if not fn.endswith('.csv'):
            continue
        p = os.path.join(dst_dir, fn)
        rows = list(csv.DictReader(io.open(p, encoding='utf-8-sig', newline='')))
        if not rows or 'text_edited' not in rows[0]:
            continue
        cols = list(rows[0].keys())
        for r in rows:
            if r['id'] in plan:
                old, new = plan[r['id']]
                assert r['text_edited'] == old, (r['id'], r['text_edited'], old)
                r['text_edited'] = new
                hit[r['id']] = (old, new)
                missed.discard(r['id'])
        with io.open(p, 'w', encoding='utf-8-sig', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=cols, lineterminator='\r\n')
            w.writeheader()
            w.writerows(rows)
    assert not missed, '这些 id 没在表里找到: %s' % sorted(missed)
    print('[text] 改了 %d 条串 (每个字都按 slot 从 charset_expand_zh113.csv 取):' % len(hit))
    for kid, old, new, lo, n in shown:
        print('   %-22s %-11s → %-11s  slot %d..%d' % (kid, old, new, lo, lo + n - 1))
    print('[out ] %s' % dst_dir)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
