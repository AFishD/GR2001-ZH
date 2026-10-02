# SLUS_206.13（PS2 美版）「中文模式 / 字库分页加载」休眠代码路径判定报告

日期：2026-09-11
分析对象：`slus_out/SLUS_206.13`（37,453,732 字节，EL32 MIPS，entry=0x00100008）
方法：纯静态（字符串普查 + 全量符号表 + DWARF 调试信息 + mipsel 指令级交叉引用 + 档案条目比对），未运行模拟器。
中间产物目录：`gr_build/tmp/slus_scan/`（strings_all.txt、symbols.txt、sym_fontlike.txt、kw_hits.txt、FONT_RES_dec.bin、mdis.py/xref*.py 等可复现脚本）。

**最终结论：C —— 中文模式未编译进 PS2 版。**
PC 版实锤的那套代码（`Chinese BIG5/GB2312 Texture Loaded`、`%s%s%02d%02d.TGA` 页文件名、`gbtext.def`/`big5text.def`、`Chinese Font load successful!!!`）在 PS2 ELF 的**代码、字符串、DWARF 调试信息、光盘档案**四个层面均零残留（详见 §1/§2/§6）。PS2 用的是另一套单字节字体系统（`RSFont`/`RSFontMgr`，font.res 单图集，无分页、无 DBCS），不存在"放了 gbtext.def 就能点亮"的旁路（§4）。

---

## 0. ELF 基本情况（分析基础）

| 项 | 值 |
|---|---|
| 段 | `main`: VA 0x00100000–0x005DED80（文件偏移 0x80 起，**VA = 文件偏移 − 0x80 + 0x100000**） |
| 工具链 | `.comment`: `MW MIPS C Compiler (2.4.1.01)` / `PlayStation2`（Metrowerks） |
| 符号 | `.symtab` 完整保留：38,721 个符号（函数名、全局变量名、vtable） |
| 调试 | `.debug` 26MB DWARF + `.line`，源码路径 `F:\GR_SOURCE\PS2\Ike\...` 全部保留 |
| 指令风格 | EE(MIPS64) 混编：常见 `sd/ld` 射寄存器；少量 MMI 指令（capstone 不识别，显示为 .byte，不影响流程判读） |

**关键优势**：全部函数带名，本报告所有结论都以符号名+VA 双重锚定，不是猜的。

---

## 1. 字符串普查（任务 1/2）

对 49,760 条可打印 ASCII≥4 字符串（全量导出于 `strings_all.txt`）按关键词扫描，并对**整个 37MB 文件**（含 .debug/.line/.mwcats/.relmain）做了字节级标记搜索：

| PC 版实锤标记 | PS2 ELF 命中 |
|---|---|
| `Chinese` / `CHINESE` / `chinese` | **0** |
| `GB2312` / `gb2312` / `GBK` / `cp936` / `936` | **0** |
| `BIG5` / `Big5` / `big5` / `cp950` | **0** |
| `text.def` / `gbtext` / `big5text` | **0** |
| `%s%s%02d%02d`（页文件名格式串） | **0** |
| `GB2400` / `.TGA`（任何 TGA 扩展名字符串） | **0**（全 ELF 无一个 `.tga` 字符串；纹理扩展名只有 `.rsb/.res`，见 extensions 统计） |
| `Chinese Font load successful` / `Font load success` | **0** |
| `CodePage` / `DBCS` / `MBCS` / `ShiftJIS` / `SHIFTJIS` | **0** |

仅有的近似命中（9 个 `%02d` 全部属于音频库/JPEG 库，与字体无关）：

```
0057A380  PS2SOUND\BNK_%02d.IDC        0058B880.. PS2Sound\banks\bnk_%02d(_%02d).sh/.ss
005822D0  %d:%02d:%02d  /  005822E0 %02d:%02d     （时钟显示）
0058D25A/0058D616  JPEG JFIF 版本告警
```

**字体功能簇的全部字符串**（同一数据区聚类，即 PS2 的"字库加载功能块"全貌）：

```
0057244C  \data\shell\fonts      ← 全局 char* kShellFontsPath (0x0055C548) 指向它
0057AD40  ntsc_ike.res           ← kResourceFilename        (0x0057ABB0)
0057AD50  strings.res            ← kStringResourceFilename  (0x0057ABC0)
0057AD60  strings.txt
0057AD70  font.res               ← kFontResourceFilename    (0x0057ABE0)
```

DWARF 中的字体源文件（PS2 专属，PC 版同名体系不存在）：
`F:\GR_SOURCE\PS2\Ike\IkeUILibrary\Font\rsfont.cpp / rsfont.h / rsfontmgr.cpp / rsfontmgr.h`、`IkeFontTable.cpp`。

> 判读：PS2 的字体功能块只有"font.res 单资源 + 单一搜索路径"，与 PC 版的 `Chinese/GB2312/BIG5` 多代码页分页体系**完全不是一个数据区，也没有任何同名逻辑**。

---

## 2. DWARF 交叉验证

26MB `.debug` 扫出 57,902 条串（`dbg_strings_.debug.txt`），其中含 `chinese|big5|gb2312|gbtext` 的命中为 **0**。DWARF 连 `F:\GR_SOURCE\...` 源码路径都保留了，若编译单元里有 chinese/pcfont 类源文件必然留痕——没有。即：**PC 那套代码在其编译的源码树里就不存在（或从未纳入 PS2 工程）**。

---

## 3. 交叉引用与调用网络（任务 3）

用 mipsel `lui+ori / lui+addiu(符号扩展)` 指针对扫描（7,526 对，`pairs2.pkl`）+ 26 位跳转目标反查，重建字体加载调用网络：

```
IkeUIMgr::PreInit (0x00274F20)
  ├─ UITextureMgr::LoadingTexturePak(i, name)
  ├─ RSFontMgr::Create (0x0021A5B0)                     // new 0x74 字节对象，+0x48 清 0
  ├─ mgr->vtbl[3](0x500)  → RSFontMgr::Initialize (0x0021A450)
  │      sb 1, 0x48(mgr)                                // "字体已启用"标志 = 1
  ├─ if (mgr->0x48 != 0)                                // 0x00275044 lbu / beqz
  │     RSFontMgr::ReadResourceFile(mgr, kFontResourceFilename)   jal @0x0027508C
  └─ IkeRootContainer::Create
IkeUIMgr::Create (0x002750F0，同款逻辑第二份)            jal ReadResourceFile @0x00275298
RSFontMgr::ReadResourceFile (0x00219380, 1292B)
  ├─ diSearchFile → idistream 打开 font.res（经 kShellFontsPath）
  ├─ Read(RSUIString) 资源名；read u32 = FontDefinition 数量 → 循环读 FontDefinition{14×u32 + RSUIString 名}
  ├─ read u32 = RSFont 数量 → 循环：RSFont::ReadResource (0x0021AB50)
  │     按 RSUIString 名与 FontDefinition(+0x3C 名) 匹配
  └─ GetTexture(UITextureMgr, "font.res") → SetTexture(model1/2)   // 字图集内嵌于 .res 容器
```

引用方式说明：`font.res`、`ENGLISH` 等字符串不是被指令对直接引用，而是启动期把字面量装进全局对象（`kFontResourceFilename` 等为 RSUIString 全局，运行时 `lw *(ptr+4)` 取字符指针），代码侧引用落在这些全局变量上——以上网络即由此实证。

**排除项**（疑似 DBCS/文本路径的符号逐一查调用者后排除）：

| 符号 | VA | 调用者 | 定性 |
|---|---|---|---|
| `sjis2jis` | 0x0040E788 | 仅 `sceDevConsPrintf`（Sony 开发控制台） | SDK 残留 |
| `TOOL_Ascii2Sjis` | 0x00537F90 | 仅 `MemCardMgr::CreateSysIcon`（记忆卡系统图标需 SJIS） | SDK 残留 |
| `DrawCharacter__FiPvPfRC7tagRECT` | 0x0053A8D0 | 仅 `UIHuman::Draw`（士兵图块绘制，tagRECT=PC 风格裁剪框） | 非文本 |

---

## 4. PS2 字体格式逆向（任务 6，供扩容路线使用）

`RSFont`/`FontDefinition`（源 rsfont.cpp）：

- **索引严格单字节**：`CharWidth(char)` 0x0021AD10、`ComputeCharTextureCoords(char)` 0x0021ADE0 都对入参做 `(s8)` 符号扩展后按"字符 − firstchar"取表；`StringWidth` 0x0021AC00 以 `lb` 逐字节遍历。**没有任何前导字节/DBCS 分支。**
- 运行时字格表：**10 字节/字符**（分配时 `n*4+n` 再 `*2` = n*10，`__construct_new_array`）：
  `{u8, u8 width, u16 u0, u16 v0, u16 u1, u16 v1}`，UV 为 u16 **半像素定点**（bit0=0.5px，`bltz→(v&1)|(v>>1)` 解码）。
- 关键字段：`FontDefinition`：+0x20 firstchar(u8)、+0x38 字格表指针、+0x3C 名称(RSUIString)、+0x44 字符数、+0x0C cell 高(float)、+0x28..0x34 四个 float（UV/尺寸缩放）；`RSFont`：+0x1C 全局缩放(float)、+0x20 缩放、+0x24 比例字体开关(u8)、+0x28 → FontDefinition*。
- **无分页**：每 RSFont 一张图集（GetTexture 从 font.res 容器取纹理），没有 PC 版"每页 N 字 × 多页 TGA"概念，也没有 0x0C/0x10/0x18 页容量立即数——PS2 上该常量组不存在。
- 实测样本：GR.IMG `FONT.RES`（存储 4,421B = 单 LZ 子流 {payload 0x113D}{out 7222B}，解压 4,343B，`FONT_RES_dec.bin`）：头为 `{u32=0x14}{"new_font_revised.rsb"}`，其后为字体名（"large" 等）+ 打包字格表（约 4–5B/字增量编码），与上述结构吻合；你们 `han_v2/font_inject.py` 已在按此格式注入并验证过。

---

## 5. 触发条件排查（任务 4）

PS2 的"语言/地区"机制完整重建（与 PC 按系统代码页的方式不同）：

```
eeRpcSetLanguage(int)  0x004CF370   断言 0 ≤ lang < 6，写全局 0x00633B50
eeRpcGetLanguage()     0x004CF360
eeRpcConvertNameByLang 0x004CF220   sprintf(静态缓冲 0x005701A0, fmt, name)：
      lang0 → "EN_%s"(0x0058B6B0)  lang1 → "FR_%s"  lang2 → "DE_%s"
      lang3 → "IT_%s"              lang4 → "ES_%s"   ≥5 → scePrintf 断言
语言名单 ENGLISH/FRENCH/GERMAN/ITALIAN/SPANISH @0x00582600–0x00582620
IkeUIMgr::PlayLogo (0x002746C0)     开机 eeRpcSetLanguage(0)（默认英语）
SelectLanguage_PS2::Accept (0x00344740)
      eeRpcSetLanguage(选择) → 对 "strings.res"/"strings.txt"(0x005825D8/0x005825E8)
      逐个 ConvertNameByLang → FindFile → RSStrMgr::Unload/ReadResourceFile
OSParseCommandLine (0x00100C00)     开发用命令行 "skiplogo"(0x00570F38)：skiplogo <lang> <surround>
      → strtol → eeRpcSetLanguage（host 开发环境才有效）
另：sceScfGetLanguage (0x0054FA08) 从被调用（OSD 语言 API），未见字体相关用途。
```

**结论**：
1. PS2 的语言切换 = **文件名前缀替换**（`EN_STRINGS.RES`/`FR_STRINGS.RES`…），与档案里实际存在的 5 语言文件一一对应（§6）；
2. `font.res` 加载路径**不做语言前缀转换**（PreInit/Create 直接用 kFontResourceFilename），也不读任何代码页/EEPROM/territory 配置；
3. 唯一的"条件开关"是 RSFontMgr+0x48（Initialize 置 1），它只控制 font.res 加不加载，不存在隐藏的中文分支；
4. 因此"在盘上放 gbtext.def/GB2400.TGA 即可触发"的设想**在 PS2 上不成立**——引擎没有任何代码会去打开这些文件名。

---

## 6. 档案比对（任务 5）

`gr_lz.load_entries` 实测（脚本 `arch.py`）：

| 档案 | 条目数 | font 类 | GB*/BIG5*/text.def 类 | 语言文件 |
|---|---|---|---|---|
| GR.IMG (tmp/GR.img) | 4070 | `FONT.RES`、`SF_FONTAINE.RSB` | **0** | EN/DE/ES/FR/IT `_STRINGS.RES`+`_STRINGS.TXT`、`STRINGS.TXT`、`IKE.RES`、`NTSC_IKE.RES` |
| han_v2/menu_orig/MENU.IMG | 686 | `FONT.RES` | **0** | 同上 5 语言 RES+TXT |

盘面上 5 语言字符串资源齐全（对应 `EN_%s` 机制），但**没有**任何 GB/BIG5/text.def/GB2400 占位文件——与代码判定一致：出厂态就没有中文数据通道。

---

## 7. 结论与下一步利用方案

### 三选一结论
**C：中文模式未编译进 PS2 版。**
不是"部分残留"：不存在需要列明的缺失件——PS2 版本压根没有 CJK 字库分页这一功能块（代码 0、字符串 0、DWARF 0、盘面数据 0）。PS2 的字体是另一套单字节系统（RSFont/font.res），仅有的 SJIS 相关符号均为 Sony SDK 残留（记忆卡图标、开发控制台），与游戏文本无关。

### 对汉化项目的可执行路线（均不依赖"休眠中文模式"）
1. **字库扩容/分辨率提升的正统路线 = 沿用你们已验证的 FONT.RES 注入**：RSFont 的字格表（firstchar + 10B/字格 + 半像素 UV）和图集纹理都在 font.res 内，引擎按字节索引；做 16/24px 大图集 + 重排字格即可提升清晰度（`han_v2/font_inject.py`、`hanzi_cells.json` 已打通）。
2. **单字节上限的绕法**：引擎每字体一表（字符−firstchar 索引、字格数存于 FD+0x44），无页切换指令可用；1288+ 字需按你们现有 hanzi_slot/词组映射方案压缩字符集，或分场景切换多套 font.rs b 内多字体（RSFontMgr 支持 RSFont 数组 + 按名匹配，FontDefinition 数量字段在文件头，可加字体条目而非加页）。
3. **语言文件旁路**：`EN_STRINGS.RES` 等前缀机制可复用——但注意 font.res 不走前缀转换，无法用放 `ZH_font.res` 的方式做字体热切换；若要"运行时换字库"需补丁 eeRpcConvertNameByLang 或 kFontResourceFilename（0x0057ABE0 的 RSUIString 内容可直接改写为任意 .res 名，是唯一现成的"字体文件名重定向点"）。
4. `SelectLanguage_PS2`（0x00344D70 ctor）与 eeRpc 全局 0x00633B50 是现成的语言状态位，做"中/英切换菜单"时可挂接到现有 6 槽位逻辑（0..5，但 ConvertNameByLang 只认 0..4，需补丁或直接绑字体重定向）。

### 主要证据地址速查（VA；文件偏移 = VA−0x100000+0x80）
| 功能 | VA |
|---|---|
| RSFontMgr::ReadResourceFile | 0x00219380 |
| RSFont::ReadResource / CharWidth / ComputeCharTextureCoords / StringWidth | 0x0021AB50 / 0x0021AD10 / 0x0021ADE0 / 0x0021AC00 |
| RSFontMgr::Create / Initialize(+0x48=1) | 0x0021A5B0 / 0x0021A450 |
| IkeUIMgr::PreInit→font 加载 jal | 0x0027508C（标志检查 0x00275044） |
| IkeUIMgr::Create→font 加载 jal | 0x00275298 |
| kFontResourceFilename / kShellFontsPath / kStringResourceFilename / kResourceFilename | 0x0057ABE0 / 0x0055C548 / 0x0057ABC0 / 0x0057ABB0 |
| "font.res" / "\data\shell\fonts" / 语言名表 | 0x0057AD70 / 0x0057244C / 0x00582600–0x00582620 |
| eeRpcSetLanguage / GetLanguage / ConvertNameByLang / 语言全局 | 0x004CF370 / 0x004CF360 / 0x004CF220 / 0x00633B50 |
| EN_/FR_/DE_/IT_/ES_ 格式串 | 0x0058B6B0–0x0058B6D0 |
| SelectLanguage_PS2::Accept / PlayLogo 默认置 0 | 0x00344740 / 0x00274834 |
| 开发命令行 "skiplogo" 解析 | 0x00100C00（关键词 0x00570F38） |
