# -*- coding: utf-8 -*-
r"""hk_sites.py — (1) EN_ORIG vs ZH113b 的 ELF 精确差异 → 站点表 + 运行时机分组 + 逐条栈安全判定
                 (2) DrawString 调用者 / fp 使用分析 (用户"钩子写坏调用者栈"假设的静态取证)

只读既有盘。
"""
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hk_lib as H     # noqa: E402

EN = H.elf('EN')
ZH = H.elf('ZH')

CALLEE_SAVED = set(range(16, 24)) | {30}      # s0..s7, fp(s8)
SAVE_RESTORE_OPS = {0x1E: 'lq', 0x1F: 'sq', 0x37: 'ld', 0x3F: 'sd',
                    0x31: 'lwc1', 0x35: 'ldc1', 0x39: 'swc1', 0x3D: 'sdc1'}

# ---------------------------------------------------------------- run → 站点
def byte_runs(eb, zb):
    """精确逐字节差异 run (EN vs ZH 的 ELF 文件内容)"""
    assert len(eb) == len(zb)
    runs = []
    i = 0
    n = len(eb)
    while i < n:
        if eb[i] != zb[i]:
            j = i
            while j < n and eb[j] != zb[j]:
                j += 1
            runs.append((i, j - i))
            i = j
        else:
            i += 1
    return runs


def merge(runs, gap):
    out = []
    for (o, l) in runs:
        if out and o - (out[-1][0] + out[-1][1]) <= gap:
            out[-1][1] = o + l - out[-1][0]
        else:
            out.append([o, l])
    return [(a, b) for (a, b) in out]


# ---------------------------------------------------------------- 分组表
# 组 = 任务书的 A.1/A.2/A.3/A.4 + CAVE + STR
GROUPS = {
    # A.1 更新/重绘路径
    'DrawText__10IkeButton3Fv': 'G1',
    'DrawText__15IkeKeyMapButtonFv': 'G1',
    'DrawText__13IkeBaseButtonFv': 'G1',
    'SetText__6RSHTMLFRC10RSUIString': 'G1',
    'SetText__15RSTextComponentFRC10RSUIString': 'G1',
    'DrawTheString__15RSTextComponentFRC10RSUIString': 'G1',
    'DisplayMessages__11ChatDisplayFv': 'G1',
    'DrawNN__14NewPS2ShortcutFv': 'G1',
    'AddOneWord__9RSFontMgrFRC9RSVector4RC9RSVector4RC7RSColorfb': 'G1',
    'Flush__9RSFontMgrFv': 'G1',
    'Draw__9RSFontMgrFv': 'G1',
    'ReadResource__15RSTextComponentFRQ23std39basic_istream<c,Q23std14char_traits<c>>': 'G1',
    # A.2 测量/排版
    'StringWidth__6RSFontCFPCc': 'G2',
    'CharWidth__6RSFontCFc': 'G2',
    'DoWordWrap__15RSTextComponentFRC10RSUIString': 'G2',
    'ComputeDrawXY__15RSTextComponentFRC10RSUIString': 'G2',
    # A.3 字形取址/绘制
    'ComputeCharTextureCoords__6RSFontCFcRfRfRfRf': 'G3',
    'DrawLetters__12IkeFontTableFv': 'G3',
    'DrawString__9RSFontMgrFPCcffRC7RSColorP6RSFontPCiPCii': 'G3',
    # A.4 其它
    'GetUISoldierAbbreviateName__Fii': 'G4',
    'GetActorNameAbbreviated__9ActorFileCFv': 'G4',
    'kShortcutDefaultSC__FUii': 'G4',
    'SetLinearSampling__8UIPacketFb': 'G4',
    'kBtnExplanationMapMax': 'G4',
    'strlwr': 'G4',
    'strupr': 'G4',
}
GROUP_NAME = {
    'G1': 'A.1 更新/重绘路径',
    'G2': 'A.2 测量/排版路径',
    'G3': 'A.3 字形取址/绘制路径（含 DrawString 序言拦截器）',
    'G4': 'A.4 其它（名字缩写/快捷键/滤波/常量/大小写）',
    'CAVE': 'CAVE 代码体（DBCS 解码器 / 度量替换体 / 截获器）',
    'STR': 'ELF 内字符串表（loading 文案）',
}
CAVE_NAMES = {'s_Pool', 'sceRemove', 'sceMkdir', 'sceDclose', 'sceDopen',
              'sceFormat', 'sceIpuInit'}
STR_RE = ('@5689', '@5690', '@5694', '@5695', '@5696', '@5698')


def group_of(sym):
    if sym in CAVE_NAMES:
        return 'CAVE'
    if sym in STR_RE:
        return 'STR'
    return GROUPS.get(sym, 'UNKNOWN')


# ---------------------------------------------------------------- 逐站点分析
def analyze(o, l):
    """o, l = ELF FILE 偏移与长度"""
    va = o + H.VA2FILE
    s = EN.sym_at(va)
    sym = s['name'] if s else '?'
    # 涉及的 4 字节指令窗
    first = (o // 4) * 4
    last = ((o + l - 1) // 4) * 4
    instrs = []
    for fo in range(first, last + 1, 4):
        we = struct.unpack_from('<I', EN.b, fo)[0]
        wz = struct.unpack_from('<I', ZH.b, fo)[0]
        ioff = max(o - fo, 0)
        ilen = min(o + l, fo + 4) - max(o, fo)
        instrs.append(dict(file=fo, va=fo + H.VA2FILE,
                           en='%08X' % we, zh='%08X' % wz,
                           en_d=H.dis1(we, fo + H.VA2FILE),
                           zh_d=H.dis1(wz, fo + H.VA2FILE),
                           diff_bytes='%d..%d' % (ioff, ioff + ilen - 1) if ilen > 0 else '',
                           diff_len=ilen, changed=(we != wz)))
    # 栈/ABI 判定
    flags = set()
    for it in instrs:
        if not it['changed']:
            continue
        for tag, w in (('EN', int(it['en'], 16)), ('ZH', int(it['zh'], 16))):
            op = w >> 26
            rs = (w >> 21) & 0x1F
            rt = (w >> 16) & 0x1F
            if op in SAVE_RESTORE_OPS:
                if rt in CALLEE_SAVED or rt == 31:
                    flags.add('SAVE_RESTORE_%s' % tag)
                if rs == 29:
                    flags.add('SPREL_%s' % tag)
            elif op == 0x09 and rs == 29:            # addiu rX,sp,n
                if rt == 29:
                    flags.add('SPADJ_%s' % tag)
                else:
                    flags.add('SPADDR_%s' % tag)
            elif op == 0x23 and rs == 29:
                flags.add('SPREL_%s' % tag)
            elif op in (0x02, 0x03):
                flags.add('REDIRECT_%s' % tag)
            elif op == 0x00 and (w & 0x3F) == 0x08:
                flags.add('JR_%s' % tag)
    return dict(elf_off=o, elf_va=va, length=l, iso_off=o + H.ELF_ISO_BASE,
                symbol=sym,
                sym_off=(va - s['value']) if s else None,
                group=group_of(sym), flags=sorted(flags), instrs=instrs)


def main():
    runs = byte_runs(EN.b, ZH.b)
    sites = merge(runs, 4)
    A = [analyze(o, l) for (o, l) in sites]

    # ---- 输出 站点表 ----
    lines = []
    lines.append('# HK 站点表 — EN_ORIG vs GR_ZH113b (ELF SLUS_206.13)')
    lines.append('')
    lines.append('ELF 大小 %d B (两盘相同); 精确差异 run = %d, 差异字节 = %d; '
                 '合并(间距≤4) = %d 处, 覆盖 %d B'
                 % (len(EN.b), len(runs), sum(r[1] for r in runs), len(sites),
                    sum(s[1] for s in sites)))
    lines.append('')
    lines.append('| # | VA | ISO | FILE | 长 | 符号 +Δ | 组 | EN → ZH | 栈/ABI 标记 |')
    lines.append('|---|---|---|---|---|---|---|---|---|')
    for i, a in enumerate(A):
        inst = [x for x in a['instrs'] if x['changed']]
        pairs = ' ; '.join('%s → %s' % (x['en_d'], x['zh_d']) for x in inst)
        lines.append('| %d | `0x%X` | `0x%X` | `0x%X` | %d | `%s +0x%X` | %s | %s | %s |'
                     % (i, a['elf_va'], a['iso_off'], a['elf_off'], a['length'],
                        a['symbol'].split('__')[0], a['sym_off'] or 0, a['group'],
                        pairs, ','.join(a['flags']) or '—'))
    lines.append('')
    # ---- 分组统计 ----
    lines.append('## 分组统计')
    lines.append('')
    lines.append('| 组 | 站点数 | 字节 | VA 范围 | 成员 |')
    lines.append('|---|---|---|---|---|')
    for g in ('G1', 'G2', 'G3', 'G4', 'CAVE', 'STR', 'UNKNOWN'):
        m = [a for a in A if a['group'] == g]
        if not m:
            continue
        members = sorted(set(a['symbol'].split('__')[0] for a in m))
        lines.append('| **%s %s** | %d | %d | 0x%X..0x%X | %s |'
                     % (g, GROUP_NAME.get(g, ''), len(m), sum(a['length'] for a in m),
                        min(a['elf_va'] for a in m), max(a['elf_va'] for a in m),
                        ', '.join('`%s`' % x for x in members)))

    # ---- DrawString 调用者 / fp 分析 ----
    lines.append('')
    lines.append('=' * 100)
    lines.append('## DrawString 序言拦截器 — 被跳过的 `sq fp,144(sp)` 取证')
    lines.append('=' * 100)
    lines.append('')
    lines.append('```')
    lines.append('0x219A70  addiu sp,sp,-224        ; 帧分配 (EN/ZH 都执行)')
    lines.append('0x219A74  EN: sd ra,160(sp)       ; ZH: j 0x565930  ← 拦截器')
    lines.append('0x219A78  EN: sq fp,144(sp)       ; ★ ZH 上被跳过 (拦截器回到 0x219A7C)')
    lines.append('0x219A7C  sq s7,128(sp)           ; ← 拦截器 j 0x219A7C 的落点')
    lines.append('   ...')
    lines.append('0x219DC0  ld ra,160(sp)           ; 尾声')
    lines.append('0x219DC4  lq fp,144(sp)           ; ★ 无条件执行 —— 但 sp+144 从未被写')
    lines.append('```')
    lines.append('')
    acc = H.sp_accesses(ZH.b, 0x219A70, 0x219E00)
    w144 = [x for x in acc if x[3] == 'sp+144' and x[1] == 'W']
    r144 = [x for x in acc if x[3] == 'sp+144' and x[1] == 'R']
    lines.append('* ZH `DrawString`(符号 size %d) 内 sp+144 的访问: **写 %d 条 %s / 读 %d 条 %s**'
                 % (0x219E00 - 0x219A70,
                    len(w144), [hex(x[0]) for x in w144],
                    len(r144), [hex(x[0]) for x in r144]))
    lines.append('* ZH 拦截器落点 `j 0x219A7C` ⇒ 唯一的写 `0x%X` **永不执行**；读 `0x%X` **每次调用都执行**。'
                 % (w144[0][0] if w144 else 0, r144[0][0] if r144 else 0))
    lines.append('* ⇒ **每次 `RSFontMgr::DrawString` 返回时, `fp`(=$s8, 被调用者保存寄存器) '
                 '被从「本次调用从未初始化过的栈槽 sp+144」重新载入。**')
    lines.append('')

    # 调用者扫描
    lines.append('### DrawString / 包装器 0x219EB0 的调用者 + 各自是否把 fp 当帧指针用')
    lines.append('')
    callers = []
    for a in range(0x100000, 0x5DED00, 4):
        o = a - H.VA2FILE
        w = struct.unpack_from('<I', ZH.b, o)[0]
        op = w >> 26
        if op in (0x02, 0x03):
            tgt = (w & 0x3FFFFFF) << 2
            tgt |= a & 0xF0000000
            if tgt in (0x219A70, 0x219EB0, 0x565930, 0x565900):
                callers.append((a, tgt, 'jal' if op == 3 else 'j'))
    lines.append('| 调用点 VA | 目标 | 形式 | 所在符号 | 该符号内 fp 写点 | fp 读点(帧指针用法) |')
    lines.append('|---|---|---|---|---|---|')
    for (a, tgt, k) in callers:
        s = ZH.sym_at(a)
        f = s['value'] if s else a
        e = (s['value'] + s['size']) if s else a + 4
        wr = H.reg_writes(ZH.b, f, e, 30)
        # fp 读点: 以 fp 为基址的内存访问 或 addiu rX,fp,n
        rd = []
        for x in range(f, e, 4):
            w = struct.unpack_from('<I', ZH.b, x - H.VA2FILE)[0]
            if ((w >> 21) & 0x1F) == 30 and (w >> 26) in (0x20, 0x21, 0x23, 0x24, 0x25,
                                                          0x27, 0x28, 0x29, 0x2B, 0x31,
                                                          0x39, 0x09, 0x1E, 0x1F, 0x37, 0x3F):
                rd.append(x)
        lines.append('| `0x%X` | `0x%X` | %s | `%s` | %s | %s |'
                     % (a, tgt, k, (s['name'].split('__')[0] if s else '?'),
                        ', '.join('0x%X' % x[0] for x in wr) or '无',
                        ', '.join('0x%X' % x for x in rd) or '无'))
    lines.append('')

    txt = '\n'.join(lines)
    with io.open(os.path.join(H.EVID, 'hk_sites.md'), 'w', encoding='utf-8') as f:
        f.write(txt)
    with io.open(os.path.join(H.EVID, 'hk_sites.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(elf_size=len(EN.b), n_runs=len(runs),
                       run_bytes=sum(r[1] for r in runs), n_sites=len(sites),
                       sites_cover=sum(s[1] for s in sites), sites=A,
                       callers=[dict(va=a, tgt=t, kind=k) for (a, t, k) in callers]),
                  f, ensure_ascii=False, indent=1)
    print('sites=%d runs=%d bytes=%d cover=%d' % (len(sites), len(runs),
                                                  sum(r[1] for r in runs),
                                                  sum(s[1] for s in sites)))
    gm = {}
    for a in A:
        gm[a['group']] = gm.get(a['group'], 0) + 1
    print('groups:', gm)
    print('callers of DrawString/wrapper:', [(hex(a), hex(t), k) for (a, t, k) in callers])


if __name__ == '__main__':
    main()
