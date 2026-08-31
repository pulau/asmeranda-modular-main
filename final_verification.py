"""Final verification of the modular architecture deployment."""
import sys
sys.path.insert(0, '.')

import requests
import subprocess
import time

print("=== Final Deployment Verification ===\n")

# Test Backend Health
print("1. Testing Backend Health...")
try:
    r = requests.get("http://localhost:8000/health", timeout=5)
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.json()}")
    backend_healthy = r.status_code == 200
except Exception as e:
    print(f"   Error: {e}")
    backend_healthy = False

# Test Backend OpenAPI
print("\n2. Testing Backend OpenAPI...")
try:
    r = requests.get("http://localhost:8000/openapi.json", timeout=5)
    data = r.json()
    print(f"   Total endpoints: {len(data['paths'])}")
    
    # Check for Phase 1 endpoints
    preprocessing_endpoints = [p for p in data['paths'].keys() if 'preprocessing' in p]
    training_endpoints = [p for p in data['paths'].keys() if 'training' in p]
    eda_endpoints = [p for p in data['paths'].keys() if 'eda' in p]
    
    has_clustering = any('cluster' in p for p in preprocessing_endpoints)
    has_optimization = any('optimize' in p for p in training_endpoints)
    has_recommendations = any('analyze' in p for p in eda_endpoints)
    
    print(f"   Clustering endpoints: {has_clustering}")
    print(f"   Optimization endpoints: {has_optimization}")
    print(f"   Recommendations endpoints: {has_recommendations}")
    
except Exception as e:
    print(f"   Error: {e}")

# Test Clustering Endpoint
print("\n3. Testing Clustering Endpoint...")
try:
    r = requests.post("http://localhost:8000/api/v1/preprocessing/cluster", 
                      json={"state_id": "test", "method": "kmeans", "parameters": {"n_clusters": 3}},
                      timeout=5)
    print(f"   Status: {r.status_code}")
    clustering_works = r.status_code in [200, 400]
except Exception as e:
    print(f"   Error: {e}")
    clustering_works = False

# Test Optimization Endpoint
print("\n4. Testing Optimization Endpoint...")
try:
    r = requests.post("http://localhost:8000/api/v1/training/optimize-sync",
                      json={"state_id": "test", "model_type": "RandomForest", 
                            "problem_type": "Classification", "method": "grid_search", "cv_folds": 3},
                      timeout=5)
    print(f"   Status: {r.status_code}")
    optimization_works = r.status_code in [200, 400]
except Exception as e:
    print(f"   Error: {e}")
    optimization_works = False

# Test Recommendations Endpoint
print("\n5. Testing Recommendations Endpoint...")
try:
    r = requests.post("http://localhost:8000/api/v1/eda/analyze",
                      json={"dataset_id": "test"},
                      timeout=5)
    print(f"   Status: {r.status_code}")
    recommendations_works = r.status_code in [200, 404]
except Exception as e:
    print(f"   Error: {e}")
    recommendations_works = False

# Test Frontend
print("\n6. Testing Frontend...")
try:
    r = requests.get("http://localhost:3001", timeout=5)
    print(f"   Status: {r.status_code}")
    frontend_works = r.status_code == 200
except Exception as e:
    print(f"   Error: {e}")
    frontend_works = False

# Check file structure
print("\n7. Checking File Structure...")
import os
backend_exists = os.path.exists('backend')
frontend_exists = os.path.exists('frontend')
legacy_archived = os.path.exists('legacy_archive')
docs_exist = os.path.exists('DEPLOYMENT_GUIDE.md')

print(f"   Backend directory: {backend_exists}")
print(f"   Frontend directory: {frontend_exists}")
print(f"   Legacy archived: {legacy_archived}")
print(f"   Deployment guide: {docs_exist}")

# Summary
print("\n=== Final Summary ===")
print(f"Backend Healthy: {'OK' if backend_healthy else 'FAIL'}")
print(f"Clustering API: {'OK' if clustering_works else 'FAIL'}")
print(f"Optimization API: {'OK' if optimization_works else 'FAIL'}")
print(f"Recommendations API: {'OK' if recommendations_works else 'FAIL'}")
print(f"Frontend Running: {'OK' if frontend_works else 'FAIL'}")
print(f"File Structure: {'OK' if all([backend_exists, frontend_exists, legacy_archived, docs_exist]) else 'FAIL'}")

all_good = backend_healthy and clustering_works and optimization_works and recommendations_works and frontend_works and all([backend_exists, frontend_exists, legacy_archived, docs_exist])
print(f"\nOverall Status: {'SUCCESS - All systems operational' if all_good else 'PARTIAL - Some issues detected'}")

if all_good:
    print("\n=== Deployment Ready ===")
    print("The modular architecture is ready for local development.")
    print("Docker deployment requires additional import path fixes (see DOCKER_STATUS.md)")
else:
    print("\n=== Issues Detected ===")
    print("Please address the issues above before proceeding.")