# extra_oomfix.ps1 -- B 的补充对照（低端区直接写监视 A/B）+ 英文盘/英文存档对照
$ErrorActionPreference = 'Stop'
$root = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
$oom  = Join-Path $root 'work\builds\GR_OOMFIX'
$run  = Join-Path $oom 'tools\run_oomfix.ps1'

Write-Output '=== u1b: 未修基底 + 原存档 + L1@30，直接监视低端 0x400..0x1000 ==='
& $run -RunName u1b_base_lowwatch -Iso 'work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso' `
  -MaxFrames 130 -ExtraArgs @('-grwatch','1024','3072','-grwatch','4864','256',
                              '-grhook','0x539110','-grhook','0x539174')

Write-Output '=== p2d: 修复盘 + 补丁存档 + L1@30，同样监视低端 ==='
& $run -RunName p2d_patched_lowwatch -Iso 'work\builds\GR_OOMFIX\OOMFIX_lay1.iso' `
  -State 'work\builds\GR_OOMFIX\states\SLUS-20613 (CC41DF03).01.p2s' `
  -MaxFrames 130 -ExtraArgs @('-grwatch','1024','3072','-grwatch','4864','256',
                              '-grhook','0x539110','-grhook','0x550048')

Write-Output '=== eng: 英文原盘 + 英文存档 + L1@30（同一解压器请求成功/失败对照） ==='
& $run -RunName eng_l1 -Iso "third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso" `
  -State 'work\builds\GR_OOMFIX\common\state_ENG_3E571E95.p2s' `
  -MaxFrames 70 -ExtraArgs @('-grwatch','4864','256','-grhook','0x539110','-grhook','0x539174')

Write-Output 'EXTRA ALL DONE'
