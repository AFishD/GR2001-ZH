# REPORT_csv_text_tool — dump→人工改换行→注入 工具链（round29）

日期 2026-10-09 · 分支 `round29/csv-text-tool` · 现役基底 `work/builds/GR_ZH89/GR_ZH89.iso`
（sha256 `6d2afd49a3d158253d9c9cfd2cd1678c57ed1ab39e6cc502938b7d37eca26cbf`）
产物盘 `work/builds/GR_ZH90/GR_ZH90.iso`（sha256 `ad5f0b47c18939b4ce4d25dbe134025966bdc6140bf2b0b6a48b491871eff8ad`）

---

## 0. 一句话结论

一条长段文本在盘上就是「一串字节 + 引擎自己按像素宽折行」；本工具链把它 dump 成
**一条一行、正文带引号、换行就是引擎换行**的 CSV，编辑者只要在 Excel 里**增删换行**，
注入器就把这些换行变成引擎的显式换行标记写回原槽位。**不改任何容器条目表、不重建 ISO、
不动 ELF**；未改动的条目逐字节不变（dump→直接注入 = 原盘 sha256 完全相同）。

---

## 1. 交付物

| 文件 | 说明 |
|---|---|
| `tools/text_csv/dump_text_csv.py` | dump：扫描资源 → 计算当前渲染折行 → 写 UTF-8 BOM + CRLF 的 CSV |
| `tools/text_csv/inject_text_csv.py` | 注入：按 `text_edited` 改换行/改字 → 子流重压 → 只写原槽位 |
| `tools/text_csv/tcslib.py` | 公共库（ISO/IMG、LZO、字符集、折行模型、容器解析、解码自检） |
| `tools/text_csv/FORMAT.md` | **给非程序员看的**格式与操作说明（列定义/换行约定/安全须知） |
| `tools/text_csv/runcap.py` | 实机捕获器（等价 `run_opt.py`，可指定 `-grscanframes`；本轮定位时间线用） |
| `tools/text_csv/scan_text_resources.py` | 覆盖范围盘点器（遍历 IMG 条目找含文本的容器） |
| `work/text_csv/GR_ZH89_text.csv` | **示例 CSV**：现役盘全量 dump（2261 行，覆盖 2 类资源） |
| `work/text_csv/GR_ZH90_edit_demo.csv` | 示例 CSV（人工改动版）：2 条改动，用于实机验证 |
| `work/archive/cmp/r29_csv/` | 验证证据（往返 sha256 输出、前后同帧 PNG、像素对照、扫描清单、文本样本） |
| 本文件 | 设计取舍 / 迁移路径 / 已知限制 / 覆盖范围 |

> 本轮**只新增文件**：`git status` 显示仅 `tools/text_csv/`（未跟踪）等新增路径，
> 没有修改任何既有脚本/文档；`tools/iso_build/patch_zh84.py` 等只读参考，未改动。

---

## 2. CSV 格式（完整定义见 `tools/text_csv/FORMAT.md`）

```
id,resource,container,entry_index,offset,len_bytes,max_bytes,kind,wrap_w,lines,text_zh,text_edited,note
LANG:G024.I007,LANG,EN_STRINGS.RES@MENU+GR.IMG#902,G024.I007,26537,723,54817,long_nowrap,0,,  "地点：俄罗斯，伊兹博尔斯克
                                                                                             （空行）
                                                                                             正式消息：…",  "（同上，人工编辑栏）",  "长段; …"
```

* **编码**：UTF-8 with BOM；记录间 CRLF；单元格内换行用 LF；`text_zh`/`text_edited`/`note` 恒加引号。
* **一条文本 = 一行**；正文里的换行在引号内部，Excel 双击打开即可编辑。
* `id` 形如 `LANG:G024.I007` / `SFXML:T0010`；`--only` 支持精确值、逗号列表与前缀 `*`。

### 换行约定（核心）

| 盘上的字节 | CSV 单元格 |
|---|---|
| `{br}` | 1 个换行 |
| `{p}` | 1 个空行（连续 2 个换行） |
| 无标记、引擎自动折行 | dump 按**当前渲染**插入 1 个换行（软换行/建议断点） |

| `text_edited` 里的写法 | 写回的字节 |
|---|---|
| 1 个换行 | `{br}` |
| 空行（≥2 个换行折叠为 1 处） | `{p}` |

**正文里不出现 `{br}`/`{p}`** —— 它们就是换行本身；机器标记 ↔ 换行的映射只由两个脚本负责。

### 「动过才生效」判定（保证零改动 = 零差异）

* `text_edited == text_zh`（或留空）⇒ **这一条完全不动**（逐字节不变）；
* 只要动过这一格 ⇒ 该条按 `text_edited` 的换行整体重写；
* 要清空一条填哨兵 `[[empty]]`；`text_zh` 是只读参考（改了不生效，注入器只读 `text_edited`）。

---

## 3. 设计取舍

1. **为什么 `text_edited` 预填成和 `text_zh` 一样**
   非程序员的最短路径是"打开 → 直接改那一格"，不用先复制粘贴。代价是"是否人工改过"
   必须有个判据 —— 用**两列是否相同**判定，简单、可解释、且让"零改动注入"严格等于"零字节改动"。
2. **软换行 = 建议，硬换行 = 人工意图**
   长段文本在盘上**没有**换行字节，只有引擎的自动折行。dump 把"现在断在哪"直接插成换行，
   编辑者一眼可见；他保留哪个断点，注入后就固定在那里（`{br}`）。既满足"人工主动操作换行"，
   又不会在没人改的时候擅自把自动折行固化成硬换行。
3. **未标定宽度的资源不插软换行**
   语言表被教程/简报/菜单等多种组件消费，宽度不同（本轮未逐一标定）⇒ `wrap_w=0`，
   只显示 `{p}` 段落，不凭空生成建议断点；需要时 `--wrapw LANG=NNN` 强制开启（会写进 `wrap_w` 列）。
   `SFXML` 的 270 有实机逐行证据（下 §4.3），默认开启。
4. **不改条目表、不重建 ISO**
   所有写回都在**原 `off` 槽位内**完成；变长用容器**尾部陈旧区**（语言表 59,930 B / XML 39,056 B
   CRLF 填充）吸收，保持解压总长与子流切分不变 ⇒ IMG 条目 `off/stored/real` 三字段一动不动
   （历史铁律：移动条目会让任务开始卡死）。
5. **只重压变了的子流**
   语言表/ XML 都是 `16384×7 + 尾流` 的 LZO 子流序列；未变子流**原压缩字节照搬**，
   变了的子流按原 `real` 尺寸重压并回环校验。既省时又避免"整块重压导致帧变胖"。
6. **两条保护性硬约束**
   ① 解压总长必须与原件**严格相等**（尾部吸收/补零），否则拒绝；
   ② 压缩帧必须 ≤ 原槽位，超槽直接报错并列出是哪几条撑爆的 —— 绝不写半成品盘。
7. **语言表两份拷贝同步写**
   `MENU.IMG#25` 与 `GR.IMG#902` 是同一逻辑表的两份副本（实测 2232 条 payload **完全相同**），
   注入器两份一起写并断言一致，避免"改了 MENU 没改 GR"的历史事故。
8. **`text_zh` 里的按键图标用私有区占位**
   0xB1~0xB5 等按键图标字节不在字表里，直接解码会变 `?`；工具把它们回落成 `U+E0xx`
   占位（可无损回写），并在 `note` 里提示该条有几个 —— 编辑者不会无意删掉图标。

---

## 4. 验证

### 4.1 往返零差异（dump → 原样注入 → 逐字节相同）

**逐行无损性**（`work/archive/cmp/r29_csv/csv_lossless.txt`，2261 行全覆盖）：

```
BOM=True ; CRLF 行数 2262 ; 列数异常行 无 ; 数据行 2261
① 渲染可复现 (全部行)   : 一致 2261 / 不一致 0      ← 用原字节重算渲染 == CSV 的 text_zh
② 非软换行行逐字节可逆  : 一致 2203 / 不一致 0      ← encode(text_zh) == 盘上原始字节
③ 软换行行 (渲染视图)   : 58 行 —— 无损性由"未改动则跳过"保证
text_edited≠text_zh 的行: 0
```

即：**2203 条**（语言表 2192 + XML 短条 11）是"文本 ↔ 字节"严格双射；
**58 条**软换行长段是"渲染视图"（多出来的换行是引擎当前折行点，不是存储字节），
它们靠"`text_edited` 没动过就整条跳过"保证零改动 —— 两条路径合起来覆盖全部 2261 行。

**整盘往返**（`work/archive/cmp/r29_csv/roundtrip_none.txt`）：

```
[diff] 全盘差异 0 B / 3 个写入窗口; 窗口外差异: 无 ✓
  EN_STRINGS.RES@MENU    条目 2232: 改动 0 / 逐字节不变 2232; ngroups=66 结构重解析 OK
  EN_STRINGS.RES@GR      条目 2232: 改动 0 / 逐字节不变 2232; ngroups=66 结构重解析 OK
  EN_SPECIAL_FEATURE.XML 条目 69: 改动 0 / 逐字节不变 69, 结构计数 {'<text>':69,'</text>':69,
                         '<studio':10,'<item':94,'<group':41,'</SpecialFeatures>':1} 不变
[hash] src 6d2afd49a3d158253d9c9cfd2cd1678c57ed1ab39e6cc502938b7d37eca26cbf
[hash] dst 6d2afd49a3d158253d9c9cfd2cd1678c57ed1ab39e6cc502938b7d37eca26cbf
```

### 4.2 真实变更 + 实机验证（前后同帧）

人工改动 2 条（`work/text_csv/GR_ZH90_edit_demo.csv`，`work/archive/cmp/r29_csv/inject_report.json`）：

| id | 内容 | 字节 | 渲染行 |
|---|---|---|---|
| `SFXML:T0010` | M18 定向地雷介绍：把「M18 定向反步兵地雷」独立成行，后面按语义重排 | 174 → 192 (+18) | 8 → 8（断点不同） |
| `LANG:G048.I008` | 战术演习练习 1 简介：第一段句号后主动换行；并删掉 3/4 段之间的空行 | 239 → 244 (+5) | 4 → 5 |

注入日志（同上文件）：

```
== LANG (EN_STRINGS.RES@MENU) ==  编辑 1 条; 解压 128545 → 128545 (+5, 尾区 59930); 帧 32414 → 32420 / 槽 47570 (余 15150); 重压子流 3/8
== LANG (EN_STRINGS.RES@GR)   ==  编辑 1 条; 解压 128668 → 128668 (+5, 尾区 60053); 帧 32415 → 32421 / 槽 47619 (余 15198); 重压子流 3/8
== SFXML (EN_SPECIAL_FEATURE.XML)== 编辑 1 条; 解压 116486 → 116486 (+18, 尾区 39056); 帧 41576 → 41575 / 槽 49700 (余 8125); 重压子流 5/8
[diff] 全盘差异 64333 B / 3 个写入窗口; 窗口外差异: 无 ✓
[verify] EN_STRINGS.RES@MENU 条目 2232: 改动 1 / 逐字节不变 2231 ; … XML 结构计数不变
```

**实机（PCSX2 gsrunner）前后同帧像素对照**（`work/archive/cmp/r29_csv/png/`）：

| 场景 | 帧 | 差异像素 | 差异外接框 | 判读 |
|---|---|---|---|---|
| 特别收录列表（进武器页之前） | F10900 / F11000 | **0** | — | 其它界面零回归 |
| 特别收录→武器→M18 介绍页 | F11100~F11600 | 3749 | (31,158)-(252,205) | 只有介绍正文前 3 行变 |
| 战术演习列表（进简报页之前） | F9000~F9200 | **0** | — | 其它界面零回归 |
| 战术演习→简报页（练习 1 简介） | F9300~F10300 | 2266 | (36,71)-(267,103) | 只有简介正文变 |

对照图（左=改前 ZH89，右=改后 ZH90）：`png/cmp_f11300.png`（M18）、`png/cmp_f09600.png`（简报），
另有 `before_*/after_*` 单帧 PNG。实机画面确认：

* M18 介绍第 1 行变成 **`M18 定向反步兵地雷`**（改前是 `M18 定向反步兵地雷由曲面的方`），
  后续行按人工断点重排 —— **人工换行原样生效**；
* 简报页第 1 段断在 **`欢迎参加第一次战术演习。`** 之后（改前是 `…本次任`）——
  说明 `{br}` 在**语言表简报组件**里同样有效（这是本轮第一次在语言表里使用 `{br}`，
  此前该表只出现 `{p}`；现已实证）。

### 4.3 折行模型与实绘逐行一致（软换行的可信度）

改前 F11300 实机画面 8 行与 CSV `text_zh` **逐行逐字相同**：

```
M18 定向反步兵地雷由曲面的方 / 形硬质弹体制成， 内装约 340 克 / C3 炸药。 /
其破片面由方形金属破片构成， / 起爆时破片以扇形射出。 /
由于装药的原因，地雷正后方存在 / 一小片杀伤区，而爆炸正面则是大 / 范围毁伤区。
```

⇒ `wrapW=270`、汉字 16 / ASCII 8 / 空格 3 / tracking 1、`{br}`/`{p}` 分段的口径在本盘、
本版本、本屏实测成立；软换行不是猜的。

### 4.4 容器自洽

* 语言表：`ngroups=66`、2232 条、有效区 68615 B，注入后**重新解析**成功、条目数与结构一致；
  两份拷贝 payload 注入后仍完全一致。
* XML：`<text>`/`</text>`/`<studio`/`<item`/`<group`/`</SpecialFeatures>` 计数不变，
  `<text>` 69 条、未编辑的 68 条逐字节不变。
* 全盘 diff 只落在 3 个写入窗口内（0 字节越界）。

---

## 5. 解码口径的坑（Lead 转来 label-fixer 的实测，本轮复核）

* **本工具链是「单字节码优先」**：只有 `0xA1..0xAD` 是双字节 lead（ELF 四处
  `sltiu reg, lead, 0xAE` 实测），`0xAF` = 单字节「的」、`0xB0` = 单字节「你」。
* **`tools/diag/res_text_dump.py` 的 `dec()` 是对偶（双字节）优先，会系统性错字**：
  实测 `AF A1 BD`（的 方）被读成「弗开」、`B0 AF`（你 的）被读成「蔡」。
  **不要用它 dump 后编辑再写回**（会把好数据写坏）。本轮未改动该脚本。
* 本工具在 dump 时做**锚点自检**并拒绝在有 `[!!]` 时出 CSV
  （`work/archive/cmp/r29_csv/dump_selfcheck.txt`）：

```
[ok] 单字节码 的 = 0xAF / 你 = 0xB0 ; 字节 0xAF → 的 / 0xB0 → 你
[ok] AF A1 BD → '的方'（对偶优先会误读成 弗开）
[ok] LANG G058.I195 = '命令'  G058.I192/193/194 = A组/B组/C组
[ok] LANG G058.I797 = '正在读取记忆卡插槽1中的记忆卡(8MB)。 请勿取出记忆卡(8MB)。'
[ok] 字表中 lead≥0xAE 的死 pair 137 个, 编码器已拒绝写出
```

* 编码器另有两道闸：拒绝写出 lead≥0xAE 的死 pair（引擎会读成两个单字节）；
  写出后**回读校验** `decode(encode(t)) == t`，不对称即报错 ——
  防止"往返 sha256 相同但内容是错字"。
* 人眼可读样本见 `work/archive/cmp/r29_csv/text_samples.txt`（A组/命令/读卡提示/教程/简报/M18 等 12 条）。
* **建议（Lead 另立任务）**：全工程统一到 `tcslib.Charset` 口径；`res_text_dump.py` 等
  对偶优先工具应标注废弃或改口径，避免后续轮次再踩。

---

## 6. 覆盖范围：现在能改什么、还覆盖不了什么

**已覆盖（本工具链）**

| 资源 | 位置 | 规模 | 变长支持 |
|---|---|---|---|
| `LANG` 语言表 | `MENU.IMG#25` + `GR.IMG#902`（两份同步） | 2232 条 / 54,695 B 正文（255 条长段） | ✅ 尾部 59,930 B 吸收 |
| `SFXML` 特别收录 | `MENU.IMG#283 EN_SPECIAL_FEATURE.XML` | 69 条 `<text>` / 45,186 B（58 条长段） | ✅ 尾部 39,056 B CRLF 吸收 |

**还没覆盖（`scan_text_resources.py` + `docs/PATCH_INVENTORY.md` 交叉确认）**

| 资源 | 位置/形态 | 为什么没覆盖 | 迁移代价 |
|---|---|---|---|
| `EN_STRINGS.TXT` [#30] | 明文（非 LZO）键值表，10 个键 | 不是 LZO 子流容器，且该表值从不被游戏显示 | 低（直接等长覆写即可，属另一类容器） |
| `.ATR` 人名字段（GR.IMG ~250 条） | `<ActorName>` XML 片段 | 需要新的解析器；历史铁律"乱改 ATR 名会致指令面板打不开" | 中（等长替换即可，风险在语义） |
| ELF `.rodata` UI 串（载入屏/等待提示等） | `0x577FA0–0x578070` 等 | 在 ELF 里，固定长度；本轮明确不动 ELF | 中（需 ELF 补丁 + `r23_audit_inventory` 缺失 0 条） |
| `.MIS` 任务容器 | GR.IMG 内 16384 B 子流序列 | 未逆向其内部结构 | 高 |
| `.BMZ/.BMB/.MAZ/.MOL/.SHT` 等 | 地图/贴图/网格 | 二进制资源，非文本（扫描器会把它们误判为"含文本"） | 不适用 |
| 影片字幕 / 纹理文字 | `ANI.MPG` 等 | 不在文本容器里 | 不适用 |

> **扫描器的局限（如实说明）**：`scan_text_resources.py` 用"连续可读串"统计，
> 高熵二进制（地图/贴图）解出来的散字仍会造成 1246 个"疑似含文本"容器（见
> `scan_text_resources.txt`）。**它只能当粗筛**，真正的文本清单以 `docs/PATCH_INVENTORY.md`
> 与 `tools/diag/dump_all_text.py` 的四类来源（RES/XML/TXT/ATR）为准。
> 本轮真正可编辑的范围就是上面"已覆盖"的两类。

---

## 7. 迁移路径（把同一套机制推广到其它资源）

1. 在 `tcslib.RES` 里加一个资源定义：容器读取（IMG 条目 / 子流 / 解压）+ 一个解析函数
   （给出 `id`/`offset`/`len`/`payload`）+ 一个"可变长怎么写回"的 `marshal`
   （有没有 4 字节长度前缀、有没有尾部可吸收区）。
2. 在 `dump_text_csv.py` 的 `DUMPERS` 里加一个 dumper：产出同样的列
   （`text_zh`/`text_edited` 预填相同内容、`kind`/`wrap_w`/`max_bytes` 按资源给）。
3. 折行宽度：能实机标定就标定（用 `runcap.py -grdrawwin` 抓 drawlog，
   `RA=21CA00` 的逐行绘制就是真实折行结果），在 `wrap_profiles.json` 里给 `wrap_w`；
   标定不了就留 0（不插软换行，只显示显式标记）。
4. 注入侧**通常不用改**：`inject_text_csv.py` 已经是"按资源定义 + 字节比较"的通用流程，
   只要 `Container.locate/span/marshal` 支持即可。

---

## 8. 已知限制 / 注意事项

1. **语言表折行宽度未标定** ⇒ 该资源默认不插软换行（`wrap_w=0`）；简报页的 `{br}` 生效已实证，
   但"每行多少字"要人工把握（简报框比介绍框宽）。
2. **注入必须从同一基底一次做完**：产物盘条目偏移已变，拿同一份 CSV 再注入会被
   `offset/len_bytes` 校验拒绝（有意的保护）。连续多轮请每轮重新 dump。
3. **`{br}` 在语言表的适用性**：本轮实证了简报组件；但语言表里还有菜单/列表等短条目
   （`kind=short`），那些组件未必走 RSHTML —— 短文本加换行时注入器会警告，请先用 `--only` 小批验证。
4. **按键图标占位（U+E0xx）不可删**：392 条语言表条目含此类字节。
5. **实机时间线的坑（对后续轮次有用）**：本机 `run_opt.py`（`-grscanframes 2000`）下引导比历史
   轮次慢约 3 倍（F9100 还在 Press START 标题屏，历史导航假设 F7050 已进主菜单）；
   `runcap.py` 用 `-grscanframes 4000` 后，`navC2`/`navTACe` 的时间线与历史轮次一致
   （特别收录 F10900、简报页 F9266）。**帧号依赖主机负载，导航不鲁棒时优先怀疑这一项。**
6. 本轮**没有**改 ELF、没有改任何既有脚本、没有移动任何 IMG 条目、没有碰制作组名单。

---

## 9. 复现命令

```powershell
$PY = 'C:\ProgramData\anaconda3\python.exe'
# ① 自检 + dump
& $PY tools/text_csv/dump_text_csv.py --iso work/builds/GR_ZH89/GR_ZH89.iso `
      --out work/text_csv/GR_ZH89_text.csv
# ② 往返零差异
& $PY tools/text_csv/inject_text_csv.py --csv work/text_csv/GR_ZH89_text.csv `
      --src work/builds/GR_ZH89/GR_ZH89.iso --dst work/text_csv/rt/rt_none.iso
# ③ 示例改动 → 产物盘
& $PY work/text_csv/dev/mkedit.py work/text_csv/GR_ZH89_text.csv work/text_csv/GR_ZH90_edit_demo.csv
& $PY tools/text_csv/inject_text_csv.py --csv work/text_csv/GR_ZH90_edit_demo.csv `
      --src work/builds/GR_ZH89/GR_ZH89.iso --dst work/builds/GR_ZH90/GR_ZH90.iso `
      --report work/archive/cmp/r29_csv/inject_report.json
# ④ 实机前后同帧
& $PY tools/text_csv/runcap.py R29SF_AFT  work/builds/GR_ZH90/GR_ZH90.iso work/_dis/navC2.txt   11700 100 10900 11700 4000
& $PY tools/text_csv/runcap.py R29TAC_AFT work/builds/GR_ZH90/GR_ZH90.iso tools/capture/navTACe.txt 12400 100 9000 11400 4000
& $PY work/text_csv/dev/pngdiff.py <改前dump目录> <改后dump目录> 9000 11700 work/archive/cmp/r29_csv/png
```

（`work/text_csv/dev/` 下是本轮的取证/演示脚本，非交付接口，可随时删除。）
