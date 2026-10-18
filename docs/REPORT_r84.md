# REPORT_r84 — △ 修复 + W=2048 单变量实验 + 上限裁定（round84，第 2 轮接力）

> 分支 `round73/font-decompile` ｜ **未切分支、未 commit、未 merge**
> 只读：所有历史 ISO、`third_party/orig/**`、`%LOCALAPPDATA%\PCSX2\**`、`work/temp/NEW_Mem/**`
> 只写：本报告 + `docs/RISK_BUDGET_r84.md` + `docs/REPORT_W2048_r84.md`
> + `work/tools/zx_r84_*.py` + `work/builds/GR_ZH98/temp/r84/**`
> + `work/builds/GR_ZH124/**` + `work/builds/GR_TEST_W2048b/**`

---

## 0. 一句话结论

**① 风险预算（任务 1）已交**：`docs/RISK_BUDGET_r84.md`
⇒ **364 个新字算术上不可达**（缺口 10.3%），并被 **Lead 采纳**（`LEAD_RULING_r84.md` §一）。

**② △ 修复（任务 2）已完成并实机验证** —— 新盘 `work/builds/GR_ZH124/GR_ZH124.iso`
```
dump_font 字形几何体检: 错误 0（上一轮 1）· 截断 0 · 空白 0 · 越窗 0
实机 6000 帧: 191 截图（基线 191）· needle newfontrevisedrs 2873 · TLB 0
              ★ 191/191 张与基线 GR_ZH113b 逐字节完全相同
nav_hook: ★ 成功到达「开发访谈 1」→ 底栏「△ 返回」实拍可见
```

**③ W=2048 单变量实验（Lead 裁定必做）已做 —— ★ 黑屏**
```
0 截图 · needle newfontrevisedrs 0 hits · 但游戏跑满 6000 帧（WPNRPK74 2930 hits）
⇒ ★「图集变大」整条路被引擎挡住（h 一个字节都没动，h 被彻底摘干净）
⇒ 详见 docs/REPORT_W2048_r84.md
```

**④ 上限的权威数字（本轮穷举更正）**：
```
全局最大 = 1,892 个对偶字形 ⇒ 本轮最多再加 **156 个新字**（需全盘重铺）
现役结构下 = **0 个**（图集已满到格子级）
```

---

## 1. 交付物索引

| 类型 | 路径 |
|---|---|
| ★ 成品盘（实机跑通） | `work/builds/GR_ZH124/GR_ZH124.iso`（1,648,164,864 B，与基线**同尺寸**）|
| | sha256 `762E613F12EF2296C4D290919E6CE2F294B91BB2E9A8B7E29AE3DB284926B3F9` |
| ★ 风险预算文档 | `docs/RISK_BUDGET_r84.md` |
| ★ W=2048 实验结论 | `docs/REPORT_W2048_r84.md` |
| W=2048 实验盘（黑屏） | `work/builds/GR_TEST_W2048b/GR_TEST_W2048b.iso`（1,648,398,336 B）|
| 本轮补丁工具 | `work/tools/zx_r84_{tri,w2048,layout,ceil_final,solve3,plan2,cells2,ceiling2}.py` |
| 上限穷举原文 | `work/builds/GR_ZH98/temp/r84/ceil_final.txt` |
| 容器/记录实测 | `work/builds/GR_ZH98/temp/r84/{cells2,ceiling2,layout,solve3,plan2}.txt` |
| 补丁报告 | `work/builds/GR_ZH98/temp/r84/{tri_report,w2048_report}.json` |
| ★ 实机证据（6000 帧） | `work/builds/GR_ZH124/temp/dump_r84/`（191 png + emulog）|
| ★ 实机证据（文字界面） | `work/builds/GR_ZH124/temp/dump_r84nav/`（6 png + drawlog）|
| 字库 dump + 体检 | `work/builds/GR_ZH124/temp/fontdump/` |
| 证据图 | `work/builds/GR_ZH98/temp/r84/{nav_full_page,nav_bottombar,slot1504_triangle}.png` |

---

## 2. △ 修复（Lead 批准，零风险）

### 2.1 做了什么

```
槽 1504（对偶码 0xB1 0xA1）的 16×16 像素:
   旧 = 上一轮 zx_r83_patch.triangle16() 手绘空心三角（墨 69）
   新 = render16('third_party/fonts/方正像素16.ttf', '△')（墨 35）

★ 容器里只改了 35 个字节（35 个墨点），差异范围 0x367D3..0x38406
```

### 2.2 八条硬断言（写盘后从盘上回读）

| # | 断言 | 结果 | 数字 |
|---|---|---|---|
| A1 | 槽 1504 回读逐 texel == 模板 | ✅ | 逐 texel |
| A2 | 容器差异字节只落在槽 1504 的 16×16 | ✅ | 35 B |
| A3 | 其余 **1735** 个现役格位逐 texel 不变 | ✅ | 不同 **0** 个 |
| A4 | PAK 长度 / 记录 psm·W·h·px_size 不变 | ✅ | 400,659 B / 0x14 / 1024 / 512 / 0x40010 |
| A5 | 回读 PAK vs 新容器差异 | ✅ | 0 B |
| A6 | 回读槽 1504 == 模板 | ✅ | ✅ |
| A7 | ELF 未改 + 名字区 + 4096 槽哈希表 + MENU 头逐字节不变 | ✅ | ✅ |
| A8 | ISO 尺寸与基线相同 | ✅ | 1,648,164,864 B |

**ISO 逐字节差异**（`zx_diff_iso.py`）：
```
差异区段 1 个, 合计 8,192 B (0.000497%)
  0x05ECBE000..0x05ECC0000  8192 B  [MENU.IMG +0x8F000]
  ⇒ 落在 ELF 4 个 gate 站点所在区段 = 0/4  ⇒ 一个 ELF 字节都没动 ✓
```

### 2.3 ★ `dump_font` 几何体检：错误 1 → **0**（任务判据达成）

```
轴 1504 的 16×16 = (256,434)
  旧 墨 69（手绘）→ dump_font 报"与 16px 模板不同"= 唯一 1 个错误
  新 墨 35（FZ16 模板）→ 逐 texel 命中模板
⇒ 图集容器: 引擎采样窗 2280 个（对偶 1736 + FT 记录 544）:
     错误 **0** / 警告 2 —— 截断(丢行) **0**, 空白 0, 越窗 0, 极稀 0
```

### 2.4 ★ 实机验证（同基线命令同输入，6000 帧）

```
third_party\emu\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe -grdumpdir <d> -grmaxframes 6000 `
   -grsnap 30 -grinput tools\capture\nav_menu_only.txt -logfile <d>\emulog.txt -- <iso>
```

| 盘 | 截图 | needle `newfontrevisedrs` | 与基线逐字节比较 |
|---|---|---|---|
| `GR_ZH113b`（基线）| 191 | 2,873 | — |
| **`GR_ZH124`（本轮成品）** | **191** ✓ | **2,873** ✓ | **191/191 逐字节完全相同** ✓ |

```
zx_cmp_shots.py work\builds\GR_ZH113b\temp\dump_p1base work\builds\GR_ZH124\temp\dump_r84
  ⇒ 同名可比 191 张 ; 仅 A 0 张 ; 仅 B 0 张
  ⇒ ★ 逐字节相同 191 / 191 ; 不同 0
⇒ 判据全过: 截图数正常(191) 且 needle > 0(2873)
⇒ 191/191 相同 ⇒ 本次改动对这条航程**完全透明**（△ 不在基线文本的画面里）
```

### 2.5 ★ 文字界面实拍（△ 可见）

```
python tools\capture\nav_hook.py GR_ZH124 --iso work\builds\GR_ZH124\GR_ZH124.iso --tag r84nav
  ⇒ 结果: ★ 成功到达 — 到达「开发访谈 1」 ; 耗时 345 s ; 截图 6 张
  ⇒ drawlog: 518,205 行, 其中可解码文本 104,042 行
```

截图实读（`work/builds/GR_ZH98/temp/r84/nav_full_page.png`）：

| 看到的内容 | 说明 |
|---|---|
| 标题「访谈」· 黄条「开发访谈 1」| 全中文正常 |
| 正文八行「开发手记: 第一辑 / 制作人: 达伦·丘基图斯 / 日志一: / 对《幽灵行动》团队而言…」| 对偶字正常；`《》·:` 标点正常 |
| `Alpha` / `Beta` / `Tom Clancy's GHOST RECON` | ASCII 正常 |
| **底栏「△ 返回」「✕ 查看」** | ★★ **△ 就是本轮的槽 1504 字形**（实拍见 `nav_bottombar.png`）|

### 2.6 离线判据

```
tools/iso_build/dump_font.py --iso GR_ZH124.iso
   ⇒ 1024×512 psm=0x14, 墨 130,203 / 524,288 texel (24.83%)
   ⇒ 记录 544 条（有墨 544 / 无墨 0）
   ⇒ 字符 1940 个 — 有字形 1939 / 缺字形 0
   ⇒ 自查: 引擎格位公式 OK ✓ 1880/1880 slot 逐个对 tcslib 口径
   ⇒ 字形几何体检: 错误 0 / 警告 2 ; 截断 0 / 空白 0 / 越窗 0   ★ 上一轮是"错误 1"
work/tools/zx_selfcheck.py --iso GR_ZH124.iso
   ⇒ 新 pair 232 条; '△' b1 a1 slot 1504 格 (256,434) 有字形=True 墨=35 ✓
   ⇒ 368 个新字里"盘上无字形"的 = 0
tools/text_csv/inject_text_csv.py --csv r83/text_in --src GR_ZH124.iso --check-only
   ⇒ exit 0 ; 只余 ascii_no_glyph 一类**不阻断**告警
```

---

## 3. W=2048 单变量实验 —— ★ 黑屏

> 完整报告：`docs/REPORT_W2048_r84.md`

| 判据 | 期望 | **实测** | |
|---|---|---|---|
| 截图数 | ~191 | **0** | ❌ |
| needle `newfontrevisedrs` | > 0 | **0 hits, 0 dumps** | ❌ |
| needle `WPNRPK74` | — | 2930 hits | 游戏在跑 |
| 帧数 | 6000 | 6000 | ✓ |
| TLB | 0 | 无异常 | ✓ |

**关键单变量**：`h` 一个字节都没动，只把**容器宽度** 1024→2048 ⇒ 黑屏。
⇒ **「图集变大被引擎挡住」被确证**，364 在 PS2 版里**不可达**。

---

## 4. ★ 上限裁定（本轮穷举更正了早前的估算）

### 4.1 早前的估算错了（如实交代）

| 版本 | 数字 | 为什么错 |
|---|---|---|
| `zx_r84_opt.py` §③ | 1612 | 判据写成「整块 y..y+h 全空的列」，把记录塞进已占位置还报成功 |
| 我的第一版 `plan.txt` | 1787 / 1922 / 1984 | 同上（`count_new` 把已占格位当空闲） |
| 任务书 r83 §7 | 「196 KB 是别的纹理」 | 4bpp 当 8bpp 算，差 4 倍（r83 已更正）|
| 任务书 r83 §7 | 「2.5% 余量」 | `107×256` 语义重复 ⇒ 实际 **−10.3%** |
| 任务书 r83 §7 | 「744 个字要搬」 | 实际 **992 个**（现役已用到 slot 1735）|

### 4.2 权威数字（`zx_r84_ceil_final.py`，穷举）

```
承认三条硬约束:
  ① 对偶 slot 是**一维**的 ⇒ 「前 n 个 slot」的位置唯一确定
  ② 采样窗必须落在 1024x512 内
  ③ 记录矩形（有墨 204 个）可自由平移，但**不可与格位重叠**

   ncol y0 gap | 最大对偶字形 n | 新字上限
    62   2  +3 |      1736      |    **0**   ← 现役结构，图集已满到格子级
    62   2  +2 |      1798      |     62
    62   2  +1 |      1860      |    124
    62   0  +0 |    **1892**    |   **156**  ← ★ 全局最大
    64   0  +0 |      1892      |    156     ← 加 ncol 不再增加（记录成瓶颈）
```

⇒ **「完全扩容不缺字」的诚实交代**：最多 **+156**，
即完整汉字覆盖 = 1,843 + 156 = **1,999 字**（仍差 208 字）。

### 4.3 为什么「现役结构下 = 0」这么反直觉？

```
现役占: 对偶 1,736 + 记录并集 40,664 texel
图集空余: 39,208 texel = 153.2 格位  ← 面积上"还有 153 格"
但实测: 这 153 格里**在 (16c, 16r) 晶格上一个 16×16 空位都没有**（= 0）
  因为它是「32px 右边缘条 × 32 行」+「每两行之间的 2px 缝」
⇒ 想加字必须先重排记录 ⇒ 没有"顺手塞"的余地
⇒ 上一轮能落 232 个字，正是把这类缝隙全用满换来的
```

---

## 5. 受保护路径

本轮 **未改动任何受保护路径**：
```
✗ tools/text_csv/*                （未改）
✗ tools/font_pipeline/data/*      （charset 仍是 r83 状态，未改）
✗ font_compact.py / make_build.py （未改）
✓ 只写: docs/ + work/tools/zx_r84_*.py + work/builds/{GR_ZH98/temp/r84,GR_ZH124,GR_TEST_W2048b}
```

---

## 6. 纪律核对

```
✓ 不动 h（W=2048 实验里 h 一个字节都没动）· 不动 4096 槽哈希表 · 不动名字区
✓ 每盘一个变量（W2048 盘只改 W/px_size/容器；GR_ZH124 只改 35 B 字形）
✓ exit=0 当假信号 —— 判据只看 emulog / 截图 / needle / 逐字节比对
✓ 没用 Select-Object -First N 截断命令输出
✓ 不 commit / 不切分支 / 不 merge
✓ 模拟器用完退出，无残留进程（已核 Get-Process）
✓ 实机前先确认没有别人的实例（每次跑前都查过，全程独占）
```

---

## 7. 未完成项（如实）

| 项 | 状态 | 原因 / 下一步 |
|---|---|---|
| **364 个新字全上盘** | ❌ **不可达** | ① h=512 图集面积差 10.3%；② 图集做大（W=2048）已实测黑屏。**Lead 已采纳** |
| **+156（全局上限）落盘** | ⚠ 未做 | Lead 裁定**不批准重铺**（性价比低）。方案保留在 `RISK_BUDGET_r84.md` §5 |
| 黑屏根因 | ⚠ 未做 | 需反汇编 `LoadingTexturePak` 一类加载路径；建议单开一轮 |
| 第二纹理/第二容器 | ⚠ 未做 | 同样要"容器变大" ⇒ W 实验已给出否定前提 |
