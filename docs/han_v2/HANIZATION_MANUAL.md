# HANIZATION_MANUAL.md — 《幽灵行动》(PS2) 汉化工程总手册

> 对象：《Tom Clancy's Ghost Recon》(USA, SLUS-206.13, Red Storm / 育碧上海 "ike" 引擎)
> 交付状态：**GR_ZH7 全量中文盘实测 PASS**（gsrunner 40,000 帧，Controller 页全中文上屏、
> 英文零损伤）。工具链与全部原始文本收编于 `..\hanliu\`。
> 本手册 = ①项目全时间线 ②反编译方法论 ③引擎铁律 ④工具链手册 ⑤从零复现指南。
> 细节深挖：`gr_tools\README.md`（§1-50 逆向全记录）、`han_v2\*.md`（专题报告）。

---

## 目录

- [〇、一句话架构](#〇一句话架构)
- [一、项目全时间线（试错→结论）](#一项目全时间线)
- [二、反编译思路与方法论（附关键 VA）](#二反编译思路与方法论)
- [三、引擎铁律清单](#三引擎铁律清单)
- [四、工具链使用手册](#四工具链使用手册)
- [五、从零复现指南（ISO → ZH7）](#五从零复现指南)

---

## 〇、一句话架构

游戏文本显示链 = **EN_STRINGS.RES（字节串）→ RSFont 单字节索引 → FONT.RES 记录表
→ COMMON.PAK atlas 表面**。汉化 = 三件套原位覆写：

1. **EN_STRINGS.RES**：8 子流 LZO1X 框架内重编码 593 条中文（字节=自定码位/DBCS 对）；
2. **FONT.RES**：行数重排 + 160 条 DBCS 记录（DP 最优压缩塞回 4,421B 槽，real 保持 7,222）；
3. **COMMON.PAK**：atlas 512×512 表面像素级收割+排格+SimHei 点阵绘制（文件尺寸不变）；
4. （全量盘）**SLUS ELF**：DrawString 绘制链 16 位化补丁（lead 标记制，SLUS_P_U），
   ISO 层 ELF@LBA295 + MENU@LBA776286 原位替换。

---

## 一、项目全时间线

> 每一步 =当时的假设 → 试错 → 结论。历史细节见 `gr_tools\README.md` §1-50 与 han_v2 专题文档。

### T0（09-05/06）格式未知的 MENU.IMG
- ISO9660 解包（iso_tool.py）；发现两座档案：MENU.IMG 58MB/686 条目（全部文本字体 UI）、
  GR.IMG 1.55GB/4070 条目（关卡资源）。
- **档案格式破解**：头 7×u32 + 0x830 条目表（48B/条：+24 stored、+28 real、+32 off）、
  名字表、4096 项哈希表。`stored==real` → 未压缩直读；否则子流压缩。
- 找到文本家族：MENU 内 `*_STRINGS.TXT`（INI 风 ` \t"KEY"\t"VALUE"`）、
  `*_STRINGS.RES`（47,570B 压缩）、`*_SPECIAL_FEATURE.XML`；GR 内 1193 `.ATR`（纯 XML）、
  46 `.MIS`。

### T1（09-06/07）压缩格式：先错后对
- **误读期**：由 `decode__4lz77FPUciPPUc @0x539110` 符号与手测，得出"字节计数格式"
  （c≤0x10 → c+3 字面量；c≥0x11 → c-17 字面量）——它能解出**部分**文本，是最大误导源。
- **定论（09-11/12 重测）**：存储层 = **标准 LZO1X**（与 ffmpeg av_lzo1x_decode 逐位一致），
  子流 = `{u32 plen}{u32 osz}{payload}`，plen<osz 为压缩、plen==osz 原样存储；
  307 个 BMZ、5 语言 42 子流全部零失败。`lz77_decode.py` 为最终解码基准。
  旧"计数格式"只是 LZO1X 首令牌与长字面量扩展的误读拼合。

### T2（09-07/09-09）EN_STRINGS.TXT 路线（最终被证伪，但遗产巨大）
- 121 高频汉字 → 单字节 0x87-0xFD（code_map.json，按 PC 官方中文频率）；框架式写回 TXT。
- **K99 首个完整中文盘（09-09）**：占位符汉字对 + PAK 像素画跨格字形，31 字上屏，
  33,000 帧存活、任务内实测 ✓ —— 证明 ISO 拼接（splice LBA 776286）与 TXT 框架写回安全。
- **证伪（09-10/12）**：k99nav38 等导航实证：**TXT 的值从不被游戏显示**——教程框、
  面板、菜单文本真身是 RES（MENU 份 + GR.IMG 份），TXT=残留文件。TXT 路线最终排除。
- 遗产：条目表三字段不动、原尺寸 ISO 拼接、"绝无空值行"、框架式写回——全部沿用到终局。

### T3（09-11）BMZ 谜团解开 + GR.IMG 纯净提取 + 文本普查
- 曾以为教程文本在 `D02_REFINERY.BMZ`（"非 LZO1X"）——用正确解码器重测：
  **307/307 全解，BMZ=纯场景数据无文本**。教程文本真身 = GR.IMG 的 EN_STRINGS.RES。
- 纯净 GR.IMG = ISO `/GR.IMG;1` @ **LBA 19175**（1,550,563,328B；早前 LBA 19194 情报有偏）。
- 普查（gr_res\ step1-10 + hanzi_demand\）：RES 2232 条分类（教程 203 / 武器HUD 79 /
  简报目标 615 / 菜单 962 / credits 331）；字频测算：全覆盖需 **566 字**，全量 1321 字。
- **⚠ 后见之明**：`WS\gr_img\GR.IMG` 是本轮之后的实验改写副本（其 EN_STRINGS.RES 被
  framed 重注入 off=481,042,432），勿作纯净源——纯净源永远取自原盘 ISO 直读。

### T4（09-12 上半）RES 结构破解 + 槽位 A/B（ZH3 前夜）
- EN_STRINGS.RES 展开态结构（res_encode.py，5 语言轮转逐字节 PASS）：
  `{u32 组数=66}` + 66 组（组 1 无 sep；组 2+ = sep + 附加串 + count + 条目）+ 条目
  `{u32 len}{bytes}{u16 attr}` + 尾 `{0}{0}`。无 magic、无偏移表、任意变长安全。
- **槽位对问题**：MENU 份 stored=47,570 < real=128,545；GR 份 stored=47,619 < real=128,668
  → 压缩写回不可避免 → E1-E15 七组 A/B 实测（gsrunner + cdvd.log 帧级判读）：
  - **铁律出土**：必须复刻原盘 **8 子流布局（16384×7 + 13857）**，单大子流 = 帧 740 必死；
    条目表 off/stored/real 三字段绝对不动。
- **ZH3（44 字）PASS**：高位字节 Latin-1 直映射 + 重绘 0xA1-0xFF 重音格为汉字 →
  显示链路第一次全通（40,000 帧）。真因结论：旧"高位字节挂死"= 错误计数编码器所致，
  与字节值本身无关。

### T5（09-12 中段）FONT.RES 翻案
- 历史结论"FONT.RES 任何改动=挂死"是**冤案**（同样是旧编码器）。T0/T1/T2 微编辑实验
  （恒等重压缩写回、每次只改一处）建立安全写回规程。
- wire format（DWARF + 实机双验证，font_parse.py 对应 ReadResourceFile @0x219380）：
  `{u32 20}{"new_font_revised.rsb"}{u32 3}` + 3 face（large/default/huge）×
  {u32 14 字段} + **10B 记录 ×224**（pad,adv,u0,v0,u1,v1）+ styles。
  - 记录语义：**采样矩形 = (u0+20, v0)-(u1+20, v1)**（u 恒 +20，实机微编辑实证）；
    **adv 单位 1/256px**（0x1000=16px）；索引 = `((int8)c - (int8)base) & 0xFF`，越界 clamp 0。
  - **0xFF"槽"= 表尾 8B + 下一 face 名长度字段，禁写**（写了 → RSFontMgr 解析崩 →
    全部文字消失；ZH5 首轮实挂定因）。
- 压缩：贪心器压不进 → **ft_dpc.py DP 最优解析**（4,232B ≤ 4,413B 限额）。

### T6（09-12）容量三重定论：89 字 = 单字节天花板
1. 实机：0x80 被跳过、0x81-0x9F 含毒字节（C1 系列图案盘）→ +0；
2. ELF：PS2 版**无中文模式**（PS2_CJK_MODE.md：字符串/DWARF/xref/盘面四重零残留），
   RSFont 严格单字节、无分页；
3. 结构：224 记录 = 0x20-0xFF 全空间，扣毒区与 EN 在用（®±µçñ、0x92、0xFF 槽）→ 0xA1-0xFF
   实际可用 **89 格**。
- ZH5（16px SimHei EBDT 真点阵 + practical89 字表）40,000 帧 PASS——单字节路线登顶。
- PC 版对照（PC_FONT_MECHANISM.md 六问全解）：PC 中文 = IsLead/IsTrail/IsDBCS 三函数簇 +
  gbtext.def 侵入式 map + 多页 TGA——**该机制未编译进 PS2**，不可移植，只能 ELF 补丁。

### T7（09-12 晚）ZH6：字形质量与 0xA1 诅咒
- 用户报告 回/队 不可接受。两轮"图案定位盘"（ISO A/B + 逐帧 dump 对比）定源：
  - **回**：16px 点阵经引擎 0.8 缩放 + glow 糊死 → 非 bug，改 20px 混合宽度；
  - **队**：**0xA1 码位 + u0=0 的记录被引擎渲染冻结**（冻结于原始 ¡ 格）→ 换码 + 全表禁 u0=0。
- ZH6（16/18/20px 混合宽度，SimHei 原厂 EBDT）40,000 帧 PASS。

### T8（09-12/13 深夜）ELF DBCS 补丁：从 synth-byte 到 lead 标记制
- **Stage1（patch_db1_elf.py，151B）**：仅钩 DrawString v1 主循环——lead/trail ∈[A1,FE] 时
  合成 `synth=(lead-0xA1)*94+(trail-0xA1)+161` 写回单字节槽、步长 +2。
  实机 PASS：Controller 页渲染 `地.图.武.器.切.换.`，英文零损伤。
- **Stage2（16 位字符 ABI）**：四个 cave（死代码区 **0x26BEA0..0x26C18F**，748B，四重引用
  扫描判死；勿向 0x26C190 方向扩——0x23198B8/C8 有 vtable 数据字）：
  ds16（字节→16 位合成）、cw（CharWidth）、cctc（ComputeCharTextureCoords）、sw（StringWidth）。
  FONT.RES 同步重排：large rows5(160) + default rows12(384=224+160 DBCS) + huge rows7(112)。
- **二分矩阵**：cw/cctc/sw/ds16 每轮开关组合 × 4300 帧快判 → v3（build_PS.py）矩阵全绿。
- **"字节对验收器"假象**：Stage2 对链渲染成"短横"，疑有串层验收器改写。
  **证伪（三重证据）**：①绘制时刻 RAM 差分（-grdumpwin 逐帧 32MB eeram）全 32MB 无改写副本；
  ②同一对 (A1,A1) 在不同 ELF 下渲染不同 → 串层验收不成立；③静态审计定位真凶 =
  **DrawString 槽位 `lh` 符号扩展**：char16=0xA1A1 → a1=0xFFFF…A1A1，cave 里 `srl a1,8`
  得 0x00FFFFA1 → idx≈1.58e9 ≥ mSize → 恒 clamp 记录 0（空格）→ 空白 quad（双线性边缘
  渗出 = "短横"）。
- **v4（build_PS_v4.py）**：三条槽位 lh→lhu（0x219BD4/0x219BE4 ← 0x97A500DE、
  0x219CA0 ← 0x97A400DE）。GR_DB7 实测：Controller 页 20 对汉字全部上屏，英文零损伤，
  40,000 帧 exit=0 —— **对链路全通，"验收器"正式死亡**。
- **v5（build_PS_v5.py，终版 lead 标记制）**：v4 的"任意对消费"会吞相邻单字节汉字
  （换弹=D2 D3 被并成垃圾对）→ 规定 **仅 lead∈{0xA1,0xA2,0xA3} 构成对**
  （役/有/下 三字一律以对编码、字形复用原单字节格 idx381-383），0xA4-0xFE 一律单字节。
  对 idx = `224 + (lead−0xA1)×94 + (trail−0xA1)`。

### T9（09-13）GR_ZH7 全量盘（当前交付）
- **字符 246** = 86 单字节（zh6 字表）+ 3 标记对字 + 157 新对字（官方 PC 译文缺字频序贪心）。
- **FONT.RES**：展开 7,062B ≤ 7,222；DP payload 4,232B ≤ 4,413；槽回环 PASS。
- **atlas**：收割被裁撤记录格清底（与保留矩形求交避让）+ 26px 带排 16px SimHei（u0≥1）→ 157 格。
- **RES**：zh6 76 条 + 新 517 条 = 593 条；8 子流 blob 46,010B ≤ 47,570（余 1,560）。
- 组装 = menu_working 底 + 三条目原位写 + ELF@LBA295 + MENU@LBA776286 → GR_ZH7.iso。
- **实测 PASS**：40,000 帧跑满 exit=0（667s）、needle 4,229（原盘基线 4,245）；
  Controller 页 左列 缩小/地图/切换队员/蹲下/平移/L3键/左右窥视/暂停菜单、右列
  放大/换弹/切换武器/执行动作/开火/视角上下/R3键/快速命令 全部中文；全局按钮
  △返回/✕确认/⬜删除 中文；英文零损伤；单字节（删除）与对字节（换弹）同页共存实证。
- 工具链与文本收编 = `..\hanliu\`；示例管线可**逐字节复现**本盘 MENU
  （`hanliu\build\example_zh7\`）。

---

## 二、反编译思路与方法论

> 全部方法在无 computer use 约束下进行：静态 = 自制工具读 ELF/DWARF；
> 动态 = 自编译插桩模拟器 pcsx2-gsrunner（-grneedle/-grscanframes/-grdumpwin/-grinput…）。

### 2.1 方法总表

| 方法 | 做法 | 典型战例 |
|---|---|---|
| **符号表先行** | .symtab/.strtab 完整可读 → 先建 VA↔符号地图再读码 | `decode__4lz77`、`RSFontMgr::ReadResourceFile`、`ComputeCharTextureCoords` 全部符号定位 |
| **needle 特征扫描** | gsrunner `-grneedle WPNRPK74 -grscanframes 10`：内存特征命中帧/次数作健康遥测 | 每轮实测判据：首中 f150、基线 4,245 次 |
| **快判（4300 帧）** | boot 挂死只需 ~4,300 帧（73s/轮）→ 先快判再长跑 | Stage2 v1 boot 毒 2 分钟定位 |
| **单变量隔离** | 一次只改一处（T2 微编辑：单字节改写/单记录改写/单 face 行数）| FONT.RES 语义 16 项逐项实证（+20 偏移、adv 1/256、0xFF 槽…） |
| **A/B 对照盘** | 同 nav 重跑两张只差一变量的 ISO，逐帧/逐区段像素对比 | E1-E15（子流布局）、C1（0x80-0x9F 毒）、db1-db7（ELF 补丁矩阵） |
| **图案定位盘** | 把"嫌疑字节"排成可见图案（横条/点阵）写入盘，屏幕读回图案 | 0xA1 u0=0 冻结（队）、16px 糊化（回）、lh 符号扩展（短横） |
| **二分矩阵** | 多 hook 各设开关，组合枚举 × 快判 | Stage2 ds16/cw/cctc/sw 四开关矩阵全绿锁定最小集 |
| **RAM 差分** | `-grdumpwin f0 f1` 窗口逐帧全 32MB eeram，找"变换副本" | 验收器证伪第一击（无改写副本存在） |
| **DWARF 逆向** | .debug 段（0x6B43A0，26MB）tag 0x02/0x0d/0x23 类布局 → 成员偏移表 | RSFont 类 +0x20 base、+0x28 cells、+0x38 指针、+0x44 mSize |
| **引用扫描判死区** | 候选 cave 区间做四重引用扫描（xref/数据字/vtable/跳转表） | 0x26BEA0..0x26C18F 判死代码，748B 落位 |
| **与 PC 版对拍** | PC 中文版同一引擎的机制作"标准答案"再移植 | PC_FONT_MECHANISM 六问 → 移植清单（但确认 PS2 无此代码） |

### 2.2 关键 VA 速查（PS2 SLUS_206.13，文件偏移 = VA − 0x100000 + 0x80）

**字体系统（RSFont/RSFontMgr）**
| VA | 符号/功能 |
|---|---|
| 0x219380 | RSFontMgr::ReadResourceFile（wire format 消费者） |
| 0x21AB50 | RSFont::ReadResource |
| 0x21AC00 / 0x21AC7C | StringWidth / StringWidth 主循环入口（0x21AC74=sw hook 跳板） |
| 0x21AD10 | CharWidth（cw hook 落点 0x21AD18） |
| 0x21ADE0 | ComputeCharTextureCoords（cctc hook 落点；索引/UV 唯一真源） |
| 0x21A450 / 0x21A5B0 | RSFontMgr::Initialize / Create |
| 0x27508C / 0x275298 | IkeUIMgr::PreInit/Create 的 font 加载 jal |
| 0x57ABE0 / 0x57ABC0 / 0x57AD70 | kFontResourceFilename / kStringResourceFilename / "font.res" |

**DrawString v1 与补丁落点**
| VA | 内容 |
|---|---|
| 0x219A70 | DrawString v1（主循环 ds16 hook 于 0x219BCC jal cave） |
| 0x219BD0/0x219BD4/0x219BE4 | 槽位写 + 两次 `lh a1,0xDE`（v4 改 0x97A500DE=lhu） |
| 0x219CA0 | `lh a1,0xDE`（v4 改 lhu）；0x219DAC/0x219DB0 槽位读回 |
| 0x219C08/0x219C14/0x219C94/0x219CAC/0x219D24/0x219D38 | µ/± 立即数常量（0xB5/0xB1 图标字） |
| 0x21AE20 | cctc 原始恢复点（00051880） |
| 0x26BEA0..0x26C18F | cave（死代码 748B）；ds16@+0x000 cw@+0x09C cctc@+0x184 sw@+0x1E8 |
| 0x23198B8 / 0x23198C8 | vtable 数据字（不可向 0x26C190 方向扩展） |

**语言机制（均"不存在/残留"证据）**
| VA | 符号 |
|---|---|
| 0x4CF370 / 0x4CF360 / 0x4CF220 / 0x633B50 | eeRpcSetLanguage / GetLanguage / ConvertNameByLang / 语言全局 |
| 0x344D70 / 0x344740 | SelectLanguage_PS2 ctor / Accept |
| 0x58B6B0-0x58B6D0 | EN_/FR_/DE_/IT_/ES_ 格式串 |
| 0x539110 | decode__4lz77（Sony SDK lz77 残留，非档案压缩路径） |

**PC 版（GhostRecon.exe，对照用）**
| VA | 功能 |
|---|---|
| 0x7BCC10 / 0x7BCC40 / 0x7BCC80 | IsLead / IsTrail / IsDBCS（GB: lead[A1,FE] trail[40,7E]∪[A1,FE]） |
| 0x655D77 | key 合成 `shl ax,8; add ax,[edi]` |
| 0x6581A0 / 0x658760 / 0x6586E0 / 0x658340 | gbtext.def 加载 / UV 公式（perRow=512/S）/ 字号三档 / 页纹理 |
| 0x8D353C | GB/BIG5 全局模式字节 |

---

## 三、引擎铁律清单

> 每条都有实机 A/B 证据。违反 = 挂死/花屏/无字，且多数**不报错**。

**档案层（IMG/ISO）**
1. IMG 条目表 off/stored/real 三字段绝对不动；替换内容一律**槽位内原位覆写**
   （RES ≤47,570、FONT 槽 4,421、PAK 400,659）；超槽 → img_patch 空隙/追加 + 重拼 ISO。
2. MENU @LBA 776286（58,300,882B）；ELF @LBA 295；GR.IMG @LBA 19175。
   ISO 组装 = 原位替换、输出尺寸 = 原盘尺寸（iso_tool build 重建法已弃用）。
3. GR.IMG 拼接历史 LBA 19194 有偏——以 ISO9660 目录树动态解析为准。

**RES 层**
4. 写回必须**复刻基底子流布局**（MENU 8 子流 [16384]×7+[13857]）；单大子流 = 帧 740 必死。
5. 展开态尾部 `{u32 0}{u32 0}` 终止符必须有；串内禁 0x00（引擎按 C 串消费）；
   attr 保持 0x0000。
6. RES 有两份（MENU 128,545 / GR 128,668，12 条差 123B）——改哪份以哪份原文为基准。
7. 显示优先级：教程/简报/任务 = **GR.IMG RES**；主菜单 UI = MENU RES；
   EN_STRINGS.TXT 值从不显示；ATR 中文名会让指令面板打不开（nav25）。

**字体层（FONT.RES + atlas）**
8. 记录有效区 = 每 face 0x20-0xFE；**0xFF"槽"= 表尾 + 下一 face 头，禁写**。
9. FONT.RES 条目 real 必须保持 7,222；payload 用 ft_dpc（≤4,413B）；
   写回前后 decode_entry 回环自检。
10. 采样矩形 = `(u0+20, v0)-(u1+20, v1)`；**u 恒 +20**；adv 单位 1/256px；
    atlas 背景 31=透明、笔画 0=实心。
11. **u0 ≥ 1**（0xA1 码位 + u0=0 记录被渲染冻结——"0xA1 诅咒"）。
12. 0xB1/0xB5 = 手柄图标字（UV 硬编码指向 pda_counterparts.rsb），CharWidth 恒 20，
    无需提供字形但布局要留位；0x92(’)/®/ç/ñ 是 EN 在用字形，重绘前必保。
13. atlas 新格 u0=x-20≥1 且与保留记录矩形、现存墨迹互不重叠（zh7 收割+避让算法）。
14. ZH7 face 行数：large rows5(0x20-0xBF) + default rows12(384) + huge rows7(0x20-0x8F)。

**字符编码层（ELF DBCS 配套）**
15. 0x80-0x9F = 毒区（boot 期容器预处理即挂）；0x00 禁入串。
16. 单字节可用池 = 0xA1..0xFE − {0xAE,0xB1,0xB5,0xE7,0xF1} − 0xFF = 89 格（ZH7 用 86）。
17. DBCS 对（SLUS_P_U）：**仅 lead∈{0xA1,0xA2,0xA3} 构成对**；对 idx =
    224+(lead−0xA1)×94+(trail−0xA1)；标记字（役/有/下）字符串中一律以对编码，
    其单字节码位不得以单字节出现。
18. DBCS 新字记录 idx = 224..383（default 表）；157 对字字形 = 16px 新格；
    标记字对字形复用原单字节格（idx 381-383）。

**实测层（gsrunner）**
19. ISO 参数必须**反斜杠路径**（正斜杠 exit=1 秒退）；记忆卡固定 `memcards_db1`
    （新空目录会使 boot 流程与固定 nav 失配）；跑前后 `taskkill //F //IM pcsx2-gsrunner.exe`。
20. 健康判据 = 跑满帧数 + exit=0 + needle 次数（基线 4,245）；cdvd 停在 544/774xxx =
    模拟器层偶发挂起，与盘无关，重跑。
21. 导航绑定名 LUp/LDown/LLeft/LRight（'up' 是十字键不能移动）；跑动 = LUp 每 25 帧
    1 tap × 8；主菜单 Options = 第 8 项（7×down）；Controller 页判读 = snap_f00033480.png。

---

## 四、工具链使用手册

> 全部工具已收编 `..\hanliu\tools\`（原件未动，来源横幅在每个文件头）；
> 本节为速查，逐工具详解见 `..\hanliu\docs\TOOLS.md`。

| 层 | 工具 | 一句话 |
|---|---|---|
| 格式 | `gr_lz.py` | IMG 档案解析 + 纯字面量安全编码（encode_literals/frame_substream） |
| | `lz77_decode.py` | 标准 LZO1X 解码基准（decode_entry/lzo1x_decompress） |
| | `lzo1x_c.py` | minilzo 兼容压缩器（RES 8 子流: level=7+use_m1+use_m4） |
| | `res_encode.py` | RES 解析/文本同构/重建/轮转/mod/probe |
| | `img_patch.py` | IMG 补丁（原地/空隙/追加，--framed） |
| | `img_tool.py` / `iso_tool.py` / `splice_iso.py` | 列表/解包（rebuild 勿用于补丁）/ ISO 例行 / MENU 原位拼接 |
| 字体 | `font_build.py` | **字表 CSV → PAK 像素差异 + FONT.RES 槽位态**（单字节/DBCS 双模式，全自检） |
| | `ft_dpc.py` | FONT.RES 专用 DP 最优压缩（≤4,413B） |
| | `font_res_parse/probe/scan.py` | FONT.RES/atlas 探针三件 |
| | `zh7_build.py` | ZH7 一体构建参照（顶层执行） |
| ELF | `patch_db1_elf.py` → `build_PS.py` → `build_PS_v4.py` → `build_PS_v5.py` | synth-byte → 16 位 ABI v3 → lhu → **lead 标记制终版 SLUS_P_U** |
| | `patch_db2c.py`(+Asm 套件)、`patch_db2*.py` | Stage2 参数化与历史存档 |
| | `dis4.py` / `dis4P.py` / `elf_info.py` / `dwarf_probe.py` / `font_parse.py` | EE 反汇编 / ELF 摘要 / DWARF / wire format 解析 |
| 组装实测 | `make_iso.py` | 原盘+MENU+ELF → 原尺寸成品 ISO（回读自检） |
| | `run_test.py` | gsrunner 一键（zh2nav/quick/bisect 预置 + ALIVE/CDVD_STALL/CRASH 判据） |
| | `probe_iso.py` / `run_iso.py` / `probe_run3.py` / `run_bisect.py` / `verify_iso.py` | 内核原件（对账用） |
| 文本 | `export_texts.py` | 6 张原始文本 CSV 一键导出（含 PC RES 格式破译） |
| | `text_replace.py` | 翻译 CSV → RES blob / GR RES / TXT / ATR（宁少勿错三禁校验） |

三条最常用命令（详细示例见 hanliu\docs\TOOLS.md）：

```bat
set PY=<anaconda3>\python.exe
cd hanliu\tools
%PY% export_texts.py                                    :: 全部原始文本 → hanliu\texts\
%PY% ..\build\example_zh7\zh7_pipeline.py               :: 复现 GR_ZH7（dry-run）
%PY% text_replace.py --mode res --charset out\charset_compiled.json ^
     --input my.csv --base-res <8子流基底> --target menu --out new.bin
```

---

## 五、从零复现指南（ISO → ZH7）

> 完整版（含故障对照表）：`..\hanliu\docs\REPRODUCE.md`。

1. **文本底账**：`PY hanliu\tools\export_texts.py` → texts\ 六表（2232/2232/2220/1193/46/2902）。
2. **字表 CSV**：按译文汉字频次列 `char,strategy[,code]`（single/pair/marker；宁少勿错）。
3. **字库**：`font_build.py --charset 字表.csv --mode dbcs --base-ft zh6\ft_expanded_zh6.bin
   --base-pak han_v2\COMMON_PAK_ZH6.bin --ttf SimHei.ttf --size 16 --out-dir out\`。
4. **译文**：`text_replace.py --mode res --charset out\charset_compiled.json --input trans.csv
   --base-res en_strings_zh_8sub_v3.bin --target menu --out out\blob.bin`（≤47,570 自动校验）。
5. **MENU**：`PY hanliu\build\example_zh7\zh7_pipeline.py`（三条目原位写 + 白名单自检；
   dry-run 到 MENU.img 为止）。
6. **ISO**：`make_iso.py --base-iso <原盘> --menu out\MENU.img --elf SLUS_P_U.elf --out out\GR_ZH.iso`。
7. **实测**：`run_test.py --iso <iso> --dump <dir> --frames 40000` → 判读 Controller 页。

---

## 附：交付物与证据索引

| 交付物 | 位置 |
|---|---|
| 工具链 + 新整合件 | `..\hanliu\tools\`（44 脚本，自检全过） |
| 原始文本 6 表 | `..\hanliu\texts\`（README 含结构与行数核对） |
| 可复现示例（逐字节复现 ZH7 MENU） | `..\hanliu\build\example_zh7\` |
| 字体资产说明 | `..\hanliu\fonts\FONTS.md` |
| 工具详解 / 复现指南 | `..\hanliu\docs\TOOLS.md` / `REPRODUCE.md` |
| 专题逆向报告 | han_v2\{RES_FORMAT, RES_AB_TEST, PS2_CJK_MODE, PS2_FONT_MECHANISM, PC_FONT_MECHANISM, ELF_DBCS_PATCH}.md |
| 逆向全记录（§1-50） | `gr_tools\README.md` |
| ZH7 证据 | `gr_build\tmp\zh7\*`（layout_dbcs.txt、快照）、`gr_build\dumps\zh7`、PROJECT_STATUS.md §11 |
