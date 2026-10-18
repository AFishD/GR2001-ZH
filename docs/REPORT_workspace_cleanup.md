# 工作区清理记录 + 当前状态索引（2026-10-12，round51 收口）

> 用户验收通过后执行："清理多余构筑 整理资料"。
> 本文记录**删了什么、留了什么、为什么**，以及**当前所有东西在哪**。

---

## 一、清理结果

| 阶段 | `work/` 占用 |
|---|---|
| 清理前 | **56.91 GB** |
| 删 21 个冗余 ISO 后 | 24.67 GB（−32.23 GB） |
| 删 38 个已被报告取代的实机抓帧转储后 | **8.49 GB（共清出 48.42 GB）** |

删除操作前逐条校验：**路径在 `<工程>\work\` 内、是文件/目录、扩展名或目录特征符合预期**；
先干跑列出清单核对，再执行。

### 1.1 删除的 ISO（21 个，每个 1.53 GB）

| 类别 | 盘 |
|---|---|
| 旧诊断盘 | `work/_zh93work/DIAG2/3/4.iso` |
| 被取代的历史构筑 | `GR_ZH91`、`GR_ZH92`、`GR_ZH93`、`GR_ZH94`、`GR_ZH95`、`GR_ZH96_fix` |
| 与 `GR_ZH98` **逐字节相同** | `GR_ZH99` |
| 被 `GR_ZH101` 取代（且 49 个标题仍错） | `GR_ZH100` |
| 测试盘 | `GR_ZH94/temp/r46/GR_ZH94_test_text.iso`、`GR_ZH95/temp/r46/GR_ZH95_test_text.iso` |
| round51 中间候选 | `r51/cand_both.iso`、`r51/cand_glyph.iso`、`r51/single28_fixed_mine.iso`、`r51/cand_both2.iso`、<br>`r51_lead/single28_fixed.iso`、`r51_lead/GR_ZH100_leadver/{GR_ZH100.iso, temp/stable_fixed.iso}`、<br>`r51_lead/GR_ZH101_badbuild/GR_ZH101.iso` |

### 1.2 删除的抓帧转储（38 个目录，16.18 GB）

round46–round50 的实机 A/B 抓帧（`cap_*` / `dump_*` / `r49_*` / `r50_*`），
**它们的结论已经写进对应报告**，原始 PNG 不再需要。

### 1.3 保留的 ISO（4 个，6.14 GB）

| 盘 | sha256 | 为什么留 |
|---|---|---|
| `work/builds/GR_EN_ORIG/GR_EN_ORIG.iso` | `2b42ea7c…` | **英文原件，不可再生** |
| `work/builds/GR_ZH97/GR_ZH97.iso` | `6fc96615…b5098` | 上一版发布（回滚点） |
| `work/builds/GR_ZH98/GR_ZH98.iso` | `f0fc6d8f…992ac3` | **最终盘的构筑基底** + 用户文本编辑基准 |
| **`work/builds/GR_ZH101/GR_ZH101.iso`** | **`e1d303ae4b102d553edaeeaff12d4ea268eba74cedaf4d5c0bd8a9b2360cc45c`** | ★ **最终交付盘** |

### 1.4 保留的小而关键的文件（**没有**随盘删除）

| 文件 | 为什么关键 |
|---|---|
| `work/builds/GR_ZH94/temp/r46/charset_before_repack.json` | 重排前 charset —— 复现"陈旧属性"必须用它 |
| `work/builds/GR_ZH95/temp/font_repack/repack_moves.json` | round50 搬运表 —— 同上 |
| `work/builds/GR_ZH98/text/` | **用户编辑基准**（`text_edited` 列） |
| `work/builds/GR_ZH101/{text,font}/` + `build_info.json` | 最终盘的文本/字库快照与构筑信息 |
| `work/builds/cand_both/temp/dump_r51_doc_cand/`、`cand_both2/temp/dump_r51_doc_cand2/`、<br>`GR_ZH98/temp/verify/r49_doc_zh98/` | **标题 A/B 的实机证据 + 它的基线**（各 ~150–609 MB） |
| `work/builds/GR_ZH98/temp/r51/lead_ab_title/ab_title_zoom.png` | 标题 `；`→`？` 的放大对照图 |

---

## 二、当前状态索引（东西都在哪）

### 2.1 交付物

| 内容 | 路径 |
|---|---|
| **最终盘（中文汉化）** | `work/builds/GR_ZH101/GR_ZH101.iso`（sha256 `e1d303ae…`） |
| 最终盘文本表（3 张，2261 条） | `work/builds/GR_ZH101/text/GR_ZH101_text_{long,long_nowrap,short}.csv` |
| 最终盘字库快照 | `work/builds/GR_ZH101/font/`（atlas PNG、charset CSV、FT CSV、summary JSON） |
| 构筑信息 | `work/builds/GR_ZH101/build_info.json` |
| **英文原件** | `work/builds/GR_EN_ORIG/GR_EN_ORIG.iso` |

### 2.2 用户要改文本时

- 编辑 `work/builds/GR_ZH98/text/` 里 CSV 的 **`text_edited` 列**（新行 = `{br}`，空行 = `{p}`，换行控制写 `{WRAP}`，保留 `{{BTN:...}}`）；
- 重出盘：
  ```
  python tools/iso_build/make_build.py GR_ZH102 \
      --from work/builds/GR_ZH101/GR_ZH101.iso \
      --inject-csv work/builds/GR_ZH98/text --no-font-repack
  ```
  ⚠ `--patch` **只接受一个**（见下）；缺字形会中止（exit 3）。

### 2.3 本轮新增工具（`tools/iso_build/`）

| 工具 | 作用 |
|---|---|
| `single_cell_font.py` | **单格字库 + 逐字与模板比对**（用户点名要的）；1382 格，错误 0 / 一致 99.85%，自带两条独立路径自证 |
| `repack_leak_scan.py` | 重排漏网容器扫描（SFXML `name=` 属性 = 从不被重编码的容器） |
| `patch_zh51_single_byte_band.py` | 修 28 个单字节汉字的字形错位（含清 64 个窗外孤儿像素 + 写盘前硬断言） |
| `patch_zh51_sfxml_titles.py` | 修 49 个 SFXML 标题的陈旧码位（只改 58 字节，`<text>` 一字未动） |
| `patch_zh100_single28_glyphs.py` | Lead 版的 28 字补丁（最终采用了任务版，保留作对照） |

### 2.4 报告

| 报告 | 内容 |
|---|---|
| **`docs/REPORT_single_cell_verify.md`** | 本轮主报告（单格字库工具 / 28 字根因 / 49 标题根因与版本对照 / 实机 A/B / 已知限制 / §9 Lead 收口补记） |
| `docs/FONT_CURRENT_STATE.md` | 字库网格配方权威说明（**顶部已加现役盘指向**） |
| `docs/BUILD_VERSIONS.md` | 版本谱系（**已补 `GR_ZH94`→`GR_ZH101` 链**） |
| `docs/PROGRESS.md` | 全历史进度（**已补 round44–round51 摘要**） |
| `docs/REPORT_workspace_cleanup.md` | 本文 |

---

## 三、本轮结论摘要（一句话版）

- **两处老错字已修**：28 个单字节汉字字形错位（自 `GR_ZH93`）+ 49 个 SFXML 标题陈旧码位（自 `GR_ZH95`）；
- **最终盘 `GR_ZH101`** 两处都含，静态验收全绿，标题修复有实机 A/B 佐证（270/299 帧逐像素相同）；
- **重排保持关闭**（`--no-font-repack`）：容量增益 0，且会破坏不在可注入表里的中文串。

## 四、遗留（如实）

1. **28 个字的实机前后截图没拿到**（两次导航都没走到武器条目页）；修复正确性由静态逐像素证据链支撑（详见主报告 §6.1 / §9.5）。
2. **`make_build.py` 的 `--patch` 是单值参数**，传两次只有最后一个生效 —— 建议改成 `action='append'`。
3. `验` / `骚` 与模板差 1~3 px（渲染器微差，保留为警告）。
4. `font_usage.py` 的容量口径仍是旧值、其自检在 round43 之前就失败（只读工具，不影响产物）。
