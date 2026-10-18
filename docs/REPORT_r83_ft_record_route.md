# REPORT_r83_ft_record_route.md — 「h=512 不变 · 容器不变」的 FT 记录/网格扩容盘 GR_ZH123

> 分支 `round73/font-decompile` ｜ **未切分支、未 commit、未 merge**
> 只读：所有历史 ISO、`third_party/orig/**`、`%LOCALAPPDATA%\PCSX2\**`、`work/temp/NEW_Mem/**`
> 只写：本报告 + `docs/{FONTRES_STRUCTURE_r83,CONTAINER_INVENTORY_r83}.md` +
> `work/builds/GR_ZH98/temp/r83/**` + `work/builds/GR_ZH123/**` + `work/tools/zx_r83_*.py`
> + `tools/font_pipeline/data/charset_compiled_zh16.json`（**受保护路径，改动见 §8**）

---

## 0. 一句话结论

**① 新盘 `work/builds/GR_ZH123/GR_ZH123.iso` 实机跑通**：6000 帧裸跑 **191 张截图**
（基线也是 191）、needle `newfontrevisedrs` **2880 次命中**、
**191/191 张截图与基线逐字节完全相同**；再用 `nav_hook` **到达「开发访谈 1」文字界面**
（344 s，6 张截图），实读画面上 **汉字正文 + 标点 + ASCII + 底栏「△ 返回」全部正常**，
其中 **△ 就是本轮新写的槽 1504 字形** ⇒ **新码位/新字形实机可见** ✓
**② 全部结构尺寸一个字节都没动**：`h` 512、`px_size` 0x40010、容器 8 段 262,160 B、
COMMON.PAK 400,659 B、FONT.RES 槽 4421 / 展开 5942 / nrec 224,224,96、
MENU.IMG 682 条 off、ISO 尺寸 —— **全部与基线相同**；ELF 只改了 4 个 `sltiu` 立即数。
**③ 净增 232 个新字**（◀ 不是任务书期望的 364）：新增对偶码槽 1504..1735。
**④ ★ 任务书的两条前提被数据否证**（详见 §6）：
  · 「容器里约 196 KB 是别的纹理，可以腾」——**算错了 4 倍**（1024×512@4bpp = 262,144 B，
    容器就是这一张纹理，没有第二块）；
  · 「图集高度 h 是唯一卡点（h≤512 硬上限）」——**没有任何一张对照盘做到"只改 h、容器不动"**，
    h 与"容器变大"在全部失败盘上同时变化。GR_ZH123 **容器完全不动、只有 gate 变了** ⇒ 跑通，
    支持「黑屏主因是容器/px_size 变大」这一解释。

---

## 1. 交付物索引

| 类型 | 路径 |
|---|---|
| ★ 成品盘（实机跑通） | `work/builds/GR_ZH123/GR_ZH123.iso`（1,648,164,864 B，与基线**同尺寸**）|
| 文档① **FONT.RES 权威结构**（反汇编实证） | `docs/FONTRES_STRUCTURE_r83.md` = `work/builds/GR_ZH98/temp/r83/R83_A_FONTRES_STRUCTURE.md` |
| 文档② **容器 10 区域清单 + 容量账** | `docs/CONTAINER_INVENTORY_r83.md` = `work/builds/GR_ZH98/temp/r83/R83_B_CONTAINER_INVENTORY.md` |
| 补丁日志（八条断言原文） | `work/builds/GR_ZH98/temp/r83/{patch_r83_report.json, make_build_r83b.log}` |
| 逐字节差异表 | `work/builds/GR_ZH98/temp/r83/diff_zh123.txt` |
| 实机证据（6000 帧） | `work/builds/GR_ZH123/temp/dump_r83b/`（191 png + emulog + needle dump）|
| ★ 实机证据（文字界面） | `work/builds/GR_ZH123/temp/dump_r83nav/`（6 png + drawlog + hook_sequence.txt）|
| 第一次实机（旧窗口口径，也跑通） | `work/builds/GR_ZH98/temp/r83/dump_first/` |
| 字形/字库 dump | `work/builds/GR_ZH123/temp/fontdump/**` |
| 本轮工具 | `work/tools/zx_r83_{struct,free,budget,plan,charset,patch}.py` |
| 反汇编转储 | `work/builds/GR_ZH98/temp/r83/{cave_A,cave_B,glyph_uv_fn,addoneword,drawstring,readres,struct,free,budget,plan}.txt` |

---

## 2. 做了什么（逐条 + 证据）

| # | 动作 | 证据 |
|---|---|---|
| ① | **不动 h / px_size / 容器段数 / PAK / MENU** | `[A6][A7][A8]`：PAK 长 400,659 不变；名字区 + 4096 槽哈希表逐字节不变；ISO 尺寸不变 |
| ② | ELF gate `sltiu …,0xB1` → `…,0xB4`（4 站点）| 0x416EE8 / 0x417160 / 0x41751C / 0x5656A4 逐站点回读 ✓（`[elf]`、`[A7]`）|
| ③ | 新增对偶码槽 **1504..1735**（232 个）：行 24 尾 col 16..61 + 行 25/26/27 全行 | `[lay]` 新槽 y 434..498 |
| ④ | 两条活带让位：EN (452,468)×92 个唯一矩形 + KB (482,498)×28 个 | `[band]` 120 个唯一矩形贪心重排；搬完剩余自由 39,208 texel = 153.2 格 |
| ⑤ | FONT.RES **只改记录矩形字段**，展开长度/记录数不变 | `[A5]` 展开仍 5942 B；差异 2,450 字节**全在**目标字段集合内 |
| ⑥ | 232 个字形画进新格（方正像素16 231 个 + simhei 兜底 1 个「嘚」）| `[A4]` 逐 texel == 模板 ✓ |
| ⑦ | 键/练/用 从旧单字节记录的采样窗**原样抠**；△ 用手绘 16×16 三角 | `[A3]` + `dump_font` 几何体检：键/练/用 已无错（唯余 △ 与模板不同，见 §7）|
| ⑧ | charset 收敛到 1504 现役 + 232 新（**删掉 slot 1736..1871 的登记**）| `zx_r83_charset.py`；`selfcheck` 抽查 232 条新 pair 全部有字形 ✓ |
| ⑨ | 文本注入（把 `{{BTN:E0B1}}` 换成字符 `△` —— gate 抬到 0xB4 后 0xB1 已是 lead）| 注入器 exit=0；`已按 CSV 修改 32 条正文`；`inject_text_csv --check-only` exit=0 |

**★ 本轮改对了上一轮会踩的一处口径：记录矩形 = 采样矩形**
```
任务书/工具里的 tcslib.GLYPH_DU/DV = (4, 2) 一直当"记录矩形 → 采样窗"的几何偏置用。
本轮用盘上自己的像素判它:
  EN 带 (ASCII, 8px 步进) y=453..467 逐 texel 描点:
    第 1 格 '!' 的竖杠落在 x=3      ⇒ 属于窗 [0,8)   (偏移 3)
    第 2 格 '"' 落在 x=10,11,13,14  ⇒ 属于窗 [8,16)  (偏移 2,3,5,6)
  若窗真是 (u0+4, v0+2), 第 1 格的 x=3 落在窗内偏移 −1 ⇒ **不可能**
⇒ 采样窗 = (u0,v0)-(u1,v1), **没有 +4/+2**。GLYPH_DU/DV 是"字形体检容差", 不是几何。
  (第一次实机用的就是旧口径 ⇒ 120 条带字形整体错 4/2 px; 修正后 dump_font 的
   "截断"错误从 2 个降到 1 个 —— 只剩 △ 那条手绘差异。)
  ★ 没有改 tcslib（受保护路径）, 只在 `zx_r83_patch.py` 里用 `RW_DU=RW_DV=0` 并写明理由。
```

---

## 3. 八条硬断言（写盘后**从盘上回读**再验）

| # | 断言 | 结果 | 数字 |
|---|---|---|---|
| A1 | 现役 **1504** 个对偶格逐 texel 不变 | ✅ | 不同 0 个 |
| A2 | 留在原位的记录采样窗逐 texel 不变 | ✅ | 88 个唯一矩形 |
| A3 | 搬家的 120 条带矩形「内容等价」（新位置位图 == 旧位置位图）| ✅ | 120/120 |
| A4 | 232 个新字格逐 texel == 16px 模板 | ✅ | 232/232（键/练/用 为原样搬运，单独核对）|
| A5 | FONT.RES 展开仍 5942 B、nrec 仍 224/224/96、差异字节 ⊆ 目标字段 | ✅ | 差异 2,450 B |
| A6 | COMMON.PAK 长度不变 + 回读一致 | ✅ | 400,659 == 400,659 |
| A7 | ELF gate 4/4 + 名字区/4096 槽哈希表逐字节不变 | ✅ | 4/4 |
| A8 | ISO 尺寸与基线相同 | ✅ | 1,648,164,864 B |

---

## 4. P3 离线判据（成品盘自身）

```
tools/text_csv/inject_text_csv.py --csv r83/text_in --src GR_ZH123.iso --check-only
   ⇒ exit 0 ; 只余 ascii_no_glyph 一类**不阻断**告警（现役盘同样）
tools/iso_build/dump_font.py --iso GR_ZH123.iso
   ⇒ 1024×512 psm=0x14, 墨 130,032 / 524,288 texel (24.80%)
   ⇒ 记录 544 条（有墨 544 / 无墨 0）
   ⇒ 字符 1940 个 — **有字形 1939 / 缺字形 0**
   ⇒ 自查: 引擎格位公式 OK ✓ 1880/1880 slot 逐个对 tcslib 口径 ; 对偶字有字形 1736/1736 ✓
   ⇒ 字形几何体检: 错误 1（只有 △ 手绘三角与模板不同）/ 警告 2 ; 截断 1 / 空白 0 / 越窗 0
work/tools/zx_selfcheck.py --iso GR_ZH123.iso
   ⇒ exit 0 ; 「新码位抽查」232 条新 pair **盘上无字形 = 0**
```

---

## 5. ★ 实机（与基线同命令同输入：裸跑 6000 帧）

```
third_party\emu\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe -grdumpdir <d> -grmaxframes 6000 \
   -grsnap 30 -grinput tools\capture\nav_menu_only.txt -logfile <d>\emulog.txt -- <iso>
```

| 盘 | 截图 | needle `newfontrevisedrs` | 与基线逐字节比较 |
|---|---|---|---|
| `GR_ZH113b`（基线）| 191 | 2,873 | — |
| `GR_ZH121`（上一轮成品）| **0** ✗ | **0** ✗ | 黑屏 |
| **`GR_ZH123`（本轮第 1 次，旧窗口口径）** | **191** ✓ | **2,880** ✓ | — |
| **`GR_ZH123`（本轮第 2 次，修正窗口后）** | **191** ✓ | **2,880** ✓ | **191/191 逐字节相同** ✓ |

```
⇒ 判据全过: 截图数正常(191) 且 needle > 0(2880)。纹理上传了、字体名进了内存、UI 走到了。
⇒ 191/191 逐字节相同 ⇒ 本次结构改动对这条航程**完全透明**（新增字不在基线文本里；
   被搬走的 120 条带字形在新位置渲染完全一致 ⇒ 也顺带验证了"搬运内容等价"）。
```

### 5.2 ★ 文字界面（真实汉字上屏）

```
python tools\capture\nav_hook.py GR_ZH123 --iso work\builds\GR_ZH123\GR_ZH123.iso --tag r83nav
  ⇒ 结果: ★ 成功到达 — 到达「开发访谈 1」 ; 耗时 344 s ; 截图 6 张
  ⇒ drawlog: 518,205 行, 其中可解码文本 104,042 行
     站点命中 {'21AD10'(CharWidth): 392580, '21AC00': 41876, '219A70'(DrawString): 31083,
               '219EB0': 31083, '5172E0'(SetTexture): 12592, '21C4C0': 3597, ...}
```

截图 `work/builds/GR_ZH123/temp/dump_r83nav/r83nav_page.png`（另 5 张 `r83nav_pg*.png`）实读：

| 看到的内容 | 说明 |
|---|---|
| 标题「访谈」 · 黄条「开发访谈 1」| 全中文正常渲染 |
| 正文八行：「开发手记: 第一辑 / 制作人: 达伦·丘基图斯 / 日志一: / 对《幽灵行动》团队而言, 这个月 / 令人无比振奋。/ 我们已完成Alpha阶段, / 正开足马力向Beta版本冲刺。/ 在此期间, 我亲眼见证了游戏 / 在团队的精雕细琢下日渐完善。」| **对偶字(槽 0..1503) 全部正常**；`《》·:` 等标点正常 |
| 正文里的 `Alpha` / `Beta` 与右下角 `Tom Clancy's GHOST RECON` | ★ **ASCII 全部正常 ⇒ 被搬走 120 条带的 EN 带在新位置渲染正确**（这是本轮唯一"动了旧像素"的部分，实机已闭环）|
| 底栏「**△** 返回」「**✕** 查看」| ★★ **△ 就是本轮新写的字形**（槽 1504，`zx_r83_patch.triangle16()` 手绘 16×16 空心三角，墨 69）⇒ **新码位/新字形在实机上真的可见** ✓ · ✕ 仍是引擎自带的 0xB5 图标码（gate 0xB4 < 0xB5，未受影响）|

⇒ ⇒ **P2 判据达成**：新字形（△，槽 1504）与"搬过家的记录带字形"都在实机画面上被肉眼确认。
（228 个"全新汉字"没有进基线文本，所以这一轮不可能出现在画面上；它们由 §4 的
  `dump_font 有字形 1939 / 缺字形 0` + `selfcheck 232 条新 pair 全部有字形` + 逐 texel == 模板 三条离线判据保证。）

---

## 6. 被本轮**否证/更正**的前提（避免后人重走）

| # | 原说法 | 本轮结论 | 证据 |
|---|---|---|---|
| ✗1 | 「图集只占 65,536 B（1024×512@4bpp），容器里约 196 KB 是别的纹理，可压缩/搬移/冻结」| **算错 4 倍**。4bpp ⇒ 262,144 B；容器 262,160 = 262,144 + 16 B tag；8×48 + 261,760 = 262,144 分毫不差。**没有别的纹理** | `R83_B` §1 |
| ✗2 | 「卡点唯一变量 = h；引擎 h ≤ 512 硬上限」| **证据不足**：H640/H640B/H1024/GR_ZH121 **同时**改了 `h` 和 `px_size`/容器段数；**没有任何一张盘只改 h**。本轮"容器一个字节不动"，跑通 ⇒ 支持"黑屏主因是容器/px_size 变大" | `R83_A` §3；§5 结果表 |
| ✗3 | 「`diff_font_record_fields.py` 证明记录头只有 h 变了」| 该工具比的是记录 +0x000..+0x05F，其中 **+0x028 起是调色板数据不是字段**，而 **`px_size` 在 +0x438，根本没被比** | `R83_A` §3 |
| ✗4 | 「记录矩形 → 采样窗有 +4/+2 偏置（`GLYPH_DU/DV`）」| **不成立**。记录分支把 (u0,v0,u1,v1) 原样当 UV；`+2` 只写在**网格公式**里。盘上 EN 带逐 texel 描点直接否证 | `R83_A` §2.4/§2.5；§2 ★ |
| ✗5 | 「记录分支恒假 ⇒ 不可达 ⇒ 必须改代码」| **判据只取决于 nrec 这个数据字段**（`nrec = fld[4]×fld[5]`，`__nwa(nrec*10+0x10)` 动态分配）。本轮**没有为记录改任何代码**（gate 只是为了多拿 lead，与记录分支无关） | `R83_A` §2.2/§2.5 |
| ✗6 | 「记录索引被 `&0xFF` 截断 ⇒ 记录上限 256」| 该 `andi` 在 0x21AE1C，而 cave 用 `j 0x21AE20` **跳过它**；索引无掩码 | `R83_A` §2.5 |
| ✓ | 「单字节码走 FT 记录表（idx = code−0x20）」| **成立且已被现役盘大量使用**：charset 的 `codes` 里 107 个高频字就是走这条路的 | `R83_A` §2.2 |

---

## 7. 未完成项（如实，含原因）

| 项 | 状态 | 原因 / 下一步 |
|---|---|---|
| **364 个缺字全上盘** | ⛔ **只做到 232 个**（63.7%）| **容量不够，不是实现不够**。h=512 + 现役布局下：对偶槽可寻址 **1736**（28 行 × 62 列，行 28 的 y=498..513 越界），现役占 1504 ⇒ **只剩 232 槽**；单字节码现役已用满 0x80..0xA0 + 0xB6..0xFF，空闲只剩 `0x7F / 0xB2 / 0xB3 / 0xB4`。gate 再抬也不涨（瓶颈是行数不是 lead 数）。 |
| **第 233 个（单字节码 `0x7F`）** | ⚠ 未开 | 只多 1 个，性价比低；且要动 `codes` 表。留作收尾。 |
| **到 364 的完整方案** | ✅ 已定量 | 改 cave 的 `addiu $t5,$t5,3` → `+0`（gap 3 行→0 行）⇒ 网格 **31 行 × 62 = 1922** 槽；再把行 12..24 的 744 个现役字形整体上移 48 px 重铺、记录带让位。像素账：1868×256 + ASCII 95×128 + 单字节 107×256 = **517,760 ≤ 524,288（只余 6,528 = 2.5%）**。**余量太薄 + 全盘重铺 ⇒ 必须单独一轮做**。 |
| **P2（新字上屏对照）** | ✅ **拿到** | `tools/capture/nav_hook.py GR_ZH123 --iso … --tag r83nav` ⇒ **成功到达「开发访谈 1」**（344 s，6 张截图）。见 §5.2。 |
| **△ 的观感** | ⚠ 已知偏差 | 手绘 16×16 三角（墨 69）。`dump_font` 几何体检把它列为唯一 1 个"错误"（与模板不同的字形）。引擎原图标在 `pda_counterparts`（20×20 彩色、硬编码 UV (25,198)-(45,218)），无法直接当 1-bit 字形。 |
| **GR.IMG 侧** | 未做（按任务书"不要动"）| — |

---

## 8. 受保护路径改动（先说明再改）

```
① tools/font_pipeline/data/charset_compiled_zh16.json   ★ 已改
   pair_of 1872 → **1736**（1504 现役 + △/键/练/用 + 228 缺字）
   删除了 slot 1736..1871 的 136 条登记（本盘没有这些格）
   新增 `_expand_r83` 段记录本轮口径
   备份 = work/builds/GR_ZH98/temp/r83/charset_before_r83.json
   一键还原: python work/tools/zx_charset.py --revert   （回到 r82 的 1872 态）
             cp work/builds/GR_ZH98/temp/r83/charset_before_r83.json <CHARSET>

② 未改：tools/text_csv/tcslib.py、font_compact.py、make_build.py、tools/font_pipeline/data/* 其它文件
   ★ 特别是 tcslib.py 的 LEAD_HI 仍是上一轮留下的 0xB5，与本盘的 0xB4 **不一致**：
     本盘 charset 的 232 个新 pair 用 lead 0xA1..0xB3（slot ≤ 1735），
     tcslib 只做区间校验（0xA1..0xB4 都合法），不影响注入正确性（`inject_text_csv --check-only` exit=0 ✓）。
     下一轮统一口径时把 LEAD_HI 改成 0xB4 或继续用 0xB5 都行。
```

---

## 9. 复现命令

```powershell
# 只读侦察（全部可重跑）
python work\tools\zx_r83_struct.py      # FONT.RES 权威结构 + 容器区域清单 → r83/struct.txt
python work\tools\zx_r83_free.py        # 原子图集占用/自由度         → r83/free.txt
python work\tools\zx_r83_budget.py      # h=512 容量预算（4 个场景）  → r83/budget.txt
python work\tools\zx_r83_plan.py        # 目标布局 + 带搬家规划       → r83/plan.txt
python work\tools\cave_dis.py work\builds\GR_ZH98\temp\r72\SLUS_206.13.elf diso 0x416ED0 0x417080

# 补丁（dry-run 会把八条断言全跑一遍，不写盘）
python work\tools\zx_r83_patch.py work\builds\GR_ZH113b\GR_ZH113b.iso --dry-run

# charset 收敛（先 dry-run）
python work\tools\zx_r83_charset.py --dry-run
python work\tools\zx_r83_charset.py --apply

# 成品盘（目录必须不存在）
python tools\iso_build\make_build.py GR_ZH123 --from work\builds\GR_ZH113b `
       --patch work\tools\zx_r83_patch.py --no-font-compact --no-text-snapshot `
       --no-font-dump --inject-csv work\builds\GR_ZH98\temp\r83\text_in

# P3 离线判据
python tools\text_csv\inject_text_csv.py --csv work\builds\GR_ZH98\temp\r83\text_in `
       --src work\builds\GR_ZH123\GR_ZH123.iso --check-only
python tools\iso_build\dump_font.py --iso work\builds\GR_ZH123\GR_ZH123.iso --out <dir>
python work\tools\zx_selfcheck.py --iso work\builds\GR_ZH123\GR_ZH123.iso
python work\tools\zx_diff_iso.py work\builds\GR_ZH113b\GR_ZH113b.iso work\builds\GR_ZH123\GR_ZH123.iso

# 实机（先确认没有别人的实例！绝不抢/杀）
third_party\emu\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe -grdumpdir <d> -grmaxframes 6000 `
   -grsnap 30 -grinput tools\capture\nav_menu_only.txt -logfile <d>\emulog.txt -- <iso>
python work\tools\zx_cmp_shots.py work\builds\GR_ZH113b\temp\dump_p1base <d>
python tools\capture\nav_hook.py GR_ZH123 --iso work\builds\GR_ZH123\GR_ZH123.iso --tag r83nav
```

---

## 10. 给下一轮的三条（按性价比）

1. **补第 233 个（单字节码 0x7F）+ 把 nav_hook 跑完拿到"新字上屏"截图** —— 半天内可完成，
   把"实机可见"这条判据闭环。
2. **做 364**：`addiu $t5,$t5,3` → `+0`（cave 1 个立即数）+ 全盘图集重铺（744 个现役字形上移 48 px、
   120 条带记录再让位）。**先做 dry-run 的像素账与断言，再实机**。余量只有 2.5%，建议同时准备
   "只上 300 个"的降级档。
3. **顺手更正三处工具口径**（都已被本轮数据判错，建议一并修）：
   · `tcslib.GLYPH_DU/DV` 注释改成"体检容差"（几何偏置是 0）；
   · `work/tools/diff_font_record_fields.py` 的 96 B 窗口 → 扩到覆盖 `+0x438 (px_size)`，
     并删掉把调色板当字段的读法；
   · `docs/REPORT_zero_missing_glyph_build2.md` §5.2 与 `LEAD_HARD_LIMIT_h512.md` 的
     "唯一变量 = h" 结论应标注为**证据不足**（本轮 §6 已给反证）。
