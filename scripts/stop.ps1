# Stop GlueUp Circle Bridge services

Write-Host "🛑 Stopping GlueUp Circle Bridge services..." -ForegroundColor Yellow

# Find and kill Flask backend
$flaskProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*src.web.server*"
}

if ($flaskProcesses) {
    foreach ($proc in $flaskProcesses) {
        Write-Host "  Stopping Flask backend (PID: $($proc.Id))..." -ForegroundColor Cyan
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "  ✅ Flask stopped" -ForegroundColor Green
} else {
    Write-Host "  ℹ️  Flask backend not running" -ForegroundColor Gray
}

# Find and kill Streamlit
$streamlitProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*streamlit*"
}

if ($streamlitProcesses) {
    foreach ($proc in $streamlitProcesses) {
        Write-Host "  Stopping Streamlit (PID: $($proc.Id))..." -ForegroundColor Cyan
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "  ✅ Streamlit stopped" -ForegroundColor Green
} else {
    Write-Host "  ℹ️  Streamlit not running" -ForegroundColor Gray
}

# Also stop any PowerShell jobs
$jobs = Get-Job -ErrorAction SilentlyContinue
if ($jobs) {
    Write-Host "  Stopping background jobs..." -ForegroundColor Cyan
    Stop-Job -Job $jobs -ErrorAction SilentlyContinue
    Remove-Job -Job $jobs -ErrorAction SilentlyContinue
}

Write-Host "✅ All services stopped" -ForegroundColor Green
