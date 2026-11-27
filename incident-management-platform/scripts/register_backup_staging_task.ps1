#requires -Version 5.1
[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
$taskName = "Incident Staging - Backup PostgreSQL"
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$scriptPath = Join-Path $PSScriptRoot "backup_staging.ps1"
if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) { throw "Backup script not found." }
$powerShellPath = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$action = New-ScheduledTaskAction -Execute $powerShellPath -Argument ('-NoProfile -NonInteractive -File "{0}"' -f $scriptPath) -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -Daily -At "02:00"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
# Docker Desktop requires the current user's interactive Windows session.
# No saved password, elevation, or execution-policy bypass is needed.
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$existing = Get-ScheduledTask -TaskName $taskName -TaskPath "\" -ErrorAction SilentlyContinue
if ($existing) {
    if ($existing.State -eq "Running") { throw "Backup task is running; retry registration after completion." }
    Set-ScheduledTask -TaskName $taskName -TaskPath "\" -Action $action -Trigger $trigger -Settings $settings -Principal $principal | Out-Null
}
else {
    Register-ScheduledTask -TaskName $taskName -TaskPath "\" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Daily staging PostgreSQL custom archive, verified and logged locally." | Out-Null
}
Get-ScheduledTask -TaskName $taskName -TaskPath "\" | Select-Object TaskName, State
Get-ScheduledTaskInfo -TaskName $taskName -TaskPath "\" | Select-Object NextRunTime, LastRunTime, LastTaskResult
