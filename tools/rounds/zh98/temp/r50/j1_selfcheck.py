import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib
cs = tcslib.Charset()
ok, lines = tcslib.selfcheck_charset(cs)
print('selfcheck_charset ok =', ok)
for L in lines:
    print('  ', L)
