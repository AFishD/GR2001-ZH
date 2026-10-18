# spinfix_batch.ps1 -- 【GR_SPINFIX】批量跑 + 自动分析 + 日志裁剪（模拟器独占；只记录不杀他人实例）
# usage:
#   powershell -File spinfix_batch.ps1 -Phase A
param([string]$Phase = 'A')
$ErrorActionPreference = 'Stop'
$root = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
$sf   = Join-Path $root 'work\builds\GR_SPINFIX'
$py   = 'C:\Users\84363\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
$run  = Join-Path $sf 'tools\spinfix_run.ps1'
$an   = Join-Path $sf 'tools\spinfix_analyze.py'

$LAY  = 'work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso'
$R2400 = 'work\builds\GR_REBUILD\GR_REBUILD2400.iso'
$S_BASE = 'work\builds\GR_SPINFIX\states\S3_base.p2s'
$S_BAD  = 'work\builds\GR_SPINFIX\states\S1_bin126_user.p2s'
$S_WIN  = 'work\builds\GR_SPINFIX\states\S2_win500_580.p2s'
$HOOKS  = '-grhook 0x539110 -grhook 0x539174 -grhook 0x102050 -grhook 0x1024CC -grhook 0x0041A35C -grhook 0x0055B730 -grhook 0x005DECC4'

$jobs = switch ($Phase) {
  'A' {
    @(
      @{ n='a1_base_stock_state'; iso=$LAY; st=$S_BASE; f=90;  e=$HOOKS },
      @{ n='a2_bad_bin126';       iso=$LAY; st=$S_BAD;  f=90;  e=$HOOKS },
      @{ n='a3_win500_580';       iso=$LAY; st=$S_WIN;  f=90;  e=$HOOKS }
    )
  }
  'B' {
    @(
      @{ n='b1_F4_bad';      iso='work\builds\GR_SPINFIX\SPINFIX_F4.iso';       st='work\builds\GR_SPINFIX\states\S1_bad_F4.p2s';      f=90;  e=$HOOKS },
      @{ n='b2_F1F2_bad';    iso='work\builds\GR_SPINFIX\SPINFIX_F1F2.iso';     st='work\builds\GR_SPINFIX\states\S1_bad_F1F2.p2s';    f=90;  e=$HOOKS },
      @{ n='b3_F1F2F4_bad';  iso='work\builds\GR_SPINFIX\SPINFIX_F1F2_F4.iso';  st='work\builds\GR_SPINFIX\states\S1_bad_F1F2_F4.p2s'; f=90;  e=$HOOKS },
      @{ n='b4_iso_only_ctl'; iso='work\builds\GR_SPINFIX\SPINFIX_F4_2400.iso'; st='work\builds\GR_SPINFIX\states\S1_bin126_user.p2s'; f=90;  e=$HOOKS },
      @{ n='b5_F4_bad_long'; iso='work\builds\GR_SPINFIX\SPINFIX_F4.iso';       st='work\builds\GR_SPINFIX\states\S1_bad_F4.p2s';      f=300; e=$HOOKS },
      @{ n='b6_F4_base_long'; iso='work\builds\GR_SPINFIX\SPINFIX_F4.iso';      st='work\builds\GR_SPINFIX\states\S3_base_F4.p2s';     f=300; e=$HOOKS }
    )
  }
}
foreach ($j in $jobs) {
  Write-Output ("===== {0}  iso={1}  state={2}  frames={3} =====" -f $j.n, $j.iso, $j.st, $j.f)
  & powershell -NoProfile -ExecutionPolicy Bypass -File $run -RunName $j.n -Iso $j.iso `
      -State $j.st -MaxFrames $j.f -Extra $j.e 2>&1 | Select-Object -Last 2
  & $py $an (Join-Path $sf ("runs\" + $j.n)) --json (Join-Path $sf ("runs\" + $j.n + "\analysis.json"))
  Write-Output ''
}
Write-Output 'BATCH DONE'
