$ErrorActionPreference = "Stop"

$TaskName = "ArrTeamEnglishBot"

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    "Задача удалена: $TaskName"
} else {
    "Задача не найдена: $TaskName"
}
