# docs/_obsolete/ —— 归档区（2026-10-18 收尾整理）

> **这里放什么**：① 被实测/实机**否证**的路线所对应的过程报告；② 一次性轮次的指南与产物记录（其盘已清理）。
> **归档 ≠ 结论作废的孤篇**：每篇文首都插入了指向 `docs/CORRECTIONS.md` 对应小节的横幅；
> 原文一字未删（过程记录价值），只是不再与权威文档并列。

| 文件 | 归档理由 |
|---|---|
| `AB_TEST_GUIDE.md` | A/B 打靶指南：验证「`sp+221` 变长步进」框架 —— 该框架**已被推翻**（`CORRECTIONS.md` §6）；对照盘 `GR_AB` 已清理 |
| `CSFIX_TEST_GUIDE.md` | `GR_CSFIX2400` 实机验收指南（一次性轮次），0 引用 |
| `CVAR_TEST_GUIDE.md` | CVAR 控制变量轮的实机指南；盘已清理。**它记录的两条关键否证**（MENU.IMG 声明长度假设不成立 / `stored≠real` 是常态）已并入 `CORRECTIONS.md` §1/§2 与 `REPORT_NULLDEREF_ZH113b.md` |
| `DISASM_TEST_GUIDE.md` | 候选修复（F1F2 / `pkt`）的实机判定表 —— 该路线**已被实机否证**（`CORRECTIONS.md` §7）；最终采用 F4+OOMFIX+F7 |
| `OOMFIX_TEST_GUIDE.md` | OOMFIX 轮给用户的验证指南（一次性）；OOMFIX 的权威取证是 `REPORT_OOMFIX.md` |
| `REPORT_16px.md` | 16px 字库终局重建 —— 报告自己写明**未通过** |
| `REPORT_SENTINEL.md` | 候选 R（`0xB1/0xB5` 图标哨兵）四张对照盘 ——**已否证**；保留的是 `REPORT_SENTINEL_FIX.md` |
| `REPORT_W2048_r84.md` | W=2048 的 r84 复核 —— 同黑屏 |
| `REPORT_atlas_stall_threshold.md` | 「像素容器变大 ⇒ 读盘停摆」的阈值论 ——**被否证**（成品盘 h=644 实机跑通） |
| `REPORT_font_compact.md` | `font_compact.py` 重排工具路线 ——被取代，最终构筑不启用 |
| `REPORT_font_repack.md` | 每轮自动字库紧凑重排 ——最终构筑固定 `--no-font-repack`（容量增益 0 + 会破坏非 `<text>` 中文串） |
| `REPORT_font_testpage.md` | round60「字库测试页」——一次性过程产物 |
| `REPORT_hook_nav.md` | round61「钩子 + 闭环导航」——一次性过程产物 |
| `REPORT_noautowrap.md` | 「关闭引擎自动折行」实验（`GR_ZH112`）——**未采用**；最终用 `{WRAP}` 人工断点 |
| `REPORT_reclut_crash.md` | round72 的 recLUT 崩溃链取证 ——旧线一次性产物，新线未复现 |
| `REPORT_reclut_crash2.md` | round74 的新崩溃链取证 ——同上 |
| `REPORT_sf_nowrap.md` | 「特别收录组件级折行开关」实验 ——**未采用** |
| `REPORT_texture_limit_rootcause.md` | 「纹理/容器变大 ⇒ 引擎卡死」根因说 ——**被否证**（`CORRECTIONS.md` §4） |
| `REPORT_w2048_probe.md` | 图集 W 1024→2048 单变量探针 ——**实机黑屏**，路线否证 |
| `REPORT_zero_missing_glyph_build.md` | round81「零缺字成品盘」——被 round82+ 与 2400 线取代 |
| `REPORT_zero_missing_glyph_build2.md` | round82 ——本文自己写明"**不要把 `GR_ZH121.iso` 当成可用成品盘发布**" |

> 返回索引：`docs/README.md` · 订正表：`docs/CORRECTIONS.md` · 当前状态：`docs/STATUS.md`
