# smoke_oomfix.ps1 -- 6000 帧冷启动冒烟（4 张盘，串行；模拟器独占）
# 判据：>=190 截图 / TLB 0 / Trap 0 / 与基底逐帧 sha256 对照
$ErrorActionPreference = 'Stop'
$root = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
$oom  = Join-Path $root 'work\builds\GR_OOMFIX'
$nav  = Join-Path $root 'tools\capture\nav_menu_only.txt'
$exe  = Join-Path $oom 'emu\gsrunner\pcsx2-gsrunner.exe'

$jobs = @(
  @{ tag = 'OOMFIX2400';        iso = 'work\builds\GR_OOMFIX\OOMFIX2400.iso';                 dump = $true  },
  @{ tag = 'GR_REBUILD2400';    iso = 'work\builds\GR_REBUILD\GR_REBUILD2400.iso';            dump = $false },
  @{ tag = 'OOMFIX_lay1';       iso = 'work\builds\GR_OOMFIX\OOMFIX_lay1.iso';                dump = $true  },
  @{ tag = 'LAY_fix1_bytecount'; iso = 'work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso';        dump = $false }
)

foreach ($j in $jobs) {
  $others = @(Get-Process -Name 'pcsx2*' -ErrorAction SilentlyContinue)
  if ($others.Count -gt 0) {
    $ids = ($others | ForEach-Object { "$($_.Id):$($_.ProcessName)" }) -join ', '
    throw "another pcsx2 instance is running ($ids) -- refusing to start (exclusive-use rule)"
  }
  $run = Join-Path $oom ("runs\smoke_" + $j.tag)
  if (Test-Path $run) { Remove-Item $run -Recurse -Force }
  New-Item -ItemType Directory -Force -Path $run | Out-Null
  Copy-Item (Join-Path $oom 'common\mc_pristine') (Join-Path $run 'mc') -Recurse -Force
  Copy-Item (Join-Path $oom 'common\bios')        (Join-Path $run 'bios') -Recurse -Force

  $argv = @('-grdumpdir', $run, '-grmaxframes', '6000', '-grsnap', '30',
            '-grscanframes', '2000')
  if ($j.dump) { $argv += @('-grdumpwin', '5970', '5970') }
  $argv += @('-grinput', $nav,
             '-grmemcards', (Join-Path $run 'mc'),
             '-grbios', (Join-Path $run 'bios'),
             '-grbiosname', 'SCPH-90006_BIOS_VX_HK_2.20.bin',
             '-logfile', (Join-Path $run 'emulog.txt'),
             '--', (Join-Path $root $j.iso))
  $line = '"' + $exe + '" ' + (($argv | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' ')
  Set-Content -Path (Join-Path $run 'cmdline.txt') -Value $line -Encoding UTF8
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  Write-Output ("SMOKE {0}: start  {1}" -f $j.tag, (Get-Date -Format 'HH:mm:ss'))
  & $exe @argv 1> (Join-Path $run 'stdout.txt') 2> (Join-Path $run 'stderr.txt')
  $code = $LASTEXITCODE
  $sw.Stop()
  $n = @(Get-ChildItem $run -Filter 'snap_f*.png').Count
  Write-Output ("SMOKE {0}: exit={1} elapsed={2:n0}s snaps={3}" -f $j.tag, $code, $sw.Elapsed.TotalSeconds, $n)
}
Write-Output 'SMOKE ALL DONE'
