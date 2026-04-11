param(
    [string]$ProjectRoot,
    [switch]$SkipFrontendChecks,
    [switch]$SkipRedis,
    [switch]$SkipRabbit,
    [string[]]$AllowSharedSplitServiceSqliteServices
)

$ErrorActionPreference = 'Stop'

$root = if ($ProjectRoot) {
    (Resolve-Path $ProjectRoot).Path
} else {
    Split-Path -Parent $MyInvocation.MyCommand.Path
}

$serviceDefinitions = @(
    @{ Name = 'gateway-bff'; Port = 8000; Workdir = (Join-Path $root 'apps\\gateway-bff'); Command = 'python -u main.py'; Health = 'http://127.0.0.1:8000/health' },
    @{ Name = 'identity-service'; Port = 8101; Workdir = (Join-Path $root 'services\\identity-service'); Command = 'python -u main.py'; Health = 'http://127.0.0.1:8101/ready' },
    @{ Name = 'learning-core-service'; Port = 8102; Workdir = (Join-Path $root 'services\\learning-core-service'); Command = 'python -u main.py'; Health = 'http://127.0.0.1:8102/ready' },
    @{ Name = 'catalog-content-service'; Port = 8103; Workdir = (Join-Path $root 'services\\catalog-content-service'); Command = 'python -u main.py'; Health = 'http://127.0.0.1:8103/ready' },
    @{ Name = 'ai-execution-service'; Port = 8104; Workdir = (Join-Path $root 'services\\ai-execution-service'); Command = 'python -u main.py'; Health = 'http://127.0.0.1:8104/ready' },
    @{ Name = 'tts-media-service'; Port = 8105; Workdir = (Join-Path $root 'services\\tts-media-service'); Command = 'python -u main.py'; Health = 'http://127.0.0.1:8105/ready' },
    @{ Name = 'asr-service'; Port = 8106; Workdir = (Join-Path $root 'services\\asr-service'); Command = 'python -u main.py'; Health = 'http://127.0.0.1:8106/ready' },
    @{ Name = 'notes-service'; Port = 8107; Workdir = (Join-Path $root 'services\\notes-service'); Command = 'python -u main.py'; Health = 'http://127.0.0.1:8107/ready' },
    @{ Name = 'admin-ops-service'; Port = 8108; Workdir = (Join-Path $root 'services\\admin-ops-service'); Command = 'python -u main.py'; Health = 'http://127.0.0.1:8108/ready' },
    @{ Name = 'asr-socketio'; Port = 5001; Workdir = (Join-Path $root 'services\\asr-service'); Command = 'python -u socketio_main.py'; Health = 'http://127.0.0.1:5001/ready' }
)
$workerDefinitions = @(
    @{ Name = 'identity-outbox-publisher'; Workdir = (Join-Path $root 'services\\identity-service'); Command = 'python -u outbox_publisher.py' },
    @{ Name = 'learning-core-outbox-publisher'; Workdir = (Join-Path $root 'services\\learning-core-service'); Command = 'python -u outbox_publisher.py' },
    @{ Name = 'ai-execution-outbox-publisher'; Workdir = (Join-Path $root 'services\\ai-execution-service'); Command = 'python -u outbox_publisher.py' },
    @{ Name = 'ai-wrong-word-projection-worker'; Workdir = (Join-Path $root 'services\\ai-execution-service'); Command = 'python -u wrong_word_projection_worker.py' },
    @{ Name = 'ai-daily-summary-projection-worker'; Workdir = (Join-Path $root 'services\\ai-execution-service'); Command = 'python -u daily_summary_projection_worker.py' },
    @{ Name = 'notes-outbox-publisher'; Workdir = (Join-Path $root 'services\\notes-service'); Command = 'python -u outbox_publisher.py' },
    @{ Name = 'notes-study-session-projection-worker'; Workdir = (Join-Path $root 'services\\notes-service'); Command = 'python -u study_session_projection_worker.py' },
    @{ Name = 'notes-wrong-word-projection-worker'; Workdir = (Join-Path $root 'services\\notes-service'); Command = 'python -u wrong_word_projection_worker.py' },
    @{ Name = 'notes-prompt-run-projection-worker'; Workdir = (Join-Path $root 'services\\notes-service'); Command = 'python -u prompt_run_projection_worker.py' },
    @{ Name = 'tts-media-outbox-publisher'; Workdir = (Join-Path $root 'services\\tts-media-service'); Command = 'python -u outbox_publisher.py' },
    @{ Name = 'admin-user-projection-worker'; Workdir = (Join-Path $root 'services\\admin-ops-service'); Command = 'python -u user_projection_worker.py' },
    @{ Name = 'admin-study-session-projection-worker'; Workdir = (Join-Path $root 'services\\admin-ops-service'); Command = 'python -u study_session_projection_worker.py' },
    @{ Name = 'admin-daily-summary-projection-worker'; Workdir = (Join-Path $root 'services\\admin-ops-service'); Command = 'python -u daily_summary_projection_worker.py' },
    @{ Name = 'admin-prompt-run-projection-worker'; Workdir = (Join-Path $root 'services\\admin-ops-service'); Command = 'python -u prompt_run_projection_worker.py' },
    @{ Name = 'admin-tts-media-projection-worker'; Workdir = (Join-Path $root 'services\\admin-ops-service'); Command = 'python -u tts_media_projection_worker.py' },
    @{ Name = 'admin-wrong-word-projection-worker'; Workdir = (Join-Path $root 'services\\admin-ops-service'); Command = 'python -u wrong_word_projection_worker.py' }
)

$runtimeDir = Join-Path $root 'logs\\runtime\\microservices'
$postgresDataDir = Join-Path $root 'logs\\runtime\\postgres-microservices\\data'
$postgresLog = Join-Path $root 'logs\\runtime\\postgres-microservices\\postgres.log'
$postgresBin = 'D:\sorfware\PostgreSQL\bin'
$backendEnv = Join-Path $root 'backend\\.env'
$microservicesEnv = Join-Path $root 'backend\\.env.microservices.local'
$redisHost = '127.0.0.1'
$redisPort = 56379
$redisKeyPrefix = 'ielts-vocab-local'
$redisDbAssignments = @{
    'GATEWAY_BFF_REDIS_DB' = '0'
    'IDENTITY_SERVICE_REDIS_DB' = '1'
    'LEARNING_CORE_SERVICE_REDIS_DB' = '2'
    'CATALOG_CONTENT_SERVICE_REDIS_DB' = '3'
    'AI_EXECUTION_SERVICE_REDIS_DB' = '4'
    'NOTES_SERVICE_REDIS_DB' = '5'
    'TTS_MEDIA_SERVICE_REDIS_DB' = '6'
    'ASR_SERVICE_REDIS_DB' = '7'
    'ADMIN_OPS_SERVICE_REDIS_DB' = '8'
}
$rabbitMqHost = '127.0.0.1'
$rabbitMqPort = 5679
$rabbitMqUser = 'guest'
$rabbitMqPassword = 'guest'
$rabbitMqVhost = '/'
$rabbitMqDomainExchange = 'ielts-vocab.domain'

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Wait-PortState {
    param(
        [int]$Port,
        [bool]$Listening,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $isListening = [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1)
        if ($isListening -eq $Listening) {
            return
        }
        Start-Sleep -Milliseconds 500
    }

    if ($Listening) {
        throw "Port $Port did not enter listening state within $TimeoutSeconds seconds."
    }

    throw "Port $Port did not become free within $TimeoutSeconds seconds."
}

function Wait-HttpReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        } catch {
        }
        Start-Sleep -Milliseconds 500
    }

    throw "Endpoint did not become ready within $TimeoutSeconds seconds: $Url"
}

function Stop-PortListeners {
    param(
        [int]$Port,
        [string]$Label
    )

    $listeners = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique

    if (-not $listeners) {
        return
    }

    foreach ($procId in $listeners) {
        try {
            Stop-Process -Id $procId -Force -ErrorAction Stop
        } catch {
        }

        Start-Sleep -Milliseconds 500
        if (Get-Process -Id $procId -ErrorAction SilentlyContinue) {
            & taskkill.exe /PID $procId /T /F | Out-Null
        }
    }

    Wait-PortState -Port $Port -Listening $false -TimeoutSeconds 30
}

function Start-PortReservations {
    param([int[]]$Ports)

    $reservations = @{}
    foreach ($port in ($Ports | Sort-Object -Unique)) {
        $deadline = (Get-Date).AddSeconds(20)
        while ((Get-Date) -lt $deadline) {
            try {
                $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, $port)
                $listener.Start()
                $reservations[$port] = $listener
                break
            } catch {
                Start-Sleep -Milliseconds 500
            }
        }

        if (-not $reservations.ContainsKey($port)) {
            throw "Port $port did not become reservable within 20 seconds."
        }
    }

    return $reservations
}

function Release-PortReservation {
    param(
        [hashtable]$Reservations,
        [int]$Port
    )

    if ($Reservations.ContainsKey($Port)) {
        $Reservations[$Port].Stop()
        $Reservations.Remove($Port)
    }
}

function Start-LoggedProcess {
    param(
        [string]$WorkingDirectory,
        [string]$CommandLine
    )

    return Start-Process -FilePath 'cmd.exe' -ArgumentList '/d', '/c', "cd /d `"$WorkingDirectory`" && $CommandLine" -WindowStyle Hidden -PassThru
}

function Stop-WorkerCommandTrees {
    param([object[]]$Definitions)

    $repoMatchRoot = $root.ToLowerInvariant()
    $cmdProcesses = @(Get-CimInstance Win32_Process -Filter "Name = 'cmd.exe'" -ErrorAction SilentlyContinue)
    if ($cmdProcesses.Count -eq 0) {
        return
    }

    foreach ($definition in $Definitions) {
        $commandFragment = ($definition.Command -replace '^python -u\s+', '').Trim().ToLowerInvariant()
        $workdirFragment = $definition.Workdir.ToLowerInvariant()
        $matchingProcesses = @(
            $cmdProcesses |
                Where-Object {
                    $_.CommandLine `
                    -and $_.CommandLine.ToLowerInvariant().Contains($repoMatchRoot) `
                    -and $_.CommandLine.ToLowerInvariant().Contains($workdirFragment) `
                    -and $_.CommandLine.ToLowerInvariant().Contains($commandFragment)
                }
        )

        foreach ($process in $matchingProcesses) {
            & taskkill.exe /PID $process.ProcessId /T /F | Out-Null
        }
    }
}

function Get-SharedSqliteOverrideEnvPrefix {
    if (-not $AllowSharedSplitServiceSqliteServices -or $AllowSharedSplitServiceSqliteServices.Count -eq 0) {
        return ''
    }

    $serviceNames = @(
        $AllowSharedSplitServiceSqliteServices |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
            ForEach-Object { $_.Trim() } |
            Select-Object -Unique
    )
    if ($serviceNames.Count -eq 0) {
        return ''
    }

    $joined = [string]::Join(',', $serviceNames)
    return "set `"ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES=$joined`" && "
}

function Set-DefaultEnvValue {
    param(
        [string]$Name,
        [string]$Value
    )

    $currentValue = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($currentValue)) {
        [Environment]::SetEnvironmentVariable($Name, $Value)
    }
}

function Set-DefaultRedisEnv {
    Set-DefaultEnvValue -Name 'REDIS_HOST' -Value $redisHost
    Set-DefaultEnvValue -Name 'REDIS_PORT' -Value $redisPort.ToString()
    Set-DefaultEnvValue -Name 'REDIS_KEY_PREFIX' -Value $redisKeyPrefix

    foreach ($assignment in $redisDbAssignments.GetEnumerator()) {
        Set-DefaultEnvValue -Name $assignment.Key -Value $assignment.Value
    }
}

function Set-DefaultRabbitEnv {
    Set-DefaultEnvValue -Name 'RABBITMQ_HOST' -Value $rabbitMqHost
    Set-DefaultEnvValue -Name 'RABBITMQ_PORT' -Value $rabbitMqPort.ToString()
    Set-DefaultEnvValue -Name 'RABBITMQ_USER' -Value $rabbitMqUser
    Set-DefaultEnvValue -Name 'RABBITMQ_PASSWORD' -Value $rabbitMqPassword
    Set-DefaultEnvValue -Name 'RABBITMQ_VHOST' -Value $rabbitMqVhost
    Set-DefaultEnvValue -Name 'RABBITMQ_DOMAIN_EXCHANGE' -Value $rabbitMqDomainExchange
}

function Ensure-ProjectPostgres {
    $pgCtl = Join-Path $postgresBin 'pg_ctl.exe'
    $pgIsReady = Join-Path $postgresBin 'pg_isready.exe'

    if (-not (Test-Path $postgresDataDir)) {
        throw "Project PostgreSQL data directory not found: $postgresDataDir"
    }

    & $pgCtl status -D $postgresDataDir | Out-Null
    if ($LASTEXITCODE -ne 0) {
        & $pgCtl start -D $postgresDataDir -l $postgresLog -o '\"-p 55432\"' | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw 'Failed to start project PostgreSQL cluster on port 55432.'
        }
        Start-Sleep -Seconds 3
    }

    & $pgIsReady -h 127.0.0.1 -p 55432 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Project PostgreSQL cluster is not accepting connections on 55432.'
    }
}

try {
    Set-Location $root
    Require-Command python

    if (-not (Test-Path $backendEnv)) {
        throw "Missing backend env file: $backendEnv"
    }
    if (-not (Test-Path $microservicesEnv)) {
        throw "Missing microservices env file: $microservicesEnv"
    }

    if (-not (Test-Path $runtimeDir)) {
        New-Item -ItemType Directory -Path $runtimeDir | Out-Null
    }

    if (-not $SkipRedis) {
        & (Join-Path $root 'scripts\start-local-redis-microservices.ps1') -ProjectRoot $root -BindHost $redisHost -Port $redisPort
        if ($LASTEXITCODE -ne 0) {
            throw 'Failed to start local Redis runtime.'
        }
        Set-DefaultRedisEnv
    }

    if (-not $SkipRabbit) {
        & (Join-Path $root 'scripts\start-local-rabbitmq-microservices.ps1') -ProjectRoot $root -BindHost $rabbitMqHost -Port $rabbitMqPort
        if ($LASTEXITCODE -ne 0) {
            throw 'Failed to start local RabbitMQ runtime.'
        }
        Set-DefaultRabbitEnv
    }

    Ensure-ProjectPostgres

    foreach ($definition in $serviceDefinitions) {
        Stop-PortListeners -Port $definition.Port -Label $definition.Name
    }
    Stop-WorkerCommandTrees -Definitions $workerDefinitions

    $portReservations = Start-PortReservations -Ports ($serviceDefinitions | ForEach-Object { $_.Port })

    foreach ($definition in $serviceDefinitions) {
        $stdoutLog = Join-Path $runtimeDir "$($definition.Name).out.log"
        $stderrLog = Join-Path $runtimeDir "$($definition.Name).err.log"
        Set-Content -Path $stdoutLog -Value ''
        Set-Content -Path $stderrLog -Value ''
        Add-Content -Path $stdoutLog -Value "===== [$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $($definition.Name) start ====="
        Add-Content -Path $stderrLog -Value "===== [$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $($definition.Name) start ====="

        $envPrefix = "set `"MICROSERVICES_ENV_FILE=$microservicesEnv`" && "
        $envPrefix += Get-SharedSqliteOverrideEnvPrefix
        Release-PortReservation -Reservations $portReservations -Port $definition.Port
        Start-LoggedProcess -WorkingDirectory $definition.Workdir -CommandLine ($envPrefix + $definition.Command + " 1>>`"$stdoutLog`" 2>>`"$stderrLog`"")
        Wait-PortState -Port $definition.Port -Listening $true -TimeoutSeconds 45
        Wait-HttpReady -Url $definition.Health -TimeoutSeconds 45
    }

    foreach ($definition in $workerDefinitions) {
        $stdoutLog = Join-Path $runtimeDir "$($definition.Name).out.log"
        $stderrLog = Join-Path $runtimeDir "$($definition.Name).err.log"
        Set-Content -Path $stdoutLog -Value ''
        Set-Content -Path $stderrLog -Value ''
        Add-Content -Path $stdoutLog -Value "===== [$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $($definition.Name) start ====="
        Add-Content -Path $stderrLog -Value "===== [$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $($definition.Name) start ====="

        $envPrefix = "set `"MICROSERVICES_ENV_FILE=$microservicesEnv`" && "
        $envPrefix += Get-SharedSqliteOverrideEnvPrefix
        $process = Start-LoggedProcess -WorkingDirectory $definition.Workdir -CommandLine ($envPrefix + $definition.Command + " 1>>`"$stdoutLog`" 2>>`"$stderrLog`"")
        Start-Sleep -Seconds 2
        if ($process.HasExited) {
            throw "$($definition.Name) exited during startup. Check $stdoutLog and $stderrLog."
        }
    }

    if (-not $SkipFrontendChecks) {
        Write-Host "Gateway ready at http://127.0.0.1:8000"
    }
    if ($AllowSharedSplitServiceSqliteServices -and $AllowSharedSplitServiceSqliteServices.Count -gt 0) {
        $joinedOverrides = [string]::Join(', ', @(
            $AllowSharedSplitServiceSqliteServices |
                Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
                ForEach-Object { $_.Trim() } |
                Select-Object -Unique
        ))
        if (-not [string]::IsNullOrWhiteSpace($joinedOverrides)) {
            Write-Host "       Shared SQLite override services: $joinedOverrides"
        }
    }

    Write-Host '[DONE] Microservice backend started successfully.'
    Write-Host '       Gateway:           http://127.0.0.1:8000'
    Write-Host '       Identity:          http://127.0.0.1:8101'
    Write-Host '       Learning core:     http://127.0.0.1:8102'
    Write-Host '       Catalog content:   http://127.0.0.1:8103'
    Write-Host '       AI execution:      http://127.0.0.1:8104'
    Write-Host '       TTS media:         http://127.0.0.1:8105'
    Write-Host '       ASR HTTP:          http://127.0.0.1:8106'
    Write-Host '       Notes:             http://127.0.0.1:8107'
    Write-Host '       Admin ops:         http://127.0.0.1:8108'
    Write-Host '       ASR Socket.IO:     http://127.0.0.1:5001'
    Write-Host '       Identity worker:   identity-outbox-publisher'
    Write-Host '       Learning worker:   learning-core-outbox-publisher'
    Write-Host '       AI worker:         ai-execution-outbox-publisher'
    Write-Host '       AI wrong worker:   ai-wrong-word-projection-worker'
    Write-Host '       AI summary worker: ai-daily-summary-projection-worker'
    Write-Host '       Notes worker:      notes-outbox-publisher'
    Write-Host '       Notes session worker: notes-study-session-projection-worker'
    Write-Host '       Notes wrong worker: notes-wrong-word-projection-worker'
    Write-Host '       Notes prompt worker: notes-prompt-run-projection-worker'
    Write-Host '       TTS worker:        tts-media-outbox-publisher'
    Write-Host '       Admin user worker: admin-user-projection-worker'
    Write-Host '       Admin stat worker: admin-study-session-projection-worker'
    Write-Host '       Admin note worker: admin-daily-summary-projection-worker'
    Write-Host '       Admin prompt worker: admin-prompt-run-projection-worker'
    Write-Host '       Admin media worker: admin-tts-media-projection-worker'
    Write-Host '       Admin wrong worker: admin-wrong-word-projection-worker'
    if (-not $SkipRedis) {
        Write-Host "       Redis:             redis://$redisHost`:$redisPort/0"
    }
    if (-not $SkipRabbit) {
        Write-Host "       RabbitMQ:          amqp://$rabbitMqUser`:$rabbitMqPassword@$rabbitMqHost`:$rabbitMqPort/%2F"
    }
    Write-Host "       Runtime logs:      $runtimeDir"
    exit 0
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)"
    exit 1
}
