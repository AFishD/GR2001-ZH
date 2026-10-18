# run_synced.ps1 -- run the GR_* research emulator with the USER'S OFFICIAL PCSX2 settings.
#
# Two engines, one settings source (the private root work\builds\GR_SYNC\data):
#
#   -Engine gsrunner  (default) : the same pcsx2-gsrunner.exe the GR repro used, but with
#                                 every live setting of the user's PCSX2.ini applied:
#                                   * -ini <priv>\inis\PCSX2.ini   -> whole [EmuCore/GS] section
#                                   * -grsetting <sec> <key> <n>   -> every other live core key
#                                 (gsrunner itself loads NO ini: it builds an in-memory settings
#                                  object from compiled defaults, so without these flags our runs
#                                  silently ran with MTVU on / native resolution, not the user's.)
#   -Engine qt        : the hooked pcsx2-qt.exe with '-datapath <priv>', i.e. the literal
#                       private-data-root mechanism. -Settings does not apply here (the ini is
#                       read verbatim). Used to PROVE the private root is what gets used and
#                       that the user's own tree is never written.
#
# usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File run_synced.ps1 -RunName s01_synced_l1
#   ... -RunName b01_base_l1   -Settings baseline
#   ... -RunName qt_readback   -Engine qt -QtMode testconfig
#
# Discipline built in: read-only on %LOCALAPPDATA%\PCSX2 (a fingerprint is taken before and
# after every run), exclusive emulator use (refuses to start if any pcsx2* is alive, and never
# kills a foreign instance), per-run copies of BIOS/memory cards so the private root stays
# byte-identical between arms.
param(
  [Parameter(Mandatory=$true)][string]$RunName,
  [ValidateSet('synced','baseline')][string]$Settings = 'synced',
  [ValidateSet('gsrunner','qt')][string]$Engine = 'gsrunner',
  [ValidateSet('run','testconfig')][string]$QtMode = 'run',
  [string]$InputFile = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_REPRO\r03_l1_memwatch\in_l1_f30.txt',
  [string]$State     = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_REPRO\common\state_LAY_fix1_bytecount.p2s',
  [string]$Iso       = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso',
  [int]$MaxFrames    = 60,
  # addr:size pairs, DECIMAL addresses (this build's -grwatch and -grmemwatch parse "0x.." as 0).
  # The task quotes both hex and decimal labels for the three code addresses and they disagree
  # (0x005391BC=5476796 but the given decimal 5480892=0x0053A1BC, ...), so both forms are watched,
  # plus 0x1300/256 (4864) -- the low-RAM burst region that provably gets rewritten at frame 44 --
  # plus 5617584 (0x55B7F0) which is the address the earlier r11 run watched.
  [string[]]$WatchPairs = @('4864:256','5480892:4','4213180:4','5613472:4','5476796:4','4209084:4','5617568:4','5617584:4'),
  [int[]]$DumpWin    = @(40,46),
  [switch]$NoWatch,
  [switch]$NoDumpWin,
  [int]$QtSeconds    = 25,
  # -IniOnly: apply ONLY '-ini <IniPath>' (no -grsetting). Used to prove the -ini mechanism
  # actually reaches the emulator core, by pointing it at a probe copy with a logged key changed.
  [switch]$IniOnly,
  [string]$IniPath   = '',
  [string[]]$ExtraArgs = @(),
  # calibration probe: force the GS renderer through the *proven* -grsetting path
  [switch]$ProbeSwRenderer,
  # single-key bisection: "section;key;value" triples joined by '|' (booleans only -- see report:
  # -grsetting clobbers integer keys, so integer keys must go through -ini)
  [string]$SingleSetting = ''
)
$ErrorActionPreference = 'Stop'

$Root     = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
$PrivBase = Join-Path $Root 'work\builds\GR_SYNC\data'      # what -datapath gets
$Priv     = Join-Path $PrivBase 'PCSX2'                     # the real DataRoot (-datapath X => X\PCSX2)
$RunDir   = Join-Path $Root "work\builds\GR_SYNC\runs\$RunName"
$GsrExe   = Join-Path $Root 'work\builds\GR_REPRO\emu\gsrunner\pcsx2-gsrunner.exe'
$QtExe    = Join-Path $Root 'work\builds\GR_HOOKEMU\qt\pcsx2-qt.exe'
$UserRoot = Join-Path $env:LOCALAPPDATA 'PCSX2'
$PrivIni  = Join-Path $Priv 'inis\PCSX2.ini'
$SyncTsv  = Join-Path $Priv '_sync\grsetting_sync.tsv'

function Get-UserFingerprint {
  # cheap but sensitive: per-file (len,mtime) over the whole user tree + hashes of the ini/sstates
  $files = Get-ChildItem $UserRoot -Recurse -File -Force -ErrorAction SilentlyContinue
  $h = [System.Security.Cryptography.SHA256]::Create()
  $sb = New-Object System.Text.StringBuilder
  foreach ($f in ($files | Sort-Object FullName)) {
    [void]$sb.Append($f.FullName).Append('|').Append($f.Length).Append('|').Append($f.LastWriteTimeUtc.Ticks).Append("`n")
  }
  $joined = $sb.ToString()
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($joined)
  $tree = [System.BitConverter]::ToString($h.ComputeHash($bytes)).Replace('-','')
  $ini  = (Get-FileHash (Join-Path $UserRoot 'inis\PCSX2.ini') -Algorithm SHA256).Hash
  return [pscustomobject]@{ files=$files.Count; tree=$tree; ini=$ini }
}

# ---- guards -------------------------------------------------------------------
$others = @(Get-Process -Name 'pcsx2*' -ErrorAction SilentlyContinue)
if ($others.Count -gt 0) {
  $ids = ($others | ForEach-Object { "$($_.Id):$($_.ProcessName)" }) -join ', '
  throw "another pcsx2 instance is running ($ids) -- refusing to start (exclusive-use rule; never kill a foreign instance)"
}
foreach ($p in @($GsrExe,$QtExe,$PrivIni,$State,$Iso,$SyncTsv)) {
  if (-not (Test-Path $p)) { throw "missing required file: $p" }
}
if ($Settings -eq 'synced' -and -not (Test-Path $InputFile)) { throw "missing input table: $InputFile" }

if (Test-Path $RunDir) { Remove-Item $RunDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null
# per-run copies: the private root stays byte-identical between arms (sha-verified in _sync)
Copy-Item (Join-Path $Priv 'bios')     (Join-Path $RunDir 'bios') -Recurse -Force
Copy-Item (Join-Path $Priv 'memcards') (Join-Path $RunDir 'mc')   -Recurse -Force

$before = Get-UserFingerprint

# ---- build the argv -----------------------------------------------------------
if ($Engine -eq 'qt') {
  $logfile = Join-Path $RunDir 'emulog.txt'
  $argv = @('-datapath', $PrivBase, '-logfile', $logfile)
  if ($QtMode -eq 'testconfig') {
    $argv += '-testconfig'
  } else {
    $argv += @('-nogui','-batch','-fastboot','-statefile',$State,'--',$Iso)
  }
  $exe = $QtExe
} else {
  $argv = @('-grdumpdir',$RunDir,'-grmaxframes',"$MaxFrames",'-grpcsample','1')
  if (-not $NoWatch) {
    foreach ($wp in $WatchPairs) {
      $parts = $wp -split ':'
      if ($parts.Count -lt 2) { continue }
      $argv += @('-grwatch', $parts[0], $parts[1])
    }
  }
  if (-not $NoDumpWin -and $DumpWin.Count -ge 2 -and $MaxFrames -gt 0) { $argv += @('-grdumpwin', "$($DumpWin[0])", "$($DumpWin[1])") }
  $syncCount = 0
  if ($Settings -eq 'synced') {
    $useIni = if ($IniPath -ne '') { $IniPath } else { $PrivIni }
    # whole [EmuCore/GS] section straight out of the user's ini
    $argv += @('-ini', $useIni)
    # every other live core key of the user's ini
    if (-not $IniOnly) {
      foreach ($row in [System.IO.File]::ReadAllLines($SyncTsv)) {
        $c = $row -split "`t"
        if ($c.Count -lt 3) { continue }
        if ($c[0] -eq 'EmuCore/GS') { continue }   # already covered by -ini
        $argv += @('-grsetting', $c[0], $c[1], $c[2])
        $syncCount++
      }
    }
  }
  if ($ProbeSwRenderer) { $argv += @('-grsetting','EmuCore/GS','Renderer','13') }
  if ($SingleSetting -ne '') {
    foreach ($triple in $SingleSetting.Split('|')) {
      $c = $triple.Split(';')
      if ($c.Count -eq 3) { $argv += @('-grsetting', $c[0], $c[1], $c[2]) }
    }
  }
  $argv += $ExtraArgs
  $argv += @('-grinput',$InputFile,
             '-grmemcards',(Join-Path $RunDir 'mc'),
             '-grbios',(Join-Path $RunDir 'bios'),
             '-grbiosname','SCPH-90006_BIOS_VX_HK_2.20.bin',
             '-grstate',$State,
             '-logfile',(Join-Path $RunDir 'emulog.txt'),
             '--',$Iso)
  $exe = $GsrExe
}
$line = '"' + $exe + '" ' + (($argv | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' ')
Set-Content -Path (Join-Path $RunDir 'cmdline.txt') -Value $line -Encoding UTF8
Write-Output "RUN $RunName  engine=$Engine settings=$Settings"
Write-Output $line

# ---- execute ------------------------------------------------------------------
$sw = [System.Diagnostics.Stopwatch]::StartNew()
if ($Engine -eq 'qt' -and $QtMode -eq 'run') {
  # bounded GUI run: we start it, let it run, then stop OUR OWN child (never a foreign process)
  $p = Start-Process -FilePath $exe -ArgumentList $argv -PassThru -WindowStyle Minimized
  $deadline = (Get-Date).AddSeconds($QtSeconds)
  while ((Get-Date) -lt $deadline -and -not $p.HasExited) { Start-Sleep -Milliseconds 500 }
  if (-not $p.HasExited) { Write-Output "(bounded run: stopping our own pid $($p.Id) after ${QtSeconds}s)"; $p.Kill() }
  $p.WaitForExit()
  $code = $p.ExitCode
} else {
  & $exe @argv 1> (Join-Path $RunDir 'stdout.txt') 2> (Join-Path $RunDir 'stderr.txt')
  $code = $LASTEXITCODE
}
$sw.Stop()
$after = Get-UserFingerprint

# ---- report -------------------------------------------------------------------
Write-Output ("exit={0} elapsed={1:n1}s" -f $code, $sw.Elapsed.TotalSeconds)
Write-Output "USER TREE : files $($before.files) -> $($after.files) ; tree-hash $($before.tree.Substring(0,16)) -> $($after.tree.Substring(0,16))"
Write-Output "USER INI  : sha256 $($before.ini.Substring(0,16)) -> $($after.ini.Substring(0,16))"
if ($before.tree -ne $after.tree -or $before.ini -ne $after.ini) {
  Write-Output "!! USER TREE CHANGED -- investigate before trusting this run !!"
} else {
  Write-Output "OK: user data root untouched (identical file set, sizes, mtimes and ini hash)"
}
$evidence = (Get-ChildItem $RunDir -Recurse -File)
$sum = ($evidence | Measure-Object -Property Length -Sum).Sum
Write-Output ("run dir files: {0} ({1:n1} MB)" -f $evidence.Count, ($sum/1MB))
foreach ($f in ($evidence | Sort-Object Length -Descending)) { "  {0,10} {1}" -f $f.Length, $f.FullName.Substring($RunDir.Length + 1) }
