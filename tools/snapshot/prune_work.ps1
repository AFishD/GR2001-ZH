# prune_work.ps1 - plan & (optionally) execute the work/ prune
# ASCII ONLY on purpose: Windows PowerShell 5.1 reads .ps1 as ANSI.
# Discipline: dry-run first; full manifest always written; long-path-safe deletes.
param(
  [switch]$Execute
)
$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$scratch = Join-Path $root '_archive_scratch'
$LONG = '\\?\'

function Norm([string]$p) {
  $p = $p -replace '/', '\'
  while ($p -match '\\\\') { $p = $p -replace '\\\\', '\' }
  return $p.TrimEnd('\', '.', ',', ';')
}

# ---------------- 1. reference set from docs + tools/final_fix ----------------
$srcFiles = @()
$srcFiles += Get-ChildItem docs -Recurse -File -Include *.md, *.json -EA SilentlyContinue
$srcFiles += Get-ChildItem tools\final_fix -Recurse -File -EA SilentlyContinue
$srcFiles += Get-Item README.md -EA SilentlyContinue

$refFiles = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
$refDirs = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
foreach ($f in $srcFiles) {
  $txt = Get-Content -Raw -LiteralPath $f.FullName -EA SilentlyContinue
  if (-not $txt) { continue }
  foreach ($m in [regex]::Matches($txt, 'work(?:[\\/]{1,2})[^\s"''`,;:)\]}<>|]+')) {
    $tok = Norm $m.Value
    if ($tok.Length -lt 8) { continue }
    $full = Join-Path $root $tok
    if (Test-Path -LiteralPath $full) {
      if ((Get-Item -LiteralPath $full).PSIsContainer) { [void]$refDirs.Add($tok) }
      else { [void]$refFiles.Add($tok) }
    }
  }
}
Write-Output "refs: files=$($refFiles.Count) dirs=$($refDirs.Count)"

# ---------------- 2. keep rules ----------------
$thirdPartyMarkers = @('\src\', '\deps\', '\build\', '\kddock-build\', '\ghidra\ghidra\', '\ghidra\docs\',
                      '\appdata\', '\jdk\', '\qt\', '\3rdparty\', '\bin\', '\lib\', '\extensions\', '\cmakefiles\')
$evidenceExt = @('.json', '.csv', '.txt', '.md', '.log', '.tsv', '.ini', '.patch', '.diff', '.yml', '.yaml', '.xml')
$scriptExt = @('.py', '.ps1', '.java', '.sh', '.bat', '.cmd', '.psm1')
# segments the project itself declares regenerable (README: "extract/ 与 temp/dump_* 均为可重建产物, 清理时直接删")
$regenSegments = @('\temp\', '\tmp\', '\extract\', '\dump_', '\dumps\', '\out\', '\build\', '\deps\', '\src\',
                   '\kddock-build\', '\bin\', '\lib\', '\cmakefiles\')

function IsThirdParty([string]$rel) {
  $l = '\' + $rel.ToLowerInvariant()
  foreach ($m in $thirdPartyMarkers) { if ($l.Contains($m)) { return $true } }
  return $false
}
function IsRegen([string]$rel) {
  $l = '\' + $rel.ToLowerInvariant()
  foreach ($m in $regenSegments) { if ($l.Contains($m)) { return $true } }
  return $false
}

$keepFiles = New-Object 'System.Collections.Generic.List[object]'
$delFiles = New-Object 'System.Collections.Generic.List[object]'

$neverTouch = @('work\builds\GR_HOOKEMU_QT2')
$explicitKeep = @(
  'work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso',
  'work\builds\GR_RELEASE\GR_ZH2400_FINAL.meta.json',
  'work\builds\GR_REBUILD\GR_REBUILD2400.iso',
  'work\builds\GR_REBUILD\build_info_rebuild.json'
)
$explicitDeleteIso = @(
  'work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso',
  'work\builds\GR_COMBFIX\COMBFIX_2400.iso',
  'work\builds\GR_COMBFIX\COMBFIX_C.iso'
)

$workRoot = $LONG + (Join-Path $root 'work')
$allFiles = [System.IO.Directory]::EnumerateFiles($workRoot, '*', [System.IO.SearchOption]::AllDirectories)
$n = 0
foreach ($fp0 in $allFiles) {
  $n++
  $fp = $fp0
  if ($fp.StartsWith($LONG)) { $fp = $fp.Substring(4) }
  $rel = $fp.Substring($root.Length + 1)
  $size = (New-Object System.IO.FileInfo($fp0)).Length

  $inQt2 = $false
  foreach ($nt in $neverTouch) { if ($rel.StartsWith($nt, [StringComparison]::OrdinalIgnoreCase)) { $inQt2 = $true } }
  if ($inQt2) { $keepFiles.Add([PSCustomObject]@{Path=$rel;Size=$size;Reason='KEEP:HOOKEMU_QT2 (do-not-touch)'}); continue }

  $lower = $rel.ToLowerInvariant()
  $ext = [System.IO.Path]::GetExtension($lower)

  if ($explicitKeep -contains $rel) { $keepFiles.Add([PSCustomObject]@{Path=$rel;Size=$size;Reason='KEEP:product/base/meta'}); continue }
  if ($explicitDeleteIso -contains $rel) { $delFiles.Add([PSCustomObject]@{Path=$rel;Size=$size;Reason='DELETE:user-named build disc (sha256 recorded first)'}); continue }

  if ($refFiles.Contains($rel) -and $ext -ne '.iso') {
    $keepFiles.Add([PSCustomObject]@{Path=$rel;Size=$size;Reason='KEEP:evidence cited by docs'}); continue
  }
  $inRefDir = $false
  foreach ($d in $refDirs) { if ($rel.StartsWith($d + '\', [StringComparison]::OrdinalIgnoreCase)) { $inRefDir = $true; break } }
  if ($inRefDir -and ($evidenceExt -contains $ext) -and $size -le 1MB -and -not (IsThirdParty $rel) -and -not (IsRegen $rel)) {
    $keepFiles.Add([PSCustomObject]@{Path=$rel;Size=$size;Reason='KEEP:small evidence in cited dir'}); continue
  }
  # forensic screenshots: cited dirs, run/shot/evidence/audit trees only, small
  if ($inRefDir -and $ext -eq '.png' -and $size -le 1MB -and -not (IsThirdParty $rel) -and -not (IsRegen $rel)) {
    $lf = '\' + $lower
    if ($lf.Contains('\runs\') -or $lf.Contains('\shots\') -or $lf.Contains('\evidence\') -or $lf.Contains('\audit\')) {
      $keepFiles.Add([PSCustomObject]@{Path=$rel;Size=$size;Reason='KEEP:forensic screenshot (runs/shots/evidence/audit)'}); continue
    }
  }
  if (($scriptExt -contains $ext) -and -not (IsThirdParty $rel)) {
    $keepFiles.Add([PSCustomObject]@{Path=$rel;Size=$size;Reason='KEEP:in-house script'}); continue
  }
  if ($ext -eq '.md' -and $size -le 1MB -and -not (IsThirdParty $rel)) {
    $keepFiles.Add([PSCustomObject]@{Path=$rel;Size=$size;Reason='KEEP:small round notes (md)'}); continue
  }
  if ($rel.StartsWith('work\tools\', [StringComparison]::OrdinalIgnoreCase)) {
    if ($rel.StartsWith('work\tools\dl\', [StringComparison]::OrdinalIgnoreCase)) {
      $delFiles.Add([PSCustomObject]@{Path=$rel;Size=$size;Reason='DELETE:re-downloadable installer (zip)'}); continue
    }
    $keepFiles.Add([PSCustomObject]@{Path=$rel;Size=$size;Reason='KEEP:RE toolchain (Ghidra/JDK/projects)'}); continue
  }
  if ($rel.StartsWith('work\_planc\', [StringComparison]::OrdinalIgnoreCase) -or
      $rel.StartsWith('work\_briefs_recovered\', [StringComparison]::OrdinalIgnoreCase)) {
    $keepFiles.Add([PSCustomObject]@{Path=$rel;Size=$size;Reason='KEEP:small evidence dir (_planc/_briefs)'}); continue
  }
  $delFiles.Add([PSCustomObject]@{Path=$rel;Size=$size;Reason='DELETE:experiment artifact / intermediate / big binary'})
}
Write-Output "scanned files: $n"

# ---------------- 3. manifest + summary ----------------
$delSize = ($delFiles | Measure-Object -Property Size -Sum).Sum
$keepSize = ($keepFiles | Measure-Object -Property Size -Sum).Sum
if (-not $delSize) { $delSize = 0 }
if (-not $keepSize) { $keepSize = 0 }

$manifest = Join-Path $scratch 'work_prune_manifest_20261018.csv'
$delFiles | Sort-Object Path | Export-Csv -LiteralPath $manifest -NoTypeInformation -Encoding UTF8
$keepManifest = Join-Path $scratch 'work_keep_manifest_20261018.csv'
$keepFiles | Sort-Object Path | Export-Csv -LiteralPath $keepManifest -NoTypeInformation -Encoding UTF8

Write-Output "==================================================="
Write-Output ("DELETE: {0} files / {1:N2} GB" -f $delFiles.Count, ($delSize/1GB))
Write-Output ("KEEP  : {0} files / {1:N2} GB" -f $keepFiles.Count, ($keepSize/1GB))
Write-Output ("manifest: $manifest")
Write-Output ("keep manifest: $keepManifest")
Write-Output "--- DELETE grouped by top-3 dirs ---"
$delFiles | ForEach-Object {
  $parts = $_.Path -split '\\'
  $key = ($parts[0..([Math]::Min(2, $parts.Count-1))] -join '\')
  [PSCustomObject]@{ Key = $key; Size = $_.Size }
} | Group-Object Key | ForEach-Object {
  [PSCustomObject]@{ Dir=$_.Name; MB=[math]::Round((($_.Group | Measure-Object -Property Size -Sum).Sum)/1MB,1); Files=$_.Count }
} | Sort-Object MB -Descending | Format-Table -AutoSize | Out-String -Width 160
Write-Output "--- DELETE items > 50 MB ---"
$delFiles | Where-Object { $_.Size -gt 50MB } | Sort-Object Size -Descending |
  ForEach-Object { "{0,9:N1} MB  {1}" -f ($_.Size/1MB), $_.Path }
Write-Output "--- KEEP grouped by reason ---"
$keepFiles | Group-Object Reason | ForEach-Object {
  [PSCustomObject]@{ Reason=$_.Name; MB=[math]::Round((($_.Group | Measure-Object -Property Size -Sum).Sum)/1MB,1); Files=$_.Count }
} | Sort-Object MB -Descending | Format-Table -AutoSize | Out-String -Width 160

if (-not $Execute) { Write-Output "DRY RUN ONLY - nothing deleted."; exit 0 }

# ---------------- 4. execute ----------------
$freed = 0; $dfail = 0
foreach ($d in $delFiles) {
  $lp = $LONG + (Join-Path $root $d.Path)
  try { [System.IO.File]::Delete($lp); $freed += $d.Size }
  catch { $dfail++; Write-Output "DEL FAIL: $($d.Path) :: $($_.Exception.Message)" }
}
Write-Output ("deleted files: freed {0:N2} GB, failures {1}" -f ($freed/1GB), $dfail)

# remove now-empty dirs, deepest first
$dirs = [System.IO.Directory]::EnumerateDirectories($workRoot, '*', [System.IO.SearchOption]::AllDirectories)
$sorted = $dirs | Sort-Object { $_.Length } -Descending
$removed = 0
foreach ($dir0 in $sorted) {
  $dir = $dir0
  if ($dir.StartsWith($LONG)) { $dir = $dir.Substring(4) }
  $rel = $dir.Substring($root.Length + 1)
  $skip = $false
  foreach ($nt in $neverTouch) { if ($rel.StartsWith($nt, [StringComparison]::OrdinalIgnoreCase)) { $skip = $true } }
  if ($skip) { continue }
  try {
    $has = $false
    foreach ($e in [System.IO.Directory]::EnumerateFileSystemEntries($LONG + $dir)) { $has = $true; break }
    if (-not $has) { [System.IO.Directory]::Delete($LONG + $dir, $false); $removed++ }
  } catch { }
}
Write-Output "removed empty dirs: $removed"

$asz = 0; $acnt = 0
foreach ($f in [System.IO.Directory]::EnumerateFiles($workRoot, '*', [System.IO.SearchOption]::AllDirectories)) {
  $asz += (New-Object System.IO.FileInfo($f)).Length; $acnt++
}
Write-Output ("AFTER: work = {0:N2} GB / {1} files" -f ($asz/1GB), $acnt)
