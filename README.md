# Manufacturing QC Cross-Check System - Backend

FastAPI backend for automated cross-checking of manufacturing documents and images.

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install system dependencies:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng

# Windows (install manually)
# Download Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
# Add to PATH or update config in ocr_service.py

# macOS
brew install tesseract
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Set up PostgreSQL database:
```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt-get install postgresql postgresql-contrib

# Or using Docker
docker run --name qc-postgres -e POSTGRES_PASSWORD=password -e POSTGRES_DB=qc_system -p 5432:5432 -d postgres:15

# Create database (if not using Docker)
sudo -u postgres createdb qc_system
sudo -u postgres createuser -P user  # Set password when prompted
```

5. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your PostgreSQL connection details:
# DATABASE_URL=postgresql://user:password@localhost:5432/qc_system
```

6. Initialize the database:
```bash
python init_db.py
```

7. Run the development server:
```bash
python -m uvicorn app.main:app --reload
```

The API will be available at: http://localhost:8000
API Documentation: http://localhost:8000/docs

## Database Migrations

To create a new migration after model changes:
```bash
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

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

## API Endpoints

### Sessions
- `POST /api/v1/sessions/` - Create a new QC analysis session
- `GET /api/v1/sessions/` - List all sessions with pagination
- `GET /api/v1/sessions/{session_id}` - Get session details with files and results
- `DELETE /api/v1/sessions/{session_id}` - Delete a session and all associated data

### Files
- `POST /api/v1/files/upload/{session_id}` - Upload multiple files to a session
- `GET /api/v1/files/session/{session_id}` - Get all files for a session
- `GET /api/v1/files/{file_id}` - Get file details
- `DELETE /api/v1/files/{file_id}` - Delete a file

### Processing
- `POST /api/v1/processing/process/{session_id}` - Start processing all files in a session
- `GET /api/v1/processing/status/{session_id}` - Get processing status and summary
- `POST /api/v1/processing/process-file/{file_id}` - Process a single file

### Supported File Types
- **Traveler PDFs**: `application/pdf`
- **Product Images**: `image/jpeg`, `image/png`
- **BOM Excel**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `application/vnd.ms-excel`

## Testing

Test the API endpoints:
```bash
python test_api.py
```

## Current Status

- ✅ Basic FastAPI structure
- ✅ Configuration management  
- ✅ Database setup (SQLAlchemy + PostgreSQL)
- ✅ Database models (Session, UploadedFile, ValidationResult)
- ✅ Pydantic schemas for API requests/responses
- ✅ Alembic database migrations
- ✅ File upload endpoints with validation
- ✅ Session management API
- ✅ File storage and management
- ✅ File processing pipeline (PDF, OCR, Excel)
- ✅ Data extraction with regex patterns
- ✅ Background processing endpoints
- ⏳ Cross-validation engine (next step)
- ⏳ Validation result generation
