# smoke_pktfp.ps1 -- finish the interrupted 5th smoke run (DFIX_pkt_fp) once the emulator is free,
# then redo the per-frame comparison with base as reference.
# ASCII-only on purpose (Windows PowerShell 5.1 reads BOM-less .ps1 as ANSI).
$ErrorActionPreference = 'Stop'
$root = 'work\builds\GR_DFIX'
$log  = "$root\audit\smoke_serial.log"

function L($m) {
  $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m
  Write-Host $line
  Add-Content -Path $log -Value $line -Encoding utf8
}
function Get-Pcsx2 {
  Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -like '*pcsx2*' } |
    Select-Object Id, ProcessName, StartTime
}

L "=== resume: DFIX_pkt_fp ==="
$p = @(Get-Pcsx2)
$n = 0
while ($p.Count -gt 0) {
  $n++
  L ("[excl] resume poll #$n : $($p.Count) pcsx2 process(es) present (" +
     (($p | ForEach-Object { "$($_.ProcessName)#$($_.Id)" }) -join ', ') + "), wait 20 s, never kill")
  Start-Sleep -Seconds 20
  $p = @(Get-Pcsx2)
  if ($n -gt 270) { L "[excl] TIMEOUT"; exit 2 }
}
L "[excl] free (waited ~$($n*20) s); start DFIX_pkt_fp"

$iso  = "$root\DFIX_pkt_fp.iso"
$dump = "$root\runs\DFIX_pkt_fp"
$out = (python work\tools\cap_run.py --iso $iso --dump $dump --nav tools\capture\nav_menu_only.txt `
         --maxframes 6000 --snap 30 2>&1 | Out-String)
$rc = $LASTEXITCODE
$out | Out-File -Encoding utf8 "$root\audit\run_DFIX_pkt_fp.txt"
Write-Host $out
$post = @(Get-Pcsx2)
L "DFIX_pkt_fp cap_run exit=$rc (not a criterion); pcsx2 procs after = $($post.Count)"

$res = (python work\tools\cap_results.py $dump 2>&1 | Out-String)
$res | Out-File -Encoding utf8 "$root\audit\results_DFIX_pkt_fp.txt"
Write-Host $res

$cmp = (python work\tools\cap_results.py "$root\runs\DFIX_pkt" "$root\runs\DFIX_fp" `
        "$root\runs\DFIX_icon" "$root\runs\DFIX_pkt_fp" "$root\runs\base" 2>&1 | Out-String)
$cmp | Out-File -Encoding utf8 "$root\audit\results_cmp_vs_base.txt"
Write-Host $cmp
L "=== resume END ==="
