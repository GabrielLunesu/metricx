"""FastAPI application entrypoint.

Configures CORS, includes routers, and exposes a healthcheck endpoint.

CHANGES (2025-12-10):
    - Removed SQLAdmin panel (security risk, unused)
    - Added Clerk configuration validation at startup
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
import os
import logging
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

# Production logging: only warnings and errors to console
# Detailed logs go to observability tools (Sentry, Langfuse)
log_level = os.environ.get("LOG_LEVEL", "WARNING").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.WARNING))
logger = logging.getLogger(__name__)

# Initialize observability stack (Sentry, RudderStack, Langfuse)
# IMPORTANT: Must be done before FastAPI app is created for Sentry to capture all errors
from .telemetry import init_observability, shutdown_observability
_observability_status = init_observability()
if any(_observability_status.values()):
    enabled = [k for k, v in _observability_status.items() if v]
    logger.warning(f"[STARTUP] Observability: {', '.join(enabled)}")

from .deps import get_settings
from . import state
from .routers import auth as auth_router
from .routers import workspaces as workspaces_router
from .routers import connections as connections_router
from .routers import entities as entities_router
from .routers import metrics as metrics_router
from .routers import pnl as pnl_router
from .routers import kpis as kpis_router
from .routers import qa as qa_router
from .routers import qa_log as qa_log_router
from .routers import finance as finance_router
from .routers import entity_performance as entity_performance_router
from .routers import ingest as ingest_router  # Phase 1.2: Meta ingestion API
from .routers import meta_sync as meta_sync_router  # Phase 2: Meta entity and metrics sync
from .routers import google_sync as google_sync_router  # Google Ads sync endpoints
from .routers import google_oauth as google_oauth_router  # Google OAuth flow
from .routers import meta_oauth as meta_oauth_router  # Meta OAuth flow
from .routers import shopify_oauth as shopify_oauth_router  # Shopify OAuth flow
from .routers import shopify_sync as shopify_sync_router  # Shopify sync endpoints
from .routers import shopify_webhooks as shopify_webhooks_router  # Shopify compliance webhooks
from .routers import pixel_events as pixel_events_router  # Attribution pixel events
from .routers import attribution as attribution_router  # Attribution and pixel health
from .routers import dashboard_kpis as dashboard_kpis_router  # Dashboard KPIs with Shopify fallback
from .routers import dashboard as dashboard_router  # Unified dashboard endpoint
from .routers import clerk_webhooks as clerk_webhooks_router  # Clerk auth webhooks
from .routers import analytics as analytics_router  # Production analytics charts
from .routers import onboarding as onboarding_router  # Onboarding flow
from .routers import polar as polar_router  # Polar billing integration
from .routers import admin as admin_router  # Admin endpoints for bulk operations
from .routers import agents as agents_router  # Agent system for automated monitoring
from . import schemas

# Import models so Alembic can discover metadata
from . import models  # noqa: F401


def create_app() -> FastAPI:
    app = FastAPI(
        title="metricx API",
        description="""
        metricx is a comprehensive advertising analytics and optimization platform.
        
        This API provides endpoints for:
        - User authentication and workspace management
        - Ad platform connections (Google Ads, Meta, TikTok)
        - Campaign, ad set, and ad entity management
        - Performance metrics and analytics
        - P&L calculations and financial reporting
        - AI-powered query analytics
        
        ## Authentication
        
        The API uses JWT-based authentication with HTTP-only cookies for security.
        All authenticated endpoints require a valid JWT token obtained through the login endpoint.
        
        ## Data Model
        
        - **Workspaces**: Top-level containers for companies/organizations
        - **Users**: Individuals with access to workspaces (Owner, Admin, Viewer roles)
        - **Connections**: Links to advertising platform accounts
        - **Entities**: Hierarchical campaign structure (Account > Campaign > Ad Set > Ad)
        - **Metrics**: Performance data and analytics
        - **P&L**: Profit and loss calculations
        """,
        version="1.0.0",
        contact={
            "name": "metricx Support",
            "email": "support@metricx.com",
        },
        license_info={
            "name": "Proprietary",
        },
        servers=[
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            },
            {
                "url": "https://t8zgrthold5r2-backend--8000.prod2.defang.dev",
                "description": "Production server"
            }
        ]
    )
    
    # Add ProxyHeadersMiddleware to trust X-Forwarded-Proto headers from load balancers
    # This ensures request.url.scheme is correctly set to "https" in production
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

    settings = get_settings()

    # CORS configuration - support multiple origins from environment variable
    # BACKEND_CORS_ORIGINS can be a comma-separated list: "https://www.metricx.ai,http://localhost:3000"
    cors_origins_str = os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:3000")
    ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]
    
    # Always include localhost for development
    if "http://localhost:3000" not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append("http://localhost:3000")
    
    # Always include production domain
    if "https://www.metricx.ai" not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append("https://www.metricx.ai")
    
    # Get backend URL from environment (for Swagger UI same-origin requests)
    backend_url = os.getenv("BACKEND_URL") or os.getenv("DEFANG_SERVICE_URL")
    if backend_url:
        # Remove trailing slash and ensure it's in the list
        backend_url = backend_url.rstrip("/")
        if backend_url not in ALLOWED_ORIGINS:
            ALLOWED_ORIGINS.append(backend_url)
    
    logger.info(f"[CORS] Allowed origins: {ALLOWED_ORIGINS}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom middleware for pixel endpoint CORS (must be added AFTER CORSMiddleware)
    # Middleware runs in reverse order, so this runs BEFORE CORSMiddleware
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response as StarletteResponse

    class PixelCORSMiddleware(BaseHTTPMiddleware):
        """Handle CORS for pixel endpoint from Shopify Web Pixel (sandboxed iframe).

        WHY: The Shopify Web Pixel runs in a sandboxed iframe with origin 'null'.
        We MUST use wildcard '*' for Access-Control-Allow-Origin because:
        1. Browsers reject echoing back 'null' as an allowed origin
        2. We don't need credentials for this endpoint
        3. Any Shopify store should be able to send pixel events
        """
        async def dispatch(self, request, call_next):
            # Only handle /v1/pixel-events
            if request.url.path == "/v1/pixel-events":
                # ALWAYS use wildcard for sandboxed iframe compatibility
                cors_headers = {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, ngrok-skip-browser-warning",
                    "Access-Control-Max-Age": "86400",
                }

                # Handle preflight OPTIONS request
                if request.method == "OPTIONS":
                    return StarletteResponse(status_code=200, headers=cors_headers)

                # For POST, add CORS headers to response
                response = await call_next(request)
                for key, value in cors_headers.items():
                    response.headers[key] = value
                return response

            return await call_next(request)

    app.add_middleware(PixelCORSMiddleware)

    # Include all API routers
    app.include_router(auth_router.router)
    app.include_router(workspaces_router.router)
    app.include_router(connections_router.router)
    app.include_router(entities_router.router)
    app.include_router(metrics_router.router)
    app.include_router(pnl_router.router)
    app.include_router(finance_router.router)
    app.include_router(entity_performance_router.router)
    app.include_router(kpis_router.router)
    app.include_router(qa_router.router)
    app.include_router(qa_log_router.router)
    app.include_router(ingest_router.router)  # Phase 1.2: Metrics ingestion
    app.include_router(meta_sync_router.router)  # Phase 2: Meta sync endpoints
    app.include_router(google_sync_router.router)  # Google Ads sync endpoints
    app.include_router(google_oauth_router.router)  # Google OAuth flow
    app.include_router(meta_oauth_router.router)  # Meta OAuth flow
    app.include_router(shopify_oauth_router.router)  # Shopify OAuth flow
    app.include_router(shopify_sync_router.router)  # Shopify sync endpoints
    app.include_router(shopify_webhooks_router.router)  # Shopify compliance webhooks
    app.include_router(pixel_events_router.router)  # Attribution pixel events
    app.include_router(attribution_router.router)  # Attribution and pixel health
    app.include_router(dashboard_kpis_router.router)  # Dashboard KPIs with Shopify fallback
    app.include_router(dashboard_router.router)  # Unified dashboard endpoint
    app.include_router(clerk_webhooks_router.router)  # Clerk auth webhooks
    app.include_router(analytics_router.router)  # Production analytics charts
    app.include_router(onboarding_router.router)  # Onboarding flow
    app.include_router(polar_router.router)  # Polar billing endpoints
    app.include_router(polar_router.webhook_router)  # Polar webhook handler
    app.include_router(admin_router.router)  # Admin endpoints (protected by ADMIN_SECRET)
    app.include_router(agents_router.router)  # Agent system for automated monitoring

    @app.get(
        "/health",
        response_model=schemas.HealthResponse,
        tags=["Health"],
        summary="Health check",
        description="""
        Simple health check endpoint to verify the API is running.
        
        This endpoint:
        - Does not require authentication
        - Returns basic service status
        - Can be used for load balancer health checks
        - Indicates the API is responsive
        """
    )
    def health():
        return schemas.HealthResponse(status="ok")
    
    @app.on_event("startup")
    async def startup_event():
        """Validate critical configuration on application startup.

        Checks:
            1. Clerk authentication configuration (required for production)
            2. Redis connection for QA features
        """
        # Validate Clerk configuration (required for auth)
        if not all([settings.CLERK_SECRET_KEY, settings.CLERK_PUBLISHABLE_KEY]):
            logging.error("[STARTUP] CLERK_SECRET_KEY and CLERK_PUBLISHABLE_KEY are required")
            logging.error("[STARTUP] Authentication will fail without Clerk configuration")
            # Don't raise - allow local dev without Clerk, but warn loudly

        if not settings.CLERK_WEBHOOK_SECRET:
            logging.warning("[STARTUP] CLERK_WEBHOOK_SECRET not set - webhook verification will fail")

        # Validate Redis connection
        if state.context_manager and state.context_manager.health_check():
            logging.info("[STARTUP] Redis context manager is healthy")
        else:
            logging.warning("[STARTUP] Redis context manager health check failed - app will start but QA features may be unavailable")
            logging.warning("[STARTUP] Check REDIS_URL environment variable - currently: " + str(settings.REDIS_URL))
            # Don't raise - allow app to start even if Redis is temporarily unavailable
            # Individual requests will handle Redis failures gracefully

    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean shutdown of observability tools."""
        logging.info("[SHUTDOWN] Flushing observability events...")
        shutdown_observability()
        logging.info("[SHUTDOWN] Observability shutdown complete")

    # Custom OpenAPI schema with security definitions
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            servers=app.servers
        )
        
        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "cookieAuth": {
                "type": "apiKey",
                "in": "cookie",
                "name": "access_token",
                "description": "JWT token stored in HTTP-only cookie. Format: 'Bearer <token>'"
            }
        }
        
        # Add security requirement to protected endpoints
        public_endpoints = ["/health", "/auth/register", "/auth/login"]
        
        for path in openapi_schema["paths"]:
            for method in openapi_schema["paths"][path]:
                # Skip adding security to public endpoints
                if path in public_endpoints:
                    continue
                
                # Add security requirement for all other endpoints
                if "security" not in openapi_schema["paths"][path][method]:
                    openapi_schema["paths"][path][method]["security"] = [
                        {"cookieAuth": []}
                    ]
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
    return app


app = create_app()


