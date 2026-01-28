# Quick setup script for GlueUp Circle Bridge UI

Write-Host "🔄 Setting up GlueUp Circle Bridge Web UI..." -ForegroundColor Green
Write-Host ""

# Check Python version
try {
    $pythonVersion = (python --version 2>&1) -replace 'Python ', ''
    Write-Host "✅ Found Python $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.8 or higher" -ForegroundColor Red
    Write-Host "   Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Check if virtual environment exists
if (-not (Test-Path ".venv")) {
    Write-Host "📦 Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ Virtual environment already exists" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Cyan
& .\.venv\Scripts\Activate.ps1

# Install backend dependencies
if (Test-Path "requirements.txt") {
    Write-Host "📦 Installing backend dependencies..." -ForegroundColor Cyan
    python -m pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Some backend dependencies may have failed to install" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  requirements.txt not found, skipping backend dependencies" -ForegroundColor Yellow
}

# Install UI dependencies
if (Test-Path "requirements-ui.txt") {
    Write-Host "📦 Installing UI dependencies..." -ForegroundColor Cyan
    pip install --quiet -r requirements-ui.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Some UI dependencies may have failed to install" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  requirements-ui.txt not found, skipping UI dependencies" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To start the application:" -ForegroundColor White
Write-Host ""
Write-Host "  Quick start:" -ForegroundColor Cyan
Write-Host "    .\scripts\start.ps1" -ForegroundColor White
Write-Host ""
Write-Host "  Or manually (two terminals):" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Terminal 1 (Backend):" -ForegroundColor Yellow
Write-Host "    .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "    python -m src.web.server" -ForegroundColor White
Write-Host ""
Write-Host "  Terminal 2 (UI):" -ForegroundColor Yellow
Write-Host "    .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "    streamlit run streamlit_app.py" -ForegroundColor White
Write-Host ""
