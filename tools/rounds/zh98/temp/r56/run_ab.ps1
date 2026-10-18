# round56 A/B: GR_ZH105(紧凑前) vs GR_ZH106(紧凑后) —— 同一导航, 逐帧对比
$ErrorActionPreference = 'Continue'
$root = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
Set-Location $root
$nav = 'tools\capture\nav_r47.txt'
$frames = 30200
$log = 'work\builds\GR_ZH98\temp\r56\ab_log.txt'
New-Item -ItemType Directory -Force -Path 'work\builds\GR_ZH98\temp\r56' | Out-Null
function L($m) { $m | Tee-Object -FilePath $log -Append }

foreach ($tag in @('A_zh105', 'B_zh106')) {
    $iso = if ($tag -eq 'A_zh105') { "$root\work\builds\GR_ZH105\GR_ZH105.iso" } else { "$root\work\builds\GR_ZH106\GR_ZH106.iso" }
    $out = "work\builds\GR_ZH98\temp\r56\dump_$tag"
    # 单实例铁律: 起跑前清掉别的实例
    Get-Process pcsx2-gsrunner -EA SilentlyContinue | ForEach-Object { L "  [warn] 杀掉残留实例 PID $($_.Id)"; Stop-Process -Id $_.Id -Force -EA SilentlyContinue }
    Start-Sleep -Seconds 3
    L "=== $tag : $iso ==="
    $env:GR_ISO = $iso
    & C:\ProgramData\anaconda3\python.exe tools\capture\run_opt.py $out $nav $frames 100 2>&1 |
        Select-Object -Last 3 | ForEach-Object { L "  $_" }
    L "  exit=$LASTEXITCODE ; 帧数=$((Get-ChildItem $out -Filter 'snap_*.png' -EA SilentlyContinue | Measure-Object).Count)"
    Start-Sleep -Seconds 5
}
L "=== A/B 抓帧完成 ==="
Get-Process pcsx2-gsrunner -EA SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force -EA SilentlyContinue }
