# run_gsrunner.ps1 -- one gsrunner run for GR_CULPRIT (read-only on all inputs)
# usage: pwsh -File run_gsrunner.ps1 -RunName c01 -InputFile <in.txt> -ExtraArgs @('-grhook','0x5391BC') -MaxFrames 45
param(
  [Parameter(Mandatory=$true)][string]$RunName,
  [Parameter(Mandatory=$true)][string]$InputFile,
  [string[]]$ExtraArgs = @(),
  [int]$MaxFrames = 45,
  [string]$Iso = 'work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso'
)
$ErrorActionPreference = 'Stop'
$root = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
$cul  = Join-Path $root 'work\builds\GR_CULPRIT'
$run  = Join-Path $cul "runs\$RunName"
if (Test-Path $run) { Remove-Item $run -Recurse -Force }
New-Item -ItemType Directory -Force -Path $run | Out-Null

# exclusive use: never kill somebody else's emulator
$others = @(Get-Process -Name 'pcsx2*' -ErrorAction SilentlyContinue)
if ($others.Count -gt 0) {
  $ids = ($others | ForEach-Object { "$($_.Id):$($_.ProcessName)" }) -join ', '
  throw "another pcsx2 instance is running ($ids) -- refusing to start (exclusive-use rule)"
}

# fresh per-run copies of memcards + bios (all sources read-only)
Copy-Item (Join-Path $cul 'common\mc_pristine') (Join-Path $run 'mc') -Recurse -Force
Copy-Item (Join-Path $cul 'common\bios')        (Join-Path $run 'bios') -Recurse -Force

$exe = Join-Path $cul 'emu\gsrunner\pcsx2-gsrunner.exe'
$argv = @(
  '-grdumpdir', $run,
  '-grmaxframes', "$MaxFrames",
  '-grpcsample', '1'
) + $ExtraArgs + @(
  '-grinput',    $InputFile,
  '-grmemcards', (Join-Path $run 'mc'),
  '-grbios',     (Join-Path $run 'bios'),
  '-grbiosname', 'SCPH-90006_BIOS_VX_HK_2.20.bin',
  '-grstate',    (Join-Path $cul 'common\state_LAY_fix1_bytecount.p2s'),
  '-logfile',    (Join-Path $run 'emulog.txt'),
  '--',          (Join-Path $root $Iso)
)
$line = '"' + $exe + '" ' + (($argv | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' ')
Set-Content -Path (Join-Path $run 'cmdline.txt') -Value $line -Encoding UTF8
Write-Output "RUN $RunName : $line"

$sw = [System.Diagnostics.Stopwatch]::StartNew()
& $exe @argv 1> (Join-Path $run 'stdout.txt') 2> (Join-Path $run 'stderr.txt')
$code = $LASTEXITCODE
$sw.Stop()
Write-Output ("exit={0} elapsed={1:n1}s" -f $code, $sw.Elapsed.TotalSeconds)
Get-ChildItem $run | Where-Object { $_.Name -notin @('mc','bios') } |
  Sort-Object Length -Descending | Select-Object Length,Name | Format-Table -AutoSize | Out-String -Width 100
