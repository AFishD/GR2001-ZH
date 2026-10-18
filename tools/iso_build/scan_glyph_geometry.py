# -*- coding: utf-8 -*-
r"""scan_glyph_geometry.py — 字形几何体检 CLI (round50): 出 `truncation_report.json` / `.md`。

    python tools/iso_build/scan_glyph_geometry.py --iso work/builds/GR_ZH98/GR_ZH98.iso \
        --out work/builds/GR_ZH98/temp/r50 [--prefix GR_ZH98] [--charset <json>]

判据与实现全部在 `tools/iso_build/glyph_geometry.py` (dump_font 每轮构筑也调它)。
★ 只读盘; 只往 --out 写报告。
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
except Exception:                                                        # noqa: BLE001
    pass

import tcslib                                            # noqa: E402
import dump_font                                         # noqa: E402
import glyph_geometry                                    # noqa: E402


def main():
    ap = argparse.ArgumentParser(description='字形几何体检 (只读): 找截断/空白/越窗/极稀')
    ap.add_argument('--iso', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--prefix', default=None)
    ap.add_argument('--charset', default=None, help='字符表 JSON (默认 tcslib.CHARSET)')
    ap.add_argument('--ttf', default=None)
    ap.add_argument('--no-template', action='store_true', help='只做几何判据, 不比 TTF 模板')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()

    iso = os.path.abspath(a.iso)
    if not os.path.isfile(iso):
        raise SystemExit('!! 找不到 ISO: %s' % iso)
    font = dump_font.load_font(iso)
    gray = dump_font.atlas_gray(font['atlas'], view='engine')
    cs = tcslib.Charset(a.charset) if a.charset else tcslib.Charset()
    doc = glyph_geometry.analyze(gray, font['atlas'], font['faces'], cs, iso_path=iso,
                                 iso_sha256=tcslib.sha256_file(iso), ttf_path=a.ttf,
                                 verbose=not a.quiet,
                                 strict_template=not a.no_template)
    doc['charset'] = glyph_geometry.rel(a.charset or tcslib.CHARSET)
    pj, pm = glyph_geometry.write_reports(doc, a.out, a.prefix or '')
    print('[geom] JSON → %s' % glyph_geometry.rel(pj))
    print('[geom] 人话 → %s' % glyph_geometry.rel(pm))
    return 0


if __name__ == '__main__':
    sys.exit(main())
