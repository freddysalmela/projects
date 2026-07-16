# Run this once as Administrator to register Gaia as a startup task.
# Usage: Right-click setup_autostart.ps1 -> "Run with PowerShell"

$taskName = "Gaia Assistant"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$launcher  = Join-Path $scriptDir "gaia_autostart.bat"

$action   = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$launcher`"" `
    -WorkingDirectory $scriptDir

$trigger  = New-ScheduledTaskTrigger -AtLogOn

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit 0 `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 2) `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Force | Out-Null

Write-Host ""
Write-Host "Done. Gaia will start automatically at next login." -ForegroundColor Green
Write-Host "To remove: Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false"
Write-Host ""
Pause
