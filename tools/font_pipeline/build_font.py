# -*- coding: utf-8 -*-
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..'))

r"""build_font.py — 16px 乱码根因修复: 图集绘制原点 X0 20→4
根因 (REPORT_mojibake.md): 引擎对字库纹理的 u 采样偏置随 psm 变化:
  13px PSMT8: sample(u_rec) = array(u_rec + 20)   (实测: '!' rec.u=0, 墨在 x=21)
  16px PSMT4: sample(u_rec) = array(u_rec + 4)    (实帧逐格取证: 键→你/退→和/出→会/练→键 = 期望格左移一格)
gen_font16 沿用 13px 的 X0=20 画格 (x=20+16c) 而记录/公式给 u=16c → 渲染整体左移一格 = 乱码。
修复: 格画在 x=4+16c (X0=4), 记录 u=16c 不变, cctc 公式不变, ELF 不动。
图标窗 (µ/± DrawString 硬编码 UV 采样 array(u+4)) 同步平移: src(19,198,64,221)→dst(3,198,48,221)。
y 194..242 为行距天然空档 (row<12 无跳行, row12 从 242 起), 图标窗与格零冲突。
本脚本 = gen_font16.py (subagent_16px) 的受控变体: 精确补丁 + 断言后 exec。
"""
import os, sys

HERE = os.path.join(REPO_ROOT, 'work', 'builds', 'GR_ZH62', 'font_out')
SRC = os.path.join(REPO_ROOT, 'tools', 'font_pipeline', 'gen_font16.py')

src = open(SRC, encoding='utf-8').read()

def rep(old, new, why):
    global src
    assert src.count(old) == 1, ('PATCH FAIL: %s (%d hits): %r' % (why, src.count(old), old[:80]))
    src = src.replace(old, new)
    print('[patch] %s' % why)

# 1) 绘制原点 20 → 4
rep('X0 = 20\n', 'X0 = 4\n', 'X0=4 (u 采样偏置 PSMT4=+4)')

# 2) 13px 旧图集回退字形的"源读取"必须保持 13px 自身约定 (+20), 不随新 X0 变
rep('    sx, sy = X0 + 13 * (slot % 37), yrow13(slot // 37)',
    '    sx, sy = 20 + 13 * (slot % 37), yrow13(slot // 37)',
    'render16_zh16 源读取固定 13px 约定 +20')

# 3) EN 带搬移: 源读取保持 +20; 目的写入改为 +4 (与采样偏置一致)
rep('    sx, sy = u0 + X0, v0 + 2               # ZH14 源采样顶 (452/468)',
    '    sx, dx_ = u0 + 20, u0 + X0             # sx=ZH14 源采样顶(+20); dx_=新图集目的(+4)\n    sy = v0 + 2',
    'EN 带源/目的坐标分离')
rep('    A[ty - 2:ty - 2 + 13, sx:sx + w_] = np.where(blk != 31, INK, BG)',
    '    A[ty - 2:ty - 2 + 13, dx_:dx_ + w_] = np.where(blk != 31, INK, BG)',
    'EN 带目的写入 dx_')
rep('    A[y0:y0 + 13, sx:sx + w_] = BG                  # 清格',
    '    A[y0:y0 + 13, dx_:dx_ + w_] = BG                # 清格',
    '▲▼清格 dx_')
rep('        xa = sx + (w_ - span) // 2',
    '        xa = dx_ + (w_ - span) // 2',
    '▲▼三角 dx_')

# 4) 图标窗: 源 (19,198,64,221) 逐 texel → 目的 x-16 = (3,198,48,221)
rep('ICON_BOX = (19, 198, 64, 221)        # 原位保留, 逐 texel verbatim',
    'ICON_BOX = (3, 198, 48, 221)         # 目的窗 (源 19,198,64,221 整体 x-16; u 硬编码 µ/± 采样 array(u+4))\nICON_SRC = (19, 198, 64, 221)',
    '图标窗 src/dst 分离')
rep("A[y0b:y1b, x0b:x1b] = np.where(ORIG8[y0b:y1b, x0b:x1b] != 31, INK, BG)",
    "sy0b, sx0b, sy1b, sx1b = ICON_SRC[1], ICON_SRC[0], ICON_SRC[3], ICON_SRC[2]\nA[y0b:y1b, x0b:x1b] = np.where(ORIG8[sy0b:sy1b, sx0b:sx1b] != 31, INK, BG)",
    '图标窗拷贝 src→dst')
rep("assert (A[y0b:y1b, x0b:x1b] == np.where(ORIG8[y0b:y1b, x0b:x1b] != 31, INK, BG)).all()",
    "assert (A[y0b:y1b, x0b:x1b] == np.where(ORIG8[sy0b:sy1b, sx0b:sx1b] != 31, INK, BG)).all()",
    '图标窗 verbatim 自检 src↔dst')

# 5) 产物改名, 落 mojibake 目录
rep("open(HERE + r'\\charset_compiled_v16.json', 'w', encoding='utf-8')",
    "open(HERE + r'\\charset_compiled_v16x.json', 'w', encoding='utf-8')",
    'charset json 改名')
rep("open(HERE + r'\\ft_expanded_v16.bin', 'wb').write(expanded)",
    "open(HERE + r'\\ft_expanded_v16x.bin', 'wb').write(expanded)",
    'expanded 改名')
rep("open(HERE + r'\\ft_slot_v16.bin', 'wb').write(slot)",
    "open(HERE + r'\\ft_slot_zh34.bin', 'wb').write(slot)",
    'slot 改名 zh34')
rep("open(HERE + r'\\COMMON_PAK_V16.bin', 'wb').write(pak2)",
    "open(HERE + r'\\COMMON_PAK_V16X.bin', 'wb').write(pak2)",
    'PAK 改名 V16X')
rep("Image.fromarray(prev).save(HERE + r'\\atlas_v16.png')",
    "Image.fromarray(prev).save(HERE + r'\\atlas_v16x.png')",
    'atlas png 改名')
rep("open(HERE + r'\\layout_v16.txt', 'w', encoding='utf-8')",
    "open(HERE + r'\\layout_v16x.txt', 'w', encoding='utf-8')",
    'layout 改名')

# HERE 变量: gen_font16.py 已定向输出到版本构筑夹 font_out/ (工具/数据/输出三者解耦)
assert "HERE = os.path.join(REPO_ROOT, 'work', 'builds', 'GR_ZH62', 'font_out')" in src, 'gen_font16 HERE 未定向版本夹 font_out'

os.makedirs(HERE, exist_ok=True)   # 版本夹 font_out/ 为会话产物目录 (不入库), 首跑需自建
open(os.path.join(HERE, 'gen_font16_x04.py'), 'w', encoding='utf-8').write(src)  # 衍生变体 → 会话产物目录
print('[write] gen_font16_x04.py (%d lines)' % src.count('\n'))
os.chdir(HERE)
exec(compile(src, 'gen_font16_x04.py', 'exec'), {'__name__': '__main__', '__file__': os.path.abspath(__file__)})
