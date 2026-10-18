# combfix_batch.ps1 -- GR_COMBFIX evidence matrix (serial, exclusive-check per run)
$ErrorActionPreference = 'Stop'
$root = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
$cf   = Join-Path $root 'work\builds\GR_COMBFIX'
$sf   = Join-Path $root 'work\builds\GR_SPINFIX'
$run  = Join-Path $cf 'tools\combfix_run.ps1'

$jobs = @(
  @{ n='a1_base_S1';  iso="$root\work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso"; st="$sf\states\S1_bin126_user.p2s"; f=46;  x="-grhook 0x539110" },
  @{ n='b1_F4_S1';    iso="$sf\SPINFIX_F4.iso";  st="$cf\states\S1_F4.p2s"; f=300; x="-grpcsample 1 -grhook 0x539110 -grhook 0x41A35C" },
  @{ n='b2_A_S1';     iso="$cf\COMBFIX_A.iso";   st="$cf\states\S1_A.p2s";  f=300; x="-grpcsample 1 -grhook 0x539110 -grhook 0x550048 -grhook 0x41A35C" },
  @{ n='b3_B_S1';     iso="$cf\COMBFIX_B.iso";   st="$cf\states\S1_B.p2s";  f=300; x="-grpcsample 1 -grhook 0x539110 -grhook 0x55B730 -grhook 0x5DECC4 -grhook 0x550048" },
  @{ n='b4_C_S1';     iso="$cf\COMBFIX_C.iso";   st="$cf\states\S1_C.p2s";  f=300; x="-grpcsample 1 -grhook 0x539110 -grhook 0x5DECC4 -grhook 0x550048" },
  @{ n='b5_C_S3';     iso="$cf\COMBFIX_C.iso";   st="$cf\states\S3_C.p2s";  f=600; x="-grpcsample 1 -grhook 0x539110" },
  @{ n='o1_LAY_S1b';  iso="$root\work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso"; st="$cf\states\S1b_bin121_low0.p2s"; f=60; x="-grpcsample 1 -grpcring 262144" },
  @{ n='o2_A_S1b';    iso="$cf\COMBFIX_A.iso";   st="$cf\states\S1b_low0_A.p2s"; f=60; x="-grpcsample 1 -grpcring 262144" },
  @{ n='o3_B_S1b';    iso="$cf\COMBFIX_B.iso";   st="$cf\states\S1b_low0_B.p2s"; f=60; x="-grpcsample 1 -grpcring 262144" },
  @{ n='o4_C_S1b';    iso="$cf\COMBFIX_C.iso";   st="$cf\states\S1b_low0_C.p2s"; f=60; x="-grpcsample 1 -grpcring 262144 -grhook 0x1021E0 -grhook 0x10269C -grhook 0x102588 -grhook 0x41A35C -grhook 0x5DECC4 -grhook 0x539110" }
)

foreach ($j in $jobs) {
  Write-Output ("==== " + $j.n + " ==== " + (Get-Date -Format 'HH:mm:ss'))
  & powershell -NoProfile -ExecutionPolicy Bypass -File $run -RunName $j.n -Iso $j.iso -State $j.st -MaxFrames $j.f -Extra $j.x 2>&1 |
    Where-Object { $_ -match 'RUN |exit=|WARN' } | ForEach-Object { $_ }
}
Write-Output 'BATCH DONE'
