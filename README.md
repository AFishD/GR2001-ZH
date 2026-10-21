# 《幽灵行动》PS2 汉化（SLUS-206.13）

一个**可复现**的 PS2 汉化工程：从英文原盘 + 只读转储出发，一条命令重建正式版，
并用 28 条硬断言自证。

```
正式版   work\builds\FINAL\GR_ZH146.iso
         sha256 98ed8579f1b536432eb3d25843c41986b8e27eaeb1fec1035f2a74c866c2ff9a
         1,648,164,864 B   Game CRC 653FBF69
```

## 我该看哪一篇

| 我想…… | 看 |
|---|---|
| **把盘做出来** | [`docs/BUILD_GUIDE.md`](docs/BUILD_GUIDE.md) |
| **改文本 / 字库 / 任务名** | [`docs/MOD_GUIDE.md`](docs/MOD_GUIDE.md) |
| 知道现在到哪一步了 | [`docs/STATUS.md`](docs/STATUS.md) |
| 看走过的弯路 | [`docs/RETROSPECT.md`](docs/RETROSPECT.md) |
| 看本轮交付的硬数字 | [`docs/REPORT_FINAL_DELIVERY.md`](docs/REPORT_FINAL_DELIVERY.md) |

## 一条命令

```powershell
python tools\final_fix\build.py
```

18 个阶段（基底 → ELF 补丁 → 字库 → 文本 → 术语/标题 → 任务名 → 自证），
每步比对 `tools/final_fix/fix_spec.json` 里声明的 sha256，不符立刻退出。

## 仓库里有什么

```
tools/final_fix/     ★ 唯一构筑入口 build.py + 唯一校验入口 verify.py + 单一真源 fix_spec.json
                       + 18 个阶段脚本 + assets/{charset,text,mis}
tools/lib/           共用库：字体 / 图集 / 容器（dump_font · repack_font · font_compact · zx_lib …）
tools/text_csv/      文本表工具（dump_text_csv / inject_text_csv）+ tcslib
docs/                22 篇：现状 / 两份指南 / 关键报告 / 试错记录 / 归档
```

## 本地自备（不进库：版权 + 体积）

* 英文原盘 `Tom Clancy's Ghost Recon (USA).iso`（sha256 `2b42ea7c…8531`）
* K2 cdvd 转储 `GR_FA2400_K2 (2026-10-17 15-08-20).dump`（sha256 `11f371f2…add9`）
* 像素字体 `方正像素16.ttf`

放哪、为什么需要，见 [`docs/BUILD_GUIDE.md`](docs/BUILD_GUIDE.md) §1。

## 纪律

* 基底**只能**是英文原盘，禁止拿历史汉化盘当基底（否则链条不可复现）。
* 能用数据解决的绝不改 ELF —— Game CRC 一变，玩家旧存档全废。
* 任何文本区**不得**出现 `0xFF`（引擎的 XML 词法器把它当 EOF）。
