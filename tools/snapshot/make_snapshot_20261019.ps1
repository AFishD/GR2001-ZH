# make_snapshot_20261019.ps1 -- build the lean orphan snapshot (finalize round, 2026-10-18)
# ASCII only (PS 5.1 reads .ps1 as ANSI).
#   powershell -NoProfile -File _archive_scratch\make_snapshot_20261019.ps1 -Branch snapshot-2026-10-19
# Writes: nothing into the real index / working tree. Only a scratch index + a local branch.
param(
  [string]$Branch = 'snapshot-2026-10-19',
  [string]$Parent = '',
  [switch]$NoCommit
)
$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$scratch = Join-Path $root '_archive_scratch'
$idx = Join-Path $scratch 'snap.index'

# ---- file set: tools/final_fix (tracked) + docs text files (working tree) ----
# NOTE: read the tracked list with the REAL index, before switching GIT_INDEX_FILE.
$tools = git ls-files tools/final_fix
if ($tools.Count -lt 6) { throw ("tools/final_fix tracked files = {0} (expected 6)" -f $tools.Count) }
$docs = Get-ChildItem docs -Recurse -File |
        Where-Object { $_.Extension -in '.md', '.json', '.csv', '.txt' } |
        ForEach-Object { $_.FullName.Substring($root.Length + 1).Replace('\', '/') }
$docs = $docs | Sort-Object -Unique
# respect .gitignore: never publish anything the repo deliberately ignores
# (e.g. .gitignore:47 docs/han_v2/*.json, :48 docs/han_v2/*.txt -> early extracted string dumps)
$ignored = @(git ls-files --others --ignored --exclude-standard -- docs)
if ($ignored.Count -gt 0) {
  Write-Output ("excluding {0} .gitignore'd docs file(s):" -f $ignored.Count)
  $ignored | ForEach-Object { Write-Output ("   - " + $_) }
}
$docs = @($docs | Where-Object { $ignored -notcontains $_ })
Write-Output ("tools/final_fix: {0}   docs(text): {1}" -f $tools.Count, $docs.Count)
foreach ($p in ($tools + $docs)) { if (-not (Test-Path -LiteralPath $p)) { throw "missing: $p" } }

if (Test-Path $idx) { Remove-Item -LiteralPath $idx -Force }
$env:GIT_INDEX_FILE = $idx

git read-tree --empty
if ($LASTEXITCODE -ne 0) { throw 'read-tree failed' }
foreach ($p in ($tools + $docs)) {
  git add -f -- $p
  if ($LASTEXITCODE -ne 0) { throw "add failed: $p" }
}
# snapshot-only README + repo policy files
$readmeBlob = (git hash-object -w (Join-Path $scratch 'snapshot_README_20261019.md')).Trim()
$giBlob     = (git hash-object -w '.gitignore').Trim()
$gaBlob     = (git hash-object -w '.gitattributes').Trim()
git update-index --add --cacheinfo "100644,$readmeBlob,README.md"
git update-index --add --cacheinfo "100644,$giBlob,.gitignore"
git update-index --add --cacheinfo "100644,$gaBlob,.gitattributes"
$tree = (git write-tree).Trim()
Write-Output "tree: $tree"

# ---- stats + safety audit from the tree itself ----
$ls = git ls-tree -r -l $tree
$count = 0; $sum = [int64]0
$badExt = @()
foreach ($line in $ls) {
  $parts = $line -split '\s+'
  $count++; $sum += [int64]$parts[3]
  $path = ($line -split '\t')[1]
  $ext = [System.IO.Path]::GetExtension($path).ToLower()
  if ($ext -in '.iso', '.elf', '.bin', '.mis', '.rsb', '.bmb', '.png', '.p2s', '.xlsx', '.dll', '.exe', '.zip', '.7z') {
    $badExt += $path
  }
}
Write-Output ("tree files: {0}   tree bytes: {1} ({2:N2} MB)" -f $count, $sum, ($sum / 1MB))
Write-Output ("forbidden-extension files: {0}" -f $badExt.Count)
if ($badExt.Count -gt 0) { $badExt | ForEach-Object { Write-Output ("   !! " + $_) }; throw 'forbidden files in snapshot tree' }
Write-Output 'hooks check (must be True):'
$hook = @($ls | Where-Object { $_ -like '*docs/REPORT_HOOKEMU_QT2_REBUILD.md*' })
Write-Output ("   docs/REPORT_HOOKEMU_QT2_REBUILD.md present = " + ($hook.Count -eq 1))
$ff = @($ls | Where-Object { $_ -like '*tools/final_fix/*' })
Write-Output ("   tools/final_fix files in tree = " + $ff.Count)
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

$msgPath = (Resolve-Path (Join-Path $scratch 'snapshot_msg_20261019.txt')).Path
$ctArgs = @('commit-tree', $tree, '-F', $msgPath)
if ($Parent -ne '') { $ctArgs += @('-p', $Parent) }
$commit = (& git @ctArgs).Trim()
Write-Output "commit: $commit"
git branch -f $Branch $commit
Write-Output ("branch {0} -> {1}" -f $Branch, $commit)
Write-Output '--- commit ---'
git log -1 --format='%H%n%s' $commit
$env:GIT_INDEX_FILE = ''
