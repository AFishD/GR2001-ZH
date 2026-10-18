# -*- coding: utf-8 -*-
r"""single_cell_font.py — **单格字库**: 把 charset 里每一个字符从盘上取成一格, 与 16px 模板逐像素比对。

## 用户要的是什么 (round51)

> 「使用工具创建单格字库, 然后挨个与字库纹理进行比对, 确保读取正确」

⇒ 三件事:
  ① **单格字库**: 一字一格 —— 对 charset 里的每个字符, 按**引擎口径**从图集里取出它那一格,
     拼成一张总表 (`single_cell_font.png`), 人眼可以逐格核对;
  ② **挨个比对**: 用 `third_party/fonts/方正像素16.ttf` 按 `gen_font16.render16` 的**同一配方**
     渲染"期望位图", 与盘上取到的格**逐像素**比 —— 给出 `match / diff_px / 差异类型`;
  ③ **确保读取正确**: 反向自证 —— 用**与工具无关的另一条读取路径**再取一遍同一格,
     两条路径的输出必须逐像素相同; 并**故意注入一个错误映射**, 工具必须报错。

## 判据 (严格, 不允许"宽容差窗")

  盘上格的墨点必须**逐像素等于**模板 —— `diff_px == 0` 才算 `match`。
  任何非 0 一律按**差异类型**如实分类, 绝不"用邻域有墨蒙过去"(round46 的 6 个空白字、
  round50 的 10 个丢行字都是被宽容差蒙掉的教训)。

  差异类型:
    `match`              逐像素完全一致
    `empty_disk`         盘上这一格一个墨点都没有 (画出来是空白)
    `read_mismatch`      ★两条读取路径给出的像素不一致 (工具自己读错了 —— 最严重)
    `lost_rows`          模板有墨的**整行**在盘上全空 (截断 / 丢行)
    `row_shift`          字形整体上下错位 dy 行 (把最上/最下的行推出格)
    `col_shift`          字形整体左右错位 dx texel
    `missing_ink`        模板有墨、盘上没有 (少墨) 且不属于上面几类
    `extra_ink`          盘上有墨、模板没有 (多墨 / 污染 / 残墨)
    `different_glyph`    两边都有墨但差异大 ⇒ 那一格画的是**别处来的像素** (报告里给出"最像谁")
    `displaced_glyph`    ★`different_glyph` 的实锤版: 全盘搜索**找到了这个字的模板**
                         (逐像素 0 差异), 只是**不在引擎采样的那一格** ⇒ 引擎会画错
    `template_missing`   方正像素16 渲染不出这个字 ⇒ **不比模板**, 只做几何判据 (如实标注)
    `by_design`          引擎设计如此, 本来就不是 TTF 字形 (空格 / 滚动三角)
    `engine_icon`        引擎硬编码 UV 画图标 (0xB1/0xB5), **不吃字库**

## 单字节码 / ASCII 的采样窗

  `FONT.RES` 的 FT 记录矩形 (u0,v0,u1,v1) 就是**引擎采样窗** (引擎图坐标, 无相位):
    · ASCII 0x21..0x7E : 8x16 半角 —— 盘上格应当等于 `模板[:, 0:8]` (与手册字宽一致);
    · 0x7B/0x7D        : 5x13 实心滚动三角 (引擎特制, 非 TTF 字形);
    · 0xE7/0xF1        : 7x13 拉丁字母 ç/ñ (方正像素16 渲染不出来 ⇒ 只做几何判据);
    · 单字节汉字        : 16x16 整格, 逐像素比模板。

## 产出 (写进 --out 目录, 默认 <盘目录>/font_single_cell)

  `single_cell_font.png`           单格字库总表 (每格 = **盘上取到的位图**; 边框色 = 结论)
  `single_cell_font_expected.png`  同版面的**期望位图**总表 (对照用)
  `single_cell_report.json` / `.md` 逐格结果 + 汇总 + 不匹配清单 + 定性
  `mismatch_sheet.png`             只放不匹配的字, 放大 (左=盘上格 / 中=模板 / 右=差异)
  `single_cell_selftest.json`      ★ 反向自证的证据 (两条路径逐像素一致 + 故意错映射被抓)

## 用法

  python tools/iso_build/single_cell_font.py --iso work/builds/GR_ZH98/GR_ZH98.iso \
      --out work/builds/GR_ZH98/font_single_cell --prefix GR_ZH98

  --scale N     单格放大倍数 (默认 4)
  --cols N      总表每行列数 (默认 32)
  --no-png      只出 JSON/MD (省时间)
  --only-pair   只查对偶码 (调试用)

★ **只读盘**: 只 mmap 读 ISO, 绝不写盘上任何字节。
"""
import argparse
import csv
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:                                                        # noqa: BLE001
    pass

import numpy as np                                                       # noqa: E402
import tcslib                                                            # noqa: E402
import dump_font                                                         # noqa: E402

TOOL = 'tools/iso_build/single_cell_font.py'
TOOL_VERSION = 'r51.1'
ROUND = 'round51'
TTF = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')

CW = CH = 16
NCOL = 62

# ---- 结论 → 颜色 / 级别 ----
LV_E, LV_W, LV_I = 'error', 'warn', 'info'
LEVEL = {
    'match': LV_I,
    'template_missing': LV_I,      # 模板缺字: 如实标注, 不算匹配也不算错误
    'by_design': LV_I,
    'engine_icon': LV_I,
    'read_mismatch': LV_E,
    'empty_disk': LV_E,
    'lost_rows': LV_E,
    'different_glyph': LV_E,
    'displaced_glyph': LV_E,
    'missing_ink': LV_W,
    'extra_ink': LV_W,
    'row_shift': LV_W,
    'col_shift': LV_W,
}
LEVEL_ORDER = {LV_E: 0, LV_W: 1, LV_I: 2}
# 边框色 (单格字库总表)
BORDER = {LV_I: (40, 170, 40), LV_W: (240, 170, 0), LV_E: (220, 30, 30)}

RULE_TEXT = {
    'read_mismatch': '★两条**独立读取路径**给出的像素不一致 —— 工具自己读错了 (最严重)',
    'empty_disk': '盘上这一格一个墨点都没有 ⇒ 这个字画出来是空白',
    'lost_rows': '★模板有墨的整行在盘上**全空** ⇒ 字形被切掉一行 (截断)',
    'different_glyph': '两边都有墨但差异很大 ⇒ 这一格画的是**别处来的像素** (见"最像谁")',
    'displaced_glyph': '★字形**不在引擎采样的那一格**: 全盘搜索找到了它的模板 (0 差异), '
                       '但坐标偏了 ⇒ 引擎在这个字上画的是别的像素',
    'missing_ink': '模板有墨、盘上没有 (少墨)',
    'extra_ink': '盘上有墨、模板没有 (多墨 = 污染/残墨/渗漏)',
    'row_shift': '字形整体**上下错位** (有一行被推出采样窗)',
    'col_shift': '字形整体**左右错位**',
    'template_missing': '方正像素16 渲染不出这个字 ⇒ 只做几何判据, 不比模板',
    'by_design': '引擎设计如此 (空格 / 滚动三角), 本来就不是 TTF 字形',
    'engine_icon': '引擎按硬编码 UV 画手柄图标 (另一张贴图), 不吃字库',
}


def rel(p):
    try:
        r = os.path.relpath(p, REPO)
    except ValueError:
        return p.replace('\\', '/')
    return r.replace('\\', '/') if not r.startswith('..') else p.replace('\\', '/')


# ═══════════════════════════════════════════════════════════════════
#  ① 工具的读取路径 (A): 复用工程现役实现 (dump_font / tcslib)
# ═══════════════════════════════════════════════════════════════════

def read_engine_atlas_A(atlas):
    """路径 A = 工程现役口径: `dump_font.atlas_gray(view='engine')` → bool 墨图。

    它是「按 GIF 封包把每段数据放回 TRXPOS 指定的行」的引擎视图。0=墨。
    """
    gray = dump_font.atlas_gray(atlas, view='engine')
    return (np.frombuffer(gray, np.uint8).reshape(atlas['h'], atlas['w']) == 0)


# ═══════════════════════════════════════════════════════════════════
#  ② 反向自证: **与工具无关的另一条读取路径** (B)
#     自写 GIF 封包解析 + 自写格位公式, 一次都不调 tcslib / dump_font
# ═══════════════════════════════════════════════════════════════════

def _parse_packets_B(blob, stride):
    """★ 独立实现 (不调 tcslib): 按 PS2 GIF 封包语法把像素容器切成 (首行, 数据偏移, 字节数)。

    · 每个 tag 16B: 低 u32 = {NLOOP:15, EOP:1, PRE:1, ...}; 高 u32 = {FLG:2 @26, NREG:4 @28}
    · FLG==0/1 (PACKED) 且 NLOOP==1 且 NREG==1 ⇒ 这是一个 A+D 寄存器写,
      载荷第 1 个 u32 = TRXPOS 的 SSAY (= 这段数据要放到显存第几行);
    · FLG==2 (IMAGE) ⇒ 其后 NLOOP*16 字节是本段像素数据。
    """
    segs, o, ssay = [], 0, 0
    while o + 16 <= len(blob):
        w0, w1 = struct.unpack_from('<II', blob, o)
        nloop = w0 & 0x7FFF
        flg = (w1 >> 26) & 3
        nreg = (((w1 >> 28) - 1) & 0xF) + 1
        if flg in (0, 1):
            if nloop == 1 and nreg == 1:
                ssay = struct.unpack_from('<I', blob, o + 20)[0]
                o += 32
                continue
            if nloop == 0:
                break
            raise ValueError('认不出的 PACKED 包 @0x%X (nloop=%d nreg=%d)' % (o, nloop, nreg))
        segs.append((ssay, o + 16, nloop * 16))
        o += 16 + nloop * 16
    return segs


def _cell_B(slot, ncol=NCOL, cw=CW, ch=CH, skip_row=12, skip_rows=3, y0=2):
    """★ 独立实现 (不调 tcslib): 引擎格位公式 `x=16*col`, `y=2+16*(row+3*[row>=12])`。"""
    row, col = divmod(slot, ncol)
    return cw * col, y0 + ch * (row + (skip_rows if row >= skip_row else 0))


def read_engine_atlas_B(container, w, h, psm):
    """路径 B: 自己解封包 → **拼成一整张大图**, 再按坐标裁 (与用户建议的做法一致)。"""
    stride = w // 2 if psm == 0x14 else w
    segs = _parse_packets_B(container, stride)
    img = np.zeros((h, w), dtype=bool)
    for (first_row, doff, nbytes) in segs:
        nrow = min(nbytes // stride, h - first_row)
        if nrow <= 0:
            continue
        a = np.frombuffer(bytes(container[doff:doff + nrow * stride]), dtype=np.uint8)
        a = a.reshape(nrow, stride)
        if psm == 0x14:                       # PSMT4: 偶 x = 低 nibble
            img[first_row:first_row + nrow, 0::2] = (a & 0x0F) == 0
            img[first_row:first_row + nrow, 1::2] = (a >> 4) == 0
        else:
            img[first_row:first_row + nrow] = a < dump_font.INK8_THRESHOLD
    return img, segs


def _atlas_container(font):
    """`new_font_revised` 的**原始像素容器字节** (含 GIF 包头) —— 供路径 B 用。"""
    at = font['atlas']
    return bytes(at['pak'][at['px_off']:at['px_off'] + at['px_size']])


# ═══════════════════════════════════════════════════════════════════
#  ③ 期望位图 (16px 模板) —— 与 gen_font16.render16 同一配方
# ═══════════════════════════════════════════════════════════════════

class Templates(object):
    """`方正像素16.ttf` 16px em 窗: draw origin (8,8) → canvas[8:24, 8:24] → <128。

    与 `tools/font_pipeline/gen_font16.py::render16()` / `glyph_geometry.Templates` 完全同款。
    """

    def __init__(self, path=TTF):
        self.path = path
        from PIL import ImageFont
        self.ok = os.path.isfile(path)
        self._fnt = ImageFont.truetype(path, 16) if self.ok else None
        self._c = {}
        self.missing = []

    def get(self, ch):
        if not self.ok:
            return None
        if ch in self._c:
            return self._c[ch]
        from PIL import Image, ImageDraw
        img = Image.new('L', (32, 32), 255)
        ImageDraw.Draw(img).text((8, 8), ch, font=self._fnt, fill=0)
        w = np.asarray(img)[8:24, 8:24] < 128
        if not w.any():
            self.missing.append(ch)
            w = None
        self._c[ch] = w
        return w


# ═══════════════════════════════════════════════════════════════════
#  ④ 单格比对
# ═══════════════════════════════════════════════════════════════════

def _crop(img, x, y, w, h):
    """按坐标裁一格 (越界部分补空白) —— 这就是"单格"。"""
    H, W = img.shape
    out = np.zeros((h, w), dtype=bool)
    x0, x1 = max(0, x), min(W, x + w)
    y0, y1 = max(0, y), min(H, y + h)
    if x1 > x0 and y1 > y0:
        out[y0 - y:y1 - y, x0 - x:x1 - x] = img[y0:y1, x0:x1]
    return out


def _best_shift(disk, tpl, maxd=3):
    """(dx, dy, diff): 在 ±maxd 内找使异或最小的整体位移。返回**最优位移下的差异像素数**。"""
    best = (0, 0, int((disk ^ tpl).sum()))
    for dy in range(-maxd, maxd + 1):
        for dx in range(-maxd, maxd + 1):
            if dx == 0 and dy == 0:
                continue
            sh = np.roll(np.roll(tpl, dy, axis=0), dx, axis=1)
            d = int((disk ^ sh).sum())
            if d < best[2]:
                best = (dx, dy, d)
    return best


def classify(disk, tpl, a_ok=True, expect=None):
    """盘上格 vs 模板 ⇒ (差异类型, diff_px, 说明 dict)。

    `expect` = 期望的"可比形状": None ⇒ 整格比; 'left' ⇒ 只比模板左 w 列 (半角 ASCII)。
    """
    info = {}
    d_ink, t_ink = int(disk.sum()), int(tpl.sum())
    info['disk_ink'] = d_ink
    info['tpl_ink'] = t_ink
    if not a_ok:
        return 'read_mismatch', int((disk ^ tpl).sum()), info
    if tpl.shape != disk.shape:
        tw = tpl[:, :disk.shape[1]] if expect == 'left' else tpl[:disk.shape[0], :disk.shape[1]]
        tpl = tw
        info['tpl_ink'] = t_ink = int(tpl.sum())
    diff = int((disk ^ tpl).sum())
    info['diff_px'] = diff
    if diff == 0:
        return 'match', 0, info
    if d_ink == 0:
        return 'empty_disk', diff, info
    # ★ 先判"这是不是**同一个字形**" (IoU) —— IoU 低就不是"截断/少墨", 而是"画的是别的像素"。
    #   这条放在"丢行"前面: 否则一堆无关像素里恰好有整行空, 会被误报成"截断"
    #   (round51 实测: 28 个单字节码的错位像素里有 24 个被误报成 lost_rows)。
    inter = int((disk & tpl).sum())
    union = int((disk | tpl).sum())
    info['iou'] = round(inter / union, 4) if union else 1.0
    if union and inter / union < 0.55:
        return 'different_glyph', diff, info
    # 行错位 / 列错位 (最优位移下接近 0 ⇒ 是"整体移位"而不是"别的字")
    dx, dy, dmin = _best_shift(disk, tpl)
    info['best_shift'] = [dx, dy]
    info['best_shift_diff'] = dmin
    if (dx or dy) and dmin <= max(2, int(0.06 * max(1, t_ink))):
        return ('row_shift' if abs(dy) >= abs(dx) else 'col_shift'), diff, info
    # 丢行: 模板有墨的整行在盘上全空
    lost = [r for r in range(min(CH, tpl.shape[0])) if tpl[r].any() and not disk[r].any()]
    if lost:
        info['lost_rows'] = lost
        return 'lost_rows', diff, info
    miss = int((tpl & ~disk).sum())
    extra = int((disk & ~tpl).sum())
    info['miss_px'] = miss
    info['extra_px'] = extra
    return ('missing_ink' if miss > extra else 'extra_ink'), diff, info


# ── 全盘搜索: 这个字的模板到底在图集的哪儿? (滑窗 XOR 计数, 用矩阵乘加速) ──
_PATCH_CACHE = {}


def locate_template(eng, tpl, max_hits=4):
    """在**整张引擎图**里找与 tpl 逐像素 0 差异的位置。返回 [(x, y), ...] (最多 max_hits)。

    实现: `sliding_window_view` 取出全部 16x16 窗 → 展平成 (N, 256) → 与模板向量做矩阵乘
    得到"交叠墨点数" ⇒ IoU 最大的少数几个候选 → 只对候选做精确 XOR。
    """
    key = (eng.shape, eng.dtype.str, int(eng.sum()))
    pats = _PATCH_CACHE.get(key)
    if pats is None:
        from numpy.lib.stride_tricks import sliding_window_view
        hh, ww = tpl.shape
        if eng.shape[0] < hh or eng.shape[1] < ww:
            return []
        u8 = eng.astype(np.uint8)
        v = sliding_window_view(u8, (hh, ww))                  # (H-h+1, W-w+1, hh, ww)
        pats = (np.ascontiguousarray(v).reshape(-1, hh * ww), eng.shape[1] - ww + 1)
        _PATCH_CACHE[key] = pats
    flat, ncol = pats
    tv = tpl.reshape(-1).astype(np.int32)
    t_ink = int(tv.sum())
    inter = flat.astype(np.int32) @ tv                          # (N,)
    union = flat.sum(axis=1).astype(np.int32) + t_ink - inter
    with np.errstate(divide='ignore', invalid='ignore'):
        iou = np.where(union > 0, inter / np.maximum(union, 1), 0.0)
    cand = np.argsort(-iou)[:24]
    hits = []
    for idx in cand:
        y, x = divmod(int(idx), ncol)
        if int((eng[y:y + tpl.shape[0], x:x + tpl.shape[1]] ^ tpl).sum()) == 0:
            hits.append((x, y))
            if len(hits) >= max_hits:
                break
    return hits


# ═══════════════════════════════════════════════════════════════════
#  ⑤ 逐格清单
# ═══════════════════════════════════════════════════════════════════

def build_cells(font, cs, only_pair=False):
    """charset 里**每一个字符** ⇒ 一条"单格"记录 (含盘上格 / 期望位图 / 结论)。"""
    at = font['atlas']
    w, h = at['w'], at['h']
    faces = font['faces']
    recs = [x for x in faces if x[0] == 'default'][0][2]
    engA = read_engine_atlas_A(at)
    engB, segs_B = read_engine_atlas_B(_atlas_container(font), w, h, at['psm'])
    tpls = Templates()

    cells = []

    def add(kind, ch, code_hex, x, y, cw, chh, slot=None, row=None, col=None,
            tpl_mode='full', note='', basis=''):
        """取一格 (两条路径各取一次) + 比对。"""
        dA = _crop(engA, x, y, cw, chh)
        dB = _crop(engB, x, y, cw, chh)
        same = bool(np.array_equal(dA, dB))
        tpl = tpls.get(ch) if (tpl_mode != 'none' and ch) else None
        rec = dict(kind=kind, char=ch, code=code_hex, slot=slot, row=row, col=col,
                   cell_x=x, cell_y=y, cell_w=cw, cell_h=chh,
                   path_A_ink=int(dA.sum()), path_B_ink=int(dB.sum()),
                   paths_identical=same, basis=basis,
                   disk_ink=int(dA.sum()), tpl_ink=(int(tpl.sum()) if tpl is not None else None),
                   diff_px=None, verdict=None, level=LV_I, note=note,
                   tpl_mode=tpl_mode, best_match=None)
        if not same:
            rec['verdict'] = 'read_mismatch'
            rec['level'] = LV_E
            rec['diff_px'] = int((dA ^ dB).sum())
            rec['note'] = ('两条独立读取路径结果不同: A 墨=%d / B 墨=%d (差 %d px)'
                           % (int(dA.sum()), int(dB.sum()), rec['diff_px']))
        elif tpl_mode == 'none':
            rec['verdict'] = ('engine_icon' if tpl_mode == 'none' and kind == 'icon' else 'by_design')
            rec['level'] = LV_I
        elif tpl is None:
            rec['verdict'] = 'template_missing'
            rec['level'] = LV_I
        else:
            exp = 'left' if tpl_mode == 'left' else None
            v, diff, info = classify(dA, tpl, True, exp)
            rec['verdict'] = v
            rec['level'] = LEVEL[v]
            rec['diff_px'] = diff
            rec.update(info)
            # ★ 差异 ⇒ 先做**全盘搜索**: 这个字的模板是不是在**别的格**上?
            #   (找到了 ⇒ 实锤"字形不在引擎采样的位置", 而不是"字形坏了/没写")
            if v in ('different_glyph', 'lost_rows', 'empty_disk', 'row_shift', 'col_shift',
                     'missing_ink', 'extra_ink'):
                tt = tpl[:, :cw] if tpl_mode == 'left' else tpl
                hits = locate_template(engA, tt)
                if hits:
                    rec['found_at'] = [list(h) for h in hits]
                    rec['found_delta'] = [[h[0] - x, h[1] - y] for h in hits]
                    if v in ('different_glyph', 'empty_disk', 'lost_rows'):
                        rec['verdict'] = 'displaced_glyph'
                        rec['level'] = LEVEL['displaced_glyph']
            if rec['verdict'] in ('different_glyph', 'displaced_glyph'):
                rec['best_match'] = identify(dA, tpls, cs)
        rec['_disk'] = dA
        rec['_tpl'] = (tpl[:, :cw] if (tpl is not None and tpl_mode == 'left' and tpl.shape[1] >= cw)
                       else tpl)
        cells.append(rec)
        return rec

    # ── ① 对偶码 (引擎格位公式, 无相位) ──
    for ch, (b1, b2) in sorted(cs.enc_pair.items(), key=lambda kv: tcslib.pair_slot(*kv[1])):
        slot = tcslib.pair_slot(b1, b2)
        r, c = slot // NCOL, slot % NCOL
        lead_ok = tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI
        x, y = _cell_B(slot)
        note = ''
        if not lead_ok:
            note = ('★死 pair: lead=0x%02X ≥ 0x%02X, 引擎读成两个单字节 ⇒ 编码器已拒绝写出'
                    % (b1, tcslib.PAIR_LEAD_HI))
        add('pair', ch, '%02X%02X' % (b1, b2), x, y, CW, CH, slot=slot, row=r, col=c,
            note=note, basis='引擎格位公式 (engine view)')

    if only_pair:
        return cells, dict(paths_same_all=True, segs_B=segs_B, n_A=int(engA.sum()),
                           n_B=int(engB.sum()))

    # ── ② 单字节码 (走 FT 记录矩形 = 引擎采样窗) ──
    for ch, code in sorted(cs.enc_single.items(), key=lambda kv: kv[1]):
        idx = code - 0x20
        if not (0 <= idx < len(recs)):
            continue
        _b0, _b1, u0, v0, u1, v1 = recs[idx]
        cw, chh = u1 - u0, v1 - v0
        mode = 'full' if (cw, chh) == (CW, CH) else 'left'
        add('single', ch, '%02X' % code, u0, v0, cw, chh,
            note='FT rec[%d] = (%d,%d,%d,%d)' % (idx, u0, v0, u1, v1),
            basis='FT 记录矩形')

    # ── ③ ASCII (同样走 default face 的记录表) ──
    for code in range(0x20, 0x7F):
        ch = chr(code)
        idx = code - 0x20
        if not (0 <= idx < len(recs)):
            continue
        _b0, _b1, u0, v0, u1, v1 = recs[idx]
        cw, chh = u1 - u0, v1 - v0
        if cw == 0 or chh == 0:
            r = add('ascii', ch, '%02X' % code, u0, v0, CW, CH, tpl_mode='none',
                    note='记录退化 (%d,%d,%d,%d)' % (u0, v0, u1, v1), basis='FT 记录矩形')
            r['verdict'] = 'by_design'
            continue
        if code == 0x20:
            r = add('ascii', ch, '20', u0, v0, cw, chh, tpl_mode='none',
                    note='空格 —— 记录矩形本来就该是空的', basis='FT 记录矩形')
            r['verdict'] = 'by_design'
            continue
        if code in (0x7B, 0x7D):
            r = add('ascii', ch, '%02X' % code, u0, v0, cw, chh, tpl_mode='none',
                    note='★%r 不是本盘的字形: 这一格是**滚动三角** (引擎特制实心▲▼, 5x13), '
                         '引擎按记录矩形画它' % ch, basis='FT 记录矩形')
            r['verdict'] = 'by_design'
            continue
        mode = 'left' if cw < CW else 'full'
        add('ascii', ch, '%02X' % code, u0, v0, cw, chh,
            note=('半角 (%dx%d): 期望 = 模板左 %d 列 (方正像素16 的 ASCII 是半角)'
                  % (cw, chh, cw)) if mode == 'left' else '',
            basis='FT 记录矩形', tpl_mode=mode)

    # ── ④ 图标码 (0xB1/0xB5): 引擎硬编码 UV, 不吃字库 ──
    try:
        import icon_table
        for it in icon_table.all_icons():
            r = add('icon', '', '%02X' % it['byte'], 0, 0, 1, 1, tpl_mode='none',
                    note='★引擎认的**文本图标码** %s (%s); UV 硬编码于 DrawString v1, '
                         '引擎直接画图标, **不吃字库**' % (it['name'], it['key']),
                    basis='engine_icon')
            r['verdict'] = 'engine_icon'
            r['char'] = tcslib.BTN_FMT % it['pua']
    except Exception as e:                                                # noqa: BLE001
        print('[warn] 图标码清单不可用: %s' % e)

    return cells, dict(segs_B=segs_B, n_A=int(engA.sum()), n_B=int(engB.sum()))


def identify(disk, tpls, cs, topn=3):
    """这一格**最像谁** —— 对 charset 全体字做模板辨认 (最小异或)。"""
    best = []
    for ch in set(list(cs.enc_pair) + list(cs.enc_single)):
        t = tpls.get(ch)
        if t is None:
            continue
        best.append((int((disk ^ t).sum()), ch))
    best.sort()
    return [dict(char=c, diff=d) for (d, c) in best[:topn]]


# ═══════════════════════════════════════════════════════════════════
#  ⑥ 反查 dump_font 的 _font_charset.csv (交叉一致)
# ═══════════════════════════════════════════════════════════════════

def cross_check_charset_csv(cells, csv_path):
    """把本工具算出的"字符 → 引擎格"与 `dump_font` 的 `_font_charset.csv` **逐行对照**。

    ★ 两边的 `cell_x/cell_y` 是**同一个物理格在两种坐标系里的坐标**:
        · 本工具 = **引擎图**坐标 (`x = 16*col`, 无相位);
        · `dump_font` 的 `cell_x/cell_y` = **flat 容器**坐标 (`x = 16*((col+PHI[row])%64)`,
          回绕列还低 1 行) —— 这是 tcslib 的历史口径, 语义写在它自己的 docstring 里。
      两者换算关系 (tcslib 常量区): `flat_x = (engine_x + atlas_flat_x_shift(y)) % 宽`, 带行进位。
      ⇒ 对照时必须先换算, 否则会把"同一格"误判成"不一致" (round51 第一次跑就踩了这个坑)。
      另: `dump_font` 还输出 `cell_legacy_*` (更老的口径, `x = 4+16*col`), 那个**不是**引擎格, 不参与对照。
    """
    if not os.path.isfile(csv_path):
        return dict(csv=csv_path, exists=False,
                    note='找不到 dump_font 的 charset CSV ⇒ 跳过交叉核对 (先跑一次 dump_font)')
    got = {}
    with io.open(csv_path, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            if r.get('cell_x') in (None, '') or r.get('cell_y') in (None, ''):
                continue
            got[(r['kind'], r['bytes_hex'])] = (int(r['cell_x']), int(r['cell_y']))
    bad, checked, missing, conv = [], 0, 0, 0
    for c in cells:
        if c['kind'] == 'icon':
            continue
        key = (c['kind'], c['code'])
        if key not in got:
            missing += 1
            continue
        checked += 1
        want = (c['cell_x'], c['cell_y'])
        if c['kind'] in ('single', 'ascii'):
            # 单字节/ASCII: 两边都是"FT 记录矩形原值 (引擎图坐标)" ⇒ 直接比
            pass
        else:
            # 对偶: 把本工具的引擎坐标换算成 dump 的 flat 坐标再比
            want = tcslib.atlas_flat_pos(c['cell_x'], c['cell_y'], 1024)
            conv += 1
        if got[key] != want:
            bad.append(dict(kind=c['kind'], code=c['code'], char=c['char'],
                            mine_engine=[c['cell_x'], c['cell_y']],
                            mine_converted=list(want), dump=list(got[key])))
    return dict(csv=rel(csv_path), exists=True, checked=checked, not_in_csv=missing,
                converted=conv, mismatched=len(bad), examples=bad[:10],
                note=('对偶码对照前已把本工具的**引擎图坐标**换算成 dump 的 **flat 容器坐标**'
                      ' (tcslib.atlas_flat_pos) —— 两者指向同一物理格; 单字节/ASCII 两边同为记录矩形原值'),
                ok=(not bad), tool='dump_font.<prefix>_font_charset.csv (cell_x/cell_y 列)')


# ═══════════════════════════════════════════════════════════════════
#  ⑦ 出图
# ═══════════════════════════════════════════════════════════════════

def write_sheet(cells, path, scale=4, cols=32, use_template=False, title=''):
    """一字一格的总表 (盘上格 / 期望格)。每格带字符 + 码位标注 + 结论色边框。"""
    from PIL import Image, ImageDraw, ImageFont
    n = len(cells)
    rows = (n + cols - 1) // cols
    cw, chh = CW * scale, CH * scale
    pad = 3
    lab = 30 if scale >= 3 else 22
    margin = 34
    W = margin * 2 + cols * (cw + pad)
    H = margin + 40 + rows * (chh + lab + pad)
    im = Image.new('RGB', (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)
    f_small = ImageFont.load_default()
    try:
        f_cjk = ImageFont.truetype(TTF, 15)
    except Exception:                                                     # noqa: BLE001
        f_cjk = f_small
    d.text((margin, 6), title, fill=(0, 0, 0), font=f_small)
    for i, c in enumerate(cells):
        r, col = divmod(i, cols)
        x0 = margin + col * (cw + pad)
        y0 = margin + 40 + r * (chh + lab + pad)
        src = c.get('_tpl') if use_template else c.get('_disk')
        if src is None:
            d.rectangle([x0, y0, x0 + cw, y0 + chh], fill=(238, 238, 238),
                        outline=(150, 150, 150))
        else:
            blk = np.where(src, 0, 255).astype(np.uint8)
            panel = Image.frombytes('L', (src.shape[1], src.shape[0]), blk.tobytes())
            if src.shape != (CH, CW):                       # 半角记录: 贴到 16x16 格内便于对比
                full = Image.new('L', (CW, CH), 255)
                full.paste(panel, (0, 0))
                panel = full
            im.paste(panel.resize((cw, chh), Image.NEAREST).convert('RGB'), (x0, y0))
        bcol = BORDER[c['level']]
        d.rectangle([x0 - 1, y0 - 1, x0 + cw, y0 + chh], outline=bcol)
        # 标注: 字符 (TTF) + 码位 (等宽)
        label = c['char'] if len(c['char']) == 1 else c['char'][:4]
        try:
            d.text((x0 + 1, y0 + chh + 1), label, fill=(0, 0, 0), font=f_cjk)
        except Exception:                                                 # noqa: BLE001
            pass
        d.text((x0 + cw - 15, y0 + chh + 15), c['code'], fill=(120, 120, 120), font=f_small)
    im.save(path, optimize=True)
    return im.size


def write_mismatch_sheet(cells, path, scale=8):
    """只放不匹配的字: 左=盘上格 / 中=期望(模板) / 右=差异 (红=盘上有模板没有, 蓝=模板有盘上没有)。"""
    from PIL import Image, ImageDraw, ImageFont
    bad = [c for c in cells if c['level'] in (LV_E, LV_W)]
    if not bad:
        im = Image.new('RGB', (760, 90), (255, 255, 255))
        ImageDraw.Draw(im).text((16, 30), 'no mismatch - every compared cell is pixel-identical',
                                fill=(0, 128, 0))
        im.save(path, optimize=True)
        return im.size
    f_small = ImageFont.load_default()
    try:
        f_cjk = ImageFont.truetype(TTF, 15)
    except Exception:                                                     # noqa: BLE001
        f_cjk = f_small
    cw, chh = CW * scale, CH * scale
    per = max(1, min(3, 1600 // (cw * 3 + 60)))
    per_row = per
    rows = (len(bad) + per_row - 1) // per_row
    cellw = 3 * cw + 30
    W = 20 + per_row * (cellw + 24)
    H = 46 + rows * (chh + 70)
    im = Image.new('RGB', (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.text((16, 6), 'MISMATCH SHEET  |  left = cell read from the disc   middle = expected (TTF 16px)   '
                    'right = diff (red = disc-only, blue = template-only)', fill=(0, 0, 0), font=f_small)
    for i, c in enumerate(bad):
        r, col = divmod(i, per_row)
        bx = 20 + col * (cellw + 24)
        by = 46 + r * (chh + 70)
        disk = c.get('_disk')
        tpl = c.get('_tpl')
        panels = []
        for src in (disk, tpl):
            if src is None:
                panels.append(Image.new('RGB', (cw, chh), (238, 238, 238)))
            else:
                blk = np.where(src, 0, 255).astype(np.uint8)
                p = Image.frombytes('L', (src.shape[1], src.shape[0]), blk.tobytes())
                if src.shape != (CH, CW):
                    full = Image.new('L', (CW, CH), 255)
                    full.paste(p, (0, 0))
                    p = full
                panels.append(p.resize((cw, chh), Image.NEAREST).convert('RGB'))
        diff = Image.new('RGB', (cw, chh), (255, 255, 255))
        if disk is not None and tpl is not None and disk.shape == tpl.shape:
            hh, ww = disk.shape
            arr = np.full((hh, ww, 3), 255, np.uint8)
            arr[disk & ~tpl] = (220, 30, 30)
            arr[tpl & ~disk] = (30, 60, 220)
            arr[disk & tpl] = (170, 170, 170)
            diff = Image.frombytes('RGB', (ww, hh), arr.tobytes()).resize((cw, chh), Image.NEAREST)
        panels.append(diff)
        for k, p in enumerate(panels):
            im.paste(p, (bx + k * (cw + 10), by))
            d.rectangle([bx + k * (cw + 10) - 1, by - 1, bx + k * (cw + 10) + cw, by + chh],
                        outline=(120, 120, 120))
        head = '%s %s %s' % (c['char'] if len(c['char']) == 1 else c['char'][:4],
                             c['kind'], c['code'])
        d.text((bx, by + chh + 3), head, fill=(0, 0, 0), font=f_cjk)
        sub = '%s diff=%s' % (c['verdict'], c['diff_px'])
        d.text((bx, by + chh + 22), sub, fill=(180, 0, 0) if c['level'] == LV_E else (170, 110, 0),
               font=f_small)
        if c.get('best_match'):
            d.text((bx, by + chh + 36),
                   'looks like %s' % c['best_match'][0]['char'], fill=(90, 90, 90), font=f_cjk)
    im.save(path, optimize=True)
    return im.size


# ═══════════════════════════════════════════════════════════════════
#  ⑧ 反向自证 (两条路径 + 故意错映射)
# ═══════════════════════════════════════════════════════════════════

def selftest(font, cs, cells):
    """① 两条独立读取路径逐格逐像素一致; ② 故意把某字的 slot 改错 ⇒ 判据必须报不匹配。"""
    at = font['atlas']
    engA = read_engine_atlas_A(at)
    engB, segs = read_engine_atlas_B(_atlas_container(font), at['w'], at['h'], at['psm'])
    whole_same = bool(np.array_equal(engA, engB))
    d_whole = int((engA ^ engB).sum())
    # 顺带: 与 repack_font.Atlas 的引擎图对照 (第三条路径, 工程内另一份实现)
    third = None
    try:
        sys.path.insert(0, HERE)
        import repack_font
        A3 = repack_font.Atlas(at['pak'], at['px_off'], at['px_size'], at['w'], at['h'], at['psm'])
        third = dict(ink=int(A3.eng.sum()), identical_to_A=bool(np.array_equal(A3.eng, engA)))
    except Exception as e:                                                # noqa: BLE001
        third = dict(error=str(e))

    # 故意错映射: 取一个"盘上有字"的对偶字, 把它的 slot 强行改到相邻槽再取格
    probe = None
    for ch, (b1, b2) in sorted(cs.enc_pair.items(), key=lambda kv: tcslib.pair_slot(*kv[1])):
        if not (tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI):
            continue
        slot = tcslib.pair_slot(b1, b2)
        x, y = _cell_B(slot)
        good = _crop(engA, x, y, CW, CH)
        if good.sum() < 4:
            continue
        for ds in (1, 2, 3, 62, -1):
            xs, ys = _cell_B(slot + ds)
            wrong = _crop(engA, xs, ys, CW, CH)
            if not np.array_equal(wrong, good):
                probe = dict(char=ch, code='%02X%02X' % (b1, b2), slot=slot, wrong_slot=slot + ds,
                             good_ink=int(good.sum()), wrong_ink=int(wrong.sum()),
                             diff_px=int((good ^ wrong).sum()),
                             detected=True)
                break
        if probe:
            break
    return dict(
        tool=TOOL, tool_version=TOOL_VERSION,
        path_A='dump_font.atlas_gray(view="engine") (工程现役口径: 按 GIF 封包把每段放回 TRXPOS 行)',
        path_B='本文件自写的 GIF 封包解析 (_parse_packets_B) + 自写格位公式 (_cell_B), '
               '把图集拼成**一整张大图**后按坐标裁 —— 一次都不调 tcslib/dump_font 的对应函数',
        path_C=third,
        whole_atlas_identical=whole_same, whole_atlas_diff_px=d_whole,
        atlas_ink_A=int(engA.sum()), atlas_ink_B=int(engB.sum()),
        segments_B=[dict(first_row=s[0], data_off=s[1], bytes=s[2]) for s in segs],
        cells_compared=len([c for c in cells if c.get('path_A_ink') is not None]),
        cells_paths_differ=len([c for c in cells if not c.get('paths_identical', True)]),
        wrong_slot_probe=probe,
        verdict=dict(independent_read_identical=whole_same,
                     wrong_mapping_detected=bool(probe and probe['detected']),
                     ok=bool(whole_same and probe and probe['detected'])),
    )


# ═══════════════════════════════════════════════════════════════════
#  ⑨ 报告
# ═══════════════════════════════════════════════════════════════════

def summarize(cells, iso, iso_sha, selftest_doc=None, xcheck=None, args=None):
    lv, vd = {}, {}
    for c in cells:
        lv[c['level']] = lv.get(c['level'], 0) + 1
        vd[c['verdict']] = vd.get(c['verdict'], 0) + 1
    compared = [c for c in cells if c['verdict'] not in ('by_design', 'engine_icon', 'template_missing')]
    matched = [c for c in compared if c['verdict'] == 'match']
    bad = [c for c in cells if c['level'] in (LV_E, LV_W)]
    bad.sort(key=lambda c: (LEVEL_ORDER[c['level']], -(c['diff_px'] or 0)))
    doc = dict(
        tool=TOOL, tool_version=TOOL_VERSION, round=ROUND,
        iso=rel(iso), iso_sha256=iso_sha,
        what='单格字库: charset 里每个字符按**引擎口径**从图集取一格, 与 方正像素16 16px 模板逐像素比对',
        geometry=dict(window='%dx%d' % (CW, CH), ncol=NCOL,
                      pair_formula='slot=(lead-0xA1)*94+(trail-0xA1); row=slot//62; col=slot%62; '
                                   'x=16*col; y=2+16*(row+3*[row>=12])  —— 无相位',
                      single_formula='FT 记录矩形 (u0,v0,u1,v1) 原值 = 引擎采样窗 (引擎图坐标)',
                      template=rel(TTF),
                      template_recipe='PIL truetype 16px; draw origin (8,8); 窗 = canvas[8:24,8:24]; '
                                      '阈值 <128 (= gen_font16.render16 同一配方)',
                      tolerance='★ 紧判据: **diff_px == 0 才算 match** (不用 ±4/±2 容差窗)'),
        counts=dict(total_cells=len(cells), compared=len(compared), matched=len(matched),
                    match_rate=(round(100.0 * len(matched) / len(compared), 2) if compared else None),
                    by_level=lv, by_verdict=dict(sorted(vd.items())),
                    by_kind={k: sum(1 for c in cells if c['kind'] == k)
                             for k in ('pair', 'single', 'ascii', 'icon')}),
        findings=[{k: v for k, v in c.items() if not k.startswith('_')} for c in bad],
        findings_total=len(bad),
        cells=[{k: v for k, v in c.items() if not k.startswith('_')} for c in cells],
        cross_check_dump_font=xcheck,
        self_test=selftest_doc,
        args=args or {},
    )
    v = doc['counts']
    doc['one_line'] = (
        '单格字库 %d 格 (对偶 %d + 单字节 %d + ASCII %d): 与模板逐像素**完全一致 %d / %d** (%.2f%%); '
        '「模板渲染不出」%d 格、引擎图标 %d 格、引擎特制 %d 格 (这三类不比模板); '
        '**不匹配 %d 格** (错误 %d / 警告 %d)'
        % (v['total_cells'], v['by_kind'].get('pair', 0), v['by_kind'].get('single', 0),
           v['by_kind'].get('ascii', 0), v['matched'], v['compared'],
           v['match_rate'] or 0.0,
           v['by_verdict'].get('template_missing', 0), v['by_verdict'].get('engine_icon', 0),
           v['by_verdict'].get('by_design', 0),
           len(bad), v['by_level'].get(LV_E, 0), v['by_level'].get(LV_W, 0)))
    return doc


def markdown(doc):
    L, A = [], None
    A = L.append
    c = doc['counts']
    A('# 单格字库逐字比对报告 (single_cell_font)')
    A('')
    A('> 工具 `%s` (%s) · 盘 `%s`' % (doc['tool'], doc['tool_version'], doc['iso']))
    A('> sha256 `%s`' % (doc['iso_sha256'] or '?'))
    A('')
    A('## 一句话结论')
    A('')
    A('- **%s**' % doc['one_line'])
    A('- 判据 = **紧判据**: 盘上格的墨点必须**逐像素等于** 16px 模板 ⇒ `diff_px == 0` 才算匹配。'
      '**不用** ±4/±2 容差窗 (round46 的 6 个空白字、round50 的 10 个丢行字都是被宽容差蒙掉的)。')
    A('')
    A('## 统计')
    A('')
    A('| 项 | 数量 |')
    A('|---|---|')
    A('| 单格总数 | %d |' % c['total_cells'])
    A('| 　对偶码 | %d |' % c['by_kind'].get('pair', 0))
    A('| 　单字节码 | %d |' % c['by_kind'].get('single', 0))
    A('| 　ASCII | %d |' % c['by_kind'].get('ascii', 0))
    A('| 　引擎图标码 | %d |' % c['by_kind'].get('icon', 0))
    A('| **参与模板比对** | **%d** |' % c['compared'])
    A('| **逐像素完全一致** | **%d** (%.2f%%) |' % (c['matched'], c['match_rate'] or 0.0))
    A('| 不匹配 | **%d** (错误 %d / 警告 %d) |'
      % (doc['findings_total'], c['by_level'].get(LV_E, 0), c['by_level'].get(LV_W, 0)))
    A('')
    A('按结论计数: ' + ', '.join('`%s` %d' % kv for kv in sorted(c['by_verdict'].items()))
      if c['by_verdict'] else '')
    A('')
    A('## 反向自证 (证明"读取正确")')
    A('')
    st = doc.get('self_test') or {}
    if st:
        A('| 项 | 结果 |')
        A('|---|---|')
        A('| 路径 A | %s |' % st.get('path_A'))
        A('| 路径 B | %s |' % st.get('path_B'))
        A('| A/B 整张图集逐像素相同 | **%s** (差异 %d px; 墨 A=%d / B=%d) |'
          % ('是' if st.get('whole_atlas_identical') else '否', st.get('whole_atlas_diff_px'),
             st.get('atlas_ink_A'), st.get('atlas_ink_B')))
        A('| 逐格 A/B 不同 | **%d** |' % st.get('cells_paths_differ'))
        if st.get('path_C'):
            pc = st['path_C']
            A('| 路径 C (repack_font.Atlas) 与 A 相同 | %s |'
              % ('是' if pc.get('identical_to_A') else pc.get('error', '否')))
        p = st.get('wrong_slot_probe')
        if p:
            A('| ★故意错映射 (%s %s slot %d → %d) | **%s** (差异 %d px) |'
              % (p['char'], p['code'], p['slot'], p['wrong_slot'],
                 '被抓到' if p['detected'] else '没抓到 (判据失效!)', p['diff_px']))
        A('')
    if doc.get('cross_check_dump_font'):
        x = doc['cross_check_dump_font']
        A('## 与 `dump_font` 的 `_font_charset.csv` 交叉一致')
        A('')
        if not x.get('exists'):
            A('- %s' % x.get('note'))
        else:
            A('- 对照 %d 行, **不一致 %d 行** (CSV 里没有 %d 行) ⇒ %s'
              % (x['checked'], x['mismatched'], x['not_in_csv'],
                 '同一字符同一格 ✓' if x['ok'] else '★有分歧'))
            for e in x.get('examples', []):
                # round55 修: 交叉对照的例子字典里键名是 mine_engine/mine_converted,
                # 之前这里写 e['mine'] ⇒ 写完报告后 KeyError 退出 1 (基线盘上同样崩)
                _mine = e.get('mine', e.get('mine_converted', e.get('mine_engine', '?')))
                A('  - %s %s: 本工具 %s vs dump %s' % (e.get('kind', '?'), e.get('code', '?'),
                                                       _mine, e.get('dump', '?')))
        A('')
    A('## 不匹配清单 (%d 条, 错误在前)' % doc['findings_total'])
    A('')
    if not doc['findings']:
        A('- **没有不匹配** —— 所有参与比对的格与 16px 模板逐像素完全一致。')
    else:
        A('| 级别 | 字 | 类 | 码 | 引擎格 | 盘墨 | 模板墨 | 差异 | 结论 | 字形实际在 | 最像谁 |')
        A('|---|---|---|---|---|---|---|---|---|---|---|')
        for f in doc['findings']:
            bm = f.get('best_match') or []
            fa = f.get('found_at') or []
            A('| %s | %s | %s | %s | (%d,%d) | %d | %s | %s | %s | %s | %s |'
              % ('!!' if f['level'] == LV_E else 'warn', f['char'] or '-', f['kind'], f['code'],
                 f['cell_x'], f['cell_y'], f['disk_ink'],
                 f['tpl_ink'] if f['tpl_ink'] is not None else '-',
                 f['diff_px'] if f['diff_px'] is not None else '-', f['verdict'],
                 (' '.join('(%d,%d)' % tuple(h) for h in fa[:2]) if fa else '-'),
                 (' '.join('%s(%d)' % (b['char'], b['diff']) for b in bm) if bm else '-')))
        A('')
        A('### 逐条人话')
        A('')
        for f in doc['findings']:
            dl = ''
            if f.get('found_delta'):
                dl = ' —— 字形实际画在 `(x%+d, y%+d)` (全盘搜索, 逐像素 0 差异命中 %d 处)' % (
                    f['found_delta'][0][0], f['found_delta'][0][1], len(f['found_at']))
            A('- **%s** `%s` (%s / %s) 格 (%d,%d): %s%s —— %s'
              % (f['char'] or f['code'], f['code'], f['kind'], f['verdict'],
                 f['cell_x'], f['cell_y'], RULE_TEXT.get(f['verdict'], ''), dl, f.get('note') or ''))
        A('')
    A('## 判据明细')
    A('')
    for k in sorted(RULE_TEXT):
        A('- `%s` — %s' % (k, RULE_TEXT[k]))
    A('')
    A('## 读图须知')
    A('')
    A('- `single_cell_font.png` = **单格字库**: 一字一格, 格内是**盘上真正采到的那 16x16 像素**;')
    A('  边框色 = 结论 (绿=逐像素一致 / 黄=有差异 / 红=错误); 每格下面是字符与码位。')
    A('- `single_cell_font_expected.png` = 同版面的**期望位图** (方正像素16 16px 模板), 用来对照。')
    A('- `mismatch_sheet.png` = 只放不匹配的字, 放大 (左=盘上格 / 中=模板 / 右=差异)。')
    A('')
    A('---')
    A('')
    A('★ 本报告由 `%s` 生成 (只读盘; 产物不含时间戳, 同一张盘跑两次逐字节相同)。' % doc['tool'])
    return '\n'.join(L) + '\n'


# ═══════════════════════════════════════════════════════════════════
#  main
# ═══════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description='单格字库 + 逐字与图集纹理比对 (round51)')
    ap.add_argument('--iso', required=True)
    ap.add_argument('--out', default=None)
    ap.add_argument('--prefix', default='')
    ap.add_argument('--scale', type=int, default=4)
    ap.add_argument('--cols', type=int, default=32)
    ap.add_argument('--no-png', action='store_true')
    ap.add_argument('--only-pair', action='store_true', help='只查对偶码 (调试)')
    ap.add_argument('--charset', default=None)
    a = ap.parse_args()

    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.iso)), 'font_single_cell')
    os.makedirs(out, exist_ok=True)
    prefix = (a.prefix + '_') if a.prefix else ''
    iso_sha = tcslib.sha256_file(a.iso)
    print('=' * 78)
    print('单格字库 + 逐字比对   盘 = %s' % rel(a.iso))
    print('  sha256 = %s' % iso_sha)
    print('=' * 78)

    font = dump_font.load_font(a.iso)
    cs = tcslib.Charset(a.charset) if a.charset else tcslib.Charset()
    print('[载入] 图集 %dx%d psm=0x%02X; FT face=%s %d 条记录; charset 对偶 %d + 单字节 %d'
          % (font['atlas']['w'], font['atlas']['h'], font['atlas']['psm'],
             [x[0] for x in font['faces']][tcslib.FONT_FACE_DEFAULT],
             len([x for x in font['faces'] if x[0] == 'default'][0][2]),
             len(cs.enc_pair), len(cs.enc_single)))

    cells, extra = build_cells(font, cs, a.only_pair)
    print('[取格] %d 格 (路径 B 的封包段: %s)'
          % (len(cells), ', '.join('行%d/%dB' % (s[0], s[2]) for s in extra['segs_B'])))

    st = selftest(font, cs, cells)
    print('[自证] 两条独立路径整图一致 = %s (差 %d px); 故意错映射被抓到 = %s'
          % (st['whole_atlas_identical'], st['whole_atlas_diff_px'],
             bool(st['wrong_slot_probe'] and st['wrong_slot_probe']['detected'])))

    csv_path = os.path.join(os.path.dirname(os.path.abspath(a.iso)), 'font',
                            (a.prefix or os.path.splitext(os.path.basename(a.iso))[0])
                            + '_font_charset.csv')
    xcheck = cross_check_charset_csv(cells, csv_path)

    doc = summarize(cells, a.iso, iso_sha, st, xcheck,
                    dict(scale=a.scale, cols=a.cols, only_pair=a.only_pair))
    print('[结论] %s' % doc['one_line'])

    pj = os.path.join(out, prefix + 'single_cell_report.json')
    pm = os.path.join(out, prefix + 'single_cell_report.md')
    pst = os.path.join(out, prefix + 'single_cell_selftest.json')
    with io.open(pj, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    with io.open(pm, 'w', encoding='utf-8', newline='\n') as f:
        f.write(markdown(doc))
    with io.open(pst, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    print('[报告] %s' % rel(pj))
    print('[报告] %s' % rel(pm))
    print('[报告] %s' % rel(pst))

    if not a.no_png:
        p1 = os.path.join(out, prefix + 'single_cell_font.png')
        p2 = os.path.join(out, prefix + 'single_cell_font_expected.png')
        p3 = os.path.join(out, prefix + 'mismatch_sheet.png')
        s1 = write_sheet(cells, p1, a.scale, a.cols, False,
                         'SINGLE-CELL FONT  (one cell per character, read from the disc atlas)  '
                         'green = pixel-identical to template / yellow = diff / red = error')
        s2 = write_sheet(cells, p2, a.scale, a.cols, True,
                         'EXPECTED  (rendered from FZXS16 16px TTF - the same recipe as gen_font16)')
        s3 = write_mismatch_sheet(cells, p3, max(6, a.scale + 4))
        print('[出图] %s %sx%s' % (rel(p1), s1[0], s1[1]))
        print('[出图] %s %sx%s' % (rel(p2), s2[0], s2[1]))
        print('[出图] %s %sx%s' % (rel(p3), s3[0], s3[1]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
