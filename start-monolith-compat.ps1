param(
    [string]$ProjectRoot,
    [switch]$AllowDetachedRuntime,
    [switch]$AllowDirtyCompatibilityDrill,
    [int]$MonolithCompatBackendPort = 5000,
    [string]$MonolithCompatRouteGroups,
    [ValidateSet('browser', 'rollback', 'all')][string]$MonolithCompatSurface = 'all'
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$startupScript = Join-Path $scriptRoot 'start-project.ps1'

& $startupScript `
    -ProjectRoot $ProjectRoot `
    -AllowDetachedRuntime:$AllowDetachedRuntime `
    -AllowDirtyCompatibilityDrill:$AllowDirtyCompatibilityDrill `
    -MonolithCompatBackendPort $MonolithCompatBackendPort `
    -UseMonolithCompatibility `
    -MonolithCompatRouteGroups $MonolithCompatRouteGroups `
    -MonolithCompatSurface $MonolithCompatSurface
exit $LASTEXITCODE
