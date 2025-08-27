# Manufacturing QC Cross-Check System - Backend

A comprehensive FastAPI backend for automated cross-validation of manufacturing documents, images, and BOMs to ensure production quality and compliance.

## 🎯 **System Overview**

This backend powers an intelligent manufacturing QC system that processes and cross-validates:
- **Traveler/Work Instruction PDFs** - Job numbers, part numbers, serials, work instructions
- **Product Images** - OCR extraction of board serials, part codes, flight status markings
- **Excel As-Built BOMs** - Job numbers, part numbers, revisions

The system automatically identifies discrepancies, validates serial number formats, and ensures manufacturing compliance through intelligent cross-referencing with priority-based validation checks.

## 🏗️ **Architecture Overview**

### **High-Level System Architecture**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   Database      │
│   (React)       │◄──►│   (FastAPI)     │◄──►│  (PostgreSQL)   │
│  - File Upload  │    │  - File Proc.   │    │  - Sessions     │
│  - Validation   │    │  - OCR/Extract  │    │  - Files        │
│  - Dashboard    │    │  - Cross-Val    │    │  - Validation   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   File Storage  │
                    │   (Local/Cloud) │
                    │  - Images       │
                    │  - PDFs         │
                    │  - Excel Files  │
                    └─────────────────┘
```

### **Backend Service Architecture**
```
┌──────────────────────────────────────────────────────────────────┐
│                          API Layer                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │  Sessions   │ │    Files    │ │ Processing  │ │ Validation  │ │
│  │  Endpoints  │ │  Endpoints  │ │ Endpoints   │ │ Endpoints   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                       Service Layer                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │   File      │ │   EasyOCR   │ │     QC      │ │  Workflow   │ │
│  │ Processor   │ │   Service   │ │  Validator  │ │Orchestrator │ │
│  │             │ │ (Async OCR) │ │(Cross-Check)│ │             │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                │
│  │    PDF      │ │    Excel    │ │   Pattern   │                │
│  │ Extractor   │ │   Parser    │ │ Extraction  │                │
│  └─────────────┘ └─────────────┘ └─────────────┘                │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                        Data Layer                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │  Sessions   │ │    Files    │ │ Validation  │ │    Utils    │ │
│  │   Model     │ │   Model     │ │   Results   │ │(Normalizers)│ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## 🔄 **Overall Approach**

### **1. File Processing Pipeline**
```
Upload → Validation → Storage → Async Processing → Data Extraction
```

**Detailed Flow:**
1. **File Upload & Validation**
   - Multi-file drag-and-drop interface
   - File type validation (PDF, JPG/PNG, Excel)
   - Size and format verification
   - Secure storage with UUID naming

2. **Async Processing by Type**
   - **PDF Processing**: PyPDF2 + pdfplumber for text extraction
   - **Image Processing**: EasyOCR with rotation handling (0°, 90°, 180°, 270°)
   - **Excel Processing**: pandas + openpyxl for structured data parsing
   - **Background Execution**: ThreadPoolExecutor for non-blocking OCR

3. **Data Extraction & Pattern Matching**
   - **Serial Numbers**: VGN-XXXXX-XXXX, INF-XXXX patterns
   - **Part Numbers**: PCA-XXXX-YY, DRW-XXXX-YY formats
   - **Job Numbers**: 5-digit manufacturing job identifiers
   - **Flight Status**: "FLIGHT" vs "EDU - NOT FOR FLIGHT" markings
   - **Revisions**: Rev A, Rev F2, etc.

### **2. Cross-Validation Engine**
```
Extract → Normalize → Compare → Validate → Classify → Report
```

**Priority-Based Validation Checks:**
1. **🔴 Critical (FAIL)**
   - Job Number Mismatch (Traveler ↔ BOM)
   - Missing Part Numbers in BOM
   - Critical serial number discrepancies

2. **🟡 Warning (WARNING)**  
   - Revision format differences (Rev F2 vs Rev F)
   - Minor serial number formatting issues
   - Missing file types

3. **🟢 Pass (PASS)**
   - All critical checks successful
   - Data matches across sources
   - Proper normalization applied

### **3. Smart Data Normalization**
**Handles manufacturing data variations:**

| Type | Input | Normalized | Notes |
|------|-------|------------|-------|
| Board Serial | `12345-0001` | `VGN-12345-0001` | Adds missing prefix |
| Unit Serial | `1619` | `INF-1619` | Standardizes format |
| Part Number | `PCA1555-01` | `PCA-1555-01` | Adds hyphens |
| Revision | `Rev F2` | `F2` | Removes prefix |
| Job Number | `Job 12345` | `12345` | Extracts digits |

### **4. Async Processing Architecture**
**Non-blocking, scalable design:**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Request   │───►│  Background │───►│   Status    │
│   (Upload)  │    │  Processing │    │  Updates    │
└─────────────┘    └─────────────┘    └─────────────┘
                          │
                          ▼
                  ┌─────────────┐
                  │ Thread Pool │
                  │ (EasyOCR)   │
                  └─────────────┘
```

**Benefits:**
- **Responsive Backend**: API responds immediately
- **Concurrent Processing**: Multiple files processed simultaneously
- **Real-time Updates**: Status polling for progress tracking
- **Scalable Design**: Thread pool handles CPU-intensive OCR

## 🛠️ **Technology Stack**

### **Core Framework**
- **FastAPI 0.116+**: Modern async web framework with automatic OpenAPI docs
- **Uvicorn**: Lightning-fast ASGI server
- **Python 3.8+**: Async/await support for concurrent processing

### **Database & ORM**
- **PostgreSQL**: Production-grade relational database
- **SQLAlchemy 2.0**: Modern async ORM with type hints
- **Alembic**: Database migration management

### **File Processing**
- **EasyOCR**: Advanced OCR with rotation handling for manufacturing text
- **OpenCV**: Image preprocessing and rotation detection
- **PyPDF2 + pdfplumber**: Comprehensive PDF text extraction
- **pandas + openpyxl**: Excel file parsing and data manipulation

### **Async & Performance**
- **ThreadPoolExecutor**: Non-blocking OCR processing
- **asyncio**: Concurrent request handling
- **Pillow**: Image format support and validation

### **API & Validation**
- **Pydantic v2**: Data validation and serialization
- **python-multipart**: File upload handling
- **CORS middleware**: Cross-origin resource sharing

## 🚀 **Key Features**

### **Intelligent OCR Processing**
- **Multi-angle Recognition**: Handles 0°, 90°, 180°, 270° rotated text
- **Confidence Scoring**: Filters low-quality extractions
- **Preprocessing Pipeline**: Image enhancement for better accuracy
- **Async Execution**: Non-blocking processing with thread pools

### **Advanced Cross-Validation**
- **Priority-based Checks**: Critical failures vs warnings
- **Smart Normalization**: Handles format variations automatically
- **Pattern Recognition**: Manufacturing-specific regex patterns
- **Fuzzy Matching**: Tolerant comparison algorithms

### **Manufacturing-Specific Logic**
- **Serial Number Formats**: VGN-XXXXX-XXXX, INF-XXXX validation
- **Part Number Patterns**: PCA-XXXX-YY, DRW-XXXX-YY recognition
- **Flight Status Validation**: Critical aerospace compliance checks
- **Revision Tracking**: Format-agnostic revision comparison

### **Production-Ready Design**
- **Session Management**: Organized QC workflow tracking
- **File Validation**: Comprehensive upload security
- **Error Handling**: Graceful failure with detailed logging
- **API Documentation**: Auto-generated OpenAPI/Swagger docs

## 🔌 **API Endpoints**

### **Session Management**
```
POST   /api/v1/sessions              # Create new QC session
GET    /api/v1/sessions              # List all sessions  
GET    /api/v1/sessions/{id}         # Get session details
DELETE /api/v1/sessions/{id}         # Delete session
```

### **File Operations**
```
POST   /api/v1/files/upload          # Upload files (PDF/Image/Excel)
GET    /api/v1/files/session/{id}    # Get session files
GET    /api/v1/files/{id}            # Get file details
DELETE /api/v1/files/{id}            # Delete file
```

### **Processing & Analysis**
```
POST   /api/v1/processing/session/{id}     # Start file processing
GET    /api/v1/processing/status/{id}      # Get processing status
POST   /api/v1/workflow/analyze/{id}       # Run complete analysis
GET    /api/v1/workflow/status/{id}        # Get workflow status
```

### **Validation Results**
```
GET    /api/v1/validation/results/{id}     # Get validation results
GET    /api/v1/validation/summary/{id}     # Get validation summary
POST   /api/v1/validation/validate/{id}    # Trigger validation
```

### **Documentation**
```
GET    /docs                         # Interactive API documentation
GET    /redoc                        # Alternative API documentation
GET    /openapi.json                 # OpenAPI specification
```

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install Python dependencies:
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

5. Initialize the database:
```bash
python init_db.py
```

6. Run the development server:
```bash
python -m uvicorn app.main:app --reload
```

The API will be available at: http://localhost:8000
API Documentation: http://localhost:8000/docs

## 🚧 **Limitations & Future Roadmap**

### **Current Limitations**

#### **1. File Processing & OCR**
- **OCR Accuracy**: EasyOCR may struggle with very low-quality images or unusual fonts
- **Rotation Detection**: Limited to 90-degree increments (0°, 90°, 180°, 270°)
- **Image Preprocessing**: Basic enhancement only; could benefit from advanced filtering
- **PDF Complexity**: May miss text in complex layouts or scanned PDFs with poor quality
- **File Size Limits**: No explicit size restrictions implemented yet

#### **2. Data Extraction & Validation**
- **Pattern Matching**: Regex-based approach may miss variations in manufacturing formats
- **Serial Number Formats**: Currently supports VGN-XXXXX-XXXX and INF-XXXX patterns only
- **Part Number Variations**: Limited to PCA-XXXX-YY and DRW-XXXX-YY formats
- **Fuzzy Matching**: Basic implementation; could be more sophisticated
- **Context Awareness**: No understanding of document structure or relationships

#### **3. Performance & Scalability**
- **Local File Storage**: Files stored locally; no cloud integration yet
- **Single-Node Processing**: No distributed processing for large workloads
- **Memory Usage**: EasyOCR models loaded in memory; high RAM usage
- **Concurrent Sessions**: Limited by thread pool size (currently 2 workers)
- **Database Scaling**: Single PostgreSQL instance; no read replicas

#### **4. Production Features**
- **Authentication**: No user authentication or authorization system
- **Audit Logging**: Limited tracking of user actions and system events
- **Rate Limiting**: No request throttling or abuse prevention
- **Monitoring**: No health checks, metrics, or alerting
- **Backup Strategy**: No automated database or file backup system

#### **5. Integration & Deployment**
- **API Versioning**: Basic v1 structure; no deprecation strategy
- **Error Handling**: Basic error responses; could be more detailed
- **Configuration**: Limited environment-specific settings
- **Docker Support**: No containerization setup yet
- **CI/CD Pipeline**: No automated testing or deployment

### **🚀 What We'd Ship Next (Priority Order)**

#### **Phase 1: Production Readiness (2-3 weeks)**
```
🔐 Security & Authentication
├── JWT-based authentication system
├── Role-based access control (Admin, Operator, Viewer)
├── API key management for external integrations
└── Rate limiting and request throttling

📊 Monitoring & Observability  
├── Health check endpoints (/health, /ready)
├── Prometheus metrics integration
├── Structured logging with correlation IDs
├── Performance monitoring and alerting
└── Database connection pooling optimization

🐳 Containerization & Deployment
├── Docker containerization with multi-stage builds
├── docker-compose for local development
├── Kubernetes manifests for production
├── Environment-specific configuration management
└── CI/CD pipeline with automated testing
```

#### **Phase 2: Enhanced Processing (3-4 weeks)**
```
🧠 Advanced OCR & AI
├── Multiple OCR engine fallbacks (EasyOCR + Tesseract)
├── Computer vision for layout detection
├── Machine learning model for pattern recognition
├── Confidence scoring and uncertainty quantification
└── Custom training data for manufacturing text

📄 Enhanced Document Processing
├── Advanced PDF parsing for complex layouts
├── Table extraction from PDFs and images
├── Multi-page document handling
├── Barcode and QR code recognition
└── Handwriting recognition for annotations

☁️ Cloud Integration
├── AWS S3/Azure Blob storage for files
├── Cloud-based OCR services (AWS Textract, Azure CV)
├── Distributed processing with message queues
├── Auto-scaling worker nodes
└── CDN integration for file delivery
```

#### **Phase 3: Intelligence & Automation (4-6 weeks)**
```
🤖 Smart Validation & ML
├── Machine learning for anomaly detection
├── Historical data analysis for trend identification
├── Predictive quality scoring
├── Automated suggestion system for corrections
└── Neural network for pattern recognition

📊 Advanced Analytics & Reporting
├── Statistical analysis of QC trends
├── Automated report generation (PDF/Excel)
├── Dashboard with real-time metrics
├── Email notifications for critical failures
└── Export APIs for external systems

🔄 Workflow Automation
├── Configurable validation rules engine
├── Automated routing based on results
├── Integration with ERP/MES systems
├── Approval workflows for exceptions
└── Batch processing for multiple sessions
```

#### **Phase 4: Enterprise Features (6-8 weeks)**
```
🏢 Enterprise Integration
├── LDAP/Active Directory authentication
├── SAML/OAuth2 SSO integration
├── REST/GraphQL APIs for external systems
├── Webhook notifications for status updates
└── Custom field definitions and validation

📈 Advanced Features
├── Version control for validation rules
├── A/B testing for processing algorithms
├── Multi-tenant architecture
├── Advanced search and filtering
└── Compliance reporting (ISO, AS9100)

🌐 Global Deployment
├── Multi-region deployment support
├── Data residency compliance
├── Language localization support
├── Time zone handling
└── Global CDN with edge processing
```

### **🎯 Technical Debt & Code Quality**

#### **High Priority**
- **Error Handling**: Implement comprehensive exception hierarchy
- **Testing**: Add unit tests, integration tests, and end-to-end tests
- **Documentation**: API documentation with examples and schemas
- **Code Coverage**: Achieve >90% test coverage
- **Performance**: Database query optimization and caching

#### **Medium Priority**
- **Code Structure**: Refactor services for better separation of concerns
- **Async Optimization**: Review async/await usage for performance
- **Memory Management**: Optimize EasyOCR model loading
- **Database**: Add indexes and query optimization
- **Configuration**: Environment-based feature flags

### **🔒 Security Enhancements**

#### **Immediate Needs**
- **Input Validation**: Comprehensive file upload security
- **SQL Injection**: Parameterized queries and ORM protection
- **File Security**: Virus scanning and malware detection
- **Data Encryption**: Encrypt sensitive data at rest
- **HTTPS**: SSL/TLS termination and security headers

#### **Long-term Security**
- **Penetration Testing**: Regular security audits
- **Compliance**: SOC2, GDPR, HIPAA readiness
- **Zero Trust**: Network security architecture
- **Secrets Management**: Vault integration for credentials
- **Audit Trail**: Comprehensive action logging

### **📊 Performance Optimizations**

#### **Database Performance**
- **Connection Pooling**: Optimize PostgreSQL connections
- **Read Replicas**: Separate read/write workloads
- **Caching**: Redis for frequently accessed data
- **Indexing**: Strategic database index optimization
- **Partitioning**: Table partitioning for large datasets

#### **Processing Performance**
- **GPU Processing**: CUDA support for EasyOCR
- **Parallel Processing**: Multi-core utilization
- **Queue Management**: Background job prioritization
- **Result Caching**: Cache processed results
- **Streaming**: Stream processing for large files

This roadmap provides a clear path from the current MVP to a production-ready, enterprise-grade manufacturing QC system! 🔧✨

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
