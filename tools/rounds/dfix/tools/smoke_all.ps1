# smoke_all.ps1 -- GR_DFIX serial smoke runs (PCSX2-gsrunner)
#
# Discipline:
#   * Emulator exclusive: before each run poll that ZERO *pcsx2* processes exist
#     (this includes the user's official PCSX2 and the rebuild executor's instance).
#     If someone else is running we ONLY WAIT (never kill) and log the pollution.
#   * Serial: the next disk starts only after the previous process exited.
#   * exit=0 is NOT evidence; the criteria live in cap_results.py output.
#
# NOTE: ASCII-only on purpose -- Windows PowerShell 5.1 reads BOM-less .ps1 as ANSI.
#
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File work\builds\GR_DFIX\tools\smoke_all.ps1
param(
  [string[]]$Tags = @('base', 'DFIX_pkt', 'DFIX_fp', 'DFIX_icon', 'DFIX_pkt_fp'),
  [int]$WaitTimeoutMin = 90
)
$ErrorActionPreference = 'Stop'
$root = 'work\builds\GR_DFIX'
$log  = "$root\audit\smoke_serial.log"
New-Item -ItemType Directory -Force "$root\runs", "$root\audit" | Out-Null

function L($m) {
  $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m
  Write-Host $line
  Add-Content -Path $log -Value $line -Encoding utf8
}

function Get-Pcsx2 {
  Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -like '*pcsx2*' } |
    Select-Object Id, ProcessName, StartTime
}

L "=== GR_DFIX serial smoke START : $($Tags -join ' -> ') ==="

$p = @(Get-Pcsx2)
if ($p.Count -gt 0) {
  L ("[excl] other instance(s) found BEFORE start (wait only, never kill): " +
     (($p | ForEach-Object { "$($_.ProcessName)#$($_.Id)" }) -join ', '))
  $deadline = (Get-Date).AddMinutes($WaitTimeoutMin)
  $n = 0
  while ($p.Count -gt 0 -and (Get-Date) -lt $deadline) {
    $n++
    L ("[excl] poll #$n : still $($p.Count) pcsx2 process(es), wait 20 s (pollution: timing of this round is not a perf criterion)")
    Start-Sleep -Seconds 20
    $p = @(Get-Pcsx2)
  }
  if ($p.Count -gt 0) { L "[excl] TIMEOUT after $WaitTimeoutMin min -- abandon this smoke round, kill nothing"; exit 2 }
  L "[excl] other instance exited by itself; exclusivity acquired (waited ~$($n*20) s)"
} else {
  L "[excl] pcsx2 processes before start = 0 OK"
}

$i = 0
foreach ($t in $Tags) {
  $i++
  if ($t -eq 'base') { $iso = "$root\base\GR_REBUILD2400_base.iso" } else { $iso = "$root\$t.iso" }
  $dump = "$root\runs\$t"
  if (-not (Test-Path $iso)) { L "[!!] missing iso $iso -- skip"; continue }

  $pre = @(Get-Pcsx2)
  L "[$i/$($Tags.Count)] $t : pcsx2 procs before = $($pre.Count)"
  if ($pre.Count -gt 0) { L "[!!] instance present before start, abort: $($pre | Out-String)"; exit 2 }

  $t0 = Get-Date
  $out = (python work\tools\cap_run.py --iso $iso --dump $dump --nav tools\capture\nav_menu_only.txt `
           --maxframes 6000 --snap 30 2>&1 | Out-String)
  $rc = $LASTEXITCODE
  $el = [int]((Get-Date) - $t0).TotalSeconds
  $out | Out-File -Encoding utf8 "$root\audit\run_$t.txt"
  Write-Host $out
  L "[$i/$($Tags.Count)] $t cap_run done elapsed=${el}s exit=$rc (exit not a criterion)"

  $post = @(Get-Pcsx2)
  L "[$i/$($Tags.Count)] $t pcsx2 procs after = $($post.Count) (" +
    (($post | ForEach-Object { "$($_.ProcessName)#$($_.Id)" }) -join ', ') + ")"

  $res = (python work\tools\cap_results.py $dump 2>&1 | Out-String)
  $res | Out-File -Encoding utf8 "$root\audit\results_$t.txt"
  Write-Host $res
  L "[$i/$($Tags.Count)] $t cap_results written: $root\audit\results_$t.txt"
}

# --- per-frame sha256 comparison: cap_results uses the LAST dir as reference -> base last ---
$cmpDirs = @()
foreach ($t in $Tags) { if ($t -ne 'base') { $cmpDirs += "$root\runs\$t" } }
$cmpDirs += "$root\runs\base"
L "[cmp] cap_results per-frame sha256: candidates vs unpatched base (base = reference)"
$cmp = (python work\tools\cap_results.py @cmpDirs 2>&1 | Out-String)
$cmp | Out-File -Encoding utf8 "$root\audit\results_cmp_vs_base.txt"
Write-Host $cmp
L "=== smoke END ==="
