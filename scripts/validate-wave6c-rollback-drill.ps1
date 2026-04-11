param(
    [string]$LocalPreviewBase = 'http://127.0.0.1:3002',
    [string]$LocalBackendBase = 'http://127.0.0.1:5000',
    [string]$LocalSpeechBase = 'http://127.0.0.1:5001',
    [ValidateSet('browser', 'rollback', 'all')][string]$MonolithCompatSurface = 'rollback',
    [string]$MonolithCompatRouteGroups,
    [string]$PythonCommand = 'python'
)

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$resolverScript = Join-Path $scriptRoot 'resolve-monolith-compat-route-groups.py'

function Invoke-ExpectedRequest {
    param(
        [string]$Label,
        [string]$Url,
        [int[]]$ExpectedStatus = @(200)
    )

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 20
        $statusCode = [int]$response.StatusCode
    } catch {
        $statusCode = 0
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }
    }

    if ($ExpectedStatus -notcontains $statusCode) {
        throw "$Label failed: expected status $($ExpectedStatus -join ',') but got $statusCode for $Url"
    }

    Write-Host "[OK] $Label -> $statusCode ($Url)"
}

function Invoke-MonolithCompatRouteProbe {
    param(
        [string]$Label,
        [string]$Url
    )

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 20
        $statusCode = [int]$response.StatusCode
    } catch {
        $statusCode = 0
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }
    }

    if ($statusCode -eq 404 -or $statusCode -lt 200 -or $statusCode -ge 500) {
        throw "$Label failed: expected an existing compatibility route but got $statusCode for $Url"
    }

    Write-Host "[OK] $Label -> $statusCode ($Url)"
}

function Normalize-BaseUrl {
    param([string]$BaseUrl)

    return ($BaseUrl.Trim()).TrimEnd('/')
}

function Resolve-MonolithCompatRouteSelection {
    param(
        [string]$Surface,
        [string]$RouteGroups
    )

    if (-not (Test-Path $resolverScript)) {
        throw "Route-group resolver was not found: $resolverScript"
    }

    $resolverArgs = @($resolverScript, '--surface', $Surface, '--json')
    if (-not [string]::IsNullOrWhiteSpace($RouteGroups)) {
        $resolverArgs += '--route-groups'
        $resolverArgs += $RouteGroups
    }

    $rawOutput = & $PythonCommand @resolverArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to resolve compatibility route selection for surface '$Surface'."
    }

    try {
        $jsonText = ($rawOutput -join [Environment]::NewLine)
        return $jsonText | ConvertFrom-Json
    } catch {
        throw "Compatibility route selection returned invalid JSON for surface '$Surface'."
    }
}

if (-not [string]::IsNullOrWhiteSpace($MonolithCompatRouteGroups) -and $MonolithCompatSurface -ne 'all') {
    throw 'Use either -MonolithCompatRouteGroups or -MonolithCompatSurface, not both.'
}

$localPreview = Normalize-BaseUrl $LocalPreviewBase
$localBackend = Normalize-BaseUrl $LocalBackendBase
$localSpeech = Normalize-BaseUrl $LocalSpeechBase

Write-Host 'Resolving compatibility rollback drill surface...'
$selection = Resolve-MonolithCompatRouteSelection -Surface $MonolithCompatSurface -RouteGroups $MonolithCompatRouteGroups
$resolvedGroups = @(($selection.route_groups | ForEach-Object { "$_".Trim() }) | Where-Object { $_ })
$resolvedProbePath = "$($selection.probe_path)".Trim()

if ($resolvedGroups.Count -eq 0) {
    throw 'Compatibility rollback drill requires at least one resolved route group.'
}

Write-Host "[INFO] compatibility surface -> $($selection.surface)"
Write-Host "[INFO] compatibility groups -> $($resolvedGroups -join ',')"
Write-Host "[INFO] compatibility probe -> $resolvedProbePath"

Write-Host 'Running local Wave 6C rollback drill checks...'
Invoke-ExpectedRequest -Label 'local compatibility preview login' -Url "$localPreview/login"
Invoke-MonolithCompatRouteProbe -Label 'local compatibility preview api proxy' -Url "$localPreview$resolvedProbePath"
Invoke-MonolithCompatRouteProbe -Label 'local compatibility backend probe' -Url "$localBackend$resolvedProbePath"
Invoke-ExpectedRequest -Label 'local compatibility speech ready' -Url "$localSpeech/ready"
Invoke-ExpectedRequest -Label 'local compatibility socket.io polling handshake' -Url "$localSpeech/socket.io/?EIO=4&transport=polling"

Write-Host '[DONE] Wave 6C rollback drill validation checks passed.'
