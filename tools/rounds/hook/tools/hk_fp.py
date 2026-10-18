# -*- coding: utf-8 -*-
r"""hk_fp.py — 打印「fp 写点 / fp 读点」的真实指令, 确认哪些调用者把 fp 当帧指针用。
另外打印 GetActorNameAbbreviated 帧内 sp+48/56/68 缓冲区与拷贝长度来源。
"""
import io
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hk_lib as H     # noqa: E402

ZH = H.elf('ZH')
EN = H.elf('EN')

POINTS = {
    'LoadingLoagoThread': [0x20C0E8, 0x20C7DC, 0x20C870, 0x20C9C0],
    'DrawCamera': [0x23BDF8, 0x23D220, 0x23D228, 0x23D230, 0x23F1C8],
    'DrawNN': [0x2DDD08, 0x2DE000, 0x2DE874, 0x2DE878, 0x2DEC44],
    'Draw@2E7D68': [0x2E7D68, 0x2E7FE0, 0x2E7FE4, 0x2E8624],
    'DisplayMessages': [0x22DD08, 0x22E410],
    'DrawString': [0x219A78, 0x219B80, 0x219B88, 0x219C9C, 0x219D08, 0x219DC4],
}

# GetActorNameAbbreviated 帧: 0x307090 size 224; cave 用 sp+48/56
FRAME_FUNCS = [
    ('GetActorNameAbbreviated__9ActorFileCFv', 0x307090, 0x307170),
    ('GetUISoldierAbbreviateName__Fii', 0x2ECDA0, 0x2ECFB8),
]


def show(va, blob=ZH, tag='ZH'):
    o = H.va2file(va)
    w = struct.unpack_from('<I', blob.b, o)[0]
    return '%s 0x%08X  %08X  %s' % (tag, va, w, H.dis1(w, va))


def main():
    L = []
    L.append('# fp 写点/读点真实指令 (ZH113b)')
    for k, v in POINTS.items():
        L.append('')
        L.append('## %s' % k)
        for va in v:
            L.append('   ' + show(va))
            L.append('   ' + show(va, EN, 'EN'))
    L.append('')
    L.append('# GetActorNameAbbreviated / GetUISoldierAbbreviateName 全帧 sp 访问 (ZH)')
    for (nm, a, b) in FRAME_FUNCS:
        L.append('')
        L.append('## %s  0x%X..0x%X' % (nm.split('__')[0], a, b))
        for (va, rw, txt, off) in H.sp_accesses(ZH.b, a, b):
            L.append('   0x%08X %s %-28s %s' % (va, rw, txt, off))
        L.append('  -- EN --')
        for (va, rw, txt, off) in H.sp_accesses(EN.b, a, b):
            L.append('   0x%08X %s %-28s %s' % (va, rw, txt, off))
    # 帧分配大小
    L.append('')
    L.append('# 帧分配 (addiu sp,sp,-N) 相关函数')
    for va in (0x307090, 0x2ECDA0, 0x21C4C0, 0x23BDC0, 0x2DDCF0, 0x219A70):
        o = H.va2file(va)
        w = struct.unpack_from('<I', ZH.b, o)[0]
        L.append('   0x%08X  %s' % (va, H.dis1(w, va)))
    txt = '\n'.join(L)
    with io.open(os.path.join(H.EVID, 'hk_fp.txt'), 'w', encoding='utf-8') as f:
        f.write(txt)
    print(txt)


if __name__ == '__main__':
    main()
