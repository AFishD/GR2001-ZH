# RELEASE_NOTES_2400.md —— 幽灵行动（PS2 · SLUS-20613）汉化 **2400 产品线** 交付说明

> 交付候选：`work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso`
> 验收报告（全部数字 + 未达成项）：`docs\REPORT_RELEASE_VERIFY.md`
> 身份证（指纹 / 补丁站点 / 指标索引）：`work\builds\GR_RELEASE\GR_ZH2400_FINAL.meta.json`

---

## 1. 这是什么

* **盘**：`GR_ZH2400_FINAL.iso`（= `work\builds\GR_COMBFIX\COMBFIX_2400.iso` 的**逐字节同源副本**，0 差异）
* **尺寸**：1,648,164,864 B（= 基底尺寸，**未变**）
* **sha256**：`d8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5`
* **md5**：`d24c324eb955a8c8dbaf92f6c766da2c`
* **ELF CRC（PCSX2 的 Game CRC）**：**`CFDB8C97`**
* **即时存档文件名必须写成**：`SLUS-20613 (CFDB8C97).01.p2s`
* **基底链**：英文原盘 → `GR_REBUILD2400.iso`（`d7f83d7e…443ca0`）→ 本盘（相对基底只改了 **78 字节 / 25 处**，全部在声明的 ELF 补丁窗口内，窗口外 **0** 字节）

内容层面它等于 2400 产品线（字库 2,350 对偶槽 / GATE 0xBA / 几何 1024×644 / 64 列 / SKIP=2 / Y0=3 / 文本已迁移），
**只多了同一组三件套修复**。

---

## 2. 本轮修了什么（你能直接感觉到的）

| 你能感觉到的变化 | 对应的修复 | 一句话原理 |
|---|---|---|
| **游戏内卡死消失**（任务完成提示处画面定死、只能强退） | **F4** + **F7** | 分配器的桶链一旦被写坏，链头指向 RAM 之外，原版会**在原地无限自旋**；F4/F7 在链头非法时**改成走原有的"换下一个桶"出口**，于是游戏继续跑 |
| **任务完成可正常结算** | 同上（+ **OOMFIX** 兜住失败资源） | 你实测的 `COMBFIX_C.iso` 与这一张是**同一组补丁**（只是基底不同：那张是 LAY 线，这张是 2400 线）⇒ 实机结论可以直接沿用 |

三件套站点（本盘均在位，且**跑到第 5970 帧逐字回读相符**）：

| 名 | 站点 VA | 原字 → 新字 | cave | 作用 |
|---|---|---|---|---|
| **F4** | `0x00102588` | `0x1459FFD1` → `0x081068D7` | `0x0041A35C`（36 B） | malloc **binmap 大块桶链扫描**：链头不在 RAM 内就 bail |
| **OOMFIX** | `0x00539174` | `0xAE620004` → `0x08154012` | `0x00550048`（44 B） | 解压器里 malloc 返回 NULL 时**不再写 NULL+4**，改走失败分支（`s0=0`） |
| **F7** | `0x001021D4` | `0x1447FFEA` → `0x08177B31` | `0x005DECC4`（36 B） | **own-bin 回边**：链头非法就 bail 到既有出口（截断自旋） |

---

## 3. 怎么用（照做即可）

1. 把 `GR_ZH2400_FINAL.iso` 复制到任意位置（别改字节）。
2. **⭐ 不要读旧的即时存档**。原因有两条，都会让你以为"没修"：
   * 即时存档（`.p2s`）里**整块 32 MB 主存**，会把存档里的**旧代码**盖回 RAM ⇒ **只改 ISO 的补丁在读旧档时不生效**；
   * 存档文件名里的 CRC 与盘不符时**根本读不到**。
   ⇒ 正确做法：**从记忆卡存档继续**，或**从关卡开头进**。
3. 如果你**一定要用**现在手上那份"已经中毒"的即时存档：把它改名为
   `SLUS-20613 (CFDB8C97).01.p2s` 放进 `%LOCALAPPDATA%\PCSX2\sstates\`。
   本盘能救（F7/F4 会在回边把坏链头拦下），但**日志里仍可能出现 1~2 行 `TLB Miss`** —— 那属正常，
   关键是**不会再有第 3 行、不会无限重复、画面不会定死**。
4. 复现原卡死场景：打到**完成全部目标** → 出现「任务完成」提示后**继续按确认 / 等它切结算**。

---

## 4. 已知残余（如实，不藏）

1. **分配器 `0x102200` 那条 unsorted 回边仍未校验**：F7 只护住 own-bin 回边。若坏指针恰好出现在 unsorted 桶，
   理论上仍可能自旋。要补需要**第三个 36 B 的零区**，而 ELF 里当前已扫不到（`REPORT_COMBFIX.md` §3.2）。
2. **F7 的上界放宽到 512 MB**（`a2 = 0x1FFFFFFE`）：坏值落在 `[32 MB, 512 MB)` 时会**多扫一轮**，
   代价是**多 2 行 TLB Miss 日志**，不会自旋。
3. **归因"是否汉化抬高触发率"仍未判定**：没有做"同场景 汉化 vs 英文"的定量对照。
   本轮只是把**已经发生**的堆损坏**从致命改成了可恢复**。
4. **ES / FR / DE / IT 语言表的已知缺陷**：
   * ES / FR（各 MENU+GR 两份）：抬闸门后仍带旧单字节码 **28+29** 处 ⇒ 若主机语言 = ES/FR，界面会**吞字**；
   * DE / IT：结构异常（解析失步），**明确不动**，约 74+76 处；
   * 主机语言 = **中文/英文**时不渲染这些表，无影响。
5. **保留槽 473 个（1872..2344）无字形**：按设计，**文本不引用**（成品盘上引用 >1735 的槽只有
   2345..2349 五个借槽）⇒ 不会出现空白方块。
6. **SF XML 里 5 处"配不出对的前导 `0xA4`"**：上游既有缺陷（`docs\REPORT_SENTINEL_FIX.md` §4/§8.1 已登记），
   本轮**原样保留**；成品盘上独立复核同样是 **5 处**，非本轮引入。
7. **本轮不在盘上的参照盘**（外部清理删除，非本工程决定）：`GR_ZH124.iso`、`GR_F364.iso`、
   `GR_FA2400_K2*.iso`、`GR_REBUILD2400_allpat.iso`、`GR_SPINFIX_F4.iso`。
   受影响的两项验收已用**等价/更强**的方式替代（见验收报告 §B 与 §D）。

---

## 5. 怎么复现 / 取证

### 5.1 离线复跑（不需要模拟器）

```powershell
$py = 'C:\Users\84363\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
$rel = 'work\builds\GR_RELEASE'

# ① 身份 / 差异窗口 / ELF 指纹（最终盘 == 候选盘；vs 基底 78 B 全在声明窗口）
& $py $rel\tools\rel_identity.py --final $rel\GR_ZH2400_FINAL.iso `
      --src work\builds\GR_COMBFIX\COMBFIX_2400.iso `
      --base work\builds\GR_REBUILD\GR_REBUILD2400.iso `
      --meta work\builds\GR_COMBFIX\COMBFIX_2400.meta.json --out $rel\temp

# ② 三闸门 / 槽 0..2349 / 保留槽 / 借槽 / ASCII 182 条（同几何基底逐 texel）
& $py $rel\tools\rel_atlas_base.py --iso $rel\GR_ZH2400_FINAL.iso `
      --base work\builds\GR_REBUILD\GR_REBUILD2400.iso `
      --allpat work\builds\GR_REBUILD\GR_REBUILD2400_allpat.iso --out $rel\temp

# ③ dump_font 家族（full/live 分开计数）—— 复用工程既有 rb_verify_k2.py，输出重定向到本轮目录
& $py $rel\tools\rel_font_dump.py --iso $rel\GR_ZH2400_FINAL.iso

# ④ 文本层：载荷级裸旧码 = 0 / 载荷逐字节相同 / 全量解码未解析字节
& $py $rel\tools\rel_text.py --iso $rel\GR_ZH2400_FINAL.iso `
      --base work\builds\GR_REBUILD\GR_REBUILD2400.iso --out $rel\temp
```

### 5.2 实机（研究用 gsrunner，**独占**，一次只跑一个）

```powershell
# 6000 帧冷启动冒烟 + 第 5970 帧 RAM 落盘（≥190 截图 / TLB 0 / Trap 0）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_RELEASE\tools\rel_smoke.ps1

# 同现场回归（S1 坏桶 + S1b 桶121毒化+低端清零；未修 vs 本盘）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_RELEASE\tools\rel_regress.ps1

# 逐帧 sha256 对照 / 补丁存活回读
& $py work\builds\GR_OOMFIX\tools\oomfix_frames.py `
      work\builds\GR_RELEASE\runs\smoke_GR_ZH2400_FINAL `
      work\builds\GR_RELEASE\runs\smoke_GR_REBUILD2400
& $py work\builds\GR_SPINFIX\tools\spinfix_ramcheck.py `
      --ram work\builds\GR_RELEASE\runs\smoke_GR_ZH2400_FINAL\win_f00005970_eeram.bin `
      --meta work\builds\GR_COMBFIX\COMBFIX_2400.meta.json
```

### 5.3 用**带钩子**的取证版模拟器（你自己复现时）

* 程序：`work\builds\GR_HOOKEMU_QT2\qt\pcsx2-qt.exe`（双击即开钩子，配置在 `qt\hook\hook_config.ini`）
* 说明书：`docs\HOOKEMU_QT2_GUIDE.md`；想**看得更细**就把配置项按
  `work\builds\GR_SPINFIX\hook_config_next.ini` 覆盖（要点：`watch = 0x0055B7A0-0x0055C000`、
  `ring_entries = 2097152`、`log_every = 500`、`max_dumps = 3`）
* 现场出现异常时**按 F10**，会在 `qt\hookdumps\hook_<帧>_<原因>\` 落 32 MB EE RAM + 2 MB IOP RAM + ring + 寄存器
* ⚠ **日志上限**：PCSX2 的 `TLB Miss` 打印**写死只打 50 行**（源码级常量，配置改不了）⇒
  第 50 行之后**看不见**，要用 `hookdumps` 的 ring/RAM 来判，不要只看日志行数。

---

## 6. 一句话总结

> 这一张 = 2400 产品线 + 同一组已在你实机上验证有效的三件套修复；
> 6000 帧实机与基底**逐帧逐像素 0 差异**，两套坏桶现场**未修死 / 本盘出**；
> 剩下的都是**已登记的上游/设计残余**，没有新回归。

---

## 7. 归档与云端（2026-10-18 收尾归档 · 第二轮已推送）

* **成品身份（复核用）**：1,648,164,864 B · sha256 `d8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5` ·
  md5 `d24c324eb955a8c8dbaf92f6c766da2c` · ELF `SLUS_206.13`（LBA 295 / 37,453,732 B）sha256 `6fce4f45967d32593eb940bff91886a829e8871910c0c4a01a7981fc7738e73a` ·
  **Game CRC = `CFDB8C97`**。
* **唯一权威补丁工具**：`tools\final_fix\`（`apply_fix.py` 施工+校验 · `fix_spec.json` 补丁表/身份/验收索引 ·
  `repro.ps1` 一键复跑 · `README.md` 说明书）。此前散落在 `work\builds\GR_COMBFIX|GR_SPINFIX|GR_OOMFIX\tools\`
  的补丁脚本已归并成这一份，只用于当轮 A/B 实验的分支代码（F1 / F1b / flavor A/B）已删除。
* **复现实测**：`apply_fix.py` 从基底 `GR_REBUILD2400.iso` 出盘 ⇒ sha256 与成品**逐字节相同**（本机 9.1 s，exit 0）；
  `repro.ps1` 端到端（含逐字节比对）14.1 s。校验模式 5.5 s / 26 条断言全通过。
* **★ 云端位置与分支名（2026-10-18 第二轮）**：远端 `public` = `https://github.com/AFishD/GR2001-ZH.git`
  * **`main` = `snapshot-2026-10-18` = 同一个提交**（公开**精简快照**，当前 67 文件 / 1.91 MB：
    `tools\final_fix\**` + 60 篇归档文档 + 公开版 `README.md` + `.gitignore`/`.gitattributes`，**不含任何游戏数据**）。
  * **修复落点 = 提交 `2c899a41`**（孤儿精简快照）：`main` 首次被它从 `f0583003` 强更
    （`--force-with-lease`，原文 `+ f0583003...2c899a41 (forced update)`，exit 0）；此后为同步归档小节
    又**快进**到 `59e43d45` 及后续纯文档提交（不改 `tools\final_fix\**`、不改成品身份与任何补丁字节）。
    ⇒ 两个分支**恒同指**，当前值以 `git ls-remote --heads public` 为准。
  * **`snapshot-2026-10-11` = `f0583003`** —— 上一轮公开状态（完整工具链 + `han_v2/` 手册等 267 文件），**未删除、未改写**。
  * 推送纪律：**未用裸 `--force`、未删远端分支、未改本地历史**；唯一一次强推使用了显式钉住旧值的
    `--force-with-lease=refs/heads/main:f0583003…`。
* **推送状态**：**已达成**（上一轮记录的「未达成：历史含 24 个 >100 MB blob / 一次 push 需 32.9 GB」，
  已用「不推完整历史、推孤儿精简快照直更 main」的方式绕过；细节见 `docs\REPORT_ARCHIVE2.md` §B）。
* **`work\` 精简（第二轮）**：20.04 GB / 66,074 文件 → **9.21 GB / 24,083 文件**（释放 **10.83 GB**）。
  保留：成品 `GR_ZH2400_FINAL.iso` + meta · 基底 `GR_REBUILD2400.iso` · **`GR_HOOKEMU_QT2\**`（未动）** ·
  被 `docs\**` 精确引用的证据（719 文件）+ 被引用目录内小证据与 `runs/shots/evidence/audit` 取证截图 ·
  全部自研脚本 · `work\tools\**` 逆向工具链（Ghidra/JDK/工程库）。
  本轮点删（sha256 存证见 `REPORT_ARCHIVE2.md` §C.4）：`GR_LAYOUT\LAY_fix1_bytecount.iso`（`a69a9ca4…`，未修对照盘）、
  `GR_COMBFIX\COMBFIX_2400.iso`（`d8007873…`，**与成品逐字节相同**）、`GR_COMBFIX\COMBFIX_C.iso`（`5c4c9f70…`）、
  `GR_HOOKEMU\**`（旧钩子版）、各轮 `temp/`/`extract/`/`dump_*` 中间物与 `work\tools\dl\*.zip`。
* **git 归档提交**：`01ab3530`（修复+验收归档）→ `8a2554ca`/`2cd167f4`（补记）→ **`a48c4241`**
  （`删除: 清理误入库的 work/ 测试产物（ISO/转储/中间盘）`，移除 4,771 条 / 11,364,158 行 ⇒ 当前树 432 文件）。
  完整记录：`docs\REPORT_ARCHIVE.md`（第一轮）与 **`docs\REPORT_ARCHIVE2.md`**（第二轮：快照/推送/精简全命令与原文）。
* ⚠ **一处过时说明**：上文（第一轮）曾把 `GR_LAYOUT\LAY_fix1_bytecount.iso` 记为「特意保留」；
  第二轮按任务书**点名删除**（不可重建，仅存 sha256）⇒ 「同现场回归」不能原样复跑，结论与日志仍在。

