# 构筑版本差异说明

现役盘 = **GR_ZH68** (work/builds/GR_ZH68, sha256 见 build_info.json)。
每版的完整工作区在对应版本分支 `archive/GR_ZHxx`; 更早 (ZH7–ZH35) 见 `archive/early-builds`
+ 归档 PROGRESS (archive/GR_ZH36 时代 work/zh16b/PROGRESS.md)。

| 版本 | 锚点分支 | 关键差异 (相对前版) |
|---|---|---|
| GR_ZH36 | archive/GR_ZH36 | 16px 完美盘: 字库 X0=4 链 (gen_font16_zh34→v22 8 段封装) + V23 ELF; 菜单/帮助条/对话框 Y 居中, ▲▼ 滚动指示, EN 带基线 |
| GR_ZH37E | archive/GR_ZH37E | 菜单乱码收口: CharWidth cave 13px 遗产破案 (ZH37E = ZH36 + 1B) |
| GR_ZH40 | archive/GR_ZH40 | 用户模拟器对照计量定案 (偏移双成分) + Y 居中 cave 0x21D940 参数化 K |
| GR_ZH43 | archive/GR_ZH43 | ELF 世系归拢 → SLUS_P_V43 (8 补丁词 + 0x5182EC nop) |
| GR_ZH49 | archive/GR_ZH49 | 简报页黑屏根治 5 字节 (0x5182EC 恢复原词 + 字库节点 NLOOP 0x40→0x04) |
| GR_ZH53 | archive/GR_ZH53 | 字库最近邻全链修复 (TEX1 站点) + 四项偏移修正 |
| GR_ZH54 | archive/GR_ZH54 | 脏像素复发 / 读卡下移 / 残余上移 三连修 |
| GR_ZH55 | archive/GR_ZH55 | 过滤层退回 ZH50 集 (修地图锯齿回归) |
| GR_ZH56 | archive/GR_ZH56 | "!find key" 破案 (MENU.IMG EN_STRINGS.TXT 条目还原) |
| GR_ZH57 | archive/GR_ZH57 | 对话框长行居中 (SWKERN) + L1 面板标签对齐 + 物品名中文 |
| GR_ZH58 | archive/GR_ZH58 | ZH57 视频后卡死修复 (SWKERN cave 迁址 0x565670) |
| GR_ZH59 | archive/GR_ZH59 | L1 面板 A/B 图标上移 3px + 对话框机制收窄 |
| GR_ZH60 | archive/GR_ZH60 | L1 按键行横向均匀分布 |
| GR_ZH61 | archive/GR_ZH61 | 子界面标题垂直居中 (fontID=5 条件 tail-cave @0x565900) |
| GR_ZH62 | archive/GR_ZH62 | 战术演习简报目标行"下沉"补偿: NTSC_IKE.RES OBJ0-3 记录 H 31→26 (draw-y 对齐 EN); PROCEED 记录明确不动 |
| GR_ZH63 | archive/GR_ZH63 | 读卡对话框修复 (用户 2026-10-02 报障): ① SWKERN cave 0x5656C8 trail 极性反转 1B (beq→bne) — 修复以来一直失效的 CJK 逐行居中 (kern 按字形计数); ② G58.I797 译文重写 (去括注+多余空格, 断句不再拆散括号组), MENU+GR 双份 RES |
| GR_ZH64 | archive/GR_ZH64 | 缩放读数条倍数标签修复 (原版字形方案): EN 原版 large 面 ASCII 恢复 — **用户实测否决 (显示效果差), 归档不推荐** |
| GR_ZH65 | archive/GR_ZH65 | EN 带方案改向 (用户定案): ASCII 改用方正像素16 同款渲染 — 位置仍高 2px, 被 ZH66 取代 |
| GR_ZH66 | archive/GR_ZH66 | ASCII 采样窗顶部留空 2 行 (记录 v 450,466; 用户 leading 理论证实): 全 ASCII 下移 2px 补回 EN 式行盒留白; ×4 顶与 EN 精确对齐 |
| GR_ZH67 | archive/GR_ZH67 | 帮助条垂直居中 (§五.7 身份收口: style-0x52 滚动说明组件): ELF 手术 cave 0x565730, y+2 仅 0x52 族 — +2 不足 (按钮行误测), 被 ZH68 取代 |
| GR_ZH68 | (main 现役) | 帮助条 +4 精校 (双盘差分定靶): EN 墨心 392.5, ZH68 [387,398] 心 392.5 精确一致; 手术常量 1 词 +2→+4 |

## 构筑清理 (2026-10-03/04)
- 中间构筑 GR_ZH63/64/65/66/67 已删 (18.6G→3.3G; 全部可经 git 补丁链重建);
  保留 GR_ZH62 (基底) / GR_ZH68 (现役) / GR_EN_ORIG (EN 基线)。
- **合并补丁 `tools/iso_build/patch_zh68_all.py`**: ZH62 → ZH68 终态一步到位
  (= ①SWKERN + ②I797双RES + ③EN带像素16 + ④帮助条手术y+4), 与增量链构筑
  **逐字节相等** (sha256 240b149f… 验证)。
- 各轮对比图证据: work/builds/GR_ZH68/temp/cmp/ (9 张)。

## 数据面构成 (ZH68)
- MENU.IMG: FONT.RES 字表槽 @0xB9120 (4421B, fld26 + ASCII 记录指向像素16 新带) + new_font_revised
  字库记录 @0x58431 (0x4044C, 1024×512 PSMT4, 8 段 GIF + 行移位 + 像素16 EN 带 @v452-467, ASCII 记录 v=(450,466) 顶部留空 2 行)
  + EN_STRINGS.RES #25 @0x377E000 (I797 重编码, 32,365B+零填, 条目表不动)
  ⚠ 字库链 89B 重放基线自 ZH64 起不适用于 EN 带 (重铺逻辑待并入 build_font.py)
- GR.IMG: EN_STRINGS.RES #902 @0xCAC1750 (I797 同步, 32,366B+零填)
- NTSC_IKE.RES: OBJ0-3 行记录 H=26 (round22 下沉补偿)
- ELF (SLUS_P_V43 谱系 + SWKERN 1B): 全部补丁逐字记录于 docs/PATCH_INVENTORY.md
