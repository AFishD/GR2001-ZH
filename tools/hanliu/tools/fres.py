# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: C:/gr_build/tmp/slus_scan/fres.py (逐字复制)。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import struct, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = open(os.path.join(REPO_ROOT, 'work', 'tmp', 'GRIMG_FONT_RES'),'rb').read()
print("size:", len(d))
print("head 128:", ' '.join('%02x'%c for c in d[:128]))
# try RSUIString: maybe {u16/u32 len, chars}
for off in (0,):
    # guess: u32 len
    ln = struct.unpack_from('<I', d, 0)[0]
    print("u32@0 =", ln, hex(ln))
    print("as text:", d[:64])
