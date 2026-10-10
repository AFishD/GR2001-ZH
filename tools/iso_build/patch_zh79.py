# -*- coding: utf-8 -*-
r"""patch_zh79.py — 回退 EN_SPECIAL_FEATURE.XML 的 name 翻译 (GR_ZH79, 修 GR_ZH78 回归)

根因 (100% 确认, work/_dis/dump_sf_keys.py):
  引擎在 **ELF @0x4776F0 起硬编码了 studio 名白名单**:
    ConceptSketches / Background / Movies / Music / Weapon / Awards /
    BackStory / SpecialistProfile / Interview / GameTrailer
  XML 解析器用 **strcmp(name属性值, 白名单串)** 判定 studio 类型。
  GR_ZH78 把 51 个 name 译成中文 → **strcmp 全部失败** → 所有 studio 类型未识别
  → 解锁/内容标志全 0 → 特别收录列表**全部按未解锁渲染 (全灰)、无当前选中项**
  → 方向键无可移动目标 (只能三角返回)。用户实测截图症状完全吻合。
  **与 GR_ZH72/ZH77 无关 (它们 name 仍是英文, 故正常)。**

本补丁:
  1. 把 `EN_SPECIAL_FEATURE.XML` (#283) 的 51 个 name 属性**恢复为英文原名** ——
     做法 = 从 GR_ZH77 (回归前状态) 取该条目字节, 原样写回;
  2. 其余一律不动 (GR/DS 前缀文案 G58.I724-727 的 RES 修复**保留**, 那是独立且正确的改动)。
  教训: **引擎内部比较键 (硬编码白名单/不可见文本) 绝对不可翻译** (同 ZH70 兵种键教训)。

用法: python patch_zh79.py <src_iso> <dst_iso>   (基底 = GR_ZH78)
"""
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
MENU_LBA = 776286
TAB_OFF, TAB_STEP = 0x830, 48
XML_IDX = 283
REF_ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH77', 'GR_ZH77.iso')


def entry(d, idx, lba=MENU_LBA):
    base = lba * 2048
    r = struct.unpack_from('<12I', d, base + TAB_OFF + TAB_STEP * idx)
    return base, r[6], r[7], r[8]


def main(src, dst):
    ref = open(REF_ISO, 'rb').read()
    rbase, rstored, rreal, roff = entry(ref, XML_IDX)
    ref_blob = ref[rbase + roff:rbase + roff + rstored]
    print('[ref] GR_ZH77 XML 条目 %d B (槽 %d)' % (len(ref_blob), rstored))

    sd = open(src, 'rb').read()
    base, stored, real, off = entry(sd, XML_IDX)
    assert stored == rstored and real == rreal, '条目尺寸不符'
    cur = sd[base + off:base + off + stored]
    if cur == ref_blob:
        print('[skip] 已与 ZH77 一致, 无需回退')
        return

    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(base + off)
        f.write(ref_blob)
        f.seek(base + off)
        assert f.read(stored) == ref_blob, '回写校验失败'
    print('[xml] 已恢复 ZH77 的 XML 字节 (%d B, name 全部英文)' % len(ref_blob))

    a, b = open(src, 'rb').read(), open(dst, 'rb').read()
    assert len(a) == len(b)
    mbase = MENU_LBA * 2048
    assert a[mbase:mbase + TAB_OFF] == b[mbase:mbase + TAB_OFF], 'MENU 头部被改'
    assert a[mbase + TAB_OFF:mbase + TAB_OFF + TAB_STEP * 700] == \
        b[mbase + TAB_OFF:mbase + TAB_OFF + TAB_STEP * 700], 'MENU 条目表被改'
    print('[verify] MENU 头部 + 条目表 未动 ✓')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1], sys.argv[2])
