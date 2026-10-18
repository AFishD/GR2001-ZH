# -*- coding: utf-8 -*-
r"""test_conservative.py — 保守性验证 (验收 #4)

证明: 「某字**只**在 .ATR 里出现」时**不会被判为可回收**。

分三层证明:
  A. 真实盘实测: 现役盘 1193 个 .ATR 解压后**一个非 ASCII 字符都没有**
     ⇒ 不存在"只在 .ATR 里出现"的真实字 (如实记录);
  B. 构造用例: 把某闲置字的对偶码字节塞进一个**真实的 .ATR** 内容里,
     走本工具的**同一个扫描函数** ⇒ 该字必须被判为"用到";
  C. 端到端: 用 B 的证据构造 usage, 走 compute_reclaim ⇒ 该字必须**不在**可回收清单里,
     且 blocked 原因里写明是 E1 文本容器证据。

另附: 对照 (positive control) —— 同一个字在**没有任何证据**时必须被判为可回收。
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import font_usage as F  # noqa: E402
import tcslib as T     # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
HERE = os.path.dirname(os.path.abspath(__file__))
idx = F.CharsetIndex()
ok = True


def chk(cond, msg):
    global ok
    ok = ok and bool(cond)
    print('%s %s' % ('[ok]' if cond else '[!!]', msg))


def blank_usage(**kw):
    u = dict(e0=set(), e1=set(), e2=set(), t3_byte=None, t3_bigram=None)
    u.update(kw)
    return u


# ── 挑一个"闲置"的字 (现役盘 LANG/SFXML 里没有的) ──
iso = T.Iso(ISO)
cs = []
for lba, tag in ((T.GR_LBA, 'GR.IMG'), (T.MENU_LBA, 'MENU.IMG')):
    cs += F.enum_img_containers(iso, lba, tag)
for c in cs:
    c['kind'] = F.classify(c['name'], c['img'], c['idx'])
    c['text'] = F.KIND_RULES[c['kind']][0]

# 用 E0 精确解析求出"在用"集合, 从中挑一个不在里面的对偶字
e0 = set()
for c in cs:
    if c['kind'] in ('LANG', 'SFXML'):
        blob, _ = F.container_blob(iso, c)
        got = (F.parse_lang_chars(blob, idx) if c['kind'] == 'LANG'
               else F.parse_sfxml_chars(blob, idx))[0]
        if got:
            e0 |= got
print('# E0 (LANG/SFXML 正文) 用到 %d 个字' % len(e0))
idle_pair = [c for c in idx.chars
             if ord(c) >= 0x80 and c not in e0 and c in idx.enc_pair
             and F.LEGAL_LEAD_LO <= idx.enc_pair[c][0] < F.LEGAL_LEAD_HI]
print('# 闲置(不在 E0)的合法对偶字: %d 个' % len(idle_pair))
TARGET = idle_pair[0]
TB = bytes(idx.enc_pair[TARGET])
print('# 本次构造用例用的字: 「%s」 对偶码 %s' % (TARGET, TB.hex(' ')))

# ── A. 真实 .ATR 实测 ──
atrs = [c for c in cs if c['kind'] == 'ATR']
tot = 0
nonascii = {}
for c in atrs:
    blob, _ = F.container_blob(iso, c)
    tot += len(blob)
    for ch in idx.decode_chars(blob):
        if ord(ch) >= 0x80:
            nonascii[ch] = nonascii.get(ch, 0) + 1
print('\n[A] 真实盘 .ATR 实测')
n_gr = len([c for c in atrs if c['img'] == 'GR.IMG'])
n_menu = len([c for c in atrs if c['img'] == 'MENU.IMG'])
chk(len(atrs) == 1460 and n_gr == 1193 and n_menu == 267,
    '.ATR 容器 %d 个 (GR.IMG %d + MENU.IMG %d; 期望 1193 + 267 = 1460)'
    % (len(atrs), n_gr, n_menu))
chk(len(nonascii) == 0,
    '.ATR 解压后共 %d B, 出现的**非 ASCII 字符** %d 种 %s'
    % (tot, len(nonascii), ''.join(sorted(nonascii))[:80] or '(无)'))
print('    ⇒ 现役盘人名**全是英文**, 不存在"只在 .ATR 里出现"的真实汉字。')

# ── B. 构造: 把目标字的对偶码塞进真实 .ATR ──
print('\n[B] 构造用例: 真实 .ATR 内容 + 目标字的对偶码')
src = None
for c in atrs:
    blob, _ = F.container_blob(iso, c)
    if b'<ActorName>' in blob:
        src = blob
        break
chk(src is not None, '找到含 <ActorName> 的真实 .ATR (%d B)' % (len(src) if src else 0))
# 在 <ActorName> 里插一个中文名 (4 个字 = 8 字节, 构成 >=4 的可读串)
fake_name = TB + bytes(idx.enc_pair[idle_pair[1]]) + bytes(idx.enc_pair[idle_pair[2]]) \
    + bytes(idx.enc_pair[idle_pair[3]])
synthetic = src.replace(b'<ActorName>', b'<ActorName>' + fake_name, 1)
chk(synthetic != src, '合成 .ATR: 在 ActorName 里插入 %d B 的"中文名"' % len(fake_name))

# 走本工具**同一个**扫描函数 (kind=ATR ⇒ text=True ⇒ E1, 串长 >= 4)
ev = F.blob_hits(synthetic, idx, F.TEXT_RUN_MIN, (F.TEXT_RUN_MIN, 16))
chk(TARGET in ev[F.TEXT_RUN_MIN],
    'E1 扫描把「%s」判为"用到" ✓ (在 >=%d 的可读串内部)'
    % (TARGET, F.TEXT_RUN_MIN))
print('    ⇒ 该 .ATR 内容里现在解出的非 ASCII 字: %s'
      % ''.join(sorted(set(idx.decode_chars(synthetic)) - set(idx.decode_chars(src)))))

# ── C. 端到端: compute_reclaim 必须拦下它 ──
print('\n[C] 端到端: 走 compute_reclaim')
usage = blank_usage(e1={TARGET})
rec = F.compute_reclaim(idx, usage, policy='text', denoised=True)
chk(TARGET not in rec['reclaim'],
    '「%s」**不在**可回收清单里 ✓' % TARGET)
chk(TARGET in rec['blocked'],
    '「%s」被拦下 ✓ 原因: %s' % (TARGET, '; '.join(rec['blocked'].get(TARGET, []))))

# ── 对照: 没有任何证据时必须可回收 ──
usage0 = blank_usage()
rec0 = F.compute_reclaim(idx, usage0, policy='text', denoised=True)
chk(TARGET in rec0['reclaim'],
    '对照: 同一个字在**没有任何证据**时确实被判为可回收 ✓ (否则判据就是坏的)')

# ── 再验证: E0 路径 (结构化文本) 同样拦得住 ──
usage_e0 = blank_usage(e0={TARGET})
rec_e0 = F.compute_reclaim(idx, usage_e0, policy='text', denoised=True)
chk(TARGET not in rec_e0['reclaim'] and TARGET in rec_e0['blocked'],
    '对照: 走 E0 (结构化文本) 路径同样拦得住 ✓')

# ── 再验证: 单字节码路径 ──
#   ★ 实测: 76 个单字节码**全部**都在 E0 里 (全都在用) ⇒ 没有"闲置的单字节字"可做用例。
#     这里改为验证**扫描器的单字节路径**本身是通的 (把单字节码塞进 .ATR 必须被检出)。
idle_single = [c for c in idx.chars if c in idx.enc_single and c not in e0]
print('\n[D] 单字节码路径')
print('    闲置的单字节字: %d 个 / 单字节码共 %d 个'
      % (len(idle_single), len(idx.enc_single)))
S = sorted(idx.enc_single)[0]
sb = bytes([idx.enc_single[S]])
syn2 = src.replace(b'<ActorName>', b'<ActorName>' + sb * 6, 1)
ev2 = F.blob_hits(syn2, idx, F.TEXT_RUN_MIN, (F.TEXT_RUN_MIN,))
chk(S in ev2[F.TEXT_RUN_MIN],
    '单字节字「%s」(码 0x%02X) 塞进 .ATR 后同样被判为"用到" ✓' % (S, sb[0]))
rec2 = F.compute_reclaim(idx, blank_usage(e1={S}))
chk(S not in rec2['reclaim'], '单字节字「%s」同样不会被回收 ✓' % S)

# ── 再验证: 死 pair 的处理 ──
print('\n[E] 死 pair (lead>=0xAE) 的分类')
rec_all = F.compute_reclaim(idx, blank_usage())
chk(len(rec_all['dead_pairs']) > 0,
    '没有证据时, 死 pair %d 个被归入**可回收的清理项** (不是"拦截项") ✓'
    % len(rec_all['dead_pairs']))
chk(all(F.pair_slot(idx.enc_pair[c]) >= 1222 for c in rec_all['dead_pairs']),
    '死 pair 的格位号全部 >= 1222 (合法对偶空间之外) ⇒ 释放它们换不来新字格位 ✓')
chk(len(rec_all['legal_pairs']) + len(rec_all['dead_pairs'])
    + len(rec_all['singles']) == len(rec_all['reclaim']),
    '可回收 %d = 合法对偶 %d + 死 pair %d + 单字节 %d ✓ (按编码器优先级分类, 不重复计数)'
    % (len(rec_all['reclaim']), len(rec_all['legal_pairs']),
       len(rec_all['dead_pairs']), len(rec_all['singles'])))
reserved = [c for c in idx.chars if c in idx.enc_single
            and (idx.enc_single[c] in idx.protected or idx.enc_single[c] in idx.mark_codes)]
chk(len(rec_all['reclaim']) == len(idx.chars) - len(reserved),
    '没有任何证据时, 除 charset 自带的 %d 个 protected/mark_codes 保护字 %s 之外, '
    '全部 %d 个字都可回收 ✓'
    % (len(reserved), ''.join(reserved[:12]), len(rec_all['reclaim'])))
chk(all('protected' in ' '.join(rec_all['blocked'][c]) or
        'mark_codes' in ' '.join(rec_all['blocked'][c]) for c in reserved),
    '这 %d 个字被拦下的原因确实是 protected/mark_codes ✓' % len(reserved))

# ── 再验证: --apply 的"绝不覆盖原文件"守卫 (纯内存断言, 不写任何文件) ──
print('\n[F] --apply 写盘守卫 (不写任何文件)')
new_raw = F.make_new_charset(idx, rec_all)
try:
    F.write_charset(idx, new_raw, idx.path)
    guard_ok = False
except ValueError as ex:
    guard_ok = True
    print('     %s' % ex)
chk(guard_ok, '--out-charset 指向输入 charset 本身时**直接拒绝** ✓ (绝不覆盖原文件)')
chk(os.path.abspath(CHARSET) == idx.path, '被保护的正是现役 charset 文件 ✓')
chk(not os.path.exists(os.path.join(HERE, 'charset_compiled_zh16.reclaimed.json')),
    '没有产生任何 .reclaimed.json 残留 ✓')

iso.close()
print('\n保守性验证结论: %s' % ('[ok] 通过 ✓' if ok else '[!!] 失败'))
sys.exit(0 if ok else 1)
