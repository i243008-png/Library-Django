# Does the last steps of Umm-e-Sulaim's part. Run from the repo root:
#   powershell -ExecutionPolicy ByPass -File tests\team\finish.ps1
$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repo
$py = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "Cannot find .venv. Create it first (python -m venv .venv, then pip install -r tests/team/api/requirements-team.txt)." -ForegroundColor Red; exit 1 }

Set-Location (Join-Path $repo "tests\team\docs")
$out = Join-Path (Get-Location) "evidence_output.txt"
"Evidence output - generated $(Get-Date -Format 'yyyy-MM-dd HH:mm')" | Out-File $out -Encoding utf8

function Run($title, $args_) {
    Write-Host "==> $title" -ForegroundColor Cyan
    "`n=== $title ===" | Out-File $out -Append -Encoding utf8
    $result = & $py @args_ 2>&1
    $result | ForEach-Object { "$_" } | Tee-Object -FilePath $out -Append
}

Run "Fishbone DEF-01" @("fishbone.py", "rca_1.json")
Run "Fishbone DEF-03" @("fishbone.py", "rca_2.json")
Run "GQM metrics" @("gqm_metrics.py", "--executed", "93", "--passed", "87")
Run "Pareto chart" @("pareto.py")

Set-Location $repo
Write-Host "==> Saving to Git" -ForegroundColor Cyan
if (-not (git config user.name)) {
    git config user.name "Umm-e-Sulaim Rana"
    git config user.email "ummesulaimrana@gmail.com"
}
git checkout umm-api-tests 2>$null
if ($LASTEXITCODE -ne 0) { git checkout -b umm-api-tests }
git add tests/team .github
git status --short
git commit -m "Add API tests, spec, generator, use cases UC-05 and UC-06, test plan, defects, RCA, weekly report"
git push -u origin umm-api-tests

Write-Host ""
Write-Host "DONE. Now open the team repo on github.com and click 'Compare & pull request'." -ForegroundColor Green
Write-Host "Raw outputs are saved in tests\team\docs\evidence_output.txt" -ForegroundColor Green
