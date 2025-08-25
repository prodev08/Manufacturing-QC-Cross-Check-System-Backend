# Manufacturing QC Cross-Check System - Backend

FastAPI backend for automated cross-checking of manufacturing documents and images.

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up PostgreSQL database:
```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt-get install postgresql postgresql-contrib

# Or using Docker
docker run --name qc-postgres -e POSTGRES_PASSWORD=password -e POSTGRES_DB=qc_system -p 5432:5432 -d postgres:15

# Create database (if not using Docker)
sudo -u postgres createdb qc_system
sudo -u postgres createuser -P user  # Set password when prompted
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your PostgreSQL connection details:
# DATABASE_URL=postgresql://user:password@localhost:5432/qc_system
```

5. Run the development server:
```bash
cd Backend
python -m uvicorn app.main:app --reload
```

The API will be available at: http://localhost:8000
API Documentation: http://localhost:8000/docs

## Project Structure

```
app/
├── main.py              # FastAPI application entry point
├── config.py            # Configuration and settings
├── database.py          # Database connection and session management
├── models/              # SQLAlchemy database models
├── schemas/             # Pydantic request/response models
├── api/                 # API route handlers
├── services/            # Business logic and file processing
├── utils/               # Utility functions
└── workers/             # Background job workers
```

## Current Status

- ✅ Basic FastAPI structure
- ✅ Configuration management
- ✅ Database setup (SQLAlchemy)
- ⏳ Database models (next step)
- ⏳ File upload endpoints
- ⏳ File processing pipeline
- ⏳ Validation engine
