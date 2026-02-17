#!/usr/bin/env python3
"""
STRATYON Database Initialization Script

This script initializes the database using SQLAlchemy models.
For production, use the SQL files in schema/ directory.

Usage:
    python backend/database/init_db.py

Environment Variables:
    DATABASE_URL - PostgreSQL connection string
                   Default: postgresql://postgres:postgres@localhost:5432/geoint_db
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
from app.core.database import Base
from app.core.config import settings

# Import all models to ensure they're registered with Base
from app.models import (
    User,
    RefreshToken,
    Province,
    District,
    Neighborhood,
    GEOINTScore,
    Keyword,
    Competitor,
    CompetitorSnapshot,
    Strategy,
    StrategyWeek,
    StrategyTask,
    MediaMention,
    PROpportunity,
)


def enable_postgis(engine):
    """Enable PostGIS extension if not already enabled."""
    print("Enabling PostGIS extension...")
    with engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.commit()
            print("✅ PostGIS extension enabled")
        except ProgrammingError as e:
            print(f"⚠️  Warning: Could not enable PostGIS: {e}")
            print("    Make sure you have superuser privileges or PostGIS is already installed")


def create_tables(engine):
    """Create all tables from SQLAlchemy models."""
    print("\nCreating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created successfully")


def print_summary(engine):
    """Print summary of created tables."""
    print("\n" + "=" * 60)
    print("Database Initialization Complete!")
    print("=" * 60)

    with engine.connect() as conn:
        # Get table count
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """))
        table_count = result.scalar()

        print(f"\n📊 Statistics:")
        print(f"   - Tables created: {table_count}")
        print(f"   - Database: {engine.url.database}")
        print(f"   - Host: {engine.url.host}")

        # List all tables
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]

        print(f"\n📋 Created Tables:")
        for table in tables:
            print(f"   - {table}")

        # Check for spatial indexes
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM pg_indexes
            WHERE indexname LIKE '%gist%'
        """))
        spatial_index_count = result.scalar()

        print(f"\n🗺️  Spatial Indexes: {spatial_index_count}")

    print("\n" + "=" * 60)
    print("\n📝 Next Steps:")
    print("   Start the backend server (geographic data auto-seeds on startup):")
    print("      cd backend && uvicorn app.main:app --reload")
    print("\n" + "=" * 60 + "\n")


def main():
    """Main initialization function."""
    print("=" * 60)
    print("STRATYON Database Initialization")
    print("=" * 60)

    # Get database URL
    database_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
    print(f"\n🔗 Database URL: {database_url.split('@')[1] if '@' in database_url else database_url}")

    # Create engine
    engine = create_engine(database_url)

    try:
        # Test connection
        print("\n🔌 Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"✅ Connected to PostgreSQL")
            print(f"   Version: {version.split(',')[0]}")

        # Enable PostGIS
        enable_postgis(engine)

        # Create tables
        create_tables(engine)

        # Print summary
        print_summary(engine)

        return 0

    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure PostgreSQL is running")
        print("  2. Verify DATABASE_URL is correct")
        print("  3. Check database exists: createdb geoint_db")
        print("  4. Ensure PostGIS is installed")
        return 1

    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
