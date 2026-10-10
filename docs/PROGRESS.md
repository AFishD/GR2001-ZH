# ZH16B 进度 — 任务内文本渲染路径攻坚

## 已完成
1. 缺陷截图确认（用户实测 ZH15）：
   - 「起爆器」→「命爆器」= G12.I002 第二行行首，pair 的 lead 字节被丢、trail 0xE0 按单字节渲染为「命」。
   - 「图上」→「g;」= G12.I023 第二行行首（同机制，trail 0x67='g'/0x3B=';'）。
   - µ/± 仍为字母 = ZH15 内容未含 ZH13B reencode（本盘验证用 GR_ZH13B 已含）。
2. **存储字节核查（决定性）**：GR_ZH15.iso GR.IMG EN_STRINGS.RES 解码实测
   G12.I002 = 113B（引爆器 pair 完整、全文完整），G12.I023 = 140B（含 µ/± pair）
   → **存储层完好，丢 lead 发生在游戏内（渲染/折行层），非我们的编码器**。
3. gsrunner 钩子（默认行为不变，仅新旗标 -grdrawwin <f0> <f1> 激活）：
   - iR5900.cpp：g_eeDrawHook 指针 + grIsDrawHookPC(0x219A70/0x219E00/0x219EB0/0x21AC00/0x21AD10)
     + recRecompile 块首 xFastCall(grDrawHookTrampoline, pc)。
   - GRResearch.cpp：DrawHookTrampoline 记录 ra/a0-a3/f12/f13 + 串 48B（StringWidth 24B@a1、
     CharWidth c=a1 仅 ≥0x80）；帧窗门控 + 每帧 3000 行上限；无旗标时零开销零行为变化。
   - 编译 PASS（build_pcsx2.py，MSVC 环境）；exe 时间戳 19:47；备份 pcsx2-gsrunner_zh16b_backup.exe。
   - 注意：cmake --install 对 updater.exe 报错（无关，gsrunner 已产出）。
4. 盘：GR_ZH13B.iso（V12 ELF + ZH13B reencode RES）已拷到 C:\gr_build\iso\（ASCII 路径）。

## 运行中 / 待办
- [ ] run_drawlog.py：GR_ZH13B + nav_t01 + -grdrawwin 26900 30000 + snap 31，30000 帧
- [ ] 分析 drawlog.txt：教程框 DrawString 走哪条路径、字节流形态（行首 pair 是否完好）
- [ ] 根因定位 + 修复 + 验证（T01 4× + 前端回归）

## 根因定案 + 修复 (2026-09-14 晚)
- **第一现场 (gsrunner 钩子 2 轮)**: DrawString 三变体为方法 (a0=this/RSFontMgr vtable
  0x597780, a1=str, v1: f12/f13=x/y); 教程框路径 = RSTextComponent::DrawTheString(0x21C4C0)
  → DrawString v3(0x219EB0) → v1 (RA=21C85C / 219EEC); DoWordWrap(0x21CC10) 逐字节
  `lb`+每字节 CharWidth 测宽 → **断点 s2 落入 pair 中间**:
  f29619 I021 三行 = L2 尾「更换姿」+<A3> (势=pair a3f2@86-87 的孤 lead), L3 首
  「随.卧倒」(孤 trail 0xF2, SINGLE[0xF2]=随) —— 与用户截图「命爆器」(孤 0xE0,
  SINGLE[0xE0]=命)/「g;」(0xA8+0xFE 走垃圾对 clamp) 同一机制。before 快照 f29636。
- **修复 = V13W**: DoWordWrap 扫描循环 pair-aware 化 (cave 重写, 单挂点):
  0x21CD70 → j 0x417500 (48 条 cave): lead∈[A1,AE) 且 trail∈[A1,FF) 且非末字节 →
  char16 → CharWidth 走 cw 对路径 → 步进 2; 否则单路径步进 1; 溢出 → 0x21CDBC
  (at=0, Substring end=s2 永不切对); 越界 → 0x21CDB8; ASCII 逐字节等价。
  cave 区 0x417500 零引用 (j/jal 目标 + 全文件字面量 count=0)。
- **sim_wrap_v13W 双断言 PASS** (真 ELF 指令字 + 真 CharWidth 链 + 真 FONT.RES 记录):
  1) I011/I012/I021/I022 真串全预算扫描断点永不 mid-pair; 2) ASCII 串与原版算法逐字节等价。
  (构建器三轮排障: jal 延迟槽 addu a0,t0,a0 → zero; label 伪项占槽空洞 → emit 计数器;
  slt op=0x2A → 0x00; SINGLE or a1,t2,a1 → t2,zero —— 上次 a1 泄漏 0x65|0x73=0x77 实锤)

## 实机验证收口 (2026-09-14, Agent B)
- [x] 验证盘核验: GR_ZH16T.iso = GR_ZH13B 基底 + SLUS_P_V13W.elf@LBA295, ELF 槽逐字节匹配,
      除 ELF 槽 2 个 LBA 外与基底零差异 (zh16_iso.py 重建后回读校验 PASS)。
- [x] before 证据确认: before_snap_f00029636/29667.png = I021 三行框, L2 尾「更换姿」/L3 首
      「随,卧倒」(势 pair 被 DoWordWrap 切断)。
- [ ] 跑 1 (run_verify2.py): GR_ZH16T + nav_t01 + -grdrawwin 26900 30200 + snap 31, 60000 帧

## 实机验证收口续 (2026-09-14, Agent C)
- 前次 V13W 运行 (run_verify2) 中断于 f17740 (drawlog 空, 未到帧窗, 应为会话终止)。
- 复核: GR_ZH16T.iso ELF 槽@LBA295 == SLUS_P_V13W.elf 逐字节匹配 PASS (37453732B)。
- 重新后台运行 run_verify2.py (60000 帧, -grdrawwin 26900 30200, snap 31)。
- before 判读基准确认: before_snap_f00029667 = I021 三行框, L2 尾「更换姿」+L3 首「随,卧倒」
  (势 pair 被切)。V13W 预期: L2 尾「更换姿势」完整, L3 首不再有孤「随」。

## 实机验证收口 (2026-09-14, Agent D)
- [x] 复核: 无遗留 gsrunner 进程; GR_ZH16T.iso 在位; run_verify2.py/nav 脚本就绪。
- [ ] 跑 1 (run_verify2.py 后台 run_verify3.log): 60000 帧, 进行中 (f~18800)。
- [x] nav_t02.txt / nav_t03.txt 已生成 (mk_nav_tlevel.py: nav_t01 基线, 27000 cross 确认前
      插 1/2 个 down tap @26400/26700) — 待 T01 自身快照 (f25550-27000 选关屏) 复核帧态。
- [x] 基准核查: gr_build\dumps 下 icx_fe_* = iconfix 任务产物 (非本任务基准);
      ZH11/ZH12 菜单基准快照已不存在 → 菜单回归 = 自跑 GR_ZH12 基准 + GR_ZH16T 测试像素对比。
- [x] 跑 1 完成: exit=0, 60000 帧, 1003s, needle WPNRPK74 f150 首中 → 健康判据 PASS。
- [x] T01 drawlog 实证 (f29671, I021 框):
      BEFORE(V12/dump_t01) = 3 行 v1 Substring (L2 串尾孤 lead A3 截断, L3 串首孤 trail F2=随);
      CURRENT(V13W/dump_verify2) = 2 行 v1 Substring, 势 pair (A3 F2) 完整连续于行中, 无孤字节。
      快照 f29667: L1 尾「卧倒」完整, L2「…练习更换姿势,卧倒并从铁丝网下面爬过去.」全对。
      I012 (f26971): 两版均 2 行, 断点移动 (before L1 止「和」/ current L1 止「调」),
      current L1 尾「调」/L2 首「整」均为完整 CJK 字形, 无孤字节 → PASS。
      注: V13W 行容量略增 (对路径测宽 vs 孤单字节测宽), I021 3行→2行为修复合理后果。
- [ ] 跑 2 (T02, nav_t02 down@26100, dump_t02, 36000 帧) 进行中。
- [!] run_tlevel.py 相对路径 bug: subprocess cwd=gsrunner 目录 → dump/nav 指向错误位置,
      首次 T02 白跑 (36000 帧空跑已终止, dump_t02 残留已清)。已改 os.path.abspath 后重跑。
- [x] T01 判定存档: dump_verify2/judge_I012_V13W_f26908_4x.png, judge_I021_V13W_f29667_4x.png
      (I021 4x: L1 尾「卧倒」/L2「…更换姿势,卧倒并从铁丝网下面爬过去.」全部完整, 无孤字)。
- [x] T01 后段抽查 (f31000-59000): 无更多教程框 (nav 30150 后无输入, 游戏待机) →
      I002(起爆器)/I023(μ±) 属其他训练关, 由 T02/T03 跑覆盖。

## 实机验证收口 + 多关卡验证 (2026-09-14, 主代理)
- [x] 复核: 无遗留 gsrunner 进程; run_verify2.py 重新后台运行 (60000 帧, -grdrawwin 26900 30200)。
- [x] **选关导航破解 (dump_t01 快照实证)**: nav_t01 时间线 = f25550 输入名字「确认」→ f25900 保存档案「否」
      → f26009-26226 选关屏 (「训练」列表 训练1-7, down 换选, cross 接受) → f26200 cross=接受进入
      → f26536 简报「训练1 - 越野训练」+ 载入中 → f26970 关内教程框 (越野训练文本)。
- [x] **多关卡导航脚本已生成**: tmp\zh16b\nav_t02.txt-nav_t07.txt = nav_t01 在 f26100 起每 150 帧插 1 个 down tap
      (N-1 个) 再接受进入 训练N。run_tprobe.py = 探针运行器 (GR_ZH16T + nav_t0N + -grdrawwin 26800 31500 +
      snap 15, 31500 帧, memcards_zh12_probe 独立副本避免与主 run memcards 冲突)。
- [ ] T02 探针运行中 (dump_t02): 判定选关屏 训练2 选中 + 简报/教程框文本完整 (无缺字/孤字/错行首)。
- [ ] T01 主验证 run 判定 (对照 before_snap_f00029636/29667)。

## T01 主验证 PASS + 多关卡排障 (2026-09-14, 主代理续)
- [x] **T01 主验证 run PASS**: run_verify2.py 60000 帧跑满 exit=0 (1002s), WPNRPK74 f150 首中,
      drawlog 145637 行, 教程框路径 F26901 PC=219EB0 RA=21C85C 完整串含 pair。
- [x] **I021 教程框 (f29698) PASS**: 完整两行「...练习更换姿势,卧倒并从铁丝网下面爬过去.」——
      before=三行断对 (L2 尾「更换姿」+孤 lead, L3 首孤「随」), now「更换姿势」完整、无孤字。
      证据: judge_v13w/I021_full_f29698.png (对照 before_snap_f00029667.png)。
- [x] **I012 教程框 (f26970) PASS**: 「...用右摇杆转身和调/整视角上下...」完整无缺字无孤字
      (调/整 分行 = 独立字形合法断行)。证据: judge_v13w/I012_L1L2_f26970.png。
- [ ] 起爆器(I002)/图上(I023)/μ±: 不在 T01 流程内, 需其他训练关 (多关卡验证)。
- [x] **T02 探针排障**: nav_t02 = nav_t01 + f26100 down tap (选关屏换选)。4 次运行全部
      挂起于 f20150 (截图保存处, 0 字节 png), 排除: 并发 (第 3 次无并发仍挂)、snap 配置
      (snap15→31 仍挂)、memcards (probe 副本→原版仍挂)。隔离实验: 探针配置+nav_t01 顺利
      过 f20150 (至 f25296+)。nav 文件逐行对比 = 仅多一行 26100 down tap (在挂点之后)。
      待做: 无 -grsnap 的 nav_t02 决定性实验。

## 多关卡续 (2026-09-14, 主代理 → 3 并发子代理)
- [x] T02 验证 PASS (dump_t2d): 教程框 = 「这里是[XX][XX]武器训练区.你要学习如何使用步枪和手枪,如何切换武器,
      换弹和使用瞄准镜.」+「按 START 键退出训练.」——训练2=小武器训练区, 串完整、行首无孤 trail/垃圾对
      (drawlog 功能级判定; GR 侧字符集与 MENU 侧不同, 未收录字节按 [XX] 标注)。
- [x] **nav_t03 bug 发现+修复**: 旧生成器把第 2 个 down 插在进关 cross(26200) 之后 → 实际仍进训练2
      (dump_t3d 与 dump_t2d 教程串完全相同)。已重生成 nav_t02-t07: down 全部在 26000 cross 与后移的
      进关 cross 之间 (26100+160i, cross=26100+160(N-1)+250)。
- [x] **gsrunner 截图挂起定论**: T02+ nav + -grsnap(任意值) → f20150 确定性挂起 (4/4);
      无 -grsnap 一切正常 (T02/T03 drawwin 轮 exit=0 跑满)。多关卡一律 run_tdraw.py (无 -grsnap)。
- [x] 工具固化: run_tdraw.py (多关卡运行器) + decode_drawlog.py (教程串解码+缺陷特征检查)。
- [→] 3 并发子代理: A=任务一收尾 (T03-T07 多关卡 + MENU 40000 前端回归 + FINAL_ELF.md);
      B=任务二 字库扩容 1212 字; C=任务三 开机画面汉化。

## T03-T07 多关卡 + MENU 回归 (2026-09-14, 子代理 A)
- [x] 复核: 无遗留 gsrunner; nav_t02-t07 已是修复版 (down 全在进关 cross 前);
      grinput 解析器按帧 sort (源码实证) → nav_t07 的 27150/27000 乱序行按帧序执行,
      语义 = 27000 cross 接受 训练7 (down 已于 26900 完成) + 27150 过渡期冗余 cross, 风险低。
- [x] **T03 PASS** (dump_t3d 重跑, 544s exit=0 跑满): 简报「T03 - Grenades / 布拉格堡, 北卡罗来纳州 /
      2008年3月15日 13:00」; 教程框 f27107 = 「这里是榴弹训练区.你要学习如何投掷手雷和使用榴弹发射器.
      随时按 START 键退出」完整, suspect=0 (无 BAD-PAIR-START/孤 trail); 换关生效 (≠T02 小武器训练区)。
      注: 本关教程串仅出现在 v1 行路径 (PC=219A70), 无 219EB0/21C85C 全串记录, 结构判定不受影响。
- [x] **T04 PASS** (dump_t4d, 544s exit=0 跑满): 简报「T04 - Heavy Weapons / M05 - Gold Mountain」;
      教程框1 f27267 = 「这里是火箭筒训练区.你要学习如何使用反坦克火箭筒.随时按 START 键退出训(练)」;
      教程框2 f29569 双行 = 「你应(该)注意到火箭筒的准星和步枪与手雷的都不一样.你必(须)要等准星变/
      时候(任)务能开火.等准星(尺)可缩到最小后再按开火键.标准的火箭发射器每发射一(次)...选弹.」
      —— 行首「时候」为正常字形, 串内 [A5][A9]/[A4][A7] 等均 mid-string 合法 pair; suspect=0。
      换关生效 (火箭筒 ≠ T03 榴弹)。
- [x] **T05 PASS** (dump_t5d, 543s exit=0 跑满): 简报「T05 - Machine Guns / 布拉格堡」; 选关屏串
      (f26800) 实证光标在「Machine Guns」= 训练5 选中; 教程框 f27427 = 「这里是机枪训练区.你要学习
      如何使用固定的机枪.随时按 START 键退出训练.」完整。
      suspect=2 均为**解码器误报**: f26800 前端「接受/返回」菜单串行首 A4/A5 —— MENU 侧字符集
      pair lead 覆盖 A1-A8 (实证 (A4,AF)=接 (A5,BA)=受 (A5,AF)=返 (A4,A8)=回), decode_drawlog.py
      只映射 GR 侧 lead A1-A3 故标 [A4]/[A5]; 属前端合法 pair, 非教程框, 真实缺陷=0。
- [x] 工具增强: decode2.py (双字符集 zh13+zh12, pair lead A1-A8, 嫌疑规则=行首 A1-AD 且
      无法成 pair 且非单字节) — 复核 T02=「轻武器训练区」((A5,AD)=轻)、T04 火箭筒框全文清晰,
      T02-T05 真嫌疑全部=0。
- [x] **T06 PASS (重点关: 爆破)** (dump_t6d, 544s exit=0 跑满): 简报「T06 - Demolitions / 布拉格堡 /
      晴天」; 选关屏串实证光标在「Demolitions」= 训练6; 教程框 f27587 两行 =
      「这里是爆破训练区.你要学习如何放置地雷并将之引爆.你可以用同样的方法来放(置爆破装药)/
      以及心跳感应器等.随时按 START 键退出训练.」——**原始字节 L1 含「A2 BB A1 E0 EB」=之引爆,
      (A1,E0)=引 pair 折行后完整** (命爆器缺陷家族=孤 0xE0 未复现); L2 行首「以」完整字形;
      suspect=0。换关生效 (爆破 ≠ T05 机枪)。注: I002 第二框 (起爆器演示) 未在本窗出现
      (nav 不推进玩家, 该框需走到埋雷点触发)。
- [x] **T07 PASS (决定性: 指挥图/图上/µ± 全落实)** (dump_t7d, 544s exit=0 跑满): 简报「T07 - Command /
      布拉格堡 / 晴天」; 选关屏光标「Command」= 训练7。三框全完整:
      ① f27597 「这里是指挥训练区.你要学习如何使用指挥界面向小队的其他队员下达命令.随时按 S(TART)/
      键退出训练.」; ② f29637 「你小队的其他队员在下面的院子里.按指挥地图键调出指挥界面.」;
      ③ **f30537 = I023 指挥图教程三行**: L1「你的小队分为两个战斗小组.你在A组.在指挥地图界面选中
      一个战斗小组并在地图上放置(路径)」= **「地图上」完整 (g; 缺陷家族修复)**; L2 行首「点,」完整
      字形 (原缺陷=行首 g;) + 串内「按 µ 键添加路径点,按 ± (键)」= **µ(0xB5)/±(0xB1) 字节落实且
      不在 pair-lead 区间 [A1,AE) 内, 折行安全**; L3 行首「键删除.」正常字形——三处折行点全部避开
      pair; suspect=0。注: µ/± 字形外观依赖 ZH13B FONT.RES reencode (先前存储层+T01 视觉链路已
      实证), drawlog 字节级判定 = 落实。

## MENU 前端回归 (2026-09-15 凌晨, 子代理 A 续)
- [x] 首测轮 (dump_menu16, GR_ZH16T + zh2/nav + snap62 + 40000 帧): 健康判据 PASS (exit=0 669s)
      但**全程停留标题/吸引模式** — 记忆卡剩余空间 <500KB → 开机「Caution!」警告屏使标题
      Press START 后移 ~8700 帧, 原 nav start@11400 打空 (证据 menucmp_f372.png: Caution vs
      dump_t01 的 Accessing)。**环境发现: nav 对开机时序敏感, 跨多轮复用 memcards 须防 MC 警告屏。**
- [x] V12 基准轮 (dump_menu13, GR_ZH13B 同配置): 快路径恢复 (同帧 f372 与 menu16 不同流),
      完整走通 建档→主菜单→选项 页面 (menu13_flow.png) — 证明当前 MC 状态可用原 nav。
- [x] **V13W 正式回归轮 (dump_menu16b, 第 8/8 次 gsrunner 预算)**: GR_ZH16T + 原 zh2/nav +
      snap62 + 40000 帧, exit=0 668s, WPNRPK74 f150 首中。
- [x] **判定 PASS: 645/645 同帧快照逐像素零差异** (cmp_menu.py, 差异像素普遍=0) — V13W 对
      前端渲染零影响。页面覆盖 (menu16b_pages.png): 标题/输入名字键盘/主菜单×2/选项控制器
      配置页 (1/2/3 布局, 键位全中文) ≥6 页全部一致。
- [x] 大 dump 清理: T02-T07 dump 仅留 drawlog/gs.log/needle 命中证据 (6-16M); dump_menu16
      仅留 gs.log; dump_menu13/menu16b 快照对保留 (回归原始证据)。

## 任务一收尾最终结论 (子代理 A, 2026-09-15)
- **V13W (SLUS_P_V13W.elf) 定版 PASS**: T01 视觉级 (I012/I021) + T02-T07 drawlog 功能级
  全部 PASS, 零重跑; 三大用户缺陷 (命爆器/g;/µ±+行首错误) 全部落实修复;
  MENU 前端 645/645 帧逐像素零差异。
- 多关卡判定表: T01 越野 / T02 轻武器 / T03 榴弹 / T04 火箭筒 / T05 机枪 / T06 爆破(引 pair
  完整) / T07 指挥(图上+µ± 落实) — 每关教程框完整, 缺陷特征=0。
- 文档: FINAL_ELF.md (定版报告) 已写; ELF_DBCS_PATCH.md §11.4 结果表+§11.5 遗留闭环已补。
- gsrunner 总预算: 8/8 (T03-T07 5 次 + menu16 + menu13 + menu16b)。
- 遗留 (不阻塞定版): I002「引爆器×2」地雷演示框需玩家埋雷触发, nav 未覆盖 (同机制已由
  T06/T07 全序列佐证); 训练 6/7 的第二教程框同理需实机推进。

---

## V14R5 轮 (2026-09-16): 「文本靠下」反汇编 + 证伪试验

用户反馈 (Human_Test_Output/GR_ZH16.iso_3): 部分文本「放置位置一直有问题 — 缩放倍数、
菜单栏文本靠下」; 并明确**每次输出应是新 ISO, 不覆盖旧盘**。

### 反汇编结论 (垂直定位链)
- `RSTextComponent::DrawTheText` (0x21CA20): 纵偏存 this+0xec; StyleIsSet(3)/(2)/(0xc)
  三分支按度量居中; 0xc 支读 this+0xf8 (W→「行数」) 与 this+0xb0 (行数) 取
  CharHeight 参与 `0xec += 0x44 − ...`。
- `RSFont::CharHeight` (0x21ACD0): `font+0x20 (float) × desc->0xc (int→float)`。
- `RSFontMgr::DrawString` (0x219EB0→0x219A70→AddOneWord 0x219F50): 逐字取
  `ComputeCharTextureCoords` 的 UV 四角, 位置由调用方 coords (F12/F13) 给。
- 缩放读数条 (0x2E82D0-0x2E8520): `0x184 = CharHeight − ResolutionYAdjust(f12)`,
  与 `0x180 = StringWidth×0.5 − ResolutionXScale(f12)` 作 DrawString 的 f12/f13。

### 证伪试验 (V14R5-a, 已回退)
假设: face 行高度量 `fld[1]` (引擎原版 26 → ZH14 16 → ZH16 13) 令 CharHeight 减半,
故「以 CharHeight 定位」的文本靠下。改 `zh16_font.py` large/default fld[1] = 16
→ 重建字库 + zh16_gr + 新盘 GR_ZH17.iso。

**实证否证**: 新旧盘同 nav 同帧窗口 (`nav_t03` drawwin 26000-28200) drawlog
**106067 行逐字节全同**; 缩放读数条 coords 亦同 (RA=2E8524 x=589.8 y=44.0 /
RA=2E85E0 x=591.2 y=164.0)。FONT.RES 槽字面确有差异 (slot sha1 f8d2edcc vs
b23664ab) → 字段确实写入, 但**不在该文本的定位路径** → 假设错误。

已回退: `V15_ROW_METRIC = CH` (large/default=13, huge=16 原样); 重建后 ft_slot
sha1 = f8d2edcc… 与试验前逐字节相同, GR_ZH17.iso sha1 = a8e4be38… = 旧盘
(0 差异), 树干净。

### 待续 (真根因未定)
下一步应从「字形墨块在格内的相对基线位置」入手: ZH16 采样行盒 CH=13 而引擎度量
按 26 计; 实测 CJK 墨落 13 盒的 rel 1..11 (ZH14 16 盒 rel 3..13)。用户所指
「靠下」极可能是**记录矩形/采样窗**与调用方期望行高的错配, 而非 face 度量字段。
需: 用 `-grdumpwin` 抓真帧比对 (无 -grsnap, 避免 f20150 挂起), 或反汇编
「行高」消费点 (CharHeight 之外的 0x44/0xb0/0xf8 语义)。

---

## R4+ 轮 (2026-09-16): 三子代理研究 + 可行性定论

R4 交接文档（`NEXT_SESSION_HANDOFF_ROUND4.md` §五）分派的甲/乙/丙三任务由三子代理完成,
主代理对矛盾处独立复核后形成**可行性定论**。**一切结论以
`work/zh16b/FEASIBILITY_ANALYSIS_R4.md` 为准**（三报告矛盾处以该文件 §一复核为准）。
本节只记定论与指针, 细节读原报告。

### 三报告一句话结论
- **甲** (`subagent_jia/REPORT_jia.md`): 字库纹理不走 LoadRSBFile 的 (p0..p3)→s1 位深分支,
  真实链条 = GetTexture→LoadIndexedRSB→diSearchFile→LoadRSBFile(mode=0)→LoadPS2Img(0x51D910),
  psm/CLUT/像素**逐字节原样进 GPU 零加工** → **改 4bpp 是纯 COMMON.PAK 数据改动, ELF 零字节改动**;
  512×1024 4bpp 像素 = 0x40000B 与现行一字节不差 → px_size/tag/记录总长不变 → 后续条目零位移。
- **乙** (`subagent_yi/REPORT_yi.md`): 穷举 EE 侧 UITexture+0x10/+0x12 全部读取者 +
  SetTexturePkt/RefreshActive 全函数 — **无 256/0x100 硬编码**; 提出「PAK 条目无存储 px 尺寸
  + 第四个未定位消费者」论断; 发现 SetTexturePkt 多 chunk 上传 ADDR 步进疑点 (0x518230,
  仅 h>512 触发) 与 **GR.IMG 内第二份 COMMON.PAK 拷贝** (0xE1D3E50, 必做同步项)。
- **丙** (`subagent_bing/REPORT_bing.md`): 名字解析域双层 — IOP 侧 IMG 树 (4096 桶哈希,
  RPC.IRX 全符号) + EE 侧 PAK 内部索引 (FindSurface 链表); LOAD_NEW_1.RSB 实测 **480×480**
  (容量不足 + 域错位) → 顶层条目不能当宿主; 换宿主可行但必含 EE 侧数据级 patch
  (0x58C1C4 "common.pak" 常量同位替换), 估 3-6 天; 闲置通道 domain==5 可挂自定义 pak。

### 主代理复核裁决 (FEASIBILITY_ANALYSIS_R4.md §一, 权威)
- **乙两条核心论断被证伪**: ① PAK 条目**有**存储像素尺寸 — `LoadingTexturePak` 0x51B8D4/0x51B92C
  显式读取 CLUT size/px size; ② px_size@0x1469 = **0x40010** (乙误读 0x1F1F1F1F — 那是
  0x147D 起的像素数据首 16B) → 乙的「第四个未定位消费者」三段论**整条不成立**,
  LoadPS2Img/LoadingTexturePak 两条解析路径均与实测布局逐字节吻合。
- **记录格式定论** (三份样本逐字节一致):
  `{flag,nl,name,psm,w,h,clut_size,clut_blob,px_size,px_blob,pad20}`,
  两 blob **各自自带 16B GIF tag** (clut_size/px_size 均内含 tag);
  walk 四条目 (arrow/new_font_revised/pda-lcd-02/pda_counterparts) 精确落文件尾 'c'@0x61D0F。
- **前轮 ZX2/ZX2B/ZX2D「确定性挂死」证据被削弱**: 三份 run 日志运行器自己标注
  「CDVD_STALL — 模拟器层偶发挂起, 直接重跑」→ R4 交接 §1.5 的「pda 描述符冻结/
  存在第二个尺寸硬假设点」**未获确证, 不再构成先验阻塞** (真实挂点待重跑 ZX2B/ZX2C 厘清)。
- **容量算术定口径** (工具真实常量 X0=20, NCOL=37, CW=13, CH=13,
  yrow(r)=Y0+13r+39·[r≥14], SKIP_ROW=14): 512×512 内 16px 死路 (零边距极限 1024<1212);
  512×608 极限布雷 1216 仅余 4 格, 保结构 1054 不够; **甲方案 512×1024 4bpp 保结构 1860+ 格,
  余量压倒性** — 这是选甲的第一理由。

### 四方案可行性表 (以 FEASIBILITY_ANALYSIS_R4.md §〇 为准)
| 方案 | 核心手段 | 判定 | 工作量 | 阻塞点 |
|---|---|---|---|---|
| **甲 4bpp 位深** | psm 19→20 + h 512→1024 半字节打包, 字节中性 | **可行 (首选)** | 0.5-1 天 | 上传/采样链是否接受 PSMT4 (步骤 A 实测) |
| **乙 扩尺寸** | font 512×608 (8bpp) | **劣 (不推荐)**: 保结构 1054 格 < 1212 | 1-2 天 | 容量零冗余; 多 chunk 步进疑点 (仅 8bpp h>512 触发) |
| **丙 换宿主** | 新独立 pak + IMG 树重建 + EE 常量改名 | 兜底 (甲乙都死才启用) | 3-6 天 | 无纯数据层解, 必含 EE patch |
| **丁 显示侧 Y 基准** | DrawTheText(0x21CA20) 头 / CharHeight(0x21ACD0) **比例补偿** (非常量) | **独立必做** (无论哪条扩容路) | 0.5-1 天 | 影响所有 CharHeight 居中文本, 须全屏回归 |

**推荐执行顺序: 甲 → 丁 → (甲不成) 乙 → (甲乙都死) 丙。**
甲的额外补强: 4bpp 后 px 总字节仍 = 0x40000 = SetTexturePkt 单块上限 (chunk=w×(0x10000/w)×4
= 512×128×4) → **恒单块上传, 0x518230 多块步进疑点对甲免疫**。

### 步骤 A 验证盘设计要点 (下一步第一件事, 单变量只回答一个问题)
- 只回答「上传/采样链是否接受 PSMT4」: psm 19→20 + CLUT 前 16 色
  (项0=`ff ff ff 7f` 墨沿用现行值, 项1-15=透明, clut_size 0x410 与 tag 不动)
  + 像素改 **512×512 的 4bpp 打包** (每行 256B, 低半字节=偶数列, 总 0x20000B)。
- px_size@0x1469 → 0x20010; px tag NLOOP 半字 `00 c0`→`00 80` (0x2000);
  记录尾部 0x20000B 填底色**保定长** (PAK 总长守恒 → MENU.IMG 行 / GR.IMG 拷贝零同步)。
- 判读: 字库正常显示 = 机制成立 → 步骤 B (h→1024, px_size/tag/总长全不动,
  工具按 16px 重排 FONT.RES face 表, 新盘名 GR_ZH20.iso); 失败 = 抓上传 tag 序列判点,
  甲降级转乙 (并改用更高目标高换容量)。
- 附加注意: 墨色 α=0x7f 沿用勿写 0xff (改变混合亮度); w 保持 512 (偶数满足 nibble 对齐)。
- 附带必做 (无论哪条路): 若最终 PAK 总长改变须同步 GR.IMG 第二份 COMMON.PAK;
  重跑 ZX2B/ZX2C 厘清「挂死」真实归因 (当前证据不足以判死任何一路)。

## R5 轮 (2026-09-16/17): 16px 管线建成 + 偏移根因破案 + 度量定案

用户指令: 合并步骤 A+B 用 `方正像素16.ttf` 重建 16px 字库; 诊断「不同页面不同偏移」。
四轮子代理 (16px 重建 / 偏移诊断 / 任务①未竟 / 任务②) + 主代理磁盘清理。**本轮改写了多个 R4+ 结论**。

### 1. 重大更正: 字体系统真实数据源 = MENU.IMG 内部 (非 GR 区 span)
- live FONT.RES 槽 @**MENU.IMG+0xB9120**; live 字库纹理记录 @**MENU.IMG+0x58431**
  (= MENU 内 COMMON.PAK 的 new_font_revised 条目)。GR 区同名 span (FONT.RES @GR+0xCADB640,
  GR 内 COMMON.PAK) 是**死拷贝** — patch 它们对字体系统无效。
- **R4+ 步骤A (GR_ZH20A) 的「PSMT4 验证通过」是空验证**: 只换了 GR 区 PAK, 字体系统仍读旧 8bpp
  纹理。报告 `subagent_jia_b/REPORT_jia_b.md` 的结论按此修正 (其 diff 自检技术仍有效)。
- 佐证: 任务②首轮 fld[1]=26 patch GR 区死拷贝 → y 仍 44; 改 patch MENU 镜像 → y=31, 因果闭合。

### 2. 16px 管线建成 (general-purpose 代理, 8 盘 ZH22 系列, `subagent_16px/`)
- 产物全建成: `gen_font16.py` (方正像素16.ttf 渲染→4bpp→face 表)、`COMMON_PAK_V16.bin`
  (PSMT4 槽零位移)、`ft_slot_v16.bin` (槽回环 PASS)、`SLUS_P_V16.elf` (=DING2+8B cave 布局常量)。
- GR_ZH22H (psm=0x14 + h=512) 完整跑通 → **PSMT4 被字体加载器支持** (独立再证实)。
- GR_ZH22 (GR 区 patch): 16px singles/EN 已正确上屏 (教程帧截图)。
- **唯一阻塞**: h=1024 崩 (帧 8820)、w=1024 崩 → **UITexture::LoadRSBFile (0x51C810) 对
  TW/TH=10 (1024 维) 有 ≤512 假设**。反汇编存档 `subagent_16px/dis_LoadRSBFile_UITexture_51C810.txt`。
  **R4 遗留「第二硬假设点」悬疑就此破案 — 就是它** (ZX2 系挂死当时是模拟器伪影+误读)。

### 3. 偏移根因破案 (general-purpose 代理, `subagent_offset/REPORT_offset.md`)
- **根因: 中文字库行高度量是英文的 1/2 (EN=26, CJK=13)**。缩放条三点严格共线
  (EN y=31 / ZH16 y=44 / ZH19B y=40, `y=CH−57` 零残差); 主菜单/简报/选项列表全吻合 26/13 模型。
- **缩放栏真基准 = EN 原版 y=31** (丁轮的 40-41 目标来自用户目测, 非原版值)。
- 特别收录菜单链: `SpecialFeaturesGR_PS2`(0x344E00)→`FillList`(0x345070)→
  `IkeListButton::DrawText`(0x207480)→`IkeBaseButton::DrawText`(0x21D830), **经 CharHeight** —
  不是丁修复盲区, 是 ×17/13 补偿不足 (缺 17→26)。
- 丁轮 ×13/17 首跑方向反 (y 44→47) 的教训: 引擎 y 轴向下, `y += H−CH`。

### 4. 任务②: fld[1]=26 + cave 摘除 → 全站点精确归位 (general-purposeB, `subagent_offset_fix/`)
- **fld[1] 定案** = FONT.RES 槽内 face 名后第 2 个 u32 (32 位有符号 int, large@0x29/default@0x92C),
  即 CharHeight 的 `desc->0xc` = **live 度量本体** (ReadResourceFile__9RSFontMgr 0x219380 解析序
  交叉定案)。**两桩历史误诊就此解开**: V14R5「fld[1] 惰性」与 16px「度量=记录几何派生」
  皆为 patch 了死拷贝 / fld 与记录同变所致。
- **GR_ZH24.iso** (现役推荐): SLUS_P_M26.elf (cave 完整摘除=V14 全等) + MENU 镜像槽 fld[1] 13→26。
  实测: 缩放条 y=**31.0 与 K99 EN 基准逐帧 0 偏差**; drawlog 106,067 行 Δ0; 主菜单 129..369、
  帮助条 419、简报 131/152/173、LOADING 391 全部与 EN 逐值相同。
- GR_ZH24B (cave ×2 过渡) 同样 31.0, 留档不推荐 (对 huge/小字体站点一并翻倍更激进)。
- 副作用: 13px 字面装进 26 度量四边形 → 纵向 2× 拉伸 (可读)。**16px 字面上屏后此拉伸自然消失**
  (16px 字形 + 26 度量 = EN 同构布局)。

### 5. 环境/磁盘
- **记忆卡纪律**: 每个 gsrunner run 必须独立 memcards 副本 (并行共用会污染脱轨; 干净基准
  `subagent_ding/memcards_ding`)。`memcards_zh12` 已废。
- **磁盘清理 (主代理)**: 删 1431 个 `*_eeram.bin/*_iopram.bin` (zh16b 35G→4G) + 22 张实验盘
  (ZH17/18TST/19/20A/16T/22 系列/25 系列孤儿盘) — C 盘可用 8.7G→73G。
  **今后每轮 gsrunner 后必须删 dump 大文件再退出。**
- 保留盘: ZH12/13/13B/14/15/16/16_user_r2/19B/24/24B。

### 6. 待办 (下一会话从这里开始)
1. **任务①重发 (general-purposeB)**: RE 修 LoadRSBFile(0x51C810) 的 ≤512 假设 → 打通 1024 维
   → 16px 终版盘 (管线产物全在 `subagent_16px/`)。ELF 合成 = M26 (无 cave) + V16 的 8B cave
   布局常量; face 度量 fld[1]=**26** (EN 同构, 与 ZH24 一致; 勿再用 ×17/16 — 真基准是 31)。
   新盘 GR_ZH26*.iso。
2. 16px 通后: 字面 26 度量观感确认 (拉伸应消失), 必要时微调; 用户实机验收。

### 7. 任务① V17 轮结果 (2026-09-17, general-purposeB, `subagent_16px_fix/REPORT_16px_fix_v17.md`) — 未通过
- **≤512 假设点不在游戏代码**: 逐指令核对 LoadPS2Img(0x51D910)/SetTexturePkt(0x5176E0)/UIPacket ctor(0x51ACC0)
  — W/H 校验 `slti 0x401` 允许 ≤1024; TEX0 TW/TH 倍增循环、TBW、TRXREG、BITBLTBUF、DMA 分块
  B′=(0x10000/W)<<2、包缓冲 0x27100B **全动态无 ≤512 立即数**。字库记录确认 mode=0→LoadPS2Img。
- **4 轮判别全证伪**: R1 ZH26 (alloc 改 0x40000)→boot 死亡 → **铁律: alloc 必须恒 0x40010,
  region=alloc−0x10, 记录总长恒 0x4044C**; R2 ZH26B (拆双 GIFTAG)→崩 2850; R3 ZH26C (分块
  256→512)→崩 2840; R4 ZH26D (TEX0.TW/TH 钳 9)→崩 2840。
- **定位结论**: TEX0 采样侧/GIFTAG 结构/分块粒度全排除 → 故障 = **TRXREG (1024,H) 图像传输区域
  本身**, 在游戏代码之下的传输层 (VU1 宏或 PCSX2 GS 的 PSMT4 大区域处理), 盘侧常规手段不可达。
  崩帧 2840-2850 = 首次字库纹理绘制, 与 ZH22I 一致。
- **现役推荐盘维持 GR_ZH24.iso** (13px + fld26 + y=31); ZH26 系列均为判别实验件勿用。
- **有效遗产**: `ft_slot_v17.bin` (16px FT + fld26, 回环 PASS)、`SLUS_P_V17.elf` (M26+w62 cctc)、
  alloc/region 约束、全套反汇编与脚本。
- **下一步候选** (唯一未证伪的盘侧路线优先): ① 记录 GIFTAG 流内嵌 A+D 重写 TRXPOS/TRXREG,
  把 512×1024 拆成 (512,256)×4 象限拆传 (R2 未改 region 不构成反证); ② PCSX2/gsrunner 侧查
  PSMT4 大区域传输; ③ VU1 微码 dump。实机与模拟器可能在 ② 上表现不同 — **实机验证 ZH26C/D
  现象可作为传输层归属的判别实验**。

### 8. 并行三任务: 解耦/行距/模拟器 (2026-09-17, general-purposeB×3 + 续作)
- **任务C 行距** (`subagent_spacing/REPORT_spacing.md`, GR_ZH29): 行进距字段 = **fld[13]** (FD+0x24,
  EN 不变式 fld[13]==fld[1], M26 槽已=26); **重叠全来自运行时覆盖**: RSHTML::SetText 0x21BD6C 立即数 18 /
  教程模板 20 / ctor 0x21D1A4 立即数 12 (消费点 +0xf8, ComputeDrawXY 0x21CA20 行游标 +0xf4 += +0xf8)。
  修复 = SLUS_P_V19.elf 三跳板 cave 0x417600 `CLAMP: f8 = max(原值, CharHeight)`。实测: 教程框 20→26、
  简报 18→26、段距 3×26、缩放条 y=31.0 保持、字距 (CharWidth+style+0x18) 与度量无关零变化。
- **任务A 解耦** (`subagent_decouple/REPORT_decouple.md`, 续作代理): V18 hook 0x219ADC (DrawString 内层
  CharHeight 消费点) 仅把 UI 字体四边形高 26→13 (字形 1:1), 不动定位/行距; 与 V19 cave 交集 0 直接并集。
  **终盘 SLUS_P_V20.elf = M26 ∪ V18 ∪ V19 (249B, diff 锁三向全等)**。
- **★ 终盘 GR_ZH31.iso 通过** (2 轮完成): 缩放条 y=31.0 (574/574=EN) + **字形 1:1 (墨迹带 9px, ZH24 为
  2× 拉伸且两行墨迹融合 38px)** + 教程框行距 26 无重叠 (墨迹隙 16px) + 战役简报行距 26 (F35817: 78/26/26)
  + drawlog 106,067 Δ0 复现性逐字节一致。**13px「位置+字形+行距」三项全对 = 当前最佳盘**。
- **任务B 模拟器** (`subagent_gs/REPORT_gs.md`): 崩因 = **PCSX2 Gif_Path::CopyGSPacketData 攒 EOP=0
  长链包溢出 9MB 缓冲** (17 份 minidump 一致, 0xC0000005 WRITE; Release 断言被剔除; 泄压阀被 IMT 门控,
  游戏从不设 IMT)。1024 维本身 GS 合法, 只是让积压更快达 9MB (≈2810 起积压, 2840 崩)。
  修复版 `pcsx2-gsrunner-p4.exe` (缓冲 64MB + 压力切片 + 守卫) 已证 **ZH26C (4bpp 1024×512) 存活**
  (28300 帧 OVERFLOW=0) 且 ZH24 回归精确一致。**用户要求不依赖定制模拟器 → 盘侧拆传任务进行中
  (subagent_split, 路线 A: SetTexturePkt chunk 0x51805C 0x10000→0x4000/0x2000 + 修 0x518230 i×w 步进 bug;
  路线 B: px blob 内嵌 A+D 象限拆传)**。
- 环境教训: gsrunner 只认反斜杠 ISO 路径, 正斜杠/被 Git Bash 吃掉会静默 frames=0 (trace 落
  C:\gr_build\dumps\boot_trace.txt); 路径必须写进脚本 raw string。

### 9. 盘侧拆传成功: 1024 维在标准模拟器存活 (2026-09-18, general-purpose, `subagent_split/REPORT_split.md`)
- **EOP 语义定案 (路线A 判死)**: SetTexturePkt 分块循环 (0x5181B8-0x5182D4) 每块只写 16B **DMA REF
  tag** (QWC=qW+1, ADDR=src+i×(B′+16)) — chunk 级无字节预算无 EOP 位, GIF tag 全来自 blob 本身。
  「0x518230 步进 bug」为误读 (a0 在 0x518210 已重赋为 B′+16, 无 bug)。
- **崩溃字节机理**: 容器 tag {NLOOP=0x4000,EOP=1,IMAGE} 需 0x40000B, REF 实付 0x3FF80B → **缺 0x80B
  → 包永不闭合** → 吞噬后续 PATH3 (含逐帧字库重传 262KB/帧) → 2840 溢出崩。缺口在游戏 n30 数学内,
  ELF 常规手段不可达 → 改走路线B。
- **路线B 实施 (路线A 之替代)**: px blob 重写为 **8 个自闭合包** ([PT NLOOP=1 EOP=0][A+D TRXPOS
  重定位][IT NLOOP=0x800/0x7E8 **EOP=1** IMAGE][64KB 行数据]×8+尾包), blob 恒 0x40010 (alloc 铁律不破),
  PAK 总长不变。**SLUS_P_V22.elf = V17 + 4B** (0x5182EC `bne→NOP`, CLUT 强制 psm13 形状 1040B 节点,
  消 645 个垃圾 tag; 4bpp 只用前 16 项零视觉影响)。
- **原版 gsrunner 判别全过** (sha256 与官方逐字节同): exit=0、**28300 帧全程**、两轮 drawlog
  8,460,375B 逐字节一致; drawlog 106,067 Δ0; LBA 774335 首读 27107; 教程帧 **16px 中文整段上屏**;
  缩放条 **y=31.0×574**; 字形与未拆传原始 blob (ZH26C-on-p4) 同帧 **10/10 逐字节一致** (像素级零差)。
- **终版 = GR_ZH32B.iso** (GR_ZH32.iso 为中间件勿用)。**「16px + 标准模拟器」成立**。
- 遗留观感项: ZH32B 基于 V17 (fld[1]=26 → CharHeight=26): 16px 字面在 26 四边形中 1.625× 纵向拉伸 +
  行距覆盖 (18/20/12) 未修 → **待合并 V19 行距 CLAMP + V18 四边形解耦的 16px 变体 (四边形高 26→16)
  = 最终 16px 完美盘** (V23/GR_ZH33)。

### 10. 乱码破案 + 16px 逐字正确盘 ZH35 (2026-09-18, general-purpose, `subagent_mojibake/REPORT_mojibake.md`)
- **根因**: 引擎对字库纹理的 **u 采样偏置随 psm 不同** — 13px/PSMT8 = rec.u+20, 16px/PSMT4 = rec.u+4
  (Δ=16 texel=8B=1 个 PSMT4 word, MENU UITexture 装载管线 psm 相关位差; 指令站点未封口, 数据侧修复正交)。
  gen_font16 沿用 13px 绘制原点 X0=20 → 16px 盘每字取到左移一格字形 → 全部错位成别的字 (清晰但错)。
- **三方证据**: ①静态 (V22 cave u0=16c+0 vs gen x=20+16c); ②13px 偏置实测 (EN 带 rec.u 从 0 起, 墨在 x=21
  ⇒ 采样=u+20); ③16px 实帧逐格取证 (ZH32B 教程 line2 六格全部=期望格−1 列, u≈68/768 斜率均=1 ⇒ 纯平移)。
- **fld[2]/fld[3] 定案**: 渲染链**无读者** (FD 域读者全集 = +0x0C fld[1] / +0x08 fld[0] / +0x20 fld[12] /
  +0x24 fld[13] / +0x38 记录 / +0x44 nrec; +0x10/+0x14 零读者) → 死字段, 32/26 皆无影响 (主代理头号嫌疑被证伪)。
  **FT[0x44] 定案** = nrec = fld[4]×fld[5] = 32×7 = 224 (cctc bounds 阈值, idx<224 走 FT 记录)。
- **修复 (纯数据, ELF 零改动)**: 图集绘制原点 **X0: 20→4** (格 x=4+16c; EN 带/▲▼ 同步 u+4; 图标窗
  (19,198,64,221)→(3,198,48,221))。ELF 仍 = SLUS_P_V22.elf。
- **GR_ZH35.iso (16px 逐字正确盘)**: 教程帧 37 字 + line2「键退出训练。」逐字正确; 记忆卡屏 (®/（）/、)
  逐字正确; 缩放条 y=31.0×574 (=EN 0 偏差); drawlog 106,067 Δ0; **原版 gsrunner 全程存活**。
  ZH34 (X0=4, fld16, y=41) 为根因验证留档。**ZH32B/ZH33 勿用 (乱码盘)**。
- 解码方法论教训: blob=8 段 GIF 流, 正确还原必须从 0x146D 起 + 顺序 GIF 语义 (9 EOP); 此前 A/D/E 图的
  「每 4 行截断/最右错位/最左错误」全部是主代理解码伪影 (起点偏 16B + 段偏移公式错), 图集实际完好。
- **遗留**: ZH35 谱系 (V22) 不含 V18B/V19 → 字形 1.625× 拉伸 + 教程框行距 20 未修 → 最终合并 ZH36 =
  MENU_V24 + SLUS_P_V23.elf (V22∪V19∪V18B, 已建好且判别轮全绿) 进行中 (subagent_final)。

### 11. ★ 16px 完美盘 GR_ZH36 终验通过 (2026-09-18, general-purpose, `subagent_final/REPORT_final.md`) — 目标达成
- **GR_ZH36.iso = K99 基底 + SLUS_P_V23.elf@LBA295 + MENU_V24.img@LBA776286** (V23 = V22 拆传 ∪ V19 行距
  CLAMP ∪ V18B 四边形高 16)。自检: ISO diff vs ZH35 100% 落 ELF 段, 数据面零改动。
- **原版 gsrunner 终验 (exit=0/475s/28300 帧全程, 一次通过)**:
  | 判据 | 结果 |
  |---|---|
  | 逐字正确 | 教程 line1 37 字 + line2 与 ZH35 逐字节相同; 记忆卡屏与 ZH35 参照逐像素 0 差异 |
  | 位置 | 缩放条 y=31.0×574 (=EN 零偏差), B 站阴性 164.0 |
  | 不拉伸 | line1 墨高 14px (ZH35 拉伸盘同窗 30px), 与同 ELF 参照逐像素同构 |
  | 行距 | 26 无重叠 (y 90→116, 墨迹净空 12px; V18B×V19 正交) |
  | 稳定 | drawlog 106,067 Δ0, PC 分布同基线, 与 ZH33r1 drawlog 逐行 0 差异 |
- **用户最终目标达成**: 汉化完整 ISO + 16px 字库 + 字体单元正确 + 显示位置正确 + 不拉伸 + 标准模拟器可跑。
- 环境注: `subagent_ding\memcards_ding` 已不存在, 后续 run 记忆卡从 gsrunner 干净 `memcards` 现拷。
- 现役盘清单: **GR_ZH36 (16px 终盘)** / GR_ZH35 (16px 逐字正确但拉伸, V22 谱系) / GR_ZH31 (13px 终盘) /
  GR_ZH24 (13px fld26 初版) / ZH34 (乱码根因验证留档) / ZH32B/ZH33 (乱码盘勿用) / ZH26C/D (1024 维判别件)。

### 12. ISO 重建校对 + BUILD_MANIFEST (2026-09-18, general-purposeB, `BUILD_MANIFEST.md`)
- 25 盘重跑脚本 + MD5 对比: **15 盘逐字节复现** (组装管线字节确定); ZH15 不符 (MENU_MCZH.img 晚于盘被改, 保旧态)。
- **删 11 张 (回收 ~16.9 GiB, 库 41GB→22GB)**: ZH13/13B/14/19B/24/26C/27/29/32/32B/34。
- **保留 14 张**: 基线 4 (ZH16/31/35/36) + 依赖缺失 6 (ZH12=全谱系 GR 区数据源永不删, ZH24B/26/26B/26D/33) +
  脚本未存档 3 (ZH16_user_r2 用户备份, ZH37C/D 配方未存档; 37D 为 1.215GB 截短盘) + ZH15 (MD5 不符)。
- **产物**: `BUILD_MANIFEST.md` = 从零重建流程 (K99+ELF@LBA295+MENU@LBA776286+GR 区迁移+spans) + 25 盘全量表
  (脚本+命令行+依赖+MD5) + 依赖缺失重建链 (M2X.elf 一键可重建等)。MD5 存档 `_md5_existing/_md5_rebuilt.txt`。

### 13. 菜单乱码收口: 破案 + ZH37E (2026-09-18, general-purposeB, `subagent_menu/REPORT_menu.md`)
- **前任「huge face 补满」理论被证伪**: judge37 九行全部仍乱且 ZH36/ZH37 菜单像素级相同 (md5 同);
  前端按钮 (FontID 1/3/4) 实际用 **large/default face (nrec=224)**, huge (nrec=96) 只被 fonts[6]/[7] 引用。
- **根因① (已修)**: `CharWidth` cave 0x416FBC 对 pair 字形硬编码 **13** (13px 遗产, V17 的 13→16 diff
  漏改此 cave) → 16px 字形按 13px 步进重叠 (row1 墨宽 55px=16+13×3 精确吻合)。
  **ZH37E = ZH36 + 1 字节 (13→16)**。
- **根因② (未修, 遗留)**: 前端对 MENU.IMG 图集的放置/采样存在 **+4 texel 位差** (mojibake 报告遗留
  「UITexture 放置管线 psm 相关 8B 位差」的前端侧): 每字形左切 4px + 前格右缘条带。教程/游戏内用 GR.IMG
  另一份图集放置正确, 故当年未暴露。ZH37F (图集每行预移位补偿) 失败留档 (记录区结构比线性假设复杂)。
- **ZH37E gsrunner 终验**: 菜单步进/居中已正确 (余 4px 位差条带=根因②); 教程 line1 逐字正确且 pair
  右缘 4px 恢复 (比 ZH35 更完整); 记忆卡屏正确; drawlog 106,067 Δ0; 28300 帧不崩; y=31 保持。
- **推荐盘: GR_ZH37E.iso** (菜单间距已修+无回归); ZH37C (宿主崩溃) / ZH37D (截断残盘) / ZH37F 勿用。
- **遗留下一会话**: 根因② 位差站点最终修法 = shell UITexture 放置 ELF 修正 (ZH37C 是正确邻域但需重做);
  用户侧双环境判别 (subagent_split/REPORT_gs.md 流程) 仍建议执行。

### 14. 用户模拟器版本考古: v2.2.0 vs gsrunner(v2.9.32) 乱码差异归因 (2026-09-18, general-purposeB, `subagent_vercheck/REPORT_vercheck.md`)
- **背景**: 用户完整版 PCSX2 = v2.2.0 (2024.10.31) 跑 GR_ZH37E 仍乱码 (记忆卡屏正常/其余撕裂状);
  gsrunner 逐字正确。用户最新稳定版 = v2.8.2, 怀疑版本间 GS 代码差异。
- **可追溯性**: `C:\gr_build\pcsx2_src` 本地 tag 完整 — v2.2.0=2d5faa627 / v2.8.2=fd9d310cc /
  HEAD=v2.9.32=236f67a82 (gsrunner 构建源)。全程只读 git (log/diff/show), 未动主工作树 GR 定制。
- **Phase B (后端查证, 实锤)**: 我们全部 10/10 个验证 run 脚本显式 `-renderer dx11` → **"逐字正确"
  结论是在 HW/DX11 下取得的** (非 SW); gsrunner inis 无 GS.ini。用户 v2.2.0 Auto 亦为 HW (N 卡→
  Vulkan/OpenGL)。**后端类别相同, 版本是主要受控差异**。
- **Phase A (代码考古)**: GSTextureCache(HW) v2.2.0..HEAD 191 提交, 4bpp/失效相关 T0 级候选:
  - `fde045241` (v2.6.0): 删 FullRectDirty 的 m_age==0 早退 — 每帧同址重传→target 恒 age 0→
    v2.2.0 永不整覆盖重建, 只能靠脏矩形精度 (与"记忆卡屏正常/后续乱码"病症精确吻合);
  - `76d5994c1` (v2.4.0): DirtyRectByPage 同格式+块级偏移修正 (v2.2.0 仅格式不同才平移) —
    GR 每段 TRXPOS 行重定位→脏矩形错位→行级漏失效→撕裂;
  - `63d3dd997` (仅 v2.8.x): LookupSource 脏区重叠强制 Update;
  - `eec395131`+`32a3e8e62` (仅 v2.8.x): 4bpp 脏矩形翻译+trbpp==4 nibble 显式处理。
  T1/T2 支撑提交若干; **Gif 侧 6 提交全为警告/版权, 排除**; GSClut 默认路径无实质变化。
- **判定**: 最高置信 = **v2.2.0 缺失 HW 纹理缓存失效修复 (版本问题)**, 非 gsrunner 特殊性。
- **用户侧行动** (按优先级): ① v2.2.0 里 F9 切 Software 渲染同一界面 — 1 分钟二分后端;
  ② 手动指定 DX11 vs Auto; ③ **升级 v2.8.2** (含全部 T0 修复; v2.6.0 缺 4 处不作最低推荐)。
- Phase C (worktree 构建 v2.2.0 实测复现) 已评估放弃: A+B 证据链完整, 构建成本 1h+/>2G,
  等效判定由用户 F9 二分 1 分钟可得。

### 15. root2 遗留审计 + 日字标定盘 ZH39P + 匹配脚本计量闭环 (2026-09-19, general-purpose, `subagent_root2/REPORT_zh39p.md`)
- **背景**: 前两轮代理被中断但留有完整成果——root2 (REPORT_root2.md: 根因②数据侧修复+ZH38 终盘+ZH38CAL) 与
  pattern 半成品 (ZH38P, 系 ZH37E 基底未含修复)。本轮先审计后续作。
- **root2 三主张独立重算全过** → **GR_ZH38.iso 维持推荐终盘**:
  ①全盘 diff vs ZH37E = 84,215B 全落 MENU.IMG 字库 blob 区 (SHA256 b512b992... 一致);
  ②菜单复跑 exit=0/406 snaps 无条带; ③drawlog 与 ZH37E 基线逐字节相同 (106,067/session)。
- **根因② 修复定案 (数据侧)**: MENU.IMG blob 每行左移 2B (4 texel), 行尾补 0x11, 段头 48B/FT/CLUT/
  µ±图标带 (y196..224)/GR.IMG 拷贝零改动 → 前端采样窗 [16c,16c+16) 恰命中 [0+16c,16+16c)。
  ZH37F 挂死机理 = 基址错 0xF0+段头被当像素移位 (GIF 结构损坏), 本修法已绕开。
- **菜单 Y 定案**: 根因② GIF 寄存器实证 (252 顶点 u≡0 mod16) + 横杠实测 N≈+2.5px 且与 EN 原盘 (K99)
  金标准 Δ≈0、行框线逐线一致、fld16→26 位移=0 → **垂直无缺陷不修**; 用户"偏上"感知与条带伪影+墨分布变化相符。
- **GR_ZH39P.iso (标定盘)**: 直接对 ZH38 实际 blob 重绘日字图案 (外框 col0/15+row0/15, 中央杠 rows7-8,
  1310 格, MENU 份按左移后几何/GR 份 X0=4), 段头/记录/CLUT/行408+ 零改动; diff vs ZH38 = 226,644B
  全锁两 blob 区间; 自检全过 (4bpp 回环逐格==图案)。
- **match_pattern.py** (subagent_root2/): 重定标到真机几何 (16 texel→~14px/步进 16px, δ 判据=竖柱密度:
  δ=0 每格 2 柱/δ=+4 合并 1 柱), --synth 3/3 PASS, 面板 N 逐行精确。
- **gsrunner 全套测量 (dx11, 闭环 PASS)**: 主菜单 ×3 帧 δ=+0.00{0:5}; 记忆卡对话框 δ=0; 训练选关 δ=0;
  教程对照 (硬门槛) δ=0; N≈+2.5 与 root2 口径一致。**新发现: 开机记忆卡屏走第三份字库** (ZH39P vs ZH38
  该屏 ndiff=0, 渲染正常, 非标定目标, 记录在案)。
- **用户侧指引**: ①GR_ZH38 正常游玩 (菜单条带已修, 教程/游戏内与 ZH37E 逐字节等价); ②GR_ZH39P 同屏截图
  (原生分辨率/GS 1x/无滤镜) 跑 `subagent_root2/match_pattern.py <png>` 或交回测量; 用户侧应得 δ=0,
  δ=+4 或每格 1 根合并柱 = 其模拟器采样窗左偏 4px (PSMT4 语义差异证据, 连 *_ann.png 交回)。

### 16. 用户模拟器垂直偏移量化: OpenCV 检测 + gsrunner 原生对照 (2026-09-19, 主代理)
- **背景**: 用户在 ~3.5x 内部分辨率模拟器上跑 GR_ZH39P (日字标定盘), 确认左右采样正常 (根因②修复
  在用户侧生效), 但菜单文字"明显错位" (竖直方向)。要求 OpenCV 脚本检测 + 自编译模拟器截图目测对照。
- **交付**: `tools/cv_vcheck.py` (Sobel 边缘行聚法 v3: 带检测→杠=短带对中点/槽=等节距长线;
  花背景菜单需人工读带表, 帮助条全自动); 对照图+原生帧 → `Human_Test_Output\GR_ZH39P_gsrunner_对照\`
  (cmp_menu_gsrunner[3x]_vs_user.png ×2 / cmp_helpbar ×2 / snap_f24986-25172 原生 4 帧)。
- **测量结果** (N = 杠中心−显示框中心, 正=偏上, 原生 px):
  | 屏 | 用户模拟器 (~3.5x) | gsrunner 原生 1x |
  |---|---|---|
  | 帮助条 (△提示行) | **+3.2** (杠 44.5 vs 槽心 54.5, s=3.13) | **≈−0.6** (杠 395 vs 槽心 394.25) |
  | 菜单 7 行 (逐行 6.1~6.6) | **+6.2** | **+2.5** (root2 金芯口径, =EN 原盘) |
- **判定**: 用户模拟器上文字相对 UI 框**整体高 ~3-4 原生 px**, 两屏方向/幅度一致 → **高分辨率渲染
  (放大采样)伪影, 非盘缺陷**。图案完整性两侧一致: 杠在格中心 (bar_dev≈0)、格 56×52 (纵横比 1.08,
  均匀 ~3.5x, 无压扁/无拉伸)、无左右错位 (用户亦目测确认)。
- **机制**: PS2 GS 原生对顶点坐标取整; 放大内部分辨率后 PCSX2 高精度渲染使文字四边形相对取整的
  UI 框产生位移 — PCSX2 经典文字偏移类问题 (Manual Renderer Fixes 的 Round Sprite / Half Pixel
  Offset 即为此设计)。
- **用户侧验证/规避**: ①内部分辨率改 Native (PS2) 1x → 应与 gsrunner 原生截图一致 (判定性实验);
  ②保持高分辨率则试 手动渲染修正: Round Sprite=Half → Half Pixel Offset (Sprite) 逐档试;
  ③若 Native 1x 仍偏 → 截图交回继续查 (当前证据不支持)。
- **盘侧结论不变**: GR_ZH38/ZH39P 在原生分辨率渲染正确 (=实机行为), 满足"标准模拟器可运行"目标。

### 16b. 复测修正 (2026-09-19 晚, 按用户方案: 二值化+低通滤波) — §16 数值修正
- **用户指正两点均成立**: ①对照图 native 1x 侧确有可见偏移 (3x 放大后 5-7 屏幕px); ②早前帮助条裁剪
  截半字形。已按「高斯低通+高阈值二值化」重测 (半透明叠加层被排除, 带检测不再被污染)。
- **参考线双族结构 (关键)**: 菜单行槽边框 = 暗线(半透明,灰~40)+亮线(不透明,灰~180+) 成对,
  两族各等节距 27.5 原生px (两侧一致), 互错 ~3.6 原生px; N 须对「边框对中心」计。
- **修正后数值** (N=杠−边框对中心, 正=偏上, 原生px):
  | 参考 | gsrunner 原生 | 用户模拟器 (~3.2x) |
  |---|---|---|
  | 菜单行槽 (逐行) | **+1.5~+2.5** (=对照图里 native 可见偏移的来源) | **+4.7~+5.2** |
  | 帮助条箱 | ≈−3~0 (箱心定位弱) | **+2.6** |
  | 行0金底 (root2 口径) | −2 vs 金芯 (=EN 原盘同位) | — |
  → **用户模拟器额外上移 ≈ +2.5~3.5 原生px** (两屏同向), 叠加在盘固有 +1.5~2.5 之上。
- **图案完整性复核**: 两侧杠都在格中心 (bar_dev≈0), 用户侧等比 ~3.2x (菜单格跨48px/15) —
  帮助条格为全高格 (顶19.5/杠44.5/底69), 早前"半高格"为误读。
- **判定修正**: 盘侧固有偏移 (+1.5~2.5, =原版行为) 与模拟器放大伪影 (+2.5~3.5) **两个成分都在**,
  用户所见 = 两者叠加 (~+5)。盘在原生(=实机)下位置正确; 不建议为放大渲染专门下移墨迹
  (会让原生/实机偏低)。
- **对照图重制** (不截半): cmp_helpbar_full_gsrunner3x_vs_user1/2.png, cmp_menupanel_gsrunner3x_vs_user3.png,
  gsrunner_helpbar_native_full.png (目录同 §16)。

### 17. Y 居中决策 + 补丁站点破译 + ZH40 任务固化 (2026-09-19, 主代理)
- **用户决策**: 确认"原版墨迹就是歪的"（EN 13px 字配 CharHeight=26 居中同样偏上）; 要求**修改显示位置
  （不动墨迹）**使文字在**原生分辨率**下栏位居中 → 原生/实机为基准, 超分辨率各自叠加伪影不再是盘问题。
  用户在其帮助条截图上红线标注 框顶 y=9/杠心 y=44.5/框底 y=99（脚本提取, 与我方测量吻合: 杠比框心
  高 2.9 原生px, 含其模拟器 ~+3 放大伪影）。
- **补丁站点 0x21D940 破译**（主代理反汇编, 前端 UI 文本组件渲染器 样式 0xC 垂直居中分支）:
  `Y += (框高−CharHeight)/2 + 组件Y偏移` — 引擎按 26 居中而字格实 16px → 墨迹偏上 ~(26−16)/2 量级;
  补丁 = `subu v0,v1,v0` → `addiu v0,v1,-K`（0x24620000|(−K&0xFFFF), 下移 (26−K)/2）;
  相邻样式 0x8 底对齐段 0x21D97C-0x21D990 也用 CharHeight（帮助条可能走此, 需分测）。
- **工具就绪**: `subagent_root2\build_zh40.py`（YK 参数化+自检 diff 恰 4B）、`run_zh40_menu.py`（菜单采集
  模板）、基线锚定帧已提取 `keep_baseline_zh39p_f25110.png`/`f25048`/`keep_zh38_menu_f25110.png`。
- **ZH40A (K=16) 状态**: 构建命令被取消但产物已落盘（1.648GB, 待验证补丁位; 不完整则删除重建）。
- **任务书固化**: `TASK_ZH40_Y_centering.md`（自包含: 事实/工具/四 Phase/纪律/红线提取脚本）——
  因子代理基础设施故障（GLM-5.3-Flash 缺思考档位, general-purpose 与 B 均无法启动）, 本轮由主代理
  备齐全部材料移交下会话执行。
- 环境注: anaconda 已装 opencv-python-headless 4.10.0.84 + numpy 固回 1.26.4（numba/scipy 兼容保持）。
- **ZH40A 验证补充**: 大小与 ZH38 逐字节同、补丁字 0x2462FFF0=addiu v0,v1,-16 ✓ 已建成可直接用;
  root2 旧脚本注释 −16 实编码 0x2462FFF6(=−10) 系笔误(未运行过), build_zh40.py 已纠正。

### 18. round7 全仓清理 (2026-09-19, 主代理)
- **73G→18G**: gr_build/iso 40G→5G (仅留 ZH43 终盘/ZH31 备选/EN_ORIG 对照, 删 23 张历史盘 — 构建链脚本全入库可复现);
  gr_build/dumps 4.5G→保留 zh2/nav.txt; work/ 各轮 dump/ISO/MENU.img/iconfix/han_v2 recomp 死路/ps2recomp_tool 全清。
- **黑屏证据三件套保留** (subagent_root2): dump_zh43_updn / dump_zh43_updn_fld / dump_en_updn — 下会话 GS 网格提交层调查的直接输入。
- **ELF 世系归拢** archive/elf_lineage (29 件 U→V43 全 git 追踪); **SLUS_P_V43.elf** 从终盘 LBA295 抽取,
  8 补丁词+0x5182EC nop 全断言通过 (sha256 3a0d76c294698d9b033962ef54bc5a9d)。
- 文档: HANDOFF_ROUND3→docs/handoffs, PROJECT_STATUS→archive/docs_legacy, gr_build 95 件 run_*.py→archive/scripts_legacy;
  README 重写; 全量清单见 **docs/CLEANUP_20260919.md**。

### 19. round8 六类目录重构 (2026-09-20, 主代理)
- **六类归置**: tools/ (工具+emu) · build/ (构筑: bases/iso/fonts) · docs/ (文档) · work/ (临时工作区) · third_party/ (第三方依赖) · test_results/ (测试结果); 根目录仅 README + 七目录。
  移动: bases→build/bases, gr_build/iso→build/iso, gr_build/pcsx2{,_src}→tools/emu/, gr_build/run→tools/emu/run, gr_build/src|deps→third_party/, tools/emu_source|dep→third_party/, hanliu→tools/hanliu, han_v2→docs/han_v2, Human_Test_Output→test_results/, 根字体→build/fonts/, gr_build/tmp→work/tmp, dumps/zh2→work/benchmarks/zh2, gr_build 控制脚本→work/。
- **路径改写**: `work/migrate_paths.py` (tokenize 两趟 + py_compile 回验) — 550 文件 / 1512 处 C:\gr_build 与仓库绝对路径 → `os.path.join(REPO_ROOT, ...)`; 手修 3 个裸 ROOT 脚本; 映射修正 (GR_K99/Ghost Recon) 31 处; 断裂 ELF 引用重指向 archive/elf_lineage 58 处。
- **C:\gr_build junction 已摘除** (cmd rmdir, 仅删链接); 仓库 gr_build/ 剩空壳 (0 文件, 被进程 cwd 占用, 重启后删)。
- 文档: README 重写 + **docs/REORG_20260920.md**; .gitignore 重写为六类版 + test_results 白名单 (dump_* 转储不入库)。
- AI 纪律: 手算路径一律用脚本改写+编译回验, 不手工 sed 绝对路径 (跨平台反斜杠坑)。

### 20. round9 黑屏破案 + GR_ZH49 五字节修复 (2026-09-21, 主代理 + 三子代理, 分支 bug/blackout-vram-dig → main 已合)
- **用户假设被证实**: "改字库显示逻辑时误伤显存处理" — 真凶确实是字库改造期引入的 ELF 补丁。
- **真闸门 `0x5182EC`** (SetTexturePkt CLUT 形状选择器): `bne a0(tex->psm),0x13` 的分支体。
  EN: psm==PSMT8 → 16×16/1KB CLUT (REF QWC=65); psm!=0x13 → 8×2/64B (REF QWC=5)。
  ZH43 NOP 掉了它 → **所有** CLUT 纹理被强制走 256 项形状, 而简报页选中条高亮是合法 PSMT4+16 项
  → 65-QWC REF 让 GS 多读 960B 垃圾 → GIF 失步 → 该帧其后全部提交被吞 → 整屏黑。
- **最小修复 GR_ZH49 = 5 字节, 不动 PAK**: ①恢复 0x5182EC 原词 0x14830005 (@ISO 0x4ABB6C);
  ②字库 CLUT 节点 NLOOP 0x40→0x04 ×2 副本 (声明 80B/16 项; 字库像素只采样索引 0/1, 523,520 像素实证)。
  sha256 a772f958...（build_zh49.py 自带差异断言）。
- **验证**: 黑屏窗 646/646 帧存活 (ZH43: 24/646); CLUT TRXREG 回 8×2; CJK TEX0 psm=0x14 全 646 帧;
  ink 42→14695 (EN 14167); **菜单回归 0/234 帧差异**; 教程 884/916 像素级一致, 32 帧差异 = 一处
  20×28px 字形单元 (0.367%), 已排除平移 → 判读为 ZH43 越界读取的修正产物。
- **三子代理收敛** (报告均入库): gsmesh (EE 侧反汇编/候选闸门表) · gspack (GS 包流, 第一分岔点
  F35854 = 高亮 CLUT 步骤) · vram (VRAM 审计, 字库足迹字节守恒)。
- **采集零改码**: 全部出自现成 `pcsx2-gsrunner-zh43diag2.exe -grreglog 1 -grreglogwin 35050 37750`;
  本轮未重编模拟器 (C:\gr_build 已不存在)。
- **产物**: 报告 `work/zh16b/subagent_blackfix/REPORT_blackfix.md`; 28 张对照图
  `test_results/GR_ZH49_对照/`; 分支已 ff 合并入 main (commit 6221fdbf)。

### 21. 快速导航 (55s 主菜单) + 战术演习简报目标行定案 — 无需补丁 (2026-09-26, 子代理×2, 分支 fix/briefing-objectives)
- **导航优化达成** (work/zh16b/subagent_navopt/): START 连点 f800-2600 (每 200 帧) + UP×3 (f2850-3050) + cross (f3250) → 主菜单 F3303 ≈55s (旧 ~29000 帧/8min)。破案: 档案屏初始高亮在底行"新建" (历代导航误入建档流程的根因), UP×3 移顶行 TEQSUNSET; f1501-2213 加载/读卡不可跳 = 理论下限 47-55s。nav_opt.txt 入库。
- **战术演习简报 (GR-M01) 目标行首次在 gsrunner 复现绘制** (快速导航解锁): 行文经 IkeBaseButton::DrawText (0x21D830) y=291/312/333/354, 表头 任务目标 经 0x21C62C y=268。rounds17-20 分析的 W=582 行屏 (ay=197-260) 实为 训练1 场景 — 旧导航多按一次 cross 误入, 并非用户所见页面。
- **双盘同帧像素实测: ZH61 目标行墨迹已与 EN 对齐** — 行 draw-y ZH=EN+3 (ZH 重编译场景资源组件 y +3..+5), 被 16px 字形格内墨迹中心偏高精确抵消: 行墨心 ZH 298.2 vs EN 299.1 (Δ−0.9px), 表头墨心 275.8=275.8, 框行线逐像素全等。
- **用户截图 (user_zh15_brief_box2_crop) 判定为旧盘代产物**: 目标行文为英文 "1 - Neutralize Tent Camp Troops" (现役盘该行已中文 "1 - 消灭营地敌军"), 且呈 pre-V18B 低墨签名 (CharHeight=26 quad + 16px 字形 → 墨低 ~10px 压分隔线)。该机理已被 V18B cave (0x417200, CH==26→16) 修复; 本轮双盘对照是其首个简报屏直接实证。
- **定案: 无需补丁** — 强加 −3/−7px 位移反而破坏当前对齐。GR_ZH62.iso = 0 补丁验证盘 (sha256 与 ZH61 全等 82ae9229...), 仅作复跑验证载体, 现役盘仍为 ZH61。
- 遗留: 训练1 场景行 ZH cy=EN+5 → 预测 ~+2px 偏低, gsrunner 无法复现 (该屏 ~500 帧自动跳转); 用户此前确认训练分支无此页面, 挂起待真实截图。
- 产物: work/zh16b/subagent_brief2/ (REPORT_brief2.md, build_zh62.py, nav_p2/nav_brief2/nav_m02.txt, dis_*.txt 反汇编); 对照图 test_results/GR_ZH62_对照/。

### 22. round22/22b 简报目标行"下沉"补偿 — 场景记录 H 31→26, 用户设计理论证实 (2026-09-26, 子代理+主代理, 分支 fix/briefing-objectives)
- **用户设计理论证实** (像素实测): EN 目标行是"下沉式"设计 — 数字基线 (平底) 304.3/325.1/346.0/366.9 各贴行带分隔线
  (305.4/327.3/347.1) 上方 ~1.1px, 仅 p/g 降部穿越; ZH 满高 CJK 块底 306.5/328.5/348.2 全部压线 → 观感整行下沉。
- **机理修正 (round22)**: +3 不在场景资源 (全部场景档案 EN/ZH61 逐字节相同; RSComponent::ReadResource 不序列化位置) —
  真源 = ELF cave 0x21D940 垂直居中公式差: ZH (H−21)/2 vs EN (H−26)/2。唯一序列化自由变量 = 记录 **H 字段**。
- **补丁**: MENU.IMG/NTSC_IKE.RES 展开态 OBJ0..OBJ3 (W=568, 全库唯一) H 31→26 → draw-y 291/312/333/354 → 288/309/330/351 (=EN),
  墨底贴 EN 基线上方, 让开分隔线 ≥2px。保持 20 子流 {plen}{osz} 帧重压缩 (单子流重帧会挂死开机, 已实证), 全盘 diff 26.5KB 两窗口内。
- **round22b (主代理复核)**: W=140 PROCEED 命令行记录属误补 — EN "PROCEED" 全大写无降部, 下沉设计不适用;
  实测 ZH61 "继续" 按钮内居中 (留白 1/1), 补后 0/4 顶边贴框 = 回归 → 回退该记录。终版 = 4 记录补丁,
  sha256 9c6267c6..., 行墨 v4≡v5 + 按钮回中双确认。
- **运维事件**: tools/emu/pcsx2 (构建树+部署) 本轮中途整目录缺失 (非回收站); p4-gsrunner 备份 + deps DLL + bios 复役
  (注意: ISO 参数须反斜杠绝对路径; 无 21C4C0 钩子); 全钩重建 configure 静默崩溃待查。
- 产物: build_zh62.py (v5), verify_v5.py, REPORT_brief2.md round22/22b, brief_obj_EN_ZH61_ZH62v5_3x.png。

### 23. port282 — 仪表化 gsrunner 移植到 v2.8.2 stable, 全量验证通过 (2026-09-26, 子代理)
- **用户指令执行**: 切换到 v2.8.2 稳定版并引入全部钩子, 今后测试/开发都在该版本上进行。内层仓库 (pcsx2_src 自有 git): master 上先打快照提交 `a657fa313` (10 文件 +1309/−8: GRResearch.{cpp,h} 新增 + 8 文件钩子), 再 `git checkout -b gr-2.8.2 v2.8.2` (fd9d310cc), cherry-pick 快照 → `cd5e3304c` **零冲突**, 逐文件人工核对 API 兼容 (VMManager::Initialize/Error 签名、SIO/Pad/*.h、g_gs_renderer、GS/ include 风格均一致)。
- **无丢失功能**: 全部 -gr* CLI、drawlog/grlog、21C4C0 组件钩子、needle 扫描、CDVD LBA watch、iR5900 入口 trampoline、**PATH3 64MB+压力切片修复** 全部在内。
- **cmake 0xC0000409 静默崩溃定案 (round22 遗留)**: 非 master 特有 (2.8.2 同崩), 根因 = **构建目录残留状态** (master 时代 cache 遇上新源码, cmake 4.0.3 fail-fast)。`rm -rf tools/emu/pcsx2/` 后 configure 即成功 (7.1s, exit 0)。`--purge` 目前不实删目录 — 切版本后必须手动删; 另: `bash 脚本 | tail` 会吞真实退出码, 诊断看 `${PIPESTATUS[0]}`。详见 work/emu_build/REPORT_port282.md §2。
- **构建/部署**: build_pcsx2.sh 全配方 ninja 739/739; exe `PCSX2 GS Runner Version v2.8.2-1-gcd5e3304c`; 已替换 Sep-17 p4 应急部署 (旧 exe 留档 `pcsx2-gsrunner-p4.exe.bak`), resources/DLLs/bios 齐备。
- **验证**: smoke 300 帧 exit 0; brief2 全量 (port282, 9200 帧, exit 0, 155s): 简报目标行 RA=21DA28 y=288/309/330/351 **576×4 与参考全等**, 表头 21C62C y=268 与 F13 分布 ±1 行级一致, 标题 x=33 (5361=5361)、y=25 (5=5) 全等, 219EB0 总数差 12 (窗口边缘抖动), 21C4C0 组件行 23,578 (参考早于该钩子故为 0, 属新产出正常)。
- **PATH3 修复 2.8.2 实证**: gifpath_diag.log 显示 PATH3 缓冲前缀达 ~63MB (旧 9MB 缓冲 7 倍溢出即 0xFEFEFEFE 崩溃源), OVERFLOW=0, 跑满 9200 帧。
- 产物: work/emu_build/REPORT_port282.md (完整冲突核对表/cmake 诊断/验证数字), work/zh16b/subagent_brief2/dump_port282/。

### 24. 工作空间精简 (2026-09-26, 主代理)
50G → 9.4G。详见 docs/WORKSPACE_SIMPLIFY_20260926.md。要点: 归档分支 archive/pre-simplify-20260926
(清理前全量快照, 陈旧轮次脚本/旧截图/失效钩子补丁/hanhua_toolkit 的唯一保留地); PC/PS2 原始文件、
方正字体、模拟器 (gr-2.8.2 源码+部署)、构建依赖全部移入 third_party (不入库, md5 清单 =
third_party/readme.md, 14,226 文件/6.06 GB, 重生成: python tools/gen_thirdparty_manifest.py);
中间盘 GR_ZH31~61 与全部采集 dump 删除 (重建路径见报告); 路径变更 tools/emu→third_party/emu 已同步
至全部活动脚本并实测通过 (smoke + 9200 帧简报全流程, 组件钩子 23,578 行与参考一致)。

### 25. 字库链实证 + 工具解耦 (2026-09-26, 主代理)
- **用户质疑证实**: 保留的 gen_font16.py (v16, X0=20) 并非现役字库生成器 — ZH62 现役字库纹理与 v16 产物 texel 差 21.5%。
- **真链定案** (逐级实证): gen_font16 (v16 基座) → build_font_zh34 (X0 20→4 + 图标窗左移16, 乱码破案代) → fix_slot_fld26
  (FT fld[1] 16→26 ×2, **重放与现役 FT 字节全等**) → make_pak_v22 (8 段 GIF 重封装) → V23→V24 封装修订
  (subagent_pattern 时代, ZH38 行移位终形; 修订装配脚本待下一轮定位, 现重放差 384 段 nibble 相位) → ZH49 NLOOP → ZH62。
  纹理残差仅 8 格/139 texel (EN/符号区, ZH36 后小补丁)。
- **解耦落地**: tools/font_pipeline/ = 真链 8 脚本 + data/ (charset/FT/atlas 输入); tools/capture/ (run_brief2*/run_opt+nav);
  tools/iso_build/build_zh62.py; tools/emu_build; PROGRESS/BUILD_MANIFEST/iso_layout → docs/; work/zh16+zh14 解散入链/归档分支。
  work/ 仅余会话产物 (brief2/navopt 报告脚本, font_out, 校验脚本)。
- **损失声明**: work/zh16/MENU_ZH16.img (58M, ISO 装配阶段输入, 未跟踪) 已不在 — 可经 hanliu 链再生或从归档分支
  恢复同代产物; ZH34 代 .bin 中间产物 (未跟踪) 已删, 由 tools/font_pipeline 重放再生 (阶段 1-2 已验证字节精确)。
- 采集输出目录: 转储统一 work/cap/; 字库中间产物 work/font_out/。

### 26. 构筑体系 + 目录收敛 (2026-09-26, 主代理)
- build/ + test_results/ 并入 work/ (work/** 不入库); build/fonts 旧参照图与 docs/review 删除。
- 新构筑器 tools/iso_build/make_build.py: make_build.py GR_ZH<NN> [--patch] [--from] →
  work/builds/<版本>/{ISO, extract/字表+字库记录+MENU.IMG, temp/, build_info.json}; 基底自动探测最新构筑。
- 首个受管构筑 work/builds/GR_ZH62 (sha 9c6267c6...); 旧位置 work/build/iso 已删除。
- 字库链阶段 5 工具 shift_zh38.py 自检路径适配新布局 (实测 89B 预期残差 ✓)。

### 27. 读卡对话框居中+断句修复 — SWKERN 失效破案 (2026-10-02, 主代理, GR_ZH63)
- **用户报障** (ZH62 人工测试): 开机 Press Start 后读卡提示屏中文行整体左偏 (左隙 < 右隙),
  断句在括号中间断开。gsrunner 双盘同 fast-nav 实拍 (f2213-2329 两对话框 + f2353 载入成功)。
- **屏归属**: 非 BOOT_SCREENS 的贴图版读卡屏 (f262-586), 是 RES 字体渲染的
  G58.I797/I791 (RA=21C85C ← RSTextComponent::DrawTheString 行循环 ← vtable+0x11C
  = DrawTheText 0x21CA20 style-3: x = anchor + (W−StringWidth)/2)。
- **量化** (框心 290.5 snap, EN 基线 −2.0): ZH62 五行左偏 −6.5~−18.5, 随 pairs 单调。
- **根因 (反汇编指令级)**: SWKERN cave (0x565670, ZH57 引入/ZH58 迁址) trail 判定极性写反 —
  0x5656C8 `beq t4,zero,+9` 使 trail≥0xA1 (真实 pair 恒如此) 走 ASCII 单步 → t1 恒 0 →
  kern 仍按字节数计 (kern=2) → 含 CJK 行 SW 高估 2×pairs → 居中左移 pairs px。
  **该 cave 自 ZH57 起对真实字符集等效 EN 原公式 (no-op), §五.2 的"已修"从未生效**
  (ZH57 时代仅数学推导, 未做像素验证 — 教训: cave 类修复必须实机闭环)。
- **修复①**: 0x5656C8 beq→bne (1 字节 0x11→0x15)。实测 MC 屏 4 行 x 移动
  +11/+8/+17/+10 = 2×pairs/2 精确吻合; 纯 ASCII t1=0 两版一致 (EN 零回归由构造保证)。
- **修复②**: I797 译文重写 (71B→54B): 「正在读取记忆卡插槽1中的记忆卡(8MB)。␠请勿取出记忆卡(8MB)。」
  (去 (for PlayStation®2) 括注与 ®2␠用 断裂; 半角空格作折行锚点, 断行落在句号后)。
  MENU #25 + GR #902 双份 (text_replace --mode res, 基底先裁陈旧尾料 — 现役 blob =
  有效 8 子流帧 32,362B + 15,208B 陈旧尾料, 引擎按子流走读忽略; 新 blob 后余量零填,
  条目表 off/stored/real 不动)。
- **构筑**: make_build.py GR_ZH63 --patch tools/iso_build/patch_zh63.py (断言式, 全盘
  diff 40,656B 限三窗口); sha256 3838ed87…。对比图
  work/builds/GR_ZH63/temp/cmp_mc_EN_vs_ZH62_vs_ZH63.png。
- **回归**: 简报流程双盘 11,000 帧 exit=0; drawlog 224,624/224,648 行, 目标行
  288/309/330/351/标题 y=25 全部保持; 键差 = 居中串 +1/+2px 预期位移 + 串堆地址漂移。
- **遗留观察**: MC 屏墨心残差 −5~−8 为行尾「。」窄字形+尾随空格的墨迹轴承 (advance
  空间已精确居中); I791 仍保留 "(for PlayStation®2)" 中英混排 (未拆散, 属风格问题,
  留待译文润色轮)。

### 28. 缩放读数条倍数标签修复 — EN 带原版字形恢复 (2026-10-02 晚, 主代理, GR_ZH64)
- **用户报障** (ZH62 人工测试): 训练 1 瞄准镜缩放读数条倍数标签 (×N/×1) 位置偏上 + 字形细碎。
- **调查**: 导航 nav_zoom.txt (主菜单→训练→训练1→R2/L2 缩放, 快捷复现)。标签绘制 = 0x2E82D0
  组件族, 调用点 RA=2E8524 (×N, f12/f13=x/y) / RA=2E85E0 (×1)。绘制坐标双盘完全一致
  (x=SW×0.5−XScale 居中, y=31.0/164.0) — **非定位 bug, 是字形层问题**。
- **根因**: 现役 EN 带 (ASCII, v376-411) = 13px 时代 Zpix 迷你字形 (7px 等宽、~5×9 细笔
  画、墨迹贴记录窗顶), 16px 时代原样 texel 继承 — 比 EN 原版 (11×13 实心字母、比例 adv、
  基线贴底) 又小又细又高。游戏内纯 ASCII 串罕见 (x4/x1 约唯一), 故 ZH38 以来无人发现。
  (+4 采样错位假说已用判定盘证伪: EN 带右移 4 texel 后碎法改变但依旧碎。)
- **修复 (patch_zh64.py, 数据侧零 ELF)**: EN 带重铺 — 从原始容器 (docs/han_v2/artifacts/
  COMMON_PAK.bin 的 new_font_revised, PSMT8 512×512) 取 large 面 92 个 ASCII 字形
  (0x21-0x7E 排除 0x7B/0x7D=自绘▲▼), 墨迹 bbox 裁切 (ink=texel<24, 值 54+ 为背景噪声),
  底对齐基线=行15 放入 16 行新带 @v452-467 (空白区, 避开 slot1426 横杠 y425/426);
  FT 记录三 face 同步改写 (adv 恢复原版比例宽度 4~19px, u/v 指新带); 空格 adv=3072。
  FT payload 1356B≤4413; 全盘 diff 3,813B 限 FT 槽+字库条目两窗口。
- **验证**: ×4 墨迹行 [32,49] (EN [33,49], 差 1px=二值化 AA 边缘); ×1 [146,169] 与 EN
  **完全一致**; x4/x1 的 f12 = 589.75/591.25 与 EN 精确相等 (比例 adv 恢复生效);
  TEQSUNSET/对话框 (8MB) = 原版衬线粗体; 回归: 简报目标行 288/309/330/351/标题 y=25/
  表头 y=268 全部保持, zoom/mc/brief2 三流程 exit=0。
- **遗留**: 比例 adv 恢复使 ASCII 串变宽 → 含 ASCII 行的居中/折行按 EN 比例重排 (实测
  对话框/简报正常); 新带未纳入 font_pipeline 重放链 (89B 基线自此不适用于 EN 带,
  下次链整备时把重铺逻辑并入 build_font.py)。

### 29. EN 带方案改向 — 方正像素16 ASCII (2026-10-03, 用户否决 ZH64, GR_ZH65)
- **用户反馈** (ZH64 实测): 原版字形提取方案显示效果差, 否决回退原版字库;
  **ASCII 直接用 16px 像素字体 (与 CJK 同款), 只需位置正确**。
- **实施 (patch_zh65.py, 基底 GR_ZH63, 零 ELF)**: 92 个 ASCII 用 gen_font16 同款管线渲染
  (ImageFont.truetype(方正像素16,16), em 窗 [8:24), 阈值 128), 取半角列窗 [0:8) 原样放入
  16 行新带 @v452-467 — 行位 = 字体 em 自身设计 (基线=行13, 与 ZH64 实测 ×1 标签 EN 全等
  行位一致; 降部最深行15 零裁切), 列位保留轴承 ('~' 超 1px 截断)。FT 三 face ASCII 记录:
  adv=0x0800 (8px 半角步宽, 字体自然), u=(i*8, i*8+8), v=(452,468); 空格 adv=8。
- **验证**: ×4/×1 清晰像素字形 (x 斜笔 + 4 横杠), 顶部差 EN 1px; TEQSUNSET/(8MB) 与
  CJK 同款清爽像素字; 简报锚点 288/309/330/351/标题 y=25/表头 y=268 全保持;
  zoom/mc/brief2 三流程 exit=0。
- **ZH64 归档不推荐** (原版字形方案); 字库链 89B 基线对 EN 带不适用 (重铺待并入 build_font.py)。

### 30. ASCII 顶部留空 2 行 — 用户 leading 理论证实 (2026-10-03, GR_ZH66)
- **用户反馈** (ZH65 实测): 像素字方案观感认可, 但"还是高了一点点, 像之前那样贴到显示
  位置最上方"。**用户机理分析证实**: EN 原版 26px 行盒内顶部留 7 行空 (排版 leading +
  双线性防渗); 我们 ZH50 禁双线性后把 16px 格填满 → 同一绘制坐标下墨迹骑高 ~2px
  (实测: EN 'x' 墨在 26px 格第 7-17 行, 我们 em 第 3-13 行; 两盘墨顶都落屏 y+1,
  EN 基线更低 = 行盒内部留白多)。
- **修复 (patch_zh66.py, 基底 ZH63)**: 采样窗顶 = 带顶 − 2 (记录 v: (452,468)→(450,466)),
  带内容与 em 行位不动 — 窗内顶部 2 行空白随四边形渲染 = 补回 EN 式 leading,
  全 ASCII 下移 2px; 降部 (最深行 15) 完整保留, 无压缩无裁切。偏移量 = REC_V0 常量可微调。
- **验证**: ×4 墨行 [33,42] — **顶部与 EN (33) 精确对齐**, 底部差 1px (像素 '4' 天生
  10px vs EN 11px, 纯字形高差); 对话框 (8MB) 同步 +1~2; 简报锚点 288/309/330/351/
  标题 y=25/表头 y=268 全保持; zoom/mc/brief2 三流程 exit=0。
- **谱系**: ZH64 (原版字形, 否决) → ZH65 (像素字, 位置高 2px) → **ZH66 (像素字+留空, 定版)**。

### 31. 帮助条垂直居中 — §五.7 组件身份收口 + style-0x52 手术 (2026-10-03 晚, GR_ZH67)
- **用户报障** (ZH62 沿袭): 主菜单等界面底部滚动说明条文字贴显示区域顶部而非居中,
  疑为字体尺寸连带对齐问题。
- **组件身份锁定 (§五.7 遗留收口)**: RSTextComponent, style=0x52 (无 bit0 水平居中位),
  W=250 H=20 ay=419, 每帧 x−2 横滚 (menu66 实测 f3303 起逐帧 301→299→297…)。
  其余全部组件 (对话框/标题/表头) style=0x53 — 0x52 为帮助条族专属判据。
- **量化**: 条带边框 @snap404; EN 墨 [389,396] (隙 8/8 居中, 26px 行盒内墨自然落中部);
  ZH66 墨 [383,398] (隙 2/6 贴顶) — 16px 四边形顶锚 + H=20 条带 → 骑高 2px。
- **修复 (patch_zh67.py, ELF 手术 12 词)**: hook 0x21CA50 (sw v1,0xEC → j 0x565730,
  延迟槽 lbu v1,0x108 先执行保真后续 bne); cave 0x565730 (ZH58 验证安全区, SWKERN 止于
  0x56571C): y=[0x3C]+[0x4C] 等价重算, style&0xFF==0x52 → +2, 写回 0xEC, j 0x21CA58。
  仅 t0/t1/t2 死寄存器。全盘 diff = hook 1 词 + cave 10 非零词, 词集精确断言。
- **验证**: 帮助条墨 [385,398] (隙 4/6 近似居中); 对话框逐帧不变 (style-0x53 零影响);
  简报锚点 288/309/330/351/标题 y=25/表头 y=268 全保持; menu/mc/brief2 三流程 exit=0。
- **教训 (第三次)**: 全盘 diff 断言必须按"预期差异词/字节集合"比对, 写"恰 N 字节"数值
  断言会踩 nop-与-零区同值 (ZH67) 和 4 字节窗口只认首字节 (ZH63) 两种坑。

### 32. 帮助条 +4 精校 — 测量方法论纠偏 (2026-10-03 深夜, GR_ZH68)
- **用户复测** (ZH67): 有改善但仍偏上一点点, 疑 j/g 式字体上抬。查证: ① CJK 格内墨迹全跨
  [0,15] 无头空 (该假设不成立); ② 条带上边框 @378-379 (此前漏检) → 条带 [379,404]。
- **测量方法论纠偏 (本轮关键)**: 之前测的 [383/385,398] "帮助条墨迹" 实为**右侧按钮行**
  (接受/返回, style-0x53 不受手术影响 — 故 ZH67/ZH68 同帧逐位相同之谜破解); 帮助条文字
  (暗灰) 须用**双盘差分** (ZH67 vs ZH68 仅差手术常量) 从条带背景纹理中抠出。
- **终测定靶**: EN 帮助文字 [389,396] 墨心 392.5; ZH67(+2)=[385,396] 心 390.5;
  +5=[388,399] 心 393.5 (float y → 光栅严格线性 +1:1, 之前"被吸收"是按钮行假象)。
- **修复 (patch_zh68.py, 1 词)**: 手术常量 +2→+4 (0x565750: 0x25080002→0x25080004)。
- **验证**: ZH68(+4) 帮助条文字 [387,398] **墨心 392.5 = EN 精确一致**; 简报锚点
  288/309/330/351/标题/表头全保持; menu/mc/brief2 三流程 exit=0。
- **谱系**: ZH67(+2, 按钮行误测) → **ZH68(+4, 双盘差分定靶, 定版)**。

### 33. 构筑清理 + 五轮合并 + 公开快照推送 (2026-10-03/04, 主代理)
- **合并补丁**: `tools/iso_build/patch_zh68_all.py` = ZH62 → ZH68 终态一步到位
  (① SWKERN 1B + ② I797 双 RES + ③ EN 带像素16 重铺 (窗顶留空2行) + ④ 帮助条手术 y+4;
  ZH64/ZH65 被否决方案不含)。**验证: 与增量链 (63→66→67→68) 构筑的 GR_ZH68.iso
  逐字节相等 (sha256 240b149f… 全同)**。
- **构筑清理**: work/builds 18.6G → 3.3G — 删中间构筑 GR_ZH63/64/65/66/67
  (全部可经 git 补丁链重建) + 全部 dump/mc 转储; 保留 GR_ZH62 (基底/用户测试参照)、
  GR_ZH68 (现役)、GR_EN_ORIG (EN 基线); 各轮对比图证据归拢 work/builds/GR_ZH68/temp/cmp/
  (9 张: MC 对话框/缩放标签 ×3 方案/TEQSUNSET ×2/帮助条 ×2)。
- **后续重建路径**: make_build.py GR_ZH63 --patch patch_zh63.py (需 assets_zh63/) →
  GR_ZH66/67/68 逐级, 或 ZH62 + patch_zh68_all.py 一步直达。
- 公开仓库 AFishD/GR2001-ZH 以新孤儿快照更新 (纪律: 严禁推本地历史)。

### 34. EN 带窗偏移切底破案 — ZH69 修正 (2026-10-04, 用户报障)
- **用户报障** (ZH68): 绝大部分英文字符/符号偏下 + 读卡对话框字符只有上半截。
- **根因 (ZH66 引入)**: "窗顶留空 2 行" 把采样窗从 (452,468) 上移到 (450,466) — 窗高恒 16,
  窗底同步上移 → **em14/15 (图集 v466/467, 降部行) 被切** = 下半截缺失; 可见墨相对四边形
  下坠 2px = "偏下"。数学上"带下移+窗不动"与"窗上移"完全等价 (ZH69 中间版实测渲染逐位
  相同) — **16px 窗 + 16px 满格 em, 任何窗偏移必切 2 行, "窗内 leading" 方案不成立**。
- **修复 (patch_zh68_all.py 更新)**: 撤销窗偏移 (窗=带 452,468, 字形完整);
  垂直对齐改由站点补偿: 帮助条 cave 保持 +4 (CJK 记录窗从未动过, §32 校准不受影响 —
  本轮 +6 试错实测多 2px 后回滚); 缩放标签试验 addiu@mtc1 后无效 (v0 已进 f12 链) 撤销,
  ×4/×1 实测已对齐 (×1 = EN 精确, ×4 顶差 1px = 字形高差, ZH66 验收过)。
- **验证**: 对话框 14 行墨完整 (em1..14; em15 空为字体设计); ×4 [32,40]/×1 [150,169]
  (= ZH66 验收状态); 帮助条 [387,399] 心 393 ≈ EN 392.5; 简报锚点全保持;
  mc/menu/zoom/brief2 四流程 exit=0。
- **教训**: ① 字体"留空"只能在字形栅格内做 (em 设计), 不能动采样窗 (窗=16px 恒等映射);
  ② 双盘差分定靶后还要确认测量对象没换 (§32 按钮行教训的变体: 本轮帮助条 +6 试错
  源于把"窗回退对 ASCII 的影响"误推到全 CJK 帮助条)。
- **谱系**: ZH68 (窗偏移, 切底) → **ZH69 (窗回正, 定版)**; GR_ZH68.iso 删除。

### 35. 小队屏兵种名乱码 — 比较键翻译错误破案 (2026-10-03, 用户报障, GR_ZH70)
- **用户报障**: 战术演习→练习1→小队设置右下角「支组进项对」— 语义不通 (疑翻译错误),
  末字横向压缩。
- **破译**: 末字 = TAB(0x09) 越界取 FT 记录 223 的窄字形 (非真'对'字); 串本体 =
  ' 支组进向\t' (RAM 池串, 不在任何静态存储)。EN 原版同位置 = ' Rifleman'
  (兵种名, RAM 中 ' Rifleman\0an-01. ' 紧邻 RIFLEMAN-01.ATR 文件名派生缓冲)。
- **根因 (确凿)**: GetLocalizedClassName (0x2BFE40) 把 ATR ClassName 大写后与
  RES 字符串比较 (id 0x390234-3B = G58.I568-572 大写 DEMO/DEMOLITIONS/RIFLEMAN/
  SNIPER/SUPPORT — **引擎内部比较键**), 命中才返回显示名。zh7 时代把这五条
  **不可见比较键**也翻译成了中文 → 四路比较恒失配 → 显示串落到残留 id 的池槽
  (垃圾 ' 支组进向\t')。**这是翻译错误, 用户判断正确**。
- **修复 (patch_zh70.py, MENU+GR 双份 RES)**: G58.I568-572 还原 EN 大写值;
  显示名条目 I563-567 (爆破手/突击队员/狙击手/支援队员) 保持中文。
- **效果与残留 (终盘字节级验证)**: 兵种字段 (DrawString v3 @RA=21C62C; EN 原版
  (313,380) 画 ' Rifleman', STR=池址): ZH69 画 ' 20 A4B1 C4D0 E1 09' (支族残串,
  池址 0x5DEA45) → ZH70 画 ' 20 A2B6 B6E1 09' (突击族, 池址 0x5D6F9F) — 首二字=突击
  (pair_of 反查: A4B1=支, A2B6=突), 末块仍为残字节 E1/09 压缩字形。字段内容随修复
  改变的通道有两说 (比较命中改 id vs 键变短挪池布局), 精确机制待 GetString 钩子分晓;
  残留 = 显示名 id 0x3902xx 在 RSStrMgr 表 3 (6 条脚本串, EN 原版同构) 中越界,
  EN 原版同越界, 其 ' Rifleman' 显示系 ATR 文件名派生串恰好占位。
- **TXT 尾空格实验判死 (字节级)**: ZH70b (键还原 + TXT 值尾 +0x20) 的字段与 ZH69
  **逐字节相同** (20 A4B1 C4D0 E1 09, 同池址 0x5DEA45) — TXT 内容挪动池布局把字段
  挪回原残串位置 → 实验剔除, 终盘 = ZH69 + 仅比较键还原 (make_build 规范重建)。
- **回归**: 简报零回归 (reg69 vs reg70 同 nav 11000 帧: COMP 与 DrawString(v3) 元组
  多重集零差异, 七锚点 (46,288)/(46,309)/(46,330)/(46,351)/(128,378)/(33,25)/(45,268)
  帧数逐一相等); squad70/reg70 均 exit=0。
  sha256 1fa547fa733507022f3d369b1e2543bed1c6e50874794041fc62eb2b5a354dac

### 36. GetString 运行时探针 — §35 残留机制全破案 (2026-10-03, GR_ZH71 实验盘, ZH70 仍现役)
- **本轮任务**: §35 留下的两说并立 (比较命中改 id vs 池布局挪移) + 显示名“越界”模型 —
  用 gsrunner GetString 钩子定点。结论: **§35 的两个残留模型都不对, 真根因在别处**。
- **strlog 探针 (内层仓 f28370b4b)**: iR5900 grIsDrawHookPC +4 站点 (0x54B970 GetString 入口 /
  0x54B9B0 返回点(s0=id s1=result) / 0x53F104 表取越界臂 / 0x53F108 join), GRResearch 拦截
  → strlog.txt (窗内 3000 行/帧 + 30M 总量)。构建踩两坑: MSVC 不吃串内裸换行 (C2001,
  改 \n); mklink 建 junction 偶发 rc=1 需手工建 (MVC_ROOT=C:\Users\84363\pbt\msvc, 由
  git show 9d9b7e69 的删除行找回 — 该值已被公开版剥离, 已记忆)。
- **双盘 strlog 事实 (EN vs ZH70, 同 nav_squad 11000 帧)**: 调用结构完全同构 (574/575 次);
  ZH70 F9303: 键 0x39023A (len 9=' RIFLEMAN') 命中 → 分派点 RA=2BFFF0 取 I565 显示名 —
  **§35 的键还原真实生效, 臂选择正确**; 表 3 双盘同 COUNT=0x322=802 条 — **§35 的
  “表 3 只有 6 条/越界”模型错误** (那 6 条是另一码事); 零越界臂。表项结构 =
  {len=1+字节长, enc(EN 2/ZH 1), ptr→池记录}, 池记录 = {字数, 码字节, 00 00 00, attr}。
- **单字节汉字层破案 (本轮最大勘误)**: charset 的 76 'codes' 是**单字节汉字** (击=B6 队=C1
  员=E9 爆=EB 手=F0 组=C4 进=D0 向=E1 …), 其余 1136 字才是双字节对 (lead 0xA1-0xAE)。
  由此 **§35 所谓“显示名残片/字库缺字”全部误判**: G58.I562-567 用单字节解码完好 =
  装备：/爆破/爆破手/突击队员/狙击手/支援队员 — zh7 数据从未坏。教训: 查字表必须
  codes+pair_of 两层都查。
- **字段真实机制**: EN 字段 (313,380) STR=堆 0x1315C10 ' Rifleman\0an-01. ' — **ATR 派生
  原串, 不走 RES**; ZH70 字段 STR=0x5D6F9F **布局敏感错误指针** (ZH70b TXT+0x20 复现
  = 池布局挪移铁证, “比较命中改 id”一说判死)。0x5D6xxx = 资源元数据池, 字段内容 =
  指针落点处的任意记录 (ZH70=' 突击向\t' 任务元数据残片)。
- **错误指针来源 (静态)**: zh7 绘层改道: 0x21C624 (DrawTheString 的 jal DrawString) →
  j 0x417590 (sceDclose 区套件) → 依活寄存器分派进 DoWordWrap+0x160 拼接段 (0x21CD70
  本身又 j 0x417500 字节分类器) → 0x565900 cave 伪 RA=21C62C 尾跳 DrawString。改道为
  全 CJK 文本承重, 不可整体回退; 字段组件经此路径时 STR 甩进资源池。
- **GR_ZH71 实验盘 (构建+实测, 未入主线)**: 假设“字段路径单字节盲” → 字库 +5 对偶
  (爆击手队员@ADF5-ADF9, 行19 空格, cave 公式免 FT; 链重放差 = 89B 基线+245B 五字墨迹,
  ISO 侧只落墨迹带, EN 带/FT/NLOOP 原样) + I562-567 纯对偶重编码 (军械：/爆破/爆破手/
  突击队员/狙击手/支援队员)。**实测: 指针这次落在士兵组装记录 (' '+兵种+' '+姓名,
  0x5DEA69) — 字段画 ' 突[坏]队员' (3/4 字形, 无幻影 TAB)**: 组装器把记录**第 4 字节
  +0x20** (mod 256: C1→E1, E9→09, F6→16 — ZH70/ZH71 两代数据全吻合; 第 5 字节仅单字节
  情形连带)。EN 同路径 9 字节 ' Rifleman' 干净 → 坏字节为 ZH 路径特有。任何 ≥5 字节
  记录的第 4 字节必中 (第 2 字形尾部) — 编码绕不开; 且列表行本就正常, 重编码无实证收益。
- **判定**: ZH71 字段 ' 突[坏]队员' 未达干净显示, **不入主线, ZH70 仍现役**; ZH71 目录
  留作实验+证据 (dump_squad_71)。字链输入已回退 1136 并重跑 (vs 现役差 89B 基线恢复),
  1141 产物快照存 assets_zh71/font_entry_zh71.bin, patch_zh71.py 改指资产。
- **下一轮方向**: (a) 字段 STR 从组件 +0xA0 (正确 RSUIString ptr 0x5ACB6F) 到 DrawString
  之间在哪一步被换成 0x5Dxxxx — 需 strlog 式写观察或对 0x417500-0x4175BC/0x565900 细逆向;
  (b) 组装器第 4 字节 +0x20 的确切指令 — 二者修其一字段即净。
- **教训**: (1) 转储运行必须验证到屏 (破运行 dump_probe_test2 记忆卡路径不存在 → 引导
  分叉, strlog 空 = 假象“GetString 不跑”, 全套错误结论差点成立 — 后被 dump_squad70 复核
  戳破); (2) run_brief2 的 ISO 参数必须**反斜杠绝对路径**; (3) 单字节汉字层是 zh16 编码
  的一部分, 任何“编码不存在/乱码”判断先过 codes 层。

### 37. §36 收口: 真根因定案 + GR_ZH72 大小写折叠守卫 (2026-10-03, 字段终净)

- **组装器 +0x20 指令级定位**: 追 0x30EE8C `jal LowerCase(Substring(1))` (兵种名"首字符
  大写其余小写"显示整形) → RSUIString::LowerCase 0x53FF80 → 折叠循环 **0x407060**:
  逐字节 `c` 经**符号扩展**查 0x585961+(s8)c 处 ctype 标志表, bit0=1 则 `c += 0x20`。
  ASCII(<0x80) 落真表 0x585961-0x5859E0 (A-Z=01/a-z=02/…, 正确); **zh16 高字节 (≥0x80)
  索引变负, 扎进表"下方"的 rodata 字符串区 0x5858E1-0x585960** ("01_CAVES.mis"/
  "\GR"/"p:\ike\releases"/"please"/"logo"/assertion 格串), 撞上奇字节即被 +0x20:
  C1(队)→E1(=向!), E9(员)→09(=TAB), F6→16 — ZH70/ZH71 观测全表逐字节吻合。
  **E0+0x20≡00 = 折叠还会把串截断** (回归轮发现池内一条串长回 13B, 见下)。
- **§36 两大误判终结**: (a) "zh7 绘层字段指针错" — 误。0x5D6F9F 是字段组装记录槽,
  ZH70/ZH72 同值; ZH71 的 0x5DEA69 不同只因 RES 改动挪了池布局。ZH70 字段显示
  ' 突击向\t' = 纯 +0x20 巧合 (E1 恰是向的码位, 09 恰是 TAB), 从来不是"任务元数据残片"。
  (b) "组装器 ZH 路径特有坏字节" — 半误。组装器与折叠循环与 EN 逐字节同 (**原生潜伏
  缺陷**), EN 全 ASCII 永不触发负索引半区; zh7 套件全程未触碰这些字节。
- **全位点清单** (ELF 扫 0x5961 立即数 ×14 处): 折叠写回 2 处 (Lower 0x407060 bit0/+0x20
  ×3 调用者; Upper 0x408910 bit1/-0x20 ×8 调用者, 两者除掩码/方向外同型); 大小写不敏感
  比较 0x406950 (×13 调用者) 只读无回写且双侧同折语义不变 — 不修; 其余 12 处为
  isdigit/isspace 类纯位测试, 高字节误判无破坏性 — 不修。
- **修复 (GR_ZH72, 纯 ELF 补丁 12 词)**: 每循环 6 词同足迹守卫 — `sltiu at,c,0x80` +
  `beq at,0,跳过` (高字节直接跳过折叠, zh16 无大小写); 查表索引改零扩展 (ASCII 地址
  逐位不变), 临时寄存器改用 t0 (两函数均无栈叶函数, 原码未用 t0; a1 不再被覆写)。
  EN/ASCII 语义逐位不变; 无新 cave; 0x5182EC 等禁区未触碰。补丁=对这两段原始引擎码的
  首次改动 (vs EN ELF 逐字节同已断言)。**反汇编往返验证逮住一处真编码错: lbu 应为
  op 0x24, 误写 0x25=lhu — 表基址 0x585961 为奇数, 偶偏移 lhu 非对齐会直接地址错误。**
- **验证 (gsrunner)**: (1) 字段: drawlog ZH72 `STR=005D6F9F | 20 A2B6 B6 C1 E9` =
  干净『 突击队员』singles 编码; 老坏样 `B6 E1 09` 全库 0 命中; 指针与 ZH70 同值。
  (2) 全屏: nav_squad F10000 同帧像素差分 vs ZH70 — **唯一差异带 = 字段文字本身**
  (x291-350, y350-364, 488px), 其余全屏逐像素一致 (零回归)。前后对照裁剪图存
  GR_ZH72/temp/field_before_after.png。(3) 简报回归 nav_p2 11000 帧 ×214 快照:
  **212/214 像素一致 + 2 帧 (F1900/1950) 微差** — 该区间零 DrawString 调用 = 开场 FMV
  解码计时抖动 (代码时序微变的固有现象, 非状态偏差; 后续 212 帧全同证状态同步)。
  drawlog 多重集 (3300-11000, 1,493,633 行) 归一化后**零文本内容变化**, 仅池指针整体
  +0xD: 一条曾被 E0→00 截断 13 字节的池串恢复全长 (折叠截断的隐藏受害者被顺带治愈;
  该串在回归窗内不可见, 像素不受影响)。(4) 字库/RES **零改动** — 89B 重放基线仍有效,
  ZH70 的 singles 编码本来就是对的。
- **判定**: 字段显示根因链闭环 (组装器 LowerCase 整形 → 折叠负索引 → 高字节+0x20),
  GR_ZH72 为现役盘; ZH71 实验的纯对偶重编码不再需要。
- **构筑清理 (2026-10-03 用户定策: 只留最新版)**: GR_ZH62/69/70/71 删除 (释放 12.8G),
  work/builds 只留 GR_ZH72 + GR_EN_ORIG (EN 基线硬链接)。工具留继至 ZH72/temp:
  盘内 ELF 提取 (SLUS_206.13.zh72) + 反汇编器 dis4t.py; 本轮证据 dump_squad_72p/
  dump_reg72/field_before_after.png 同在。后续基底 = GR_ZH72; archive 分支实际只到
  GR_ZH62 (BUILD_VERSIONS 表 ZH63+ 锚点列已纠错)。
- **教训**: (1) "布局敏感指针"类结论必须先排除"内容巧合" — ZH70 的 E1 恰=向、09 恰=TAB
  把坏字节伪装成了"另一条真实字符串"; (2) 引擎 ctype 表用符号扩展索引时, ≥0x80 落点
  = 表下方的任意 rodata, 移植非 ASCII 编码前必须核对负索引半区; (3) 手写指令必须过
  反汇编往返 (lbu/lhu 编码错肉眼难辨, 往返一跑即现形); (4) 差分白名单窗口长度要按
  实际写入范围算 (首版 win 长度 4B 漏连续 5 词, 被全盘差分当场逮住)。

### 38. 人名缩写 DBCS 化 — 命令面板/小队名单"只剩一个点" (2026-10-04, 用户报障, GR_ZH73)

- **用户报障**: 训练中按 R1 调出小队面板、L1 取消详细地图后进入查看队伍状态界面, 队员框里的
  人名只剩一个孤立的 "."; 战役中进界面时部分人名能显示、部分不显示, 能显示的都是英文;
  而关卡内准心对准角色时中文人名显示正常。
- **复现 (gsrunner 扫键)**: F19002 起 `CommandMapFrameModel::Draw` 在
  PC=219A70 RA=2BA808/2BB070/2BB230/2BB40C 画出 `AA 2E 20 20 20 20` / `A2 2E 20 20 …`
  = 孤 lead 字节 + "." + 补位空格 → 屏上只剩一个点 (证据 work/_squad/zh_cmdbox.png 4x)。
- **根因 (指令级)**: 引擎有**两份同构的"缩写名"实现**, 都假设名字是 ASCII:
  - A) `ActorFile::GetActorNameAbbreviated` 0x307090 (RSString) — 34 个调用点
    (SPPlatoonScreen::SetRosterText / SPSoldierSelect / SPSoldierKit / AfterAction);
  - B) `GetUISoldierAbbreviateName` 0x2ECDA0 (RSUIString) — 仅被关卡内命令面板调用。
  两者算法相同: `tmp = Left(name,1); tmp += "."; if FindChar(name,' ') 命中 →
  tmp += Right(name, len-idx-1)`。汉化后的 ATR `<ActorName>` 是双字节对编码 + 尾随空格补齐
  (如 霍勒多明格斯 = `AA B3 A9 C6 A3 DA A4 CC A2 EC A6 CE 20 20 20 20`), 于是 Left 只取到
  **半个汉字** (孤 lead, 渲染不出), 而 FindChar 命中的是补位空格 → 输出 `AA 2E 20 20 20 20`
  = 一个点。准心全名走 `GetActorName` 另一条路径, 故关卡内中文名正常 (与用户观察一致)。
- **修复 (tools/iso_build/patch_zh73.py, 纯 ELF, 零数据改动)**: 名字含 ≥0xA1 字节即判为中文 →
  **不做 ASCII 缩写, 返回去掉尾随空格的完整人名**; 纯 ASCII 走原逻辑 (逐位不变)。
  - helper 0x565760 (a0=chars, a1=len) → v0=去尾空长度、v1=含高字节标志;
  - 挂点 A 0x3070B4 → j 0x5657C8 (v1=1 时 Left(name,v0) → tmp, 再走原收尾);
  - 挂点 B 0x2ECEC0 → j 0x56583C (同构; RSUIString 无长度字段 → 先 Length 再复取 impl,
    避开 callee 对 t 寄存器的破坏)。
  cave 落点 0x565760-0x5658C4 ⊂ 既有安全区延伸段, **41 份 EE RAM 转储** (任务/小队/简报/开机
  各阶段) 复核该区间全零。
- **验证 (gsrunner, EN / ZH72 / ZH73 同 nav)**:
  - 命令面板: ZH72 画 "." → ZH73 画 `霍勒多明格斯/加纳马克斯威/山姆比尔德/特伦特诺里斯`
    (右对齐位置正确、无溢出); 可疑字节扫描 0 命中; 三段对照图
    work/_squad/cmp_cmdpanel_EN_ZH72_ZH73.png (EN|ZH72|ZH73)。
  - drawlog 多重集对照 (窗口 13000-20200): 差异**仅** 4 个人名的画/测宽条目 (各 206 行),
    其余全等 → 零旁路回归。
  - ASCII 路径: 小队设置屏 (nav_squad) ZH72 vs ZH73 drawlog 多重集 **0 差异** (492 条目),
    "C. Hunt" / "Chris Hunt (健康)" 逐字保持 → 300+ 英文 ATR 零回归。
- **遗留**: 菜单侧 (A) 的中文用例需在"士兵选择/战后统计"屏实测 —— 本轮三次扫键均未打开士兵池
  (小队设置屏光标初始在"开始", cross 直接进关; 移光标后 cross/circle 未触发列表),
  该分支已按真实 ATR 字节仿真 (5/5 输出全名) 且 ASCII 零回归已证。

### 39. 任务内 HUD 指示条文字靠上 — y 基准校准 (2026-10-04, 分支 gr-zh74-hudfeed, GR_ZH74)

> 编号注: §38 = ZH73 人名缩写轮 (fix/squad-roster-names 分支)。本轮与其同为 ZH72 的
> 兄弟增量, ELF 字节零交集 (本轮仅 0x22E218 一词; ZH73 = 0x307xxx/0x2ECxxx/0x5657xx),
> 合并时后到者以先到盘为基底重出即可。

- **用户报障**: 任务中击杀/操作后左上角黑底指示条 ("A/B组：XXXX") 文字显示位置靠上;
  自动导航难达, 用户给出实测路径 = 主菜单→战术演习→练习2→进图后按 R3 出 "B组：前进"。
- **导航破局 (tools/capture/nav_mission.txt)**: nav_p2 前缀到 11000 cross ≠ 出发
  (11000 后仍停在装备/队员确认屏) — 补 13000/13600 双 cross 触发出击; 时间线
  = F13100-13800 出发确认框, F13850-13950 黑场, **F14000 起在任务内**; R3@18500 →
  指示条 F18688-19060 (约 12s), R3@19500 → F19600-19950 复现 ✓。
- **指示条绘制链**: STR=014428C0 (堆上动态串, zh16 = 42 C4 A8CD … = 'B组：前进…'),
  经 219A70 (DrawString int 变体) 自 RA=22E274 直调 — 不经菜单的 0x565900 forge,
  历代样式 y 补偿站点全部不覆盖此路径。
- **定量 (ZH72 vs EN 原版, 同 nav 同帧)**: 黑框两盘同位 (snap y24-40, 17 行); EN
  字墨 y29-36 (上5/下4, 居中); ZH 字墨 y24-35 (**上0-1 顶死上沿/下5**) — 亮度加权
  质心 ZH72 32.03 vs EN 32.54 (质量中心只差 0.5px, 但 CJK 墨 12 行 vs 拉丁 8 行,
  边缘顶框 = "靠上"观感的真正来源)。引擎侧 F12=30.0/F13=24.0 两盘相同 → 偏移全在
  墨迹相对笔位的排布 (套件 CJK 墨自 pen+0 起画, 无 Latin 基线留空)。
- **修复 (patch_zh74.py, 纯 ELF 1 词)**: 0x22E218 `lui v0,0x3F80` (1.0f) →
  `0xBFC0` (-1.5f)。文本 Y = 0x22E224 `sub.s f20, f1, f0` (f1 = 25+行×行高,
  f0 = 该常数) → Y 24→26.5 = +2.5px 下移。f20 全函数仅一写一读, 黑框几何
  (quad 段 [obj+0x64]+20.0 系) 独立不受影响。EN 对齐与几何居中两口径在
  "墨迹边缘对称"意义下重合, 无 K 口径分歧。
- **两则过程教训**: (1) 首版误改 0x22E1C8 (20.0f) — 该常数经 f21→mov.s f12 喂的是
  **X**: 实测 F12 30→33 而 F13 不动 — 反汇编译码 mov.s 寄存器域有坑 (0x4600AB06
  被误标为 f0), 手数位解码才见 fs=21/f20; 常数角色必须以 drawlog F12/F13 实测归因,
  不能只看反汇编注释。(2) -2.0 常数实测 +3.7px 过冲 (下距归零) → 按 gsrunner 质心
  校准收敛到 -1.5; 逐行阈值判读受 AA 半行噪声放大, 质心才是稳健标尺。
- **验证**: ZH74 字墨 y27-38 (上3/下2, 对称居中, 顶框消除); F12=30.0 不动 (X 零
  位移); 简报回归 nav_p2 vs ZH72 **214/214 快照逐像素一致** (补丁仅任务内路径,
  菜单零涉及); 前后对照图 work/builds/GR_ZH74/temp/hudfeed_before_after.png。
- **遗留**: 行间排布的 f1 基数存在 ±1 的运行间波动 (动画相位), 上/下距随之 ±1 —
  用户已往接受 1px 级残差; 若实机观感仍偏, 杠杆即本常数 (每 0.5f ≈ 0.5px)。
### 40. 两轮合并: ZH73 ∪ ZH74 → GR_ZH75 (2026-10-04, 分支 merge/zh73-zh74)

- **合并依据**: 两轮同为 ZH72 的兄弟增量、**ELF 字节零交集** —— ZH73 改
  0x3070B4 / 0x2ECEC0 + cave 0x565760-0x5658C4, ZH74 改 0x22E218; 故按既定约定
  "后到者以先到盘为基底重出": `make_build.py GR_ZH75 --from work/builds/GR_ZH74
  --patch tools/iso_build/patch_zh73.py` (反向顺序等价, 两补丁各自带原值断言)。
- **产物**: work/builds/GR_ZH75/GR_ZH75.iso, sha256 `d6848604…)`, 尺寸 = 原盘。
  **合并盘 ELF 逐点回读**: ZH74 侧 0x22E218=0x3C02BFC0(-1.5f) 且首版误改点
  0x22E1C8 保持原词 0x3C0241A0; ZH73 侧 0x3070B4→j 0x5657C8 / 0x2ECEC0→j 0x56583C,
  helper/caveA/caveB 三段的 `jr ra`、`j`/`jal` 目标与 ascii 回跳全部逐词核对通过。
- **实测 (gsrunner, 同 nav 同帧)**:
  - HUD 指示条 (nav_mission, RA=22E274): EN y=24.0 / ZH72 y=24.0 / **ZH75 y=26.5**
    (= ZH74 值), 文案「B组：已到达目的地」帧窗 F18688-19954 与两轮各自盘一致 →
    ZH74 修复在合并盘生效且未被 ZH73 覆盖;
  - 人名缩写 (nav_sqsweep): **ZH75 命令面板 4 名 = 霍勒多明格斯/加纳马克斯威/
    山姆比尔德/特伦特诺里斯** (= ZH73 值), 小队设置屏 ASCII 名 "C. Hunt" 等逐字保持 →
    ZH73 修复同样在合并盘生效。
- **git 合并**: 分支 `merge/zh73-zh74` = gr-zh74-hudfeed(8105d3e3) ∪
  fix/squad-roster-names(c98968b0); 三份文档手工归并 (以对方全 CRLF 版为基底,
  插入 §38/§十八/GR_ZH73 行后再补本节)。顺手订正 patch_zh74.py 两处陈旧措辞
  (docstring "下移 3px" 与实际 +2.5px 不符; 日志沿用首版 "20.0→23.0" 的旧文案)。
### 41. 命令面板中文人名下移 — ZH73 恢复全名后的纵向归位 (2026-10-04, 用户实测报障, GR_ZH76)

- **用户报障**: ZH73 把人名从"一个点"恢复成中文全名后**位置偏上**。机理: 原版英文名块
  靠下 (为 g/y/p 降部留白, 拉丁大写墨自笔位 +5.4 起), 中文四字整块填满字格、墨自笔位 +0
  起画 → 同坐标下整块上抬, 上沿几乎贴住框线。该路径是**任务内命令面板专用绘制链**
  (`CommandMapFrameModel::Draw` 直调 DrawString v1), 菜单文字组件的 CJK 居中补偿
  (0x21D940 K=21) 覆盖不到 —— 与 ZH74 修的 HUD 指示条同性质。
- **定量 (gsrunner 同 nav 同帧, EN 原盘 vs ZH75, 名字条逐行墨统计)**:
  | 框 | EN 墨带 / 质心 | ZH75 墨带 / 质心 | Δ质心 |
  |---|---|---|---|
  | 高亮框 H. Dominguez / 霍勒多明格斯 | 129.1-143.4 / 135.90 | 126.0-140.4 / 132.52 | **高 3.38px** |
  | 右侧框 G. Maxwell / 加纳马克斯威 | 129.1-141.4 / 135.91 | 125.1-139.5 / 132.35 | **高 3.56px** |
  (ZH72 时框内画的是 "." 低位点号, 故当时看不出; 正是 ZH73 的修复让该缺陷暴露。)
- **修复 (tools/iso_build/patch_zh76.py, 纯 ELF: 1 挂点 + 21 词 cave)**: 在 DrawString v1
  序言挂点 (0x219A74), 当 **调用者 RA 落在命令面板函数体内**且**串含 ≥0xA1** 时,
  把 f13(Y) += K; 其余调用与纯 ASCII 串逐位放行 → 英文名/弹药数字零回归。
- **K 标定 (两枚实测盘, 关键教训)**: K 与最终墨迹位移**不是 1:1** —
  K=2.5f 实测只移动 +1.3px; K=7.5f 移动 +5.6px ⇒ 渲染增益 ≈0.86。
  按"与英文墨心对齐"(Δ≈3.0px) 反推 **K = 4.5f (0x40900000)**。
  (教训: 这类 Y 常数不能按"想要多少写多少", 必须做一次标定盘再定值。)
- **首版卡死与延迟槽教训 (最重要)**: 首版钩在函数**首条** 0x219A70 上, 而 `j` 的延迟槽
  (0x219A74 `sd ra,0xA0(sp)`) 会先于 cave 执行 —— 此时 sp 尚未下移, 于是把 ra 写进
  **调用方栈** → 栈损坏 → 开机后卡在档案屏 (第 2 个采样点起快照字节全同、绘制日志仅
  108k 行, 正确盘同期 314,509 行)。改钩**第 2 条** 0x219A74 后, 延迟槽 0x219A78
  (`sq fp,0x90(sp)`) 在 sp 已下移后执行且幂等, cave 再补回存 ra 并跳 0x219A7C。
  **规律: 用 `j` 挂钩时, 必须逐条核对延迟槽指令在"hook 之前"执行是否安全 (幂等/无副作用),
  否则要避开该挂点或改挂下一条。**
- **cave 落点**: 0x565930-0x565984 ⊂ 0x565930-0x565C00 恒零区 (ZH73 用的 0x565760-0x5658C4
  已占), **73 份 EE RAM 转储**该区间全零。
- **验证 (gsrunner 同 nav 同帧; 墨带 = 逐行像素统计, 质心 = 墨量加权)**:
  | 框 | EN 墨带 / 质心 | ZH75 (修前) | ZH76 (修后) |
  |---|---|---|---|
  | 高亮框 (H. Dominguez / 霍勒多明格斯) | 129.1-142.4 / 136.19 | 126.0-140.4 / 132.79 | **129.1-142.4 / 135.86 (= EN 墨带逐行相同)** |
  | 右侧框 (G. Maxwell / 加纳马克斯威) | 128.2-140.5 / 134.94 | 125.1-139.5 / 132.35 | **128.2-142.6 / 135.73 (顶沿与 EN 相同; 底沿多 2.1px = CJK 字块天生高 14.4 vs 拉丁 12.3)** |
  框内区 ≈126-144.5: ZH75 上距 −0.9 (捅出框沿) / 下距 5.0 → ZH76 上距 2.2 / 下距 1.9 (对称居中)。
  - 全屏逐行像素差 (ZH75 vs ZH76) = 2,577 px / 56 行 = **恰好 4 条名字行** (每条 14 行), 其余零差;
    弹药行 26/- · 30/- · 1/5 的绘制参数与像素完全未动;
  - 健康: 绘制日志 314,509 行 (= ZH75 同 nav 同帧), 无卡死无旁路回归;
  - 对照图 work/builds/GR_ZH76/temp/cmp/ (整面板 / 高亮框 6x / 右侧框 6x, 均 EN|ZH75|ZH76)。
- **遗留**: 菜单侧同一份缩写实现 (0x307090) 的中文用例仍待"士兵选择/战后统计"屏实测
  (该路径走 IkeBaseButton 的 CJK 居中补偿, 预期本就不需要本补偿)。
### 42. GR_ZH76 第二轮: 零寄存器泄漏重做 (修首版"菜单文字变色"回归, 2026-10-04 用户实测)

- **用户报障 (第一条)**: "修改动到了部分文字显示逻辑, 主菜单下方选项说明等出现变色"。
- **定量定位 (同 nav 同帧像素级)**:
  | 对照 | 结果 |
  |---|---|
  | ZH72 vs ZH75 主菜单 f3400/f3600 | **逐像素零差** → 与 ZH73/ZH74 无关 |
  | ZH72 vs ZH76 同帧 | 出现色差, 色带恒 15 行: y385-399 (帮助条) / y23-37 (标题) / y261-275 (菜单行) |
  | 色差性质 | **仅 G 通道 −3~−9, B/R 不变** → 是"变色"不是位移 (位移会带描边形状差) |
- **二分定位 (探针盘)**: 造两枚探针 (基底=干净 ZH75, 同 nav_opt 4000 帧):
  - 探针 A = 仅序言舞 (`sd ra,0xA0(sp)` + 回跳), **零寄存器触碰**;
  - 探针 B = A + 范围判断 (碰 t0/v0, 不扫串不动 f13)。
  结果: **探针 B 与完整 ZH76 复现同一处变色** (y385-399, G −8.8, 793px; 全部像素差 0.311%)。
  (探针 A 一次运行跑岔了流程 —— 记忆卡/引导时序漂移致同帧不同屏, 该对照作废, 不作结论;
  但序言舞在数值上可证透明: 两个 store 地址不重叠、sp 与寄存器值不变。)
- **根因**: **本引擎违反 MIPS o32 ABI 约定** —— 调用方在 **t0 / v0** 中携带活数据调用
  DrawString v1 (与本项目已知怪癖"实参走延迟槽"同族)。按 ABI 推断"caller-saved 入口即死"
  在此引擎**不成立**; 借用它们作暂存 → 上层渲染读到的活数据被改 → 颜色出错。
- **修法 (零泄漏 cave, 31 词)**:
  - 开头 4 条 `sw` 把 **t0/t1/t2/v0 存入 sp+0x10-0x1F** —— 选这组槽位的依据: hook 之后序言
    会执行 `sq s0,0x10(sp)` / `sq s1,0x20(sp)` 等, **无条件整槽覆写**, 故此刻写入绝对安全,
    且不会破坏任何活数据;
  - 命中路额外把 **f0** 存 `sp+0x20` (同样随后被 `sq s1` 覆写) 再恢复;
  - 收尾逐条 `lw` 恢复 → `sd ra,0xA0(sp)` → 回 0x219A7C。
  - 结果: **除故意修改的 f13 外, 进出 cave 的机器状态逐位相同** (真正的全透明钩子)。
- **编码教训**: 恢复用 4 条 `lw` 首版把 rs/rt 写反 (`lw $sp,16($t0)`: 把垃圾载入 sp),
  被**反汇编往返**当场逮住 —— 新增/改写 lw/sw 类指令必须过 `tools/diag/dis_ee.py` 往返验证。
  另一条: 探针盘也必须过反汇编反查, 否则"探针自身的 bug"会被误读成被测对象的结论
  (探针 B 首版 beq 偏移错 1 词, 直接跳过存 ra → 开机崩, 一度误导定位方向)。
- **验证 (同 nav 同帧)**:
  - **主菜单: ZH76v2 vs 干净 GR_ZH75 = 逐字节全等 (max=0)** @ f2500/3400/3600/3800 → 回归消除;
  - 命令面板人名仍与英文对齐 (高亮框墨带 129.1-142.4 = EN 同带, 质心 135.86 vs EN 136.19);
  - 全屏逐行像素差 ZH75 vs ZH76v2 = 2,577px / 56 行 = 恰好 4 条名字行; 弹药行零变化;
  - 绘制日志 314,509 行 (= ZH75) → 无卡死无旁路;
  - GR_ZH76 sha256 更新为 `a73add9666ac39f6f627cb361c61bb9001f942bb28fbc1973280755378c1e2a8`。
- **纪律沉淀**: ①本引擎"caller-saved = 入口死值"假设**不成立**, 任何新 cave 借用 t0-v1/a0-a3
  前必须先做探针盘验证; ②若必须用暂存, 优先"序言稍后必然覆写的栈槽"而非借寄存器;
  ③挂钩 `j` 必须核延迟槽 (§41 教训), 二轮又核寄存器泄漏 —— **cave 白盒审计清单:
  延迟槽 / 寄存器泄漏 / 栈槽归属 / 反汇编往返 / 同 nav 同帧像素回归**。
### 43. GR_ZH77 — 全部角色档案人名汉化 (255 条; 用户报障"翻译不完整") + 字表缺字实测

- **用户报障 (第二条)**: "翻译并不完整 —— 只有训练模式里的角色名汉化了, 其它模式的人名
  (显示为'缩写+.+全名', 如 J.Bachman) 仍是英文"。
- **机理**: 人名来自 GR.IMG 的 1193 个 `.ATR` 档案的 `<ActorName>` 字段。zh9 时代**只汉化了
  5 个 RIFLEMAN** (Corey Moss / Samuel Beard / Horace Dominguez / Garner Maxwell / Trent Norris),
  训练模式恰好抽到这几个 → 看着"已汉化"; 战役/快速任务/多人抽到其余 ATR → 全英文。
- **实际范围**: 1193 = 5 已汉化 + **250 待译 (245 个唯一实名, 406 个姓名词素)** +
  **937 个"角色描述/脚本键"必须保持英文** (POW 19 处 / Pilot 30 / Refugee 36 / Soldier 36 /
  Eritrean 2 处被任务脚本 `.MIS` 直接字符串匹配) + 1 个无该字段。
- **字表硬约束 (本轮最大发现)**: zh16 字表共 **1212 字** (单字节码 76 + 对偶码 1136);
  在 397 个常用音译字里**缺 50 个** (逊/汤/普/森/兰/戴/米/怀/杰/斐/蒂/芬/莱/菲/蒙/麦/迈/彭/宁/
  阮/吴/乔/丹/亨/洪/琼/瑟/史/翰/历/廉/赖/富/恩/戈/贡/洛/隆/雅/伯/皮/泰/昂/韦…)。
  → 本轮**不扩字库**, 改用"表内同音/近音替代" (丹→旦、亨→汉、洪→红、琼→约、怀→外、蒙→门、
  瑟→色、史→士、翰→汉、逊→迅、历→力、廉→连、杰→吉、蒂→迪、莱/赖→来、兰→蓝、米→密、
  普→扑 pū、阮→软 ruǎn 同音、伯→博 bó 同音、泰→太 tài 同音…), 即"字表内最优近似",
  零字库改动、零渲染风险。译名用字 176 个, 全部 ∈ 字表。
  (提质路线 = 扩字库加 ~50 个音译字, 属 ZH71 领域, 另轮评估。)
- **修复 (纯数据, 零 ELF)**: `tools/iso_build/patch_zh77.py` + 资产
  `tools/iso_build/assets_zh77/names_zh77.json` (408 条词素→中文)。遍历 1193 个 ATR, 把
  `<ActorName>` 纯 ASCII 字段按 token 级音译**原位等长覆写** (不足补 0x20, 与 zh9 的 5 条同法);
  条目表 off/stored/real 与 GR.IMG 头部逐字节不动。
- **验证**:
  - 脚本自检: 差异 3,080 B 全部落在 ATR 字段窗口内; 回读自验; 头部/条目表回读零差;
  - **独立数据验收** (`work/_dis/verify_zh77.py`): 4070 条条目表零差; 译名字节数 ≤ 原字段;
    937 个角色键**逐字节未动**; 既有 5 条中文幂等未改;
  - **完备性 (终盘直扫)**: 中文 255 / 角色键英文 937 / 无字段 1 / **压缩条目 1 (见例外)** = 1193;
  - **唯一例外 (1 条)**: `D_JODIT_HAILE.ATR` (`Jodit Haile`) 是 1192 个未压缩 ATR 之外**唯一**的
    压缩条目 (条目 stored=482 / payload=474 / real=1076)。解压后等长改名 → 用
    `tools/gr_tools/lzo1x_c.py` 重压得 486-490 B **超出 474 B 槽位**; 且该串在 LZO 流中被
    match 编码, 无法原位改写字面量。要修必须改条目表 stored (482→496, 恰好吃掉 14 B 对齐留白,
    且新尾正好落在下一条目起点) 或越槽写入 —— 二者都违反"条目表 off/stored/real 绝对不动"
    铁律, 故本轮保留该 1 条英文并在此登记, 待用户决策后另轮处理。
  - **运行时回归**: 与 ZH76 同 nav (nav_sqsweep, 20200 帧) **全 199 个快照逐像素一致**;
    绘制日志 314,509 行 (= ZH76/ZH75) 无卡死。
  - **测试盲区 (如实登记)**: 能列出非训练组人名的屏 (士兵池 / 战役小队屏) 在本套测试导航下
    未能稳定到达 (战役导航跨盘不可复现: 两盘同 nav 同帧像素差 95%), 故本轮以数据层 + 全量
    回归为主要证据; 实机确认请用户在**战役/快速任务存档**里查看 (其小队正是含未译 ATR 的那批)。
- **纪律沉淀**: ①批量替换前必须**直接从容器 (ISO/IMG) 扫描**统计待改集合 —— 本轮先用文本
  dump 正则统计, 漏掉了含撇号的名字 (Todd D'Agostino / Joe O'Brien), 是补丁脚本的断言
  ("词素缺译: 'Todd'") 把它抓出来的; ②脚本角色键 (被 .MIS 匹配的 POW/Pilot/Refugee/Soldier/
  Eritrean) **一律不译**, 该跳过集必须逐名核对 (937 条) 而非凭直觉; ③**压缩条目是批量替换的
  盲区** —— 统计与验收都必须按"条目是否压缩"分类并单独列出未处理项, 避免"看起来 100%"。
### 44. GR_ZH78 — 特别收录分栏标题汉化 + "GR任务"改"幽灵行动®任务" (用户报障第三/四条)

- **用户报障**: ①主菜单→特别收录→设定图/屏幕截图 里几个分栏标题未翻译 (Soldiers/Enemies 之类);
  ②"GR任务"应译作"幽灵行动®任务" (GR 要译成幽灵行动, 整词 = 幽灵行动®任务)。
- **两处来源 (完全不同, 需分别处理)**:
  | 报障 | 真实来源 | 说明 |
  |---|---|---|
  | ① 分栏标题 | `MENU.IMG EN_SPECIAL_FEATURE.XML` (#283) 的 `<studio\|group name="...">` | **51 个 name= 全是英文** (Soldiers/Enemies/Specialists 1-2/Training/Background/GR Mission 1-15/DS Mission 1-8/DS Soldiers/GR·DS vehicles/Music/Weapon/Movies/GameTrailer/Awards/SpecialistProfile/BackStory/Interview) |
  | ② "GR任务" | `MENU EN_STRINGS.RES` #25 + `GR EN_STRINGS.RES` #902 的 **G58.I724-727** | EN 原文 = `GR Mission` / `DS Mission` / `GR MP` / `DS MP`; zh7 时代译为 6B 的 `GR任务/DS任务/GR联机/DS联机` |
- **关键取证**:
  - XML 属性 `name=` **只用于界面显示** (每个名字在文件里唯一次出现, 不参与 pic 引用/键比较) → 可安全替换;
  - XML 的中文用 **zh16 字表编码** (非 GBK/UTF-8) —— 与 RES/ATR 同码页, 可正确往返解码;
  - 字表 1212 字仍缺「草」「故」「念」等, 故 `ConceptSketches` 译为 **设定图** (与 RES 里
    `G58.I740 Sketches=设定图` 一致), `BackStory` 译为 **背景资料**;
  - 入口文案 RES 侧本已汉化 (`G59.I037 Special Features=特别收录`, `G58.I740 Sketches=设定图`,
    `G58.I746 Screenshots=屏幕截图`) —— 缺的正是 XML 分栏名与 GR 前缀文案。
- **修复 (纯数据, 零 ELF, 全在 MENU.IMG)**:
  - A. XML 51 个分栏名 → 中文, **等长原位覆写** (不足补空格), 按原 8 子流边界重打包
    (重压 40,232B / 槽 49,700B); GR Mission N → **幽灵行动®任务N**, DS Mission N → 沙漠风暴任务N,
    DS Soldiers/vehicles → 沙漠风暴士兵/沙漠车辆 (受 11B 槽位约束);
  - B. G58.I724-727 4 条: 新译 10-12B > 原 6B, **必须重编码** → 走官方
    `tools/hanliu/tools/text_replace.py --mode res` (8 子流框架 + LZO 自检),
    **MENU 与 GR 双库同步** (GR任务→幽灵行动®任务 / DS任务→沙漠风暴任务 /
    GR联机→幽灵行动联机 / DS联机→沙漠风暴联机); 产物 `assets_zh78/res_{menu,gr}_zh78.bin`。
- **踩坑记录 (RES 条目结构)**: 子流内条目 = `[00 00][长度 4B 小端, 值只在首字节][串体]`;
  串变长必须整段平移, 而 8 子流是**按 real 定长切分** (16384×7+13857) 且子流 3 无尾零可吸收
  → 手搓重排不可行, 正解是交给官方管线 (它会 `serialize_exact` 到固定 real 并复刻子流布局)。
  另: 喂管线前**必须裁尾** (槽内有余量尾料, 否则 `decode_blob` 报 "input depleted")。
- **验证**:
  - 补丁自检: XML 51/51 命中; MENU/GR 双库 8 子流重打包并回读 4+4 条新串; 条目表/头部未动;
  - **独立验收** (`work/_dis/verify_zh78.py`, 直接从成品盘解码): XML 分栏 51 个全为中文
    (设定图/士兵/专家1/…/幽灵行动®任务1); 双库 G58.I724-727 四条逐一命中;
  - 回归: 与 ZH77 同 nav 同帧 (199 快照) 除已知分屏差异外无异常;
  - 对照图 `work/builds/GR_ZH78/temp/cmp/zh78_sf_titles_EN_vs_ZH.png` (51 条 EN→ZH)。
- **测试盲区 (如实登记)**: 本轮构造的菜单导航**未能稳定进入「特别收录→设定图/屏幕截图」屏**
  (数次尝试都停在小队/装备屏), 故 XML 51 条的**上屏显示未经实机/模拟器视觉确认** ——
  但数据层已逐条解码核对 + XML `name=` 无键语义 (改动面可判定), 实机确认请用户协助。
- **纪律沉淀**: ①同一句用户报障可能横跨**不同资源** (XML 属性 vs RES 条目), 必须先定位再动手;
  ②"GR" 这类**品牌前缀**在 XML 与 RES 两处都要改, 否则同一界面中英混杂;
  ③字表缺字会直接决定译名 (ConceptSketches→设定图), 替换前先查字表。
### 45. 构筑管线改造: 每次构筑自动产出全量文本总表 (用户需求)

- **需求**: "修改整个构筑工具管线, 我希望可以每次构筑的时候都同时输出一份全部文本的表格"。
- **实现** (两件新工具 + make_build 挂钩):
  | 工具 | 作用 |
  |---|---|
  | `tools/diag/dump_all_text.py` | 从任意 ISO 遍历**六类文本来源**, 与参考盘 (默认 GR_EN_ORIG) 逐条并列对照 → `all_text.csv` / `summary.txt` / `summary.json` |
  | `tools/diag/text_table_xlsx.py` | 渲染多 sheet Excel: 总览 / 全部文本 / 分来源各一张 (冻结首行 + 自动筛选 + 差异行浅绿高亮) |
  | `tools/iso_build/make_build.py` | 构筑末尾自动调用上述两件 (失败只告警不影响构筑); `--no-textdump` 可关; `build_info.json` 增记 `text_table` 路径 |
- **覆盖来源与实测基数 (GR_ZH78)**:
  | 来源 | 条数 | 含中文 | 中文率 |
  |---|---|---|---|
  | GR:ATR (1193 档案 ActorName/ClassName) | 2385 | 254 | 10.6% |
  | MENU:RES (66 组 UI/任务/培训) | 2232 | 1745 | 78.2% |
  | GR:RES (任务内文案) | 2232 | 1745 | 78.2% |
  | MENU:SF (特别收录 XML 分栏名+条目) | 620 | 80 | 12.9% |
  | MENU:TXT (武器/规则键值) | 1 | 0 | 0% (DP 压缩态, 标注跳过 — 该表值从不显示) |
  | **合计** | **7470** | **3824** | **51.2%** |
- **表列**: `source, key, en(参考盘), zh(本盘), changed(是否与参考盘不同), len_en, len_zh, hex_zh, offset`。
  `changed` 列是逐轮回归的抓手 (改了哪些条一眼可见); `hex_zh` 便于核对码页字节。
- **用法**: 构筑时自动产出 `work/builds/<版本>/temp/textdump/all_text.xlsx`;
  单独重跑 `python tools/diag/dump_all_text.py <iso> [--ref <参考iso>]`。
- **产物位置约定**: 文本总表属**测试产物**, 落各版本 `temp/` (不入库, 与截图/日志同规)。
### 46. 特别收录屏"无光标/无法移动"根因 = XML 内容在 zh7 时代丢失 (重大发现)

- **用户报障**: 主菜单 → 特别收录 → 按 X 进入后**界面无选中光标、方向键只有音效不能移动,
  唯一有效操作是三角返回** (附实机截图: 10 行列表全灰、无高亮行、右侧预览框空白)。
- **排查结论: 与本项目任何一轮改动无关, 是 zh7 时代的 XML 内容丢失。**

#### 证据链 (字节级)

| 检查 | EN 原盘 | ZH72 起 (含 ZH77/ZH78) |
|---|---|---|
| `</SpecialFeatures>` 闭合 | 存在 (尾部 `\t</studio>\r\n</SpecialFeatures>\r\n\r\n`) | **也存在** (经子代理复核: 四个版本各 1 次; 本表初版误记"丢失" = 检测窗口取 `[-64:]` 太窄所致, 特此勘误) |
| studio 节点偏移 | 20, 10442, 14611, 15941, **33976**, 37891, … | 20, 10442, 14611, 15941, **28208**, 32008, … |
| 第 5 个 studio 起 | — | **整体前移 5,768 B** |
| 节点计数 | studio 10 / group 41 / item 94 / picname 252 | **完全相同** (只位置变了) |
| 压缩后 payload | 49,636 B (槽 49,700, **仅余 64 B**) | 40,136 B (**内容少了 5,768 B 才省出空间**) |

- **成因**: zh7 汉化以文本方式重写该 XML 时, 把一段 5,768 B 的内容 (含制表/换行结构) 折成
  纯 `\r\n` 填充以保持槽长 → **内容丢失但字节数不变**, 因此历轮 diff 与"节点计数"检查
  都没发现。
- **为何表现为"无光标"**: `SetStudioType` (0x345C60) 逻辑 =
  `if (type != -1) *(0x5FA628) = SFStudio->GetSdutio(type);` —— 引擎按 studio 序号取数据;
  XML 内容错位 → 取到的解锁标志全 0 → `FillList` 把所有行按"未解锁"渲染 (全灰、无当前项)
  → `UpDownPressed/NavigateBetweenItems` 无可选目标 → 方向键无效; `Back` 独立于列表 → 可返回。
- **GR_ZH78 的角色**: 本轮只把 51 处 `name` 的值等长换成中文 (零字节增减)。
  ZH77 (改前) 与 ZH78 (改后) 的 XML **压缩后仅差 32 B**, 结构逐节点一致 →
  **该屏异常在 ZH77 上必然同样存在**, 用户是首次进入该界面才发现, 不是本轮回归。

#### 修复为何不能直接做 (槽位瓶颈)

EN 原件 compress 后 payload = **49,636 / 槽 49,700 (余 64 B)**, 而自研 `lzo1x_c.py`
压同一内容需 51,510 B (比游戏原版压缩器差 1,874 B) → **直接铺 EN 原件必然超槽**;
zh7 版能装下正是因为**内容少了 5,768 B**。故修复必须"内容净缩减 ≥ ~1,900 B"。

#### 已备选方案 (待实施)

1. **中文回填缩容**: EN 里大量 `<text>` 长文本是英文; ZH77 损坏版里这些节点**已是中文**
   (中文信息密度高、文本更短)。把 ZH77 的已译文本节点**按节点名对齐装回 EN 结构**,
   既恢复丢失节点、又显著缩短内容 → 大概率可装进槽。需做节点级对齐与逐节点校验。
2. **外部压缩器**: 找到与游戏打包同级的 LZO1X 实现 (或调 `chains/level` 组合) 弥补 1,874 B 差。
3. **槽位扩容**: 改条目表 `stored` 吃掉相邻留白 —— **违反"条目表三字段绝对不动"铁律**, 需用户决策。

#### 纪律沉淀

- **"节点计数相同"不等于"结构完好"** —— 必须同时校验**节点偏移序列**与**尾部闭合标签**;
- 槽位余量要**逐条目实测** (本条目仅 64 B 余量, 是全盘最紧的之一), 动手前先量;
- 用户截图是最高价值证据 (一眼看出"全灰无选中"= 解锁标志全 0, 而非"绘制坏"或"输入坏")。

#### §46 勘误与结论修订 (2026-10-04, 子代理独立复核后)

1. **勘误**: 初版称 ZH 系"`</SpecialFeatures>` 闭合丢失"**不成立** —— 四版本各含 1 次,
   初版检测窗口 `[-64:]` 过窄导致误判; 尾部"大量 \r\n"只是中段内容被折叠后的**填充**。
2. **中段塌陷确为既有**: ZH72 与 ZH77 的 XML 明文 sha 相同, 该塌陷**无法**解释
   "ZH77 正常 / ZH78 异常"。
3. **因此故障只能归因于 ZH78 相对 ZH77 的两处 delta**:
   - ① `EN_SPECIAL_FEATURE.XML` 51 个 `name` 属性中文化 (+0x20 补白);
   - ② 双库 RES `G58.I724-727` 四条标签变长 (2.2~2.4 倍)。
4. **强嫌疑 = ①**: 本盘 ELF **@0x4776F0 起硬编码了 studio 名白名单**
   (`ConceptSketches / Background / Movies / Music / Weapon / Awards / BackStory /
   SpecialistProfile / Interview / GameTrailer`), XML 解析器以 strcmp 比对 `name` 判定
   studio 类型 → 中文名全部失配 → 类型未识别 → 解锁标志全 0 → 列表全灰无光标。
   证据: `work/_dis/dump_sf_keys.py` 输出 (ELF 里紧邻 `SpecialFeatures`/`Special_feature.xml`/
   `group`/`pic`/`unlock`/`name`/`item`/`text` 等标签名, 构成解析器键表)。
   **与 ZH70"兵种比较键勿译"完全同族。**
5. **验证盘 GR_ZH79** = ZH78 + XML 回退为 ZH77 原字节 (RES 修改保留);
   sha256 `f6345cf6ff5fe8479a4cbb97325fa32d6fb33fbddff5f519ad255b02dcaab141`。
   另需 (若 ZH79 仍异常) 做"RES 回退、XML 保持中文"的反向盘以判定 ②。
6. **RES 侧已证零破坏** (子代理逐组逐条比对): ZH77→ZH78 双库 RES 变化条目**恰好 4 条**,
   组数/条数/子流 real 尺寸/attr 全部相同, 且"ZH77 容器只改这 4 条后重建 = ZH78 逐字节相同"。

#### §46 汇编级确证: studio name 是引擎比较键 (2026-10-04)

反汇编 `tools/iso_build/../../work/builds/GR_ZH78/temp/SLUS_206.13.zh78`:

```
; SFStudio::ParseStudioWithGroup(SFStudio_T&, const RSXMLTag*) @0x1F7430
001F7478  lui   $v0, 0x0057
001F747C  addiu $a0, $sp, 232
001F7480  jal   0x0053E820   ; RSString::operator==(const char*)   ← 与 C 字符串逐字比较
001F7484  addiu $a1, $v0, 30360      ; a1 = 0x5776F8 → 指向白名单串表
                                          (ELF 文件偏移 0x4776F0 区 = ConceptSketches/Background/…)
```

以及 `SFStudio::GetSdutio(eSFStudioType)` @0x1F6E30:

```
001F6E58  sltiu $at, $s0, 10         ; 枚举值域 = 10 (恰为 10 个 studio)
001F6E64  lui   $v0, 0x0057
001F6E68  addiu $v1, $v0, 30592      ; 0x577780 = eSFStudioType 跳转/名字表基址
```

**结论**: 引擎解析 `EN_SPECIAL_FEATURE.XML` 时, 以 `RSString::operator==(const char*)`
把 `name` 属性值与**硬编码白名单**逐串比对来判定 studio 类型 (10 种)。
GR_ZH78 把 name 译成中文后**全部失配** → studio 类型未识别 → 解锁标志全 0 →
特别收录列表全灰、无当前选中项 → 方向键无目标、只能返回。

**据此定案: `EN_SPECIAL_FEATURE.XML` 的 `name` 属性属"引擎内部比较键", 永久禁译**
(与本盘 ELF 硬编码的 studio 白名单绑定); 若将来确需汉化该屏标题, 必须**同时改 ELF 白名单**
或改走"显示名与比较键分离"的其它机制, 不可只改 XML。

#### §46 修复验证与导航机制发现 (2026-10-04 模拟器实测)

**修复验证 (同导航同帧)**:

| 盘 | 到达该屏 | 列表首行区域均值 BGR | 判定 |
|---|---|---|---|
| GR_ZH77 (回归前) | ✓ | 蓝绿高亮 | 正常 |
| **GR_ZH79 (XML 回退)** | ✓ F4642 | [48.5, **100.2**, **124.1**] | **正常 (选中高亮恢复)** |
| GR_ZH78 (故障) | ✓ F4642 | [91.5, 55.5, 45.8] | 异常 (全灰无高亮) |

- **F4600 (进入该屏首帧) 两盘逐像素完全一致 (max=0)** → 界面与列表文案本身无差异;
- **F4700 起差异集中在 y69-97 行带** = 列表首行 → 正是"有无选中高亮"的差别;
- 绘制站点集合两盘完全相同 (无缺失绘制), 仅次数差异 (故障盘因无法操作停留更久);
- 对照图 `work/builds/GR_ZH79/temp/cmp/sf_ZH77fix_vs_ZH78.png`。

**导航机制重大发现 (此前所有导航失败的根因)**:
`-grinput` 每行语义 (`third_party/emu/pcsx2_src/pcsx2-gsrunner/GRResearch.cpp:546-571`):
`tap`/`press` (默认) → release_frame = fr + **12** (即 12 帧长按);
`release` → release_frame = fr (该行同时含一次 press); `hold` → 永不松开。
**本作菜单按住约 7 帧即开始连发** → 一次 `tap` 会移动 2~3 项, 且同一段长按在不同帧给出
2 或 3 项 (菜单 tick 与模拟器帧相位漂移) → "数 tap 次数"必然随机落点, 这就是此前总是
进到"战役/选项/多人游戏"的原因。
**正解: `tap` 按下 + 紧跟一行 `release` 提前松开 = 2~3 帧短按 → 每次精确 ±1 项。**
主菜单 (9 项, 首尾环绕): 1训练 2战术演习 3战役 4快速任务/重放 5多人游戏 6统计
**7特别收录** 8选项 9制作组; 光标初始在第 1 项 → **上移 3 次 = 1→9→8→7 = 特别收录**
(避开路径上的子菜单, 最可靠)。标定导航 `work/_dis/nav_sf_ok.txt`。

### 47. 特别收录分栏标题汉化: group 名成功 / studio 名逆向成果 (GR_ZH81)

#### 需求
"分栏标题需要汉化, 允许逆向修改游戏原盘逻辑, 但要保证汉化后的 ISO 在标准模拟器上正常运行。"

#### 探针实验矩阵 (同导航同帧; 判据 = 特别收录屏列表首行高亮 BGR)

| 探针 | 改动 | 首行 BGR | 判定 |
|---|---|---|---|
| GR_ZH79 (基准) | 无 | [48.5 100.2 124.1] | 正常 |
| **P4** | **只改 XML 的 41 个 group 名** | **[48.5 100.2 124.1]** | **正常 ✓** |
| P1 | 只改 ELF 的 10 个 studio 名 | [91.5 55.5 45.8] | 异常 ✗ |
| GR_ZH80 | ELF studio + XML studio + group 全改 | [91.5 55.5 45.8] | 异常 ✗ |
| GR_ZH78 | 只改 XML studio + group | [91.5 55.5 45.8] | 异常 ✗ |

#### 结论一: group 名可安全汉化 (已实施)
全 ELF 扫描确认 `Soldiers/Enemies/Specialists/GR Mission/DS Mission/DS Soldiers/...`
**不存在于任何硬编码表** (ELF 内同名字符串均属其它用途, 地址远离 SF 区) → 属**纯显示文本**。
P4 实测光标零影响 → 已落地为 **GR_ZH81** (41 处, 等长原位覆写)。

#### 结论二: studio 名是引擎内部标识, 不能改字符串
`SFStudio::GetSdutio(eSFStudioType)` @0x1F6E30 是 **枚举→名字** 的跳转分派:
```
001F6E64  lui   $v0, 0x0057
001F6E68  addiu $v1, $v0, 30592       ; 跳转表 @0x577780[10]
001F6E6C  sll   $v0, $s0, 2
001F6E70  addu  $v0, $v0, $v1
001F6E74  lw    $v0, 0($v0)
001F6E78  jr    $v0
case0..9: RSString("Movies" / "ConceptSketches" / "Music" / "Weapon" / "Awards" /
                   "BackStory" / "SpecialistProfile" / "Background" /
                   "Interview" / "GameTrailer")
```
跳转表: [0]0x1F6E80→Movies [1]0x1F6EB0→ConceptSketches [2]0x1F6EE0→Music
[3]0x1F6F10→Weapon [4]0x1F6F40→Awards [5]0x1F6F70→BackStory
[6]0x1F6FA0→SpecialistProfile [7]0x1F6FD0→Background [8]0x1F7000→Interview
[9]0x1F7030→GameTrailer

- 该返回值被 **10 处**消费 (`InitFromSFStudio` ×2, `SetStudioType` ×3,
  `CheckStudio_Group_Item_SubItem_LockUnlock`, `Finish`, `ProcessMessage` ×2, `SetVisible`)
  全部用于 `RSString::operator==(const char*)` **比较**;
- **P1 实验证明: 只改 ELF 一侧也断链** → 比较的另一端不是 XML 的 name (或不止 XML),
  故"双向同步改名"也不可行;
- `ConceptSketches` / `Background` 另有 5 处引用 (0x1F6004/0x1F6150/0x1F62B8/0x1F6AD8/0x1F7DFC),
  全部同为 `__eq__` 比较, 位置都在 SFStudio 类内。

**下一步 (代码级方案)**: 保留英文标识不动, 在**显示最后一步**插入"英文→中文"查表;
  或在比较点插入 cave 做双向归一。前提是先定位 studio 名**实际被绘制的调用点**
  (本轮尚未打通"进入 studio 内部"的导航, 该屏的 group 标题绘制点待确认)。

#### 交付
- **GR_ZH81** sha256 `307abccce31a3371ab53b57fc73e97179ae73fb81590a9645f8e5a9e6a3296ba`
  = GR_ZH79 + XML 41 个 group 名汉化 (studio 保持英文); 全盘 diff 相对 GR_ZH79 仅 1 段
  (MENU+0x3771800, XML 条目内);
- 实测: 首行高亮 BGR 与基准**逐值相同** → 光标正常; ISO 尺寸/头部/条目表零改动,
  亦未触碰模拟器 → 可在标准模拟器运行。

#### §47 最终验证: EN 原盘同帧逐行对照 (2026-10-04)

用标定导航 (`work/_dis/nav_sf_ok.txt`) 跑 EN 原盘, 同样在 **F5442 进入**、**F5500 稳定**,
与 GR_ZH81 同帧逐行对照:

| EN 原盘 (F5500) | GR_ZH81 (F5500) | 状态 |
|---|---|---|
| Movies (黄色高亮框) | **影片** (黄色高亮框) | ✅ 光标位置一致 |
| Sketches | 设定图 | ✅ |
| Music | 音乐 | ✅ |
| Weapons | 武器 | ✅ |
| Awards | 奖章 | ✅ |
| Background | 背景 | ✅ |
| (空白框, 未解锁) | (空白框, 未解锁) | ✅ 行为一致 |
| Screenshots | 屏幕截图 | ✅ |
| Interview | 访谈 | ✅ |
| Game Trailers | 预告片 | ✅ |

- **星标解锁状态、光标位置、右侧预览图全部一致**; 第 7 行空白在 EN 原版**同样空白**
  (= `G58.I745 Specialist` 未解锁, 非翻译缺陷);
- 列表 10 项文案来自 **RES G58.I739-748**, 已全部汉化 (由 `dump_all_text` 总表核验);
- 对照图 `work/builds/GR_ZH81/temp/cmp/sf_EN_vs_ZH81_final.png`。

**结论: 特别收录的列表文案 (来自 RES) + 分栏标题 group 名 (来自 XML) 已全部汉化;
studio 名 (ELF 内部标识) 不参与显示, 无需汉化。该部分汉化完成且无错。**

### 48. 特别收录: item 名规范重译 + 取消空格填充 + 状态机导航 (GR_ZH82)

#### 用户报障 (GR_ZH81 实机)
1. 特别收录 → **影片**: 仍显示 "GR 任务 1"、"GR 片头" 这类**缩写+中文+空格**格式,
   未按现行规范译为 "幽灵行动®任务N"; 目测名称中间多了空格。
2. 特别收录 → **设定图**: 文字已汉化但**没有居中**, 后面似乎跟了几个空格。

#### 根因 (字节级定位)
- **问题 1**: 上一版 (GR_ZH81) **只改了 `<studio|group>` 的 name, 漏了 `<item name=...>`**。
  而这些 `<item name>` 是 **zh7 时代**用"缩写+中文+空格"格式译的:
  ```
  <item name="GR Opening">   → name="GR 片头"        (47 52 20 A6DB A6C3)
  <item name="GR Mission 1"> → name="GR 任务 1"      (47 52 20 DAC9 20 31)
  <item name="M24">          → name="M24 狙击步枪"
  ```
  共 25 条 GR/DS 前缀 item 与现行规范不符 (且 "GR"/"DS" 完全未译)。
- **问题 2**: 上一版为保持"槽内等长"给译名**补了 0x20 空格** (如 `士兵␣␣␣␣`);
  游戏把尾随空格**计入文本宽度** → 视觉左偏 → 看起来没居中。

#### 本版修复 (tools/iso_build/patch_zh82.py)
- **`<item name>` 25 处** 按现行规范重译:
  `GR Mission N`→`幽灵行动®任务N`、`DS Mission N`→`沙漠风暴任务N`、
  `GR Opening/Ending`→`幽灵行动片头/片尾`、`DS Opening/Ending`→`沙漠风暴片头/片尾`;
- **`<group name>` 41 处** 全部重译, **不再补任何空格**;
- **`<studio name>` 保持英文** (引擎内部标识, 见 §47);
- 译名变长 → **XML 内容整体重排** (116430 → 116486 B, +56), 8 子流边界重划,
  重压 40187 B / 槽 49700 (余 9513);
- 脚本内断言: item=25、group=41、**无 `name="GR |DS "` 残留**、**任何 name 值不得以 0x20 结尾**。

#### 验证
- `GR_ZH82` sha256 = d690d95c662eda96170f93f06b2260e1a3847c90b027747ac48777ac4dbb161f
- 模拟器实测: 到达特别收录屏 (F5442), **列表首行高亮 BGR = [48.5 100.2 124.1]**
  与基准 GR_ZH79 **逐值相同** → 光标正常;
- 文本总表行数 7460 → **7717** (新增 item/group 名逐条入表)。

#### 状态机导航 (响应用户建议, tools/capture/nav_state.py)
用户建议: "新增一个导航逻辑, 通过钩子来读取当前的对应状态, 用状态机来实现导航, 防止漂移。"

**现状评估**: 模拟器为预编译产物 (`pcsx2-gsrunner.exe`), 源码在 `third_party/emu/pcsx2_src/`,
重建需 MSVC 工具链 (本机无 `cl`) → 本轮**不改模拟器**。但模拟器**已提供运行时状态钩子**:
- `-grdrawwin <a> <b>`: 输出每帧**绘制站点 + 参数** (drawlog) —— 等价于渲染钩子;
- `-grneedle`: 在 EE/IOP 内存里扫字节 needle;
- `-grinput` 的输入序列在启动时固定, **无法运行时改写**。

**实现**: `tools/capture/nav_state.py` = **外层状态机**:
1. **观测**: 读 drawlog, 解出每帧绘制的中文文本;
2. **判定**: 按特征串分类当前界面 ——
   `FILE_SELECT`(选择你的档案) / `SPECIAL_FEATURES`(影片+设定图+屏幕截图) /
   `CAMPAIGN_DIFF`(选择难度+新兵) / `MULTI_NAME`(输入你的名字) /
   `OPTIONS`(游戏玩法) / `MAIN_MENU`(战术演习+快速任务) / `UNKNOWN`;
3. **决策+执行**: 依次尝试"主菜单上移 k 次"(9 项首尾环绕, 理论上 k=3 → 特别收录),
   每轮用分类器**确认落点**, 命中即保存标定导航 `work/_dis/nav_state_<版本>_ok.txt`;
4. **抗连发**: 每个按键 = `tap` + 紧跟 `release`(fr+2) 的 2~3 帧短按
   (见 §46: `tap` 默认按住 12 帧会被菜单连发, 是历史导航漂移的根因)。

**分类器实测** (对既有 dump 回放):
| dump | 判定 | 特征 |
|---|---|---|
| ZH82 `dump_v82` | SPECIAL_FEATURES | 影片/设定图/屏幕截图 |
| ZH78 `dump_sfB78` | SPECIAL_FEATURES | 影片/设定图/屏幕截图 |
| ZH78 `dump_sf78b` | CAMPAIGN_DIFF | 选择难度/新兵/老兵 |
| ZH78 `dump_sf78` | FILE_SELECT | 选择你的档案 |
→ **判定准确**, 状态机可据此收敛, 不再盲猜时序。

### 49. 工程清理与定稿 (GR_ZH82 用户实测通过后)

#### 现役盘
| 版本 | 说明 | sha256 |
|---|---|---|
| **GR_ZH82** | **现役交付盘**: 特别收录 item 名规范重译 25 处 + group 名 41 处, 零空格填充 | `d690d95c662eda96170f93f06b2260e1a3847c90b027747ac48777ac4dbb161f` |

- 用户实机测试: **通过**;
- 校验: 全盘 `name` 属性 **GR/DS 残留 = 0**、**尾随空格 = 0**;
  10 个 `<studio name>` 保持英文 (引擎内部标识); ISO 尺寸 / MENU 头部 / 条目表零改动。

#### 清理记录 (磁盘 47.2 GB → 5.87 GB, 释放 41.3 GB)
**保留**:
- `work/builds/GR_EN_ORIG/` —— 英文原盘, `tools/diag/dump_all_text.py` 的参考基准 (必需);
- `work/builds/GR_ZH82/` —— 现役盘 (+ `temp/dump_v82` 验证现场与对照图);
- `work/builds/GR_EN_ORIG/temp/dump_enf/` —— EN 原盘特别收录屏同帧对照现场;
- `work/builds/GR_ZH82/temp/dump_sm3/` —— 状态机导航命中轮现场;
- `work/archive/` (4.9 MB) —— 各轮关键对照图 6 张 + GR_ZH82 全量文本总表 xlsx。

**删除** (均可由脚本复现):
- 中间构筑 11 个: `GR_ZH72` `GR_ZH73` `GR_ZH74` `GR_ZH75` `GR_ZH76` `GR_ZH77` `GR_ZH78`
  `GR_ZH79` `GR_ZH80` `GR_ZH81` + 子代理遗留 `BISA` `BISB` `BISC` `BISD` `BISE`;
- 探针盘 6 个: `probeA` `probeB` `probe_p1_elf` `probe_p4_group` + `work/_dis/{E1,E2,E3}.iso`
  (P1~P4 探针结论已固化进 §47, 盘无需留存);
- 临时盘: `work/_squad/*.iso` (_zh77/_zh78/_zh79b_test)、`probe*.iso`、`SLUS_*_test.elf`;
- 冗余 drawlog: 状态机试错轮 `sm1/sm2/sm4/sm5/sm6`、EN 盘 8 个探索性 dump、
  `work/_dis/temp`、子代理 `work/_squad/dump_bisA~E`。

#### 复核
- 现役盘 sha256 与提交记录**逐字符一致** (`d690d95c662eda96170f93f06b2260e1a3847c90b027747ac48777ac4dbb161f`);
- 磁盘可用空间 88.9 GB → **143.1 GB**。

#### 当前工程闭环状态
1. ✅ **构筑管线**: 每次构筑自动产出全量文本总表 (`all_text.xlsx` / `.csv` / `summary.*`);
2. ✅ **特别收录**: 列表文案 (RES) + item 名 + group 分栏标题 (XML) 全部汉化, 空格零填充;
3. ✅ **回归修复**: GR_ZH78 的特别收录屏故障已修 (根因 = 误译引擎比较键, 见 §46);
4. ✅ **状态机导航**: `tools/capture/nav_state.py` 用 drawlog 作状态钩子, 判界面后迭代收敛,
   取代盲按时序 (见 §48);
5. ⏳ **未完成项** (供后续): 特别收录"进入栏目后的 group 标题"那一屏的本机可视化验证
   (group 名已汉化且由 P4 探针证明光标零影响, 但状态机尚无"屏内选择并进入"的动作);
   若要单次运行内动态导航, 需重建 `pcsx2-gsrunner` (需 MSVC 工具链)。

### 50. 任务名(关卡名)专用 12px 双字库 — 完成 (2026-10-05, GR_ZH353)

#### 需求
用户要求: **只有任务名(关卡名)用 12px**, 不动其它 16px 内容, 不污染任何其它界面。

#### 难点与突破 (9 轮, 逐轮证据 `work/_dis/TWELVEPX_ROUND1..9.md`)

| 轮 | 突破 |
|---|---|
| 1-2 | 定位关卡名绘制链: 样式 `A3=006892DC` → 面 `0x688B68`('default') → 记录基址 `0x687D90`; 关卡名用 `default` 面, 文件列表用 `large` 面 |
| 3 | **引擎采样坐标 `u = 记录 u0 − 288`**(10 组二进制消失实验 + 交叉求解 + 涂色验证 9/9) |
| 4 | 找到关卡名数据源: `MENU.IMG #170` 子流@0 的 `<MissionFile>` XML(LZO 内, 裸搜不可见) |
| 5 | 换码位方案落地: `GR-` → `0x8E 0x8F 0x91`, **12px 且零污染** |
| 6 | 宽度/定位管线全定位: `0x21AC00`(串宽) → cave `0x417150` → `0x21AD10` → `rec[1] × style[+28]`; 定位 `x = 容器左 + (容器宽 − 文本宽)/2` |
| 7 | 发现 XML 有**两份副本**(`MENU.IMG #170` + `GR.IMG #661`); 重做实验确认 `<MapName>`/`<Name>` 均非来源 |
| 8 | **方法论突破**: `run_late.py` 把转储帧推到战役画面(10327), 确认 `GR-M01` 是**资源包名**(运行时构造, 不在 ISO 任何数据流中) |
| 9 | **最终方案**: 找到日期/时间来源(`MENU.IMG #25` / `GR.IMG #902`), 用 `<0x80` 罕见 ASCII 占位码位消除污染 |

#### 最终方案 (`tools/iso_build/patch_zh12px.py`)

1. MENU.IMG 图集 `v=480..495`(实测全空) 铺 14 个 12px 字形, 步进 14 texel;
2. 空闲码位 `0x84..0x91` → `0`-`9`/`G`/`R`/`M`/`-`, FT **三面** idx 100..113 改记录;
3. ELF 字符串资源 `GR-`(VA `0x57ED20`) → 换码位;
4. `MENU.IMG #170 <MapName>` → `\x90\x84\x85 Caves`;
5. `default` 面新增占位码位 `0x5E`/`0x60` ← idx 16/17 的**原 16px 字形**;
6. `default` 面 idx 45(`M`)/16(`0`)/17(`1`) → 12px 字形(**保留原推进**, 免字距变化);
7. `#25`/`#902`: `Apr 16, 2008`→`Apr \x60 6, 2\x5E\x5E 8`; `05:45`→`\x5E 5:45`。

#### 三个关键机制 (实测, 非推测)
1. **采样坐标** `u = 记录 u0 − 288` ⇒ 要采到图集位置 `P`, 记录写 `u0 = P + 288`;
2. **推进 = `rec[1]`**(`0x21AD10` 返回 `rec[1] × style[+28]`);
3. **⚠ 码位 ≥ 0x80 在宽度计算里被当成全宽** ⇒ 占位码位必须 `< 0x80`
   (用 `0x92/0x93` 时日期文本左移 ~7 px, 实测 427 px 差异; 改 ASCII 后 0 px)。

#### `M`/`0`/`1` 为何不能换码位
这 3 个字符的码位由**代码生成**。8 轮排查已排除: `<MapName>`/`<Name>`/`<Environment>`
(各两份副本)、`.MIS` 文件名、ELF `M01_CAVES.mis`、记忆卡、`MapNameId` 常量;
运行时包名 `GR-M01` 在**全部 LZO 子流与裸搜中均为 0 处**。
⇒ 只能把 `default` 面记录 UV 借到 12px; 而该面被日期/时间共用
⇒ 用第 5/7 步的占位码位把日期/时间搬回 16px。

#### 验证 (GR_ZH353 vs 英文原盘, 战役简报 F11000)
```
总差异 359 px
  关卡名 GR-M01      347 px   ← 6/6 全部 12px
  日期/时间/年份        0 px   ← 零污染
  简介/标题/按钮/地图/底部栏  0 px
  任务目标              12 px
```
- ISO 1,648,164,864 B; MENU.IMG 686 条目 / GR.IMG 4070 条目, 越界/未对齐/重叠 = 0;
- 对比图 `work/archive/cmp/GR_ZH353_final.png`(英文原盘 16px ↔ GR_ZH353 12px)。

#### ⚠ 制作组名单勘误
此前把 `EN_STRINGS.RES` 当作"制作组名单"是**错误的** —— 其原盘内容是
`Victory!` / `Firefight` / `The players win if all enemies are eliminated`,
属**游戏内 UI 提示文本**, 本地化成中文是预期交付内容。

**真正的制作组名单 = `GR.IMG #551..#565`**(15 个含 `CREDIT` 的文件, 共 826,392 B):
`GR_ZH253` / `GR_ZH256` / `GR_ZH353` 三盘实测 **0 字节差异**(完全不触碰)。

#### 现役盘 (2026-10-05)
| 版本 | 用途 | 关键点 |
|---|---|---|
| **`GR_ZH353`** | **★ 12px 最终盘** | 关卡名 6/6 全部 12px + 零污染 |
| **`GR_ZH256`** | **主本地化交付盘** | 理想人名译名 + 间隔号 `·`, 零回归; 关卡名保持 16px |
| `GR_ZH253` | 反汇编/补丁**基准盘** | 含 Plan C 码位方案(`0x7F..0x83`); `GR_ZH353` 的 `--from` 基底, **勿删** |
| `GR_EN_ORIG` | 英文原盘基线 | **硬链接**到 `third_party/orig/ps2/Tom Clancy's Ghost Recon (USA).iso`(sha256 `2b42ea7c…`), 零额外占用 |

#### 清理记录 (磁盘 7.80 GB → 6.20 GB, 释放 1.60 GB)
**删除**(均可由 `make_build.py` / `run_opt.py` 重建):
- `temp/dump_*` 转储 10 个(`GR_EN_ORIG/dump_C_EN2`、`GR_ZH253/dump_{C253,C253b,CAMP2,CAMPAIGN,LATE10327,M1,M2}`、`GR_ZH256/dump_C256`、`GR_ZH353/dump_Y353`);
- `extract/` 字表提取 3 个(`GR_ZH253`/`GR_ZH256`/`GR_ZH353`, 各 55.9 MB)。

**保留**: 4 个 ISO + `build_info.json` + `temp/mc/`(记忆卡, 小且省时间)。
中间版本 `ZH83~ZH352`(约 270 个探针/实验盘)在本轮之前已随各轮清理删除。

#### 未完成 / 供后续
- 关卡名若要显示**中文译名**(而非 `GR-M01`), 需改**代码生成**的 token(代码层, 8 轮已排除全部数据源);
- `huge` 面仅 96 条记录, idx ≥ 96 走网格回退公式(不影响本方案, 未用到)。

### 51. 读档卡死破案: GR_ZH253 的实验性 ATR 扩展破坏 GR.IMG 布局 (2026-10-06, 用户报障)

#### 用户报障
> GR_ZH253 稳定复现在 Press START button 界面后卡死, 画面卡在"正在读取数据"屏,
> 背景音乐不断在一小节内循环。记忆卡 temp/Mcd001.ps2。

#### 复现与判据
新增 `work/_dis/detect_stuck.py`: 比较相邻截图, 连续 N 帧逐像素相同 ⇒ 卡死。
```
GR_ZH253 + 用户卡        ⇒ 从 f05000 起连续 80 帧相同 ⇒ 卡死 ✓ 复现
GR_ZH253 + 模板卡        ⇒ 未卡死
GR_ZH256 + 用户卡        ⇒ 未卡死
GR_ZH353 + 用户卡        ⇒ 卡死
```
截图确认卡死画面 = **"正在读取数据。请勿移除记忆卡槽1里的记忆卡(8MB)…"**。

#### 排除过程 (存档本身无问题)
| 卡 | 结果 |
|---|---|
| 模板卡 (sha `73f929fe…`) | 未卡死 |
| 用户卡 (sha `f2d78a4d…`) | 卡死 |
| 用户卡 − `BASLUS-20613GHOST002` 目录项 | 卡死 |
| 用户卡 + 存档数据区换成模板卡 | 未卡死 |
| **模板卡 + 用户卡 GHOST001 数据 (page 7042..7284)** | **卡死** |
| **英文原盘 + 用户卡** | **正常 (用户实测确认)** |

⇒ 存档无损坏 (英文原盘可正常游玩) ⇒ **汉化盘的问题**。

#### 根因 (build_info.json 对比)
```
GR_ZH253: base=GR_ZH251, patch=work/_dis/atr_expand_v3.py   ← **ATR 条目扩展 (实验性)**
GR_ZH256: base=GR_ZH251, patch=work/_dis/atr_dot_patch2.py  ← **ATR 人名间隔号 (原位等长, 最终方案)**
GR_ZH353: base=GR_ZH253, patch=tools/iso_build/patch_zh12px.py
```

**GR.IMG 条目位置与原盘不同的数量**:
```
GR_ZH253: **199 个**, 最高 off+stored = 1550502528 (0x5C6ACA80)  ← 超原盘 6.3 MB
GR_ZH256:   14 个, 最高 off+stored = 1544205912 (0x5C0AB658)  ← 与原盘一致
```

⇒ `atr_expand_v3.py` 把 ATR 条目**扩大**, 引发 199 个条目**连锁搬迁**;
游戏对 GR.IMG 某些条目有**硬编码偏移访问** ⇒ 搬迁后读档失败 ⇒ 卡死。

#### 修复
**以布局正常的 `GR_ZH256` 为基底重建 12px 盘**:
```
make_build.py GR_ZH360 --from work/builds/GR_ZH256 --patch tools/iso_build/patch_zh12px.py
```
(两者 MENU.IMG sha256 完全相同 `40ed5a4f…` ⇒ 字库/图集/FT 状态一致, 补丁可直接复用)

#### 验证 (GR_ZH360)
| 项目 | 结果 |
|---|---|
| GR.IMG 搬迁条目 | **14 个 (与原盘一致)** ✓ |
| GR_ZH360 + 用户卡 | **未卡死** ✓ |
| GR_ZH360 + 模板卡 | **未卡死** ✓ |
| 关卡名 12px | 347 px 全 12px ✓ |
| 日期/时间/年份/简介/标题/按钮/地图 | **0 px 零污染** ✓ |
| 总差异 (vs 模板卡基线) | 359 px (仅关卡名 347 + 目标区 12) |

#### 纪律沉淀
1. **`GR_ZH253` 是废弃的实验盘** (含 `atr_expand_v3.py`), **不得作为交付或基底**;
   `patch_zh12px.py` 的 docstring 已加警告, 基底改用 `GR_ZH256`。
2. **GR.IMG 条目位置与原盘一致是硬约束** —— 与 MENU.IMG 的
   "内部偏移不得移动" 同等重要 (游戏有硬编码访问)。
3. **构筑后必须检查布局**: 对比 `off/stored` 与原盘, 搬迁条目数应仅为**必要**的少量。
   工具 `work/_dis/diff_iso_entries.py`。
4. 新增工具 `work/_dis/detect_stuck.py` (卡死判据) 与 `work/_dis/mk_card.py` (测试卡生成)。

#### 现役盘更新
| 版本 | 用途 |
|---|---|
| **`GR_ZH360`** | **★ 12px 最终盘 (修复读档卡死)** —— 基底 `GR_ZH256` + `patch_zh12px.py` |
| **`GR_ZH256`** | **主本地化交付盘** (布局与原盘一致) |
| `GR_ZH353` | **已废弃** (继承 GR_ZH253 的 199 个搬迁 ⇒ 读档卡死) |
| `GR_ZH253` | **已废弃** (实验性 ATR 扩展盘) |

### 52. 12px 范围修正: 关卡名改用「语言表 token 换码位」(用户报障三项) (2026-10-06)

#### 用户报障
> ① 你的修复触碰到了之前对每个字符位置的偏移 ⇒ 菜单、标题界面出现先前修好的错位
> ② 12px 范围出错: 进入 GR-M01 全部 12px, 但 GR-M02 最后的 `2` 变回 16px;
>    任务简报页任务目标的 `1` 也变成 12px 而不是 16px
> ③ 战术演习每个任务简报右上角仍是汉化的「战术X」, 要求恢复英文 `TAC0x`

#### 破案: 关卡名的真正来源
**`EN_STRINGS.RES` 语言字符串表** (`MENU.IMG #25` / `GR.IMG #902`, 两份同内容):

```
容器: {u32 组数} + 每组 {u32 条目数} + 条目 {u32 len}{data[len]}{u16 attr}
右上角显示 = 该任务条目的首个 token (取「首个空格字节偏移」按 DBCS 感知拷贝 n 字符)
  战役模式      : 取 MapName 条目, 前面拼 ELF 静态串 "GR-" (VA 0x57ED20, 字符串 id 0x4DEC1)
  战术演习模式  : 取 Name 条目, 无前缀
```

实测对照:
| 盘 | 战役 M01 | 战术演习 TAC01 |
|---|---|---|
| EN 原盘 | `M01 Caves` → `GR-M01` | `TAC01 Shooting` → `TAC01` |
| 汉化盘 | `M01 山洞` → `GR-M01` | `战术1 射击` → `战术1` |

#### 根因 (为什么 v1 会污染)
`GR-M01` 的 `M`/`0`/`1` 是 ASCII 码位, v1 为把它们变 12px
**借用了 `default` 面的 idx 16/17/45 记录**, 并把日期里的 `0`/`1` 换成占位码位 0x5E/0x60 规避。
后果: 所有走 `default` 面的 `M`/`0`/`1` 全变 12px
⇒ 任务目标 `1` 变 12px (报障 ②)、菜单/标题含数字或 M 的文字错位 (报障 ①)、
`M02` 的 `2` 未借到仍 16px (报障 ②)。

#### 修复 `tools/iso_build/patch_zh12px2.py` (v2)
| 步 | 内容 |
|---|---|
| 1 | 12px 字形带 v=480..495, 25 个字形 (0-9 M D P G R T A C a c r i n g -) |
| 2 | FT 三面 idx 95..120 (码位 0x7F..0x91 + 0x93..0x98, **跳过 0x92**) → 12px 记录 |
| 3 | ELF `GR-` → 占位码位 |
| 4 | 宽度表 25 码位 → 8 |
| 5 | **语言表 43 个 MapName/Name token → 占位码位** (战役 MapName 38 + 战术演习 Name 5) |
| — | 删除: 借 `default` 面记录、日期串占位、MENU.IMG #170 XML 改动 |

纪律: 占位码位必须 `< 0xA1`(DBCS 感知拷贝) 且 `≤ 0x9B`(宽度表范围); 0x92 基盘有独立字形必须跳过;
条目表 off/stored/real 一律不动。

#### 验证
```
GR_ZH361 (战役, 模板卡 + navM2, 13000 帧):
  未卡死; vs 16px 基线 GR_ZH253 同 nav 同卡:
    总差异 357 px — 全部在关卡名区 (GR-M01 全 12px ✓)
    日期/时间/年份/任务目标/简介/标题/继续按钮/地图/底部提示 全部 0 px ✓
GR_ZH362 (战术演习, 模板卡 + navTAC, 14000 帧):
  简报右上角 战术1 → **TAC01** (12px) ✓

静态核对 (GR_ZH256 → GR_ZH361):
  ELF 23 B (仅 GR- + 宽度表); FT 仅 large/default 面 idx 95..120;
  图集仅 398 texel (y484..491 x1..341); **MENU.IMG/GR.IMG 条目表 0 变动** ✓
静态核对 (GR_ZH361 → GR_ZH362):
  ELF 0 / 图集 0 / 条目表 0 — 只差语言表 5 条 TAC Name ⇒ 战役行为逐字节相同 ✓
```

对比图: `work/archive/cmp/GR_ZH361_final.png`

#### 现役盘更新
| 版本 | 说明 |
|---|---|
| **`GR_ZH362`** | **★ 12px 最终盘** (v2 补丁; 战役 + 战术演习右上角均 12px 且零污染) |
| `GR_ZH361` | 同 v2 但未含 TAC Name 修正 (战术演习仍显示「战术1」) ⇒ 已被 362 取代 |
| `GR_ZH360` | v1 借记录方案 ⇒ **有污染, 勿用** |
| `GR_ZH256` | 16px 主交付盘 (无 12px) |
| `GR_ZH253` / `GR_ZH353` | **废弃** (199 条目搬迁 ⇒ 读档卡死) |

#### 遗留
1. 训练关 (T01..T07) 的 MapName 在汉化表里不是 `Training`, 本轮未定位其 token
   ⇒ 训练关关卡名暂未变 12px
2. `GR_ZH361`/`GR_ZH362` 只做了模板卡验证, 用户卡(含 GHOST001/002 存档)尚未复跑
3. `detect_stuck.py` 会把「静态简报页」误判为卡死 (需按画面内容区分)

### 53. 关卡名来源修正: 取的是 Name 不是 MapName (GR_ZH363) (2026-10-06)

#### 用户反馈 (第 10 轮交付后)
> TAC01 成功修改, 但是 GR-M01 里面的 M01 还是 16px

#### 复查: 按字形高度逐字符测量 (F11000 战役简报右上角)

| 盘 | "GR-" 三字符 | "M01" 三字符 |
|---|---|---|
| 16px 基线 `GR_ZH253` | h10 / h10 / h10 | h10 / h10 / h10 |
| v1 `GR_ZH360` (借记录) | h8 / h7 / h2 | h8 / h8 / h8 |
| v2 `GR_ZH361/362` (只改 MapName) | h8 / h7 / h2 ✓ | **h10 / h10 / h10 ✗ 仍是 16px** |

⇒ 上一轮把「战役取 MapName」当结论是**误判**: 那次对比只看到"关卡名区 357 px 差异",
其实是**只有 "GR-" 三个字符变了** (它是 ELF 静态串, 独立绘制), `M01` 根本没变。

#### 正确结论: **两种模式都取 `Name` 条目**

| 模式 | 显示 | 取值条目 | 前缀 |
|---|---|---|---|
| 战役 | `GR-M01` | **Name** (`M01 - 铁龙`) | ELF 静态串 `GR-` |
| 战术演习 | `TAC01` | **Name** (`战术1 - 射击`) | 无 |

(这也解释了为什么只改 TAC 的 Name 就能修好战术演习, 而战役没修好。)

#### 修复: `patch_zh12px2.py` 第 5 步扩展到 Name 条目

| 条目类 | 模式 | 替换 (全部等长) |
|---|---|---|
| 战役 Name | `M01 - 铁龙` / `D01 …` / `DP01 …` / `MP01 …` | 首个 token → 占位码位 (ASCII 原样换码位) |
| 训练关 Name | `训练N - 越野训练` (`c2 b3 3N 20 2d 20`, 6 B) | → 占位 `T0N` + `" - "` (6 B) |
| 战术演习 Name | `战术N - 中文` (`ba a4 f0 3N 20 2d 20`, 7 B) | → 占位 `TAC0N` + `" -"` (7 B) |
| 战术演习 MapName | `战术N 中文` | → 占位 `TAC0N` + 空格 |
| 战役 MapName (保留) | `M01 山洞` | 首个 token → 占位码位 (等长, 中文词保留) |

⇒ `MENU.IMG #25` / `GR.IMG #902` 各 **73 个条目**（两份完全一致）

#### 验证 `GR_ZH363`

```
上机 (模板卡 + navM2, 13000 帧, 战役 F11000 简报页):
  GR-M01 六字符高度 = h8 / h7 / h2 / h7 / h8 / h8  ⇒ **全部 12px ✓**
  vs 16px 基线 GR_ZH253 同导航同卡: 总差异 353 px, **全部在关卡名区**;
    日期 / 时间 / 年份 / 任务目标 / 简介 / 标题 / 继续按钮 / 地图 全部 0 px ✓

静态 (GR_ZH256 → GR_ZH363):
  ELF 23 B (GR- + 宽度表); 图集 398 texel (y484..491 x1..341);
  FT 仅 large/default 面 idx 95..120; **MENU.IMG / GR.IMG 条目表 0 变动** ✓
  逐字节: M01 Name `4d3031202d20…` → `897f80202d20…`; M02 → `897f8120…`;
          训练1 Name `c2b331202d20…` → `8e7f80202d20…`; TAC01 Name → `8e8f907f80202dc0b6` ✓
```

#### M02 上机验证 (成功)
两条路都试过:
1. **用户存档卡路径**「战役 → X → 下 1 次 → X」在本模拟器**无法复现**:
   把用户卡 (`temp/Mcd001.ps2`, sha256 `F2D78A4D…`) 放进 `temp/mc/` 后,
   游戏停在「选择文件」层 (2 个 TEQSUNSET + 空位 + 新建); `grlog.txt` 显示所有按键
   (bind 0/2/6) **都已注入**但画面完全不变 ⇒ 该卡镜像在本模拟器构建下不被识别
   (输入被忽略), **不是补丁问题**。**注意: 原始 `temp/Mcd001.ps2` 未被改动 (hash 未变)**。
2. **快速任务路径** (最终成功): `navQ2d.txt` = 主菜单下移 2 次 → 快速任务 →
   设置页「任务」字段按 **右** 改成 M02 → 连按 X 依次确认 → 简报页 (f11900 起)。
   - 简报页内容确认为 M02 (任务目标 = `1 - 营救飞行员` / `2 - 营救武器官` /
     `3 - 前往撤离区` / `X - 摧毁机载设备`)
   - **右上角 `GR-M02` 六字符高度 = h8 / h8 / h2 / h7 / h8 / h8 ⇒ 全部 12px ✓**
     (与 M01 完全一致; 16px 基线是 h10/h10/h10/h10/h10/h10)

#### 现役盘
| 版本 | 说明 |
|---|---|
| **`GR_ZH363`** | **★ 最终盘** (战役 `GR-M01` 6/6 全 12px + 战术演习 `TAC01` + 零污染) |
| `GR_ZH362` / `GR_ZH361` | 只改了 MapName ⇒ 战役 `M01` 仍 16px ⇒ 已被 363 取代 |
| `GR_ZH360` | v1 借记录 ⇒ 污染文本 ⇒ 废弃 |
| `GR_ZH256` | 16px 主交付盘 / 构筑基底 |
| `GR_ZH253` / `GR_ZH353` | 废弃 (读档卡死) |

对比图: `work/archive/cmp/GR_ZH363_final.png`

### 54. ★★ 「所有战术演习任务进入游戏后卡死」根因: GR.IMG 14 个条目被 ATR 补丁搬走 (GR_ZH366 / GR_ZH267) (2026-10-06)

#### 用户报障
> 出现 bug: TAC01 选择进入游戏之后卡死；补充: **所有战术演习任务加入都卡死**

#### 模拟器复现 (同导航 `navTACe.txt`: 战术演习 → 简报页 → X 接受 → 进入关卡, 20000 帧)
| 盘 | 简报页后 | 结论 |
|---|---|---|
| **英文原盘 `GR_EN_ORIG`** | f11300 起持续变化 (f12000 变化 204238 px … f19900 仍 6101 px) | **正常进入并运行 ✓** |
| `GR_ZH256` (16px, **无 12px 补丁**) | f10400 起**全 0 变化** | **卡死 ✗** |
| `GR_ZH363` (12px 盘) | 同上 | **卡死 ✗** |

同法测**战役** (`navM2e.txt`): `GR_ZH256` 简报页 → X → 画面自 f12400 完全静止 ✗
⇒ **卡死与 12px 补丁无关**, 且**战役/战术演习都卡死** (用户只是先试了战术演习)。

#### 逐项排除
| 实验 | 结果 |
|---|---|
| `GR_T2` = 英文原盘 + 汉化 `EN_STRINGS.RES` (两份) | **正常进入 ✓ ⇒ 语言字符串表无罪** |
| 汉化字库 `huge` 面被截断 96 条 (原盘 224, `fld=[…,16,14]`→`[…,16,6]`); 面外正是 `{u32 nstyles}=8` ⇒ 记录 `f1=0` ⇒ 布局死循环。补到 224 条 (`GR_ZH365`) | **仍卡死 ✗** (但缺陷真实, 已修) |
| **GR.IMG 条目 `off` 逐条比对** | **14 个条目被搬到 GR.IMG 尾部 ⇒ 根因** |

#### 根因
ATR「间隔号 `·`」补丁 (`work/_dis/atr_dot_patch2.py`) 把 .ATR 名字换成更长的
「理想译名+`·`」, 内容涨 1~4 B, 原槽放不下 ⇒ **补丁把 14 个条目搬到 GR.IMG 尾部**
并改写条目表 off/stored/real:
```
STRINGS.TXT  0xCB37190 → 0x1CAC2000
DEMOLITIONS-03/05/11/15/21/28/43/49/51.ATR
D_SCOTT_IBRAHIM.ATR  SCOTT_IBRAHIM.ATR  RIFLEMAN-07.ATR  RIFLEMAN-54.ATR
```
`.ATR` 是**任务数据**, **关卡开始时读取** ⇒ 位置与原盘不一致 ⇒ 读取失败 ⇒ 卡死。
正是工程铁律「**GR.IMG 条目位置必须与原盘一致**」所警告的情况
(第 9 轮 `GR_ZH253` 的 199 次搬迁 = 读档卡死)。

#### 修复 `work/_dis/r11_atr_unmove.py`
14 个条目**写回原偏移**, 条目表 off/stored/real 恢复原盘值 ⇒ **位置 0 差异**:
- 13 个 `.ATR`: 汉化内容比原槽大 1~4 B ⇒ 退回**英文原盘内容** (长度正好)
- `STRINGS.TXT`: 汉化 6090 B > 原槽 2587 B ⇒ 退回英文原盘内容

代价: 这 13 个 ATR 名字回到英文 (均为 `DEMOLITIONS-xx`/`RIFLEMAN-xx` 通用兵种名 + `SCOTT_IBRAHIM`);
**其余全部 .ATR (含带 `·` 的人名) 保持汉化** ✓。

#### 上机验证
```
GR_ZH366 (12px + ATR 修复): 战术演习简报 → X →
  f11300:166926 → f12000:202759 → … f19900:5906 (持续变化)
  ⇒ **与英文原盘同样的"进入并运行"曲线 ✓✓ 卡死消除**
GR_ZH267 (16px + ATR 修复): 见同轮验证
```

#### 12px 同步加固 (第 10 轮遗留的结构性改动已回退)
| 位置 | 第 10 轮 | 现在 |
|---|---|---|
| 战术演习 `MapName` | 整串换 `"TAC01  "` (丢第二个词) | **不动** |
| 战术演习 `Name` | `"战术1 - 射击"` → `"TAC01 -射击"` (`" - "` 少空格) | `战术N`(4 B) → 占位 `TAC`+数字, **`" - 射击"` 原样保留** |
| 战役/训练关 `MapName` | token 换占位码位 (对显示无影响) | **不动** |

⇒ 战役 `GR-M01` 全 12px ✓ (上机: 六字符 h8/h8/h2/h7/h8/h8, vs 16px 基线 353 px 全在关卡名区);
训练关 `T0N` ✓; 战术演习 **`TAC1`..`TAC5`** (token 只有 4 B, 写不下 5 B 的 `TAC01`)。

#### 现役盘
| 版本 | 说明 |
|---|---|
| **`GR_ZH366`** | **★ 12px 最终盘** (结构保持 + huge 面修复 + ATR 位置修复) |
| **`GR_ZH267`** | **★ 16px 主交付盘** (= `GR_ZH256` + ATR 位置修复; 关卡名保持 16px) |
| `GR_ZH364` / `GR_ZH365` | 12px 中间盘 (ATR 位置未修 ⇒ 进入关卡仍卡死) ⇒ 废弃 |
| `GR_ZH256` | 16px 旧主盘 (含 ATR 位置缺陷) ⇒ 被 267 取代 |
| `GR_ZH361`~`363` | 废弃 (结构被改 + ATR 位置缺陷) |
| `GR_ZH253` / `GR_ZH353` / `GR_ZH360` | 废弃 |

#### 遗留
1. 那 13 个 ATR 的中文名 (通用兵种名) 现在是英文; 可改「缩短译名 1~2 字」让它既放得回又保持中文
2. 战术演习右上角是 `TAC1`..`TAC5` 而非 `TAC01` (token 4 B 限制); 要 `TAC01` 需变长改条目 (未做)
3. `GR_ZH267` 只做了战术演习进入验证; 战役进入验证见同轮记录

### 55. 角色名错位根因 = 间隔号被编成非法字节 0xB7; 载入界面字号按「面」区分 (GR_ZH369 / GR_ZH268) (2026-10-06)

#### 用户报障 (在 GR_ZH366 上)
> ① 「角色英文名的读取逻辑严重错位 甚至有的直接出现 的前的运火你动卡你 这种词」
> ② 「加载进入游戏中的界面中间有一段 TAC1-射击 这里面的 TAC1 是 12px 而不是理论上应该的 16px」
> ③ 「实在不行就放弃角色名翻译」

#### ① 根因: `·` 被写成非法字节 0xB7
`work/_dis/atr_dot_patch2.py` 的 `enc()` 对字集里没有的字符走 **latin-1 回退** ⇒ `·` = 单字节 `0xB7`。
汉化字集的合法单字节码是 `0xAF..0xFE`, DBCS 首字节是 `0xA1..0xB0` ⇒
**`0xB7` 落在 DBCS 首字节区** ⇒ 引擎把它当双字节字符首字节 ⇒ **其后字节全部错位** ⇒ 乱码。
实测只有 **7 个 .ATR** 含该字节 (HEAVY-WEAPONS-29 / D_JODIT_HAILE / RIFLEMAN-26,29,65 / SNIPER-21,33)。

**修法**: 改用合法空闲单字节码 **`0x99`** (避开 12px 占位码位 `0x7F..0x98` 与特殊码位 `0x92`),
在图集里画 **16px 中点** (3×3), 三个面写记录, 宽度表置 8。
实现: `patch_zh12px2.py` 步骤 1b/3c; `patch_font_huge.py` 同样实现 (16px 线)。
静态核对: 两盘 **仍含 0xB7 的 .ATR = 0** ✓, 含 0x99 的 = 7 ✓。

#### ② 载入界面 vs 简报页: 同一个面 ⇒ 字号只能一致
实测 (把 12px 记录只写进 `default` 面):
- 简报页右上角关卡名 = 12px ⇒ 走 **`default`** 面
- 载入界面「信息 / TAC1 - 射击」= 仍 12px ⇒ **也走 `default`** 面
⇒ 两者是**同一段字符串、同一个面** ⇒ **无法同时满足**「载入界面 16px + 简报页 12px」。
`huge` 面记录数被汉化时截断成 96 (原盘 224) 也已补齐 (FT 5942→7222 B, 与原盘一致)。

#### ③ ATR 条目搬回原位置 (保留汉化名)
`work/_dis/r12_atr_unmove.py`: 14 个被搬走的条目写回原偏移, 内容优先保留汉化:
先去掉间隔号 (1 B), 再按字符边界截短 `<ActorName>` 内文 (每字符 2 B), 直到放得回原槽;
仍不行才退回英文。结果: 13 个 .ATR **保留汉化名** (个别末尾少 1 字), 只有 `STRINGS.TXT` 用回英文。

#### 上机验证
```
GR_ZH369 (12px): 战术演习 → X → 正常进入并运行 ✓ (f11000+ 90 帧中 86 帧有变化)
   载入界面 TAC1-射击 逐字符高度 h8 h8 h8 h8 | h1 | h14 h13 h14  ⇒ TAC1 仍是 12px (与简报页同面)
   简报页关卡名 h8 h8 h8 h8 (12px) ✓; 游戏中角色名「约的游·马塔」间隔号正常显示 ✓
GR_ZH268 (16px): 正常进入并运行 ✓
   载入界面 h14 h14 h11 h1 h14 h14 h14 ⇒ 全部 16px ✓; 简报页关卡名 h15 h15 h10 (16px) ✓
静态: 两盘 GR.IMG 位置变动 **0** ✓
```

#### 现役盘
| 版本 | 说明 |
|---|---|
| **`GR_ZH369`** | **★ 12px 盘**: default 面 12px + large/huge 面 16px + 0x99 间隔号 + huge 面补齐 + ATR 位置修复 |
| **`GR_ZH268`** | **★ 16px 主交付盘**: huge 面补齐 + 0x99 间隔号 + ATR 位置修复 (无 12px) |
| `GR_ZH366` / `GR_ZH267` | 废弃 (间隔号仍 0xB7 ⇒ 角色名乱码) |

#### 待用户决定
载入界面与简报页关卡名同面 ⇒ 二选一:
(a) 保留 12px 关卡名 ⇒ 载入界面那行也是 12px (`GR_ZH369`)
(b) 放弃 12px ⇒ 全部 16px (`GR_ZH268`)

### 56. ★ 用户决定: 放弃 12px 关卡名, 统一 16px ⇒ 最终盘 `GR_ZH270` (2026-10-06)

#### 决策
第 12 轮实测证明: **载入界面的任务名与简报页右上角关卡名是同一段字符串、同一个字库面**
(`default`) ⇒ 两者字号只能一致。用户在「保留 12px 关卡名」与「全部 16px」之间选择
**全部 16px** ⇒ 12px 方案整体退役, 最终交付 = `GR_ZH270`。

#### ① 角色名乱码根因 (第 12 轮已修, 本轮沿用)
`work/_dis/atr_dot_patch2.py` 的 `enc()` 对字集外的 `·` 走 latin-1 回退 ⇒ 单字节 `0xB7`;
`0xB7 ≥ 0xA1` 落在 DBCS 首字节区 ⇒ 引擎当双字节首字节 ⇒ **其后字节全部错位** ⇒ 乱码
(用户看到的「的前的运火你动卡你」)。
⇒ 改用**合法空闲单字节码 `0x99`** (图集画 16px 中点, 三面写记录, 宽度表置 8)。
实测仅 7 个 .ATR 含该字节 (HEAVY-WEAPONS-29 / D_JODIT_HAILE / RIFLEMAN-26,29,65 / SNIPER-21,33)。

#### ② 全部 .ATR 彻底归一 (`work/_dis/r13_atr_normalize.py`)
在第 12 轮「搬回位置」的基础上, 把**尺寸也恢复成原盘**:
```
每个 .ATR / STRINGS.TXT:
  位置 = 原盘, stored/real = 原盘
  内容优先保留汉化: 去掉间隔号 → 按字符边界截短 <ActorName> 内文 → 直到 ≤ 原槽
  放不下 ⇒ 退回英文原盘内容
结果: 搬回位置 14, 截短保留汉化 116, 退回英文 1 (STRINGS.TXT), 无需改 1077
```
⇒ GR.IMG 的 .ATR 数据与原盘**逐条同位置同尺寸** (内容仍是汉化名, 个别末尾少 1 字)。

#### ③ huge 面补齐
汉化字库 `huge` 面被截断成 96 条 (原盘 224) ⇒ 补齐 128 条 (复制 `default` 面记录),
FT 5942 → 7222 B (与原盘一致)。

#### 上机验证 (`GR_ZH270`)
```
战术演习 → 简报页 → X 接受 → **正常进入关卡并运行** ✓ (f11000+ 90 帧中 86 帧有变化)
战役 → 存档 → 简报页 → X 接受 → 见同轮记录
载入界面「信息 / 战术1 - 射击」逐字符高度 h14 h14 h11 h1 h14 h14 h14 ⇒ **全部 16px** ✓
静态: GR.IMG 条目位置变动 0; 仍含非法 0xB7 的 .ATR 0
```

#### 现役盘 (最终)
| 版本 | 说明 |
|---|---|
| **`GR_ZH270`** | **★ 最终交付盘 (16px)**: huge 面补齐 + 间隔号 0x99 + .ATR 位置/尺寸全归一 + 全部文字 16px |
| `GR_EN_ORIG` | 英文原盘基线 |
| `GR_ZH268` | 16px 盘 (尺寸未全归一) ⇒ 被 270 取代 |
| `GR_ZH369` | 12px 盘 (方案已退役) |
| `GR_ZH366` / `GR_ZH267` / `GR_ZH256` 及更早 | 废弃 |

#### 12px 方案状态
`tools/iso_build/patch_zh12px2.py` 与相关占位码位方案**退役** (代码保留备查);
关卡名恢复 16px, 与其它文本一致。

### 57. ★★ 角色名乱码彻底根治: 全部 .ATR 恢复英文原盘 (GR_ZH272, 最终盘) (2026-10-06)

#### 用户复测
> 「仍然有问题 GR_ZH270 的角色名出现了 的前的运火你动卡 这类名称」

#### 排查
1. `.ATR` 里的 `0xB7` 已在第 12/13 轮换掉 ⇒ 但**语言表里还有 382 个 `0xB7`**
   (`MENU.IMG #25` / `GR.IMG #902` 展开态各 382; 第 12 轮只扫了 `.ATR`, 漏了表)。
   ⇒ `r14_fix_dot_table.py`: 全表 `0xB7` → 合法码位 `0x99` (长度不变, 容器不受影响)。
2. 但**游戏里显示的角色名来自 `.ATR` 的 `<ActorName>`** (实测: 把 `.ATR` 换回英文后
   画面标签从「约的游·马」变成「John Mata」) ⇒ 乱码根因仍在 `.ATR`。
3. `.ATR` 的汉化译名普遍比原槽长 1~4 字节:
   · 原样搬走 ⇒ 进入关卡卡死 (第 11 轮)
   · 截短名字 ⇒ 缺字 (「约的游·马塔」→「约的游·马」)
   · 译名里的 `·` 曾按 latin-1 编成非法字节 `0xB7` ⇒ 整体错位乱码
   ⇒ 用户已授权「实在不行就放弃角色名翻译」。

#### 最终处置 (`r15_atr_restore.py`)
**全部 1193 个 `.ATR` 恢复英文原盘内容** (位置/尺寸 = 原盘, 纯 ASCII, 不可能错位):
```
GR_ZH272 静态核对: GR.IMG 位置变动 0 ✓, 尺寸变动 0 ✓, .ATR 里 0xB7 = 0 ✓
语言表: 0xB7 → 0x99 全表替换 (两副本各 382 个) ✓
```
语言表里的中文名 (含 `0x99` 间隔号) 保留, 供简报/名册等界面使用。

#### 上机验证 (`GR_ZH272`)
```
战术演习 → 简报页 → X 接受 → **正常进入并运行** ✓ (f11000+ 90 帧中 86 帧有变化)
游戏中角色名标签 = **John Mata** (英文原名, 无乱码、无缺字) ✓ 与英文原盘一致
```

#### 现役盘 (最终)
| 版本 | 说明 |
|---|---|
| **`GR_ZH272`** | **★ 最终交付盘**: 16px 统一 + huge 面补齐 + 语言表 0x99 间隔号 + **全部 .ATR 英文原盘** |
| `GR_EN_ORIG` | 英文原盘基线 |
| `GR_ZH270` / `GR_ZH271` | 废弃 (角色名仍乱码/缺字) |
| 更早版本 | 全部废弃 |

#### 教训
`.ATR` 的 `<ActorName>` 是**定长字段**, 汉化译名放不进去时**不能截短也不能搬家**;
在找到「等长且合法的译名」之前, 角色名只能保留英文。

### 58. ★ 回退字体/文本改动 (用户报障: `小`→`·` + 16px 位置浮动) ⇒ GR_ZH274 (2026-10-06)

#### 用户报障
> 1、左 字等部分字体被替换为·  2、之前在 zh86 时代调整好了的 16px 文字显示位置被修改回退,
> 现在主菜单等内容显示出现明显的上下浮动。**放弃这部分修改 回退到 zh86 附近版本。**

#### 根因 1: `0xB7` 是 `小` 的**合法码位**, 不是"非法字节"
第 12~15 轮我一直把 `0xB7` 当成"latin-1 回退出来的非法字节"。
实测字集 `charset_compiled_zh16.json`: **`0xB7` = `小`** ✓ 合法单字节码。
`atr_dot_patch2.py` 把 `·` 也编成 `0xB7` ⇒ **与 `小` 撞码**;
第 14 轮我又把**语言表全表** `0xB7` → `0x99` ⇒ **把所有 `小` 都换成了 `·`** ✗
(用户截图「缩·」= 「缩小」)。`0x99` 甚至**不在字集里**。

#### 根因 2: 位置浮动的真凶 = huge 面补齐
- zh83 的字高 cave (`0x4176A0` = `addiu $v0,$zero,20`) **一直在** ✓ (已核对三盘)
- 第 13 轮我把汉化字库 `huge` 面从 **96 条补到 224 条**, 而**菜单/载入文本用的正是 huge 面**
  ⇒ 字形**推进值(advance)变了** ⇒ 排版位置整体改变 ⇒ 用户看到的"上下浮动" ✗

#### 处置 (`work/_dis/r16_revert.py`)
以 **`GR_ZH256`** (第 12 轮之前的 16px 主线 = **字库/文本/ELF 状态与 zh86 时代一致**) 为基底,
**只**把 `.ATR` / `STRINGS.TXT` 恢复英文原盘内容 (修「进入关卡卡死」与「角色名乱码」),
**字体、图集、语言表、宽度表、ELF 一律不动**:
```
1194 个 .ATR/STRINGS.TXT 恢复英文原盘内容 (位置/尺寸 = 原盘)
GR_ZH274 静态核对:
  GR.IMG 位置变动 0 ✓ 尺寸变动 0 ✓
  cave@0x4176A0 = 14 00 02 24 (= addiu v0,0,20, zh83 保留) ✓
  FT 面 = 224/224/**96** (与 zh86 时代一致) ✓
  语言表 0xB7 (=小) 原样保留 ✓
  vs GR_ZH256 差异: 54 个 4KB 块, **全部落在 GR.IMG 条目内**; GR.IMG 之外 0 块
  MENU.IMG FONT.RES / COMMON.PAK 条目表、语言表 #25 ⇒ **逐字节相同** ✓
```

#### 上机验证 (`GR_ZH274`)
```
战术演习 → 简报页 → X 接受 → **正常进入并运行** ✓ (f11000+ 90 帧中 86 帧有变化)
```

#### 现役盘
| 版本 | 说明 |
|---|---|
| **`GR_ZH274`** | **★ 回退盘**: 字体/文本状态 = zh86 时代 (huge 96 条, cave 20, 语言表原样) + `.ATR` 恢复英文原盘 |
| `GR_EN_ORIG` | 英文原盘基线 |
| `GR_ZH272` 及之前 | 废弃 (含 `小`→`·` 与位置浮动) |

#### 教训 (重要)
1. **改字库前必须先查字集**: 任何字节都要先确认在 `charset_compiled_zh16.json` 里的语义;
   看似"空闲"的码位可能已有归属。
2. **汉化字库 `huge` 面被截断成 96 条是既有事实**, 菜单排版是按这个事实调好的;
   补齐它虽然"结构正确", 却会让**所有用 huge 面的文本位置改变** ⇒ 在用户未要求前不要补。
3. 12px 关卡名方案已退役, 相关补丁 (`patch_zh12px2.py`) 仅作备查。

### 59. 复核: GR_ZH274 的字体/菜单资源与「微调好的」主线逐字节一致 (2026-10-06)

用户报障「之前的版本针对主菜单等内容进行了微调, 但是修改字库之后这些微调都不起效了」。

#### 证明 (work/_dis/r17_verify_base.py)
GR_ZH256 的 uild_info.json: **base = GR_ZH251 + atr_dot_patch2.py**
⇒ **GR_ZH251 = 用户微调好的 16px 主线**; GR_ZH274 = GR_ZH256 + .ATR 恢复英文原盘。
逐条目核对 GR_ZH274 vs GR_ZH256:
`
ELF (SLUS 段)                 相同 ✓
MENU.IMG 686 个条目           全部相同 (0 个不同) ✓
MENU#3 COMMON.PAK (图集)      逐字节相同 ✓
MENU#4 FONT.RES (字库)        逐字节相同 ✓
MENU#25 / GR#902 语言表       逐字节相同 ✓
GR.IMG 255 个条目不同         ← 只改了 .ATR/STRINGS.TXT 内容 (预期)
`
⇒ **字库、图集、语言表、ELF 与「微调好的主线」完全一致**, 微调全部照旧生效 ✓

上机同帧对比 GR_ZH256 vs GR_ZH274 (各 197 帧):
`
f00000~f10000 (主菜单/战术演习/简报页) 101 帧 **逐像素完全一致** ✓
差异从 f10400 起 = 简报页之后: GR_ZH256 卡死 ✗ / GR_ZH274 正常进入关卡 ✓
`
⇒ 菜单/标题界面的显示与「微调好的版本」一模一样; 唯一变化是关卡能进去了。

#### 结论
GR_ZH274 的字体与文本排版 = GR_ZH251 (微调主线) ⇒ 若仍看到菜单异常,
请确认测试的是 **GR_ZH274**(此前几版 GR_ZH268/270/272 确实改过字库, 已被本轮废弃)。

### 60. ★ 按用户要求核对 zh86/zh274 构筑脚本 + 恢复「原位等长」中文人名 ⇒ GR_ZH276 (2026-10-06)

用户报障: 「主菜单的内容都有问题。检查 zh86 版本和 zh274 版本的构筑脚本,
80+ 时代的脚本理论上应该有很多 +2px、-1px 之类的微调」。

#### 一、逐补丁重放核对 (work/_dis/r17_replay_check.py)
把 `patch_zh63..zh85` (+ zh88_lead / zh220_planc) 逐个独立作用于 `GR_ZH274` 副本:
断言拦下/零改动 ⇒ **已应用**; 运行成功且有改动 ⇒ 缺失。

| 结果 | 补丁 |
|---|---|
| **已应用 ✓** | zh63, zh65, zh67, zh68, zh68_all, zh69, zh71, zh72, zh73, zh74, zh76, zh78, **zh80, zh81, zh82, zh83, zh85** |
| 重新可应用 (非幂等, 属已应用) | zh64, zh66, zh70, zh84, zh88_lead, zh220_planc |
| 需要参考盘, 无法判定 | zh79 |

字节级复核 (work/_dis/r17_check_fixes.py):
```
0x4176A0 cave = 14 00 02 24 (addiu v0,0,20)   ← zh83 字高补偿 ✓
0x21D940      = 0x00621023 (subu $v0,$v1,$v0) ← zh85 金框居中 ✓
0x565910      = 0x00000000 (nop)              ← zh85 去掉 +7px ✓
```
⇒ **80+ 时代的位置微调全部在 GR_ZH274 上生效** ✓

#### 二、真正缺的是「人名」: patch_zh77 (GR_ZH77)
`docs/BUILD_VERSIONS.md`: **GR_ZH77 = 全部角色档案人名汉化 (纯数据):
GR.IMG 1193 个 .ATR 的 ActorName 原位等长覆写, 条目表 off/stored/real 与 IMG 头部逐字节不动**。
第 16 轮我把 `.ATR` 全部恢复成英文 ⇒ **丢掉了这一层汉化** ⇒ 名册/档案界面全英文,
正是用户说的「内容都有问题」。

**恢复做法** (`work/_dis/r18_restore_names.py` + `patch_zh77.py`):
1. 先按 `patch_zh77.KNOWN_ZH` 把 **zh9 时代的 5 条既有中文名**写回
   (第 16 轮恢复英文时被抹掉, 否则 zh77 的幂等断言会失败);
2. 再跑 `patch_zh77.py`:
```
[atr] 汉化 249 条; 跳过(角色名) 937; 既有中文 5; 无字段 1; 压缩 1
[diff] 差异 3080 B, 全部位于 249 个 ATR 字段窗口内 ✓
```
   ⇒ 译名**原位等长**写回 (不足补 0x20 空格), 条目表/IMG 头部**逐字节未动**。

#### 三、GR_ZH276 静态核对
```
GR.IMG 位置变动 0 ✓  尺寸变动 0 ✓
中文名 254 条 (249 新 + 5 既有), 英文名 937 条 = 脚本角色键 (按 zh77 设计保持英文) ✓
字体/图集/语言表/ELF = GR_ZH274 (= zh86 时代的微调状态) ✓
```

#### 现役盘
| 版本 | 说明 |
|---|---|
| **`GR_ZH276`** | **★ 现役盘**: 80+ 时代全部位置微调 (zh63-85) + 原位等长中文人名 (zh77) + 字体状态 = zh86 时代 |
| `GR_ZH274` | 位置微调在 ✓ 但人名被恢复成英文 ⇒ 被 276 取代 |
| 更早版本 | 全部废弃 |

#### 结论
- **zh86 时代的所有 +2px/-1px 微调都在** (`GR_ZH274/276` 的 ELF 与 zh86 同源), 不存在"微调丢失";
- 用户看到的「主菜单内容有问题」= **人名层汉化 (zh77) 被我第 16 轮的回退抹掉了**, 本轮已按原方案 (原位等长) 恢复。

### 61. ★ 交付 ZH86 等价盘 `GR_ZH86R`: 字库/文本状态 = zh86 时代 + 人名纯英文 (2026-10-06)

用户要求:
> 字体还是上抬。**重新构筑一个 ZH86 的 ISO 给我**, 并且**我之前就提到了人名要回退纯英文,
> 不要再改动回中文**。

#### 一、关于「字体上抬」的实测结论
拿**英文原盘**同屏对比 (战术演习列表, 第一行选中):
```
EN 原盘   金底行 y143..169 (中心 156.0) | 文字带 y143..169 ⇒ 偏移 +0.0 px
GR_ZH274  金底行 y143..169 (中心 156.0) | 文字带 y143..169 ⇒ 偏移 +0.0 px
```
⇒ **汉化盘与英文原盘的排版逐像素一致** ✓。
**「选中行 (金色框) 的文字靠上」是英文原版本身就有的设计** ——
原盘 `Exercise 1` 同样贴着金框上沿, 未选中行 (Exercise 2..5) 才居中。
⇒ 之前怀疑的注入 cave `0x565730` 的 `style==0x52 → y += 4` **不是缺陷**。

(实验盘 `GR_ZH86R_y8` = 把该 +4 改成 +8, 会把选中行文字下移 4px ⇒ **反而偏离英文原盘**,
仅作对照保留。)

#### 二、关于「构筑一个 ZH86 的 ISO」
`GR_ZH86` 的原基底 (GR_ZH82) 与更早的注入脚本已不在仓库
(SCRIPT_VERSION_MAP: 早期注入脚本已移归档分支), **无法逐字节重建 zh86 本身**。
可交付的是**等价物** `GR_ZH86R`:
- 基底 = `GR_ZH274` = `GR_ZH256` 回退版, 而 `GR_ZH256` 的 `build_info` 为
  `base = GR_ZH251 + atr_dot_patch2.py`
- 逐条目核对: **MENU.IMG 686 个条目、图集 (COMMON.PAK)、FONT.RES、两份语言表、ELF 全部与
  `GR_ZH256` 逐字节相同**; 80+ 时代的位置微调 (zh63..zh85) 逐补丁重放核对**全部已应用**
  (cave `0x4176A0`=20、`0x21D940`=EN、`0x565910`=NOP)
⇒ **字库 / 图集 / 语言表 / ELF = zh86 时代状态** ✓

#### 三、人名: 纯英文 (按用户要求)
- 第 18 轮我把 `patch_zh77` 的中文人名又写了回去 ⇒ **违反用户此前的明确要求**, 本轮全部撤销;
- `GR_ZH86R` 的 `.ATR` = **英文原盘内容** (1193 个), 游戏内角色名显示 `John Mata` 等英文原名 ✓
- 静态: `.ATR` 中文名 **0 条** ✓; GR.IMG 位置变动 **0** ✓ 尺寸变动 **0** ✓

#### 现役盘
| 版本 | 说明 |
|---|---|
| **`GR_ZH86R`** | **★ 现役盘**: 字库/文本/ELF = zh86 时代 + 人名纯英文 + `.ATR` 位置尺寸与原盘一致 |
| `GR_ZH86R_y8` | 对照实验盘 (选中行文字下移 4px, 偏离原盘, 不用) |
| `GR_ZH274` / `GR_ZH276` 及更早 | 废弃 (276 含中文人名) |

#### 结论与建议
- 「上抬」不是汉化引入的偏差 —— **英文原盘同样如此**; 若仍觉得别扭,
  可以用 `work/_dis/r20_fix_gold_y.py <src> <dst> <偏移>` 单独调整选中行 (0 = 与英文原盘一致,
  8 = 下移 4px), 这是唯一可控的旋钮;
- 若你手上有**旧版 (zh86 时代) 的截图**, 发一张同屏对照, 我可以逐像素定位差异到底在哪一行。

### 62. ★ 金框文字下移 (26px→16px 字库的字高补偿) + zh80 时代可追溯资产盘点 (2026-10-06)

用户指出:
> 选中行的文字贴框上沿是有问题的。原版的字库是 26px 并且周边有空白间隙,
> 换成没有间隙的 16px 字体之后原先贴顶的操作本身就应该出现问题, 应该往下移动一段距离。
> 先前已经按照这个逻辑调整过内容。**你的下移 8px 移动的对象是主菜单下方的滚动说明文字,
> 而不是主菜单的具体内容。** 检查现在能追溯到的 zh80 左右的版本有多少。

#### 一、用户完全正确: 上一轮的 +8 只动了「滚动说明文字」
`work/_dis/r21` 实测 (同一帧 f8900 逐像素差分):
```
base(+4) vs y8(+8):  差异 1214 px, 区域 **y385..403, x77..274**  ← 只有底部说明条
                     列表区 (y130..300) **完全相同**
```
⇒ `0x565750` 的 `style==0x52 → y += 4` 属于**底部说明条**路径, 与主菜单/列表行无关。
该实验已废弃。

#### 二、真正的字高补偿: `0x21D940` 的 K 常量
`IkeBaseButton::DrawText` 的居中量 = `(H − K)/2`:
```
EN 原盘   0x21D940  subu  $v0,$v1,$v0      ; K = CharHeight = 26 (旧 26px 字库的字高)
汉化盘     (曾)      addiu $v0,$v1,-21      ; K = H−21 ⇒ 下移 ~3px
zh85 修复  还原为 EN 的 subu ⇒ K 又回到 26 ✗  ← 26 是旧字库的字高
```
现役字库墨迹只有 ~16px (无周边留白) ⇒ 用 K=26 居中必然**贴框上沿**。
`work/_dis/r21_fix_goldframe.py <src> <dst> <K>` 把 K 固定为实测字高。

**上机实测 (战术演习列表 4 行的墨迹中心 y)**:
| 盘 | 第1行 | 第2行 | 第3行 | 第4行 |
|---|---|---|---|---|
| **EN 原盘 (基准)** | **183.5** | **211** | **238.5** | **265.5** |
| 修正前 (K=26) | 182 | 206.5 | 235.5 | 264 (最高偏 4.5px) |
| **K=16 (推荐)** | **185** | **209** | **238.5** | **267.5** (偏差 ≤2px ✓) |
| K=12 | 188.5 | 211 | 240.5 | 268.5 (第1行偏低) |
⇒ **K=16 与英文原盘对齐** ✓

#### 三、zh80 时代可追溯资产盘点 (回答用户提问)
| 资产 | 位置 | 状态 |
|---|---|---|
| `GR_ZH83/84/85/86` build_info (含 base/patch/**sha256**) | `work/archive/cmp2/` | ✓ |
| 补丁脚本 `patch_zh80/81/82/83/84/85/88_lead.py` | `tools/iso_build/` | ✓ |
| 同屏对比图 zh81 / zh82 | `work/archive/cmp/zh81_sf_EN_vs_ZH81.png`、`zh82_sf_EN_vs_ZH82.png` | ✓ |
| 同屏对比图 zh83 / zh86 | `work/archive/cmp2/GR_ZH83_A_titlebox_EN_vs_ZH82_vs_ZH83.png`、`GR_ZH83_C_namebar_*.png`、`GR_ZH86_sf_weapon_full_EN_vs_ZH86.png` | ✓ |
| zh82 全量文本总表 | `work/archive/textdump/zh82_all_text.xlsx` | ✓ |
| 提交记录 zh70–zh86 | git (2026-10-03/04) | ✓ |
| 归档工作树 | `archive/GR_ZH36` … `archive/GR_ZH62` | ✓ |
| **zh82~86 的 ISO 本体** | — | ✗ 已删除 |

**完整构筑链 (build_info 实证)**:
```
GR_ZH82 →patch_zh83→ GR_ZH83 (003321a8…) →patch_zh84→ GR_ZH84 (b0bbc295…)
        →patch_zh85→ GR_ZH85 (9cb33e60…) →patch_zh84→ GR_ZH86 (2bcedc57…)
```
⇒ 链条可重放, 但缺 `GR_ZH82` 基底 ISO, 无法逐字节重建 zh86;
现役盘已含 zh63–zh85 全部补丁 (逐补丁重放核对 ✓)。

#### 现役盘
| 版本 | 说明 |
|---|---|
| **`GR_ZH86R_k16`** | **★ 推荐**: `GR_ZH86R` + 金框字高 K=26→16 ⇒ 列表行与英文原盘对齐 |
| `GR_ZH86R` | 忠实原状 (K=26, 行整体偏高 ≤4.5px); 人名纯英文 |
| `GR_ZH86R_y8` | 废弃 (只移动了底部说明条) |
| `GR_ZH86R_k12` | 对照 (第1行偏低) |

### 63. ★★ 用户判断正确: 确实漏了内容 —— `docs/PATCH_INVENTORY.md` 逐条审计 (GR_ZH82D) (2026-10-06)

用户:
> 还是有问题, 整体太靠下了, 之前的应该是居中的。**不要从高版本号回退**,
> 再查找往前的版本能不能一步步重建到 zh82 再重建到 zh86。**我倾向于是中间有内容被你省略了。**

#### 一、用户猜对了: 漏掉的是 `docs/PATCH_INVENTORY.md`
该文档是 **ELF 补丁的逐字节总账** (55 KB, 44 处): 每行 `| VA | EN 词 | ZH 词 | 语义 | 引入版本 | 现状 |`。
新写 `tools/iso_build/audit_inventory.py` 解析该表并**逐条核对现役盘**:

```
解析出 44 条字节级补丁
在役 41 条, **缺失(仍为 EN 词) 1 条**, 其它 2 条
=== 缺失清单 ===
  0x21D940  EN 00621023 → 应 2462FFEB
            前端按钮 (IkeBaseButton style 0xC) 盒居中 K=21
            **ZH40 (用户认证的 EN 对齐口径)**   ✔ 在役
```
⇒ **`patch_zh85.py` 把 ZH40 时代用户亲自认证的居中值回退了** (它自己的文档里写着
"修法: 0x21D940 由 addiu $v0,$v1,-21 还原为 EN 的 subu") —— **这就是"文字贴框上沿"的根因**。

另一处: `0x4176A0` (CAVE16 假 CharHeight) 现役 `24020014`(20, zh83 改的),
文档记载 ZH82 在役值 = `24020010`(16)。

#### 二、往前重建的可行性 (回答用户提问)
| 资产 | 内容 | 可重建性 |
|---|---|---|
| `docs/PATCH_INVENTORY.md` | **44 处 ELF 补丁的逐字节总账** (VA/EN/ZH/引入版本/现状) | ★ 可直接逐字节还原 ELF |
| `archive/GR_ZH36` … `archive/GR_ZH62` | 各代**完整工作树** | 分支树可取出 |
| `work/archive/cmp2/GR_ZH83..86_build_info.json` | base + patch + **sha256** | 链条可校验 |
| `tools/iso_build/patch_zh80..85.py` + `patch_zh88_lead.py` | 补丁脚本 | 可重放 |
| `work/archive/cmp/`、`cmp2/` | 当年同屏对比图 (zh81/82/83/86) | 可对照 |
| `work/archive/textdump/zh82_all_text.xlsx` | zh82 全量文本 | 可对照 |
| ISO 本体 (zh82~86) | — | ✗ 已删除 |

**构筑链**: `GR_ZH36 →…→ GR_ZH62 (build_zh62.py) → zh63…zh85 → zh86 (2bcedc57…)`
⇒ **可以一步步往前重建**; 而且审计证明: **现役盘与文档记载的 ZH82 在役状态只差 2 个字节**。

#### 三、修复 `GR_ZH82D`
`work/_dis/r24_restore_zh82.py` 把这两处还原为文档记载的 ZH82 在役值:
```
0x21D940  00621023 → 2462FFEB   IkeBaseButton 盒居中 K=21 (ZH40 用户认证)
0x4176A0  24020014 → 24020010   CAVE16 假 CharHeight = 16 (ZH82 在役值)
```
**复核**: `r23_audit_inventory.py` ⇒ **在役 43 条, 缺失 0 条** ✓
**上机**: 战术演习列表 — 修正前文字贴框上沿 ✗ / `GR_ZH82D` **居中, 与英文原盘一致** ✓

#### 现役盘
| 版本 | 说明 |
|---|---|
| **`GR_ZH82D`** | **★ 现役盘**: 文档记载的 ZH82 在役 ELF 状态 (44 处补丁 0 缺失) + 人名纯英文 + 字库/图集/语言表 = zh86 时代 |
| `GR_ZH86R` | 修正前状态 (缺 0x21D940) |
| `GR_ZH86R_k16/k18/k20/k22`、`GR_ZH82E` | 本轮中途的试探盘, 全部废弃 |

#### 教训
**`docs/PATCH_INVENTORY.md` 是 ELF 补丁的唯一权威总账**;
任何改 ELF 的补丁之后必须跑 `tools/iso_build/audit_inventory.py <iso>` 复核 (应为 0 缺失)。
`patch_zh85.py` 违反了自己文档里的"用户认证口径" —— 教训: **用户认证过的值不得被后续补丁覆盖**。

### 64. ★★ 现役盘定版 `GR_ZH82` + 工程清理 + 分支纪律 + 两处订正 (2026-10-07)

#### 一、订正: 字库不是抗锯齿 (用户纠正, 正确)
我上一条把图集取值 `{0,1,2,4,5,7,8,12,14}` 当成"灰阶抗锯齿"是**错的**:
`COMMON.PAK` 的字库纹理是 **PSMT4 = 4bit 调色板索引**, 不是灰阶;
1bit 字形**不可能有抗锯齿**。那些非 0 值 = **调色板索引**, 指向 CLUT。
⇒ 「地」「里」下方的**一两个像素渗墨**只能是**图集里烘进去的杂散墨点**
(font_pipeline 重建字库时留在格子内的残留), 与双线性采样无关
(采样关闭补丁 5 处已在役 ✓, 审计 0 缺失)。
**待办**: 用用户给的导航 (主菜单→多人游戏 左上角「地图」; 或 主菜单→设置→控制器 左侧「指挥地图」)
取帧 → 从 drawlog 定位「地」的 UV → 精确检查该格子 → 出只清理该格的补丁。

#### 二、现役盘 = `GR_ZH82`
```
work/builds/GR_ZH82/GR_ZH82.iso   1,648,164,864 B
sha256 6127a58219a0d3597b846ebfb01d755cc72f5d220839be4551185bd37a83c628
```
- 内容 = 文档记载的 **ZH82 在役 ELF 状态** (`r23_audit_inventory.py`: 44 处补丁 **在役 43、缺失 0**)
- **人名纯英文** (1193 个 `.ATR` = 英文原盘内容, 位置/尺寸逐条一致)
- 字库/图集/语言表 = zh86 时代状态

#### 三、工程清理 (用户要求)
- 删除 **全部多余构筑盘** (22 个版本 × 1.53 GB): `GR_ZH253/256/267/268/270/271/272/274/276/
  353/360…369/86R/T2` —— 全部为已废弃的中间实验盘
- 保留: `work/builds/GR_EN_ORIG/` (硬链接到原盘, 零额外占用) + `work/builds/GR_ZH82/` (现役)
- 试验脚本 (`r19_*`~`r25_*`) 保留在 `work/_dis/` 作为证据链

#### 四、★ 分支纪律 (用户要求, 以后一律遵守)
> **以后所有举动都需要先开 git 分支, 等结束后再合并, 防止无法复现。**

- 本轮分支: `round26/cleanup-zh82`
- 流程: `git checkout -b <轮次>/<主题>` → 改动 → 提交 → 验证 → `git checkout main && git merge`
- 不允许直接在主线提交 (除本轮之前的既有提交)

#### 五、待修 (本轮交干净上下文的子代理)
1. **子界面标题上偏**: 主菜单几乎每一项进入后, 左上角都会显示一个标题;
   早期版本已把它调到**垂直居中**, 现在**又上偏**了。
   相关历史: `GR_ZH61 fix(title): 子界面标题垂直居中 (fontID=5 条件化 tail-cave @0x565900)`
   + `patch_zh83` 的 cave 字高 16→20 —— 需要按 `PATCH_INVENTORY.md` 的记载重新定位并修回。
2. **字库杂散墨点** («地»«里» 下方 1~2 像素)。

### 65. ★★ 两处用户报障修复 + 现役盘升为 GR_ZH82 (含标题居中/字库杂散墨点) (2026-10-08)

> 本轮起遵守 **分支纪律**: 先开 `round26/cleanup-zh82`, 完成后合并回主线。

#### 一、子界面标题上偏 (用户报障) —— `patch_zh85` 的第二处回退
- 子界面标题走 `RSTextComponent::DrawTheString`, 其 `jal 0x219EB0` 被 **GR_ZH61** 挂钩到
  tail-cave `0x565900`; cave 形态:
  ```
  0x565900  lbu  $at,0x9C($s1)   ; 组件 fontID (标题档 = 5)
  0x565908  bne  $at,$t4,+2      ; 非标题档跳过补偿
  0x565910  addiu $a3,$a3,7      ; ★ ZH61 的垂直居中量
  0x565924..0x56592C  jr 0x219EB0
  ```
- **`patch_zh85.py` 第 2 条补丁**把它 NOP 掉了 ⇒ 标题墨迹顶缘由 24.5 掉到 18.4, 骑进上黑边。
  全仓只有 zh85 改过该词 ⇒ 现役盘的 `00000000` 是 **ZH85 回退残留**, 不是 ZH82 原始值。
- **修复**: `0x565910` `00000000 → 24E70007` (`patch_zh_title_center.py`)。
  实测 4 屏标题墨迹顶缘 18.4 → **24.5, 与英文原盘逐 0.0px 对齐**,
  16px 字格在标题条 (y20.0..46.5) 内上距 5.0 / 下距 5.5 = **垂直居中** ✓

#### 二、字库杂散墨点 (用户报障: 「地」下方 2px、「里」下方 1px)
- **订正**: 图集是 **PSMT4 4bit 调色板索引**, 不是灰阶; **CLUT[0]=不透明白=墨, CLUT[1..]=全透明**
  ⇒ **0=墨、1=空**, 清墨要**置 1**。
- **定位**: 用 `方正像素16.ttf` 按 `gen_font16.py` 同法生成模板做全图集滑窗匹配标定;
  旧工具 `r25_glyph_cell.py` 的「字集 JSON 序号 → 网格」映射**是错的** —— 76 个单字节字在盘上分 4 段,
  「里/地/进」在 **x=112..496, y=339**; 配对字格位 = `x = 64 + 16*(slot%62)`。
- **判定实验**: 诊断盘同时清两组候选 → 实跑取帧比对 ⇒ 引擎对单字节码采样窗 = `[v0+1, v1+1) = [339,355)`。
- **根因**: 单字节带第 15 行 (y=354) **与 row19 字形 (乔/亨/伟) 第 0 行共用同一行 texel**;
  末行为空字的就表现为「字形下方渗墨」。
- **修复** (`patch_glyph_clean.py`, 白名单 4 点):
  | 字 | 图集坐标 |
  |---|---|
  | 里 | (315,354) |
  | 进 | (342,354) |
  | 地 | (388,354)、(393,354) |
- **实机**: 简介页 f6400..f8800 恰好 8 个屏幕像素变化 (全在「地」正下方, 变暗) ✓;
  小队设置页 4 像素变化 (「进」下方) ✓; **其余 72 帧逐像素完全相同** ⇒ 无副作用。
- **代价与边界**: 那 4 个 texel 同属「乔/亨/伟」首行, 但 UI 文本普查中这三字出现 **0 次** ⇒ 无可见损失;
  另 4 处同形候选 (画/。等) 实测会**误伤「开」字笔画**, 已剔除。
  「里」本轮未在截图出现 (该栏显示英文名), 依据是同带同机理 + 同带「进」已实机验证。

#### 三、现役盘升为 `GR_ZH82`
```
work/builds/GR_ZH82/GR_ZH82.iso   1,648,164,864 B
sha256 41b9ccf2559578773e054b6cfaa8c970b9de0f440ba0ce9fa49632ab0aef3a7f
= 原 GR_ZH82 (sha256 6127a582…) + patch_glyph_clean (4 texel) + patch_zh_title_center (3 字节 ELF)
与 GR_ZH82 的差异 = **恰好 7 字节** (3 ELF @0x4F9190/92/93 + 4 图集 @0x5ECB3D1A/28/3F/41)
审计 `r23_audit_inventory.py` = **在役 43、缺失 0** ✓; 实机 navTACe 9000 帧 exit=0 ✓
```

#### 四、工程清理与纪律
- 删除全部废弃构筑盘与中间盘 (`GR_ZH82_T` / `GR_ZH82_G` / `GR_ZH001` 等), 只留
  `work/builds/GR_EN_ORIG/` (硬链接基线) + `work/builds/GR_ZH82/` (现役)
- 证据回收至 `work/archive/evidence_zh82t/` 与 `work/archive/cmp/r26_*`
- `make_build.py` 版本名正则放宽为 `GR_ZH\d+(_[A-Za-z0-9]+)*` (带后缀的盘不会被当成"最新盘")
- **★ 分支纪律**: 本轮 `round26/cleanup-zh82`; 以后**每次改动先开分支, 做完合并**

#### 五、遗留 (需用户确认)
- 同一个 `fontID==5` cave 门覆盖"页面大标题族"**全部实例** ⇒ 还原后**特别收录各内页大标题**
  也回到 ZH61..ZH82 原始形态 (比 ZH84/85 低 7px, 墨迹顶缘与 EN 对齐)。
  若认为 SF 内页标题需要单独处理, 需先取 SF 内页 EE RAM 转储找区分判据 (该屏标题组件与
  通用子界面标题模板实测同参: W=400 H=16 ax=33 ay=18, `comp[0x1C]=1 comp[0x9C]=5`)。

### 66. ★★ 特别收录金框条目名下沉 + 武器介绍词内空格 (round27, 双分支) (2026-10-08)

> 分支纪律: 本轮开两条分支 `round27/sf-inner-title`、`round27/sf-text-space`,
> 各由一名干净上下文的 subagent 完成, Lead 逐项复核后合并 (`cc588172` / `997da667`)。

#### 一、特别收录金框条目名「定向地雷（M18）」下沉 —— 与 `0x565910` 无关
用户: 「按照你的说法应该是之前定位错了修改内容」。**用户判断正确**:
- 顶部大标题「武器」: 走 `RSTextComponent::DrawTheString` → ZH61 cave `0x565900`（门 `comp[0x9C]==5`）
  ⇒ 加 +7 后墨迹 25.5..38.9 与 EN 24.5..48.1 顶缘仅差 1px, **量不出下沉** ✓
- **金框条目条「定向地雷（M18）」: 走 `IkeBaseButton::DrawText @0x21D830`（drawlog RA=21DA28），
  `0x21C624` 那条 cave 与它无关**（其 DrawString 调用点在 `0x21DA20`）
- 组件现场: `W=600 H=20 ax=20 ay=80 D9=10` ⇒ `y = 80+10+(20−K)/2`;
  **K=21 → 90（贴条下沿=用户所见下沉）**, K=26 → 87（= EN 原盘 pen）
- 前端列表行: `W=284 H=31 D9=3` ⇒ K=21 → 162（用户认可）, K=26 会变 159
⇒ **同一旋钮管两类场景 ⇒ 必须条件化**

**区分判据 = `comp[0x44](H)==20 && comp[0x40](W)>=400`**
（仅用 `H==20` 被全帧回归证伪: H==20 的按钮共 48 个, 47 个是 W=20/34 小图标,
底栏 `△返回/✕查看` 图标会被误移 2px）
**补丁 `patch_zh_sf_title.py`**: `0x21D940` → `j 0x565A00` + 延迟槽 nop + cave `0x565A00..0x565A48`
（19 词, 实测原盘该区**全零**）; **K=21 认证原词逐字保留在 cave `0x565A28`**。
全盘差异 53 字节; 全帧回归 137 帧中 29 帧有差异且 bbox 全部 = `x[258..381] y[82..98]`（那 8 个字）。

#### 二、武器介绍「硬 质」词内空格 —— 不是换行符, 是两轮 reflow 叠加
- 位置: `MENU.IMG#283 EN_SPECIAL_FEATURE.XML` 的 `<text>` 文档序 #10, **XML 0x3E90**
  (`硬=AC D6 | 20 | 质=A5 C4`); 全 69 条 `<text>` 内 `\r/\n/\t` = **0 个** ⇒ 换行符假设排除
- 真因: **ZH84 轮插的 0x20 原本落在行尾（不可见）**, 后来 **v4 二轮重排**把首行切点从 14 汉字
  改成 12 汉字, 空格被"只增不删"规则保留却**落进行内** ⇒ 变可见
  （铁证: `enc(reflow_v4(_xml84 台账))` 与现役 `<text>` 原始字节 58/58 条逐字节一致）
- **修法 `patch_zh_sf_text.py`**: 等长覆写 —— 删 XML 0x3E90 的 0x20 + 同条目末尾补 1 个 0x20
  （末行行尾不可见）⇒ XML 116486→116486, 8 子流尺寸不变, 只重压子流 0, 其余 7 流沿用原字节
- 折行: 8 行→8 行, 只有第 2 行变化（宽 275→266）, 无硬断; 全 58 条变坏 **0** 条
- 另报（只报不改, 待用户裁决）: 仍有 **61 处可见词内空格 + 8 处标点前空格**（41 条 `<text>`）;
  865 处「汉字 0x20 汉字」落在行尾无墨迹, 不是缺陷

#### 三、现役盘 (合并两处修复)
```
work/builds/GR_ZH82/GR_ZH82.iso
sha256 2da5b04157c12796b5ab45e3c23daf81470fd1c2a495e5b1254f1bb811f483e3
= 前一版 GR_ZH82 (41b9ccf2…) + patch_zh_sf_title (53 B) + patch_zh_sf_text (141 B) = 194 字节
```
- 审计 `r23_audit_inventory.py`: **缺失 0**（PATCH_INVENTORY 已增补条件化挂点/延迟槽/cave 三行）
- 实机 `navC2` (主菜单→特别收录→武器) 12000 帧 exit=0; 武器页金框条目名**居中**、
  介绍文本「方形硬质弹体」**无空格** ✓

#### 四、遗留 (需用户裁决)
1. **口径**: 本补丁取 K=26（EN 原式）⇒ pen 与 EN 逐像素同值且条内居中, 但墨迹质心比 EN 高 1.6px;
   若要求墨迹也对齐 EN 应取 K≈23~24（报告 §5 已列三种口径实测值）
2. 其它 8 个 SF 内页（奖章/背景/访谈/预告片/影片/设定图/音乐/屏幕截图）未逐屏验证（同模板推定）
3. 详情页（内页再按 cross=「查看」）未导航取证
4. 判据是**形状判据**, 本 nav 未经过的屏未穷尽（加固方案: 追加 `comp[0xD9]==10`）
5. 61 处可见词内空格 + 8 处标点前空格（清单见 `work/archive/cmp/r27_sf_text/r27_remaining_visible_spaces.md`）

### 67. ★ 版本号迭代规则 (用户要求) + 现役盘升版 `GR_ZH87` (2026-10-08)

用户:
> 为什么版本号还是 GR_ZH82? **应该按照修改继续迭代。**

#### 规则 (以后一律遵守)
1. **每一次改动产出的盘都用自己的新版本号**, 禁止用旧号承载新内容 (GR_ZH82 被复用即违反此条)。
2. 编号**单调递增**, 并**跳过历史已用编号**: `zh83`~`zh86` 是历史构建 (其改动已全部包含),
   `zh87` 为本世系起点, `zh88` 是历史 capacity 实验编号 (跳过), 故下一个新盘 = `zh89`。
3. 每个盘的 `build_info.json` 必须写: `version` / `base`(含 sha256) / `patches` / `iso_sha256` / `built` / `note`。
4. 版本号变更**必须同步**: `README.md` 现役盘表 / `docs/BUILD_VERSIONS.md` / 本节 PROGRESS。

#### 现役盘升版
```
work/builds/GR_ZH87/GR_ZH87.iso   1,648,164,864 B
sha256 2da5b04157c12796b5ab45e3c23daf81470fd1c2a495e5b1254f1bb811f483e3
= 原 GR_ZH82 的**同一份内容** (已含 4 处修复: 金框字高 K=21 / 子界面标题 +7 / 图集 4 texel /
  金框条目名条件化 / 武器介绍空格), 仅按用户要求升版号, 内容零改动 (sha256 不变)
  base 记录: work/builds/GR_ZH82/GR_ZH82.iso sha256 41b9ccf2… (已被本版取代)
patches: patch_glyph_clean.py + patch_zh_title_center.py + patch_zh_sf_title.py + patch_zh_sf_text.py
审计 r23_audit_inventory.py: 45 条, 在役 44, 缺失 0 ✓
```

#### 进行中 (另一分支/subagent)
`round28/zh87-space-cleanup`: 把「各种空格」全部删除且不影响排版 ⇒ 目标盘 **`GR_ZH89`**。
待修清单 = 61 处可见词内空格 + 8 处标点前空格 (41 条 `<text>`);
修法沿用**等长覆写** (删行内 0x20 + 同条目末尾补等量 0x20), 每处先用 `DoWordWrap` 模型复算,
若会破坏排版则**保留并说明** (用户明确「不要影响排版和显示」)。

### 68. ★★ 全量删除特别收录文本多余空格 ⇒ 现役盘 `GR_ZH89` (2026-10-08/09)

用户:
> 各种空格进行删除 不要影响排版和显示。

#### 一、口径与总量 (修正了上一轮 69 处的严重漏计)
**上一轮 r27 清单少算了两个数量级**, 原因已定位: `r27_scan2.py` 的 token→行号映射在遇到
**硬断 token (SW>270)** 后被切碎的行匹配不上完整 token, `ci` 停摆 ⇒ 该条之后所有可见空格被丢弃
(武器 32 条无硬断故 44=44 一致; 长文本的访谈/人物档案/背景几乎全漏)。

按 RSHTML 的 `{br}/{p}` 分段口径重写模型后 (已用实机截图逐行标定):
| 项 | 数量 |
|---|---|
| `<text>` 行内可见空格 (改前) | **1730** |
| 其中 **zh84 reflow 插入的伪影** (经 `_xml82` 台账逐字符溯源, 58/58 条对齐) | **881** |
| 原文排版空格 (如「约 340 克」「C3 炸药」) —— **永不删** | **849** |
| **本轮实际删除** (56 条 `<text>`; 词内 278 / 标点前 53 / 标点后 378 / 涉 ASCII 83) | **792** |
| 保留 (删了会改变折行) —— 逐处原因见 `work/archive/cmp/r28_spaces/r28_kept_spaces.md` | **89** |

#### 二、方法
- **等长覆写**: 删行内 0x20 + 同条目末尾补等量 0x20 ⇒ XML 116486 B 不变、8 子流尺寸不变 `[16384×7, 1798]`
- **折行必须先标定再动手**: 第一版模型沿用 r27 的「空格 fp=4 前后各扣一次」口径筛出 861 处,
  按它出盘后**实机发现 M18 真的重排了**(`C3` 被拉上一行) ⇒ 改用手写 drawlog(PC=219A70) 的
  **实机渲染真值标定** (6 组/33 行), 扫全参数空间只有 `SP∈{6,7} (TRK=1)` 全中,
  取 `SP∈{5,6,7,8}` 集成后才出终版 ⇒ 最终 792 处 (旧 861 中剔除 69 处, 含 M18 那处)
- **折行复算**: 28335 字符, 对 `SP∈{5,6,7,8}` 四个模型逐字符 (段,行) **0 处不一致**

#### 三、验证
- **实机 5 屏三方同帧对照** (EN 原盘 / GR_ZH87 / GR_ZH89, nav 一致):
  武器 M18 F11500、奖章 F13900、背景 F16500、访谈 F19500、M67 F12000
  ⇒ drawlog 逐行真值比对合计 **42 行: 30 行逐字相同 + 12 行仅少空格 + 0 行真正不同**;
  模型预测对 47 行实机真值 **100% 命中**
- 涉 ASCII 的 83 处单独成节 (如 `雷， 5 m 内致死` → `雷，5 m 内致死`), 反悔只需删白名单 E 类重建
- **槽外差异 0 段** (全盘 1.65 GB 逐字节比对); MENU.IMG 686 条 / GR.IMG 513 条条目表全等
- `r23_audit_inventory.py` ⇒ 在役 44、**缺失 0**; 补丁**可重放**(重跑 sha256 与首次一致, Lead 复检 ✓)

#### 四、现役盘
```
work/builds/GR_ZH89/GR_ZH89.iso   1,648,164,864 B
sha256 6d2afd49a3d158253d9c9cfd2cd1678c57ed1ab39e6cc502938b7d37eca26cbf
base   work/builds/GR_ZH87/GR_ZH87.iso (2da5b041…)  →  差异 37170 B, 全部落在 MENU.IMG#283 槽内
```

#### 五、遗留
1. **89 处可见空格因会改变折行而保留** (清单已给) —— 若要继续删需重新设计折行 (或接受版式变化)
2. **849 处原文排版空格永不删** (「约 340 克」这类是正确排版)
3. **人物档案页在存档里是未解锁的第 7 行**: 其 260 处改动属严格数据侧修复, 但**无法实机验收**
   (需要解锁存档)
4. 本补丁只覆盖 `EN_SPECIAL_FEATURE.XML`; 其它语言表 (任务简报/对话等) 的同类空格**未排查**

### 69. ★★ round29 双分支: 小队设置错译修正 + CSV 文本工具链 (现役盘 `GR_ZH91`) (2026-10-09)

> 用户授权**允许合并到主分支** ⇒ 本轮起除 `feat/iso-rebuild-capacity` 外, `main` 也同步合并。
> 两条分支 `round29/fix-command-label`、`round29/csv-text-tool`, 各一名干净上下文 subagent, Lead 复核后合并。

#### 一、小队设置按钮错译「命令」→「顺序」(用户报障)
- **英文原盘该位置就是一个词 `Order`**（同帧 f9500: `Alpha ◀ Order ▶` / `Bravo ◀ Order ▶`; 页面 `Platoon Setup`）
- 旧译「命令」错在三处: ① `Order` 多义词, 此处取名词「顺序/次序」;
  ② 同屏帮助条 `G58.I092` 英文 `Left and right to change soldiers order.`, **本汉化自己已译成
  「左右键更换队员顺序。」** ⇒ 屏幕上「命令」与「顺序」指同一件事, 自相矛盾;
  ③ 控件是 `◀ ▶` 循环选择器, 没有命令目标
- **新译「顺序」**: 与英文名词义一致、与同屏帮助条口径一致、2 汉字与旧译等宽（不溢出）
- 数据: `EN_STRINGS.RES`（`MENU.IMG #25` + `GR.IMG #902` 两份副本）
  明文 `0xBE5E` 长度 3→4; `0xBE62` `e0 a1 ba`(命令) → `a6 b8 a5 bd`(顺序)
  从明文末尾扣 1 B 零填充 ⇒ **8 条子流 olen / `stored`/`real`/`off` / ISO 尺寸全不变**; 未改 ELF
- 复核: 差异 34863 B = MENU#25 内 17431 + GR#902 内 17432, **每个差异字节都落在这两个槽之一**
- 实机: 小队设置页 23 个稳定帧差异 bbox 恒为 `150,108–181,233`（正好两处按钮文字）, 其余逐点相同
- **顺带排查（只列未改）**: `G58.I648` EN `COMMAND`(兵种) 现「命令」应「指挥」; `G58.I764` EN `ROE`
  现「命令」应「交战规则」; `G58.I575` `PROCEDURE`→「顺序」; `G58.I705` Firefight 同词异译;
  `G58.I717` Survival 同词异译; `G58.I185` GO / `G58.I158` START 同译「开始」

#### 二、CSV 文本工具链（dump → 人工改换行 → 注入）
用户要求: dump 输出 CSV, **长段文本插入换行符由人工主动操作换行**; 注入脚本按 CSV 的换行换行。
- `tools/text_csv/dump_text_csv.py` / `inject_text_csv.py` / `tcslib.py` / `FORMAT.md` / `runcap.py` / `scan_text_resources.py`
- CSV 列: `id,resource,container,entry_index,offset,len_bytes,max_bytes,kind,wrap_w,lines,"text_zh","text_edited","note"`
  （UTF-8 BOM + CRLF、一条一行、正文加引号; 多行单元格 = 人工换行）
- 映射: `{br}`→换行, `{p}`→空行, 引擎自动折行点→**软换行**（建议断点, 人工自由增删）
- 判定: `text_edited == text_zh` ⇒ 该条**完全不动**（零字节改动）; 动过 ⇒ 按人工换行重写
- 变长只在**原槽位内**做（尾部陈旧区吸收 + 只重压变了的子流）⇒ IMG 条目 `off/stored/real` 一律不动
- **Lead 独立复检**: 用未改动的 CSV 注入回现役盘 ⇒ **往返零差异**（src=dst=`6d2afd49…`）✓
- 产物盘 `GR_ZH90`（`ad5f0b47…`）与现役盘差异 64333 B, **全部落在三个写入窗口内**
  （MENU#25 LANG 13469 / GR#902 LANG 13472 / MENU#283 SFXML 37392）, 窗口外 0 字节
- 真实变更实机验证: M18 介绍 174→192 B、练习1简介 239→244 B ⇒ 人工断点生效
  （武器页差异仅 bbox(31,158)-(252,205), 列表页 0 像素差异; 简报页第 1 段断在
  「欢迎参加第一次战术演习。」之后 ⇒ **实证 `{br}` 在语言表简报组件里同样有效**）

#### 三、解码口径统一（重要, 待另立任务）
`tools/diag/res_text_dump.py` 的 `dec()` 是**对偶优先**, 实测引擎/本项目编码器是**单字节优先**
（`0xA1..0xAD` 才是双字节 lead; `0xAF`=的、`0xB0`=你）⇒ 对偶优先会把 `AF A1 BD` 读成「弗开」,
让整份 dump **系统性错字**（`队中的队员` → `队弗中他队员`）。
`tools/text_csv/tcslib.py` 用正确口径并加了锚点自检（任一不通过拒绝出 CSV）+
编码器拒绝 lead≥0xAE 死 pair + 回读校验。**建议后续统一到 `tcslib.Charset`, 标注/废弃旧 `dec()`**。

#### 四、现役盘
```
work/builds/GR_ZH91/GR_ZH91.iso   1,648,164,864 B
sha256 42d04a4f61982a00b2b31b6a4ecc97ec0d814810b56e0695befdb63b4b92ec88
= GR_ZH89 (6d2afd49…) + patch_zh_fix_order_label.py
审计 r23_audit_inventory.py ⇒ 在役 44、缺失 0 ✓
```
清理: 删除 GR_ZH90（工具链 demo 盘）/ GR_ZH90_label（已被本版取代）; 只留 `GR_EN_ORIG` + `GR_ZH91`。
**版本号**: `GR_ZH90` 已被本轮两个盘占用（工具链 demo / 错译修正）⇒ 下一个新盘 = **`GR_ZH92`**。

#### 五、工具链覆盖范围（报告已写约束与迁移路径）
- **已覆盖**: `LANG`（MENU#25 + GR#902, **2232 条**/54695 B, 255 长段）、`SFXML`（MENU#283, 69 条 `<text>`）
- **未覆盖**: `EN_STRINGS.TXT`[#30]（明文非 LZO）、GR.IMG ~250 条 `.ATR` 的 `<ActorName>`
  （需新解析器 + 历史「乱改 ATR 名致指令面板打不开」铁律）、ELF `.rodata` UI 串（载入屏/等待提示）、
  `.MIS` 任务容器（未逆向）
- **顺带修正的事实**: 语言表组间有 4 字节分隔（实测恒 0）, `ngroups=66`, 条目 **2232 条**（不是 588）;
  本机 `run_opt.py`（`-grscanframes 2000`）引导比历史慢约 3 倍 ⇒ 导航全废,
  用 `runcap.py -grscanframes 4000` 后时间线与历史一致

### 70. ★ work/ 目录收敛 + 构筑产物一律落在版本文件夹内 (2026-10-10)

用户:
> 每次使用构筑脚本时 都要连带在版本号文件夹内输出**文本 csv 和字库的 dump**；
> **work 文件夹内现在用不到的内容在确认可以复原的情况下都进行清除，只留下 build**；
> **每一轮需要 dump 或者各种操作都要限制在版本文件夹内**。

#### 一、work/ 现状 (清理后)
```
work/
└── builds/
    ├── GR_EN_ORIG/   英文原盘基线 (硬链接, 零额外占用)
    └── GR_ZH91/      现役盘 + 该版本的文本表 (GR_ZH91_text.csv / .meta.json)
```
- 清理前 `work/` 有 12 个顶层目录、**约 15.9 GB**；清理后只剩 `builds/`（**约 4.2 GB**），**释放约 14.4 GB**。
- **清理前的可复原性保障**（用户要求「确认可以复原」）：先把所有「删掉就找不回」的内容**全部提交进 git**
  （提交 `ab477120`）：
  - `work/archive/**`（各轮证据图/对照图，docs 里被引用）
  - `work/_dis/*.py|md|txt|json`（各轮诊断/修复/文档脚本与记录）
  - `work/_squad/*.txt|md`（小队界面普查等文本记录）、`work/_briefs/**`、`work/_dot_*`、`work/_probe_known.json`
  - `work/text_csv/GR_ZH91_text.csv`（+meta，给用户编辑的正式文本表）
  删除的其余内容均为**可再生成的中间产物**：`iso_tree`（ISO 解包）、`tmp`、`_dis` 的输出/日志、
  `_squad` 的二进制中间数据、`text_csv/dev` 测试产物、`r35_before_tools`（旧工具快照，git 历史里有）、
  `text_versions`（已入库）。
- **审计工具迁址**：`work/_dis/r23_audit_inventory.py` ⇒ **`tools/iso_build/audit_inventory.py`**
  （`work/_dis` 已整体删除）。用法与语义不变，铁律不变：
  **任何改 ELF 的补丁之后必须跑它，结果必须「缺失 0 条」**。

#### 二、★ 新规：一轮的所有产物只落在该版本的文件夹里
```
work/builds/<版本>/
├── <版本>.iso                 构筑产物
├── build_info.json            版本元信息 (base/patches/iso_sha256/text_snapshot/font_dump)
├── <版本>_text.csv            该版本文本快照 (可编辑)
├── <版本>_text.txt            该版本文本快照 (轻量, 便于 git diff)
├── <版本>_font_atlas.png      该版本字库图集 (可视化)
├── <版本>_font_ft.csv         该版本字库 FT 记录表
├── <版本>_font_charset.csv    该版本字符集清单 (含是否有字形)
├── <版本>_font_summary.json   字库 dump 摘要
└── temp/                      该轮实机转储/中间态 (dump_<TAG>/、注入报告等)
```
- **不再写** `work/text_versions/**`（旧归档目录已删除，改由版本文件夹承载）
- **不再写** `work/tmp/**`
- 以后每一轮的 dump / 注入 / 实机转储 / 报告**一律放进该版本文件夹**（`temp/` 或按需子目录）

#### 三、对既有铁律的补充
1. **`work/` 只保留 `builds/`**；不要把脚本、日志、证据散落到 `work/` 其它位置。
   —— 工具放 `tools/`，文档放 `docs/`，每轮产物放 `work/builds/<版本>/`。
2. 需要在 `work/` 之外留证据时，**提交进 git**（`work/**` 被 .gitignore 忽略，需 `git add -f`），
   或者放到 `docs/` / `tools/` 下。
3. 删除任何东西之前，先确认**能从 git 或从 ISO 重新生成**。

### 71. ★ 构筑产物一律落在版本文件夹内 + 每轮自带「文本表 + 字库快照」(2026-10-10)

用户:
> 每次使用构筑脚本时 都要连带在版本号文件夹内输出**文本 csv 和字库的 dump**；
> work 文件夹内现在用不到的内容在确认可以复原的情况下都进行清除，只留下 build；
> **每一轮需要 dump 或者各种操作都要限制在版本文件夹内**。

#### 一、版本文件夹布局（新规，已实装）
```
work/builds/<版本>/
├── <版本>.iso                  构筑产物
├── build_info.json             版本元信息 (base / patches / iso_sha256 / text_snapshot / font_dump)
├── text/   <版本>_text.csv     该版本文本表 (Excel 可直接编辑)
│           <版本>_text.txt     轻量副本 (id<TAB>正文, 便于 git diff; 已剥离 {WRAP})
│           <版本>_text.meta.json
├── font/   <版本>_font_atlas.png      图集可视化 (1024×512 → 2 倍, 黑=有字形)
│           <版本>_font_ft.csv         FT 记录表 (face/index/code/advance/u0..v1/slot/ink/has_ink)
│           <版本>_font_charset.csv    字符集清单 (char/unicode/kind/bytes/slot/cell/has_glyph/note)
│           <版本>_font_summary.json   统计 + 各文件 sha256 + 网格配方
├── temp/                       该轮中间态 (inject 报告、textdump)
└── extract/                    dump 用的解包中间物 (字表/图集/MENU.IMG)
```
- **不再写** `work/text_versions/**`（含 INDEX.md）与 `work/tmp/**`；`diff_text_versions.py` 的临时文件改到系统临时目录
- 新增 `--no-font-dump` 跳过字库 dump；`--inject-csv` 现在也接受版本名/版本目录

#### 二、字库 dump 的实测数字（现役盘 `GR_ZH91`）
| 项 | 值 |
|---|---|
| face | 3（记录 224 / 224 / 96） |
| FT 记录 | **544** |
| 字符 | **1456**（ascii 95 / single 76 / pair 1281 / icon 4） |
| 有字形 | **1423** |
| 缺字形 | **33** = 31 个小写 ASCII 与符号（字形在别的 face，实机可读 ⇒ 告警级）+ `欣`/`袁`（只有死 pair、格子实测为空） |
| 图集 | 1024×512 PSMT4，墨占比 18.91% |
| 可复现 | 同一目录重复 dump，四件套 sha256 全同；独立 dump 与版本文件夹内 sha256 相同 |

字库抽查（独立用 `tcslib` 重解析同一 ISO 复核）：FT CSV 行数 544 == 记录数、逐条与磁盘字表一致；
`的`(single 0xAF, cell 16,178)、`好`(pair A2F6, slot 179, cell 884,34, 墨 61)、
`攻`(pair A1F4, slot 83, cell 340,18, 墨 68) 的 `has_glyph` 与坐标全部一致；
ASCII `'A'` 记录 `(0,8,256,452,264,468)` 与 `docs/FONT_CURRENT_STATE.md` 权威值吻合。

#### 三、目录收敛断言（实跑）
`work/` 除 `work/builds/` 外：构筑前 `['builds/']` → 全部操作后 `['builds/']`，**新增 0**。

#### 四、work/ 清理结果
- 顶层从 12 个目录（约 15.9 GB）收敛为**只有 `builds/`**（约 4.2 GB），共释放约 **14.4 GB**
- 清理前先把「删掉就找不回」的内容**全部入库**（提交 `ab477120`）：`work/archive/**`、`work/_dis/*.py|md|txt|json`、
  `work/_squad/*.txt|md`、`work/_briefs/**`、`work/_dot_*`、`work/_probe_known.json`、`work/text_csv/GR_ZH91_text.csv`
- 又从**索引**移除 `work/` 下除 `builds/` 外的全部路径（提交 `e1265b9e`）⇒ 工作区与索引同时干净，
  内容仍可从 git 历史取回（例 `git show ab477120:work/_dis/r23_audit_inventory.py`）
- 审计工具迁址：`work/_dis/r23_audit_inventory.py` ⇒ **`tools/iso_build/audit_inventory.py`**（已冒烟：在役 44 / 缺失 0）

#### 五、现役版本文件夹已补齐
`work/builds/GR_ZH91/` 现含 `text/`（3 件）+ `font/`（4 件）+ `build_info.json` + ISO，
即用户要的「版本号文件夹内自带文本 csv 和字库 dump」。

### 72. ★★ `{WRAP}` 改为人工断点控制 + 现役盘升为 `GR_ZH92` (2026-10-11)

用户:
> **我希望主动控制断点，只在内容里添加 `{Warp}` 控制断点。**
> 我修改了 `GR_ZH91_text.csv` 的 M2203（实为 `SFXML:T0010`），检查一下能否正确识别和注入。

#### 一、检查结论（用户改动被正确识别，但断点当时不生效）
- 用户只改 1 条：`SFXML:T0010`（M18 定向反步兵地雷 介绍，CSV 第 2689 行）
  —— 重写文案 + 删掉 `{WRAP}` 前后的人工空格 + 把 7 个 `{WRAP}` 挪到他想要的断行处
- 预检 exit 0、真实注入 exit 0 ⇒ **文案写进去了**；但旧语义下 `{WRAP}` 是「建议断点、注入时整段丢弃」
  ⇒ **他指定的断点不生效**（引擎仍自行按宽度折行）—— 这正是要改的

#### 二、新语义（round36 实装）
| | 改前 | **改后** |
|---|---|---|
| 人写的 `{WRAP}` | 注入时丢弃 ⇒ 断点永不生效 | **断点指令 ⇒ 注入时写出真换行 `{br}`** |
| dump 是否自动插标记 | 会（1548 个，混在正文列） | **绝不插** |
| 「引擎现在在哪折行」 | 与人工断点不可分 | 只进**只读列** `wrap_hint`（字符位置）/ `wrap_preview`（插 `\|` 预览） |
- **`{WRAP}` 与 `{Warp}` 不是大小写关系**（W,a,r,p vs W,R,A,P）⇒ 正则按两种拼写 + `re.I` 收
- 位置校验：行首/行尾/紧邻另一个标记或换行 ⇒ **报错拦截**（那些位置会写出 `{br}{br}`，CSV 无法无损表示）
- 写法错（`{WRAP` / `{WRP}` / `{WRAPP}`）⇒ 注入前拦截，exit 1，`--force` 不能绕过
- **旧格式表（`text-csv/1|2`）改长段 ⇒ 拒绝注入**（有意保护：旧表 1548 个自动提示会被当成断点全固化），
  并给出 `--carry-edited` 重 dump 命令；新表格式 = **`text-csv/3`**

#### 三、用户改动的验收（6/6 全过）
1. **往返零差异**：新表原样注入 ⇒ 与 `GR_ZH91.iso` 逐字节相同（`42d04a4f…`）
2. **断点生效**：`SFXML:T0010` 的 `{br}` 0 → **7**，位置 `15,28,38,52,63,78,92`，与用户标记一一对应
3. **再 dump 回来**：变 7 个真换行、`{WRAP}`=0，文本可读
4. **多轮稳定**：三轮 编辑→注入→dump→再注入，`{br}` 7→8→7 不漂移、可见文本 hash 不变
5. **错误处理**：9 个写法/位置用例 + 旧格式表 ⇒ 全部 exit 1 且未写盘
6. **实机**：特别收录→武器(M18) 断行完全按用户标记；107 帧中 98 帧逐像素一致，
   仅武器内页 9 帧变（差恒 6263 px = 介绍文本框）

#### 四、现役盘 = `GR_ZH92`
```
work/builds/GR_ZH92/GR_ZH92.iso   1,648,164,864 B
sha256 1d30c1067beb8fc8534193486f23f75489447eb0487ab24d06ef66c0627120b6
= GR_ZH91 (42d04a4f…) + 用户新文本 (SFXML:T0010 重写 + 7 个人工断点)
```
- 构筑：`make_build.py GR_ZH92 --from work/builds/GR_ZH91/GR_ZH91.iso --inject-csv <新表>`
- 审计 `tools/iso_build/audit_inventory.py` ⇒ **在役 44、缺失 0**
- 版本文件夹自带 `text/`（`text-csv/3`）+ `font/`（图集 PNG + FT csv + 字符集 csv + summary）
- **版本号规则**：每次改动产出新盘用新版本号 ⇒ 下一个新盘从 `GR_ZH93` 起

#### 五、文本表安装与以后的操作
- 新表已装入 `work/builds/GR_ZH91/text/GR_ZH91_text.csv`（sha256 `af93d4b0…`，
  与构筑 GR_ZH92 时用的 `temp/GR_ZH91_text_carry.csv` **逐字节相同**）；
  用户原表（旧格式）逐字节备份在 `work/builds/GR_ZH91/temp/GR_ZH91_text_v2_用户改动保留.csv`
- 安装命令：`python work/builds/GR_ZH91/temp/install_text_csv.py`（复制 + 校验 sha256 + 只读预检）
- 以后流程：改 `text_edited` → **哪里要断行就写 `{WRAP}`（或 `{Warp}`）** → 构筑时 `--inject-csv <表>`

#### 六、遗留
- `make_build.py` 的 `make_text_snapshot()` 仍 `.replace('{WRAP}','')`：构筑流程里**无害**
  （快照取自刚产出盘的新 dump，正文列无标记），建议后续改成把 `{WRAP}`/`{Warp}` 渲染成 `\n`
- `kind=icon` 的 `0xB1/0xB5/0xE7/0xF1` 语义未逆向（`E7`/`F1` 很可能是 `ç`/`ñ`）
