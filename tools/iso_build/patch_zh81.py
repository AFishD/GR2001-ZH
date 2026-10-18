# -*- coding: utf-8 -*-
r"""patch_zh81.py — 特别收录 group 分栏标题汉化 (GR_ZH81, 光标安全)

探索结论 (探针实验, 同导航同帧判定首行高亮 BGR):
  | 探针 | 改动 | 首行 BGR | 判定 |
  |---|---|---|---|
  | ZH79 (基准) | 无 | [48.5 100.2 124.1] | 正常 |
  | **P4** | **只改 XML 的 41 个 group 名** | **[48.5 100.2 124.1]** | **正常** ✓ |
  | P1 | 只改 ELF 的 10 个 studio 名 | [91.5 55.5 45.8] | 异常 ✗ |
  | ZH80 | ELF + XML studio + group 全改 | [91.5 55.5 45.8] | 异常 ✗ |
  | ZH78 | 只改 XML studio + group | [91.5 55.5 45.8] | 异常 ✗ |

  → **group 名可自由汉化** (无 ELF 白名单, 纯显示文本, 已全 ELF 扫描确认);
  → **studio 名 (ELF @0x5776xx 白名单) 两侧任一被改都会断链** —— 该名字是引擎内部
    标识, 必须走"代码级英文匹配 + 中文显示"方案 (留待后续轮次), 本轮保持英文。

本补丁 = GR_ZH79 + XML 的 41 个 group 名中文化 (等长原位覆写, 不足补 0x20)。
用法: python patch_zh81.py <src_iso> <dst_iso>   (基底 = GR_ZH79)
"""
import importlib.util
import os
import re
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
from lz77_decode import lzo1x_decompress                      # noqa: E402
from lzo1x_c import compress as lzo_compress                  # noqa: E402

spec = importlib.util.spec_from_file_location('p80', os.path.join(HERE, 'patch_zh80.py'))
P80 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P80)
codes, pairs = P80.load_charset()
enc, entry, subs_of = P80.enc, P80.entry, P80.subs_of
GROUP_ZH = P80.GROUP_ZH
XML_IDX = P80.XML_IDX


def main(src, dst):
    sd = open(src, 'rb').read()
    shutil.copyfile(src, dst)
    base, stored, real, off = entry(sd, XML_IDX)
    subs = subs_of(sd[base + off:base + off + stored])
    assert len(subs) == 8, '子流 %d' % len(subs)
    xml = bytearray(b''.join(s[0] for s in subs))
    n = 0
    skip = []
    for m in re.finditer(rb'<(studio|group)\s+name="([^"]*)"', bytes(xml)):
        if m.group(1).decode() != 'group':
            continue                                    # studio 保持英文
        en = m.group(2).decode('latin-1')
        zh = GROUP_ZH.get(en)
        if zh is None:
            continue
        nb = enc(zh, codes, pairs)
        v0, v1 = m.start(2), m.end(2)
        if len(nb) > v1 - v0:
            skip.append((en, zh, len(nb), v1 - v0))
            continue
        xml[v0:v1] = nb + b' ' * (v1 - v0 - len(nb))
        n += 1
    print('[xml] group 名汉化 %d 处 (跳过超长 %d: %s)' % (n, len(skip), skip))
    assert n == 41, 'group 仅改 %d 处 (期望 41)' % n
    # studio 名必须保持英文 (断言)
    for m in re.finditer(rb'<studio\s+name="([^"]*)"', bytes(xml)):
        assert all(c < 0x80 for c in m.group(1)), 'studio 名被误改: %r' % m.group(1)
    print('[check] 10 个 studio 名仍为英文 ✓')

    sizes = [s[2] for s in subs]
    new_xml = bytes(xml)
    frame = bytearray()
    q = 0
    for k, S in enumerate(sizes):
        chunk = new_xml[q:q + S]
        q += S
        c = lzo_compress(chunk, level=7, use_m1=True, use_m4=True)
        back, err, _ = lzo1x_decompress(c, out_size=S)
        assert err is None and back == chunk, '子流 %d 回环失败' % k
        frame += struct.pack('<II', len(c), S) + c
    assert len(frame) <= stored, '超槽 %+d' % (len(frame) - stored)
    with open(dst, 'r+b') as f:
        f.seek(base + off)
        f.write(bytes(frame) + b'\x00' * (stored - len(frame)))
        f.seek(base + off)
        rb = subs_of(f.read(stored))
        joined = b''.join(s[0] for s in rb)
        assert joined == new_xml, '回读不符'
    print('[pack] %d B (槽 %d) 回读 ✓' % (len(frame), stored))

    a, b = open(src, 'rb').read(), open(dst, 'rb').read()
    assert len(a) == len(b)
    mbase = P80.MENU_LBA * 2048
    assert a[mbase:mbase + P80.TAB_OFF] == b[mbase:mbase + P80.TAB_OFF], 'MENU 头部被改'
    print('[verify] 尺寸/头部/条目表 未动 ✓')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1], sys.argv[2])
