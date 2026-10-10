> **⚠ 2026-10-10 修正（Lead 复核时发现并修复）**
> 本报告首版的 ASCII 判据过严：把「default face 记录表里找不到字形」当阻断项，
> 会**误拦小写 `a-z`**（现役盘正文用了 5648 处且实机可读 —— 例 `Tom Clancy 的幽灵行` 的小写正常显示；
> 字形在 FT 的其它 face 里）。
> 现已改为：**ASCII 字形缺失只提示不阻断**（`ascii_no_glyph`），**汉字仍严格阻断**。
> 复检：含小写 ASCII 的改动 exit=0 且真实注入成功；含 `龘` 的改动 exit=3 且拒绝写盘。
> 详见 `tools/text_csv/FORMAT.md` 末尾附记与 `work/_dis/r32_test_ascii_fix.py`。

# REPORT_charset_guard.md — 注入前「字库覆盖预检」(round30)

> 用户原话：
> > 注入脚本**实际注入前要先进行检查字库是否覆盖完全**。
>
> 交付：`tools/text_csv/inject_text_csv.py` 在**真正写盘之前**逐字符检查每一条会被写入的文本；
> 有任何缺字 ⇒ **默认拒绝写盘**（退出码 3）并列出人话清单；`--force` 才强行继续（显著告警）；
> 新增 `--check-only` 只预检不写盘。公共检查器 = `tools/text_csv/tcslib.py::GlyphCache`。
>
> 测试脚本：`work/_dis/r30g_test_guard.py`（实跑日志 `work/builds/GR_ZH92_guard/r30g_test_guard.log`）
> 探针脚本：`work/_dis/r30g_probe_*.py`（25 个只读探针 + 11 张位图/联络表 PNG，逐条定案判据；结论见 §一）

---

## 一、检查项与判据

### 1.1 检查范围（与"真正会被写入"同口径）

只检查**注入器确实会写**的条目 —— 与主循环的过滤条件完全一致：

| 条件 | 说明 |
|---|---|
| 在 `--only` 选中的 id 内 | `--only` 之外的行本来就不写 |
| `resource` ∈ `T.RES` | 未知 resource 的行被跳过 |
| `text_edited` 非空且 ≠ 哨兵 `[[empty]]` | 空单元格 = 不改动这一条 |
| `text_edited` ≠ `text_zh` | ★ 「动过才生效」：与现值逐字相同的行整条跳过 |

⇒ **没改动 = 零检查 = 零影响**（全量 CSV 未改动时预检耗时 2.2 s，结论"字库覆盖完全"）。

### 1.2 逐字符三项检查

| # | 检查项 | 判据（盘上/表上实证） |
|---|---|---|
| ① | **能编码** | ASCII(<0x80) 直通；`U+E0xx` 按键图标占位直通；否则须在 `charset_compiled_zh16.json` 的 `codes`（单字节码）或 `pair_of`（对偶码）里查到 |
| ② | **盘上真有字形** | 见 §1.3（**不是**只看 JSON） |
| ③ | **不是死 pair** | 对偶码 lead 必须 ∈ `[0xA1,0xAE)`。ELF 四处 `sltiu reg, lead, 0xAE`（`0x416EE8 / 0x417160 / 0x41751C / 0x5656A4`）实测；`lead≥0xAE` 的 pair 会被引擎读成两个单字节 ⇒ 乱码 |

**问题分类**（报错文案对应）：

| kind | 人话 | 建议 |
|---|---|---|
| `not_in_charset` | 字符集里没有这个字 | 换常用字；或用工程手段扩字符集+字库 |
| `dead_pair` | 只有 lead≥0xAE 的双字节码 | 换字；或把该字加进单字节码/合法 lead 段 |
| `no_glyph` | 字符集里有，但盘上字库图集里那格是空的 | 换字；或先扩字库 |

### 1.3 ★ 「盘上真有字形」怎么查（本次逆向的核心）

**字形来源两条路，判据必须分开**（混淆过一次就是历史事故）：

```
① 单字节码 / ASCII  (< 0x80，或 charset codes 里的 0xAF..0xFE)
     idx = code - 0x20
     if idx < FT[0x44] (= fld[4]×fld[5] = 224)  ⇒  走 FT 记录表
        字形在 FT 记录矩形 (u0,v0)-(u1,v1) 处
        ⇒ 判据: 矩形内 / (+4,+2) / 邻域(±4,±2) 三档取或, 任一处有墨即算有字形

② 对偶 pair  (idx = (b1-0xA1)*94 + (b2-0xA1) + 0xE0 ≥ 0xE0 ≥ 224)
     ⇒ 永远走 ELF cave 硬编码网格公式, 与 FT 记录表无关
        slot = (b1-0xA1)*94 + (b2-0xA1)
        row = slot / 62 ; col = slot % 62
        x = 4 + 16*col ; y = 2 + 16*(row + 3*[row>=12])
        ⇒ 判据: 该 16×16 格内有墨即算有字形
```

**证据链**（`work/_dis/r30g_probe_*.py` 实跑）：

| 结论 | 证据 |
|---|---|
| 盘上位置 | `MENU.IMG#3 COMMON.PAK`（`off=0x57400`）、`MENU.IMG#4 FONT.RES`（`off=0xB9120`）；PAK 记录链 `new_font_revised` psm=0x14 1024×512 PSMT4，PX@`+0x146D`，**零余字节** |
| FT 记录表 | 展开态 5942 B；`u32[24]=3` 个 face（large/default/huge），每个 `fld[4]×fld[5]=32×7=224` 条 10 B 记录；`FT[0x44]=224` 正是 ELF cave 的 `idx<224` 阈值 |
| 单字节码走记录表 | `0xAF`(的) 记录矩形 `(16,178,32,194)` 的位图**就是「的」**（见 `r30g_probe_region.py` 位图打印）；`0xB7`(小)、`0xB0`(你) 同理 |
| pair 走网格公式 | 全部 1281 个 pair 按上式取格，1279 个有墨；只有 2 个（`欣` slot=1364 / `袁` slot=1426）落空 —— 而这两个字**本盘正文里根本没用到**（实测 0 处），且它们的 pair 都是死 pair（`AFD1` / `B0B1`），本来就不可编码 |
| 采样偏置 | 16px/PSMT4 的记录矩形 → 图集采样窗 = `(u0+4, v0+2)`（`docs/PROGRESS.md` §10「u 采样偏置随 psm 不同：13px/PSMT8 = rec.u+20，16px/PSMT4 = rec.u+4」）。实测：`0xE1`(向)/`0xE2`(和) 的矩形本体墨量 1/2（几乎空），但邻域内 25/26 ⇒ 必须带容差 |
| 图集墨语义 | PSMT4 texel `0`=墨、`1`=空；`CLUT[0]=0x8004`（alpha 位非零）⇒ 与 `docs/FONT_CURRENT_STATE.md` 一致 |
| **不误判 0xB7** | `0xB7` 是单字节「小」的合法码位（`codes` 实测），`enc_pair` 里**没有** `0xB7` 开头的条目 ⇒ 永远不会被当 lead。测试 T5 实证 |
| **不误判 lead 边界** | `0xA1`(方 pair A1BD) / `0xAF`(的) / `0xB0`(你) 三条各来一次，均**不在**问题清单里；而"对偶优先"会误读出来的 `弗`(`AF A1`) 被正确报为 `dead_pair` |

### 1.4 反向检查（本盘没有、英文原盘有的 ASCII）

对文本里每个 ASCII 字符：若 `charset JSON` 未声明该字符（不在 `codes` 里），就报出来，
并标注**现役图集里还有没有字形**：

* 有字形（如 `?` `]` `}` 空格）⇒ 提示"能正常显示，不阻断"；
* 没字形（小写 `a-z` 与 `^ _ \` | ~`，实测 31 个码位）⇒ 提示"画出来是空白"，**并且已由 ② 计入缺字清单 ⇒ 拒绝写盘**。

---

## 二、行为与退出码

| 退出码 | 含义 | 何时 |
|---|---|---|
| `0` | 成功 | 预检通过并注入完成；`--check-only` 时 = "可以注入" |
| `1` | 结构性错误 | CSV 与源盘 `offset/len` 不符、超槽、回读不符、`--force` 也写不进的不可编码字 |
| `2` | 参数/环境错误 | 非 `--check-only` 却没给 `--dst` |
| `3` | **字库覆盖预检不通过** | 有缺字且未加 `--force`；**此时一个字节都没写** |

* **默认拒绝写盘**：退出码 3，`--dst` 不产生文件（测试 T2/T4/T5/T6/T7/T10b 实证）。
* **`--force` 例外**：显式指定才继续，并打印
  `[!! 警告] --force 已指定: 预检不通过 (N 个字有问题), 仍继续注入。`
  `产物里这些字会显示为空白或乱码, 请务必人工核对。`
* **`--check-only`**：只预检不写盘，退出码反映结果，且**不产生任何文件**（连 `--report` 之外的都不建）。
* **`--report`**：新增 `charset_precheck` 一节，含 `verdict`（`pass`/`fail`/`forced`）、
  `font_source`、`checked_entries`、`problem_chars` / `missing_chars` / `dead_pair_chars`、
  逐字 `chars`（kind/char/cp/reason/locator/advice/hits[出现在哪些 id 第几处]）、`en_only_ascii`。
* 顺带修掉一个**老毛病**：`raise SystemExit(中文)` 走的是 stderr 原始编码（中文 Windows = GBK），
  会打出乱码。现在 `sys.excepthook` 里统一按 UTF-8 输出（`_excepthook`），所有报错都是人话中文。

---

## 三、性能

| 场景 | 耗时 |
|---|---|
| 全量 2261 条、未改动（0 条待检查） | **2.2–2.4 s** |
| 全量 2261 条 + 10 条改动（含 ~50 个不同字的字形查询） | **2.2 s**（`--check-only`） |
| 1000 次 `check_text`（含缓存命中） | **0.015 s** |

实现要点：`charset` 用 set/dict 查表（`Charset` 装载时一次性建好，不逐字重解析 JSON）；
图集**每行只做一次 `bytes.translate`**（C 速度拆 nibble），之后逐 texel 只查表；
每个字符的字形判定结果**按字缓存**（`GlyphCache._gc`），同一个字只查一次图集。

---

## 四、测试与证据（全部实跑）

测试脚本 `work/_dis/r30g_test_guard.py`；完整日志 `work/builds/GR_ZH92_guard/r30g_test_guard.log`。

| 项 | 内容 | 结果 |
|---|---|---|
| **T9** | 全量 2261 条 `--check-only` | exit=0，2.2–2.4 s，"字库覆盖完全 ✓" |
| **T1** | 从 `GR_ZH91` 现 dump CSV + 10 条合法中文改动 ⇒ 预检通过 / 注入成功 | exit=0；产物 sha256 **`89dee16df79a1c72f59dece572fc555dea7deefa18a6e129081ffe2ef2306b64`** |
| **T1b** | 同一 CSV 再跑一次 ⇒ sha256 稳定 | `89dee16d…` **一致** |
| **T1c** | 报告 `charset_precheck.verdict` | `pass` |
| **T8** | ★ **预检不改变正常注入结果**：`git show HEAD:` 原版注入器 vs 本版，同一 CSV/基底 | 原版 `89dee16d…` = 本版 `89dee16d…` **逐字节一致** |
| **T2** | 缺字例：塞 `龘`(U+9F98) / `𠮷`(U+20BB7) / `😀`(U+1F600) / `Ω`(U+03A9) | 4/4 **exit=3、拒绝写盘、清单含字+码点+id**；报告 `verdict=fail` |
| **T3** | `--force` 放行"可编码但无字形"（小写 `abc`） | exit=0、写出盘、**显著告警**；产物 `735fa93d…` |
| **T3b** | `--force` 遇到"根本没有可用编码"的字（`龘`） | exit=1、**仍未写盘**、报"没有任何字节序列能表示它" |
| **T4** | `--check-only` 不写盘 | 缺字 CSV exit=3 且**目录无新增文件**；合法 CSV exit=0；无 `--dst` 非 check-only exit=2 |
| **T5** | 边界例：`小`(0xB7)、`的`(0xAF)、`你`(0xB0)、`方`(A1BD)、`一`(0xC5)、`上`(0xFE) | 6 个**全部不误判**；唯一报出的是"对偶优先会误读出来"的 `弗`（`AF A1`，正确报 `dead_pair`） |
| **T6** | 死 pair 例：`欣`(`AFD1`)、`袁`(`B0B1`) | exit=3，正确报 `dead_pair` 而非"缺字" |
| **T7** | 反向检查：`abc XYZ_` | exit=3；`U+0061` 报"现役图集里也没有字形" |
| **T10** | `--only` 范围正确性 | 只选中的条目里缺字 ⇒ exit=3；缺字在未选中条目里 ⇒ exit=0 |

**失败项：无 —— 全部 PASS。**

### 4.1 缺字报错实例（真实输出，T2 `龘`）

```
===== 字库覆盖预检 (写盘前) =====
# 字库: 1024x512 @COMMON.PAK+0x146D; FT default face, 224 条记录
# 待检查(会被写入) 1 条; 逐字符检查完成
[!!] 发现 1 个「有问题的字」(共影响 1 处文本):
  ── 字符集里没有 U+9F98  「龘」
     原因: 字符集 (charset JSON) 里没有这个字
     出现在: LANG:G001.I000 (EN_STRINGS.RES@MENU+GR.IMG#902) 第 4 个字符 [G001.I000]
     怎么办: 该字不在本盘字符集里。要么改写文案换成常用字, 要么先扩字符集+字库再注入。

[拒绝写盘] 预检不通过: 1 个字有问题 (1 个字符集缺字 + 0 个死 pair)。
  怎么办: ① 按上面每条的建议改写文案 (最省事); 或 ② 先扩字库; 或 ③ 确要强行写入加 --force (会写出空白/乱码, 请自负)。
```

### 4.2 无字形报错实例（T7，小写字母）

```
  ── 盘上字库没有字形 U+0061  「a」
     原因: FT 记录 0x61 的矩形 (512,452,520,468) 及邻域在图集里是空的
     字形位置: FT rec[65]=(512,452,520,468)
     出现在: LANG:G001.I000 (EN_STRINGS.RES@MENU+GR.IMG#902) 第 1 个字符 [G001.I000]
     怎么办: 字符集里有这个字, 但盘上字库 (FT 记录/图集) 里没有它的字形, 写进去会显示空白。
             要么改写文案, 要么先扩字库。
```

### 4.3 产物

| 文件 | 说明 |
|---|---|
| `work/builds/GR_ZH92_guard/T1_guard.iso` | 正常例产物 `89dee16d…` |
| `work/builds/GR_ZH92_guard/T1_guard_rerun.iso` | 重跑，sha256 相同 |
| `work/builds/GR_ZH92_guard/T8_no_guard.iso` | 原版（无预检）产物，sha256 相同 |
| `work/builds/GR_ZH92_guard/T3_forced.iso` | `--force` 产物 `735fa93d…` |
| `work/builds/GR_ZH92_guard/T2_miss*_report.json` | 缺字例报告（`verdict=fail`） |
| `work/builds/GR_ZH92_guard/r30g_test_guard.log` | 完整实跑日志 |
| `work/text_csv/dev/r30g_*` | 测试用 CSV（**不动 `work/text_csv/*.csv`**） |

> 现役盘 `work/builds/GR_ZH91/GR_ZH91.iso` 全程只读，测试后 sha256 仍为
> `42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88`。

---

## 五、还查不出什么（**重要，请如实转述给用户**）

| # | 查不出来的东西 | 说明 / 影响 |
|---|---|---|
| 1 | **字形存在，但渲染宽度/行高不对** | 检查只回答"画得出来吗"，不回答"画得好不好看"。FT 记录里的宽度字节（`rec+1`）、face 的 `CharHeight`、四边距等几何量都没校；字宽不对会导致**排版错位**（挤在一起或撑开），预检放行 |
| 2 | **字形存在，但内容不是这个字** | 判据是"格里有墨"。若字库图集那一格被铺成了**别的字**（历史上 ZH32B 就发生过"清晰但全错位成别的字"），预检**查不出来**。本次只能靠"单字节码记录矩形位图人眼核对"（`r30g_probe_region.py`）抽查 |
| 3 | **字符集有、FT 记录表里却没有槽位** | `idx = code-0x20 ≥ 224` 的单字节码会被报 `no_glyph`（记录越界）；但 `pair` 的网格公式**不做边界检查**——`slot ≥ 42*62=2604` 时会算到图集外面，被 `no_glyph` 捕获（`欣`/`袁` 即此类）。若将来扩图集行数，这里的常量要同步改 |
| 4 | **"能编码但渲染成别处乱码"的组合情形** | 例如单字节码后面紧跟 ASCII 的字节组合，引擎按 DBCS 判据切分时可能与预期不同。预检只逐字符判定，不模拟整串解码 |
| 5 | **超长/超槽** | 由注入器原有的 `max_bytes` 与压缩帧超槽检查负责（退出码 1），**不是**预检的职责 |
| 6 | **换行/软换行是否正确** | 由 `wrap_w` / 渲染行数统计负责（注入器会打印行数前后对比），预检不管 |
| 7 | **其它资源里的文本** | 预检只覆盖 `LANG` + `SFXML` 两类（工具链的覆盖范围）；盘里其它 RES 字符串表、ELF 内字符串、纹理/影片字幕里的字**没查** |
| 8 | **字形"好不好看"（缺笔、糊、越窗）** | 需要像素级审计（历史上做过 `zh13_en_audit` 那类采样窗 ±1 邻墨审计），预检只做"有/无" |
| 9 | **多 face 差异** | 检查固定用 `default` face（引擎的 `GetFont` 调用者索引 4/5/6 与菜单侧 per-component fontID；现役 `style[0] ≡ style[1]`）。若某处走 `huge` face（96 条记录，只覆盖 0x20..0x7F），CJK 部分**本来就不走记录表**，无影响；但 ASCII 在 huge 面与 default 面若不一致，预检不区分 |
| 10 | **不检查 `text_zh` 列** | 只看 `text_edited`（真正会写的那一列）。`text_zh` 改了也不生效 |

### 5.1 本次顺带查出的**盘上既有问题**（不是本轮引入，供工程侧决策）

| 发现 | 证据 | 影响 |
|---|---|---|
| **小写英文 `a-z` 与 `^ _ \` \| ~` 在现役 16px 图集里没有字形** | EN 带（y=452..468）实测**有字形的码位 64 个**：`space !"#$%&'()*+,-./ 0-9 :;<=>?@ A-Z [ \ ] { }`；**无字形 31 个**：`^ _ \` a-z \| ~`。这 31 个的记录矩形**及 ±16/±8 大邻域全是空的**；用英文原盘对应字形做模板在整张图集里也搜不到 | 这些字符写进正文会**显示空白**。本盘正文里现用的小写共 **26 种、5648 次**（`a` 536、`e` 554、`r` 614…）—— 若实机确认这些位置是空白，需要重铺 EN 带（数据侧，不动 ELF） |
| **`欣`(slot=1364) / `袁`(slot=1426) 的网格格在图集里是空的** | 两个 slot 的 16×16 格墨量 = 0；它们的 pair 又是死 pair（`AFD1`/`B0B1`） | 本盘正文 0 处使用 ⇒ **无实际影响**；但字符表里留着这两个"不可用"条目，建议后续清理或补字形 |
| **`charset_compiled_zh16.json::grid` 是过时值** | 实测 `ncol=62/cw=ch=16/skip_row=12/skip_rows=3/x0=4`，JSON 里写的是 `37/13/13/14/…` | 无人读 `grid`（`docs/FONT_CURRENT_STATE.md` §三已记），仅误导人工阅读 |

> 上述三项都是**只读探查的结论**，本轮没有改动任何盘上数据（铁律：不动现役盘）。

---

## 六、给用户的一句话操作说明

> **在 Excel 里改完 `text_edited` 直接注入就行 —— 注入器写盘前会自己检查每个字在不在字库里；
> 有缺字它会拒绝写盘并告诉你"哪个字、在哪一条、怎么办"，你按提示换个常用字再来一次即可。**

想先确认再注入（不写盘）：

```powershell
& C:\ProgramData\anaconda3\python.exe tools/text_csv/inject_text_csv.py `
    --csv work/text_csv/GR_ZH91_text.csv `
    --src work/builds/GR_ZH91/GR_ZH91.iso --check-only
```

（退出码 0 = 可以注入；3 = 有缺字，看屏幕上的清单。）

---

## 七、改动清单

| 文件 | 改动 |
|---|---|
| `tools/text_csv/tcslib.py` | 新增 `parse_ft_faces()` / `parse_pak_records()` / `atlas_cell_xy()` / `GlyphCache`（字库覆盖检查器）；新增网格常量 `NCOL/CW/CH/GRID_*` 与 `GLYPH_DU/DV`、`GLYPH_TOL_*`、`FONT_FACE_DEFAULT` |
| `tools/text_csv/inject_text_csv.py` | 新增 `charset_precheck()` / `print_precheck()` / `charset_precheck_section()` / `_write_report()` / `_disp()` / `_excepthook`；新增 `--check-only`；`--dst` 改为可选；退出码常量 `EXIT_*`；`--force` 语义扩展；报告新增 `charset_precheck` 一节；修掉中文 `SystemExit` 乱码 |
| `tools/text_csv/FORMAT.md` | 新增 §6「注入前会自动做字库覆盖预检」（检查项/退出码/报错样式/小写字母已知限制），§4 加第 8 条，§0 加 `--check-only` 示例；原 §6/§7 顺延为 §8/§9 |
| `work/_dis/r30g_test_guard.py` | 验收测试脚本（T1–T10） |
| `work/_dis/r30g_probe_*.py` | 25 个只读探针（定案 FT/图集/判据）+ 11 张位图/联络表 PNG |
| `work/builds/GR_ZH92_guard/**` | 测试产物与日志 |

**未改动**：`dump_text_csv.py`、`tools/iso_build/**`、`docs/` 下其它文档、现役盘、
`work/text_csv/*.csv`（用户正在用的 CSV 一律没碰；测试 CSV 全在 `work/text_csv/dev/`）。
