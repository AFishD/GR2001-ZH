# -*- coding: utf-8 -*-
r"""patch_zh_sf_spaces_all.py — 「特别收录」各内页介绍文本: 删除全部**行内可见的多余半角空格**

## 目标
`MENU.IMG #283 EN_SPECIAL_FEATURE.XML` 的 69 条 `<text>` 里, 由 zh84 轮"折行补空格"插入、
后被二轮重排错位成**行内**的 0x20 —— 引擎会把行内空格画成可见空隙。本补丁把**全部 N_DEL 处**
此类空格删掉, 且**逐条用引擎折行模型复算证明版式零变化**。

## 判定链(全部可复核, 生成脚本 work/_dis/r28_mkpatch.py)
1. 引擎口径解码 (DBCS lead 0xA1..0xAD, 其余单字节) + `RSHTML` 按 `{br}`/`{p}` **分段各自折行**;
2. `RSTextComponent::DoWordWrap` 模型 (wrapW=270, 汉字16/ASCII8): 每 token 扣 SW+1, 每个字面空格
   扣 SP, 断行时新行预算 = wrapW − SW(token) —— SP/模型形式用 **6 组实机渲染真值 33 行**标定
   (`work/_dis/r28_calib.py`: 只有 SP∈{6,7}(TRK=1) 全中; 集成取 SP∈{5,6,7,8});
3. 空格画在其前一 token 的行尾 ⇒ 只有「后一 token 首行 == 前一 token 末行」才是**行内可见**;
4. 逐字符溯源 `work/_dis/_xml82.txt`(zh84 reflow **之前**的台账): 可见空格里 881 处是 reflow 插入,
   849 处是原文排版(如「约 340 克」「C3 炸药」) ⇒ 只删"插入的"那些;
5. 逐处贪心复算: 删掉这处(并等量补尾)后, 对 **SP=5/6/7/8 每个模型**都必须满足「每段行数不变 +
   每个存活字符的 (段号,行号) 不变」; 做不到的 N_KEEP 处**保留不动**(清单见 _keep.md)。

## 写入方式(等长覆写)
每条 `<text>`: 删 N 个 0x20, 在**同一 `<text>` 内**补 N 个 0x20(最后一个含 token 段的末尾 ⇒
末行行尾 ⇒ 无墨迹) ⇒ XML 总长 116486 B 不变 ⇒ 8 个子流解压尺寸不变 ⇒ 子流边界不变
⇒ 其余字节逐字节不变。只重压"内容有变化"的子流; 未变的子流沿用原压缩字节。

## 自验(失败即 raise, 绝不写出可疑盘)
* 白名单逐处: 偏移落在该 `<text>` 体内 / 该字节就是 0x20 / 前置 6 字节 / 后置 6 字节全等;
* 折行复算: 每段行数不变 + 每个存活字符 (段,行) 不变;
* 字节环回: 无删除时重建体 == 原体 (证明字节级重建无损);
* 结构: `<text>/<studio>/<item>/<group>/</SpecialFeatures>` 计数 + 全部 name 属性逐字节不变;
* 等长: XML 总长不变; 子流 LZO 回环解压逐字节一致; 写入后从盘上回读 8 子流再比一次;
* 全盘: 槽前 + 槽后至盘尾逐字节不变(分块比对)。

用法: python patch_zh_sf_spaces_all.py <src_iso> <dst_iso> [info.json]
"""
import hashlib
import json
import os
import re
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
from lz77_decode import lzo1x_decompress                      # noqa: E402
from lzo1x_c import compress as lzo_compress                  # noqa: E402

MENU_LBA = 776286
TAB_OFF, TAB_STEP = 0x830, 48
XML_IDX = 283
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
XML_LEN = 116486                 # 现役/基线盘实测值 (断言)
LEAD_MAX = 0xAE
W_CJK, W_ASCII, TRACK, FP, WRAPW = 16, 8, 1, 4, 270
SP_ENSEMBLE = (5, 6, 7, 8)      # 标定后集成: 只 SP∈{6,7} 全中, 取 ±1 覆盖组合不确定度
TAG_RE = re.compile(r'\{(?:br|p)\}')
N_DEL = 792

# ── 白名单: 文档序 -> [(XML 绝对偏移, 前置 6 字节 hex, 后置 6 字节 hex), ...] ──
WHITELIST = {
    10: [   # Weapon / 定向地雷 (M18) (2 处)
        (0x3EEF, 'a5f8a5faa8cb', 'd3fca1eadba1'),
        (0x3F07, 'a3eea1a1a8cb', 'aabceba1afa1'),
    ],
    11: [   # Weapon / 定向炸药 (M2) (1 处)
        (0x405E, 'cbd4a4eaa4f5', 'a5b1a1e3a8d1'),
    ],
    12: [   # Weapon / 杀伤手雷 (M67) (2 处)
        (0x41A9, 'c0f020fca8cb', '35206d20a3f1'),
        (0x4216, 'bda3c2cca1e0', 'ebf0fca8cc3c'),
    ],
    13: [   # Weapon / M24 狙击步枪 (4 处)
        (0x431A, 'a1ef20e5a7ee', 'a5d4a8ccfad9'),
        (0x4331, 'a1efe520a8cb', 'a1b0c020372e'),
        (0x439F, 'a2bacbeca3d8', 'a3a4a7f6aaa7'),
        (0x43B0, 'acc2a1f5a9d0', 'a8cc3c2f7465'),
    ],
    14: [   # Weapon / L96A1 狙击步枪 (2 处)
        (0x44CA, 'a1ef20e5a8cb', 'a1b0c020372e'),
        (0x44EC, 'b6a1b0a1a5f7', 'a1bda8cb20a5'),
    ],
    15: [   # Weapon / SVD 狙击步枪 (3 处)
        (0x462C, 'eda2a4c6a1ef', 'e5a8cb20a1b0'),
        (0x4630, 'a1ef20e5a8cb', 'a1b0c020372e'),
        (0x4654, 'a5f7a1bda8cb', 'a5e0bf203130'),
    ],
    16: [   # Weapon / M82A1 反器材步枪 (4 处)
        (0x47A4, 'c6a1efe5a8cb', 'bfa8d3a6c4a2'),
        (0x47C1, 'a3ada2f0a4a5', 'afa3aca4c8a1'),
        (0x47DC, 'b0a1a5a1eaf7', 'a1bda8cb20a5'),
        (0x47E1, 'f720a1bda8cb', 'a5e0bf203130'),
    ],
    17: [   # Weapon / M16A2 突击步枪 (2 处)
        (0x4930, 'a4c6c0b6a8cb', 'a1b0c020352e'),
        (0x4954, 'a5f7a1bda8cb', 'a5e0bf203330'),
    ],
    19: [   # Weapon / OICW (8 处)
        (0x4C42, 'c5a5d1a1eabc', 'a4afa5baa5ea'),
        (0x4C5E, 'afa1abbea7ee', 'a5d4a8cc20fa'),
        (0x4C72, 'e6c4a1d0a8cd', 'c5a4b1cba1b0'),
        (0x4C81, '4d313620a7ee', 'a5d9a3c8b420'),
        (0x4C9E, '20a1efe5a8cb', 'd4a4e0c5a2a7'),
        (0x4CB7, 'e1bfa1b0c0be', 'a8cc20a1e1bf'),
        (0x4CEE, 'bfa3d9a1abbe', 'dba3d7a8cb20'),
        (0x4CF4, '20dba3d7a8cb', 'a5e0bf203620'),
    ],
    20: [   # Weapon / M4 短突击步枪 (2 处)
        (0x4E39, '20b7a6b0a8cb', 'e8b4a3a3204d'),
        (0x4E62, '34356d6d20e5', 'bfa8cc20a1d6'),
    ],
    21: [   # Weapon / SA-80 突击步枪 (1 处)
        (0x4FF5, '6d20e5bfa8cc', 'c0f0cbb4a1f2'),
    ],
    22: [   # Weapon / MP5 冲锋枪 (4 处)
        (0x5134, 'acadade5a8cc', 'a1d620333020'),
        (0x514A, 'f2a9c2a1a5ec', 'a1b5a1cea5b4'),
        (0x515B, 'eda2a4c6a8d1', '3320a1b0a1dd'),
        (0x5171, 'a2e7a2c0a8cc', '4d503520a1f0'),
    ],
    23: [   # Weapon / MP5SD 微声冲锋枪 (3 处)
        (0x52B5, 'acadade5a8cb', 'a1b0c020396d'),
        (0x52D5, 'bfa8d3a3a3c5', 'a2bca2c0a3e7'),
        (0x52F0, 'c3b8aab6aac4', 'a5dca2afaad2'),
    ],
    24: [   # Weapon / M249 班用机枪 (3 处)
        (0x549B, 'f9abfaaadaaf', 'd9e8b4203230'),
        (0x54AE, 'd4a7a5bfa8cc', 'a5a9e5a5dcfb'),
        (0x54C6, 'a3a4a5d1c0b6', 'a2e7a2c0a8cc'),
    ],
    25: [   # Weapon / MG3 通用机枪 (3 处)
        (0x55FC, '20a7a5bfa8cb', 'a2a8fbe1a1ab'),
        (0x5648, 'faaada20a8cc', 'a2bee4f7a3d7'),
        (0x5658, 'f6aaa7dba8cb', 'a2f3e5a1c4a7'),
    ],
    26: [   # Weapon / RPK74 轻机枪 (4 处)
        (0x578B, 'a2bea8aea2be', 'a1c4a8cb20cb'),
        (0x57A1, 'a3ccaaaea8cc', 'a3a320414b2d'),
        (0x57C8, '6d20e5bfa8cc', 'a1f2a9c2a1a5'),
        (0x57D5, 'cbeca1b5a1ce', 'a5b4a8d120a9'),
    ],
    27: [   # Weapon / M9 手枪 (2 处)
        (0x58F9, 'a2c0f0e5a8cb', 'a1cd20396d6d'),
        (0x5916, '3520a1b0a8cc', 'faa3e1a2f1a1'),
    ],
    28: [   # Weapon / M9SD 微声手枪 (6 处)
        (0x5A39, 'c0f020e5a8cb', 'c0b6a3f7a2aa'),
        (0x5A44, 'a2aaf9b7a8cc', 'a4f4a4c0a8cb'),
        (0x5A58, 'e8b4a5d7a2aa', 'a1fabfa8d3a8'),
        (0x5A81, 'a3dbaab4a8cb', 'a2c5bcdea3ec'),
        (0x5A98, 'e5a3f7a7baaf', 'a2bfa2eba8cb'),
        (0x5AB3, 'aca4c8afa1a4', 'b4a1ab20bea8'),
    ],
    29: [   # Weapon / M136 火箭筒 (7 处)
        (0x5BCF, 'a7eea5d4a8cb', 'a1b0c0203834'),
        (0x5BF0, 'ade4a3ada2f0', 'a4a5a8cc20a3'),
        (0x5BF5, 'f020a4a5a8cc', 'a3c9a3adbfcb'),
        (0x5C0C, '20e4a3ada8cc', 'a1cba3c9a3ad'),
        (0x5C18, 'adbfa4c0a8cb', '4d31333620a2'),
        (0x5C3D, 'fda9f9bfa8cb', 'a5abd4b6a4fd'),
        (0x5C6A, '31333620e4fb', 'a1f5caa1f1a8'),
    ],
    30: [   # Weapon / Groza 突击步枪 (4 处)
        (0x5DA7, 'a3d7a3fba5d1', 'a3d7c1efa2a5'),
        (0x5DCD, 'acbfa2f5a8cd', 'a2b6b6a1efe5'),
        (0x5DE1, 'b6a1efe5a8d1', 'abfda3f7a2b6'),
        (0x5E2E, 'a2f5a8d6a8cc', 'a5a9e5a1b0c0'),
    ],
    31: [   # Weapon / AN-94 突击步枪 (2 处)
        (0x5F7B, 'a2bba4aba8cd', '3138303020a1'),
        (0x5F8D, 'a3a4a1b0a1dd', 'c0a2e7a2c0a8'),
    ],
    32: [   # Weapon / Bizon 冲锋枪 (9mm) (3 处)
        (0x6113, 'c0a7acadade5', 'a8cc20fad420'),
        (0x6116, 'adade520a8cc', 'fad420414b2d'),
        (0x6155, 'a9aaa1e6a5cb', 'a6b8a8cc3c2f'),
    ],
    33: [   # Weapon / 9A-91 短突击步枪 (3 处)
        (0x6272, 'a1ef20e5a8cc', 'e5a6b3a5aea9'),
        (0x629D, 'fafba2e0a8cc', 'a1d620397833'),
        (0x62B1, 'aaa1fabfa8d3', 'efa2a5b4a3d9'),
    ],
    34: [   # Weapon / M60 机枪 (1 处)
        (0x6453, 'aabca2f1a2bb', 'a8cc3c2f7465'),
    ],
    35: [   # Weapon / FN-FAL 步枪 (短型) (2 处)
        (0x6568, 'b6a1efe5a8cb', 'd920323020a6'),
        (0x65EC, 'f7bca4c0a8cc', '5061726120a1'),
    ],
    36: [   # Weapon / PSG-1 狙击步枪 (2 处)
        (0x675B, 'a2e1adb7a8cc', '5053472d3120'),
        (0x676E, 'fea2edb6a1ef', 'e522a8cb20a1'),
    ],
    37: [   # Weapon / M98 狙击步枪 (1 处)
        (0x68DC, 'a5d6a2e0afe5', 'a4bea1b9e3be'),
    ],
    38: [   # Weapon / PKM 通用机枪 (3 处)
        (0x6A37, 'b7caa2f5a8cc', 'facba1b0c0ab'),
        (0x6A50, 'e2a4efa2cebf', 'a1f8a3daa5d1'),
        (0x6A6E, 'b6e2a6e3a9a2', 'a5e0a7d1a8cb'),
    ],
    39: [   # Weapon / 测距望远镜 (AN/GVS-5) (1 处)
        (0x6BE5, 'cfdba7eea5d4', 'a2f3a1c4a7ef'),
    ],
    40: [   # Weapon / 传感器 (AN/GSQ-187) (4 处)
        (0x6D90, 'a2bda2c1a8cb', 'a2aba1c9a2e1'),
        (0x6DAB, 'afa3bfdda8d1', 'a1faa2ace2a1'),
        (0x6DC6, 'a5a1a1a5a8cc', 'faabafa7f8a2'),
        (0x6DE0, 'e6a1e6a8a9bd', 'a1f9afd9a2d2'),
    ],
    43: [   # Awards / 国会最高勋章 (2 处)
        (0x7FF9, 'a1e5c6d6a8cb', 'a7eda2ebd4d1'),
        (0x8013, 'a3a9a4f4a7b3', 'a6b2a8cd7b62'),
    ],
    44: [   # Awards / 优异服役十字勋章 (6 处)
        (0x817E, 'a1e5c6d6a8cb', 'a7eda2ebd4d1'),
        (0x8198, 'a3a9a4f4a7b3', 'a6b2a8cd7b62'),
        (0x8200, 'a2fca4dea8d1', 'a2c5a2baa3fa'),
        (0x8219, 'b3a6b2e6caaf', 'a3f6a2b3a8cc'),
        (0x8237, 'cda2b6cda8cb', 'a2ababd7a4fb'),
        (0x8251, 'a4dfa5b4a8cb', 'e8a1d6a1eba8'),
    ],
    45: [   # Awards / 银星勋章 (3 处)
        (0x82E6, 'a1e5c6d6a8cb', 'a7eda2ebd4d1'),
        (0x8300, 'a3a9a4f4a7b3', 'a6b2a8cd7b62'),
        (0x8399, 'cdaaae20a8d1', 'baa4decdaae2'),
    ],
    46: [   # Awards / 战功星章 (3 处)
        (0x8429, 'a1e5c6d6a8cb', 'a7eda2ebd4d1'),
        (0x8443, 'a3a9a4f4a7b3', 'a6b2a8cd7b62'),
        (0x84C5, 'b2afe6caa8cb', 'a2c5a2d0a3b6'),
    ],
    47: [   # Awards / 战伤勋章 (3 处)
        (0x8566, 'a1e5c6d6a8cb', 'dac9a7d3a1d5'),
        (0x8580, 'f6a2b3cba6b5', 'a3a9baa3eea7'),
        (0x859D, 'f4a3dfc3a2b0', 'a9b1a1aca8cb'),
    ],
    48: [   # Awards / 步兵战斗章 (CIB) (6 处)
        (0x863E, 'a1e5c6d6a8cb', 'abe2a2bea1f9'),
        (0x8656, 'c2cba6b5a3a9', 'a1efa2b3bad8'),
        (0x868E, 'a6c4aba6a8cc', 'a6b5a5fea5eb'),
        (0x86AB, 'a3fba5d1a3d7', 'c1a2c9acebda'),
        (0x86C5, 'd9a1a9a1bdc3', 'a2b0a2bbd1a8'),
        (0x86E1, 'a3a3a1a9ead0', 'a1e5d3c820ba'),
    ],
    50: [   # SpecialistProfile / 斯通 (19 处)
        (0x898A, 'aabcacf7a8cb', 'eda5a1d9a2eb'),
        (0x899B, 'a4a8a2f8a8cc', '227b707da2bc'),
        (0x8AA0, 'd4a5dfeaa8cc', 'a2f3a1c8a5b6'),
        (0x8AB2, 'a3d3a3a9a8cb', 'a2b2a1c3a1f9'),
        (0x8ACC, 'a1bca4cea2b9', 'abcea1aea6b7'),
        (0x8B38, 'b620c2b3a8cc', '3230303020a2'),
        (0x8B84, 'a7aad6baa8cc', '3230303320a2'),
        (0x8B9E, 'f0f5b6c1a7a7', 'a6b5a8cb2031'),
        (0x8BBE, 'a1cca8d5a8cb', 'a1efa1e52034'),
        (0x8BD6, 'dfd3a1bea8cc', '3230303520a2'),
        (0x8BEF, 'a1daaabba4b6', 'a1a7a6a7a5cf'),
        (0x8C1C, 'ead9a2edb6f0', 'afa3c3a5eaa3'),
        (0x8C39, 'acf8a4a1a5ef', 'e2a1d4a5efa8'),
        (0x8C56, 'acf8a3a9a7df', 'a3a6a8cb20a5'),
        (0x8C75, 'b6a2a4d2a8cc', 'a1b2a3a32054'),
        (0x8D08, 'a7e5a6a4a3e4', 'a1b6a2f8b4a2'),
        (0x8D33, 'a2e9aac4a9e3', 'abaaa8cb20a2'),
        (0x8D57, 'a9a1f920a1b2', 'abdaacf3afa8'),
        (0x8D73, 'c5d9a1b220bc', 'a6a7a5cfb7c1'),
    ],
    51: [   # SpecialistProfile / 奥萨泽 (19 处)
        (0x8F76, 'e3a8dfa9b7e2', 'a5dfaf20476f'),
        (0x8FB4, '20a6f929a2ca', 'd9a9d5a8f9a7'),
        (0x8FD2, 'a5d7a9d1a2fc', 'dbde20a6fbab'),
        (0x8FF0, 'a4aca9f3a9dc', 'a7dfa1c020a5'),
        (0x9027, 'dfa1c5a1f9f0', 'a8cc20a4afa5'),
        (0x9048, 'c6a1b6baa8cc', 'a2baaba5bca8'),
        (0x910C, 'f5d3abfea4c7', 'a9cba7e0a8cb'),
        (0x9148, 'adeaa1d8a3e0', 'afabccabc7ea'),
        (0x9161, 'a7d8a1a9a8cc', 'a3a4a5a3a2ca'),
        (0x917C, 'd1e1a9d1a2fc', 'afa3a1a1c7d6'),
        (0x9199, 'a2eca6f7a6bf', 'a5d7afabfea4'),
        (0x91D1, 'a2f1a7ada1f0', 'aae2a3daa2a4'),
        (0x91EC, 'c5e5a6d2a8cb', 'eda2cca9daa9'),
        (0x9246, 'aacfa7eca8cc', 'abcfa2c1b8a8'),
        (0x9275, 'a3e5d9c5a2c9', 'a1eaa2e1afa2'),
        (0x929F, 'efdea2f6a8cb', 'a2c5d0a1efa9'),
        (0x92BC, 'a1a1a9d5a6af', 'a8cba1b2afab'),
        (0x92CC, 'de20a3daa8cb', 'cbfbeadea5d0'),
        (0x930F, 'acd2a2f6a8cd', 'a5eaa5df2072'),
    ],
    52: [   # SpecialistProfile / 格雷 (19 处)
        (0x940B, 'a3b6a4c5a8cb', 'a9b2a6aaa1fc'),
        (0x9420, 'aacba1ada8cc', 'a3c8bca4cba3'),
        (0x9435, 'aaafaad1a8cc', '227b707da2bc'),
        (0x9545, 'a3a9a5c3a9a2', 'a7d6a8cc2031'),
        (0x9570, '6f737461a8cc', 'd6a1bcb8abe2'),
        (0x95B0, 'a1f8a4cea8cc', 'a6b5a3a92047'),
        (0x95C4, 'a3aca5bca1bc', 'a5b320373525'),
        (0x9630, 'a3c8a2dea8cc', 'a3f0a1e6a3d8'),
        (0x965C, '35313320a3df', 'a9daa7cda3b5'),
        (0x9669, 'a2f4a3bfa8cc', '3139393920a2'),
        (0x967E, 'd7c1ecd6a8cc', '3230303420a2'),
        (0x979C, 'a2dea1f9a3f9', 'a8d120abcbea'),
        (0x97BC, 'a2f3a3d7a4c7', 'a2b0a2cabcab'),
        (0x97D5, 'a1f9fbb8a1aa', 'a3e0eaafa1f9'),
        (0x97EF, 'f9a1e6afa1e4', 'a2a3a8cc20a5'),
        (0x9850, 'abf4a3b9a8cb', 'dea6b3a2a4a8'),
        (0x986B, 'a8a4a8a3a8cc', 'a2ecfcafa7a6'),
        (0x9886, 'a2caccc5a1dd', 'a8cbaabcaade'),
        (0x9898, 'a4bea2aaa8cc', 'a2ecfca3fba3'),
    ],
    53: [   # SpecialistProfile / 汉克尔 (28 处)
        (0x99A0, 'a3a9a7d8a8cc', 'a1f8b0a4c8a4'),
        (0x99B8, 'a2eea1bfa8cb', 'a1fda1aca8f5'),
        (0x99C3, 'a8f5a6aaa8cc', '227b707da2bc'),
        (0x9A86, 'a6d6a1eaabfa', 'afa9cca1ad20'),
        (0x9AE3, '29a2cabca3e4', 'd3afabbaa8ab'),
        (0x9B15, 'a4c1a1e6a8cc', 'bc20456d6465'),
        (0x9B86, 'a1a7a6c7a5df', 'a5dfa8afa3df'),
        (0x9B9B, 'a3c9c2b3a8cc', 'f2a5eda2eba5'),
        (0x9BB4, 'a1dba2dea8cb', 'dba1aca4b6a1'),
        (0x9BC7, 'df20a5bba8cc', '3230303320a2'),
        (0x9C19, 'dea2c8c5a2cc', 'a9daafa3d3fb'),
        (0x9C35, 'a1aec6f0a8cc', 'e2a2d2a9abde'),
        (0x9C51, 'bca1b6cea9b2', 'a6bacda9cea6'),
        (0x9C6F, 'a3c1a2f6a2bb', 'dbafa3dbaab4'),
        (0x9C8A, 'aaa5abafa3c3', 'a5eaa1c2a6fc'),
        (0x9CAA, 'a5e8a1eaa3c1', 'a2f6a1ada8cb'),
        (0x9CBE, 'd9d2a4f4a8cc', 'eda5d1a2a8a3'),
        (0x9CD8, 'a3afa1e9c1e9', 'a9b3dea2a4bc'),
        (0x9CF0, 'a6fba1ada8cb', 'a9b2a6baa7cf'),
        (0x9D08, 'a4b2a2aaa8cc', 'fbc5a4c1a1b2'),
        (0x9D2E, 'aca9a4c7a8cc', 'a1b2acf8a6c7'),
        (0x9D4D, 'a4bea2aaa8cb', 'd9c1cea8a3a1'),
        (0x9D62, 'eaa2bbc5a8cb', 'dea1f9a6d6a2'),
        (0x9D78, 'a9f1a6baa8cc', 'a9e8a2c6a8d4'),
        (0x9DAA, 'a2b5a6b2a8cb', 'aad2a2a4a8ec'),
        (0x9DD7, 'b8a4a2d7a8cb', 'a5a3a2c0a3d2'),
        (0x9DEF, 'c4f9a2f6a8cb', 'fbeaa4c8a6f1'),
        (0x9E16, 'adafa8aea8a4', 'a8cc3c2f7465'),
    ],
    54: [   # SpecialistProfile / 亚各布斯 (26 处)
        (0x9EEF, 'a1ada2b1a8d0', 'a1ccd5a1ada8'),
        (0x9F17, 'abc7a3b6a8cc', 'a4cca7e8a1ad'),
        (0x9F22, 'a1ada2b1a8d0', '227b707da2bc'),
        (0xA01B, 'aad1a9daa8cb', 'da204d617279'),
        (0xA034, 'b3a6ede9a8cb', 'a3e4a1ada3a4'),
        (0xA05B, 'a1c2a6b3a8cb', '3230303220a2'),
        (0xA06A, 'b1a6f929a8cc', 'a1b2d9a5a3a2'),
        (0xA074, 'a5a3a2dda8cb', 'd1c8a2bafb20'),
        (0xA0A3, 'e5a4ce29a8cc', 'a4ada1ad2034'),
        (0xA0C4, 'a1c2a2b0a8cb', '3139393220a2'),
        (0xA0E1, '3220a3bfa8cb', 'a1f02043696e'),
        (0xA106, 'a5a2a1ada8cb', 'd0a8daa1dda3'),
        (0xA11E, 'a4d1a4b9a8cb', '3139393620a2'),
        (0xA144, 'a1e5a1cda4c7', 'a3aca1bca8cc'),
        (0xA14B, 'a3aca1bca8cc', 'a1a7a9ac2037'),
        (0xA15F, 'a1dba2dea8cb', '3139393720a2'),
        (0xA1CC, 'a3bca8aea8cc', '3230303120a2'),
        (0xA230, 'd7d1dcd5a1d3', 'a5e0a7d1a3e1'),
        (0xA24B, 'fca4f6a4f3ed', 'c5a1dda8cb20'),
        (0xA2A3, 'a1eba1eba4d7', 'cda1ada6a7a5'),
        (0xA2BE, 'a2aaa5c728b2', 'aad9bfa3a9ab'),
        (0xA359, 'a1f9a1c8a8cb', 'a3a3204a6572'),
        (0xA36E, 'b7afa6f6abfa', 'abcba2e9a8cc'),
        (0xA39A, 'afd6a4c7a8cc', 'a5d7a5f9a4ac'),
        (0xA3B6, 'a3b0a9d5a8cb', 'a1b2a7f8aac5'),
        (0xA3D2, 'e4a2ddafa4b7', 'a5a1a8cc3c2f'),
    ],
    55: [   # SpecialistProfile / 拉默雷斯 (16 处)
        (0xA4F1, 'a2b2a1c3a8cc', '227b707da2bc'),
        (0xA5F0, 'a1f3a4c0a8cb', 'a3e4b8a3dca5'),
        (0xA62F, 'a2fca1ada1e9', 'a1c8a8cc20a3'),
        (0xA6A4, 'a7a8f320a8cc', 'a1e6a3d8d5a9'),
        (0xA6CD, 'a3a4a2e5a8cb', 'abe3bc204d65'),
        (0xA6E3, 'a2dfa1ada3a4', 'a2e5a8cc2032'),
        (0xA6E8, 'a420a2e5a8cc', '3230303520a2'),
        (0xA769, 'a7dfa3a6a8cc', '456e72697175'),
        (0xA779, 'b1a6f9dba8cb', 'a6d5abcba5f3'),
        (0xA7F3, 'a1b2afeaa8cc', '48656e727920'),
        (0xA803, 'daafa1c8a8ae', 'a1e4a7eec5a9'),
        (0xA81F, 'e8a2e5a2a8e2', 'a1c8eaa5aaa1'),
        (0xA837, 'a3a7e1e2a8cb', 'a6f6abfabca1'),
        (0xA866, 'afeea1c3a5aa', 'a9daafa8d120'),
        (0xA8C0, 'aaabcba2e9af', 'a4c5a2d6aab6'),
        (0xA8DD, 'd9a6cea4b9e2', 'a5d7a5f9a4ac'),
    ],
    56: [   # SpecialistProfile / 高登 (14 处)
        (0xA9D4, 'dabda4c7a8cc', '227b707da2bc'),
        (0xAB32, 'e7203135a8cc', '536169676f6e'),
        (0xAB4F, '3220a6dfabc0', 'a3e3a8cb2031'),
        (0xAB99, 'a5c4afa1e5c6', 'a8cb20a9b2d9'),
        (0xABED, 'abe8a2e5a8cc', '3139393420a2'),
        (0xABFE, 'cfb7c1c4a3d1', 'b8a8cb20a1b2'),
        (0xAC11, 'aaf7c1e9a8cb', 'a3c8f8a1a3a2'),
        (0xAC72, 'a4cea5a8a2c2', 'a1ada3dfc1e2'),
        (0xAC8C, 'fba2a4a8ecaf', 'eaa8cb20a2a8'),
        (0xACD1, 'a4a8a1aca8cc', 'a3d7d1aabea1'),
        (0xAD5E, 'a9cba7e0a8cb', 'aadaa5d5abe3'),
        (0xAD7B, 'ded5a3f0aae3', 'afa6a4c8a8cc'),
        (0xAD8F, 'a6a8aba8a8cb', 'a1aaa6d8a2b2'),
        (0xADB0, 'a5d6e6caafea', 'a8cb20a3b0de'),
    ],
    57: [   # SpecialistProfile / 加利斯基 (14 处)
        (0xAF9C, '79646965a8cb', 'a9e0a4ce29e2'),
        (0xAFBC, 'a6b329bcacf1', 'a5edb820a2f1'),
        (0xAFE8, 'b3f5aba9a8cb', 'dba1aca1f0a4'),
        (0xB002, 'a8e5aba9a5cb', 'a8cba3a1aabc'),
        (0xB045, 'a4c1a1e6a8cc', '3139393520a2'),
        (0xB05B, 'a6e3a8d4a7f0', 'a6cea8cb20d4'),
        (0xB0BB, '31393938a8d1', '3230303220e2'),
        (0xB0DD, 'a8e5a9daa8cb', '3230303220a2'),
        (0xB1D6, 'a2e8a9cca8cb', 'a1ccd5a5a9aa'),
        (0xB1F0, 'e0eaa9dda3dc', 'a8cca2bea3a6'),
        (0xB208, 'c220a5efa8cb', 'a7a6a5efe220'),
        (0xB22A, 'a4a1a5efa8cc', 'a1f6d9a6f9a1'),
        (0xB27E, 'a8a2a4a8ecaf', 'a4c5a2d6a3af'),
        (0xB2DF, 'aaeaa2fca3fb', 'a8cc20a5b6a6'),
    ],
    58: [   # SpecialistProfile / 科汉 (21 处)
        (0xB44D, 'a2c7aba6a8cc', '227b707da2bc'),
        (0xB5BF, 'a6daa1e6a8cb', 'a6b520426172'),
        (0xB603, 'abe2a3dfa8cc', 'a3f0a1e6a3d8'),
        (0xB626, 'a2b3a5bba8cc', '3230303320a2'),
        (0xB63A, 'fbcea5d7a8d1', '3230303420a2'),
        (0xB657, 'a1e5a6e3e2da', 'c9a8cb20a6b6'),
        (0xB67C, 'dfa4aad3a8cb', 'a4b6a1a7a3e4'),
        (0xB700, 'f0a2ecd8a8cb', 'a1e9a2b3c2b3'),
        (0xB718, 'f0a2ecd8a4ec', 'a7c1a4add0a6'),
        (0xB73A, 'a4c7a1dba8cc', 'a6dda9e8a1d3'),
        (0xB7A4, 'a9daa7cdafb8', 'a3a5a8cb20a6'),
        (0xB7A9, 'b820a3a5a8cb', 'a6dda9e8a2d4'),
        (0xB7E4, 'b6afa7aca3f2', 'abfaabfaa1f9'),
        (0xB813, 'a5b4aca2a8cb', 'a6dda9e8a2ca'),
        (0xB82A, 'a2d4a2aca8cb', 'eda5d1a3f2a6'),
        (0xB84C, 'a6b6a2d4a8cb', 'a2c5bda4bef7'),
        (0xB865, 'a4a8ecbcacf8', 'abccabc7a8cc'),
        (0xB881, 'c1cea1d3a5ba', 'aac9aadcafc1'),
        (0xB89D, 'a6dda9e8a3e4', 'a2a4a1c8b7af'),
        (0xB8B8, 'a4e1c5afaae4', 'a1e6a3eda8cb'),
        (0xB8D5, 'dee22d2da6dd', 'a9e8a6b320a2'),
    ],
    59: [   # SpecialistProfile / 门兹 (22 处)
        (0xB9BF, 'aaa3d1a6edb0', 'a8f5c5eea9c3'),
        (0xB9DA, 'a2f7a1dda8cc', 'a3bdfea8cc22'),
        (0xBAA2, 'a2bea3fba8cc', '48656c6d7574'),
        (0xBAC4, 'a1a5acc2a3e3', 'a8cb20a6d5ab'),
        (0xBAE9, 'aad1a5bca8cc', 'a1b2bca1bca9'),
        (0xBAFD, 'a5cba5cba8cb', 'a6dfd1a1acaf'),
        (0xBB17, '6d757420a9e3', 'a6d7a8cb20b3'),
        (0xBB65, 'adb3a3dfa8cc', '3139393420a2'),
        (0xBBAA, 'f5a1abbea8cc', 'a1b2a5c5a2b7'),
        (0xBBDD, 'a2f0a4a5a8cc', '3230303620a2'),
        (0xBBEF, 'a6a7a5cfb7c1', 'a5bca1b6a8cc'),
        (0xBC0A, 'a6c7a5efa8cb', 'a4eca1b2a1d4'),
        (0xBC27, 'aca5a3bba8cc', 'a1b2a3dbaab4'),
        (0xBC44, 'a1baa3b1aad1', 'cda2eca9f9a9'),
        (0xBC52, 'af20a9daa8cb', 'a5dda1c6a9b3'),
        (0xBCB1, 'fbafa1e7a3f7', 'a8cb20aabca1'),
        (0xBCC7, 'a1daa1c7a8cc', 'a1b2fbb8cca5'),
        (0xBCE1, 'a8afa7fea2f7', 'a3b1a6b3a2f0'),
        (0xBCFF, 'b2afa2f0a9bb', 'a9c8acdfa8cc'),
        (0xBD1B, 'a9b7a9daa7a1', 'dea2a420bca8'),
        (0xBD34, 'afb8a1d5a2ca', 'e2a7b820c5a3'),
        (0xBD4D, 'a2c6a8d4a3df', 'a3f6bc20c5a4'),
    ],
    60: [   # SpecialistProfile / 坦尼 (22 处)
        (0xBE45, 'eddea5d0a7d8', 'a6d7afa8d7a8'),
        (0xBE61, 'd2afa8d7a8da', 'a1c5d5b0f0fe'),
        (0xBE6A, 'd5b0f0fea8d0', '227b707da2bc'),
        (0xBEE6, 'c5a1ecd9a6bb', 'aaae297b6272'),
        (0xBF73, 'eacda2b9a8cc', '49616e20a2e1'),
        (0xBF9B, 'bcf7acd3a8cc', '49616e203139'),
        (0xBFE5, 'a1bca9dea8d1', 'abe4a1d4a3e4'),
        (0xC005, 'a8d7a8daa8d1', 'a4f5aabaa9d4'),
        (0xC021, 'd2bca4f2a8cc', 'a1b2bca1bca9'),
        (0xC07B, 'a5ada3eea8cc', 'a4f4dbdea6fb'),
        (0xC095, 'a7d3a1d5a8cb', 'a1b2afeba1af'),
        (0xC0FD, 'a3c9c2b3a8cc', '3230303420a2'),
        (0xC120, '20a3dbdcafeb', 'a1afa2daa8cb'),
        (0xC141, 'a6a8abaca1fe', 'a1aaa3f7d629'),
        (0xC15E, 'a1e9adb3a3df', 'c8a7c022a8cc'),
        (0xC165, 'c8a7c022a8cc', '3230303520a2'),
        (0xC19C, 'aa20bbe3a8f3', 'c5a1eca8cca1'),
        (0xC1CE, 'abb0a1e6a1c3', 'a8ccfbc5a1ec'),
        (0xC20F, 'acdebbe0a8cb', 'a9e3a4a3a1ac'),
        (0xC258, 'aad7a3f4a8cb', 'a1c2c6a3a9a3'),
        (0xC275, 'aa22de22a8cb', 'a1b2a9b3a4c5'),
        (0xC2AF, 'a5e1a2ada8a6', 'a8cb20a5dca9'),
    ],
    61: [   # SpecialistProfile / 海利 (17 处)
        (0xC3F7, 'a2cca9daa8d0', '227b707da2bc'),
        (0xC4E9, 'b6a2fca3fbce', 'a5d7eaa7daa6'),
        (0xC561, 'a9d5a1bea8cb', 'a3a4a5a3a2ca'),
        (0xC57C, 'f9daaceba8cc', '3139393420a2'),
        (0xC593, 'f9a5dfa4c0fe', 'a1bca8cb20c5'),
        (0xC5A6, 'dffea1bca8cb', 'a9d9d5203139'),
        (0xC5B8, 'a3a3a8dfa5fc', 'a7a6a6d6a5d7'),
        (0xC5D3, 'b7afa8eba6ce', 'a9e7a3fb2832'),
        (0xC5E9, 'f929a7d8a3d9', 'a8dfa3dfa6df'),
        (0xC60C, 'abe2a3dfa8cc', '3139393720a7'),
        (0xC63D, 'a4caaabda8cb', 'bc2053686573'),
        (0xC655, 'a1c5c3d6abbb', 'a1ada3eea8cc'),
        (0xC65C, 'a1ada3eea8cc', '3230303020a2'),
        (0xC679, 'a4caaabda8cb', 'bc2045737361'),
        (0xC6A8, '6520a6f3a5f5', 'a8cc20a8f0a3'),
        (0xC6CA, 'd4a5b3d1a1ba', 'a5b9c3a8cba9'),
        (0xC6EA, 'a3a4a1eca6b5', 'a3a9a4caaabd'),
    ],
    62: [   # SpecialistProfile / 伊布拉伊姆 (23 处)
        (0xC9D9, 'afa3bfdda8cc', 'b0bda3a8a4cc'),
        (0xC9F4, 'a4a8a1c8a1ad', 'a8d0227b707d'),
        (0xCA8A, 'cda2e9f3a8cb', 'a5cba2b2aaa7'),
        (0xCAE7, 'daa1acafa8cc', '45646f756172'),
        (0xCB10, 'a9caa1c8a8cb', 'a3a4ea203139'),
        (0xCB3D, '7320a1a2a7da', 'aabca1aca8cc'),
        (0xCB44, 'aabca1aca8cc', '3139383520a2'),
        (0xCB7C, 'a7f2d6fea8cb', 'bca2a1a8e5c1'),
        (0xCB9A, 'a7a9dec1a8cc', 'bc204d616361'),
        (0xCBB6, 'a3a4a2e5a8cb', '3230303220a2'),
        (0xCBC9, 'a5dea4b1aabc', 'a1c0bda1bca5'),
        (0xCBD7, 'abe2a3dfa8cb', 'bc20466f7274'),
        (0xCC19, 'e2a1e5c6a8cc', '3230303520a2'),
        (0xCC2F, 'd1a3d7c1a8cb', 'a1e6a3d8d520'),
        (0xCC44, 'a6dfa3dfa4aa', 'd3a8cc203230'),
        (0xCC48, 'a4aa20d3a8cc', '3230303720a2'),
        (0xCC9C, 'ace1a7cca8a3', 'a1aea3fba3e0'),
        (0xCCA7, 'a3e0a3daa8cb', 'a1f0a5d6a5e6'),
        (0xCD06, 'a1c3a5d6a8cb', 'a1cca4fbfba6'),
        (0xCD7B, 'a1cda2f6a8cc', 'c5fba1a5cca8'),
        (0xCD96, 'a1ada1b2a9aa', 'a3daa2e5af20'),
        (0xCDC6, 'a9b2a3bfa8cb', 'dea1f9a1d6a1'),
        (0xCDE1, 'a6dba2caa2a8', 'aadaa1f9a8cc'),
    ],
    63: [   # BackStory / 何为幽灵？ (15 处)
        (0xCF6B, 'a5eaa3dfa9c5', 'a5d3a1efa2b3'),
        (0xCFAB, 'c4afa4aca3dc', 'a2eca3f520a8'),
        (0xCFB0, 'dc20a2eca3f5', 'a8cc7b707d44'),
        (0xCFDC, 'acc5a2b8a8cc', 'a1b6a1cda5ea'),
        (0xCFF9, 'a3f0adada8cb', 'a1b2a1fcd9a9'),
        (0xD012, 'a5b4d3a9b1af', 'a2f4a3bfa8cb'),
        (0xD02E, 'dba6cca1c0af', 'eaa8ccabb0a3'),
        (0xD051, 'adb6a2e1adb7', 'a8cb204420a3'),
        (0xD054, 'e1adb720a8cb', '4420a3bca3a9'),
        (0xD0FB, 'a4e4a1a4a8cb', 'a2abbca1c5c3'),
        (0xD110, 'a1b2a1fca8cc', 'bad8a1d3a4b4'),
        (0xD176, 'a3ccaaaea8cb', 'a1cdb0afaafd'),
        (0xD18F, 'a5d6aba9a5cb', 'afbad8aaf8a2'),
        (0xD1A9, 'afd9a1d6a1b2', 'a3fba5d1a3d7'),
        (0xD1B8, 'f620a2b3a8d1', 'a5eaa3dfa1d6'),
    ],
    64: [   # BackStory / 兵种简介 (18 处)
        (0xD29E, 'a1efe5f0a8cc', 'a1b2e8b4204d'),
        (0xD2B3, 'a7eea5d4a8cb', 'a2abcbeca3d8'),
        (0xD2C5, '20a1e1bfa1b0', 'c0bea8cc20a2'),
        (0xD2DF, 'a2a4d0a2acaf', 'a8afbf20e4a9'),
        (0xD326, '706f6e29a8cb', 'a1cdb7c1a4ca'),
        (0xD33F, 'afc3a2b0a8cc', 'a1b2a1fca3d8'),
        (0xD353, 'a9a2a3ada8cb', 'd4aca7a5bacb'),
        (0xD36B, 'bab620c3a2b0', 'a8ccabb0a3d9'),
        (0xD399, 'd3a7f5a4adaf', 'a8cc7b707deb'),
        (0xD3B8, 'afa2fab8a8cb', 'eba3c9f0a1ae'),
        (0xD484, 'a9eaafa3bfdd', 'a8cb20fba4cd'),
        (0xD4AA, 'a1c0a1eba8cb', 'a8b6a2a5decc'),
        (0xD4C4, 'ddc3a2b0a8cb', 'a5faa4f4a5dc'),
        (0xD4DF, 'd0d4a1cea8a2', 'a1d3a2dda1a5'),
        (0xD52E, 'a1e5c620a8cc', 'a5c5a1c8a4b9'),
        (0xD54A, 'a7a5cfc1e9af', 'e6caa3d8a1a4'),
        (0xD569, '49435720d5c3', 'a2b0a6a8a2dd'),
        (0xD579, '473320a2cafb', 'a8cc3c2f7465'),
    ],
    65: [   # BackStory / 战争序幕 1 (29 处)
        (0xD6D4, 'a1cfa9d5abb9', 'a8cb20a3d5a1'),
        (0xD715, 'a2dda2dda7bd', 'a2bea8cb20ac'),
        (0xD746, 'afbbaceba8cc', 'a6e3a2c6a9d6'),
        (0xD762, 'a1cdadb3a3df', 'a2dda1c9a8cb'),
        (0xD77B, 'a3d7a8aea8cc', 'a8eba8d4a7c6'),
        (0xD797, 'd4bdabefa3d5', 'a8cbbba1c4a3'),
        (0xD7B5, 'aabca2c7a3b1', 'afacbaa2b2a2'),
        (0xD800, 'a3e9a6cea8cc', '3230303720a2'),
        (0xD956, 'c1a6f3d3a8cc', 'ace1a7cca6a4'),
        (0xD986, 'a2eca6f7a6bf', 'a5d7a8aa20a6'),
        (0xD9A5, 'b0a6b6a4cff3', 'acf8a8a320a8'),
        (0xDAC6, 'f0d3a1a1a8cb', 'a7a6a3e9a6ce'),
        (0xDADA, 'abb4a1aaa8cc', 'a8eba8d4a7c6'),
        (0xDB8F, 'a9bea1dea8cc', '3620a2e6a7ad'),
        (0xDBA3, 'cea6ecdca8cb', 'a7a6a5dfeaaa'),
        (0xDBBD, 'afa2f1a3acea', 'a9d5a7d6f2a2'),
        (0xDBF4, 'a3bbaae1a8cb', 'a7a6a3e9a6ce'),
        (0xDC09, 'faa3a1e1a8cb', 'a1fea1aaa8eb'),
        (0xDC82, 'eca1cba1b2af', 'acebc9a8cb20'),
        (0xDC97, 'a6b3a1b9a8cc', 'a9cba7eca7da'),
        (0xDCB4, 'a3f7a2aaacd5', 'a1d5a3e7a2c7'),
        (0xDCCF, 'f7c0a6d2a8cb', 'a1fea1aaa5eb'),
        (0xDD12, 'aac8a4aaa8cc', 'a1abbee2aacd'),
        (0xDD2B, 'a1fea1aaaabb', 'a8cba3dfa9da'),
        (0xDD4A, 'a7daaaa5a1c2', 'a6fcaff6e6a8'),
        (0xDD60, 'a3a1a9fba8cb', 'a9cba7eca7da'),
        (0xDD7B, 'a2f3a5dfa9f5', 'aaeea9d8a6ec'),
        (0xDD9A, 'a1a1a1b6a1cd', 'a1b2a1fca1d3'),
        (0xDE90, 'c9a3dfb8a8cb', 'a2d6d4a7e9ab'),
    ],
    66: [   # BackStory / 战争序幕 2 (23 处)
        (0xDF65, 'a3faa5cba8cb', 'a6f9a1bea5f9'),
        (0xDF80, 'bfb7a1e2a2e7', 'baa9daa8cc20'),
        (0xDF92, 'a5eee0afa8cb', 'd9a8dfa5fca7'),
        (0xDFAC, 'fbcea5d7bac3', 'abe3a4a3a8cc'),
        (0xDFC7, 'fea6e5e2a8cb', 'a1aea1f0c5a4'),
        (0xDFF5, 'a4ada3c9a8cc', 'edaaf7eaa3b0'),
        (0xE00C, 'e0afacbaa9d5', 'a7d6f0cea3e1'),
        (0xE015, 'f0cea3e1a3a9', 'a2dda1fba1ab'),
        (0xE168, '656220d4a3f3', 'a3cdd5a8dfa3'),
        (0xE1CF, 'cea3bda3dcb8', 'a8cb20adb3ba'),
        (0xE1F6, 'a4a2a4d2a8cb', 'a2c5a5eaa5df'),
        (0xE23A, 'aacca1aca8cb', 'a7b6a2fca3fb'),
        (0xE257, 'a5eda2eba5df', 'a9e3a8b6a8cc'),
        (0xE274, 'abe4a1e6a1c3', 'afa9ad20a9c9'),
        (0xE290, 'b6a4cceda6ba', 'a1abe420a1e6'),
        (0xE2AD, 'a9d5a8f9a4b1', 'a9caa8cc20a1'),
        (0xE2C2, 'acd1a2e3a8cb', 'c5eea5dfa6f5'),
        (0xE2D8, 'a4a3a1aca8cb', 'a5eda2eba5df'),
        (0xE316, 'a8aaa6c2a8cb', 'a5b9a4b3bad8'),
        (0xE333, 'b1d5acd1a7da', 'f0d6a8cc7b70'),
        (0xE34A, 'afbaa2bfa8cb', 'aca9daeda4b1'),
        (0xE35C, 'a3f0adada8cc', 'a1b2a1fcafda'),
        (0xE374, '20bda1e3a8cb', 'a2c8a1a7aad0'),
    ],
    67: [   # Interview / 开发访谈 1 (48 处)
        (0xE4A8, 'a1aca5aaa8cb', 'edeea2e6abb4'),
        (0xE4B8, 'a4caa7dba8cc', 'a6aaa1fca3c3'),
        (0xE4E0, 'a2f3a2b0a3c6', 'd0a8cc20edac'),
        (0xE53F, 'd0cca6eda8cb', 'a4dcd7d2fda3'),
        (0xE552, 'a6daa1f3a8cc', 'a3fba3e0bba4'),
        (0xE56D, 'a1e2a1aca2bd', 'cea2c2a6aaa1'),
        (0xE599, 'a1a1a1b0acf7', 'a8cb20a2c5a3'),
        (0xE5AB, 'a2dda1c8a8cd', 'a6aaa1fcbcaa'),
        (0xE5C6, 'afa1d1c5a4cd', 'a1f3aadaa8cc'),
        (0xE5F0, 'a7a5cfa1e5c6', 'a8d120a4a8d5'),
        (0xE60A, 'a9cba1ada8cc', 'a6aaaba5bc20'),
        (0xE668, 'a6cea3fba8d4', 'a3bda2c628a6'),
        (0xE6A3, 'd4a3bda2c6ea', 'a2d6d5a9c5a1'),
        (0xE6D5, 'a3d8a2aaa8cc', '536f756e6465'),
        (0xE76B, 'afa5c7bea8cb', 'a6d8a4fba5ea'),
        (0xE784, 'aae8a5b1a8cb', 'a6d6a8d4a2fc'),
        (0xE79D, 'e9e6a1dca8cc', 'a3a4a2bfa3d2'),
        (0xE7DB, 'adc5a7d2a8cc', 'a6aacbded920'),
        (0xE7EB, '64726978a8cb', 'a2c5a5e8d9bd'),
        (0xE816, 'a9e3a6d7a8cc', 'a6aaa5dca4c8'),
        (0xE832, 'a2c2b0a1fcc5', 'a3d7a1addea4'),
        (0xE840, '20aff5f4a8cc', 'a6aaa1fcccbc'),
        (0xE8B6, 'a5cea2fea8cb', 'a4afd1a1accc'),
        (0xE8CC, 'a2d6a3e6a8cc', 'abb5d1f5f4a9'),
        (0xE8FE, '20a2b2a7d3d5', 'a1acf7a9b5fe'),
        (0xE96E, 'c9d5a3bfa8cb', 'f5f4cea1abbe'),
        (0xE983, 'd4a3f9dafdb8', 'a3a5a2caa2f6'),
        (0xE9A5, 'a2dda1fba5a3', 'a1c1a1c8a1a6'),
        (0xE9B9, 'a2aaa5c7a8cb', 'a1cdf5f4a7bd'),
        (0xEA56, 'a1eaabfaa8cc', 'a3a4a3bfa5ce'),
        (0xEA6B, 'fea1adf0a8cb', 'a3edf6cea1f6'),
        (0xEA81, '20a2fee9a8cb', 'a3e5a5a1a2af'),
        (0xEAB9, 'a7dfa4d0a8cb', 'a1fda1aca4be'),
        (0xEB2D, 'c7a1f9f0a8cb', 'a1aaa1e9a1ac'),
        (0xEB4A, 'a1bfa4e4a2f6', 'a8cca6aaafa3'),
        (0xEB65, 'f4a1eabca1d0', 'a1cda4f4a5b1'),
        (0xEC34, 'b0e0a1baa8cb', 'a6aadecca5e0'),
        (0xEC4A, 'a7ccafeaa8cc', 'd1c5a1efa1b2'),
        (0xECDD, 'fee9a5aaa8cb', 'a1b2a1fca3da'),
        (0xECF8, 'a2feaab6fde2', 'aaada3aca8cc'),
        (0xED0E, 'aac6a5e0a8cc', 'a2c6cea6cee2'),
        (0xED20, 'a920a2f6a8cc', 'a5bca4d0a3e3'),
        (0xEDEF, 'adb7a5c9a8cc', 'aad6adb7a5c9'),
        (0xEE0A, 'a1b2cffea1ad', 'c5a4dda1e9af'),
        (0xEE43, 'a1b0a3d0a8cb', 'a2c2a1b2a1fc'),
        (0xEE69, 'a2c6cea6cee2', 'a8f4a8a420a8'),
        (0xEE8D, 'a2bb20f7a7ce', 'a1dea1ada1b2'),
        (0xEEBF, 'cbd4a7cfa8cc', 'abb5d1a2bade'),
    ],
    68: [   # Interview / 开发访谈 2 (94 处)
        (0xEFF6, 'faa3c6d0a8cb', 'a6aaa1fca1ea'),
        (0xF007, '42657461a8cc', 'd5a1adedc5a1'),
        (0xF032, 'bcacace0a8cb', 'a1eda1cec5df'),
        (0xF043, '42657461a8cb', 'a2d0b8a2d3cb'),
        (0xF068, 'a9bda4c7a8cc', 'cbc5a4c1cea1'),
        (0xF080, 'a5f0a1dda2c8', 'a3d3fba9daaa'),
        (0xF09E, 'a3b1a1ada6aa', 'a2dda3d7a1e6'),
        (0xF0BC, 'e2a3d4a1d3db', 'aab6eedac9a8'),
        (0xF0D1, 'a7c8a8aba8cb', 'a2afbcbda1b0'),
        (0xF0EB, 'c1d5a2a4a8ec', 'aff5f4a8cbed'),
        (0xF106, 'a1d5aad1a5ce', 'a2fee2a1c1a1'),
        (0xF13A, 'd0a5decea8cc', 'dea1f9abb5d1'),
        (0xF192, 'a3a1debda2b9', 'a8cc20a6aaa1'),
        (0xF208, 'a6b8a3a6a8cc', 'a2c9a9eea3f1'),
        (0xF224, 'a3d3fba2f4ea', 'dac9afa9acc5'),
        (0xF257, 'a2e2a3d4a8cc', 'd5a3a2204265'),
        (0xF278, 'e2a3d4a1aebb', 'c6a5e8a2ec20'),
        (0xF299, 'a3d7a1aea3bf', 'a8cb20edcca1'),
        (0xF2EF, 'c9efa2a5a8cc', 'bca3c3a3d420'),
        (0xF302, 'd5cea1cca1f9', 'a2bbdba8cb20'),
        (0xF31E, 'a2cda1c4aad1', '2d2daabca1d1'),
        (0xF383, 'e4dea4d2a8cc', 'a5bbc1a1eabc'),
        (0xF399, 'a4f6a2f4a8cb', 'caa1a4d0a1a7'),
        (0xF3B7, 'edc5a1efa8cb', 'a6aaa1fcbba5'),
        (0xF3CE, 'a4aba4c8a8cb', 'a2c8f0a6c3af'),
        (0xF454, 'a3e4a3e4a8cc', 'a2dda1fba2f6'),
        (0xF46E, 'd3a2e9afa6b0', 'a2c9cea1d2a1'),
        (0xF47D, 'd220a3daa8cb', 'a9b3cdaaaeaf'),
        (0xF496, 'b6a4c1a6aade', 'a3f7dea7badc'),
        (0xF4B2, 'a3f7a2aaa8cb', 'a2c8c5eea1a6'),
        (0xF509, 'eea1bdc8a8cb', 'a1aca1edd7ab'),
        (0xF535, 'c1e2a6b3a3ac', 'aaeda2afd2a4'),
        (0xF5CB, 'a3bfa5aaa8cb', 'a1b2a1f6a5a8'),
        (0xF5EA, 'dcd9a1aaa1b2', 'a7f9a4f0a4c9'),
        (0xF609, 'a2fcabdaa1ae', 'dea5c7a1f3a8'),
        (0xF620, 'f6c5a3b6a8cc', 'b0a5aaaad6a8'),
        (0xF63E, 'a4cbace1a1ad', 'a8cb20dea3b8'),
        (0xF682, 'a1c3a1f9a6d7', 'a8cc7b707da3'),
        (0xF750, 'dcaad820a8cc', 'a1f6a5a8bcaa'),
        (0xF7F8, 'f2d5a1ada8cc', 'eda8a3a3afa1'),
        (0xF80E, 'a3c8aad6a8cb', 'c3a7dbabe3a4'),
        (0xF855, 'a3dbaab4a8cc', 'a7bda4b0a1f2'),
        (0xF898, 'a3d3a1a8a8cb', 'a1aed9f5f4ce'),
        (0xF8AE, 'b3e6a1e3a2a1', 'a1ddb8a1ccd5'),
        (0xF8BF, 'a5d1a1a8a8cc', 'a6aac5bda3a8'),
        (0xF8DA, 'a7d12d2da2dd', 'a4d2a3fba4d2'),
        (0xF933, 'ddbcaba6a8cc', 'a2f4ead3a1a8'),
        (0xF949, 'a9cba1ada8cb', 'a1e4a1bba4b6'),
        (0xF964, 'a2bea3fba2e0', 'a8cba7acb6a2'),
        (0xF973, 'fec5aaeda8cc', '554920a2baa4'),
        (0xF984, 'abfda2e2a8cb', 'a2c5a1dfa2e1'),
        (0xFA8D, 'd9eda3b6a8cc', 'a6aaa5dcd9bc'),
        (0xFAA6, 'b6eea3ccaaae', 'a2e7a2f5a8cb'),
        (0xFB0E, 'e8a4fbaad1de', 'a3c3afa6d7a8'),
        (0xFB33, 'd020f5f4a8cc', 'a6aaa1fca2c8'),
        (0xFB8F, 'a1aca5aaa8cb', 'eda1f3aae8a4'),
        (0xFBAA, 'd1a3c3a2abd0', 'f5f4a8cca4d9'),
        (0xFBBC, 'e2a2b7a4d9cb', 'd4a2bbdba1fd'),
        (0xFBD6, 'a1dfbca1d3db', 'a6a9a2d4a8cc'),
        (0xFC37, 'a5aaa4a3a8d0', 'a9b1a2f3a1e9'),
        (0xFC52, 'a2f3a3d7a3c3', 'a5bca8ceaab6'),
        (0xFC72, 'a1a7a8d8a8cb', 'dac9e2d3a1a8'),
        (0xFC89, 'd3dba6a9a2d4', 'a8cc7b707da4'),
        (0xFCF6, 'a2dda8b3a4c1', 'b0a7fbbcc5aa'),
        (0xFD0F, 'aad2deaadafb', 'eaa5b6a2e929'),
        (0xFD86, 'a7dea2dda8cb', 'dea1f9a6aaa1'),
        (0xFDA0, 'abbea3f7a2aa', 'a8cca7b0a4b8'),
        (0xFDB4, 'a4deaabfa8cb', 'a2c5a2e0a1bf'),
        (0xFDCF, '4920c1a3f4b4', '22a1a5e52022'),
        (0xFDD4, 'b42022a1a5e5', '22a2a2c5a6db'),
        (0xFDF0, 'a1c8aca4a3a9', 'a3b0a9bda3bf'),
        (0xFE81, 'a4a3a1aca8cb', 'aabcaadea8cb'),
        (0xFE9D, 'b9e5a2f3a6df', 'afa1c820abd0'),
        (0xFEB0, 'a1c1a6c3a8cc', '3a2d297b707d'),
        (0xFF2B, 'a6fea5dea8cb', 'd5a3c8bca2ca'),
        (0xFF3B, 'fb20a3e0a8cc', 'a9e3a8a7a2cc'),
        (0xFFB9, 'a3fba3e0a8cc', 'a6aaa2eea2fb'),
        (0xFFD4, 'af3920eea2e6', '22abcfa4da22'),
        (0xFFF2, 'e5c6afbaa5bb', '28eda1ea20d9'),
        (0x1000A, 'aad1afa3edf6', '29a8cc20a3b0'),
        (0x1002B, 'a1c1a1ada8cb', 'aabcaadea2f6'),
        (0x10079, 'a3fba3b4a8cb', 'a6d6d2a4a8dc'),
        (0x10091, 'a2bba3caa8cc', 'a6aaf0a6c3a3'),
        (0x100A9, 'd0f5f4a2abbc', 'a1eaabfaa5bc'),
        (0x100D3, 'cea2e7a2c0df', 'cf28bda3a8a4'),
        (0x101A2, 'aaa5bbc1a8cc', 'a5eaa4f0a3e3'),
        (0x101BC, 'ccd3a1a8a8cb', 'a2f6a1cca3a9'),
        (0x101D8, 'aab6eedea4d2', 'afa2edb6a3bf'),
        (0x101F1, 'a9eabda6a4bc', 'c5a1d5b7a3c9'),
        (0x1020D, 'e52d2ddea7c8', 'afd9a8cb20a9'),
        (0x10260, 'bca6abe5a8cc', 'a6aadfd5204d'),
        (0x102C6, 'abb2bcd3a8cc', 'a9f3a9f3a8cc'),
        (0x10349, 'daafa2d4a3f2', 'f7a3f920a6cc'),
        (0x10385, 'c3bfa3b0a6aa', 'a6c3a9c5fea8'),
    ],
    69: [   # Interview / 开发访谈 3 (193 处)
        (0x10506, 'a3bda2c6a8cb', 'a8a7a2cca5bc'),
        (0x10542, 'a2f6a7c7a4fb', 'a5cea2fea8cc'),
        (0x10576, 'b6baa1ada8cc', 'a6aaaaf1aaf1'),
        (0x10587, 'a4d8aceaa8cb', 'a1f8c1a3f4e2'),
        (0x105BE, 'a1a9a8d2a8cb', 'a7b8fbeaaaa7'),
        (0x105D8, 'a1c8abd0a8cc', 'a5bbc1a2eba1'),
        (0x105EE, 'adcda1aca8cb', 'a1c1a3a9a6f6'),
        (0x10647, 'f9cea5fca8cb', 'a1e9a3fba3b4'),
        (0x1065E, 'bac5aacaa8cb', 'a3d9d9bbaad1'),
        (0x106DD, 'eaa4d8dba8cc', 'c5a1eca2eba1'),
        (0x106EB, 'da20c9cea8cb', 'a6aabca4f6a1'),
        (0x10704, 'f6a1aac8a8cb', 'a2eea1bfa6aa'),
        (0x10723, 'e3a8dcd5a1aa', 'c8a8cb20a1ea'),
        (0x1089B, 'afb7a4c7a8cc', 'a9febbace9fe'),
        (0x108D0, 'c4a6e7c8a8cc', 'a6aabda3a8a7'),
        (0x10915, 'a1b2aba2a8aa', 'a9b2a3bfa8cc'),
        (0x10949, 'a2dba2daa2bc', 'a3b0a7d7cea8'),
        (0x10A37, 'abd0bde5a2bb', 'f7a2baa9c4a1'),
        (0x10A5B, 'a4c7a1ada8cc', 'a6aaa1d3a2f6'),
        (0x10A73, '20627567a8d1', 'a4d920627567'),
        (0x10B3A, '4f77656ea8cb', 'a8a7a2cca5bc'),
        (0x10BFC, 'b8a2bacca2a4', 'acf7a2a4a5ef'),
        (0x10C27, '20eda6baa3f7', 'a2aaa1b6cda1'),
        (0x10C60, 'b7a3dfa6c3f6', 'a8cc20b0a7ec'),
        (0x10C71, 'aff0d1dba8cb', 'a1b2cca1b4ab'),
        (0x10C89, 'f1a4fbb0a8cc', 'a1b2a6f1a4fb'),
        (0x10CB5, 'abccabc7a8cb', 'a2c5a6aaaf20'),
        (0x10D49, 'a2faa1ada1aa', 'a7a7a8fca3f7'),
        (0x10D57, 'aaafa1fea2f8', 'a8cc7b707da7'),
        (0x10D6F, 'f3a9cae5a8cc', 'a5eaa4f0a3e3'),
        (0x10DA6, 'a1eebca9b2ce', 'a8cb20a1cca4'),
        (0x10DBB, 'a3dba2f3a8cc', 'a6aaa3e4a1f9'),
        (0x10DCA, '524120afb7cc', 'e9a8cb20a3d9'),
        (0x10E16, 'a3e0a3afe5d0', 'd5a3b2ce22af'),
        (0x10E24, 'f120a3fca8cb', 'cca3afa3f6a2'),
        (0x10E3E, 'a4cea1a8a5e7', 'a9daa8cb20a1'),
        (0x10E43, 'e720a9daa8cb', 'a1aea9d9a4af'),
        (0x10EE2, 'b8a3a520a8cb', 'a1aedeb4aad1'),
        (0x10EFE, 'a3fca1f3aae8', 'a4fba8cd20b0'),
        (0x10F10, 'c1a3f4b8a8cb', 'a1b2a1fcccbd'),
        (0x10F27, 'a4bea1aacab0', 'a8cc7b707db0'),
        (0x10F7D, 'a1ccd5dba8cb', 'a3e4a3b8a4c8'),
        (0x10F96, 'af20b8a3a5b7', 'a3f7a5aaa1dd'),
        (0x10FB8, '76696368a8cb', 'a8a7a2cca5bc'),
        (0x1102C, '42657461a8cc', '227b62727d41'),
        (0x11052, 'abccabc7a8d0', '227b62727da6'),
        (0x11073, 'adfca3f7a8cf', '227b62727d41'),
        (0x110B7, 'a6aaa5dca2be', 'a1adfca3f7a8'),
        (0x110DB, 'a7e8a1ada8cc', '227b62727da6'),
        (0x110FA, 'e9aad1afa8cc', '227b62727d41'),
        (0x11165, 'a9b3a2f6a8cf', '227b62727da6'),
        (0x11183, 'f62e2e2ea8d0', '227b62727d41'),
        (0x111A0, 'a9b3a2f6a8cf', '227b62727da6'),
        (0x111D8, 'e8eaa1ada8cc', '227b62727d41'),
        (0x11211, 'fbc5acc8a8cb', 'b0a7a7a8fcc5'),
        (0x1122A, 'ccb7a3f7a6f1', 'b0a5aaa8a3a8'),
        (0x11232, 'a5aaa8a3a8cc', '227b62727d41'),
        (0x1124F, 'abccabc7a8d0', '227b62727da6'),
        (0x1126A, 'a7a6a5efa8cc', '227b62727d41'),
        (0x112F6, 'a1e4a7eea8cb', '4461646479a8'),
        (0x11342, 'e9aad1afa8cc', '227b62727d41'),
        (0x1137C, 'a3afa9cea9b1', 'c6af2e2e2e22'),
        (0x113A5, 'a9b1c6afa8d0', '227b62727da6'),
        (0x1142F, 'a9b3a2dda8cc', 'fbb8a3a5a1ed'),
        (0x11445, 'a2dda1ada8cc', 'a1aea5a1d9bd'),
        (0x1147E, 'a9c3a1d5a8cc', 'eda1aebba5c0'),
        (0x11498, 'a1dda3c1a1d4', 'a8cca5bca1b6'),
        (0x114B4, 'f3afa1c5a8a4', 'a8cbaabcaade'),
        (0x114D1, 'eaa9ddd0a1ac', 'a8ccedfbb8a3'),
        (0x11594, 'a4cfa8a3a8cb', 'dea1f9a9b2a6'),
        (0x115B0, 'aed9a3b0a5ef', 'a2aaa9baacf7'),
        (0x115CB, 'afeaa4ada1ac', 'afa8cc20fbb8'),
        (0x115DA, 'a6aaa4c8a8cb', 'a6b3a3acaaed'),
        (0x115F2, 'cf20a8a3a8cb', 'd9ded9a5a9a3'),
        (0x11632, 'a5a1a1ada8cc', 'a3e5a2bba8cb'),
        (0x11669, 'aaf0a4caadae', 'a8cc20a9a5ab'),
        (0x11694, 'a3bda2c6a8cb', 'a8a7a2cca5bc'),
        (0x11728, 'c8a2a7afa8cb', 'eaeaa1c1a3a9'),
        (0x117B4, 'b6dbaab6a1dd', 'a4c9a2afa2c8'),
        (0x117D4, 'aea1f9c5a6ba', 'a8aea1e8a8cb'),
        (0x117FA, '3120a4c1a1ad', '29a8cba2c5a1'),
        (0x1186E, 'a3cdace6a8cc', 'f7aab6a4c1a4'),
        (0x1187F, '636b6579a8cb', 'fbeac5a1a6a2'),
        (0x11898, 'a3a4abb5a2bb', 'a1d5a8cca6aa'),
        (0x118B2, 'bf20d3cea8cf', 'a2f6bcfb2068'),
        (0x118FA, 'cfa1e5c6a8cc', 'a6aaa1fcd5a3'),
        (0x1190C, '6120a1ada8cb', 'f5f4a2f6a9cb'),
        (0x11917, 'a9cba1ada8cc', 'a6aaa2e3a3c0'),
        (0x11930, 'a4a3a1aca8d1', 'a1c1a4a3a1ac'),
        (0x1194F, 'a2b0afd9a8cd', 'a9b2a6baa2c9'),
        (0x1199A, '5320a7d8abfe', 'c5a3b6a1b4a1'),
        (0x119B7, 'a1fea2f8a8cb', 'a9a5aba6a2af'),
        (0x119FA, '20627567a8d1', 'a2b7a4d9a8d1'),
        (0x11A22, '20a6a922aaac', 'a6c3afaad7a3'),
        (0x11A3D, 'a2a5d5afa1d3', 'cdaaaeafa5bc'),
        (0x11A73, 'aaceaacba6ec', 'a4dca1ada8cc'),
        (0x11B09, 'd4dda2bda8cc', 'a6aaa1fca2fe'),
        (0x11B28, 'd6eaa2caa8f5', 'ded5a8cc20de'),
        (0x11B43, 'aad1a6a8a2ac', 'a2e2a3d420a8'),
        (0x11B87, 'a1d0a1ada8cb', 'a6aaa1eaa2f3'),
        (0x11BF3, 'a2b5a3b3a8cb', 'a2caacf6a3a9'),
        (0x11C0F, 'aba6c2aad6bc', 'd9a8aba7dba8'),
        (0x11C28, 'a2bfafeaa8cb', 'a6aaa4ada4c7'),
        (0x11C49, 'a3bda2c6a8cb', 'efa2a5a3e37b'),
        (0x11C90, 'd1efa2a5afea', 'a1aca5aaa8cb'),
        (0x11CA5, 'a3a8a1ada8cc', 'a6aaa1fca1ea'),
        (0x11CBC, 'a7f6a2c9a8cc', 'a1d1a9eea1d1'),
        (0x11CD4, 'a2e3a2aca8cc', 'd5a1ada9eeab'),
        (0x11D32, 'b6afa7dfa4d0', 'a8cc7b707da2'),
        (0x11D5A, 'a5eca6b0afed', 'acc8a2b2a1c3'),
        (0x11D76, 'decba4c5a8cc', 'a3d3fbdac9a2'),
        (0x11D8D, 'afa1e5a1cdef', 'dda1aea3bfa8'),
        (0x11DAE, 'a9daa2cca2ca', 'a1dfa1aea3bf'),
        (0x11DCC, 'a2e3a2aca1c7', 'cfa7f6a2c920'),
        (0x11DEA, 'a1a1e6afa1bd', 'a2c0fba2f620'),
        (0x11E18, 'b3edc5eea8cc', 'a6aaa1fca5e8'),
        (0x11E2F, 'c1afa2e3a2ac', 'aafda1a7a1d0'),
        (0x11E40, 'f620a2c9a8cb', 'eda3afa1e4a1'),
        (0x11E6A, 'a1c7a3a7a8cd', 'a1f6a5a8a7bd'),
        (0x11E7E, 'a9f9acbba8cb', 'a1f6a5a8a9b2'),
        (0x11EE9, 'a9a1ad20a8cc', 'a5bbc1ceafea'),
        (0x11F0C, 'acdaa9cba8cc', 'a1ccd5a1e9ad'),
        (0x11F27, 'a1b2a1fca1aa', 'a6a7a5cfa1e5'),
        (0x11FD7, 'cbc5a4cba8cb', 'a2c5a3e5a2bc'),
        (0x11FF4, 'ead6a6aaa1fc', 'a3e4a7adafef'),
        (0x1201A, 'aacfa3f9a9da', 'a8cb20a6aaa1'),
        (0x121A8, 'a1ada3a9a8cb', 'a6aaacb6a5aa'),
        (0x121C2, 'a4c1a1cda4b3', 'a3d3fbf5f4ce'),
        (0x121D3, 'a1cc20afa8cc', 'a9a5aba6a1c1'),
        (0x121EF, 'fca2bafba1e3', 'bba4d1a8cb20'),
        (0x12205, 'a2b7a4d9a8cc', 'd2a1bff5f4bc'),
        (0x12244, 'd9bca5c5a4c7', 'aad1f8a1a3d3'),
        (0x1225C, 'a1ccd5afa9b2', 'a5d1a3b0fea3'),
        (0x12279, 'cdc5a5eea8d1', 'a5e8aad6afa2'),
        (0x12312, 'a1eaa1eda8cc', 'a5d1a5d1a2bd'),
        (0x1232B, 'f4cca2dda6b5', 'a1d0a4dea8cb'),
        (0x12345, 'f4a9b1d5edee', 'd3a1efaabca2'),
        (0x1237E, 'a9e1a9dca8cb', 'a4dda1b9a1b6'),
        (0x123A0, 'a1d5a1ada8cf', 'a5bbc1a1cda3'),
        (0x123B8, 'acaca2d3a1ad', 'a2f3a2b0a8cc'),
        (0x123BF, 'a2f3a2b0a8cc', 'edc5a4c1d5a1'),
        (0x123D5, 'a1b0a3c8f5f4', 'a4aaa2c9a3c3'),
        (0x123EA, '20afa3fba3b4', 'a8cceda1f3aa'),
        (0x12426, 'c8afa1d0a5de', 'cca2f6a3a920'),
        (0x12443, 'cca1b0a3c8ed', 'd9c5ee20a2b7'),
        (0x12452, 'a1b9a1b6a8d1', 'b4a4c7efa2a5'),
        (0x1249A, 'dafdf5f4a8cc', 'fea9eeaab6aa'),
        (0x124B5, 'abe1a1e8a8cb', 'a2bafbaab6ee'),
        (0x124CB, 'a9d4abe4a8cb', 'a5dca2ebabb5'),
        (0x124E4, 'a1eda2bda8cb', 'a6fea5decdad'),
        (0x12521, 'a9e3a6d7a8cb', 'a2baa5daaab6'),
        (0x12554, 'a3a1debda2b9', 'a8cc20a6aaa1'),
        (0x12578, 'c5eea9e5aad6', 'af20476f6c64'),
        (0x12599, 'b4bcabadacb8', 'a2f3c1a2b2ab'),
        (0x125BF, 'e5bbace1a8cc', 'a2d0b8a2d3cb'),
        (0x125D1, 'c1f520f4a8cb', 'a1eda1cea3d3'),
        (0x12640, 'a2beacd3a8cb', 'a1cfa2b0a2c8'),
        (0x12658, 'a9b3ace1a8cc', 'dea1f9a2ddac'),
        (0x1266F, 'a1ac20afa8cc', 'a9b3a1f2a6aa'),
        (0x12695, 'a1a8a6cea8cb', 'a1b9a1b6ea7b'),
        (0x126C8, 'a9cba1ada8cf', 'a6a7a5cfa1e5'),
        (0x126E3, '20d5a3bfa8cb', 'a6aaa1fccbd4'),
        (0x126FC, 'd420a2e2a3d4', 'a1ada8cc7b70'),
        (0x12753, '42657461a8cb', 'a2c5a1b2a1fc'),
        (0x127C2, 'eebaa2dea8cc', 'a1d8a5eba8cb'),
        (0x127DD, 'a1d3abe6aac9', 'afa5c520a1c8'),
        (0x12831, 'a2bcadb7a8cc', 'a6faeeaae3a1'),
        (0x1284E, 'a7d7a7d4a1ae', 'd9d2a4f4a8cb'),
        (0x12864, 'e9f0a1d4a8cb', 'a3affaa1fca1'),
        (0x12879, 'a2eba3eca8cc', 'a3ccaaaea1f6'),
        (0x12892, 'a1fca1cca4a3', 'a1aca1eaa2eb'),
        (0x128C7, 'b8a1d5b4a2d3', 'a8cc7b707da3'),
        (0x12911, 'a8f3a6c7a8cb', 'a5cea2fec4a8'),
        (0x12951, 'a5a2aba6a8cc', '4265617520a1'),
        (0x129F5, 'a2adaba6a8cc', '4265617520a1'),
        (0x12A28, 'a5a4a1c3a8cc', 'a1cba4f4a2bb'),
        (0x12A56, 'a1f9a3b1a8cb', 'a1f3aae8a4fb'),
        (0x12A72, 'b8a1d5a6d6fe', 'c5a9eef920a9'),
        (0x12A8B, 'a1d5ced2aac5', 'eaeaf020a8aa'),
        (0x12AA2, 'a8d7a8daa8cb', 'eda2c9a1accc'),
        (0x12AB6, 'a2eaa5a7a8cc', 'a1d1a3e4a1b2'),
        (0x12ACD, '20a6d7b8a8cb', '4265617520ab'),
        (0x12AE6, 'a1acd9eea2f6', 'a2bda8d620a8'),
        (0x12B65, 'aae3a4c0a8cc', 'a1f9a3b1c5a9'),
        (0x12B81, 'b0a1adc5a2bf', 'a1e4a3d9a6e9'),
        (0x12B97, 'a2bbaacfa8cc', 'a3a4a8aaa2ca'),
        (0x12BAE, 'db20a1dda8cb', 'a2a8fbc5a1bd'),
        (0x12BC9, 'a1cfa1adaab6', 'a9eea8cb20a1'),
        (0x12BF2, 'a1f3a4c0a8cc', 'a3edf6a1b9a1'),
        (0x12C0A, 'a5c8a1a7a8cb', 'a4c8a2c8aacf'),
        (0x12CDA, 'a3fbacbea8cb', 'a5eaa4f0c4a8'),
        (0x12DAF, 'a1ada6d6a8cb', 'd1a7c6a2caac'),
        (0x12DF7, 'a3edf6cea8cc', 'a3b0aac5a3f9'),
    ],
}


# ───────────────────────── 盘 / XML ─────────────────────────

def subs_of(raw):
    subs, p = [], 0
    while p + 8 <= len(raw):
        L, S = struct.unpack_from('<II', raw, p)
        if L == 0 or p + 8 + L > len(raw):
            break
        try:
            dd, err, _ = lzo1x_decompress(raw[p + 8:p + 8 + L], out_size=S)
        except Exception:
            break
        if err is not None:
            break
        subs.append({'raw': raw[p:p + 8 + L], 'dec': bytes(dd), 'L': L, 'S': S})
        p += 8 + L
    return subs


def load_charset():
    c = json.load(open(CHARSET, encoding='utf-8'))
    dc = {v: k for k, v in c['codes'].items()}
    dp = {tuple(v): k for k, v in c['pair_of'].items()}
    return dc, dp


def dec_engine(b, dc, dp):
    """引擎口径解码 + 逐字→字节偏移。返回 (text, byte_off[])"""
    o, mp, i, n = [], [], 0, len(b)
    while i < n:
        v = b[i]
        if v < 0x80:
            o.append(chr(v)); mp.append(i); i += 1
        elif 0xA1 <= v < LEAD_MAX and i + 1 < n and (v, b[i + 1]) in dp:
            o.append(dp[(v, b[i + 1])]); mp.append(i); i += 2
        else:
            o.append(dc.get(v, '.')); mp.append(i); i += 1
    return ''.join(o), mp


# ───────────────────────── 折行模型 (与 work/_dis/r28_lib.py 同源) ─────────────────────────

def strlen(s):
    return 0 if not s else sum(W_ASCII if ord(c) < 0x80 else W_CJK for c in s) + (len(s) - 1) * TRACK


def segments(text):
    """按 {br}/{p} 切段 (RSHTML::CreateStrings 口径)。返回 [(start, end, seg)]"""
    segs, pos = [], 0
    for m in TAG_RE.finditer(text):
        segs.append((pos, m.start(), text[pos:m.start()])); pos = m.end()
    segs.append((pos, len(text), text[pos:]))
    return segs


def seg_tokens(seg):
    res, i = [], 0
    while i < len(seg):
        if seg[i] == ' ':
            i += 1
            continue
        j = i
        while j < len(seg) and seg[j] != ' ':
            j += 1
        res.append((seg[i:j], i, j))
        i = j
    return res


def wrap_seg_detail(seg, SP):
    """RSTextComponent::DoWordWrap (标定后 form Q 口径)。返回 (lines, cl)"""
    toks = seg_tokens(seg)
    cl = [None] * len(seg)
    if not toks:
        return ([seg] if seg else []), cl
    lines, cur, budget = [], '', WRAPW
    for ti, (tk, a, b) in enumerate(toks):
        w = strlen(tk)
        if WRAPW < w:                                       # 硬断分支
            for k, ch in enumerate(tk):
                c = (W_ASCII if ord(ch) < 0x80 else W_CJK) + TRACK
                if budget - c < 0:
                    lines.append(cur); cur, budget = ch, WRAPW - c
                else:
                    cur += ch; budget -= c
                cl[a + k] = len(lines)
        else:
            if budget - (w + TRACK) < 0:
                lines.append(cur); cur, budget = tk, WRAPW - w
            else:
                cur += tk; budget -= w + TRACK
            for k in range(b - a):
                cl[a + k] = len(lines)
        if ti + 1 < len(toks):
            if cl[b - 1] is not None:
                for p in range(b, toks[ti + 1][1]):
                    if seg[p] == ' ':
                        cl[p] = cl[b - 1]
            budget -= SP
            cur += ' '
    if cur:
        lines.append(cur)
    return lines, cl


def char_layout(text, SP):
    lay, counts = [None] * len(text), []
    for (a, b, s) in segments(text):
        lines, cl = wrap_seg_detail(s, SP)
        counts.append(len(lines))
        for k in range(len(s)):
            if cl[k] is not None:
                lay[a + k] = (len(counts) - 1, cl[k])
    return lay, counts


def comp_pos(text):
    """补偿空格插入位 = 最后一个含 token 的段末尾 (与筛选脚本 r28_plan2.py 同源)"""
    pos = len(text)
    for (a, b, s) in segments(text):
        if seg_tokens(s):
            pos = b
    return pos


def rebuild(body, t, mp0, char_dels, ins):
    """由字符级计划重建 <text> 体字节(等长)。char_dels=字符下标集合。"""
    ds, n = set(char_dels), len(t)
    out, done = bytearray(), False
    for ci in range(n):
        if not done and ci == ins:
            out += b'\x20' * len(ds); done = True
        if ci in ds:
            continue
        nxt = mp0[ci + 1] if ci + 1 < n else len(body)
        out += body[mp0[ci]:nxt]
    if not done:
        out += b'\x20' * len(ds)
    return bytes(out)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    sd = open(src, 'rb').read()
    base = MENU_LBA * 2048
    r = struct.unpack_from('<12I', sd, base + TAB_OFF + TAB_STEP * XML_IDX)
    stored, real, off = r[6], r[7], r[8]
    print('[in ] %s' % src)
    print('[in ] MENU.IMG#283 stored=%d real=%d off=0x%X slot@0x%X' % (stored, real, off, base + off))
    subs = subs_of(sd[base + off:base + off + stored])
    assert len(subs) == 8, '子流 %d 个 (期望 8)' % len(subs)
    sizes = [s['S'] for s in subs]
    xml = b''.join(s['dec'] for s in subs)
    assert len(xml) == sum(sizes) == XML_LEN, 'XML 长度 %d != %d' % (len(xml), XML_LEN)
    print('[in ] XML %d B (子流解压 %s, 压缩 %s, 帧 %d / 槽 %d)'
          % (len(xml), sizes, [s['L'] for s in subs], sum(s['L'] + 8 for s in subs), stored))

    dc, dp = load_charset()
    ms = list(re.finditer(rb'<text>([^<]*)</text>', xml))
    assert len(ms) == 69, '<text> 条数 %d != 69' % len(ms)
    doc = {i: (m.start(1), m.end(1)) for i, m in enumerate(ms, start=1)}

    # ── 字节级重建无损性自检 (无删除时重建 == 原体) ──
    for i in range(1, 70):
        a, b = doc[i]
        body = xml[a:b]
        t, mp0 = dec_engine(body, dc, dp)
        if not re.search(r'[\u4e00-\u9fff]', t):
            continue
        assert rebuild(body, t, mp0, set(), comp_pos(t)) == body, '#%d 字节重建不自洽' % i
    print('[chk ] 69 条 <text> 字节级重建自洽 (无删除时原样还原) OK')

    # ── 白名单逐处断言 ──
    wl = {k: v for k, v in WHITELIST.items() if v}
    assert set(wl) <= set(doc), '白名单文档序越界'
    del_by_text, n_del = {}, 0
    for idx, items in sorted(wl.items()):
        a, b = doc[idx]
        for (o, pre, post) in items:
            assert a <= o < b, '#%d 偏移 0x%X 不在 <text> 体内' % (idx, o)
            assert xml[o] == 0x20, '#%d @0x%X 不是 0x20' % (idx, o)
            assert xml[o - len(pre) // 2:o].hex() == pre, '#%d @0x%X 前置字节不符' % (idx, o)
            assert xml[o + 1:o + 1 + len(post) // 2].hex() == post, '#%d @0x%X 后置字节不符' % (idx, o)
            del_by_text.setdefault(idx, []).append(o - a)
            n_del += 1
    assert n_del == N_DEL, '白名单条数 %d != N_DEL %d' % (n_del, N_DEL)
    print('[wl  ] 白名单 %d 条文本 / %d 处删除, 逐处 0x20+前后字节断言 OK' % (len(wl), n_del))

    # ── 折行复算 + 重建 ──
    new_body, n_line_chg = {}, 0
    for idx in sorted(del_by_text):
        a, b = doc[idx]
        body = xml[a:b]
        t, mp0 = dec_engine(body, dc, dp)
        char_dels = []
        for p in del_by_text[idx]:
            hit = [k for k in range(len(mp0)) if mp0[k] == p]
            assert len(hit) == 1 and t[hit[0]] == ' ', '#%d 字节 %d 不是空格字符' % (idx, p)
            char_dels.append(hit[0])
        ins = comp_pos(t)
        nb = rebuild(body, t, mp0, char_dels, ins)
        assert len(nb) == len(body), '#%d 等长断言失败 %d vs %d' % (idx, len(nb), len(body))
        t2, _ = dec_engine(nb, dc, dp)
        assert len(t2) == len(t), '#%d 解码长度变化 %d vs %d' % (idx, len(t2), len(t))
        mp = {}
        kx, ds = 0, set(char_dels)
        for i in range(len(t)):
            if i in ds:
                kx += 1
                continue
            mp[i] = i - kx + (len(ds) if i >= ins else 0)
        for SP in SP_ENSEMBLE:
            l0, c0 = char_layout(t, SP)
            l1, c1 = char_layout(t2, SP)
            assert c0 == c1, '#%d (SP=%d) 每段行数变化 %s -> %s' % (idx, SP, c0, c1)
            for i in range(len(t)):
                if i in ds:
                    continue
                assert l0[i] == l1[mp[i]], '#%d (SP=%d) 字符 %d %r 行号 %s -> %s' % (
                    idx, SP, i, t[i], l0[i], l1[mp[i]])
        n_line_chg += 1
        new_body[idx] = nb
    print('[wrap] %d 条文本: 对 SP∈%s 每个模型, 每段行数不变 + 逐字符行号不变 (版式零变化) OK'
          % (n_line_chg, list(SP_ENSEMBLE)))

    # ── 组装新 XML ──
    parts, pos = [], 0
    for i in range(1, 70):
        a, b = doc[i]
        parts.append(xml[pos:a])
        parts.append(new_body.get(i, xml[a:b]))
        pos = b
    parts.append(xml[pos:])
    new_xml = b''.join(parts)
    assert len(new_xml) == len(xml), 'XML 总长变化 %d' % len(new_xml)

    for pat in (rb'<text>', rb'</text>', rb'<studio', rb'<group', rb'<item', rb'</SpecialFeatures>'):
        assert new_xml.count(pat) == xml.count(pat), '结构破坏: %s' % pat.decode()
    names0 = re.findall(rb'name="([^"]*)"', xml)
    assert re.findall(rb'name="([^"]*)"', new_xml) == names0, 'name 属性被改'
    print('[str ] 元素计数 + %d 个 name 属性逐字节不变 OK' % len(names0))

    # 逐条验证: 除白名单条目外其它 <text> 体逐字节不变
    ms2 = list(re.finditer(rb'<text>([^<]*)</text>', new_xml))
    assert len(ms2) == 69
    for i in range(1, 70):
        if i in new_body:
            continue
        assert ms2[i - 1].group(1) == ms[i - 1].group(1), '<text>#%d 意外变化' % i
    print('[str ] 其余 %d 条 <text> 逐字节不变 OK' % (69 - len(new_body)))

    # ── 重压: 只重压变了的子流 ──
    frame, n_repack, bnd = bytearray(), 0, []
    q = 0
    for k, S in enumerate(sizes):
        bnd.append((q, q + S)); q += S
    for k, S in enumerate(sizes):
        a, b = bnd[k]
        chunk = new_xml[a:b]
        if chunk == subs[k]['dec']:
            frame += subs[k]['raw']
            continue
        c = lzo_compress(chunk, level=7, use_m1=True, use_m4=True)
        back, err, _ = lzo1x_decompress(c, out_size=S)
        assert err is None and back == chunk, '子流 %d 回环失败' % k
        frame += struct.pack('<II', len(c), S) + c
        n_repack += 1
        print('[pack] 子流 %d 重压 %d → %d B' % (k, subs[k]['L'], len(c)))
    assert len(frame) <= stored, '超槽 %+d' % (len(frame) - stored)
    print('[pack] 帧 %d B / 槽 %d (余 %d), 重压 %d 个子流'
          % (len(frame), stored, stored - len(frame), n_repack))

    # ── 写盘 + 回读自验 ──
    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(base + off)
        f.write(bytes(frame) + b'\x00' * (stored - len(frame)))
        f.seek(base + off)
        rb = subs_of(f.read(stored))
        assert len(rb) == 8, '回读子流 %d 个' % len(rb)
        assert b''.join(x['dec'] for x in rb) == new_xml, '回读 XML 不符'
    print('[ver ] 回读 8 子流 → XML 逐字节一致')

    # ── 全盘逐字节校验(槽外) ──
    with open(src, 'rb') as f1, open(dst, 'rb') as f2:
        rest, bad = base + off, 0
        while rest > 0:
            n = min(8 << 20, rest)
            if f1.read(n) != f2.read(n):
                bad += 1
            rest -= n
        assert not bad, '槽前区域被改'
        print('[ver ] 槽前 %d B 逐字节不变' % (base + off))
        f1.seek(base + off + stored); f2.seek(base + off + stored)
        while True:
            x, y = f1.read(8 << 20), f2.read(8 << 20)
            assert x == y, '槽后区域被改'
            if not x:
                break
        print('[ver ] 槽后至盘尾逐字节不变')

    h_src = hashlib.sha256(sd).hexdigest()
    h_dst = hashlib.sha256(open(dst, 'rb').read()).hexdigest()
    print('[hash] src %s' % h_src)
    print('[hash] dst %s' % h_dst)
    info = dict(patch='tools/iso_build/patch_zh_sf_spaces_all.py',
                src_iso=os.path.abspath(src), src_sha256=h_src,
                dst_iso=os.path.abspath(dst), dst_sha256=h_dst,
                target='MENU.IMG#283 EN_SPECIAL_FEATURE.XML <text> (特别收录各内页介绍)',
                scope='reflow-inserted visible spaces (use _xml82 lineage as proof)',
                n_texts=len(new_body), n_deleted=n_del,
                xml_len_before=len(xml), xml_len_after=len(new_xml),
                substream_sizes=sizes, n_substream_repacked=n_repack)
    if len(sys.argv) > 3:
        json.dump(info, open(sys.argv[3], 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print('[json] -> %s' % sys.argv[3])
    return info


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
