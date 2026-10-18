# run_ab.ps1 -- round47 实机 A/B: 修前 GR_ZH94 → 修后 GR_ZH96_fix, 严格串行, 绝不并发
# 用 run_opt.py 跑 (它每轮把 third_party/emu/run/memcards 的模板卡复位 ⇒ 引导时间线可比)。
$repo = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
$py = 'C:\ProgramData\anaconda3\python.exe'
$log = "$repo\work\builds\GR_ZH94\temp\r47\ab\run_ab.log"
function Log($m) { ((Get-Date -Format 'HH:mm:ss') + '  ' + $m) | Tee-Object -FilePath $log -Append }

Log '=== AB start ==='
Log ("pre: pcsx2=" + (@(Get-Process pcsx2-gsrunner -EA SilentlyContinue).Count))

# ---------- 第 1 轮: 修前 ----------
$env:GR_ISO = "$repo\work\builds\GR_ZH94\GR_ZH94.iso"
Log "round1 (修前) ISO=$env:GR_ISO  tag=r47before  nav=nav_r47.txt  maxf=32000 snap=100"
& $py "$repo\tools\capture\run_opt.py" r47before nav_r47.txt 32000 100 *>> $log
Log "round1 run_opt returncode=$LASTEXITCODE"

# 等仿真器彻底退出
for ($i = 0; $i -lt 120; $i++) {
    if (-not (Get-Process pcsx2-gsrunner -EA SilentlyContinue)) { break }
    Start-Sleep -Seconds 5
}
Log ("round1 emulator gone; pcsx2=" + (@(Get-Process pcsx2-gsrunner -EA SilentlyContinue).Count))
Start-Sleep -Seconds 30
Log ("after 30s: pcsx2=" + (@(Get-Process pcsx2-gsrunner -EA SilentlyContinue).Count))

# ---------- 第 2 轮: 修后 ----------
$env:GR_ISO = "$repo\work\builds\GR_ZH96_fix\GR_ZH96_fix.iso"
Log "round2 (修后) ISO=$env:GR_ISO  tag=r47after  nav=nav_r47.txt  maxf=32000 snap=100"
& $py "$repo\tools\capture\run_opt.py" r47after nav_r47.txt 32000 100 *>> $log
Log "round2 run_opt returncode=$LASTEXITCODE"

for ($i = 0; $i -lt 120; $i++) {
    if (-not (Get-Process pcsx2-gsrunner -EA SilentlyContinue)) { break }
    Start-Sleep -Seconds 5
}
Log ("round2 emulator gone; pcsx2=" + (@(Get-Process pcsx2-gsrunner -EA SilentlyContinue).Count))

foreach ($d in @("$repo\work\builds\GR_ZH94\temp\dump_r47before", "$repo\work\builds\GR_ZH96_fix\temp\dump_r47after")) {
    $n = (Get-ChildItem $d -Filter 'snap_*.png' -EA SilentlyContinue | Measure-Object).Count
    Log "dump $d  snaps=$n"
}
Log '=== AB done ==='
