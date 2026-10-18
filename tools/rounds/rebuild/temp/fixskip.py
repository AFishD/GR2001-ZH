import io
import os

p = os.path.abspath(r'work\builds\GR_REBUILD\tools\rb_verify_k2.py')
t = io.open(p, encoding='utf-8').read()

REP = [
    # 基底盘 (GR_ZH124) 与来源盘 (GR_F364) 均已丢失 ⇒ 与基底/来源盘对比的段落自动跳过，
    # 只保留「不依赖已丢失输入」的全部判据（几何/保留槽/借槽/allpat/文本引用槽）。
    ("    fb = open_font(a.base)",
     "    fb = None if os.environ.get('RB_NO_BASE') else open_font(a.base)"),
    ("    live_bad = []\n    for s in range(LIVE_HI + 1):",
     "    live_bad = []\n    for s in (range(LIVE_HI + 1) if fb is not None else ()):"),
    ("    f8 = open_font(R84_SRC)\n    bad_r84 = []\n    for s in range(R84_LO, R84_HI + 1):",
     "    f8 = None\n    bad_r84 = []\n    for s in (range(R84_LO, R84_HI + 1) if f8 is not None else ()):"),
    ("    ftb = b''.join(s[0] for s in T.lzo_subs(fb['ft_slot']))\n"
     "    faces_b, _ = zx_lib.ft_records(ftb, 28)",
     "    ftb = (b''.join(s[0] for s in T.lzo_subs(fb['ft_slot']))\n"
     "           if fb is not None else b'')\n"
     "    faces_b, _ = (zx_lib.ft_records(ftb, 28) if fb is not None else ([], 0))"),
    ("    for (fn, fld, rows) in faces_b:",
     "    for (fn, fld, rows) in (faces_b if fb is not None else ()):"),
]
for old, new in REP:
    assert old in t, 'anchor not found: %r' % old[:60]
    t = t.replace(old, new, 1)

# 段落说明
t = t.replace("    # ── [3] 独立读回: 三闸门 + 全槽可寻址 ──",
              "    # ── [3] 独立读回: 三闸门 + 全槽可寻址 ──\n"
              "    # RB_NO_BASE=1 ⇒ 跳过「与已丢失基底盘/来源盘对比」的段落 (GR_ZH124 / GR_F364 已不存在)")
io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('patched', p)
