from fastapi import APIRouter

from app.api.v1.routes import companies, documents, evaluations, health, warnings

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(companies.router)
api_router.include_router(warnings.router)
api_router.include_router(evaluations.router)
api_router.include_router(documents.router)
