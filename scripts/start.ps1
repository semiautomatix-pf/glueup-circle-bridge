# Start both backend and frontend for GlueUp Circle Bridge

Write-Host "🚀 Starting GlueUp Circle Bridge..." -ForegroundColor Green
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path ".venv")) {
    Write-Host "❌ Virtual environment not found. Run setup-ui.ps1 first" -ForegroundColor Red
    exit 1
}

# Load .env file if it exists
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

$SERVER_PORT = $env:SERVER_PORT
if (-not $SERVER_PORT) {
    $SERVER_PORT = "8080"
}

Write-Host "🔧 Starting Flask backend on port $SERVER_PORT..." -ForegroundColor Cyan

# Start Flask backend in new window
$flaskJob = Start-Job -ScriptBlock {
    param($port)
    Set-Location $using:PWD
    & .\.venv\Scripts\Activate.ps1
    python -m src.web.server
} -ArgumentList $SERVER_PORT

# Wait for backend to be ready
Write-Host "⏳ Waiting for backend to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

$maxRetries = 10
$retries = 0
$backendReady = $false

while ($retries -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$SERVER_PORT/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Backend is ready!" -ForegroundColor Green
            $backendReady = $true
            break
        }
    } catch {
        # Backend not ready yet
    }
    $retries++
    Start-Sleep -Seconds 1
}

if (-not $backendReady) {
    Write-Host "❌ Backend failed to start" -ForegroundColor Red
    Stop-Job -Job $flaskJob
    Remove-Job -Job $flaskJob
    exit 1
}

Write-Host ""
Write-Host "🌐 Starting Streamlit UI..." -ForegroundColor Cyan

# Start Streamlit in new window
$streamlitJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    & .\.venv\Scripts\Activate.ps1
    streamlit run streamlit_app.py
}

Write-Host ""
Write-Host "📊 Services running:" -ForegroundColor Green
Write-Host "  - Flask backend: http://localhost:$SERVER_PORT (Job ID: $($flaskJob.Id))" -ForegroundColor White
Write-Host "  - Streamlit UI: http://localhost:8501 (Job ID: $($streamlitJob.Id))" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop, or run scripts\stop.ps1" -ForegroundColor Yellow
Write-Host ""

# Keep script running and monitor jobs
try {
    while ($true) {
        if ($flaskJob.State -eq "Failed" -or $streamlitJob.State -eq "Failed") {
            Write-Host "❌ One or more services failed" -ForegroundColor Red
            break
        }
        Start-Sleep -Seconds 2
    }
} finally {
    Write-Host ""
    Write-Host "🛑 Stopping services..." -ForegroundColor Yellow
    Stop-Job -Job $flaskJob, $streamlitJob -ErrorAction SilentlyContinue
    Remove-Job -Job $flaskJob, $streamlitJob -ErrorAction SilentlyContinue
    Write-Host "✅ Services stopped" -ForegroundColor Green
}
