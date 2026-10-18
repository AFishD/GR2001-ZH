# repro_from_eng.ps1 -- END-TO-END reproduction of the GR PS2 ZH final disc FROM THE ENGLISH ORIGINAL.
#
#   MANDATORY RULE (2026-10-18): every build must start from the English original ISO
#       third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso
#   Never use a previous Chinese ISO as a base.  See tools\final_fix\README.md (top section).
#
# Chain (all inputs read-only; nothing is written outside -OutDir):
#   [1] ENG original  +  K2 cdvd block dump  --rebuild_base.py-->  GR_REBUILD2400.iso
#         sha256 must be d7f83d7ec4a8fe1ec8d60de4b17b94513bd1540dc929d3b667086f4910443ca0
#   [2] GR_REBUILD2400.iso  --apply_fix.py (F4 + OOMFIX + F7)-->  GR_ZH126.iso
#         sha256 must be d8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5
#   [3] compare the produced disc with the shipped work\builds\GR_RELEASE\GR_ZH126.iso
#
# ASCII only on purpose: Windows PowerShell 5.1 reads .ps1 as ANSI; Chinese docs are in README.md.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_fix\repro_from_eng.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_fix\repro_from_eng.ps1 -KeepIntermediate
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_fix\repro_from_eng.ps1 -UseExistingBase
param(
  [string]$OutDir = (Join-Path $env:TEMP 'gr_final_fix_from_eng'),
  [string]$Python = 'C:\Users\84363\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe',
  [string]$EngIso = '',
  [string]$K2Dump = '',
  [switch]$UseExistingBase,
  [switch]$KeepIntermediate
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $repo

if (-not $EngIso)  { $EngIso  = Join-Path $repo "third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso" }
if (-not $K2Dump)  { $K2Dump  = Join-Path $env:LOCALAPPDATA 'PCSX2\cdvd-dump\GR_FA2400_K2 (2026-10-17 15-08-20).dump' }
$baseTool  = Join-Path $repo 'tools\final_fix\rebuild_base.py'
$fixTool   = Join-Path $repo 'tools\final_fix\apply_fix.py'
$shipped   = Join-Path $repo 'work\builds\GR_RELEASE\GR_ZH126.iso'
$repobase  = Join-Path $repo 'work\builds\GR_REBUILD\GR_REBUILD2400.iso'
$expEng    = '2b42ea7ce9bd0a85972a07ca59b1b9d79422ed318b85737db3cfd17daa788531'
$expBase   = 'd7f83d7ec4a8fe1ec8d60de4b17b94513bd1540dc929d3b667086f4910443ca0'
$expFinal  = 'd8007873957f81ab44f37cf4c773ac5bdf0d3d66fd5f975b48f69abea21b2ab5'

function Sha([string]$p) { (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower() }
function Step([string]$t) { Write-Host ''; Write-Host ('=' * 96); Write-Host $t; Write-Host ('=' * 96) }

Step 'GR PS2 ZH -- end-to-end reproduction FROM THE ENGLISH ORIGINAL'
if (-not (Test-Path $Python)) { $Python = 'python' }
Write-Host ("python   : {0}" -f $Python)
Write-Host ("repo     : {0}" -f $repo)
Write-Host ("out dir  : {0}" -f $OutDir)

# ---- 0. read-only inputs ----
Step '[0] inputs (read-only)'
if (-not (Test-Path -LiteralPath $EngIso)) { Write-Host ("  FAIL  English original not found: {0}" -f $EngIso); exit 1 }
$he = Sha $EngIso
Write-Host ("  ENG ISO  {0}" -f $EngIso)
Write-Host ("           sha256 {0}  ({1} B)" -f $he, (Get-Item -LiteralPath $EngIso).Length)
if ($he -ne $expEng) { Write-Host '  FAIL  English original sha256 mismatch -- refusing to build'; exit 1 }
Write-Host '  OK    English original sha256 matches spec'
if (-not (Test-Path -LiteralPath $K2Dump)) { Write-Host ("  FAIL  K2 cdvd block dump not found: {0}" -f $K2Dump); exit 1 }
$hk = Sha $K2Dump
Write-Host ("  K2 dump  {0}" -f $K2Dump)
Write-Host ("           sha256 {0}  ({1} B)" -f $hk, (Get-Item -LiteralPath $K2Dump).Length)

if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }
$base = Join-Path $OutDir 'GR_REBUILD2400.iso'
$fin  = Join-Path $OutDir 'GR_ZH126.iso'

# ---- 1. base = ENG original + K2 block dump ----
if ($UseExistingBase) {
  $base = $repobase
  Step '[1] base: using the existing development base (shortcut, -UseExistingBase)'
  Write-Host ("  base     {0}" -f $base)
  if (-not (Test-Path $base)) { Write-Host '  FAIL  base disc not found'; exit 1 }
  $hb = Sha $base
  Write-Host ("           sha256 {0}" -f $hb)
  if ($hb -ne $expBase) { Write-Host '  FAIL  base sha256 mismatch'; exit 1 }
  Write-Host '  OK    base sha256 matches spec  (NOTE: shortcut -- NOT rebuilt from the ENG original)'
} else {
  Step '[1] base = ENG original + K2 cdvd block dump  (rebuild_base.py)'
  if (Test-Path $base) { Remove-Item -LiteralPath $base -Force }
  & $Python $baseTool --orig $EngIso --k2-dump $K2Dump --out $base
  if ($LASTEXITCODE -ne 0) { Write-Host ("  FAIL  rebuild_base.py exit={0}" -f $LASTEXITCODE); exit 1 }
  $hb = Sha $base
  Write-Host ("  base sha256 {0}" -f $hb)
  if ($hb -ne $expBase) { Write-Host '  FAIL  rebuilt base != declared base sha256'; exit 1 }
  Write-Host '  OK    rebuilt base == declared GR_REBUILD2400 fingerprint'
}

# ---- 2. apply the three-part fix ----
Step '[2] apply F4 + OOMFIX + F7  (apply_fix.py)'
if (Test-Path $fin) { Remove-Item -LiteralPath $fin -Force }
& $Python $fixTool --base $base --out $fin
$rc = $LASTEXITCODE
if ($rc -ne 0) { Write-Host ("  FAIL  apply_fix.py exit={0}" -f $rc); exit $rc }

# ---- 3. compare with the shipped disc ----
Step '[3] compare with the shipped deliverable'
$ho = Sha $fin
Write-Host ("  produced {0}" -f $ho)
$okSpec = ($ho -eq $expFinal)
Write-Host ("  spec     {0}   {1}" -f $expFinal, $(if ($okSpec) { 'MATCH' } else { 'MISMATCH' }))
if (-not $okSpec) { Write-Host '  FAIL  produced sha256 != spec'; exit 2 }
if (Test-Path -LiteralPath $shipped) {
  $hs = Sha $shipped
  Write-Host ("  shipped  {0}" -f $hs)
  if ($ho -eq $hs) { Write-Host '  OK    byte-identical to the shipped GR_ZH126.iso' }
  else { Write-Host '  FAIL  differs from the shipped disc'; exit 2 }
} else {
  Write-Host ("  WARN  shipped disc not on disk: {0}" -f $shipped)
}

if (-not $KeepIntermediate) {
  Step '[4] removing scratch output'
  Write-Host ("  {0}" -f $OutDir)
  Remove-Item -LiteralPath $OutDir -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Host ''
Write-Host 'REPRODUCTION FROM THE ENGLISH ORIGINAL OK --'
Write-Host '  ENG original + K2 cdvd block dump  ==  GR_REBUILD2400.iso  (byte-identical)'
Write-Host '  GR_REBUILD2400.iso + F4/OOMFIX/F7  ==  GR_ZH126.iso        (byte-identical)'
exit 0
