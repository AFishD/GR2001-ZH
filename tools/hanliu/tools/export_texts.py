#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""export_texts.py — 全部原始文本导出 → hanliu/texts/*.csv (汉化翻译的工作底账)

导出六张表 (全部 utf-8-sig, 可直接被 text_replace.py / 翻译流程消费):

  menu_res_en.csv   MENU.IMG EN_STRINGS.RES 展开态全量 (66 组 2232 条)
                    列: group,idx,attr,len,hex,text
  gr_res_en.csv     GR.IMG EN_STRINGS.RES 展开态全量 (66 组 2232 条, 教程/简报真身)
                    纯净源 = 原盘 ISO 内 GR.IMG(LBA 19175) 条目(off 212,604,752,
                    stored 47,619 → 展开 128,668);并与缓存基准比对
  txt_family.csv    MENU.IMG + GR.IMG 的 *_STRINGS.TXT 五语言家族 (各 222 键)
                    列: source,lang,key,value
  atr_actors.csv    GR.IMG 全部 .ATR (1193 个) XML 角色档案标签
                    列: atr,actor_name,class_name,weapon,stamina,stealth,leadership,n_tags,other_tags
  mis_briefings.csv han_v2 mis_decoded 全部 .MIS (46 个) 简报
                    列: mis,location,date,time,map_name,briefing_len,briefing_text
  pc_official_zh.csv 官方 PC 中文翻译 (GBK→UTF-8)
                    列: source,key,idx,value ;source ∈ {strings.txt, STRINGS.RES}

注意: 旧工作区 gr_img/GR.IMG 是历史实验改写副本 (EN_STRINGS.RES 被 framed 重注入),
本工具默认不使用它; 纯净数据一律从原盘 ISO 直读 (mmap 定点, 不解包全盘)。

用法:
  python tools/hanliu/tools/export_texts.py [--out texts目录] [--menu-img 路径] [--iso 原盘ISO] [--skip-iso]
选项缺省值 = 仓库相对路径 (tools/hanliu/tools 出发推导)。

文本列转义: \\t \\n \\r \\xNN (其余原样); hex 列 = 原始字节 .hex(), 二者拼合即无损。
宁少勿错: 解析失败/计数与已知基准(2232/222/1193/46/83)不符时报错退出, 不静默产出。
"""
import argparse
import csv
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lz77_decode import decode_entry            # noqa: E402
from res_encode import parse_expanded           # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # tools/hanliu/tools → 仓库根
HAN = os.path.join(REPO, 'docs', 'han_v2')
DEF_ISO = os.path.join(REPO, 'third_party', 'orig', 'ps2', "Tom Clancy's Ghost Recon (USA).iso")
DEF_MIS_DIR = os.path.join(HAN, 'mis_decoded')
DEF_PC_SHELL = os.path.join(REPO, 'third_party', 'orig', 'ghost_recon_pc', 'Data', 'Shell')
GR_RES_CACHE = os.path.join(HAN, 'GR_EN_STRINGS_RES_decoded.bin')
# 原盘 EN MENU.IMG (58MB 衍生资产不入库): 缓存于 EN 基线夹 (GR_EN_ORIG 无版本号盘,
# 与构筑夹同构), 缺失时 ensure_menu_img() 自动从原盘抽取
DEF_MENU_IMG = os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'extract', 'MENU.IMG')
MENU_LBA, MENU_SIZE = 776286, 58300882          # 见 docs/BUILD_MANIFEST.md / make_build.py
GR_IMG_LBA = 19175                              # RES_FORMAT.md §十: /GR.IMG;1 = LBA 19175
GR_RES_OFF = 212604752                          # 纯净 EN_STRINGS.RES 条目 (同文档 §十一)
GR_RES_STORED = 47619

LANGS = ('EN', 'DE', 'ES', 'FR', 'IT')
EXP_MENU_RES_ENTRIES = 2232
EXP_TXT_KEYS = 222
EXP_ATR = 1193
EXP_MIS = 46
EXP_PC_RES_KEYS = 83


def esc(raw: bytes) -> str:
    out = []
    for b in raw:
        c = chr(b)
        if c == '\\':
            out.append('\\\\')
        elif c == '\t':
            out.append('\\t')
        elif c == '\n':
            out.append('\\n')
        elif c == '\r':
            out.append('\\r')
        elif 0x20 <= b <= 0x7E:
            out.append(c)
        else:
            out.append(c if 0xA0 <= b <= 0xFF else '\\x%02x' % b)
    return ''.join(out)


def die(msg):
    raise SystemExit('[export_texts] FAIL: ' + msg)


# ------------------------------------------------------------- IMG 视图

class ImgView:
    """IMG 档案只读视图 (可叠在 ISO mmap 上: base = LBA*2048)。"""

    def __init__(self, mm, base=0):
        self.mm = mm
        self.base = base
        total = struct.unpack_from('<I', mm, base)[0]
        names_off = struct.unpack_from('<I', mm, base + 0x10)[0]
        tab_end = struct.unpack_from('<I', mm, base + 4)[0]
        raw_names = mm[base + names_off:base + tab_end]
        names = [x.decode('latin-1') for x in raw_names.split(b'\x00') if x]
        self.total = total
        self.index = {}
        for i, nm in enumerate(names):
            r = struct.unpack_from('<12I', mm, base + 0x830 + 48 * i)
            self.index[nm.upper()] = (i, r[6], r[7], r[8])

    def read(self, name):
        ent = self.index.get(name.upper())
        if ent is None:
            die('IMG 内无条目 %s' % name)
        i, stored, real, off = ent
        raw = self.mm[self.base + off:self.base + off + stored]
        if len(raw) != stored:
            die('条目 %s 读越界: stored=%d 实得=%d' % (name, stored, len(raw)))
        if stored == real:
            return raw
        out, stats = decode_entry(raw)
        bad = [s for s in stats if s[3]]
        if bad:
            die('LZO 解码失败 %s: %s' % (name, bad))
        return out


def open_iso_gr_img(iso_path):
    """从原盘 ISO mmap 出 GR.IMG 的 ImgView (定点, 不解包)。"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import mmap
    from iso_tool import parse_iso, flatten
    f = open(iso_path, 'rb')
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    fh, root = parse_iso(iso_path)
    hit = [c for c in flatten(root) if c.name.upper() == 'GR.IMG']
    fh.close()
    if not hit:
        die('ISO 内无 GR.IMG')
    lba = hit[0].lba
    if lba != GR_IMG_LBA:
        print('  提示: 本盘 GR.IMG LBA=%d (文档基准 %d)' % (lba, GR_IMG_LBA))
    return ImgView(mm, lba * 2048)


def ensure_menu_img():
    """EN 基准 MENU.IMG 缓存保障: work/builds/GR_EN_ORIG/extract 缺失时从原盘 ISO 抽取 (LBA/大小同 make_build.py)。"""
    if os.path.exists(DEF_MENU_IMG):
        return
    if not os.path.exists(DEF_ISO):
        die('无 menu-img 缓存 (%s) 且无原盘 ISO (%s)' % (DEF_MENU_IMG, DEF_ISO))
    os.makedirs(os.path.dirname(DEF_MENU_IMG), exist_ok=True)
    with open(DEF_ISO, 'rb') as f:
        f.seek(MENU_LBA * 2048)
        data = f.read(MENU_SIZE)
    assert len(data) == MENU_SIZE, 'MENU.IMG 抽取长度异常'
    open(DEF_MENU_IMG, 'wb').write(data)
    print('[menu] 原盘抽取 EN MENU.IMG → %s' % DEF_MENU_IMG)


# ------------------------------------------------------------------ 导出器

def export_menu_res(outdir):
    import mmap
    f = open(DEF_MENU_IMG, 'rb')
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    exp = ImgView(mm).read('EN_STRINGS.RES')
    groups = parse_expanded(exp)
    n = sum(len(g.strings) for g in groups)
    if n != EXP_MENU_RES_ENTRIES:
        die('MENU RES 条数 %d != 基准 %d' % (n, EXP_MENU_RES_ENTRIES))
    path = os.path.join(outdir, 'menu_res_en.csv')
    with open(path, 'w', encoding='utf-8-sig', newline='') as fo:
        w = csv.writer(fo)
        w.writerow(['group', 'idx', 'attr', 'len', 'hex', 'text'])
        for gi, g in enumerate(groups, 1):
            for ii, (s, attr) in enumerate(g.strings):
                w.writerow(['G%02d' % gi, 'I%03d' % ii, '%04X' % attr,
                            len(s), s.hex(), esc(s)])
    print('[1/6] menu_res_en.csv            %d 组 %d 条' % (len(groups), n))
    return n


def _write_res_csv(path, exp, title):
    groups = parse_expanded(exp)
    n = sum(len(g.strings) for g in groups)
    if n != EXP_MENU_RES_ENTRIES:
        die('%s 条数 %d != 基准 %d' % (title, n, EXP_MENU_RES_ENTRIES))
    with open(path, 'w', encoding='utf-8-sig', newline='') as fo:
        w = csv.writer(fo)
        w.writerow(['group', 'idx', 'attr', 'len', 'hex', 'text'])
        for gi, g in enumerate(groups, 1):
            for ii, (s, attr) in enumerate(g.strings):
                w.writerow(['G%02d' % gi, 'I%03d' % ii, '%04X' % attr,
                            len(s), s.hex(), esc(s)])
    print('%-14s %d 组 %d 条 (%d 字节)' % (title + ':', len(groups), n, len(exp)))
    return n


def export_gr_res(outdir, iso_path, skip_iso):
    path = os.path.join(outdir, 'gr_res_en.csv')
    cache = open(GR_RES_CACHE, 'rb').read() if os.path.exists(GR_RES_CACHE) else None
    if skip_iso or not os.path.exists(iso_path):
        if cache is None:
            die('无原盘 ISO 且无缓存基准 %s' % GR_RES_CACHE)
        _write_res_csv(path, cache, 'gr_res_en.csv')
        print('      (缓存基准 GR_EN_STRINGS_RES_decoded.bin)')
        return
    gr = open_iso_gr_img(iso_path)
    ent = gr.index.get('EN_STRINGS.RES')
    if ent is None:
        die('GR.IMG 内无 EN_STRINGS.RES')
    i, stored, real, off = ent
    tag = ''
    if (off, stored, real) != (GR_RES_OFF, GR_RES_STORED, len(cache or b'')):
        tag = '  [条目参数与纯净基准不同: off=%d stored=%d real=%d]' % (off, stored, real)
    exp = gr.read('EN_STRINGS.RES')
    if cache is not None and exp == cache:
        note = '实时解码 == 缓存基准 (纯净)'
    else:
        note = '警告: 实时解码 != 缓存基准, 请核查 ISO 是否原盘!' + tag
    n = _write_res_csv(path, exp, 'gr_res_en.csv')
    print('      (原盘 ISO GR.IMG off=%d stored=%d) %s' % (off, stored, note))


def export_txt_family(outdir, iso_path, skip_iso):
    rows = []
    nkeys = None
    import mmap
    f = open(DEF_MENU_IMG, 'rb')
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    views = [('MENU', ImgView(mm))]
    if not skip_iso and os.path.exists(iso_path):
        views.append(('GR', open_iso_gr_img(iso_path)))
    for src_label, view in views:
        for lang in LANGS:
            nm = '%s_STRINGS.TXT' % lang
            data = view.read(nm)
            got = 0
            for ln in data.replace(b'\r\n', b'\n').split(b'\n'):
                m = TXT_LINE.match(ln.decode('latin-1'))
                if not m:
                    continue
                rows.append([src_label, lang, m.group(1), m.group(2)])
                got += 1
            if nkeys is None:
                nkeys = got
            elif nkeys != got:
                die('%s %s 键数 %d != %d' % (src_label, nm, got, nkeys))
    if nkeys != EXP_TXT_KEYS:
        die('TXT 键数 %d != 基准 %d' % (nkeys, EXP_TXT_KEYS))
    path = os.path.join(outdir, 'txt_family.csv')
    with open(path, 'w', encoding='utf-8-sig', newline='') as fo:
        w = csv.writer(fo)
        w.writerow(['source', 'lang', 'key', 'value'])
        w.writerows(rows)
    print('[3/6] txt_family.csv             %d 行 (%d 键 × %d 语言份)'
          % (len(rows), nkeys, len(rows) // nkeys))
    return len(rows)


TXT_LINE = re.compile(r'^\t"([^"]+)"\t+"(.*)"\s*$')
TAG_KEEP = ('ActorName', 'ClassName', 'Weapon', 'Stamina', 'Stealth', 'Leadership')


def export_atr(outdir, iso_path, skip_iso):
    path = os.path.join(outdir, 'atr_actors.csv')
    if skip_iso or not os.path.exists(iso_path):
        print('[4/6] atr_actors.csv             跳过 (无原盘 ISO)')
        return 0
    gr = open_iso_gr_img(iso_path)
    atrs = sorted(k for k in gr.index if k.endswith('.ATR'))
    if len(atrs) != EXP_ATR:
        die('ATR 数 %d != 基准 %d' % (len(atrs), EXP_ATR))
    n_no_name = 0
    with open(path, 'w', encoding='utf-8-sig', newline='') as fo:
        w = csv.writer(fo)
        w.writerow(['atr', 'actor_name', 'class_name', 'weapon', 'stamina',
                    'stealth', 'leadership', 'n_tags', 'other_tags'])
        for key in atrs:
            xml = gr.read(key).decode('latin-1', 'replace')
            tags = {}
            for m in re.finditer(r'<([A-Za-z0-9_]+)>([^<]*)</\1>', xml):
                tags.setdefault(m.group(1), m.group(2))
            others = ';'.join('%s=%s' % (k, v) for k, v in sorted(tags.items())
                              if k not in TAG_KEEP)
            if not tags.get('ActorName', ''):
                n_no_name += 1
            w.writerow([key, tags.get('ActorName', ''), tags.get('ClassName', ''),
                        tags.get('Weapon', ''), tags.get('Stamina', ''),
                        tags.get('Stealth', ''), tags.get('Leadership', ''),
                        len(tags), others])
    if n_no_name:
        print('  警告: %d 个 ATR 无 ActorName' % n_no_name)
    print('[4/6] atr_actors.csv             %d 个档案' % len(atrs))
    return len(atrs)


def export_mis(outdir):
    path = os.path.join(outdir, 'mis_briefings.csv')
    files = sorted(f for f in os.listdir(DEF_MIS_DIR) if f.upper().endswith('.MIS'))
    if len(files) != EXP_MIS:
        die('MIS 数 %d != 基准 %d (源目录 %s)' % (len(files), EXP_MIS, DEF_MIS_DIR))
    n_empty = 0
    with open(path, 'w', encoding='utf-8-sig', newline='') as fo:
        w = csv.writer(fo)
        w.writerow(['mis', 'location', 'date', 'time', 'map_name',
                    'briefing_len', 'briefing_text'])
        for fn in files:
            xml = open(os.path.join(DEF_MIS_DIR, fn), 'r', encoding='latin-1').read()

            def tag(name):
                m = re.search(r'<%s>(.*?)</%s>' % (name, name), xml, re.S)
                return m.group(1) if m else ''
            brief = tag('BriefingText')
            if not brief:
                n_empty += 1
            w.writerow([fn[:-4], tag('LocationText'), tag('DateText'),
                        tag('TimeText'), tag('MapName'), len(brief), brief])
    if n_empty:
        print('  警告: %d 个 MIS 无 BriefingText' % n_empty)
    print('[5/6] mis_briefings.csv          %d 份简报' % len(files))
    return len(files)


def export_pc_zh(outdir):
    path = os.path.join(outdir, 'pc_official_zh.csv')
    rows = []
    st = open(os.path.join(DEF_PC_SHELL, 'strings.txt'), 'rb').read().decode('gbk')
    n_txt = 0
    for ln in st.splitlines():
        m = re.match(r'^\s*"([^"]+)"\s*"(.*)"\s*$', ln)
        if m:
            rows.append(['strings.txt', m.group(1), '', m.group(2)])
            n_txt += 1
    # STRINGS.RES: {u32 count} + count×{u32 klen}{key}{u8 flag}{u32 n}
    #              {n×{u32 len}{GBK bytes}{u16 0}}{u32 0} + 文件尾 {u32 0}
    d = open(os.path.join(DEF_PC_SHELL, 'STRINGS.RES'), 'rb').read()
    cnt = struct.unpack_from('<I', d, 0)[0]
    if cnt != EXP_PC_RES_KEYS:
        die('PC STRINGS.RES 键数 %d != 基准 %d' % (cnt, EXP_PC_RES_KEYS))
    off = 4
    n_res = 0
    for _ in range(cnt):
        klen = struct.unpack_from('<I', d, off)[0]
        off += 4
        key = d[off:off + klen].decode('latin-1')
        off += klen + 1                      # 键后 1 字节 flag (0x00 一般 / 0x01 ShellScenes)
        n = struct.unpack_from('<I', d, off)[0]
        off += 4
        for _j in range(n):
            ln = struct.unpack_from('<I', d, off)[0]
            off += 4
            val = d[off:off + ln].decode('gbk', 'replace')
            off += ln + 2                    # 值后 u16 0
            rows.append(['STRINGS.RES', key, str(len(rows)), val])
            n_res += 1
        off += 4                             # 键块尾 u32 0
    if struct.unpack_from('<I', d, off)[0] != 0 or off + 4 != len(d):
        die('PC STRINGS.RES 尾部异常 @0x%X / %d' % (off, len(d)))
    print('      STRINGS.RES 精确消费: %d 键 %d 值, 尾 u32 0 ✓' % (cnt, n_res))
    with open(path, 'w', encoding='utf-8-sig', newline='') as fo:
        w = csv.writer(fo)
        w.writerow(['source', 'key', 'idx', 'value'])
        w.writerows(rows)
    print('[6/6] pc_official_zh.csv         strings.txt %d 行 + STRINGS.RES %d 键 %d 值'
          % (n_txt, cnt, n_res))
    return len(rows)


def main():
    global DEF_MENU_IMG
    ap = argparse.ArgumentParser(description='导出全部原始文本 CSV')
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'texts'))
    ap.add_argument('--menu-img', default=DEF_MENU_IMG)
    ap.add_argument('--iso', default=DEF_ISO)
    ap.add_argument('--skip-iso', action='store_true',
                    help='不读原盘 ISO (gr_res/atr 用缓存基准, txt/atr 缺 GR 份)')
    a = ap.parse_args()
    if a.menu_img == DEF_MENU_IMG:
        ensure_menu_img()
    DEF_MENU_IMG = a.menu_img
    os.makedirs(a.out, exist_ok=True)
    print('输出目录: %s' % a.out)
    export_menu_res(a.out)
    export_gr_res(a.out, a.iso, a.skip_iso)
    export_txt_family(a.out, a.iso, a.skip_iso)
    export_atr(a.out, a.iso, a.skip_iso)
    export_mis(a.out)
    export_pc_zh(a.out)
    print('全部导出 PASS')


if __name__ == '__main__':
    main()
