# hanliu/texts — 原始文本导出（翻译工作底账）

生成器: `..\tools\export_texts.py`（可随时重跑，带基准条数自检）。
生成日期: 2026-09-12/13（GR_ZH7 交付轮）。

> 公开库说明: 本目录 CSV 为游戏文本导出物，**不入库**（.gitignore 剥离，本地保留）。
> 克隆后运行 `python tools/hanliu/tools/export_texts.py` 自备原盘一键再生，行数基准见下表。

**所有 CSV 一律 utf-8-sig 编码**（带 BOM，Excel 直接打开不乱码）；第一行为表头；
含逗号/引号/换行的字段按 RFC4180 双引号转义。

| 文件 | 内容 | 数据行数（不含表头） | 纯净源 |
|---|---|---|---|
| `menu_res_en.csv` | MENU.IMG `EN_STRINGS.RES` 展开态全量 | **2232**（66 组） | menu_orig\MENU.IMG（原盘副本） |
| `gr_res_en.csv` | GR.IMG `EN_STRINGS.RES` 展开态全量（教程/任务简报/任务目标真身） | **2232**（66 组） | 原盘 ISO 内 GR.IMG（LBA 19175, off 212,604,752, stored 47,619 → 展开 128,668）；已验证与 `han_v2\GR_EN_STRINGS_RES_decoded.bin` 逐字节一致 |
| `txt_family.csv` | MENU.IMG + GR.IMG 两份 × 5 语言 `*_STRINGS.TXT`（武器/物品拾取名、键位名） | **2220** = 222 键 × 10 份 | 两档案原文 |
| `atr_actors.csv` | GR.IMG 全部 `.ATR` 角色档案标签 | **1193** | 原盘 ISO 内 GR.IMG |
| `mis_briefings.csv` | 全部 `.MIS` 简报（解码自 LZO1X，46 份） | **46** | han_v2\mis_decoded |
| `pc_official_zh.csv` | 官方 PC 中文翻译（GBK→UTF-8），翻译的最佳参考源 | **2902** = strings.txt 225 + STRINGS.RES 2677 值 | `Ghost Recon\Data\Shell\` |

## 各表结构

### menu_res_en.csv / gr_res_en.csv
```
group,idx,attr,len,hex,text
G58,I003,0000,2,4f6b,Ok
```
- `group` = 组号 G01..G66；`idx` = 组内条目 I000..；两者拼成 key `G58.I003`，
  即 `text_replace.py --mode res` 的 key。
- `attr` = 条目尾 u16 属性（EN 全 0000；DE/IT 个别 8000=含 `{p}` 分页）。
- `hex` = 原始字节流 .hex()；`text` = 可读形式。**hex 为无损真身**；
  text 列转义规则：`\t` `\n` `\r` `\\` `\xNN`（0x00-0x1F 控制字节），0x80-0xFF
  按 Latin-1 直接显示为对应字符（如 0x92=’ 0xAE=®）。

### txt_family.csv
```
source,lang,key,value
MENU,EN,WPN_M4,M4
```
- `source` ∈ {MENU, GR}；`lang` ∈ {EN, DE, ES, FR, IT}；key/value 即 TXT 内
  `\t"KEY"\t..."VALUE"` 行。注意两份 TXT 的 WPN_PSG1 行尾带一个多余制表符（原始如此）。

### atr_actors.csv
```
atr,actor_name,class_name,weapon,stamina,stealth,leadership,n_tags,other_tags
D_SCOTT_IBRAHIM.ATR,Scott Ibrahim,sniper,...,16,other_tags…
```
- ATR = 纯 XML（仅 D_JODIT_HAILE.ATR 曾压缩）。`other_tags` = 其余全部标签的
  `tag=value` 分号串。共 65 种标签；**ActorName 是唯一值得汉化的字段**，但注意：
  实机已证（nav25）指令面板在 ATR 含中文名时打不开，此路需另寻编码，默认保留英文。

### mis_briefings.csv
```
mis,location,date,time,map_name,briefing_len,briefing_text
D02_REFINERY,Refinery,2008.07.01,0530 Hours,D02_Refinery,2345,"It looks like ..."
```
- `{p}` = 简报分页符，原样保留。
- **18 个 MIS（DP/MP/T 系训练关）无内联 BriefingText**：它们用 `<BriefingId>` 数字
  引用 GR.IMG RES 的简报条目（G12-G18 训练组 / G19-G33 战役组），文本在
  gr_res_en.csv 里。这是原始结构，不是导出缺陷。

### pc_official_zh.csv
```
source,key,idx,value
strings.txt,WPN_FRAG,,爆裂手雷
STRINGS.RES,String,25,消灭所有敌人
```
- 翻译参考主源。`strings.txt` = 武器/物品/键位 225 行；`STRINGS.RES` = 官方全部
  界面/简报/训练/制作表文案 83 键 2677 值（含训练教程官方译本）。
- PC STRINGS.RES 二进制格式（本次破译）：
  `{u32 count=83}` + count×`{u32 klen}{key}{u8 flag}{u32 n}{n×{u32 len}{GBK}{u16 0}}{u32 0}`
  + 文件尾 `{u32 0}`；flag=0x01 仅 ShellScenes；精确消费 91,775B。

## 已知非纯净源警告
`WS\gr_img\GR.IMG`（1,550,563,328B, 2026-09-12）是历史实验改写副本：其
`EN_STRINGS.RES` 已被框架化单子流重注入（off=481,042,432, stored=129,185），
**不要**把它当纯净档使用。本目录 gr_res_en/atr 的数据一律从原盘 ISO 直读。
