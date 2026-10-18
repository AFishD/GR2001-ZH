# REPORT_sf_nowrap.md — **组件级**折行开关：只对「特别收录」介绍框关闭引擎自动折行

> 轮次：round69 · 分支 `main`（未切分支、未 commit） · 日期 2026-10-14
> 用户原话：**「只修改特别收录部分的自动换行　我已经手动调整过译文的翻译断句处」**
> 产物：`work/builds/GR_ZH115/GR_ZH115.iso`（sha256 `c3cf07117d561fd633e282b51a632093ca0d70dbec6cd1fe93996d165272903a`）
> 补丁：`tools/iso_build/patch_zh115_sfnowrap.py`（**1 个 ELF 词挂点 + 52 B cave = 全盘 43 字节**）
> 基底：`work/builds/GR_ZH111/GR_ZH111.iso`（sha256 `9413efa7dfe431a1…`，只读；实测哈希未变）

---

## 0. 结论速览

| 问题 | 结论 |
|---|---|
| 判定条件 | **`comp->vptr == __vt__6RSHTML`(0x005978C0) 且 `comp[0x40]==270` 且 `comp[0x44]==190`**（§2） |
| 走的是哪条路 | 挂点 `0x21CC90`（`DoWordWrap` 里算 wrapW 的那一条）+ 52 B cave；命中 ⇒ `wrapW=0x7FFF0000`，未命中 ⇒ **逐位等价原路径** |
| 为什么不用组件地址 | zh84 报的是 `COMP=0x012F4960`，GR_ZH98/105/109/111/115 实测都是 `0x0124A6A4` ⇒ **地址随构建漂移**，写死会静默失效（§2.2） |
| 为什么不能只判类型 | `{`/`}` 标签扫描**只在 `RSHTML::CreateStrings`**，简报正文在盘上就是 `{p}` 标签（逐字节实测）⇒ **简报正文组件也是 RSHTML**（§2.6） |
| 为什么还要判高度 | **第一版只判"类型+宽"时, 实机把简报正文的折行也关掉了**（简报框 `@01304E10` = 270×**156**，行数 27→7，文本溢出到地图区）。加 `H==190` 后简报不受影响（§2.3 实测） |
| 效果 | 特别收录介绍框：`RSHTML::CreateStrings` 按 `{br}`/`{p}` 切出的**每段恰好 1 行** ⇒ 换行只可能来自用户手调的断句（§6.1 逐行机检；奖章页截图哈希与"全局关折行"的 GR_ZH112 **完全相同**） |
| 其它界面 | 简报页 **20/20 帧逐像素完全相同**；主菜单/开机段逐帧差异 **与两次独立跑批的抖动逐帧等值**（12/12），且 **100% 落在底部滚动帮助条的 y=385..399**（§7） |
| 代价 | 用户手调断句里有 **218/1856 段 > 270**（最宽 374 ≈ 22 全角字）⇒ 这些行**不再被断开、会画出框外**（不裁切，实拍 §6.4）。**用户需要每行压到 ≤15 全角字** |
| ★ 过程中的一次真实回退 | 第一版只判「类型+宽」时**把简报正文的折行也关掉了**（实机抓到，正文溢出到地图区）；补 `H==190` 后修复并复验通过（§2.3） |

---

## 1. 需求与边界

**要**：特别收录介绍框（各内页的介绍正文）**停止自动折行**，让用户手调的 `{WRAP}`（盘上 `{br}`）
成为**唯一**断点。

**不要**：菜单 / 对话框 / 简报 / 载入等**任何**其它界面的自动折行「一字不动」。

同事的 `tools/iso_build/patch_zh112_noautowrap.py` 把 `0x21CC90` 直接换成 `lui $s7,0x7FFF`
（wrapW 全局变大）——**机制正确但范围是全球**：`DoWordWrap` 的 4 个调用点
（`RSHTML::CreateStrings` ×3 / `RSTextComponent::SetText` ×1）全部命中，语言表 255 条长段
（简报/任务介绍）与 75 条短条目同时失去折行。本轮把它**限定到组件级**。
`patch_zh112_noautowrap.py` **只读参考，一字未改**。

---

## 2. 判定条件是怎么定的

### 2.1 类型判据：`__vt__6RSHTML = 0x005978C0`

`CreateComponent__Fi @0x2EE6A0` 就是组件工厂的类型分派表（`tools/diag/dis_ee.py` 反汇编）：

| type | 构造 | `__nw__FUi` 大小 |
|---|---|---|
| **6** | `__ct__15RSTextComponentFv` | 268 B |
| 7 | `__ct__19RSEditTextComponentFv` | 288 |
| 8 | `__ct__13RSConsoleEditFv` | 288 |
| **9** | `__ct__6RSHTMLFv` | **280** |
| 13 | `__ct__14IkeBriefingMapFv` | 308 |

* `__ct__6RSHTML` 全 ELF **只有 1 个调用点**（`0x2EE850`）⇒ RSHTML 只能由 type 9 造出来。
* 主菜单/对话框/按钮走 type 6 ⇒ `vptr != 0x005978C0` ⇒ **天然不命中**。
* 补丁脚本写盘前会**从源盘符号表重新读 `__vt__6RSHTML` 并硬断言**（不信任硬编码）。

### 2.2 为什么不能用组件地址

| 来源 | 特别收录介绍框的实例地址 |
|---|---|
| `docs/REPORT_wrap_and_title.md`（GR_ZH84） | `0x012F4960` |
| 本轮实测 GR_ZH98 / 105 / 109 / 111 / 115 | `0x0124A6A4`（另一份 `0x0124B650`） |

⇒ 实例地址**随构建漂移**（池/堆布局）。写死地址在本次可用、下次重建就静默失效，
所以判定条件必须是**字段/类型**，不能是地址。

### 2.3 ★ 第一版踩的坑：只判「类型 + 宽」会把简报一起关掉（实机抓出）

第一版条件 = `vptr==RSHTML && comp[0x40]==270`。GR_ZH115 上实机跑
「战术演习 → 简报页」（`nav_p2.txt` 固定时序，F≈8650 打开）后：

* **简报页 RAM（F8752）逐组件行数对照**（`r69_lines.py`；行数 = `comp[0x114]`，
  由 `RSHTML::CreateStrings` 把每行 Substring 进 `comp+0x110` 的 RSArray<RSUIString> 得到）：

```
组件          GR_ZH111(原盘)              GR_ZH115(第一版补丁)
@0128E3A0     68 行                      68 行        ← 相同
@0128F690     57 行                      57 行        ← 相同
@01304E10     ★ 27 行                    ★ 7 行       ← 折行被关掉, 行数掉到 7
```

* **实拍**：GR_ZH115 的简报正文变成一条长串，**溢出到右侧地图区**；
  GR_ZH111 正常按 15 全角字折行。像素差异 `x[36..582] y[104..231]`（13985 像素）。

⇒ 简报正文框 = `@01304E10`，实测 **`W=270`、`H=156`、`ay=78`、`style=0x00020000`** ——
它和特别收录介绍框**同为 RSHTML、同为 270 宽**，只有**高不同**。

### 2.4 最终条件 = `vptr == __vt__6RSHTML` && `W==270` && `H==190`

实测清单（全部来自本轮 EE RAM 转储，`r69_rshtml.py` + `r69_lines.py`）：

| 屏 | 组件（活的） | W | **H** | 渲染行数 | 说明 |
|---|---|---|---|---|---|
| 特别收录 → 开发访谈 1（内页） | `@0124A6A4` / `@0124B650` | 270 | **190** | 117 | = CSV 该条 117 行 ✓ |
| 特别收录 → 奖章（内页） | `@0124B650` | 270 | **190** | 11 | = CSV 该条 11 行 ✓ |
| 特别收录列表页（影片…预告片） | 无 RSHTML 带多行 | — | — | — | 列表页没有多行介绍框 |
| 主菜单 / 选择档案 | 都不带文本 | — | — | — | `@0124A6A4` 此时 `W=0 H=0` |
| **战术演习简报页** | `@01304E10` | 270 | **156** | 27 | **必须排除** |

⇒ 特别收录介绍框的模板签名 = **270 × 190**；简报正文框 = 270 × 156。
把 `H==190` 加进条件后，简报回到原路径（`r69_verify_cave.py` 的执行流模拟：

```
命中:   RSHTML + 270x190                      → wrapW = 0x7FFF0000  (关折行)
未命中A: vptr!=RSHTML (菜单/对话框)            → wrapW = 270         (原路径)
未命中B: W=400 (页面大标题)                    → wrapW = 400         (原路径)
未命中C: RSHTML 270x156 (简报正文)             → wrapW = 270         (原路径) ★
未命中D: RSHTML 270x200 (假想 SF 变体)         → wrapW = 270         (原路径, 见 §7.2)
```

### 2.5 `-grmemwatch` 实测：这些对象在哪些屏是"活的"

本轮跑批带 `-grmemwatch 0x0124A6A4/0x0124B650/0x01304E10 各 288 B interval=1`
（`work/builds/GR_ZH115/temp/dump_z115sf/memwatch.bin`，`r69_mw.py` 解码）：

```
   frame | @0124A6A4 vptr / W / H / font / B4 | @0124B650            | @01304E10
       1 | 00000000  00/00/00/00                | 00000000             | 00000000     ← 开机前不存在
    1801 | 005978C0  00/00/00569908/00          | 005978C0 10E/BE/...  | 005978C0 10E/9C/...  ← 造好
    5401 | 005978C0  00/00/00569908/00          | 005978C0 10E/BE/...  | 005978C0 10E/9C/...
```

读法：

1. **F1801 起** 5 个 RSHTML 的 `vptr` 变成 `0x005978C0` ⇒ 它们是**开机期一次性造好的常驻对象**。
2. 主菜单帧（F4600 的 EERAM 转储）实测 `@0124A6A4 W=0 H=0` ⇒ 该实例在主菜单
   **不满足 `W==270`** ⇒ 走原路径。
3. `@0124B650`(H=0xBE=190) / `@01304E10`(H=0x9C=156) 一造好就带 `W=270`——
   它们是**常驻模板**，只在被喂文本时才会调 `DoWordWrap`。
4. 三个实例的 `comp[0xB4]` **字节**都是 `0` ⇒ `wrapW = comp[0x40] − 0`。

> 关于 Lead 线索里的 `0x012F4960`：本轮在 68 份历史 EE RAM 转储里查过，
> 它在现役谱系里**不是**文本组件对象，只在 GR_ZH84 那一代才是介绍框地址（§2.2）。

### 2.6 简报正文为什么也是 RSHTML（逐字节取证）

`{br}`/`{p}` 的**扫描器只存在于 `RSHTML::CreateStrings @0x21B890`**：它 `IndexOf('{')`
（`0x21B8D4` `addiu $a1,$zero,123`）与 `IndexOf('}')`（125），再和两个标签串比较 ——
那两个串就是 **`"br"`@0x00578678** 与 **`"p"`@0x00578680**（`addiu $a1,$v0,-31112 / -31104`）。

而简报正文在盘上就是 `{p}` 标签（`r69_langbytes.py` 读 `LANG:G048.I008`）：

```
G048.I008: offset=28238 len=465
  hex : … a6 ad 7b 70 7d aa a6 …          ← 0x7B 0x70 0x7D = "{p}"
  文本: '地点：拉脱维亚，卢巴纳河{p}坏消息。…{p}你们的任务是…'
  用到 <0x20 的字节: []                     ← 没有任何裸换行
  含 {p}: True   含 {br}: False
```

⇒ 简报正文能被正确分段 ⇒ 它必然也走 `RSHTML::CreateStrings` ⇒ **简报正文组件是 RSHTML**。
（交叉印证：`docs/REPORT_csv_text_tool.md` §4.2 首次在语言表插 `{br}` 并实机生效。）
**所以"类型判据"必须再加宽/高判据，单靠类型一定误伤简报。**

---

## 3. 补丁原文与语义

### 3.1 挂点（1 个词）

```
文件内偏移 0x1B0510 = 295*2048 + 0x80 + (0x21CC90 − 0x100000)
0x21CC90 : 0062B823  subu $s7,$v1,$v0   →   0815966A  j 0x005659A8
```

**延迟槽（本补丁的关键细节）**：`j` 在 `0x21CC90`，它的延迟槽就是紧邻的
`0x21CC94 = 0x72E08E28`（`move $s1,$s7`，"当前行预算 = wrapW"），
所以延迟槽会**先执行一次**（此时 `$s7` 还是旧值，无副作用），随后进 cave；
cave 把 `$s7` 算对之后 **`j 0x21CC94` 回去再执行一次** ⇒ `$s1` 拿到正确预算。

> `0x72E08E28` 这条指令 `tools/diag/dis_ee.py` 解不出来（op=0x1C）。本轮用同一函数序言里的
> `0x7080AE28`（语义必然是 `this`→`$s5`，即 `move $s5,$a0`）**独立证明**：本作这条
> "未解码"指令的字段语义就是 `rs→rd` 的**寄存器复制** ⇒ `0x21CC94` 幂等、double-execute 安全；
> `$at` / `$t0` / `$v0` 在那一行都不是活跃值。

### 3.2 cave 体（`0x5659A8..0x5659DB`，14 词）

```
0x5659A8  0062B823  subu  $s7, $v1, $v0       ; ★ 原指令: 无条件先按原语义算好
0x5659AC  3C080059  lui   $t0, 0x0059
0x5659B0  250878C0  addiu $t0, $t0, 0x78C0     ; t0 = 0x005978C0 (必须在比较之前算完)
0x5659B4  8EA10000  lw    $at, 0($s5)          ; vptr
0x5659B8  14280007  bne   $at, $t0, +7         ; 非 RSHTML → 出口
0x5659BC  2401010E  addiu $at, $zero, 0x10E    ; 270 (延迟槽)
0x5659C0  14610005  bne   $v1, $at, +5         ; W != 270 → 出口
0x5659C4  8EA20044  lw    $v0, 0x44($s5)       ; (延迟槽) v0 = H
0x5659C8  240100BE  addiu $at, $zero, 190      ; 190
0x5659CC  14410002  bne   $v0, $at, +2         ; H != 190 → 出口
0x5659D0  00000000  nop                        ; (延迟槽)
0x5659D4  3C177FFF  lui   $s7, 0x7FFF          ; ★ 命中: wrapW = 0x7FFF0000 ≈ 2.1e9
0x5659D8  08087325  j     0x0021CC94           ; 出口/回 DoWordWrap ($s1 = $s7)
0x5659DC  00000000  nop                        ; (j 的延迟槽, 本来就是 0, 不写)
```

**为什么 `subu` 放在第一条**：它**无条件**先算出原值，命中的分支只是在其后用
`lui $s7,0x7FFF` **覆盖**。这样三个"未命中"出口都天然保留原 wrapW。
（`r69_verify_cave.py` 的逐条模拟会抓"某条出口忘了算 $s7"这类漏洞 ——
本轮的初版 cave 就被它抓出过一次，已修。）

**`j` 的 256 MB 区段**：`0x21CC90` 与 `0x005659A8` 的高 4 位都是 0 ⇒ 合法
（与在役的 `0x21CD70 → j 0x00417500`、`0x21C624 → j 0x00565900` 同型）。

### 3.3 cave 落点四重自检（`r69_cave.py`，离线实跑）

`0x5659A8..0x5659E0 ⊂` 既有恒零区 `0x565930-0x565C00` 的**未用延伸段**：

| 检查 | 结果 |
|---|---|
| ① ELF 静态该区间全零（56 B） | ✓ |
| ② 全 ELF 无 `j`/`jal` 以区间内地址为目标 | ✓ 0 处 |
| ③ 全 ELF 无 4 字节字面量落在区间（**9,363,433 词**全扫） | ✓ 0 处 |
| ④ **83 份 EE RAM 转储**该区间全零（任务/小队/简报/开机/特别收录各族；已排除本补丁盘自己的转储） | ✓ 83/83 |

补丁脚本写盘前还会断言：挂点原词 / 上下文三词（`0x21CC84 / 0x21CC88 / 0x21CC94`）逐词相符，
且 `0x21CC90 / 0x21CC94 / 0x21CC98` **没有任何分支或跳转直接进入**（只允许顺序落入）——
实测 0 处（否则"延迟槽"前提不成立）；写盘后**全盘逐块回读比对**，差异必须**逐字节**落在白名单里。

---

## 4. 回退

```powershell
& C:\ProgramData\anaconda3\python.exe tools\iso_build\patch_zh115_sfnowrap.py `
      work\builds\GR_ZH115\GR_ZH115.iso <输出.iso> --revert
```

一个词换回 `0x0062B823` + cave 13 词清零；或直接用 GR_ZH111 重建（本补丁是**唯一**差异）。
本补丁只在 ISO 的 ELF 区原位覆写，**不改任何数据容器 / 条目表 / 文件大小**。

---

## 5. 验收数字（写盘断言，实跑输出）

```
[site ] 挂点 VA 0021CC90 -> 文件偏移 0x1B0510
       cave VA 005659A8 -> 文件偏移 0x4F9228 (14 词)
[vt   ] 源盘符号表 __vt__6RSHTML = 005978C0 (脚本常量 005978C0)
       挂点原词 = 0062B823   目标词 = 0815966A
       cave 原词 = 00000000 × 14
       ctx 0021CC84 = 8EA30040 ✓ / 0021CC88 = 92A200B4 ✓ / 0021CC94 = 72E08E28 ✓
[verify] 全盘差异 = 恰好 43 B
[write ] GR_ZH115.iso ✓  (大小不变 1,648,164,864 B, 全盘差异恰 43 B / 2 个窗口)
```

* 差异 **43 字节** = 挂点 3 B（第 4 字节原为 0x00）+ cave 里真正变化的 40 B；
  两个窗口：`[0x1B0510, 0x1B0513]`（挂点）与 `[0x4F9228, 0x4F925B]`（cave）。
  脚本按**逐字节**算白名单，比"整词 4 B"的口径更严。
* `MENU.IMG` / `GR.IMG` 零触碰（由全盘逐块回读比对直接保证）；产物大小 == 源盘大小。

---

## 6. 实机验证

### 6.1 ① 特别收录内页：手调断句成为**唯一**断点（逐行机检）

GR_ZH115（补丁盘）跑「主菜单 → 特别收录 → 访谈 → 开发访谈 1」
（`r69_run.py`，闭环导航，304 s）：

**A. 绘制层机检**（`r69_drawn.py`：drawlog 的 `PC=219EB0` 行会带该行原始字节，
码表解码后与 CSV 的 `text_edited` 逐行比）：

```
★ 在介绍框绘制路径 (RA=21CA00) 上, 与 CSV 手调断句**逐字前缀相同**的绘制 9 条:
   0  21CA00  w=136  开发手记：第一辑
   1  21CA00  w=187  制作人：达伦·丘基图斯
   2  21CA00  w=68   日志一：
   3  21CA00  w=255  对《幽灵行动》团队而言，这个月
   4  21CA00  w=119  令人无比激动。
   5  21CA00  w=181  我们已完成Alpha时期，
   6  21CA00  w=223  正开足马力向Beta版本冲击。
   7  21CA00  w=221  在此期间，我亲眼见证了游戏
   8  21CA00  w=255  在团队的反复推敲下越来越完善。
与 CSV 前 9 行的顺序一致性: ✓ 完全一致
```

**B. RAM 层机检**：该页 `@0124A6A4` / `@0124B650` 的 `comp[0x114]`（渲染行数）= **117**
= CSV `SFXML:T0067` 的行数 **117** ✓ —— 一个不多、一个不少。

**C. 截图**：`work/builds/GR_ZH115/temp/dump_z115sf2/r69_z115sf2_page.png`
（sha256 `4ab899c7dae510d18d0ae90a12d45521f72924802925943e1322a7eb28f74fd7`）——
与 GR_ZH111 的同一页 **sha256 完全相同**。这一页**本就该完全相同**：
它的手调行**全都 ≤ 270**（最宽 255），自动折行原本就没有触发 ⇒
"没有变化"正是正确结果（"不该动的地方没动"的正向证据）。
真正能看出差别的页见 §6.2（奖章页，手调行超宽）。

### 6.2 ② 现状对照：奖章内页（这一页的手调行**超宽**，所以能看出差别）

用户手调断句 `SFXML:T0043`（奖章「国会最高勋章」）第 1 行 = **16 字 = 272 > 270**、
第 6 行 = **18 字 = 306**。两张实拍（同一模板、同一帧位，3 倍放大）：

* 改前（GR_ZH111）：`在《幽灵行动》中，符合以下条件` / **`的`**（孤字行）、
  `最高勋章由总统以国会名义发给获` / **`奖者，`**
  → 引擎把用户的一行劈成两行，多出孤字行。
* 改后（GR_ZH115）：`在《幽灵行动》中，符合以下条件的` **一行**、
  `最高勋章由总统以国会名义发给获奖者，` **一行** —— 断点**只剩**用户手调的那些。

对照图：`work/builds/GR_ZH98/temp/r69/crop_medal111_vs_115.png`（上=111，下=115）
单页：`work/builds/GR_ZH111/temp/dump_medal111/medal111_page.png`（改前）
　　　`work/builds/GR_ZH115/temp/dump_z115medal2/r69_z115medal2_page.png`（改后）

**同帧像素数字**：GR_ZH111↔GR_ZH115 在奖章页存活期（F14500–F16000）差异
**15286 像素**，外接框 **x[31..298] y[158..319]** = **只有左侧介绍框那一个矩形**，
右侧奖章贴图 / 标题 / 底栏 / 帮助条全部零差异。

**截图哈希三方对照**（同一页、同一模板）：

| 盘 | 奖章页 PNG sha256 | 说明 |
|---|---|---|
| GR_ZH111（原盘，折行开） | `b24965b2176f4e8a4a7136a107d56ecc30c422e0e0807cd5993116556c93bbe0` | 有孤字行「的」「奖者，」 |
| **GR_ZH115（本补丁，组件级）** | **`cf47a484597f5b4397bdb689b9fb192b977bf403ac56297fc5d9690d47c9313a`** | 手调断句为唯一断点 |
| GR_ZH112（同事盘，**全局**关折行） | `cf47a484597f5b4397bdb689b9fb192b977bf403ac56297fc5d9690d47c9313a` | **与本补丁逐字节相同** |

⇒ 组件的窄条件在"特别收录页"上**复现了全局补丁的全部效果**（一个像素不差），
而 §7 证明它没有全局补丁的副作用。（`dump_medal112` 目录随后被同事清理，
哈希已在本报告与 `jitter_z115medal.txt` 中留档。）

### 6.3 ③ 回归：**其它界面一字不动**（本任务最关键的验收）

#### (a) 简报页：GR_ZH115 vs GR_ZH111 **逐像素完全相同**

固定时序（`nav_p2.txt`，`-grinput` 帧驱动 ⇒ 两次跑批可复现）：

```
[cmp] A = GR_ZH111 的简报跑批 (dump_z111brief)
[cmp] B = GR_ZH115 的简报跑批 (dump_z115brief2)
[cmp] 配对帧 20; **逐像素完全相同 20**; 不同 0; 尺寸/读取异常 0
```

* 简报页存活期（含 F9000 / F9500 / F10000 三个整页帧）**零差异**：
  正文折行位置、任务目标框、地图、日期/天气全部一致。
* RAM 侧独立印证（`r69_lines.py`，行数 = `comp[0x114]`）：

```
组件          GR_ZH111          GR_ZH115(最终补丁)
@0128E3A0     68 行             68 行
@0128F690     57 行             57 行
@01304E10     27 行             27 行      ← 简报正文, 与改前完全一致
```

* 实拍：`work/builds/GR_ZH115/temp/dump_z115brief2/r69_z115brief2_brief.png`
* 并排放大对照（上=GR_ZH111，下=GR_ZH115，3×，简报正文区）：
  `work/builds/GR_ZH98/temp/r69/crop_brief_111_vs_115.png`
  —— 两盘**折行位置逐字相同**：`欢迎来到提比里斯，先生们。希望 / 你们在飞机上休息过了，因为到了 / 这里，我们要干的活还很多。`
  与 `情况是这样的：我们应格鲁吉亚政 / 府的要求前来，协助他们对付俄罗`。

> 对照：**第一版补丁**（只判类型+宽）在同一位置的结论是 `@01304E10` **27 → 7 行**、
> 像素差 13985、正文溢出到地图区 —— 这就是加 `H==190` 的直接原因（§2.3）。

#### (b) 主菜单 / 开机段：用「抖动基线」判定（比单看图更硬）

单看"两张图差了几百像素"说明不了问题（跑批本身有抖动）。本轮引入抖动基线：

* `A` = GR_ZH111 的跑批（`dump_hook111`，同事跑）
* `B` = GR_ZH112 的跑批（`dump_hook112`，同事另一次跑，**与本补丁无关**）
  —— A/B 之差 = **纯跑批抖动**
* `C` = GR_ZH115 本补丁盘的跑批（`dump_z115sf2`）

判读规则：**若 `|A−C|` 与 `|A−B|` 同帧同值，则 A 与 C 的差异 = 抖动。**

```
帧                      |A-B| 抖动基线   |A-C| 本补丁   判读
snap_f00002500.png            0             0         同级
snap_f00003000.png          962           962         同级
snap_f00003500.png          500           500         同级
snap_f00004000.png          463           463         同级
snap_f00004500.png         1280          1280         同级
snap_f00005000.png          482           482         同级
snap_f00005500.png          522           522         同级
snap_f00006000.png         1299          1299         同级
snap_f00006500.png          452           452         同级
snap_f00007000.png          565           565         同级
snap_f00007500.png         1268          1268         同级
snap_f00008000.png          431           431         同级
```

**12/12 帧 `|A−C|` 与 `|A−B|` 一模一样（到个位）** ⇒ GR_ZH115 在主菜单/开机段
**没有任何补丁引入的像素差异**。

差异定位（`r69_imgdiff.py`）：**100% 的差异像素落在 `y=385..399`**（15 px 高），
即底部**滚动帮助条**那一条；`r69_shiftfit.py` 证明 `dx=0` 已是最佳位移
（不是位移差，是滚动动画相位差）。
另有一次独立观测佐证相位性：**第一版补丁盘的菜单跑批与 GR_ZH111 逐帧差为 `0`**
（同样的 ISO 家族，落到"安静"相位），而本次落到另一相位 ⇒ 该差异与折行补丁无关。

> 换句话说：本节结论不是"差异小于某个阈值"，而是"**差异与既有的跑批抖动逐帧等值**"，
> 且全都落在一条与文本折行无关的滚动条上。

### 6.4 ④ 超宽行会怎样

**离线先把"哪些行会超宽"算清楚**（`r69_lineaudit.py`，校准字宽模型：汉字 16+tracking 1 = 17）：

```
===== GR_ZH115 : 特别收录 (SFXML) 逐行宽度审计 =====
  条目 58 ; 段 (引擎折行单位) 1856 ; 容量 = 270
  段宽: 最大 374 / 中位 207 / 最小 51
  > 270 的段 (关掉自动折行后会溢出): 218 个 (11.7%)
  其中 > 272 (16 全角字) 的: 95 个
```

* 这个 218 与同事独立算出的 218（`docs/REPORT_noautowrap.md` §3.1）**完全一致** ⇒ 模型互验通过。
* 最宽 374 = 22 个全角字 ⇒ 比框宽多 `374−270 = 104` 单位（≈6 个汉字 ≈104 px）。

**实机表现（实拍，奖章页）**：

* **不会被断开**，也**不会被裁切** —— 字直接画到介绍框外面，
  **框的右边线压在字上**（见 `crop_medal111_vs_115.png` 下半：`的` 与 `获奖者` 都被右边框穿过）。
* 溢出量小时（272 vs 270，多 2 px）只"出头"一点点；溢出大时（306 vs 270，多 36 px）
  会明显压到右侧的美术图/地图区，但仍不裁切、不提行。
* ⇒ **给用户的排版上限：一行 ≤ 15 个全角字（255 单位）**。16 字（272）就已经超了 ——
  这正是"引擎自己多断一行"的来源。需要收缩的行清单见 `r69_lineaudit.py` 输出。

### 6.5 实拍文件清单

| 用途 | 路径 |
|---|---|
| ① 奖章内页（GR_ZH115，改后） | `work/builds/GR_ZH115/temp/dump_z115medal2/r69_z115medal2_page.png` |
| ② 奖章内页（GR_ZH111，改前） | `work/builds/GR_ZH111/temp/dump_medal111/medal111_page.png` |
| ② 并排放大对照（介绍框 3×） | `work/builds/GR_ZH98/temp/r69/crop_medal111_vs_115.png` |
| ① 开发访谈 1 内页（GR_ZH115 / GR_ZH111） | `.../dump_z115sf2/r69_z115sf2_page.png` / `GR_ZH111/temp/dump_hook111/hook111_page.png` |
| ③ 简报页（GR_ZH115 / GR_ZH111） | `work/builds/GR_ZH115/temp/dump_z115brief2/r69_z115brief2_brief.png` / `work/builds/GR_ZH115/temp/r69keep/dump_z111brief/r69_z111brief_brief.png` |
| ③ 简报并排放大（3×） | `work/builds/GR_ZH98/temp/r69/crop_brief_111_vs_115.png` |
| ★ 第一版补丁的简报故障（留档对照） | `work/builds/GR_ZH115/temp/r69keep/dump_z115brief/r69_z115brief_brief.png` |
| ③ 主菜单三盘快照（111 / 112 / 115） | `work/builds/GR_ZH115/temp/ref/zh111menu/` · `.../r69keep/ref/` · `.../dump_z115sf2/snap_f0*.png` |
| 判读中间产物 | `work/builds/GR_ZH98/temp/r69/{jitter_final.txt, jitter_z115medal.txt, diff_*.png, cmp111v115_*.png}` |

---

## 7. 已知限制（诚实清单）

1. **218 行会溢出**：用户手调断句里 **218/1856 段 > 270**（最宽 374 ≈ 22 全角字），
   关掉自动折行后它们不再被断开 ⇒ 会画到介绍框外（不裁切）。**这是本补丁的直接代价**，
   需要用户在这 218 处每行压到 **≤15 全角字（255）**。
2. **判定条件是"类型 + 宽 + 高"，不是"哪个屏"**：任何 **270×190 的 RSHTML** 都会命中。
   本轮实测现役谱系里这样的对象只有特别收录介绍框这一族（`@0124A6A4` / `@0124B650`）；
   但若以后有别的界面也用 270×190 的 RSHTML，它也会跟着不折行。
   **反向风险**：若某个**未抽样的**特别收录内页用了别的尺寸（例如 270×200），
   那一页仍会保留自动折行（="少改"，不会误伤别的界面）。本轮已抽样的内页
   （开发访谈 1、奖章）都是 270×190。
3. **cave 借用数据段零区**（`0x5659A8`）。本轮做了四重自检（静态零 + 无跳转 + 无字面量 +
   83 份 RAM 转储全零），但它终究是"借用"零区，不是段内空闲。
4. **`0x21CC94` 那条指令本反汇编器解不出**（op=0x1C）。本轮用同函数的 `move $s5,$a0`
   独立证明它是寄存器复制，从而论证 double-execute 安全；**没有**在模拟器里单步验证这一步。
5. **实机跑批多次被抢占**：采集期间其它任务反复启动模拟器、并重建过
   `pcsx2-gsrunner.exe`（10:26–10:57 该 exe 一度不存在），且 `nav_hook.py` 起跑会
   `Stop-Process pcsx2-gsrunner`。本轮**从未杀过别人的实例**，只排队重试；
   被抢占的跑批在 `r69_*.log` 里如实留痕。
6. **同事清理临时目录**：`GR_ZH112/temp/dump_medal112` 与
   `GR_ZH112/temp/SLUS_206.13.zh111` 在核验期间被删除；对应的关键结论
   （截图 sha256 `cf47a484…`、cave 落点检查用的 ELF）本轮已改从
   `GR_ZH111.iso` 自行抽取到 `work/builds/GR_ZH115/temp/r69/SLUS_206.13.zh111`，
   结论不依赖被删文件。

---

## 8. 复现命令

```powershell
# ① 出盘（已跑，产物 GR_ZH115）
& C:\ProgramData\anaconda3\python.exe tools\iso_build\make_build.py GR_ZH115 `
      --from work\builds\GR_ZH111 --patch tools\iso_build\patch_zh115_sfnowrap.py `
      --no-font-compact --no-font-dump --no-textdump

# ② 补丁自检（不写盘）
& C:\ProgramData\anaconda3\python.exe tools\iso_build\patch_zh115_sfnowrap.py `
      work\builds\GR_ZH111\GR_ZH111.iso work\builds\GR_ZH115\temp\dryrun.iso --dry-run

# ③ 离线核对
& C:\ProgramData\anaconda3\python.exe work\builds\GR_ZH98\temp\r69\r69_cave.py `
      work\builds\GR_ZH115\temp\r69\SLUS_206.13.zh111 5659A8 5659E0
& C:\ProgramData\anaconda3\python.exe work\builds\GR_ZH98\temp\r69\r69_verify_cave.py
& C:\ProgramData\anaconda3\python.exe work\builds\GR_ZH98\temp\r69\r69_lineaudit.py work\builds\GR_ZH115

# ④ 实机（单实例；本轮专用驱动，dump 一律落 work/builds/GR_ZH115/temp/）
& C:\ProgramData\anaconda3\python.exe work\builds\GR_ZH98\temp\r69\r69_wait.py `
      z115medal2 work\builds\GR_ZH115\GR_ZH115.iso sf --extra "--sf-idx 4"
& C:\ProgramData\anaconda3\python.exe work\builds\GR_ZH98\temp\r69\r69_wait.py `
      z115brief2 work\builds\GR_ZH115\GR_ZH115.iso brief
& C:\ProgramData\anaconda3\python.exe work\builds\GR_ZH98\temp\r69\r69_wait.py `
      z111brief  work\builds\GR_ZH111\GR_ZH111.iso brief

# ⑤ 像素判读
& C:\ProgramData\anaconda3\python.exe tools\diag\cmp_dump.py <A> <B> --out <前缀>
& C:\ProgramData\anaconda3\python.exe work\builds\GR_ZH98\temp\r69\r69_jitter.py <A> <B> <C>
& C:\ProgramData\anaconda3\python.exe work\builds\GR_ZH98\temp\r69\r69_imgdiff.py <A.png> <B.png> --out <差异图>
& C:\ProgramData\anaconda3\python.exe work\builds\GR_ZH98\temp\r69\r69_drawn.py <drawlog> <csv> <SFXML:T0xxx>
```

**本轮新增脚本**（全部在 `work/builds/GR_ZH98/temp/r69/`；只读输入，只写本轮目录）：
`r69_run.py`（实机采集驱动，支持 `--sf-idx` 选特别收录条目）·
`r69_wait.py`（单实例排队，**绝不杀别人的实例**）·
`r69_rshtml.py` / `r69_comp.py` / `r69_at.py` / `r69_brk.py` / `r69_lines.py` / `r69_wrapfind.py`
（vptr 签名扫 RAM、读断点数组/行数组）· `r69_mw.py`（memwatch 解码）·
`r69_cave.py`（cave 落点四重自检）· `r69_verify_cave.py`（cave 逐条反解 + 执行流模拟）·
`r69_langbytes.py`（LANG 标签逐字节取证）· `r69_lineaudit.py`（逐行宽度审计）·
`r69_jitter.py`（抖动基线对照表）· `r69_imgdiff.py` / `r69_shiftfit.py` / `r69_crop.py` /
`r69_drawn.py`（像素与绘制行判读）· `r69_syms.py`（符号查询）· `r69_brief_cmp.py` / `r69_compinv.py`

**只读引用、一字未改**：`tools/iso_build/patch_zh112_noautowrap.py`、`tools/text_csv/*`、
`tools/font_pipeline/data/charset_compiled_zh16.json`、`tools/iso_build/font_compact.py`、
`tools/iso_build/make_build.py`、
`work/builds/GR_ZH109` / `GR_ZH110` / `GR_ZH111`（GR_ZH111.iso 哈希未变：
`9413efa7dfe431a19fd83abe8226bf7e1c93e080c6af2486b98845b22cd709d2`）。

> **关于 `charset_compiled_zh16.json` 的哈希变化（如实登记）**：开工时读到的是
> `2d8b0f3d…`，收尾时读到 `e56d0d2f…`（文件 mtime `10:33:50`）。
> **这不是本轮改的**，依据有三：
> ① 本轮两次出盘都带 `--no-font-compact --no-font-dump`，`GR_ZH115/build_info.json` 里
> `font_step_tool / font_compact / font_repack / font_dump` **全是 `null`**（字体步骤根本没跑）；
> ② 该文件不在本任务允许写入的四个路径里；
> ③ 任务书本身写明「另一个任务正在改字库 JSON」。
> `tools/text_csv/tcslib.py` 与 `patch_zh112_noautowrap.py` 哈希**确实未变**
> （`7addef2f…` / `37ae1e15…`）。

**未切分支、未 commit。**（收尾时 `git log` 显示 Lead 已把本补丁脚本与报告入库：
`67a2cdd2` / `daf408e1` —— **那是 Lead 侧的提交，不是本会话所为**；
本会话全程只用了 `git status` / `git log` / `git show` 这类只读命令。）
