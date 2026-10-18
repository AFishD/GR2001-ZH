# -*- coding: utf-8 -*-
r"""oomfix_meta_ext.py —— 给出盘 meta.json 追加「cave 选址理由 / 存档注意事项 / 验证读数」。

出盘工具 `oomfix_apply.py` 落的是**构建期**证据（逐字节 diff + 自证）；
本工具把**选址理由**与**后续验证读数**补进同一份 meta.json（不改产物、不重算 sha256）。
用法: python oomfix_meta_ext.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OOM = os.path.abspath(os.path.join(HERE, '..'))

CAVE_RATIONALE = (
    "cave 落点 0x00550048..0x00550080（56 B，本补丁只用前 44 B）的理由："
    "(1) 原盘/两基底逐字节全零（出盘工具断言）；"
    "(2) .symtab（19496 个 FUNC 区间）没有任何符号覆盖或紧邻该区间；"
    "    上一条函数在 0x00550040 `j 0x0054FF68` + 延迟槽 `addiu sp,sp,0x30` 收尾 ⇒ 不可能线性落入；"
    "    下一段（0x00550080 起）是 VU0 微码（TEST_VU0_CODE/.vutext/.vif.2/_$BEGIN_VU0_DRIVER）；"
    "(3) 全 .text（只扫 FUNC 符号覆盖的地址，避开把 .rodata/.data 当代码的假命中）对 "
    "0x550040..0x5500C0 的 j/jal/分支目标 = 0；"
    "(4) 装载段内没有 32 位字面量指向该区间；"
    "(5) lui+addiu/ori 合成地址扫描：整个 0x54FF00..0x550200 只有 1 处引用（0x005500F0，VU0 微码），不涉及本区间；"
    "(6) .relmain 的 200,480 条重定位没有一条落点在此；"
    "(7) 与 DBCS cave 全区（0x416E00..0x417800）、4 个闸门、ZH cave block B（0x565600..0x565B00）、"
    "0x411690 / 0x21CC08 / 0x407078 / 0x408928 等既知占用区无重叠（出盘工具逐字节断言）；"
    "(8) 运行期未被改写：冷启动跑到第 5970 帧后，EE RAM 里 12 个补丁字逐字相符。"
    " 被否决的候选：0x0055B730..0x0055B780 属 __data_start/main_arena 数据区（运行时堆管理结构）；"
    "0x005DECC4..0x005DED00 是 __data_end 到 __bss_start 的填充但紧邻 _overlay_group_addresses/BSS。"
)

CAVE_AUDIT = dict(
    region='0x00550048..0x00550080 (56 B, 原盘全零，本补丁用前 44 B)',
    zero_in_base=True,
    symbols_overlapping=0,
    ctrl_refs_from_func_code=0,
    literal_words_pointing_in=0,
    lui_synth_refs=0,
    reloc_sites_in_region=0,
    forbidden_overlaps=0,
    rewritten_after_cold_boot_6000f=False,
    rejected_candidates=['0x0055B730..0x0055B780 (data/main_arena)',
                         '0x005DECC4..0x005DED00 (__data_end padding, 邻 BSS/overlay)'],
    evidence=[r'work\builds\GR_OOMFIX\cave_scan.json',
              r'work\builds\GR_OOMFIX\tools\oomfix_cave.py',
              r'work\builds\GR_OOMFIX\runs\smoke_OOMFIX2400\win_f00005970_eeram.bin'],
)

SAVESTATE_NOTE = (
    "★ 验证本补丁**不能**读旧的即时存档：PCSX2 的 .p2s 内含整块 32 MB EE 主存（eeMemory.bin），"
    "读档后 VM 从存档 PC 继续、BIOS 不再从光盘装载 ELF ⇒ 光盘里的补丁会被存档里的旧代码覆盖。"
    "实测：修好的盘 + 旧存档，f43/f44 的 RAM 与未修盘逐字节相同（差分 0 B）。"
    "要用同一现场验证，必须把同样的补丁打进存档的 eeMemory.bin："
    "work\\builds\\GR_OOMFIX\\states\\SLUS-20613 (CC41DF03).01.p2s"
    "（工具 work\\builds\\GR_OOMFIX\\tools\\oomfix_zstd.py + tools\\state_patch_spec.json）。"
)

VERIFICATION = dict(
    recipe=dict(exe=r'work\builds\GR_OOMFIX\emu\gsrunner\pcsx2-gsrunner.exe',
                exe_sha256='E58253069BEE248FA46ACF56873540D096BB3B816F0A3B40783BFA3074813EE6',
                state=r'work\builds\GR_OOMFIX\common\state_LAY_fix1_bytecount.p2s',
                state_patched=r'work\builds\GR_OOMFIX\states\SLUS-20613 (CC41DF03).01.p2s',
                input=r'work\builds\GR_OOMFIX\inputs\in_l1_f30.txt (30 l1 press)',
                maxframes=130),
    unpatched=dict(run=r'work\builds\GR_OOMFIX\runs\u1_base_l1',
                   trap_lines=4990386, unrecognized_op_lines=53,
                   w1300_hits_frame44=63, low_0_400_diff_bytes=839,
                   low_400_1000_diff_bytes=2483, ram_diff_f43_f46_bytes=83405),
    patched=dict(run=r'work\builds\GR_OOMFIX\runs\p2_patched_state',
                 trap_lines=0, unrecognized_op_lines=0,
                 w1300_hits_frame44=0, low_0_400_diff_bytes=0, low_400_1000_diff_bytes=0,
                 ram_diff_f43_f44_bytes=31218,
                 cave_entries=4, caller_fail_branch_taken=True,
                 outcome='frame 44 终止：Jump to unaligned address (PC: 0x7e7e7e7e) → VM Paused'),
    smoke=dict(frames=6000, snaps=191, tlb_miss=0, trap=0, unrecognized_op=0,
               frames_identical_vs_base='191/191 (different 0)'),
)

SUMMARY = ('F1+F2 已确定性验证：消除低端写入与 Trap，并复用调用者现成的失败分支；'
           '但在该存档现场游戏仍在第 44 帧以另一种方式终止（根因 = 那次 64 KB 分配失败/堆耗尽，未解决）。'
           '详见 docs\\REPORT_OOMFIX.md')


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    for tag in ('OOMFIX2400', 'OOMFIX_lay1'):
        p = os.path.join(OOM, tag + '.meta.json')
        m = json.load(open(p, encoding='utf-8'))
        m['cave_rationale'] = CAVE_RATIONALE
        m['cave_audit'] = CAVE_AUDIT
        m['savestate_note'] = SAVESTATE_NOTE
        m['verification'] = VERIFICATION
        m['summary'] = SUMMARY
        m['meta_extended_by'] = r'work\builds\GR_OOMFIX\tools\oomfix_meta_ext.py（追加说明字段，未改产物/未重算 sha256）'
        json.dump(m, open(p, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
        print('[ok] %s  (%d B)' % (p, os.path.getsize(p)))


if __name__ == '__main__':
    main()
