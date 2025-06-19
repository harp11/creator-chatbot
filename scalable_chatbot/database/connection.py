from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator
import logging
from config import Config

logger = logging.getLogger(__name__)

# SQLAlchemy setup
Base = declarative_base()
metadata = MetaData()

class DatabaseManager:
    """Manages database connections with connection pooling"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
    
    def initialize_sync_db(self):
        """Initialize synchronous database connection"""
        if self._initialized:
            return
            
        try:
            # Create engine with connection pooling
            if Config.is_sqlite():
                # SQLite configuration for local development
                self.engine = create_engine(
                    Config.DATABASE_URL,
                    connect_args={"check_same_thread": False},
                    poolclass=StaticPool,
                    echo=True  # Enable SQL logging for debugging
                )
            else:
                # PostgreSQL configuration for production
                self.engine = create_engine(
                    Config.DATABASE_URL,
                    pool_pre_ping=True,
                    pool_recycle=300,
                    echo=True
                )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info("Synchronous database connection initialized")
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize sync database: {e}")
            raise
    
    @contextmanager
    def get_db_session(self) -> Generator[Session, None, None]:
        """Get synchronous database session with automatic cleanup"""
        if not self._initialized:
            self.initialize_sync_db()
            
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def create_tables(self):
        """Create all database tables"""
        if not self._initialized:
            self.initialize_sync_db()
            
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def close_connections(self):
        """Close all database connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")

# Global database manager instance
db_manager = DatabaseManager()

# Dependency for FastAPI
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions"""
    with db_manager.get_db_session() as session:
        yield session 