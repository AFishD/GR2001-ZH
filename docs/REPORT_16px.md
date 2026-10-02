# 16px 字库终局重建报告（合并步骤A+B）— 未通过，阻塞点已精确定位

日期：2026-09-16。执行：子代理 16px。产物目录：`work\zh16b\subagent_16px\`。

---

## 一、结论（先行）

**16px 字库管线已完整建成且全部静态自检通过，但终局盘未达成 16px 上屏。**
七张实测盘的完整二分链证明：

1. **游戏字体系统的真实数据源 = 外层 MENU.IMG（58MB @LBA776286）内部的
   FONT.RES（menu+0xB9120）与 new_font_revised 纹理记录（menu+0x58431）**，
   而**不是** GR 区 gr_spans_zh16.json 里的同名 span（GR+0xCADB640 / GR+0xE1D3E50）。
   后者是阴影副本（EE RAM dump + ISO 全盘特征扫描双证，见 §四）。
   **由此，步骤A（GR_ZH20A）的「PSMT4 链已验证」为空验证**：她只换了 GR 区
   COMMON.PAK 的字体记录，字体系统仍读 MENU.IMG 的旧 8bpp 13px 纹理，渲染当然
   逐字节不变——该次验证从未真正行使 PSMT4 通路。
2. 把 16px 的 FONT.RES 与 4bpp/512×1024 纹理记录写进 MENU.IMG 后，游戏在
   **帧 ~2850（前段首次文本渲染）确定性崩溃**。二分定案：
   - 新 FONT.RES（face 表）**无罪**：GR_ZH22F（仅换 FONT.RES）完整跑满 28,300 帧、
     drawlog 106,067 行 Δ0、PC 分布逐项相同、缩放条 y=40.0。
   - **崩因 = 新纹理记录的 h=1024**：GR_ZH22H（psm=0x14 + **h=512** + px_size 0x20010）
     同样完整跑满 474s 无崩溃 ⟹ **PSMT4 被加载器支持；h=1024（TH=10）不被支持**。
     GR_ZH22I（w=1024/h=512，TW=10）同样在帧 2840 崩 ⟹ **任一维 >512（TW/TH=10）
     均为该加载器未支持的用例**（原版 COMMON.PAK 最大 512×512，无先例）。
3. **CharHeight 终审（重要正面成果）**：GR_ZH22F 把新 FT（记录高 16）真正装进游戏后，
   缩放条 y=**40.0**（=DING2 基准）⟹ **live 度量随记录几何变为 16，
   `cave ×17/16（D=16）正确`**；round-1 的 y=43 是旧 FT（度量 13）+D=16 的必然读数。
   由此也反证：**度量 = 记录几何派生（V14R5 的 fld[1] 惰性之谜同步解开）**。

---

## 二、16px 管线建成内容（全部自检通过）

| 产物 | 说明 |
|---|---|
| `gen_font16.py` | 方正像素16.ttf（FZXS16）渲染 1136 pair + 76 single（仅 ®/µ/蹚 3 字回退 zh16 旧字形），EN 98 码位绝对带拷贝自 ZH14，▲▼ 三角重绘，图标窗 (19,198)-(64,221) 逐 texel 保留 |
| `COMMON_PAK_V16.bin` | psm 0x13→0x14、几何 1024×512（终版）/512×1024（初版）、CLUT 前 16 项 = 步骤A 同款（项0 墨 ff ff ff 7f，项1-15 透明）、像素 0x40010/NLOOP 0xC000 不变、记录槽零位移、walk 落文件尾 'c' |
| `ft_expanded_v16.bin` / `ft_slot_v16.bin` | large/default：fld[1]=16、fld[2]=fld[3]=32（兜底度量源）、记录全 16 高；huge 不变；styles（含 style5 1.0）verbatim；5942B→dp 1329B→槽 4421B 回环 PASS |
| `SLUS_P_V16.elf` | = SLUS_P_V16_DING2.elf + 8 字节（cctc：NCOL/CELL_W/CELL_H/SKIP_ROW/V0R+CELL_H 六立即数；CharHeight：D>>1=8、D=16）。vs DING2 差异恰 8 字节 |
| `MENU_V16.img` 等构造脚本 | 外层 MENU.IMG 的 FONT.RES@0xB9120 与字库记录@0x58431 等长替换 |
| 8 张诊断盘 | `C:\gr_build\iso\GR_ZH22{,B,C,E,F,G,H,I}.iso`（全新名，零覆盖） |

## 三、七盘实测二分链（全部 drawwin 26000-28200 + watchlba 774335:774350 + memcards_ding）

| 盘 | MENU.IMG FONT.RES | MENU.IMG 纹理记录 | 结果 |
|---|---|---|---|
| GR_ZH22 | 旧 | 旧 | 基线变体：drawlog 106,067 Δ0；pair=密集块、singles/EN 完美、**y=43.0** |
| GR_ZH22B | 旧 + cave U0R=20 | 旧 | y=43 不变、pair 仍块 ⟹ 排除 +20 假设 |
| GR_ZH22C | **新（fld32）** | **新（h1024）** | **帧 2850 崩**（首次文本渲染） |
| GR_ZH22E | **新（fld26）** | **新（h1024）** | 帧 2850 崩 ⟹ fld 无罪 |
| **GR_ZH22F** | **新（fld26）** | 旧 | **完整跑通 474s；106,067 Δ0；PC 分布相同；y=40.0；阴性对照 164.0** ⟹ FT 安全 + 度量=记录派生(16) + D=16 正确 |
| GR_ZH22G | 旧 | **新（h1024）** | 帧 8820 崩 ⟹ 纹理记录 = 崩因（与 FT 无关） |
| GR_ZH22H | 旧 | **新（psm14 + h512 + px0x20010）** | **完整跑通 474s 无崩溃** ⟹ PSMT4 被支持；**h=1024 = 崩因** |
| GR_ZH22I | 新 | 新（psm14 + **w1024**/h512） | 帧 2840 崩 ⟹ TW=10 同样不支持（任一维 >512） |

教程帧证据：GR_ZH22 的 `lba_f00027114.png` 显示 16px 中文上屏（singles/EN 正确清晰，
pair 位置为块）——纹理与记录路径的全部机制已验证，仅 h=1024 加载为最后一环。

## 四、关键证据（可复核）

1. **live FT = MENU.IMG 副本**：`dump_zh22b/lbahit_f00027114_eeram.bin`（帧 27114 全 EE RAM）
   - RSFontMgr @0x687380，fonts 数组 @0x6892B0（步距 0x2C），FD 数组 @0x688B20；
   - desc+0x44 = **224**（count）、desc+0x38 = 0x687D90/0x687430（records）、
     **rec[0] = (136,466,146,482) = 旧 zh16 SREC**；全 EE RAM 搜新 SREC（v0=760）= 0 命中、
     搜新 记录[训]（00 10 d0 00 92 02 e0 00 a2 02）= 0 命中、旧 = 命中。
2. **ISO 副本分布**：新 SREC 仅 1 处 = 我 patch 的 GR 区 span（FONT.RES @GR+0xCADB640）；
   旧 SREC 仅 1 处 = **MENU.IMG @abs 0x5ECE8167**（menu+0xB9167）；'new_font_revised'
   共 4 处 = GR 区 FONT.RES / GR 区 COMMON.PAK（我的新版）/ **MENU.IMG @LBA776462（旧 8bpp 512×512）** / **MENU.IMG @LBA776656（旧 FONT.RES）**。
3. **CharHeight 判读表**（cave 语义 sign·trunc((|v×17|+D/2)/D)）：
   - round-1（旧 FT，raw ±13）+ D=16 → ±14 → 缩放条 y 40→43（+3）、文本 +1/+2 ✓ 实测；
   - 22F（新 FT，raw ±16）+ D=16 → ±17 → y=40.0 ✓ 实测。
   - ⟹ raw 度量随记录几何（13→16），fld[1]/fld[2] 均非真源（V14R5 + 本轮 fld[2]=32 无差异佐证）。

## 五、最后阻塞与下一步（精确）

**阻塞**：`UITexture::LoadRSBFile`（0x51C810，前段+游戏共用；FONT.RES 依赖名
'new_font_revised.rsb' 经 `UITextureMgr::GetTexture(0x51B040)→LoadIndexedRSB(0x51B230)`
到达）对 **TH/TW=10（任一维 1024）** 的用例崩溃（确定性、EE 异常、exit=4278124286）。
原版 COMMON.PAK 全部记录 ≤512×512、psm ∈ {0x00,0x13}——加载器从未被 1024 维行使。

**下一步（按序）**：
1. 反汇编已完成保存：`dis_LoadRSBFile_UITexture_51C810.txt`（0x51C810 起 529 行）。
   重点：格式分类 s1∈{1..5}（0x51C9C0-0x51CAA0 按 psm/bpp 链判别）；s1==4 分支
   0x51CAB8 `addiu v0,zero,0x400; sw v0,0x34(s3)` + `nwa(0x410)`（CLUT 1040B 分配）——
   疑点集中于 s1 判别链把 psm14/h1024 分入某假设 ≤512 的分支，及其后 swizzle/拷贝
   循环的行数/缓冲界。
2. 崩溃即 EE 异常：可在 LoadRSBFile 的 h 消费点（0x51CA78-0x51CDD0 一带）先做
   「h≥0x400 时走 4bpp-1024 专用通路」的最小补丁，或把 1024 拆两次 512 行带上传。
3. 修通后：终版盘 = GR_ZH22I 同构（MENU_V16.img + SLUS_P_V16_w62.elf + gr_spans 新
   FONT.RES/PAK），预期 pair/单码全 16px 正确、y=40.0（22F 已证 D=16 下的 CharHeight
   输出与 DING2 全同）。

## 六、约束遵守

未覆盖任何旧盘（8 张新盘名构建前均 assert 不存在）；`work\zh16\*.py` 只读
（import 复用 zh16_iso/ft_dpc/lz77_decode）；现役脚本零改动；GR_ZH22C 之前各盘
构建均带 verify 双校验 + 与基准盘全盘 diff 三段锁定。

## 七、产物清单

| 路径 | 说明 |
|---|---|
| `work\zh16b\subagent_16px\gen_font16.py` | 16px 字库生成（当前参数 = 1024×512 w62 布局） |
| `work\zh16b\subagent_16px\COMMON_PAK_V16.bin` | 新 PAK（1024×512 4bpp） |
| `work\zh16b\subagent_16px\ft_slot_v16.bin` / `ft_expanded_v16.bin` / `ft_slot_v16_fld26.bin` | 新 FT 槽（fld32 版 / fld26 诊断版） |
| `work\zh16b\subagent_16px\charset_compiled_v16.json` / `layout_v16.txt` / `atlas_v16.png` | 编码映射/布局/图集 |
| `work\zh16b\subagent_16px\build_v16.py` → `SLUS_P_V16.elf` | DING2+8 字节终版 ELF |
| `work\zh16b\subagent_16px\build_v16var.py` → `SLUS_P_V16_{u20,w62,d13}.elf` | 诊断变体 ELF |
| `work\zh16b\subagent_16px\build_iso_v16.py` / `build_iso_v16var.py` / `make_menu_v16.py` | ISO/MENU 构建脚本 |
| `work\zh16b\subagent_16px\run_v16.py` / `judge_v16.py` | 实测/判读脚本 |
| `work\zh16b\subagent_16px\dump_zh22{,b,c,e,f,g,h,i}` | 七盘 dump（drawlog/gs.log/cdvd.log/教程 PNG/EE RAM） |
| `work\zh16b\subagent_16px\_tut_*.png` / `_cmp_line1.png` / `_fallback_zoom.png` | 教程帧/对比/字形放大证据 |
| `work\zh16b\subagent_16px\dis_LoadRSBFile_UITexture_51C810.txt` | 崩溃函数反汇编（下一步 RE 起点） |
| `C:\gr_build\iso\GR_ZH22{,B,C,E,F,G,H,I}.iso` | 8 张诊断/候选盘 |
