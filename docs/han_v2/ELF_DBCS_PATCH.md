# ELF DBCS 补丁（SLUS_206.13）— 字体绘制链 16 位化改造与实测报告

> 日期：2026-09-12。对象：`slus_out\SLUS_206.13`（美版 ELF，main 段 VA 0x100000 起）。
> 目标：让引擎消费 DBCS 双字节中文字符串，突破 ZH6 单字节 89 字字符集上限。
> 所有地址为 ELF 虚拟地址（VA = 文件偏移 − 0x80 + 0x100000）。
> 脚本与产物：`C:\gr_build\tmp\dbcs\`；实测 dump：`C:\gr_build\dumps\db1`（Stage1）、
> `C:\gr_build\dumps\db3/db4/db6` 等（Stage2 各轮）。
> **最终结论一句话（§九 修正版）：引擎中不存在"字节对验收器"——Stage2 的 dash 真因是
> DrawString v1 字符槽用 lh（符号扩展）加载 16 位字符，char16≥0x8000 被扩展成负数，
> cw/cctc cave 的 `srl a1,8` 算出垃圾 idx → 每对 clamp 到记录 0（空格），空白 quad 的
> 双线性边缘渗出即"短横"。补丁 = 三条 lh→lhu + lead 标记制（仅 0xA1-0xA3 作对前导，
> SLUS_P_U.elf，与 zh6 单字节串无冲突），GR_DB7 实证 DBCS 对渲染汉字；GR_ZH7 全量盘
> （86 单字节 + 3 标记对字 + 157 新对字、600 条译文）实测通过（§九）。**

---

## 一、引擎事实（绘制链逆向摘要）

```
DrawString v1 (RSFontMgr::DrawString, 0x219A70)   ← 唯一带字符循环的绘制入口
DrawString v2 (0x219E00) / v3 (0x219EB0)          ← 包装/坐标换算, 委托 v1
  开头: jal strlen(0x406F28) → s7;  jal CharHeight(0x21ACD0);  jal StringWidth(0x21AC00)
        c.olt.s f0,f1 + bc1t 0x219DC0               ← 若 x+width < 0 整串剔除
  循环体: lb a1,0(str) → jal 0x40BFC8(存字节到 [sp+0xDF]) → lb a1,0xDF(sp)
          → jal CharWidth(0x21AD10) → 0x20/0xB1/0xB5 特判(按钮 glyph 硬编码 UV) → jal CCTC(0x21ADE0)
          → AddOneWord(0x219F50)
  循环尾: 0x219DAC nop / 0x219DB0 addiu s0,s0,1 (空格分支 0x219D94 自带 +1)
  帧布局: 0xDF=字符, 0xC0=x 游标, 0xB0-0xBC=CCTC 输出, 0xDD/0xDE 全函数零引用(可借用)
RSFont::CharWidth (0x21AD10)     idx = (char − mStartChar[FD+0x20]) & 0xFF, 越界回退 0
RSFont::ComputeCharTextureCoords (0x21ADE0)  同公式 → 10B 记录 UV; 复活点 0x21AE20
RSFont::StringWidth (0x21AC00)   逐字节 Σ宽 + (len−1)×mKerningOffset; 帧 0x60;
  epilogue @0x21ACA4; 全 ELF 48 个调用全部走 0x21AC00 正门(扫描证实)
FontDefinition: +0x20 mStartChar(=32), +0x38 mKerningData(10B 记录), +0x44 mSize
  10B 记录 = {u8 pad, u8 width, u16 u0, u16 v0, u16 u1, u16 v1}
RSFontMgr g_pFontMgr @0x5E70D8; 8 样式按名绑 3 face;
  ★eeram 实证: styles2-5(sx1.0/1.64)=FD slot0='large', styles0-1=slot1='default',
  styles6-7(sx0.8/1.63)=slot2='huge' —— 但 Controller 页标签实测走 **default** face
  (f2870 与 f33479 双时点 ring: 标签字符回退宽度=12=default rec0 的 width)。
死代码洞: 0x26BEA0..0x26C18F (748B) = FindPropertyForModelID + FindPropertyForID。
  ★注意: 两者在 VA 0x23198B8/0x23198C8 有 vtable 数据字引用(裸字扫描可证),
  洞不可向 0x26C190(__dt__, 亦在 vtable)方向扩展; 本实验 748B 内使用安全。
```

---

## 二、Stage1 方案：synth-byte（仅改 DrawString v1）——**实测 PASS**

### 2.1 判定与合成

```
若 s[i] ∈ [0xA1,0xFE] 且 ∉ {0xAE,0xB1,0xB5,0xE7,0xF1} 且 s[i+1] ∈ [0xA1,0xFE] 且 i < len−1:
    synth = ((lead−0xA1)×94 + (trail−0xA1) + 161) & 0xFF;  [sp+0xDF]=synth, [sp+0xDE]=2
否则: [sp+0xDF]=原字节, [sp+0xDE]=1
循环尾 0x219DAC/0x219DB0 ← lbu v0,0xDE(sp) + addu s0,s0,v0
```

保留码 {0xAE,0xB1,0xB5,0xE7,0xF1}=®±µçñ；EN 文本高位字节仅 {0x92,0xAE,0xB1,0xB5,0xE7,0xF1}
（§9 普查），0x92<0xA1 被区间检查排除 → 英文零影响。

### 2.2 指令级 diff（3 条 + cave 39 条，共改 151B）

| 地址 | 原指令 | 补丁后 |
|---|---|---|
| 0x219BCC | `jal 0x40BFC8` | `jal 0x26BEA0`（cave ds1） |
| 0x219DAC | `nop` | `lbu v0,0xDE(sp)` (0x93A200DE) |
| 0x219DB0 | `addiu s0,s0,1` | `addu s0,s0,v0` (0x02028021) |

cave ds1（逻辑）：lead 区间+保留码+末字节防越界+trail 区间检查 → `synth` 公式 → 存回；
逐条反汇编见 `patch_db1_elf.py` 与 §七。0x40BFC8 全 ELF 仅此一个调用点（扫描证实）。

### 2.3 Stage1 测试盘（MENU_db1.img，底 = menu_orig）

FONT.RES：码位 0xA1..0xA8 × 3 face（表偏移 0x5D/0x960/0x1260）共 24 条记录 → 图集尾部空带
测试格 `{0,0x10,sx−20,478,sx−20+16,504}`，sx=20+18i；COMMON.PAK：y478-504 绘 SimHei 16px
`地图武器切换确认`；EN_STRINGS.RES：G65.I116（原 Reload Weapon）→ 23B
`(A1,A1) 2E (A1,A2) 2E … (A1,A8)`；G43.I10 捐赠 10B。

### 2.4 实测（GR_DB1.iso，gsrunner 40000 帧）

- 对应性 verify_iso.py PASS（ELF/MENU 逐字节 + 原件差异 151B）。
- **存活：跑满 exit=0（667s）；WPNRPK74 f150 首中 3985 次（ZH6 基线 4245 同量）。**
- **DBCS：f33480 Controller 页右列行2 = `地.图.武.器.切.换.`（前 6 对逐一正确）**；
  证据 `tmp\dbcs\evid_stage1_db1_f33480.png`、`db1_i116_row5x.png`（f39866 复核非动画）。
- **18B 截断**：23B 串只渲染 18B（6 对+6 点）后停止——机制见 §五（每字符 x 游标
  越界即停的 per-char 剔除检查 0x219D14，DBCS 串宽于原英文标签槽所致，非字体表问题）。
- **英文零损伤**：与 zh6 f33480 逐像素 diff，17 个英文标签+ticker 逐像素一致 → PASS。

**Stage1 判定：PASS** —— 真实 DBCS 汉字上屏（synth 路径），但合成仅覆盖 (lead=A1, trail=A1..A6)
能被游戏"字节对验收器"放行的组合（见 §五），全量化受验收器封锁。

---

## 三、Stage2 方案：16 位字符 ABI（v3 = `build_PS.py` → SLUS_P_S.elf，改动 560B）

### 3.1 字符表示

```
字符槽 [sp+0xDE] 半字 = (lead<<8)|trail；步长槽 [sp+0xDD]（0xDD/0xDE 原版零引用）
读取点 0x219BD0/0x219BD4/0x219BE4/0x219CA0 改 lh；步长改 lbu 0xDD
DBCS 记录 idx = 224 + (lead−0xA1)×94 + (trail−0xA1)
```

### 3.2 四 cave（0x26BEA0 区）

| cave | 偏移 | 挂接 | 职责 |
|---|---|---|---|
| ds16 | +0x000 (39条) | jal 自 0x219BCC | 单/双字节判定 → sh char16 + 步长 |
| cw | +0x09C | j 自 0x21AD18 | 高字节≠0 → idx 公式 → mSize 回退 0 → 记录宽×mScaleX→fptosi |
| cctc | +0x184 | j 自 0x21ADE0 | 同 idx 公式；入口补 andi v1；出口补 lw t2,0x38(t2)；跳回 0x21AE20 |
| sw | +0x1E8 (41条) | j 自 0x21AC74 | 最小对设计：ASCII→复刻原 jal 回 0x21AC7C；对→char16 宽→s4+=2→回 0x21AC84 |

外加：v1 七处槽位改造；六处图标码立即数 −0x4B→0xB5、−0x4F→0xB1
（0x219C08/0x219C14/0x219C94/0x219CAC/0x219D24/0x219D38；16 位 lh 后字符为正）。
**StringWidth 的 0x21AC74 之后原版代码一条不动**（最小对设计的关键）。

### 3.3 FONT.RES 记录数重排（历代测试盘）

| 盘 | large | default | huge | DBCS 记录位置 | 展开态 |
|---|---|---|---|---|---|
| db2 | rows3(96) | **rows14(448)** 含 idx224-253 | rows6(96) | default | 6902B |
| db3 | **rows9(288)** 含 idx224-256 | rows3(96) | rows6(96) | large | 6582B |
| db4 | rows3(96) | rows7(224) | **rows17(272)** 含 idx224-256 | huge | 6422B |
| db6 | **rows14(448)** 含 idx224-421 | rows3(96) | rows7(112) | large | 7062B |

字符串：G65.I115/I116/I117 → 3 条 20B 纯对串（lead A1/A2/A3，next30 高频字全覆盖）；
G43.I10 捐赠 19B。

---

## 四、Stage2 迭代史与二分定位（每轮 73-670s 实测）

### 4.1 v1（patch_db2_elf.py）：boot 挂死

全跑 39900 帧 exit=0 但 f3038 起画面永久定格：**boot 挂死（游戏假活）**。cdvd 末读
f2817 LBA799173（LOAD_NEW_2.RSB 流）后静默——与 §9 毒串死亡签名一致。
单变量隔离（`probe_iso.py`/`probe_run3.py`，boot 判定 73s/轮；
**注意 gsrunner 的 ISO 参数必须反斜杠路径，正斜杠 exit=1 秒退**）：

| 探针 | ELF | MENU | 判定 |
|---|---|---|---|
| E | SLUS_db2(v1) | MENU_db1 | **HUNG** f2817 → 毒在 ELF |
| M | SLUS_db1 | MENU_db2 | ALIVE → MENU 无毒 |

**根因 F1【sw cave 栈帧泄漏】**：v1 的 sw cave 自建 −0x30 帧且直接 `ld ra; addiu sp,sp,0x30; jr ra`
返回，未撤销原版 StringWidth 序言（`addiu sp,sp,-0x60; sd ra,0x50(sp); sq s0-s4`）的 0x60 帧 →
每次调用泄漏 0x30B 且调用方以错位 sp 恢复 → boot 期首次测宽（LOAD_NEW_2.RSB 预处理）即死。

### 4.2 v2（patch_db2b_elf.py）：boot 活了，但零字形

修复三处：**F1** sw 改为不建帧、复用 s0-s7、`j 0x21ACA4` 原版 epilogue 出口（kerning 入 cave）；
**F2** cctc 入口补 `andi v1,a1,0xFF`、出口补 `lw t2,0x38(t2)`；**F3** 六处图标码立即数改正值。
v2 全跑：**流程完全正常**（准时 Controller 页、needle 与 db1 同频 3985 次）但**全部界面零字形**
（标题页"文字"实为 logo 贴图）。四象限定位（Name Entry 字母为字形判读点，`run_bisect.py`）：

| ELF | MENU | 结果 |
|---|---|---|
| db1 | db1 | ✓（Stage1 基线） |
| db1 | db2 | ✓ 主菜单文字正常（M_long）→ MENU_db2 无毒 |
| db2b | db1 | **✗ 零字形**（E2_long）→ ELF 单独致病 |
| db2b | db2 | ✗（db2 全跑） |

**v2 的 sw"全串重写"cave 有毒**：53 条指令经字面模拟器逐条验证算术全对、透明拦截版
（P-H：cave 仅 `jal CharWidth; j 0x21AC7C`）亦 ✓——毒性机制未定位到指令级（疑与引擎对
StringWidth"每次调用只测一个字节"契约的隐含假设有关）。处理：**放弃全串重写，改道最小对设计**。

### 4.3 v3（build_PS.py → SLUS_P_S.elf）：最小对 sw 设计，二分矩阵全绿

sw 最小对：只拦截 DBCS 对；ASCII → 复刻原 `jal CharWidth` 后回 0x21AC7C（原版累加/kerning/
循环全保留）；对 → char16 宽 → s4+=2 → 回 0x21AC84。二分矩阵（Name Entry 字母判读）：

| 探针 | 内容 | 结果 |
|---|---|---|
| P-A | ds16+槽位+立即数（cw/cctc/sw 原版） | ✓ 字形全渲染 |
| P-D | P-A + cctc | ✓ |
| P-E | P-A + cw | ✓ |
| P-H | P-A + sw 透明拦截 | ✓ |
| P-F/P-K/P-N | P-A + sw 全串重写（三种变体） | ✗ |
| **P-S** | **最小对** | **✓** |

---

## 五、Stage2 DBCS 渲染：face 归属逐轮排除 + "对验收器"的发现

> ★**本章结论已被 §九推翻**：不存在"字节对验收器"。dash 真因 = 字符槽 lh 符号扩展
> （char16≥0x8000 → cw/cctc cave 垃圾 idx → 每对 clamp 记录 0）。"（A1,A1)-(A1,A6)
> 放行"的解读亦不成立——Stage1 的 6 对渲染来自 synth 路径绕开 cw/cctc；18B 截断 =
> per-char x 游标剔除（0x219D14）。本章保留为排查史。

v3 上盘后（GR_DB2 = P_S + MENU_db2）：流程/健康/英文全部 ✓（f33480 Controller 页英文标签
与 zh6 逐像素一致），但 3 条 20B DBCS 串渲染为 **10 个相同短横**。逐轮排除：

| 轮 | DBCS 记录位置 | 运行时验证（f2870 eeram） | 结果 |
|---|---|---|---|
| db2 | default rows14(448) | — | dash |
| db3 | large rows9(288) | FD: rows=9 mSize=288, KD[224-256]=我方记录 ✓ | dash（节距 11.2px = 回退宽 12） |
| db4 | huge rows17(272) | FD: rows=17 mSize=272, KD[224-256]=我方记录 ✓ | dash（同上） |
| db6 | large rows14(448) | — | dash（同上） |

**四种 face 放置（含 RAM 实证表正确、源串完整）全部渲染同一 dash → dash 与 FONT.RES 无关。**
P-O2 仪表（cw ext 路径 clamp 点写 ring @0x01F00000 + `-grdumpwin 33470 33482` 窗口 dump）
读到：**DBCS 字符确实到达 cw ext（idx=260 有记录）且该次 `lw v1,0x44(a2)` 读出 mSize=0**
（a0/font 异常或调用方即异常层）+ 大量 idx=0 回退记录。

**最终判定（所有证据的统一解释）**：游戏存在一个**独立于绘制链的字节对验收层**
（boot 期字符串预处理或绘制前 re-encode）：对串中每个 (lead,trail) 对照内部允许表放行/
替换——**已证 (A1,A1)..(A1,A6) 放行（Stage1 渲染汉字）；(A1,A7+) 与 (A2/A3,·) 拒绝**
（拒绝输出 = '-' 占位 glyph，即截图中的等宽短横；db5 的 dash-dot 交替 = 7 对全拒 + 6 个
'.' 分隔符照排）。该验收层解释了全部现象：Stage1 的 18B 截断（第 7 对 (A1,A7) 起被拒 →
后缀不渲染）；Stage2 整串 dash（每对都被拒）；英文零损伤（无对）；
§9 的 0x80-0x9F boot 毒（同一预处理层的另一分支）。

**→ DBCS 全量化的唯一钥匙 = 定位并改写这个"对验收器"表/逻辑（下一轮 RE 目标：
f2816-2817 窗口 EE dump 差分 + LOAD_NEW_2.RSB 预处理函数定位）。绘制链（本报告的
四 cave + 槽位改造）已被证明就绪——验收器放行的对可以直达字体表。**

---

## 六、容量结论（基于已验证的机制）

| 通道 | 数字 |
|---|---|
| 单字节（ZH6 既有，无对） | **89 字** |
| Stage1 synth（对验收器放行窗内） | lead A1 × trail A1-A6 = **6 字**已证；窗上界未探测 |
| Stage2 16 位（验收器放行后可达） | default face rows14 → idx 224-447 = **224 DBCS 槽**；理论 rows15 → 256 |
| face 预算 | large 448(4480B) + default 96(960B) + huge 112(1120B) + 头 502B = 7062B ≤ 7222B |
| DP 压缩 | 6582-7062B → payload 3165-3824B ≤ 4413B（非瓶颈） |
| atlas 可绘 16×26 格 | 模式 A 241 格（清退非保护）/ 与 89 共存 55 格 |
| RES 运输 | blob ≤47,570B；捐赠源 G43.I10 |

**当前可交付 = 单字节 89（ZH6）+ 验收器窗内少量对（≥6 已证）。
全量化（224+ DBCS 槽）卡在"对验收器"——绘制链已就绪。**

---

## 七、复现规程（全部 magic number）

```
0) 工具链: <anaconda3>\python.exe
   gsrunner = C:\gr_build\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe
   ★ gsrunner 的 ISO 参数必须反斜杠路径 (正斜杠 exit=1 秒退不启动)
   ★ -grdumpwin <f0> <f1> = 窗口期逐帧 EE dump; boot 挂死判定只需 ~4300 帧 (73s/轮)
1) ELF: patch_db1_elf.py → SLUS_db1.elf (Stage1, 151B)
        build_PS.py      → SLUS_P_S.elf (Stage2 v3, 560B; 用 patch_db2c.py 的 Asm/build)
   Stage1: 0x219BCC(jal cave) / 0x219DAC←0x93A200DE / 0x219DB0←0x02028021
   Stage2: 0x219BCC(jal ds16) / 0x219BD0←0x27A400DE / 0x219BD4,0x219BE4←0x87A500DE /
     0x219CA0←0x87A400DE / 0x219DAC←0x93A200DD / 0x219DB0←0x02028021 /
     0x21AD18←j cw / 0x21ADE0←j cctc / 0x21AC74←j sw(单条, tail 不动) /
     0x219C08←0x240300B5 / 0x219C14←0x240300B1 / 0x219C94←0x240300B5 / 0x219CAC←0x240300B1 /
     0x219D24←0x240200B5 / 0x219D38←0x240200B1
   原值断言: 0x219BCC=0x0C102FF2, 0x219BD0=0x27A400DF, 0x219BD4/0x219BE4=0x83A500DF,
     0x219CA0=0x83A400DF, 0x219DAC=0, 0x219DB0=0x26100001, 0x21AD18=0x90820024,
     0x21ADE0=0x8C8A0028, 0x21AC74=0x0C086B44, 0x21AE20=0x00051880
   死区: 0x26BEA0..0x26C18F (748B); ★vtable 数据字在 VA 0x23198B8/0x23198C8 → 不可向
     0x26C190 (__dt__) 方向扩展
2) MENU: db1_build.py → MENU_db1.img / db6_build.py → MENU_db6.img (large rows14 承载 DBCS)
   face 记录表 E_LRG/E_DEF/E_HUG = 0x5D/0x960/0x1260; 记录 '<BB4H'=pad,adv,u0,v0,u1,v1
   EN_STRINGS: 8 子流 CHUNKS=[16384]×7+[13857] 总 128545B; 捐赠 G43.I10(组42,条10)
3) ISO: probe_iso.py <ELF> <MENU> <ISO> (ELF@LBA295 + MENU@LBA776286 原位替换)
4) 实测: run_iso.py <ISO> <dump> (zh2 nav 34 键, 40000 帧; memcards 用 memcards_db1 —
   ★新建空 memcards 目录会使 boot 流程与固定 nav 失配!)
   快判: probe_run3.py (4300 帧) / 二分: run_bisect.py (15500 帧, Name Entry 字母=字形探针)
   健康: WPNRPK74 f150-200 首中 + 跑满 exit=0; 判读: Controller 页 = snap_f00033480.png
```

产物清单：`tmp\dbcs\{patch_db1_elf.py, patch_db2_elf.py(v1 毒存档), patch_db2b_elf.py(v2 存档),
build_PS.py(v3 终版), patch_db2c.py(二分参数化), build_PO/PO2.py(cw 仪表),
SLUS_db1.elf, SLUS_db2.elf, SLUS_db2b.elf, SLUS_P_S.elf(终版), SLUS_P_O2.elf(仪表),
db1/2/3/4/5/6_build.py, db1_iso.py, db2_iso.py, probe_iso.py, probe_run3.py, run_iso.py,
run_bisect.py, run_db4_win.py, db2_capacity_scan.py, verify_iso.py, cdvd_diff.py,
fontmgr_probe*.py, font_dump.py, sim_sw.py, quad_search.py, xform_dump.py,
MENU_db1.img, MENU_db2.img, MENU_db6.img, MENU_db3/4.img(中间体),
evid_*.png, db1_i116_row5x.png, db3_f33232_right_3x.png, dash_across_builds.png 等}`。

---

## 八、结论表

| 项 | Stage1 (db1) | Stage2 v3 (db6) |
|---|---|---|
| 跑满 exit=0 | ✓ (667s) | ✓ (667s) |
| WPNRPK74 首中/总数 | f150 / 3985 | f150 / 3985 |
| DBCS 渲染 | 地.图.武.器.切.换.（synth ✓, 18B 截断） | ✗ 每对→'-'（对验收器拒绝） |
| 英文零损伤 | ✓ 逐像素 | ✓ 逐像素 |
| face 归属发现 | — | ★Controller 标签走 default face（回退宽 12 实测）；eeram 证 styles2-5 绑 large |
| 判定 | **PASS** | **部分：链路就绪，卡对验收器（开放）** |

→ 下一轮：定位字节对验收器（f2816 窗口 dump 差分 + LOAD_NEW_2.RSB 预处理函数 RE），
放行全对后本报告的绘制链即可支撑 224+ DBCS 槽的全量盘。

---

## 九、"验收器战役"终局（2026-09-12）：验收器不存在，真凶 = lh 符号扩展

### 9.1 排除过程（静态 RE + RAM 差分双引擎夹击的结果）

1. **动态差分（决定性）**：win_db4（`-grdumpwin 33470 33482`，Controller 页可见期逐帧
   32MB eeram）逐帧搜索测试串 (A1,A1)(A1,A2)…：**绘制时刻串仅存在于 RES 原始容器副本
   （0x5b11b0/c9/e2），逐帧不变，全 32MB 无任何 0x2D 替换副本、无第二份变换拷贝**。
   ——"f2816 boot 期预处理改写串"假说被证伪（RAM 中的 2D 连排 = 日志格式串
   `-------- load ps2 sky --------` 与 GS 包数据，与测试串无关）。
2. **逻辑证伪**：(A1,A1) 在 Stage1（db1）渲染出汉字、在 Stage2（db6 的 I115 同样以
   (A1,A1) 开头）渲染 dash——同一字节对、同一 RAM 内容、不同 ELF → 按"对值"放行/拒绝
   的字符串层验收器在逻辑上不成立。
3. **静态定位真凶**：反汇编 SLUS_P_S.elf（dis4P.py = dis4.py 换 ELF 路径），逐条审计
   四 cave + DrawString v1 槽位：
   - 0x219BD4/0x219BE4 = `lh a1, 0xDE(sp)`、0x219CA0 = `lh a0`——**lh 符号扩展**：
     char16 = 0xA1A1（≥0x8000）→ a1 = 0xFFFFFFFFFFFFA1A1。
   - cw cave（0x26BF3C）入口 `srl t0, a1, 8` → 0x00FFFFA1 → idx = (0xFFFF00)×94+…
     ≈ 1.58e9 ≥ mSize → **sltu 恒假 → 每一对 clamp 到记录 0（空格）**；cctc cave 同构。
   - 于是 CharWidth 返回空格宽（default 空格 adv=10 + kerning 1 = 实测节距 11.0px ✓），
     CCTC 返回空格格 UV → 空白 quad；其双线性采样边缘渗出相邻字形底缘 = 视觉上的
     "等宽短横"（db3/db4/db6 三种 face 放置像素级相同 ✓——因为根本没查 DBCS 记录）。
   - P-O2 ring 的事后再解读：`(idx=248/249/250, mSize=224)` = 干净 char16 的对在 db4
     default face(mSize=224) 被 clamp 的直接记录；垃圾 idx 0x5DFFC571 = 符号扩展路径。
4. **Stage1 为何能过**：ds16 cave 在字节循环内直接消费对（synth 后步进 2），
   cw/cctc 从未收到 char16 → 无符号扩展问题。§五"18B 截断=第 7 对被拒"应更正为
   per-char x 游标剔除（0x219D14），与验收器无关。
5. **0x80-0x9F boot 毒（§9 RES_AB_TEST）与此无关**，仍是字符串预处理层的独立分支。

### 9.2 补丁（SLUS_P_T.elf = P-S + 3 字节，build_PS_v4.py；终版 = P-U 标记制，build_PS_v5.py）

| 地址 | P-S（v3） | P-T（v4） |
|---|---|---|
| 0x219BD4 | 87A500DE `lh a1,0xDE(sp)` | **97A500DE `lhu a1,0xDE(sp)`** |
| 0x219BE4 | 87A500DE `lh a1,0xDE(sp)` | **97A500DE `lhu a1,0xDE(sp)`** |
| 0x219CA0 | 87A400DE `lh a0,0xDE(sp)` | **97A400DE `lhu a0,0xDE(sp)`** |

- ASCII 零影响：ds16 存 0x00XX，lhu==lh；0x92 高位单字节经 cave `andi 0xFF` 后不变。
- 附带修复：0xB5/0xB1 图标码比较（+0xB5/+0xB1 立即数）在 lhu 下恢复设计语义。

**P-U（终版）：lead 标记制**。GR_DB7 通过后自审发现根本性冲突：v4 的 ds16 消费
**任意** (lead,trail∈[A1,FE]) 对 → 与 zh6 单字节汉字串不可共存（相邻两个单字节汉字
必被并成一个垃圾对，如 换弹=D2 D3 → pair(D2,D3) → idx 越界 → 整词变空格）。
解法 = **仅 lead ∈ {0xA1,0xA2,0xA3} 构成对**（此三码位的 役/有/下 在字符串中一律
以对形式编码），0xA4-0xFE 一律单字节（保留码 ®±µçñ >0xA3 自动单字节，无需再查表）：
- ds16/sw 的 lead 检查 = `sltiu t1,a1,0xA1`(单) + `sltiu t1,a1,0xA4`(≥A4 单)，
  比原区间+保留码检查更短（ds16 28 条 / sw 30 条）；
- cw/cctc/七槽位/六立即数与 P-T 相同；vs 原版 481B（差异全部在 cave 区，断言于脚本）；
- zh6 的 76 条译文中出现 役/有/下 的位置由构建器强制改编码为对（字形复用其原单字节格，
  记录 idx 381-383 指向 ZH6 格，零重绘）。

### 9.3 验证（GR_DB7 = SLUS_P_T + MENU_db2）

- probe_run3 快判 ALIVE（f4173）→ 40000 帧全跑 **exit=0（669s）、WPNRPK74 共 3995 次**
  （基线 3985 同量）。
- **Controller 页（f33500 快照）：I116 行 = `向不被式经前更下上难`、I117 行 =
  `对自数失称在使正改法`——20 对逐一渲染为 16px SimHei 汉字，无任何 dash**；
  I115（'Change Fire rate'）不属于页面 3 的显示行（其串在 RAM 0x5b11b0 完好）。
  注：页面右列行2/行4 绑定的是 I116/I117（zh3 时代换弹=I116 显示于行2 已证）。
- 英文零损伤：Zoom In/Night Vision/Perform action/Fire Weapon/…/ticker 与 zh6 同帧一致。
- 证据：`tmp\dbcs\zh7_db7_full.png`、`zh7_db7_rows4x.png`、`win_db7\`（13 帧 eeram）。

### 9.4 GR_ZH7 全量盘（246 字 = 86 单字节 + 3 标记对字 + 157 新对字；593 条译文）

| 项 | 配方 | 实测 |
|---|---|---|
| ELF | **SLUS_P_U.elf**（lhu + lead 标记制） | — |
| FONT.RES | large **rows5**(160=0x20-0xBF，保 0x92/®/±/µ；çñ 2 格让出) + default **rows12**(384 = 原224 含 zh6 89 字 + idx224-383 = 160 对记录) + huge **rows7**(112=0x20-0x8F 全 ASCII) | 展开 7062B ≤ 7222；DP payload **4232B** ≤ 4413；槽回环 PASS |
| 对字表 | 157 新字 = levelb 官方 PC 译文缺字频序贪心（tmp\zh7_sel.json）：第 k 字 ↔ (0xA1+k//94, 0xA1+k%94)，idx=224+k ≤ 380；另 役/有/下 对形式占 idx 381-383（字形=ZH6 原单字节格，零重绘） | 含 ？。标点；逐字 16px SimHei |
| 编码规则 | 86 个非标记 zh6 字 = 单字节；标记字 + 157 新字 = 对；EN 原文零改动（ASCII + ®±µçñ/0x92 单字节自动安全） | 构建器 assert 单字节 ∉ {A1,A2,A3} |
| atlas | 收割被裁撤记录格（large 0xC0+ / huge 0x90+ / default 0x7F-0xA0 占位，196 矩形清底，与全部保留记录矩形求交避让）+ 26px 带排格（u0≥1） | 157/157 格；COMMON_PAK_ZH7.bin |
| RES | zh6 76 条 + 新 517 条官方 PC 译文（levelb_entries，剔除鼠标/键盘词条），标记制重编码 | blob **46,010B** ≤ 47,570（余 1,560） |
| 组装 | menu_working 底 + probe_iso（ELF@LBA295 + MENU@LBA776286）→ GR_ZH7.iso | 构建 PASS（差异全在白名单） |
| 实测 | run_iso 40000 帧（zh2 nav，memcards_db1） | **见 §9.5** |

逐格布局：`tmp\zh7\layout_dbcs.txt`（含 157 新字 + 3 标记对的字/对/cell/record 五元组）。

### 9.5 GR_ZH7 实测判定（**PASS**）

- gsrunner 40000 帧（run_iso，zh2 nav，memcards_db1）：**跑满 exit=0（667s）**；
  WPNRPK74 帧 150 首中、共 **4,229 次**（zh6 基线 4,245 同量）；boot 环/Name Entry/
  主菜单/Controller 页全程流程零漂移。
- **Controller 页（f33480，证据 `tmp\zh7\zh7_f33480_full.png` + 四张 2x/3x 裁剪）**：
  - 左列：缩小 / 地图 / 切换队员 / 蹲下 / 平移 / L3键+◄► / 左右窥视 / 暂停菜单
  - 右列：放大 / 换弹 / 切换武器 / 执行动作 / 开火 / 视角上下 / R3键 / 快速命令
  - 按钮栏：△ 返回、✕ 确认（全局中文按钮提示，主菜单与 Name Entry 同样生效：
    ⬜ 删除）；未译条目（Stance Up、Night Vision、Shuffle/walk/run、Turn left/right、
    ticker）英文原样零损伤；Name Entry 键盘字母/数字/符号全部正常（large rows5）。
  - **单字节与对字节共存实证**：删除(单字节⬜)、换弹/切换武器(对) 同页同现；
    zh6 时代的 89 字形全部保留。
- 已知小瑕疵：右列"视角上下"行下方有一处 ~6px 的"_"形弱迹（空白 quad 边缘渗漏
  的残留表现，不影响辨识；疑似该行 widget 的隐藏第二串）。
- 容量数字：字符 246（86 单字节 + 3 标记对字 + 157 对字，atlas 157 新格 + 复用格）；
  译文 593 条（zh6 76 + 新 517）上屏见 Controller 页及按钮栏；FONT 7062B/4232B、
  RES 46,010B / 47,570B。

### 9.6 产物清单（本轮新增）

| 文件 | 说明 |
|---|---|
| `tmp\dbcs\build_PS_v4.py` / `SLUS_P_T.elf` | lhu 修复构建器 / GR_DB7 验证 ELF（=P-S+3B） |
| `tmp\dbcs\build_PS_v5.py` / `SLUS_P_U.elf` | lead 标记制构建器 / **终版 ELF** |
| `tmp\dbcs\run_db7_win.py`、`win_db7\` | DB7 验证跑（win dump 13 帧 eeram） |
| `tmp\dbcs\zh7_db7_*.png` | DB7 汉字上屏证据 |
| `tmp\zh7_build.py` | ZH7 一体构建器（FONT+PAK+RES+IMG，全自检） |
| `tmp\zh7\ft_expanded/slot_zh7.bin`、`COMMON_PAK_ZH7.bin`、`layout_dbcs.txt` | 字体/图集/布局产物 |
| `tmp\zh7\container_zh7.bin`、`en_strings_zh7_8sub.bin`、`zh7_sel.json` | RES 容器/blob/词条选择 |
| `tmp\MENU_ZH7.img`、`iso\GR_ZH7.iso`、`dumps\zh7` | 成品镜像/成品盘/实测 dump |

### 9.7 遗留与风险

1. 对字形（160 项）仅入 **default** face（Controller/菜单标签实证面）；HUD（large）/
   字幕（huge）若日后果译及，需按 §9.4 同法扩对应 face（预算：large rows5+default
   rows12+huge rows7 组合已用 7062/7222，扩面需以 default 让渡）。
2. large face 裁至 0xBF：ç(0xE7)×1、ñ(0xF1)×1 两码位在 large 系样式回退空格
   （EN 全文仅 2 处，未在验证路径）。
3. 对字 trail 覆盖 0xA1-0xFE 全域（含 ®±µ 等保留码作 trail——保留码限制仅适用于
   lead 与单字节路径，trail 在对内被整体消费，GR_DB7 实证无碍）。
4. lead 标记制的代价：役/有/下 三字失去单字节形态（必须以对编码）；若未来词条
   扩到 A2 lead 的 94 槽之外，需 default rows13+（large/huge 相应再让）。
5. §9（RES_AB_TEST）的 0x80-0x9F boot 毒仍未解（与本战役正交，容量上已绕开）。

---

## 十、任务载入崩溃战役（2026-09-13/14）：vtable thunk 指向旧洞起点 —— cave 迁址 0x416ED0（v9）

> 现象：U/V6/V7/V8 四代补丁 ELF 的盘「主菜单→Training→进 T01」在 **f26575 确定性崩溃**
> （R5900 野跳 PC=0x383FE000）；原盘同 nav 跑满 59,900 帧。MENU 前端 40000 帧从不崩。
> 判别矩阵（PROJECT_STATUS §17.3）已证与盘内容无关，必要因子 = ELF 补丁本体。
> 前作产物 `han_v2\tmp\crashfix\`；终作 `tmp\crashfix\{build_PS_v9.py → SLUS_P_V9.elf}`。

### 10.1 二分与现场（gsrunner 5 轮 + recError 钩子）

| 探针 | 内容 | 结果 |
|---|---|---|
| probeA | 仅 loop-tail 两指令（0x219DAC←lbu v0,0xDD(sp) / 0x219DB0←addu s0,s0,v0），其余原版 | **f27400 存活** → loop-tail 无辜 |
| probeB | V6 全部 cave+挂点，loop-tail 还原 nop/addiu | **f26575 崩** → 毒在 cave/挂点侧 |
| 钩子 | iR5900.cpp recError 头插 EE 寄存器+栈 dump（diff 存档 gsrunner_hook_iR5900.diff） | **t9=PC=0x383FE000、ra=0x47D9F0、a0=s3=0x00EA0770** |

ra=0x47D9F0 不在字体链（0x219xxx/0x21Axxx）→ 野跳发生地在 POB 模型载入代码。

### 10.2 根因（指令级闭环）

```
类 vtable @VA 0x598EA0，槽 +0x3C (=0x598EDC) = 0x0026BE90   ← 数据字引用，在函数入口前 0x10
0x26BE90: addiu a0,a0,-0x8 ; j 0x26BEA0                    ← 调整器 thunk (this-=8)
0x26BEA0: FindPropertyForModelID（「死代码洞」起点 = 旧 cave ds16 头）
任务载入 RSSky::Initialize → POBLoader::Load → POBLoader::LoadGeometry @0x47D9E0:
  lw t9, 0(s3)        ; t9 = 对象 vptr（s3=a0=this=0xEA0770）
  lw t9, 0x3C(t9)     ; t9 = vtable 槽 15 = 0x26BE90（thunk）
  jalr t9             ; → thunk → j 0x26BEA0 → 落进 ds16 cave 头
ds16 头三条 = andi a1,0xFF ; sh a1,0(a0) ; … sb v0,-1(a0)
  → 以 modelID 为「字符」把对象 vptr 低 2 字节覆写、vptr[-1] 覆写为步长 1/2
下一条同对象虚调用 lw t9,0x3C(坏 vptr) → 读出堆数据 0x383FE000 → jalr t9 野跳（确定性 f26575）
```

- MENU 前端不载 POB → 40000 帧从不崩；任务载入必经 POBLoader → 必崩同帧同 PC。
- ★旧 §一 的「vtable 数据字 @0x23198B8/0x23198C8」系**读取域误判**：0x2319xxx 的线性
  VA 映射落在 `.mwcats` 调试节（文件偏移 0x220ADD0..0x223047C > PT_LOAD filesz=0x4DED80，
  运行时不加载）。
- ★find_deadzone 判据 2（数据字窗 [entry, entry+size)）漏掉**入口前**的 thunk 槽
  0x598EDC→0x26BE90。判据修正：数据字窗必须含 [entry−0x20, entry)；且「全文件无数据字
  等于洞内地址」是假阴性——真实引用经 thunk 的 j 指令（代码引用）间接到达。

### 10.3 修复：cave 迁址 0x26BEA0 → 0x416ED0（14 个未引用 SDK ioman 桩，4272B）

- 新区零引用自检（构建器内建 + 独立复核）：[CAVE−0x20, CAVE+0x2EC+0x20) 对 jal/j 目标、
  任意 4 对齐数据字（含入口前 0x20 thunk 窗）、lui+lo 物化地址，**三类 count=0**。
- v9 = 迁址 + ZH11 网格常量（NCOL=37, CELL_W=13, CELL_H=15, Y0=128, LEAD_HI=0xAE）；
  五重自检 PASS（含「旧洞 0x26BE90..0x26C18F 逐字节还原」「vs zh11V8 差异仅 4 个 j/jal
  目标字+新旧 cave 区（1173B）」「vs 41×12 同迁址版仅差 4B 常量字」）。
- sim_cave_v9 全路径字面模拟（真 ELF 字节，延迟槽语义）：ds16/cw/cctc/sw 39 向量 PASS。

### 10.4 实测判定（gsrunner，全部后台+轮询防超时纪律）

| 轮 | 盘 | 判定 |
|---|---|---|
| T01 nav 60000 | GR_ZH10（V9+ZH11 内容） | **跑满 exit=0；越过 f26575；零野跳；WPNRPK74 f150 首中共 6232 次；f29698 教程框中文上屏**（对照原盘同帧 EN 基线 grk99_t01ab2，HUD 状态一致；行尾有 §9.5 已知 1-2px 级排版弱迹） |
| T01 nav 60000 ×2 复跑 | 同盘 | 各跑满 exit=0，6232 次逐次一致（确定性复现） |
| MENU 40000（zh2 nav） | 同盘 | 跑满 exit=0；**645/645 快照与 GR_ZH11 轮 dumps\zh11 逐像素完全一致（diff=0）**；WPNRPK74 4232 次=基线同数 |
| 码位抽扫（ZH10T 33600） | V9+MENU_DB11Z+ZH11 GR 两槽 | 156 项 / 144 过 / 0 mismatch / 7 渗墨；**坏项集合 (8,1)(8,2)(12,1)(13,1)(14,4)(15,0)(16,7) 与 ZH11T 基线逐一相同**（全部 §19 已知 1-2px 竖向渗墨）；60 对抽样项全干净 |
| 150000 帧浸泡（nav_soak） | 同盘 | 跑满 exit=0；f150 首中共 15583 次；零野跳 |

（动态佐证链：迁址前身 41×12+ZH9 内容实验盘曾跑到 f56820 存活——被会话超时杀死，非模拟器事件。）

### 10.5 普通模拟器与遗留

- `ninja -C C:\gr_build\pcsx2 PCSX2`（还原钩子后）exit=0（重编 iR5900.obj）。该定制树
  ENABLE_QT_UI=OFF 且 deps 无 Qt6 开发件（仅运行时 DLL）→ **树内无 pcsx2.exe 目标**
  （pcsx2/CMakeLists 仅 add_library(PCSX2)；Qt 配置实测 cmake 4.0.3 对中文 cwd 触发
  fail-fast 0xC0000409，ASCII cwd 后报 Qt6Config.cmake 缺失）。按 ZH8b 轮先例以重建后的
  vanilla pcsx2-gsrunner（-grdumpdir 仅激活 ISO 引导路径，无 needle/nav/maxframes）裸跑
  终盘 10 分钟验证（带钩子 gsrunner 存档 pcsx2-gsrunner_hooked.exe.bak；结果见
  PROJECT_STATUS §20）。
- 教训：**「死代码」判定必须含数据字入口前 0x20 窗 + thunk 间接链**；调试节（.mwcats/
  .debug）的线性映射字不是运行时引用——两者都误导过本轮排查。

## 十一、DoWordWrap pair-aware 战役（2026-09-14）：逐字节折行切断 DBCS pair —— cave 0x417500（V13W）

> 现象：用户实测 ZH15 训练关教程框三缺陷——「起爆器」→「命爆器」、「图上」→「g;」、
> 「第二行开头显示错误」（L2 尾「更换姿」+ L3 首孤「随」）。
> 前作/终作 `tmp\zh16b\{build_PS_v13W.py → SLUS_P_V13W.elf}`；验证盘 GR_ZH16T.iso
> （= GR_ZH13B 基底 + V13W ELF@LBA295，ELF 槽逐字节校验 PASS）。

### 11.1 根因（gsrunner 绘制钩子第一现场）

```
教程框路径 = RSTextComponent::DrawTheString(0x21C4C0)
          → RSFontMgr::DrawString v3(0x219EB0) → v1(0x219A70)
DoWordWrap(0x21CC10) 逐字节 lb + 每字节 CharWidth 测宽
  → 断点 s2 落入 DBCS pair 中间（lead 单字节 = 1/2 字宽 → 累计宽度提前/推后越界）
孤 lead 渲染成 trail 的单字节字形：
  引=(0xA1,0xE0) 丢 lead → 孤 0xE0 = 「命」（起爆器→命爆器）
  L2 尾孤 lead 0xA3 = 势、L3 首孤 trail 0xF2 = 随（更换姿势/随.卧倒）
  0xA8+0xFE 走垃圾对 clamp（图上→g;）
存储层完好（GR.IMG EN_STRINGS.RES pair 完整，G12.I002=113B / I023=140B 实测）——
丢 lead 发生在折行层。
```

### 11.2 修复：DoWordWrap 扫描循环 pair-aware 化（V13W）

- 单挂点 0x21CD70 → j 0x417500，48 条 cave（安全区 0x417500 零引用自检：j/jal 目标 +
  全文件字面量 count=0；0x26BEA0 毒区未回用，§10 教训继承）。
- 逻辑：lead∈[0xA1,0xAE) 且 trail∈[0xA1,0xFF) 且非末字节 → char16 走 CharWidth 对路径
  步进 2；否则单字节路径步进 1；溢出 → 0x21CDBC（at=0、Substring end=s2 永不切对）；
  越界 → 0x21CDB8；ASCII 逐字节等价。
- sim_wrap_v13W 双断言 PASS（真 ELF 指令字 + 真 CharWidth 链 + 真 FONT.RES 记录）：
  I011/I012/I021/I022 真串全预算扫描断点永不 mid-pair；ASCII 串与原版算法逐字节等价。
- 构建器排障记录（cave 汇编发射器三轮）：jal 延迟槽 addu a0,t0,a0 → zero（a0 泄漏）；
  label 伪项占槽空洞 → emit 计数器；slt op=0x2A → 0x00；SINGLE or a1,t2,a1 → t2,zero
  （上次 a1 泄漏 0x65|0x73=0x77 实锤）。

### 11.3 实测判定（gsrunner，防超时纪律：全部后台+轮询）

| 轮 | 盘/nav | 判定 |
|---|---|---|
| T01 nav 60000（-grdrawwin 26900 30200） | GR_ZH16T + nav_t01 | **跑满 exit=0（1002s）；WPNRPK74 f150 首中；drawlog 145,637 行；教程框路径 F26901 PC=219EB0 RA=21C85C 完整串含 pair** |
| I021 教程框 f29698 | 同上 | **PASS：完整两行「…练习更换姿势,卧倒并从铁丝网下面爬过去.」——before=三行断对（L2 尾「更换姿」孤 lead、L3 首孤「随」）；now「更换姿势」完整、无孤字**（证据 tmp\zh16b\judge_v13w\I021_full_f29698.png，对照 before_snap_f00029667.png） |
| I012 教程框 f26970 | 同上 | **PASS：L1 尾「…用右摇杆转身和调」/L2「整视角上下…」完整无缺字无孤字**（调/整 分行=独立字形合法断行；证据 judge_v13w\I012_L1L2_f26970.png） |
| 起爆器(I002)/图上(I023)/μ± | — | 不在 T01（越野训练）流程内 → **多关卡验证**（见 11.4） |

### 11.4 多关卡验证（2026-09-14 新增：不同训练关显示不同教程文本）

- 选关导航破解（dump_t01 快照实证）：nav_t01 = f25550 输入名字「确认」→ f25900 档案「否」
  → f26009-26226 选关屏（「训练」列表 训练1-7，down 换选、cross 接受）→ f26200 cross 进入
  → f26536 简报「训练1 - 越野训练」+载入中 → f26970 关内教程框。
- 导航脚本：tmp\zh16b\nav_t02..t07.txt（修复版：N-1 个 down 全部在选关屏内、进关 cross 后移至
  最后一个 down 后 250 帧——旧版把 down 插进进关 cross 之后导致换关不生效，已弃用）。
- **gsrunner 截图挂起（环境发现）**：T02+ nav + `-grsnap` 任意值 → **f20150 确定性挂起**
  （截图保存处，4/4 复现；snap15/snap31、并发/单跑、memcards 原版/副本均复现；同配置
  nav_t01 顺利通过；无 `-grsnap` 的 nav_t02 跑满 exit=0）。多关卡验证一律 **无 -grsnap**，
  教程框判定用 `-grdrawwin` drawlog 字节流（功能级判定）+ T01 已有截图基准。
- **多关卡结果表（drawlog 功能级，判定器 decode2.py = zh13+zh12 双字符集 + 真孤字节检查；
  每轮 32500 帧跑满 exit=0；"缺陷特征" = BAD-PAIR-START/孤 trail 行首/垃圾对）**：

| 关 | 盘内名（简报/选关光标实证） | 教程框（首行摘要） | 缺陷特征 | 判定 |
|---|---|---|---|---|
| T01 | 越野训练（训练 1） | （视觉级，见 11.3）I012 越野 + I021 姿势框 | 0 | **PASS** |
| T02 | 轻武器训练区（训练 2） | 「这里是轻武器训练区.你要学习如何使用步枪和手枪,如何切换武器,换弹和使用瞄准镜.」+「(按) START 键退出训练.」 | 0 | **PASS** |
| T03 | T03 - Grenades／榴弹训练区 | 「这里是榴弹训练区.你要学习如何投掷手雷和使用榴弹发射器.随时按 START 键退出」 | 0 | **PASS** |
| T04 | T04 - Heavy Weapons／火箭筒训练区 | 「这里是火箭筒训练区.你要学习如何使用反坦克火箭筒…」+ 准星框「你应该注意到…/时候才能开火.等准星收缩到最小后…」 | 0 | **PASS** |
| T05 | T05 - Machine Guns／机枪训练区 | 「这里是机枪训练区.你要学习如何使用固定的机枪.随时按 START 键退出训练.」 | 0（2 嫌疑证伪=前端「接受/返回」MENU 侧合法 pair，(A4,AF)=接/(A5,BA)=受 实证） | **PASS** |
| T06 | T06 - Demolitions／**爆破**训练区 | 「这里是爆破训练区.你要学习如何放置地雷并将之引爆.你可以用同样的方法来放(置爆破装药)/以及心跳感应器等.」——原始字节「A2 BB **A1 E0** EB」=之引爆，**引 pair 折行后完整** | 0 | **PASS** |
| T07 | T07 - Command／指挥训练区 | 指挥界面框 + 指挥地图键框 + **I023 三行**：L1「…在指挥地图界面…并在**地图上**放置」、L2 行首「点，」+「按 **µ** 键添加路径点，按 **±**」、L3 行首「键删除.」——三处折行点全部避开 pair | 0 | **PASS** |

- **三大用户缺陷落实**：「命爆器」（孤 0xE0）→ T06 爆破框引 pair (A1,E0) 完整；「g;」（I023 行首
  垃圾对）→ T07 L1 图上完整、L2 行首「点」；µ/± + 第二行行首错误 → T07 L2 µ(0xB5)/±(0xB1)
  单字节完整绘制（均在 pair-lead 区间 [A1,AE) 之外，折行安全），字形由 ZH13B FONT.RES reencode
  提供。I002（引爆器×2 地雷演示框）需玩家埋雷触发，nav 未覆盖——同机制已由 T06/T07 全序列佐证。
- 定版报告：tmp\zh16b\FINAL_ELF.md。

### 11.5 遗留

- ~~μ/± 显示状态（PS2 键帽图标 or 字母）~~：**已闭环（T07）**——µ/± 按单字节字形完整绘制，
  字形内容 = ZH13B reencode 所含 µ/± 字模（用户缺陷中的「仍是字母」系 ZH15 缺 reencode 所致）。
- V13W 实机问题隔离迭代预案：cave 指令 → 挂点 → 模拟器漏模拟路径（未触发——T01 一次通过，
  T02-T07 亦一轮通过，零重跑）。

### 11.6 V14R2 wrap cave 取址修复（2026-09-15，二轮用户反馈残字/映射错根因定案）

- **根因（子代理 C 字节级定位，tmp\zh16\WRAP_PROGRESS.md）**：0x417500 cave 首条取数
  `lw $t1,0xfc($sp)` 取到的是 RSUIString 的 **impl 结构体指针**（= `*(token+4)`），不是字符缓冲
  `*(*(token+4)+4)`。RSUIString = {vptr@+0, impl*@+4}，impl = {u16 len+1, u8 flag, pad, char* chars@+4}
  （构造函数 0x542020 / Length 0x53FD50 / DoWordWrap 自己 0x21CEFC 双解引用三处独立证实）。
  pair 判据作用在 impl 头/堆邻接字节上 → trail 检查恒失败 → **步进恒 1 = 退回 V12 逐字节行为**，
  CharWidth 测垃圾宽度。**cave 自 V13W 诞生起从未在真机工作过**；§11.4 的 T01-T07 drawlog
  功能级 PASS 部分依赖断点"恰好对齐"（I021/I019/I023 运气对齐），I000/I012/I015 则 mid-pair
  （用户二轮截图 1/2 与旧 I012 残字同源）。
- **受害串定案**（GR_ZH16.iso 实测提取，与截图逐字吻合）：G12.I000 化=(A3,A7) 切断 → L2 首
  (A7,A8)=值；I015 武=(A1,AB) 切断 → 孤 AB+器单字节 BE=(AB,BE)=迅；I012 整=(A3,D4) 切断 →
  孤 D4=以。断点字节再被 Substring 施加到真字符流 = 按字节错位。
- **修复（2 指令字，零尺寸）**：延迟槽 0x21CD74 `27A400F8`(addiu a0,sp,0xf8, cave 路径死代码)
  → `8FA400FC`(lw a0,0xfc(sp)=impl)；cave 0x417504 `8FA900FC`(lw t1,0xfc(sp)=impl 指针)
  → `8C890004`(lw t1,0x4(a0)=chars)。安全性：ELF 全扫描 j 0x417500 仅此一 hook；a0 在
  0x417574 重赋值前无消费者；两出口（0x21CDB8/0x21CDBC）随即重写 a0。
- **落点**：build_PS_v14.py build_wrap_cave() 内 emit 改 rs='a0' imm=0x004 + put(WHOOK+4,[0x8FA400FC])；
  自检 1 增 0x21CD74 原值断言，自检 4/5 允差扩 0x21CD74/wrap字1。ELF 重建 PASS（2026-09-15）。
- **漏检教训**：sim_wrap_v13W.py 在模拟内存直接把 *(sp+0xfc) 写成 chars——建模了"应然"而非
  "实然"，断言只验证判据未验证取址。修复后语义 = 应然模型：任意预算断点全 pair 对齐。
