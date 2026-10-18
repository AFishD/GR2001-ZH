# Build protection list: files referenced by docs/**/*.md|json and tools/final_fix/**
$ErrorActionPreference = 'Continue'
$root = (Get-Location).Path
$out  = Join-Path $root '_archive_scratch'

# --- 1. gather reference sources ---
$srcFiles = @()
$srcFiles += Get-ChildItem docs -Recurse -File -Include *.md,*.json -EA SilentlyContinue
$srcFiles += Get-ChildItem tools\final_fix -Recurse -File -EA SilentlyContinue
$srcFiles += Get-ChildItem README.md -EA SilentlyContinue

Write-Output "reference sources: $($srcFiles.Count) files"

# --- 2. extract work\... tokens ---
$refs = @{}
foreach ($f in $srcFiles) {
  $txt = Get-Content -Raw -LiteralPath $f.FullName -EA SilentlyContinue
  if (-not $txt) { continue }
  foreach ($m in [regex]::Matches($txt, 'work(?:\\|/)[^\s"''`,;:)\]\}<>|]+')) {
    $tok = $m.Value -replace '/', '\'
    $tok = $tok.TrimEnd('\', '.', ',', ';')
    if ($tok.Length -lt 6) { continue }
    if (-not $refs.ContainsKey($tok)) { $refs[$tok] = New-Object System.Collections.Generic.HashSet[string] }
    [void]$refs[$tok].Add($f.FullName.Substring($root.Length + 1))
  }
}
Write-Output "distinct work-path tokens referenced: $($refs.Count)"

# --- 3. resolve tokens: exact file, exact dir, or descendant match ---
$resolved = @()   # objects: Token, Kind, ResolvedPath, Size, Refs
$unresolved = @()
foreach ($tok in ($refs.Keys | Sort-Object)) {
  $p = Join-Path $root $tok
  if (Test-Path -LiteralPath $p) {
    $it = Get-Item -LiteralPath $p
    if ($it.PSIsContainer) {
      $sz = (Get-ChildItem -LiteralPath $p -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum
      $resolved += [PSCustomObject]@{ Token=$tok; Kind='DIR'; Path=$tok; Size=$sz; Refs=$refs[$tok].Count }
    } else {
      $resolved += [PSCustomObject]@{ Token=$tok; Kind='FILE'; Path=$tok; Size=$it.Length; Refs=$refs[$tok].Count }
    }
  } else { $unresolved += $tok }
}
Write-Output "resolved: $($resolved.Count)   unresolved(gone): $($unresolved.Count)"

# --- 4. referenced paths that don't exist but have a sibling/prefix that does (dir-level refs) ---
#    For each referenced *file* token, also protect its parent dir listing files (meta.json, *.json, *.csv)
$protectFiles = New-Object System.Collections.Generic.HashSet[string]
$protectDirs  = New-Object System.Collections.Generic.HashSet[string]
foreach ($r in $resolved) {
  if ($r.Kind -eq 'FILE') { [void]$protectFiles.Add($r.Path) } else { [void]$protectDirs.Add($r.Path) }
}

$resolved | Sort-Object Size -Descending |
  ForEach-Object { "{0,12:N2} MB  {1,-5} {2}  (refs {3})" -f ($_.Size/1MB), $_.Kind, $_.Path, $_.Refs } |
  Set-Content -LiteralPath (Join-Path $out 'protect_resolved.txt') -Encoding UTF8
$unresolved | Set-Content -LiteralPath (Join-Path $out 'protect_unresolved.txt') -Encoding UTF8

($protectFiles | Sort-Object) | Set-Content -LiteralPath (Join-Path $out 'protect_files.txt') -Encoding UTF8
($protectDirs  | Sort-Object) | Set-Content -LiteralPath (Join-Path $out 'protect_dirs.txt') -Encoding UTF8

Write-Output "protect files: $($protectFiles.Count)   protect dirs: $($protectDirs.Count)"
$psz = 0; foreach ($f in $protectFiles) { if (Test-Path -LiteralPath (Join-Path $root $f)) { $psz += (Get-Item -LiteralPath (Join-Path $root $f)).Length } }
$dsz = 0; foreach ($d in $protectDirs)  { $dsz += (Get-ChildItem -LiteralPath (Join-Path $root $d) -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum }
Write-Output ("protected size (incl dir trees): {0:N2} GB" -f (($psz+$dsz)/1GB))
Write-Output "---- resolved NON-ISO referenced paths (all) ----"
$resolved | Where-Object { $_.Token -notlike '*.iso' } | Sort-Object Token | ForEach-Object { "{0,10:N3} MB  {1,-5} {2}" -f ($_.Size/1MB), $_.Kind, $_.Path }
Write-Output "---- referenced ISO paths ----"
$resolved | Where-Object { $_.Token -like '*.iso' } | Sort-Object Token | ForEach-Object { "{0,10:N0} MB  {1,-5} {2}" -f ($_.Size/1MB), $_.Kind, $_.Path }
