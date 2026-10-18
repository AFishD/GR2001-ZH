# -*- coding: utf-8 -*-
r"""make_review_r68.py — 生成 round68「特别收录」145 条标题体检表 + 落盘用编辑表.

输入 (只读):
  work/builds/GR_ZH98/temp/r68/GR_ZH111_base_text_sf_titles.csv   ← 从 GR_ZH111.iso 现 dump
  work/builds/GR_ZH109/text_backup_before_wrapfix/GR_ZH109_text_long.csv  ← 用户新译 (text_edited)
  work/builds/GR_ZH111/text/GR_ZH111_text_long.csv                ← 盘上正文 (text_zh)
输出 (只写 r68/):
  titles_review.csv        ← 体检表 (列见 --help / 报告)
  GR_ZH114_text_sf_titles.csv  ← 给 GR_ZH114 构筑用的表 (只改 text_edited)
用法: python make_review_r68.py
"""
import csv
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                               # noqa: E402

BASE = os.path.join(HERE, 'GR_ZH111_base_text_sf_titles.csv')
REVIEW = os.path.join(HERE, 'titles_review.csv')
EDIT_TABLE = os.path.join(HERE, 'GR_ZH114_text_sf_titles.csv')
CHARSET_TXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r64',
                           'available_charset.txt')

# ═══════════════════════════════════════════════════════════════════════════
#  基础字集 = GR_ZH111 现役 1285 字 (r64 导出的清单, 生成于字库扩容之前)
# ═══════════════════════════════════════════════════════════════════════════
def load_baseline_chars():
    with io.open(CHARSET_TXT, 'r', encoding='utf-8') as f:
        txt = f.read()
    txt = ''.join(ln for ln in txt.splitlines() if not ln.startswith('#'))
    return set(ch for ch in txt if ch.strip())


BASE_CHARS = load_baseline_chars()

# ═══════════════════════════════════════════════════════════════════════════
#  体检结论 (逐条; 已改的写在 EDITS 里)
# ═══════════════════════════════════════════════════════════════════════════
STUDIO_IDS = ['A0001', 'A0031', 'A0044', 'A0054', 'A0086', 'A0112', 'A0115',
              'A0123', 'A0137', 'A0142']
EMPTY_IDS = ['A%04d' % n for n in range(45, 54)]
DS_MISSION_IDS = (['A%04d' % n for n in range(23, 31)]        # group  DS mission 1..8
                  + ['A%04d' % n for n in range(36, 44)]      # group  DS Mission 1..8
                  + ['A%04d' % n for n in range(105, 112)])   # item   DS Mission 1..7

STUDIO_REASON = (
    '【保持】studio 档在 **五份语言副本里逐字节相同** (本轮独立复核 10/10 份: DE/ES/FR/IT '
    '的 group/item 名都是各自语言 (**132/145 条不同**), 只有这 10 个 studio 名**一个字节都不差**) '
    '⇒ 它是菜单找条目的**结构键**, 不是文案。硬证据: `SFStudio::GetSdutio(eSFStudioType)` '
    '(ELF 0x1F6E30) 是**枚举→名字的跳转表** (0x577780[10] → RSString("Movies"/"ConceptSketches"/…)'
    '), 返回值被 10 处 `RSString::operator==` 消费; 实验 P1 (只改 ELF) / GR_ZH78 (只改 XML) / '
    'GR_ZH80 (两边都改) **全部把光标搞坏** (首行高亮 BGR 异常), 只有**不动它们**才正常。'
    '屏幕上的中文名 (影片/设定图/音乐/武器…) 由 ELF/RES 那侧另外提供, **不在本表**。'
    '⇒ 建议保持英文原样; 本轮一个字未动。')

EMPTY_REASON = (
    '【未改·待你定】原版 EN/IT **本来就是空** (`<item name="" pic="sf_Music_01.rsb">`, '
    '`<text></text>`)。DE/ES/FR 三份副本只是填了**占位编号**: 德 `Musik 1..9` / 西 `Música N` / '
    '法 `Musique N` (A0045 是 `Music 1`)。所以这不是"漏译", 是原版就没写名字。'
    '⇒ 建议要么**保持空白** (与 EN 一致), 要么照 DE/ES/FR 的口径补成 `音乐 1`..`音乐 9` '
    '(9 条都同长 4 字, 无版式风险)。要不要补 **请你定**; 要补我一条命令就能加。')

# 逐条 (id -> dict(verdict, suggest, reason, applied))
D = {}


def set_(idn, verdict, suggest, reason, applied=False, extra='', need=''):
    D[idn] = dict(verdict=verdict, suggest=suggest, reason=reason, applied=applied,
                  extra=extra, need=need)


# ── studio: 结构键 ──────────────────────────────────────────────────────────
for k in STUDIO_IDS:
    set_('SFXML:' + k, '结构键不该译', '(保持英文原样)', STUDIO_REASON)

# ── 空标题 ─────────────────────────────────────────────────────────────────
for n, k in enumerate(EMPTY_IDS, 1):
    set_('SFXML:' + k, '空标题待定', u'音乐 %d' % n, EMPTY_REASON)

# ── group: 概念草图 / 兵种 / 战役分组 (保留) ───────────────────────────────
for k, s, why in (
        ('A0002', u'士兵', u'`Soldiers` 直译, 与专家/敌人/训练同族, 用词一致。'),
        ('A0003', u'专家1', u'`Specialists 1`; 编号直译, 与专家2成对。'),
        ('A0004', u'专家2', u'`Specialists 2`; 同上。'),
        ('A0005', u'敌人', u'`Enemies` 直译。'),
        ('A0006', u'训练', u'`Training` 直译。'),
        ('A0032', u'士兵', u'`Soldiers` (Background 档下的同一组), 与 A0002 口径一致。'),
        ('A0033', u'幽灵行动', u'`Ghost Recon` = 幽灵行动 (用户译文全篇用《幽灵行动》)。'),
        ('A0034', u'幽灵行动车辆', u'`GR vehicles`; GR = 幽灵行动, 与 A0033 一致。')):
    set_('SFXML:' + k, '正确', s, u'【保持】' + why)
for n, k in enumerate(['A%04d' % i for i in range(7, 22)], 1):
    set_('SFXML:' + k, '正确', u'幽灵行动®任务%d' % n,
         (u'【保持】`GR Mission {n}`; 与语言表菜单串 **LANG:G058.I724「幽灵行动®任务」** 同款 '
          u'(含 ®), 15 条口径统一。').format(n=n))

# ── group: DS 任务 (错译 → 已改) ───────────────────────────────────────────
for k in DS_MISSION_IDS:
    idx = int(k[1:])
    num = (idx - 22) if idx <= 30 else ((idx - 35) if idx <= 43 else (idx - 104))
    set_('SFXML:' + k, '错译', u'荒漠围攻任务%d' % num,
         u'【已改】英文原名 `DS Mission %d` 里的 **DS = Desert Siege** —— 《幽灵行动》的**资料片**'
         u'《荒漠围攻》(2002), 不是 1991 年海湾战争的"沙漠风暴行动" (Desert Storm)。'
         u'用户自己的新译正文里 **SFXML:T0030** 原文 "the one used in Desert Siege" 就译作'
         u'**《荒漠围攻》**。⇒ 这些条目在"特别收录"里指的是资料片的关卡, 旧译"沙漠风暴"是'
         u'**换了一个历史事件**。新译 4 字 ↔ 旧译 4 字 (**版式零变化**)。' % num,
         applied=True)

# ── item: DS 片头/片尾 ─────────────────────────────────────────────────────
for k, tail in (('A0089', u'片头'), ('A0090', u'片尾')):
    set_('SFXML:' + k, '错译', u'荒漠围攻' + tail,
         u'【已改】理由同 DS 任务: `DS` = Desert Siege = 用户译文里的《荒漠围攻》, '
         u'不是 Desert Storm (沙漠风暴)。字形宽度不变 (%s 6 字 → 6 字)。' % tail, applied=True)

# ── group: DS 士兵 / 车辆 (保留) ───────────────────────────────────────────
set_('SFXML:A0022', '可改好', u'荒漠围攻士兵',
    u'【未改·待你定】英文 `DS Soldiers` 里的 DS 同样是 Desert Siege。旧译用"沙漠"做**缩写**, '
    u'本身不算错 (沙漠=desert), 与 EN 的缩写口径一致; 但同一份列表里会同时出现'
    u'「荒漠围攻任务1」与「沙漠士兵」。要完全统一可改成 `荒漠围攻士兵` (**+2 字 / +32px**, '
    u'标题条偏长风险)。**本轮不动**, 等你一句话。')
set_('SFXML:A0035', '可改好', u'荒漠围攻车辆',
    u'【未改·待你定】同 A0022: `DS vehicles`。建议与 A0022 一起决定改或不改。')

# ── 武器 / 装备 ────────────────────────────────────────────────────────────
set_('SFXML:A0055', '可改好', u'反步兵地雷 (M18)',
    u'【未改·待你定】英文 `Claymore (M18 Claymore)`; 用户译文 T0010 原话是'
    u'「M18 **定向反步兵地雷**由曲面的…」。现译「定向地雷」不算错 (阔剑本来就是定向雷), '
    u'只是省了"反步兵"。★ 若按用户原文全称 `定向反步兵地雷 (M18)` 会 **+3 字 (+48px)**; '
    u'折中写法 `反步兵地雷 (M18)` 只 **+1 字 (+16px)** 且用上用户的原词。'
    u'**标题条会截断, 所以本轮没动** —— 请挑一个 (或保持现状)。')
set_('SFXML:A0056', '错译', u'爆破装药 (M2)',
    u'【已改】英文原名 `Demo Charge (M2 Demolitions Charge)` = **爆破装药/爆破药块**; '
    u'旧译"定向炸药"把 `Demolitions Charge` 读成了"有方向性的炸药" (那是成形装药/定向爆破), '
    u'用户译文 T0011 首句就写着「M2**爆破装药**是一种定向聚能装药」。等长 (4 字↔4 字)。'
    u'★ 这一条是 round63 演示盘的做法, 但**现役 GR_ZH111 基底上还没落地** (它的基底是 GR_ZH109, '
    u'没带 round63 的标题改动), 本轮重新落一次。', applied=True)
set_('SFXML:A0057', '错译', u'破片手榴弹 (M67)',
    u'【已改】英文 `FRAG (M67 Hand Grenade)`; 用户译文 T0012 首句「M67是美军现役制式'
    u'**破片手榴弹**」。旧译"杀伤手雷"不是制式术语 (手雷=口语), 且与正文用词不一致。'
    u'**+1 字 (+16px)**, 总宽 12 字, 远低于偏长线 (15~16 字才被标偏长)。', applied=True)
for k, s in (('A0058', u'M24 狙击步枪'), ('A0059', u'L96A1 狙击步枪'),
             ('A0060', u'SVD 狙击步枪')):
    set_('SFXML:' + k, '正确', s, u'【保持】狙击步枪分类正确; 与用户译文 T0013/T0014/T0015 '
                                 u'(M24/L96A1/SVD) 对得上。')
set_('SFXML:A0061', '正确', u'M82A1 反器材步枪',
    u'【保持】M82A1 的美军分类就是**反器材步枪** (anti-materiel rifle); 用户译文 T0016 只说到'
    u'「.50口径的半自动步枪」, 但没有冲突 —— 反器材步枪更准确, 也更短。')
set_('SFXML:A0062', '正确', u'M16A2 突击步枪',
    u'【保持】用户译文 T0017「M16A2是美国陆军标准制式步枪」, 分类一致 (突击步枪=assault rifle)。')
set_('SFXML:A0063', '正确', u'M16/M203',
    u'【保持】型号代号; **五份语言副本逐字节相同** (EN/DE/ES/FR/IT 都不译) ⇒ 原版就当专名。')
set_('SFXML:A0064', '正确', u'OICW',
    u'【保持】型号代号; 五份副本相同。用户译文 T0019 保留了 `OICW` 并给出全称「目标单兵战斗武器」。')
set_('SFXML:A0065', '错译', u'M4 卡宾枪',
    u'【已改】英文原名 `M4`; 用户译文 T0020 首句「**M4卡宾枪**是M16步枪的缩短型」。'
    u'旧译"M4 短突击步枪"错在**制式分类** (M4 = carbine 卡宾枪; 真正的短突击步枪是 9A-91 那一类)。'
    u'**−2 字 (−32px)**, 顺带把宽度让出来。★ 同 A0056, 这是 round63 演示盘的改动, '
    u'现役 GR_ZH111 基底上还没有, 本轮重新落一次。', applied=True)
set_('SFXML:A0066', '可改好', u'SA-80 卡宾枪',
    u'【未改·待你定】用户译文 T0021 把 SA-80 说成「L85单兵武器的**卡宾缩短**型」—— 照 round63 '
    u'改 M4 的同一把尺子 (正文说 carbine ⇒ 标题写卡宾枪), 这里也该写 `SA-80 卡宾枪` (−2 字)。'
    u'⚠ 但 SA-80/L85 在军迷认知里普遍是**突击步枪**, 游戏正文那句 "carbine version" 讲的是'
    u'枪族关系。**两种口径都站得住, 所以请你定**; 本轮保持"突击步枪"。')
set_('SFXML:A0067', '正确', u'MP5 冲锋枪', u'【保持】用户译文 T0022 同词 (冲锋枪)。')
set_('SFXML:A0068', '正确', u'MP5SD 微声冲锋枪',
    u'【保持】用户译文 T0023 说"一体式消音器版本"; `微声冲锋枪` 是制式叫法, 与"消音器"不冲突。')
set_('SFXML:A0069', '正确', u'M249 班用机枪',
    u'【保持】用户译文 T0024「M249 SAW（**班用自动武器**）」; 班用机枪 = 同一族的制式简称。')
set_('SFXML:A0070', '正确', u'MG3 通用机枪', u'【保持】MG3 的制式分类就是通用机枪。用户译文 T0025 未给分类, 无冲突。')
set_('SFXML:A0071', '正确', u'RPK74 轻机枪',
    u'【保持】用户译文 T0026「以胜任**轻机枪**的角色定位」—— 与标题逐字对得上。')
set_('SFXML:A0072', '正确', u'M9 手枪', u'【保持】用户译文 T0027「该枪为9毫米**手枪**」。')
set_('SFXML:A0073', '正确', u'M9SD 微声手枪', u'【保持】同 A0068 的口径 (SD = 消音/微声)。')
set_('SFXML:A0074', '正确', u'M136 火箭筒',
    u'【保持】用户译文 T0029「M136为一次性**无后坐力武器**」; `火箭筒` 是玩家口径的通称, '
    u'与正文不冲突 (AT4 打的确实是火箭弹), 而且更短。')
set_('SFXML:A0075', '正确', u'Groza 突击步枪',
    u'【保持】用户译文 T0030 逐字同款「**Groza突击步枪**专为俄罗斯内务部特种部队设计」。')
set_('SFXML:A0076', '正确', u'AN-94 突击步枪',
    u'【保持】用户译文 T0031 未点名型号, 只说"俄制AK-74的继任者"; AN-94 正是该枪, 分类正确。')
set_('SFXML:A0077', '可改好', u'野牛冲锋枪 (9mm)',
    u'【未改·待你定】用户译文 T0032 通篇叫它「**野牛冲锋枪**」(Bizon 的俄语含义就是野牛)。'
    u'改成 `野牛冲锋枪 (9mm)` 会 **−4 字** (15→11), 顺带**摘掉"偏长"标记**; '
    u'代价是标题里再也看不到拉丁名 `Bizon` (正文里也没有)。'
    u'⇒ 这是个**命名风格**取舍 (保留拉丁型号 vs 纯中文), 请你定; 本轮保持现状。')
set_('SFXML:A0078', '可改好', u'9A-91 紧凑型突击步枪',
    u'【未改·待你定】用户译文 T0033「9A-91是俄制**紧凑型突击步枪**」。现译"短突击步枪"'
    u'本身也通 (AKS-74U 那类就叫短突击步枪, round63 也是这么论证 M4 的), 只是与用户用词不同; '
    u'改成"紧凑型"要 **+2 字 (+32px)**。⇒ **不必要的变化 + 变长, 本轮不动**。')
set_('SFXML:A0079', '正确', u'M60 机枪', u'【保持】用户译文 T0034 只说"该型美制机枪…被称为猪"; `机枪` 无冲突。')
set_('SFXML:A0080', '错译', u'FN-FAL 步枪 (伞兵型)',
    u'【已改】英文原名 `FN-FAL Para`: `Para` = **伞兵型** (折叠枪托的空降型), 不是"短型"; '
    u'用户译文 T0035 自己就写着「**伞兵型**稍短且更轻便」⇒ 旧译与同一条目的正文自相矛盾。'
    u'**+1 字 (+16px)**, 总宽 15 字 (偏长档, 实机需看一眼)。'
    u'★ 同 A0056/A0065, round63 演示改动, 现役基底上未落地, 本轮重新落一次。', applied=True)
for k, s in (('A0081', u'PSG-1 狙击步枪'), ('A0082', u'M98 狙击步枪'),
             ('A0083', u'PKM 通用机枪')):
    set_('SFXML:' + k, '正确', s,
         u'【保持】分类与用户译文 T0036/T0037/T0038 一致 (PSG-1 远程战术狙击枪 / M98 美制 .338 '
         u'半自动 / PKM 俄制 PK 改进型)。')
set_('SFXML:A0084', '可改好', u'激光测距仪 (AN/GVS-5)',
    u'【未改·待你定】用户译文 T0039「AN/GVS-5是一种轻型便携**双筒望远镜式激光测距仪**」。'
    u'EN 名是 `Binoculars (AN/GVS-5 Binoculars)`, 所以"测距**望远镜**"抓的是 Binoculars 那一半, '
    u'"激光测距仪"抓的是 Range Finder 那一半 —— **两者等长 (15 字)**。'
    u'游戏里它是望远镜+测距两用, 现译其实更贴合用途, **本轮不动**; 想统一到用户用词随时可换。')
set_('SFXML:A0085', '正确', u'传感器 (AN/GSQ-187)',
    u'【保持】用户译文 T0040「AN/GSQ-187是一种布设式远程**传感器**」逐字对得上。')
for k, s in (('A0087', u'幽灵行动片头'), ('A0088', u'幽灵行动片尾')):
    set_('SFXML:' + k, '正确', s, u'【保持】`GR = Ghost Recon = 幽灵行动`, 与用户译文用词一致; 片头/片尾通顺。')
for n, k in enumerate(['A%04d' % i for i in range(91, 105)], 1):
    set_('SFXML:' + k, '正确', u'幽灵行动®任务%d' % n,
         u'【保持】`GR Mission %d`; 与语言表菜单串 **LANG:G058.I724「幽灵行动®任务」** 逐字同款 '
         u'(含 ®), 全列表 15 条口径统一。' % n)
set_('SFXML:A0113', '错译', u'恐惧的总和',
    u'【未改·需新字】英文 `The Sum of All Fears` = 2002 年同名电影 (中文通行名《**恐惧的总和**》, '
    u'台译《惊天核网》)。现译"极限危机"**不是**这部电影的任何通行译名, 属于改写。'
    u'★ 本轮**做不了**: `恐` `惧` 两个字**不在现役 1285 字里** (实测 encodable=False)。'
    u'⇒ 列进"等扩容"清单。备选 `惊天核网` 的用字也要单独查 (见 extra_chars)。',
    extra=u'恐惧', need='yes')
set_('SFXML:A0114', '正确', u'XIII',
    u'【保持】游戏代号; **五份语言副本逐字节相同** (EN/DE/ES/FR/IT 全都不译) ⇒ 原版当专名。')
set_('SFXML:A0116', '正确', u'国会最高勋章',
    u'【保持 — 这就是用户自己的用词】用户新译 T0043 原文: 第一处叫「**荣誉勋章**」, '
    u'但紧接着自己写了「由总统以国会名义颁发, 所以又称"**国会最高勋章**"」—— 也就是说'
    u'`Congressional Medal of Honor` 的**别名就是用户写的"国会最高勋章"**, 标题用它没有错。'
    u'★ 想用主名「荣誉勋章」需要 `荣`: 实测 `荣` 现在**能编码但没有字形** (扩容任务刚把码位加进 '
    u'JSON, 字形还没画) ⇒ **要等扩容盘**。本轮**不改**。', extra=u'荣', need='optional')
set_('SFXML:A0117', '正确', u'优异服役十字勋章',
    u'【保持】用户新译 T0044 写「**杰出**服役十字勋章」; 盘上正文 (缩减后) 是「**优异**服役十字勋章」。'
    u'`杰` 只有码位没有字形 (扩容中) ⇒ 标题跟**盘上正文**一致才是对的, 本轮不改。',
    extra=u'杰', need='optional')
set_('SFXML:A0118', '正确', u'银星勋章', u'【保持】用户新译 T0045 与盘上正文都是「银星勋章」, 逐字一致。')
set_('SFXML:A0119', '正确', u'战功星章',
    u'【保持】用户新译 T0046 写「**铜星**勋章」(制式名), 盘上正文因缺 `铜` 用了旧名「战功星章」。'
    u'标题只有跟盘上正文一致才不打架 ⇒ 不改; 要改回"铜星勋章"得等 `铜` 进字库。', extra=u'铜', need='optional')
set_('SFXML:A0120', '正确', u'战伤勋章',
    u'【保持】用户新译 T0047 写「**紫心**勋章」, 盘上正文因缺 `紫` 用旧名「战伤勋章」。'
    u'同上, 标题与正文一致优先。', extra=u'紫', need='optional')
set_('SFXML:A0121', '正确', u'步兵战斗章 (CIB)',
    u'【保持】用户新译 T0048 写「步兵战斗**徽章**」, 盘上正文因缺 `徽` 用「步兵战斗章」。'
    u'标题与正文一致 ⇒ 不改。', extra=u'徽', need='optional')
set_('SFXML:A0122', '错译', u'战役勋表',
    u'【已改】英文 `Campaign Ribbons`。用户新译 T0049 与**盘上正文**都写「**战役勋表**」'
    u'(正文里出现两次: "战役勋表用于奖励…" "每项战役都有专门设计的勋表"), 只有标题写成'
    u'"战役勋**带**" ⇒ 标题与正文自相矛盾。等长 (4 字↔4 字)。', applied=True)
for k, s in (('A0124', u'斯通'), ('A0125', u'奥萨泽'), ('A0126', u'格雷')):
    set_('SFXML:' + k, '正确', s, u'【保持】与盘上正文档案标题 (吉克·斯通 / 古拉姆·奥萨泽 / 苏安·格雷) 的姓一致。')
set_('SFXML:A0127', '正确', u'汉克尔',
    u'【保持】用户新译写「克劳斯·**亨**克尔」, 盘上正文因缺 `亨` 改成「克劳斯·**汉**克尔」⇒ '
    u'标题跟正文一致才对。要回到"亨克尔"得等 `亨` 进字库。', extra=u'亨', need='optional')
set_('SFXML:A0128', '正确', u'亚各布斯',
    u'【保持】用户新译写「威尔·**雅**各布斯」, 盘上正文因缺 `雅` 用「威尔·**亚**各布斯」⇒ '
    u'标题跟正文一致。要回到"雅各布斯"得等 `雅`。', extra=u'雅', need='optional')
set_('SFXML:A0129', '错译', u'拉米雷斯',
    u'【已改】英文 `H. Ramirez`。用户新译 T0055 是「汉利·**拉米雷斯** SGT」, 盘上正文同样是'
    u'「汉利·**拉米雷斯**」; 只有标题还留着**上一代旧译**「拉默雷斯」⇒ 标题与正文两个人名。'
    u'等长 (4 字↔4 字)。★ 这也是 round63 演示盘的做法, 现役 GR_ZH111 基底上还没落地, 本轮重新落一次。',
    applied=True)
set_('SFXML:A0130', '正确', u'高登',
    u'【保持】用户新译写「哈罗德·巴兹·**戈**登」, 盘上正文因缺 `戈` 用「**高**登」⇒ 标题跟正文一致。'
    u'要回到"戈登"得等 `戈`。', extra=u'戈', need='optional')
set_('SFXML:A0131', '错译', u'加林斯基',
    u'【已改】英文 `A. Galinksy` (原版把 Galinsky 拼错了)。用户新译 T0057 与盘上正文都是'
    u'「阿斯特拉·**加林斯基**」, 只有标题是旧译「加**利**斯基」⇒ 标题与正文不一致。'
    u'等长 (4 字↔4 字)。', applied=True)
set_('SFXML:A0132', '错译', u'科安',
    u'【已改】英文 `L. Cohen`。用户新译写「林迪·**科恩**」, 盘上正文因缺 `恩` 用'
    u'「林迪·**科安**」; 标题却是旧译「科**汉**」⇒ 跟正文不一致。等长 (2 字↔2 字)。', applied=True)
set_('SFXML:A0133', '错译', u'曼兹',
    u'【已改】英文 `D. Munz`。用户新译写「迪特·**蒙茨**」, 盘上正文因缺 `蒙/茨` 用'
    u'「迪特·**曼兹**」; 标题却是旧译「门兹」⇒ 跟正文不一致。等长 (2 字↔2 字)。', applied=True)
set_('SFXML:A0134', '正确', u'坦尼',
    u'【保持】用户新译 T0060 与盘上正文都是「尼格尔·坦尼」(用户新译原写"奈杰尔·坦尼", 缺 `奈/杰`) 。')
set_('SFXML:A0135', '错译', u'海尔',
    u'【已改】英文 `J. Haile`。用户新译 T0061 与盘上正文都是「约迪特·**海尔**」, '
    u'标题却是旧译「海利」⇒ 跟正文不一致。等长 (2 字↔2 字)。', applied=True)
set_('SFXML:A0136', '错译', u'伊布拉信',
    u'【已改】英文 `S. Ibrahim`。用户新译写「斯科特·**易卜拉欣**」, 盘上正文因缺 `卜/欣` 用'
    u'「斯科特·**伊布拉信**」; 标题却是旧译「伊布拉伊姆」⇒ 跟正文不一致。'
    u'新旧都 5 字 (等长)。', applied=True)
set_('SFXML:A0138', '正确', u'何为幽灵？',
    u'【保持】`Who Are the Ghosts?`; 正文 T0063 的标题行《幽灵行动》：何为"幽灵"？与之呼应, '
    u'问号已在 round51 修正 (实机 A/B 验过)。')
set_('SFXML:A0139', '正确', u'兵种简介',
    u'【保持】`Soldier Classes`; 正文 T0064 的首行**就是**「兵种简介：」⇒ 逐字一致。')
for k, s in (('A0140', u'战争序幕 1'), ('A0141', u'战争序幕 2')):
    set_('SFXML:' + k, '正确', s,
         u'【保持】`Prologue to War N` 直译正确。正文 T0065/T0066 里的**文章大标题**是'
         u'「东欧与俄罗斯战役／非洲战役背景」, 那是文章自己的标题, 与菜单条目名本来就不同 '
         u'(EN 原版同样如此), **不是**不一致。')
for n, k in enumerate(['A0143', 'A0144', 'A0145'], 1):
    _cn = [u'一', u'二', u'三'][n - 1]
    _en = ['FIRST', 'SECOND', 'THIRD'][n - 1]
    set_('SFXML:' + k, '可改好', u'开发手记 %d' % n,
         (u'【未改·待你定】`Interview {n}` 直译就是"访谈", 现译「开发访谈 {n}」没错; '
          u'但正文 T{tn} 的文章标题是「**开发手记**：第{cn}辑」'
          u'(EN: DESIGNER DIARIES: {en} SET) —— 菜单条目名与文章标题不同 '
          u'**EN 原版也是这样**, 所以不算错。'
          u'想让菜单跟文章口径统一, 可改成「开发手记 {n}」(等长)。**请你定**。')
         .format(n=n, tn=66 + n, cn=_cn, en=_en))


def main():
    with io.open(BASE, 'r', encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 145, len(rows)
    cols = list(rows[0].keys())
    review, n_applied, n_ext = [], 0, 0
    stat = {}
    for r in rows:
        rid, tag = r['id'], r['tag']
        key = tag + ':' + rid.split(':')[1]
        d = D.get(rid)
        if d is None:
            raise SystemExit('!! 没有体检结论: %s' % rid)
        cur = r['text_edited']
        sug = d['suggest']
        # suggest 里的 "(保持英文原样)" 之类 -> 用现值
        sug_txt = cur if sug.startswith('(') else sug
        extra = ''.join(sorted(set(ch for ch in sug_txt
                                   if ord(ch) >= 0x80 and ch not in BASE_CHARS)))
        if not d['extra']:
            d['extra'] = extra
        if d['applied']:
            n_applied += 1
            r['text_edited'] = sug_txt
        stat[d['verdict']] = stat.get(d['verdict'], 0) + 1
        if d['need'] == 'yes':
            n_ext += 1
        review.append(dict(
            id=rid, tag=tag, text_en=r['text_en'], text_zh=r['text_zh'],
            verdict=d['verdict'], suggest=sug_txt, reason=d['reason'],
            n_chars_old=len(cur), n_chars_new=len(sug_txt),
            extra_chars=d['extra'], needs_expansion=d['need'] or 'no'))
    # ── 写体检表 ──
    rc = ['id', 'tag', 'text_en', 'text_zh', 'verdict', 'suggest', 'reason',
          'n_chars_old', 'n_chars_new', 'extra_chars', 'needs_expansion']
    with io.open(REVIEW, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, lineterminator='\r\n')
        w.writerow(rc)
        for x in review:
            w.writerow([x[c] for c in rc])
    # ── 写编辑表 (只改 text_edited) ──
    with io.open(EDIT_TABLE, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, lineterminator='\r\n')
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c] for c in cols])
    print('# verdict 分布: %s' % sorted(stat.items(), key=lambda kv: -kv[1]))
    print('# 已改 %d 条; needs_expansion=yes %d 条' % (n_applied, n_ext))
    print('# 体检表 %s' % REVIEW)
    print('# 编辑表 %s' % EDIT_TABLE)
    # 变化行的宽度
    print('\n%-13s %-22s -> %-24s %s' % ('id', 'text_zh(盘上)', 'text_edited(新)', 'version'))
    for r in rows:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
