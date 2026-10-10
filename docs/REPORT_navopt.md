# REPORT_navopt — 优化开机→主菜单导航 (GR_ZH61.iso, gsrunner)

日期: 2026-09-24。目标: gsrunner 开机到主菜单 ≤ 1 分钟。
**结果: 达成 — 主菜单首行绘制于 F3303 ≈ 55.0 秒 (60fps 仿真时钟; 实测进程墙钟 ≈ 56.6s)。旧方法 ~29000+ 帧 (≈8 分钟)。**

## 交付物

| 文件 | 说明 |
|---|---|
| `nav_opt.txt` | 最终导航 (14 行输入) |
| `main_menu_f3500.png` | 主菜单截图 (F3500, 左侧行列表: 训练/战术演习/…/制作组) |
| `profile_select_f2600.png` | 档案选择界面截图 (F2600) |
| `dump_optFINAL/drawlog.txt` | 最终运行的 drawlog (2400-4500), 主菜单证据 |
| `dump_optA..optE` | 探测运行 (dump 目录) |
| `run_opt.py` / `snap_tl.py` / `an_draw.py` | 运行脚本 / 快照时间线 / drawlog 解码 |

## 最终导航 `nav_opt.txt`

```
800 start tap     # 自 f800 起每 200 帧 START 连点 (跳过 logo/宣传视频/Press START)
1000 start tap
1200 start tap
1400 start tap
1600 start tap
1800 start tap
2000 start tap
2200 start tap
2400 start tap
2600 start tap
2850 up tap       # 上×3: 高亮从"新建"→"TEQSUNSET"(顶行)
2950 up tap
3050 up tap
3250 cross tap    # 选择 TEQSUNSET → 主菜单
```

运行命令 (cwd = gsrunner 目录):
```
pcsx2-gsrunner.exe -grdumpdir <dump> -grscanframes 2000 -grsnap 100 -grmaxframes 4500 \
  -grmemcards <存档副本目录> -grinput nav_opt.txt -renderer dx11 -- <ISO路径>
```
记忆卡每轮先从 `tools/emu/run/memcards` 复制 (含 TEQSUNSET 存档), 从不回写。

## 时间线 (最终运行 dump_optFINAL, drawlog 实证)

| 帧区间 | 画面 | 证据 |
|---|---|---|
| 0–~1500 | 开机黑屏 / PS2 SCE logo (f1600-1800 亮屏) | 快照亮度 (probe B: f1600 mean=82) |
| 1501–1945 | 请等待! / 载入中… (游戏加载, START 不可跳) | drawlog F1501/1541/1621… (probe D) |
| 2213–2259 | 正在读取记忆卡插槽1 中的数据… | drawlog F2213/2259 |
| ~2352 | 载入成功 (记忆卡读入完成) | drawlog F2352 |
| 2462–2479 | **档案选择界面** (选择文件 / TEQSUNSET / -空- / -空- / 新建) | drawlog F2462(FINAL 首帧 2479) |
| 2850/2950/3050 | UP×3: 高亮 底行"新建" → 顶行 TEQSUNSET | (F3303 前无名称输入画面出现 = 未误入"新建") |
| 3250 | cross: 选择 TEQSUNSET | — |
| 3283 | 档案画面最后绘制帧 | drawlog |
| **3303** | **主菜单首行绘制** (训练/战术演习/练习/快速任务/战役/多人游戏/重放/选项/统计/特别收录/制作组/游戏信息…) | drawlog F3303, RA=21DA28, y=132 行首"训练" |

按键效果 (与 press 时间的关系):
- **START tap** = 12 帧按下 (grlog: bind 9 = 1.0 → f+12 = 0.0)。f800–1400 的 tap 落在 logo/黑屏, 无效果但无害; 真正跳过宣传视频/Press START 的是 ~f1600–2600 区间的 tap (对照 probe A: 从 f1500 每 300 帧连点, F2713 已出现档案组件)。不按 START 时 FMV 自然播完到 ~f29000 (旧校准数据)。
- **UP×3 必要**: 档案界面初始高亮在底行"新建" (旧会话 cross 直进名称输入的原因)。UP×3 到顶行 TEQSUNSET; 若初始已在顶行, UP 在顶部截停, 同样安全 (无回绕证据, probe C/D/E 三次一致成功)。
- **cross** 选择当前高亮 → 载入存档 → 主菜单 (F3283→F3303 仅 ~20 帧切换)。

## 测量与对比

| 方案 | 主菜单到达帧 | 仿真时间 (÷60) | 备注 |
|---|---|---|---|
| 旧 nav (等 FMV 播完) | ~29600+ 且选档失败 (进了"新建"名称输入) | ≈ 8.2 min | F29600 才到选档 |
| probe C (taps 1500-3000 step300, UP 3400×3, cross 3800) | F3852 | 64.2 s | 成功但超 1 分钟 |
| probe E (taps 800-2800 step200, UP 2800×3, cross 3200) | F3251 | 54.2 s | 2800 帧 start/up 同帧 (已消除) |
| **最终 nav_opt.txt** (dump_optFINAL) | **F3303** | **55.0 s** | 实测进程墙钟 77s 总 / 56.6s 至菜单帧 |

**1 分钟目标: 达成。**

## 下限分析 (什么在 gating)

- 更早的 START (f≤1400) 无效果 — 当时仍在 SCE logo/黑屏, 游戏输入状态机未生效。
- F1501–2213 的"请等待!/载入中…"与记忆卡读取无法跳过 (probe D 中 tap 2000/2200 落在其上, 画面照常推进) — 这是理论下限: 档案界面最早 ~F2462 出现。
- 因此理论最快 ≈ F2462 (选档出现) + UP/cross (~300 帧) + 菜单载入 (~50 帧) ≈ **F2800–F3300, ~47–55 s**; 当前 F3303 已接近下限。
- 若需再压缩: 只能压缩选档前缓冲 (UP 提前到 ~2700), 收益 <100 帧。

## 复现注意事项

- gsrunner cwd 必须是其自身目录 (resources/DLL)。
- 中文路径 cv2.imwrite 会失败 — 用 `cv2.imencode + np.tofile` (本目录脚本已处理)。
- 本模型会话无法直接读图, 全部验证经由 drawlog 文本解码 (`an_draw.py`, 依赖 `work/zh16/charset_compiled_zh16.json`) 与快照亮度统计 (`snap_tl.py`)。
- 每轮运行前重新复制 memcards, 避免 runner 对副本的写入累积。
