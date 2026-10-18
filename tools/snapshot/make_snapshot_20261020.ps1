# make_snapshot_20261020.ps1 -- lean orphan snapshot for the script-relocation round.
# ASCII only (PS 5.1 reads .ps1 as ANSI).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\snapshot\make_snapshot_20261020.ps1 [-NoCommit]
#
# Content = tools\** (tracked: relocated scripts + final_fix + maint + snapshot)
#         + docs\** text files (working tree, minus anything .gitignore'd)
#         + top-level README.md / .gitignore / .gitattributes
# Never touches the real index or the working tree: scratch index + commit-tree only.
param(
  [string]$Branch = 'snapshot-2026-10-20',
  [string]$Parent = '7f067ce1d6b4c44c0cfe460a89a1fd51ec692adc',   # previous snapshot tip (remote main)
  [switch]$NoCommit
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $root
$scratch = Join-Path $root '_archive_scratch'
$idx = Join-Path $scratch 'snap.index'

# ---- file set (read the REAL index before switching GIT_INDEX_FILE) ----
$tools = @(git ls-files tools)
if ($tools.Count -lt 1000) { throw ("tools tracked files = {0} (expected >1000)" -f $tools.Count) }

$docs = Get-ChildItem docs -Recurse -File |
        Where-Object { $_.Extension -in '.md', '.json', '.csv', '.txt' } |
        ForEach-Object { $_.FullName.Substring($root.Length + 1).Replace('\', '/') }
$docs = $docs | Sort-Object -Unique
$ignored = @(git ls-files --others --ignored --exclude-standard -- docs tools)
if ($ignored.Count -gt 0) {
  Write-Output ("excluding {0} .gitignore'd file(s):" -f $ignored.Count)
  $ignored | ForEach-Object { Write-Output ("   - " + $_) }
}
$docs = @($docs | Where-Object { $ignored -notcontains $_ })

$all = @($tools + $docs)
Write-Output ("tools(tracked): {0}   docs(text): {1}   total: {2}" -f $tools.Count, $docs.Count, $all.Count)
foreach ($p in $all) { if (-not (Test-Path -LiteralPath $p)) { throw "missing: $p" } }

if (Test-Path $idx) { Remove-Item -LiteralPath $idx -Force }
$env:GIT_INDEX_FILE = $idx
git read-tree --empty
if ($LASTEXITCODE -ne 0) { throw 'read-tree failed' }
foreach ($p in $all) {
  git add -f -- $p
  if ($LASTEXITCODE -ne 0) { throw "add failed: $p" }
}
# snapshot-only README + repo policy files
$readmeBlob = (git hash-object -w (Join-Path $PSScriptRoot 'snapshot_README_20261020.md')).Trim()
$giBlob     = (git hash-object -w '.gitignore').Trim()
$gaBlob     = (git hash-object -w '.gitattributes').Trim()
git update-index --add --cacheinfo "100644,$readmeBlob,README.md"
git update-index --add --cacheinfo "100644,$giBlob,.gitignore"
git update-index --add --cacheinfo "100644,$gaBlob,.gitattributes"
$tree = (git write-tree).Trim()
Write-Output "tree: $tree"

# ---- stats + forbidden-extension audit from the tree itself ----
$ls = git ls-tree -r -l $tree
$count = 0; $sum = [int64]0; $badExt = @(); $extTally = @{}
foreach ($line in $ls) {
  $parts = $line -split '\s+'
  $count++; $sum += [int64]$parts[3]
  $path = ($line -split '\t')[1]
  $ext = [System.IO.Path]::GetExtension($path).ToLower()
  if ($extTally.ContainsKey($ext)) { $extTally[$ext]++ } else { $extTally[$ext] = 1 }
  if ($ext -in '.iso', '.elf', '.bin', '.mis', '.rsb', '.bmb', '.png', '.p2s', '.xlsx', '.dll', '.exe', '.zip', '.7z') {
    $badExt += $path
  }
}
Write-Output ("tree files: {0}   tree bytes: {1} ({2:N2} MB)" -f $count, $sum, ($sum / 1MB))
Write-Output '--- by extension ---'
$extTally.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object {
  Write-Output ("   {0,-8} {1}" -f $_.Key, $_.Value)
}
Write-Output ("forbidden-extension files: {0}" -f $badExt.Count)
if ($badExt.Count -gt 0) { $badExt | ForEach-Object { Write-Output ("   !! " + $_) }; throw 'forbidden files in snapshot tree' }

Write-Output 'hooks check (must all be True):'
$hook = @($ls | Where-Object { $_ -like '*docs/REPORT_HOOKEMU_QT2_REBUILD.md*' })
Write-Output ("   docs/REPORT_HOOKEMU_QT2_REBUILD.md present = " + ($hook.Count -eq 1))
$ff = @($ls | Where-Object { $_ -like '*tools/final_fix/*' })
Write-Output ("   tools/final_fix files in tree = " + $ff.Count)
$tb = @($ls | Where-Object { $_ -like '*tools/re/toolbelt/*' })
Write-Output ("   tools/re/toolbelt files in tree = " + $tb.Count)
$rm = @($ls | Where-Object { $_ -like '*tools/README_scripts.md*' })
Write-Output ("   tools/README_scripts.md present = " + ($rm.Count -eq 1))
$af = @($ls | Where-Object { $_ -like '*tools/final_fix/apply_fix.py*' })
Write-Output ("   tools/final_fix/apply_fix.py present = " + ($af.Count -eq 1))
$mv = @($ls | Where-Object { $_ -like '*docs/REPORT_SCRIPTS_MOVE.md*' })
Write-Output ("   docs/REPORT_SCRIPTS_MOVE.md present = " + ($mv.Count -eq 1))
Write-Output '--- tree by top dir ---'
$ls | ForEach-Object {
  $p = ($_ -split '\t')[1]
  $sz = [int64](($_ -split '\s+')[3])
  $top = ($p -split '/')[0]
  [PSCustomObject]@{ Top = $top; Size = $sz }
} | Group-Object Top | ForEach-Object {
  [PSCustomObject]@{ Top = $_.Name; KB = [math]::Round((($_.Group | Measure-Object -Property Size -Sum).Sum) / 1KB, 1); Files = $_.Count }
} | Sort-Object KB -Descending | Format-Table -AutoSize | Out-String -Width 120

if ($NoCommit) { Write-Output 'NO COMMIT (-NoCommit).'; $env:GIT_INDEX_FILE = ''; exit 0 }

$msgPath = (Resolve-Path (Join-Path $PSScriptRoot 'snapshot_msg_20261020.txt')).Path
$ctArgs = @('commit-tree', $tree, '-F', $msgPath)
if ($Parent -ne '') { $ctArgs += @('-p', $Parent) }
$commit = (& git @ctArgs).Trim()
Write-Output "commit: $commit"
git branch -f $Branch $commit
Write-Output ("branch {0} -> {1}" -f $Branch, $commit)
Write-Output '--- commit ---'
git log -1 --format='%H%n%s' $commit
Write-Output '--- ancestry check (parent must be the previous snapshot tip) ---'
git log --oneline -3 $commit
$env:GIT_INDEX_FILE = ''
