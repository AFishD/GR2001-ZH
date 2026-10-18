# -*- coding: utf-8 -*-
r"""s6_dis.py — 用仓库自带的 PS2 EE 反汇编器 (tools/hanliu/tools/dis4.py) 反汇编现役盘的 cave。

做法: 把 GR_ZH93.iso 里 LBA 295 起的前 7MB (= SLUS_206.13 文件头) 抽到 temp/r44/,
      再把 dis4.py 的 ELF 路径改指到它, exec 出 dis() 函数 (不跑它的顶层 main)。只读 ISO。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_repo(p):
    while True:
        if os.path.isfile(os.path.join(p, 'tools', 'text_csv', 'tcslib.py')):
            return p
        q = os.path.dirname(p)
        if q == p:
            raise SystemExit('!! 找不到仓库根')
        p = q


REPO = find_repo(HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LOG = []


def log(s):
    print(s)
    LOG.append(s)


ELF_LBA = 295
HEAD_LEN = 0x700000


def extract_elf_head(iso):
    out = os.path.join(HERE, 'SLUS_206.13.zh93.head')
    if not os.path.isfile(out) or os.path.getsize(out) != HEAD_LEN:
        with open(iso, 'rb') as f:
            f.seek(ELF_LBA * 2048)
            b = f.read(HEAD_LEN)
        assert b[:4] == b'\x7fELF', b[:8]
        with open(out, 'wb') as f:
            f.write(b)
    return out


def load_dis4(elf_path):
    src = open(os.path.join(REPO, 'tools', 'hanliu', 'tools', 'dis4.py'), encoding='utf-8').read()
    old = "ELF = os.path.join(REPO_ROOT, 'build', 'bases', 'slus_out', 'SLUS_206.13')"
    assert old in src, 'dis4.py 的 ELF 常量行变了, 请同步本脚本'
    src = src.replace(old, 'ELF = %r' % elf_path)
    g = {'__name__': 'dis4mod', '__file__': os.path.join(REPO, 'tools', 'hanliu', 'tools', 'dis4.py')}
    exec(compile(src, 'dis4.py', 'exec'), g)          # noqa: S102
    return g


def main():
    iso = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')
    elf = extract_elf_head(iso)
    log('[elf] 现役盘 ELF 头 → %s (%d 字节)' % (os.path.basename(elf), os.path.getsize(elf)))
    g = load_dis4(elf)
    dis = g['dis']
    for nm, va, ln in (('cw  cave (hook 0x21AD18)', 0x416F40, 0x80),
                       ('cctc cave (hook 0x21ADE0)', 0x417050, 0x100),
                       ('sw  cave (hook 0x21AC74)', 0x417150, 0x80)):
        log('=' * 78)
        log('[%s] VA 0x%06X..0x%06X' % (nm, va, va + ln))
        log(dis(va, ln))
    with open(os.path.join(HERE, 's6_dis.log'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
