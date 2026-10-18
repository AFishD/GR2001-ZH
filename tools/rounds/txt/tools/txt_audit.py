# -*- coding: utf-8 -*-
r"""txt_audit.py —— 任务 A：3 个中文文本容器「逐条目 中文 payload 字节长度 vs 英文原串字节长度」审计。

只读：所有 ISO 一律 mmap(ACCESS_READ)（复用 tools\text_csv\tcslib.py 的 Iso）。
写入：work\builds\GR_TXT\audit\**

口径
----
容器清单（出处 work\tools\migrate_legacy.py CONTAINER_SPECS / CORE_TAGS）:
  LANG  MENU.IMG #25   EN_STRINGS.RES@MENU
  LANG  GR.IMG   #902  EN_STRINGS.RES@GR
  SFXML MENU.IMG #283  EN_SPECIAL_FEATURE.XML
条目 key：
  LANG  = G%02d.I%03d  (组号 1-based, 条目号 0-based) —— 与既有 dump 口径
          (work\builds\GR_TXMIG\temp\after\all_text.csv 的 source=MENU:RES/GR:RES) 完全一致
  SFXML = 第 k 条 <text> 正文 (1-based)，附所在元素的 name= 属性做界面线索

字形数（任务书口径）
  naive_bytes = 1 字节 = 1 字形（CVAR_04 用的是**原盘 ELF**，本身没有 DBCS cave；
                 但它有一个 font 级开关：DrawString 里 `lbu v1,36(font)` 决定步进 +1 还是 +2，
                 见 docs\REPORT_TEXT_OVERFLOW.md §2。故同时给出 step1 / step2 两种口径。）
"""
import hashlib
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'text_csv'))
import tcslib as T                                                       # noqa: E402

OUT = os.path.join(ROOT, 'work', 'builds', 'GR_TXT', 'audit')

ISO = {
    'EN_TRUE': r"third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso",
    'EN_ORIG': r"work\builds\GR_EN_ORIG\GR_EN_ORIG.iso",
    'ZH113b': r"work\builds\GR_ZH113b\GR_ZH113b.iso",
    'CVAR04': r"work\builds\GR_CVAR\CVAR_04_text.iso",
}
# (kind, img, lba, idx, tag)
SPECS = (
    ('LANG', 'MENU.IMG', T.MENU_LBA, 25, 'EN_STRINGS.RES@MENU'),
    ('LANG', 'GR.IMG', T.GR_LBA, 902, 'EN_STRINGS.RES@GR'),
    ('SFXML', 'MENU.IMG', T.MENU_LBA, 283, 'EN_SPECIAL_FEATURE.XML'),
)
ATTR_RE = re.compile(rb'(\w+)\s*=\s*"([^"]*)"')
TAG_RE = re.compile(rb'<(\w+)([^>]*)>')


def load_container(iso, lba, idx):
    e = iso.img_entry(lba, idx)
    raw = iso.read(e['iso_off'], e['stored'])
    subs = T.lzo_subs(raw)
    blob = b''.join(s[0] for s in subs)
    return dict(entry=e, raw=raw, subs=subs, blob=blob,
                frame_len=sum(8 + s[1] for s in subs))


def entries_of(kind, blob):
    """返回 [(key, offset, length, data, ctx)]"""
    if kind == 'LANG':
        ents, used = T.parse_lang(blob)
        out = []
        for e in ents:
            out.append(('G%02d.I%03d' % (e.g + 1, e.i), e.data_off, e.length, e.data, ''))
        return out, used
    out = []
    for (k, off, ln, body) in T.parse_sfxml(blob):
        # 找包含它的最近的开标签，取 name= 作为界面线索
        pre = blob[:off]
        tags = list(TAG_RE.finditer(pre))
        ctx = ''
        if tags:
            t = tags[-1]
            attrs = dict((a.decode('latin-1'), b.decode('latin-1'))
                         for a, b in ATTR_RE.findall(t.group(2)))
            ctx = '%s%s' % (t.group(1).decode('latin-1'),
                            (' name=%s' % attrs['name']) if 'name' in attrs else '')
        out.append(('T%03d' % k, off, ln, body, ctx))
    return out, T.xml_tail_start(blob)


def decoded(data):
    """尽力给出可读文本：GBK 解码，失败退回 latin-1（带替换标记）"""
    try:
        return data.decode('gbk')
    except UnicodeDecodeError:
        return data.decode('gbk', 'replace')


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    res = {'iso': {}, 'containers': {}, 'notes': []}
    for tag, rel in ISO.items():
        p = os.path.join(ROOT, rel)
        res['iso'][tag] = dict(path=rel, size=os.path.getsize(p))
        print('[iso] %-8s %s' % (tag, rel))

    # 缓存每盘的容器
    cache = {}
    for tag, rel in ISO.items():
        iso = T.Iso(os.path.join(ROOT, rel))
        for (kind, img, lba, idx, name) in SPECS:
            key = (tag, name)
            try:
                c = load_container(iso, lba, idx)
                ents, used = entries_of(kind, c['blob'])
            except Exception as ex:                                   # noqa: BLE001
                res['containers']['%s|%s' % (tag, name)] = dict(error=repr(ex))
                print('[!!] %-8s %-24s 解析失败: %r' % (tag, name, ex))
                continue
            sub_sizes = [s[2] for s in c['subs']]
            cache[key] = dict(ents=ents, used=used, blob=len(c['blob']),
                              frame_len=c['frame_len'],
                              entry=dict(stored=c['entry']['stored'],
                                         real=c['entry']['real'],
                                         off=c['entry']['off'],
                                         iso_off=c['entry']['iso_off']),
                              sub_real=sub_sizes)
            res['containers']['%s|%s' % (tag, name)] = dict(
                kind=kind, img=img, idx=idx,
                entry_stored=c['entry']['stored'], entry_real=c['entry']['real'],
                iso_off=c['entry']['iso_off'],
                frame_len=c['frame_len'], blob_len=len(c['blob']),
                sum_real=sum(sub_sizes), n_subs=len(sub_sizes),
                n_entries=len(ents), used_end=used,
                blob_sha256=hashlib.sha256(c['blob']).hexdigest())
            print('[ok ] %-8s %-24s blob=%-7d n=%-5d used=%-6d frame=%-6d'
                  % (tag, name, len(c['blob']), len(ents), used, c['frame_len']))
        iso.close()

    report = {}
    for (kind, img, lba, idx, name) in SPECS:
        en = cache[('EN_TRUE', name)]
        en2 = cache.get(('EN_ORIG', name))
        zh = cache[('ZH113b', name)]
        cv = cache[('CVAR04', name)]
        e_e, z_e, c_e = en['ents'], zh['ents'], cv['ents']
        rows = []
        n = min(len(e_e), len(z_e))
        same_keys = (len(e_e) == len(z_e)) and all(
            e_e[i][0] == z_e[i][0] for i in range(n))
        zh_eq_cvar = (len(z_e) == len(c_e)) and all(
            z_e[i][3] == c_e[i][3] for i in range(min(len(z_e), len(c_e))))
        for i in range(n):
            ke, oe, le, de, ce = e_e[i]
            kz, oz, lz, dz, cz = z_e[i]
            rows.append(dict(key=ke, off_en=oe, off_zh=oz,
                             len_en=le, len_zh=lz, d=lz - le,
                             en=decoded(de), zh=decoded(dz), ctx=ce or cz))
        grew = [r for r in rows if r['d'] > 0]
        shrunk = [r for r in rows if r['d'] < 0]
        same = [r for r in rows if r['d'] == 0]
        tot_en = sum(r['len_en'] for r in rows)
        tot_zh = sum(r['len_zh'] for r in rows)
        top = sorted(rows, key=lambda r: -r['d'])
        rep = dict(
            tag=name, kind=kind, img=img, idx=idx,
            n_en=len(e_e), n_zh=len(z_e), n_cvar=c_e and len(c_e),
            keys_1to1=same_keys, zh113b_eq_cvar04=zh_eq_cvar,
            n_grew=len(grew), n_shrunk=len(shrunk), n_equal=len(same),
            total_en=tot_en, total_zh=tot_zh, total_delta=tot_zh - tot_en,
            max_grow=(top[0]['d'] if top else 0),
            max_grow_key=(top[0]['key'] if top else None),
            max_shrink=(top[-1]['d'] if top else 0),
            max_shrink_key=(top[-1]['key'] if top else None),
            max_len_zh=max((r['len_zh'] for r in rows), default=0),
            max_len_en=max((r['len_en'] for r in rows), default=0),
            # 字形数口径
            glyph_naive_en=tot_en, glyph_naive_zh=tot_zh,
            glyph_step2_en=(tot_en + 1) // 2, glyph_step2_zh=(tot_zh + 1) // 2,
            entry_en=dict(stored=en['entry']['stored'], real=en['entry']['real']),
            entry_zh=dict(stored=zh['entry']['stored'], real=zh['entry']['real']),
            en_blob=en['blob'], zh_blob=zh['blob'],
            # 每个 <text>/entry 的“引擎可能撞上的固定阈值”计数
            over_64=[r['key'] for r in rows if r['len_zh'] > 64],
            over_128=[r['key'] for r in rows if r['len_zh'] > 128],
            over_255=[r['key'] for r in rows if r['len_zh'] > 255],
            over_511=[r['key'] for r in rows if r['len_zh'] > 511],
            over_1023=[r['key'] for r in rows if r['len_zh'] > 1023],
            en_over_64=[r['key'] for r in rows if r['len_en'] > 64],
            en_over_128=[r['key'] for r in rows if r['len_en'] > 128],
            en_over_255=[r['key'] for r in rows if r['len_en'] > 255],
            en_over_511=[r['key'] for r in rows if r['len_en'] > 511],
        )
        report[name] = rep
        topn = 30
        with open(os.path.join(OUT, 'A_top_growth_%s.csv'
                               % re.sub(r'[^A-Za-z0-9]+', '_', name)),
                  'w', encoding='utf-8-sig', newline='') as f:
            f.write('key,len_en,len_zh,grow,off_en,off_zh,ctx,en,zh\n')
            for r in top[:topn]:
                f.write('"%s",%d,%d,%d,0x%X,0x%X,"%s","%s","%s"\n'
                        % (r['key'], r['len_en'], r['len_zh'], r['d'], r['off_en'],
                           r['off_zh'], r['ctx'].replace('"', "'"),
                           r['en'].replace('"', "'").replace('\n', '\\n'),
                           r['zh'].replace('"', "'").replace('\n', '\\n')))
        print('[cmp] %-24s n=%-5d grew=%-5d shrunk=%-5d equal=%-5d '
              'maxgrow=%-4d total %d -> %d (%+d)'
              % (name, len(rows), len(grew), len(shrunk), len(same),
                 rep['max_grow'], tot_en, tot_zh, tot_zh - tot_en))

    res['A'] = report
    with open(os.path.join(OUT, 'A_len_audit.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print('[out] %s' % os.path.join(OUT, 'A_len_audit.json'))


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:                                                 # noqa: BLE001
        pass
    main()
