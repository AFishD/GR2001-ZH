# clean_work_builds.ps1 -- retire the per-version build folders; keep only the
# release ISO, the live forensic toolkit and the RE toolchain.
# ASCII only.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\maint\clean_work_builds.ps1 [-Apply]
#
# KEEP (and why):
#   work\builds\GR_RELEASE\GR_ZH126.iso   the delivered product (sha256 d8007873..1b2ab5)
#   work\builds\GR_HOOKEMU_QT2\**         live forensic toolkit - user forbade touching it
#   work\_cleanup_manifest_20261018.txt   the cleanup ledger itself
#   work\temp\NEW_Mem\**                  user-supplied runtime evidence (cited read-only by
#                                         REPORT_cave_count_vs_bytes / _save_crash / _zh_heap_corruption / _r84)
#   work\tools\**                         RE toolchain: vendored Ghidra + JDK + Ghidra project DBs
#                                         (derived analysis evidence, not offline-reproducible) + logs;
#                                         15 relocated scripts still read work\tools\ghidra_out etc.
#
# DELETE: every other folder under work\builds (中间盘 / evidence / meta / logs / dumps / screenshots).
param([switch]$Apply)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $root

$KEEP_DIRS = @('GR_HOOKEMU_QT2')
$targets = New-Object System.Collections.Generic.List[object]

foreach ($d in (Get-ChildItem 'work\builds' -Directory -Force)) {
  if ($KEEP_DIRS -contains $d.Name) { continue }
  foreach ($f in (Get-ChildItem $d.FullName -Recurse -File -Force -ErrorAction SilentlyContinue)) {
    if ($d.Name -eq 'GR_RELEASE' -and $f.Name -eq 'GR_ZH126.iso') { continue }   # the product
    $targets.Add($f)
  }
}

$total = ($targets | Measure-Object Length -Sum).Sum
Write-Output ("=== DELETE LIST : {0} files / {1:N2} GB ===" -f $targets.Count, ($total / 1GB))
Write-Output ''
Write-Output '--- per version folder ---'
$targets | Group-Object { ($_.FullName.Substring((Join-Path $root 'work\builds').Length + 1) -split '\\')[0] } |
  ForEach-Object {
    [pscustomobject]@{
      Folder = $_.Name
      Files  = $_.Count
      MB     = [math]::Round((($_.Group | Measure-Object Length -Sum).Sum) / 1MB, 1)
    }
  } | Sort-Object MB -Descending | Format-Table -AutoSize | Out-String -Width 120

$ledger = 'work\_cleanup_manifest_20261018b.txt'
$targets | Sort-Object FullName | ForEach-Object {
  "{0}`t{1}" -f $_.FullName.Substring($root.Length + 1), $_.Length
} | Set-Content -LiteralPath $ledger -Encoding UTF8
Write-Output ("full manifest -> {0}" -f $ledger)
Write-Output ''

if (-not $Apply) { Write-Output 'REPORT ONLY. Re-run with -Apply to delete.'; exit 0 }

# delete deepest-first so directories become empty before removal.
# CRITICAL: never Remove-Item -Recurse a folder that still holds a KEEP file.
# (2026-10-18 incident: recursing GR_RELEASE deleted the shipped GR_ZH126.iso.)
$PROTECT = @()
$isoPath = Join-Path $root 'work\builds\GR_RELEASE\GR_ZH126.iso'
if (Test-Path -LiteralPath $isoPath) { $PROTECT += $isoPath }

$dirs = New-Object System.Collections.Generic.List[object]
foreach ($d in (Get-ChildItem 'work\builds' -Directory -Force)) {
  if ($KEEP_DIRS -contains $d.Name) { continue }
  foreach ($sub in (Get-ChildItem $d.FullName -Recurse -Directory -Force -ErrorAction SilentlyContinue)) { $dirs.Add($sub) }
  $dirs.Add($d)
}
# drop any directory that is an ancestor of a protected file
$dirs = $dirs | Where-Object {
  $dn = $_.FullName
  -not ($PROTECT | Where-Object { $_ -like ($dn + '\*') })
}
foreach ($f in $targets) {
  if ($PROTECT -contains $f.FullName) { continue }
  Remove-Item -LiteralPath $f.FullName -Force -ErrorAction SilentlyContinue
}
$dirs | Sort-Object { $_.FullName.Length } -Descending | ForEach-Object {
  if (Test-Path -LiteralPath $_.FullName) {
    Remove-Item -LiteralPath $_.FullName -Force -Recurse -ErrorAction SilentlyContinue
  }
}
# put the product back-safe: it was never a target
Write-Output ''
Write-Output '--- after ---'
$w = Get-ChildItem 'work' -Recurse -File -Force -ErrorAction SilentlyContinue
Write-Output ("work\ files = {0}   size = {1:N2} GB" -f $w.Count, (($w | Measure-Object Length -Sum).Sum / 1GB))
$iso = Get-Item 'work\builds\GR_RELEASE\GR_ZH126.iso' -ErrorAction SilentlyContinue
Write-Output ("release ISO present = {0}  ({1} B)" -f [bool]$iso, $(if ($iso) { $iso.Length } else { 0 }))
$h = Get-ChildItem 'work\builds\GR_HOOKEMU_QT2' -Recurse -File -Force -ErrorAction SilentlyContinue
Write-Output ("GR_HOOKEMU_QT2 files = {0}" -f $h.Count)
