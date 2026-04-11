param(
    [string]$LocalPreviewBase = 'http://127.0.0.1:3002',
    [string]$LocalGatewayBase = 'http://127.0.0.1:8000',
    [string]$LocalSpeechBase = 'http://127.0.0.1:5001',
    [string]$RemoteBase = 'https://axiomaticworld.com',
    [switch]$SkipLocal,
    [switch]$SkipRemote,
    [switch]$SkipBrowserCoverageAudit,
    [switch]$SkipRollbackCoverageAudit,
    [string]$PythonCommand = 'python'
)

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$routeCoverageScript = Join-Path $scriptRoot 'describe-monolith-route-coverage.py'

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

function Normalize-BaseUrl {
    param([string]$BaseUrl)

    return ($BaseUrl.Trim()).TrimEnd('/')
}

function Invoke-RouteCoverageAudit {
    param([string]$Surface)

    if (-not (Test-Path $routeCoverageScript)) {
        throw "Route coverage script was not found: $routeCoverageScript"
    }

    $rawOutput = & $PythonCommand $routeCoverageScript --surface $Surface --json
    if ($LASTEXITCODE -ne 0) {
        throw "Route coverage audit failed for surface '$Surface'."
    }

    try {
        $jsonText = ($rawOutput -join [Environment]::NewLine)
        return $jsonText | ConvertFrom-Json
    } catch {
        throw "Route coverage audit returned invalid JSON for surface '$Surface'."
    }
}

function Get-RouteCoverageGapLabels {
    param($Payload)

    $labels = @()
    foreach ($group in @($Payload.route_groups)) {
        foreach ($record in @($group.monolith_only_route_methods)) {
            $labels += "$($group.name): $($record.method) $($record.normalized_path)"
        }
    }
    return $labels
}

function Assert-BrowserRouteCoverage {
    $payload = Invoke-RouteCoverageAudit -Surface 'browser'
    $summary = $payload.summary
    $uncoveredCount = [int]$summary.uncovered_monolith_route_method_count
    if ($uncoveredCount -ne 0) {
        $labels = Get-RouteCoverageGapLabels -Payload $payload
        $message = "Browser route coverage audit failed: $uncoveredCount uncovered route-method(s). $($labels -join '; ')"
        throw $message
    }

    $message = "[OK] browser route coverage -> $($summary.covered_monolith_route_method_count)/$($summary.monolith_route_method_count) covered"
    Write-Host $message
}

function Write-RollbackRouteCoverageSummary {
    $payload = Invoke-RouteCoverageAudit -Surface 'rollback'
    $summary = $payload.summary
    $uncoveredCount = [int]$summary.uncovered_monolith_route_method_count
    if ($uncoveredCount -eq 0) {
        Write-Host '[OK] rollback route coverage -> no rollback-only gaps remain.'
        return
    }

    $labels = Get-RouteCoverageGapLabels -Payload $payload
    $message = "[INFO] rollback route coverage -> $uncoveredCount rollback-only route-method(s) remain: $($labels -join '; ')"
    Write-Host $message
}

if ($SkipLocal -and $SkipRemote -and $SkipBrowserCoverageAudit) {
    throw 'At least one validation dimension must stay enabled.'
}

$localPreview = Normalize-BaseUrl $LocalPreviewBase
$localGateway = Normalize-BaseUrl $LocalGatewayBase
$localSpeech = Normalize-BaseUrl $LocalSpeechBase
$remote = Normalize-BaseUrl $RemoteBase

if (-not $SkipBrowserCoverageAudit) {
    Write-Host 'Running browser route coverage audit...'
    Assert-BrowserRouteCoverage
}

if (-not $SkipRollbackCoverageAudit) {
    Write-Host 'Summarizing rollback-only route coverage...'
    Write-RollbackRouteCoverageSummary
}

if (-not $SkipLocal) {
    Write-Host 'Running local Wave 6C cutover checks...'
    Invoke-ExpectedRequest -Label 'local gateway ready' -Url "$localGateway/ready"
    Invoke-ExpectedRequest -Label 'local speech ready' -Url "$localSpeech/ready"
    Invoke-ExpectedRequest -Label 'local preview login' -Url "$localPreview/login"
    Invoke-ExpectedRequest -Label 'local preview api proxy' -Url "$localPreview/api/books/stats"
    Invoke-ExpectedRequest -Label 'local socket.io polling handshake' -Url "$localSpeech/socket.io/?EIO=4&transport=polling"
}

if (-not $SkipRemote) {
    Write-Host 'Running remote Wave 6C cutover checks...'
    Invoke-ExpectedRequest -Label 'remote frontend' -Url "$remote/"
    Invoke-ExpectedRequest -Label 'remote api proxy' -Url "$remote/api/books"
    Invoke-ExpectedRequest -Label 'remote socket.io polling handshake' -Url "$remote/socket.io/?EIO=4&transport=polling"
}

Write-Host '[DONE] Wave 6C cutover validation checks passed.'
