# -*- coding: utf-8 -*-
r"""font_usage.py — 字库「用量核算 + 码位/格位回收」工具 (round38)

═══════════════════════════════════════════════════════════════════════════════
这个工具解决什么问题
═══════════════════════════════════════════════════════════════════════════════

现有的「字库覆盖预检」(tools/text_csv/inject_text_csv.py 的 charset_precheck)
**只做加法、不做减法**:

    · 它只统计「**将被写入的文本**里、字库没有的字」  → 缺字 (加法)
    · 它**从不统计**「字库里**有**、但全盘文本已经不再使用」的字 → 闲置 (减法)

于是字库只会越来越大: 改一次译就多几个字, 老字永远占着码位与图集格位,
即使游戏里再也不会画它。本工具补上「减法」那一半。

═══════════════════════════════════════════════════════════════════════════════
★ 方法论 (本工具的核心, 全部结论都可复现)
═══════════════════════════════════════════════════════════════════════════════

【已证伪的旧方法 —— 别再用】
    在**整个 1.6 GB ISO** 里搜某个字的 2 字节编码, 命中就算"还在用"。
    **无效**。实测: 全盘 65536 种 2 字节组合 **全部出现** (见报告 T3 一节)。
    ⇒ 每个字都"找得到", 这个判据的信息量为 **0**。

【本工具的四级证据】

    E0 结构化文本 (最精确)
        LANG (EN_STRINGS.RES, 两份拷贝) 用 tcslib.parse_lang 逐条取正文;
        SFXML (EN_SPECIAL_FEATURE.XML)  用 tcslib.parse_sfxml 逐条取 <text> 正文。
        ⇒ 这是**引擎真正会画出来**的字集合, 没有阈值、没有猜测。

    E1 其它"可能装文本"的容器里的可读串
        XML / TXT / MIS / ATR / RES / ELF / 其它 ISO 文件 —— 用 charset 感知的
        字节扫描, 取长度 >= 4 的"像文本的串"里解码出来的字。

    E2 结构上不可能画字的容器里的可读串
        RSB(贴图) / PAK(打包) / MEDIA(视频音频) / OTHER —— 同样扫, 但**分开统计**。

    E3 原始字节 (无信息量)
        编码在任意上下文的原始字节里出现过。只作对照, 不作为判据。

【★ 假阳性对照 —— 把"噪声"变成**可测量、可证明**的东西】
    给一张**英文原盘** (默认 work/builds/GR_EN_ORIG/GR_EN_ORIG.iso)。英文盘里
    **没有中文**, 所以任何"在英文盘里被命中的中文字"都**必然是巧合**。

    本工具逐容器比对两张盘, 并做**集合减法**:
        某容器的证据 = 中文盘在该容器里的命中  −  英文盘在**同一个容器**里的命中
    这为什么成立:
      · 若容器**逐字节相同** ⇒ 两边的命中集合**逐元素相同** ⇒ 减完是空集
        (**可证明**该容器不含任何中文信息);
      · 若容器不同 (本地化动过) ⇒ 只有"英文盘没有、中文盘才有"的命中才算证据。

    实测 (GR_ZH92 vs GR_EN_ORIG, 4713 个容器): 相同 **4683** 个, 不同 **30** 个。
    那 30 个里, 除 LANG / SFXML 外, 其余 (贴图/字库/主程序) 减完**一个新字都不剩**。

【回收判据】
    --policy text   (默认): 不在 E0、也不在 E1  ⇒ 可回收
    --policy strong        : 不在 E0            ⇒ 可回收 (更激进)
    --policy strict        : 不在 E0/E1/E2/E3   ⇒ 可回收 (最保守; 实测 = 0 个)
    给了对照盘时, E1/E2 一律先做上面的集合减法。

═══════════════════════════════════════════════════════════════════════════════
用法
═══════════════════════════════════════════════════════════════════════════════

  # ① 只核算「字库 vs 全盘用量」(不读文本表)
  python tools/font_pipeline/font_usage.py --iso work/builds/GR_ZH92/GR_ZH92.iso

  # ② 完整核算 (含新文本缺字清单) + 两份报告
  python tools/font_pipeline/font_usage.py --iso work/builds/GR_ZH92/GR_ZH92.iso ^
      --text-dir work/builds/GR_ZH92/text ^
      --md <报告.md> --json <报告.json>

  # ③ 看回收方案 (**不写任何文件** —— dry-run 是默认)
  ... --apply --dry-run

  # ④ 真的落盘 (必须二次确认; 写出**新** charset JSON, 绝不覆盖原文件)
  ... --apply --yes-really --out-charset <新文件.json> --out-plan <重排计划.json>

  # ⑤ 回收后自检 (用回收后的 charset 重新扫一遍盘)
  ... --apply --dry-run --verify
  ... --charset <新文件.json> --verify

退出码: 0 正常 / 1 自检或结构性失败 / 2 参数错 / 3 --apply 被拒绝
"""
import argparse
import copy
import hashlib
import io
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T                                                  # noqa: E402

# ─────────────────────────────── 常量 ───────────────────────────────
DEFAULT_ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
DEFAULT_CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                               'charset_compiled_zh16.json')
DEFAULT_CONTROL = os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso')
EMPTY_SENTINEL = '[[empty]]'          # 与 inject_text_csv.py 同口径 (清空一条的哨兵)

LEGAL_LEAD_LO, LEGAL_LEAD_HI = 0xA1, 0xAE     # 引擎只认 lead 0xA1..0xAD
TRAIL_LO, TRAIL_HI = 0xA1, 0xFE               # 对偶 trail 实测区间 (94 个)
GRID_NCOL, GRID_CW, GRID_CH = 62, 16, 16
GRID_X0, GRID_Y0 = 4, 2
GRID_SKIP_ROW, GRID_SKIP_ROWS = 12, 3
BTN_BYTES = (0xB1, 0xB5, 0xE7, 0xF1)          # 手柄按键图标控制字节 (合法文本字节)

TEXT_RUN_MIN = 4          # E1: "可能装文本"的容器, 可读串最小长度
DEFAULT_MIN_RUN = 16      # E2: 结构上不可能画字的容器, 可读串最小长度
THRESHOLDS = (4, 8, 16, 24, 32, 48)   # 敏感性分析用

# 容器分类: text=True ⇒ 归入 E1; text=False ⇒ 归入 E2
KIND_RULES = {
    'LANG':   (True, '语言表 EN_STRINGS.RES'),
    'SFXML':  (True, '特别收录 EN_SPECIAL_FEATURE.XML'),
    'XML':    (True, '其它 .XML'),
    'MIS':    (True, '.MIS 任务/简报'),
    'TXT':    (True, '.TXT 纯文本'),
    'RES':    (True, '其它 .RES 资源表'),
    'ATR':    (True, '.ATR 人名'),
    'ELF':    (True, 'SLUS_206.13 主程序'),
    'ISO_FILE': (True, 'IMG 以外的 ISO 文件'),
    'RSB':    (False, '贴图容器'),
    'PAK':    (False, '打包容器'),
    'MEDIA':  (False, '视频/音频流'),
    'OTHER':  (False, '其它'),
}
TEXT_KINDS = tuple(k for k, v in KIND_RULES.items() if v[0])
KIND_DESC = {k: v[1] for k, v in KIND_RULES.items()}

MEDIA_EXT = {'.PSS', '.SS', '.TM', '.MPG', '.M2V', '.SB', '.MAB', '.MAH', '.SH', '.SHT'}
RSB_EXT = {'.RSB', '.BMZ', '.MAZ', '.CHZ', '.QOZ', '.POZ', '.QOB', '.ICO', '.GTF', '.BMH'}
PAK_EXT = {'.PAK', '.PSF', '.CSF', '.PSF_BIN', '.CSF_BIN'}

ASCII_STR_RE = re.compile(rb'[\x20-\x7e]{4,}')
PUA_LO, PUA_HI = 0xE000, 0xE0FF


# ═════════════════════════════ 字符集 ═════════════════════════════

class CharsetIndex:
    """charset JSON 的只读视图 + 扫描索引。

    ★ 解码口径**严格等于 tcslib.Charset.decode** (单字节码优先 → 再对偶 → 私有区回落)。
      历史待办: tools/diag/res_text_dump.py 的 dec() 用的是**对偶优先**, 与本工程口径
      **不一致** (会把 AF A1 BD 解成「弗开」而不是「的方」)。本工具不复制那个错误口径,
      并用 --selfcheck 的真实字节用例把它钉死。
      (本轮只新增文件 / 只读调用 ⇒ 没有改动 res_text_dump.py; 结论已写进报告交给 Lead。)
    """

    def __init__(self, path=DEFAULT_CHARSET):
        self.path = os.path.abspath(path)
        self.raw = json.load(io.open(path, encoding='utf-8'))
        self.enc_single = {ch: int(v) for ch, v in self.raw['codes'].items()}
        self.enc_pair = {ch: tuple(v) for ch, v in self.raw['pair_of'].items()}
        self.codes = {v: ch for ch, v in self.enc_single.items()}
        self.pair_of = {v: ch for ch, v in self.enc_pair.items()}
        self.chars = sorted(set(self.enc_single) | set(self.enc_pair))
        self.protected = {int(x, 16) for x in self.raw.get('protected', [])}
        self.mark_codes = {int(x, 16) for x in self.raw.get('mark_codes', [])}
        self.alphabet = bytes(sorted(
            set(range(0x20, 0x7F)) | set(self.codes) |
            {p[0] for p in self.pair_of} | {p[1] for p in self.pair_of} | set(BTN_BYTES)))
        self._rx = {}

    # ---------- 解码 ----------
    def decode_chars(self, b):
        """按引擎口径解码, 返回「真字符」列表 (丢掉控制字符与私有区回落)。

        分支顺序与 tcslib.Charset.decode **逐条一致** (单字节优先), 但不分配
        map 数组 ⇒ 快得多。返回值里的 ASCII 也是字符 (str), 便于统一处理。
        """
        out = []
        i, n = 0, len(b)
        pairs, codes = self.pair_of, self.codes
        while i < n:
            v = b[i]
            if v < 0x80:
                if 0x20 <= v < 0x7F:
                    out.append(chr(v))
                i += 1
            elif 0xA1 <= v < 0xAE and i + 1 < n and (v, b[i + 1]) in pairs:
                out.append(pairs[(v, b[i + 1])])
                i += 2
            elif v in codes:
                out.append(codes[v])
                i += 1
            else:
                i += 1
        return out

    def decode_text(self, b):
        return T.Charset(self.path).decode(b)[0]

    # ---------- 编码侧 ----------
    def encodable(self, ch):
        if ord(ch) < 0x80:
            return True
        if ch in self.enc_single:
            return True
        p = self.enc_pair.get(ch)
        return bool(p) and LEGAL_LEAD_LO <= p[0] < LEGAL_LEAD_HI

    def code_bytes(self, ch):
        if ch in self.enc_single:
            return (self.enc_single[ch],)
        p = self.enc_pair.get(ch)
        return tuple(p) if p else None

    def kind_of(self, ch):
        if ch in self.enc_single:
            return 'single'
        if ch in self.enc_pair:
            p = self.enc_pair[ch]
            return 'pair' if LEGAL_LEAD_LO <= p[0] < LEGAL_LEAD_HI else 'dead_pair'
        return 'none'

    def slot_of(self, ch):
        p = self.enc_pair.get(ch)
        return pair_slot(p) if p else None

    def run_re(self, min_len):
        rx = self._rx.get(min_len)
        if rx is None:
            rx = re.compile(b'[' + re.escape(self.alphabet) + b']{%d,}' % min_len)
            self._rx[min_len] = rx
        return rx

    def pair_capacity(self):
        used = [p for p in self.pair_of if LEGAL_LEAD_LO <= p[0] < LEGAL_LEAD_HI]
        used94 = [p for p in used if TRAIL_LO <= p[1] <= TRAIL_HI]
        total94 = (LEGAL_LEAD_HI - LEGAL_LEAD_LO) * (TRAIL_HI - TRAIL_LO + 1)
        return dict(total=total94, used=len(used94), free=total94 - len(used94),
                    used_any_trail=len(used),
                    dead=sum(1 for p in self.pair_of if p[0] >= LEGAL_LEAD_HI),
                    single_used=len(self.enc_single))


def pair_slot(pair):
    """对偶码 → 图集格位号 (与 ELF cave / tcslib.atlas_cell_xy 同一张配方单)。"""
    return (pair[0] - 0xA1) * 94 + (pair[1] - 0xA1)


def slot_cell(slot):
    """格位号 → 图集格左上角 (x, y)。

        col = slot % 62, row = slot // 62
        x = 4 + 16*col, y = 2 + 16*(row + 3*[row >= 12])
    """
    col, row = slot % GRID_NCOL, slot // GRID_NCOL
    x = GRID_X0 + GRID_CW * col
    y = GRID_Y0 + GRID_CH * (row + (GRID_SKIP_ROWS if row >= GRID_SKIP_ROW else 0))
    return x, y


# ═════════════════════════ 容器枚举 ═════════════════════════

def enum_img_containers(iso, lba, tag):
    base = lba * T.SEC
    noff = struct.unpack_from('<I', iso.mm, base + 0x10)[0]
    nend = struct.unpack_from('<I', iso.mm, base + 4)[0]
    names = [x.decode('latin-1')
             for x in bytes(iso.mm[base + noff:base + nend]).split(b'\x00') if x]
    out = []
    for i, nm in enumerate(names):
        r = struct.unpack_from('<12I', iso.mm, base + T.TAB_OFF + T.TAB_STEP * i)
        stored, real, off = r[6], r[7], r[8]
        if not stored or not off:
            continue
        out.append(dict(img=tag, lba=lba, idx=i, name=nm, stored=stored,
                        real=real, off=off))
    return out


def iso_file_list(iso):
    """ISO9660 根目录树 → [(path, lba, size)] (只读)"""
    pvd = 16 * T.SEC
    root_lba = struct.unpack_from('<I', iso.mm, pvd + 158)[0]
    root_size = struct.unpack_from('<I', iso.mm, pvd + 166)[0]
    files, stack = [], [(root_lba, root_size, '')]
    while stack:
        lba, size, pre = stack.pop()
        data = bytes(iso.mm[lba * T.SEC:lba * T.SEC + size])
        i = 0
        while i < len(data):
            L = data[i]
            if L == 0:
                i = (i // T.SEC + 1) * T.SEC
                if i >= len(data):
                    break
                continue
            if i + L > len(data) or L < 34:
                break
            rec = data[i:i + L]
            nm = rec[33:33 + rec[32]].decode('latin-1')
            ext = struct.unpack_from('<I', rec, 2)[0]
            sz = struct.unpack_from('<I', rec, 10)[0]
            fl = rec[25]
            i += L
            if nm in ('\x00', '\x01'):
                continue
            p = pre + '/' + nm if pre else nm
            if fl & 2:
                stack.append((ext, sz, p))
            else:
                files.append((p.split(';')[0], ext, sz))
    return files


def classify(name, img, idx):
    up = name.upper()
    if name == 'EN_STRINGS.RES' and ((img == 'MENU.IMG' and idx == T.LANG_MENU_IDX) or
                                     (img == 'GR.IMG' and idx == T.LANG_GR_IDX)):
        return 'LANG'
    if name == 'EN_SPECIAL_FEATURE.XML':
        return 'SFXML'
    if img == 'ISO_FILE':
        return 'ELF' if up.startswith('SLUS') else 'ISO_FILE'
    e = os.path.splitext(up)[1]
    if e == '.XML':
        return 'XML'
    if e == '.MIS':
        return 'MIS'
    if e == '.TXT':
        return 'TXT'
    if e == '.ATR':
        return 'ATR'
    if e == '.RES':
        return 'RES'
    if e in RSB_EXT:
        return 'RSB'
    if e in PAK_EXT:
        return 'PAK'
    if e in MEDIA_EXT:
        return 'MEDIA'
    return 'OTHER'


def container_key(c):
    return (c['img'], c['idx'], c['name'])


def container_blob(iso, c):
    """容器的**引擎可见内容**: LZO 子流解开; 没有子流就是原始字节。"""
    base = c['lba'] * T.SEC
    raw = bytes(iso.mm[base + c['off']:base + c['off'] + c['stored']])
    if c['stored'] != c['real'] or c['img'] == 'ISO_FILE':
        subs = T.lzo_subs(raw)
        if subs:
            return b''.join(s[0] for s in subs), raw
    return raw, raw


def container_sha1(iso, c):
    base = c['lba'] * T.SEC
    return hashlib.sha1(bytes(iso.mm[base + c['off']:base + c['off'] + c['stored']])).hexdigest()


def build_container_list(iso, extra_iso_files=True):
    cs = []
    for lba, tag in ((T.GR_LBA, 'GR.IMG'), (T.MENU_LBA, 'MENU.IMG')):
        cs += enum_img_containers(iso, lba, tag)
    if extra_iso_files:
        for path, lba, size in iso_file_list(iso):
            if os.path.basename(path).upper() in ('GR.IMG', 'MENU.IMG') or not size:
                continue
            cs.append(dict(img='ISO_FILE', lba=lba, idx=-1, name=path,
                           stored=size, real=size, off=0))
    for c in cs:
        c['kind'] = classify(c['name'], c['img'], c['idx'])
        c['text'] = KIND_RULES.get(c['kind'], (False, ''))[0]
    return cs


# ═════════════════════════ 扫描 ═════════════════════════

def blob_hits(blob, idx, decode_min, thresholds):
    """一次 regex 扫描 + 按需解码 → ``{阈值: set(字)}``。

    可读串 = 连续 N 个字节都落在「ASCII 可打印 / 单字节码 / 对偶 lead / 对偶 trail /
    按键字节」这 189 个值里。真文本天然满足; 随机二进制满足的概率很低
    (实测: >=16 的串只覆盖全盘 2.9% 的字节, >=24 只覆盖 1.7%)。
    """
    out = {t: set() for t in thresholds}
    if not blob:
        return out
    for m in idx.run_re(4).finditer(blob):
        L = m.end() - m.start()
        if L < decode_min:
            continue
        chars = None
        for t in thresholds:
            if L >= t:
                if chars is None:
                    chars = idx.decode_chars(m.group(0))
                out[t] |= set(chars)
    return out


def parse_lang_chars(blob, idx):
    """E0: 语言表**逐条正文**解码 (tcslib.parse_lang 口径)。返回 (chars, note)。"""
    try:
        ents, used_end = T.parse_lang(blob)
    except Exception as ex:                                         # noqa: BLE001
        return None, 'parse_lang 失败: %s' % ex
    if not ents or used_end > len(blob):
        return None, 'parse_lang 结果不可信 (entries=%d, used_end=%d, blob=%d)' % (
            len(ents), used_end, len(blob))
    chars = set()
    for e in ents:
        chars |= set(idx.decode_chars(e.data))
    return chars, 'parse_lang: %d 条正文 (有效区 %d B)' % (len(ents), used_end)


def parse_sfxml_chars(blob, idx):
    """E0: 特别收录 XML 的 <text> 正文解码 (tcslib.parse_sfxml 口径)。"""
    try:
        items = T.parse_sfxml(blob)
    except Exception as ex:                                         # noqa: BLE001
        return None, 'parse_sfxml 失败: %s' % ex
    if not items:
        return None, 'parse_sfxml 没有找到任何 <text>'
    chars = set()
    for (_k, _o, _l, body) in items:
        chars |= set(idx.decode_chars(body))
    return chars, 'parse_sfxml: %d 条 <text> 正文' % len(items)


def bigram_presence(blobs, chunk=1 << 22):
    """全盘「任意字节 / 任意 2 字节序列是否出现过」—— 用于证明 E3 口径无信息量。"""
    try:
        import numpy as np
    except ImportError:                                             # noqa: BLE001
        return None, None
    acc = np.zeros(65536, dtype=np.int64)
    b1 = np.zeros(256, dtype=np.int64)
    for blob in blobs:
        n = len(blob)
        off = 0
        while off < n:
            end = min(n, off + chunk)
            seg = np.frombuffer(blob[off:end], dtype=np.uint8)
            b1 += np.bincount(seg, minlength=256)
            if len(seg) >= 2:
                v = seg[:-1].astype(np.uint16) * np.uint16(256) + seg[1:].astype(np.uint16)
                acc += np.bincount(v, minlength=65536)[:65536]
            off = end
    return b1 > 0, acc > 0


def apply_debug_limit(containers, n):
    """★ 调试截断: 只留前 N 个容器, 但**始终保留 LANG / SFXML** (否则 E0 为空, 毫无意义)。

    ⚠ 截断后**决策与 --verify 用同一份容器表** (口径一致), 但结论不可用于正式判断 ——
      没扫到的容器里的字会被误判为可回收。
    """
    if not n or n >= len(containers):
        return containers
    keep = [c for c in containers if c['kind'] in ('LANG', 'SFXML')]
    rest = [c for c in containers if c['kind'] not in ('LANG', 'SFXML')]
    return rest[:max(0, n - len(keep))] + keep


def scan_disc(iso, idx, containers, ctrl=None, nontext_min_run=DEFAULT_MIN_RUN,
              verbose=True, progress_every=600):
    """扫全盘 → 每个容器的四级证据 (给了对照盘就做**集合减法**)。

    ctrl = dict(iso=<对照 Iso>, map={(img,idx,name): container}) 或 None

    返回 dict(per, e0, e1, e2, ctrl_e1, ctrl_e2, ctrl_e0, by_kind, blob_bytes,
              stored_bytes, t3_byte, t3_bigram, n_containers)
    """
    per = []
    e0, e1, e2 = set(), set(), set()
    ce0, ce1, ce2 = set(), set(), set()
    by_kind = {}
    blob_total = stored_total = 0
    blobs_for_t3 = []
    for n, c in enumerate(containers):
        blob, _raw = container_blob(iso, c)
        blob_total += len(blob)
        stored_total += c['stored']
        th = (TEXT_RUN_MIN, nontext_min_run)
        dec_min = TEXT_RUN_MIN if c['text'] else max(TEXT_RUN_MIN, nontext_min_run)
        h = blob_hits(blob, idx, dec_min, th)
        # 结构化精确解码 (只对 LANG / SFXML)
        e0_c, e0_note = None, None
        if c['kind'] == 'LANG':
            e0_c, e0_note = parse_lang_chars(blob, idx)
        elif c['kind'] == 'SFXML':
            e0_c, e0_note = parse_sfxml_chars(blob, idx)
        # 对照侧
        oc = ctrl['map'].get(container_key(c)) if ctrl else None
        oh = None
        if ctrl is not None:
            if oc is None:
                oh = {t: set() for t in th}
            else:
                oblob, _oraw = container_blob(ctrl['iso'], oc)
                oh = blob_hits(oblob, idx, dec_min, th)
        cut = (lambda s, t: (s - oh[t]) if oh is not None else set(s))
        raw1, raw2 = h[TEXT_RUN_MIN], h[nontext_min_run]
        ev1 = cut(raw1, TEXT_RUN_MIN) if c['text'] else set()
        ev2 = set() if c['text'] else cut(raw2, nontext_min_run)
        ev0 = set(e0_c) if e0_c else set()
        ev = ev0 | ev1 | ev2
        per.append(dict(img=c['img'], idx=c['idx'], name=c['name'], kind=c['kind'],
                        stored=c['stored'], real=c['real'], blob=len(blob),
                        e0=ev0, e1=ev1, e2=ev2, ev=ev,
                        raw1=raw1, raw2=raw2, ctrl1=(oh or {}).get(TEXT_RUN_MIN, set()),
                        ctrl2=(oh or {}).get(nontext_min_run, set()),
                        n_runs4=0, e0_note=e0_note,
                        identical=(ctrl is not None and oc is not None and
                                   c['stored'] == oc['stored'] and
                                   container_sha1(iso, c) == container_sha1(ctrl['iso'], oc))))
        if c['text']:
            e1 |= ev1
            ce1 |= raw1
        else:
            e2 |= ev2
            ce2 |= raw2
        e0 |= ev0
        if e0_c:
            ce0 |= set(e0_c)
        d = by_kind.setdefault(c['kind'], dict(n=0, stored=0, blob=0, chars=set(),
                                               e0=set(), e1=set(), e2=set(),
                                               raw_chars=set(), containers=[]))
        d['n'] += 1
        d['stored'] += c['stored']
        d['blob'] += len(blob)
        d['chars'] |= ev
        d['e0'] |= ev0
        d['e1'] |= ev1
        d['e2'] |= ev2
        d['raw_chars'] |= raw1 | raw2
        d['containers'].append((c['img'], c['idx'], c['name'], len(blob)))
        blobs_for_t3.append(blob)
        if verbose and progress_every and (n + 1) % progress_every == 0:
            print('    …已扫 %d/%d 个容器 (%.0f MB)'
                  % (n + 1, len(containers), blob_total / 1048576))
    if verbose:
        print('    …已扫 %d/%d 个容器 (%.0f MB)'
              % (len(containers), len(containers), blob_total / 1048576))
    t3b, t3g = bigram_presence(blobs_for_t3)
    return dict(per=per, e0=e0, e1=e1, e2=e2, ctrl_e1=ce1, ctrl_e2=ce2, ctrl_e0=ce0,
                by_kind=by_kind, blob_bytes=blob_total, stored_bytes=stored_total,
                t3_byte=t3b, t3_bigram=t3g, n_containers=len(containers))


def char_to_t3(ch, idx, present_byte, present_bigram):
    if present_byte is None:
        return None
    if ch in idx.enc_single:
        return bool(present_byte[idx.enc_single[ch]])
    p = idx.enc_pair.get(ch)
    if not p:
        return False
    return bool(present_bigram[p[0] * 256 + p[1]])


# ═════════════════════════ 文本表 ═════════════════════════

def cell_chars(cell):
    """CSV 单元格 → 字符集合 (剔掉工具标记 / 换行 / 控制字符)。"""
    s = T.WRAP_RE.sub('', cell)
    s = T.BTN_RE.sub('', s)
    return {c for c in s if ord(c) >= 0x20 and c not in '\r\n\t' and ord(c) != 0x7F}


def read_text_tables(spec):
    paths, notes = T.expand_csv_inputs([spec])
    rows, files = [], []
    for p in paths:
        rs, _cols = T.read_table_rows(p)
        files.append(dict(path=p, rows=len(rs)))
        for r in rs:
            zh = r.get('text_zh', '')
            ed = r.get('text_edited', '')
            use_ed = bool(ed.strip()) and ed.strip() != EMPTY_SENTINEL
            rows.append(dict(id=r.get('id', '').strip(), file=os.path.basename(p),
                             kind=r.get('kind', '').strip(),
                             cur=cell_chars(zh), new=cell_chars(ed if use_ed else zh),
                             changed=bool(use_ed and ed != zh)))
    return rows, files, notes


# ═════════════════════════ 回收核算 ═════════════════════════

def split_by_code(idx, chars):
    """按**编码器优先级**把字分成 (单字节, 合法对偶, 死对偶) 三组。

    ★ 同一个字可能**同时**有单字节码和对偶码 —— 实测现役 charset 有 5 个
      (`延 志 普 略 米`, 它们的对偶都是死 pair)。`encode()` 的分支顺序是
      `enc_single` → `enc_pair` ⇒ **单字节优先**, 对偶那一份是"死重量"(永不被编码)。
      分类必须照同一优先级, 否则会**重复计数**(三组之和会大于字数)。
    """
    singles, pairs, dead = [], [], []
    for ch in chars:
        if ch in idx.enc_single:
            singles.append(ch)
        elif ch in idx.enc_pair:
            (pairs if LEGAL_LEAD_LO <= idx.enc_pair[ch][0] < LEGAL_LEAD_HI
             else dead).append(ch)
    return singles, pairs, dead


def compute_reclaim(idx, usage, policy='text', denoised=True, ignore_reserved=False,
                    needed_chars=None):
    """算出「可回收字」与「被拦下的字 (及原因)」。

    可回收 = 字库里有、但四级证据里都**没有**它 (给了对照盘时, E1/E2 已减掉对照命中)。

    ★★ needed_chars (来自 --text-dir 的新译文用字) **必须排除** —— 这是硬要求:
       回收是为了给新字腾格位; 若把新译文自己要用到的字回收掉, 就自相矛盾了
       (它会同时出现在"缺字清单"和"可回收清单"里)。实测确实存在这种字:
       现役盘没用到、但新译文用到了 ⇒ 必须拦住。

    ★ 「死 pair」(lead>=0xAE, 引擎 sltiu 读不了) **不算拦截理由** —— 它们是字符表里的
      历史残留, 解码器永远不会产出它们 (decode 只认 lead 0xA1..0xAD), 编码器也拒绝写出。
      把它们摘掉是**清理**, 不是"回收格位"; 报告里单独统计 (不占合法对偶空间)。

    ★ protected / mark_codes 按 tools/hanliu/tools/font_build.py 的原意**只管单字节码**
      (PROTECTED = 0xAE,0xB1,0xB5,0xE7,0xF1 = 英文盘在用的 ® ± µ ç ñ; MARK_CODES =
      0xA1,0xA2,0xA3 = v5 ELF 标记码)。text_replace.py 的用法同样是 `ch in self.codes`
      (单字节表) 才查 mark_codes ⇒ 对偶字的 lead/trail **不**受这两个列表约束。
    """
    e0, e1, e2 = usage['e0'], usage['e1'], usage['e2']
    need = set(needed_chars or ())
    reclaim, blocked = [], {}
    for ch in idx.chars:
        if ord(ch) < 0x80:
            continue
        reasons = []
        if ch in e0:
            reasons.append('E0 结构化文本: LANG/SFXML 正文里确证在用')
        if policy in ('text', 'strict'):
            if ch in e1:
                reasons.append('E1 其它可能装文本的容器里有可读串证据'
                               + (' (已减掉英文原盘命中)' if denoised else ''))
            if ch in e2:
                reasons.append('E2 非文本容器里有可读串证据'
                               + (' (已减掉英文原盘命中)' if denoised else ''))
        if policy == 'strict':
            if char_to_t3(ch, idx, usage['t3_byte'], usage['t3_bigram']):
                reasons.append('E3 原始字节命中 (无信息量口径)')
        if ch in need:
            reasons.append('★ 新译文 (--text-dir) 里要用到 —— 回收它会自相矛盾')
        if not ignore_reserved and ch in idx.enc_single:
            b = idx.enc_single[ch]
            if b in idx.protected:
                reasons.append('单字节码 0x%02X 在 charset JSON 的 protected 里 '
                               '(英文盘在用, 不许回收)' % b)
            if b in idx.mark_codes:
                reasons.append('单字节码 0x%02X 在 charset JSON 的 mark_codes 里 '
                               '(标记码, 不许回收)' % b)
        if reasons:
            blocked[ch] = reasons
        else:
            reclaim.append(ch)
    reclaim.sort()
    singles, pairs, dead = split_by_code(idx, reclaim)
    return dict(reclaim=reclaim, blocked=blocked, legal_pairs=pairs, dead_pairs=dead,
                singles=singles,
                counts=dict(total=len(reclaim), pair=len(pairs), single=len(singles),
                            dead=len(dead),
                            slots=len({pair_slot(idx.enc_pair[c]) for c in pairs})))


def build_plan(idx, rec, needed_chars=None):
    """回收后的「码位/格位释放 + 重排建议」计划 (纯数据, 不落盘)。

    ★ 分类用 split_by_code (单字节优先, 与 encode() 一致), 避免同一个字被算两次。
    """
    freed_pairs, freed_singles, dead_pairs = [], [], []
    for ch in rec['reclaim']:
        cb = idx.code_bytes(ch) or ()
        also = ''
        if ch in idx.enc_single and ch in idx.enc_pair:
            also = ('★ 该字**同时**有对偶码 %02X%02X (死重量, 编码器永不用它); 两个一起摘掉'
                    % tuple(idx.enc_pair[ch]))
        if ch in idx.enc_single:
            freed_singles.append(dict(char=ch, cp='U+%04X' % ord(ch),
                                      code='%02X' % idx.enc_single[ch], note=also))
        elif ch in idx.enc_pair and LEGAL_LEAD_LO <= idx.enc_pair[ch][0] < LEGAL_LEAD_HI:
            slot = pair_slot(idx.enc_pair[ch])
            x, y = slot_cell(slot)
            freed_pairs.append(dict(char=ch, cp='U+%04X' % ord(ch), code='%02X%02X' % cb,
                                    slot=slot, col=slot % GRID_NCOL, row=slot // GRID_NCOL,
                                    x=x, y=y, note=also))
        else:
            slot = pair_slot(idx.enc_pair[ch])
            dead_pairs.append(dict(char=ch, cp='U+%04X' % ord(ch),
                                   code=('%02X%02X' % cb) if len(cb) == 2 else '?',
                                   slot=slot, col=slot % GRID_NCOL, row=slot // GRID_NCOL,
                                   note=('死 pair (lead>=0xAE): 引擎 sltiu 读不了, '
                                         '解码器永不产出它, 不占合法对偶空间' + also)))
    used = {tuple(v) for v in idx.enc_pair.values()}
    holes = []
    for L in range(LEGAL_LEAD_LO, LEGAL_LEAD_HI):
        for t in range(TRAIL_LO, TRAIL_HI + 1):
            if (L, t) not in used:
                slot = pair_slot((L, t))
                x, y = slot_cell(slot)
                holes.append(dict(code='%02X%02X' % (L, t), slot=slot, x=x, y=y))
    avail = [dict(code=d['code'], slot=d['slot'], x=d['x'], y=d['y'], src='回收释放')
             for d in freed_pairs]
    avail += [dict(code=d['code'], slot=d['slot'], x=d['x'], y=d['y'], src='原有空位')
              for d in holes]
    assign = []
    for i, ch in enumerate(sorted(needed_chars or [])):
        if i >= len(avail):
            break
        a = avail[i]
        assign.append(dict(char=ch, cp='U+%04X' % ord(ch), code=a['code'],
                           slot=a['slot'], x=a['x'], y=a['y'], src=a['src']))
    return dict(freed_pairs=freed_pairs, freed_singles=freed_singles,
                dead_pairs=dead_pairs, holes=holes, assign=assign,
                n_freed_pair=len(freed_pairs), n_dead_pair=len(dead_pairs),
                n_holes=len(holes), n_assign=len(assign))


def make_new_charset(idx, rec):
    """构造回收后的 charset dict (纯内存, 不落盘)。含两条硬断言。"""
    new = copy.deepcopy(idx.raw)
    drop = set(rec['reclaim'])
    for ch in list(new['codes']):
        if ch in drop:
            del new['codes'][ch]
    for ch in list(new['pair_of']):
        if ch in drop:
            del new['pair_of'][ch]
    for ch, v in idx.raw['codes'].items():
        if ch not in drop and new['codes'].get(ch) != v:
            raise AssertionError('不变式①破坏: 在用字 %r 的单字节码被改动 (%r → %r)'
                                 % (ch, v, new['codes'].get(ch)))
    for ch, v in idx.raw['pair_of'].items():
        if ch not in drop and new['pair_of'].get(ch) != v:
            raise AssertionError('不变式①破坏: 在用字 %r 的对偶码被改动 (%r → %r)'
                                 % (ch, v, new['pair_of'].get(ch)))
    keep = set(new['codes']) | set(new['pair_of'])
    for ch in drop:
        if ch in keep:
            raise AssertionError('不变式②破坏: 被回收的字 %r 仍在输出里' % ch)
    for k in ('mode', 'trim19', 'markers', 'mark_codes', 'protected', 'grid'):
        if k in idx.raw:
            new[k] = copy.deepcopy(idx.raw[k])
    return new


def write_charset(idx, new, out_charset, out_plan=None, plan=None):
    op = os.path.abspath(out_charset)
    if op == idx.path:
        raise ValueError('--out-charset 与输入 charset 是同一个文件, 拒绝覆盖: %s' % op)
    d = os.path.dirname(op)
    if d:
        os.makedirs(d, exist_ok=True)
    with io.open(op, 'w', encoding='utf-8') as f:
        json.dump(new, f, ensure_ascii=False, indent=1)
    if out_plan:
        d = os.path.dirname(os.path.abspath(out_plan))
        if d:
            os.makedirs(d, exist_ok=True)
        with io.open(out_plan, 'w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=1)
    return op


def idx_from_raw(raw, path, template):
    n = CharsetIndex.__new__(CharsetIndex)
    n.path = path
    n.raw = raw
    n.enc_single = {ch: int(v) for ch, v in raw['codes'].items()}
    n.enc_pair = {ch: tuple(v) for ch, v in raw['pair_of'].items()}
    n.codes = {v: ch for ch, v in n.enc_single.items()}
    n.pair_of = {v: ch for ch, v in n.enc_pair.items()}
    n.chars = sorted(set(n.enc_single) | set(n.enc_pair))
    n.protected = set(template.protected)
    n.mark_codes = set(template.mark_codes)
    n.alphabet = bytes(sorted(
        set(range(0x20, 0x7F)) | set(n.codes) |
        {p[0] for p in n.pair_of} | {p[1] for p in n.pair_of} | set(BTN_BYTES)))
    n._rx = {}
    return n


def verify_reclaim(iso, containers, ref_idx, ref_usage, new_idx, verbose=True,
                   nontext_min_run=DEFAULT_MIN_RUN):
    """回收后自检: 用**回收后的 charset** 重新扫一遍盘, 确认没有任何在用字丢失映射。

    三重检查:
      ① 用**新** charset 重扫 ⇒ 解出来的字里有没有新表没有的? (口径有没有变)
      ② 用**旧** charset 扫出来的「在用」字, 在新表里是否仍有映射, 且**逐字节相同**?
      ③ 回收清单里的字, 是否真的都不在「在用」集合里?
    """
    res = dict(ok=True, problems=[])
    if verbose:
        print('\n===== --verify 回收后自检 =====')
    scan = scan_disc(iso, new_idx, containers, ctrl=None,
                     nontext_min_run=nontext_min_run, verbose=False)
    res['rescanned'] = dict(containers=scan['n_containers'], blob_bytes=scan['blob_bytes'])
    used_new = scan['e0'] | scan['e1'] | scan['e2']
    # ★ 只查**字库里的字**: ASCII (<0x80) 引擎走单字节路径, 与 charset JSON 无关,
    #   本来就不在 chars 里 ⇒ 不能算"丢了映射"。
    missing = sorted(c for c in used_new
                     if ord(c) >= 0x80 and c not in new_idx.chars)
    if missing:
        res['ok'] = False
        res['problems'].append('用新 charset 重扫, 有 %d 个字解不出来却没有映射: %s'
                               % (len(missing), ''.join(missing[:40])))
    if verbose:
        print('  ① 用回收后的 charset 重扫全盘: %d 个容器 / %.0f MB → 证据字 %d 个'
              % (scan['n_containers'], scan['blob_bytes'] / 1048576, len(used_new)))
        print('     %s' % ('[ok] 全部有映射 ✓' if not missing else '[!!] 有解不出来的字'))
    used_ref = ref_usage['e0'] | ref_usage['e1'] | ref_usage['e2']
    lost, bad_map = [], []
    for ch in sorted(used_ref):
        if ord(ch) < 0x80:
            continue
        if not new_idx.encodable(ch):
            lost.append(ch)
        elif new_idx.code_bytes(ch) != ref_idx.code_bytes(ch):
            bad_map.append(ch)
    if lost:
        res['ok'] = False
        res['problems'].append('有 %d 个「在用」的字在回收后的 charset 里丢了映射: %s'
                               % (len(lost), ''.join(lost[:40])))
    if bad_map:
        res['ok'] = False
        res['problems'].append('有 %d 个「在用」的字的码位被改动了: %s'
                               % (len(bad_map), ''.join(bad_map[:40])))
    if verbose:
        print('  ② 回收前「在用」字 %d 个 → 新 charset: 丢映射 %d / 码位被改 %d  %s'
              % (len(used_ref), len(lost), len(bad_map),
                 '[ok] ✓' if not (lost or bad_map) else '[!!]'))
    dropped = set(ref_idx.chars) - set(new_idx.chars)
    still_used = sorted(dropped & used_ref)
    if still_used:
        res['ok'] = False
        res['problems'].append('回收清单里混进了「在用」的字: %s' % ''.join(still_used[:40]))
    if verbose:
        print('  ③ 新表比旧表少 %d 个字; 其中「在用」的 %d 个  %s'
              % (len(dropped), len(still_used), '[ok] ✓' if not still_used else '[!!]'))
        print('  ⇒ 自检结论: %s' % ('[ok] 通过 —— 没有任何在用字丢失映射 ✓'
                                    if res['ok'] else '[!!] 失败'))
    return res


# ═════════════════════════ 报告 ═════════════════════════

def disp(ch):
    o = ord(ch)
    return '\\x%02X' % o if (o < 0x20 or o == 0x7F) else ch


def fmt_chars(chars, per_line=60, limit=None):
    s = ''.join(disp(c) for c in sorted(chars))
    if limit and len(s) > limit:
        return s[:limit] + '…(共 %d 个)' % len(chars)
    return '\n'.join(s[i:i + per_line] for i in range(0, len(s), per_line)) or '(空)'


def human_report(R):
    L = []
    A = L.append
    idx, usage, rec, plan = R['idx'], R['usage'], R['rec'], R['plan']
    cap = idx.pair_capacity()
    need = R.get('need', [])
    need_pair = [c for c in need if ord(c) >= 0x80]
    e0, e1, e2 = usage['e0'], usage['e1'], usage['e2']
    allblock = e0 | e1 | e2
    A('# 字库用量核算 + 码位/格位回收 (dry-run 报告)')
    A('')
    A('- 盘: `%s`' % os.path.relpath(R['iso'], REPO).replace('\\', '/'))
    A('- 盘 sha256: `%s`' % R['iso_sha256'])
    A('- 字符集: `%s`' % os.path.relpath(idx.path, REPO).replace('\\', '/'))
    A('- 字符集 sha256: `%s`' % R['charset_sha256'])
    A('- 假阳性对照盘: %s' % ('`%s`'
                              % os.path.relpath(R['control_iso'], REPO).replace('\\', '/')
                              if R.get('control_iso') else '**未提供** (保守度大幅下降)'))
    A('- 回收口径: `--policy %s`; E1 串长 >= %d; E2 串长 >= %d'
      % (R['policy'], TEXT_RUN_MIN, R['min_run']))
    A('- 本报告**只读**: 没有修改任何 ISO / 字库 / 字符集文件。')
    A('')

    A('## 一句话结论')
    A('')
    A('| 问题 | 答案 |')
    A('|---|---|')
    A('| 字库现在有多少字? | **%d** 个 (单字节 %d + 对偶 %d) |'
      % (len(idx.chars), cap['single_used'], len(idx.enc_pair)))
    A('| 其中**盘上确证在用**的? | **%d** 个 (E0 结构化文本; 另有 %d 个 ASCII 也在用) |'
      % (len(e0 & set(idx.chars)), len([c for c in e0 if ord(c) < 0x80])))
    A('| 加上其它容器的可读串证据后不能动的? | **%d** 个 |'
      % len(allblock & set(idx.chars)))
    A('| ⇒ **可以回收几个字**? | **%d** 个 |' % rec['counts']['total'])
    A('| — 其中能腾出**图集格位**的 (合法对偶) | **%d** 个 |' % rec['counts']['pair'])
    A('| — 只是清理历史垃圾的 (死 pair, 引擎读不了) | %d 个 |' % rec['counts']['dead'])
    A('| — 单字节码 | %d 个 |' % rec['counts']['single'])
    if R.get('text_files') and R.get('need_protected'):
        A('| — ★ 因"新译文要用到"而**不回收** | %d 个 |' % R['need_protected'])
    A('| 原本还剩多少合法对偶空位? | **%d** 个 |' % plan['n_holes'])
    A('| 新文本还需要补几个字? | **%d** 个 (非 ASCII **%d** + ASCII %d) |'
      % (len(need), len(need_pair), len(need) - len(need_pair)))
    A('| **够不够用**? | %s |' % R['capacity_verdict'])
    A('')
    A('> ★ **关键区分**: 「可回收 %d 个字」听起来很多, 但真正能**换出新字格位**的只有 '
      '%d 个 (合法对偶码)。另外 %d 个是**死 pair** —— 它们的 lead 是 0xAE/0xAF/0xB0, '
      '而引擎的判据是 `sltiu lead, 0xAE` (只认 0xA1..0xAD), 解码器**永远不会**产出它们, '
      '编码器也拒绝写出。摘掉它们是**打扫卫生**, 不增加可用格位。'
      % (rec['counts']['total'], rec['counts']['pair'], rec['counts']['dead']))
    A('>')
    A('> 回收**只释放码位与图集格位**, 不移动任何仍在用的字 (见「不变式」一节)。')
    if R.get('text_files'):
        A('>')
        A('> ★ **新译文保护**: `--text-dir` 里用到的字一律不回收 —— 回收是为了给新字腾'
          '格位, 把新字自己要用的字回收掉是自相矛盾的。本次因此拦下 **%d** 个字'
          '(它们盘上没用到、但新译文要用)。' % R.get('need_protected', 0))
    A('')

    A('### 闲置字的码位类型分解 (这决定了回收到底值多少)')
    A('')
    A('| 码位类型 | 闲置 (可回收) | 在用 | 说明 |')
    A('|---|---:|---:|---|')
    A('| 合法对偶 (lead 0xA1..0xAD) | **%d** | %d | ★ 只有这些能换出新字格位 |'
      % (rec['counts']['pair'], cap['used'] - rec['counts']['pair']))
    A('| 死 pair (lead 0xAE..0xB0) | %d | %d | 引擎读不了, 纯历史残留 |'
      % (rec['counts']['dead'], cap['dead'] - rec['counts']['dead']))
    A('| 单字节码 (0xAF..0xFE) | %d | %d | 走 FT 记录表, 不占对偶格位 |'
      % (rec['counts']['single'], cap['single_used'] - rec['counts']['single']))
    A('')
    if plan['freed_pairs']:
        A('### ★ 真正能腾出来的 %d 个图集格位 (这就是回收的全部价值)'
          % plan['n_freed_pair'])
        A('')
        A('| 字 | 码位 | 对偶码 | 格位 slot | col | row | 图集 x | 图集 y |')
        A('|---|---|---|---:|---:|---:|---:|---:|')
        for d in plan['freed_pairs']:
            A('| %s | %s | `%s` | %d | %d | %d | %d | %d |'
              % (disp(d['char']), d['cp'], d['code'], d['slot'], d['col'], d['row'],
                 d['x'], d['y']))
        A('')
    A('')

    A('## 一、工具扫了什么 (覆盖范围自证)')
    A('')
    A('扫过 **%d** 个容器, 原始字节 **%d B (%.1f MB)**, 解压后内容 **%d B (%.1f MB)**。'
      % (usage['n_containers'], usage['stored_bytes'], usage['stored_bytes'] / 1048576,
         usage['blob_bytes'], usage['blob_bytes'] / 1048576))
    A('')
    A('覆盖清单: GR.IMG 全部 4070 个条目 + MENU.IMG 全部 686 个条目 + IMG 以外的 '
      'ISO 文件 (SLUS_206.13 / MODULES/*.IRX / IOPRP242.IMG …)。')
    A('')
    A('| 类别 | 是什么 | 容器数 | 解压后字节 | 证据级别 | 该类别命中的字 | 该类"独有"贡献 |')
    A('|---|---|---:|---:|---|---:|---:|')
    owner = {}
    for k, d in usage['by_kind'].items():
        for ch in d['chars']:
            owner.setdefault(ch, []).append(k)
    for k in sorted(usage['by_kind'], key=lambda x: -usage['by_kind'][x]['blob']):
        d = usage['by_kind'][k]
        uniq = sum(1 for ch, ks in owner.items() if ks == [k])
        lvl = 'E0' if k in ('LANG', 'SFXML') else ('E1' if KIND_RULES[k][0] else 'E2')
        A('| `%s` | %s | %d | %d | %s | %d | %d |'
          % (k, KIND_DESC.get(k, ''), d['n'], d['blob'], lvl, len(d['chars']), uniq))
    A('')
    A('### 逐类"贡献"明细 (各贡献了多少个用到的字)')
    A('')
    for k in sorted(usage['by_kind'], key=lambda x: -len(usage['by_kind'][x]['chars'])):
        d = usage['by_kind'][k]
        lvl = 'E0' if k in ('LANG', 'SFXML') else ('E1' if KIND_RULES[k][0] else 'E2')
        A('- **%s** (%s, %s): %d 个容器 / %.1f MB → 命中 **%d** 个字'
          ' (其中结构化 E0 %d / 可读串 %d / 非文本可读串 %d)'
          % (k, KIND_DESC.get(k, ''), lvl, d['n'], d['blob'] / 1048576, len(d['chars']),
             len(d['e0']), len(d['e1']), len(d['e2'])))
    A('')
    A('> 「该类独有贡献」= 该字**只有这一类**容器提供证据。数字越大, 说明这一类**必须**扫'
      '(漏了就会误回收); 数字为 0 说明它的证据被别的类别完全覆盖。')
    A('')

    A('## 二、字库用量: 四级证据')
    A('')
    A('| 级别 | 含义 | 命中的字 | 说明 |')
    A('|---|---|---:|---|')
    A('| **E0 结构化文本** | LANG 语言表 + SFXML 逐条正文**解码** | **%d** | 引擎真正会画的字; 无阈值 |'
      % len(e0))
    A('| **E1 其它文本容器可读串** | XML/TXT/MIS/ATR/RES/ELF 里 >=%d 的可读串 | **%d** | %s |'
      % (TEXT_RUN_MIN, len(e1),
         ('已减掉英文原盘命中' if R.get('control_iso') else '未减对照 ⇒ 含噪声')))
    A('| **E2 非文本容器可读串** | 贴图/打包/视频音频里 >=%d 的可读串 | **%d** | %s |'
      % (R['min_run'], len(e2),
         ('已减掉英文原盘命中' if R.get('control_iso') else '未减对照 ⇒ 含噪声')))
    if usage.get('t3_bigram') is not None:
        A('| **E3 原始字节** | 编码在任意上下文的原始字节里出现过 | %d / %d | **无信息量**, 见下 |'
          % (int(usage['t3_bigram'].sum()), len(usage['t3_bigram'])))
    A('')
    if usage.get('t3_bigram') is not None:
        A('### ★ 为什么"全盘字节搜索"这个判据必须废掉')
        A('')
        A('实测: 全盘 **65536 种 2 字节组合里出现了 %d 种**。'
          % int(usage['t3_bigram'].sum()))
        A('⇒ 拿"某字的 2 字节编码在盘上找不找得到"当判据, **每个字都找得到**,')
        A('   信息量为 **0**。这就是本工具改用「结构化文本 + 对照减法」的原因。')
        A('')
    A('### 没被用到 (可回收) 的字: 判定依据')
    A('')
    A('判定依据 = **在全部 %d 个容器里, 该字的编码都没有构成"证据"**:'
      % usage['n_containers'])
    A('')
    A('1. 不在 LANG / SFXML 的**逐条正文**里 (E0 精确判定, 与 CSV 表口径一致);')
    A('2. 不在任何其它容器的**可读串**里 —— 或虽在, 但**英文原盘同一个容器里也有**')
    A('   (⇒ 可证明是巧合, 已减掉)。')
    A('')

    A('## 三、可回收清单 (dry-run —— 本报告没有真的回收)')
    A('')
    A('合计 **%d** 个字: **合法对偶 %d 个 (真正释放图集格位)** + 死 pair %d 个 (清理) '
      '+ 单字节 %d 个。'
      % (rec['counts']['total'], rec['counts']['pair'],
         rec['counts']['dead'], rec['counts']['single']))
    A('')
    A('### 全部可回收的字')
    A('')
    A('```')
    A(fmt_chars(rec['reclaim']))
    A('```')
    A('')
    if plan['dead_pairs']:
        A('### 其中 %d 个是"死 pair"(清理项, 不换格位)' % plan['n_dead_pair'])
        A('')
        A('```')
        A(fmt_chars([d['char'] for d in plan['dead_pairs']]))
        A('```')
        A('')
        A('> 它们的 lead 是 0xAE/0xAF/0xB0, 引擎 `sltiu lead,0xAE` 判为**两个单字节**, '
          '解码器 `decode()` 也永远不会产出它们 ⇒ 摘掉它们对游戏**没有任何影响**, '
          '但**也不增加可用格位**。')
        A('')
    if rec['blocked']:
        A('### 被拦下、**不**回收的字 (%d 个) 及原因' % len(rec['blocked']))
        A('')
        buckets = {}
        for ch, rs in rec['blocked'].items():
            buckets.setdefault('; '.join(rs), []).append(ch)
        for why in sorted(buckets, key=lambda x: -len(buckets[x])):
            A('- **%d 个字** — %s' % (len(buckets[why]), why))
            A('  ```')
            A('  ' + fmt_chars(buckets[why], 58).replace('\n', '\n  '))
            A('  ```')
        A('')

    A('## 四、新文本缺字清单 (来自 `--text-dir`)')
    A('')
    if not R.get('text_files'):
        A('> 本次没有给 `--text-dir`, 所以只做了「字库 vs 全盘用量」。')
        A('')
    else:
        A('读了 %d 张表 / %d 条文本: %s'
          % (len(R['text_files']), R['text_rows'],
             ', '.join('`%s`(%d)' % (os.path.basename(f['path']), f['rows'])
                       for f in R['text_files'])))
        A('')
        A('| 项 | 数量 |')
        A('|---|---:|')
        A('| 新文本用到的不同字符 | %d |' % len(R['new_chars']))
        A('| 其中**字库没有**的 (要补) | **%d** |' % len(need))
        A('| — 非 ASCII (真正要补字) | **%d** |' % len(need_pair))
        A('| — ASCII (引擎走单字节路径, 不阻断) | %d |' % (len(need) - len(need_pair)))
        A('| 字库里有、新文本用不到的 | %d |' % len(R['idle']))
        A('| — 本次改译**新释放**的 | %d |' % len(R['idle_from_edits']))
        A('| — 早就闲置的 | %d |' % len(R['idle_long_ago']))
        A('')
        A('### 真正要补的字 (非 ASCII, %d 个)' % len(need_pair))
        A('')
        A('```')
        A(fmt_chars(need_pair))
        A('```')
        A('')
        if need_pair:
            A('| 字 | 码位 | 出现在哪些条目 (前 3) |')
            A('|---|---|---|')
            for ch in sorted(need_pair)[:90]:
                A('| %s | U+%04X | %s |' % (disp(ch), ord(ch),
                                            ', '.join(R['need_ids'].get(ch, [])[:3]) or '—'))
            A('')
        if len(need) - len(need_pair):
            A('### ASCII 缺字 (%d 个, 只提示不阻断)' % (len(need) - len(need_pair)))
            A('')
            A('```')
            A(fmt_chars([c for c in need if ord(c) < 0x80]))
            A('```')
            A('')
        A('### 闲置字 (%d 个): 新文本用不到' % len(R['idle']))
        A('')
        A('```')
        A(fmt_chars(R['idle'], 60, 1500))
        A('```')
        A('')
        A('### ★ 交叉验证: 闲置字里, 有多少**真的**可以回收?')
        A('')
        rc = set(rec['reclaim'])
        n_rc = len([c for c in R['idle'] if c in rc])
        n_b0 = len([c for c in R['idle'] if c in e0])
        n_b12 = len([c for c in R['idle'] if c not in e0 and (c in e1 or c in e2)])
        n_bp = len([c for c in R['idle'] if c not in rc and c not in e0
                    and c not in e1 and c not in e2])
        n_legal = len([c for c in R['idle'] if c in rc and c in set(rec['legal_pairs'])])
        n_dead = len([c for c in R['idle'] if c in rc and c in set(rec['dead_pairs'])])
        A('| 结果 | 数量 | 说明 |')
        A('|---|---:|---|')
        A('| 闲置字 (新文本口径) | %d | 新译文里一个字都没用到 |' % len(R['idle']))
        A('| ⇒ 被 E0 拦下 (盘上 LANG/SFXML 正文里还在用) | **%d** | '
          '"新文本没用" ≠ "盘上没用" |' % n_b0)
        A('| ⇒ 被 E1/E2 拦下 (别处容器有可读串证据) | **%d** | 疑似还在别处用 |' % n_b12)
        A('| ⇒ 被 protected/mark_codes 拦下 | **%d** | 字符集自带保护 (单字节码) |' % n_bp)
        A('| ⇒ **确认可回收** | **%d** | 全盘 %d 个容器都没有它的证据 |'
          % (n_rc, usage['n_containers']))
        A('| — 其中**合法对偶** (真能换格位) | **%d** | ★ 这才是回收的实际价值 |' % n_legal)
        A('| — 其中**死 pair** (只是清理) | %d | 引擎读不了, 不占合法格位 |' % n_dead)
        A('')
        if R.get('xcheck'):
            X = R['xcheck']
            A('### ★★ 与 CSV 文本表的口径交叉验证 (E0 是否可信)')
            A('')
            A('| 口径 | 字库内用到的字 |')
            A('|---|---:|')
            A('| 本工具 E0 (直接解析盘上 LANG/SFXML 正文) | **%d** |' % X['e0'])
            A('| CSV `text_zh` 列 (dump 出来的现值) | **%d** |' % X['csv_zh'])
            A('| 只在 E0 里、CSV 没有 | **%d** |' % len(X['only_e0']))
            A('| 只在 CSV 里、E0 没有 | **%d** |' % len(X['only_csv']))
            A('')
            if not X['only_e0'] and not X['only_csv']:
                A('**两套口径逐字完全一致** (差集为空) ⇒ E0 解析可信, 与既有工具链同口径 ✓')
            else:
                A('两套口径有差异, 明细见 JSON 报告的 `text.xcheck`。')
            A('')
        A('**这就是本工具相对"只做加法"预检的价值**: 新文本没用到的 %d 个字里, '
          '只有 %d 个是**全盘**都没用到 (其中真正能换格位的只有 %d 个); '
          '其余 %d 个盘上别处还在用 —— 回收了就会花屏。'
          % (len(R['idle']), n_rc, n_legal, len(R['idle']) - n_rc))
        A('')

    A('## 五、容量结论: 够不够补新字')
    A('')
    A('| 项 | 数量 |')
    A('|---|---:|')
    A('| 合法对偶空间 (lead 0xA1..0xAD × trail 0xA1..0xFE) | %d |' % cap['total'])
    A('| 已经用掉 | %d |' % cap['used'])
    A('| **原本剩余空位** | **%d** |' % cap['free'])
    A('| 回收释放的**合法**格位 | %d |' % plan['n_freed_pair'])
    A('| **回收后可用** | **%d** |' % (cap['free'] + plan['n_freed_pair']))
    A('| 新文本要补的非 ASCII 字 | %d |' % len(need_pair))
    A('| **余量** | **%d** |' % (cap['free'] + plan['n_freed_pair'] - len(need_pair)))
    A('| 另有死 pair (lead>=0xAE, 引擎读不了) | %d 个 —— 本来就不能用 |' % cap['dead'])
    A('')
    A('**结论: %s**' % R['capacity_verdict'])
    A('')
    A('> 单字节码 %d 个 (0xAF..0xFE) 走 FT 记录表, **不占对偶格位**; '
      '回收单字节字只腾出 FT 记录, 对"补新汉字"没有直接帮助。' % cap['single_used'])
    A('>')
    A('> ⚠ **不要**把"可回收 %d 个字"当成"多出 %d 个格位": 其中 %d 个是死 pair, '
      '它们的码位不在合法对偶空间里 (slot >= %d), 引擎也不认。真正的增量是 **%d** 个。'
      % (rec['counts']['total'], rec['counts']['total'], rec['counts']['dead'],
         (LEGAL_LEAD_HI - LEGAL_LEAD_LO) * 94, plan['n_freed_pair']))
    A('')

    if R.get('control'):
        C = R['control']
        A('## 六、假阳性对照 (英文原盘) —— 把噪声变成可测量的东西')
        A('')
        A('- 对照盘: `%s`' % os.path.relpath(R['control_iso'], REPO).replace('\\', '/'))
        A('- 容器逐字节比对: **相同 %d 个 / 不同 %d 个** (共 %d 个)'
          % (C['same'], C['diff'], C['same'] + C['diff']))
        A('- 不同的容器 (%d 个): %s' % (C['diff'],
                                        ', '.join(C['diff_names'][:14]) +
                                        (' …' if len(C['diff_names']) > 14 else '')))
        A('')
        A('**推理**: 英文盘里**没有中文** ⇒ 英文盘命中的"中文字"**必然是巧合**。')
        A('容器逐字节相同 ⇒ 两盘命中集合**逐元素相同** ⇒ 减完是空集 (可证明)。')
        A('')
        A('| 口径 | 中文盘命中 | 英文盘命中(全是假阳性) | 相减后剩下的**新证据** |')
        A('|---|---:|---:|---:|')
        A('| E1 文本容器可读串 | %d | %d | **%d** |'
          % (len(usage['ctrl_e1']), len(usage['ctrl_e1']), len(e1)))
        A('| E2 非文本容器可读串 | %d | %d | **%d** |'
          % (len(usage['ctrl_e2']), len(usage['ctrl_e2']), len(e2)))
        A('| E0 结构化文本 | %d | %d | **%d** (LANG/SFXML 精确解析, 不需要减) |'
          % (len(e0), len(usage['ctrl_e0']), len(e0)))
        A('')
        A('> 注意 E2 一列: 英文盘在贴图/视频里命中 **%d** 个字 (占字库 %.0f%%), '
          '与中文盘几乎一样多 ⇒ 这一级别的**原始**命中基本全是噪声, 正是靠对照减法才'
          '能用。' % (len(usage['ctrl_e2']),
                      100.0 * len(usage['ctrl_e2']) / len(idx.chars)))
        A('')

    A('## 七、还没被覆盖 / 覆盖得不够的地方 (诚实清单)')
    A('')
    for line in R['limits']:
        A('- %s' % line)
    A('')

    A('## 八、不变式 (回收时**绝不**动到在用的字)')
    A('')
    A('`--apply` 在写盘前跑两条硬断言, 不满足就抛异常、一个字都不写:')
    A('')
    A('1. 输出 charset 里**每一个仍保留的字**, 其映射与输入**逐字节相同**;')
    A('2. 被摘掉的每一个字, 都**不在**「在用」集合里。')
    A('')
    A('格位公式 (与 `tcslib.atlas_cell_xy` 逐位一致, 已自检):')
    A('')
    A('```')
    A('slot = (b1-0xA1)*94 + (b2-0xA1)')
    A('col  = slot % 62 ;  row = slot // 62')
    A('x    = 4 + 16*col ;  y = 2 + 16*(row + 3*[row>=12])')
    A('```')
    A('')
    return '\n'.join(L)


# ═════════════════════════ 主流程 ═════════════════════════

def main():
    ap = argparse.ArgumentParser(
        description='字库用量核算 + 码位/格位回收 (默认只读 / dry-run)')
    ap.add_argument('--iso', default=DEFAULT_ISO, help='要扫的盘 (只读)')
    ap.add_argument('--charset', default=DEFAULT_CHARSET, help='字符集 JSON')
    ap.add_argument('--ref-charset', default=None,
                    help='--verify 用的参考 charset (默认 = 现役 charset)')
    ap.add_argument('--text-dir', default=None, help='文本表目录/文件 (可省略)')
    ap.add_argument('--control-iso', default=DEFAULT_CONTROL,
                    help='英文原盘 (假阳性对照; 默认 %s)' % os.path.relpath(DEFAULT_CONTROL, REPO))
    ap.add_argument('--no-control', dest='control_iso', action='store_const', const=None,
                    help='不做对照 (保守度会大幅下降, 不推荐)')
    ap.add_argument('--min-run', type=int, default=DEFAULT_MIN_RUN,
                    help='E2 非文本容器的可读串最小长度 (默认 %d)' % DEFAULT_MIN_RUN)
    ap.add_argument('--policy', choices=('text', 'strong', 'strict'), default='text',
                    help='回收口径: text(默认) / strong / strict')
    ap.add_argument('--ignore-reserved', action='store_true',
                    help='忽略 charset JSON 的 protected / mark_codes 保护 '
                         '(它们只管单字节码; 默认尊重, 不回收被保护的单字节字)')
    ap.add_argument('--json', default=None, help='JSON 报告输出路径')
    ap.add_argument('--md', default=None, help='Markdown 报告输出路径')
    ap.add_argument('--apply', action='store_true', help='生成回收后的新 charset (默认 dry-run)')
    ap.add_argument('--dry-run', action='store_true', default=True, help='只算不写 (默认)')
    ap.add_argument('--no-dry-run', dest='dry_run', action='store_false')
    ap.add_argument('--yes-really', action='store_true', help='--apply 的二次确认')
    ap.add_argument('--out-charset', default=None, help='回收后的新 charset JSON (不覆盖原文件)')
    ap.add_argument('--out-plan', default=None, help='重排计划 JSON')
    ap.add_argument('--verify', action='store_true', help='回收后自检 (重扫全盘)')
    ap.add_argument('--no-iso-files', dest='iso_files', action='store_false', default=True,
                    help='不扫 IMG 以外的 ISO 文件')
    ap.add_argument('--debug-limit-containers', type=int, default=None,
                    help='★ 调试用: 只扫前 N 个容器 (LANG/SFXML 始终保留; '
                         '会降低保守度, 不要用于正式结论)')
    ap.add_argument('--selfcheck', action='store_true', help='只跑工具自检')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()

    if a.selfcheck:
        return 0 if selfcheck() else 1
    if a.min_run < TEXT_RUN_MIN:
        print('[!!] --min-run 不能小于 %d' % TEXT_RUN_MIN)
        return 2

    idx = CharsetIndex(a.charset)
    iso_path = os.path.abspath(a.iso)
    print('== font_usage.py ==')
    print('# 盘: %s' % os.path.relpath(iso_path, REPO))
    iso = T.Iso(iso_path)
    iso_sha = T.sha256_file(iso_path)
    cs_sha = T.sha256_file(idx.path)
    print('# 盘 sha256: %s' % iso_sha)
    print('# 字符集: %s (sha256 %s, %d 字)'
          % (os.path.relpath(idx.path, REPO), cs_sha[:16], len(idx.chars)))

    containers = build_container_list(iso, extra_iso_files=a.iso_files)
    containers = apply_debug_limit(containers, a.debug_limit_containers)
    print('# 容器: %d 个 (GR.IMG + MENU.IMG%s)%s'
          % (len(containers), ' + ISO 文件' if a.iso_files else '',
             '  ★ 已被 --debug-limit-containers 截断' if a.debug_limit_containers else ''))
    if a.debug_limit_containers:
        print('# [!!] --debug-limit-containers=%d: 只扫了 %d 个容器 (LANG/SFXML 已保留), '
              '**结论不可用于正式判断** —— 没扫到的容器里的字会被误判为可回收。'
              % (a.debug_limit_containers, len(containers)))

    ctrl = None
    ctrl_iso = None
    cinfo = None
    if a.control_iso and os.path.isfile(a.control_iso):
        ctrl_iso = os.path.abspath(a.control_iso)
        ciso = T.Iso(ctrl_iso)
        ccs = build_container_list(ciso, extra_iso_files=a.iso_files)
        ctrl = dict(iso=ciso, map={container_key(c): c for c in ccs})
        print('# 对照盘: %s (%d 个容器)'
              % (os.path.relpath(ctrl_iso, REPO), len(ccs)))
    elif a.control_iso:
        print('# [!!] 对照盘不存在: %s ⇒ 本次不做对照 (保守度下降)'
              % a.control_iso)

    print('# 开始扫描…')
    usage = scan_disc(iso, idx, containers, ctrl=ctrl, nontext_min_run=a.min_run,
                      verbose=not a.quiet)

    if ctrl is not None:
        same = sum(1 for ev in usage['per'] if ev['identical'])
        diff_names = sorted({ev['name'] for ev in usage['per'] if not ev['identical']})
        cinfo = dict(same=same, diff=len(usage['per']) - same, diff_names=diff_names)
        print('# 对照: 容器逐字节相同 %d / 不同 %d; E1 相减前 %d → 后 %d; '
              'E2 相减前 %d → 后 %d'
              % (same, len(usage['per']) - same, len(usage['ctrl_e1']), len(usage['e1']),
                 len(usage['ctrl_e2']), len(usage['e2'])))

    R = dict(need=[], idle=[], new_chars=set(), idle_from_edits=[], idle_long_ago=[],
             need_ids={}, text_files=[], text_rows=0)
    if a.text_dir:
        rows, files, notes = read_text_tables(a.text_dir)
        for n in notes:
            print('# [表] %s: %s' % (n['code'], n['msg']))
        old_chars, new_chars, ids = set(), set(), {}
        for r in rows:
            old_chars |= r['cur']
            new_chars |= r['new']
            for ch in r['new'] - set(idx.chars):
                ids.setdefault(ch, [])
                if len(ids[ch]) < 5 and r['id'] not in ids[ch]:
                    ids[ch].append(r['id'])
        font_chars = set(idx.chars)
        need = sorted(new_chars - font_chars)
        idle = sorted(font_chars - new_chars)
        R.update(need=need, idle=idle, new_chars=new_chars, need_ids=ids,
                 text_files=files, text_rows=len(rows),
                 idle_from_edits=[c for c in idle if c in old_chars],
                 idle_long_ago=[c for c in idle if c not in old_chars])
        print('# 文本表: %d 张 / %d 条; 缺字 %d (非 ASCII %d); 闲置 %d'
              % (len(files), len(rows), len(need),
                 len([c for c in need if ord(c) >= 0x80]), len(idle)))
        # ★ 交叉验证: E0 结构化解析出来的字集合 与 CSV 的 text_zh 集合 对比
        e0_font = {c for c in usage['e0'] if ord(c) >= 0x80}
        zh_font = {c for c in old_chars if ord(c) >= 0x80}
        R['xcheck'] = dict(
            e0=len(e0_font), csv_zh=len(zh_font),
            only_e0=sorted(e0_font - zh_font), only_csv=sorted(zh_font - e0_font))
        print('# [交叉验证] E0 结构化解析 %d 个非 ASCII 字 vs CSV text_zh %d 个: '
              '只在 E0 %d / 只在 CSV %d'
              % (len(e0_font), len(zh_font), len(R['xcheck']['only_e0']),
                 len(R['xcheck']['only_csv'])))

    # ★ 必须**先读文本表**再算回收: 新译文要用到的字一律不回收 (否则自相矛盾)
    rec = compute_reclaim(idx, usage, policy=a.policy, denoised=ctrl is not None,
                          ignore_reserved=a.ignore_reserved,
                          needed_chars=R['new_chars'])
    # 只统计"**仅因为**新译文要用而拦下"的字 (盘上本来就没用到的那几个) ——
    # 新译文用到的字绝大多数本来就因 E0 在用而拦下, 混在一起会误导。
    ev_all = usage['e0'] | usage['e1'] | usage['e2']
    n_need_blocked = len([c for c in R['new_chars']
                          if c in rec['blocked'] and c not in ev_all])
    R['need_only_blocked'] = sorted(c for c in R['new_chars']
                                    if c in rec['blocked'] and c not in ev_all)
    if n_need_blocked:
        print('# [回收保护] ★ 有 %d 个字"盘上没用到、但新译文要用" ⇒ 一律不回收 '
              '(否则新译文自己缺字): %s'
              % (n_need_blocked, ''.join(R['need_only_blocked'][:40])))

    plan = build_plan(idx, rec, [c for c in need if ord(c) >= 0x80])
    cap = idx.pair_capacity()
    avail = cap['free'] + plan['n_freed_pair']
    n_need = len([c for c in need if ord(c) >= 0x80])
    verdict = (('够用 —— 回收后可用 %d 个格位, 要补 %d 个, 余 %d 个'
                % (avail, n_need, avail - n_need)) if avail >= n_need else
               ('**不够** —— 回收后可用 %d 个格位, 但还要补 %d 个, 缺 %d 个'
                % (avail, n_need, n_need - avail)))

    limits = []
    limits.append('**视频/音频流** (`MEDIA`: .PSS/.SS/.TM/…) 只做了**字节级**扫描 —— '
                  '引擎不会从它们里面画字, 但本工具仍按最保守口径扫了它们的字节。')
    limits.append('**运行时写入的数据** (记忆卡存档、运行时拼出来的字符串) 无法离线扫描; '
                  '若某字只在存档里用, 本工具会误判为可回收。')
    if not ctrl:
        limits.append('⚠ **本次没有对照盘** ⇒ E1/E2 的噪声**没有被减掉**, 可回收量被严重'
                      '低估 (甚至可能为 0)。强烈建议加 `--control-iso <英文原盘>`。')
    else:
        limits.append('**与英文盘不同的 %d 个容器** (`%s`) 无法用"逐字节相同"证明, '
                      '但它们的命中已用**同容器集合减法**处理 (只有英文盘没有的命中才算证据)。'
                      % (cinfo['diff'], ', '.join(cinfo['diff_names'][:6])))
    limits.append('E1/E2 判据是「编码落在长度 >= 阈值的可读串内部」。若某个容器里藏着'
                  '**很短**的中文串 (E1 < %d 字节 / E2 < %d 字节), 会被漏判。'
                  '可用 `--min-run` 调小重跑对比。' % (TEXT_RUN_MIN, a.min_run))
    limits.append('`.ATR` 实测 **1193 个文件 / 712 KB 解压后一个非 ASCII 字符都没有** '
                  '(人名全是英文); `.MIS` / `.XML` / `.TXT` 也实测无中文证据。'
                  '本工具仍把它们当文本容器逐字节扫, 是为了将来人名/简报回填中文时不会漏。')
    limits.append('SFXML 只解析 `<text>…</text>` 正文 (与 dump/inject 同一口径); '
                  'XML 里的**标签属性**若含中文, 不在 E0 里。')
    limits.append('本工具**不改**字库图集 PNG / FT 记录表 —— 回收后要真正生效, '
                  '还得由字库管线重铺图集 (本轮不在范围内)。')
    limits.append('字符集 JSON 里的 `grid` 块写的是 **ncol=37 / cw=ch=13 / skip_row=14** '
                  '(13px 时代的几何), 与 16px 图集实际用的 **62×16 / skip_row=12** '
                  '**不一致**; 本工具一律按 62×16 公式算格位 (与 tcslib/ELF cave 一致), '
                  '`grid` 块原样保留不动 —— 建议后续单独修正这个陈旧字段。')

    R.update(idx=idx, usage=usage, rec=rec, plan=plan, iso=iso_path,
             iso_sha256=iso_sha, charset_sha256=cs_sha, policy=a.policy,
             min_run=a.min_run, control=cinfo, control_iso=ctrl_iso, limits=limits,
             capacity_verdict=verdict, need_protected=n_need_blocked)

    print('')
    print('================ 结论 ================')
    print('字库 %d 字; E0 结构化确证在用 %d 字 (字库内); E0∪E1∪E2 不能动 %d 字'
          % (len(idx.chars), len(usage['e0'] & set(idx.chars)),
             len((usage['e0'] | usage['e1'] | usage['e2']) & set(idx.chars))))
    print('⇒ 可回收 %d 字: 合法对偶 %d 个 (**真正腾出图集格位**) + 死 pair %d 个 (清理) '
          '+ 单字节 %d 个'
          % (rec['counts']['total'], rec['counts']['pair'], rec['counts']['dead'],
             rec['counts']['single']))
    print('原本空位 %d + 回收 %d = 可用 %d; 要补非 ASCII %d 个'
          % (cap['free'], plan['n_freed_pair'], avail, n_need))
    print('容量: %s' % verdict)
    if a.text_dir:
        rc = set(rec['reclaim'])
        print('交叉验证: 闲置字 %d 个 → 确认可回收 %d 个 (合法对偶 %d / 死pair %d); '
              '被 E0 拦下 %d 个'
              % (len(R['idle']), len([c for c in R['idle'] if c in rc]),
                 len([c for c in R['idle'] if c in set(rec['legal_pairs'])]),
                 len([c for c in R['idle'] if c in set(rec['dead_pairs'])]),
                 len([c for c in R['idle'] if c in usage['e0']])))
        if R.get('xcheck'):
            X = R['xcheck']
            print('E0 vs CSV text_zh: 字库内用到 %d vs %d; 差集 E0-only %d / CSV-only %d'
                  % (X['e0'], X['csv_zh'], len(X['only_e0']), len(X['only_csv'])))
    if cinfo:
        print('对照(英文盘): 容器相同 %d/不同 %d; E1 相减 %d→%d; E2 相减 %d→%d'
              % (cinfo['same'], cinfo['diff'], len(usage['ctrl_e1']), len(usage['e1']),
                 len(usage['ctrl_e2']), len(usage['e2'])))

    if a.md:
        d = os.path.dirname(os.path.abspath(a.md))
        if d:
            os.makedirs(d, exist_ok=True)
        io.open(a.md, 'w', encoding='utf-8').write(human_report(R))
        print('-> %s' % os.path.relpath(os.path.abspath(a.md), REPO))
    if a.json:
        d = os.path.dirname(os.path.abspath(a.json))
        if d:
            os.makedirs(d, exist_ok=True)
        J = dict(
            tool='font_usage.py', iso=R['iso'], iso_sha256=iso_sha,
            charset=idx.path, charset_sha256=cs_sha, policy=a.policy,
            min_run=a.min_run, text_run_min=TEXT_RUN_MIN,
            debug_limit_containers=a.debug_limit_containers,
            coverage=dict(containers=usage['n_containers'],
                          stored_bytes=usage['stored_bytes'],
                          blob_bytes=usage['blob_bytes'],
                          by_kind={k: dict(n=v['n'], blob=v['blob'],
                                           chars=len(v['chars']), e0=len(v['e0']),
                                           e1=len(v['e1']), e2=len(v['e2']),
                                           raw_chars=len(v['raw_chars']))
                                   for k, v in usage['by_kind'].items()}),
            evidence=dict(
                e0=sorted(usage['e0']), e1=sorted(usage['e1']), e2=sorted(usage['e2']),
                ctrl_e1=sorted(usage['ctrl_e1']), ctrl_e2=sorted(usage['ctrl_e2']),
                ctrl_e0=sorted(usage['ctrl_e0']),
                t3_bigrams_present=(int(usage['t3_bigram'].sum())
                                    if usage.get('t3_bigram') is not None else None)),
            reclaim=dict(chars=rec['reclaim'], counts=rec['counts'],
                         legal_pairs=rec['legal_pairs'], dead_pairs=rec['dead_pairs'],
                         freed_pair_codes=plan['freed_pairs'],
                         freed_single_codes=plan['freed_singles'],
                         cleanup_dead_pairs=plan['dead_pairs'],
                         protected_by_new_text=[c for c in R['new_chars']
                                                if c in rec['blocked']],
                         blocked={ch: rs for ch, rs in rec['blocked'].items()}),
            capacity=dict(pair_total=cap['total'], pair_used=cap['used'],
                          pair_free=cap['free'], pair_dead=cap['dead'],
                          reclaimed_slots=plan['n_freed_pair'], available=avail,
                          needed=n_need, verdict=verdict),
            text=None if not a.text_dir else dict(
                files=[os.path.relpath(f['path'], REPO).replace('\\', '/')
                       for f in R['text_files']], rows=R['text_rows'],
                need=need, need_non_ascii=[c for c in need if ord(c) >= 0x80],
                need_ascii=[c for c in need if ord(c) < 0x80], need_ids=R['need_ids'],
                idle=R['idle'], idle_from_edits=R['idle_from_edits'],
                idle_long_ago=R['idle_long_ago'],
                idle_reclaimable=[c for c in R['idle'] if c in set(rec['reclaim'])],
                idle_blocked_e0=[c for c in R['idle'] if c in usage['e0']],
                idle_blocked_e1=[c for c in R['idle'] if c not in usage['e0']
                                 and c in usage['e1']],
                idle_blocked_e2=[c for c in R['idle'] if c not in usage['e0']
                                 and c not in usage['e1'] and c in usage['e2']],
                xcheck=R.get('xcheck')),
            control=None if not cinfo else dict(
                iso=ctrl_iso, same=cinfo['same'], diff=cinfo['diff'],
                diff_names=cinfo['diff_names']),
            plan=dict(holes=plan['n_holes'], assign=plan['assign']),
            limits=limits,
        )
        json.dump(J, io.open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('-> %s' % os.path.relpath(os.path.abspath(a.json), REPO))

    rc = 0
    new_raw = None
    if a.apply:
        out_cs = a.out_charset or (os.path.splitext(idx.path)[0] + '.reclaimed.json')
        dry = a.dry_run or not a.yes_really
        print('')
        print('================ --apply %s ================'
              % ('(dry-run: 不写任何文件)' if dry else '(真的写盘)'))
        print('将摘掉 %d 个字: 对偶 %d / 单字节 %d / 死 pair %d'
              % (rec['counts']['total'], rec['counts']['pair'],
                 rec['counts']['single'], rec['counts']['dead']))
        print('释放对偶码位 (前 24): %s'
              % ', '.join('%s=%s' % (d['char'], d['code'])
                          for d in plan['freed_pairs'][:24] if d.get('slot') is not None))
        print('释放图集格位: %d 个; 原有空位 %d 个; 可分配 %d 个'
              % (plan['n_freed_pair'], plan['n_holes'],
                 plan['n_freed_pair'] + plan['n_holes']))
        if plan['assign']:
            print('重排建议 (新字 → 码位/格位; 不移动任何在用字):')
            for d in plan['assign'][:40]:
                print('   %s %s → 码位 %s  格位 slot=%d 图集(%d,%d)  [%s]'
                      % (d['char'], d['cp'], d['code'], d['slot'], d['x'], d['y'], d['src']))
        else:
            print('重排建议: (没有给出 --text-dir 或没有缺字 ⇒ 不分配)')
        print('目标 charset: %s' % os.path.relpath(os.path.abspath(out_cs), REPO))
        new_raw = make_new_charset(idx, rec)
        if dry:
            print('[dry-run] %s ⇒ **一个文件都不写**。'
                  % ('未指定 --yes-really' if not a.yes_really else '--dry-run 生效'))
        else:
            op = write_charset(idx, new_raw, out_cs, out_plan=a.out_plan, plan=plan)
            print('[written] %s (摘掉 %d, 保留 %d)'
                  % (op, rec['counts']['total'], len(new_raw['codes'])
                     + len(new_raw['pair_of'])))
            if a.out_plan:
                print('[written] %s' % os.path.abspath(a.out_plan))

    if a.verify:
        if new_raw is None:
            # 单独 --verify: --charset 就是要检查的"回收后"表, 参考表取 --ref-charset
            ref_path = os.path.abspath(a.ref_charset or DEFAULT_CHARSET)
            if ref_path == idx.path:
                print('\n[!!] --verify 需要一张**回收后**的 charset: 用 --charset <新表> '
                      '(参考表用 --ref-charset, 默认现役表) 或配合 --apply。')
                rc = 2
                new_raw = None
            else:
                ref_idx = CharsetIndex(ref_path)
                print('\n# --verify: 参考表 %s / 待检表 %s'
                      % (os.path.relpath(ref_path, REPO), os.path.relpath(idx.path, REPO)))
                ref_usage = scan_disc(iso, ref_idx, containers, ctrl=ctrl,
                                      nontext_min_run=a.min_run, verbose=False)
                v = verify_reclaim(iso, containers, ref_idx, ref_usage, idx,
                                   nontext_min_run=a.min_run)
                if not v['ok']:
                    rc = 1
        else:
            nidx = idx_from_raw(new_raw, idx.path, idx)
            v = verify_reclaim(iso, containers, idx, usage, nidx,
                               nontext_min_run=a.min_run)
            if not v['ok']:
                rc = 1

    if ctrl is not None:
        ctrl['iso'].close()
    iso.close()
    print('')
    print('# 本次运行%s。' % ('**没有修改任何 ISO / 字符集 / 字库文件** (只读核算)'
                             if not (a.apply and not a.dry_run and a.yes_really)
                             else '写出的文件见上面 [written] 行'))
    return rc


def selfcheck():
    """工具自检: 格位公式 / 解码口径 / 判据的可复现性。"""
    ok = True
    idx = CharsetIndex()

    def chk(cond, msg):
        nonlocal ok
        ok = ok and bool(cond)
        print('%s %s' % ('[ok]' if cond else '[!!]', msg))

    bad = [s for s in range(0, 62 * 44) if slot_cell(s) != T.atlas_cell_xy(s)]
    chk(not bad, 'slot_cell() 与 tcslib.atlas_cell_xy() 在 0..%d 上逐位一致 (不一致 %d 个)'
        % (62 * 44 - 1, len(bad)))
    tcs = T.Charset()
    for s in (bytes.fromhex('af a1 bd'), b'G058.I192', bytes.fromhex('b0 af'),
              bytes.fromhex('b1 b5 e7 f1'), bytes(range(0xA0, 0xB4))):
        mine = idx.decode_chars(s)
        theirs = [c for c in tcs.decode(s)[0]
                  if ord(c) >= 0x20 and not (PUA_LO <= ord(c) <= PUA_HI)]
        chk(mine == theirs, 'decode_chars(%s) == tcslib.Charset.decode 口径 (%r)'
            % (s.hex(' '), ''.join(mine)))
    t = idx.decode_text(bytes.fromhex('af a1 bd'))
    chk(t == '的方', 'AF A1 BD 解为 %r (期望 的方; res_text_dump.py 的"对偶优先"会误读成 弗开)'
        % t)
    # ── 容量: 只断言**自洽**, 不断言历史数字 (charset 会被扩字库轮次合法改写) ──
    cap = idx.pair_capacity()
    chk(cap['total'] == (LEGAL_LEAD_HI - LEGAL_LEAD_LO) * (TRAIL_HI - TRAIL_LO + 1),
        '合法对偶空间 = 13 × 94 = %d (与 lead/trail 区间定义自洽)' % cap['total'])
    chk(cap['used'] + cap['free'] == cap['total'],
        '已用 %d + 空位 %d = %d ✓ (自洽)' % (cap['used'], cap['free'], cap['total']))
    chk(cap['dead'] == len([p for p in idx.pair_of if p[0] >= LEGAL_LEAD_HI]),
        '死 pair (lead>=0xAE) = %d 个 (按定义统计)' % cap['dead'])
    chk(all(LEGAL_LEAD_LO <= p[0] < LEGAL_LEAD_HI or p[0] >= LEGAL_LEAD_HI
            for p in idx.pair_of), '所有对偶的 lead 都落在定义域内 ✓')
    # ── 扫描字母表: 断言"等于由字符集推出的集合", 不写死数字 ──
    want = set(range(0x20, 0x7F)) | set(idx.codes) | \
        {p[0] for p in idx.pair_of} | {p[1] for p in idx.pair_of} | set(BTN_BYTES)
    chk(set(idx.alphabet) == want and len(idx.alphabet) == len(want),
        '扫描字母表 %d 个字节, 等于由字符集推出的集合 ✓' % len(idx.alphabet))
    # ── ★ 字符集自身的风险 (与 charset 版本无关的通用检查) ──
    shadow = sorted(ch for ch, b in idx.enc_single.items() if b < 0x80)
    poison = sorted(ch for ch, b in idx.enc_single.items() if 0x80 <= b <= 0x9F)
    both = sorted(set(idx.enc_single) & set(idx.enc_pair))
    both_legal = [c for c in both if LEGAL_LEAD_LO <= idx.enc_pair[c][0] < LEGAL_LEAD_HI]
    print('   [i] 现役字符集: 单字节码 %d 个, 对偶码 %d 个, 去重后 %d 字'
          ' (构筑期 GR_ZH92 font dump 是 76 + 1281 = 1357)'
          % (len(idx.enc_single), len(idx.enc_pair), len(idx.chars)))
    print('   [i] 容量: 合法对偶空间 %d, 已用 %d, 空位 %d, 死 pair %d'
          % (cap['total'], cap['used'], cap['free'], cap['dead']))
    if shadow:
        print('   [!!] %d 个单字节码 < 0x80 (%s) —— tcslib.decode 先走 `v < 0x80` ASCII 分支,'
              % (len(shadow), ' '.join('%s=0x%02X' % (c, idx.enc_single[c])
                                       for c in shadow[:6])))
        print('        这些码位上的字**永远解不回来** (encode_strict 的对称自检会失败);'
              ' 本工具的扫描器同口径, 也看不见它们 ⇒ 会误判为可回收。')
    if poison:
        print('   [!!] %d 个单字节码落在 0x80..0x9F (工具链"毒区";'
              ' tools/hanliu/tools/text_replace.py 明确拒绝写出)' % len(poison))
        print('        例: %s' % ' '.join('%s=0x%02X' % (c, idx.enc_single[c])
                                          for c in poison[:6]))
    if both:
        print('   [i] %d 个字**同时**有单字节码和对偶码 (%s) —— encode() 单字节优先,'
              % (len(both), ''.join(both[:12])))
        print('        对偶那一份是"死重量"。其中对偶 lead 合法的有 %d 个 %s'
              % (len(both_legal),
                 '(它们占着合法格位却永不被编码 ⇒ 额外的可回收格位!)'
                 if both_legal else '(都是死 pair, 不占合法格位 ⇒ 无影响)'))
    # ★ 自相矛盾检查: charset 自己的 codes 落在自己的 protected / mark_codes 里
    conflict = sorted((c, idx.enc_single[c]) for c in idx.enc_single
                      if idx.enc_single[c] in idx.protected
                      or idx.enc_single[c] in idx.mark_codes)
    if conflict:
        print('   [!!] charset **自相矛盾**: %d 个单字节码落在它自己的 protected/mark_codes 里'
              % len(conflict))
        print('        %s' % ' '.join('%s=0x%02X' % (c, b) for c, b in conflict[:10]))
        print('        这些字被本工具列为"不许回收"(尊重 charset 自带的保护), 但按定义它们'
              '本就不该占用这些码位 ⇒ 建议扩字库侧核对 (protected 原意: 英文盘在用的 '
              '® ± µ ç ñ + 毒区字节 0x92)。')
    import random
    random.seed(20261005)
    rnd = bytes(random.randrange(256) for _ in range(1 << 20))
    h = blob_hits(rnd, idx, 4, (TEXT_RUN_MIN, 16, 24))
    n16 = len([c for c in h[16] if c in idx.enc_pair])
    chk(n16 > 0, '1 MB 纯随机数据在 E2(>=16) 口径下命中 %d 个对偶字 —— '
        '这就是**噪声本底**, 必须靠对照盘减掉 (实测中文盘/英文盘命中数几乎相同)' % n16)
    # 不变式: 造一个"回收 5 个字"的假清单, 验证映射逐字节不变
    fake = dict(reclaim=sorted(idx.chars)[:5], blocked={}, counts={})
    new = make_new_charset(idx, fake)
    keep_ok = all(new['codes'].get(k) == v for k, v in idx.raw['codes'].items()
                  if k not in set(fake['reclaim']))
    keep_ok &= all(new['pair_of'].get(k) == v for k, v in idx.raw['pair_of'].items()
                   if k not in set(fake['reclaim']))
    chk(keep_ok, '不变式①: 回收 5 个字后, 其余 %d 个字的映射逐字节不变'
        % (len(idx.raw['codes']) + len(idx.raw['pair_of']) - 5))
    chk(all(k in new['codes'] or k in new['pair_of'] for k in fake['reclaim']) is False,
        '不变式②: 被回收的字确实从输出里消失')
    for k in ('mode', 'trim19', 'markers', 'mark_codes', 'protected', 'grid'):
        chk(new.get(k) == idx.raw.get(k), '顶层字段 %r 原样保留' % k)
    print('自检结论: %s' % ('[ok] 通过 ✓' if ok else '[!!] 失败'))
    return ok


if __name__ == '__main__':
    sys.exit(main())
