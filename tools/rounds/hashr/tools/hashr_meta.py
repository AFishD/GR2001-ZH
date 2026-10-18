# -*- coding: utf-8 -*-
r"""hashr_meta.py — 由构建报告生成交付用 meta.json (GR_HASHR2400 / GR_HASHR_base)

    python work/builds/GR_HASHR/tools/hashr_meta.py
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
OUT = os.path.join(REPO, 'work', 'builds', 'GR_HASHR')
SENT = (0xB1, 0xB5)

rep = json.load(io.open(os.path.join(OUT, 'temp', 'GR_HASHR2400_build.json'),
                        encoding='utf-8'))
extra, log = rep['extra'], rep['log']
sent_slots = [(L - 0xA1) * 94 + (t - 0xA1) for L in range(0xA1, 0xBA) for t in SENT]
old_names = json.load(io.open(os.path.join(OUT, 'backup',
                                           'charset_compiled_zh16.json.before_hashr'),
                              encoding='utf-8'))
meta = dict(
    tag='GR_HASHR2400',
    title='2,400 字成品盘 + 数据侧「哨兵 trail」重排 (对偶码 trail ∉ {0xB1,0xB5})',
    iso=os.path.join('work', 'builds', 'GR_HASHR', 'GR_HASHR2400.iso'),
    iso_sha256=extra['out_sha'], iso_size=extra['out_size'],
    base=dict(path=os.path.relpath(extra['base'], REPO), sha256=extra['base_sha'],
              size=extra['base_size']),
    build_command=('python work/builds/GR_HASHR/tools/hashr_build.py --mode k2 '
                   '(先 --dry-run 跑全部断言)'),
    verify_command='python work/builds/GR_HASHR/tools/hashr_verify.py',
    changelog=[
        '① charset: 注销全部 50 个 trail ∈ {B1,B5} 的对偶码登记 '
        '(42 真字 + 8 私有区占位); 42 真字整体搬到保留段低位连续 42 槽 1936..1977',
        '② 图集: 42 个字形逐 texel 搬到新槽 (旧槽清零为确定性空模板 0x11)',
        '③ 文本: 3 个中文容器载荷内 738 处 old_pair → new_pair (2 字节换 2 字节)',
    ],
    no_change=[
        '几何 (1024x644 / 64 列 / SKIP=2 / Y0=3) 与 px_size 329744',
        'ELF 闸门 0xBA (4 站点) 与网格常量 (5 字节一个字未动)',
        'FONT.RES / IMG 条目表 (stored/off/real) / ISO 尺寸 / ISO9660',
        '任何文本的字符序列 / 字距 / 折行 (版式影响 = 0)',
    ],
    gate=extra['gate'], slot_space=extra['slot_space'],
    sentinel_trails=[0xB1, 0xB5],
    sentinel_slots=dict(count=len(sent_slots), slots=sent_slots,
                        codes=['%02X%02X' % (0xA1 + s // 94, 0xA1 + s % 94)
                               for s in sent_slots]),
    capacity=dict(
        pair_of_before=extra['pair_of_before'], pair_of_after=extra['pair_of_after'],
        single_codes=103,
        total_glyph_slots=extra['pair_of_after'] + 103,
        requirement=2400,
        note='禁用 2 个 trail ⇒ 对偶可用 2350−50 = 2300；保留段压缩让出 42 槽；'
             '总字形槽 2300+103 = 2403 ≥ 2400 ✓（未抬闸门）'),
    moves=[dict(char=a['char'], old_code='%02X%02X' % tuple(a['old_pair']),
                old_slot=a['old_slot'], new_code='%02X%02X' % tuple(a['new_pair']),
                new_slot=a['new_slot'], evicted_placeholder='U+%04X'
                % ord(a['evicted_placeholder'])) for a in extra['moves']],
    retired=[dict(char='U+%04X' % ord(d['char']), code='%02X%02X' % tuple(d['pair']),
                  slot=d['slot']) for d in extra['retired']],
    glyph_move=dict(n=len(extra['touch']), ink_total=sum(t['ink'] for t in extra['touch']),
                    proof='每个新格回读 == 基底旧格（逐 texel），构建期与回读期各一次'),
    text=dict(hits=extra['text_hits'], per_code=extra['text_per_code'],
              changed_ranges=extra['text_changed_ranges'],
              containers={'EN_STRINGS.RES@MENU': 286, 'EN_STRINGS.RES@GR': 286,
                          'EN_SPECIAL_FEATURE.XML': 166},
              coverage='376 份文本 CSV 权威口径: 被搬 42 字中 32 个在 3 容器（已全改）、'
                       '10 个在全部 CSV 里 0 次；*.TXT 原始命中 0（唯一例外为二进制段）'),
    atlas=extra['atlas'],
    diff=extra.get('diff'),
    diff_list=dict(json='work/builds/GR_HASHR/audit/diff_spans.json',
                   txt='work/builds/GR_HASHR/audit/diff_spans.txt',
                   note='全部差异区间 (off / len / base_hex / prod_hex)；'
                        '3 容器与图集的重压会让"压缩后字节"在重压子流内整体变化，'
                        '但**解压后**的内容只有登记的 2 字节替换（见 verify.txt [V2b]）'),
    selfcheck=dict(
        A1_sentinel_after=0, A2_real_chars='1941 → 1941 (丢失 0)',
        A3_pair_of='2300 条，单射/lead/trail 全合法',
        A4_text_hits=extra['text_hits'], A5_other_text=0,
        A6_glyph_move='42/42 逐 texel', A7_record_overlap=0, A8_record_pixels_changed=0,
        A9_cells='0..2349 互不重复', A10_container_roundtrip=True,
        R1_readback='42/42', R2_readback_containers=7, R6_IMG_entry_fields='未动',
        D_out_of_window=0),
    charset=dict(path='tools/font_pipeline/data/charset_compiled_zh16.json',
                 pair_of_before=extra['pair_of_before'],
                 pair_of_after=extra['pair_of_after'],
                 backup='work/builds/GR_HASHR/backup/charset_compiled_zh16.json.before_hashr',
                 added_section='_trail_fix_hashr'),
    gate_pairs=dict(path='tools/text_csv/gate_pairs.json',
                    backup='work/builds/GR_HASHR/backup/gate_pairs.json.before_hashr',
                    change='新增 trail_fix / trail_fix_pairs / trail_fix_old 段；'
                           'pairs 段原样（load_gate_pairs 行为已实测不变）'),
    dump_font=dict(
        base=dict(iso='work/builds/GR_FA2400_K2/GR_FA2400_K2.iso',
                  charset='backup/charset_compiled_zh16.json.before_hashr',
                  chars=2548, has_glyph=2075, missing=473, pair_has_glyph='1877/2350',
                  geometry_errors=473),
        prod=dict(iso='work/builds/GR_HASHR/GR_HASHR2400.iso',
                  charset='tools/font_pipeline/data/charset_compiled_zh16.json',
                  chars=2498, has_glyph=2075, missing=423, pair_has_glyph='1877/2300',
                  geometry_errors=423),
        command='python work/builds/GR_HASHR/tools/hashr_dump_font.py --iso <iso> '
                '--out <dir> [--charset <json>] --no-png'),
    emulator=dict(
        command='python work\\tools\\cap_run.py --iso <iso> --dump <dir> '
                '--nav tools\\capture\\nav_menu_only.txt --maxframes 6000 --snap 30 --wait-first',
        raw_command='pcsx2-gsrunner.exe -grdumpdir <out> -grmaxframes 6000 -grsnap 30 '
                    '-grinput tools\\capture\\nav_menu_only.txt -grmemcards <out>\\mc '
                    '-logfile <out>\\emulog.txt -- <iso>',
        prod=dict(dump='work/builds/GR_HASHR/runs/hashr2400', n_snap=191, unique_frames=163,
                  tlb_miss=0, trap_exception=0, stalled_pc=0, exit=0, elapsed_s=102,
                  post_procs='none', window='23:48:46 → 23:50:17 (独占，无并发)'),
        base=dict(dump='work/builds/GR_HASHR/runs/k2_base', n_snap=191, unique_frames=163,
                  tlb_miss=0, trap_exception=0, stalled_pc=0, exit=0, elapsed_s=102,
                  post_procs='none', window='23:51:15 → 23:52:57 (尾部约 20 s 与 GR_FPSBISECT '
                                           'batch D 重叠，仅影响速度)'),
        frame_compare='191 张截图 sha256 全部相同（不同 0）⇒ 画面逐像素一致，无可见副作用',
        criteria_ok=True),
    evidence=dict(build_log='work/builds/GR_HASHR/temp/GR_HASHR2400_build.log',
                  verify='work/builds/GR_HASHR/audit/verify.txt',
                  recon=['work/builds/GR_HASHR/audit/recon.txt',
                         'work/builds/GR_HASHR/audit/recon2.txt'],
                  disasm=['work/builds/GR_HASHR/audit/cave_zh113b_drawstring.txt',
                          'work/builds/GR_HASHR/audit/cave_zh113b_entry.txt',
                          'work/builds/GR_HASHR/audit/imm_scan.txt'],
                  report='docs/REPORT_SENTINEL_FIX.md'),
    unknown=['交付 B (GR_ZH113b) 在「不改几何/闸门」下无解（鸽笼证明见报告 §6）',
             '本机 gsrunner 复现不出用户的累积型卡死 ⇒ 实机判据只能证「未引入新故障」',
             '钩子开启时 trail 不进入图标特判（报告 §1.3 反汇编补证）⇒ 若仍卡走代码侧 8 字节臂'],
)
with io.open(os.path.join(OUT, 'GR_HASHR2400.meta.json'), 'w', encoding='utf-8',
             newline='\n') as f:
    json.dump(meta, f, ensure_ascii=False, indent=1)
print('wrote %s' % os.path.join(OUT, 'GR_HASHR2400.meta.json'))
print('moves=%d retired=%d sentinel_slots=%d diff=%s'
      % (len(meta['moves']), len(meta['retired']), len(sent_slots), meta['diff']))
