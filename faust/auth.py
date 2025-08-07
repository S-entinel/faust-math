
import os
import jwt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.exc import SQLAlchemyError
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich.align import Align

from .database import get_database, get_user_by_username, create_user, User
from .config import get_config

class AuthenticationError(Exception):
    """Authentication related errors"""
    pass

class TerminalAuth:
    """Terminal-based authentication system"""
    
    def __init__(self):
        self.config = get_config()
        self.database = get_database()
        self.console = Console()
        
        # JWT Configuration
        self.jwt_secret = self.config.jwt_secret_key
        self.jwt_algorithm = 'HS256'
        self.jwt_expire_hours = 24
        
        # Current user state
        self.current_user = None
        self.access_token = None
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        return self.current_user is not None and self.access_token is not None
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current authenticated user"""
        return self.current_user
    

    def show_welcome_screen(self):
        """Display enhanced welcome screen with fading ASCII art overlay"""
        self.console.clear()
        
        # Try to restore previous session first
        if self._try_restore_session():
            return True
        
        # ASCII art for Faust (scaled down and optimized)
        faust_art = """
    ╬╬╣▓▓▓███████████████████████████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓█▓████▓▓▓▓▒
    ╣▓▓█████▓▓████████████████████████████▓▓▓▓▓▓▓▓▓▓██▓▓▓▓▓▓▓▓██▓▓▓▓▓▓▓▓██▓█████████
    ▓██████▓▓██████████████▓███████████████▓▓▓██▓▓▓▓▓███▓▓▓▓▓███████▓▓██▓▓▓███▓▓▓▓▓▓
    ███████▓▓█████████████▓▓██████▓████████▓▓▓▓▓██▓▓▓▓████▓▓▓█▓███████▓▓███▓╬▓█▓▓▓▓▓
    ██████▓▓█████████████▓▓███████▓▓█▓▓█████▓▓▓▓▓▓█▓▓▓██████▓▓████████▓▓▓▓███▓▓▓▓█▓▓
    █▓███▓▓▓███▓▓███████▓▓▓█▓█▓███▓╫▓▓▓██▓███▓▓▓▓▓▓██▓▓▓██████▓██████▓▓▓▓▓▓▓▓██▓▓▓▓▓
    ▓▓▓█▓▓▓▓█▓▓▓▓█████▓█▓▓██▓▓▓▓█▓▓╟▓▓╬▓▓██▓▓▓▓▓▓▓╬▓▓██▓▓█████▓▓▓█████▓▓▓▓▓╬▓▓▓██▓▓▓
    ▓▓▓▓▓▓▓█▓▓▓▓███▓█▓▓▓▓▓█▓▓▓▓▓█▓▌╚▓▓▒╫▓▓▓▓▓▓▓▓╣▓▓╬╣╬▓██▓▓██▓▓▓▓▓████▓▓▓▓▓▓▓▓▓▓▓███
    ▓▓▓▓▓▓▓▓▓▓▓▓█▓█▓▓╬▓▓▓▓▓╣▓▓▓▓▓▓▌░▓▓▓╙▓╣▓▓▓▓╣▓▓╬▓▓╬╬╣▓██▓▓███▓▓▓▓█████▓▓▓▓▓▓▓▓▓▓▓█
    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▌╫▓▓▓▓▓╢▓▓▓▓▓▓▌░╟▓▓▒╠▓╣▓▓▓▓╣▓▓╬▓▓▓╬╣▓███▓▓███▓▓▓▓█████▓▓▓▓▓▓▓▓▓█
    ▓▓▓▓▓▓▓▓▓▓▓▓▓█▓▓▒▓▓▓▓▓▓╟▓▓▓▓▓▓▌░╙▓▓▌░╟▓╣▓▓▓▓▓▓▓▒╟▓▓╬╣▓▓███▓████▓███████▓▓██████▓
    ▓▓▓█▓▓▓▓▓▓▓▓██▓▓░▓▓▓▓▓▓▐▓█▓▓▓▓▌░░╟╬▓░░╣╬╣▓▓█▓▓▓▓▓╠▓▓▒╠▓▓▓██████████▓█████▓██████
    ▓▓██▓▓▓▓▓▓▓███▓▓░▓█████▀███████#╦░╬╣▌░Γ╢╬╬╣▓██▓███╬▓█▓╙╬█▓████████████████▓█████
    ▓▓██▓▓▓▓▓▓▓████▓│▓╬▓▓▓▓░▓████▓▓▒░░╠╬╬▒░!╟╚╬╬▓▓▓▓▓▓▓▒╙▓▓░╠▓▓▓█▓▓█████████████▓███
    ▓▓██▓█▓▓▓▓▓██╫▓▓░╫▒▓▓▓▓▒╟████▓▓▌░'^╠╢▓░ '╠░▒╚╬╣╬╬▓▓▓▓╠▓▓▄╬█▓╬▓╬╣▓███████████████
    ╬▓▓█▓▓▓▓▓▓▓█▒╚▓▓▄▓███████████▓╢▓░   ╠╬▓⌐  ╙'░╙▒╩╠╫▓████████████▓▓╬▓█████████████
    ╬╣▓██▓█▓▓▓██▒░▓███╬███████▀███╬╩╩              '░╣▀╟████████▀████▌░░███▓▓███████
    ╬╣█████▓▓▓██▒░▓█▓▒╠███████▓▓██░'                   ╚████████▓▓█╬██╩║██░░≥ⁿ▓█████
    ╬╣▓█▓██▓▓▓▓█░"╙╝╩╙╙╙╙▓▓██▓▓╬╬█░                      ║▓▓▓▓▓▓╬╣█╢╨ .▓▓░░└!░╙█████
    ╬╬▓█¬║▓▓▓▓▓▓▌      ]▓╬╬╣╣╬╩╚╩▓                      ╫▒░╚╣╣╬╩╠▓▀   ▐▓░░░~ ! ▓████
    ╬╬▓▌,░▓▓▓▓▓▓█▌      ╟▓▒░░░╦▄▓▒                      ▐▓▄▄▄▄▄▄▓╩    ╬░░░!   ╔█████
    ╠╬╣▓Q'╚▓▓▓▓▓▓╫▄     ^╫▓▀▀▀▀╙╙                        `└╙╙╙╙╙╙    ▐░╙┘", ,▄██████
    ░╠▓▓▓▓▄▓▓▓▓▓▓▒╠⌐                                                ]▒░░∩",▓████████
    ░╠▓█▓▓▓▓▓▓▓▓▓▓ "                        [                       ╩   ,▓██████████
    │▐▓█▓▓▓▓▓▓▓▓▓▓▌,,                       ░                      ▒,,,▓████████████
    │░▓▓▓╣▓▓▓▓▓▓▓▓▓▓▓▓µ                     ]                     ╣█▓▓████████▓█████
    ┐░▓▓▓╣▓▓▓▓▓▓▓▓▓▓▓▓▓▄                                        ╓▓████▓████████▓▓███
    │]▓╣█╣▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓µ                                    ╓▓███████▓█████████▓▓█
    ┐▐╬▓█╬▓▓▓▓╬╣╣╬╬▓▓▓▓▓▓█▓µ              ^   ^             ╓▓██████████▓▓████████▓▓
    │║╬▓▓╬╣▓▓▓▓╣╬╬╬╣▓▓▓▓▓███▓▄,                          ,▄▓█████████████▓▓███████▓▓
    │╫╬╬▓▓╫▓▓▓▓╬╬╬╣╬▓▓▓▓▓▓▓████▓▓▄                     =░▓█████████████████▓▓███████
    ¡╬╬╬╬╫╝▓▓▓▓▓╬╬╣╬▓▓▓▓▓╣▓▓███████▒≥,              ;░│░░▓██████████████████▓▓▓█████
    j╬╬╬╬░▒╣▓▓▓█╬╬╬╬╣▓▓▓▓▓▓▓▓██████▓░││░≥╓      ,≥░│││││¡╫████████████████████▓▓████
    ▐╬╬╬╬░╠╠▓▓▓▓╬╬╬╬╬▓▓▓▓▓▓▓▓▓█████▓▒░░░░││░≥»ê░│││░░##░░╚▀▓████████████████████▓███
    ╠╬╬╬╬ !▒╟▓▓▓▓╬╬╬╬╣▓▓▓▓▓▓▓▓▓███▒▒▒░░░░░░░░░░░░░░░░╬░░│''╟█████████████████████▓▓█
        """
        
        # Create overlay content with fading art effect
        from rich.align import Align
        from rich.text import Text
        import time
        
        # Show ASCII art with gradual fade out effect - centered
        art_lines = faust_art.strip().split('\n')
        fade_levels = ["white", "bright_white", "dim white", "bright_black", "dim bright_black"]
        
        # Calculate vertical centering
        terminal_height = self.console.size.height
        art_height = len(art_lines)
        vertical_padding = max(0, (terminal_height - art_height) // 2)
        
        for fade_level in fade_levels:
            # Force complete screen clear with escape sequences
            self.console.print("\033[2J\033[H", end="")  # Clear screen and move cursor to top
            self.console.clear()
            
            # Add vertical padding to center the art
            for _ in range(vertical_padding):
                self.console.print()
            
            # Display centered art
            for line in art_lines:
                self.console.print(Align.center(f"[{fade_level}]{line}[/{fade_level}]"))
            
            time.sleep(0.4)
        
        # Force complete clear with multiple methods to ensure no residue
        self.console.print("\033[2J\033[H", end="")  # ANSI escape sequence clear
        self.console.clear()  # Rich's clear method
        import os
        if os.name == 'nt':  # Windows
            os.system('cls')
        else:  # Unix/Linux/MacOS
            os.system('clear')
        
        time.sleep(0.5)  # Pause to ensure complete clear
        
        # Clean, elegant title reveal
        title_text = "F A U S T"
        subtitle_text = "An AI math tutor and assistant"
        
        # Minimalist title design
        self.console.print("\n" * 8)  # Center vertically
        
        # Main title with clean spacing
        title_display = Text()
        title_display.append(title_text, style="bold white")
        self.console.print(Align.center(title_display))
        self.console.print()
        
        # Subtitle with elegant styling
        subtitle_display = Text()
        subtitle_display.append(subtitle_text, style="dim white")
        self.console.print(Align.center(subtitle_display))
        self.console.print("\n" * 2)
        
        # Subtle initialization sequence
        init_states = [
            ("Initializing", 0.8),
            ("Loading knowledge base", 1.0),
            ("Connecting to AI", 0.9),
            ("Ready", 0.5)
        ]
        
        for state, delay in init_states:
            if state == "Ready":
                self.console.print(Align.center(f"[white]◆ {state}[/white]"))
            else:
                with self.console.status(Align.center(f"[dim white]◆ {state}...[/dim white]")):
                    time.sleep(delay)
        
        self.console.print("\n" * 3)
        
        # Clean authentication prompt
        auth_text = Text()
        auth_text.append("Authentication Required", style="white")
        self.console.print(Align.center(auth_text))
        
        auth_subtitle = Text()
        auth_subtitle.append("Please login or register to continue", style="dim white")
        self.console.print(Align.center(auth_subtitle))
        
        self.console.print("\n" * 2)
        
        # Mathematical decoration - minimal and elegant
        math_symbols = "∫ ∑ ∞ π δ λ"
        math_display = Text()
        math_display.append(math_symbols, style="dim bright_black")
        self.console.print(Align.center(math_display))
        
        self.console.print("\n" * 2)
        
        return self._auth_menu()

    def _show_faust_awakening_animation(self):
        """Show Faust waking up with mathematical elements"""
        import random
        import time
        
        # Mathematical equations that "compute" in the background
        equations = [
            "∫₋∞^∞ e^(-x²) dx = √π",
            "e^(iπ) + 1 = 0",
            "∑_{n=1}^∞ 1/n² = π²/6", 
            "lim_{x→0} (sin x)/x = 1",
            "∇²φ = 0"
        ]
        
        self.console.print(Align.center("[dim bright_black]◊ MATHEMATICAL CONSCIOUSNESS LOADING ◊[/dim bright_black]"))
        self.console.print()
        
        # Show equations "calculating"
        for eq in random.sample(equations, 3):
            with self.console.status(f"[dim]{eq}[/dim]", spinner="dots"):
                time.sleep(random.uniform(0.8, 1.5))
            self.console.print(f"[dim white]✓ {eq}[/dim white]")
        
        self.console.print()
        
        # Personality loading
        personality_traits = [
            "Loading mathematical rigor",
            "Calibrating academic precision", 
            "Initializing tsundere protocols",
            "Setting emotional barriers to 'distant'",
            "Preparing to be helpful... reluctantly"
        ]
        
        for trait in personality_traits:
            time.sleep(0.6)
            self.console.print(f"[dim bright_black]» {trait}[/dim bright_black]")
        
        self.console.print()
        time.sleep(1.5)
        
        # Final awakening
        self.console.print(Align.center("[white]◊ FAUST ONLINE ◊[/white]"))
        time.sleep(1.0)

    def _auth_menu(self) -> bool:
        """Display authentication menu"""
        while True:
            self.console.print("[white]Options:[/white]")
            self.console.print("  [1] Login")
            self.console.print("  [2] Register") 
            self.console.print("  [3] Quit")
            self.console.print()
            
            choice = Prompt.ask("Enter choice", choices=["1", "2", "3"], default="1", console=self.console)
            
            if choice == "1":
                if self._login():
                    return True
            elif choice == "2":
                if self._register():
                    return True
            elif choice == "3":
                self.console.print("\n[dim]Goodbye.[/dim]")
                return False
            
            self.console.print()
    
    def _login(self) -> bool:
        """Handle user login"""
        self.console.print("\n[white]LOGIN[/white]")
        self.console.print()
        
        try:
            username = Prompt.ask("Username", show_default=False, console=self.console)
            if not username:
                self.console.print("[bright_red]✗ Username cannot be empty[/bright_red]")
                return False
            
            password = Prompt.ask("Password", password=True, show_default=False, console=self.console)
            if not password:
                self.console.print("[bright_red]✗ Password cannot be empty[/bright_red]")
                return False
            
            # Attempt authentication
            with self.database.get_session() as session:
                user = get_user_by_username(session, username)
                
                if not user or not user.check_password(password):
                    self.console.print("[bright_red]✗ Invalid username or password[/bright_red]")
                    return False
                
                # Update last login
                user.last_login = datetime.utcnow()
                user.last_active = datetime.utcnow()
                session.commit()
                
                # Set authentication state
                self._set_authenticated_user(user)
                
                self.console.print(f"[white]✓ Welcome back, {user.display_name or user.username}[/white]")
                return True
        
        except SQLAlchemyError as e:
            self.console.print(f"[bright_red]✗ Database error: {e}[/bright_red]")
            return False
        except Exception as e:
            self.console.print(f"[bright_red]✗ Login failed: {e}[/bright_red]")
            return False
    
    def _register(self) -> bool:
        """Handle user registration"""
        self.console.print("\n[white]REGISTRATION[/white]")
        self.console.print()
        
        try:
            # Get username
            while True:
                username = Prompt.ask("Username (3-50 characters)", show_default=False, console=self.console)
                if not username:
                    self.console.print("[bright_red]✗ Username cannot be empty[/bright_red]")
                    continue
                if len(username) < 3:
                    self.console.print("[bright_red]✗ Username must be at least 3 characters[/bright_red]")
                    continue
                if len(username) > 50:
                    self.console.print("[bright_red]✗ Username must be less than 50 characters[/bright_red]")
                    continue
                break
            
            # Get email (optional)
            email = Prompt.ask("Email (optional)", default="", show_default=False, console=self.console)
            if email and not self._validate_email(email):
                self.console.print("[bright_red]✗ Invalid email format[/bright_red]")
                return False
            
            # Get display name (optional)
            display_name = Prompt.ask("Display name (optional)", default=username, show_default=False, console=self.console)
            
            # Get password
            while True:
                password = Prompt.ask("Password (minimum 6 characters)", password=True, show_default=False, console=self.console)
                if not password:
                    self.console.print("[bright_red]✗ Password cannot be empty[/bright_red]")
                    continue
                if len(password) < 6:
                    self.console.print("[bright_red]✗ Password must be at least 6 characters[/bright_red]")
                    continue
                
                # Confirm password
                password_confirm = Prompt.ask("Confirm password", password=True, show_default=False, console=self.console)
                if password != password_confirm:
                    self.console.print("[bright_red]✗ Passwords do not match[/bright_red]")
                    continue
                break
            
            # Create user
            with self.database.get_session() as session:
                try:
                    user = create_user(
                        session=session,
                        username=username,
                        password=password,
                        email=email if email else None,
                        display_name=display_name if display_name != username else None
                    )
                    
                    # Set authentication state
                    self._set_authenticated_user(user)
                    
                    self.console.print(f"[white]✓ Registration successful! Welcome, {user.display_name or user.username}[/white]")
                    return True
                
                except ValueError as e:
                    self.console.print(f"[bright_red]✗ {e}[/bright_red]")
                    return False
        
        except SQLAlchemyError as e:
            self.console.print(f"[bright_red]✗ Database error: {e}[/bright_red]")
            return False
        except Exception as e:
            self.console.print(f"[bright_red]✗ Registration failed: {e}[/bright_red]")
            return False
    
    def _validate_email(self, email: str) -> bool:
        """Simple email validation"""
        import re
        pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        return re.match(pattern, email) is not None
    
    def _set_authenticated_user(self, user: User):
        """Set authenticated user and create JWT token"""
        self.current_user = user.to_dict()
        self.access_token = self._create_access_token(user.id, user.username)
        
        # Save session for restoration
        self._save_session()
    
    def _create_access_token(self, user_id: int, username: str) -> str:
        """Create JWT access token"""
        now = datetime.utcnow()
        expire = now + timedelta(hours=self.jwt_expire_hours)
        
        payload = {
            'sub': str(user_id),
            'username': username,
            'iat': now,
            'exp': expire,
            'type': 'access'
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def _verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.JWTError:
            raise AuthenticationError("Invalid token")
    
    def _save_session(self):
        """Save current session to file"""
        if not self.current_user or not self.access_token:
            return
        
        session_file = self.config.app_dir / '.session'
        session_data = {
            'user': self.current_user,
            'token': self.access_token,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            import json
            with open(session_file, 'w') as f:
                json.dump(session_data, f)
            session_file.chmod(0o600)  # Read-write for owner only
        except IOError:
            # Fail silently if we can't save session
            pass
    
    def _try_restore_session(self) -> bool:
        """Try to restore previous session"""
        session_file = self.config.app_dir / '.session'
        
        if not session_file.exists():
            return False
        
        try:
            import json
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            token = session_data.get('token')
            if not token:
                return False
            
            # Verify token is still valid
            payload = self._verify_token(token)
            user_id = int(payload.get('sub'))
            
            # Get fresh user data from database
            with self.database.get_session() as db_session:
                user = db_session.query(User).filter(User.id == user_id).first()
                if not user or not user.is_active:
                    self._clear_session()
                    return False
                
                # Update last active
                user.last_active = datetime.utcnow()
                db_session.commit()
                
                # Restore authentication state
                self.current_user = user.to_dict()
                self.access_token = token
                
                self.console.print(f"[white]✓ Welcome back, {user.display_name or user.username}[/white]")
                return True
        
        except (json.JSONDecodeError, AuthenticationError, ValueError, SQLAlchemyError):
            # Clear invalid session
            self._clear_session()
            return False
        except IOError:
            return False
    
    def _clear_session(self):
        """Clear saved session"""
        session_file = self.config.app_dir / '.session'
        try:
            session_file.unlink(missing_ok=True)
        except IOError:
            pass
        
        self.current_user = None
        self.access_token = None
    
    def logout(self):
        """Logout current user"""
        if self.current_user:
            username = self.current_user.get('display_name') or self.current_user.get('username')
            self.console.print(f"[white]Goodbye, {username}.[/white]")
        
        self._clear_session()
    
    def show_profile(self):
        """Display user profile information"""
        if not self.current_user:
            self.console.print("[bright_red]✗ Not authenticated[/bright_red]")
            return
        
        user = self.current_user
        
        # Create profile table
        table = Table(show_header=False, box=None, border_style="white")
        table.add_column("Field", style="white", width=15)
        table.add_column("Value", style="white")
        
        table.add_row("Username", user.get('username', 'N/A'))
        table.add_row("Display Name", user.get('display_name', 'N/A'))
        table.add_row("Email", user.get('email', 'Not provided'))
        table.add_row("Created", user.get('created_at', 'N/A')[:10] if user.get('created_at') else 'N/A')
        table.add_row("Last Login", user.get('last_login', 'N/A')[:10] if user.get('last_login') else 'N/A')
        
        panel = Panel.fit(
            table,
            title="[white]USER PROFILE[/white]",
            border_style="white",
            padding=(1, 2)
        )
        self.console.print(panel)
        self.console.print()
    
    def change_password(self):
        """Change user password"""
        if not self.current_user:
            self.console.print("[bright_red]✗ Not authenticated[/bright_red]")
            return False
        
        self.console.print("\n[white]CHANGE PASSWORD[/white]")
        self.console.print()
        
        try:
            # Current password verification
            current_password = Prompt.ask("Current password", password=True, show_default=False, console=self.console)
            if not current_password:
                self.console.print("[bright_red]✗ Current password cannot be empty[/bright_red]")
                return False
            
            # New password
            while True:
                new_password = Prompt.ask("New password (minimum 6 characters)", password=True, show_default=False, console=self.console)
                if not new_password:
                    self.console.print("[bright_red]✗ Password cannot be empty[/bright_red]")
                    continue
                if len(new_password) < 6:
                    self.console.print("[bright_red]✗ Password must be at least 6 characters[/bright_red]")
                    continue
                
                # Confirm new password
                password_confirm = Prompt.ask("Confirm new password", password=True, show_default=False, console=self.console)
                if new_password != password_confirm:
                    self.console.print("[bright_red]✗ Passwords do not match[/bright_red]")
                    continue
                break
            
            # Update password in database
            with self.database.get_session() as session:
                user = session.query(User).filter(User.id == self.current_user['id']).first()
                if not user or not user.check_password(current_password):
                    self.console.print("[bright_red]✗ Current password is incorrect[/bright_red]")
                    return False
                
                user.set_password(new_password)
                session.commit()
                
                self.console.print("[white]✓ Password changed successfully[/white]")
                return True
        
        except SQLAlchemyError as e:
            self.console.print(f"[bright_red]✗ Database error: {e}[/bright_red]")
            return False
        except Exception as e:
            self.console.print(f"[bright_red]✗ Password change failed: {e}[/bright_red]")
            return False

# Global authentication instance
_auth = None

def get_auth() -> TerminalAuth:
    """Get global authentication instance"""
    global _auth
    if _auth is None:
        _auth = TerminalAuth()
    return _auth