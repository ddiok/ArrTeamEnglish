$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = "C:\Program Files\Python312\python.exe"
$LogDir = Join-Path $ProjectDir "logs"
$StdOutLog = Join-Path $LogDir "bot.out.log"
$StdErrLog = Join-Path $LogDir "bot.err.log"

if (-not (Test-Path -LiteralPath $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

Set-Location -LiteralPath $ProjectDir

& $PythonExe (Join-Path $ProjectDir "bot.py") 1>> $StdOutLog 2>> $StdErrLog
