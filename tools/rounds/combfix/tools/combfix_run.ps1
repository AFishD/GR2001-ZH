# combfix_run.ps1 -- GR_COMBFIX single gsrunner run (exclusive; never kills other instances)
# usage:
#   powershell -File combfix_run.ps1 -RunName r01 -Iso <iso> -MaxFrames 300 `
#        [-State <p2s>] [-InputFile <txt>] [-Extra "-grhook 0x1021D4"]
param(
  [Parameter(Mandatory=$true)][string]$RunName,
  [Parameter(Mandatory=$true)][string]$Iso,
  [string]$State = '',
  [string]$InputFile = 'work\builds\GR_SPINFIX\inputs\in_l1_f30.txt',
  [int]$MaxFrames = 300,
  [string[]]$ExtraArgs = @(),
  [string]$Extra = ''
)
if ($Extra -ne '') { $ExtraArgs = @($Extra -split '\s+' | Where-Object { $_ -ne '' }) }
$ErrorActionPreference = 'Stop'
$root = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
$cf   = Join-Path $root 'work\builds\GR_COMBFIX'
$run  = Join-Path $cf "runs\$RunName"
if (Test-Path $run) { Remove-Item $run -Recurse -Force }
New-Item -ItemType Directory -Force -Path $run | Out-Null

$others = @(Get-Process -Name 'pcsx2*' -ErrorAction SilentlyContinue)
if ($others.Count -gt 0) {
  $ids = ($others | ForEach-Object { "$($_.Id):$($_.ProcessName)" }) | Sort-Object
  Write-Output ("[WARN] other pcsx2 instance running (record only, never kill): " + ($ids -join ', '))
  Set-Content -Path (Join-Path $run 'OTHERS_RUNNING.txt') -Value ($ids -join "`n") -Encoding UTF8
}
$sf = Join-Path $root 'work\builds\GR_SPINFIX'
Copy-Item (Join-Path $sf 'common\mc_pristine') (Join-Path $run 'mc') -Recurse -Force
Copy-Item (Join-Path $sf 'common\bios')        (Join-Path $run 'bios') -Recurse -Force

function Resolve-Arg([string]$p) {
  if ($p -eq '') { return '' }
  if ([System.IO.Path]::IsPathRooted($p)) { return $p }
  return (Join-Path $root $p)
}
$exe = Join-Path $cf 'emu\gsrunner\pcsx2-gsrunner.exe'
$argv = @('-grdumpdir', $run, '-grmaxframes', "$MaxFrames")
if ($State -ne '') { $argv += @('-grstate', (Resolve-Arg $State)) }
if ($InputFile -ne '') { $argv += @('-grinput', (Resolve-Arg $InputFile)) }
$argv += $ExtraArgs
$argv += @('-grmemcards', (Join-Path $run 'mc'),
           '-grbios',     (Join-Path $run 'bios'),
           '-grbiosname', 'SCPH-90006_BIOS_VX_HK_2.20.bin',
           '-logfile',    (Join-Path $run 'emulog.txt'),
           '--',          (Resolve-Arg $Iso))
$line = '"' + $exe + '" ' + (($argv | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' ')
Set-Content -Path (Join-Path $run 'cmdline.txt') -Value $line -Encoding UTF8
Write-Output ("RUN " + $RunName + " : " + $line)

$sw = [System.Diagnostics.Stopwatch]::StartNew()
& $exe @argv 1> (Join-Path $run 'stdout.txt') 2> (Join-Path $run 'stderr.txt')
$code = $LASTEXITCODE
$sw.Stop()
Write-Output ("exit=" + $code + " elapsed=" + [math]::Round($sw.Elapsed.TotalSeconds,1) + "s")
Get-ChildItem $run -File | Sort-Object Length -Descending |
  ForEach-Object { "{0,12}  {1}" -f $_.Length, $_.Name }
