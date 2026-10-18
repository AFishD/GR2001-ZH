# docs/CORRECTIONS.md —— 历史错误断言订正表（权威）

> 生成：2026-10-18（收尾轮）· 执行者：收尾子代理
> **用途**：本工程跨 90+ 轮的文档里沉淀了若干**后来被实测/实机否证**的断言。这些断言散落在过程报告里，
> 单看某一篇会被误导。本表把它们**逐条订正**，并给出可复核的命令/文件证据。
> **口径**：过程报告一律**保留原文**（它们是过程记录），但凡含错误断言的，文首都会被插入一条
> 「⚠ 历史错误断言订正」横幅，指向本表的对应小节。**冲突时以本表 + `docs/STATUS.md` 为准。**
>
> 被否证的路线类过程报告已归档到 `docs/_obsolete/`（见 `docs/_obsolete/README.md`）。

---

## §1 「汉化改了 ISO9660 的 MENU.IMG 声明长度」 —— 部分是事实，但「零差异」的说法**不成立**（如实订正）

**任务书给的订正口径**是"实为**零差异**"。**实测不支持这个说法**，按纪律如实登记：

测量方法（只读，逐字段比对英文原盘 vs 成品盘 `work\builds\GR_RELEASE\GR_ZH126.iso`）：

```powershell
python - <<'PY'   # 等价脚本：读 PVD 根目录记录 + IMG 容器头 12 个 u32
PY
```

实测结果（2026-10-18，命令输出原文见 `docs/REPORT_FINALIZE.md` §C）：

| 对象 | 字段 | 英文原盘 | 成品 GR_ZH126 | 差异 |
|---|---|---|---|---|
| `MENU.IMG;1` ISO9660 目录记录 | data length (LE@+10 / BE@+14) | 58,300,882 | **58,308,608** | **+7,726** |
| `MENU.IMG` 容器头 | `u32[0] size` | 58,300,882 | **58,308,608** | **+7,726** |
| `MENU.IMG` 容器头 | 其余 11 个字段（names_end/sector/tbl_end/names_start/data_start/hash_off/…） | — | 逐字段相同 | **0** |
| `GR.IMG;1` ISO9660 目录记录 | 整条记录 40 B | — | 逐字节相同 | **0** |
| `GR.IMG` 容器头 | 全部 12 个字段 | — | 逐字段相同 | **0** |
| `SLUS_206.13;1` ISO9660 目录记录 | 整条记录 | — | 逐字节相同 | **0** |

**订正后的正确表述**

1. **成品盘上 MENU.IMG 的「声明长度」确实被改过**：ISO9660 目录记录与 IMG 容器头**两处同步**
   从 58,300,882 改成 **58,308,608**（= 28,471 扇区 × 2048，**扇区对齐**），差值 **+7,726 B**，
   **文件内容一字未动**（这是 2400 线的**设计选择**，不是缺陷）。
2. 该设计在 2400 线的容量报告里就是**计划值**：`docs/CAPACITY_2400.md:211`
   「58,300,882 → 58,308,608（h=644）」。同族改变在 LAY 线也被记录：`docs/REPORT_CULPRIT_STORE.md:346`。
3. 「汉化改了 MENU.IMG 声明长度 ⇒ 读流截断/卡死」这条**因果断言不成立**：
   `docs/REPORT_NULLDEREF_ZH113b.md:155` 已实测否证（该轮 A 线盘上这处**根本没有差异**，
   任务书的假设被推翻）；成品盘带着这处 +7,726 B 通过 6000 帧实机与同现场回归
   （`docs/REPORT_RELEASE_VERIFY.md` §E/§F）。
4. 因此「**零差异**」这个说法只在**两个范围**内成立，务必写清范围：
   * **GR.IMG / SLUS_206.13** 的目录记录与容器头：**逐字节零差异**（上表）；
   * `MENU.IMG` 容器头的**除 `size` 外的 11 个字段**：零差异；
   * A 线（`GR_ZH113b` 系）盘上该处**零差异**（`REPORT_NULLDEREF_ZH113b.md` §）。
   全盘笼统说「MENU.IMG 声明长度零差异」**是错的**。

> ⚠ **未达成/待裁决**：任务书的本条口径与成品盘字节不符，本表按「实测优先」登记，
> 并把原始读数留在 `docs/REPORT_FINALIZE.md` §C 供复核。

---

## §2 「`stored != real` 导致读流截断」 —— **否证**（`stored≠real` 是 LZ 压缩的常态）

* **错误断言**：IMG 条目里 `stored`（压缩后长度）≠ `real`（原始长度）⇒ 引擎按 `stored` 读流被截断 ⇒ 卡死。
* **实测否证**：`docs/REPORT_NULLDEREF_ZH113b.md:163/573` —— **六盘（3 盘 × 2 个 IMG）逐条审计**：
  `stored > real` **0 条**；`stored ≠ real` 的分布（`MENU.IMG` 212/686、`GR.IMG` 1452/4070）
  **英文原盘与汉化盘完全相同** ⇒ 这是**LZ 子流压缩的正常形态**（只有已压缩/等长条目才 `stored == real`）。
* **正确表述**：`stored ≠ real` 是压缩容器的常态，与卡死无因果关系；
  `stored > real` 才是异常，而它在六盘上为 0。
* 相关：`docs/REPORT_TEXT_OVERFLOW.md:640`（沿用该否证）、`docs/REPORT_iso_space_ledger.md`
  （`space_show.py` 用它做**容量**统计，与截断无关）。

---

## §3 「中文串更长 ⇒ 溢出」 —— **否证**（中文总量只有英文的 **48.6%**）

* **错误断言**：中文用双字节、串更长 ⇒ 撑爆缓冲区/表 ⇒ 崩。
* **实测否证**：`docs/REPORT_TEXT_OVERFLOW.md:19`：`MENU:RES` 128,545 B / `GR:RES` 128,668 B
  对英文 264,xxx B ⇒ **中文只有英文的 48.6%**；`:533` 的决定性对照盘 `TXT_03_len_eq_en`
  （把中文**填到与英文等长**）**反而不崩**，而 `TXT_01`（真实中文，更短）**崩**
  ⇒ 触发条件不是长度，而是**内容/编码**（字节分布与引擎硬编码容量）。
* **正确表述**：中文比英文**短得多**（48.6%），长度方向与"溢出"相反；
  真正的机理链条见 `docs/REPORT_DISASM_ROOTCAUSE.md`、`docs/REPORT_HEAP_EXHAUSTION.md`、
  `docs/REPORT_USERDUMP_ANALYSIS.md`，最终以 `tools/final_fix/`（F4+OOMFIX+F7）收口。

---

## §4 「huge 面 224→96 是卡死成因」 —— **否证**（`CVAR_04` / `AB_04` 反证）

* **错误断言**（早期"huge 面补齐"轮次）：汉化把字库 `huge` 面从原盘 224 条减到 96 条 ⇒ 卡死成因。
* **实测否证**：控制变量盘 **`CVAR_04_text`**（= 中文文本 + **完全未改动的原盘 ELF**，`5fec662f…`）
  与 **`AB_04_fontres_real5942`** 把 `huge`/`FONT.RES` 这一维单独改回去，**仍然卡**
  （`docs/REPORT_DISASM_ROOTCAUSE.md` §0 三条硬结论：
  "不卡的盘"与"卡的盘"用的是**同一份代码**，差别只在**数据（文本）**；
  `CVAR_04`（实机崩）的 ELF = 原盘 ELF ⇒ **触发物不是汉化 cave，也不是 huge 面**）。
* **正确表述**：`huge` 面 96 vs 224 与卡死**无因果**；它是**早期（12 轮）**的历史事实，
  在 `docs/BUILD_VERSIONS.md`、`docs/PROGRESS.md` 里以**编年记录**形式保留（已加横幅）。
* 归档：`docs/_obsolete/AB_TEST_GUIDE.md`（承载该路线的打靶盘指南）。

---

## §5 「`mult` 丢 `×94`」 —— **否证**（R5900 三操作数 `MULT`，未丢；丢的是**我们自己的反汇编器**的 `rd`）

* **错误断言**：`0x416FA0` / `0x41708C` 的 `mult` 之后没有 `mflo` ⇒ 地址算式少乘 94。
* **实测否证**：`docs/REPORT_LAYOUT_AUDIT.md:16`「**U1 判定：`×94` 一个字都没丢**」；
  `:85/:106` 给出字节级反汇编 `018e6018 >>> mult $t4, $t4, $t6 <<<`（R5900 **三操作数**，结果直接落 `rd`）。
* **根因**：**本工程自己的反汇编器**把 `rd` 字段丢了 —— `docs/DISASM_TEST_GUIDE.md:397`
  `if fn == 0x18: return "mult $%s, $%s" % (r[rs], r[rt])`（少打印 `rd`）。
* **正确表述**：`mult` 结果**没有**被丢；`slot=(lead−0xA1)*94+(trail−0xA1)` 的公式在盘上自洽。
* 仍残留该错误表述的文档：`docs/REPORT_DISASM_ROOTCAUSE.md`（§"#3 mult 之后没有 mflo，地址算式丢项"，
  已加横幅点名）。

---

## §6 「`sp+221` 是笔误」 —— **否证**（它是解码器写入的字符长度，三元组自洽）

* **错误断言**：`DrawString+0x33C` 读 `lbu v0,221(sp)` 是笔误（"应该是 222"）。
* **实测否证**：`docs/AB_TEST_GUIDE.md:15`、`docs/REPORT_HOOK_BISECT.md:107/432`、
  `docs/REPORT_DISASM_ROOTCAUSE.md:503`：解码 cave `0x416F34 sb $v0,-1($a0)` 把**本字符的长度**
  写在调用者缓冲**前一字节**；`DrawString` 的 224 B 帧里 `sp+221`（长度）/`sp+222..223`（2 字节字符）
  是**三元组**，全部在帧内、不越界。AB_01 探针（把 221 改成 222）**立刻变坏** ⇒ 反证"笔误"说。
* **正确表述**：`sp+221` 是**解码器写入的字符长度**，不是笔误；"变长步进"框架已废弃，
  但**槽位语义自洽**（`docs/REPORT_cave_count_vs_bytes.md` §2/§3 逐字节取证）。
* 相关：`docs/REPORT_NULLDEREF_ZH113b.md:573` 的否证表亦收录本条。

---

## §7 「F1F2 / `pkt` 是修复」 —— **实机否证**；最终三件套是 **F4 + OOMFIX + F7**

* **错误断言**：`SPINFIX_F1F2.iso`（"治因盘"：`StringWidth` 口径 + `GetStringWidth` 等）
  与 `DFIX_pkt`（`pkt` 候选）能治本 ⇒ 应进交付盘。
* **实机否证**：
  * F1/F1b 会带来 **660..810 段 6 帧像素差异**（`docs/REPORT_COMBFIX.md`）⇒ 未采纳；
  * `SPINFIX` 轮的 A/B 显示"治因"路线**没有拦住**本轮病灶（野 `free` + 插链），
    F4（自旋 bail）才拦住（`docs/REPORT_SPINFIX.md`、`docs/REPORT_COMBFIX.md` §"四张组合修复盘"）；
  * `pkt` 路线（`docs/DFIX_REPORT.md`）未被交付盘采用。
* **正确表述（最终盘事实）**：成品盘 = **F4（`0x00102588` → `j 0x0041A35C`）+ OOMFIX（`0x00539174` →
  `j 0x00550048`）+ F7（`0x001021D4` → `j 0x005DECC4`）**，共 **78 B / 25 run**，全部在声明窗口内
  `tools/final_fix/fix_spec.json`（单一真源）+ `tools/final_fix/apply_fix.py --verify-only`
  26/27 条断言可自证。**F1/F1b/flavor A/flavor B 已删除，不应复活。**
* 仍残留该表述的文档：`docs/REPORT_SPINFIX.md`、`docs/DFIX_REPORT.md`、`docs/HOOKEMU_QT2_GUIDE.md`、
  `docs/REPORT_COMBFIX.md`（均已加横幅；`REPORT_COMBFIX.md` 同时是最终结论的取证来源，**保留**）。

---

## §8 附：其它已纠正/待注意的口径

| 断言 | 现状 | 依据 |
|---|---|---|
| `LAY_fix1_bytecount.iso` 是"特意保留"的对照盘 | ❌ **过时**（该盘已按指示删除，只留 sha256 与"结论/日志/截图仍在"的说明） | `tools/final_fix/README.md` §4.4 · `docs/STATUS.md` §6 · `fix_spec.json · archived_away_disks` |
| 基底"必须从 `GR_REBUILD2400.iso` 起" | ❌ **作废**：今后必须从**英文原版 ISO** 起（`GR_REBUILD2400.iso` 仅作开发期快捷基底） | `tools/final_fix/README.md` 顶部 · `tools/final_fix/repro_from_eng.ps1` · `rebuild_base.py` |
| `GR_ZH2400_FINAL` 是成品名 | ❌ **改名**为 `GR_ZH126`（版本号规则：无后缀 + 下一个未用轮次号） | `docs/REPORT_FINALIZE.md` §A |
| 2fps / 读盘停摆 = 钩子开销 | ❌ 否证：开销在**数据侧** | `docs/REPORT_FPS_BISECT.md` |
