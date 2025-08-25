#!/usr/bin/env python3
"""
Database initialization script for the QC System.

This script creates all database tables based on the SQLAlchemy models.
Run this script after setting up your PostgreSQL database.
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import create_tables, engine
from app.config import settings


def main():
    """Initialize the database"""
    print(f'Initializing database: {settings.database_url}')
    
    try:
        # Test database connection
        with engine.connect() as conn:
            print('✅ Database connection successful')
        
        # Create tables
        create_tables()
        print('✅ Database tables created successfully')
        
        print('\nDatabase initialization complete!')
        print('You can now start the FastAPI server with:')
        print('  python -m uvicorn app.main:app --reload')
        
    except Exception as e:
        print(f'❌ Database initialization failed: {e}')
        print('\nPlease ensure:')
        print('1. PostgreSQL is running')
        print('2. Database exists')
        print('3. Connection details in .env are correct')
        sys.exit(1)


if __name__ == '__main__':
    main()
