# -*- coding: utf-8 -*-
r"""patch_zh80.py — 特别收录分栏标题完全汉化: ELF 白名单 + XML name 同步中文化 (GR_ZH80)

背景 (GR_ZH78 回归根因, 汇编级确证):
  `SFStudio::GetSdutio(eSFStudioType)` @0x1F6E30 是 **枚举→名字** 的分派函数:
      001F6E68  addiu $v1, $v0, 30592     ; 跳转表 @0x577780[10]
      001F6E78  jr    $v0
      case0..9: RSString("Movies"/"ConceptSketches"/"Music"/"Weapon"/"Awards"/
                          "BackStory"/"SpecialistProfile"/"Background"/
                          "Interview"/"GameTrailer")
  引擎拿这个英文名去 XML 里按 `name` 属性**匹配 studio 节点** → **两侧必须一致**。
  GR_ZH78 只改了 XML 一侧 → 匹配失败 → studio 未识别 → 解锁标志全 0 → 列表全灰无光标。

本补丁 (双向同步中文化, 实现"分栏标题完全汉化"):
  A. **ELF**: 把 GetSdutio 引用的 10 个 studio 名字符串**原位改写**为中文码页字节
     (译名均 ≤ 原串长度, 原位覆写 + 0x00 收尾; 10 个译名互不相同以免索引冲突):
       Movies→影片 ConceptSketches→设定图 Music→音乐 Weapon→武器 Awards→奖章
       BackStory→幕后 SpecialistProfile→专家档案 Background→背景画面
       Interview→访谈 GameTrailer→预告片
  B. **XML** (#283): 
     - 10 个 `studio` 的 name 同步改为**同一批中文** (与 ELF 严格一致);
     - 41 个 `group` 的 name 改为中文 (group 名**无 ELF 白名单**, 属纯显示文本,
       已用全 ELF 扫描确认 Specialists/GR Mission/DS Soldiers 等均不存在于 ELF);
       等长覆写 (不足补 0x20)。
  C. 条目表 / IMG 头部不动; 保持 ISO 尺寸。

用法: python patch_zh80.py <src_iso> <dst_iso>   (基底 = GR_ZH79)
"""
import json
import os
import re
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
from lz77_decode import lzo1x_decompress                      # noqa: E402
from lzo1x_c import compress as lzo_compress                  # noqa: E402

ELF_LBA, SEC_OFF, SEC_ADDR = 295, 0x80, 0x00100000
MENU_LBA = 776286
TAB_OFF, TAB_STEP = 0x830, 48
XML_IDX = 283
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')

# ELF 里 10 个 studio 名字符串的 VA (GetSdutio 引用)
ELF_STUDIO = {
    0x577708: ('Movies', '影片'),
    0x577670: ('ConceptSketches', '设定图'),
    0x577710: ('Music', '音乐'),
    0x577718: ('Weapon', '武器'),
    0x577720: ('Awards', '奖章'),
    0x577728: ('BackStory', '幕后'),
    0x577740: ('SpecialistProfile', '专家档案'),
    0x577680: ('Background', '背景画面'),
    0x577758: ('Interview', '访谈'),
    0x577768: ('GameTrailer', '预告片'),
}
# XML group 名译名 (纯显示文本)
GROUP_ZH = {
    'Soldiers': '士兵', 'Specialists 1': '专家1', 'Specialists 2': '专家2',
    'Enemies': '敌人', 'Training': '训练', 'DS Soldiers': '沙漠士兵',
    'Ghost Recon': '幽灵行动', 'GR vehicles': '幽灵行动车辆',
    'DS vehicles': '沙漠车辆',
}
for _i in range(1, 16):
    GROUP_ZH['GR Mission %d' % _i] = '幽灵行动®任务%d' % _i
for _i in range(1, 9):
    GROUP_ZH['DS mission %d' % _i] = '沙漠风暴任务%d' % _i
    GROUP_ZH['DS Mission %d' % _i] = '沙漠风暴任务%d' % _i


def load_charset():
    c = json.load(open(CHARSET, encoding='utf-8'))
    return dict(c['codes']), {k: tuple(v) for k, v in c['pair_of'].items()}


def enc(zh, codes, pairs):
    o = bytearray()
    for ch in zh:
        if ord(ch) < 0x80:
            o.append(ord(ch))
        elif ch in codes:
            o.append(codes[ch])
        elif ch in pairs:
            o += bytes(pairs[ch])
        else:
            raise AssertionError('字表无此字: %r' % ch)
    return bytes(o)


def elf_off(va):
    return ELF_LBA * 2048 + SEC_OFF + (va - SEC_ADDR)


def subs_of(raw):
    subs, p = [], 0
    while p + 8 <= len(raw):
        L, S = struct.unpack_from('<II', raw, p)
        if L == 0 or p + 8 + L > len(raw):
            break
        try:
            dd, err, _ = lzo1x_decompress(raw[p + 8:p + 8 + L], out_size=S)
        except Exception:
            break
        if err is not None:
            break
        subs.append((bytes(dd), L, S))
        p += 8 + L
    return subs


def entry(d, idx, lba=MENU_LBA):
    base = lba * 2048
    r = struct.unpack_from('<12I', d, base + TAB_OFF + TAB_STEP * idx)
    return base, r[6], r[7], r[8]


def main(src, dst):
    codes, pairs = load_charset()
    sd = open(src, 'rb').read()
    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        # ---------- A. ELF: studio 名原位中文化 ----------
        print('=== A. ELF GetSdutio 白名单中文化 ===')
        for va, (en, zh) in sorted(ELF_STUDIO.items()):
            nb = enc(zh, codes, pairs)
            assert len(nb) <= len(en), 'ELF 串超长 %s→%s (%d>%d)' % (en, zh, len(nb), len(en))
            o = elf_off(va)
            f.seek(o)
            cur = f.read(len(en))
            assert cur == en.encode(), 'ELF 原串不符 @0x%X: %r' % (va, cur)
            f.seek(o)
            f.write(nb + b'\x00' * (len(en) + 1 - len(nb)))   # 原位覆写 + NUL 收尾
            f.seek(o)
            back = f.read(len(en) + 1)
            assert back[:len(nb)] == nb and back[len(nb)] == 0, '回读不符 %s' % en
            print('   0x%06X %-18s(len %2d) → %-8s(%dB) ✓' % (va, en, len(en), zh, len(nb)))

        # ---------- B. XML: studio + group 名中文化 ----------
        print('=== B. XML name 中文化 ===')
        base, stored, real, off = entry(sd, XML_IDX)
        subs = subs_of(sd[base + off:base + off + stored])
        assert len(subs) == 8, '子流 %d' % len(subs)
        xml = bytearray(b''.join(s[0] for s in subs))
        n_st = n_gr = 0
        for m in re.finditer(rb'<(studio|group)\s+name="([^"]*)"', bytes(xml)):
            kind = m.group(1).decode()
            en_name = m.group(2).decode('latin-1')
            if kind == 'studio':
                # studio: 用与 ELF 完全一致的中文
                zh = next((z for _va, (e, z) in ELF_STUDIO.items() if e == en_name), None)
            else:
                zh = GROUP_ZH.get(en_name)
            if zh is None:
                continue
            nb = enc(zh, codes, pairs)
            v0, v1 = m.start(2), m.end(2)
            if len(nb) > (v1 - v0):
                print('   [跳过] %s %r 译名 %dB > 原位 %dB' % (kind, en_name, len(nb), v1 - v0))
                continue
            xml[v0:v1] = nb + b' ' * (v1 - v0 - len(nb))
            if kind == 'studio':
                n_st += 1
            else:
                n_gr += 1
        print('   studio %d 处 + group %d 处 已中文化' % (n_st, n_gr))
        assert n_st == 10, 'studio 仅改 %d 处' % n_st
        assert n_gr == 41, 'group 仅改 %d 处 (期望 41)' % n_gr

        # 重打包 (按原 8 子流边界)
        sizes = [s[2] for s in subs]
        new_xml = bytes(xml)
        assert len(new_xml) == sum(sizes)
        frame = bytearray()
        q = 0
        for k, S in enumerate(sizes):
            chunk = new_xml[q:q + S]
            q += S
            c = lzo_compress(chunk, level=7, use_m1=True, use_m4=True)
            back, err, _ = lzo1x_decompress(c, out_size=S)
            assert err is None and back == chunk, '子流 %d 回环失败' % k
            frame += struct.pack('<II', len(c), S) + c
        assert len(frame) <= stored, 'XML 重压超槽 %d > %d' % (len(frame), stored)
        f.seek(base + off)
        f.write(bytes(frame) + b'\x00' * (stored - len(frame)))
        f.seek(base + off)
        rb = subs_of(f.read(stored))
        joined = b''.join(s[0] for s in rb)
        assert joined == new_xml, 'XML 回读不符'
        print('   XML 重压 %dB (槽 %d) 回读 ✓' % (len(frame), stored))

    # ---------- C. 完整性 ----------
    a, b = open(src, 'rb').read(), open(dst, 'rb').read()
    assert len(a) == len(b), 'ISO 尺寸变化'
    mbase = MENU_LBA * 2048
    assert a[mbase:mbase + TAB_OFF] == b[mbase:mbase + TAB_OFF], 'MENU 头部被改'
    assert a[mbase + TAB_OFF:mbase + TAB_OFF + TAB_STEP * 700] == \
        b[mbase + TAB_OFF:mbase + TAB_OFF + TAB_STEP * 700], 'MENU 条目表被改'
    print('=== C. ISO 尺寸/MENU 头部/条目表 未动 ✓ ===')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1], sys.argv[2])
