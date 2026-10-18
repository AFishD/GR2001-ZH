# -*- coding: utf-8 -*-
r"""combfix_statefix.py -- patch a savestate's eeMemory with **every** patch the disc carries.

为什么需要它：`spinfix_state_fix.py` 只读 meta 的 `sites` / `caves`；而 COMBFIX_A/B/C 的
F4 是**从基底继承**的（写在 meta 的 `inherited_patches` 里），不会被它注入 ⇒ 存档里
0x102588 仍是原来的 `bne`，现场跑出来的是「没有 F4 的盘」（本工程 d2 首跑就踩到了：
F7 生效后倒在**未受保护的 binmap 回边** 0x1024D0/0x102584 上自旋）。

本工具把 meta 的 sites + caves + inherited_patches 合成一份标准 spec（sites/caves），
再调用 GR_SPINFIX 的 spinfix_state_fix.py 做真正的注入与回读自证。

用法：
  python combfix_statefix.py --state <in.p2s> --meta <flavor.meta.json> --iso <flavor.iso> --out <out.p2s>
"""
import argparse
import json
import os
import struct
import subprocess
import sys

ROOT = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
PY = sys.executable


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('--state', required=True)
    ap.add_argument('--meta', required=True)
    ap.add_argument('--iso', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--spec', default=None)
    a = ap.parse_args()

    meta = json.load(open(os.path.join(ROOT, a.meta), encoding='utf-8'))
    sites = [dict(name=s['name'], va=s['va'], new_word=s['new_word']) for s in meta['sites']]
    caves = [dict(name=c['name'], va=c['va'], words=c['words']) for c in meta['caves']]
    for inh in meta.get('inherited_patches', []):
        sites.append(dict(name=inh['name'], va=inh['va'], new_word=inh['new_word']))
        caves.append(dict(name=inh['name'], va=inh['cave']['va'], words=inh['cave']['words']))
    spec = dict(flavor=meta['flavor'] + '(+inherited)', sites=sites, caves=caves)
    sp = a.spec or os.path.join(ROOT, 'work', 'builds', 'GR_COMBFIX', 'out',
                                'statepatch_%s.json' % meta['tag'])
    with open(sp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    print('[spec] %s  sites=%d caves=%d（含继承的 %s）' % (
        sp, len(sites), len(caves),
        ','.join(i['name'] for i in meta.get('inherited_patches', [])) or '无'))
    tool = os.path.join(ROOT, 'work', 'builds', 'GR_SPINFIX', 'tools', 'spinfix_state_fix.py')
    cmd = [PY, tool, '--state', a.state, '--meta', sp, '--iso', a.iso, '--out', a.out]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    print(r.stdout[-4000:] if r.stdout else '')
    if r.returncode != 0:
        print(r.stderr[-4000:] if r.stderr else '')
        raise SystemExit('state fix failed rc=%d' % r.returncode)
    return 0


if __name__ == '__main__':
    sys.exit(main())
