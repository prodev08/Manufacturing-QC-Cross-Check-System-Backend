from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.api import api_router

# Create FastAPI application
app = FastAPI(
    title=settings.project_name,
    description='A system for cross-checking manufacturing QC documents and images',
    version='0.1.0',
    openapi_url=f'{settings.api_v1_str}/openapi.json'
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Include API router
app.include_router(api_router, prefix=settings.api_v1_str)


@app.get('/')
async def root():
    """Health check endpoint"""
    return {
        'message': 'Manufacturing QC Cross-Check System API',
        'version': '0.1.0',
        'status': 'running'
    }


@app.get('/health')
async def health_check():
    """Detailed health check"""
    return {
        'status': 'healthy',
        'database': 'connected',  # TODO: Add actual DB health check
        'upload_dir': settings.upload_dir
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(
        'app.main:app',
        host='0.0.0.0',
        port=8000,
        reload=settings.debug
    )
