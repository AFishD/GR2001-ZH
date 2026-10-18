# repro.ps1 -- one-click reproduction of the GR PS2 ZH final disc (ASCII only on purpose:
# Windows PowerShell 5.1 reads .ps1 as ANSI, so keep this file ASCII; Chinese docs live in README.md).
#
#   Path A (shortcut, development base):  base GR_REBUILD2400.iso --apply_fix.py--> GR_ZH126.iso
#   Path B (mandatory for release):       English original --rebuild_base.py--> base --apply_fix.py--> GR_ZH126.iso
#           ==> tools\final_fix\repro_from_eng.ps1   (this is the authoritative recipe since 2026-10-18)
#
#   MANDATORY RULE: every build must start from the English original ISO
#   (third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso), never from a previous Chinese ISO.
#   The old path B of this file (work\builds\GR_REBUILD\tools\rb_build.py) needed a deleted
#   intermediate (work\builds\GR_CSFIX\temp\K2_SLUS_206.13.elf) and is therefore retired;
#   rebuild_base.py takes that ELF straight out of the K2 cdvd block dump instead.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_fix\repro.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_fix\repro.ps1 -VerifyOnly
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_fix\repro.ps1 -OutDir D:\tmp\repro
param(
  [string]$OutDir = (Join-Path $env:TEMP 'gr_final_fix_repro'),
  [string]$Python = 'C:\Users\84363\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe',
  [switch]$VerifyOnly,
  [switch]$KeepOutput
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $repo

$base    = Join-Path $repo 'work\builds\GR_REBUILD\GR_REBUILD2400.iso'
$final   = Join-Path $repo 'work\builds\GR_RELEASE\GR_ZH126.iso'
$tool    = Join-Path $repo 'tools\final_fix\apply_fix.py'
$expBase = 'd7f83d7ec4a8fe1ec8d60de4b17b94513bd1540dc929d3b667086f4910443ca0'
$expFin  = 'd8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5'

function Sha([string]$p) { (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower() }

Write-Host '================================================================================'
Write-Host 'GR PS2 ZH -- one-click reproduction (shortcut path A: existing base)'
Write-Host '================================================================================'
if (-not (Test-Path $Python)) { $Python = 'python' }
Write-Host ("python : {0}" -f $Python)
Write-Host ("repo   : {0}" -f $repo)

# ---- 0. prerequisites ----
Write-Host ''
Write-Host '[0] prerequisites'
if (-not (Test-Path $base)) {
  Write-Host ("  FAIL  base disc not found: {0}" -f $base)
  Write-Host '        for the mandatory end-to-end chain from the English original run:'
  Write-Host '        powershell -File tools\final_fix\repro_from_eng.ps1'
  exit 1
}
$hb = Sha $base
Write-Host ("  base   {0}" -f $hb)
if ($hb -ne $expBase) { Write-Host '  FAIL  base sha256 mismatch (refuse to patch an unknown base)'; exit 1 }
Write-Host '  OK    base sha256 matches spec'
if (-not (Test-Path $final)) { Write-Host ("  WARN  deliverable not on disk: {0}" -f $final) }

# ---- 1. verify the deliverable in place ----
if ($VerifyOnly) {
  Write-Host ''
  Write-Host '[1] verify-only: the deliverable disc as it sits on disk'
  & $Python $tool --verify-only --iso $final --base $base
  exit $LASTEXITCODE
}

# ---- 2. rebuild the final disc from the base ----
Write-Host ''
Write-Host '[1] apply the three-part fix to a fresh copy of the base'
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }
$out = Join-Path $OutDir 'GR_ZH126.iso'
if (Test-Path $out) { Remove-Item -LiteralPath $out -Force }
& $Python $tool --base $base --out $out
$rc = $LASTEXITCODE

# ---- 3. byte-compare the rebuild against the deliverable ----
Write-Host ''
Write-Host '[2] compare the rebuild with the shipped deliverable'
if ($rc -ne 0) { Write-Host ("  FAIL  apply_fix.py exit={0}" -f $rc); exit $rc }
$ho = Sha $out
Write-Host ("  rebuilt  {0}" -f $ho)
if (Test-Path $final) {
  $hf = Sha $final
  Write-Host ("  shipped  {0}" -f $hf)
  if ($ho -eq $hf) { Write-Host '  OK    byte-identical to the shipped disc' }
  else { Write-Host '  FAIL  rebuild differs from the shipped disc'; exit 2 }
} else {
  if ($ho -eq $expFin) { Write-Host '  OK    rebuild sha256 == spec sha256' } else { Write-Host '  FAIL  sha256 != spec'; exit 2 }
}

if (-not $KeepOutput) {
  Write-Host ''
  Write-Host ("[3] removing scratch output {0}" -f $OutDir)
  Remove-Item -LiteralPath $OutDir -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Host ''
Write-Host 'REPRODUCTION OK -- the shipped GR_ZH126.iso is exactly base + F4/OOMFIX/F7.'
exit 0
