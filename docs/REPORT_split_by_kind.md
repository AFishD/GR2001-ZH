# REPORT_split_by_kind — 文本表按 `kind` 分类成多张（round37）

> **用户原话**：「**修改一下脚本 改成按照 kind 进行分类 输出多个表格。**」
>
> **一句话结论**：dump 现在按 `kind` 产出**多张表**（`<版本>_text_long.csv` /
> `_long_nowrap.csv` / `_short.csv`，每张表**列完全不变**、还是 16 列），注入支持
> **给一个目录或多次给文件**（多表按 `id` 合并，同一个 id 的 `text_edited` 不一致就报错不写盘）；
> 构筑器与跨版本对比工具同步支持。
> **现役盘 `GR_ZH92.iso`（`1d30c106…`）一个字节都没动**：三张表原样注入 ⇒ 产物 sha256
> **仍是 `1d30c106…`**（逐字节相同）；用户手工写的 `SFXML:T0010`（7 个 `{WRAP}`）**原样保留**，
> 盘上 7 个 `{br}` 位置仍是 `15,28,38,52,63,78,92`。

---

## 1. 为什么要拆

原来是一张 `GR_ZH92_text.csv`：**2261 行**里混着三类完全不同的东西 ——

| 混在一起的东西 | 条数 | 编辑时要注意的事 |
|---|---|---|
| 特别收录的长段（武器/勋章介绍） | 58 | ★ 可以写 `{WRAP}` 控制断点；折行宽度 270 已标定 |
| 语言表长段（简报/说明/帮助正文） | 255 | 也是长段，但折行宽度**未标定**（没有 `wrap_hint`） |
| 按钮 / 条目名 / 短提示 | 1948 | **别加换行**（多半不是 RSHTML 组件） |

后果：在 Excel 里翻找费劲；更糟的是"**改了一张、另一张忘了改**"这种歧义无法被发现
（比如同一条文本被人在两处改了不同内容，工具只能猜）。
拆成多张后，**文件名就写着这张表是干什么的**，而且多表合并时能**机器判定**有没有互相矛盾。

---

## 2. 新布局（都在 `work/builds/<版本>/text/` 内）

| 文件 | `kind` | 条数 | 是什么 | 编辑注意 |
|---|---|---|---|---|
| `GR_ZH92_text_long.csv` | `long` | **58** | ★ 特别收录长段 | **可写 `{WRAP}` 控制断点**；`wrap_w=270`（有 `wrap_hint`/`wrap_preview`） |
| `GR_ZH92_text_long_nowrap.csv` | `long_nowrap` | **255** | 语言表长段（简报等） | 长段；宽度未标定 ⇒ `wrap_hint` 为空；同样可写 `{WRAP}` |
| `GR_ZH92_text_short.csv` | `short` | **1948** | 按钮 / 条目名 / 短提示 | **别加换行、别写 `{WRAP}`** |
| `GR_ZH92_text_locked.csv` | `locked` | 0 | 字节回环不稳定的条目 | **0 条时不产出这张表**（真有才出现） |
| `GR_ZH92_text.txt` | — | 2261 | **合并成一份**的轻量副本（`id<TAB>正文`） | 只读视图；给 git diff / 跨版本对比 |
| `GR_ZH92_text.meta.json` | — | — | 每张表的条数 / kind 列表 / 总条数 / sha256 | 配套元信息 |

* **合计 2261 = 58 + 255 + 1948**（`id` 无重复、无遗漏）。
* **不再产出合并的大 CSV**（原来那张 `GR_ZH92_text.csv` 已从 `text/` 移出，
  存到 `work/builds/GR_ZH92/temp/r37/old_zh92_merged/` 供对照）。
* **每张表的表头与列与拆分前逐字符相同**（16 列）：
  `id,resource,container,entry_index,offset,len_bytes,max_bytes,kind,wrap_w,lines,wrap_hint,wrap_preview,text_zh,text_en,text_edited,note`
* 拆表**不影响**任何既有语义：`text_zh` 只读、`text_edited` 是编辑栏、`{WRAP}` 是人工断点、
  `wrap_hint`/`wrap_preview` 只读、`text_en` 只读 —— 全部照旧（见 `tools/text_csv/FORMAT.md` §2.2）。

**本次产出的三张表（可直接核对 sha256）**

| 表 | 条数 | 字节 | sha256 |
|---|---|---|---|
| `GR_ZH92_text_long.csv` | 58 | 326 595 | `c5252b99b58a0454d2217eb825206a22e1ed5fbcd52313d082261a5036ba2ff6` |
| `GR_ZH92_text_long_nowrap.csv` | 255 | 289 456 | `31fe96049b0c0124489571f86c0e7cb14a61b95784449f4086bf54014ab73980` |
| `GR_ZH92_text_short.csv` | 1948 | 338 198 | `9759b3b1a689a3d04e640b6a76460a0ad3425e37a06cb8b2188022957033e730` |
| `GR_ZH92_text.txt`（合并） | 2261 | 202 085 | `ae60f337d28c78e65840cb4185426fa96e84655528b55dd5d3b191b6969a7731` |

> **复 dump 确定性**：对同一个 ISO 再 dump 一次 ⇒ 三张表的 sha256 **完全相同**（实测）。

---

## 3. 怎么改、怎么注入（给非程序员）

**改文案**

1. 打开 `work/builds/GR_ZH92/text/`，按你要改的内容**挑表**：
   * 改长段（特别收录介绍）⇒ `GR_ZH92_text_long.csv`，想固定断行就在那个位置写 `{WRAP}`；
   * 改简报/说明 ⇒ `GR_ZH92_text_long_nowrap.csv`；
   * 改按钮/条目名 ⇒ `GR_ZH92_text_short.csv`（**别加换行**）。
2. **只改 `text_edited` 一列**（`text_zh` 右边的 `text_en` 是英文原文，只读参考）。

**注入 / 构筑（两种都行）**

```powershell
# ① 只注入（原盘只读；★ 给目录最省事 —— 该目录下所有 *_text_*.csv 全部读入，不会漏表）
& C:\ProgramData\anaconda3\python.exe tools/text_csv/inject_text_csv.py `
    --csv work/builds/GR_ZH92/text `
    --src work/builds/GR_ZH92/GR_ZH92.iso --dst work/builds/GR_ZH93/GR_ZH93.iso `
    --report work/builds/GR_ZH93/temp/inject_report.json

# ② 走构筑器（推荐；会自动产出下一版的多张表 + 字库快照）
& C:\ProgramData\anaconda3\python.exe tools/iso_build/make_build.py GR_ZH93 `
    --from work/builds/GR_ZH92 --inject-csv work/builds/GR_ZH92/text
#   也可以只写版本名: --inject-csv GR_ZH92   (自动解析到它的 text/ 目录)

# ③ 只想改其中一类 ⇒ 给单个表文件（给几次都行；没给到的 kind 一个字都不动）
... --csv work/builds/GR_ZH92/text/GR_ZH92_text_long.csv
```

**多表合并规则**（注入器 / 构筑器 / 对比工具同一套实现，在 `tools/text_csv/tcslib.py`）

1. 多张表按 `id` 合并（先给的表在前）；
2. 同一个 `id` 在两张表里 **`text_edited` 不同 ⇒ 报错退出（退出码 1）且一个字都不写盘**，
   并把"两张表各写了什么"并排列出来 —— 这就是"改了一张、另一张没改"的歧义，工具不替你选；
3. 同一个 `id`、`text_edited` 相同 ⇒ 去重放行（打印「去重 N 行」）；
4. 只读列（`text_en` / `wrap_hint` / `wrap_preview`）照旧整列丢弃。

**旧表怎么办**

| 你手上的表 | 注入器的行为 |
|---|---|
| `text-csv/4` 多表（本轮） | 正常注入 ✓ |
| `text-csv/3` **合并的大表**（round36，如 `GR_ZH91_text.csv`） | **仍然能注入，结果与多表逐字节等价**；但会打印一大段「**请改用多表**」+ 重新 dump 的命令 |
| `text-csv/1` `text-csv/2`（round35 及更早） | 改了长段 ⇒ **拒绝注入**（退出码 1），给出 `--carry-edited` 重新 dump 的命令（round36 既有保护，未变） |
| 重新 dump 时想留住你改过的 `text_edited` | `dump_text_csv.py ... --carry-edited <旧表或旧表目录>`（可给多次/给目录） |

---

## 4. 代码改动清单（只打补丁，没重建任何 ISO）

| 文件 | 改了什么 |
|---|---|
| `tools/text_csv/tcslib.py` | **新增多表公共设施**：`split_table_name` / `is_table_csv` / `expand_csv_inputs`（文件·目录·多次 → 有序去重的表路径）/ `read_table_rows` / `merge_table_rows`（按 `id` 合并 + **歧义检测**）/ `write_txt_snapshot`（合并 TXT，`{WRAP}`→真换行）/ `table_set_summary`（路径+条数+sha256）；格式常量 `FMT_TABLES='text-csv/4'` |
| `tools/text_csv/dump_text_csv.py` | 按 `kind` 写**多张表**（`<基准>_<kind>.csv`，0 条的 kind 也写**只有表头的空表**）+ **合并 TXT 一份** + meta 记各表条数/kind/总条数/sha256；新增 `--only-kind`；`--carry-edited` 支持多次/目录；老合并大表若还在目录里 ⇒ **明确提示它是过期快照**；`--out` 现在是"基准路径" |
| `tools/text_csv/inject_text_csv.py` | `--csv` 支持**目录**与**多次/多值**；多表按 `id` 合并 + **歧义 ⇒ exit 1 不写盘**（含 `--report` 的 `rejected-by-ambiguous-id`）；老合并大表 ⇒ **明确提示「请改用多表」**（行为不变）；其余（字库预检 exit=3、`{WRAP}` 展开、旧格式拒绝、`--only`/`--check-only`/`--dry-run`/`--report`）**逐条保持** |
| `tools/iso_build/make_build.py` | `--inject-csv` 支持**目录/多表**（`resolve_inject_input`，版本名 → `text/` 多表目录）；文本快照改为**多表 + 合并 TXT**（复用 tcslib 同一套合并口径）；`build_info.json.text_snapshot` 新增 `tables[]`（每张表的 path/kind/rows/bytes/**sha256**）、`kinds`、`tables_total_rows`、`tables_dir`、`layout` |
| `tools/text_csv/diff_text_versions.py` | 支持**两版多表对比**（先按 `id` 合并再比，**输出格式不变**）；给 ISO 时的临时 dump 也按多表读；`--list` 列出多表；表比 TXT 新时给提示 |
| `tools/text_csv/FORMAT.md` | 顶部加「round37 变了什么」；§0 三步上手改多表；**新增 §2.2「多表布局：哪张表是干什么的」**；§3.6 加 `text-csv/4` 行；§9 更新 TXT 口径；**新增 §11 round37 验证证据** |
| `docs/BUILD_TOOLCHAIN.md` | §2.1 产出布局、§8.1–8.6（多表目录注入、`text/` 各表、标准动作、对比工具、取舍） |
| `docs/REPORT_split_by_kind.md` | 本报告（新增） |

---

## 5. 验收（全部实跑，日志留档 `work/builds/GR_ZH92/temp/r37/`）

### ① 往返零差异 ✅

| 做什么 | 命令（要点） | 结果 |
|---|---|---|
| 多表原样注入**现役盘** | `inject_text_csv.py --csv work/builds/GR_ZH92/text --src GR_ZH92.iso --dst t6_zh92_rt.iso` | `[hash] src/dst` **都是 `1d30c1067beb8fc8534193486f23f75489447eb0487ab24d06ef66c0627120b6`**；`[diff] 全盘差异 **0 B** / 3 个写入窗口; 窗口外差异: 无 ✓`（`log_t6_zh92_roundtrip.txt`） |
| 同上，**改完代码后用最终状态再跑一遍** | `… --dst t20_final_rt.iso` | 同样 **`1d30c106…`** 逐字节相同（`log_t20_final_roundtrip.txt`） |
| 拆表前的盘也不受影响 | 不带用户改动的多表注入 `GR_ZH91.iso` | 产物 **`42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88`** = `GR_ZH91.iso` 逐字节相同（`log_t3_rt.txt`） |
| 合并 TXT 不变 | 多表合并出的 TXT vs 拆表前大表派生的 TXT | **逐字节相同**（`ae60f337d28c…`）⇒ git diff 里只看到 CSV 被拆开（`log_t16_redump_zh92.txt`） |
| 复 dump 确定性 | 对同一 ISO 再 dump | 三张表 sha256 **完全相同** |

### ② 拆分正确 ✅（`verify_split.py` → `log_t5_verify_split.txt`）

```
[ok] 条数 = long 58 / long_nowrap 255 / short 1948 (期望 58 / 255 / 1948)
[ok] 合计 2261 = 2261
[ok] GR_ZH92_text_long.csv / _long_nowrap.csv / _short.csv 表头与 16 列原表**完全相同**
[ok] 合并后 2261 行, id 唯一 2261 个 (无重复无遗漏)
[ok] 与原大表不同的单元格: 2 处  →  SFXML:T0010 . text_edited / SFXML:T0010 . note
[ok] 差异**只**出现在 SFXML:T0010 的 text_edited (搬运的用户改动) 与 note (搬运说明) 两列
[ok] 其余 2260 行 × 16 列与原大表**逐字符相同**
```

> 那 2 处正是**用户改动本身**：`text_edited` 被 `--carry-edited` 原样搬过来了，
> `note` 多了一句"是从旧表搬运过来的人工改动"。

### ③ 用户改动保留 ✅

```
[ok] SFXML:T0010 落在 **long** 表里 (kind=long)
[ok] text_edited 与用户原表**逐字符相同** (144 字符)
[ok] 里面有 7 个 {WRAP} 标记
[ok] 断点位置 = [15, 28, 38, 52, 63, 78, 92] (期望 15,28,38,52,63,78,92)
[ok] 盘上 {br} 位置 = [15, 28, 38, 52, 63, 78, 92] (期望 15,28,38,52,63,78,92)
[ok] 盘上 {p} 个数 = 0 (期望 0)
[ok] 盘上可见文本 == 用户 text_edited 去掉 {WRAP} 后 (102 字符)
```

`GR_ZH92_text_long.csv` 里该条（原样保留用户写法）：

```
M18 定向反步兵地雷由曲面的{WRAP}方形硬质弹体制成，内装有大{WRAP}约340克C3炸药。{WRAP}其破片面由方形金属破片构成，{WRAP}起爆时破片以扇形射出。{WRAP}由于装药的原因，地雷在正后方会{WRAP}存在一小片杀伤区，而爆炸正面{WRAP}则是大范围的毁伤区。
```

`GR_ZH92.iso` 盘上该条（`194 B`，7 个 `{br}`）：

```
M18 定向反步兵地雷由曲面的{br}方形硬质弹体制成，内装有大{br}约340克C3炸药。{br}其破片面由方形金属破片构成，{br}起爆时破片以扇形射出。{br}由于装药的原因，地雷在正后方会{br}存在一小片杀伤区，而爆炸正面{br}则是大范围的毁伤区。
```

注入器的「人工断点落点核对」逐条打印了落点（`log_t1_multi.txt`）：

```
#   你写的断点位置: 第 15, 28, 38, 52, 63, 78, 92 个字符之后
#   盘上新增 {br} 位置: 第 15, 28, 38, 52, 63, 78, 92 个字符之后   ✓ 一一对应
#     ⏎ 第 15 个字符之后: …向反步兵地雷由曲面的⏎方形硬质弹体制成，内…
```

### ④ 多表注入 ≡ 原大表注入 ✅

| 用哪份表 | 基底 | 产物 sha256 |
|---|---|---|
| 多表目录 `zh91_mt`（含搬运的用户改动） | `GR_ZH91.iso` | `1d30c106…`（`log_t1_multi.txt`） |
| **原合并大表** `GR_ZH91_text.csv`（`text-csv/3`） | `GR_ZH91.iso` | **`1d30c106…`**（`log_t2_merged.txt`） |

⇒ 两者**逐字节等价**；注入器对老表打印了「请改用多表」的提示（`log_t2_merged.txt` 前 25 行）。

### ⑤ 歧义检测 ✅（`test_ambiguity.py` → `log_t7_ambiguity.txt`）

```
A. 同一个 id 在两张表里 text_edited **不同**
   # 合并  : 4 张表共 2262 行 → 按 id 合并后 **2261 行**
   [!!] 发现 1 处**多表歧义**: 同一个 id 出现在两张表里, 而 text_edited **不一致**
     ── LANG:G001.I000
        A: …GR_ZH92_text_short.csv   你写的: '胜利！'
        B: …GR_ZH92_text_zzamb.csv   你写的: '胜利！XXXX'
   [ok] 退出码 = 1        [ok] **没有**产出任何 ISO        [ok] 报告 mode=rejected-by-ambiguous-id
B. 同一个 id 但 text_edited **相同** ⇒ 去重放行
   [ok] 退出码 = 0   「去重 1 行」   产物与基底**逐字节相同** (`1d30c106…`)
C. --csv 给不存在的路径 ⇒ 退出码 2 + 人话说明（原有退出码约定不变）
```

### ⑥ 构筑链路 ✅（`log_t8_makebuild_GR_ZH93.txt`）

```powershell
& python tools/iso_build/make_build.py GR_ZH93 --from work/builds/GR_ZH92 --inject-csv work/builds/GR_ZH92/text
```

```
[base] work/builds/GR_ZH92\GR_ZH92.iso (sha 1d30c1067beb8fc8...)
# 输入表: 3 张 …  #   long 58 行 / long_nowrap 255 行 / short 1948 行
# 合并  : 3 张表共 2261 行 → 按 id 合并后 **2261 行**
[hash] src/dst 都是 1d30c106…  ⇒ 逐字节相同 (无改动)
[inject] 1/1 完成: work/builds/GR_ZH92/text → ISO sha 1d30c1067beb8fc8…
[text-snapshot] 2261 条 / 长段 313 / 65714 字符 (中文 45737)  — 耗时 2.9s
[text-snapshot] long 58 行 / long_nowrap 255 行 / short 1948 行  (各带 sha)
[done] 本版本文本副本: 3 张表 / 2261 条 …
[done] 本版本字库 dump: work/builds/GR_ZH93/font (face 3 / 记录 544 / 字符 1456, 缺字形 33)
```

产物核对：

* `work/builds/GR_ZH93/`：`GR_ZH93.iso`（sha `1d30c106…`，与基底相同）、
  `text/`（3 张表 + `GR_ZH93_text.txt` + `GR_ZH93_text.meta.json`）、
  `font/`（图集 PNG + FT CSV + charset CSV + summary.json）、`build_info.json`；
* `build_info.json → text_snapshot` 字段齐全：
  `format="text-csv/4"`、`layout`、`tables_dir`、
  **`tables[]` 每张表带 `path` / `kind` / `rows` / `bytes` / `sha256`**、
  `kinds`、`tables_total_rows=2261`、`txt` + `txt_sha256`、`meta`、`entries/long/short/chars/cjk_chars`、`resources`；
* `python tools/text_csv/diff_text_versions.py GR_ZH92 GR_ZH93` ⇒ **0 处差异**（2261 条全部相同，`log_t11_diff_zh92_zh93.txt`）。

### ⑦ 空表与过滤 ✅（`log_t12_onlykind.txt`）

```
& python tools/text_csv/dump_text_csv.py --iso GR_ZH92.iso --out … --only-kind long,short,locked --no-en
[out] 按 kind 分类写出 3 张表 …
   long      58 行     short   1948 行     locked     0 行
[注意] 下面这些表**本次 0 条** (照样产出了只有表头的空表, 不是漏了): GR_ZH92_text_locked.csv
[注意] --only-kind 点名的 locked 在这次 dump 里**一条都没有** ⇒ 产出空表
[注意] --only-kind 只写出 2006 行, 另外 255 行 (其它 kind) **没有写进任何表**
```

空表内容 = **表头一行**（16 列）：
`id,resource,container,entry_index,offset,len_bytes,max_bytes,kind,wrap_w,lines,wrap_hint,"wrap_preview","text_zh","text_en","text_edited","note"`

### ⑧ 其它已实跑的路径 ✅

| 场景 | 命令 | 结果 |
|---|---|---|
| `--csv` 给**多次** | `--csv a_long.csv --csv a_short.csv --dry-run` | 2 张表 / 合并 2006 行 / exit 0（`log_t14_multiarg.txt`） |
| `--csv` 给**多值** | `--csv a_long.csv a_short.csv` | 同上（同上日志） |
| `--carry-edited` 给**多表目录** | `dump --carry-edited work/builds/GR_ZH92/text --only-kind long` | 读入 3 张表；搬运 `SFXML:T0010` 的 7 个 `{WRAP}`（`log_t13_carrydir.txt`） |
| `--stats` | `dump --stats` | 正常（`log_t15_stats.txt`） |
| 多表 vs 多表对比 | `diff_text_versions.py <只有多表的目录A> <B>` | 合并 3 张/侧，输出格式不变，1 处差异 = 那 7 个 `{WRAP}`（`log_t9_diff_tables.txt`） |
| 版本名对比 | `diff_text_versions.py GR_ZH91 GR_ZH92` | 用合并 TXT，1 处差异 = `SFXML:T0010` 的 7 个断点（`log_t10_diff_zh91_zh92.txt`） |
| `--inject-csv` 参数解析 | `resolve_inject_input()`（`test_resolve.py`） | 版本名 → `…/text`（多表目录）；版本目录 → 自动进它的 `text/`；单表文件 / 老的大表 / 绝对路径目录 全部正确；不存在的版本 → `None`（构筑器报错 exit 2）（`log_t17_resolve.txt`） |

### ⑨ 既有行为逐条保持 ✅（`test_regress.py` → `log_t18_regress.txt`）

多表改造**没有动**任何既有保护，全部实跑复验：

| 场景 | 结果 |
|---|---|
| A. 文案里有缺字（加了个「龘」） | **退出码 3**，报「字符集里没有 U+9F98 龘」+ 处理建议，`--check-only` 不写盘；`--report` 的 `charset_precheck.verdict = fail` |
| B. `--only` 仍然只作用于指定 id | `--only SFXML:T9999` ⇒ exit 0（不在范围内）；`--only SFXML:T0010` ⇒ exit 3（正是那条缺字） |
| C. 旧格式 `text-csv/2` 的**被编辑长段** | **退出码 1**，打印「这份表是旧格式…」+ `--carry-edited` 重新 dump 的命令，不写盘 |
| D. `{WRAP}` 写在**文本最开头** | **退出码 1**，报「断点标记在文本最开头…」，不写盘 |
| E. `--check-only` / 被拒绝时 | 四次运行**都没有产出任何 ISO** |

---

## 6. 已知限制 / 注意事项

1. **`--csv` 给目录 = 读入目录里所有 `*_text_*.csv`**（刻意如此，避免漏表）。
   要只注入一部分，请**显式给那几个表文件**，别靠"把表移出目录"。
2. **同一条文本请不要在两处改**：多表合并会检测到 `text_edited` 不一致并**拒绝注入**（这是保护，不是 bug）。
   注意"同一条文本"指的是**同一个 `id`**（每张表里的 `id` 都是唯一的，正常不会重复）。
3. **老合并大表（`text-csv/3`）仍可注入**（逐字节等价），但会被提示改用多表；
   `text-csv/1` `text-csv/2` 的**长段编辑**仍然**拒绝**（round36 既有保护，未变）。
4. **构筑器自动产出的新表里，`{WRAP}` 写法不会自动继承**：
   `make_build.py` 的快照是"盘上现值的 dump"，所以下一版（如 `GR_ZH93_text_long.csv`）里
   `SFXML:T0010` 显示的是**7 个真换行**而不是 `{WRAP}`（两者注入结果**完全相同**）。
   想保留 `{WRAP}` 写法 ⇒ 单独 dump 一次并加 `--carry-edited <上一版的 text 目录>`。
5. **TXT 快照里的 `{WRAP}` 现在渲染成真换行**（视图 = 盘上的换行）。
   round36 及更早是"把标记删掉"，那会让视图凭空少掉换行 —— 本轮顺手修掉了 FORMAT.md §9 里记的"待改进"。
6. **`diff_text_versions.py` 仍优先用合并 TXT**（行为不变）：若有人**手工改了表还没重新构筑**，
   TXT 就是旧的 —— 此时工具会提示"多表 CSV 比 TXT 更新"，并告诉你可以直接把表目录给它。
7. `--dry-run` 仍然**需要 `--dst`**（原有行为，未改）。
8. `work/builds/GR_ZH91/text/GR_ZH91_text.csv`（用户改过的那张**老合并大表**）
   **保持原样未动**，它现在是"搬运来源"；`work/builds/GR_ZH92/text/` 才是新的多表工作目录。
   那张老表已被**移出** `text/`（副本在 `work/builds/GR_ZH92/temp/r37/old_zh92_merged/`）。
9. 三张表里的 `offset` / `len_bytes` 仍然**不能改**（改了注入器会拒绝）；
   多表并不改变"注入必须从同一基底盘一次做完"这条约束。
10. **git 提示（给 Lead）**：`work/**` 在 `.gitignore` 里，所以 `text/` 下的新表默认**不入库**；
    而被删掉的那张老合并大表 `work/builds/GR_ZH92/text/GR_ZH92_text.csv` **原本是被跟踪的**
    （早前 `git add -f` 过）⇒ 本次改动在 `git status` 里表现为
    `D work/builds/GR_ZH92/text/GR_ZH92_text.csv` + `M …meta.json`。
    若要把多表也纳入仓库，需要 `git add -f work/builds/GR_ZH92/text/*`（由 Lead 决定）。
    该老表的**逐字节副本**留在 `work/builds/GR_ZH92/temp/r37/old_zh92_merged/`（sha256 `ff413ff8…`）。

---

## 7. 给用户的一句话

> **文本表现在按 kind 分成了三张**：`_long.csv`（长段，**想固定断行就在那儿写 `{WRAP}`**）、
> `_long_nowrap.csv`（简报等语言表长段）、`_short.csv`（按钮和条目名）；
> 三张表的列和以前一模一样，**只改 `text_edited` 一列**；
> 改完把 **`text/` 这个目录**交给下一轮构筑（`--inject-csv work/builds/GR_ZH92/text`）就行 ——
> 目录里的表会被**全部**读进去，不会再出现"漏改一张"的情况；
> 你上次写的 `SFXML:T0010` 那 7 个 `{WRAP}` **原样还在** `_long.csv` 里，
> 盘上 7 个断点的位置一个都没变。
