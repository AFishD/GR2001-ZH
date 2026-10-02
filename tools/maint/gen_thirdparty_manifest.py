# -*- coding: utf-8 -*-
r"""gen_thirdparty_manifest.py — third_party 内容清单生成器

third_party/ 全部内容不入库 (见 .gitignore), 本脚本遍历生成 readme.md:
每文件一行 <md5>  <大小字节>  <相对路径>, 按区段分组。内容变更后重跑即可。
用法: python tools/maint/gen_thirdparty_manifest.py
"""
import hashlib, os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TP = os.path.join(ROOT, 'third_party')

SECTIONS = [
    ('orig/ps2', 'PS2 原盘 (用户自抓) 与系统文件抽取'),
    ('orig/ghost_recon_pc', 'PC 版 Ghost Recon 原始安装 (格式研究参照)'),
    ('fonts', '第三方字体 (方正像素16)'),
    ('emu', '模拟器 (PCSX2 2.8.2 定制构建: 源码 gr-2.8.2 分支 + 部署运行时 + BIOS/记忆卡)'),
    ('deps', '构建依赖 (CMake/Ninja 工具链安装态)'),
    ('dep', '构建依赖 (原始下载档案)'),
]


def md5(path, total):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
            total[0] += len(b)
    return h.hexdigest()


def main():
    lines = ['# third_party 内容清单', '',
             '本目录全部内容**不入库** (.gitignore: `third_party/**`)，此清单为唯一 tracked 记录:',
             '每行 = `<md5> <字节数> <相对 third_party 的路径>`。内容增删后重跑:',
             '`python tools/maint/gen_thirdparty_manifest.py`', '',
             '生成时间: %s' % time.strftime('%Y-%m-%d %H:%M'), '']
    grand_n, grand_b = 0, 0
    t0 = time.time()
    for sub, desc in SECTIONS:
        base = os.path.join(TP, sub.replace('/', os.sep))
        if not os.path.isdir(base):
            continue
        lines += ['## %s — %s' % (sub, desc), '', '```']
        n = b = 0
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames.sort()
            for fn in sorted(filenames):
                p = os.path.join(dirpath, fn)
                rel = os.path.relpath(p, TP).replace(os.sep, '/')
                sz = os.path.getsize(p)
                lines.append('%s  %14d  %s' % (md5(p, [0]), sz, rel))
                n += 1
                b += sz
        lines += ['```', '', '小计: %d 文件 / %.2f GB' % (n, b / 1e9), '']
        grand_n += n
        grand_b += b
    lines += ['---', '', '总计: %d 文件 / %.2f GB (hash 耗时 %.0f s)' % (grand_n, grand_b / 1e9, time.time() - t0)]
    out = os.path.join(TP, 'readme.md')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('written', out, '%d files, %.2f GB' % (grand_n, grand_b / 1e9))


if __name__ == '__main__':
    main()
