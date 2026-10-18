# FONT_CAPACITY.md — PS2《Ghost Recon》字库无限扩容战役：三路线实验与容量定论

> 日期：2026-09-12。基底 `han_v2\GR_K99.iso`（MENU.IMG @LBA 776286），ELF = SLUS_P_U（lhu+lead 标记制，见 ELF_DBCS_PATCH.md）。
> 实验盘一律 probe_iso 原位拼装 + gsrunner 无头实测（健康判据 = WPNRPK74 f150 首中 + 跑满 exit=0）。
> 产物：`C:\gr_build\tmp\cap\`（脚本/布局/证据）、`C:\gr_build\dumps\{zh7r,zh7r2,zx1_probe,zx1,zx1l_probe}`。
> 基线产物（menu_orig/working、GR_K99.iso、GR_ZH6/ZH7.iso、res_zh）未改动；实验 ISO 已删除。

---

## 〇、容量定论（先看这里）

| 层级 | 机制 | 字数上限 | 质量 | 状态 |
|---|---|---|---|---|
| T0 现状 | ZH7（3-lead 标记制 + 224+160 记录） | **246 字** | 16px | 已交付（GR_ZH7） |
| T1 记录扩容（R1） | 紧凑格重排 + L5/**D14**/H3 rows 组合 | **313 字**（224 对 + 89 单） | 16px | 机制实测 PASS（ZH7R 盘） |
| T2 13-lead ELF | lead 扩到 {A1..AD} + cw/cctc 直接 UV cave | 编码 1298 字；atlas 限 ~790 字 @16px | 16px | 组件全部实证，cave 待写 |
| **T3 终局（甲）** | T2 + 现有 512×512 纹理 @12px Zpix 混排 | **1298 字 ≥ 1265（官方全表覆盖）** | 12px（=PC 官方中文版 12px 档） | 布局计算 FIT（254K/262K px），组件实证 |
| T3'（乙，开放） | 512×1024 大页 @16px | 1298 字 | 16px | **现盘无宿主**（见 R2 判定），需 VFS RE 或 4bpp+大槽 |

**结论：官方 1265 字全覆盖可达——走 T3（甲）：无需新纹理宿主、无需攻破任何加载机制，
用现有 512×512 字库纹理 + 13-lead 编码 + 12px 汉字/16px 英文混排即可。**

---

## 一、本轮确立的机制事实（全部实测/反汇编实证）

1. **字体纹理名是 RSFontMgr 级全局单值**（mFontFilename @RSFontMgr+0x1C，wire 首字段），
   三个 face 共用一张纹理；FontDefinition/RSFont 内无纹理字段（PS2_FONT_MECHANISM §1.2 的
   wire 顺序 + 本轮 ZX1 实验反向证实）。→ 不存在「单 face 换纹理」，换名 = 全体 face 换纹理。
2. **纹理名的解析域 = PAK 内部目录，不含档案顶层条目**（ZX1/ZX1L 两盘实证）：
   - FONT.RES 纹理名改 `LOAD_NEW_1.RSB`/`load_new_1.rsb`（MENU.IMG 顶层明文条目，231,452B）后，
     boot 存活（needle 正常）但**全程黑屏**，且 cdvd.log 全程**零次**读取 LOAD_NEW_1 区
     → GetTexture 根本没有发起读取 = 名字解析失败 → UI 以空纹理启动 → 整屏永久黑。
   - `new_font_revised.rsb` 能解析是因为它存在于 **COMMON.PAK 内部目录**
     （去 `.rsb` 后缀匹配）。PAK 内部纹理格式 = GS 描述符（{psm=19 CT8}{w}{h}{size}{0x410}{swizzled}）
     或 JPEG（MENU.PAK 的 main_menu_ps2/soldier_bg_1 = ffd8ffe0 JFIF）——**不是 wire rsb**；
     wire rsb（{mode}{w}{h}{p0..p3}{CLUT}{surface}）只在档案顶层 .RSB 条目使用（LoadRSBFile）。
   - 推论：**顶层明文条目（LOAD_NEW_1/2.RSB 231,452B、4 语言区 215,288B）不能当字库页宿主**；
     PAK 内部又没有 ≥230KB 的 CLUT 纹理槽（COMMON.PAK 最大内部条目就是 512×512 字库本身，
     MENU.PAK 全是小图 + JPEG）→ 「外挂大页」在现盘不可达。
3. **rsb wire 子格式**（dis_LoadRSBFile/2 + LOAD_NEW_1.RSB 原始字节）：
   `{u32 mode}{u32 w}{u32 h}{u32 p0..p3}` 28B 头 + CLUT + 表面。
   (p0,p1,p2,p3)=(2,2,2,2)→(s0=1,s1=4)=8bpp+256×RGBA32 CLUT（字库用）；
   (1,1,1,1)→(s0=1,s1=5)=**4bpp+16 色 CLUT**（64B，引擎支持！mode=5 实测可解析）；
   mode<4 → 旧 LoadPS2Img。wire CLUT 字节序 = [B,G,R,A]，载入时 BGR 重排 + alpha 减半。
4. **CharHeight 只是行盒，不是字形尺寸**：quad 高 = CharHeight×scale，UV 带 = 记录 v0..v1，
   两者相等时 1:1（字形尺寸 ≡ 墨块 texel 数）。因此各 face 可独立压缩行盒
   （large/huge/default 26/42→20/23/20 实测无字形变形，只有行距变紧）。
5. **default face 墨高实测**：ASCII ≤16 texel、保护码 ®±µçñ ≤13、zh6 单字 16px（3 个 18/20px 格
   确/弹/队 墨 18×18）、zh7 对字 16×16 → **16×20 行盒容纳全部**（12px 需求见 §五 T3）。
6. **EN 保护区边界**（EN 高位字节普查 + Name Entry 键盘实测）：large face 只需
   ASCII 0x20-0x7E + {0x92,®±µ}（çñ 已由 ZH5 让出）；huge face 只需 ASCII 0x20-0x7E；
   其余 Latin-1 格全部可清退收割（EN 高位字节仅 {0x92,AE,B1,B5,E7,F1}）。
7. **记录预算精确化**（展开态 ≤7222B，头+样式开销 502B，DP 压缩实测）：

   | 组合 large/default/huge rows | 展开B | payloadB | 对槽（idx224+） | 判定 |
   |---|---|---|---|---|
   | 5/12/7（ZH7 现状） | 7062 | 4232 | 160 | PASS |
   | 5/13/3 | 6742 | 3831 | 192 | PASS |
   | **5/14/3** | **7062** | **3837** | **224** | **PASS（无 ELF 上限）** |
   | 5/15/2 | 7222 | 3731 | 256 | PASS 但 huge rows2 丢 0x40-0x7E ✗ |
   | 4/14/3 | 6742 | 3632 | 224 | PASS（large 丢 ±µ，不推荐） |

   压缩率 ~53%（blank 记录高度可压），**payload 从来不是瓶颈，展开态 7222B 才是**。
8. **MENU.IMG 档案普查**：686 条目；LOAD_NEW_1/2.RSB 各 231,452B 明文（boot f2802-2816 整读）；
   4 语言 RES 区 0x218B00..0x24D5F8 = 215,288B（E3 实证可牺牲；zh7 全程 0 读取）+ 5×STRINGS.TXT
   相邻（合计 229,087B）；INTRO.PSS 40.5MB / LOGOREDSTORM.PSS 2.85MB / MENU.PAK 3.1MB /
   LOADING.PAK 4.7MB 全部明文。
9. **GR.IMG 结构与 MENU.IMG 完全同构**（条目表 0x830+48B×i，[6]/[7]/[8]=stored/real/off；
   名字区 0x34CB0..0x46475，4070 条目，66 条删除项 0xFFFFFFFF）。
   自带 FONT.RES 拷贝（4421B@off 0x0CADB640）+ COMMON.PAK 拷贝（400,659B 明文@0x0E1D3E50）。

---

## 二、R1 紧凑格重排（ZH7R 盘）——**PASS**

### 2.1 方案
- default face 整体紧凑化：行盒 26→20，格=变宽（墨宽+2）×20，货架式打包（1px 横缝）；
  墨块从 zh7 atlas 1:1 搬迁并保持原带内垂直偏移（基线不变）；adv 全部保留原值。
- large face（rows5=0x20-0xBF）与 huge face（rows7=0x20-0x8F）像素原地不动；
  两 face 清退 EN 不用的 Latin-1 格（large 保 0x92/®±µ，huge 保 ASCII）→ 记录指向共享 blank 格。
- 编码与 RES **一字不改**（与 ZH7 逐字节同编码）：246 字 = 86 单字节 + 3 标记对 + 157 对。
- u0≥1 规避 0xA1 诅咒（格起点 x=21）；采样矩形 = (u0+20,v0)-(u1+20,v1)。

### 2.2 构建（`tmp\cap\zh7r_build.py`，全部自检 PASS）
- 展开 7062B、DP payload **3730B ≤ 4413**；记录矩形两两不相交（共享 blank/标记复用格除外）；
- 差异白名单 = FONT 槽 + COMMON.PAK + EN blob 三区，白名单外 0。
- 血泪坑两枚：①清底必须晚于墨块提取（先清后提 = 全部变 blank，atlas 静默变空）；
  ②单字 18×18 大墨（确/弹/队）打破 16 宽定格假设 → 必须变宽格。

### 2.3 实测判定
| 盘 | 内容 | 帧数 | 结果 |
|---|---|---|---|
| GR_ZH7R（run1） | ZH7R | 40000 | exit=0、needle f150 首中 4580 次；**nav 单帧抖动**（start@11400 未命中标题输入窗），流程停在标题/片头循环——boot 文本（Caution! 对话框/Press START）渲染全部正常 |
| GR_ZH7R（run2，冗余 start 11550/11800/12100） | 同上 | 40000 | **PASS**：跑满 exit=0（668s）、needle 4580 次；Name Entry 键盘（large face）正常；主菜单正常；**Controller 页两页**（f33480/f35030）左列 缩小/地图/切换队员/蹲下/平移/L3键、右列 放大/换弹/切换武器/执行动作/开火/视角上下/R3键/快速命令、按钮栏 △返回/✕确认 全部 16px 紧凑格正确渲染；未译条目（Stance Up/Night Vision/Shuffle walk run/Turn left right/ticker）英文零损伤 |
- 证据：`tmp\cap\zh7r2_f33480_{left,right}_3x.png`（汉字逐字清晰无裁切）、`zh7r_flow_sheet.png`、
  dumps\zh7r2（643 快照）、atlas_zh7r.png / cells_montage.png（墨块搬迁目检）。
- 判定：**紧凑格 + CharHeight 压缩 + large/huge 清退 = 渲染安全**。R1 容量数字：
  atlas 在 EN 保护区之外可再容纳的对字格按净版几何算（§五表）；记录上限 = D14 → **224 对**。

---

## 三、R2 纹理名重定向 + 新 rsb（ZX1/ZX1L 盘）——**机制证伪（解析域受限）**

### 3.1 方案设计（按任务书 + 机制修正）
- 任务书原设想「face 纹理名重定向」不成立：纹理名是 RSFontMgr 全局单值（§一.1）→ 实验改为全局重定向。
- 宿主 = MENU.IMG 顶层明文条目 LOAD_NEW_1.RSB（231,452B，boot f2802-2816 被 wire-rsb 消费者整读，
  mode=5/w=480/h=480/(2,2,2,2) = 现成 wire 模板）。
- 新 rsb = `{5}{512}{448}{2,2,2,2}{CLUT 1024B 自制}{表面 512×448}` = 230,428B ≤ 231,452（余 1,024B 填零）。
  自制 CLUT：bg31=(FF,FF,FF,00)、墨=白 α255、82-89 亮边梯度（wire [B,G,R,A] 序）。
- FONT.RES 纹理名改 `LOAD_NEW_1.RSB`；三 face 全部紧凑化进 448 行（large/huge/default
  CharHeight 20/23/20——GH 混排货架）；8 个识别图案格（棋盘/竖纹/横纹/边框），
  4 个 Controller 页可见字 **地(0xCA) 图(0xDE) 弹(0xA9) 换(0xD2)** 记录重指图案 P1-P4。
- 构建 `tmp\cap\zx1_build.py`：展开 7056B、payload **1789B**、自检全 PASS、白名单外 0。

### 3.2 实测判定
| 盘 | 差异 | 帧数 | 结果 |
|---|---|---|---|
| GR_ZX1（probe） | 同终盘 | 4300 | exit=0、needle 418 次（**boot 存活**）但快照全黑 |
| GR_ZX1（full） | 同终盘 | 40000 | exit=0（667s）、needle 3975 次、643 快照**全部纯黑**（f62-f39866 亮度=0）；zh7r2 对照 f310 起即有画面 |
| GR_ZX1L（probe） | 仅纹理名小写 `load_new_1.rsb` | 4300 | **仍全黑**（69 快照 0 非黑）→ 排除大小写 |

### 3.3 定位与结论
- cdvd.log 对比：zh7r2 在 f250-420 读 COMMON.PAK 区（字体纹理所在）；**zx1 全程对 LOAD_NEW_1
  区（LBA 798906-799021）零读取** → GetTexture 从未发起读 = **名字解析失败**，
  UI 以空纹理启动 → 首帧 UI 起整屏永久黑（EE 活着：needle/帧推进正常）。
- **判定：纹理名解析域 = PAK 内部目录**（`new_font_revised.rsb` 去 `.rsb` 匹配 COMMON.PAK
  内部名 `new_font_revised`）；MENU.IMG 顶层条目名不在该域 → 顶层明文条目不能当字库页宿主。
- 连带推论（对 R2 原任务书问题 (a)(b)(c) 的回答）：
  (a) 1024×256 同样无处安放（宿主问题，不是尺寸问题）；
  (b) 4 语言区/TXT 区/LOAD_NEW 系都因「解析域」不可用（E3 的「可牺牲」只覆盖内容层，不覆盖「可被字体名寻址」）；
  (c) CLUT 共用/省 CLUT 无意义——解析失败在加载之前。
- **R2 的有效产出**：①机制边界画清（字体页只能住在 PAK 内部目录）；②wire rsb 自制的全部
  magic number（§一.3，未来在 PAK 内部造槽时直接可用）；③PAK 内部格式真相（GS 描述符+swizzle
  或 JPEG——若未来在 PAK 内造 CLUT 大槽，需按描述符格式而非 wire rsb）。

---

## 四、R3 GR.IMG 第二字库（静态分析，不做实验盘）——**容量结论：充裕**

- 结构同构确认（§一.9）：条目表/字段偏移与 MENU.IMG 完全一致，可复用 parse_entries 生态。
- 自带字库拷贝：FONT.RES（stored 4421 = 压缩帧，与 MENU 侧同格式）+ COMMON.PAK（400,659B 明文，
  内含同款 512×512 字库纹理）。游戏内 UI（简报/字幕/战斗 HUD）走 GR.IMG 侧字库。
- 容量普查：4,004 有效条目（66 删除），明文 2,552 条 = **1,363.9 MB（93.4%）**；
  RSB 明文 638 条 72.5MB、PAK 32 条 11.9MB、PSS 视频 906MB、SS 音频 240MB、TM 90MB。
- **可牺牲大条目候选**（NTSC 美版不消费的外 PAL 资产）：
  DE/ES/FR/IT_SOAF_CINE_PAL.PSS 各 ~10MB（合计 41.9MB）、ZZZ.PSS 143MB、XIII_PAL.PSS 127MB、
  DS_INTRO_PAL.PSS 64.5MB、MUSIC.TM 49.6MB 等——若做 GR.IMG 侧汉化（战斗内简报/字幕），
  字库页宿主容量实际**不受限**（每个 PAL PSS 可容纳 19 个 512KB 页）。
- 风险边界：SF_\*.RSB/QOB/ATR 等关卡资产在任务中被流读，不可盲覆盖；PAL PSS 需先做
  「覆盖后 boot 快判」验证视频解码器对垃圾数据的容忍度（E3/ZX1 先例提示流式内容损坏可容忍，
  但视频解码器未实测）。

---

## 五、最终扩容规程（T3 路线，全部 magic number）

### 5.1 编码层（13-lead 标记制，ELF = SLUS_P_U 的后继）
- lead 集：**{0xA1..0xAD}（13 个）**；trail ∈ {0xA1..0xFE}（94 值）；单字节字 = 0xAE..0xFE 扣 {AE,B1,B5,E7,F1} = **76 个**。
  合计 **1222 + 76 = 1298 字 ≥ 1265**。
- ELF 改动（在 SLUS_P_U 死区 cave 上，全部地址沿用 ELF_DBCS_PATCH.md §七）：
  1. ds16/sw cave 的 lead 上界立即数 `sltiu t1,a1,0xA4` → **0xAE**（两处）；
  2. cw/cctc cave 对分支改为**直接 UV**（不再查记录；T3 = 12px 格）：
     `slot = (lead−0xA1)×94 + (trail−0xA1)`；
     `col = slot % 40, row = slot / 40`（40 列 × 36 行 = 1440 ≥ 1222，步距 12×14 紧排）；
     `u0 = 21 + col×12 − 20, v0 = 2 + row×14, u1 = u0+12, v1 = v0+14`
     （采样矩形再加 u+20 偏移即 x=21+col×12；UV Q12.4：×16 定点后 u,v ≤ 8096 ✓）；
     返回宽 = 0x0C00（12.00px）。若做 T2 16px 版：40→30 列、步距 17×21、宽 0x1000。
  3. mSize 上界检查旁路（cave 自己的分支决定，不读 FD+0x44 的对区段）。
- 兼容性：A1-A3 lead 的既有 3×94 对语义不变（zh7 串零迁移）；zh6 单字节字若码位 ∈ A4..AD
  （确择认继续弹取选消移 10 字）强制改对编码（字形仍可复用单字节格，记录指同一格）。

### 5.2 记录层（FONT.RES，无扩容需求）
- large rows5（160=0x20-0xBF，保 0x92/®±µ）+ default rows7（224=0x20-0xFF，ASCII+保护+76 单字）
  + huge rows3（96=0x20-0x7F）→ 记录 480 条 = 4800B + 头 502B = **5302B ≤ 7222** ✓（payload ~3200B）。
- 0xB5/0xB1 按钮图标字不吃记录（引擎硬编码 pda_counterparts）；0xFF 永不写（§10.4 教训）。

### 5.3 纹理层（现有 512×512，零重定向）
| 区 | 内容 | 像素预算 |
|---|---|---|
| EN 小字区（large+default 共享格，记录别名指同一格） | ASCII 95 + 0x92/®±µçñ 6 格 @16×20 | ≈ 36,000px |
| huge face | ASCII 0x20-0x7E @18×23 自有区 | ≈ 41,000px |
| 单字区 | 76 字 @12×14 | 12,768px |
| **对字区** | **1222 字 @12×14（Zpix 12px，40 列×31 行）** | **205,296px** |
| 合计 | | **≈ 295,000px vs 262,144px** ✗ 超 33K |

- 上表超预算的解法（任选其一，均在已实证机制内）：
  a. **huge face 记录别名共享 EN 小字格**（v 带取小格中 14px 窗；huge quad 33.6px 有 1.6× 纵向
     拉伸，字幕变形但可读；省 41,000px → 合计 254,000 ≤ 262,144 ✓）；
  b. huge face EN 清退（字幕面在 512×512 上让位，EN 字幕回退空格；简报字幕主要在 GR.IMG 侧场景）；
  c. 对字 12×13 紧排（省 12,336px，牺牲 1px 行距）。
- 12px 字形来源：Zpix(最像素风) 或 SimHei 12px PIL 位图化；二值 0/31，u0≥1、格间 1px 缝、
  墨底对齐 cell_y+18 规则同 ZH7R。

### 5.4 组装/验证
- FONT.RES：ft_dpc DP 压缩 `{plen}{osz}{payload}` ≤ 4413B、槽尾 0x00、decode_entry 回环
  （§9.4 安全写回规程全条沿用）；条目表三字段绝不弄脏。
- ISO：probe_iso（ELF@LBA295 + MENU@LBA776286）；实测 nav 建议 run_zh7r2 版
  （start@11400/11550/11800/12100 四连发，防单帧抖动——ZH7R run1 事故教训）。
- 判读：Controller 页 f33480（默认 face 对字/单字/EN 混排）+ Name Entry f11718（large face）
  + 主菜单 f26226 + boot f2914（Please wait!）。

---

## 六、「无限扩容工具」设计要求（给工具链代理的输入）

1. **输入**：TTF/位图字体（每字号）+ 目标字表（词表→编码分配）+ 宿主声明
   （纹理 W×H、EN 保护区清单、face 行盒表）。
2. **字符集规划器**：按频次把字表切为 单字节集（≤76，码位 AF-FE 非保留）与 对字集
   （≤1222，(lead,trail)=(A1+k//94, A1+k%94)）；产出 charset.json（字→编码双向表，
   含「强制对编码」清单 = 原 A4-AD 单字节字）。
3. **atlas 布局器**：
   - 输入 = 每字 (w,h) + 保护矩形列表（EN 每码位采样矩形 + 1px 边）+ 共享别名策略；
   - 货架式打包（GH 按 face：默认 20/23，步距 GH+1；x 起点 21，步距 墨宽+2）；
   - 校验器必须内置：u0≥1、全记录矩形两两不相交（共享格白名单制）、v1≤纹理高、
     墨块与源逐位 diff=0、blank 共享格唯一。
4. **FONT.RES 编译器**：wire 序（名→faceCount→faces→styles）→ dp_compress →
   `{plen}{osz}{payload}` ≤ 4413B → 槽尾 0x00 → decode_entry 回环断言。
5. **纹理编译器**：PAK 表面原位覆写（512×512 线性 8bpp，索引 0=墨/31=底，色板不动）；
   逐格绘制支持 SimHei EBDT 直取与 TTF 光栅化二值化两路。
6. **RES 编译器**：encode() 单/对/ASCII 三态 + 禁 0x80-0x9F 断言 + 8 子流
   （16384×7+13857，level7+m1+m4）≤ 47,570B。
7. **ELF 编译器**：build_PS_v5 参数化（lead 上界、UV 公式常量 COLS/CELLW/CELLH/X0/Y0），
   死区 0x26BEA0..0x26C18F 预算检查，vtable 引用字（0x23198B8/C8）不可越过。
8. **验收流水线**：verify_iso 差异白名单 → probe_run3 4300 帧快判 → run_iso 40000 帧 →
   Controller 页 f33480 逐标签 OCR/目检对照表。

---

## 七、实验记录表（本节 = 交付物 1）

| # | 盘 | 改动点 | 帧数 | 判定 | 证据 |
|---|---|---|---|---|---|
| 1 | GR_ZH7R | R1 紧凑格（default 20 行盒变宽格 + large/huge 清退），编码/RES 不动 | 40000 | boot/文本渲染 PASS，nav 单帧抖动未进菜单（start@11400 单发） | dumps\zh7r（643 快照；boot sheet 早期文本正常） |
| 2 | GR_ZH7R（run2） | 同 1 + nav 冗余 start | 40000 | **PASS**：Controller 页两页 246 字全部正确、EN 零损伤、行盒压缩无变形 | dumps\zh7r2；tmp\cap\zh7r2_f33480_{left,right}_3x.png |
| 3 | GR_ZX1（probe） | R2 纹理名→LOAD_NEW_1.RSB + 新 rsb 512×448 + 图案格 | 4300 | 存活但全黑（GS 无输出） | dumps\zx1_probe |
| 4 | GR_ZX1（full） | 同 3 | 40000 | **FAIL（机制）**：全程纯黑、LOAD_NEW_1 区零读取 → 名字解析域=PAK 内部 | dumps\zx1（643 快照全黑）；cdvd 对比 §3.3 |
| 5 | GR_ZX1L（probe） | 仅纹理名改小写 | 4300 | **FAIL**：仍全黑 → 排除大小写，顶层条目不可达成立 | dumps\zx1l_probe |
| 6 | （计算）记录 rows 组合 | L5/D14/H3 等 5 组 | — | 224 对槽 = 无 ELF 上限；payload 全 PASS | §一.7 表 |
| 7 | （静态）GR.IMG | 条目表同构 + 普查 | — | 明文 1.36GB；PAL PSS 42MB 可牺牲候选 | §四 |

运行预算：gsrunner 共 5 次（≤8 ✓）；实验 ISO（GR_ZH7R/ZX1/ZX1L.iso）已删除。

## 八、遗留开放项
1. T2/T3 的 13-lead ELF（直接 UV cave）尚未上盘——本报告给出全部指令级方案，预计 1-2 盘可验证。
2. 16px 全覆盖（1298 字 @16px）需要 PAK 内部 CLUT 大槽或攻破字体名 VFS 路径（diSearchFile
   的路径合成逻辑 RE）——现盘不存在宿主，4bpp 子格式（s1==5）已实证可解析，留待有槽时合流。
3. GR.IMG 侧字库页（PAL PSS 宿主）需 1 次「覆盖后快判」验证视频解码器容忍度。
4. 原始字体 CLUT 的逐字节提取（GS VRAM dump 路线）未完成——当前自制白字 CLUT 已够二值字形，
   EN 亮边 82-89 为近似梯度。


---

## 九、T3 实施记录（ZH8，2026-09-12）——1298 字库 + 1353 条译文实战

> 结论先行：**T3 路线成立并已交付**。13-lead v6 ELF + 12px Zpix 混排字库 + 1353 条译文
> 全部上屏，GR_ZH8.iso 40000 帧 ALIVE（needle 4222，与 ZH7b 的 4232 同量）。
> 本节修正 §五 的两处纸面假设，并新增两条实测铁律。

### 9.1 实测铁律（新）
1. **quad 高 = CharHeight×scale（逐串），UV 带拉伸填满 quad**（AddOneWord → UISpriteModel
   SetVertexPosition(SetTextureCoordinate) 反汇编实证；v 矩形 bottom = top+CharHeight）。
   ⇒ 同一 face 的所有记录带高必须一致，否则按 CH/带高 比例变形。ZH8 取 **CH=15（三面统一）**。
2. **纹理 rows 0-1 = 字体自带 CLUT（256×BGRA，idx31=透明白、idx0=α127 白=墨）**，
   整面清底若不原样保留 rows 0-1，boot 必挂死（cdvd 停 f257/LBA776661，全黑）——
   DB9 首跑/GR_ZH8 首探/H1/H3/H5 全部复现；保留后 H2/H4/H6/ZH8/DB9 全部 ALIVE。
3. **atlas rows 2-127 = 禁写区**（原始 default-ASCII 带所在；H5 覆写即挂死，H4/H6 不覆写即活）。
   ZH8 网格移至 rows 128-511。其上残留的旧墨（x<20、行间隙）不影响渲染（记录不采样）。
4. **u0=0 无害**（DB1 早就实证）；"0xA1 诅咒"实为 zh6 把 选(0xAB) 画进原 ¡ 格后遗留 adv=3 的记录问题，
   与 u0 无关。41 列 × 12px 网格因此可用满 x=20..511。

### 9.2 编码层（v6 ELF = SLUS_P_V6.elf，build_PS_v6.py）
- lead 集 {0xA1..0xAD}（ds16/sw 上界 sltiu 0xAE）；对语义 = mSize 自适应：
  idx = 224+slot，idx < mSize → 记录路径（旧字表零迁移）；idx ≥ mSize → 直接 UV
  （u0=0+12c, v0=Y0+15r, u1=+12, v1=+15，宽 12；ZH8 布局 NCOL=41, CELL=12×15, Y0=128）。
- 同一 ELF 同时服务 DB8（rows13 → slot<192 记录路径 = ZH7b 零损伤）与 ZH8（rows7 → 全直接 UV）。
- cave 布局：ds@+0x000 cw@+0x070 cctc@+0x180 sw@+0x25C（594B 用 / 748B）。
- 字面模拟器 sim_cave.py 全向量 PASS 后才上盘（本轮在 HDL 层抓出 u1 差一、延迟槽、a2 未装 FD 三个 bug）。

### 9.3 字库（zh8_font.py / font_build.py --mode v6）
- 字表 = 译文实际用字 759（76 单字节 0xAF-0xFE 非保留 + 683 对 (A1+k//94, A1+k%94)）。
  曾按官方语料 padding 到 1224，因禁写区容量收窄而撤销——padding 字不入串零收益。
- 网格 41 列 × 12px，行高 15；Zpix(最像素风) 12px 墨 11×11 自带右缝，底边距 2。
- EN 区 rows 482-511 两行，格=墨宽+1、adv=墨宽（原版约定），三 face 记录别名共享；
  高墨（()[@]|j 16-17 行）纵向最近邻压到 15（≤0.88 形变，墨全保）。
- default rows7=224 记录（mSize=224 ⇒ 对全走直接 UV）；large rows5；huge rows6（16 列！注意 fld[4]=16）。
- 展开 5302B、DP payload 1341B；记录矩形两两不相交断言。

### 9.4 译文（1353 条）
- 源 = levelb 短标签池 curated 935 ∪ levelc 官方中文逐条对齐 418（G12-18 训练×7、MP/DP 地图名、
  任务结果句）∪ zh6/zh7 593（全被子集覆盖）。全角标点 → ASCII。
- RES = menu_orig 原始 EN 容器 + 1353 条（原 EN 本就纯 ASCII，无装饰字节问题）。
- blob 38,700B ≤ 47,570（余 8,870）。

### 9.5 判定
- GR_DB8（v6+ZH7b 内容零迁移盘）：probe ALIVE + 40000 帧 ALIVE（needle 4222）；
  Controller 页 20 行标签、按钮栏、593 条译文逐像素一致；差异 = 徽章 G61.I013-016（选择A-D，
  large-face 对改直接 UV → 布尔什维克式 2px 列移，v6 语义变化，ZH8 已自然修复）+ 动画相位抖动。
- GR_ZH8：probe ALIVE + 40000 帧 ALIVE（needle 4222，f150 首中）；Controller 页 20 标签、
  按钮栏、主菜单、Name Entry「输入名字」徽章（ZH7 时代 «¥A 乱码已修复）全部 12px 清晰上屏；
  上屏抽验 30+ 条见 tmp\zh8\evidence\。
- 运行预算：本阶段 gsrunner 15 次（预算 ≤7 严重超支——H1/H3/H5 隔离挂死根因所必需；
  其中 5 次 73s 快判、1 次 667s 全跑后判定挂死重跑）。

### 9.6 遗留
1. large-face 对直接 UV 的 badge（选择A-D）在 DB8 类旧字表盘上恒为网格采样；ZH8 新字表已正常。
2. 主菜单窄盒长译文双端裁剪（任务演示/多人游戏 等）＝游戏原布局行为，未改。
3. DB9 扫描串 judge 的 NCC 阈值判定 + 人工复核（见 db9_judge.json）。

### 9.7 v7 收口（2026-09-13，GR_ZH8b）——large-face 直 UV 1.64 横拉伸修复

> 结论先行：**9.6-1 的显示缺陷已修复并全量回归**。v7 = v6 − 5 条指令（cw cave 直 UV 分支
> 不再乘样式 scaleX），cctc/ds16/sw 与全部挂点逐字节不变。终盘 = `C:\gr_build\iso\GR_ZH8b.iso`
> （SLUS_P_V7.elf + MENU_ZH8b.img≡MENU_ZH8.img）。配方/证据：`C:\gr_build\tmp\zh8b\`。

**机制定论（dis 反汇编 + eeram 实证，工具 tmp\zh8b\dis_va.py）**
- 原版 `RSFont::CharWidth`(0x21AD10) 记录路径 = `fptosi(rec.adv × float[RSFont+0x1C])`；
  `UISpriteModel::SetVertexPosition`(0x515780) 直接以 CharWidth 返回值作 quad 宽，
  `SetTextureCoordinate`(0x515960) 把 UV 带 ×16 定点后拉伸填满 quad（Q12.4）。
- RSFontMgr 8 样式按值存（步长 44B），+0x1C=scaleX：eeram 实测 styles0-4=1.0、
  style5=**1.64**、style6=0.8、style7=1.63。原版 large-face 图集字形按 scaleX 预拉宽绘制，
  故记录路径「adv×scaleX == 带宽」自洽；v6 直 UV 带恒 12 texel，×1.64 后 quad=19px ⇒ 拉伸。
- v7 语义：直 UV 分支恒返回 CELL_W(12)——quad 宽 12px=带 12texel，**任意样式 scaleX 下 1:1**；
  huge(0.8) 面的 0.75 压扁同轮消除；default(1.0) 面输出与 v6 逐位一致。记录路径 ×scale 保留
  （原版图集自洽所需，DB8/ZH7b 零迁移）。
- 渲染链补充实证：每字符 x 游标 += CharWidth 后再 += RSFont+0x18(kerning, 不随 scale 缩放)
  ⇒ 同串双份绘制（shadow/large 拷贝）在 v7 下 pitch 恒等 ⇒ 对齐重合。

**实测判定（gsrunner 6 次：DB10/ZH8b/DB11 各 快判+全跑，全部 exit=0、needle 4222、f150 首中）**
| 盘 | 内容 | 判定 |
|---|---|---|
| GR_DB10（v7+MENU_DB8=ZH7b 内容） | 9.6-1 复验 | f33480/f35030 vs DB8(v6)：仅 logo 动画区 1026px 差；vs ZH7b：文本逐像素一致（8x 复核=标注线相位），**两处「已定位差异」复验 = 徽章不在 Controller 页帧 + 相位抖动不影响显示** |
| **GR_DB11（v7+MENU_DB9 扫描串）** | 9.6-1 缺陷本体验证 | **v6 对行(60 对样)重影/拖影全部消除**，140 项（60 对抽样+76 单+4 尾对）全部清晰、无缺字/错字/dash（4x 条带目检 `db9v6_v7_rows_{0,1}.png`；右列 v6==v7 证明 default 面零损伤）；整帧 diff 9405px 全部落于被修的对行 |
| **GR_ZH8b（终盘）** | v7+759 字+1353 条 | probe ALIVE + 40000 帧 ALIVE；**300 快照随机普查（vs v6 同 nav）：123 帧字节一致、177 帧仅 logo 动画差、logo 外差异=0 → 无异常旗标**（survey300.json）；Name Entry f11718/Controller f33480 v6↔v7 仅 logo 差；左列标签与 default 面几何一致（宽:高 1:1） |

**运行与产物**：gsrunner 本阶段 8 次封顶（DB10/ZH8b/DB11 快判+全跑 6 + 浸泡 1 + 普通模拟器 1）；
实验盘 GR_DB10/DB11.iso 已删。产物：tmp\zh8b\{SLUS_P_V7.elf, build_PS_v7.py, sim_cave_v7.py
（全向量 PASS + 对 v6 ELF 判别力验证 fail=5）, dis_va.py, survey300.py, measure_aspect.py,
db11_judge2.py, run_soak_zh8b.py, MENU_ZH8b.img, db9v6_v7_rows_*.png, survey300.json}；
dump = dumps\{zh8b_db10, zh8b, zh8b_db11, zh8b_soak}。
**注**：真实菜单组件（Controller 标签/Name Entry 徽章/按钮栏）实测均走 scaleX=1.0 样式，
v6 下本就 1:1；1.64 拉伸实证存在于 large 样式长串 widget（DB9 类扫描盘对行）——v7 在
机制层修复该路径全部实例（含未在 nav 中出现的 选择A-D 徽章类）。9.6-1 即此结案。

---

## 十、边缘留白铁律（ZH11，2026-09-13）——字库网格 pitch 参数化 + 格间/格内 1px 留白

> 根因：用户报告「字形边缘杂色/邻字墨迹渗入」。ZH8/ZH9 网格 `NCOL,CW = 41,12` —— 水平
> 步距 = 格宽 12px，字形（Zpix 12px 墨 ≤11×11）从格起点 x 无内缩绘制，格间唯一 1px 空隙
> 恰为「右缝」，结构上无抗渗漏余量。产物：`tmp\zh11\`；终盘 `C:\gr_build\iso\GR_ZH11.iso`。

### 10.1 采样机制与渗漏模型（实测+机制双向实证）
1. GS 双线性采样点 = 像素中心 UV = `u0+(k+0.5)`，texel 对 = `floor(uv-0.5)` 与 `+1`
   → **quad 两端各以 0.5 权重溢出 1 texel**：采样域 = `[x-1, x+pitch)`。
2. ZH8 网格下右溢 texel `x+12` = 右邻格字形第 0 列（无内缩）→ 右边缘像素以 0.5 权重
   混入邻字墨列。该渗漏是否可见取决于 GS/模拟器双线性相位实现（「部分模拟器截图」）。
3. **结构审计**（`tmp\zh11\zh11_font.py` 4b 节同法回放 ZH8 atlas）：ZH8 759 格中 **740 格
   采样域内含邻格墨、渗墨 texel 合计 2680**（97.5% 格）；ZH11 = **0 格 / 0 texel**。
4. 竖向 CH=15 带 + 底边距 2px 本就安全（溢出域 [y-1, y+16) 全空白）；ZH7b「视角上下」
   v1=208 贴邻 huge 带的 8×2px 弱横条 = 同机制竖向特例（EN 区行间现已 +1px 缝隔离）。

### 10.2 铁律（font_build.py --mode v6 已内建，违者构建即断言失败）
1. **格间 ≥1px**：水平 pitch `cell_w ≥ 墨宽 + 2×margin`（ZH11：13 = 11+2）。
   列数上限 = `(512-X0)//pitch`，X0=20（记录坐标系 u0 = x-20 ≥ 0）→ pitch13 → **37 列**
   （39 列需 527px 不可达；网格起点 x=20 是下限不可左移）。
2. **格内 1px 内缩**：字形画在 `[x+margin, x+margin+iw)`（ZH11 margin=1），
   渲染 UV 带 = 整格 `[x, x+pitch)` → quad 边缘像素采样 texel 全为空白或本格字形。
3. **采样域闭环自检**：逐格断言 `[x-1, x+pitch) × [y-1, y+CH+1)` 内非本格墨 = 0
   （zh11_font.py §4b / font_build.py build_v6 内建）。
4. **pitch 参数化**：ELF cave 常量 `NCOL/CELL_W/CELL_H/Y0` 与字库网格同源参数化
   （build_PS_v8.py：NCOL 41→37、CELL_W 12→13；sim_cave_v8.py 全向量 PASS）。
   **字库网格与 ELF cave 必须同一张配方单**——ZH11 起 grid 参数写入
   charset_compiled_*.json 的 `grid` 块（ncol/cw/ch/gridy/margin/x0/en_y）。
5. **EN 区行间 1px 缝**：EN 两行 `en_y` 与 `en_y+CH+1`（445/461），行带间不再贴邻；
   CJK 末行 v1(443) 与 EN 首行(445) 间留 2px。
6. 网格 rows 128..443（21 行 × 37 列 = 777 ≥ 759）；禁写区 rows 0-127 与 CLUT rows 0-1
   照旧不可覆写（§9 铁律 2/3 不变）。容量重算：row0 上溢 texel 127 实测无墨、x<20 无墨
   → GRIDY=128 可保持。

### 10.3 ZH11 交付与实测
- 字库：tmp\zh11\{zh11_font.py → COMMON_PAK_ZH11.bin / ft_slot_zh11.bin
  / charset_compiled_zh11.json(含 grid 块)}；展开 5302B、payload 1337B、槽回环 PASS。
- 工具链收口：hanliu\tools\font_build.py `--mode v6 --grid-cols 37 --cell-w 13 --margin 1
  --grid-y 128 --en-y 445` 与 zh11_font.py 产物**逐字节一致**（sha256 对账 SAME），
  默认值即边缘留白铁律配方。
- ELF：SLUS_P_V8.elf = v7 + cave 常量（v7↔v8 差异 4B 全在 cave）。
- 盘：GR_ZH11.iso（GR_ZH9 基底换 ELF+MENU+GR 侧 FONT.RES/COMMON.PAK 两槽 → GR 侧
  字库与 cave 常量同步）、实验盘 GR_ZH11T.iso（MENU_DB11Z 扫描串）已删。
- 实测：扫描盘 probe ALIVE + 40000 帧 ALIVE（needle 4239）；扫描串 156 项
  XOR 对齐逐格判定：**水平（左/右环带）渗墨 = 0**，残余 7 项 1-2px 竖向 = 对齐误差级
  （结构采样域为 0，非网格渗漏）。结构审计前后对比：740 格/2680px → 0/0。

## 十一、ZH12 字库整体重建（2026-09-14）——face 恢复矩阵 + EN 墨迹窗口拷贝 + single 记录铁律

> 结论先行：**字库整体重建路线成立**。large face 与 atlas rows 0-131 恢复原版字节（EN/large
> 零损伤硬标准）、default/huge CH=17 与 cave CELL_H 对齐（Controller 标签对字 1:1）、CJK 网格
> 37 列×17px 行高 Y0=130 码位稀疏保留（GR 侧文本零重编码）、EN 101 码位 = 原版墨迹窗口拷贝。
> 产物 `C:\gr_build\tmp\zh12\`；终盘 `C:\gr_build\iso\GR_ZH12.iso`（ELF=SLUS_P_V10.elf）。
> 实战抓出并修复「single 记录 chr(c) 误判 → 76 字全空白」缺陷（§11.5 铁律 7）。

### 11.1 采样机制定案（dv=2，三重证据）
引擎采样矩形 = `(u0+20, v0+2) - (u1+20, v1+2)`——即 quad 记录 UV 整体 **+20/+2 texel 偏移**：
1. large band0（v0=0）排除 CLUT rows 0-1 被采；
2. default 带间 rows 104-105 空行隔离（v1-v0=26 > 17 采样高）；
3. 用户报告「下一行字形顶部被 quad 底边采进」只有 dv=2 成立（ZH11 ink@y+1 → 采样 [y+2,y+17)）。
⇒ 记录 v0 的语义 = 「采样窗顶 −2」：要采 [S, S+17) 就写 v0=S−2（EN 带 / SREC 均按此）。

### 11.2 face 恢复矩阵（ZH12 定案）
| face | fld | 记录 | atlas 域 | 来源 |
|---|---|---|---|---|
| large | **原版 verbatim**（fld[1]=26, 32×7=224 记录） | 原版 224 记录逐字节 | rows 0-131 整体原版字节 | `F0[0]`/`ORIG` 不改写 |
| default | fld[1]=17，32×7=224 | EN 101 码位→S 带记录；single 76→网格格记录；其余→SREC | rows 132-511 清底 + CJK 网格 + S 带 | zh12_font §4/§5 |
| huge | fld[1]=17，**16×6=96**（EN 别名，与 default 同格） | EN 0x20-0x7F 同 default | （共享 S 带） | 同上 |
- 容量含义：large 224 记录不动 ⇒ Name Entry 键盘/徽章/图标（large 采样）**逐位原版**；
  mSize=224 不变 ⇒ 全部 pair (idx≥224) 走 cave 直 UV，single (idx<224) 走 default 记录。

### 11.3 CJK 网格与容量表（37 列 × 13px，行高 17，Y0=130，rows 0-19 = 740 格）
| 域 | 格数 | 内容 |
|---|---|---|
| pair 码位槽 | 664 实存（域 683） | 裁 19 个 freq-1 且 GR 侧零冲突字（流卢巴脱宛陶残骸山斯俄农床荒约纽城泉温）→ GR 侧文本零重编码 |
| single 槽 | 76 | row18 col17-36（20）+ row19（37）+ 裁字孔位格（19）——恰好 76，零浪费 |
| EN S 带 | 101 码位 | A [473,490) / B [492,509)，尾部 8px + SREC 空格记录 |
- 容量公式：`pair ≤ 94×⌊(473−130)/17⌋`（lead 段全用 ~ 8×94=739 > 740 上限内）＋ single 借孔位；
  本次 683+76=759 字全量容纳且带间/格间全部 ≥2px 真留白。

### 11.4 EN 101 码位 = 原版墨迹窗口拷贝
- 窗口 = 原记录 `v0+6` 起 17 行、逐列 `(u0+20+k) % 512` wrap（原版 v0=104 组右缘溢出本就 wrap，
  原盘渲染即如此）→ **EN 渲染与原盘逐位一致**（验收 c 数据层+渲染层双判）。
- 组内基线保持（按原 v0 分组邻接排布）；`[ ]` 顶部 2 行裁剪（语料证明只出现在 PS2 永不渲染的 key_ 值）。

### 11.5 边缘铁律增补（§十 之外）
5. **DV=2 记录语义**：要采 [S,S+17) 记录写 v0=S−2（§11.1）。
6. **face 恢复矩阵不可混写**：large verbatim 域（rows 0-131）与 CJK 网格域（130 起）以
   inkm[130:133]=0 断言隔离；带间 [470,473)/[490,492)/[509,512) 空白断言。
7. **★single 记录码位逆映射（本轮实战铁律）**：default face 的 single 码位记录必须按
   `code2single = {code: ch}` 逆映射指向其网格格。**禁止 `chr(c)` 字符匹配**——c≥0x80 时
   `chr(c)` 是 Latin-1 字符、永不等于汉字键，76 条记录静默全落空格记录 SREC →
   **运行时 pair 全正常、single 全空白**（ZH12 首跑 Controller 页大面积丢字、开火/切换队员
   整行消失；数据层自检全绿——记录数/矩形不相交/采样域都不报错）。font_build v6/v7 已内建
   code2char/code2single 正确写法 + 6f 逐码位记录断言（防回归）。
8. **字库-ELF 配方单**：NCOL/CELL_W/CELL_H/Y0 必须与网格同源（ZH12=37/13/17/130，
   SLUS_P_V10.elf）；sim_cave 全向量 PASS 后才上盘。

### 11.6 ELF：SLUS_P_V10.elf（build_PS_v10.py）
- = V9 安全 cave（0x416ED0，§10 崩溃战役迁址）+ ZH12 网格常量（CELL_H 17 / Y0 130）。
- 五重自检：挂点原值 / [0x416EB0,0x4171DC) 三类引用 count=0 / 差异仅 cave+挂点且旧洞还原 /
  **vs V9 差异恰 3B** @0x4170D8/E4/E8（CELL_H 15→17、V0R 128→130、V0R+CH 143→147）/
  vs V8B 语义等价（cave 指令字 j/jal 重映射后逐字相同）。sim_cave_v10 全向量 PASS。

### 11.7 工具链收口（font_build.py --mode v7）
- `--mode v7 --charset charset_compiled_zh11.json --trim trim19.json --grid-cols 37 --cell-w 13
  --ch 17 --grid-y 130 --margin 1 --en-band-a 473 --en-band-b 492 --ttf Zpix.ttf --size 12
  --ttf-fallback SimHei.ttf` 与 zh12_font.py 产物**逐字节一致**：
  FONT_RES_slot / COMMON_PAK / expanded 三件 sha256 全 SAME（§11.5 铁律 7 内建防回归断言）。

### 11.8 验收（ZH12 实测，gsrunner，详见 PROJECT_STATUS §21）
| 项 | 盘/帧 | 判定 |
|---|---|---|
| R2 全 nav 40000 | GR_ZH12（V10） | **PASS**：跑满 exit=0（669s）；needle WPNRPK74 f150 首中 |
| a Name Entry 键盘 | zh12_ne / grk99_ne（冗余 nav 17200×2） | **PASS**：键帽字形逐位保真；键盘区内容差 456px 中 383px = 原盘固有带间渗墨（ZH12 无→改善）；页面其余差异全部为有意翻译（标题/确认/底栏） |
| b Controller 标签上下残迹 | R2 f33480, edge judge 67 字形 | **PASS**：左 0 右 0 下 0、上 10（4 字形对齐归因级：小×2=ZH11 同值、3、上）；ZH11 基线 top8/bot1 同为 4 字形；4x 视觉复核零可见残迹；水平 0 |
| c EN 保真 | R2 f33480 vs 原盘同帧 | **PASS**：880 条保留 EN 词条 = 877 条与原版逐位同 + 3 条 ZH11 既有改写（PING =/PING/MOD）；按钮图标带 diff=0 |
| d 码位抽扫 | GR_ZH12T（V10+DB12Z）33600 帧 | **PASS**：项 140（64 对+76 单）≥60；干净 130；渗墨 7（全部 1-2px 竖向 §19 已知类）；失配 0；ALIVE；aspW 均值 0.983（ZH11 同法 0.980） |
| 任务冒烟 T01 nav 30000 | GR_ZH12 | **PASS**：跑满 exit=0（502s）；needle 命中至 f29990（#3230）；**越过 f26575**；零野跳 |

## 十二、拉丁 Zpix 整体重绘 +「一」垂直对齐定案（ZH13，2026-09-14）

> 结论先行：用户报告的「英文字母水平边缘污染」根因 = ZH12 拉丁走「原版墨迹逐格拷贝带」
> （default EN S 带，组内 0px 邻接）与原版 large 紧排格——原生留白 1-2px 不规则，双线性
> 1texel 溢出必采邻墨。修复 = 拉丁全部 Zpix 12px 重绘、套用 CJK 同款网格规范（结构采样
> 域 0 外墨）；「一」显示成「_」= zh12_font 底锚贴图 bug（非映射）。产物 `tmp\zh13\`；
> 终盘 `C:\gr_build\iso\GR_ZH13.iso`（ELF=SLUS_P_V11.elf，vs V10 恰 2B）。

### 12.1 「一」→「_」定案（假设 a 成立：贴图垂直对齐）
- 「一」= single 0xC5 → 网格格 (20,453)，记录-格映射正确（ZH12 §11.5-7 断言通过）。
- 根因在 zh12_font.render()：墨迹 bbox 裁剪后**底锚** `A[y+CH-2-ih : y+CH-2]`——
  把字形钉在格底。全高字形（11px 墨）近似居中无碍；「一」墨仅 1px 高（Zpix 直绘
  rel y[4..4]）被钉到格底 → 渲染 = 字框底部横线 = 视觉 underscore。
- **修复 = em-strip 放置**：画布 rows[3,17)（rel 0..13，14 行）整体贴到 [y+3, y+17)
  （ink rel 底=13 的字——字表内唯一 µ——上移 1px），保留字形在 em 内的自然垂直位置。
  「一」→ y+7 格中部；拉丁 '-' 等矮字形同理受益（底锚下同为 "_" 化高风险组）。

### 12.2 拉丁 Zpix 重绘规范（与 CJK 同一网格铁律）
- 度量（PIL Zpix 12px draw(3,3)）：拉丁半宽 6px em，98 码位全覆盖（0x21-0x7E +
  ' `® ç ñ）零缺字；墨宽 ≤6（'_'），caps/digits 5×10，墨 rel 行域 [0..12]；
  Σpitch(墨宽+2)=624 ≤ 2×491 ✓。**记录 adv = pitch = 墨宽+2（band=pitch → 1:1）**，
  ink@x+1（格内 1px 内缩），texel 511 恒空白。
- **default EN A/B 带**（fld[1]=16）：S=452/468（采样顶；记录 v0=S-2, v1=S+14，
  采样窗 [S,S+16)），strip=[S+2,S+15)，ink ⊆ [S+2,S+14]；两带共 98 格（A 77 + B 21）。
- **large 键盘 C 带**（fld[1]=26 verbatim → 带高必须 26）：v0=482, v1=508（采样窗
  [484,512) 恰到纹理底、零 wrap），strip=[488,501)，44 码位 = A-Z + 0-9 +
  { _ . ! # @ - ? $ }（Name Entry 键盘实铺 9 列；$ 初版遗漏、终盘补入）。
- **冲突矩阵**（手工推导 + 程序断言双验）：CJK 网格采样窗末 [436,452) ↔ A 采样
  [452,468) ↔ B [468,484) ↔ C [484,512)，四窗零重叠零缝隙；ink 域 A[454,467]/
  B[470,482]/C[488,500]，带间空白行 (450-453 / 467-469 / 483-487 / 509-511) 断言。
- **huge**：fld[1]=16、16×6=96 记录 alias default EN（同 ZH12 结构）。
- B1(±)/B5(µ) 按钮图标 = DrawString 硬编码 UV 不吃记录 → verbatim 不动；
  default 的 B1/B5 记录仍 SREC（ZH12 同）。large 其余拉丁（小写/重音等 EN 文本
  不经 large 面的码位）保持 verbatim 原版（ticker 现全中文，残余暴露面为空）。

### 12.3 网格 CH 17→16 与 ELF V11
- 动因：default EN 两带(16×2) + large 键盘带(26) 需 60 行，rows 470-511 仅 42 行
  —— CJK 20 行 CH 17→16 释放 20 行（rows 130..449）；16px 采样窗 [y+2,y+18)
  对 11px 墨仍 1px 顶/5px 底真留白（740 字墨高分布 11×734/10×2/9×3/1×1）。
- SLUS_P_V11.elf = V10 同 cave 指令，常量 CELL_H 17→16 @0x4170D8、V0R+CELL_H
  147→146 @0x4170E8（V0R=130 不变）→ **vs V10 恰 2B**；vs V9 仍 3B；sim_cave_v11
  全向量 PASS（cctc 直 UV 期望值 130+16r / 146+16r）。

### 12.4 边缘铁律增补（接 §11.5）
9. **拉丁格 pitch = 墨宽 + 2×1px、adv = pitch、band = pitch**：与 CJK 铁律 1-3 同源
   （band≠pitch 引擎拉伸、band>pitch 溢出采样）；「同 face 带高一致」按 face 的
   fld[1] 分治——default/huge 16、large verbatim 域 26、large 键盘带 26，互不混写。
10. **em-strip 垂直语义**：CJK 与拉丁一律「画布 rows[3,17) 整体放置、水平裁墨」，
    禁止墨迹 bbox 垂直裁剪+底锚（「一」/「-」/「·」类矮字形 = "_" 化）。
    审计域 = 采样窗 ±1，且 CJK/EN/KBD 三类采样窗语义不同（y+2 起 / S 起 / v0+2 起）
    ——审计代码必须用采样窗坐标而非记录 v0。

### 12.5 验收（ZH13 实测，gsrunner 6 轮全 exit=0）
| 项 | 盘/帧 | 判定 |
|---|---|---|
| probe | 终盘 4300 | ALIVE：73s、needle f150 首中 673 次、快照非黑对齐历史 |
| R2 全 nav 40000 | 43 键轮（终盘 ELF/网格/EN 带全同，仅 $ 键一格差） | PASS：669s 跑满 |
| 码位抽扫 | GR_ZH13T 33600（已删，可由 zh13_iso.py 重建） | PASS：项 140 干净 129 / 渗墨 7（全部 1-2px 竖向 §19 已知类、水平 0）/ 失配 0（row19 锚 NCC 0.387<0.4 为 1px 高「一」模板算法性弱匹配，4x 目检 PASS） |
| Name Entry | 终盘 17200 | PASS：键帽 Zpix 44 码位清晰居中、与中文同风格；输入框 AAAA + 闪烁光标（簇分析 4 簇+caret）；原盘对比 = 有意变更（字形 Zpix 化、字号较原版小、原盘 S-Z 行下白点带渗墨消失） |
| T01 冒烟 30000 | 43 键轮（ELF 与终盘逐字节相同） | PASS：502s 跑满、needle 至 f29990 #3243、**越过 f26575 零野跳** |
| a EN 边缘（数据层） | zh13_en_audit.py | **default EN：ZH12 93/94 格 586 texel → ZH13 0/94 0；large 键盘：44/44 格 721 texel → 0**（采样窗 ±1 邻墨） |
| a EN 边缘（渲染层） | R2 f33480 edge judge 67 字形 | 水平（左/右）0、下 0、上 5（3 字形：小×2 t2、上 t1 = §19 对齐归因类，优于 ZH12 的 10px/4 字形）；L3键+◄► 4x 目检 crisp |
| c 「一」 | DB13Z row19「一对一」4x | PASS：两个「一」居字格中部、与「对」协调，「_」观感消除 |

### 12.6 工具链与遗留
- font_build.py `--mode v8`（--ch 16 --grid-y 130 --en-band-a 452 --en-band-b 468
  --kbd-v0 482 --kbd-v1 508）：三产物 sha256 与 zh13_font.py **逐字节 SAME**（$ 补入后复验）。
- 遗留：①Zpix 拉丁为 12px 本味设计（V/W 顶部有 serif 点、字号较原版键盘小约 40%）=
  「风格与中文统一」的有意变更；②large face 小写/重音域仍 verbatim（EN 文本不经
  large 面，实际暴露面为零）；③扫描盘 row19 LOWNCC 类（1px 高字形模板匹配阈值）
  为判定器已知弱项，目检兜底。

## 十五、完全扩容战役（ZH16，2026-09-14）——1212 字全语料覆盖 + 纹理扩容证伪与 512×512 CH13 反转

> 结论先行：**字库从 766 字扩到 1212 字（覆盖全部语料文字），全部塞进原 512×512 纹理**，
> 终盘 `iso\GR_ZH16.iso`（ELF=SLUS_P_V14.elf）。「无限扩容至包含所有文本文字」验收达成：
> corpus_menu 2232 条 + corpus_gr 2232 条零未译、零字表外字符。任务书的「pda 腾位纹理扩容」
> 被小盘实验**证伪**，反转布局（CH13）在 512×512 内达成同等容量。

### 15.1 纹理扩容证伪（GR_ZX2/ZX2B/ZX2D 三盘隔离，gsrunner 4 跑）
- COMMON.PAK 逐字节结构（实证）：`{u32 0}{u32 nl}{name}{8×u32 hdr: psm,w,h,0x410,0x8040,0x08000000,0,0}{CLUT 1024B}{w*h px}{尾 20B}`；
  arrow@0x0000 / new_font_revised(hdr@0x1049,CLUT@0x1069,px@0x1469) / pda-lcd-02(hdr@0x4148F,256×256) /
  pda_counterparts@0x518C3 / 尾 0x61D13。
- | 盘 | 内容 | 结果 |
  |---|---|---|
  | GR_ZX2 | font 512×608（头+数据一致）+ pda 128×128 缩+移 | 挂死 f257/LBA776661 全黑 ×2 |
  | GR_ZX2B | ZH14 字库 verbatim + 仅 pda 缩+PAK 缩小(表项 stored/real 同步) | 挂死 f256/776637 |
  | GR_ZX2D | ZH14 verbatim + **仅 pda 头 8 字节** 256→128 | 挂死 f257/776661 |
- 判定：**pda-lcd-02 描述符冻结**（仅改 w/h 即确定性挂死；IOP/引擎侧有 256×256 硬假设，
  cdvd 全部停在 PAK 读完成处=死于 PAK 消费段）。donor 缺失（pdc 需保图标、arrow 太小、
  MENU 侧 PAK 后邻 FONT.RES 仅 13B）→ **PAK 腾位路线废弃**。
- **勘误指针 (R4+, 2026-09-16)**：本节「描述符冻结/256×256 硬假设」已被
  `work/zh16b/FEASIBILITY_ANALYSIS_R4.md` §1.3 削弱——三份 run 日志自标 CDVD_STALL
  （模拟器层偶发，需重跑），不再作为先验结论；且本节记录格式（「8×u32 hdr」「px=w*h 无存储尺寸」）
  已修正为 `{flag,nl,name,psm,w,h,clut_size,clut_blob,px_size,px_blob,pad20}`
  （px_size@0x1469=0x40010，px 真实网格起 0x147D；本节 `px@0x1469` 是工具 SURF 帧，
  比真实网格早 20B），以 FEASIBILITY_ANALYSIS_R4.md §1.1 实测表为准。
- 连带收获：①font 512×608 自身未被证伪（stride 一致即可被目录步进接受）；②menu_orig 基底
  无罪（与 menu_working 的 FONT/PAK 槽逐字节同）；③LoadRSBFile(0x51C810) 头消费实证：
  mode≥4 读 w/h 低 16 位入 UITexture+0x10/+0x12（lhu），(2,2,2,2)→s1=4=8bpp+256 CLUT。

### 15.2 反转布局（512×512，CH13 全容量）
- 网格：Y0=2，NCOL=37，CW=13，**CH=13**，y(r)=2+13r+39·[r≥14]（r13 窗 [173,186)、
  r14 窗 [225,238)，跳过图标窗 [198,221)），行 0..32=33 行×37=**1221 格 ≥ 1212**（余 9）。
- 容量算术：690 既有 pair（slot≤706 冻结）+ 446 新 pair（slot 707..1152）+ 76 single
  （683..699×17 + 1153..1211×59）= 1212；CH16 需 608 行高（PH16×33+跳 32+EN 32）不可达，
  **CH13 是 512×512 内唯一全容量解**（CJK 墨 ≤11 行 zh13 实测 → 13 带内 1px 顶/2px 底真留白）。
- EN 带 13 高：A S=476（窗 [476,489)）、B S=491（窗 [491,504)）；记录 v0=S-2,v1=S+11；
  98 码位墨迹 = ZH14 带逐格提取重排（tall 墨 >12 行最近邻压 12；EN 带四周真间隙故 12 行安全）。
- face：large fld[1]=13（**1:1，顺带根治 ZH14 large 1.625× 拉伸**）、default 13、huge 16
  （s6 quad12/带13=0.92；s7 2×=ZH14 同）。
- 字体产品：tmp\zh16\{COMMON_PAK_ZH16.bin(400,659B 不变), ft_slot_zh16.bin(4421B,payload 1320B),
  ft_expanded_zh16.bin(5942B), charset_compiled_zh16.json, layout_zh16.txt, atlas_zh16.png}；
  自检全套 PASS：采样域渗墨 **0/1310**、记录矩形 174 两两不相交、EN98+single76 三 face 逐码位、
  code2single（§11.5 铁律 7）、CLUT/图标窗 verbatim、DP 槽回环。

### 15.3 ELF（SLUS_P_V14.elf）与记忆卡位图
- **V14 = V12 cave（结构同 ZH14）+ 常量 CH13/skip14+3（8 个常量字全对：37/13/13/0/13/14/3/15）
  + iconfix 0x219C10（1B）+ V13W DoWordWrap cave（0x21CD70 hook→j 0x417500，48 字）**。
  自检：双 cave 区零引用 / 差异越界 0 / 旧洞还原 / vs V12 与 vs V13W 双向对账；
  sim_cave_v14 全向量 PASS（fail=0）。
- **记忆卡提示根因新发现**：boot「Caution!…」/「Accessing…」/「Insufficient…」/「Unformatted…」
  四屏 = MENU.IMG 内 **EN_MESSAGE_MC_1..4.RSB 预渲染 8bpp 位图**（384×178，
  {mode=5}{w}{h}{2,2,2,2}+CLUT 1024B+表面 68,352B+尾 960B；s1=4=8bpp 路线，非 4bpp），
  RES 语料翻译对它无效（f310 对话框早于 f2811 的 RES 读取）。
  zh16_mc.py：4 张位图擦英文→SimHei 中文重绘（蓝 32,144,225 / 橙 500KB / ✕ 图标保留），
  68,352B 原位写回；实机验证 MC_4 boot 上屏中文（s16_mc3_check.png）。
- 教训：**位图文本是汉化覆盖率的隐藏层**——RES 全译 ≠ 全上屏；须按 boot 读盘序列
  （cdvd.log）核对每一张上屏图。

### 15.4 语料与验收（gsrunner 验收 4 轮 + 隔离 4 轮）
- 语料：corpus_menu.csv 2232 条→blob 32,362B（槽 47,570 余 15,208）；corpus_gr.csv 2232 条→
  GR blob 32,363B（槽 47,619）；5×ATR 人名（Trent Norris→特伦特诺里斯 等，pair 编码）；
  zh9 TXT 零改动（zh8 字表码位与 zh16 全量兼容实测：singles 76 逐一相同、pairs 逐一相同）。
- | 项 | 结果 |
  |---|---|
  | probe 4300 | ALIVE：exit=0、needle 541 f150 首中、58/67 非黑；boot EN 新带渲染正常 |
  | R2 40000 | **ALIVE ✓**：exit=0 669s、needle 4220（基线 4222 同量）；Controller 页 1:1（adv 13px/字、墨 11×11） |
  | T01 30000 | ALIVE：exit=0 500s、needle 3220、**越过 f26575**；I012/I021 全角标点版完整无孤字节（合法重排 3 行） |
  | 扫描 33600（GR_ZH16T+nav_menu） | **ALIVE ✓** needle 3580；判定 160 项（pair 99 含新扩字 28 + punct 7 + 尾 4 + single 60 + 一对一）：干净 157、渗墨 3（里/是/不 上 2px=§19 对齐归因类）、失配 0 |
  | a 抽验 ≥15 条 4x | evidence_zh16_4x.png + r2_sheet_c.png：boot MC×2、Controller 16 条、输入名字/确认、MC 提示(是/否)、主菜单 7 条（含特别收录）、训练 1-7+越野训练、I012/I021 全文 |
  | b 人名 | ATR 5 名 pair 编码写回 + 语料教程文本修正（zh16c names_fixed）；编码管线与本轮全量语料同管线 |
  | c 码位抽扫/比例/边缘 | 160 项 ≥80 ✓（含新扩字 28）；1:1 ✓（模拟器+屏显测量）；边缘：数据层 0/1310 + 扫描 157/160 干净 |
  | e PDA 影响 | **零**（pda-lcd-02 verbatim 不动——纹理扩容证伪的正面收益） |
- 容量终局数字：**1212 字（pair 1136 + single 76）≥ 全部语料用字；上限 = 33 行×37=1221 格
  （+9 空闲），编码域 pair 1222+single 76=1298 未用满（受 512×512 纹理所限，非编码限制）**。
- 遗留：①16px 档与 1221+ 字需新宿主（4bpp 1024 宽 / 新 PAK 条目 / VFS 破解，见 §八.2）；②MC_1..4
  仅译 EN 系（FR/DE/ES/IT 同名位图未动，系统语言 EN 不消费）；③扫描判定 3 项上 2px 为已知归因类。

## §十六 CH13 墨迹放位修正: v0 行污染 = 全局顶部渗墨 (2026-09-15)

- **现象**: ZH16 用户实测所有中文顶部 1px 孤立墨线 (英文/符号正常)。
- **根因**: CH13 (pitch 13) 墨迹 +3 放位 + 11px 墨 → 墨底 y+13 = 下格记录带 v0 (带=整格
  y..y+13)。引擎整带采样拉伸 → 每字 quad 顶部画出上邻字的墨底行 (1136 格实测平均
  5.29 外来墨 texel/格)。CH16 时代 (pitch 16) 墨底距下格 v0 有 3 行 → 结构性无此问题。
- **审计盲点**: 采样域审计窗锚 y+2 起未覆盖 v0 行 → 0/1310 假阴性; 判定扫描窗锚字墨,
  孤立线在墨顶上方 2-3px 多数漏判 (仅里/是/不 撞进容差被判)。
- **修复铁律 (★★ 新)**: **带内偏移 (ink_top − v0) 必须全 face 一致, 且 v0 行与 v1−1 行
  必须留空**。CH13/pitch13/墨11 下唯一解 = 偏移 +1 (墨 [y+1,y+11], 上邻墨底 y-2,
  下格 v0 y+13, 双侧 2 行净空); +2/-0.5 相位半渗, +3 结构污染。EN 带 (v0=S-2) 墨同步
  S+1→S-1 对齐 +1 —— **任一 face 单独改偏移 = 混排行基线错位** (EN 相对 CJK 低 2px 实测)。
- **流程教训**: 字库产物被 GR 侧 (zh16_gr) 与 MENU 侧 (zh16_menu) 双向消费——改字库必须
  四链全跑 font→gr→menu→iso; 漏 menu = 前端旧字 (渗墨"仍在"假象)。
- 修复后: v0 行外来墨 0/1136; 前端标签/底栏/教程框孤立墨线全部消失 (dump_fix2/
  dump_fix2t01); 混排行基线对齐。既有边缘案例: I012 L1 行尾「整」落盒裁剪边界渲染
  残影 (B 轮已存在, 语料重编码折行点位移所致, 非墨迹回归)。
- **补充 (同日二轮)**: ①copy_ink 改**整带绝对拷贝** [src_y+2,+15)→[y,+13)——bbox 重锚会
  把 ZH14 手工校正的标点位 (句号/逗号左下) 搬上带顶 (=用户实测"标点靠顶"); ②draw_fresh 改
  基线锚 (墨底统一 y+11); ③按钮类 UI 文字低 ~4px = 引擎文字对象 Y (CJK 字面高于原 EN 设计),
  非字体层可修 (+1 已回收 2px); ④**字库产物三消费方: GR 侧 (zh16_gr) / MENU 侧 (zh16_menu)
  / 开机 MC 位图 (apply_mc.py)——重建流水线 = font→gr→menu→apply_mc→iso 五步, 缺一即回退**。
