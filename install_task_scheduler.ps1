$ErrorActionPreference = "Stop"

$TaskName = "ArrTeamEnglishBot"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$StartScript = Join-Path $ProjectDir "start_bot.ps1"

if (-not (Test-Path -LiteralPath $StartScript)) {
    throw "Cannot find start script: $StartScript"
}

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$StartScript`"" `
    -WorkingDirectory $ProjectDir

$Trigger = New-ScheduledTaskTrigger -AtLogOn

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Runs ArrTeamEnglish Telegram pronunciation bot at Windows logon." `
    -Force | Out-Null

Start-ScheduledTask -TaskName $TaskName

Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName, State
