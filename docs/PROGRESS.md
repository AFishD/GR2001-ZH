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
