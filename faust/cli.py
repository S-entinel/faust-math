

import sys
import signal
import time
import random
from typing import List, Optional, Dict, Any
from datetime import datetime
import click
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.live import Live

from .config import get_config
from .auth import get_auth
from .session_manager import create_session_manager
from .ai_service import get_ai_service
from .math_renderer import get_math_renderer

class FaustCLI:
    """Natural chat interface for Faust Math Teacher"""
    
    def __init__(self):
        self.config = get_config()
        self.auth = get_auth()
        self.console = Console()
        self.session_manager = None
        self.ai_service = None
        self.math_renderer = get_math_renderer()
        
        # Application state
        self.running = False
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.console.print("\n[dim]Connection terminated.[/dim]")
        self.running = False
        sys.exit(0)
    
    def start(self):
        """Start the Faust CLI application"""
        self.console.clear()
        
        try:
            # Authentication
            if not self.auth.show_welcome_screen():
                return
            
            # Initialize services after authentication
            self._initialize_services()
            
            # Show initial connection
            self._show_connection_established()
            
            # Main conversation loop
            self._conversation_loop()
            
        except KeyboardInterrupt:
            self.console.print("\n[dim]Connection closed.[/dim]")
        except Exception as e:
            self.console.print(f"[bright_red]Connection error: {e}[/bright_red]")
            sys.exit(1)
    
    def _initialize_services(self):
        """Initialize services after authentication"""
        user = self.auth.get_current_user()
        if not user:
            raise RuntimeError("Authentication failed")
        
        self.console.print("[dim]Establishing connection...[/dim]")
        
        # Initialize AI service
        self.ai_service = get_ai_service()
        
        # Initialize session manager
        self.session_manager = create_session_manager(user['id'])
        
        # Load or create default session
        sessions = self.session_manager.list_sessions(1)
        if sessions:
            self.session_manager.load_session(sessions[0]['session_id'])
        else:
            self.session_manager.create_new_session("Math Discussion")
        
        time.sleep(0.5)  # Brief pause for realism
    
    def _show_connection_established(self):
        """Show connection to Faust"""
        user = self.auth.get_current_user()
        username = user.get('display_name') or user.get('username')
        
        self.console.print(f"[bright_black]Connected to FAUST-AI[/bright_black]")
        self.console.print(f"[bright_black]User: {username}[/bright_black]")
        self.console.print()
        
        # Faust's greeting
        time.sleep(0.3)
        self.console.print("[bright_black]Faust is online[/bright_black]")
        time.sleep(0.8)
        
        greeting = self.ai_service.get_conversation_starter()
        self._display_faust_message(greeting)
        
        self.console.print()
        self.console.print("[dim]Type your message or /help for commands[/dim]")
        self.console.print()
    
    def _conversation_loop(self):
        """Main conversation loop"""
        self.running = True
        
        while self.running:
            try:
                # Simple prompt
                user_input = Prompt.ask("[white]You[/white]", show_default=False)
                
                if not user_input.strip():
                    continue
                
                # Handle commands
                if user_input.startswith('/'):
                    self._handle_command(user_input)
                else:
                    # Chat message
                    self._handle_chat_message(user_input)
                
            except KeyboardInterrupt:
                self.running = False
            except EOFError:
                self.running = False
            except Exception as e:
                self.console.print(f"[bright_red]Error: {e}[/bright_red]")
    
    def _handle_command(self, command: str):
        """Handle slash commands"""
        cmd = command.strip().lower()
        
        if cmd == '/help':
            self._show_help()
        elif cmd == '/quit' or cmd == '/exit':
            self.console.print("\n[dim]Faust: Until next time.[/dim]")
            self.running = False
        elif cmd == '/clear':
            self.console.clear()
        elif cmd == '/new':
            self.session_manager.create_new_session("New Discussion")
            self.console.print("[bright_black]Started new conversation[/bright_black]")
        elif cmd == '/history':
            self._show_simple_history()
        elif cmd == '/sessions':
            self._show_simple_sessions()
        elif cmd == '/logout':
            if Confirm.ask("End session?"):
                self.auth.logout()
                self.running = False
        else:
            self.console.print(f"[bright_red]Unknown command: {cmd}[/bright_red]")
            self.console.print("[dim]Type /help for available commands[/dim]")
    
    def _handle_chat_message(self, message: str):
        """Handle regular chat message with streaming"""
        # Show thinking indicators
        thinking_messages = [
            "Faust is thinking...",
            "Faust is analyzing...",
            "Faust is processing...",
            "Faust is calculating..."
        ]
        
        thinking_msg = random.choice(thinking_messages)
        
        # Show thinking with delay
        with self.console.status(f"[dim]{thinking_msg}[/dim]", spinner="dots"):
            time.sleep(random.uniform(0.8, 1.5))  # Realistic thinking time
        
        # Show typing indicator
        self.console.print(f"[dim]Faust is typing...[/dim]")
        time.sleep(0.5)
        
        # Stream the response
        self._stream_faust_response(message)
    
    def _stream_faust_response(self, user_message: str):
        """Stream Faust's response naturally"""
        full_response = ""
        response_display = Text()
        
        try:
            # Use Live for smooth streaming
            with Live(response_display, console=self.console, refresh_per_second=15, transient=False) as live:
                # Show "Faust:" label first
                self.console.print("[white]Faust:[/white] ", end="")
                
                for chunk_data in self.session_manager.send_message_stream(user_message):
                    if chunk_data['chunk']:
                        # Add each character with natural typing speed
                        for char in chunk_data['chunk']:
                            full_response += char
                            
                            # Render math and display
                            rendered = self.math_renderer.render(full_response)
                            response_display = Text.from_markup(rendered, style="white")
                            
                            live.update(response_display)
                            
                            # Variable typing speed for realism
                            if char in '.,!?':
                                time.sleep(random.uniform(0.1, 0.3))  # Pause at punctuation
                            elif char == ' ':
                                time.sleep(random.uniform(0.03, 0.08))  # Brief pause at spaces
                            else:
                                time.sleep(random.uniform(0.01, 0.05))  # Regular typing speed
                    
                    if chunk_data['is_complete']:
                        # Save to database
                        if chunk_data.get('chat_history'):
                            self.session_manager.chat_history = chunk_data['chat_history']
                            self.session_manager._save_message_to_db(
                                user_message, 
                                full_response,
                                chunk_data.get('tokens_used'), 
                                chunk_data.get('response_time_ms')
                            )
                        break
        
        except Exception as e:
            self.console.print(f"\n[bright_red]Faust: I'm having technical difficulties... {e}[/bright_red]")
        
        self.console.print()  # Add space after response
    
    def _display_faust_message(self, message: str):
        """Display a static message from Faust with typing effect"""
        self.console.print("[white]Faust:[/white] ", end="")
        
        rendered_message = self.math_renderer.render(message)
        
        # Simple typing effect for static messages
        for char in rendered_message:
            print(char, end="", flush=True)
            if char in '.,!?':
                time.sleep(random.uniform(0.1, 0.2))
            elif char == ' ':
                time.sleep(random.uniform(0.02, 0.05))
            else:
                time.sleep(random.uniform(0.01, 0.03))
        
        print()  # New line after message
    
    def _show_help(self):
        """Show available commands"""
        self.console.print()
        self.console.print("[white]Available commands:[/white]")
        self.console.print("  /help     - Show this help")
        self.console.print("  /clear    - Clear screen")
        self.console.print("  /new      - Start new conversation")
        self.console.print("  /history  - Show recent messages")
        self.console.print("  /sessions - Show all conversations")
        self.console.print("  /logout   - End session")
        self.console.print("  /quit     - Exit application")
        self.console.print()
        self.console.print("[dim]Just type your math question to chat with Faust[/dim]")
        self.console.print()
    
    def _show_simple_history(self):
        """Show recent conversation history"""
        if not self.session_manager.current_session_id:
            self.console.print("[dim]No active conversation[/dim]")
            return
        
        history = self.session_manager.get_session_history(10)
        
        if not history:
            self.console.print("[dim]No message history[/dim]")
            return
        
        self.console.print()
        self.console.print("[white]Recent conversation:[/white]")
        self.console.print()
        
        for msg in history[-5:]:  # Show last 5 messages
            timestamp = datetime.fromisoformat(msg['timestamp']).strftime("%H:%M")
            speaker = "You" if msg['role'] == "user" else "Faust"
            
            content = msg['content'][:100]
            if len(msg['content']) > 100:
                content += "..."
            
            self.console.print(f"[dim]{timestamp}[/dim] [white]{speaker}:[/white] {content}")
        
        self.console.print()
    
    def _show_simple_sessions(self):
        """Show conversation sessions"""
        sessions = self.session_manager.list_sessions(10)
        
        if not sessions:
            self.console.print("[dim]No conversations yet[/dim]")
            return
        
        self.console.print()
        self.console.print("[white]Your conversations:[/white]")
        self.console.print()
        
        for i, session in enumerate(sessions, 1):
            title = session['title'][:40]
            if len(session['title']) > 40:
                title += "..."
            
            last_active = datetime.fromisoformat(session['last_active'])
            time_diff = datetime.utcnow() - last_active
            
            if time_diff.days > 0:
                time_str = f"{time_diff.days}d ago"
            elif time_diff.seconds > 3600:
                hours = time_diff.seconds // 3600
                time_str = f"{hours}h ago"
            else:
                minutes = time_diff.seconds // 60
                time_str = f"{minutes}m ago"
            
            current = " (current)" if session['session_id'] == self.session_manager.current_session_id else ""
            
            self.console.print(f"  {i}. {title} - {session['message_count']} messages - {time_str}{current}")
        
        self.console.print()
        self.console.print("[dim]Use /load <session_id> to switch conversations[/dim]")
        self.console.print()

# Click CLI interface
@click.command()
@click.version_option()
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--config-dir', help='Custom configuration directory')
def main(debug: bool, config_dir: Optional[str]):
    """
    Faust - AI Math Teacher Terminal Application
    
    A brilliant but emotionally distant AI math tutor that runs in your terminal.
    Built with Python, Rich UI, and Google Gemini AI.
    """
    try:
        # Override config directory if specified
        if config_dir:
            import os
            os.environ['FAUST_CONFIG_DIR'] = config_dir
        
        # Set debug mode
        if debug:
            os.environ['FAUST_DEBUG'] = '1'
        
        # Start the CLI application
        app = FaustCLI()
        app.start()
        
    except KeyboardInterrupt:
        print("\nConnection closed.")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()