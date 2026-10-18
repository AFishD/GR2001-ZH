# -*- coding: utf-8 -*-
r"""spinfix_state_fix.py —— 把某个 flavor 的补丁**同时**打进即时存档的 eeMemory.bin。

为什么必须这样做（GR_OOMFIX 已实测、本工程沿用）：
  PCSX2 的 .p2s 里 `eeMemory.bin` 是**整块 32MB EE 主存**；`-grstate` 载入后 VM 直接从
  存档的 PC 继续，BIOS 不会再从光盘装载 ELF ⇒ **只改 ISO 的补丁在读旧存档时不生效**。
  要在同一现场验证代码修复，必须把补丁也写进存档的 eeMemory.bin。

做法：从**已构建好的 ISO 的 ELF** 里按 meta.json 声明的窗口（站点字 + cave 全部字）
      逐字节抄进存档 RAM 的同一 VA。这样「盘上跑的代码」与「存档里的代码」逐字相同。

用法：
  python spinfix_state_fix.py --state <in.p2s> --meta <flavor.meta.json> --iso <flavor.iso> --out <out.p2s>
"""
import argparse
import hashlib
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sf_common as C   # noqa: E402
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    'spinfix_state', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'spinfix_state.py'))
_sst = importlib.util.module_from_spec(_spec)
sys.modules['spinfix_state'] = _sst


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('--state', required=True)
    ap.add_argument('--meta', required=True)
    ap.add_argument('--iso', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    z = C.load_zstd_tool()
    meta = json.load(open(os.path.join(C.ROOT, a.meta), encoding='utf-8'))
    elf, lba, esize = C.read_elf_from_iso(os.path.join(C.ROOT, a.iso))
    ram = bytearray(z.decompress_entry(os.path.join(C.ROOT, a.state), 'eeMemory.bin'))
    assert len(ram) == 32 << 20

    # 声明窗口：站点 4B + cave 全部字
    wins = []
    for s in meta['sites']:
        va = int(s['va'], 16)
        wins.append((va, struct.pack('<I', int(s['new_word'], 16)), 'site ' + s['name']))
    for c in meta['caves']:
        va = int(c['va'], 16)
        wins.append((va, b''.join(struct.pack('<I', int(w, 16)) for w in c['words']),
                     'cave ' + c['name']))

    print('[state-fix] state=%s' % a.state)
    print('            meta =%s (flavor %s)' % (a.meta, meta['flavor']))
    print('            iso  =%s' % a.iso)
    for va, blob, why in wins:
        eo = C.elf_off(va, lba)
        fromiso = elf[eo:eo + len(blob)]
        assert fromiso == blob, '%s：ISO 与 meta 不符 @0x%08X' % (why, va)
        old = bytes(ram[va:va + len(blob)])
        ram[va:va + len(blob)] = blob
        print('   %-10s VA 0x%08X (%2d B)  %s -> %s'
              % (why, va, len(blob), old[:8].hex(), blob[:8].hex()))

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    z.rewrite(os.path.join(C.ROOT, a.state), os.path.abspath(a.out), 'eeMemory.bin', bytes(ram))
    chk = z.decompress_entry(os.path.abspath(a.out), 'eeMemory.bin')
    ok = all(chk[va:va + len(blob)] == blob for va, blob, _w in wins)
    base_ram = z.decompress_entry(os.path.join(C.ROOT, a.state), 'eeMemory.bin')
    nd = sum(1 for i in range(len(chk)) if chk[i] != base_ram[i])
    print('[out] %s  %d B  sha256=%s'
          % (a.out, os.path.getsize(a.out), C.sha256_file(a.out)))
    print('   回读 OK=%s ; 与输入存档差异 %d B（声明窗口合计 %d B）'
          % (ok, nd, sum(len(b) for _v, b, _w in wins)))
    assert ok, '回读不符'
    assert nd <= sum(len(b) for _v, b, _w in wins), '改动超出声明窗口'
    return 0


if __name__ == '__main__':
    sys.exit(main())
