**★ 现役盘 (2026-10-11 · round43) = `GR_ZH93`** (`work/builds/GR_ZH93/GR_ZH93.iso`)

- sha256 **e037f6292940811144e2d0d629ec4c4f3e2cfc306d099a4c96b44f6ee08d19be** (1,648,164,864 B)
- = `GR_ZH92` (`1d30c106…`) + **方案 C 字库扩容**（`tools/iso_build/patch_zh93_planc.py`：
  ELF 4 处 gate `sltiu …,0xAE`→`0xB1` ⇒ lead 区间 `0xA1..0xB0`，对偶容量 **1504**）
  + 字库格位公式订正（round41）+ `ç`/`ñ` 进字符集（round43，**盘上字节零变化**）
- 文本表格式 = **`text-csv/4`**（按 `kind` 拆成多张；注入 `--csv` 可给**目录**）
- **★ 资料包（给用户）**：`work/builds/GR_ZH93/release/`（23 文件 / 22.8 MB）
  —— 3 张可注入表 + 10 张 view-only 普查表 + 字库纹理 2×/1× + `字库报告.xlsx`（6 页）
  + `README.md` + `MANIFEST.json`；生成器 `tools/maint/make_release_pack.py`
- 字库现算数字：对偶 容量 1504 / 已用 1319 / 空 185 / ★可直接用 **45** / 需回收 140；
  单字节已用 **110**（汉字 108 + ç/ñ 2）/ 真正可用 0；charset 1429 / dump 1526；
  图集 20.29%；对偶格 87.70%
- **★ 版本号规则**：每次改动产出新盘用新版本号 ⇒ **下一个新盘从 `GR_ZH94` 起**
- 以后操作：改 `text_edited`（想断行写 `{WRAP}`）→ 构筑加 `--inject-csv <text 目录>`
- 详见 `docs/PROGRESS.md §73`、`docs/REPORT_release_pack.md`

---

**★ 现役盘 (2026-10-11) = `GR_ZH92`** (`work/builds/GR_ZH92/GR_ZH92.iso`)

- sha256 **1d30c1067beb8fc8534193486f23f75489447eb0487ab24d06ef66c0627120b6** (1,648,164,864 B)
- = `GR_ZH91` (`42d04a4f…`) + **用户新文本**（`SFXML:T0010` 重写 + **7 个人工断点**）
- **★ `{WRAP}` 新语义**：人写的 `{WRAP}`/`{Warp}` = **断点指令**，注入时写出真换行 `{br}`；
  dump **不再自动插标记**；「引擎现在在哪折行」只进只读列 `wrap_hint` / `wrap_preview`；
  文本表格式 = **`text-csv/3`**（旧格式表改长段会被拒绝，需用 `--carry-edited` 重新 dump）
- 审计 `tools/iso_build/audit_inventory.py` ⇒ **在役 44、缺失 0**
- 版本文件夹自带 `text/`（可编辑表）+ `font/`（图集 PNG + FT csv + 字符集 csv + summary）
- **★ 版本号规则**：每次改动产出新盘用新版本号 ⇒ 下一个新盘从 `GR_ZH93` 起
- 以后操作：改 `text_edited` → 哪里要断行写 `{WRAP}` → 构筑加 `--inject-csv <表>`
- 详见 `docs/PROGRESS.md §70–§72`

---

**★ 现役盘 (2026-10-09) = `GR_ZH91`** (`work/builds/GR_ZH91/GR_ZH91.iso`)

- sha256 **42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88** (1,648,164,864 B)
- base `GR_ZH89` (`6d2afd49…`) + `patch_zh_fix_order_label.py`
  ⇒ **小队设置按钮错译修正「命令」→「顺序」**（英文原盘 = `Order`；同屏帮助条本汉化已作
  「左右键更换队员顺序。」）; 语言表 `MENU#25` + `GR#902` 两份副本, 子流/条目/ISO 尺寸全不变
- 复核: 差异 34863 B 全部落在两个语言表槽内; 审计 **在役 44、缺失 0**; 补丁可重放
- **★ 新增文本工具链**（用户要求）: `tools/text_csv/`
  dump 出 CSV（`{br}`→换行、自动折行点→软换行, **人工主动操作换行**）→ 注入按 CSV 换行写回
  **Lead 复检往返零差异**（未改动 CSV 注入回原盘 ⇒ sha256 相同）; 真实变更实机验证通过
- **★ 版本号**: `GR_ZH90` 被本轮两个盘占用（工具链 demo / 错译修正）⇒ 下一个新盘 = `GR_ZH92`
- 清理: 只保留 `GR_EN_ORIG` + `GR_ZH91`
- 未覆盖资源与解码口径统一建议: 见 `docs/PROGRESS.md §69`

---

**★ 现役盘 (2026-10-08/09) = `GR_ZH89`** (`work/builds/GR_ZH89/GR_ZH89.iso`)

- sha256 **6d2afd49a3d158253d9c9cfd2cd1678c57ed1ab39e6cc502938b7d37eca26cbf** (1,648,164,864 B)
- base `GR_ZH87` (`2da5b041…`) + `patch_zh_sf_spaces_all.py` ⇒ 差异 37170 B, 全部落在 MENU.IMG#283 槽内
- **全量删除特别收录文本多余空格**: 实际删 **792 处 / 56 条 `<text>`**（881 处 reflow 伪影中，
  89 处因删了会改变折行而保留）；849 处原文排版空格（「约 340 克」）永不删
- **排版零变化**: 28335 字符对 4 个折行模型逐字符 (段,行) 0 处不一致；
  实机 5 屏三方对照 42 行 = 30 行逐字相同 + 12 行仅少空格 + **0 行真正不同**
- `r23_audit_inventory.py` = **在役 44、缺失 0**；补丁**可重放**（Lead 复检 sha256 一致 ✓）
- **★ 版本号规则**：每次改动产出新盘用新版本号；下一个新盘从 `GR_ZH90` 起
- 遗留：89 处保留（会改折行）；人物档案页 260 处改动无法实机验收（存档第 7 行未解锁）

---

**★ 现役盘 (2026-10-08) = `GR_ZH87`** (`work/builds/GR_ZH87/GR_ZH87.iso`)

- sha256 **2da5b04157c12796b5ab45e3c23daf81470fd1c2a495e5b1254f1bb811f483e3** (1,648,164,864 B)
- = 原 `GR_ZH82` 的同一份内容（已含 5 项修复：金框字高 K=21、子界面标题 +7、图集 4 texel 清理、
  金框条目名条件化、武器介绍词内空格），**仅按用户要求升版号，内容零改动**
- 审计 `r23_audit_inventory.py` = **在役 44、缺失 0**
- **★ 版本号迭代规则**：每次改动产出新盘用**新版本号**（单调递增，跳过历史已用编号）；
  `zh83`~`zh86` 为历史构建（改动已全部包含），`zh88` 为历史 capacity 实验编号 ⇒ 下一个新盘 = `GR_ZH89`
- **★ 分支纪律**：每次改动先开 git 分支，做完再合并（round26/27/28）
- 进行中：`round28/zh87-space-cleanup` ⇒ 全量删除多余空格，目标盘 `GR_ZH89`

---

**★ 现役盘 (2026-10-08 · round27 合并) = `GR_ZH82`** (`work/builds/GR_ZH82/GR_ZH82.iso`)

- sha256 **2da5b04157c12796b5ab45e3c23daf81470fd1c2a495e5b1254f1bb811f483e3** (1,648,164,864 B)
- = 前一版 `GR_ZH82` (`41b9ccf2…`) + `patch_zh_sf_title.py` (53 B) + `patch_zh_sf_text.py` (141 B)
  - **特别收录金框条目名条件化**: `0x21D940` → `j 0x565A00`; 判据 `comp[0x44](H)==20 && comp[0x40](W)>=400`
    ⇒ 整屏条目条用 K=26(EN 原式), 其余沿用 K=21(**原词逐字保留在 cave 0x565A28**)
  - **武器介绍词内空格**: `MENU.IMG#283` XML `0x3E90` 的 0x20 删掉 + 同条目末尾补 1 个（等长覆写）
- `r23_audit_inventory.py` = **缺失 0**（总账已增补条件化挂点/延迟槽/cave 三行）
- 实机 `navC2` 12000 帧 exit=0；武器页金框条目名居中、介绍文本「方形硬质弹体」无空格 ✓
- **分支纪律**: `round27/sf-inner-title` + `round27/sf-text-space` 已合并（cc588172 / 997da667）
- 遗留: K 口径可选 K≈23~24（墨迹也对齐 EN）；其它 8 个 SF 内页未逐屏验证；61 处可见词内空格待裁决

---

**★ 现役盘 (2026-10-08) = `GR_ZH82`** (`work/builds/GR_ZH82/GR_ZH82.iso`)

- sha256 **41b9ccf2559578773e054b6cfaa8c970b9de0f440ba0ce9fa49632ab0aef3a7f** (1,648,164,864 B)
- = ZH82 在役 ELF 状态 **+ 子界面标题居中还原 + 字库杂散墨点清理**
  - `patch_zh_title_center.py`: `0x565910` `00000000 → 24E70007` (ZH61 tail-cave 的 `a3 += 7`;
    被 `patch_zh85` 误 NOP ⇒ 标题墨迹顶缘 18.4 → **24.5 与英文原盘对齐**)
  - `patch_glyph_clean.py`: 图集 4 个杂散 texel (里 315,354 / 进 342,354 / 地 388,354 + 393,354);
    图集 **0=墨、1=空** (PSMT4 调色板索引)
- 相对前一版 GR_ZH82 (`6127a582…`) 差异 = **恰好 7 字节**
- `r23_audit_inventory.py` = **在役 43、缺失 0** ✓；实机 navTACe 9000 帧 exit=0 ✓
- **人名纯英文**；字库/图集/语言表其余部分 = zh86 时代状态
- 清理: 只保留 `GR_EN_ORIG` + `GR_ZH82`
- **★ 分支纪律**: 本轮 `round26/cleanup-zh82`；以后每次改动先开分支，做完合并

---

**★ 现役盘 (2026-10-07) = `GR_ZH82`** (`work/builds/GR_ZH82/GR_ZH82.iso`)

- sha256 **6127a58219a0d3597b846ebfb01d755cc72f5d220839be4551185bd37a83c628** (1,648,164,864 B)
- `docs/PATCH_INVENTORY.md` 的 44 处 ELF 补丁: **在役 43、缺失 0** (`tools/iso_build/audit_inventory.py`)
  - `0x21D940` = `2462FFEB` (IkeBaseButton 盒居中 K=21, ZH40 用户认证的 EN 对齐口径)
  - `0x4176A0` = `24020010` (CAVE16 假 CharHeight = 16, ZH82 在役值)
- **人名纯英文**: 1193 个 `.ATR` = 英文原盘内容, 条目位置/尺寸逐条一致
- 字库/图集/语言表/ELF = zh86 时代状态
- **清理**: 已删除 22 个废弃构筑盘, 只留 `GR_EN_ORIG` + `GR_ZH82`
- **★ 分支纪律**: 每次改动先开 git 分支, 做完再合并 (本轮 `round26/cleanup-zh82`)
- **订正**: 字库纹理是 PSMT4 4bit **调色板索引**, 不是灰阶 —— 1bit 字形无抗锯齿;
  「地」「里」下方渗墨 = 图集内杂散墨点 (待修)

---

**★ 现役盘 (2026-10-06) = `GR_ZH82D`** (`work/builds/GR_ZH86R/GR_ZH82D.iso`)

- **还原文档记载的 ZH82 在役 ELF 状态**: `tools/iso_build/audit_inventory.py` 解析
  `docs/PATCH_INVENTORY.md` 的 44 处字节级补丁并逐条核对 ⇒ **在役 43, 缺失 0**
  - `0x21D940` 00621023 → **2462FFEB** (IkeBaseButton 盒居中 K=21, **ZH40 用户认证的 EN 对齐口径**)
    —— 曾被 `patch_zh85` 回退 ⇒ 文字贴框上沿 (用户报障根因)
  - `0x4176A0` 24020014 → **24020010** (CAVE16 假 CharHeight = 16, ZH82 在役值)
- **人名纯英文** (1193 个 `.ATR` = 英文原盘); 字库/图集/语言表 = zh86 时代
- 上机: 战术演习列表文字**居中**, 与英文原盘一致 ✓
- 往前重建: `GR_ZH36 →…→ GR_ZH62 → zh63…zh85 → zh86`; ELF 可由 PATCH_INVENTORY 逐字节还原

---

**★ 推荐盘 (2026-10-06) = `GR_ZH86R_k16`** (`work/builds/GR_ZH86R/GR_ZH86R_k16.iso`)

- **金框字高补偿**: `0x21D940` 的 K 常量 26→16 (旧 26px 字库的字高 vs 现役 16px 墨迹)
  ⇒ 列表/金框文字下移 ~3px, **与英文原盘对齐** (实测 4 行墨迹中心 185/209/238.5/267.5
  vs EN 183.5/211/238.5/265.5, 偏差 ≤2px; 修正前偏高最多 4.5px)
- **字库/图集/语言表/ELF = zh86 时代状态**; **人名纯英文** (1193 个 `.ATR` = 英文原盘)
- 上一轮的 `0x565750` (+4→+8) 实测**只移动了底部说明条** (y385..403), 与菜单内容无关 ⇒ 已废弃
- **zh80 时代可追溯**: build_info (zh83–86 含 sha256)、补丁 zh80–85/zh88_lead、
  同屏对比图 (zh81/82/83/86)、zh82 文本总表、提交记录 zh70–zh86; ISO 本体已丢失
- 构筑链: `GR_ZH82 →zh83→ ZH83 →zh84→ ZH84 →zh85→ ZH85 →zh84→ ZH86`

---

**★ 现役盘 (2026-10-06) = `GR_ZH86R`** (`work/builds/GR_ZH86R/GR_ZH86R.iso`) — ZH86 等价盘

- **字库/图集/语言表/ELF = zh86 时代**: 与微调主线 `GR_ZH251`(=`GR_ZH256` 的 base) 逐字节相同;
  80+ 时代位置微调 (zh63–zh85) 逐补丁重放核对全部已应用
- **人名纯英文**: 1193 个 `.ATR` = 英文原盘内容 (位置/尺寸逐条一致); 游戏中显示 `John Mata` 等
- **「金色选中行文字靠上」= 英文原版设计**: 同屏实测 EN 与汉化盘偏移均为 +0.0 px
- 静态: GR.IMG 位置变动 0、尺寸变动 0; `.ATR` 中文名 0 条
- 无法逐字节重建真正的 zh86 (其基底 GR_ZH82 与更早注入脚本已不在仓库), 故交付等价物
- 对照盘 `GR_ZH86R_y8` = 选中行下移 4px (偏离原盘, 不用)

---

**★ 现役盘 (2026-10-06) = `GR_ZH276`** (`work/builds/GR_ZH276/GR_ZH276.iso`)

- **80+ 时代的位置微调全部在** (逐补丁重放核对: zh63–zh85 均已应用; cave `0x4176A0`=20、
  `0x21D940`=EN、`0x565910`=NOP 字节级复核通过)
- **中文人名恢复**: `patch_zh77` 原位等长覆写 249 条 (+ zh9 时代既有 5 条),
  937 条脚本角色键按设计保持英文; 条目表/IMG 头部逐字节未动
- **字体/图集/语言表/ELF = zh86 时代** (huge 面 96 条, 未补; 语言表原样)
- 静态: GR.IMG 位置变动 **0**、尺寸变动 **0**
- 教训: 角色名只能原位等长覆写; 不可截短、不可搬家

---

**★ 现役盘 (2026-10-06) = `GR_ZH274`** (`work/builds/GR_ZH274/GR_ZH274.iso`) — 回退版

- **字体/文本状态 = zh86 时代**: huge 面 96 条 (不补)、cave 字高 20 (zh83 保留)、语言表原样
  ⇒ 用户报障的「`小`→`·`」与「16px 位置上下浮动」都已消除
- **`.ATR`/`STRINGS.TXT` 全部恢复英文原盘** (1194 个; 位置/尺寸 = 原盘)
  ⇒ 修「进入关卡卡死」与「角色名乱码」; 角色名显示英文原名
- 静态核对: GR.IMG 位置/尺寸变动 **0**; vs `GR_ZH256` 的差异**全部落在 GR.IMG 条目内**;
  MENU.IMG (FONT.RES/COMMON.PAK/语言表) 与 ELF **逐字节相同**
- 上机: 战术演习进入关卡 ✓
- **教训**: `0xB7` 是字集里 `小` 的合法码位; 汉化字库 huge 面 96 条是既有事实, 补齐会改变排版

---

**★★ 最终交付盘 (2026-10-06) = `GR_ZH272`** (`work/builds/GR_ZH272/GR_ZH272.iso`)

- **角色名乱码彻底根治**: 全部 **1193 个 `.ATR` 恢复英文原盘内容**
  (位置/尺寸与原盘逐条一致; 游戏里显示的角色名即来自 `.ATR` 的 `<ActorName>`)
- **语言表**: 非法间隔号 `0xB7` → 合法码位 `0x99` (两副本各 382 个)
- **huge 面补齐**: 96 → 224 条, FT 5942 → 7222 B (与原盘一致)
- **16px 统一**: 12px 关卡名方案退役 (载入界面与简报页关卡名同字符串同面)
- 上机: 战术演习进入关卡 ✓; 角色名显示 `John Mata` (英文原名) ✓
- 静态: GR.IMG 位置变动 0, 尺寸变动 0, .ATR 里 0xB7 = 0

---

**★ 最终交付盘 (2026-10-06) = `GR_ZH270`** (`work/builds/GR_ZH270/GR_ZH270.iso`)

- **16px 统一**: 用户决定放弃 12px 关卡名 (载入界面与简报页关卡名同字符串同字库面, 字号只能一致)
- **角色名乱码根因已修**: ATR 间隔号 `·` 曾被写成非法字节 `0xB7` (落在 DBCS 首字节区)
  ⇒ 名字整体错位; 改用合法空闲码位 `0x99` + 图集 16px 中点
- **`.ATR` 彻底归一**: 位置与尺寸都恢复成原盘 (116 个名字截短保留汉化, 1 个退回英文)
- **huge 面补齐**: 96 → 224 条, FT 5942 → 7222 B (与原盘一致)
- 上机: 战术演习进入关卡 ✓; 载入界面全部 16px ✓; 静态: 位置变动 0, 非法 0xB7 = 0

---

**现役盘 (2026-10-06 · 第 12 轮)**
- **16px 主交付盘 = `GR_ZH268`** (`work/builds/GR_ZH268/GR_ZH268.iso`)
- **12px 盘 = `GR_ZH369`** (`work/builds/GR_ZH369/GR_ZH369.iso`)

**第 12 轮修复**
1. **角色名乱码根因**: ATR 间隔号 `·` 被 `atr_dot_patch2.py` 按 latin-1 写成单字节 `0xB7`;
   `0xB7 ≥ 0xA1` 落在 DBCS 首字节区 ⇒ 引擎当双字节首字节 ⇒ 其后字节全部错位 (乱码)。
   改用**合法空闲码位 `0x99`** + 图集 16px 中点, 修正 7 个 .ATR。
2. **载入界面字号**: 实测载入界面与简报页关卡名**同用 `default` 面** ⇒ 两者字号只能一致
   (12px 关卡名 ⇒ 载入界面那行也 12px; 见 `docs/PROGRESS.md §55`)。
3. **huge 面补齐**: 汉化字库 huge 面 96 条 (原盘 224) ⇒ 补齐, FT 5942→7222 B。
4. **ATR 条目搬回原位**并保留汉化名 (`work/_dis/r12_atr_unmove.py`)。
5. 静态核对: 两盘 GR.IMG 条目位置变动 **0**, 仍含非法 0xB7 的 .ATR **0**。

**第 11 轮修复 (背景)**: ATR 补丁把 14 个 GR.IMG 条目搬到尾部 ⇒ 进入关卡卡死;
`work/_dis/r11_atr_unmove.py` / `r12_atr_unmove.py` 写回原偏移。

**现役盘清单 (2026-10-06)**

| 版本 | 用途 | 关键点 |
|---|---|---|
| **`GR_ZH268`** | **★ 16px 主交付盘** | 全部 16px; 含第 11/12 轮全部修复 |
| **`GR_ZH369`** | **★ 12px 盘** | 关卡名 12px (default 面); 含同上修复 |
| `GR_EN_ORIG` | 英文原盘基线 | 硬链接到原盘, 零额外占用 |
| `GR_ZH366` / `GR_ZH267` | 废弃 | 间隔号仍 0xB7 ⇒ 角色名乱码 |
| `GR_ZH256` 及更早 | 废弃 | 含 ATR 条目位置缺陷 |

---

# 构筑版本差异说明

**现役盘 (2026-10-06 · 第 11 轮)**
- **16px 主交付盘 = `GR_ZH267`** (`work/builds/GR_ZH267/GR_ZH267.iso`) = `GR_ZH256` + GR.IMG 条目位置修复
- **12px 最终盘 = `GR_ZH366`** (`work/builds/GR_ZH366/GR_ZH366.iso`) = 12px 方案 + huge 面修复 + 条目位置修复

**第 11 轮根因**: ATR「间隔号」补丁把 **14 个 GR.IMG 条目搬到尾部**
(`STRINGS.TXT` + 13 个 `.ATR`: DEMOLITIONS-03/05/11/15/21/28/43/49/51, D_SCOTT_IBRAHIM,
SCOTT_IBRAHIM, RIFLEMAN-07/54)。`.ATR` 是任务数据、**关卡开始时读取** ⇒
位置与原盘不一致 ⇒ **战役与战术演习进入关卡全部卡死**（用户报障）。
修复: `work/_dis/r11_atr_unmove.py` 写回原偏移（13 个 ATR 与 STRINGS.TXT 退回英文原盘内容）。
模拟器实测: 英文原盘可进入 ✓ / `GR_ZH256` 冻结 ✗ / `GR_ZH366`+`GR_ZH267` 正常进入 ✓。
详见 `docs/PROGRESS.md §54` 与 `work/_dis/R11_TAC_HANG.md`；对比图
`work/archive/cmp/GR_ZH366_hangfix.png`。

**现役盘清单 (2026-10-06)**

| 版本 | 用途 | 关键点 |
|---|---|---|
| **`GR_ZH267`** | **★ 16px 主交付盘** | `GR_ZH256` + 条目位置修复; 关卡名 16px |
| **`GR_ZH366`** | **★ 12px 最终盘** | 12px + huge 面修复 + 条目位置修复 |
| `GR_EN_ORIG` | 英文原盘基线 | 硬链接到原盘, 零额外占用 |
| `GR_ZH256` | 旧 16px 盘 | 含条目位置缺陷 ⇒ 被 267 取代 |
| `GR_ZH364` / `GR_ZH365` | 12px 中间盘 | 条目位置未修 ⇒ 进入关卡卡死 ⇒ 废弃 |
| `GR_ZH361`~`363` | 废弃 | 字符串结构被改 + 条目位置缺陷 |
| `GR_ZH253` / `GR_ZH353` / `GR_ZH360` | 废弃 | 读档卡死 / 文本污染 |

**后续增量以 `GR_ZH256` 为基底**, 且任何改 `GR.IMG` 的补丁之后必须核对条目 `off` 与原盘一致
(或跑 `work/_dis/r11_atr_unmove.py`)。



**锚点分支实际只建到 archive/GR_ZH62** — 表中 ZH63+ 的 archive 列为历史笔误 (从未建过
对应分支), 以本注为准; archive/GR_ZH62 及更早 = 当时完整工作区 (ISO/转储本就不入库);
更早 (ZH7–ZH35) 见 `archive/early-builds` + 归档 PROGRESS (archive/GR_ZH36 时代
work/zh16b/PROGRESS.md)。

| 版本 | 锚点分支 | 关键差异 (相对前版) |
|---|---|---|
| **GR_ZH353** | **现役** | **任务名专用 12px 双字库** (7 步: 图集 v480..495 铺 14 字形 / 码位 `0x84..0x91` 换码 / ELF `GR-` / `#170 <MapName>` / `default` 面占位码位 `0x5E`/`0x60` ← idx 16/17 原 16px / idx 45,16,17 → 12px / `#25`,`#902` 日期换占位)。验证: 关卡名 347 px 全 12px, 日期/时间/年份 0 px 污染。见 §50 |
| **GR_ZH256** | 盘已保留 | 理想人名译名 + 间隔号 `·`, 零回归 (主本地化交付盘) |
| GR_ZH253 | 盘已保留 | **反汇编/补丁基准盘** (含 Plan C 码位方案 `0x7F..0x83`); `GR_ZH353` 的构建基底 |
| GR_ZH82 | 已删除 | 特别收录 item 名规范重译 (25 处) + group 分栏标题汉化 (41 处), **零空格填充**; 用户实测通过。sha256 `d690d95c…` |
| GR_ZH81 | 已删除 (被 ZH82 取代) | XML 41 个 `<group name>` 汉化 (studio 保持英文)。首次成功汉化分栏标题; 但补了 0x20 空格 → 文本不居中, 且漏改 `<item name>`。sha256 `307abccc…` |
| GR_ZH80 | 实验盘, 已删除 | ELF GetSdutio 白名单 + XML studio/group 双改。**失败**: 证明 studio 名两侧任一被改都断链 (P1 探针) |
| GR_ZH79 | 已归档 (被 ZH82 取代); 盘已删 | 把 EN_SPECIAL_FEATURE.XML 恢复为 ZH77 原样 (修 ZH78 回归); RES 的 G58.I724-727 修复保留。sha256 `f6345cf6ff5fe8479a4cbb97325fa32d6fb33fbddff5f519ad255b02dcaab141` |
| GR_ZH78 | **已回退** (其 XML name 中文化引入特别收录屏故障, 见 PROGRESS §46); 盘已删 | 特别收录分栏标题汉化 + GR 前缀文案。**教训**: EN_SPECIAL_FEATURE.XML 的 `<studio name>` 是引擎比较键, 禁译 —— 误译导致 studio 类型未识别、列表全灰无光标 |
| GR_ZH77 | 已被 ZH79+ 取代; 盘已删 | **全部角色档案人名汉化** (纯数据): GR.IMG 1193 个 .ATR 的 ActorName 原位等长覆写, 250 处 → 中文; 1 个压缩条目保留英文 |
| GR_ZH76 | 已被后续版本取代; 盘已删 | **命令面板中文人名下移 + 零寄存器泄漏** (纯 ELF 1 挂点 + 31 词 cave): DrawString v1 序言按"RA∈命令面板 且 串含 ≥0xA1"条件 f13 += 4.5f; 二版改存栈槽 → 零泄漏 |
| GR_ZH75 | 分支 merge/zh73-zh74; 盘已删 | **合并盘 = ZH73 ∪ ZH74**; 两补丁 ELF 字节零交集 |
| GR_ZH74 | 分支 gr-zh74-hudfeed; 盘已删 | 任务内 HUD 指示条文字 y 校准 (纯 ELF 1 词): 0x22E218 减数 1.0f→-1.5f, 文本 +2.5px |
| GR_ZH73 | 分支 fix/squad-roster-names; 盘已删 | 人名缩写 DBCS 化 (纯 ELF 69 词): ActorFile::GetActorNameAbbreviated 0x307090 与 GetUISoldierAbbreviateName 0x2ECDA0 在中文名上只输出 "." → 改"含 ≥0xA1 即返回完整人名" |
| GR_ZH72 | 已被后续版本取代; 盘已删 | 大小写折叠循环高字节守卫 (纯 ELF 12 词): LowerCase 0x407060 / UpperCase 0x408910 ctype 负索引 → zh16 高字节 ±0x20 破坏; 小队屏兵种字段终净『突击队员』 |
| GR_ZH71 | (main 实验盘, 不推荐) | strlog 探针轮实验: 字库 +5 对偶 (爆击手队员@ADF5-F9) + I562-567 纯对偶重编码 — 字段实测 ' 突[坏]队员' 未达标, 未入主线 |
| GR_ZH70 | (git 补丁链) | 兵种比较键还原 (G58.I568-572 → EN 大写, zh7 误译根因): 小队屏兵种字段改善 (残留字段当时误判为"zh7 绘层指针错", 真根因 = 引擎折叠负索引, 见 §37/§十七, ZH72 修复) |

## 构筑清理
- **2026-10-05 (第四轮, 12px 方案定稿后)**: work/builds **7.80 GB → 6.20 GB**, 释放 **1.60 GB**。
  保留: `GR_EN_ORIG` (硬链接, 零占用) + `GR_ZH253` (基准盘) + `GR_ZH256` (主交付) +
  `GR_ZH353` (12px 最终盘) + 各自 `build_info.json` + `temp/mc/` (记忆卡)。
  删除: `temp/dump_*` 转储 10 个 (`dump_C_EN2` / `dump_{C253,C253b,CAMP2,CAMPAIGN,LATE10327,M1,M2}` /
  `dump_C256` / `dump_Y353`) + `extract/` 字表提取 3 个 (各 55.9 MB)。
  **全部可由 `make_build.py` / `run_opt.py` 重建**; 磁盘可用 122.2 GB → **125.3 GB**。
  中间版本 `ZH83~ZH352` (约 270 个探针/实验盘) 在本轮之前已随各轮清理删除。
- **2026-10-04 (第三轮, 用户实测 GR_ZH82 通过后)**: work/builds **47.2 GB → 5.87 GB**, 释放 **41.3 GB**。
  保留: `GR_EN_ORIG` (文本总表参考基准, 必需) + `GR_ZH82` (当时现役盘) + `work/archive/` (关键对照图 6 张 + 文本总表 xlsx)。
  删除: 中间构筑 GR_ZH72~ZH81 (10 个) + 子代理遗留 BISA~BISE (5 个) + 探针盘
  probeA/probeB/probe_p1_elf/probe_p4_group + `work/_dis/{E1,E2,E3}.iso` + `work/_squad/*_test.iso`
  + `SLUS_*_test.elf` + 冗余 drawlog (状态机试错轮/EN 探索性 dump) + 子代理 dump_bisA~E。
  **全部可由 `tools/iso_build/patch_zh*.py` 补丁链从 EN 原盘复现**; 磁盘可用 88.9 GB → 143.1 GB。
- 2026-10-03/04 (第一轮): 中间构筑 GR_ZH63/64/65/66/67 已删 (18.6G→3.3G; 全部可经 git 补丁链重建)。
  **合并补丁 `tools/iso_build/patch_zh68_all.py`**: ZH62 → 现役终态一步到位
  (= ①SWKERN + ②I797双RES + ③EN带像素16 (窗=带 452,468) + ④帮助条手术y+4)。
  ZH68 时代与增量链逐字节等价 (sha256 240b149f); ZH69 起为修正版。
  (旧对比图 work/builds/GR_ZH68/temp/cmp/ 9 张已随本轮清理删除, 结论在 PROGRESS。)
- **2026-10-03 (第二轮, 用户定策: 只留最新版)**: 删除 GR_ZH62 (1.9G) / GR_ZH69 (3.3G) /
  GR_ZH70 (5.4G) / GR_ZH71 (2.2G), 释放 **12.8G**; work/builds 只留 **GR_ZH72 (现役,
  sha256 0c11d1ff…)** + GR_EN_ORIG (EN 基线, ISO 为原盘硬链接零成本, 保留作对照/从零重建
  基础; 其 temp 旧转储 2.5G 未动)。后续基底一律 = GR_ZH72 (其 temp 已留继工具: 盘内
  ELF 提取 SLUS_206.13.zh72 + 反汇编器 dis4t.py; 本轮证据 dump_squad_72p/dump_reg72/
  field_before_after.png)。ZH71 的 1141 字库快照仍存 tools/iso_build/assets_zh71 (§36)。

## 数据面构成 (`GR_ZH253` / `GR_ZH256`; `GR_ZH353` = 在此基础上叠加 12px 双字库)

### `GR_ZH253` / `GR_ZH256` 基底
- MENU.IMG: FONT.RES 字表槽 @0xB9120 (4421B, fld26 + ASCII 记录指向像素16 新带) + new_font_revised
  字库记录 @0x58431 (0x4044C, 1024×512 PSMT4, 8 段 GIF + 行移位 + 像素16 EN 带 @v452-467,
  ASCII 记录 v=(452,468) 窗=带)
  + EN_STRINGS.RES #25 @0x377E000 (I797 重编码, 32,365B+零填, 条目表不动)
- GR.IMG: EN_STRINGS.RES #902 @0xCAC1750 (I797 同步, 32,366B+零填)
- NTSC_IKE.RES: OBJ0-3 行记录 H=26 (round22 下沉补偿)
- ELF (SLUS_P_V43 谱系 + SWKERN 1B): 全部补丁逐字记录于 docs/PATCH_INVENTORY.md

### `GR_ZH353` 增量 (12px 双字库, `tools/iso_build/patch_zh12px.py`)
- **MENU.IMG 图集**: 12px 字形带 `v=480..495` (实测全空) 铺 14 字形, 步进 14 texel, 格 8×16,
  字形 5×8 居中 (偏移 x+1/y+4)
- **FONT.RES 字表槽 @0xB9120**: 三面 idx 100..113 → 12px 记录
  (`(0, 8, u+288, 480, u+296, 496)`, 依据引擎采样 `u = 记录 u0 − 288`);
  `default` 面 idx 114/115 未用; 重压 1443 B / 槽 4421
- **`default` 面占位码位**: `0x5E`('^')/`0x60`('`') ← idx 16/17 的**原 16px 字形**;
  idx 45(`M`)/16(`0`)/17(`1`) → 12px 字形 (**保留原推进 `rec[1]`**)
- **ELF**: 字符串资源 `GR-` VA `0x57ED20` → `0x8E 0x8F 0x91`
- **MENU.IMG #170 `<MapName>`**: `M01 Caves` → `\x90\x84\x85 Caves` (条目搬到末尾 0x378B000,
  stored 23182→23293, real 不变 90910); `GR.IMG #661` 同份副本**默认不改** (实测无效且有副作用)
- **MENU.IMG #25 / GR.IMG #902**: 日期/时间字符串 `Apr 16, 2008`→`Apr \x60 6, 2\x5E\x5E 8`;
  `05:45`→`\x5E 5:45` (占位码位必须 `< 0x80`, 否则宽度被当全宽致文本左移)
- **未改动**: 制作组名单 `GR.IMG #551..#565` (0 字节差异); `GR.IMG #661`

---

## `GR_ZH94` → `GR_ZH101` 链 (2026-10-12, round44–round51)

> 本文件此前停在 12px 双字库那条支线; 下面是主链最近 8 个盘的谱系。详细过程见各 `docs/REPORT_*.md`。

| 盘 | sha256 | 关键内容 |
|---|---|---|
| `GR_ZH94` | `1cac50c1…f301` | 图集 dump 撕裂伪影定位: 像素区是 **GIF 封包流**(非定长行) ⇒ dump 默认改**引擎视图** |
| `GR_ZH95` | `c1f5d849…b5afafb` | ★ **字库紧凑重排(repack)首次上线** ⇒ 改了码位但**未重编码 SFXML `name=` 属性**, 埋下 49 处标题错字 |
| `GR_ZH96_fix` | `4486d576…c709` | 记录带 `yrow-1` 残墨修复 (20 格 / 76 texel); `patch_zh96_record_band.py` |
| `GR_ZH97` | `6fc96615…b5098` | 发布包 (`docs/REPORT_release_zh97.md`) |
| `GR_ZH98` | `f0fc6d8f…992ac3` | 回收 20 个人名缺字 + 字库清理(残墨 0); **round51 两处修复的基底** |
| `GR_ZH99` | 同 `GR_ZH98` | 无数据改动(逐字节相同) |
| `GR_ZH100` | `190575f6…` | 28 字字形修复(但 **49 个标题仍错**) |
| **`GR_ZH101`** | **`e1d303ae4b102d553edaeeaff12d4ea268eba74cedaf4d5c0bd8a9b2360cc45c`** | ★ **最终盘**: 28 字字形 + 49 个标题两处都含 |

### `GR_ZH101` 构筑

```
python tools/iso_build/make_build.py GR_ZH101 \
    --from work/builds/GR_ZH98/temp/r51/cand_both2.iso \
    --inject-csv work/builds/GR_ZH98/text --no-font-repack
```

- 与基底 `GR_ZH98` 差异 **39703 字节**: 字库像素容器内 **2062**(28 个单字节汉字的字形) +
  文本区 **37641**(49 个 SFXML `name=` 属性); **ELF / PVD / 两个 IMG 条目表 / 制作组名单
  `GR.IMG #551..#565` / PAK 48B 包头 / FONT.RES 差异全 0**。
- ⚠ `make_build.py` 的 `--patch` 是**单值参数**(传两次只有最后一个生效) ⇒ 本轮先用两个补丁做出
  候选盘 `cand_both2.iso`, 再以它为基底构筑。建议改成 `action='append'`。

### 两处修复

1. **28 个单字节汉字(0x80..0x9B)字形错位**(自 `GR_ZH93` 起):
   字形被写进别人的记录格(偏 +12/+13/−16 格) ⇒ 游戏里画的是别的字。
   根因: round43 `patch_zh93_font_ext_fix.py` 用 **flat 容器坐标**写字形, 引擎按**引擎图**采样;
   round45/46 只修了对偶格与行 24 的 6 个记录码。
   修法: `patch_zh51_single_byte_band.py`(写 28 个正确位图 + 清 64 个窗外孤儿像素 + 写盘前硬断言)。
2. **49 个 SFXML `name=` 标题陈旧码位**(自 `GR_ZH95` 重排起):
   标题在 `<item name="…">` 属性里, `dump_text_csv` 只抓 `<text>` ⇒ 从不进可注入表 ⇒ 从不被重编码。
   修法: `patch_zh51_sfxml_titles.py`(只改 58 字节, 全在 `name=` 属性内, `<text>` 一字未动;
   重压帧 41648 ≤ 槽 49700 ⇒ IMG 条目表不动, MENU.IMG 其余 685 条目逐字节不变)。

### 验收

单格字库 `single_cell_font.py`: **1382 格, 错误 0 / 逐像素完全一致 1371-1373 (99.85%)**, 两条独立路径自证;
审计缺失 0; `--check-only` exit 0; `dump_font` 自查 1504/1504; 残墨 0;
标题实机 A/B **270/299 帧逐像素相同**(差异仅标题那一个字 `；`→`？`)。
**重排保持 `--no-font-repack`**(容量增益 0 + 会破坏非 `<text>` 中文串)。
