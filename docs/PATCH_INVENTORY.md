# PATCH_INVENTORY.md — 汉化补丁全量清单 (逐字节核实版)

> 生成: 2026-09-23 · 目的: 回应"先前的各轮操作对这个补丁有了混乱的修改"的怀疑 —— 把**当前终盘
> GR_ZH56** 里每一处改游戏的东西 (ELF 词补丁 / 数据资源 / 字体纹理) 逐字节核对后登记在案,
> 标明位置、语义、来源轮次与现状, 并把**已回退/已废弃**的东西单独列出防止被再次套用。
>
> **核实方法**: 本文档不是抄旧报告。全部结论出自对现役盘的字节级 diff:
> - ELF: `work/zh16b/subagent_inventory/verify_elf_diff.py` (GR_ZH56 vs GR_EN_ORIG 全 37MB 逐 4 字节词 diff, 恰 **375 词**, 与逐级中间盘链 diff 归因到轮);
> - 数据: `verify_img_diff.py` (MENU.IMG 686 条目逐条比对 + GR.IMG 1.55GB 流式全字节 diff 并映射到条目);
> - 字体: FONT.RES 经 LZO 解码后逐 face 解析; COMMON.PAK 8 段 GIF 结构与 CLUT 节点逐字段断言;
> - 机器可读全表: `work/zh16b/subagent_inventory/elf_diff_zh56_vs_en.txt` (375 行 VA/旧词/新词)。
> VA→文件偏移映射 = 各构建脚本在用的 `file_off = 295*2048 + 0x80 + (VA − 0x100000)` (该映射由每轮
> 构建脚本的 `cur==want` 断言背书)。

---

## 〇、一句话总览

**当前终盘 = `build/iso/GR_ZH56.iso`**, sha256
`fc4f242bdef46c85229303394d4662ee9f1a1a3b4552892867e89a601cdbbfae` (1,648,164,864 B)。
谱系: EN 原盘 → (hanliu zh7/zh9 数据层) → zh16b 16px 字库管线 → GR_ZH31 → ZH36/37E/38/40/41A/43 → ZH49 → ZH50 → ZH55 → **ZH56**。

ELF 侧共 **375 个差异词** (0x1FF8D0–0x578070, ELF 头 0x80B 与 0x578070 以上零改动),
全部归因到下表六个子系统; 数据侧 MENU.IMG **25 条目**、GR.IMG **8 处** (7 条目 + 头部 12B)。
核对结论: **没有发现"失控"修改** —— 每一处差异都能对应到一个入库脚本的补丁表或一个有报告的轮次;
真正的"混乱"是历史上多轮加加减减留下的**尸体** (见 §三), 它们已全部确认不在 ZH56 里。

各盘 sha256 (均为 1,648,164,864 B):

| 盘 | sha256 | 状态 |
|---|---|---|
| GR_EN_ORIG | 2b42ea7ce9bd0a85… | 对照基准 |
| GR_ZH31 | 13f68ef5cb9c7af4… | 13px 终盘 (备选) |
| GR_ZH43 | 6869254528fe5262… | 黑屏问题盘 (已被 ZH49 取代) |
| GR_ZH49 | a772f958adef8fbe… | 黑屏修复盘 |
| GR_ZH50 | bb62ee7ecb097bbe… | + 最近邻过滤 5 词 |
| GR_ZH55 | 07e05cf6b453d4ac… | + 10 词/cave, ELF 与 ZH56 完全相同 |
| **GR_ZH56** | **fc4f242bdef46c85…** | **终盘** (ZH55 + EN_STRINGS.TXT 数据修复) |

---

## 一、ELF 补丁全表 (GR_ZH56 vs EN, 375 词, 按 subsystem 分组)

### A. 中文绘制系统 (DBCS 16 位 ABI + 字形度量 cave) —— zh16b V12/V13W/V14 世系, ZH31 起全部在役

| 位置 (VA) | EN 词 | ZH56 词 | 语义 | 引入 | 现状 |
|---|---|---|---|---|---|
| 0x219BCC | 0C102FF2 | 0C105BB4 | DrawString 主循环 ds16 hook → `j 0x416ED0` (ds16 cave) | V14 世系 (任务一, PROGRESS §1-13) | ✔ 在役 |
| 0x219BD0 | 27A400DF | 27A400DE | 槽位取数 `addiu a0,sp,0xDF→0xDE` | V14 | ✔ |
| 0x219BD4 / 0x219BE4 | 83A500DF ×2 | 97A500DE ×2 | `lh→lhu` (槽位符号扩展修复, v4) | V14 | ✔ |
| 0x219C08 / 0x219C10 / 0x219C14 | 2403FFB5/FFB5/FFB1 | 240300B5/B5/B1 | µ/± 图标字立即数 (符号扩展→零扩展) | V14 | ✔ |
| 0x219C94 | 2403FFB5 | 240300B5 | 同上 (第二站点) | V14 | ✔ |
| 0x219CAC | 2403FFB1 | 240300B1 | 同上 | V14 | ✔ |
| 0x219D24 / 0x219D38 | 2402FFB5/FFB1 | 240200B5/B1 | 同上 (DrawString2 站点) | V14 | ✔ |
| 0x219CA0 | 83A400DF | 97A400DE | `lh→lhu` #3 | V14 | ✔ |
| 0x219DAC / 0x219DB0 | 00000000/26100001 | 93A200DD/02028021 | ds16 槽位读回改写 (`lbu v0,0xDD(sp)` / `addu`) | V12-V14 | ✔ |
| 0x21AC74 | 0C086B44 | 08105C54 | StringWidth hook → `j 0x417150` (sw cave) | V14 | ✔ |
| 0x21AD18 / 0x21AD1C | 90820024/10400003 | 08105BD0/00000000 | CharWidth hook → `j 0x416F40` (cw cave), 延迟槽 nop | V14 | ✔ |
| 0x21ADE0 / 0x21ADE4 | 8C8A0028/30A300FF | 08105C14/00000000 | ComputeCharTextureCoords hook → `j 0x417050` (cctc cave) | V14 | ✔ |
| 0x21CD70 / 0x21CD74 | 8EA20098/27A400F8 | 08105D40/8FA400FC | **DoWordWrap 内部 hook → `j 0x417500`** (pair-aware 折行, V13W 唯一改动; `FINAL_ELF.md`) | V13W (2026-09-14 定版) | ✔ |
| 0x21CDD4 | 72C03E28 | 02403821 | wrap 配套 | V13W | ✔ |
| 0x21CECC | 24420001 | 00000000 | wrap 配套 | V13W | ✔ |

**Cave 体** (EN 里是死代码, 差异 185+45 词; 逐指令语义见 `archive/elf_lineage/` 各 ELF 与 `subagent_zh41/verify_patch_sites.txt`):

| Cave 区间 (VA) | 词数 | 身份 | 备注 |
|---|---|---|---|
| 0x416ED0–0x416F3F | ~ | **ds16 cave** (字节→16 位合成) | hook 0x219BCC |
| 0x416F40–0x41704F | ~ | **cw cave** (CharWidth, pair-aware 步进 2) | hook 0x21AD18; ZH37E 把其中 13→16 (0x416FBC: 2402000D→24020010) |
| 0x417050–0x41714F | ~ | **cctc cave** (UV 计算, w62: 0x4170AC 0x25→0x3E 为 V17 遗产) | hook 0x21ADE0 |
| 0x417150–0x4171CF | ~ | **sw cave** (StringWidth) | hook 0x21AC74 |
| 0x417200–0x417218+ | ~ | **V18B 四边形高 cave** (见 B 组) | hook 0x219ADC |
| 0x417500–0x4175BC | 45 | **V13W DoWordWrap pair-aware cave** | hook 0x21CD70 |

16px 化时 (ZH32B→ZH36 谱系, V16/V17/V22/V23 + ZH37E) 上述 cave 内 **8 个布局常量** 13px→16px 重调
(ZH31→ZH43 链实测): `0x416FBC` (0D→10, ZH37E 一字修复), `0x4170AC` (25→3E), `0x4170C4` (0D→10),
`0x4170D4` (0D→10), `0x4170D8` (0E→0C), `0x4170EC` (0D→10), `0x4170FC` (0F→12), `0x41720C` (0D→10)。

### B. 四边形高/行距 (V18B + V19 + ZH55 修 正) —— 布局/居中族

| 位置 (VA) | EN 词 | ZH56 词 | 语义 | 引入 | 现状 |
|---|---|---|---|---|---|
| 0x219ADC | 44820000 | 08105C80 | DrawString 内层 CharHeight 消费点 hook → `j 0x417200` | V18 (ZH31), 洞体 V18B | ✔ 在役 |
| 0x417200… | (死代码) | `li v0,0x1A; bne…; … li 0x10…` | **V18B quad cave**: 字形四边形高 CH==26→16 (16px 字形 1:1 不拉伸) | V18B (ZH31); 13→16 常量随 16px 轮 | ✔ 在役 |
| 0x21BD68 / 0x21BD6C | 24020012/AE0200F8 | 08105DA0/00000000 | RSHTML::SetText 行距 trampoline → `j 0x417680` | V19 (ZH31) | ✔ 在役 |
| 0x21C048 / 0x21C04C | 8E2600A8/2402FFFF | 08105D94/00000000 | 装载路径 trampoline → `j 0x417650` | V19 | ✔ |
| 0x21CFD8 / 0x21CFDC | 92030108/14600005 | 08105DAC/00000000 | Recalc 路径 trampoline → `j 0x4176B0` | V19 | ✔ |
| 0x417600–0x417678 | (死代码) | CLAMP 函数体 | **V19 行距 clamp cave**: f8 = max(原值, CharHeight) | V19 (ZH31) | ✔ 在役 (常数已改, 见下行) |
| 0x417620 | 0C1046BC | 24020010 | clamp 内 `jal CharHeight` → `li v0,16`: 语义改为 **f8 = max(原值, 16)**, 简报滚动面板行距还原 EN=18 | ZH55 (REPORT_offsets P0 方案) | ✔ 在役 |
| 0x417650 / 0x417680 / 0x4176B0 | (死代码) | 跳板体 | V19 三跳板 (a1=18 → CLAMP → 回跳) | V19 | ✔ |
| 0x21CB28 | 54200004 | 54200037 | style-0xC 块 bnel 改跳 → 0x21CC08 | ZH43 | ✔ 在役 |
| 0x21CC08 | 00000000 | 081045A4 | `j 0x411690` (行数守卫 cave) | ZH43 | ✔ 在役 |
| 0x411690–0x4116A4 | 00000000 ×5 | 24020002/14C20002/—/2484FFF6/080872CF ×2 | **ZH43 外科 cave**: 仅"2 行 0xC 块"块高 52→42, 其余行数走原路 | ZH43 (`REPORT_zh43.md`; 注: 报告写"8 词", 实测与 EN 差 **7 词** — 0x411698 延迟槽 EN 本为 0) | ✔ 在役 |
| 0x21CB30 | 0C086B34 | 0C105DA8 | style-0xC 居中 `jal CharHeight(0x21ACD0)` → `jal 0x4176A0` (CAVE16 假 CharHeight 恒 16) | ZH55 | ✔ 在役 |
| 0x21CB40 | 00641823 | 00641823 (=EN) | ComputeDrawXY 盒居中共享指令 (**保持 EN**) | — (ZH53 曾改 −21, ZH54 还原) | ✔ =EN (勿动: font==0 路径共享, 见 §三) |
| 0x4176A0 / 0x4176A4 / 0x4176A8 | 27BDFF70/FFB10050/FFB30070 | 24020010/03E00008/00000000 | **CAVE16**: `li v0,16; jr ra; nop` (16B 全零区假 CharHeight) | ZH55 | ✔ 在役 |
| 0x21D940 | 00621023 | 2462FFEB | 前端按钮 (IkeBaseButton style 0xC) 盒居中 K=21: `subu v0,v1,v0` → `addiu v0,v1,-21` | ZH40 (用户认证的 EN 对齐口径) | ✔ 在役 |
| 0x1FF8D0 | 00621023 | 2462FFEB | IkeButton3 (双行大按钮) K=21 | ZH55 (REPORT_offsets P1) | ✔ 在役 |
| 0x2071B4 | 00621023 | 2462FFF0 | IkeKeyMapButton (控制器说明页) **K=16** 几何居中 | ZH55 (ZH54 决策) | ✔ 在役 (副作用: R3 行下沉, 见 §五) |
| 0x216578 | 26270003 | 26270005 | IkeFontTable 字母 rowY+3→+5 (16px 墨在 26px 格内居中) | ZH55 | ✔ 在役 |

### C. 纹理过滤 (最近邻) —— ZH50 集

| 位置 (VA) | EN 词 | ZH56 词 | 语义 | 引入 | 现状 |
|---|---|---|---|---|---|
| 0x219FF4 / 0x21A0F8 / 0x21A1C4 / 0x21A2C4 | 24050001 ×4 | 24050000 ×4 | RSFontMgr (AddOneWord/Flush/Draw/Draw2) 延迟槽 `li a1,1→0`: 字库路径 SetLinearSampling(false) | ZH50 (`subagent_texfilter/build_zh50.py`) | ✔ 在役 |
| 0x519AC8 | 10C30054 | 00000000 | UIPacket::SetLinearSampling 状态缓存早退 `beq→nop` (否则传 false 被缓存早退吞掉) | ZH50 | ✔ 在役 |

### D. GS/CLUT 发射层 —— V22 的教训 (现为 EN)

| 位置 (VA) | EN 词 | ZH56 词 | 语义 | 历史 | 现状 |
|---|---|---|---|---|---|
| 0x5182EC | 14830005 | 14830005 (=EN) | SetTexturePkt CLUT 形状选择 `bne a0(psm),0x13` | ZH32 时代 NOP (V22, `build_zh32b.py:24-27`) → **ZH49 恢复** (`build_zh49.py:31,57`) | ✔ =EN。**NOP 是黑屏根因, 永久禁再 NOP** |

### E. 杂项 (misc)

| 位置 (VA) | EN 词 | ZH56 词 | 语义 | 引入 | 现状 |
|---|---|---|---|---|---|
| 0x577FA0–0x578070 | "Chargement en co…"(法/德/西/意/英 载入屏等 8 条 UI 串) | DBCS 标记制中文串 (lead∈{A1,A2,A3} 码) | ELF .rodata 载入屏/等待提示文案汉化 | hanliu ZH7 世系 (SLUS_P_U 以来, ZH31 已含) | ✔ 在役 (41 词) |

### F. 词数对账

| 组 | 词数 |
|---|---|
| A 中文绘制系统 hooks+caves (含 8 个 16px 常量) | 253 |
| B 四边形高/行距/居中 (V18B/V19/ZH40/ZH43/ZH55) | 55 |
| C 过滤 5 词 | 5 |
| D 0x5182EC | 0 (=EN) |
| E rodata 串 | 41 |
| 其他单点 (0x1FF8D0/0x2071B4/0x216578 等已计入 B) | — |
| **合计** | **375** ✓ (与全盘 diff 精确吻合) |

---

## 二、数据侧修改全表 (MENU.IMG @LBA 776286 / GR.IMG @LBA 19175)

### MENU.IMG (686 条目中 25 条与 EN 不同; 全部条目表字段除 EN_STRINGS.TXT 外未动)

| 条目 [#idx] | 改了什么 | 来源轮次/脚本 | 现状 |
|---|---|---|---|
| FONT.RES [#4] | 槽内原位覆写 (4,421B, real=7,222 不变)。当前内容 = **16px ft**: large/default 各 224 记录 fld[1]=26, huge 96 记录 fld[1]=16 | zh16 管线 → V17 (`work/zh16b/subagent_16px_fix/ft_slot_v17.bin`, **逐字节等于现盘**) → 随 ZH32B/ZH36 上盘 | ✔ 在役 |
| COMMON.PAK [#3] | 槽内原位覆写 (400,659B 恒长)。层叠: ①16px PSMT4 图集 (gen_font16) ②**8 段自闭合 GIF 拆传** (`subagent_split/make_pak_v21.py` → COMMON_PAK_V21.bin) ③root2 菜单图集**每行左移 2B**(4 texel) 修前端 4px 位差 (ZH38) ④▲▼/ñ 三格重绘 (ZH41A) ⑤**字库 CLUT 节点 NLOOP 0x40→0x04 ×2 副本** (ZH49) | subagent_16px → subagent_split → subagent_root2 → build_zh41a.py → build_zh49.py | ✔ 在役。已逐字节验证: 8 段全 NLOOP/EOP=1 自闭合 ✓; CLUT 节点 (psm=0x14,1024×512,clut=0x410) MENU 份 @MENU+0x58459 与 GR 份均 = 0x04 (ZH43 为 0x40) ✓ |
| EN_STRINGS.RES [#25] | 8 子流 LZO1X 框架内重编码 593 条中文 (47,570B 槽不动) | hanliu ZH7 (`tools/hanliu/tools/text_replace.py`) | ✔ 在役 |
| *_MESSAGE_MC_1-4.RSB ×20 (DE/EN/ES/FR/IT) | 记忆卡屏 5 语言消息汉化 (69,404B 恒长) | hanliu ZH7 | ✔ 在役 |
| EN_SPECIAL_FEATURE.XML [#283] | 特别收录文本汉化 (49,700B 恒长) | hanliu ZH7 | ✔ 在役 |
| EN_STRINGS.TXT [#30] | **曾损坏, ZH56 修复**: zh9 TXT 路线时代被写为管线测试半成品并迁址到 off=0x378A000 (stored=6971/real=6933, 明文非 LZO, `WPN_M4`='M4'+UTF-8 乱码, WPN_M1911 空值) → 游戏键查找全失败 ("!find key")。ZH56 用 EN 原条目 raw 2749B 原位还原 + 余量清零, 条目表 stored→2749/real→6930 | 破坏: zh9 TXT 时代; 修复: `subagent_findkey/build_zh56.py` | ✔ 已修 (数据=EN 原字节, sha b6263d56…; 键值仍为 EN 文本) |

### GR.IMG (流式全字节 diff: 5 个差异区段; 除下述外与 EN 逐字节相同)

| 位置 | 改了什么 | 来源轮次 | 现状 |
|---|---|---|---|
| EN_STRINGS.RES [#902] | GR 份中文 RES (47,619B 槽不动) | hanliu ZH7/zh9 (显示优先级: 教程/简报/任务读 GR 份) | ✔ 在役 |
| FONT.RES [#906] | GR 份 FONT.RES 同步覆写 (**死拷贝** — 字体系统只读 MENU 份, R5 轮定案) | zh9/zh16 (gr_spans 白名单同步) | ✔ 在役 (无害冗余) |
| COMMON.PAK [#3451] | GR 份 PAK 同步副本; **ZH49 的 CLUT 节点 2B 修复双副本都打了** (实测 GR 份=0x04) | zh16 起同步纪律; ZH49 | ✔ 在役 |
| RIFLEMAN-01/11/48/58/59.ATR (5 条) | 人名汉化 (ATR=纯 XML; 注意铁律: 乱改 ATR 名曾致指令面板打不开) | zh9 (`gr_spans_zh16.json` 白名单 5×ATR) | ✔ 在役 |
| STRINGS.TXT [#917] | **迁移+改写**: off 0xCB37190 (LZO 2587/6561) → 追加到 0x1CAC2000 (未压缩 6090/6090) | zh9 TXT 路线产物 | ⚠ 死数据: TXT 值从不被游戏显示 (T2 定案), 条目表字段被改属历史既成事实, 无显示影响; 与头部 0xB438-0xB444 的 12B 表指针差异同为该迁移副作用 |
| EN_STRINGS.TXT [#903] | — | — | ✔ 与 EN 逐字节相同 (build_zh56 所述已证实) |

### 字体数据语义摘要 (现盘实测)

- FONT.RES (MENU 份, LZO 解码 5,942B): 3 face —— large(default) 224 记录 fld[1]=26/fld[13]=26;
  huge 96 记录 fld[1]=16/fld[13]=42。采样矩形 `(u0+20,v0)-(u1+20,v1)`、adv 1/256px 等铁律见
  `docs/han_v2/HANIZATION_MANUAL.md` §三 (其中 u 恒 +20 为 13px 口径; 16px 图集绘制原点 X0=4,
  root2 行左移后前端采样窗 [16c,16c+16))。
- 字库纹理 = PSMT4 1024×512, **8 段自闭合 GIF 拆传** (每段 [48B 头][PT NLOOP=1][A+D TRXPOS][IT EOP=1][≤64KB 行数据]×8+尾 tag), blob 恒 0x40010 (alloc 铁律), PAK 总长守恒。
- CLUT 节点: 80B/16 项声明 (NLOOP=0x04) —— 依据: 字库像素全盘实测只用调色板索引 {0,1}。

---

## 三、历史遗留与冲突 (改过又改回的 / 死的 / 勿再套用的)

以下每一项都已在 ZH56 字节上复核过"当前状态":

1. **0x5182EC (CLUT 形状闸门)**: ZH32 时代被 NOP (V22, 为让 4bpp 字库 CLUT 走 1040B 大节点) →
   ZH49 恢复 EN 原词 0x14830005, 改用"字库 CLUT 节点 NLOOP 0x40→0x04"达成同一目的。
   **NOP 副作用 = 简报页整屏黑 (PSMT4+16 项资产被强制大形状 → GIF 失步)。勿再 NOP。** 当前 = EN ✓
2. **TEX1 三站点 5 词 (0x4501EC/0x450210/0x44E3D4/0x44E4BC/0x44E4C0)**: ZH53 加入 (简报 ctx1 残留
   双线性封堵) → **ZH55 删除** (作用于所有 CBmpObject 绑定 → 地图等全部 2D 纹理丢双线性, 用户实测
   锯齿; ZH55 改从 ZH49 重建)。当前 5 处全部 = EN 原词 ✓ (build_zh55.py:60-63 断言 + 本轮复核)。
   **勿再套用 REPORT_zh53 §三的这三站补丁。**
3. **0x21CB40 (ComputeDrawXY 共享指令)**: ZH53 P1 改 `addiu v1,-21` → ZH54 还原 EN (font==0 路径
   共享该指令, 读卡界面整体下移 +10.5px)。当前 = EN 00641823 ✓。**勿再改; style-0xC 居中改走
   0x21CB30→CAVE16。**
4. **0x4175C0 "CharHeight ×17/16 cave"**: 丁轮 (13px 时代) 方案遗产。**实测当前谱系所有盘
   (ZH31→ZH56) 该地址均为 EN 原词 AFA00018 —— 不存在**, 16px 布局走 V18B(quad 16)+CAVE16+K 常量,
   与 ×17/16 无关。见到旧文档提"×17/16 cave"一律以本文档为准。
5. **旧手册的 cave 地址 0x26BEA0–0x26C18F (hanliu SLUS_P_U 时代)**: 现役谱系**不含**该区任何改动
   (全盘 diff 0x26BEA0 段 = 0 差异)。现役 cave 全部在 0x411690 / 0x416ED0–0x4176AC。
   `docs/han_v2/HANIZATION_MANUAL.md` §2.2 的 cave 地址对现役盘已过时 (其余铁律仍有效)。
6. **ZH54 (26903fb0…) 是旁支**: ZH55 不是在 ZH54 上继续, 而是从 **ZH49 重建** (build_zh55.py:25),
   ZH54 的 TEX1 站点词被弃、其 K=16/CAVE16 决策被保留。**不要再拿 ZH54 当基底。**
7. **ZH43 是问题盘**: 其 0x5182EC=NOP 即黑屏根因, 已被 ZH49 取代; ZH43 的数据侧 (PAK 节点 0x40)
   也被 ZH49 更新。留档勿用。
8. **SetLinearSampling "空操作"误判**: round11 (ZH53) 曾据简报窗寄存器流断言 ZH50 的 5 词无效,
   round12 (ZH54) 撤回 (菜单/开机走另一提交路径)。**当前 5 词在役**, 引用结论时以 REPORT_zh54 §① 为准。
9. **13px 时代资产已全面退役**: FONT.RES (ZH31=6f93e96f…) / PAK (c2e07551…) 均已被 16px 版取代
   (25cb23fd… / fa8d372e…)。GR_ZH31 仅作 13px 备选盘保留。
10. **zh9 TXT 路线尸物**: GR.IMG STRINGS.TXT 迁移改写 + MENU EN_STRINGS.TXT 迁址 (后者内容损坏,
    ZH56 已还原 EN 字节)。TXT 值从不显示 (T2 铁案), 这两处是**死数据**, 除非做武器名 CJK (§五.5)
    否则不要再碰 TXT。
11. **计数口径差异 (文档级, 非盘级)**: REPORT_zh43 称外科补丁"8 词", 实测与 EN 差 7 词
    (0x411698 延迟槽 EN 本为 0); REPORT_offsets 建议的 P1 三词中 0x21CB40 已弃, 仅 0x2071B4/0x1FF8D0
    上盘且 0x2071B4 用的 K=16 而非建议的 K=21 (用户几何居中决策, REPORT_zh54 §②③)。
12. **K 口径并存 (有意但需知晓)**: 按钮族 = K=21 (EN 对齐, 0x21D940/0x1FF8D0); 标题/控制器族 =
    K=16/CAVE16 (几何居中, 0x2071B4/0x216578/0x21CB30)。两口径相差 2.5px, REPORT_offsets 曾警告
    勿混用 —— 现状是用户在 ZH54/55 主动选择的混合, 不是事故; 新站点补 K 前先问用户要哪个口径。

---

## 四、复现链 (从零到 GR_ZH56)

基底: `build/bases/GR_K99.iso` (= EN 原盘 + hanliu 时代 ISO 拼接基底); ELF 谱系存档:
`archive/elf_lineage/SLUS_P_U → V23 → V43`。

```
[层1 数据: hanliu 管线]  tools/hanliu/tools/
  export_texts.py → 翻译 CSV
  text_replace.py (RES 8子流重编码 / TXT / ATR)      → EN_STRINGS.RES, *_MESSAGE_MC_*.RSB, EN_SPECIAL_FEATURE.XML, STRINGS.TXT(zh9,死)
  font_build.py + ft_dpc.py                          → (zh7/zh9 字库, 已被 16px 层取代)
  make_iso.py / splice_iso.py                        → K99 基底 + MENU 数据层
[层2 GR 区迁移]  work/zh16/zh16_iso.py + gr_spans_zh16.json
  GR.IMG 区 = ZH12 整区迁移 + 白名单三槽 (FONT/PAK/RES) + 5×ATR
[层3 16px 字库]  work/zh16b/subagent_16px/gen_font16.py (方正像素16 → 4bpp)
  subagent_16px_fix/ft_slot_v17.bin                  → FONT.RES (现盘逐字节=此件)
  subagent_split/make_pak_v21.py → COMMON_PAK_V21.bin (8 段拆传)
[层4 数据修复轮]
  subagent_root2 (ZH38): 图集行左移 2B     build_zh41a.py (ZH41A): ▲▼/ñ
  subagent_findkey/build_zh56.py (ZH56): EN_STRINGS.TXT 还原
[层5 ELF]  (现役 = ZH49 后未再改, 亦即 archive/elf_lineage/SLUS_P_V43.elf)
  build_PS_v5.py (U) → V12(图标) → V13W(DoWordWrap 0x417500) → V14(ds16/cw/cctc/sw)
  → V16/V17(16px 常量) → V18B(0x417200) ∪ V19(0x417600 三跳板) = V20 (ZH31)
  → V22(0x5182EC nop, 已废) ∪ V19 ∪ V18B = V23 (ZH36) → ZH37E(+1 词 0x416FBC 13→16)
  → ZH40 (build_zh40.py: 0x21D940 K=21) → ZH43 (外科 cave 0x411690, REPORT_zh43)
  → ZH49 (build_zh49.py: 0x5182EC 恢复 + CLUT 节点 0x04)   ← 黑屏修复, 现役 ELF 定格于此
  → ZH50 (build_zh50.py: 过滤 5 词)
  → ZH55 (build_zh55.py: +0x417620/0x21CB30/CAVE16/0x2071B4/0x216578/0x1FF8D0)
[组装]  ISO 组装 = 原位替换: ELF@LBA295 + MENU@LBA776286, 输出尺寸=原盘 (zh16_iso.py / make_iso.py)
[验证]  work/zh16b/subagent_inventory/{verify_elf_diff.py, verify_img_diff.py}
```

每一级构建脚本都带 `cur==want` 断言 + 全盘 diff 白名单自检; 逐级词差已实测 (ZH31→43=17 词,
43→49=1, 49→50=5, 50→55=7, 55→56=0)。

---

## 五、未解决 / 待办 (来自各轮报告; 序号 1/2/5 已于 GR_ZH57 处理, 见 §六)

1. ~~**训练场 L1 队伍控制面板按键不对齐**~~ — **GR_ZH57 已修** (NewPS2Shortcut::DrawNN 标签锚点, 见 §六)。
2. ~~**读卡/记忆卡对话框长行不居中**~~ — **GR_ZH57 已修** (StringWidth 字距按字节计数的 SWKERN cave, 见 §六)。
3. **控制器页 R3 键下沉** — K=16 (0x2071B4) 的 +5px 副作用, 待用户定夺 K=21 或行级例外 (`REPORT_zh56.md` §三)。
4. **载入屏文字偏高 5px** — 修法已备未上盘: 0x20C7A8/0x20C83C 240→245 (`REPORT_zh53.md` §四)。
5. ~~**武器/装备名 CJK 汉化**~~ — **GR_ZH57 已做物品/装备类** (望远镜/定向雷等 10 键, 走 charset 正确编码; 见 §六); 武器型号简写按用户要求保持 EN。
6. **HUD 计时器 13px 上移** (去拉伸副作用)、**教程提示框**、**多人死亡字幕 TriggleForBlackCamera 横向失配** — REPORT_zh53 §四 未覆盖项。
7. **底部滚动提示栏组件身份未锁定** (三候选全给出公式, 需 drawlog/eeram 定位) — `REPORT_offsets.md` §五。
8. **REPORT_offsets 中置信项上屏确认**: 顶部标题/控制器页的 K=16 观感、ctor-12 组件存在性清单。
9. **GR_ZH57 实机验收**: L1 面板标签下移 2.5px、对话框长行居中、物品名中文显示。

---

## 六、GR_ZH57 增量 (2026-09-24, 分支 fix/dialog-names-l1)

**GR_ZH57 = GR_ZH56 + 5 ELF 词 + 44 词 cave + EN_STRINGS.TXT 条目重写**
sha256 `6740b1ecd3ba6f0f16e6d92daf095072c165709227da1dd72d2b1e0837cb1054`;
构建脚本 `work/zh16b/subagent_findkey/build_zh57.py` (全程断言 + 回读自验)。

### ELF 增量 (在 §一 全表之上新增)

| VA | 旧词 | 新词 | 语义 | 来源 |
|---|---|---|---|---|
| 0x2DE5A4 | 0C086B34 | 3C0241A8 | L1 面板标签锚点: jal CharHeight → lui v0,21.0f | 本轮 (子代理 l1panel2) |
| 0x2DE5A8 | 00000000 | 44820800 | mtc1 v0,f1 (f1=21.0) | 同上 |
| 0x2DE5AC | 44820000 | 00000000 | (原 mtc1 v0,f0 → nop) | 同上 |
| 0x2DE5B4 | 46800060 | 00000000 | (原 cvt.s.w → nop) | 同上 |
| 0x21AC90 | 8E620018 | 08158E00 | StringWidth 字距 hook: lw v0,0x18(s3) → j 0x563800 | 本轮 (子代理 dialog) |
| 0x563800–0x5638AC | 全零 | 44 词 cave | SWKERN: 字形计数 (lead 0xA1-0xAD + trail 0xA1-0xFE 成对) 后 kern×(glyphs−1), 跳回 0x21ACA4 | 同上 (修补: 子代理方案漏 $t1 初始化, 已加) |

机制: (L1) 标签 y = iconCY − CharHeight()/2; V18B 后墨迹 16px 而 CH=26 → 标签高 2.5px;
改为常数 21 → y = iconCY−10.5 = EN 墨心。
(对话框) StringWidth 字距总账按字节数计而绘制按字形 → 含 CJK 的行高估 kern×n_pairs →
逐行居中左漂 kern×n/2 px; cave 改为字形计数。纯 ASCII 结果不变 (EN 零回归)。

### 数据增量

| 位置 | 变化 | 说明 |
|---|---|---|
| MENU.IMG EN_STRINGS.TXT (@0x378A000) | ZH56 的 EN 内容 → charset 编码 CJK 值 | 10 键: WPN_EXTRAAMMO=追加弹药(额不在字表)/ITM_BINOCULARS=望远镜/ITM_SENSOR=传感器/ITM_CLAYMORE=定向雷/ITM_BOMB=爆破装药/No Restrictions=无限制/Pistols Only=仅手枪/Primary Weapons Only=仅主武器/Standard Kits=标准装备/Originals Only=仅原版 |
| 同上条目表 (0x830+48×30) | stored 2749→2718, real 6930→6628 | framed 2718B (payload 2710), 经 text_replace.py --mode txt 正确编码 (charset_compiled_zh16.json, **非 UTF-8**) + LZO 自检 |

**管线教训 (防再犯)**: 当年此条目被写坏 = ①用 UTF-8 而非游戏码页; ②明文与 stored/real 头不一致。
正确流程: `text_replace.py --mode txt --charset work/zh16/charset_compiled_zh16.json
--base-txt <EN解码态> --input <csv> --out <前缀>` 产出 `.txt`(明文,可核对) +
`.framed.bin`(含 LZO 自检回环), 再按 IMG 条目 framing 写入
(in-data 头 = [payload长][real], 条目表 stored = 总长)。

---

## 附: 核实脚本

- `work/zh16b/subagent_inventory/verify_elf_diff.py` — 全 37MB ELF 逐词 diff + 逐级链归因 (可复跑)
- `work/zh16b/subagent_inventory/verify_img_diff.py` — MENU 686 条目逐条比对 + GR.IMG 流式字节 diff→条目映射
- `work/zh16b/subagent_inventory/elf_diff_zh56_vs_en.txt` — 375 行 (VA, EN 词, ZH56 词) 机器可读全表
- 另有本轮的 FONT.RES 解码、PAK 8 段/CLUT 节点断言、锚点逐盘探针 (本文 §一/§二 全部数字的出处),
  均为一次性内联脚本, 结论已固化在上表; 断言类事实可用 `subagent_offsets/assert_offsets.py` (74 项)
  与 `subagent_blackfix/build_zh49.py` 的节点签名搜索交叉复跑。

---

## 七、GR_ZH58 增量 (2026-09-24, 修复 ZH57 视频后卡死)

**问题**: GR_ZH57 开头演示视频播完后卡死 (cdvd 尾帧 6748 vs 正常 8962; 用户 PCSX2 2.8.2 与
gsrunner v2.9.32 同样复现 ⟹ 盘侧 bug, 与模拟器版本无关)。

**根因**: ZH57 的 SWKERN cave 放在 **0x563800** — 该区静态全零且无 xref, 但**运行时 f260 起
被游戏数据表覆盖** (`20 07 20 07...`)。菜单阶段 StringWidth 首次大量调用时 `j 0x563800`
跳到垃圾 → 卡死。二分定位: `_bisect_sw`(仅 hook+cave) 卡死 / `_bisect_l1`、`_bisect_nm` 正常。

**修复 (GR_ZH58)**: SWKERN cave 迁址 **0x565670** (镜像内 0x56566E-0x56D7EF 的 33KB 恒零填充区)。
选址方法: f1500/3000/4500/6000/7500/9000 六周期 RAM 转储逐字节 AND 求恒零区。
hook 词: 0x21AC90 `8E620018` → `0815959C` (j 0x565670); 其余与 ZH57 相同。
sha256 `833ecd7ebba8d426…`; 验证: 启动 cdvd 尾帧 8960 (时间线与 ZH56 一致) +
40000 帧标准冒烟 ALIVE (needle 3978)。

**新纪律 (cave 落点铁律)**: 静态"全零 + 无 xref"**不等于**运行时安全 — 零区可能是运行期
数据缓冲。**新增 cave 必须做多帧 RAM 转储恒零验证** (覆盖视频/菜单/任务等阶段),
方可用作代码落点。已知安全落点: 0x416ED0-0x4176B0 (V 系洞穴簇, 多轮实证) 与
0x565670-0x5658B0 (本轮 6 转储恒零)。

**盘谱系补全**: ZH56 → ZH57 (作废, 卡死) → **ZH58 (当前终盘)**。

**模拟器版本说明**: gsrunner 仪表化版基于 PCSX2 v2.9.32 (git describe); 用户实测 2.8.2
稳定版。本次卡死两版本同样复现, 与版本无关; ZH58 对两版本同时生效。

---

## 八、GR_ZH63 增量 (2026-10-02, 读卡对话框修复)

**GR_ZH63 = GR_ZH62 + ELF 1B + RES 两份重编码**
sha256 `3838ed874b8bf531e6ec46cc42a38cfb7baf928f870293b8287f1551cd250378`;
构建脚本 `tools/iso_build/patch_zh63.py` (断言式 + 全盘 diff 三窗口白名单)。

### ELF 增量

| VA | 旧词 | 新词 | 语义 | 来源 |
|---|---|---|---|---|
| 0x5656C8 | 11800009 | 15800009 | SWKERN cave 内 trail 判定 `beq t4,zero,+9`→`bne`: 修复极性反转 (详见 §六 SWKERN 行的勘误) | 本轮 (PROGRESS §27) |

**勘误 (§六 SWKERN 行)**: ZH57 的 SWKERN cave 自引入起 trail 判定极性即反 —
真实 pair (trail∈[A1,FE]) 全部走 ASCII 单步路径, t1 恒 0, cave 等效 EN 原公式
(kern 按字节计)。"读卡/记忆卡对话框长行不居中" 实际到 ZH63 才真正修复。
kern 真值 = 2 (实测 MC 屏 4 行 x 位移 = 2×pairs/2 精确吻合)。

### 数据增量

| 位置 | 变化 | 说明 |
|---|---|---|
| MENU.IMG EN_STRINGS.RES #25 (@0x377E000, 槽 47,570B) | G58.I797 译文重写, 新 blob 32,365B + 余量零填 | 条目表 off/stored/real 不动 (stored=槽长, 引擎子流走读提前终止); 旧译 71B「…(PlayStation®2␠用)。…」→ 新译 54B「正在读取记忆卡插槽1中的记忆卡(8MB)。␠请勿取出记忆卡(8MB)。」 |
| GR.IMG EN_STRINGS.RES #902 (@0xCAC1750, 槽 47,619B) | 同步 I797, 新 blob 32,366B + 零填 | GR 份子流尾块 osz=13,980 (≠MENU 的 13,857), 重帧按各自基底复刻 |

生成工具: `text_replace.py --mode res --charset tools/font_pipeline/data/charset_compiled_zh16.json
--input tools/iso_build/assets_zh63/i797.csv --base-res <裁尾基底> --target menu|gr`。
(基底 = 现役 ZH blob 裁掉陈旧尾料后的有效 8 子流帧 — 喂 text_replace 前必须裁尾,
否则其 decode_blob 走进尾料报 INVALID BACK。)

---

## 九、GR_ZH64 增量 (2026-10-02, 缩放读数条倍数标签修复)

**GR_ZH64 = GR_ZH63 + 字库 EN 带重铺 (零 ELF)**
sha256 `890a7c291533d8edf5cdc792c730d26dce89a72df20da361377b585e1d2ebdaf`;
构建脚本 `tools/iso_build/patch_zh64.py` (断言式 + 全盘 diff 两窗口白名单)。

### 修改面 (全部在 MENU.IMG)

| 位置 | 变化 | 说明 |
|---|---|---|
| FONT.RES 槽 @0xB9120 (4421B) | large/default/huge 三 face 的 ASCII 记录 (0x21-0x7E, 92 字形, 排除 0x7B/0x7D) 改写: adv 恢复 EN 原版比例宽度 (4~19px), u/v → 新带 @v452; 空格 adv=3072 | payload 1356B ≤ 4413 (DP 压缩), 回环 PASS; CJK 格/单字节/▲▼/µ± 记录零触碰 |
| COMMON.PAK 字库记录 @0x58431 | 新 EN 带 16 行 (v452-467) 写入 seg7 | 从原始容器 new_font_revised (PSMT8) 提取 large 面字形, bbox 裁切 (ink<24), 底对齐基线=行15; 旧 mini 带 (v376-411) 原样保留 (▲▼ 记录仍指向它) |

### 语义
- 修复: 训练 1 瞄准镜缩放读数条倍数标签 (×N/×1) 细碎+偏上 (用户 2026-10-02 报障);
  同时全游戏 ASCII (TEQSUNSET/(8MB)/START...) 恢复 EN 原版字形与比例宽度。
- 坐标层实证: 标签绘制 f12/f13 双盘本就一致 (x=SW×0.5−XScale, y=31/164), 缺陷纯在字形层。
- 副作用 (预期内): ASCII 串宽变化 → 居中/折行按 EN 比例重排 (对话框/简报实测正常)。
- 字库链注意: 89B 重放基线自此不适用于 EN 带 (重铺未纳入 build_font.py 重放链, 待下次链整备)。

---

## 十、GR_ZH65 增量 (2026-10-03, EN 带改用方正像素16 — 用户定案)

**GR_ZH65 = GR_ZH63 + EN 带像素化 (零 ELF)** (跳过被否决的 ZH64, 基底仍 ZH63)
sha256 `0e73d0481280f2f469b32453edeba3e09fdd6cdb131fec8797ce2f8aef095eb8`;
构建脚本 `tools/iso_build/patch_zh65.py`。

**§九 (ZH64 原版字形方案) 状态: 用户实测否决 ("显示效果上差了很多"), ZH64 归档不推荐。**

### 修改面 (全部在 MENU.IMG, 窗口与 §九 相同)

| 位置 | 变化 |
|---|---|
| FONT.RES 槽 @0xB9120 | 三 face ASCII 记录 (92 字形): adv=0x0800 (8px 半角步宽), u=(i*8, i*8+8), v=(452,468); 空格 adv=8 |
| COMMON.PAK 字库记录 @0x58431 | 新带 @v452-467: 方正像素16 渲染 (gen_font16 同管线: TTF@16, em 窗, 阈值128), 半角列窗 [0:8) em 行位原样 (基线=行13, 降部最深行15), '~' 超 1px 截断 |

### 语义
- 全游戏 ASCII (×N/×1/TEQSUNSET/(8MB)/START...) = 16px 像素字体, 与 CJK 同款同基线;
- ASCII 串宽 = 8px/字符 (半角等宽); 居中/折行随之 (实测对话框/简报正常)。
- 字库链 89B 重放基线对 EN 带不适用 (重铺逻辑待并入 build_font.py 重放链)。

---

## 十一、GR_ZH66 增量 (2026-10-03, ASCII 顶部留空 — 用户 leading 理论)

**GR_ZH66 = GR_ZH63 + EN 带像素16 + 采样窗顶留空 2 行 (零 ELF)**
sha256 `6973eb897cf3b0bf744106699d2625b92dbb86191fde9fbade826f761b22e3c5`;
构建脚本 `tools/iso_build/patch_zh66.py`。ZH64 (原版字形) / ZH65 (像素字无留空) 均归档。

### 修改面: 与 §十 相同两窗口, 唯一差异 = FT 记录 v: (452,468) → **(450,466)**
采样窗顶 = 带顶 −2: 窗内顶部 2 行空白随四边形渲染 = 补回 EN 式行盒 leading
(EN 原版 26px 行盒内顶部留 7 行; ZH50 禁双线性 + 16px 格填满后同坐标墨迹骑高 ~2px —
用户 2026-10-03 机理分析, 实测证实)。全 ASCII 下移 2px; 降部 (最深行15) 完整保留。
偏移量微调 = patch_zh66.py 的 REC_V0 常量。

### 验证: ×4 墨行 [33,42] 顶部与 EN (33) 精确对齐 (底部差 1px = 像素 '4' 10px vs EN 11px);
对话框 (8MB) +1~2 同步; 简报锚点全保持; 三流程 exit=0。

---

## 十二、GR_ZH67 增量 (2026-10-03, 帮助条垂直居中 — ELF 手术)

**GR_ZH67 = GR_ZH66 + style-0x52 手术 cave (12 词)**
sha256 `6baf8984cf96989e0ac6540a5bc3f41ec6075402d25802553460a776fe0079ae`;
构建脚本 `tools/iso_build/patch_zh67.py` (差异词集精确断言)。

### ELF 增量

| VA | 旧词 | 新词 | 语义 |
|---|---|---|---|
| 0x21CA50 | AC8300EC (sw v1,0xEC(a0)) | 081595CC (j 0x565730) | DrawTheText 入口 0xEC 写点 hook; 延迟槽 0x21CA54 (lbu v1,0x108) 先执行保真后续 bne |
| 0x565730-0x56575C | 全零 | 12 词 cave | y=[0x3C]+[0x4C] 等价重算; style([0x14])&0xFF==0x52 → y+=2; 写回 0xEC; j 0x21CA58。仅用 t0/t1/t2 死寄存器 |

### 语义
- §五.7 底部滚动提示栏身份收口: RSTextComponent style=0x52 (帮助条族专属, 其余组件
  全 0x53), W=250 H=20 ay=419 每帧 x−2 横滚。
- 帮助条 16px 文字在 H=20 条带内骑高 2px (EN 26px 行盒墨迹自然居中) → +2 居中。
- cave 落点 0x565730 ⊂ ZH58 六转储验证安全区 (0x565670-0x5658B0), SWKERN 止于 0x56571C。

---

## 十三、GR_ZH68 增量 (2026-10-03, 帮助条 +4 精校 — 1 词)

**GR_ZH68 = GR_ZH67 + 手术常量 +2→+4**
sha256 `240b149fed38b7848fff366eace65817fc228501cfe848b5d19fa1dd8414ffae`;
构建脚本 `tools/iso_build/patch_zh68.py` (0x565750: 0x25080002→0x25080004)。

### §十二勘误: ZH67 的 "+2 生效但 ZH68+3 渲染不变" 之谜
此前测的 [383/385,398] 墨带 = 右侧按钮行 (接受/返回, style-0x53), 非帮助条文字;
帮助条文字 (暗灰, 条带背景纹理内) 须双盘差分 (仅手术常量不同) 抠出。float y → 光栅
严格线性。终测: EN 文字心 392.5; +2→390.5, +5→393.5 → **+4 = 392.5 精确命中**。
