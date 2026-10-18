# -*- coding: utf-8 -*-
r"""sent_verify56.py —— SENT_05 / SENT_06 的**独立终检**（从盘上重读，不复用构建脚本的状态）。

检查项：
  1. 尺寸 / sha256 / 与基底逐字节差异 run（必须恰好落在声明站点上）；
  2. **全 ELF 再普查**：把整段 PT_LOAD 读进来，逐字扫 imm16 ∈ {0x00B1,0x00B5,0xFFB1,0xFFB5}，
     与**基底**的同一张表对比 ⇒ 消失的站点必须**恰好等于**声明补丁集，新增必须 = 0；
  3. SENT_05 vs SENT_02：差异必须**恰好 = CharWidth 的 2 个字节**（单变量递进自证）；
  4. 每个站点逐字回读；
  5. 4 个 gate（ZH113b）原样未动；
  6. 补丁区间内 0xB1/0xB5 立即数残留 = 0。
输出 → work\builds\GR_SENT\audit\I_verify56.txt
"""
import array
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
OUTDIR = os.path.join(ROOT, 'work', 'builds', 'GR_SENT')
AUD = os.path.join(OUTDIR, 'audit')
ISO_OF_VA = 0x6C780
ELF_VA0, ELF_FILESZ = 0x100000, 0x4DED00
ICON_IMMS = {0x00B1, 0x00B5, 0xFFB1, 0xFFB5}

PRODS = (
    ('SENT_05_icon_all_off',
     os.path.join(OUTDIR, 'SENT_05_icon_all_off.iso'),
     os.path.join(ROOT, 'work', 'builds', 'GR_CVAR', 'CVAR_04_text.iso'),
     os.path.join(OUTDIR, 'SENT_02_icon_path_off.iso')),
    ('SENT_06_icon_all_off_zh113b',
     os.path.join(OUTDIR, 'SENT_06_icon_all_off_zh113b.iso'),
     os.path.join(ROOT, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso'),
     None),
)
GATES = (0x416EE8, 0x417160, 0x41751C, 0x5656A4)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def elf_imms(p):
    """全段扫 imm16 ∈ ICON_IMMS，返回 {VA: imm}。用 array 提速。"""
    f = open(p, 'rb')
    f.seek(ELF_VA0 - ISO_OF_VA)
    buf = f.read(ELF_FILESZ)
    f.close()
    a = array.array('I')
    a.frombytes(buf[:len(buf) - (len(buf) % 4)])
    out = {}
    for i, w in enumerate(a):
        imm = w & 0xFFFF
        if imm in ICON_IMMS:
            out[ELF_VA0 + i * 4] = imm
    return out


def diff_runs(a, b):
    runs = []
    with open(a, 'rb') as fa, open(b, 'rb') as fb:
        off = 0
        while True:
            ba, bb = fa.read(1 << 22), fb.read(1 << 22)
            if not ba and not bb:
                break
            n = min(len(ba), len(bb))
            i = 0
            while i < n:
                if ba[i] != bb[i]:
                    j = i
                    while j < n and ba[j] != bb[j]:
                        j += 1
                    runs.append((off + i, j - i))
                    i = j
                else:
                    i += 1
            off += n
    return runs


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    os.makedirs(AUD, exist_ok=True)
    buf = []

    def P(*x):
        line = ' '.join(str(y) for y in x)
        print(line)
        buf.append(line)

    base_imms_cache = {}
    ok_all = True
    for (name, prod, base, cmp2) in PRODS:
        meta = json.load(open(os.path.join(OUTDIR, name + '.meta.json'), encoding='utf-8'))
        P('=' * 92)
        P('## %s' % name)
        P('=' * 92)
        P('  产物      = %s' % os.path.relpath(prod, ROOT))
        P('  基底      = %s' % os.path.relpath(base, ROOT))
        P('  sha256    = %s' % sha256_file(prod))
        P('  声明 sha  = %s   ⇒ %s' % (meta['sha256'],
                                       '一致 ✓' if sha256_file(prod) == meta['sha256'] else '不符 ✗'))
        sz, bsz = os.path.getsize(prod), os.path.getsize(base)
        P('  尺寸      = %d B  (基底 %d) ⇒ %s' % (sz, bsz, '不变 ✓' if sz == bsz else '变了 ✗'))

        # 1) 站点逐字回读
        f = open(prod, 'rb')
        bad = []
        for s in meta['sites']:
            f.seek(s['iso_off'])
            got = struct.unpack('<I', f.read(4))[0]
            if got != int(s['new_word'], 16):
                bad.append((s['va'], s['new_word'], '0x%08X' % got))
            # 再确认 ISO 偏移口径
            assert s['iso_off'] == int(s['va'], 16) - ISO_OF_VA
        P('  站点回读  = %d 处，不符 %d 处 %s' % (len(meta['sites']), len(bad), bad))
        if bad:
            ok_all = False

        # 2) 全 ELF 再普查（与基底对比）
        if base not in base_imms_cache:
            base_imms_cache[base] = elf_imms(base)
        bi = base_imms_cache[base]
        pi = elf_imms(prod)
        gone = sorted(set(bi) - set(pi))
        added = sorted(set(pi) - set(bi))
        declared = sorted(int(s['va'], 16) for s in meta['sites'])
        P('  基底全 ELF imm16∈{00B1,00B5,FFB1,FFB5} 站点 = %d 处' % len(bi))
        P('  产物全 ELF 同口径站点                        = %d 处' % len(pi))
        P('  消失的站点 = %d 处；新增 = %d 处' % (len(gone), len(added)))
        P('  消失集合 == 声明补丁集 ? %s' % ('是 ✓' if gone == declared else
                                            '否 ✗ 差集: 声明未消失=%s 未声明却消失=%s'
                                            % ([hex(x) for x in set(declared) - set(gone)],
                                               [hex(x) for x in set(gone) - set(declared)])))
        P('  新增站点 = %s' % ([hex(x) for x in added] or '无 ✓'))
        if gone != declared or added:
            ok_all = False

        # 3) 与基底 / 与 SENT_02 的逐字节差异
        runs = diff_runs(base, prod)
        tot = sum(n for _o, n in runs)
        allowed = [(s['iso_off'], 4) for s in meta['sites']]
        outside = [(o, n) for (o, n) in runs
                   if not any(a <= o and o + n <= a + ln for (a, ln) in allowed)]
        P('  vs 基底   : %d run / %d B ；允许区外 %d run %s'
          % (len(runs), tot, len(outside), outside if outside else '✓'))
        P('  差异 run  : %s' % ['0x%X+%d' % (o, n) for (o, n) in runs])
        if outside:
            ok_all = False
        if cmp2:
            runs2 = diff_runs(cmp2, prod)
            P('  vs SENT_02: %d run / %d B  @ %s'
              % (len(runs2), sum(n for _o, n in runs2),
                 ['0x%X+%d' % (o, n) for (o, n) in runs2]))
            exp = sorted(s['iso_off'] for s in meta['sites'] if s['va'] in ('0x21AD38', '0x21AD4C'))
            got_off = sorted(o for (o, _n) in runs2)
            P('  ⇒ 是否恰好只差 CharWidth 的 2 个字节 @%s ? %s'
              % (['0x%X' % x for x in exp], '是 ✓' if got_off == exp else '否 ✗'))

        # 4) gate / 结构（仅 ZH113b）
        if name.endswith('zh113b'):
            g = []
            for va in GATES:
                f.seek(va - ISO_OF_VA)
                g.append('0x%X=0x%08X' % (va, struct.unpack('<I', f.read(4))[0]))
            P('  gate 4 处 : %s' % ' / '.join(g))
            f.seek(0x21AD10 - ISO_OF_VA)
            w = struct.unpack('<2I', f.read(8))
            P('  CharWidth 入口 trampoline = 0x%08X 0x%08X（应 0x27BDFFF0 + sd ra / j 0x416F40）' % w)
            f.seek(0x21AD18 - ISO_OF_VA)
            P('  j 目标     = 0x%08X （应 0x08105BD0 = `j 0x416F40`）'
              % struct.unpack('<I', f.read(4))[0])
        f.close()
        P('')

    P('=' * 92)
    P('总判定：%s' % ('全部通过 ✅' if ok_all else '有 ✗ 项'))
    with open(os.path.join(AUD, 'I_verify56.txt'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(buf) + '\n')
    print('[out] %s' % os.path.join(AUD, 'I_verify56.txt'))


if __name__ == '__main__':
    main()
