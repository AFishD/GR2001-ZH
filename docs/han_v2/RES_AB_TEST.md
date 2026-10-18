# RES_AB_TEST.md — EN_STRINGS.RES 未压缩写回 + 档案条目重指向 A/B 实测结论文档

日期: 2026-09-12
环境: PCSX2 gsrunner (无头), SLUS-206.13, ISO 基底 `han_v2\GR_K99.iso`
(MENU.IMG 在 LBA 776286), 模拟器 `C:\gr_build\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe`

---

## 一、目的

验证「把 128,545B 展开态 EN_STRINGS.RES 以未压缩方式写入可牺牲数据区,
并把条目表 off 指向该处、stored=real=128545」是否安全。
(`res_encode.py build --framed-lzo` 输出 59,145B > 原 47,570B 槽位, 压缩写回
原地不可行, 因此才有本重指向方案。)

## 二、布局发现 (menu_orig\MENU.IMG, 686 条目, 档案 58,300,882B)

五语言 STRINGS.RES 条目表:

| 条目 | off | stored | real | 备注 |
|---|---|---|---|---|
| EN_STRINGS.RES | 0x0377E000 | 47,570 | 128,545 | 档案数据区最末条目 (end=0x37899D2, 之后到档案尾仅 769B) |
| DE_STRINGS.RES | 0x00218B00 | 55,542 | 146,910 | ┐ |
| ES_STRINGS.RES | 0x00226400 | 53,077 | 142,148 | │ 四语言区连续, 0x218B00..0x24D5F8, |
| FR_STRINGS.RES | 0x00233360 | 55,413 | 149,664 | │ 总跨度 215,288B ≥ 128,545B |
| IT_STRINGS.RES | 0x00240BE0 | 51,736 | 139,082 | ┘ |

- 四语言区之后紧邻 5 个 STRINGS.TXT (0x24D600..0x250BDF) 与 LOGOUBI.PSS。
- 数据区无重叠; 档案内 **不存在 ≥128,545B 的无条目引用空隙**
  (看似 0x3608D40..0x366F240 的"空隙"实为 IW_*.QOZ/.BMZ 武器模型群;
  最大真空隙仅 ~49KB)。故"未压缩写回"只能走牺牲区+重指向。
- 472 个 stored==real 条目 (PAK/RSB/ATR/TXT/XML…) 的头部 0/472 带
  {plen}{osz} 子流框架 → 历史惯例: 未压缩载荷=纯内容本体。
- 头部 0x20 处并无哈希表; 真正的附属表在 0x9230..0xD230 (4096 u32 槽,
  值均为条目索引 <686, 3626 个 0xFFFFFFFF 空桶) → 哈希表只存索引,
  不含 off/stored/real 副本。

## 三、被测方案 (E1) 与条目表改动

- 数据: `C:\gr_build\tmp\en_strings_res_expanded.bin` (128,545B,
  经 lz77_decode.decode_entry 与盘上 EN stored 区逐字节一致) 写到 0x219000
  (2048 对齐, DE 数据区内)。
- 条目表仅改 EN 一条 (i=25, 记录 0x830+48*25):
  off: 0x0377E000 → 0x00219000; stored: 47,570 → 128,545; real: 不变。
- 自检全过: 总大小 58,300,882 不变; 685 个其余条目字段逐一相同;
  全档案字节差异仅限 [EN 记录 12B] + [0x219000, +128,545)。
- 组装: 复制 GR_K99.iso → `C:\gr_build\iso\GR_AB.iso`, splice_iso.py 拼入
  LBA 776286; 与基底逐字节 diff 确认差异只在 MENU.IMG 区内。

## 四、实验矩阵与结果 (gsrunner, needle 判据 + 快照)

判据: 健康 = 'WPNRPK74' 帧 200 内首命中 + 'PressSTARTbutton'/'Chooseyourprofil'
入内存 + 跑满帧数 + 画面正常推进。探针 2000 帧, 终验 24000 帧。

| 实验 | off | stored | real | 载荷 | 结果 |
|---|---|---|---|---|---|
| C0 基底对照 (GR_K99.iso) | 0x377E000 | 47570 | 128545 | 原始 | **PASS** 24000 帧, 全 needle 正常 |
| E1 方案本体 (裸 stored==real) | 0x219000 | 128545 | 128545 | 裸展开态 | **FAIL ×2 确定性卡死**: 帧 780 起 cdvd 静默、EE 停帧 (0% CPU), 两次命中数逐帧一致; 卡在"Accessing memory card"黑屏框 |
| E3 只覆盖四语言区数据 (不动表) | 0x377E000 | 47570 | 128545 | 原始 | **PASS** 2000 帧 (证明 SP 流程不消费 DE/ES/FR/IT 数据内容, 该区可牺牲) |
| E7 恒等子流框架 | 0x219000 | 128553 | 128545 | {128545}{128545}+本体 | **FAIL** 同 E1 死法 (软卡死, 帧走但游戏停滞) |
| E13 framed-lzo 压缩框架 | 0x219000 | 59145 | 128545 | 合法 LZO1X 单子流 (解码自检==基准) | **FAIL** 同 E1 死法 |
| E14 同 E13 换位置 (LOAD_NEW_2.RSB 区内) | 0x2C77000 | 59145 | 128545 | framed-lzo | **FAIL** 同 E1 死法 |
| E15 仅重定位 (原始 47,570B 压缩字节原样搬家) | 0x219000 | **47570** | 128545 | 原始 | **PASS** 2000 帧 (重定位本身安全) |

E1 曾重试一次 (任务预案"cdvd 偶发挂起重试"), 两次停帧位置/命中数完全一致,
且同日基底对照顺利跑满 24000 帧 → **排除偶发, 确定性由补丁引起**。

## 五、关键诊断证据 (cdvd.log, "帧 LBA" 记录)

1. 引擎读 EN 条目是 **从 off 向前预留头的固定 32 扇区 (64KB) 窗口流式读**
   (基底: 0x377E000-0x2000 起, 1+24+7 三段完成 32 扇区), 读完才继续后续流程。
2. E7 与 E13 载荷完全不同 (恒等帧 vs LZO 帧), **cdvd.log 逐字节一致**:
   同样从 0x218000 起, 都恰在读满 24/32 扇区 (止于 0x223800) 后永远静默
   → 死亡与载荷内容、stored 大小数值均无关, 是"重指向条目的窗口读中途夭折"。
3. E14 (不同 off) 也在窗口读中途死亡 (4/32 扇区) → 与具体位置无关。
4. 死后 cdvd 子系统整体静默 (连无关读取都没有), IOP 侧挂起 → 游戏停在
   依赖 IOP RPC 的存储卡检查画面; E1 的 EE 更进一步完全停帧。
5. 全部失败跑中 IOP 侧 needle ('WPNRPK74' iop) 命中为 0 (基底约帧 260 即有)
   → strings 从未成功进入 IOP。
6. 注意: E1 失败跑里 WPNRPK74 帧 150 的 EE 命中**不能**证明新 RES 解析成功
   (来源不可区分), 实际上新载荷从未被完整读取过。

## 六、结论

**「EN_STRINGS.RES 未压缩写回 (stored==real) + 档案条目重指向」不安全。**
确定性导致引导在标题/存储卡阶段挂死 (cdvd 对该条目的 64KB 窗口流式读
中途夭折), 换载荷框架 (裸/恒等帧/合法 LZO 帧) 与换位置 (0x219000 /
0x2C77000) 均无法规避。

通过对照实验额外确立的边界 (对后续方案极有价值):

1. **牺牲区覆盖安全**: 四语言 DE/ES/FR/IT 数据区 (0x218B00..0x24D5F8)
   在美版 SP 流程中被引擎扫过 (帧 ~545 起, ~1793 扇区) 但内容损坏无任何
   影响 (E3)。
2. **条目重定位安全**: 保持 stored/real 不变, 把原始压缩字节搬到任意
   2048 对齐位置完全正常 (E15)。
3. **毒变量 = stored 字段偏离原值 47,570**: 一旦 stored>原值 (无论载荷
   合法性), 该条目的读取必死。机制未知 (引擎内部校验或 IOP 读取路径
   约束), 需 IOP 追踪或真机验证; 若将来要攻破, 优先排查:
   - IOP 侧是否按编译期/首扫期常量给 strings 条目分配读取缓冲;
   - 条目表是否有两阶段读取 (先扫原表、后按新表读数据) 产生一致性校验。
4. 因此现阶段可行的写回路线收窄为: **off/stored/real 三个字段一律不动,
   仅在原 47,570B 槽位内原地覆写** — 要求压缩后 (含子流框架) ≤47,570B。
   原盘 minilzo 比率 37.0% (47,570/128,545); 现有贪心压缩器 46%
   (59,145B) 尚不达标, 需升级压缩器 (加 M2 短匹配+懒惰匹配等) 后再验。
   另: 首次放中文时务必同时做"原内容原槽位重压缩写回"的 A/B 引导测试
   (E15 已证明搬家安全, 可把新压缩流放四语言区做对照, 但表字段仍不得动)。

## 七、产物清单

| 文件 | 说明 |
|---|---|
| `C:\gr_build\tmp\MENU_ab.img` | E1 方案镜像 (自检通过, 实测不安全) |
| `C:\gr_build\iso\GR_AB.iso` | E1 拼盘 (GR_K99.iso + MENU_ab.img @LBA 776286) |
| `C:\gr_build\tmp\MENU_e3.img` / `iso\GR_E3.iso` | E3 牺牲区覆盖对照 (PASS) |
| `C:\gr_build\tmp\MENU_e7.img` / `iso\GR_E7.iso` | E7 恒等子流框架 (FAIL) |
| `C:\gr_build\tmp\MENU_e13.img` / `iso\GR_E13.iso` | E13 framed-lzo 重指向 (FAIL) |
| `C:\gr_build\tmp\MENU_e14.img` / `iso\GR_E14.iso` | E14 换位置对照 (FAIL) |
| `C:\gr_build\tmp\MENU_e15.img` / `iso\GR_E15.iso` | E15 仅重定位对照 (PASS) |
| `C:\gr_build\dumps\ab_res / ab_ctl / ab_e3 / ab_e7 / ab_e13 / ab_e14 / ab_e15` | 各跑 grlog/gs.log/cdvd.log/快照 |
| `C:\gr_build\tmp\ab_build_img.py, ab_check_img.py, ab_build_e3/e7/e13/e14/e15.py, ab_list_entries.py, ab_gap_check.py, ab_hash_inspect.py, ab_identity_check.py, ab_cdvd*.py` | 构建/自检/分析脚本 |

基底 GR_K99.iso 与 han_v2 下既有文件均未改动 (本文件为 han_v2 内唯一新增)。

---

## 八、ZH3: 真实字形格汉字绘制 + GR_ZH3 实测全通过 (2026-09-12)

### 8.1 显示链路真因 (最终结论)

字符串高位字节被引擎按 **Latin-1 直映射**进字库 atlas 的字形格:
GBK 串的每字节 b → 引擎查 b 号码位的字形贴屏。zh2 实证: 换弹=D2 D3 屏显
`ÒÓ©ª`, 切换武器=D4 D5 D2 D3 E5 E6 D A DB 屏显 `ÔÕÒÓåæÚÛ` —— 每个高位
字节都精确落在同码位 Latin-1 字形上。因此**只要把汉字画进 atlas 的对应
码位格子, 高位字节即显示为汉字**。FONT.RES 的高码位记录为过期数据 (勿用)。

### 8.2 atlas 结构与三 face 格子表 ( artifacts\COMMON_PAK.bin 表面 @0x1069, 512x512 线性 8bpp )

atlas = 三个字号 face, 每 face 的字形按 specimen 串序 (ASCII 0x20-0x7E →
0x7F-0xA0 占位虚线 → Latin-1 0xA1-0xFF) 逐格左→右、条带间换行烘焙;
**条带跨 face 共享 y 带** (如 y110-127 同时含 T1 末行与 T2 ASCII 首行)。
调色: 背景=31(透明), 笔画核心=0, 右缘亮边=82-89 (引擎反向 alpha)。
部分字形整支只有亮边值 (如 ­ 0xAD 软连字符) —— 用 A<26 做掩码会漏格。

行带实测 (行墨水剖面): T1 = y54-75 / y80-101 / y110-127; T2 = y159-178 /
y185-218 (+descender); BIG = y352-393 / y394-434 / y436-476。

**T2 face (菜单标签字号, 最重要)**, 条带2=0xA1..0xD2 (¡@x21-28, 2 碎片),
条带3=Ó@0-10(† 为前条带孤儿格, Ó 实为 x20-32)..ÿ@440-449:
锚点: ¡@x21(非任务早先估的 40), ©(环形有孔)@x91-104, Æ(最宽)@x385-401,
Ç@x402-413, ð(0xF0, 易误读为 ñ)@x306-315, ÷@x374-383, ø@x384-393,
ù@x394-402, ú@x403-411, û@x412-420, ü@x421-429, ý@x430-439, þ@x440-449,
ÿ@x450-459 (FF)。**0xD6(Ö) 无格** (Õ 与 × 之间无格); µ(0xB5) 之后一格为
™ 形状 (占 0xB6 位, T1 同); 条带尾部 x484-512 = FF 后孤儿格 (Win-1252)。
条带2 与 条带3 的总格数 = 50 + 45(缺Ö)=94。

**T1 face (帮助条小字)**: 条带1=¡@x66(2 碎片)..Ë@505-512(截断); 条带2=Ì@x20..ù@x489-499, ú@x500-509; 条带3=û@x5-17, ü@x20-28, ý@x29-39, þ@x40-49, ÿ@x50-60。锚点: µ@x245-253, Æ@x438-456 (6 个 A 系列后), ©@x137-150, ®@x185-198。88 目标码全有格 (含 Ö@131-139, 与 T2 不同 T1 有 Ö)。

**BIG face (大标题)**: 条带(316-351)=ASCII 尾+虚线占位+¿?+À@x358-377,
Á@379-403, Â@406-430, Ã@433-457, Ä@460-484, Å@487-511; 条带(394-434)=
Æ@x21-45, Ç@x48-82, È@83-108, É@109-129, Ê@130-150, Ë@151-171, Ì@172-183,
Í@184-192, Î@193-202, Ï@203-211, Ð@212-236(2 碎片), Ñ@237-262, Ò@263-284,
Ó@285-312, Ô@313-340, Õ@341-368, Ö@369-396, ×@397-424, Ø@425-441, Ù@442-469,
Ú@470-491, Û@492-512(截断); 条带(436-476)=Ü@x20-41..ð(0xF0)@x415-426,
其后为占位虚线, **ñ(0xF1)-ÿ(0xFF) 无格**。¡(0xA1)..¾(0xBE) 无格 (仅 ¿? 与
À 起)。88 目标码中 46 个有格。

验证方法: 每条带渲染「run 边界蓝线+码位标签」标注图逐格目视核对
(tmp/zh3/anno_*.png); 关键易错点 = ð/ñ、¦§ 粘连、¡¢ 碎片、¾ 后的
软连字符亮 bar、WIN-1252 孤儿格 (†@T2 条带2 x0-10 等)。

### 8.3 重绘策略 (han_v2\COMMON_PAK_ZH3.bin, 400,659B)

以 artifacts\COMMON_PAK.bin 为底 (干净)。每汉字 h 的 [c1,c2] 在每个有格
face: c1 格 → 整格清 31 + 贴 simhei (字号=条带高-2, 宽超限水平压缩居中,
texel=round(31*(1-alpha))); c2 格 → 清 31 (空格)。109 个 c1 格贴字 +
111 个 c2 格清空 + 2 处条带头部清空 (截断格回绕采样区: T1s4 x0-6,
T2s3/BIGr5 x0-20)。透视频 = painted_T2s3/T2s4/T1s3/T1s4/T1s5/BIGr*.png,
逐格可读 (切@D4, 组@D8, 器@DA, 息@DC, 图@DC, 界@F4, 上@F6, 限@F8, 枪@FA,
雷@FD ...)。

### 8.4 组装毒点与修复 (本次最大坑)

早期构建 (zh2_try1/try2 同因) 在**帧 740** 确定性挂死 —— 时机 =
Options→Controller 页首次大批取串。二分定位 (K99 基底 / +PAK / +RES /
组合): **毒 = EN_STRINGS.RES 的单子流大帧**。引擎 RES 解析器按
`{u32 plen}{u32 osz}` 子流链**延迟解码** (每页用到的组即时解), 单个
128,545B 大子流使解析在第一重度用串页失控挂死。最终 zh2 (zh2c 构建)
用 8 子流 blob 所以通过; zh2_try1/2 与 zh3 早期构建都用单子流压缩帧。

修复配方 (ab_build_zh3.py 终版):
1. RES 内容 = 当前 res_zh 译文容器, **credits 组(组61)整组条目清空**
   (组内无 88 目标码位, 零损失; 旧"nocredits"配方 = 尾部粗截断, 会误伤
   键/面/界/雷等标签串, 弃用), 尾部按 real=128,545 补零;
2. 展开态按 **16384×7 + 13857 分块**, 每块独立 LZO1X (level7+m1+m4),
   串成 {plen}{osz} 链 = **47,127B ≤ 47,570B** 槽位限;
3. **槽尾 443B 不填零**: menu_working 的 K99 TXT 数据 @0x378A000 位于
   RES 槽位 stored 尾界后的松弛区、且在引擎 RES 读取窗口内, 零填充会
   摧毁 TXT 头部 (TXT 数据本身从未被 RES 帧覆盖, 勿再"修复"它);
4. 条目表三字段绝对不动; TXT 条目 off 亦不动 (引擎疑似从窗口偏移取
   TXT, off 重定向方案已试, 不需要)。

### 8.5 GR_ZH3 实测结果

- ISO: `C:\gr_build\iso\GR_ZH3.iso` = GR_K99.iso + MENU_zh3.img @LBA 776286
- 26000 帧跑: **跑满, exit=0**, WPNRPK74 needle 3,190 次命中, 419 快照
  (dumps\zh3)。早期构建的帧 740 挂死彻底消失。
- 40000 帧跑 (dumps\zh3_run3b): 跑满。流程 = 开机存储卡对话框(无输入
  期, ~f600-3100) → 片头 → 标题(start@11400 跳片头) → Name Entry
  (档案流按键半命中) → 主菜单(Options 高亮 @f26226, 与 zh2 同帧位) →
  **Options→Controller 页 @f32860(pad1)/f33480(pad3)**。
- **视觉判定 PASS**: 同一页 zh2 显示 mojibake (`ÊÊÐÂ`/`ÒÒ©ª`/
  `ÒÒÒÒ¡¢ÌÌ`/`ÔÕÔÓåæÚÛ`) 的位置, GR_ZH3 显示**汉字字形** (成对编码:
  c1 汉字格 + c2 空格, 每汉字两格宽); 放大裁剪
  `C:\gr_build\tmp\zh3\hanzi_left.png` / `hanzi_right.png` 可见多行
  2/4 字汉字标签, 未翻译条目保持英文, 与 68 条译文覆盖一致。

### 8.6 产物

| 文件 | 说明 |
|---|---|
| `han_v2\COMMON_PAK_ZH3.bin` | 真实字形格绘制字库 (109 c1 贴字+111 c2 清空) |
| `han_v2\COMMON_PAK_ZH3_T2only.bin` | 二分用 T2-only 变体 (已证明无毒) |
| `C:\gr_build\tmp\ab_build_zh3.py` | 终版组装脚本 (8 子流配方+自检 BUILD PASS) |
| `C:\gr_build\tmp\MENU_zh3.img` | 成品 MENU 镜像 |
| `C:\gr_build\tmp\en_strings_zh_8sub_v3.bin` | 8 子流 RES blob (47,127B) |
| `C:\gr_build\iso\GR_ZH3.iso` | 成品盘 (跑满 40000 帧) |
| `C:\gr_build\dumps\zh3, zh3_run3b` | 实测快照 (汉字渲染证据) |
| `C:\gr_build\tmp\zh3\anno_*.png, painted_*.png, hanzi_*.png` | 格子表标注图/绘造视/实拍放大 |

基线产物 (menu_orig/working、GR_K99.iso、res_zh、pairs 系) 未改动。

---

## 九、0x80-0x9F 控制区渲染实验 (C1 系列, 2026-09-12)

### 9.1 目的与方法

判定 0x80-0x9F 这 32 个码位能否显示字形 (若可, 字库容量 89→120)。
方法 = zh3 成功配方 + **唯一内容差异**: 把 zh3 blob (en_strings_zh_8sub_v3.bin)
解码回展开态容器 (128,545B; 结构 = res_zh 译文容器 + G62 credits 整组清空 +
尾部补零, 与 EN_STRINGS_ZH.bin 逐组比对仅 G62 差异已验证), 将其中 **1 条条目
G65.I116** (Reload Weapon→换弹 `D2 D3 A9 AA`, zh3 快照 f33480 证实显示于
Options→Controller 页右列行2) 的内容替换为诊断串, 重新按 16384×7+13857
分块 LZO1X (level7+m1+m4) 压缩写回原槽位。压缩管线自证: 重压**未修改**容器
逐块字节数与 v3 完全一致 (合计 47,127B) → 与 zh3 唯一差异 = 该条目内容。

自检全部通过: IMG 总大小/686 条目表字段不动; vs 基底 diff 仅 COMMON.PAK+RES
帧链; vs MENU_zh3.img PAK 区逐字节相同 (PAK 不动); 槽尾不填零。

诊断串 V1 (任务 spec): `A` + 0x80..0x9F 每字节跟 `.` + `B` + 对照字节
`C0 C8 D2 A9` (= 盘/右/换/弹 四个已绘汉字 c1 格, 链路对照)。70B。

### 9.2 实验矩阵与结果 (gsrunner, zh2 nav 复用, 健康=WPNRPK74 早命中+跑满)

| 轮 | ISO | G65.I116 内容 | 结果 |
|---|---|---|---|
| V1×2 | GR_C1.iso | 70B 全区诊断串 | **FAIL×2 完全相同**: 帧 2816、cdvd 末读 LBA 799181 (LOAD_NEW_2.RSB 区流读中途) 后永远静默, 2852 起黑屏但 EE needle 持续命中 (帧在走、游戏假活) |
| 对照 | GR_ZH3.iso 重跑 (zh3_ctl) | 原 换弹 | **PASS** 跑满 40000 帧, f33480 Controller 页汉字正常 → 环境无漂移, 毒 = 诊断串内容 |
| B1 | GR_C1_c1b.iso | ASCII 孪生 72B (`A`+`=`.` ×32+`B`+对照) | **PASS** → 长度/结构/点/对照字节全部无毒 |
| B2 | GR_C1_c1d.iso | `A`+0x80-0x8F 点分+`B`+对照 (38B) | **FAIL** 同 2816/LBA 799181 |
| B3 | GR_C1_c1e.iso | `A`+0x90-0x9F 点分+`B`+对照 (38B) | **FAIL** 同 2816/LBA 799181 |
| B4 | GR_C1_c1f.iso | `A`+单字节 0x80+`.`+`B`+对照 (8B) | **PASS 跑满 40000 帧** → 0x80 单独无毒 |
| B5 | GR_C1_c1g.iso | Win-1252 已定义 23 字节 (剔除未定义 81/8D/8F/90/9D 与 0x80) | **FAIL** (2852 起黑屏) → 已定义子集仍含毒 |

判定协议: 死亡在帧 2816 (boot 末段), 只需 ~8000 帧即可判; 2914 点亮 (片头)
= 活。所有死亡跑的 cdvd.log 与 zh3 基线逐字节相同 40,058 行后同点夭折,
确定性挂死 (非 cdvd 偶发)。

### 9.3 关键发现

1. **引擎在 boot 末期 (~帧 2816, 存储卡检查后、LOAD_NEW_2.RSB 装载流中) 即
   解码并预处理整个 RES 容器** —— 远早于任何菜单显示。字符串内容含毒字节
   = 确定性 boot 挂死 (cdvd 静默+黑屏假活)。此前「帧 740 Controller 页取串
   挂死」的旧结论应修正为: 挂死发生在 boot 期容器预处理, 与页面无关
   (8 子流之所以能过, 是因为全链无 0x80-0x9F 字节, 而非"延迟解码躲过")。
2. **0x80 渲染判定 (c1f 快照 f33480 放大)**: `A`[80]`.` 之间**无墨且无空位**
   (A 墨尾 x381 → 点墨头 x382, 零间隙) → **0x80 被引擎跳过**: 不出字形、
   不占格、不吃后续字节 (点与 B 完好)。atlas 即便有 0x80 格也不会被取用。
3. **毒字节下界**: 0x81-0x8F 至少 1 个毒, 0x90-0x9F 至少 1 个毒 (两半双死),
   且 c1g 证明剔除 Win-1252 未定义字节 (81/8D/8F/90/9D) 后仍毒 → **毒不止
   未定义字节**; 结合 0x80 安全, 毒 ⊆ 0x81-0x9F 且两半各有。4 轮二分预算
   (c1d/c1e/c1f/c1g) 用满, 未再细分。
4. 机制假说 (供后续 RE): 0x80-0x9F = Latin-1 **C1 控制区**, 引擎字符串
   预处理对 <0xA0 字节走特殊表 (0x80=跳过、若干码位 handler 坏/成对解析)。
   SJIS 前导字节理论 (0x81-0x9F 为 lead) 与 "zh2 中 0xE5 0xE6 按独立格渲染"
   矛盾 (标准 SJIS 会配对吞字), 故不是标准 SJIS 解码; 但 "0x92+'l' 合法
   配对不炸、0x92+'.' 非法配对炸" 亦无法排除 (未单测 0x92)。
5. **EN 数据普查 (字符串内容层)**: 0x80-0xA0 中唯一被 EN 原文用作字符的是
   **0x92 (弯引号) 14 处** (MENU 份 G12-G18 训练简报 "you'll" 类; GR.IMG 份
   15 处)。其余 (83/86/88/8E/8F/91/96/99/9A/A0) 全部只出现在 u32 长度字段
   (结构层), 与渲染无关。武器/物品名表 (EN_STRINGS_plain_full.bin) 无高位
   字节。

### 9.4 容量结论

**0x80-0x9F → +0 字。** 0x80 被跳过不出形; 0x81-0x9F 含 ≥2 个分布两半区的
毒字节, 串中出现即 boot 挂死, 不能用作汉字槽位 (逐字节毒清单需引擎 RE 或
更多二分轮, 性价比低)。0x92 虽为 EN 在用码位, 但其格**不可重绘** (训练文本
未翻译时需原样显示弯引号), 且其单字节安全性未单独验证。字库扩容只能走
FONT.RES/新 atlas 通道, 0xA1-0xFF 的 89 格仍是现有上限。

### 9.5 产物

| 文件 | 说明 |
|---|---|
| `C:\gr_build\tmp\ab_build_c1.py` / `ab_build_c1x.py` | V1 构建脚本 / 参数化构建器 (tag+hex) |
| `C:\gr_build\tmp\c1\zh3_expanded_decoded.bin` | v3 blob 解码 = zh3 展开态容器真身 (128,545B) |
| `C:\gr_build\tmp\c1\container_c1*.bin` / `en_strings_c1_*.bin` | 各轮容器与 8 子流 blob |
| `C:\gr_build\tmp\MENU_c1*.img` / `C:\gr_build\iso\GR_C1*.iso` | 各轮镜像 (ISO 已按约束跑完即删) |
| `C:\gr_build\tmp\c1\c1f_f33480_full.png` / `c1f_row2_10x.png` | 0x80 跳过判定 + 汉字对照证据 |
| `C:\gr_build\tmp\c1\zh3ctl_f33480_full.png` / `c1V1_f33480_black.png` | 对照 PASS / V1 黑屏对比 |
| `C:\gr_build\dumps\c1, c1_c1b, c1_c1d, c1_c1e, c1_c1f, c1_c1g, zh3_ctl` | 各轮 dump |

han_v2 既有产物未改动 (本节为唯一追加); res_zh\EN_STRINGS_ZH.bin 只读未动。

## 九、FONT.RES 编辑翻案实验 (2026-09-12)

**假说**: 历史「FONT.RES 任何改动=挂死」的结论全部产生于 LZO1X 破解之前——
当时写回用的是错误的「计数格式」编码器, 挂死原因很可能是垃圾压缩流而非改动
本身。本实验用已验证的 LZO1X 工具链重测: 恒等重压缩写回 (T1) + 逐字段微编辑
语义探测 (T2)。

### 9.1 T0 基线

menu_orig\MENU.IMG @0xB9120 取 4,421B 存储字节 → lz77_decode.decode_entry 解码
= **7,222B, 与 artifacts\font_rsfb_engine.bin 逐位一致**。帧结构
`{u32 plen=4413}{u32 osz=7222}{payload 4413B}` 恰好填满槽位 (尾 0 字节)。

### 9.2 T1 恒等重压缩写回 (翻案主实验)

- lzo1x_c.py 全 LEVELS(3..7)+M1 最小 4,439B, **超 4,413B 上限 26B**。
  令牌直方图对比定位差距: 我们 49 个 M3(3B 远距令牌) vs 原盘 23+4 个——
  原盘 minilzo 更偏好近距 M2/M4A。
- 为此写 **DP 最优解析压缩器 `C:\gr_build\tmp\ft_dpc.py`** (语法=原盘实证
  子集 M2/M3/M4A/字面量段/EOF, 不用 M1/M4B; 状态机 ctx∈{R,B,A} 对齐
  lz77_decode; 匹配后置字面量 k 计真实字节): 7,222B → **payload 4,410B
  (61.06%, 比原盘 4,413B 还小 3B)**, lz77_decode 双模式 (out_size/自由)
  自检逐位通过。
- 写回: `{plen=4410}{osz=7222}{payload}` = 4,418B, 槽位尾 3B 填 0x00;
  条目表 off/stored/real 三字段不动; 组装 GR_FT_ID.iso (splice_iso,
  LBA 776286, 前置自检: 新槽位解码 == font_rsfb_engine.bin)。
- **实测 (15000 帧, nav 2800cross/11400start): 存活**。exit=0 跑满,
  WPNRPK74 needle 帧 150 命中 (与原盘基线同帧), Name Entry 键盘画面
  正常 (dumps\ft_id)。**恒等重压缩 FONT.RES 不挂死 — 假说证实**,
  挂死成因锁定为旧 count-format 编码器的垃圾压缩流。

### 9.3 T2 微编辑语义探测 (每次只改一处, 同 nav 重跑)

记录表实测起点 0x5F、步长 10B、base 字符 0x20
(**任务书里 `@0x5f+(0x41-0x20)*10=0x26F` 是算术笔误, 0x41 → 0x1A9**;
链式证据: 相邻记录 x0(c+1)==x1(c) 全表衔接, 如 @.x1=A.x0=0x135, V.x1=W.x0=0x50)。
10B 记录 = 5×u16 `{x0, y0, x1, y1, tag}` (x0/x1=图集采样列, y0/y1=行带:
A-D 在 y 0..26 行, V-Z 在 26..52 行, 行高 26 = 0x55 处 u32)。

| 轮 | 改动 (@0x1A9, 'A') | 帧数/exit | needle | 视觉观察 (同帧 f14942 全图 diff) | 语义 |
|---|---|---|---|---|---|
| T1 | 无 (恒等重压缩) | 15000/0 | f150 | 全屏零差异预期, 键盘正常 | — |
| B1 | u16#1 x0: 309→307 | 15000/0 | f150 | **仅大键盘 'A' 键帽 140px 变化**: A 左侧出现 2px 外来像素竖条 (=前一字符 '@' 右缘), A 本体与屏幕位置不变 | x0=图集采样左缘 |
| B2 | u16#3 x1: 323→321 | 15000/0 | f150 | **仅 'A' 129px 变化**: A 右侧被截 2px, 变窄 | x1=图集采样右缘 |
| B3 | u16#5 tag: 0x0A00→0x0B00 | 15000/0 | f150 | **仅 'B' 键帽 138px 变化: B 字形整体左移 ~1px, 'A' 自身不动** | tag 非自身矩形, 作用于相邻(后一)字符绘制位置 (字距/承前间距类度量) |

B4 ('W' x0-3) 按任务条件跳过 (B1-B3 已有明确视觉变化)。标题 "Name Entry"
与小字行的 'A' 在 B1/B2 中零变化 → 它们用 default/huge face 的独立记录表,
0x5F 表只服务 large face (Name Entry 键盘)。

### 9.4 结论与安全写回规程

1. **FONT.RES 完全可编辑**: 恒等重压缩与 3 处独立微编辑 (4 张盘) 全部
   15000 帧跑满、needle 帧命中位与原盘一致、画面正常。任何「改 FONT.RES
   必挂死」的历史结论作废; 引擎只认合法 LZO1X 流, 不校验压缩器签名。
2. 记录语义: `{x0,y0,x1,y1,tag}` — 前四项=图集矩形 (改即字形重指/裁剪,
   可用于把汉字字形注入图集后重指记录), tag=相邻字符位置度量 (改它会
   扰动后一字符, 注入时保持模板字符 tag 原值即可)。
3. **安全写回规程**: (a) 只动 7,222B 展开内容, 条目表 off/stored/real
   绝对不动; (b) 编辑后用 ft_dpc.py DP 压缩, payload 必须 ≤4,413B
   (帧 8+plen ≤ stored=4,421, 槽尾 0x00 填充); (c) 保持单子流布局,
   `{plen}{7222}{payload}` 一帧; (d) 写回前 decode_entry 槽位自检 ==
   编辑内容; (e) splice_iso 原位拼盘, gsrunner 跑盘验证 (毒盘判据:
   帧 ~740-780 停滞黑屏; 本实验 4 盘零挂死)。
4. 实验产物: `C:\gr_build\tmp\ft_dpc.py` (DP 压缩器), `ft_payload_id.bin`,
   `ft_expanded_B1/B2/B3.bin`, `ft_build_edit.py` (微编辑组装),
   `ft_run.py` (运行器), `ft_diff.py/ft_crop.py` (同帧全图 diff/裁剪),
   dumps\ft_id / ft_B1 / ft_B2 / ft_B3 (快照证据)。实验 ISO 已按约删除。

---

## 十、ZH5: 菜单汉字 12px→16px 分辨率提升 + 单字节字符集定版 (2026-09-12)

### 10.1 结果速览

| 项 | ZH3 (旧) | ZH5 (本轮) |
|---|---|---|
| 菜单标签汉字格宽 | ~10px (重音字母残格, 双字节槽位对=2格/字) | **16px 等宽** (FONT.RES 记录重排) |
| 字形来源 | SimHei 矢量缩进残格 | **SimHei 16px EBDT 原厂真点阵** (二值 0/31) |
| 编码 | GBK 对 (c1 汉字格+c2 空格), 2 字节/字 | **单字节** 1 字/码位, 89 字符集 |
| 字库容量 | 44 字 | **89 字** (32 译文用字 100% + practical89 核心按钮字) |
| 新增按钮条目 | 无 | Accept→确认 / Cancel→取消 / Back→返回 / Quick Save→快速保存 / Quick Load→快速载入 (8 条) |
| 实测 | PASS | **PASS** (40000 帧跑满 exit=0, WPNRPK74 4232 次) |

### 10.2 FONT.RES 全结构破解 (本轮核心成果)

MENU.IMG FONT.RES (stored 4,421 @0xB9120, 展开态 7,222B = artifacts\font_rsfb_engine.bin)
= RSFont 资源 `{u32 20}{"new_font_revised.rsb"}{u32 3 faces}`, 三 face 顺序:

| face | 头偏移 | 记录表 | 行带 (v0) | 用途 (实测) |
|---|---|---|---|---|
| large | 0x1C | **0x5F** | 0/26/52/78/104 (5 行×26px) | Name Entry 大键盘 (T2 实验实证) + 帮助条小字 (T1) |
| default | 0x91D | **0x962** | 104/130/156/182 (4 行×26px) | **菜单标签/按钮提示 (主战场)** |
| huge | 0x1220 | **0x1262** | 182/224/266/308/350/392/434 (7 行×42px) | 大标题 (BIG) |

- 记录 10B = 5×u16 `{u0, v0, u1, v1, adv}`; adv 单位 = **1/256 px** (0x1000=16.00px;
  T2-B3 实证 +0x100 ≈ 后字位移 1px)。每表 **223 条有效记录 (0x20-0xFE)**。
- **引擎采样矩形 = (u0+20, v0)-(u1+20, v1), 即 u 恒 +20px** (v 不加)。
  证据: ①三 face 全部 16 条行带逐带"谷点对齐"最优偏移 = +19/+20;
  ②default 表 0xB1/0xB5/0xC6/0xD2/0xE7/0xF1 格 +20 与 zh3 实测墨迹逐像素相等;
  ③zh3 在 +20 处重绘上屏成功。0xA1-0xBF 在 huge face 的"无格"实为 2px 占位虚线格。
- COMMON.PAK 纹理 = `new_font_revised` 512×512 8bpp @0x1069 (PAK 头 {len}{name}{u32 w}{u32 h});
  调色 背景=31(透明)/笔画=0, 引擎反向 alpha。ASCII 行带 y5-23/30-50/110-127/134-152
  用 A<26 阈值测不到 (亮边 82-89), 全阈值 (v≠31) 才可见 —— zh3 行带剖面漏检的主因。
- 保护区 (引擎只有 EN 语言): ASCII 0x20-0x7E 全部 + 0x92(弯引号) + ®±µçñ
  (0xAE×23 条/0xB1×7/0xB5×21/0xE7×1/0xF1×1, 见 tmp\hanzi_demand\report.md)。

### 10.3 布局设计 (阶段1)

89 码位 × 16px 格, default 表记录改为 `{sx-20, v0, sx-20+16, v1, 0x1000}`, 槽位分配:

| 行带 | paint 区 (y) | 槽数 | 说明 |
|---|---|---|---|
| A | **y482-508** (atlas 尾部空带 y478-511) | 30 | 零冲突首选 |
| B | y156-182 (default Latin-1 行1) | 26 | 覆盖非保护重音 |
| C | y182-208 (default Latin-1 行2) | 28 | ç(233-242) ñ(316-325) 让位 |
| D | y52-78 (large 行1) | 6 (共26) | 记录仍属 default face, 指到哪画到哪 |

逐码位布局表: `C:\gr_build\tmp\zh5\layout_zh5.txt` (89 行, 含 paint 槽与记录五元组)。
重压缩: ft_dpc.py DP → **payload 4,393B ≤ 4,413B** (帧 4,401B + 20B 填充),
lz77_decode 双模式自检过。自检: 全文件仅 89 条目标记录共 485 字节变化。

### 10.4 血泪坑: default 表 0xFF"槽位" = 表尾 + huge 头 (第一轮挂死定因)

default 表 0x962 + 223 条×10 = 0x1218, 之后 8B 尾 (恰为 0xFF 半条记录
`ae 01 b6 00 b8 01 d0 00`) 紧接 huge 头 @0x1220 `{u32 4}{"huge"}`。
首轮把 文=0xFF 当普通码位写 10 字节记录 → **覆盖 0x1218-0x1221,
huge 名长度字段 04→55** → RSFontMgr 名字解析崩 → 字体系统全灭:
开机环正常渲染但 "Please wait!" 文字消失 (snap_f2914 对比 zh3 同帧),
流程停在环上 40000 帧不动 (EE 活、画面假活, 与 E1/c1 毒型不同的新毒型:
**字体资源解析失败**)。修复: 字符集收缩到 0xA1-0xFE (89 码), 0xFF 槽不写。
**教训: 三表的 0xFF 记录一律不存在, 任何表只可写 0x20-0xFE。**

### 10.5 字符集 v5 定版 (阶段3)

- 编码空间: 0xA1-0xFF 扣英文在用 5 格 (AE/B1/B5/E7/F1) 再扣 0xFF 非法槽 = **89 码**。
- 分配: 68 条译文用字 32 个全部入集 (31 个保留 zh3 GBK c1 码位, 有 从 B1 迁到 0xA2),
  其余按 practical89 顺序补足 → 核心按钮字 确认继续取消返回是否开关保存载入退出
  设置始暂停删除 全部在集 (码表见 tmp\zh5\charset_v5.json)。
- 76 条内容变更 (68 重编码 + 8 新增按钮条目 G58.I169/I728/I729/I734/I763/I768/
  G61.I048/I049, 组号=清单号-1), 展开态 payload 110,383→110,177B,
  8 子流 (16384×7+13857, level7+m1+m4) = **46,759B ≤ 47,570B** (余 811B)。
- 组装 (ab_build_zh3.py 配方 + FONT.RES 槽): menu_working 底 + COMMON_PAK_ZH5.bin
  + FONT.RES 槽 0xB9120 + EN 槽 blob, 槽尾不填零。自检全过: 总大小/686 条目表/
  差异白名单 (PAK+FONT.RES+EN 帧链)/TXT 头 16B 未动。

### 10.6 GR_ZH5 实测判定 (阶段4)

- ISO: `C:\gr_build\iso\GR_ZH5.iso` = GR_K99.iso + MENU_zh5.img @LBA 776286。
- gsrunner 40000 帧 (nav=dumps\zh2\nav.txt): **跑满 exit=0**; WPNRPK74 帧 150 首中
  (与基线同帧), 4,232 次; boot 环 "Please wait!" 文字正常 (f2914);
  主菜单 Options 高亮 @f26226 (与 zh2/zh3 同帧位, 流程零漂移)。
- **视觉判定 PASS** (f30000 Controller 页, 对照 dumps\zh3_run3b 同帧):
  - 汉字明显大于 zh3: 地图/切换队员/切换武器/换弹 16px SimHei 点阵, 行 ink 高 13px
    与英文行完全等高 (zh3 为 ~10px 碎片); 放大图 tmp\zh5\cmp_left/cmp_right/cmp_full_page.png。
  - **新字符集按钮字上屏**: 三页按钮提示 △=返回 ×=确认 (cmp_btnbar.png);
    Quick Save/Load 译名在列表更深处未入镜 (不在判定路径)。
  - 未译条目英文原样 (Zoom Out/Fire Weapon/...), ASCII 无任何损伤。
- BIG face (huge 表) 同步重绘: 0xC0-0xF0 区真实格 (行6/7) 贴 SimHei 矢量二值化;
  0xA1-0xBF 区原为 2px 占位虚线 (与 zh3 "¡-¾ 无格" 结论一致), 清虚线留空。

### 10.7 产物

| 文件 | 说明 |
|---|---|
| `han_v2\COMMON_PAK_ZH5.bin` | 16px 字库 (400,659B; 89 点阵格 + BIG 重绘, 表面外零改动) |
| `C:\gr_build\tmp\zh5\ft_expanded_zh5.bin` / `ft_slot_zh5.bin` | FONT.RES 展开态编辑产物 / 槽位帧 (4,421B) |
| `C:\gr_build\tmp\zh5\charset_v5.json` / `layout_zh5.txt` | 89 字符集码表 / 逐码位布局表 |
| `C:\gr_build\tmp\zh5\container_zh5.bin` / `en_strings_zh5_8sub.bin` | 展开态容器 (128,545B) / 8 子流 blob (46,759B) |
| `C:\gr_build\tmp\zh5_build_font_pak.py` / `zh5_build_res.py` / `zh5_charset.py` | 三段构建脚本 (含全部自检) |
| `C:\gr_build\tmp\MENU_zh5.img` / `C:\gr_build\iso\GR_ZH5.iso` | 成品镜像 / 成品盘 |
| `C:\gr_build\dumps\zh5` | 40000 帧实测 (645 快照 + gs.log) |
| `C:\gr_build\tmp\zh5\cmp_*.png, sheet16.png, row_A-D.png, atlas_zh5.png` | 对比/预览证据 |

基线产物 (menu_orig/menu_working、GR_K99.iso、res_zh、ZH3 系) 未改动。

---

## 十一、ZH6: 字形质量修复 (0xA1 码位诅咒实证 + 混合宽度 16/18/20px) (2026-09-12)

### 11.1 ZH5 缺陷逐格诊断 (先实证, 后动手)

用户报告: `返回`的**回**渲染近实心矩形、`切换队员`的**队**阝旁被削成细条+点、`地图`的图偏糊、`确认`尚可。
诊断链 (tmp\zh6_diag1..8.py, dumps\zh5\snap_f00033480):

1. **atlas 格零绘制 bug**: COMMON_PAK_ZH5.bin 里 回/队/图/员/确/认/切/换/返/择/选/继 全部 12 格
   与 PIL 直出 SimHei 16px EBDT 点阵**逐位相同** (diff=0)。绘制/布局链无缺陷。
2. **屏显像素取证**: Controller 页 quads 实测 — 切@x148 宽13 / 换@162 / **条@177 宽2-3px 且
   advance 仅 ~6px (其余字 12.8px)** / 员@183; 按钮栏 返@404 宽12.8 / **回@419 为 11×14 近实心
   圆角框**; 弹/武/器/地/图/确/认/返 全部正常。→ 同页同字库, 仅 0xA1/0xB2 两码位异常。
3. **原记录反查**: default 表 0xA1 原始记录 = (5,156,9,182,0x0800) —— ¡ 的 **2-texel 窄格**;
   0xB2 = (160,156,167,182,0x0600) —— ² 的 3.5-texel 窄格。而 0xA6 认 (原始宽 6) 渲染正常,
   排除"窄格码位一律坏"。

### 11.2 0xA1/0xB2 定源实验 (两轮图案 ISO, dumps\zh6d / zh6d2)

方法: 唯一变量 = FONT.RES 两条记录改指 + PAK 内多处识别图案 (P1 竖条纹/P2 棋盘/P3 ¡原位竖纹/
P4 ²原位横纹/P5/P6), 字符串与其它内容不动, gsrunner 跑到 f33480 读 Controller 页。

| 实验 | 0xA1 记录 | 0xB2 记录 | f33480 观察 | 结论 |
|---|---|---|---|---|
| ZH5 (基线) | (0,482,16,508) 指本格 clean 队 | (240,482,256,508) 指本格 clean 回 | 队=2×15px 细条 (advance~6px); 回=近实心框 | 0xA1 **不**按记录渲染; 0xB2 疑似但被 glow 糊化难判 |
| ZH6D | (0,508,16,511) 指 P5 3行墨条 | (482,478,492,510) 指 P6 竖纹 | 0xA1=细条(仍非 P5 块); **0xB2=2px 周期竖纹带, 顶端比正常字形高 ~3px (v0=478 实证!)** | **0xB2 严格跟随记录** (含 v0 微移); 0xA1 仍异常 |
| ZH6D2 | (240,482,256,508) 指 P2 棋盘 | (0,482,16,508) 指 P1 竖纹 | **0xA1=4texel 周期棋盘块 (全 26 行高)**; **0xB2=P1 竖纹** | **两码位都跟随记录; 0xA1 的失效条件 = u0=0 (三个 build 全部吻合)** |

结论 (实证三盘一致):
- **引擎逐字段消费 FONT.RES 记录 {u0,v0,u1,v1,adv}, 采样 = (u0+20,v0)-(u1+20,v1), adv 高字节
  (adv>>8) = half-px 推进量** — 无字段换位、无流解码分歧 (0xB2 的 v0 微移与棋盘/条纹周期均精确复现)。
- **码位 0xA1 在 u0=0 时渲染冻结**: 表现为采样 ¡ 原位区 (x25-29,y156-182, ZH5 后为聊格中列) 的
  2-3px 细条 + advance~6px (=原记录 adv 0x0800×0.8)。u0≠0 时正常。0xB2 无此问题 (u0=0 亦正常)。
  机制未明 (疑似引擎内部对首格/0 值记录的特判路径); 规避 = 0xA1 码位不用 + 全表禁 u0=0 记录。
- **回 的"实心矩形" = 16px→12.8px (scale 0.8) 线性采样 + 自发光 glow 把回的 1.5px 双框糊死**
  —— 纯 16px 分辨率极限, 非绘制/采样缺陷。图/员 同理 (糊但可辨)。

### 11.3 混合宽度布局 (修复本体)

- **码位回避**: 队 0xA1 ↔ 役 0xEC 换码 (役 = 译文零使用字, 0xA1 永不出现在字符串); 全部 4 带打包
  起点 x=21 (**u0≥1**, 消灭 u0=0 记录类)。回 保留 0xB2 (跟随记录已实证)。
- **混合宽度**: 格宽=adv=16/18/20px 三档, SimHei 18/20px EBDT 原厂 strike (PIL 自动命中, 二值):
  20px = 回队图员确弹 (用户点名 + 高频复杂); 18px = 选器换返择继续载速移视退息信武野服进制前放;
  其余 16px。屏显尺寸 = adv×scale: 16px 格 12.8px → 20px 格 16px (+25%), 点阵密度同步 +25%。
- 布局: 带 A/B/C/D (y482-508/156-182/182-208/52-78) 空闲 run 首适配, 保护区 (®±µçñ±1) 不变;
  带 D 首次启用 [41,183) 区 (与 ZH5 仅用 [20,105) 相比扩容, 覆盖 large face 非保护重音区, 政策同 ZH5)。
- 逐码位表: `tmp\zh6\layout_zh6.txt` (89 行, 含 size/paint/rec 五元组); 字符集: `tmp\zh6\charset_zh6.json`。
- FONT.RES 重排 89 记录 487B 变化, ft_dpc DP 压缩 **payload 4411B ≤ 4413B** (余量 2B)。
- PAK: COMMON_PAK_ZH6.bin = 净底重绘 (89 点阵格 + huge face 矢量同 ZH5 法), 表面外零改动。
- RES: 76 条译文按新码表重编码 (队 0xA1→0xEC), 8 子流 blob 46,759B ≤ 47,570B (与 ZH5 同量)。

### 11.4 GR_ZH6 实测判定

- ISO: `C:\gr_build\iso\GR_ZH6.iso` = GR_K99.iso + MENU_zh6.img @LBA 776286。
- gsrunner 40000 帧 (nav=dumps\zh2\nav.txt): **跑满 exit=0 (669s)**; WPNRPK74 帧 150 首中
  **4,245 次** (基线 ZH5 4,232 同量); boot 环 "Please wait!" 正常 (f2914);
  主菜单 Options 高亮 @f26226 (与 zh2/zh3/zh5 同帧位, 流程零漂移); ASCII 全程无损伤。
- **视觉判定 PASS** (f33480 Controller 页, 对照 dumps\zh5 同帧; 证据 tmp\zh6\cmp_*.png):
  - **队 (0xEC)**: 20px 点阵完整 阝+人, 细条消失 (cmp_dui_12x.png 下/上对比)。
  - **回 (0xB2)**: 20px 双框回, **内口清晰可辨**, 实心块消失 (cmp_hui_16x.png 右/左对比)。
  - **图/员 (20px) 与 18px 组**: 内结构明显更清晰 (cmp_zh5_zh6_leftcol/rightcol.png),
    换弹/切换武器 字面尺寸 +12~25%, 点阵密度同步提升; ASCII 与版面无任何损伤。

### 11.5 产物

| 文件 | 说明 |
|---|---|
| `han_v2\COMMON_PAK_ZH6.bin` | 混合宽度字库 (400,659B; 表面外零改动) |
| `C:\gr_build\tmp\zh6\ft_expanded_zh6.bin` / `ft_slot_zh6.bin` | FONT.RES 展开态编辑 / 槽位帧 (4,421B) |
| `C:\gr_build\tmp\zh6\charset_zh6.json` / `layout_zh6.txt` | 89 字符集 (队↔役换码) / 逐码位混排布局表 |
| `C:\gr_build\tmp\zh6\container_zh6.bin` / `en_strings_zh6_8sub.bin` | 展开态容器 / 8 子流 blob (46,759B) |
| `C:\gr_build\tmp\zh6_build_font_pak.py` / `zh6_build_res.py` / `zh6_diag*.py` | 构建/诊断脚本 (含全部自检) |
| `C:\gr_build\tmp\MENU_zh6.img` / `C:\gr_build\iso\GR_ZH6.iso` | 成品镜像 / 成品盘 |
| `C:\gr_build\dumps\zh6` | 40000 帧实测 |
| `C:\gr_build\tmp\zh6\cmp_zh5_zh6_*.png, sheet_zh6.png, atlas_zh6.png` | ZH5/ZH6 对比与预览证据 |
| `C:\gr_build\dumps\zh6d, zh6d2` | 两轮定源实验快照 (诊断证据) |

基线产物 (menu_orig/menu_working、GR_K99.iso、ZH5 系、res_zh) 未改动; 实验 ISO (GR_ZH6D/D2) 已删。

## 十二、ELF DBCS 补丁：绘制链 16 位化 + "字节对验收器"的发现 (2026-09-12)

> 详见 `han_v2/ELF_DBCS_PATCH.md`（指令级 diff、cave 清单、复现规程、全部 magic number）。
> 脚本/产物：`tmp/dbcs/`；dump：`dumps/db1`（Stage1）、`dumps/db3/db4/db6`（Stage2 各轮）。

### 12.1 Stage1（synth-byte 补丁）——PASS

- 补丁：仅 DrawString v1 三处（0x219BCC jal→cave、0x219DAC←lbu v0,0xDE(sp)、
  0x219DB0←addu s0,s0,v0）+ cave@0x26BEA0（39 条）：对 (lead,trail) 合成
  `synth=((lead−A1)×94+(trail−A1)+161)&0xFF`，步长 2 写 [sp+0xDE]。改动 151B。
- 测试盘：FONT.RES 0xA1-0xA8 ×3 face → 图集尾部测试格；G65.I116 → `地.图.武.器.切.换.确.认`
  (23B 对串+点分隔)；G43.I10 捐赠 10B。
- 实测（GR_DB1.iso，40000 帧）：**跑满 exit=0；WPNRPK74 f150 首中 3985 次；f33480
  Controller 页渲染 `地.图.武.器.切.换.`（synth 6/8 对逐一正确）；英文 17 标签+ticker
  与 zh6 逐像素一致（零损伤）**。18B 截断：第 7 对起不渲染（见 12.3）。

### 12.2 Stage2（16 位字符 ABI）——链路就绪，卡"对验收器"

- 补丁 v3（build_PS.py，560B）：四 cave（ds16/cw/cctc/sw）+ 七处槽位（lh/lbu 16 位化）+
  六处图标码立即数改正值；StringWidth 用最小对设计（ASCII 完全走原版路径）。
- 迭代史（全部有探针/全跑证据）：v1 sw cave 栈帧泄漏 → boot 挂死（f2817，cdvd 静默于
  LBA799173，与 §9 毒串签名同点；探针 E/M 单变量隔离定位）；v2 修复后零字形
  （四象限 + Name Entry 字母二分定位 sw"全串重写"有毒，字面模拟器证明算术全对 →
  机制未明，弃用）；v3 最小对 → Name Entry/主菜单/Controller 页英文全绿。
- **DBCS 串渲染 = 每对一个等宽短横**。四轮 face 归属排除（default448/large288/huge272/
  large448 全试，f2870 eeram 逐轮验证 FD rows/mSize/KD 记录正确落位、源串完整）+ 
  P-O2 cw clamp 点仪表（`-grdumpwin 33470 33482`）→ **短横与 FONT.RES 无关**：
  DBCS 字符确实到达 CharWidth ext 路径（ring 记到 idx=260）但该次 mSize 读=0，
  其余为 idx0 回退（回退宽 12 与截图节距 11.2px 吻合）。
- **结论：游戏存在 ELF 无关的"字节对验收器"**（字符串预处理层，f2816-2817
  LOAD_NEW_2.RSB 窗口活跃，即 §9 毒串同层）：已证 (A1,A1)..(A1,A6) 放行
  （Stage1 渲染汉字），(A1,A7+)、(A2/A3,·) 拒绝 → 输出 '-' 占位 glyph
  （每对一个，'.' 分隔符照排——db5 dash-dot 交替实证）。§9 的 0x80-0x9F boot 毒
  与 18B 截断均为该层的不同表现分支。

### 12.3 遗留开放问题

1. **对验收器的允许表与代码位置**（下一轮 RE：f2810-2850 窗口 dump 差分 + 
   LOAD_NEW_2.RSB 预处理函数定位）。放行全部 (A1-FE,A1-FE) 后，
   绘制链（本报告四 cave）即可支撑 224+ DBCS 槽。
2. Stage1 18B 截断：与验收器拒绝第 7 对 (A1,A7) 吻合；亦可能与标签槽宽
   （per-char x 游标剔除 0x219D14）复合，待验收器解决后自然消除。

### 12.4 容量与路线

- 单字节 89（ZH6）+ 对验收器窗内少量对（(A1,A1)-(A1,A6) 6 字已证）= 当前可交付。
- 验收器放行后：large face rows14 = 448 记录（idx 224-447 = 224 DBCS 槽），
  展开 6902-7062B ≤ 7222B、DP payload 3165-3824B ≤ 4413B、atlas 模式 A 241 格。
- face 归属实证：Controller/菜单标签样式(2-5)绑 **default** face（回退宽 12 实测；
  f2870 eeram 绑 large——两个时点读数不同，face 与样式的绑定需按 UI 屏分别确认，
  全量盘应三 face 同步扩容或按屏分配）。
