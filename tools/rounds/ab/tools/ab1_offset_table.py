# -*- coding: utf-8 -*-
r"""ab1_offset_table.py — 任务 1-A: cave 站点读写偏移一致性表 (只读)

产出:
  evidence/A_offset_table.md      人读: 68 处逐条 + 35 处文字链逐条 + 语义
  evidence/A_suspicious_offsets.md  ★ 可疑偏移站点表 (判定核心输入)
  evidence/A_offset_table.json    机器可读
"""
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ab_lib as A     # noqa: E402
import nh_lib as N     # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.makedirs(A.EVID, exist_ok=True)

# ---- 文字/字体/UI 链符号 (报告 §3.5 的 35 处) ----
TEXT_SYMS = [
    'DrawString__9RSFontMgr', 'DrawLetters__12IkeFontTable', 'StringWidth__6RSFont',
    'CharWidth__6RSFont', 'ComputeCharTextureCoords__6RSFont',
    'AddOneWord__9RSFontMgr', 'Flush__9RSFontMgr', 'Draw__9RSFontMgr',
    'ComputeDrawXY__15RSTextComponent', 'DoWordWrap__15RSTextComponent',
    'SetText__6RSHTMLF', 'SetText__15RSTextComponent', 'ReadResource__15RSTextComponent',
    'DrawTheString__15RSTextComponent', 'DrawText__10IkeButton', 'DrawText__15IkeKeyMapButton',
    'DrawText__13IkeBaseButton', 'DisplayMessages__11ChatDisplay',
    'GetUISoldierAbbreviateName', 'GetActorNameAbbreviated', 'SetLinearSampling__8UIPacket',
]
CAVE_SYMS = ['s_Pool', 'sceRemove', 'sceMkdir', 'sceFormat', 'sceDopen', 'sceDclose',
             'sceIpuInit', 'strlwr', 'strupr']
STR_SYMS = ['@5689', '@5690', '@5694', '@5695', '@5696', '@5698']


def exact_runs(a, b):
    n = len(a)
    runs, i = [], 0
    while i < n:
        if a[i] == b[i]:
            i += 1
            continue
        j = i
        while j < n and a[j] != b[j]:
            j += 1
        runs.append((i, j))
        i = j
    merged = []
    for s, e in runs:
        if merged and s - merged[-1][1] <= 4:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return runs, merged


def classify(sym):
    if sym is None:
        return 'other'
    if any(sym.startswith(x) for x in TEXT_SYMS):
        return 'text_chain'
    if any(sym.startswith(x) for x in CAVE_SYMS):
        return 'cave'
    if any(sym.startswith(x) for x in STR_SYMS):
        return 'cave_str'
    return 'other'


def is_offset_class(w_en, w_zh, a):
    """判断这条指令的差异是否属于「偏移/步进类立即数」"""
    d_en, d_zh = A.dis1(w_en, a), A.dis1(w_zh, a)
    op_en, op_zh = w_en >> 26, w_zh >> 26
    # 内存访问 (load/store) 的 16 位偏移
    if op_en in A.LOADS or op_en in A.STORES:
        return True
    # addiu / sltiu / andi 等立即数算术 (非跳转)
    if op_en in A.ALUI and op_en != 0x0F:
        return True
    if op_zh in A.LOADS or op_zh in A.STORES or (op_zh in A.ALUI and op_zh != 0x0F):
        return True
    return False


def main():
    e_en, f_en = A.load_elf('EN_ORIG')
    e_zh, f_zh = A.load_elf('ZH113b')
    e_fx, _ = A.load_elf('ZH113b_fix')
    buf = io.StringIO()
    recs = []

    # 0) 先核对 ZH113b vs ZH113b_fix 只有 1 字节
    r0, m0 = exact_runs(e_zh.b, e_fx.b)
    buf.write('# A) cave 站点读写偏移一致性表\n\n')
    buf.write('> 只读比对 `GR_EN_ORIG.iso` vs **`GR_ZH113b.iso`（A/B 的基底）**。\n')
    buf.write('> ELF = `SLUS_206.13` @ISO LBA %d(=0x%X)；`FILE = VA − 0x%X`；'
              '`ISO = VA − 0x%X`。\n\n' % (A.ELF_LBA, A.ELF_ISO_BASE, A.VA2FILE, A.VA2ISO))
    buf.write('- ZH113b vs ZH113b_fix 精确差异 run = %d, 字节 = %d'
              % (len(r0), sum(e - s for s, e in r0)))
    for (s, e) in r0:
        va = e_zh.off2va(s)[0]
        buf.write('  → FILE 0x%X VA 0x%X  %s → %s\n'
                  % (s, va, e_zh.b[s:e].hex(' '), e_fx.b[s:e].hex(' ')))
    buf.write('\n')

    raw_runs, merged = exact_runs(e_en.b, e_zh.b)
    buf.write('- EN vs ZH113b: 精确 run = **%d** / **%d B**；合并(间距≤4) = **%d 处** / %d B\n\n'
              % (len(raw_runs), sum(e - s for s, e in raw_runs), len(merged),
                 sum(e - s for s, e in merged)))

    # 1) 逐处 (68) 详表
    for i, (s, e) in enumerate(merged):
        va = e_en.off2va(s)[0]
        sym = e_en.sym_at(va)
        sname = sym['name'] if sym else None
        delta = (va - sym['value']) if sym else None
        cat = classify(sname)
        instrs = []
        # 覆盖该 run 的 4 字节字 (含首尾所在字)
        w0 = s & ~3
        w1 = ((e - 1) | 3) + 1
        for o in range(w0, w1, 4):
            we = struct.unpack_from('<I', e_en.b, o)[0]
            wz = struct.unpack_from('<I', e_zh.b, o)[0]
            ava = e_en.off2va(o)[0]
            instrs.append(dict(va=ava, file=o, en=we, zh=wz,
                               en_d=A.dis1(we, ava), zh_d=A.dis1(wz, ava),
                               same=(we == wz),
                               off_class=(we != wz and is_offset_class(we, wz, ava))))
        rec = dict(idx=i, file=s, file_end=e, va=va, va_end=e_en.off2va(e - 1)[0],
                   length=e - s, sym=sname, sym_delta=delta,
                   sym_size=(sym['size'] if sym else None), cat=cat,
                   iso_off=s + A.ELF_ISO_BASE,
                   en_hex=e_en.b[s:e].hex(' '), zh_hex=e_zh.b[s:e].hex(' '),
                   instrs=instrs,
                   n_off_class=sum(1 for x in instrs if x['off_class']))
        recs.append(rec)

    buf.write('## A.1 全部 %d 处差异 (逐条)\n\n' % len(recs))
    buf.write('| # | 类别 | 符号 +Δ | VA | FILE | ISO | len | 改前 (EN) | 改后 (ZH) |\n')
    buf.write('|---|---|---|---|---|---|---|---|---|\n')
    for r in recs:
        en_s, zh_s = [], []
        for x in r['instrs']:
            if not x['same']:
                en_s.append('0x%08X %s' % (x['en'], x['en_d']))
                zh_s.append('0x%08X %s' % (x['zh'], x['zh_d']))
        if not en_s:
            en_s, zh_s = ['(字节差未落在指令字段) ' + r['en_hex']], [r['zh_hex']]
        buf.write('| %d | %s | `%s+0x%X` | 0x%X | 0x%X | 0x%X | %d | %s | %s |\n'
                  % (r['idx'], r['cat'], r['sym'], r['sym_delta'] or 0, r['va'], r['file'],
                     r['iso_off'], r['length'], ' ; '.join(en_s), ' ; '.join(zh_s)))

    # 2) 文字链 35 处
    tc = [r for r in recs if r['cat'] in ('text_chain',)]
    buf.write('\n## A.2 文字/字体/UI 链 (%d 处) —— 逐条语义\n\n' % len(tc))
    for r in tc:
        buf.write('### run#%d  `%s +0x%X`  VA 0x%X  FILE 0x%X  ISO 0x%X  len=%d\n'
                  % (r['idx'], r['sym'], r['sym_delta'], r['va'], r['file'], r['iso_off'],
                     r['length']))
        for x in r['instrs']:
            if x['same']:
                buf.write('  ·  0x%08X  `0x%08X` %s   (未变)\n' % (x['va'], x['en'], x['en_d']))
            else:
                buf.write('  ★  0x%08X  EN `0x%08X` %-34s | ZH `0x%08X` %s%s\n'
                          % (x['va'], x['en'], x['en_d'], x['zh'], x['zh_d'],
                             '   ⟵ 偏移/步进类' if x['off_class'] else ''))
        buf.write('\n')

    # 3) ★ 可疑偏移站点表
    sus = io.StringIO()
    sus.write('# ★ 可疑偏移站点表 (任务 1-A 的核心输出)\n\n')
    sus.write('口径: 一条差异若**改动了「立即数偏移/步进」**'
              '(load/store 的 16 位偏移, 或 addiu/sltiu/andi 的立即数) ⇒ 入选本表。\n\n')

    off_sites = [x for r in recs for x in r['instrs'] if x['off_class']]
    sus.write('全 ELF 68 处差异中, **偏移/步进类差异站点共 %d 个**'
              '(涉及 %d 处 run):\n\n' % (len(off_sites),
                                        len(set(id(x) for x in off_sites))))
    sus.write('| # | VA | FILE | ISO | 符号+Δ | 类别 | EN | ZH | 立即数变化 | 判定 |\n')
    sus.write('|---|---|---|---|---|---|---|---|---|---|\n')
    j = 0
    for r in recs:
        for x in r['instrs']:
            if not x['off_class']:
                continue
            j += 1
            we, wz = x['en'], x['zh']
            imm_en = we & 0xFFFF
            imm_zh = wz & 0xFFFF
            s_en = imm_en - 0x10000 if imm_en & 0x8000 else imm_en
            s_zh = imm_zh - 0x10000 if imm_zh & 0x8000 else imm_zh
            sus.write('| %d | 0x%X | 0x%X | 0x%X | `%s+0x%X` | %s | `%s` | `%s` | %d → %d | %s |\n'
                      % (j, x['va'], x['file'], x['file'] + A.ELF_ISO_BASE, r['sym'],
                         r['sym_delta'], r['cat'], x['en_d'], x['zh_d'], s_en, s_zh, '待判定'))
    json.dump(dict(runs=recs, off_sites=off_sites), open(os.path.join(A.EVID, 'A_offset_table.json'),
                                                         'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    open(os.path.join(A.EVID, 'A_offset_table.md'), 'w', encoding='utf-8').write(buf.getvalue())
    open(os.path.join(A.EVID, 'A_suspicious_offsets_raw.md'), 'w',
         encoding='utf-8').write(sus.getvalue())
    print(buf.getvalue()[:12000])
    print('---- 偏移类站点 %d 个 ----' % len(off_sites))
    print(sus.getvalue()[:6000])


if __name__ == '__main__':
    main()
