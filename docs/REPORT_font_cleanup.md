# 字库清理报告 —— 残墨清除 + 死字回收（round49，产出 **GR_ZH98**）

> 工具 `tools/iso_build/font_residue.py` (r49.1) · `tools/iso_build/patch_zh98_font_cleanup.py` (r49.1)
> 基底 `GR_ZH97`（sha256 `6fc9661591509682…`）· 产出 `work/builds/GR_ZH98/GR_ZH98.iso`
> **本轮只动两样东西: `charset_compiled_zh16.json` 的 144 条死字映射 + `COMMON.PAK`
> `new_font_revised` 像素容器的 14940 个 texel**；其它一个字节都没碰（全盘差分已证）。

---

## 〇、一句话（给非程序员）

**碎片清了 14940 个黑点（图集墨从 104748 降到 89808），顺手把 144 个"再也用不到的旧字"
回收掉，码位从 1319 个降到 1175 个 —— 现在字库还能再放 237 个新字（原来只有 93 个）。
游戏里一个字、一个图标都没变（全盘逐字节差分：像素容器之外 0 字节改动）。**

| 用户问题 | 答案 |
|---|---|
| 纹理里那些碎片清掉了吗？ | **清了**：真残墨 4831 px（32 块）+ 144 个死字的字形 10109 px = **14940 px**；清完再测**残墨 = 0 px** |
| 那 20 个人名用字还有没有被用到？ | **一个都没被用到**：`珍琳费贾赖辉辛迈郑闫阮阳陈隆雅韦魏鲍鹏麦` 在**全部注入表**（2261 行、所有列）出现 **0 次**；`view_character_names.csv`（4439 行）里 `has_cjk=yes` 的行 = **0 条** ⇒ 人名确实已经全是英文 |
| 报告里说的"92 个旧字没回收"是什么？ | 那是"**charset 空槽里、格子上还有墨**"的格子数。逐格拆开后：这些格子里的墨**全部属于引擎在用的采样窗**（50 格整格归单字节记录码、42 格被 FT 记录矩形压着）⇒ **92 个里一个都不能"回收成新字位"**。真正能回收的是"0 次使用"的**死字**，共 144 个（含那 20 个） |
| 现在还能再放多少个新字？ | **237 个**（图集上那格是白的口径；原来 93 个）。严格口径（连别人的采样窗都不碰）171 个（原来 88 个） |

---

## 一、工单三件事怎么落地的

### ① 残墨：先划清"引擎到底会采样哪些像素"，再谈清不清

图集里有 **4 类"别人的地盘"**，不先排除就会误清：

| 采样路径 | 覆盖范围 | 说明 |
|---|---|---|
| 对偶码（1504 个字位） | `x=16*col`，`y=2+16*(row+3*[row≥12])`，`col=slot%62 ≤ 61` | ⇒ **x 最大 976，格右边界 991**；图集宽 1024 = 64 格 ⇒ 每行右边 **2 格（x=992..1023）对偶路径永远采不到** |
| 单字节 / ASCII 的 **FT 记录矩形** | 3 个 face、544 条非空矩形 | 矩形**不对齐 16×16**（例：武器页上下滚动箭头 = 码 `0x7B`/`0x7D` 的 5×13 小矩形 `(89,395)-(94,408)`） |
| 手柄图标码 `0xB1/0xB5` | 硬编码 UV 走另一张贴图（`pda_counterparts.rsb`） | 但它们在 FT 记录表里仍占着格子（`(136,420)-(146,436)` 被 `0x20/0x7F/0xA1..0xAD` 共用）⇒ 那一角不能动 |
| 网格外的结构性空洞 | `y=0..1`、`y=194..241`（被 `GRID_SKIP_ROWS=3` 跳掉的 3 行）、`y≥450`、行 24 右侧（x≥256） | 对偶公式同样不覆盖 |

判据（`font_residue.py`）：

```
残墨 = 墨 ∧ ¬(charset 已用对偶格) ∧ ¬(全部 FT 记录窗, 膨胀 ±(4,2))
```

* **已用对偶格**整格保留（那是活字形）；
* **FT 记录窗**取"原矩形 ∪ 矩形+(4,2) ∪ 膨胀 ±(4,2)"的**超集** —— 宁可少清，不赌。

实测（GR_ZH97）：

| 项目 | 数值 |
|---|---|
| 图集墨 | 104748 texel（19.98%） |
| **残墨** | **4831 px（4.61%）、32 块** |
| ├ 落在"单字节记录码占死的格"里 | 309 px（10 个格，行 21/22 col 5..8、行 23 col 8/9 —— **旧字形碎片**，只清窗内之外那块） |
| └ 落在"对偶公式永不覆盖的区域" | 4522 px（回绕列 x≥992 **2212**、网格下方 y≥450 **1922**、包头空洞带 17、顶部 2 行 2 等） |

### ② 20 个人名字：逐表复核 = 全部死字

扫**全部注入表**（`*_text_*.csv` 3 张 / 2261 行 / 所有列，含 `text_en`/`note` 等只读列）：
20 个字**各出现 0 次**。再扫**全部 view 表**（8 张，含 `GR_ZH97_view_character_names.csv` 4439 行）：
`has_cjk=yes` 的行 **0 条** ⇒ 盘上 .ATR 里没有任何中文人名 ⇒ 这 20 个字是**彻底的死字**。

顺带把"**所有** 0 次使用的对偶字"都找了出来：**144 个**（20 个人名字全在里面）：

```
µ丁丹丽乔亨伟伯佐俊傅兰冈凡刘勃卜历史叶吕吴哥哲唐圣坤培夏奈奋姚娜娱孙宁宇宋宗富岩峰廉弗彭
彼徐怀思恩戈戴扬斌斐昂晓曹朱李杜杨杰柯柴桑楠欣欧歇殷毅毕汀汤沈泰洛津洪浩滕潘熊玉王玲珀珊
珍琳琼瑞瑟皮督福穆缪罕翁翔翰耶肖舒艾芬茨荣莉莱菲葆蒂蒙蓓蔡蕾袁裁詹费贾赖辉辛迈逊邹郑闫阮
阳陈隆雅霍韦魏鲍鹏麦黛
```

**这 144 个字的"为什么是死的"**：它们是 round40~45 为**把英文人名译成中文**而加进 charset 的
人名用字（姓氏/名字字表 + `µ`）；round48 之后人名已按用户要求改回英文 ⇒ 这些字在任何一张
可注入表里都不再出现。它们**不是**排版用字、也不是程序串用字：逐字在 8 张 view 表里查过，
只有 8 个字（勃吴宗恩楠洛潘琼）在 **`has_cjk=no`** 的二进制串里各撞到 1~2 次
（压缩贴图 `.BMZ/.BM` 与 ELF 里两个字节恰好撞上对偶码，`cjk_run=1`，是**误码不是用字**）。

### ③ "92 个旧字没被回收"的真相

`GR_ZH97/release/字库报告.md` 写的是「要先"回收旧字"才能用的位子：92 个（格子上压着旧字形）」。
逐格拆开（`residue.json` 的 `slots` 全表 + 报告 §五）：

| 92 个的构成 | 个数 | 能不能给新字用 |
|---|---|---|
| 整格被**单字节记录码**占死（`ATLAS_ENGINE_SINGLE_CELLS`） | **50** | **永远不能**：引擎拿这些格画单字节汉字/符号（`0xDB..0xFE` 等在行 18/19，`0x9D..0xA0/0xAE/0xFF` 在行 24，图标码在行 21/22/23） |
| 被 **FT 记录矩形**压着 | **42** | **不能**：那是单字节/ASCII 的采样窗 |
| 合计 | 92 | ⇒ **可回收成新字位 = 0 个** |

⇒ 报告那句话的口径容易让人误会成"有 92 个旧字躺在那里等着回收"。
真实情况是：**能回收的字位来自"0 次使用的死字"（144 个）**，而这 92 个格子的墨
属于引擎在用的采样窗，动它就是 round43 那个"写坏活字形"的坑。

---

## 二、工具 `tools/iso_build/font_residue.py`（用户点名要的"小工具"）

```
# 量 GR_ZH97（要用"当年那份"字符表 —— 见下面的 ⚠）
python tools/iso_build/font_residue.py --iso work/builds/GR_ZH97/GR_ZH97.iso \
    --charset work/builds/GR_ZH98/temp/charset_before_font_cleanup.json \
    --out work/builds/GR_ZH97/temp/font_residue --prefix GR_ZH97
# 量本轮的产出盘（用现役字符表）
python tools/iso_build/font_residue.py --iso work/builds/GR_ZH98/GR_ZH98.iso \
    --out work/builds/GR_ZH98/temp/font_residue --prefix GR_ZH98
```

产物（**只读**，只在 `--out` 目录写文件）：

| 文件 | 内容 |
|---|---|
| `residue.json` | 逐格/逐区域 `{col,row,x0,y0,ink_px,分类,建议}` + **1504 个槽位全表** + 回绕列判定 + 副本判定 |
| `residue_report.md` | 人话总结（哪些真残墨可清 / 哪些必须保留 / 为什么） |
| `residue_map.png` | 三色标注图：蓝=已用字形格 / 绿=FT 采样窗（保留）/ 红=残墨 / 黄=不可寻址区 |
| `residue_zoom.png` | 残墨簇 4 倍放大 **[清理前 \| 清理后]** 对照（`AFTER` 里的红点 = 会被清的像素） |

**每个"建议清除"的格都有可解释的理由**（`reason` 字段），例如：

* 空对偶槽 + 不在任何采样窗内 + 却有墨 ⇒ 真残墨（旧字形没清干净）；
* 整格被单字节记录码占死 + 窗内的一角保留 ⇒ 只清窗外那块；
* 对偶公式永不覆盖（回绕列/空洞带/网格下方）⇒ 画不出来，可清。

> ⚠ 残墨是**相对字符表**算的（"已用对偶格"来自字符表）⇒ 量**历史盘**要用**当年那份**字符表。
> 本轮量 GR_ZH97 用的就是 `GR_ZH98/temp/charset_before_font_cleanup.json`：
> `font_residue.py --iso …/GR_ZH97.iso --charset …/charset_before_font_cleanup.json`
> ⇒ **4831 px**；若用回收后的新字符表去量同一张旧盘，会把"那 144 个被回收字的字形"
> 也算成残墨（14695 px），那不是残墨。

### 两处"实测而非猜"的定案

1. **"回绕列"x=992..1023 的语义**：穷举全部 **1504** 个 slot 的采样窗 ⇒ 命中 x≥992 的 **0 px**；
   穷举全部 544 条 FT 记录矩形 ⇒ 原样命中 **0 px**、加 `+(4,2)` 命中 **13 px**、膨胀后 **16 px**
   （只有 `large`/`default` 的 `0xDA` 那条 `(976,338)-(992,354)` 挨到边上）。
   **"回绕副本"是历史写入工具按"裸图 flat 坐标"又写了一遍的产物**：用 FFT 互相关逐块比对，
   每一行那 2 格的墨都是**别处内容的逐像素副本**，而且副本比源**低 1 行**（`dy=+1`）——
   正是 `tcslib` 里记的旧 flat 公式"回绕列的字形低 1 行"的指纹（`corr == 块内墨数` 完全吻合）。
2. **FT 记录矩形到底是不是采样窗**：逐条看"墨的包围盒相对矩形左上角的偏移" —
   有墨的 544 条里，墨从**第 0 列**就开始的 **91 条**、从**第 0 行**开始的 **77 条**；
   实例：ASCII `A` 的矩形 `(256,452)-(264,468)` 里是一个**端正的 A**，同一矩形 `+(4,2)` 里是**错位的碎片**。
   ⇒ **矩形本身就是采样窗**（`+(4,2)` 是历史**写入侧**偏置）。
   定位用原矩形（与 `repack_font` 同口径），而**清理保护罩仍故意用 ±(4,2) 膨胀**。

---

## 三、回收 + 清理怎么落盘：`patch_zh98_font_cleanup.py`

构筑命令（**可重放**）：

```bash
python tools/iso_build/make_build.py GR_ZH98 \
    --from work/builds/GR_ZH97/GR_ZH97.iso \
    --patch tools/iso_build/patch_zh98_font_cleanup.py \
    --inject-csv work/builds/GR_ZH97/text \
    --no-font-repack
```

补丁做三件事（都只碰 charset 与像素容器的数据区）：

1. **判死字**：扫全部注入表（所有列）+ 全部 view 表的 `has_cjk=yes` 行 ⇒ 144 个
   （任何一个只要在 `has_cjk=yes` 行里出现过就**不删**，本轮 0 个触发）；
2. **擦像素**：残墨 4831 px + 144 个死字的整格（144 格 × 256 px = 36864 px 区域，其中墨 10109 px）。
   写盘走 `repack_font.Atlas.write_pixels`（只写封包**数据区**），写前记下 8 个 48B 包头、
   写后**逐字节核对**，并回读校验"盘上引擎图 == 原图 − 清除掩码"；
3. **改 charset**：`pair_of` 1319 → **1175**（−144）。改前留底
   `GR_ZH98/temp/charset_before_font_cleanup.json`；被删字的**码位 + 16×16 字形位图**
   存进 `GR_ZH98/temp/font_recycle_backup.json` ⇒ **可还原**（位图 base64 + `np.unpackbits`）。

### ★ 为什么这一轮**关掉**了"字库紧凑重排"（`--no-font-repack`）

先按标准流程跑过一轮（`--patch` + 自动重排 + 注入），实测代价：

* 重排把 1175 个字压到最前面的可用格 ⇒ **1039 个字改了码位** ⇒ 盘上所有旧编码文本必须整体重编码；
* 更麻烦的是它撞坏了一条**字节级锚点**：`tcslib.selfcheck_anchors` 要求 `(0xAF,0xA1)` 必须是
  合法对偶码（`AF A1 BD` 那条锚点），重排后 1175 个字只用到 lead `0xAD`，`0xAF` 段全空
  ⇒ `dump_text_csv.py` **直接拒绝出表**（构建日志：
  `work/builds/GR_ZH97/temp/r49/build_zh98_attempt1_with_repack.log`）。`tcslib` 是受保护文件，
  不该为了让它过而改它；
* 而重排**换来的容量是 0**：
  重排口径 `可用格 1409 − 在用 1175 = 234`；不重排口径 `原本就白的 90 + 本轮擦白的 144 = 234`
  —— **一模一样**。

⇒ 决策：**不重排**。好处是**一个字位都没变**，盘上文本**逐字节原样**，
"文本逐字符不变"这件事从"重编码之后再验证"变成**"根本没动过"**。
（这也正是工单里写的期望：「回收只动 charset 与图集，不动文本」。）
将来要再加字、需要重排时，照常跑标准流程即可 —— 那时才需要整体重编码。

---

## 四、静态验收（逐条，全部可复现）

| 验收项 | 命令 | 结果 |
|---|---|---|
| 补丁清单缺失 0 条 | `audit_inventory.py GR_ZH98.iso` | **在役 44 / 缺失 0 / 其它 1**（与 GR_ZH97 逐字相同） |
| 字库覆盖预检 | `inject_text_csv.py --csv …/GR_ZH97/text --src GR_ZH98.iso --check-only` | **exit 0** |
| 引擎格位公式 | `dump_font.py` → `grid_row_alignment` | **行 0..24 全 0**；`grid_selfcheck` **1504/1504、mismatched 0、dup 0、oob 0** |
| 缺字形 | `dump_font.py` → `missing_glyph` | **0**（1383 个字符：`has_glyph` 1382 / `missing` 0；那个"未映射字节"占位不算字形） |
| 残墨像素数 | `font_residue.py` | **4831 px → 0 px** |
| 图集墨 | `dump_font.py` → `atlas.ink_texels` | **104748 → 89808**（−14940，−14.3%） |
| 可直接用的新字位 | `dump_font.py` → `pair.vacuum_usable` | **93 → 237** |
| 严格干净格（不碰任何采样窗） | `dump_font.py` → `pair.strict_window_free` | **88 → 171** |
| 对偶已用 / 空位 | `dump_font.py` | 1319/185 → **1175/329** |
| 文本逐字符不变 | `diff_text_versions.py GR_ZH98 GR_ZH97` | **修改 0 条**；2261 条内容相同；字符 65271→65271、中文 45771→45771 |
| 文本**逐字节**不变 | 注入器自检 | `[diff] 全盘差异 0 B / 3 个写入窗口`；`EN_STRINGS.RES@MENU/@GR` **改动 0 / 逐字节不变 2232**；`EN_SPECIAL_FEATURE.XML` **改动 0 / 69** |
| 全盘差异只落在图集 | `iso_bytes_diff.py ZH97 ZH98` | 差异 **11659 字节**，**容器外差异 0**；真正变化的 texel **14940**（= 墨量下降，一一对应） |
| 受保护区域 | `check_protected_ranges.py` | **23 个敏感区域，含差异 0 个**：ELF / PVD / MENU.IMG 与 GR.IMG 条目表 / `GR.IMG #551..#565` 制作组名单 / COMMON.PAK 头部与像素容器之后 / **FONT.RES 全部** |

> `GR_ZH98.iso` sha256 = `f0fc6d8fd00232dc6afe5237143cadef29fec2b1cbedfd0c416ce4b723992ac3`
> （尺寸与基底同为 1648164864 B）

**"现有盘全只读"也逐张核对了**（本轮结束后重算 sha256，与各自记录值一致）：

```
GR_EN_ORIG  2b42ea7ce9bd0a85972a07ca59b1b9d79422ed318b85737db3cfd17daa788531
GR_ZH91     42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88
GR_ZH92     1d30c1067beb8fc8534193486f23f75489447eb0487ab24d06ef66c0627120b6
GR_ZH93     e037f6292940811144e2d0d629ec4c4f3e2cfc306d099a4c96b44f6ee08d19be
GR_ZH94     1cac50c1c7a6c827da006bdd09ce1214dc59b00493c7ce9e17495c2ac0d4f301
GR_ZH95     c1f5d8498c66de2061346a75d482d5485105250a3a2984e8604a20b7eb5afafb
GR_ZH96_fix 4486d5769286b93a82e6acfa06c57c4c9e284d909411fd2be570fd77078ac709
GR_ZH97     6fc9661591509682e4079885f4e978310a25631e25f33a31213a947dceeb5098  ← 基底, 未变
```

**回收是"可还原"的**（抽验脚本 `verify/r49_check_backup.py`，逐个 144 个字）：

| 检查 | 结果 |
|---|---|
| 备份里的码位 == 改前 charset 的 `pair_of` | **144/144 一致** |
| 备份里的 16×16 位图 == GR_ZH97 盘上那一格（逐像素） | **144/144 相同** |
| 同一格在 GR_ZH98 上是否已全空 | **144/144 全空** |
| 仍留在 charset 里的死字 | **0 个** |

---

## 五、实机验收（pcsx2-gsrunner，单实例，模板记忆卡复位）

**方法**：两盘用**同一份 nav**（帧号对齐）、每轮**从模板复位记忆卡**（与 `tools/capture/run_opt.py`
同一套口径：`third_party/emu/run/memcards` → 独占目录）、起跑前等"连续 2 次、间隔 30s 无任何
`pcsx2-gsrunner` 实例"（单实例守规）、导航键一律 `tap` + 紧跟 `release`(fr+2) 的 **2~3 帧短按**
（`tap` 默认按住 12 帧，本作菜单 ~7 帧即连发 ⇒ 长按会一次移 2~3 项）。
跑完用 `cap_diff.py` 对**同名帧逐像素**比较。

驱动脚本：`work/builds/GR_ZH98/temp/verify/r49_ab_all.py`（→ `cap_run.py` / `cap_diff.py`）。

| 轮次 | nav | 帧数 | 覆盖到的页面（drawlog 判定） | A/B 结果 |
|---|---|---|---|---|
| `r49_menu` | `r49_nav_menu.txt` | 13000 | 引导「载入中…」→ 选择文件 → **主菜单**（光标停在「训练」，底栏提示） | **127/127 帧逐像素相同** |
| `r49_doc` | `r49_nav_doc.txt` | 30200 | 选择文件 →（输入名字屏）→ 主菜单 → 特别收录列表 → **武器页** → 统计页 → **特别收录长文页「何为幽灵？」+ 连滚 14 次** | **299/299 帧逐像素相同** |
| `r49_wpn` | `r49_nav_weapon.txt` | 30500 | 主菜单 → 特别收录 → **武器**（列表/详情）+ 滚动 | **302/302 帧逐像素相同** |

每轮的 `cap_<tag>.json` 里记着：iso sha256 / nav sha256 / 帧数 / 末帧 / 页面判定 / require 是否命中；
两盘三次的 `rc=0`、帧数、末帧、页面判定**逐项相同**（例：doc 轮两盘都是 `299 帧 / 末帧 30199 /
['选择文件','输入名字(键盘屏)','主菜单','特别收录','武器页','统计页','DOC(何为幽灵)']`）。

> `r49_doc` 那一轮的 drawlog 里确实画出了受影响的字：`中 斗 训 习 面 务 可 出 如 以 到 定 是 任 火 动`
> —— 它们所在的字形格本轮**一个像素都没动**（只在"已用对偶格"之外清理）。
>
> `r49_wpn` 那一轮**没有**在 drawlog 里出现「手枪」这个探针词（`require` 未命中，两盘一样），
> 也就是说"武器详情页上那两枚 ▲▼ 箭头有没有出现在画面上"这一条**没有直接拍到**；
> 但下面这条静态证明比拍到更强：**箭头那两个 5×13 小矩形 (89,395)-(94,408) / (97,395)-(102,408)
> 所在的所有采样窗像素，两盘逐点相同（差异 0）**。

### 静态证明（比实机 A/B 更彻底：覆盖"每一个会被画出来的像素"）

`work/builds/GR_ZH98/temp/verify/r49_check_windows.py` 把两盘图集的差异按"这些像素归谁"分组：

| 组 | 覆盖 | 差异 | 期望 | 结果 |
|---|---|---|---|---|
| ① 544 条 FT 记录矩形（**原矩形 = 实测定案的采样窗**） | 40664 px | **0** | 0 | OK |
| ② 记录窗 ±(4,2) 膨胀（最保守口径，剔除被回收的格） | 50627 px | **0** | 0 | OK |
| ③ charset 在用的对偶格（**活字形 1175 个**） | 300800 px | **0** | 0 | OK |
| ④ 被回收的 144 个字的格子（**故意**擦白） | 36864 px | 10109 | = 它们的墨 | ✓ |
| ⑤ 其余 = 残墨区（**故意**清） | 139365 px | 4831 | = 4831 | ✓ |

**①②③ 全 0 差异 ⇒ 两盘在所有"引擎会采样到"的像素上逐点相同**；④⑤ 的差异恰好等于报告里
写的两个清理量（10109 + 4831 = **14940** = 全盘差异 texel 数，且**全部是"墨→空"、空→墨 0 个**）。

因为残墨按定义就是**引擎采样不到的像素**，A/B 的期望是"**逐像素完全相同**"；
实测三对全部如此 ⇒ 与"画不出来"的判定互相印证（**清掉的 14940 px 没有一个出现在画面上**）。

---

## 六、资料包

```
python tools/iso_build/dump_font.py --iso work/builds/GR_ZH98/GR_ZH98.iso \
    --out work/builds/GR_ZH98/font --prefix GR_ZH98 --scale 2 --only-sampled
python tools/maint/make_release_pack.py --build GR_ZH98 --view-from work/builds/GR_ZH98/text
```

产物 `work/builds/GR_ZH98/release/`：**25 个文件**（`MANIFEST.json` 逐个 sha256）。

| 部分 | 内容 |
|---|---|
| 顶层 | `README.md`（人话总索引，从 GR_ZH97 的复制后改版本号/sha/数字）、`MANIFEST.json`、`字库报告.md`、`字库报告.xlsx`（6 页） |
| `text/` | 16 个：3 张可注入表 + `text.meta.json` + 10 张 view-only 表 + `view_containers.meta.json` + `README_文本表.md`（人话说明） |
| `font/` | 6 个：`atlas.png`(2×) / `atlas_1x.png` / **`atlas_sampled.png`**（`dump_font --only-sampled`：只拼"引擎真正会采样的格"）/ `atlas_README.txt`（看图须知）/ `charset.csv` / `ft.csv` |

**顺带修了"字库报告"里那句让用户误会的口径**（`tools/maint/make_release_pack.py`，只加说明文字、
不动任何数字逻辑）：「需回收 92 个」那一行现在旁边就写着"这些格子的墨全部属于引擎在用的采样窗
⇒ 对偶码永远不能用 ⇒ 不存在'回收旧字就多出位子'这回事"（Markdown 版与 xlsx 的「概要」页都加了）。

`release/` 里 4 个人工维护文件（`README.md` / `text/README_文本表.md` /
`font/GR_ZH98_font_atlas_README.txt` / `font/GR_ZH98_font_atlas_sampled.png`）已在 MANIFEST 里
登记为 `(人工维护)`。

---

## 七、已知限制（诚实交代）

1. **"92 个旧字"的 0 回收结论是"口径结论"，不是"没找到"**：它们是被单字节记录码/FT 记录窗
   占住的格子；要让它们变成新字位，得先把单字节字形搬到别处并改 `FONT.RES` 的记录矩形 ——
   那是另一个工程（`FONT.RES` 本轮要求"差异 0"）。
2. **FT 记录窗的保护罩用 ±(4,2) 膨胀**（比实测的"原矩形"更宽）⇒ 有 44 个格被判"被压着"而少清。
   这是**故意的保守**（round43 有过"写坏活字形导致进不了游戏"的实证）。
3. **144 个死字的"死"是"当前全部文本表 0 次"**，不是"永远用不到"：将来若要再用人名汉字，
   可以用 `GR_ZH98/temp/font_recycle_backup.json` 把码位与字形**原样还原**（位图已逐格存好）。
4. **图像会随翻译变化**：本轮结论基于 `work/builds/GR_ZH97/text` 这一版用户表；
   用户改表后重跑 `font_residue.py` 即可得到新的残墨/死字清单（工具全部现算，不写死常量）。
5. **"回绕列是谁写的"没有考古到底**：已证明"引擎采样不到"+"是别处内容的逐像素副本（低 1 行）"，
   没证明是历史上哪一次写入造成的。不影响清理决策（画不出来 = 可清）。
6. 本轮**没有跑紧凑重排**，charset 里留着 144 个空洞（码位不连续）。这不影响任何功能
   （容量按"可用格 − 在用"算），但下一个跑标准重排的轮次会做一次大换码 + 整体重编码。
7. **charset 的 `_font_repack.iso_sha256` 仍指向 GR_ZH97**（因为 `--no-font-repack` 会跳过
   `stamp_charset`；按工单"charset 只允许做回收死字这一种改动"，本轮**没有再写它**）。
   下一轮构筑时 `repack_font.plan()` 会因此打印一条"charset 记录的盘 ≠ 输入盘"的提醒 ——
   那条提醒自己就写着"正常构筑里这表示基底被本轮的 `--patch` 改过（没问题）"。
   本轮的准确状态记录在 charset 的 `_font_recycle_zh98` 段与
   `GR_ZH98/temp/font_cleanup_report.json` 里。同理 `_font_repack` 里的
   `used=1319 / remaining_capacity=90` 是 round46 那次重排留下的旧数字，**不要当现值**
   （现值看 `字库报告.xlsx` 或 `font/GR_ZH98_font_summary.json`：已用 1175 / 可直接用 237）。

---

## 八、复现命令（一条条抄就能重放）

```bash
# 0) 量残墨 / 死字 (只读)
python tools/iso_build/font_residue.py --iso work/builds/GR_ZH97/GR_ZH97.iso \
    --charset work/builds/GR_ZH98/temp/charset_before_font_cleanup.json \
    --out work/builds/GR_ZH97/temp/font_residue --prefix GR_ZH97
python tools/iso_build/patch_zh98_font_cleanup.py \
    work/builds/GR_ZH97/GR_ZH97.iso work/builds/_dry/GR_ZH98.iso --list-only

# 1) 构筑 (补丁 = 清残墨 + 擦死字字形 + 回收码位; 不重排 ⇒ 文本逐字节不动)
python tools/iso_build/make_build.py GR_ZH98 \
    --from work/builds/GR_ZH97/GR_ZH97.iso \
    --patch tools/iso_build/patch_zh98_font_cleanup.py \
    --inject-csv work/builds/GR_ZH97/text --no-font-repack

# 2) 静态验收
python tools/iso_build/audit_inventory.py work/builds/GR_ZH98/GR_ZH98.iso
python tools/text_csv/inject_text_csv.py --csv work/builds/GR_ZH97/text \
    --src work/builds/GR_ZH98/GR_ZH98.iso --check-only
python tools/text_csv/diff_text_versions.py GR_ZH98 GR_ZH97
python tools/iso_build/font_residue.py --iso work/builds/GR_ZH98/GR_ZH98.iso \
    --out work/builds/GR_ZH98/temp/font_residue --prefix GR_ZH98     # 期望残墨 0 px
python work/builds/GR_ZH98/temp/verify/iso_bytes_diff.py \
    work/builds/GR_ZH97/GR_ZH97.iso work/builds/GR_ZH98/GR_ZH98.iso \
    --json work/builds/GR_ZH98/temp/verify/diff_zh97_vs_zh98.json
python work/builds/GR_ZH98/temp/verify/check_protected_ranges.py \
    work/builds/GR_ZH97/GR_ZH97.iso work/builds/GR_ZH98/GR_ZH98.iso \
    work/builds/GR_ZH98/temp/verify/diff_zh97_vs_zh98.json
python work/builds/GR_ZH98/temp/verify/r49_check_windows.py    # 采样窗像素逐点相同
python work/builds/GR_ZH98/temp/verify/r49_check_backup.py     # 144 个死字可还原

# 3) 实机 A/B (单实例 + 模板记忆卡复位; 两盘同一份 nav)
python work/builds/GR_ZH98/temp/verify/r49_ab_all.py all
python work/builds/GR_ZH98/temp/verify/cap_diff.py \
    work/builds/GR_ZH98/temp/verify/r49_menu_zh97 \
    work/builds/GR_ZH98/temp/verify/r49_menu_zh98 --tag r49_menu

# 4) 资料包 (+ 只拼"引擎会采样的格"的 1:1 图)
python tools/iso_build/dump_font.py --iso work/builds/GR_ZH98/GR_ZH98.iso \
    --out work/builds/GR_ZH98/font --prefix GR_ZH98 --only-sampled
python tools/maint/make_release_pack.py --build GR_ZH98 --view-from work/builds/GR_ZH98/text
```

---

## 九、产物清单

| 路径 | 内容 |
|---|---|
| `work/builds/GR_ZH98/GR_ZH98.iso` | 新盘（sha256 `f0fc6d8f…`） |
| `work/builds/GR_ZH98/temp/font_residue/` | 残墨测量四件套（json/report/map/zoom） |
| `work/builds/GR_ZH98/temp/font_cleanup_report.json` | 补丁报告（死字清单、逐格坐标、擦除像素数、备份路径） |
| `work/builds/GR_ZH98/temp/font_recycle_backup.json` | 144 个死字的码位 + 字形位图（**可还原**） |
| `work/builds/GR_ZH98/temp/charset_before_font_cleanup.json` | charset 改前留底（= GR_ZH97 那份，1319 条） |
| `work/builds/GR_ZH98/temp/verify/` | 全部验收日志 + 实机抓帧 + 差分 JSON + `r49_check_windows.py` / `r49_check_backup.py` |
| `work/builds/GR_ZH97/temp/font_residue/` | **清理前**的残墨测量四件套（4831 px） |
| `work/builds/GR_ZH98/release/` | 资料包（25 个文件，含 `README.md` / `字库报告.xlsx` / `font/…_sampled.png`） |
| `tools/iso_build/font_residue.py` | 残墨测量仪（只读） |
| `tools/iso_build/patch_zh98_font_cleanup.py` | 清理/回收补丁（可重放） |
