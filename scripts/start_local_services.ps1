# Local stack launcher (no Docker)
# Starts gateway + microservices. Dashboard should already be running or start separately.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
New-Item -ItemType Directory -Force -Path "$Root\logs" | Out-Null

$uv = Join-Path $Root "venv\Scripts\uvicorn.exe"
if (-not (Test-Path $uv)) {
    Write-Error "Missing venv uvicorn at $uv. Run: .\venv\Scripts\python.exe -m pip install -e . --no-deps"
    exit 1
}

$services = @(
    @{ Name = "gateway";  App = "backend.api.main:app";                 Port = 8000 },
    @{ Name = "twin";     App = "simulator.api.main:app";               Port = 8001 },
    @{ Name = "scenario"; App = "simulator.scenarios.api:app";          Port = 8002 },
    @{ Name = "risk";     App = "risk.api.main:app";                    Port = 8003 },
    @{ Name = "rag";      App = "knowledge.api.main:app";               Port = 8004 },
    @{ Name = "copilot";  App = "copilot.api.main:app";                 Port = 8005 },
    @{ Name = "forecast"; App = "backend.services.forecast.main:app";   Port = 8006 }
)

foreach ($svc in $services) {
    $listening = Get-NetTCPConnection -LocalPort $svc.Port -State Listen -ErrorAction SilentlyContinue
    if ($listening) {
        Write-Host ("{0} already on :{1}" -f $svc.Name, $svc.Port)
        continue
    }
    $out = Join-Path $Root ("logs\svc-{0}.out.log" -f $svc.Name)
    $err = Join-Path $Root ("logs\svc-{0}.err.log" -f $svc.Name)
    Start-Process -FilePath $uv -ArgumentList @($svc.App, "--host", "127.0.0.1", "--port", "$($svc.Port)") `
        -WorkingDirectory $Root -RedirectStandardOutput $out -RedirectStandardError $err -NoNewWindow
    Write-Host ("started {0} on :{1}" -f $svc.Name, $svc.Port)
}

Write-Host ""
Write-Host "Dashboard: streamlit run dashboard/app.py --server.port 8501"
Write-Host "Gateway:   http://127.0.0.1:8000/docs"
