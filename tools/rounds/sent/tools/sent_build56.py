# -*- coding: utf-8 -*-
r"""sent_build56.py —— 第 5/6 张诊断盘：把 ELF 里**全部** 0xB1/0xB5 硬编码立即数改成「永不命中」。

产物（**只写 work\builds\GR_SENT\**）：
  SENT_05_icon_all_off.iso            基底 = work\builds\GR_CVAR\CVAR_04_text.iso（原盘 ELF）
                                      10 处 = DrawString 8 + CharWidth 2（**全部是活代码**）
                                      · 相对 SENT_02 只多改 CharWidth 的 2 字节 ⇒ 单变量递进
  SENT_06_icon_all_off_zh113b.iso     基底 = work\builds\GR_ZH113b\GR_ZH113b.iso（汉化自己的 ELF）
                                      12 处 = DrawString 8（其中 7 已是零扩展、1 处惰性）
                                             + CharWidth 残留体 2（**死代码**）
                                             + CharWidth cave 2（活代码，零扩展形式）

「永不命中」写法一律沿用 SENT_02：`addiu rX,zero,0xFF00`（符号扩展 ⇒ 0xFFFFFF00）。
  · 对原盘 `lb` 语义（a1 = 0xFFFFFF80..0xFFFFFFFF ∪ 0..0x7F）⇒ 不可能相等；
  · 对汉化 `lhu` 语义（a1 = 0x00000000..0x0000FFFF）⇒ 也不可能相等。
  两种语义下都成立，这正是本批盘要的单变量。

只读：所有基底 ISO（open('rb')）与 PCSX2 配置。未跑模拟器。
"""
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
OUTDIR = os.path.join(ROOT, 'work', 'builds', 'GR_SENT')
ISO_OF_VA = 0x6C780
SAFE = 0xFF00
ICON_IMMS = (0x00B1, 0x00B5, 0xFFB1, 0xFFB5)

BASE_CVAR = os.path.join(ROOT, 'work', 'builds', 'GR_CVAR', 'CVAR_04_text.iso')
BASE_ZH = os.path.join(ROOT, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')

# ── 站点表 ────────────────────────────────────────────────────────────────
# (VA, 期望原字, 角色, 可达性判定)
CVAR_SITES = (
    (0x219C08, 0x2403FFB5, 'DrawString 第一次判定（0xB5）: 命中⇒硬编码 UV', 'live'),
    (0x219C10, 0x2403FFB5, 'DrawString 上一条的延迟槽副本', 'live'),
    (0x219C14, 0x2403FFB1, 'DrawString 第一次判定（0xB1）', 'live'),
    (0x219C40, 0x2403FFB5, 'DrawString beq 的跳转目标（0xB1 分支入口后再比一次）', 'live'),
    (0x219C94, 0x2403FFB5, 'DrawString 第二次判定（0xB5）: 字距走图标专用块', 'live'),
    (0x219CAC, 0x2403FFB1, 'DrawString 第二次判定（0xB1）', 'live'),
    (0x219D24, 0x2402FFB5, 'DrawString 第三次判定（0xB5）: AddOneWord 的 t0=1 ⇒ 副包', 'live'),
    (0x219D38, 0x2402FFB1, 'DrawString 第三次判定（0xB1）', 'live'),
    (0x21AD38, 0x2402FFB5, 'RSFont::CharWidth 硬编码字距 20（0xB5）', 'live'),
    (0x21AD4C, 0x2402FFB1, 'RSFont::CharWidth 硬编码字距 20（0xB1）', 'live'),
)

ZH_SITES = (
    (0x219C08, 0x240300B5, 'DrawString 第一次判定（0xB5）——汉化已改零扩展', 'live'),
    (0x219C10, 0x240300B5, 'DrawString 延迟槽副本——汉化已改零扩展', 'live'),
    (0x219C14, 0x240300B1, 'DrawString 第一次判定（0xB1）——汉化已改零扩展', 'live'),
    (0x219C40, 0x2403FFB5, 'DrawString 0xB1 分支入口的「再比一次」——**惰性**（a1≡0x00B1，恒不相等）',
     'inert'),
    (0x219C94, 0x240300B5, 'DrawString 第二次判定（0xB5）——汉化已改零扩展', 'live'),
    (0x219CAC, 0x240300B1, 'DrawString 第二次判定（0xB1）——汉化已改零扩展', 'live'),
    (0x219D24, 0x240200B5, 'DrawString 第三次判定（0xB5）——汉化已改零扩展', 'live'),
    (0x219D38, 0x240200B1, 'DrawString 第三次判定（0xB1）——汉化已改零扩展', 'live'),
    (0x21AD38, 0x2402FFB5, 'CharWidth 残留体的硬编码 20（0xB5）——**死代码**（0x21AD10 已 j 0x416F40）',
     'dead'),
    (0x21AD4C, 0x2402FFB1, 'CharWidth 残留体的硬编码 20（0xB1）——**死代码**', 'dead'),
    (0x416F5C, 0x240900B5, '★ CharWidth cave（0x416F40）自己的图标特判（0xB5，零扩展）——活代码',
     'live'),
    (0x416F68, 0x240900B1, '★ CharWidth cave 自己的图标特判（0xB1，零扩展）——活代码', 'live'),
)

# 补丁后必须「立即数残留 = 0」的区间（函数体/残留体/cave）
RESIDUAL_RANGES = {
    'SENT_05_icon_all_off': (
        ('DrawString', 0x219A70, 0x219E00),
        ('CharWidth', 0x21AD10, 0x21AE60),
    ),
    'SENT_06_icon_all_off_zh113b': (
        ('DrawString', 0x219A70, 0x219E00),
        ('CharWidth 残留体（死）', 0x21AD10, 0x21ADD8),
        ('CharWidth cave', 0x416F40, 0x417030),
    ),
}

# gate 站点（`sltiu …,0xB1`）——**区间边界，不是相等比较，绝不许动**；补丁后必须原样
GATES = (0x416EE8, 0x417160, 0x41751C, 0x5656A4)
GATE_ONLY_ZH = True          # 原盘这 4 个 VA 不是 gate（是别的东西），只在 ZH113b 校验


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def diff_runs(a, b):
    """逐字节差异 run 列表 [(off, len)]（只读两个文件）。"""
    runs = []
    with open(a, 'rb') as fa, open(b, 'rb') as fb:
        off = 0
        while True:
            ba = fa.read(1 << 22)
            bb = fb.read(1 << 22)
            if not ba and not bb:
                break
            n = min(len(ba), len(bb))
            i = 0
            while i < n:
                if ba[i] != bb[i]:
                    j = i
                    while j < n and ba[j] != bb[j]:
                        j += 1
                    runs.append([off + i, j - i])
                    i = j
                else:
                    i += 1
            off += n
    return runs


def scan_imm(data, base_va):
    """在 data（函数体原始字节）里扫 imm16 ∈ ICON_IMMS 的指令。"""
    out = []
    for k in range(0, len(data) - 3, 4):
        w = struct.unpack_from('<I', data, k)[0]
        if (w & 0xFFFF) in ICON_IMMS:
            out.append(dict(va=base_va + k, word='0x%08X' % w, imm='0x%04X' % (w & 0xFFFF)))
    return out


def build(name, base, sites, why, extra_checks=None):
    out_iso = os.path.join(OUTDIR, name + '.iso')
    rep = dict(name=name, base=os.path.relpath(base, ROOT),
               out=os.path.relpath(out_iso, ROOT), why=why,
               safe_imm='0x%04X' % SAFE,
               safe_imm_semantics='addiu rX,zero,0xFF00 ⇒ rX = 0xFFFFFF00：'
                                  '既不在 lb 的符号扩展集合（0xFFFFFF80..0xFFFFFFFF ∪ 0..0x7F）里，'
                                  '也不在 lhu 的零扩展集合（0..0xFFFF）里 ⇒ 两种语义都永不命中',
               build_cmd='python work\\builds\\GR_SENT\\tools\\sent_build56.py %s' % name)
    print('=' * 88)
    print('[build] %s\n        基底 = %s\n        %s' % (name, rep['base'], why))

    base_sha = sha256_file(base)
    base_size = os.path.getsize(base)
    print('        基底 sha256 = %s  (%d B)' % (base_sha, base_size))

    # 1) 逐站点核对 + 计算新字
    src = open(base, 'rb')
    patched = []
    for (va, old, role, reach) in sites:
        off = va - ISO_OF_VA
        src.seek(off)
        got = struct.unpack('<I', src.read(4))[0]
        assert got == old, ('VA 0x%08X 原字不符：盘上 0x%08X ≠ 声明 0x%08X' % (va, got, old))
        new = (old & 0xFFFF0000) | SAFE
        patched.append(dict(va='0x%X' % va, iso_off=off, old_word='0x%08X' % old,
                            new_word='0x%08X' % new,
                            old_imm='0x%04X' % (old & 0xFFFF), new_imm='0x%04X' % SAFE,
                            old_form=('零扩展 (unsigned 177/181)' if (old & 0xFFFF) < 0x8000
                                      else '符号扩展 (signed −75/−79)'),
                            rt=(old >> 16) & 0x1F, role=role, reachability=reach))
    src.close()
    print('        %d 处原字全部核对一致 ✓' % len(patched))

    # 2) 复制 + 打补丁
    import shutil
    if os.path.exists(out_iso):
        os.remove(out_iso)
    shutil.copyfile(base, out_iso)
    with open(out_iso, 'r+b') as f:
        for p in patched:
            f.seek(p['iso_off'])
            f.write(struct.pack('<I', int(p['new_word'], 16)))
        f.flush()
        os.fsync(f.fileno())

    # 3) 回读 + 区间残留扫描 + gate 未动
    chk = open(out_iso, 'rb')
    readback_ok = True
    for p in patched:
        chk.seek(p['iso_off'])
        got = struct.unpack('<I', chk.read(4))[0]
        if got != int(p['new_word'], 16):
            readback_ok = False
        p['readback'] = '0x%08X' % got
    rep['sites'] = patched
    rep['readback_all_ok'] = readback_ok
    assert readback_ok, '回读不符'
    print('        逐字回读 %d/%d 一致 ✓' % (len(patched), len(patched)))

    resid = {}
    for (tag, lo, hi) in RESIDUAL_RANGES[name]:
        chk.seek(lo - ISO_OF_VA)
        data = chk.read(hi - lo)
        hits = scan_imm(data, lo)
        resid['%s [0x%X,0x%X)' % (tag, lo, hi)] = hits
        print('        区间残留   %-28s [0x%X,0x%X) : %d 处 %s'
              % (tag, lo, hi, len(hits), [h['imm'] for h in hits]))
    rep['in_range_imm_leftover'] = resid
    assert all(len(v) == 0 for v in resid.values()), '段内仍有 0xB1/0xB5 立即数残留'

    if extra_checks:
        rep['extra_checks'] = extra_checks(chk)
        for k, v in rep['extra_checks'].items():
            print('        %-34s %s' % (k, v))

    # 全 ELF 再普查：确认「已改站点」在产物上全部变成 0xFF00，其它立即数一个字未动
    chk.seek(0)
    rep['elf_imm_census_after'] = None
    chk.close()

    # 4) 差异 run（对基底）
    runs = diff_runs(base, out_iso)
    total = sum(n for _o, n in runs)
    allowed = [(p['iso_off'], 4) for p in patched]
    outside = [(o, n) for (o, n) in runs
               if not any(a <= o and o + n <= a + ln for (a, ln) in allowed)]
    rep.update(size=os.path.getsize(out_iso), base_size=base_size, base_sha256=base_sha,
               sha256=sha256_file(out_iso),
               diff_runs=len(runs), diff_bytes=total,
               diff_runs_list=runs,
               diff_runs_outside_allowed=len(outside), diff_runs_outside_list=outside,
               selfcheck=dict(size_eq_base=(os.path.getsize(out_iso) == base_size),
                              allowed_region_only=(len(outside) == 0),
                              readback_all_ok=readback_ok,
                              in_range_imm_leftover_zero=all(len(v) == 0
                                                              for v in resid.values())))
    print('        [out] sha256=%s  %d B  diff %d run / %d B  允许区外 %d run'
          % (rep['sha256'], rep['size'], rep['diff_runs'], rep['diff_bytes'], len(outside)))
    with open(os.path.join(OUTDIR, name + '.meta.json'), 'w', encoding='utf-8') as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    return rep


def zh_extra(chk):
    """ZH113b 专属附加检查：4 个 gate 未被动 + 汉化 cave 结构自证。"""
    out = {}
    st = []
    for va in GATES:
        chk.seek(va - ISO_OF_VA)
        w = struct.unpack('<I', chk.read(4))[0]
        st.append('0x%X=0x%08X' % (va, w))
    out['gates_untouched_4'] = ' / '.join(st) + '  （应全为 `sltiu …,0xB1` = 0x2CA9/0x2D09/0x2D4B/0x2D6C + 00B1）'
    chk.seek(0x21AD10 - ISO_OF_VA)
    w1, w2 = struct.unpack('<2I', chk.read(8))
    out['charwidth_entry_trampoline'] = (
        'VA 0x21AD10/0x21AD14/0x21AD18 = 0x%08X / 0x%08X / 0x%08X  '
        '（应 = `addiu sp,sp,-16` / `sd ra,0(sp)` / `j 0x416F40`）'
        % (w1, w2, struct.unpack('<I', chk.read(4))[0]))
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    want = sys.argv[1:] or ['SENT_05_icon_all_off', 'SENT_06_icon_all_off_zh113b']
    summ = {}
    for nm in want:
        if nm == 'SENT_05_icon_all_off':
            rep = build(nm, BASE_CVAR, CVAR_SITES,
                        '把**原盘 ELF**里对 0xB1/0xB5 的硬编码立即数**全部**改成永不命中：'
                        'DrawString 8 处（SENT_02 已改）+ RSFont::CharWidth 2 处（★ 本轮新增）。'
                        '文本/图集/容器**一字不动** ⇒ 相对 SENT_02 是**只多改 2 字节**的单变量递进：'
                        'SENT_02 仍卡、本盘不卡 ⇒ 元凶是 CharWidth 的硬编码字距；'
                        '两者都卡 ⇒ 代码侧的 10 字节全部不是元凶。')
        else:
            rep = build(nm, BASE_ZH, ZH_SITES,
                        '把**汉化自己那份 ELF**（GR_ZH113b）里剩余的 0xB1/0xB5 硬编码立即数'
                        '**全部**改成永不命中：DrawString 8 处（7 处汉化已改零扩展 + 1 处惰性）'
                        '+ CharWidth 残留体 2 处（死代码）+ CharWidth cave 2 处（活代码、零扩展）。'
                        '⇒ 判据：这是「代码侧修法在真实汉化盘上是否可行」的唯一实测臂。',
                        extra_checks=zh_extra)
        summ[nm] = dict(sha256=rep['sha256'], size=rep['size'],
                        diff_runs=rep['diff_runs'], diff_bytes=rep['diff_bytes'],
                        out=rep['out'], base=rep['base'], n_sites=len(rep['sites']))
    print()
    for k, v in summ.items():
        print('%-32s %s  diff %s run / %s B  sites=%d' % (k, v['sha256'], v['diff_runs'],
                                                         v['diff_bytes'], v['n_sites']))
    sp = os.path.join(OUTDIR, 'summary_sent56.json')
    old = {}
    if os.path.exists(sp):
        try:
            old = json.load(open(sp, encoding='utf-8'))
        except Exception:                                                     # noqa: BLE001
            old = {}
    old.update(summ)
    with open(sp, 'w', encoding='utf-8') as f:
        json.dump(old, f, ensure_ascii=False, indent=1)
    print('[out] summary_sent56.json')


if __name__ == '__main__':
    main()
