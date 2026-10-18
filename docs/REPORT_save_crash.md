# REPORT_save_crash.md — round70:「完成关卡→存档→加载→黑屏卡死」实机定位

> 执行者 = 实机崩溃定位子代理 · 2026-10-14 · 分支 `main`（未切分支、未 commit）
> 素材 = 用户即时存档 `work/temp/SLUS-20613 (7A361FB5).01.p2s`（10:07:35）
> 产物目录 = `work/builds/GR_ZH116/`（tmp/temp）、脚本 = `tools/iso_build/fix_zh116_*.py`

---

## 0. 一句话结论

**用户从这个即时存档进去、走「战后回顾 → 继续 → 要保存吗?(是) → 选档案 → 选择文件」这条路,
必然在「选择文件」屏卡死**（EE 主线程进 BIOS 内核 idle/等待循环 `0x00081FC0`, 一万帧不返回,
按键全无效, 记忆卡**没有**被写）。

**这个卡死与汉化盘无关** —— 三条独立证据:

| # | 实验 | 结果 |
|---|---|---|
| 1 | `GR_EN_ORIG`（未改动的英文原盘）+ 同一存档 + 同一输入 | **逐帧同构**: 屏幕切换帧号 (f856/916/1964)、PC 轨迹、卡死点全部相同 |
| 2 | 把存档 `eeMemory.bin` 里**汉化 ELF 与英文 ELF 不同的 1850 个字节全部还原成英文值**（`fix_zh116_mkstate.py`）+ 英文原盘 | **照样卡死在同一帧**（f1964 → `0x81FC0`，直到 f9000 不动）⇒ 连**代码补丁**也不是原因 |
| 3 | `GR.IMG` 条目布局对照（`fix_zh116_entries.py`） | **4070/4070 条目 `off/stored/real` 与英文原盘逐字段相同**（0 搬迁）；MENU.IMG 只有 `EN_STRINGS.TXT`(off 2414080→58236928, 历史既定) 与 `NTSC_IKE.RES` 两项 ⇒ **不是 PROGRESS §51 那类"条目搬迁导致读档卡死"** |

⇒ 换盘不改变结果；**卡死的触发条件在"这份即时存档所恢复的游戏状态"里**，不在盘上。

---

## 1. 怎么加载即时存档（本轮的模拟器改动）

gsrunner **原本没有任何读存档的开关**（只有 Qt 前端有 `-state`/`-statefile`）。本轮新增:

| 文件 | 改动 |
|---|---|
| `third_party/emu/pcsx2_src/pcsx2-gsrunner/GRResearch.cpp` / `.h` | 静态 `s_state_file` + `-grstate <file>` 解析 + `GetStateFile()` |
| `third_party/emu/pcsx2_src/pcsx2-gsrunner/Main.cpp` | `ParseCommandLineArgs` 开头 `params.save_state = GRResearch::GetStateFile();`（`VMManager::Initialize` 会加载） |

构建: `bash tools/emu_build/build_pcsx2.sh`（`MVC_ROOT=C:\Users\84363\pbt\msvc`），
增量 = 2 个 .cpp + 链接 ≈ 90 s。**坑**: 链接要求 `pcsx2-gsrunner.exe` 不被占用,
并行任务的 gsrunner 会让链接 `LNK1104` 失败（本轮等了 ~6 分钟）。

跑法（`tools/iso_build/fix_zh116_run.py` 封装）:

```powershell
python tools/iso_build/fix_zh116_run.py --iso work/builds/GR_ZH111/GR_ZH111.iso `
  --tag <名字> --state "work/temp/SLUS-20613 (7A361FB5).01.p2s" `
  --maxframes 12000 --snap 15 --pcsample --input <帧号输入表> [--live <运行时命令文件>] `
  [--memcards <记忆卡目录>]
```

实测: 存档加载后**第一帧就是用户的「战后回顾」屏**（与存档内截图逐像素同屏）⇒ 加载本身没问题。

---

## 2. 复现流程与现象（帧号确定性）

输入表 `work/builds/GR_ZH116/temp/nav_save_full.txt`:

| 帧 | 按键 | 画面 |
|---|---|---|
| 4..330 | — | 「战后回顾」（你胜利了 / 任务目标 / 信息 / 继续·退出） |
| 300 | cross | — |
| **345** | — | 「**要保存当前进度吗？**」是/否（默认「否」） |
| 800 | left + cross | 选「是」 |
| **930** | — | 「**选择你的档案。**」（TEQSUNSET / TEQSUNSET / 乱码「—⊤—」） |
| 1400 | cross | 选第 1 个档案 |
| **1815→1965→1980** | — | 黑屏过渡帧（17051 B，即用户说的"加载界面"）→「**选择文件**」（幽灵行动● 任务 2 新兵 / -空-） |
| — | 任意按键 | **完全无效**（连按 cross/down，逐帧截图逐字节相同） |

观测证据:

* `-grpcsample 1`（每 4 帧记 `cpuRegs.pc`）: **f1964 起 PC 恒为 `0x00081FC0`，直到 f12000**。
* `0x00081FC0` 处是 `nop` 滑梯 + `0x81FD8: beq $0,$0,-7`（死循环）, 后面跟着
  `lui $29,0x0008 / jalr $31,$3 / addiu $29,$29,0x1FC0 / addiu $3,$0,-5 / syscall` 这类内核桩。
  **该字节序列不在游戏 ELF 里**（全 ELF 搜 0 命中），且在**存档生成时就已经在 RAM 里**
  ⇒ 是 BIOS/内核在低地址的 idle 桩, 不是野指针。
  同一 PC 在**保存提问 → 档案屏**的过渡帧（f856..f916）也出现过 ⇒ 它是"**主线程在等事件**"的
  idle/等待循环, 而这次它**再也不返回**。
* 记忆卡**没有被写**: 跑完 `mc/Mcd001.ps2` 与用户原卡 sha1 完全一致（`1e3255493928373a`）
  ⇒ 存档流程在写卡**之前**就卡住。

---

## 3. 用户当时跑的是哪一代盘（判据）

`fix_zh116_elf_fp.py` / `fix_zh116_state_probe.py`:

* ELF 指纹: 各代 `SLUS_206.13` **互相不同的 1884 个偏移**去问存档 `eeMemory.bin`（EE RAM 里
  段的映射实测 = `RAM[p_paddr + i] == ELF[0x80 + i]`, 逐字节 100%）:

  | 盘 | 判别性偏移命中 |
  |---|---|
  | GR_ZH109 / **111** / 113 / **114** | **1884 / 1884** |
  | GR_ZH112 | 1880 |
  | GR_ZH98 | 1874 |
  | GR_ZH115 | 1850 |
  | GR_EN_ORIG | 34（1.8%） |

* 字库容器指纹: `extract/font_new_font_revised.bin` 的 sha —
  GR_ZH111/112/114/115 同为 `f13061ec5da8`，**GR_ZH113 不同**（`df7c5d11d3b3`，扩容 329 字盘）。
* 时间线: 存档 10:07:35 < GR_ZH115 构筑 10:08:25（晚 53 s）⇒ 不可能是 115。

⇒ **用户在跑 GR_ZH111 或 GR_ZH114**（两者 ELF/字库/LANG 完全相同，只差 SFXML 标题 58 条）；
GR_ZH109 与 111 文本也相同 ⇒ 崩溃路径与这几代的差异无关。

---

## 4. 附带的记忆卡取证（为什么"卡死与盘无关"还有一层含义）

* 用户卡 `Mcd001.ps2`（8,650,752 B，528 B/页 × 16384 页）目录树:
  `BASLUS-20613GHOST001`(dir, clu=3103, 7 项) / `BASLUS-20613GHOST002`(dir, clu=3603, 7 项)
  + 两个 123,905 B 的同名数据文件 + `icon.sys`/`slime*.ico`。
* 存档内容 = **XML 文本**（`<UnlockedMissions>`/`<OptionsFile>`/`campaign.xml` + 一堆 `*.atr`）。
  档案名 **`TEQSUNSET`** 在**仓库自带模板卡（2026-09-24）里也是 `TEQSUNSET`**
  ⇒ 不是今天被写坏的字符串（先前怀疑的"名字被加前缀"排除）。
* 用户卡的 GameRecon 存档与「选择文件」屏里显示的「幽灵行动● 任务 2 新兵」一致（slot1），
  slot2 空。

### 4.1 ★ 换卡对照：卡死**只在"用户这张卡"上出现**

同一存档 + 同一输入表 + 同一张盘，只换记忆卡（`--memcards`）:

| 记忆卡 | 结果 |
|---|---|
| **用户卡（`%LOCALAPPDATA%\PCSX2\memcards`）** | f930 档案屏 → f1980「选择文件」→ **f1964 起 PC 钉在 `0x81FC0` 直到结束（卡死）** |
| 仓库模板卡 `third_party/emu/run/memcards/Mcd001.ps2`（有效卡、**含** 2026-09-24 的 GR 存档） | f870 弹「**记忆卡槽1里没有记忆卡(8MB)**」→ 之后流程可走、**PC 全程只有 `0x411FB0`（无卡死）** |
| 2026-09-05 备份卡 `memcards/backup_20260905/Mcd001.ps2`（有效卡、含 9 月的 GR 存档） | 同模板卡（f870 弹"没有记忆卡"、**不卡死**）|
| 用户卡 **改名**掉 GR 存档目录项（`fix_zh116_rencard.py`, 等长改名保持卡片结构合法） | 同上：弹"没有记忆卡"、**不卡死** |
| 用户卡 **清 mode 位**删掉 GR 存档（`fix_zh116_mkcard.py`） | PCSX2 会把整张卡当不可用 ⇒ 游戏弹"没有记忆卡"（**这个对照不成立**, 记下来免得再踩） |
| 全 `0xFF` 空白卡 | 同上"没有记忆卡" |

⇒ 结论: **卡死必须"用户这张卡 + 它里面那份 GR 存档"同时在场**才会发生;
一旦游戏找不到它自己的存档（任何其它卡 / 改名 / 空卡），游戏走的是"没有记忆卡"的
错误分支, **不会卡死**。也就是说: 卡死发生在**游戏处理它自己那份存档数据**的路径上。

> ★ 更正一条差点写错的推测: 现查字节, **2026-09-05 的备份卡里同样是 `TEQSUNSET`**
> （先前 `SUNSET` 计数 1 只是 `TEQSUNSET` 的子串命中）⇒ **档案名一直是 `TEQSUNSET`**,
> 不存在"名字被加前缀"这回事。另外: 仓库模板卡 `third_party/emu/run/memcards/Mcd001.ps2`
> 在存档区与 09-05 备份卡**逐字节相同**（就是同一张卡的拷贝）。
>
> ★ 真正的内容差异: **用户现卡的 `GHOST001` 里有 `campaign.xml` + 一串 `*.atr`（战役中途存档）**,
> 而 09-05 备份卡/模板卡的 `GHOST001` 只有 `<UnlockedMissions/>`/`<OptionsFile>` 这类选项数据
> ⇒ 只有"**存在战役存档**"的那张卡会走到卡死分支。

---

## 5. 结论与建议

1. **不是汉化引入的**（§0 三条证据 + §4.1 换卡对照）⇒ **本轮不出 GR_ZH116, 也不需要出**。
   任何"改文本/改字库/改 ELF"都不会影响这个卡死。
2. 触发条件 = `这份即时存档恢复的游戏状态` + `用户卡上那份 GR 存档`;
   与盘（汉化 / 英文原盘）、与汉化的 1850 个 ELF 字节都无关。
3. 给用户的可操作建议（按代价排序）:
   * **先备份记忆卡**, 然后换一张卡 / 或把本卡临时移走 `BASLUS-20613GHOST00*` 再走
     "完成任务 → 存档" 流程, 看是否还黑屏 —— 按本轮实测, **"卡上有没有那份战役存档"是唯一
     能改变结果的自变量**（有它 → 卡死; 没有它 → 游戏弹"记忆卡槽1里没有记忆卡"并继续）;
   * 若确认是那份存档的问题, 从 `backup_20260905` / `.stuck` 备份恢复记忆卡后再试
     （注意: 09-05 备份卡里**没有** `campaign.xml` 战役存档, 与本轮"不卡死"的对照卡内容一致）;
   * 用户真机 10:09:21 那次**写卡是成功了的**（`Mcd001.ps2` mtime=10:09:21）, 之后才黑屏 ⇒
     如果那次写卡只写了一半就崩, 卡上那份`campaign.xml`存档现在可能就是**半成品**;
     本轮只能证明"有它才卡死", **无法离线证明"它坏了"**。

---

## 6. 已知未完成 / 待办（诚实清单）

* 用户报的最终画面是"**加载界面过后黑屏**"，而本复现卡在"**选择文件**"屏（写卡之前）；
  用户那台机器 10:09:21 **确实写卡成功过**，之后才黑屏 ⇒ **我的复现点比用户实际卡死点更早**，
  两者**可能不是同一件事**（但都在"存档→加载"这条路径上）。
* 因此"**这是不是用户真机那个黑屏**"仍需一次**不带即时存档**的完整流程验证
  （冷启动 → 读用户战役存档 → 打完任务 → 存档），需要 ~30–60 分钟连续游玩级别的脚本。
* 未做的对照: 换 BIOS（本机 gsrunner 用 `SCPH-70012_BIOS_V12_USA_200.bin`,
  用户 Qt 用 `SCPH-90006_BIOS_VX_HK_2.20.bin`）——记忆卡 IOP 模块来自 BIOS,
  这是一个**尚未排除的混淆项**（本轮没做 `-grbios` 开关，重编要再抢一次 exe）。
* 没有把 `-grstate` 之外的状态钩子（运行时存/读档、寄存器 dump）加进 gsrunner;
  需要时按 `GRResearch.cpp` 里 `-grinputlive` 的写法加即可。

---

## 7. 本轮新增文件

| 文件 | 作用 |
|---|---|
| `third_party/.../GRResearch.cpp` `.h` / `Main.cpp` | **`-grstate <p2s>`**: gsrunner 启动时读即时存档（唯一的模拟器改动） |
| `tools/iso_build/fix_zh116_run.py` | gsrunner 跑存档 + 截图 + PC 采样 + live 输入的一站式封装 |
| `tools/iso_build/fix_zh116_p2s.py` | 读 `.p2s`（zip + zstd method 93; 本机 zipfile 不认, 用 `zstandard` 手工解） |
| `tools/iso_build/fix_zh116_mkstate.py` | 改存档 `eeMemory.bin`（把汉化 ELF 字节还原成英文）→ 新 `.p2s` |
| `tools/iso_build/fix_zh116_elf_fp.py` | ELF 指纹判"用户跑哪一代盘" |
| `tools/iso_build/fix_zh116_state_probe.py` | 文本快照指纹（同目的, 备用） |
| `tools/iso_build/fix_zh116_entries.py` | MENU/GR.IMG 条目布局 vs 原盘（§51 那类搬迁检查） |
| `tools/iso_build/fix_zh116_mcwalk.py` `_mclist.py` `_mcscan.py` `_save.py` `_mkcard.py` `_rencard.py` | 记忆卡目录/存档导出与对照卡生成（只读原卡, 只写副本） |
| `tools/iso_build/fix_zh116_dis.py` `_stack.py` | 极简 MIPS 反汇编 + 走栈找调用链（定位 `0x81FC0` 用） |
| `work/builds/GR_ZH116/temp/` | 全部实机产物: `dump_base111` `dump_save_yes_111` `dump_hang111` `dump_full111` `dump_en_orig` `dump_revert_en` `dump_probe111` `dump_nocr` `dump_nosave` `dump_ren` `dump_repo` `dump_boot111` `dump_bootusercard` |
