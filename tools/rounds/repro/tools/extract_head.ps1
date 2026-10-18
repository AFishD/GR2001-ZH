# GR_REPRO: bounded extractor for a flood-sized emulog.
# Reads only the first -HeadBytes of a huge log, finds the first TLB Miss / Trap exception,
# and writes: <out>_head.txt (everything before the storm) + <out>_trigger.txt (context + storm start).
param(
  [Parameter(Mandatory=$true)][string]$Path,
  [Parameter(Mandatory=$true)][string]$OutPrefix,
  [int]$HeadBytes = 33554432,   # 32 MB
  [int]$ContextBefore = 400,
  [int]$StormLines = 200
)

$fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
try {
  $take = [Math]::Min([int64]$HeadBytes, $fs.Length)
  $buf = New-Object byte[] $take
  $read = 0
  while ($read -lt $take) {
    $n = $fs.Read($buf, $read, [int]($take - $read))
    if ($n -le 0) { break }
    $read += $n
  }
} finally { $fs.Dispose() }

$text = [System.Text.Encoding]::ASCII.GetString($buf, 0, $read)
$lines = $text -split "`n"

$firstIdx = -1
$firstKind = ''
for ($i = 0; $i -lt $lines.Count; $i++) {
  if ($lines[$i] -match 'TLB Miss' -or $lines[$i] -match 'Trap exception') {
    $firstIdx = $i
    $firstKind = if ($lines[$i] -match 'TLB Miss') { 'TLB Miss' } else { 'Trap exception' }
    break
  }
}

$hdr = @()
$hdr += "# extractor: work/builds/GR_REPRO/tools/extract_head.ps1"
$hdr += "# source     : $Path"
$hdr += "# source size: $((Get-Item -LiteralPath $Path).Length) bytes"
$hdr += "# bytes read : $read (head window)"
$hdr += "# lines read : $($lines.Count)"
$hdr += "# first 'TLB Miss'/'Trap exception' at line $($firstIdx + 1) kind='$firstKind'"

Set-Content -LiteralPath "${OutPrefix}_head.txt" -Value ($hdr + $lines[0..([Math]::Min($firstIdx - 1, $lines.Count - 1))]) -Encoding UTF8

if ($firstIdx -ge 0) {
  $from = [Math]::Max(0, $firstIdx - $ContextBefore)
  $to = [Math]::Min($lines.Count - 1, $firstIdx + $StormLines)
  Set-Content -LiteralPath "${OutPrefix}_trigger.txt" -Value ($hdr + $lines[$from..$to]) -Encoding UTF8
  "first match line=$($firstIdx+1) kind=$firstKind"
  "context written: lines $($from+1)..$($to+1)"
} else {
  "no TLB Miss / Trap exception inside the first $read bytes"
}
