$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$port = 9222

# Start Chrome with remote debugging
$proc = Start-Process $chromePath -ArgumentList "--remote-debugging-port=$port","--no-first-run","--no-default-browser-check" -PassThru -WindowStyle Hidden
Start-Sleep 3

try {
    # Get WebSocket debugger URL
    $json = Invoke-RestMethod "http://localhost:$port/json" -TimeoutSec 5
    $wsUrl = $json[0].webSocketDebuggerUrl

    Write-Host "Chrome started with CDP at ws://localhost:$port"
    Write-Host "WebSocket URL: $wsUrl"
    Write-Host "Page URL: $($json[0].url)"
} catch {
    Write-Host "CDP not accessible: $_"
    Write-Host "Process running: $($proc.HasExited)"
}

# Keep running for a bit
Start-Sleep 5
if (!$proc.HasExited) {
    Stop-Process $proc.Id -Force
    Write-Host "Chrome stopped"
}
