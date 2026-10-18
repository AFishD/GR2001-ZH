# -*- coding: utf-8 -*-
r"""r72_fetch_tools.py — 抓 Ghidra / EmotionEngine 插件的下载直链 (绕开被限流的 GitHub API)

输出: work/tools/dl_urls.txt  (每行: 名称<TAB>URL)
"""
import io
import os
import re
import sys
import urllib.request

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
OUT = os.path.join(REPO, 'work', 'tools', 'dl_urls.txt')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def page(u):
    r = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(r, timeout=60).read().decode('utf-8', 'replace')


lines = []

# ---- Ghidra 11.4.2 (skill README 指定的 tag) ----
tag = 'Ghidra_11.4.2_build'
try:
    h = page('https://github.com/NationalSecurityAgency/ghidra/releases/expanded_assets/' + tag)
    zips = re.findall(r'href="(/NationalSecurityAgency/ghidra/releases/download/[^"]+\.zip)"', h)
    print('Ghidra %s:' % tag)
    for z in zips:
        print('   %s' % z)
        if z.endswith('.zip'):
            lines.append(('ghidra', 'https://github.com' + z))
except Exception as e:
    print('Ghidra ✗ %s' % e)

# ---- chaoti cgd / ghidra-emotionengine-reloaded 最新版 ----
try:
    base = 'https://github.com/chaoticgd/ghidra-emotionengine-reloaded/releases'
    h = page(base + '/latest')
    m = re.search(r'/releases/tag/([^"]+)"', h)
    latest = m.group(1) if m else None
    print('EmotionEngine latest tag: %s' % latest)
    if latest:
        h2 = page(base + '/expanded_assets/' + latest)
        got = re.findall(r'href="(/chaoticgd/ghidra-emotionengine-reloaded/releases/download/[^"]+)"', h2)
        for z in got:
            print('   %s' % z)
            if z.endswith('.zip'):
                lines.append(('emotionengine', 'https://github.com' + z))
except Exception as e:
    print('EmotionEngine ✗ %s' % e)

# ---- GhydraMCP (可选; skill 自带的安装器也指向它) ----
try:
    base = 'https://github.com/starsong-consulting/GhydraMCP/releases'
    h = page(base + '/latest')
    m = re.search(r'/releases/tag/([^"]+)"', h)
    latest = m.group(1) if m else None
    print('GhydraMCP latest tag: %s' % latest)
    if latest:
        h2 = page(base + '/expanded_assets/' + latest)
        got = re.findall(r'href="(/starsong-consulting/GhydraMCP/releases/download/[^"]+)"', h2)
        for z in got[:6]:
            print('   %s' % z)
            if z.endswith('.zip'):
                lines.append(('ghydramcp', 'https://github.com' + z))
except Exception as e:
    print('GhydraMCP ✗ %s' % e)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with io.open(OUT, 'w', encoding='utf-8') as f:
    for k, u in lines:
        f.write('%s\t%s\n' % (k, u))
print()
print('写出 %s (%d 条)' % (OUT, len(lines)))
