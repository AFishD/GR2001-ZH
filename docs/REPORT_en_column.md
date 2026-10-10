# REPORT_en_column.md — CSV 增加只读参考列 `text_en`（英文原文，round34）

> 用户原话：
> > 另外 我希望**旁边有一列英文原文来进行辅助校对**。

**交付**

| 文件 | 改动 |
|---|---|
| `tools/text_csv/tcslib.py` | 新增「英文基线盘 → 文本」一节：`EN_ISO_DEFAULT` / `EN_CP1252` / `EN_ICON_BYTES` / `decode_en()` / `en_read_tables()` / `fmt_en_hist()`；**没见过的字节一律硬拒绝**（`EnDecodeError`） |
| `tools/text_csv/dump_text_csv.py` | 新增列 `text_en`（紧挨 `text_zh` 右边）+ `--en-iso` / `--no-en`；**默认自动**用 `work/builds/GR_EN_ORIG/GR_EN_ORIG.iso`；按 `id` 左连接、对不上/英文为空都写进 `note`；**洁净硬门槛扩到 4 列**；`meta.json` 新增 `en` 段 |
| `tools/text_csv/inject_text_csv.py` | 新增 `IGNORED_COLS = ('text_en',)` + `drop_ignored_cols()`：读 CSV 后**第一件事就是把这一列整列丢掉**（结构性保证，不是"忘了处理"）；控制台打印丢弃统计 |
| `tools/text_csv/FORMAT.md` | 列定义表加 `text_en`；新增 **§2.1「text_en（英文原文）—— 只读，怎么用它校对」**；§0/§1/§4/§5.5/§9 同步 |
| `work/text_csv/GR_ZH91_text.csv` | **重新生成**（2261 行，源盘 `work/builds/GR_ZH91/GR_ZH91.iso`，`42d04a4f…`） |
| `work/text_csv/GR_ZH91_text.meta.json` | 同步（新增 `en` 段：英文盘 sha256、对齐统计、字节映射表、两份拷贝差异清单） |
| `docs/REPORT_en_column.md` | 本报告 |

**结论：8/8 项验收全部通过。** 列位置正确、对齐 2250/2261（99.51%）、往返**零字节差异**、
`text_en` 里写任何垃圾都**不影响产物**、CSV 里 PUA/不可见字符 **0 个**。

测试脚本与日志（全部在 `work/text_csv/dev/`，本轮编号 `r34_*`）：

| 脚本 / 日志 | 作用 |
|---|---|
| `work/text_csv/dev/r34_probe_en.py` | 英文基线盘结构侦察（条目数/组结构/字节分布/回环） |
| `work/text_csv/dev/r34_probe2.py` → `dev/r34/log_en_bytes_ctx.txt` | **每个高位字节的上下文取证**（本报告 §2 的来源） |
| `work/text_csv/dev/r34_probe3.py` | 中文 CSV 的 id 集合 vs 英文盘 id 集合（对齐率预演） |
| `work/text_csv/dev/r34_copies_diff.py` → `dev/r34/log_en_copies_diff.txt` | 英文盘两份 LANG 拷贝逐条差异 |
| `work/text_csv/dev/r34_which_copy.py` → `dev/r34/log_which_copy.txt` | 判定中文译文是从哪一份拷贝翻的 |
| `work/text_csv/dev/r34_en_lib_test.py` | 新 tcslib 接口自测（含"未识别字节硬拒绝"） |
| `work/text_csv/dev/r34_check_csv.py` → `dev/r34/log_check_csv.txt` | 新旧 CSV 逐格对照 + 洁净计数 |
| `work/text_csv/dev/r34_evidence.py` → `dev/r34/evidence.txt` | 表头/BOM/CRLF、`note` 说明、抽样对照、对齐统计 |
| `work/text_csv/dev/r34_mangle_en.py` | 把 `text_en` 改成垃圾（10 行，覆盖 PUA/NUL/非法标记/10KB） |
| `work/text_csv/dev/r34_fallback_auto.py` | 「英文盘不存在」分支验证 |
| `dev/r34/log_rt_official.txt` / `log_rt_junk.txt` / `log_checkonly.txt` | 三次注入实跑全文 |

---

## 一、列位置与格式

```
id,resource,container,entry_index,offset,len_bytes,max_bytes,kind,wrap_w,lines,
"text_zh","text_en","text_edited","note"
```

实跑（`dev/r34/evidence.txt`）：

```
# 文件: work/text_csv/GR_ZH91_text.csv (816.3 KB)
# BOM(EF BB BF): True
# CRLF 记录数: 2262; 裸 LF (单元格内换行): 6267
# 表头行: id,resource,container,entry_index,offset,len_bytes,max_bytes,kind,wrap_w,lines,"text_zh","text_en","text_edited","note"
# 行数: 2261; LANG 2192 + SFXML 69
```

* `text_en` **紧挨 `text_zh` 右边**（用户要的"旁边"），`text_edited` 仍在它右边，**只改那一列**。
* 仍是 **UTF-8 with BOM + CRLF**，`text_en` 与其它正文列一样**加引号**（`ALWAYS_QUOTE`），
  单元格内的换行是 LF —— Excel 双击直接可开。
* `text_en` 里的换行与 `text_zh` **同一套写法**（`{br}`→换行、`{p}`→空行），
  但**不插软换行**（软换行按中文宽度算，套到英文上没意义）。

---

## 二、英文基线盘的高位字节：逐字节取证

英文盘正文里 `>=0x80` 的字节**共 10 种**（主拷贝 @MENU 侧 9 种；`0xA0` 只出现在 @GR 那份拷贝里），
**每一种都取到了上下文**（`log_en_bytes_ctx.txt`）：

| 字节 | 次数 | 出现在 | 英文原文上下文 | 判定 |
|---|---|---|---|---|
| `0x85` | 1 | `SFXML:T0068` | `…find a different line of work[85]just as an honest evaluation…` | **`…`**（Windows-1252 省略号） |
| `0x92` | 14 | `G012.I024` 等 7 条 | `…you[92]ll see a firing arc…` / `It[92]s good for snipers…` | **`’`**（右单引号） |
| `0xA0` | 2 | `G050.I010`（**仅 @GR 拷贝**） | `…as quickly as possible.[A0]The demolition charges…` | **空格**（不换行空格，降级成普通空格） |
| `0xAE` | 27 | `G058.I772` 等 | `…memory card (8MB) (for PlayStation[AE]2)…` | **`®`** |
| `0xB1` | 7 | `G012.I023` 等 7 条 | `…press the [B1] button  to remove it.` | ★ **手柄按键图标** |
| `0xB5` | 21 | `G012.I023/I024/I027` 等 | `Use the [B5] button to add a waypoint…` | ★ **手柄按键图标** |
| `0xBE` | 1 | `SFXML:T0010` | `…plastic shell with a layer of [BE] of a pound of composition C3 explosive…` | **`¾`** |
| `0xE7` | 1 | `G059.I028` | `Fran[E7]ais` | **`ç`** |
| `0xE9` | 1 | `SFXML:T0066` | `A growing d[E9]tente between the two countries…` | **`é`** |
| `0xF1` | 1 | `G059.I031` | `Espa[F1]ol` | **`ñ`** |

**结论 1：英文盘的高位字节就是 Windows-1252。** 10 种里 8 种文字字节
（`0x85` `0x92` `0xA0` `0xAE` `0xBE` `0xE7` `0xE9` `0xF1`）在上下文里**唯一自洽**地读作
`… ’ 空格 ® ¾ ç é ñ`（`you’ll` / `PlayStation®2` / `détente` / `Français` / `Español` / `¾`），
另 2 种（`0xB1` `0xB5`）是**引擎直接画图标的占位字节**。**没有一个是"猜"的。**

**结论 2（交叉验证 `¾`）**：`SFXML:T0010` 的英文是 `a layer of ¾ of a pound of composition C3`，
中文盘同一条译作「内装约 **340 克** C3 炸药」—— `¾ 磅 = 340.2 克`。**两盘互相印证。**

**结论 3（把 round33 的挂账结掉一半）**：

* `0xB1` / `0xB5` **确认是按键图标**：英文原文自己写着 `press the [B1] button` /
  `Use the [B5] button` ⇒ round33 把它们标成 `{{BTN:E0B1}}` / `{{BTN:E0B5}}` **是对的**。
* `0xE7` / `0xF1` **在英文盘里就是 `ç` / `ñ`**（`Français` / `Español`，语言选择菜单）——
  round33 报告 §1.3 的怀疑得到证实。中文盘那两条 `Fran{{BTN:E0E7}}ais` / `Espa{{BTN:E0F1}}ol`
  **很可能不是按键图标而是重音字母**；但**中文盘的字库里这两个字节画成什么，本轮没有实机取证**，
  所以中文侧**照旧原样保留**（不改动、不猜测），只在 `text_en` 里如实显示 `Français` / `Español`，
  并把这一条**继续挂账**（§六）。

**处理方式（与 `{{BTN:...}}` 同一思路）**：

| 字节 | CSV 里写成 | 说明 |
|---|---|---|
| `0xB1` `0xB5` | `{{BTN:E0B1}}` `{{BTN:E0B5}}` | 与 `text_zh` **完全同一套写法**，位置一一对应，方便核对 |
| 其余 7 种 | `’` `®` `¾` `ç` `é` `ñ` `…` / 普通空格 | **可见字符**，Excel 直接显示 |
| 任何**没见过的**字节 | —— | **拒绝 dump 并报错**（`EnDecodeError`，指名条目 + 字节 + 上下文） |

> 为什么不让 `0xA0`（不换行空格）原样进 CSV：它是**不可见**的，会变成"看起来一样的空格"，
> 属于 round33 那条硬门槛要拦的字符。降级成普通空格并在 `note` 里注明。
> （实测它**只出现在 @GR 那份拷贝**里，而 `text_en` 取的是 @MENU 拷贝 ⇒ 交付的 CSV 里 `0xA0` 实际 0 个。）

---

## 三、对齐方法与对齐率

**对齐键**

| 资源 | 键 | 说明 |
|---|---|---|
| `LANG` | `id`，形如 `G058.I195` | 两侧都用同一个 `parse_lang` 解析器、同一套 `G组号.I条目号` 编号 |
| `SFXML` | 条目序，形如 `T0010` | 两侧都是 `<text>` 在 XML 里出现的次序（1-based） |

**左连接**：中文有、英文没有 ⇒ `text_en` 留空 + `note` 写原因。三种情况在 `note` 里分别写成：

| 情况 | `note` 里的话 |
|---|---|
| 对上了、有英文 | （不写；若该条含非 ASCII 字节则追加 `; ★text_en 里有英文盘原始非 ASCII 字节 0x92→’×2 (…)`） |
| 对上了、但英文盘该条**本身就是空的** | `; ★英文原文本身为空 (英文基线盘里这条存在但正文 len=0, 不是没对齐)` |
| 英文盘**完全没有**这一条 | `; ★英文基线盘里没有这一条 (按 id / 条目序对不上) ⇒ text_en 留空` |
| 没给英文盘 | `; ★text_en 留空 (英文原文列): <原因>` |

**实跑结果**（dump 控制台 + `evidence.txt`）：

```
# --- text_en 对齐结果 (只读参考列) ---
# LANG   2192 行: 有英文原文 2192; 英文本身为空 0; 对不上 0
# SFXML  69 行: 有英文原文 58; 英文本身为空 11; 对不上 0
# 合计  2261 行: text_en 非空 2250 (99.51%); 英文本身为空 11; 对不上 0
# 其中 49 行的 text_en 里含英文盘原始非 ASCII 字节 (已转成可见字符, 并在该行 note 里注明) ✓
```

| 资源 | 中文行数 | `text_en` 非空 | 英文本身为空 | **对不上** |
|---|---|---|---|---|
| `LANG` | 2192 | **2192 (100%)** | 0 | **0** |
| `SFXML` | 69 | 58 | 11 | **0** |
| 合计 | 2261 | **2250 (99.51%)** | 11 | **0** |

**唯一"没英文"的 11 条**（全部是 SFXML）：

```
SFXML:T0001 SFXML:T0002 SFXML:T0003 SFXML:T0004 SFXML:T0005 SFXML:T0006
SFXML:T0007 SFXML:T0008 SFXML:T0009 SFXML:T0041 SFXML:T0042
```

**原因（已查明，不是错位）**：这 11 条在**英文基线盘里就是空条目**（`<text></text>`，`len=0`），
**中文盘同样为空**（`text_zh` 也是空、`len_bytes=0`）。也就是说**两盘在这 11 条上完全一致地空着**，
`text_en` 留空是**如实反映现状**。（顺带：`LANG` 侧英文盘 2232 条里有 40 条空条目，
中文盘 dump 时同样跳过这 40 条 ⇒ 两边都是 2192 条，**一一对应**。）

### 3.1 英文盘内部两份 LANG 拷贝有 12 条不一样 —— 取了哪一份

英文基线盘里 `EN_STRINGS.RES` 有**两份拷贝**（`MENU.IMG#25` / `GR.IMG#902`），
两份**内容不完全相同**（`log_en_copies_diff.txt`，12 条）：

| 条目 | @MENU | @GR | 中文译文跟哪一份 |
|---|---|---|---|
| `G012/13/…/18.I002` | `…go off on timers after you're clear of the **blast area**…` | `…timers **well** after you're clear of the **mission area**…` | **@MENU**（中文：「当你离开**爆炸范围**后」） |
| `G019.I006` | `…the **Caucasus Mountains**…` | `…the **Caucusus Moutains**…`（错别字） | **@MENU**（中文：「**高加索山区**」） |
| `G021.I008` | `in any way **practical**` | `in any way **practicable**` | 两可（中文「可行的」） |
| `G044.I010` | 少一整句 | 多 `They'll be detonated 30 seconds after you plant them, so move quickly.` | **@MENU**（中文**没有**"30 秒后引爆"这句） |
| `G049.I009` | `Here's` | `Here’s` | 两可 |
| `G050.I010` | `**plant** demo charges` / `naval base.{p}Your mission` | `**place** demo charges` / `naval base.{p} Your mission` | **@MENU**（中文：「在那里**安放**炸药」） |

⇒ **`text_en` 取第一份拷贝 `EN_STRINGS.RES@MENU`**（与中文盘 dump 的 `container` 主拷贝一致）。
6 条有判定价值的里 **4 条明确指向 @MENU**、2 条两可 —— 即：**这就是当初译者看到的英文**。
12 条的完整清单写进了 `.meta.json` 的 `en.copies_differ`，报告里也留档，**没有隐藏**。

---

## 四、验收实测（8 项）

### T1 往返零差异：新 CSV 原样注入 ⇒ sha256 = `42d04a4f…` ✓

```
& python tools/text_csv/inject_text_csv.py --csv work/text_csv/GR_ZH91_text.csv `
    --src work/builds/GR_ZH91/GR_ZH91.iso --dst work/builds/GR_ZH95_en/GR_ZH95_en_official.iso
```

`dev/r34/log_rt_official.txt`：

```
# 列  : id,resource,container,entry_index,offset,len_bytes,max_bytes,kind,wrap_w,lines,text_zh,text_en,text_edited,note
# 只读列: text_en —— **完全忽略** (2250 个非空单元格已丢弃, 不参与注入; 改了也不会进游戏) ✓
# 待检查(会被写入) 0 条; 逐字符检查完成
# 候选 2261 行; 实际改动 0; 未改动(与 text_zh 相同)跳过 2250; 与源盘等价跳过 11; 不在 --only 内 0
[diff] 全盘差异 0 B / 3 个写入窗口; 窗口外差异: 无 ✓
[hash] src 42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88
[hash] dst 42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88
[hash] 逐字节相同 (无改动)
```

**2261 行 `text_edited` 与 `text_zh` 逐格相同**（`log_check_csv.txt`：`2261/2261 ✓`）⇒ 一条都不写盘。

**附带两条**：

* 交付的 `work/text_csv/GR_ZH91_text.csv` 自身 sha256 =
  `7d55b9623a8ff89ea3b5d88b9d0bd5811f2ae892078ac06b2f643957f0e4d6b7`；
  **重新 dump 一次逐字节相同**（`dev/r34/log_idem.txt`，幂等 ✓）。
* 现役盘 `work/builds/GR_ZH91/GR_ZH91.iso` 全程只读，sha256 仍为 `42d04a4f…` ✓

### T2 `text_en` 不影响注入：故意改乱 ⇒ 产物 sha256 **不变** ✓

`r34_mangle_en.py` 把 **10 行**的 `text_en` 改成各种"会坏事"的写法：

| 条目 | 改成 |
|---|---|
| `LANG:G001.I000` | 中文乱码 `乱码乱码乱码 GARBAGE` |
| `LANG:G001.I002` | **留空** |
| `LANG:G012.I023` | 写错的按键标记 `{{BTN:ZZZZ}} {{{ }}} {{BTN:E0B1}` |
| `LANG:G012.I024` | **私有区 U+E0B1 + NUL + SOH + ESC + DEL + U+0085 + 软连字符** |
| `LANG:G050.I010` | 10,000 个 `X` |
| `LANG:G058.I797` | `"quoted", comma` + 换行 + CR（CSV 破坏串） |
| `SFXML:T0010` | 中文 + mojibake + `{{BTN:0000}}` |
| `SFXML:T0011` | 三个空格 |
| `SFXML:T0066` | `DROP TABLE text_en; --` |
| `SFXML:T0068` | 5,000 个 `a` |

自检确认：**除 `text_en` 外逐格完全相同**（0 处不同），只动了这 10 行。
`dev/r34/log_rt_junk.txt`：

```
# 只读列: text_en —— **完全忽略** (2249 个非空单元格已丢弃, 不参与注入; 改了也不会进游戏) ✓
# 按键标记: 共 60 处 / 4 个不同的标记: {{BTN:E0B1}} {{BTN:E0B5}} {{BTN:E0E7}} {{BTN:E0F1}}
# 候选 2261 行; 实际改动 0; 未改动(与 text_zh 相同)跳过 2250; 与源盘等价跳过 11; 不在 --only 内 0
[diff] 全盘差异 0 B / 3 个写入窗口; 窗口外差异: 无 ✓
[hash] src 42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88
[hash] dst 42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88
[hash] 逐字节相同 (无改动)
```

三个盘直接比 sha256：

```
往返产物(官方 CSV) : 42D04A4F61982A00B2B31B6A4ECC97EC0D814810B56E0695BEFDB63B4B92EC88
text_en 乱码产物   : 42D04A4F61982A00B2B31B6A4ECC97EC0D814810B56E0695BEFDB63B4B92EC88
源盘 GR_ZH91(未动) : 42D04A4F61982A00B2B31B6A4ECC97EC0D814810B56E0695BEFDB63B4B92EC88
三者相同: True
```

> 注意：连**写错的 `{{BTN:ZZZZ}}`** 都没能拦下注入 —— 因为那一列在扫描之前就已经被丢掉了。
> 这是**有意的**：`text_en` 是只读参考，不是输入。

**保证是怎么做的（不是"碰巧没读"）**：`inject_text_csv.py` 里

```python
IGNORED_COLS = ('text_en',)

def drop_ignored_cols(rows, cols):
    ...
```

在 `read_csv()` 之后**立刻**调用，后续所有代码（按键标记扫描 / 字库预检 / 写入计划）
都**不可能再看到**这一列。

### T3 CSV 洁净：PUA / 不可见控制字符 = 0；`{{BTN:...}}` 计数不变 ✓

```
# 洁净: 2261 行 × 4 列 = 365776 字符; PUA/不可见控制字符 = 0 ✓
#   {{BTN:...}} 计数 text_zh      = 30
#   {{BTN:...}} 计数 text_en      = 28
#   {{BTN:...}} 计数 text_edited  = 30
#   {{BTN:...}} 计数 note         = 58
#   {{BTN:...}} 中文两列合计: 旧 60 → 新 60 ✓
# text_en 非空 2250/2261; 非 ASCII 字符: ®(U+00AE)×27 ¾(U+00BE)×1 ç(U+00E7)×1 é(U+00E9)×1 ñ(U+00F1)×1 ’(U+2019)×14 …(U+2026)×1
```

* `text_zh` / `text_edited` 的 `{{BTN:...}}` 计数 **旧 60 → 新 60，一处没变** ✓
* `text_en` 28 处 = `0xB1`×7 + `0xB5`×21（`0xE7`/`0xF1` 按 Windows-1252 显示成 `ç`/`ñ`，
  所以不是 30）—— 与英文盘实际字节数完全吻合。
* 新增的非 ASCII 字符**只有 7 种**，全部是**可见**字符（`® ¾ ç é ñ ’ …`），
  **没有任何 PUA / 控制 / 零宽字符**。
* dump 端硬门槛（`assert_cells_clean`）已扩到 4 列，实测通过。

### T4 抽样对照 10+ 条（含 SFXML 长段与 LANG 短文本）✓

（`dev/r34/evidence.txt`，`⏎` = 单元格内换行）

**SFXML 长段**

```
[SFXML:T0010]  kind=long wrap_w=270
  中 | M18 定向反步兵地雷由曲面的方 ⏎ 形硬质弹体制成， 内装约 340 克 ⏎ C3 炸药。 ⏎ 其破片面由方形金属破片构成， ⏎ 起爆时破片以扇形射出。 …
  英 | The M18 Claymore anti-personnel mine consists of a curved rectangular plastic shell with a layer of ¾ of a pound of composition C3 explosive. It has a fragmentation face of rectangular steel fragments designed to blow out in a fan-shaped pattern. …

[SFXML:T0011]  kind=long wrap_w=270
  中 | M2 定向炸药是一种定向装药， ⏎ 能够穿透石料和其他轻型建筑材 ⏎ 料。放置得当时， ⏎ 这类炸药可以摧毁道路、 ⏎ 桥梁和其他永久性建筑。
  英 | The M2 Demolitions charge is a shaped directional charge capable of cutting through concrete and other light building materials. Placed properly, these charges are capable of destroying roads, bridges, and other permanent structures.

[SFXML:T0066]  kind=long wrap_w=270
  中 | 非洲战役： ⏎  ⏎  ⏎ 俄罗斯大乱余波未平，世界各地又 ⏎ 接连爆发多场小规模战事。 ⏎ 其中最致命的，是埃塞俄比亚与厄 ⏎ 立特里亚战火又起。 …
  英 | The African Campaign: ⏎  ⏎ In the wake of the upheaval in Russia, a series of small brushfire wars erupt around the world. One of the deadliest is a resumption of hostilities between Ethiopia and Eritrea. ⏎  ⏎ A growing détente between the two countries is dis …

[SFXML:T0067]  kind=long wrap_w=270
  中 | 开发手记：第一辑 ⏎  ⏎  ⏎ 达伦丘基图斯 ⏎  ⏎ 制作人 ⏎  ⏎ 幽灵行动 ⏎  ⏎ 手记 1: ⏎  ⏎  ⏎ 对幽灵行动团队来说，这个月相当 ⏎ 提气。我们完成了 Alpha 节点， …
  英 | DESIGNER DIARIES: FIRST SET ⏎  ⏎ Darren Chukitus ⏎ Producer ⏎ Ghost Recon ⏎ Entry 1: ⏎  ⏎ It has been an exciting month for the Ghost Recon team. We have finished our Alpha milestone …

[SFXML:T0068]  kind=long wrap_w=270
  中 | 开发手记：第二辑 ⏎  ⏎  ⏎ 罗比爱德华兹 (副制作人)： ⏎  ⏎ 手记 1: ⏎  ⏎  ⏎ 一切都在正常推进，我们正走向 ⏎ Beta。到了这一步， ⏎ "正常"就意味着压力。 …
  英 | DESIGNER DIARIES: SECOND SET ⏎  ⏎ Robbie Edwards (Associate Producer): ⏎ Entry 1: ⏎  ⏎ Things are moving along normally as we progress towards beta. Normal at this stage in a project means filled with stress. …
```

**LANG 短文本 / 术语 / 记忆卡提示**

```
[LANG:G001.I000]  kind=short
  中 | 胜利！
  英 | Victory!

[LANG:G001.I002]  kind=short
  中 | 全部敌人被消灭后玩家获胜。
  英 | The players win if all enemies are eliminated.

[LANG:G058.I797]  kind=long_nowrap
  中 | 正在读取记忆卡插槽1中的记忆卡(8MB)。 请勿取出记忆卡(8MB)。
  英 | Accessing memory card (8MB) (for PlayStation®2) in MEMORY CARD slot 1. Do not remove memory card (8MB) (for PlayStation®2), reset, or switch off console.

[LANG:G058.I772]  kind=long_nowrap
  中 | 记忆卡(8MB)(PlayStation®2 用)空间不足。请插入一张有空余空间的记忆卡(8MB)(PlayStation®2 用)。
  英 | Insufficient space on memory card (8MB) (for PlayStation®2). Insert a memory card (8MB) (for PlayStation®2) with at least 500KB of free space, or create some space using the console's internal browser.
```

**按键图标 / 重音字母（最需要对照的两类）**

```
[LANG:G012.I023]  kind=long_nowrap
  中 | 你的小队分为两个战斗小组。你在A组。… 按 {{BTN:E0B5}} 键添加路径点，按 {{BTN:E0B1}} 键删除。练习给B组下达移动命令。…
  英 | Your platoon is organized into two fireteams.  You're in Fireteam Alpha.  …  Use the {{BTN:E0B5}} button to add a waypoint, and press the {{BTN:E0B1}} button  to remove it.  …

[LANG:G012.I024]  kind=long_nowrap
  中 | 添加路径点时按住 {{BTN:E0B5}} 键会出现一个射击扇面。…
  英 | If you hold the {{BTN:E0B5}} button down while adding a waypoint you’ll see a firing arc. …

[LANG:G059.I028]  kind=short
  中 | Fran{{BTN:E0E7}}ais
  英 | Français
```

⇒ **英文那列是通顺英文，与中文逐条对得上，没有错位、没有乱码。**
按键标记在两列里**位置与个数一一对应**（`G012.I023` 两边都是 `E0B5` 在前、`E0B1` 在后）。

### T5 对齐率统计与未对齐清单 ✓

见 §三。**合计 2250/2261 = 99.51%**；未对齐 **0 条**；11 条"英文本身为空"已列出并说明原因。

### T6 兜底分支（不给英文盘）✓

三种情况都实测过，都**留空 + 在 `note` 里说明**，且**不影响 dump 的其它输出**：

```
# [跳过] text_en 整列留空 —— 命令行给了 --no-en
# [跳过] text_en 整列留空 —— --en-iso 指定的文件不存在 (Z:\nope\missing.iso)
# [跳过] text_en 整列留空 —— 英文基线盘不存在 (work/builds/GR_EN_ORIG/NOT_THERE.iso), 也没给 --en-iso
```

（第三种用 `dev/r34_fallback_auto.py` 把 `EN_ISO_DEFAULT` 指到不存在的路径来验证自动探测分支。）

### T7 没破坏既有行为 ✓

* 旧 CSV（round33 版）与新 CSV **除 `note` 外逐格完全相同**（`log_check_csv.txt`）：

```
# 旧列逐格一致 (除 note): ✓ (0 处不同)
# note: 原样 2201, 追加说明 60, 前缀不符 0
# text_edited == text_zh 的行: 2261/2261 ✓ (未编辑任何东西)
```

  `note` 只在末尾**追加**说明（60 行 = 49 行含非 ASCII 字节 + 11 行英文为空），**不覆盖原文**。
* `{{BTN:...}}` 计数、`text_zh`/`text_edited` 内容、`offset/len_bytes/max_bytes/kind/wrap_w/lines`
  全部未变 ⇒ **round33 的行为一个字没动**。
* 同事的 `tools/text_csv/diff_text_versions.py`（用 `csv.DictReader` + `.get('text_edited')`，
  **按列名取值**）在新 CSV 上照常工作：`2261 条 / 65347 字符 / 其中中文 45732`，exit=0。
* `--check-only` 在新 CSV 上：`待检查(会被写入) 0 条 … [ok] 字库覆盖完全 ✓ [check-only] 只预检, 未写盘。`

### T8 英文盘里的"占位/控制字符"如实报告 ✓

* 英文盘正文里 `>=0x80` 的字节 **9 种，全部列在 §2**，逐个给了上下文与判定；
  **没有一个被静默丢弃**。
* 英文盘正文里 **ASCII 控制字符（`<0x20` / `0x7F`）0 个**（`r34_probe3.py` 全表扫描）。
* 若将来英文盘冒出**本工具没见过的字节**，dump 会**拒绝写 CSV**并报错，
  例如人为造一个 `0x9F`：

```
[ok] 已拒绝: 英文盘 TEST 第 7 个字节是 0x9F —— 本工具**没见过**这个字节, 不猜它的含义。
   上下文: b'hello \x9f world'
   怎么办: 请人工确认这是哪个字符 (英文盘的高位字节实测符合 Windows-1252), 然后加进 tcslib.EN_CP1252 …
```

---

## 五、改了什么（逐处）

### `tools/text_csv/tcslib.py`

新增一节「英文基线盘 → CSV 的 text_en 列 (round34)」（在文件末尾 `splice` 之后）：

| 名字 | 作用 |
|---|---|
| `EN_ISO_DEFAULT` | 默认英文盘路径 `work/builds/GR_EN_ORIG/GR_EN_ORIG.iso` |
| `EN_CP1252` | 8 个高位字节 → 可见字符（`0x85→…` `0x92→’` `0xA0→空格` `0xAE→®` `0xBE→¾` `0xE7→ç` `0xE9→é` `0xF1→ñ`） |
| `EN_ICON_BYTES` | `0xB1` `0xB5` → `{{BTN:E0B1}}` `{{BTN:E0B5}}` |
| `decode_en(data, where)` | 字节 → 文本 + 统计；**未列出的字节 / C0 / DEL ⇒ 抛 `EnDecodeError`（拒绝 dump）** |
| `en_read_tables(iso)` | 读英文盘 LANG（拷贝 0）+ SFXML，返回 `{id: 文本}` ×2 + info（条目数/字节分布/空条目/两份拷贝差异/逐条原始字节） |
| `fmt_en_hist()` | 人话打印 `92×14→’ AE×27→® …` |

### `tools/text_csv/dump_text_csv.py`

* `COLS` 插入 `text_en`（在 `text_zh` 之后）；`ALWAYS_QUOTE` 加 `text_en`；新增 `CELL_COLS`。
* `assert_cells_clean()` 默认扫 **4 列**，错误提示里点明"若出在 text_en 列 = 英文盘有没见过的字节"。
* 新增 `hexkey()` / `_en_byte_note()` / `attach_text_en()`（左连接 + note 说明 + 统计）。
* 新增 CLI `--en-iso <iso>` 与 `--no-en`；**默认自动探测** `EN_ISO_DEFAULT`。
* 新增控制台一节「text_en (只读参考列: 英文原文)」与「text_en 对齐结果」。
* `meta.json` 新增 `en` 段（英文盘路径/sha256/来源拷贝/对齐键/策略/两资源统计/字节映射表/
  `copies_differ`/`aligned`）。

### `tools/text_csv/inject_text_csv.py`

* 模块 docstring 加一条"`text_en` 完全忽略"。
* 新增 `IGNORED_COLS` + `drop_ignored_cols()`；`main()` 里 `read_csv()` 之后立刻调用并打印统计。
* **其余逻辑一行未改**（按键标记扫描、字库预检、写入、报告）。

### `tools/text_csv/FORMAT.md`

* 标题、文件表、round34 提示块。
* §0 三步上手（含 `--en-iso` / `--no-en` 示例）。
* §1 引号列清单加 `text_en`。
* §2 列定义表加 `text_en` 行；**新增 §2.1**（是什么/怎么对齐/为什么只读/7 步校对流程）。
* §4 加第 9 条（`text_en` 只读，附实测结论）。
* §5.5 硬门槛从 3 列改 4 列，计数更新为 `365,776 字符 / {{BTN}} 146 处`
  （`text_zh` 30 + `text_en` 28 + `text_edited` 30 + `note` 58；`note` 多出的 28 处是新加的
  「英文原文原始字节」注记，仍是**合法可复制**的标记）。
* §9 更新：`0xB1/0xB5` 已确认是图标、`0xE7/0xF1` 在英文盘是 `ç/ñ`（继续挂账）、
  两份拷贝 12 条差异、11 条 SFXML 空条目属正常。

---

## 六、已知限制 / 挂账

1. **`0xE7` / `0xF1` 在中文盘上到底画成什么，仍未实机确认。** 本轮只证明了英文盘里它们是
   `ç` / `ñ`。中文盘字符表里这两个字节**没有映射**，工具链仍按 `{{BTN:E0E7}}` / `{{BTN:E0F1}}`
   原样保留（**不改动现役盘**）。建议专项：实机看语言选择菜单里法语/西语两行的显示，
   若是方框/空图标 ⇒ 中文盘确实缺这两个重音字形，需要另开补字库的工作项。
2. **`text_en` 只覆盖 `LANG` + `SFXML` 两类资源**（与 `text_zh` 的覆盖面一致）。
   盘里其它文本（其它 RES 字符串表、ELF 内字符串、纹理/影片字幕）仍然没有英文对照列。
3. **`text_en` 不插软换行** ⇒ 英文那格显示的是**显式换行**（`{br}`/`{p}`）视图，
   与 `text_zh`（XML 长段带软换行）在行数上不可直接比较。要按宽度比较行数请另开需求。
4. **英文盘两份拷贝的 12 条差异已留档但未做取舍**：`text_en` 取 @MENU（有 4 条证据支持
   "这就是译者看到的英文"）。若将来有人能证明译者用的是 @GR，改一行即可换源
   （`tcslib.en_read_tables` 里的 `ent_by_copy[0]` → `[1]`）。
5. **`text_en` 是"参考"，不是"标准答案"**：英文原文本身有错别字
   （@MENU 侧如 `G019.I006` 的 `Caucasus Mountains` 反而**是正确**的那份；@GR 侧写成了
   `Caucusus Moutains`），校对时请以中文文案质量为重，不要把英文当唯一真理。

---

## 附：复现命令

```powershell
$py = 'C:\ProgramData\anaconda3\python.exe'

# ① 重新 dump（自动带 text_en）
& $py tools/text_csv/dump_text_csv.py --iso work/builds/GR_ZH91/GR_ZH91.iso `
    --out work/text_csv/GR_ZH91_text.csv

# ② 往返零差异（新 CSV 原样注入 ⇒ 应与源盘 sha256 相同）
& $py tools/text_csv/inject_text_csv.py --csv work/text_csv/GR_ZH91_text.csv `
    --src work/builds/GR_ZH91/GR_ZH91.iso --dst work/builds/GR_ZH95_en/GR_ZH95_en_official.iso

# ③ text_en 不影响注入（改乱再注入 ⇒ 与 ② 产物 sha256 相同）
& $py work/text_csv/dev/r34_mangle_en.py work/text_csv/GR_ZH91_text.csv `
    work/text_csv/dev/r34/GR_ZH91_text.en_junk.csv
& $py tools/text_csv/inject_text_csv.py --csv work/text_csv/dev/r34/GR_ZH91_text.en_junk.csv `
    --src work/builds/GR_ZH91/GR_ZH91.iso --dst work/builds/GR_ZH95_en/GR_ZH95_en_tenjunk.iso

# ④ 证据汇总
& $py work/text_csv/dev/r34_evidence.py work/text_csv/GR_ZH91_text.csv
& $py work/text_csv/dev/r34_check_csv.py `
    work/text_csv/dev/r34/r33_prev_GR_ZH91_text.csv work/text_csv/GR_ZH91_text.csv
```

**产物盘（测试用，均在 `work/builds/GR_ZH95_en/`）**

| 文件 | 含义 | sha256 |
|---|---|---|
| `GR_ZH95_en_official.iso` | 用**官方 CSV** 原样注入 | `42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88` |
| `GR_ZH95_en_tenjunk.iso` | 用 **`text_en` 全改乱**的 CSV 注入 | `42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88` |

> 现役盘 `work/builds/GR_ZH91/GR_ZH91.iso` **全程只读**，未被修改（sha256 未变）。
> 本次改动**没有**碰 `tools/iso_build/**`、`tools/text_csv/diff_text_versions.py`、
> `docs/` 下其它文档；没有动 `GR.IMG` 条目 `off`/`stored`；没有碰制作组名单
> （`GR.IMG #551..#565`）；没有动 `MENU.IMG` 内部偏移；**没有执行任何 git 操作**。
