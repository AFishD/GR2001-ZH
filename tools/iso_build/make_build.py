# -*- coding: utf-8 -*-
r"""make_build.py — 一次性版本构筑器 (work/builds/<版本>/)

用法:
  python tools/iso_build/make_build.py GR_ZH63                                   # 基底=最新构筑, 原样继承
  python tools/iso_build/make_build.py GR_ZH63 --patch my_patch.py               # 继承后应用补丁 (python <patch> <src_iso> <dst_iso>)
  python tools/iso_build/make_build.py GR_ZH63 --from work/builds/GR_ZH62        # 指定基底

基底解析顺序: --from > work/builds/ 下版本号最大者 > work/build/iso/GR_ZH*.iso (旧位置)。
产出 work/builds/<版本>/:
  <版本>.iso                     完整盘
  extract/ft_font_res.bin        字表 (MENU.IMG @0xB9120, 4421B)
  extract/font_new_font_revised.bin  字库纹理 PAK 记录 (MENU.IMG @0x58431, 0x4044C)
  extract/MENU.IMG               文本/UI 容器全量 (58MB; 文本在压缩 RES 内, 用 hanliu 工具解码)
  temp/                          模拟器测试截图/日志/转储落这里
  build_info.json                版本/基底/sha256/时间

布局常数 (MENU.IMG 内, 全版本稳定, 见 docs/BUILD_MANIFEST.md):
  MENU_LBA=776286, 字库记录 @0x58431 (0x4044C), 字表槽 @0xB9120 (4421B)
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, time

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
BUILDS = os.path.join(REPO, 'work', 'builds')
LEGACY = os.path.join(REPO, 'work', 'build', 'iso')
MENU_LBA, MENU_SIZE = 776286, 58300882
OFF_FT, OFF_REC = 0xB9120, 0x58431
REC_LEN = 0x4147D - 0x1031


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def latest_build():
    best = (-1, None)
    if os.path.isdir(BUILDS):
        for d in os.listdir(BUILDS):
            m = re.fullmatch(r'GR_ZH(\d+)', d)
            if m and os.path.isfile(os.path.join(BUILDS, d, d + '.iso')):
                best = max(best, (int(m.group(1)), os.path.join(BUILDS, d)))
    if best[1] is None and os.path.isdir(LEGACY):
        for d in os.listdir(LEGACY):
            m = re.fullmatch(r'GR_ZH(\d+)\.iso', d)
            if m:
                best = max(best, (int(m.group(1)), LEGACY))
    return best[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('version')
    ap.add_argument('--patch', help='补丁脚本: python <patch> <src_iso> <dst_iso>')
    ap.add_argument('--from', dest='base', help='基底构筑目录或 ISO 路径')
    a = ap.parse_args()
    ver = a.version
    assert re.fullmatch(r'GR_ZH\d+', ver), '版本名须为 GR_ZH<数字>: %s' % ver
    out = os.path.join(BUILDS, ver)
    assert not os.path.exists(out), out + ' 已存在'

    if a.base:
        base = a.base
    else:
        base = latest_build()
        assert base, '找不到基底 (work/builds 为空且无旧位置 ISO)'
    base_iso = base if base.endswith('.iso') else os.path.join(base, os.path.basename(base) + '.iso')
    assert os.path.isfile(base_iso), base_iso
    print('[base] %s (sha %s...)' % (base_iso, sha256(base_iso)[:16]))

    os.makedirs(out)
    dst_iso = os.path.join(out, ver + '.iso')
    if a.patch:
        r = subprocess.run([sys.executable, a.patch, base_iso, dst_iso])
        assert r.returncode == 0, '补丁脚本失败'
    else:
        shutil.copyfile(base_iso, dst_iso)
    assert os.path.getsize(dst_iso) == os.path.getsize(base_iso), 'ISO 尺寸变化?'
    print('[iso] %s (%.2f GB)' % (dst_iso, os.path.getsize(dst_iso) / 1e9))

    ext = os.path.join(out, 'extract')
    os.makedirs(ext)
    with open(dst_iso, 'rb') as f:
        f.seek(MENU_LBA * 2048)
        menu = f.read(MENU_SIZE)
    assert len(menu) == MENU_SIZE
    open(os.path.join(ext, 'MENU.IMG'), 'wb').write(menu)
    open(os.path.join(ext, 'ft_font_res.bin'), 'wb').write(menu[OFF_FT:OFF_FT + 4421])
    open(os.path.join(ext, 'font_new_font_revised.bin'), 'wb').write(menu[OFF_REC:OFF_REC + REC_LEN])
    print('[extract] 字表 4421B + 字库记录 %dB + MENU.IMG %dMB → extract/' % (REC_LEN, MENU_SIZE // 1048576))

    os.makedirs(os.path.join(out, 'temp'))
    info = dict(version=ver, base=base_iso, patch=a.patch or None,
                iso_sha256=sha256(dst_iso), built=time.strftime('%Y-%m-%d %H:%M'))
    json.dump(info, open(os.path.join(out, 'build_info.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('[done] %s — 测试产物放 %s/temp/' % (out, out))


if __name__ == '__main__':
    main()
