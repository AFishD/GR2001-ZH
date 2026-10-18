# rel_smoke.ps1 -- GR_RELEASE 6000-frame cold-boot smoke (交付候选 + 基底, 串行, 独占)
# 判据: >=190 截图 / TLB 0 / Trap 0 / 逐帧 sha256 vs 基底 / 第 5970 帧 RAM 回读(补丁存活)
# 纪律: 起跑前轮询 pcsx2*, 命中**只记录不杀**; 输出只落在 work\builds\GR_RELEASE\**
$ErrorActionPreference = 'Stop'
$root = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
$rel  = Join-Path $root 'work\builds\GR_RELEASE'
$sf   = Join-Path $root 'work\builds\GR_SPINFIX'
$nav  = Join-Path $root 'tools\capture\nav_menu_only.txt'
$exe  = Join-Path $root 'third_party\emu\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe'

$jobs = @(
  @{ tag = 'GR_ZH2400_FINAL';  iso = "$rel\GR_ZH2400_FINAL.iso";                        dump = $true  },
  @{ tag = 'GR_REBUILD2400';   iso = "$root\work\builds\GR_REBUILD\GR_REBUILD2400.iso"; dump = $true  }
)

foreach ($j in $jobs) {
  $others = @(Get-Process -Name 'pcsx2*' -ErrorAction SilentlyContinue)
  $run = Join-Path $rel ("runs\smoke_" + $j.tag)
  if (Test-Path $run) { Remove-Item $run -Recurse -Force }
  New-Item -ItemType Directory -Force -Path $run | Out-Null
  if ($others.Count -gt 0) {
    $ids = ($others | ForEach-Object { "$($_.Id):$($_.ProcessName):$($_.StartTime)" }) | Sort-Object
    Write-Output ("[WARN] other pcsx2 running (record only, never kill): " + ($ids -join ', '))
    Set-Content -Path (Join-Path $run 'OTHERS_RUNNING.txt') -Value ($ids -join "`n") -Encoding UTF8
  }
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
  Set-Content -Path (Join-Path $run 'cmdline.txt') -Value ($argv -join ' ') -Encoding UTF8
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  Write-Output ("SMOKE " + $j.tag + ": start " + (Get-Date -Format 'HH:mm:ss'))
  & $exe @argv 1> (Join-Path $run 'stdout.txt') 2> (Join-Path $run 'stderr.txt')
  $code = $LASTEXITCODE
  $sw.Stop()
  $n = @(Get-ChildItem $run -Filter 'snap_f*.png').Count
  $post = @(Get-Process -Name 'pcsx2*' -ErrorAction SilentlyContinue)
  Write-Output ("SMOKE " + $j.tag + ": exit=" + $code + " elapsed=" + [math]::Round($sw.Elapsed.TotalSeconds,0) + "s snaps=" + $n + " post_procs=" + $(if($post.Count -gt 0){$post.Count}else{'none'}))
}
Write-Output 'SMOKE ALL DONE'
