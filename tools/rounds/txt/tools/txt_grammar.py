# -*- coding: utf-8 -*-
r"""txt_grammar.py —— 用**原盘 ELF 里的真实加载器文法**去解析 EN_STRINGS.RES，与项目自有
`tcslib.parse_lang` 的文法对照，确认容器到底是哪一种（只读 ISO）。

原盘加载器证据（VA / 反汇编见 audit/B_funcfixed.txt 的 RSStringTable__ReadResource 段）:
  0053EC50 RSStringTable::ReadResource(istream&)
     read(u32)                       -> ngroups
     × ngroups:  Read(istream&,RSUIString&)   {u32 len}{len bytes}
                 read(u16)                    -> attr
                 read(u32)                    -> nstrings
     read(u32)                       -> n_strings
     × n_strings: Read(istream&,RSUIString&)  {u32 len}{len bytes}
  0053FE40 Read(istream&,RSUIString&) 实现: read u32 len; 若 len<=0 ⇒ 清空并返回(不消费字节);
           否则 new[](len+1); read(len); buf[len]=0
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'text_csv'))
import tcslib as T                                                       # noqa: E402

ISO = {
    'EN_TRUE': r"third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso",
    'ZH113b': r"work\builds\GR_ZH113b\GR_ZH113b.iso",
    'CVAR04': r"work\builds\GR_CVAR\CVAR_04_text.iso",
}
SPECS = (('MENU.IMG', T.MENU_LBA, 25, 'EN_STRINGS.RES@MENU'),
         ('GR.IMG', T.GR_LBA, 902, 'EN_STRINGS.RES@GR'),
         ('MENU.IMG', T.MENU_LBA, 283, 'EN_SPECIAL_FEATURE.XML'))


def load(iso, lba, idx):
    e = iso.img_entry(lba, idx)
    raw = iso.read(e['iso_off'], e['stored'])
    return b''.join(s[0] for s in T.lzo_subs(raw))


def parse_loader(blob, limit=None):
    """原盘加载器文法。返回 (groups, strings, end, err)"""
    p = 0
    ng, = struct.unpack_from('<I', blob, p)
    p += 4
    groups, err = [], None
    for g in range(ng):
        ln, = struct.unpack_from('<I', blob, p)
        p += 4
        if ln <= 0 or p + ln > len(blob):
            err = 'group %d: name len=%d 非法 @0x%X' % (g, ln, p)
            break
        name = blob[p:p + ln]
        p += ln
        attr, = struct.unpack_from('<H', blob, p)
        p += 2
        n, = struct.unpack_from('<I', blob, p)
        p += 4
        groups.append((g, name, attr, n, p))
    nstr, = struct.unpack_from('<I', blob, p)
    p += 4
    strings = []
    for i in range(nstr):
        if p + 4 > len(blob):
            err = 'string %d: 越界 @0x%X' % (i, p)
            break
        ln, = struct.unpack_from('<I', blob, p)
        p += 4
        if ln <= 0 or p + ln > len(blob):
            err = 'string %d: len=%d 非法 @0x%X' % (i, ln, p)
            break
        strings.append(blob[p:p + ln])
        p += ln
    return groups, strings, p, err


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    for tag, rel in ISO.items():
        iso = T.Iso(os.path.join(ROOT, rel))
        for (img, lba, idx, name) in SPECS:
            if 'XML' in name:
                continue
            blob = load(iso, lba, idx)
            print('=' * 78)
            print('%s  %s  blob=%d' % (tag, name, len(blob)))
            print('  头 64 B: %s' % blob[:64].hex(' '))
            ents, used = T.parse_lang(blob)
            print('  [项目 parse_lang  ] ngroups=%d 条目=%d used_end=%d 余=%d'
                  % (struct.unpack_from('<I', blob, 0)[0], len(ents), used,
                     len(blob) - used))
            try:
                gs, ss, end, err = parse_loader(blob)
                print('  [原盘加载器文法] ngroups=%d n_strings=%d end=%d 余=%d err=%s'
                      % (len(gs), len(ss), end, len(blob) - end, err))
                for (g, nm, at, n, off) in gs[:10]:
                    print('      g%-3d name_len=%-4d attr=0x%04X nstrings=%-4d @0x%X  %r'
                          % (g, len(nm), at, n, off, nm[:32]))
            except Exception as ex:                                   # noqa: BLE001
                print('  [原盘加载器文法] 解析异常: %r' % (ex,))
        iso.close()


if __name__ == '__main__':
    main()
