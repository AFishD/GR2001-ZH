# REPORT_build_text_integration — dump/注入 打进构筑工具 + 每轮自动产出「版本文本副本」（round31）

日期 2026-10-10 · 目录 `C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization` ·
现役基底 `work/builds/GR_ZH91/GR_ZH91.iso`（sha256 `42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88`）·
Python `C:\ProgramData\anaconda3\python.exe`（3.12.7）

> 本轮**没有动 git**（分支合并交给 Lead → `round31/build-integrate`）、**没有改现役盘**、
> **没有改 `tools/text_csv/` 下任何既有文件**（那位同事正在同一目录改占位符格式，
> 本轮只调用、只在同目录新增一个 `diff_text_versions.py`）。

---

## 0. 一句话结论（人话）

1. **构筑完自动就有文本副本。** 以后每次 `make_build.py` 跑完，新盘里的文本会自己 dump 出来三份：
   该版本目录里的 `_text.csv`（给 Excel 改）、`_text.txt`（给对比看），以及
   `work/text_versions/` 里的一份固定归档 —— **各个版本内部到底写了什么字，随时能翻出来对比**。
2. **想改文案**：改这一轮自动产出的 `<版本>_text.csv` 的 `text_edited` 列 → 下一轮构筑加一句
   `--inject-csv <那个 csv>` 就注进去了。缺字会被**挡在写盘之前**，构筑直接失败并告诉你哪个字不行。
3. **注入失败 = 构筑失败**，不会悄悄给你一张"看着成功、其实没注入"的盘。

---

## 1. 交付物

| 文件 | 状态 | 说明 |
|---|---|---|
| `tools/iso_build/make_build.py` | **改** | `--inject-csv`（可多次，构筑的一等步骤，失败即中止）+ `--no-text-snapshot` + 版本文本快照三段式产出 + `build_info.json` 的 `text_snapshot` 段 |
| `tools/text_csv/diff_text_versions.py` | **新增**（同目录既有文件一律未动） | 跨版本按 `id` 对比文本：增/删/改，`--out` 导出，`--list` 列版本；**只读** |
| `docs/BUILD_TOOLCHAIN.md` | **改**（只追加 §8 新章节，既有章节一字未动） | 构筑流程里 dump/注入的位置、产物路径、改文案的标准动作、对比方法、已知限制 |
| `docs/REPORT_build_text_integration.md` | **新增** | 本文件（设计取舍 + 实跑验证 + 证据清单） |
| `work/tmp/r31_logs/*` | 新增（日志） | 本轮 6 次实跑构筑 + 3 次对比的完整控制台输出 |
| `work/builds/GR_ZH93_inj/`、`work/builds/GR_ZH96_chain/` | 新增（测试产物） | 注入成功例的 ISO（`fc04697f…` / `1542f404…`）+ 三件套文本副本 + `temp/inject*_report.json` |
| `work/text_versions/` | 新增（稳定归档位） | 3 个版本的文本副本 + `INDEX.md` 索引 |

测试版本名都带后缀（`_snap` / `_inj` / `_bad` / `_nosnap` / `_chain`），
`latest_build()` 只认纯 `GR_ZH<数字>` ⇒ **不会被当成"最新盘"，不影响其他人**。

---

## 2. 改了什么（`make_build.py`）

### 2.1 流水线新顺序

```
--from 基底
  → 拷基底 / --patch <补丁>
  → --expand-entry 扩容（可选）
  → ★ --inject-csv 文本注入（0..N 次，按命令行顺序，每次以"上一步产物"为 --src）   ← 新增
  → --verify-img 条目表校验（可选；现在校验的是**注入之后**的最终盘）
  → extract/ 抽取字表 + 字库记录 + MENU.IMG
  → temp/textdump/ 全量文本总表（--no-textdump 可关）
  → ★ 版本文本快照：对**最终 ISO 本身**再 dump 一次                              ← 新增
      work/builds/<VER>/<VER>_text.csv / .txt / .meta.json
      work/text_versions/<VER>_text.txt / .csv / <VER>_snapshot.json / INDEX.md
  → build_info.json（含 text_snapshot 段）
```

### 2.2 四个关键实现点

1. **`run_live()`：子进程输出原样转播、不吞掉。**
   注入器的「字库覆盖预检」报告必须出现在构筑日志里（尤其是失败时），所以用
   `Popen(stdout=PIPE, stderr=STDOUT)` 边读边打，最后把全文返回给失败分支做摘要；
   子进程一律加 `-u`（否则管道 8 KB 块缓冲，报告会憋到最后才出）。
2. **注入链：`--src <当前产物>` → `--dst <临时盘>` → 成功后 `os.replace` 原子替换。**
   这样多份 CSV 天然串成一条链（第 N 步的产物就是第 N+1 步的基底），中途失败**不会**留下半成品盘；
   每一步都带 `--report work/builds/<VER>/temp/inject<N>_report.json` 存档。
3. **失败即中止（硬要求）。** 退出码原样向外传（预检缺字 = 3），并在日志末尾打一段
   `[!!] 文本注入失败 (exit=3) —— 构筑中止, **未产出最终 ISO**`，含缺字清单摘要、
   `inject_report` 路径、以及"要重跑先删版本目录"的提示；
   `build_info.json` 里落 `failed` / `failed_stage` / `inject_report`，`iso_sha256: null`。
   本工具**不提供 `--force` 透传** —— 缺字必须失败。
4. **版本文本快照（默认开，`--no-text-snapshot` 关）。**
   * 先跑 `dump_text_csv.py --iso <最终盘> --out work/builds/<VER>/<VER>_text.csv`；
   * 把 CSV 读回来生成 `_text.txt`（每行 `id<TAB>正文`；换行 `\n`、制表 `\t`、反斜杠 `\\`，
     全部单行 ⇒ 可直接 `diff`、可直接 `git diff`、行数 = 条目数）；
     同一个 dump 派生出 TXT，**不额外读盘**；
   * 归档一份到 `work/text_versions/`，并刷新 `INDEX.md`（版本 / 条目 / 长段 / 字符 / 中文字 / ISO sha / 时间）；
   * `build_info.json.text_snapshot` 写：CSV/TXT/归档路径、各自的 sha256 与字节数、
     **条目数 / 长段数 / 字符数 / 中文字数**、各资源条数、dump 耗时、ISO sha256。
   * 快照失败（例如 dump 的解码自检不过）⇒ **构筑非 0 退出**，ISO 保留，`text_snapshot_error` 落盘。

新增命令行开关：

```
--inject-csv CSV        （可多次）在 --patch 之后按顺序注入
--inject-only IDS       调试用：只注入指定 id（透传 --only）
--no-text-snapshot      跳过版本文本副本（默认不跳过）
```

---

## 3. 怎么用

```powershell
# ① 正常构筑一轮（补丁 + 可选注入）；构筑完自动有文本副本
& C:\ProgramData\anaconda3\python.exe tools/iso_build/make_build.py GR_ZH93 `
    --from work/builds/GR_ZH92 --patch tools/iso_build/patch_zh93.py --verify-img

# ② 想改文案：Excel 打开 work/builds/GR_ZH93/GR_ZH93_text.csv，只改 text_edited 一列
#     （换行直接敲回车；{{BTN:XXXX}} 手柄图标标记原样保留）

# ③ 下一轮把这个 CSV 交给构筑器（字库覆盖预检不过就失败，不会写出空白方块）
& C:\ProgramData\anaconda3\python.exe tools/iso_build/make_build.py GR_ZH94 `
    --from work/builds/GR_ZH93 --inject-csv work/builds/GR_ZH93/GR_ZH93_text.csv

# ④ 对比任意两个版本的文本
& C:\ProgramData\anaconda3\python.exe tools/text_csv/diff_text_versions.py GR_ZH92 GR_ZH93
& C:\ProgramData\anaconda3\python.exe tools/text_csv/diff_text_versions.py GR_ZH92 GR_ZH93 `
    --out work/archive/cmp/r31/diff.txt
& C:\ProgramData\anaconda3\python.exe tools/text_csv/diff_text_versions.py --list
```

`diff_text_versions.py` 的参数可以是**版本名**（自动在 `work/text_versions/`、
`work/builds/<版本>/` 里找快照）、**CSV / TXT 路径**、**构筑目录**，或**ISO 路径**
（临时 dump 到 `work/tmp/`，用完即删，**不动 ISO**）。

---

## 4. 实跑验证（全部真实执行，日志见 `work/tmp/r31_logs/`）

### 4.1 测试 A：现役盘做基底 → 快照三处产物 + `build_info.json` 字段

```powershell
& C:\ProgramData\anaconda3\python.exe tools/iso_build/make_build.py GR_ZH92_snap `
    --from work/builds/GR_ZH91 --verify-img
```

结果：**exit 0，全程 49.4 s**（含 1.65 GB 拷贝 + sha256 + 全量文本总表 + xlsx + 快照）。

```
[base] work/builds/GR_ZH91\GR_ZH91.iso (sha 42d04a4f61982a00...)
[iso] work\builds\GR_ZH92_snap\GR_ZH92_snap.iso (1.65 GB)
[verify] MENU.IMG: 686 条目 (686 有数据), 越界/未对齐 0, 重叠 0
[verify] GR.IMG: 4070 条目 (4070 有数据), 越界/未对齐 0, 重叠 0
[extract] 字表 4421B + 字库记录 263244B + MENU.IMG 55MB → extract/
[textdump] xlsx 写出: ...\temp\textdump\all_text.xlsx (7716 行, 7 个 sheet)
[text-snapshot] 2261 条 / 长段 313 / 65347 字符 (中文 45732)  — 耗时 1.3s
[text-snapshot] CSV work/builds/GR_ZH92_snap/GR_ZH92_snap_text.csv (608 KB)  sha 06d39a2e2801…
[text-snapshot] TXT work/builds/GR_ZH92_snap/GR_ZH92_snap_text.txt (199 KB)  sha 90293a22d8ae…
[text-snapshot] 归档 work/text_versions/GR_ZH92_snap_text.txt + work/text_versions/GR_ZH92_snap_text.csv
[text-snapshot] 索引 work/text_versions/INDEX.md
[done] 本版本文本副本: ... (2261 条 / 65347 字符, 中文 45732)
EXIT=0  ELAPSED_SEC=49.4
```

> 这次 A 是用**最终代码**重跑的（本文件所有测试都在最终代码上跑过）。
> CSV/TXT 的 sha256 与更早一次运行**完全一致**（`06d39a2e2801…` / `90293a22d8ae…`）
> ⇒ 文本快照是确定性的：同一张盘 dump 出来的副本可复现、可当基线。

三处产物都在：

| 位置 | 文件 |
|---|---|
| 版本目录 | `GR_ZH92_snap_text.csv`（608 KB）、`GR_ZH92_snap_text.txt`（199 KB）、`GR_ZH92_snap_text.meta.json` |
| 稳定归档 | `work/text_versions/GR_ZH92_snap_text.{txt,csv}`、`GR_ZH92_snap_snapshot.json`、`INDEX.md` |
| 元信息 | `build_info.json` → `text_snapshot`（字段齐全，见下） |

`build_info.json`（节选）：

```json
 "text_snapshot": {
  "version": "GR_ZH92_snap",
  "iso_sha256": "42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88",
  "generated": "2026-10-10 11:29:09", "dump_seconds": 1.3, "format": "text-csv/1",
  "csv": "work/builds/GR_ZH92_snap/GR_ZH92_snap_text.csv", "csv_bytes": 622104,
  "csv_sha256": "06d39a2e2801e4b08fa3ee5d46f6f8a015c43a3e3fc288a648fd9e9abf22d1ee",
  "txt": "work/builds/GR_ZH92_snap/GR_ZH92_snap_text.txt", "txt_bytes": 203654,
  "txt_sha256": "90293a22d8aea012737fcb8672e84db5221f62073585173e87fe8532b4a8da07",
  "archive_csv": "work/text_versions/GR_ZH92_snap_text.csv",
  "archive_txt": "work/text_versions/GR_ZH92_snap_text.txt",
  "entries": 2261, "long": 313, "locked": 0, "short": 1948,
  "chars": 65347, "cjk_chars": 45732,
  "resources": {"LANG": {...2192 条...}, "SFXML": {...69 条...}},
  "txt_format": "每行 id<TAB>正文(单行); 换行=\\n 制表=\\t 反斜杠=\\\\"
 }
```

TXT 头几行（`id<TAB>正文`，单行）：

```
LANG:G001.I000	胜利！
LANG:G001.I001	遭遇战
LANG:G001.I002	全部敌人被消灭后玩家获胜。
```

### 4.2 测试 B：`--inject-csv` 改 2 条 → 成功，且**只在该条所在窗口有差异**

改动清单（人工改 `text_edited`）：

| id | 旧 | 新 |
|---|---|---|
| `LANG:G001.I000` | 胜利！ | 胜利！！ |
| `SFXML:T0010` | …由曲面的方 / 形硬质弹体制成…金属破片**构成**， | …由曲面的**方形**硬质弹体制成…金属破片**组成**，（把两处软换行接回一行） |

```powershell
& C:\ProgramData\anaconda3\python.exe tools/iso_build/make_build.py GR_ZH93_inj `
    --from work/builds/GR_ZH91 --inject-csv work/tmp/r31_edits/B_ok.csv --verify-img
```

结果：**exit 0，57 s**，注入器自己的断言 + 独立取证脚本都给出一致结论：

```
===== 字库覆盖预检 (写盘前) =====
# 待检查(会被写入) 2 条; 逐字符检查完成
[ok] 字库覆盖完全: 每条文本的每个字符都能编码, 且盘上都有字形 ✓
id                 kind     len_before  len_after    delta     行(前)     行(后)
LANG:G001.I000     short             6          8       +2        1        1
SFXML:T0010        long            174        183       +9        8        8
[write] EN_STRINGS.RES@MENU    @ISO 0x623AD000 帧 32422 B + 零填至槽 47570 B; 回读一致 ✓
[write] EN_STRINGS.RES@GR      @ISO 0xF034F50 帧 32423 B + 零填至槽 47619 B; 回读一致 ✓
[write] EN_SPECIAL_FEATURE.XML @ISO 0x623A0800 帧 41567 B + 零填至槽 49700 B; 回读一致 ✓
[diff] 全盘差异 97597 B / 3 个写入窗口; 窗口外差异: 无 ✓
[verify] EN_STRINGS.RES@MENU 条目 2232: 改动 1 / 逐字节不变 2231; ngroups=66 结构重解析 OK
[verify] EN_STRINGS.RES@GR   条目 2232: 改动 1 / 逐字节不变 2231; ngroups=66 结构重解析 OK
[verify] EN_SPECIAL_FEATURE.XML 条目 69: 改动 1 / 逐字节不变 68, 结构计数不变
[hash] src 42d04a4f61982a00…   [hash] dst fc04697fadebadc0…
[inject] 1/1 完成 → ISO sha fc04697fadebadc0…
[verify] MENU.IMG / GR.IMG 条目表: 越界/未对齐 0, 重叠 0
```

**独立取证**（`work/tmp/probe_r31/cmp_iso.py`，逐字节比对现役盘 vs 注入后，不依赖注入器的自述）：

```
# 差异字节总数: 97597 ; 合并后窗口数: 2 (定位粒度 4096 B, 间隔 <= 8192 B 合并)
  [1] 文件 0xF034000..0xF03D000 (36864 B)  LBA 122984..123001  区域 GR.IMG   ← LANG 的 GR 份拷贝
  [2] 文件 0x623A0000..0x623B5000 (86016 B)  LBA 804672..804713  区域 MENU.IMG ← LANG 的 MENU 份 + SFXML
# IMG 条目表 (off/stored/real) 对比 —— 铁律要求一律不动:
  MENU.IMG  条目 686 ; 字段被改动的条目 0 (应为 0 ✓)
  GR.IMG    条目 4070 ; 字段被改动的条目 0 (应为 0 ✓)
# 结论: 差异 97597 B, 全部落在上列 2 个窗口内 ✓
```

> LANG 语言表在盘上有**两份拷贝**（`MENU.IMG#25` + `GR.IMG#902`），注入器同步写两份
> ⇒ 一条 LANG 改动会命中 2 个窗口（这正是设计要求的"两份同步"）。SFXML 只有一份。

再直接从盘里读字节验证"写进去的确实是 CSV 里写的东西"（`work/tmp/probe_r31/probe_text.py`）：

| 条目 | 基底（174 B） | 注入后（183 B） |
|---|---|---|
| `SFXML:T0010` | 0 个 `{br}`（7 个换行全是 dump 的软换行视图） | `{br}×5`、`{p}×0` —— 与 CSV 里敲的 5 个回车**一一对应** |
| `LANG:G001.I000` | `A4 B7 A3 A6 A8 CF A8 CF`… 6 B | 8 B，`胜利！！` |

### 4.3 测试 C：故意放缺字 → **构筑必须失败**（预检拦截路径）

改动：`LANG:G001.I000` → `胜利龘！`（`龘` U+9F98，盘上画不出来）。完整日志见
`work/tmp/r31_logs/C_build_GR_ZH94_bad.log`。

```
===== 字库覆盖预检 (写盘前) =====
# 字库: 1024x512 @COMMON.PAK+0x146D; FT default face, 224 条记录
# 待检查(会被写入) 1 条; 逐字符检查完成
[!!] 发现 1 个「有问题的字」(共影响 1 处文本):
  ── 字符集里没有 U+9F98  「龘」
     原因: 字符集 (charset JSON) 里没有这个字
     出现在: LANG:G001.I000 (EN_STRINGS.RES@MENU+GR.IMG#902) 第 3 个字符 [G001.I000]
     怎么办: 该字不在本盘字符集里。要么改写文案换成常用字, 要么先扩字符集+字库再注入。

[拒绝写盘] 预检不通过: 1 个字有问题 (1 个「字符集没有 / 盘上无字形」 + 0 个「死 pair」)。

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
[!!] 文本注入失败 (exit=3) —— 构筑中止, **未产出最终 ISO**。
     注入用的 CSV : work/tmp/r31_edits/C_bad_char.csv
     当时的产物   : work/builds/GR_ZH94_bad/GR_ZH94_bad.iso  (补丁后的中间态, 未注入任何文本)
     注入报告     : work/builds/GR_ZH94_bad/temp/inject1_report.json
     原因 = 字库覆盖预检不通过 (有缺字), 缺字清单见上面 「字库覆盖预检 (写盘前)」一节:
     ── 字符集里没有 U+9F98  「龘」
     原因: 字符集 (charset JSON) 里没有这个字
     怎么办: 把缺字换成常用字 (最省事), 改完 CSV 再重跑构筑;
!!!...
C_EXIT=3  ELAPSED_SEC=3.8
```

失败后的状态（都验过）：

| 检查 | 结果 |
|---|---|
| 构筑退出码 | **3**（非 0 ✓），3.8 s 就失败（没有白跑全量流程） |
| 是否产出最终盘 | **没有**：`GR_ZH94_bad.iso` 仍是"补丁后的中间态"，与基底**逐字节相同**（sha256 相同 ✓） |
| 是否有快照产物 | 没有 `_text.*`，`work/text_versions/` 里也没有该版本 ✓ |
| 半成品临时盘 | 没有 `.inject1.iso.tmp` 残留 ✓ |
| `build_info.json` | `iso_sha256: null` + `failed` / `failed_stage: inject1` / `inject_report` ✓ |

### 4.4 测试 D：`diff_text_versions.py` 对「基底 vs 注入后」输出正确差异

```
& python tools/text_csv/diff_text_versions.py GR_ZH92_snap GR_ZH93_inj --out work/archive/cmp/r31/diff_GR_ZH92_snap_vs_GR_ZH93_inj.txt

# A = GR_ZH92_snap     ← work/text_versions/GR_ZH92_snap_text.txt
#     2261 条 / 65347 字符 / 其中中文 45732
# B = GR_ZH93_inj      ← work/text_versions/GR_ZH93_inj_text.txt
#     2261 条 / 65353 字符 / 其中中文 45732
# 对齐口径 : 按 id; 文本按「转义单行形式」比较 (换行=\n 制表=\t 反斜杠=\\)

====================== 汇总 ======================
只在 A (GR_ZH92_snap) 消失 : 0 条
只在 B (GR_ZH93_inj) 新增 : 0 条
两边都有、内容不同 : 2 条
两边都有、内容相同 : 2259 条
条目数   2261 → 2261 (+0)
字符数   65347 → 65353 (+6)
中文字   45732 → 45732 (+0)

====================== 修改 (2 条) ======================
[~] LANG:G001.I000   (A 1 行 → B 1 行)
    - 胜利！
    + 胜利！！
[~] SFXML:T0010   (A 8 行 → B 13 行)
    - M18 定向反步兵地雷由曲面的方
    - 形硬质弹体制成， 内装约 340 克
    + M18 定向反步兵地雷由曲面的方形硬
    + 质弹体制成， 内装约 340 克
    + (空行)
    - 其破片面由方形金属破片构成，
    + (空行)
    + 其破片面由方形金属破片组成，
    + (空行) …
```

* 差异条目与人工改动**完全对上**（2 条，其余 2259 条逐字符相同）；
* 「增加/删除」两类这次都是 0 条（没有 id 进出 —— 因为 id 是按 `LANG:Gxxx.Ixxx` / `SFXML:Txxxx`
  稳定编号，**换行或长度变化都不会让 id 错位**，这也正是"按 id 对齐"的意义）；
* 给 ISO 路径也能比：`diff_text_versions.py GR_ZH91 GR_ZH93_inj` 会临时 dump 现役盘再比，
  结果同样是 2 条改动（日志 `F_diff_final_inj.log`）。

### 4.5 附加验证 1：`--no-text-snapshot` 真的跳过（要求 2）

```
TEST D: --no-text-snapshot --no-textdump
[extract] 字表 4421B + 字库记录 263244B + MENU.IMG 55MB → extract/
[done] ...   D_EXIT=0  ELAPSED_SEC=3     ← 不 dump, 3 秒结束
```
`GR_ZH95_nosnap/` 里**没有** `_text.*`；`build_info.json` 里 `"text_snapshot": null` ✓。

### 4.6 附加验证 2：`--inject-csv` 连续两步（要求 3 的顺序语义）

第二步的 CSV 是从**第一步的产物** dump 出来的（`GR_ZH93_inj_text.csv` 改一条
`LANG:G001.I001` → `遭遇战！`；它在 LANG 里的 `offset` 已因第一步 +2 变成 26）：

```
make_build.py GR_ZH96_chain --from work/builds/GR_ZH91 \
    --inject-csv work/tmp/r31_edits/B_ok.csv \
    --inject-csv work/tmp/r31_edits/D_ok2.csv --verify-img

[inject] 1/2 完成: B_ok.csv → ISO sha fc04697fadebadc0…     ← 与 GR_ZH93_inj 逐字节相同
[inject] 2/2 完成: D_ok2.csv → ISO sha 1542f404cf5fe624…
[text-snapshot] 2261 条 / 长段 313 / 65354 字符 (中文 45732)
E_EXIT=0  ELAPSED_SEC=66.4
```

两点结论：
1. 第 1 步产物 sha 与单独跑测试 B **完全相同** ⇒ 注入是确定性的，链式不会引入漂移；
2. 第 2 步用"上一步产物的 CSV"能过，用"基底的 CSV"会被注入器拒绝（`offset/len` 不符）——
   这是有意的保护，已在文档里写明正确用法。

差异条数 3 条（`GR_ZH92_snap` vs `GR_ZH96_chain`，日志 `G_diff_final_chain.log`），
字符数 65347 → 65354（+7 = +2 +2 +3），与两次注入的字节增量一致。

### 4.7 附加验证 3：增/删/改三条路径（用小样本夹具，不耗构筑时间）

真实两个版本之间本轮没有 id 进出，所以用一对 3 行的小夹具把「新增 / 删除 / 修改」三条路径都跑一遍
（`work/tmp/r31_edits/fixture_A_text.txt` vs `fixture_B_text.txt`）：

```
====================== 汇总 ======================
只在 A (fixture_A) 消失 : 1 条
只在 B (fixture_B) 新增 : 1 条
两边都有、内容不同 : 2 条
两边都有、内容相同 : 0 条

====================== 修改 (2 条) ======================
[~] LANG:G001.I000   (A 1 行 → B 1 行)
    - 胜利！
    + 胜利！！
[~] SFXML:T0010   (A 2 行 → B 3 行)
    + 其破片面由方形金属破片组成，

====================== 只在 B 新增 (1 条) ======================
[+] LANG:G001.I099
    + 新加的条目（只在 B 里）

====================== 只在 A 消失 (1 条) ======================
[-] LANG:G001.I001
    - 遭遇战
```

同时验证：`--limit 1` 只截断**控制台**（打印 `…(还有 1 条, 用 --out <文件> 导出完整清单)`），
`--out` 写出的文件始终完整（34 行）✓；`--list` 能列出 3 个版本 × 2 种格式 + 构筑目录里的副本 ✓。

### 4.8 汇总

| 测试 | 命令要点 | 结果 |
|---|---|---|
| A 快照三件套 | `GR_ZH92_snap --from GR_ZH91` | exit 0 / 49.4 s；三处产物 + `build_info.text_snapshot` 字段齐全 ✓ |
| B 注入成功例 | `--inject-csv B_ok.csv` | exit 0 / 57 s；改 2 条；全盘差异 97597 B 全在窗口内，条目表 0 处改动 ✓ |
| C 缺字拦截 | `--inject-csv C_bad_char.csv`（`龘`） | **exit 3** / 3.8 s；预检报告完整打印；没写盘、没快照、中间态与基底逐字节相同 ✓ |
| D 跨版本对比 | `diff_text_versions.py` | 增 0 / 删 0 / 改 2 / 同 2259，条目与人工改动一一对应 ✓ |
| E 关快照 | `--no-text-snapshot` | exit 0 / 3 s；无 `_text.*`，`text_snapshot: null` ✓ |
| F 链式注入 | `--inject-csv a --inject-csv b` | exit 0 / 66.4 s；第 1 步产物 sha 与单跑一致，第 2 步匹配中间产物 ✓ |
| G 增删改三路径 | 夹具 `fixture_A/B_text.txt` | 增 1 / 删 1 / 改 2，`--limit` 与 `--out` 行为正确 ✓ |

---

## 5. 设计取舍

1. **为什么 CSV 和 TXT 都要出？** 实测全量 dump 只要 **1.3–1.5 s**（2261 条，SSD），
   不值得为省这点时间牺牲可用性：CSV 是人工编辑/校对的主角（Excel 双击即开），
   TXT 是给"看和比"的（单行、199 KB、行数 = 条目数，diff 起来干净）。TXT 由同一份 dump 派生，
   不额外读盘，增量成本几乎为零。
2. **为什么快照失败算构筑失败？** 用户要的是"每一轮新 ISO 都会顺带一份副本"，
   如果快照静默失败，就会出现"这一轮没有文本副本、事后才发现"的情况。
   现在：ISO 照样保留（不白跑），但退出码非 0 + `text_snapshot_error` 落盘 + 打印单独重跑的命令。
3. **为什么快照默认开、只留一个"关"的开关？** 需求就是"每一轮都要有副本"，
   所以默认必须产出；`--no-text-snapshot` 只服务于调试/省时间的少数场景
   （`--no-textdump` 同理，两个开关相互独立）。
4. **TXT 为什么不带表头/BOM？** 让"每行 `id<TAB>正文`"这句话成立（行数 = 条目数），
   也让 `diff` 第一行就是数据；版本/统计信息放进 `build_info.json`、`<VER>_snapshot.json`、`INDEX.md`。
5. **为什么不做 `--force` 透传？** 缺字必须拦截；想强行写入的人应该直接调用注入器并看到警告，
   不该在构筑器里被一个开关糊过去。
6. **为什么 `diff_text_versions.py` 严格只读、且支持直接给 ISO？** 对比是"看"的操作，
   任何写盘都会增加事故面；但为了让"还没构筑过文本副本的老盘"也能比，允许临时 dump 到 `work/tmp/`
   （用完即删，ISO 只读打开）。
7. **依赖的接口面尽量小。** 只用到 `dump_text_csv.py --iso/--out` 与
   `inject_text_csv.py --csv/--src/--dst/--report/--only` 的命令行，以及 CSV 的
   `id / resource / kind / container / text_zh / text_edited` 六列 —— 同事改占位符格式时不受影响
   （实测本轮期间 `tcslib.py`、`inject_text_csv.py`、`dump_text_csv.py`、`FORMAT.md` 都在被同事改动，
   本集成照常工作）。

---

## 6. 已知限制与接力提醒（重要）

1. **⚠ 长段文本"再编辑"会把软换行变成段落空行（既有工具链行为，非本轮引入）。**
   本轮实测确认：
   * 长段（SFXML，wrapW=270）在 CSV 里显示的换行**大部分是 dump 的渲染视图软换行**，盘上并没有换行
     （基底 `SFXML:T0010`：174 B、`{br}×0`）；
   * 一旦编辑注入，这些换行就**固化**成 `{br}`（写入字节与 CSV 里敲的回车一一对应，实测 `{br}×5 / {p}×0`，
     盘上**没有**空行）；
   * 再 dump 时，`tcslib.wrap_render()` 会在每个 `{br}` 处多渲染出一个空行 ⇒ 该条 `text_zh` 里出现空行；
   * **风险点**：如果下一轮又编辑这条（哪怕只改一个字），单元格里那些空行会被
     `cell_to_bytes_text()` 折叠成 `{p}` 写进盘 —— **原来的普通换行会变成真·空行**。
   * 现役盘已经有 **26 条**长段处于这种状态（例：`SFXML:T0043/T0044/T0045`，note 里写着 `硬换行 ×3`）。
   * 这属于 `tools/text_csv/tcslib.py`（`wrap_render` 的显示口径与 `text_to_cell` 不一致）的范畴，
     **本轮按要求没有改她的文件**；请 Lead 转给正在改 text_csv 的同事，或在下一轮统一处理
     （建议：`wrap_render` 对 `{br}` 不额外多出一行，或在 dump 时把渲染视图与存储视图分开标注）。
   * 规避办法（本轮起就能用）：编辑长段前，先把该条 `text_edited` 里**多余的空行删掉**再改字。
2. **多份 `--inject-csv` 必须"各自匹配上一步产物"**：注入会改变同一容器里后续条目的 `offset`，
   拿基底 dump 的 CSV 当第二份会被注入器拒绝（exit 1）。正常做法就是"上一轮产出的 `<VER>_text.csv`"。
   一轮里需要改的条目建议合并成一份 CSV 一次注入。
3. **快照覆盖范围 = dump 能看到的范围**：`LANG`（语言表，两份拷贝）+ `SFXML`（特别收录 XML），
   共 2261 条。盘里其它文本（其它 RES 字符串表、ELF 内字符串、纹理字幕等）不在其中
   （见 `docs/REPORT_csv_text_tool.md`）。⇒ "版本文本副本"目前不等于"全盘所有文字"。
4. **`work/**` 在 `.gitignore` 里**（仓库"游戏衍生数据不入库"策略）⇒ 文本副本是本地产物，
   跨版本对比请用 `diff_text_versions.py`（而不是指望 git 里有这些文本）。
5. **磁盘**：每个测试版本目录含 1.65 GB ISO。本轮结束后已删掉 3 份"与基底逐字节相同"的测试 ISO
   （`GR_ZH92_snap` / `GR_ZH94_bad` / `GR_ZH95_nosnap`，删前逐个校验 sha256 相同），
   保留 `GR_ZH93_inj.iso` 与 `GR_ZH96_chain.iso`（内容真的变了，可做实机验证）。
   要全部清掉：
   ```powershell
   Remove-Item -Recurse -Force work/builds/GR_ZH92_snap, work/builds/GR_ZH93_inj, `
       work/builds/GR_ZH94_bad, work/builds/GR_ZH95_nosnap, work/builds/GR_ZH96_chain
   ```
   （构筑器不覆盖已存在的版本目录 —— 想重跑同名测试必须先删目录。）
6. **未做实机验证**：本轮只到"构筑 + 字节级断言 + 文本对比"，没有跑 PCSX2。
   `GR_ZH93_inj.iso` / `GR_ZH96_chain.iso` 已就位，可直接上模拟器抽帧看那两三条改动。
   （`LANG:G001.I000` 是营地界面的短标签；`SFXML:T0010` 在「特别收录」里。）

---

## 7. 证据文件清单

| 路径 | 内容 |
|---|---|
| `work/tmp/r31_logs/A_build_GR_ZH92_snap.log` | 测试 A 完整控制台输出（含 dump 的自检行） |
| `work/tmp/r31_logs/B_build_GR_ZH93_inj.log` | 测试 B 完整输出（预检 + 写入 + 全盘差异断言 + 快照） |
| `work/tmp/r31_logs/C_build_GR_ZH94_bad.log` | 测试 C 预检拦截的完整输出（exit 3） |
| `work/tmp/r31_logs/D_build_GR_ZH95_nosnap.log` | `--no-text-snapshot` 输出 |
| `work/tmp/r31_logs/E_build_GR_ZH96_chain.log` | 链式两步注入输出 |
| `work/tmp/r31_logs/D_cmp_iso.txt` | 独立逐字节比对（现役盘 vs 注入后）+ 条目表未改动断言 |
| `work/tmp/r31_logs/F_diff_final_inj.log`、`G_diff_final_chain.log`、`H_diff_fixture_addremove.log` | 跨版本对比的完整输出（含增/删/改三条路径） |
| `work/archive/cmp/r31/diff_GR_ZH92_snap_vs_GR_ZH93_inj.txt`、`…_vs_GR_ZH96_chain.txt` | `--out` 导出的完整差异报告 |
| `work/tmp/r31_edits/B_ok.txt|.csv`、`C_bad_char.txt|.csv`、`D_ok2.txt|.csv` | 本轮改动清单与原样 CSV（可复现） |
| `work/tmp/probe_r31/cmp_iso.py`、`probe_text.py`、`list_hardbreak.py`、`edit_csv.py` | 取证/改 CSV 的临时脚本（**非交付物**，放在 `work/tmp/` 下，随时可删） |
| `work/builds/GR_ZH93_inj/temp/inject1_report.json`、`work/builds/GR_ZH96_chain/temp/inject{1,2}_report.json` | 注入器自带的 JSON 报告（含「字库覆盖预检」一节） |
| `work/builds/GR_ZH94_bad/temp/inject1_report.json` | 失败例的报告（`mode: rejected-by-precheck`） |
| `work/text_versions/INDEX.md` | 所有已归档版本文本副本的索引表 |
