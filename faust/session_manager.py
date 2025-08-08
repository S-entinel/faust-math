import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .database import (
    get_database, User, ChatSession, Message, 
    ensure_user_owns_session
)
from .ai_service import get_ai_service

class SessionManager:
    """Manages chat sessions and conversation history"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.database = get_database()
        self.ai_service = get_ai_service()
        self.console = Console()
        
        # Current active session
        self.current_session = None
        self.current_session_id = None
        self.chat_history = []
        self.current_academic_level = 'normal'  # Default level
        
        # Load user's preferred academic level
        self._load_user_academic_level()

    def _load_user_academic_level(self):
        """Load user's preferred academic level from database"""
        try:
            with self.database.get_session() as session:
                user = session.query(User).filter(User.id == self.user_id).first()
                if user:
                    self.current_academic_level = user.get_academic_level()
        except Exception as e:
            self.console.print(f"[dim bright_black]Warning: Could not load academic level: {e}[/dim bright_black]")
            self.current_academic_level = 'normal'
    
    def set_academic_level(self, level: str, session_only: bool = False) -> bool:
        """Set academic level for user or current session"""
        valid_levels = ['child', 'normal', 'academic']
        if level.lower() not in valid_levels:
            self.console.print(f"[bright_red]✗ Invalid academic level. Must be one of: {', '.join(valid_levels)}[/bright_red]")
            return False
        
        level = level.lower()
        
        try:
            with self.database.get_session() as session:
                if session_only and self.current_session_id:
                    # Set level for current session only
                    chat_session = ensure_user_owns_session(session, self.current_session_id, self.user_id)
                    chat_session.set_session_academic_level(level)
                    session.commit()
                    
                    self.current_academic_level = level
                    self.current_session = chat_session.to_dict(include_ai_context=True)
                    
                    level_info = self.ai_service.get_academic_level_info(level)
                    self.console.print(f"[white]✓ Session academic level set to: {level_info['name']}[/white]")
                    
                else:
                    # Set level for user (affects all new sessions)
                    user = session.query(User).filter(User.id == self.user_id).first()
                    if user:
                        user.set_academic_level(level)
                        session.commit()
                    
                    # Also update current session if exists
                    if self.current_session_id:
                        chat_session = ensure_user_owns_session(session, self.current_session_id, self.user_id)
                        chat_session.set_session_academic_level(level)
                        session.commit()
                        self.current_session = chat_session.to_dict(include_ai_context=True)
                    
                    self.current_academic_level = level
                    level_info = self.ai_service.get_academic_level_info(level)
                    self.console.print(f"[white]✓ Academic level set to: {level_info['name']} ({level_info['description']})[/white]")
                
                return True
                
        except Exception as e:
            self.console.print(f"[bright_red]✗ Failed to set academic level: {e}[/bright_red]")
            return False
    
    def get_current_academic_level(self) -> str:
        """Get the effective academic level for current session"""
        if self.current_session and self.current_session.get('session_academic_level'):
            return self.current_session['session_academic_level']
        return self.current_academic_level
    
    def show_academic_level_info(self):
        """Display current academic level information"""
        current_level = self.get_current_academic_level()
        level_info = self.ai_service.get_academic_level_info(current_level)
        
        # Create info table
        table = Table(show_header=False, box=None, border_style="white")
        table.add_column("Field", style="white", width=18)
        table.add_column("Value", style="white")
        
        table.add_row("Current Level", f"{level_info['name']}")
        table.add_row("Description", level_info['description'])
        table.add_row("Complexity", level_info['complexity'])
        table.add_row("Teaching Style", level_info['teaching_style'])
        table.add_row("Typical Topics", ", ".join(level_info['topics'][:3]) + "...")
        
        # Session-specific info
        if self.current_session and self.current_session.get('session_academic_level'):
            table.add_row("Scope", "Session Only")
        else:
            table.add_row("Scope", "User Default")
        
        panel = Panel.fit(
            table,
            title="[white]ACADEMIC LEVEL SETTINGS[/white]",
            border_style="white",
            padding=(1, 2)
        )
        self.console.print(panel)
        self.console.print()
    
    def create_new_session(self, title: str = None, academic_level: str = None) -> str:
        """Create a new chat session with optional academic level"""
        try:
            with self.database.get_session() as session:
                # Create new chat session
                session_id = str(uuid.uuid4())
                chat_session = ChatSession(
                    session_id=session_id,
                    user_id=self.user_id,
                    title=title or "New Math Session"
                )
                
                # Set academic level for session if specified
                if academic_level:
                    chat_session.set_session_academic_level(academic_level)
                
                session.add(chat_session)
                session.commit()
                
                # Set as current session
                self.current_session_id = session_id
                self.current_session = chat_session.to_dict(include_ai_context=True)
                self.chat_history = []
                
                # Update current academic level
                effective_level = chat_session.get_effective_academic_level(self.current_academic_level)
                self.current_academic_level = effective_level
                
                level_info = self.ai_service.get_academic_level_info(effective_level)
                self.console.print(f"[white]✓ Created new session: {title or 'New Math Session'} ({level_info['name']})[/white]")
                return session_id
                
        except SQLAlchemyError as e:
            self.console.print(f"[bright_red]✗ Failed to create session: {e}[/bright_red]")
            raise
    
    def load_session(self, session_id: str) -> bool:
        """Load an existing chat session and set appropriate academic level"""
        try:
            with self.database.get_session() as db_session:
                chat_session = ensure_user_owns_session(db_session, session_id, self.user_id)
                
                # Update last active
                chat_session.last_active = datetime.utcnow()
                db_session.commit()
                
                # Set as current session
                self.current_session_id = session_id
                self.current_session = chat_session.to_dict(include_ai_context=True)
                self.chat_history = chat_session.get_ai_context()
                
                # Get effective academic level for this session
                user = db_session.query(User).filter(User.id == self.user_id).first()
                user_level = user.get_academic_level() if user else 'normal'
                effective_level = chat_session.get_effective_academic_level(user_level)
                self.current_academic_level = effective_level
                
                # Load recent messages for display
                messages = db_session.query(Message).filter(
                    Message.chat_session_id == chat_session.id
                ).order_by(Message.timestamp.desc()).limit(10).all()
                
                message_count = len(messages)
                level_info = self.ai_service.get_academic_level_info(effective_level)
                self.console.print(f"[white]✓ Loaded session: {chat_session.title} ({message_count} messages, {level_info['name']})[/white]")
                
                return True
                
        except (SQLAlchemyError, ValueError) as e:
            self.console.print(f"[bright_red]✗ Failed to load session: {e}[/bright_red]")
            return False
                
        except (SQLAlchemyError, ValueError) as e:
            self.console.print(f"[bright_red]✗ Failed to load session: {e}[/bright_red]")
            return False
    
    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List user's chat sessions"""
        try:
            with self.database.get_session() as session:
                chat_sessions = session.query(ChatSession).filter(
                    ChatSession.user_id == self.user_id,
                    ChatSession.is_archived == False
                ).order_by(ChatSession.last_active.desc()).limit(limit).all()
                
                return [cs.to_dict() for cs in chat_sessions]
                
        except SQLAlchemyError as e:
            self.console.print(f"[bright_red]✗ Failed to list sessions: {e}[/bright_red]")
            return []
    
    def show_sessions_table(self):
        """Display sessions with academic level information"""
        sessions = self.list_sessions()
        
        if not sessions:
            self.console.print("[dim]No chat sessions found. Use /new to create one.[/dim]")
            return
        
        table = Table(show_header=True, header_style="white", border_style="white", box=None)
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", style="white", min_width=20)
        table.add_column("Level", style="cyan", width=10)
        table.add_column("Messages", justify="center", width=8)
        table.add_column("Last Active", style="dim", width=12)
        table.add_column("ID", style="dim", width=10)
        
        for i, session_data in enumerate(sessions, 1):
            # Format last active time
            last_active = datetime.fromisoformat(session_data['last_active'])
            time_diff = datetime.utcnow() - last_active
            
            if time_diff.days > 0:
                time_str = f"{time_diff.days}d ago"
            elif time_diff.seconds > 3600:
                hours = time_diff.seconds // 3600
                time_str = f"{hours}h ago"
            elif time_diff.seconds > 60:
                minutes = time_diff.seconds // 60
                time_str = f"{minutes}m ago"
            else:
                time_str = "now"
            
            # Current session indicator
            title = session_data['title']
            if session_data['session_id'] == self.current_session_id:
                title = f"[white]→ {title}[/white]"
            
            # Academic level display
            session_level = session_data.get('session_academic_level')
            if session_level:
                level_display = session_level.upper()
            else:
                level_display = "DEFAULT"
            
            table.add_row(
                str(i),
                title,
                level_display,
                str(session_data['message_count']),
                time_str,
                session_data['session_id'][:8]
            )
        
        panel = Panel.fit(
            table,
            title="[white]MATH SESSIONS[/white]",
            border_style="white",
            padding=(1, 2)
        )
        self.console.print(panel)
        self.console.print()
    
    def send_message_stream(self, message: str):
        """Send message to AI with current academic level - returns generator"""
        if not self.current_session_id:
            # Create a new session if none exists
            self.create_new_session("Math Session")
        
        current_level = self.get_current_academic_level()
        return self.ai_service.send_message_stream(message, self.chat_history, current_level)
    
    def send_message(self, message: str) -> str:
        """Send message to AI with current academic level (non-streaming version)"""
        if not self.current_session_id:
            # Create a new session if none exists
            self.create_new_session("Math Session")
        
        try:
            current_level = self.get_current_academic_level()
            
            # Send to AI with academic level
            ai_response = self.ai_service.send_message(message, self.chat_history, current_level)
            
            if not ai_response['success']:
                return ai_response['response']
            
            response_text = ai_response['response']
            
            # Save to database
            self._save_message_to_db(
                message, 
                response_text,
                ai_response.get('tokens_used'),
                ai_response.get('response_time_ms')
            )
            
            # Update chat history
            self.chat_history = ai_response['chat_history']
            
            return response_text
            
        except Exception as e:
            self.console.print(f"[bright_red]✗ Failed to send message: {e}[/bright_red]")
            return "I... I seem to be having technical difficulties. Please try again."
    
    def _save_message_to_db(self, user_message: str, ai_response: str, tokens_used: int = None, response_time: int = None):
        """Save conversation messages to database"""
        try:
            with self.database.get_session() as session:
                chat_session = ensure_user_owns_session(session, self.current_session_id, self.user_id)
                
                # Save user message
                user_msg = Message(
                    chat_session_id=chat_session.id,
                    role="user",
                    content=user_message
                )
                session.add(user_msg)
                
                # Save AI response
                ai_msg = Message(
                    chat_session_id=chat_session.id,
                    role="assistant",
                    content=ai_response,
                    tokens_used=tokens_used,
                    response_time_ms=response_time
                )
                session.add(ai_msg)
                
                # Update session
                chat_session.message_count += 2
                chat_session.last_active = datetime.utcnow()
                chat_session.store_ai_context(self.chat_history)
                
                # Auto-generate title for first message
                if chat_session.message_count == 2 and chat_session.title == "New Math Session":
                    new_title = self._generate_title_from_message(user_message)
                    chat_session.title = new_title
                
                session.commit()
                
                # Update local state
                self.current_session = chat_session.to_dict(include_ai_context=True)
                
        except Exception as e:
            self.console.print(f"[bright_red]✗ Failed to save to database: {e}[/bright_red]")
    
    def rename_session(self, new_title: str) -> bool:
        """Rename the current session"""
        if not self.current_session_id:
            self.console.print("[bright_red]✗ No active session to rename[/bright_red]")
            return False
        
        try:
            with self.database.get_session() as session:
                chat_session = ensure_user_owns_session(session, self.current_session_id, self.user_id)
                chat_session.title = new_title
                chat_session.last_active = datetime.utcnow()
                session.commit()
                
                # Update local state
                self.current_session = chat_session.to_dict(include_ai_context=True)
                
                self.console.print(f"[white]✓ Session renamed to: {new_title}[/white]")
                return True
                
        except (SQLAlchemyError, ValueError) as e:
            self.console.print(f"[bright_red]✗ Failed to rename session: {e}[/bright_red]")
            return False
    
    def delete_session(self, session_id: str = None) -> bool:
        """Delete a session (current session if no ID provided)"""
        target_session_id = session_id or self.current_session_id
        
        if not target_session_id:
            self.console.print("[bright_red]✗ No session specified[/bright_red]")
            return False
        
        try:
            with self.database.get_session() as session:
                chat_session = ensure_user_owns_session(session, target_session_id, self.user_id)
                session.delete(chat_session)
                session.commit()
                
                # If deleting current session, clear it
                if target_session_id == self.current_session_id:
                    self.current_session_id = None
                    self.current_session = None
                    self.chat_history = []
                
                self.console.print("[white]✓ Session deleted[/white]")
                return True
                
        except (SQLAlchemyError, ValueError) as e:
            self.console.print(f"[bright_red]✗ Failed to delete session: {e}[/bright_red]")
            return False
    
    def clear_current_session(self) -> bool:
        """Clear messages from current session"""
        if not self.current_session_id:
            self.console.print("[bright_red]✗ No active session to clear[/bright_red]")
            return False
        
        try:
            with self.database.get_session() as session:
                chat_session = ensure_user_owns_session(session, self.current_session_id, self.user_id)
                
                # Delete all messages
                session.query(Message).filter(
                    Message.chat_session_id == chat_session.id
                ).delete()
                
                # Clear AI context and reset counters
                chat_session.clear_ai_context()
                chat_session.message_count = 0
                chat_session.last_active = datetime.utcnow()
                
                session.commit()
                
                # Update local state
                self.current_session = chat_session.to_dict(include_ai_context=True)
                self.chat_history = []
                
                self.console.print("[white]✓ Session cleared[/white]")
                return True
                
        except (SQLAlchemyError, ValueError) as e:
            self.console.print(f"[bright_red]✗ Failed to clear session: {e}[/bright_red]")
            return False
    
    def get_session_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get message history for current session"""
        if not self.current_session_id:
            return []
        
        try:
            with self.database.get_session() as session:
                chat_session = ensure_user_owns_session(session, self.current_session_id, self.user_id)
                
                messages = session.query(Message).filter(
                    Message.chat_session_id == chat_session.id
                ).order_by(Message.timestamp.asc()).limit(limit).all()
                
                return [msg.to_dict() for msg in messages]
                
        except (SQLAlchemyError, ValueError) as e:
            self.console.print(f"[bright_red]✗ Failed to get history: {e}[/bright_red]")
            return []
    
    def show_session_history(self, limit: int = 10):
        """Display recent session history"""
        if not self.current_session_id:
            self.console.print("[dim]No active session. Start a conversation first.[/dim]")
            return
        
        history = self.get_session_history(limit)
        
        if not history:
            self.console.print("[dim]No message history in current session.[/dim]")
            return
        
        self.console.print(f"\n[white]Recent History - {self.current_session['title']}[/white]\n")
        
        for msg in history[-limit:]:  # Show last N messages
            timestamp = datetime.fromisoformat(msg['timestamp']).strftime("%H:%M")
            role_prefix = "YOU" if msg['role'] == "user" else "FAUST"
            role_style = "white" if msg['role'] == "user" else "white"
            
            content_preview = msg['content'][:80]
            if len(msg['content']) > 80:
                content_preview += "..."
            
            self.console.print(f"[dim]{timestamp}[/dim] [{role_style}]{role_prefix}:[/{role_style}] {content_preview}")
        
        self.console.print()
    
    def _generate_title_from_message(self, message: str) -> str:
        """Generate a title from the first user message"""
        # Take first 4-6 words, max 35 characters
        words = message.split()
        title = " ".join(words[:6])
        
        if len(title) > 35:
            title = title[:32] + "..."
        
        return title if title else "Math Session"
    
    def get_current_session_info(self) -> Dict[str, Any]:
        """Get information about current session including academic level"""
        if not self.current_session:
            return {
                'active': False,
                'message': 'No active session'
            }
        
        current_level = self.get_current_academic_level()
        level_info = self.ai_service.get_academic_level_info(current_level)
        
        return {
            'active': True,
            'session_id': self.current_session_id,
            'title': self.current_session['title'],
            'message_count': self.current_session['message_count'],
            'created_at': self.current_session['created_at'],
            'last_active': self.current_session['last_active'],
            'academic_level': current_level,
            'academic_level_info': level_info
        }

def create_session_manager(user_id: int) -> SessionManager:
    """Create a new session manager for a user"""
    return SessionManager(user_id)