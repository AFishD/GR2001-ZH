# r74_extract.py - READ-ONLY. Extract a named entry from a .p2s into an output file.
import os
import sys

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
sys.path.insert(0, os.path.join(REPO, "tools", "iso_build"))
import fix_zh116_p2s as R  # noqa: E402


def main():
    p2s, entry, out = sys.argv[1], sys.argv[2], sys.argv[3]
    b = R.read_entry(p2s, entry)
    with open(out, "wb") as f:
        f.write(b)
    print("%s :: %s -> %s (%d B)" % (os.path.basename(p2s), entry, out, len(b)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
