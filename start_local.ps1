#!/usr/bin/env pwsh
# Start all services for local development
# Usage: powershell -ExecutionPolicy Bypass -File start_local.ps1

$ErrorActionPreference = "Continue"
$logDir = "logs\local"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

# Kill existing processes on our ports
Write-Host "=== Killing stale processes ===" -ForegroundColor Yellow
foreach ($port in @(8000,8001,8002,8003,8004,8005,8006,8007,8008,8501)) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($c in $connections) {
        $pid = $c.OwningProcess
        if ($pid -and $pid -ne 0) {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Host "  Killed PID $pid on port $port" -ForegroundColor Red
        }
    }
}
Start-Sleep -Seconds 2
Write-Host ""

$env:GATEWAY_API_KEY_ENABLED = "false"

# Service definitions: Name, Port, Module, HealthEndpoint, ExtraEnv
$services = @(
    @{Name="Twin State Manager"; Port=8001; Module="simulator.api.main"; Env=@{TWIN_STORE_DIR="data/twin_store"}},
    @{Name="Scenario Engine";    Port=8002; Module="simulator.scenarios.api"},
    @{Name="Risk Engine";        Port=8003; Module="risk.api.main"},
    @{Name="RAG Service";        Port=8004; Module="knowledge.api.main"; Env=@{VECTOR_STORE_DIR="knowledge/vector_store"}},
    @{Name="Copilot Agent";      Port=8005; Module="copilot.api.main"; Env=@{OLLAMA_HOST="http://localhost:11434";FORECAST_ENGINE_URL="http://localhost:8006";TWIN_ENGINE_URL="http://localhost:8001";RISK_ENGINE_URL="http://localhost:8003";REPORT_ENGINE_URL="http://localhost:8007";DISASTER_ENGINE_URL="http://localhost:8008"}},
    @{Name="Forecast Engine";    Port=8006; Module="backend.services.forecast.main"; Env=@{TWIN_STORE_DIR="data/twin_store"}},
    @{Name="Report Service";     Port=8007; Module="backend.api.report"},
    @{Name="Disaster Engine";    Port=8008; Module="disaster_intelligence.api.main"},
    @{Name="API Gateway";        Port=8000; Module="backend.api.main"; Env=@{GATEWAY_HOST="127.0.0.1";DISASTER_ENGINE_URL="http://localhost:8008";TWIN_ENGINE_URL="http://localhost:8001"}},
    @{Name="Dashboard";          Port=8501; Script="python -m streamlit run dashboard/app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false"}
)

foreach ($svc in $services) {
    $name = $svc.Name
    $port = $svc.Port
    $log = "$logDir\$($name.ToLower().Replace(' ','_')).log"
    
    Write-Host "Starting $name on port $port..." -ForegroundColor Cyan
    
    if ($svc.Script) {
        # Direct script (dashboard)
        $envCmd = ""
        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = "python"
        $startInfo.Arguments = "-m streamlit run dashboard/app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false"
        $startInfo.UseShellExecute = $false
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $startInfo.WorkingDirectory = (Get-Location).Path
        $proc = [System.Diagnostics.Process]::Start($startInfo)
        Write-Host "  PID: $($proc.Id)" -ForegroundColor Green
    } else {
        $module = $svc.Module
        $extraEnv = $svc.Env
        
        # Build environment block
        $envBlock = "set GATEWAY_API_KEY_ENABLED=false`r`n"
        $envBlock += "set TWIN_STORE_DIR=data/twin_store`r`n"
        $envBlock += "set OLLAMA_HOST=http://localhost:11434`r`n"
        $envBlock += "set VECTOR_STORE_DIR=knowledge/vector_store`r`n"
        foreach ($key in $extraEnv.Keys) {
            $envBlock += "set $key=$($extraEnv[$key])`r`n"
        }
        
        $cmd = "cmd /c `"cd /d D:\var-codes\satelite && $envBlock python -m uvicorn ${module}:app --host 127.0.0.1 --port $port`" 1> `"$log`" 2>&1"
        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = "cmd"
        $startInfo.Arguments = "/c cd /d D:\var-codes\satelite && python -m uvicorn ${module}:app --host 127.0.0.1 --port $port"
        $startInfo.UseShellExecute = $false
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $startInfo.WorkingDirectory = (Get-Location).Path
        # Set environment
        $startInfo.EnvironmentVariables["GATEWAY_API_KEY_ENABLED"] = "false"
        $startInfo.EnvironmentVariables["TWIN_STORE_DIR"] = "data\twin_store"
        $startInfo.EnvironmentVariables["OLLAMA_HOST"] = "http://localhost:11434"
        $startInfo.EnvironmentVariables["VECTOR_STORE_DIR"] = "knowledge\vector_store"
        foreach ($key in $extraEnv.Keys) {
            $startInfo.EnvironmentVariables[$key] = $extraEnv[$key]
        }
        $proc = [System.Diagnostics.Process]::Start($startInfo)
        Write-Host "  PID: $($proc.Id) Log: $log" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "=== All services started ===" -ForegroundColor Green
Write-Host "Waiting 15 seconds for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Health checks
Write-Host ""
Write-Host "=== Health Checks ===" -ForegroundColor Cyan
$healthUrls = @(
    @{Name="Twin State";    Url="http://127.0.0.1:8001/health"},
    @{Name="Scenario";      Url="http://127.0.0.1:8002/health"},
    @{Name="Risk";          Url="http://127.0.0.1:8003/health"},
    @{Name="RAG";           Url="http://127.0.0.1:8004/health"},
    @{Name="Copilot";       Url="http://127.0.0.1:8005/health"},
    @{Name="Forecast";      Url="http://127.0.0.1:8006/health"},
    @{Name="Report";        Url="http://127.0.0.1:8007/health"},
    @{Name="Disaster";      Url="http://127.0.0.1:8008/health"},
    @{Name="Gateway";       Url="http://127.0.0.1:8000/health"},
    @{Name="Dashboard";     Url="http://127.0.0.1:8501"}
)

foreach ($h in $healthUrls) {
    try {
        $resp = Invoke-WebRequest -Uri $h.Url -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-Host "  [OK]  $($h.Name) ($($h.Url)) -> $($resp.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] $($h.Name) ($($h.Url)) -> $($_.Exception.Message)" -ForegroundColor Red
    }
}
