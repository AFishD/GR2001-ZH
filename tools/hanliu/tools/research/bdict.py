# -*- coding: utf-8 -*-
"""b-pool EN->ZH dictionary.
Sources: official PC Chinese (Ghost Recon/Data/Shell/strings.txt + STRINGS.RES, GBK)
for vocabulary; semantic translation otherwise. Punctuation: ASCII (charset budget).
Keys are normalized: \\x92->', \\xa0->' ', whitespace collapsed, .strip(), then UPPER().
"""
import re

def norm(s: str) -> str:
    s = s.replace('\x92', "'").replace('\xa0', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def key(s: str) -> str:
    return norm(s).upper()

# ---------------- KEEP: no translation (0 hanzi demand) ----------------
KEEP = {
    # language names (shown in own language by convention)
    'ENGLISH', 'FRANÇAIS', 'DEUTSCH', 'ITALIANO', 'ESPAÑOL', 'RUSSIAN',
    # NPC proper names appearing in main pool
    'MOROSHKIN', 'PAPASHVILI',
    # format / debug / internal
    '%0X%1X%2', 'VAR TUNING', 'CARVE WORLD', 'I LINK',
    '<BR>', '<IMAGE,DMG_LOGO.RSB,256,179>', 'L2/R2 R1', 'CAO YAN', 'L2/R2           R1',
}

# ---------------- roles (credits <title>X) ----------------
ROLES = {
    'ANIMATOR': '动画师',
    'ARTISTIC DIRECTOR': '艺术总监',
    'BRAND MANAGER': '品牌经理',
    'CASTING DIRECTOR': '选角导演',
    'COMPOSER': '作曲',
    'CONTENT MANAGER': '内容经理',
    'DATA MANAGER': '数据经理',
    'DIALOGUE EDITOR': '对白剪辑',
    'DIRECTOR OF PUBLISHING': '发行总监',
    'EDITOR IN CHIEF': '主编',
    'GAME DESIGNER': '游戏设计师',
    'GRAPHIC DESIGNER': '平面设计师',
    'GRAPHIC STUDIO MANAGER': '美术工作室经理',
    'INFO DESIGNER': '信息设计师',
    'LEAD ANIMATOR': '动画主管',
    'LEAD GAME DESIGNER': '主游戏设计师',
    'LEAD GRAPHIST': '主美术师',
    'LEAD INFO DESIGNER': '主信息设计师',
    'LEAD PROGRAMMER': '主程序员',
    'LEAD TESTER': '测试主管',
    'MARKETING DIRECTOR': '市场总监',
    'MARKETING GROUP MANAGER': '市场集团经理',
    'PRODUCER': '制作人',
    'PRODUCT MANAGER': '产品经理',
    'PRODUCTION MANAGER': '制作经理',
    'PROGRAMMER': '程序员',
    'RSE DEVELOPMENT TEAM': 'RSE开发团队',
    'RSE TESTING TEAM': 'RSE测试团队',
    'SITE MANAGING DIRECTOR': '网站管理总监',
    'SOUND DESIGNER': '声音设计师',
    'SOUNDELUXE CREDITS': 'Soundeluxe制作组',
    'STORY EDITOR': '剧情编辑',
    'TESTER': '测试员',
    'TESTER STUDIO MANAGER': '测试工作室经理',
    'U.S. MARKETING': '美国市场',
    'UBISOFT ENTERTAINMENT': 'Ubisoft娱乐',
    'UBISOFT U.S.': 'Ubisoft美国',
    'VOICE TALENT': '配音演员',
    'WEAPONS PROVIDED BY': '武器提供',
}

# ---------------- main EN->ZH dict ----------------
D = {}
def _m(pairs):
    for en, zh in pairs:
        D[en.upper()] = zh

_m([
 # ---- votes / lobby fragments ----
 ('ABSTAIN:', '弃权:'), ('ELIGIBLE TO VOTE:', '可以投票:'), ('NAY:', '不同意:'), ('YAY:', '同意:'),
 ('ALL >', '全部>'), ('- INVALID GAME VERSION', '- 游戏版本不正确'),
 ('- SERVER FULL', '- 服务器已满'), ('- SERVER NOT RESPONDING', '- 服务器没有响应'),
 ('KIT:', '装备:'), ('PLATOON MUST REMAIN ACTIVE', '小队必须处于激活状态'),
 ('PLATOON MUST REMAIN INACTIVE', '小队必须处于非激活状态'), ('REMAINING', '剩余'),
 ('SERVER GAME MODE:', '服务器游戏模式:'), ('EXITED', '退出了'), ('HAS ELIMINATED', '消灭了'),
 ('JOINED', '加入了'),
 # ---- times / bitdepth ----
 ('1 MINUTE', '1分钟'), ('1 MINUTE 30 SECONDS', '1分30秒'), ('2 MINUTES', '2分钟'),
 ('3 MINUTES', '3分钟'), ('5 MINUTES', '5分钟'), ('30 SECONDS', '30秒'), ('45 SECONDS', '45秒'),
 ('5 MIN', '5分'), ('10 MIN', '10分'), ('20 MIN', '20分'),
 ('16 BIT', '16位'), ('24 BIT', '24位'), ('32 BIT', '32位'),
 # ---- empties / warnings ----
 ('-EMPTY-', '-空-'), ('-UNAVAILABLE-', '-不可用-'), ('-WARNING-', '-警告-'),
 ('(TIME REMAINING:', '(剩余时间:'),
 # ---- difficulty ----
 ('ELITE', '精英'), ('VETERAN', '老兵'), ('RECRUIT', '新兵'), ('LEGENDARY', '传奇'),
 ('DIFFICULTY', '难度'), ('DIFFICULTY:', '难度:'), ('DIFFICULTY: %0', '难度: %0'),
 ('DIFFICULTY LEVEL:', '难度等级:'), ('SELECT DIFFICULTY', '选择难度'), ('SELECT DIFFICULTY:', '选择难度:'),
 ("'ELITE' IS ONLY FOR THE BEST.", '精英只属于最强者。'),
 ("'RECRUIT' IS FOR NEW PLAYERS.", '新兵适合新玩家。'),
 ('FOR NEW RECRUITS.', '适合新手。'), ('FOR COMBAT VETERANS.', '难度中等。'),
 ('FOR ELITE SOLDIERS.', '适合高手。'),
 # ---- soldier types / kits ----
 ('RIFLEMAN', '突击队员'), ('SNIPER', '狙击手'), ('SUPPORT', '支援队员'),
 ('DEMOLITIONS', '爆破手'), ('DEMO', '爆破手'), ('SPECIALIST', '专家'), ('STANDARD', '标准'),
 ('RIFLEMAN KIT:', '突击队员装备:'), ('SNIPER KIT:', '狙击手装备:'),
 ('SUPPORT KIT:', '支援队员装备:'), ('DEMO KIT:', '爆破手装备:'),
 ('PICKS KIT', '选装备'), ('PICKS TEAM', '选小组'),
 # ---- companies / callsigns ----
 ('RED COMPANY', '红队'), ('BLUE COMPANY', '蓝队'), ('GREEN COMPANY', '绿队'), ('GOLD COMPANY', '黄队'),
 ('ALPHA', 'A组'), ('BRAVO', 'B组'), ('CHARLIE', 'C组'),
 ('ALPHA:', 'A组:'), ('BRAVO:', 'B组:'), ('CHARLIE:', 'C组:'),
 ('ALPHA TEAM', 'A小队'), ('BRAVO TEAM', 'B小队'),
 # ---- weather ----
 ('SUNNY', '晴天'), ('PARTLY CLOUDY', '多云'), ('CLOUDY', '阴天'), ('RAIN', '有雨'),
 ('SNOW', '有雪'), ('FOG', '有雾'), ('CLEAR (NIGHT)', '晴天(夜晚)'),
 ('PARTLY CLOUDY (NIGHT)', '多云(夜晚)'), ('WEATHER = PARTLY CLOUDY', '天气 = 多云'),
 # ---- ROE ----
 ('ADVANCE', '前进'), ('ADVANCE AT ALL COSTS', '不惜一切代价前进'), ('AT ALL COSTS', '不惜一切代价前进'),
 ('ASSAULT', '突击'), ('RECON', '侦察'), ('SUPPRESS', '压制'), ('HOLD', '待命'),
 # ---- statuses ----
 ('HEALTHY', '健康'), ('WOUNDED', '受伤'), ('DEAD', '死亡'), ('POW', '战俘'),
 ('PINNED DOWN', '被压制'), ('TAKING FIRE', '受到攻击'), ('TAKING FRIENDLY FIRE', '受到友方攻击'),
 ('ENEMIES NEARBY', '附近出现敌人'), ('ENEMIES SPOTTED', '发现敌人'),
 ('ENEMY ARMOR SPOTTED', '发现敌人的装甲车辆'), ('ENEMY ARMOR ELIMINATED', '敌人的装甲车辆被消灭'),
 ('NON-COMBATANTS SPOTTED', '发现敌人非战斗人员'), ('FRIENDLIES IN SIGHT', '发现友方人员'),
 ('ENEMY SOLDIER DOWN', '敌士兵阵亡'), ('TEAM MEMBER WOUNDED', '队员受伤'),
 ('TEAM MEMBER OUT OF ACTION', '队员失去战斗能力'), ('PRISONER SECURED', '犯人已获救'),
 ('HOSTAGE SECURED', '人质已获救'), ('DEMO CHARGE SET', '已安装炸弹'),
 ('AT DESTINATION', '已到达目的地'), ('EXTRACTION ZONE', '撤离区'), ('INSERTION ZONE', '突入区'),
 # ---- NPC labels ----
 ('A GEORGIAN REBEL', '格鲁吉亚叛军'), ('A PEACEKEEPER', '维和士兵'),
 ('AN ERITREAN WORKER', '厄立特里亚工人'), ('REFUGEE', '难民'), ('PILOT', '飞行员'),
 # ---- save / campaign labels ----
 ('GR MISSION', 'GR任务'), ('DS MISSION', 'DS任务'), ('GR MP', 'GR联机'), ('DS MP', 'DS联机'),
 ('CAMPAIGN-ELITE', '战役-精英'), ('CAMPAIGN-VETERAN', '战役-老兵'),
 ('CAMPAIGN-RECRUIT', '战役-新兵'), ('CAMPAIGN-LEGENDARY', '战役-传奇'),
 ('CAMPAIGN MISSION', '战役任务'), ('CAMPAIGN NAME:', '战役名称:'), ('CAMPAIGN SET:', '战役设置:'),
 ('CAMPAIGN WON', '战役胜利'), ('CAMPAIGN', '战役'), ('CAMPAIGNS', '战役'),
 ('NEW CAMPAIGN', '新战役'), ('DELETE CAMPAIGN', '删除战役'), ('RESUME CAMPAIGN', '继续战役'),
 ('SAVED CAMPAIGNS', '已保存的战役'), ('LOAD SAVED CAMPAIGN', '载入已保存的战役'),
 ('LOAD SAVED CAMPAIGN.', '载入已保存的战役。'), ('SELECT A CAMPAIGN.', '选择一个战役。'),
 ('SELECT DESERT SIEGE CAMPAIGN.', '选择沙漠围剿战役。'),
 ('SELECT GHOST RECON CAMPAIGN.', '选择幽灵行动战役。'),
 ('START NEW CAMPAIGN.', '开始新战役。'), ('COMPLETE PERCENT', '完成百分比'),
 ('QM - ELITE - F', '快速任务-精英-F'), ('QM - ELITE - M', '快速任务-精英-M'),
 ('QM - ELITE - R', '快速任务-精英-R'), ('QM - LEGENDARY - F', '快速任务-传奇-F'),
 ('QM - LEGENDARY - M', '快速任务-传奇-M'), ('QM - LEGENDARY - R', '快速任务-传奇-R'),
 ('QM - RECRUIT - F', '快速任务-新兵-F'), ('QM - RECRUIT - M', '快速任务-新兵-M'),
 ('QM - RECRUIT - R', '快速任务-新兵-R'), ('QM - TIME - F', '快速任务-计时-F'),
 ('QM - TIME - M', '快速任务-计时-M'), ('QM - TIME - R', '快速任务-计时-R'),
 ('1-1 RANDOM', '随机1对1'), ('CO-OP RANDOM', '随机合作'), ('SOLO RANDOM', '随机单人'),
 ('TEAM RANDOM', '小组随机'),
 # ---- files ----
 ('FILE #1', '文件#1'), ('FILE #2', '文件#2'), ('FILE #3', '文件#3'),
 ('FILE SELECT', '选择文件'), ('DELETE FILE', '删除文件'), ('RESUME FILE', '恢复文件'),
 ('FILE NAME:', '文件名:'), ('SAVED DATE', '保存日期'),
 ('YOU ARE ABOUT TO DELETE "%0"!', '你将删除"%0"!'),
 ('YOU ARE ABOUT TO DELETE %0.', '你将删除%0。'),
 ('YOU ARE ABOUT TO OVERWRITE %0.', '你将覆盖%0。'),
 ('FORMAT SUCCESSFUL.', '格式化成功。'), ('SAVE SUCCESSFUL.', '保存成功。'),
 ('LOAD SUCCESSFUL.', '载入成功。'), ('OVERWRITE SUCCESSFUL.', '覆盖成功。'),
 ('FILE FAILED TO SAVE.', '文件无法保存。'),
 ('ERROR: CANNOT SAVE REPLAY.', '出错: 无法保存重放文件。'),
 ('SELECT SLOT A', '选择A槽'), ('SELECT SLOT B', '选择B槽'),
 ('SELECT SLOT C', '选择C槽'), ('SELECT SLOT D', '选择D槽'),
 ('SLOT IS TAKEN', '位置被占'),
 # ---- load/save ----
 ('LOAD', '载入'), ('LOAD GAME', '载入游戏'), ('LOAD KEYS', '载入设置'),
 ('LOAD LAST SAVE', '载入最近一次的存档'), ('LOAD SAVED GAME', '载入已保存的游戏'),
 ('LOADING...', '载入中...'), ('SAVE', '保存'), ('SAVE GAME', '保存游戏'),
 ('SAVE KEYS', '保存设置'), ('SAVE KEY CONFIG', '保存设置'), ('SAVE REPLAY', '保存重放'),
 ('SAVE/LOAD', '保存/载入'), ('QUICK SAVE', '快速保存'), ('QUICK LOAD', '快速载入'),
 ('QUICKSAVE', '快速保存'), ('QUICK SAVE FAILED!', '快速保存失败!'),
 ('QUICK SAVE WAS SUCCESSFUL', '快速保存成功'), ('QUICK LOAD FAILED!', '快速载入失败!'),
 ('QUICK LOAD WAS SUCCESSFUL', '快速载入成功'), ('QUICK LOADING...', '快速载入中...'),
 ('QUICK SAVE/LOAD', '快速保存/载入'), ('NEW', '新建'), ('NEW GAME', '新游戏'),
 ('NEW SAVE GAME', '新的游戏存档'), ('NEW KEY CONFIG', '新的设置'),
 ('NEXT MAP', '下一个地图'), ('NEXT MAP:', '下一张地图:'),
 ('DELETE', '删除'), ('DELETE SAVE', '删除游戏存档'), ('DELETE REPLAY', '删除重放文件'),
 ('DELETE KEY CONFIG', '删除设置'), ('RESTART', '重新开始'), ('RESUME', '继续'),
 ('CONTINUE', '继续'), ('CONTINUE?', '继续？'), ('PAUSE', '暂停'), ('QUIT', '退出'),
 ('EXIT', '退出'), ('BACK', '返回'), ('PAUSE MENU', '暂停菜单'),
 # ---- maps ----
 ('MAP', '地图'), ('MAP:', '地图:'), ('MAP INFO', '地图信息'), ('MAP NAME:', '地图名称:'),
 ('MAP REPS', '地图重放'), ('MAP REPS:', '地图重放:'), ('WORLD MAP', '世界地图'),
 ('COMMAND MAP', '指挥地图'), ('OBSTACLE MAP', '障碍地图'),
 # ---- confirm ----
 ('OK', '确认'), ('YES', '是'), ('NO', '否'), ('ON', '开'), ('OFF', '关'),
 ('SAME', '同样'), ('SET', '设定'), ('CHANGED', '已更改'), ('ENABLED', '启用'),
 ('DISABLED', '被禁用'), ('ACTIVATE', '启用'), ('DEACTIVATE', '停用'),
 ('INVALID', '无效'), ('NONE', '无'), ('UNKNOWN', '未知'), ('UNKNOWN REASON', '原因未知'),
 ('REQUIRED', '需要'), ('NOT REQUIRED', '不需要'), ('READY', '准备好'), ('NOT READY', '未准备好'),
 ('WAITING', '等待中'), ('PLAYING', '游戏中'), ('LOCKED', '已锁定'),
 ('DEFAULT', '缺省'), ('MAKE DEFAULT', '成为缺省'), ('RESET TO DEFAULTS', '恢复缺省设置'),
 ('REVERT', '还原'), ('LOW', '低'), ('MEDIUM', '中'), ('HIGH', '高'),
 ('MAIN', '主要'), ('SCREEN', '屏幕'), ('CONFIG', '设置'), ('ADVANCED', '高级'),
 ('GAMEPLAY', '游戏玩法'), ('CONTROLLER', '控制器'),
 # ---- split screen ----
 ('SPLIT SCREEN', '分屏'), ('SPLIT-SCREEN PLAY', '分屏游戏'),
 ('WAITING FOR PLAYER 1', '等待玩家1'), ('WAITING FOR PLAYER 2', '等待玩家2'),
 ('PLAYER 1', '玩家1'), ('PLAYER 2', '玩家2'),
 # ---- movement / controls ----
 ('SHUFFLE', '碎步'), ('SHUFFLE/WALK/RUN', '碎步/行走/奔跑'),
 ('STANCE UP', '站起'), ('STANCE DOWN', '蹲下'), ('STANCE UP/DOWN', '站起/蹲下'),
 ('DROP STANCE', '蹲下'), ('RAISE STANCE', '站起'), ('CYCLE STANCE', '切换姿势'),
 ('PEEK LEFT', '向左窥视'), ('PEEK RIGHT', '向右窥视'), ('PEEK LEFT/RIGHT', '左右窥视'),
 ('NIGHT VISION', '夜视镜'), ('NIGHT VISION/CHANGE WEAPON', '夜视镜/换武器'),
 ('MOVE', '移动'), ('MOVE FORWARD', '向前移动'), ('MOVE BACKWARD', '向后移动'),
 ('MOVE LEFT', '向左移动'), ('MOVE RIGHT', '向右移动'), ('RUN', '奔跑'),
 ('ALWAYS RUN', '总是奔跑'), ('STRAFE', '平移'), ('SIDESTEP', '平移'),
 ('TURN', '转身'), ('TURN LEFT/RIGHT', '左右转身'), ('LOOK', '视角'),
 ('LOOK UP/DOWN', '视角上下'), ('SHIFT', '切换'),
 ('REVERSE', '反转'), ('REVERSE ON', '开启反转'), ('REVERSE OFF', '关闭反转'),
 ('REVERSE LOOK UP AND DOWN.', '视角上下反转。'),
 ('FIRE', '开火'), ('FIRE WEAPON', '开火'), ('ZOOM', '缩放'),
 ('ZOOM IN', '放大'), ('ZOOM OUT', '缩小'), ('ZOOM WEAPON', '缩放武器'),
 ('ZOOM WEAPON IN', '放大武器'), ('ZOOM WEAPON OUT', '缩小武器'),
 ('RESET WEAPON ZOOM', '重设武器缩放'), ('CHANGE MAGAZINE', '更换弹夹'),
 ('RELOAD WEAPON', '换子弹'), ('CYCLE WEAPON', '切换武器'), ('CYCLE SOLDIER', '切换队员'),
 ('CYCLE SOLDIER ', '切换队员'), ('USE ITEM', '使用物品'),
 ('PERFORM ACTION', '执行动作'), ('PERFORM ACTION ', '执行动作'),
 ('SELECT PRIMARY', '选择主要武器'), ('SELECT SECONDARY', '选择备用武器'),
 ('SELECT SOLDIER', '选择队员'), ("SELECT THE SOLDIER'S KIT.", '选择队员装备。'),
 ("SELECT THE SOLDIER'S TYPE.", '选择队员兵种。'),
 ('AUTO AIM', '自动瞄准'), ('AUTO TARGETING', '自动瞄准'),
 ('COMMAND INTERFACE', '控制界面'), ('COMMAND INTERFACE LOCK', '控制界面锁定'),
 ('CHAT', '聊天'), ('TOGGLE CAMERA', '切换视角'), ('TOGGLE OBSERVER', '切换观看模式'),
 ('TOGGLE FILL MODE', '切换填充镜头'), ('TOGGLE COMMAND DISPLAY', '切换指挥显示'),
 ('TOGGLE COMPASS DISPLAY', '切换指南针显示'), ('TOGGLE SOLDIER DISPLAY', '切换战士显示'),
 ('TOGGLE WEAPONS DISPLAY', '切换武器显示'), ('TOGGLE CONSOLE DISPLAY', '切换控制台显示'),
 ('TOGGLE DEBUG DISPLAYS', '切换除错显示'), ('TOGGLE AMBIENT', '切换环境音效'),
 ('TOGGLE JOURNAL PLAY', '切换日游戏'), ('TOGGLE JOURNAL RECORD', '切换日记录'),
 ('TOGGLE VIBRATION ON OR OFF.', '开启或关闭振动。'),
 ('SWAP LOOK AND TURN', '视角/转身互换'),
 ('PAD LOOK REVERSE Z', '手柄视角Z轴反转'), ('PAD TURN REVERSE ZR', '手柄转向ZR反转'),
 ('L1: 2D INTERFACE', 'L1: 2D界面'), ('L3 BUTTON +', 'L3键+'), ('R3 BUTTON', 'R3键'),
 ('R2: ZOOM IN/OUT', 'R2: 缩放'),
 ('FOLLOW NEXT', '跟随下一个'), ('FOLLOW LAST', '跟随上一个'),
 ('QUICK ORDER', '快速命令'), ('RADAR SYSTEM', '雷达系统'), ('ENEMY INDICATOR', '敌人指示器'),
 ('SINGLE SHOT', '单发'), ('BURST', '三弹连发'), ('FULL AUTO', '全自动'),
 ('INITIAL RATE OF FIRE', '初始射击频率'), ('CHANGE FIRE RATE', '更改射击频率'),
 ('CHANGE RATE OF FIRE', '更改射击频率'),
 # ---- options: audio ----
 ('SOUND', '声音'), ('MUSIC', '音乐'), ('VOICE', '语音'),
 ('MASTER VOLUME', '主音量'), ('MASTER SWITCH', '主开关'),
 ('EFFECTS VOLUME', '效果音量'), ('EFFECTS SWITCH', '效果开关'),
 ('MUSIC VOLUME', '音乐音量'), ('MUSIC SWITCH', '音乐开关'),
 ('VOICE VOLUME', '语音音量'), ('VOICE SWITCH', '语音开关'),
 ('SURROUND SOUND', '环绕声'), ('USE EAX', '使用EAX音效'),
 ('ALTERNATE SOUND CACHE', '备用声音缓存'),
 ('ADJUST MAIN VOLUME.', '调整主音量。'), ('ADJUST SPECIAL EFFECTS VOLUME.', '调整效果音量。'),
 ('ADJUST THE VOICE VOLUME.', '调整语音音量。'),
 # ---- options: video ----
 ('GRAPHICS', '图像'), ('RESOLUTIONS', '分辨率'), ('SHADOWS', '阴影'), ('TEXTURES', '材质'),
 ('MODELS', '模型'), ('Z-BUFFER DEPTH', 'Z缓冲深度'), ('EDGE ANTI-ALIASING', '边缘反锯齿'),
 ('VSYNC', '视频同步'), ('HUMAN SHADOWS', '人物阴影'), ('VEHICLE SHADOWS', '车辆阴影'),
 ('DEAD BODIES', '显示尸体'), ('COMPRESS TEXTURES', '压缩材质'),
 ('MAXIMUM BULLET HOLES', '最大弹孔数'), ('MAXIMUM CHARACTER WOUNDS', '最大伤口显示'),
 ('CHARACTER SMOOTHING', '人物平滑'), ('MAP TEXTURE DETAIL', '地图材质'),
 ('CHARACTER TEXTURE DETAIL', '人物材质'), ('EFFECTS TEXTURE DETAIL', '效果材质'),
 ('CHARACTER MODEL DETAIL', '人物模型细致度'), ('TREE MODEL DETAIL', '树木模型细致度'),
 ('EFFECTS DETAIL', '效果细致度'), ('DETAIL', '细致度'), ('LOW LOD', '低细节'),
 ('ALL LOW LOD', '全部低细节'), ('ALL DETAIL', '全部高细节'),
 ('ENVIRONMENT MAPPING ON', '打开环境效果'), ('BLOOD', '血腥效果'),
 ('BRIGHTNESS', '亮度'), ('GAMMA SETTING', '亮度设置'), ('SCREEN POSITION', '屏幕位置'),
 ('SENSITIVITY', '灵敏度'), ('VIBRATION', '振动'),
 ('CHANGE CONTROLLER SETTINGS.', '更改控制器设置。'),
 ('CHANGE GAMEPLAY OPTIONS.', '更改游戏玩法选项。'),
 ('CHANGE SCREEN POSITION.', '更改屏幕位置。'), ('CHANGE SOUND SETTINGS.', '更改声音设置。'),
 ('SHOW BLOOD IN THE GAME.', '显示血腥效果。'), ('SHOW DEAD BODIES IN THE GAME.', '显示尸体。'),
 ('SHOW INTRO MOVIE', '播放开场动画'),
 # ---- names / profiles ----
 ('NAME', '名字'), ('NAMES', '名单'), ('NAME ENTRY', '输入名字'), ('SOLDIER NAME', '队员姓名'),
 ('PLAYER NAME', '玩家姓名'), ('PLAYER NAME:', '玩家名字:'), ('NAME:', '名字:'),
 ('NAME YOUR PLAYER', '输入你的名字'), ('NAME YOUR PLAYER:', '输入你的名字:'),
 ('ENTER YOUR NAME.', '输入你的名字。'), ('ENTER YOUR NAME', '输入你的名字'),
 ('NEW NAME', '新名字'), ('DELETE NAME', '删除名字'),
 ('CHOOSE A PROFILE', '选择一个档案'), ('CHOOSE YOUR PROFILE.', '选择你的档案。'),
 ('CREATE NEW PROFILE.', '创建新档案。'), ('PERMANENTLY DELETES PLAYER.', '永久删除玩家。'),
 ('SOLDIER PROFILE', '队员档案'),
 # ---- mission / objectives ----
 ('MISSION', '任务'), ('MISSION %0:', '任务%0:'), ('MISSION:', '任务:'),
 ('MISSION NAME:', '任务名称:'), ('MISSION TYPE', '任务类型'), ('MISSION TYPE:', '任务类型:'),
 ('MISSION WON', '任务完成'), ('MISSION LOST', '任务失败'),
 ('NEW QUICK MISSION', '新任务'), ('QUICK MISSION', '快速任务'),
 ('SAVED QUICK MISSIONS', '已保存的快速任务'), ('LOAD QUICK MISSION', '载入任务'),
 ('OBJECTIVE COMPLETE', '目标完成'), ('OBJECTIVE FAILED', '目标失败'), ('OBJECTIVES', '任务目标'),
 ('CAMPAIGN MISSION', '战役任务'), ('CUSTOMIZE YOUR MISSION', '自定义你的任务'),
 ('PICK A NEW MISSION TO PLAY?', '选择一个新的任务？'), ('SELECT A MISSION.', '选择一个任务。'),
 ('END MISSION', '结束任务'), ('PLAY BRIEFING', '播放简介'), ('STOP BRIEFING', '停止播放'),
 ('BRIEFING', '简介'), ('ENTER THE BATTLEFIELD.', '进入战场。'),
 ('ELIMINATE ALL ENEMIES.', '消灭所有敌人。'),
 # ---- results / outcomes ----
 ('COMPLETED', '已完成'), ('FAILED', '已失败'), ('INCOMPLETE', '未完成'),
 ('SUCCESS', '成功'), ('FAILURE', '失败'), ('WON', '胜利'), ('DRAW', '平局'),
 ('YOU WON', '你胜利了'), ('YOU LOST', '你失败了'), ('NO TEAM WON', '没有胜利方'),
 ('YOUR TEAM WON', '你的小组胜利了'), ('RED TEAM WON', '红队胜利了'),
 ('BLUE TEAM WON', '蓝队胜利了'), ('GREEN TEAM WON', '绿队胜利了'),
 ('GOLD TEAM WON', '黄队胜利了'),
 ('TIME HAS EXPIRED...', '时间已过...'),
 ('ALL SOLDIERS HAVE BEEN LOST...', '所有的小组成员都阵亡了...'),
 ('A NEW SPECIALIST IS AVAILABLE.', '一个新专家前来报到。'),
 ('ARE YOU SURE?', '你确定吗？'), ('ACCESS REWARDS.', '查看奖章。'),
 ('CHECK THE CREDITS.', '查看制作组。'), ('CHECK THE RESULTS.', '查看结果。'),
 ('CHECK YOUR GAME PROGRESS.', '查看你的游戏进度。'),
 ('LOAD A SAVED GAME.', '载入已保存的游戏。'),
 ('LOAD SCREEN SETTINGS SCRIPT.', '载入窗口设置文件。'),
 ('SAVE SCREEN SETTINGS.', '保存窗口设置。'),
 # ---- menus ----
 ('GAME SELECTION', '游戏选择'), ('GAME OPTIONS', '游戏选项'), ('GAME SETTINGS', '游戏设置'),
 ('GAME MODE', '游戏模式'), ('GAME TYPE', '游戏类型'), ('GAME TYPE:', '游戏类型:'),
 ('GAME STATE:', '游戏状态:'), ('GAME OVER:', '游戏结束:'), ('OPTIONS', '选项'),
 ('SETTINGS', '设置'), ('SET UP', '设定'), ('CHOOSE AN OPTION', '选择一个选项'),
 ('M.O.T.D.', '每日信息'), ('MESSAGE OF THE DAY', '每日信息'), ('MESSAGE OF THE DAY:', '每日信息:'),
 ('CURRENT GAME STATS', '当前游戏统计'), ('INFORMATION', '信息'), ('INFO', '信息'),
 ('GAME INFORMATION', '任务信息'), ('INSTRUCTIONS', '指导'), ('HELP MENU', '帮助菜单'),
 ('TRAINING SPACE:', '训练地点:'), ('ACCESS CODE', '代码'), ('INPUT', '输入'),
 ('TYPE', '类型'), ('TYPE:', '类型:'), ('MODE', '模式'), ('MODE:', '模式:'),
 ('TRAINING', '训练'), ('EXERCISE', '练习'), ('TACTICAL EXERCISES', '战术演习'),
 ('TESTING', '测试'), ('SELECT TRAINING TYPE', '选择训练类型'),
 ('SELECT TRAINING PROCEDURE', '选择训练顺序'), ('SELECT A LEVEL', '选择关卡'),
 ('CHECKPOINT', '记录点'), ('LEVEL', '等级'), ('RANK', '军衔'), ('SPECIALTY', '专长'),
 ('ENDURANCE', '耐力'), ('STEALTH', '隐藏能力'), ('LEADERSHIP', '领导能力'),
 ('WEAPONS OFFICER', '武器军官'),
 # ---- platoon / team ----
 ('PLATOON ASSIGNMENT', '队员分配'), ('PLATOON SELECTOR', '小队选择'),
 ('PLATOON STATS', '小队统计'), ('PLATOON SETUP', '小队设置'), ('PLATOON LEADER:', '小队领队:'),
 ('PLATOON 1', '小队 1'), ('PLATOON 2', '小队 2'), ('PLATOON 3', '小队 3'), ('PLATOON 4', '小队 4'),
 ('PLATOON NOT AVAILABLE', '小队不可用'),
 ('SQUAD SELECTOR', '小组选择'), ('TEAM SELECTOR', '小组选择'),
 ('TEAM', '小组'), ('TEAM >', '小组>'), ('IN ORDER', '按顺序'), ('ORDER', '命令'),
 ('COMMAND', '命令'), ('ROE', '命令'),
 ('SOLDIER', '队员'), ('SOLDIER SELECTION', '队员选择'),
 ('SOLDIER STATS', '队员统计'), ('SOLDIERS RESULTS', '队员成绩'),
 ('KIT/ROSTER SELECTION', '装备/名册选择'), ('ROSTER', '名册'), ('STATS/KIT', '状态/装备'),
 ('PROCEED TO PLATOON SELECTION.', '前往小队选择。'), ('PROCEED TO PLAYER SETUP.', '前往玩家设置。'),
 ('UNASSIGN ALL', '全部重新分配'), ('UNASSIGN THE PLATOON.', '取消小队分配。'),
 ('UNASSIGNING PLAYERS', '正在取消玩家分配'),
 ('REMOVING PLAYER FROM PLATOON', '让玩家离开团队'),
 ('AUTO ASSIGN', '自动分配'), ('AUTO ASSIGN STAT POINTS', '自动分配属性点数'),
 ('ASSIGNED PLAYERS', '已经分配玩家'), ('UNASSIGNED PLAYERS', '未分配玩家'),
 ('VOTE FOR TEAM LEADER', '选举小组领队'),
 # ---- multiplayer / network ----
 ('MULTIPLAYER', '多人游戏'), ('MULTIPLAYER SETUP', '多人游戏设置'),
 ('MULTIPLAYER SETUP.', '多人游戏设置。'), ('SINGLE PLAYER', '单人游戏'),
 ('SINGLEPLAYER SETUP', '单人游戏设置'), ('JOIN GAME', '加入游戏'), ('JOIN PORT', '加入端口'),
 ('CREATE GAME', '创建游戏'), ('CLIENT JOIN', '客户机加入'), ('DEDICATED SERVER', '专用服务器'),
 ('NAMED GAME', '已命名的游戏'), ('BEHIND FIREWALL', '在防火墙后'),
 ('CHOOSE NETWORK INTERFACE CARD', '选择网络接口'), ('INTERNET', '因特网'), ('LAN', '局域网'),
 ('ONLINE', '在线'), ('ON-LINE PLAY', '在线游戏'), ('LINK PLAY', '连线游戏'),
 ('LINK CABLE', '连接电缆'), ('CONNECTION TYPE', '联网类型'), ('CONNECTION INFO:', '联网信息:'),
 ('CONNECTING...', '连接中...'), ('CONNECTION FAILURE', '连接失败'),
 ('CANNOT ESTABLISH CONNECTION.', '无法建立连接。'), ('CANNOT CONNECT TO SERVER', '无法连接服务器'),
 ('JOINING', '加入中'), ('SEARCHING...', '搜寻中...'), ('REFRESH LIST', '刷新列表'),
 ('EDIT SERVER', '编辑服务器'), ('EDIT SERVER LIST', '编辑服务器列表'),
 ('SERVER INFO', '服务器信息'), ('SERVER INFO DIALOG', '服务器信息'),
 ('SERVER NAME', '服务器名称'), ('SERVER NAME:', '服务器名称:'), ('SERVER SETUP', '服务器设置'),
 ('SERVER IS FULL', '服务器已满'), ('SERVER IS IN USE', '服务器正被使用'),
 ('SERVER SETUP SCREEN IN USE BY', '服务器设置窗口正在被使用, 对方是'),
 ('PASSWORD', '密码'), ('PASSWORD:', '密码:'), ('INVALID PASSWORD', '密码错误'),
 ('INCORRECT PASSWORD', '密码不正确'), ('ENTER PASSWORD FOR SERVER', '输入服务器密码'),
 ('DEFAULT JOIN PASSWORD', '缺省加入密码'), ('REMOTE ACCESS PASSWORD', '远程登录密码'),
 ('ALLOW REMOTE ACCESS', '允许远程登录'), ('REMOTE SERVER', '远程服务器'),
 ('REMOTE SERVER ACCESS DENIED:', '远程服务器拒绝你登录:'),
 ('REMOTE ACCESS IS DISABLED', '无法远程登录'),
 ('ALLOW OBSERVERS', '允许观看'), ('ALLOW OBSERVERS:', '允许观看:'),
 ('OBSERVER MODE', '观看模式'), ('OBSERVER MODE SELECTED', '已选择观看模式'),
 ('USE THREAT INDICATOR', '使用威胁指示器'), ('USE THREAT INDICATOR:', '使用威胁指示器:'),
 ('ENABLE VOTING', '允许投票'), ('CAST VOTE', '投票'),
 ('VOTE IN PROGRESS', '正在投票'), ('VOTE TO EJECT ENDING --->', '投票结束--->'),
 ('VOTE TO EJECT IN PROGRESS --->', '投票正在进行--->'),
 ("VOTES TO KICK PLAYER '", "投票踢掉玩家'"),
 ('REQUEST EJECT', '要求踢掉玩家'), ('EJECT', '踢掉'), ('EJECT PLAYER', '踢掉玩家'),
 ("DON'T EJECT PLAYER", '不踢掉玩家'), ('DO YOU WISH TO EJECT', '你想踢掉'),
 ('AUTO MATCH', '自动对应'), ('AUTO START', '自动开始'),
 ('AUTO-START TIMER', '自动开始计时器'), ('AUTO-START TIMER:', '自动开始计时器:'),
 ('RANDOM TEAMS', '随机小组'), ('RANDOM TEAMS:', '随机小组:'),
 ('RANDOM TEAMS OPTION ENABLED', '使用随机小组选项'),
 ('CANNOT ENABLE RANDOM TEAMS:', '无法使用随机小组:'),
 ('RANDOM INSERTION ZONES', '随机突入区'), ('RANDOM INSERTION ZONES:', '随机突入区:'),
 ('RANDOM', '随机'), ('INDIVIDUAL', '个人'), ('INDIVIDUAL LIMIT', '个人限制'),
 ('NO LIMIT', '无限制'), ('INFINITE', '无限'), ('NO TIMEOUT', '无时间限制'),
 ('TIME LIMIT', '时间限制'), ('TIME LIMIT:', '时间限制:'),
 ('RESPAWN', '重生'), ('RESPAWN:', '重生:'), ('RESPAWN COUNT:', '重生计数:'),
 ('RESPAWN TYPE:', '重生类型:'), ('CANNOT CHANGE RESPAWN COUNT:', '无法更改重生记数:'),
 ('MAX IFF', '敌我识别'), ('MAX IFF:', '敌我识别:'), ('IDENTIFY FRIEND OR FOE', '敌我识别'),
 ('AI BACKUP', '电脑支援'), ('AI BACKUP:', '电脑支援:'),
 ('AI BACKUP REQUEST DENIED:', '电脑支援请求被拒绝:'),
 ('MAX PLAYERS', '玩家上限'), ('MAX PLAYERS:', '玩家上限:'), ('MAX PLAYER COUNT:', '玩家上限:'),
 ('PLAYER COUNT:', '玩家记数:'), ('TOTAL PLAYER COUNT:', '全部玩家记数:'),
 ('HOST:', '主机:'), ('PING', 'PING'), ('PING =', 'PING ='),
 ('POINTS =', '得分 ='), ('HITS', '命中'), ('SHOTS', '射击数'), ('KILLS', '杀敌数'),
 ('HIT %', '命中率'), ('BEST TIME', '最佳时间'),
 ('TOTAL HIT % =', '总命中率 ='), ('TOTAL HITS =', '总命中 ='),
 ('TOTAL KILLS =', '总杀敌 ='), ('TOTAL SHOTS FIRED =', '总射击数 ='),
 ('FASTEST PLAYER:', '最快玩家:'), ('LAST HIT BY', '上次被击中时对方为'),
 ('SHOW HIT BY', '显示击中来源'), ('SHOW STATUS', '显示状态'),
 ('TIME ELAPSED:', '已过时间:'), ('ELAPSED TIME', '已过时间'),
 ('ELASPED MISSION TIME:', '已过任务时间:'), ('GAME TIME', '游戏时间'),
 ('TIME REMAINING:', '剩余时间:'), ('REMAINING', '剩余'),
 ('ENTERED SERVER SETUP SCREEN:', '已经进入服务器设置窗口:'),
 ('EXITED SERVER SETUP SCREEN:', '已经退出服务器设置窗口:'),
 ('EJECTED FROM SERVER', '已被踢出服务器'), (': YOU HAVE BEEN EJECTED', ': 你被踢掉了'),
 ('ENTERING', '正在进入'), ('SERVER GAME MODE: ', '服务器游戏模式:'),
 ('ENTER TEXT', '输入文字'), ('ENTERS/DELETES LETTERS.', '输入/删除字母。'),
 ('CYCLES THROUGH LETTERS.', '选择各种字母。'), ('EXISTS OUT OF DELETE MODE.', '存在于删除模式之外。'),
 ('HIT A KEY TO MAP', '点击一个按键进行设置'), ('PRESS START BUTTON', '按 START 键'),
 ('SCROLL TEXT UP.', '向上滚动文字。'), ('SCROLL TEXT DOWN.', '向下滚动文字。'),
 ('ITEM MISSING:', '物品失踪:'), ('SCRIPT', '脚本'), ('SCRIPT RUNNING:', '文件运行中:'),
 ('SECURITY DIALOG', '安全对话'), ('DISABLING', '停用'),
 ('INSTALL UBI.COM', '安装ubi.com'), ('PLAY IT ON UBI.COM', '在ubi.com上进行游戏'),
 ('MOVIES', '影片'), ('GAME TRAILERS', '预告片'), ('INTERVIEW', '访谈'),
 ('SKETCHES', '设定图'), ('SPECIAL FEATURES', '特别收录'), ('SCREENSHOTS', '屏幕截图'),
 ('AWARDS', '奖章'), ('DECORATIONS', '勋章'), ('CREDITS', '制作组'), ('BACKGROUND', '背景'),
 ('FIGHT THE MACHINE.', '与电脑对战。'), ('TWO PLAYERS HEAD TO HEAD.', '两个玩家对战。'),
 ('TEAM VS. TEAM.', '小组对战。'), ('ARCADE MODE', '街机模式'), ('ARCADE MODE:', '街机模式:'),
 ('ACCEPT', '接受'), ('ADD', '添加'), ('STOP', '停止'), ('PLAY', '播放'), ('VIEW', '查看'),
 ('MODS', 'MOD'), ('ACTIVE MODS', '使用的MOD'), ('AVAILABLE MODS', '可选的MOD'),
 ('AVAILABLE KITS', '可选的装备'), ('AVAILABLE KITS:', '可选的装备:'),
 ('INCREASE PRIORITY', '增加优先级'), ('RECORD GAME', '记录游戏'),
 ('REPLAYS', '重放'), ('REPLAY:', '重放:'), ('VIEW REPLAY', '观看重放'),
 ('SELECT REPLAY', '选择重放文件'), ('LOADING REPLAY... PLEASE WAIT.', '载入重放中... 请稍候。'),
 ('CHAT MESSAGES', '聊天信息'), ('TEAM CHAT', '小组聊天'), ('EDIT CHAT MESSAGE', '编辑聊天信息'),
 ('EDIT DIALOG', '编辑信息'), ('CHAT MSG', '聊天信息'),
 ('CO-OP', '合作'), ('SOLO', '单人'), ('GAME MODE', '游戏模式'),
 ('FIRE FIGHT', '歼灭战'),
 # ---- gametypes ----
 ('FIREFIGHT', '歼灭战'), ('FIREFIGHT COOPERATION', '合作歼灭战'),
 ('MISSION COOPERATION', '合作任务'), ('SURVIVAL', '幸存者'), ('SEARCH AND RESCUE', '搜救'),
 ('SHARP SHOOTER', '神枪手'), ('HAMBURGER HILL', '占山为王'), ('CAT AND MOUSE', '猫捉老鼠'),
 ('BEL', '据点'),
 # ---- i.link / misc ----
 ('KEEP', 'KEEP'),
])

# context-fixups: strings whose translation depends on exact original (kept verbatim en)
D['KIT/ROSTER SELECTION'] = '装备/名册选择'
D['QM - TIME - F'] = '快速任务-计时-F'
D['QM - VETERAN - F'] = '快速任务-老兵-F'
D['QM - VETERAN - M'] = '快速任务-老兵-M'
D['QM - VETERAN - R'] = '快速任务-老兵-R'

_m([
 ('ABORT', '中止'), ('ACTION', '行动'), ('AFTER ACTION', '战后回顾'),
 ('CANCEL', '取消'), ('CHANGE', '更改'), ('DOWN', '蹲下'), ('DONE', '完成'),
 ('FRIENDLY', '友军'), ('GO', '开始'), ('GO! GO! GO! GO! GO!', '出发！'),
 ('GAME LAUNCH HALTED.', '游戏启动中止。'), ('GAME NAME:', '游戏名称:'),
 ('GAME LAUNCH ABORTED', '游戏被中止'), ('IP ADDRESS:', 'IP地址:'),
 ('LOCATION: GEORGIA', '地点: 格鲁吉亚'), ('MAIN MENU', '主菜单'),
 ('MAIN MENU ONLY OPTIONS', '只能通过主菜单选择的选项'), ('MAP KEY', '设置按键'),
 ('PLAYER SETUP', '玩家设置'), ('PLAYER:', '玩家:'), ('PLAYERS', '玩家'),
 ('PREPARING TO LAUNCH:', '准备开始:'), ('PROCEED', '继续'), ('REPICK TEAM', '重新选组'),
 ('RETICULE', '准星'), ('SELECT MAIN MENU COMMAND', '选择主菜单命令'),
 ('SELECT SAVED GAME', '选择已保存的游戏'), ('START', '开始'), ('STATISTICS', '统计'),
 ('STATUS', '状态'), ('TEAM DETAIL, ENEMY LOW', '小组高, 敌人低'), ('VS.', '对'),
 ('WEAPON', '武器'), ('WEAPONS', '武器'), ('WRONG MAP VERSION', '地图版本不正确'),
 ('WRONG SOFTWARE VERSION', '软件版本不正确'),
 ('YOUR IP ADDRESS IS', '你的IP地址是 '), ('YOUR IP ADDRESS:', '你的IP地址:'),
 ('FRIENDLY', '友军'),
])

# legal / copyright lines: keep English
LEGAL = {
    '2002 UBI SOFT ENTERTAINMENT.', 'ALL RIGHTS RESERVED.',
    'UBI SOFT ENTERTAINMENT AND THE', "TOM CLANCY'S GHOST RECON IS A",
    'ARE TRADEMARKS OF', 'RESPECTIVE OWNERS.',
    'RED STORM ENTERTAINMENT, INC.', 'STEMBRIDGE GUN RENTAL',
}

_NAME_TOK = re.compile(r"^[A-Z][\w.'\-]*$|^(III|II|IV|von|van|der|de|la|le)$")
def _nameish(n: str) -> bool:
    toks = n.split()
    if not (1 <= len(toks) <= 5):
        return False
    ok = 0
    for t in toks:
        tt = t.strip(',()')
        if tt.upper() in ('III', 'II', 'IV') or _NAME_TOK.match(tt) or t == '(Jihad)':
            ok += 1
    return ok == len(toks) and any(c.isupper() for c in n)

def translate(en: str):
    """returns (zh, category); category in {'zh','keep','role','miss'}"""
    k = key(en)
    n = norm(en)
    if not any(c.isalpha() and ord(c) < 128 for c in n):
        return None, 'keep'          # numbers / punctuation / markup only
    if k in KEEP:
        return None, 'keep'
    if k in D:
        return D[k], 'zh'
    if n.startswith('<title>'):
        r = ROLES.get(n[len('<title>'):].strip().upper())
        if r is not None:
            return '<title>' + r, 'role'
    if k in LEGAL or _nameish(n):
        return None, 'keep'
    return None, 'miss'
