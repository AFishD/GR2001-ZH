# -*- coding: utf-8 -*-
"""r76_mknav.py - generate the long cold-boot -> mission -> play input table.

The boot/menu frames were established empirically (see R76 report):
  800..2602   start taps  -> skip logos / "Press START"
  2720, 2840  up x2       -> "选择文件": initial highlight is 新建, up x2 -> slot 1
  3150        cross       -> load BASLUS-20613GHOST001
  3600, 3900  down x2     -> main menu: 训练 -> 战役
  4200        cross       -> campaign screen
  4700        cross       -> accept -> mission 7 loads
  ~7400                   in-level gameplay confirmed by snapshot
"""
import sys

BOOT = """# r76 long run: cold boot -> load memcard save -> campaign mission 7 -> play
800 start tap
802 start release
1000 start tap
1002 start release
1200 start tap
1202 start release
1400 start tap
1402 start release
1600 start tap
1602 start release
1800 start tap
1802 start release
2000 start tap
2002 start release
2200 start tap
2202 start release
2400 start tap
2402 start release
2600 start tap
2602 start release
2720 up tap
2722 up release
2840 up tap
2842 up release
3150 cross tap
3172 cross release
3600 down tap
3602 down release
3900 down tap
3902 down release
4200 cross tap
4222 cross release
4700 cross tap
4722 cross release
"""


def main():
    end = int(sys.argv[1]) if len(sys.argv) > 1 else 58000
    out = []
    out.append(BOOT.rstrip("\n"))
    # generic play: hold forward for a long stretch, look around, fire, repeat
    f = 7800
    i = 0
    pattern = [("up", 900), ("R1", 30), ("left", 200), ("up", 900), ("right", 200),
               ("up", 900), ("down", 200), ("up", 900), ("R1", 30), ("cross", 200)]
    while f < end:
        for (btn, hold) in pattern:
            if f >= end:
                break
            out.append("%d %s tap" % (f, btn))
            out.append("%d %s release" % (f + 20, btn))
            f += hold
            i += 1
    out.append("# %d input events" % i)
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
