# hanliu/docs/TOOLS.md — 各工具详细用法

约定：`PY = <anaconda3>\python.exe`（带 numpy/PIL）；工具目录 =
`hanliu\tools\`；以下命令均在 tools 目录下执行（或用绝对路径）。
所有工具自检：库模块 `PY -c "import xxx"`；顶层执行脚本 `PY -m py_compile xxx.py`。
**凡 docstring 标注"顶层执行"的收编脚本，import 即执行，勿盲目 import。**

---

## 1. 格式层（IMG 档案 / LZO1X / RES）

### gr_lz.py — IMG 档案解析 + 纯字面量安全编码
```python
import gr_lz
data, ents = gr_lz.load_entries(path)      # 档案条目表（离线，只读表头+表）
files, fails = gr_lz.extract_all(path)     # 全量解包（内存型，小档案适用）
gr_lz.encode_literals(payload)             # 纯字面量安全编码（每段 run+17，恒 ≥0x11，
                                           # 绝不发出 c≤0x10 控制令牌 —— 引擎挂死红线）
gr_lz.frame_substream(payload, out_size)   # {u32 plen}{u32 osz}{payload} 框架
```
注意：`decompress_stream` 是历史计数格式解码器（已被证明是误读），仅存档；
正确解码一律用 `lz77_decode.decode_entry`。

### lz77_decode.py — 标准 LZO1X 解码器（全项目解码基准）
```bat
PY lz77_decode.py <stored文件> <输出文件> [--info]
```
```python
from lz77_decode import decode_entry, lzo1x_decompress, iter_substreams
out, stats = decode_entry(stored_bytes)      # 全部子流，sum(osz)==real 校验
back, err, ip = lzo1x_decompress(payload, out_size=n)   # 单子流
```
实绩：MENU/GR 两档案 5 语言 RES + 307 个 BMZ + ATR/MIS 全量零失败。

### lzo1x_c.py — minilzo 兼容压缩器（写回用）
```bat
PY lzo1x_c.py selftest
PY lzo1x_c.py compress <in> <out> [--frame] [--m1] [--level N]
PY lzo1x_c.py bench <expanded.bin> [orig_stored.bin]
```
RES 8 子流写回的标准参数（ZH7 实测）：`compress(chunk, level=7, use_m1=True, use_m4=True)`。

### res_encode.py — *_STRINGS.RES 解析/重编码
```bat
PY res_encode.py parse  <in.res> <out.txt>       # 存储/展开态 → 文本同构
PY res_encode.py build  <in.txt> <out.res> [--framed-lzo out.framed]
PY res_encode.py round  <in.res>                 # parse→build 逐字节比对（自检）
PY res_encode.py mod <in.res> <out.res> 5 4 A C6 # 最小单字节改动
PY res_encode.py probe <in.res>                  # 结构摘要
```
文本同构格式：`[G01] sep=0` 组头 + `I000=...` 条目（转义 `\\ \n \r \t \xNN`）。

### img_patch.py — IMG 安全补丁（空隙法 + 原地 + 追加）
```bat
PY img_patch.py <in.img> <out.img> EN_STRINGS.TXT=<new.bin> [FONT.RES=<slot.bin>] [--framed] [--no-inplace]
```
适用于 TXT/XML/未压缩文件。**两类例外**（工具内部有对应处理，见 zh7_pipeline）：
- FONT.RES 槽位态（帧被 0x00 填充到 4421）：`--framed` 识别不了，须用
  `zh7_pipeline.py` 第 4 步的原位写（real 字段保持 7,222）。
- EN_STRINGS.RES 的 8 子流 blob：走原位覆写（stored=47,570 不变，内容 ≤ 槽即可）。

### img_tool.py / iso_tool.py / splice_iso.py
```bat
PY img_tool.py list <img>                        :: 列条目（tag RAW/LZ77, stored/real/off）
PY img_tool.py extract <img> <outdir>            :: 全量解包（MENU 58MB 可行; GR.IMG 勿用）
PY img_tool.py replace <img> <out.img> NAME=f …  :: 重建式替换（重排偏移! 补丁勿用）
PY iso_tool.py list|extract|build …              :: ISO9660 例行操作
PY splice_iso.py <原盘iso> <menu.img> <输出iso> [776286]   :: 仅换 MENU 的原位拼接
```
⚠ `img_tool.py replace/rebuild` 会重排数据区偏移——引擎依赖原偏移，**汉化补丁用
img_patch.py 或管线原位写，勿用 replace**。

## 2. 字体层（FONT.RES + COMMON.PAK）

### font_build.py — 字库生成器（新整合件）
```bat
PY font_build.py --charset 字表.csv --mode dbcs ^
   --base-ft  <FONT.RES 展开态 7222B（如 zh6\ft_expanded_zh6.bin）> ^
   --base-pak <COMMON.PAK 400,659B（如 han_v2\COMMON_PAK_ZH6.bin）> ^
   --ttf D:\Document\Fonts\SimHei.ttf --size 16 --out-dir out\
```
- 字表 CSV：`char,strategy[,code]`；strategy ∈ `single`（单字节码位，code 可省略自动
  分配）/ `pair`（DBCS 对，idx=224+k 顺序分配）/ `marker`（lead 标记字，码位限
  A1/A2/A3）。
- 输出：`COMMON_PAK_NEW.bin`（仅表面 0x1069 起像素差异）、`FONT_RES_expanded.bin`、
  `FONT_RES_slot.bin`（4,421B 槽位态）、`charset_compiled.json`（text_replace 输入）、
  `layout.txt`（逐格布局）。
- 自检（全部 ELF 无关）：parse_faces 回环、展开 ≤7,222B、DP payload ≤4,413B、
  槽 decode 回环、PAK 差异白名单、u0≥1、格互不重叠。
- `--mode single`：ZH3/ZH5 保守路线，FONT.RES 零改动，仅重绘既有格像素（≤89 字）。

### font_res_parse.py / font_res_probe.py / font_res_scan.py（探针）
顶层执行脚本，顶部改路径后直接跑；分别用于 face 结构解析、atlas 矩形叠加渲染、
记录边界扫描。排查"字形错位/缺失"时用。

### ft_dpc.py — LZO1X DP 最优压缩器（FONT.RES 专用）
```python
from ft_dpc import dp_compress
payload = dp_compress(expanded7222)     # 全局最优, ZH7 实测 4,232B ≤ 4,413B
```
FONT.RES 写回**必须**用它（lzo1x_c 贪心版压不进 4,413B 限额）。

### zh7_build.py — ZH7 一体构建（参照实现，原件逐字收编）
顶层执行；路径硬编码为 ZH7 原始输入。学习/比对用；生产用 `build\example_zh7\zh7_pipeline.py`。

## 3. ELF 层（SLUS_206.13 DBCS 补丁）

| 脚本 | 产物 | 说明 |
|---|---|---|
| `patch_db1_elf.py` | SLUS_db1.elf | Stage1 synth-byte，151B，实机 PASS |
| `patch_db2_elf.py` / `patch_db2b_elf.py` | SLUS_db2(b).elf | Stage2 v1/v2 存档（v1 boot 毒） |
| `patch_db2c.py` | （参数化） | Stage2 二分版 + MIPS Asm 套件（`build_PS_v5` 运行时读取其文本） |
| `build_PS.py` | SLUS_P_S.elf | Stage2 v3（最小 ABI，二分矩阵全绿） |
| `build_PS_v4.py` | SLUS_P_T.elf | v3 + 槽位 lh→lhu（GR_DB7 实证对渲染） |
| `build_PS_v5.py` | SLUS_P_U.elf | **终版**：lead 标记制（仅 A1-A3 成对），ZH7 采用 |

全部顶层执行、读原件 ELF（`slus_out\SLUS_206.13`，只读）、写 SLUS_P_*.elf 到
dbcs 目录。关键改动面：cave=0x26BEA0..0x26C18F（748B 死区，四重引用扫描判死）；
DrawString v1 @0x219A70；槽位 lh→lhu @0x219BD4/0x219BE4/0x219CA0；入口
0x219BCC；cw 0x21AD18 / cctc 0x21ADE0 / sw 0x21AC74 三跳。
**勿向 0x26C190 方向扩展**（0x23198B8/C8 有 vtable 数据字）。

### 反汇编/取证
- `dis4.py`（slus_scan 版，ELF 路径在顶部）/ `dis4P.py`（dbcs 版，默认
  SLUS_P_S.elf）：PS2 EE 手写反汇编器（EE MULT、MMI、LQ/SQ、COP1，符号表注释）。
- `elf_info.py`：ELF 头/节表摘要。`dwarf_probe.py`：.debug 段 DWARF 探针。
- `font_parse.py`：FONT.RES wire format 逐字段解析（与 ReadResourceFile 对应）。
- `fres.py`：GR.IMG 内 FONT.RES 探针。

## 4. 组装 / 实测层

### make_iso.py — 成品 ISO 一键组装（新整合件）
```bat
PY make_iso.py --base-iso "…原盘.iso" --menu out\MENU_ZH7.img ^
   --elf gr_build\tmp\dbcs\SLUS_P_U.elf --out out\GR_ZH7.iso
```
原位替换 ELF@LBA295 + MENU@LBA776286；回读比对 + 尺寸断言；拒绝输出=基底路径。
不加 `--elf` = 只换 MENU（等价 splice_iso）。

### run_test.py — gsrunner 一键测试（新整合件）
```bat
PY run_test.py --iso C:\…\GR_ZH7.iso --dump C:\gr_build\dumps\t1 --frames 40000
PY run_test.py --iso <iso> --dump <dir> --preset quick     :: 4300 帧 boot 快判
PY run_test.py --iso <iso> --dump <dir> --input mynav.txt --dry-run
```
预置导航：`zh2nav`（34 键到 Controller 页，判读 `snap_f00033480.png`）/
`quick` / `bisect`（15,500 帧 Name Entry 字形探针）/ `boot`。
判据：ALIVE（跑满 + exit=0 + needle ≥ 阈值）/ CDVD_STALL（模拟器层偶发挂起，
重跑即可）/ CRASH。**ISO 参数必须反斜杠路径**；记忆卡固定 `memcards_db1`。
基线：GR_ZH7 = 40,000 帧 exit=0（667s），needle 4,229（原盘 4,245）。

### probe_iso.py / run_iso.py / probe_run3.py / run_bisect.py / verify_iso.py
上述新整合件的内核原件（顶层执行，路径/参数写死在文件头）。保留用于与
历史证据链对账。

## 5. 文本层

### export_texts.py — 全部原始文本导出（新整合件）
```bat
PY export_texts.py                     :: 输出到 ..\texts\（默认）
PY export_texts.py --skip-iso          :: 无原盘环境（gr_res 用缓存基准）
```
产出与基准条数自检见 `..\texts\README.md`。内部同时实现了 PC 版 STRINGS.RES
格式破译（{count}×{klen}{key}{flag}{n}×{len}{GBK}{u16 0}{u32 0}+尾 {u32 0}）。

### text_replace.py — 文本替换器（新整合件）
```bat
:: RES（主用法）：593 条译文 → 8 子流 blob
PY text_replace.py --mode res --charset charset_compiled.json --input trans.csv ^
   --base-res en_strings_zh_8sub_v3.bin --target menu --out new_blob.bin

:: GR.IMG 侧（超 47,619 槽时自动另出 .expanded，配 img_patch stored==real 重定位）
PY text_replace.py --mode res … --target gr --base-res <GR 展开态或 framed>

:: TXT（武器/物品名）
PY text_replace.py --mode txt --charset … --input txt.csv --base-txt EN_STRINGS.TXT ^
   --out EN_new                      → EN_new.txt + EN_new.framed.bin

:: ATR（默认仅 ASCII；中文自负实机验证责任）
PY text_replace.py --mode atr --charset … --input atr.csv --base-atr-dir atr\ --out-dir out\
```
CSV：`key,en,zh`（utf-8-sig）。key：`G58.I003` / TXT 键 / `文件.ATR:标签`。
en 列非空且漂移 → 默认警告，`--strict-en` 报错。编码三禁：字表外字符、
0x00、0x80-0x9F。

## 6. research/（普查与测算）

- `hanzi_demand\*`：字频/容量测算（bdict/tdict 双语料、levelb_entries 1188 条
  短标签池、report.md 结论：89 字=架构天花板、566 字=全覆盖需求）。
- `gr_res\step1-10*.py`：GR.IMG RES 全量普查（条目表/解码/分类/候选表）。
- `pcfont\*`：PC 版中文字库普查（SXM 拉丁字模、census）。
- `slus_scan\` 其余：PC 版 font.res 解析、十六进制工具等。

## 7. 自检清单（2026-09-13 实测）

- import 级（无副作用库模块，12 个）：`gr_lz lz77_decode lzo1x_c res_encode img_patch
  img_tool ft_dpc font_build text_replace make_iso run_test export_texts` — 全 PASS
- compile 级（顶层执行收编件 + research，50 个）：`iso_tool splice_iso font_res_scan
  zh7_probe_res patch_db1_elf patch_db2_elf patch_db2b_elf patch_db2c build_PS
  build_PS_v4 build_PS_v5 probe_iso run_iso probe_run3 run_bisect run_bisect_win
  verify_iso dis4 dis4P elf_info dwarf_probe font_parse fres zh7_build
  font_res_parse font_res_probe` + `tools\research\*.py`（22 个）+ `__init__.py` — 全 PASS
- 功能级：export_texts 6 CSV（2232/2232/2220/1193/46/2902）全对；
  example_zh7 dry-run 与 GR_ZH7 原版 MENU 逐字节一致；
  text_replace res/txt/atr 三模式冒烟全过（txt framed 2,714B ≤ 原 2,749 槽、回环 OK；
  atr 仅目标标签重写、其余逐字节不变）。
