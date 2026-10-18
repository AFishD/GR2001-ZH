import io
import os

p = os.path.abspath(r'work\builds\GR_REBUILD\tools\rb_verify_k2.py')
t = io.open(p, encoding='utf-8').read()
old = "REPO = os.path.abspath(os.path.join(HERE, '..', '..'))"
new = "REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))"
assert old in t, 'pattern not found'
t = t.replace(old, new)
io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('patched REPO in', p)
