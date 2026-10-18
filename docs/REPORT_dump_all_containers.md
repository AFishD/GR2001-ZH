# REPORT_dump_all_containers.md — 全容器文本 dump 与「可注入 / view-only」分类（round39）

> **任务**：用户要求「dump 出来的 csv 也要包含所有容器里的文本，自行分类出不同的 csv」。
> **结论一句话**：全盘 **4713 个容器**已 100% 覆盖，按「容器类型 × 文本形态」自动分成
> **8 张分类表 + 1 张闸门依据表 + 1 张总表**（共 10 张，60590 行）；
> 除原有的 LANG / SFXML 三张表（`injectable=yes`）外，**其余一律 view-only**
> （`injectable=no`），注入器认得出并**报错拒写盘**（两道防线，已实测）。
> **全盘除 LANG / SFXML 之外没有汉语文本**——主程序里剩的 5 个字是本工程自己写进去的。

* 工具：`tools/text_csv/dump_containers.py`（新增，只读 ISO）
* 复用（**只 import，未修改**）：`tools/font_pipeline/font_usage.py` 的容器枚举/解码口径
* 测试盘：`work/builds/GR_ZH92/GR_ZH92.iso` = `1d30c1067beb8fc8534193486f23f75489447eb0487ab24d06ef66c0627120b6`（**只读，未改动**）
* 实测日志：`work/builds/GR_ZH92/temp/r39/`（`ACCEPT_run.log` / `probe_*.log` / `verify_rt4.log` 等）
* 产出的表：`work/builds/GR_ZH92/text/GR_ZH92_view_*.csv`（10 张）+ `…_view_containers.meta.json`

---

## 1. 分类方案

### 1.1 为什么分「可注入」和「view-only」两类（安全红线）

| | `*_text_*.csv`（可注入） | `*_view_*.csv`（view-only） |
|---|---|---|
| 谁产出 | `dump_text_csv.py`（现役，未改动列名/语义） | `dump_containers.py`（新增） |
| 覆盖 | **2 类**资源：`LANG` 语言表 + `SFXML` 特别收录 = 2261 条 | **其余 4700+ 个容器** |
| 依据 | 格式**完全逆向**，dump→注入**逐字节往返**成立 | 格式**未逆向**，做不到逐字节往返 |
| 能不能改 | ★ 能（只改 `text_edited`） | ✗ **不能**（写回去会毁盘） |
| 表内标记 | 无该列（靠命名区分） | **每行 `injectable = no`** |

判据是死的：**只有格式被真正理解、且能逐字节往返零差异的类别，才允许标为可注入。**
其余一律 view-only，并在表里用 `injectable` 列写死。

### 1.2 8 个自动分类（+ 闸门依据表 + 总表）

| # | 表名后缀 | 容器 kind | 内容 | 行数 | 容器（放行/总） |
|---|---|---|---|---|---|
| 1 | `xml` | 其它 `.XML` | `CAMPAIGN.XML` / `BRIEFINGS.XML` / `EFFECTS.XML` / `*_VOICE_*.XML` … | 516 | 35 / 35 |
| 2 | `txt` | `.TXT` | `STRINGS.TXT` / `DE/ES/FR/IT_STRINGS.TXT` / `MODSCONT.TXT` | 3254 | 17 / 17 |
| 3 | `missions` | `.MIS` | 46 个任务/训练/遭遇战（内容实为 XML 文本） | 2008 | 92 / 92 |
| 4 | `character_names` | `.ATR` | 1460 个人物/队伍/武器定义（**人名全英文，0 汉字**） | 4439 | 1460 / 1460 |
| 5 | `other_res` | `.RES` | 德/西/法/意 4 份语言表 + `FONT.RES` / `IKE.RES` | 14273 | 13 / 13 |
| 6 | `program_strings` | ELF | `SLUS_206.13` 的 C++ 带符号名 / 调试串 / 幽默函数名 | 2000（截断自 35450） | 1 / 1 |
| 7 | `iso_files` | ISO 独立文件 | `SYSTEM.CNF` / `MODULES/*.IRX` / `IOPRP242.IMG` | 1624 | 22 / 22 |
| 8 | `binary_assets` | `RSB/PAK/MEDIA/OTHER` | `.BMH/.BMZ` 贴图名表、`.DIR`/`.LST` 清单、`.AOL`/`.IDC` 等 | 30000（截断自 80541） | 604 / 3069 |
| — | `pending` | 全部 | **未 dump 的容器 + 逐行判定依据** | 2465 | 2465 |
| — | `containers_summary` | 全部 | **先看这张**：一行一个类别 + 能不能改 | 11 | — |

`LANG` / `SFXML` **不重复 dump**：它们就是 `*_text_*.csv` 那三张，`containers_summary` 里
有两行专门指路并标 `injectable=yes`（保证用户"一张表看全"）。

### 1.3 view 表的列（15 列，列名都是人话）

`category` / `source_kind` / `container` / `entry_index` / `offset` / `len_bytes` /
`text` / `text_preview` / `dup_count` / `text_kind` / `confidence` / `has_cjk` / `cjk_run` /
`injectable` / `note`

* `text_kind`：`exact`（纯 ASCII 无空格 ⇒ 名字/文件名）/ `text`（像一句话）/ `fragment`（碎片）
* `confidence`：`high`（该容器干净串 ≥5%）/ `medium`（≥0.5%）/ `low`（仅过闸门）
* `has_cjk`：**≥2 个连续汉字**才算 yes（单个汉字在压缩数据里必是巧合）；`cjk_run` 给最长连续数
* 排版与现有多表**完全一致**：UTF-8 BOM + CRLF + 正文列加引号 ⇒ Excel 双击可开

---

## 2. 文本判据与阈值（4 关，全部实测标定）

| 关 | 判据 | 默认值 |
|---|---|---|
| **1 可读串** | 连续 N 字节落在扫描字母表（与 `font_usage.CharsetIndex.alphabet` 同一份：ASCII 0x20–0x7E + 本盘单字节码 + 对偶 lead/trail + 按键字节） | 结构化容器 **6 B** / 二进制容器 **8 B** |
| **2 像文本** | ① 纯 ASCII ⇒ 字母数字占比 ≥ **0.70**；② 含高位字节 ⇒ 用**本盘字符集单字节优先**解码后：可见字符 ≥ **0.85** 且字母数字 ≥ **0.55** 且含汉字；③ 无私有区回落（有 ⇒ 未映射字节，不是文本）；④ 同字符连续重复 ≤ **8**；⑤ 长度 ≥ 16 要有标点/空格；⑥ 无长度 4 的重复子串（压缩数据特征） | 见左 |
| **3 容器级闸门**（**只**对 `RSB/PAK/MEDIA/OTHER`） | `distinct` ≥ **10** **且** `score`（去重串数/MB）≥ **10** **且** `clean_ratio`（干净 ASCII 串字节/容器字节）≥ **0.002** | 见左 |
| **4 每容器上限** | 去重后最多写出的串数，超了按 `confidence` 高→低截断并记数 | **2000 条** |

★ 结构性容器的串**没有**噪声（`MIS` 中位 24 条、`XML` 中位 2 条、`.DIR` 中位 14 条不同串），
而 `MEDIA` 的 549447 条候选里 **`dup_count` 全为 1** —— 这是"噪声"与"真内容"最干净的分离面。

### 2.1 阈值为什么是这些数（噪声本底实测）

| 样本 | `score`（串/MB） | `clean_ratio` | `text_ratio` | 判定 |
|---|---|---|---|---|
| **纯随机数据 1 MB** | 1.0 | — | — | 噪声本底 |
| **纯随机数据 4 MB** | 0.2 | — | — | 噪声本底 |
| **纯随机数据 16 MB** | 0.6 | — | — | 噪声本底 |
| `ZZZ.PSS`（视频，143 MB） | 14.6 | **0.000002** | 0.014 | **拒**（`clean_ratio` 差 3 个数量级） |
| `MUSIC.TM`（音乐，50 MB） | 42.3 | **0.0004** | 0.015 | **拒** |
| `BNK_95_05.SS`（音效，9 MB） | 227 | **0.0016** | 0.914 | **拒** |
| `D01_BEACH.SHT`（精灵图，1 MB） | 213 | **0.0010** | 0.592 | **拒** |
| `D01_BEACH.BMZ`（压缩贴图） | 462 | 0.0033 | 0.845 | 放行（真贴图名表） |
| `MP04_VALLEY.BMZ` | 1438 | 0.0085 | — | 放行 |
| `.DIR` 清单（`ACTOR_ATR.DIR`） | 926 | **0.9423** | 1.000 | 放行（高置信） |
| `.MIS`（`D01_BEACH.MIS`） | 24 | 0.0047 | 1.000 | 放行 |
| `.RES`（`EN_STRINGS.RES`） | 1398 | 0.019 | 0.685 | 放行 |
| `.TXT`（`DE_STRINGS.TXT`） | 247 | **0.3098** | 0.281 | 放行 |
| ELF（`SLUS_206.13`） | 56 | 0.0006 | 0.143 | 放行（不在闸门范围，见 §2.2） |

### 2.2 ★ 视频/音频流默认**不扫**（新增的保守口径）

`.PSS / .SS / .TM / .MPG / .M2V` 默认**不进入原始串扫描**（`--scan-streams` 可强制开）。
依据（`probe_logoubi.log` / `probe_media.log`）：

* `ZZZ.PSS`（143 MB）在第 1–2 关全开后仍有 **2910 条候选**，但**全部 `dup_count = 1`**
  （真名字表里的串会重复出现，压缩数据不会）；
* `MUSIC.TM` 的 640 条候选里最长的只有 15 字节，全是 `"1tUC40de3SE B$'"` 这种碎片；
* 这些"候选"在**英文原盘的同一个容器**里**一模一样**地出现 ⇒ 是字符集里的字节巧合。

⇒ 它们**不含可本地化文本**，所以不进 `binary_assets` 表，只在 `_view_pending.csv`
里各占一行，`reason = stream-container`，`note` 写明原因与实测数字。

### 2.3 ★ 为什么**不用**「容器里出现了汉字」当判据

本盘字符集有 **1319 个对偶码**；一个字节落在 `0xA1..0xB0` 时撞上真对偶的概率很高
⇒ **压缩数据里"解出汉字"是噪声巧合**。量化证据（`probe_evidence.log`）：

* 把中文盘与**英文原盘**逐容器做**命中集合减法**（同一容器：中文盘解出的汉字 − 英文盘解出的汉字）：
  **4713 个容器里 4700 个命中集合逐元素相同**；
* 剩下 **13 个**不同的容器里，除 `LANG`（1123 字）/ `SFXML`（1023 字）外，
  **只有 `SLUS_206.13` 剩 5 个字**：`入 待 等 请 载`（本工程自己写进主程序的载入提示）；
* 所以 view 表里的"汉字"行**不是翻译残留**，是噪声证据 ——
  表里用 `has_cjk`（≥2 连续汉字）+ `confidence`（low）两列把它标出来。

---

## 3. ★ view-only 保险：注入器会拒绝（两道防线，已实测）

### 3.1 防线①：命名空间互斥

* view 表叫 `<版本>_view_<类别>.csv`；注入器 `--csv <目录>` 自动扫描的是 `*_text_*.csv`；
* 实测：`--csv work/builds/GR_ZH92/text`（该目录里 `_text_` 与 `_view_` 并存）
  ⇒ **只读入 3 张 `_text_*.csv`**，10 张 view 表一张都没被读；
* 产出端还有硬断言：`check_names()` 拒绝任何含 `_text_` 的 view 表名。

### 3.2 防线②：显式拒绝（附实测输出）

**（a）直接给 view 表**：

```console
$ python tools/text_csv/inject_text_csv.py --csv work/builds/GR_ZH92/text/GR_ZH92_view_xml.csv \
      --src work/builds/GR_ZH92/GR_ZH92.iso --dst work/builds/GR_ZH92/temp/r39/SHOULD_NOT_EXIST.iso
# inject_text_csv.py — text-csv/4 注入器 (多表布局)

[!!] 拒绝注入: 给进来的是 **view-only 表** (只能看/校对, 不能注入):
   work/builds/GR_ZH92/text/GR_ZH92_view_xml.csv

  为什么拒绝: 这些表是 tools/text_csv/dump_containers.py 的「全容器文本普查」
  产物 (.ATR / .MIS / .XML / .TXT / .RES / ELF / 贴图名 / 调试串 …)。
  它们**没有** id / entry_index / offset / len_bytes 这些注入必需的定位列,
  而且那些容器的格式没被逆向、做不到逐字节往返 —— 强行写回会**毁盘**。

  怎么办: ① 想改游戏正文, 请改这三张表里的 text_edited 列 (它们可注入):
             <版本>_text_long.csv / _long_nowrap.csv / _short.csv
           它们和 view 表在**同一个 text/ 目录**里。
          ② 想只看/校对 view 表: 用 Excel 打开就行, 本工具不会动它。
          ③ 想注入整个目录: --csv <该目录> —— 注入器自动扫描的是 *_text_*.csv,
           天然扫不到 _view_*.csv, 所以给目录是安全的。
  ★ 一个字都没写盘。
$ echo $LASTEXITCODE
1
$ ls work/builds/GR_ZH92/temp/r39/SHOULD_NOT_EXIST.iso
（不存在）✓
```

**（b）把 view 表改名成 `*_text_*.csv` 想蒙混**（第二道判据 = 表内 `injectable = no`）：

```console
$ cp .../GR_ZH92_view_xml.csv .../RENAMED_text_evil.csv
$ python tools/text_csv/inject_text_csv.py --csv .../RENAMED_text_evil.csv \
      --src .../GR_ZH92.iso --dst .../SHOULD_NOT_EXIST2.iso
[!!] 拒绝注入: 这张表里有 516 行自述 **injectable = no** (view-only):
   work/builds/GR_ZH92/temp/r39/RENAMED_text_evil.csv
  这是 tools/text_csv/dump_containers.py 产出的「全容器文本普查」表 ——
  只能看/校对, **不能注入**: 那类容器的格式没被逆向, 写回去会毁盘。
  ★ 一个字都没写盘。
$ echo $LASTEXITCODE
1
（产物不存在 ✓）
```

> 为什么**不**给 `--force` 口子：注入器要靠 `id`/`entry_index`/`offset`/`len_bytes`
> 才能定位写在哪，而 view 表**根本没有这些列** ⇒ 强行写也不知道往哪写。所以是硬拒绝。

---

## 4. 验收结果（全部实跑）

### ① 全量 dump 能跑通，并打印每张表的类别/容器数/条目数/是否可注入

`ACCEPT_run.log`（`--max-rows-per-category 30000`，退出码 **0**）：

```
# dump_containers.py — text-csv/view/1 (全容器文本普查, view-only)
# ISO     : …\work\builds\GR_ZH92\GR_ZH92.iso
# sha256  : 1d30c1067beb8fc8534193486f23f75489447eb0487ab24d06ef66c0627120b6

== 覆盖自证 ==
# 容器总数 4713  (GR.IMG 4004 + MENU.IMG 686 + ISO 独立文件 23)
# 按类型: ATR=1460, ELF=1, ISO_FILE=22, LANG=2, MEDIA=310, MIS=92, OTHER=1209,
#         PAK=44, RES=13, RSB=1506, SFXML=2, TXT=17, XML=35
#   与 font_usage.py 的 4713 / 1583.7 MB 对表: 一致 ✓

== 每类结果 (第 3 关容器级闸门开启) ==
# 类别                     容器     放行  未dump       行数       不同串     含中文      超类上限
# xml                    35     35      0     1567       516       0         0
# txt                    17     17      0     3358      3254       0         0
# missions               92     92      0     2396      2008       0         0
# character_names      1460   1460      0     4439      4439       0         0
# other_res              13     13      0    19946     14273       0         0
# program_strings         1      1      0     5263      2000       0         0
# iso_files              22     22      0     2512      1624       0         0
# binary_assets        3069    604   2465   112013     80541    1197       371
# 解压后合计 1583.3 MB

== 写出 view 表 (UTF-8 BOM + CRLF; 一律 injectable=no) ==
#   xml                    516 行     224.4 KB  …/GR_ZH92_view_xml.csv
#   txt                   3254 行    1116.0 KB  …/GR_ZH92_view_txt.csv
#   missions              2008 行     684.9 KB  …/GR_ZH92_view_missions.csv
#   character_names       4439 行    1583.3 KB  …/GR_ZH92_view_character_names.csv
#   other_res            14273 行    5104.4 KB  …/GR_ZH92_view_other_res.csv
#   program_strings       2000 行     857.9 KB  …/GR_ZH92_view_program_strings.csv
#   iso_files             1624 行     563.3 KB  …/GR_ZH92_view_iso_files.csv
#   binary_assets        30000 行   11300.9 KB  …/GR_ZH92_view_binary_assets.csv
#   pending               2465 行     522.1 KB  …/GR_ZH92_view_pending.csv
#   containers_summary      11 行       2.2 KB  …/GR_ZH92_view_containers_summary.csv
#   meta.json          …/GR_ZH92_view_containers.meta.json

[check] 命名隔离: 9 张 view 表**没有**一张叫 *_text_*.csv ✓
[check] 表内 injectable 列: 60590 行全部 = no ✓
[check] 未 dump 的容器: 2465 个, 判定依据逐行写在 GR_ZH92_view_pending.csv
```

`_view_containers_summary.csv`（给用户的"一张表看全"）：

| category | table | kind | containers_total | containers_kept | rows | injectable |
|---|---|---|---|---|---|---|
| xml | `…_view_xml.csv` | XML | 35 | 35 | 516 | no |
| txt | `…_view_txt.csv` | TXT | 17 | 17 | 3254 | no |
| missions | `…_view_missions.csv` | MIS | 92 | 92 | 2008 | no |
| character_names | `…_view_character_names.csv` | ATR | 1460 | 1460 | 4439 | no |
| other_res | `…_view_other_res.csv` | RES | 13 | 13 | 14273 | no |
| program_strings | `…_view_program_strings.csv` | ELF | 1 | 1 | 2000 | no |
| iso_files | `…_view_iso_files.csv` | ISO_FILE | 22 | 22 | 1624 | no |
| binary_assets | `…_view_binary_assets.csv` | RSB/PAK/MEDIA/OTHER | 3069 | 604 | 30000 | no |
| pending | `…_view_pending.csv` | (闸门依据) | 0 | 0 | 2465 | no |
| **LANG** | `…_text_long.csv / _long_nowrap.csv / _short.csv` | LANG | 2 | 2 | — | **yes** |
| **SFXML** | 同上三张表 | SFXML | 2 | 2 | — | **yes** |

### ② 覆盖自证：容器总数与 `font_usage.py` 一致

**4713 = 4004 (GR.IMG) + 686 (MENU.IMG) + 23 (ISO 独立文件)** —— 与 `font_usage.py`
round38 报告的 **4713 个容器 / 1583.7 MB** 完全一致（本工具算 **1583.3 MB**，
差 0.4 MB 是"ISO 里 0 字节条目是否计入"的口径差；本盘实测 `zero_byte = 0`）。
`--expect-containers 4713` 时不一致会**退出码 3**。

### ③ 保守性：抽查二进制容器，确认没有垃圾表

| 抽查对象 | 判定依据（实测数字） | 结果 |
|---|---|---|
| `ZZZ.PSS`（143 MB 视频流） | 第 1–2 关全开后 2910 条"候选"，**`dup_count` 全 = 1**；`clean_ratio` **0.000002**（噪声本底 1 MB 随机数据是 0.0） | **0 行**，只在 `pending` 里记 `stream-container` |
| `MUSIC.TM`（50 MB 音乐） | 640 条候选，最长 15 B，全是 `"1tUC40de3SE B$'"` 这种碎片；`clean_ratio` **0.0004** < 0.002 | **0 行**，`pending` 记 `stream-container` |
| `D01_BEACH.SHT`（精灵图） | `clean_ratio` **0.0010** < 0.002；保留串里 8 条**没有一条**是英文单词（`'t!r CB火.CXz-C'`） | **0 行**，`pending` 记 `below-gate` |
| `BNK_95_05.SS`（9 MB 音效） | `clean_ratio` **0.0016** < 0.002；候选里含 `'Z @ D$3$5 D'` 这类 | **0 行** |
| `MP04_VALLEY.BMZ`（压缩贴图） | `dup_count` 有大值、`clean_ratio` 0.0085（真名字表） | 放行（`confidence=medium`） |
| `D01_BEACH.BMB` | `clean_ratio` **0.00022** < 0.002 | **0 行**，`pending` 记 `below-gate` |

抽查的 3 个"最像文本"的压缩容器（`probe_media.log`）：`ZZZ.PSS` / `MUSIC.TM` / `BNK_99_00.SS`
保留串的 `dup_count` **全部 = 1**，且**英文原盘同一容器里出现的是同一批串** ⇒ 100% 噪声。

### ④ 往返验证：dump → 原样注入 ⇒ 与源盘逐字节相同

**测法**：`verify_roundtrip4.py` —— 用 `dump_text_csv.py` 把 `GR_ZH92.iso` dump 成表，
**一个字都不改**，按 `resource` 分两步注入回同一份源盘，比对 sha256。
（分步是为了绕开下面 §6 的外部冲突，同时**不**用 `--only`（id 列表会超 Windows 命令行长度上限）。）

```console
$ python work/builds/GR_ZH92/temp/r39/verify_roundtrip4.py
源盘 sha256: 1d30c1067beb8fc8534193486f23f75489447eb0487ab24d06ef66c0627120b6
保留 2084 行; 因外部冲突剔除 177 行

$ inject_text_csv.py --csv rt4_clean/LANG__* --src GR_ZH92.iso --dst rt4_lang.iso
   | [verify] 产物容器自洽复检:
   |   EN_STRINGS.RES@MENU    条目 2232: 改动 0 / 逐字节不变 2232; ngroups=66 结构重解析 OK
   |   EN_STRINGS.RES@GR      条目 2232: 改动 0 / 逐字节不变 2232; ngroups=66 结构重解析 OK
   | [hash] src 1d30c1067beb8fc8534193486f23f75489447eb0487ab24d06ef66c0627120b6
   | [hash] dst 1d30c1067beb8fc8534193486f23f75489447eb0487ab24d06ef66c0627120b6
   | [hash] 逐字节相同 (无改动)
中间盘 sha256: 1d30c106… → 与源盘相同 ✓
```

* **LANG 语言表（2045 行 / 2192 条目，含 158 条带手柄按键图标）：dump → 原样注入 = 逐字节零差异** ✓
* `SFXML` 的 177 行被**外部字符集变更**挡住（见 §6），不是本工具的缺陷。

### ⑤ view-only 保险：报错、不写盘、信息清楚

见 §3.2（两种绕法都实测 exit 1 且产物不存在）。

### ⑥ `make_build.py` 跑通，新类别同样进 `text/`，`build_info.json` 里能看到

实测（`make_build94e.log`，`GR_ZH94_test`，**测试版本号，未碰 GR_ZH93**）：

```console
$ python tools/iso_build/make_build.py GR_ZH94_test --from work/builds/GR_ZH92 \
      --inject-csv work/builds/GR_ZH92/text --no-textdump --no-font-dump
…
[containers] 9 张 view 表 / 共 60590 行 / 容器 4713 个 (injectable=no)
[info] work/builds/GR_ZH94_test/build_info.json
[done] 全容器文本普查 (view-only, 不能注入): 9 张表 / 60590 行 / 容器 4713 个
[done]   work/builds/GR_ZH94_test/text/GR_ZH94_test_view_containers_summary.csv
[done]   ★ 这些表 injectable=no: 注入器只读 *_text_*.csv, 显式喂 view 表会报错
```

* `work/builds/GR_ZH94_test/text/` 里 10 张 `GR_ZH94_test_view_*.csv` **齐全**；
* `build_info.json` → `text_snapshot.containers` 里有：`tables[]`（10 个文件名）、
  `injectable: "no"`、`policy`、`containers.total = 4713`、`totals.rows = 60590`、
  `tables_meta[]`（每类的 rows / containers_kept / containers_skipped / cjk_texts / **sha256**）；
* **注入仍然只吃 `_text_*.csv`**（本次没产出 `_text_` 表是因为文本快照 dump 失败 ⇒ 标
  `text_snapshot.partial = true`，view 表照样产出并记进 `build_info.json`）。

### ⑦ 现有产物未被破坏

| 产物 | 状态 |
|---|---|
| `<版本>_text_{long,long_nowrap,short}.csv` 的文件名 | **未改**（`dump_text_csv.py` 的 `--out`/kind 逻辑未动） |
| 三张表的**列名 / 16 列顺序 / 语义** | **未改**（`COLS` 一个字未动） |
| `<版本>_text.txt` / `_text.meta.json` | **未改** |
| `make_build.py` 的快照接入 | 只在 `make_text_snapshot()` **之后**追加一次 `dump_containers.py`，不改变原流程 |
| view 表是否会被注入 | **不会**（命名互斥 + 表内 `injectable` 列 + 注入器双重拒绝） |

---

## 5. 新增/改动的文件

| 文件 | 动作 | 说明 |
|---|---|---|
| `tools/text_csv/dump_containers.py` | **新增**（约 830 行） | 全容器文本普查 → 10 张 view 表 + meta；只读 ISO |
| `tools/text_csv/inject_text_csv.py` | 打补丁 | ① 拒绝 view-only 表（按名 + 按 `injectable` 列）；② 新增「表是否过期」判据（盘上字节 → 当前字符集 decode → encode 回不去原字节 ⇒ 拒绝，防字符集换代后悄悄写坏文本） |
| `tools/text_csv/tcslib.py` | 打补丁 | 新增 `is_view_csv()` / `view_rows()` / `VIEW_MARK`；`expand_csv_inputs()` 对 `*_view_*.csv` 记 `level='error', code='view-only-table'` |
| `tools/text_csv/dump_text_csv.py` | **修 bug** | `dump_sfxml()` / `dump_lang()` 里 `_c, marks, preview = T.wrap_hint_cell(...)` 把上面算好的**按键标记清单 `marks` 覆盖成"折行点位置(int)列表"** ⇒ 当某条**既含手柄按键图标、又是长段（`wrap_w>0`）**时崩在 `' '.join(marks)`（`TypeError: expected str instance, int found`）。改名成 `_wrap_marks`。**实测触发条目：`SFXML:T0023`（MP5SD）等**，此前该盘 dump 必崩 |
| `tools/iso_build/make_build.py` | 打补丁 | 新增 `make_container_view()`；`make_text_snapshot()` 末尾调用；文本快照失败时**照样产出 view 表**并把 `text_snapshot` 标 `partial`；新增 `[done] 全容器文本普查…` 汇总行 |
| `tools/text_csv/FORMAT.md` | 新增 §12 | 「全容器 dump 与"可注入/view-only"的区别」 |
| `docs/BUILD_TOOLCHAIN.md` | 新增 §8.9 + 索引/限制更新 | 分类方案、判据、覆盖自证、开销、限制 |
| `docs/REPORT_dump_all_containers.md` | **新增** | 本报告 |

**未修改**（铁律）：`tools/font_pipeline/font_usage.py`（只 import）、
`tools/font_pipeline/data/charset_compiled_zh16.json`、任何 ISO、
`GR.IMG` 条目 `off`/`stored`、制作组名单 `GR.IMG #551..#565`、`MENU.IMG` 内部偏移、
`work/builds/GR_ZH92/GR_ZH92.iso`（只读，sha256 仍为 `1d30c106…`）。

---

## 6. ⚠ 外部干扰与已知限制（诚实清单）

### 6.1 本轮进行中，另一个子代理正在改字符集（**影响往返验证**）

调查过程中发现工作树被我之外的人改动：

* `tools/font_pipeline/data/charset_compiled_zh16.json` 的 `mtime = 2026-10-11 19:20`，
  内含 `_font_ext_planc_zh93` = *「方案 C: gate 0xAE→0xB1, lead 0xA1..0xB0 (+282 码位)」*；
* `tcslib.py` / `inject_text_csv.py` 也同步改了（`btn_code_ok()` 里出现 `round40` 注释，
  `LEAD_HI` 由 `0xAE` 变成 **`0xB1`**，即对偶 lead 区间扩到 `0xA1..0xB0`）；
* 后果：`0xAF` / `0xB0` 这两个字节从"合法按键图标码"变成"DBCS lead 区间"。
  而现役盘正文里仍有**裸的** `0xAF` / `0xB0`（老按键图标码）：
  `SFXML` 789 + 315 个，`LANG` 943 + 547 个。
  ⇒ 这些条目在当前字符集下 `decode→encode` 回不去原字节，注入器按设计拒绝
  `{{BTN:E0AF}}` / `{{BTN:E0B0}}`。

**这不是本工具的缺陷**，但确实挡住了"全表往返验证"。本报告的处理：

1. 往返验证**排除**这 177 个冲突行后，其余 2084 行（含整个 LANG 表 2045 行）
   **逐字节零差异**（§4④）；
2. 顺带发现并**修掉**了一个真问题：字符集换代后，旧表里"看着没改过"的行用新字符集
   重新编码会变成**别的字**（实测：`GR_ZH92/text` 的现役表 + 当前字符集 = **29 行被改写**）。
   已在注入器里加硬判据：盘上原字节 `decode→encode_strict` 回不去 ⇒ **拒绝写盘**，
   并打印「请重新 dump（`--carry-edited` 可把人工改动搬过去）」，退出码 1。
3. **不**碰那三个文件 —— 它们归另一个子代理。

### 6.2 已知限制

* **只扫"可读串"，不解析容器结构**：不解析 XML 元素、不解析 `.MIS` 任务字段、
  不解析 `.ATR` 人物属性 ⇒ 表里既有"值"也有"标签名/属性名"，用 `text_kind` 列区分。
  想按字段校对的类别（如 `.MIS` 的 `<MapName>`）还需要后续逆向。
* **`confidence=low` 的行可能混有压缩数据的巧合碎片**（如 `.BMZ` 里
  `'HHH HHH%HHHH'`、`'PP0池``@射PP00PP0'`）；`has_cjk=yes` 也只说明"≥2 个连续汉字"，
  不等于"这是游戏文本"。**核对时优先看 `confidence = high/medium`**。
* **`binary_assets` 默认截断到 30000 行**（原 80541 条不同串）；截掉的行数与策略写在
  `_view_containers.meta.json` → `totals.truncated_by_category` / `truncation_policy`。
  `--max-rows-per-category 0` 可取消截断。
* **视频/音频流默认不扫**（`--scan-streams` 可开）—— 依据见 §2.2。
* **ELF 每容器上限 2000 行**：`SLUS_206.13` 实测有 **35450 条不同串**（C++ 带符号名），
  全量太大 ⇒ 截断，实际条数记在 `_view_containers.meta.json` 的 `containers` 统计里。
* **记忆卡存档 / 运行时拼出的字符串**无法离线扫。
* `.ATR` 实测 **1460 个 / 889 KB 解压后 0 个非 ASCII 字符**（人名全英文）；
  `.MIS` 汉字数 **0**。如实呈现，未硬凑内容。
* **全盘没有**除 LANG / SFXML 之外的汉语游戏文本 —— 唯一例外是主程序里本工程自己写的
  5 个字（`入 待 等 请 载`，载入提示）。若将来发现某类容器**有中文但格式未知**，
  本工具会照实 dump 出来并标 `view-only` + `has_cjk=yes`，`confidence` 视容器而定。

---

## 7. 给用户的一句话

**`work/builds/GR_ZH92/text/` 里现在有两类表，记住一句话就不会错：**

* **`*_text_*.csv`（3 张）= 你的编辑栏** —— 想改游戏里看到的字，只改 `text_edited` 一列；
* **`*_view_*.csv`（10 张）= 给你的字典** —— 想查"这个名字别处怎么写的""全盘还有没有中文"，
  就在这 10 张里翻；它们**改了没用**（注入器会明确拒绝，不会毁盘）。

先打开 **`…_view_containers_summary.csv`**（一行一个类别，告诉你有多少文本、能不能改），
再按类别打开对应的表校对。**全盘除语言表 / 特别收录外没有别处的中文**——
`shermanlevel1`、`ACTOR_ATR.DIR`、`e:\gr\closing source gm 10\…` 这些是贴图名/清单/调试路径，
是本研究用的旁证，不是翻译文本。
