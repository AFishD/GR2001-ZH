# REPORT_pc_structure.md — PC《幽灵行动》(官方简中 v1.4.0.0) 字体/文本组织剖析

> **round77 / 分支 `round73/font-decompile`**。只读素材：`third_party/orig/ghost_recon_pc`（完整安装，1.98 GB / 10,401 文件）。
> PC 侧另用：PS2 原始盘 `third_party/orig/ps2/Tom Clancy's Ghost Recon (USA).iso`（只读）。
> 脚本：`work/tools/pc_*.py`（全部新建，未改任何既有工具）。中间产物：`work/builds/GR_ZH98/temp/r77/`。
> 本文所有偏移均为**文件内字节偏移**；EXE 的 VA 为 ImageBase `0x400000` 下的虚拟地址（`.rdata`/`.data` 的 VA = 文件偏移 + 0x400000）。

---

## 〇、结论先行（给 Lead 的 5 句话）

1. **PC 装的是官方简体中文版**（`Ike.log`：`Ghost Recon (RELEASE) version = 1.4.0.0`，安装路径 `C:\Program Files (x86)\Red Storm Entertainment\Ghost Recon\`；`Ike.log` 里出现 `FindFile could not find file 主菜单.map`）。⇒ 它带**一整套官方中文本地化机制**，不是英文版。
2. **PC 有两套并列的字库系统**：
   * **(甲) ike 引擎原生的 `RSFontMgr`**（与 PS2 **同源同构**）：`Data/Shell/font.res` + `Data/Shell/Art/new_font_revised.rsb`（拉丁字形图集）。这就是 PS2 那套"wire rsb + FONT.RES 记录表"的 PC 版。
   * **(乙) 中文 DBCS 本地化字库（PC 独有）**：`Data/Shell/Art/gbtext.def`（**码→槽位表**，1288 条）+ `Data/Shell/Art/GB{12,16,24}{00..04}.TGA`（**外部页纹理**）。**槽位→页/行/列→UV 全部由代码现算，字库里一张度量表都没有。**
3. **PC 的中文字形容量不靠"容器余量"，靠"页文件 + 现算地址"**：`perRow = 512/S`、`perPage = perRow²`、`page = slot/perPage`；页数上限**硬编码为每字号 5 页**（`0x6584C3 cmp ebp,5`），字号扫描 1..39（`0x6584D1 cmp edi,0x28`），槽位是 **u16**（`0x6582DD mov word [edx+0xE], si`）。⇒ 12px 档理论容量 **5×1764 = 8820 槽 ≥ GB2312 全体 7445**。
4. **格式同源性：PC 版就是 PS2 版的"格式教科书"**——`.qob`/`.pob` 有**逐字节完全相同**的同名文件（`grass_1.qob`/`grass_2.qob`/`dust.pob`），`.rsb` 容器模型在 PS2 的 638 个 `.RSB` 条目上**同样精确成立**，`.mis`/`.atr`/`.kit`/`.gun`/`.gtf` 是**同一份 XML 文本被 LZ 压过**（PC = 明文）。
5. **⇒ "内容/逻辑分离"可以照做，但 PS2 的等价物不是"多页"，而是"把网格常量与图集尺寸变成数据"**：PS2 侧 `new_font_revised` 那张 COMMON.PAK 记录里的 `w`/`h` **本来就是 u32 数据**（`1024`/`512`），而 ELF cave 里的 `NCOL=62 / CW=CH=16 / Y0=2 / SKIP` 是**立即数**。**把立即数改成数据表 + 把纹理 w/h 当数据用（加宽图集 = PC 的"分页"）** 就是最小改动，且 512×512→1024×1024 一次翻倍（4bpp 下 1024 格 → 2048 格）。

---

## 一、侦察口径

| 素材 | 路径 | 说明 |
|---|---|---|
| PC 安装 | `third_party/orig/ghost_recon_pc/` | 顶层 `Data/ Mods/ ubicom/ GhostRecon.exe igor.exe ScriptEd.dll Chinese.dat options.xml Ike.log …` |
| PC 字体目录 | `Data/Shell/` | `font.res` 4796 B、`IKE.RES` 280118 B、`STRINGS.RES` 91775 B、`strings.txt` 6790 B、`Art/` |
| PC 字体图 | `Data/Shell/Art/*.rsb`、`*.tga`、`gbtext.def` | 42 个 `.rsb` + 6 个 `GB*.tga` + 1 个 `gbtext.def` |
| PC 文本 | `Data/Shell/strings.txt`、`Data/Shell/STRINGS.RES`、`Chinese.dat` | 目录根 `Chinese.dat` 2202 B |
| PC 工具 | `igor.exe`（RSE 官方编辑器，认 `Red Storm Bitmap Files (*.rsb)`）、`ScriptEd.dll` | 见 §D.3 |
| PS2 原始盘 | `third_party/orig/ps2/Tom Clancy's Ghost Recon (USA).iso` | ISO9660：`GR.IMG;1`@LBA 19175 (1,550,563,328 B)、`MENU.IMG;1`@LBA 776286、`SLUS_206.13;1`@LBA 295 |
| 既有成果（**必须先读，本文在其上推进**） | `docs/han_v2/PC_FONT_MECHANISM.md`（指令级还原 PC 中文 DBCS 字库）、`docs/han_v2/artifacts/{Chinese0.rsb, gbtext.def}` | 本轮的 `Chinese0.rsb` 与 `docs/han_v2/artifacts/Chinese0.rsb` **sha256 完全相同**（`290cb0953b866ef31e2f17b5371467d0b112addeb8e667d2a29806af7d77ffb5`） |

---

## A. PC 的字体是怎么组织的

### A.1 字体数据在哪里、什么格式

**(甲) ike 引擎原生 `RSFontMgr` 字库（与 PS2 同构）**

| 文件 | 大小 | 角色 |
|---|---|---|
| `Data/Shell/font.res` | 4,796 B | 字体描述资源（= PS2 的 `FONT.RES`） |
| `Data/Shell/Art/new_font_revised.rsb` | 262,253 B | **拉丁字形图集**（= PS2 的 `new_font_revised.rsb`） |
| EXE 内 `RT_RCDATA` `IDR_SXM12/16/24`(+`B` 繁体组) | 212,064 / 282,752 / 62,312 B | 拉丁字形位图池 |
| EXE 内 `RT_RCDATA` `IDR_SXME12/16/24` | 2,688 / 6,688 / 16,704 B | 伴随资源 |

**`font.res` 实测字节**（`work/builds/GR_ZH98/temp/r77/pc_fontres_struct.txt`）：

```
@0x0000  04 00 00 00            u32 = 4                    资源类型
@0x0004  69 6b 65 00            "ike\0"                    RSE 资源标签
@0x0008  22 7d 31 01            u32 = 0x01317D22 = 20020514  构建日期戳(2002-05-14)
@0x000C  14 00 00 00            u32 = 20 (长度前缀)
@0x0010  "new_font_revised.rsb"                           ← 唯一的字形纹理名
@0x0024  02 00 00 00            faceCount = 2
@0x0028  07 00 00 00  "default"                           face[0]
@0x092F  "large"                                          face[1]
@0x1234  "default\0…"  (16 B, NUL 填充)                   运行期结构里的 face 名
@0x1258  "default\0…"  (16 B)
@0x127C  "large\0…"    (16 B)
@0x129E  "large\0…"    (16 B)
```

旁证（EXE 静态构造 thunk，`work/builds/GR_ZH98/temp/r77/pc_rsb_dis.txt` L637-644）：
`0x464BD0  push 0x8B690C('font.res') / mov ecx,0x8D9230 / call 0x56DED0` ——
**与 PS2 完全一样：`font.res` 是文件级静态常量，不来自任何表。**

**`new_font_revised.rsb` 逐字节结构**（`pc_rsb_headtail.txt` / `pc_rsb_final.txt`）：

```
0x00  u32 mode = 9
0x04  u32 w    = 256
0x08  u32 h    = 256
0x0C  u32 x    = 0
0x10  u32 p0..p3 = 8,8,8,8     ← 大端存储(见 §C.1)，Σp = 32 bpp
0x14..0x1F  同上
0x20  00 00 00 FF FF FF FF FF FF FF FF   (11 B，mode 9 专属附属块)
0x2B  ← 表面起点（256×256×32bpp = 262,144 B）
0x4002B 表面结束
0x4002B..0x4006C  66 B 尾部（末 4 字节恒 FF FF FF FF）
```

**渲染验证（`pc_nfr_ink.png` / `nfr_ch_B.png`）**：B 通道还原出**清晰的拉丁字形图集**——`!"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_``abcdefghijklmnopqrstuvwxyz{|}~` 以及 Latin-1 重音字（`À Á Â Ã Ä Å Æ Ç È É Ê Ë Ì Í Î Ï Ð Ñ Ò Ó Ô Õ Ö × Ø Ù Ú Û Ü Ý Þ ß à á …`）、`¼½¾ µ ¶ ± ® © ™ ▲▼◄►`。

> ⇒ **`new_font_revised.rsb` 在 PC 与 PS2 上同名、同角色（唯一字形图集）**。差别只在容器：PC 是 256×256 32bpp 的**明文单文件**；PS2 是 COMMON.PAK 里的 1024×512 4bpp 记录。

**(乙) 中文 DBCS 本地化字库（PC 独有，见 `docs/han_v2/PC_FONT_MECHANISM.md`，本轮独立复核）**

| 文件 | 大小 | 角色 |
|---|---|---|
| `Data/Shell/Art/gbtext.def` | 2,576 B | **码→槽位表**：1,288 条 × 2 B `[lead, trail]`（GBK 自然字节序），记录顺序号 = 槽位 0..1287 |
| `Data/Shell/Art/GB1200.tga` | 1,048,594 B | 12px 页 0（= 18 B TGA 头 + 512×512×4 32bpp BGRA，`imgtype=2` `desc=0x20` 顶行优先） |
| `Data/Shell/Art/GB1600.tga` / `GB1601.tga` | 各 1,048,594 B | 16px 页 0 / 页 1 |
| `Data/Shell/Art/GB2400/2401/2402.tga` | 各 1,048,594 B | 24px 页 0/1/2 |
| `Data/Shell/Art/gb{1200,1600,1601,2400,2401,2402}.rsb` | 各 524,397 B | 上述 TGA 的**引擎缓存**（16bpp R5G6B5） |
| `Data/Shell/Art/Chinese0..4.rsb` | 各 524,381 B | **另一套等价的中文页**（mode 6，512×512 16bpp），EXE 内**无引用** |

### A.2 PC 的字形容量是否受固定网格限制？

**不是"容器尺寸"限制，而是"页数 × 每页格数"限制，且两个数都写在代码里。**

EXE 关键指令（本轮 capstone 反汇编，`pc_cn_load.txt` / `pc_rsb_dis.txt`）：

| VA | 指令 | 含义 |
|---|---|---|
| `0x657E1C` | `mov dword ptr [esi], 0x200` | **页宽 512 写死进管理器**（mgr+0） |
| `0x657E6E` | `push 0x8C7E84` = `"GB"` + `0x434610`(append) | mgr+0x14 = 前缀 `"GB"` |
| `0x657E3D` | `push 0x8C7E88` = `"Data\Shell\Art\"` | mgr+4 = 目录 |
| `0x6581A0` | `fread(buf,2,1,f)` 循环 `map.insert((lead<<8)|trail, i)` | **gbtext.def 载入器**；`0x6582DD mov word [edx+0xE], si` ⇒ **槽位是 u16** |
| `0x658340` | `sprintf(buf,"%s%s%02d%02d.TGA", dir, "GB", edi, ebp)` @`0x8C7EB4` | **页文件名现算**（`%02d`=字号，`%02d`=页号） |
| `0x6583AB` | `call [0x859144]` = `GetFileAttributesA`；`0x6583B1 cmp eax,-1 / je 0x6584C2` | 页不存在 → 跳过该页继续 |
| **`0x6584C3`** | **`cmp ebp, 5` / `0x6584CA jl 0x658376`** | **每字号最多 5 页（硬编码）** |
| **`0x6584D1`** | **`cmp edi, 0x28` / `0x6584D8 jl 0x65836E`** | **字号扫描 1..39（40 上限）** |
| `0x6586E0` | `≤18→12；18<x≤24→24；x>24→16` | 字号量化三档 |
| `0x6587E5` | `idiv esi`（esi = 字号 S） | `perRow = 512 / S` → 12→42 / 16→32 / 24→21 |
| `0x6587F5` | `imul ebp, edi` | `perPage = perRow²` → 1764 / 1024 / 441 |
| `0x658852` | `idiv ebp`（perPage） | `page = slot / perPage` |
| `0x658859` | `idiv edi`（perRow） | `row = cell / perRow` |
| `0x658861/0x658874` | `imul edx,esi` / `imul eax,esi` | `X = col*S`，`Y = row*S`（像素） |
| `0x65889B..0x6588B3` | `fild/fdiv 512` | `U0=X/512, V0=Y/512, U1=(X+S)/512, V1=(Y+S)/512` |

**容量算术（与磁盘上页文件数逐一吻合）**：

| 字号 | perRow | perPage | 装 1288 字需 | 实际文件 | 5 页上限容量 |
|---|---|---|---|---|---|
| 12 | 42 | **1764** | 1 页 | `GB1200.tga` ✓ | **8820 槽** |
| 16 | 32 | **1024** | 2 页 | `GB1600/1601.tga` ✓ | 5120 槽 |
| 24 | 21 | **441** | 3 页 | `GB2400/2401/2402.tga` ✓ | 2205 槽 |

> **PC 的"绕过"方式 = 三点**：①字形数据是**独立文件**（页纹理），换页不动代码；②地址是**公式现算**（页/行/列由 slot 除出来），代码里没有"槽位表"；③每页尺寸 `w×h` 记在**文件头**（TGA/RSB 头都是 u32），尺寸是数据不是常量。
> **PC 仍然有限制**：每字号 5 页、字体尺寸只有 12/16/24 三档。但这两个限制都**远大于需要**（12px 档 8820 槽 > GB2312 全体 7445 > 本项目 1288）。

### A.3 字体度量/访问结构 vs PS2 的 `FONT.RES` 记录

| | PS2 | PC（ike `RSFontMgr`） | PC（中文 DBCS 字库） |
|---|---|---|---|
| 定位资源 | `font.res`（`RSFontMgr::ReadResourceFile("font.res")`） | `Data/Shell/font.res` 4,796 B | 无（`gbtext.def` 直接读） |
| 纹理名 | `font.res` 首字段 = `"new_font_revised.rsb"` | `font.res@0x000C` = `"new_font_revised.rsb"`（**同名字符串**） | 现算 `"%s%s%02d%02d.TGA"` |
| face 数 | 3（large/default/huge） | **2**（`default` / `large`，`font.res@0x0024` = 2） | 3 档字号（12/16/24） |
| 每字形记录 | `{u8 f0}{u8 f1=advance}{u16 u0}{u16 v0}{u16 u1}{u16 v1}` = **8 B/字**，逐字形存 UV 矩形+步进 | `font.res` 里 face 后接字段表（**与本轮解析的 PC 中文链无关**）；拉丁度量另有 SXM 路径 | **没有记录表**。advance = 整格 S；UV = `(col*S, row*S, +S, +S)`，全部现算 |
| 记录条数 | `FontDefinition+0x44` u32（224/224/96） | — | 1288（= `gbtext.def` 条数） |
| 缺字行为 | 走 cave 公式（idx ≥ mSize） | — | `slot = 0`（映射查不到时，`0x6587DC`） |

> **★ 这是最关键的对比结论**：PS2 用**"逐字形记录表"**（要存 u0/v0/u1/v1/advance）⇒ 表会撞 `FONT.RES` 展开态 7222 B 上限（见 `docs/han_v2/FONT_CAPACITY.md` §一.7）；PC 中文链用**"均匀网格 + 现算地址"**⇒ **没有任何表可撞**。两者的字形位图都躺在纹理里，差别纯粹在"**寻址是存下来的还是算出来的**"。

---

## B. PC 的文本是怎么组织的

### B.1 剧情/简报/菜单文本在哪些文件、什么格式

| 类别 | 文件 | 格式 |
|---|---|---|
| 界面串（源） | `Data/Shell/strings.txt`（6,790 B） | 文本：`<TAB>"KEY"<TAB…>"VALUE"`，GBK；225 条键值对 |
| 界面串（编译） | `Data/Shell/STRINGS.RES`（91,775 B） | **二进制串表**，结构见下 |
| 任务/简报 | `Mods/*/Mission/*.mis`（55 个） | **XML** `<MissionFile>` `VersionNumber 2.000000` |
| 演员/武器/装备/游戏类型 | `*.atr` / `*.gun` / `*.kit` / `*.gtf` | **XML**：`<ActorFile>`1.000000 / `<GunFile>`1.000000,1.500000 / `<KitFile>`1.000000 / `<GameTypeFile>`1.000000 |
| 模型/地图 | `*.qob` / `*.pob` / `*.map` | **二进制命名块**：`{u32 11}"BeginModel\0"…` / `{u32 9}"BeginPOB\0"{float 1.0}{float}…` / `{u32 13}"BeginMapv4.0\0"…` |
| 战役/解锁 | `campaign.xml` `unlocked_*.xml` `best_times.xml` | XML |
| 字表 | `Chinese.dat`、`Data/Shell/Art/gbtext.def` | 纯双字节 GBK 序列（无分隔符） |

**`STRINGS.RES` 实测格式**（`pc_strings_res_parse.txt`，从 `0x000000` 起逐字节复现）：

```
0x0000  u32 groupCount = 83
组 i:   {u32 nameLen}{name}{u8 0}{u32 itemCount}
        条目 × itemCount:  {u32 byteLen}{GBK 字节}{u16 0x0000}
        组尾:               {u32 0x00000000}
```
实例（逐字段落盘核对，`pc_verify2.txt`）：
```
@0x000004  09 00 00 00 "GameType0" 00
@0x000012  04 00 00 00                    本组 4 条
@0x000016  06 00 00 00 CA A4 C0 FB A3 A1 00 00   len=6  → “胜利！”
@0x000022  04 00 00 00 BC DF B5 D0 00 00         len=4  → “歼敌”
@0x00002C  1A 00 00 00 …(26 B)… 00 00            len=26 → “消灭所有敌人后即获得胜利。”
@0x00004C  0C 00 00 00 …(12 B)… 00 00            len=12 → “消灭所有敌人”
@0x00005E  00 00 00 00                    组尾
```
⇒ **长度前缀（u32）+ GBK + u16 终止符**，与 `strings.txt` 的键一一对应（键名 = `<Group><n>` 或动作键）。

> ⚠ **踩坑记录**：`pwsh` 控制台是 cp936，`python -c`/管道输出的 GBK 串会二次乱码。本轮首轮探测时把 `CA A4 C0 FB A3 A1` 误读成「失败！」、把 26 B 那条误读成「恢复地所有敌人后即可获得失败。」。
> **正确做法：一律落盘成 UTF-8 文件再用 read 工具读**（本文所有中文串均按此法复核，见 `pc_verify2.txt`）。

### B.2 `Chinese.dat` 完整解码

* 产物：**`work/builds/GR_ZH98/temp/r77/Chinese_dat.txt`**（一行一条，带偏移/序号/GBK 字节/字符），另出 `Chinese_dat_report.txt`、`Chinese_dat_chars.txt`。
* **结构**：2,202 B，**无任何分隔符**（`\x00`/`\r\n`/`\n` 计数全为 0），`2202 = 2 × 1101` ⇒ **1,101 个双字节 GBK 槽位**。
* **全部 GBK 解码成功（0 失败），1101 个字符 0 重复**（严格去重）。
* 分类：**CJK 统一表意 1,092 + CJK 全角标点/其它 9 + ASCII 0**。
* **开头实测（`pc_verify_head.txt` / `pc_verify2.txt`）**：
  ```
  @0x0000  CAA4 C0FB A3A1  → "胜利！"
  前 40 字：胜利！火并当场消灭所有敌人玩家即告。失败隐秘行动安全抵达撤离地点你已占领中央基去
  ```
  * ⚠ **对本任务书侦察结论的订正**：任务书写「开头即『失败！…恢复地…出错…名字…人物…』」——**不成立**。
    逐项核验：`Chinese.dat` **不含** `恢复地` / `出错` / `名字` / `人物` 这四串（`恢复` 二字根本不在表内）；
    首两字是 **`胜` `利`**（`CAA4 C0FB`）不是 `失` `败`（`CAA7 B0DC`；`失败` 出现在文件 **第 19 槽 @0x0024**）。
    该误读与 `docs/han_v2/PC_FONT_MECHANISM.md` §4 注记的「胜利！火并当场消灭所有敌人…」一致 —— **以本轮字节证据为准**。
* **类别判定：它是"字符集表 / 译文字表"（charset），不是界面串、不是提示串、也不是句表** ——
  因为它没有任何分隔符、没有重复、且**每个元素都是一个合法汉字**（1,101 个全不重复）；句子表不可能做到零重复。
  它读起来像"句子碎片"（`胜利！火并当场消灭所有敌人玩家即告。失败…`）= **按某种 UI 语料的首次出现顺序去重后的字表**。
* **与 `gbtext.def` 的关系（`pc_charset_rel.txt`）**：
  * `Chinese.dat` ⊂ `gbtext.def`（**严格子集，差 0**）
  * `gbtext.def` \ `Chinese.dat` = **187 字**（埃半豹宾补怖材惨藏策层拆厂巢乘逞齿充窗幢床胆帝陡毒夺俄恶二阀烦贩匪锋风符负概敢糕工勾狗轨害壕毫荷涸轰户滑荒恢积激缉棘脊济歼监荐见焦脚缴剿劫仅谨惊景举巨锯卷掘柯客恐览冷黎炼聊猎临邻留陆旅缕络麻卖猫冒媒美漠努怒判陪朋碰批坡迫旗敲巧峭亲倾穷泉热容散骚色善绍蛇神慎省拾识售兽书曙署属损滩填痛偷途团挖挽微危纹惜溪喜峡衔闲险箱校懈兴形序寻押严眼冶遗役勇屿狱灾糟造怎展掌植智终洲柱拽踪坐浏）
  * `strings.txt` 用字 ⊆ `gbtext.def` = **True**（差 0）；`STRINGS.RES` 用字 ⊆ `gbtext.def` = **True**（差 0）
* **EXE 内无 `"Chinese.dat"` 字符串引用**（全文搜 `Chinese` 只有 3 处，全部是 `@Chinese BIG5 Texture Loaded` / `Chinese GB2312 Texture Loaded` / `Chinese Font load succeeded!!!`）。
  ⇒ **`Chinese.dat` = 本地化工具/语料产物，不是引擎运行期数据**；真正被引擎读的是 `gbtext.def`（由 `"Data\Shell\Art\" + "GB" + "text.def"` 现拼，`0x8C7EA8` = `"text.def"`）。

### B.3 PC 是否存在"中文资源"

**存在，而且是完整的官方中文资源集**：

| 类别 | 文件 | 证据 |
|---|---|---|
| 中文字形页 | `Data/Shell/Art/GB1200/1600/1601/2400/2401/2402.tga`（各 1,048,594 B） | 18 B TGA 头 + 512×512×4；页数公式与之吻合 |
| 中文字形页缓存 | `Data/Shell/Art/gb{...}.rsb`（各 524,397 B） | mode 9、512×512、16bpp R5G6B5 |
| 另一套中文页 | `Data/Shell/Art/Chinese0..4.rsb`（各 524,381 B） | mode 6、512×512、16bpp；exe 无引用（另见 §A.2 注） |
| 中文码表 | `Data/Shell/Art/gbtext.def` | 1,288 个 GBK 码，升序（LE u16 序） |
| 中文语料/字表 | `Chinese.dat` | 1,101 个 GBK 码 ⊂ gbtext.def |
| 中文串表 | `Data/Shell/strings.txt` + `STRINGS.RES` | GBK；`strings.txt` 里 `"WPN_FRAG" "爆裂手雷"`、`"ITM_BINOCULARS" "望远镜"` |
| 中文文件名资源 | `Ike.log` 里 `FindFile could not find file 主菜单.map` | 引擎**按当前语言拼中文文件名**去查找 |
| 中文语系 ID | EXE `0x86CA90..0x86CAE0`：`chinese-traditional / chinese-singapore / chinese-simplified / chinese-hongkong / chinese` | 语言枚举 |

> 全目录搜 `Chinese/CHS/zh` 命名 + GBK 内容：`Chinese0..4.rsb` 与 `Chinese.dat` 是仅有的中文字面命名文件；GBK 内容另见于 `strings.txt`/`STRINGS.RES`/`gbtext.def`。

### B.4 PC 的文本长度是否受限？

**在容器层没有固定长度上限，且运行时缓冲极大；未发现 PC 侧存在 PS2 式的"固定缓冲"隐患。**

| 环节 | 证据 | 结论 |
|---|---|---|
| `strings.txt` | 纯文本，行长度自然增长（最长值实测 26 字） | 无上限 |
| `STRINGS.RES` | `{u32 byteLen}{bytes}` **长度前缀**，容器按需增长 | 无固定槽 |
| `.mis/.atr/.gun/.kit/.gtf` | XML 文本，标签值任意长 | 无上限 |
| `gbtext.def` | `2 B/条` × N，N 由文件大小决定（2576 B → 1288 条） | 只受 u16 槽位限制 |
| 渲染期缓冲 | `0x658340` 栈帧 `0x19030`（102,448 B）；文本主函数 `0x655A10` 栈帧 `0x400DC`（262,364 B） | 不存在 256/512 B 级小缓冲 |

> ⚠ 反向提醒：**PS2 侧的"长度"隐患不是文本容器给的，而是 PS2 自己的布局给的**（`FONT.RES` 展开态 7222 B / 单容器 0x40000 / 62 列网格）。PC 这一侧**没有任何等价硬墙**可参照。

---

## C. 格式同源性：PC vs PS2

### C.1 `.rsb`（Red Storm Bitmap）——**同一格式，且容器模型在 PS2 上同样精确**

**PC 侧模型（本轮实测，`pc_rsb_final.txt` 自检 42 个文件命中 40；`pc_tga2rsb.txt` 用 TGA 反证表面偏移）**：

```
{u32 mode}{u32 w}{u32 h}
  mode 4/5/6: 0x0C {u32 p0}{u32 p1}{u32 p2}{u32 p3}   （小端）
  mode 9    : 0x0C {u32 x}，0x10 {u32 p0..p3}          （大端）
Σp = 位深（p_i = 每通道位数）
  Σp ≤ 8  → 紧跟 CLUT：2^Σp × 4 B（Σp=8 → 1024 B；Σp=4 → 64 B）
  Σp ≥ 16 → 无 CLUT；mode 9 另有 11 B 附属块 `00 00 00 FF FF FF FF FF FF FF FF`
表面 = w × h × Σp/8 字节，逐行 top-down，无 swizzle
尾部 = 固定大小资源尾块，末 4 字节恒 FF FF FF FF
```

**决定性反证**：把 `GB1600.tga`（512×512 32bpp BGRA，top-down）按 `R5G6B5` 转换后，其**全部 524,288 B 在 `gb1600.rsb` 内的匹配位置 = `0x2B`（43）**；`GB1601/GB2400/GB1200` 同样 = `0x2B`。⇒ 表面偏移与像素格式**双证成立**。

**自检结果（PC，`pc_rsb_final.txt`）**：`filesize == 头 + w*h*Σp/8 + 尾` 对 42 个文件命中 40（例外 2 个见 §E）。例：

| 文件 | mode | w×h | Σp | 表面 | 尾部 |
|---|---|---|---|---|---|
| `new_font_revised.rsb` | 9 | 256×256 | 32 | 262,144 | 66 |
| `gb1600.rsb` | 9 | 512×512 | 16 | 524,288 | 66 |
| `Chinese0.rsb` | 6 | 512×512 | 16 | 524,288 | 65 |
| `hud.rsb` | 5 | 256×128 | 32 | 131,072 | 61 |
| `reticle_pistol.rsb` | 4 | 8×8 | 16 | 128 | 53 |
| `main_menu-01.rsb` | 6 | 1024×512 | 24 | 1,572,864 | 65 |

**同一模型套到 PS2（`pc_ps2_rsb_check.txt`，PS2 `GR.IMG` 内 638 个 `.RSB` 条目）**：

```
BRFG_MAP-01.RSB   mode=5 256x256 p=(5,6,5,0)  16bpp  →  28+131072+61 = 131161 = 实际 ✓
BRFG_MAP.RSB      mode=6 256x256 p=(5,6,5,0)  16bpp  →  28+131072+65 = 131165 = 实际 ✓
KIT_SNIPER-01.RSB mode=5  64x64  p=(4,4,4,4)  16bpp  →  28+8192+61  = 8281   = 实际 ✓
KIT_DEMOLITIONS-01.RSB mode=6 64x64 p=(4,4,4,4) 16bpp → 28+8192+65 = 8285   = 实际 ✓
LOAD_NEW_1.RSB    mode=5 480x480 p=(2,2,2,2)  8bpp   →  28+1024+230400 = 231452 = 实际 ✓（CLUT 1024 B）
M03_BRIDGE_OVERLAY.RSB mode=5 84x87 p=(2,2,2,2) 8bpp →  28+1024+7308  = 8360   = 实际 ✓
DECORATIONS.RSB   mode=5 256x128 p=(8,8,8,8)  32bpp  →  28+131072+61 = 131161 = 实际 ✓
LOAD_ICON.RSB     mode=5 128x128 p=(5,6,5,0)  16bpp  →  28+32768+61  = 32857  = 实际 ✓
```
**而且 PS2 文件与 PC 文件出现相同的 (mode, 尾部) 组合**：`(5,61)` 在两端都成立（PC `hud.rsb` 131,161 = PS2 `BRFG_MAP-01.RSB` 131,161；PC `load_icon.rsb` 32,857 = PS2 `LOAD_ICON.RSB` 32,857），`(6,65)` 亦然。**⇒ 同一容器格式，双端同构。**

> 与既有认知的对接：`docs/han_v2/FONT_CAPACITY.md` §一.3 记的 PS2 wire rsb `{mode}{w}{h}{p0..p3}` + CLUT + 表面 —— 本轮把它**补全成可精确算总长的模型**，并在 PS2 侧 638 个条目上验证；`p = 每通道位数、CLUT = 2^Σp × 4` 同时解释了 (2,2,2,2)→8bpp+1024 B CLUT 与 (1,1,1,1)→4bpp+64 B CLUT 两条旧记录。

### C.2 文本类：`.mis` / `.atr` / `.gun` / `.kit` / `.gtf` / `.xml` / `.txt` —— **同格式，PC 是明文版**

PS2 的 `.mis` 在 `GR.IMG` 内是 **LZ 压缩**（`stored < real`），解出来后**与 PC 的 `.mis` 结构完全相同**：

| 对 | PC | PS2(GR.IMG 条目 / 或 `docs/han_v2/mis_decoded/`) | 共同前缀 |
|---|---|---|---|
| `M01_CAVES` | `Mods/Origmiss/Mission/m01_caves.mis` 82,610 B `3c4d697373696f6e46696c653e0d0a09` | `D01_BEACH.MIS` stored=17,540 real=64,523；`mis_decoded/M01_CAVES.MIS` 90,910 B | 201 B 逐字节相同 |
| `T01` | `t01.mis` 58,237 B | `mis_decoded/T01.MIS` 58,269 B | 202 B |
| `TRAINING_MP` | `training_mp.mis` 9,774 B | `mis_decoded/TRAINING_MP.MIS` 9,595 B | 201 B |

两端字节头完全一致：`<MissionFile>\r\n\t<VersionNumber>2.000000</VersionNumber>\r\n\t<Shell>` …（分叉点只在 `<MapNameId>` 数值）。

`.atr` 在 PS2 上 **1194 个条目中 1192 个 `stored == real`（未压缩）**，头部 `3c4163746f7246696c653e0d0a093c56657273696f6e4e756d6265723e312e3030303030303c2f` = `<ActorFile>\r\n\t<VersionNumber>1.000000</` —— **与 PC 的 `.atr` 逐字节同一前缀**。
`.kit` 在 PS2 上 141/141 未压缩，头部 = `<KitFile>`；`.gun`/`.gtf`/`.res`/`.kil` 在 PS2 上被压缩（`stored < real`），但压缩帧头形态统一（`{u32 stored}{u32 real}{u32 flags}…`，例 `D01_BEACH.MIS`: `d8130000 00400000 25…`）。

### C.3 二进制类：`.qob` / `.pob` / `.map` —— **同格式，且部分文件逐字节完全相同**

**★ 最强证据（`pc_qob_diff.txt`）**：

| 文件 | PC | PS2 (GR.IMG) | 结果 |
|---|---|---|---|
| `GRASS_1.QOB` | `Mods/Origmiss/Model/grass_1.qob` 635 B | stored=635 real=635 off=0x0DCCC4A0 | **逐字节相同 = True** |
| `GRASS_2.QOB` | `Mods/Origmiss/Model/grass_2.qob` 635 B | stored=635 real=635 off=0x0DCCC720 | **逐字节相同 = True** |
| `DUST.POB` | `Mods/Origmiss/Model/dust.pob` 680 B | stored=680 real=680 off=0x0DCC4540 | **逐字节相同 = True** |
| `DEMOLITIONS-01.ATR` | 689 B | 692 B | 同格式，前 135 B 相同，之后为不同数据 |

结构对照：

```
PC  grass_1.qob     0b000000 426567696e4d6f64656c00 …      {u32 11}"BeginModel\0"
PS2 GRASS_1.QOB     0b000000 426567696e4d6f64656c00 …      （完全一致）
PC  jv_humvee.pob   09000000 426567696e504f4200 0000803f 840b833a 0b000000 426567696e4d6f64656c00
PS2 AT4_BLAST.POB   09000000 426567696e504f4200 0000803f 93b9f13a 0b000000 426567696e4d6f64656c00
                    {u32 9}"BeginPOB\0"{float 1.0}{float}{u32 11}"BeginModel\0"   ← 字段逐个对上
PC  m02_farm.map    0d000000 426567696e4d617076342e3000 …   {u32 13}"BeginMapv4.0\0"
```

### C.4 同源性总表

| 扩展名 | PC 侧形态 | PS2 侧形态 | 同一格式？ | 可用性 |
|---|---|---|---|---|
| `.rsb` | 明文单文件，43/28 B 头 + 表面 + 尾 | 明文（GR.IMG 638 条**全部 stored==real**） | **是**（容器模型 1:1 验证） | ★★★ PC 可当格式教科书 |
| `.mis` | 明文 XML `<MissionFile>` 2.000000 | LZ 压缩的同一 XML | **是** | ★★★ |
| `.atr` | 明文 XML `<ActorFile>` 1.000000 | 1192/1194 **未压缩**，同一 XML | **是** | ★★★ |
| `.kit` | 明文 XML `<KitFile>` 1.000000 | 141/141 **未压缩**，同一 XML | **是** | ★★★ |
| `.gun` | 明文 XML `<GunFile>` 1.000000/1.500000 | 压缩的同一 XML | **是** | ★★ |
| `.gtf` | 明文 XML `<GameTypeFile>` 1.000000 | 压缩的同一 XML | **是** | ★★ |
| `.xml` / `.txt` | 明文 | GR.IMG 内压缩 | **是** | ★★ |
| `.qob` | `{u32 11}"BeginModel\0"` 命名块二进制 | 同一二进制，**部分文件逐字节相同** | **是** | ★★★ |
| `.pob` | `{u32 9}"BeginPOB\0"{float 1.0}…` | 同上，**部分文件逐字节相同** | **是** | ★★★ |
| `.map` | `{u32 13}"BeginMapv4.0\0"` | 未取样（GR.IMG 无 `.map`，另有 `.MAZ/.MAH`） | 很可能 | ★ |
| `.res` | `STRINGS.RES` 明文串表 | PS2 `EN_STRINGS.RES` **压缩**（stored 47,619 / real 128,668） | 同族，需解压后逐条对齐 | ★★ |
| `.pak` | 无（PC 用真实目录） | `COMMON.PAK` 等 32 个，明文 | — | ★★ |
| `.bmf/.gtf/.chr` 等 | PC 侧 `.bmf`=Motion，`.chr`=Character | PS2 侧有 `.CHA/.CHZ` | 未验证 | — |

**PC 的资源定位方式与 PS2 完全不同**（对"分离"很重要）：PC 用**真实目录 + 搜索路径表**（EXE `0x8C10F0` 起）：
```
\data\shell\fonts   \data\shell\art   \data\textures   \data\model
\data\save\game     \data\save\replay \mods\origmiss\sound
\data\sound\music   \data\mission     \data\motion      \data\map
\data\character     \data\actor
```
PS2 则是**档案（IMG/PAK）内目录**，而且字体纹理名**只在 PAK 内部目录里解析**（`FONT_CAPACITY.md` §三 ZX1 实验）。**这条差异是 §D 的核心约束。**

---

## D. 结论：能不能照 PC 的办法做"内容/逻辑分离"

### D.1 PC 是否把「字形数据（内容）」与「字体读取/寻址逻辑（代码）」分开了？

**分开了，而且分得非常干净。** 三条实测证据：

1. **码→槽位表是外部文件**：`Data\Shell\Art\GBtext.def`，2,576 B = 1,288 × 2 B `[lead, trail]`；载入器 `0x6581A0` 每次 `fread(buf,2,1,f)` 后 `map.insert((lead<<8)|trail, i)`，`i` = 记录顺序号。**槽位编号完全由文件行序决定 ⇒ 加字 = 往文件里追加两条字节。**
2. **字形位图是外部文件**：页名 `"%s%s%02d%02d.TGA"`（`0x8C7EB4`）现算，字号与页号都是**运行时参数**；页数由 `GetFileAttributesA` 探测（`0x6583AB`）。**加页 = 放一个 `GB1602.TGA` 进目录。**
3. **纹理尺寸是数据**：`GB*.tga` 是 18 B TGA 头 + 512×512×4（尺寸在头里）；引擎转出的 `gb*.rsb` 头里 `w`/`h` 是 u32。**没有任何"512"写在文件格式里当常量**——512 只在 EXE 里（`0x657E1C mov dword [esi],0x200`）当"页宽"用。
4. **寻址逻辑全在代码里且极简**：`perRow = 512/S` → `perPage = perRow²` → `page/row/col` → `X=col*S, Y=row*S` → `U=X/512, V=Y/512`。**没有表、没有指针、没有边界数组。**
5. **唯一的"限量"是代码常量**：每字号 5 页（`0x6584C3 cmp ebp,5`）、字号 12/16/24 三档（`0x6586E0`）、槽位 u16（`0x6582DD`）。

**⇒ PC 的"内容/逻辑分离"= 「内容：两个外部文件（码表 + 页纹理）; 逻辑：一段不含任何表数据的除法公式; 容量：由文件数量与 u16 槽位决定，不由任何容器尺寸决定」。**

### D.2 PS2 侧要照做，最小改动是什么？

**先划清 PS2 侧的既有硬约束（全部已有实证，不是本轮新增）**：
* `RSFontMgr` 只有**一个**字形纹理（`mgr+0x28` 的 UIModel；`FontDefinition` 0x48 无纹理字段）——《FONT_CURRENT_STATE.md》§四·补「多 face / 多字库的真实能力」。
* CJK 字形矩形**不来自 FONT.RES 记录**，走 ELF cave 硬编码公式 `row = idx/62; col = idx%62; x = col*16; y = 2+16*(row+3*[row≥12])`，且步进宽固定 16 —— 同节「硬约束 1」。
* 纹理名解析域 = **PAK 内部目录**（ZX1/ZX1L 两盘实测全黑 + cdvd 零读取）——《FONT_CAPACITY.md》§三。
* `FONT.RES` 展开态上限 7222 B（记录预算），单容器 0x40000 —— 同文 §一.7/§一.8。

**因此：PC 的"多页"部分不可直接照搬（缺第二个纹理槽），但 PC 的"把尺寸与网格当数据"这一条可以，而且正是解药。** 分三级方案，按改动量排序：

#### 方案 P0（**最小改动，推荐先做**）：把 cave 的网格常量变成数据表 + 图集尺寸按数据读
* **依据**：PC 的 `perRow` 由 `512/S` 现算、页宽 512 只是 mgr 的一个 u32；PS2 侧对应的 `new_font_revised` **PAK 记录里的 `w`/`h` 本来就是 u32**（`docs/FONT_CURRENT_STATE.md` §二：`@0x58431` 的 `new_font_revised`，`psm=0x14 w=1024 h=512 clut_size=0x410 px_size=0x40010`）。
* **动作**：①在 ELF 里给 `NCOL/CW/CH/Y0/SKIP_ROW/SKIP_ROWS` 一个**数据表**（现在它们是 cave 立即数，`0x4170AC addiu r14,r0,62` 等），cave 改成从表里 `lw`；②表内容 = 与 PAK 头 `w/h` 一致的网格参数。
* **收益**：**改容量不再需要改代码**（只改 ELF 数据表 + 图集纹理 + 记录数），这就是 PC 那套"内容/逻辑分离"的 PS2 等价物。
* **代价**：极小（几十字节表 + cave 里 6 条 `lw`）。**已有先例**：`SLUS_P_V10→V11` 只改 2 B（CELL_H 17→16、V0R+CELL_H 147→146）即完成一次配方换代。

#### 方案 P1（**容量翻倍，一步到位**）：把单张图集从 1024×512 扩到 1024×1024（= PC 的"分页"在 PS2 上的等价物）
* **依据**：
  * PC 证明"**页 = 在图集里加一段偏移**"：`page = slot/perPage` 后再算 `row/col`，效果完全等价于**加宽图集**。
  * PS2 现役图集是 `1024×512 PSMT4`（`docs/FONT_CURRENT_STATE.md` §一/§二），引擎寻址 `U0 = 16*(slot%62)`，**它本来就允许 U 超过 1024 之外吗？不——现役靠 `p = col + PHI[row]` 的取模回绕**（同文 §六.1）。⇒ 只要把网格 **NCOL 从 62 提到 124**（或 62→62 但行数翻倍），`U0 = 16*(slot%NCOL)` 自然覆盖更宽/更高的图集。
  * `docs/han_v2/FONT_CAPACITY.md` §15.1 已记：**「font 512×608 自身未被证伪（stride 一致即可被目录步进接受）」**，且 `work/zh16b/FEASIBILITY_ANALYSIS_R4.md` §1.3 已削弱"描述符冻结"结论 ⇒ 改图集 w/h 并非禁区。
* **动作**：①COMMON.PAK 内 `new_font_revised` 记录 `w=1024,h=512` → `w=1024,h=1024`，`px_size 0x40010` → `0x80010`，整条记录 +262,144 B（MENU.IMG 条目表 `stored/real/off` 同步重排，工具链已有）；②ELF 数据表（方案 P0）改 `NCOL/行数/SKIP`。
* **收益**：容量 **1024 格 → 2048 格（4bpp 下 524,288 texel）**；若同时上 8bpp（CLUT 用现有），再翻倍。
* **风险**：与 `pda-lcd-02` 描述符实验（GR_ZX2B/ZX2D 挂死）不同——**字体纹理本身的 w/h 改动从未被证伪**，且其读盘路径是 `UITextureMgr::LoadingTexturePak` 的常规 PAK 消费。**建议先做一次 probe（4300 帧）快判。**

#### 方案 P2（**照抄 PC 的"多页"**）：需要第二个纹理槽 —— **不推荐作为最小改动**
* 要动 `RSFontMgr`（加第二个字形 UIModel）+ 绘制链（page≠0 时切换绑定）+ cave（UV 加 page 偏移），三处联调；而**收益与 P1 相同**（页 = 图集里的一段偏移）。
* **⇒ 结论：PS2 不需要"页"，只需要"更大的图集 + 数据化的网格"。**

### D.3 有没有现成的 PC 工具/格式可以直接复用？

| 工具/格式 | 证据 | 可复用性 |
|---|---|---|
| **`igor.exe`** | `igor.exe`（**文件偏移**，下同）`0x557408` `Red Storm Bitmap Files (*.rsb)\|*.rsb\|All Files (*.*)\|\|*.*\|\|`（6 处对话框过滤器）；`0x4FE478 'CFont'`、`0x553E4C 'CreateFontIndirectA'`、`0x501360 'Small Fonts'` | **RSE 官方 RSB 编辑器/转换器，且带字体生成代码**（GDI `CreateFontIndirectA` + `CFont` 类）⇒ **可直接用来读写/生成 `.rsb` 纹理**，也可当"RSB 格式规范"的活体参照 |
| **RSB 格式本身** | §C.1 的精确模型（PC 40/42 + PS2 8/8 精确总长） | 写 PS2 侧图集时按同一容器算大小；PS2 的 `.RSB` 顶层条目与 PC 同构 |
| **`ScriptEd.dll`** | 有同一套 `chinese-traditional/simplified/hongkong/singapore` 语言串（@0x5E390..0x5E3E0），**无字体代码** | 只作语言枚举参照 |
| **`Ike.log` / `IkeCrash.log`** | `Ike.log` 记录引擎实际 FindFile 失败项（含中文名 `主菜单.map`）；`IkeCrash.log` 有模块基址/时间戳 | **PC 版相当于 PS2 的 `cdvd.log`**——可用它反查"哪个资源真的被读了"（本轮 A.2 的 gbtext/TGA 结论即靠此路 + 反汇编交叉验证） |
| **`docs/han_v2/PC_FONT_MECHANISM.md`**（上一轮产物） | DBCS 扫描器 `0x7BCC10/40/80` 常量对 `(0xA1,0xFE)/(0xA1,0xF9)/(0x40,0x7E)`；`key=(lead<<8)\|trail`；SXM 混排 | **PS2 ELF 若要做 DBCS，这些常量对与扫描结构可直接移植**（该文 §7 已列建议） |
| **`STRINGS.RES` 明文串表** | §B.1 的长度前缀格式 | 可当 PS2 `RES` 的"解码后参照"，核对压缩前后条目顺序 |

### D.4 「PC 的办法不适用于 PS2」的部分（**必须说清**）

| PC 做法 | 能否照搬到 PS2 | 证据/理由 |
|---|---|---|
| 字形位图放**独立外部文件** | ⚠ **不能照字面搬** | PS2 没有"真实目录"：字体纹理名只在 **PAK 内部目录**解析（`FONT_CAPACITY.md` §三 ZX1/ZX1L 两盘全黑 + cdvd 零读取）。⇒ PS2 的"外部"只能是"PAK 内的新记录"，不是新文件。 |
| **多页**（page = slot/perPage） | ⚠ 机制可搬，实现不宜 | `RSFontMgr` 只有一个字形 UIModel（`FONT_CURRENT_STATE.md` §四·补），加第二纹理要动绘制链；而"页"与"更宽的图集"在 UV 上完全等价 ⇒ 用 P1 代替。 |
| **页宽 512 写死（mgr+0）** | ⚠ 不可照搬 | PS2 的等价常量在 cave（`0x4170AC addiu r14,r0,62` 等）**且 CJK 记录不走 FONT.RES**（同节「硬约束 1」）⇒ 只能改 cave，改不了纯数据。 |
| 字号任意（1..39）+ 三档量化 | ✅ 可搬 | PS2 现役已有 large/default/huge 三 face + `GetFont` 无边界检查；量化表可直接学 PC 的 `≤18→12 / ≤24→24 / >24→16`。 |
| **码→槽位表外部化** | ✅ **强烈建议照搬** | PS2 的记录表（`FONT.RES`）就是"槽位表"，它撞 7222 B 展开态上限；PC 的做法证明**表可以只存 2 B/字的码，把 UV 交给公式**。PS2 的 v6/v7/v8 cave **已经在做这件事**（`idx ≥ mSize → 直接 UV`）——PC 只是把它做到极致（100% 公式化，0 记录）。 |
| **纹理尺寸当数据** | ✅ 可搬（= P1） | PAK 记录的 `w/h` 本来就是 u32；`LoadRSBFile(0x51C810)` 头消费实测 `mode≥4 读 w/h 低 16 位入 UITexture+0x10/+0x12`（`FONT_CAPACITY.md` §15.1 连带收获）。 |
| **拉丁字库与中文字库分家（SXM + TGA）** | ✅ 已经是 PS2 现状 | PS2 也是"`new_font_revised` 管 ASCII（记录表路径）+ cave 管 CJK（公式路径）"，两者共用一张 512×512/1024×512 图集；PC 用**两张不同纹理**。⇒ PS2 若要分离中英字号，需第二纹理槽（同 P2 难点）。 |

---

## E. 已知限制与未决项

1. **`.rsb` 尾部块语义未定**。Σp ≥ 16 的文件，尾部大小固定（mode 4 = 53、5 = 61、6 = 65、9 = 66 B），内容为少量小整数（可见 `01/02/03`）+ 大量 0 + **结尾恒为 `FF FF FF FF`**；Σp ≤ 8（调色板）文件的"尾部"则正好是 1024 B CLUT（`28 + 1024 + 表面 = 文件长`精确成立）。**未做的事**：尾部字段的语义（疑似 mipmap/资源尾标记）。**操作提示：改写 `.rsb` 时必须原样保留尾部。**
2. **2 个 PC `.rsb` 不符合模型**：`Data/Shell/Art/pda-lcd-02.rsb` 与 `reticle_misc.rsb`（两者 `0x10` 处读出 `0x00010008` 而非 `0x00000008`，即 mode 9 头部另有一个变体字段）。文件总长仍符合 43 + 表面 + 66，只是字段解析要特判。
3. **`Chinese0..4.rsb` 的归属未完全定案**：像素面 512×512 16bpp 确定；格距实测为 **Chinese1 = 16 px**、**Chinese2/3/4 = 24 px**（列格线墨量对比 700:1，判据极强），**Chinese0 = 12 或 24 px 不确定**（pitch 24 与 12 的分值接近，因为小字号字形密、格线本身有墨）。它们与 `gb*.rsb` 的像素**不相等**（最大相等率 0.72，且色彩集不同：`Chinese*` 有 9 个 u16 值、`gb*` 只有 2 个），EXE 内无引用 ⇒ **支持上一轮"早期字库页缓存残留"的判断**，但"5 页分别对应哪些字号"仍是推断。
4. **PC `font.res` 的完整字段布局未逐字段定案**。已确证：`{u32 4}{"ike\0"}{u32 20020514}{u32 20}"new_font_revised.rsb"{u32 2}` + `{u32 7}"default"` + … + `"large"`，且运行期结构里 face 名是 16 B 定点缓冲（`@0x1234/0x1258` `default`、`@0x127C/0x129E` `large`）。**未确证**：face 记录里 `default` 之后那串 `0a/10/10/10/20/07/00/00` 的字段语义（PS2 侧 wire 序是 `08,0C,10,14,00,04,30,34,28,2C,18,1C,20,24`，PC 侧序不同）。⇒ **不要**用本文的 PC `font.res` 片段去反推 PS2 的 wire 序。
5. **PC SXM 的"每字形 10 字节度量记录"未能独立复现**。我把 EXE 的 `SXM/SXME` RCDATA 抽出（`pc_sxm.txt`：`IDR_SXM12` 212,064 B / `IDR_SXM16` 282,752 B / `IDR_SXM24` 62,312 B / `IDR_SXME12` 2,688 B / `IDR_SXME16` 6,688 B / `IDR_SXME24` 16,704 B），按 8 字节/10 字节两种步长解析都**不像干净度量表**（更像位图池）。⇒ `docs/han_v2/PC_FONT_MECHANISM.md` §5.1 的 10 字节记录布局**未经本轮独立验证**，引用时请标注出处。
6. **PS2 `.rsb` 模型命中率 88/638**：638 个条目里大量条目首 u32 是 `0x00010000`/`0x00010001`（mode=65536/65537），属于**另一种纹理封装**（非本模型覆盖），另有 29 个 mode 5 条目尾部为 1009（调色板族，与 61 的区别在于 Σp=8）。**未做的事**：把 mode 65536/65537 那一族单独定性。
7. **未做任何写操作**。本轮**没有**修改 `third_party/orig/**` 任何文件、没有生成实验 ISO、没有跑 `pcsx2-gsrunner`/`pcsx2-qt`、没有改 `tools/text_csv/*`、`font_compact.py`、`make_build.py`、`tools/font_pipeline/data/*`。

---

## F. 脚本与中间产物清单

| 脚本（新建） | 作用 |
|---|---|
| `work/tools/pc_font_struct.py` | 通用 hexdump / `font.res` 结构探针 |
| `work/tools/pc_chinese_dat.py` | `Chinese.dat` GBK 解码（→ `Chinese_dat.txt`） |
| `work/tools/pc_text_res.py` | `strings.txt` / `STRINGS.RES` 解析（→ 全量 dump） |
| `work/tools/pc_exe_strings.py` | EXE/DLL 里字体与中文字符串普查 |
| `work/tools/pc_rdata.py` / `pc_dis_range.py` | 按 VA 读字面量 / 对齐反汇编 |
| `work/tools/pc_cn_load.py` / `pc_rsb_dis.py` | 中文字库初始化器与 RSB 相关 xref 反汇编 |
| `work/tools/pc_rsb_probe.py` / `pc_rsb_surface.py` / `pc_rsb_render.py` | RSB 头部/表面判定与渲染 |
| `work/tools/pc_tga2rsb.py` | **TGA→R5G6B5 反证表面偏移（0x2B）** |
| `work/tools/pc_rsb_final.py` / `pc_rsb_headtail.py` / `pc_rsb_align2.py` | 容器模型自检（42 文件）+ 头尾 dump + 格距判定 |
| `work/tools/pc_cn_font_grid.py` / `pc_cn_grid2.py` / `pc_cn_font_measure.py` / `pc_cn_font_cc.py` / `pc_cn_font_view.py` / `pc_cn_font_profile.py` / `pc_cn_pages.py` | 中文页网格/连通域/互比 |
| `work/tools/pc_charset_rel.py` | `Chinese.dat` ↔ `gbtext.def` ↔ 串表 关系 |
| `work/tools/pc_homology.py` | PC vs PS2 文本类格式对照 |
| `work/tools/pc_ps2_img.py` / `pc_ps2_extract.py` | PS2 ISO/GR.IMG 条目普查与抽样 |
| `work/tools/pc_ps2_rsb_check.py` | **把 PC 容器模型套到 PS2 的 638 个 `.RSB`** |
| `work/tools/pc_qob_diff.py` | **PS2 vs PC 同名 `.qob/.pob/.atr` 逐字节比对** |
| `work/tools/pc_sxm.py` / `pc_nfr_view.py` | EXE SXM 资源 / 拉丁图集渲染 |
| `work/tools/pc_verify_head.py` / `pc_verify2.py` | **中文串落盘复核（防 cp936 控制台二次乱码）** |

**关键中间产物**（`work/builds/GR_ZH98/temp/r77/`）：
`Chinese_dat.txt`（**任务书要求的交付物**）、`Chinese_dat_report.txt`、`Chinese_dat_chars.txt`、`gbtext_def_chars.txt`、
`pc_fontres_struct.txt`、`pc_rsb_dis.txt`、`pc_cn_load.txt`、`pc_exe_strings.txt`、`pc_strings_res_probe.txt`、`pc_strings_res_parse.txt`、`pc_STRINGS_RES_dump.txt`、`pc_strings_txt.txt`、
`pc_rsb_probe.txt`、`pc_rsb_surface.txt`、`pc_rsb_final.txt`、`pc_rsb_headtail.txt`、`pc_rsb_align2.txt`、`pc_tga2rsb.txt`、`pc_cn_grid2.txt`、`pc_cn_font_cc.txt`、`pc_cn_font_measure.txt`、`pc_cn_pages.txt`、
`pc_homology.txt`、`ps2_gr_img_entries.txt`、`pc_ps2_rsb_check.txt`、`pc_qob_diff.txt`、`pc_charset_rel.txt`、`pc_sxm.txt`、
图：`nfr_ch_B.png`（PC 拉丁图集）、`cn0_final.png`、`gb1600_final.png`、`cn0_16px_first64_4x.png` 等。
