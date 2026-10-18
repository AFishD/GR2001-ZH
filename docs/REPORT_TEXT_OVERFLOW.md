# REPORT_TEXT_OVERFLOW.md —— 「文本层 ⇒ 卡死」具体机理的取证与决定性验证盘

> 执行者：汉化执行者（文本溢出/长串审计子代理）· 2026-10-15
> 仓库根 `C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization`
> **只读**：`third_party\orig\**`、`work\builds\GR_CVAR\**`、`work\builds\GR_AB\**`、`work\builds\GR_ZH113b\**`、
> `work\builds\GR_EN_ORIG\**`、`%LOCALAPPDATA%\PCSX2` **一字未改**。
> 写入范围仅：`work\builds\GR_TXT\**`、本文件。
> **未跑模拟器**（本任务不需要；实机判据在用户手上）⇒ 无并发污染。
> 未 commit / 未切分支 / 未 merge。**未使用 `Select-Object -First N`**（一次误用已立即改用
> `Get-Content`/重定向到文件，见 §9「纪律偏差」）。

---

## 0. 一句话结论（先说会改变你下一步判断的四条）

```
① ★ 任务书里「中文串天生更长 ⇒ 字形数可达英文 2 倍」这个前提，**被数据推翻了**：
   两个 LANG 容器各 2232 条，中文 payload 总量 55,751 B，英文 114,617 B（MENU）/
   114,740 B（GR）⇒ 中文只有英文的 **48.6%**。
   增长的条目只有 **45/2232 = 2.0%**，**最大增长只有 +10 字节**，且集中在
   「布拉格堡，北卡罗来纳州」「防空导弹」「局域网」「确认」「视频同步」这类
   **联机/控制台/选项标签**族，不是队伍选择界面的名字。
   ⇒ 若病根真是"串变长"，那它必须由**极少数 +1..+10 字节**触发 —— 这本身就是一个
   可被 TXT_01/TXT_03 直接否证或证实的强命题。**别的"文本层"机理必须同时被考虑。**

② ★ 崩溃点不是字库，是 **RSUIString（UI 字符串对象）**：
   `pc=0x541038` = `RSUIString::Substring(int,int) const` **+0xD8**，
      崩溃指令 = `+0xE4` 的 `sb zero,0(a0)`（写结尾 NUL），**addr=0x0 [store]**；
      同函数 `+0x74` 的 `sh v0,0(s0)` 把长度存成 **u16**，
      而拷贝循环的上界是**未截断**的 `end − start` ⇒ **u16 截断型堆溢出**（固定容量候选 1）。
   `pc=0x541eb0` = `RSUIString::~RSUIString()` **+0x20**，块内 `+0x28 sw vtable,0(this)` /
      `+0x2C lw m_str,4(this)` ⇒ 析构器被作用在**野指针 this** 上；
      17 次观测到的 `this` 是**等差数列、公差恰 = 0x5A72D8 = RSUIString 的 vtable 常量**
      （该块自己写进去的那个常量）⇒ 某个循环的指针步进被"vtable 常量"驱动，不是随机走飞。
   同链还有 `pc=0x541ca0` = `RSUIString::operator=`（引用计数赋值）、
   `pc=0x102764` = `mmalloc_free+0x34`、`pc=0x102a30/0x102aa4` = `small_free`
   ⇒ 现场是「**共享字符串对象 + 分配器**」，与字库/图集无关。
   这 6 个 PC 所在区间在**原盘 / CVAR_04 / ZH113b 三盘上逐字节相同**（§3.1）。

③ ★ 三张盘已产出（`work\builds\GR_TXT\`，全部**槽外差异 0 run**）：
   `TXT_01_short`（中文全部 ≤ 英文长度）/ `TXT_03_len_eq_en`（中文全部 **==** 英文长度）
   / `TXT_02_orig_text`（汉化盘 + 英文文本）。
   **判定表见 §5** —— 这三张盘能把「长度」与「内容/编码」一刀切开。

④ ★★ **本轮新发现的候选 R（我给的权重最高）**：汉化对偶码把 **286 个汉字的第二字节**
   做成了 **0xB1 / 0xB5**（各 144 / 170，散在 **221 条**里；XML 另有 158 处），
   而**原盘 `DrawString` 对这两个字节有硬编码"图标特判"**（`0x219C08/0x219D2C`），
   命中后走 `AddOneWord(..., flag=1)` ⇒ **容量只有 2 的副包**（`fontmgr+0x4C`，`slti ,2`）
   ⇒ 每遇到一次就多一轮 flush。**这是"内容驱动、与长度无关"的形状**，
   与 §2 的"中文比英文短一半"完全自洽；`CVAR_04` 用原盘 ELF ⇒ **没有 DBCS cave ⇒
   这 286 处全部走图标路径**。主顶点包的固定容量同时确证为 **1280 字**（`slti ,1280`）。
```

---

## 1. 方法与证据索引（全部可复跑）

| # | 命令 | 产出 |
|---|---|---|
| 1 | `python work\builds\GR_TXT\tools\txt_audit.py` | `audit/A_len_audit.json`、`audit/A_top_growth_*.csv` |
| 2 | `python work\builds\GR_TXT\tools\txt_audit_xml.py` | `audit/A_xml_audit.json`、`audit/A_xml_top_growth_*.csv` |
| 3 | `python work\builds\GR_TXT\tools\txt_a_detail.py` | `audit/A_detail.txt`、`audit/A_detail_rows.json` |
| 4 | `python work\builds\GR_TXT\tools\txt_bufscan.py` | `audit/B_funcfixed.txt`（10 个函数全文反汇编）、`audit/B_fixedmem.txt`（231 个常量长度内存调用站点）、`audit/B_stackbuf.txt`（801 个 ≥256 B 栈帧函数） |
| 5 | `python work\builds\GR_TXT\tools\txt_ba_verify.py` | `audit/B_verify.txt`（三盘逐字节同一性 + 指令回读） |
| 6 | `python work\builds\GR_TXT\tools\txt_grammar.py` | 容器文法对照（证明项目 `parse_lang` 口径正确，见 §4.1） |
| 7 | `python work\builds\GR_TXT\tools\txt_xmlview.py` / `txt_xmlpair.py` | XML 节点口径核对（§2.3） |
| 8 | `python work\builds\GR_TXT\tools\txt_capacity.py` | `RSFontMgr` 顶点包容量常量（1280 / 2）+ `fontmgr+0x6C` 的写入者 + **`0xB1/0xB5` 形态普查**（§3.6 候选 R） |
| 9 | `python work\builds\GR_TXT\tools\txt_build.py` | 三张盘 + 每张 `.meta.json` + `summary.json` |
| 10 | `python work\builds\GR_TXT\tools\txt_verify.py` | `audit/C_verify.txt`（产物盘独立终检，从盘上重读） |

**反汇编工具**：`work\tools\cave_dis.py`（`diso` 模式）+ `work\tools\cave_syms.py`（ELF 内 `.symtab`，38,722 符号）。
两者**只读**；ELF 取 `third_party\orig\ps2\slus_out\SLUS_206.13`（原盘解出）。

---

## 2. A. 长串 / 字形数审计

### 2.1 容器级读数（第 ①② 项交付）

| 容器 | 条目 | EN payload | ZH payload | **变长条目** | 缩 | 等 | **最长增长** | EN blob | ZH blob | EN used_end | ZH used_end |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `EN_STRINGS.RES@MENU` | 2232 | 114,617 B | **55,751 B** | **45** | 1639 | 548 | **+10 B** | 128,545 | 128,545 | 128,537 | 69,671 |
| `EN_STRINGS.RES@GR` | 2232 | 114,740 B | **55,751 B** | **45** | 1639 | 548 | **+10 B** | 128,668 | 128,668 | 128,660 | 69,671 |
| `EN_SPECIAL_FEATURE.XML`（69 个 `<text>`） | 69 | 84,065 B | **47,857 B** | **0** | 58 | 11 | **0** | 116,430 | 116,486 | 116,426 | 80,101 |
| `EN_SPECIAL_FEATURE.XML`（145 个 `name="…"`） | 145 | 1,501 B | **1,383 B** | **28** | 64 | 53 | **+10 B** | — | — | — | — |

* **条目 1:1 对齐已验证**：两容器 EN/ZH 都是 2232 条，且 `(group, index)` 序列逐条相同
  （`A_len_audit.json` 的 `keys_1to1 = true`）；`CVAR_04` 的 3 个容器 blob 与 `GR_ZH113b` **逐字节相同**
  （`zh113b_eq_cvar04 = true`）⇒ 下面所有数字对两张盘同时成立。
* **容器总长与槽位不变**：`stored` / `real` 在 EN 与 ZH 上**完全相同**
  （MENU 47,570 / 128,545；GR 47,619 / 128,668；XML 49,700 / 116,430），
  与任务书「容器总长与槽位不变、逐条 payload 长度可不同」一致 ✓。
* **中文容器的"缩水"是结构性的**：`used_end` 从 128,537 → **69,671**，即 ZH 的 blob 尾部有
  **58,874 B 全零**（校验见 §4.1：`rebuild_lang` 断言原尾部全零通过）。
* XML 的 `<text>` 口径是**完整的 69/69**：另有 **25 个 `<text/>` 自闭合空元素**（EN/ZH 各 25），
  不是漏匹配（`txt_xmlpair.py`：`open <text> 69 / close </text> 69 / selfclose <text/> 25 / open any 94`）。
* XML 的 blob 长度在汉化后 **116,430 → 116,486（+56 B）**，而 IMG 条目 `real` 仍是 **116,430**
  ⇒ **`real` 比实际解压总量少 56 B**（汉化盘既有小瑕疵，登记为观察项，本次不改）。

### 2.2 增长最猛的 N 条（第 ③ 项交付，含 key 与界面线索）

`EN_STRINGS.RES@MENU` 的 45 条**全部**如下（`@GR` 的 45 条逐条相同，因为两份容器同源）：

| key | en len | zh len | 增长 | 英文原串 | 中文（按游戏 charset 解码） |
|---|---|---|---|---|---|
| `G12.I031` `G13.I031` `G14.I031` `G15.I031` `G16.I031` `G17.I031` `G18.I031` | 13 | 23 | **+10** | `Ft. Bragg, NC` | 布拉格堡， 北卡罗来纳州 |
| `G39.I002` `G53.I002` | 13 | 22 | +9 | `Ft. Bragg, NC` | 布拉格堡，北卡罗来纳州 |
| `G58.I727` | 5 | 12 | +7 | `DS MP` | 沙漠风暴联机 |
| `G58.I726` | 5 | 11 | +6 | `GR MP` | 幽灵行动联机 |
| `G55.I002` | 15 | 20 | +5 | `Near Tacoma, WA` | 华盛顿州，塔科马附近 |
| `G56.I002` | 12 | 17 | +5 | `Ft. Drum, NY` | 德拉姆堡， 纽约州 |
| `G03.I002` | 17 | 21 | +4 | `You are now king.` | 你现在成了中心基地之主。 |
| `G42.I014` `G47.I014` | 3 | 7 | +4 | `SAM` | 防空导弹 |
| `G57.I002` | 15 | 19 | +4 | `Hot Springs, CO` | 温泉城， 科罗拉多州 |
| `G08.I002` | 17 | 20 | +3 | `You are now king.` | 你们队现在占据中心基地。 |
| `G45.I013` | 2 | 5 | +3 | `HQ` | 指挥部 |
| `G58.I284` `G58.I321` | 3 | 6 | +3 | `LAN` | 局域网 |
| `G59.I005` | 11 | 14 | +3 | `LAST HIT BY` | 上次被…（含 2 个图标占位） |
| `G59.I006` | 14 | 17 | +3 | `LOAD LAST SAVE` | 载入最近一次的存档 |
| `G65.I021` | 5 | 8 | +3 | `Blood` | 血腥效果 |
| `G58.I003` `G58.I004` | 2 | 4 | +2 | `Ok` / `OK` | 确认 |
| `G59.I010` | 5 | 7 | +2 | `BURST` | 三弹连发 |
| `G65.I071` | 5 | 7 | +2 | `VSync` | 视频同步 |
| `G65.I098` | 7 | 9 | +2 | `USE EAX` | 使〔图标〕EAX音效 |
| `G10.I005` | 3 | 4 | +1 | `SAR` | 搜救 |
| `G21.I013` | 11 | 12 | +1 | `Georgian HQ` | 格鲁吉亚总部 |
| `G28.I005` | 11 | 12 | +1 | `M10 Vilnius` | M10 维尔纽斯 |
| `G31.I014` | 11 | 12 | +1 | `KA-50 Hokum` | KA-50 短吻鳄 |
| `G58.I029` `G58.I173` `G58.I185` `G58.I204` `G58.I236` `G58.I328` `G58.I546` `G58.I547` `G58.I686` `G58.I724` | 2..10 | 3..11 | +1 | `NEW` `NAME:` `GO` `Stealth` `Kills` `ADD` `WON` `YOU WON` `Max IFF: ` `GR Mission` | 新建 / 名字： / 开始 / 隐藏能力 / 杀敌数 / 添加 / 胜利 / 你胜利了 / 敌我识别： / 幽灵行动®任务 |
| `G59.I013` `G61.I007` | 7 / 3 | 8 / 4 | +1 | `MAX IFF` / `Run` | 敌我识别 / 奔跑 |

**最长条目**（中文普遍比英文短很多）：

| key | zh | en |
|---|---|---|
| `G43.I010` | 768 | 1,580 |
| `G40.I006` | 753 | 1,480 |
| `G24.I007` | 737 | 1,440 |
| `G47.I008` | 731 | 1,514 |
| `G44.I010` | 710 | 1,472 |

（ZH 长度 == 768 的只有 1 条、≥700 的 5 条；EN ≥1500 的有 2~3 条。**中文没有撞上任何"整"阈值**，
不是被构建器按 768 截断的形状。）

**界面线索判定**：增长条目全部落在 **联机（MP）/ 控制台 / 选项 / 战绩 / 地名** 族
（`G58` = 联机与控制台标签、`G59` = 战绩、`G65` = 视频/血腥选项、`G03/G08` = 任务胜利文案、
`G12..G18/G39/G53/G55/G56/G57` = 地名）。**没有一条是队伍选择界面的人名**
（人名走 `.ATR` 的 `ActorName` / `ClassName`，不在 `EN_STRINGS.RES` 里）。
⇒ 「队伍选择界面崩溃」的**触发串**很可能不是这批增长条目，而是**编码/解码路径**（见 §5 判定表）。

### 2.3 字形数（第 ② 项交付）—— 三种口径并列

| 口径 | EN | ZH | ZH/EN |
|---|---|---|---|
| **A. 每字节 = 1 字形**（任务书口径 / 也是原盘引擎的实际口径，见 §3.6） | MENU 114,617 / GR 114,740 | **55,751** | **0.486 / 0.486** |
| B. 每 2 字节 = 1 字形（若字体开了双字节标志 `font+0x24`） | MENU 57,309 / GR 57,370 | 27,876 | 0.487 / 0.486 |
| C. XML `<text>` 正文，每字节 = 1 字形 | 84,065 | 47,857 | 0.569 |

```
★★ 结论：无论取哪种口径，中文的"字形数"都只有英文的 **0.49 ~ 0.57 倍**，
   而不是任务书假设的「可达英文的 2 倍」。
   ⇒ 「中文字形数是英文的 2 倍 ⇒ 撑爆顶点/字形缓冲」这条机理，
     **在容器级数据上不成立**（不是"没证据"，是"证据反向"）。
```

**补充（口径 A 的正确性有反汇编依据）**：原盘 `RSFontMgr::DrawString`
（VA `0x219A70`，§3.6 有全文）在 `+0x33C` 处的原义是
`bne lbu 36(font),0 → i+=2 else i+=1` —— 即**按 font 级标志决定步进**。
汉化把它改成"从栈上读变长步长"（`work\builds\GR_AB\tools\ab_build.py` 打靶的就是这 8 字节）。
`CVAR_04` 用的是**原盘 ELF**，所以它走的是原义。原盘上这个标志对英文/中文是**同一个字体对象**，
因此"中文字形数 / 英文字形数"完全由**字节数**决定 —— 也就是口径 A。

---

## 3. B. 「被撞坏的缓冲」——定位与判断

### 3.1 地址映射与三盘同一性（`audit/B_verify.txt`）

```
ELF: PT_LOAD#0  file_off=0x80  va=0x100000
     ISO = VA − 0x6C780        （ELF 起始 ISO 0x93800，故 ELF_ISO_BASE(VA=0x100000)=0x93880）
     FILE = VA − 0xFFF80       （ELF 文件内偏移）
```

| VA 区间 | 内容 | EN vs **CVAR_04**（原盘 ELF） | EN vs **ZH113b** |
|---|---|---|---|
| `0x540F00..0x541F50` | **RSUIString 字符串类**（Substring / operator= / ~dt / Left / Right / FindChar） | **0 B 异** ✅ | **0 B 异** ✅ |
| `0x101C00..0x102B00` | **dlmalloc**（chunk_free / chunk_alloc / mmalloc_free / small_free） | **0 B 异** ✅ | **0 B 异** ✅ |
| `0x219A00..0x21AF40` | `DrawString` + `RSFont` 度量/UV | 0 B 异 ✅ | **57 B 异**（汉化点） |
| `0x21C280..0x21D300` | `SetTextID` / `DoWordWrap` / `AddOneWord` 邻域 | 0 B 异 ✅ | **36 B 异**（汉化点） |
| `0x2ECDA0..0x2ECFC0` | `GetUISoldierAbbreviateName` | 0 B 异 ✅ | 4 B 异 |
| `0x307090..0x307170` | `GetActorNameAbbreviated` | 0 B 异 ✅ | 4 B 异 |

⇒ **崩溃现场（RSUIString + 分配器）在两张盘上都是原盘代码**
（与 `REPORT_NULLDEREF_ZH113b.md` §1.1 的"18 个停顿 PC 逐字节相同"一致，本次把范围扩到了
整个字符串类 + 整个 dlmalloc）。
**⇒ CVAR_04 上不存在"汉化 cave 写错"这一层；触发器只能是喂进去的数据。**

### 3.2 `pc=0x541038` —— `RSUIString::Substring(int start, int end) const` +0xD8

符号：`0x00540F60  Substring__10RSUIStringCFii  size=408`（`cave_syms.py`），覆盖 `0x540F60..0x5410F8`。

原盘反汇编（`audit/B_funcfixed.txt` 的 `Substring__10RSUIStringCFii` 段）：

```
540F60  addiu sp,sp,-128
540F7C  v0 = 0x5A0000 ; 540F88 v0 += 0x72D8   → v0 = 0x5A72D8 = RSUIString 的 vtable
540F9C  jal __nw__FUi(8)                      ; 造一个 8 字节的 RSString 节点
540FAC  v1 = end − start
540FB0  v0 = v1 + 1 ; bgtz → 540FCC
540FD0  sb 1, 2(s0)                           ; refcount = 1
540FD4  sh v0, 0(s0)                          ; ★★ len = (end − start + 2) 存成 u16（截断）
540FD8  jal __nwa__FUii( lhu 0(s0) )          ; ★ 分配 = 截断后的 len 字节
540FE0  sw v0, 4(s0)                          ; data = 缓冲
540FE4  a0 = data ; a2 = len
540FEC  jal memset(data, 0, len)
540FF8  slt at, start, end ; beq → 541038
541004  a1 = 0                                ; i = 0
   loop:                                      ; ★ 循环上界 = **未截断的** end − start
541008  v1 = lw 4(this) ; v1 = lw 4(v1)       ; src = this->m_str->data
541014  v0 = lw 4(obj)                        ; dst = obj->data
541018  v1 = v1 + start
54101C  a0 = lb 0(v1)                         ; c = src[start++]
541024  v1 = v0 + i
541030  bne (start<end → loop)
541034  sb a0, 0(v1)                          ; dst[i] = c        ← 无边界检查
541038  ★ emulog 的 pc 停在这里（= 该**基本块**的入口，见 §3.4）
54103C  v1 = 0x5A72D8
54104C  a0 = lw 4(lw 0(s1))                   ; dst = obj->data
541050  a0 = a0 + i
541054  ★ sb zero, 0(a0)                      ; dst[i] = 0  ← emulog: addr=0x0 [store]
541058  sw v1, 0(s5)                          ; result->vtable = 0x5A72D8
541060  sw obj, 4(s5)                         ; result->m_str = obj
541064  a0 = lw 4(s5) ; 541068 lbu v1,2(a0) ; 541070 sb v1+1,2(a0)   ; refcount++
```

**判断**：
1. 这个函数是**字符串切片**：`__nw__(8)` 造节点 → `__nwa__(len)` 造数据缓冲 → 逐字节拷贝 → 补 NUL。
   **它是"把数据搬进新缓冲"的函数**，与任务书猜测一致。
2. **`0x541038` 是块入口，不是出错指令**。块 `0x541038..` 里唯一的 store 是
   `+0x1C` 的 `sb zero,0(a0)`（写结尾 NUL），而 `a0 = dst + i`。
   `addr=0x0` ⇒ **`dst + i == 0`**（`dst==NULL`、或 `i` 把指针回卷到 0）。
   **⇒ 现场是"往一个 NULL/回卷的字符串缓冲写结尾 NUL"**，不是越界写大地址。
3. ★ **函数内部自带的固定容量缺陷（固定缓冲候选 1）**：
   `len` 存进 **u16**（`+0x74` 的 `sh`），但**拷贝循环的上界是 `end − start`（32 位，未截断）**，
   且 NUL 写在 `dst[end−start]`。一旦 `end − start ≥ 65534`：
   `len` 回卷成小值 ⇒ `__nwa__` 只给小缓冲 ⇒ **拷贝循环写爆堆**。
   ⇒ **"固定缓冲容量"的候选值 = `(u16)(end−start+2)`，即 65535 字节的长度域**；
   有效缓冲容量 = `lbu`/`lhu` 出的 `len`。
   （本盘数据里最长的串只有 768/1,580 B，所以这条**本轮没有触发**；登记为原盘固有缺陷。）

### 3.3 `pc=0x541eb0` —— `RSUIString::~RSUIString()` +0x20

符号：`0x00541E90  __dt__10RSUIStringFv  size=184`，覆盖 `0x541E90..0x541F48`。

```
541E90  addiu sp,sp,-64 ; sd ra,48(sp) ; … ; s1 = this ; s0 = a1(删除标志)
541EA8  beq s1, zero → 541F2C                  ; this == NULL 就跳过
541EB0  ★ emulog 的 pc（= 该基本块入口；块从分支的落空边开始）
541EB4  v0 = 0x5A72D8
541EB8  ★ sw v0, 0(s1)         ; this->vtable = 0x5A72D8   ← emulog: addr=<this> [store]
541EBC  ★ v1 = lw 4(s1)        ; v1 = this->m_str           ← emulog: addr=<this>+4 [load]
541EC0  beq v1, zero → 541F18
541EC8  v0 = lbu 2(v1) ; 541ECC v0 -= 1 ; 541ED0 sb v0,2(v1)   ; ★ m_str->refcount-- (u8)
541ED8  bne v0, zero → 541F14
541EE0  s2 = lw 4(s1)          ; m_str
541EEC  v0 = lw 4(s2)          ; m_str->data
541EF8  sh zero, 0(s2)         ; m_str->len = 0
541EFC  jal __dla__FPv(m_str->data)     ; operator delete[]  ← 真正 free
541F08  jal __dl__FPv(m_str)            ; operator delete
541F10  sw zero, 4(s1)         ; this->m_str = NULL
541F18  blez (int)(s16)a1 → 541F30
541F24  jal __dl__FPv(this)    ; 若 a1>0 连 this 一起删
```

**判断**：这是**共享字符串（引用计数）的析构**：把 vtable 写回、`m_str` 引用计数 −1、
归零就 `delete[] data` + `delete m_str`。
emulog 观测到的 `this`（= `addr`）是：

```
0xcf3f1098, 0xcee49dc0, 0xce8a2ae8, 0xce2fb810, 0xcdd54538, 0xcd7ad260, 0xcd205f88,
0xccc5ecb0, 0xcc6b79d8, 0xcc110700, 0xcbb69428, 0xcb5c2150, 0xcb01ae78, 0xcaa73ba0,
0xca4cc8c8, 0xc9f255f0, 0xc997e318      （emulog 逐个 store/load 成对出现，共 17 对）
```

相邻差 **恒为 0x5A72D8** —— 也就是**同一基本块刚写进去的那个 vtable 常量**。
⇒ 某个循环的**步进值 = 0x5A72D8**（被污染的数据里含 vtable 常量），
析构器被反复作用在一串野指针上，每次递减一个"vtable 大小"。
**这条比"随机野指针"信息量大**：污染源把 **0x5A72D8 当成了长度/步长**在用。
（首个 `this=0xcf3f1098` 落在 `0xC0000000+` 内核段 ⇒ 必然 `TLB Miss`。）

### 3.4 ★ emulog 的 `pc=` 是「重编译块入口」，不是出错指令地址（本轮新证据）

`third_party\emu\pcsx2_src\pcsx2\vtlb.cpp:537`：
```cpp
const std::string message(fmt::format("TLB Miss, pc=0x{:x} addr=0x{:x} [{}]",
                                      cpuRegs.pc, addr, mode ? "store" : "load"));
```
而 `R5900.cpp:145` 在"异常发生在延迟槽"时用 `cpuRegs.pc − 4` 作 EPC
⇒ `cpuRegs.pc` 是**当前指令自己的地址**。

但**实测反证**：`pc=0x541eb0` 处是 `lui v0,0x005A`（`3C02005A`，无内存访问），
而同一 pc 下成对出现 `[store]` 与 `[load]`。块内实际的内存访问是
`+0x08 sw` / `+0x0C lw`（偏移 8 / 4**字节**，而 `addr` 报的是**全地址**）。
⇒ **日志里的 `pc` = PCSX2 重编译基本块的起始地址**
（`0x541EB0` 正是 `beq`@`0x541EA8`+延迟槽之后的落空边；`0x541038` 正是 `beq`@`0x541000` 的跳转目标）。
**这一条把"崩溃指令"从"不可判定"变成"可判定"**：读 §3.2/§3.3 时按"块内所有访存"来对，而不是只对第一条。

**同链其它 PC 的归属**（`cave_syms.py`）：

| pc | 所属函数 | 偏移 | 报出的 addr | 读法 |
|---|---|---|---|---|
| `0x541038` | `RSUIString::Substring(int,int) const` | +0xD8 | `0x0 [store]` | 块内 `+0x1C` `sb zero,0(dst+i)` ⇒ `dst+i==0` |
| `0x541CA0` | `RSUIString::operator=(const RSUIString&)` | +0x0 | `0x3`/`0x4 [load]` | 块内 `+0x14 lw v1,4(a0)` / `+0x18 lw v0,4(a1)` / `+0x24 lw a0,4(v1)` ⇒ `a0/a1 = 0xFFFFFFFF/0` |
| `0x541EB0` | `RSUIString::~RSUIString()` | +0x20 | `<野> [store]`+`[load]` | 块内 `+0x08 sw vtable,0(this)` / `+0x0C lw m_str,4(this)` |
| `0x102764` | `mmalloc_free` | +0x34 | `0x4 [load]` | 分配器拿到 NULL 块头 |
| `0x102A30` | `small_free` | +0x0 | `0x4 [load]` | 同上 |
| `0x102AA4` | `small_free` | +0x74 | `0x4 [store]` | 同上（写回被污染的链表） |

⇒ **整条链是「共享字符串对象（引用计数）→ 分配器」**，一个字节都没落在字库/图集/渲染器上。

### 3.5 固定缓冲 / 固定容量候选（第 2、3 项交付）

| # | 位置 | 证据（原盘反汇编） | 固定容量候选 | 本轮是否触发 |
|---|---|---|---|---|
| **1** | `RSUIString::Substring` `0x540FD4` | `sh v0,0(s0)` 把 `(end−start+2)` 存 **u16**，而拷贝循环上界是未截断的 `end−start` | **长度域 65,535 B**（回卷后实际缓冲更小） | 否（最长串 768/1,580 B） |
| **2** | `RSString` 对象布局 `{u16 len@+0, u8 refcount@+2, char* data@+4}` | `~RSString`/`~RSUIString`/`operator=` 全部用 `lbu`/`sb` 操作 `+2` | **引用计数 = 1 字节（255 封顶）** ⇒ 回卷即**提前释放 ⇒ 悬垂/双 free ⇒ 分配器链表走 NULL** | **形态高度吻合，静态不可判**（需实机） |
| **3** | `RSFontMgr::DrawString` `0x219A70`，帧 `addiu sp,sp,-224` | 解码格是 **`sp+223` = 帧的最后一个字节**；`jal wctomb`(`0x40BFC8`) 只写 **1 字节**；`lb 223(sp)` 读回 1 字节 | **1 字节**。汉化正是因为这里放不下 2 字节，才把它改成 `sp+222` + `lhu`（`docs\REPORT_NULLDEREF_ZH113b.md` §3.5 run#5） | 否（原盘只写 1 B） |
| 4 | `DoWordWrap__15RSTextComponent` `0x21CC10` | 帧 **288 B**；5 个 `RSUIString` 临时（8 B）在 `sp+0xF8/0x100/0x108/0x110/0x118`，`RSString` 在 `sp+0xD0`；折行结果存在 **`RSArray<int>`**（`IncreaseToSize_Array<i>` `0x21D2A0`）⇒ **动态数组，不是固定缓冲** | 无可写死的容量；行数组会 `realloc` | — |
| 5 | `GetUISoldierAbbreviateName__Fii` `0x2ECDA0` | 帧 **160 B**；`RSUIString` 临时在 `sp+0x70/0x78/0x80/0x88/0x90`；调 `FindChar(start=0, c=' ', &idx)`(`a2=0x20` 是**空格字符**，不是容量) → `Length()` → `Right(L−idx−1)` | **`FindChar` 的 `a2` 是字符不是长度**（我的首轮误判，已纠正） | — |
| 6 | `GetActorNameAbbreviated__9ActorFileCFv` `0x307090` | 帧 **80 B**；`RSString` 临时 `sp+0x30/0x38/0x40`，`FindChar` 出参 `sp+0x4C`；同 5 的调用形状 | 同上 | — |
| 7 | `RSStrMgr::ReadResourceFile` `0x54B680` | `sp += −0x81F0` ⇒ **33,264 B 栈帧**（全 ELF 最大级） | 大固定帧（未发现向其中拷文本的路径） | — |
| 8 | `RSFont::CharWidth` `0x21AD10` / `ComputeCharTextureCoords` `0x21ADE0` | `idx = (c − face->firstchar) & 0xFF`；`if (idx < 0) idx = 0`；`if (idx >= nrec) idx = 0` | **★ 原盘是"钳位到 0"**，不是越界读 | — |
| **9** | **`AddOneWord__9RSFontMgr…` `0x219F50`** | `+0x70`：`v1 = lw 68(s0)`；`+0x7C`：**`slti v1, v1, 1280`**（`0x28630500`）；未满即 `ret`，满则 flush（`SetAlpha`/`SetLinearSampling`/`AddModel`）并把 `+0x44` 清零。`+0x17C`：第二包走 `+0x4C`，判据 **`slti v1, v1, 2`** | **主顶点包 = 1280 字（word）；副包 = 2 字**。`fontmgr+0x6C`（= `DrawString` 的闸门比较对象）由 `RSFontMgr::Initialize(int)`(`0x21A454` `sw $2,108($4)`) / `ReallocateSize(int)`(`0x21A3BC` `sw $5,108($4)`) 设定 ⇒ 闸门容量 = `+0x6C` | 静态确证（常量就在指令里） |
| **10** | **`DrawLetters__12IkeFontTableFv` `0x2164C0`** | 帧 **144 B**；`s0 = lw 56(this)` 起步长 **+20 B**（`0x2165A8 addiu s0,s0,20`），循环上界 **`slti v0,s2,104`**（`0x2165A0`），每 **12** 个换行（`0x216500 div s2,12`）；字符写进 **`sp+0x8C` 的 2 字节栈缓冲**（`sb char`@`0x8C` + `sb zero`@`0x8D`，`0x216544`/`0x2164F4`） | **表记录 20 B × 104 条 = 2,080 B；12 列；字符串格 = 2 字节**（帧内只剩 4 B 余量）。这就是汉化改的 `DrawLetters+0xB8`（`addiu a3,s1,3` → `5`）所在处 | 静态确证 |

**★ 第 8 条是一条重要的反向结论**：`docs\REPORT_MEMDRIFT_ZH113b.md` §5.1 描述的
「`huge` 面 `nrec 224→96` ⇒ `idx ≥ 96` ⇒ 负 UV / 采样到图集外」，
**在 `CVAR_04`（原盘 ELF）上不存在** —— 原盘的 `CharWidth`/`ComputeCharTextureCoords`
在 `idx` 越界时**钳位到记录 0**（`0x21AD80..0x21AD98` / `0x21ADE0..0x21AE18`）。
那条机理需要**汉化自己的 cave**（`0x416F40` / `0x417050`）才成立。
⇒ 「CVAR_04 崩溃」与「ZH113b 崩溃」虽然同族（都死在 dlmalloc），**但上游触发路径不同**，
不能把 MEMDRIFT §5.1 的结论直接套到 CVAR_04 上。

**全量固定长度内存调用清单**：`audit/B_fixedmem.txt`（932 个内存调用点中 231 个带常量长度参数，
逐站点列出 `site / function / callee / a0..a3 常量 / 栈目标`）。
其中与**文字/名字/UI** 相关、且目标是栈缓冲的站点（节选）：

```
0x00302960 Delete__10SPBriefingFv        strcpy  a1=32  dst=sp+32     ← SPBriefing（简报界面）
0x0030408C SetVisible__10SPBriefingFb    strcpy  a1=32  dst=sp+96
0x0030F688 ReplaceKilledSoldiers__15SPPlatoonScreenFP15Campaign  memset dst=sp+312
0x0032A0C4.. ProcessMessage__13PS2NewProfileFP13RSGameMessage sprintf a2=32/48/95/46/33/35/64/...
0x0033DF18 UpdateDialog__11AfterActionFP19MemCardOperationVarUi  sprintf dst=sp+184/200
0x00346764 Finish__23SpecialFeaturesMain_PS2Fv  sprintf a2=64 dst=sp+80
0x0054071C FloatToString__10RSUIStringFfii      （字符串化，栈缓冲）
0x00540878 IntToString__10RSUIStringFi          （字符串化，栈缓冲）
0x005378CC CreateSysIcon__10MemCardMgrFi   memcpy a2=64/48 dst=sp+1120/1184/1232/1280
```
**登记为候选清单，本轮未判定哪一条真被撞**（见 §7 未达成项）。
`audit/B_stackbuf.txt` 另列 801 个 ≥256 B 栈帧函数。

### 3.6 ★★ 候选 R（本轮**新发现**，最贴合"内容驱动、与长度弱相关"的形状）：0xB1 / 0xB5 图标哨兵

**原盘 `DrawString` 对 `0xB1` / `0xB5` 有硬编码特判**（`0x219C08..0x219C40`、`0x219CA0..0x219D3C`）：

```
219C08  v1 = 0xFFB5 ; 219C0C  beq c, 0xFFB5 → 0x219C44   ; c == 0xB5
219C14  v1 = 0xFFB1 ; 219C18  beq c, 0xFFB1 → 0x219C40   ; c == 0xB1
        （命中则**跳过** ComputeCharTextureCoords，改用硬编码图标 UV
          0x41C8/0x4346/0x41A8/0x435A 与 0x4234 等）
219D24  v0 = 0xFFB5 ; 219D2C  beq a0,0xFFB5 → 0x219D64
219D38  v0 = 0xFFB1 ; 219D3C  beq a0,0xFFB1 → 0x219D68
219D64/219D68: … ; 219D78  t0 = 1
        ⇒ 图标字走 AddOneWord(…, flag = 1) ⇒ **副包 `fontmgr+0x4C`（容量 2）**
```

**汉化文本里这两个字节的形态统计**（`tools\txt_capacity.py`，对 3 张盘的 3 个容器逐条扫）：

| 盘 / 容器 | payload | `0xB1` 出现 | `0xB5` 出现 | 含其中之一的条目 | 当 **trail**（2 字节汉字的第二字节） | 裸单字节（真图标） |
|---|---|---|---|---|---|---|
| **EN_TRUE** `RES@MENU`/`RES@GR` | 114,617 / 114,740 | 7 | 21 | 21 | 0 | **28** ✓（原盘本来的图标占位） |
| **ZH113b / CVAR04** `RES@MENU` | 55,751 | 144 | 170 | **221** | **286** | **28** ✓ |
| **ZH113b / CVAR04** `RES@GR` | 55,751 | 144 | 170 | **221** | **286** | **28** ✓ |
| **ZH113b / CVAR04** `SFXML` | 47,857 | 62 | 96 | 34 | **158** | 0 |

```
★ 汉化的对偶码是把 trail 放在 [0xA1,0xFE] 里 —— 于是 **286 个汉字的第二字节
  恰好等于 0xB1 / 0xB5**，在**原盘引擎**上会命中"图标特判"分支：
  一个 2 字节汉字被拆成「1 个字形 + 1 个图标」，并且这个图标字走的是
  **容量只有 2 的副包（fontmgr+0x4C）** ⇒ 每次画到它们就多一次 flush
  （SetAlpha / SetLinearSampling / AddModel(fontmgr+0x4C) 三个调用 + 计数清零）。
★ 这正好解释：① 为什么"内容"驱动而不是"长度"驱动（286 处与串长无关，只与
  用到了哪些汉字有关）；② 为什么英文字典里没有这个形态（EN 的 28 个 0xB1/0xB5
  全是**故意的图标占位**，不是字符的一部分 ⇒ 原盘从不把"字符"送进这条路径）；
  ③ 为什么 ZH113b 要专门做 DBCS cave 把 `0xB1/0xB5` 的特判拿掉
  （`migrate_legacy.py` 的 `ICON_CHARS`；`LEAD_CAPACITY_2400.md` §9/§10.2）。
   而 **CVAR_04 用的是原盘 ELF ⇒ 没有这个 cave ⇒ 这 286 处全部走图标路径**。
★ 本轮**没有**把这 286 处做成对照盘（**3 张额度已用满**，且任务书第 3 张盘的名额
  我改用于"长度拉平"的对偶实验）。**这是我认为下一步最该出的盘**：
  把 trail 全部换成非哨兵值（需要几何路给出另一个合法 trail 或改写编码），
  或者反过来在 CVAR_04 基础上**只**把这 286 处改成非 `0xB1/0xB5`。
```

**对已产出三张盘的锋利预测（可用来判别候选 R）**：
`TXT_01` 只截短 45 条、`TXT_03` 只补/截空格 —— **两者都原样保留了那 286 个哨兵 trail 字节**。
⇒ **若两张盘仍然崩、且崩在同一段 PC（`0x541038` / `0x541eb0` / `0x541ca0`）**，
则候选 R 的权重大幅上升（长度这条线被排除、内容形态这条线仍在）。


### 3.7 顺带取证的两条（会改变后续判断）

1. **`0x40BFC8` = `wctomb`**（`cave_syms.py`），而它的实现是个**桩**：
   ```
   40BFC8  bne a0,zero → 40BFD8
   40BFCC  sb a1, 0(a0)          ; *s = (char)wc    ← 只写 1 字节
   40BFD0  jr ra ; 40BFD4  v0 = 0
   40BFD8  jr ra ; 40BFDC  v0 = 1
   ```
   即"宽字符→本地字符"在 PS2 版被实现成 **低字节直捅 1 字节**。
   这正是 `DrawString` 里 `sp+223` 那 1 字节格的来源，也解释了汉化为什么必须改 `sp+222`。
2. **容器文法核对（`txt_grammar.py`）**：`RSStringTable::ReadResource`(`0x53EC50`)
   + `Read(istream&,RSUIString&)`(`0x53FE40`) 读的是
   `{u32 ngroups}` + 每组 `{u32 len}{name}{u16}{u32 n}` + `{u32 n_strings}` + `{u32 len}{data}×`，
   **与 `EN_STRINGS.RES` 的实际字节不符**（实测：把 EN blob 按该文法走，
   第 2 组就把 `0x6F726F46` 当长度、在 `0x21A1` 处失步）。
   **⇒ 项目自有的 `tcslib.parse_lang` 口径是正确的**（`{u32 ngroups}` +
   每组 `[u32 sep] {u32 count}` + `count×{u32 len}{data}{u16 attr}`），
   §2 的全部数字建立在这个已知正确的口径上；`attr` 在这些条目上恒为 `0x0000`。
   （`RSStringTable` 那份是**另一个资源族**的加载器，不要拿来改文本盘。）

---

## 4. C. 三张决定性验证盘（`work\builds\GR_TXT\`）

### 4.1 基底选择与理由

| 盘 | 基底 | 为什么 |
|---|---|---|
| `TXT_01_short` | **`CVAR_04_text.iso`** | 它是**已实证会崩**的最小复现盘（原盘 ELF + 原盘图集/记录表 + 3 份中文文本），且用户在**进入关卡→队伍选择界面**实测崩过。**只改文本一个变量** ⇒ 行为差异可直接解释。若换 `GR_ZH113b` 当基底，基底自身还带 26,502 B 的 ELF/图集/结构改动，**不是单变量**。 |
| `TXT_03_len_eq_en` | **`CVAR_04_text.iso`** | 同上。TXT_01 把长度**封顶**（≤ 英文），本盘把长度**拉到等长**（== 英文），两张盘从两侧夹住"长度"这一个变量。 |
| `TXT_02_orig_text` | **`GR_ZH113b.iso`** | 按任务书：做成"其余全汉化、3 份文本是英文"，与既有 `CVAR_05_elf_atlas.iso`（ELF+图集、无文本）互为镜像。 |

> 任务书的 `TXT_03_sel_screen.iso`（只改队伍选择界面用到的串）**没有做** ——
> 我**不知道**该界面读了哪些 key（§2.2 已证明增长条目全在联机/控制台/选项/地名族，
> 人名根本不走 `EN_STRINGS.RES`）。按任务书规定「不知道就跳过并写明」，
> 我把第 3 张盘的名额改用于**信息量更高的对偶实验** `TXT_03_len_eq_en`。
> **这是对本任务书的一处有意偏离，如实登记。**

### 4.2 每张盘改了什么 / sha256 / 自检

| 盘 | 相对基底改了什么 | 改了槽 | 手数 | 差异 | sha256 | 尺寸 |
|---|---|---|---|---|---|---|
| `TXT_01_short.iso` | 两个 LANG 容器里**所有 `zh_len > en_len` 的条目**（各 45 条，共 90 条）截短到 **≤ en_len**；**XML 槽逐字节不动** | 2/3 | 90 条 | 759 run / 64,273 B | `59bb55ee5921c0b5f3fbfcf1b01fe691423dedd652cece21b9ac9d04f503bc2f` | 1,648,164,864 |
| `TXT_03_len_eq_en.iso` | 两个 LANG 容器**全部 2,232 条**载荷用空格(0x20)补齐/截短到**恰好 == en_len**（补 1,639 + 截 45 + 不变 548，每容器）；**XML 槽逐字节不动** | 2/3 | 1,684 条/容器 | 897 run / 78,889 B | `9eab6be660f6838cc1a909d526379dd3c47f48f3792d09252cdce674eb50228d` | 1,648,164,864 |
| `TXT_02_orig_text.iso` | 3 个容器的槽内容**整体换成英文原盘同名槽（逐字节）** | 3/3 | 3 槽 | 1,304 run / 143,389 B | `6cfa5a2fb7dfc286b29e949535f7f8852fc39898dabc151c8198ac5db83c3fc4` | 1,648,164,864 |

**每张盘的硬自检（`*.meta.json` 的 `selfcheck`，全部通过）**：
1. `slot_only = true` —— **槽外差异 run = 0**（1 MB → 4 KB → 字节 三段式精确 diff）。
2. `size_eq_base = true` —— 与基底同尺寸，LBA / ISO9660 / 目录记录未动。
3. IMG 条目表的 `stored` / `real` / `off` / `name` **回读断言不变**。
4. 产物盘**回读**：解码出的 blob 与目标 blob 逐字节相同；`keep` 模式的槽逐字节未变。
5. **解压总长不变**（`repack` 断言），每个重压子流都做了 `lzo1x_decompress` **回环自检**。
6. 帧长 ≤ 槽长 `stored`；槽内帧后余量按既有约定补 0（与 `GR_ZH113b` 实测一致：尾部非零字节 = 0）。
7. `TXT_01` 额外断言：改后 **2,232/2,232 条** `len ≤ en_len`（`n_gt_en = 0`）。
8. `TXT_03` 额外断言：改后 **2,232/2,232 条** `len == en_len`（`n_len_mismatch = 0`），
   且 `used_end` 变成 **128,537 / 128,660** —— **与英文原盘完全相同的有效长度**。
9. `rebuild_lang` 断言"尾部全零"才允许按零重建（原 blob 尾部确实全零），**不会吃掉非零尾料**。

**构建命令**：
```powershell
python work\builds\GR_TXT\tools\txt_build.py                 # 三张全建
python work\builds\GR_TXT\tools\txt_build.py TXT_01_short    # 单张重建
$env:TXT_DRY='1'; python work\builds\GR_TXT\tools\txt_build.py   # 只算不写

# ★ 独立终检（从盘上重新读，不依赖构建时的内存状态）
python work\builds\GR_TXT\tools\txt_verify.py    # → audit/C_verify.txt
```

**独立终检（`tools\txt_verify.py` → `audit/C_verify.txt`）**：对每张盘重算 sha256、
重读 3 个容器的条目字段、重算**两份 IMG 全表**（686 + 4070 条 × 48 B）的 sha256 并与**基底**比对、
再独立复核该盘的设计命题（`≤ en_len` / `== en_len` / `== 英文原盘 blob`）。**结果见 §4.4。**

### 4.3 每张盘的**预期现象**（哪些"看着坏了"是设计内）

* 三张盘都会**显示错乱**，且**这不是 bug**：
  `TXT_01`/`TXT_03` 的 ELF/图集/FONT.RES 仍是原盘的 ⇒ 中文本来就查不到字形（CVAR_04 也是乱码）；
  `TXT_01` 的截断可能把某个 2 字节对偶码切成半截；`TXT_03` 会在行尾多出空格。
* **判据只有一条：硬卡死 + 画面静止 + emulog 出现同时间戳无限重复的 TLB Miss 段。**
  缺字/乱码/英文界面一律先按"预期"处理。

### 4.4 独立终检结果（`tools\txt_verify.py` → `audit/C_verify.txt`）

```
TXT_01_short        ✅
     sha256 59bb55ee5921c0b5 (OK)
     IMG表@776286 未变        IMG表@19175 未变
     EN_STRINGS.RES@MENU 2232 条 全部 <= en_len (0 条不符)
     EN_STRINGS.RES@GR   2232 条 全部 <= en_len (0 条不符)
     EN_SPECIAL_FEATURE.XML 字段一致 槽未变
TXT_03_len_eq_en    ✅
     sha256 9eab6be660f6838c (OK)
     IMG表@776286 未变        IMG表@19175 未变
     EN_STRINGS.RES@MENU 2232 条 全部 == en_len (0 条不符)
     EN_STRINGS.RES@GR   2232 条 全部 == en_len (0 条不符)
     EN_SPECIAL_FEATURE.XML 字段一致 槽未变
TXT_02_orig_text    ✅
     sha256 6cfa5a2fb7dfc286 (OK)
     IMG表@776286 未变        IMG表@19175 未变
     EN_STRINGS.RES@MENU blob == 英文原盘
     EN_STRINGS.RES@GR   blob == 英文原盘
     EN_SPECIAL_FEATURE.XML 字段一致 槽已改

总判定: ✅ 三张盘全部通过
```

（`IMG表@776286` = `MENU.IMG` 686 条 × 48 B，`IMG表@19175` = `GR.IMG` 4070 条 × 48 B，
都是**整表 sha256**，与**本盘基底**比对 ⇒ 条目表一字未动。终检完全从盘上重读，
不依赖构建进程的内存状态。）

---

## 5. D. 给用户的测试判定表

> **测试顺序建议**：先 `TXT_01_short`（最省事、信息量最大），再 `TXT_02_orig_text`，最后 `TXT_03_len_eq_en`。
> 每张盘**用与 CVAR_04 相同的路径**：进入关卡 → 到**队伍选择界面**（CVAR_04 崩在这里），
> 然后再按 `docs\CVAR_TEST_GUIDE.md` §3 的正常游玩 / 火箭筒 / L1 小队地图 / 存读档各做一次。
> 每张盘之间**重启模拟器**。记录模板沿用 `CVAR_TEST_GUIDE.md` §3。

| # | 观察 | 结论 | 下一步 |
|---|---|---|---|
| 1 | **只有 `TXT_01_short` 不崩**（`TXT_03` 崩） | ★ **"中文串超过英文原长"确实是触发条件** —— 而且是 45 条 / 每条 ≤ +10 B 的极窄触发 | 把 45 条按族二分（联机标签 / 地名 / 战绩 / 选项）再出 2~3 张盘定位到具体 key；同时**必须**解释"为什么 +1..+10 字节能撞坏堆"（§3.5 候选 1/2/3 里逐项排除） |
| 2 | **只有 `TXT_03_len_eq_en` 不崩**（`TXT_01` 崩） | 触发条件不是"超过英文长度"，而是**"中文总量/长度远小于英文"**（CVAR_04 只有 48.6%）⇒ 病根是**内容/编码**（字节分布），长度方向相反 | 做"中文总量 = 英文总量、但内容仍是中文"的对照组（`TXT_03` 已被空格补齐，与 CVAR_04 的差别只有空格）⇒ 若 `TXT_03` 也不崩，则**总量**可疑；若两者都崩，转 #4 |
| 3 | **两张都不崩** | ★ **长度完全与本题无关**（无论封顶还是拉平都修好了 ⇒ 说明真正起作用的是"载荷被重写过"这件事本身，而不是长度） | 病根在**内容层**：把 `TXT_01` 的改动缩小到**单条**（45 条逐条出盘/或按族出 4 张），找出唯一一条；同时查 §3.5 候选 2（引用计数回卷）——它天然解释"内容驱动、与长度无关" |
| 4 | **两张都仍崩** | ★ **长度不是原因**（封顶和拉平都救不了）⇒ §2 的"字形数只有 0.49×"与这条一致 | 转 **`TXT_02_orig_text`**：若它**也不崩** ⇒ 病根确定在"这 3 份容器的**中文内容**"（含编码/字节分布），下一步做"半中文"盘（只换 `EN_STRINGS.RES@MENU` / 只换 `@GR` / 只换 XML）二分；若它**也崩** ⇒ 病根**不在文本层**，回到 ELF/图集/结构部件（`CVAR_01/02/03/05/06`） |
| 5 | **`TXT_02_orig_text` 崩** | ★ 与 `CVAR_05_elf_atlas`（ELF+图集、无文本）对照：若 05 不崩而 02 崩，病根在**"文本 + 全汉化"的交互**；若 05 也崩，病根在 **ELF+图集**，与文本无关 | 报回来，我按 `docs\CVAR_TEST_GUIDE.md` §5 的二级二分继续出盘 |
| 6 | **三张全不崩** | 文本层的**任何**扰动都能消除症状 ⇒ 更像**时序/堆布局敏感**（历史量级的一点点变化就改变分配顺序） | 这条结论本身价值极高：说明 CVAR_04 的崩溃是**堆布局脆弱**，而不是某条数据必然致毒。下一步应做"只改 1 条/只改 1 字节"的极限扰动盘 |
| 7 | **三张全崩** | 文本层**不是**病根（或至少不是唯一病根） | 回到 `CVAR_01_elf` / `CVAR_02_atlas` / `CVAR_03_ft` / `CVAR_06_rest` 的读数；**注意 `CVAR_04` 只改了文本却崩了 ⇒ 若三张文本盘都崩，则"文本层"这条线要往"任何改动的存在"上收** |
| 8 | **`TXT_01` 与 `TXT_03` 都仍崩，且崩在同一段 PC**（`0x541038` / `0x541eb0` / `0x541ca0`，或 `0x10xxxx` 分配器） | ★★ **候选 R（§3.6 的 0xB1/0xB5 图标哨兵）权重最高**：长度这条线被两侧夹死排除，而两张盘都**原样保留了那 286 个哨兵 trail 字节** | 出第 4 张盘：在 `CVAR_04` 基础上**只**把那 286 处 trail 换成非 `0xB1/0xB5` 的合法值（需要几何路给替代 trail，或改编码），其余一字不动。若它不崩 ⇒ **候选 R 定案** |

**判定纪律**：一次只跑一张、同一操作序列、每张至少玩 15~20 分钟（症状是"玩一段时间才出现"）。
卡死后立刻记 `emulog.txt` 尾部 60 行 + 是否出现 `pc=0x541038` / `0x541eb0` / `0x541ca0`
及其它 `0x10xxxx`（分配器）。
★ **新判据**：若日志里出现 **`pc=0x541038` / `0x541eb0` / `0x541ca0`** 三者之一，
说明**同一条链**（RSUIString 字符串对象 → 分配器）复现了 —— 这比只看"TLB 打满 50"更精确。

---

## 6. 混淆因素（必须一起读）

| # | 因素 | 说明 |
|---|---|---|
| C1 | **三张盘之间没有英文对照臂** | `TXT_02` 是"汉化盘 + 英文文本"，不是英文原盘。阴性对照仍是 `CVAR_00_orig` / 英文原盘 |
| C2 | `TXT_01` 的截断可能切开 2 字节对偶码 | 会把某个字符变成半截 lead 字节 ⇒ 乱码更严重（预期内），但也可能让引擎走**回退分支** |
| C3 | `TXT_03` 的补齐会改变**渲染宽度/折行** | 每行尾部多出空格 ⇒ 折行点、每屏行数都会变。这是"长度"实验不可避免的副作用，但它**同时**改了"可见文本量" |
| C4 | **本机复现能力有限** | `docs\REPORT_MEMDRIFT_ZH113b.md` §2 已定案：gsrunner 在 BIOS/记忆卡/ISO/版本全对齐后**复现不出缺页**（80,000 帧 TLB 0）⇒ 验收**只能靠用户实机** |
| C5 | `TXT_02` 顺带**修好了 XML 的 56 B 不一致** | 汉化盘 XML blob 116,486 vs `real` 116,430；换成英文槽后两者一致（116,430）⇒ `TXT_02` 变量不止一个（但那是"恢复原状"方向） |
| C6 | §3.5 候选 2（**u8 引用计数**）无法静态判定 | 它需要一个**运行期**的引用计数达到 255。要证实/证伪必须实机（见 §7） |
| C7 | 模拟器是**独占资源** | 本任务**未跑模拟器**；用户测试时请确认零 `pcsx2` 进程再跑，勿并发（`LEAD_CAPACITY_2400.md` §18.1） |
| C8 | `pc=` 是**块入口**不是出错指令 | 用它判"同一条链"可以，用它判"哪条指令"不行（§3.4） |

---

## 7. 未达成项（如实列出）

1. **没有实机数据**：三张盘**没有跑过**（任务书明示本任务不需要模拟器）。
   所有"预期现象"都只是预期；"能不能进主菜单"请用户第一次测的时候顺带记一笔。
2. **`pc=0x541038` 的 `[store]` 到底落在哪一次迭代没定案**：
   已确定块入口与块内唯一的 store（`sb zero,0(dst+i)`），但**`dst` 是 NULL 还是 `i` 把指针回卷到 0**
   两种解释都能产生 `addr=0x0`，静态分不开。
3. **`0x5A72D8` 步进的驱动者未定案**：知道了"公差 = vtable 常量"，
   但**没有找到那个以它为步长的循环**（需要实机在 `~RSUIString` 上下写断点/回溯 `$ra`）。
4. **§3.5 候选 2（u8 引用计数 255 回卷）未证实**：需要实机在
   `RSString+2`（引用计数）上设**写监视**，看有没有对象被打满 255 后回绕。
   这是本轮**最有希望解释"内容驱动、与长度弱相关"**的一条，但纯静态做不到。
5. **`audit/B_fixedmem.txt` 的 231 个常量长度调用点没有逐个判定"哪一条被撞"**：
   只给出了清单（含 `SPBriefing` / `SPPlatoonScreen` / `PS2NewProfile` 等 UI 候选）。
   判定需要一个真实的越界写现场（实机）。
6. **XML 的逐条长度只覆盖 `<text>`（69 条）与 `name=`（145 条）**：
   另有 `<picname>`(240) / `<moviename>`/`<soundname>`/`<3dname>`(各 94) 等节点**未逐条比对**
   （它们多是资源文件名，倾向不译；**未核实**）。
7. **`EN_STRINGS.TXT`(#30) 与 `NTSC_IKE.RES`(#282) 两个非文本容器改动未纳入本轮**（任务书只点名 3 个容器）。
8. ~~没有穷举"CVAR_04 上哪些字节序列会让原盘引擎走非常规路径"~~ → **本轮已做**（§3.6 候选 R：
   3 张盘 × 3 容器的 `0xB1/0xB5` 形态普查）。**仍未做的是"其余特判字节"**：
   原盘 `DrawString` 只对 `0xB1/0xB5` 与空格（`0x20`，`0x219BE8`）有特判；
   `RSFont` 的其它阈值为空 —— 未再穷举。
9. **候选 R 没有做成对照盘**：3 张额度已用满（任务书上限），而任务书点名的第 3 张盘是
   `TXT_03_sel_screen`（我因不知道 key 而改用长度对偶实验，见 §4.1）⇒
   **"清掉 286 个哨兵 trail"这张盘没有出**。这是本轮**最该补的一张盘**（§5 判定表第 8 行）。
10. **`Disable icon special-case` 是否就是 CVAR_04 崩因，静态无法判定**：
   它需要实机 GS 抓帧（看某汉字的第二字节是否被画成 △ / ✕ 图标）或对
   `AddOneWord` 的 `flag` 参数下断点。**静态只能给出"286 处会命中"这个量**。

---

## 8. 纪律与偏差登记

| 项 | 状态 |
|---|---|
| 既有 ISO / PCSX2 配置 | **全程只读**（`mmap(ACCESS_READ)`；无任何 `open(...,'wb')` 指向既有 ISO） |
| 写入范围 | 仅 `work\builds\GR_TXT\**` 与本文件 ✅ |
| commit / 分支 / merge | **未做** ✅ |
| 模拟器 | **未跑**（无并发污染；未发现也无需轮询 pcsx2 进程） |
| 磁盘 | 单盘 1,648,164,864 B × 3 = 4.94 GB（构建后 C: 剩余 ~20.9 GB） |
| **纪律偏差** | ① 任务书的第 3 张盘 `TXT_03_sel_screen.iso` 改为 `TXT_03_len_eq_en.iso`（理由见 §4.1）；② 过程中**误用过一次 `Select-Object -First 62`** 做输出截断（用户明令禁止）—— 未影响任何产物或读数，之后全部改为重定向到文件 + `Get-Content`/`read`。为此**如实登记**。 |

---

## 9. 产物索引

| 路径 | 内容 |
|---|---|
| `work\builds\GR_TXT\TXT_01_short.iso` / `.meta.json` | 中文全部 ≤ 英文长度（基底 CVAR_04） |
| `work\builds\GR_TXT\TXT_03_len_eq_en.iso` / `.meta.json` | 中文全部 == 英文长度（基底 CVAR_04） |
| `work\builds\GR_TXT\TXT_02_orig_text.iso` / `.meta.json` | 汉化盘 + 英文文本（基底 GR_ZH113b） |
| `work\builds\GR_TXT\summary.json` | 三张盘 sha256 / 尺寸 / 差异 run 一览 |
| `work\builds\GR_TXT\audit\A_len_audit.json` | A 的**全部**原始读数（4 盘 × 3 容器 × 逐条目） |
| `work\builds\GR_TXT\audit\A_detail.txt` / `A_detail_rows.json` | A 的逐条明细（含按游戏 charset 解码的中文） |
| `work\builds\GR_TXT\audit\A_top_growth_*.csv` | 每个容器增长最大的 30 条 |
| `work\builds\GR_TXT\audit\A_xml_audit.json` / `A_xml_top_growth_*.csv` | XML 的 `<text>` / `name=` 逐条读数 |
| `work\builds\GR_TXT\audit\B_funcfixed.txt` | 10 个函数（含 Substring / ~RSUIString / DoWordWrap / AddOneWord / DrawLetters / 两个名字函数）全文反汇编 |
| `work\builds\GR_TXT\audit\B_fixedmem.txt` | 231 个"常量长度内存调用"站点清单 |
| `work\builds\GR_TXT\audit\B_stackbuf.txt` | 801 个 ≥256 B 栈帧函数 |
| `work\builds\GR_TXT\audit\B_verify.txt` | 三盘逐字节同一性 + 崩溃点指令回读 |
| `work\builds\GR_TXT\audit\_drawletters.txt` / `_addoneword.txt` | `DrawLetters` / `AddOneWord` 段反汇编（`show_block.py` 切出） |
| `work\builds\GR_TXT\tools\*.py` | 本轮全部脚本（全部只读既有 ISO） |

---

## 10. 与既有结论的关系（哪些沿用、哪些修正）

| 既有结论 | 本轮处置 |
|---|---|
| 停顿 PC 在 EE 侧游戏自带 dlmalloc ⇒ **受害者现场**（`REPORT_NULLDEREF_ZH113b.md` §1.1、`LEAD_CAPACITY_2400.md` §19.2） | **沿用**，并把现场扩到整个 `RSUIString` 字符串类（§3.2/§3.3） |
| 18 个停顿 PC 在 EN/ZH 上逐字节相同（`REPORT_NULLDEREF_ZH113b.md` §1.1） | **沿用并扩大**：`0x540F00..0x541F50` + `0x101C00..0x102B00` 三盘（含 CVAR_04）**0 B 异**（§3.1） |
| 「中文字形数可达英文 2 倍」（任务书前提） | **★ 推翻**：实测 **0.486 倍**（§2.3） |
| `huge` 面 `nrec 224→96` ⇒ `idx ≥ 96` ⇒ 负 UV（`REPORT_MEMDRIFT_ZH113b.md` §5.1） | **★ 限定适用范围**：原盘 `CharWidth`/`ComputeCharTextureCoords` **钳位到 0**（§3.5 候选 8）⇒ 该机理**只对汉化 cave 成立，对 CVAR_04 不成立** |
| `REPORT_MEMDRIFT_ZH113b.md` §5.3「`0xB1..0xB9` 是潜在编码器/解码器失配」 | **★ 具体化为候选 R**（§3.6）：不是"潜在"，而是**已经在盘上 286 处**，且原盘有硬编码特判 |
| cave 覆盖 SDK 函数已排除（`LEAD_CAPACITY_2400.md` §19.3 ⛔） | **沿用，未重查** |
| `stored != real` / ISO9660 / 条目越界等旧断言已推翻 | **沿用，未重查** |
