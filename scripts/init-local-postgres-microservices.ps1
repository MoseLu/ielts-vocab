param(
    [string]$DbHost = '127.0.0.1',
    [int]$Port = 5432,
    [string]$AdminUser = 'postgres',
    [Parameter(Mandatory = $true)]
    [string]$AdminPassword,
    [string]$OutputEnvFile = '',
    [string]$SslMode = 'disable'
)

$ErrorActionPreference = 'Stop'

$serviceDefinitions = @(
    @{ ServiceName = 'identity-service'; EnvPrefix = 'IDENTITY_SERVICE'; Database = 'ielts_identity_service'; Role = 'ielts_identity_service' },
    @{ ServiceName = 'learning-core-service'; EnvPrefix = 'LEARNING_CORE_SERVICE'; Database = 'ielts_learning_core_service'; Role = 'ielts_learning_core_service' },
    @{ ServiceName = 'catalog-content-service'; EnvPrefix = 'CATALOG_CONTENT_SERVICE'; Database = 'ielts_catalog_content_service'; Role = 'ielts_catalog_content_service' },
    @{ ServiceName = 'ai-execution-service'; EnvPrefix = 'AI_EXECUTION_SERVICE'; Database = 'ielts_ai_execution_service'; Role = 'ielts_ai_execution_service' },
    @{ ServiceName = 'notes-service'; EnvPrefix = 'NOTES_SERVICE'; Database = 'ielts_notes_service'; Role = 'ielts_notes_service' },
    @{ ServiceName = 'tts-media-service'; EnvPrefix = 'TTS_MEDIA_SERVICE'; Database = 'ielts_tts_media_service'; Role = 'ielts_tts_media_service' },
    @{ ServiceName = 'asr-service'; EnvPrefix = 'ASR_SERVICE'; Database = 'ielts_asr_service'; Role = 'ielts_asr_service' },
    @{ ServiceName = 'admin-ops-service'; EnvPrefix = 'ADMIN_OPS_SERVICE'; Database = 'ielts_admin_ops_service'; Role = 'ielts_admin_ops_service' }
)

function Resolve-PsqlPath {
    $command = Get-Command psql -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $service = Get-CimInstance Win32_Service |
        Where-Object { $_.Name -match '^postgresql-x64-' } |
        Select-Object -First 1

    if (-not $service) {
        throw 'Could not find psql in PATH or a local PostgreSQL Windows service.'
    }

    $pathName = $service.PathName
    $match = [regex]::Match($pathName, '"([^"]+pg_ctl\.exe)"')
    if (-not $match.Success) {
        throw "Could not derive psql.exe from service path: $pathName"
    }

    $binDir = Split-Path -Parent $match.Groups[1].Value
    $psqlPath = Join-Path $binDir 'psql.exe'
    if (-not (Test-Path $psqlPath)) {
        throw "psql.exe was not found under $binDir"
    }
    return $psqlPath
}

function New-RandomPassword {
    $guid = [guid]::NewGuid().ToString('N')
    return "svc-$guid"
}

function Invoke-Psql {
    param(
        [string]$PsqlPath,
        [string]$Database,
        [string]$Sql,
        [switch]$TuplesOnly
    )

    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        Set-Content -Path $tempFile -Value $Sql -Encoding UTF8
        $arguments = @(
            '-v', 'ON_ERROR_STOP=1',
            '-h', $DbHost,
            '-p', $Port.ToString(),
            '-U', $AdminUser,
            '-d', $Database,
            '-f', $tempFile
        )
        if ($TuplesOnly) {
            $arguments = @('-t', '-A') + $arguments
        }

        $env:PGPASSWORD = $AdminPassword
        $output = & $PsqlPath @arguments 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw ($output -join [Environment]::NewLine)
        }
        return ($output -join [Environment]::NewLine).Trim()
    } finally {
        Remove-Item -LiteralPath $tempFile -ErrorAction SilentlyContinue
        Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    }
}

function Test-DatabaseExists {
    param(
        [string]$PsqlPath,
        [string]$DatabaseName
    )

    $result = Invoke-Psql -PsqlPath $PsqlPath -Database 'postgres' -TuplesOnly -Sql @"
SELECT 1
FROM pg_database
WHERE datname = '$DatabaseName';
"@
    return $result -eq '1'
}

function Ensure-Role {
    param(
        [string]$PsqlPath,
        [hashtable]$ServiceDefinition,
        [string]$Password
    )

    $roleExists = Invoke-Psql -PsqlPath $PsqlPath -Database 'postgres' -TuplesOnly -Sql @"
SELECT 1
FROM pg_roles
WHERE rolname = '$($ServiceDefinition.Role)';
"@

    if ($roleExists -eq '1') {
        Invoke-Psql -PsqlPath $PsqlPath -Database 'postgres' -Sql @"
ALTER ROLE $($ServiceDefinition.Role) WITH LOGIN PASSWORD '$Password';
"@ | Out-Null
        return
    }

    Invoke-Psql -PsqlPath $PsqlPath -Database 'postgres' -Sql @"
CREATE ROLE $($ServiceDefinition.Role) LOGIN PASSWORD '$Password';
"@ | Out-Null
}

function Ensure-Database {
    param(
        [string]$PsqlPath,
        [hashtable]$ServiceDefinition
    )

    if (-not (Test-DatabaseExists -PsqlPath $PsqlPath -DatabaseName $ServiceDefinition.Database)) {
        Invoke-Psql -PsqlPath $PsqlPath -Database 'postgres' -Sql @"
CREATE DATABASE $($ServiceDefinition.Database) OWNER $($ServiceDefinition.Role);
"@ | Out-Null
    }

    Invoke-Psql -PsqlPath $PsqlPath -Database 'postgres' -Sql @"
ALTER DATABASE $($ServiceDefinition.Database) OWNER TO $($ServiceDefinition.Role);
GRANT ALL PRIVILEGES ON DATABASE $($ServiceDefinition.Database) TO $($ServiceDefinition.Role);
"@ | Out-Null
}

try {
    $psqlPath = Resolve-PsqlPath
    $repoRoot = Split-Path -Parent $PSScriptRoot
    if (-not $OutputEnvFile) {
        $OutputEnvFile = Join-Path $repoRoot 'backend\.env.microservices.local'
    }

    $servicePasswords = @{}
    foreach ($definition in $serviceDefinitions) {
        $password = New-RandomPassword
        $servicePasswords[$definition.ServiceName] = $password
        Ensure-Role -PsqlPath $psqlPath -ServiceDefinition $definition -Password $password
        Ensure-Database -PsqlPath $psqlPath -ServiceDefinition $definition
        Write-Host "Provisioned $($definition.ServiceName) -> db=$($definition.Database) role=$($definition.Role)"
    }

    $lines = @(
        '# Load this after backend/.env when starting the split microservices locally.',
        "POSTGRES_HOST=$DbHost",
        "POSTGRES_PORT=$Port",
        "POSTGRES_SSLMODE=$SslMode",
        'DB_BACKUP_ENABLED=false',
        ''
    )

    foreach ($definition in $serviceDefinitions) {
        $password = $servicePasswords[$definition.ServiceName]
        $databaseUrl = "postgresql://$($definition.Role):$password@${DbHost}:$Port/$($definition.Database)?sslmode=$SslMode"
        $lines += "$($definition.EnvPrefix)_DATABASE_URL=$databaseUrl"
    }

    $parentDir = Split-Path -Parent $OutputEnvFile
    if (-not (Test-Path $parentDir)) {
        New-Item -ItemType Directory -Path $parentDir | Out-Null
    }
    Set-Content -Path $OutputEnvFile -Value $lines -Encoding UTF8

    Write-Host ''
    Write-Host "Wrote microservice database env file to $OutputEnvFile"
    Write-Host 'Keep that file local. It contains generated service passwords.'
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)"
    exit 1
}
