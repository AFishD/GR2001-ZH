# -*- coding: utf-8 -*-
r"""ab4_hugeface.py — 任务 1-B: `huge` 面记录号越界检查 (只读)

引擎口径 (docs/FONTRES_STRUCTURE_r83.md §2.5, 且由 cave 反汇编自证):
  单字节码 c   : idx = (c & 0xFF) - face[+0x20]        face[+0x20] = 0x20 ⇒ idx = (c-0x20)&0xFF
  对偶码 (L,T) : idx = (L-0xA1)*94 + (T-0xA1) + 0xE0   (≥ 0xE0 = 224 恒成立)
  判据         : idx < face[+0x44](= nrec = fld[4]*fld[5]) ⇒ 用记录表 ; 否则用网格公式 slot = idx-224
  ⇒ nrec < 224 时, **单字节码 c ≥ 0x20+nrec** 会掉进网格分支, 而 slot = idx-224 < 0 ⇒ 负 UV。

产出: evidence/B_huge_face.md / B_huge_face.json
"""
import csv
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ab_lib as A     # noqa: E402
import nh_lib as N     # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
CSV_BEFORE = os.path.join(A.REPO, 'work', 'builds', 'GR_TXMIG', 'temp', 'before', 'all_text.csv')
CHARSET_R82 = os.path.join(A.REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82',
                           'charset_before_r82.json')
GATE_B1 = 0xB1          # GR_ZH113b 的闸门 (LEAD_CAPACITY §1.3/§10)
LEAD_LO = 0xA1

KW = ['MAP', 'L1', 'SQUAD', 'TEAM', 'AT4', 'RPG', 'LAUNCH', 'WEAPON', 'HUD', 'AMMO',
      'FIRE', 'MSN', 'MISSION', 'OBJ', 'SOLDIER', 'RELOAD', 'GREN', 'TUBE', 'MM1',
      'CARL', 'GUSTAV', 'LAW', 'SMAW', 'PANZER']


def ft_faces(plain):
    """→ [(name, fld, [ (idx, b0,b1,u0,v0,u1,v1) ])], consumed"""
    p = 28
    n = struct.unpack_from('<I', plain, 24)[0]
    out = []
    for _ in range(n):
        l = struct.unpack_from('<I', plain, p)[0]
        p += 4
        nm = plain[p:p + l].decode('latin-1')
        p += l
        fld = list(struct.unpack_from('<14I', plain, p))
        p += 56
        nrec = fld[4] * fld[5]
        rows = []
        for r in range(nrec):
            rows.append((r,) + struct.unpack_from('<BB4H', plain, p + 10 * r))
        p += nrec * 10
        out.append((nm, fld, rows))
    return out, p, n


def tokenize(hexs, gate=GATE_B1):
    """按 GR_ZH113b 的引擎口径把 on-disk 字节切成 token。
    → [(kind, bytes, byte_value, idx)]  kind ∈ {'ascii','single','pair','orphan'}
      byte_value = 该 token 的**码值**（单字节 = 字节本身；对偶码 = (L-0xA1)*94+(T-0xA1)+0xE0）
      idx        = 引擎的记录号：单字节 = (byte_value - 0x20) & 0xFF ; 对偶 = byte_value"""
    b = bytes.fromhex(hexs)
    out, i = [], 0
    while i < len(b):
        c = b[i]
        if LEAD_LO <= c < gate and i + 1 < len(b):
            cv = (c - 0xA1) * 94 + (b[i + 1] - 0xA1) + 0xE0
            out.append(('pair', b[i:i + 2], cv, cv))
            i += 2
        elif LEAD_LO <= c < gate:
            out.append(('orphan', b[i:i + 1], c, (c - 0x20) & 0xFF))
            i += 1
        else:
            out.append(('ascii' if c < 0x80 else 'single', b[i:i + 1], c, (c - 0x20) & 0xFF))
            i += 1
    return out


def main():
    buf = io.StringIO()
    W = buf.write
    data = {}

    W('# B) `huge` 面记录号越界检查\n\n')
    W('## B.0 引擎口径（先把它钉死）\n\n')
    W('```\n'
      '单字节码 c   : idx = (c & 0xFF) − face[+0x20]          face[+0x20] = 0x20 ⇒ idx = (c − 0x20) & 0xFF\n'
      '对偶码 (L,T) : idx = (L − 0xA1)·94 + (T − 0xA1) + 0xE0  ⇒ idx ≥ 224 恒成立\n'
      '分支判据     : idx < face[+0x44] (= nrec = fld[4]×fld[5]) ⇒ 走「记录表」 ; 否则走「网格公式」\n'
      '网格分支     : slot = idx − 224 ⇒ U0 = 16·(slot % COLS) , V0 = 16·(row) + 2 …\n'
      '```\n')
    W('自证（ZH113b 的 cave 反汇编，`ISO = VA − 0x6C780`）:\n\n')
    W('```\n'
      '0x417050  lw   t2,40(a0)        ; t2 = face = this[+0x28]\n'
      '0x417054  andi v1,a1,255        ; c & 0xFF\n'
      '0x417058  srl  t4,a1,8\n'
      '0x41705C  bne  t4,zero,0x417078 ; 有 lead ⇒ 对偶分支\n'
      '0x417064  lb   a1,32(t2)        ; face[+0x20] = 0x20\n'
      '0x417068  subu v1,v1,a1         ; idx = c − 0x20\n'
      '0x41706C  andi a1,v1,255        ; idx &= 0xFF\n'
      '0x417098  lw   v1,68(t2)        ; v1 = face[+0x44] = nrec\n'
      '0x41709C  sltu v0,a1,v1         ; idx < nrec ?\n'
      '0x4170A0  bne  v0,zero,0x417134 ; 是 ⇒ 记录表\n'
      '0x4170A8  addiu t4,a1,-224      ; ★ 否则 slot = idx − 224   (nrec<224 且 idx<nrec 时 slot 为负)\n'
      '...\n'
      '0x4170E8  addiu t5,t5,3         ; SKIP_ROWS\n'
      '0x4170F8  addiu t5,t6,2         ; V0\n'
      '```\n\n')
    W('⇒ **结论（纯数学）**: 只要 nrec < 224, 立刻出现 `idx ∈ [nrec, 223]` 的单字节码走网格分支, '
      'slot = idx−224 < 0 ⇒ 负 UV。对偶码 idx ≥ 224 恒成立, 两种 nrec 下都走网格（EN 也一样）\n'
      '⇒ **对偶码完全不受 nrec 变化影响**。\n\n')

    # ---------------- 面记录数 ----------------
    W('## B.1 三个面的 nrec (EN vs ZH)\n\n')
    W('| 盘 | IMG | 条目 stored/real | 内部头 comp/real | 解压明文 | 面 | fld[4]×fld[5] | **nrec** | 记录矩形 (u1-u0)×(v1-v0) 众数 |\n')
    W('|---|---|---|---|---|---|---|---|---|\n')
    faces = {}
    for tag in ('EN_ORIG', 'ZH113b'):
        iso = N.Iso(A.ISO[tag])
        for imgk, imgp in (('MENU', A.IMG['MENU']), ('GR', A.IMG['GR'])):
            e, base, raw, ents = A.fontres_entry(iso, imgp)
            plain, comp, real, se = A.decompress_fontres(raw)
            fs, used, nface = ft_faces(plain)
            faces[(tag, imgk)] = (e, comp, real, plain, fs, raw)
            for (nm, fld, rows) in fs:
                from collections import Counter
                c = Counter((r[5] - r[3], r[6] - r[4]) for r in rows)
                mode = c.most_common(1)[0]
                W('| %s | %s | %d / %d | %d / %d | %d | `%s` | %d×%d | **%d** | %d×%d ×%d |\n'
                  % (tag, imgk, e['stored'], e['real'], comp, real, len(plain), nm,
                     fld[4], fld[5], len(rows), mode[0][0], mode[0][1], mode[1]))
        iso.close()
    W('\n槽尾: ')
    for tag in ('EN_ORIG', 'ZH113b'):
        for imgk in ('MENU', 'GR'):
            e, comp, real, plain, fs, raw = faces[(tag, imgk)]
            tail = raw[8 + comp:]
            W('%s/%s slot=%d 用=%d 尾=%d(全零=%d) ; ' % (tag, imgk, len(raw), 8 + comp, len(tail),
                                                      sum(1 for x in tail if x == 0)))
    W('\n\n')

    data['faces'] = {('%s/%s' % k): dict(stored=v[0]['stored'], real_entry=v[0]['real'],
                                          comp=v[1], real_internal=v[2], nrec=[len(f[2]) for f in v[4]])
                     for k, v in faces.items()}

    # ---------------- charset ----------------
    cs = json.load(open(CHARSET_R82, encoding='utf-8'))
    # JSON 的 codes = {char: byte}; 字符以 latin-1 装的 GBK 字节 ⇒ 还原
    def fixch(s):
        try:
            return s.encode('latin-1').decode('gbk')
        except Exception:
            return s
    single = {}
    for ch, cv in cs['codes'].items():
        single[int(cv)] = fixch(ch)
    W('## B.2 单字节码表（GR_ZH113b 时代 charset: `charset_before_r82.json`, codes=%d, pair_of=%d）\n\n'
      % (len(cs['codes']), len(cs['pair_of'])))

    def ch_of(c):
        return single.get(c)

    # ---------------- 文本 ----------------
    W('## B.3 L1 地图/小队 + 火箭筒 HUD 文案 → 记录号\n\n')
    W('语料: `work\\builds\\GR_TXMIG\\temp\\before\\all_text.csv`（实测为 **GR_ZH113b.iso** 的 dump，'
      '`summary.json.iso = GR_ZH113b.iso`✓），取 `hex_zh` 的盘上字节流。\n\n')

    rows_sel, rows_all = [], []
    hits = {}          # c -> dict(char, idx, n, strings)
    with open(CSV_BEFORE, encoding='utf-8-sig', errors='replace', newline='') as f:
        for row in csv.DictReader(f):
            hx = (row.get('hex_zh') or '').strip()
            if not hx:
                continue
            try:
                toks = tokenize(hx)
            except Exception as ex:
                continue
            rec = dict(source=row['source'], key=row['key'], en=row['en'], zh=row['zh'],
                       toks=[(k, cb.hex(), bv, ix) for (k, cb, bv, ix) in toks])
            rows_all.append(rec)
            blob = (row['key'] + '|' + (row['en'] or '') + '|' + (row['source'] or '')).upper()
            if any(k in blob for k in KW):
                rows_sel.append(rec)

    def scan(rows):
        h = {}
        for rec in rows:
            for (kind, cb, bv, ix) in rec['toks']:
                if kind in ('ascii', 'pair'):
                    continue
                d = h.setdefault(bv, dict(byte=bv, idx=ix, char=None, n=0, kind=kind, keys=[]))
                d['n'] += 1
                if len(d['keys']) < 4:
                    d['keys'].append(rec['key'])
        return h

    hits = scan(rows_sel)
    hits_all = scan(rows_all)
    for h in (hits, hits_all):
        for bv, d in h.items():
            d['char'] = ch_of(bv)
        h['__n_keys__'] = len(rows_sel) if h is hits else len(rows_all)

    W('### B.3.1 选中的界面文案条数与统计\n\n')
    W('| 口径 | 条数 | 非 ASCII 单字节码位 | 其中 **huge idx ≥ 96** | 其中 idx ≥ 224(全 nrec 都越界) |\n')
    W('|---|---|---|---|---|\n')
    for lbl, h in (('关键词命中 (L1/地图/小队/武器/火箭筒…)', hits),
                   ('全语料', hits_all)):
        rows = [v for k, v in h.items() if k != '__n_keys__']
        n = sum(v['n'] for v in rows)
        n96 = sum(v['n'] for v in rows if v['idx'] >= 96)
        n224 = sum(v['n'] for v in rows if v['idx'] >= 224)
        W('| %s | %d 条 | %d | **%d** | %d |\n' % (lbl, h.pop('__n_keys__'), n, n96, n224))
    W('\n')

    W('### B.3.2 ★ `idx ≥ 96` 的字符清单（关键词命中的界面文案）\n\n')
    W('| 单字节码 | 字符 | **idx = code−0x20** | huge(96) 判定 | 次数 | 出处 |\n')
    W('|---|---|---|---|---|---|\n')
    rows96 = sorted([v for v in hits.values() if v['idx'] >= 96], key=lambda v: -v['n'])
    for v in rows96:
        W('| 0x%02X | %s | **%d** | ★ 越界 ⇒ 网格分支 slot=%d | %d | %s |\n'
          % (v['byte'], v['char'] or '?', v['idx'], v['idx'] - 224,
             v['n'], ', '.join('`%s`' % k for k in v['keys'])))
    W('\n(共 %d 个不同单字节码 / %d 个码位)\n\n'
      % (len(rows96), sum(v['n'] for v in rows96)))

    W('### B.3.3 全语料 `idx ≥ 96` 的字符清单（完整）\n\n')
    W('| 单字节码 | 字符 | idx | huge(96) | 次数 | 例 |\n|---|---|---|---|---|---|\n')
    all96 = sorted([v for v in hits_all.values() if v['idx'] >= 96], key=lambda v: v['byte'])
    for v in all96:
        W('| 0x%02X | %s | %d | ★越界 | %d | `%s` |\n'
          % (v['byte'], v['char'] or '?', v['idx'], v['n'],
             v['keys'][0] if v['keys'] else ''))
    W('\n(共 %d 个单字节码)\n\n' % len(all96))

    # 反面对照: EN 盘
    W('### B.3.4 对照: 英文原盘\n\n')
    W('EN_ORIG 的 `huge` nrec = **224** ⇒ 单字节码 c ∈ [0x20,0xFF] 的 idx = 0..223 **恒 < 224** '
      '⇒ 永远走记录表, 不存在本缺陷。\n'
      '汉化把 huge 的 fld[5] 由 14 改成 6 ⇒ nrec 224→96 ⇒ idx ≥ 96 的码位（**全部非 ASCII 单字节码**）'
      '掉进网格分支。\n\n')

    # ---------------- 写盘 ----------------
    data['chars_ge96_key'] = rows96
    data['chars_ge96_all'] = all96
    open(os.path.join(A.EVID, 'B_huge_face.json'), 'w', encoding='utf-8').write(
        json.dumps(data, ensure_ascii=False, indent=1))
    open(os.path.join(A.EVID, 'B_huge_face.md'), 'w', encoding='utf-8').write(buf.getvalue())
    print(buf.getvalue())


if __name__ == '__main__':
    main()
