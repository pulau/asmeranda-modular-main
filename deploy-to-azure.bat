@echo off
REM ===========================================================================
REM Asmeranda AI - Azure Container Apps deployment (full stack)
REM
REM Prasyarat:
REM   - Azure CLI terpasang (https://aka.ms/install-azure-cli)
REM   - Docker Desktop berjalan
REM   - Login: az login
REM   - ACR & Container Apps Environment sudah ada (lihat AZURE_DEPLOYMENT_GUIDE.md)
REM
REM Variabel yang harus di-set sebelum menjalankan (atau diedit di sini):
REM   - RESOURCE_GROUP : nama resource group
REM   - ACR_NAME       : nama Azure Container Registry (lowercase, no dashes)
REM   - CONTAINER_APP  : nama Container App
REM   - CONTAINER_ENV  : nama Container Apps Environment
REM
REM Contoh:
REM   set RESOURCE_GROUP=asmeranda-rg
REM   set ACR_NAME=asmerandaacr
REM   set CONTAINER_APP=asmeranda
REM   set CONTAINER_ENV=asmeranda-env
REM   deploy-to-azure.bat
REM ===========================================================================

if "%RESOURCE_GROUP%"=="" set RESOURCE_GROUP=asmeranda-rg
if "%ACR_NAME%"=="" set ACR_NAME=asmerandaacr
if "%CONTAINER_APP%"=="" set CONTAINER_APP=asmeranda
if "%CONTAINER_ENV%"=="" set CONTAINER_ENV=asmeranda-env
if "%LOCATION%"=="" set LOCATION=southeastasia

set IMAGE_TAG=latest
set IMAGE=%ACR_NAME%.azurecr.io/asmeranda:%IMAGE_TAG%

echo ===========================================================================
echo  Asmeranda AI - Azure Deployment (Full Stack)
echo  RG:     %RESOURCE_GROUP%
echo  ACR:    %ACR_NAME%
echo  APP:    %CONTAINER_APP%
echo  ENV:    %CONTAINER_ENV%
echo  LOC:    %LOCATION%
echo  IMAGE:  %IMAGE%
echo ===========================================================================

REM --- 1) Login ACR
echo.
echo [1/6] Login ke Azure Container Registry...
az acr login --name %ACR_NAME%
if errorlevel 1 goto :error

REM --- 2) Build image (multi-stage: frontend Next.js + backend FastAPI)
echo.
echo [2/6] Build Docker image (multi-stage: frontend + backend)...
docker build -f Dockerfile.azure -t %IMAGE% .
if errorlevel 1 goto :error

REM --- 3) Push ke ACR
echo.
echo [3/6] Push image ke ACR...
docker push %IMAGE%
if errorlevel 1 goto :error

REM --- 4) Pastikan resource group
echo.
echo [4/6] Memastikan resource group...
az group show --name %RESOURCE_GROUP% >nul 2>&1 || (
    az group create --name %RESOURCE_GROUP% --location %LOCATION%
)

REM --- 5) Container Apps Environment
echo.
echo [5/6] Memastikan Container Apps Environment...
az containerapp env show --name %CONTAINER_ENV% --resource-group %RESOURCE_GROUP% >nul 2>&1 || (
    echo   Creating environment %CONTAINER_ENV%...
    az containerapp env create --name %CONTAINER_ENV% --resource-group %RESOURCE_GROUP% --location %LOCATION%
)

REM --- 6) Deploy Container App (full stack - 2 containers dalam 1 app)
echo.
echo [6/6] Deploy Container App dengan 2 containers (backend + frontend)...
az containerapp create ^
    --name %CONTAINER_APP% ^
    --resource-group %RESOURCE_GROUP% ^
    --environment %CONTAINER_ENV% ^
    --image %IMAGE% ^
    --registry-server %ACR_NAME%.azurecr.io ^
    --registry-username %ACR_NAME% ^
    --registry-password "$(az acr credential show --name %ACR_NAME% --query 'passwords[0].value' -o tsv)" ^
    --ingress external ^
    --target-port 3000 ^
    --env-vars-file azure.env ^
    --query properties.configuration.ingress.fqdn

if errorlevel 1 goto :error

echo.
echo ===========================================================================
echo  DEPLOY BERHASIL
echo  Buka: https://%CONTAINER_APP%.%LOCATION%.azurecontainer.io
echo  (atau lihat FQDN di atas)
echo.
echo  Catatan: Container App berisi 2 container:
echo    - backend  (FastAPI di 8000, internal)
echo    - frontend (Next.js di 3000, ekspos publik)
echo  Routing /api/* dari frontend ke backend diatur oleh next.config.js
echo ===========================================================================
goto :eof

:error
echo.
echo [ERROR] Deployment gagal. Periksa output di atas.
exit /b 1
