# EN_STRINGS.RES 二进制结构 (完整破解) 与重编码器

日期: 2026-09-12
适用: Ghost Recon PS2 (SLUS-206.13, ike 引擎) MENU.IMG / GR.IMG 内
`EN_STRINGS.RES`、`DE/ES/FR/IT_STRINGS.RES` (五语言已交叉验证)。

---

## 一、总览: 两层结构

```
MENU.IMG 条目表 (off=0x377E000, stored=47570, real=128545)
  └─ 存储层: 8 个 LZ 子流串联 {u32 plen}{u32 osz}{LZO1X payload}
       └─ 解压(LZO1X) → 展开态 128,545 字节 = 引擎 strings 解析器真正消费的形式
            └─ 结构层: {u32 组数=66} + 66 组字符串 + {0}{0} 终止符
```

- 存储层解码器: `gr_tools\lz77_decode.py` (标准 **LZO1X**, 与 ffmpeg
  `av_lzo1x_decode` 逐位一致; 本次 5 语言 42 个子流全部精确解到 osz,
  总长逐字节等于条目表 real 字段 —— 再次独立验证了该结论)。
- **没有 magic**。展开态首 u32 就是组数 (0x42=66)。
- **没有偏移表、没有对齐、没有填充**。全部字段顺序排列, 长度自描述。

## 二、展开态完整结构 (引擎实际解析的东西)

```c
// 多字节字段一律小端 (LE)
u32  num_groups;                       // = 66
u32  count[0];                         // 组 1 的条数 (组 1 没有 sep 字段!)
entry   g1[count[0]];
for (g = 1; g < num_groups; g++) {     // 组 2..66
    u32  sep;                          // "附加串个数", EN 恒为 0
    附加串 extra[sep];                 // {u32 len}{bytes}  —— 注意: 无 u16 尾
    u32  count[g];
    entry   gn[count[g]];
}
u32 0;
u32 0;                                 // 终止符 (sep=0 + count=0)

// 字符串条目
entry = {
    u32 len;                           // 字节数 (不含尾)
    u8  data[len];                     // Latin-1 区任意字节, 0x00-0xFF
    u16 attr;                          // 恒 0x0000 (DE/IT 各有个别 0x8000, 见下)
};
```

要点:

| 项 | 结论 |
|---|---|
| 魔数 | 无。首 u32 = 组数 (EN=66) |
| 组 1 特例 | 头部 `{组数}{组1条数}` 连写, 组 1 不设 sep 字段 |
| 组间分隔 | `sep u32`(=0) + `count u32`, 即旧笔记说的 `{0}{n}` |
| 字符串长度 | **u32** 前缀, 后接数据 + **u16 属性字段** (旧笔记以为 u16 必为 0000 终止符) |
| 空串 | `{u32 0}{u16 0}` = 6 字节, EN 有 40 条 |
| 最长串 | 1580 字节 (EN G43.I10, 任务简报) |
| 字符集 | 单字节 Latin-1 语义, 无转义机制; EN 原文即含 0x92(') 0xAE(®) 0xB1(±) 0xB5(µ) 0xE7(ç) 0xF1(ñ) |
| 文本标记 | `{p}` 分页、credits 组的 `<br>` `<title>` `<image>` 等, 原样存于数据内 |
| 嵌入 NUL | EN 全部 2232 条无一个 0x00 (解析按 len, 但引擎字符串按 C 语义用, 汉化时应避开) |

EN 字节收支 (逐字节核对): `8(头) + Σ条目 + 65×8(组头 sep+count) + 8(终止符)
= 8 + (6×2232 + 114617) + 520 + 8 = 128545` ✓ 精确消费, 无余字节。

### EN 66 组条数分布 (Σ=2232)

```
G01-11  mp_mode_outcome : 4,5,8,6,6,4,5,8,6,8,10            (70)
G12-18  training        : 35×7                              (245)
G19-33  gr_campaign     : 17,18,19,19,17,16,16,22,18,22,20,16,16,15,22 (273)
G34-39  mp_map_info     : 6×6                               (36)
G40-52  ds_campaign     : 16,15,19,17,20,16,14,16,10,15,16,16,16 (196)
G53-57  ds_mp_map_info  : 6×5                               (30)
G58     main_ui_pool    : 802   (主菜单/对话框/MP 大厅/记忆卡等核心 UI)
G59     menu_mp_ui      : 41
G60     internal_id     : 1     ("mainmenu")
G61     control_labels  : 53    (按键设置界面)
G62     credits         : 289
G63/G64 resource_names  : 24, 10 (.rsb 截图/.wav 文件名, 不直接显示)
G65     options_ui      : 145
G66     resource_names  : 7
```

## 三、三个容易踩坑的隐藏字段 (DE/IT 里出现, EN 为零)

1. **sep / 附加串**: DE G60 与 IT G22、G32 前 `sep=1`, 后跟 1 条
   `{u32 len}{bytes}` 的"附加串"(DE: `\x09`; IT: `Aiutare`、`Berkut",`)。
   看内容是本地化残留碎片, 语义不明, 但**结构位置在 count 之前、没有 u16 尾**。
   之所以此前没被发现: 旧解析把 `{0}{n}` 的 0 当成组头一部分, 而 EN 恰好
   sep 恒为 0, 两种读法字节消耗完全相同。只有 DE/IT 的非零 sep 能把两者区分开。
2. **u16 属性字段**: 条目尾 u16 不总是 0x0000 —— DE G59.I012、IT G21.I008、
   IT G31.I008 为 `0x8000`, 全部是含 `{p}` 分页的任务简报类条目 (疑似
   "多页/可分页"标志, 本地化编译器产物)。EN 2232 条全为 0。
3. **组 1 无 sep**: 只有组 2 起才有 sep 字段; 文件尾 `{0}{0}` 是
   "sep=0+count=0" 的自然终结。

## 四、工具: gr_tools\res_encode.py

```bat
:: RES(存储态或展开态均可) -> 文本同构格式
python gr_tools\res_encode.py parse  EN_STRINGS.RES  strings.txt

:: 文本 -> 展开态 RES (stored==real 未压缩写回, 配 img_patch.py)
python gr_tools\res_encode.py build  strings.txt  EN_STRINGS.RES.new
::                              可选: --framed-lzo EN_STRINGS.RES.framed
::                              (单子流贪心 LZO1X 压缩写回, 配 img_patch.py --framed)

:: 轮转自检: parse->build 与展开态逐字节比对
python gr_tools\res_encode.py round  EN_STRINGS.RES

:: 最小改动: 把 G05.I004 的 'A' 改为 0xC6 并自检
python gr_tools\res_encode.py mod EN_STRINGS.RES out.res 5 4 A C6

:: 结构摘要
python gr_tools\res_encode.py probe EN_STRINGS.RES
```

文本同构格式 (与 decoded.bin 同构, 一行一字符串, 编号强制连续):

```
# 注释/空行忽略
[G01] sep=0
I000=Victory!
I008[8000]=...      <- attr 非 0 时用 [HEX] 后缀 (保真 DE/IT 用)
[G02] sep=0
...
转义: \\  \n  \r  \t  \xNN ; 其余 0x20-0x7E 原样
```

## 五、轮转验证结果 (encode(parse(x)) == x)

| 验证 | 结果 |
|---|---|
| EN 展开态: parse→build vs 原文 | **逐字节 PASS** (128,545 B) |
| EN 存储态: LZO 解码→parse→build vs 展开态 | **逐字节 PASS** |
| EN 文本往返: text→build→text | **PASS** |
| DE / ES / FR / IT 四语言同套验证 (含 sep/附加串/0x8000 attr) | **全部逐字节 PASS** |
| `--framed-lzo` 压缩写回 (自研贪心 LZO1X, 59,145 B) | 解码自检 == 展开态 **PASS** |

说明: 存储态字节本身不做逐字节复现 —— LZO1X 压缩器的选点无法确定性重现
(minilzo 优化策略未实现, 也无必要)。写回走两条路:
1. **未压缩** (推荐, 项目既定约定): 展开态整文件写回, 条目表 stored=real=128545,
   引擎跳过解码直接读 —— `img_patch.py` 默认行为;
2. **压缩框架** (`--framed-lzo`): 合法 LZO1X 单子流, `img_patch.py --framed`
   会把 real 写成 osz, 引擎走正常解码路径。

## 六、最小改动验证 (未来放汉字槽位字节)

- `mod ... 5 4 A C6`: G05.I004 "Accumulate the most kills..." 首字节
  'A'(0x41) → 0xC6。结果: **全文件恰好 1 字节差异** (@0x2F0), 长度不变,
  66 组起始偏移全部不变, 重解析 ✓。
- 变长测试: 同一条目末尾追加 2 字节 (模拟双字节汉字) → 文件 +2 字节,
  该条目 len 字段 0x4B→0x4D 正确重算, 尾部 `{0}{0}` 完好, 66 组重解析 ✓
  (产物 `C:\gr_build\tmp\mod_grow.res`)。
- 结论: 结构无偏移表, **任意条目任意变长都安全**, 组与后续条目自动顺延。

## 七、与 GR_EN_STRINGS_RES_decoded.bin 的关系 (重要警告)

`han_v2\GR_EN_STRINGS_RES_decoded.bin` (128,668 B) 是此前会话手搓的"规范
重序列化"版本, 结构与本文完全一致, 但**内容被人改过 12 条训练文本**
(G12-G17.I002 等: "…timers after you're clear of the blast area." 被改成
"…timers well after you're clear of the mission area." 等, +123 字节)。
它不是纯净解码产物。汉化应以本次从 MENU.IMG 原样解出的展开态为基准:
`C:\gr_build\tmp\en_strings_res_expanded.bin` (128,545 B, 未动任何原始文件)。

## 八、"中文写回 RES" 可行性结论

1. **格式层: 完全可行。** 字符串是 `{u32 len}{任意字节}{u16 attr}`, 长度
   自描述, **没有转义、没有保留字节、没有对齐/偏移约束**; 0x80-0xFF 高位
   字节就是普通数据 (EN 原文自带 6 种, 法/德/意/西文版大量使用)。
   写回变长毫无障碍 (见第六节)。
2. **解析层: 安全。** 引擎按 len 切分, 不扫描内容; 组数/条数任意可变
   (DE/IT 的组条数分布即与 EN 不同)。唯一注意: 避免在串内放 0x00
   (项目既定重映射方案 0x80-0xFF/空闲 ASCII 本来就不含 0x00), attr 保持 0。
3. **渲染层: 真正的瓶颈在 FONT.RES** (与 RES 格式无关): 0x80-0xFF 槽位
   必须先注入对应字形 (项目已有 RSFB 注入方案; FONT.RES 条目码字段 16 位,
   可挂 Latin Extended-A 等)。
4. **风险声明**: RES 的"未压缩写回"沿用了 TXT/.ATR 已实机验证过的
   stored==real 档案层机制, 但 RES 条目本身尚未单独开机验证 —— 上真机/
   PCSX2 前, 建议先做"原内容未压缩写回"的 A/B 引导测试 (排除非格式因素)。
   之前"计数框架中文 TXT 导致记忆卡画面卡死"的事故, 现在可以定因:
   当时的 LZ 框架编码是错误的 (那不是 LZ77 真格式), 与 RES/TXT 格式本身无关。

## 九、关键文件

| 文件 | 说明 |
|---|---|
| `gr_tools\res_encode.py` | RES 解析/文本同构/重建/轮转/最小改动 工具 (本次新增) |
| `gr_tools\lz77_decode.py` | LZO1X 存储层解码器 (既有, 已验证) |
| `gr_tools\img_patch.py` | IMG 空隙/追加写回 (stored=real; --framed 支持压缩框架) |
| `C:\gr_build\tmp\en_strings_res_raw.bin` | MENU.IMG 内 EN_STRINGS.RES 原始存储字节 (47,570 B) |
| `C:\gr_build\tmp\en_strings_res_expanded.bin` | 展开态真身 (128,545 B, 未受历史编辑污染) |
| `C:\gr_build\tmp\en_strings.txt` | EN 全量文本同构格式 (66 组 2232 条) |
| `C:\gr_build\tmp\mod_A_C6.res` / `mod_grow.res` | 最小改动/变长测试产物 |

## 十、BMZ/ATR/MIS 格式重测结论 (2026-09-11, 基于纯净 GR.IMG)

背景: 当年「D02_REFINERY.BMZ 非 LZO1X」的结论是用错误的计数解压器得出的;
本次用 `gr_tools\lz77_decode.py` (标准 LZO1X) 重测, **全部破解, 零失败**。

**纯净 GR.IMG 提取**: 实际位置是 ISO9660 目录 `/GR.IMG;1` = **LBA 19175**,
大小 = 头 0x00 u32 = 1,550,563,328 B (早前情报的 LBA 19194 有偏, 读不出合法头)。
命令: `dd if=GR_K99.iso of=GR.img bs=2048 skip=19175 count=757113` 后截断到 1550563328。
纯净产物: `C:\gr_build\tmp\GR.img`。条目表用 `gr_tools\gr_lz.py` 的 `load_entries`
(4070 条目, 仅用条目表; 其 `decompress_stream` 是旧错误解码器, 勿用)。

### BMZ (307 个, 场景/模型容器) — 已破解但无文本

- 存储层与全档案一致: `{u32 plen}{u32 osz}{payload}` 子流串联, payload = 标准 LZO1X
  (压缩子流 plen<osz; 另有 plen==osz 原样子流)。
- **批量验证 307/307 全部解压成功**, 每条 sum(osz)==real, 0 错误
  (日志 `C:\gr_build\tmp\bmz_atr\bmz_batch_verify.log`)。
- 例 D02_REFINERY.BMZ (stored 2,006,906 → real 3,208,480): 196 子流 (184 压缩 +
  12 原样), 前 12 个子流 osz 均为 16384 (16KB 块)。
- 解码产物 = **纯二进制场景数据** (纹理/几何块), 全文不含任何明文英文
  ("the "、"press " 等常见词 0 命中, 常规 strings 全是噪声)。
  → **教程文本不在 BMZ**。旧「BMZ 载教程文本」说法不成立; 训练教程真身在
  GR.IMG 的 `EN_STRINGS.RES` (见 TRAINING_TEXTS.txt)。
- 排除项: 无需 magic/头偏移/异或壳/nested-LZO 假设 — 标准 LZO1X 直接全过。
- 解码命令:
  `python -c "import sys; sys.path.insert(0,r'...\gr_tools'); import gr_lz,lz77_decode; d,e=gr_lz.load_entries(r'C:\gr_build\tmp\GR.img'); ent=[x for x in e if x['name']=='D02_REFINERY.BMZ'][0]; out,st=lz77_decode.decode_entry(d[ent['off']:ent['off']+ent['stored']]); open('out.bin','wb').write(out)"`

### ATR (1193 个, 队友 XML) — 已破解

- **1192/1193 个 stored==real, 本身就是 XML 文本** `<ActorFile>` (与 PC 版 .atr 同构,
  可参照 `Ghost Recon\Mods\Mp1\Actor\*.atr`); 仅 `D_JODIT_HAILE.ATR` 走 LZO1X
  (482→1076, 单子流, 解压 0 错误) — 即"以前成功解码/改中文名"的那个。
- 标签共 65 种: `<ActorName>` 队友名, `<ClassName>` 兵种, `<Weapon>`/`<Stamina>`/
  `<Stealth>`/`<Leadership>` 0-8 属性, `<ModelFace>`/`<KitPath>`/`<LOD2>` 等资源引用。
  **汉化点 = ActorName** (档案层未压缩写回已实机验证过)。
- 5 名 Ghost 队友: `D_SCOTT_IBRAHIM.ATR`=Scott Ibrahim(sniper), `D_LINDY_COHEN.ATR`=
  Lindy Cohen(rifleman), `D_NIGEL_TUNNEY.ATR`=Nigel Tunney(demolitions),
  `D_DIETER_MUNZ.ATR`=Dieter Munz(support), `D_JODIT_HAILE.ATR`=Jodit Haile(rifleman)。
- **ATR 内没有简报字段** — 简报在 .MIS (下)。

### MIS (46 个, 任务/简报 XML) — 简报真身

- 同为 XML `<MissionFile>`: `<BriefingText>` 任务简报 (`{p}` 为分段符),
  `<LocationText>`/`<DateText>`/`<TimeText>`/`<MapName>` 等 + 对应 `<xxxId>` 数字串 ID。
- 例 D02_REFINERY.MIS (24,176→100,987, 7 子流 0 错误): BriefingText 开头
  "It looks like we have a rush job on our hands. We're making good progress in the
  push for Massawa itself, but the Ethiopian forces have adopted a scorched-earth
  policy..."。

### 产物清单 (C:\gr_build\tmp\bmz_atr\)

| 文件 | 说明 |
|---|---|
| `..\GR.img` | 从 ISO LBA 19175 提取的纯净 GR.IMG (1,550,563,328 B) |
| `D02_REFINERY.BMZ.dec` / `.BMB.dec` | BMZ/BMB 解码产物 (无文本, 场景数据) |
| `D02_REFINERY.MIS.dec` | 任务简报 XML (BriefingText 所在) |
| `EN_STRINGS.RES.dec` | 训练教程文本真身 (128,668 B) |
| `atr\*.ATR` / `atr\D_JODIT_HAILE.ATR.dec` | ATR 样本 + 唯一压缩 ATR 的解码 |
| `bmz_first64.txt` | 全部 307 个 BMZ 的头 64B + 子流参数 |
| `bmz_batch_verify.log` | 307/307 批量验证日志 |
| `entries.json` | GR.IMG 全部 4070 条目表 (name/stored/real/off) |

## 十一、GR.IMG RES 结构与普查结论 (2026-09-12, 基于纯净 GR.IMG)

纯净 GR.IMG (`C:\gr_build\tmp\GR.img`, LBA 19175, 1,550,563,328 B) 内的 STRINGS 家族
与 MENU.IMG **完全同构**: 5 语言 `*_STRINGS.RES` 全部为 LZO 压缩态, 用 `lz77_decode.py`
零错误解出。EN 份: off=212,604,752, stored=47,619, real=**128,668**, 8 子流;
解析出 66 组 2232 条, 每组条数分布/sep/attr/高位字节与 MENU 逐一相同;
`res_encode.py` 轮转逐字节 PASS; 字节收支 `8+(6×2232+114,740)+520+8=128,668` 精确消费。

**勘误 (修正第七章)**: `GR_EN_STRINGS_RES_decoded.bin` (128,668 B) 经比对与 GR.IMG
解压态**逐字节一致** —— 它是 GR.IMG 份的忠实解码, 不是"污染版"。盘片上 GR.IMG 与
MENU.IMG 各存一份 EN_STRINGS.RES, 内容本就有 **12 条差异 (合计 +123 B)**:
G12~G18.I002 "timers **well** after ... **mission** area" vs "timers after ... **blast** area";
G19.I006 "Moutains"拼写; G21.I008 "practicable" vs "practical"; G44.I010 多一句
"They'll be detonated 30 seconds..."; G49.I009 弯引号 0x92; G50.I010 place/plant + \xA0。
两份各自成立, 改哪份以哪份原文为基准。

其余语言: DE 55,542/146,910 (37.8%)、ES 53,077/142,148、FR 55,413/149,664、
IT 51,736/139,082, 各 9~10 子流 0 错误。全库 4070 条目: 压缩 1452 / 明文 2618,
Σstored/Σreal = 93.4% (音视频明文拉高; 文本类 ~37~40%)。

**新发现 — STRINGS.TXT 家族 (6 个, 各约 2.6KB stored / 6.9KB real)**: 明文
`Token→显示名` 表 (222 行), 是**武器/物品拾取名真身**: WPN_M4→"M4"、WPN_AT4→"M136"、
ITM_CLAYMORE→"Claymore"、ITM_BOMB→"Demo Charge"、WPN_EXTRAAMMO→"Extra Ammo" +
键位名 + Kit 限制 ("Grenades Only" 等); 各语言版仅 4~10 行互异。
另: **FONT.RES 在 GR.IMG 有一份** (off 212,710,976, stored 4,421, real 7,222) —
字形注入须与 MENU.IMG 份分别处理。明文 XML 家族还有 KIT(131)/ENV(28)/VCL(17)/
PRJ(9)/ITM(6)/XML(4)/TOE(1) — 均无显示文本; CONSOLE/IGOR*.TXT 为 PC 调试残留。

**原地覆写约束 (数字)**: EN_STRINGS.RES stored 槽位 47,619 B < 展开态 128,668 B,
且 framed-LZO 同规模实测 59,145 B 也超槽 → GR.IMG 侧写回**必须走 img_patch.py
stored==real 重定位**, 与 TXT/.ATR 验证过的路径一致; 中文替换只会缩短展开态, 无溢出。

44 字表可达性: 2232 条中稳妥可达约 58 条候选 (队名 A队/B队/1队~4队、兵种 枪手/雷、
信息/地图/武器、控制标签 前进/左移/右移/左视/右视/选枪/换枪/换弹/聊天/聊天信息、
"下雷"类 HUD 与目标、行前带雷等), 逐条槽位字节见 `C:\gr_build\tmp\gr_res\survey.md`
第四章与 `cand_table.md`; 教程 203 句与 28 份简报在 44 字表下全部 SKIP (缺
敌/我/友/不/胜/负/东南西北/机/狙/夜/存 等), 需 FONT.RES 扩容后再攻。
分类统计: 教程 203(+42 头) / 武器HUD兵种ROE 79 / 任务目标简报无线电 615 /
菜单界面 962 / credits 等其他 331。全量 dump: `C:\gr_build\tmp\gr_res\en_dump.txt`。

## 十二、FONT.RES (RSFont) 语义结论 (2026-09-12, 翻案实验 + ZH5 实装全实证)

补充第八章第 3 条: FONT.RES 已完整破解并实机编辑成功 (GR_ZH5 上屏)。
详细实验矩阵见 RES_AB_TEST.md 第九章 (T0-T2 微编辑) 与第十章 (ZH5)。

### 文件结构

```
{u32 20}{"new_font_revised.rsb"}{u32 3}
face×3: {u32 len}{name}                      // "large" / "default" / "huge"
        {u32 步长=10}{u32 行高×3}{u32 首字符=0x20}...
        记录表: 223 条 × 10B (字符 0x20..0xFE, 逐字符 (c-0x20)*10)
        8B 尾 (实为 0xFF 的半条记录残迹, 不可写!)
FontDefinition 数组 + 缩放浮点块 (尾部 ~270B)
```

| face | 表偏移 (MENU.IMG 展开态) | 行高 | 用途 |
|---|---|---|---|
| large | 0x5F | 26px | Name Entry 键盘 / 帮助条 |
| default | 0x962 | 26px | 菜单标签/按钮提示 |
| huge | 0x1262 | 42px | 大标题 |

### 记录语义 (10B = 5×u16, 全部实机微编辑实证)

`{u0, v0, u1, v1, adv}`
- u0/u1 = 图集采样左右缘, v0/v1 = 上下缘 (矩形, 各 face 行带内);
- **adv = 字符推进宽度, 单位 1/256 px** (0x1000 = 16.00px; 实测 +0x100 ≈ 后一字符位移 1px);
- **引擎采样矩形 = (u0+20, v0)-(u1+20, v1)**: u 恒加 20px (v 不加)。
  三 face 16 条行带逐带谷点对齐全落在 +19/+20; default 表 0xB1/0xB5/0xC6/0xD2/
  0xE7/0xF1 格 +20 与图集实测墨迹逐像素一致; GR_ZH3/ZH5 在 +20 处重绘上屏成功。
- 图集 = COMMON.PAK 内具名纹理 `new_font_revised` (512×512 8bpp @0x1069;
  PAK 条目头 = {u32 name_len}{name}{u32 w}{u32 h}...), 背景 31=透明、笔画 0=实心
  (引擎反向 alpha; 82-89 为亮边值, 低阈值墨水剖面会漏检亮边字形)。

### 硬约束 (违反 = 字体系统全灭, 开机环无字假活)

1. 每表只有 **0x20-0xFE 共 223 条**有效记录; **0xFF"槽位"= 表尾 8B + 下一 face 头**,
   写 10B 会破坏下一 face 名长度字段 → RSFontMgr 名字解析崩 → 全部文字消失、
   UI 初始化停摆 (GR_ZH5 首轮实挂, snap f2914 "Please wait!" 消失定因)。
2. 编辑后必须 ft_dpc.py (DP 最优, tmp\ft_dpc.py) 重压缩, payload ≤4,413B
   (帧 {plen}{7222}{payload} + 0x00 填满 stored=4,421 槽); 写回前后 decode_entry 自检。
3. 条目表 off=0xB9120/stored=4,421/real=7,222 三字段不动 (menu 与 GR.IMG 各一份,
   GR.IMG 份 off=212,710,976 同尺寸, 如需游戏内字体须分别处理)。
4. 引擎只加载 EN strings: 图集受保护字形 = ASCII 全部 + 0x92 + ®±µçñ;
   其余 Latin-1 与全部占位虚线格可覆盖。

### 实装配方 (ZH5, 已 40000 帧实测)

16px 汉字格: 记录改 `{sx-20, v0, sx-20+16, v1, 0x1000}`, 在图集 (sx,v0)-(sx+16,v1)
贴 SimHei 16px EBDT 真点阵 (二值); 槽位优先用图集尾部空带 y478-511 与 default
Latin-1 两行的非保护区; 布局与码表见 `C:\gr_build\tmp\zh5\layout_zh5.txt`。
