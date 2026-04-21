param(
    [string]$ProjectRoot,
    [string]$BindHost = '127.0.0.1',
    [int]$Port = 55432,
    [string]$ContainerName = 'ielts-vocab-postgres-microservices',
    [string]$Image = 'postgres:18',
    [string]$AdminUser = 'postgres',
    [string]$AdminPassword = 'postgres',
    [string]$DataDir = '',
    [string]$MicroservicesEnv = '',
    [switch]$ForceRecreate
)

$ErrorActionPreference = 'Stop'

$root = if ($ProjectRoot) {
    (Resolve-Path $ProjectRoot).Path
} else {
    Split-Path -Parent $PSScriptRoot
}

$runtimeDir = Join-Path $root 'logs\runtime\postgres-microservices-docker'
if (-not $DataDir) {
    $DataDir = Join-Path $runtimeDir 'data'
}
if (-not $MicroservicesEnv) {
    $MicroservicesEnv = Join-Path $root 'backend\.env.microservices.local'
}

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Quote-PgLiteral {
    param([string]$Value)
    return "'" + ($Value -replace "'", "''") + "'"
}

function Quote-PgIdentifier {
    param([string]$Value)
    return '"' + ($Value -replace '"', '""') + '"'
}

function Test-TcpReady {
    param(
        [string]$TargetHost,
        [int]$TargetPort
    )

    $client = $null
    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $async = $client.BeginConnect($TargetHost, $TargetPort, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(1500)) {
            return $false
        }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        if ($client) {
            $client.Dispose()
        }
    }
}

function Wait-PostgresReady {
    param([int]$TimeoutSeconds = 60)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $output = & docker exec $ContainerName pg_isready -h 127.0.0.1 -p 5432 -U $AdminUser 2>&1
        if ($LASTEXITCODE -eq 0 -and (Test-TcpReady -TargetHost $BindHost -TargetPort $Port)) {
            return
        }
        Start-Sleep -Seconds 2
    }

    throw "Docker PostgreSQL did not become ready within $TimeoutSeconds seconds on ${BindHost}:$Port."
}

function Get-ContainerExists {
    $output = & docker ps -a --filter "name=^/${ContainerName}$" --format '{{.Names}}' 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $false
    }
    $lastLine = @($output | Where-Object { $_ }) | Select-Object -Last 1
    if (-not $lastLine) {
        return $false
    }
    return ($lastLine.Trim() -eq $ContainerName)
}

function Get-ContainerRunning {
    $output = & docker ps --filter "name=^/${ContainerName}$" --format '{{.Names}}' 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $false
    }
    $lastLine = @($output | Where-Object { $_ }) | Select-Object -Last 1
    if (-not $lastLine) {
        return $false
    }
    return ($lastLine.Trim() -eq $ContainerName)
}

function Invoke-DockerPsql {
    param(
        [string]$Database = 'postgres',
        [string]$Sql,
        [switch]$TuplesOnly
    )

    $arguments = @(
        'exec',
        '-e', "PGPASSWORD=$AdminPassword",
        $ContainerName,
        'psql',
        '-v', 'ON_ERROR_STOP=1',
        '-U', $AdminUser,
        '-d', $Database
    )
    if ($TuplesOnly) {
        $arguments += @('-t', '-A')
    }
    $arguments += @('-c', $Sql)

    $output = & docker @arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw (($output | Out-String).Trim())
    }
    return (($output | Out-String).Trim())
}

function Read-ServiceDatabaseSpecs {
    param([string]$EnvPath)

    if (-not (Test-Path $EnvPath)) {
        return @()
    }

    $specs = @()
    foreach ($line in Get-Content $EnvPath) {
        if ($line -notmatch '^(?<key>[A-Z0-9_]+)_DATABASE_URL=(?<value>.+)$') {
            continue
        }

        $uri = [System.Uri]$matches['value']
        $userInfo = $uri.UserInfo.Split(':', 2)
        if ($userInfo.Count -lt 2) {
            continue
        }

        $specs += [pscustomobject]@{
            EnvKey = $matches['key']
            User = [System.Uri]::UnescapeDataString($userInfo[0])
            Password = [System.Uri]::UnescapeDataString($userInfo[1])
            Database = $uri.AbsolutePath.TrimStart('/')
        }
    }

    return @(
        $specs |
            Sort-Object User, Database -Unique
    )
}

function Ensure-ServiceDatabaseSpec {
    param([pscustomobject]$Spec)

    $roleName = Quote-PgIdentifier $Spec.User
    $rolePassword = Quote-PgLiteral $Spec.Password
    $databaseName = Quote-PgIdentifier $Spec.Database
    $roleExists = Invoke-DockerPsql -TuplesOnly -Sql "SELECT 1 FROM pg_roles WHERE rolname = $(Quote-PgLiteral $Spec.User);"

    if ($roleExists -eq '1') {
        Invoke-DockerPsql -Sql "ALTER ROLE $roleName WITH LOGIN PASSWORD $rolePassword;" | Out-Null
    } else {
        Invoke-DockerPsql -Sql "CREATE ROLE $roleName LOGIN PASSWORD $rolePassword;" | Out-Null
    }

    $databaseExists = Invoke-DockerPsql -TuplesOnly -Sql "SELECT 1 FROM pg_database WHERE datname = $(Quote-PgLiteral $Spec.Database);"
    if ($databaseExists -ne '1') {
        Invoke-DockerPsql -Sql "CREATE DATABASE $databaseName OWNER $roleName;" | Out-Null
    }

    Invoke-DockerPsql -Sql "ALTER DATABASE $databaseName OWNER TO $roleName;" | Out-Null
    Invoke-DockerPsql -Sql "GRANT ALL PRIVILEGES ON DATABASE $databaseName TO $roleName;" | Out-Null
}

try {
    Require-Command docker

    foreach ($directory in @($runtimeDir, $DataDir)) {
        if (-not (Test-Path $directory)) {
            New-Item -ItemType Directory -Path $directory | Out-Null
        }
    }

    if ($ForceRecreate -and (Get-ContainerExists)) {
        & docker rm -f $ContainerName | Out-Null
    }

    if (-not (Get-ContainerExists)) {
        if (Test-TcpReady -TargetHost $BindHost -TargetPort $Port) {
            throw "Port $Port is already in use. Stop the current PostgreSQL listener before starting Docker PostgreSQL."
        }

        $dataMount = (Resolve-Path $DataDir).Path
        $portMapping = "${BindHost}:${Port}:5432"
        & docker run -d `
            --name $ContainerName `
            --restart unless-stopped `
            -e "POSTGRES_USER=$AdminUser" `
            -e "POSTGRES_PASSWORD=$AdminPassword" `
            -e "POSTGRES_DB=postgres" `
            -p $portMapping `
            -v "${dataMount}:/var/lib/postgresql" `
            $Image `
            -c max_connections=200 `
            -c shared_buffers=256MB `
            -c wal_level=replica | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw 'Failed to create Docker PostgreSQL container.'
        }
    } elseif (-not (Get-ContainerRunning)) {
        & docker start $ContainerName | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw 'Failed to start Docker PostgreSQL container.'
        }
    }

    Wait-PostgresReady -TimeoutSeconds 90

    foreach ($spec in Read-ServiceDatabaseSpecs -EnvPath $MicroservicesEnv) {
        Ensure-ServiceDatabaseSpec -Spec $spec
    }

    Write-Host "[DONE] Docker PostgreSQL ready on postgresql://$AdminUser@$BindHost`:$Port/postgres"
    Write-Host "       Container:   $ContainerName"
    Write-Host "       Data dir:    $DataDir"
    exit 0
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)"
    exit 1
}
