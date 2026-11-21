# Reset the app to the documented baseline (Windows PowerShell).
# Wipes the database volume, restarts the stack, waits until the app answers,
# then verifies the seeded data. Run from anywhere inside the repository:
#   powershell -ExecutionPolicy Bypass -File tests/team/baseline/reset.ps1
param([int]$TimeoutSeconds = 900)

Set-Location (git rev-parse --show-toplevel)
$compose = @("compose", "-f", "docker-compose-dev.yml")

Write-Host "1/4 Stopping the stack and deleting its volumes (database, redis, backups)..."
docker @compose down -v
if ($LASTEXITCODE -ne 0) { throw "docker compose down -v failed" }

Write-Host "2/4 Starting the stack (the seed runs automatically on an empty database)..."
docker @compose up -d
if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }

Write-Host "3/4 Waiting for http://localhost:8000/api/v1/version/ (up to $TimeoutSeconds s)..."
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$ready = $false
while ((Get-Date) -lt $deadline) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/version/" -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 5
}
if (-not $ready) { throw "The app did not become ready in $TimeoutSeconds s. Run: docker compose -f docker-compose-dev.yml logs web" }

Write-Host "4/4 Checking the baseline data..."
Get-Content "tests/team/baseline/check_seed.py" -Raw | docker @compose exec -T web python manage.py shell
if ($LASTEXITCODE -ne 0) { throw "Baseline data check failed" }
Write-Host "Reset complete."
