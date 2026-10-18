# 报告：重编码覆盖面补全（容器级登记表 + 陈旧码表追平）

> round58 · 工具 `tools/iso_build/font_compact.py` (r58.0) + `tools/iso_build/make_build.py`
> 交付盘 **`work/builds/GR_ZH108/GR_ZH108.iso`** · sha256 `0577f8dd06e6d123acc18aee3a59ba94bf25cc60a83b70e7b8f3f41d27fc9834`
> 基底 `work/builds/GR_ZH107/GR_ZH107.iso`（sha256 `de918f668301e8a15286b0dc55e30715491b0bc9b415d91b1bc3232919828ef0`，只读未改）

---

## 0. 一句话结论

**用户问"单独打补丁改那 8 条会不会每次重排都失效"—— 会。所以本轮把覆盖面补进了工具本身**：

1. **容器级文本登记表**（按**容器名/模式**，不写死索引）：`*_STRINGS.RES` / `*_STRINGS.TXT` /
   `*_SPECIAL_FEATURE.XML` / `IGORHELP.TXT` —— 本盘命中 **31 个容器**，从此每一轮重排都**必然**覆盖它们；
2. **容器级判据 + 逐段闭环**：登记容器内每一段"源码表能解出 ≥2 连续汉字"的字节都重映射，
   **不依赖 C 字符串 / NUL 边界**（这正是那 8 条引号串两轮都漏的原因），任何一段做不到 ⇒ 抛错、不写盘；
3. **一次性"陈旧码表追平"迁移**：`GR_ZH107` 已是紧凑盘 ⇒ 布局 0 改动 ⇒ 重编码这一遍本来根本不会跑；
   本轮按**内容寻址 + 盘 sha256 钉死**的清单，把 round46 第一次紧凑重排漏掉的 5 个容器追平到现役码表；
4. **`MENU.IMG#30 EN_STRINGS.TXT` 的那 8 条引号串全部修好**：解出来是 `追加弹药 / 望远镜 / 传感器 /
   爆破装药 / 无限制 / 仅手枪 / 仅主武器 / 仅原版`（= `docs/PATCH_INVENTORY.md` 记录的 **ZH57 设计值**），
   且经查实该文件自 **round46**（不是 round56）起就是坏的 —— 详见 §4。

验收：**31 个登记容器逐字闭环 31/31**；门禁 **16 项全过**；与 `GR_ZH107` 的差异 **共 16 字节，全部落在
5 个登记容器内**，PVD / 两个 IMG 条目表 / `GR.IMG#551..#565` / `FONT.RES` / ELF / 字库像素容器 **差异 0**；
紧凑布局（在用 1175 = slot 0..1174，空闲 329 = slot 1175..1503）与单格字库（1371/1373 = 99.85%，错误 0）**不变**；
对产物再跑一次 **0 改动**（幂等）。

---

## 1. 缘起：为什么不做"单独补丁 (c)"

用户的问题是：**"如果直接选择 c（单独补丁改那 8 条）会不会导致每次重排都失效？"**
答案是**会**：紧凑重排 = "把在用字形压到 slot 0..N-1"，**码位每次都变**；任何写死"旧字节 → 新字节"
的一次性补丁，下一轮重排就整体过期（而且过期后是**静默**变味，不报错）。
所以本轮选 (b)：**把"哪些容器载有引擎文本"这件事本身写进工具**，并让工具在**每一次**重排时逐段闭环地
重编码它们。

---

## 2. 现状普查（含"普查表口径的两个坑"）

### 2.1 普查表口径的坑（Lead 的 20 个容器清单是怎么来的）

Lead 的清单来自 `work/builds/GR_ZH107/text/GR_ZH107_view_*.csv`（`dump_containers.py` 的 view-only 表）。
复核时发现两个口径问题，都会影响"含中文容器"的判定：

| 坑 | 现象 | 后果 |
|---|---|---|
| ① `has_cjk=yes` 要求 **≥2 连续汉字**（`cjk_run>=2`），而 Lead 统计用的是 `cjk_run>=1` | 法语/德语的重音字节撞上**单字节码带**，每行出 1 个"汉字"（`Mission termin员e`） | `FR/ES/DE/IT_STRINGS.RES` 等被算成"含中文容器"（270/238/198/60 行），其实**与中文无关** |
| ② 表里的"串"有**最小长度闸门**，短引号值被整条丢掉 | `EN_STRINGS.TXT` 的值是 8 字节的 `"传感器"` ⇒ 表里那两行是 `has_cjk=no / cjk_run=0` | **真正出问题的那 8 条串所在的容器反而没进清单** |

⇒ 结论：**登记表不能从普查表推**。本轮的登记表按 `docs/` 的补丁记录/实证反推容器名，并用
`font_compact.py` 自己的容器级判据在盘上实测（见 §3、§6）。

### 2.2 全盘三代普查（4690 个容器 × 三代码表）

用 `work/builds/GR_ZH98/temp/r58/census_r58.py` 对**每个容器的展开态**做了三代解码对比：

| 代 | 来源 | 说明 |
|---|---|---|
| **G0** | `work/builds/GR_ZH94/temp/r46/charset_before_repack.json` | round46 **第一次**紧凑重排**之前** |
| **G1** | `work/builds/GR_ZH98/temp/r56/charset_before_r56.json` | round46 之后 … round56 之前 |
| **G2** | `tools/font_pipeline/data/charset_compiled_zh16.json` | 现役（round56 之后，本轮未改） |

结果（`census_r58.json` / `census_r58.log`，耗时 2355 s）：

```
容器 4690 个
  · 2635 个：连"换代会变的对偶码"都没有 ⇒ 换码也改不动它（直接判 0）
  · 1875 个：有 "≥2 连续汉字段" 会因换代而变字节（其中 1871 个**不在**登记表里）
  ·   58 个：展开态 > 4 MB 的巨型媒体容器，按"媒体数据"排除（普查表那 117 个含中文容器没有一个 > 200 KB）
```

**这 1871 个"未登记候选"是不是真文本？三条独立证据说"不是"：**

1. **工具自己的标定判据**（`texty`，round56 标定、零假阳：最长汉字串 ≥6 且该串汉字 ≥16 且不同字 ≥10
   且对偶码占比 ≥0.5）在本轮构筑里**扫了全部 4690 个容器**，选中 **3 个**（= 已知的
   `MENU.IMG#25/#902 EN_STRINGS.RES` + `MENU.IMG#283 EN_SPECIAL_FEATURE.XML`），
   **新发现文本容器 = 0**（构筑日志：`要处理的容器 31 个（其中**新发现**的文本容器 0 个）`）；
2. **单字节码带判据**：真文本的汉字走**对偶码**（2 字节），而芯片像素/压缩数据里的"汉字"绝大多数来自
   **单字节码带**（`charset.codes` 里那 110 个把 0x80..0xFF 映射成汉字的码，**从不因重排而变**）。
   实测"前 80 个汉字里带外占比"：
   `EN_SPECIAL_FEATURE.XML 0.54 / EN_STRINGS.RES 0.80 / EN_STRINGS.TXT 0.62`，
   而 **1871 个未登记候选里 ≥0.5 的有 0 个**（`census_bandfrac.py`）；
3. **内容长相**：候选的"中文"全是同一个字节带的重复噪声 —— `著著著著著著…`（`.RSB` 贴图）、
   `火习火习火习…`（`.QOZ` 武器模型）、`更伞磅进要纤…`（`.CHA` 角色动画）、
   `战指要命命它伞队练射…`（`.PSS` 视频）。它们的扩展名分布：
   `.RSB×538 / .CHA×321 / .BMZ×318 / .CHZ×140 / .QOB×118 / .SB×56 / .POB×50 / .QOZ×41 / .MAZ×38 …`
   —— 全是游戏资源，没有一个像文本文件。

**⇒ 回答 Lead 的问题"还有没有没被登记的含中文容器"：没有。**
本盘**真正载有引擎文本**的容器 = 登记表命中的 **31 个**（§6.1）+ ELF 的 5 语言载入提示槽
（`KNOWN_TEXT_REGIONS`，round57 已覆盖）+ 全盘扫描新发现的 **0 个**。

---

## 3. 覆盖面判据：为什么必须"容器级"

旧口径是**两层**，两层都漏：

* ①  "已知文本容器"按 `(lba, idx)` 写死 3 个 —— 索引一变（`--expand-entry` / 补丁搬条目）就失效；
* ②  全盘扫描的判据要求"**NUL 结尾的 C 字符串**"且"最长汉字串 ≥6"——
  `EN_STRINGS.TXT` 的值是 `\r\n\t"键"\t\t\t"值"` 形式的**行文本**，既不 NUL 结尾、最长也只有 3~4 个汉字，
  两层都抓不到（round57 报告 §6.1 列的"待 Lead 决策"就是它）。

r58 的判据（**容器级**）：

| 步骤 | 内容 |
|---|---|
| ①  | 容器**名字**匹配登记表模式（`^(EN\|DE\|ES\|FR\|IT)_STRINGS\.RES$` 等 4 条）⇒ 整个容器按"可能载有引擎文本"处理；**不看索引** |
| ②  | 容器内**每一段"源码表能解出 ≥ `min_cjk`（=2）连续汉字"的字节**都是重映射候选 —— **不要求 NUL 边界**（这正是 ② 层漏掉的原因） |
| ③  | 结构字节零改动：改动必须落在"被重映射的字符区间"内；LANG 格式容器进一步限制在**条目载荷**内（长度前缀 / 属性字节一个都不碰）。若 `parse_lang` 解不动（实测 `DE_STRINGS.RES`：`ngroups=66` 但某条 length 越界 ⇒ `struct.error`），退回**整块容器级**重映射，而不是把该容器排除在外 |
| ④  | **逐段闭环**：`目标码表解(改后同区间)` 必须与 `源码表解(改前同区间)` **逐字相同**；做不到 ⇒ `CompactError`（带**容器名 + 字节偏移**）、不写盘 |
| ⑤  | 逐容器报告：段数 / 重映射段数 / 未变段数 / 改动字节 / 跳过理由 |

**LZO 重压装不下时的兜底（新能力）**：我们的 LZO 压缩器比游戏原压缩器弱 ~3.6%，有些容器
（如 `DE_STRINGS.RES` 9 子流，整体重压 **+1985 B**）只改 1 个字节就**超槽**。这时若改动字节在
LZO 流里恰好是**字面量**（literal），就只改那几个字面量的**值**：**帧长逐字节不变、令牌结构不变**，
改完再回环校验（`解出来必须 == 目标字节`）。
本轮 `DE/ES_STRINGS.RES` ×4 个容器走的都是这条路（重压超槽 1985/1989 B ⇒ 字面量原位改写），
`EN_STRINGS.TXT` 走的是正常重压（改后帧 2718 B == 槽 2718 B，正好装下）。

---

## 4. 源代际判定：那 8 条串的"原字"到底是哪一代？

**这是本轮唯一需要 Lead 知晓的判断**：`MENU.IMG#30 EN_STRINGS.TXT` 的字节属于 **G0**
（round46 **之前**），不是 round57 报告里当"旧解"用的 G1。三条独立证据：

1. **6 份 round46 前的 charset 快照**（`GR_ZH92/93/94/font/charset_matching_this_disk.json`、
   `GR_ZH94/temp/r46/charset_before_repack.json`、`GR_ZH95/temp/font_repack/charset_before.json`、
   `work/_planc/charset_before_planc.json`）解这个容器的 **10 个键值完全一致**；
2. 那 10 个值**逐条等于** `docs/PATCH_INVENTORY.md`「GR_ZH57 … MENU.IMG EN_STRINGS.TXT 条目重写」
   记录的设计值（含"额不在字表 ⇒ 追加弹药"这个细节）：

   | 键 | 107 现役(G2)读法 | M107 的 G1 读法 | **G0 读法 = ZH57 设计值** | 108 现值 |
   |---|---|---|---|---|
   | `WPN_EXTRAAMMO` | 乎加弹巡 | 色加弹、 | **追加弹药** | 追加弹药 ✔ |
   | `ITM_BINOCULARS` | 航远镜 | 昨远镜 | **望远镜** | 望远镜 ✔ |
   | `ITM_SENSOR` | 侧抛器 | 传感器 | **传感器** | 传感器 ✔ |
   | `ITM_CLAYMORE` | 定向雷 | 定向雷 | **定向雷** | 定向雷 ✔ |
   | `ITM_BOMB` | 爆类装巡 | 爆破装、 | **爆破装药** | 爆破装药 ✔ |
   | `No Restrictions` | 无军制 | 无限制 | **无限制** | 无限制 ✔ |
   | `Pistols Only` | 午手枪 | 亲手枪 | **仅手枪** | 仅手枪 ✔ |
   | `Primary Weapons Only` | 午主武器 | 亲主武器 | **仅主武器** | 仅主武器 ✔ |
   | `Standard Kits` | 标准装备 | 标准装备 | **标准装备** | 标准装备 ✔ |
   | `Originals Only` | 午各秒 | 亲原版 | **仅原版** | 仅原版 ✔ |

3. **G1 本身就是 round46 打坏的读法**：`色加弹、/昨远镜/亲手枪/亲主武器/亲原版` 5 条是乱码或半乱码；
   只有 G0 是"人话 + 与补丁记录逐字对上"。

⇒ 本轮按 **G0 → 现役** 追平，于是这 10 条串**第一次**读成设计值（8 条引号串全部修好）。

> ⚠ 与 Lead 简报的差异（需要知情）：简报里把 `亲手枪` 当成"原字"之一 —— 那是 **G1（round46 起就坏）
> 的读法**（r57 报告 §6.1 表格的"旧解"列）。若 Lead 要的是"逐字保持 107 之前的 G1 显示"，把
> `STALE_MIGRATIONS[0]['stale_charset']` 换成 `work/builds/GR_ZH98/temp/r56/charset_before_r56.json`
> 即可（**改一个字段，不用改代码**），但那样 8 条里有 4 条仍是乱码。
> 另外：`EN_STRINGS.TXT` 的值**从不被游戏显示**（引擎读 `EN_STRINGS.RES`，见
> `tools/gr_tools/README.md`、`docs/han_v2/GR_SIDE.md`）⇒ 这条选择**没有实机风险**，
> 只影响"盘上文件读起来对不对"。

---

## 5. 工具改动清单

`tools/iso_build/font_compact.py`（r57.0 → **r58.0**）：

| 新增/改动 | 说明 |
|---|---|
| `CONTAINER_TEXT_REGISTRY` | 容器级登记表（4 条名字/模式 + 每条的 `min_cjk`/`kind`/`why`/`provenance`），`registry_match(name)` 按名字匹配 |
| `cjk_segments()` / `verify_segments()` | 容器级"段"口径 + **逐段闭环**（不依赖 NUL 边界；失败信息带容器名 + 偏移） |
| `plan_reencode()` | 登记容器全部进"要处理"集合；按角色选源码表（陈旧/现役）；逐容器出报告 `scan.registry`；写盘记录带 `src_cs` |
| `STALE_MIGRATIONS` + `pending_migration()` | 一次性"陈旧码表追平"清单：`from_iso_sha256` 钉死输入盘 + `entries` 按**槽位字节 sha256 内容寻址** + 文本指纹（角色 `migrate` / `current`） |
| `lzo1x_literal_origins()` + `Slot.repack_literal_patch()` | LZO 字面量原位改写（重压超槽时的兜底；帧长与令牌结构不变 + 回环校验） |
| `try_parse_lang()` | 安全版 `parse_lang`：结构畸形（实测 DE）时退整块容器级重映射，不抛异常 |
| `gate()` **A3** | 新增"登记容器全覆盖"硬门禁：31 个容器逐个给结论（已迁移 ⇒ 逐段闭环；现役 ⇒ 指纹；其余 ⇒ 证明"与码位无关"），**有洞 ⇒ 拒绝写 charset** |
| `gate()` A | 逐条按 `w['src_cs']`（每写盘动作自己的源码表）比对 —— 否则迁移容器会被"现役码表当源"误判 |
| `plan_compact()` | 迁移命中 ⇒ `changed=True` + `reencode_only=True`（布局/码位 0 改动，但确实要写盘） |
| `commit_charset()` | 只改 `pair_of` + 追加 `_font_compact`（本轮 `pair_of` 逐条不变） |

`tools/iso_build/make_build.py`：

* `run_font_compact()`：`reencode_only` 时**不生成**"强制重编码"文本表（布局与码位都没变，
  注入仍用用户原表 ⇒ 少一次无谓的整表重写）；
* 顺带修掉一个**潜伏 bug**：`info['reencode_containers']` 里读的是 `w['detail']['kind']`，
  而 `summ['reencode_writes']` 的元素没有 `detail` 键 —— 只要"字库步骤真的写了盘"就会 `KeyError`
  （r56/r57 都是单跑 CLI、r57 的构筑又恰好 0 改动，所以一直没暴露）。已改为 `w['kind']` 并补 `diff_bytes/method`。

---

## 6. 验收（全绿数字）

### 6.1 登记容器逐个：`旧码表解(GR_ZH107) == 新码表解(GR_ZH108)` 逐字相同

**先说清楚"31 个"与 Lead 清单的关系**：Lead 的清单（"17 个未覆盖 + 3 个已覆盖"）是**普查表口径**下的
子集，本轮按容器名/模式登记后，实际命中 **31 个** —— 比 Lead 的清单多出：`DE/IT_STRINGS.TXT` ×4
（德/意版本 TXT 里没有中文，属"登记了但 0 改动"）、`GR.IMG#4058 EN_SPECIAL_FEATURE.XML`、
`GR.IMG#4066 IT_SPECIAL_FEATURE.XML`、以及 **Lead 清单里漏掉的 `EN_STRINGS.TXT` 本体**
（`MENU.IMG#30`；GR 侧 `#903` 是英文原文、0 汉字）。

31 个容器**全部通过**（`verify_all_r58.py`，`verify_r58.json`）。角色口径：
`migrate/independent` 比"该容器字节实际所属的那一代"；`current` 比"现役解 vs 现役解"。

| 容器 | 角色 | 改动 | 段数 |
|---|---|---|---|
| `MENU.IMG#26 DE_STRINGS.RES` / `GR.IMG#900 DE_STRINGS.RES` | migrate | 1 B ×2（字面量原位改写） | 48 |
| `MENU.IMG#27 ES_STRINGS.RES` / `GR.IMG#904 ES_STRINGS.RES` | migrate | 1 B ×2（字面量原位改写） | 0 |
| `MENU.IMG#30 EN_STRINGS.TXT` | migrate | **15 B**（13 个字 / 重压） | 10（重映射 8 / 未变 2） |
| `MENU.IMG#25` / `GR.IMG#902 EN_STRINGS.RES`、`MENU.IMG#283 EN_SPECIAL_FEATURE.XML` | current | 0 B（指纹 ✓，已现役） | 2360 / 2360 / 2612 |
| 其余 23 个（`*_STRINGS.RES`、`*_STRINGS.TXT`、`*_SPECIAL_FEATURE.XML`、`IGORHELP.TXT` 等） | independent | 0 B（`陈旧解 == 现役解` ⇒ 与码位无关） | 0~28 |

* **31/31 逐字闭环**
* （对照）若一律拿 **G1(pre-r56)** 当"旧码表"：27/31 相同 —— 不相同的 4 个 =
  `MENU.IMG#30`（本轮**故意**用 G0，见 §4）+ 3 个现役容器（它们本来就在 G2 上，G1 解是乱码）

### 6.2 那 8 条引号串

`MENU.IMG#30 EN_STRINGS.TXT` 解出来（新码表）：`追加弹药 / 望远镜 / 传感器 / 定向雷 / 爆破装药 /
无限制 / 仅手枪 / 仅主武器 / 标准装备 / 仅原版` —— **10 个键逐条等于 `docs/PATCH_INVENTORY.md` 的设计值**，
8 条引号串全部修好（107 上是 `乎加弹巡/航远镜/侧抛器/爆类装巡/无军制/午手枪/午主武器/午各秒`）。

> 注：`dump_containers` 的普查表**看不到**这些串（§2.1 坑②），所以这一项只能靠"直接解容器"来验
> （工具的门禁 A/A3 与 `verify_all_r58.py` §2 都是这么做）。

### 6.3 紧凑布局（用户的核心诉求，保持）

```
在用 1175 = slot 0..1174 连续        ✓
空闲  329 = slot 1175..1503 连续     ✓
可 用 格 278 个全在末尾; 记录码占死 51; prefix_ok=True tail_ok=True; 搬运 0 个字 / 改码位 0 个
charset: 只改 pair_of（本轮逐条不变），iso_version=GR_ZH108
```

### 6.4 单格字库 / 字库 dump

| 项 | GR_ZH107 | GR_ZH108 |
|---|---|---|
| 单格字库逐像素一致 | 1371 / 1373 = **99.85%** | 1371 / 1373 = **99.85%**（不变） |
| 不匹配 | 2（**错误 0** / 警告 2） | 2（**错误 0** / 警告 2） |
| `dump_font` 缺字形 | 0 | **0**（字符 1384 / 有字形 1382 / 对偶 1175） |

### 6.5 其它硬指标

| 检查 | 结果 |
|---|---|
| `audit_inventory.py GR_ZH108 --missing` | 在役 44 条 / **缺失 0 条** / 其它 1 条 |
| `inject_text_csv.py --csv work/builds/GR_ZH107/text --check-only` | **exit 0** |
| 门禁（写盘后、改 charset 前） | **16 项全过**：C1~C4 / A×5 / A0 / A2 / B0 / **A3** / B / D / E |
| 幂等（对产物再跑 `font_compact --dry-run`） | **0 改动 / 不产出任何文件** |
| 文本快照与 107 逐表 sha256 | `long`/`long_nowrap`/`short`/合并 TXT **全部相同** ⇒ 注入是无损的（没有多余 diff） |

### 6.6 差异归属（`diff_attr_r58.py`，按**真实容器边界**算）

```
总差异: 16 字节 / 6 段 —— 全部落在 5 个登记容器内:
   MENU.IMG#30 EN_STRINGS.TXT   12 B（压缩帧里；解压态是 15 B，其余被匹配拷贝吸收）
   MENU.IMG#26 DE_STRINGS.RES    1 B      GR.IMG#900 DE_STRINGS.RES   1 B
   MENU.IMG#27 ES_STRINGS.RES    1 B      GR.IMG#904 ES_STRINGS.RES   1 B
允许区间之外            : 0 B   ✓
ELF (37.5 MB, 按 ELF 头算) : 0 B   ✓
PVD (LBA16..17)         : 0 B   ✓
两个 IMG 条目表           : 0 B   ✓
GR.IMG#551..#565 制作组名单: 0 B   ✓
FONT.RES 槽              : 0 B   ✓
字库像素容器              : 0 B   ✓（本轮没搬字）
```

### 6.7 门禁抓到的两个真问题（说明门禁不是摆设）

1. **试跑阶段**：`verify_segments` 的段闭环抓出 `MENU.IMG#30` 没被真正重映射
   （`源解 追加弹药 ≠ 目标解 乎加弹巡`）⇒ 查出"通用分支漏用陈旧映射"的代码 bug，修掉后才写盘；
2. **第一次真构筑**：门禁 A 拦下 `MENU.IMG#26 DE_STRINGS.RES`（"现役码表当源"误判）⇒
   **中止并在盘上回滚**：`GR_ZH108.iso` 中间态 sha256 == `GR_ZH107` 的 sha256（**逐字节回到基底**），
   charset 自动回滚。这正是"门禁不过就停、不留半成品"的实证。

---

## 7. 已知限制（如实说明）

1. **判据的语义边界**：登记表按**容器名模式**登记"这个容器载有引擎文本"。本轮的全部已知文本容器都在
   4 条模式里（31 个）；若将来某个补丁把中文写进别的容器（例如某个 `.ATR` 的 `<ActorName>`、`CAMPAIGN.XML`
   的标题属性），**必须往 `CONTAINER_TEXT_REGISTRY` 登记**（带出处），否则仍会像 `EN_STRINGS.TXT` 一样静默变味。
   兜底只剩"全盘扫描 + `texty` 判据"（要求最长串 ≥6，抓不到短串）。
2. **"陈旧码表追平"清单是一次性的**：它被 `from_iso_sha256` 钉死在 `GR_ZH107` 上，**下一轮自动失效**
   （不会误伤别的盘）。若将来又出现"某容器停在旧代际"，要新加一条清单（并像本轮一样给内容寻址 + 文本指纹）。
   `entries` 里的 `migrate/current` 角色是**人工判定的证据**（§4），不是自动推断。
3. **普查的体量口径**：全盘三代普查没有解析 > 4 MB 的巨型媒体容器（58 个，逐代解码要几十分钟，
   而它们的"汉字"必然是像素/压缩噪声）；普查表那 117 个含中文容器没有一个 > 200 KB。
4. **DE/ES 那 2 个字节的改动**：它们改的是**重音字节撞上对偶码**的"假汉字"（德语 `Hauptmenü`、
   西语 `Menú Principal`），改完"引擎看到的字"与 GR_ZH105 一致（不回归），但这几个语言本来就不是现役语言
   （实机跑中文/英文路径），**没有实机影响**；之所以坚持改，是为了让"旧解 == 新解"在**整个容器**上成立。
5. **`EN_STRINGS.TXT` 是死数据**：其值从不被引擎显示（引擎读 `EN_STRINGS.RES`）；修它是为了
   "盘上内容正确 + 空位不留坑"，**不代表实机会有可见变化**。
6. **实机 A/B 没跑**（本轮按 Lead 要求不做）：静态证据见 §6，实机验证由 Lead 用
   `tools/capture/run_opt.py`（单实例）做。
7. **工具文件在构筑后又清了一次死代码**（`font_compact.py` 里一份被并入统一出口的重复 `writes.append`
   留下的两行占位）；它只是个**无副作用的赋值**，删除前后行为完全相同。删完已用最终文件复跑：
   `--iso GR_ZH107 --dry-run`（迁移仍被正确识别）+ `--iso GR_ZH108 --dry-run`（**0 改动**、不产出文件）。

---

## 7.5 铁律遵守情况

| 铁律 | 执行 |
|---|---|
| 不动 git | 全程**没有**执行任何 git 命令（版本对比用 sha256 + 自己的脚本） |
| 不改历史 ISO（GR_ZH107 及更早只读） | `GR_ZH107.iso` 交付前后 sha256 均为 `de918f66…`（未变）；更早的 ISO 只读 |
| 不改 `GR_ZH107/text/`、已有 release | 只**读** `work/builds/GR_ZH107/text`（`--inject-csv` 的输入），未写 |
| 不改 `tools/text_csv/tcslib.py`、旧 `repack_font.py` | 两个文件本轮**一行未改**（工具只 import 复用） |
| charset JSON 只改 `pair_of` | 本轮 `pair_of` 逐条不变；`commit_charset()` 的自检保证除 `pair_of` 与 `_font_compact` 元信息外其余字段逐字节不变，并盖上 `iso_version=GR_ZH108` |
| 只往 `work/builds/GR_ZH108/`、`work/builds/GR_ZH98/temp/r58/` 写 | 所有中间产物/脚本/日志都在这两处；另按要求新建本报告 |
| 实机单实例、走 `run_opt.py` | 本轮不跑实机（由 Lead 做 A/B） |
| 门禁过不去就停 | 两次真的停过：试跑阶段的段闭环、第一次构筑的门禁 A（见 §6.7），都**没有绕过**，盘被完整回滚 |

---

## 8. 证据清单

| 路径 | 内容 |
|---|---|
| `work/builds/GR_ZH108/GR_ZH108.iso` | **交付盘**（sha256 `0577f8dd…`） |
| `work/builds/GR_ZH108/build_info.json` | 构筑信息（`font_compact` / `font_dump` / `text_snapshot`） |
| `work/builds/GR_ZH108/temp/font_compact/compact_report.json` | 方案 + 门禁 16 项 + `scan.registry`（逐容器段数/改动） |
| `work/builds/GR_ZH98/temp/r58/make_build_108.log` | 构筑全程（含门禁逐条输出） |
| `work/builds/GR_ZH98/temp/r58/verify_all_r58.py` + `.log` / `verify_r58.json` | §6.1~6.3 的验收脚本与结果 |
| `work/builds/GR_ZH98/temp/r58/diff_attr_r58.py` + `diff_107_vs_108.{log,json}` | §6.6 差异归属（允许区间按登记表算） |
| `work/builds/GR_ZH98/temp/r58/census_r58.py` + `census_r58.json` + `census_summary.py` / `census_bandfrac.py` | §2.2 全盘三代普查与判读 |
| `work/builds/GR_ZH98/temp/r58/probe_*.py`、`debug_de*.py`、`fast_repro.py` | §4 源代际判定 / LZO 字面量 / 定位过程的取证脚本 |
| `work/builds/GR_ZH98/temp/r58/verify/GR_ZH108__single_cell_report.{json,md}` | §6.4 单格字库逐字比对 |
