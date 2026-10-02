# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: C:/gr_build/tmp/slus_scan/font_parse.py (逐字复制)。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""font_rsfb_engine.bin (= FONT.RES 解压体) 解析器 —— 与 SLUS_206.13 ReadResourceFile(0x219380)
   / RSFont::ReadResource(0x21AB50) 的流式 wire format 一一对应。实证：7222B 全部消费。

wire format:
  u32 strlen; char name[strlen]                 纹理文件名
  u32 faceCount
  每 face: u32 len; char name[len]
           u32 charWidth, charHeight, gridWidth, gridHeight,
               columns, rows,
               f32 texStartX, texStartY, texWidth, texHeight,
               u32 texOffsetX, texOffsetY, startChar, lineHeight
           u8 rec[columns*rows][10] = {u8 pad, u8 advance, u16 u0, v0, u1, v1}   (半像素单位)
  u32 styleCount
  每 style: u32 len; char id[len]
            i32 charWidth, charHeight, spaceWidth, kerningOffset
            u8  fixedWidth
            f32 scaleX, scaleY
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = open(os.path.join(REPO_ROOT, 'docs', 'han_v2', 'artifacts', 'font_rsfb_engine.bin'), 'rb').read()
p = 0
ln = struct.unpack_from('<I', D, p)[0]; p += 4
tex = D[p:p+ln].decode(); p += ln
nfaces = struct.unpack_from('<I', D, p)[0]; p += 4
print("texture=%s  faces=%d" % (tex, nfaces))
FIELD_ORDER = [0x08,0x0C,0x10,0x14,0x00,0x04,0x30,0x34,0x28,0x2C,0x18,0x1C,0x20,0x24]
FN = {0x00:'mColumns',0x04:'mRows',0x08:'mCharWidth',0x0C:'mCharHeight',0x10:'mGridWidth',
      0x14:'mGridHeight',0x18:'mTextureOffsetX',0x1C:'mTextureOffsetY',0x20:'mStartChar',
      0x24:'mLineHeight',0x28:'mTextureWidth',0x2C:'mTextureHeight',0x30:'mTextureStartX',0x34:'mTextureStartY'}
faces = []
for f in range(nfaces):
    nl = struct.unpack_from('<I', D, p)[0]; p += 4
    name = D[p:p+nl].decode(); p += nl
    fd = {}
    for off in FIELD_ORDER:
        fd[off] = struct.unpack_from('<I', D, p)[0]; p += 4
    f32 = lambda o: struct.unpack_from('<f', struct.pack('<I', fd[o]))[0]
    n = fd[0x00]*fd[0x04]
    recs = [D[p+i*10:p+i*10+10] for i in range(n)]; p += n*10
    print("face[%d] '%s': cols=%d rows=%d charW=%d charH=%d grid=%dx%d startChar=%d lineH=%d tex=%.0fx%.0f start=%.0f,%.0f off=%d,%d nrec=%d" % (
        f, name, fd[0x00], fd[0x04], fd[0x08], fd[0x0C], fd[0x10], fd[0x14], fd[0x20], fd[0x24],
        f32(0x28), f32(0x2C), f32(0x30), f32(0x34), fd[0x18], fd[0x1C], n))
    us = [struct.unpack_from('<HHHH', r, 2) for r in recs]
    print("   advance(b1) range %d..%d ; u0 %d..%d v0 %d..%d u1 %d..%d v1 %d..%d (半像素)" % (
        min(r[1] for r in recs), max(r[1] for r in recs),
        min(u[0] for u in us), max(u[0] for u in us), min(u[1] for u in us), max(u[1] for u in us),
        min(u[2] for u in us), max(u[2] for u in us), min(u[3] for u in us), max(u[3] for u in us)))
    faces.append((name, fd, recs))
nstyles = struct.unpack_from('<I', D, p)[0]; p += 4
print("styles=%d" % nstyles)
for i in range(nstyles):
    nl = struct.unpack_from('<I', D, p)[0]; p += 4
    sid = D[p:p+nl].decode(); p += nl
    w, h, sw, ko = struct.unpack_from('<iiii', D, p); p += 16
    fixed = D[p]; p += 1
    sx, sy = struct.unpack_from('<ff', D, p); p += 8
    print("  style[%d] id='%-8s' charWidth=%d charHeight=%d spaceWidth=%d kerningOffset=%d fixed=%d scale=%.3f/%.3f" % (
        i, sid, w, h, sw, ko, fixed, sx, sy))
print("consumed %d of %d bytes: %s" % (p, len(D), p == len(D)))
