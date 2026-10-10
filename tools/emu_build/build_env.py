#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""build_env.py — 生成 MSVC 构建环境 (供 build_pcsx2.sh 使用)

背景 (round11 踩坑记录):
  cmake 在本环境有两个独立的坑:
  1) 通过 Python subprocess 调用 cmake.exe 时, 一旦设置 MSVC 环境变量就会
     0xC0000409 (stack buffer overrun) 崩在编译器检测阶段; 而从 git-bash 直接
     以 shell 形式调用同一个 cmake 则正常。=> 构建改由 build_pcsx2.sh 跑。
  2) 仓库路径含空格与括号 (当年目录名如此), 会让 cmake 传给 cmd 的
     try-compile 命令行错乱 (编译器被当成参数)。=> 用 ASCII junction
     C:\grbuild 指向仓库, 所有 cmake 调用走 junction 路径。
  3) cmake 4.0.3 在 -DCMAKE_CXX_FLAGS=/I"path" 这种带内嵌引号的参数上崩溃;
     且 vulkan 头目录未进 INCLUDE 会导致 D3D.cpp 编译失败。
  => vulkan 头目录直接加进 INCLUDE 环境变量, 不用 CMAKE_CXX_FLAGS。

用法: source <(python build_env.py)   # 打印 export 语句供 eval
   或: python build_env.py --print
"""
import os, sys

PBT = os.environ.get('MVC_ROOT')
if not PBT:
    sys.exit('[build_env] 需设置 MVC_ROOT 环境变量 (指向 MSVC 便携工具链根, 不内置本机路径)')   # 与 build_pcsx2.sh 的 MVC_ROOT 对齐
VC = PBT + r'\VC\Tools\MSVC\14.51.36231'
SDK = PBT + r'\Windows Kits\10'
VER = '10.0.28000.0'
JUNC_BS = 'C:' + '\\' + 'grbuild'          # C:\grbuild
JUNC_FS = 'C:/grbuild'                     # cmake 用正斜杠
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tools/emu_build → 仓库根

PATH_PARTS = [
    VC + r'\bin\Hostx64\x64',
    SDK + r'\bin' + '\\' + VER + r'\x64',
    SDK + r'\bin' + '\\' + VER + r'\x64\ucrt',
]
INC_PARTS = [
    VC + r'\include',
    SDK + r'\Include' + '\\' + VER + r'\ucrt',
    SDK + r'\Include' + '\\' + VER + r'\shared',
    SDK + r'\Include' + '\\' + VER + r'\um',
    SDK + r'\Include' + '\\' + VER + r'\winrt',
    SDK + r'\Include' + '\\' + VER + r'\cppwinrt',
    JUNC_BS + r'\third_party\emu\pcsx2_src\3rdparty\vulkan\include',
]
LIB_PARTS = [
    VC + r'\lib\x64',
    SDK + r'\Lib' + '\\' + VER + r'\ucrt\x64',
    SDK + r'\Lib' + '\\' + VER + r'\um\x64',
]

CM_ARGS = [
    '-G', 'Ninja',
    '-DCMAKE_PREFIX_PATH=' + JUNC_FS + '/third_party/deps',
    '-DCMAKE_BUILD_TYPE=Release',
    '-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
    '-DENABLE_QT_UI=OFF',
    '-DENABLE_GSRUNNER=ON',
    '-DENABLE_TESTS=OFF',
    '-DUSE_VULKAN=OFF',
    '-DUSE_OPENGL=ON',
    '-DDISABLE_ADVANCE_SIMD=ON',
    '-DBUNDLE_EMOJI_FONT=OFF',
    '-DLTO_PCSX2_CORE=OFF',
    '-DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF',
]

print('REPO=' + REPO)
print('JUNCTION=' + JUNC_BS)
print('SRC=' + JUNC_BS + r'\third_party\emu\pcsx2_src')
print('BLD=' + JUNC_BS + r'\third_party\emu\pcsx2')
print('PATH_PARTS=' + '|'.join(PATH_PARTS))
print('INC_PARTS=' + '|'.join(INC_PARTS))
print('LIB_PARTS=' + '|'.join(LIB_PARTS))
print('CM_ARGS=' + ' '.join("'%s'" % a for a in CM_ARGS))
