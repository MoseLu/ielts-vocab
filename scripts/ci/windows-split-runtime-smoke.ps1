param(
    [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'

$root = if ($ProjectRoot) {
    (Resolve-Path $ProjectRoot).Path
} else {
    Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
}

$portsToCleanup = @(3020, 5001, 8000, 8101, 8102, 8103, 8104, 8105, 8106, 8107, 8108)
$backendEnv = Join-Path $root 'backend\.env'
$backendEnvExample = Join-Path $root 'backend\.env.example'
$microservicesEnvExample = Join-Path $root 'backend\.env.microservices.local.example'
$microservicesEnv = Join-Path $root 'backend\.env.microservices.local'
$startScript = Join-Path $root 'start-microservices.ps1'

function Wait-HttpReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 240
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
        Start-Sleep -Seconds 2
    }

    throw "Timed out waiting for $Url"
}

function Stop-PortListeners {
    param([int]$Port)

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
        Start-Sleep -Milliseconds 300
        if (Get-Process -Id $procId -ErrorAction SilentlyContinue) {
            & taskkill.exe /PID $procId /T /F | Out-Null
        }
    }
}

function Ensure-BackendEnv {
    if (Test-Path $backendEnv) {
        return
    }

    if (Test-Path $backendEnvExample) {
        Copy-Item $backendEnvExample $backendEnv
        return
    }

    @(
        'SECRET_KEY=ci-secret-key'
        'JWT_SECRET_KEY=ci-jwt-secret-key'
        'COOKIE_SECURE=false'
        'EMAIL_CODE_DELIVERY_MODE=mock'
        'ADMIN_INITIAL_PASSWORD=admin123'
    ) | Set-Content -Path $backendEnv -Encoding UTF8
}

function Ensure-MicroservicesEnv {
    if (Test-Path $microservicesEnv) {
        return
    }

    if (-not (Test-Path $microservicesEnvExample)) {
        throw "Missing microservices env example: $microservicesEnvExample"
    }

    Copy-Item $microservicesEnvExample $microservicesEnv
    (Get-Content $microservicesEnv) `
        -replace 'POSTGRES_PORT=5432', 'POSTGRES_PORT=55432' `
        -replace 'replace_me', 'ci-postgres-password' `
        | Set-Content -Path $microservicesEnv -Encoding UTF8
}

Ensure-BackendEnv
Ensure-MicroservicesEnv

$process = $null
try {
    foreach ($port in $portsToCleanup) {
        Stop-PortListeners -Port $port
    }

    $process = Start-Process `
        -FilePath 'powershell.exe' `
        -ArgumentList @(
            '-NoProfile',
            '-ExecutionPolicy', 'Bypass',
            '-File', $startScript,
            '-ProjectRoot', $root,
            '-SkipFrontendChecks',
            '-SkipRedis',
            '-SkipRabbit',
            '-UseDockerPostgres'
        ) `
        -PassThru

    Wait-HttpReady -Url 'http://127.0.0.1:8000/health'

    Push-Location $root
    try {
        pnpm --dir frontend exec playwright test tests/e2e/smoke.spec.ts --project=chromium
    } finally {
        Pop-Location
    }
} finally {
    if ($process -and -not $process.HasExited) {
        try {
            Stop-Process -Id $process.Id -Force -ErrorAction Stop
        } catch {
        }
    }
    foreach ($port in $portsToCleanup) {
        Stop-PortListeners -Port $port
    }
}
