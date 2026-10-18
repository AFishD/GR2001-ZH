# make_synced_root.ps1 -- build a PRIVATE, user-equivalent PCSX2 data root for GR_SYNC.
#
# Reads (read-only):  %LOCALAPPDATA%\PCSX2\inis\PCSX2.ini, bios\, memcards\, patches\, cheats\
# Writes (only here): work\builds\GR_SYNC\data\**
#
# The user's data root is NEVER written to: every copy is a read.
# Rewrites performed on the copied ini (recorded in data\_sync\ini_rewrites.diff):
#   * [Folders]           -> absolute paths inside this private root
#   * BlockDumpSaveDirectory -> private root (the user's value points at their own %LOCALAPPDATA%)
#   * Adapter             -> removed (it names the *user's* GPU; the host GPUs differ)
#
# usage: powershell -NoProfile -ExecutionPolicy Bypass -File make_synced_root.ps1
$ErrorActionPreference = 'Stop'

$UserRoot = Join-Path $env:LOCALAPPDATA 'PCSX2'
# NOTE: pcsx2-qt's '-datapath X' does NOT use X as the data root: EmuFolders::SetDataDirectory()
# does DataRoot = X\PCSX2 (Pcsx2Config.cpp:2252). So the private root is the PCSX2 subdirectory,
# and the launcher must pass -datapath <parent>.
$PrivBase = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_SYNC\data'
$Priv     = Join-Path $PrivBase 'PCSX2'
$GsrExe   = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_REPRO\emu\gsrunner\pcsx2-gsrunner.exe'

if (-not (Test-Path $UserRoot)) { throw "user data root not found: $UserRoot" }

# --- 0. folders -----------------------------------------------------------------
$dirs = @('inis','bios','memcards','patches','cheats','cheats_ws','gamesettings','logs','sstates',
          'cache','snaps','textures','covers','inputprofiles','videos','cdvd-dump','_sync','_runs')
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path (Join-Path $Priv $d) | Out-Null }

# --- 1. ini (copy + rewrite) ----------------------------------------------------
$srcIni = Join-Path $UserRoot 'inis\PCSX2.ini'
$dstIni = Join-Path $Priv 'inis\PCSX2.ini'
$raw = [System.IO.File]::ReadAllText($srcIni)

function Set-IniValue([string]$text, [string]$section, [string]$key, [string]$value) {
  $lines = $text -split "`r?`n"
  $out = New-Object System.Collections.Generic.List[string]
  $inSec = $false; $done = $false
  foreach ($l in $lines) {
    $t = $l.Trim()
    if ($t -match '^\[(.+)\]$') {
      if ($inSec -and -not $done) { $out.Add("$key = $value"); $done = $true }
      $inSec = ($Matches[1] -eq $section)
      $out.Add($l); continue
    }
    if ($inSec -and $t -match "^$([regex]::Escape($key))\s*=") {
      $out.Add("$key = $value"); $done = $true; continue
    }
    $out.Add($l)
  }
  if ($inSec -and -not $done) { $out.Add("$key = $value") }
  return ($out -join "`r`n")
}
function Remove-IniKey([string]$text, [string]$section, [string]$key) {
  $lines = $text -split "`r?`n"
  $out = New-Object System.Collections.Generic.List[string]
  $inSec = $false
  foreach ($l in $lines) {
    $t = $l.Trim()
    if ($t -match '^\[(.+)\]$') { $inSec = ($Matches[1] -eq $section); $out.Add($l); continue }
    if ($inSec -and $t -match "^$([regex]::Escape($key))\s*=") { continue }
    $out.Add($l)
  }
  return ($out -join "`r`n")
}

$before = $raw
# [Folders]: every path becomes absolute inside the private root.
$folderMap = [ordered]@{
  'Bios' = "$Priv\bios"; 'Snapshots' = "$Priv\snaps"; 'Savestates' = "$Priv\sstates";
  'MemoryCards' = "$Priv\memcards"; 'Logs' = "$Priv\logs"; 'Cheats' = "$Priv\cheats";
  'CheatsWS' = "$Priv\cheats_ws"; 'Cache' = "$Priv\cache"; 'Textures' = "$Priv\textures";
  'Patches' = "$Priv\patches"; 'UserResources' = "$Priv\resources"; 'InputProfiles' = "$Priv\inputprofiles";
  'Videos' = "$Priv\videos"; 'Covers' = "$Priv\covers"
}
foreach ($k in $folderMap.Keys) { $raw = Set-IniValue $raw 'Folders' $k $folderMap[$k] }
foreach ($k in @('Patches','UserResources','InputProfiles','Videos','Covers','CheatsWS')) {
  if ($before -notmatch "(?m)^$k\s*=") { $raw = Set-IniValue $raw 'Folders' $k $folderMap[$k] }
}
$raw = Set-IniValue $raw 'EmuCore' 'BlockDumpSaveDirectory' "$Priv\cdvd-dump"
$raw = Remove-IniKey  $raw 'EmuCore/GS' 'Adapter'

$header = @(
  '; ============================================================================',
  '; GR_SYNC private data root -- byte-faithful copy of the user''s official PCSX2 2.8.2',
  '; PCSX2.ini (source: %LOCALAPPDATA%\PCSX2\inis\PCSX2.ini), with ONLY these rewrites:',
  ';   [Folders] *                 -> absolute paths inside this private root',
  ';   [EmuCore] BlockDumpSaveDirectory -> this private root (was the user''s own folder)',
  ';   [EmuCore/GS] Adapter        -> removed (names the user''s GPU; host GPUs differ)',
  '; Never edit this file expecting the user''s tree to change; it is a copy.',
  '; ============================================================================'
) -join "`r`n"
[System.IO.File]::WriteAllText($dstIni, $header + "`r`n" + $raw, [System.Text.UTF8Encoding]::new($false))

# record exactly what changed
[System.IO.File]::WriteAllLines((Join-Path $Priv '_sync\ini_rewrites.diff'),
  (Compare-Object ([System.IO.File]::ReadAllLines($srcIni)) ([System.IO.File]::ReadAllLines($dstIni)) |
    ForEach-Object { "$($_.SideIndicator) $($_.InputObject)" }))

# --- 2. BIOS: only the revision the ini selects, plus its companion files --------
$biosName = 'SCPH-90006_BIOS_VX_HK_2.20.bin'
$sec = ''
foreach ($line in [System.IO.File]::ReadAllLines($srcIni)) {
  if ($line -match '^\[(.+)\]$') { $sec = $Matches[1]; continue }
  # case-sensitive key AND section: [Folders] "Bios" must not win over [Filenames] "BIOS"
  if ($sec -ceq 'Filenames' -and $line -cmatch '^\s*BIOS\s*=\s*(.+)$') { $biosName = $Matches[1].Trim() }
}
$stem = [System.IO.Path]::GetFileNameWithoutExtension($biosName)
$biosCopied = @()
foreach ($f in Get-ChildItem (Join-Path $UserRoot 'bios') -File) {
  if ($f.Name -ieq $biosName -or $f.BaseName -ieq $stem) {
    Copy-Item $f.FullName (Join-Path $Priv 'bios') -Force
    $biosCopied += $f.Name
  }
}

# --- 3. memory cards (both slots the ini enables) --------------------------------
$mcCopied = @()
foreach ($m in @('Slot1_Filename','Slot2_Filename')) {
  foreach ($line in [System.IO.File]::ReadAllLines($srcIni)) {
    if ($line -match "^\s*$m\s*=\s*(.+)$") {
      $name = $Matches[1].Trim()
      if ($name -ne '') {
        $p = Join-Path $UserRoot "memcards\$name"
        if (Test-Path $p) { Copy-Item $p (Join-Path $Priv 'memcards') -Force; $mcCopied += $name }
      }
    }
  }
}

# --- 4. patches / cheats (verbatim; may be empty) --------------------------------
$patches = @(Get-ChildItem (Join-Path $UserRoot 'patches') -File -Recurse -ErrorAction SilentlyContinue)
if ($patches.Count) { Copy-Item (Join-Path $UserRoot 'patches\*') (Join-Path $Priv 'patches') -Recurse -Force }
$cheats = @(Get-ChildItem (Join-Path $UserRoot 'cheats') -File -Recurse -ErrorAction SilentlyContinue)
if ($cheats.Count) { Copy-Item (Join-Path $UserRoot 'cheats\*') (Join-Path $Priv 'cheats') -Recurse -Force }

# --- 5. settings-sync key list for gsrunner -grsetting ---------------------------
# Emit every integer/bool key of the *user's* ini whose name our gsrunner binary
# actually contains as a C string (a key the binary does not read is dead and must
# not be "synced", otherwise we would claim a setting took effect when it cannot).
$blob = [System.Text.Encoding]::ASCII.GetString([System.IO.File]::ReadAllBytes((Resolve-Path $GsrExe)))
$wanted = @('EmuCore','EmuCore/Speedhacks','EmuCore/CPU','EmuCore/CPU/Recompiler','EmuCore/Gamefixes',
            'Framerate','EmuCore/GS','Logging')
$sec = ''; $rows = New-Object System.Collections.Generic.List[string]; $skipped = New-Object System.Collections.Generic.List[string]
foreach ($line in [System.IO.File]::ReadAllLines($dstIni)) {
  $t = $line.Trim()
  if ($t -match '^\[(.+)\]$') { $sec = $Matches[1]; continue }
  if ($t -eq '' -or $t.StartsWith(';') -or $t.StartsWith('#')) { continue }
  $i = $t.IndexOf('='); if ($i -lt 0) { continue }
  $k = $t.Substring(0,$i).Trim(); $v = $t.Substring($i+1).Trim()
  if ($wanted -notcontains $sec) { continue }
  if ($k -eq 'Adapter') { continue }
  $num = $null
  if     ($v -match '^-?\d+$')      { $num = $v }
  elseif ($v -ieq 'true')           { $num = '1' }
  elseif ($v -ieq 'false')          { $num = '0' }
  else { $skipped.Add("$sec/$k = $v (non-numeric)"); continue }
  if (-not $blob.Contains($k + [char]0)) { $skipped.Add("$sec/$k = $v (DEAD: absent from gsrunner binary)"); continue }
  $rows.Add("$sec`t$k`t$num")
}
[System.IO.File]::WriteAllLines((Join-Path $Priv '_sync\grsetting_sync.tsv'), $rows)
[System.IO.File]::WriteAllLines((Join-Path $Priv '_sync\grsetting_skipped.txt'), $skipped)

# --- 6. provenance manifest ------------------------------------------------------
$manifest = New-Object System.Collections.Generic.List[string]
$manifest.Add("source_root`t$UserRoot")
$manifest.Add("source_ini`t$srcIni")
$manifest.Add("bios_selected`t$biosName")
foreach ($f in Get-ChildItem $Priv -Recurse -File) {
  $rel = $f.FullName.Substring($Priv.Length + 1)
  $h = (Get-FileHash $f.FullName -Algorithm SHA256).Hash
  $manifest.Add("$rel`t$($f.Length)`t$h")
}
[System.IO.File]::WriteAllLines((Join-Path $Priv '_sync\manifest.tsv'), $manifest)

Write-Output "private root : $Priv"
Write-Output "bios copied  : $($biosCopied -join ', ')"
Write-Output "mcards copied: $($mcCopied -join ', ')"
Write-Output "patches      : $($patches.Count)  cheats: $($cheats.Count)"
Write-Output "grsetting rows: $($rows.Count)  skipped: $($skipped.Count)"
