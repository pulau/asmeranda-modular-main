# Docker Desktop Deployment Script for Asmeranda Modular Application
# This script uses Docker Desktop to run the application

Write-Host "🚀 Starting Asmeranda Modular Application (Docker Desktop Deployment)" -ForegroundColor Green

# Check if Docker Desktop is running
try {
    $dockerVersion = docker version --format '{{.Server.Version}}'
    Write-Host "✅ Docker Desktop is running (version: $dockerVersion)" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker Desktop is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Stop existing containers if they exist
Write-Host "🧹 Cleaning up existing containers..." -ForegroundColor Yellow
docker-compose down

# Build and start services
Write-Host "🔨 Building Docker images..." -ForegroundColor Yellow
docker-compose build

Write-Host "🚀 Starting services..." -ForegroundColor Yellow
docker-compose up -d

# Wait for services to start
Write-Host "⏳ Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Check if services are running
$backendRunning = docker inspect -f '{{.State.Running}}' asmeranda-backend
$frontendRunning = docker inspect -f '{{.State.Running}}' asmeranda-frontend

if ($backendRunning -eq "true" -and $frontendRunning -eq "true") {
    Write-Host "✅ Services started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🌐 Access the application at:" -ForegroundColor Cyan
    Write-Host "   Frontend: http://localhost:3000" -ForegroundColor White
    Write-Host "   Backend API: http://localhost:8000" -ForegroundColor White
    Write-Host "   API Docs: http://localhost:8000/docs" -ForegroundColor White
    Write-Host ""
    Write-Host "📊 View logs with: docker-compose logs -f" -ForegroundColor Cyan
    Write-Host "🛑 Stop services with: docker-compose down" -ForegroundColor Cyan
} else {
    Write-Host "❌ Services failed to start" -ForegroundColor Red
    Write-Host "Backend running: $backendRunning" -ForegroundColor Yellow
    Write-Host "Frontend running: $frontendRunning" -ForegroundColor Yellow
    docker-compose logs
    exit 1
}