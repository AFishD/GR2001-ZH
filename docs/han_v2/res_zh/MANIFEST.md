# EN_STRINGS_ZH.bin 翻译清单

- 基准: `C:\gr_build\tmp\en_strings_res_expanded.bin` (128,545 B, 纯净展开态)
- 约束: 44 汉字槽位表 (han_v2\hanzi_assign_expanded.json),
  每个汉字 = 2 字节槽位对; 条目 attr=0; 组/条目结构不变.
- 选中 68 条, 全部完成翻译; 字表用字 32/44: 一 上 下 信 切 前 右 员 器 图 地 天 小 左 弹 息 所 手 择 换 有 枪 武 移 组 聊 行 视 进 选 野 队
- 文件总长: 128545 -> 128266 字节 (Δ-279)

| 组.条目 | 英文原文 | 中文译文 | 译法备注 |
|---|---|---|---|

## G58 main_ui_pool (主 UI 池)
| G58.I003 | Ok | 行 | 行=可以/确认; 字表无“好/是”; 用字: 行 |
| G58.I004 | OK | 行 | 同上; 用字: 行 |
| G58.I091 | Left and right to select soldier. | 左右选择队员. | 官方PC无此句; 全部字表字; 用字: 左 右 选 择 队 员 |
| G58.I092 | Left and right to change soldiers order. | 左右换队员. | 省略“顺序”, 保留换位语义; 用字: 左 右 换 队 员 |
| G58.I095 | Select the soldier's kit. | 选择队员武器. | kit(装备包)借译为武器; 用字: 选 择 队 员 武 器 |
| G58.I126 | Information | 信息 | 信/息 皆在字表; 用字: 信 息 |
| G58.I142 | INFORMATION | 信息 | 同 I126; 用字: 信 息 |
| G58.I186 | PROCEED | 前进 | 前进=继续推进; 用字: 前 进 |
| G58.I191 | ROSTER | 队员 | 花名册->队员名单; 用字: 队 员 |
| G58.I196 | Select Soldier | 选择队员 | 用字: 选 择 队 员 |
| G58.I197 | PLATOON SELECTOR | 小队选择 | platoon->小队; 用字: 小 队 选 择 |
| G58.I198 | SQUAD SELECTOR | 小组选择 | squad->小组, 与小队区分; 用字: 小 组 选 择 |
| G58.I200 | PICKS KIT | 选武器 | kit->武器; 用字: 选 武 器 |
| G58.I201 | PICKS TEAM | 选组 | 用字: 选 组 |
| G58.I203 | Weapon | 武器 | 武/器 皆在字表; 用字: 武 器 |
| G58.I230 | Information | 信息 | 同 I126; 用字: 信 息 |
| G58.I245 | advance | 前进 | ROE 命令; 官方PC: 前进; 用字: 前 进 |
| G58.I305 | TEAM | 小组 | 用字: 小 组 |
| G58.I317 | SOLDIER SELECTION | 队员选择 | 用字: 队 员 选 择 |
| G58.I318 | KIT/ROSTER SELECTION | 武器/队员选择 | kit/roster 借译; 用字: 武 器 队 员 选 择 |
| G58.I326 | INFO | 信息 | 用字: 信 息 |
| G58.I331 | DONE | 行 | 完成->行(字表无“完成”); 用字: 行 |
| G58.I333 | MAP | 地图 | 地/图 皆在字表; 用字: 地 图 |
| G58.I360 | INFORMATION | 信息 | 同 I126; 用字: 信 息 |
| G58.I361 | ROSTER | 队员 | 同 I191; 用字: 队 员 |
| G58.I362 | SOLDIER | 队员 | 士兵->队员(GR 语境); 用字: 队 员 |
| G58.I369 | TEAM SELECTOR | 选组 | 与 I198 措辞区分; 用字: 选 组 |
| G58.I409 | TEAM | 小组 | 同 I305; 用字: 小 组 |
| G58.I412 | MAP:  | 地图:  | 保留原尾随空格; 用字: 地 图 |
| G58.I423 | Team | 小组 | 用字: 小 组 |
| G58.I425 | MAP INFO | 地图信息 | 用字: 地 图 信 息 |
| G58.I487 | COMMAND MAP | 地图 | 指挥地图; 指/挥无字, 取地图; 用字: 地 图 |
| G58.I505 | Team | 小组 | 用字: 小 组 |
| G58.I507 | Platoon 1  | 小队 1  | 保留尾随空格; 用字: 小 队 |
| G58.I508 | Platoon 2  | 小队 2  | 用字: 小 队 |
| G58.I509 | Platoon 3  | 小队 3  | 用字: 小 队 |
| G58.I510 | Platoon 4  | 小队 4  | 用字: 小 队 |
| G58.I532 | Rifleman | 枪手 | 官方PC“突击队员”字表不可达; 枪手; 用字: 枪 手 |
| G58.I565 | Rifleman | 枪手 | 同 I532; 用字: 枪 手 |
| G58.I570 | RIFLEMAN | 枪手 | 同 I532; 用字: 枪 手 |
| G58.I647 | SOLDIER | 队员 | 同 I362; 用字: 队 员 |
| G58.I659 | Team > | 小组 > | 命令菜单根项; 用字: 小 组 |
| G58.I660 |   All > |   所有 > | 官方PC“所有小组...”; 保留前导空格; 用字: 所 有 |
| G58.I742 | Weapons | 武器 | Game Information 子项; 用字: 武 器 |
| G58.I752 | Advance | 前进 | 命令菜单; 官方PC: 前进; 用字: 前 进 |
| G58.I757 | Alpha Team | Alpha 小队 | 混排: 队名保留英文; 用字: 小 队 |
| G58.I758 | Bravo Team | Bravo 小队 | 混排: 队名保留英文; 用字: 小 队 |
| G58.I761 | Map | 地图 | 用字: 地 图 |
| G58.I762 | Change | 换 | 按钮提示 Change->换; 用字: 换 |
| G58.I371 | NEXT MAP | 下一地图 | 用字: 下 一 地 图 |
| G58.I689 | Next Map:  | 下一地图:  | 保留尾随空格; 用字: 下 一 地 图 |

## G59 menu_mp_ui
| G59.I003 | REPICK TEAM | 换组 | repick->换组; 用字: 换 组 |
| G59.I018 | MAP | 地图 | 用字: 地 图 |
| G59.I020 | Map | 地图 | 用字: 地 图 |

## G61 control_labels (按键设置)
| G61.I001 | Move Forward | 前进 | 官方PC key "forward"=前进; 用字: 前 进 |
| G61.I003 | Move Left | 左移 | 官方PC: 向左平移; 取左移; 用字: 左 移 |
| G61.I004 | Move Right | 右移 | 官方PC: 向右平移; 取右移; 用字: 右 移 |
| G61.I023 | Chat | 聊天 | 官方PC: 聊天; 用字: 聊 天 |
| G61.I024 | Toggle Camera | 切换视野 | 官方PC“切换视角”无“角”字; 视野代; 用字: 切 换 视 野 |
| G61.I039 | Change Magazine | 换弹 | 官方PC: 更换弹夹; 取换弹; 用字: 换 弹 |
| G61.I045 | Follow Next | 下一队员 | 官方PC: 选择下一个队员; 用字: 下 一 队 员 |
| G61.I046 | Follow Last | 上一队员 | 官方PC: 选择上一个队员; 用字: 上 一 队 员 |

## G65 options_ui (选项界面)
| G65.I040 | COMMAND MAP | 地图 | 同 G58.I487; 用字: 地 图 |
| G65.I054 | Team Chat | 小组聊天 | 官方PC team_chat=小组聊天; 用字: 小 组 聊 天 |
| G65.I112 | Command Map | 地图 | 同 G58.I487; 用字: 地 图 |
| G65.I116 | Reload Weapon | 换弹 | 官方PC: 更换弹夹; 用字: 换 弹 |
| G65.I117 | Cycle Weapon | 切换武器 | 用字: 切 换 武 器 |
| G65.I118 | Cycle Soldier  | 切换队员  | 用字: 切 换 队 员 |
