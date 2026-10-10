# 现役字库权威状态（盘内实测，2026-10-04；2026-10-05 补注）

> **2026-10-05 版本补注**：本文的 16px 网格配方在现役盘
> **`GR_ZH253` / `GR_ZH256` / `GR_ZH353`** 中**完全未变**（`NCOL=62`、`CW=CH=16`、
> `Y0=2`、`SKIP_ROW=12`、`SKIP_ROWS=3`、EN 带 `v=452/468`、纹理 1024×512 PSMT4）。
> `GR_ZH353` **新增**一条独立的 **12px 字形带 `v=480..495`**（实测原本全空），
> 供**任务名(关卡名)**专用，不影响 16px 任何路径 —— 见 README「12px 双字库方案」、
> `docs/PROGRESS.md §50`、`work/_dis/TWELVEPX_ROUND1..9.md`。
> 本文下文引用的 `GR_ZH84` 盘**已被删除**，但其中的实测结论对现役盘仍然成立。

> ⚠ 本文以 **GR_ZH84 盘内只读实测** 为准（脚本 `work/_dis/verify_grid*.py`，日志同名 `.log`）。
> 仓库里大量历史文档记录的是**旧版字库**（CH13 / 12px / 13px 网格 / 512×512 纹理），
> **与现役不符**；`gen_font16.py` 自己的 docstring 也已过时（与代码矛盾）。冲突时以本文为准。
>
> **初版勘误**：本文初版把 `gen_font16.py` 的 docstring 当作事实，导致 EN 带与纹理两处数字写错
> （382/397、512×1024）。以下为**实测修正后的正确值**，初版错误已全部替换。

## 一、现役字库 = 纯 16px（唯一现役版本）

网格配方来源：`tools/font_pipeline/gen_font16.py` 的**代码常量 L45-52**（NCOL/CW/CH/Y0/SKIP_*）。
⚠ **但 L50 的 `EN_A, EN_B = 382, 397` 不能信** —— 见下方"EN 带"行。

| 参数 | 实测值 | 依据 |
|---|---|---|
| 网格列数 `NCOL` | **62** | 代码 L45；ELF cave `0x4170AC addiu r14,r0,62`；纹理 row 0..11 每行恰 62 格 |
| 格宽 `CW` | **16** | 代码 L45；`0x4170C4 li 16`；列 pitch 实测 16 |
| 格高 `CH` | **16** | 同上 |
| 网格起点 `Y0` | **2** | `0x4170F8 addiu r13,r14,2` |
| 跳行起点 `SKIP_ROW` | **12** | `0x4170D8 li 12`；实测 row11→row12 空档恰 48 行 |
| 跳行数 `SKIP_ROWS` | **3** | `0x4170E8 addiu r13,r13,3` |
| `SKIP_OFF` | **48** = `CH×SKIP_ROWS` | cave 动态算，无立即数 |
| **EN 带（盘上 FT 记录 v0/v1）** | **452 / 468** | 实测 ASCII 记录 v0 唯一值 = 452、v1 = 468；纹理带精确占 y452..467 |
| EN 带（`gen_font16.py` L50 口径 = 采样顶 S） | 代码写 **382/397**（→ v0/v1 = 380/395）**≠ 现役盘** | 全链实跑产物墨行 (380,392)+(395,407)，**452..467 全空**；现役盘 380..392 是**未被 FT 引用的死墨**；两边差 1723 B |
| 纹理 | **1024 × 512** texel, 4bpp | PAK 头实测 `w=1024 h=512 psm=0x14` |
| 容量 | 42 行 × 62 列 = **2604 格** | 现用 1212 字（76 单 + 1136 对） |

**⚠ EN 带有两套坐标系，不可直接比较**（2026-10-04 审计澄清）：
- `gen_font16.py:50` 的 `EN_A/EN_B` = **"采样顶 S"**，记录 `v0 = S-2, v1 = S-2+13`（见该文 L214 打印）。
- 盘上 FT 记录 = **v0/v1**。现役 = **452/468**；换算到 S 口径应为 **454/470**，且带高 13→16。
- **⇒ 现役 EN 带几何由 ZH64/65/69 重铺而来，`gen_font16` 这条链根本不产生它**
  （差 1723 B = 395..407 的 88B + 452..467 的 1634B + 1B NLOOP）。
  这正是历史 `FONT_PIPELINE.md`「重放仅差 89B」被否证的原因。
- **改 L50 前必须先改 L272 的 `A[412:512]` 断言**（二者互锁），并补回缺失的 `patch_zh69.py`。

**字形来源**：`方正像素16.ttf`（FZXS16）16px 原生网格渲染；EN 98 码位复用上版图集。

**⚠ 不要误读的字段**：`fld[1]`（FontDefinition+0xC，CharHeight 语义）实测 **26**（large/default 面），
**不是网格 CH**；huge 面 `fld[1]=16`。

## 二、盘内位置（MENU.IMG @LBA 776286）

| 项 | 偏移 | 大小 | 实测 |
|---|---|---|---|
| 字表槽 FT | `0xB9120` | 4421 B | `u32[0]`=**0x529(1321)**、`u32[1]`=**0x1736(5942)** —— 这两个是**存储态 LZ 帧头**(payload 长 / 展开长)，**不是 wire 长度**；FT 展开态实为 5942 B |
| 字库 PAK 记录 | `0x58431` | 263,244 B (`0x4044C`) | 见下 |

PAK 记录格式（实测复现，**逐字节零剩余**）：
```
{u32 type}{u32 nameLen}{name}{u32 psm}{u32 w}{u32 h}{u32 clut_size}{clut[clut_size]}{u32 px_size}{px[px_size]}
```
`@0x58431` 的 `new_font_revised`：
```
type=0x0  nameLen=0x10  name='new_font_revised'  psm=0x14(PSMT4)  w=1024  h=512
clut_size=0x410(1040B)  px_size=0x40010  end=0x4044C(263244)
CLUT_DATA=+0x28  PX_SIZE_OFF=+0x438  PX_TAG=+0x43C  PX_DATA=+0x44C
```
- **只有 4 个 u32 参数**（psm/w/h/clut_size）。历史 `FONT_CAPACITY.md §548` 记的 "8×u32 hdr"
  是**误读** —— 它说的"第 5..8 个 u32"其实是 **CLUT 数据的前 16 字节**；CLUT 是 **1040 B** 不是 1024。
- **`type` 不是布尔**，是**记录类型**（0/2/3），`0x63` 才是结束哨兵。
- 4 条记录（0x1031 + 0x4044C + 0x10446 + 0x1044C）= 0x61D0F，`0x63` 恰在 0x61D0F，+4 = 400659 = 文件尾，**零余字节**。
- 像素容器：8 段 PT TRXPOS y = 0/64/128/192/256/320/384/448（覆盖行 0..510）。

**历代对照**（供识别过时描述）：
| 盘 | psm | 纹理 | FT 展开 | ASCII 'A' 记录 |
|---|---|---|---|---|
| 原版 / EN_SCOUT | 0x13 | 512×512 | 7222 B | (0,12,318,104,331,130) |
| **ZH82/83/84（现役）** | **0x14** | **1024×512** | **5942 B** | **(0,8,256,452,264,468)** |

## 三、元数据层：`charset_compiled_zh16.json::grid` 是**过时**的

现值（旧 CH13 残留）：`ncol:37, cw:13, ch:13, skip_row:14, skip_off:39, en_y:[476,491], icon_box:[19,198,64,221]`

**建议改为**（含审计提出的"拆键"以避免同名不同义）：
```json
{"ncol": 62, "cw": 16, "ch": 16, "gridy": 2,
 "skip_row": 12, "skip_rows": 3, "skip_off": 48,
 "en_y": [452, 468],
 "x0_render": 20, "x0_draw": 4,
 "icon_src": [19, 198, 64, 221], "icon_dst": [3, 198, 48, 221],
 "dv": 2, "n_chars": 1212}
```
- **`en_y` = [452, 468]**（记录 v0/v1；ZH16 时写 `[476,491]` 是旧 CH13 版）
- **`x0` 必须拆键**：`gen_font16` 的 `X0=20`（渲染原点）vs `build_font.py` 的 `X0=4`（PSMT4 采样偏置修正后的绘制原点）**同名不同义**
- `icon_box` 同理拆 `icon_src`/`icon_dst`（整体 x−16）
- 需新增 `skip_rows: 3`

**注**：`codes` / `pair_of` 两个字段（1212 字码位映射）**是现役正确的**；且**无人读 `grid`**（20+ 处消费者只用前两者），故该过时项**无程序危害，仅误导人工阅读**。

## 四、历史版本对照（识别过时描述用）

| 版本 | 网格参数 | 字号 | 状态 |
|---|---|---|---|
| ZH11 | NCOL=37, CW=13, CH=15, Y0=128 | 12px | 已废弃 |
| ZH12 | NCOL=37, CW=13, CH=17, Y0=130 | 12px | 已废弃 |
| ZH13 | NCOL=37, CW=13, CH=16, Y0=130；EN 带 452/468 | 12px | 已废弃 |
| ZH16 | NCOL=37, CW=13, **CH=13**, Y0=2, skip_row=14, skip_off=39；EN 带 **476/491** | 12px | **已废弃（上一版）** |
| **现役** | **NCOL=62, CW=CH=16, Y0=2, SKIP_ROW=12, SKIP_OFF=48；EN 带 452/468；纹理 1024×512** | **16px** | **现役** |

**识别技巧**：文档里出现 `CW=13` / `CH=13` / `NCOL=37` / `en_y=[476,491]` / `skip_row=14` /
`Y0=130` / `12px` / `Zpix` / `512×512 纹理` / `ft 7222` 且**在描述"当前状态"**的，都是过时描述。
出现在带日期的历史章节（如 `FONT_CAPACITY.md` §九~§十六）里属正常演进记录。

## 四·补、字库加载链与两条**硬约束**（2026-10-04 深度逆向，见 `work/_dis/REVERSE_FONT_LOAD.md`）

> 三重独立证据：盘上字节 + 反汇编(`dis_ee2.py`) + 运行时(RAM dump `win_f00011030_eeram.bin` / 4 份 `cdvd.log`)。

### 加载链（一句话）
```
IkeUIMgr::PlayLogo → PreInit @0x274F20
  ├─ UITextureMgr::LoadingTexturePak(0,0) @0x51B660   → "common.pak"
  ├─ RSFontMgr::Create() @0x21A5B0                    → 单例, sizeof 0x74
  ├─ RSFontMgr::Initialize(0x500) @0x21A450
  └─ RSFontMgr::ReadResourceFile("font.res") @0x219380
        ├─ 首字段 = 纹理名 "new_font_revised.rsb" → mgr+0x1C (mFontFilename)
        ├─ faceCount=3 → RSArray<FontDefinition>(mgr+0x0C), 每项 0x48
        ├─ styleCount=8 → RSArray<RSFont>(mgr+0x04), 每项 0x2C
        ├─ UIModel1(mgr+0x28).SetTexture(GetTexture("new_font_revised.rsb")) ← **唯一字形图集**
        └─ UIModel2(mgr+0x4C).SetTexture(GetTexture("pda_counterparts.rsb")) ← µ/±/图标 lane
```
- 文件名来自 **ikeuimgr.cpp 的文件级静态 `kFontResourceFilename @0x57ABE0`**（`"font.res"` 字面量 `@0x57AD70`），**不来自任何表**（全 ELF 4 处代码引用、**0 处数据引用**）。
- `IkeUIMgr::Create @0x2750F0` 有**单例短路**（`0x275124`），PreInit 先跑过一次后它永不执行 ⇒ **实际只读一次 `font.res`**。
- 纹理宿主 = **COMMON.PAK**（`LoadingTexturePak` 的 kind=0 → `"common.pak"`）。

### ★ 硬约束 1：CJK 字形矩形**不来自 FONT.RES 记录**
```
DBCS 码位: idx = (b0-0xA1)*94 + (b1-0xA1) + 0xE0  ≥ 0xE0 = def+0x44
⇒ 必然 ≥ 记录表 count  ⇒ 必然走 **mod cave 0x4170A0-0x417130** 的硬编码公式:
     row = idx / 62 ; col = idx % 62 ; x = col*16 ; if(row>=12) row += 3 ; y = row*16 + 2
且 cave **0x416FC0** 把 CJK 步进宽**固定为 16**。
⇒ **想改 CJK 的字形位置或宽度, 必须动 cave; 纯数据(改 FONT.RES)改不动 CJK。**
⇒ 只有 **ASCII 区**走记录表, 那部分纯数据可改。
```
（历史文档中"加第二套 face 即可换字形"的说法，对 CJK **不成立** —— 前提漏了这条 cave 分支。）

### ★ 硬约束 2：GR.IMG 侧字库是**死拷贝**
GR.IMG **确实自带**一份独立的 FONT.RES + COMMON.PAK（原盘与 MENU 侧 sha1 完全相同：
FONT.RES `896f1a7d…`、COMMON.PAK `ec98f3b2…`），但 **运行时从不读**：

| 资源 | MENU 侧读取 | GR 侧读取 |
|---|---|---|
| FONT.RES | **3/3 扇区** | **0/3** |
| COMMON.PAK | **197/197 扇区** | **0/197** |

（4 份独立 `cdvd.log` 逐 LBA 匹配：EN 原盘 + ZH84 三次运行，结论一致。）
⇒ **历史 `FONT_CAPACITY.md §四`"游戏内 UI(简报/字幕/战斗 HUD)走 GR.IMG 侧字库"的结论被推翻。**
⇒ **当前构建流水线仍在往 GR.IMG 写 FONT.RES/COMMON.PAK —— 这是无效动作**（可考虑停写以省时）。
⇒ 也意味着**"GR 侧单独做小字号"这条路不存在**。

### 多 face / 多字库的真实能力
- `RSArray<RSFont>` = `{T* mData@0; int mSize@4}`，**无硬上限**（`IncreaseToSize_Array @0x21A9A0` 用 `__nwa` 任意增长）；现役运行时 **mSize=8**（default×2, large×4, huge×2）。
- `GetFont(i) @0x3A17D0` = `mData_of_mgr+4[i]`，**无边界检查**；9 个调用者索引 = **4,4,5,5,5,4,4,6,6**（无 0/1/2/3/7）。
- **菜单侧不走 `GetFont`**，而是内联 `__vc__16RSArray<6RSFont>Fi @0x2007E0`（14 处）；`RSTextComponent` 用它**资源里的 per-component fontID**（`ReadResource+0x3C` 读 u32 → 存 `+0x9C`，解析出的 `RSFont*` 存 `+0x98`）。
- **让菜单走 `GetFont(1)` = no-op**：现役 `FONT.RES` 里 **style[0] ≡ style[1]**（同 face、同字段、scale 1.0、同一 FontDefinition）。

| 想做的事 | 可行性 |
|---|---|
| 第二套**字形**（记录表区 / ASCII） | ✅ **纯数据**（`faceCount` 是 u32，数组无限增长） |
| 第二套字形**用于 CJK** | ❌ 必须动 cave（见硬约束 1） |
| 第二套**纹理** | ❌ 必须改 ELF：`FontDefinition`(0x48) **无纹理字段**；绘制链只认**一个**字形 UIModel(`mgr+0x28`)；`FindSurface @0x51B140` 按名去重 |

### 结构布局（每项有依据，详见报告 §6）
| 结构 | sizeof | 关键字段 |
|---|---|---|
| `RSFontMgr` | **0x74** | +0x04 `RSArray<RSFont>` / +0x0C `RSArray<FontDefinition>` / +0x1C `RSFilename`(mFontFilename) / +0x28 UIModel#1(字形) / +0x48 u8 mReady / +0x4C UIModel#2(图标) / +0x6C int size |
| `FontDefinition` | **0x48** | +0x0C CharHeight(**26/26/16**) / +0x38 rec 指针 / +0x3C face 名 / **+0x44 记录条数(224/224/96)** |
| `RSFont` | **0x2C** | +0x04 face 名 / +0x14 空格宽 / +0x1C scaleX / +0x20 scaleY / +0x28 `FontDefinition*` |

（wire 读序与结构偏移**不同**：14 个 u32 的文件顺序 = 08,0C,10,14,00,04,30,34,28,2C,18,1C,20,24。）

## 五、与垂直偏移问题相关的既有结论

`docs/han_v2/FONT_CAPACITY.md` §十六 曾记录：
> ③**按钮类 UI 文字低 ~4px = 引擎文字对象 Y（CJK 字面高于原 EN 设计），非字体层可修**
>    （+1 已回收 2px）

**⚠ 这条结论的后半句已被后续轮次推翻**（2026-10-04）：实际做法**正是改引擎里的字高/偏移常量**，
而且验证有效：

| 问题 | 引擎侧修法 | 实测 |
|---|---|---|
| 训练标题框下对齐 | `0x4176A0` cave 字高 `16 → 20`（`patch_zh83.py`）| 下留白 1.2 → 3.3（EN 4.3）|
| 金框条目名/栏目行下沉 3px | `0x21D940` 的 `addiu $v0,$v1,-21` **还原为 EN 的 `subu $v0,$v1,$v0`**（K=CharHeight=26）| y 90 → **87**（EN 87）|
| 内页大标题下沉 7px | `0x565910` 的 `addiu $a3,$a3,7` → **nop** | y 25 → **18**（EN 18）|

**正确表述**：这类偏移**要改引擎里那个被硬编码的字高/偏移常量**（而不是改字库数据）。
字库层改不了，但引擎层可以 —— 且这些 hook 点已有先例可循。

**注意**：这些是**逐点硬编码**的修法，覆盖面各不相同：
- `0x4176A0` 是 `ComputeDrawXY` 的居中分支（**只影响走该分支的组件**）；
- `0x21D940` 影响**所有走 `IkeBaseButton::DrawText` style-0xC 分支的按钮族**（金框列表 10 行模板一致）；
- `0x565910` 是 zh7 绘层 cave，只对 `comp[0x9C]==5` 的组件生效（内页大标题模板一致）。

### 实测补充（`work/_squad/UI_TEXT_SURVEY.txt`，1165 行全界面文本站点普查）：
- 控制器界面左列 `x` 随文本长度变化（100~186）= 右对齐；右列 `x` 恒 418 = 左对齐；
  **同一行右列 y 比左列大 3**（引擎数据本身，非字库问题）。
