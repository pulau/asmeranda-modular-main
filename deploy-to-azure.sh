#!/usr/bin/env bash
# ===========================================================================
# Asmeranda AI - Azure Container Apps deployment (full stack)
#
# Prasyarat:
#   - Azure CLI terpasang (https://aka.ms/install-azure-cli)
#   - Docker berjalan
#   - az login
#   - ACR & Container Apps Environment sudah ada (lihat AZURE_DEPLOYMENT_GUIDE.md)
#
# Variabel environment (atau diedit di sini):
#   - RESOURCE_GROUP : nama resource group
#   - ACR_NAME       : nama Azure Container Registry (lowercase)
#   - CONTAINER_APP  : nama Container App
#   - CONTAINER_ENV  : nama Container Apps Environment
#   - LOCATION       : Azure region (default southeastasia)
#
# Contoh:
#   export RESOURCE_GROUP=asmeranda-rg
#   export ACR_NAME=asmerandaacr
#   export CONTAINER_APP=asmeranda
#   export CONTAINER_ENV=asmeranda-env
#   ./deploy-to-azure.sh
# ===========================================================================
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-asmeranda-rg}"
ACR_NAME="${ACR_NAME:-asmerandaacr}"
CONTAINER_APP="${CONTAINER_APP:-asmeranda}"
CONTAINER_ENV="${CONTAINER_ENV:-asmeranda-env}"
LOCATION="${LOCATION:-southeastasia}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE="${ACR_NAME}.azurecr.io/asmeranda:${IMAGE_TAG}"

echo "=============================================================================="
echo " Asmeranda AI - Azure Deployment (Full Stack)"
echo " RG:     ${RESOURCE_GROUP}"
echo " ACR:    ${ACR_NAME}"
echo " APP:    ${CONTAINER_APP}"
echo " ENV:    ${CONTAINER_ENV}"
echo " LOC:    ${LOCATION}"
echo " IMAGE:  ${IMAGE}"
echo "=============================================================================="

# 1) Login ACR
echo
echo "[1/6] Login ke Azure Container Registry..."
az acr login --name "${ACR_NAME}"

# 2) Build image (multi-stage: frontend Next.js + backend FastAPI)
echo
echo "[2/6] Build Docker image (multi-stage: frontend + backend)..."
docker build -f Dockerfile.azure -t "${IMAGE}" .

# 3) Push ke ACR
echo
echo "[3/6] Push image ke ACR..."
docker push "${IMAGE}"

# 4) Resource group
echo
echo "[4/6] Memastikan resource group..."
if ! az group show --name "${RESOURCE_GROUP}" >/dev/null 2>&1; then
    az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}"
fi

# 5) Container Apps Environment
echo
echo "[5/6] Memastikan Container Apps Environment..."
if ! az containerapp env show --name "${CONTAINER_ENV}" --resource-group "${RESOURCE_GROUP}" >/dev/null 2>&1; then
    echo "  Creating environment ${CONTAINER_ENV}..."
    az containerapp env create \
        --name "${CONTAINER_ENV}" \
        --resource-group "${RESOURCE_GROUP}" \
        --location "${LOCATION}"
fi

# 6) Deploy Container App (multi-container)
echo
echo "[6/6] Deploy Container App dengan 2 containers (backend + frontend)..."

# Cek apakah Container App sudah ada
if az containerapp show --name "${CONTAINER_APP}" --resource-group "${RESOURCE_GROUP}" >/dev/null 2>&1; then
    echo "  Updating existing Container App..."
    az containerapp update \
        --name "${CONTAINER_APP}" \
        --resource-group "${RESOURCE_GROUP}" \
        --image "${IMAGE}" \
        --set-env-vars-file azure.env
else
    echo "  Creating new Container App..."
    ACR_PASSWORD=$(az acr credential show --name "${ACR_NAME}" --query 'passwords[0].value' -o tsv)
    az containerapp create \
        --name "${CONTAINER_APP}" \
        --resource-group "${RESOURCE_GROUP}" \
        --environment "${CONTAINER_ENV}" \
        --image "${IMAGE}" \
        --registry-server "${ACR_NAME}.azurecr.io" \
        --registry-username "${ACR_NAME}" \
        --registry-password "${ACR_PASSWORD}" \
        --ingress external \
        --target-port 3000 \
        --env-vars-file azure.env
fi

# Tampilkan FQDN
FQDN=$(az containerapp show --name "${CONTAINER_APP}" --resource-group "${RESOURCE_GROUP}" \
        --query properties.configuration.ingress.fqdn -o tsv)

echo
echo "=============================================================================="
echo " DEPLOY BERHASIL"
echo " Buka:  https://${FQDN}"
echo
echo " Catatan: Container App berisi 2 container:"
echo "   - backend  (FastAPI di 8000, internal)"
echo "   - frontend (Next.js di 3000, ekspos publik)"
echo " Routing /api/* dari frontend ke backend diatur oleh next.config.js"
echo "=============================================================================="
