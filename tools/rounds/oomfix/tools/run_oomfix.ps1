# run_oomfix.ps1 -- one gsrunner run for GR_OOMFIX (read-only on every input ISO/state)
# usage:
#   pwsh -File run_oomfix.ps1 -RunName u1_base_l1 -Iso <iso> -State <p2s> -InputFile <txt> `
#        -MaxFrames 130 -ExtraArgs @('-grdumpwin','43','46')
param(
  [Parameter(Mandatory=$true)][string]$RunName,
  [Parameter(Mandatory=$true)][string]$Iso,
  [string]$State = 'work\builds\GR_OOMFIX\common\state_LAY_fix1_bytecount.p2s',
  [string]$InputFile = 'work\builds\GR_OOMFIX\inputs\in_l1_f30.txt',
  [int]$MaxFrames = 130,
  [string[]]$ExtraArgs = @()
)
$ErrorActionPreference = 'Stop'
$root = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
$oom  = Join-Path $root 'work\builds\GR_OOMFIX'
$run  = Join-Path $oom "runs\$RunName"
if (Test-Path $run) { Remove-Item $run -Recurse -Force }
New-Item -ItemType Directory -Force -Path $run | Out-Null

# exclusive use: never kill somebody else's emulator
$others = @(Get-Process -Name 'pcsx2*' -ErrorAction SilentlyContinue)
if ($others.Count -gt 0) {
  $ids = ($others | ForEach-Object { "$($_.Id):$($_.ProcessName)" }) -join ', '
  throw "another pcsx2 instance is running ($ids) -- refusing to start (exclusive-use rule)"
}

Copy-Item (Join-Path $oom 'common\mc_pristine') (Join-Path $run 'mc') -Recurse -Force
Copy-Item (Join-Path $oom 'common\bios')        (Join-Path $run 'bios') -Recurse -Force

$exe = Join-Path $oom 'emu\gsrunner\pcsx2-gsrunner.exe'
$argv = @(
  '-grdumpdir', $run,
  '-grmaxframes', "$MaxFrames",
  '-grpcsample', '1'
) + $ExtraArgs + @(
  '-grinput',    (Join-Path $root $InputFile),
  '-grmemcards', (Join-Path $run 'mc'),
  '-grbios',     (Join-Path $run 'bios'),
  '-grbiosname', 'SCPH-90006_BIOS_VX_HK_2.20.bin',
  '-grstate',    (Join-Path $root $State),
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
Get-ChildItem $run -File | Where-Object { $_.Length -gt 0 } |
  Sort-Object Length -Descending | ForEach-Object { "{0,12}  {1}" -f $_.Length, $_.Name }
