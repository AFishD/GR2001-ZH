# REPORT_btn_placeholder.md — 手柄按键图标占位符「私有区字符 → ASCII 标记」（round33）

> 用户原话：
> > 出现问题：**excel 缺少字库 无法显示各个手柄按键占位符**，**修改使用其它符号**。

**交付**

| 文件 | 改动 |
|---|---|
| `tools/text_csv/tcslib.py` | 标记 ↔ 私有区占位 的双向编解码 + 校验；`is_placeholder` 新旧两写法都认；`charset` 自检加 36 项标记断言；`GlyphCache` 预检整体跳过标记 |
| `tools/text_csv/dump_text_csv.py` | CSV 输出 `{{BTN:XXXX}}` 标记 + `note` 写人话清单；**写 CSV 前的硬门槛**：三列里出现 PUA / 不可见控制字符就拒绝落盘 |
| `tools/text_csv/inject_text_csv.py` | 写盘**之前**全 CSV 前瞻扫描标记；写错 ⇒ 人话报错 + 拒绝注入（`--force` 也拦）；兼容旧私有区 CSV；预检不吃标记 |
| `tools/text_csv/FORMAT.md` | 新增 §5「手柄按键图标标记 `{{BTN:XXXX}}`」；§2/§4/§6/§8/§9 同步 |
| `work/text_csv/GR_ZH91_text.csv` | **重新生成**（源盘 `work/builds/GR_ZH91/GR_ZH91.iso`，`42d04a4f…`） |

**结论：8/8 项验收全部通过**，往返**零字节差异**，老 CSV **不受影响**。

测试脚本（本轮编号取 `r33_*`，因 `work/_dis/r31_*` `r32_*` 已被 round31/32 占用）：

| 脚本 | 作用 | 日志 |
|---|---|---|
| `work/_dis/r33_smoke_tcslib.py` | tcslib 单元级冒烟（不需要 ISO）**43/43 通过** | 控制台 |
| `work/_dis/r33_test_all.py` | 端到端 8 项验收 | `work/builds/GR_ZH92_btn/logs/*.log`，汇总 `work/builds/GR_ZH92_btn/r33_test_all_out.txt` |
| `work/_dis/r33_show_marks.py` | 新 CSV 的标记统计与人眼样例 | 控制台 |
| `work/_dis/r33_probe.py` | 占位字节分布侦察（按条目 / 按码位 / 上下文） | 控制台 |
| `work/_dis/r33_scan.py` | CSV 里 PUA / 控制字符 / 零宽字符扫描器 | 控制台 |
| `work/_dis/r33_diff_cols.py` | `text_zh` vs `text_edited` 逐行比对 | 控制台 |

---

## 一、问题与根因（先量清楚）

### 1.1 盘上到底有多少占位字节

`work/_dis/r33_probe.py` 从现役盘 `GR_ZH91` 直接数：

```
===== LANG =====
条目总数 2232; 含占位符条目 23; 占位符总数 30
按码位: 0xB1×7, 0xB5×21, 0xE7×1, 0xF1×1
  LANG:G012.I023 len=146 n=2  …按 [BTN:B5] 键添加路径点，按 [BTN:B1] 键删除。…
  LANG:G012.I024 len=107 n=1  添加路径点时按住 [BTN:B5] 键会出现一个射击扇面。…
  LANG:G012.I027 len= 80 n=1  …练习用左摇杆和 [BTN:B5] 键在队员之间切换。
  LANG:G059.I028 len=  8 n=1  Fran[BTN:E7]ais
  LANG:G059.I031 len=  7 n=1  Espa[BTN:F1]ol
===== SFXML =====
SFXML 含占位符条目 0, 占位符 0

===== 全盘: LANG+SFXML 正文里所有未映射字节分布 =====
  LANG: 未映射字节 0xB1×7, 0xB5×21, 0xE7×1, 0xF1×1
  SFXML: 未映射字节
```

* **23 条 / 30 个占位字节**，全在语言表，`SFXML` 侧 0 个。
* 简报里的「**60 次**」= 这些占位在 CSV 的 **`text_zh` + `text_edited` 两列**各出现一遍
  （`14/42/2/2` = `7/21/1/1` × 2 列）。语言表里**实际是 30 个占位字节**。

### 1.2 根因

`tcslib.Charset.decode` 对「字符表未映射的字节」回落成私有区字符 `U+E000 + 字节值`，
于是 `0xB1` → `U+E0B1`。这个回落本身是对的（保证 `encode(decode(b)) == b`，字节无损），
但 **Excel 没有任何 PUA 字形** ⇒ 单元格里只显示方框/空白，用户**看不见也就没法编辑**。

### 1.3 顺带发现：`0xE7` / `0xF1` 恐怕**不是**手柄按键

`U+E0E7` / `U+E0F1` 出现在两条**语言名**里：

| 条目 | 正文 | Latin-1 读法 |
|---|---|---|
| `LANG:G059.I028` | `Fran{{BTN:E0E7}}ais` | `Fran` **`ç`** `ais`（Français） |
| `LANG:G059.I031` | `Espa{{BTN:E0F1}}ol` | `Espa` **`ñ`** `ol`（Español） |

`0xE7`/`0xF1` 正好是 Latin-1 的 `ç`/`ñ`，而这两条又正好是语言选择菜单的法语/西语名。
**所以这两处很可能是"重音字母"，与"手柄按键图标"不是一回事**。

但——本盘字符表里这两个字节**没有映射**，工具链**没有依据**把它们当文字解出来。
按「不编造语义」的原则，本轮**一律**按同一格式标记化，并在 `note` 里如实写「手柄按键图标」，
在 §五「还查不出」里**明确挂账**：语义待专项逆向（哪个字节 = 手柄哪个键 / 哪个是重音字母）。

> 这也是为什么标记写成 **`{{BTN:XXXX}}`（码位）** 而不是 `{{键:方块}}`：**不猜。**

---

## 二、标记格式

```
{{BTN:E0B1}}
 └┬─┘└┬─┘└┬┘
  │   │   └── 4 位大写十六进制 = 原码位 (0xE000 + 原字节值)
  │   └────── 冒号
  └────────── 双花括号 + BTN (大小写不敏感, dump 输出统一大写)
```

| 要求 | 落实 |
|---|---|
| 一眼看出是「手柄按键图标」 | 词面就是 `BTN`；`note` 列再写明「含手柄按键图标 ×N: 请原样保留 …」 |
| 不会被误当正文删掉 | 双花括号 + 大写词，形状特殊；且**写错就拒绝注入**（见 §四 T4），删半边也拦 |
| 短 | 12 个字符（`{br}`/`{p}` 这类引擎标记只有 4~6，但那些在 CSV 里就是**换行**，不冲突） |
| Excel 复制粘贴不被打散 | **纯 ASCII、无空格、无换行、无逗号/引号** ⇒ 是一个不可分割的文本片段 |
| 不与引擎换行标记冲突 | `{br}` / `{p}` 是**单**花括号，`{{BTN:…}}` 是**双**花括号；实测现役盘 2261 行里**没有任何** `{` `}` `{{` `}}` 字面量（`work/_dis/r33_braces.py`） |
| CSV 里不再有 PUA / 不可见字符 | dump 端硬断言（§三.2），实测 0 个 |

**语义**：`{{BTN:E0B1}}` ≡ `U+E0B1` ≡ 盘上字节 `0xB1`。三者一一对应，**不涉及键名**。

---

## 三、实现

### 3.1 `tcslib.py`

| 新增 / 改动 | 说明 |
|---|---|
| `BTN_FMT` / `BTN_RE` / `BTN_PREFIX_RE` / `BTN_LO=0xE080` / `BTN_HI=0xE0FF` | 标记格式与**合法码位区间** |
| `pua_to_marks(text)` | `U+E080..U+E0FF` → `{{BTN:E0XX}}`（**dump 出 CSV 方向**） |
| `Charset.marks_to_pua(text)` | 正则逆运算（**注入方向**）；写错 → `BtnMarkError` |
| `Charset.scan_marks(text)` | 一次扫出**全部**问题，供「人话报错」用 |
| `Charset.btn_code_ok(code)` | 码位合法性：须在 `E080..E0FF`，且对应字节**不在** `codes` 里 |
| `Charset.is_placeholder(s)` | **新旧两写法都认**：单字符 `U+E080..U+E0FF`、整串 `{{BTN:XXXX}}`（大小写不敏感） |
| `Charset.encode / encode_strict` | 先 `marks_to_pua` 归一化 ⇒ 标记与私有区两条路**等价**，`encode(decode(b)) == b` 仍成立 |
| `GlyphCache.check_text` | **先 `BTN_RE.sub('', text)` 整体剔除标记**，再逐字符查字库 —— 不吃字库 ⇒ 绝不误报缺字 |
| `GlyphCache.en_only_ascii` | 同样剔除标记，免得报告里凭空多出 `{ B T N : 0 1 }` 8 个字 |
| `text_to_cell` | 输出单元格时自动带标记 |
| `cell_to_bytes_text` | 兼容两种写法（标记 / 原始私有区） |
| `selfcheck_charset` | 新增 36 项标记断言（往返、大小写、字节、7 种非法写法），**dump 时强制执行** |
| ⚠ 收紧 | `is_placeholder` 区间由 `U+E000..U+E0FF` 收紧为 **`U+E080..U+E0FF`**（`decode` 唯一可能产出的区间）；`U+E000..U+E07F` 以前会被 encode 写成 `0x00..0x7F` **裸控制字节**且回读不对称，现在按「字符集里没有」拒绝 |

**为什么 `decode` 仍返回私有区、不直接返回标记**（关键设计）：

1. **折行模型**：`strlen()` 按「一个占位 = 一个 16px 宽的字」算。若正文里是 12 字符的
   ASCII 标记，`ord(c) < 0x80` 会把宽度算成 `12×8 + 11 = 107 px`，`SFXML` 的软换行
   全部错位。保持私有区 ⇒ 折行模型**一行代码都不用改**（实测 `strlen('中\ue0b1文') = 50`）。
2. **字节级忠实**：`decode`/`encode` 是引擎口径的互逆函数，CSV 只是它的一个**视图**；
   视图层的写法转换放在 `pua_to_marks` / `marks_to_pua`，职责清楚。

### 3.2 `dump_text_csv.py`

* `text_zh` / `text_edited` 走 `T.text_to_cell` ⇒ 自动是标记写法。
* `note` 追加人话（实测样例）：

```
★含手柄按键图标 ×2: 请原样保留 {{BTN:E0B5}} {{BTN:E0B1}} 不要删改
  (这些标记 = 游戏里直接画出来的按键图标/特殊符号, 不吃字库;
   删掉或写错都会被注入器拒绝, 详见 FORMAT.md §4)
```

* **新增硬门槛 `assert_cells_clean`**：写 CSV **之前**逐字符扫 `text_zh`/`text_edited`/`note`，
  命中 PUA / C0（除 `\n`）/ DEL / C1 / 零宽 / 双向控制 / 软连字符 / BOM ⇒
  **拒绝写出 CSV** 并指名道姓。实跑输出：

```
[check] 已扫描 2261 行 × 3 个文本列的 162946 个字符: PUA 私有区 0 个 / 不可见控制字符 0 个 ✓
```

* 顺带修：`kind=locked` 的条目以前直接写原始私有区（本轮起 `pua_to_marks` 兜住），
  实测现役盘 locked = 0 条，属**预防性**修补。
* 统计口径修正：老口径 `0xAF..0xFE and not in codes` 数出「392 条含控制字节」（假阳性）；
  新口径按**解出来的正文里的私有区字符**数 ⇒ **23 条 / 30 个**（真实值）。

### 3.3 `inject_text_csv.py`

**★ 写盘之前**先做一次全 CSV 前瞻扫描（不碰 ISO ⇒ `--check-only` / `--dry-run` 同样会拦）：

```python
cs = T.Charset()
btn_probs, btn_used = scan_btn_marks(rows, cs)      # 扫 text_zh + text_edited 两列
n_btn, n_btn_bad = print_btn_marks(btn_probs, btn_used)
if btn_probs:
    ... 写出报错 + 可选 --report ...
    sys.exit(EXIT_STRUCT)                           # 退出码 1 —— --force 不参与
iso = T.Iso(a.src)                                   # 到这里才开始碰盘
```

* 逐行兜底：`cell_to_bytes_text` 抛 `BtnMarkError` 时**先于** `CharsetError` 接住，
  给「哪一条 / 哪个标记 / 怎么写 / 怎么办」的人话报错（不落进「这个字字符表里没有」的泛泛提示）。
* **兼容**：`Charset.encode_strict` 内部归一化 ⇒ 老 CSV 的原始私有区字符照旧能注入。
* **预检放行**：`GlyphCache.check_text` 整体剔除标记；`charset_precheck` 另行计数并打印：

```
# 其中含手柄按键图标标记 3 处: {{BTN:E0B1}} {{BTN:E0B5}}
#   这些标记由引擎**直接画图标**, 不吃字库 ⇒ 已整体跳过字形检查, 不会、也不该被报成缺字 ✓
```

* 报告/控制台里的 `text_before` / `text_after` 改用 `pua_to_marks` 显示（人看得见），
  折行行数仍用私有区形式算（不污染模型）。
* `--report` 新增 `btn_marks` 一节（`total` / `distinct` / `problems`）。

---

## 四、验收实测（全部实跑）

### T1 扫描证明

```
文件: work/text_csv/GR_ZH91_text.csv (2261 行, 622104 B)
扫描了 text_zh / text_edited / note 三列共 162946 个字符
  PUA 私有区 (U+E000..U+F8FF)  : 0 个 (0 ✓)
  不可见控制字符 (C0/DEL/C1)   : 0 个
  零宽 / 双向控制 / BOM        : 同上一并计入, 合计 0 个
  ---- {{BTN:XXXX}} 标记 ----
  text_zh     : 30 处
  text_edited : 30 处
  note        : 30 处 (人话提示里列举的现成标记)
  文件内合计  : 90 处
  含标记的条目: 23 条 (与语言表里含占位字节的条目数一致)
  按码位 (text_zh 列 = 语言表里真实的占位字节数): {{BTN:E0B1}}×7, {{BTN:E0B5}}×21, {{BTN:E0E7}}×1, {{BTN:E0F1}}×1
  ⇒ text_zh + text_edited = 60 —— 即简报里说的「60 次」
```

> **关于「60」**：`text_zh` 30 + `text_edited` 30 = **60**（与简报一致）；
> `note` 列另有 30 处**提示性**引用 ⇒ 文件内合计 **90**。语言表里实际占位字节 = **30**。

`work/_dis/r33_scan.py`（独立扫描器，不依赖工具链）交叉验证：

```
===== work\text_csv\GR_ZH91_text.csv =====
  文件大小 622104 B
  [ok] 未发现 PUA / 不可见控制字符 / 零宽字符 ✓
```

### T2 往返零差异（新格式）

```
命令: inject --csv work/text_csv/GR_ZH91_text.csv --src GR_ZH91.iso --dst GR_ZH92_btn.iso
退出码: 0
[diff] 全盘差异 0 B / 3 个写入窗口; 窗口外差异: 无 ✓
  EN_STRINGS.RES@MENU    条目 2232: 改动 0 / 逐字节不变 2232; ngroups=66 结构重解析 OK
  EN_STRINGS.RES@GR      条目 2232: 改动 0 / 逐字节不变 2232; ngroups=66 结构重解析 OK
  EN_SPECIAL_FEATURE.XML 条目 69: 改动 0 / 逐字节不变 69, 结构计数不变
[hash] src 42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88
[hash] dst 42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88
[hash] 逐字节相同 (无改动)
```

⇒ dump（新格式）→ 原样注入 ⇒ **sha256 与输入 ISO 逐字节相同** ✓

### T3 真实改动（含标记的条目，只改汉字）

改 2 条：`LANG:G012.I023`（`给`→`向`）、`LANG:G012.I024`（`或`→`和`）。
两条**都带按键标记**（前者 2 个：`{{BTN:E0B5}}` `{{BTN:E0B1}}`；后者 1 个：`{{BTN:E0B5}}`）。

```
退出码: 0
# 按键标记: 共 60 处 / 4 个不同的标记: {{BTN:E0B1}} {{BTN:E0B5}} {{BTN:E0E7}} {{BTN:E0F1}}
===== 字库覆盖预检 (写盘前) =====
[ok] 字库覆盖完全: 每条文本的每个字符都能编码, 且盘上都有字形 ✓
# 候选 2261 行; 实际改动 2; 未改动(与 text_zh 相同)跳过 2248; 与源盘等价跳过 11; 不在 --only 内 0
LANG:G012.I023     long_nowrap        146        145       -1        1        1
LANG:G012.I024     long_nowrap        107        106       -1        1        1
[hash] dst 2d1c46bed2a3c5c403f30722e7cd3c29676d25e4d8b292c23a9e7bef6f27d28e
```

**前后字节 dump（`LANG:G012.I023`，146 B → 145 B）**

```
改前: b0 af b7 c1 …（略）… b9 20 b5 20 b2 a3 b7 a2 be a1 e3 a2 a1 a1 dd a8 cb b9 20 b1 20 b2 a2 b4 a1 cb a8 cc b3 c7 a2 c2 42 c4 d1 …（略）…
                                                              ↑↑            ↑↑              ↑↑
                                                            0xB5          0xB1            给= A2 C2
改后: b0 af b7 c1 …（略）… b9 20 b5 20 b2 a3 b7 a2 be a1 e3 a2 a1 a1 dd a8 cb b9 20 b1 20 b2 a2 b4 a1 cb a8 cc b3 c7 e1 42 c4 d1 …（略）…
                                                            0xB5          0xB1            向= E1
```

完整字节串见 `work/builds/GR_ZH92_btn/r33_test_all_out.txt`，逐条断言结果：

```
  ── LANG:G012.I023
     标记字节 ['0xB5', '0xB1'] vs ['0xB5', '0xB1']  → 一致 ✓
     标记在正文中的位序 [55, 66] vs [55, 66]  → 一致 ✓
  ── LANG:G012.I024
     标记字节 ['0xB5'] vs ['0xB5']  → 一致 ✓
     标记在正文中的位序 [9] vs [9]  → 一致 ✓
```

⇒ 只改了汉字（`给`→`向` 少 1 B），**标记对应的字节与原来逐字节相同、位置也相同** ✓

### T4 错误处理（5 种写错，三条路都拒）

| 用例 | 写入 | 报错（人话） | exit（正常/`--force`/`--check-only`） | 产物 |
|---|---|---|---|---|
| `bad_hex` | `{{BTN:ZZZZ}}` | 冒号后面必须是**4 位十六进制数字** 0-9 A-F（你写的是 `'ZZZZ'`，共 4 个字符…） | 1 / 1 / 1 | 未产出 ✓ |
| `no_close` | `{{BTN:E0B1` | 标记没写完 —— **缺少右边的两个花括号 `}}`** | 1 / 1 / 1 | 未产出 ✓ |
| `unknown_cp` | `{{BTN:1234}}` | 码位 U+1234 不在可用区间 U+E080..U+E0FF 内 | 1 / 1 / 1 | 未产出 ✓ |
| `one_brace` | `{BTN:E0B5}` | 花括号只写了**一个** —— 两边都必须写**两个**花括号 | 1 / 1 / 1 | 未产出 ✓ |
| `mapped_cp` | `{{BTN:E0AF}}` | 码位 U+E0AF 就是字节 0xAF，而它在本盘字符表里是正常汉字「的」 | 1 / 1 / 1 | 未产出 ✓ |

实跑原文（`bad_hex`，完整报告见日志 `logs/03_bad_bad_hex.log`）：

```
[!!] 发现 1 处**写错的按键标记** —— 拒绝注入 (--force 也不能绕过):
  ── LANG:G012.I023  (text_edited 列  @EN_STRINGS.RES@MENU+GR.IMG#902)
     你写的是: '{{BTN:ZZZZ}}'
     问题    : 冒号后面必须是**4 位十六进制数字** 0-9 A-F (你写的是 'ZZZZ', 共 4 个字符; 常见错因: 少写/多写一位, 或用了非十六进制字母)
  正确写法只有一种: {{BTN:XXXX}} —— 双花括号 + BTN + 冒号 + 4 位十六进制。
  例如: {{BTN:E0B1}}
  ★ 本 CSV 里现成的正确标记有: {{BTN:E0B1}} {{BTN:E0B5}} {{BTN:E0E7}} {{BTN:E0F1}}
    最稳的做法: 在 Excel 里**直接从 note 列复制**一个现成的标记粘贴过去。
  ★ 为什么必须拦: 写错的标记**没有任何字节序列**能表示它, 只能改 CSV。
    若放行, 游戏里会原样显示出 "{{BTN:..." 这串英文字符。
[拒绝注入] 有 1 处按键标记写法错误, 未写任何文件。
```

⇒ **写错必定被拦，且绝不当普通文本写进去**；`--force` 也**不能**绕过（写错的标记没有任何字节能表示）。 ✓

### T5 兼容性（旧的私有区 PUA 版 CSV）

用 round30 时代 dump 的老 CSV（`work/text_csv/dev/r30g_GR_ZH91_text.csv`，`text_zh` 列里
仍是原始私有区字符 **30 个**）：

```
退出码: 0
[diff] 全盘差异 0 B / 3 个写入窗口; 窗口外差异: 无 ✓
[hash] src 42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88
[hash] dst 42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88
[hash] 逐字节相同 (无改动)
```

⇒ **换格式不会把老 CSV 弄坏**；新旧两种写法产物**逐字节相同** ✓

### T6 预检不吃标记

```
退出码: 0
# 按键标记: 共 60 处 / 4 个不同的标记: {{BTN:E0B1}} {{BTN:E0B5}} {{BTN:E0E7}} {{BTN:E0F1}}
===== 字库覆盖预检 (写盘前) =====
# 待检查(会被写入) 2 条; 逐字符检查完成
# 其中含手柄按键图标标记 3 处: {{BTN:E0B1}} {{BTN:E0B5}}
#   这些标记由引擎**直接画图标**, 不吃字库 ⇒ 已整体跳过字形检查, 不会、也不该被报成缺字 ✓
[ok] 字库覆盖完全: 每条文本的每个字符都能编码, 且盘上都有字形 ✓
```

未经改动的全量 CSV 也一样：`--check-only` ⇒ `exit=0`。 ✓

### T7 `--check-only` 也能拦

```
退出码: 1
# only: (全部)   CHECK-ONLY
[!!] 发现 1 处**写错的按键标记** —— 拒绝注入 (--force 也不能绕过):
     问题    : 标记没写完 —— **缺少右边的两个花括号 }}**
[拒绝注入] 有 1 处按键标记写法错误, 未写任何文件。
```

⇒ 预检阶段就能拦下，**不产出任何文件** ✓

### T8 CSV 洁净硬门槛（dump 端，防回归）

`dump_text_csv.assert_cells_clean` 在**写 CSV 之前**执行 —— 用 11 类「Excel 看不见」的
字符合成单元格，断言一律拒绝落盘；同时断言正常行（含标记与 LF 换行）放行：

```
  PUA 私有区 (方框根因)         U+E0B1 → 拒绝 ✓  LANG:TEST.I000 的 text_zh 列 @第 2 个字符: U+E0B1 (私有区占位)
  PUA 越界                 U+E041 → 拒绝 ✓  … U+E041 (私有区占位)
  TAB 制表符                U+0009 → 拒绝 ✓  … U+0009 (不可见控制字符)
  C0 控制字符                U+0001 → 拒绝 ✓  …
  C0 控制字符 (CR)           U+000D → 拒绝 ✓  …
  C1 控制字符                U+0085 → 拒绝 ✓  …
  DEL                    U+007F → 拒绝 ✓  …
  零宽空格                   U+200B → 拒绝 ✓  …
  双向控制符                  U+202E → 拒绝 ✓  …
  BOM                    U+FEFF → 拒绝 ✓  …
  软连字符                   U+00AD → 拒绝 ✓  …
  正常行 (标记+换行)            → 放行 ✓ (57 个字符: 标记 + LF 换行都合法)
```

⇒ 用户要求的「CSV 里不允许再出现任何 PUA / 不可见控制字符」**不只是观测结果，
而是 dump 端会主动拒绝违反的文件**（宁可不给文件，也不给一份看不见内容的文件）✓

### 附加：`tcslib` 单元冒烟 43/43

`work/_dis/r33_smoke_tcslib.py`（不需要 ISO）覆盖：`is_placeholder` 新旧写法、
`marks_to_pua` / `pua_to_marks` 往返、大小写不敏感、7 种非法写法全拒、
`{br}`/`{p}` 与标记互不干扰、折行模型宽度不变、`U+E041` 越界被拒。**合计 43 通过 / 0 失败**。

### 附加：`dump_text_csv.py` 自检（每次 dump 强制跑）

```
# [ok] is_placeholder('{{BTN:E0B1}}')=True (标记新写法)
# [ok] {{BTN:E0B1}} → '\ue0b1'
# [ok] '\ue0b1' → {{BTN:E0B1}}
# [ok] {{BTN:E0B1}} 编码为字节 0xB1
# [ok] 旧写法 '\ue0b1' 编码为同一字节 0xB1 (向后兼容)
# [ok] 标记大小写不敏感 ({{btn:e0b1}})
# [ok] 非法标记 '{{BTN:ZZZZ}}' / '{{BTN:E0B1' / '{BTN:E0B1}' / '{{BTN:1234}}' / '{{BTN:E0AF}}' … 被拒绝 (BtnMarkError)
# [ok] 字表中 lead>=0xAE 的死 pair 137 个, 编码器已拒绝写出
```

---

## 五、还查不出 / 覆盖不到的（如实挂账）

1. **占位字节的语义未知**。哪个字节 = 手柄哪个键、`0xE7`/`0xF1` 是不是重音字母（§1.3），
   **本轮没有逆向**，标记只写码位、**不编造键名**。需要时另立任务（建议做法：在指挥地图
   教程页做帧捕获 + `0x21ADE0` UV 表的写入点下断，把"哪个字节 → 哪张图标 UV"对上）。
2. **只覆盖 `LANG` + `SFXML` 两类资源**（与 round29/30 同口径）。盘里其它字符串表 /
   ELF 内字符串 / 纹理字幕里的占位字节**没扫过**。本轮只保证：这两类资源里，
   **CSV 中出现 PUA 会当场拒绝落盘**（§三.2），不会静默漏出去。
3. **合法码位区间是"由 decode 反推"的**（`E080..E0FF` 且字节未被 `codes` 占用）。
   将来若扩字符表把某个字节占用掉，**老 CSV 里对应的标记会被新判据拒绝**
   （报「该码位现在是正常汉字」）—— 这是**有意**的（宁可报错也不写错），但需要在扩表时记得。
4. **`markers 校验不查 ISO**：标记扫描是纯 CSV 内容检查，**早于**源盘结构校验。
   若 CSV 里同时有「标记写错」和「offset 与源盘不符」，只会先报标记错（改完再报后者）。
5. **Excel 行为未实机验证**：本轮只保证"CSV 文件里不再有 PUA / 不可见字符"
   （这是"Excel 显示方框"的充分原因），**没有真的用 Excel 打开截图**。
   标记是纯 ASCII，按定义不会被 Excel 吃掉；但如果用户在 Excel 里用了「查找替换」
   把 `{` 或 `}` 批量换掉，仍会破坏标记 —— 这种情况注入器会如实报错拒绝（T4）。
6. **`kind=locked` 条目**在现役盘是 0 条，本轮只是预防性修补，**没有真实样本**验证。
7. **`is_placeholder` 区间收紧**（`E000..E07F` 不再算占位）属行为变更：
   现役盘无此数据，但若有**第三方**工具链依赖旧行为，会看到「charset 无此字」的新报错
   —— 这个报错**比原来更正确**（原来会写出裸控制字节），但值得知会。

---

## 六、给用户的一句话

> 手柄按键图标的**方框已经换成看得见的 `{{BTN:E0B1}}` 这种标记**了，在 Excel 里直接就能
> 看到、能复制粘贴；**你只改汉字就行，这几个花括号里的东西原样别动**。
> 万一不小心删掉一半或者打错，注入器会**当场拦下并告诉你哪里错了、该怎么写**，
> 绝不会把 `{{BTN:...` 这串字写进游戏里。旧的文件也照样能用。

---

## 附：改动文件与产物清单

| 路径 | 说明 |
|---|---|
| `tools/text_csv/tcslib.py` | 公共库（标记编解码 + 校验 + 预检放行） |
| `tools/text_csv/dump_text_csv.py` | dump（标记输出 + note + CSV 洁净硬门槛） |
| `tools/text_csv/inject_text_csv.py` | 注入（标记前瞻拦截 + 兼容 + 预检） |
| `tools/text_csv/FORMAT.md` | 新增 §5；§2/§4/§6/§8/§9 同步 |
| `work/text_csv/GR_ZH91_text.csv` | 重新生成的 CSV（2261 行，607.5 KB） |
| `work/text_csv/GR_ZH91_text.meta.json` | 配套 meta（源盘 `42d04a4f…`） |
| `work/_dis/r33_*.py` | 6 个测试 / 探针脚本 |
| `work/builds/GR_ZH92_btn/logs/*.log` | 子进程实跑日志（22 份） |
| `work/builds/GR_ZH92_btn/r33_test_all_out.txt` | 验收汇总（8/8） |
| `work/builds/GR_ZH92_btn/r33_report_{roundtrip,edit,legacy}.json` | 注入报告 |
| `work/builds/GR_ZH92_btn/GR_ZH92_btn.iso` | 往返验证产物（sha256 = `42d04a4f…`，与源盘相同） |
| `work/builds/GR_ZH92_btn/GR_ZH92_btn_edit.iso` | 真实改动产物（sha256 = `2d1c46be…`） |
| `work/builds/GR_ZH92_btn/GR_ZH92_btn_legacy.iso` | 旧 CSV 兼容验证产物（sha256 = `42d04a4f…`） |

**未动**：现役盘 `work/builds/GR_ZH91/GR_ZH91.iso`（只读，sha256 仍 `42d04a4f…`）、
`tools/iso_build/**`、`docs/` 下其它文档、`MENU.IMG` 内部偏移、`GR.IMG` 条目表
`off`/`stored`/`real`、制作组名单 `GR.IMG #551..#565`；**未做任何 git 操作**。
