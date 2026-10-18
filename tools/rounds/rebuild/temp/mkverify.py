import io,os,re
src=os.path.abspath(r'tools\re\toolbelt\cap_verify_k2.py')
dst=os.path.abspath(r'work\builds\GR_REBUILD\tools\rb_verify_k2.py')
t=io.open(src,encoding='utf-8').read()
t=t.replace("OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_FA2400_K2')",
            "OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', 'temp', 'verify_out')")
t=t.replace("    ap.add_argument('--no-dump', action='store_true')",
            "    ap.add_argument('--no-dump', action='store_true')\n"
            "    ap.add_argument('--charset', default=None,\n"
            "                    help='覆盖 tcslib.CHARSET (默认=盘上现役文件)')")
t=t.replace("    P('cap_verify_k2.py  ★ SKIP=2 成品核对: %s' % os.path.abspath(a.iso))",
            "    P('rb_verify_k2.py (cap_verify_k2.py 的 charset 可换副本)  ★ SKIP=2 成品核对: %s'\n"
            "      % os.path.abspath(a.iso))\n"
            "    if a.charset:\n"
            "        T.CHARSET = os.path.abspath(a.charset)\n"
            "        P('[cs ] ★ 本次校验用 charset = %s' % T.CHARSET)")
io.open(dst,'w',encoding='utf-8',newline='\n').write(t)
print('written',dst, len(t))
