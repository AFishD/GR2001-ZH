# move_scripts_from_work.ps1 -- relocate every .py/.ps1 out of work\ into tools\
# ASCII only. Re-runnable (idempotent: skips when source is already gone).
#
#   pwsh -NoProfile -File tools\maint\move_scripts_from_work.ps1 [-DryRun]
#
# Mapping rules
#   work\tools\*.py|*.ps1              -> tools\re\toolbelt\
#   work\tools\ghidra_scripts\*        -> tools\re\ghidra_scripts\      (ours: .java + .py)
#   work\builds\<BUILD>\<rel>          -> tools\rounds\<theme>\<rel>    theme = BUILD minus 'GR_' lowercased
#   work\_planc\*.py                   -> tools\rounds\planc\           (restored from git fe4991d1)
#   _archive_scratch\*.ps1|*.md|snap.index -> tools\snapshot\
#
# NOT moved (deliberate, see tools\README_scripts.md):
#   work\builds\GR_HOOKEMU_QT2\**   -- user-forbidden (live forensic toolkit)
#   work\tools\ghidra\**            -- vendored third-party Ghidra distribution
#   work\tools\jdk|appdata|ghidra_proj*|ghidra_out|__pycache__ -- local toolchain / project DBs
param([switch]$DryRun)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $root

$moves = New-Object System.Collections.Generic.List[object]
function Add-Move([string]$src, [string]$dst) {
  $moves.Add([pscustomobject]@{ Old = $src; New = $dst })
}
# PS 5.1: -Include needs -Recurse or a wildcard path -> always filter by extension ourselves
function Get-Scripts([string]$dir, [switch]$Recurse) {
  $a = @{ Path = $dir; File = $true; Force = $true; ErrorAction = 'SilentlyContinue' }
  if ($Recurse) { $a.Recurse = $true }
  Get-ChildItem @a | Where-Object { $_.Extension -eq '.py' -or $_.Extension -eq '.ps1' }
}

$SKIP_BUILD = @('GR_HOOKEMU_QT2')          # user: forbidden to touch
$TOOLCHAIN  = @('ghidra','jdk','appdata','ghidra_proj','ghidra_proj_ee','ghidra_out','__pycache__')

# ---- 1. work\tools\*.py  +  work\tools\ghidra_scripts\* ----
foreach ($f in (Get-Scripts 'work\tools')) {
  Add-Move ("work\tools\" + $f.Name) ("tools\re\toolbelt\" + $f.Name)
}
$gs = 'work\tools\ghidra_scripts'
if (Test-Path $gs) {
  foreach ($f in (Get-ChildItem $gs -File -Force)) {
    Add-Move ("work\tools\ghidra_scripts\" + $f.Name) ("tools\re\ghidra_scripts\" + $f.Name)
  }
}

# ---- 2. work\builds\<BUILD>\**\*.py|*.ps1 ----
foreach ($b in (Get-ChildItem 'work\builds' -Directory -Force)) {
  if ($SKIP_BUILD -contains $b.Name) { continue }
  $theme = ($b.Name -replace '^GR_','').ToLower()
  $base  = $b.FullName.Length + 1
  foreach ($f in (Get-Scripts $b.FullName -Recurse)) {
    $rel = $f.FullName.Substring($base)
    Add-Move ("work\builds\" + $b.Name + "\" + $rel) ("tools\rounds\" + $theme + "\" + $rel)
  }
}

# ---- 3. work\builds root-level scripts (if any) ----
foreach ($f in (Get-Scripts 'work\builds')) {
  Add-Move ("work\builds\" + $f.Name) ("tools\rounds\_root\" + $f.Name)
}

# ---- 4. _archive_scratch scripts / snapshot machinery ----
foreach ($f in (Get-ChildItem '_archive_scratch' -File -Force -ErrorAction SilentlyContinue |
                Where-Object { $_.Extension -in '.ps1','.md' -or $_.Name -eq 'snap.index' })) {
  Add-Move ("_archive_scratch\" + $f.Name) ("tools\snapshot\" + $f.Name)
}

# ---- 5. recover work\_planc\*.py from git fe4991d1 (deleted 2026-10-18 by the aborted cleanup) ----
$PLANC_REF = 'fe4991d1'
$plancDst = Join-Path $root 'tools\rounds\planc'
if (-not (Test-Path -LiteralPath $plancDst)) { New-Item -ItemType Directory -Path $plancDst -Force | Out-Null }
$plancRefs = @(git ls-tree -r --name-only $PLANC_REF -- work/_planc 2>$null)
foreach ($p in $plancRefs) {
  if ($p -notmatch '\.py$') { continue }
  $name = Split-Path $p -Leaf
  $dst  = Join-Path $plancDst $name
  if (Test-Path -LiteralPath $dst) { continue }
  $tmp = Join-Path $env:TEMP ("planc_" + [guid]::NewGuid().ToString('N') + ".py")
  cmd /c "git show $PLANC_REF`:$($p -replace '/','/') > `"$tmp`""
  if ((Test-Path -LiteralPath $tmp) -and (Get-Item -LiteralPath $tmp).Length -gt 0) {
    Move-Item -LiteralPath $tmp -Destination $dst -Force
    Add-Move ($p -replace '/','\') ("tools\rounds\planc\" + $name)
  } else { Write-Output ("   !! planc restore failed: " + $p) }
}
Write-Output ("planc recovered: {0}" -f (@($plancRefs | Where-Object { $_ -match '\.py$' }).Count))

# ---- report + execute ----
$total = $moves.Count
$dup = $moves | Group-Object New | Where-Object { $_.Count -gt 1 }
Write-Output ("planned moves: {0}" -f $total)
if ($dup) { Write-Output ("!! destination collisions: {0}" -f $dup.Count); $dup | ForEach-Object { Write-Output ("   " + $_.Name) } }
$moves | Group-Object { ($_.New -split '\\')[0..2] -join '\' } | Sort-Object Count -Descending |
  ForEach-Object { Write-Output ("   {0,6}  {1}" -f $_.Count, $_.Name) }

if ($DryRun) { Write-Output 'DRY RUN - nothing moved.'; exit 0 }

$done = 0; $skipped = 0; $failed = @()
foreach ($m in $moves) {
  $src = Join-Path $root $m.Old
  $dst = Join-Path $root $m.New
  if (-not (Test-Path -LiteralPath $src)) { $skipped++; continue }
  $d = Split-Path $dst -Parent
  if (-not (Test-Path -LiteralPath $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
  try { Move-Item -LiteralPath $src -Destination $dst -Force; $done++ }
  catch { $failed += ("{0} -> {1} : {2}" -f $m.Old, $m.New, $_.Exception.Message) }
}
Write-Output ("moved: {0}   source-already-gone: {1}   failed: {2}" -f $done, $skipped, $failed.Count)
if ($failed.Count) { $failed | ForEach-Object { Write-Output ("   !! " + $_) } ; exit 1 }

# ---- write the old->new map ----
$csv = 'tools\scripts_move_map.csv'
$moves | Sort-Object Old | Export-Csv -LiteralPath $csv -NoTypeInformation -Encoding UTF8
Write-Output ("map written: {0}  rows={1}" -f $csv, $moves.Count)
