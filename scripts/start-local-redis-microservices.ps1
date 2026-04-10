param(
    [string]$ProjectRoot,
    [string]$BindHost = '127.0.0.1',
    [int]$Port = 56379,
    [string]$RedisServerPath = ''
)

$ErrorActionPreference = 'Stop'

$root = if ($ProjectRoot) {
    (Resolve-Path $ProjectRoot).Path
} else {
    Split-Path -Parent $PSScriptRoot
}

$runtimeDir = Join-Path $root 'logs\\runtime\\redis-microservices'
$dataDir = Join-Path $runtimeDir 'data'
$logPath = Join-Path $runtimeDir 'redis.log'
$configPath = Join-Path $runtimeDir 'redis.local.conf'

function Resolve-RedisServerPath {
    if ($RedisServerPath) {
        if (-not (Test-Path $RedisServerPath)) {
            throw "Configured Redis server path does not exist: $RedisServerPath"
        }
        return (Resolve-Path $RedisServerPath).Path
    }

    $configured = $env:REDIS_SERVER_PATH
    if ($null -eq $configured) {
        $configured = ''
    }
    $configured = $configured.Trim()
    if ($configured) {
        if (-not (Test-Path $configured)) {
            throw "REDIS_SERVER_PATH does not exist: $configured"
        }
        return (Resolve-Path $configured).Path
    }

    $command = Get-Command redis-server -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    throw 'Redis server binary not found. Install redis-server or set REDIS_SERVER_PATH.'
}

function Test-RedisReady {
    param(
        [string]$TargetHost,
        [int]$TargetPort
    )

    $client = $null
    $stream = $null
    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $client.ReceiveTimeout = 2000
        $client.SendTimeout = 2000
        $client.Connect($TargetHost, $TargetPort)
        $stream = $client.GetStream()

        $payload = [System.Text.Encoding]::ASCII.GetBytes("*1`r`n`$4`r`nPING`r`n")
        $stream.Write($payload, 0, $payload.Length)

        $buffer = New-Object byte[] 64
        $read = $stream.Read($buffer, 0, $buffer.Length)
        if ($read -le 0) {
            return $false
        }

        $response = [System.Text.Encoding]::ASCII.GetString($buffer, 0, $read)
        return $response.StartsWith('+PONG')
    } catch {
        return $false
    } finally {
        if ($stream) {
            $stream.Dispose()
        }
        if ($client) {
            $client.Dispose()
        }
    }
}

function Wait-RedisReady {
    param(
        [string]$TargetHost,
        [int]$TargetPort,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-RedisReady -TargetHost $TargetHost -TargetPort $TargetPort) {
            return
        }
        Start-Sleep -Milliseconds 500
    }

    throw "Redis did not become ready within $TimeoutSeconds seconds on ${TargetHost}:$TargetPort."
}

try {
    if (Test-RedisReady -TargetHost $BindHost -TargetPort $Port) {
        Write-Host "Redis already ready on redis://$BindHost`:$Port/0"
        exit 0
    }

    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($listener) {
        throw "Port $Port is already in use but does not respond as Redis."
    }

    $serverPath = Resolve-RedisServerPath

    foreach ($directory in @($runtimeDir, $dataDir)) {
        if (-not (Test-Path $directory)) {
            New-Item -ItemType Directory -Path $directory | Out-Null
        }
    }

    $configLines = @(
        "bind $BindHost",
        "port $Port",
        "dir $dataDir",
        'dbfilename dump.rdb',
        'save ""',
        'appendonly no',
        "logfile $logPath"
    )
    Set-Content -Path $configPath -Value $configLines -Encoding ASCII

    Start-Process -FilePath $serverPath -ArgumentList $configPath -WindowStyle Hidden | Out-Null
    Wait-RedisReady -TargetHost $BindHost -TargetPort $Port -TimeoutSeconds 30

    Write-Host "[DONE] Local Redis ready on redis://$BindHost`:$Port/0"
    Write-Host "       Runtime dir: $runtimeDir"
    exit 0
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)"
    exit 1
}

