from fastapi import APIRouter
from app.api.endpoints import sessions, files, processing, validation, workflow

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

api_router.include_router(
    processing.router,
    prefix='/processing',
    tags=['processing']
)

api_router.include_router(
    validation.router,
    prefix='/validation',
    tags=['validation']
)

api_router.include_router(
    workflow.router,
    prefix='/workflow',
    tags=['workflow']
)
