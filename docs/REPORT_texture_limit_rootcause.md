# ★ 根因报告：像素容器/纹理变大后引擎卡死（round85）

> 作者：执行任务（round85）· 工作目录 `C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization`
> 结论一句话：**卡点是"引擎在读/搬运 `new_font_revised` 像素容器时，一个全局读流游标停在
> PAK 内 428,032 B 处不再前进"，此后该盘上所有后续文件加载全部失败。**
> **1024×1024 尺寸判据确实存在（已给出精确 VA/指令），但它不是本次卡死的原因——探针已实证。**
> **⇒ 用 1~2 条指令绕开：不可行（本轮已用探针盘否证 2 处 1 字改动）。**

---

## 0. 本轮新增工具（全部在 `work\tools\`，只读；只有 `root_probe_gate.py` 写新盘）

| 工具 | 作用 |
|---|---|
| `root_dis.py` | 给定 VA 反汇编（用 `cave_dis.py` 的 R5900 解码器 + r72 的 ELF）；`callers/find/str/map` 子命令 |
| `root_trace.py` | `back <VA>` 找函数序言 / `xref` / `fn` 基本块树 |
| `root_cfg.py` | 轻量基本块 CFG |
| `root_atlas_layout.py` | 自足解析 ISO9660 → MENU.IMG → IMG 条目表 → COMMON.PAK 记录链 → 容器；打印容器 16 B 步进的 tag 形状 |
| `root_ram_find.py` | 在 EE RAM 快照里按 GIF 头签名定位**像素容器在 RAM 里的真实形态** |
| `root_ram_atlas.py` / `root_emu_check.py` / `root_strs.py` | 辅助（RAM 扫描 / unicorn 判据复算 / gsrunner 字符串表） |
| `root_probe_gate.py` | 出探针盘：只改 ELF 尺寸判据上界，逐字节差异断言 |
| `root_run.py` | 实机跑（gsrunner 串行，单实例，`--log` 捕获 stdout） |

### 0.1 ★ 更正任务书给的 VA→ISO 映射

任务书与 `dump_decode_cave.py` 写的是 `ISO = 0x93800 + (VA − 0x100080)`（= VA − 0x6C880）。
**实测应为 `ISO = VA − 0x6C780`**（差 0x100）。三个锚点 × 两张盘交叉核验：

```
VA 0x416EE8（cave 的 sltiu …）        ⇒ ISO 0x3AA768 = 2CA900B4 ✓
VA 0x51D9BC（LoadPS2Img slti …1025）  ⇒ ISO 0x4B123C = 28610401 ✓
VA 0x51DB24（镜像分支同一条）          ⇒ ISO 0x4B13A4 = 28610401 ✓
```

---

## 1. 已找到的"尺寸硬判据"：`UITexture::LoadPS2Img`（精确到指令）

ELF 符号表（Ghidra headless 读出的 mangled 名）确定了整条路径：

```
0x51B660  LoadingTexturePak__12UITextureMgrFiPCc        (PAK 装载入口)
0x51C810  LoadRSBFile__9UITextureFRQ23std39basic_istream<...>   (记录解析；唯一的 LoadPS2Img 调用者)
0x51D910  LoadPS2Img__9UITextureFRQ23std39basic_istream<...>    (读 w/h/clut/px_size + 拷贝像素)
```

`LoadPS2Img` 里 **4 条** 尺寸判据（`VA / 原字 / 反汇编`）：

| VA | 原字 | 反汇编 | 失败去向 |
|---|---|---|---|
| 0x51D9BC | `28610401` | `slti $at, $v1, 1025` | `beq $at,$zero → 0x51DC14` |
| 0x51D9C8 | `28410401` | `slti $at, $v0, 1025` | 同上 |
| 0x51DB24 | `28610401` | `slti $at, $v1, 1025` | 同上（PSMT8/PSMT4 镜像分支） |
| 0x51DB30 | `28410401` | `slti $at, $v0, 1025` | 同上 |

`$v1/$v0` 来自 `96230010 lhu $v1,16($s1)` / `96220012 lhu $v0,18($s1)`，也是**记录 +0x01C / +0x020**
（w / h）被写进 UITexture 的落点。同函数另有三条尺寸判据：

```
0x51D9EC  2c810411  sltiu $at, $a0, 1041        ; clut_size < 1041
0x51DA3C  04800075  bltz  $a0, →0x51DC14        ; px_size 非负
0x51DA44  3c010010 / 34210001 / 0081082a        ; px_size < 0x100001
```

失败分支 `0x51DC14` 的语义（逐条读过）：**清空整个 UITexture 对象**（+0x08/+0x0C/+0x10...
+0x3C 全清零、`sb 1, 44($s1)` 置"已删"标志）并 **`$v0 = 0` 返回**；调用者对返回值**不判**
（0x51C85C 的 `jal` 之后直接 `beq $zero,$zero → 0x51D8EC`，即 0x51C864 起就是整个函数尾部）。
⇒ 静态语义 = **"这张纹理被静默丢弃 + 读流位置停在半途"**。

### 1.1 这 4 条判据解释了什么、没解释什么

```
✓ 解释 W 2048：w=2048 ≥ 1025 ⇒ 0x51D9BC 直接拒绝 ⇒ 纹理被丢 ⇒ 黑屏。
✗ 解释不了 h=640：w=1024 / h=640 两条都 < 1025 ⇒ 过闸；
   px_size=0x501F0 < 0x100001 ⇒ 过闸；clut=1040 < 1041 ⇒ 过闸 ⇒ 静态上应"成功"。
✗ 也解释不了为什么 W2048 的读盘在 **frame 257** 就停（见 §2）。
```

---

## 2. ★ 实测根因：读流游标停在 PAK 内 428,032 B（= LBA 776,669）

数据全部来自对比运行（同一 gsrunner、同一 maxframes=6000）：

| 盘 | PAK `stored` | 容器 `px_size` | 读到最大 LBA | 读盘事件跨度 | PAK+Δ 处最大字节 |
|---|---|---|---|---|---|
| `GR_ZH123`（可用） | 400,659 | 262,160 | 804,733 | frame 0..5984 | — |
| `GROWCTL`（对照，PAK 长大 +66,144） | 466,803 | **262,160（不变）** | 804,852 | frame 0..5999 | — |
| `W2048` | 662,803 | 524,304 | **776,669** | **frame 0..257** | **428,032 B (0x68800)** |
| `W2048` + 本轮 gate 补丁 | 662,803 | 524,304 | **776,669** | **frame 0..257** | **428,032 B** |

```
★ LBA 776,669 = PAK 起始 LBA 776,460 + 209 扇区 = 428,032 B ⇒ 恰好是扇区对齐的读游标位置
★ W2048 盘的 39,802 条读盘事件与本轮补丁盘**逐条相同**（frame 0..257、maxLBA 776,669、最后三条
  都是 (257,776667)(257,776668)(257,776669)）⇒ 补丁对读流**零影响** ⇒ 补丁确实没被走到/不相关
```

### 2.1 这个位置是不是"卡的准确时刻"？—— 用可用盘做了对照核对

可用盘 `GR_ZH123` 在同一帧窗口内的读盘是**连续推进**的：

```
frame 242  LBA 776287..776309     ← MENU.IMG 头
frame 249  LBA 776438..776461     ← 正好读到 PAK 起始 776460
frame 250  LBA 776462..776485     ┐
frame 251  LBA 776486..776517     │
frame 252  LBA 776518..776545     │ PAK 记录 + 容器 的连续流
frame 255  LBA 776598..776627     │
frame 256  LBA 776628..776653     │
frame 257  LBA 776654..776669     ┘  ← ★ 与失败盘"停住"的位置**完全相同**
frame 260  LBA 776670..776700     ← 可用盘**继续**读下去
```

⇒ 两张盘在 frame 257 都到达 PAK+428,032；**可用盘继续（frame 260 起下一批），失败盘就到此为止**
（之后 5,743 帧、约 99 秒内**一次盘都没读**）。

### 2.2 卡死的下游后果（三判据 + 资源层证据）

| 盘 | PNG 截图 | GIF-upload 转储 | `newfontrevisedrs` | `weaponsanditems` | `WPNRPK74` | TLB Miss |
|---|---|---|---|---|---|---|
| GROWCTL（对照 ✓） | **191** | 1 | 2872 hits / 6 dumps | 2816 / 1 | 2930 / 1 | 0 |
| **W2048（✗）** | **0** | **0** | **0 hits / 0 dumps** | **0 / 0** | 2930 / 1 | 0 |

```
· frame 260 正是「atlas 容器开始被装载」的时刻（对照盘上 newfontrevisedrs 的**首次命中**在 frame 260）
· 失败盘上 newfontrevisedrs / weaponsanditems **一次都没在内存里出现过**（EE/IOP 皆无）
  ⇒ 它们的**文件数据根本没被搬上机**，不是"搬上来了但没用"
· WPNRPK74 只在 frame 144 出现（那是它自己在早期加载留下的字符串），frame 5998 还在被命中
  ⇒ 主循环仍跑满 6000 帧 ⇒ **是加载子系统停摆，不是游戏崩/被判定黑屏**
· HWSTAT（三次运行同口径）: Draw Calls 39588→**5812**；Copies 10969→**0**；Uploads 314→**2**
  ⇒ GS 侧几乎停止上传/绘制（Uploads 314→2 与 newfontrevisedrs/weaponsanditems 全缺一致）
· TLB Miss 全部 0 ⇒ 没有内存管理异常
```

### 2.3 ★ 已排除变量（本轮独立对照）

```
✓ 排除「PAK 长大 + 682 条条目 off 平移 + ISO 长大」：
  GROWCTL 盘同时做了这三件事（PAK 400,659→466,803、MENU.IMG 声明 +66,144、682 条 off 平移、
  ISO 804,768→804,852 扇区），实机跑满 6000 帧、读到 LBA 804,852、191 张截图 ✓
  ⇒ 唯一剩下的变量 = **图集容器本身变大**（524,304 B，16 段；对照盘容器一字未动）
✓ 排除「ISO 长度/声明不一致」：W2048 盘 size = PVD vol_space = 804,852 扇区，逐项 0 差 ✓
✓ 排除「1024 判据」：见 §3 探针
```

---

## 3. ★ 探针盘：补丁 + 三判据（本轮实测）

### 3.1 补丁（精确到字）

| 项 | 值 |
|---|---|
| 源盘 | `work\builds\GR_TEST_W2048\GR_TEST_W2048.iso`（该盘长度已由上一轮逐项核对自洽） |
| 探针盘 | `work\builds\GR_ROOT85\GR_ROOT85_gate.iso` |
| 站点 1 | VA `0x51D9BC` · ISO `0x4B123C` · 原字 `28610401`（`slti $at,$v1,1025`）→ 新字 `28610801`（`slti $at,$v1,2049`） |
| 站点 2 | VA `0x51D9C8` · ISO `0x4B1248` · 原字 `28410401`（`slti $at,$v0,1025`）→ 新字 `28410801`（`slti $at,$v0,2049`） |
| 理由 | 把 `UITexture::LoadPS2Img` 的 w/h 上界从 1024 抬到 2048，正好放行 W=2048 的图集；引擎其余参数是**运行时按 w 派生**的（`TEX0.TW = log2(w)`、`B' = (0x10000/w)<<2`），不需要配套改常量 |
| 断言 | 全盘逐字节差异 = **2 字节**（每站点只动立即数高字节）；两站点回读一致 ✓；`VA 0x416EE8` 映射锚点校验 ✓ |

### 3.2 三判据（补丁盘 vs 同参数对照盘）

两次运行参数完全一致：`-grmaxframes 6000 -grsnap 500 -grscanframes 4000 -renderer dx11`，
同一 gsrunner、串行、跑完确认退出（`exit=0`；按约定只当信号，不当判据）。

| 判据 | 对照盘（`GR_ZH123` 副本） | **补丁探针盘** | 结论 |
|---|---|---|---|
| 截图张数 | **11** | **0** | ✗ 无改善 |
| needle `newfontrevisedrs` | **1 hit / 1 dump** | **0 hit / 0 dump** | ✗ 无改善 |
| needle `weaponsanditems` | 2 hits / 2 dumps | **0 / 0** | ✗ 无改善 |
| needle `WPNRPK74` | 1 hit / 1 dump | 1 hit / 1 dump | 与对照同 |
| GIF-upload 转储 (`gsup_*`) | 1 个 | **0 个** | ✗ |
| TLB Miss | **0** | **0** | 无异常 |
| CDVD 读流 | frame 0..5984，maxLBA 804,733 | **frame 0..257，maxLBA 776,669** | ✗ 与未打补丁的 W2048 **逐条相同** |

⇒ **结论：探针盘与未打补丁的 W2048 盘在可观测层面完全等价 ⇒ 1~2 条指令（改尺寸判据）绕不开。**

---

## 4. 附带发现（对后续有直接影响）

### 4.1 容器在 RAM 里的真实形态（首次实证）

在可用盘 `GR_ZH123` 的 EE RAM 快照（`temp\dump_r83b\newfontrevisedrs_f00003268_eeram.bin`）里定位到：

```
容器在 RAM 的地址 0x006908B0（8 段结构逐字节 == 盘上容器，0x40010 B 全等 ✓）
  [0x000000] 01 00 00 00 00 00 00 10   ← PT   tag（nloop=1, nreg=1, flg=0）
  [0x000010] 00 00 00 00 00 00 00 00   ← A+D  (TRXPOS)
  [0x000020] 00 88 00 00 00 00 00 08   ← IMAGE tag（nloop=2048, eop=1）
  [0x000030] 段 0 像素 0x8000 B
  [0x008030] 段 1 的 PT/A+D/IMAGE（TRXPOS 的 SSAY=0x40）+ 0x8000 B
  ...                                   段 k 首行 = 64·k
  [0x040000] 00 80 00 00 00 00 00 08   ← 尾部 no-op tag（16 B）
⇒ 容器 = 8×(48 B GIF 头 + 0x8000 B 像素) + 16 B 尾 tag = 0x40010 ✓
⇒ 关键：像素缓冲在 RAM 里**就是盘上容器原样**（含每段的三个 tag）
```

⇒ 这是"容器变大 ⇒ 引擎读流停摆"的最直接物证：引擎搬的是**含 GIF 头的整块**，不是纯像素。

### 4.2 `LoadPS2Img` 的字节至字节拷贝循环（h=640 待查点）

```
0x51D828..0x51D8B4:
  每轮取 1 字节，展开成 16 B（andi/sll 把低/高 nibble 各自扩成 8 B "8h"/"1h" 模式）
  src += 1（$t2）; dst += 16（$t3 每轮 +0x10，循环体内再 +1）
  循环条件 0x51D8B8: a3 < (px_size>>1)，a3 每轮 +1
  ⇒ dst 的**低 16 位每轮恰好归 0**（低 8 位 +8+8 = 0x10，高 8 位不变）⇒ 256 B 步进
  ⇒ 0x51D8C0 的 `mult` 是死码（mflo 从不被读，与 0x51B974 同类）
```

对 h=640（容器 10 段 / `px_size=0x501F0` = 2 个 `B'=0x40000` 块）这条链的取数是否越界，
本轮**没有**拿到实机证据 ⇒ 见 §5.2，如实标注未定。

---

## 5. 结论与下一步

### 5.1 结论

```
① 「变大后卡死」的直接机制（已实证）：
   引擎在读/搬运 new_font_revised 的像素容器时，其**读流游标停在 PAK 内 428,032 B
   （LBA 776,669，扇区对齐）**，此后该盘上**所有**后续文件加载全部失败
   （newfontrevisedrs 与 weaponsanditems 一次都没进内存），
   GS 上传 314→2、Copies 10969→0、截图 0；主循环仍跑满 6000 帧、TLB Miss = 0。
   ⇒ 表现为"停在装载画面"，不是崩溃。

② 「1~2 条指令绕开」：**不可行（本轮已否证）**。
   已找到并实测了唯一一对"尺寸硬判据"（`LoadPS2Img` 的 4 条 `slti …,1025`），
   把 W/H 上界抬到 2048 后，探针盘的 CDVD 读流与未打补丁盘**逐条相同**、三判据全 0 改善。
   ⇒ 卡点发生在该判据**之前/之外**，改它无用。

③ 「h ≤ 512 硬上限」这个说法：**不成立**（判据其实是 w<1025 ∧ h<1025，且与本次卡死无关）。
   可用盘上 4 条判据的值就是 1025，对 1024×512 的现役图集恒真。
```

### 5.2 未定项（如实标注，避免后人重走）

```
· h=640 的失败点**本轮没有分离出来**：w=1024/h=640/px_size=0x501F0/clut=1040 逐条都过 §1 的
  全部判据，静态上应成功。⇒ 它要么与 W2048 同源（读流停摆），要么在 0x51D828 卷积循环里，
  要么在 SetTexturePkt 的分块记账（B'=(0x10000/w)<<2、+0x30）里。
  ★ 判定它需要**新的一次单变量实机**：h=513 + 容器 9 段（px_size=0x40140 一类），
    看读流是否同样停在 428,032 B。若同样停在 428,032 ⇒ 与尺寸无关、与"容器段数/字节数"有关。
· 428,032 B 这个数没找到代码常量（IOP RAM 里也没有该值）；它是否等价于某个
  固定读窗口/BIO 缓冲上界，**未定**。下一轮建议：用 `-grwatchlba 776660 64` 抓停摆前后的
  完整读请求（gsrunner 自带该开关），并抓停摆后的 EE/IOP RAM 快照（本轮探针盘的
  `dump_gate\WPNRPK74_f00004000_*` 已是 6000 帧状态，可直接比对）。
```

### 5.3 对"要装下 364 个缺字"的建议（沿用上一轮已成立的判断，本轮无反对证据）

```
· 不要动图集尺寸/容器（本轮再次证明这是唯一的致命变量）。
· 走 FONT.RES 记录路线（nrec 224/224/96 抬大 + 记录矩形指向任意 UV）——容器一个字节不动。
· 若必须扩容图集：先做 §5.2 的那一次单变量（h=513，9 段容器），
  在"读流是否停在 428,032"这一条上把机制钉死，再谈改造。
```

---

## 6. 本轮产出的盘与可复跑命令

```
探针盘 : work\builds\GR_ROOT85\GR_ROOT85_gate.iso   （W2048 + 2 字判据补丁）
对照盘 : work\builds\GR_ROOT85\GR_ROOT85_base.iso   （GR_ZH123 副本，同 harness 对照）

python work\tools\root_probe_gate.py work\builds\GR_TEST_W2048\GR_TEST_W2048.iso ^
        work\builds\GR_ROOT85\GR_ROOT85_gate.iso --sites "0x51D9BC 0x51D9C8"
python work\tools\root_run.py --iso work\builds\GR_ROOT85\GR_ROOT85_gate.iso ^
        --dump work\builds\GR_ROOT85\temp\dump_gate --maxframes 6000 --snap 500
python work\tools\root_run.py --iso work\builds\GR_ROOT85\GR_ROOT85_base.iso ^
        --dump work\builds\GR_ROOT85\temp\dump_base --maxframes 6000 --snap 500
python work\tools\root_atlas_layout.py <iso>          # 容器逐字节解剖
python work\tools\root_gsup2.py <dumpdir>             # GIF-upload 转储解剖
```

### 6.1 本轮结果快照（供核对）

```
补丁盘 run : exit=0 elapsed=102s  frames=6000  PNG=0   gsup=0   eeram=1  TLB=0
             needle newfontrevisedrs = 0 hits / 0 dumps ; WPNRPK74 = 1/1 ; weaponsanditems = 0/0
             cdvd.log = 39802 事件, frame 0..257, maxLBA 776669
对照盘 run : exit=0 elapsed=102s  frames=6000  PNG=11  gsup=1   eeram=3  TLB=0
             needle newfontrevisedrs = 1/1 ; WPNRPK74 = 1/1 ; weaponsanditems = 2/2
             cdvd.log = 60388 事件, frame 0..5984, maxLBA 804733
原始 W2048 : cdvd.log = 39802 事件, frame 0..257, maxLBA 776669   ← 与补丁盘逐条相同
```

*（本报告只写 `docs/REPORT_texture_limit_rootcause.md` 一个新文件；未覆盖任何既有文档，
未 commit、未切分支、未改 `third_party/orig/**` 与 `%LOCALAPPDATA%\PCSX2\**` 之外的东西；
探针盘与对照盘都在 `work\builds\GR_ROOT85\` 新建目录内。）*
