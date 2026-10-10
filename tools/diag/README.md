# tools/diag/ — 诊断工具组 (2026-10-04 建, GR_ZH73/ZH76 两轮沉淀, 入库)

本组工具 = 人名缩写轮 + 人名纵向归位轮中现做的取证工具, 全部**相对仓库根推导路径 / 参数化路径**,
不写死版本 (此前 `work/builds/GR_ZH72/temp/dis4t.py` 一类固定路径脚本在换盘后即失效)。
解释器一律 `C:\ProgramData\anaconda3\python.exe` (numpy / opencv-python / Pillow)。

| 工具 | 用法 | 用途 |
|---|---|---|
| `an_draw.py` | `python tools/diag/an_draw.py <drawlog.txt> text\|grep\|susp\|keys [参数]` | gsrunner `-grdrawwin` drawlog 解码: 把 `PC/RA/x/y + 串体` 还原成可读中文; `grep` 按文本过滤; `susp` 列出可疑串 (孤 lead / 毒字节); `keys` 列绘制站点分布。`--pc 219EB0,219A70 --ra XXXX --f0 A --f1 B --limit N` |
| `draw_sites.py` | `python tools/diag/draw_sites.py <drawlog> <PC前缀> <RA前缀> [f0 f1]` | 按前缀枚举绘制站点: (RA, x, y, 文本) ×次数 + 首现帧 —— 定位"这条字是谁画的/画了几次/坐标多少" |
| `res_text_dump.py` | `python tools/diag/res_text_dump.py menu\|gr [通配] [--iso <iso>] [--raw]` | 从现役 ISO 直接解码 `EN_STRINGS.RES` 全量文本 (含 key `G##.I###`), 用于核对译文/定位文案; 默认 ISO = `work/builds/GR_ZH72/GR_ZH72.iso` (用 `--iso` 指新版) |
| `dis_ee.py` | `python tools/diag/dis_ee.py <ELF> <hexVA> [字节数]` | PS2 EE (R5900) 反汇编, 带符号名解析 (整数/MMI 指令; 浮点见 cop1.py) |
| `cop1.py` | `python tools/diag/cop1.py <ELF> <hexVA> <字节数>` | COP1 (浮点) 指令解码: `add.s/mov.s/mtc1/cvt.s.w/c.ole` 等 —— **读 Y/X 常数链必用** (ZH74/ZH76 两轮的教训: 整数反汇编看不懂 f13/f21 在哪被改) |
| `xref.py` | `python tools/diag/xref.py <hexVA> [...] [--elf <ELF>]` | ELF 内 `jal/j` 调用点扫描 (钉死某函数的所有入口) |
| `syms.py` | `python tools/diag/syms.py <正则> [--size] [--elf <ELF>]` | ELF 符号表检索 (含 size), 用于按 C++ 名字找函数 + 求函数边界 (cave RA 过滤用) |
| `ink_rows.py` | `python tools/diag/ink_rows.py <png> <x0> <y0> <x1> <y1> [thr] [--dark]` | 逐行墨迹统计: 墨带范围 + 墨量加权质心; `--dark` = 深字浅底 (高亮黄框)。**纵向对位标定/验收的标准尺** |
| `row_prof.py` | `python tools/diag/row_prof.py <pngA> <pngB> <x0> <y0> <x1> <y1> [thr] [--dark]` | 两图同区逐行墨量对照打印 —— 直接看同一串文本移动了几行 (验证 Y 补丁实际生效量) |
| `diff_rows.py` | `python tools/diag/diff_rows.py <pngA> <pngB> <x0> <y0> <x1> <y1>` | 两图同帧逐行差异像素统计 —— 回归验收: 差异必须只落在预期行 |
| `shift_est.py` | `python tools/diag/shift_est.py <pngA> <pngB> <x0> <y0> <x1> <y1>` | 相位相关亚像素位移估计 (**仅同文本两盘对比有效**, 异文本会给出低置信假值 —— ZH76 轮实测) |
| `cmp_img.py` | `python tools/diag/cmp_img.py <out.png> <x0> <y0> <x1> <y1> <scale> <标签>:<png> [...]` | 多盘同帧对照图 (竖排 + 标签), 坐标用原生 640×448; **每轮修复后的"EN 原盘 vs 修复盘"对比图就用它** |
| `crop_img.py` | `python tools/diag/crop_img.py <in.png> <out.png> <x0> <y0> <x1> <y1> [scale]` | 单图裁剪放大 (原生坐标), 用于细节取证 |
| `atr_scan.py` | `python tools/diag/atr_scan.py <iso> [名字通配]` | 盘点 GR.IMG 全部 .ATR 的 `ActorName`/`ClassName`/尺寸 (自动 LZO 解压), 用于**批量文本替换前统计待改集合** (ZH77 轮: 1193 个 ATR / 265 个唯一名) |
| `frame_cmp.py` | `python tools/diag/frame_cmp.py <pngA> <pngB> [阈值]` | 两图**无阈值**通道差 + 差异行带 (含 BGR 均值 Δ) —— 专抓**变色/亮度**类回归 (形状差用 diff_rows) |
| `snapdiff_all.py` | `python tools/diag/snapdiff_all.py <dirA> <dirB> [阈值]` | **整轮**快照逐帧比对 (数百帧一次跑完) —— 零回归验收的标准做法 (ZH77: 199/199 帧逐像素一致) |
| `name_table_png.py` | `python tools/diag/name_table_png.py <out.png> [行数]` | 从 EN/汉化两盘直扫 ATR 人名并渲染"英文→中文"对照表图片 (纯数据轮的交付图) |

**Y/X 常数标定流程 (ZH76 轮沉淀, 适用于一切"文字位置"类修复)**:
1. `ink_rows.py` 量化 EN 原盘 vs 现役盘的墨带/质心差 (Δ 目标);
2. 用两个不同 K 值各出一枚**标定盘**实测位移 (`row_prof.py` 读行带), 得"K→像素"斜率
   (实测增益 ≈0.86, **K 与像素不是 1:1**, 不能按想要的像素直接写常数);
3. 线性内插出目标 K, 重建正式盘; 4. `diff_rows.py` 验收 (差异只落在目标行)。

ELF 抽取 (符号表在文件 0x61CF80, **必须整段 37,453,732B**, 截短到段长会让 syms/xref 崩):

```
python -c "f=open(r'work/builds/GR_ZH76/GR_ZH76.iso','rb');f.seek(295*2048);open(r'work/builds/GR_ZH76/temp/SLUS_206.13.zh76','wb').write(f.read(37453732))"
```

约定: 取证产物落 `work/builds/<被测版本>/temp/` (对照图建议 `temp/cmp/`), **不入库**;
实例见 `work/builds/GR_ZH73/temp/cmp/`、`work/builds/GR_ZH76/temp/cmp/`。
