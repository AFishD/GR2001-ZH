# DFIX_REPORT —— 候选修复盘（可实机测试）与本机冒烟

> 生成：2026-10-17 · 执行者：**GR_DFIX** 子代理
> 输入（只读）：`work\builds\GR_REBUILD\GR_REBUILD2400.iso`、`work\builds\GR_DISASM\tools\dfix_apply.py`、`docs\REPORT_DISASM_ROOTCAUSE.md`、`docs\DISASM_TEST_GUIDE.md`
> 产物（本目录）：`work\builds\GR_DFIX\**`；追加文档：`docs\DISASM_TEST_GUIDE.md` §7
> 前提事实：重建盘 ELF sha256 = `5cb59175d28bfea3f37a9eb485399ea3925a2ca6f73d32d65e226d274abf47d8`
> （与 K2 逐字节相同 ⇒ **B 线 gate 0xBA**）

---

## 0. 摘要（先读这段）

| 盘 | 补丁 | sha256 | 站点 | 本机冒烟（6000 帧） | 与未修基底逐帧对照 |
|---|---|---|---|---|---|
| *基底副本* | 无（重建盘原件复制） | `d7f83d7e…43ca0` | 0 | 191 张 / 163 画面 / TLB 0 / Trap 0 | 参照物（且与已验收 `dump_final` 191/191 相同） |
| **`DFIX_pkt.iso`** ★ | `pkt`（2 站） | `73a6f6ef…c4008c` | 2 | 191 / 163 / 0 / 0 | **191/191 相同（不同 0 张）**；EE RAM 只差 6 字节 |
| `DFIX_fp.iso` | `fp`（1 站） | `e2f8a163…1f5300` | 1 | 191 / 163 / 0 / 0 | **191/191 相同**；EE RAM 只差 1 字节 |
| `DFIX_icon.iso` | `icon --all12`（12 站） | `ee3b52da…e68a341` | 12 | 191 / 163 / 0 / 0 | **191/191 相同**；EE RAM 只差 21 字节 |
| `DFIX_pkt_fp.iso`（备选） | `pkt+fp`（3 站） | `7bfed9fd…7ffef91` | 3 | 191 / 163 / 0 / 0 | **191/191 相同**；EE RAM 只差 7 字节 |

**一句话结论**：四张盘都**做出来了、都通过了原字断言与产物自证、都能在本机跑满 6000 帧且零 TLB/Trap**；
但**本机这条 6000 帧导航不触发根因**（没有火箭筒 / L1 / 队伍选择 / 长正文），所以四张盘在本机与未修基底
**逐帧逐字节相同**（"不同帧数 = 0"）—— 这是**预期读数**，判决必须由用户在实机按
`docs\DISASM_TEST_GUIDE.md` §7 的序列做（**先 `DFIX_pkt`**）。

**★ 工具层的重大发现（必须先说）**：`work\builds\GR_DISASM\tools\dfix_apply.py` 的
`--iso <盘> --out <新盘>` 模式**写出的不是 ISO，而是抽出来的 37,453,732 B ELF**
（源码 `read_elf_from_iso()` 只返回 ELF 字节，`out = bytearray(data)` 直接写这个数组）。
`docs\DISASM_TEST_GUIDE.md` §4 里给的
`--iso X --out RB_F3.iso --set pkt` 命令**会产生一个不能引导的 `.iso` 文件**。
本轮因此自建 `work\builds\GR_DFIX\tools\mk_dfix_iso.py`：**仍然 import `dfix_apply` 作为唯一站点表真源**
（不改它一个字节），把同样的 4 字节改动落在整盘 `ELF_LBA*2048 + va2off(VA)` 处，产物可直接进模拟器/实机。

---

## A. 补丁可行性与站点表

### A.1 `--check` 原始输出（基底副本，命令与输出逐字）

命令：

```powershell
python work\builds\GR_DISASM\tools\dfix_apply.py --iso work\builds\GR_DFIX\base\GR_REBUILD2400_base.iso --check
```

原始输出存档：`work\builds\GR_DFIX\audit\check_base.txt`

```
=== dfix_apply ===
输入   : ISO work\builds\GR_DFIX\base\GR_REBUILD2400_base.iso（SLUS_206.13 @ LBA 295, 37453732 B）
sha256 : 5cb59175d28bfea3f37a9eb485399ea3925a2ca6f73d32d65e226d274abf47d8
PT_LOAD: [('0x100000', '0x80', '0x4ded00')]
血统   : B（gate 0xBA；b1/b5 属前导区间 ⇒ 图标特判**几乎不可达**）
闸门   : ['0x00BA', '0x00BA', '0x00BA', '0x00BA']
图集几何: ncol=64, rowShift=2, V0=+3, V1=+19

（未给 --set ⇒ --check 默认断言全部站点表）
--- 站点断言（共 21 处）---
  OK [icon] 0x00219C08  240300B5 (期望 240300B5) -> 2403FF00   DrawString 图标判定 #1 (0xB5)
  OK [icon] 0x00219C10  240300B5 (期望 240300B5) -> 2403FF00   DrawString 图标判定 #1 延迟槽 (0xB5)
  OK [icon] 0x00219C14  240300B1 (期望 240300B1) -> 2403FF00   DrawString 图标判定 #2 (0xB1)
  OK [icon] 0x00219C94  240300B5 (期望 240300B5) -> 2403FF00   DrawString 图标判定 #3 (0xB5) 字距
  OK [icon] 0x00219CAC  240300B1 (期望 240300B1) -> 2403FF00   DrawString 图标判定 #4 (0xB1) 字距
  OK [icon] 0x00219D24  240200B5 (期望 240200B5) -> 2402FF00   DrawString 图标判定 #5 (0xB5) → AddOneWord(t0=1)
  OK [icon] 0x00219D38  240200B1 (期望 240200B1) -> 2402FF00   DrawString 图标判定 #6 (0xB1) → AddOneWord(t0=1)
  OK [icon] 0x00416F5C  240900B5 (期望 240900B5) -> 2409FF00   CharWidth cave 图标宽度 (0xB5) → 20
  OK [icon] 0x00416F68  240900B1 (期望 240900B1) -> 2409FF00   CharWidth cave 图标宽度 (0xB1) → 20
  OK [icon-dead] 0x0021AD38  2402FFB5 (期望 2402FFB5) -> 2402FF00   CharWidth 原文残留（死代码）(0xB5)
  OK [icon-dead] 0x0021AD4C  2402FFB1 (期望 2402FFB1) -> 2402FF00   CharWidth 原文残留（死代码）(0xB1)
  OK [icon-inert] 0x00219C40  2403FFB5 (期望 2403FFB5) -> 2403FF00   DrawString 惰性站点（符号扩展，改了不改变走向）
  OK [fp] 0x005659A4  0808669F (期望 0808669F) -> 0808669E   DrawString 拦截器返回目标：j 0x219A7C → j 0x219A78（补回 sq $fp,144(sp)）
  OK [pkt] 0x0021A040  1060004C (期望 1060004C) -> 00000000   主顶点包 flush 后无条件复位计数（去掉 fontmgr+0x48 条件）
  OK [pkt] 0x0021A144  1060000B (期望 1060000B) -> 00000000   副顶点包 flush 后无条件复位计数（去掉 fontmgr+0x48 条件）
  OK [probe-slot] 0x00417084  25ADFF5F (期望 25ADFF5F) -> 25AD003F   F_UV: t5 = trail + 0x3F（把 +0xE0 预并进 t5）
  OK [probe-slot] 0x00417090  018D6021 (期望 018D6021) -> 00006012   F_UV: t4 = mflo（补回被丢弃的乘积累加）
  OK [probe-slot] 0x00417094  258500E0 (期望 258500E0) -> 018D2821   F_UV: a1 = t4 + t5
  OK [probe-slot] 0x00416F98  254AFF5F (期望 254AFF5F) -> 254A003F   CharWidth cave: t2 = trail + 0x3F
  OK [probe-slot] 0x00416FA4  010A4021 (期望 010A4021) -> 00004012   CharWidth cave: t0 = mflo
  OK [probe-slot] 0x00416FA8  250800E0 (期望 250800E0) -> 010A4021   CharWidth cave: t0 = t0 + t2
  断言通过 21 / 21

--- 只读参照（不改动）---
  0x00416EE8 = 2CA900BA   DBCS 前导上界 #1
  0x00417160 = 2D0900BA   DBCS 前导上界 #2
  0x0041751C = 2D4B00BA   DBCS 前导上界 #3
  0x005656A4 = 2D6C00BA   DBCS 前导上界 #4（字形计数 cave 内）
  0x004170AC = 240E0040   图集每行列数 ncol (62 / 64)
  0x004170E8 = 25AD0002   row>=12 的行位移 (+3 / +2)
  0x004170F8 = 25CD0003   V0 = row*16 + (2 / 3)
  0x004170FC = 25CE0013   V1 = row*16 + (18 / 19)

[check] 未写任何文件。
```

**结论：21 / 21 全通过**（与 `audit/check_rebuild_iso.txt` 的既有读数一致）。
基底副本 sha256 = `d7f83d7ec4a8fe1ec8d60de4b17b94513bd1540dc929d3b667086f4910443ca0`
（= 源盘 `work\builds\GR_REBUILD\GR_REBUILD2400.iso` 的实算值，尺寸 1,648,164,864 B，`Get-FileHash` 复核）。

### A.2 产物自证（`mk_dfix_iso.py`）

每张盘写出后做 6 项自证（全部通过，见各 `*.meta.json` 的 `selfcheck`）：

| 自证 | 含义 |
|---|---|
| `size_unchanged` | 整盘尺寸与基底一致（不重排、不截断） |
| `diff_only_in_windows` | 流式逐字节 diff 的**全部**差异段都落在声明的 4 字节窗口内 |
| `every_window_touched` | 每个声明窗口都真的改了字节（不是"以为改了"） |
| `readback_all_ok` | 从**产物**重新解析 ISO→ELF→按 VA 回读，新字全对 |
| `gates_geom_untouched` | 4 个 DBCS 闸门 + 4 个图集几何常量一字未动 |
| `elf_lba_size_unchanged` | 产物里 ELF 仍在 LBA 295、37,453,732 B |

产物 `--check` 读数（**预期就是"少了已打站点数"**，因为站点表断言的是**原字**）：
`DFIX_pkt` 19/21、`DFIX_fp` 20/21、`DFIX_icon` 9/21、`DFIX_pkt_fp` 18/21
（分别 2 / 1 / 12 / 3 处"原字不符"= **已被正确改写**）。原始输出见
`audit/check_DFIX_pkt.txt`、`audit/check_DFIX_fp.txt`、`audit/check_DFIX_icon.txt`、`audit/check_DFIX_pkt_fp.txt`。

### A.3 站点表与差异（VA / ISO 偏移 / 原字 / 新字）

> 全表（自动生成）：`work\builds\GR_DFIX\audit\summary_sites.md`
> ISO 偏移 = `VA − 0x6C780`（与 `REPORT_DISASM_ROOTCAUSE.md` §4 的换算一致，本轮以
> `ELF_LBA 295 × 2048 + (VA − 0xFFF80)` 独立复算，两者逐站点相同）。

**`DFIX_pkt.iso`（★ 优先，2 站 / 4 段差异 / 6 字节）**

| VA | ISO 偏移 | 原字 | 新字 | 站点 |
|---|---|---|---|---|
| `0x0021A040` | `0x001AD8C0` | `1060004C` | `00000000` | 主顶点包 flush 后无条件复位计数 |
| `0x0021A144` | `0x001AD9C4` | `1060000B` | `00000000` | 副顶点包 flush 后无条件复位计数 |

`diff_runs`: `0x1AD8C0`+1 `4c→00` ; `0x1AD8C2`+2 `6010→0000` ; `0x1AD9C4`+1 `0b→00` ; `0x1AD9C6`+2 `6010→0000`

**`DFIX_fp.iso`（1 站 / 1 段 / 1 字节）**

| VA | ISO 偏移 | 原字 | 新字 | 站点 |
|---|---|---|---|---|
| `0x005659A4` | `0x004F9224` | `0808669F` | `0808669E` | `j 0x219A7C → j 0x219A78`（补回 `sq $fp,144(sp)`） |

`diff_runs`: `0x4F9224`+1 `9f→9e`

**`DFIX_icon.iso`（12 站 / 12 段 / 21 字节）**

| VA | ISO 偏移 | 原字 | 新字 | 组 / 站点 |
|---|---|---|---|---|
| `0x00219C08` | `0x001AD488` | `240300B5` | `2403FF00` | icon · 判定 #1 |
| `0x00219C10` | `0x001AD490` | `240300B5` | `2403FF00` | icon · 判定 #1 延迟槽 |
| `0x00219C14` | `0x001AD494` | `240300B1` | `2403FF00` | icon · 判定 #2 |
| `0x00219C94` | `0x001AD514` | `240300B5` | `2403FF00` | icon · 判定 #3 字距 |
| `0x00219CAC` | `0x001AD52C` | `240300B1` | `2403FF00` | icon · 判定 #4 字距 |
| `0x00219D24` | `0x001AD5A4` | `240200B5` | `2402FF00` | icon · 判定 #5 → AddOneWord(t0=1) |
| `0x00219D38` | `0x001AD5B8` | `240200B1` | `2402FF00` | icon · 判定 #6 → AddOneWord(t0=1) |
| `0x00416F5C` | `0x003AA7DC` | `240900B5` | `2409FF00` | icon · CharWidth cave 宽度 |
| `0x00416F68` | `0x003AA7E8` | `240900B1` | `2409FF00` | icon · CharWidth cave 宽度 |
| `0x0021AD38` | `0x001AE5B8` | `2402FFB5` | `2402FF00` | icon-dead · 死代码 |
| `0x0021AD4C` | `0x001AE5CC` | `2402FFB1` | `2402FF00` | icon-dead · 死代码 |
| `0x00219C40` | `0x001AD4C0` | `2403FFB5` | `2403FF00` | icon-inert · 惰性 |

**`DFIX_pkt_fp.iso`（备选，3 站 / 5 段 / 7 字节）** = `pkt` 两站 + `fp` 一站（下表省略，同上）。

### A.4 ★ 每处改动会改变什么行为 / 可能引入什么风险（逐站点写进 meta.json 的 `effect` / `risk`）

**`pkt`（两站，改变 flush 语义 —— 本轮唯一可能改变正常渲染的一刀）**
* **行为**：把"顶点包 flush 之后的计数器复位"从**有条件**（`fontmgr+0x48 != 0`）改成**无条件**。
  原逻辑里 `count` 是在**写入并自增之后**才与容量（主包 1280 / 副包 2）比较；满则 flush，
  而 flush 后仅当 `fontmgr+0x48 != 0` 才 `sw $zero,count`。⇒ 一旦在 `count` 已满时 `+0x48 == 0`，
  `count` **永不复位**，此后每次 `AddOneWord` 都把顶点写到下标 `≥ 容量` ⇒ 顶点缓冲越界写 ⇒
  相邻 dlmalloc 堆块头被改坏（这是静态上唯一"写入下标无上界"的地点，且 A/B 两线字节相同）。
* **风险**：若 `+0x48 == 0` 时"故意不复位"是有意设计，改后会**少送/多送一帧顶点** ⇒
  渲染撕裂 / 丢字 / 闪烁。**因此本盘单独一张、单独测**；一旦出现上述现象立刻回滚本盘。

**`fp`（1 站，零语义加固）**
* **行为**：DrawString 拦截器结尾不再跳过 `0x219A78 sq $fp,144(sp)` ⇒ 尾声 `lq $fp,144(sp)`
  恢复的是**正确的调用者 `$fp`**；静态上唯一真受害者是 `0x2BA5C0`（把 `$fp` 当字体管理器再调 DrawString）。
* **风险**：若有调用者**故意**依赖"DrawString 之后 `$fp` 是垃圾"，会拿到不同的 `$fp`（与 ABI 相悖，几乎不可能）。
  预期与未修盘逐像素一致。

**`icon`（12 站，行为等价于已被实机证明的 `SENT_06` 同型补丁）**
* **行为**：图标特判的比较值 `0x00B1/0x00B5` → `0xFF00`（永不命中）⇒ 这些字符不再走
  `0x219C48..0x219C8C` 的硬编码 UV 块与 `20.0f/11.0f` 硬编码字距、不再用 `t0=1` 写**副顶点包**（容量 2），
  改走**普通字形路径**（`0x219C20 → 0x21ADE0`）与普通字距 ⇒ 不再每 2 个图标就强制一次主+副双包 flush。
* **风险**：若某文本把 `0xB1/0xB5` 当**图标码**用，图标会**消失**（走普通字形路径，不画图标）；
  只有在 `0xB1/0xB5` 本来就是**正常汉字**时才会显示变差。`icon-dead`/`icon-inert` 6 字节行为等价（死代码 / 走向不变）。

> ⚠ **未包含 `probe-slot`**：按任务书与报告 U1（与 `REPORT_atlas_artifact.md` §3 实机取证矛盾），
> **不推荐盲改**，本轮**没有**出这张盘。

### A.5 产物清单（路径 / sha256 / 尺寸）

| 文件 | 字节 | sha256 |
|---|---|---|
| `work\builds\GR_DFIX\base\GR_REBUILD2400_base.iso` | 1,648,164,864 | `d7f83d7ec4a8fe1ec8d60de4b17b94513bd1540dc929d3b667086f4910443ca0` |
| `work\builds\GR_DFIX\DFIX_pkt.iso` | 1,648,164,864 | `73a6f6efaab49b04b132fcfe3e409fc54823a27f9303ca7852df2b354bc4008c` |
| `work\builds\GR_DFIX\DFIX_fp.iso` | 1,648,164,864 | `e2f8a16339729ed0990af4cf9399f407a8626cdb156f84c7f0b39a9aa01f5300` |
| `work\builds\GR_DFIX\DFIX_icon.iso` | 1,648,164,864 | `ee3b52da5a2c864037dcc24f4798f5a76e7a716d193a84302de7573dfe68a341` |
| `work\builds\GR_DFIX\DFIX_pkt_fp.iso` | 1,648,164,864 | `7bfed9fd9f313d006b8c7b01d46caf319f81af0e06f913ef1af04846f7ffef91` |

（每张盘的 `*.meta.json` 同目录；sha256 由 `summarize.py` **独立重算**并与 meta 记录逐字相等。）

---

## B. 本机冒烟（逐张串行）

### B.1 口径与命令

命令（每张盘逐字相同，`cap_run.py` 内部即任务书给定命令）：

```powershell
third_party\emu\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe -grdumpdir <out> -grmaxframes 6000 -grsnap 30 `
  -grinput tools\capture\nav_menu_only.txt -grmemcards <out>\mc -logfile <out>\emulog.txt -- <iso>
```

判据：**≥190 截图 / `TLB Miss` 0 / 无 `Trap exception` / 到中文主菜单**；
外加与**同基底未修盘**逐帧 sha256 对照（同帧号 PNG 逐字节比较）。

### B.2 模拟器独占记录（只等不杀）

原始日志：`work\builds\GR_DFIX\audit\smoke_serial.log`

```
[16:29:16] === GR_DFIX serial smoke START : base -> DFIX_pkt -> DFIX_fp -> DFIX_icon -> DFIX_pkt_fp ===
[16:29:16] [excl] other instance(s) found BEFORE start (wait only, never kill): pcsx2-gsrunner#44556
[16:29:16] [excl] poll #1 : still 1 pcsx2 process(es), wait 20 s ...
[16:29:36] [excl] poll #2 : still 1 pcsx2 process(es), wait 20 s ...
[16:29:56] [excl] poll #3 : still 1 pcsx2 process(es), wait 20 s ...
[16:30:16] [excl] other instance exited by itself; exclusivity acquired (waited ~60 s)
```

* 那个 `pcsx2-gsrunner#44556` 是**重建执行者**的实例（命令行 `-grdumpdir …GR_REBUILD\temp\dump_mc0_12k
  -grmaxframes 12000 … -- GR_REBUILD2400.iso`），**未被我方触碰**，自行退出后才起跑。
* ⇒ **污染声明**：本轮所有**时间/帧率**读数受他人实例共享机器影响，**只作定性**（是否 2fps/挂起），
  不作性能基准；画面/日志类判据不受影响。

### B.3 逐张读数（全部达标）

| 盘 | 截图 | 去重画面 | `TLB Miss` | `Trap exception` | cdvd 事件 | maxLBA | 耗时 | 跑后残留进程 |
|---|---|---|---|---|---|---|---|---|
| `base`（未修对照） | **191** | 163 | **0** | **0** | 60420 | 804765 | 103 s | 无 ✓ |
| **`DFIX_pkt`** | **191** | 163 | **0** | **0** | 60420 | 804765 | 103 s | 无 ✓ |
| `DFIX_fp` | **191** | 163 | **0** | **0** | 60420 | 804765 | 103 s | 无 ✓ |
| `DFIX_icon` | **191** | 163 | **0** | **0** | 60420 | 804765 | 103 s | **1（他人的实例，见下）** |
| `DFIX_pkt_fp` | **191** | 163 | **0** | **0** | 60420 | 804765 | 103 s | 无 ✓ |

* 判据 **≥190 截图 ✓ / `TLB Miss` 0 ✓ / 无 `Trap exception` ✓**；
  帧号区间全部 `270..5970`、首帧/末帧同名、`needle newfontrevisedrs = 2885`、`weaponsanditems = 5532`
  —— 五轮完全同口径。
* 原始输出：`audit/results_base.txt`、`audit/results_DFIX_pkt.txt`、`audit/results_DFIX_fp.txt`、
  `audit/results_DFIX_icon.txt`、`audit/results_DFIX_pkt_fp.txt`；命令存档：`audit/run_*.txt`、各 `runs\<tag>\RUN.txt`。
* **污染登记（如实）**：
  1. 起跑前重建执行者的 12000 帧实例（`#44556`）占了模拟器 ⇒ 等待 60 s 才取得独占（**只等不杀**）。
  2. `DFIX_icon` 跑到 **16:36:07** 时，重建执行者又启动了一个实例
     （`#44524`，`-grdumpdir GR_REBUILD\temp\dump_hashr … -- GR_REBUILD2400_hashr.iso`），
     与我的 icon 跑**尾部重叠约 66 s** ⇒ 该轮时间读数不可作性能基准（截图/日志类判据不受影响，
     因为渲染确定性已由 §B.5 的"同 ISO 两轮 EE RAM 0 字节差异"证明）。
  3. 该重叠导致我的串行脚本按纪律**中止第 5 张**（`DFIX_pkt_fp`）；等对方自行退出后于 16:38:14 补跑完成，
     全程独占（`post_procs = 0`）。

### B.4 逐帧 sha256 对照（与**同基底未修盘**）

原始输出：`work\builds\GR_DFIX\audit\results_cmp_vs_base.txt`（`cap_results.py` 以最后一目录为对照 ⇒ base 放最后）

```
[cmp] DFIX_pkt    vs 对照 base : 同名可比 191 张 ; 逐字节相同 **191** (100.0%) ; 不同 0 张 []
[cmp] DFIX_fp     vs 对照 base : 同名可比 191 张 ; 逐字节相同 **191** (100.0%) ; 不同 0 张 []
[cmp] DFIX_icon   vs 对照 base : 同名可比 191 张 ; 逐字节相同 **191** (100.0%) ; 不同 0 张 []
[cmp] DFIX_pkt_fp vs 对照 base : 同名可比 191 张 ; 逐字节相同 **191** (100.0%) ; 不同 0 张 []
```

**⇒ 四张候选盘与未修基底在 6000 帧里逐像素完全一致，"不同帧数 = 0"。**

**交叉验证（额外的一条硬证据）**：我的 `base` 轮与**重建执行者已验收的转储**
`work\builds\GR_REBUILD\temp\dump_final` 也是 **191/191 逐字节相同**（`audit/` 中命令可复现）：

```
[cmp] base vs 对照 dump_final : 同名可比 191 张 ; 逐字节相同 **191** (100.0%) ; 不同 0 张 []
```

⇒ 我复制过来的基底盘与原件**行为等价**（同一份 ISO、同一采集口径），§B.4 的对照基线成立。

### B.5 ★ 比截图更硬的一条：EE RAM 字节级等价（`ram_equiv.py`）

模拟器在 `GR: dumped RAM (<容器>) frame N` 命中时会把**整块 32 MiB EE RAM**（含载入后的 ELF 镜像，
VA == RAM 偏移）与 2 MiB IOP RAM 落盘。于是可以判"补丁之外**一个字节都没变**"：

* **噪声基线（同一个 ISO 的另一轮 = `dump_final`）**：EE 转储 **0 字节**差异；
  IOP 转储 **2 字节** @ `0x2B461/0x2B462`（运行间漂移，与本补丁无关）。
* 四张候选盘 × 9 个 EE + 9 个 IOP 转储：

| 盘 | EE 转储差异字节（9 个转储全部相同） | 差异偏移 | IOP |
|---|---|---|---|
| `DFIX_pkt` | **6** | `0x21A040,0x21A042,0x21A043` / `0x21A144,0x21A146,0x21A147` | 仅噪声 2 字节 |
| `DFIX_fp` | **1** | `0x5659A4` | 仅噪声 2 字节 |
| `DFIX_icon` | **21** | 12 个站点 VA（`0x219C08…0x3AA7E8`） | 仅噪声 2 字节 |
| `DFIX_pkt_fp` | **7** | pkt 6 + fp 1 | 仅噪声 2 字节 |

**差异字节数 == 该盘声明的补丁字节数，且偏移全部落在声明的站点 VA 上** ⇒
除补丁本身外，**游戏状态在 32 MiB EE RAM 内逐字节相同**（含堆、文本容器、图集、字库）。
原始输出：`work\builds\GR_DFIX\audit\ram_equiv.txt`（工具：`work\builds\GR_DFIX\tools\ram_equiv.py`）。

**日志侧**：`emulog.txt` 每轮均 12,046 行；归一化（去时间戳/地址/路径）后**没有任何游戏侧新行**，
差异全部是 host 路径、`Resulting System Time`、线程号（`audit/logdiff_nonnoise.txt`）。

### B.6 每张盘"预期看到什么"（本机口径 + 实机口径）

| 盘 | 本机 6000 帧**实际**看到 | 实机应按什么口径读 |
|---|---|---|
| `base` | 中文 PS2 记忆卡界面（f300）→ Ubisoft/Red Storm logo → 片头动画 → 进入关卡；全程 191 张、TLB 0、Trap 0 | 对照组：同序列跑一遍，记录"卡/掉帧"的次数与位置 |
| **`DFIX_pkt`** | 与 base **逐帧、逐字节相同**（本序列**没有**触发根因：无火箭筒、无 L1、无队伍选择、无长正文） | **判决实验**：若 B 线的"2fps 挂起"消失或降级 ⇒ #1（顶点包复位闸门）成立；若完全不变 ⇒ 顶点包不是根因；若出现撕裂/丢字 ⇒ 立刻回滚 |
| `DFIX_fp` | 与 base 逐帧相同（**预期**如此，属零语义加固） | 预期与未修盘无异；若症状改善 ⇒ `0x2BA5C0` 那条控制流确实可达（U2 得证） |
| `DFIX_icon` | 与 base 逐帧相同（B 线 gate 0xBA 下 `0xB1/0xB5` 属前导区间 ⇒ 该特判**几乎不可达**，故这是**预期**读数） | 一致性核对：预期无变化；若反而改善 ⇒ B 线仍存在孤立 `0xB1/0xB5`（重大发现） |
| `DFIX_pkt_fp` | 与 base 逐帧相同（备选盘，未单独判定） | 与 `DFIX_pkt` 同读；若两者结论不一致，说明 `fp` 也有份 |

### B.7 ⚠ 如实登记：本 nav 脚本**没有**出现游戏的中文主菜单

判据里的"到中文主菜单"是**沿用**既有报告的验收口径（`docs\REBUILD_PLAN.md` §5 (e)）；
本轮实拍到的中文界面是 **PS2 记忆卡读取屏（f300）**：

![PS2 记忆卡界面（中文，base f300）](work/builds/GR_DFIX/runs/base/snap_f00000300.png)

而 191 帧里**没有**游戏自己的主菜单（「训练/战术演习/战役/…」+ 底栏「△ 返回 / ✕ 接受」——
该画面的既有手工取证例：`work\builds\GR_F364\temp\GR_F364_evidence_mainmenu.png`）。
逐帧画面分组（`audit/frames_base.txt`，163 个去重画面）：
f270–570 记忆卡读取屏（中文，静态 11 张）→ f600/630/1080 近黑（1.6 KB）→ f660–810 Ubisoft logo →
**f840–1050 纯黑（8 张）** → f1110–1770 Red Storm logo → **f1800–2040 纯黑（9 张）** →
f2070–5970 片头动画 + 关卡内画面（每张都不同）。
`nav_menu_only.txt` 的注释说"3272 之后什么都不按 ⇒ 主菜单保持"，但实测 3272 的 `cross` 之后游戏
**已进入关卡**（f3300 起是室内场景），且 1800/2000/2200/2400/2600 的 `start` 短按把菜单段整段跳过了。

* **这不是补丁引入的**：该帧序列与重建执行者已验收的 `dump_final` **191/191 逐字节相同**（§B.4）。
* ⇒ 结论：**本 nav 脚本无法用于验证"到中文主菜单"**；该项在**本轮**记为**未达成**（需要带反馈的
  导航或手工导航，例如 `tools\capture\nav_hook.py` 那种闭环方式）。这条对**用户测试**没有影响——
  用户手动进菜单即可，判据本身不变。

### B.8 顺带发现的新异常（本轮**没有** Trap/TLB/黑屏类新异常）

| # | 现象 | 判定 |
|---|---|---|
| 1 | 两段纯黑（f840–1050 共 8 张、f1800–2040 共 9 张，同 sha `1ce80c81b010`），且整段没有主菜单画面 | **基线特性**（与 `dump_final` 逐字节相同）⇒ 不是补丁引入；但说明该 nav 脚本的菜单段标定已失效，**建议后续修 nav 脚本**，不要用它判"到主菜单" |
| 2 | IOP RAM 在 f≥260 的转储里有 2 字节（`0x2B461/0x2B462`）运行间漂移 | **模拟器侧噪声**（同一 ISO 两轮也漂移）⇒ 已建噪声基线；任何"字节级等价"判据都必须先扣掉它 |
| 3 | `DFIX_icon` 轮与他人实例尾部重叠 66 s | 仅**时间读数**污染；截图/内存等价不受影响（渲染确定性已由"同 ISO 两轮 0 字节差异"证明） |
| 4 | `dfix_apply.py --iso --out` 写出的是 ELF 而不是 ISO（见 §0） | **工具缺陷**（既有文档 `DISASM_TEST_GUIDE.md` §4 的命令因此不可用）⇒ 本轮用 `mk_dfix_iso.py` 绕过，**未改动** `GR_DISASM` 任何文件 |

---

## C. 未达成项与后续

## C. 未达成项与后续

| # | 未达成 | 已做到哪一步 | 需要什么才能闭环 |
|---|---|---|---|
| **N1** | **没有证明任何一张候选盘改变行为** | 四张盘在本机 6000 帧里与未修基底**逐帧逐字节相同**（§B.4/§B.5）。这是**预期**：`nav_menu_only` 序列不触发根因（没有火箭筒、L1、队伍选择、长正文）| **用户在实机的 §7 序列**（这正是本轮出盘的目的）；或做一张带触发的导航脚本（火箭筒/L1 段） |
| **N2** | "到中文主菜单"未在帧内出现 | §B.7 已给出逐帧断点；与已验收转储 191/191 相同 ⇒ 基线行为 | 修 `nav_menu_only.txt` 的菜单段标定，或改用闭环 nav；用户手动进菜单即可绕过 |
| **N3** | **A 线（gate 0xB1）没有出盘** | 本轮基底是 B 线（`GR_REBUILD2400.iso`，ELF 与 K2 相同）。补丁集两线通用，工具也能自动识别血统 | 指定一张 A 线盘（如 `GR_ZH113b` / `GR_SENT*` 系列）作为 `--base`，用同一 `mk_dfix_iso.py` 一条命令即可复现四张盘 |
| **N4** | 未做长导航（12000 帧）与 attract 模式 | 本轮按任务书跑 6000 帧（103 s/张，5 张） | 若需要长时程，`-grmaxframes 12000` 复跑（≈3.5 min/张） |
| **N5** | 未上真机（PS2 / OPL / HDL） | 本机 = `pcsx2-gsrunner` 研究模拟器 | 用户实机；盘的引导性由"与已验收重建盘只差声明字节"保证 |
| **N6** | `probe-slot`（U1）未出盘 | 按任务书"不推荐盲改"**故意不出** | 若要做探针，命令：`mk_dfix_iso.py --sets probe-slot`（6 站）—— **只在探针盘上跑**，不进现役盘 |
| **N7** | 时间/帧率读数受污染（他人实例重叠） | 已登记（§B.3） | 需要干净独占窗口才能给性能数字；本轮只给"是否挂起"的定性 |
| **N8** | 未在模拟器里下断点验证 `fontmgr+0x48` 的时序（报告 P1/P2） | `pcsx2-gsrunner` 是本工程的采集构建，未发现可用的调试断点接口 | 官方 PCSX2 调试器（用户侧）按 `DISASM_TEST_GUIDE.md` §3 的 P1/P2 做 |

**给下一轮的最短路径**：
1. 用户实机按 `docs\DISASM_TEST_GUIDE.md` §7 跑 `DFIX_pkt` → `DFIX_fp` → `DFIX_icon`（各一张盘）；
2. 若 `DFIX_pkt` 让 B 线的 2fps 挂起消失/降级 ⇒ 采纳 `pkt` 并做回归（连续游玩 + 反复开关菜单），
   同时把 `fontmgr+0x48` 的写者（U3）补上以说明"为什么原来会越界"；
3. 若三张盘都无变化 ⇒ 用 `pcsx2` 调试器做 P1（`0x21A048`/`0x21A14C` 断点）直接判 `count ≥ 容量` 是否发生，
   再决定是否转向 §5 的其他路线（U3 容量来源 / U1 槽位算式 / U4 被 NOP 的分支）。

---

## D. 复现命令（全部可重跑）

```powershell
# 0) 磁盘与独占检查（跑前必须 0 个 *pcsx2* 进程）
Get-PSDrive C
Get-Process | Where-Object { $_.ProcessName -like '*pcsx2*' }

# 1) 复制基底并记录 sha256（源盘只读）
Copy-Item work\builds\GR_REBUILD\GR_REBUILD2400.iso work\builds\GR_DFIX\base\GR_REBUILD2400_base.iso
(Get-FileHash work\builds\GR_DFIX\base\GR_REBUILD2400_base.iso -Algorithm SHA256).Hash

# 2) 21 处原字断言（不改盘）
python work\builds\GR_DISASM\tools\dfix_apply.py --iso work\builds\GR_DFIX\base\GR_REBUILD2400_base.iso --check

# 3) 出四张可引导盘（各自单独一盘；每张自带 *.meta.json 与自证）
python work\builds\GR_DFIX\tools\mk_dfix_iso.py --base work\builds\GR_DFIX\base\GR_REBUILD2400_base.iso `
       --out work\builds\GR_DFIX\DFIX_pkt.iso    --sets pkt --tag DFIX_pkt
python work\builds\GR_DFIX\tools\mk_dfix_iso.py --base work\builds\GR_DFIX\base\GR_REBUILD2400_base.iso `
       --out work\builds\GR_DFIX\DFIX_fp.iso     --sets fp  --tag DFIX_fp
python work\builds\GR_DFIX\tools\mk_dfix_iso.py --base work\builds\GR_DFIX\base\GR_REBUILD2400_base.iso `
       --out work\builds\GR_DFIX\DFIX_icon.iso   --sets icon --all12 --tag DFIX_icon
python work\builds\GR_DFIX\tools\mk_dfix_iso.py --base work\builds\GR_DFIX\base\GR_REBUILD2400_base.iso `
       --out work\builds\GR_DFIX\DFIX_pkt_fp.iso --sets pkt+fp --tag DFIX_pkt_fp

# 4) 站点/哈希汇总（独立重算 sha256）
python work\builds\GR_DFIX\tools\summarize.py      # -> audit\summary_sites.md

# 5) 串行冒烟（含独占轮询；等待他人实例，只等不杀）
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_DFIX\tools\smoke_all.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_DFIX\tools\smoke_pktfp.ps1   # 若第 5 张被中止

# 6) 逐帧 sha256 对照（base 必须放最后 = 对照）
python work\tools\cap_results.py work\builds\GR_DFIX\runs\DFIX_pkt work\builds\GR_DFIX\runs\DFIX_fp `
       work\builds\GR_DFIX\runs\DFIX_icon work\builds\GR_DFIX\runs\DFIX_pkt_fp work\builds\GR_DFIX\runs\base

# 7) EE/IOP RAM 字节级等价（含同 ISO 噪声基线）
python work\builds\GR_DFIX\tools\ram_equiv.py --tags DFIX_pkt DFIX_fp DFIX_icon DFIX_pkt_fp
```

**纪律回执**：只读引用 `work\builds\GR_REBUILD\**`、`GR_DISASM\**`、`third_party\**`；
写入仅 `work\builds\GR_DFIX\**`、`docs\DFIX_REPORT.md`、`docs\DISASM_TEST_GUIDE.md`（追加 §7）；
**未** commit / 未切分支 / 未 merge；**未**删除任何既有产物（新增 4 张盘 + 1 份基底副本 = 8.2 GB；
不含 `runs\**` 的转储）；未使用 `Select-Object -First N`；日志一律在进程退出后读；
`exit=0` 未作为判据（判据见 §B.3 的截图数 / TLB / Trap 与 §B.4/§B.5 的逐帧、逐字节对照）。
