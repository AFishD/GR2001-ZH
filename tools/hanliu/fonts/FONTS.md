# fonts/ — 字体资产说明（只记录路径与授权注记，不复制字体文件本体）

## 当前采用：SimHei（中易黑体）

| 项 | 内容 |
|---|---|
| 本机路径 | `D:\Document\Fonts\SimHei.ttf`（TrueType，10,044,356B，内嵌 EBDT 点阵 strike） |
| 取形方式 | PIL `ImageFont.truetype(..., 16).getmask(ch, mode='L')` 直接取 **16px 原厂点阵 strike**（非轮廓渲染），阈值 >128 → 墨(0)，其余 → 底色(31) |
| 使用历史 | ZH5（16px 89 字，40000 帧 PASS）→ ZH6（16/18/20px 混合宽度修复 回/队）→ ZH7（157 对字 16px，40000 帧 PASS）；example_zh7 亦用它复现出逐字节一致产物 |
| 质量注记 | 16px strike 在经引擎 0.8 缩放 + glow 后会糊（ZH5 的 回 字教训）；关键笔画少的字用 18/20px 混合宽度可修（ZH6 配方，见 layout_zh5.txt/charset_zh6.json 与 han_v2\RES_AB_TEST.md §十一） |
| 授权注记 | SimHei 版权归北京中易电子（Microsoft Windows 简体中文版随附字体）。**仅限本机本地取形生成自有点阵，不得把 TTF 文件本身打包分发**；生成的字形位图归游戏补丁自行斟酌（汉化补丁惯例，非法律意见） |

## 备选：Zpix（最像素）

| 项 | 内容 |
|---|---|
| 选型结论 | 12/24px 原生网格（tmp\fonts_test\ 实测）；12px 与引擎 default 行带更配，但本次工程最终未采用 |
| 授权注记 | Zpix 由 SolidZORO 发布，**个人使用免费、商用需授权**（详见其仓库 LICENSE）；若成品补丁公开分发，需确认授权范围 |

## 字表/布局数据（本目录附带的历史定版）

| 文件 | 说明 |
|---|---|
| `charset_zh6.json` | ZH6 单字节 89 字码表（codes: 字→0xA1..0xFE 码位；含 3 标记字 役/有/下）+ 76 条译文 |
| `charset_v5.json` | ZH5 字符集定版记录 |
| `layout_zh5.txt` | ZH5 逐格布局（code/char/row/slot_x/矩形）——单字节保守路线参考 |
| `layout_dbcs.txt` | ZH7 逐格布局（idx 224-383 每格 rec 矩形 + 标记字对 381-383 复用说明）——DBCS 路线参考 |

## 工程约束速记（详见 HANIZATION_MANUAL.md §三）

- 可用单字节码位 = 0xA1..0xFE 减去 EN 保护区 {0xAE ®, 0xB1 ±, 0xB5 µ, 0xE7 ç, 0xF1 ñ}
  与 0xFF 毒槽；0xA1..0xA3 在 DBCS 补丁(SLUS_P_U)下作 lead 标记码（役/有/下 一律以对编码）。
- 新格绘制 u0 = x-20 ≥ 1（0xA1 码位诅咒：u0=0 的记录被引擎渲染冻结）。
- 采样矩形 = (u0+20, v0)-(u1+20, v1)，u 恒 +20；adv 单位 1/256 px（16px 字 adv=0x1000=16.00）。
- atlas 背景 31=透明、笔画 0=实心（引擎反向 alpha）；换字体只需改 `font_build.py --ttf --size`。
