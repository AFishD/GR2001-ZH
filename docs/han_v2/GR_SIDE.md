# GR_SIDE.md — GR.IMG 侧汉化（教程句 / 武器名 / 队友名）结构对账、工艺与实测

> 日期：2026-09-13。基底 `han_v2\GR_K99.iso`（GR.IMG @LBA 19175，1,550,563,328B，4070 条目）。
> 终盘 = `C:\gr_build\iso\GR_ZH9.iso` = **GR_ZH8b.iso（SLUS_P_V7.elf + MENU_ZH8b≡MENU_ZH8.img）
> 原样拷贝 + GR.IMG 白名单字节 @LBA 19175 原位写入**（尺寸/LBA 不变）。
> 工具 = `hanliu\tools\gr_build.py`（一键）、`han_v2\tmp\gr_side\patch_gr.py`（补丁+白名单
> 自检入口）；工作区 `han_v2\tmp\gr_side\`；
> dump = `C:\gr_build\dumps\{grzh9_probe, grzh9_t01, grzh8_t01ab, grzh7b_t01ab, grk99_t01ab2, grzh9vm_t01, grzh9_v7}`。

---

## 〇、结论速览

| 项 | 判定 |
|---|---|
| GR.IMG 结构对账 | 与 MENU.IMG 完全同构；**FONT.RES 展开态 7222B 与 COMMON.PAK 400,659B 和 MENU 原版逐字节相同** → MENU 侧 ZH8 字库产物可同源复用（独立写回 GR 槽位，差异复验通过） |
| 教程句 G12-G18 | 238 条译文（trans_zh8 复用 232 + 训练标题 6）压缩帧原位覆写，blob **41,504B ≤ 47,619**（余 6,115），帧走 osz 总和=real=128,668 实证 |
| 武器/动作名 | GR.IMG STRINGS.TXT **stored=2,587 ≠ real=6,561（LZO 压缩，推翻任务书 "stored==real 明文" 预设）** → 未压缩明文 **空隙重定位**（MENU 侧 EN_STRINGS.TXT 同款实证工艺）；94 行换值；实测窗口内 PS2 未读该文件（启动期读的是 MENU.IMG EN_STRINGS.TXT） |
| 队友名 | 训练 TOE 5 名 Ghost（rifleman-01/11/48/58/59）ActorName **单字节码**（0xAF-0xFE 非保留，不经 lead/cave，规避 nav25 指令面板风险）+ 空格补齐等长 |
| boot 快判 | **PASS**：exit=0 / 73s / needle WPNRPK74 f150 首中 / 快照非黑 |
| 简报屏中文 | **PASS**（f26536：信息 / 训练1 - 越野训练 / 2008年3月15日｜13:00｜晴天 / 任务目标 / 载入中...）——但文字源 = **MENU.IMG RES**（ZH8-ab 对照盘 GR 侧全 EN 同样显示同一中文） |
| 任务内教程框判定 | **被共享崩溃阻断**：ZH9 / ZH8 / ZH7b / **ZH9vm（原版 MENU+v6 ELF+GR 补丁）** / **ZH9 终盘（v7 ELF）** 在 **f26575 同一 PC（0x383fe000）`R5900 Exception: Jump to unmapped recLUT page`**，原盘同 nav 跑满 59,900 帧——崩盘唯一公共因子 = **ELF 文本补丁本体（U/V6/V7 三世代）**；译制 MENU 与 GR 补丁均被剥离排除，归因收窄见 §五 |

---

## 一、GR.IMG 结构对账（与 MENU.IMG 逐字段）

档案头/条目表/名字区与 MENU.IMG 完全同构（0x830 起 48B/条，[6]/[7]/[8]=stored/real/off）。
GR 4070 条目（MENU 686）；GR 数据区起 0x46800，档案 1,550,563,328B。

| 条目 | GR.IMG off / stored / real | MENU.IMG 同名条目 | 差异记录 |
|---|---|---|---|
| EN_STRINGS.RES | 212,604,752 / 47,619 / 128,668 | 58,187,776 / 47,570 / 128,545 | 同构 8 子流 **[16384]×7+[13980]**（MENU 末流 13857）；66 组 2232 条与 MENU 完全平行，**仅 12 条文本差**（G12-G18.I002 'blast area'→'mission area' 措辞、G49/G50 的 0x92 引号差异、G19/G21/G44 简报微差），译文按位对齐有效 |
| FONT.RES | 212,710,976 / 4,421 / 7,222 | 24,140,80*（menu_orig）/ 4,421 / 7,222 | **展开态 7,222B 逐字节相同**（decode 后比对） |
| COMMON.PAK | 236,797,520 / 400,659 / 400,659（明文） | 同尺寸 | **逐字节相同**（sha1 ec98f3b2…）→ GR 侧 atlas = MENU 原版同一纹理的拷贝 |
| STRINGS.TXT | 213,086,608 / **2,587** / 6,561 | （MENU 无此条目） | **压缩态**（单子流 LZO）——推翻 "stored==real 明文" 预设 |
| EN/DE/ES/FR/IT_STRINGS.TXT | 212.6-213.1M / ~2,750 / ~6,930 | 同构 | 压缩态；MANUAL §三.7 已证 "EN_STRINGS.TXT 值从不显示" |
| .ATR ×1193 | 各自 stored==real（纯 XML） | 无 | ActorName 标签全部在文件相对偏移 124 处 |
| IKE.RES | 212,773,600 / 38,048 / 319,009 | — | 解码无错；不含武器名表（'weapons and items' 不在其内） |

训练阵容（TRAINING.TOE 解码实证）：Alpha = rifleman-48（Horace Dominguez）；
Bravo = rifleman-58（Garner Maxwell）、rifleman-11（Samuel Beard）、rifleman-59（Trent Norris）；
另补 rifleman-01（Corey Moss，队员池首位）共 5 名 Ghost。

## 二、GR 侧字库（任务 1）

**前提实证**：GR 的 FONT.RES 展开态与 COMMON.PAK 和 MENU 原版逐字节相同 → ZH8 字库产物
（`tmp\zh8\ft_slot_zh8.bin` 4,421B DP 帧 + `COMMON_PAK_ZH8.bin`）可同源复用；构建器仍按
「独立写回」执行并强制复验：
- 槽位对账（off/stored/real 与已确证值一致）→ PASS；
- ft_slot 回环（展开 5,302B、子流无错）→ PASS；
- PAK 差异全部落在 atlas 表面 `0x1069..+262144` 内（表外 0 字节）→ PASS。
- FONT_CAPACITY.md §九 三条铁律（CLUT rows0-1 禁碰 / atlas rows2-127 禁写 / 同 face 带高一致
  CH=15）随 ZH8 产物全部继承；GR 侧无需重绘（同一输入 → 同一安全输出）。

## 三、文本汉化（任务 2）

### 3.1 教程句（G12-G18，29 句 ×7 组拷贝 + 标题）
- 译文 238 条 = `trans_zh8.csv` 的 G12-G18 **232 条**（MENU 侧已上屏配方，PS2 手柄化措辞：
  「随时按 START 键退出训练」「左摇杆/右摇杆」）+ **新增 G13-G18.I030 训练标题 6 条**
  （训练2 - 轻型武器 / 训练3 - 榴弹 / 训练4 - 重武器 / 训练5 - 机枪 / 训练6 - 爆破 /
  训练7 - 指挥；G12.I030「训练1 - 越野训练」trans_zh8 已有）。全部字表内（759 字），0 条放弃。
- 写回：解码 8 子流 → 换值（v6 编码）→ 其余条目装饰修复（[0xA4..0xAD]+≥0xA1 插 0x20；
  本轮实际 0 条触发）→ 复刻子流布局重压缩 → **blob 41,504B ≤ 47,619**，逐子流回环 PASS；
  帧尾之后的槽内旧字节保留（MENU 侧 ZH7/ZH8 同款工艺），引擎按 Σosz==real 停走
  （补丁副本实测：帧走至 41,504B 处 Σosz=128,668 恰好等于 real）。

### 3.2 武器/物品名（STRINGS.TXT 家族）
- 官方 PC 中文名（pc_official `strings.txt` 键值）对齐 GR TXT 222 行：**98 键字表内可用，
  实际替换 94 行**（89 行官方即中文 + 6 行人工适配：手雷/M9-消音/MP5-消音/备用弹/观测镜/
  所有小组攻击；PC 键位类 key_* 33 行宁少勿错跳过）。v6 全编码（单字节/对/ASCII）。
- **存储约束实测**：GR STRINGS.TXT stored=2,587 < real=6,561 → 明文写回必超槽位 → 采用
  **空隙重定位**（MENU 侧 EN_STRINGS.TXT 实证工艺）：未压缩 6,090B 写入 BNK 音频库间
  **6MB 垫区 @481,042,432**（不与任何条目重叠），条目表仅改该行 stored/real/off 三字段。
- **消费端真相（实测）**：boot→崩溃点窗口内 cdvd 对 GR.IMG 的 STRINGS.TXT **新旧位置均零读取**；
  启动期 f236-362 实际读取的是 **MENU.IMG 的 EN_STRINGS.TXT**（LBA 804,698-804,725，
  ZH8 盘该文件即武器名启动期来源、内容仍基本 EN——属 MENU 侧范围）。GR.IMG STRINGS.TXT
  是否在更晚窗口（武器拾取/HUD）被读，因崩溃点提前无法判定 → 94 行替换作为无害沉淀
  （diff 白名单含其表行+垫区）。

### 3.3 队友名（5 名 Ghost ActorName）
- 为规避 nav25「ATR 中文名→指令面板挂死」前科，全部采用**单字节码**（0xAF-0xFE 非保留；
  引擎原生 Latin-1 直通路径 → default face 记录，不经 13-lead/cave），尾部空格补齐原字节长：

| ATR | 原名 | 译名 | 编码后 |
|---|---|---|---|
| RIFLEMAN-48.ATR | Horace Dominguez | 雷一枪 | 6B+10 空格 |
| RIFLEMAN-58.ATR | Garner Maxwell | 火枪 | 4B+10 空格 |
| RIFLEMAN-11.ATR | Samuel Beard | 小雷 | 4B+8 空格 |
| RIFLEMAN-59.ATR | Trent Norris | 向前 | 4B+8 空格 |
| RIFLEMAN-01.ATR | Corey Moss | 何斗 | 4B+6 空格 |

## 四、补丁形态与自检（patch_gr.py / gr_build.py）

`hanliu\tools\gr_build.py` = 一键七阶段（对账→字库→RES→TXT→ATR→白名单自检→ISO 组装）；
`tmp\gr_side\patch_gr.py` 为任务口径入口。补丁副本 = `tmp\gr_side\GR_patched.img`
（1,550,563,328B，尺寸不变 → ISO LBA 不变，无需重拼）。

自检结果（全 PASS）：
- 差异 **131,727B / 27,141 区段，白名单外 0**；白名单 = FONT 槽 + COMMON.PAK + RES 槽
  （前 41,504B）+ TXT 垫区 + 5×ATR + 条目表 TXT 行 12B；
- 条目表 4070 行除 TXT 行 stored/real/off 12B 外**逐字节不动**；
- 容器/子流/槽三级回环 + token 键集不变断言。

## 五、实测判定（gsrunner 有效 7 次 + 1 次 0 帧路径误写，预算 8/8）

| # | 盘 | 内容 | 帧数 | 结果 |
|---|---|---|---|---|
| 1 | GR_ZH9 | boot 快判 | 4,300 | **PASS**：exit=0、73s、WPNRPK74 f150 首中、快照非黑（UI 渲染正常） |
| 2 | GR_ZH9（v6 时） | T01 nav（k99t02 配方：start@11400 → 训练→T01 → 29500 起 LUp 跑动） | 59,900（请求） | **f26575 终止**：`R5900 Exception: Jump to unmapped recLUT page (PC: 0x383fe000)`；f26536 简报屏中文完整（信息/训练1 - 越野训练/2008年3月15日｜13:00｜晴天/任务目标/载入中...） |
| 3 | GR_ZH8（GR 侧全 EN 原版） | 同 nav | 同 | **f26575 同 PC 同帧崩** → GR 侧补丁（字库/RES/TXT/ATR）**排除**；且简报中文照出 → 简报文字源 = MENU.IMG RES |
| 4 | GR_ZH7b（SLUS_P_U 旧 ELF） | 同 nav | 同 | **f26575 同 PC 同帧崩**（简报屏 ZH7 时代中文：信息/晴天/任务目标，标题仍 EN）→ 排除 v6 独有 |
| 5 | GR_K99（原盘，路径误写致 0 帧退出，未计入有效运行） | — | 0 | 重跑见 #6 |
| 6 | GR_K99（原盘） | 同 nav | 59,900 | **跑满 exit=0 无崩溃**：f26536 简报（EN）→ 载入完成 → **任务内教程框 EN 基准确认**（f27094=G12.I012 移动框、f29698=G12.I021 站姿/卧倒框，nav 可连续推进多页） |
| 7 | GR_ZH9vm（**原版 MENU** + v6 ELF + GR 补丁全量） | 同 nav | 同 | **f26575 同 PC 同帧崩** → 译制 MENU **排除** |
| 8 | GR_ZH9 终盘（**v7 ELF**（SLUS_P_V7，ZH8b 基底）+ 译制 MENU + GR 补丁） | 同 nav（32,000 帧） | 同 | **f26575 同 PC 同帧崩** → v7（仅改 cw 直 UV 分支，cctc/ds16/sw 逐字节不变）与 U/V6 共享此 bug，三世代实锤 |

> 终盘 GR_ZH9.iso 已按任务书改用 **ZH8b 基底（SLUS_P_V7.elf + MENU_ZH8b≡MENU_ZH8）** 重挂
> GR 补丁（ELF/MENU/GR 三区逐字节复验）；实验盘 GR_ZH9vm.iso 已删（判别数据记录于下表）。

### 5.1 关键定位（进任务崩溃 = ELF 补丁共通 bug，跨任务共享阻断项）
- 崩溃点 = T01 载入完成瞬间（简报「载入中...」→ 3D 世界/HUD 初始化）。判别矩阵：
  | 盘 | ELF | MENU | GR 补丁 | 结果 |
  |---|---|---|---|---|
  | 原盘 | 原版 | 原版 | 无 | **跑满 PASS（教程框 EN 正常）** |
  | ZH7b | SLUS_P_U | 译制 | 无 | 崩 |
  | ZH8 | SLUS_P_V6 | 译制 | 无 | 崩 |
  | ZH9（v6 时） | SLUS_P_V6 | 译制 | 有 | 崩 |
  | ZH9vm | SLUS_P_V6 | **原版** | 有 | 崩 |
  | ZH9 终盘 | SLUS_P_V7 | 译制 | 有 | 崩 |
- 逻辑收束：GR 补丁（#3 无之亦崩）与译制 MENU（#7 无之亦崩）都被**必要条件排除**；
  崩盘唯一公共必要因子 = **ELF 文本补丁本体**，且 **U/V6/V7 三世代全部触发**——bug 位于
  三者共享的 cave 架构（ds16/sw/cctc 钩子及挂点；v7 只改了 cw 直 UV 分支的 scaleX 乘法），
  任务载入路径存在前端 nav 未覆盖的调用形态，返回/寄存器状态被破坏 → 野跳 0x383fe000。
  **归因移交 ELF/MENU 侧**；这也是本项目所有译制盘（不论 MENU 还是 GR 侧）无法进任务的
  总根因。
- 历史口径修正：k99t02「进 T01/教程框出现」的 dump 已删无法复核；ZH7b/ZH8/ZH9 三盘
  复现表明该证据很可能即为同一**简报屏**（含任务地点照片与信息框），而非任务内教程框。
- GR 侧判定现状：boot + 简报屏中文 + 静态三级自检全 PASS；任务内教程框（GR.IMG RES 的
  真正消费端）中文上屏与队友名/武器名实机显示，待 ELF 侧修复 cave 后用同一 nav 回补
  （GR_ZH9 内容无需改动，原盘教程框 EN 基准帧已留存于 dumps\grk99_t01ab2）。

## 六、与 MENU 侧差异清单（GR 侧特有 / 需注意）

1. RES 槽 47,619/real 128,668（MENU 47,570/128,545）；子流末流 13,980（MENU 13,857）。
2. GR RES 原文与 MENU 平行但非全同（12 条差异）→ 译文必须以 **GR 侧原文** 为基准对位
   （本轮 238 条经位对齐校验）。
3. STRINGS.TXT 为压缩态且 GR/MENU 两份独立；PS2 启动期实际消费 **MENU.IMG 的
   EN_STRINGS.TXT**（武器名显示的现役来源），GR 份在实测窗口未被读。
4. ATR 仅 GR.IMG 有（1,193 个纯 XML）；ActorName 相对偏移固定 124。
5. 字库/COMMON.PAK 与 MENU 原版字节相同 → 字库产物可直接同源复用（仍独立写回+复验）。
6. 简报屏文字（标题/日期/天气等）实测来自 **MENU RES**（G12-G18/G58），GR RES 的消费端
   是任务内教程框/字幕/HUD——两份 RES 并非简单主备关系。

## 七、产物与遗留

产物：
- `C:\gr_build\iso\GR_ZH9.iso`（终盘，1,648,164,864B，ZH8b/v7 基底）；`hanliu\tools\gr_build.py`；
  `han_v2\tmp\gr_side\{patch_gr.py, build_zh9vm.py, run_grzh9_probe.py, run_grzh9_t01.py,
  run_grzh7b_ab.py, run_grzh8_ab.py, run_grk99_ab2.py, run_grzh9vm.py, run_grzh9_v7.py,
  gr_strings_zh.txt, txt_hits.json, atr_patch.json, gr_res_zh_blob.bin, gr_res_container.bin}`；
  dump `dumps\{grzh9_probe, grzh9_t01, grzh8_t01ab, grzh7b_t01ab, grk99_t01ab2, grzh9vm_t01,
  grzh9_v7}`。实验盘 GR_ZH9vm.iso 已删（判别数据记录于 §5.1 矩阵）；
  tmp\gr_side 的 1.5G 工作副本（GR.img/GR_patched.img）已删，gr_build.py 可再生。

遗留：
1. **ELF 文本补丁的任务载入 bug（f26575 野跳 0x383fe000）** —— 四盘判别矩阵（§5.1）已把
   根因收束到 SLUS_P_U/V6 共享的 cave 架构（前端 nav 未覆盖的任务内调用形态）。修复后用
   `run_grzh9_t01.py` 同一 nav 回补：任务内教程框中文上屏（对照原盘 EN 基准帧 f27094/
   f29698）、队友名单字节码显示、指令面板 nav25 复查。
2. PS2 启动期武器名来源 = **MENU.IMG EN_STRINGS.TXT**（实测 f236-362 读取；内容仍基本 EN，
   属 MENU 侧范围）；GR.IMG STRINGS.TXT 在崩溃点前零读取，真实消费窗口待定。
3. ATR 中文名实机显示效果未验证（同阻断 1）；gr_build.py --no-atr 开关已备回退。
4. G13-G18 训练标题为自拟（官方 PC 仅训一）；简报天气「晴天」来自 MENU G58.I472（ZH8 已译）。
