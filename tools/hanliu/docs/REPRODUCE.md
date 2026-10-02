# hanliu/docs/REPRODUCE.md — 从零复现指南（新环境：原盘 ISO → GR_ZH7 成品盘）

前提：Windows + `<anaconda3>\python.exe`（numpy/PIL）；工作区 =
`WS = C:\Users\<user>\Desktop\旧工作区`；工具链 = `WS\hanliu\tools`。
全部步骤只读原盘与基座产物，输出写 hanliu\（或指定 tmp 目录）。

## 0. 环境与素材清单

| 需要 | 说明 |
|---|---|
| 原盘 ISO | `WS\Tom Clancy's Ghost Recon (USA).iso`（1,648,164,864B，勿动） |
| MENU 基底 | `WS\han_v2\menu_working\MENU.IMG`（K99 底；等价 menu_orig + K99 三件） |
| 字体基座 | `gr_build\tmp\zh6\ft_expanded_zh6.bin`（7,222B 展开态 FONT.RES） |
| PAK 基座 | `WS\han_v2\COMMON_PAK_ZH6.bin`（400,659B） |
| RES 基底 | `gr_build\tmp\en_strings_zh_8sub_v3.bin`（8 子流，ZH6 后状态） |
| 字符选择 | `gr_build\tmp\zh7_sel.json`（157 对字 + 517 条新译）+ `zh6\charset_zh6.json` |
| 字体文件 | `D:\Document\Fonts\SimHei.ttf`（16px EBDT strike） |
| DBCS ELF | `gr_build\tmp\dbcs\SLUS_P_U.elf`（成品盘必须；只换译文不需要） |
| 模拟器 | `gr_build\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe` + `memcards_db1` |

## 1. 提取原始文本（翻译工作底账）

```bat
cd WS\hanliu\tools
PY export_texts.py
```
→ `..\texts\*.csv` 六张表（2232/2232/2220/1193/46/2902，见 texts\README.md）。
翻译以 `pc_official_zh.csv` 为参考主源，逐条填 `zh` 列得自己的 trans CSV。

## 2. 定字符集 → 字表 CSV

- 从 trans CSV 统计全部汉字（含标点）；
- 单字节字（高频按钮/标签字，≤89 格）写 `char,single[,code]`；
- 低频字写 `char,pair`（频次序！idx=224+k 按此顺序分配）；
- 选 3 个高频字作 lead 标记字 `char,marker[,A1/A2/A3]`（字符串中一律以对出现）。
- 宁少勿错：font_build 对超容量/码位冲突/字表外字符一律报错退出。
参考成品：`build\example_zh7\out\charset_example.csv`（246 字）。

## 3. 字库生成

```bat
PY font_build.py --charset 字表.csv --mode dbcs ^
   --base-ft  gr_build\tmp\zh6\ft_expanded_zh6.bin ^
   --base-pak han_v2\COMMON_PAK_ZH6.bin ^
   --ttf D:\Document\Fonts\SimHei.ttf --size 16 --out-dir out\
```
自检全过 → out\ 得 COMMON_PAK_NEW.bin / FONT_RES_slot.bin / charset_compiled.json。
（保守无-ELF 路线：`--mode single`，≤89 字，只需换 PAK。）

## 4. 译文重编码

```bat
PY text_replace.py --mode res --charset out\charset_compiled.json ^
   --input trans.csv --base-res gr_build\tmp\en_strings_zh_8sub_v3.bin ^
   --target menu --out out\en_strings_8sub.bin
```
校验：≤47,570B 槽 + 解码回环；字表外字符在此步报错（回 §2 扩表或改文案）。

## 5. 组装 MENU

```bat
PY build\example_zh7\zh7_pipeline.py
```
（或单独调管线第 4 步逻辑：menu_working 副本 + FONT.RES/PAK/RES 三条目原位写 +
条目表不变 + 差异白名单自检 → MENU_*.img，58,300,882B。）

## 6. 成品 ISO

```bat
PY make_iso.py --base-iso "WS\Tom Clancy's Ghost Recon (USA).iso" ^
   --menu out\MENU_*.img --elf gr_build\tmp\dbcs\SLUS_P_U.elf --out out\GR_ZH.iso
```
约 3 分钟；尺寸=原盘、回读比对自动断言。

## 7. 实测（gsrunner）

```bat
taskkill //F //IM pcsx2-gsrunner.exe        :: 防文件锁
PY run_test.py --iso WS\hanliu\out\GR_ZH.iso --dump C:\gr_build\dumps\zh7new ^
   --frames 40000
```
健康 = ALIVE（跑满 40,000 帧 + exit=0 + needle ≥ 3,000）；判读 Controller 页 =
`dump\snap_f00033480.png`（左列 缩小/地图/切换队员/蹲下/平移/L3键/左右窥视/暂停菜单、
右列 放大/换弹/切换武器/执行动作/开火/视角上下/R3键/快速命令 应为中文）。
CDVD_STALL → 重跑即可（模拟器层偶发挂起，与盘无关）。

## 8. 常见故障对照

| 症状 | 真因（历史实证） | 处置 |
|---|---|---|
| 开机环无字/全部文字消失 | FONT.RES 0xFF 槽被写（=表尾+huge 头） | 只写 0x20-0xFE 记录 |
| boot 即挂（~f4300 前） | 0x80-0x9F 毒字节入串；或 RES 单大子流 | text_replace 三禁已挡；子流复刻基底 |
| Controller 页某字冻结不动 | u0=0 记录（0xA1 诅咒） | u0≥1（font_build 已强制） |
| 相邻两个单字节汉字变垃圾 | 无 lead 标记制（任意对消费） | 必须配 SLUS_P_U + 标记字以对编码 |
| gsrunner 秒退 exit=1 | ISO 路径用了正斜杠 | run_test 已自动转换 |
| cdvd 停在 544/774xxx | 模拟器层挂起 | 重跑 |
