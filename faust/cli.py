import sys
import os
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
from rich.table import Table
from rich.panel import Panel

from .config import get_config
from .auth import get_auth
from .session_manager import create_session_manager
from .ai_service import get_ai_service
from .math_renderer import get_math_renderer

class FaustCLI:
    """Natural chat interface for Faust"""
    
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
        """Enhanced connection display with academic level info"""
        user = self.auth.get_current_user()
        username = user.get('display_name') or user.get('username')
        
        self.console.print(f"[bright_black]Connected to FAUST-AI[/bright_black]")
        self.console.print(f"[bright_black]User: {username}[/bright_black]")
        
        # Show current academic level
        current_level = self.session_manager.get_current_academic_level()
        level_info = self.ai_service.get_academic_level_info(current_level)
        self.console.print(f"[bright_black]Academic Level: {level_info['name']}[/bright_black]")
        self.console.print()
        
        # Faust's greeting
        time.sleep(0.3)
        self.console.print("[bright_black]Faust is online[/bright_black]")
        time.sleep(0.8)
        
        greeting = self.ai_service.get_conversation_starter(current_level)
        self._display_faust_message(greeting)
        
        self.console.print()
        self.console.print("[dim]Type your message or /help for commands[/dim]")
        self.console.print(f"[dim]Current academic level: {level_info['name']} (use /level to change)[/dim]")
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
        """Enhanced command handler with academic level commands"""
        cmd_parts = command.strip().split()
        cmd = cmd_parts[0].lower()
        
        if cmd == '/help':
            self._show_help()
        elif cmd == '/quit' or cmd == '/exit':
            self.console.print("\n[dim]Faust: Until next time.[/dim]")
            self.running = False
        elif cmd == '/clear':
            self.console.clear()
        elif cmd == '/new':
            self._handle_new_session_command(cmd_parts)
        elif cmd == '/history':
            self._show_simple_history()
        elif cmd == '/sessions':
            self._show_simple_sessions()
        elif cmd == '/load':
            self._handle_load_session(cmd_parts)
        elif cmd == '/level':
            self._handle_academic_level_command(cmd_parts)
        elif cmd == '/info':
            self._show_session_info()
        elif cmd == '/logout':
            if Confirm.ask("End session?"):
                self.auth.logout()
                self.running = False
        else:
            self.console.print(f"[bright_red]Unknown command: {cmd}[/bright_red]")
            self.console.print("[dim]Type /help for available commands[/dim]")
    
    def _handle_new_session_command(self, cmd_parts: List[str]):
        """Handle creating new session with optional academic level"""
        title = "New Discussion"
        academic_level = None
        
        # Parse arguments: /new [title] --level [level]
        if len(cmd_parts) > 1:
            args = cmd_parts[1:]
            
            # Look for --level flag
            if '--level' in args:
                level_index = args.index('--level')
                if level_index + 1 < len(args):
                    academic_level = args[level_index + 1]
                    # Remove level args from title
                    args = args[:level_index] + args[level_index + 2:]
            
            # Remaining args are title
            if args:
                title = ' '.join(args)
        
        self.session_manager.create_new_session(title, academic_level)
        
        # Show greeting in new academic level
        current_level = self.session_manager.get_current_academic_level()
        greeting = self.ai_service.get_conversation_starter(current_level)
        self._display_faust_message(greeting)
        self.console.print()

    def _handle_load_session(self, cmd_parts: List[str]):
        """Handle loading a specific session by ID"""
        if len(cmd_parts) < 2:
            self.console.print("[bright_red]Usage: /load <session_id>[/bright_red]")
            self.console.print("[dim]Get session IDs from /sessions command[/dim]")
            return
        
        session_id = cmd_parts[1]
        
        # Try to load the session
        if self.session_manager.load_session(session_id):
            session_info = self.session_manager.get_current_session_info()
            self.console.print(f"[white]✓ Loaded session: {session_info['title']}[/white]")
        else:
            self.console.print("[bright_red]✗ Failed to load session. Check the session ID and try again.[/bright_red]")
    
    def _handle_academic_level_command(self, cmd_parts: List[str]):
        """Handle academic level commands"""
        if len(cmd_parts) == 1:
            # Show current level info
            self.session_manager.show_academic_level_info()
            return
        
        subcommand = cmd_parts[1].lower()
        
        if subcommand == 'set':
            if len(cmd_parts) < 3:
                self.console.print("[bright_red]Usage: /level set <child|normal|academic> [--session-only][/bright_red]")
                return
            
            level = cmd_parts[2].lower()
            session_only = '--session-only' in cmd_parts
            
            if self.session_manager.set_academic_level(level, session_only):
                # Give Faust a chance to react to level change
                current_level = self.session_manager.get_current_academic_level()
                reaction = self._get_level_change_reaction(current_level)
                self._display_faust_message(reaction)
                self.console.print()
        
        elif subcommand == 'info':
            self.session_manager.show_academic_level_info()
        
        elif subcommand == 'list':
            self._show_available_levels()
        
        else:
            self.console.print("[bright_red]Usage: /level [set <level>] [info] [list][/bright_red]")
    
    def _show_available_levels(self):
        """Display all available academic levels"""
        levels = ['child', 'normal', 'academic']
        
        table = Table(show_header=True, header_style="white", border_style="white", box=None)
        table.add_column("Level", style="white", width=12)
        table.add_column("Description", style="white", min_width=25)
        table.add_column("Complexity", style="cyan", width=12)
        table.add_column("Example Topics", style="dim", min_width=30)
        
        for level in levels:
            level_info = self.ai_service.get_academic_level_info(level)
            current = " (current)" if level == self.session_manager.get_current_academic_level() else ""
            
            table.add_row(
                f"{level_info['name']}{current}",
                level_info['description'],
                level_info['complexity'],
                ", ".join(level_info['topics'][:2]) + "..."
            )
        
        panel = Panel.fit(
            table,
            title="[white]AVAILABLE ACADEMIC LEVELS[/white]",
            border_style="white",
            padding=(1, 2)
        )
        self.console.print(panel)
        self.console.print()
        
        self.console.print("[dim]Use '/level set <level>' to change academic level[/dim]")
        self.console.print("[dim]Use '/level set <level> --session-only' to change for current session only[/dim]")
        self.console.print()
    
    def _get_level_change_reaction(self, new_level: str) -> str:
        """Get Faust's reaction to academic level change"""
        reactions = {
            'child': [
                "Oh! Well, I suppose I should adjust my explanations for a younger student. Don't worry, I'll be... gentler with the mathematical concepts.",
                "I see we're switching to a more elementary approach. Very well, I can work with students of all ages... though I do hope you'll still appreciate the beauty of mathematics!",
                "Hmph, fine. I'll use simpler language, but the mathematical rigor remains the same! Mathematics is mathematics, regardless of age."
            ],
            'normal': [
                "Ah, back to the standard level. This is... comfortable territory for most students. We can cover proper high school mathematics now.",
                "Good, we're at a reasonable academic level. I can provide appropriately challenging explanations without overwhelming you.",
                "Normal mode it is. Perfect for building solid mathematical foundations... which you'll need if you want to advance further."
            ],
            'academic': [
                "Excellent! Finally, someone ready for serious mathematical discourse. I can use proper notation and advanced concepts without holding back.",
                "Academic level, I see. Good. Now we can engage in real mathematical analysis without... dumbing things down unnecessarily.",
                "Perfect. I was getting tired of oversimplifying everything. Let's discuss mathematics at the level it deserves to be discussed."
            ]
        }
        
        import random
        return random.choice(reactions.get(new_level, ["Level changed. Let's continue with our mathematical discussion."]))
    
    def _show_session_info(self):
        """Display current session and academic level information"""
        session_info = self.session_manager.get_current_session_info()
        
        if not session_info['active']:
            self.console.print("[dim]No active session. Start a conversation first.[/dim]")
            return
        
        level_info = session_info['academic_level_info']
        
        table = Table(show_header=False, box=None, border_style="white")
        table.add_column("Field", style="white", width=15)
        table.add_column("Value", style="white")
        
        table.add_row("Session", session_info['title'])
        table.add_row("Messages", str(session_info['message_count']))
        table.add_row("Academic Level", f"{level_info['name']}")
        table.add_row("Complexity", level_info['complexity'])
        table.add_row("Session ID", session_info['session_id'][:12] + "...")
        
        # Format timestamps
        created = datetime.fromisoformat(session_info['created_at']).strftime("%Y-%m-%d %H:%M")
        last_active = datetime.fromisoformat(session_info['last_active']).strftime("%Y-%m-%d %H:%M")
        
        table.add_row("Created", created)
        table.add_row("Last Active", last_active)
        
        panel = Panel.fit(
            table,
            title="[white]CURRENT SESSION INFO[/white]",
            border_style="white",
            padding=(1, 2)
        )
        self.console.print(panel)
        self.console.print()
    
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
        """Enhanced help with academic level commands"""
        self.console.print()
        self.console.print("[white]Available commands:[/white]")
        self.console.print("  [white]Basic Commands:[/white]")
        self.console.print("    /help           - Show this help")
        self.console.print("    /clear          - Clear screen")
        self.console.print("    /info           - Show session information")
        self.console.print("    /quit           - Exit application")
        self.console.print()
        self.console.print("  [white]Session Management:[/white]")
        self.console.print("    /new [title]    - Start new conversation")
        self.console.print("    /history        - Show recent messages")
        self.console.print("    /sessions       - Show all conversations")
        self.console.print("    /load <id>      - Load conversation by session ID")
        self.console.print()
        self.console.print("  [white]Academic Level Control:[/white]")
        self.console.print("    /level          - Show current academic level")
        self.console.print("    /level list     - Show all available levels")
        self.console.print("    /level set <level>  - Set academic level (child/normal/academic)")
        self.console.print("    /level set <level> --session-only  - Set level for current session only")
        self.console.print()
        self.console.print("  [white]Account:[/white]")
        self.console.print("    /logout         - End session")
        self.console.print()
        self.console.print("[dim]Just type your math question to chat with Faust[/dim]")
        self.console.print("[dim]Faust adapts her explanations based on your academic level[/dim]")
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
            self.console.print(f"     [dim]ID: {session['session_id']}[/dim]")
        
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