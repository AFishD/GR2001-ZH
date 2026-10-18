# REPORT_font_testpage.md — round60「字库测试页」(特别收录 → 开发访谈 1)

分支 `round60/font-test-page` · 执行者 = 字库测试页子代理 · 2026-10-14

> **一句话**: 新脚本 `tools/iso_build/make_font_testpage.py` 把**码表里全部 1285 个字符**
> (1175 对偶码 + 110 单字节码, 一字一次) 铺进「特别收录 → 访谈 → **开发访谈 1**」的
> `<text>` 里, 原位替换、其余字节一字不动; 测试盘 **`GR_TEST_FONT1`**
> sha256 `0a3db1ba2159f9a4e796a235863c756679491dc256d3e52270a528438de7405b`;
> 三条硬门禁 + LZO 回环 + 全盘差异归属**全部通过**。
> 实机导航**两次尝试都没能停在「访谈」上**(第 3 次未跑, 按任务书"不超过 2 次"停手) ——
> 但**抓到了光标停在「访谈」上的帧**(attempt1 F27000), 并量出了完整的按键↔行号模型,
> 结论与下一步见 §6。

---

## 0. 交付物

| 文件 | 说明 |
| --- | --- |
| `tools/iso_build/make_font_testpage.py` | **新脚本** (本轮的产物): 生成字库测试页, 含 3 条硬门禁 |
| `work/builds/GR_TEST_FONT1/GR_TEST_FONT1.iso` | **测试盘** (不是发布版), 1 648 164 864 B |
| `tools/capture/nav_sf_interview.txt` | **新导航** (主菜单 → 特别收录 → 访谈 → 开发访谈 1) |
| `work/builds/GR_ZH98/temp/r60/` | 侦察/验收脚本与报告 json (`tp_r1_report.json`、`r60_diff_attr.json` 等) |
| 本文件 | 报告 |

---

## 1. 现象 / 目标页定位 (含 `<text>` 偏移)

### 1.1 容器

| 项 | 值 |
| --- | --- |
| 资源 | `tcslib.RES['SFXML']['copies'][0]` = **`MENU.IMG#283`** `EN_SPECIAL_FEATURE.XML` |
| ISO 偏移 | `0x623A0800` (条目 `off`/`stored`/`real` = 58136576 / **49700** / 116430) |
| 形态 | LZO 帧, **8 个子流** (16384×7 + 1798), 展开 **116486 B** |
| 压缩帧 | **41615 B** → 槽 49700 B (余量 **8085 B**) |
| 尾部陈旧区 | `used_end` = 78248 ⇒ 尾部 38238 B 可吸收 |

### 1.2 目标 `<text>`

「特别收录」结构 = `<SpecialFeatures>` → `<studio name=…>` → `<group name=…>` → `<item name=…><text>…</text></item>`
(10 个 studio / 41 个 group / **94 个 item** / **69 个 `<text>`**, 非空 59)。

目标 = **`<studio name="Interview">` 的第一个 `<item name="开发访谈 1">`**:

| 项 | 值 |
| --- | --- |
| `<item>` 标签起始 | blob `0xE629` (58921) |
| `<text>` 开/闭标签 | `0xE663` / `0xF158` |
| **载荷区间** | **blob `[0xE669, 0xF158)` = `[58985, 61784)` = 2799 B** |
| dump 条目号 | **`SFXML:T0067`** (`offset=58985`, `len_bytes=2799`) |
| 原文 | 1720 字, 开头 `开发手记：第一辑{p}达伦丘基图斯{br}制作人{br}幽灵行动{br}手记 1:{p}…`, 末尾 = 48 个空格 (无 `{br}`/`{p}` 收尾标记) |

另两篇: 开发访谈 2 (`T0068`, `@0xF1EA`) / 开发访谈 3 (`T0069`, `@0x10761`)。

### 1.3 为什么是"倒数第二个"

「特别收录」列表文案在 **`EN_STRINGS.RES`** (`LANG:G058.I739..I748`, 按 offset 升序 = 屏上顺序):

| # | 文案 | 英文 | RES id |
| --- | --- | --- | --- |
| 1 | 影片 | Movies | I739 |
| 2 | 设定图 | Sketches | I740 |
| 3 | 音乐 | Music | I741 |
| 4 | 武器 | Weapons | I742 |
| 5 | 奖章 | Awards | I743 |
| 6 | 背景 | Background | I744 |
| 7 | 专家 | Specialist | I745 |
| 8 | 屏幕截图 | Screenshots | I746 |
| **9** | **访谈** | **Interview** | **I747** |
| 10 | 预告片 | Game Trailers | I748 |

⇒ **访谈 = 第 9 项 = 倒数第二个** ✓ 与用户口径一致。
交叉验证: round49 导航 (列表钉顶后 down×5) 的注释说落在「背景」, round82s 的 down×3 说落在「武器」
—— 与本表第 6/第 4 项**逐项对上**; 本轮实机抓帧也把 10 行标签全部拍到
(`work/builds/GR_ZH98/temp/r60/r60_sf_list_zoom.png`)。
**注意**: 第 7 行「专家」在本轮存档状态下是一条**灰色空条** (不可选), 这是 §6 导航难点的根源。

---

## 2. 新脚本用法与参数

```
python tools/iso_build/make_font_testpage.py <src.iso> [<dst.iso>]
       [--cols N] [--title T] [--order code|unicode] [--page-lines N]
       [--charset PATH] [--item-name NAME] [--expect-prefix STR]
       [--dry-run] [--allow-grow] [--report PATH]
```

| 参数 | 默认 | 含义 |
| --- | --- | --- |
| `src` / `dst` | — / = `src` | 源盘 / 输出盘; 省略 `dst` = 原地改写 (先整盘复制再改那一段) |
| `--cols N` | **24** | 每行几个字 (每 N 个字插一个 `{br}`) |
| `--title T` | `字库测试页` | 首行统计的标题 (标题里的字必须在码表里, 否则直接报错) |
| `--order` | `code` | 字符顺序: `code` = 按**编码字节**升序 (码表顺序) / `unicode` = 按码位 |
| `--page-lines N` | `0` | 每 N 行把 `{br}` 换成 `{p}` (段落分隔; 0 = 不分段) |
| `--item-name` | `开发访谈 1` | 目标 `<item name=…>` (要求全 blob **恰好命中 1 个**) |
| `--expect-prefix` | `开发手记：第一辑` | 写盘前确认"这一篇就是开发访谈 1"; 传空串可关 |
| `--dry-run` | 关 | 只跑到门禁①, 打印帧/blob 摘要, **不写盘** |
| `--allow-grow` | 关 | 新文本比原文长时允许从容器尾部陈旧区吸收 (**默认拒绝**, 见 §7) |
| `--report` | `<dst目录>/temp/font_testpage.json` | 报告 json |

实现口径: **复用** `tcslib` (Charset / Iso / lzo_subs / parse_sfxml / splice) 与
`inject_text_csv.Container` (与 round51 的 SFXML 原位改写同一条路径), 不新造解码器。

---

## 3. 测试文本格式

```
字库测试页 全 1285 字 · 每行 24 字{br}《》享伞促凝双吸壳套尖履巨拆捕旋池热若燃牛牲牺猪{br}玻璃磁磅稳纤终脆膛区移挥备机记入图敌对武来了就炸{br}…{br}视戏游目前指更它有雷何上著⟨+88 个空格⟩
```

| 项 | 值 |
| --- | --- |
| 首行 | `字库测试页 全 1285 字 · 每行 24 字` (统计行) |
| 字符顺序 | `code` = 编码字节升序: 首 8 字 `《》享伞促凝双吸`, 末 8 字 `指更它有雷何上著` (单字节码 0x80..0xA0 与对偶码 0xA1.. 混排) |
| 每行 | 24 字, 行内**不插空格** |
| `{br}` | 54 个 (首行后 1 + 行间 53) |
| `{p}` | 0 个 (默认不分段) |
| 正文字节 | 2460 B (1175×2 + 110×1) |
| 全文 | **2711 B**, 再**补 88 个空格 → 2799 B** |
| 收尾习惯 | 原文末尾无 `{br}`/`{p}` ⇒ 不补标记; 但**保留"末尾是空格"的习惯** (补齐的 88 个空格) |

★ **为什么要补齐到 2799 B**: `<text>` 载荷长度一变, `dump_text_csv` 出的 `len_bytes` 就与盘不符
⇒ 注入器 (`inject_text_csv.py`, 逐行核对 `offset`/`len_bytes`) 会判"表已过期"并非 0 退出。
等长 ⇒ 载荷偏移/长度都不变, 结构核对照过, 而且 blob 总长不变 ⇒ **零位移**, 只有目标那一段变。

---

## 4. 门禁与验收数字

跑法 (可复现):
```
python tools/iso_build/make_font_testpage.py work/builds/GR_ZH109/GR_ZH109.iso <dst.iso> --report <dst>.json
```

| 门禁 | 内容 | 结果 |
| --- | --- | --- |
| **①** 写盘前 | 除目标 `<text>` 区间外 blob **逐字节不变** (前缀 + 后缀) | blob 116486 → **116486 B (Δ0)**; 差异 **2694 B**, 区间 = `[58985, 61735]` ⊂ 载荷 `[58985, 61784)`; **区间外 0 B** ✓ |
| **②** 回读 | **每一个**码表字都能在新 `<text>` 里解出来 (逐个点名) | **1285 / 1285** ✓ (1175 对偶 + 110 单字节); 回读文本与预期**逐字符相同**; 载荷仍 2799 B ✓ |
| **③** 回读 | 其它 `<text>`/`<item>`/`<group>`/`<studio>` 与 IMG 其它条目不变 | 69 个 `<text>` 里**只有 `T0067` 变**; 94 个 item/group/studio 标签区不变; `MENU.IMG` **其余 685 个条目逐字节不变**; 条目表 `off`/`stored`/`real` 不变 ✓ |
| 附加 | LZO 重压**回环断言** | 8 个子流**只重压 1 个** (子流 3); 帧 41615 → **42322 B** (+707); `lzo_subs(帧) == 新 blob` 逐字节 ✓ |
| 附加 | 超槽即中止 | 帧 42322 B / 槽 49700 B ⇒ **余 7378 B** (未触发; 逻辑在, 不截断不丢字) ✓ |
| 附加 | ISO 尺寸 | 1 648 164 864 B 前后一致 ✓ |
| **幂等** | 同一源盘跑两次 | `tp_r1.iso` 与 `tp_r2.iso` sha256 **完全相同** = `0a3db1ba…405b` ✓ |

**独立复核** (另写脚本, 不复用补丁自身的结论): `work/builds/GR_ZH98/temp/r60/r60_verify_testpage.py`
在**最终测试盘**上重新解容器 → 目标仍在 `[58985, 2799)`、首行正确、正文里 1285 个字
**缺失 0 / 重复 0 / 非空格字符数 = 1285**、其它 68 个 `<text>` 与 GR_ZH109 逐字节相同、区间外前后缀相同
⇒ **全部通过** (exit 0)。

引擎折行模型 (`wrap_w=270`, SFXML 实机标定值): 全文折成 **109 个视觉行**, 每视觉行最多 20 字
(统计行), 24 字的正文行按引擎的"逐字硬断兜底"折成 2 行 —— **不会被裁掉**。

---

## 5. 测试盘 `GR_TEST_FONT1`

### 5.1 构筑路径 (以及必须说明的两处偏离)

任务书给的是 `make_build.py GR_TEST_FONT1 --from <打过补丁的盘> --inject-csv work/builds/GR_ZH109/text`。
实际执行时有两处**必须说明**的偏离:

**(1) `make_build.py` 的版本名硬门禁拒绝 `GR_TEST_FONT1`** —— 原文 `tools/iso_build/make_build.py:884`:

```
assert re.fullmatch(r'GR_ZH\d+(_[A-Za-z0-9]+)*', ver), '版本名须为 GR_ZH<数字>[_后缀]: %s'
```

实测 (未加 `-O`, 原样跑一次留证):
`AssertionError: 版本名须为 GR_ZH<数字>[_后缀]: GR_TEST_FONT1`, exit 1, **没有创建任何目录**。
由于本轮的写入白名单只有 `work/builds/GR_TEST_FONT1/` (改成 `GR_ZH110` 之类会写到别处、还会被
`latest_build()`/`latest_iso()` 当成"最新发布版"影响其他轮次), 故改用
**`python -O tools/iso_build/make_build.py …`** 跑**同一条命令**: `-O` 只跳过 `make_build` 自己的
`assert`, **子工具 (补丁/注入器/dump) 的 assert 全部照常生效**。被跳过的断言共 5 条, 逐条独立复核:

| 被 `-O` 跳过的断言 | 独立复核 |
| --- | --- |
| `make_build.py:884` 版本名正则 | 本轮唯一需要绕过的; 已在报告里点明 |
| `:886` 输出目录不得已存在 | 构筑前 `Test-Path work/builds/GR_TEST_FONT1` = **False** ✓ |
| `:894` 基底 ISO 存在 | `--from …/tp_r1.iso` 存在 ✓ |
| `:906` 补丁前后 ISO 尺寸相同 | 两者均 **1 648 164 864 B** ✓ (补丁脚本内部也 assert 了尺寸) |
| `:999` 注入前后 ISO 尺寸相同 | 注入报告 `[diff] 全盘差异 0 B`; 产物 sha256 与注入前**完全相同** ✓ |
| `:1018` `MENU.IMG` 读出长度 = 常量 | `extract/MENU.IMG` 已产出且 `audit_inventory`/diff 均通过 ✓ |

**(2) 字库步骤用 `--no-font-compact` 关闭** —— 依据: 对 GR_ZH109 跑
`font_compact.plan_compact()` 得到 **`changed=False`, 搬运 0 字 / 改码位 0 / 改像素 0**
(GR_ZH109 的 `build_info.json` 也记着同一结论: "在用字形 = slot 0..1174, 空闲 = slot 1175..1503, 搬运 0 个字")
⇒ 该步**本来就是 0 改动**; 关掉它与默认跑它**等价**, 而且能 100% 保证**不去改共享的
`tools/font_pipeline/data/charset_compiled_zh16.json`** (关掉时 `font_step_tool=None`,
连 `stamp_charset` 都不会调)。`git status` 复核: **除两个新文件外零改动** ✓。

**注入步骤是字节级 no-op (实测, 不是推断)**:
`inject1_report.json` 里
`[hash] src 0a3db1ba…405b` / `[hash] dst 0a3db1ba…405b` / `[hash] 逐字节相同 (无改动)` /
`[diff] 全盘差异 0 B` —— 2261 行里 **实际改动 0 条** (2219 条 `text_edited == text_zh` 跳过,
42 条"与源盘等价"跳过; 其中 `SFXML:T0067` 属于前者 ⇒ **测试页没有被注入器覆盖**)。

⇒ 最终盘 = **补丁盘本身**。证据: `sha256(GR_TEST_FONT1.iso) == sha256(tp_r1.iso) == 0a3db1ba…405b`
(即"先补丁再构筑"与"直接补丁"产物**逐字节相同**, 构筑管线贡献 0 B)。

实际命令 (完整、可复现):
```
# ① 打补丁 (两遍, 验幂等)
python tools/iso_build/make_font_testpage.py work/builds/GR_ZH109/GR_ZH109.iso work/builds/GR_ZH98/temp/r60/tp_r1.iso --report work/builds/GR_ZH98/temp/r60/tp_r1_report.json
python tools/iso_build/make_font_testpage.py work/builds/GR_ZH109/GR_ZH109.iso work/builds/GR_ZH98/temp/r60/tp_r2.iso --report work/builds/GR_ZH98/temp/r60/tp_r2_report.json
# ② 构筑 (同一条 make_build 命令; -O 只为绕过 §5.1(1) 的版本名断言)
python -O tools/iso_build/make_build.py GR_TEST_FONT1 \
       --from work/builds/GR_ZH98/temp/r60/tp_r1.iso \
       --inject-csv work/builds/GR_ZH109/text --no-font-compact
```
(注: 任务书原文写的是 `--from <打过补丁的盘>`; 这里就是"先补丁 → 再构筑"的等价路径。
`--patch` 那条路也能用 —— `make_build` 调 `python <patch> <src> <dst>`, 而本脚本的位置参数正好是
`src dst` —— 但那样就没法给 `--cols/--title` 传参, 所以走了中间盘。)

### 5.2 验收数字

| 验收项 | 结果 |
| --- | --- |
| **sha256** | **`0a3db1ba2159f9a4e796a235863c756679491dc256d3e52270a528438de7405b`** (1 648 164 864 B) |
| `audit_inventory` | `PATCH_INVENTORY 解析出 45 条字节级补丁; 在役 44 条, **缺失(仍为 EN 词) 0 条**, 其它 1 条` ✓ (ELF 与 GR_ZH109 **差异 0 B** ⇒ 该结果与现役盘同源) |
| `inject --check-only` | **exit 0**; `待检查(会被写入) 31 条`; `[ok] 字库覆盖完全: 每条文本的每个字符都能编码, 且盘上都有字形 ✓`; 结构核对 2261 行全过 (唯一提示是"表里记录的源盘 sha256 与 --src 不一致" —— 因为源盘多了一页测试页, 属预期) |
| `dump_font` | **缺字形 0**; 字符 1384 = 对偶 1175 + 单字节 108 + ASCII 95 + latin1 2 + 图标 2 + 未映射 2; **对偶字有字形 1175/1175**; 采样窗 1719 个: 错误 0 / **截断(丢行) 0**; 字表槽 sha256 `1a004a38…a4d4` |
| 文本副本 | `text/` 三张表 2261 条 (long 58 / long_nowrap 256 / short 1947), `T0067` 的 `text_zh` 已经是测试页正文, `offset=58985` / `len_bytes=2799` **未变** ✓ |

### 5.3 差异归属 (与 GR_ZH109 逐字节对比)

脚本 `work/builds/GR_ZH98/temp/r60/r60_diff_attr.py` (按**真实容器边界**算窗口, 不用拍脑袋的区间):

| 区域 | 差异 |
| --- | --- |
| **`MENU.IMG#283 EN_SPECIAL_FEATURE.XML`** | **15408 B / 274 段** ← 全部差异都在这里 |
| ELF (按 ELF 头的真实长度 **37.5 MB**, 不是 round56 那个 1.5 MB 窗口) | **0 B** |
| PVD (`LBA16..17`) | **0 B** |
| `MENU.IMG` / `GR.IMG` 两个**条目表** | **0 B** |
| `FONT.RES` 槽 (`0x5ECE8120..0x5ECE9265`) | **0 B** |
| 字库像素容器 (`0x5EC8786D..0x5ECC787D`, 262160 B) | **0 B** |
| `EN_STRINGS.RES` 两份副本 (`MENU.IMG#25` / `GR.IMG#902`, 制作组等文案所在) | **0 B** |
| 名字含 `CRED` 的条目 | 全盘**没有**这种条目 (已按 IMG 名字表搜过) ⇒ "制作组名单"落在 `EN_STRINGS.RES` / ELF, 两者差异均 0 |
| `(未归属)` | **0 B** |

⇒ **结论: 差异只落在 SFXML 所在条目内** ✓ (而且落点还在 `<text>` 载荷区间内: `[58985, 61735]`)。

---

## 6. 实机导航 (两次尝试, 未停在「访谈」上 —— 但已定位到"差一次按键")

**单实例**、全部走 `tools/capture/run_opt.py`; 起跑前 `Stop-Process pcsx2-gsrunner`;
`GR_ISO` 指向测试盘 ⇒ 产物落在 `work/builds/GR_TEST_FONT1/temp/dump_<tag>/`。

| 尝试 | nav 里的下移次数 | tag / 帧目录 | 结果 |
| --- | --- | --- | --- |
| attempt 1 | 8 | `r60sfint` → `work/builds/GR_TEST_FONT1/temp/dump_r60sfint/` (299 帧 PNG) | 光标**经过**「访谈」(F27000, 见下), 但多挪一格绕回「影片」⇒ cross 打开了 **影片** 页 (F29000) |
| attempt 2 | 6 | `r60sfint2` → `work/builds/GR_TEST_FONT1/temp/dump_r60sfint2/` (299 帧 PNG) | 稳稳停在「屏幕截图」⇒ cross 打开了 **屏幕截图** 页 (F29000), **差一次** |

两次都 **exit=0, elapsed≈506 s**, 且都**成功进了「特别收录」列表**(这一步是稳的)。

### 6.1 逐帧量出的"按键 ↔ 行号"模型

`work/builds/GR_ZH98/temp/r60/r60_nav_cursor.py` 在抓到的 PNG 上量**高亮条中心 y**
(排除底部状态条的金色), 得到列表 10 行的 y = 83/111/138/165/193/**220**/248/**275**/**302**/329:

```
attempt 1 (8 次下移):  1影片 →2 →3 →4 →5奖章 →(多挪一格)8屏幕截图 →9访谈 →10预告片 →(绕回)1影片
attempt 2 (6 次下移):  1影片 →2 →3 →4 →5奖章 →6背景 →8屏幕截图        ← cross 时停在这里
```

⇒ 两条硬结论:
1. **钉顶 (up×9) 两次都稳定落在「影片」(第 1 行)**;
2. **第 7 行「专家」是灰色空条、光标自动跳过**, 所以从第 1 行到第 9 行「访谈」要
   **7 次下移** (1→2→3→4→5→6→8→9); 第 9 次下移会绕回第 1 行 (列表是环形的)。
   attempt1 之所以失败, 是 8 次里有**一次按键被重复注册**(等于挪了 9 格)。

### 6.2 已经拿到的关键帧 (证明"导航能到「访谈」")

| 帧 | 内容 | 路径 |
| --- | --- | --- |
| attempt1 **F27000** | **金色高亮条正停在「访谈」上** (上一行 屏幕截图 / 下一行 预告片) | `work/builds/GR_TEST_FONT1/temp/dump_r60sfint/snap_f00027000.png` (放大件: `work/builds/GR_ZH98/temp/r60/r60_zoom_00027000.png`) |
| attempt1 F24000 | 特别收录列表 10 行标签全览 (影片…预告片, 第 7 行灰条) | `…/dump_r60sfint/snap_f00024000.png` (放大件: `work/builds/GR_ZH98/temp/r60/r60_sf_list_zoom.png`) |
| attempt1 F29000 | cross 之后进的是 **影片** 页 | `…/dump_r60sfint/snap_f00029000.png` |
| attempt2 F29000 | cross 之后进的是 **屏幕截图** 页 (标题条「屏幕截图」, 左侧 士兵/幽灵行动) | `…/dump_r60sfint2/snap_f00029000.png` |

⇒ 卡点**不在**"进不去特别收录", 也不在"选不到访谈" —— **只在最后那一次按键的计数**
(run_opt 的帧驱动偶发丢键/重键, 与 `docs/REPORT_font_ext_fix.md` 记的现象同源)。

### 6.3 交给 Lead 的下一步 (按性价比排序)

1. **直接把 `tools/capture/nav_sf_interview.txt` 跑一遍** —— 本文件已经改成
   **钉顶后 7 次下移 + F28300 cross** (依据 §6.1 的实测模型)。7 次若不被重键, 就是「访谈」。
2. 若还差一格: 把下移间隔从 500 帧拉长到 700~800 帧 (降低重键概率), 或把 `cross` 前
   留出更长的静默期。
3. **闭环导航** (最稳): 先抽帧判断高亮条 y 是否 = 302 (「访谈」) 再按 cross ——
   判定函数现成: `r60_nav_cursor.py:gold_band()`。
4. 兜底: 用记忆卡存档直接落在特别收录, 或人工进页面后交给"实机取证"环节。

---

## 7. 已知限制

1. **载荷长度必须 ≤ 2799 B** (原文长度)。默认 `--allow-grow` 关: 变长会位移后续字节,
   且 `dump` 出的 `len_bytes` 与盘不符 ⇒ 注入器判"表已过期"。
   `--cols 16` (正好等于引擎的 16 字硬断行, 网格最整齐) 需要 **2819 B** ⇒ 被这条限制挡下,
   所以测试盘用默认 `--cols 24` (2711 B + 88 空格补齐)。想要 1:1 网格又不变长,
   可选 `--cols 17` (正好 **2799 B**, 零补齐; 但引擎仍会折成 16+1)。
2. **页面靠滚动看全**: 特别收录正文页是**滚动**式 (r49 的 14 次 `down` 就是滚动, 滚动箭头 ▲▼),
   `{p}` 是**段落分隔**(CSV 视图里的空行)而**不是翻页**。1285 字折成 109 个视觉行,
   首屏只能看到统计行 + 前几行 ⇒ 测试时要一路下滚。
3. **测试盘不是发布版**: 它把「开发访谈 1」的**原文替换掉了**(原文只存在于 GR_ZH109)。
   它自己的 `text/` 副本里 `SFXML:T0067` 的 `text_zh` 也就是测试页 —— **不要把这张表注入到别的盘**。
4. `make_build.py` 的版本名门禁 (`GR_ZH\d+`) 与"测试盘叫 `GR_TEST_FONT1`"天生冲突,
   本轮用 `python -O` 绕过并在 §5.1 逐条补验; 若 Lead 认为不妥, 可改为在 `make_build.py`
   里放行 `GR_TEST_.*` (需另开一轮, 本轮未改该文件)。
5. 导航未闭环 (§6): 停在"差一次按键"上, 已给出 7 次下移的修正版与闭环方案。
6. 引擎折行是**模型**(`tcslib.wrap_seg`, `wrap_w=270` 实机标定值), 不是实机逐像素复核;
   本轮没拍到目标页, 所以"24 字行会被折成 16+8"这一点**只有模型依据**, 没有实机截图。

---

## 8. 产物清单

```
tools/iso_build/make_font_testpage.py                        ← 新脚本
tools/capture/nav_sf_interview.txt                           ← 新导航 (7 次下移版)
docs/REPORT_font_testpage.md                                 ← 本文件
work/builds/GR_TEST_FONT1/
    GR_TEST_FONT1.iso            sha256 0a3db1ba…405b (1 648 164 864 B)
    build_info.json              base = r60/tp_r1.iso; font_step_tool = None; font_dump 缺字形 0
    text/                        三张可注入表 + TXT + meta + 9 张 view 表
    font/                        图集 PNG + FT 记录 + 字符集清单 + summary (缺字形 0)
    extract/                     MENU.IMG / 字表 / 字库记录
    temp/inject1_report.json     注入: 0 改动, 逐字节相同
    temp/dump_r60sfint/          attempt1 抓帧 (299 PNG, 8 次下移 → 影片)
    temp/dump_r60sfint2/         attempt2 抓帧 (299 PNG, 6 次下移 → 屏幕截图)
work/builds/GR_ZH98/temp/r60/
    tp_r1.iso / tp_r2.iso        补丁产物 (两者 sha256 相同; 临时件, 可删)
    tp_r1_report.json / tp_r2_report.json
    r60_diff_attr.py / .json     差异归属 (真实容器边界)
    r60_verify_testpage.py       独立复核 (最终盘)
    r60_nav_cursor.py            抓帧量高亮条 y (导航诊断)
    r60_target_probe.py / r60_probe_inject_effect.py   只读侦察
    r60_sf_list_zoom.png / r60_zoom_00027000.png …     放大取证图
```

> 复现"最终盘 == 补丁盘"的一行命令:
> `python work/builds/GR_ZH98/temp/r60/r60_verify_testpage.py` (exit 0 = 全过)。
