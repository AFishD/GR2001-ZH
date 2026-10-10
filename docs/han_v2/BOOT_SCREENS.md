# BOOT_SCREENS.md — 开机/前端早期画面文字资源定位与汉化可行性（2026-09-14 调查轮）

> 任务：查清「读取记忆卡」「按 START 键」等开机画面未汉化的文字到底存在哪。
> 方法：纯静态 + 已有证据 + 2 次 gsrunner 验证跑（原盘 boot 600 帧 / GR_ZH12 6500 帧），
> 禁止 computer use。未修改任何游戏文件与成品 ISO。
> 证据目录：`tmp\boot_probe\`（cdvd.log、快照、纹理解码图、contact sheet、run 脚本）。

---

## 一、结论速览（逐屏判定表）

| # | 画面 | 显示文本 | 存储位置 | 渲染方式 | ZH12 现状 | 汉化判定 |
|---|---|---|---|---|---|---|
| 1 | 开机记忆卡检查「Accessing memory card (8MB)…」 | 同左（整段） | **MENU.IMG 条目5 `EN_MESSAGE_MC_4.RSB`**（预渲染纹理 384×178，ISO LBA 776658） | **贴图直显**（非字体） | 未译（英文烤图） | **需贴图重绘**（可行，同尺寸原位覆写，无字体依赖） |
| 2 | 记忆卡异常 3 态（空间不足 / 未格式化 / 无卡 Caution，含 △Retry ✕Continue） | 整段+按钮 | **MENU.IMG 条目10/15/20 `EN_MESSAGE_MC_1/2/3.RSB`**（LBA 776827/776997/777166） | 贴图直显 | 未译 | 同上 |
| 3 | 标题屏「Press START button」 | 同左 | **MENU.IMG EN_STRINGS.RES 组 G58.I007**（条目25，ISO LBA 804698） | 引擎字体（RSFont） | **已译「按 START 键」**（0xB9/0xB2） | **已完成**（建议下次 nav 跑 f11000-12000 快照实锤） |
| 4 | 标题屏背景（Tom Clancy's GHOST RECON 标志画 + 2002 Ubi Soft/Red Storm 行） | 烤图 | MENU.PAK 内部条目 `start_bg`（JPEG 640×448，条目230，LBA 799585） | 贴图 | 保留原文 | **不处理**（logo 类烤图，属美术资产） |
| 5 | 档案选择「Choose your profile.」 | 同左 | G58.I045 | 字体 | 已译（选择档案） | 已完成 |
| 6 | Name Entry「Enter your name.」/ File #1-3 | 同左 | G58.I044 / I026-I028 | 字体 | 已译（ZH8 轮「输入名字」徽章实机实证） | 已完成 |
| 7 | 加载转轮圆环中央「Loading...」 | 同左 | **SLUS ELF 静态串，5 语言槽表**：EN @文件偏移 **0x4780D8**（`Loading...\0`，RAM 0x578058 实证）；邻槽 FR/DE/IT/ES（0x478020-0x4780C0） | 引擎字体 | 未译 | **ELF 同长度字节替换即可**（≤10B，新发现可汉化点，工作量极小） |
| 8 | 加载转轮圆环（图形） | 无文字 | MENU.IMG 条目38/39 `LOAD_NEW_1/2.RSB`（480×480 8bpp）+ ELF 名串 `load_new_1/2.rsb`@0x478000 | 贴图 | — | 无需处理 |
| 9 | 任务载入「Loading Mission... Please Wait.」/「LOADING...」 | 同左 | G58.I269 / I125 | 字体 | 已译（载入中...） | 已完成 |
| 10 | LOGOUBI / LOGOREDSTORM / INTRO 视频 | 烤在视频里 | MENU.IMG 条目35-37（.PSS） | 视频 | 保留 | 不处理（惯例） |
| 11 | 游戏内记忆卡对话框（保存/载入/格式化 30 条长句） | G58.I772-I801 | MENU.IMG EN_STRINGS.RES | 字体（IkeDialog） | **仅少部分已译**（I787 等已译；I772/I774/I797 等长句保留 EN，含 ®=0xAE） | 现有 RES 管线补译即可（注意对话框自动换行） |

**一句话回答用户**：「读取记忆卡」那屏 = `EN_MESSAGE_MC_*.RSB` **预渲染贴图**（因为记忆卡检查发生在字符串资源加载之前），不是没翻译的字体文本；「按 START 键」屏的文本 = G58.I007，**当前终盘 GR_ZH12 已经译了**（显示于片头视频之后的标题屏，与旧快照「f150-370=Press START 屏」的时序认知不同，见 §三）。

---

## 二、「驼峰 needle」之谜解开（认知修正）

- 旧认知：needle `'PressSTARTbutton'`（EE 0x5AB103）、`'Chooseyourprofil'`（0x5AB418）是内部 token/资源名。
- **实情：gsrunner 的 needle 匹配本来就是空格不敏感的。** 跑 #1 的 f390 EE RAM 转储里，
  0x5AB103 处的字节就是**带空格的显示文本 `Press START button`**（`Choose your profile.`、
  `Enter your name.` 同区），而 `b'PressSTARTbutton'`（真驼峰）在 32MB RAM 中**零命中**。
  这些地址 = EN_STRINGS.RES 编译进 RAM 的字符串 DB（条目格式 `{u32 len|0x80000000}{chars}`）。
- 同理 `WPNRPK74`（0x57F1C8，f150 首中）= ELF 内武器名 "RPK74"（ELF LBA 2597 处有明文）
  经运行时去空格/加前缀构造的**武器图标资源 ID**，是唯一真正的"运行时构造串"；
  它在 MENU.IMG 读取（f236）之前就出现，来源是 ELF 自带武器数据库。
- 全 ISO 字节搜索 'Press START button' 零命中的原因：EN_STRINGS.RES 是 LZO1X 压缩态，
  字面量段被控制字节切碎（压缩流里连 "Insufficient"+控制+“space on memory card”都断开）。
  解码后（`lz77_decode.decode_entry`）G58 组 802 条全部可读（`han_v2/res_strings_all.txt`）。

## 三、加载时序铁证（跑 #1：原盘 boot 600 帧，cdvd.log 逐帧）

| 帧 | 读取内容 | 说明 |
|---|---|---|
| f0-f159 | ISO LBA 16-18582 | SYSTEM.CNF + SLUS_206.13 全量流式载入（37MB） |
| f160-f212 | LBA 18583-19174（ELF→GR.IMG 间隙） | ELF 尾/模块区 |
| **f236** | **MENU.IMG 头/名字表**（LBA 776286+） | 前端档案开始加载；**GR.IMG 此时零读取**（前端全部资源来自 MENU.IMG） |
| f243-f249 | MENU.0-2 BNK_00 声库 | |
| f249-f257 | MENU.3 **COMMON.PAK**（字体 atlas） | |
| **f257-f273** | MENU.4 **FONT.RES** + **MENU.5-24 全部 MESSAGE_MC 纹理**（实测读 EN/DE/IT 变体，至 DE_MC_3 中途停止） | **记忆卡消息纹理在字符串资源之前预载** |
| f260 | needle `newfontrevisedrs` 首中（字体已就绪） | |
| f374-f384 | MENU.283 EN_SPECIAL_FEATURE.XML + **MENU.25 EN_STRINGS.RES** | 字符串资源此时才读 |
| **f390** | needle 'PressSTARTbutton'/'Chooseyourprofil' 首中（0x5AB103/0x5AB418） | = RES 编译进 RAM 字符串 DB 的时刻 |
| f567-f573 | MENU.29 IT_STRINGS.RES + **全部 5 语言 STRINGS.TXT** | |
| f573+ | MENU.35 LOGOUBI.PSS 开始流式播放 | 之后：LOGOREDSTORM → 转轮(load_new) → 标题屏 → INTRO |

**为什么记忆卡消息必须是预渲染纹理**：记忆卡检查在 f257-273 发起并立即显示消息
（快照 f300/f400），而 EN_STRINGS.RES 到 f381 才开始读——此刻字符串 DB 根本不存在，
字体串路线不可用，所以厂商把这 4 条消息按语言烤成 20 张 RSB 贴图（5 语言×4 态）。

**跑 #1 像素实证**：snap_f00000300/f00000400 所示消息框与 `EN_MESSAGE_MC_4.RSB`
解码图**逐字一致（含换行）**；且 RAM 转储中 'Accessing memory card' **零命中**
（若走字体渲染，DB 里必有该串）→ 贴图直显铁证。

**跑 #2（GR_ZH12 6500 帧）时序修正**：f300 记忆卡贴图（英文，ZH12 未译此贴图）→
f1500 Ubi logo 视频 → f2500-3000 转轮（ELF 串 "Loading..." 英文，因 ELF 未动）→
**f4000-5000 标题屏=纯 start_bg 背景画，无 Press START 文字**（blink 关相/文字在
INTRO 之后；历史 nav 配方 start@11400 才是文字相）→ f5500+ INTRO 暗场。
故「f150-370 = Press START 屏」的旧快照时序认知作废：f150 首中的是 WPNRPK74（ELF 侧），
标题屏文字相在 f10000 之后。

## 四、各资源定位明细

### 4.1 MESSAGE_MC 纹理（记忆卡 4 态消息）— 用户所指「读取记忆卡」屏
- 条目（MENU.IMG，stored==real=69,404 B，同尺寸原位覆写安全）：

| 条目 | 名 | 内容（EN） | ISO LBA |
|---|---|---|---|
| 5 | EN_MESSAGE_MC_4.RSB | Accessing memory card (8MB) (for PlayStation®2) in MEMORY CARD slot 1. Do not remove… | 776658 |
| 10 | EN_MESSAGE_MC_1.RSB | Insufficient space … Insert a memory card … △Retry ✕Continue | 776827 |
| 15 | EN_MESSAGE_MC_2.RSB | Unformatted memory card (8MB)…. Press ✕ button to continue. △Retry ✕Continue | 776997 |
| 20 | EN_MESSAGE_MC_3.RSB | Caution! If you wish to save your game data, insert a memory card …（§21.3 空白卡 Caution 即此图） | 777166 |

- 每条目后有 DE/ES/FR/IT 平行变体（条目 6-9/11-14/16-19/21-24，同尺寸）。
- wire RSB 格式（RES_AB_TEST/§12.2 已证可自制）：`{u32 5}{u32 w=384}{u32 h=178}{2,2,2,2}`
  + 1024B CLUT（256×BGRA）+ 68,352B 8bpp 表面。
- 解码图：`tmp\boot_probe\EN_MESSAGE_MC_1..4.png`。

### 4.2 G58 组（MENU.IMG EN_STRINGS.RES 主 UI 池 802 条）— 开机相关条目
- I007 `Press START button` / I025 `File Select` / I026-028 `File #1-3` /
  I044 `Enter your name.` / I045 `Choose your profile.` / I091-095 选人提示 /
  I125 `LOADING...` / I269 `Loading Mission... Please Wait.` / I270 `Loading Replay...` /
  I538 `Quick loading...` / I772-I801 记忆卡 30 条。
- ZH12 终盘核对（`gr_build\tmp\zh12\MENU_ZH12.img` 解码）：I007=按 START 键、
  I044/I045/I125/I269/I787 等已译；**I772/I774/I797 等长句保留英文**（1342 条选译未收录）。
- 渲染路径：字体（RSFont 三 face），与已实机验证的主菜单/Name Entry 中文同一条路。

### 4.3 ELF 静态语言表（新发现）
- `Loading...`/`Please wait!` 5 语言槽表，紧随 `load_new_1.rsb`/`load_new_2.rsb` 名后：
  FR@0x478020 / DE@0x478058 / IT@0x478070 / ES@0x4780A8 / **EN@0x4780D8**（文件偏移；
  实机 RAM = 文件偏移 + 0x100000 − 0x80，EN 槽 RAM 0x578058 实测命中）。
- 渲染走引擎字体 → ZH12 字库已在，**把 EN 槽 10 字节换成 CJK 码串+`\0` 即上屏**
  （对字节 A1..AD lead 或 76 单字节码均可，V10 ELF 绘制链已支持；注意槽长勿越界，
  下一槽 FR 前有充裕填充）。同表 `Please wait!`（0x4780E8）可同法处理。

### 4.4 start_bg / LOAD_NEW / LOADING.PAK
- `start_bg`：MENU.PAK 内部条目（目录=名字+u32 JPEG 长度+JFIF），640×448 标题画，
  **无 Press START 文字**（`tmp\boot_probe\pak_start_bg.png`）。
- `LOAD_NEW_1/2.RSB`：480×480 转轮图（无文字）。
- `LOADING.PAK`（4.7MB）：无 JPEG（GS swizzle 纹理），未发现文字元素。

## 五、建议实施路径（优先级序）

1. **MESSAGE_MC 纹理汉化**（用户痛点，唯一"不可直接改文本"的屏）：
   - 保留 CLUT、边框、△/✕ 按钮图标像素；仅清并重绘文本区（16px SimHei 或 12px Zpix，
     色值取原文字像素的 CLUT 索引）。
   - 4 张图分别写：正在读取记忆卡…/记忆卡空间不足…/记忆卡未格式化…/注意！…（官方 PC
     译文见 `Ghost Recon\Data\Shell\STRINGS.RES` 可对齐）。
   - **5 个语言变体写同一中文图**（boot 实读 EN/DE/IT，显示 lang0=EN；全覆写消除歧义）。
   - 写回 = stored==real 同尺寸原位覆写（img_patch inplace 或直接 ISO 内 LBA 写入），
     条目表零改动；异常回滚=原字节还原。风险评级：低。
2. **ELF "Loading..." 槽替换**（10 分钟级）：EN 槽 0x4780D8 写 `载入中...\0` 等价 CJK
     码串；走既有 build_PS 管线或直接 ELF 字节补丁+重拼 ISO。
3. **Press START 屏实锤**：下次 nav 跑（start@11400 配方）加 f11000-12000 快照，
   确认「按 START 键」上屏（机制上无障碍：RES/字体均在文字相之前就绪）。
4. **游戏内记忆卡长句补译**：G58.I772-I801 未译条目按 RES 管线补（blob 余量 8,870B，
   足够；注意 ® 与对话框换行宽度）。

## 六、证据与产物清单（tmp\boot_probe\）
- `dump_boot600\`：cdvd.log（40,315 行逐帧 LBA）、grlog.txt、snap_f*.png（f300/f400=MC_4 贴图实证）。
- `dump_zh12_title\`：ZH12 6500 帧 snap_*（f4500=纯背景标题画）。
- `EN_MESSAGE_MC_1..4.png`：4 态纹理解码图；`LOAD_NEW_1.png`：转轮图；`pak_start_bg.png`：标题背景。
- `zh12_title_contact.png`：ZH12 时序 contact sheet；`run_boot600.py` / `run_zh12_title.py`：跑脚本。
- 已清理 4×32MB EE/IOP RAM 转储（判定后即删）。

---

## 七、实施记录（2026-09-14 实施轮：MC 贴图 + ELF Loading 槽 → GR_ZH15 交付）

> 承接 §五实施路径 ①②。新件 `tmp\bootscreen\`（脚本/产物/证据）；终盘 = `C:\gr_build\iso\GR_ZH15.iso`
> （sha256 `8de326b9e83d6436161c8ccba5af860cd1dfd392ea6a8ac2d68b8687c4ddd092`，= GR_ZH13 原样 + 两区补丁）。

### 7.1 ①MESSAGE_MC 20 贴图中文重绘（完成）
- **解码**：wire RSB = 28B 头 `{u32 5}{u32 384}{u32 178}{2,2,2,2}` + 1024B CLUT(BGRA) + 68,352B 8bpp
  表面（自顶向下）= 69,404；entry5 解码与上轮参考 PNG **逐像素一致**。条目表名序
  = [EN,DE,ES,FR,IT]×{MC_4,MC_1,MC_2,MC_3}（条目 5-24，与 §4.1 LBA 全对上）。
- **配色结构**：灰框 (179,179,179) 4px 环；正文蓝 (110,150,240)+14 级 AA 渐变；橙 (225,144,32)
  仅 MC_1/MC_3（500KB）；按钮白 (230,230,230)；△圈 x188-212 / ✕圈 x265-292（y142-163）。
  **20 条目 CLUT 各不相同**（17 种哈希；蓝 22-36 档全有；橙 DE 变体是 (183,117,26) 系；
  MC_4 组 CLUT 无橙/白）→ 必须逐条目用其自身调色板。
- **工艺**（`tmp\bootscreen\mc_redraw.py`）：文字几何/AA 强度按态算一次 → 逐条目映射到该条目
  CLUT 渐变族取档（无近邻色损失）；清空区 (14,13)-(372,140) + 按钮文字区 (214,140)-(262,170)/
  (296,140)-(370,170) 写该条目纯黑索引；其余 surface 字节零触碰。SimHei 16px（SimSun 11px 上标 ®，
  SimHei 无 ® 轮廓）；行位对齐原图（MC_1/2/3 y=19 起、MC_4 y=16 起，pitch 25）。文案：
  正在读取插槽 1 中的记忆卡 (8MB)…／剩余空间不足+500KB(橙)…／尚未格式化+按 × 键继续／
  注意！…或按 × 键不保存而继续；按钮 △重试 ✕继续。同态 5 语言条目全覆写同一中文图。
- **自检**：20/20 条目头+CLUT 逐字节不变；MENU 尺寸/条目表不变；全档案 diff 仅在 20 条目数据区
  （outside_diffs=0，diff_bytes=793,924）。预览 `tmp\bootscreen\mc\zh_MC1..4.png`。

### 7.2 ②ELF「Loading.../Please wait!」槽替换（完成）
- 槽表实勘与 §4.3 一致；**5 语言一并中文化**（决策：boot 实读 EN/DE/IT 变体，全覆写消除分支歧义；
  FR/DE/IT/ES 槽位均实测充裕）。
- 字节：`Loading...→载入中...` = A2A9 A1A7 D6 2E2E2E 00（载=(A2,A9) 入=(A1,A7) 中=单字节 D6，
  与译文 RES 同编码）；`Please wait!→请等待!` = A3D6 A1F8 A2DF 21 00。每槽先断言
  {原串+\0 填充} 再整槽清零写入。**diff=152B，限 0x478020..0x4780F3**；ELF 尺寸不变
  （`tmp\bootscreen\elf_patch.py` → SLUS_ZH15.elf）。

### 7.3 ③组装 + 实测（GR_ZH15）
- 组装（`tmp\bootscreen\zh15_iso.py`）= GR_ZH13.iso + SLUS_ZH15.elf@LBA295 + MENU_MCZH.img@LBA776286；
  尺寸 1,648,164,864 不变；回读 PASS；**全盘 diff 白名单（ELF 槽区+20 条目区）外 0 组**。
- **实测 A（boot 4000 帧，-grsnap 2 + -grdumpwin 240 300，memcards_zh12）**：
  记忆卡检查画面 **f262-584 中文上屏**（此前 f257-584 为英文贴图），f588 转黑 → f660 LOGO 视频。
  证据 = `tmp\bootscreen\dump_boot\snap_f00000270.png`（等 f262-558 窗帧）；
  逐帧墨迹剖面：f260=0 → f262=9601 恒定 → f588=0。-grdumpwin 240-300 共 61 帧 RAM 转储按约执行后已清理。
- **实测 B（zh2 nav 40000 帧，-grsnap 62，与 zh13_r2 基线同节奏）**：
  - 跑满 exit=0、669s（基线 669s）；WPNRPK74 **f150 首中共 4231 = 基线 4231**（日志行数 8679=8679）。
  - 645/645 快照逐像素对比基线：**179 帧差异全部归因、零未解释差异**——
    ①f310-558（5 帧）=MC 贴图 EN→ZH（本轮）；②f2852-3534（11 帧）=转轮文字（本轮）；
    ③f11594-21576（163 帧，恒 101px）=**上游 ZH13 的 Name Entry $ 键重绘**（zh13_r2 基线跑在
    $ 修复前 10:30，修复后 ISO 10:54；ZH15 f12772 与修复后验证跑 zh13_ne2 同帧 **diff=0** 实证）。
  - **转轮中文上屏**：f2852「载入中...」（暗相，10x 增强清晰）、f2914「请等待!」（亮相 8x 清晰）
    = `tmp\bootscreen\mc\zh15_2852_zoom10.png / zh15_2914_zoom8.png`。§一 #7 判定兑现。
- **Press START 实锤 = 推翻 §一 #3 的字体串判定**（待办 3 执行结果）：
  f11160 标题屏快照（`tmp\bootscreen\mc\zh15_title_text_2x.png`）显示 **英文** "Press START button"。
  而本轮 RES 解码：EN_STRINGS.RES 中 I007=按 START 键（0xB9 START 0xB2）**在译**、全 RES 零
  "START button" 字样，ELF/5 语言 STRINGS.TXT 亦无该串 → 屏显必来自**非字体资源**。
  定位：MENU.PAK=档案条目 **230**（3,099,360B，非旧记 799585 LBA 的内部推断），内部目录含
  **`multi_pressstart`**（@371696，头 {0x13}{512}{256}{187}+GS 描述符，≈32.9KB 压缩纹理，
  与 COMMON.PAK 系同族压缩格式）= 头号嫌疑；另有大量 `text` 命名条目（其中数个为字体版权串）。
  → **修正判定：标题提示 = PAK 内部预渲染贴图**，汉化需解 PAK 内部压缩纹理后重绘（下轮）。
- 运行预算：gsrunner 2 次（boot 78s / nav 669s）。实验产物已清理（RAM 转储/批量快照删除，
  证据帧+日志保留）。

### 7.4 第二实施轮（2026-09-14：MC 贴图 v4 Zpix 统一重绘 + Press START 格式定案 → GR_ZH16T）

> 承接 §7.1-7.3。用户实测反馈「开机读取-老字库与新字库同时出现」，本轮诊断 + 重绘修正。

**① 「混显」根因诊断（实勘截图 `Human_Test_Output\GR_ZH15.iso\开机读取-老字库与新字库同时出现.png`）**：
截图文字 = G58.I791（正在读取数据.请勿移除记忆卡槽1里的记忆卡(8MB) (for PlayStation®2),重启或关闭主机.），
橙框+游戏场景背景 → 是**游戏内记忆卡对话框（RES 字体渲染管线）**，非 boot MC 贴图（boot 贴图窗口
f262-586 渲染统一无混显，ZH15 实测帧可证）。混显机制 = 引擎字体链：CJK 走新 Zpix 图库、Latin/数字
走游戏原始 face（老字形）→ 同句混排。**归字体链任务（字库扩容轮）处理，不在贴图轮范围**；
但 v3 MC 贴图用 SimHei 16px 确与游戏内 Zpix 风格不一致 → 本轮统一 Zpix 重绘（v4）。

**② MC 贴图 v4 Zpix 统一重绘（完成，`tmp\bootscreen\mc_redraw_zpix.py` → MENU_MCZH.img）**：
- 在库字符（CJK+全角标点 66 个）直接从最新字库图集 zh14（COMMON_PAK_ZH14.bin@SURF0x1069 +
  layout_zh14.txt）逐格拷墨（13×16 cell，cell_top=行顶）；缺库字符（ASCII/（）/× 等 29 个）PIL
  Zpix.ttf 12px 渲染（XOR 实证与图集同字形）；**禁止引用老字形 PNG/COMMON_PAK_ZH12.bin**。
- 墨迹 1-bit 硬像素 → 该条目 CLUT 渐变族最亮档（原文字核心色）。行位/清空区/按钮区与 v3 相同。
- 标点注意：图集全角标点（。，、）为手工校正位（句号/顿号左下），必须拷图集墨而非 PIL 直绘；
  ® 用 PIL Zpix 小号（图集 ® 在老字形保护区 rows0-131）。
- 自检：在库汉字 766 格 XOR=0（glyph_check.json 空）；20/20 头+CLUT 逐字节不变；MENU 尺寸/条目表
  不变；全档案 diff 仅 20 条目数据区（outside_diffs=0，diff_bytes=778,952）。

**③ Press START（MENU.PAK 条目230 multi_pressstart）格式定案（本轮深挖，改写不可行 → 保留英文，已知限制）**：
- 条目真身 = @371688..379856（payload 8,168B；§7.3 的「≈32.9KB」是目录漏识别 padlayout/platoonscreen
  两条目所致的误算，已修正）。MENU.PAK 内部 123 条目（扫描法）+ JPEG 型（start_bg 等）未含在此 123 中。
- 条目布局完全解开（blackbar/multi_pressstart/platoonscreen/t01_training 四条目链验证一致）：
  `{u32 type=2}{u32 nameLen}{name\0}{u32 psm=19(CT8)}{u32 w}{u32 h}{u32 csize1}{u32 dsize1}{desc1}
   {u32 csize2}{u32 dsize2}{desc2}`，恰好走完到下一条目名。dsize = GS 包展开尺寸 = 16+原始数据
  （desc1: 1040=16+CLUT1024；desc2: 131,088=16+512×256 表面）。
- desc1/desc2 = 游戏自研 **GS 上传描述符程序**（多条目共享头字节 `80 00 02 68 17 10 8a 85`/
  `00 x0 26 74 00 42 b1`；像素非内联原码，csize2 ≈ 表面 6%）。
- **排除 LZO1X**：引擎唯一解压器 = `lzo1x_decompress@0x4300D0`，仅被 `diinputbuf::underflow` 调用
  （流缓冲层，16KB 块，服务 IMG 档案 stored<real 压缩条目，EN_STRINGS.RES/FONT.RES 即此类）；
  menu230 内层与标准 LZO1X 及零前置变体均不兼容（INVALID BACK）。COMMON.PAK 字库纹理（type=0）=
  另一格式 `{19}{512}{512}{0x410}{0x8040}{0x08000000}…+RAW 线性表面`（zh5_pakscan 已证）。
- 不可行定量：非压缩 wire rsb 同内容 = 132,124B ≫ 条目 8,168B；MENU.PAK stored==real=3,099,360B
  内嵌 MENU.IMG（ISO 定长布局）无增长空间 → **按预案保留英文贴图**。后续轮可攻 desc 程序编码
  （custom GS push-buffer，需从 ThreadDecodeTexture/UIQuadModel 渲染路径反推）。

**④ 组装 + 实测（GR_ZH16T，实验盘名，终盘命名避开 ZH16 留给字库扩容轮）**：
- `tmp\bootscreen\zh16t_iso.py` = GR_ZH13.iso + SLUS_ZH15.elf@LBA295 + MENU_MCZH.img(v4)@LBA776286；
  尺寸 1,648,164,864 不变；回读 PASS；全盘 diff 白名单（ELF 槽区+20 MC 条目区）外 0 组。
- boot 4000 帧（-grdumpwin 240 300）：**PASS** — MC4「正在读取插槽 1 中的记忆卡 (8MB)…」Zpix 统一
  字形 f262-586 上屏（证据 `tmp\bootscreen\boot16\snap_f00000270.png`），与 v3 同窗同时序
  （f260=0 → f262 起 ink 恒 6,063 → f590=0），v4/v3 同帧 diff=7,580px（纯字形差）。无新旧混显。
- ELF 10 槽复核正确（载入中.../请等待! ×5 语言）；运行预算：本轮 gsrunner 2 次（boot 78s + nav 669s）。
