# -*- coding: utf-8 -*-
r"""cvar_meta_fix.py — 修正各 meta.json 的 desc 字段 (命令行传中文会被代码页弄坏)

描述文本写在本脚本里 ⇒ 保证 UTF-8 正确。只改 desc / 追加 guide 引用, 其它字段不动。
用法: python cvar_meta_fix.py --dir .
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DESC = {
    'CVAR_01_elf': '原盘 + 仅 P1：ELF 代码补丁（SLUS_206.13）。含字库解码 cave（覆盖 EN 侧既有代码 的 '
                   '0x416ED0..0x41721B / 0x417500..0x4176E8）、原盘全零区里新增的 cave（0x411690、'
                   '0x565670..0x565A47）、字形带常量闸门改动（0xFFB5→0x00B5 等，22 个站点）、'
                   'ELF 内字符串表 ASCII→GBK（0x577FA0）、以及 14 个零散指令改动。'
                   '不含图集/FONT.RES/文本。',
    'CVAR_02_atlas': '原盘 + 仅 P2：MENU.IMG 与 GR.IMG 里的 COMMON.PAK（含其中的字库容器 new_font_revised '
                     '与图集像素）。★ 本盘 COMMON.PAK 的 stored/real 都是 400659，与原盘**完全一致**，'
                     'PAK 没有长大 ⇒ 不需要 P5 的任何簿记联动，本盘是纯粹的 P2 单变量。',
    'CVAR_03_ft': '原盘 + 仅 P3：MENU.IMG 与 GR.IMG 里的 FONT.RES（各 4421 B 盘上长度）。'
                  '★ 注意：ZH 版 FONT.RES 的内部头 f0/f1 缩小了（MENU 1489/5942、GR 1332/5942，'
                  'EN 是 4413/7222），但 IMG 条目表的 stored/real 仍是 4421/7222，'
                  '盘上剩余部分用 0 补齐；两份 FONT.RES 在 EN 里字节相同，在 ZH 里已不再相同。',
    'CVAR_04_text': '原盘 + 仅 P4：三份文本容器 —— MENU.IMG::EN_STRINGS.RES（stored 47570 / real 128545）、'
                    'GR.IMG::EN_STRINGS.RES（stored 47619 / real 128668）、'
                    'MENU.IMG::EN_SPECIAL_FEATURE.XML（stored 49700 / real 116430）与 '
                    'GR.IMG::EN_SPECIAL_FEATURE.XML（stored 49710 / real 116488）。'
                    '这四项的尺寸与 off 全部未变，条目表一字节未动。',
    'CVAR_05_elf_atlas': '原盘 + P1+P2：ELF 补丁 + 字库图集（不含 FONT.RES、不含任何中文文本）。'
                         '这是最接近「字库可用但没有中文文本」的组合，用来区分'
                         '「字形/图集侧」与「文本侧」谁触发卡死。',
    'CVAR_06_rest': '原盘 + P5+P6：ISO/IMG 结构簿记（MENU.IMG 条目表 #30 EN_STRINGS.TXT 被搬到 '
                    'MENU.IMG 末尾、#282 NTSC_IKE.RES stored 长大，共 4 个游程 8 字节）'
                    '加上**其余全部未归类改动**（P1..P4 的补集，共 136 个结构）。'
                    'P6 里最大的一块是 20 个 *_MESSAGE_MC_*.RSB 的调色板/像素改写（778,952 B）。',
    'CVAR_00_orig': '英文原盘对照基线。本盘**不复制**，直接使用 work\\builds\\GR_EN_ORIG\\GR_EN_ORIG.iso'
                    '（sha256 2b42ea7ce9bd0a85972a07ca59b1b9d79422ed318b85737db3cfd17daa788531）。',
    'CVAR_ALL_localized': '汉化基底盘（全部部件都在）。本盘**不复制**，直接使用 '
                          'work\\builds\\GR_ZH113b\\GR_ZH113b.iso'
                          '（sha256 ff3abd3c50e380f666955ccb6226b67198e181589c0db9b4d52e4643208f6445）。',
}

GUIDE = 'docs/CVAR_TEST_GUIDE.md'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default='.')
    x = ap.parse_args()
    for name, d in DESC.items():
        if name in ('CVAR_00_orig', 'CVAR_ALL_localized'):
            continue
        p = os.path.join(x.dir, '%s.meta.json' % name)
        if not os.path.exists(p):
            print('  !! 缺少 %s' % p)
            continue
        with open(p, encoding='utf-8') as f:
            j = json.load(f)
        old = j.get('desc', '')
        j['desc'] = d
        j['desc_was_mojibake'] = (old != d)
        j['test_guide'] = GUIDE
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(j, f, indent=1, ensure_ascii=False)
        print('  %-22s desc 已修正 (旧值长度 %d)' % (name, len(old)))
    # 回读校验
    print('== 回读校验 ==')
    for name in DESC:
        if name in ('CVAR_00_orig', 'CVAR_ALL_localized'):
            continue
        p = os.path.join(x.dir, '%s.meta.json' % name)
        with open(p, encoding='utf-8') as f:
            j = json.load(f)
        print('  %-22s JSON 合法 OK  parts=%-22s sha256=%s'
              % (name, '+'.join(j['parts']), j['sha256'][:16]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
