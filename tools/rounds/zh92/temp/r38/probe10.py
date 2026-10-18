# -*- coding: utf-8 -*-
r"""probe10.py — 现役 charset 里"落在毒区/被 ASCII 分支遮蔽"的单字节码 (观察项)

背景: 另一个子代理正在扩字库, 现役 charset 的单字节码从 76 个涨到 111 个,
      新增的 35 个落在 **0x7F..0xA0**。这里检查两件事:
        ① 0x7F: tcslib 的 decode 先走 `v < 0x80` (ASCII) 分支 ⇒ 这个码位**永远解不出**它映射的字;
        ② 0x80..0x9F: tools/hanliu/tools/text_replace.py 明确把它当**毒区**拒绝写出。
      两件事都意味着"这些字的编码写出去, 引擎/工具链读不回来"。
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import font_usage as F  # noqa: E402
import tcslib as T     # noqa: E402

CS = os.path.join(REPO, 'tools/font_pipeline/data/charset_compiled_zh16.json')
raw = json.load(io.open(CS, encoding='utf-8'))
idx = F.CharsetIndex(CS)
tcs = T.Charset(CS)

suspects = []
for ch, v in raw['codes'].items():
    b = int(v)
    if b == 0x7F:
        suspects.append((ch, b, 'DEL: decode 的 v<0x80 分支先吃掉它'))
    elif 0x80 <= b <= 0x9F:
        suspects.append((ch, b, '毒区 0x80-0x9F: text_replace.py 拒绝写出'))
    elif b == 0xA0:
        suspects.append((ch, b, '0xA0: 非 ASCII 但不在单字节码原设计区间 (0xAF..0xFE)'))
print('现役 charset 单字节码 %d 个; 其中落在 0x7F..0xA0 的 **%d 个**:'
      % (len(raw['codes']), len(suspects)))
for ch, b, why in sorted(suspects, key=lambda x: x[1]):
    # ① 解码能不能解回这个字?
    dec = tcs.decode(bytes([b]))[0]
    # ② encode_strict 的编解码对称自检能不能过?
    try:
        tcs.encode_strict(ch)
        rt = 'ok'
    except Exception as ex:                                         # noqa: BLE001
        rt = type(ex).__name__
    print('   %s U+%04X 码 0x%02X | decode(0x%02X)=%r | encode_strict=%s | %s'
          % (ch, ord(ch), b, b, dec, rt, why))

print('\n【结论】')
n7f = len([1 for _c, b, _w in suspects if b == 0x7F])
npoison = len([1 for _c, b, _w in suspects if 0x80 <= b <= 0x9F])
print('  0x7F (被 ASCII 分支遮蔽): %d 个' % n7f)
print('  0x80..0x9F (工具链毒区): %d 个' % npoison)
print('  ⇒ 这些码位上的字, **写出去之后本工程自己的解码器读不回来**;')
print('     对字库用量核算的影响: 本工具的扫描器与 tcslib 同口径 ⇒ 也看不见它们,')
print('     若这些字真的用在文本里, 会被本工具误判为"可回收"。')
print('     本工具**没有**修改这个 charset (只读); 这只是观察记录, 交 Lead 判断。')

# 这些字在盘上文本里用到了吗?
print('\n【这些字在现役盘文本里用到没有?】')
iso = T.Iso(os.path.join(REPO, 'work/builds/GR_ZH92/GR_ZH92.iso'))
e0 = set()
for c in F.build_container_list(iso):
    if c['kind'] in ('LANG', 'SFXML'):
        blob, _ = F.container_blob(iso, c)
        got = (F.parse_lang_chars(blob, idx) if c['kind'] == 'LANG'
               else F.parse_sfxml_chars(blob, idx))[0]
        if got:
            e0 |= got
for ch, b, _w in sorted(suspects, key=lambda x: x[1]):
    print('   %s 码 0x%02X: %s' % (ch, b, '在盘上文本里**出现**' if ch in e0
                                   else '没在盘上文本里出现'))
iso.close()
