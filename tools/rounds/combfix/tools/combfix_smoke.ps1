# combfix_smoke.ps1 -- GR_COMBFIX 6000-frame cold-boot smoke (4 discs + 2 bases, serial)
# criteria: >=190 snaps / TLB 0 / Trap 0 / per-frame sha256 vs own base
$ErrorActionPreference = 'Stop'
$root = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
$cf   = Join-Path $root 'work\builds\GR_COMBFIX'
$sf   = Join-Path $root 'work\builds\GR_SPINFIX'
$nav  = Join-Path $root 'tools\capture\nav_menu_only.txt'
$exe  = Join-Path $cf 'emu\gsrunner\pcsx2-gsrunner.exe'

$jobs = @(
  @{ tag = 'COMBFIX_A';        iso = "$cf\COMBFIX_A.iso";        dump = $true  },
  @{ tag = 'COMBFIX_B';        iso = "$cf\COMBFIX_B.iso";        dump = $true  },
  @{ tag = 'COMBFIX_C';        iso = "$cf\COMBFIX_C.iso";        dump = $true  },
  @{ tag = 'SPINFIX_F4';       iso = "$sf\SPINFIX_F4.iso";       dump = $false },
  @{ tag = 'COMBFIX_2400';     iso = "$cf\COMBFIX_2400.iso";     dump = $true  },
  @{ tag = 'GR_REBUILD2400';   iso = "$root\work\builds\GR_REBUILD\GR_REBUILD2400.iso"; dump = $false }
)

foreach ($j in $jobs) {
  $others = @(Get-Process -Name 'pcsx2*' -ErrorAction SilentlyContinue)
  if ($others.Count -gt 0) {
    $ids = ($others | ForEach-Object { "$($_.Id):$($_.ProcessName)" }) | Sort-Object
    Write-Output ("[WARN] other pcsx2 running (record only): " + ($ids -join ', '))
  }
  $run = Join-Path $cf ("runs\smoke_" + $j.tag)
  if (Test-Path $run) { Remove-Item $run -Recurse -Force }
  New-Item -ItemType Directory -Force -Path $run | Out-Null
  Copy-Item (Join-Path $sf 'common\mc_pristine') (Join-Path $run 'mc') -Recurse -Force
  Copy-Item (Join-Path $sf 'common\bios')        (Join-Path $run 'bios') -Recurse -Force

  $argv = @('-grdumpdir', $run, '-grmaxframes', '6000', '-grsnap', '30', '-grscanframes', '2000')
  if ($j.dump) { $argv += @('-grdumpwin', '5970', '5970') }
  $argv += @('-grinput', $nav,
             '-grmemcards', (Join-Path $run 'mc'),
             '-grbios',     (Join-Path $run 'bios'),
             '-grbiosname', 'SCPH-90006_BIOS_VX_HK_2.20.bin',
             '-logfile',    (Join-Path $run 'emulog.txt'),
             '--',          $j.iso)
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  Write-Output ("SMOKE " + $j.tag + ": start " + (Get-Date -Format 'HH:mm:ss'))
  & $exe @argv 1> (Join-Path $run 'stdout.txt') 2> (Join-Path $run 'stderr.txt')
  $code = $LASTEXITCODE
  $sw.Stop()
  $n = @(Get-ChildItem $run -Filter 'snap_f*.png').Count
  Write-Output ("SMOKE " + $j.tag + ": exit=" + $code + " elapsed=" + [math]::Round($sw.Elapsed.TotalSeconds,0) + "s snaps=" + $n)
}
Write-Output 'SMOKE ALL DONE'
