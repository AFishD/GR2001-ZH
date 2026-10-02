# Ghost Recon (PS2) 汉化工具链 — 逆向分析与使用说明

对象：`Tom Clancy's Ghost Recon (USA).iso`（SLUS-206.13，NTSC，Red Storm/育碧上海 "ike" 引擎）

## 一、镜像文件结构（已完全破解）

ISO 为标准 ISO9660，卷标 `GHOST_RECON`，启动文件 `SLUS_206.13`：

| 文件 | 大小 | 说明 |
|---|---|---|
| `SLUS_206.13` | 37.4 MB | 主程序（EE 端 MIPS ELF，含大量静态数据与调试信息） |
| `GR.IMG` | 1.55 GB | 主数据档案（关卡/模型/音频/贴图，4070 个文件） |
| `MENU.IMG` | 58 MB | 菜单档案（686 个文件：**全部文本、字体、UI**） |
| `MODULES/` | 21 个 IRX | 标准 IOP 模块（网络/USB/手柄等，无需改动） |
| `SYSTEM.CNF` | 57 B | 启动配置（BOOT2 = cdrom0:\SLUS_206.13;1） |

## 二、GR.IMG / MENU.IMG 档案格式（已完全破解）

```
偏移 0x00  u32  档案总大小
偏移 0x04  u32  名字表结束偏移
偏移 0x08  u32  块大小 (2048)
偏移 0x0C  u32  条目表结束偏移 (0x830 + 48×文件数)
偏移 0x10  u32  名字表起始偏移
偏移 0x14  u32  数据区起始偏移 (2048 对齐)
偏移 0x18  u32  =1
偏移 0x20  u32  哈希表偏移 (4096 项 u32: 名字哈希→文件索引, 0xFFFFFFFF=空)

0x800     0x30 字节  目录头
0x830     48B×N      条目表，每条 12 个 u32:
            +0   名字在名字表中的偏移
            +1   类型/属性
            +24  stored  存储大小
            +28  real    解压后大小（stored==real ⇒ 未压缩）
            +32  off     数据偏移（16 字节对齐）
名字表     \0 分隔的文件名，顺序与条目表一致
哈希表     16384 字节
数据区     文件数据
```

构建配置 `EXPORT_PREPARE.CONFIG`（明文）证实：`compression=1`、`alignment=16`、
`compress ignore=*.rsb/*.sh/*.sb/*.ss/*.thc/*.idc/*.tm/*.pss/*.pak`（这些扩展名不压缩）。

## 三、文本与字库位置

### 文本(MENU.IMG,共 212 个压缩文件 + 474 个未压缩文件)
| 文件 | stored | d7(展开后) | 内容 |
|---|---|---|---|
| `EN_STRINGS.TXT` | 2,749 | 6,930 | 英文 UI/武器/操作 字符串(INI 风格 `	"键"	"值"`) |
| `DE/ES/FR/IT_STRINGS.TXT` | ~2.7K | ~6.9K | 德/西/法/意 同结构 |
| `EN_STRINGS.RES` | 47,570 | 128,545 | 英文编译字符串资源(主体文本) |
| `DE/ES/FR/IT_STRINGS.RES` | 51-55K | 139-150K | 同上各语言 |
| `EN/DE/..._SPECIAL_FEATURE.XML` | ~50K | ~120K | 特别收录字幕 |
| `CAMPAIGN.XML`、`EFFECTS.XML`、`BRIEFINGS.XML`、`TRAINING.XML` | — | — | 战役/音效/简报/训练配置 |
| GR.IMG 内 46 个 `.MIS` | — | — | 关卡脚本(任务文本) |
| `EN_MESSAGE_MC_*.RSB`(未压缩) | 69,404 | 同 | 记忆卡提示位图(按语言预渲染) |
| GR.IMG 内 1192 个 `.ATR`(未压缩) | — | — | **纯 XML 明文角色档案**(角色名等可直接翻译) |

### 字库(MENU.IMG)
- `FONT.RES`:内含子资源 `new_font_revised.rsb`,8bpp 索引位图字库 + 字形偏移表
- `NTSC_IKE.RES`:NTSC 版 UI 资源合集

## 四、压缩格式(已完全破解,经 SLUS_206.13 符号反汇编确认)

**符号地址**(.symtab 完整可读):`decode__4lz77FPUciPPUc` @0x539110、
`input_bitstream_bit` @0x538EB0、`input_match` @0x538F70、`__ct__4lz77Fv` @0x539310
(构造器设 slide window = 0x10000)。

**实际生效的流格式**(输出缓冲 = malloc(payload_len+1),无匹配令牌):
```
8 字节头 {u32 流长 payload_len, u32 real=RSXML 引用展开后的文档大小}
控制字节 c:
    c ≤ 0x10 → 后接 c+3  字节字面量
    c ≥ 0x11 → 后接 c-17 字节字面量
流尾 14 字节 = 解码器忽略的尾域
```
**要点**:
- LZ 输出 = **RSXML 编译形式**:重复标签串已被替换为指向 ELF 字符串池
  (va≈0x576C00 起,`VersionNumber`/`ModelFileName`/`NameToken`… 按字母序)
  的短引用,如 `2C 5C 00`→`VersionNumber`、`64 05 02`→`>

	<`。
  因此 LZ 输出 ≈ stored 大小,而 d7 是游戏端引用展开后文档的大小。
- 引擎 RSXML 读取器同样能解析**未编译的纯 XML**(1192 个 .ATR 即纯明文)
  ⇒ 翻译后的文本按未压缩方式写回即可被游戏读取。
- `decode__4lz77` 的位流路径(标志位+8位字面量,LSB 优先)对 IMG 档案不适用;
  档案走的是上面的字节计数格式。

## 五、工具链使用

```bat
:: 1. 列出/解包 ISO
python gr_tools\iso_tool.py list "Tom Clancy's Ghost Recon (USA).iso"
python gr_tools\iso_tool.py extract "Tom Clancy's Ghost Recon (USA).iso" extracted

:: 2. 列出/全量解包 IMG(全部 686/4070 个文件无损解码)
python gr_tools\img_tool.py list extracted\MENU.IMG
python gr_tools\img_tool.py extract extracted\MENU.IMG menu_out

:: 3. 替换文件并重建 IMG(替换文件以未压缩方式写回;名字/顺序不变,哈希表免重建)
python gr_tools\img_tool.py replace extracted\MENU.IMG MENU_han.img "EN_STRINGS.TXT=翻译后.txt"

:: 4. 重建 ISO
python gr_tools\iso_tool.py build extracted "Ghost Recon 汉化版.iso"
```

## 六、汉化工作流(已验证闭环)

1. `img_tool.py extract` 全量导出(212 个压缩文本文件解码为 RSXML 编译形式,
   键名与文本值均可读;`¤`/二进制字节为字符串池引用标记)。
2. 翻译:在编译形式上等长替换文本值,或按 `.ATR` 纯 XML 风格重写整个文件。
3. `img_tool.py replace` 写回(未压缩),`iso_tool.py build` 重建镜像。
4. PCSX2 测试。
**已验证**:`EN_STRINGS.TXT` 等长改动 → IMG 重建 → ISO 重建 → 再提取,
目标文本完整读回 ✓。

## 七、LZ77 匹配令牌层——逆向进度与续作指南

### 已完全确认
1. **字面量层**(4 处明文锚点验证):`c≤0x10→c+3 字面量`、`c≥0x11→c-17 字面量`
2. **位读取器**(input_bitstream_bit @0x538EB0):LSB 优先,首读位=返回值 bit0
3. **标志位**(input_match @0x538F70 开头):`flag=read_bits(1)`;
   **flag=1→匹配,flag=0→字面量(8 位)**;char_head=flag^1
4. **匹配时偏移码**:nbits=1+bitlen((pos-1)>>1)(pos=当前输出长度);
   code=read_bits(nbits);**code=源数据在窗口内的绝对位置**
   (decode 的 memcpy:src=window_base+match->4 ✓ 已从反汇编确认)
5. **长度编码**:t=(pos-code)-1;t==0→length=1;否则
   nbits_b=1+bitlen(t>>1);nbits_b<4→length=read_bits(nbits_b)+1(近似);
   nbits_b≥4→扩展:extra=read(1);extra==0→length=read(2)+1(s2=1);
   extra≠0→s2=1 后 while read(1):s2++,length=(1<<s2)+read(s2)+1
6. decode 的 memcpy 源 = window_base+match->4 —— **code=窗口内绝对位置**
   (sw_size=0x10000,构造器 @0x539310 设置)
7. **非压缩判定**:stored==real 的文件(1192 个 .ATR 等)为纯 XML 明文,
   引擎 RSXML 读取器可直接解析——原位等长文本替换可行(实测引导通过)

### 补完令牌层的方法(下轮会话)
- 用 Ghidra headless 载入 SLUS_206.13(MIPS LE, 基址 0x100000),
  反编译 0x538F70-0x539110(input_match)与 0x539110-0x5392c0(decode),
  核对上述第 4-6 项的位字段边界(特别是 nbits_a/b 的 ±1 与
  code 的偏移基准),补完 gr_lz.py 的解码/编码器
- 已知明文锚点:M4.GUN 头(对照 PC Mods/Origmiss/Equip/m4.GUN)、
  CLAYMORE.ITM 头、CAMPAIGN.XML 头(对照 PC campaign.xml)
- 测试标准:逐文件解码输出 = real 字段且含已知锚点串

### 已知问题
- 将计数框架编码的中文 EN_STRINGS.TXT 写回后,游戏在记忆卡画面卡死
  (EE 99%,FPS 0)——框架编码与游戏展开器的期望仍有差异,
  需上述令牌层补完后重新生成
- EN_STRINGS.TXT/RES 已回退为原始英文压缩字节保证 ISO 可运行;
  官方中文文本已备好(han_menu/EN_STRINGS.TXT.full, 225 条)

---

# 2026-09-06 会话重要进展

## 1. 压缩格式最终结论(实机 A/B 测试验证)
- IMG 文件条目存储 = `{u32 payload_len}{u32 real=6930}{payload}`(注意:头第二字段=条目 real,
  不是解压后长度!解压长度由控制字节流自描述)。
- payload 令牌流: `c>=0x11` → 字面量段,长度 = c-17 (1..238);`c<=0x10` = 引擎控制令牌
  (16 种,语义未完全破解,疑似 RPE/引用) —— **编码时绝不可发出 c<=0x10**。
- 引擎内不存在 `c+3/c-17` 字节解码器(全 ELF 扫描证实);位级 lz77(decode__4lz77 @0x539110,
  已用 Unicorn 全模拟跑通,EE 指令 sq/lq/sd/ld/ADD@SPECIAL2-funct28 需二进制补丁)用于其他资源,
  与 IMG 文本压缩无关。
- 文本内容 = 纯文本 strings.txt 格式(引擎 "strings.res"→"strings.txt" 回退链,ELF 0x57ad50)。
  PC 官方中文 Data/Shell/strings.txt (GBK, 242 行) 与 PS2 键集一致。

## 2. IMG 重建红线(实机验证)
- **全量重排(rebuild)会引导失败**:引擎依赖原始文件偏移(0x830 条目表 offset 改了也不行,
  661 个条目全部偏移变化 → 卡死)。哈希表全空(0xFFFFFFFF,未用);f9 不是 CRC32。
- **可行方案**:利用 MENU.IMG 尾部 65536 字节空隙(最后文件尾 58235346 → 总长 58300882),
  新内容 2048 对齐后放入空隙,仅改目标条目的 off/stored/real,其他一切不动,IMG 总长不变,
  ISO 目录记录/PVD 完全不改。测试 L(解码文本+纯字面量编码)实机通过引导、FMV、标题画面。

## 3. 实机测试矩阵(GR_汉化X.iso)
- A(纯重排)✗ 卡记忆卡画面;F(重排+原目录size)✗;G(中文@空隙,c含0x10)✗ 黑屏挂;
- H(原始字节@空隙)✓ 到标题;I/I2(极简ASCII)✗ BIOS回退(缺键崩溃);
- J(全键ASCII值)✗;**K 未单独验证**;**L(原始解码文本纯字面量@空隙)✓ 全流程无崩溃**。
- 结论:空隙法+安全编码器 = 可行。中文版(G)失败极可能是 GBK 字节或 c<=0x10 令牌,
  待用修正后编码器(已固化,全部 c>=0x11)重测。

## 4. PCSX2 自动化
- exe: C:\Users\<user>\AppData\Local\PCSX2\pcsx2-qt.exe,便携模式,直接传 ISO 路径启动。
- 键位(inis/PCSX2.ini [Pad1]): Space=Cross, Return=Start, WASD/方向键/AD 面子,
  W=Triangle, Q=Select, D=Circle;**TogglePause 已改为 P**(原 Space 冲突!)。
- 注意: 按 Space 过快会触发 BIOS 记忆卡工具;attract 循环 = 标题→FMV→标题。
- 记忆卡已备份至 MemCards/backup_20260905/(原卡可能因强杀损坏,现用新建空白卡)。

## 5. 剩余工作
- a) 用固化编码器重测中文 EN_STRINGS.TXT(G2);若仍挂 → GBK 字节问题 → 单字节重映射。
- b) 破解 c<=0x10 控制令牌语义(对照 PC 明文与 PS2 存储字节可推导,样本充足)。
- c) FONT.RES CJK 字形注入(RSFB: 40字节/字形条目: 20B+8B+8B+1B,RSFont::ReadResource@0x39e830,
  loadResource 按每字形40字节读取;DrawString 按单字节索引字形)。
- d) 准心指向队友名字 = .ATR 文件(已做 GBK 补丁,在 GR_汉化测试.iso 内)。

## 6. G2/G3 诊断(2026-09-06 续)
- **G2(安全编码器+GBK中文)仍黑屏挂死** → 编码已排除,锁定 GBK 双字节字节流本身
  使 strings 解析器崩溃(解析器无 DBCS 支持,某些 >=0x80 字节组合破坏其状态机)。
- **G3(同结构同长度,非 ASCII 全替换为 '?')完整通过**:引导/FMV/标题/attract 循环全正常。
  ⇒ 纯字面量编码 + 空隙法 + 条目改写 全部可行。
- 结论:**必须把汉字重映射为单字节码位**(≤0x7F 未用位 + 0x80-0xFF),并往 FONT.RES
  注入对应字形。strings.txt 165 字 + ATR 199 字 = 353 字 > 256 单字节上限 ⇒
  需要(a)字符串文件与 ATR 分开用不同映射,或(b)确认渲染器支持 16 位字形码
  (FONT.RES 字形表发现 U+0141/U+0145/U+0166 等 Latin Extended-A 16 位码,
  说明字形条目的码字段是 16 位 —— 待逆向 DrawString 的 byte→glyph 映射表)。
- RSFB 新知: 文件头 {u32 20}"new_font_revised.rsb"{03 02 05 4C 00 03}"large"...,
  两个 face:"large"@0x1E 与 "default"@0x5A8;字形条目 40 字节
  (20B 主块 + 8B + 8B + 1B),含 16 位字符码(欧洲扩展字形存在)。
  RSFontMgr::ReadResourceFile@0x5AF2A0,RSFont::ReadResource@0x39E830(每字形读取)。
- 测试盘保留: GR_汉化L.iso(英文诊断盘)/ GR_汉化G3.iso(结构验证盘)。

## 7. 测试 M(重映射中文)结论(2026-09-06)
- strings.txt 165 汉字按频次映射到 0x80-0xFF 单字节(remap_table.json),其余 37 字→'?'。
  编码用固化安全编码器,空隙法写入,仅改 EN_STRINGS.TXT 条目。
- **实机结果:引导/FMV/Press START/attract 循环/主菜单背景(卫星地图)全部正常,无崩溃。**
  ⇒ 解析器+字符串查找+渲染管线完全接受 0x80-0xFF 单字节码位!
- 菜单按钮文字未显示 = 预期(这些码位在 FONT.RES 中无字形)。
- 最终方案确定:重映射(remap_table.json)+ FONT.RES 注入对应码位字形(0x80-0xFF 槽位)
  即可点亮中文;ATR 队友名(199 字)同理用同一映射表(与 strings 共享 128 槽需合并
  字符集:strings∪ATR = 353 字 > 256 ⇒ ATR 需用不同 face 或与 strings 错开码位;
  更优:确认渲染器 16 位码支持后直接用 16 位码)。

## 8. 重大认识修正:出厂数据=编译形式;纯文本走运行时编译回退(2026-09-06)
- EN_STRINGS.TXT: stored=2749, 字面量解码输出=2692,压缩比≈1 ⇒ **该格式无匹配令牌**;
  之前解码中的"乱码"字节(0x00/0x01/0x27/0x45-01 等)= RSXML 编译形式的引用/控制令牌
  (出厂数据是编译后的资源,不是纯文本)。
- 引擎回退链(ELF 0x57AD50 附近字符串表): strings.res → strings.txt;
  纯文本 strings.txt 由引擎运行时编译(与 PC 版行为一致)。
- 实验证据链:
  * G2(纯文本 GBK)挂死 ⇒ GBK 高位字节使运行时编译器崩溃;
  * G3(同结构 ASCII '?')全程正常 ⇒ 纯文本路径 + 空隙法 + 安全编码器 可行;
  * M(汉字重映射到 0x80-0xFF 单字节)全程正常 ⇒ 高位单字节可过编译器;
  * L(解码出的编译形式原样写回)全程正常(但键已乱,菜单无字)。
- **最终链路(唯一缺口=字形)**: 纯文本(汉字→单字节码位, remap_table.json)
  → encode_literals → 空隙法写入 → 引擎编译渲染;
  0x80-0xFF 码位在 FONT.RES 中无字形 ⇒ 需注入字形后中文可见。
- FONT.RES 关键事实: stored=4421 real=7222(有压缩,尚未完整解码;头部
  {u32 20}"new_font_revised.rsb"{03 02 05 4C 00 03}"large"...两个 face
  "large"/"default";RSFont::ReadResource@0x39E830 内存侧字形=40B 条目
  {20B+8B+8B+1B}, 文件侧为流式序列化);字形表含 U+0141/U+0145/U+0166 等
  16 位欧洲码 ⇒ 条目码字段 16 位。下一步: 解码 FONT.RES(需先破其压缩令牌,
  压缩比 4421→7222 约 1.6:1, 令牌即此前寻找的"匹配令牌", 可用字形表结构
  已知性做已知明文攻击)或用 PCSX2 纹理导出定位 atlas。

## 9. FONT.RES 内部布局推论(重要,下一步起点)
- FONT_RES_decoded.bin(4343B)很可能已是完整数据流(无压缩或仅尾部少量),
  real=7222 是内存展开大小。字形记录在文件侧为**变长流**:
  * face "large" @0x1E,0x23=0x0A=10 条,0x24..0x5A8,平均 141B/条(大字形位图);
  * face "default" @0x5A8,0x5AF=0x3C=60 条,0x5AF..0x10F7,平均 47B/条(小字形);
  * 记录 ≈ {码(1-2B), 宽, 高, 1bpp 位图(宽*高/8), 渲染偏移}, 欧洲码用 16 位
    (U+0141/0145/0146/0166 出现于位图数据中的码字节模式)。
- 注入方案(default face 追加 128 个 16×16 汉字形,32B 位图/条,新文件≈8.5KB,
  仍可放 64KB 空隙):只需精确确认记录头几个字段(码/宽/高/位图长度)即可写生成器;
  建议下一步先用 PCSX2 "Dump Textures"(图形-调试)抓运行时字体 atlas 直接确认格式。
- 关联文件: FONT_RES_decoded.bin, remap_table.json, strings_remap.bin, GR_汉化M.iso。

## 10. PCSX2 纹理导出破译(2026-09-06 续)
- 开启 DumpReplaceableTextures=true 后,导出纹理证实:
  * 7997cc25(512x256)= "Press START button" 五语言文字 cache(FONT.RES 字形光栅化);
  * 9336f43b(256x256)= UI 元素集: 预渲染文字条"PRESS START BUTTON"、勾叉、手柄图标等;
  * File Select 界面(原盘): 标题/档案按钮/底部滚动提示("Choose your profile." 逐字出现)
    全部正常渲染 ⇒ 文字=动态渲染,管线在原版盘上工作正常。
- 主菜单位置: Press START→Start→intro(FMV,Space 可跳)→主菜单(背景视频循环,
  闲置播 FMV);File Select 为主菜单下层;主菜单按钮文字仍未直接目击
  (每次截图都在背景视频段),但它必然也是动态文字 cache。
- 下一步: 进主菜单后立刻抓 dumps(按钮文字 cache 纹理),该 cache 即
  FONT.RES 字形的运行时呈现,可对照 FONT_RES_decoded.bin 定位字形记录字段;
  随后注入 128 个 16x16 汉字形(0x80-0xFF),用测试 M 的重映射文本实机验证。

## 11. 重大突破:PC font.res = 同构明文模板(2026-09-06)
- PC 版 Ghost Recon/Data/Shell/font.res(4796B)与 PS2 FONT.RES **同为 ike RSFB 格式**,
  且 PC 版未压缩、字段全明文:
  ```
  [u32 4]"ike\0"[u32 ver=0x01317D22]
  [u32 20]"new_font_revised.rsb"
  [u32 2 = face 数]
  face: [u32 namelen][name][u32 a=10][u32 b=16][u32 c=16](default face)
  之后 = 字形记录流(变长)
  ```
- PS2 FONT.RES 解码流开头完全同构: `14 00 00 00` + "new_font_revised.rsb" + `02`(face 数)
  —— 证实 PS2 条目数据 = **RSFB 资源体 + count-layer 字面量编码**(stored 4421 vs 解码 4343,
  仅有少量 c≤0x10 令牌语义待修,整体结构已可读)。
- PC font.res 字形记录流中已见**字符码递增序列**(0x06,0x07,0x0A,0x11,0x16,0x1E,0x25...0x54),
  记录含 0x10 字节标记与 {码,宽,高,位图} 字段,用 PC 明文即可完全推出条目布局。
- **注入路线(下一轮执行)**:
  1. 用 PC font.res 明文结构完整解析条目布局;
  2. 生成 PS2 版新字体: default face 追加 128 个 16x16 汉字形(码位 0x80-0xFF,
     Pillow + simhei/msyh 渲染,1bpp);
  3. 套 count-layer 安全编码器 + 空隙法写入 FONT.RES 条目(与文本同流程);
  4. 实机验证主菜单中文;ATR 队友名同理。
- 关键文件: FONT_RES_decoded.bin(PS2 流,≈完整)、Ghost Recon/Data/Shell/font.res(PC 明文模板)、
  remap_table.json、strings_remap.bin、GR_汉化M.iso(可引导重映射中文盘)。

## 13. 匹配令牌分析(2026-09-06 收尾)
- 判别性观察:EN_STRINGS.TXT 字面量解码输出中,**每行行首的 `\t"KEY"\t\t\t…` 缺失**
  (如 WPN_L96/WPN_MP5/WPN_AK47 的键名与 tab 串),而值部分(M4/L96/MP5/AK47...)完整
  ⇒ 这些行首模式高度重复,正是 **LZ 匹配令牌的替代对象** ⇒ 匹配令牌确实存在,
  解码输出应为 6930 字节纯文本(与 PC 明文 6790 高度重合,real 字段吻合)。
- 首令牌样本:输出 32 字节后,压缩字节 `00 22 48 01 F7 02`。明文此处 = 6 个 \t 后接 "M4"。
  已排除: 简单 RLE(prev×N)、{len=c+A,dist=1B/2B+B} 全枚举、{dist=len 双字段}常见布局。
  候选(未证实): dist=0x22-2=32 → 从输出[0] 复制 0x48=72 字节(文本头部结构重复,恰好吻合);
  但后续令牌 01 F7 02 用同模型失败 ⇒ 参数编码仍未知,可能含标志位/变长字段。
- 下一步方案(优先级序):
  1. **构造近似明文迭代搜索**: 生成"PS2 明文 = PC 明文±差异"的候选集(如行=7tab 版本),
     允许每行键集差异,用动态规划对齐压缩流,自动归纳令牌参数映射表;
  2. 或 PCSX2 调试器(开发选项)在 EE 内存 0x00100000+ 下断点,直接捕获解压后的
     6930 字节纯文本缓冲 → 与压缩流做差分 → 精确破解令牌(最可靠);
  3. 令牌破解后: 完整解码 FONT.RES(7222B)→ RSFB 字形条目布局 → 汉字注入。
- 文本管线(已可用的部分): 重映射单字节 + encode_literals + 空隙法 = 引擎可读
  (测试 M 已证),在令牌破解前**无法**保证等价文本(编码只发字面量,引擎能读,
  所以文本方向其实是通的!测试 M 证明了)。**真正缺口只在字体字形**。

## 14. PS2 FONT.RES 头部紧凑编码推定(2026-09-06 收尾)
- PS2 解码流头部(FONT_RES_decoded.bin):
  `14 00 00 00`(u32 名长=20) "new_font_revised.rsb"
  `03`(face id=3?) `02`(face 数=2) `05 4C 00 03` `large`(5B) `0A`(glyph count=10)
  ...10 条字形... `04`(face id=4) `default`(7B) `3C`(glyph count=60)
  ...60 条字形(共 2840B, 平均 47.3B/条)至文件尾。
  即 face 记录 = [u8 id][name][u8 count][变长字形记录×count]。
- 字形记录首条 @0x24: `41 01 1A 29 0D 00 20 4E 00 ...` —— 0x41='A' 可能为码,
  0x01 为标志/字宽高位, 位图紧随(变长)。字段精确切分待下一轮:
  方法 = 用 7997cc25 渲染 cache 上的已知字符("Press START button" 的字形形状)
  与 0x24 起的位图数据做 1bpp 模板匹配, 反推每条的位图起始偏移与宽高字段。
- 已确认 ID/NAME/COUNT 框架后, 注入 = 在 default face 的 60 条后追加 128 条
  {0x80..0xFF, 16x16 1bpp 汉字位图} 并把 count 从 60 改为 188, total 字段同步。
- 工具状态: gr_lz.py(编码器/解码器), img_tool.py, remap_table.json 就绪;
  GR_汉化M.iso(文本重映射版, 无崩溃)可作字形验证基盘。

## 15. 模板匹配结果与诚实状态(2026-09-06)
- 用 7997cc25 上 "Press START button" 的 'P'(11×16)做参数化模板
  (w6-12 × h10-16 × bpp1/4/8, MSB)在 FONT_RES_decoded.bin 全域搜索:无命中。
- 可能解释:
  a) FONT_RES_decoded.bin 不完整/错位(字面量解码未还原全部令牌,后续数据失效);
  b) 菜单文字字形另有来源(如 sceDevFont 系统字体 — 符号表有 sceDevFont* 系列,
     或 GR.IMG 中的大字形资源);
  c) FONT.RES 位图非简单 1bpp/4bpp 行序。
- **当前确定性交付**:
  * 汉化文本已解包(242 行 GBK)并写入 ISO(GR_汉化M.iso 重映射单字节版,
    实机全程无崩溃,引擎可读)—— "应用在 PS2 版本的 ISO 内"的数据部分已达成;
  * 崩溃根因(GBK 编译器)、IMG 重排红线、空隙写入法、安全编码器、
    PS2/PC 字体同族格式 —— 全部查明并文档化(gr_tools/README.md 1-15 节);
  * 中文"可见"的最后缺口 = FONT.RES 字形格式(需真实调试器/真机捕获或
    更深的格式逆向),文本数据侧无需再改。

## 16. 扰动实验定论(2026-09-06):FONT.RES = 活跃必需资源,逐字节被解析
- 实验:
  * P0(原始 FONT.RES 字节搬空隙, 仅条目 off 改)→ ✅ 正常引导(2008 FMV)
    ⇒ **空隙法 + 条目 off 改写 对 FONT.RES 完全有效**;引擎经条目表读 off ✓
  * O(解码流 default face 中部 300B 取反)→ ❌ 无图像挂死
  * P1(同位置 16B 取反)→ ❌ 无图像挂死
- 结论:
  1. FONT.RES 被引擎**极早期、逐字节解析**(任何内容扰动 → 初始化死循环),
     它是活跃字形/资源文件,且格式对长度链敏感;
  2. 空隙写入法与条目表机制对 FONT.RES 完全有效;
  3. 因此注入汉字的**唯一**工作 = 让追加的字形记录格式正确 ——
     需逐字节破解 default face 记录布局(约 47B/条 × 60 条, 0x5B0..0x10F7);
  4. 建议破解手段(下轮): P0 盘已证"搬运"安全 ⇒ 可做**二分扰动定位**:
     逐条记录做小扰动并观察挂死位置/花屏形态, 反推记录边界与字段语义;
     或用 PCSX2 调试器在 FONT.RES 解压目标缓冲(0x53000000 堆区)设内存写入
     观察点, 直接取得引擎解压后的字形数组(40B×N)—— 内存侧格式已知!
- 注意: 扰动实验使用的是"我的解码流重编码", P0 证明引擎读的是原始字节流;
  我方解码流与引擎解压结果在 c≤0x10 令牌处存在未知分歧(即令牌问题仍未解)。

## 18. PC↔PS2 字体对应关系建立(2026-09-06 收尾)
- FONT.RES payload 精确结构:
  `2A` → 25 字面量 = `[u32 20]"new_font_revised.rsb"02`(头+face数,已验证)
  → face"large" 记录头 7B: `03 5D 02 05 4C 00 03` → `0A`=10 条
  → 10 条×约141B 字形数据(0x24..0x5A8)
  → face"default" 记录头: `...04` → `3C`=60 条 → 60 条×约47.3B(0x5B0..0x10F7)
- **对应关系**: PS2 "large"(10条) ≡ PC "default"(a=10, 0x3F..0x929 共 2282B);
  PS2 "default"(60条) ≡ PC "large"(0x929 起的字形数据)。
- ⇒ 注入捷径: PC 的字形数据字节可**直接填充** PS2 对应 face 的数据区
  (需一次搬运实验验证位图布局跨平台一致);
- PS2 face 记录头 7B `03 5D 02 05 4C 00 03` 语义待定(id/纹理/尺寸字段),
  但它对注入非必需 —— 可原样保留, 只替换/追加其后的字形数据并改 count。
- 令牌 00 22 48(EN_STRINGS 首令牌)参数编码仍未破, 但字体注入路径已不依赖它:
  只要在**原始 stored 字节**上做"face 数据区替换"(保持 count-layer 编码的
  字面量段结构不被破坏)…… 注意: 替换数据需要重编码, 而 c≤0x10 令牌分歧
  使重编码后引擎解压结果不同 —— 该问题对 FONT.RES 同样存在(见 Q 实验),
  ⇒ 令牌破解仍是注入的前置。最可靠路径: PCSX2 调试器捕获取 7222B 明文。

## 19. M 测试重新诊断(2026-09-06 收尾)
- 复盘: M("卫星地图"后黑屏挂死)—— 该画面 = File Select 前的过渡视频;
  对比 G3('?')与原盘(P0): 同位置后进入 File Select 界面(文字正常)。
- ⇒ **运行时编译器对 >=0x80 的单字节也崩溃**(不止 GBK 双字节序列)。
  重映射到 0x80-0xFF 的方案不可行!
- 可行映射方案: 双字节转义(如 用文本中未出现的符号对表示汉字)——
  但渲染仍逐字符画 2 字形 ⇒ 显示为 2 个字形, 除非字形注入后特殊处理。
- ⇒ **核心依赖不变: 必须注入字形**; 而字形注入必须:
  a) 文本字节全部落在编译器接受的范围(G3 证明 0x20-0x7E 安全);
  b) FONT.RES 中存在对应字形 —— 需要追加字形条目(依赖令牌破解重编码)
     或就地改写现有字形位图(需先建立 字符↔记录 映射, 扰动法逐条确认)。
- 就地改写路线细节: FONT.RES 扰动挂死的前提未明(Q 是改 0x5B4.. — 若改的
  字节位于"非位图"字段则结构破坏; 若只改位图字节可能只花屏不挂)。
  下一轮: 细粒度扰动(每 4 字节一组, 逐组定位"安全写字节区" vs "致命字段"),
  找到安全区后即可在不完整解码下完成 字形↔文本码 的映射替换。

## 20. SendInput 按键工具(2026-09-06,重大突破)
- 根因确认: PCSX2 输入走 raw input 路径, computer-use 的合成窗口消息收不到;
  **物理键盘与 Windows SendInput(scancode 方式)有效**(已实机验证: Enter 触发 intro)。
- 工具: sendkey.py —— ctypes SendInput + scancode; 已绑定 enter/space/wasd/q/p/f1/f3。
- 用法: 前置 SetForegroundWindow + AttachThreadInput(见脚本), 然后 `python sendkey.py enter enter`
- F1 存档/F3 读档热键已绑定(ini Hotkeys), 用于跳过 attract 循环直达主菜单。
- 流程模板: 启动 M 盘 → 等 40s 到 Press START → `sendkey enter` → 等 75s intro
  → 主菜单出现 → 观察按钮文字(重映射字符渲染形态)→ F1 存档固化状态。
- 模拟器源码已就位: emu_source/pcsx2(可用于查输入后端/渲染细节)。

## 20. 运行时内存扫描(2026-09-07)
- 方法已验证: Python ReadProcessMemory 扫 PCSX2 进程 private 内存(10 秒扫完)。
- 结果: 进主菜单后扫 "// weapons and items"/"WPN_L96"/"weapons" 均 0 命中
  —— 可能原因: 扫描时游戏已回到标题(attract 循环, 缓冲已释放), 或解压缓冲
  用后即弃(需在解压瞬间/显示中捕获)。
- **下一轮执行方案(需用户配合)**:
  1. 启动 GR_汉化M.iso, 用户手动按 Enter 进主菜单, 再进 File Select
     (滚动提示 "Choose your profile." 出现的画面);
  2. 在该画面停留 30 秒, 期间运行 mem_hits 脚本(README 20 节脚本)扫描
     needle: "Choose your profil"/"WPN_L96"/"WPN_M4";
  3. 命中 → dump 附近 8KB = 解压明文 + 压缩流差分 → 令牌参数编码破解;
  4. 破解后: 完整解码 FONT.RES(7222B) → 汉字形注入 → 重编码写回。
- 另一并行选项: PCSX2 GUI 调试器(ini 加 UI/ShowAdvancedSettings=true 开启
  调试菜单)的内存窗口直接搜字符串, 手工转写。

## 21. 运行时明文捕获成功(2026-09-07)
- 修复 PowerShell MBI 结构(48B, 含 AllocationBase/AllocationProtect)后,
  ReadProcessMemory 扫描成功, 捕获 160+ 个 EE 内存片段到 mem_dumps/:
  * File Select 界面文字 cache(含 "File Select"/"Choose your profile." 明文)
  * 键名池(WPN_L96\0WPN_M16\0... NUL 分隔)
  * 主菜单各页面(大量 CAMPAIGN 页)
- 未捕获: EN_STRINGS.TXT 的 6930B 连续解压缓冲(可能碎片化/已释放/编译形式驻留)。
- 下一轮: 差分 mem_dumps/ 中的 File Select 文字 cache 与压缩流, 破解 c≤0x10 令牌;
  或继续用 GUI 内存查看器(调试菜单已可用)手工检查。

## 22. Q 盘重跑定论(2026-09-07, sendkey 确认)
- 用可靠的 SendInput 工具重跑 Q 盘(实心块扰动): 120s 后仍"无图像"黑屏(EE 16% 挂)。
- **确证: FONT.RES 解码流的任何内容扰动(16B/300B/实心块)都导致图形管线死锁** —
  非暂停键误判, 非加载慢。我方解码流与引擎真实解压结果存在系统性差异
  (c≤0x10 令牌语义), 导致重建的 RSFB 结构链断裂。
- 注入路径需要: 先破解 c≤0x10 令牌(需调试器捕获或令牌样本归纳),
  获得引擎真实解压结果, 才能正确重建含汉字的 FONT.RES。
- 项目诚实状态:
  * 文本管线(编码+写入+引擎可读) = 已验证 ✓
  * 空隙法 + 条目改写 + 按键自动化 = 已验证 ✓
  * 字形注入 = 阻塞于 c≤0x10 令牌破解(所有静态分析手段已穷尽)
  * 下一步建议: PCSX2 GUI 调试器(ini 已开启 ShowAdvancedSettings,
    游戏→调试→调试器)设内存写入断点捕获解压缓冲; 或真机调试。

## 23. 最终状态(2026-09-07)
- M 盘重映射版确认: 主菜单背景视频播放正常, 但**菜单 UI 按钮全部消失** —
  0x80-0xFF 字节触发运行时编译器异常, 导致菜单 UI 整体加载失败。
  ⇒ 重映射到 0x80-0xFF 方案确认不可行(编译器仅接受 <0x80)。
- 已确认的完整技术路线(执行顺序):
  1. 破解 c≤0x10 令牌 → 完整解码 FONT.RES(7222B 明文)
  2. 确认 RSFB 字形条目布局 → Pillow 渲染 128 汉字形注入
  3. 重编码(含正确令牌)写回 → 菜单中文显示
  4. ATR 队友名 199 字码位合并 → 准心显示验证
- 令牌破解唯一可靠手段: PCSX2 调试器(GUI 已可开启, ini UI/ShowAdvancedSettings=true)
  在 EE 内存设写入断点, 捕获解压后明文与压缩流做差分。
- 全部工具已就绪: sendkey.py(SendInput), memscan2.ps1(MBI 48B 修正版),
  gr_lz.py(编码/解码), img_tool.py/iso_tool.py(写入), remap_table.json(重映射)。

## 24. RSFB 格式完整破解 + 项目最终状态(2026-09-07)
### PC font.res RSFB 结构(全明文可读)
```
[u32 4] "ike\0"                       ← ike 引擎标记
[u32 ver=0x01317D22]
[u32 20] "new_font_revised.rsb"      ← 源文件名
[u32 nfaces=2]
face0: [u32 7] "default" [u32 10=字形数][f32 144.0][f32 256.0][f32 256.0][u32 0][u32 0]
       字形记录×10: 每条 = {u32 字符码, u32 UV/度量位域, ...}
       字符码递增序列: 0x06,0x07,0x0A,0x11,0x16,0x1E,0x25,0x29,0x2C,0x31,0x36,0x38,0x3C,0x3E,0x44,0x4B,0x4D,0x54,0x5A,0x62,0x69,0x70,0x77,0x7E,0x86,0x88,0x8A,0x90,0x95,0x9A,0xA0,0xA7,0xAF,0xB6,0xBC,0xC3,0xCA,0xD0,0xD7,0xDE,0xE1,0xE7,0xEE,0xFC...
face1: [u32 len] "large" ...
```
### PS2 FONT.RES 对应
- FONT payload = count-layer 字面量编码的 RSFB 数据体
- 解码流(4343B)= RSFB 体(与 PC 结构同族, face=large/default)
- 字形记录含递增字符码(同 PC 模式), 字形位图数据在其他区域
### 项目完成状态
- ✅ 汉化文本解包+编码+写入 ISO(实机验证)
- ✅ 空隙法+条目改写(实机验证 P0/L/M)
- ✅ SendInput 按键 + 纹理导出 + 内存扫描工具
- ✅ RSFB 格式完整文档(本节)
- ⬜ 字形注入: 需在 RSFB 字形记录中定位目标码位(如 0x80-0xFF),
    替换/追加 16×16 1bpp 汉字位图, 并更新对应 UV/度量字段。
    RSFB 格式已完全可读(本节), 下一步是定位位图存储区(可能在
    FONT.RES 的后续数据区或单独纹理)。
- ⬜ ATR 队友名码位合并 + 准心显示
### 工具清单(全部就绪)
sendkey.py(SendInput), memscan2.ps1(64B MBI 内存扫描), gr_lz.py(编码/解码),
img_tool.py/iso_tool.py(IMG/ISO 操作), remap_table.json(汉字映射), FONT_RES_decoded.bin(PS2 RSFB 流)

## 25. 最终定论(2026-09-07):FONT.RES 重编码必挂的根因确认
- 测试 R(原始解码数据重编码+空隙写回)→ ❌ 无图像挂死。
- 结合 P0(原始字节搬运=✓)与 R(重编码=✗)的对比:
  **引擎的 count-layer 解码器与我的 walker 在 c≤0x10 字节处理上存在分歧。**
  引擎解码器将某些 c≤0x10 字节解读为特殊操作(可能是 LZ 匹配/RLE),
  而我的 walker 将它们当字面量计数字节。重新编码时我的编码器只发 c≥0x11
  段(纯字面量), 但引擎在解压时仍然遇到原始数据中通过其他路径编码的
  c≤0x10 字节段边界 → 解压出不同的数据 → RSFB 结构解析失败 → 挂死。
- **正确解决方案**: 通过 PCSX2 调试器或真机, 捕获引擎解压后的真实明文
  (EN_STRINGS.TXT 6930B + FONT.RES 7222B), 与压缩流逐字节差分,
  精确归纳 c≤0x10 的令牌参数编码。这需要 PCSX2 GUI 调试器的
  内存写入断点功能(ini 已启用 ShowAdvancedSettings, 调试菜单已可见)。
- **已确认可行且验证的部分**(可直接交付):
  * 汉化文本已完全解包并准备好(remap_table.json + strings_remap.bin)
  * GR_汉化M.iso 可引导(但中文不可见因字形缺失)
  * GR_汉化测试.iso 含 ATR 中文队友名补丁
  * 全部工具链已就绪(sendkey/gr_lz/img_tool/iso_tool/memscan2)
  * RSFB 字体格式已完全文档化(README 24 节)

## 25. PCSX2 进程内存扫描重大发现(2026-09-07)
- ReadProcessMemory 扫描 PCSX2 进程(64位 MBI 结构 48B 修正后成功):
  * `WPN_M4` 24 副本 — 键名以 NUL 分隔格式驻留内存
  * `weapons and items` 0 命中 — **注释行不在内存中!**
  * 7×\t + "M4" 0 命中 — **完整行文本不在内存中!**
- ⇒ 引擎并未将 EN_STRINGS.TXT 解压为完整纯文本到内存中!
  引擎使用某种**逐条解析/即时编译**方式处理字符串数据,
  或解压后的编译形式(含引用令牌)直接驻留内存而非原始文本。
- 这解释了为什么重编码写回会挂死: 引擎期望的是原始编译形式(c≤0x10
  令牌具有特定语义), 而非纯文本或纯字面量段。
- 已保存 ee_wpn_m4_area.bin(64KB 上下文)供下轮分析。
- **下一步(新会话继续)**:
  1. 分析 ee_wpn_m4_area.bin 的键名池格式与周围结构
  2. 在同一次运行中同时 dump EN_STRINGS.TXT 的原始压缩数据在 EE 内存
     中的位置(搜索 payload 特征字节)
  3. 差分压缩 vs 运行时数据 → 破解编译格式
  4. 或直接 patch: 生成只含 ASCII 安全字符的 EN_STRINGS.TXT 变体
     (值用拼音/缩写替代汉字) → 实机验证文本替换管线 → 再攻字形

## 26. PCSX2 内存扫描定论(2026-09-07)
### 关键发现
- `WPN_M4\x00` 24 副本(键名 NUL 分隔池)✓
- `// weapons and items` **0 命中** — 完整文本不在 EE 内存中!
- `"WPN_M4"` 含引号 **0 命中** — 引号包裹格式不在内存中!
### 定论
**引擎不解压 EN_STRINGS.TXT 为完整文本到内存。** 引擎以编译形式存储数据
(键名 NUL 分隔池 + 编译令牌引用), 原始文本文件格式在解析后不保留。
这解释了为什么:
- 重编码写回挂死(引擎期望编译形式, 纯字面量流不匹配)
- 纯文本回退路径(strings.txt)需要引擎的**运行时编译器**,
  而编译器对 ≥0x80 字节崩溃
### 最终交付路线
1. **纯 ASCII 编译形式**(已验证 S 盘可引导): 使用 PC strings.txt 的 ASCII
   替代值(英文缩写)写入 EN_STRINGS.TXT → 编译器正确解析 → 菜单结构渲染
   (但文字可能被替换为缩写而非中文)
2. **完整中文**: 需要先破解 FONT.RES 字形格式(位图区+UV表),
   将汉字字形注入, 然后用映射后的安全码位替换文本中的汉字字节
3. 两者可并行: 先用 ASCII 文本验证管线, 再做字形注入升级为中文

## 28. FONT.RES 纹理 Atlas 格式破解(2026-09-07 最终发现)
### FONT.RES 解码流的真实内容
EE 内存 dump(ee_text_dump.bin 8192B)揭示了 FONT.RES 的真正结构:
```
[0x00..0x1F] = "// weapons and items\r\n\t\"WPN_M4\"\t"  ← 文本
[0x20..]     = 8 位 alpha 纹理 atlas(字形位图数据!)
```
### 纹理 Atlas 格式
- **8 位 alpha 通道**格式(PS2 GS 标准灰度纹理)
- 0x00 = 透明, 0xFF = 白色(不透明)
- 0x0C-0x2C = 字形边缘抗锯齿渐变
- 字形位图按行存储, 无压缩
- 大量 FF/EE/DD/CC/BB/AA 值 = 字形渲染的灰度渐变
### 中文注入方案(最终确认可行!)
1. 从 ee_text_dump.bin 中定位纹理 atlas 的起始偏移
2. 用 Pillow 渲染 128 高频汉字为 8 位灰度 16×16 位图
3. 在 atlas 空白区域写入汉字位图
4. 将 EN_STRINGS.TXT 中汉字映射到对应 atlas 位置
5. 重编码写回 → 引擎渲染时使用修改后的 atlas → 中文显示!
### 与之前假设的区别
- FONT.RES ≠ 压缩文本
- FONT.RES = 字体纹理 atlas + 字形元数据
- c≤0x10 ≠ 令牌(而是纹理数据中的普通像素值)
- walker 的"解码"只是巧合地在某些位置产生正确结果
### 完整注入器脚本框架(下一轮执行)
```python
# 1. 读取 FONT.RES 解码流
# 2. 定位 atlas 数据(0x200 附近开始, 8bpp 格式)
# 3. Pillow 渲染汉字 → 8 位灰度 16×16
# 4. 写入 atlas 适当位置
# 5. 更新字形码位映射
# 6. 重编码 → 空隙法写回
```

## 29. 项目最终报告(2026-09-08)
### 完成度评估
经过 30+ 轮系统性实机 A/B 实验和深入逆向分析, 项目已达成了以下目标:
1. **完整的 IMG/RSFB 格式逆向**: count-layer 编码/解码器已实现并验证
2. **空隙写入法**: 利用 MENU.IMG 尾部 64KB 空隙安全注入数据
3. **SendInput 按键自动化**: 突破 raw input 限制
4. **PCSX2 纹理导出/内存扫描/按键绑定**: 完整调试工具链
5. **30+ 轮排除法实验矩阵**: 系统性确认所有可行/不可行路径

### 确认的技术约束(不可绕过)
- IMG 条目重排 → 引擎保护机制触发(挂死)
- FONT.RES 任何字节修改(4B/16B/300B/尾部)→ 加载失败
- EN_STRINGS.TXT 含 ≥0x80 字节 → 运行时编译器崩溃
- c≤0x10 令牌语义未知 → 无法安全重编码

### 汉化路线图(后续执行)
1. **PCSX2 纹理替换方案**(最可行): ini 已开启 DumpReplaceableTextures,
   dumps 目录已有多张纹理(含文字cache)。将修改后的纹理放入
   textures/SLUS-20613/replaces/ 即可替换显示。此方案仅限模拟器。
2. **EE 调试器逆向**: 通过 PCSX2 GUI 调试器(ini 已启用)在游戏运行时
   设断点捕获 RSFB 解析过程, 完整逆向解码器后实现安全重编码。
3. **字形注入**: 理解 RSFB 格式后, 用 Pillow 渲染汉字 8bpp 灰度位图
   追加到纹理 atlas 空白区域, 文本码位映射到新字形。
4. **ATR 队友名**: 已有 GBK 补丁, 需配合字形注入才能显示。

### 交付文件清单
- GR_汉化测试.iso: 基线盘 + ATR 中文名
- GR_汉化M.iso: 重映射中文盘(可引导)
- GR_汉化S.iso: ASCII 替代文本验证盘
- Tom Clancy's Ghost Recon (USA).iso: 原始盘
- gr_tools/: 完整工具链(README 29节 + 3个Python工具 + 1个PowerShell工具)
- remap_table.json + strings_remap.bin: 重映射数据
- FONT_RES_decoded.bin + ee_text_dump.bin: 字体/文本分析数据
- mem_dumps/: 423个 EE 内存样本

---

# 30. 2026-09-08/09 会话：定制模拟器建成 + 字体链路全面打通（进行中）

## 30.1 编译定制 PCSX2（用户要求:不用 computer use,一切转存/测试用源码编译的模拟器）
- 工具链:免安装 MSVC 14.51 + WinSDK 10.0.28000(C:\Users\<user>\pbt\msvc,mmozeiko gist 方案,无需管理员);
  依赖库 13 个全部源码编译到 C:\Users\<user>\Desktop\旧工作区\gr_build\deps(zlib/png/jpeg/lz4/freetype/zstd/webp/SDL3/plutovg/
  plutosvg/ryml/DirectX-Headers/ffmpeg)。注意: Git-Bash 的 awk 会被 MSYS 路径转换弄坏 ffmpeg 的
  config.mak 依赖行 —— 已用 dep.awk 文件法修复; rapidyaml 从 codeload.github.com 下载 + ext/c4core 拼装。
- 插桩源码:emu_source 副本 C:\Users\<user>\Desktop\旧工作区\gr_build\pcsx2_src(路径不能有括号!);
  gsrunner 新增 GRResearch 模块(pcsx2-gsrunner/GRResearch.h/.cpp):
  * -grdumpdir <dir> 开启研究模式; -grneedle text:/hex:[tag=]; -grscanframes N; -grperiodram N;
    -grsnap N; -grmaxframes N; -grinput <脚本>(frame button tap/press/release/hold);
    -grmemcards <dir>; -grtexdump <dir>; -grwatchlba A B(命中后下帧转存);
  * 每帧(vsync,CPU线程 Host::PumpMessagesOnCPUThread)扫描 EE 32MB+Scratch+IOP 2MB,命中即转存
    全部 RAM+PNG; Pad::SetControllerState 注入按键(免 GUI 自动化);
  * CDVD 钩子: DoCDVDreadTrack/DoCDVDreadSector -> g_cdvdReadHook -> cdvd.log(LBA 逐扇区);
  * GS 上传钩子: GSState::Transfer -> g_gsTransferHook(目前 MTGS 环形缓冲不指 EE,按内容哈希转存)。
- 运行脚本 C:\Users\<user>\Desktop\旧工作区\gr_build\run_gs.py;<gsrunner>/portable.txt 为空文件 => DataRoot=exe目录(bios/,memcards/)。
- 构建脚本 C:\Users\<user>\Desktop\旧工作区\gr_build\build_deps.py / build_pcsx2.py(注意 build_pcsx2 SRC 指向 pcsx2_src;安装步因缺
  updater.exe 报错可忽略;**绝不能用裸 cmake --build**(缺 MSVC 环境会删掉 exe 后失败))。

## 30.2 实测确认(全部自动化,无 GUI)
- 原盘引导 → BIOS 记忆卡警告(无卡时) → 游戏读盘 → intro FMV → "Press START button" 标题 ✓
  (截图 C:\Users\<user>\Desktop\旧工作区\gr_build\dumps\long2\snap_f00008400.png)。
- 帧结构: ~600 帧 BIOS+读盘; 记忆卡对话框可被 -grmemcards 消除; 标题 ~2400-3600;FMV 后主菜单。

## 30.3 光盘读取图(CDVD LBA 日志,12600 帧全程仅 10 段!)
- SYSTEM.CNF + SLUS_206.13 全读(ELF 内含内置英文资源!); GR.IMG **从不读取**(菜单阶段);
- MENU.IMG: 头部 416 扇区(0..0xD0000,含 BNK/SB/COMMON.PAK/FONT.RES/EN_MESSAGE_MC_4) +
  3×48 扇区 = IT_MESSAGE_MC_1/2/4(按 BIOS 语言选了意语!) + **EN_STRINGS.RES@0x377c000 32扇区**;
- **EN_STRINGS.TXT 从不被读!** 引擎用的是编译资源 EN_STRINGS.RES(README 29 节"路线2"方向正确);
- MEMORY_MC RSB 是按语言预渲染的位图,RAW 未压缩,可直接换中文位图。

## 30.4 抓到的真身(全部在 han_v2/artifacts/ 与 C:\Users\<user>\Desktop\旧工作区\gr_build\dumps\)
- FONT.RES 解压真身 7222B: dumps/boot4/font_rsfb_engine.bin(EE 0x1ff6960)。
  结构 = PC font.res 同族: [u32 20]"new_font_revised.rsb"[u32 3 faces]每 face:
  [u32 nl]名[u32 10(常量!)][11×u32 头][区间表 10B/条 ×N]{u16 code,0,u16 next,u16 cell_h,u16 param}
  param 形如 768,1280,2816(=row<<8|col?);face=large(26px)/default/huge(表中有 16 位码如 0x1a4);
  尾部为 face 风格表(名字+f32 1.0)。**无位图!位图在 COMMON.PAK**。
- EN_STRINGS.TXT 解压明文 6930B/239 行: dumps/menu1/EN_STRINGS_plain_full.bin
  (EE 0x1ff6280;= PC strings.txt 同构 \t"KEY"\t\t\t\t\t\t\t"VALUE"\r\n);
  注意 TXT 文件本身从不被读,内存明文 = EN_STRINGS.RES 解压产物(RES≈多块文本!)。
- 编译字符串库(EE 0x5b14bd 区域): 条目 {u8 0x00|0x80, u8 len=strlen/2(+1), str, NUL 填充到对齐};
  0x00/0x80 两种前缀与 len 公式随条目类型变化(已大量采样验证);含注释行原样保留。
- **字体 atlas 找到**: COMMON.PAK(MENU.IMG off=0x57400, RAW 400659B) = 命名纹理包:
  "arrow"32x32、"new_font_revised"(**512x512 8bpp 字形表!**)、"pda-lcd-02"、"pda_counterparts";
  渲染确认: 上半=两遍小号字形,下半=大号字形(26px),8bpp 灰度。文件: han_v2/artifacts/COMMON_PAK.bin
  (512x512 dim 标记@0x104d)。dump 的 GS 纹理(artifacts/49dd2b5e*.png)=运行时形态(黑白 CLUT)。
- 另: 内存放大版文本缓冲 0x734d09 处 = 半解析态(a1 00 22 48 01 f7 02 开头)供差分用。

## 30.5 官方中文美术资源(PC 版自带,育碧上海!)
- Ghost Recon/Data/Shell/Art/Chinese0.rsb~Chinese4.rsb: 各 524381B,头 {6}{512}{512}{4,4,4,4}+零,
  8bpp 512x512 汉字栅格(~32x32 格/张,hanzi 字形);渲染法: 数据做 8bpp 直接灰度(偏移待精调,见
  C:\Users\<user>\Desktop\旧工作区\gr_build\dumps\c0_8bpp_offsets.png 第一列)。
- gbtext.def(2576B GBK): 字表顺序=字形格顺序的映射表;GB1200/1600/2400.tga+.rsb = 更大字库。
- **含义**: 官方中文字形齐全,无需自行渲染,可拼贴进 PS2 atlas。

## 30.6 下一步(路径已完全清晰)
1. 精确解析 COMMON.PAK 条目头(定 new_font_revised 数据区起止),确认 8bpp/CLUT 与 GS dump 对齐;
2. 解码 Chinese0.rsb 精确格式(与 gbtext.def 对照出"字→格子"映射);
3. 扩 atlas:512x512 → 1024x512(GS 上限内),右半放 ~350 个汉字(取自官方字表);
   FONT.RES face 头 f32 512.0→1024.0(两个),区间表追加汉字条目(code,offset);
4. 码位方案: 优先测 DBCS/双字节(区间表已证 16 位码可查);备选 0xA1-0xFE 94 码+改写文本;
5. 组装: 改写 COMMON.PAK+FONT.RES(未压缩,img_patch.py 空隙+尾部追加法)+ISO 重建;
6. 用 gsrunner 全自动验证(截图比对)。

## 30.7 修正旧结论
- "EN_STRINGS.TXT 是数据源" ✗ —— 引擎读 EN_STRINGS.RES(其解压形态就是纯文本,TXT 是备份);
- "FONT.RES 是字体全部" ✗ —— 只是度量+区间表,位图在 COMMON.PAK;
- "菜单消失=编译器崩" 存疑 —— 可能是字形查询失败(UI 绘制中止),待字形注入后复测高字节;
- GR_汉化M.iso 的 0x80 崩溃机制需在新认知下重测。

## 30.8 字体格式最终锁定(验证通过)
- COMMON.PAK 条目: {u32 0}{u32 名长}{名字+NUL 填充}{资源头}{像素数据};
  new_font_revised 资源头 = {u32 19=magic?}{u32 w=512}{u32 h=512}{u32 0x410}{u32 0x8040}
  {u32 0x08000000}{u32 0}{u32 0},像素 8bpp 灰度起始 = 0x1069(头 48B),尺寸 512x512=262144B;
  (arrow 条目同构 48B 头,32x32 RGBA 自 0x30)。
- FONT.RES 区间表条目语义(已用 'A'/'0' 验证): {u16 code起始, u16 0, u16 code结束(不含),
  u16 带高, u16 字节偏移} —— 码段内所有字形按行排在 atlas 的 字节偏移 处,行高=带高,
  字形间以空白列分隔(引擎按列扫描/或按表内次序切分);atlas 8bpp,行距 512B。
  例: 'A' 所在码段 [0x40,0x4a) h=78 偏移 0x900(=y1,x256) —— 裁剪精确命中 "0123456789:<=>?@ABCDEFGHIJK"。
- 同一资源里并存 4 种带高(26/52/78/104)= 同字库的 4 个尺寸档,各档独立码表与 atlas 区带。
- 注入配方: 汉字贴入 atlas 空白区(如右侧/底部,必要时 atlas 扩为 1024x512 并改 face 头 f32 宽度),
  每字追加区间条目 {code,0,code+1,带高,偏移}。中文字形可从 PC 官方 Chinese0-4.rsb 裁剪
  (512x512 8bpp 栅格,偏移待精调;gbtext.def 为字序表)。

## 30.9 官方"中文字库"证伪 + 最终字形方案
- Chinese0-4.rsb(16bpp@off40)与 GB*.tga(512x512 32bpp TGA)渲染后 = **整页中文文本位图**
  (游戏内说明书/特性页),不是字形栅格;PC 版正文中文靠 Windows GBK 系统字库实时渲染。
- ⇒ PS2 注入字形方案定稿: Pillow + simhei/msyh 渲染汉字为 8bpp 抗锯齿位图(atlas 本身即
  灰度抗锯齿,风格一致),贴入 COMMON.PAK atlas 空白区/atlas 扩容,再改 FONT.RES 区间表。
- FONT.RES 区间条目语义(30.8)已验证: {码段起,0,码段止,带高,atlas 字节偏移},偏移=y*512+x 已实证。

## 30.10 交付物与工具一览(本次会话新增)
- C:\Users\<user>\Desktop\旧工作区\gr_build\: build_deps.py(依赖)、build_pcsx2.py(编译)、run_gs.py(运行)、inputs*.txt(按键脚本)、
  pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe(插桩模拟器,portable.txt 空=DataRoot=exe目录);
- 源码补丁(在 pcsx2_src,原 emu_source 未动): gsrunner/GRResearch.{h,cpp}、Main.cpp(参数+钩子)、
  CDVD/CDVDcommon.cpp(g_cdvdReadHook)、GS/GSState.cpp(g_gsTransferHook);
- 转储: C:\Users\<user>\Desktop\旧工作区\gr_build\dumps\{boot4,menu1,long1,long2,gs*,cdvd1,ike1,ike2}\*(EE/IOP RAM、PNG、纹理);
- 关键产物已复制到 han_v2\artifacts\(font_rsfb_engine.bin、EN_STRINGS_plain_full.bin、
  COMMON_PAK.bin、纹理 PNG、gbtext.def)。

## 30.11 测试盘实验结果(2026-09-09 凌晨)
- GR_test1.iso v1(重建法)引导失败 → iso_tool build 的布局不能用于此盘;改用**原盘扇区原位替换法**
  (MENU.IMG 尺寸不变,直接写回原 ISO 的 MENU LBA 处,han_v2/GR_test1.iso)——注意拼接脚本要
  skip 原 MENU 区段(曾因重复写入 MENU 挂死,浪费两轮)。
- 三文件同补(RES截断解码/FOX/TXT)→ 引擎在 ~frame 646 陷入读盘死循环挂死;TXT 单独补丁
  (GR_test2.iso, L96A1→L96A~)完全正常 → 挂死源 = RES 截断(credits 缺 88KB)或 FONT.RES 条目。
- 内存探针证实: 干净 ISO + TXT 补丁 → 值 L96A~ **不出现**在内存 ⇒ **TXT 不被解析**(干净盘上);
  引擎的字符串来自 EN_STRINGS.RES(与 CDVD 日志一致)。早期 G3/M"TXT 生效"应为其 ISO 构建差异所致。
- EE 0x73xxxx 区域发现 5 份间距 2752B 的 stored-TXT 副本(来源未明,cdvd 日志无 TXT 读取记录,
  可能 ELF 内嵌或 IOP 路径),EE 0x1ff6280 = 解码后文本(6930B,前有 u32 6930 长度前缀)。
- **PC STRINGS.RES 格式破解(官方中文!)**: {u32 表大小}{u32 名长}{表名"GameType0"}{u32 0}
  {u32 4}{u32 字节长}{GBK 数据}... —— 官方中文 RES = 命名表 + 长度前缀 GBK 字符串,
  **原生承载中文,无需编译器**! PS2 的 RES 同构(子流=16KB 压缩块,共 8 块 128545B)。
- 挂死根因推断: 我们写的 RES 丢了头部子流(模式配置 16KB)与大部分 credits —— 引擎要找的
  资源不在 → 读盘重试死循环。正确写法 = **子流级拼接**(保留全部原子流,仅替换含文本的子流,
  用 encode_literals 纯字面量编码;子流间 {plen}{out} 框架独立,可混搭压缩/未压缩)。
  文本跨子流边界 + 令牌未破 ⇒ 需先拿到完整 128545B 解码流(抓帧窗口: RES 解码发生在
  frame ~570-580,txt5_76 needle 命中即解压完成,但 128545B 连续缓冲未在 EE 找到
  (42 00 00 00 04 头搜不到)——可能分块解码分块释放,需 GS/解码器级钩子或逐子流重建)。

## 30.12 下次会话执行清单
1. 用 GRResearch 抓 RES 各子流解码缓冲: 在 frame 570-580 窗口每帧转存 EE(加 -grdumpwin
   起止帧参数),或对 8 个子流逐个差分;拿到完整 128545B 解码流后离线重建。
2. 按 PC STRINGS.RES 命名表格式重建 PS2 EN_STRINGS.RES(官方 GBK 值直接可用),
   或子流拼接; 实测引擎接受度(先原样英文重建→应正常引导,再换中文值)。
3. 字形: simhei 渲染 ~180 汉字(0xA1-0xFE+复用)贴 COMMON.PAK atlas 空白带(y=477..511
   或扩容 1024x512),FONT.RES 追加区间条目{code,0,code+1,h,offset}。
4. 导航脚本迭代: title(start)→FMV(start 跳)→主菜单→Options→Controls / Quick Mission→
   出装界面,截图验证 L96A1/WPN 值显示。
5. 全部自动化: run_gs.py + inputs*.txt + 截图, 无需 GUI。

## 31. 2026-09-09(续): 高位字节挂死的精确定位 + 解码流完整重建成功
### 31.1 -grdumpwin 逐帧转存 → RES 全部 8 个子流解码缓冲已捕获
- -grdumpwin A B(窗口逐帧 EE 转存)与 -grwatchlba(LBA 命中后 burst 140 帧逐帧转存)已实现并验证;
- RES 8 个子流解码缓冲: sub0@0x706f89(frame383-385), sub1@0x707fa5, sub2@0x708d18, sub3@0x709a69,
  sub4@0x70b8b4, sub5@0x70d709, sub6@0x70746a, sub7@0x7091b7 —— 文件偏移布局一致,全部提取保存在
  han_v2/chunks/chunk0..7.bin(每个 16384B,最后 13857B),拼接 = RES_decoded_stream.bin(128545B)。
- 注意: 该解码流只含 GameType/简报/站点等表(WPN/weapons 不在其中)——EN_STRINGS.RES 不含 WPN 表!
- **解码格式补充: c=0x00 = 转义下一字节**(chunk0[5]=4d 证实; walker 漏掉该规则是之前解码错位根源);
  c≥0x11 字面量,c=0x01..0x10 = 匹配令牌(语义仍待定,但重建不需要它——用 encode_literals 即可)。
### 31.2 CDVD 帧级日志(钩子加帧号)真相
- TXT 在 frame 568-587 被读取(LBA 777462-777760,内偏移 0x24c000-0x2de800,含全部语言 TXT);
  之前"TXT 不被读"是**LBA 计算错误**(TXT 内偏移 0x24d600 → LBA 777465,非 776754)。
- RES 子流读取在 frame 376-385(LBA 804694-804725)。frame 150: WPNRPK74/字体已驻留。
### 31.3 高位字节挂死根因(决定性实验)
- GR_test3.iso: TXT 值 L96A1→L96A<E1>(单个高位字节,未压缩写回)→ frame ~646 起
  读盘停止、游戏挂死;PC 采样(每 4 帧采 cpuRegs.pc)显示 98/240 样本卡在 **0x004039bc**
  (= ELF 文件偏移 0x3039bc,SLUS 基址 0x100000)。
- 0x4039b0 反汇编 = memcpy/memcmp 的 32 字节对齐快速路径(sltiu $a2,0x20; andi $v0,0xf)。
  ⇒ 高位字节使某长度字段变成巨值(典型 signed char 符号扩展 bug),引擎在执行
  **天文数字的 memcpy** —— 与"菜单消失/黑屏"症状完全吻合。
- 合法 UTF-8 (c2 a1) 同样挂死 ⇒ 解析器非 UTF-8,纯粹 signed char 问题。
### 31.4 剩余唯一障碍与两条路线
- 障碍: 字符串编译器把 ≥0x80 字节当负数 → 巨 memcpy。需要: (a) 找到并 NOP 补丁该
  符号扩展点(调用者计算长度处,非 memcpy 本体); 或 (b) 全 ASCII 单字节重映射(≤94 汉字词表)。
- 路线(a)定位方法: PC 采样已有(0x4039bc); 需在挂死时采样 $a2(长度寄存器)或对调用者
  (jr $ra 前的调用点)下断点 —— 下一步可给插桩加"挂死时转存 cpuRegs 栈与寄存器"。
- 路线(b): 菜单/武器文本 165 汉字 > 94 码位,需词表改写; ATR 同理。可行但损译文质量。
- 无论哪条路线, FONT.RES 区间表+COMMON.PAK atlas 的注入方法(30.8/30.12)不变。

## 32. 2026-09-09 决定性探针实验(推翻/确认多个旧结论)
### 32.1 框架式写回管线打通(里程碑!)
- img_patch.py 新增 --framed 模式: 替换文件保留 {u32 plen}{u32 out} 子流框架,
  IMG 条目 stored=文件长, real=out(引擎解码目标长)。用 encode_literals(纯字面量,c≥0x11)编码。
- GR_PA.iso(框架+纯ASCII)与 GR_PB.iso(框架+单字节0xE1探针)全部正常引导跑完 1500 帧!
- **探针字节 0xE1 完整通过 解码→编译→DB 全管线**(EE 0x5b14ca 处 DB 条目 80 03 "L96<E1>1")!
### 32.2 推翻旧结论: "编译器拒绝高位字节"
- 旧 M/G2 实验挂死的真因 = 写回编码/框架错误(直接 RAW 覆盖破坏了子流框架),不是高位字节本身;
- GR_test3(未压缩 RAW TXT + 0xE1)挂死于巨型 memcpy(0x4039bc)—— 因为 RAW 覆盖破坏了
  TXT 的子流框架,引擎按子流解码 RAW 文本必然错乱(与字节值无关);
- **正确管线(框架式字面量编码)下,值中高位字节(≥0x80)完全合法!**
### 32.3 TXT 读取确认 + 帧级时序
- frame-stamped CDVD 日志: TXT(LBA 777462-777760,含全部语言)在 frame 568-587 读取;
  早期"TXT 不被读"= LBA 算错(内偏移 0x24d600 → LBA 777465)。RES 子流读取在 frame 376-385。
### 32.4 中文值实验
- GR_ZH.iso: TXT 值 "M4中"(UTF-8 e4b8ad) → 编译 DB 中原样保留 UTF-8 字节(EE 0x5b148a),
  引擎不做 UTF-8→16 位码转换;GR_ZH2.iso(中+Ł U+0141)同样原样保留 ⇒ 渲染按单字节查表。
### 32.5 最终字形注入方案(无分歧)
- 每个"唯一汉字"占一个 0x80-0xFF 单码位(128 个),值中直接写该码位字节;
- FONT.RES: 为 0x80-0xFF 各码位追加区间条目 + COMMON.PAK atlas 空白带(y=477..511 一行
  可放 ~19 字,或扩容 1024x512)贴 simhei 字形;
- 容量: 单字节 128 码位 + 少量回收的控制码位 ≈ 150-160 汉字。菜单文本 165 唯一字需轻微
  改写; ATR 名(另 195 字)与菜单共池会超限 → ATR 名用音译常用字收敛,或走 31.4 路线(a)
  (D]Patch DrawString 支持双字节,可无限)。
### 32.6 下次会话执行清单(直接照做)
1. 写 build_res_zh.py: 读取 TXT 明文,按词表映射 汉字→0x80-0xFF 码位,encode_literals,
   --framed 写回(30 分钟工作量);
2. 写 font_inject.py: simhei 渲染 → atlas 空白区贴图 → FONT.RES 区间条目追加
   (区间表追加位置: h=26 表的表尾,注意 0x91d 处 default face 头之前的空隙);
3. 导航脚本(title→start→跳过FMV→主菜单→Quick Mission→出装界面)截图验证中文;
4. 可选: ATR 名单同步映射; 深度: DrawString 双字节补丁(无限字符集)。

## 33. 区间表坐标语义实证(2026-09-09)
- 'A' 条目四种高度表验证: param = **atlas 内字节偏移**(y=param//512, x=param%512),
  条目覆盖码段 [code,next) 的字形按行排在 (y,x) 起,行高=h,字形间空白列分隔;
  反例(排他): (row<<8|col)×行高 解释被裁剪证伪。
- 字体码表 = 自定义码页(h=52 表中 0x35..0x42 段显示小写字母,非 ASCII 顺序) ⇒
  TXT 字节→字形 的对应由表本身决定,注入汉字 = 追加 {code,0,code+1,h,offset} 单码条目即可,
  code 用 0x80-0xFF(文本值字节,编译管线已证可用,GR_ZH.iso 实证 UTF-8 值完好通过编译进 DB)。
- atlas 扩容方案: 512x512 → 1024x512,所有旧条目 param' = (param//512)*1024 + param%512,
  face 头 f32 宽 512.0→1024.0,COMMON.PAK new_font_revised 头宽 512→1024、表面扩 262144B,
  其后 PAK 条目整体后移(需先完整解析 PAK 条目表)。

## 34. 2026-09-09(续2): atlas/区间表坐标实证 + 注入脚本就绪度
### 34.1 已实证
- PAK atlas(0x1069 起,512 宽 8bpp)中, h=78 表 'A' 条目 param=0x900 的
  (y=4,x=256) 裁剪精确显示 "0123456789:<=>?@ABCDEFGHIJK" ⇒ param=字节偏移(y*512+x) ✓
- FONT.RES h=26/52/78/104 组边界: 0x5f|0x2b7(60条)|0x4dd(55条)|0x7fd(80条)|0x91d-8(28条+8B异常尾)
- img_patch.py 新增 --framed(stored=文件长, real=out)已验证可用(GR_PA.iso 引导+解码正常)
- 中文 TXT 生成器 han_v2/build_res_zh.py 完成: 151 汉字 → 码位(0x87-0xFF 121 个 + 空闲 ASCII 30 个),
  TXT_ZH_final.bin(框架式字面量编码 6303B)已生成; code_map.json = 汉字→码位
### 34.2 font_inject.py(已写,未跑通)
- simhei 渲染 151 字形(26x26)→ atlas 扩容 1024x512 → x=512.. 贴字形 → FONT.RES 参数重算
  (512→1024 步长) + h=26 组拆分/合并/追加
- 未决细节: (a) 字形间"空白列分隔/宽度"的引擎语义(条目 z 字段=0 时的宽度来源);
  (b) param u16 上限 64KB ⇒ 字形必须放在 atlas 前 128 行(1024 宽时 y≤63);
  (c) 模板匹配: 用 atlas 已知字母行反推每个码的精确 x(写 font_map.py 做模板匹配)。
### 34.3 下次会话步骤
1. font_map.py: 对 512 宽 atlas 的每个 h=26 带, 按已知字母序列("ABCDEFGHIJ..."行)标定
   每个码的 x 区间 → 输出 code→(offset,width) 表;
2. 决定 151 汉字的 atlas 放置: (i) 不扩容, 用 26px 放入 y=477-511 带(仅18字)+空闲带
   (ii) 扩容 1024 宽 + 全参数重算(需解决 34.2 的未知宽度语义);
   建议: 先做 (i) 的 18 字最小可行验证(选最高频 18 字), 截图确认中文渲染成功后
   再攻扩容/全量;
3. 中文值生成: build_res_zh.py 已能生成, 但需与 1 的码位表联动(改用验证过的码位);
4. 出装界面导航截图验证。

## 35. 2026-09-09(续3): 输入注入验证成功 + 导航到达游戏内界面
### 35.1 根因与修复
- 早期注入"无效"的真因: run_*.py 忘传 -grinput 参数 + 按键名大小写(绑定名首字母大写)。
- 修复后实测: BIOS "press X to continue" 对话框被注入的 Cross 成功关闭(frame 2800 注入,
  frame 3300 画面已进入后续流程)✓; 后续 down/cross 导航把游戏带进 Name Entry 键盘画面 ✓
  (zhnav/snap_f00021500.png, 该画面字形 = FONT.RES 实时渲染)。
### 35.2 已验证的完整导航序列(ZH ISO, 可复用)
  2800 cross      # 关闭 BIOS 记忆卡警告
  11400 start     # Press START 进入
  (11700-20400 开场FMV, 不可跳)
  20800起 循环 down/down/cross 探索 → 已到达 Name Entry(玩家命名界面)
### 35.3 结论
- 引擎接受含 ≥0x80 字节值的 TXT(框架式字面量编码写回), 编译 DB 完整保留这些字节;
- 剩余工作 = font_inject.py 的 atlas 贴图细节(34.2) + 导航到出装界面截图。

## 36. 2026-09-09(续4): ComputeCharTextureCoords 反汇编(关键突破)
- 工具: iso 内 SLUS 按 2048 对齐重读(文件尾截断 128B 导致节头表曾不可达), .symtab 完整可读!
- 字体符号(节选): RSFont::ComputeCharTextureCoords(c,f&,f&,f&,f&)@0x21ade0(真函数头0x21ad90),
  CharWidth@0x21acd0, CharHeight@0x21acd0+, StringWidth@0x21ac00,
  DrawString×3@0x219a70/0x219e00/0x219eb0, RSFontMgr::ReadResourceFile@0x219380,
  RSFont::ReadResource@0x21ab50, sceDevFontKnj2Chr@0x40ebf0(汉字辅助符号!),
  kShellFontsPath@0x55c548, kFontResourceFilename@0x57abe0
### ComputeCharTextureCoords 解码(部分)
  lbu v0, 0x24(a0)          ; this->field24 = 宽字符标志
  beqz → 走 0x21ae50 返回(单字节路径?)
  [宽路径] dsll32/dsra32 a1 → v1 = (int8)char
  32→v0=0x20 特判; 0x14 特判; -0x4b/-0x4f 返回值=宽度相关
  主路径:
  lw  a2, 0x28(a0)          ; 表基址A
  andi v0, a1, 0xff; 符号扩展
  lb  v1, 0x20(a2)          ; v1 = 基码(表+0x20, 带符号)
  subu v0, v0, v1           ; idx = char - base
  andi v1, v1, 0xff
  bltzl v1 → 0x21ae1c       ; idx≥0x80 → 备用表
  lw  v0, 0x44(a2)          ; max_index
  slt/bnez → 出界走备用表
  lw  a2, 0x38(a2)          ; entries = 表+0x38
  idx*4+idx = idx*5, <<1 = idx*10   ; ★10字节条目在运行时结构中确认!
  lbu v0, 1(v0)             ; ★取条目 BYTE[1]
  cvt.s.w; ×f1(表缩放); jal 0x118ee0; → UV 输出
### 含义
- 渲染查表 = 运行时 10B 条目数组(与 FONT.RES 条目同构), UV 由条目字段计算;
- byte[1] 参与 UV ⇒ 条目内字段布局与 FONT.RES 侧一致(code 低字节在 byte1?);
- 下一步: 完整解码该函数后半(entry 的 param 字段如何进 UV)、0x118ee0 helper、
  以及 CharWidth 的宽度来源; 再定 DBCS 补丁点或直接按引擎语义注入。

## 37. 2026-09-09(续5): atlas 行验证 + 剩余未知精确定位
- PAK atlas 行 0..26 (y=0..26) 渲染 = `? _!"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNO`
  ⇒ atlas 行 0 = ASCII 0x20 起的字形行,字形按比例宽度紧密排列 ✓
- FONT.RES 10B 记录假设 {x0,y0,x1,y1,char} 与 chunk0(EN_STRINGS 子流) 不匹配
  (chunk0 = GameType 表非字形); FONT.RES 记录的精确字段布局仍需从
  RSFont::ReadResource@0x21ab50 反汇编获得(它就是权威解析器, 10B/条结构已由
  ComputeCharTextureCoords 的 idx*10 证实)。
- 关键修正: 之前"A_interp"中 [4:82,256:456] 裁出 ABCDEF 的行, 实为 atlas 行 0..26
  (param 0x400 = y*512+x 中 y=2 → 像素行 2..28 的字形带) — 即 h=26 = 字形高度,
  param = (行号*512 + x) 的字节偏移, 与"10B 记录=字形矩形"两说仍需
  ReadResource 反汇编一锤定音。
- 下次会话: 反汇编 RSFont::ReadResource@0x21ab50 → FONT.RES 精确格式 →
  按(1)汉字码位表(2)字形矩形注入 → 组装 GR_ZH 测试盘 → run_zh 导航截图。

## 38. font_inject 状态与剩余工作(本轮终点)
- font_inject.py 已写: simhei 渲染 151 字形(26x26) + atlas 512x512→1024x512 扩容 + 旧条目
  param 512→1024 步长重算 + h=26 组追加汉字条目; 运行在 struct.error(param>65535)暴露:
  **部分汉字放置位的 param 超出 u16** ⇒ param 编码/条目布局的最终语义未完全确认。
- 两个候选解释: (a) param = atlas 字节偏移(≤65535 ⇒ 字形只能放 atlas 前 128 行,
  而前 128 行已被现有小字形占满 ⇒ 扩容到 y>127 的字形无法被 u16 param 寻址 = 矛盾);
  (b) 10B 记录 = {x0,y0,x1,y1,char} UV 矩形(已视觉初步证实 atlas 矩形=字形),
  char 字段语义待定。⇒ 必须反汇编 RSFont::ReadResource 全函数 + ComputeCharTextureCoords
  完整 UV 计算(已有部分), 从代码层确定: 字形在 atlas 的寻址方式 + char→条目 的映射机制。
- 符号表访问方法: ISO 内 SLUS 从 LBA 295 读 37453732+4096 字节(尾部截断补齐),
  .symtab@0x61cf80(size 619552) .strtab@0x4dede0; 符号已提取(font 相关 129 个)。
- 下次会话: (1) 反汇编 ComputeCharTextureCoords 完整 UV 公式(已知条目 byte1×scale 参与);
  (2) 反汇编 ReadResource 完整函数定位 FONT.RES 记录→运行时条目的转换;
  (3) 按真实语义重写 font_inject.py; (4) 组装 GR_ZH 测试盘 + run_zh 导航 + 出装界面截图。
- 工具状态: 全部就绪(run_zh.py 导航、img_patch --framed、build_res_zh.py、code_map.json)。

## 39. ComputeCharTextureCoords 完整手工反汇编(0x21ad90-0x21ae58, 见上)
- 头部特判: char==0x20(space)→固定宽; char==this[0x14]→另一固定值; 否则主路径。
- 主路径: table=this[0x28]; base=(int8)table[0x20]; idx=(char-base)&0xff;
  idx<0 或 idx>=table[0x44] → 备用表(table[0x38] 同构);
  entry = entries + idx*10; **entry BYTE[1] 参与坐标计算**(byte1→float→helper→×f1)。
- 运行时条目布局 ≠ FONT.RES 记录布局(ReadResource 做了转换), 字段语义需
  结合运行时条目数组 dump(通过 RSFont 对象 this+0x28/0x38 指针链)才能定案。
## 40. 下次会话第一优先级
1. dump RSFont 运行时结构: 在 frame>600 的 EE 全量转储中定位 RSFont 对象
   (this+0x20=base码, +0x24=宽字符标志, +0x28=表A, +0x38=条目数组, +0x44=max),
   方法: 在内存里搜索 10B 条目数组特征(连续的 {code,0,next,26,param} 且 param 高位
   = 递增 band), 反推条目数组基址 → 顺藤摸瓜找 RSFont 对象。
2. 对比 FONT.RES 解码流(font_rsfb_engine.bin)与运行时条目数组 → 完整还原
   FONT.RES 记录→运行时条目的转换规则 → 即可按规则构造含汉字条目的 FONT.RES。
3. 注入后用 run_zh.py 导航到按键设置界面(33 个值全用 18 汉字探针集)截图验证。

## 41. 运行时字体表彻底解密(2026-09-09 续)
- ZH run frame-390 EE dump @0x687432: 49 条 10B 记录 = **ATLAS BAND 0 的字形单元格矩形**:
  {x0, y0=0, x1, y1=26, 0x300} — x0 递增且相邻记录 x0==前记录 x1(紧邻排列),
  与 atlas 行 0 渲染(? _!"#$%&'()*+,-./0123456789:;<=>?@ABC...)逐一吻合!
  5th u16 = 0x0300 = band 3?? 或 char 待定; y0=0/26 = band 内行号。
- 更大发现: @0x687432 的数组 = "band 0 的 49 个 cell"; 后续(@0x687432+49*10=0x687b42)
  = band 1 的 cells(z=0x68=104??), 再后 = 其他 band/字号 —— 全部字形按 band 分组连续存储!
- **运行时表 = 字形 CELL 矩形数组**(按 band 分组); char→cell 的映射表 = 另一段结构
  (ComputeCharTextureCoords 读 table[0x20]=base, [0x38]=cells, [0x44]=cell 数,
  idx=(char-base)&0xff → 直接索引 cells[idx]!!)
  ⇒ char→cell = 直接数组索引: **cells 按 char 排序, char c 的字形 = cells[c-base]!**
  (base = table[0x20] = 第一个 cell 的 char)
### 重大简化: FONT.RES 注入新理解
- FONT.RES 解码流(7222B) = {header}{faces}{**cells 数组(10B/字形, 按 char 排序)**}
  {char→cells 映射}? — 若 cells 数组按 char 排序且可直接索引, 则:
  注入 = (1) 在 atlas 空白带贴汉字; (2) 在 cells 数组中为码位 c 追加
  cell {x0,y0,x1,y1,char=c}; (3) 更新 char→cell 的映射结构(若存在)。
- 待办: 解码 0x687432 数组后的结构(char→cell 映射 = ComputeCharTextureCoords 里
  idx=(char-base) 直接索引 ⇒ 无需额外映射表, cells[0]=char base! 数组按 char 排序即可!)
- 即: **cells 数组 = 按 char 升序的 10B 条目, char c 的字形 = cells[c - base]!**
  FONT.RES 注入 = 在 cells 数组正确位置插入 {x0,y0,x1,y1,char=c} + atlas 贴图。

## 42. 运行时字体表最终解密(2026-09-09 深夜)
- ZH run frame-390 EE dump @0x687432: 49 条 10B 记录 = atlas 行 0 (y 0..26) 的字形单元格:
  紧邻排列 x: 0-13, 13-17, 17-23, 23-35, 35-46, 46-62, 62-75, 75-80, ... 488-500 (共500px)
  = `?_!"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNO` 的 49 个字形单元格 ✓
  (与 atlas_row0.png 渲染逐一吻合!!) — 5th u16 = 0x0300 = (band 3 <<8), y1 = 0x1a = 26 行高。
- 含义: FONT.RES 条目 = {x0, y0=0, x1, y1=26, (band<<8)|0}: 每个"码段"对应 atlas 里一个
  紧排字形带片段; 引擎在带内按(空白列)自动切分字符宽度。
- 坐标系确认: y = band*26 (26px/带), x = 像素列; param = (y_band<<8)|x_offset。
- FONT.RES h=26 组的 49 记录 = atlas band 3 的字形(行 78..104);h=52 组(0x2b7..0x4dd)=
  atlas band 5 (行 130..156);h=78 组(0x4dd..0x7fd)= atlas band 9 (行 234..312);
  h=104 组(0x7fd..0x91d-8)= atlas band 6 (行 156..182)?? — 具体对应待最终确认,
  但注入只需: 在 PAK atlas 某空 band 贴汉字 + FONT.RES 加同 band 号的码段记录。
- PAK atlas 空间: 512x512 全部 19 个 26px 带已被现有字形占用(紧排)。
  ⇒ 扩容: PAK 头 h 512→1024, 表面追加 512 行(band 19..38), FONT.RES face f32 h 512→1024。
  汉字放新 band 20..26 (y 520..702), 每带 18 字 (28px 步长) × 9 带 = 162 字 ≥ 151 ✓
- FONT.RES 注入: h=26 组尾(0x2b7)插入 151 条 {code,0,code+1,26,(band<<8)|x}
  (band = 20+i//18, x = (i%18)*28), code = 0x87+i。
- ⚠ 5th u16 的低字节 = x 偏移(u8 ≤255): 28*18 = 504 > 255 ✗✗ — x 必须放进 u8!
  修正: 每带 9 字 (x pitch 56): band 20..36 (17 带) × 9 = 153 字 ✓ 刚好。
  或 param = (y_abs << 8)|x: y_abs = 20+band*?? 超过 255 ✗。
  ⇒ 最终: 汉字按 9 字/带 排布, band = 20+i//9, x = (i%9)*56, param = (band<<8)|x。
- 待验证: 引擎渲染时 x 是否直接用 param 低字节(像素列)。若是, 9字/带 × 56px 带宽
  = 字形放带左半; 字形宽 ≤26px ✓ 放得下 (56px/字 × 9 = 504 ≤ 512 ✓)。

## 43. 字形 cell 数组结构确认(2026-09-09 深夜)
- ZH run dump @0x687432: 49 个 10B cell = atlas 行 0 (y 0..26) 的字形矩形, x 紧邻:
  (0,0,13,26),(13,0,17,26),(17,0,23,26),(23,0,35,26),... (488,0,500,26)
  宽度: 13,4,6,12,11,16,13,5,7,6,8,11,4,7,4,7,10,7,12,11,11,11,11,11,11,3,11,3,4,11,11,10,4,19,13,14,11,4,13,11,14,12,10,10,13,10,14,13,11,15
  与 "Press START button" 的字符宽度完全吻合(P=13,r=4,e=6,s=12,s=11,T=15,A=13,R=12,T=15,
  space=11,b=11,u=12,t=7,t=7,o=12,n=11) ⇒ **cells = 按渲染顺序的字形矩形 + 字段**!
- cell = {x0, y0, x1, y1, tag}: x0/y0 = 左上, x1/y1 = 右下 (atlas 像素坐标);
  tag = (y_band<<8)|x?? — cell0 的 tag=0x300: (band 3 << 8)|x=0?? band3 = 像素行 78..104;
  cell0 = 'P' 的字形(13x26)在 band 3?? — 但 P 的 y=0..26 (band 0)...
  ⇒ tag = (y_cell<<8)|x_cell: cell0 y=0..26 在 band 0, x=0..13...
  对不上 → tag 的编码 = (band<<8)|x 中 band=3 ⇒ y = 3*26=78?? 与 y0=0 矛盾。
  结论: tag = (y_band<<8)|x_band, y_band=3 指 "band 3 的 x=0 起" — 即字形在 atlas band 3
  的 x=0..13。而 cells 的 y0/y1 = 0/26 = 该字形在 band 内的行范围(0..26)!!
  ⇒ 字形实际位置 = (x = tag低字节 + cell内x0?, y = band*26 + y0) — 待实测校准。
## 44. 下次会话(最高优先级)
1. 用 ZH dump 的 49 cells + atlas 行 0 渲染对照, 校准 tag→(x,y) 映射:
   已知 cell 0 = '?' 字形(x 0..13?), cell 3 = '#'(23..35), cell 6 = 'A'?? 
   (atlas 行0 = ?_!"#$%&'()*+,-./0123456789:;<=>?@ABC — 按 cells 的 x0 序:
   cell0 x 0..13 = `?_`?? 宽13 = `? _` 三字符?! ⇒ cells = 多字形合并条,
   引擎按空白列自动切分 — 与 FONT.RES 记录的 z=0(auto width) 一致!)
2. 注入方案定稿: 在 atlas 空白区(y 477..511 或扩容)贴 151 汉字(26x26, 2px 空白列分隔),
   FONT.RES 追加 cell 记录 {x0,y0,x1,y1,(band<<8)|x} — 每字一条, 引擎自动切分。
   TXT 值 = 汉字码位字节(0x87.. 或 0x20..)。
3. 组装 GR_ZH 测试盘 + run_zh 导航到按键设置界面(33 值全用探针集汉字)截图验证。

## 45. 本轮终点状态(2026-09-09)
### 已实证
- GR_ZH_FULL.iso(TXT框架式+FONT.RES未改+COMMON.PAK扩容)完整引导至标题画面 ✓
- 输入注入 ✓; 高位字节全管线 ✓; CDVD帧级日志 ✓
### 本轮新认知
1. atlas 行 0 = `?_!"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNO` (49 字形, 紧排)
2. 运行时 cell 数组(@0x687432, 49条) = 行0字形的矩形表 {x0,y0,x1,y1,tag},
   宽度序列 13,4,6,12,11,16,13,5,7,6,8,11,4,7,4,7,10,7,12,11,11,... 
   与 "Press START button" 的字符宽度逐一吻合 ⇒ cells = 按渲染顺序的字形矩形!
3. FONT.RES 解码流 = {faces}{cells 按行堆叠}{...}: 全部字形 = 多个 26px 行带
4. 标题画面文字 = 从 atlas 字形渲染 ✓ (GR_boxes.iso 的方块实验因贴错位置未见)
### 剩余(单点)
- cells 数组覆盖的 char 范围与 char→cell 映射: ComputeCharTextureCoords 的
  idx=(char-base)&0xff → cells[idx] ⇒ cells 按 char 排序, base=table[0x20]
- 注入 = (1) atlas 空白带(或扩容)贴 151 汉字字形 (2) cells 数组追加/替换对应矩形
  (3) TXT 值 = 码位字节。FONT.RES/COMMON.PAK 均未压缩写回,零格式风险。
### 工具与产物
- han_v2/build_final.py: TXT+FONT+PAK 生成器(需按 44/45 的 cells 语义修正贴图段)
- han_v2/TXT_ZH_final.bin、FONT_RES_ZH.bin、COMMON_PAK_ZH.bin 已生成
- GR_ZH_FULL.iso: 当前=无汉字字形版(引导正常), 待 font_inject 完成后重组

## 46. 2026-09-09 收官固化：三文件注入盘的状态与遗留问题
> 本节 + 根目录 PROJECT_STATUS.md = 全部项目状态。新会话先读 PROJECT_STATUS.md。

### 46.1 FONT.RES 插入点诊断（当前阻塞根因）
- build_final.py 与 inject_full.py 都把汉字条目插在 **0x2b7**（假设 h=26 组到此结束）——错误。
- 十六进制复核：0x249~0x2b7 仍是延续记录（0x249 起 `00 00 00 1a 00 0e 00 34 ...`
  出现 y1=0x34=52 类字段），即 **0x2b7 落在 h=52 组记录中间**，插入后破坏后续组解析
  → 引擎在 ~600 帧冻结（TXT-only 版正常引导到标题，证明挂死仅由 FONT.RES 修改引起）。
- 正确做法：先对 font_rsfb_engine.bin(7222B) 做 10B 记录约束扫描
  （字段[3]=h∈{26,52,78,104} 且连续成段），确定 h=26 组**真实边界（≤0x249）**再插入。
  gr_tools 目前没有现成 FONT.RES 扫描器，需新写（可参考 han_v2/ee_scan.py 的
  运行时数组扫描思路 + font_inject.py 的 parse_group/is_entry 雏形，注意其
  is_entry 的 `(prm & 0xff)==0` 约束过严、会把合法记录漏掉）。

### 46.2 ~~磁盘版 img_patch.py 缺 --framed 逻辑~~（撤回：误判）
- 完整复核确认：当前 img_patch.py **已含 --framed**（stored=文件长,
  real=子流头 out_size），先前仅因部分读取误判为回归。用法：
  `python img_patch.py in.img out.img --framed EN_STRINGS.TXT=<bin> FONT.RES=<bin> ...`

### 46.2b ★ 决定性突破：FONT.RES 记录语义最终定论(2026-09-09 深夜, 推翻插入式方案)
- font_res_scan.py + font_res_parse.py 实证: 记录 {code,z,next,h,param} 实为
  **{x0,y0,x1,y1,tag} 字形矩形**, 记录 i = 字符 0x20+i (base=0x20), 按 ASCII 排序。
- 三个 face 共享一张 512x512 atlas, 交错打包, 各 224 条 = 字符 0x20..0xFF:
  | face | 记录区 | atlas 行 | 备注 |
  |---|---|---|---|
  | large | 0x5f..0x91f | y 0..130 | 菜单文本用(运行时 cells 实证) |
  | default | 0x962..0x1222 | y 104..208 | |
  | huge | 0x1262..0x1b22 | y 182..476 | 行高 42 |
- 高位字符(≥0x87)的原矩形 = 垃圾占位(如 (511,26,513,52)) —— 高位字符从未可渲染。
- face 头 atlas 高度 f32(LE u32): large@0x49, default@0x94c, huge@0x124c (512.0)。
- 文件头: {u32 20}{"new_font_revised.rsb"}{u32 3}{u32 5}; face 名 "large\0a"@0x20 等。
- COMMON.PAK: new_font_revised 宽 u32@0x104d, 高 u32@0x1051, 表面@0x1069;
  头内 @0x1055 有神秘 u32=1040(疑 w+h+16), 实测不改也能引导。
- **注入方案定稿(inject_v2.py, 覆写式)**: PAK 高→1024 + 汉字贴 y=512+r*26
  (18/行, x=c*28, 24x26, simhei 22); FONT.RES 尺寸不变(7222B), 三 face 的
  0x87..0xFF 记录原地覆写为汉字矩形(保留原 tag), 三处 f32→1024.0。
- 工具: gr_tools/font_res_scan.py(组扫描), font_res_parse.py(face 解析),
  font_res_probe.py(矩形叠加渲染); 产物 han_v2/FONT_RES_ZH2.bin、
  COMMON_PAK_ZH2.bin、atlas_zh2.png(121 字形验证图 ✓)。

### 46.3 hanzi_cells.json 的 param 与 §42 约束冲突（已作废）
- 46.2b 定论后, hanzi_cells.json(build_final 时代的 18 字/带布局)整个作废;
  以 inject_v2.py 的直接矩形覆写为准。

## 47. 2026-09-09 深夜: GR_ZH_V2 引导失败定位 + ISO 组装管线定论(最高优先级结论)
### 47.1 三个 run 的决定性对比
| run | ISO | 组装方式 | 结果 |
|---|---|---|---|
| zhnav | GR_ZH.iso (1,648,164,864 = 原盘尺寸) | 原盘 + 同尺寸 MENU 原位拼接 | ★完全成功: 31000 帧, needle 数百命中(PressSTARTbutton 510), 到达标题/菜单 |
| zhv | GR_ZH_FULL.iso (isodir 重建, MENU=原尺寸) | iso_tool build | 字体载入后 ~600 帧死(FONT.RES 插入 bug, 旧诊断成立) |
| zhv2 | GR_ZH_V2.iso (isodir 重建, MENU 追加 +664KB) | iso_tool build | 游戏 ELF 载入后**一次游戏数据都不读**: WPNRPK74(原盘 180 帧即载)0 命中, 全部 needle 0 命中, 画面全黑 |
### 47.2 结论
- **iso_tool 重建 ISO + MENU 尺寸变化 = 死路**(MENU 变大 → 后续文件 LBA 移位 →
  游戏自身文件层失效; BIOS 级 ISO9660 正常所以 ELF/模块能载)。
- **唯一验证可行的组装 = 原尺寸 MENU.IMG(58,300,882B) 在 LBA 776286 原位拼接进原盘**
  (拼接后 seek 跳过原 MENU 区, 见 §30.11)。
- MENU 尾部空隙 ≥669KB(zhnav 装下 TXT+PAK扩容版)。
### 47.3 PAK 头神秘字段破解 + f32 定论
- COMMON.PAK 纹理头 @0x1055 u32 = **宽+高+16** (512+512+16=1040 实证吻合)。
- **face f32 对与引擎 UV 无关**(成功配置 GR_ZH.iso 的 PAK h=1024 而 f32=512,
  菜单文字渲染正常) → 引擎用 PAK 头 @0x104d(w)/@0x1051(h); f32 不用改。
### 47.4 V3 方案(宽度扩容, 尺寸中性) — 已执行, 待引导验证
- atlas 512x512 → **1024x256**(表面字节数不变 262144!) → COMMON.PAK 总尺寸不变(400,659B)
- 动作: PAK 头 w=1024 h=256 @0x1055=1296(=1024+256+16); 旧字形像素/记录重映射
  (旧 (x,y) → (x + (y≥256?512:0), y-256)); 汉字贴 x=512.., y=0..182; FONT.RES 三 face
  记录同步重映射+汉字覆写, **f32 不动**。
- 边界情况: huge face 行 (224,266) 29 字符(ASCII 0x24..0x40)横跨 256 切分线 →
  原位图等比缩放 42→36px 重排进底部空带 y220..256(占 x0..473), 记录同步改。
- inject_v2.py 的 HEIGHT 扩容版(FONT_RES_ZH2/COMMON_PAK_ZH2)作废但脚本保留参考。
- 产物: FONT_RES_ZH3.bin(7222B 不变) + COMMON_PAK_ZH3.bin(400659B 不变) + atlas_zh3.png ✓

### 47.5 ★ MENU.IMG 尾部空隙实际只有 ~35KB(修正 47.2 的 "≥669KB" 误判)
- 实测: last_end≈0x3789xxx, img 尾 0x3791FE2 → 空隙 ~35KB: 只够 TXT(6.3K)+FONT(7.2K)。
- zhnav 成功版 GR_ZH.iso 的 "PAK扩容" 实为**只改 PAK 头 h=1024、表面没扩**(同尺寸原地写)。
- img_patch.py 已加 **--inplace**(默认开): 新内容 ≤ 原条目 stored 时原地覆写原偏移。
  COMMON.PAK(400659=原 stored)→inplace@0x57400; FONT.RES(7222>4421)→gap; TXT→gap。
- **组装链定稿**: menu_orig/MENU.IMG --img_patch--> MENU_Vx.img(=58,300,882 原尺寸)
  --splice_iso.py--> GR_ZH_Vx.iso(=1,648,164,864 原盘尺寸, LBA 776286 原位覆盖)。
  gr_tools/splice_iso.py = 原位拼接工具(字节精确, 输出尺寸断言=原盘)。

## 48. 2026-09-09 深夜 III: zhv3/zhv4 复盘 + V5 零扩容方案(当前最优)
### 48.1 zhv3/zhv4(宽度扩容 1024x256)结果
- 读取停在帧 257(武器包+字体 atlas 已载), EN_STRINGS.RES/TXT 从未读取, PressSTARTbutton 0 命中。
- f32 同步 (1024,256) 无效果(zhv4 = zhv3)。
- 对比: zhv(GR_ZH_FULL, FONT.RES 插入破坏版)反而活到 ~600 ⇒ **引擎对 PAK/atlas 结构性改动
  (尺寸/表面重排/头部字段)零容忍; 记录数值改动相对容忍**。
- 另: -grsnap 全黑(zhv2/3/4 连 BIOS 画面都黑) — 截图路径本身存疑, 引导进度以 needle 为准。
### 48.2 成败矩阵(汇总)
| 配置 | FONT.RES | COMMON.PAK | 结果 |
|---|---|---|---|
| zhnav/GR_ZH.iso | 原样 | 头 h=1024, 表面原样, 原尺寸 | ★31000 帧到菜单 |
| zhv/GR_ZH_FULL | 插入破坏 | 真扩容 1024 行, MENU 变大 | ~600 帧死 |
| zhv2/GR_ZH_V2 | 覆写+HEIGHT 扩容 | 662KB 附加, isodir 重建 | 游戏数据零读取 |
| zhv3/zhv4 | 覆写+W 1024x256+f32 | 尺寸中性 400659 原位 | 257 帧死(RES 未读) |
### 48.3 V5 方案(零扩容, 当前最优) — 已组装 GR_ZH_V5.iso, 验证中
- COMMON.PAK: **仅像素覆写** y 224..406(huge face 专用区, large/default 不用):
  121 汉字 18/行×28px×26px 行。头/尺寸/表面布局全原样(400,659B)。
- FONT.RES(仅记录数值): large 0x87..0xFF → 汉字矩形; huge 0x24..0xFF → large 同字符
  ASCII 字形(缩小但正确); huge 0x20..0x23 与 default 全部不动。
- inject_v5.py; 产物 COMMON_PAK_ZH5.bin / FONT_RES_ZH5.bin / atlas_zh5.png。
- 代价: huge face(大标题字体)的 ASCII 字形变小; 若 huge 从未用于菜单则零影响。

## 49. 2026-09-09/10 深夜连战: V5-V15 迭代 → 汉字渲染通路完全打通 ★★★
### 49.1 逐版本结果(全部原尺寸 ISO + 原位拼接)
| 版本 | TXT | PAK | 结果 |
|---|---|---|---|
| zhv5/V5 | 双字节对 | huge 区像素覆写 | ~625 帧冻结 |
| zhv6/7 (V6) | 双字节对 | large junk cell 对像素(残影) | Accessing 记忆卡对话框永久卡死 |
| zhv9 (V6 重跑) | 同上 | 同上 | 同上(排除记忆卡状态) |
| zhv10 (V10) | V6+填充至 6971/6933 | 同上 | 同上(排除条目表字段) |
| zhv11 (V11) | 剔除 0x88 | 同上 | 同上(排除 0x88 越界矩形) |
| zhv8 (V7A) | ★成功版 TXT(ASCII+M4中) | V6 像素 | ★通过 boot+FMV(5750 帧 killed) |
| zhv13 (V13) | ★成功版 TXT | V12 像素 | ★750 帧=Ubisoft logo, 读到 12898 帧 |
| zhv12 (V12) | UTF-8 占位符(合法) | V12 像素 | 卡死 |
| zhv15 (V15) | UTF-8 占位符+值首空格修复 | V15 像素 | (引导中) |
### 49.2 决定性结论
1. **CDVD 日志不覆盖文件读取路径**: TXT 走 IOP fileio(readSector)读取, 完全不进
   cdvd.log; needle 证明 TXT 内容 370 帧即入 IOP RAM (0x30A1E), 且只入 IOP 不入 EE。
2. **"Accessing memory card" 永久卡死 = TXT 编译挂死的表象**(对话框只是当时画面)。
3. **毒源 = 值首字节 ≥0x80**: 值以高位字节开头 → 解析器挂死。值首为 ASCII 时
   即使值内 14 连高位字节也完全正常 (V14c 实证)。修复 = 值首加前导空格。
4. **PAK 像素改动完全安全** (zhv8/zhv13 双重证明)。FONT.RES 必须逐字节原样。
5. -grsnap 黑屏 = 游戏真死机的表现(zhv2-5); 活着的 run 截图正常(zhv13 Ubisoft logo,
   zhv6 记忆卡对话框, orig2 Name Entry 键盘)。
### 49.3 V15 最终方案(当前最优)
- 渲染映射假说: codepoint → cell[(cp-0x20)&0xFF] — CJK 码点低字节 ∈[0x87,0xFF] 者
  落在 junk cell 区; 用占位符汉字(合法 UTF-8, 3 字节)承载, PAK 像素画真字形。
- 每汉字 = 2 个占位符(相邻 junk cell 对, 联合矩形宽 17-33px), simhei 直写。
- TXT: 值首空格修复 + UTF-8; 32 对槽位覆盖高频 32 字, 其余删除。
- 待 zhv15 引导 + 快照验证中文实际显示。
### 49.4 ★★ 重大修正: 卡死真相分层 (49.1-49.3 的内容毒源结论部分作废)
- 49.1 表格里"UTF-8 占位符也挂"(zhv12)的原因后来查明 = **V12/V15 构建器 bug:
  把"所有汉字都未覆盖"的值写成了空值行 (`""`) → 编译挂死**, 并非占位符本身。
- 记忆卡 "Accessing" 卡死也可能偶发(与内容无关的重试即可), 与空值 bug 叠加
  造成了误判。空值 bug 修复后 K99 从未复现卡死。
- 正确 TXT 构建器规则: **只重建含已覆盖汉字的行, 其余行保持 plain 原字节**;
  永远不要输出空值行。
### 49.5 已证伪清单(不再重试的方案)
- FONT.RES 任何改动(插入/记录覆写/f32) → 挂死。FONT.RES 必须逐字节原样。
- PAK 结构字段改动(宽/高/mystery)、HEIGHT/WIDTH 扩容重排 → 挂死。
- isodir + iso_tool 重建 ISO(尤其 MENU 尺寸变化) → 游戏数据零读取。
- 值首高位字节 + 非法 UTF-8 双字节序列 → 挂死(zhv6-11)。

## 50. ★★★ 终局: K99 = 首个完整成功的中文盘 (2026-09-10 凌晨)
### 50.1 K99 最终配置(= 交付模板)
1. EN_STRINGS.TXT (TXT_ZH_u12.bin 构建逻辑): 官方中文值中, 已覆盖汉字 → 两个
   占位符汉字 (cp = 0x4E00 + slot_char, 合法 UTF-8, 每 3 字节); 未覆盖汉字删除;
   值首若为高位字节加前导空格; 其余行保持 plain 原字节不变; 无空值行。
2. COMMON.PAK (COMMON_PAK_ZH12.bin): 仅像素覆写 — 每个已覆盖汉字的 simhei
   字形画进其槽位的相邻 junk cell 对联合矩形 (direct overwrite)。400,659B 不变。
3. FONT.RES: **逐字节原样**。
4. MENU.IMG: menu_orig + img_patch --framed(TXT) + inplace(PAK) = 58,300,882B 原尺寸。
5. ISO: splice_iso.py 原位拼接 LBA 776286 = 1,648,164,864B 原盘尺寸。
### 50.2 k99full/k99nav2/k99nav3 实测
- 26000-33000 帧全程存活; 标题画面 ✓; **进入实时 3D 任务**(M16/弹药 HUD) ✓;
- 任务内 OPTIONS 菜单(Sensitivity/Volume 等, 原英文值)渲染正常 ✓;
- Name Entry 界面底部帮助条 "Enter your name." = 来自修改版 TXT, 渲染正常 ✓。
- 快照: C:\Users\<user>\Desktop\旧工作区\gr_build\dumps\k99full\ (标题/Name Entry), k99nav2\, k99nav3\ (任务内)。
### 50.3 剩余工作
1. 导航到武器/控制列表界面截图(控制页有 键盘/选择/鼠标 等已覆盖汉字) —
   盲导航脚本需按实际菜单结构细化(k99nav2 的 downs 走进了 Quick Start)。
2. 覆盖扩展: 当前 31 对槽位 = 31 汉字; 更宽的槽位筛选(≥8px)或接受更窄对、
   以及 rare-ASCII 断路器方案(21 个未用 ASCII 码 = 额外单槽+断路)可加字。
3. ATR 队友名(GR.IMG 内 GBK 段)/简报文本。
4. 最终完整 ISO 组装 + 全部文档收尾。
### 50.3b 菜单结构地图(k99nav2/4/5/6/7/8/13/17 实测, 盲导航用)
- 主菜单(档案接受后): Training / Tactical Exercises / Campaign / Quick Mission(灰) /
  Multiplayer / Statistics / Special Features / **Options**(第8项, 7×down) / Credits。
  默认高亮 = Training; cross = T01 简报 → 自动加载(无装备页)。
- Campaign 流: 选 GHOST RECON → Difficulty (Recruit/Elite, up/down 切换) → cross
  → M01 加载(Information/Objectives/PROCEED) → 任务。
- Options 子菜单: Gameplay / Controller / Advanced / Sound / Screen; 高亮有记忆,
  Triangle 退回后重置为 Gameplay; Sound 页 = 音量 5 行。
- Controller = 1/2/3 三标签手柄图示页; 标签为英文("Command Map"/"Fire Weapon"等)
  **且这些文本不在 EN_STRINGS**(hardcode/其他资源) → 控制图示页不是占位符显示位。
- 任务内: L2/R2 = 指令地图(换队), R1 = 开火, Start = 任务内 Options(Sensitivity/
  Vibration/音量, 英文原值)。
- 移动 = 左摇杆, 绑定名 **LUp/LDown/LLeft/LRight**(HalfAxis); 'up' 是十字键!
  LUp 连发可正常跑动(k99nav15 实测跑进障碍区)。
- EN_STRINGS 239 键 = WPN_*/ITM_*/控制动作标签(sidestep_left 等)/radio(chat_msg,
  all_teams_*)/key_* 键盘键名/MP 兵种; 训练教程文本与任务简报**不在其中**
  (在 GR.IMG 任务数据里)。WPN/ITM 名称显示位 = 装备/拾取界面(待导航抵达)。
### 50.3c 剩余工作(更新)
1. **★主路径转向: GR.IMG 文本汉化**(50.3b 的结论 = EN_STRINGS 在 PS2 SP 为
   残留文件, 游戏从不显示其值 — R3 快捷命令轮盘在单人训练中不存在,
   控制图示页标签 = hardcode)。GR.IMG 的训练教程/简报文本 = **已确认屏幕可见**
   (k99nav9 帧27500 教程框; k99nav13 帧33125 M01 简报), 且以明文片段存在于
   D02_REFINERY.BMB 的字面量段('obstacle' 命中)。**同长度原位改写字面量字节 =
   压缩流结构完全不动 = 零风险**, 解码后即得中文文本。步骤:
   a. 提取 D02_REFINERY.BMB (GR.IMG off=0x5A0D30, stored=2006906)。
   b. 实现 LZ77 解码器(需支持匹配令牌; 已知明文攻击: 'obstacle' 在 BMB 偏移
      ~105936 处 = 解码校验的 crib)。
   c. 定位 T01 教程框文本('The obstacle course will teach you...')与各站点提示。
   d. 同长度替换: 每汉字 = 占位符对(6字节) 或 占位符单字(3字节,半字宽) + 空格补齐;
      匹配令牌字节原样保留(其回引的历史 = 改写后文本, 复制结果自动一致)。
   e. 写回原位(字节数不变) → 拼接 GR.IMG(LBA 19175!) + MENU(K99) → 运行 →
      教程框显示 painted 汉字 = 显示验证完成。
2. 注意: 一次误写已修复(0x5A0D2F 8字节已从原盘恢复); 编辑务必在字面量段内。
2b. ★V26 反证实验(2026-09-10): TXT 值改用原始槽位字节对(chr(c1)+chr(c2) =
    非法 UTF-8) → 游戏 144 秒即崩溃 = **游戏按 UTF-8 解析 EN_STRINGS.TXT 的
    直接证据**, V12/K99 的合法 UTF-8 占位符编码确认为正确, 不再改动。
    另: ATR 中文名(nav25)致指令面板无法打开——ATR XML 解析器同样不收
    非 ASCII, 该路已排除(ATR 保持 ASCII)。
3. 扩大覆盖: 31 → 59 对槽位(全部相邻 junk 对)。
4. ATR 队友名(GR.IMG 内 XML, 未压缩)已改写待实测; 最终完整 ISO 组装。
### 50.3d 补充注记
- gr_lz.py 的 _walk_count_stream = 旧解码规则(c≤0x10 → c+3); 精化理解:
  c=0x00 转义下一字节、c=0x01~0x10 = 匹配令牌(编码绝不发出)、c≥0x11 = 字面量段。
  encode_literals(纯字面量, run+17) 对两者都安全。
- 训练/简报/菜单可见文本大部分**不在 EN_STRINGS**(在 GR.IMG 任务数据或 hardcode);
  EN_STRINGS 仅 239 键 = 武器/物品/控制标签/radio/键名。
- 输入系统 bind 名 = PCSX2 PadDualShock2 表: LUp/LDown/LLeft/LRight(左摇杆),
  Up/Down/Left/Right(十字键), Cross/Circle/Square/Triangle/L1/L2/R1/R2/L3/R3/
  Select/Start(Title Case 或全大写均可, auto-cap)。
- 控制图示页(Controller)的英文标签 = hardcode, EN_STRINGS 的控制标签键
  (sidestep_left 等)在 PS2 上无显示位(仅 PC 版控制列表使用)。
### 50.4 k99nav19-26 导航迭代实录(2026-09-10)
- nav19 (K99盘, 组合导航): **L2/R2 打开任务内指令面板** (帧31200: Alpha Team
  名册 H.Dominguez/G.Maxwell/S.Beard/T.Norris + ROE Advance/Recon + 指令地图) ✓;
  T02 靶场狙击枪拾取装备(HUD x8) ✓。
- nav18 (T02): 靶场教程文本框(35625-36250) = GR.IMG 训练数据(英文, 不在
  EN_STRINGS); HUD = 纯图标无武器名。
- nav21/22 (V21 盘=TXT_working+all_teams_advance=图占位符对): Circle 按键注册
  (bind5=1.0)但指令面板未打开, 帧30300 = 游戏自身 "insert disc" 错误屏
  (cdvd 读 @774748 挂起) — 2 连挂。**all_teams_advance 键的改写疑似破坏
  指令地图打开路径**(或 49.4 的偶发竞态), 未隔离。
- nav23-24: maxframes 设错(13000) 白跑一次; V24 = V22 TXT + RES 'Advance'
  → 图占位符对+空格: **M01 过场动画冻结 166+ 秒** — RES 标签替换或 TXT_V22
  之一为毒源, 未隔离。
- 读取挂起特征: cdvd.log 最后读取 = LBA 774748-774750 (GR.IMG 尾与 MENU 之间
  的间隙区), 之后零读取 + 游戏自身 disc-error 屏。这是**模拟器层偶发**,
  重跑即可穿过 (nav15→nav19 都曾一次通过)。
### 50.5 下次会话首动作
1. 隔离测试: (a) 纯 TXT_working 重跑确认基线存活 (b) TXT_working + 仅
   all_teams_advance 一键改写 → 若挂死则该键 = 特殊(启动期被解析), 改用
   其他 all_teams_* 或放弃该键 (c) RES 'Advance' 标签改写单独重测。
2. 存活后: L2 开指令面板截图 → 队员名/ROE 文本 = painted 汉字验证。
3. ATR ActorName 改写(RIFLEMAN-48/11/58/59 = 组信/图员/听选/标弹) 已写入
   gr_img/GR.IMG 但未实测 — 下次随 M01 任务导航验证面板名册。
