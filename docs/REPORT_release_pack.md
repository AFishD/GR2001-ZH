# REPORT_release_pack.md — round43：`ç`/`ñ` 修正 + 首份「资料包」（`work/builds/GR_ZH93/release/`）

> **对象盘（全程只读）**：`work/builds/GR_ZH93/GR_ZH93.iso`
> sha256 = `e037f6292940811144e2d0d629ec4c4f3e2cfc306d099a4c96b44f6ee08d19be`（1,648,164,864 B）
> **本轮未改任何 ISO**；**未执行任何 git 操作**（铁律：git 由 Lead 负责，分支 `round43/latin-fix-and-release`）。
> 测试产物 / 验证脚本 / 日志：`work/builds/GR_ZH93/temp/r43/`（`v0`…`v12`）。
> 资料包：`work/builds/GR_ZH93/release/`（24 文件 / 22.80 MB，含 `MANIFEST.json`）。

---

## 〇、给用户的一句话

**`Français` / `Español` 现在在表里就是两个正常字母了**（不再是 `{{BTN:E0E7}}` 那种误导写法）；
你手上**旧的写法照样能注入**，两种写法写出来的盘**一模一样**。
资料包在 `work/builds/GR_ZH93/release/`：**3 张表能改、10 张只能看**，
字库**还能直接加 45 个新字**（单字节码已经一个都加不了）。

---

## 一、修了什么（`ç` / `ñ`）

### 1.1 问题

round42 已定性：`0xE7` = 拉丁小写 **`ç`**、`0xF1` = **`ñ`**（**不是**手柄图标；
FT 记录 idx=199 / 209 在图集上确有字形；实机画的就是这两个字母）。
但这两个字节**不在字符集里** ⇒ `decode()` 把未映射字节回落成私有区 `U+E0E7`
⇒ 文本表里写成 `Fran{{BTN:E0E7}}ais`：**功能正确，标签误导**（用户看不出那是字母 ç）。

### 1.2 改法（只打补丁；**盘上字节一个都没变**）

| 文件 | 改动 | 行数 |
|---|---|---|
| `tools/font_pipeline/data/charset_compiled_zh16.json` | `codes` **只加两条**：`"ç": 231` / `"ñ": 241`（**其余一个字符都没动** —— 编辑是"在 `"著": 255` 后插入两行"的字面替换） | +2 行 |
| `tools/text_csv/tcslib.py` | 新增 `BTN_LATIN1_ALIAS=(0xE7,0xF1)` / `LATIN1_ALIAS_CHARS` / `Charset.normalize_latin1_alias()`；`btn_code_ok()` 对这两个字节**放行**（历史别名）；`encode_strict()` 先归一化再做 encode/decode 对称自检；订正 3 处过时注释 | ~30 行 |
| `tools/text_csv/icon_table.py` | `NOT_ICON_CODES` 标 `in_charset=True / kind='latin1'`；`describe()`/`summary_lines()` 措辞订正；自检新增 **9 条**（含 `is_icon(0xE7/0xF1) is False` 三种写法的硬断言 + 与 charset 交叉验证） | ~25 行 |
| `tools/iso_build/dump_font.py` | `charset_rows()` 里这两行归 `kind='latin1'`（原来落在 `icon` 段）；`capacity_report()` 增加 `used_hanzi` / `used_latin1` / `latin1_bytes` 拆分 | ~25 行 |

**为什么不需要整体重编码**：字节值不变（`ç` 仍写 `0xE7`、`ñ` 仍写 `0xF1`），
改动只发生在"字节 ↔ 字符"的**视图层**。这一点由下面的往返验证**证明**，不是推断。

### 1.3 向后兼容（硬要求）的三处实现

1. `btn_code_ok()`：`0xE7/0xF1` 显式放行 ⇒ 老 CSV 的 `{{BTN:E0E7}}`/`{{BTN:E0F1}}` 仍被接受；
2. `encode()` 的占位分支**未改** ⇒ `U+E0E7` 照旧写成 `0xE7`（老 CSV 一个字都不用改）；
3. `normalize_latin1_alias()`：编码前把 `U+E0E7/U+E0F1` 归一化成 `ç/ñ`，
   让 `encode_strict()` 的**对称自检**对老写法同样成立（否则合法的老 CSV 会被判成死）。

---

## 二、验收（逐条实跑，日志路径可直接打开）

| # | 验收项 | 结果 | 证据 |
|---|---|---|---|
| ① | 重新 dump ⇒ `LANG:G059.I028` 正文 = **`Français`**（不再是 `{{BTN:E0E7}}`） | ✓ `text_zh`/`text_edited` 都是 `Français`；`I031` = `Español`；三张表里 `BTN:E0E7/E0F1` **0 处** | `v1_dump_zh93.log`、`v1b_check_fr.py` |
| ② | **往返零差异**：新表原样注入 `GR_ZH93.iso` | ✓ exit 0；`[hash] src == dst == e037f629…8d19be`；`[diff] 全盘差异 0 B`；2261 行往返自检全过 | `v2_inject_new.log` |
| ③ | **旧写法** `{{BTN:E0E7}}` 注入 ⇒ 同 sha | ✓ 两种旧表（只改 `text_edited` / 两列都旧写法）都 exit 0，sha **同 `e037f629…`**；且该行**确实进了写入集**（`待检查(会被写入) 33 条`），编码出的字节与盘上一致 ⇒ 0 差异 | `v4_inject_legacy_edit.log`、`v4_inject_old_full.log` |
| ④ | **两种写法等价**（决定性证据） | ✓ 真改一格（`Français!` vs `Fran{{BTN:E0E7}}ais!`）⇒ 两路产物 sha256 **都是 `98d333f7d9e56c95bd89c1d723a4537285571e46130283a6c69407f3ead3fef9`**；两盘上该条目字节都是 `46 72 61 6e e7 61 69 73 21`（`Fran\xE7ais!`） | `v4_inject_probe_new.log`、`v4_inject_probe_old.log`、`v5_bytes_proof.log` |
| ⑤ | `--check-only` | ✓ **exit 0**，`[ok] 字库覆盖完全`，未写盘 | `v8_checkonly.log` |
| ⑥ | `dump_font.py` ⇒ kind 统计 | ✓ `ascii 95 / single 108 / latin1 2 / pair 1319 / icon 2`（**latin1 仍 2、icon 仍 2**）；引擎格自查 1504/1504 一致、对偶字有字形 1319/1319 | `v6_dumpfont_2x.log`、`v6b_dumpfont_1x.log` |
| ⑦ | `icon_table.py` 自检 | ✓ exit 0、日志里 **0 处 `[!!]`** | `v7_icon_selfcheck.log` |
| ⑧ | 从**资料包**直接注入 | ✓ `--csv work/builds/GR_ZH93/release/text` ⇒ exit 0、sha 同 `e037f629…`（meta 也被正确读到：`text-csv/4 / 源盘 sha256 e037f629…`） | `v12_inject_from_release.log` |
| ⑨ | view-only 表拒注入（资料包内的拷贝） | ✓ 显式喂 ⇒ **exit 1、产物不存在**；**改名**去掉 `_view_` 后 ⇒ 仍 **exit 1**（防线②：`2008 行自述 injectable = no`）；给整个目录 ⇒ exit 0 且只读 3 张表 | `v11_view_reject1.log`、`v11_view_reject2.log`、`v11_view_dircheck.log` |
| ⑩ | `字库报告.xlsx` 读回复核 | ✓ 6 页、每页行数正常；**11 个关键数字与 `dump_font` 的 `summary.json` 逐个相等**；空位清单 45 行且 slot 序列逐个相同；office 结构检查 `verdict=pass`、`formulas=0` | `v10_verify_xlsx.log`、`v10b_office_checks.json` |

**④ 为什么是决定性的**：如果只比"原样注入"，两种写法都会因为"编码出的字节与盘上相同"而被跳过
（sha 相同是平凡的）。所以第 ④ 项**故意改一个字**（`!`）逼它真写盘：
两路各自写出 `Français!` / `Fran{{BTN:E0E7}}ais!`，**产物 sha256 完全相同** ⇒
"标记"确实被还原成同一个字节，而不是被当成普通文本写进去。

---

## 三、资料包内容（`work/builds/GR_ZH93/release/`，24 文件 / 22.80 MB）

```
release/
├─ README.md                     8,352 B   人话总索引 + 现役盘信息 + 模拟器跑法
├─ MANIFEST.json                12,773 B   每个文件的字节数 + sha256（含人工维护的 README）
├─ 字库报告.xlsx                17,646 B   6 页：索引/概要/字符分类/空位清单/手柄图标码/口径与限制
├─ 字库报告.md                   7,250 B   同一份报告的 Markdown 版
├─ text/  (16 文件)
│   ├─ README_文本表.md          9,824 B   ★★ 哪张能改 / 怎么改 / 怎么注入（人话）
│   ├─ GR_ZH93_text_long.csv          326,699 B   ★ 可注入（58 行；可写 {WRAP}）
│   ├─ GR_ZH93_text_long_nowrap.csv   289,923 B   ★ 可注入（256 行）
│   ├─ GR_ZH93_text_short.csv         337,397 B   ★ 可注入（1947 行）
│   ├─ GR_ZH93_text.meta.json          15,303 B   多表元信息（注入器靠它对源盘 sha）
│   ├─ GR_ZH92_view_containers_summary.csv   2,206 B   ⚠ 只能看（目录页，11 行）
│   ├─ GR_ZH92_view_binary_assets.csv   11,572,103 B   ⚠ 只能看（30000 行）
│   ├─ GR_ZH92_view_other_res.csv        5,226,896 B   ⚠（14273 行）
│   ├─ GR_ZH92_view_character_names.csv  1,621,310 B   ⚠（4439 行）
│   ├─ GR_ZH92_view_txt.csv              1,142,750 B   ⚠（3254 行）
│   ├─ GR_ZH92_view_program_strings.csv    878,537 B   ⚠（2000 行）
│   ├─ GR_ZH92_view_missions.csv           701,383 B   ⚠（2008 行）
│   ├─ GR_ZH92_view_iso_files.csv          576,838 B   ⚠（1624 行）
│   ├─ GR_ZH92_view_pending.csv            534,654 B   ⚠（2465 行）
│   ├─ GR_ZH92_view_xml.csv                229,736 B   ⚠（516 行）
│   └─ GR_ZH92_view_containers.meta.json    12,177 B   ⚠ view 表来源盘/阈值
└─ font/  (4 文件)
    ├─ GR_ZH93_font_charset.csv       268,406 B   字符集清单
    ├─ GR_ZH93_font_atlas.png          49,460 B   2048×1024（2 倍最近邻；黑=墨/白=空）
    ├─ GR_ZH93_font_atlas_1x.png       36,565 B   1024×512（1:1）
    └─ GR_ZH93_font_ft.csv             25,869 B   FT 记录表（3 个 face）
```

* 产出工具：**`tools/maint/make_release_pack.py`（本轮新增）**
  —— 自己重跑 `dump_font`（2× 进 `font/`、1× 进 `temp/release_pack/font1x/`），
  拷表、现算数字、写 `字库报告.xlsx`/`.md`、写 `MANIFEST.json`；**一行都不写盘内数据**。
* **view 表保留原名 `GR_ZH92_view_*`（不冒名）**：它们是在 GR_ZH92 上做的全容器普查
  （meta 里写着来源盘 sha256 `1d30c106…`）；GR_ZH93 与它只差注入的译文，容器清单相同。
* 资料包里的 view 表**保留 `injectable=no` 列**，且命名带 `view` ⇒ 两道防线都还在（验收⑨）。

### 3.1 字库报告：数字**全部现算**（与 `dump_font` 同源）

| 项 | 值 | 备注 |
|---|---|---|
| 汉字（对偶码）总容量 | **1504** | (lead 上界 0xB1 − 下界 0xA1) × 94 |
| 已用 / 空 | **1319 / 185** | 对偶格占用 **87.70%** |
| ★ 现在就能直接加 | **45** | 空位里"引擎格一个墨点都没有"（row 23 有 36 个、row 24 有 9 个） |
| 需回收 | **140** | 格子上还压着旧字形 |
| 最严格口径 | 41 | 连别人的采样窗都不碰 |
| 单字节码 已用 | **110** | = 汉字 **108** + 拉丁字母 **ç/ñ 2**（round43 新增；round43 前是 108） |
| 单字节码 真正可用 | **0** | 只剩 `B1 B5`，两个都是图标码 |
| 字符总数 | charset **1429** / dump **1526** | 1429 = 110 + 1319（round43 前是 1427）；1526 不变 |
| 图集占用 | **20.29%** | 墨 106392 / 524288 texel |

> ⚠ 与用户给的参考数字的两处**有意差异**（都是"现算"的必然结果，已在报告与文档里写明）：
> 单字节已用 **108 → 110**、charset 字符总数 **1427 → 1429**（各 +2 = ç/ñ）。
> 报告里把 110 拆成「汉字 108 + 拉丁字母 2」，两个口径都看得到。

---

## 四、资料更新（阶段三）

| 文档 | 改了什么 |
|---|---|
| `README.md` | 现役盘块重写：指向 `GR_ZH93` + sha256 `e037f629…` + 资料包位置 + 资料包产出工具；铁律加第 6 条「产物限制在版本文件夹内」；关键文档入口加资料包一行 |
| `docs/PROGRESS.md` | **新增 §73**：round37–43 全纪要（拆表 / 用量回收 / 全容器 dump / 方案 C 扩容 / 格位公式订正 / 图标码定案 / ç/ñ 修正 + 资料包），含 9 条验收与 5 条已知限制 |
| `docs/FONT_CURRENT_STATE.md` | 顶部加 round43 补注；§6.2 数字更新（单字节 108→**110**、charset 1427→**1429**、剩余字节 `B1 B5`、kind 明细）；**新增 §6.3**「ç/ñ 与图标码只有 2 个」（含两种写法等价的实测 sha） |
| `docs/BUILD_TOOLCHAIN.md` | round42 节的"候选 4 个字节"加订正行；**新增「round43 追加」一节**：工具链改动表 + **`release/` 目录约定** + 生成命令 + 9 条验收 |
| `tools/text_csv/FORMAT.md` | 标题补 round43；§0 加资料包落点；§5.1 图标码改成"只有 2 个"（△/✕）并指向 `icon_table.py`；§5.5 加 round43 复测（140 处标记、只剩 2 种）；**新增 §5.6**「ç/ñ 现在直接写字母，`{{BTN:E0E7}}` 是历史别名」 |
| `docs/BUILD_VERSIONS.md` | 顶部插入 `GR_ZH93` 块（sha / 方案 C / 资料包 / 字库数字 / **下一个版本号从 `GR_ZH94` 起**） |

**未改**（铁律）：`docs/REPORT_*.md`（历史定稿）、`tools/font_pipeline/font_usage.py`、
任何 ISO、`GR.IMG` 条目的 `off`/`stored`、制作组名单条目、`MENU.IMG` 内部偏移。

> 本轮**未执行任何 git 命令**。上表是逐文件改动摘要（可用 `git diff` 复核，由 Lead 执行）。
> `charset_compiled_zh16.json` 的改动是**字面插入两行**（`"ç": 231,` / `"ñ": 241`），
> 其余内容逐字节未动 —— 由编辑方式本身保证；实测该文件仍解析出 `codes 110 / pair_of 1319`。

---

## 五、已知限制（诚实挂账）

1. **`font_usage.py` 的口径已经过时（只读冻结，未修改）** —— 实测对比
   `temp/r41/font_usage_selfcheck_before.log`（round43 **之前**的基线）与
   `temp/r43/v13_font_usage_selfcheck.log`（本轮）：
   * 该工具自检**在 round43 之前就已经失败**（exit 1），失败项 `decode_chars(...) != tcslib 口径`
   * 与「32 个单字节码落在毒区」**逐行完全相同** ⇒ **不是本轮引入的**；
   * 本轮只带来两处可预期的增量：
     `单字节码 108 → 110`、`去重后 1427 → 1429`（= ç/ñ），
     以及 `charset 自相矛盾: 1 个 → 3 个`（历史 `0x92=若` + 本轮 `0xE7=ç` / `0xF1=ñ`）；
   * ⚠ 它的**容量数字也是旧口径**（`合法对偶空间 1222 / 已用 1168 / 空位 54 / 死 pair 151`）
     —— 那是**方案 C 扩容前**的 lead 上界（`0xA1..0xAD`）；现役口径是
     **1504 / 1319 / 185 / 0 死 pair**（`tcslib.pair_capacity()`，见 `字库报告.xlsx`）。
     **以 `tcslib` / `dump_font` / 字库报告为准**，不要用该工具的数字。
   * 该工具按铁律**只读未改**；要修口径需单独一轮（属 charset 元数据 + 冻结工具变更）。
2. **PHI 是实证拟合值**（1297 个对偶字逐像素比对：本式 785 个 0 误差），不是从反汇编完整推出；
   极端情况下个别行的列相位可能仍有偏差。报告「口径与限制」页已写明。
3. **view 表里的"文本"只是"字节层面像文本"**：`confidence=low` 的多数是巧合；
   本轮**没有**逐个核对它们是不是游戏里真会显示的文本。
4. **`GR_ZH92_view_pending.csv` 的 2465 个"被跳过的容器"未人工复核**。
5. **UI 快捷键表的 index→动作名未逆向**（`kShortcutDefaultTC @0x2BEFE0`）；
   资料包只登记"存在这张表、与文本码无关"，**不做猜测**。
6. **`text_en`（英文原文）列里的 `ç`/`ñ` 走的是另一条路**（英文盘的 Windows-1252 映射表
   `EN_CP1252`），与本盘字符集无关 —— 两列现在看起来一样，但来源不同（已在 FORMAT.md §2.1 说明）。
7. **资料包的 README 是人工维护**：`make_release_pack.py` **不覆盖** `release/README.md`
   与 `release/text/README_文本表.md`；重跑脚本后请人工确认它们与数字仍然一致
   （本轮数字与脚本输出已核对一致）。

---

## 六、下一步建议（交给 Lead / 用户）

1. **Lead**：把本轮改动合到分支 `round43/latin-fix-and-release`（本轮未动 git）；
   合并前可跑一次 `git diff` 复核上表。
2. **用户**：直接用 `work/builds/GR_ZH93/release/text/README_文本表.md` 里的三步上手；
   想加新字时先看 `字库报告.xlsx` 的「空位清单」页（45 个 slot 的 lead/trail/图集坐标都列好了）。
3. **若要继续扩容**：优先用那 45 个"可直接用"的格位；单字节码这条路已经堵死
   （只剩 2 个图标码）—— 详见报告「口径与限制」页。
4. **若要动 `protected` 口径**（限制 1）：属 charset 元数据变更，建议单独一轮，
   连同 `font_usage.py` 的告警文案一起处理（该工具当前冻结）。
