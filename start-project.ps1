param(
    [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'

$root = if ($ProjectRoot) {
    (Resolve-Path $ProjectRoot).Path
} else {
    Split-Path -Parent $MyInvocation.MyCommand.Path
}
$frontendPort = 3002
$backendPort = 5000
$speechPort = 5001
$logDir = Join-Path $root 'logs\runtime'
$frontendOut = Join-Path $logDir 'frontend-preview.out.log'
$frontendErr = Join-Path $logDir 'frontend-preview.err.log'
$backendOut = Join-Path $logDir 'backend.out.log'
$backendErr = Join-Path $logDir 'backend.err.log'
$speechOut = Join-Path $logDir 'speech-service.out.log'
$speechErr = Join-Path $logDir 'speech-service.err.log'

function Write-Step {
    param([string]$Message)
    Write-Host $Message
}

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
        [int]$TimeoutSeconds = 30
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
        Write-Host "        Port $Port was already free."
        return
    }

    foreach ($procId in $listeners) {
        $processName = ''
        try {
            $processName = (Get-Process -Id $procId -ErrorAction Stop).ProcessName
        } catch {
        }

        if ($processName) {
            Write-Host "        Stopping $Label process on port ${Port}: PID=${procId} Process=$processName"
        } else {
            Write-Host "        Stopping $Label process on port ${Port}: PID=${procId}"
        }

        Stop-Process -Id $procId -Force -ErrorAction Stop
    }

    Wait-PortState -Port $Port -Listening $false -TimeoutSeconds 15
}

function Ensure-CleanWorkingTree {
    git update-index -q --refresh | Out-Null
    $statusLines = @(git status --porcelain --untracked-files=all)
    if ($statusLines.Count -gt 0) {
        throw "The working tree is not clean. Commit, stash, or remove local changes before starting."
    }
}

function Ensure-LatestCode {
    $insideRepo = (git rev-parse --is-inside-work-tree 2>$null).Trim()
    if ($insideRepo -ne 'true') {
        throw 'The current directory is not a Git repository.'
    }

    Ensure-CleanWorkingTree

    Write-Host '        Fetching latest remote refs...'
    git fetch --prune origin

    $currentBranch = (git rev-parse --abbrev-ref HEAD).Trim()
    $upstreamBranch = (git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>$null).Trim()
    if (-not $upstreamBranch) {
        throw "Branch $currentBranch has no upstream branch configured."
    }

    $parts = @((git rev-list --left-right --count "HEAD...$upstreamBranch").Trim() -split '\s+' | Where-Object { $_ })
    if ($parts.Count -lt 2) {
        throw 'Failed to read Git branch sync status.'
    }

    $ahead = [int]$parts[0]
    $behind = [int]$parts[1]

    if ($behind -eq 0 -and $ahead -eq 0) {
        Write-Host "        Branch is already aligned with $upstreamBranch."
        return
    }

    if ($behind -eq 0 -and $ahead -gt 0) {
        Write-Host "[INFO] Local branch is ahead of $upstreamBranch by $ahead commit(s)."
        Write-Host '       Startup will use the current local HEAD.'
        return
    }

    if ($behind -gt 0 -and $ahead -eq 0) {
        Write-Host "        Local branch is behind $upstreamBranch by $behind commit(s)."
        Write-Host '        Attempting fast-forward pull...'
        git pull --ff-only
        return
    }

    throw "The current branch has diverged from $upstreamBranch. Local ahead: $ahead  Remote ahead: $behind."
}

function Start-LoggedProcess {
    param(
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$CommandLine
    )

    Start-Process -FilePath 'cmd.exe' -ArgumentList '/d', '/c', "cd /d `"$WorkingDirectory`" && $CommandLine" -WindowStyle Hidden | Out-Null
}

try {
    Set-Location $root

    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir | Out-Null
    }

    Write-Step '[1/5] Stopping existing services on project ports...'
    Stop-PortListeners -Port $backendPort -Label 'backend'
    Stop-PortListeners -Port $speechPort -Label 'speech-service'
    Stop-PortListeners -Port $frontendPort -Label 'frontend-preview'

    Write-Step '[2/5] Checking required commands and files...'
    Require-Command git
    Require-Command npm
    Require-Command python

    if (-not (Test-Path (Join-Path $root 'package.json'))) {
        throw 'package.json was not found in the project root.'
    }
    if (-not (Test-Path (Join-Path $root 'backend\app.py'))) {
        throw 'backend\app.py was not found.'
    }
    if (-not (Test-Path (Join-Path $root 'backend\speech_service.py'))) {
        throw 'backend\speech_service.py was not found.'
    }
    if (-not (Test-Path (Join-Path $root 'backend\.env'))) {
        throw 'backend\.env was not found. Flask configuration is incomplete.'
    }

    Write-Step '[3/5] Ensuring the code is up to date...'
    Ensure-LatestCode

    Write-Step '[4/5] Rebuilding frontend preview assets...'
    npm run build

    Set-Content -Path $backendOut -Value ''
    Set-Content -Path $backendErr -Value ''
    Set-Content -Path $speechOut -Value ''
    Set-Content -Path $speechErr -Value ''
    Set-Content -Path $frontendOut -Value ''
    Set-Content -Path $frontendErr -Value ''

    Add-Content -Path $backendOut -Value "===== [$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] backend start ====="
    Add-Content -Path $backendErr -Value "===== [$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] backend start ====="
    Add-Content -Path $speechOut -Value "===== [$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] speech start ====="
    Add-Content -Path $speechErr -Value "===== [$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] speech start ====="
    Add-Content -Path $frontendOut -Value "===== [$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] frontend preview start ====="
    Add-Content -Path $frontendErr -Value "===== [$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] frontend preview start ====="

    Write-Step '[5/5] Starting backend, speech service, and frontend preview...'
    Start-LoggedProcess -Title 'IELTS Flask Backend' -WorkingDirectory (Join-Path $root 'backend') -CommandLine "python -u app.py 1>>`"$backendOut`" 2>>`"$backendErr`""
    Wait-PortState -Port $backendPort -Listening $true -TimeoutSeconds 30
    Wait-HttpReady -Url "http://127.0.0.1:$backendPort/api/books/stats" -TimeoutSeconds 30

    Start-LoggedProcess -Title 'IELTS Speech Service' -WorkingDirectory (Join-Path $root 'backend') -CommandLine "python -u speech_service.py 1>>`"$speechOut`" 2>>`"$speechErr`""
    Wait-PortState -Port $speechPort -Listening $true -TimeoutSeconds 30
    Wait-HttpReady -Url "http://127.0.0.1:$speechPort/health" -TimeoutSeconds 30

    Start-LoggedProcess -Title 'IELTS Frontend Preview' -WorkingDirectory $root -CommandLine "npm run preview -- --host 0.0.0.0 --port $frontendPort 1>>`"$frontendOut`" 2>>`"$frontendErr`""
    Wait-PortState -Port $frontendPort -Listening $true -TimeoutSeconds 30
    Wait-HttpReady -Url "http://127.0.0.1:$frontendPort/login" -TimeoutSeconds 30

    Write-Host '[DONE] Project restarted successfully.'
    Write-Host "       Frontend preview: http://127.0.0.1:$frontendPort"
    Write-Host "       Flask backend:    http://127.0.0.1:$backendPort"
    Write-Host "       Speech service:   http://127.0.0.1:$speechPort"
    Write-Host "       Logs directory:   $logDir"
    Write-Host "       Nginx should proxy /socket.io to port $speechPort and / to port $frontendPort."
    exit 0
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)"
    exit 1
}
