# -*- coding: utf-8 -*-
"""Charset + glyph probe for the GR_ZH111 baseline.

Usage:
  python charset_probe.py chars <char...>        # membership of individual chars
  python charset_probe.py text  <string>...       # check_text on each string
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                               # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH111', 'GR_ZH111.iso')


def main():
    cs = T.Charset()
    iso = T.Iso(ISO)
    g = T.GlyphCache(cs, iso)
    print('# charset: single=%d pair=%d ; glyph notes=%s'
          % (len(cs.enc_single), len(cs.enc_pair), g._note))
    args = sys.argv[1:]
    mode = args[0] if args else 'chars'
    if mode == 'chars':
        for s in args[1:]:
            for ch in s:
                o = ord(ch)
                single = cs.enc_single.get(ch)
                pair = cs.enc_pair.get(ch)
                enc = g.encodable(ch)
                gr = g.glyph_reason(ch)
                print('%-4s U+%04X  single=%-6s pair=%-12s encodable=%-5s glyph=%s'
                      % (ch, o, single, pair, enc, 'OK' if gr is None else 'MISSING: ' + gr))
    else:
        for s in args[1:]:
            probs = g.check_text(s)
            bad = [p['char'] for p in probs if p['kind'] != 'ascii_no_glyph']
            warn = [p['char'] for p in probs if p['kind'] == 'ascii_no_glyph']
            print('%-34s bad=%-14s warn=%s' % (s, ''.join(bad) or '-', ''.join(warn) or '-'))
            for p in probs[:6]:
                print('      %s: %s' % (p['kind'], p['reason']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
