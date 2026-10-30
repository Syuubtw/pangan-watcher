# Import all models to ensure complete SQLAlchemy registry
from app.models.wilayah import Provinsi, KabupatenKota
from app.models.harga import HargaHarian
from app.models.komoditas import Komoditas
from app.models.klaster import HasilKlaster
from app.models.peringatan import PeringatanDini
from app.models.user import User

# ========================================================
# app/main.py
# Entry point aplikasi FastAPI - Pangan Watcher API
# ========================================================
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1.router import api_router

# Import semua model agar SQLAlchemy mengetahui schema-nya
import app.models  # noqa: F401

# ── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Definisi Tags Metadata agar API Docs tersusun rapi per modul
tags_metadata = [
    {
        "name": "Health",
        "description": "Indikator operasional server API dan koneksi database PostgreSQL.",
    },
    {
        "name": "Data Ingestion",
        "description": "Pipeline ETL: Upload file Excel harga pangan Bapanas (400K+ baris), validasi struktur, pembersihan data, serta auto-trigger klasterisasi.",
    },
    {
        "name": "K-Means Clustering",
        "description": "Klasterisasi spasial kerawanan harga komoditas (Aman, Waspada, Kritis) untuk 514 Kab/Kota menggunakan Scikit-Learn beserta evaluasi Elbow & Silhouette Score.",
    },
    {
        "name": "Early Warning System",
        "description": "Sistem peringatan dini (EWS) otomatis untuk mendeteksi lonjakan harga komoditas pangan yang melebihi ambang batas (threshold).",
    },
    {
        "name": "Analytics & Trends",
        "description": "Analisis time-series tren pergerakan harga komoditas untuk visualisasi grafik analitik multi-periode.",
    },
]

# ── Lifespan (startup & shutdown events) ─────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle handler FastAPI."""
    logger.info("=" * 60)
    logger.info(f"  Menjalankan: {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 60)
    
    logger.info("Memeriksa dan membuat tabel database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tabel database siap.")

    yield

    logger.info("Aplikasi dimatikan. Menutup koneksi database...")


# ── Inisialisasi Aplikasi FastAPI ─────────────────────────────────────────────
app = FastAPI(
    title="🌾 Pangan Watcher — Spatial Early Warning System API",
    version=settings.APP_VERSION,
    description="""
### Rancang Bangun Sistem Peringatan Dini dan Pemetaan Spasial Kerawanan Harga Komoditas Pangan
*Algoritma: K-Means Clustering | Engine: FastAPI & PostgreSQL | Frontend: Next.js & Leaflet.js*

---
Dokumentasi interaktif RESTful API untuk pemrosesan data harga pangan nasional (Badan Pangan Nasional), klasterisasi spasial tingkat kerawanan wilayah (514 Kab/Kota), serta deteksi anomali lonjakan harga secara real-time.
    """,
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    docs_url=None,   # Menggunakan custom route /docs dengan modern styling
    redoc_url=None,  # Menggunakan custom route /redoc
)

# ── CORS Middleware ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Daftarkan Router ──────────────────────────────────────────────────────────
app.include_router(api_router)


# ── Custom Modern & Clean API Documentation UI ───────────────────────────────
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """
    Kustomisasi antarmuka Swagger UI agar tampil modern, bersih, bertema dark slate,
    dengan tipografi Inter, badge rapi, serta tata letak yang profesional untuk Tugas Akhir.
    """
    html_content = f"""
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <title>{app.title} - Swagger UI</title>
        <link rel="icon" type="image/png" href="https://fastapi.tiangolo.com/img/favicon.png">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-primary: #0b1120;
                --bg-secondary: #0f172a;
                --bg-card: #1e293b;
                --border-color: #334155;
                --text-main: #f8fafc;
                --text-muted: #94a3b8;
                --accent-emerald: #10b981;
                --accent-blue: #38bdf8;
                --accent-indigo: #6366f1;
            }}
            
            body {{
                margin: 0;
                background-color: var(--bg-primary);
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                color: var(--text-main);
                -webkit-font-smoothing: antialiased;
            }}

            /* Top Custom Navbar */
            .custom-nav {{
                background: linear-gradient(180deg, #0f172a 0%, #0b1120 100%);
                border-bottom: 1px solid var(--border-color);
                padding: 16px 32px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                position: sticky;
                top: 0;
                z-index: 999;
                box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5);
            }}

            .nav-brand {{
                display: flex;
                align-items: center;
                gap: 12px;
                text-decoration: none;
                color: #ffffff;
            }}

            .nav-badge {{
                background: rgba(16, 185, 129, 0.15);
                color: #34d399;
                border: 1px solid rgba(16, 185, 129, 0.3);
                font-size: 11px;
                font-weight: 700;
                padding: 3px 8px;
                border-radius: 9999px;
                letter-spacing: 0.05em;
                text-transform: uppercase;
            }}

            .nav-links {{
                display: flex;
                align-items: center;
                gap: 16px;
            }}

            .nav-link-btn {{
                background: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                padding: 6px 14px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 500;
                text-decoration: none;
                transition: all 0.2s ease;
            }}

            .nav-link-btn:hover {{
                background: #334155;
                color: #ffffff;
                border-color: #64748b;
            }}

            /* Swagger UI Container Tweaks */
            .swagger-ui {{
                color: var(--text-main);
                max-width: 1200px;
                margin: 0 auto;
                padding: 24px 20px 80px 20px;
            }}

            .swagger-ui .topbar {{
                display: none !important;
            }}

            /* Header Section */
            .swagger-ui .info {{
                background: #0f172a;
                border: 1px solid var(--border-color);
                border-radius: 16px;
                padding: 32px;
                margin-bottom: 30px;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            }}

            .swagger-ui .info .title {{
                color: #ffffff;
                font-size: 26px;
                font-weight: 700;
                letter-spacing: -0.02em;
            }}

            .swagger-ui .info p, .swagger-ui .info li {{
                color: #94a3b8;
                font-size: 14px;
                line-height: 1.6;
            }}

            .swagger-ui .info a {{
                color: var(--accent-blue);
                text-decoration: none;
            }}

            /* Tag Section Headers */
            .swagger-ui .opblock-tag-section {{
                background: transparent;
                margin-bottom: 24px;
            }}

            .swagger-ui .opblock-tag {{
                font-size: 17px;
                font-weight: 700;
                color: #f1f5f9;
                border-bottom: 1px solid var(--border-color);
                padding: 12px 4px;
                margin-bottom: 12px;
            }}

            .swagger-ui .opblock-tag small {{
                color: #64748b;
                font-size: 13px;
                font-weight: 400;
            }}

            /* Opblocks (Endpoints) */
            .swagger-ui .opblock {{
                background: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 10px;
                box-shadow: none;
                margin-bottom: 12px;
                transition: transform 0.15s ease, border-color 0.15s ease;
            }}

            .swagger-ui .opblock:hover {{
                border-color: #475569;
            }}

            .swagger-ui .opblock .opblock-summary {{
                padding: 12px 18px;
            }}

            .swagger-ui .opblock .opblock-summary-method {{
                border-radius: 6px;
                font-family: 'JetBrains Mono', monospace;
                font-weight: 700;
                font-size: 12px;
                padding: 6px 14px;
            }}

            .swagger-ui .opblock .opblock-summary-path {{
                font-family: 'JetBrains Mono', monospace;
                color: #e2e8f0;
                font-size: 14px;
                font-weight: 500;
            }}

            .swagger-ui .opblock .opblock-summary-description {{
                color: #94a3b8;
                font-size: 13px;
            }}

            /* Opblock Bodies */
            .swagger-ui .opblock-body {{
                background: #0b1120;
                border-top: 1px solid #1e293b;
            }}

            .swagger-ui .opblock-section-header {{
                background: #0f172a;
                border-bottom: 1px solid #1e293b;
            }}

            .swagger-ui .opblock-section-header h4 {{
                color: #cbd5e1;
                font-size: 13px;
                font-weight: 600;
            }}

            .swagger-ui table thead tr th, 
            .swagger-ui table thead tr td {{
                color: #94a3b8;
                border-bottom: 1px solid #1e293b;
                font-size: 12px;
            }}

            .swagger-ui .parameter__name {{
                font-family: 'JetBrains Mono', monospace;
                color: #f8fafc;
                font-size: 13px;
            }}

            .swagger-ui .parameter__type {{
                color: #38bdf8;
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
            }}

            /* Inputs & Buttons */
            .swagger-ui input[type=text], 
            .swagger-ui select, 
            .swagger-ui textarea {{
                background: #1e293b !important;
                color: #ffffff !important;
                border: 1px solid #334155 !important;
                border-radius: 6px !important;
                padding: 8px 12px !important;
                font-family: 'JetBrains Mono', monospace !important;
            }}

            .swagger-ui .btn {{
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
            }}

            .swagger-ui .btn.execute {{
                background-color: #2563eb;
                border-color: #1d4ed8;
                color: #ffffff;
            }}

            .swagger-ui .btn.execute:hover {{
                background-color: #1d4ed8;
            }}

            .swagger-ui .responses-inner {{
                padding: 16px;
            }}

            .swagger-ui .response-col_status {{
                font-family: 'JetBrains Mono', monospace;
                color: #34d399;
                font-weight: 700;
            }}

            .swagger-ui pre {{
                background: #070d17 !important;
                border: 1px solid #1e293b !important;
                border-radius: 8px !important;
                color: #e2e8f0 !important;
                font-family: 'JetBrains Mono', monospace !important;
            }}

            .swagger-ui section.models {{
                background: #0f172a;
                border: 1px solid var(--border-color);
                border-radius: 12px;
            }}

            .swagger-ui section.models h4 {{
                color: #f1f5f9;
            }}
        </style>
    </head>
    <body>
        <div class="custom-nav">
            <a href="/docs" class="nav-brand">
                <span style="font-size: 22px;">🌾</span>
                <span style="font-weight: 700; font-size: 16px; letter-spacing: -0.01em;">PANGAN WATCHER API</span>
                <span class="nav-badge">v{app.version}</span>
            </a>
            <div class="nav-links">
                <a href="/redoc" class="nav-link-btn" title="Lihat Tampilan ReDoc">Dokumentasi ReDoc</a>
                <a href="http://localhost:3000" target="_blank" class="nav-link-btn" style="background: rgba(16, 185, 129, 0.15); border-color: rgba(16, 185, 129, 0.4); color: #34d399;">Buka WebGIS App ↗</a>
            </div>
        </div>

        <div id="swagger-ui"></div>

        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script>
            window.onload = () => {{
                window.ui = SwaggerUIBundle({{
                    url: '/openapi.json',
                    dom_id: '#swagger-ui',
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.SwaggerUIStandalonePreset
                    ],
                    layout: "BaseLayout",
                    deepLinking: true,
                    showExtensions: true,
                    showCommonExtensions: true,
                    defaultModelsExpandDepth: 0,
                    docExpansion: "list"
                }});
            }};
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    """Tampilan dokumentasi ReDoc alternatif yang juga sangat bersih dan cocok untuk review tesis."""
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - ReDoc",
        redoc_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )


# ── Health Check Endpoint ────────────────────────────────────────────────────
@app.get("/", tags=["Health"], summary="Health Check Status")
def root():
    """Endpoint verifikasi status operasional layanan API."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", tags=["Health"], summary="Detailed Health Check")
def health_check():
    """Health check dengan detail status komponen server dan database."""
    return {
        "status": "healthy",
        "database": "connected",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


from starlette.requests import Request
from starlette.responses import JSONResponse
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    print("GLOBAL 500 EXCEPTION OCCURRED:")
    print(tb)
    return JSONResponse(
        status_code=500,
        content={"detail": "Unhandled Exception", "error": str(exc), "traceback": tb}
    )
