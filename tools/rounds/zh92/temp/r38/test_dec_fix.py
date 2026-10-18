# -*- coding: utf-8 -*-
r"""test_dec_fix.py — 验证 res_text_dump.py 的单字节优先口径修正"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'diag'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import res_text_dump as R  # noqa: E402
import tcslib  # noqa: E402

CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
dec = R.Dec(CS)
cs = tcslib.Charset(CS) if hasattr(tcslib, 'Charset') else None

CASES = [
    (bytes([0xAF, 0xA1, 0xBD]), '的方'),
    (bytes([0xAF]), '的'),
    (bytes([0xB0]), '你'),
    (bytes([0x41, 0x42]), 'AB'),
]
ok = True
for raw, want in CASES:
    got = dec.text(raw)
    good = got.startswith(want)
    ok &= good
    print('  %-14s → %-8s (期望以 %s 开头) %s'
          % (raw.hex(' ').upper(), got, want, '✓' if good else '✗'))
print('单字节优先修正:', '通过 ✓' if ok else '失败 ✗')

# 与 tcslib 交叉: 抽 charset 里前 200 个字做 encode→decode 往返
if cs is not None:
    n = bad = 0
    for ch in list(json.load(io.open(CS, encoding='utf-8'))['pair_of'])[:200]:
        try:
            b = cs.encode_strict(ch) if hasattr(cs, 'encode_strict') else None
        except Exception:  # noqa: BLE001
            b = None
        if not b:
            continue
        n += 1
        if dec.text(bytes(b)) != ch:
            bad += 1
            if bad <= 5:
                print('   往返不一致: %s (%s) → %s' % (ch, bytes(b).hex(' ').upper(), dec.text(bytes(b))))
    print('与 tcslib 交叉: 抽检 %d 字, 不一致 %d 个 %s' % (n, bad, '✓' if bad == 0 else '✗'))
