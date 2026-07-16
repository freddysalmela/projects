# Creates a shortcut in your Windows Startup folder so Gaia launches at login.
# No admin rights required.
# Usage: Right-click -> "Run with PowerShell"

$boosterDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcher     = Join-Path $boosterDir "gaia_autostart.bat"
$startupDir   = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupDir "Gaia Assistant.lnk"

$shell        = New-Object -ComObject WScript.Shell
$shortcut     = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath      = $launcher
$shortcut.WorkingDirectory = $boosterDir
$shortcut.WindowStyle     = 1  # Normal window (visible console)
$shortcut.Description     = "Gaia Voice Assistant"
$shortcut.Save()

Write-Host ""
Write-Host "Done! Shortcut created:" -ForegroundColor Green
Write-Host "  $shortcutPath"
Write-Host ""
Write-Host "Gaia will start automatically at next login."
Write-Host "To remove autostart: delete the shortcut above, or run:"
Write-Host "  Remove-Item '$shortcutPath'"
Write-Host ""
Pause
