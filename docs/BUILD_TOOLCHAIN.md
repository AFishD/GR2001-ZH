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

## 8. 文本快照与文本注入（round31 新增；round37 起文本表**按 kind 分多张**）

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
| `<VER>_font_charset.csv` | `char,unicode,kind,bytes_hex,slot,cell_x,cell_y,has_glyph,note`（`kind` = ascii/single/pair/icon） |
| `<VER>_font_summary.json` | face 数 / 记录数 / 字符数 / 有字形 / 缺字形 / 图集尺寸与哈希 / 各文件 sha256 / 网格配方 |

* **全部口径复用 `tools/text_csv/tcslib.py`**（`parse_ft_faces` / `parse_pak_records` /
  `atlas_cell_xy` / `GlyphCache`），没有重新逆向任何格式；`has_ink` = 引擎真画得出来吗
  （记录矩形 / `+4,+2` 实测偏置矩形 / ±邻域 三处任一有墨），`has_glyph` 用 `GlyphCache` 的原判据。
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


