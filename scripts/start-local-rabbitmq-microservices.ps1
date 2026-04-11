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

function Get-RabbitMQSearchRoots {
    $configured = $env:RABBITMQ_SEARCH_ROOTS
    if ($null -eq $configured) {
        $configured = ''
    }
    $configured = $configured.Trim()
    if ($configured) {
        return @(
            $configured -split ';' |
                Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
                ForEach-Object { $_.Trim() } |
                Select-Object -Unique
        )
    }

    return @(
        'F:\software',
        'D:\software',
        'C:\software'
    )
}

function Resolve-RabbitMQServerCandidate {
    param(
        [string]$CandidatePath,
        [string]$Label
    )

    if (-not (Test-Path $CandidatePath)) {
        throw "$Label does not exist: $CandidatePath"
    }

    $resolvedPath = (Resolve-Path $CandidatePath).Path
    $item = Get-Item $resolvedPath
    if (-not $item.PSIsContainer) {
        if ($item.Name -ieq 'rabbitmq-server.bat' -or $item.Name -ieq 'rabbitmq-server') {
            return $resolvedPath
        }
        throw "$Label must point to a RabbitMQ install directory or rabbitmq-server.bat: $CandidatePath"
    }

    $candidatePaths = @()
    if ($item.Name -ieq 'sbin') {
        $candidatePaths += Join-Path $resolvedPath 'rabbitmq-server.bat'
    }
    $candidatePaths += Join-Path $resolvedPath 'sbin\rabbitmq-server.bat'

    $nestedServerDirs = @(
        Get-ChildItem -Path $resolvedPath -Directory -Filter 'rabbitmq_server-*' -ErrorAction SilentlyContinue
    )
    foreach ($serverDir in $nestedServerDirs | Sort-Object FullName -Descending) {
        $candidatePaths += Join-Path $serverDir.FullName 'sbin\rabbitmq-server.bat'
    }

    foreach ($path in ($candidatePaths | Select-Object -Unique)) {
        if (Test-Path $path) {
            return (Resolve-Path $path).Path
        }
    }

    throw "$Label does not contain rabbitmq-server.bat: $CandidatePath"
}

function Find-RabbitMQServerFromSearchRoots {
    $candidatePaths = @()
    foreach ($searchRoot in @(Get-RabbitMQSearchRoots)) {
        if (-not (Test-Path $searchRoot)) {
            continue
        }

        try {
            return Resolve-RabbitMQServerCandidate -CandidatePath $searchRoot -Label 'Discovered RabbitMQ install'
        } catch {
        }

        $rabbitDirs = @(Get-ChildItem -Path $searchRoot -Directory -Filter 'RabbitMQ-*' -ErrorAction SilentlyContinue)
        foreach ($rabbitDir in $rabbitDirs | Sort-Object FullName -Descending) {
            $candidatePaths += $rabbitDir.FullName
        }
    }

    foreach ($candidatePath in ($candidatePaths | Select-Object -Unique)) {
        try {
            return Resolve-RabbitMQServerCandidate -CandidatePath $candidatePath -Label 'Discovered RabbitMQ install'
        } catch {
        }
    }

    return $null
}

function Resolve-RabbitMQServerPath {
    if ($RabbitMQServerPath) {
        return Resolve-RabbitMQServerCandidate -CandidatePath $RabbitMQServerPath -Label 'Configured RabbitMQ path'
    }

    $configured = $env:RABBITMQ_SERVER_PATH
    if ($null -eq $configured) {
        $configured = ''
    }
    $configured = $configured.Trim()
    if ($configured) {
        return Resolve-RabbitMQServerCandidate -CandidatePath $configured -Label 'RABBITMQ_SERVER_PATH'
    }

    $searchRootServer = Find-RabbitMQServerFromSearchRoots
    if ($searchRootServer) {
        return $searchRootServer
    }

    foreach ($commandName in @('rabbitmq-server.bat', 'rabbitmq-server')) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($command) {
            return Resolve-RabbitMQServerCandidate -CandidatePath $command.Source -Label "Discovered command $commandName"
        }
    }

    throw 'RabbitMQ server binary not found. Install RabbitMQ, set RABBITMQ_SERVER_PATH, or set RABBITMQ_SEARCH_ROOTS.'
}

function Get-ErlangSearchRoots {
    $configured = $env:ERLANG_SEARCH_ROOTS
    if ($null -eq $configured) {
        $configured = ''
    }
    $configured = $configured.Trim()
    if ($configured) {
        return @(
            $configured -split ';' |
                Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
                ForEach-Object { $_.Trim() } |
                Select-Object -Unique
        )
    }

    return @(
        'C:\Program Files',
        'F:\software',
        'D:\software',
        'C:\software'
    )
}

function Resolve-ErlangHomeCandidate {
    param(
        [string]$CandidatePath,
        [string]$Label
    )

    if (-not (Test-Path $CandidatePath)) {
        throw "$Label does not exist: $CandidatePath"
    }

    $resolvedPath = (Resolve-Path $CandidatePath).Path
    $item = Get-Item $resolvedPath
    if (-not $item.PSIsContainer) {
        if ($item.Name -ieq 'erl.exe') {
            $binDir = Split-Path -Parent $resolvedPath
            return (Resolve-Path (Split-Path -Parent $binDir)).Path
        }
        throw "$Label must point to an Erlang home, bin directory, or erl.exe: $CandidatePath"
    }

    $binDirPath = if ($item.Name -ieq 'bin') {
        $resolvedPath
    } else {
        Join-Path $resolvedPath 'bin'
    }
    $erlExePath = Join-Path $binDirPath 'erl.exe'
    if (Test-Path $erlExePath) {
        if ($item.Name -ieq 'bin') {
            return (Resolve-Path (Split-Path -Parent $resolvedPath)).Path
        }
        return $resolvedPath
    }

    throw "$Label does not contain bin\\erl.exe: $CandidatePath"
}

function Find-ErlangHomeFromSearchRoots {
    foreach ($searchRoot in @(Get-ErlangSearchRoots)) {
        if (-not (Test-Path $searchRoot)) {
            continue
        }

        try {
            return Resolve-ErlangHomeCandidate -CandidatePath $searchRoot -Label 'Discovered Erlang root'
        } catch {
        }

        $candidateDirs = @()
        foreach ($pattern in @('Erlang*', 'erl-*', 'otp*')) {
            $candidateDirs += @(
                Get-ChildItem -Path $searchRoot -Directory -Filter $pattern -ErrorAction SilentlyContinue
            )
        }

        foreach ($candidateDir in @(
            $candidateDirs |
                Sort-Object FullName -Descending |
                Select-Object -ExpandProperty FullName -Unique
        )) {
            try {
                return Resolve-ErlangHomeCandidate -CandidatePath $candidateDir -Label 'Discovered Erlang install'
            } catch {
            }
        }
    }

    return $null
}

function Resolve-ErlangHome {
    $configured = $env:ERLANG_HOME
    if ($null -eq $configured) {
        $configured = ''
    }
    $configured = $configured.Trim()
    if ($configured) {
        return Resolve-ErlangHomeCandidate -CandidatePath $configured -Label 'ERLANG_HOME'
    }

    $command = Get-Command erl.exe -ErrorAction SilentlyContinue
    if ($command) {
        return Resolve-ErlangHomeCandidate -CandidatePath $command.Source -Label 'Discovered erl.exe command'
    }

    $searchRootHome = Find-ErlangHomeFromSearchRoots
    if ($searchRootHome) {
        return $searchRootHome
    }

    throw 'Erlang runtime not found. Set ERLANG_HOME, install erl.exe on PATH, or set ERLANG_SEARCH_ROOTS.'
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
    $erlangHome = Resolve-ErlangHome
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
        ('set "ERLANG_HOME=' + $erlangHome + '"'),
        ('set "PATH=' + (Join-Path $erlangHome 'bin') + ';%PATH%"'),
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
