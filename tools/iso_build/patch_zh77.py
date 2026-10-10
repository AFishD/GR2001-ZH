# -*- coding: utf-8 -*-
r"""patch_zh77.py — GR.IMG 全部角色档案 (1193 个 .ATR) 人名汉化 (GR_ZH77)

用户报障 (第二条): "翻译并不完整 —— 只有训练模式里的角色名汉化了, 其它模式的人名
(显示为 '缩写+.'+全名, 如 J.Bachman) 仍是英文"。

机理: 人名显示 = ATR 文件里的 `<ActorName>` 字段。zh9 时代只汉化了 5 个 RIFLEMAN
(Corey Moss / Samuel Beard / Horace Dominguez / Garner Maxwell / Trent Norris),
训练模式恰好抽到这几个, 其它模式 (战役/快速任务/多人) 抽到未汉化的 ATR → 全英文。

本补丁 (纯数据, 零 ELF):
  遍历 GR.IMG 的 1193 个 .ATR (1192 个 stored==real 未压缩), 把 `<ActorName>` 字段内
  **纯 ASCII 的人名** 按 token 级音译表 (assets_zh77/names_zh77.json) 替换为中文,
  **原位等长覆写** (不足处补 0x20 空格, 与 zh9 时代 5 条同法), 条目表 off/stored/real
  与 IMG 头部**逐字节不动**。

硬约束 (全部断言):
  - 新值字节数 == 原字段字节数 (槽位内原位, 绝不改文件长度);
  - 译名每个字必须在 zh16 字表 (charset_compiled_zh16.json: codes 76 + pair_of 1136) 内;
  - 已有中文的字段 (zh9 的 5 条) 必须逐字节等于既有译名 (幂等, 不重译);
  - 条目表 / 头部 / 非目标文件逐字节不变 (全盘 diff 白名单 = 实际改动的字段窗口);
  - 压缩条目 (stored!=real) 跳过并计数。**本项目仅 1 条** = `D_JODIT_HAILE.ATR`
    (ActorName `Jodit Haile`, 槽 482B / payload 474B / real 1076B): 解压后改名会改变
    压缩后长度, 用 tools/gr_tools/lzo1x_c.py 重压得 486-490B > 474B 槽位 (且该串在
    LZO 流中被 match 编码, 不能原位改写字面量) → 要保持 482B 槽位就只能不动它。
    彻底修需要改条目表 stored (482→496, 正好吃掉 14B 对齐留白) 或越槽写入 —— 二者都
    违反"条目表 off/stored/real 绝对不动"的既有铁律, 故本轮**保留 1 条英文名**并在
    文档中登记 (255 条中文 / 1 条英文残留 / 937 条脚本角色键按设计保持英文)。

跳过的英文名 (脚本角色描述 / 比较键, 翻译会破坏任务脚本): 含 Soldier / Eritrean / a / an
的词, 以及 POW / Pilot / Refugee / `?` / `@` 开头的模板条目。任务脚本 (.MIS) 对这些名字
直接按字符串匹配 (POW 19 处 / Pilot 30 / Refugee 36 / Soldier 36 / Eritrean 2)。

用法: python patch_zh77.py <src_iso> <dst_iso>   (基底 = GR_ZH76)
"""
import json
import os
import re
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
GR_LBA = 19175
TAB_OFF, TAB_STEP = 0x830, 48
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
TOKENS = os.path.join(HERE, 'assets_zh77', 'names_zh77.json')
RE_NAME = re.compile(rb'<ActorName>(.*?)</ActorName>', re.S)
SKIP_TOKENS = {'Soldier', 'Eritrean', 'a', 'an'}
SKIP_NAMES = {'?', 'POW', 'Pilot', 'Refugee'}
# zh9 时代已汉化的 5 条 (文件名 → 既有译名字节, 幂等校验用)
KNOWN_ZH = {
    'RIFLEMAN-01.ATR': b'\xa6\xdd\xce\xa8\xe9\xa6\xce',
    'RIFLEMAN-11.ATR': b'\xa7\xc4\xa7\xbe\xa6\xd6\xa8\xd4\xa6\xc7',
    'RIFLEMAN-48.ATR': b'\xaa\xb3\xa9\xc6\xa3\xda\xa4\xcc\xa2\xec\xa6\xce',
    'RIFLEMAN-58.ATR': b'\xa2\xbe\xa3\xfd\xa3\xbd\xa2\xc6\xa6\xce\xa6\xc4',
    'RIFLEMAN-59.ATR': b'\xa3\xfb\xa9\xfa\xa3\xfb\xaa\xaf\xce\xa6\xce',
}


def load_charset():
    c = json.load(open(CHARSET, encoding='utf-8'))
    codes = dict(c['codes'])
    pairs = {k: list(v) for k, v in c['pair_of'].items()}
    return (set(codes) | set(pairs)), codes, pairs


def enc(zh, codes, pairs):
    """按游戏字表编码: 单字节码 (0xAF-0xFE) 优先, 否则对偶码 (lead,trail)"""
    out = bytearray()
    for ch in zh:
        if ch in codes:
            out.append(codes[ch])
        elif ch in pairs:
            out += bytes(pairs[ch])
        else:
            raise AssertionError('字表无此字: %r' % ch)
    return bytes(out)


def load_tokens():
    d = json.load(open(TOKENS, encoding='utf-8'))
    return {k: v for k, v in d.items() if isinstance(v, str) and v}


def translate(name, tok, charset):
    """英文全名 → 中文 (token 级拼接); 返回 None 表示不译"""
    parts = name.split()
    if not parts:
        return None
    if set(parts) & SKIP_TOKENS or name in SKIP_NAMES or name.startswith('@'):
        return None
    out = []
    for p in parts:
        if p not in tok:
            raise AssertionError('词素缺译: %r (来自 %r)' % (p, name))
        out.append(tok[p])
    zh = ''.join(out)
    for ch in zh:
        if ch not in charset:
            raise AssertionError('译名用字越界: %r ← %r' % (ch, name))
    return zh


def main(src, dst):
    charset, codes, pairs = load_charset()
    tok = load_tokens()
    print('[asset] 字表 %d 字 (单字节 %d + 对偶 %d); 词素译名 %d 条'
          % (len(charset), len(codes), len(pairs), len(tok)))

    shutil.copyfile(src, dst)
    base = GR_LBA * 2048
    with open(dst, 'r+b') as f:
        f.seek(base)
        head = f.read(TAB_OFF)                       # GR.IMG 头部 (含名字表偏移)
        names_off = struct.unpack_from('<I', head, 0x10)[0]
        names_end = struct.unpack_from('<I', head, 4)[0]
        f.seek(base + names_off)
        names = [x.decode('latin-1') for x in
                 f.read(names_end - names_off).split(b'\x00') if x]
        f.seek(base + TAB_OFF)
        table = f.read(TAB_STEP * len(names))         # 条目表 (48B × 4070)
        ents = [struct.unpack_from('<12I', table, TAB_STEP * i) for i in range(len(names))]

        stat = {'patched': 0, 'skipped_role': 0, 'already': 0, 'compressed': 0, 'nofield': 0}
        windows, expect = [], []
        for i, nm in enumerate(names):
            if not nm.upper().endswith('.ATR'):
                continue
            r = ents[i]
            stored, real, off = r[6], r[7], r[8]
            if stored != real:
                stat['compressed'] += 1
                assert nm not in KNOWN_ZH
                continue
            f.seek(base + off)
            raw = bytearray(f.read(real))
            m = RE_NAME.search(bytes(raw))
            if not m:
                stat['nofield'] += 1
                continue
            v0, v1 = m.start(1), m.end(1)
            cur = bytes(raw[v0:v1])
            if any(b >= 0x80 for b in cur):
                assert nm in KNOWN_ZH, '非预期中文名: %s = %r' % (nm, cur)
                assert cur.rstrip(b' ') == KNOWN_ZH[nm], \
                    '既有译名不符 %s: %r != %r' % (nm, cur.rstrip(b' '), KNOWN_ZH[nm])
                stat['already'] += 1
                continue
            en = cur.decode('ascii').rstrip(' ')
            zh = translate(en, tok, charset)
            if zh is None:
                stat['skipped_role'] += 1
                continue
            nb = enc(zh, codes, pairs)
            assert len(nb) <= len(cur), \
                '译名超长 %s: %r(%dB) > %r(%dB)' % (nm, zh, len(nb), en, len(cur))
            new = nb + b' ' * (len(cur) - len(nb))
            f.seek(base + off + v0)
            f.write(new)
            windows.append((base + off + v0, len(cur)))
            expect.append((base + off + v0, new))
            stat['patched'] += 1

        # 回读自验
        for pos, new in expect:
            f.seek(pos)
            assert f.read(len(new)) == new, '回读不符 @%d' % pos
        # 头部 + 条目表 逐字节未动
        f.seek(base)
        assert f.read(TAB_OFF) == head, 'GR.IMG 头部被改'
        f.seek(base + TAB_OFF)
        assert f.read(TAB_STEP * len(names)) == table, '条目表被改'
        print('[atr] 汉化 %d 条; 跳过(角色名) %d; 既有中文 %d; 无字段 %d; 压缩 %d'
              % (stat['patched'], stat['skipped_role'], stat['already'],
                 stat['nofield'], stat['compressed']))

    # 全盘 diff 白名单
    win = sorted(windows)
    merged = []
    for o, l in win:
        if merged and o <= merged[-1][0] + merged[-1][1]:
            e = max(merged[-1][0] + merged[-1][1], o + l)
            merged[-1] = (merged[-1][0], e - merged[-1][0])
        else:
            merged.append((o, l))
    x, y = open(src, 'rb'), open(dst, 'rb')
    pos, bad, n = 0, [], 0
    while True:
        ca, cb = x.read(1 << 22), y.read(1 << 22)
        if not ca:
            break
        if ca != cb:
            for i in range(len(ca)):
                if ca[i] != cb[i]:
                    p = pos + i
                    n += 1
                    if not any(o <= p < o + l for o, l in merged):
                        bad.append(p)
        pos += len(ca)
    x.close()
    y.close()
    assert not bad, '窗口外差异: %s' % [hex(v) for v in bad[:6]]
    assert n > 0, '没有任何差异?'
    print('[diff] 差异 %d B, 全部位于 %d 个 ATR 字段窗口内 ✓' % (n, len(merged)))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1], sys.argv[2])
