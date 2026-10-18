# 并发看门狗: 每 20 秒检查 pcsx2 实例数, 若 >=2 则终止"后起的那个"
# 目的: gsrunner 只能单实例, 后起者会把先起者顶死 (实测两次: cap_94 f23000 / r47before f2300)
# 运行 40 分钟后自动退出
$log = 'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_ZH94\temp\r47\watchdog_concurrency.log'
$deadline = (Get-Date).AddMinutes(40)
"[$(Get-Date -Format 'HH:mm:ss')] 看门狗启动 (运行 40 分钟)" | Out-File -FilePath $log -Append -Encoding utf8
$killed = 0
while ((Get-Date) -lt $deadline) {
    $ps = Get-Process pcsx2-gsrunner -EA SilentlyContinue | Sort-Object StartTime
    if ($ps -and @($ps).Count -ge 2) {
        $newest = @($ps)[-1]
        $oldest = @($ps)[0]
        "[$(Get-Date -Format 'HH:mm:ss')] 检测到 $($ps.Count) 个实例; 保先杀后 => 终止 PID $($newest.Id) (启动 $($newest.StartTime.ToString('HH:mm:ss'))), 保留 PID $($oldest.Id) (启动 $($oldest.StartTime.ToString('HH:mm:ss')))" | Out-File -FilePath $log -Append -Encoding utf8
        try { Stop-Process -Id $newest.Id -Force; $killed++ } catch { "[$(Get-Date -Format 'HH:mm:ss')] 终止失败: $_" | Out-File -FilePath $log -Append -Encoding utf8 }
    }
    Start-Sleep -Seconds 20
}
"[$(Get-Date -Format 'HH:mm:ss')] 看门狗退出, 共终止 $killed 次" | Out-File -FilePath $log -Append -Encoding utf8
