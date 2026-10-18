# REPORT_icon_codes.md — 手柄图标码总表（round42）

> **用户原话**
> > 手柄图标码理论上应该不止 4 个。我见过有四个手柄按键加至少一个左右键。检查一下逻辑是不是有缺漏的。

**对象盘**：实验基盘 `work/builds/GR_ZH93/GR_ZH93.iso`（`e037f629…8d19be`，**只读**）；
实验产物 `work/builds/GR_ZH96_icon/GR_ZH96_icon.iso`（`f90a34ad…`）。
**逆向对象**：`third_party/orig/ps2/slus_out/SLUS_206.13`（美版原始 ELF）+ 现役盘里的 ELF（LBA 295）。

---

## 〇、一句话结论

**引擎的「文本图标码」总共只有 2 个：`0xB1` = △（绿三角键）、`0xB5` = ✕（叉键）。**

它们**不是**某张表里的两项，而是绘制函数 `RSFontMgr::DrawString` v1 里**写死的两个 `if`**
⇒ 「文本图标码」的个数**上限就是 2**，**不存在**"还没找到的更多图标码"。

用户看到的「四个手柄按键 + 至少一个左右键」是**真的**，但那是 **UI 界面直接画的**
（按钮提示栏 / 快捷键栏），走的是另一套按「动作编号」取图的系统，**和文本字节没有任何映射关系**。

原先被算进"图标"的 `0xE7` / `0xF1` **不是图标**，是拉丁字母 **ç / ñ**
（语言选择菜单里的 `Français` / `Español`）。

---

## 一、候选图标字节全集（只读枚举）

口径：`0xB1..0xFF` 里**没被字符集占用**的字节。下界取 `0xB1` 是因为 `0xA1..0xB0` 是引擎的
DBCS **lead 区间**（ELF 四处 `sltiu …,0xB1` 实测），图标码写在那里会被当成对偶首字节吞掉后一个字。

脚本：`work/builds/GR_ZH93/temp/r42/p01_candidates.py` → `candidates.json`

```
字符集现状: 单字节码 108 个 / 对偶码 1319 个 (lead 0xA1..0xB0, trail 0xA1..0xFE)
单字节码区间 0x80..0xFF 内的空缺: A1..B0(lead) B1 B5 E7 F1

候选图标字节 = 0xB1..0xFF 减字符集占用 ⇒ 共 4 个:
    B1  B5  E7  F1
```

**⇒ 字节空间是满的**：本盘 `0xB1..0xFF` 只剩这 4 个空字节，其余全被中文字符集占用
（占用它们的字节一律按"汉字"画，**不可能**是图标码）。所以"还有没有别的图标码"这个问题，
在**字节空间层面**就已经收窄到只有这 4 个候选。

---

## 二、ELF 证据（反汇编）

### 2.1 唯一的字符循环绘制入口，只有 3 个字符值特判

`RSFontMgr::DrawString` **v1** @**0x219A70**（912 B）——符号表：
`DrawString__9RSFontMgrFPCcffRC7RSColorP6RSFontPCiPCii`。
v2（`0x219E00`）/ v3（`0x219EB0`）只是坐标换算 + 委托 v1 ⇒ **全 ELF 只有这一处逐字符循环**。

它对**字符值**只有 3 个特判：

```asm
00219BE8  addiu $v1, $zero, 32        ; c == 0x20 (空格) → 空格分支
00219BEC  beq   $a1, $v1, 0x219D80

00219C08  addiu $v1, $zero, -75       ; c == 0xB5  ┐
00219C0C  beq   $a1, $v1, 0x219C44    ;             │ 图标路径 #1
00219C10  addiu $v1, $zero, -75       ;  (延迟槽)     │
00219C14  addiu $v1, $zero, -79       ; c == 0xB1  │
00219C18  beq   $a1, $v1, 0x219C40    ;             ┘
00219C1C  nop
00219C20  ...
00219C30  jal   0x0021ADE0            ; ← 其余任何字符: 走字形路径 (ComputeCharTextureCoords)

00219C94  addiu $v1, $zero, -75       ; c == 0xB5  ┐ 同函数内第 2 组比较
00219CAC  addiu $v1, $zero, -79       ; c == 0xB1  ┘ (决定 x 位置校正)
00219D24  addiu $v0, $zero, -75       ; c == 0xB5  ┐ 同函数内第 3 组比较
00219D38  addiu $v0, $zero, -79       ; c == 0xB1  ┘ (决定 AddOneWord 的"是图标"标志)
```

⇒ 同一个函数里同样的比较共 **6 处，全部只涉及 `0xB5` 与 `0xB1`**，**没有第三个值**。

> 交叉验证：全 ELF 穷举 `addiu rt,$zero,imm` 且 `imm ∈ 0xFF80..0xFFFF`
> （= 把某个高位字节当特殊字符判的所有地方），落在字体/文本链 `0x219xxx..0x21Axxx` 的
> **只有上面这两组**。脚本：`p02_elf_icon_scan.py`。

### 2.2 图标 UV 是**写死的常量**（不是查表 ⇒ 表里不可能有更多项）

```asm
; ── c == 0xB5 ──
00219C4C  lui $v1, 0x3F80   → 1.0
00219C54  lui $v1, 0x4346   → 198.0
00219C5C  lui $v1, 0x41A8   → 21.0
00219C64  lui $v1, 0x435A   → 218.0     ⇒ UV = (u 1..21, v 198..218)
; ── c == 0xB1 ──
00219C70  lui $v1, 0x41C8   → 25.0
00219C78  lui $v1, 0x4346   → 198.0
00219C80  lui $v1, 0x4234   → 45.0
00219C88  lui $v1, 0x435A   → 218.0     ⇒ UV = (u 25..45, v 198..218)
```

### 2.3 图标**不吃字库**：`RSFontMgr` 里有两个 UISpriteModel

`RSFontMgr::ReadResourceFile` @**0x219380** 尾部：

```asm
002197B8..002197C8   model[+40] 初始化 (容量 = 108)      ← 文字
002197CC..002197DC   model[+76] 初始化 (容量 = 2)        ← 图标
002197E8..002197F8   SetTexture(model[+40], GetTexture(字体资源名))
00219800  lui   $v0, 0x0058
0021980C  addiu $a1, $v0, -31152        ; a1 = 0x00578650 → C 字符串 "pda_counterparts.rsb"
0021981C..00219828   SetTexture(model[+76], GetTexture("pda_counterparts.rsb"))
```

`AddOneWord` @**0x219F50** 的第 6 个参数（`bool`）就区分两条路：

```asm
00219F6C  bne $t0, $zero, 0x21A078      ; t0 != 0 ⇒ 走 model[+76] (图标)
00219F74  lw  $t9, 40($s0)              ; 否则   走 model[+40] (文字)
```

DrawString v1 只在 `0xB5`/`0xB1` 那两个分支里给它传 1（`0x219D78 addiu $t0,$zero,1`）。

⇒ 图标是**另一张纹理**上的精灵（`pda_counterparts.rsb`，`GR.IMG #861`；
`MENU.IMG#3 COMMON.PAK` 里另有一条同名 256×256 记录），**与字库无关** ——
这也解释了历史现象：把 `0xE7/0xF1` 当"图标"去查字库永远查不出名堂。

### 2.4 那玩家看到的「△○✕□ + 左右键」是什么？

**UI 侧「快捷键图标」系统**，按**动作编号**取 UV，与文本字节**没有**映射：

`kShortcutDefaultTC(unsigned int index, int)` @**0x2BEFE0**（返回 RSVector4 纹理坐标）
= 一张 16 项的 `switch`（index `0..6`, `23..31`）：

| index | UV | index | UV |
|---|---|---|---|
| 3 | (147,141)-(168,160) | 27 | (85,178)-(120,198) |
| 4 | (168,141)-(189,160) | 28 | (0,178)-(20,198) |
| 5 | (0,0)-(0,0) 空 | 29 | (21,178)-(41,198) |
| 6 | (209,45)-(237,103) | 30 | (42,178)-(62,198) |
| 26 | (0,178)-(20,198) | 31 | (63,178)-(83,198) |

脚本：`p03c_shortcut_tc.py`（按 case 体边界切分，避免读到相邻 case）。

**结论**：玩家在按钮提示栏看到的手柄图标 = 这套系统画的（**不是**文本码）⇒
dump 文本永远看不到它们；**也不能**用 `{{BTN:xxxx}}` 去调它们。

---

## 三、图标美术资源：**原盘与现役盘逐字节相同**

| 资源 | EN_ORIG（美版原盘） | GR_ZH93 / GR_ZH96_icon | |
|---|---|---|---|
| `GR.IMG #861 PDA_COUNTERPARTS.RSB` (262237 B) | sha256 `77c0951dcc4f0a4c…` | **相同** | ✓ |
| `COMMON.PAK` 记录 `pda_counterparts` (256×256 PSM8) 像素 | sha256 `010e7edba76b1fef…` | **相同** | ✓ |
| 同上 CLUT | sha256 `7ccd9f312e2d79bc…` | **相同** | ✓ |

⇒ 文本图标码画出来的图标 = **美版原版图标**，本工程一个字都没改过它。
（脚本 `p28_icon_art_hash.py`）

**图标图集本身长这样**（`pda_counterparts`，v=168..226 一带，放大 8 倍）：
`work/builds/GR_ZH93/temp/r42/iconband_EN_ORIG.png`
图集里那一行是 **✕ △ □ ○** 四个面键 + 空白键 + "?" + "✓" + 宽箭头 ——
但**文本路径只够得到其中 2 个**（`0xB1`/`0xB5`）。

---

## 四、实机逐码判定（**全部 4 个候选码都跑到了**）

**实验盘**：`work/builds/GR_ZH96_icon/GR_ZH96_icon.iso`（`f90a34ad782b2e99…`）
= GR_ZH93 + **只改 `SFXML:T0063`（"何为幽灵？"条目）的正文**：

```
1={{BTN:E0B1}}图
2={{BTN:E0B5}}图
3={{BTN:E0E7}}图
4={{BTN:E0F1}}图
5={{BTN:E0B1}}{{BTN:E0B5}}图
6={{BTN:E0E7}}{{BTN:E0F1}}图
```
（每个标记后面紧跟一个「图」当参照 —— 图标画不出来时会看到它紧贴在 `=` 后面。）

**实机**：`GR_ISO=…GR_ZH96_icon.iso python tools/capture/run_opt.py icon_t63 nav_sf6.txt 28000 100`
（复用已验证的配方 `tools/capture/nav_sf6.txt`；exit=0 / 469 s / 28000 帧 / **单实例**）

**判定截图**：`work/builds/GR_ZH96_icon/temp/dump_icon_t63/snap_f00026200.png`
放大图：`work/builds/GR_ZH93/temp/r42/game_t63_zoom.png`

| 行 | 盘上字节 | 实机画出来的是 | 判定 |
|---|---|---|---|
| `1=` | `0xB1` | **绿色 △ 三角键帽图标** | ★**图标码**：△ |
| `2=` | `0xB5` | **蓝/粉 ✕ 叉键帽图标** | ★**图标码**：✕ |
| `3=` | `0xE7` | 小写拉丁 **`ç`**（c 带软音符） | **不是图标** = 字母 ç |
| `4=` | `0xF1` | 小写拉丁 **`ñ`**（n 带波浪号） | **不是图标** = 字母 ñ |
| `5=` | `0xB1 0xB5` | △ 与 ✕ 并排，**两张都画对** | 两码可连续使用 ✓ |
| `6=` | `0xE7 0xF1` | ç 与 ñ 并排 | 两个字母可连续使用 ✓ |

**同时**：底部提示栏照旧显示 `△ 返回` / `✕ 查看`（见同帧截图）——
那是 UI 画的，与上面 6 行正文无关，正好把两套东西在同屏摆在一起。

> 也就是说：**图标画得出来、位置正确、不是空白也不是乱码** ⇒
> `0xB1`/`0xB5` 的硬编码 UV 与美术资源是匹配的（现役盘**没有**图标错位的毛病）。

---

## 五、★ 总表（给人看的）

| 盘上字节 | CSV 里写成 | 是哪个键 | 长什么样 | 验证过吗 |
|---|---|---|---|---|
| `0xB1` | `{{BTN:E0B1}}` | **△ 三角键** | 深色圆键帽 + **绿色三角** | ✅ **实机截图**（f26200）**+ ELF 硬编码 UV + 图标图集** 三重 |
| `0xB5` | `{{BTN:E0B5}}` | **✕ 叉键** | 深色圆键帽 + **蓝/粉叉** | ✅ 同上 |
| `0xE7` | ~~`{{BTN:E0E7}}`~~ | **不是手柄键** | 小写字母 **ç** | ✅ 实机截图（f26200） |
| `0xF1` | ~~`{{BTN:E0F1}}`~~ | **不是手柄键** | 小写字母 **ñ** | ✅ 实机截图（f26200） |
| 其它所有字节 | — | — | **不是图标码** | 引擎只认上面两个值（ELF 穷举） |

**玩家看到的其它手柄图标**（△ ○ ✕ □、空白键、`?`、`✓`、宽箭头…）：
由 UI 快捷键系统 `kShortcutDefaultTC`（`0x2BEFE0`）按**动作编号**绘制，
**与文本码无关** ⇒ 文本里写不出来、`{{BTN:xxxx}}` 也调不出来。

---

## 六、工具链改了什么（**`{{BTN:XXXX}}` 格式零变化**）

| 文件 | 改动 |
|---|---|
| `tools/text_csv/icon_table.py` | **新增**。图标码总表（`ICON_CODES` / `NOT_ICON_CODES` / `SHORTCUT_SYSTEM`）+ 查询接口 + **候选枚举** + 自检（可单跑） |
| `tools/text_csv/tcslib.py` | **新增**查询接口（惰性导入包装，老脚本零改动）：`icon_info()` / `icon_key()` / `icon_name()` / `all_icons()` / `engine_icon_bytes()` / `candidate_icon_bytes()` / `describe_icon_byte()` / `icon_summary_lines()`。**既有格式、区间、编解码、字库预检一行未动** |
| `tools/iso_build/dump_font.py` | ① `icon_bytes()` 改为「`0xB1..0xFF` 未被字符集占用 ∪ 旧 `SINGLE_BAND` 未映射字节」（**1 个都不少**）；② 控制台**打印图标码全集**（含文本里没用到的）+ 候选逐个解释；③ `summary.json` 新增 **`icons`** 一节；④ `_font_charset.csv` 的 `kind` 新增 `latin1` / `unmapped`（`icon` 只剩真图标）；⑤ 「空字节」相关文案更正 |
| `tools/text_csv/FORMAT.md` | **追加**「★ round42 新增：手柄图标码总表」（非程序员人话版） |
| `docs/BUILD_TOOLCHAIN.md` | **追加**同名一节 + **更正**上文 `kind=icon` 的旧口径 |

### 6.1 修掉的「缺漏」到底是什么

| | 旧逻辑 | **新逻辑** |
|---|---|---|
| 什么时候认出一个图标码 | **只有 dump 的文本里出现过**那个未映射字节 | **枚举字节空间**：`0xB1..0xFF` 减去字符集占用 |
| 引擎认、但当前译文没用到的码 | **完全看不见** | 列出来（本盘没有这种码：两个都已被译文使用） |
| `0xE7`/`0xF1` | 混报成"手柄按键图标" | 单列成 `latin1`，注明是 **ç / ñ** |
| dump_font 的字库清单 | 只见 `icon` 一类 | `icon` / `latin1` / `unmapped` 三类分开 |

**查询示例**：

```python
import tcslib
tcslib.icon_name(0xB1)                  # '△ 三角键'
tcslib.icon_key('{{BTN:E0B5}}')         # 'cross'
tcslib.all_icons()                      # 全部 2 个图标码
tcslib.candidate_icon_bytes(tcslib.Charset())   # 本盘 0xB1..0xFF 里空着的字节
tcslib.describe_icon_byte(0xE7, tcslib.Charset())   # '不是图标 0xE7 = ç …'
```

### 6.2 回归验证（改动没破坏任何既有行为）

| 项 | 结果 |
|---|---|
| `python tools/text_csv/icon_table.py`（独立自检） | **全部通过 ✓** |
| `work/…/r42/p22_icon_table_selfcheck.py`（32 项） | **32 通过 / 0 失败** |
| `inject_text_csv.py --csv work/builds/GR_ZH93/text --src GR_ZH93.iso --check-only` | **exit=0**（`{{BTN:…}}` 60 处 / 4 个标记照旧识别；字库预检照旧通过） |
| `dump_font.py --iso GR_ZH93.iso --out …/r42/fonttest` | 正常产出；`kind` 计数 `ascii 95 / icon 2 / latin1 2 / pair 1319 / single 108`；引擎格位自查 **1504/1504 一致 ✓** |
| 标记格式 / 区间 / 编解码 | **逐字节未变**（`{{BTN:%04X}}`、`U+E080..U+E0FF`、`marks_to_pua`/`pua_to_marks` 全原样） |

---

## 七、已知限制（诚实挂账）

1. **shortcut 图标的 `index → 动作名` 没逆向**。只确证了"存在这张表、它在 UI 侧、
   与文本字节无关"。要把索引对上"哪个动作"需要 UI/动作表侧取证（另立任务）。
2. **`pda_counterparts.rsb` 的运行时装载路径未 100% 定死**：
   `GR.IMG #861 PDA_COUNTERPARTS.RSB`（262237 B，头 93 B，`ver=6 w=256 h=256` 且四通道位宽 `8 8 8 8`
   ⇒ 256×256 **RGBA8888**，恰好填满）与 `COMMON.PAK` 里的同名 256×256 PSMT8 记录
   **是两张不同的图**。实机已证"画出来是对的"，但**引擎实际采的是哪一张**没有下断验证。
   （两张图的美术内容都来自同一套原版素材，本工程都未改动。）
3. **只覆盖"文本码"这条路**：HUD 直接绘制的图标（血条旁、准星旁…）不在本表范围，
   它们是 UI 代码里的精灵，本来就没有"码"。
4. **`0xE7/0xF1` 是 ç/ñ 只由"实机画出来是字母"+"出现在 Français/Español"两证支持**；
   没有在法/西语菜单里实机切换语言验证（需要改语言设置，本轮没做）。
5. 本轮**没有改动任何既有 ISO**：`GR_EN_ORIG` / `GR_ZH91` / `GR_ZH92` / `GR_ZH93` 全部只读；
   实验盘是新建的 `GR_ZH95_icon` / `GR_ZH96_icon`。
6. 实机只跑了**一个实例**（`run_opt.py` 串行两次，各 exit=0）。

---

## 八、给用户的一句话

> **手柄图标码真的只有两个**：`{{BTN:E0B1}}` = **△ 三角键**、`{{BTN:E0B5}}` = **✕ 叉键**。
> 我在实机上把 4 个可疑的码一个个打出来看过：`B1` 画出绿三角、`B5` 画出叉，
> 而另外两个（`E7`/`F1`）画出来是**字母 ç 和 ñ**（法语/西语菜单里的），**不是手柄键**。
> 你看到的"四个面键 + 左右键"是**界面自己画的按钮提示栏**（△ 返回 / ✕ 查看 那一排），
> 那套图标**不来自文本**，所以文本里写不出来、也不该去写。
> 工具链这边已经把「只认文本里出现过的码」这个缺漏修掉了：现在它会**把全集列出来**
> （含没被用到的），并且会告诉你**每个码是哪个键**。你原来的写法一个字都不用改。

---

## 附：本轮产物与脚本

| 路径 | 说明 |
|---|---|
| `tools/text_csv/icon_table.py` | ★ 图标码总表 + 查询接口（新增） |
| `work/builds/GR_ZH93/temp/r42/p01_candidates.py` | 候选字节枚举 |
| `…/p02_elf_icon_scan.py` | 全 ELF 图标字节比较点 + 图标条 UV 常量扫描 |
| `…/p03c_shortcut_tc.py` | `kShortcutDefaultTC` 的 index→UV 表 |
| `…/p04_icon_band.py` `…/p05_texture_probe.py` `…/p06_icon_strip.py` `…/p07_en_atlas.py` | 图集/纹理定位（含"EN 是 512×512 PSMT8、ZH 是 1024×512 PSMT4"的发现） |
| `…/p12_icon_sheet.py` `…/p13_icon_boxes.py` `…/p16_ascii_icons.py` | 图标图集抠图与 UV 框逐框判定 |
| `…/p17_find_texture.py` `…/p19_rsb_render.py` | 定位并试解 `PDA_COUNTERPARTS.RSB` |
| `…/p22_icon_table_selfcheck.py` | 工具链自检（32 项） |
| `…/p25_make_test_csv2.py` | 实验 CSV 生成（只改 `SFXML:T0063`） |
| `…/p28_icon_art_hash.py` | 图标美术资源跨盘一致性 |
| `work/builds/GR_ZH96_icon/GR_ZH96_icon.iso` | 实验盘（`f90a34ad…`） |
| `work/builds/GR_ZH96_icon/temp/dump_icon_t63/snap_f00026200.png` | ★ 实机判定截图 |
| `work/builds/GR_ZH93/temp/r42/game_t63_zoom.png` | 判定截图 4 倍放大（人眼可读） |
| `work/builds/GR_ZH93/temp/r42/iconband_EN_ORIG.png` | 图标图集那一带（放大 8 倍） |
| `work/builds/GR_ZH93/temp/r42/hintbar_f26200.png` | 底部提示栏放大（证明那些图标是 UI 画的） |
