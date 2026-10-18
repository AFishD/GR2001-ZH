# round63 报告 —「特别收录」标题 (XML 属性 `name=`) 可编辑、可回写覆盖

* 分支: `round63/sf-titles-inject`(Lead 已切好; **本轮不 commit**)
* 基底盘: `work/builds/GR_ZH109/GR_ZH109.iso` sha256 `a0558f4e…b919a`(只读)
* 演示盘: `work/builds/GR_ZH110/GR_ZH110.iso` sha256 `d2a933160cd69311afc6aa30a4ccad621bf194a4ae1cb531b067c0da9669d89f`
* 改动文件(2 个): `tools/text_csv/inject_text_csv.py`(**属性级写入通道**)、
  `tools/text_csv/dump_sf_titles_csv.py`(**新增**, 产可注入标题表)
* 新增文档: 本报告
* **未动**: 任何历史 ISO / `GR_ZH109/text/` / `GR_ZH109/text_r62/` / release;
  `tools/text_csv/tcslib.py`(一个字节没改)、`dump_containers.py`、`dump_text_csv.py`、
  `tools/iso_build/*.py`(`make_build.py` / `repack_font.py` / `font_compact.py` 全未改)、
  字库图集; 未 git add / commit / 切分支
* 本轮**未跑实机**(模拟器被另一个任务占用, 按要求没碰)

---

## 1. 用户需求与结论

> **「修改构筑工具 让标题条目也能正常修改和回写覆盖 — 我发现有很多处错译」**

| 需求 | 落地 | 证据 |
|------|------|------|
| 标题能像正文一样在 CSV 里改 | 新增**可注入表** `<版本>_text_sf_titles.csv`(145 行, `id=SFXML:A####`) | 表 145 行 / 17 列; 与 round62 的 view 表**逐行一致**(tag/entry_index/offset/len/text 全等) |
| 改完能**回写覆盖**到盘上 | `inject_text_csv.py` 新增**属性级写入通道**(`--csv` 给目录会自动读入) | 4 条标题真落盘, 回读一致 ✓ |
| 支持**改字数** | 增长吃 `</SpecialFeatures>` 之后的**陈旧尾巴**(38238 B); 超出即**中止**(不截断/不静默丢字) | 本次 1 条改长(+1 B)、1 条改短(−3 B)、2 条等长; 净 −2 B, 帧 41615→41628 / 槽 49700(余 8072) |
| 有很多处**错译** | 出「待校对清单」145 行(按 tag 分组 + 英文原名 + 自动标记), 并实测**哪些错译现在改不了**(缺字) | 清单 `work/builds/GR_ZH98/temp/r63/GR_ZH110_sf_titles_checklist.csv`; §6.2 列了 10 条"明显错译但缺字"的例子 |

一句话: **标题现在和正文一样是"可编辑的表 + 可回写的通道", 只是多了一层"标题专属"的门禁
(单行、不含 `" < &`、不能清空)与一条"改字数"的吸收规则。**

---

## 2. 交付物

### 2.1 可注入表: `<版本>_text_sf_titles.csv`(17 列)

| 产物 | 行 | 字节 | sha256(前 16) |
|------|----|------|----------------|
| `work/builds/GR_ZH110/text/GR_ZH110_text_sf_titles.csv`(**标准位置**: 与其它注入表同目录) | 145 | 133 209 | `9d1c324468b7b7fa` |
| `work/builds/GR_ZH98/temp/r63/inject_titles/GR_ZH110_text_sf_titles.csv`(**本次构筑实际用的那张**, 含 4 条演示改动) | 145 | 130 286 | `f3e26c32584ec66e` |
| `work/builds/GR_ZH98/temp/r63/GR_ZH110_sf_titles_checklist.csv`(**待校对清单**) | 145 | 66 601 | `977cb1d2d8c942cb` |
| `work/builds/GR_ZH98/temp/r63/demo_blocked_rong/GR_ZH110_text_sf_titles.csv`(缺字演示表) | 145 | 130 179 | — |

列(前 6 列是注入器的定位列, 名字与其它文本表一致; 注入器要求的
`id/resource/entry_index/offset/len_bytes/text_edited` 一个不缺):

```
id, resource, container, entry_index, offset, len_bytes, max_bytes, kind, tag, attr,
copy_role, lang, dup_count, text_en, text_zh, text_edited, note
```

* `id = SFXML:A####`(A = attribute)与正文表的 `SFXML:T####` **永不会撞 id** ⇒
  标题表可以和 `_text_long/_short.csv` **同时**给 `--csv`, 多表按 id 合并那一套完全复用。
* `entry_index = A####` = 本容器内第几个 `name=` 属性(1-based, blob 顺序)= **注入时的权威定位**。
* `offset`/`len_bytes` = 属性**值**在解压 blob 里的偏移/长度 ⇒ 与源盘**对表**用(改字数后偏移会漂移)。
* `tag` = `item`/`group`/`studio` ⇒ 复核"这个序号上确实是它"。
* `text_en` = 同盘英文原样副本(`GR.IMG#4058`)同序号的英文原名(tag 序列 145 行**逐行一致**才对齐);
  **只读参考列**, 注入器读表后立刻整列丢掉(`IGNORED_COLS`, 实测 136 个非空单元格被丢弃)。
* `max_bytes` = `len_bytes` + 陈旧尾巴(38238)= 单条能长到多少的**宽松提示**; 真正的硬门禁是"内容不得超出 blob 总长 / 重压后帧不得超出槽位"。
* 只列**注入目标** `MENU.IMG#283`(= `tcslib.RES['SFXML']['copies'][0]`)的 **145 个** `name=` 属性,
  含纯 ASCII 的(便于与英文对照); 另外 9 份副本只出现在 view 表里。

### 2.2 待校对清单(给用户逐条改错译用)

`work/builds/GR_ZH98/temp/r63/GR_ZH110_sf_titles_checklist.csv`(145 行, UTF-8 BOM + CRLF):

```
grp, order, id, entry_index, tag, offset, len_bytes, text_zh, text_en, text_edited,
dup_count, flag, note
```

* 按 `tag` 分组 **studio(10) → group(41) → item(94)**, 组内按盘上顺序; `text_en` 是英文原名。
* `flag` 自动标记: **结构名 ×10**(studio 档, 见 §6.3)、**型号/代号 ×3**(`M16/M203`、`OICW`、`XIII`)、
  **偏长 ×6**(超过 14 字, 栏宽有限)、**空标题 ×9**、**无英文对照 ×9**。
* 改完把 `text_edited` 填回 `*_text_sf_titles.csv` 的同一列(或直接把清单改完照抄), 然后按 §7 注入。

### 2.3 新增 dump 工具: `tools/text_csv/dump_sf_titles_csv.py`

```
python tools/text_csv/dump_sf_titles_csv.py --iso <盘> --out <基准>/<版本>_text.csv
       [--checklist <清单.csv>] [--stats] [--json <报告.json>]
```

* 命名落在注入器的扫描空间里(`*_text_*.csv`)⇒ **给目录就会被自动读入**, 不用改命令行;
* 副本识别/属性正则与 round62 的 `_view_sf_titles.csv` **同一口径**(逐行一致已自证), 但**只读 10 个容器**(不跑 4713 容器普查, 几秒完成);
* 硬自证(不通过就**拒绝写表**): ① 每个属性的 `offset` 回读命中; ② 含非 ASCII 的属性数与 `name=` 数相等(不漏);
  ③ `text_zh` 用注入口径能**逐字节还原**盘上原字节(145/145); ④ 文本列无 PUA/不可见字符;
* ★ 铁律: **只读 ISO**, 只写 CSV/JSON。

### 2.4 注入器新增的属性级写入通道(§3)

`tools/text_csv/inject_text_csv.py`: 正文行的老路径**行为逐字保留**(只有标题表时正文 0 改动;
只有正文表时属性 0 改动; 老的报错文案一字未改), 属性行走**独立的一条通道**
(`is_attr_row()` 按 `id` 分流 → `plan_attr_edits()` → `Container.edits` → 同一套重压/写盘/复检)。

对老路径做的**唯一**改动是两处非行为性的:
① 把正文行原来那段 `try/except (WrapPlacementError/WrapMarkError/BtnMarkError/CharsetError)`
提成 `encode_cell_or_die()`(属性行要复用同一套人话报错, **文案一字未改**);
② `Container.build_blob()` 里加了"反向重建"硬断言(§3.3 门禁①)——它对正文行同样成立,
只会让**本来就不该发生**的情况变成显式报错, 不改变任何正常路径的产物。

---

## 3. 写入通道设计

### 3.1 定位口径(为什么不能只看 offset)

标题**改了字数**就会让**后面所有属性**的偏移整体平移。实测: 本次 4 条改动让 `MENU.IMG#283`
里 **78 个后续属性**的 `offset` 漂移(第一处 −3 B、后面 −2 B ⇒ 新 dump 出来就是新偏移)。
所以:

| 步骤 | 规则 |
|------|------|
| ① 定位 | **按 `entry_index`(A####)= 第 N 个 `name=` 属性**——唯一权威 |
| ② 复核 | `tag` 列必须与盘上第 N 个属性的标签一致(不一致 ⇒ 拒绝: 表来自别的盘/结构变了) |
| ③ 幂等 | 盘上现值 **== `text_edited`** ⇒ 已经写过了 ⇒ **跳过**(同一份表再跑 = 0 改动) |
| ④ 写入 | 盘上现值 **== `text_zh`**(= dump 时看到的旧文)⇒ 位置可信 ⇒ 写入; 若 `offset/len_bytes` 与表不符(前面的改动让偏移漂移) ⇒ 只**告警**并列出漂移行 |
| ⑤ 拒绝 | 盘上现值**既不是** `text_zh` **也不是** `text_edited` ⇒ **拒绝写盘**(表与源盘不同步, 硬写会盖掉别人/别轮的改动); 这一类 `--force` 可忽略 |
| ⑥ 重编码 | `text_zh` 为空(`font_compact` 的"强制重编码副本"会清空它)⇒ 按新字符集重编写入(与正文行同口径), 位置仍由 ①② 复核 |

* ④/⑤ 是**内容判据**, 与 "offset 有没有漂移" 无关 —— 表在说哪条属性由 ① ② 决定,
  "这条现在是不是还是我看到的那条"由 ④/⑤ 决定。

### 3.2 「改长」怎么吸收 / 装不下怎么办

* 解压 blob **总长严格不变**(116486 B)。原因: IMG 条目表的 `real` 字段 = 总解压长, 而
  **条目表一个字节都不许动**(验收⑦)。实测该字段本来就陈旧: 英文原盘
  `MENU.IMG#283` = `real 116430 / blob 116430`(相等), 而中文盘从 GR_ZH98 起就是
  `real 116430 / blob 116486`(**多 56 B**), 盘能正常跑 ⇒ 引擎并不把它当硬上界;
  本工具的策略是**绝不把差距变得更大**: 只让**内容**长进 `</SpecialFeatures>` 之后的陈旧尾巴,
  总长不动。
* 内容变长 Δ>0: 从陈旧尾巴里吃 Δ(现役盘 **38238 B** 可用); `Δ > 尾巴` ⇒ **中止**
  (退出码 1, 报"需要多少 / 只有多少", **不截断、不静默丢字**)。
* 内容变短 Δ<0: 尾部补 `\x00`(补的这段全在 `used_end` 之后)。
* 重压后 **帧 > 槽位**(`stored`)⇒ **中止**(退出码 1), 提示精简或 `--only` 分小批。
* 实测数字(本次 4 条改动, 净 −2 B):

  | 量 | 基底 GR_ZH109 | 产物 GR_ZH110 |
  |----|--------------|---------------|
  | 压缩帧 / 槽 | 41615 / 49700(余 8085) | **41628 / 49700(余 8072)** |
  | 解压 blob | 116486 | **116486(不变)** |
  | `</SpecialFeatures>` 结束 | 78248(尾巴 38238) | 78246(尾巴 38240) |
  | 重压子流 | — | 6/8(后 2 条完全落在 CRLF 陈旧尾巴里 ⇒ 字节未变 ⇒ 原帧照搬) |

### 3.3 五道硬门禁(任一不过就**不写盘**)

| # | 门禁 | 实现 / 本次结果 |
|---|------|------------------|
| ① | **除被编辑的区间外, blob 逐字节不变** | **反向重建**: 把新 blob 里被编辑的区间换回**盘上原字节**, 结果必须**逐字节等于原 blob**。它对"改长/改短"同样成立(改长时后续字节整体平移, 单纯逐字节 diff 看不出来); `Δ=0` 时还额外做一次严格逐字节 diff(改动必须全部落在编辑区间内)。**两类通道(正文+属性)都过这一关** |
| ② | **字符集 + 字形预检** | 复用现成的 `charset_precheck`(**写盘前**, 覆盖属性行)。缺字 ⇒ **退出码 3**, 指名道姓(本次实测见 §5.1) |
| ③ | **槽位装不下就拒绝** | 帧长 > `stored` ⇒ 退出码 1 |
| ④ | **写盘后重新 load 回读** | 从产物盘重新解压: 每个被编辑的属性解出来必须 == `text_edited`(再按字符集解一次比对); **其余 141 个属性逐字节不变**; **69 个 `<text>` 逐字节不变**; `<text>/<studio>/<item>/<group>/</SpecialFeatures>` **结构计数不变**; 条目表 `off/stored/real` 不变; 解压总长不变 |
| ⑤ | **幂等** | 同一份表对**已经写过的盘**再跑: 4 条判"已写过"跳过 ⇒ 0 改动, 产物 sha256 **完全相同** |

### 3.4 只改注入目标那一份

* 属性通道**只写** `tcslib.RES['SFXML']['copies'][0]`(现役盘 = `MENU.IMG#283`),
  代码里**硬断言** `len(copies) == 1`(将来若加副本, 直接拒绝而不是悄悄多写);
* 另外 9 份副本(DE/ES/FR/IT 西文原码 + `GR.IMG#4058` 英文原样)**根本不在写入列表里**,
  实测它们**每个槽位逐字节相同**(见 §5.5)。

---

## 4. 演示改动与理由(4 条真落盘 + 1 条被拦)

| id | 序号 | 原文(盘上) | 改后 | ΔB | 英文原名 | 为什么是错译 |
|----|------|-----------|------|----|---------|--------------|
| `SFXML:A0056` | 56 | `定向炸药 (M2)` | **`爆破装药 (M2)`** | 0 | `Demo Charge (M2 Demolitions Charge)` | `Demolitions Charge` = **爆破装药**(爆破作业用的装药); "定向炸药"字面是"有方向性的炸药"(成型/定向爆破装药), 与原文不是一回事 |
| `SFXML:A0065` | 65 | `M4 短突击步枪` | **`M4 卡宾枪`** | **−3** | `M4` | M4 的制式分类就是 **卡宾枪(carbine)**; "短突击步枪"是另一类武器(同一张表里 `9A-91` 才是那个分类)。**这是"改短"用例** |
| `SFXML:A0080` | 80 | `FN-FAL 步枪 (短型)` | **`FN-FAL 步枪 (伞兵型)`** | **+1** | `FN-FAL Para` | `Para` = **伞兵型**(折叠枪托的伞兵型号), 不是"短型"; ★ **同一张盘同一条目的正文**(`SFXML:T0035`)自己写着「**伞兵型**稍短且更轻便」⇒ 标题与正文自相矛盾, 改后一致。**这是"改长"用例** |
| `SFXML:A0129` | 129 | `拉默雷斯` | **`拉米雷斯`** | 0 | `H. Ramirez` | 音译错误: `Ra-mi-rez` ⇒ "拉**米**雷斯"(通用译名); "默"(mò)与 mi 读音不符 |
| `SFXML:A0116` | 116 | `国会最高勋章` | ~~`国会荣誉勋章`~~ | — | `Congressional Medal of Honor` | **故意留着做"缺字必须被拦下"的证据**: 「荣」不在字符集里 ⇒ 预检 **exit 3**(§5.1) |

* 4 条改动全部**只用盘上现有字**(每条都先逐字查过字符集 + 字形);
* 净 −2 B: 1 长 / 1 短 / 2 等长 —— **"改字数"三个方向都在真盘上跑过**;
* 宽度提示: 4 条里只有 `FN-FAL 步枪 (伞兵型)` 比原来**宽 1 个汉字**(估 +16 px), 注入器已按
  14 字阈值**告警**; 这一条最需要实机确认(见 §6.1)。

---

## 5. 实测验收数字

### 5.1 「缺字被拦下」—— 实测证据(用户点名的那条错译)

```
$ python tools/text_csv/inject_text_csv.py \
      --csv work/builds/GR_ZH98/temp/r63/demo_blocked_rong/GR_ZH110_text_sf_titles.csv \
      --src work/builds/GR_ZH109/GR_ZH109.iso --check-only
# 待检查(会被写入) 5 条; 逐字符检查完成
[!!] 发现 1 个「有问题的字」(共影响 1 处文本):
  ── 字符集里没有 U+8363  「荣」
     原因: 字符集 (charset JSON) 里没有这个字
     出现在: SFXML:A0116 (MENU.IMG#283 EN_SPECIAL_FEATURE.XML) 第 3 个字符 [A0116]
     怎么办: 该字不在本盘字符集里。要么改写文案换成常用字, 要么先扩字符集+字库再注入。
[拒绝写盘] 预检不通过: 1 个字有问题 …
[check-only] 只预检, 未写盘。
退出码 = 3      ← 一个字都没写盘
```

同一张表里**另外 4 条合法改动照常通过**, 只有含「荣」的那条被摘出来 ⇒ 拦的是"字", 不是"整份表"。

### 5.1b 其它门禁的**实测**(逐条造"坏表"跑出来的, 不是设计意图)

| 用例 | 坏在哪 | 退出码 | 报出来的话(摘) |
|------|--------|--------|------------------|
| `bad_format` | 4 行分别是: 标题里有**换行** / 有 **`"`** / 写了 **`[[empty]]`** / 写了 **`{WRAP}`** | **1** | `单元格里有换行 —— 标题是**单行** XML 属性值` / `标题里有会破坏 XML 属性语法的字符: " …(第 2 个字节 = 0x22)` / `标题不能清空 ([[empty]]): name="" 会把这条条目标题整条删掉` / `单元格里有 {WRAP} —— 那是长段正文的人工断点, 标题用不上`; **--force 也 exit 1** |
| `bad_tag` | 把 `A0100` 的 `tag` 改成 `studio`(盘上是 `item`) | **1** | `CSV 的 tag='studio' 与源盘第 A0100 个 name 属性的标签 'item' 不符 —— 表与源盘不同步`;加 `--force` ⇒ **0** |
| `bad_stale` | `A0120` 的 `text_zh` 改成盘上没有的文本(现值既非 `text_zh` 也非 `text_edited`) | **1** | `表与源盘不同步: 盘上第 A0120 个属性 (item) 现在是 '战伤勋章', 而表里 text_zh 写的是 '何为幽灵？' …—— 硬写会盖掉别处的改动`;加 `--force` ⇒ **0** |
| `bad_grow` | 一条标题改成 40000 个汉字(净 +79994 B > 尾巴 38238 B) | **1** | `装不下: 这次改动让内容变长 +79994 B, 而 </SpecialFeatures> 之后的陈旧尾巴只有 38238 B (超 41756 B) …本工具**不会**截断、也不会静默丢字`;★ **没有写出任何文件**(实测 `Test-Path` = False) |

四种坏表都在 `work/builds/GR_ZH98/temp/r63/bad_*/`(造表脚本 `make_bad_tables_r63.py`),
日志 `log_gate_*.txt`。★ 注意 `bad_format` 那类**写法错**即使加 `--force` 也是退出码 1。

### 5.2 `--check-only` 退出码

| 输入 | 退出码 | 说明 |
|------|-------|------|
| 演示表(4 条合法改动) | **0** | 预检通过 + 属性行写法/定位/tag 全通过; 并预览"要写 4 条, 改长 1 / 改短 1 / 等长 2, 净 −2 B" |
| 缺字表(4 条 + `荣`) | **3** | 见 §5.1 |
| `work/builds/GR_ZH110/text`(**整个目录**, 4 张表 2406 行) | **0** | 多表合并 2406 行, 标题通道 145 行候选、要写 0(已被本轮写过) |

`--check-only` 还会跑属性行的**写法/定位检查**(单行、`" < &`、`[[empty]]`、tag 复核、与源盘对表),
因此"改错格式"在干跑阶段就能发现。用法:

```
python tools/text_csv/inject_text_csv.py --csv <表或目录> --src <盘> --check-only
```

### 5.3 注入与回读(`make_build.py GR_ZH110 --from GR_ZH109 --inject-csv <标题表>`)

```
[inject 1/1] … --csv …/r63/inject_titles --src GR_ZH110.iso --dst GR_ZH110.inject1.iso.tmp
===== 属性级通道: 「特别收录」标题 (SFXML 的 name= 属性) =====
# 表里属性行 145 行; 候选 145; 要写 4 (改长 1 / 改短 1 / 等长 2, 净 -2 B); 未改跳过 141; 已写过(幂等)跳过 0
== SFXML (EN_SPECIAL_FEATURE.XML) ==
   编辑 4 条; 解压 116486 → 116486 B (-2, 尾部陈旧区 38238 B)
   压缩帧 41615 → 41628 B / 槽 49700 (余 8072); 重压子流 6/8
[write] EN_SPECIAL_FEATURE.XML @ISO 0x623A0800 帧 41628 B + 零填至槽 49700 B; 回读一致 ✓
[diff] 全盘差异 37563 B / 3 个写入窗口; 窗口外差异: 无 ✓
[verify] EN_SPECIAL_FEATURE.XML 条目 69: 改动 0 / 逐字节不变 69, 结构计数
         {'<text>': 69, '</text>': 69, '<studio': 10, '<item': 94, '<group': 41,
          '</SpecialFeatures>': 1} 不变
[verify] EN_SPECIAL_FEATURE.XML 属性 145: 改动 4 / 逐字节不变 141
[hash] dst d2a933160cd69311afc6aa30a4ccad621bf194a4ae1cb531b067c0da9669d89f
```

**独立复验**(`work/builds/GR_ZH98/temp/r63/verify_r63.py`, 不走注入器的复检代码, 直接重新解析字节):

| 项 | 结果 |
|----|------|
| ① 被改的标题回读 | **4/4 == 表里 `text_edited`**;`A0056 +0 B`、`A0065 −3 B`、`A0080 +1 B`、`A0129 +0 B` |
| ② 未编辑的属性 | **141/145 逐字节不变**(改动 4) |
| ② `<text>` 元素 | **69/69 逐字节不变** |
| ③ 另外 9 份副本 | **9/9 帧逐字节相同 + blob 逐字节相同 + 条目表不变**(差异字节 0) |
| ④ 条目表 | `MENU.IMG#283` 的 `off/stored/real` **不变**; 解压总长 116486 **不变** |
| ⑤ 反向重建 | 把 4 个新值换回原字节后, 与基底 blob **逐字节相同**(差异只有末尾 2 B `\x00` 补零, 起点 116486 ≥ `used_end` 78248, 全在陈旧尾巴里) |
| ⑥ 全盘差异归属 | 总差异 **37563 B**, 全部落在 `MENU.IMG#283` 槽 `0x623A0800..0x623ACA24`; **槽外 0 B** |
| 结论 | **失败 0 项** |

`work/builds/GR_ZH98/temp/r57/diff_attr_r57.py`(按**真实容器边界**做窗口归属):

```
   MENU.IMG#283 EN_SPECIAL_FEATURE.XML   37563 B / 2 段   [0x623A0800..0x623AAA9A]
  字库像素容器内: 0 B      FONT.RES 槽内: 0 B      允许区间之外: 0 B  ✓
  ELF (真实 37.5MB): 0 B / 0 段 ✓      PVD (LBA16..17): 0 B ✓
  两个 IMG 条目表: 0 B ✓               GR.IMG#551..#565: 0 B ✓
```

### 5.4 ELF / 字库

| 检查 | 命令 | 结果 |
|------|------|------|
| ELF 补丁清单 | `python tools/iso_build/audit_inventory.py work/builds/GR_ZH110/GR_ZH110.iso` | 解析 45 条: **在役 44 / 缺失(仍为 EN 词) 0 / 其它 1**(那条是既有的字距 hook, 与本轮无关) |
| 字库 dump | 构筑自动跑 `dump_font`(产物 `work/builds/GR_ZH110/font/`) | 记录 544(有墨 502)/ 字符 1384: **有字形 1382 / 缺字形 0**; 采样窗 1719 个: 错误 0 / 警告 2 / **截断 0**; 字库步骤 **0 改动** |

### 5.5 幂等(`⑧`)

```
$ python tools/text_csv/inject_text_csv.py --csv <同一张标题表> \
      --src work/builds/GR_ZH110/GR_ZH110.iso --dst <新盘>
# 表里属性行 145 行; 候选 145; 要写 0; 未改跳过 141; **已写过(幂等)跳过 4**
[verify] EN_SPECIAL_FEATURE.XML 属性 145: 改动 0 / 逐字节不变 145
[diff] 全盘差异 0 B / 3 个写入窗口; 窗口外差异: 无 ✓
[hash] src d2a933160cd69311afc6aa30a4ccad621bf194a4ae1cb531b067c0da9669d89f
[hash] dst d2a933160cd69311afc6aa30a4ccad621bf194a4ae1cb531b067c0da9669d89f
[hash] 逐字节相同 (无改动)
退出码 = 0
```

(上面这次是用**最终版**注入器跑的; 构筑那次是改动前的版本 —— 两次的判据都通过,
差别只是最终版多了一道"现值必须等于 `text_zh`"的前置检查, 对本次 4 条本来就成立。)

### 5.6 现有表 / 上一轮新表**没有被破坏**

工具侧: `dump_containers.py` 与 `dump_text_csv.py` **一个字节没改**(`git diff --stat` 只有
`inject_text_csv.py` 与新文件) ⇒ 它们产出的表结构/口径不可能变。
产物侧(逐表 sha256 对照, `work/builds/GR_ZH98/temp/r63/cmp_tables_r63.py`):

| 表 | GR_ZH109 基线 → GR_ZH110 | 判定 |
|----|--------------------------|------|
| `view_xml / view_txt / view_missions / view_character_names / view_other_res / view_program_strings / view_iso_files / view_binary_assets / view_pending` | 9 张**逐字节相同** | ✓ |
| `text_long_nowrap.csv` | 逐字节相同(256 行) | ✓ |
| `text_long.csv` / `text_short.csv` | 行数不变(58 / 1947); 不同的行 58 / 11 条, 差在 `max_bytes`(SFXML 行的"单条扩容预算"随容器变化)、`offset`(前面标题改了字数 ⇒ 后续平移)、`note`/`text_edited`(见下) | 解释见下, 非缺陷 |
| `view_containers_summary.csv` | 11 → 12 行(round62 新增的 `sf_titles` 那一行 + SFXML 指路行改写) | ✓ 与 round62 报告一致 |
| `view_sf_titles.csv`(round62 新表) | round62 基线 1450 行 → 本轮 1450 行, **列相同**; **文本变了 4 条**(就是本次注入的 4 条) + 78 条只有 `offset` 漂移; 其余 9 份副本 **0 行变化** | ✓ |

* `text_long.csv` 的 `text_edited`/`note` 差异**不是工具变化**: 上一版那份表的 `text_edited`
  里带着人工写的 `{WRAP}` 断点写法(构筑时用 `--carry-edited <上一版 text 目录>` 搬过来的),
  而本次演示只注入了**标题表**(carry 源里没有 `T####` 行)⇒ 新表按 dump 默认口径写出
  `text_edited = text_zh`(**盘上字节完全一样**, 两种写法都编码成同一个 `{br}`)。
  正式流程给 `--inject-csv <上一版 text 目录>` 时, `{WRAP}` 写法照旧会被搬过来。
* ★ 唯一被**构筑器**改写的非产物文件: `tools/font_pipeline/data/charset_compiled_zh16.json`
  末尾 3 行 stamp(`iso_sha256`/`iso_version`/`stamped`, GR_ZH109 → GR_ZH110)。
  **映射内容 0 改动**(`git diff` 只有这 3 行), 这是 `font_compact` 每次构筑的标准行为
  (`font_compact.py:2308`), 与本轮改动无关。

### 5.7 构筑器能原样读入标题表(下一轮不用改命令行)

`work/builds/GR_ZH98/temp/r63/check_makebuild_reads_titles_r63.py` 直接调构筑器的
`read_text_tables()`:4 张表(`long` / `long_nowrap` / **`sf_titles`** / `short`)合并 **2406 行,
冲突 0 处**, 其中 **145 条标题行**(`SFXML:A####`)完整读入 ⇒ 下一轮的版本快照会自动带上标题
(本轮快照生成时 `text/` 里还没有标题表, 所以本轮 TXT 快照里标题 0 行 —— 属时序, 不是缺陷)。

---

## 6. 已知限制(必读)

### 6.1 ★★★ 标题栏宽度 / 居中版式**必须实机验**(本轮没跑实机)

* 标题画在一个**固定的标题条**里(实机形态是 `◀ 标题 ▶`, 见 `docs/REPORT_zh82w_text_space.md` §5.2);
  历史报告已证标题条**会截断**最后一个字(`docs/REPORT_single_cell_verify.md` §5.1 的 8×14 px 差异区),
  垂直居中另有专门结论(`docs/REPORT_zh82t_title_center.md`: 标题条 y20.0..46.5, 16px 字格垂直居中)。
* 本轮 4 条改动里 3 条**不会变宽**(1 条变窄 3 B, 2 条等长); 只有
  `FN-FAL 步枪 (短型)` → `FN-FAL 步枪 (伞兵型)` **宽 1 个汉字**(估 +16 px, 该条本来就有 14 个字)。
  注入器对 >14 字的标题**只告警不阻断** —— 请把这一条**优先**上实机看:
  特别收录 → 武器 → 用标题栏 `◀ ▶` 翻到 FN-FAL 那页, 确认标题完整、不被截断、左右箭头不挤。
* 判据(实机或 GS 截图): 标题**最后一个字完整**、没有半个字/空白格、`◀ ▶` 未被顶掉。

### 6.2 缺字: 当前字符集只有 1285 字 ⇒ **很多"明显错译"现在改不了**

字符集 = 110 单字节码 + 1175 对偶码 = **1285 字**; 字库还空着 **329 个对偶位**
(dump_font 实测), 所以"先扩字库再改"是可行的, 但**不能靠注入器绕过**。

本轮实测**被预检拦下**的改动(全部是真实错译, 全部只差 1~2 个字):

| 标题 | 应改成 | 缺的字 |
|------|--------|--------|
| `国会最高勋章` | 国会**荣**誉勋章 | 荣 |
| `战功星章` | **铜**星勋章 | 铜 |
| `战伤勋章` | **紫**心勋章 | 紫 |
| `步兵战斗章 (CIB)` | 步兵战斗**徽**章 | 徽 |
| `伊布拉伊姆` | 易**卜拉欣** | 卜、欣 |
| `高登` | **戈**登 | 戈 |
| `亚各布斯` | **雅**各布斯 | 雅 |
| `科汉` | 科**恩** | 恩 |
| `汉克尔` | **亨**克尔 | 亨 |
| `极限危机`(The Sum of All Fears) | **恐惧**的总和 | 恐、惧 |

⇒ 建议的下一步(不在本轮范围): 挑一批这样的错译, 用 `font_compact`/`patch_zh104_relocate`
那套扩字库流程把字补进去(**329 个空位**够用), 再回来改标题 —— 通道本身已经就绪。

### 6.3 `studio` 档的 10 个名字**建议不要汉化**

`ConceptSketches` / `Background` / `Music` / `Weapon` / `Movies` / `GameTrailer` / `Awards` /
`SpecialistProfile` / `BackStory` / `Interview`:

* 它们在 **EN/DE/ES/FR/IT 五份副本里逐字节相同**(= 五语都没译), 而同一批数据里**真正给人看的**
  `item`/`group` 名字五份各不相同 ⇒ 它们更像菜单**用来找条目**的结构键, 不是本地化文案;
* 汉化它们既可能没有显示效果, 又可能让菜单找不到条目 ⇒ **本轮没动**, 表里每行 note 都写了
  "★★ 这是 studio 档的结构名 …建议不要改"; 清单里 `flag` 也标了 `★结构名`。
* 若你要试译: 请单独 `--only SFXML:A0001` 一条, **实机确认菜单能进得去**再说。

### 6.4 标题表要**手动 dump 一次**(`make_build.py` 未改)

按铁律本轮**没改** `make_build.py`。它在构筑时只会调 `dump_text_csv.py`(正文)与
`dump_containers.py`(view 表), **不会**产标题表 ⇒ 每版新盘建好后手动跑一次
`dump_sf_titles_csv.py`(一条命令, 几秒)。**回写侧不需要任何改动**: `--inject-csv <版本>`
或 `<版本>/text` 会自动把标题表读进去(已实测 §5.7)。
若 Lead 同意, 下一轮可以在 `make_build.make_container_view()` 旁边加一行调用把它自动化
(改动量 ≈ 5 行, 需要先汇报)。

### 6.5 其它

1. **只写一份**: 属性通道只改 `MENU.IMG#283`; `GR.IMG#4058`(英文原样第二份)与 4 份西文副本
   一律不动。若将来证明确有加载路径读 `GR.IMG#4058`, 需要另开一轮讨论(本轮无实机证据)。
2. **标题必须单行**: 换行 / `{br}` / `{p}` / `{WRAP}` / `"` / `<` / `&` / `[[empty]]` **一律拒绝**
   (--force 也不能绕过); 因为标题是 XML **属性值**, 这些字符会破坏解析或把标题截断。
3. **`max_bytes` 只是提示**: 单条标题的"扩容预算"是全局共享的(整条陈旧尾巴);
   真正判据是 §3.2 的两条(内容不超 blob 总长 / 帧不超槽位)。
4. **`font_compact` 场景已兼容但未实跑**: 若某轮字库重排真的发生(本轮 0 改动), 构筑器会把注入表
   换成"清空 `text_zh`"的重编码副本; 属性通道对此已有明确分支(§3.1 第⑥条), 但**没有真跑过**
   (要等下一轮真的扩字库时才能验证)。
5. **9 个空的 `name=""`**(`studio="Music"` 下的曲目条目): 表里以 `len_bytes=0` 如实呈现;
   想给它们起名字请**实机确认**那一栏画的是什么(round62 报告 §7.3 已记为未解)。
6. **未做**: 实机截图验证(模拟器被占用)、扩字库、`make_build` 集成、其它语言盘。

---

## 7. 用法示例(用户怎么改 CSV + 怎么注入)

```powershell
# ── ① 建好这一版后, 产一次「可注入标题表」(与正文表同目录) ─────────────
python tools/text_csv/dump_sf_titles_csv.py --iso work/builds/GR_ZH110/GR_ZH110.iso `
       --out work/builds/GR_ZH110/text/GR_ZH110_text.csv
#   → work/builds/GR_ZH110/text/GR_ZH110_text_sf_titles.csv (145 行)
#   想顺手拿一份"按 studio/group/item 分组 + 英文原名"的校对清单, 再加:
#       --checklist work/builds/GR_ZH98/temp/r63/GR_ZH110_sf_titles_checklist.csv

# ── ② 用 Excel 打开那张表, 只改 text_edited 一列 ─────────────────────
#   · 对照右边的 text_en(英文原名)看是不是错译;
#   · 留空 / 不改 = 这条不动; 想改就写新标题(**不能有换行**);
#   · ⚠ 标题栏宽度固定 ⇒ 别写太长(超过 14 字注入器会告警);
#   · ⚠ studio 档(ConceptSketches/Music/…)是结构名, 建议不要译(见 §6.3);
#   · 缺字会被拦下并告诉你缺哪个字(见 §5.1)。

# ── ③ 干跑预检(不写盘; 缺字 -> 退出码 3, 写法错 -> 1, 通过 -> 0) ────
python tools/text_csv/inject_text_csv.py --csv work/builds/GR_ZH110/text `
       --src work/builds/GR_ZH110/GR_ZH110.iso --check-only
#   只想试一条: 加 --only SFXML:A0116

# ── ④ 真构筑下一版(标题和正文一起注入) ────────────────────────────
python tools/iso_build/make_build.py GR_ZH111 --from work/builds/GR_ZH110 `
       --inject-csv work/builds/GR_ZH110/text
#   (make_build 会把该目录下所有 *_text_*.csv 一起读入 —— 标题表已经在这个命名空间里,
#    所以"以后多了新的 kind 也不会漏"这条老规矩对标题同样成立)

# ── ⑤ 只想单独注入标题表(不碰正文) ────────────────────────────────
python tools/text_csv/inject_text_csv.py `
       --csv work/builds/GR_ZH110/text/GR_ZH110_text_sf_titles.csv `
       --src work/builds/GR_ZH110/GR_ZH110.iso --dst work/builds/GR_ZH110/GR_ZH110.titles.iso
```

---

## 8. 复现命令(本轮全部产物与日志)

```powershell
R = work/builds/GR_ZH98/temp/r63      # 本轮临时目录

# 侦察: 容器结构 / real 字段 / 候选改动逐字体检
python $R/probe_r63.py            # MENU#283: 槽 49700 / blob 116486 / 尾巴 38238 / 145 属性
python $R/probe_r63b.py           # 10 份副本的 real vs blob
python $R/probe_r63c.py           # EN 原盘 vs GR_ZH98 vs GR_ZH109: real 一直 116430 / blob 116486
python $R/probe_chars_r63.py      # 候选错译逐字: 字符集 + 字形
python $R/probe_words_r63.py      # 词级: 哪些改法现在能用

# 造表 + 演示改动
python tools/text_csv/dump_sf_titles_csv.py --iso work/builds/GR_ZH109/GR_ZH109.iso `
       --out $R/inject_titles/GR_ZH109_text.csv
python $R/make_demo_tables_r63.py # 4 条真改动 + 1 条缺字演示表

# 预检 / 干跑 / 真注入
python tools/text_csv/inject_text_csv.py --csv $R/demo_blocked_rong --src work/builds/GR_ZH109/GR_ZH109.iso --check-only   # exit 3
python tools/text_csv/inject_text_csv.py --csv $R/inject_titles --src work/builds/GR_ZH109/GR_ZH109.iso --dst <tmp> --dry-run
python tools/iso_build/make_build.py GR_ZH110 --from work/builds/GR_ZH109/GR_ZH109.iso `
       --inject-csv $R/inject_titles --no-textdump

# 验收
python $R/verify_r63.py                                       # 独立复验 (§5.3)
python work/builds/GR_ZH98/temp/r57/diff_attr_r57.py `
       work/builds/GR_ZH109/GR_ZH109.iso work/builds/GR_ZH110/GR_ZH110.iso `
       --json $R/diff_attr_r63.json                            # 差异归属 (§5.3)
python tools/iso_build/audit_inventory.py work/builds/GR_ZH110/GR_ZH110.iso   # 缺失 0
python $R/cmp_tables_r63.py                                   # 现有表对照 (§5.6)
python $R/check_makebuild_reads_titles_r63.py                 # 构筑器读标题表 (§5.7)
python $R/show_inject_report_r63.py                           # 注入报告里的属性通道一节

# 幂等 (第二遍写出的盘应与第一遍 sha256 相同)
python tools/text_csv/inject_text_csv.py --csv $R/inject_titles `
       --src work/builds/GR_ZH110/GR_ZH110.iso --dst <tmp2>   # 0 改动, sha 不变
```

日志(全在 `work/builds/GR_ZH98/temp/r63/`): `log_checkonly_blocked.txt`、
`log_checkonly_ok.txt`、`log_checkonly_GR_ZH110_dir.txt`、`log_dryrun.txt`、
`log_make_build_GR_ZH110.txt`、`log_verify_r63.txt`、`log_diff_attr_r63.txt`、
`log_audit_inventory.txt`、`log_idem.txt`、`log_cmp_tables.txt`、`log_only_dryrun.txt`、
`log_gate_bad_format.txt`、`log_gate_bad_tag.txt`、`log_gate_bad_stale.txt`、
`log_gate_bad_grow.txt`、`log_dump_titles_GR_ZH110.txt`、`log_inject_report.txt`、
`log_makebuild_reads_titles.txt`、
`verify_r63.json`、`diff_attr_r63.json`、`dump_sf_titles_*.json`。

---

## 9. 交付清单(一句话)

标题现在**可编辑可回写**: 新增可注入表 `<版本>_text_sf_titles.csv`(145 行, `id=SFXML:A####`,
工具 `dump_sf_titles_csv.py`)与注入器的**属性级写入通道**(按 `entry_index` 定位、支持**改字数**、
增长吃 38238 B 陈旧尾巴、超出即中止); 实测 4 条真实错译落盘(1 长 / 1 短 / 2 等长, 净 −2 B,
帧 41615→41628 / 槽 49700), **另外 9 份副本 0 改动、141 个未编辑属性与 69 个 `<text>` 逐字节不变、
差异 37563 B 全部落在 MENU.IMG#283 槽内、槽外 0 B、ELF/PVD/IMG 条目表/字库 0 差异、
audit 缺失 0、dump_font 缺字形 0、报告文件 sha 幂等**; 缺字(`国会荣誉勋章` 的「荣」)**实测 exit 3 被拦下**;
**★ 唯一必须补的验证是实机版式**(标题栏宽度/居中, 模拟器本轮被占用)。
