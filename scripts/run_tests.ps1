# Run tests across backend and frontend
Write-Host "Running Backend Tests..." -ForegroundColor Cyan
$env:PYTHONPATH = "$PWD/backend/src"
python -m pytest backend/tests tests/

if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend tests failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Running Frontend Type Checks..." -ForegroundColor Cyan
Set-Location -Path "$PWD/frontend"
npm run lint

if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend checks failed!" -ForegroundColor Red
    exit 1
}

Write-Host "All tests and type checks passed successfully!" -ForegroundColor Green
