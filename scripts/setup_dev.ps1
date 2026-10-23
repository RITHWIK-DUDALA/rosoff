# CDPR Development Environment Setup Script (PowerShell)
Write-Host "=== CDPR Development Environment Setup ===" -ForegroundColor Cyan

python --version
Write-Host "Installing Python backend dependencies..." -ForegroundColor Yellow
pip install -r backend/requirements.txt
pip install pytest pytest-asyncio pytest-cov jsonschema pyyaml

Write-Host "Validating configuration..." -ForegroundColor Yellow
python -c "from backend.cdpr.config import load_robot_config; cfg = load_robot_config(); print('Loaded config successfully. Robot ID:', cfg.robot_id)"

Write-Host "Setup complete. Ready to run simulation." -ForegroundColor Green
