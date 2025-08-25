from fastapi import APIRouter
from app.api.endpoints import sessions, files

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    sessions.router,
    prefix='/sessions',
    tags=['sessions']
)

api_router.include_router(
    files.router,
    prefix='/files',
    tags=['files']
)
