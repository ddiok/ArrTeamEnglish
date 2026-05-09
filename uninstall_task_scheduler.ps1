$ErrorActionPreference = "Stop"

$TaskName = "ArrTeamEnglishBot"

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    "Removed task: $TaskName"
} else {
    "Task not found: $TaskName"
}
