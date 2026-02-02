#!/usr/bin/env python3
"""
Direct migration script for crypto_news tables - NO ALEMBIC NEEDED
This script creates tables directly using SQLAlchemy models.

Usage:
    python scripts/migrate_crypto_news_direct.py
    
Returns:
    0: Success
    1: Error
"""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text, inspect, create_engine
from src.database.models import Base, CryptoNews, NewsDuplicate, NewsArchive
from dotenv import load_dotenv

load_dotenv()


def get_sync_engine():
    """Get synchronous engine from DATABASE_URL for migration"""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        raise ValueError("DATABASE_URL is not set in .env file")
    
    # Convert async URL to sync URL for migration
    # postgres+asyncpg://user:pass@host/db -> postgresql://user:pass@host/db
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    sync_url = sync_url.replace("postgres+asyncpg://", "postgresql://")
    
    return create_engine(sync_url, echo=False)


def check_existing_tables(engine):
    """Check if tables already exist"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    tables_to_create = ['crypto_news', 'news_duplicates', 'news_archive']
    existing = [t for t in tables_to_create if t in existing_tables]
    
    return existing


def create_tables():
    """Create tables from SQLAlchemy models"""
    try:
        # Get sync engine
        engine = get_sync_engine()
        
        print("=" * 60)
        print("CRYPTO NEWS MIGRATION - DIRECT SCRIPT")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print()
        
        # Check existing tables
        existing = check_existing_tables(engine)
        if existing:
            print(f"⚠️  Found existing tables: {', '.join(existing)}")
            print()
            response = input("Do you want to DROP and recreate these tables? (yes/no): ").strip().lower()
            if response != 'yes':
                print("❌ Migration cancelled.")
                return False
            
            # Drop existing tables
            print("🗑️  Dropping existing tables...")
            with engine.connect() as conn:
                if 'news_duplicates' in existing:
                    conn.execute(text("DROP TABLE IF EXISTS news_duplicates CASCADE"))
                if 'news_archive' in existing:
                    conn.execute(text("DROP TABLE IF EXISTS news_archive CASCADE"))
                if 'crypto_news' in existing:
                    conn.execute(text("DROP TABLE IF EXISTS crypto_news CASCADE"))
                conn.commit()
            print("✅ Old tables dropped")
            print()
        
        # Create new tables
        print("📝 Creating tables from models...")
        print("  - crypto_news")
        print("  - news_duplicates")
        print("  - news_archive")
        
        # Create all tables for models that don't exist yet
        Base.metadata.create_all(engine)
        
        print("✅ Tables created successfully")
        print()
        
        # Verify tables were created
        inspector = inspect(engine)
        created_tables = inspector.get_table_names()
        
        print("📊 Verification:")
        print(f"  ✓ crypto_news: {'crypto_news' in created_tables}")
        print(f"  ✓ news_duplicates: {'news_duplicates' in created_tables}")
        print(f"  ✓ news_archive: {'news_archive' in created_tables}")
        
        if all(t in created_tables for t in ['crypto_news', 'news_duplicates', 'news_archive']):
            print()
            print("✅ Indices created:")
            
            # Show indices for crypto_news
            try:
                indices = inspector.get_indexes('crypto_news')
                for idx in indices:
                    print(f"  - {idx['name']}: {idx['column_names']}")
            except Exception as e:
                print(f"  (Note: {e})")
            
            print()
            print("=" * 60)
            print("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            return True
        else:
            print("❌ Migration failed: Some tables not created")
            return False
            
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    try:
        success = create_tables()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
