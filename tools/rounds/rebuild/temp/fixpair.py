import io
import os

for rel in (r'work\builds\GR_REBUILD\tools\rb_textaudit.py',
            r'work\builds\GR_REBUILD\tools\rb_sfffd.py'):
    p = os.path.abspath(rel)
    t = io.open(p, encoding='utf-8').read()
    old = "pair_dec = {tuple(p): ch for ch, p in cs.pair_of.items()}"
    new = ("pair_dec = {tuple(k): v for k, v in cs.pair_of.items()}"
           "   # cs.pair_of 本身即 (b1,b2)→字")
    assert old in t, 'anchor missing in %s' % rel
    t = t.replace(old, new)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
    print('patched', p)
