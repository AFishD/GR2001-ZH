# spinfix_run.ps1 -- 【GR_SPINFIX】一次 gsrunner 运行（独占；永不杀别人的实例）
# usage:
#   pwsh -File spinfix_run.ps1 -RunName r01 -Iso <iso> -MaxFrames 130 `
#        [-State <p2s>] [-InputFile <txt>] [-ExtraArgs @('-grhook','0x1024A8')]
param(
  [Parameter(Mandatory=$true)][string]$RunName,
  [Parameter(Mandatory=$true)][string]$Iso,
  [string]$State = '',
  [string]$InputFile = 'work\builds\GR_SPINFIX\inputs\in_l1_f30.txt',
  [int]$MaxFrames = 130,
  [string[]]$ExtraArgs = @(),
  [string]$Extra = '',
  [switch]$KeepRun
)
if ($Extra -ne '') { $ExtraArgs = @($Extra -split '\s+' | Where-Object { $_ -ne '' }) }
$ErrorActionPreference = 'Stop'
$root = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
$sf   = Join-Path $root 'work\builds\GR_SPINFIX'
$run  = Join-Path $sf "runs\$RunName"
if (Test-Path $run) { Remove-Item $run -Recurse -Force }
New-Item -ItemType Directory -Force -Path $run | Out-Null

# 独占检查：有别人的 pcsx2 就拒绝（只等不杀）
$others = @(Get-Process -Name 'pcsx2*' -ErrorAction SilentlyContinue)
if ($others.Count -gt 0) {
  $ids = ($others | ForEach-Object { "$($_.Id):$($_.ProcessName)" }) | Sort-Object
  Write-Output ("[WARN] 检测到其它 pcsx2 实例（只记录，不杀）：{0}" -f ($ids -join ', '))
  Set-Content -Path (Join-Path $run 'OTHERS_RUNNING.txt') -Value ($ids -join "`n") -Encoding UTF8
}
Copy-Item (Join-Path $sf 'common\mc_pristine') (Join-Path $run 'mc') -Recurse -Force
Copy-Item (Join-Path $sf 'common\bios')        (Join-Path $run 'bios') -Recurse -Force

$exe = Join-Path $sf 'emu\gsrunner\pcsx2-gsrunner.exe'
$argv = @('-grdumpdir', $run, '-grmaxframes', "$MaxFrames")
if ($State -ne '') { $argv += @('-grstate', (Join-Path $root $State)) }
if ($InputFile -ne '') { $argv += @('-grinput', (Join-Path $root $InputFile)) }
$argv += $ExtraArgs
$argv += @('-grmemcards', (Join-Path $run 'mc'),
           '-grbios',     (Join-Path $run 'bios'),
           '-grbiosname', 'SCPH-90006_BIOS_VX_HK_2.20.bin',
           '-logfile',    (Join-Path $run 'emulog.txt'),
           '--',          (Join-Path $root $Iso))
$line = '"' + $exe + '" ' + (($argv | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' ')
Set-Content -Path (Join-Path $run 'cmdline.txt') -Value $line -Encoding UTF8
Write-Output "RUN $RunName : $line"

$sw = [System.Diagnostics.Stopwatch]::StartNew()
& $exe @argv 1> (Join-Path $run 'stdout.txt') 2> (Join-Path $run 'stderr.txt')
$code = $LASTEXITCODE
$sw.Stop()
Write-Output ("exit={0} elapsed={1:n1}s" -f $code, $sw.Elapsed.TotalSeconds)
Get-ChildItem $run -File | Sort-Object Length -Descending |
  ForEach-Object { "{0,12}  {1}" -f $_.Length, $_.Name }
