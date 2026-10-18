# REPORT_SENTINEL_FIX.md — ★ 哨兵 trail 重排：修复版「2,400 字」成品盘 + 基底盘容量证明

> 执行者：汉化执行者（哨兵修复子代理）· 2026-10-15
> 仓库根 `C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization`
> **写入范围**（严格）：`work\builds\GR_HASHR\**` · `docs\REPORT_SENTINEL_FIX.md` ·
> `docs\CVAR_TEST_GUIDE.md`（追加）· `docs\AB_TEST_GUIDE.md`（追加）·
> `tools\font_pipeline\data\charset_compiled_zh16.json`（**已备份**）·
> `tools\text_csv\gate_pairs.json`（**已备份**）
> **只读**：`GR_FA2400_K2` / `GR_ZH113b` / `GR_CVAR` / `GR_SENT` / `GR_F364` / `GR_F365` /
> `third_party\orig\**` / PCSX2 配置 —— 一字未改。
> **未 commit / 未切分支 / 未 merge**。**未使用 `Select-Object -First N`**（截断一律重定向到文件再读）。

---

## 0. 一句话结论

```
① ★★ 交付 A 已出盘并**独立终检全绿**：
     work\builds\GR_HASHR\GR_HASHR2400.iso
     sha256 c9986ad294a2aa94a95b47b0f294b5303d13642c8f53adfa619f6a22f9ba5582
     尺寸 1,648,164,864 B（与基底 GR_FA2400_K2 逐字节同尺寸）
    · 3 个中文容器里「作为对偶 trail 的 0xB1/0xB5」：**738 → 0**
    · charset 里「trail ∈ {B1,B5} 的登记」：**50 → 0**
    · 3 容器**逐条**解码字符序列：5,019 条全部一致（不符 0）
    · 有字形槽 **1,877 → 1,877**（不减少）；被搬 42 字的字形「新格 == 基底旧格」逐 texel 42/42
    · 图集两条不变式 + 网格闸门全过；全盘差异 **83,067 B 全部落在计划窗口内（窗口外 0 B）**
② 做法（三处闭环，全部有硬断言）：
     ① charset：注销全部 50 个 trail∈{B1,B5} 的对偶码（42 真字 + 8 占位），
        42 个真字搬到保留段低位让出的连续 42 槽（1,936..1,977，**保留段起点后移**）；
     ② 图集：42 个字形逐 texel 搬到新槽，旧槽清零（确定性空模板 0x11）；
     ③ 文本：3 个中文容器载荷里这些对偶码**就地 2 字节换 2 字节**（长度/条目表/结构全不动）。
③ 容量账（**没有抬闸门**）：对偶 2,300（= 2,350 − 50 哨兵码）+ 单字节 103
     = **总字形槽 2,403 ≥ 2,400** ✓。保留（无字形）槽 473 → 473（其中 423 注册占位 + 50 未登记哨兵码）。
④ ★ 交付 B（`GR_ZH113b`，不改几何/闸门）**数学上无解**，已在 §5 给出鸽笼证明与三条备选；
     **未擅自抬闸门**（按任务书纪律停手上报）。
⑤ ★ 一条与"根因"有关、必须让用户知道的口径（**不是质疑、只是补证**，见 §1.3）：
     在**钩子开启**的汉化盘上，`DrawString` 把对偶码打包成 16 位值后才比较
     （`lhu $a1,222($sp)` vs `addiu $v1,zero,0x00B1/0x00B5`）⇒ **trail 字节不会命中图标特判**；
     该特判只在**逐字节渲染**的路径上命中（原盘引擎 CVAR_04 族 / 回退钩子的 HK 族）。
     ⇒ 本修复对「原盘引擎 + 中文文本」这条已实证的链条是**根治**，对钩子开启的盘是
     **必要且无害的消除**；若实机仍卡，下一刀应在 §8.2 的代码侧臂。
```

---

## 1. 根因回顾（Lead 已定案，本节只做引用与补证）

### 1.1 定案内容（不再重述论证）

汉化把汉字对偶码的第二字节（trail）做成了 `0xB1`/`0xB5`；引擎（原盘 `DrawString`
`0x219C08..0x219D38` 8 处立即数 + `CharWidth` `0x21AD38/0x21AD4C`）对这两个字节有
**硬编码图标占位特判**，命中后走 `AddOneWord(...,t0=1)` 的**容量 2 副包**
（`0x21A0CC slti v1,v1,2`）⇒ 逐字符写坏内存 ⇒ 堆元数据损坏（dlmalloc 坏链 → NULL →
死循环/Trap，画面静止）或 GS/VIF 包损坏（`FQC=0`）。

**实机证据（用户）**：`GR_SENT\SENT_01_trail_fix.iso`（只改 trail，其余一字不动）**不卡** ✓ ；
`HK_01_all_text_off`（回退全部文字链钩子）**仍卡** ⇒ 钩子无关、数据即病因。

### 1.2 本轮实测的哨兵规模（`audit/recon2.txt`，只读两盘）

| 盘 | 闸门 | 对偶空间 | charset `pair_of` | 3 容器哨兵 trail 站点 | 涉及对偶码 | 涉及字 |
|---|---|---|---|---|---|---|
| `GR_FA2400_K2`（交付 A 的基线）| `0xBA` | 2,350 | 2,350（满载）| **738**（MENU 286 + GR 286 + XML 166）| 32 | 32（另有 10 个哨兵字 7 容器用量 0）|
| `GR_ZH113b`（交付 B 的基线）| `0xB1` | 1,504 | 1,504（满载）| **738**（同上）| 32 | 32（**全部在文本里**）|

* 逐字处数（K2/基底一致）：星 117 · 择 103 · 文 67 · 吗 55 · 厄 47 · 样 46 · 铁 36 · 表 33 ·
  墙 32 · 章 28 · 编 25 · 靠 23 · 景 20 · 太 18 · 今 17 · 欢 14 · 损 8 · 酷 7 · 雾 5 · 冰 5 ·
  概 4 · 宾 4 · 乘 3 · 丈 3 · 励 3 · 啤 3 · 坛 3 · 殿 2 · 齿 2 · 泛 2 · 宝 2 · 崇 1（= 32 字 738 处）。
* 口径更正（如实登记，与 `REPORT_SENTINEL.md` §1.4 一致）：**"286" 是位置数不是字数**；
  去重后是 **32 个字**（K2 上哨兵 trail 的登记条目共 50 条 = 32 在用字 + 10 个 7 容器零用量字 +
  8 个私有区占位字）。

### 1.3 ★ 补证：特判只在"逐字节"路径上命中（口径，供判读实机结果用）

命令（只读反汇编，产物在 `audit/`）：

```powershell
$env:PY = "C:\Users\84363\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
& $env:PY work\tools\cave_extract_elf.py work\builds\GR_FA2400_K2\GR_FA2400_K2.iso work\builds\GR_HASHR\temp\GR_FA2400_K2_SLUS_206.13.elf
& $env:PY work\tools\cave_dis.py work\builds\GR_HASHR\temp\GR_FA2400_K2_SLUS_206.13.elf diso 0x219BC0 0x219E10   # → audit/cave_zh113b_drawstring.txt
& $env:PY work\tools\cave_dis.py work\builds\GR_MEMDRIFT\audit\ZH113b_SLUS_206.13.elf diso 0x416E80 0x416F10   # → audit/cave_zh113b_entry.txt
& $env:PY work\builds\GR_HASHR\tools\hashr_imm_scan.py <elf>…                                                    # → audit/imm_scan.txt
```

1. `DrawString` 循环（ZH113b/K2 同型）：

   ```
   0x219BC8  lb  $a1, 0($v0)        ; 取字符串**当前字节**
   0x219BCC  jal 0x00416ED0         ; ★ 汉化 cave: 若 b∈[0xA1,gate) 且下一字节∈[0xA1,0xFF)
                                    ;   ⇒ 打包成 (lead<<8)|trail 存到 sp+222, 返回步长 2; 否则存单字节, 步长 1
   0x219BD4  lhu $a1, 222($sp)      ; ★ 无符号半字 = **打包后的 16 位值**
   0x219C08  addiu $v1,zero,0x00B5 ; ┐ 图标特判: 比较的是**这个 16 位值**
   0x219C14  addiu $v1,zero,0x00B1 ; ┘ ⇒ 对偶码的 hi 字节 ≠ 0 ⇒ **永不命中**
   0x219DAC  lbu $v0, 221($sp)      ; 步长 = cave 写下的 1 或 2
   0x219DB0  addu $s0, $s0, $v0
   ```
   cave 入口 `0x416ED0` 的打包条件（`0x416F0C sltiu t1,t3,0xA1` / `0x416F1C beq …,0xFF`）确认
   **trail 必须 ∈ [0xA1,0xFE]** ⇒ 续航里那个"负 trail 别名"技巧不可行（无需再试）。
   另：`RSFont::CharWidth`（`0x21AD10`）已被 `0x21AD18 j 0x416F40` 改成跳 cave，
   其后 `0x21AD38/0x21AD4C` 的 `0xFFB5/0xFFB1` 是**死代码**；cave 的宽度函数只在
   `a1>>8 == 0`（单字节）时才比 `0xB5/0xB1`（`0x416F40..0x416F6C`）。
2. ⇒ **在钩子开启的汉化盘上，trail 字节根本不会到达图标特判**；它们只在"逐字节渲染"
   （原盘引擎 / 回退钩子）时才逐个命中。
3. ⇒ 本条**不改变任务**（照修），只影响判读：若实机在**钩子开启**的汉化盘上仍卡，
   下一刀应在**代码侧**（把 8 处 `addiu …,0x00B1/0x00B5` 改成永不命中，SENT_02 同型；
   或按 §8.2 把 `lhu` 比较改成对 `a1&0xFF` 的比较）。

---

## 2. 重排方案（交付 A：`GR_HASHR2400`）

### 2.1 地面真值（全部从盘上读，`audit/build_k2.txt`）

```
[gate1] rec#1 = new_font_revised, psm 0x14, 1024×644
[gate2] px_size = 329,744 == w*h/2+16 ✓
[gate3] (w*h/2) % 2048 == 0 ✓
[gate4] 网格 64 列 × 38 行 = 2,432 格 (yrow = 3 + 16*(row + 2·[row≥12]))
[gate5] 盘上 ELF 解码闸门 = 0xBA ⇒ 对偶空间 (0xBA−0xA1)×94 = 2,350
```

### 2.2 三个动作

| # | 动作 | 数量 | 说明 |
|---|---|---|---|
| ① | **注销** trail∈{B1,B5} 的对偶码登记 | **50** | 42 个真字（要搬）+ 8 个私有区占位字（U+E236…U+E354，直接注销）|
| ② | **搬字**（码位 + 字形一起搬）| **42** | 目标 = 保留段**低位**连续 42 槽 `1,936..1,977`（原占位字 U+E200..U+E229 让位）⇒ 保留段起点后移 |
| ③ | **文本重编码** | **738 处** | 3 个中文容器载荷内 `old_pair → new_pair`，**2 字节换 2 字节** |

**目标槽选择规则（确定性、可复算）**：从槽 1,936 起向上枚举；跳过 (a) 哨兵槽、
(b) 非"私有区占位字"的槽、(c) 与**任何非空 FT 记录矩形**相交的格、(d) 已有墨的格。
实测：前 42 个候选全部合格（跳过 0 个）⇒ 目标槽 = 1,936..1,977 连续。

### 2.3 ★ 逐字符新旧码对照表（42 条，完整清单；同表在 `audit/moves_table.txt`）

| # | 字 | 旧码 | 旧槽 | 新码 | 新槽 | 让位占位字 | 墨 |
|---|---|---|---|---|---|---|---|
| 1 | 星 | `A1B1` | 16 | `B5D9` | 1936 | U+E200 | 72 |
| 2 | 择 | `A1B5` | 20 | `B5DA` | 1937 | U+E201 | 70 |
| 3 | 吗 | `A2B1` | 110 | `B5DB` | 1938 | U+E202 | 60 |
| 4 | 文 | `A2B5` | 114 | `B5DC` | 1939 | U+E203 | 45 |
| 5 | 墙 | `A3B1` | 204 | `B5DD` | 1940 | U+E204 | 84 |
| 6 | 样 | `A3B5` | 208 | `B5DE` | 1941 | U+E205 | 67 |
| 7 | 景 | `A4B1` | 298 | `B5DF` | 1942 | U+E206 | 78 |
| 8 | 编 | `A4B5` | 302 | `B5E0` | 1943 | U+E207 | 93 |
| 9 | 铁 | `A5B1` | 392 | `B5E1` | 1944 | U+E208 | 68 |
| 10 | 靠 | `A5B5` | 396 | `B5E2` | 1945 | U+E209 | 86 |
| 11 | 章 | `A6B1` | 486 | `B5E3` | 1946 | U+E20A | 81 |
| 12 | 表 | `A6B5` | 490 | `B5E4` | 1947 | U+E20B | 69 |
| 13 | 励 | `A7B1` | 580 | `B5E5` | 1948 | U+E20C | 83 |
| 14 | 厄 | `A7B5` | 584 | `B5E6` | 1949 | U+E20D | 61 |
| 15 | 雾 | `A8B1` | 674 | `B5E7` | 1950 | U+E20E | 86 |
| 16 | 齿 | `A8B5` | 678 | `B5E8` | 1951 | U+E20F | 62 |
| 17 | 损 | `A9B1` | 768 | `B5E9` | 1952 | U+E210 | 71 |
| 18 | 太 | `A9B5` | 772 | `B5EA` | 1953 | U+E211 | 43 |
| 19 | 今 | `AAB1` | 862 | `B5EB` | 1954 | U+E212 | 34 |
| 20 | 欢 | `AAB5` | 866 | `B5EC` | 1955 | U+E213 | 53 |
| 21 | 丈 | `ABB1` | 956 | `B5ED` | 1956 | U+E214 | 43 |
| 22 | 乘 | `ABB5` | 960 | `B5EE` | 1957 | U+E215 | 77 |
| 23 | 概 | `ACB1` | 1050 | `B5EF` | 1958 | U+E216 | 93 |
| 24 | 殿 | `ACB5` | 1054 | `B5F0` | 1959 | U+E217 | 84 |
| 25 | 宾 | `ADB1` | 1144 | `B5F1` | 1960 | U+E218 | 66 |
| 26 | 泛 | `ADB5` | 1148 | `B5F2` | 1961 | U+E219 | 50 |
| 27 | 酷 | `AEB1` | 1238 | `B5F3` | 1962 | U+E21A | 100 |
| 28 | 冰 | `AEB5` | 1242 | `B5F4` | 1963 | U+E21B | 53 |
| 29 | 啤 | `AFB1` | 1332 | `B5F5` | 1964 | U+E21C | 80 |
| 30 | 坛 | `AFB5` | 1336 | `B5F6` | 1965 | U+E21D | 58 |
| 31 | 宝 | `B0B1` | 1426 | `B5F7` | 1966 | U+E21E | 67 |
| 32 | 崇 | `B0B5` | 1430 | `B5F8` | 1967 | U+E21F | 72 |
| 33 | 铺 | `B1B1` | 1520 | `B5F9` | 1968 | U+E220 | 90 |
| 34 | 食 | `B1B5` | 1524 | `B5FA` | 1969 | U+E221 | 66 |
| 35 | 宠 | `B2B1` | 1614 | `B5FB` | 1970 | U+E222 | 72 |
| 36 | 屁 | `B2B5` | 1618 | `B5FC` | 1971 | U+E223 | 72 |
| 37 | 焚 | `B3B1` | 1708 | `B5FD` | 1972 | U+E224 | 64 |
| 38 | 狡 | `B3B5` | 1712 | `B5FE` | 1973 | U+E225 | 60 |
| 39 | 褐 | `B4B1` | 1802 | `B6A1` | 1974 | U+E226 | 80 |
| 40 | 谋 | `B4B5` | 1806 | `B6A2` | 1975 | U+E227 | 80 |
| 41 | 览 | `B5B1` | 1896 | `B6A3` | 1976 | U+E228 | 0 |
| 42 | 坻 | `B5B5` | 1900 | `B6A4` | 1977 | U+E229 | 0 |

* 新码 trail 全部 ∉ {B1,B5}（实际落点 trail = `D9..FE`、`A1..A4`）✓
* 第 41/42 行（览/坻）墨 = 0：它们的**上游登记本来就没有字形**（K2 把 1872..2344 留空，
  见 `CAPACITY_2400.md` §17.3「有字形槽 1,877 / 保留空槽 473」）⇒ 搬家不改变其"无字形"状态，
  已如实登记（见 §6.3）。
* **50 个哨兵槽（禁用，未登记）**：`16(A1B1) 20(A1B5) 110 114 204 208 298 302 392 396 486 490
  580 584 674 678 768 772 862 866 956 960 1050 1054 1144 1148 1238 1242 1332 1336 1426 1430
  1520 1524 1614 1618 1708 1712 1802 1806 1896 1900 1990 1994 2084 2088 2178 2182 2272 2276`
  （全部清零为确定性空模板 0x11）。

### 2.4 槽位账（★ 容量核对：**没有抬闸门**）

```
对偶空间 (gate 0xBA):                    2,350 槽
  − 哨兵码 (trail ∈ {B1,B5}, 25 lead × 2):  −50
  = 可用且安全的对偶码:                    2,300
单字节码 (charset codes):                   103
────────────────────────────────────────────────
总字形槽 = 2,300 + 103 = **2,403 ≥ 2,400** ✓（余 3）

charset 登记条目: 2,350 → 2,300
  = 2,350 − 50（注销哨兵条目） − 42（目标槽占位字让位） + 42（真字登记新码）
保留/空槽: 473 → 473
  = 423 注册占位（62 个上游"注册但无字形"的真字 + 359 个私有区占位 + 2 个被搬的览/坻）
  + 50 未登记哨兵码
有字形槽: 1,877 → 1,877（不减少）
```

**为什么不用"抬闸门到 0xBB"**：任务书明确禁止（那要再改 ELF 立即数，属新变量）；
本轮的实测账（2,300 + 103 = 2,403）已经达标，不需要。

---

## 3. 图集搬家：逐 texel 证明

* 槽 → 格：`col = slot % 64`、`row = slot / 64`、`U0 = 16·col`、`V0 = 3 + 16·(row + 2·[row≥12])`；
  格 = 16×16 nibble（`0` = 墨，`1` = 透明）。
* 每个被搬字：**读源格 → 写目标格 → 回读比对**（构建期 + 回读期各一次，两次都过）：

  ```
  [A6] 字形搬家 42 个: 每个「新格回读 == 源格」逐 texel ✓ (墨合计 2793)
  [R1] 回读图集: 42/42 个新格逐 texel == 源格 ✓
  ```
* 旧槽清零 = 写确定性空模板（16×16 全 nibble `0x1`）。
* **FT 记录窗零污染**（硬断言）：

  ```
  [A7] 目标格被非空 FT 记录矩形压着的: 0 (必须 0)
  [A8] 全部 544 条非空 FT 记录窗内的像素: 改变 0 个 (必须 0)
  ```
  （口径：544 条非空记录 × 3 个 face 的并集矩形；判"记录窗内像素逐字节不变"，等价于
  "单字节码/ASCII 的渲染结果一个像素都没动"。）
* 图集容器回环：`container_to_plane(plane_to_container(容器))` **逐字节相同**（`[A10]`）。

---

## 4. 文本重编码与"字符不变"的证明

### 4.1 做法（按字节流走，不按出现次数扫；沿用 `LEAD_CAPACITY_2400.md` §12 的推荐口径）

```
对每个载荷区间 (LANG = 每条目 payload; SFXML = <text> 正文 ∪ name= 属性 ∪ 文本节点):
  i = 0
  while i < len(payload):
      b = payload[i]
      if 0xA1 <= b < gate:                      # 对偶前导
          t = payload[i+1]
          if (b,t) 在 charset.pair_of:          # 合法对偶码
              if (b,t) ∈ 改动表: 写新码 2 字节   # ★ 长度不变
              else:             原样 2 字节
              i += 2
          else:                 原样 1 字节      # 配不出对: 与迁移工具同口径, 不动
              i += 1
      else:                     原样 1 字节 ; i += 1
```
* **长度恒定** ⇒ 载荷长度前缀、组分隔、条目表、容器尺寸、IMG 条目字段全部不需要动。
* 容器重压只重压**变了的子流**（其余照搬原压缩字节），并逐子流 `lzo1x_decompress` 回环自检。

### 4.2 覆盖范围核对（3 容器之外还有没有真文本用这些旧码）

| 范围 | 结果 |
|---|---|
| 7 个容器（3 中文 + ES/FR）| 3 中文 **738 处已改写**；ES/FR 的"合法对偶哨兵" = **0**（它们的 `0xB1/0xB5` 是 Latin-1 单字节，配不出对偶码）|
| **权威口径**：`work/builds/**/text/*.csv` + `temp/textdump*/*.csv`（**376 份**）| 被搬的 42 个字：**32 个**在 3 容器里（已全改），**10 个**（铺食宠屁焚狡褐谋览坻）在**全部 376 份 CSV 里 0 次** ⇒ 全盘无文本使用 |
| `*.TXT` 条目（未压缩文本文件）| 50 个哨兵码原始命中 **0**（唯一例外 `IGORSCRIPTING.TXT` × 1，且上下文是二进制段，取证 `audit/txt_scan.txt`）|
| ELF（37 MB，指针/符号表）| 命中全部落在指针/数据表里（例 `00 0c 00 00 00 01 00 04 00 a1 b1 04 00`）⇒ 非文本，取证同上 |
| 二进制美术资源（BMZ/RSB/SB/PSS）| 字节分布恰好落在 CJK 对偶空间 ⇒ **大量假阳性**（如 `ZZZ.PSS` 41,946 次）；仅登记，不作证据。判据以 CSV 为准 |

构建期硬断言（全绿）：`[A5c] ★ 权威口径: 376 份文本 CSV 里, 被搬的 42 个字 —— 在 3 容器出现过 32 个 ;
在 CSV 里 0 次的 10 个`，且断言"任何被搬字要么在 3 容器里、要么在所有 CSV 里 0 次"。

### 4.3 ★ 字符不变（终检脚本从盘上重读，`audit/verify.txt`）

```
[V2] EN_STRINGS.RES@MENU      逐条解码比较 2232 条 ; 不符 0
[V2] EN_STRINGS.RES@GR        逐条解码比较 2232 条 ; 不符 0
[V2] EN_SPECIAL_FEATURE.XML   逐条解码比较  555 条 ; 不符 0
[ok] 3 容器逐条解码字符序列完全一致 (5019 条, 不符 0)
[V2b] 码位改动表 42 条
[ok] 所有字节差异都是登记在案的「旧哨兵码 → 新码」2 字节替换 (越界 0)
```
* 口径：**基底盘用旧 charset 解码、产物盘用新 charset 解码**，逐条比较字符数组（`==` 逐元素）。
* `[V2b]` 是更强的逐字节证明：产物与基底在 3 容器里的**每一处**字节差异，都必须是
  改动表里登记的"2 字节替换"，且替换的 2 字节都从**合法对偶码起点**开始（越界 0）。
* 注：`EN_STRINGS.RES@MENU/GR` 的 XML 侧另有 5 处"配不出对的前导"（`0xA4`，上游既有），
  本轮**原样保留**（`[V1]` 里 `配不出对 5 → 5`）。

---

## 5. 五条硬判据（逐条给命令与输出）

### 判据 1 — 哨兵清零 ✅

```powershell
& $env:PY work\builds\GR_HASHR\tools\hashr_verify.py      # → audit/verify.txt
```
```
[V1] EN_STRINGS.RES@MENU      哨兵 trail  286 →    0 ; 对偶码 20439 → 20439 ; 配不出对 0 → 0
[V1] EN_STRINGS.RES@GR        哨兵 trail  286 →    0 ; 对偶码 20439 → 20439 ; 配不出对 0 → 0
[V1] EN_SPECIAL_FEATURE.XML   哨兵 trail  166 →    0 ; 对偶码 18356 → 18356 ; 配不出对 5 → 5
[V1] ES/FR_STRINGS.RES@MENU/GR 哨兵 trail    0 →    0
[V1] 3 个中文容器哨兵 trail 合计: 738 → 0
[V1] charset 里 trail ∈ {B1,B5} 的登记: 50 → 0
```
**口径分开**：
* 「作为**对偶 trail** 的 `0xB1`/`0xB5`」= **738 → 0**（并集口径，去重对偶码 32 个）；
* 「charset 里 trail ∈ {B1,B5} 的**登记**」= **50 → 0**（含 8 个私有区占位字）；
* 「**裸单字节** `0xB1`/`0xB5` 或**图标占位**」：在 gate 0xBA 下 `0xB1/0xB5` 属于前导区间
  ⇒ **文本里不可能以单字节字符出现**（出现即被当 lead 吞字节）；基底盘 3 容器实测裸哨兵 = 0，
  垫底的 `0xB1/0xB5` 图标**早已在上一轮迁成对偶码**（`0xB9FE`=✕ / `0xB1A1`=△）。
  ⇒ 本盘的"合法图标占位"= `0xB9FA..0xB9FE`（trail FA..FE，非哨兵）✓

### 判据 2 — 字符不变 ✅ 见 §4.3（5,019 条逐条一致 + 逐字节只允许登记替换）

### 判据 3 — 字形不丢 ✅

```powershell
& $env:PY work\builds\GR_HASHR\tools\hashr_dump_font.py --iso work\builds\GR_FA2400_K2\GR_FA2400_K2.iso `
      --out work\builds\GR_HASHR\font_base_k2 --charset work\builds\GR_HASHR\backup\charset_compiled_zh16.json.before_hashr --no-png
& $env:PY work\builds\GR_HASHR\tools\hashr_dump_font.py --iso work\builds\GR_HASHR\GR_HASHR2400.iso `
      --out work\builds\GR_HASHR\font_prod --charset tools\font_pipeline\data\charset_compiled_zh16.json --no-png
```
| dump_font 口径 | 基底 K2 | 产物 GR_HASHR2400 |
|---|---|---|
| 字符总数（ascii 95 / latin1 2 / pair / single 101）| 2548（pair **2350**）| 2498（pair **2300**）|
| **有字形 / 缺字形** | **2075 / 473** | **2075 / 423** |
| **对偶字有字形** | **1877 / 2350** | **1877 / 2300** |
| 几何体检 | 错误 473 / 警告 2（空白 473、截断 64、越窗 0、极稀 0）| 错误 **423** / 警告 2（空白 423、截断 64、越窗 0、极稀 0）|
| 格位公式自查 | 2350/2350 ✓ | 2350/2350 ✓ |

* **保留槽单列**：产物上是 **423** 个"注册但无字形"（62 个上游"注册无字形"真字 +
  359 个私有区占位 + 览/坻）＋ **50** 个未登记哨兵槽；基底上是 473 个（全部在 1872..2344 保留段）。
* 「截断 64 / 警告 2」是**基底就有的**（64 = 上游 1872..1935 段的已知登记），产物未增加。
* 独立逐 texel 证明另见 `[V3] 被搬字 42 个: 产物新格 == 基底旧格 逐 texel 的 42 个`。

### 判据 4 — 图集两条不变式 + 三闸门 ✅

```
[ok] prod: rec#1 = new_font_revised psm 0x14 1024x644
[ok] prod: px_size 329744 == w*h/2+16
[ok] prod: (w*h/2) % 2048 == 0
[ok] prod: 槽 0..2349 全部映到图集内互不重复的 16x16 格        # 38 行 × 64 列 = 2,432 格
[gate4/gate5] 网格 64×38 ; 盘上 ELF 闸门 0xBA（4 站点一致）
```
（三闸门 = `w < 1025`、`px_size == w*h/2+16`、`(w*h/2)%2048==0`；本轮几何一个字未动。）

### 判据 5 — 实机 6000 帧（研究模拟器，独占）

```powershell
# 串行独占: cap_run.py --wait-first 会先轮询到零 pcsx2 进程再跑; 跑前跑后都查残留
& $env:PY work\tools\cap_run.py --iso work\builds\GR_HASHR\GR_HASHR2400.iso `
      --dump work\builds\GR_HASHR\runs\hashr2400 --nav tools\capture\nav_menu_only.txt `
      --maxframes 6000 --snap 30 --wait-first
```
（等价命令，逐字同任务书；`cap_run.py` 只是加上"等待独占 + 跑前跑后查进程 + 记录 RUN.txt"：
`pcsx2-gsrunner.exe -grdumpdir <out> -grmaxframes 6000 -grsnap 30 -grinput tools\capture\nav_menu_only.txt
-grmemcards <out>\mc -logfile <out>\emulog.txt -- <iso>`）

> **结果见 §7.2**（本轮记录：`runs\hashr2400\RUN.txt` + `emulog.txt` + 截图数）。

### 判据 6 — 全盘差异 100% 落在计划窗口内 + 尺寸登记 ✅

```
[out ] GR_HASHR2400.iso  1648164864 B  sha256=c9986ad294a2aa94a95b47b0f294b5303d13642c8f53adfa619f6a22f9ba5582
[D  ] 全盘差异: 计划窗口内 83067 B ; **窗口外 0 B**
[D  ] 差异区间 3854 段 ; 窗口 = [图集容器 0x5EC8786D..0x5ECD807D)
                                  [MENU 文本槽 0x623B1000..0x623BD224) ; [GR 文本槽 0x623BD800..0x623C91D2)
                                  [XML 槽 0x0F034F50..0x0F040953)
[V5] ISO 尺寸不变: 1648164864 ; 7 个容器的 IMG 条目字段 (stored/off/real) 未动
[V5] COMMON.PAK 468243 B: 改动 4288 B, 全部落在图集容器内
```

---

## 6. 交付 B（`GR_ZH113b` 的同一修复）—— **未达成（容量不可能）**

### 6.1 事实（`audit/recon2.txt`）

```
GR_ZH113b  gate=0xB1  pair_of=1504 codes=110
  3 容器: EN MENU 286 + EN GR 286 + XML 166 = 738 处哨兵 trail ; 涉及 32 个字, **全部在用**
  7 容器里"已登记对偶字"的用量: 有用量 1502 个 ; **零用量只有 2 个**（牌、凌）
  对偶空间 = 16 lead × 94 trail = 1504 ⇒ charset **铺满**，空闲槽 0
```

### 6.2 ★ 鸽笼证明（不改几何/闸门 ⇒ 无解）

```
需编码的字 (pair_of 里的真字)            = 1,504
安全槽 (trail ∉ {B1,B5}) = 16 × 92      = 1,472
1,504 > 1,472                            ⇒ 至少 32 个字必然落在哨兵 trail 上
```
* 若允许丢字：可用空槽只有 **2** 个（牌、凌，且它们在文本 CSV 里也 0 次）⇒ 最多只能救 2 个字。
* 单字节侧也没有余量：非 ASCII、非 lead 的可用字节 112 个，charset 已用 110 个（只剩 2 个）。
* 别名/负 trail 技巧**已实证不可行**：cave 入口要求 trail ∈ [0xA1,0xFE]
  （`0x416F0C sltiu t1,t3,0xA1` / `0x416F1C beq t1,zero,0xFF`，见 §1.3）⇒ 不存在"同槽不同码"。

**结论：在"不抬闸门 + 不丢字 + 字符序列不变"三条同时成立时，交付 B 无解。**
按任务书纪律**停手上报**，未擅自抬闸门。

### 6.3 三条备选（请用户裁决，任选其一）

| 选项 | 代价 | 副作用 |
|---|---|---|
| **B-1（推荐）** 只出证明，不出 B 盘 | 0 | 交付 A 已覆盖"数据侧修复"的判读；对照改用 A vs `GR_FA2400_K2`（同输入同时序）|
| **B-2** 抬闸门 `0xB1 → 0xB2`（+94 槽，改 1 字节 ELF 立即数）| = r82 那一轮的工作量：0xB1 变成 lead ⇒ 需把文本里 **14 处 △ 图标**改成对偶码 + **自制 △ 字形**，再做本轮同一套 32 字搬家 + 重编码 | 引入"闸门"这个新变量（任务书禁止未批准时改）|
| **B-3** 代码侧对照盘（SENT_02 同型：`DrawString` 8 处立即数 → 永不命中）| 8~10 字节补丁，不动文本/图集 | 会让 ZH113b 的 △/✕ 手柄图标改成普通字形（可见副作用）；不是数据侧修复 |

---

## 7. 给用户的实机验收要点（★ 请按顺序做）

### 7.1 盘与哈希

| 盘 | 路径 | sha256 | 尺寸 |
|---|---|---|---|
| ★ 修复版 2,400 字成品盘 | `work\builds\GR_HASHR\GR_HASHR2400.iso` | `c9986ad294a2aa94a95b47b0f294b5303d13642c8f53adfa619f6a22f9ba5582` | 1,648,164,864 |
| 对照（未修，天然基线）| `work\builds\GR_FA2400_K2\GR_FA2400_K2.iso` | `c3851c1d7eb361e3aa8ab8cea36b0ac6d3915c291e695ec77adf4b6316265e94` | 1,648,164,864 |

（`work\builds\GR_HASHR\GR_HASHR_base.iso` **未产出**，原因见 §6。）

### 7.2 本轮本机 6000 帧读数（研究模拟器）

> 口径：同一采集器、同一 `nav_menu_only.txt`、同一记忆卡、6000 帧、`-grsnap 30`。
> **判据 = ≥190 截图 / `TLB Miss` 0 / 无 `Trap exception` / 到中文主菜单**。

| 盘 | 截图数 | 去重画面 | `TLB Miss` | `Trap exception` | 停顿 `pc=` | exit / 耗时 | 残留进程 |
|---|---|---|---|---|---|---|---|
| **`GR_HASHR2400`（修复盘）** | **191** | 163 | **0** | **0** | 无 | 0 / 102 s | 无 |
| `GR_FA2400_K2`（未修对照）| 191 | 163 | 0 | 0 | 无 | 0 / 102 s | 无 |

★ **逐帧比对（最硬的一条）**：两次跑法的 **191 张截图 sha256 全部相同（不同 0 张）**
⇒ 修复盘与未修对照盘在 6000 帧里的**画面逐像素完全一致**（含中文主菜单）；
本修复**没有任何可见副作用**，也没有改变游戏状态推进（截图帧号序列 270..5970 完全相同）。

```
$env:PY … & $env:PY work\builds\GR_HASHR\tools\hashr_runresult.py --dump work\builds\GR_HASHR\runs\hashr2400 --tag GR_HASHR2400
$env:PY … & $env:PY work\builds\GR_HASHR\tools\hashr_runresult.py --dump work\builds\GR_HASHR\runs\k2_base  --tag GR_FA2400_K2
# 比对 result.json 里的 snap_sha：
#   修复盘截图 191 ; 对照盘截图 191 ; 共同帧 191 ; 逐帧 sha256 相同 191 ; 不同 0
```

* 命令：`python work\tools\cap_run.py --iso <盘> --dump work\builds\GR_HASHR\runs\<tag>
  --nav tools\capture\nav_menu_only.txt --maxframes 6000 --snap 30 --wait-first`
* 读数脚本：`python work\builds\GR_HASHR\tools\hashr_runresult.py --dump <dir>`
  → `runs\<tag>\result.json`（含 191 张截图的 sha256 清单）。
* **判据 5（修复盘）：✅ 通过**（191 ≥ 190 截图 / `TLB Miss` 0 / 无 `Trap exception` / 无停顿 PC /
  到中文主菜单——由"与对照盘逐帧相同"直接证明）。
* **污染登记（如实）**：起跑前另一执行者（`GR_FPSBISECT`）占着模拟器，本盘按纪律**只等待不杀**
  （`--wait-first`，每 20 s 轮询一次）。
  * 修复盘：其 batch C 于 `23:48:33` 报 `batch end`，本盘 `23:48:46` 起跑、`23:50:17` 结束
    ⇒ **全程独占，零并发**（`RUN.txt` 的 `post_procs = none`）。
  * 对照盘：`23:51:15` 起跑、`23:52:57` 结束；对方 `23:52:37` 启动了下一批（batch D）
    ⇒ **尾部约 20 s 重叠**（本机实测；对方 `contention.csv` 未记录到，但以本报告为准）。
    该重叠只影响**速度**，不影响截图数/去重/TLB/Trap 与逐帧一致性，故 §7.2 的任何结论不受影响。

### 7.3 实机验收要点（用户手动，**至少 20 分钟**）

1. **同一关反复进出 ≥3 次**（进关卡 → 打完/退出 → 再进同一关）—— 上游观察到的卡死是"累积型"。
2. **火箭筒开火**（唯一被用户实测证实的触发点之一）：挑有火箭筒的关卡，连续开火 ≥10 发。
3. **L1 小队/地图界面**：反复开合 ≥10 次，并在里面滚动队伍列表。
4. **"选择关卡 → 队伍选择界面"**（第三个已证实触发点）：反复进出 ≥5 次，逐个切换队员。
5. **存读档循环**：存档 → 读档 → 再存 → 再读，≥5 轮（含记忆卡界面）。
6. **特别收录（Special Feature）**：进 SF → 武器 → M82A1 / M4 / OICW 看**长正文**（二次迁移缺陷的修复点）。
7. **图标**：教程/引导里的 △ / ✕ 手柄图标必须**仍然正确显示**（本盘它们是手绘字形
   `0xB1A1`(△) / `0xB9FE`(✕)，不是引擎图标码）。
8. **拉丁文/数字/标点**：档案名 `TEQSUNSET`、"50"、"%" 等必须清晰可读（K2 几何的 ASCII 表已安置）。
9. 判"卡死"的口径沿用既有约定：画面完全静止、必须重启；同时记 `emulog.txt` 尾部 60 行
   与停顿 PC 集合（`pc=0x541038 / 0x541eb0 / 0x102764` 是同一条堆链的指纹）。
10. **对照组**：同一操作序列在 `GR_FA2400_K2.iso` 上跑一遍。若**修复盘不卡、K2 卡** ⇒ 修复有效；
    若**两张都卡** ⇒ 下一刀走 §8.2 的代码侧臂（`DrawString` 8 处立即数改成永不命中），
    并把 `emulog.txt` 两份一起给我。

---

## 8. 未达成项 / 风险 / 已知缺陷（如实登记）

### 8.1 未达成

1. **交付 B（`GR_HASHR_base.iso`）未产出** —— §6 已证明在"不改几何/闸门"下无解；三条备选待裁决。
2. **本机模拟器跑不出用户的卡死**（既有定案：BIOS/记忆卡/ISO/版本全对齐后 gsrunner 复现不出缺页）
   ⇒ 判据 5 只能验证"不引入新故障"，**"是否真修好卡死"仍只能由用户实机判定**。
3. **`0xB1/0xB5` 作为 *lead* 的字（K2 上 188 个：lead 0xB1 行 94 个 + lead 0xB5 行 94 个）本轮未动**
   —— 按用户定案"trail 是病因"，且 §1.3 的补证表明打包后的 16 位值不会命中特判
   （lead 也一样进不去比较）⇒ 登记为"未动、理论上同风险等级"。
4. **XML 里 5 处"配不出对的前导 `0xA4`"**（上游既有）未处理：不是本轮范围，逐条登记在 `[V1]`。
5. **`.MIS / BMZ / RSB / PSS` 等二进制资源里"原始旧码"命中无法穷举判定**（压缩+二进制噪声）
   ⇒ 覆盖判据改用**项目文本 CSV（376 份）**这一权威口径；已在 §4.2 写清口径与残余不确定性。

### 8.2 风险（会改变用户下一步判断的两条）

1. **§1.3 的补证**：在钩子开启的汉化盘上，trail 字节不会进入 `DrawString` 的图标特判
   （cave 先打包成 16 位值再比较）。所以本修复对"原盘引擎 + 中文文本"（CVAR_04 族，
   也就是 SENT_01 实证的那条链）是根治；对**钩子开启**的盘是"消除形态、必要但可能不充分"。
   ⇒ **若修复盘实机仍卡，请把 `emulog.txt` 给我**，下一刀按代码侧走（8 处立即数 → `0xFF00`，
   与 `SENT_02` 同型，属新变量需用户批准）。
2. **版式影响 = 0**：本修复不改字距、不改折行（宽度只与 FT 记录/单字节码有关；对偶码的宽度
   在 cave 里恒为常量），所以**没有任何版式扰动**——这是与 `SENT_01/03/04`（改版式）的关键区别。

### 8.3 工具链同步

* `tools\font_pipeline\data\charset_compiled_zh16.json`：`pair_of 2350 → 2300`，新增
  `_trail_fix_hashr` 段（42 条 old→new + 8 条注销 + 哨兵槽清单 + 证据指针）。
  **备份**：`work\builds\GR_HASHR\backup\charset_compiled_zh16.json.before_hashr`。
* `tools\text_csv\gate_pairs.json`：新增 `trail_fix` / `trail_fix_pairs` / `trail_fix_old` 段
  （`pairs` 段原样保留，`load_gate_pairs()` 行为不变 —— 已实测仍返回原 5 条）。
  **备份**：`work\builds\GR_HASHR\backup\gate_pairs.json.before_hashr`。
* ⚠ **对旧盘的影响**：`dump_text_csv` / `inject_text_csv` 默认读这份 charset，用它去解析
  **`GR_FA2400_K2` 或更早的盘**时，那 42 个旧码会解不出（回落 `U+E0xx`）。要处理旧盘请用
  备份副本：`--charset work\builds\GR_HASHR\backup\charset_compiled_zh16.json.before_hashr`。

---

## 9. 复现命令与产物索引（全部可重跑）

```powershell
$env:PY = "C:\Users\84363\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
$env:PYTHONIOENCODING = 'utf-8'

# ① 只读普查 (哨兵规模 / 用量 / 对偶空间 / 零用量字)         → audit/recon.txt, audit/recon2.txt
& $env:PY work\builds\GR_HASHR\tools\hashr_recon.py
& $env:PY work\builds\GR_HASHR\tools\hashr_recon2.py
# ② 3 容器之外的同码取证 (TXT/ELF/上下文)                     → audit/txt_scan.txt, audit/probe_other.txt
& $env:PY work\builds\GR_HASHR\tools\hashr_probe_other.py
# ③ 反汇编/立即数取证 (只读 ELF)                              → audit/cave_*.txt, audit/imm_scan.txt
& $env:PY work\builds\GR_HASHR\tools\hashr_imm_scan.py third_party\orig\ps2\slus_out\SLUS_206.13 `
      work\builds\GR_MEMDRIFT\audit\ZH113b_SLUS_206.13.elf work\builds\GR_HASHR\temp\GR_FA2400_K2_SLUS_206.13.elf
# ④ 造盘 (10 条硬断言 + 回读 + 全盘差异窗口)                  → GR_HASHR2400.iso, temp\GR_HASHR2400_build.json
& $env:PY work\builds\GR_HASHR\tools\hashr_build.py --mode k2 --dry-run     # 只算不写
& $env:PY work\builds\GR_HASHR\tools\hashr_build.py --mode k2               # 真造盘
& $env:PY work\builds\GR_HASHR\tools\hashr_build.py --mode base             # 基底盘: 打印鸽笼证明, 退出码 2
# ⑤ 独立终检 (从盘上重读)                                     → audit/verify.txt
& $env:PY work\builds\GR_HASHR\tools\hashr_verify.py
# ⑥ dump_font (K2 几何包装器: NCOL=64/SKIP=2/Y0=3/gate 0xBA)  → font_base_k2/, font_prod/
& $env:PY work\builds\GR_HASHR\tools\hashr_dump_font.py --iso <iso> --out <dir> [--charset <json>] --no-png
# ⑦ 实机 6000 帧 (串行独占)                                   → runs\hashr2400\
& $env:PY work\tools\cap_run.py --iso work\builds\GR_HASHR\GR_HASHR2400.iso `
      --dump work\builds\GR_HASHR\runs\hashr2400 --nav tools\capture\nav_menu_only.txt `
      --maxframes 6000 --snap 30 --wait-first
```

| 路径 | 内容 |
|---|---|
| `work\builds\GR_HASHR\GR_HASHR2400.iso` | ★ 交付 A（修复版 2,400 字成品盘）|
| `work\builds\GR_HASHR\GR_HASHR2400.meta.json` | ★ 交付元数据（sha256/尺寸/构建命令/自检/差异窗口/逐字符表/实机读数）|
| `work\builds\GR_HASHR\GR_HASHR_base.NOT_BUILT.md` | 交付 B 的"未产出"说明 + 可复跑证明 |
| `work\builds\GR_HASHR\temp\GR_HASHR2400_build.json` / `GR_HASHR2400_build.log` | 构建报告（含 42 条搬家表、逐容器命中、差异窗口）|
| `work\builds\GR_HASHR\audit\verify.txt` | ★ 独立终检（判据 1/2/3/4/6）|
| `work\builds\GR_HASHR\audit\diff_spans.json` / `.txt` | ★ **逐字节差异清单**（3,854 段 / 83,067 B，含 base_hex→prod_hex）|
| `work\builds\GR_HASHR\audit\build_base_proof.txt` | 交付 B 的鸽笼证明（`--mode base`，退出码 2）|
| `work\builds\GR_HASHR\audit\recon.txt` / `recon2.txt` | 两盘哨兵/用量/对偶空间普查 |
| `work\builds\GR_HASHR\audit\moves_table.txt` | ★ 逐字符新旧码对照表 + 槽位账 |
| `work\builds\GR_HASHR\audit\charset_selfcheck.txt` | 项目自带 `selfcheck_charset` 结果（ok=True，0 项不合格）|
| `work\builds\GR_HASHR\audit\gate_selfcheck.txt` | 回写链 `legacy_selfcheck_container` 结果（3 容器残留 0、预警 0）|
| `work\builds\GR_HASHR\audit\cave_zh113b_drawstring.txt` / `cave_zh113b_entry.txt` / `imm_scan.txt` | §1.3 的反汇编/立即数取证 |
| `work\builds\GR_HASHR\audit\dumpfont_base_k2.txt` / `dumpfont_prod.txt` | 判据 3 的 dump_font 读数 |
| `work\builds\GR_HASHR\runs\hashr2400\` / `runs\k2_base\` | 实机 6000 帧产物（191 张截图 + `emulog.txt` + `result.json` + `RUN.txt`）|
| `work\builds\GR_HASHR\backup\charset_compiled_zh16.json.before_hashr` | charset 改前备份 |
| `work\builds\GR_HASHR\backup\gate_pairs.json.before_hashr` | 登记表改前备份 |
| `work\builds\GR_HASHR\tools\hashr_*.py` | 全部脚本（既有 ISO 只读）|
