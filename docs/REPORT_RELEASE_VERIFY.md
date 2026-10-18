# REPORT_RELEASE_VERIFY.md —— `GR_ZH2400_FINAL.iso` 全量验收报告

* 验收对象：`work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso`
  （sha256 `d8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5`，1,648,164,864 B，ELF CRC **CFDB8C97**）
* 交付说明：`docs\RELEASE_NOTES_2400.md` · 身份证：`work\builds\GR_RELEASE\GR_ZH2400_FINAL.meta.json`
* 本轮写入范围：`work\builds\GR_RELEASE\**` + 本文件 + `docs\RELEASE_NOTES_2400.md`（其余全部只读）
* 回归判定：**无回归**。逐帧对照 191/191 相同、载荷逐字节 0 差异、差异窗口外 0 字节、ISO 尺寸不变。
  ⇒ **不阻断交付**。
* 未达成项：见 §D（4 项，全部因为**参照盘被外部清理删除**，均已给出等价或更强的替代验证）

---

## 0. 环境事件（影响可复跑性，必须记录）

| 时点 | C 盘可用 | 事件 |
|---|---|---|
| 本轮开工（16:10） | 2.60 GB | `GR_ZH124.iso` / `GR_F364.iso` / `GR_FA2400_K2*.iso` / `GR_ZH113b.iso` **已不在盘上**（更早的清理） |
| 16:27 | 3,122 MB | 起跑 6000 帧冒烟 |
| 16:30 | **46,243 MB** | ★ **外部大量删除**（非本执行者）：`GR_SPINFIX\SPINFIX_F4.iso`、`GR_REBUILD\GR_REBUILD2400_allpat.iso`、`GR_REBUILD2400_hashr{,_allpat}.iso`、`GR_COMBFIX\emu\**`、`GR_DFIX\*.iso`、`GR_LAYOUT\base\*.iso` 消失 |
| 16:44 | 44,492 MB | 本执行者清理自己的中间物（各 run 的 `mc\`/`bios\` 副本、`gsup_*.bin`、`*_eeram.bin`）回收 557 MB |

⇒ 盘上现存 ISO 只剩 9 张（2 张原盘 + 6 张产品盘 + 1 张未修基底）。
**这一条直接决定了 §D 的 4 个未达成项**；本报告对每一项都给了替代验证，且**没有用推断冒充实测**。

**另两条取证口径说明（如实）**：

* A 段分析的 `qt\logs\emulog.txt`（741,534 B / 6,535 行）**已被用户的下一次会话覆盖**
  （16:38:30 起新会话，日志被截断重写）⇒ **源头不可再读**。A 段的全部读数是在覆盖前完成的，
  数字落在本报告 §A；关键结论已用用户 12 份 dump 的 `meta.txt/regs.txt` 复核过。
* 本执行者**全部 6 次模拟器起跑**（2 次 6000 帧 + 4 次现场）**都没有他人 pcsx2 实例**
  （`runs\**\OTHERS_RUNNING.txt` 一个都没有生成；用户那次 `pcsx2-qt` 起于 16:38:30，晚于我最后一次跑完的 16:34:37）
  ⇒ **独占纪律成立，性能/帧数据无争用污染**。

---

## A. 用户新日志复核（只读）

**素材**：`work\builds\GR_HOOKEMU_QT2\qt\logs\emulog.txt`（741,534 B / 6,535 行 / **单次会话**）
+ `work\builds\GR_HOOKEMU_QT2\qt\hookdumps\**`（12 份落盘）

### A.1 这次跑的是哪张盘（先钉死）

```
L78  [0.2348] isoFile open ok: …\work\builds\GR_COMBFIX\COMBFIX_C.iso
L99  [0.2817] CRC: CF9B8C97
L243 [1.2100] ELF Loading: cdrom0:\SLUS_206.13;1, Game CRC = CF9B8C97, EntryPoint = 0x00100008
```
⇒ 是 `COMBFIX_C.iso`（CRC `CF9B8C97`），与 2400 盘**同一组补丁**（F4+OOMFIX+F7），只是基底线不同。

### A.2 ① 结算前有没有 `Trap` / `Unrecognized` / 跳飞 / 淹没刷屏

| 检查 | 命令 | 结果 |
|---|---|---|
| `Trap` | `Select-String -SimpleMatch 'Trap'` | **0 行** |
| `Trap exception` | 同上 | **0 行** |
| `Unrecognized` | 同上 | **0 行** |
| `ReportErrorAsync` / `recLUT` / `panic` / `Assertion` | 同上 | **0 / 0 / 0 / 0 行** |
| 异常自动落盘 | `hookdumps\*` 目录名 | **0 个** `reason=exception*`（12 份**全是** `hotkey_f10`，即用户自己按 F10） |
| 跳飞 | 块入口直方图（见 A.3） | 无单一 PC 支配；本会话 4 份 dump 的 `0x102180/0x1021A0/0x1021D0` 命中 **0/0/0** |
| 淹没刷屏 | 行型归一化计数 | 最大重复型是 `HookWatch: watch hits=…`（**5,465 行 = 设计行为**，`log_every=2000`，共 1,093 万次监视写）；**无**异常刷屏 |

**会话时间线（关键事件）**

| 时刻 | 行 | 事件 |
|---|---|---|
| 0.23 s | 78/99 | 开盘 + ELF 载入 + CRC CF9B8C97 |
| 10.96–12.54 s | 1641–1649 | 开场 FMV |
| 72.91 s | 2434 | `RSGameStateMgr::SaveGame() IN/OUT`（存档） |
| 189.83 / 205.70 s | 3443–3457 / 3591–3604 | free()+大块插链 的 TLB 突发（见 A.4） |
| 268.72 / 271.16 s | 4110–4129 | **F4 签名对**（`pc=0x1024d0` + `0x102584`，各 1 轮就 bail） |
| 316.46 s | 4585–4602 | 又一次 free()+插链 突发（**TLB 打印配额在此打满 50 行**） |
| 317.12–318.97 s | 4617/4619 | **FMV**（关卡/任务结算过场） |
| **336.54 s** | **4646** | **`RSGameStateMgr::Shutdown() OUT`** ← 游戏状态被正常销毁（= 关卡结束/退出，与"完成任务→结算"一致） |
| 350.18 s | — | 用户第 4 次按 F10（frame 17498） |
| 418.18 s | 尾部 | `(VMManager) Pausing...` → `Releasing host memory`（**用户正常暂停退出**） |
| 全程 | — | 跑到 **frame 21,535**（≈418 s 墙钟），无 Trap |

### A.3 ② `TLB Miss` 行数与内容

* **50 行 = PCSX2 的打印上限**（`vtlb.cpp` 里 `if (spamStop++ < 50)` 写死），**不是"只有 50 次"**。
* 分成 **4 个突发**，每个突发都在 **0.002 s 内**结束（是**一次性**事件，不是循环）：

| 时刻(s) | 行数 | PC（块首） | 地址 | 归属 |
|---|---|---|---|---|
| 189.8334–189.8347 | 15 | `101d10 101dac 101dd8 101de4 101e08 101e34 101e6c 102008` | `20014aa / fecd15c8 / fecd15d0 / fecd15d4 / 14 / 10` | free()+大块插链（毒化那一刻） |
| 205.6970–205.6972 | 14 | 同上 + `101fe0 102000` | `14e228f7 / 14e228ff / 14e22903 / 14 / 10 / fecd15c8…` | free()+插链（**第三个坏指针**） |
| **268.7176 / 271.1626** | **2 + 2** | **`1024d0` / `102584`** | `fecd15c8 / fecd15d4` | **malloc binmap 扫描 —— F4 正常工作签名**（各只 1 轮就 bail，**没有第 3 行**） |
| 316.4550–316.4560 | 17 | `101fe0 102000 102008 101e34` | `fecd15c8 / fecd15d4 / 10` | free()+插链 |

* ★ **关键否定证据**：整份日志的 TLB 行里 **没有任何一行** 的 PC 是 `0x102180 / 0x1021A0 / 0x1021D0`
  —— 也就是**用户原先那种"own-bin 三块纯读自旋"没有再出现**。
* 与 `REPORT_COMBFIX.md` §4.1 的口径对照：那次卡死日志里 `0x1024d0/0x102584` 也是**成对 2 行**出现
  （179.9 / 250.8 / 264.4 / 267.4 s）——**同型**；区别是那次最后被 `0x102180→0x1021A0→0x1021D0` 的
  三块循环吃掉，这次没有。

### A.4 ③ `F7` / `F4` / `OOMFIX` cave 是否被执行（**部分未达成，如实登记**）

**先说做不到的**：用户这版钩子（`qt\hook\hook_config.ini`）**不记录逐 PC 执行命中**
（`trace_pc` 未启用；`trigger` 12 个 PC 只用于落盘且 `dump_on_trigger=0`）⇒
**用户日志里数不出 cave 命中次数**。已核过：
* 全 12 份 `ring.txt`（每份 262,144 条、只记 `watch=0x00500000-0x00580000` 内的**写**）里
  **没有**任何 `pc=005500xx / 005DECxx / 0041A3xx` 记录；
* 全 12 份 `regs.txt` 的 `recent_block_pcs`（4,096 条块入口）里同样 **0** 命中；
* 但这**不能**当作"没执行"的证据（ring 只覆盖落盘前 ~116–1000 帧、且只记写、cave 基本只读不写）。

**能做到的（本次给出的最强证据）**：

1. **补丁确实进了 RAM 且没被旧存档盖掉**（读用户 frame 17498 的 `ee_ram.bin`，10/10 逐字相符）：

   | VA | RAM 实测 | 期望 | 判定 |
   |---|---|---|---|
   | `0x00102588`（F4 站点） | `0x081068D7` | `0x081068D7` | ✓ |
   | `0x001021D4`（F7 站点） | `0x08177B31` | `0x08177B31` | ✓ |
   | `0x00539174`（OOMFIX 站点） | `0x08154012` | `0x08154012` | ✓ |
   | `0x0041A35C` / `0x0041A378`（F4 cave 首/末字） | `0x0322082B` / `0x08040964` | 同 | ✓ |
   | `0x005DECC4` / `0x005DECE0`（F7 cave 首/末字） | `0x00E2082B` / `0x08040878` | 同 | ✓ |
   | `0x00550048`/`0x00550060`/`0x0055006C`（OOMFIX cave） | `0x10400005`/`0xAE600004`/`0x0814E4A8` | 同 | ✓ |
   | 闸门 `0x00416EE8` / `0x005656A4` | `0x2CA900BA` / `0x2D6C00BA` | 同 | ✓ |

2. **F4 被"用上"的直接签名**：268.7 s / 271.2 s 各出现 **恰好 2 行** `pc=0x1024d0` + `0x102584`
   （binmap 扫描撞到坏链头 → F4 在 `0x102588` 拦下 → 退到 top 切分继续）⇒ **至少 2 次**。
3. **F7 是否被触发**：本次**没有** own-bin 三块自旋签名 ⇒ **只能说"未观察到需要 F7 的现场"**，
   **不能**说 F7 执行过或没执行过。
4. **OOMFIX**：无任何可判读痕迹（同上的钩子限制）⇒ **未达成**。

### A.5 ④ 有没有新的异常模式（对比 `REPORT_COMBFIX.md` §4 矩阵）

| 项 | §4 矩阵（修复前/本机现场） | 用户本次（修复后/实机） | 判定 |
|---|---|---|---|
| `0x102180→0x1021A0→0x1021D0` 三块纯读自旋 | o1/o2/o3/d1 **全部死在这条循环** | **0 次**（TLB 无该 PC、块入口直方图 0/0/0） | ★ **消失** |
| `0x1024d0/0x102584` 成对 2 行（F4 签名） | 有（4 次） | **有（2 次，各 2 行）** | 同型 ✓ |
| free()+大块插链 的坏指针突发 | 有（139.3 / 224.7 / 237.8 s） | **有（189.8 / 205.7 / 316.5 s）**，坏地址同型（`0x14e228f7` 与旧日志完全相同） | ★ **损坏源未消失** |
| `Trap` | a1 盘 70,266 次 | **0 次** | ★ 消失 |
| 结算前致命 EE 异常 | 0（旧日志也是 0） | 0 | 一致 |
| 新形态 | — | **无新增异常模式** | — |

> ★ **诚实结论**：底层"堆被写坏（野 free + 把垃圾值插进桶链）"这件事**依然在发生**，频率与旧日志同量级；
> 本轮修复改变的是**它不再把游戏钉死**：桶链扫描被截断、分配器恢复到 top 切分继续跑，
> 于是 317 s 还能放 FMV、336.5 s 还能正常 `Shutdown()` 游戏状态、418 s 用户主动退出。

### A.6 A 的结论

**本次实机与"修复有效"一致 ✓**，具体：

1. 三件套补丁**确实在 RAM 里、且在整个会话里没被盖掉**（frame 17498 逐字回读 10/10）；
2. 原来的**致命自旋签名（三块纯读循环）0 次**，而修复前它必然出现；
3. F4 的"拦下坏链头"签名出现 **2 次**，与设计一致；
4. 全程 `Trap`/`Unrecognized`/`ReportErrorAsync` **0**，无异常自动落盘，无刷屏；
5. 会话以 `RSGameStateMgr::Shutdown()` + 正常暂停退出结束，跑到 frame 21,535
   ⇒ **与"任务完成能正常进入结算"的用户陈述一致**；
6. **保留意见两条**：(a) `TLB Miss` 打印配额在 316.455 s 就打满 ⇒ **之后的 miss 不可见**，
   "没有第 3 行"只在配额内成立；(b) 钩子没做 PC 级执行追踪 ⇒ **cave 命中次数数不出来**（见 A.4）。

---

## B. 对 `GR_ZH2400_FINAL.iso` 的全量验收

### B1. 三闸门 / 图集不变式 / 差异窗口 / 尺寸

```powershell
& $py work\builds\GR_RELEASE\tools\rel_identity.py --final work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso `
      --src work\builds\GR_COMBFIX\COMBFIX_2400.iso `
      --base work\builds\GR_REBUILD\GR_REBUILD2400.iso `
      --meta work\builds\GR_COMBFIX\COMBFIX_2400.meta.json --out work\builds\GR_RELEASE\temp
& $py work\builds\GR_RELEASE\tools\rel_atlas_base.py --iso work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso `
      --base work\builds\GR_REBUILD\GR_REBUILD2400.iso `
      --allpat work\builds\GR_REBUILD\GR_REBUILD2400_allpat.iso --out work\builds\GR_RELEASE\temp
```

| 判据 | 数字 | 判定 |
|---|---|---|
| final == 候选盘 `COMBFIX_2400.iso` | 差异字节 **0**（run 数 0） | ✓ |
| sha256(final) == sha256(候选) == meta | `d8007873…b2ab5` | ✓ |
| 尺寸不变 | 1,648,164,864 == 基底 == meta | ✓ |
| 差异 100% 落在声明窗口 | **78 B / 25 run**，窗口内 **78/78**，**窗口外 0 B** | ✓ |
| ELF 指纹 | lba 295 / 37,453,732 B / sha256 `6fce4f45…` / **xorCRC CFDB8C97** | ✓ |
| 站点字回读（3 条） | `0x102588=081068D7`、`0x539174=08154012`、`0x1021D4=08177B31` | ✓ |
| 闸门字回读（4 条） | `416EE8/417160/41751C/5656A4` 全 = `…00BA` | ✓ |
| **三闸门** w<1025 | **w = 1024** | ✓ |
| **三闸门** `px_size == w*h/2+16` | **329744 == 1024*644/2+16** | ✓ |
| **三闸门** `(w*h/2)%2048 == 0` | **0** | ✓ |
| `px_size ≤ 329,744` | 329,744 | ✓ |
| 容器/段/payload | 329,728 B / 11 段 / payload **329,200 == w*h/2 − 11*48** | ✓ |
| 图集平面 == 基底 | 面偏移字节 **0**；逐槽 **2350/2350** 逐 texel 相同；ink 141,022 == 141,022 | ✓ |
| 槽 0..2349 几何 | 越界 **0** / 格位重复 **0** / 不同格位 **2350**；用到行 0..36；**V1_max = 627 ≤ 644** | ✓ |
| allpat 2350 槽全解码 | **未达成**（探针盘被删，见 §D1） | — |

### B2. `dump_font` 全套口径

```powershell
& $py work\builds\GR_RELEASE\tools\rel_font_dump.py --iso work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso
#   → 驱动工程既有 rb_verify_k2.py（判据代码一字不动），只把它的 OUTDIR 改到本轮目录
```

| charset 口径 | 采样窗 | 错误 | 空白 | 截断 | 越窗 | 警告 | 判定 |
|---|---|---|---|---|---|---|---|
| **全量**（`pair_of 2350`） | 2,894（对偶 2350 + FT 544） | **473** | 473 | 64 | **0** | 2 | 473 = **保留槽 473 个**（1872..2344） |
| **只含有字形槽** 0..1871（1872 条） | 2,416（对偶 1872 + FT 544） | **0** | **0** | **0** | **0** | 2 | **几何体检 ok ✓** |

* 容量：全量 `capacity 2350 / used 2350 / free 0`；live `used 1872 / free 478`；`lead = 0xA1..0xB9`
* **保留槽单列**：`1872..2344` 共 **473** 个，实测**全空**（有墨 0 个）✓
* **有字形槽**：现役 `0..1735` 空白 0 个、r83/r84 `1736..1871` 空白 0 个、借槽 5 个 ⇒ 合计 **1,877**
* **借槽逐 texel == 模板**（handoff JSON + 自制 ✕）：✓，墨量 `2345:69 / 2346:60 / 2347:31 / 2348:58 / 2349:25`
* **文本引用槽位**（缺字形 = 引用了无字形槽）：

  | 容器 | blob | 引用对偶槽 | 槽 > 1735 的 | 落在保留段 1736..2344 的 |
  |---|---|---|---|---|
  | `EN_STRINGS.RES@MENU` | 128,545 B | 1,131 | 5 个 `[2345..2349]` | **0** ✓ |
  | `EN_STRINGS.RES@GR` | 128,668 B | 1,131 | 5 个 `[2345..2349]` | **0** ✓ |
  | `EN_SPECIAL_FEATURE.XML` | 116,486 B | 1,381 | 4 个 `[2345..2348]` | **0** ✓ |

* **ASCII 表 182 条**：把 K2 轮落盘的逐条证明 `GR_FA2400_K2\temp\dump_k2_final\ascii_182_records.json`
  拿到**成品盘**上重算（FT 矩形 + 该矩形内墨量 + `equal` 标记）⇒ **182/182 ✓**
  （另：仍留在 `x≥992` 条带上的 **21/21** 条与基底逐 texel 相同）
* FONT.RES：**3 faces / 544 条记录**（与基底一致）

### B3. 载荷级旧码扫描 = 0

```powershell
& $py work\builds\GR_RELEASE\tools\rel_text.py --iso work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso `
      --base work\builds\GR_REBUILD\GR_REBUILD2400.iso --out work\builds\GR_RELEASE\temp
```

| 容器 | ★ 载荷级 `0xB1..0xB9` 出现在**单字节位** | 全 blob 口径（含结构区/陈旧尾巴） |
|---|---|---|
| `MENU:RES` | **0 处 ✓** | 7 处（全 `0xB2`） |
| `GR:RES` | **0 处 ✓** | 7 处（全 `0xB2`） |
| `MENU:SF` | **0 处 ✓** | 0 处 |

（判据是"**没有裸字节**"，不是"没有这些字节"——迁移后它们会作为**对偶 lead** 合法出现。）

### B4. 逐字符一致（不符 0）

| 判据 | `MENU:RES` | `GR:RES` | `MENU:SF` |
|---|---|---|---|
| 条目数（vs 基底） | 2232 == 2232 | 2232 == 2232 | 595 == 595 |
| **载荷逐字节相同**（更强的"逐字符一致"） | **不同 0** ✓ | **不同 0** ✓ | **不同 0** ✓ |
| 解压 blob 长 | 128,545 == 基底 | 128,668 == 基底 | 116,486 == 基底 |
| 全量解码字符数 | 36,819（CJK 26,700） | 36,819（CJK 26,700） | 11,696（CJK 3,429） |
| **未解析字节** | **0** ✓ | **0** ✓ | **5** ⚠ |

* `MENU:SF` 的 **5 处** 全部是同一个字节 **`0xA4`**（"配不出对的前导"，即 `0xA4` 后面跟的不是合法 trail
  0xA1..0xFE，而是 ASCII `M/2/5` 或 `0x82/0x98`），分布在 `node#800 / #870 / #910 / #930` 等 5 处，
  形态一律是 `…△⟨A4⟩M16…` / `…△⟨A4⟩200…`。
* **这是上游既有缺陷，不是本轮引入**：`docs\REPORT_SENTINEL_FIX.md` §4 已登记
  「`EN_STRINGS.RES@MENU/GR` 的 XML 侧另有 5 处"配不出对的前导"（`0xA4`，上游既有），本轮原样保留」，
  §8.1 第 4 条再次列为"未处理、非本轮范围"。本次独立复核**恰好也是 5 处** ⇒ 与登记一致。
* 由于 FINAL 与基底在这一层**逐字节相同**，该缺陷**与本次修复无关**。

> 说明（为什么不用 `migrate_legacy_audit.py --ref-iso`）：该工具 `[B]` 段假定 `--ref-iso` 是
> **迁移前（GATE 0xB1）** 的盘；这样的盘**已全部不在磁盘上**（见 §0/§D4）。
> 拿一张**已迁移（0xBA）** 的盘当基底去解，会得到 385 / 385 / 41 处**假差异**（基底侧被解成乱码，
> 例如 `在中央基地内独自停留按有间最长…`）。本报告因此改用**载荷逐字节相同 + 全量解码 0 未解析**
> 两条独立判据替代，并在 §D4 如实登记原判据未达成。

### B5. 实机 6000 帧（独占）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_RELEASE\tools\rel_smoke.ps1
```

* 独占纪律：起跑前轮询 `Get-Process pcsx2*` ⇒ **0 个他人实例**；跑后残留 **0**；`OTHERS_RUNNING.txt` 未生成。
* 模拟器：`third_party\emu\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe`
  （sha256 `e58253069bee248fa46acf56873540d096bb3b816f0a3b40783bfa3074813ee6`）

| 判据 | 本盘 `GR_ZH2400_FINAL` | 基底 `GR_REBUILD2400` | 目标 |
|---|---|---|---|
| 截图张数 | **191** | 191 | **≥190 ✓** |
| 去重画面 | 169 | 169 | 一致 ✓ |
| 帧区间 | 270..5970 | 270..5970 | — |
| `TLB Miss` | **0** | 0 | **0 ✓** |
| `Trap exception` | **0** | 0 | **0 ✓** |
| `Unrecognized op` | **0** | 0 | **0 ✓** |
| `Pausing` | **0** | 0 | — |
| 结束标志 | `=== run end, frames=6000 ===` | 同 | 跑完 ✓ |
| cdvd 事件 / 帧域 / maxLBA | 50,819 / 0..5861 / 804,765 | 完全相同 | 一致 ✓ |
| exit code / 墙钟 | 0 / 102 s | 0 / 106 s | — |
| 到中文界面 | ✓ `runs\smoke_GR_ZH2400_FINAL\snap_f00004500.png`：**输入名字** / 全键位 / **确认** / 底栏「输入你的名字。 删除 返回 接受」 | 同 | ✓ |

* **拉丁/ASCII 表完好（§16.4 判据 1&2 的实机证据）**：该帧上 `A..Z`、`0..9`、`_ . ! # @ - ? $`
  与 `△`(返回) / `✕`(接受) 全部可读；另外把成品盘图集里的 `V W X Y Z 0 1` 三个 face 全部画出来
  （`temp\ascii_glyphs.png` + `.json`）逐个字形正确、有墨。
* ⚠ 观察（**非判据、非回归**）：同一帧里第三行第 6 键（几何位置 = `X`）**实拍字形偏稀疏**，
  而图集里的 `X`（码位 `0x58`，rect `1016,208,1024,224`，墨 30）是**正确的**。
  该帧与基底**逐字节相同**，故**继承自基底**；**根因未定位**，登记为待查项（不影响三闸门/文本/结算）。

### B6. 逐帧 sha256 与基底对照

```powershell
& $py work\builds\GR_OOMFIX\tools\oomfix_frames.py `
      work\builds\GR_RELEASE\runs\smoke_GR_ZH2400_FINAL `
      work\builds\GR_RELEASE\runs\smoke_GR_REBUILD2400 --json work\builds\GR_RELEASE\temp\frames_vs_base.json
```

```
A = runs\smoke_GR_ZH2400_FINAL : 截图 191（去重 169）/ 帧 270..5970 / TLB 0 / Trap 0 / op 0 / Pausing 0
B = runs\smoke_GR_REBUILD2400  : 截图 191（去重 169）/ 帧 270..5970 / TLB 0 / Trap 0 / op 0 / Pausing 0
共同帧 191；逐帧 sha256 相同 191 / 不同 0
不同帧: [] ⇒ 逐像素 0 差异
```

* 与 `RB_REBUILD` 的 `cap_results.py` 交叉核对：`[cmp] 同名可比 191 张 ; 逐字节相同 191 (100.0%) ; 不同 0`
* ⇒ **0 帧差异**，无需像素级落点分析。**无回归。**

### B7. 同现场回归（未修基底 vs 本盘；两套现场）

```powershell
& $py work\builds\GR_COMBFIX\tools\combfix_statefix.py `
      --state <原存档> --meta work\builds\GR_COMBFIX\COMBFIX_2400.meta.json `
      --iso work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso `
      --out work\builds\GR_RELEASE\states\<新存档>.p2s --spec work\builds\GR_RELEASE\temp\statepatch_*.json
powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_RELEASE\tools\rel_regress.ps1
```

> 存档必须逐盘重打：`.p2s` 里含**整块 32 MB 主存**，不重打就等价于"没打补丁的盘"。
> 本次两支成品臂的存档由 `combfix_statefix.py` 生成，**逐字回读自证 16 条全 OK**，
> 与输入存档差异 **78 B**（恰等于补丁字节数）。

**现场一：`S1`（用户原始坏桶 126）**

| 臂 | 盘 | 存档 | 帧 | **Trap** | Unrecog | TLB | 结束 |
|---|---|---|---|---|---|---|---|
| 未修 | `LAY_fix1_bytecount.iso` | `S1_bin126_user.p2s` | 46 | **70,266** | 58 | 2 | 死在异常风暴 |
| **本盘** | **`GR_ZH2400_FINAL.iso`** | **`states\S1_FINAL.p2s`** | **300** | **0** | **0** | 2 | **`run end, frames=300` ✓** |

* 本盘该臂 hook 命中：`0x41A35C`（F4 cave）**1** 次、`0x550048`（OOMFIX cave）**14** 次、`0x539110`（解压器）**14** 次。

**现场二：`S1b`（等价新现场 = 桶 121 毒化 `0x6ED47823` + 低端 `0x8..0xF/0x14..0x17` 清零）**

| 臂 | 盘 | 存档 | 帧 | Trap | TLB | 最后 512 条块入口里的三块循环 | 结束 |
|---|---|---|---|---|---|---|---|
| 未修 | `LAY_fix1_bytecount.iso` | `S1b_bin121_low0.p2s` | 60 | 0 | 2 | **`0x102180`×22 / `0x1021A0`×21 / `0x1021D0`×21** = 纯读死循环 | 帧数不推进 |
| **本盘** | **`GR_ZH2400_FINAL.iso`** | **`states\S1b_low0_FINAL.p2s`** | **60** | **0** | 8 | **`0/0/0`**，块入口回到游戏逻辑（`0x42C188 / 0x42E070 / 0x42E158 …`） | **`run end, frames=60` ✓** |

* 本盘该臂 hook 命中（与 `REPORT_COMBFIX.md` §4.2 的 `o4_C_S1b` **逐项同值**）：

  | PC | 含义 | 次数 |
  |---|---|---|
  | `0x5DECC4` | **F7 cave 进入** | **3** |
  | `0x1021E0` | **F7 bail → 既有"换下一个桶"出口** | **3** |
  | `0x41A35C` | **F4 cave 进入** | **1** |
  | `0x550048` | **OOMFIX cave 进入** | **14** |
  | `0x539110` | 解压器 | 14 |
  | `0x10269C` | malloc 正常返回 | **2,031** |

⇒ **"未修死、修复出"成立 ✓**（两套现场都是单变量对照：同存档、同输入、同模拟器，只换盘）。

### B8. 补丁存活（跑到第 N 帧回读补丁字）

```powershell
& $py work\builds\GR_SPINFIX\tools\spinfix_ramcheck.py `
      --ram work\builds\GR_RELEASE\runs\smoke_GR_ZH2400_FINAL\win_f00005970_eeram.bin `
      --meta work\builds\GR_COMBFIX\COMBFIX_2400.meta.json
```

```
site  F4     0x00102588 = 081068D7 (期望 081068D7) OK
site  OOMFIX 0x00539174 = 08154012 (期望 08154012) OK
site  F7     0x001021D4 = 08177B31 (期望 08177B31) OK
cave  F4     0x0041A35C  9 字：全部相符 OK
cave  OOMFIX 0x00550048 11 字：全部相符 OK
cave  F7     0x005DECC4  9 字：全部相符 OK
⇒ 补丁在运行到该帧时仍在（OK）
```
* 现场 RAM：`win_f00005970_eeram.bin`（33,554,432 B，第 5970 帧落盘）⇒ **29 个字逐字相符 ✓**

---

## C. 交付物

| 交付物 | 路径 | 要点 |
|---|---|---|
| **成品盘** | `work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso` | 与 `COMBFIX_2400.iso` **逐字节 0 差异**；sha256 `d8007873…b2ab5`；md5 `d24c324e…da2c`；CRC **CFDB8C97**；1,648,164,864 B |
| **身份证** | `work\builds\GR_RELEASE\GR_ZH2400_FINAL.meta.json` | 基底链 4 步 / 三件套站点表（站点+cave 字节）/ 闸门回读 / 全部验收指标索引 / 残余与未达成项 |
| **交付说明** | `docs\RELEASE_NOTES_2400.md` | 用户可感知变化 / 怎么用（新 CRC + 旧即时存档不适用）/ 7 条已知残余 / 复现与取证（含钩子版 + `hook_config_next.ini`） |
| **本报告** | `docs\REPORT_RELEASE_VERIFY.md` | A/B 全部数字 + 未达成项 + 跨机验证最小步骤 |
| 证据目录 | `work\builds\GR_RELEASE\temp\**` | `rel_identity.{json,txt}` / `rel_atlas_base.{json,txt}` / `rel_font_dump.{txt}` + `rbverify\**` / `rel_text.{json,txt}` / `frames_vs_base.json` / `ascii_glyphs.{png,json}` |
| 实机现场 | `work\builds\GR_RELEASE\runs\**` | `smoke_GR_ZH2400_FINAL`（191 截图 + emulog + 5970 帧 RAM）、`smoke_GR_REBUILD2400`、`reg_{a1,o1,p1,p2}_**`（含 `exectrace_tail.txt` / `hooklog.txt`） |
| 复跑脚本 | `work\builds\GR_RELEASE\tools\**` | `rel_identity.py` / `rel_atlas_base.py` / `rel_font_dump.py` / `rel_text.py` / `rel_smoke.ps1` / `rel_regress.ps1` / `probe_ascii.py` / `probe_a4.py` |

---

## D. 未达成项（如实列，全部有替代验证）

| # | 未达成项 | 原因 | 替代验证（本报告已给） |
|---|---|---|---|
| **D1** | `allpat` **2350 槽全量图案解码** | 探针盘 `GR_REBUILD\GR_REBUILD2400_allpat.iso` 与 `…_hashr_allpat.iso` **被外部清理删除**（§0）。该检查的本质是"验证**槽↔格位映射方案**"，探针盘是唯一载体，**无法离线重建**（重建要重跑造盘链） | ① 槽几何独立核对：`0..2349` 越界 0 / 格位重复 0 / 不同格位 2350（`rel_atlas_base.py [B]`）；② K2 轮自己的 `allpat_decode.json` 记录为 **2350** 全解（几何与 charset 相同）；③ 借槽 5 个 + 保留槽 473 个的**定向寻址**实测正确 |
| **D2** | ASCII 182 条「逐 texel == **GR_ZH124**」 | `GR_ZH124.iso` 已不在磁盘上 | 把 K2 轮**落盘的逐条证明**（`ascii_182_records.json`：face/idx/code/base 矩形/new 矩形/墨量/equal）拿到**成品盘**上重算 ⇒ **182/182 ✓**；再叠加"成品盘图集与**同几何直接基底**逐 texel 2350/2350 相同" |
| **D3** | r83/r84 槽 `1736..1871`「逐 texel == **GR_F364**」 | `GR_F364.iso` 已不在磁盘上 | 136 槽**全部有墨**（空白 0）+ 与**同几何直接基底**逐 texel 相同（`2350/2350` 覆盖了这段） |
| **D4** | `migrate_legacy_audit.py [B]`「基底闸门逐字符一致」 | 需要**迁移前（GATE 0xB1）** 的参照盘，此类盘**已全部被删**；拿已迁移盘当基底会产生 385/41 处假差异 | ① 载荷**逐字节**相同（比"解码后逐字符相同"更强）✓；② 载荷级裸旧码 **0** ✓；③ 全量解码未解析字节 = 0（`MENU:SF` 的 5 处是**已登记的上游缺陷**）✓ |

### 另有 1 项"未定位"（不是判据，但如实登记）

* **键盘 `X` 键实拍字形偏稀疏**：图集里的 `X` 正确、该帧与基底**逐字节相同**（⇒ 继承自基底、非本轮引入），
  **根因未定位**。状态：`未定位`，不影响三闸门 / 文本 / 结算。

---

## E. 交付候选的**实机进行中**观察（provisional，非完成判据）

**发现时点**：本轮验收收尾时（16:48）读到用户**新开的一次实机会话**正在跑
**`work\builds\GR_COMBFIX\COMBFIX_2400.iso`** —— 它与本次交付候选 `GR_ZH2400_FINAL.iso`
**逐字节相同**（sha256 均为 `d8007873…b2ab5`）。这不是我安排的跑，但它是**交付字节的真机样本**。

快照来源：`work\builds\GR_RELEASE\temp\userlog_LIVE_2400\emulog_snapshot.txt`（只读复制；会话仍在进行）

| 读数 | 值 |
|---|---|
| 盘 / CRC | `COMBFIX_2400.iso` / **CFDB8C97**（= 交付候选） |
| 已跑到 | **frame 33,330** / 557 s（快照时点） |
| `Trap` | **0** |
| `Unrecognized` | **0** |
| **`TLB Miss`** | **0** ← 比 LAY 线那次（打满 50 行）更干净 |
| `Pausing` | 0（会话进行中） |
| 进度事件 | 555.0 s 有一次 **FMV**（关卡/结算过场） |
| 结束标志 | 尚无（会话未结束） |

**结论（谨慎）**：这是**进行中**的样本 ⇒ **不作为 §B5 的替代**，只作为"交付字节在真机上跑得动、
前 33,330 帧 0 Trap / 0 TLB"的**旁证**。会话结束后建议再取一次 `emulog.txt` 与（若按 F10）`hookdumps`，
用本报告 §F 的第 5 步判据复核。

---

## F. 若要在**别的机器 / 别的模拟器**上验证：最小步骤

1. **校验文件**（任何 OS）：
   `sha256(GR_ZH2400_FINAL.iso) == d8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5`，
   大小 `1648164864`。不符就别往下做。
2. **确认补丁在盘上**（不需要模拟器）：取 ISO 根目录记录 `SLUS_206.13`（LBA 295，37,453,732 B），
   在 ELF 文件偏移 = `VA − 0x6C780 − 295*2048` 处读 4 字节小端，应为：
   * `VA 0x00102588 = 0x081068D7`
   * `VA 0x001021D4 = 0x08177B31`
   * `VA 0x00539174 = 0x08154012`
   * 闸门 `VA 0x00416EE8 / 0x00417160 / 0x0041751C / 0x005656A4` 的低字节全 = `0xBA`
3. **模拟器读 CRC**：启动日志里必须出现 `CRC: CFDB8C97`。**不是这个值 ⇒ 你跑的不是这张盘。**
4. **不要用旧的即时存档**（会连同 32 MB 主存把旧代码盖回来）。用记忆卡存档或从关卡开头进。
5. **判"修好没有"的最短路径**：打到"完成全部目标 → 任务完成提示 → 继续确认/等结算"。
   * 能进结算/能继续玩 = 好；
   * 日志里出现 1–2 行 `TLB Miss (pc=0x1024d0 / 0x102584)` **属正常**；
   * 出现 **`0x102180 → 0x1021A0 → 0x1021D0` 反复循环** 或画面定死 = 坏（请把 `emulog.txt` + 盘 sha256 发回）。
   * ⚠ PCSX2 的 `TLB Miss` **只打 50 行**，所以"日志里没有第 3 行"只在配额内成立；要更硬的证据用 hookdumps。
6. **要 PC 级证据**：用 `work\builds\GR_HOOKEMU_QT2\qt\pcsx2-qt.exe`（自带钩子），
   按 `work\builds\GR_SPINFIX\hook_config_next.ini` 覆盖 `qt\hook\hook_config.ini`
   （`watch = 0x0055B7A0-0x0055C000`、`ring_entries = 2097152`、`log_every = 500`、`max_dumps = 3`），
   异常时**按 F10** 落盘，然后看 `hookdumps\hook_<帧>_*\ring.txt / ee_ram.bin`。
7. **复现本报告的本机矩阵**（需要 4 GB+ 空闲、一次只跑一个实例）：
   `rel_smoke.ps1`（2 × ~102 s）+ `rel_regress.ps1`（4 × 3–9 s）+ 两条 `python` 对照命令（见 §B6/§B8）。
