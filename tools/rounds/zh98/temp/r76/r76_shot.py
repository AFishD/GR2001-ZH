# -*- coding: utf-8 -*-
"""r76_shot.py - READ-ONLY: pull the embedded Screenshot.png out of each .p2s."""
import os
import sys

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
sys.path.insert(0, os.path.join(REPO, "tools", "iso_build"))
import fix_zh116_p2s as R  # noqa: E402

OUT = os.path.join(REPO, "work", "builds", "GR_ZH98", "temp", "r76", "shots")

STATES = [
    ("zh0949", os.path.join(REPO, "work", "temp", "NEW_Mem", "SLUS-20613 (7A361FB5).01.p2s")),
    ("zh0949backup", os.path.join(REPO, "work", "temp", "NEW_Mem", "SLUS-20613 (7A361FB5).01.p2s.backup")),
    ("zh1042", os.path.join(REPO, "work", "temp", "NEW_Mem", "sstate_1042", "SLUS-20613 (7A361FB5).01.p2s")),
    ("zh1042backup", os.path.join(REPO, "work", "temp", "NEW_Mem", "sstate_1042", "SLUS-20613 (7A361FB5).01.p2s.backup")),
    ("en180", r"C:\Users\84363\AppData\Local\PCSX2\sstates\SLUS-20613 (3E571E95).10.p2s"),
    ("en470", r"C:\Users\84363\AppData\Local\PCSX2\sstates\SLUS-20613 (3E571E95).01.p2s"),
    ("en470backup", r"C:\Users\84363\AppData\Local\PCSX2\sstates\SLUS-20613 (3E571E95).01.p2s.backup"),
    ("en_slot2", r"C:\Users\84363\AppData\Local\PCSX2\sstates\SLUS-20613 (3E571E95).02.p2s"),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    for tag, p in STATES:
        if not os.path.isfile(p):
            print("%-14s MISSING %s" % (tag, p))
            continue
        try:
            b = R.read_entry(p, "Screenshot.png")
        except Exception as e:  # noqa: BLE001
            print("%-14s ERR %s" % (tag, e))
            continue
        o = os.path.join(OUT, tag + ".png")
        with open(o, "wb") as f:
            f.write(b)
        print("%-14s %8d B -> %s" % (tag, len(b), o))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
