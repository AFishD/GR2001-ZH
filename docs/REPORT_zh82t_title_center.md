# REPORT_zh82t_title_center.md — 子界面标题垂直居中修复 (GR_ZH82_T, 2026-10-07)

> 报障: **主菜单几乎每一项进入后, 界面左上角的子界面标题上偏** (早期版本已调到垂直居中)。
> 结论: 根因是 `patch_zh85.py` 把 **GR_ZH61 引入的标题居中量** NOP 掉了; 本补丁只还原这一个词。
> 产物: `tools/iso_build/patch_zh_title_center.py` + `work/builds/GR_ZH82_T/GR_ZH82_T.iso`
> (sha256 `9459a2ffa74c8244947f4fdbeba080da32cc96a74d5a7783b3b3fd2250213a2e`)。

---

## 1. 根因 (逐字节定位)

标题走 `RSTextComponent::DrawTheString`, 其 jal 被 **GR_ZH61** 挂钩到 tail-cave `0x565900`
(提交 `0bcbeb34`, `work/zh16b/subagent_l1panel3/build_zh61.py`):

```
0x21C624  jal 0x219EB0 (DrawString)  →  j 0x565900          ← 挂点 (ZH82 实测 08159640, 在役 ✓)
0x565900  lbu   $at, 0x9C($s1)        ; 组件 fontID (标题档 = 5)
0x565904  addiu $t4, $zero, 5
0x565908  bne   $at, $t4, +2          ; 非标题档跳过补偿
0x56590C  nop
0x565910  addiu $a3, $a3, 7           ; ★ 标题 y +7  (居中量)
0x565914  nop
0x565918  lui/ori $at, 0x21C62C ; move $ra,$at   ; 伪 RA = jal 的返回点
0x565924  lui/ori $at, 0x219EB0 ; jr $at         ; 尾跳 DrawString
0x565930  sw $t0,0x10(sp)             ; ← 尾跳延迟槽, 已被 ZH76 cave 占用 (勿动!)
```

**唯一的改动面就是 `0x565910`**:

| 版本 | `0x565910` | 语义 | 子界面标题 |
|---|---|---|---|
| EN 原盘 | `00000000` | 死零填充 (无此 cave) | 用 26px 行盒字形, 墨迹 y24.5-44 |
| ZH61 … ZH82 (原始) | `24E70007` | `$a3 += 7` (**用户认证的垂直居中**) | 墨迹 y24.5-38.9 |
| ZH85 (回退) | `00000000` | NOP | 墨迹 y18.4-31.7 → **上偏 7px** |
| **ZH82_T (本补丁)** | **`24E70007`** | `$a3 += 7` | **墨迹 y24.5-38.9 ✓** |

**全仓只有一个脚本改过这个词**: `grep -r '565910'` ⇒ 仅 `tools/iso_build/patch_zh85.py`
(`0x24E70007 → 0x00000000`)。⇒ 现役盘 GR_ZH82 的 `0x565910 = 0` 是 ZH85 的回退残留,
**不是 ZH82 原始状态**; 还原 +7 即回到 ZH61..ZH82 的原始 (用户认证) 形态。

**ZH85 判据为何错**: 它用 drawlog 的**笔位**比对 (EN y=18 / ZH y=25 ⇒ 判"ZH 偏低 7px"),
但 EN 的笔位 18 之后还有 **26px 行盒的上留白**, 其**墨迹实际从 y24.5 起**; 中文 16px 满格
字库墨迹自笔位 +0 起画 ⇒ 同一笔位下中文墨迹天然高 ~7px, +7 只是把两者**墨迹顶缘对齐**。
(佐证: `GR_ZH61` 提交信息实测 "EN y24-42 / ZH(无补偿) y18-31, 偏高 7.5px"。)

---

## 2. 实机实测 (gsrunner, 三盘同 nav 同帧, `tools/capture/navTACe.txt`, 13000 帧 / snap 100)

**标题条几何** (无文字列 x[150..330] 逐行均值实测, 三盘一致):
上黑边 y14.4-17.4, **条体 y20.0-46.5 (几何中心 33.2)**, 下黑边 y47.2-49.2。

| 帧 | 界面 (标题) | EN 原盘墨迹 | ZH82 修改前 | ZH82_T 修改后 | 位移 |
|---|---|---|---|---|---|
| f6000 | 选择文件 / File Select | y23.5-44.0 (质心 34.88) | y18.4-31.7 (25.36) | **y24.5-38.9 (31.85)** | +7.0 |
| f8300 | 战术演习 / Tactical Exercises | y24.5-44.0 (35.56) | y18.4-31.7 (24.78) | **y24.5-38.9 (31.62)** | +7.0 |
| f9800 | 简介 / Briefing | y23.5-49.1 (35.41) | y18.4-31.7 (25.42) | **y24.5-38.9 (31.68)** | +7.0 |
| f10800 | 小队设置 / Platoon Setup | y23.5-48.1 (35.38) | y18.4-31.7 (24.94) | **y24.5-38.9 (31.53)** | +7.0 |
| f11200 | 小队设置 (同上) | y23.5-48.1 (35.38) | y18.4-31.7 (24.94) | **y24.5-38.9 (31.53)** | +7.0 |

- **修改前**: 墨迹顶缘 18.4 **已经骑进上黑边 (18.5)** = 用户所见"贴顶/上偏";
- **修改后**: 墨迹顶缘 24.5 **与 EN 原盘逐 0.0px 对齐**; 16px 字格 y25.0-41.0 在条体
  (20.0-46.5) 内**上距 5.0 / 下距 5.5 = 垂直居中** (EN 字形格上距 5 / 下距 2.5,
  其墨迹中心 34.25 偏条体中心 +1.05, 属原版 26px 行盒的基线效应)。
- 证据文件:
  - 对照图 `work/archive/cmp/GR_ZH82_T_title_montage.png` (4 屏 × EN|ZH82|ZH82_T 标题条 3 倍放大)
  - 对照图 `work/archive/cmp/GR_ZH82_T_title_EN_vs_ZH82_vs_T.png`
  - 原始量测 `work/builds/GR_ZH82_T/evidence/r26_title_cmp.txt`
  - 三盘转储 `work/builds/{GR_EN_ORIG/temp/dump_T1en, GR_ZH82/temp/dump_T1zh82, GR_ZH82_T/temp/dump_T1t}`

**回归 (ZH82 vs ZH82_T 全 127 帧逐像素)**: 有差异 76 帧, **差异 bbox 全部落在
x[30..90] y[16..38] = 左上角标题文字区**; 其余 51 帧逐像素全等, 主菜单/列表/金框/帮助条/
简报/游戏内 HUD 零改动 (bne 门 `fontID==5` 之外逐位不变)。

## 3. 铁律核对

| 检查 | 结果 |
|---|---|
| `r23_audit_inventory.py GR_ZH82_T.iso` | **解析 44 条, 在役 43, 缺失 0, 其它 1** (与现役盘 GR_ZH82 完全一致; "其它 1" = `0x21AC90` 记载 ZH57 值 `08158E00`、现役为 ZH58 迁址值 `0815959C`, 文档级已知差异) |
| `0x21D940` (用户认证 K=21) | `2462FFEB` **未动** (脚本内硬断言) |
| `0x4176A0` (用户认证 CAVE16=16) | `24020010` **未动** (脚本内硬断言) |
| `0x565930` (ZH76 cave 首词) | `AFA80010` **未动** (脚本内硬断言) |
| 全盘差异 | **仅 3 字节** = `0x4F9190-0x4F9193` (VA 0x565910 词), 白名单断言 |
| 尺寸 | 1,648,164,864 B 不变; 只打补丁, 未重建 ISO |
| EMU | ZH82_T 同 nav 13000 帧 `exit=0`, 进游戏正常 |

## 4. 复现

```powershell
# 1) 打补丁 (基底 = 现役盘 GR_ZH82)
python tools/iso_build/patch_zh_title_center.py `
  work/builds/GR_ZH82/GR_ZH82.iso work/builds/GR_ZH82_T/GR_ZH82_T.iso
# 2) 审计 (必须缺失 0)
python work/_dis/r23_audit_inventory.py work/builds/GR_ZH82_T/GR_ZH82_T.iso
# 3) 实机帧
$env:GR_ISO='...\work\builds\GR_ZH82_T\GR_ZH82_T.iso'
python tools/capture/run_opt.py T1t navTACe.txt 13000 100
python work/_dis/r26_title_cmp.py 6000 8300 9800 10800     # 三盘同帧墨迹对照
python work/_dis/r26_regress.py                            # ZH82 vs ZH82_T 全帧回归
```

> 注: `make_build.py` 的版本名正则为 `GR_ZH<数字>`, 不接受 `GR_ZH82_T`, 故本盘按
> make_build 的同流程手工组装 (mkdir + 以 `<src> <dst>` 调用补丁脚本) 并写入
> `work/builds/GR_ZH82_T/build_info.json`。未改动 make_build.py。

## 5. 建议的 PATCH_INVENTORY 增量行 (待 Lead 决定是否并入总账)

> 未直接写入 `docs/PATCH_INVENTORY.md`: 该表是 `r23_audit_inventory.py` 的**唯一判据源**,
> 加行会让**现役盘 GR_ZH82** 立即变成 "缺失 1 条" (它本来就缺这个词), 影响 Lead 的
> 基线审计口径。建议在 GR_ZH82_T 升为现役盘时一并加入:

```markdown
| 0x565910 | 00000000 | 24E70007 | 子界面标题垂直居中 (ZH61 cave, fontID==5 时 a3+=7) | ZH61 / 还原于 GR_ZH82_T | ✔ 在役 |
```

## 6. 已知影响面 / 遗留 (需用户知晓)

- 该 cave 的门是 `comp[0x9C] == 5` (标题档), **覆盖面 = 全部"页面大标题族"**:
  文件选择/战术演习/简介/小队设置 等全部子界面标题 (本轮已 4 屏实测), 以及
  **特别收录各内页的大标题** (ZH85 当初就是为它们做的回退)。
- ⇒ 还原后, 特别收录内页大标题会**比 ZH84/85 状态低 7px**, 回到 ZH61..ZH82 的原始形态
  (墨迹顶缘与 EN 一致)。若用户仍认为 SF 内页标题需要单独下移 0px, 需要为"SF 内页"找
  一个**区分判据** (该屏标题组件与通用子界面标题模板实测同参: W=400 H=16 ax=33 ay=18
  `comp[0x1C]=1 comp[0x9C]=5`), 需先取 SF 内页的 EE RAM 转储另立条件分支 —— 本轮未做。
- 尾跳延迟槽 `0x565930` 现被 **ZH76 cave 首词** (`sw $t0,0x10(sp)`) 占用 (ZH61 时代是 nop),
  这是 ZH61 之后、本轮之前就存在的既成事实: **改它等于拆 ZH76**, 故本补丁只动 `0x565910`,
  保持该现状不变。
