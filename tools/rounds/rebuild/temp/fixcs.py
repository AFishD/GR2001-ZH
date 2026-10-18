import io
import os

for rel in (r'work\builds\GR_REBUILD\tools\rb_textaudit.py',
            r'work\builds\GR_REBUILD\tools\rb_sftext_k2cs.py'):
    p = os.path.abspath(rel)
    t = io.open(p, encoding='utf-8').read()
    old = "        T.CHARSET = os.path.abspath(a.charset)"
    new = ("        T.CHARSET = os.path.abspath(a.charset)\n"
           "        T.Charset.__init__.__defaults__ = (T.CHARSET,)   # 默认参数是 def 期绑定的")
    if old in t:
        t = t.replace(old, new)
    old2 = ("    T.CHARSET = os.path.join(REPO, 'work', 'builds', 'GR_HASHR', 'backup',\n"
            "                             'charset_compiled_zh16.json.before_hashr')")
    new2 = old2 + "\n    T.Charset.__init__.__defaults__ = (T.CHARSET,)"
    if old2 in t:
        t = t.replace(old2, new2)
    io.open(p, 'w', encoding='utf-8', newline='\n').write(t)
    print('patched', p)
