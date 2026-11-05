$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'

$python = Join-Path $backend 'venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Host '未找到 backend\venv，请先按 README 创建虚拟环境并安装依赖。' -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Write-Host '未找到 frontend\node_modules，请先运行 npm install。' -ForegroundColor Yellow
    exit 1
}

Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$backend'; & '$python' -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$frontend'; npm run dev"

Write-Host '后端 API 文档: http://localhost:8000/docs' -ForegroundColor Green
Write-Host '前端开发服务器: http://localhost:5173' -ForegroundColor Green
