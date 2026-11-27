#requires -Version 5.1
[CmdletBinding()]
param(
    # Optional subdirectory of backups/, useful for isolated destination tests.
    [string]$DestinationDirectory,
    [switch]$PreviewRetention
)

$ErrorActionPreference = "Stop"
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$backupRoot = Join-Path $projectRoot "backups"
$logRoot = Join-Path $backupRoot "logs"
$runId = (Get-Date -Format "yyyy-MM-dd_HH-mm-ss") + "_" + [Guid]::NewGuid().ToString("N")
$filename = "staging_$runId.dump"
$remotePath = "/tmp/$filename"
$clock = [Diagnostics.Stopwatch]::StartNew()
$exitCode = 1
$remoteCreated = $false
$partialPath = $null
$lockHandle = $null
$logPath = $null
$containerId = $null

function Write-BackupLog {
    param([string]$Message)
    $line = "{0} {1}" -f [DateTimeOffset]::Now.ToString("o"), $Message
    Write-Host $line
    if ($script:logPath) { Add-Content -LiteralPath $script:logPath -Value $line -Encoding UTF8 }
}

function Invoke-CheckedDocker {
    param([string]$Stage, [string[]]$DockerArguments)
    # Windows PowerShell 5.1 can wrap stderr as ErrorRecord even for successful
    # native programs. Capture it, then explicitly check the process exit code.
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $nativeOutput = @(& $script:dockerPath @DockerArguments 2>&1)
        $nativeCode = $LASTEXITCODE
    }
    finally { $ErrorActionPreference = $previousPreference }
    if ($nativeCode -ne 0) {
        # Do not log arbitrary native output: Compose errors may contain env values.
        throw "Docker failure during '$Stage' (exit code $nativeCode). Check Docker Desktop and staging service availability."
    }
    return $nativeOutput
}

try {
    New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
    $logPath = Join-Path $logRoot ("backup_$runId.log")
    Write-BackupLog "BEGIN environment=staging compose_project=incident-staging service=db"
    $lockHandle = [IO.File]::Open((Join-Path $backupRoot ".backup-staging.lock"), [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)

    if (-not $DestinationDirectory) { $DestinationDirectory = $backupRoot }
    $destination = [IO.Path]::GetFullPath($DestinationDirectory)
    if ($destination -ne $backupRoot -and -not $destination.StartsWith($backupRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Destination must be backups/ or one of its subdirectories."
    }
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    $finalPath = Join-Path $destination $filename
    $partialPath = $finalPath + ".partial"

    $dockerCommand = Get-Command docker.exe -ErrorAction SilentlyContinue
    $dockerPath = if ($dockerCommand) { $dockerCommand.Source } else { Join-Path $env:ProgramFiles "Docker\Docker\resources\bin\docker.exe" }
    if (-not (Test-Path -LiteralPath $dockerPath -PathType Leaf)) { throw "Docker executable not found." }
    $composeFile = Join-Path $projectRoot "compose.staging.yaml"
    $envFile = Join-Path $projectRoot ".env.staging"
    if (-not (Test-Path -LiteralPath $composeFile -PathType Leaf) -or -not (Test-Path -LiteralPath $envFile -PathType Leaf)) {
        throw "Staging Compose configuration or environment file missing."
    }
    $composeArgs = @("compose", "-p", "incident-staging", "-f", $composeFile, "--env-file", $envFile)
    $ids = @(Invoke-CheckedDocker -Stage "locate staging database" -DockerArguments ($composeArgs + @("ps", "-q", "db")))
    if ($ids.Count -ne 1 -or [string]$ids[0] -notmatch "^[a-f0-9]{12,64}$") { throw "Expected exactly one running staging database container." }
    $containerId = [string]$ids[0]
    $labelJson = Invoke-CheckedDocker -Stage "verify container labels" -DockerArguments @("inspect", "--format", "{{json .Config.Labels}}", $containerId)
    $labels = "$labelJson" | ConvertFrom-Json
    if ($labels.'com.docker.compose.project' -ne "incident-staging" -or $labels.'com.docker.compose.service' -ne "db") { throw "Container identity mismatch: refusing backup." }
    $databaseUser = Invoke-CheckedDocker -Stage "read database user" -DockerArguments @("exec", $containerId, "printenv", "POSTGRES_USER")
    $databaseName = Invoke-CheckedDocker -Stage "read database name" -DockerArguments @("exec", $containerId, "printenv", "POSTGRES_DB")
    if ("$databaseName" -ne "incident_management_staging" -or "$databaseUser" -ne "incident_staging") {
        throw "Unexpected staging database identity: refusing backup."
    }
    Write-BackupLog "Target verified: incident-staging/db database=incident_management_staging"
    Write-BackupLog "pg_dump: starting custom archive"
    $remoteCreated = $true
    Invoke-CheckedDocker -Stage "pg_dump" -DockerArguments @("exec", $containerId, "pg_dump", "-U", "$databaseUser", "-d", "$databaseName", "-Fc", "-f", $remotePath) | Out-Null
    Write-BackupLog "pg_dump: OK"
    Invoke-CheckedDocker -Stage "pg_restore --list" -DockerArguments @("exec", $containerId, "pg_restore", "--list", $remotePath) | Out-Null
    Write-BackupLog "Archive validation: pg_restore --list OK"
    $remoteHashLine = Invoke-CheckedDocker -Stage "archive checksum" -DockerArguments @("exec", $containerId, "sha256sum", $remotePath)
    $remoteHash = ("$remoteHashLine" -split "\s+")[0]
    if ($remoteHash -notmatch "^[a-fA-F0-9]{64}$") { throw "Invalid remote SHA256 response." }
    Write-BackupLog "Copy: starting to local .partial file"
    Invoke-CheckedDocker -Stage "copy archive" -DockerArguments @("cp", ($containerId + ":" + $remotePath), $partialPath) | Out-Null
    if (-not (Test-Path -LiteralPath $partialPath -PathType Leaf) -or (Get-Item -LiteralPath $partialPath).Length -le 0) {
        throw "Local archive missing or empty."
    }
    $localHash = (Get-FileHash -LiteralPath $partialPath -Algorithm SHA256).Hash
    if ($localHash -ne $remoteHash) { throw "Local archive checksum mismatch." }
    Write-BackupLog "Copy: OK; local SHA256 matches validated container archive"
    Invoke-CheckedDocker -Stage "remove container temporary archive" -DockerArguments @("exec", $containerId, "rm", "-f", "--", $remotePath) | Out-Null
    $remoteCreated = $false
    Write-BackupLog "Container temporary archive: removed"
    # No overwrite; same-directory rename publishes only a complete checked file.
    [IO.File]::Move($partialPath, $finalPath)
    $partialPath = $null
    $size = (Get-Item -LiteralPath $finalPath).Length
    Write-BackupLog "SUCCESS archive=$finalPath bytes=$size SHA256=$localHash"
    $exitCode = 0
}
catch {
    $exitCode = 1
    Write-BackupLog ("FAILURE: " + $_.Exception.Message)
}
finally {
    if ($remoteCreated -and $containerId) {
        try {
            Invoke-CheckedDocker -Stage "failure cleanup in container" -DockerArguments @("exec", $containerId, "rm", "-f", "--", $remotePath) | Out-Null
            Write-BackupLog "Failure cleanup: container temporary archive removed"
        }
        catch { $exitCode = 1; Write-BackupLog ("CLEANUP FAILURE: " + $_.Exception.Message) }
    }
    if ($partialPath -and (Test-Path -LiteralPath $partialPath)) {
        try { Remove-Item -LiteralPath $partialPath -Force; Write-BackupLog "Failure cleanup: local partial archive removed" }
        catch { $exitCode = 1; Write-BackupLog ("CLEANUP FAILURE: " + $_.Exception.Message) }
    }
    if ($lockHandle) { $lockHandle.Dispose() }
    $clock.Stop()
    Write-BackupLog ("END exit_code={0} duration_seconds={1:F2}" -f $exitCode, $clock.Elapsed.TotalSeconds)
}
# Optional simulation after successful publication and release of the shared lock.
if ($exitCode -eq 0 -and $PreviewRetention) {
    & (Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe") -NoProfile -NonInteractive -File (Join-Path $PSScriptRoot "retention_staging.ps1")
    if ($LASTEXITCODE -ne 0) { Write-BackupLog "Retention preview failed; completed backup preserved"; $exitCode = 1 }
}
exit $exitCode
