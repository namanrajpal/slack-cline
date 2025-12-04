# Quick setup script for slack-cline (Windows PowerShell)

Write-Host "🚀 Setting up slack-cline..." -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
try 
{
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) 
    {
        throw "Docker not running"
    }
} 
catch 
{
    Write-Host "❌ Error: Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check if .env exists
if (-not (Test-Path ".env")) 
{
    Write-Host "📝 Creating .env from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "⚠️  Please edit .env with your Slack credentials!" -ForegroundColor Yellow
}

# Compile proto files
Write-Host "🔧 Compiling proto files..." -ForegroundColor Cyan

# Create virtual environment if it doesn't exist
if (-not (Test-Path "backend\venv")) 
{
    Write-Host "Creating Python virtual environment..." -ForegroundColor Gray
    python -m venv backend\venv
}

# Activate virtual environment and install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Gray
& backend\venv\Scripts\Activate.ps1
pip install -q -r requirements.txt

# Compile proto files
Push-Location backend
python compile_protos.py
Pop-Location

Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Edit .env with your Slack credentials"
Write-Host "2. Run: docker-compose build"
Write-Host "3. Run: docker-compose up"
Write-Host "4. Run: ngrok http 8000 (in another terminal)"
Write-Host "5. Update Slack app URLs with ngrok URL"
Write-Host ""
Write-Host "Then test: /cline run create a readme file" -ForegroundColor Yellow
Write-Host ""
