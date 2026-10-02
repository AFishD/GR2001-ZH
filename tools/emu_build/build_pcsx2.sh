#!/usr/bin/env bash
# build_pcsx2.sh — 重建仪表化 gsrunner (round11 定版配方)
#
# 为什么是 shell 而不是 python: 见 build_env.py 头注释 —— Python subprocess 调用
# cmake + MSVC 环境会 0xC0000409 崩溃, git-bash 直接调用正常。
#
# 前置: ASCII junction C:\grbuild -> 仓库 (路径含空格/括号会破坏 cmake 的
#       try-compile 命令行)。自动创建。
# 用法: bash tools/emu_build/build_pcsx2.sh [--configure] [--purge]
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
JUNC='C:\grbuild'
JUNC_FS='C:/grbuild'

# --- junction 保障 ---
if [ ! -d "/c/grbuild/third_party/emu/pcsx2_src" ]; then
  echo "[junc] 创建 $JUNC -> $REPO"
  cmd //c "if exist C:\\grbuild rmdir C:\\grbuild" >/dev/null 2>&1 || true
  python -c "
import subprocess,sys
r=subprocess.run(['cmd','/c','mklink','/J',r'C:\\grbuild',sys.argv[1]],
                 capture_output=True,text=True,errors='replace')
print('  mklink rc=',r.returncode)
sys.exit(0 if r.returncode==0 else 1)
" "$REPO" || { echo "!! junction 创建失败 (需管理员?)"; exit 1; }
fi
[ -d "/c/grbuild/third_party/emu/pcsx2_src" ] || { echo "!! junction 不可用"; exit 1; }

# --- MSVC + SDK 环境 ---
M="${MVC_ROOT:?需设置 MVC_ROOT 环境变量, 指向 MSVC 便携工具链根 (含 VC/Tools/MSVC 与 Windows Kits/10)}"   # MSVC 便携工具链 (必填, 不内置本机路径)
VC="$M\\VC\\Tools\\MSVC\\14.51.36231"
SDK="$M\\Windows Kits\\10"
VER='10.0.28000.0'
M_POSIX="$(cygpath -u "$M")"               # git-bash 的 PATH 用 POSIX 形式
export PATH="$M_POSIX/VC/Tools/MSVC/14.51.36231/bin/Hostx64/x64:$M_POSIX/Windows Kits/10/bin/$VER/x64:$M_POSIX/Windows Kits/10/bin/$VER/x64/ucrt:$PATH"
export INCLUDE="$VC\\include;$SDK\\Include\\$VER\\ucrt;$SDK\\Include\\$VER\\shared;$SDK\\Include\\$VER\\um;$SDK\\Include\\$VER\\winrt;$SDK\\Include\\$VER\\cppwinrt;C:\\grbuild\\third_party\\emu\\pcsx2_src\\3rdparty\\vulkan\\include"
export LIB="$VC\\lib\\x64;$SDK\\Lib\\$VER\\ucrt\\x64;$SDK\\Lib\\$VER\\um\\x64"

command -v cl >/dev/null || { echo "!! cl.exe 不在 PATH"; exit 1; }

# --- configure ---
if [ "${1:-}" = "--purge" ] || [ "${1:-}" = "--configure" ] \
   || [ ! -f "/c/grbuild/third_party/emu/pcsx2/build.ninja" ]; then
  echo "[cmake] configure ..."
  cmake -S "$JUNC_FS/third_party/emu/pcsx2_src" -B "$JUNC_FS/third_party/emu/pcsx2" \
    -G Ninja -DCMAKE_PREFIX_PATH="$JUNC_FS/third_party/deps" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    -DENABLE_QT_UI=OFF -DENABLE_GSRUNNER=ON -DENABLE_TESTS=OFF \
    -DUSE_VULKAN=OFF -DUSE_OPENGL=ON -DDISABLE_ADVANCE_SIMD=ON \
    -DBUNDLE_EMOJI_FONT=OFF -DLTO_PCSX2_CORE=OFF \
    -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF
fi

echo "[ninja] build pcsx2-gsrunner ..."
ninja -C "$JUNC_FS/third_party/emu/pcsx2" pcsx2-gsrunner

# --- 部署: gsrunner 运行需要 exe 同目录有 resources/ 与依赖 DLL ---
GSDIR="/c/grbuild/third_party/emu/pcsx2/pcsx2-gsrunner"
if [ ! -d "$GSDIR/resources" ]; then
  echo "[deploy] 复制 resources/ (EmuFolders::SetResourcesDirectory 必需, 否则静默 exit)"
  cp -r "/c/grbuild/third_party/emu/pcsx2_src/bin/resources" "$GSDIR/resources"
fi
echo "[deploy] 复制依赖 DLL"
cp -f /c/grbuild/third_party/deps/bin/*.dll "$GSDIR/" 2>/dev/null || true

echo "[done] $JUNC\\third_party\\emu\\pcsx2\\pcsx2-gsrunner\\pcsx2-gsrunner.exe"
ls -la "$GSDIR/pcsx2-gsrunner.exe"
echo "[提示] cmake --install 会因 updater 目标缺失而失败, 故手动部署上述两项。"
