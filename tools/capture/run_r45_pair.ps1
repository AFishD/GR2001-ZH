# run_r45_pair.ps1 -- 串行跑两个实机 (不并发): ① 探针盘 ② 现役盘基线
# 用法: pwsh -File tools\capture\run_r45_pair.ps1
$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$py = 'C:\ProgramData\anaconda3\python.exe'
$nav = 'tools\capture\nav_r45a.txt'

Write-Output "=== [1/2] 探针盘 GR_ZH97_probe $(Get-Date -Format 'HH:mm:ss') ==="
& $py tools\capture\run_r45.py --iso work\builds\GR_ZH97_probe\GR_ZH97_probe.iso `
    --nav $nav --dump work\builds\GR_ZH97_probe\temp\dump_probe `
    --maxframes 34000 --snap 100 --scanframes 4000 *> work\builds\GR_ZH97_probe\temp\r45\run_probe.log
Write-Output "probe exit=$LASTEXITCODE $(Get-Date -Format 'HH:mm:ss')"
Get-Content work\builds\GR_ZH97_probe\temp\r45\run_probe.log -Tail 6

Write-Output "=== [2/2] 现役盘基线 GR_ZH93 $(Get-Date -Format 'HH:mm:ss') ==="
& $py tools\capture\run_r45.py --iso work\builds\GR_ZH93\GR_ZH93.iso `
    --nav $nav --dump work\builds\GR_ZH97_probe\temp\dump_base93 `
    --maxframes 34000 --snap 100 --scanframes 4000 *> work\builds\GR_ZH97_probe\temp\r45\run_base93.log
Write-Output "base93 exit=$LASTEXITCODE $(Get-Date -Format 'HH:mm:ss')"
Get-Content work\builds\GR_ZH97_probe\temp\r45\run_base93.log -Tail 6
Write-Output "=== ALL DONE $(Get-Date -Format 'HH:mm:ss') ==="
