# 构筑工具链与 ISO 配方

> 本文件是「怎么安全地改这张盘」的唯一权威说明。所有结论都来自实机实验，
> 不是推测。新增补丁脚本前请先读完第 3 节「铁律」。

---

## 1. 盘面事实（定值，勿改）

| 项 | 值 |
|---|---|
| ISO 总大小 | 1,648,164,864 B（固定，任何情况下不得改变）|
| 扇区 | 2048 B |
| PVD | LBA 16，根目录 LBA 261，`MODULES` 目录 LBA 262 |
| `SYSTEM.CNF;1` | LBA 294 |
| `SLUS_206.13;1` | LBA 295（ELF，37,453,732 B）|
| `GR.IMG;1` | LBA 19175（1,550,563,328 B）|
| `MENU.IMG;1` | LBA 776286（58,300,882 B）|

### 地址换算

```
off(VA) = LBA*2048 + 0x80 + (VA - 0x100000)      # 文件内
off(VA) = 0x80 + (VA - 0x100000)                 # 裸 ELF
两者相差 0x93800（= GR.IMG 起始处 ELF 的偏移）
```

### IMG 容器格式

```
条目表 @0x830, 步长 48 B, 12×u32
  [6] = stored（盘上占用）  [7] = real（解压后）  [8] = off（容器内偏移）
名字表: 头部 +0x10 = 名字起点, +0x04 = 名字终点（NUL 分隔）
```

`MENU.IMG` 686 条目，`GR.IMG` 4070 条目。

### MENU.IMG 内关键位置（全版本稳定）

| 偏移 | 内容 |
|---|---|
| `0xB9120` | `FONT.RES` 槽（4421 B，LZO 压缩，展开 5942 B = 字表）|
| `0x58431` | `new_font_revised` 纹理 PAK 记录（`0x4044C` B）|
| `0x58431 + 0x44C` | 字库纹理像素平面（262,144 B，PSMT4 1024×512）|

---

## 2. 工具链

```
tools/iso_build/
  iso_tools.py      ISO9660 读取 / safe_rebuild / img_expand / verify
  make_build.py     一次性版本构筑器（本文件的主角）
  dump_font.py      版本字库 dump（图集 PNG + FT 记录表 + 字符集清单 + 汇总；只读、可复现）
  patch_zh*.py      各轮补丁脚本（python <patch> <src_iso> <dst_iso>）

tools/capture/run_opt.py   PCSX2 无头运行 + 截图 + drawlog/strlog
tools/diag/dump_all_text.py 全量文本总表
tools/font_pipeline/      字库流水线（BDF → 纹理 / 字表）
```

### 2.1 构筑一个版本

```bash
# 从最新版继承
python tools/iso_build/make_build.py GR_ZH300

# 指定基底 + 应用补丁
python tools/iso_build/make_build.py GR_ZH300 --from work/builds/GR_ZH256 --patch my_patch.py

# 扩容 MENU.IMG 内某条目（可多次），并做条目表自洽校验
python tools/iso_build/make_build.py GR_ZH300 --patch my_patch.py \
    --expand-entry STRINGS.TXT=200000 --verify-img

# 把上一轮自动产出的文本表注入（写盘前会做字库覆盖预检，缺字 ⇒ 构筑失败）
# ★ round37: 给 **text 目录**最省事 —— 该目录下所有 *_text_*.csv 全部读入
python tools/iso_build/make_build.py GR_ZH301 --from work/builds/GR_ZH300 \
    --inject-csv work/builds/GR_ZH300/text
# （只给版本名也行: --inject-csv GR_ZH300 ⇒ 自动解析到 work/builds/GR_ZH300/text/）

# 调试时跳过文本总表 / 跳过字库 dump
python tools/iso_build/make_build.py GR_ZH300 --no-textdump --no-font-dump
```

产出（**一切都在版本文件夹内**，构筑不往 `work/` 其它地方写任何东西）：

```
work/builds/<版本>/
  <版本>.iso                        完整盘
  build_info.json                   版本/基底/补丁/sha256/时间 + text_snapshot + font_dump
  text/                             本版本文本快照（每次构筑自动产出）
    <版本>_text_long.csv            ★ 长段（可写 {WRAP} 控制断点）—— 58 条
    <版本>_text_long_nowrap.csv     语言表长段（简报等，宽度未标定）—— 255 条
    <版本>_text_short.csv           按钮 / 条目名 / 短提示 —— 1948 条
    <版本>_text_locked.csv          不可编辑条目（通常 0 条 ⇒ 不产出）
    <版本>_text.txt                 合并成**一份**的轻量副本：每行 `id<TAB>正文`（换行 \n）
    <版本>_text.meta.json           各表的条数 / kind 列表 / 总条数 / 每张表的 sha256
    ★ round37 起**不再产出合并的大 CSV**（每张表仍是 16 列，表头与原大表完全相同）
  font/                             本版本字库 dump（每次构筑默认产出；--no-font-dump 可关）
    <版本>_font_atlas.png           图集可视化（0=墨 / 非 0=空；2 倍最近邻放大）
    <版本>_font_ft.csv              FT 记录表（3 个 face 的记录：码位/矩形/采样点/有没有墨）
    <版本>_font_charset.csv         字符集清单（ascii/single/pair/icon：有没有字形）
    <版本>_font_summary.json        统计 + 各文件 sha256（**无时间戳** ⇒ 同盘两次 dump 完全相同）
  temp/                             注入报告 / 全量文本总表 / 模拟器截图日志
    inject<N>_report.json           --inject-csv 第 N 步的注入报告（含「字库覆盖预检」）
    textdump/all_text.xlsx|.csv     全量文本总表（每次自动出）
  extract/ft_font_res.bin           字表（MENU.IMG @0xB9120）
  extract/font_new_font_revised.bin 字库纹理 PAK 记录
  extract/MENU.IMG                  MENU.IMG 全量（58 MB）
```

> 旧的 `work/text_versions/**`（文本归档）与 `work/tmp/**`（临时目录）**已取消写入** ——
> 版本快照只留在各自的版本文件夹里；跨版本对比用 §8.5 的 `diff_text_versions.py`
> （它在 `work/builds/<版本>/text/` 里找快照，仍可只读兜底旧的 `work/text_versions/`）。
> 未被任何工具依赖的旧目录（`work/text_versions`、`work/tmp`、`work/text_csv`、`work/archive`…）
> **可以直接删**（内容都是各版本快照的副本 / 中间态，可从版本文件夹或 ISO 重新生成）。


### 2.2 校验

```bash
python tools/iso_build/iso_tools.py work/builds/GR_ZH300/GR_ZH300.iso   # 文件树
python tools/iso_build/make_build.py ... --verify-img                   # 条目表自洽
```

`verify_img()` 检查三件事：**越界 / 未 4 字节对齐 / 条目重叠**。
当前 `GR_ZH253` 基线：MENU.IMG 686 条目、GR.IMG 4070 条目，三项均为 0。

### 2.3 运行模拟器

```bash
$env:GR_ISO = "<绝对路径>\GR_ZH300.iso"
python tools/capture/run_opt.py <TAG> <nav.txt> <maxframes> <shotinterval> <w0> <w1>
```

- `nav.txt` 里必须是**反斜杠绝对路径**
- 单次约 152–220 s
- **同一 ISO 不能并发跑两次**（`PermissionError: [WinError 32]`）

---

## 3. 铁律（违反会卡死或损坏盘）

### 3.1 绝不从零构造 ISO

RB01/RB02 两轮实验都卡在 LBA 18582。从零构造会丢掉：

- LBA 0..11 PS2 保护/授权区
- LBA 32..37 / 48..53 / 64..65 Sony 系统数据
- LBA 256..260 路径表（**PS2 cdvd 驱动必需**）
- PVD 的 `pub_id` / `app_id` / `copyright` / `created` 等字段

⇒ **必须以原盘为底，只改必要部分**（RB03 验证通过）。`safe_rebuild()` 就是这么做的。

### 3.2 IMG 条目只需 4 字节对齐

实测 `GR.IMG` **4070/4070** 条目都是 4 字节对齐，**只有 4.8% 是 2048 对齐**。
用 2048 对齐会把每个条目后面 2044 B 的空隙全部浪费掉。

⇒ 分配新空间时按 4 字节对齐。

### 3.3 条目之间的「空隙」不一定是空的

`STRINGS.TXT` 之后那个 6,285,366 B 的「空隙」有 **91.9% 非零**，是未登记的真实数据。

⇒ **必须按内容判断**（全零才算空闲），不能只看条目表算出来的缝隙。

### 3.4 RES 容器是多子流（multi-substream），布局不能动

`MENU`/`GR` 的 `.RES` 和 `.MIS` 都是固定 **16384 B** 一块的子流序列：

```
{u32 plen}{u32 osz}{LZO payload}   × N（16384 B 块）+ 余数
```

⇒ 替换 `RES` 内容时必须保持子流切分；**不能整体重排**。

### 3.5 MENU.IMG 内部偏移不可搬动

ELF 里硬编码了 MENU.IMG 内部偏移。实测：把 `.MIS` 数据搬到别处、条目表更新得
完全自洽（0 越界 / 0 重叠），**游戏仍然卡在记忆卡画面**。

⇒ `EN_STRINGS.RES` 的 `off/stored/real` 三字段**绝对不动**。
   需要增长时只能用「原地利用条目自身 slack」，不能用搬迁。

### 3.6 其它

- 绝不 NOP `0x5182EC`
- `0x21CB40` 保持英文
- 绝不写 `0xFF` 记录
- 新 cave 只能放在 RAM 验证过的全零区
- `FONT.RES` 不是文本；`.BMZ`/`.RSB`/`.PAK`/`.QOB`/`.QOZ` 是二进制资源，不当文本处理
- **字库纹理有两份副本**（MENU.IMG 和 GR.IMG）。实测引擎**只读 MENU.IMG 那份**
  （cdvd 日志：MENU 纹理区 133 次命中，GR.IMG 0 次）⇒ 改 MENU.IMG 那份。

---

## 4. 原地增长 vs 搬迁

ATR 人名加点（253 处编辑）的经验：

| 策略 | 成本 |
|---|---|
| **原地增长**（条目自身 slack 够用）| 240 处，净增 177 B |
| 搬迁到别处的全零空隙 | 13 处，共 133 KB |

⇒ **优先原地增长**：`need <= stored + slack_after` 就原地写并更新 `stored/real`，
否则才搬到已验证全零的空隙。

参考实现：`tools/font_pipeline/apply_name_dots.py`。

---

## 5. 可回收空间（已实测）

| 位置 | 大小 | 依据 |
|---|---|---|
| GR.IMG `VIDEO.RSB` 尾部 | 525,308 B | 整个 525,340 B 条目只有 9 个非零字节（官方空占位，EN 原盘相同）|
| GR.IMG `SHORTCUT.RSB` 尾部 | 103,188 B | 全零 |
| GR.IMG 全盘零空隙 | 89,101 B | 按内容判定 |
| MENU.IMG 全盘零空隙 | 76,011 B | 628 处，最大 61,236 B @58239646 |
| GR.IMG 盘尾 slack | 65,536 B | |

---

## 6. 噪声基线

同一张盘重跑，drawlog / strlog **逐字节相同**，87/87 截图相同。
⇒ 任何差异都是真实改动，可以放心用「像素差异」判定实验结果。

---

## 7. 已知未解问题

**12px 字形的纹理采样坐标。** 已确证：

- 引擎使用 MENU.IMG 的纹理（填满整张 ⇒ 文字消失）
- FT 记录决定「画哪个字形」（把 'T' 的记录换成 'U' 的 ⇒ 渲染出 U）
- 引擎采样 `v=452` 那几行（清空该带 ⇒ 文字消失）
- **但引擎采样的 `u` 不是记录里的 `u0`**：把记录指向的矩形填墨或擦成背景，
  渲染 **0 像素变化**

详见 `work/_dis/TWELVEPX_ROUND1.md`。**这是当前 12px 工作的唯一阻塞点。**

---

## 8. 文本快照与文本注入（round31 新增；round37 起文本表**按 kind 分多张**；round39 加 view-only 全容器普查）

> `tools/text_csv/dump_text_csv.py` / `inject_text_csv.py` 的**格式与换行约定**以
> `tools/text_csv/FORMAT.md` 为准（尤其 §2.2「多表布局」）；本节只讲"在构筑里怎么用"。
> 实跑记录与设计取舍见 `docs/REPORT_build_text_integration.md`（round31）、
> `docs/REPORT_build_font_dump.md`（round36：产物目录收敛 + 字库 dump）与
> `docs/REPORT_split_by_kind.md`（round37：按 kind 拆表）。

### 8.1 流水线里的位置

```
--from 基底
  → 拷基底 / --patch <补丁>
  → --expand-entry 扩容（可选）
  → ★ --inject-csv 文本注入（0..N 次，按命令行顺序；每次以"上一步的产物"为 --src）
  → --verify-img 条目表自洽校验（可选）
  → extract/ 抽取 字表 + 字库记录 + MENU.IMG
  → temp/textdump/ 全量文本总表（--no-textdump 可关）
  → ★ 版本文本快照 → text/（对**最终 ISO 本身**再 dump 一次；--no-text-snapshot 可关）
  → ★ 版本字库 dump → font/（同样对最终 ISO；--no-font-dump 可关）
  → build_info.json（含 text_snapshot 段 + font_dump 段）
```

### 8.2 每轮构筑自动产出的「版本文本副本」（都在版本文件夹内）

| 产物 | 说明 |
|---|---|
| `work/builds/<VER>/text/<VER>_text_long.csv` | ★ **长段**（可写 `{WRAP}` 控制断点）—— 58 条 |
| `work/builds/<VER>/text/<VER>_text_long_nowrap.csv` | **语言表长段**（简报等，折行宽度未标定）—— 255 条 |
| `work/builds/<VER>/text/<VER>_text_short.csv` | **按钮 / 条目名 / 短提示** —— 1948 条 |
| `work/builds/<VER>/text/<VER>_text_locked.csv` | 不可编辑条目（字节回环不稳定；**通常 0 条 ⇒ 不产出**） |
| `work/builds/<VER>/text/<VER>_text.txt` | **合并成一份**的轻量单行副本：每行 `id<TAB>正文`；换行 `\n`、制表 `\t`、反斜杠 `\\` |
| `work/builds/<VER>/text/<VER>_text.meta.json` | 各表条数 / kind 列表 / 总条数 / 每张表的 sha256（dump 工具自己写） |
| `build_info.json` → `text_snapshot` | `tables[]`（每张表的 path / kind / rows / bytes / sha256）+ `kinds` + `tables_total_rows` + TXT 的路径与 sha256 + 条目数 / 长段数 / 字符数 / 中文字数 |

* **每张表的表头与列完全不变**（16 列，与拆分前的大表逐字符相同），只是行按 `kind` 分开；
  **合计条数不变**（58 + 255 + 1948 = 2261）。某一类 0 条时**照样产出只有表头的空表**。
* **不再产出合并的大 CSV**（避免"改了一张、另一张没改"的歧义）；TXT 快照仍**合并成一份**，
  且行序 = dump 的自然顺序（LANG → SFXML）⇒ 从大表切到多表后 **TXT 逐字节不变**
  （实测 sha256 `ae60f337…`，见 `REPORT_split_by_kind.md`）。
* TXT 里的 `{WRAP}` 现在**渲染成真换行**（视图 = 盘上的换行；round36 是"删掉标记"，
  那会让视图凭空少掉换行）—— 这一条同时修掉了 FORMAT.md §9 里记的"待改进"。
* 快照 dump 的是**刚产出的最终 ISO 本身**（补丁 / 扩容 / 注入全部做完之后），所以它反映"这一版盘里真实的文本"。
* 实测开销：2261 条约 **1.3–3 s**（1.65 GB 的盘，SSD）；TXT 由同一次 dump 派生，不额外读盘。
  整个版本构筑（含 1.65 GB 拷贝 + sha256 + 全量文本总表 + 文本快照 + 字库 dump）实测 **60–70 s**。
* 快照失败（例如 dump 的解码口径自检不过 / 多表里同一个 id 冲突）⇒ **构筑以非 0 退出**，ISO 保留，
  `build_info.json` 里记 `text_snapshot_error`。
* `--no-text-snapshot` 可关（**默认开启**）。
* ★ round39：`<VER>/text/` 里还会多出 **9 张 view-only 表** `<VER>_view_*.csv`
  （全容器文本普查，`injectable=no`，**只读不参与注入**）—— 见 §8.9。
  它们**照样在 `text/` 里**，因为注入器 `--csv <目录>` 只扫 `*_text_*.csv`，扫不到 `_view_*.csv`。
* ⚠ **不再写 `work/text_versions/**`**（round31–35 的归档位已被取代）：每轮快照只在
  `work/builds/<VER>/text/`。该旧目录现在没有任何工具依赖，**可以整目录删除**；
  真删掉之后，旧版本的快照就只能从它自己的 ISO 重新 dump（`diff_text_versions.py <ISO> <版本>` 支持）。
* ⚠ `work/**` 在 `.gitignore` 里（仓库"游戏衍生数据不入库"策略）⇒ 文本副本是本地产物，
  跨版本对比请用 §8.5 的工具，而不是 git diff。

### 8.3 注入是构筑的一等步骤（`--inject-csv`）

```powershell
# 最常用：继承上一版 + 打补丁 + 把上一版的文本注入（★ 给 **text 目录**最省事）
python tools/iso_build/make_build.py GR_ZH93 --from work/builds/GR_ZH92 `
    --patch tools/iso_build/patch_zh93.py `
    --inject-csv work/builds/GR_ZH92/text

# 版本名也行（自动解析到 work/builds/GR_ZH92/text/ 这个**多表目录**）
python tools/iso_build/make_build.py GR_ZH93 --from work/builds/GR_ZH92 --inject-csv GR_ZH92

# 只给其中几张表（注入器 --csv 支持多值；没给到的 kind 一个字都不动）
python tools/iso_build/make_build.py GR_ZH93 --from work/builds/GR_ZH92 `
    --inject-csv work/builds/GR_ZH92/text/GR_ZH92_text_long.csv

# 连续注入多份（按命令行顺序；每一份都必须匹配"上一步的产物"）
python tools/iso_build/make_build.py GR_ZH93 ... --inject-csv a.csv --inject-csv b.csv

# 调试：只注入指定 id（透传给 inject_text_csv.py --only）
... --inject-csv a.csv --inject-only LANG:G001.I000
```

* 每一步 = `inject_text_csv.py --csv <目录或表> --src <当前产物> --dst <下一产物>
  --report work/builds/<VER>/temp/inject<N>_report.json`，成功后原子替换当前产物。
* `--inject-csv` 的参数解析顺序（`resolve_inject_input`）：直接给的文件/目录（目录里没表就再看它的
  `text/`）→ `work/builds/<版本>/text`（**多表目录**，推荐）→ `work/builds/<版本>/text/<版本>_text.csv`
  （老布局的大表）→ `work/builds/<版本>/<版本>_text.csv` → `work/text_versions/<版本>_text.csv`（旧归档，只读兜底）。
* **多表按 `id` 合并**：同一个 id 出现在两张表里、`text_edited` **不同** ⇒ 注入器 **exit 1 且不写盘**
  （"改了一张、另一张没改"的歧义，工具不替你选）；相同则去重放行。合并实现与 dump/对比工具共用
  `tools/text_csv/tcslib.py`。
* **注入失败 ⇒ 构筑立即中止（非 0 退出）**，注入器的完整输出（含「字库覆盖预检」一节）
  原样打进构筑日志；`build_info.json` 记 `failed` / `failed_stage` / `inject_report`：
  * **退出码 3** = 字库覆盖预检不通过（缺字）——注入器**没有写任何盘**，缺字清单会逐条列出；
  * **退出码 1** = 结构性错误（表与源盘 `offset/len` 不符 / 超槽 / 回读不符 / 标记写错 /
    多表里同一个 id 的 `text_edited` 不一致）。
* ⚠ 多份表/目录必须**按顺序各自匹配上一步产物**：注入会改变同一容器里后续条目的 `offset`，
  拿基底的表当第二份会被注入器拒绝（有意的保护）。实际做法就是"上一轮构筑自动产出的
  `<VER>/text/` 拿来当这一轮的 `--inject-csv`"。
* 本工具**不提供 `--force` 透传** —— 缺字必须让构筑失败，不许静默写出空白方块。

### 8.4 改文案的标准动作（给非程序员）

1. 正常构筑一轮：`python tools/iso_build/make_build.py GR_ZH93 --from work/builds/GR_ZH92 --patch ...`
2. Excel 打开这一轮**自动产出**的 `work/builds/GR_ZH93/text/`，**按你要改的内容挑表**：
   * `GR_ZH93_text_long.csv` —— 长段（**可以写 `{WRAP}` 控制断点**）；
   * `GR_ZH93_text_long_nowrap.csv` —— 语言表长段（简报/说明）；
   * `GR_ZH93_text_short.csv` —— 按钮 / 条目名 / 短提示（别加换行）。
   **只改 `text_edited` 一列**（换行直接敲回车；`{{BTN:XXXX}}` 标记原样保留）。
3. 下一轮把它交给构筑器：
   `python tools/iso_build/make_build.py GR_ZH94 --from work/builds/GR_ZH93 --inject-csv work/builds/GR_ZH93/text`
   （也可以简写成 `--inject-csv GR_ZH93`）
4. 构筑器**写盘前**做字库覆盖预检：有缺字就**拒绝并中止**，把"哪个字 / 在哪一条 / 怎么办"打给你看 —— 改完再来一次。
5. 成功之后，`work/builds/GR_ZH94/text/GR_ZH94_text.txt` 就是这一版盘里的真实文本（不用再手工 dump）。

### 8.5 对比两版文本

```powershell
python tools/text_csv/diff_text_versions.py GR_ZH92 GR_ZH93        # 按 id 对齐, 列出 改/增/删
python tools/text_csv/diff_text_versions.py GR_ZH92 GR_ZH93 --out temp/diff.txt
python tools/text_csv/diff_text_versions.py --list                 # 看有哪些版本可比
```

* 版本名依次在 `work/builds/<版本>/text/`、`work/builds/<版本>/`（旧布局）、
  `work/text_versions/`（更早的归档，只读兜底）里找快照；
  也可以直接给 CSV / TXT / **多表目录** / 构筑目录 / ISO 路径（给 ISO 会在**系统临时目录**里临时 dump，
  **不动 ISO**，也不再往 `work/tmp/` 写东西）。
* ★ round37 多表支持：一版是**多张表**时（`text/<版本>_text_<kind>.csv`），先**按 `id` 合并**再比对
  ⇒ **输出格式与单表时完全一样**。优先用合并 TXT（一份、视图一致）；没有 TXT 就用多表合并。
  同一个 id 在两张表里 `text_edited` 不一致时打显著告警并按先给的那张为准（只读工具；
  注入器遇到同样情况会直接拒绝注入）。
* **只读**：不写 ISO、不改任何 CSV。控制台默认每节最多 60 条（`--limit`），`--out` 写的文件始终完整。
* 输出含：增/删/改条数、条目数/字符数/中文字数变化，以及每条改动的行级 `- 旧 / + 新`。


### 8.6 取舍与已知限制

* 快照给的是 **dump 的渲染视图**（`text_edited`，其中的 `{WRAP}` 渲染成真换行），与盘上字节
  不是一一对应 —— 这正是人工编辑所需的形态，但**不要**把它当"字节级 diff"用（字节级证据请用
  `inject_text_csv.py` 自带的「全盘差异窗口」断言）。
* **TXT 与多表 CSV 的口径一致**（都取 `text_edited`、都把 `{WRAP}` 当换行）⇒ 同一版的两者
  内容相同；但若有人**手工改了表还没重新构筑**，TXT 就是旧的 ——
  此时 `diff_text_versions.py` 会提示"多表 CSV 比 TXT 更新"，并告诉你可以直接把表目录给它。
* 老格式（`text-csv/1` `text-csv/2`）CSV 的空行语义见 `tools/text_csv/FORMAT.md` §3.6。
* 快照只覆盖 `dump_text_csv.py` 能看到的资源（`LANG` 语言表 + `SFXML` 特别收录 XML，2261 条）；
  盘里其它文本（其它 RES 字符串表、ELF 内字符串、纹理字幕）仍不在此列，见 `docs/REPORT_csv_text_tool.md`。
* `--inject-csv` 给**目录**时会读入目录里**所有** `*_text_*.csv` —— 这是刻意的（不会漏表），
  但也意味着你**不能**靠"把一张表移出目录"来排除它；要只注入一部分请显式给那几个表文件。

### 8.7 版本字库 dump （`font/`，本轮新增）

```powershell
# 正常构筑就会产出；想单独重跑：
python tools/iso_build/dump_font.py --iso work/builds/GR_ZH93/GR_ZH93.iso `
    --out work/builds/GR_ZH93/font --prefix GR_ZH93 [--scale 2] [--no-png]
```

| 文件 | 内容（列/字段） |
|---|---|
| `<VER>_font_atlas.png` | 图集 1024×512 按 **0=墨→黑 / 非 0=空→白** 二值化，默认 2 倍最近邻放大（约 46 KB） |
| `<VER>_font_ft.csv` | `face,face_name,index,code,advance,u0,v0,u1,v1,slot_x,slot_y,ink_px,has_ink` |
| `<VER>_font_charset.csv` | `char,unicode,kind,bytes_hex,slot,cell_x,cell_y,cell_legacy_x,cell_legacy_y,has_glyph,glyph_basis,note`（`kind` = ascii/single/pair/icon） |
| `<VER>_font_summary.json` | **`capacity` 容量/用量段** + face 数 / 记录数 / 字符数 / 有字形 / 缺字形 / 图集尺寸与哈希 / `grid` 引擎格配方 / `grid_selfcheck` / 各文件 sha256 |

* ★ **round41 起 `cell_x/cell_y` 是「引擎真实采样处」**（对偶 = 引擎格位公式
  `x=16*((col+PHI[row])%64)`、回绕列 `y+1`；单字节/ASCII = FT 记录矩形做行相位校正后的位置）。
  旧口径 `x=4+16*col` **在 1504/1504 个 slot 上都与真格不同**，只作对照留在
  **`cell_legacy_x` / `cell_legacy_y`** 两列里（实测与改版前的 `cell_x/cell_y` 逐行全等）。
  `glyph_basis` 标明判定依据（`ft_record` / `atlas_cell` / `engine_icon`）。
  公式、证据与置信度见 `tools/text_csv/FORMAT.md` §6.5.1 与
  `docs/REPORT_dump_font_capacity.md`。
* ★ **容量/用量**（`summary.json::capacity` + 终端「字库还能装多少字」一栏）：
  对偶**容量/已用/空位/引擎格真空可直接用/需先回收** + 单字节已用与剩余（含被手柄图标码
  占掉的字节）+ 两套字符总数口径（charset / dump）+ 图集占用率。
  **全部按当前 charset 与 `tcslib` 常量动态算，不写死任何数字**（lead 上界一变自动跟着变）。
  实测 GR_ZH93：容量 1504 / 已用 1319 / 空位 185 / 直接可用 **45** / 需回收 140；
  单字节已用 108、可用 **0**（仅剩的 `B1 B5 E7 F1` 是 `{{BTN:…}}` 手柄图标码）。
* `grid_selfcheck`：把刚写出的 CSV **读回来**，对**全部 slot**（现役 1504 个）逐个复核
  引擎格位公式，不一致即打印 `[font][warn] !!` 并记进 `notes`。
* **全部口径复用 `tools/text_csv/tcslib.py`**（`parse_ft_faces` / `parse_pak_records` /
  `atlas_cell_xy_engine` / `GlyphCache`），没有重新逆向任何格式；`has_ink` = 引擎真画得出来吗
  （记录矩形 / `+4,+2` 实测偏置矩形 / ±邻域 三处任一有墨），`has_glyph` 用 `GlyphCache` 的原判据
  （对偶码走 `atlas_cell_xy_engine`，单字节/ASCII 走 FT 记录表）。
* **可复现**：四件套都不含时间戳 —— **同一个 `font/` 目录**下对同一 ISO 两次 dump，sha256 完全相同（实测）。
  唯一的例外是 `summary.json` 里记了输出路径 ⇒ 换 `--out` 目录 dump 时它的 sha 会变（另三个文件不变）。
  `build_info.json` 的 `font_dump` 段记路径 + sha256 + 计数。
* 已知限制：
  * `has_glyph` 对**单字节/ASCII** 只查 `FONT.RES` 的 **default face**（`GlyphCache` 的既有口径）
    ⇒ 小写 `a-z` 会报"缺字形"，但引擎的 ASCII 单字节路径在别的 face 有字形、实机可读
    （`docs/FONT_CURRENT_STATE.md`、`FORMAT.md` §6.4）。**这一类只当告警看**。
  * `kind=icon` 是「字符表未映射、引擎直接给 UV 画图标/特殊符号」的字节（现役 4 个：
    `0xB1 0xB5 0xE7 0xF1`）。**语义未逆向**，`0xE7/0xF1` 很可能是重音字母而非按键（round34 旁证）。
  * 只 dump `MENU.IMG` 侧的字库（引擎**只读这一份**；`GR.IMG` 侧是死拷贝）。
  * PNG 是纯二值化、没画网格线（保证"黑=墨"可以逐像素反推）；网格几何在 `summary.json::grid`。
  * ★ **PHI 行相位表是实证拟合**（785/1297 逐像素满分，不是从反汇编完整推出的）；
    row 24 的相位 = 0 是本轮用该行 6 个字形模板比对本轮实测的（见报告 §置信度）。
    换盘 / 图集被重铺后必须**重新拟合**，否则 `cell_x/cell_y` 会整体偏移。
  * ★ 对偶码的"有字形"判据 = **「引擎格第 1..15 行有墨」**（剔掉第 0 行的 1 行渗漏：
    回绕列字形低 1 行，最后一行会落进下一行格的第 0 行）。实测现役盘 1319/1319 不受影响，
    而 `GR_ZH92` 上正确暴露出 **22 个真缺**的字。判据只保证"不是空白"，
    **不保证字形完整** —— 发布前把关请用模板比对（`docs/REPORT_dump_font_capacity.md`）。
  * ★ **同一份 charset 配不同基盘结论不同**：现役盘 `GR_ZH93` 上 1319/1319 全有字形，
    换 `GR_ZH92` 当 `--src` 会真缺 22 个（全在 atlas row 19，57 字扩容那一轮才铺的）
    ⇒ 构筑基盘要钉在 `GR_ZH93`/`GR_ZH93planc` 这一支。

### 8.8 字库用量核算 + 码位/格位回收（`tools/font_pipeline/font_usage.py`，round38 新增）

**它补的是工具链缺的那一半。** `inject_text_csv.py` 的字库覆盖预检**只做加法**：
只统计"要写入的文本里、字库没有的字"（缺字），**从不统计**"字库里有、但全盘已经不再使用"
的字（闲置）。于是字库只增不减 —— 改一次译就多几个字，老字永远占着码位与图集格位。
本工具做**减法**：全盘扫一遍，算出哪些字真的不再被用到、能腾出多少格位。

```powershell
# ① 只核算「字库 vs 全盘用量」（不读文本表）
python tools/font_pipeline/font_usage.py --iso work/builds/GR_ZH92/GR_ZH92.iso

# ② 完整核算（含新文本缺字清单）+ 两份报告
python tools/font_pipeline/font_usage.py --iso work/builds/GR_ZH92/GR_ZH92.iso `
    --text-dir work/builds/GR_ZH92/text `
    --md <报告.md> --json <报告.json>

# ③ 看回收方案（**不写任何文件** —— dry-run 是默认）
... --apply --dry-run

# ④ 真落盘（必须二次确认；写出**新** charset JSON，绝不覆盖原文件）
... --apply --yes-really --out-charset <新文件.json> --out-plan <重排计划.json>

# ⑤ 回收后自检（用回收后的 charset 重新扫一遍盘）
... --apply --dry-run --verify
... --charset <新文件.json> --verify

# ⑥ 工具自检（格位公式 / 解码口径 / 不变式，秒级）
python tools/font_pipeline/font_usage.py --selfcheck
```

#### 8.8.1 四级证据（全部可复现，不是猜）

| 级别 | 是什么 | 判据 |
|---|---|---|
| **E0 结构化文本** | `LANG` 语言表（`tcslib.parse_lang` 逐条正文）+ `SFXML`（`tcslib.parse_sfxml` 逐条 `<text>`） | 引擎**真正会画出来**的字，无阈值 |
| **E1 其它文本容器可读串** | `XML/TXT/MIS/ATR/RES/ELF/其它 ISO 文件` 里长度 ≥ 4 的"像文本的字节串" | charset 感知扫描 |
| **E2 非文本容器可读串** | `RSB/PAK/MEDIA/OTHER`（贴图/打包/视频音频）里长度 ≥ `--min-run`(16) 的可读串 | 同上，但**分开统计** |
| **E3 原始字节** | 编码在任意上下文的原始字节里出现过 | **无信息量**，只作对照 |

**回收判据**（`--policy`）：`text`（默认）= 不在 E0/E1/E2；`strong` = 不在 E0；
`strict` = 不在 E0/E1/E2/E3（实测 = 0 个，见下）。

#### 8.8.2 ★ 假阳性对照：把噪声变成**可测量、可证明**的东西

`--control-iso`（默认 `work/builds/GR_EN_ORIG/GR_EN_ORIG.iso`）给的是**英文原盘**。
英文盘里没有中文 ⇒ 任何"在英文盘里被命中的中文字"**必然是巧合**。本工具逐容器比对：

```
某容器的证据 = 中文盘在该容器里的命中  −  英文盘在**同一个容器**里的命中
```

* 容器**逐字节相同** ⇒ 两边命中集合逐元素相同 ⇒ 减完是空集（**可证明**该容器不含中文信息）；
* 容器不同（本地化动过）⇒ 只有"英文盘没有、中文盘才有"的命中才算证据。

实测（GR_ZH92 vs GR_EN_ORIG，4713 个容器）：**相同 4683 / 不同 30**。那 30 个里除
`LANG`/`SFXML` 外（字库 `FONT.RES`/`COMMON.PAK`、20 个本地化贴图、`NTSC_IKE.RES`、
`EN_STRINGS.TXT`、主程序 `SLUS_206.13`），**减完一个新字都不剩**。

#### 8.8.3 实测结论（现役盘 GR_ZH92，构筑期 charset 1357 字）

| 项 | 值 |
|---|---|
| 扫过的容器 | **4713** 个（GR.IMG 4070 + MENU.IMG 686 + ISO 文件 23） |
| 原始字节 / 解压后内容 | 1546.9 MB / **1584 MB** |
| E0 确证在用（字库内） | **1206** 字 |
| E1 相减后 | 1206 字（**比 E0 多 0 个** ⇒ 其它文本容器没有独立贡献） |
| E2 相减后 | **0** 字（该级别原始命中 1315 字，英文盘也命中 1315 字 ⇒ 全是噪声） |
| 全盘闲置（字库 − E0） | **151** 字 |
| — 其中**合法对偶**（真能腾格位） | **14** 字 |
| — 其中**死 pair**（lead ≥ 0xAE，引擎读不了） | **137** 字 |
| 新文本缺字（`--text-dir`） | 151 个（非 ASCII **70** 个） |
| — ★「盘上没用到、但新译文要用」⇒ **不许回收** | 6 个（`± 延 志 普 略 米`） |
| 可回收（且新译文不需要） | **145** 字 = 合法对偶 **13** + 死 pair **132** |
| 回收后可用对偶格位 | 78 + 13 = **91** ≥ 70 ⇒ **够用，余 21** |

> ★ **"新译文保护"是硬要求**：回收是为了给新字腾格位，把新字自己要用的字回收掉是
> 自相矛盾的（它会同时出现在"缺字清单"和"可回收清单"里）。实测确实有这种字
> （现役盘 6 个），本工具一律拦住。没有这道保护，可回收量会被虚报成 151。

> ★ **别把"可回收 145 个字"当成"多出 145 个格位"**：其中 132 个是死 pair
> （lead `0xAE/0xAF/0xB0`），而引擎的判据是 `sltiu lead, 0xAE`（只认 `0xA1..0xAD`），
> 解码器**永远不会**产出它们 ⇒ 摘掉是**打扫卫生**，不增加可用格位。
> 真正的增量只有 **13 个**。人名用字 `兰 冈 凡 刘 俊 傅 勃 卜 …` 全是死 pair；
> 只有 `丁 丹 丽 乔 亨 伟 伯 佐` 等 8 个是合法对偶。

#### 8.8.4 为什么"在全盘字节里搜某个字的编码"是**废判据**

实测：全盘 **65536 种 2 字节组合里出现了 65536 种**（全部）。2 字节序列在 1.6 GB 里
随机命中期望值 ≈ 24000 次 ⇒ "找得到"是必然，信息量为 **0**。这会把 1357 个字**全部**
判成"在用"，一个都回收不了。正确做法就是上面的 E0 + 对照减法。

#### 8.8.5 与「只做加法」预检的关系（互补，不是替代）

| | `inject_text_csv.py` 预检（加法） | `font_usage.py`（减法） |
|---|---|---|
| 问的问题 | "**要写的文本**里有字库没有的字吗？" | "**字库里有**全盘不再用的字吗？" |
| 输入 | 要写入的 CSV 行 | 整张盘 + 字符集 |
| 输出 | 缺字 ⇒ **拒绝写盘**（退出码 3） | 可回收字 ⇒ **释放码位/格位** |
| 时机 | **每次注入前**，秒级，是硬门槛 | 按需（改译一批之后），分钟级，是决策依据 |

两者口径**已经对齐**：本工具的 E0（直接解析盘上 `LANG`/`SFXML` 正文）与 CSV `text_zh`
列逐字**完全一致**（实测差集 `E0-only 0 / CSV-only 0`）。

**顺序**：先 `font_usage.py` 算出"能腾多少、够不够"，需要时 `--apply` 出**新** charset
（+ 重排计划）→ 字库管线按计划重铺图集 → 再用 `inject_text_csv.py` 注入文本
（预检会把关）。

#### 8.8.6 不变式（回收**绝不**动到在用的字）

`--apply` 写盘前跑两条硬断言，不满足就抛异常、一个字都不写：

1. 输出 charset 里**每一个仍保留的字**，其映射与输入**逐字节相同**；
2. 被摘掉的每一个字，都**不在**"在用"集合里。

另有：`--out-charset` 与输入是同一路径时**直接拒绝**（绝不覆盖原文件）；
`--apply` 需 `--yes-really` 二次确认；`--dry-run` 是默认行为。
`--verify` 用回收后的 charset **重扫一遍盘**，三重检查（解不出来的字 / 丢映射 / 码位被改）。

#### 8.8.7 已知限制（诚实清单）

* **视频/音频流**（`.PSS/.SS/.TM/…`）只做字节级扫描 —— 引擎不会从它们里面画字，但仍按最保守口径扫了。
  （★ round39 补充：`dump_containers.py` 对这类容器的口径**更严** —— 默认**不扫**，
  因为实测里面的"候选串"全部只出现 1 次，是字符集里的字节巧合，见 §8.9.3；`--scan-streams` 可开。）
* **运行时写入的数据**（记忆卡存档、运行时拼出来的字符串）无法离线扫描。
* E1/E2 判据是"编码落在长度 ≥ 阈值的可读串内部" ⇒ 藏得**很短**的中文串会被漏判（`--min-run` 可调）。
* `.ATR` 实测 **1460 个文件 / 889 KB 解压后一个非 ASCII 字符都没有**（人名全是英文）；
  `.MIS`/`.XML`/`.TXT` 也实测无中文证据。仍逐字节扫是为了将来回填中文时不漏。
* `SFXML` 只解析 `<text>…</text>` 正文（与 dump/inject 同口径）。
* 本工具**不改**字库图集 PNG / FT 记录表 —— 回收后要生效还得由字库管线重铺图集。
* 字符集 JSON 里的 `grid` 块写的是 **13px 时代**的几何（`ncol=37/cw=ch=13/skip_row=14`），
  与 16px 图集实际用的 **62×16/skip_row=12** 不一致；本工具一律按 62×16 公式算格位
  （与 `tcslib.atlas_cell_xy` / ELF cave 逐位一致，并已与 `font/…_font_charset.csv`
  里的 `slot/cell_x/cell_y` **1281 条逐条比对通过**）。`grid` 块原样保留不动。
  * ⚠ **round41 补注**：这里比的 `tcslib.atlas_cell_xy` 是**legacy 口径**（`x = 4+16*col`），
    它**不是引擎真实格**。引擎格现在由 `tcslib.atlas_cell_xy_engine()` 给
    （行相位 + 64 格回绕，见 §8.7 与 `tools/text_csv/FORMAT.md` §6.5.1）。
    本工具（`font_usage.py`）**本轮未改**，`slot_cell()` 仍是 legacy 口径 ——
    它自己的 `--selfcheck` 有一行是"`slot_cell()` 与 `tcslib.atlas_cell_xy()` 逐位一致"，
    两个名字保持同一口径才没把那一行打红。要用引擎格请改用 `atlas_cell_xy_engine()`。

---

### 8.9 ★ 全容器文本普查（view-only 表，round39 新增）

**用户要的是什么**：「一张表看全游戏里所有文本，并且能按类别分开校对」。

`dump_text_csv.py` 只覆盖 **2 类**资源（LANG 语言表 + SFXML 特别收录，共 2261 条），
而盘上**有 4713 个容器**。round39 补上其余全部：

```powershell
# 单独跑（默认写到 <ISO 同目录>/text/<版本>_view_*.csv）
python tools/text_csv/dump_containers.py --iso work/builds/GR_ZH92/GR_ZH92.iso

# 跟 dump_text_csv.py 同一个基准名（构筑器就是这么调的）
python tools/text_csv/dump_containers.py --iso <盘> `
    --out-base work/builds/GR_ZH92/text/GR_ZH92_text.csv

# 只看统计不写文件 / 放宽闸门排查 / 每类最多 3 万行
... --stats        ... --no-gate        ... --max-rows-per-category 30000
```

**构筑器自动产出**（不用手工跑）：`make_text_snapshot()` 跑完 `dump_text_csv.py` 之后，
接着跑一次 `dump_containers.py`（`--out-dir <VER>/text --prefix <VER> --max-rows-per-category 30000`），
结果记进 `build_info.json` → `text_snapshot.containers`
（`tables_meta[]` 每张表的 rows / containers_kept / containers_skipped / cjk_texts / sha256
+ `containers.total`（4713）+ `totals.rows` + `injectable: "no"` + `policy`）。

#### 8.9.1 ★ 安全红线：view 表**绝不能**被注入

| 防线 | 机制 | 实测 |
|---|---|---|
| ① 命名隔离 | view 表叫 `<VER>_view_<类别>.csv`，注入器自动扫描的是 `*_text_*.csv` | 给 `--csv work/builds/GR_ZH92/text`（目录里同时有 `_text_` 与 `_view_`）⇒ **只读 3 张 `_text_`**，view 表扫不到 ✓ |
| ② 显式拒绝（按名） | `tcslib.is_view_csv()` 命中 `_view_` ⇒ `level=error, code=view-only-table` | `--csv …_view_xml.csv` ⇒ **exit 1、未写任何盘**、打出"为什么拒绝 + 怎么办" ✓ |
| ③ 显式拒绝（按内容） | 表里有 `injectable` 列且值 = `no` ⇒ 拒绝 | 把 view 表**改名**成 `RENAMED_text_evil.csv` ⇒ 仍 **exit 1、未写盘** ✓ |
| ④ 产出端硬断言 | dump 写盘前断言文件名**不含** `_text_`、且含 `_view_<类别>`、且表头有 `injectable` 列 | `check_names()` ✓ |

> **为什么不给 view 表加 `--force` 开关**：那些容器的格式没被逆向，注入器**没有**
> `id`/`entry_index`/`offset`/`len_bytes` 这些定位列可依据 —— 就算强行写也不知道往哪写。
> 所以这是**硬拒绝**，不给绕过的口子。

#### 8.9.2 分类方案（8 类 + 1 张闸门依据表）

见 FORMAT.md §12.2 的表。一句话：按「**容器类型 × 文本形态**」分 8 张，
外加 `_view_containers_summary.csv`（先看这张）与 `_view_pending.csv`（没 dump 的容器 + 判定依据）。

#### 8.9.3 文本判据（4 关；阈值实测标定，不是拍的）

| 关 | 判据 | 默认阈值 |
|---|---|---|
| 1 可读串 | 连续 N 字节落在扫描字母表（ASCII 可打印 + 本盘单字节码 + 对偶 lead/trail + 按键字节） | 结构化容器 6 B / 二进制容器 8 B |
| 2 像文本 | 纯 ASCII ⇒ 字母数字占比 ≥ 0.70；含高位字节 ⇒ 可见字符 ≥ 0.85 且字母数字 ≥ 0.55 且含汉字；无私有区回落；同字符连续 ≤ 8；长度 ≥ 16 要有标点；无长度 4 的重复子串 | 见左 |
| 3 **容器级闸门**（只对 `RSB/PAK/MEDIA/OTHER`） | `distinct` ≥ M **且** `score`（不同串/MB）≥ S **且** `clean_ratio`（干净 ASCII 串字节/容器字节）≥ C | M=10, S=10, C=0.002 |
| 4 每容器上限 | 去重后最多写出的串数；超了按 `confidence` 高→低排序后截断并记数 | 2000 条 |

**阈值依据（全部可复现，`work/builds/GR_ZH92/temp/r39/`）**：

* 纯随机数据 **1 / 4 / 16 MB** 在第 1–2 关全开下的 `score` 只有 **1.0 / 0.2 / 0.6 每 MB**；
* 压缩/流式容器：`ZZZ.PSS`（143 MB）`clean_ratio` **0.000002**；`MUSIC.TM`（50 MB）**0.0004**；
  `BNK_*.SS` **0.0009**；压缩贴图 `.BMZ` 0.003–0.008；
* 真文本容器：`.MIS` `clean_ratio` **0.0047** / `text_ratio` **1.00**；名字表 `.DIR` **0.94**；
  `.TXT` **0.31**；`.RES` **1398 串/MB**；`.XML` **0.92**；
* 视频/音频流（`.PSS/.SS/.TM/.MPG/.M2V`）**默认不扫**（`--scan-streams` 可开）：
  实测里面的"候选串"**全部只出现 1 次**（`ZZZ.PSS` 2910 条候选的 `dup_count` 全是 1），
  是本盘字符集里的字节巧合，**不含可本地化文本**。

#### 8.9.4 覆盖自证

`dump_containers.py` 复用 `font_usage.py` 的容器枚举（**只 import，不改那个文件**），
所以两边算出来的容器数必须一致 —— 实测 **4713 = 4004 (GR.IMG) + 686 (MENU.IMG) + 23 (ISO 独立文件)**，
解压后 **1583.3 MB**（`font_usage.py` round38 报告 1583.7 MB，差 0.4 MB 是
"ISO 里 0 字节条目是否计入"的口径差）。给 `--expect-containers 4713` 时不一致会**退出码 3**。

#### 8.9.5 开销

扫全盘 4713 个容器 / 1583 MB 解压后内容，实测 **约 4 分钟**（SSD）；
只读 ISO，不写任何 ISO / 字符集 / 字库文件。
构筑器里它跑在文本快照之后，**失败不影响构筑**（只记 `text_snapshot.containers.error`）；
文本快照本身失败时也会**照样产出 view 表**并标 `text_snapshot.partial = true`。

#### 8.9.6 已知限制（诚实清单）

* **只扫"可读串"**，不解析任何容器结构（不解析 XML 元素、不解析 `.MIS` 任务字段）
  ⇒ 表里既有值也有标签名，用 `text_kind` 列区分。
* 二进制容器的 `confidence=low` 行**可能混有压缩数据的巧合碎片**；
  `has_cjk=yes` 也只说明"≥2 个连续汉字"，不等于"这是游戏文本"（详见 FORMAT.md §12.5）。
* 视频/音频流不扫（默认）；记忆卡存档/运行时拼串无法离线扫。
* `binary_assets` 默认按 `--max-rows-per-category 30000` 截断（原 80541 条不同串），
  截掉的行数与策略写在 `_view_containers.meta.json` 的 `totals.truncated_by_category`。
* 全盘**没有**除 LANG/SFXML 之外的汉语文本（除主程序里本工程自己写的 5 个字）——
  详见 FORMAT.md §12.5 与 `docs/REPORT_dump_all_containers.md`。




---

## ★ round42 追加：手柄图标码总表（并**更正**上文 `kind=icon` 的口径）

> **一句话**：引擎的「文本图标码」**只有 2 个** —— `0xB1`=△ 三角键、`0xB5`=✕ 叉键。
> 它们是绘制函数 `RSFontMgr::DrawString` v1 里**写死的两个 `if`**（ELF 0x219C08/0x219C14/…），
> 所以**不存在**"更多没找到的图标码"。

### ⚠ 对上文的一处更正

上文字库 dump 一节里写「`kind=icon` 是「字符表未映射、引擎直接给 UV 画图标/特殊符号」的字节
（现役 4 个…）」——**这已经不准确了**，round42 起：

| 口径 | 旧 | **新（round42）** |
|---|---|---|
| `kind=icon` | 全部未映射字节（现役 4 个） | **只有引擎真认的图标码**（`0xB1`/`0xB5`，2 个） |
| 其余未映射字节 | 混在 `icon` 里 | `latin1`（`0xE7`=ç / `0xF1`=ñ，**是字母不是图标**）/ `unmapped`（空字节） |
| 「有没有图标码没被文本用到」 | 看不出来（只报文本里出现过的） | `summary.json` 的 **`icons`** 一节列出**全集**（含没用到的）+ 候选字节枚举 |

### 新增 / 改动

| 文件 | 改动 |
|---|---|
| `tools/text_csv/icon_table.py` | **新增**：图标码总表 + 查询接口 + 候选枚举 + 自检（可单跑：`python tools/text_csv/icon_table.py`） |
| `tools/text_csv/tcslib.py` | **新增**查询接口 `icon_info/icon_key/icon_name/all_icons/engine_icon_bytes/candidate_icon_bytes/describe_icon_byte/icon_summary_lines`。**`{{BTN:XXXX}}` 格式、区间、编解码、字库预检口径零变化** |
| `tools/iso_build/dump_font.py` | ① `icon_bytes()` 改为「`0xB1..0xFF` 里未被字符集占用的字节 ∪ 旧 `SINGLE_BAND` 未映射字节」（**1 个都不少**），引擎图标码排最前；② 控制台打印图标码全集 + 候选逐个解释；③ `summary.json` 新增 `icons` 一节（`engine_icon_codes` / `candidate_bytes` / `not_icon_codes` / `shortcut_system` / `evidence` / `how_to_read`） |
| `tools/text_csv/FORMAT.md` | 追加「★ round42 新增：手柄图标码总表」（给非程序员的人话版） |
| `docs/REPORT_icon_codes.md` | **新增**：候选清单 / ELF 证据 / 实机逐码判定 / 总表 / 已知限制 |

### 引擎侧事实（ELF `SLUS_206.13`，全部可复核）

| 事实 | 地址/证据 |
|---|---|
| 唯一的字符循环绘制入口 | `DrawString` v1 @`0x219A70`（v2/v3 只是坐标换算 + 委托） |
| 字符值只有 3 个特判：`0x20`（空格）/ `0xB5` / `0xB1` | `0x219BE8` / `0x219C08` / `0x219C14`（同函数内共 6 处比较，只涉及这两个值） |
| 图标 UV **硬编码**（不是查表） | `0xB5`→(1,198)-(21,218) @`0x219C4C..0x219C64`；`0xB1`→(25,198)-(45,218) @`0x219C70..0x219C88` |
| 图标**不吃字库**：`RSFontMgr` 有两个 UISpriteModel | `RSFontMgr::ReadResourceFile` @`0x219380` 尾部：`+40`=文字（纹理=字体资源），`+76`=图标（容量 2 quad，纹理 = C 字符串 `pda_counterparts.rsb` @VA `0x578650`） |
| `AddOneWord` 的第 6 个 `bool` 参数 = "这是图标吗" | `AddOneWord` @`0x219F50`：`t0!=0` 走 model[+76]（`0x21A078`），否则走 model[+40] |
| 玩家看到的**其它**手柄图标（△○✕□/左右键…）来自 UI 快捷键系统 | `kShortcutDefaultTC(unsigned int index, int)` @`0x2BEFE0`：一张 32 项的 switch，按**动作编号**取 UV，**与文本字节无映射关系** |

### 候选字节（本盘 `GR_ZH93` / `GR_ZH96_icon`）

`0xB1..0xFF` 里没被字符集占用的字节 = **4 个**：`B1 B5 E7 F1`
（`0xB1`/`0xB5` = 图标码；`0xE7`/`0xF1` = ç/ñ）。

> ⚠ **round43 起这句要改**：`0xE7`/`0xF1` 已进 charset 的 `codes`（是拉丁字母）⇒
> 候选只剩 **`B1 B5` 两个**。见文末「round43 追加」。

> **★ 最重要的一条**：**「空出来的字节」≠「新的图标码」。**
> 引擎只认 `0xB1`/`0xB5`；往别的字节写只会走字形路径。做字符集扩容时不要指望
> "释放一个字节换一个图标"。

---

## ★ round43 追加：`ç`/`ñ` 进字符集 + **资料包**（`release/` 目录约定）

> **一句话**：`0xE7`/`0xF1` 从"未映射字节（被误写成 `{{BTN:…}}`）"正式变成**拉丁字母 ç/ñ**；
> 工具链全链同步，**盘上字节零变化**；并新增"把一轮的资料打成包"的工具与目录约定。

### 1. `ç`/`ñ` 的工具链改动（向后兼容是硬要求）

| 文件 | 改动 |
|---|---|
| `tools/font_pipeline/data/charset_compiled_zh16.json` | `codes` **只加两条**：`"ç": 231` / `"ñ": 241` |
| `tools/text_csv/tcslib.py` | 新增 `BTN_LATIN1_ALIAS=(0xE7,0xF1)` + `LATIN1_ALIAS_CHARS` + `Charset.normalize_latin1_alias()`；`btn_code_ok()` 对这两个字节**放行**（历史别名）；`encode_strict()` 先归一化再做 encode/decode 对称自检 |
| `tools/text_csv/icon_table.py` | `NOT_ICON_CODES` 标 `in_charset=True / kind='latin1'`；自检里加**硬断言** `is_icon(0xE7/0xF1) is False`（三种写法都验） |
| `tools/iso_build/dump_font.py` | `charset_rows()` 里这两行归 `kind='latin1'`（原来在 `icon` 段）；`capacity_report()` 增加 `used_hanzi` / `used_latin1` 拆分 |

* **效果**：`decode(0xE7)` → `ç`（不再是私有区 `U+E0E7`）⇒ CSV 里看得见、可编辑；
  `Français` / `Español` 直接写字母。
* **向后兼容**：老 CSV 的 `{{BTN:E0E7}}`/`{{BTN:E0F1}}` **仍被接受**，且与写字母
  **注入出逐字节相同的盘**（实测两路产物 sha256 都是 `98d333f7…`，盘上字节都是 `46 72 61 6e e7 …`）。
* **kind 统计不变**：`ascii 95 / single 108 / latin1 2 / pair 1319 / icon 2`（合计 1526）。
* 单字节码 **108 → 110**（汉字 108 + ç/ñ 2）；charset 字符总数 **1427 → 1429**。
* ⚠ `charset` 的 `protected` 仍列着 `0xE7/0xF1`（原意"英文盘在用、不许回收"）⇒
  只读工具 `font_usage.py` 会把这 2 个（连同历史 `0x92=若`）印成 `[!!] charset 自相矛盾`。
  那是**过时口径的告警**，不影响任何产物（该工具按铁律只读，未修改）。
* ⚠ **`font_usage.py` 的容量数字是方案 C 之前的旧口径**（自检打印
  `合法对偶空间 1222 / 已用 1168 / 空位 54 / 死 pair 151`；lead 上界还停在 `0xAD`）。
  现役权威口径 = `tcslib.pair_capacity()` / `dump_font` / `字库报告.xlsx`
  （**1504 / 1319 / 185 / 0 死 pair**）。该工具自检在本轮**之前就已经失败**
  （`decode_chars` 口径与 `tcslib` 不一致等，逐行相同）⇒ 本轮只带来
  `单字节码 108→110`、`去重 1427→1429`、`自相矛盾 1→3` 三处可预期增量；
  证据：`work/builds/GR_ZH93/temp/r41/font_usage_selfcheck_before.log` vs
  `temp/r43/v13_font_usage_selfcheck.log`。

### 2. `release/` 目录约定（★ 所有产物限制在版本文件夹内）

```
work/builds/<版本>/
  <版本>.iso            ← 现役盘（只读）
  text/                 ← 本版文本表（3 张可注入 + 9~10 张 view-only + meta + txt）
  font/                 ← 本版字库四件套（atlas png / charset csv / ft csv / summary json）
  temp/                 ← 测试产物（含本轮 r43/ 的验证脚本与日志）
  release/              ← ★ 给用户的资料包（本工具产出；只读，不被构筑流程改写）
    README.md           人话总索引 + 现役盘信息 + 模拟器跑法（人工维护）
    MANIFEST.json       每个文件的字节数 + sha256（脚本产出）
    字库报告.xlsx        6 页：索引 / 概要 / 字符分类 / 空位清单 / 手柄图标码 / 口径与限制
    字库报告.md          同一份报告的 Markdown 版
    text/               3 张可注入表 + <版本>_text.meta.json + 10 张 view-only 表
                        + README_文本表.md（人话：哪张能改 / 怎么改 / 怎么注入）
    font/               <版本>_font_atlas.png（2×）· …_atlas_1x.png（1:1）
                        · …_font_charset.csv · …_font_ft.csv
```

**生成命令**（新增 `tools/maint/make_release_pack.py`）：

```powershell
# 默认 --build GR_ZH93；--view-from 指 view-only 表的来源目录（round39 的普查落点）
& C:\ProgramData\anaconda3\python.exe tools/maint/make_release_pack.py --build GR_ZH93
& ... make_release_pack.py --build GR_ZH93 --skip-font-dump      # 复用版本夹里已有的 font/
```

* 脚本会**自己重跑 `dump_font`**（`--scale 2` 进 `font/`、`--scale 1` 进 `temp/release_pack/font1x/`），
  所以 `release/font/` 与 `release/字库报告.*` 里的数字**必然同源**。
* **数字全部现算**：读 charset JSON + 盘上图集（`tcslib.Charset` / `dump_font.load_font` /
  `GlyphCache` / `capacity_report`）⇒ **没有任何写死的 1504/1319/45/140**。
* **只读 ISO**：脚本一行都不写盘内数据；它只写 `release/` 与 `temp/release_pack/`。
* view-only 表**用 glob 抓 `*_view_*.csv`**（断言 ≥10 张），并保留 `injectable=no` 列
  ⇒ 注入器的两道防线在资料包里同样生效（显式喂 ⇒ exit 1 不写盘；给目录 ⇒ 只读 3 张可注入表）。
* ⚠ `release/README.md` 与 `release/text/README_文本表.md` 是**人话文档**，脚本**不覆盖**它们。

### 3. 本轮验收（全部实跑，日志在 `work/builds/GR_ZH93/temp/r43/`）

| 项 | 结果 |
|---|---|
| 重新 dump ⇒ `LANG:G059.I028` = `Français` | ✓ 2261 行往返自检全过 |
| 新表原样注入 `GR_ZH93.iso` | ✓ exit 0，sha256 仍 `e037f629…8d19be` |
| **旧写法** `{{BTN:E0E7}}` 注入 | ✓ 同 sha（该行确实进了写入集，编码出的字节与盘上一致 ⇒ 全盘 0 差异） |
| **两种写法等价**（真改一格） | ✓ 两路产物 sha256 都是 `98d333f7…`，盘上字节都是 `46 72 61 6e e7 …` |
| `--check-only` | ✓ exit 0 |
| `dump_font` / `icon_table.py` 自检 | ✓ kind `latin1 2 / icon 2`；自检 exit 0、零 `[!!]` |
| 从资料包 `release/text` 直接注入 | ✓ exit 0、sha256 同 `e037f629…`（meta 也被正确读到） |
| view 表拒注入（资料包内的拷贝） | ✓ 显式喂 exit 1 / 改名后仍 exit 1 / 给目录 exit 0 |
| `字库报告.xlsx` 读回复核 | ✓ 6 页、关键数字与 `dump_font` 输出**逐个一致** |
