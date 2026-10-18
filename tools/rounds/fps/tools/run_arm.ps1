# run_arm.ps1 -- run ONE gsrunner arm of the GR_FPS A/B.
#
# 纪律 (任务书):
#   * 模拟器一次只跑一个实例 -> 跑前/跑后都查 *pcsx2* 进程, 有残留就拒绝起跑
#   * 日志被独占 -> 只在进程退出后才读 emulog/grlog
#   * exit=0 不算证据 -> 记录 frames / elapsed / TLB / Trap, 以数字为准
#   * 只写 work/builds/GR_FPS/**
#
# 用法:
#   pwsh -File work\builds\GR_FPS\tools\run_arm.ps1 -Arm zh113b -Iso <iso> [-Frames 34000] [-Snap 60] [-Nav nav_play.txt] [-Tag probe]
param(
    [Parameter(Mandatory = $true)][string]$Arm,
    [Parameter(Mandatory = $true)][string]$Iso,
    [int]$Frames = 34000,
    [int]$Snap = 60,
    [string]$Nav = 'nav_play.txt',
    [string]$Tag = ''
)

$ErrorActionPreference = 'Stop'
$repo = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
$gs = Join-Path $repo 'third_party\emu\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe'
$mcTpl = Join-Path $repo 'third_party\emu\run\memcards'
$root = Join-Path $repo 'work\builds\GR_FPS\out'
$navPath = Join-Path $repo ("work\builds\GR_FPS\tools\$Nav")

if (-not (Test-Path $Iso)) { throw "ISO 不存在: $Iso" }
if (-not (Test-Path $gs)) { throw "gsrunner 不存在: $gs" }
if (-not (Test-Path $navPath)) { throw "nav 不存在: $navPath" }

$name = if ($Tag) { "$Arm`_$Tag" } else { $Arm }
$out = Join-Path $root $name
if (Test-Path $out) { Remove-Item -Recurse -Force $out }
New-Item -ItemType Directory -Force -Path $out | Out-Null

# ---- 每次都用全新的记忆卡副本 (与 run_opt.py 同一纪律: 卡上剩余空间会改变 BIOS 引导耗时)
$mc = Join-Path $out 'mc'
New-Item -ItemType Directory -Force -Path $mc | Out-Null
foreach ($f in 'Mcd001.ps2', 'Mcd002.ps2') {
    Copy-Item (Join-Path $mcTpl $f) (Join-Path $mc $f) -Force
}

# ---- 跑前进程检查
$pre = @(Get-Process | Where-Object { $_.ProcessName -like '*pcsx2*' })
if ($pre.Count -gt 0) {
    $pre | ForEach-Object { Write-Output "PRE-RESIDUAL PID=$($_.Id) $($_.ProcessName)" }
    throw "有 $($pre.Count) 个残留 pcsx2 进程 -> 拒绝起跑 (严禁并发)"
}

$argList = @(
    '-grdumpdir', $out,
    '-grmaxframes', "$Frames",
    '-grsnap', "$Snap",
    '-grinput', $navPath,
    '-grmemcards', $mc,
    '-logfile', (Join-Path $out 'emulog.txt'),
    '--', $Iso
)
$cmdline = '"' + $gs + '" ' + (($argList | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' ')

$runTxt = Join-Path $out 'RUN.txt'
$t0 = Get-Date
$sw = [System.Diagnostics.Stopwatch]::StartNew()
& $gs @argList *> (Join-Path $out 'stdout.txt')
$code = $LASTEXITCODE
$sw.Stop()
$t1 = Get-Date

# ---- 跑后进程检查
$post = @(Get-Process | Where-Object { $_.ProcessName -like '*pcsx2*' })
$postStr = if ($post.Count -eq 0) { 'none' } else { ($post | ForEach-Object { "PID=$($_.Id)" }) -join ',' }

$lines = @(
    "arm = $name",
    "iso = $Iso",
    "nav = $navPath",
    "maxframes = $Frames",
    "snap = $Snap",
    "cmd = $cmdline",
    "start = $($t0.ToString('yyyy-MM-dd HH:mm:ss.fff'))",
    "end   = $($t1.ToString('yyyy-MM-dd HH:mm:ss.fff'))",
    "exit = $code",
    "elapsed_s = $([math]::Round($sw.Elapsed.TotalSeconds,1))",
    "post_procs = $postStr"
)
Set-Content -Path $runTxt -Value $lines -Encoding UTF8

$lines | ForEach-Object { Write-Output $_ }
