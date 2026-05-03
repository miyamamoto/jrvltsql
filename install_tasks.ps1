param(
    [string]$TaskName = "JRVLTSQL_DailySync",
    [string]$Time = "06:30",
    [ValidateSet("sqlite", "postgresql")]
    [string]$DbType = "postgresql",
    [int]$DaysBack = 7,
    [int]$DaysForward = 3,
    [switch]$PersistPostgresEnvironment,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$bat = Join-Path $root "daily_sync.bat"

if (-not (Test-Path $bat)) {
    throw "daily_sync.bat not found: $bat"
}

if ($Time -notmatch '^\d{1,2}:\d{2}$') {
    throw "Time must use HH:mm format, for example 06:30"
}

if ($PersistPostgresEnvironment) {
    if ($DbType -ne "postgresql") {
        throw "-PersistPostgresEnvironment can only be used with -DbType postgresql"
    }

    $defaults = @{
        POSTGRES_HOST = "127.0.0.1"
        POSTGRES_PORT = "5432"
        POSTGRES_DATABASE = "keiba_dev"
        POSTGRES_USER = "ingestion_writer"
    }

    foreach ($name in @("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DATABASE", "POSTGRES_USER", "POSTGRES_PASSWORD")) {
        $value = [Environment]::GetEnvironmentVariable($name, "Process")
        if ([string]::IsNullOrWhiteSpace($value) -and $defaults.ContainsKey($name)) {
            $value = $defaults[$name]
        }
        if ([string]::IsNullOrWhiteSpace($value)) {
            throw "$name is required to persist PostgreSQL environment for the scheduled task"
        }
        [Environment]::SetEnvironmentVariable($name, $value, "User")
    }

    $postgresDatabase = [Environment]::GetEnvironmentVariable("POSTGRES_DATABASE", "Process")
    if ([string]::IsNullOrWhiteSpace($postgresDatabase)) {
        $postgresDatabase = $defaults["POSTGRES_DATABASE"]
    }
    [Environment]::SetEnvironmentVariable("POSTGRES_DB", $postgresDatabase, "User")
    Write-Host "Persisted POSTGRES_* values to the Windows user environment"
}

if ($Force -and (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$dailySyncArgs = "--db $DbType --days-back $DaysBack --days-forward $DaysForward"
$cmdArgument = "/c `"`"$bat`" $dailySyncArgs`""
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $cmdArgument -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Set-ScheduledTask -TaskName $TaskName -Trigger $trigger -Action $action -Settings $settings | Out-Null
} else {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "JRA daily sync for jrvltsql" | Out-Null
}

Write-Host "Scheduled task ready: $TaskName at $Time ($bat $dailySyncArgs)"
