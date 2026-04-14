# Windows タスクスケジューラに 1日1回実行タスクを登録
# PowerShell 管理者権限で実行推奨

$taskName = "sokudoku-auto-issue"
$batPath = "C:\Users\USER\sokudoku-automation\run_daily.bat"
$triggerTime = "09:00"  # 毎日午前9時

# 既存タスクがあれば削除
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# タスクアクション定義
$action = New-ScheduledTaskAction -Execute $batPath

# 毎日9:00トリガー
$trigger = New-ScheduledTaskTrigger -Daily -At $triggerTime

# 設定 (ユーザーログオン不要、バッテリー稼働可、再試行)
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 5)

# ユーザー指定 (ログオン中実行。パスワード不要)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive

# 登録
Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "100万人の速読 新規塾ID自動発行 (毎日 $triggerTime)"

Write-Host ""
Write-Host "登録完了: $taskName"
Write-Host "実行時刻: 毎日 $triggerTime"
Write-Host ""
Write-Host "確認: Get-ScheduledTask -TaskName '$taskName' | Format-List"
Write-Host "手動実行: Start-ScheduledTask -TaskName '$taskName'"
Write-Host "削除:     Unregister-ScheduledTask -TaskName '$taskName'"
