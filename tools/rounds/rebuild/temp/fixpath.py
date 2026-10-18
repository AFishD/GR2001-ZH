import io
import os

p = os.path.abspath(r'work\builds\GR_REBUILD\tools\rb_verify_k2.py')
t = io.open(p, encoding='utf-8').read()
old = "sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))"
new = ("sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))\n"
       "sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))")
assert old in t, 'pattern not found'
t = t.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
print('patched sys.path in', p)
