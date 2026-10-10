# BUILD_MANIFEST.md — 构建产物生成指示表（ISO 重建校对与清理轮）

**日期**：2026-09-18 ｜ **执行**：ISO 重建校对与清理（重跑脚本 → MD5 对比 → 相同删盘 → 写本表）
**对象**：`C:\gr_build\iso\` 25 张汉化盘（24 张 1,648,164,864 B + GR_ZH37D 1,304,428,544 B 截短）
**结论**：16 盘成功重跑复现，其中 **15 盘逐字节复现（MD5 全同）→ 已删 11 张非基线盘（回收 16.9 GiB）**；1 盘（ZH15）MD5 不符保留；8 盘因依赖缺失/脚本未存档未经重跑保留。现存 **14 张**（~22 GB）。基线重跑前 MD5 全量存档于 `work\zh16b\_md5_existing.txt`，重跑产物 MD5 存档于 `work\zh16b\_md5_rebuilt.txt`（临时输出盘与临时副本脚本已删）。
**未跑 gsrunner、未做反汇编、未改动任何现存脚本**（重跑一律用原脚本原样：或脚本本身参数化，或复制到临时目录 `_repro_tmp\` 仅改输出/失效路径后运行，对比完成即删）。

---

## 一、如何从零重建任一盘（通用流程）

所有盘共用同一组装公式（`work\zh16\zh16_iso.py` 的 `build()/verify()` 为权威实现，全部 subagent 构建脚本 import 它）：

```
盘 = GR_K99.iso (基底, bases\GR_K99.iso, 1,648,164,864 B)
   + SLUS_P_*.elf      @LBA295   (字节偏移 604,160;      大小恒 37,453,732 B)
   + MENU_*.img        @LBA776286(字节偏移 1,589,833,728; 大小恒 58,300,882 B)
   + GR.IMG 数据区     @LBA19175 (字节偏移 39,270,400;   大小 1,550,563,328 B)
       （整区自 C:\gr_build\iso\GR_ZH12.iso 迁移——**ZH12 是全谱系 GR 区数据源，删它则所有盘不可重建**）
   + gr_spans_*.json 白名单补丁（FONT.RES/COMMON.PAK/RES 槽 hex 字节 + 5×ATR 人名，写至 GR 区内 off）
```

重建步骤：
1. **装依赖**：核对下表「依赖中间产物」列全部存在（ELF/MENU/PAK/ft_slot/spans）；
2. **跑脚本**：`<anaconda3>/python.exe <脚本> [参数]`（环境变量见命令行列）。所有脚本自带：构建前 `assert 盘不存在`（防覆盖）、写后回读校验、`verify()` 双 0 越界（GR 区 vs ZH12 补丁越界 = 0，基底区 vs K99 越界 = 0）；
3. **对 MD5**：与 `_md5_existing.txt` 基线（或本表）比对，逐字节同 ⇒ 等价盘。
4. 输出名默认指向 `C:\gr_build\iso\<盘名>.iso`；**若同名盘已存在，复制脚本到临时目录改输出路径后再跑，绝不覆盖**。

两处历史路径漂移（重跑时需在临时副本修正，本轮已验证修正后 MD5 逐字节同）：
- `gr_build\tmp\zh13\zh13_iso.py` 的 `BASE` 指向已清理的 `han_v2\GR_K99.iso` → 改指 `bases\GR_K99.iso`（同一文件）；
- `work\iconfix\build_iso.py` 的 `DST` 指向项目根下 `iso\`（现不存在）→ 改指实际输出位置。

---

## 二、全盘清单（25 张）

状态图例：**可复现已删** ｜ **可复现建议保留**（基线） ｜ **保留-MD5不符** ｜ **保留-依赖缺失** ｜ **保留-脚本未存档**
MD5 列：「前=后」表示重跑产物与原盘逐字节同。

| 盘名 | 状态 | 生成脚本（路径 + 运行命令行） | 依赖中间产物（均在，除标注缺失） | MD5 | 判定/用途 |
|---|---|---|---|---|---|
| GR_ZH12 | 保留-依赖缺失 | `gr_build\tmp\zh12\zh12_iso.py` | ❌GR_ZH11.iso（已删，GR 区源）、❌han_v2\GR_K99.iso（现位 bases\）；ELF=SLUS_P_V10.elf、MENU_ZH12.img、ft_slot_zh12/COMMON_PAK_ZH12（gr_build\tmp\zh12\ 全在） | 692e7ce6…（未重跑） | 首个全汉化盘；**全谱系 GR.IMG 区数据源，永不删** |
| GR_ZH13 | 可复现已删 | `gr_build\tmp\zh13\zh13_iso.py`（BASE 路径修正后重跑） | K99(bases)、GR_ZH12、SLUS_P_V11.elf、MENU_ZH13.img、ft_slot_zh13/COMMON_PAK_ZH13 | 7046459a… 前=后 | 第二版全量汉化盘（V11+Zpix EN 带）；ZH13B/ZH15 的构建基底 |
| GR_ZH13B | 可复现已删 | `work\iconfix\build_iso.py`（DST 路径修正后重跑） | GR_ZH13、iconfix\SLUS_P_V12.elf、MENU_ZH13B.img、GR_RES_blob_ZH13B.bin | d9aa710c… 前=后 | ZH13 + V12 ELF + 图标窗修复（iconfix 终盘） |
| GR_ZH14 | 可复现已删 | `work\zh14\zh14_iso.py` | K99(bases)、GR_ZH12、zh14\SLUS_P_V12.elf、MENU_ZH14.img、ft_slot_zh14/COMMON_PAK_ZH14 | ae2d51b6… 前=后 | 第三版（网格 Y0=2 跳行 / large fld16 / huge fld20） |
| GR_ZH15 | 保留-MD5不符 | `work\bootscreen\zh15_iso.py` | K99、GR_ZH13（可由 zh13_iso.py 重建）、bootscreen\SLUS_ZH15.elf、MENU_MCZH.img | 前 d96cffd3… / 后 a59ebc8d… **DIFF** | ZH13+记忆卡屏汉化盘；**输入已变**：差异仅落 MENU 区 LBA 776661 起（≈20 个 MC 条目域，合并段 1.37 MB）——现役 MENU_MCZH.img 晚于盘被修改（mc_redraw/Zpix 后续轮），盘保旧态 |
| GR_ZH16 | 可复现建议保留（用户在用） | `work\zh16\zh16_iso.py`，`python …zh16_iso.py ZH16`（或 import 后调 build/verify；__main__ 会附带产出 work\zh16\GR_ZH16T.iso） | K99、GR_ZH12、zh16\SLUS_P_V14.elf、MENU_ZH16.img、gr_spans_zh16.json | 99b57099… 前=后 | 第四版终盘（V14 基准）；全部 16px 谱系的对拍基准 |
| GR_ZH16_user_r2 | 保留-脚本未存档 | 无（用户实机测试原盘备份，见 NEXT_SESSION_HANDOFF_ROUND3 §首行） | — | 6f83cbd1…（未重跑） | 用户三轮实机测试用盘备份 |
| GR_ZH19B | 可复现已删 | `subagent_ding\zh19_ding_iso.py`；`DING_ELF=…\SLUS_P_DING2.elf DING_ISO=<输出> python …zh19_ding_iso.py` | K99、GR_ZH12、DING2.elf、MENU_ZH16.img、gr_spans_zh16.json | aaa48fc8… 前=后 | 任务丁 R2（CharHeight ×17/13 比例缩放）判别盘 |
| GR_ZH24 | 可复现已删 | `subagent_offset_fix\zh24_iso.py`；`M26_MENU=…\MENU_ZH16_M26.img python …zh24_iso.py <输出> …\SLUS_P_M26.elf …\gr_spans_zh16_m26.json` | K99、GR_ZH12、M26.elf、MENU_ZH16_M26.img、ft_slot_zh16_m26.bin、gr_spans_zh16_m26.json | eaa162d8… 前=后 | 任务② fld[1]=26 首版盘（缩放条 y=31 归位，13px 纵向 2× 拉伸） |
| GR_ZH24B | 保留-依赖缺失 | 同上，ELF 换 ❌SLUS_P_M2X.elf（已删），spans=work\zh16\gr_spans_zh16.json，MENU 默认 MENU_ZH16.img | M2X.elf **缺失**（重建链见 §四.1） | 10b769de…（未重跑） | cave ×2 过渡留档盘（对 huge/小字体更激进，不推荐） |
| GR_ZH26 | 保留-依赖缺失 | 脚本未存档（R1 判别盘） | ❌R1 专用 PAK（alloc=0x40000 违例版）未存档；SLUS_P_V17.elf 在 | c2196846…（未重跑） | 1024 维判别 R1：alloc 违例 → **boot 死亡盘**（勿用；其价值=alloc 铁律的实证） |
| GR_ZH26B | 保留-依赖缺失 | `subagent_16px_fix\build_v17r2.py` | ❌SLUS_P_V16_w62.elf（已删，重建链见 §四.2）；其余（ft_slot_v16/PAK_V16/MENU_ZH16 等）全在 | c70196e3…（未重跑） | 1024 维判别 R2：拆双 GIFTAG，崩 2850 |
| GR_ZH26C | 可复现已删 | `subagent_16px_fix\build_zh26c.py` | SLUS_P_V17.elf、COMMON_PAK_V16.bin、MENU_ZH16.img、ft_slot_v17.bin（脚本现场合成 V17S3.elf 与 MENU_ZH26C.img） | 29c7b4f1… 前=后 | 1024 维判别 R3：B′512 分块，崩 2840；p4 修补模拟器上的 blob 参照盘 |
| GR_ZH26D | 保留-依赖缺失 | 脚本未存档（R4） | ❌SLUS_P_V17T9.elf、❌MENU_ZH26D.img（均已删，重建链见 §四.3） | ef4c5c0f…（未重跑） | 1024 维判别 R4：TEX0.TW/TH 钳 9，崩 2840 |
| GR_ZH27 | 可复现已删 | `subagent_decouple\iso_zh27.py`；`python …iso_zh27.py GR_ZH27.iso`（ELF 默认 V18） | K99、GR_ZH12、V18.elf、offset_fix\MENU_ZH16_M26.img、gr_spans_zh16_m26.json | 4e994bdc… 前=后 | 任务A V18 解耦（UI 字体四边形高 26→13）测试盘 |
| GR_ZH29 | 可复现已删 | `subagent_spacing\zh24_iso.py`；`M26_MENU=…\MENU_ZH16_M26.img python …zh24_iso.py GR_ZH29.iso …\SLUS_P_V19.elf …\gr_spans_zh16_m26.json` | K99、GR_ZH12、V19.elf、MENU_ZH16_M26.img、gr_spans_zh16_m26.json | 1a81de5b… 前=后 | 任务C V19 行距 CLAMP（f8=max(原值,CharHeight)）盘 |
| GR_ZH31 | 可复现建议保留（终盘） | `subagent_decouple\iso_zh27.py`；`python …iso_zh27.py GR_ZH31.iso SLUS_P_V20.elf` | K99、GR_ZH12、V20.elf（M26∪V18∪V19）、MENU_ZH16_M26.img、gr_spans_zh16_m26.json | 47a7dcc0… 前=后 | **13px 终盘**：「位置+字形+行距」三项全对（y=31 + 1:1 + 行距 26） |
| GR_ZH32 | 可复现已删 | `subagent_split\build_zh32.py` | SLUS_P_V17.elf、COMMON_PAK_V21.bin、MENU_ZH16.img、ft_slot_v17.bin（现场合成 V21.elf/MENU_V21.img） | 314bad52… 前=后 | 路线B 判别中间件（V21 ELF=V17 原样、无 CLUT 补丁，勿用） |
| GR_ZH32B | 可复现已删 | `subagent_split\build_zh32b.py` | SLUS_P_V17.elf、COMMON_PAK_V21.bin、MENU_ZH16.img、ft_slot_v17.bin（现场合成 V22.elf/MENU_V22.img） | 924cee1f… 前=后 | V22（CLUT 强制 psm13 形状）+V21 PAK；「16px+标准模拟器」首证盘（后证乱码） |
| GR_ZH33 | 保留-依赖缺失 | `subagent_final\build_zh33.py` | ❌subagent_split\MENU_V22.img（已删，重建链见 §四.4）；SLUS_P_V23.elf 在、GR_ZH32B 原盘 diff 锁（盘已删，需先重建 ZH32B） | 5a5c7dd0…（未重跑） | V23 ELF+ZH32B 数据（X0=20 偏置期），**乱码盘勿用** |
| GR_ZH34 | 可复现已删 | `subagent_mojibake\build_zh34.py` | COMMON_PAK_V16X.bin、ft_slot_zh34.bin、MENU_ZH16.img、split\SLUS_P_V22.elf、make_pak_v21.py（现场合成 common_pak_seg_tmp/MENU_V23/make_pak_v22） | 4baaeba9… 前=后 | X0=4 乱码修复验证盘（fld16/y=41 根因验证留档） |
| GR_ZH35 | 可复现建议保留（终盘） | `subagent_mojibake\build_zh35.py` | common_pak_seg_tmp.bin、ft_slot_zh34_fld26.bin、MENU_V23.img、split\SLUS_P_V22.elf、gr_spans_zh16.json（现场合成 MENU_V24.img） | a1556a9b… 前=后 | **16px 逐字正确盘**（X0=4+fld26，V22 谱系；纵向 1.625× 拉伸未修） |
| GR_ZH36 | 可复现建议保留（终盘） | `subagent_final\build_zh36.py` | SLUS_P_V23.elf、MENU_V24.img、common_pak_seg_tmp.bin、ft_slot_zh34_fld26.bin、gr_spans_zh16.json、GR_ZH35.iso（diff 锁） | 055ae7e3… 前=后 | **16px 完美终盘**（V23=V22∪V19∪V18B）：逐字正确+y=31+不拉伸+行距 26+标准模拟器全程 |
| GR_ZH37C | 保留-脚本未存档 | 脚本未存档（subagent_menu\build_zh37.py 仅产 GR_ZH37.iso，该盘亦不在库） | MENU_V25.img/ft_slot_zh37.bin 在，但 C/D 变体配方未存档 | adc4e133…（未重跑） | 前端菜单 huge face 补 224 记录实验判别件（r1–r3 谱系诊断盘） |
| GR_ZH37D | 保留-脚本未存档 | 脚本未存档 | 同上 | d748bbe9…（未重跑） | 同上诊断件；**尺寸 1,304,428,544 B（截短盘，非全尺寸）** |

---

## 三、已删除盘清单（11 张，均为 MD5 逐字节复现后删除，共回收 18,129,813,504 B ≈ 16.9 GiB）

| 已删盘 | 复现命令（临时输出名 `_RB` 后缀跑于 `_repro_tmp\`，MD5 全同后删原盘） |
|---|---|
| GR_ZH13.iso | `python gr_build\tmp\zh13\zh13_iso.py`（临时副本：BASE han_v2→bases） |
| GR_ZH13B.iso | `python work\iconfix\build_iso.py`（临时副本：DST 改向） |
| GR_ZH14.iso | `python work\zh14\zh14_iso.py` |
| GR_ZH19B.iso | `DING_ELF=…SLUS_P_DING2.elf DING_ISO=… python subagent_ding\zh19_ding_iso.py` |
| GR_ZH24.iso | `M26_MENU=…MENU_ZH16_M26.img python subagent_offset_fix\zh24_iso.py …SLUS_P_M26.elf …gr_spans_zh16_m26.json` |
| GR_ZH26C.iso | `python subagent_16px_fix\build_zh26c.py` |
| GR_ZH27.iso | `python subagent_decouple\iso_zh27.py GR_ZH27.iso` |
| GR_ZH29.iso | `M26_MENU=… python subagent_spacing\zh24_iso.py …SLUS_P_V19.elf …gr_spans_zh16_m26.json` |
| GR_ZH32.iso | `python subagent_split\build_zh32.py` |
| GR_ZH32B.iso | `python subagent_split\build_zh32b.py` |
| GR_ZH34.iso | `python subagent_mojibake\build_zh34.py` |

复现附带结论：上述 11 盘 + 基线 4 盘（ZH16/31/35/36）重跑全部 `[BUILD] 写出+回读 PASS` + `verify 双 0 越界` + MD5 全同 ⇒ **整个组装管线（K99+ELF+MENU+GR 区迁移+spans）是字节确定性的**。被构建脚本重写的中间产物（MENU_V21/V23/V24.img、SLUS_P_V21/V22.elf、make_pak_v22.py、common_pak_seg_tmp.bin、GR_ZH14T.iso）重跑后与原文件逐字节一致（已核验），副作用新文件已清理，目录状态复原。

## 四、依赖缺失的中间产物重建链

1. **SLUS_P_M2X.elf**（ZH24B 用）：运行 `subagent_offset_fix\build_m26_elf.py`（输入 subagent_ding\SLUS_P_DING2.elf + work\zh16\SLUS_P_V14.elf 均在；脚本同时重建 SLUS_P_M26.elf，确定性已由本轮旁证）。→ 重建后即可用 §二 ZH24 命令行复现 ZH24B。
2. **SLUS_P_V16_w62.elf**（ZH26B 用）：= `subagent_16px\SLUS_P_V16.elf` + cctc 6B 改写（0x4170AC: 0x1E→0x3E；其余 5 处 0x4170C4/D4/D8/EC/FC 与 V16 已同值）——已实测 V16 现存字节与 w62 断言仅差这 1 处；改写逻辑见 build_v17r2.py §2。→ 重建后运行 build_v17r2.py（注意它会先归档现 SLUS_P_V17.elf 再重写，跑完需复原）。
3. **SLUS_P_V17T9.elf + MENU_ZH26D.img**（ZH26D 用）：V17T9 = SLUS_P_V17.elf + 2B（0x5188A8/0x5188B0 `andi v1,a0/t0,0xffff`→`addiu v1,zero,9`，REPORT_16px_fix §三）；MENU_ZH26D = MENU_ZH16.img 双副本等长替换（FT@0xB9120=ft_slot_v17.bin + 记录@0x58431=COMMON_PAK_V16 记录，构建逻辑同 build_zh26c.py）。→ 重建后按 zh16_iso build+verify 组盘。
4. **MENU_V22.img**（ZH33 用）：运行 `subagent_split\build_zh32b.py` 即再生成（本轮复现 ZH32B 时已验证再生成物与原构建逐字节一致后复原删除）。→ 之后再跑 build_zh33.py（其 diff 锁还需 GR_ZH32B.iso，可先按 §二重建）。
5. **GR_ZH11.iso 与 han_v2\GR_K99.iso**（ZH12 链）：最早实验盘与旧位置基底，均未存档。GR_K99 现存 `bases\GR_K99.iso`（ZH13 复现逐字节同 ⇒ 与 han_v2 原件等价）；GR_ZH11 无替代 ⇒ **ZH12 不可重跑，但 ZH12 本身是所有盘的 GR 区数据源，必须保留**。
6. **ZH26 R1 专用 PAK**（alloc=0x40000 违例版）与 **ZH37C/ZH37D 构建脚本**：未存档，不可重建（前者为 boot 死亡实验件，无重建价值）。

## 五、附注

- 本轮重跑前 25 盘 MD5 基线：`work\zh16b\_md5_existing.txt`；重跑产物 MD5：`work\zh16b\_md5_rebuilt.txt`（临时输出盘与临时副本脚本已删）。
- ZH15 是唯一「脚本可跑但 MD5 不符」盘：输入 MENU_MCZH.img 的 MC 条目区晚于盘被改。若需按现输入重造新版 ZH15，属内容变更而非复现，须走新盘名。
- 全部构建脚本默认输出 `C:\gr_build\iso\<盘名>.iso` 且带防覆盖断言；重跑现役盘（ZH16/31/35/36 等）时务必用临时输出名。
- `C:\gr_build` 为指向本项目 `gr_build\` 的 junction（同一份文件）。
