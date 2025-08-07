

import uuid
import json
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text, Boolean, ForeignKey, Index, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.types import TypeDecorator, VARCHAR

from .config import get_config

Base = declarative_base()

class UUID(TypeDecorator):
    """Platform-independent UUID type for SQLite"""
    impl = VARCHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(VARCHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return str(value)

class User(Base):
    """User model for authentication and preferences"""
    __tablename__ = 'users'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Authentication
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=True)  # Optional
    password_hash = Column(String(255), nullable=False)
    
    # User identification
    display_name = Column(String(100), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_active = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # User preferences as JSON
    preferences = Column(JSON, default=dict)
    
    # Relationships
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_username', 'username'),
        Index('idx_email', 'email'),
        Index('idx_last_active', 'last_active'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"
    
    def set_password(self, password: str):
        """Hash and set password"""
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters")
        if len(password) > 128:
            raise ValueError("Password too long")
            
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """Verify password against hash"""
        if not self.password_hash or not password:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self, include_sensitive=False) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'display_name': self.display_name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_active': self.last_active.isoformat() if self.last_active else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'preferences': self.preferences or {}
        }
        
        if include_sensitive:
            data['has_password'] = bool(self.password_hash)
        
        return data

class ChatSession(Base):
    """Chat session with AI context persistence"""
    __tablename__ = 'chat_sessions'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Session identification
    session_id = Column(UUID, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    # User relationship
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Session metadata
    title = Column(String(500), nullable=False, default="New Math Session")
    message_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_active = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # AI Context Storage for conversation continuity
    ai_context = Column(JSON, default=list)
    
    # Status
    is_archived = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("Message", back_populates="chat_session", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_session_id', 'session_id'),
        Index('idx_user_sessions', 'user_id', 'last_active'),
        Index('idx_archived', 'is_archived'),
    )
    
    def __repr__(self):
        return f"<ChatSession(id={self.id}, session_id={self.session_id[:8]}..., user_id={self.user_id})>"
    
    def store_ai_context(self, chat_history: List[Dict[str, Any]]):
        """Store AI chat history for context restoration"""
        self.ai_context = chat_history
        self.last_active = datetime.utcnow()
    
    def get_ai_context(self) -> List[Dict[str, Any]]:
        """Retrieve AI chat history"""
        return self.ai_context or []
    
    def clear_ai_context(self):
        """Clear AI context when conversation is reset"""
        self.ai_context = []
        self.last_active = datetime.utcnow()
    
    def belongs_to_user(self, user_id: int) -> bool:
        """Security check: verify session belongs to user"""
        return self.user_id == user_id
    
    def to_dict(self, include_ai_context: bool = False) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'title': self.title,
            'message_count': self.message_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_active': self.last_active.isoformat() if self.last_active else None,
            'is_archived': self.is_archived
        }
        
        if include_ai_context:
            data['ai_context'] = self.get_ai_context()
        
        return data

class Message(Base):
    """Individual messages in chat sessions"""
    __tablename__ = 'messages'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Session relationship
    chat_session_id = Column(Integer, ForeignKey('chat_sessions.id'), nullable=False)
    
    # Message content
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    tokens_used = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    
    # Relationships
    chat_session = relationship("ChatSession", back_populates="messages")
    
    # Indexes
    __table_args__ = (
        Index('idx_session_messages', 'chat_session_id', 'timestamp'),
        Index('idx_role', 'role'),
    )
    
    def __repr__(self):
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(id={self.id}, role={self.role}, content='{content_preview}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'chat_session_id': self.chat_session_id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'tokens_used': self.tokens_used,
            'response_time_ms': self.response_time_ms
        }

class Database:
    """Database manager for Faust application"""
    
    def __init__(self):
        config = get_config()
        self.database_url = config.get_database_url()
        
        self.engine = create_engine(
            self.database_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,
            pool_recycle=300
        )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a database session"""
        return self.SessionLocal()
    
    def init_database(self):
        """Initialize database with tables"""
        self.create_tables()
    
    def check_health(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            with self.get_session() as session:
                user_count = session.query(User).count()
                return {
                    'status': 'healthy',
                    'user_count': user_count,
                    'timestamp': datetime.utcnow().isoformat()
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

# Global database instance
_database = None

def get_database() -> Database:
    """Get the global database instance"""
    global _database
    if _database is None:
        _database = Database()
        _database.init_database()
    return _database

# Helper functions for user operations
def get_user_by_username(session: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return session.query(User).filter(
        User.username == username,
        User.is_active == True
    ).first()

def get_user_by_email(session: Session, email: str) -> Optional[User]:
    """Get user by email address"""
    if not email:
        return None
    return session.query(User).filter(
        User.email == email.lower(),
        User.is_active == True
    ).first()

def create_user(session: Session, username: str, password: str, email: str = None, display_name: str = None) -> User:
    """Create a new user"""
    # Check if username already exists
    existing = get_user_by_username(session, username)
    if existing:
        raise ValueError("Username already exists")
    
    # Check if email already exists
    if email:
        existing_email = get_user_by_email(session, email)
        if existing_email:
            raise ValueError("Email already registered")
    
    user = User(
        username=username,
        email=email.lower() if email else None,
        display_name=display_name or username,
        preferences={
            'theme': 'dark',
            'math_display': 'unicode',
            'auto_save': True
        }
    )
    user.set_password(password)
    user.last_login = datetime.utcnow()
    
    session.add(user)
    session.commit()
    
    return user

def ensure_user_owns_session(session: Session, session_id: str, user_id: int) -> ChatSession:
    """Security: Ensure user owns the session they're trying to access"""
    chat_session = session.query(ChatSession).filter(
        ChatSession.session_id == session_id,
        ChatSession.user_id == user_id
    ).first()
    
    if not chat_session:
        raise ValueError(f"Session not found or access denied")
    
    return chat_session