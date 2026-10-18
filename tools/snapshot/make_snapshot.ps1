# make_snapshot.ps1 - build the lean orphan snapshot tree/commit (ASCII only: PS 5.1 reads .ps1 as ANSI)
# Usage:
#   powershell -NoProfile -File _archive_scratch\make_snapshot.ps1 -Message _archive_scratch\snapshot_msg.txt
#   ... -Message <file> -Parent <commit>      # child commit (phase 2)
param(
  [string]$Message = '',
  [string]$Parent  = '',
  [string]$Branch  = 'snapshot'
)
$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$scratch = Join-Path $root '_archive_scratch'
$idx = Join-Path $scratch 'snap.index'
if (Test-Path $idx) { Remove-Item -LiteralPath $idx -Force }
$env:GIT_INDEX_FILE = $idx

# ---- file set ----
$fixDocs = git show --name-only --format="" 01ab3530 | Where-Object { $_ -like 'docs/*' }
$citedDocs = @(
  'docs/PROGRESS.md',
  'docs/BUILD_TOOLCHAIN.md',
  'docs/BUILD_VERSIONS.md',
  'docs/PLACEHOLDER_AND_SYMBOLS.md',
  'docs/REPORT_build_font_dump.md',
  'docs/REPORT_csv_text_tool.md',
  'docs/REPORT_font_content_logic_split.md',
  'docs/REPORT_probe_lead_limit.md',
  'docs/REPORT_zh_heap_corruption.md',
  'docs/REPORT_zh90_order_label.md',
  'docs/han_v2/BOOT_SCREENS.md',
  'docs/REPORT_ARCHIVE2.md'
)
$tools = @('tools/final_fix/apply_fix.py', 'tools/final_fix/fix_spec.json', 'tools/final_fix/repro.ps1', 'tools/final_fix/README.md')

$docs = @($fixDocs) + @($citedDocs)
foreach ($p in ($docs + $tools)) { if (-not (Test-Path -LiteralPath $p)) { throw "missing: $p" } }
$docsUnique = $docs | Sort-Object -Unique
Write-Output "docs: $($docsUnique.Count) (fix $($fixDocs.Count) + cited $($citedDocs.Count))  tools: $($tools.Count)"

# ---- build tree in a scratch index (never touches the real index or the branch) ----
git read-tree --empty
if ($LASTEXITCODE -ne 0) { throw 'read-tree failed' }
foreach ($grp in @($docsUnique, $tools)) {
  foreach ($p in $grp) {
    git add -f -- $p
    if ($LASTEXITCODE -ne 0) { throw "add failed: $p" }
  }
}
# inject snapshot-only README + repo ignore/attr files
$readmeBlob = (git hash-object -w (Join-Path $scratch 'snapshot_README.md')).Trim()
$giBlob     = (git hash-object -w '.gitignore').Trim()
$gaBlob     = (git hash-object -w '.gitattributes').Trim()
git update-index --add --cacheinfo "100644,$readmeBlob,README.md"
git update-index --add --cacheinfo "100644,$giBlob,.gitignore"
git update-index --add --cacheinfo "100644,$gaBlob,.gitattributes"
$tree = (git write-tree).Trim()
Write-Output "tree: $tree"

# ---- stats from the tree itself ----
$ls = git ls-tree -r -l $tree
$count = 0; $sum = 0
foreach ($line in $ls) {
  $parts = $line -split '\s+'
  $count++; $sum += [int64]$parts[3]
}
Write-Output ("tree files: {0}   tree bytes: {1} ({2:N2} MB)" -f $count, $sum, ($sum/1MB))
Write-Output "--- tree by top dir ---"
$ls | ForEach-Object {
  $p = ($_ -split '\t')[1]
  $sz = [int64]((($_ -split '\s+')[3]))
  $top = ($p -split '/')[0]
  [PSCustomObject]@{ Top=$top; Size=$sz }
} | Group-Object Top | ForEach-Object {
  [PSCustomObject]@{ Top=$_.Name; KB=[math]::Round((($_.Group | Measure-Object -Property Size -Sum).Sum)/1KB,1); Files=$_.Count }
} | Sort-Object KB -Descending | Format-Table -AutoSize | Out-String -Width 120

if ($Message -eq '') { Write-Output 'NO COMMIT (no -Message).'; exit 0 }

# ---- commit ----
$msgPath = (Resolve-Path $Message).Path
$args = @('commit-tree', $tree, '-F', $msgPath)
if ($Parent -ne '') { $args += @('-p', $Parent) }
$commit = (& git @args).Trim()
Write-Output "commit: $commit"
git branch -f $Branch $commit
Write-Output ("branch {0} -> {1}" -f $Branch, $commit)
Write-Output '--- commit ---'
git log -1 --format='%H%n%s%n%n%b' $commit
Write-Output '--- reset scratch index env ---'
$env:GIT_INDEX_FILE = ''
