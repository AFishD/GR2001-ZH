# tools/final_fix —— 唯一正式构筑脚本

本目录 = 整个汉化工程**唯一的**构筑链。两个入口，别的都是它们调用的阶段脚本。

```
python tools\final_fix\build.py      # 从英文原盘重建正式版（16 阶段）
python tools\final_fix\verify.py     # 28 条硬断言自证
```

完整用法见 [`docs/BUILD_GUIDE.md`](../../docs/BUILD_GUIDE.md)，
修改做法见 [`docs/MOD_GUIDE.md`](../../docs/MOD_GUIDE.md)。

---

## 文件

| 文件 | 作用 |
|---|---|
| **`build.py`** | ★ 唯一构筑入口。按 `fix_spec.json` 跑 16 个阶段，逐步核对 sha256 |
| **`verify.py`** | ★ 唯一校验入口。28 条硬断言 + FF 闸门（`--ff-gate` 单独跑） |
| **`fix_spec.json`** | ★ **单一真源**：输入指纹 / 16 个阶段（工具+参数+期望 sha256）/ 闸门 |
| `elf_patches.json` | ELF 补丁逐字节表（`apply_fix.py` 的输入）：F4 / F7 / F7b / OOMFIX |
| `assets/charset/` | 字符集：2300 对偶 + 103 单字节码，含 `.before_zh130` / `.before_zh139` 快照 |
| `assets/text/` | 文本表：`enrich/`（富文本 43 条）+ `merge/`（合并层 4 张 CSV） |
| `assets/mis/` | `map.tsv`：40 个 `*.MIS` 的目标任务名 |

## 16 个阶段

| # | id | 脚本 | 一句话 |
|---|---|---|---|
| 1 | `base` | `rebuild_base.py` | 英文原盘 ⊕ K2 cdvd 转储 ⇒ 2400 产品线基底 |
| 2 | `elf` | `apply_fix.py` | 卡死修复四件套（239 B / 70 段） |
| 3 | `glyph_edge` | `patch_zh130_glyph_edge.py` | 字库右缘采样修正（36 对偶换位 + `X` 三 face） |
| 4 | `stale` | `patch_zh133_stale_hashr.py` | 旧码残留追赶 |
| 5 | `text2` | `patch_zh134_textfix2.py` | 文本层修正 #2 |
| 6 | `profile` | `patch_profile2_text.py` | `著`=`0xFF` 被 XML 词法器当 EOF 的修复 |
| 7 | `gate_ff` | `verify.py --ff-gate` | 闸门：文本区出现 `0xFF` 即 FAIL |
| 8 | `glyphs61` | `patch_zh138_glyphs61.py` | 61 个「有码无字」补画 |
| 9 | `chars139` | `patch_zh139_chars.py` | +13 个实证生字 ⇒ PUA 槽 |
| 10 | `chars140` | `patch_zh140_chars.py` | +9 个富文本生字 |
| 11 | `enrich` | `inject_text_csv.py` | 富文本表注入 |
| 12 | `chars141` | `patch_zh141_chars.py` | +3 个真字形 `…` `×` `惧` |
| 13 | `merge_text` | `inject_text_csv.py` | 合并文本层（正文/空行/标题/LANG） |
| 14 | `ike142` | `patch_zh142_ike.py` | 折行 270→286 + 面板 290→306 |
| 15 | `ike143` | `patch_zh143_ike.py` | 折行 286→294（面板不动） |
| 16 | `misnames40` | `patch_misnames40.py` | **40/40** 个任务名（可变长度 + 零填充 + LZO 令牌重指） |

阶段 1–15 是"底盘"，16 是"最后一层内容"。`build.py` 用引用计数决定中间盘何时可删。

## 共用库在哪

字体/图集/容器实现在 `tools/lib/`（`dump_font` / `repack_font` / `font_compact` /
`glyph_geometry` / `iso_tools` / `zx_lib` / `lz77_decode` / `lzo1x_c` / `icon_table`），
文本表工具在 `tools/text_csv/`。`build.py` 把它们都塞进子进程 `PYTHONPATH`。

## 保留的两个诊断

| 文件 | 用途 |
|---|---|
| `cave_verify_f7b.py` | ELF cave 选址证明（C1–C7：全零 / 快照未变 / 无指针字 / 无跳转目标 …） |
| `elf_crc.py` | 单独算一张盘的 PCSX2 Game CRC（判"旧存档还能不能用"） |

其余一次性脚本（`repro*.ps1` 14 个、`fontfix_*.py` 10 个、`make_*_meta.py` 4 个 …）
本轮已删除，内容在 git 历史里。

## 三条不容商量的规矩

1. **基底只能是英文原盘**（+ K2 转储）。禁止拿历史成品盘当基底。
2. **能用数据解决的绝不改 ELF** —— Game CRC 一变，玩家旧存档全废。
3. **文本区不得出现 `0xFF`** —— 引擎的 XML 词法器把它当 EOF（第 7 步闸门会拦）。
