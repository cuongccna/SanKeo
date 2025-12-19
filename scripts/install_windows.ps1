# PowerShell script for Windows local development setup
Write-Host "=== SanKeo Local Development Setup ===" -ForegroundColor Green

# Check Python
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python not found! Please install Python 3.10+" -ForegroundColor Red
    exit 1
}
Write-Host "Found: $pythonVersion" -ForegroundColor Cyan

# Create Virtual Environment
Write-Host "`nCreating virtual environment..." -ForegroundColor Yellow
python -m venv venv

# Activate venv
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Install packages
Write-Host "`nInstalling Python packages..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host "`n=== Setup Complete ===" -ForegroundColor Green
Write-Host @"

Next steps:
1. Configure .env file with your credentials
2. Ensure PostgreSQL is running (sankeo_db database)
3. Ensure Redis is running (localhost:6379)
4. Run: python init_db.py (to create tables)
5. Run services:
   - Bot:      python -m src.bot.main
   - Worker:   python -m src.worker.main
   - Ingestor: python -m src.ingestor.main
"@ -ForegroundColor Cyan
