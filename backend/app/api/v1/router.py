# ========================================================
# app/api/v1/router.py
# Router utama API v1 - semua endpoint terdaftar di sini
# ========================================================
from fastapi import APIRouter
from app.api.v1.endpoints import upload, clusters, alerts, trends

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(upload.router)    # POST /api/v1/upload/
api_router.include_router(clusters.router)  # GET/POST /api/v1/clusters/
api_router.include_router(alerts.router)    # GET/POST /api/v1/alerts/
api_router.include_router(trends.router)    # GET /api/v1/trends/
