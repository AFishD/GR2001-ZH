# rel_regress.ps1 -- B7 同现场回归 (两套现场 x 未修基底/成品盘), 串行独占, 输出只在 GR_RELEASE\**
#   S1  : 坏桶 126 存档 (用户现场)          S1b : 桶 121 毒化 + 低端清零 (等价新现场)
# 判据: Trap / TLB Miss / 能否跑完 (=== run end) / 块入口循环形态
$ErrorActionPreference = 'Stop'
$root = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
$rel  = Join-Path $root 'work\builds\GR_RELEASE'
$sf   = Join-Path $root 'work\builds\GR_SPINFIX'
$cf   = Join-Path $root 'work\builds\GR_COMBFIX'
$exe  = Join-Path $root 'third_party\emu\pcsx2\pcsx2-gsrunner\pcsx2-gsrunner.exe'
$nav  = Join-Path $sf 'inputs\in_l1_f30.txt'
$lay  = Join-Path $root 'work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso'
$fin  = Join-Path $rel 'GR_ZH2400_FINAL.iso'

$jobs = @(
  @{ n='a1_LAY_S1';      iso=$lay; st=(Join-Path $sf 'states\S1_bin126_user.p2s');   f=46;  x=@('-grhook','0x539110') },
  @{ n='o1_LAY_S1b';     iso=$lay; st=(Join-Path $cf 'states\S1b_bin121_low0.p2s');  f=60;  x=@('-grpcsample','1','-grpcring','262144') },
  @{ n='p1_FINAL_S1';    iso=$fin; st=(Join-Path $rel 'states\S1_FINAL.p2s');        f=300; x=@('-grpcsample','1','-grhook','0x539110','-grhook','0x5DECC4','-grhook','0x550048','-grhook','0x41A35C') },
  @{ n='p2_FINAL_S1b';   iso=$fin; st=(Join-Path $rel 'states\S1b_low0_FINAL.p2s');  f=60;  x=@('-grpcsample','1','-grpcring','262144','-grhook','0x1021E0','-grhook','0x10269C','-grhook','0x102588','-grhook','0x41A35C','-grhook','0x5DECC4','-grhook','0x539110') }
)

foreach ($j in $jobs) {
  $run = Join-Path $rel ("runs\reg_" + $j.n)
  $others = @(Get-Process -Name 'pcsx2*' -ErrorAction SilentlyContinue)
  if (Test-Path $run) { Remove-Item $run -Recurse -Force }
  New-Item -ItemType Directory -Force -Path $run | Out-Null
  if ($others.Count -gt 0) {
    $ids = ($others | ForEach-Object { "$($_.Id):$($_.ProcessName):$($_.StartTime)" }) | Sort-Object
    Write-Output ("[WARN] other pcsx2 running (record only, never kill): " + ($ids -join ', '))
    Set-Content -Path (Join-Path $run 'OTHERS_RUNNING.txt') -Value ($ids -join "`n") -Encoding UTF8
  }
  Copy-Item (Join-Path $sf 'common\mc_pristine') (Join-Path $run 'mc') -Recurse -Force
  Copy-Item (Join-Path $sf 'common\bios')        (Join-Path $run 'bios') -Recurse -Force
  $argv = @('-grdumpdir', $run, '-grmaxframes', "$($j.f)", '-grstate', $j.st, '-grinput', $nav)
  $argv += $j.x
  $argv += @('-grmemcards', (Join-Path $run 'mc'),
             '-grbios',     (Join-Path $run 'bios'),
             '-grbiosname', 'SCPH-90006_BIOS_VX_HK_2.20.bin',
             '-logfile',    (Join-Path $run 'emulog.txt'),
             '--',          $j.iso)
  Set-Content -Path (Join-Path $run 'cmdline.txt') -Value ($argv -join ' ') -Encoding UTF8
  Write-Output ("==== " + $j.n + " ==== start " + (Get-Date -Format 'HH:mm:ss'))
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  & $exe @argv 1> (Join-Path $run 'stdout.txt') 2> (Join-Path $run 'stderr.txt')
  $code = $LASTEXITCODE
  $sw.Stop()
  Write-Output ("REG " + $j.n + ": exit=" + $code + " elapsed=" + [math]::Round($sw.Elapsed.TotalSeconds,0) + "s")
}
Write-Output 'REG ALL DONE'
