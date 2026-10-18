# r71 门禁一键复跑 (构筑后)
$ErrorActionPreference = 'Continue'
$PY = 'C:\ProgramData\anaconda3\python.exe'
$R  = 'work\builds\GR_ZH98\temp\r71'
$ISO_A = 'work\builds\GR_ZH113\GR_ZH113.iso'
$ISO_B = 'work\builds\GR_ZH113_B\GR_ZH113_B.iso'

Write-Host '===== ① check-only (最终产物 + 回读表) ====='
& $PY tools\text_csv\inject_text_csv.py --csv "work\builds\GR_ZH113_B\text" --src $ISO_B --check-only *> "$R\precheck_final.txt"
Write-Host "GATE1_EXIT=$LASTEXITCODE"

Write-Host '===== ★ 逐条自查 ====='
& $PY "$R\r71p_check_final.py" "work\builds\GR_ZH113_B\text" --label 'GR_ZH113_B 最终产物' *> "$R\selfcheck_r71b.txt"
Write-Host "EXIT=$LASTEXITCODE"; Get-Content "$R\selfcheck_r71b.txt" -Encoding UTF8 | Select-Object -Last 6

Write-Host '===== ② 回读 == 表 ====='
& $PY "$R\r71u_readback.py" *> "$R\readback_r71b.txt"
Get-Content "$R\readback_r71b.txt" -Encoding UTF8 | Select-Object -First 6

Write-Host '===== ③ 范围 ====='
& $PY "$R\r71q_scope.py" *> "$R\scope_r71b.txt"
Get-Content "$R\scope_r71b.txt" -Encoding UTF8

Write-Host '===== wrapfix 审计 ====='
& $PY "$R\r71w_wrapaudit.py" *> "$R\wrapaudit_r71b.txt"
Get-Content "$R\wrapaudit_r71b.txt" -Encoding UTF8 | Select-Object -Last 8

Write-Host '===== 引号体检 ====='
& $PY "$R\r71ac_quotes.py" *> "$R\quotes_r71b.txt"
Get-Content "$R\quotes_r71b.txt" -Encoding UTF8

Write-Host '===== ⑥ audit_inventory ====='
& $PY tools\iso_build\audit_inventory.py $ISO_B --missing *> "$R\audit_inventory_r71b.txt"
Get-Content "$R\audit_inventory_r71b.txt" -Encoding UTF8 | Select-Object -Last 4

Write-Host '===== ⑧ 差异归属 ====='
& $PY work\builds\GR_ZH98\temp\r57\diff_attr_r57.py $ISO_A $ISO_B --json "$R\diff_attr_r71b.json" *> "$R\diffattr_r71b.txt"
Get-Content "$R\diffattr_r71b.txt" -Encoding UTF8 | Select-Object -Last 14

Write-Host '===== ⑦ 字库 ====='
& $PY "$R\r71x_fontgate.py" *> "$R\fontgate_r71b.txt"
Get-Content "$R\fontgate_r71b.txt" -Encoding UTF8 | Select-Object -First 8

Write-Host '===== charset 只是盖章 ====='
& $PY "$R\r71y_charsetdelta.py" *> "$R\charsetdelta_r71b.txt"
Get-Content "$R\charsetdelta_r71b.txt" -Encoding UTF8 | Select-Object -Last 4

Write-Host '===== 统计 ====='
& $PY "$R\r71aa_stats.py" *> "$R\stats_r71b.txt"
Get-Content "$R\stats_r71b.txt" -Encoding UTF8 | Select-Object -First 12
