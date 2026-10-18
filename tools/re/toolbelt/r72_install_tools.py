# -*- coding: utf-8 -*-
r"""r72_install_tools.py — 在工作区内安装 Ghidra 逆向工具链（全部落在 work/tools/）

步骤:
  1) 解压已下载的 JDK 21  → work/tools/jdk/
  2) 解析 Ghidra **12.1.2** 的资源直链（atom feed）→ 下载 → 解压 → work/tools/ghidra/
  3) 下载 EmotionEngine Reloaded 插件（与 12.1.2 匹配的构建）→ 放进 ghidra/Extensions/Ghidra/
  4) 可选: GhydraMCP 的 ghidra12.1.2 构建
  5) 用 analyzeHeadless 验证（列版本 + 尝试分析）
一切路径都在工作区内；不做任何系统级安装、不改 PATH、不动注册表。
"""
import io
import os
import re
import subprocess
import sys
import urllib.request
import zipfile
import xml.etree.ElementTree as ET

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
TOOLS = os.path.join(REPO, 'work', 'tools')
DL = os.path.join(TOOLS, 'dl')
GHIDRA_VER = '12.1.2'
NS = {'a': 'http://www.w3.org/2005/Atom'}
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.makedirs(DL, exist_ok=True)


def get(u, timeout=90):
    r = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(r, timeout=timeout).read()


def fetch(u, dst):
    if os.path.isfile(dst) and os.path.getsize(dst) > 1000:
        print('   已有 %s (%.1f MB)' % (os.path.basename(dst), os.path.getsize(dst) / 1e6))
        return dst
    print('   下载 %s …' % os.path.basename(dst))
    data = get(u, timeout=900)
    with open(dst, 'wb') as f:
        f.write(data)
    print('   → %.1f MB' % (len(data) / 1e6))
    return dst


# ---------- 1) JDK ----------
print('=== 1) JDK ===')
jdkzip = os.path.join(DL, 'jdk21.zip')
jdkdir = os.path.join(TOOLS, 'jdk')
if not os.path.isdir(jdkdir):
    os.makedirs(jdkdir, exist_ok=True)
    print('   解压 %s …' % jdkzip)
    with zipfile.ZipFile(jdkzip) as z:
        z.extractall(jdkdir)
    # 顶层通常是 jdk-21.x.y+z/ ⇒ 拍平
    subs = [d for d in os.listdir(jdkdir) if os.path.isdir(os.path.join(jdkdir, d))]
    if len(subs) == 1:
        inner = os.path.join(jdkdir, subs[0])
        for it in os.listdir(inner):
            os.rename(os.path.join(inner, it), os.path.join(jdkdir, it))
        os.rmdir(inner)
java = os.path.join(jdkdir, 'bin', 'java.exe')
print('   java: %s  %s' % (java, '✓' if os.path.isfile(java) else '✗'))
if os.path.isfile(java):
    print('   ' + subprocess.run([java, '-version'], capture_output=True, text=True).stderr.strip().replace('\n', ' | '))

# ---------- 2) Ghidra ----------
print('=== 2) Ghidra %s ===' % GHIDRA_VER)
url_file = os.path.join(TOOLS, 'ghidra_url.txt')
if os.path.isfile(url_file) and GHIDRA_VER in io.open(url_file, encoding='utf-8').read():
    gurl = io.open(url_file, encoding='utf-8').read().strip()
else:
    x = ET.fromstring(get('https://github.com/NationalSecurityAgency/ghidra/releases.atom'))
    tags = [e.find('a:id', NS).text.split('/')[-1] for e in x.findall('a:entry', NS)]
    print('   可用 tag: %s' % tags[:8])
    gurl = None
    for t in tags:
        if GHIDRA_VER not in t:
            continue
        h = get('https://github.com/NationalSecurityAgency/ghidra/releases/expanded_assets/' + t).decode('utf-8', 'replace')
        z = re.findall(r'href="(/NationalSecurityAgency/ghidra/releases/download/[^"]+\.zip)"', h)
        if z:
            gurl = 'https://github.com' + z[0]
            break
if not gurl:
    print('   ✗ 找不到 Ghidra %s 的 zip' % GHIDRA_VER)
    sys.exit(2)
print('   URL: %s' % gurl)
gzip_path = os.path.join(DL, 'ghidra_%s.zip' % GHIDRA_VER)
gsrc = None
if os.path.isfile(gzip_path) and os.path.getsize(gzip_path) > 10 ** 8:
    gsrc = gzip_path
    print('   已有 %s (%.1f MB)' % (os.path.basename(gzip_path), os.path.getsize(gzip_path) / 1e6))
else:
    print('   下载中（约 400 MB，耐心等）…')
    data = get(gurl, timeout=1800)
    with open(gzip_path, 'wb') as f:
        f.write(data)
    gsrc = gzip_path
    print('   → %.1f MB' % (len(data) / 1e6))

ghidra_dir = os.path.join(TOOLS, 'ghidra')
if not os.path.isfile(os.path.join(ghidra_dir, 'support', 'analyzeHeadless.bat')):
    print('   解压到 %s …' % ghidra_dir)
    with zipfile.ZipFile(gsrc) as z:
        z.extractall(TOOLS)
    subs = [d for d in os.listdir(TOOLS) if d.startswith('ghidra_') and os.path.isdir(os.path.join(TOOLS, d))]
    if subs:
        os.rename(os.path.join(TOOLS, subs[0]), ghidra_dir)
print('   analyzeHeadless: %s' % ('✓' if os.path.isfile(os.path.join(ghidra_dir, 'support', 'analyzeHeadless.bat')) else '✗'))

# ---------- 3) EmotionEngine 插件 ----------
print('=== 3) EmotionEngine Reloaded 插件 (匹配 %s) ===' % GHIDRA_VER)
ext_dir = os.path.join(ghidra_dir, 'Extensions', 'Ghidra')
os.makedirs(ext_dir, exist_ok=True)
try:
    x = ET.fromstring(get('https://github.com/chaoticgd/ghidra-emotionengine-reloaded/releases.atom'))
    for e in x.findall('a:entry', NS):
        tag = e.find('a:id', NS).text.split('/')[-1]
        h = get('https://github.com/chaoticgd/ghidra-emotionengine-reloaded/releases/expanded_assets/' + tag).decode('utf-8', 'replace')
        zs = re.findall(r'href="(/chaoticgd/ghidra-emotionengine-reloaded/releases/download/[^"]+\.zip)"', h)
        hit = [z for z in zs if ('ghidra_%s_' % GHIDRA_VER) in z]
        if hit:
            dst = os.path.join(ext_dir, os.path.basename(hit[0]))
            fetch('https://github.com' + hit[0], dst)
            print('   ✓ 装入 %s (tag %s)' % (os.path.basename(dst), tag))
            break
    else:
        print('   ✗ 没找到匹配 %s 的插件构建；可用: %s' % (GHIDRA_VER, zs[:3]))
except Exception as ex:
    print('   ✗ %s' % ex)

# ---------- 4) GhydraMCP (可选) ----------
print('=== 4) GhydraMCP (可选, 我们主要用 headless) ===')
try:
    x = ET.fromstring(get('https://github.com/starsong-consulting/GhydraMCP/releases.atom'))
    for e in x.findall('a:entry', NS):
        tag = e.find('a:id', NS).text.split('/')[-1]
        h = get('https://github.com/starsong-consulting/GhydraMCP/releases/expanded_assets/' + tag).decode('utf-8', 'replace')
        zs = re.findall(r'href="(/starsong-consulting/GhydraMCP/releases/download/[^"]+\.zip)"', h)
        hit = [z for z in zs if ('ghidra%s' % GHIDRA_VER) in z]
        if hit:
            dst = os.path.join(ext_dir, os.path.basename(hit[0]))
            fetch('https://github.com' + hit[0], dst)
            print('   ✓ 装入 %s' % os.path.basename(dst))
            break
    else:
        print('   跳过（无 %s 匹配构建）' % GHIDRA_VER)
except Exception as ex:
    print('   ✗ %s' % ex)

print()
print('=== 5) 验收 ===')
al = os.path.join(ghidra_dir, 'support', 'analyzeHeadless.bat')
if os.path.isfile(al):
    r = subprocess.run(['cmd', '/c', al, '-help'], capture_output=True, text=True, timeout=300)
    out = (r.stdout or '') + (r.stderr or '')
    print('   analyzeHeadless 退出码 = %d' % r.returncode)
    print('   ' + '\n   '.join(out.splitlines()[:6]))
print()
print('结论: Ghidra = %s ; JDK = %s ; 插件 = %s' % (
    '✓' if os.path.isfile(al) else '✗',
    '✓' if os.path.isfile(java) else '✗',
    ', '.join(os.listdir(ext_dir)) if os.path.isdir(ext_dir) else '✗'))
