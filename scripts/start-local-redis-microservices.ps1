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

function Get-RedisSearchRoots {
    $configured = $env:REDIS_SEARCH_ROOTS
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

function Find-RedisLauncherFromSearchRoots {
    $candidatePaths = @()
    foreach ($searchRoot in @(Get-RedisSearchRoots)) {
        if (-not (Test-Path $searchRoot)) {
            continue
        }

        $redisDirs = @(Get-ChildItem -Path $searchRoot -Directory -Filter 'Redis-*' -ErrorAction SilentlyContinue)
        foreach ($redisDir in $redisDirs | Sort-Object FullName -Descending) {
            foreach ($fileName in @('RedisService.exe', 'redis-server.exe')) {
                $candidatePath = Join-Path $redisDir.FullName $fileName
                if (Test-Path $candidatePath) {
                    $candidatePaths += $candidatePath
                }
            }
        }
    }

    foreach ($candidatePath in ($candidatePaths | Select-Object -Unique)) {
        return New-RedisLauncher -CandidatePath $candidatePath
    }

    return $null
}

function New-RedisLauncher {
    param([string]$CandidatePath)

    $resolvedPath = (Resolve-Path $CandidatePath).Path
    $leafName = [System.IO.Path]::GetFileName($resolvedPath)
    if ($leafName -ieq 'RedisService.exe') {
        return [pscustomobject]@{
            FilePath = $resolvedPath
            Mode = 'service'
        }
    }

    $serviceWrapperPath = Join-Path (Split-Path -Parent $resolvedPath) 'RedisService.exe'
    if (Test-Path $serviceWrapperPath) {
        return [pscustomobject]@{
            FilePath = (Resolve-Path $serviceWrapperPath).Path
            Mode = 'service'
        }
    }

    return [pscustomobject]@{
        FilePath = $resolvedPath
        Mode = 'server'
    }
}

function Resolve-RedisLauncher {
    if ($RedisServerPath) {
        if (-not (Test-Path $RedisServerPath)) {
            throw "Configured Redis server path does not exist: $RedisServerPath"
        }
        return New-RedisLauncher -CandidatePath $RedisServerPath
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
        return New-RedisLauncher -CandidatePath $configured
    }

    $serviceCommand = Get-Command RedisService -ErrorAction SilentlyContinue
    if ($serviceCommand) {
        return New-RedisLauncher -CandidatePath $serviceCommand.Source
    }

    $searchRootLauncher = Find-RedisLauncherFromSearchRoots
    if ($searchRootLauncher) {
        return $searchRootLauncher
    }

    $command = Get-Command redis-server -ErrorAction SilentlyContinue
    if ($command) {
        return New-RedisLauncher -CandidatePath $command.Source
    }

    throw 'Redis server binary not found. Install redis-server / RedisService, set REDIS_SERVER_PATH, or set REDIS_SEARCH_ROOTS.'
}

function Convert-ToRedisConfigPath {
    param([string]$Path)

    return ([System.IO.Path]::GetFullPath($Path)).Replace('\', '/')
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

    $launcher = Resolve-RedisLauncher

    foreach ($directory in @($runtimeDir, $dataDir)) {
        if (-not (Test-Path $directory)) {
            New-Item -ItemType Directory -Path $directory | Out-Null
        }
    }

    $configLines = @(
        "bind $BindHost",
        "port $Port",
        "dir $(Convert-ToRedisConfigPath $dataDir)",
        'dbfilename dump.rdb',
        'save ""',
        'appendonly no',
        "logfile $(Convert-ToRedisConfigPath $logPath)"
    )
    Set-Content -Path $configPath -Value $configLines -Encoding ASCII

    $argumentList = if ($launcher.Mode -eq 'service') {
        @('run', '--foreground', '--config', $configPath, '--port', "$Port", '--dir', $dataDir)
    } else {
        @('redis.local.conf')
    }

    Start-Process -FilePath $launcher.FilePath -ArgumentList $argumentList -WorkingDirectory $runtimeDir -WindowStyle Hidden | Out-Null
    Wait-RedisReady -TargetHost $BindHost -TargetPort $Port -TimeoutSeconds 30

    Write-Host "[DONE] Local Redis ready on redis://$BindHost`:$Port/0"
    Write-Host "       Runtime dir: $runtimeDir"
    exit 0
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)"
    exit 1
}
