# Powershell script to run backend and frontend concurrently
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting RAMP (SIH26080) Local Development Environment" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Start Backend in background
Write-Host "Starting FastAPI backend on http://localhost:8000..." -ForegroundColor Green
$backendJob = Start-Job -ScriptBlock {
    Set-Location -Path "$using:PWD/backend"
    $env:PYTHONPATH = "src"
    python -m uvicorn ramp.main:app --reload --host 0.0.0.0 --port 8000
}

# 2. Start Frontend
Write-Host "Starting Vite frontend on http://localhost:5173..." -ForegroundColor Green
Set-Location -Path "$PWD/frontend"
npm run dev

# Cleanup job on exit
Stop-Job $backendJob
Remove-Job $backendJob
