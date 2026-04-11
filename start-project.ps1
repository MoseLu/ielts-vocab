param(
    [string]$ProjectRoot,
    [switch]$AllowDetachedRuntime,
    [switch]$AllowDirtyCompatibilityDrill,
    [switch]$UseMonolithCompatibility,
    [string]$MonolithCompatRouteGroups,
    [ValidateSet('browser', 'rollback', 'all')][string]$MonolithCompatSurface = 'all',
    [switch]$SkipRedis,
    [switch]$SkipRabbit,
    [string[]]$AllowSharedSplitServiceSqliteServices, [int]$MonolithCompatBackendPort = 5000
)
$ErrorActionPreference = 'Stop'
$root = if ($ProjectRoot) {
    (Resolve-Path $ProjectRoot).Path
} else {
    Split-Path -Parent $MyInvocation.MyCommand.Path
}
$frontendPort = 3002
$legacyMonolithPort = $MonolithCompatBackendPort
$gatewayPort = 8000
$speechPort = 5001
$logDir = Join-Path $root 'logs\runtime'
$frontendOut = Join-Path $logDir 'frontend-preview.out.log'
$frontendErr = Join-Path $logDir 'frontend-preview.err.log'
$backendOut = Join-Path $logDir 'backend-compat.out.log'
$backendErr = Join-Path $logDir 'backend-compat.err.log'
$speechOut = Join-Path $logDir 'speech-compat.out.log'
$speechErr = Join-Path $logDir 'speech-compat.err.log'
$microservicesScript = Join-Path $root 'start-microservices.ps1'
$microservicesLogDir = Join-Path $logDir 'microservices'
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
            $statusCode = [int]$response.StatusCode
        } catch {
            $statusCode = if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
                [int]$_.Exception.Response.StatusCode
            } else {
                0
            }
        }
        if ($statusCode -ge 200 -and $statusCode -lt 500) { return }
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
        throw 'The working tree is not clean. Commit, stash, or remove local changes before starting.'
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

function Write-CompatibilityDrillCodeState {
    $insideRepo = (git rev-parse --is-inside-work-tree 2>$null).Trim()
    if ($insideRepo -ne 'true') {
        throw 'The current directory is not a Git repository.'
    }

    $currentBranch = (git rev-parse --abbrev-ref HEAD 2>$null).Trim()
    $statusLines = @(git status --porcelain --untracked-files=all)
    $dirtyCount = $statusLines.Count

    Write-Host "[WARN] Dirty compatibility drill override enabled."
    Write-Host "       Branch: $currentBranch"
    Write-Host "       Working tree entries: $dirtyCount"
    Write-Host '       Skipping clean-tree and remote-sync enforcement for this local rollback drill only.'
}

function Normalize-ComparablePath {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return ''
    }

    return ([System.IO.Path]::GetFullPath($Path)).TrimEnd('\').Replace('/', '\').ToLowerInvariant()
}

function Get-GitWorktreeCatalog {
    $lines = @(git worktree list --porcelain 2>$null)
    if ($LASTEXITCODE -ne 0 -or $lines.Count -eq 0) {
        return @()
    }

    $catalog = @()
    $entry = @{}

    foreach ($line in ($lines + '')) {
        if (-not $line) {
            if ($entry.ContainsKey('Path')) {
                $catalog += [pscustomobject]@{
                    Path = $entry.Path
                    NormalizedPath = Normalize-ComparablePath $entry.Path
                    Branch = $entry.Branch
                    Detached = [bool]$entry.Detached
                }
                $entry = @{}
            }
            continue
        }

        if ($line.StartsWith('worktree ')) {
            $entry.Path = $line.Substring(9).Trim()
            continue
        }

        if ($line.StartsWith('branch ')) {
            $entry.Branch = $line.Substring(7).Trim()
            continue
        }

        if ($line -eq 'detached') {
            $entry.Detached = $true
        }
    }

    return $catalog
}

function Assert-CanonicalRuntimeWorktree {
    param([switch]$AllowDetachedRuntime)

    $currentRoot = Normalize-ComparablePath $root
    $worktrees = @(Get-GitWorktreeCatalog)
    if ($worktrees.Count -eq 0) {
        return
    }

    $currentEntry = $worktrees | Where-Object { $_.NormalizedPath -eq $currentRoot } | Select-Object -First 1
    if (-not $currentEntry) {
        return
    }

    if (-not $currentEntry.Detached) {
        if ($currentEntry.Branch) {
            Write-Host "        Runtime owner worktree: $($currentEntry.Path) ($($currentEntry.Branch))"
        }
        return
    }

    if ($AllowDetachedRuntime) {
        Write-Host '[WARN] Detached worktree runtime allowed by -AllowDetachedRuntime.'
        return
    }

    $preferredEntry = $worktrees |
        Where-Object { -not $_.Detached -and $_.Branch } |
        Sort-Object Path |
        Select-Object -First 1

    if ($preferredEntry) {
        throw "Detached worktree runtime is blocked for ports $frontendPort/$gatewayPort/$speechPort. Use $($preferredEntry.Path) ($($preferredEntry.Branch)) or rerun with -AllowDetachedRuntime."
    }

    throw "Detached worktree runtime is blocked for ports $frontendPort/$gatewayPort/$speechPort. Rerun with -AllowDetachedRuntime only if you intentionally want this worktree to own the canonical runtime."
}

function Start-LoggedProcess {
    param(
        [string]$WorkingDirectory,
        [string]$CommandLine
    )

    Start-Process -FilePath 'cmd.exe' -ArgumentList '/d', '/c', "cd /d `"$WorkingDirectory`" && $CommandLine" -WindowStyle Hidden | Out-Null
}

function Get-WindowsPowerShellPath {
    $powerShellCommand = Get-Command 'powershell.exe' -ErrorAction SilentlyContinue
    if ($powerShellCommand) { return $powerShellCommand.Source }

    $legacyCommand = Get-Command 'powershell' -ErrorAction SilentlyContinue
    if ($legacyCommand) { return $legacyCommand.Source }

    throw 'Unable to locate a PowerShell executable to launch the split backend runtime.'
}

function Resolve-SharedBackendDataRoot {
    $gitCommonDirRaw = (git rev-parse --path-format=absolute --git-common-dir 2>$null).Trim()
    if (-not $gitCommonDirRaw) { return Join-Path $root 'backend' }

    $gitCommonDir = (Resolve-Path $gitCommonDirRaw).Path
    $canonicalRepoRoot = Split-Path -Parent $gitCommonDir
    $canonicalBackendRoot = Join-Path $canonicalRepoRoot 'backend'
    if (Test-Path $canonicalBackendRoot) { return $canonicalBackendRoot }

    return Join-Path $root 'backend'
}

function Resolve-MonolithCompatRouteGroupsFromSurface {
    param(
        [string]$Surface,
        [string]$RouteGroups
    )

    $resolverScript = Join-Path $root 'scripts\resolve-monolith-compat-route-groups.py'
    if (-not (Test-Path $resolverScript)) {
        throw "resolve-monolith-compat-route-groups.py was not found."
    }

    $resolverArgs = @($resolverScript, '--surface', $Surface, '--json')
    if (-not [string]::IsNullOrWhiteSpace($RouteGroups)) {
        $resolverArgs += '--route-groups'
        $resolverArgs += $RouteGroups
    }
    $resolvedOutput = & python @resolverArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to resolve monolith compatibility route selection for surface '$Surface'."
    }

    try {
        $jsonText = ($resolvedOutput -join [Environment]::NewLine)
        return $jsonText | ConvertFrom-Json
    } catch {
        throw "Failed to parse monolith compatibility route selection for surface '$Surface'."
    }
}

try {
    Set-Location $root
    $resolvedMonolithCompatGroups = ''
    $resolvedMonolithCompatProbePath = '/api/books/stats'

    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir | Out-Null
    }

    Write-Step '[1/6] Checking required commands and runtime owner...'
    Require-Command git
    Require-Command pnpm
    Require-Command python
    Assert-CanonicalRuntimeWorktree -AllowDetachedRuntime:$AllowDetachedRuntime

    Write-Step '[2/6] Stopping existing services on canonical local ports...'
    Stop-PortListeners -Port $legacyMonolithPort -Label 'legacy-monolith'
    if ($UseMonolithCompatibility) {
        Stop-PortListeners -Port $gatewayPort -Label 'gateway-bff'
        Stop-PortListeners -Port $speechPort -Label 'speech-service'
    }
    Stop-PortListeners -Port $frontendPort -Label 'frontend-preview'

    Write-Step '[3/6] Checking required files...'
    if (-not (Test-Path (Join-Path $root 'package.json'))) {
        throw 'package.json was not found in the project root.'
    }
    if (-not (Test-Path (Join-Path $root 'frontend\package.json'))) {
        throw 'frontend\package.json was not found.'
    }
    if (-not (Test-Path (Join-Path $root 'frontend\vite.config.ts'))) {
        throw 'frontend\vite.config.ts was not found.'
    }
    if (-not (Test-Path (Join-Path $root 'backend\.env'))) {
        throw 'backend\.env was not found. Split backend configuration is incomplete.'
    }
    if ($UseMonolithCompatibility) {
        if (-not (Test-Path (Join-Path $root 'backend\app.py'))) {
            throw 'backend\app.py was not found.'
        }
        if (-not (Test-Path (Join-Path $root 'backend\speech_service.py'))) {
            throw 'backend\speech_service.py was not found.'
        }
    } elseif (-not (Test-Path $microservicesScript)) {
        throw 'start-microservices.ps1 was not found.'
    }
    if (-not $UseMonolithCompatibility -and -not (Test-Path (Join-Path $root 'backend\.env.microservices.local'))) {
        throw 'backend\.env.microservices.local was not found. Split backend database configuration is incomplete.'
    }

    Write-Step '[4/6] Checking code state...'
    if ($UseMonolithCompatibility -and $AllowDirtyCompatibilityDrill) {
        Write-CompatibilityDrillCodeState
    } else {
        Ensure-LatestCode
    }

    Write-Step '[5/6] Rebuilding frontend preview assets...'
    pnpm --dir frontend build

    Set-Content -Path $frontendOut -Value ''
    Set-Content -Path $frontendErr -Value ''
    Add-Content -Path $frontendOut -Value "===== [$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] frontend preview start ====="
    Add-Content -Path $frontendErr -Value "===== [$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] frontend preview start ====="

    Write-Step '[6/6] Starting backend path and frontend preview...'
    if ($UseMonolithCompatibility) {
        if (-not [string]::IsNullOrWhiteSpace($MonolithCompatRouteGroups) -and $MonolithCompatSurface -ne 'all') {
            throw 'Use either -MonolithCompatRouteGroups or -MonolithCompatSurface, not both.'
        }

        $sharedBackendRoot = Resolve-SharedBackendDataRoot
        $sharedSqliteDbPath = Join-Path $sharedBackendRoot 'database.sqlite'
        $sharedBackupDir = Join-Path $sharedBackendRoot 'backups'
        $backendEnvPrefix = ('set "ALLOW_MONOLITH_COMPAT_RUNTIME=1" && set "BACKEND_PORT={0}" && ' -f $legacyMonolithPort)
        $compatSelection = Resolve-MonolithCompatRouteGroupsFromSurface -Surface $MonolithCompatSurface -RouteGroups $MonolithCompatRouteGroups
        $resolvedMonolithCompatGroups = (($compatSelection.route_groups | ForEach-Object { "$_".Trim() }) -join ',').Trim(',')
        $resolvedMonolithCompatProbePath = "$($compatSelection.probe_path)".Trim()
        if (-not [string]::IsNullOrWhiteSpace($resolvedMonolithCompatGroups)) {
            $backendEnvPrefix += ('set "MONOLITH_COMPAT_ROUTE_GROUPS={0}" && ' -f $resolvedMonolithCompatGroups)
        }

        if (Test-Path $sharedSqliteDbPath) {
            $backendEnvPrefix += ('set "SQLITE_DB_PATH={0}" && set "DB_BACKUP_DIR={1}" && ' -f $sharedSqliteDbPath, $sharedBackupDir)
        }

        Set-Content -Path $backendOut -Value ''
        Set-Content -Path $backendErr -Value ''
        Set-Content -Path $speechOut -Value ''
        Set-Content -Path $speechErr -Value ''
        Add-Content -Path $backendOut -Value "===== [$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] backend compatibility start ====="
        Add-Content -Path $backendErr -Value "===== [$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] backend compatibility start ====="
        Add-Content -Path $speechOut -Value "===== [$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] speech compatibility start ====="
        Add-Content -Path $speechErr -Value "===== [$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] speech compatibility start ====="

        Start-LoggedProcess -WorkingDirectory (Join-Path $root 'backend') -CommandLine "${backendEnvPrefix}python -u app.py 1>>`"$backendOut`" 2>>`"$backendErr`""
        Wait-PortState -Port $legacyMonolithPort -Listening $true -TimeoutSeconds 30
        Wait-HttpReady -Url "http://127.0.0.1:$legacyMonolithPort$resolvedMonolithCompatProbePath" -TimeoutSeconds 30

        Start-LoggedProcess -WorkingDirectory (Join-Path $root 'backend') -CommandLine "${backendEnvPrefix}python -u speech_service.py 1>>`"$speechOut`" 2>>`"$speechErr`""
        Wait-PortState -Port $speechPort -Listening $true -TimeoutSeconds 30
        Wait-HttpReady -Url "http://127.0.0.1:$speechPort/ready" -TimeoutSeconds 30

        $previewEnvPrefix = ('set "VITE_API_PROXY_TARGET=http://127.0.0.1:{0}" && set "VITE_SPEECH_PROXY_TARGET=http://127.0.0.1:{1}" && ' -f $legacyMonolithPort, $speechPort)
    } else {
        $powerShellPath = Get-WindowsPowerShellPath
        $microserviceArgs = @(
            '-NoProfile',
            '-ExecutionPolicy', 'Bypass',
            '-File', $microservicesScript,
            '-ProjectRoot', $root,
            '-SkipFrontendChecks'
        )
        if ($SkipRedis) {
            $microserviceArgs += '-SkipRedis'
        }
        if ($SkipRabbit) {
            $microserviceArgs += '-SkipRabbit'
        }
        foreach ($serviceName in @(
            $AllowSharedSplitServiceSqliteServices |
                Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
                ForEach-Object { $_.Trim() } |
                Select-Object -Unique
        )) {
            $microserviceArgs += '-AllowSharedSplitServiceSqliteServices'
            $microserviceArgs += $serviceName
        }

        & $powerShellPath @microserviceArgs
        if ($LASTEXITCODE -ne 0) {
            throw 'start-microservices.ps1 failed.'
        }

        $previewEnvPrefix = 'set "VITE_API_PROXY_TARGET=http://127.0.0.1:8000" && set "VITE_SPEECH_PROXY_TARGET=http://127.0.0.1:5001" && '
    }

    Start-LoggedProcess -WorkingDirectory (Join-Path $root 'frontend') -CommandLine "${previewEnvPrefix}pnpm preview -- --host 0.0.0.0 --port $frontendPort 1>>`"$frontendOut`" 2>>`"$frontendErr`""
    Wait-PortState -Port $frontendPort -Listening $true -TimeoutSeconds 30
    Wait-HttpReady -Url "http://127.0.0.1:$frontendPort/login" -TimeoutSeconds 30
    Wait-HttpReady -Url "http://127.0.0.1:$frontendPort$(if ($UseMonolithCompatibility) { $resolvedMonolithCompatProbePath } else { '/api/books/stats' })" -TimeoutSeconds 30

    Write-Host '[DONE] Project restarted successfully.'
    Write-Host "       Frontend preview:  http://127.0.0.1:$frontendPort"
    if ($UseMonolithCompatibility) {
        Write-Host "       Backend API:       http://127.0.0.1:$legacyMonolithPort (compatibility)"
        Write-Host "       Speech service:    http://127.0.0.1:$speechPort"
        Write-Host "       Compatibility surface: $MonolithCompatSurface"
        Write-Host "       Dirty drill override:  $AllowDirtyCompatibilityDrill"
        if (-not [string]::IsNullOrWhiteSpace($resolvedMonolithCompatGroups)) {
            Write-Host "       Compatibility groups:  $resolvedMonolithCompatGroups"
        }
        Write-Host "       Compatibility probe:   $resolvedMonolithCompatProbePath"
        Write-Host "       Compatibility logs: $backendOut / $backendErr / $speechOut / $speechErr"
    } else {
        Write-Host "       Gateway API:       http://127.0.0.1:$gatewayPort"
        Write-Host "       ASR Socket.IO:     http://127.0.0.1:$speechPort"
        Write-Host "       Backend logs:      $microservicesLogDir"
        Write-Host "       Compatibility path: .\\start-monolith-compat.ps1"
    }
    Write-Host "       Frontend logs:     $frontendOut / $frontendErr"
    Write-Host "       Nginx should proxy /api to port $(if ($UseMonolithCompatibility) { $legacyMonolithPort } else { $gatewayPort }), /socket.io to port $speechPort, and / to port $frontendPort."
    Write-Host "       Legacy backend/app.py on port $legacyMonolithPort is compatibility-only."
    exit 0
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)"
    exit 1
}
