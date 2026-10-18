# REBUILD_PLAN.md —— 从幸存工具链重建《PS2 幽灵行动 SLUS-206.13》中文 2,400 字盘

> 制定：2026-10-17（本轮重建执行者）｜ 仓库根 = `C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization`
> 目标产物：`work/builds/GR_REBUILD/GR_REBUILD2400.iso`
> 前置阅读（地面真值）：`work/builds/GR_ZH98/temp/LEAD_CAPACITY_2400.md` · `docs/CAPACITY_2400.md`（§12 = K2 做法）·
> `docs/BUILD_VERSIONS.md` · `work/builds/GR_CSFIX/REPORT_CSFIX.md` · `work/builds/GR_CSFIX/audit/ENV_ISO_LOSS.md`

---

## 0. 一句话

**全部 ISO 产物已随磁盘清理丢失，且不可逐字节重建**（`GR_ZH124/_stage644/GR_F364/GR_FA2400_K2` 均为一次性派生盘）。
但 **PCSX2 的 CDVD 块转储（BDV2）幸存**，其中 `GR_FA2400_K2 (2026-10-17 15-08-20).dump` 存着 K2 盘**当次实跑读到的原始扇区**
—— 该转储**恰好覆盖了字库全链与全部中文文本容器**。因此本轮的路线是：

```
GR_REBUILD2400.iso = 英文原盘
                   ⊕ K2 转储的全部真扇区（ELF / 图集 / FONT.RES / 中文语言表 / 中文 SF XML / MENU.PAK / LOADING.PAK …）
                   ⊕ MENU.IMG 尾部位移重建（K2 把 FONT.RES 起的整个尾部后移 0x10800，转储没覆盖的扇区按位移回填）
                   ⊕ GR.IMG 侧三份"同逻辑表副本"的按惯例同步（GR#902 / GR#906 / #3451）
```

**这不是"恢复"**：产物不是 K2 的字节副本（见 §4「与 K2 的预期差异」）。

---

## 1. 目标盘规格（照 K2，不引入新变量）

| 项 | 值 | 依据 |
|---|---|---|
| 盘尺寸 | 1,648,164,864 B（804,768 扇区）| 与原盘同尺寸；ISO9660 目录与本盘结构零改动 |
| ELF | `SLUS_206.13` @ISO 604,160（37,453,732 B）| **逐字节 = K2 真件**（`work/builds/GR_CSFIX/temp/K2_SLUS_206.13.elf`）|
| 图集几何 | `w=1024` / `h=644` / `psm=0x14` / **64 列** / `SKIP_ROWS=2` / `Y0=3` / `V1=V0+16` | `docs/CAPACITY_2400.md` §12.1 |
| 图集容器 | `MENU.IMG #3 COMMON.PAK` 内 `new_font_revised`，`stored=329,744`（`= 1024*644/2 + 16`）| 同上 |
| 字表 | `MENU.IMG #4 FONT.RES`，槽 4,421 B → LZO 展开 5,942 B（3 face / 544 条 FT 记录口径）| 同上 |
| 闸门 | `GATE = 0xBA`（4 个 ELF 站点 `0x416EE8 / 0x417160 / 0x41751C / 0x5656A4`）| 随 K2 ELF 一起落地 |
| 网格常量 | `COLS 62→64` @VA`0x4170AC`；`SKIP 3→2` @`0x4170E8`；`Y0 2→3` @`0x4170F8`；`V1 18→19` @`0x4170FC` | 随 K2 ELF 一起落地（共 8 字节）|
| 槽位 | 对偶槽 **2,350**（`(0xBA-0xA1)*94`）+ 单字节 103 | 随 K2 charset 口径 |
| 含哪些部件 | ① ELF ② MENU.IMG 全部（含图集/字表/中文语言表/中文 SF XML/MENU.PAK/LOADING.PAK/过场）③ GR.IMG（原盘内容 + 3 份副本同步）| §3 |

---

## 2. 输入清单与判据（每一步：输入 / 脚本 / 判据）

### 幸存输入（只读）

| 类别 | 路径 | 用途 |
|---|---|---|
| 英文原盘 | `third_party/orig/ps2/Tom Clancy's Ghost Recon (USA).iso`（sha256 `2b42ea7c…`）| 基底 |
| 块转储 | `%LOCALAPPDATA%\PCSX2\cdvd-dump\*.dump`（21 个；1 个长度自检失败）| 取回汉化真字节 |
| K2 ELF | `work/builds/GR_CSFIX/temp/K2_SLUS_206.13.elf` | ELF 校验锚 |
| 几何/图集工具 | `work/tools/cap_*.py`（`cap_build.py` 的图案内核被复用）| 图案盘（寻址闭环）|
| 文本工具 | `tools/text_csv/{tcslib.py,dump_text_csv.py,inject_text_csv.py,gate_pairs.json}` | 容器编解码权威口径 |
| 迁移工具 | `work/tools/{migrate_legacy.py,migrate_legacy_audit.py,legacy_singles.py}` | 载荷级旧码扫描 |
| charset | `tools/font_pipeline/data/charset_compiled_zh16.json` | 逐字符比对 |
| dump_font | `tools/iso_build/dump_font.py`、`work/tools/cap_verify_k2.py` | 槽位/缺字取证 |
| 模拟器 | `third_party/emu/pcsx2/pcsx2-gsrunner/pcsx2-gsrunner.exe` + `tools/capture/nav_menu_only.txt` | 实机判据 |

### 步骤表

| # | 步骤 | 输入 | 脚本 | 判据（硬）|
|---|---|---|---|---|
| 1 | 基底装配：原盘 ⊕ K2 转储扇区 | 原盘 + `GR_FA2400_K2 (…).dump` | `work/builds/GR_REBUILD/tools/rb_build.py` [1] | ELF 区逐字节 == `K2_SLUS_206.13.elf`；`MENU#3` 记录 `(psm,w,h,px)=(20,1024,644,329744)`；`MENU#25` 首条 payload 非 ASCII（是中文对偶码）|
| 2 | **MENU.IMG 尾部位移重建** | 原盘 + 步骤 1 产物 | 同上 [1c] | K2 条目表实测：`FONT.RES` 起整个尾部 `+0x10800`（COMMON.PAK 增长量）；对 `x ≥ MENU_base+0xC9920` 且扇区未被转储覆盖者取 `原盘[x-0x10800]` |
| 3 | GR#902 中文语言表重建 | 步骤 1 的 `MENU#25`（K2 中文）+ 原盘 `MENU#25`/`GR#902` | 同上 [2] | ① 两份容器 `(g,i)` 序列相同；② 英文盘逐条 payload 相同率 ≥99%；③ `[S2]` 反向重建 == 源 blob；④ 逐条 payload == MENU 中文侧；⑤ `used_end` == MENU 侧；⑥ 重压帧 ≤ 槽 |
| 4 | GR#906 FONT.RES 同步 | 步骤 1 的 `MENU#4` | 同上 [3] | 写后回读 == MENU 侧 slot（英文盘两份逐字节相同）|
| 5 | GR#3451 COMMON.PAK 旁证取回 | `GR_ZH113b (2026-10-15 19-39-44).dump` 的 MENU#3 槽 | 同上 [4] | 记录头 `(20,1024,512,262160)`；前 5,229 B == K2 真字节 100% |
| 6 | 回压 K2 真扇区 | K2 转储 | 同上 [5] | 覆盖写过的区域里，转储覆盖的扇区全部还原为 K2 真字节 |
| 7 | 寻址证明盘 | 成品盘 + `cap_build.py` 图案内核 | `tools/rb_allpat.py` | 2,350/2,350 槽图案解回槽号；格位重复 0 |
| 8 | 离线全量核对 | 成品盘 + 图案盘 | `work/tools/cap_verify_k2.py` | 三闸门 / dump_font / 保留槽单列 / ASCII 182 条 |
| 9 | 载荷级旧码扫描 | 成品盘 | `work/tools/migrate_legacy_audit.py` | `0xB1..0xB9` 单字节位 = 0；逐字符不同 = 0 |
| 10 | 实机 6000 帧 | 成品盘 | `work/tools/cap_run.py` → `cap_results.py` | ≥190 截图 / `TLB Miss` 0 / `Trap exception` 0 / 到中文主菜单 / 跑前跑后零残留 |
| 11 | 拉丁实拍对照 | 成品盘 dump + K2 基线 dump | 截图逐像素 | `TEQSUNSET` / `(8M` / `PlayStation® 2` 可读 |

---

## 3. 哪些环节因中间盘丢失**必须重做**

| 环节 | 结论 | 理由 |
|---|---|---|
| **ELF（字库 cave / 闸门 / 记录- vs 网格 / 文本钩子）** | ✅ **不必重做** | K2 转储覆盖 `SLUS_206.13` 全部 18,288 扇区 ⇒ 逐字节取回 |
| **图集（1024×644 / 2,350 槽字形）** | ✅ **不必重做** | `MENU.IMG #3 COMMON.PAK` 197→230 扇区 100% 被转储覆盖；`rb_build.py [A2]` 实证 `px=329,744` |
| **字表（FONT.RES 记录表）** | ✅ **不必重做** | `MENU.IMG #4` 3 扇区 100% 覆盖 |
| **三份中文文本容器** | ⚠️ **部分重做** | `MENU#25`、`MENU#283` 100% 覆盖（直接取回）；**`GR#902` 无任何转储覆盖** ⇒ 按"两份容器同一逻辑表"的工程既有结论（`docs/REPORT_csv_text_tool.md:98`、`docs/REPORT_zh90_order_label.md:164`）从 MENU 侧对应关系重建 |
| **MENU.IMG 其余部件（MENU.PAK / LOADING.PAK / 语言表 / SF XML / 过场）** | ⚠️ **部分重做** | 转储覆盖 46,988,288..56,459,264 与 2,496,512..6,727,680（MENU 内偏移）；**其余按 §2 步骤 2 的 +0x10800 位移回填** |
| **GR.IMG 侧 `#902 / #906 / #3451`** | ⚠️ **按惯例同步 + 旁证** | 引擎**从不读 GR.IMG 那份字库**（`docs/BUILD_TOOLCHAIN.md:193-194`、`docs/REPORT_build_font_dump.md:340`）；`#906` 用 MENU 侧（英文盘两份逐字节相同）、`#3451` 用 ZH113b 系旁证（记录头与 K2 真字节 100% 一致）|
| **100 轮补丁链（`patch_zhNN.py` 逐代 ISO）** | ⛔ **不重放** | 链路基底（`GR_ZH91`、`r54/*`、`GR_ZH97_base`、`GR_ZH113b` …）全部丢失；`36 份 build_info.json` 只够证明链的形态，不够重放（见 §5） |

---

## 4. 与 K2 的**预期差异**（承认不是字节副本）

| # | 差异 | 量级 | 影响 |
|---|---|---|---|
| 1 | MENU.IMG 尾部位移区内、且转储未覆盖的扇区 = **原盘对应字节**（位移回填），不是 K2 重压后的字节 | 已量化于 `temp/rb_build.log` | 内容等价（同文件同压缩前内容），**压缩字节不同** |
| 2 | `GR#902 EN_STRINGS.RES` 是**重建**的：逻辑字符串与 MENU 侧逐条相同，但 LZO 子流切分由 `T.lzo_compress` 重做 | 帧 32,848 B | ★ 与 `work/builds/GR_TXMIG/temp/build/migrate_report.json` 记录的 `EN_STRINGS.RES@GR` 帧长 **32,848 完全相同** |
| 3 | `GR#3451 COMMON.PAK` = ZH113b 系旁证（h=512 图集），非 K2 原字节 | 400,659 B；前 5,229 B 与 K2 真字节 100% 相同 | 死拷贝（引擎不读），不影响实机 |
| 4 | `GR#906 FONT.RES` = K2 的 MENU 侧（5,942 B 展开），不是 K2 的 GR 侧原字节 | 4,421 B | 死拷贝 |
| 5 | MENU.IMG 里 DE/ES/FR/IT 的 `*_MESSAGE_MC_*.RSB`（记忆卡画面，约 490 KB）为原盘英文版 | 490 KB | 非中文界面无关；切到 ES/FR/DE/IT 时那些画面是英文 |
| 6 | 全盘 sha256 ≠ K2 的 `c3851c1d…` | — | 见 `docs/REBUILD_REPORT.md` |

---

## 5. 判据表（复跑命令 = 可被他人按步骤重跑）

```powershell
# ── 环境 ──  python 在 PATH；chromium 无关；模拟器独占（跑前轮询零 pcsx2）
Get-PSDrive C

# ── ① 出盘（4~5 s）──
python work\builds\GR_REBUILD\tools\rb_build.py
#   预期末行: ★ 产物 = work\builds\GR_REBUILD\GR_REBUILD2400.iso ; sha256 = <见 docs/REBUILD_REPORT.md>

# ── ② 寻址证明盘（全 2,350 槽图案）──
python work\builds\GR_REBUILD\tools\rb_allpat.py
#   预期: [R5] 回读闭环 2350 / 2350 ; [R6] 格位互不重复

# ── ③ 离线全量核对（三闸门 / dump_font / ASCII 182 条）──
python work\tools\cap_verify_k2.py --iso work\builds\GR_REBUILD\GR_REBUILD2400.iso `
       --allpat work\builds\GR_REBUILD\GR_REBUILD2400_allpat.iso `
       --base third_party\orig\ps2\GR_K99.iso --tag rebuild_final `
       --out work\builds\GR_REBUILD\temp\cap_verify_rebuild.txt

# ── ④ 载荷级旧码扫描 + 逐字符一致 ──
python work\tools\migrate_legacy_audit.py work\builds\GR_REBUILD\GR_REBUILD2400.iso `
       --ref-iso work\builds\GR_REBUILD\GR_REBUILD2400.iso --gate 0xBA --base-gate 0xB1

# ── ⑤ 实机 6000 帧（独占；跑前轮询零 pcsx2-gsrunner）──
python work\tools\cap_run.py --iso work\builds\GR_REBUILD\GR_REBUILD2400.iso `
       --dump work\builds\GR_REBUILD\temp\dump_final --nav tools\capture\nav_menu_only.txt `
       --maxframes 6000 --snap 30
python work\tools\cap_results.py work\builds\GR_REBUILD\temp\dump_final
#   原始命令（cap_run.py 逐字使用）:
#   pcsx2-gsrunner.exe -grdumpdir <out> -grmaxframes 6000 -grsnap 30 `
#     -grinput tools\capture\nav_menu_only.txt -grmemcards <out>\mc -logfile <out>\emulog.txt -- <iso>
```

| 判据 | 目标 | 口径 |
|---|---|---|
| (a) 三闸门 | `w≤1024` ✓ `px_size==w*h/2+16` ✓ `(w*h/2)%2048==0` ✓ `px_size ≤ 329,744` ✓ | `cap_verify_k2.py` |
| (b) dump_font | 槽 0..2349 全可寻址；缺字形 0（live 口径）；保留空槽**单列** | `cap_verify_k2.py` + `dump_font.py` |
| (c) 载荷级旧码 | 3 个中文容器 `0xB1..0xB9` 单字节位 = **0** | `migrate_legacy_audit.py` |
| (d) 逐字符一致 | 与 MENU 侧权威文本逐条相同，不同 = **0** | 同上 |
| (e) 实机 | ≥190 截图 / `TLB Miss` 0 / 无 `Trap exception` / 到中文主菜单 / 零残留 | `cap_results.py` |
| (f) 拉丁可读 | `TEQSUNSET` / `(8M` / `PlayStation® 2` 清晰 | 截图对照 |
| (g) 寻址闭环 | 2,350/2,350 槽图案解回槽号 | `rb_allpat.py` |

---

## 6. 纪律（本轮遵循）

- 只读 `third_party/**`、英文原盘、PCSX2 配置与转储、`GR_CSFIX`/`GR_HASHR`/`GR_SENT` 等既有产物目录；
  写入仅 `work/builds/GR_REBUILD/**`、`docs/REBUILD_PLAN.md`、`docs/REBUILD_REPORT.md`。
- 不 commit / 不切分支 / 不 merge；不删除任何既有产物（v1 停滞盘的转储另存 `temp/dump_v1_stall` 作缺陷证据）。
- **模拟器独占**：起跑前后轮询 `pcsx2-gsrunner`；发现他人实例只等不杀；日志等进程退出后再读。
- 不使用 `Select-Object -First N`（需要截断先重定向到文件再读）。
- 闸门层级 / 几何 / 槽位策略照 K2；本轮**未引入任何新变量**（`+0x10800` 位移、`GR#902/906/3451` 同步均为 K2/工程既有做法）。
