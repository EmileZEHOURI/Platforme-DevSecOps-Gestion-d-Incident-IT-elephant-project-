#requires -Version 5.1
[CmdletBinding()]
param([switch]$Apply, [string]$PlanPath)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\backups"))
$logs = Join-Path $root "logs"
$lock = $null
$journal = $null
$exitCode = 1

function Assert-SafePath([string]$Path, [string]$Within) {
    $full = [IO.Path]::GetFullPath($Path)
    if ($full -ne $Within -and -not $full.StartsWith($Within + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path outside authorized backups directory."
    }
    $cursor = $full
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse point refused: $cursor" }
        }
        $cursor = Split-Path -Parent $cursor
    }
    return $full
}
function Log([string]$Message) {
    $line = [DateTimeOffset]::Now.ToString("o") + " " + $Message
    Write-Host $line
    if ($script:journal) { Add-Content -LiteralPath $script:journal -Value $line -Encoding UTF8 }
}
function File-Hash([string]$Path) {
    $stream = [IO.File]::Open($Path, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace("-", "") }
    finally { $sha.Dispose(); $stream.Dispose() }
}
function Snapshot {
    $entries = @()
    foreach ($item in @(Get-ChildItem -LiteralPath $root -Force | Sort-Object Name)) {
        if ($item.Name -eq ".backup-staging.lock") { continue }
        $link = [bool]($item.Attributes -band [IO.FileAttributes]::ReparsePoint)
        $hash = ""
        if (-not $link -and -not $item.PSIsContainer) { $hash = (File-Hash $item.FullName) }
        $entries += [pscustomobject][ordered]@{
            Name=$item.Name; Directory=[bool]$item.PSIsContainer; Link=$link
            Size=$(if ($item.PSIsContainer) { 0 } else { $item.Length })
            Modified=$(if ($item.PSIsContainer -and -not $link) { "" } else { $item.LastWriteTimeUtc.ToString("o") })
            Attributes=[string]$item.Attributes; Hash=$hash
        }
    }
    $proofs = @()
    foreach ($item in @(Get-ChildItem -LiteralPath $logs -Filter "backup_*.log" -Force | Sort-Object Name)) {
        if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            $proofs += [pscustomobject]@{Name=$item.Name; Hash="UNSAFE"}
        } else {
            $proofs += [pscustomobject]@{Name=$item.Name; Hash=(File-Hash $item.FullName)}
        }
    }
    return [pscustomobject][ordered]@{Files=@($entries); Proofs=@($proofs)}
}
function Fingerprint($Value) { return ($Value | ConvertTo-Json -Depth 8 -Compress) }
function New-Plan($State) {
    $decisions = @()
    $reliable = @()
    foreach ($item in $State.Files) {
        if ($item.Directory -and -not $item.Link) { continue }
        $reason = "unknown or incomplete filename"
        $date = [datetime]::MinValue
        $match = [regex]::Match($item.Name, '^staging_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_([a-f0-9]{32})\.dump$')
        $valid = $false
        if ($item.Link) { $reason = "symbolic link or junction protected" }
        elseif ($match.Success -and [datetime]::TryParseExact($match.Groups[1].Value, "yyyy-MM-dd_HH-mm-ss", [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::None, [ref]$date)) {
            if ($date -gt (Get-Date)) { $reason = "future date protected" }
            else {
                $proofName = "backup_" + $match.Groups[1].Value + "_" + $match.Groups[2].Value + ".log"
                $proof = @($State.Proofs | Where-Object { $_.Name -ceq $proofName -and $_.Hash -ne "UNSAFE" })
                $reason = "missing or invalid verification evidence"
                if ($proof.Count -eq 1 -and $item.Size -gt 0) {
                    $text = [IO.File]::ReadAllText((Join-Path $logs $proofName))
                    $expected = "SUCCESS archive=" + (Join-Path $root $item.Name) + " bytes=" + $item.Size + " SHA256=" + $item.Hash
                    $successes = @($text -split "\r?\n" | Where-Object { $_ -match ' SUCCESS archive=' })
                    $valid = $successes.Count -eq 1 -and $successes[0].EndsWith($expected, [StringComparison]::OrdinalIgnoreCase) -and
                        $text.Contains("BEGIN environment=staging compose_project=incident-staging service=db") -and
                        $text.Contains("Target verified: incident-staging/db database=incident_management_staging") -and
                        $text.Contains("Archive validation: pg_restore --list OK") -and
                        $text.Contains("Copy: OK; local SHA256 matches validated container archive") -and
                        ($text.TrimEnd() -match 'END exit_code=0 duration_seconds=[0-9.,]+$') -and
                        ($text.IndexOf("Archive validation: pg_restore --list OK") -lt $text.IndexOf($expected, [StringComparison]::OrdinalIgnoreCase)) -and
                        ($text.IndexOf("Copy: OK; local SHA256 matches validated container archive") -lt $text.IndexOf($expected, [StringComparison]::OrdinalIgnoreCase)) -and
                        ($text -notmatch 'FAILURE|END exit_code=[1-9]')
                }
            }
        }
        $decision = [pscustomobject][ordered]@{Name=$item.Name; Size=$item.Size; Hash=$item.Hash; Date=$date.ToString("s"); Action="PROTECT"; Reason=$reason}
        $decisions += $decision
        if ($valid) {
            $decision.Action = "KEEP"
            $decision.Reason = ""
            $offset = (([int]$date.DayOfWeek + 6) % 7)
            $reliable += [pscustomobject]@{Name=$item.Name; Date=$date; Day=$date.ToString("yyyy-MM-dd"); Week=$date.Date.AddDays(-$offset).ToString("yyyy-MM-dd"); Decision=$decision}
        }
    }
    $ordered = @($reliable | Sort-Object @{Expression="Date";Descending=$true}, @{Expression="Name";Descending=$true})
    $days = @()
    $weeks = @()
    foreach ($entry in $ordered) {
        if (@($days | ForEach-Object { $_.Day }) -notcontains $entry.Day) { $days += $entry }
        if (@($weeks | ForEach-Object { $_.Week }) -notcontains $entry.Week) { $weeks += $entry }
    }
    $daily = @($days | Select-Object -First 7)
    $weekly = @($weeks | Select-Object -First 4)
    $sufficient = $days.Count -ge 7 -and $weeks.Count -ge 4
    foreach ($entry in $ordered) {
        $reasons = @()
        if ($entry.Name -eq $ordered[0].Name) { $reasons += "latest verified archive" }
        if (@($daily | ForEach-Object { $_.Name }) -contains $entry.Name) { $reasons += "daily point" }
        if (@($weekly | ForEach-Object { $_.Name }) -contains $entry.Name) { $reasons += "weekly point (Monday-Sunday)" }
        if (-not $sufficient) { $reasons += "insufficient history: need 7 days and 4 weeks" }
        if ($reasons.Count) { $entry.Decision.Reason = $reasons -join "; " }
        else { $entry.Decision.Action="DELETE"; $entry.Decision.Reason="verified archive outside daily/weekly union" }
    }
    return [pscustomobject][ordered]@{
        Version=1; Root=$root; Created=[DateTimeOffset]::Now.ToString("o"); Snapshot=$State
        Reliable=$reliable.Count; Daily=$daily.Count; Weekly=$weekly.Count
        Sufficient=$sufficient; Decisions=@($decisions)
    }
}

try {
    Assert-SafePath $root $root | Out-Null
    if (-not (Test-Path -LiteralPath $root -PathType Container)) { throw "Backup directory unavailable." }
    Assert-SafePath $logs $root | Out-Null
    if (-not (Test-Path -LiteralPath $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }
    $stamp = (Get-Date -Format "yyyy-MM-dd_HH-mm-ss") + "_" + [guid]::NewGuid().ToString("N")
    $journal = Join-Path $logs ("retention_" + $stamp + ".log")
    Log ("BEGIN mode=" + $(if ($Apply) {"APPLY"} else {"SIMULATION"}))
    $lockPath = Assert-SafePath (Join-Path $root ".backup-staging.lock") $root
    $lock = [IO.File]::Open($lockPath, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    $state = Snapshot
    if ($PlanPath) {
        Assert-SafePath $PlanPath $logs | Out-Null
        $prior = Get-Content -LiteralPath $PlanPath -Raw | ConvertFrom-Json
        if ($prior.Version -ne 1 -or $prior.Root -ne $root -or (Fingerprint $prior.Snapshot) -cne (Fingerprint $state)) {
            throw "Stale or invalid plan: files or verification evidence changed."
        }
    }
    # Always recompute decisions: never trust DELETE instructions from a JSON file.
    $plan = New-Plan $state
    $planFile = Join-Path $logs ("retention_" + $stamp + ".json")
    $plan | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $planFile -Encoding UTF8
    $delete = @($plan.Decisions | Where-Object Action -eq "DELETE")
    $protected = @($plan.Decisions | Where-Object Action -eq "PROTECT")
    $total = [long]0
    foreach ($entry in $plan.Decisions) { $total += $entry.Size }
    Log ("detected={0} reliable={1} daily={2} weekly={3} additionally_protected={4} deletable={5} bytes_before={6}" -f $plan.Decisions.Count,$plan.Reliable,$plan.Daily,$plan.Weekly,$protected.Count,$delete.Count,$total)
    foreach ($decision in $plan.Decisions) { Log ($decision.Action + " " + $decision.Name + " : " + $decision.Reason) }
    $removed = 0
    $removedBytes = 0
    if ($Apply -and $delete.Count) {
        if ((Fingerprint (Snapshot)) -cne (Fingerprint $state)) { throw "File list changed before application; no deletion performed." }
        # Verify every path before the first deletion.
        foreach ($entry in $delete) { Assert-SafePath (Join-Path $root $entry.Name) $root | Out-Null }
        $expected = $state
        foreach ($entry in $delete) {
            Assert-SafePath $root $root | Out-Null
            Assert-SafePath $logs $root | Out-Null
            if ((Fingerprint (Snapshot)) -cne (Fingerprint $expected)) { throw "Files changed during application; remaining archives preserved." }
            $target = Assert-SafePath (Join-Path $root $entry.Name) $root
            if ((Split-Path -Parent $target) -ne $root) { throw "Non-direct child refused." }
            Remove-Item -LiteralPath $target -Force -ErrorAction Stop
            $removed++
            $removedBytes += $entry.Size
            Log ("DELETED " + $entry.Name)
            $expected.Files = @($expected.Files | Where-Object Name -cne $entry.Name)
        }
    }
    Log ("END removed={0} bytes_after={1} plan={2} exit_code=0" -f $removed,($total-$removedBytes),$planFile)
    $exitCode = 0
}
catch { Log ("FAILURE " + $_.Exception.Message + " exit_code=1") }
finally { if ($lock) { $lock.Dispose() } }
exit $exitCode
