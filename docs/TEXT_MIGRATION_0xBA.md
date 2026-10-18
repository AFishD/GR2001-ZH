# 旧单字节码全量迁移 + 回写工具链同步（GATE 0xB1 → 0xBA）

> 任务：`textmig`（B 路）· 基底盘 `work/builds/GR_ZH113b/GR_ZH113b.iso` · 产物盘 `work/builds/GR_TXMIG/GR_TXMIG.iso`
> 地面真值：`work/builds/GR_ZH98/temp/LEAD_CAPACITY_2400.md`（§1.4 / §2 / §3-B / §4.3 / §5）
> 状态：**文本迁移 + 闸门 0xBA 这一层已完成并自证**；**必须与几何路（图集/字形/charset）合并才成盘**（见 §7）。
> ★ **第二轮已执行**（2026-10-15 晚，charset 已被几何执行者合并）：见 **§11** ——
> 4 项任务（①charset 补丁验证 ②ES/FR ③回写链同步 ④重跑迁出最终迁移层）的逐项结果、
> 新产物 `work/builds/GR_TXMIG/GR_TXMIG_r2.iso`（sha256 与 `GR_TXMIG.iso` **完全相同**）、
> ES/FR 的**容量硬阻**（未达成）与 DE/IT 的已知缺陷登记。

---

## 0. 一句话结论

| 判据 | 结果 | 证据 |
|---|---|---|
| 抬闸门后必须迁移的 `0xB1..0xB9` 裸字节，产物盘剩 **0 处** | ✅ | `temp/audit/audit_report.json` `A_after.unpaired = 0` |
| 迁移后按**基底闸门语义**重解，逐字符与基底一致 | ✅ | `B`: MENU:RES/GR:RES/MENU:SF 各 `diff = 0`（2232+2232+595 条） |
| 逐行（CSV 行级）真值一致 | ✅ | `C3`: 5 个来源全部 `0` |
| `0xB1..0xB9` 之外一个字节都不动 | ✅ | `S2` 反向重建 + `S8` 全盘 diff 全落窗口内 |
| 全盘差异 100% 落在计划窗口、窗口外 0 字节 | ✅ | `S8`: 104,427 B / 1241 区间，**窗口外 0** |
| ISO 尺寸不变 | ✅ | 1,648,164,864 B（两侧相同） |
| ELF 4 站点闸门 = 0xBA | ✅ | `S7` 回读 4/4 |
| 回写链自动拒绝遗留旧码 | ✅ | `tools/text_csv/inject_text_csv.py --selfcheck`（+默认写盘路径），4/4 测试通过 |
| **charset 登记 5 个借槽对偶码** | ❌ **未做**（受保护路径） | 见 §7-P1 |

**迁移量 = 3,279 处**（不是 LEAD 表里的 3,073 —— 差 206 处，原因是 LEAD 的统计工具口径不全，见 §1）。

---

## 1. 迁移量：真值 3,279 处，以及 LEAD 表 3,073 的差额来源

### 1.1 逐码 / 逐容器（`temp/build/migrate_report.json`）

| 码 | 字 | MENU:RES | GR:RES | MENU:SF | 合计 |
|---|---|---|---|---|---|
| 0xB1 | △（引擎图标码） | 7 | 7 | 0 | **14** |
| 0xB2 | 键 | 227 | 227 | 2 | **456** |
| 0xB3 | 练 | 211 | 211 | 16 | **438** |
| 0xB4 | 用 | 222 | 222 | 45 | **489** |
| 0xB5 | ✕（引擎图标码） | 21 | 21 | 0 | **42** |
| 0xB6 | 击 | 220 | 220 | 80 | **520** |
| 0xB7 | 小 | 210 | 210 | 43 | **463** |
| 0xB8 | 时 | 202 | 202 | 76 | **480** |
| 0xB9 | 按 | 187 | 187 | 3 | **377** |
| | **合计** | **1507** | **1507** | **265** | **3279** |

### 1.2 与 LEAD 表逐码对账

`work/tools/legacy_singles.py`（LEAD 的统计工具）在基底 CSV 上的输出是
`0xB1:14 0xB2:454 0xB3:423 0xB4:470 0xB5:42 0xB6:459 0xB7:423 0xB8:412 0xB9:376 = 3073`，
**本工具的独立复现逐码逐值相同**（`temp/audit/audit_report.json` `A_before`，见 §4）。

差额 **+206 = 3279 − 3073**，全部落在 `MENU:SF`（265 vs 59）：

| 区域 | 处数 | `dump_all_text.py` 看得见吗 |
|---|---|---|
| `<text>…</text>` 正文，**长度 ≤ 400 B** | 58 | ✅ 看得见（`RE_NODE = >([^<>]{2,400})<`） |
| `<text>…</text>` 正文，**长度 > 400 B** | **192** | ❌ **看不见**（正则上限 400，且正文里没有 `>`/`<` 可重新起配） |
| `<item/group/studio name="…">` 标题属性 | **15** | ❌ 看不见（dump 只抓 `studio`/`group` 的 name，且是当 `section:` 键） |
| 其中被 `RE_GRP` 抓到的 studio/group 名 | 1 | ✅ |
| **dump 口径合计** | **59** | = LEAD 表的 SF 列 ✓ |

⇒ **LEAD 表的 3,073 是"dump 可见范围"的下界，不是盘上真实需要迁移的量。**
两类被漏掉的东西都是**上屏文本**（长正文是条目正文；`name=` 是"特别收录"标题通道，
`docs/REPORT_final_364.md` §2/§6.4 已定性，回写链本来就有独立的"属性通道"）。
本工具按**真值 3,279** 迁移（`sf_region_counts()` 在每次运行里复算这个拆解并打进日志）。

### 1.3 字符身份是**从盘上反查出来的**，不是照抄表

`LEAD_CAPACITY_2400.md` §1.4 的表里 `0xB9` 写作 `—`（未知）。本轮从三处独立取证定为 **按**：

* `work/builds/GR_ZH98/temp/r82/charset_before_r82.json`（r82 抬闸门**之前**的 charset）
  的 `codes`：`0xB2=键 0xB3=练 0xB4=用 0xB6=击 0xB7=小 0xB8=时 0xB9=按`；
* 现行 charset 的 `codes` 仍保有 `0xB6..0xB9` 四条；
* **盘上字形辨认**（本轮新证据）：单字节码的字形走 `FONT.RES` 记录（索引 = 码 − 0x20），
  把记录 149..153 的矩形按引擎口径（GIF 封包行映射）取出来就是
  `✕(宽空格矩形) / 击 / 小 / 时 / 按` —— 见 `temp/handoff/glyph_slot*.png`
  （2347 = 小、2345 = 按，逐像素目视确认）。

`0xB1` = △、`0xB5` = ✕ 由 `tools/text_csv/icon_table.py` 定性（引擎在 `DrawString` 里写死的
两个文本图标码），并已由 r82 的 `_expand_zh121` 记录交叉确认（"△ 也改对偶，否则会被当 lead 吞掉"）。

### 1.4 迁移映射（产物盘实际写入的对偶码）

| 旧单字节码 | 字 | 新对偶码 | slot | 来源 |
|---|---|---|---|---|
| 0xB1 | △ | `0xB1A1` | 1504 | charset `pair_of`（已有） |
| 0xB2 | 键 | `0xB1A2` | 1505 | charset（r82 迁入） |
| 0xB3 | 练 | `0xB1A3` | 1506 | charset（r82 迁入） |
| 0xB4 | 用 | `0xB1A4` | 1507 | charset（r82 迁入）＝ 任务书给的锚点 ✓ |
| 0xB5 | ✕ (U+E0B5) | `0xB9FE` | **2349** | ★ 借槽 |
| 0xB6 | 击 | `0xB9FD` | **2348** | ★ 借槽 |
| 0xB7 | 小 | `0xB9FC` | **2347** | ★ 借槽 |
| 0xB8 | 时 | `0xB9FB` | **2346** | ★ 借槽 |
| 0xB9 | 按 | `0xB9FA` | **2345** | ★ 借槽 |

借槽规则：闸门 0xBA 容量 = `(0xBA−0xA1)×94 = 2350` slot（0..2349），charset 已占 0..1871
⇒ 从**顶部**往下借 5 个（2345..2349），把 **1872..2344（473 个）**留给几何路新增字形。
借条：`work/builds/GR_TXMIG/migration_pairs.json`（= 工具的 `migration_pairs.json`）。
合并清单：`work/builds/GR_TXMIG/charset_pairs_patch.json`。

---

## 2. 工具（都可复用，全部有 `--help` 级注释）

| 工具 | 作用 |
|---|---|
| `work/tools/migrate_legacy.py <src.iso> <dst.iso> [--base-gate 0xB1] [--gate 0xBA] [--reserve-slots] [--pairs-in/--pairs-out] [--dry-run]` | ★ 全量迁移（3 容器 + 结构/长度前缀维护 + ELF 闸门 + 8 条内置硬自检 + 全盘 diff 窗口） |
| `work/tools/migrate_legacy_audit.py <iso> --ref-iso <base.iso> [--csv/--ref-csv] [--pairs ...]` | ★ **独立实现**的验收（闸门感知 legacy-singles 复测 + ISO 级逐字符 + CSV 行级三方对账） |
| `work/tools/migrate_selfcheck_test.py` | 闸门自检的 正/负/回归 三向测试（4/4 PASS） |
| `work/tools/migrate_glyph_handoff.py <src.iso>` | 借槽 5 个字的**原字形导出**（bitmap + PNG + 目标格坐标），交给几何路直接 blit |

复现（已实跑）：

```powershell
# 干跑（只报告 + 自检，不写盘）
python work/tools/migrate_legacy.py work/builds/GR_ZH113b/GR_ZH113b.iso `
    work/builds/GR_TXMIG/GR_TXMIG.iso --reserve-slots --dry-run --out work/builds/GR_TXMIG/temp/build

# 出盘
python work/tools/migrate_legacy.py work/builds/GR_ZH113b/GR_ZH113b.iso `
    work/builds/GR_TXMIG/GR_TXMIG.iso --reserve-slots --out work/builds/GR_TXMIG/temp/build

# 独立验收
python work/tools/migrate_legacy_audit.py work/builds/GR_TXMIG/GR_TXMIG.iso `
    --ref-iso work/builds/GR_ZH113b/GR_ZH113b.iso `
    --csv work/builds/GR_TXMIG/temp/after/all_text.csv `
    --ref-csv work/builds/GR_TXMIG/temp/before/all_text.csv `
    --pairs work/builds/GR_TXMIG/temp/build/migration_pairs.json `
    --out work/builds/GR_TXMIG/temp/audit

# 工具链自检
python tools/text_csv/inject_text_csv.py --csv . --src work/builds/GR_TXMIG/GR_TXMIG.iso --selfcheck
```

---

## 3. 构建器内置自检（`migrate_legacy.py`，任一条失败 ⇒ `[!!]` + **不写盘**）

| 自检 | 内容 | 实跑结果 |
|---|---|---|
| `[S1]` | 每个待迁移字节有字、每个字有合法对偶码（lead < gate、trail ∈ [A1,FE]） | 9/9 档 ✓ |
| `[S2]` | **反向重建**：新载荷换回盘上原字节 ⇒ 逐字节 == 源 blob（等价于"除载荷区间外一个字节都没变"，改长也成立） | ✓ |
| `[S3]` | 逐载荷按**基底闸门**重扫 ⇒ 裸 `0xB1..0xB9` = 0 处，且重扫到的迁移 lead 数 == 写入数 | 0 处 ✓ |
| `[S4]` | 载荷之外（结构区/陈旧尾巴）的同类字节**只登记不阻断**（它们是长度/属性数字字段） | 结构区 846+846+368、尾巴 56+56+9 处，全部不在载荷内 ✓ |
| `[S5]` | 逐载荷：基底语义解出的字序列 == 新闸门语义解出的字序列 | 0 差异 ✓ |
| `[S6]` | 新载荷 == 解码文本的**规范编码**（无非法/非规范写法；既存缺陷单独登记） | 既存缺陷 0 条 ✓ |
| `[S7]` | 回读产物盘：3 容器 blob 逐字节 == 目标、IMG 条目表 `off/stored/real` 未动、ELF 4/4 = 0xBA | ✓ |
| `[S8]` | ISO 尺寸不变 + 全盘差异全落窗口内 | ✓（见 §6） |

结构维护方式（关键）：载荷变长 ⇒ **只改该条目的 4 B 长度前缀**；整个容器的解压总长**严格不变**，
增长吃 `used_end` 之后的**陈旧尾巴**：

* `EN_STRINGS.RES@MENU/GR`：各裁掉 1507 B 尾巴，**其中非零 0 B**（纯零填充）✓
* `EN_SPECIAL_FEATURE.XML`：裁掉 265 B，全部非零 —— 尾巴内容是 `0D 0A` 重复的**换行填充**
  （`xml_tail_start` 之后 36,385 B 全是 CRLF）⇒ 裁剪安全 ✓

⇒ **IMG 条目表（off/stored/real）一个字节都没动**，其余 682 条条目、名字区、哈希表零改动。

---

## 4. 独立验收（`migrate_legacy_audit.py`，另一套代码重验）

容器/条目表自己 mmap 走 IMG 表；LANG 解析直接用 **`dump_all_text.py` 用的那个
`tools/hanliu/tools/text_replace.parse_expanded_groups`**；LZO 用 hanliu 的 `lz77_decode`；
SFXML 用与 dump 完全相同的正则。**不是自己验自己。**

### `[A]` legacy-singles 复测（闸门感知）

| 盘 | 基底闸门解析（≡ `legacy_singles.py`） | 新闸门解析：`0xB1..0xB9` 里"不是合法对偶 lead"的裸字节 |
|---|---|---|
| 基底 `GR_ZH113b`（旧） | **3073 处**（逐码与 LEAD 表相同） | 2320 处（＝抬闸门必然踩到的地雷） |
| 产物 `GR_TXMIG`（新） | 3386 处 —— **旧口径的假阳性**（见下） | **0 处** ✅ |

★ **为什么必须带闸门**：迁移后 `0xB1..0xB9` 是**对偶码的 lead**（△=`0xB1A1`、按=`0xB9FA`…）。
拿 `legacy_singles.py` 的旧解析（只把 `0xA1..0xB0` 当前导）去读产物盘，每个对偶码都被拆成
"一个裸首字节 + 一个裸尾字节"，解析随之**错位**，于是数出 3386 处假阳性。
`legacy_singles.py` 的 usage 本来就写了 `[gate_hex]`（`work/tools/legacy_singles.py:5`），
**只是没有实现**（代码从不读 `sys.argv[2]`）；而该文件不在本轮写入范围（见 §7-P3）。

正确判据（闸门口径）＝ 产物盘 **0 处**，且这 0 是**可证**的：产物盘上每个 `0xB1..0xB9` 字节
都是本次插入的对偶 lead（`[S3]` 自洽计数），逐码计数（`--selfcheck` 输出）：
`0xB1:667×2 / 0xB9:840×2` 等与迁移账目一一对应。

### `[B]` ISO 级逐字符一致

| 容器 | 条目 | 解压长（产物/基底） | 逐字符不同 |
|---|---|---|---|
| `EN_STRINGS.RES@MENU` | 2232 | 128,545 / 128,545 | **0** |
| `EN_STRINGS.RES@GR` | 2232 | 128,668 / 128,668 | **0** |
| `EN_SPECIAL_FEATURE.XML` | 595（正文+标题+name 属性） | 116,486 / 116,486 | **0** |

### `[C]` 行级三方对账（CSV 的 `zh` 列 / 闸门真值 / stock dump 口径）

| 来源 | 行 | `[C0]` 复现官方口径 | `[C1]` 基底 CSV 就解错 | `[C2]` 产物 CSV 因 charset 未登记 | `[C3]` ★真值逐行不同 |
|---|---|---|---|---|---|
| MENU:RES | 2192→2192 | 0 | 275 | 331 | **0** |
| GR:RES | 2192→2192 | 0 | 275 | 331 | **0** |
| MENU:SF | 441→441 | 0 | 18 | 18 | **0** |
| MENU:TXT | 1→1 | 0 | 0 | 0 | **0** |
| GR:ATR | 2385→2385 | 0 | 0 | 0 | **0** |

* `[C0] = 0` 证明我对官方 dump 口径的复现是逐字符正确的，下面的数才可信；
* `[C1] = 568 行` 是**官方 dump 在基底盘上就已经解错的行数**（"重配对"在 dump 层的表现）。
  底层的处数：**1227 处**（603+603+21）旧单字节码被 pairs-first 吃成了对偶码
  —— 这正是"基底 CSV 的 `zh` 不是基底盘真值"的原因，所以判据 (a) 必须用**闸门真值**比，
  不能拿两份 stock CSV 的 `zh` 直接相减；
* `[C2] = 680 行` 全部来自 **§7-P1（charset 未登记 5 个借槽对偶码）**：引擎侧无影响，
  但读 charset 的脚本会把产物盘上这 5 个字解错；
* `[C3] = 0` 是判据 (a) 的行级形式：**基底真值 == 产物真值**。

### `[D]` 官方 `cmp_text_csv.py`（任务书点名的口径）

`temp/cmp_text_csv.txt`：`hex_zh` 不同的行 = **781**（GR:RES 385 / MENU:RES 385 / MENU:SF 11）。
这是**预期**：`hex_zh` 就是字节本身，迁移必然改字节。解码文本的一致性由 `[B]/[C3]` 证明。
（另：行数 7715 → 7716、key 交集 7372 —— SF 的行键是 `node@0x偏移` 与 `section:名字`，
两者**都随迁移漂移**，所以 SF 的行键必然对不上；这是 dump 行键的设计问题，已在
`migrate_legacy_audit.py` 的 `payload_rows()` 里改成**稳定序键**并在注释里写明。）

---

## 5. 逐字符一致性证明（三层，互相独立）

1. **构建器层**（`[S5]/[S6]`）：每个载荷在**基底闸门语义**下解出的字序列 == 在新闸门语义下解出的
   字序列；且新载荷 == 该文本的规范编码。基底盘用 `codes` + **旧单字节码→字**补表解码
   （现行 charset 早已把 0xB2/0xB3/0xB4 从 `codes` 摘掉，不补表会得到 U+E0B2 这种占位而误判）。
2. **ISO 层**（`[B]`）：另一套独立代码从两张盘各自解析出 2232/2232/595 条载荷逐字符比对 ⇒ 0。
3. **行层**（`[C3]`）：CSV 行级真值比对 ⇒ 5 个来源全 0。

---

## 6. 全盘差异窗口（`[S8]`）

```
ISO 尺寸 1,648,164,864 B == 源盘 ✓
全盘差异 = 104,427 B / 1241 个连续区间 ; 窗口外差异 = 0
窗口 (7 个, 逐窗口差异字节数 = 该容器压缩帧里真正变了的字节):
  [0x0F034F50, +47619) GR.IMG#902   EN_STRINGS.RES@GR         差异 32,150 B / 400 区间
  [0x0623A0800, +49700) MENU.IMG#283 EN_SPECIAL_FEATURE.XML    差异 32,152 B / 400 区间
  [0x0623AD000, +47570) MENU.IMG#25  EN_STRINGS.RES@MENU      差异 40,121 B / 437 区间
  [0x003AA768, +4)  ELF 0x416EE8   差异 1 B  (只动立即数低字节)
  [0x003AA9E0, +4)  ELF 0x417160   差异 1 B
  [0x003AAD9C, +4)  ELF 0x41751C   差异 1 B
  [0x004F8F24, +4)  ELF 0x5656A4   差异 1 B
  ---------------------------------------------------------------
  合计 = 32,150 + 32,152 + 40,121 + 4 = **104,427 B** ✓ (与报告 JSON 的 diff.n 一致)
```

4 个 ELF 站点：`0xB1 → 0xBA`，每站点**只动最低字节**（`0x2CA900B1 → 0x2CA900BA` 等；
VA→ISO = `VA − 0x6C780`，与 `docs/REPORT_probe_lead_limit.md:36-39` 的锚点一致）。

容器帧（压缩后）都装得进原槽位：

| 容器 | 帧（原 → 新） | 槽 | 余 | 重压子流 |
|---|---|---|---|---|
| `EN_STRINGS.RES@MENU` | 32,696 → 32,847 | 47,570 | 14,723 | 5/8 |
| `EN_STRINGS.RES@GR` | 32,697 → 32,848 | 47,619 | 14,771 | 5/8 |
| `EN_SPECIAL_FEATURE.XML` | 41,279 → 41,418 | 49,700 | 8,282 | 8/8 |

未变子流**照搬原压缩字节**（逐字节相同），变了的子流重压并做解压回环断言。

---

## 7. 未达成项 / 交给别人（如实列出）

### P1 ★ charset 里没有这 5 个借槽对偶码（**唯一的硬缺口**）

`charset_compiled_zh16.json` 是几何路（`geom2400`）的受保护路径，**本轮没写它**。
后果与处置：

* **引擎侧无影响**：引擎的 slot 由 `(lead,trail)` 直接算（`slot=(lead−A1)*94+(trail−A1)`），
  不读 charset；只需图集在那个 slot 上有字形；
* **工具链侧有影响**：`dump_all_text.py` / 任何读 charset 的脚本会把产物盘上
  `击/小/时/按/✕` 这 5 个字解成"单字节 + 尾字节"（实测 `[C2]` = 680 行）；
* **已做的兜底**：新增 `tools/text_csv/gate_pairs.json`（5 条），`tcslib.load_gate_pairs()`
  被自检与编码读取 ⇒ 工具链**现在就能正确工作**（`--selfcheck` 在产物盘上 0 残留 + 退出码 0）；
* **必须做的事**（几何路/LEAD）：按 `work/builds/GR_TXMIG/charset_pairs_patch.json` 把 5 条并入
  `pair_of`、把 `0xB6..0xB9` 从 `codes` 摘掉（否则它们随时会被编码器写成裸前导字节）。
  合并后重跑一次本工具即可（它优先用 charset 的对偶码，借条自动作废）。

### P2 ★ 产物盘必须与几何路合并才成盘

本轮产物 = 文本已迁移 + ELF 闸门 0xBA，**图集一个字都没动**（`COMMON.PAK`/`FONT.RES`/
条目表/charset 全部逐字节未改）。所以在合并前：

* 借槽 5 个字（slot 2345..2349）在图集上**还没有字形** ⇒ 实机上是空白；
* 几何路需要：图集 `h 512→644`、网格列 `62→64`、字形铺到 slot 0..2344（473 个新字），
  并把 `temp/handoff/glyph_handoff.json` 里 4 个字的 bitmap blit 到
  `target_cell`（row 36, col 41..44, y=626）；
* ✕（slot 2349）**图集里没有现成字形**：0xB5 是引擎图标码，它的 `FONT.RES` 记录 149
  用的是"宽空格"矩形 `(480,213)-(490,229)`（与 f364 记录 95 同矩形）⇒ 必须从 UI 图标资源
  或 TTF 另取 ✕（`handoff.usable_as_glyph=false` 已标注）。

### P3 `work/tools/legacy_singles.py` 的 `[gate_hex]` 参数未实现（该文件不在本轮写入范围）

其 usage 写了 `python legacy_singles.py <all_text.csv> [gate_hex]`，但代码从不读第二个参数。
**一行修法**（请 LEAD 决定是否授权）：

```python
gate = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0xB1      # 基底闸门 = 前导上界
...
        if 0xA1 <= c < gate:          # 原为 0xA1 <= c <= 0xB0
            i += 2
            continue
```
在此之前，请用 `work/tools/migrate_legacy_audit.py [A]`（闸门口径，产物盘 `0xB1..0xB9`
未配对裸字节 = 0）作为判据 —— 它同时复现旧口径（基底盘 3073 逐值相同）以证明等价性。

### P4 ★ 新发现：非英文语言表也带裸旧码，**不在** LEAD 声明范围内（需 LEAD 裁决）

本轮的**全 IMG 条目扫掠**（`work/tools/migrate_scan_all_entries.py`，4,756 个条目全解压扫一遍）
与逐表体检（`work/tools/migrate_scan_lang_tables.py`）把"迁移范围是不是真的只有 3 个容器"
这件事查实了：

| 条目（各 2 份拷件） | 解压 B | LANG 解析 | **载荷**裸旧码 | 语言 |
|---|---|---|---|---|
| `EN_STRINGS.RES`（MENU#25 / GR#902） | 128,545 / 128,668 | OK（2232 条） | **1507 ×2** | 中文（已迁移 ✓） |
| `ES_STRINGS.RES`（MENU#27 / GR#904） | 142,148 | OK（2232 条） | **28 ×2 = 56** | 西班牙文原文 |
| `FR_STRINGS.RES`（MENU#28 / GR#907） | 149,664 | OK（2232 条） | **29 ×2 = 58** | 法文原文 |
| `DE_STRINGS.RES`（MENU#26 / GR#900） | 146,910 | **失败**（第 60 组失步，前 1704 条可读⇒29 处） | 37 ×2（全 blob） | 德文原文 |
| `IT_STRINGS.RES`（MENU#29 / GR#910） | 139,082 | **失败**（第 ~369 条失步，21 处） | 38 ×2（全 blob） | 意大利文原文 |

* `*.MIS` / `*.ATR` / `*.TXT` / `IGORHELP.TXT`：全 IMG 扫掠里**一个条目都没有**裸旧码
  ⇒ LEAD §1.4 那句"英文原文，0 处"**首次有了独立证据**（也解释了为什么 `dump_all_text` 的
  6 个来源里它们全是 0）✓
* 其余 2,239 个"命中"条目都是**二进制资源**（`.PSS` 视频 66 个 / `.RSB` 纹理 551 个 /
  `.BMZ` `.QOZ` `.QOB` `.POL` `.SH` `.SB` 模型粒子…… 合计 2,757 万字节）—— 那些字节是像素/顶点/
  音频数据，引擎从不按文本读 ⇒ **原始字节扫描对二进制资源是假阳性**，只有"语言表 + 那 3 个容器"
  才是真文本。`NTSC_IKE.RES`/`IKE.RES`（234 处）也不是文本表（头 `03000000 69000000 …`，
  浮点/矩阵结构）。
* **对迁移的实际影响**：这 4 张表**没迁**（LEAD §1.4 明确"迁移范围只在 3 个容器"，
  本执行者不越界）。它们在基底盘上一直是**未汉化的原文**：0xB1/0xB5 在它们里面是引擎图标码
  （照旧由图标路径画），其余 `0xB2..0xB9` 会走 FT 记录表画出中文记录（历史遗留的视觉瑕疵）。
  抬闸门后若引擎**真的渲染**这些表，那 ~114 处（ES 56 + FR 58）会被当对偶前导吞字；
  DE/IT 另外还有结构异常、`parse_lang`/`parse_expanded_groups` 都解不动（**既存缺陷**）。
* **建议**：若 LEAD 判定"主机语言 = ES/FR/DE/IT 时会被渲染"，则需要在**发布前**补做 ——
  同一套变换直接可用（ES/FR 是标准 LANG 表，改 `migrate_legacy.py` 的容器清单即可；
  DE/IT 得先解决结构失步）。若判定不会渲染（US 版按主机语言取表，汉化只写了 EN），
  则本条**只需登记**，不必动。**这是 LEAD 的裁决项，不是本执行者能自决的范围。**

### P5 未做（本轮范围之外）

* **未跑模拟器**：本轮的判据全部是盘上取证（字节/结构/解码），没有实机验证；
  实机 6000 帧那条验收属 LEAD（且本产物在合并前不宜上机 —— 见 P2）。
* **未动 `dump_all_text.py` 的 SF 抽取口径**（`RE_NODE` 上限 400 + 缺 `name=` 属性）：
  这是 §1.2 那 206 处漏统计的根因，但该文件不在本轮写入范围。建议后续把
  `extract_xml` 换成 `parse_sfxml + parse_xml_attrs`（回写链已有现成函数），
  否则每次做文本统计都会低估 SF。
* **`GR_ZH124/125`、`GR_F364/F365` 的历史乱码未修**：它们各自有 r83/r82 时期的
  "半迁移"文本（实测 `GR_F365` 仍能在 3 个容器里各查到 1 处裸旧码，`--selfcheck` 已能点名）。
  本轮只对 `GR_ZH113b` 这条干净线做了全量迁移。

---

## 8. 回写工具链同步更新（任务 4）

备份（改前）：`work/builds/GR_TXMIG/backup/tcslib.py.bak`、`inject_text_csv.py.bak`。

### `tools/text_csv/tcslib.py`（**追加**一节，未改任何既有行为）

| 新增 | 作用 |
|---|---|
| `read_decode_gate(iso)` | ★ 从**盘上 ELF 4 站点**实测解码闸门（4 处不一致就报错）—— 闸门是**盘的属性**，不是全局常量 |
| `legacy_window(gate)` | 检查窗口 `[0xB1, gate)`；`gate ≤ 0xB1` ⇒ **空窗口**（老盘零行为变化） |
| `scan_legacy_residue(data, gate, pairs)` | 找"旧闸门之下的裸单字节码"（载荷级） |
| `assert_no_legacy_residue(...)` | 有残留 ⇒ 抛 `LegacyCodeError`，报**逐码清单 + 首例 + 修法** |
| `legacy_selfcheck_container(c, blob, gate, extra_pairs)` | 对**新 blob** 自检（LANG 条目 payload + SFXML 正文 + `name=` 标题属性） |
| `load_gate_pairs()` / `gate_pairs.json` | 借槽对偶码登记表（charset 未合并时的过渡） |
| `charset_gate_warnings(cs, gate, extra)` | 表级预警：`codes` 里落在 `[0xA1,gate)` 的字（含它的对偶码与来源） |

### `tools/text_csv/inject_text_csv.py`

* **默认路径**：重压前对每个容器的**新 blob** 调 `legacy_selfcheck_container()`
  （`tools/text_csv/inject_text_csv.py:1722-1727`）—— 有残留即 `[!!]` **拒绝写盘**；
* **`--selfcheck`**（新开关，等价物）：不读表、不写盘，只回答"这张盘能不能安全注入"，
  逐容器打印残留数与合法对偶 lead 计数；**退出码 2 = 拒绝**（为此把
  `if __name__ == '__main__': main()` 改成 `sys.exit(main())`，普通路径仍返回 0）；
* 老盘（gate 0xB1）上**一个字节都不查**（窗口为空）⇒ 既有工作流零影响。

### 三向测试（`work/tools/migrate_selfcheck_test.py`，`temp/selfcheck_test.log`）

| 用例 | 期望 | 实测 |
|---|---|---|
| 正：`GR_TXMIG`（gate 0xBA，已迁移） | 残留 0 | 0 / 0 / 0 ✓ exit 0 |
| 负：合成载荷 `41 42 B6 20 43`（裸 0xB6）与 `B9 41` | 拦下 | 两例都抛 `LegacyCodeError` ✓ |
| 正：合成载荷 `B9 FB 41`（合法对偶码 时） | 放行 | 放行 ✓ |
| 回归：`GR_ZH113b`（gate 0xB1） | 窗口为空、0 查询 | ✓ |
| 负（真实盘）：`GR_F365`（gate 0xB5，历史未迁移盘） | 拒绝 | 3/3 容器拒绝 ✓ |

---

## 9. 产物清单（`work/builds/GR_TXMIG/`）

指纹（SHA-256，两侧尺寸都是 1,648,164,864 B）：

| 盘 | SHA-256 |
|---|---|
| 基底 `work/builds/GR_ZH113b/GR_ZH113b.iso` | `ff3abd3c50e380f666955ccb6226b67198e181589c0db9b4d52e4643208f6445` |
| 产物 `work/builds/GR_TXMIG/GR_TXMIG.iso` | `c3c1e6c5f9535bb30d25c6ec3a9c84ecda509351dc8a055aad64be426a3dd2de` |

★ 基底盘哈希与 charset 元数据 `_font_compact.iso_sha256` / `iso_version = GR_ZH113_B`
**逐字符相同** ⇒ "基底盘 = 被 charset 盖章的那张 GR_ZH113b" 有第三方出处，不是我这边认定的。

| 路径 | 内容 |
|---|---|
| `GR_TXMIG.iso` | ★ 产物盘（文本已迁移 + ELF 闸门 0xBA；尺寸与基底相同） |
| `migration_pairs.json` / `charset_pairs_patch.json` | 借槽借条 / 给 charset 所有者的合并清单 |
| `backup/tcslib.py.bak`、`backup/inject_text_csv.py.bak` | 改前备份 |
| `temp/before/all_text.csv`、`summary.txt` | 基底盘全量文本 dump（迁移前基线） |
| `temp/after/all_text.csv`、`summary.txt` | 产物盘全量文本 dump（迁移后） |
| `temp/legacy_singles_before.txt` / `legacy_singles_after_stock.txt` | `legacy_singles.py` 在基底/产物 CSV 上的**原样输出**（含 3386 假阳性的现场） |
| `temp/cmp_text_csv.txt` | 官方 `cmp_text_csv.py` 输出（781 行 hex 变化，见 §4） |
| `temp/build/migrate_report.json` + `.log` | 构建器全量证据（逐容器/逐码/窗口/自检） |
| `temp/audit/audit_report.json` + `.log` | 独立验收全量证据（A/B/C 段） |
| `temp/selfcheck_test.log` | 工具链自检三向测试 |
| `temp/handoff/glyph_handoff.json` + `glyph_slot*.png` | 5 个借槽字的原字形与目标格 |
| `temp/dry*.log` | 各次干跑日志（S1..S6 逐步通过的过程） |

---

## 10. 纪律与范围声明

* **未** commit / 未切分支 / 未 merge；历史 ISO、`third_party/orig/**`、PCSX2 配置只读；
* 只写了：`work/builds/GR_TXMIG/**`、`work/tools/migrate_*.py`、`docs/TEXT_MIGRATION_0xBA.md`、
  `tools/text_csv/**`（`tcslib.py` / `inject_text_csv.py` 改前已备份，`gate_pairs.json` 新增）；
* **未** 动图集 / `COMMON.PAK` / `FONT.RES` / IMG 条目表 / charset JSON：
  `[S7]` 回读证明前两者与条目表逐字节未变；
* 每条结论都有命令或文件证据（见上表路径）；未达成的项已在 §7 逐条列出（P1 是硬缺口）。

---

## 附：`inject_text_csv.py --selfcheck` 在产物盘上的实测输出（节选）

```
#   实测闸门   = 0xBA  (ELF 4 站点 ['0x416ee8', '0x417160', '0x41751c', '0x5656a4'])
#   检查窗口   = 0xB1..0xB9
#   gate_pairs = 5 条 (.../tools/text_csv/gate_pairs.json)
#   [表级预警] charset codes 里还有 4 个字落在 [0xA1,0xBA) (它们不能按单字节码写出):
#       '击' = 0xB6  (对偶码 0xB9FD, 来自 gate_pairs.json)
#       '小' = 0xB7  (对偶码 0xB9FC, 来自 gate_pairs.json)
#       '时' = 0xB8  (对偶码 0xB9FB, 来自 gate_pairs.json)
#       '按' = 0xB9  (对偶码 0xB9FA, 来自 gate_pairs.json)
   [gate] EN_STRINGS.RES@MENU: 合法对偶 lead 计数 0xA1:5452 … 0xB1:667 0xB9:840
#   EN_STRINGS.RES@MENU      解压  128545 B · 残留 0 处 ✓
#   EN_STRINGS.RES@GR        解压  128668 B · 残留 0 处 ✓
#   EN_SPECIAL_FEATURE.XML   解压  116486 B · 残留 0 处 ✓
# 结论: ✓ 本盘所有文本容器在闸门 0xBA 下都没有"旧单字节码"残留
```

---

# 11. ★ 第二轮执行报告（2026-10-15 晚 · charset 合并后）

> 任务书：`work/builds/GR_ZH98/temp/LEAD_CAPACITY_2400.md` **§15**（§15.1 / §15.3 / §15.4）+ §14
> 本轮交工的 4 项：①charset 补丁验证 ②补做 ES/FR ③回写工具链同步 ④重跑并出最终迁移层
> 纪律：未 commit / 未切分支 / 未 merge；未跑模拟器（本轮判据全在盘上）

## 11.0 一句话结论

> **证据路径基准**：本节所有 `temp/...` 均相对于 `work/builds/GR_TXMIG/`（即 `work/builds/GR_TXMIG/temp/...`）。
> **第三方改动登记**：执行期间 `tools/text_csv/tcslib.py` 被**几何路**改过（+194/−3，19:42）；
> 经只读 `git diff` 核对，改动**没有触及** `parse_lang` / `parse_sfxml` / `lzo_compress` / `lzo_subs` /
> `splice` / `xml_tail_start` 任何一个迁移所用函数的定义，且本轮产物与旧产物 **sha256 逐字节相同**
> ⇒ 该改动**未影响**本报告的迁移结论。（该文件不在 textmig 的本轮写入范围内。）

| 项 | 结果 | 关键证据 |
|---|---|---|
| ① charset 补丁自洽（§15.1） | ✅ **已由几何执行者合并**，`pair_of = 2350`、slot 0..2349 一一映射 | `temp/charset_merge_dryrun.log`、`temp/charset_probe.json` |
| ④ 重跑主迁移（3 容器） | ✅ **全部硬判据通过**，产物 `GR_TXMIG_r2.iso` sha256 与旧产物**逐字节相同** | `temp/r2/build/migrate_report.json`、`temp/r2/audit/audit_report.json` |
| ② 补做 ES/FR（§15.3） | ❌ **未达成 —— 盘上没有空间**（解压层差 20/21 B，压缩层差 2,015/2,136 B，而扇区余量只有 11 B） | `temp/capacity/defect_report.json`、`temp/capacity/esfr_capacity_probe.json` |
| ② DE/IT 明示不动 | ✅ **已登记为已知缺陷**（逐文件裸码计数 + 两个解析器失败证据 + 风险说明） | 同上 + §11.3.2 |
| ③ `legacy_singles.py [gate_hex]` | ✅ **实现**，并写明两个口径陷阱（SF 盲点 206 · 产物盘 3,386/3,604 假阳性） | `work/tools/legacy_singles.py` 文件头 + 4 组实跑 |
| ③ `dump_all_text.py extract_xml` | ✅ **改用 `parse_sfxml + parse_xml_attrs`**，SF 口径 59 → **265**，全盘合计 → **3,279** | `temp/dumpfix_before/`、`temp/r2/dump_before/` |
| 新增：回写链 2 处口径对齐 | ✅ 见 §11.4.3 / §11.4.4 | — |

## 11.1 ① charset 补丁：几何执行者已合并（本轮改为"验证 + 对齐"）

`tools/font_pipeline/data/charset_compiled_zh16.json`（受保护路径，**本轮只读、一个字节都没写**）
在我执行期间被几何执行者更新：

```
size 122698 B · mtime 2026-10-15 19:39:00
sha256 7FE2BF5922B5A3505FDF44A93FB9217AADF7A8FB249A327CB9EFCB4EB6EB7FAC5
pair_of 2350 条 · slot 0..2349 一一映射 · codes 103 条
```

| 检查（`temp/charset_probe.json`） | 实测 | 与 §15.1 补丁 |
|---|---|---|
| `pair_of` 条数 | **2350** | ✅ 与 §7/§15.1 目标一致 |
| slot 2345 = 按 | `0xB9FA` | ✅ 逐值一致 |
| slot 2346 = 时 / 2347 = 小 / 2348 = 击 | `0xB9FB` / `0xB9FC` / `0xB9FD` | ✅ 逐值一致 |
| slot 2349 | `0xB9FE` = **'✕' U+2715** | ⚠ 字符名口径差异（见下） |
| `codes` 里的 0xB6..0xB9 | **已摘掉** ✅ | ✅ 与 §15.1 一致 |
| `codes` 里的 0xBA..0xFF（战/要/在…） | **全部保留**（74 个） | ✅ 满足 §12.2 |
| 0..1871 既有条目 | 一个字段都没动 | ✅ |
| 1872..2339 / 2340..2344 | PUA 占位 `U+E394..U+E398` 等（保留空槽，无字形） | ✅ 与 §7 一致 |

**★ 唯一的对接口径差异（已解决）**：`charset_pairs_patch.json` 与 `migration_pairs.json` 里 ✕ 的键写的是
`\ue0b5`（U+E0B5 = tcslib 对未映射字节的 PUA 回落名），而几何执行者合并后的 charset 用的是
**`\u2715`（U+2715 MULTIPLICATION X，真字形）**。两者是同一个逻辑字 ⇒ 按两处 sidecar 文件里
既有的约定「**以 charset 为准**」对齐，并在工具里做了别名解析：

* `work/tools/migrate_legacy.py` 新增 `_icon_char()`：按"先 charset 实际名、再别名"解析图标码
  （否则 `\ue0b5` 查不到 ⇒ 工具会去**再借一个空槽**，把文本指到 1872..2344 那些**没有字形**的槽上）；
* `work/tools/migrate_legacy_audit.py` 新增 `align_legacy_tab()`：`LEGACY_TAB[0xB5]` 跟着对偶码表走
  （否则 [B] 会把同一个字判成差异 —— 假阳性）；
* `charset_pairs_patch.json` 追加 `_merged_2026-10-15` 段，把合并状态与这条口径差异登记在案。

**验证（`temp/charset_merge_dryrun.log`）**：补丁逐条已幂等 ✓；合并后自洽 ✓；`codes` 0xB6..0xB9 == ∅ ✓；
0..1871 未动 ✓。**注意**：补丁里 `codes_remove` 已被合并方执行过，所以本脚本读到的快照里"少掉的 4 条"
是**合并前**发生的 —— 脚本按幂等处理并显式打印这一点，不假装是自己删的。

**★ 一个必须记住的连带影响**：§15.1 把 `0xB6..0xB9` 从 `codes` 摘掉之后，**迁移工具再也无法从 charset
查到 击/小/时/按 这 4 个字**（它们已进对偶空间）。若不同步补兜底表，`build_map` 会认为它们"没有字" ⇒
**借空槽 ⇒ 文本指向 2340..2344 那些无字形的 PUA 占位槽**。因此 `LEGACY_CHARS` 已从 3 条扩到 7 条
（`0xB2/0xB3/0xB4 + 0xB6/0xB7/0xB8/0xB9`），并注明出处；`charset.codes` 仍然优先 ⇒ **合并前后行为一致**。

## 11.2 ④ 重跑主迁移 → 最终迁移层

### 命令（可复现）

```powershell
python work/tools/migrate_legacy.py work/builds/GR_ZH113b/GR_ZH113b.iso `
    work/builds/GR_TXMIG/GR_TXMIG_r2.iso --containers core `
    --out work/builds/GR_TXMIG/temp/r2/build
```

**产物路径（明确写死）**：`work\builds\GR_TXMIG\GR_TXMIG_r2.iso`
（上一版 `GR_TXMIG.iso` **保留不动**，便于对照；两版 sha256 相同，见下）

| 盘 | 尺寸 | SHA-256 |
|---|---|---|
| 基底 `work/builds/GR_ZH113b/GR_ZH113b.iso` | 1,648,164,864 | `ff3abd3c50e380f666955ccb6226b67198e181589c0db9b4d52e4643208f6445` |
| 上一版 `work/builds/GR_TXMIG/GR_TXMIG.iso` | 1,648,164,864 | `c3c1e6c5f9535bb30d25c6ec3a9c84ecda509351dc8a055aad64be426a3dd2de` |
| ★ 本轮 `work/builds/GR_TXMIG/GR_TXMIG_r2.iso` | 1,648,164,864 | **`c3c1e6c5f9535bb30d25c6ec3a9c84ecda509351dc8a055aad64be426a3dd2de`** |

★ **两版 sha256 完全相同** —— 这是一条很有力的交叉验证：几何执行者**独立**按 §15.1 把 5 个对偶码
放到容量顶部（2345..2349），得到的**与上一轮工具"从容量顶部借槽"的分配逐值一致**
（按=2345 / 时=2346 / 小=2347 / 击=2348 / ✕=2349）。本轮工具**没有产生任何借条**
（`[cs] ★ 借槽` 一行不出现，`reserved_pairs = {}`）⇒ §7-P1 那个"硬缺口"**已经关掉**。

### 逐项硬判据（全部通过）

| # | 判据（任务书 ④ / §14.1） | 实测 | 证据 |
|---|---|---|---|
| 1 | **主判据**：载荷字节流里裸 `0xB1..0xB9` = **0** | **0 / 0 / 0**（MENU-GR-SF 三容器，**独立实现**逐载荷扫） | `temp/r2/audit/audit_report.json` `B[*].bare_after` |
| 1b | 同一判据的 CSV 口径（[A2]，含 SF 长正文 + `name=`） | **0 处** ✓ | 同上 `A_after.unpaired` |
| 2 | 逐字符一致 = **0 差异** | MENU 2232 / GR 2232 / SF 595 条，**0** | 同上 `B[*].diff` |
| 2b | 行级真值 [C3]（5 个来源） | 全 **0** | 同上 `C[*].c3_truth_diff` |
| 2c | [C0] 复现官方 dump 口径（含**新** SF 口径） | 全 **0** | 同上 `C[*].c0_stock_repro_mismatch` |
| 3 | `0xB1..0xB9` 之外 **0 改动** | `[S2]` 反向重建逐字节 == 源 blob ✓（未触发 `[!!]`）；帧内未变子流照搬原压缩字节 | `temp/r2/build/migrate_report.json` + `migrate.log` |
| 4 | 全盘 diff **100% 落在计划窗口内** | **104,427 B / 1,241 区间 / 窗口外 0**；7 个窗口 | 同上 `diff` |
| 5 | ISO 尺寸不变 | `1,648,164,864 == 源盘` ✓ | 同上 |
| 5b | **条目表不动** | 3 容器 `(off, stored, real)` 回读**逐字段相同** ✓ | `[S7]` 三行 |
| 6 | ELF 4 站点回读 = `0xBA` | **4/4** ✓（每站点只动最低字节） | `[S7]` |
| 7 | 迁移量 | **3,279 处**（与上一轮逐码完全一致） | `[sum]` |

全盘差异窗口（与上一轮**逐数字相同**，进一步证明两版是同一份产物）：

```
[0x003AA768,+4) ELF 0x416EE8 差异 1 B   [0x003AA9E0,+4) ELF 0x417160 差异 1 B
[0x003AAD9C,+4) ELF 0x41751C 差异 1 B   [0x004F8F24,+4) ELF 0x5656A4 差异 1 B
[0x00F034F50,+47619) GR.IMG#902   EN_STRINGS.RES@GR        差异 32,152 B / 400 区间
[0x0623A0800,+49700) MENU.IMG#283 EN_SPECIAL_FEATURE.XML   差异 40,121 B / 437 区间
[0x0623AD000,+47570) MENU.IMG#25  EN_STRINGS.RES@MENU      差异 32,150 B / 400 区间
------------------------------------------------------------------------------
合计 104,427 B ✓  窗口外 0 ✓
```

**"最小差异 / 槽内吸收"性质保持不变**（几何路做合并要靠它）：解压总长逐容器不变（128,545 / 128,668 /
116,486），增长吃 `used_end` 之后的陈旧尾巴（1,507 / 1,507 / 265 B），重压后帧仍装得进原槽
（32,847 ≤ 47,570 / 32,848 ≤ 47,619 / 41,418 ≤ 49,700），**IMG 条目表 0 字节改动**。

## 11.3 ② ES/FR：**未达成 —— 不是代码问题，是盘上没有空间**

### 11.3.1 精确账（`temp/capacity/defect_report.json` + `esfr_capacity_probe.json`）

| 容器（各 2 份拷件） | 解压长 | `used_end` | 陈旧尾巴 | 载荷裸旧码（= 增长） | 结论 |
|---|---|---|---|---|---|
| `ES_STRINGS.RES` MENU#27 / GR#904 | 142,148 | 142,140 | **8 B** | **28** | ✗ **差 20 B** |
| `FR_STRINGS.RES` MENU#28 / GR#907 | 149,664 | 149,656 | **8 B** | **29** | ✗ **差 21 B** |
| （对照）`EN_STRINGS.RES`×2 | 128,545 / 128,668 | 69,671 | 58,874 / 58,997 | 1,507 | ✓ 槽内吸收 |
| （对照）`EN_SPECIAL_FEATURE.XML` | 116,486 | 80,101 | 36,385 | 265 | ✓ 槽内吸收 |

**根因**：这两张表是**未汉化的原文**，从建盘起**从未被编辑过** ⇒ 条目数据**正好铺满整个 blob**，
没有可吃的陈旧尾巴。而迁移每处 **+1 B**（1 字节 → 2 字节对偶码），28/29 处就是 28/29 B。

**压缩层也不行**（我实测了而不是估算）：重压后帧

```
ES: 53,077 → 55,092 B (+2,015)     FR: 55,413 → 57,549 B (+2,136)
```

而 IMG 里"本条目 `off+stored` 到下一入口 `off`"的**扇区对齐余量只有 11 B**
（`[ES][pad11][FR][pad11][IT]…`，MENU 与 GR 两份相同）。⇒ **"只改本条目 `stored`/`real`、不搬移数据"
也不可行**（+2,015 ≫ 11）。

⇒ 要补 ES/FR 必须**改 IMG 条目表并搬移后续条目（级联改 `off`）**，属结构性改动，
与"最小差异 / 条目表未动"直接冲突。**本路没有硬撑**：`migrate_legacy.py` 按设计**拒绝写盘**
（`[!!] ES_STRINGS.RES@MENU 装不下: 内容变长 +28 B…`，见 `temp/r2/dry_esfr.log`，退出码 1），
账目交给 LEAD 重排（LEAD §13.4「若实测装不下 ⇒ 停手回报，由 Lead 重排」）。

### 11.3.2 给 LEAD 的三个选项（都需你裁决，我不自决）

| 选项 | 内容 | 代价 |
|---|---|---|
| **A. 认账不动**（推荐先做） | ES/FR 与 DE/IT 一起登记为"抬闸门后若主机语言=ES/FR 会吞字"的已知缺陷，交付说明里告知用户 | 0；风险与 DE/IT 同类，但 ES/FR 结构完好、随时可补 |
| **B. 允许条目扩容** | 只改这 4 个条目的 `stored`/`real` + 把该 IMG 里**其后**的条目整体挪 1 个扇区（级联改 `off`） | 打破"条目表未动"；需重算后续所有条目的 LBA、重跑全盘 diff 判据 |
| **C. 零增长改法** | 给 △/✕（FR 还要 键）找**单字节**目标码（`0xBA..0xFF` 已被战/要/在…占满；`0x80..0xA0` 也许还有空位）⇒ 1 字节换 1 字节、**增长 0** | 要新增 FONT.RES 记录 + 图集字形（△ 已有 slot 1504 的对偶字形，但单字节码走的是 FONT.RES 记录路径）；且与 §15.1 已定的对偶码方案并存需要额外说明 |

**ES/FR 的迁移本身没有任何技术不确定性**：变换与主迁移完全一致（ES = 0xB1:7 + 0xB5:21；
FR = 0xB1:7 + 0xB5:21 + 0xB2:1），容器清单里已经加好（`--containers esfr` 就能跑），
**只等空间**。LEAD §15.3 的"≈114 处"估算**完全准确**（实测 56 + 58 = **114**）。

### 11.3.3 DE/IT：登记为**已知缺陷**（§15.3 裁决：明确不动）

`work/tools/migrate_defect_scan.py`（新工具，只读）逐份取证：

| 容器（各 2 份） | 解压长 | `ngroups` | 全 blob 裸 `0xB1..0xB9` | LANG 解析 |
|---|---|---|---|---|
| `DE_STRINGS.RES` MENU#26 / GR#900 | 146,910 | 66 | **37 处/份**（`0xB1:8 0xB2:1 0xB5:21 0xB9:7`） | **失败** |
| `IT_STRINGS.RES` MENU#29 / GR#910 | 139,082 | 66 | **38 处/份**（`0xB2:8 0xB4:2 0xB5:28`） | **失败** |

**两个解析器都解不动**（既存结构异常，非本轮引入）：

```
T.parse_lang            : unpack_from requires a buffer of at least 1952808011 bytes
                          for unpacking 4 bytes at offset 1952808007 (actual 146910)   [DE]
                          ... 1953917720 / offset 1953917716 (actual 139082)            [IT]
parse_expanded_groups   : 同一处失步（dump 口径也一样解不动）
head64(DE) = 42000000 04000000 05000000 "Sieg!" 0000000c 000000 "Feuergefecht" 00000036 ...
head64(IT) = 42000000 04000000 09000000 "Vittoria!" 00000007 "Scontro" 00000037 ...
```

⇒ `ngroups`(=66) 之后逐组读 `{u32 count}` 时**把 payload 字节当成了 count** 去 `unpack`，
说明**组边界/条目边界已失步** ⇒ **载荷边界不可信 ⇒ 不能按载荷改写**。

**⚠ 风险说明（写进交付说明）**：若主机语言 = DE/IT，引擎会去渲染这两张表；抬闸门到 `0xBA` 后表内
每个裸 `0xB1..0xB9` 都会变成**对偶前导**、吃掉后一字节（整串重配对）⇒ 界面可能出现
`4 / 0 / ( / P / H` 之类 ASCII 乱码，甚至内存损坏（§1.4 已实证同类现象）。**本路不修**（既存结构
异常），只登记；若要修，必须**先解决 LANG 组结构失步**再谈迁移。

**残余清单（产物盘上，独立复核 `temp/r2/audit/` 的 [E] 段）**：

```
ES:MENU / ES:GR  载荷 28/份 · 全 blob 49/份   ES+FR = 114 处（装不下）
FR:MENU / FR:GR  载荷 29/份 · 全 blob 38/份
DE:MENU / DE:GR  全 blob 37/份 · LANG 失败     DE+IT = 150 处（解析失步，明确不动）
IT:MENU / IT:GR  全 blob 38/份 · LANG 失败
8 份拷件合计残留 (全 blob 口径) = 324 处
```

## 11.4 ③ 回写工具链同步（交付项）

改前备份：`work/builds/GR_TXMIG/backup/{legacy_singles.py.bak, dump_all_text.py.bak,
migrate_legacy.py.bak, migrate_legacy_audit.py.bak}`。

### 11.4.1 `work/tools/legacy_singles.py` —— `[gate_hex]` **真正实现**

原状：usage 写了 `[gate_hex]`，但代码从不读 `sys.argv[2]`（写死 `0xA1..0xB0`）。现在：

```python
gate = int(a, 16) if ... else 0xB1          # 前导上界 (基底盘 = 0xB1)
...
if 0xA1 <= c < gate:  i += 2 ; continue     # 对偶前导
if c >= gate:         count[c] += 1         # 以单字节形式出现
```

并加了 `--used N`（阶梯表的"已用"基数，默认读 charset 的 `pair_of` 条数）、超出容量时打印
`★ 超容 N, 不可用`、以及**四组实跑锚点**：

| 输入 CSV | 闸门 | `0xB1..0xB9` 合计 | 说明 |
|---|---|---|---|
| `temp/before/all_text.csv`（旧 dump 口径） | 0xB1 | **3,073** | 复现 LEAD §1.4 的历史值 ✓ |
| `temp/r2/dump_before/all_text.csv`（**修好的** dump 口径） | 0xB1 | **3,279** | ★ 真值 ✓ |
| `temp/after/all_text.csv`（旧口径产物 CSV） | 0xB1（旧口径） | **3,386** | ★ 假阳性现场（LEAD §15.4 的数）|
| `temp/r2/dump_after/all_text.csv`（新口径产物 CSV） | 0xB1（旧口径） | **3,604** | 同一现象的更大口径（多看见 192+14 处）|
| `temp/r2/dump_after/all_text.csv` | **0xBA** | **0** | ✓ 闸门口径下残留 0 |

### 11.4.2 文件头写明两个口径陷阱（原文摘录）

* **① SF 盲点**：本工具读的是 `dump_all_text.py` 的 CSV，而旧 `extract_xml` 的
  `RE_NODE = >([^<>]{2,400})<` **上限 400 字节**、且只抓 `studio|group` 的 `name=`
  ⇒ **>400B 正文 + `item` 的 `name=` 都看不见**。实测 SF：真值 **265**（正文 250 + `name=` 15）
  vs 旧 dump 口径 **59** ⇒ **少算 206**；这 206 正是"**3,279 − 3,073**"的差额
  ⇒ **LEAD §1.4 的 3,073 是下界，真值 3,279**。
* **② 读产物盘必须用闸门口径**：产物盘上 `0xB1..0xB9` 已是**对偶码的 lead**；沿用基底口径去读
  会把每个对偶码拆成"裸首字节 + 裸尾字节"、整条 payload 错位 ⇒ 实测 **3,386 / 3,604 处假阳性**
  （真实残留 **0**）。正确用法 `legacy_singles.py <产物CSV> 0xBA`。
  并显式声明：**它只有"闸门"没有"对偶码表"**，数不出"哪些字节不是合法对偶 lead"
  ⇒ **产物盘的主判据是 `migrate_legacy_audit.py` 的载荷级扫描，不是本工具**（§14.2 的降级要求）。

### 11.4.3 `tools/diag/dump_all_text.py::extract_xml` —— 改用回写链的现成函数

```python
① 旧口径 (RE_GRP + RE_NODE)            原样保留 ⇒ 既有行键/行数一个都不少
② tcslib.parse_sfxml                   <text> 正文**不限长度**  ⇒ 补 >400B 的 192 处
③ inject_text_csv.parse_xml_attrs      name="…" 标题属性       ⇒ 补 item 的 14 处
   (studio/group 已被 ① 的 section: 行覆盖, 不重复计)
⇒ 59 + 192 + 14 = 265 ✓ 与迁移真值逐值一致
```

`parse_xml_attrs` 用 importlib 隔离加载（与 `migrate_legacy.py::_xml_attrs` 同一手法），
保证"dump 看得到什么"与"回写能改什么"认的是**同一批属性**。

**实测对照**（同一张基底盘 `GR_ZH113b`）：

| dump 口径 | MENU:SF 行数 | SF 的 `0xB1..0xB9` | 全盘合计 |
|---|---|---|---|
| 旧（`temp/before/all_text.csv`） | 441 | **59** | **3,073** |
| 新（`temp/r2/dump_before/all_text.csv`） | 546（有 hex 的） | **265** | **3,279** |

逐码也对上了：新口径 SF = `0xB2:2 0xB3:16 0xB4:45 0xB6:80 0xB7:43 0xB8:76 0xB9:3`，
与迁移器 `sf_region_counts()` 的 `250 + 15 = 265` **逐值相同** —— 两条独立路径互证。

### 11.4.4 顺带修掉的两个真问题（都在 §13 合并路径上）

1. **`migrate_legacy.py --no-elf` 的语义原本是错的**：`[S7]` 回读时把期望值写成 `base_gate`，
   而几何先行流程（§13 步骤 3）要求"源盘闸门**已经等于** `--gate`、本轮不动 ELF"。
   现在：`--no-elf` ⇒ **要求源盘 4 站点 `imm == --gate`**（否则报错并提示去掉 `--no-elf`），
   `[S7]` 也一律按 `gate` 校验。**已用几何盘实跑验证**：
   `GR_CAP2400.iso` 的 4 站点实测 `0xBA` ⇒ `[elf] --no-elf: 源盘 4/4 站点已 == 0xBA ✓ ⇒ 本轮不动 ELF`
   （`temp/r2/dry_noelf.log`）。
2. **`canonical_encode` 的单字节兜底缺闸门保护**：`single_pref`（引擎图标码 0xB1/0xB5）落在
   `[0xA1,gate)` 内时，原代码会**直接写出这个会吞字节的裸 lead**。现在改为**报错中止**
   （`字 '✕' 只有引擎图标单字节码 0xB5, 而它落在闸门区间内 ⇒ 抬闸门后不可按单字节写`），
   与 §12.2 的"最小差异 + 不许猜"一致。

### 11.4.5 新增/扩展的验收能力

| 工具 | 变化 |
|---|---|
| `work/tools/migrate_legacy_audit.py` | ① `[B]` 段新增 **§14.1 主判据的载荷级独立实现**（`_unpaired_count`：按新闸门走，`0xB1..0xB9` 里**凑不出合法对偶码**的才算裸字节）⇒ 3 容器 **0/0/0**；同时打印"误用基底语义"的假阳性数（1660/1660/81）做对照。② 新增 `[E]` 段：非英文语言表已知缺陷登记（**非阻断**）。③ `align_legacy_tab()` 对齐 ✕ 的字符名。 |
| `work/tools/migrate_defect_scan.py`（新） | 10 份 `*_STRINGS.RES` 拷件的**容量可行性 + 解析健康**逐表体检 ⇒ `temp/capacity/defect_report.json`。 |
| `work/builds/GR_TXMIG/temp/charset_merge_dryrun.py`（新） | 按 §15.1 **在内存里**验证 charset 补丁合并（幂等 + 自洽 + `pair_of == 2350`），**绝不写受保护路径**。 |
| `work/builds/GR_TXMIG/temp/esfr_capacity_probe.py`（新） | ES/FR 的**解压层 / 压缩层**双口径容量账（含重压回环自检）。 |
| `work/builds/GR_TXMIG/temp/cmp_geom_text.py`（新） | 几何盘 vs 基底盘的 3 个文本容器逐字符比对（见 §11.6）。 |

## 11.5 未达成项（如实列出）

1. **★ ES/FR 迁移未达成**（§11.3）—— 容量硬阻（差 20/21 B 解压、2,015/2,136 B 压缩），
   **不是代码问题**：容器清单已加好、变换已就位、只等空间；**需 LEAD 在 A/B/C 三个选项里裁决**。
2. **DE/IT 仍未修**（§11.3.3）—— 既存 LANG 结构失步，属**已知缺陷**，按 §15.3 明确不动。
3. **未跑实机** —— 本轮全部判据都是盘上取证（字节/结构/解码/解压回环）；实机 6000 帧、
   图标实拍、`TLK`/`TLB` 计数属 LEAD 的 §13 复核。
4. **未产出"几何盘 + 文本迁移"的合并成品** —— §13 的合并顺序属 LEAD 执行；
   本轮只把**工具与口令**备好（`--no-elf` 已实跑验证），**没有替 LEAD 决定用哪张几何盘**
   （理由见 §11.6）。
5. `GR_ZH124/125`、`GR_F364/F365` 的历史乱码仍未修（超出本轮范围，同上一轮 §7-P5）。

## 11.6 ★ 交叉路径警示（给 LEAD 的 §13 合并前置检查）

按 §13，合并基底应当是"几何盘"，然后 `migrate_legacy.py <几何盘> <成品盘> --no-elf`。
我用 `temp/cmp_geom_text.py` 实测了 `GR_CAP2400.iso` vs `GR_ZH113b.iso` 的 3 个文本容器：

| 容器 | blob | 逐字符（两盘都用**基底语义**解） | 裸 `0xB1..0xB9`（基底口径） |
|---|---|---|---|
| `EN_STRINGS.RES@MENU` | 128,545 **逐字节相同** ✓ | 2232 条 · **0 不同** ✓ | 1,514 / 1,514 ✓ |
| `EN_STRINGS.RES@GR` | 128,668 **逐字节相同** ✓ | 2232 条 · **0 不同** ✓ | 1,514 / 1,514 ✓ |
| **`EN_SPECIAL_FEATURE.XML`** | 116,486 **★ 不同** | 69 条中 **32 条文本不同** | 几何 **284** vs 基底 **265** |

细节：几何盘的 SF 里 `0xB3` 16→2、`0xB4` 45→3（**已被改写成对偶码**，其 lead 就是 `0xB1` ⇒ `0xB1` 0→59），
而 `0xB6:84 / 0xB7:43 / 0xB8:82 / 0xB9:9` **仍是裸字节** ⇒ 这是一个**半迁移态**容器；
且 `--no-elf` 实跑在该容器上报 **4 条既存缺陷**（`@0x545E..0x5516`、`@0x5FA6..0x6064` 等
"字 U+FFFD 既无对偶码也无单字节码"）。逐处样例（`<text>` #15）：

```
基底 bytes: ... 用(b4) <pair aa fe> ...
几何 bytes: ... <pair b1a4 = 用> ...
几何解出:  '…极适合△跑斗摧毁轻装甲车辆…'   ← 基底语义下的样子 (半迁移态的典型表现)
```

**结论/建议**：`GR_CAP2400.iso` 目前**不宜直接当 §13 的合并基底**（至少 SF 这一格不行）——
要么让几何路用 `GR_ZH113b` 的 SF，要么确认几何盘那份 SF 是**有意的更新文本**。
两个 EN 语言表容器**可以**直接用（逐字节相同）。这条不在我的写入范围，属**须 LEAD/几何路确认**的前置条件。

