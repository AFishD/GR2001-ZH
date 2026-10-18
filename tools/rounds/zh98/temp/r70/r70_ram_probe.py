# -*- coding: utf-8 -*-
r"""r70_ram_probe.py — 从即时存档里解出 EE RAM 并做若干探针

用途: 崩溃复现任务（a4a335cb）的辅助静态分析。
  · 解 .p2s 里的 eeMemory.bin / iopMemory.bin (zstd, zip method 93)
  · 探针1: 搜各代特有字符串 ⇒ 判定用户跑的是哪一代盘
  · 探针2: 搜"战后回顾"当前屏的字符串 ⇒ 确认卡死时屏幕状态
  · 探针3: 搜加载/存档相关提示串 ⇒ 看是否有被截断/写坏的痕迹
  · 探针4: 统计中文串分布 (按解码器的 pair 表解出)
只读存档; 输出到 work/builds/GR_ZH98/temp/r70/ram/
"""
import io
import json
import os
import re
import sys
import zipfile

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
P2S = os.path.join(REPO, 'work', 'temp', 'SLUS-20613 (7A361FB5).01.p2s')
OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r70', 'ram')
os.makedirs(OUT, exist_ok=True)

import zstandard as zstd  # noqa: E402

z = zipfile.ZipFile(P2S)


def read_entry(name):
    info = z.getinfo(name)
    raw = z.open(name).read()          # 压缩数据
    if info.compress_type == 0:
        return raw
    d = zstd.ZstdDecompressor()
    return d.decompress(raw, max_output_size=info.file_size)


for nm in ('eeMemory.bin', 'iopMemory.bin'):
    fp = os.path.join(OUT, nm)
    if not os.path.isfile(fp):
        data = read_entry(nm)
        open(fp, 'wb').write(data)
        print('  解出 %s: %d B' % (nm, len(data)))
    else:
        print('  已有 %s' % nm)

ee = open(os.path.join(OUT, 'eeMemory.bin'), 'rb').read()
iop = open(os.path.join(OUT, 'iopMemory.bin'), 'rb').read()
print('  EE RAM %d B ; IOP RAM %d B' % (len(ee), len(iop)))

# ── 解码器: 用现役 charset (1614 字) 解中文 ──
c = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                   'charset_compiled_zh16.json'), encoding='utf-8'))
pair = {(a, b): ch for ch, (a, b) in c['pair_of'].items()}
single = {v: ch for ch, v in c['codes'].items()}


def dec(b):
    o, i = [], 0
    while i < len(b):
        x = b[i]
        if x < 0x80:
            o.append(chr(x)); i += 1
        elif x in single:
            o.append(single[x]); i += 1
        elif i + 1 < len(b) and (b[i], b[i + 1]) in pair:
            o.append(pair[(b[i], b[i + 1])]); i += 2
        else:
            o.append('\ufffd'); i += 1
    return ''.join(o)


def find_zh(ram, min_run=3, limit=60):
    """找出连续中文(>=min_run 个汉字)的片段"""
    out = []
    i = 0
    n = len(ram)
    while i < n - 1:
        if (ram[i], ram[i + 1]) in pair and 0xA1 <= ram[i] <= 0xB0:
            j = i
            buf = []
            while j < n - 1 and (ram[j], ram[j + 1]) in pair and 0xA1 <= ram[j] <= 0xB0:
                buf.append(pair[(ram[j], ram[j + 1])]); j += 2
            if len(buf) >= min_run:
                out.append((i, ''.join(buf)))
                if len(out) >= limit:
                    return out
            i = j
        else:
            i += 1
    return out


print()
print('=== 探针1: 各代特有字符串（判定盘代）===')
probes = {
    'GR_ZH111 缩减版 T0062 开头': '斯科特',
    'GR_ZH109 丰富版 T0062 开头': '伊布拉信',
    'GR_ZH114 改过的标题': '荒漠围攻',
    'GR_ZH109 旧标题': '沙漠风暴',
    '当前屏(战后回顾)': '战后回顾',
    '你胜利了': '你胜利了',
    '任务目标': '任务目标',
    '难度/新兵': '新兵',
    '继续/退出': '退出',
}
for k, s in probes.items():
    try:
        b = s.encode('utf-8')     # ASCII 直通; 中文需要编码
    except Exception:
        b = b''
    # 中文用 pair 编码
    enc = bytearray()
    for ch in s:
        if ord(ch) < 0x80:
            enc.append(ord(ch))
        elif ch in c['pair_of']:
            enc += bytes(c['pair_of'][ch])
        elif ch in single:
            enc.append([v for vv, v in single.items() if vv == ch][0])
        else:
            enc = None
            break
    if enc is None:
        print('  %-28s (含 charset 外字符, 跳过)' % k)
        continue
    cnt = ee.count(bytes(enc))
    print('  %-28s EE 中出现 %4d 次' % (k, cnt))

print()
print('=== 探针2: EE RAM 里的中文串（前 40 条，>=4 字）===')
for off, s in find_zh(ee, min_run=4, limit=40):
    print('   0x%08X  %s' % (off, s[:60]))
