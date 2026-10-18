# REPORT_zero_missing_glyph_build2.md — 「零缺字成品盘」构建（round82）

> 分支 `round73/font-decompile` ｜ **未切分支、未 commit、未 merge**
> 只读：所有历史 ISO、`third_party/orig/**`、`%LOCALAPPDATA%\PCSX2\**`、`work/temp/NEW_Mem/**`
> 只写：本报告、`work/builds/GR_ZH98/temp/r82/**`、`work/builds/GR_ZH121/**`、`work/tools/zx_*.py`
> （另有任务书显式点名的探针盘 `work/builds/GR_TEST_FONTCAP_{H640,H640B,H1024,GROW}`）
>
> ## 一句话结论（不美化）
> **①** 成品盘 **`work/builds/GR_ZH121/GR_ZH121.iso` 已产出**，**六条硬断言全绿**，
> **P3 离线判据全过**（`[ok] 字库覆盖完全` / **缺字形 0** / `audit_inventory` 在役 44 缺失 0）。
> **②** ★ **但它实机跑不起来**：6000 帧里 **0 张截图、0 次纹理上传、needle `newfontrevisedrs` 0 命中**
> —— 游戏卡在进 UI 之前（黑屏）。**P1（贴图加高 + 容器重切）实机失败，且已定位到唯一变量**。
> **③** 隔离实验（全部裸跑 6000 帧、同一输入、基线可复现 191/191 逐字节一致）：
> | 变体 | 只改了什么 | 结果 |
> |---|---|---|
> | 基线 `GR_ZH113b` | — | 191 张截图、`newfontrevisedrs` 2873 hits ✓ |
> | `GR_TEST_FONTCAP_GROW` | **PAK 长大 + MENU 682 条 off 平移 + 声明长度扇区对齐** | **191 张截图、2872 hits ✓ 正常** |
> | `GR_TEST_FONTCAP_H640` | 上面 + **px_size 0x40010→0x501F0 + 容器重切成 10 段** | **0 张截图 ✗ 黑屏** |
> | `GR_TEST_FONTCAP_H640B` | 同上，但声明长度改成 28,482 扇区（= round31 探针 A/B 实机验证过的值）| **0 张截图 ✗** |
> | `GR_TEST_FONTCAP_H1024` | 同上，但记录 `h` 改成 1024（赌"引擎按 h 分配行数"）| **0 张截图 ✗** |
> | `GR_ZH121`（成品） | 全套 + charset + 丰富版文本 | **0 张截图 ✗**（同因） |
> ⇒ **卡点 = 像素容器/`px_size` 变大这一件事**；布局平移、扇区对齐、`h` 都不是原因。
> **④** 因此：**"零缺字"在离线层面已完全成立**（368 个新码位 + 364 个缺字全部有字形、可编码），
> **但没有拿到"实机可见"的闭环**。详见 §6 未做项与 §7 限制。

---

## 1. 交付物索引

| 类型 | 路径 |
|---|---|
| ★ 成品盘（离线全绿、实机黑屏） | `work/builds/GR_ZH121/GR_ZH121.iso`（1,648,164,864 B，**与原盘同尺寸**；sha256 `e99c458fcf5fa1a0…`）|
| 成品盘补丁日志（六条断言原文） | `work/builds/GR_ZH98/temp/r82/patch_font_full.log` / `patch_gr121_report.json` |
| 注入报告（316 条正文改写 + 回读一致） | `work/builds/GR_ZH121/temp/inject1_report.json` |
| 逐字节差异表 | `work/builds/GR_ZH98/temp/r82/diff_zh121.txt`（工具 `zx_diff_iso.py`）|
| 实机证据 | `GR_ZH113b/temp/dump_p1base{,2}`（基线 ×2）、`GR_TEST_FONTCAP_{GROW,H640,H640B,H1024}/temp/dump_*`、`GR_ZH121/temp/dump_zh121` |
| 字形/字库 dump | `work/builds/GR_ZH121/temp/fontdump/**`（图集 PNG 2048×1280、charset CSV、summary JSON）|
| 工具（全部 `work/tools/`）| `zx_lib.py` `zx_patch_font.py` `zx_patch_full.py` `zx_patch_p1.py` `zx_patch_probe.py` `zx_charset.py` `zx_textcheck.py` `zx_migration.py` `zx_recon.py` `zx_fontres.py` `zx_icon.py` `zx_selfcheck.py` `zx_cmp_shots.py` `zx_cdvd.py` `zx_diff_iso.py` `zx_logdiff.py` `zx_prefixchk.py` |
| 侦察/实验原始输出 | `r82/recon2.txt` `textcheck.txt` `migration.txt` `fontres.txt` `icon.txt` `diff_zh121.txt` |

**必须汇报的两处"受保护路径"改动（已先发消息说明）**
```
① tools/text_csv/tcslib.py
   L53/54  LEAD_HI 0xB1→0xB5 ; PAIR_LEAD_HI 0xB1→0xB5        （8 处调用全部由这两个常量参数化）
   L1369+  selfcheck_charset 的"图标占位往返"段: 对落在 lead 区间内的字节 (0xB1)
           改为断言"被正确拒绝"（gate 抬到 0xB5 后 0xB1 已不是图标码, 旧断言必然失败）
② tools/font_pipeline/data/charset_compiled_zh16.json
   pair_of 1504→1872（+368）; codes 110→107（删 0xB2/键、0xB3/练、0xB4/用）
   原文件备份 r82/charset_before_r82.json ; 一键还原: python work/tools/zx_charset.py --revert
```
⇒ 不改①的注入器**预检会 exit=3**（新 lead 被判死 pair）⇒ 构筑根本走不到注入；
不改②则新字无码位。两条都是必要项，不是顺手改动。

---

## 2. 做了什么（按任务书"已修正方案"逐条）

| # | 动作 | 状态 | 证据 |
|---|---|---|---|
| ① | 图集 1024×512→**1024×640 PSMT4**，`px_size 0x40010→0x501F0`，10 段自闭合 GIF 包 + 尾部 16 B no-op | ✅ 数据正确 | `[ct ] 新容器 10 段 = 10*48 + 10*0x8000 + 16 = 0x501F0 (= 328176)` |
| ② | **搬两条活带**：EN 带 `(452,468)`→`(594,610)`、键盘带 `(482,498)`→`(610,626)`，像素同步搬 | ✅ 数据正确 | `[band] … Δy=+142 ⇒ 墨 1879 texel` / `Δy=+128 ⇒ 墨 1799 texel`；`①b 窗口内容逐像素相等 ✓` |
| ③ | 格位 = 行24尾 46 + 行25/26/27 各 62 + 行28/29/30 → 实际用 **368 格**（slot 1504..1871）| ✅ | `[draw] 368 格已画: slot 1504..1871 ; y 434..546` |
| ④ | COMMON.PAK 原地长大 +66,016 + MENU.IMG 平移 + ISO9660 目录记录；**ISO 尺寸不变** | ✅ | `COMMON.PAK 400659 → 466675 (Δ = +66016)`；`声明 … ⇒ 58331136 (28,482 扇区)`；`尺寸不变 1648164864 B` |
| ⑤ | ELF 4 处 gate `sltiu …,0xB1`→`…,0xB5`（0x416EE8/0x417160/0x41751C/0x5656A4）| ✅ | 站点逐字节实测命中（`recon2.txt` §6），补丁按低字节替换 |
| ⑥ | 「嘚」U+561A 用 `C:\Windows\Fonts\simhei.ttf` 按现役配方渲 | ✅ | `[glyph] 364 个缺字字形就绪 (方正 363 + simhei 兜底 1 ['嘚'])` |
| ⑦ | 迁移字 △/键/练/用 进新 slot | ✅ | 键/练/用 从旧图集 rec[146/147/148] 采样窗**原样抠**（墨 93/74/59）；△ 见 §7-3 |
| ⑧ | charset 同步 + 丰富版文本注入 | ✅ | `pair_of 1504→1872 ; codes 110→107`；`已按 CSV 修改 316 条正文` |

**FONT.RES 改法是本轮的一个关键实验结论（否掉了任务书里"原位字节替换"的隐含期望）**
```
· 逐字节来源追踪 (zx_fontres.py): 1328 个待改字节里只有 **7 个**是 LZO 字面量, 其余全走匹配拷贝,
  且共享字面量会连带改坏非目标字段 ⇒ "只改 7 个字节"实测让 10 个非目标字节也变了 ⇒ 该路否掉 ✗
· 改用"重压 LZO 子流": 槽 4421 B = [12 B 头 {1489,5942,5162}][帧 {1461,5942}][**尾部 2924 B 全 0**]
  重压后帧 1469 B ≤ 4421 ⇒ **stored 4421 不变、展开 5942 不变、记录数 224/224/96 不变**,
  差异 1328 字节 == 目标集合 ✓ ⇒ 位移仍恰好 +66,016 ✓（不触发 Lead 警告的"裸 round-trip 毁盘"）
```

---

## 3. 六条硬断言（逐条原文 + 数字）

写盘后**从盘上回读**再验（`zx_patch_font.py` 断言段，日志 `r82/patch_font_full.log`）：

| # | 断言 | 结果 | 关键数字 |
|---|---|---|---|
| ① | 行 0..511 里现役 1504 个 pair 格 + 单字节/EN/第二条带被引用的矩形 **逐字节不变** | ✅ | `1504 个 pair 格逐字节不变`；`FT 记录矩形 212 条逐字节不变`（两条活带 332 条按设计搬走）；补一条更强判据 `①c 行 0..511 的计划外像素改动 = 0`（改动 22,822 px **全部**落在 368 个目标格内）|
| ② | 新字墨点全部落在目标格内（格外墨点改动 = 0） | ✅ | `格外改动 = 0`；`新行区杂散墨 = 0`；`新行区墨 9871 texel`；`②b 368 个格回读 == 16px 字形模板 (逐像素)` |
| ③ | 字节级：实际变动 ⊆ (新行 512..639) ∪ (行 24..30 目标格) ∪ (两条带新旧位置) | ✅ | `新容器 328176 B（旧 262160，Δ=+66016）`；`①c` 的像素级包含关系 + `①b` 带内容等价 |
| ④ | 段表回读 == 目标（逐 texel） | ✅ | `④ 段表回读 == 目标 (逐 texel, 1024 x 640) ✓`（从 dst ISO 重新解封包）|
| ⑤ | FONT.RES 记录数 / 展开长度 5942 不变 | ✅ **且更强** | `stored 4421 不变、展开 5942 B 不变、记录数 [('large',224),('default',224),('huge',96)] 不变、差异 1328 字节 == 目标集合` |
| ⑥ | MENU.IMG：只动 u32[+0x00] 与 #4 起的 off；名字区/哈希表 0 字节差异 | ✅ | `元数据区 [0,0x57400) 计划外字节改动 0`；`名字区 11542 B / 4096 槽表 16,384 B 逐字节不变`；`每条 u32[0]/u32[1] 不变`；改动字节 2052 = 头 4 + 682 条 off + 1 条 stored |

**P3 离线判据（成品盘自身）**
```
tools/text_csv/inject_text_csv.py --csv work/builds/GR_ZH121/text_in --src GR_ZH121.iso --check-only
   ⇒ exit 0 ; [ok] 字库覆盖完全: 每条文本的每个字符都能编码, 且盘上都有字形 ✓   (待检查 2250 条)
tools/iso_build/dump_font.py --iso GR_ZH121.iso
   ⇒ 1024×640 psm=0x14, 墨 140597/655360 ; 字符 2075 个 — **有字形 2075 / 缺字形 0** ✓
   ⇒ 自查: 引擎格位公式 OK (1880/1880 slot 逐个对 tcslib 口径) ; 对偶字有字形 1872/1872 ✓
tools/iso_build/audit_inventory.py GR_ZH121.iso
   ⇒ 在役 44 条, 缺失(仍为 EN 词) 0 条 ✓
work/tools/zx_selfcheck.py --iso GR_ZH121.iso
   ⇒ selfcheck_charset 36 条全 [ok] ; 全量文本问题只剩 616 条 ascii_no_glyph（**只告警不阻断**, 现役盘同样）
     —— 基线盘同口径是 861 条 no_glyph, **新盘 0 条** ✓
```

---

## 4. 与原盘的逐字节差异（`r82/diff_zh121.txt`，工具 `zx_diff_iso.py`）

```
A = GR_ZH113b.iso (1,648,164,864 B)    B = GR_ZH121.iso (1,648,164,864 B)   ← **尺寸完全相同**
★ 差异区段 10 个, 合计 57,798,656 B (3.507%) ; 其中 MENU.IMG 区内 57,749,504 B ; ELF 4 站点 4/4 命中

  0x000082000..0x000083000     4,096 B   ISO9660 MENU.IMG;1 目录记录 data length (LE @0x828D8 / BE @0x828DC)
  0x0003AA000..0x0003AB000     4,096 B   ELF gate 0x416EE8 区段
  0x0004F8000..0x0004F9000     4,096 B   ELF gate 0x5656A4 区段
  0x00F034000..0x00F03D000    36,864 B   GR.IMG 内 EN_STRINGS.RES 重压帧（文本注入）
  0x05EC2F000..0x05EC38000    36,864 B   [MENU.IMG +0x0]        头部 u32[0] + 条目表 683 处字段
  0x05EC87000..0x05EC88000     4,096 B   [MENU.IMG +0x58000]    COMMON.PAK 记录 h/px_size + 容器
  0x05ECBD000..0x0623BB000 57,663,488 B  [MENU.IMG +0x8E000]    ★ 尾部整体后移 66,016 B（682 条目数据）
  0x0623BD000..0x0623C6000    36,864 B   [MENU.IMG +0x378E000]  EN_STRINGS.RES 重压帧（文本注入）
  0x0623C9000..0x0623CA000     4,096 B   [MENU.IMG +0x379A000]  EN_SPECIAL_FEATURE.XML 重压帧
  0x0623CF000..0x0623D0000     4,096 B   [MENU.IMG +0x37A0000]  （同上, 跨区段）
ISO 总尺寸、PVD vol_space、LBA、名字区、4096 槽哈希表 —— **零改动** ✓
```

---

## 5. ★ 实机：P1 失败 + 归因实验（本轮最重要的负面结论）

**跑法**：裸跑（任务书指定的写法，`exit=0` 是假信号，必须看截图/needle）
```
third_party\emu\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe -grdumpdir <d> -grmaxframes 6000 \
   -grsnap 30 -grinput tools\capture\nav_menu_only.txt -logfile <d>\emulog.txt -- <iso>
```

### 5.1 结果表
| 盘 | 截图 | `GIF upload` | needle `newfontrevisedrs` | needle `weaponsanditems` | 判定 |
|---|---|---|---|---|---|
| `GR_ZH113b`（基线）| **191** | 2 | **2873** | 2636 | ✓ |
| `GR_ZH113b` 第二次跑 | **191** | — | — | — | ✓ **与第一次逐字节相同 191/191**（模拟器可复现）|
| `GR_TEST_FONTCAP_GROW`（只长大+平移）| **191** | 2 | **2872** | 2636 | ✓ **正常** |
| `GR_TEST_FONTCAP_H640`（+容器/px_size）| **0** | 0 | **0** | 0 | ✗ 黑屏 |
| `GR_TEST_FONTCAP_H640B`（+扇区对齐声明长度）| **0** | 0 | 0 | 0 | ✗ 黑屏 |
| `GR_TEST_FONTCAP_H1024`（+记录 h=1024）| **0** | 0 | 0 | 0 | ✗ 黑屏 |
| `GR_ZH121`（成品盘）| **0** | 0 | 0 | 0 | ✗ 黑屏 |

### 5.2 归因（单变量，逐个否证）
```
已被证伪的三条假设（每条都做了盘并实机跑）:
  ✗ "声明长度不扇区对齐 ⇒ 最后一个条目尾部读不到"
      → H640B（声明 58,331,136 = 28,482 扇区, 与 round31 实机验证过的探针 A/B 同值）**仍然黑屏**
  ✗ "引擎按 h 分配纹理行数, h=640 只分到 512 行 ⇒ 多出的段写坏显存"
      → H1024（记录 h=1024, 容器仍 640 行/px_size 0x501F0）**仍然黑屏**
  ✗ "MENU 682 条 off 整体平移把某个结构搞坏了"
      → GROW 盘（PAK 长大 + 682 条平移 + 扇区对齐声明长度, **图集一字不动**）**正常启动**,
        191 张截图, needle 2872/2636 与基线同档
⇒ 唯一剩下的变量 = **像素容器本身变大**（px_size 0x40010 → 0x501F0 / 10 段 0x8000 自闭合包）
现象特征: 不是"画面错"而是**根本没走到 UI** —— 纹理一次都没上传、字体名一次都没进内存
         (needle 0 命中) ⇒ 更像加载期失败/越界, 而不是采样期错误。
```
**给下一轮的第一手线索（我没能验证）**：`LoadingTexturePak` 的记账式
`iVar4 = w*(0x10000/w)*4 + 0x10 = 0x40010`；`+0x30 = px_size + ceil(px_size/iVar4)*(-0x10)`
⇒ 基线 `ceil(0x40010/0x40010) = 1` 块，本方案 `ceil(0x501F0/0x40010) = **2**` 块。
**建议的单变量下一步**：造 `px_size = 0x40011`（只比现役大 1 字节、仍是 1 块）的盘跑一次 ——
若它也黑屏 ⇒ 引擎对 `px_size` 有硬上限（= 0x40010）；若正常 ⇒ 是"**块数/块读法**"的问题，
应去反编译 `LoadingTexturePak` 的读循环（而不是继续调图集数据）。

### 5.3 并行冲突（如实记录，我没有抢/没有杀）
12:58 有另一个任务的 `nav_hook.py GR_TEST_FONTCAP_H640 --tag p1nav` 跑在我那版**坏盘**上
（python pid 14456 / emu pid 43012），262 s 后报 **"主菜单钩子不响应 / 0 张截图"** ——
与本文 §5.1 的独立复现一致，可直接引用为失败证据。我把现象+修法写在
`r82/LEAD_ZX_P1_FAIL_AND_FIX.md` 留给它，全程未干扰；我自己的实验在它之后排队执行。

---

## 6. 剩余未做项与原因（如实）

| 项 | 状态 | 原因 |
|---|---|---|
| **P2（新字上屏与旧字同屏对照）** | ⛔ 未做 | 前提是"盘能启动到 UI"；当前所有含新容器的盘都在 UI 之前黑屏，**没有可对照的画面**。判据（△ 画成三角 / 块数不翻倍 / 对照行正常）已写好，等容器问题解决即可直接跑 |
| **P1 的"画面逐像素一致"判据** | ⚠ 只拿到间接证据 | 6000 帧的航程只到**片头影片**（截图 f5700 是动画），主菜单/记忆卡屏/名字页没进入。基线两跑 191/191 一致 ⇒ 模拟器可复现；GROW 盘 191 张、107 张逐字节相同、84 张不同（片头影片相位差，`newfontrevisedrs` 2872 vs 2873）|
| **`cdvd.log` 的 261,760→327,680 判据** | ⛔ 未取到 | 该数字是"容器段数据字节数"，引擎在**黑屏盘上根本没读到那一步**；基线侧读数已备好工具（`zx_cdvd.py`），但黑屏盘读数恒为 0，无意义 |
| **GR.IMG 侧同步** | 未做（按任务书"不要动"）| 任务书明确不动；且 MENU 侧尚未跑通，先不扩散 |
| **△ 的"引擎图标观感"** | 部分 | 见 §7-3 |

---

## 7. 已知限制

1. **成品盘当前不可实机使用**（§5）：数据/文本层面已"零缺字"，但引擎在加载变大的像素容器时失败。
   **不要把 `GR_ZH121.iso` 当成可用成品盘发布。**
2. **`px_size` 上限未定**：只证明"0x501F0 不行"，没证明"上限就是 0x40010"（§5.2 给了 1 次实验就能定）。
3. **△ 的字形是手绘三角**：引擎的 △/✕ 图标来自 `pda_counterparts`（20×20 彩色、硬编码 UV
   (25,198)-(45,218)），而图集里 `0xB1`/`0xB5` 的记录矩形 (480,213,490,229) 实测**采样窗全透明**
   ⇒ 无法从图集抠；20×20 彩色 → 16×16 1-bit 的转换被我判定为"不如直接画一个干净的三角"。
   新槽里是 **16×16 空心三角（墨 39）**，`selfcheck` 通过；**观感未经实机验证**。
4. **迁移字宽度变化**：键/练/用 原本走单字节记录（记录宽 16）⇒ 迁到对偶码后仍 16 px ✓ 宽度不变；
   **△ 原本 20 px（记录 b1=10 的图标宽），迁后 16 px**，含 △ 的行会窄 4 px（未实机验证）。
5. **`real` 字段保持原值**：COMMON.PAK 的 `stored` 400,659→466,675，`real` 保持 400,659（与 round31
   实机验证过的探针 B 同做法）；GROW 盘实机正常 ⇒ 这条已间接验证 ✓。
6. **`0xB1` 图标码在新 gate 下失效**：文字里的 `{{BTN:E0B1}}` 会被注入器**拒绝**
   （tcslib 的 `btn_code_ok` 按新 lead 区间正确报错）⇒ 本方案把 7 处 `{{BTN:E0B1}}` 换成字符 `△`
   （映射到对偶码 0xB1 0xA1 = slot 1504）。**✕（0xB5）不受影响**（gate=0xB5 时它不是 lead）✓。
7. **仓库 charset 现在处于"1872 对偶"状态**（与 GR_ZH121 一致）。若并行任务用旧盘构筑，
   注入器**会以 exit=3 明确失败**（新码位在那张盘上无字形），不会静默出错；
   要回到基线：`python work/tools/zx_charset.py --revert`。
8. **h=640 本身没问题**（Lead 的 P1′ 实机 PASS + 本文 GROW 盘），**问题只在容器/px_size**。

---

## 8. 复现命令（全部可重跑）

```powershell
# 只读侦察
python work\tools\zx_recon.py            # 条目/容器/FONT.RES/ELF 站点  → r82/recon2.txt
python work\tools\zx_textcheck.py        # 丰富版 vs 缩减版 + 364/386/25 → r82/textcheck.txt
python work\tools\zx_migration.py        # 迁移清单与各 gate 档位的账  → r82/migration.txt
python work\tools\zx_fontres.py          # FONT.RES 结构 + 两条改法的可行性 → r82/fontres.txt
python work\tools\zx_icon.py             # △/✕ 图标来源诊断            → r82/icon.txt
python work\tools\zx_prefixchk.py        # 段前缀逐字节差异（模板法自证）

# 补丁（dry-run 会把六条断言全跑一遍，不写盘）
python work\tools\zx_patch_font.py work\builds\GR_ZH113b\GR_ZH113b.iso --dry-run
python work\tools\zx_patch_font.py work\builds\GR_ZH113b\GR_ZH113b.iso --dry-run --p1

# 成品盘（目录必须不存在）
python tools\iso_build\make_build.py GR_ZH121 --from work\builds\GR_ZH113b `
       --patch work\tools\zx_patch_full.py --no-font-compact --no-textdump `
       --no-text-snapshot --no-font-dump --inject-csv work\builds\GR_ZH121\text_in

# P3 离线判据
python tools\text_csv\inject_text_csv.py --csv work\builds\GR_ZH121\text_in `
       --src work\builds\GR_ZH121\GR_ZH121.iso --check-only
python tools\iso_build\dump_font.py --iso work\builds\GR_ZH121\GR_ZH121.iso --out <dir>
python tools\iso_build\audit_inventory.py work\builds\GR_ZH121\GR_ZH121.iso
python work\tools\zx_selfcheck.py --iso work\builds\GR_ZH121\GR_ZH121.iso

# 实机（先确认没有别人的实例！绝不抢/杀）
third_party\emu\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe -grdumpdir <d> -grmaxframes 6000 `
   -grsnap 30 -grinput tools\capture\nav_menu_only.txt -logfile <d>\emulog.txt -- <iso>
python work\tools\zx_cmp_shots.py <dumpA> <dumpB> [--region <abs_off> <len>]

# 探针盘（隔离实验）
$env:ZX_PROBE='--growonly'   # 或 --h1024
python tools\iso_build\make_build.py GR_TEST_FONTCAP_GROW --from work\builds\GR_ZH113b `
       --patch work\tools\zx_patch_probe.py --no-font-compact --no-textdump `
       --no-text-snapshot --no-font-dump
```

---

## 9. 给下一轮的三个具体动作（按性价比排序）

1. **`px_size = 0x40011` 单变量盘**（10 分钟）：定"是硬上限还是块数问题"（§5.2）。
2. 若确认是**块数/块读法**：反编译 `LoadingTexturePak` 的读循环（VA `0x51B660` 一带，
   现成反编译 `work/builds/GR_ZH98/temp/r73/deep_part.txt` L53–L133），确认 `+0x30` 与
   `ceil(px_size/iVar4)` 的用法；必要时把容器做成"**2 个块、每块自带 16 B 头**"的形态
   （`+0x30` 的公式恰好假设这种布局）。
3. 若确认是**硬上限**：改用"不加高图集"的容量路线（Lead `LEAD_FINDING_gate_cost.md` 的 0xC0 档 +
   搬带后行 25/26/27 的 232 格 = 上限 1736 槽），只能容纳 **+232** 个新字 ⇒ 需要用户把 364 个缺字
   缩到 ≤232（或接受分两批：先做 232 个高频字）。**这条我建议在动手前先跟用户确认口径。**
