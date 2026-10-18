# -*- coding: utf-8 -*-
r"""r72_fetch_tools2.py — 用 atom feed 抓插件的最新 tag + 资源直链 (比抓 HTML 稳)

用途: 补上 r72_fetch_tools.py 没抓到的
  · chaoticgd/ghidra-emotionengine-reloaded  (Ghidra 认 PS2 MIPS R5900/MMI 的插件)
  · starsong-consulting/GhydraMCP            (可选: MCP 桥; 我们改用 headless, 装不装都行)
"""
import io
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
OUT = os.path.join(REPO, 'work', 'tools', 'dl_urls2.txt')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
NS = {'a': 'http://www.w3.org/2005/Atom'}


def get(u):
    r = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(r, timeout=60).read()


def tags(repo):
    x = ET.fromstring(get('https://github.com/%s/releases.atom' % repo))
    return [e.find('a:id', NS).text.split('/')[-1] for e in x.findall('a:entry', NS)]


lines = []
for repo, key, pat in (
        ('chaoticgd/ghidra-emotionengine-reloaded', 'emotionengine', r'\.zip$'),
        ('starsong-consulting/GhydraMCP', 'ghydramcp', r'\.zip$'),
):
    print('== %s ==' % repo)
    try:
        ts = tags(repo)
        print('   tags: %s' % ts[:5])
    except Exception as e:
        print('   ✗ atom: %s' % e); continue
    for t in ts[:6]:
        try:
            h = get('https://github.com/%s/releases/expanded_assets/%s' % (repo, t)).decode('utf-8', 'replace')
        except Exception as e:
            print('   %s ✗ %s' % (t, e)); continue
        got = re.findall(r'href="(/%s/releases/download/[^"]+)"' % repo, h)
        zips = [z for z in got if re.search(pat, z)]
        print('   %s → %d 个 zip' % (t, len(zips)))
        for z in zips:
            print('      %s' % z)
            lines.append((key, t, 'https://github.com' + z))
        if zips:
            break

with io.open(OUT, 'w', encoding='utf-8') as f:
    for k, t, u in lines:
        f.write('%s\t%s\t%s\n' % (k, t, u))
print()
print('写出 %s (%d 条)' % (OUT, len(lines)))
