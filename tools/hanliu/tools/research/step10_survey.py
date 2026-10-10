# -*- coding: utf-8 -*-
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import sys, re, json
sys.path.insert(0, os.path.join(REPO_ROOT, 'tools', 'gr_tools'))
from res_encode import parse_expanded

gr = parse_expanded(open(os.path.join(REPO_ROOT, 'work', 'tmp', 'gr_res', 'gr_en_strings_expanded.bin'),'rb').read())
def S(gi, si): return gr[gi-1].strings[si][0].decode('latin-1','replace')

MAP = json.load(open(os.path.join(REPO_ROOT, 'docs', 'han_v2', 'hanzi_assign_expanded.json'), encoding='utf-8'))

def zh(*toks):
    out = bytearray()
    for t in toks:
        if len(t) == 1 and t in MAP:
            out += bytes(MAP[t])
        else:
            out += t.encode('ascii')
    return bytes(out), ' '.join('%02X' % b for b in out)

MONTH = r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|March|April|June|July|September|October|November|December|Ft\.|Location)'
sub = {'C_obj':0,'C_brief':0,'C_result':0,'C_meta':0,'C_trig':0,'C_mp':0,'C_mpmap':0}
for g in list(range(19,34))+list(range(40,53)):
    for si in range(len(gr[g-1].strings)):
        t = S(g,si)
        if '{p}' in t or len(t) > 200: sub['C_brief'] += 1
        elif re.match(r'^(\d+ - |X - )', t): sub['C_obj'] += 1
        elif re.match(MONTH, t) or re.match(r'^\d{1,2}:\d{2}$', t) or re.match(r'^(M\d{2}|D\d{2}|TAC\d{2}|T0\d)', t):
            sub['C_meta'] += 1
        elif any(t.startswith(p) for p in ('Mission','Not enough','You ','The ','A truck','A Truck','All ','Civilian','Enemy has','US soldier','Demo Charge Set','Weapons Officer','No Enemy','The remaining','Ashenafi','Hostage','The Convoy','The Explosives','The Refinery','The Intelligence','The Enemy','The UN','The players','The last','The pilot','The game','Winner','Try to','Accumulate','Be the first','Your team','You are','Attackers','Defenders')):
            sub['C_result'] += 1
        else: sub['C_trig'] += 1
for g in range(1,12): sub['C_mp'] += len(gr[g-1].strings)
for g in list(range(34,40))+list(range(53,58)): sub['C_mpmap'] += len(gr[g-1].strings)
print(sub, 'sum', sum(sub.values()))

C = []
def add(g, i, toks, note): C.append((g, i, toks, note))

add(58, 264, ['下','雷'], '无 已/设 字，以动宾 表已布设')
add(58, 663, ['上','!','上','!','上','!','上','!','上','!'], '冲/快 缺字，以 上 代 GO（口语可懂）')
add(58, 505, ['队'], 'TEAM 大写同条 409')
add(58, 409, ['队'], '')
add(58, 192, ['A','队'], '希腊字母代号转 A/B/C')
add(58, 193, ['B','队'], '')
add(58, 194, ['C','队'], '')
add(58, 266, ['A','队',':',' '], '')
add(58, 267, ['B','队',':',' '], '')
add(58, 268, ['C','队',':',' '], '')
add(58, 757, ['A','队'], '')
add(58, 758, ['B','队'], '')
add(58, 507, ['1','队',' '], '原文尾带空格，保持')
add(58, 508, ['2','队',' '], '')
add(58, 509, ['3','队',' '], '')
add(58, 510, ['4','队',' '], '')
add(58, 203, ['武','器'], '士兵属性页标签')
add(58, 531, ['雷'], '兵种 爆破手 无法表达，单字 雷 指代，损失大（备选 SKIP）')
add(58, 532, ['枪','手'], 'Rifleman→枪手，语义贴合')
add(58, 565, ['枪','手'], '')
add(58, 570, ['枪','手'], '大写变体')
add(58, 563, ['雷'], 'Demo 简称')
add(58, 568, ['雷'], 'DEMO 大写变体')
add(58, 126, ['信','息'], 'Information 三处同文')
add(58, 142, ['信','息'], '')
add(58, 230, ['信','息'], '')
add(58, 486, ['地','图'], 'WORLD MAP→地图，世界 省略')
add(58, 487, ['图'], '指挥 缺字，单字 图，损失大（备选保留英文）')
add(65, 112, ['图'], '同上')
add(58, 182, ['选','手',':'], '名 缺字')
add(58, 522, ['选','手'], '')
add(58, 659, ['队',' ','>'], '')
add(58, 456, ['行','前','带','雷','.'], '部分/若干 省略；任务前 以 行前 概括')
add(58, 458, ['行','前','带',' ','M136','.'], '火箭筒名保留 ASCII')
add(58, 732, ['击'], '开火/射击 缺字，单字 击')
add(61, 1, ['前','进'], '')
add(61, 3, ['左','移'], '')
add(61, 4, ['右','移'], '')
add(61, 9, ['左','视'], 'Peek→视')
add(61, 10, ['右','视'], '')
add(65, 125, ['左','视'], '')
add(65, 126, ['右','视'], '')
add(61, 11, ['选','枪'], '主武器→选枪')
add(61, 12, ['换','枪'], '副武器→换枪，主副之别由选/换区分')
add(61, 13, ['选','A'], '')
add(61, 14, ['选','B'], '')
add(61, 15, ['选','C'], '')
add(61, 16, ['选','D'], '')
add(61, 39, ['换','弹'], '')
add(65, 116, ['换','弹'], 'Reload Weapon→换弹')
add(61, 23, ['聊','天'], '')
add(65, 54, ['队','聊'], '')
add(65, 53, ['聊','天','信','息'], '')
add(61, 5, ['下'], '站姿系动词全缺，仅余上/下，损失大（备选 SKIP）')
add(61, 6, ['上'], '同上')
add(30, 9, ['1',' - ','下','雷',' ','51'], '地点 潜艇舱 省略，保留编号')
add(30, 10, ['2',' - ','下','雷',' ','52'], '')
add(30, 12, ['X',' - ','下','雷'], '油库 省略')
add(44, 1, ['下','雷',' ','1'], '极光残骸1→编号 1')
add(44, 2, ['下','雷',' ','2'], '')
add(44, 3, ['下','雷',' ','3'], '')
add(44, 11, ['1',' - ','下','雷'], '残骸处 省略')
add(50, 11, ['1',' - ','下','雷'], '仓库 省略')
add(50, 2, ['下','雷','.'], '此处 省略')
add(45, 9, ['1',' - ','雷','图'], '雷区图 缺 区，动词 取 省略')
add(0, 0, ['ITM_BOMB→雷'], 'STRINGS.TXT: Demo Charge→雷；与 Claymore 撞名，Claymore 建议 SKIP')

rows = []
for g,i,toks,note in C:
    if g == 0:
        rows.append(('STRINGS.TXT','ITM_BOMB / "Demo Charge"','ITM_BOMB→雷','—',note))
        continue
    b, hx = zh(*toks)
    orig = S(g,i)
    rows.append(('G%02d.I%03d' % (g,i), orig[:56] + ('…' if len(orig)>56 else ''),
                 ''.join(toks), hx, note or '—'))
print('候选条数:', len(rows))

lines = ['| 位置 | 英文原文 | 建议中文 | 槽位字节 (hex) | 语义损失备注 |',
         '|---|---|---|---|---|']
for a,b,c,d,e in rows:
    lines.append('| %s | %s | %s | %s | %s |' % (a,b,c,d,e))
table = '\n'.join(lines)
open(os.path.join(REPO_ROOT, 'work', 'tmp', 'gr_res', 'cand_table.md'),'w',encoding='utf-8',newline='\n').write(table+'\n')
print(table[:2200])
