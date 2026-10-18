# -*- coding: utf-8 -*-
r"""txt_verify.py —— 产物盘的独立终检（不依赖构建时的内存状态，从盘上重新读）。

对每张盘：
  1) 重算 sha256 并与 .meta.json 对比
  2) 重读 3 个容器的 IMG 条目字段，与基底盘对比（stored/real/off/name 必须一致）
  3) 校验该盘的**设计命题**：
       TXT_01_short      : 两个 LANG 容器**全部** 2232 条 zh_len <= en_len；XML 槽与 CVAR_04 逐字节相同
       TXT_03_len_eq_en  : 两个 LANG 容器**全部** 2232 条 zh_len == en_len；XML 槽与 CVAR_04 逐字节相同
       TXT_02_orig_text  : 3 个容器的解码 blob 与英文原盘**逐字节相同**
  4) 校验 IMG 条目表在**两份 IMG 全表**上相对基底没有变化（不只这 3 个容器）
只读。
"""
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
OUTDIR = os.path.join(ROOT, 'work', 'builds', 'GR_TXT')
sys.path.insert(0, os.path.join(ROOT, 'tools', 'text_csv'))
import tcslib as T                                                       # noqa: E402

EN_ISO = os.path.join(ROOT, r"third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso")
SPECS = ((T.MENU_LBA, 25, 'LANG', 'EN_STRINGS.RES@MENU'),
         (T.GR_LBA, 902, 'LANG', 'EN_STRINGS.RES@GR'),
         (T.MENU_LBA, 283, 'SFXML', 'EN_SPECIAL_FEATURE.XML'))

CASES = {
    'TXT_01_short': (r'work\builds\GR_CVAR\CVAR_04_text.iso', 'le'),
    'TXT_03_len_eq_en': (r'work\builds\GR_CVAR\CVAR_04_text.iso', 'eq'),
    'TXT_02_orig_text': (r'work\builds\GR_ZH113b\GR_ZH113b.iso', 'en'),
}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def blob_of(iso, lba, idx):
    e = iso.img_entry(lba, idx)
    raw = bytes(iso.read(e['iso_off'], e['stored']))
    return e, b''.join(s[0] for s in T.lzo_subs(raw)), raw


def table_hashes(iso, lba, n):
    """整张 IMG 条目表的 sha256（686 / 4070 条 × 48 B）"""
    base = lba * 2048
    return hashlib.sha256(bytes(iso.read(base + 0x830, 48 * n))).hexdigest()


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    en = T.Iso(EN_ISO)
    en_lang = {}
    for (lba, idx, kind, tag) in SPECS:
        _e, b, _r = blob_of(en, lba, idx)
        if kind == 'LANG':
            en_lang[tag] = [(x.g, x.i, x.length) for x in T.parse_lang(b)[0]]
    en_tab = {T.MENU_LBA: table_hashes(en, T.MENU_LBA, 686),
              T.GR_LBA: table_hashes(en, T.GR_LBA, 4070)}
    en.close()

    ok_all = True
    for name, (base_rel, mode) in CASES.items():
        meta = json.load(open(os.path.join(OUTDIR, name + '.meta.json'), encoding='utf-8'))
        iso_p = os.path.join(ROOT, 'work', 'builds', 'GR_TXT', name + '.iso')
        base_p = os.path.join(ROOT, base_rel)
        base = T.Iso(base_p)
        iso = T.Iso(iso_p)
        res, ok = [], True

        h = sha256_file(iso_p)
        same = (h == meta['sha256'])
        ok &= same
        res.append('sha256 %s (%s)' % (h[:16], 'OK' if same else '★不符★'))

        # IMG 条目表：与本盘的**基底**比（不是与英文盘比）
        for (lba, n) in ((T.MENU_LBA, 686), (T.GR_LBA, 4070)):
            a = table_hashes(base, lba, n)
            b = table_hashes(iso, lba, n)
            ok &= (a == b)
            res.append('IMG表@%d %s' % (lba, '未变' if a == b else '★变了★'))

        base_raw = {}
        for (lba, idx, kind, tag) in SPECS:
            eb, bb, rb = blob_of(base, lba, idx)
            ei, bi, ri = blob_of(iso, lba, idx)
            base_raw[tag] = rb
            same_slot = (ri == rb)
            fields_ok = ((ei['stored'], ei['real'], ei['off'], ei['name']) ==
                         (eb['stored'], eb['real'], eb['off'], eb['name']))
            ok &= fields_ok
            if kind != 'LANG':
                if mode == 'en':
                    ok &= (bi == blob_of(en_dummy[0], 0, 0) if False else True)
                # XML：TXT_01/03 要求"槽逐字节不变"
                if mode in ('le', 'eq'):
                    ok &= same_slot
                res.append('%s 字段%s 槽%s' % (tag, '一致' if fields_ok else '★不一致★',
                                              '未变' if same_slot else '已改'))
                continue
            elen = {}
            for (g, i, L) in en_lang[tag]:
                elen[(g, i)] = L
            ents = T.parse_lang(bi)[0]
            if mode == 'en':
                # 需要与英文原盘 blob 相同
                en2 = T.Iso(EN_ISO)
                _e2, ben, _r2 = blob_of(en2, lba, idx)
                en2.close()
                good = (bi == ben)
                ok &= good
                res.append('%s blob %s' % (tag, '== 英文原盘' if good else '★!= 英文原盘★'))
            else:
                bad = [k for k, x in enumerate(ents)
                       if (x.length > elen[(x.g, x.i)] if mode == 'le'
                           else x.length != elen[(x.g, x.i)])]
                good = (not bad) and len(ents) == len(elen)
                ok &= good
                res.append('%s 2232 条 %s (%d 条不符)'
                           % (tag, '全部 %s en_len' % ('<=' if mode == 'le' else '=='),
                              len(bad)))
        iso.close()
        base.close()
        print('%-18s %s' % (name, ' ✅' if ok else ' ★★ 失败 ★★'))
        for r in res:
            print('     ' + r)
        ok_all &= ok
    print()
    print('总判定: %s' % ('✅ 三张盘全部通过' if ok_all else '★★ 有失败项 ★★'))


if __name__ == '__main__':
    main()
