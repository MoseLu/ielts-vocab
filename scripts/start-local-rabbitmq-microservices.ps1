param(
    [string]$ProjectRoot,
    [string]$BindHost = '127.0.0.1',
    [int]$Port = 5679,
    [string]$NodeName = 'ielts_vocab_local',
    [string]$RabbitMQServerPath = ''
)

$ErrorActionPreference = 'Stop'

$root = if ($ProjectRoot) {
    (Resolve-Path $ProjectRoot).Path
} else {
    Split-Path -Parent $PSScriptRoot
}

$runtimeDir = Join-Path $root 'logs\runtime\rabbitmq-microservices'
$dataDir = Join-Path $runtimeDir 'db'
$logDir = Join-Path $runtimeDir 'log'
$configPath = Join-Path $runtimeDir 'rabbitmq.conf'
$launcherPath = Join-Path $runtimeDir 'start-rabbitmq-local.cmd'

function Resolve-RabbitMQServerPath {
    if ($RabbitMQServerPath) {
        if (-not (Test-Path $RabbitMQServerPath)) {
            throw "Configured RabbitMQ server path does not exist: $RabbitMQServerPath"
        }
        return (Resolve-Path $RabbitMQServerPath).Path
    }

    $configured = $env:RABBITMQ_SERVER_PATH
    if ($null -eq $configured) {
        $configured = ''
    }
    $configured = $configured.Trim()
    if ($configured) {
        if (-not (Test-Path $configured)) {
            throw "RABBITMQ_SERVER_PATH does not exist: $configured"
        }
        return (Resolve-Path $configured).Path
    }

    foreach ($commandName in @('rabbitmq-server.bat', 'rabbitmq-server')) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($command) {
            return $command.Source
        }
    }

    throw 'RabbitMQ server binary not found. Install RabbitMQ or set RABBITMQ_SERVER_PATH.'
}

function Resolve-NodeName {
    param([string]$RequestedName)

    if ($RequestedName -match '@') {
        return $RequestedName
    }

    return "$RequestedName@$env:COMPUTERNAME"
}

function Test-RabbitMQReady {
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

        $protocolHeader = [byte[]](65, 77, 81, 80, 0, 0, 9, 1)
        $stream.Write($protocolHeader, 0, $protocolHeader.Length)

        $buffer = New-Object byte[] 256
        $read = $stream.Read($buffer, 0, $buffer.Length)
        return ($read -gt 0)
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

function Wait-RabbitMQReady {
    param(
        [string]$TargetHost,
        [int]$TargetPort,
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-RabbitMQReady -TargetHost $TargetHost -TargetPort $TargetPort) {
            return
        }
        Start-Sleep -Milliseconds 1000
    }

    throw "RabbitMQ did not become ready within $TimeoutSeconds seconds on ${TargetHost}:$TargetPort."
}

try {
    if (Test-RabbitMQReady -TargetHost $BindHost -TargetPort $Port) {
        Write-Host "RabbitMQ already ready on amqp://guest:guest@$BindHost`:$Port/%2F"
        exit 0
    }

    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($listener) {
        throw "Port $Port is already in use but does not respond as RabbitMQ."
    }

    $serverPath = Resolve-RabbitMQServerPath
    $resolvedNodeName = Resolve-NodeName -RequestedName $NodeName
    $distPort = $Port + 20000

    foreach ($directory in @($runtimeDir, $dataDir, $logDir)) {
        if (-not (Test-Path $directory)) {
            New-Item -ItemType Directory -Path $directory | Out-Null
        }
    }

    $configLines = @(
        "listeners.tcp.1 = $BindHost`:$Port",
        "distribution.listener.interface = $BindHost"
    )
    Set-Content -Path $configPath -Value $configLines -Encoding ASCII

    $launcherLines = @(
        '@echo off',
        'setlocal',
        ('set "RABBITMQ_BASE=' + $runtimeDir + '"'),
        ('set "RABBITMQ_CONFIG_FILE=' + $configPath + '"'),
        ('set "RABBITMQ_LOG_BASE=' + $logDir + '"'),
        ('set "RABBITMQ_MNESIA_BASE=' + $dataDir + '"'),
        ('set "RABBITMQ_NODENAME=' + $resolvedNodeName + '"'),
        ('set "RABBITMQ_NODE_PORT=' + $Port + '"'),
        ('set "RABBITMQ_DIST_PORT=' + $distPort + '"'),
        ('call "' + $serverPath + '"')
    )
    Set-Content -Path $launcherPath -Value $launcherLines -Encoding ASCII

    Start-Process -FilePath 'cmd.exe' -ArgumentList '/d', '/c', "`"$launcherPath`"" -WindowStyle Hidden | Out-Null
    Wait-RabbitMQReady -TargetHost $BindHost -TargetPort $Port -TimeoutSeconds 60

    Write-Host "[DONE] Local RabbitMQ ready on amqp://guest:guest@$BindHost`:$Port/%2F"
    Write-Host "       Runtime dir: $runtimeDir"
    exit 0
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)"
    exit 1
}
