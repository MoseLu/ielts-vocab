param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Command
)

$ErrorActionPreference = 'Stop'

# Keep stdout/stderr predictable when PowerShell proxies Git Bash output.
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:CHERE_INVOKING = '1'
$programFilesX86 = ${env:ProgramFiles(x86)}

$commandEntry = Get-Command bash.exe -ErrorAction SilentlyContinue
$bashCandidates = @(
    if ($commandEntry) { $commandEntry.Source }
    Join-Path $env:ProgramFiles 'Git\bin\bash.exe'
    Join-Path $env:ProgramFiles 'Git\usr\bin\bash.exe'
    if ($programFilesX86) { Join-Path $programFilesX86 'Git\bin\bash.exe' }
    if ($programFilesX86) { Join-Path $programFilesX86 'Git\usr\bin\bash.exe' }
    Join-Path $env:LocalAppData 'Programs\Git\bin\bash.exe'
    Join-Path $env:LocalAppData 'Programs\Git\usr\bin\bash.exe'
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -Unique

if (-not $bashCandidates) {
    throw "Git Bash was not found. Install Git for Windows or add bash.exe to PATH."
}

$bashPath = $bashCandidates[0]
& $bashPath --noprofile --norc -lc $Command
exit $LASTEXITCODE
