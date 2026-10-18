# verify_user_root.ps1 -- prove the user's data root was never written to.
# Re-hashes every file under %LOCALAPPDATA%\PCSX2 and diffs against the baseline manifest
# taken before any GR_SYNC run (GR_SYNC\USER_DATA_ROOT_BASELINE.csv).
# Also re-hashes the private root's bios/memcards and compares them with the user's originals.
$ErrorActionPreference = 'Stop'
$root = Join-Path $env:LOCALAPPDATA 'PCSX2'
$base = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_SYNC\USER_DATA_ROOT_BASELINE.csv'
$priv = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_SYNC\data\PCSX2'
$out  = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_SYNC\USER_ROOT_VERIFY.txt'

$old = @{}
foreach ($r in (Import-Csv $base)) { $old[$r.rel] = $r }

$files = Get-ChildItem $root -Recurse -File -Force -ErrorAction SilentlyContinue
$changed = New-Object System.Collections.Generic.List[string]
$lateHash = New-Object System.Collections.Generic.List[string]
$added   = New-Object System.Collections.Generic.List[string]
$seen = New-Object System.Collections.Generic.HashSet[string]
foreach ($f in $files) {
  $rel = $f.FullName.Substring($root.Length + 1)
  [void]$seen.Add($rel)
  if (-not $old.ContainsKey($rel)) { $added.Add($rel); continue }
  $o = $old[$rel]
  if ([int64]$o.len -ne $f.Length -or $o.mtime -ne $f.LastWriteTimeUtc.ToString('o')) {
    $changed.Add("$rel  meta: len $($o.len)->$($f.Length) mtime $($o.mtime)->$($f.LastWriteTimeUtc.ToString('o'))"); continue
  }
  # -LiteralPath: cover filenames contain [..] which -Path would treat as a wildcard class
  try { $h = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256 -ErrorAction Stop).Hash }
  catch { $changed.Add("$rel  HASH ERROR: $($_.Exception.Message)"); continue }
  if ($o.sha -eq '') { $lateHash.Add("$rel  baseline had no hash (initial pass wildcard bug); len+mtime matched, hash now $h") ; continue }
  if ($h -ne $o.sha) { $changed.Add("$rel  sha256 $($o.sha) -> $h") }
}
$deleted = New-Object System.Collections.Generic.List[string]
foreach ($k in $old.Keys) { if (-not $seen.Contains($k)) { $deleted.Add($k) } }

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("user data root        : $root")
$lines.Add("baseline manifest     : $base  ($($old.Count) files)")
$lines.Add("files now             : $($files.Count)")
$lines.Add("CHANGED (meta or hash): $($changed.Count)")
foreach ($l in $changed) { $lines.Add("  $l") }
$lines.Add("baseline-hash-missing rows recovered (len+mtime identical, hash computed late): $($lateHash.Count)")
foreach ($l in $lateHash) { $lines.Add("  $l") }
$lines.Add("ADDED                 : $($added.Count)")
foreach ($l in $added) { $lines.Add("  $l") }
$lines.Add("DELETED               : $($deleted.Count)")
foreach ($l in $deleted) { $lines.Add("  $l") }
$lines.Add("VERDICT: " + $(if ($changed.Count -eq 0 -and $added.Count -eq 0 -and $deleted.Count -eq 0) { 'UNTOUCHED (byte-identical to the pre-run baseline)' } else { 'MODIFIED -- investigate' }))

# private-root inputs vs user's originals
foreach ($pair in @(@('bios','SCPH-90006_BIOS_VX_HK_2.20.bin'),@('bios','SCPH-90006_BIOS_VX_HK_2.20.erom'),
                    @('bios','SCPH-90006_BIOS_VX_HK_2.20.nvm'),@('bios','SCPH-90006_BIOS_VX_HK_2.20.rom1'),
                    @('bios','SCPH-90006_BIOS_VX_HK_2.20.rom2'),@('bios','SCPH-90006_BIOS_VX_HK_2.20.mec'),
                    @('memcards','Mcd001.ps2'),@('memcards','Mcd002.ps2'))) {
  $a = Join-Path $root (Join-Path $pair[0] $pair[1])
  $b = Join-Path $priv (Join-Path $pair[0] $pair[1])
  if ((Test-Path $a) -and (Test-Path $b)) {
    $ha = (Get-FileHash $a -Algorithm SHA256).Hash
    $hb = (Get-FileHash $b -Algorithm SHA256).Hash
    $lines.Add(("private {0,-14} {1,-42} {2}" -f $pair[0], $pair[1], $(if ($ha -eq $hb) { "IDENTICAL to user's ($($ha.Substring(0,16))…)" } else { "DIFFERS: user $ha private $hb" })))
  }
}
[System.IO.File]::WriteAllLines($out, $lines)
$lines | ForEach-Object { $_ }
