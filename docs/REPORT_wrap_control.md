# REPORT_wrap_control.md — `{WRAP}` 语义变更：从「建议断点（注入时丢弃）」→「人工断点（注入成真换行）」

**round36 / 分支 `round34/wrap-control` / 2026-10-10**
工具链: `tools/text_csv/{tcslib.py, dump_text_csv.py, inject_text_csv.py, FORMAT.md}`（本报告不含 `tools/iso_build/**` 改动）

---

## 0. 结论（一句话）

> **用户原话**：「我希望主动控制断点，只在内容里添加 `{Warp}` 控制断点。」

| | 改之前（round35） | **改之后（round36）** |
|---|---|---|
| `{WRAP}` 是什么 | dump 自动插的「引擎会在这折行」**提示** | **人写的人工断点指令** |
| 注入时怎么处理 | **整段丢弃** ⇒ 用户写的断点**永远不生效**（用户报障的根因） | **变成真换行**（盘上写出 `{br}`） |
| dump 会不自动插 | 会（现役盘 1548 个，混在正文列里） | **绝不**（正文列 0 个） |
| 「引擎现在在哪折行」 | 和人工断点长得一模一样、分不出来 | 只进**只读列** `wrap_hint` / `wrap_preview` |

- **用户在 `SFXML:T0010`（M18 定向反步兵地雷）写的 7 个 `{WRAP}` 已实机生效**：
  盘上 `{br}` 0 → **7**，位置 `15, 28, 38, 52, 63, 78, 92`（第 N 个字符之后）与他写标记的位置**一一对应**；
  实机「特别收录 → 武器 → M18」介绍框断行完全按他的标记（§6、图 `temp/wrapcmp_M18_f10900_zoom.png`）。
- **没改动的条目一个字都不动**：新 dump 的表原样注入 ⇒ 产物与 `GR_ZH91.iso` **逐字节相同**
  （sha256 `42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88`）。

---

## 1. 新语义（round36）

### 1.1 写入方向（inject：`text_edited` → 盘上字节）

| 你写的 | 盘上 | 说明 |
|---|---|---|
| `{WRAP}` / `{Warp}`（**两种拼写都认，大小写不限**：`{wrap}` `{WARP}` `{wArP}` …） | `{br}` | ★ **人工断点** |
| 1 个换行（回车 / Alt+Enter） | `{br}` | 与写标记等价 |
| 1 个空行（连续 2 个换行） | `{p}` | 段间空一行 |
| ≥3 个连续换行 | 折叠成 1 个 `{p}` | 引擎没有更多空行的写法（告警） |
| 写错的标记（`{WRAP` `{WRP}` `{WRAPP}` `{ WRAP }` …） | **拒绝注入** exit 1 | `--force` 也不能绕过 |
| 位置非法（最开头/最末尾/紧挨另一个标记或换行） | **拒绝注入** exit 1 | 会写出连续标记 `{br}{br}`，CSV 无法无损表示 |

> ⚠ 一个实现细节：**`{Warp}` 与 `{WRAP}` 不是大小写关系**（`Warp` = W,a,r,p；`WRAP` = W,R,A,P）。
> 用户写的是 `{Warp}`，历史文档写的是 `{WRAP}` ⇒ 正则收进**两种拼写**：
> `WRAP_RE = re.compile(r'\{(?:WRAP|WARP)\}', re.I)`（共 16 种大小写组合），dump/报错统一写成 `{WRAP}`。

### 1.2 读取方向（dump：盘上字节 → CSV）

* `{br}` → 恰好 1 个换行；`{p}` → 恰好 1 个空行（round35 口径，未变）。
* **`wrap_w>0` 的资源不再往正文列插任何标记**；引擎折行点只进只读列（§3）。
* 往返自检（`cell_to_bytes_text(text_zh) == 盘上字节`）保留，实测 2261 行全过 —— 这是
  「改 N 次也不会累积变坏」的机器判据。

### 1.3 两类资源的行为

| 资源 | 折行宽度 | 只读折行提示 | `{WRAP}` 人工断点 |
|---|---|---|---|
| `SFXML`（特别收录 XML，69 条） | 270（已实机标定） | 58 条长段共 1548 个位置 | ✅ 已实机验证（M18，§6） |
| `LANG`（语言表，2232 条，两份拷贝同步写） | 0（未标定，被多种组件消费） | 0 个（不猜） | ✅ 同一套代码路径；`{br}` 在该组件已实证吃（`docs/REPORT_csv_text_tool.md` §8 简报组件），本轮**未做新的实机验证**（如实登记） |

⇒ **两类资源的断点语义完全一致**（同一个 `tcslib.cell_to_bytes_text`）；差别只在
「要不要/能不能给折行提示」，与人工断点无关。

---

## 2. 工具链改动清单（只改这 4 个文件）

### 2.1 `tools/text_csv/tcslib.py`

| 改动 | 说明 |
|---|---|
| `WRAP_RE` | 从 `\{WRAP\}`(re.I) 扩成 `\{(?:WRAP|WARP)\}`(re.I)，新增 `WRAP_SPELLINGS` |
| `_wrap_lookalike` / `WRAP_TYPOS` / `_wrap_syntax_reason` | 写法错误判定覆盖两种拼写（`{WRP}` `{WRAPP}` `{WRAP` `{WA…}` …） |
| **新增 `scan_wrap_placement`** | 位置规则：最开头 / 最末尾 / 紧邻另一个标记 / 紧邻换行 ⇒ 人话问题列表 |
| **新增 `WrapPlacementError`** | 位置非法的异常类型（继承 `CharsetError`，**不可被 `--force` 绕过**） |
| **新增 `expand_wrap_marks`** | 先查写法、再查位置，然后把 `{WRAP}`/`{Warp}` → `\n`（返回 `(新文本, 断点数)`） |
| `cell_to_bytes_text` | `strip_wrap_marks`（丢弃）→ **`expand_wrap_marks`（变真换行）**；`stats` 增加 `n_wrap_breaks` |
| **新增 `wrap_hint_cell`** | 引擎正文 → `(单元格, 折行点位置表, 带 \| 的预览)`；**不插任何标记** |
| **新增 `wrap_break_positions` / `tag_break_positions`** | 「第 N 个字符之后」口径的断点定位（供注入器做落点核对） |
| `render_cell` / `wrap_render` | **不再插标记**（= `text_to_cell`，安全兜底）；删除 `mark_wrap_points`、`strip_wrap_marks` |
| `selfcheck_newlines` | 重写为 round36 口径（含 `{Warp}` 等价、位置非法拦截、`wrap_hint` 口径等 47 条断言） |
| `encode_strict` 不变式 | 「带 `{WRAP}` 的文本绝不允许进字节流」保留（改文案为"人工断点"） |

> 关键设计：**`render_cell` 现在恒不插标记**（`n_soft` 恒 0）。这样即使有旧调用方误用，
> 也只会得到一份**不含标记**的单元格 —— 绝不会"替用户把引擎折行固化成硬换行"。

### 2.2 `tools/text_csv/dump_text_csv.py`

* `FMT_VERSION = 'text-csv/3'`（**新格式号**；旧 `text-csv/1` `text-csv/2` 语义不兼容，见 §7）。
* 新增两列（**只读**，紧跟 `lines` 之后）：
  `… kind, wrap_w, lines, wrap_hint, wrap_preview, text_zh, text_en, text_edited, note`。
* 正文列（`text_zh` / `text_edited`）改用 `T.text_to_cell`（**零标记**）；折行点走 `T.wrap_hint_cell`。
* `note` 改写：`长段; 引擎自动折行点 N 处 (只读提示, 见 wrap_hint / wrap_preview 列; **不会**写进盘)
  + 显式换行 ×M; ★ 想**固定**断行: 在 text_edited 里想断的地方写 {WRAP} (也接受 {Warp}…)`。
* 「Excel 显示不出来」硬门槛扫描列从 4 列扩到 **6 列**（含两个新只读列）。
* 新增 `--carry-edited <旧 CSV>`：把旧表里 `text_edited != text_zh` 的行**原样搬进新表**
  （只搬这一列；报告逐条列出 id、`{WRAP}` 个数与断点位置）。
  另有**保险**：若目标 CSV 已存在且里面有改过的行、而你没给 `--carry-edited`，dump 会显著提醒
  （列出 id + 重新搬运的命令）。
* 往返自检结论行改为：`正文列里的断点标记 0 个 (dump **不写**标记); 引擎折行提示(只读列) 1548 个;
  搬运来的人工断点 7 个`；`meta.roundtrip` 记录 `wrap_marks_in_text_columns=0`。

### 2.3 `tools/text_csv/inject_text_csv.py`

* `FMT_CURRENT = 'text-csv/3'`；`FMT_LEGACY = ('text-csv/1', 'text-csv/2')`。
* `IGNORED_COLS = ('text_en', 'wrap_hint', 'wrap_preview')` —— 读 CSV 后**第一件事**整列丢掉，
  结构性保证"这三个只读列里写什么都没用"。
* `scan_wrap_marks` 重写：统计 `text_edited` 里的合法标记（= 真断点）与 `text_zh` 里的
  （= 只读列，提示无效），并对 `text_edited` 做**位置**预检（在写盘前，`--check-only` 同样拦）。
* 报错分两类人话：写法错 / 位置非法；都列出「你写的是、问题、正确写法、怎么办」。
* **旧格式保护**：meta 说 `text-csv/1` `text-csv/2` 且你改过长段 ⇒ 拒绝 + 给出 `--carry-edited` 命令；
  meta 丢失时改用**内容判据**（`text_zh` 里带合法 `{WRAP}` = 新 dump 绝不会有的写法）⇒ 同样拒绝。
* 落点核对：逐行打印「你写的断点位置」vs「盘上新增的 `{br}` 位置」+ 前后文，并断言一一对应；
  报告 JSON 里给出 `wrap_breaks.positions[]`（`cell_break_positions` / `br_added` / `landed_ok`）。
* 删除内容启发式 `legacy_suspect_rows`（round36 里"长段没有标记"是**正常**的，旧启发式会误报）。

### 2.4 `tools/text_csv/FORMAT.md`（给用户看的手册）

§0 三步上手（新增 `--carry-edited` 用法与"**必须用新 dump 的表**"警示）、§2 列定义（新增两列 +
位置口径）、**§3 全面重写**（新语义表 / 位置规则 / FAQ）、§3.6 旧格式表处置、§4 编辑规矩、
§5.5 硬门槛列数、§6.1 预检口径、§9 已知限制、§10 round36 验收证据。

---

## 3. `wrap_hint` / `wrap_preview` 设计（只读折行提示）

**目标**：让用户仍然能"看到引擎现在在哪折行"，但**绝不**让它与人工断点混在一起。

| 列 | 内容 | 例子（`SFXML:T0010` 注入前的真实取值） |
|---|---|---|
| `wrap_hint` | 折行点**字符位置**，逗号分隔；从 **1** 开始数，数的是 `text_zh` 整格字符（含其中的换行）；语义 = **「第 N 个字符之后引擎换到下一行」** | `17,36,43,58,70,86,102` |
| `wrap_preview` | 同一件事的"看得见"版本：在那些位置插 `\|` | `M18 定向反步兵地雷由曲面的方 \|形硬质弹体制成， 内装约 340 克 \|C3 炸药。 \|…`（`lines=8`） |

* 只对 `wrap_w>0` 的资源计算（现役盘 = `SFXML`；`LANG` 未标定宽度 ⇒ 两列留空，不猜）。
* 口径 = 引擎折行模型 `RSTextComponent::DoWordWrap`（`docs/REPORT_wrap_and_title.md`），
  经 `wrap_seg_spans` 取行边界 ⇒ `wrap_hint_cell` 把它换算成**单元格坐标**。
* **只读**：注入器结构性丢弃这两列（`IGNORED_COLS`），改了不会影响产物一个字节。
* 与「第 N 个字符之后」的报错/落点口径**完全一致**，便于用户自己核对。
* 位置口径的已知偏差：折行模型按"单空格切词"，会把连续空格折叠后再算宽度
  （实测只有 `LANG:G058.I760` 一条受影响，且只在该资源被 `--wrapw` 强制打开时可见）。
  这只影响**只读提示的数值**；`{WRAP}` → `{br}` 的位置是逐字符精确的。

---

## 4. 交付物与落点

| 文件 | 说明 |
|---|---|
| `work/builds/GR_ZH91/text/GR_ZH91_text.csv` | **重新 dump** 的新格式表（`text-csv/3`，2261 行，931.9 KB）：正文列 0 个 `{WRAP}` + 新增两列只读提示 + **用户改动已搬运**（`SFXML:T0010`）—— ⚠ **见下方"待办"** |
| `work/builds/GR_ZH91/text/GR_ZH91_text.meta.json` | 新表元信息（`format=text-csv/3`、源盘 sha256、`carry` 逐条记录、`roundtrip` 自检结果） |
| `work/builds/GR_ZH91/text/GR_ZH91_text.txt` | 版本单行副本：**重新生成后与构筑时那一份逐字节相同**（sha256 `ae4794c70610…`）⇒ 无需改动 |
| `work/builds/GR_ZH91/temp/*` | 全部测试脚本、日志、测试盘、实机 dump、对照图（见 §5/§6，索引见 `temp/README_wrap_control.md`） |
| `docs/REPORT_wrap_control.md` | 本报告 |

> ### ⚠ 待办（唯一未完成的一步）：把新表装进 `text/`
>
> 生成新表时 `work/builds/GR_ZH91/text/GR_ZH91_text.csv` **正被用户的 Excel 打开**
> （进程 `EXCEL` pid 3472，窗口标题 `GR_ZH91_text.csv - Excel`），Windows 拒绝覆盖
> （6 次重试均 sharing violation）。新表已就绪，放在版本文件夹内：
>
> | 源（temp/） | → | 目标（text/） |
> |---|---|---|
> | `GR_ZH91_text_carry.csv` | → | `GR_ZH91_text.csv` |
> | `GR_ZH91_text_carry.meta.json` | → | `GR_ZH91_text.meta.json` |
>
> **安装（一条命令，先关闭 Excel）**：
>
> ```powershell
> & C:\ProgramData\anaconda3\python.exe work/builds/GR_ZH91/temp/install_text_csv.py
> ```
>
> 脚本会复制 + 校验 sha256 + 跑 `--check-only` 预检并打印结论。
> 在此之前，正式位置那份仍是**旧格式 `text-csv/2`**（注入器会**拒绝**它 —— 这是预期行为，
> 见 §7 第 1 条；用户的改动**没有丢**，已在 `.meta.json` 的 `carry` 里逐条记录）。
> ⚠ 也请提醒用户：**别在 Excel 里点保存**，否则会把旧格式表写回去。

搬运记录（`.meta.json` 的 `carry`）：

```json
"carry": { "csv": "…/temp/GR_ZH91_text_v2_用户改动保留.csv", "csv_format": "text-csv/2",
           "edited_rows": 1,
           "carried": [ { "id": "SFXML:T0010", "mark": 7, "cell_chars": 144,
                          "break_positions": [15,28,38,52,63,78,92], "disk_len_now": 174 } ],
           "wrap_marks_carried": 7 }
```

> 开工前用户那份表（含他的编辑）已**逐字节备份**在
> `work/builds/GR_ZH91/temp/GR_ZH91_text_v2_用户改动保留.{csv,meta.json,txt}`
> （csv sha256 `33B144EE98B69E0E0B596F40A595690EB1404C1AC44EC7F606585187F9C5FE75`）。

---

## 5. 验收（六项，全部实跑；脚本与日志都在 `work/builds/GR_ZH91/temp/`）

### ① 往返零差异 —— `temp/t1_roundtrip_zero.py`，日志 `log_t1_roundtrip_zero.txt`

```
新 dump 的表（无任何人工改动）原样注入:
  [hash] src 42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88
  [hash] dst 42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88
  [hash] 逐字节相同 (无改动)
  [diff] 全盘差异 0 B / 3 个写入窗口; 窗口外差异: 无 ✓
  [verify] 条目 2232 / 2232 / 69 全部"逐字节不变"
【结论①】产物与基底 **逐字节相同** ✓  与现役盘 42d04a4f… 一致 ✓
```

⇒ **"没改动的条目一个字都不动"** 成立（这正是"dump 不再自动插 `{WRAP}`"的直接后果）。

### ② 用户改动生效 —— `temp/t2_user_wrap.py`，日志 `log_t2_user_wrap.txt`

```
# 人工断点: text_edited 里有 7 个 {WRAP} / {Warp} 标记 (分布在 1 行) —— 注入时**变成真换行** ({br}) ✓
#   SFXML:T0010 ×7
id                 kind     len_before  len_after    delta     行(前)     行(后)    br前    br后     人工断点
SFXML:T0010        long            174        194      +20        8        8      0      7        7
#   你写的断点位置: 第 15, 28, 38, 52, 63, 78, 92 个字符之后
#   盘上新增 {br} 位置: 第 15, 28, 38, 52, 63, 78, 92 个字符之后   ✓ 一一对应
#     ⏎ 第 15 个字符之后: …向反步兵地雷由曲面的⏎方形硬质弹体制成，内…
#     ⏎ 第 28 个字符之后: …质弹体制成，内装有大⏎约340克C3炸药。…
#     ⏎ 第 38 个字符之后: …约340克C3炸药。⏎其破片面由方形金属破…
#     ⏎ 第 52 个字符之后: …由方形金属破片构成，⏎起爆时破片以扇形射出…
#     ⏎ 第 63 个字符之后: …爆时破片以扇形射出。⏎由于装药的原因，地雷…
#     ⏎ 第 78 个字符之后: …原因，地雷在正后方会⏎存在一小片杀伤区，而…
#     ⏎ 第 92 个字符之后: …片杀伤区，而爆炸正面⏎则是大范围的毁伤区。…
盘上 SFXML:T0010: 注入前 {br}=0 {p}=0  →  注入后 {br}=7 {p}=0  (正文 174 → 194 B)
【核对】盘上 {br}=7 且 {p}=0 ✓ | 位置一一对应 ✓ | 去掉标记后文本==用户文案 ✓ | 无 "WRAP" 字面 ✓
【结论②】用户的 7 个断点全部按他指定的位置落到了盘上 ✓
产物盘: work/builds/GR_ZH91/temp/wrapctl.iso  sha256 1d30c1067beb8fc8534193486f23f75489447eb0487ab24d06ef66c0627120b6
```

### ③ 再 dump 回来 —— `temp/t3_redump.py`，日志 `log_t3_redump.txt`

```
text_zh 里的换行 = 7 个; {WRAP} 标记 = 0 个; text_edited == text_zh: True
Excel 里看到的这一格:
  1| M18 定向反步兵地雷由曲面的      5| 起爆时破片以扇形射出。
  2| 方形硬质弹体制成，内装有大      6| 由于装药的原因，地雷在正后方会
  3| 约340克C3炸药。                7| 存在一小片杀伤区，而爆炸正面
  4| 其破片面由方形金属破片构成，    8| 则是大范围的毁伤区。
第二轮往返: 原样注入 ⇒ 与 wrapctl.iso 逐字节相同 ✓
【结论③】7 个 {br} 变回 7 个真换行，断行位置与用户指定的一致 ✓
```

### ④ 多轮稳定 —— `temp/t4_multi_round.py`，日志 `log_t4_multi_round.txt`

```
起点: {br}=7 {p}=0 位置=[15,28,38,52,63,78,92] 可见文本hash=569090818eb7 字节=194
第 1 轮 再加 1 个断点（写成 {Warp}，小写开头）:
  盘上 {br}=8 位置=[15,17,28,38,52,63,78,92]; 可见文本 hash 不变 (569090818eb7); 字节 198 (+4 = 1 个 {br})
  ✓ 只多了 1 个断点, 其余一个都没动
第 1 轮 dump 回来: 9 行 (8 个真换行), {WRAP}=0 ✓
第 2 轮 把刚加的断点去掉: {br}=7 位置=[…] 可见文本 hash 569090818eb7 字节 194
  ✓ 回到起点的结构签名 (逐项一致, 无累积漂移)
第 2 轮 dump 回来 + 原样再注入: 与 r2.iso 逐字节相同 ✓
【结论④】三轮编辑/注入/dump 后断点数与位置**没有漂移**, 可见文本一字未变, 每轮往返零差异 ✓
```

### ⑤ 错误处理 —— `temp/t5_errors.py`，日志 `log_t5_errors.txt`

| # | 用例 | 退出码 | 报错要点（人话） |
|---|---|---|---|
| ① | 合法 `{Warp}`（小写） | **0** | 「人工断点: … 注入时**变成真换行**」 |
| ② | `{WRAP`（缺右括号） | **1** | 「断点标记**没写完** —— 缺少右边的花括号 }（正确写法: `{WRAP}`, 也接受 `{Warp}`）」 |
| ③ | `{WRP}` | **1** | 「这不是合法的断点标记 —— 只有两种拼写: `{WRAP}` 与 `{Warp}`…」 |
| ④ | `{WRAPP}` | **1** | 同上 |
| ⑤ | 行首 `{WRAP}` | **1** | 「断点标记在**文本最开头** —— 盘上会多出一个空行开头…」 |
| ⑥ | 行尾 `{WRAP}` | **1** | 「断点标记在**文本最末尾**…」 |
| ⑦ | `{WRAP}{WRAP}` | **1** | 「**两个断点标记紧挨着** —— 会写出连续换行 `{br}{br}`…想空一行请敲**一个空行**」 |
| ⑧ | `{WRAP}` 后紧跟换行 | **1** | 「断点标记**后面紧跟着换行**…」 |
| ⑨ | `{WRAP}` 前紧跟换行 | **1** | 「断点标记**紧跟在换行后面**…」 |
| ⑩ | 旧格式 `text-csv/2` 表（含 1548 个自动标记）直接注入 | **1** | 「这份 CSV 是**旧格式** (`text-csv/2`)…⇒ 拒绝注入」+ 给出 `--carry-edited` 重新 dump 的命令 |

九个用例全部 `--check-only` 跑，**未产出任何 ISO**（脚本逐个断言过）。

### ⑥ 实机验证（模拟器）—— `temp/nav_sf_weapons.txt` + 两个 dump 目录

* 导航（本机实测时间线；`runcap.py -grscanframes 4000`）：
  `引导 START×27 → 选择文件屏 上×3 + cross(载入 TEQSUNSET) → 主菜单 上×3 = 特别收录 → cross
   → 列表 下×3 = 武器 → cross → 武器内页（M18 默认选中）`
  （主菜单「快速任务」是灰项、光标会跳过 ⇒ 必须用 **up 回绕**数格子，不能用 down。）
* 抓帧：`F10900` = 武器内页稳态；`F9800` = 特别收录列表（选中「武器」）。
* 对照（同 nav、同帧）：

| | 介绍框内容（实机 F10900） |
|---|---|
| **注入前** `GR_ZH91.iso` | `M18 定向反步兵地雷由曲面的方` / `形硬质弹体制成， 内装约 340 克` / `C3 炸药。` / `其破片面由方形金属破片构成，` / `起爆时破片以扇形射出。` / `由于装药的原因， 地雷正后方存在` / `一小片杀伤区， 而爆炸正面则是大` / `范围毁伤区。`（引擎自动折行） |
| **注入后**（7 个 `{WRAP}`） | `M18 定向反步兵地雷由曲面的` / `方形硬质弹体制成，内装有大` / `约340克C3炸药。` / `其破片面由方形金属破片构成，` / `起爆时破片以扇形射出。` / `由于装药的原因，地雷在正后方会` / `存在一小片杀伤区，而爆炸正面` / `则是大范围的毁伤区。` |

* 逐帧回归（`tools/diag/snapdiff_all.py`）：**107 帧里 98 帧逐像素一致**；
  有差异的 9 帧 = `F10100..F10900`（正好是武器内页停留的那 9 帧），差异恒为 **6263 px**
  （变化区域 = 介绍文本框）。
* 图证据（都在 `temp/`）：
  * `wrapcmp_M18_f10900_zoom.png` —— 介绍框 **3 倍放大**，上=注入前 / 下=注入后；
  * `wrapcmp_M18_f10900_full.png` —— 整屏上下对照；
  * `dump_WRAPBEFORE/` `dump_WRAPAFTER/` —— 两轮各 107 张原生快照 + drawlog。

---

## 6. 复现命令

```powershell
$PY = 'C:\ProgramData\anaconda3\python.exe'
$T  = 'work/builds/GR_ZH91/temp'

# ① 往返零差异 / ② 用户改动生效 / ③ 再 dump / ④ 多轮稳定 / ⑤ 错误处理
& $PY $T\t1_roundtrip_zero.py
& $PY $T\t2_user_wrap.py
& $PY $T\t3_redump.py
& $PY $T\t4_multi_round.py
& $PY $T\t5_errors.py
& $PY $T\selftest_tcslib.py          # tcslib 口径自检 (47+ 条断言)

# ⑥ 实机 (先跑"注入前", 再跑"注入后"; 不要并发)
& $PY tools\text_csv\runcap.py WRAPBEFORE work/builds/GR_ZH91/GR_ZH91.iso `
      $T\nav_sf_weapons.txt 11000 100 6000 11000 4000
& $PY tools\text_csv\runcap.py WRAPAFTER  work/builds/GR_ZH91/temp/wrapctl.iso `
      $T\nav_sf_weapons.txt 11000 100 6000 11000 4000
& $PY tools\diag\snapdiff_all.py $T\dump_WRAPBEFORE $T\dump_WRAPAFTER 12
& $PY $T\mk_cmp_image.py             # 生成对照图

# 重新 dump 版本表 (用户改动用 --carry-edited 搬过来) + 重新生成单行副本
& $PY tools\text_csv\dump_text_csv.py --iso work/builds/GR_ZH91/GR_ZH91.iso `
      --out work/builds/GR_ZH91/text/GR_ZH91_text.csv `
      --carry-edited $T\GR_ZH91_text_v2_用户改动保留.csv
& $PY $T\regen_text_txt.py
```

---

## 7. 已知限制 / 注意（如实登记）

1. **旧表（`text-csv/1` `text-csv/2`）不能再注入**：注入器按 `.meta.json` 的 `format` 拦住
   （meta 丢失时按内容拦）。**必须用本轮重新 dump 的表**；用 `--carry-edited` 搬改动。
2. **旧版产品盘不能用**：Lead 之前用旧注入器跑出的产物（`a0dbf5ab…`）里 `{WRAP}` 是被**丢弃**的
   （文案变了、断点没生效）⇒ 请作废，改用本轮的 `temp/wrapctl.iso`（sha256 `1d30c106…`）
   或按 §6 重新注入。
3. **`LANG`（语言表）侧的人工断点未做新的实机验证**：代码路径与 `SFXML` 完全相同，
   且简报组件吃 `{br}` 已在此前实证；但语言表里还有菜单/列表等短条目，
   给 `kind=short` 的条目加换行时注入器会告警（组件未必走 RSHTML）⇒ 请先 `--only` 小批验证。
4. **`wrap_hint`/`wrap_preview` 是"模型预测"，不是实机读数**（模型 = `DoWordWrap` 口径，
   已被实机标定过）；它只是**只读提示**，不影响任何字节。
5. **`tools/iso_build/make_build.py` 有一处过期口径（本轮未改，铁律 #2）**：
   它的 TXT 快照 `make_text_snapshot()` 仍写 `.replace('{WRAP}', '')`。
   在构筑流程里**无害**（快照是对"刚产出的盘"重新 dump 的表，正文列里没有标记），
   但如果你手工把带 `{WRAP}` 的 CSV 喂给它当输入，TXT 视图会把标记删掉而不是显示成换行。
   建议后续把它改成 `re.sub(r'\{(?:WRAP|WARP)\}', '\n', txt, flags=re.I)`（一行改动）。
   同理，`make_build.py` 里 rc==1 的提示文案可补一句「也可能是断点标记写错/旧格式 CSV」。
6. **`docs/` 其它文档（`REPORT_wrap_br_fix.md` 等）里的 round35 口径未回改**：
   它们记录的是当时的事实（历史留档），**已由 FORMAT.md §3 与本源报告取代**。
7. 注入仍受**原槽位**限制（压缩帧不得超过槽位）与 `max_bytes` 提示；本轮 `SFXML` 用掉
   +20 B（尾部陈旧区 39056 B，压缩帧反而少 1 B）。

---

## 8. 给用户的一句话

> **你在 `text_edited` 里哪里写 `{WRAP}`（`{Warp}` 也一样），注入后游戏里就在哪里断行** ——
> 你那 7 个断点已经全部生效，实机画面见 `temp/wrapcmp_M18_f10900_zoom.png`（上=改前 / 下=改后）；
> 只读列 `wrap_hint` / `wrap_preview` 只告诉你"引擎现在会自动折在哪"，看一眼就行、改了没用。
> 另外：**请用本轮重新 dump 出来的那张表**（`text/GR_ZH91_text.csv`），
> 旧表里的 `{WRAP}` 是当年机器自动加的提示，已经不能再用它注入了。
