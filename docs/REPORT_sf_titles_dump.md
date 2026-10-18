# round62 报告 —「特别收录」标题在 CSV 里搜不到: 根因 + 补全

* 分支: `round62/sf-titles-dump`
* 现役盘: `work/builds/GR_ZH109/GR_ZH109.iso` (sha256 `a0558f4e…b919a`, 1 648 164 864 B)
* 改动: **只改** `tools/text_csv/dump_containers.py` (文本 dump 工具) + 新增本报告与临时验收脚本
* 未动: 任何 ISO / 字库 / `GR_ZH109/text/`（上一轮产物）/ release / `tcslib.py` / `make_build.py` / `repack_font.py` / `font_compact.py`; 未 commit

---

## 1. 用户报告与结论

> 「我想要在 CSV 中查找标题对应的字符串 但是没有搜索到 我搜索的是**国会荣誉勋章** 但是搜索到的只有这一个标题下的正文内容而没有标题 是不是脚本漏扫描了」

**用户说得对: 脚本确实漏扫了。** 有两处独立原因, 缺一不可:

| # | 原因 | 证据 |
|---|------|------|
| ① | 「特别收录」的**条目名/组名/工作室名**存在 `EN_SPECIAL_FEATURE.XML` 的 `<item name="…">` / `<group name="…">` / `<studio name="…">` **属性**里, 而 `dump_text_csv.py` 只导出 `<text>…</text>` 元素 (`tcslib.TEXT_RE`, 见 `REPORT_en_column.md` 之后的口径) ⇒ **标题从来没进过任何可注入表** | 改动前 13 张 CSV 里, 123 个含中文的属性名只有 28 个能搜到 (巧合) |
| ② | `dump_containers.py` 的**通用串扫描**也看不见它们 —— 第 2 关「像文本」判据的可见字符表 `OKVIS_RE`(>=0.85) 与字母数字表 `WORD_RE`(>=0.55) **只含 ASCII**, 一个"以汉字为主"的串必然被判"不像文本"丢掉 | 结构化类的 view 表 `cjk_texts` **全是 0**（`_view_xml.csv` 也是 0）; 唯一非 0 的是二进制噪声表 `_view_binary_assets.csv` 的 1199 行"巧合汉字" |

**关于用户搜的那个串本身**（重要, 与工具无关): `国会荣誉勋章` **在这张盘的任何地方都不存在**。

* 盘上第 116 个标题属性 = `国会最高勋章`, 对应英文原名 `Congressional Medal of Honor`（见 §5 的 EN/ZH 对照）；
* 而 `荣` 这个字**当前字符集里根本没有**: `tcslib.Charset.encode_strict('国会荣誉勋章')` → `CharsetError: charset 无此字: '荣'(U+8363)`（实测, 见 `work/builds/GR_ZH98/temp/r62/r62_probe_injectability.txt`）。
  ⇒ 这不是"搜不到", 是"这一版翻译就没这么写"; 想改成 `国会荣誉勋章` 还得先有 `荣` 的字形。

---

## 2. 实测数字（全部可复现）

盘上文件名以 `_SPECIAL_FEATURE.XML` 结尾的容器共 **10 份**（不是 6 份）= **5 种语言 × MENU/GR 两侧**:

| 容器 | 语言 | 角色 | `name=` 属性 | 其中含非 ASCII | 其中真有连续 2 汉字 | `<text>` 元素 |
|------|------|------|------------:|--------------:|-------------------:|-------------:|
| `MENU.IMG#283 EN_SPECIAL_FEATURE.XML` | EN | **zh-main（注入目标 = `tcslib.RES['SFXML']['copies'][0]`）** | 145 | **123** | **123** | 69 |
| `GR.IMG#4058 EN_SPECIAL_FEATURE.XML` | EN | lang-copy（英文原样, 未汉化） | 145 | 0 | 0 | 69 |
| `GR.IMG#4059` / `MENU.IMG#285 ES_SPECIAL_FEATURE.XML` | ES | lang-copy（西文原码） | 145 ×2 | 74 ×2 | 0 | 69 |
| `GR.IMG#4061` / `MENU.IMG#286 FR_SPECIAL_FEATURE.XML` | FR | lang-copy（西文原码） | 145 ×2 | 10 ×2 | 0 | 69 |
| `GR.IMG#4057` / `MENU.IMG#284 DE_SPECIAL_FEATURE.XML` | DE | lang-copy（西文原码） | 145 ×2 | 3 ×2 | 0 | 69 |
| `GR.IMG#4066` / `MENU.IMG#287 IT_SPECIAL_FEATURE.XML` | IT | lang-copy（西文原码） | 145 ×2 | 0 | 0 | 69 |
| **合计** | | | **1450** | **297** | **123** | 690 |

* **123 个含中文的属性名 = 93 个不同的标题串**（`幽灵行动®任务1..14`、`沙漠风暴任务1..8` 等在 `group` 与 `item` 下各写一遍 ⇒ 同一串出现 2~3 次）。
* 「含中文」判据 = **连续 ≥2 个汉字**。DE/ES/FR/IT 四份副本是**西文原码**, 用本盘中文码表解码会把 `í/ü/é` 这类字节解成**孤立**汉字（实测 `GR Misi视n 1`、`B装nder`、`Sp员cialistes 1`）⇒ 孤立汉字是解码噪声, 不是中文标题。
* 那 8 份非注入目标副本 `kind=XML`, 改动前/后都会被通用扫描过一遍, 但受 §1-② 限制, **汉字为主的串一条都进不去** `_view_xml.csv`。
* 每份副本 145 个 `name=` 之外, 还有 145 个 `pic=`（贴图/音频文件名, 纯 ASCII）与 ~95 个 `unlock=`（标志位, 纯 ASCII）—— 都不是给人看的文本, **不进本表**。

---

## 3. 改动点（文件 + 函数）

文件: `tools/text_csv/dump_containers.py`（唯一被改的代码文件, 均为**新增**逻辑, 既有代码路径逐字未动）

| 位置 | 内容 |
|------|------|
| 文件头 docstring | 新增 `sf_titles` 类别行 + 一整节 `★ round62: 为什么必须单列一张 _view_sf_titles.csv`（根因、实测数字、与 `_view_xml.csv` 的关系、注入出路） |
| `CATEGORIES` | 新增类别 `sf_titles`（`order=15`, `kinds=()`, `kind_label='SFXML 属性'`）⇒ 表名 `*_view_sf_titles.csv` |
| `SF_TITLE_COLS` / `SF_TITLE_QUOTE` / `SF_TITLE_COLS_NOTE` | 本表专用 20 列 + 每列含义（写进 meta） |
| `SFXML_NAME_RE` / `SFXML_TAG_RE` / `SFXML_ATTR_RE` / `SFXML_TITLE_TAGS` / `SFXML_TITLE_ATTR` / `NONASCII_BYTE_RE` / `LANG_PREFIX_RE` | 属性扫描用的正则与常量 |
| `SF_TITLE_NOTE` + `SF_TITLE_NOTE_TAIL` | 每行的 `note`（为什么 view-only + 想改该怎么改） |
| **`sfxml_copies_of(conts)`** | 新函数: 按**文件名**挑出全部 `*_SPECIAL_FEATURE.XML` 副本, 排序并标 `lang` / `copy_role`（`zh-main` = `tcslib.RES['SFXML']['copies'][0]`） |
| **`scan_sfxml_titles(iso, cs, conts, max_rows)`** | 新函数: 逐副本解析属性 ⇒ 行表 + 副本清单; 含两条硬自证（属性值偏移回读、含非 ASCII 属性数 == 写出行数, 不等即 `SystemExit`） |
| `main()` | 新增 `want_sf` 判定 + 扫描通道 + stdout 副本清单表 + 统计写入 `stat['sf_titles']`; 写表分支加 `elif cat == 'sf_titles'`; summary 的 SFXML 指路行改写; meta 新增 `sf_titles{…}` 块; 结尾 `[check]` 与"下一步"提示各加一行 |

**收进新表的两档属性**（严格按 blob 顺序, 不排序）:
1. `<item|group|studio>` 的 `name=` —— **全量**, 含纯 ASCII 的英文原名（英文副本也有价值: 可与中文副本按 `entry_index` 对齐）;
2. **任何**标签上**含非 ASCII 字节**的属性值 —— 兜底（本盘上这一档正好是空集: 297 个非 ASCII 属性全部落在档 ① 的 `name=` 上, 已自证相等）。

---

## 4. 新表结构

`work/builds/GR_ZH109/text_r62/GR_ZH109_view_sf_titles.csv`
UTF-8 BOM + CRLF, **1450 行**（= 145 × 10 副本）, 1 016 211 B, sha256 `9cb8fe96…ffe0577`

```
category,source_kind,container,lang,copy_role,copy_index,tag,attr,entry_index,
tag_offset,offset,len_bytes,text,text_preview,dup_count,is_title,has_cjk,cjk_run,
injectable,note
```

| 列 | 含义 |
|----|------|
| `container` | `MENU.IMG#283 EN_SPECIAL_FEATURE.XML`（与其它 view 表同一写法） |
| `lang` / `copy_role` / `copy_index` | 副本语言（EN/DE/ES/FR/IT）/ `zh-main`(=注入目标) 或 `lang-copy` / 1..10 |
| `tag` / `attr` | `item`/`group`/`studio` / 属性名（标题恒为 `name`） |
| `entry_index` | 本容器内第几个被列出的属性（1-based, blob 顺序）——**EN 与 ZH 副本结构相同, 可用它对齐英/中标题** |
| `tag_offset` / `offset` / `len_bytes` | 解压后 blob 里 `<` 的偏移 / **属性值**的偏移 / 值字节数 ⇒ 可定位、可直接给补丁工具用 |
| `text` / `text_preview` | 解码后的值 (= 引擎画出来的标题); 图标占位写成 `{{BTN:XXXX}}` |
| `dup_count` | 同一 `text` 在本副本里出现了几次 |
| `is_title` / `has_cjk` / `cjk_run` | `yes`=条目标题 / 有连续 ≥2 汉字 / 最长连续汉字数 |
| `injectable` | **恒为 `no`**（全表自述 view-only） |
| `note` | 为什么不能直接改 + 想改走哪条路（等长原位重映射 → 报告本节） |

**与旧表的关系（`_view_xml.csv` 一个字节都没改）**: 8 份非注入目标副本仍会被通用扫描过一遍, 但因为 `judge()` 只认 ASCII, 其汉字标题进不来; `*_text_*.csv` 只有 `<text>` 正文。所以:
**找「特别收录」的条目标题/组名/工作室名 → 只看 `*_view_sf_titles.csv`; 找正文 → `*_text_long/short.csv`。**
两张表的指针都写进了 `*_view_containers_summary.csv`（新增 1 行 `sf_titles` + 改写 `SFXML` 指路行的 `table`/`note`）和 `*_view_containers.meta.json`（`sf_titles{why, columns, coverage, decode_policy, relation_to_view_xml, how_to_edit, copies[], totals}`）。

---

## 5. 验收数字

复现: `python work/builds/GR_ZH98/temp/r62/r62_verify_sf_titles.py`（独立重新解析盘上字节, 不走 dump 工具的代码路径）→ 日志 `r62_verify_stdout.txt` / 记录 `r62_verify_sf_titles.json`, **失败 0 项**。

### 5.1 搜到率

| 口径 | 改动前 13 张 CSV | 新表 `*_view_sf_titles.csv` |
|------|-----------------:|---------------------------:|
| 注入目标含中文属性名（**按出现次数**） | **28 / 123** | **123 / 123 = 100 %** |
| 注入目标含中文标题（**按不同串**） | **27 / 93**（其余 66 个标题一个字都搜不到） | **93 / 93 = 100 %** |
| 全部 10 份副本的含非 ASCII 属性 | — | **297 / 297 = 100 %** |
| 每份副本的 `name=` 属性（145 × 10） | — | **1450 / 1450** |

改动前那 27/28 个命中**全部**来自 `*_text_long.csv`(27) / `_long_nowrap.csv`(5) / `_short.csv`(5) —— 即"标题恰好也在某篇 `<text>` 正文里出现过"的巧合, 与标题字段无关。

### 5.2 用户点名串的定位（新表里的**标题行**）

| 搜索串 | 结果 |
|--------|------|
| `国会荣誉勋章` | **0 行**（盘上不存在; `荣` 也不在字符集里 —— 见 §1） |
| `国会最高勋章` | `MENU.IMG#283` `<item name="…">` 第 116 个属性, `tag@32935` **值@32947 (11 B)**, `is_title=yes`, `cjk_run=6`（EN 原名 `Congressional Medal of Honor`） |
| `优异服役十字勋章` | 第 117 个属性, `tag@33323` **值@33335 (16 B)**（EN `Distinguished Service Cross`） |
| `何为幽灵` | 第 138 个属性, `tag@53410` **值@53422 (9 B)** = `何为幽灵？`（EN `Who Are the Ghosts?`; 盘上是全角问号, 搜不含问号的子串也能命中） |

EN/ZH 对照抽查（`entry_index` 对齐, 结构逐行相同: 145 = 145, tag 序列完全一致）:

| idx | EN (`GR.IMG#4058`) | ZH (`MENU.IMG#283`) |
|----:|--------------------|---------------------|
| 2 | `Soldiers` | `士兵` |
| 90 | `DS Ending` | `沙漠风暴片尾` |
| 116 | `Congressional Medal of Honor` | `国会最高勋章` |
| 117 | `Distinguished Service Cross` | `优异服役十字勋章` |
| 138 | `Who Are the Ghosts?` | `何为幽灵？` |
| 139 | `Soldier Classes` | `兵种简介` |

### 5.3 13 张表逐表对照（基线 `GR_ZH109/text/` ↔ 本轮 `GR_ZH109/text_r62/`）

基线有效性: `GR_ZH109_view_containers.meta.json` 的 `iso_sha256` == 现役 ISO 实测 sha256, 且 9 张 view 数据表的**每个 sha256 都与盘上文件一致** ⇒ 基线就是"未改动工具 + 同一张 ISO"的产物。

| 表 | 基线行 | 本轮行 | Δ | 字节相同 |
|----|-------:|-------:|--:|:--------:|
| `GR_ZH109_text_long.csv` | 58 | （本工具不产出） | – | 用户自己改过 `text_edited`, 与本轮无关 |
| `GR_ZH109_text_long_nowrap.csv` | 256 | （本工具不产出） | – | sha 与建盘时一致 |
| `GR_ZH109_text_short.csv` | 1947 | （本工具不产出） | – | sha 与建盘时一致 |
| `GR_ZH109_view_xml.csv` | 516 | 516 | 0 | **yes ✓** |
| `GR_ZH109_view_txt.csv` | 3254 | 3254 | 0 | **yes ✓** |
| `GR_ZH109_view_missions.csv` | 2008 | 2008 | 0 | **yes ✓** |
| `GR_ZH109_view_character_names.csv` | 4439 | 4439 | 0 | **yes ✓** |
| `GR_ZH109_view_other_res.csv` | 14273 | 14273 | 0 | **yes ✓** |
| `GR_ZH109_view_program_strings.csv` | 2000 | 2000 | 0 | **yes ✓** |
| `GR_ZH109_view_iso_files.csv` | 1624 | 1624 | 0 | **yes ✓** |
| `GR_ZH109_view_binary_assets.csv` | 30000 | 30000 | 0 | **yes ✓** |
| `GR_ZH109_view_pending.csv` | 2465 | 2465 | 0 | **yes ✓** |
| `GR_ZH109_view_containers_summary.csv` | 11 | **12** | **+1** | 只增一行 (`sf_titles`) + SFXML 指路行的 `table`/`note` 改写 |
| **`GR_ZH109_view_sf_titles.csv`** | — | **1450** | **新增** | 本轮唯一新文件 |

* 9 张 view 数据表**逐字节相同**（sha256 相等, 不只是行数相同）。
* `*_text_*.csv` 本轮一张都没写（本工具按设计只写 `*_view_*.csv`; 命名隔离断言 + `injectable=no` 双保险照旧: `[check] 命名隔离: 10 张 view 表没有一张叫 *_text_*.csv ✓` / `62041 行全部 = no ✓`）。
* 新表自查: `injectable` 全 `no`; `has_cjk=yes` 的行确实都有连续 ≥2 汉字; 无 PUA/控制符/零宽等不可见字符; **1450 行的 `offset`/`len_bytes` 拿回盘上都能解出同一个 `text`**（偏移回读自证）。

---

## 6. 可注入性结论（这些标题要变成"可编辑可注入"需要什么）

实测数据（`r62_probe_injectability.py`, 只在内存里试算, **不写盘**）:

```
容器 MENU.IMG#283 EN_SPECIAL_FEATURE.XML
槽 stored     49700 B      (IMG 条目的 stored; 压缩帧必须 <= 它)
解压 blob    116486 B      子流 8 条 [16384 ×7, 1798]
原压缩帧      41615 B      ⇒ 槽内余量 +8085 B
有效结束      used_end = 78248 ⇒ </SpecialFeatures> 之后有 38238 B 陈旧尾巴可吸收增长

等长(只换字)   Δ=+0  重压 1 条子流  ⇒ 帧 41623 B (余 +8077) OK
+2 字节        Δ=+2  重压 3 条子流  ⇒ 帧 41619 B (余 +8081) OK
+30 字节       Δ=+30 重压 3 条子流  ⇒ 帧 41620 B (余 +8080) OK
123 条各 +1 字 (共 +123 B):  帧 41636 B (余 +8064) OK
123 条各 +20 字 (共 +2460 B): 帧 41555 B (余 +8145) OK
```

### 6.1 结论

**可行, 而且有现成机制 —— 但"等长"和"改字数"是两条不同的路。**

1. **等长原位重映射（改字不改长度）: 今天就能做, 零风险。**
   `tools/iso_build/patch_zh51_sfxml_titles.py` 就是完整实现（round51 用它修了 49 个陈旧码位标题）:
   逐字把 `旧码位 → 新码位` 写回, 长度不变 ⇒ 只重压**含该属性的那个子流**, 帧大小几乎不动, 不动 IMG 条目表, 并带"改动只许落在属性区间内""回读复核""盘上其它条目逐字节不变"三重断言。
   本轮实测余量 **+8085 B**, 等长改写只动几十字节 ⇒ 安全边际极大。

2. **改字数（标题变长/变短）: 机制上也通, 因为 `<text>` 正文注入**每轮都在这么干**。**
   `inject_text_csv.Container.build_blob()` 的规则是"**解压总长严格不变**": 增长量由 `</SpecialFeatures>` 之后的 **38238 B 陈旧尾巴**吸收（`new = new[:len(blob)]`）, 缩短则补 `\x00`。属性值和 `<text>` 元素在同一条 blob 里 ⇒ 把标题改长**和现在把正文改长是同一件事**。
   实测: 123 个标题各加 1~20 个汉字（共 +123 ~ +2460 B）时, 重压后的帧仍在 41.5~41.6 KB, **槽位 49700 B 还剩 8 KB 左右**。

### 6.2 要真正做成"可注入", 还差什么 + 风险点

| # | 事项 | 说明 / 风险 |
|---|------|-------------|
| 1 | **没有属性级注入通道** | 现在只有 `inject_text_csv.py`（吃 `*_text_*.csv` 的 `text_edited`, 只认 `id` = `LANG:G###.I###` / `SFXML:T####`）。属性要能改, 需要: ① 给注入器加一类 `SFXML:A####`（或 `MENU#283:attr@offset`）行; 或 ② 写一个专门的 `patch_zh*_sfxml_titles_csv.py` 吃本表的 `container+offset+len_bytes`。**本报告不实现**, 只给结论 |
| 2 | **字符集 + 字形覆盖**（最容易踩） | 新标题必须**每个字都在 `charset_compiled_zh16.json` 里且盘上有字形**。实测反例: `荣` 就没有（`encode_strict` 直接报错）。注入器已有 `charset_precheck()` 做同类预检, 属性通道必须复用 |
| 3 | **槽位余量 8085 B** | 增长若让压缩帧超过 `stored = 49700 B` ⇒ 必须扩容 IMG 条目（`font_compact.Slot.repack` 明确拒绝; 有 relocation 先例 `patch_zh104_relocate.py`）。实测 +2.4 KB 文本的帧增长 ≈ 0（因为替掉的是陈旧尾巴）, 但**不可外推**: 若替换的是高压缩率区域, 最坏情况大约 1 字节文本 ≈ 1 字节压缩 ⇒ 8 KB 余量大致等价于 8 KB 新增文本, 需逐次实测 |
| 4 | **陈旧尾巴必须保住** | 38238 B 的增长空间来自 `</SpecialFeatures>` 之后的陈旧区。任何"整容器重建/清理尾部"的改动（例如未来某轮把 SFXML 重压成紧凑帧）会把这个空间吃掉 ⇒ 到时要重新测量 |
| 5 | **UI 排版宽度** | 标题画在固定栏宽里（16px/12px 两种字面, 见 `REPORT_16px.md` / `REPORT_zh82t_title_center.md`）。改长会溢出/被截断 ⇒ 改字数必须实机验版式, 不是纯文本问题 |
| 6 | **只该改注入目标那一份** | 引擎显示的标题来自 `MENU.IMG#283`（round51/79/84 的实机结论）。另外 9 份里, DE/ES/FR/IT 是**西文原码**（用中文码表改写会毁掉它们的本地化）, `GR.IMG#4058` 是**英文原样的第二份 EN 副本** —— 它是否在某条加载路径上被读, 本轮**未验证**（已知实机证据都指向 #283）。改前先确认 |
| 7 | **安全红线不变** | 本表 `injectable=no` 是**故意**的: 属性能改 ≠ 现在就能改（没有写盘通道、没有实机验证）。在这条通道落地之前, 本表只能看/校对 |

---

## 7. 已知限制

1. **本表 view-only**: `injectable` 恒 `no`, 改了不会被注入器采纳（注入器连文件都不会读: 命名 `*_view_*.csv` 与 `*_text_*.csv` 互斥, 显式喂进去也会报错退出 1）。
2. **非 EN 副本的文本是"本盘字符集硬解"的结果**: DE/ES/FR/IT 四份是西文原码, 解出来会带孤立汉字噪声（`GR Misi视n 1`）。这些行照实列出并靠 `lang` / `copy_role` / `cjk_run` 区分; 本表**不**为它们做"正确解码"（没有对应码表, 且引擎显示的不是它们）。
3. **9 个空 `name=""`**（`<studio name="Music">` 下的曲目条目, `idx 45..53`, 每份副本 9 行, 全表 90 行）: 这些条目的标题**不在** `name=` 里; 它们显示什么文字本轮未查（`pic="sf_Music_0X.rsb"`）。表里以 `len_bytes=0` 如实呈现。
4. **`_view_xml.csv` 一个字节都没动**, 所以"只看 `_view_xml.csv`"的用户依然看不到汉字标题 —— 这是**有意**的取舍（该表有下游读者, 且 `judge()` 判据改动会波及全部 12 张表）。发现路径改由 summary + meta + stdout 提示 + 本报告承担。
5. **通用扫描对中文全盲**（第 2 关判据只认 ASCII, 12 张 view 表的 `cjk_texts` 全为 0）是本轮**没有**修的既有行为: 修它会让 `.MIS`/`.ATR`/`.RES` 等表的行数暴涨, 与"既有行为不变"的验收冲突。若要让"全盘普查"也能看见中文, 建议单开一轮加 `--cjk-runs`（默认关）而不是改判据。
6. `tools/iso_build/make_build.py` L417 有一份**硬编码的表名清单**（`('xml','txt',…,'pending','containers_summary')`）, 新表 `sf_titles` 不在里面 ⇒ 只影响 `build_info.json` 里那一行展示文案, **不影响功能**（`[containers] %d 张 view 表` 走的是 meta 动态读取, 显示 10 张）。按铁律**本轮没改**; 要改就是加一个字符串, 等 Lead 决定。
7. `tools/maint/make_release_pack.py` 用 `glob('*_view_*.csv')` + `assert len(vs) >= 10` 收表 ⇒ 新表**自动**进 release, 无需改动。
8. 其它语言/地区盘（GR_EN_ORIG 等）未跑; 本通道按文件名识别副本, 预期同样适用。

---

## 8. 复现命令

```powershell
# ① 侦察: 盘上有几份 *_SPECIAL_FEATURE.XML、各有多少含中文属性
python work/builds/GR_ZH98/temp/r62/r62_recon_sf_copies.py

# ② 重跑 dump (与 make_build.py 同参: --out-dir/--prefix/--max-rows-per-category 30000)
python tools/text_csv/dump_containers.py --iso work/builds/GR_ZH109/GR_ZH109.iso `
       --out-dir work/builds/GR_ZH109/text_r62 --prefix GR_ZH109 --max-rows-per-category 30000
#    只跑新通道: 加 --only-category sf_titles

# ③ 验收 (123/123 搜到率 + 3 个点名串 + 13 张表逐表对照)
python work/builds/GR_ZH98/temp/r62/r62_verify_sf_titles.py

# ④ 可注入性试算 (只读, 只在内存里重压)
python work/builds/GR_ZH98/temp/r62/r62_probe_injectability.py

# ⑤ 口径核对: lead 的 recon 数出 28 vs 本轮 27 —— 差在"按出现次数"还是"按不同串"
python work/builds/GR_ZH98/temp/r62/r62_diff_decoders.py
```

产物:

* `work/builds/GR_ZH109/text_r62/`（本轮全量 view 表 11 张 + meta; `text/` 未动）
* `work/builds/GR_ZH98/temp/r62/`（侦察/验收/试算脚本 + `*.json` + `*_stdout.txt` 日志）
* 本报告 `docs/REPORT_sf_titles_dump.md`

## 9. 交付清单（一句话）

用户报的"标题搜不到"已定位为**两个真实漏扫**并补齐: 新增 **`GR_ZH109_view_sf_titles.csv`（1450 行, 10 份副本, 123 个中文标题 100% 可搜, 带容器+字节偏移）**; 现有 9 张 view 数据表**逐字节未变**, 只新增 1 张表、summary 增 1 行; 标题要变可注入**技术上可行**（等长原位重映射 = round51 现成做法, 槽内还余 8085 B / 陈旧尾巴 38238 B 可吸收增长）, 但需要新写属性级注入通道 + 字符集/字形预检 + 实机验版式。
