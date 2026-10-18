# -*- coding: utf-8 -*-
r"""round56 验收 B: 拿 font_cell_map 的**逐槽位 CSV** 断言用户要的布局。

  断言 ① 状态 = used 的行 = 1175 行, 且 slot 全部 ≤ 1174 (即在用字形 = slot 0..1174)
  断言 ② 其它状态的行 = 329 行, 且 slot 全部 ≥ 1175 (即空闲/可用格全在最末端)
  另打印逐行 (row) 的分布, 便于人眼核对"末端整块空着"。

用法: python assert_layout.py <font_cell_map.csv> [期望在用数]
"""
import csv
import io
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)


def main():
    path = sys.argv[1]
    n_used_exp = int(sys.argv[2]) if len(sys.argv) > 2 else 1175
    with io.open(path, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    slots = dict((int(r['slot']), r) for r in rows)
    assert len(rows) == 1504, '槽位数 %d ≠ 1504' % len(rows)
    used = sorted(s for s, r in slots.items() if r['status'] == 'used')
    free = sorted(s for s, r in slots.items() if r['status'] != 'used')
    print('font_cell_map CSV: %s' % path)
    print('  在用 %d 行, 非在用 %d 行' % (len(used), len(free)))
    ok1 = (used == list(range(n_used_exp)))
    ok2 = (free == list(range(n_used_exp, 1504)))
    print('  ① 在用 = slot 0..%d ?  %s   (实测 %d..%d, 连续=%s)'
          % (n_used_exp - 1, ok1, used[0], used[-1], used == list(range(used[0], used[-1] + 1))))
    print('  ② 空闲 = slot %d..1503 ?  %s   (实测 %d..%d, 连续=%s)'
          % (n_used_exp, ok2, free[0], free[-1], free == list(range(free[0], free[-1] + 1))))
    print('  ③ 在用最大 slot %d < 空闲最小 slot %d ?  %s'
          % (used[-1], free[0], used[-1] < free[0]))
    st = {}
    for s in free:
        st[slots[s]['status']] = st.get(slots[s]['status'], 0) + 1
    print('  空闲格状态构成: %s' % st)
    fb = {}
    for s in free:
        fb.setdefault(s // 62, []).append(s % 62)
    print('  空闲格按网格行 (row): %s' % dict((k, len(v)) for k, v in sorted(fb.items())))
    ub = {}
    for s in used:
        ub.setdefault(s // 62, []).append(s % 62)
    print('  在用格按网格行 (row): %s' % dict((k, len(v)) for k, v in sorted(ub.items())))
    if not (ok1 and ok2 and used[-1] < free[0]):
        print('  ✗ 布局断言不过')
        return 1
    print('  ✓ 布局断言全过: **在用字形全部落在 slot 0..%d, 可用/空闲格全部落在 slot %d..1503**'
          % (n_used_exp - 1, n_used_exp))
    return 0


if __name__ == '__main__':
    sys.exit(main())
