<#
.SYNOPSIS
    Builds the HookWatch-instrumented PCSX2 (Qt UI + gsrunner fallback) and refreshes
    the portable Qt directory.

.DESCRIPTION
    Rebuilds from the patched source snapshot in .\src (a copy of
    third_party\emu\pcsx2_src with the HookWatch patch applied), using:
      * MSVC 14.51 (portable toolchain, via setup_x64.bat)
      * Ninja
      * Qt 6.10.3 MSVC x64  (downloaded with aqt into .\deps)
      * KDDockWidgets 2.4.1 (built into .\deps\kddock)
      * the project's existing dependency prefix  third_party\deps

    Outputs:
      .\build\pcsx2-qt\pcsx2-qt.exe
      .\build\pcsx2-gsrunner\pcsx2-gsrunner.exe
      .\qt\                               portable pcsx2-qt (exe + Qt + DLLs + hook\)
      .\build\pcsx2-gsrunner\resources\   copied so the console runner can boot

.EXAMPLE
    pwsh -File .\build_hooked_emu.ps1
    pwsh -File .\build_hooked_emu.ps1 -Reconfigure -Jobs 12
#>
param(
    [switch]$Reconfigure,
    [switch]$SkipBuild,
    [int]$Jobs = 10,
    [string]$MsvcSetup = 'C:\Users\84363\pbt\msvc\setup_x64.bat'
)

$ErrorActionPreference = 'Stop'

$here = $PSScriptRoot
$root = (Resolve-Path (Join-Path $here '..\..\..')).Path
$src  = Join-Path $here 'src'
$bld  = Join-Path $here 'build'
$qt   = Join-Path $here 'deps\6.10.3\msvc2022_64'
$kdd  = Join-Path $here 'deps\kddock'
$deps = Join-Path $root 'third_party\deps'
$out  = Join-Path $here 'qt'

function Assert-Path([string]$path, [string]$what)
{
    if (-not (Test-Path -LiteralPath $path)) { throw "$what not found: $path" }
}

Assert-Path $src  'Patched source tree (src)'
Assert-Path $qt   'Qt prefix (deps\6.10.3\msvc2022_64)'
Assert-Path $kdd  'KDDockWidgets prefix (deps\kddock)'
Assert-Path $deps 'Project dependency prefix (third_party\deps)'
Assert-Path $MsvcSetup 'MSVC setup script'

function Invoke-Dev([string]$command)
{
    Write-Host ">> $command" -ForegroundColor DarkGray
    cmd /c "call `"$MsvcSetup`" >nul 2>&1 && $command"
    if ($LASTEXITCODE -ne 0) { throw "command failed (exit $LASTEXITCODE): $command" }
}

$needConfigure = $Reconfigure -or -not (Test-Path -LiteralPath (Join-Path $bld 'CMakeCache.txt'))
if ($needConfigure)
{
    Write-Host '== configure ==' -ForegroundColor Cyan
    $prefix = "$qt;$kdd;$deps"
    Invoke-Dev "cmake -S `"$src`" -B `"$bld`" -G Ninja -DCMAKE_BUILD_TYPE=Release `"-DCMAKE_PREFIX_PATH=$prefix`" -DENABLE_QT_UI=ON -DENABLE_GSRUNNER=ON -DENABLE_TESTS=OFF -DUSE_VULKAN=OFF -DUSE_OPENGL=ON -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF"
}

if (-not $SkipBuild)
{
    Write-Host '== build (pcsx2-qt + pcsx2-gsrunner) ==' -ForegroundColor Cyan
    Invoke-Dev "ninja -C `"$bld`" pcsx2-qt pcsx2-gsrunner -j $Jobs"
}

$qtExe = Join-Path $bld 'pcsx2-qt\pcsx2-qt.exe'
$gsExe = Join-Path $bld 'pcsx2-gsrunner\pcsx2-gsrunner.exe'
Assert-Path $qtExe 'Built pcsx2-qt.exe'
Assert-Path $gsExe 'Built pcsx2-gsrunner.exe'

# gsrunner requires <exe dir>\resources to boot (EmuFolders::SetResourcesDirectory).
$gsRes = Join-Path $bld 'pcsx2-gsrunner\resources'
if (-not (Test-Path -LiteralPath $gsRes))
{
    Write-Host '== copy resources for gsrunner ==' -ForegroundColor Cyan
    Copy-Item -LiteralPath (Join-Path $src 'bin\resources') -Destination $gsRes -Recurse -Force
}

Write-Host '== deploy portable Qt directory ==' -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $out | Out-Null
Copy-Item -LiteralPath $qtExe -Destination (Join-Path $out 'pcsx2-qt.exe') -Force
Copy-Item -LiteralPath (Join-Path $kdd 'bin\kddockwidgets-qt62.dll') -Destination $out -Force
Copy-Item -Path (Join-Path $deps 'bin\*.dll') -Destination $out -Force

$d3d12 = Join-Path $deps 'bin\D3D12'
if (Test-Path -LiteralPath $d3d12)
{
    Copy-Item -LiteralPath $d3d12 -Destination $out -Recurse -Force
}

$hookOut = Join-Path $out 'hook'
if (Test-Path -LiteralPath $hookOut)
{
    Remove-Item -LiteralPath $hookOut -Recurse -Force
}
Copy-Item -LiteralPath (Join-Path $here 'hook') -Destination $out -Recurse -Force

$windeployqt = Join-Path $qt 'bin\windeployqt.exe'
Assert-Path $windeployqt 'windeployqt.exe'
& $windeployqt --release --no-opengl-sw --no-system-d3d-compiler --no-translations --dir $out (Join-Path $out 'pcsx2-qt.exe') | Out-Null
if ($LASTEXITCODE -ne 0) { throw "windeployqt failed (exit $LASTEXITCODE)" }

Write-Host ''
Write-Host 'Build + deploy finished.' -ForegroundColor Green
Write-Host "  Qt frontend : $(Join-Path $out 'pcsx2-qt.exe')"
Write-Host "  gsrunner    : $gsExe"
Write-Host ''
Write-Host 'Run with hooks:'
Write-Host "  cd `"$out`""
Write-Host '  .\pcsx2-qt.exe -hook'
Write-Host '  (or: .\pcsx2-qt.exe -hookconfig .\hook\hook_config.ini)'
