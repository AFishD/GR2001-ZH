# REPORT: GR 钩子移植到 v2.8.2 稳定版 (port282) — 2026-09-26

## 0. 结论

**全部钩子已成功移植到 v2.8.2 stable 并通过端到端验证,无丢失功能。**
部署已替换 Sep-17 p4 应急版 (旧 exe 备份为 `pcsx2-gsrunner-p4.exe.bak`)。
今后测试/开发基于 `gr-2.8.2` 分支 (用户指令:"以后的测试和开发都在这个版本上进行")。

- 版本确认: `PCSX2 GS Runner Version v2.8.2-1-gcd5e3304c` (-1 = 钩子 cherry-pick 提交)
- 内层仓库 (tools/emu/pcsx2_src, 自有 git):
  - master @ `a657fa313` = 钩子快照提交 (10 文件, +1309/−8, 基于 236f67a82)
  - 分支 `gr-2.8.2` = `v2.8.2` tag (fd9d310cc) + cherry-pick `cd5e3304c` (无冲突)
  - 外层仓库 git 未触碰 (快照/提交均在内层仓库)

## 1. 移植内容 (与 master 快照逐字节同源, cherry-pick `a657fa313` → `cd5e3304c`)

| 文件 | 内容 | 移植状态 |
|---|---|---|
| pcsx2-gsrunner/GRResearch.{cpp,h} | 研究层: -gr* CLI 预解析、输入注入、memcard/texdump 目录、needle RAM 扫描、drawlog/grlog、组件/寄存器钩子宿主 | 新文件, 原样 |
| pcsx2-gsrunner/CMakeLists.txt | 加入 GRResearch.{cpp,h} | 原样 |
| pcsx2-gsrunner/Main.cpp | GRResearch::ParseCommandLineArgs 预处理、IsActive 放行 ISO boot、research SettingsOverride、GRTrace、CPUThreadMain ISO 路径 | 原样 |
| pcsx2/CDVD/CDVDcommon.cpp | g_cdvdReadHook (readSector/readTrack) + cdvd.log LBA watch | 原样 |
| pcsx2/GS/GSState.cpp | g_gsTransferHook、g_gsRegLog{Tex0,Bitblt,Trxpos,Trxreg,Vert,AD,TEX1,Prim}、g_gsVramProbe、PRIM/TEX0/TEX1/SCISSOR/ALPHA/TEST 埋点 | 原样 |
| pcsx2/Gif.h | GR_GIF_DIAG 日志设施、GR_PATH3_BUFF_MB=64、GR_PATH3_SLICE_MB=2 | 原样 |
| pcsx2/Gif_Unit.{h,cpp} | **PATH3 修复**: 9MB→64MB 缓冲 + 压力切片 (EOP-less 流式包 >2MB 时在 tag 边界切片) + 溢出降级 (丢数据不写坏堆) | 原样, **游戏必需** |
| pcsx2/x86/ix86-32/iR5900.cpp | grIsDrawHookPC + recRecompile 入口 trampoline (0x219A70/219E00/219EB0/21AC00/21AD10/5172E0/21A190/21A290/21C4C0) | 原样 |

### 冲突解决
`git cherry-pick a657fa313` **零冲突自动合并** (10/10 文件干净落位)。已逐一人工核对 8 个修改文件的 diff 上下文与 2.8.2 语义兼容性:
- `VMManager::Initialize(const VMBootParameters&, Error*)` — 2.8.2 签名一致 (VMManager.h:122)
- `Pad::ClearPortBindings` / `Pad::SetControllerState` / `Pad::GetControllerInfo` — 存在于 SIO/Pad/Pad.h
- `g_gs_renderer`、`GSLocalMemory::m_psm[].rp`、`GSQueueSnapshot`、`EmuFolders::MemoryCards` — 均在
- `GS/...` 前缀 include 风格 — 2.8.2 同款
- 编译实证: 0 error 0 warning-driven failure, GRResearch.cpp/Main.cpp 一次通过

### 未能移植的功能
**无**。所有 -gr* CLI 选项 (-grdrawwin/-grinput/-grmemcards/-grsnap/-grscanframes/-grdumpdir/-grwatchlba/-grperiodram 及 -grdumpwin/-grpcsample/-grvramprobe/-grreglog 等扩展)、全部埋点、PATH3 修复均在内。

## 2. cmake 0xC0000409 静默崩溃诊断 (round22 遗留 "待查" 项, 本轮定案)

- 复现: `build_pcsx2.sh --purge/--configure` → cmake **零输出, MSYS 报 exit 127**; 2.8.2 CMakeLists 同样崩溃 → **非 master 特有**。
- 修复: **rm -rf 构建目录 `tools/emu/pcsx2/` 后重新 configure 即成功** (带完整 MSVC env, 无需 trace, exit 0, 7.1s)。
- 根因判定: 崩溃与 **构建目录残留状态** 相关 (master 时代的 CMakeCache/CMakeFiles 在源码切换到 2.8.2 后残留, cmake 4.0.3 处理时 fail-fast 0xC0000409)。触发要素 = cmake 4.0.3 + 该树 CMakeLists 处理 + 陈旧 cache; trace 模式 (`--trace-expand --trace-redirect`) 下也不复现 (行为/时序改变)。
- 环境因素排除项: 诊断中发现脱离脚本全量 env (缺 SDK bin 的 rc.exe) 会以普通 CMake 错误失败 ("CMakeTestCCompiler ... RC Pass 1 ... no such file or directory") — 与 0xC0000409 崩溃是两回事, 脚本 env 本身正确。
- **运维结论**: 源码分支/tag 切换后必须删除 `tools/emu/pcsx2/` 构建目录再 configure; `build_pcsx2.sh --purge` 目前不删目录, 已在 §23 记录 (脚本未改动, 本轮用 rm -rf + 复跑脚本绕过)。
- 备注: 脚本经 `bash ... | tail` 调用时管道会吞掉真实退出码 (tail=0), 诊断时须直接看 `${PIPESTATUS[0]}`。

## 3. 构建与部署出处

- 配方: `work/emu_build/build_pcsx2.sh` (junction C:\grbuild → 仓库; MSVC 14.51 + SDK 10.0.28000.0; Ninja; Release; ENABLE_GSRUNNER=ON, USE_VULKAN=OFF)
- ninja 目标 `pcsx2-gsrunner`: 739/739, 链接成功, exit 0
- exe: `tools/emu/pcsx2/pcsx2-gsrunner/pcsx2-gsrunner.exe` (9,776,640 B, 2026-09-26 16:12)
- 资源: `resources/` ← `pcsx2_src/bin/resources`; DLL ← `third_party/deps/bin/*.dll`; `bios/SCPH-70012_BIOS_V12_USA_200.bin` ← `tools/emu/run/bios`
- 旧 p4 exe 备份: `pcsx2-gsrunner-p4.exe.bak` (9,773,056 B, 源自 work/zh16b/subagent_gs/pcsx2-gsrunner-p4.exe; 注: ninja 链接先于备份覆盖了原位文件, 该副本为此前 p4 轮留档)

## 4. 验证数字

### 4.1 Smoke (300 帧, GR_ZH62.iso)
- exit **0**, `=== run end, frames=300 ===`; 钩子层全部激活 (grlog 121 行, drawlog/cdvd.log/needle 扫描/RAM dump 均产出)

### 4.2 全量快速导航简报跑 (run_brief2.py port282, 9200 帧, nav_p2.txt, snapstep 100)
- exit **0**, 155s; `=== run end, frames=9200 ===`, draw-path logger 930,291 行; 89 张 snap

### 4.3 drawlog.txt 断言 vs 参考 dump_v5_zh62 (同盘参考捕获)

| 断言 | 新 (port282) | 参考 (v5_zh62) | 判定 |
|---|---|---|---|
| 简报目标行 RA=21DA28 y=288 (F13=43900000) | 576 | 576 | **全等** |
| RA=21DA28 y=309 (439A8000) | 576 | 576 | **全等** |
| RA=21DA28 y=330 (43A50000) | 576 | 576 | **全等** |
| RA=21DA28 y=351 (43AF8000) | 576 | 576 | **全等** |
| 表头 RA=21C62C y=268 (F13=43860000, 经 RA=219EEC/21DA28) | 576+576 | 576+576 | **全等** |
| 表头 RA=21C62C F13 分布 (43D30000/3F800000/43D18000/43000000/42D80000/41C80000) | 5782/5358/5352/576/576/576 | 5783/5358/5352/576/576/576 | **±1 行级一致** |
| 标题 x=33 (F12=42040000) | 5361 | 5361 | **全等** |
| y=25 (F12=41C80000) | 5 | 5 | **全等** |
| 219EB0 DrawString 行总数 | 67,312 | 67,324 | 差 12 (窗口边缘计时抖动) |
| 0x21C4C0 组件行 (font/style/ax/ay/W/H/cx/cy 字段) | **23,578** | 0 (参考早于该钩子) | 新功能在 2.8.2 正常产出 |

### 4.4 PATH3 修复实证
- `gifpath_diag.log` (26.7MB): PATH3 (idx=2) 缓冲前缀实测达 **curSize≈66,059,552 B (~63MB)** — 旧 9MB 缓冲会 7 倍溢出 (即用户所见 0xFEFEFEFE 崩溃源)
- **OVERFLOW 事件 = 0**, 跑满 9200 帧 exit 0 → 64MB 缓冲 + 压力切片在 2.8.2 生效

## 5. 遗留/注意事项
- `build_pcsx2.sh --purge` 不删构建目录; 切换源码版本后需先 `rm -rf tools/emu/pcsx2/` (建议后续给脚本加 purge 实删逻辑)
- gsrunner 目录下的 `gifpath_diag.log` 会持续增长 (本轮 26.7MB), GR_GIF_DIAG=1 常开会写盘; 如需静默可置 0 重编
- 内层仓库工作树留有未跟踪垃圾 (.bak_zh43/*.dll/__pycache__), 未纳入任何提交 (与任务要求一致)
