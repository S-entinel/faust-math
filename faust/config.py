
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

class Config:
    """Configuration manager for Faust application"""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Set up paths
        self.home_dir = Path.home()
        self.app_dir = self.home_dir / '.faust'
        self.config_file = self.app_dir / 'config.json'
        self.database_file = self.app_dir / 'faust.db'
        self.log_file = self.app_dir / 'faust.log'
        
        # Ensure app directory exists
        self.app_dir.mkdir(exist_ok=True)
        
        # Load configuration
        self.settings = self._load_config()
        
        # Environment variables with defaults
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.jwt_secret_key = self._get_or_create_jwt_secret()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        default_config = {
            'theme': 'dark',
            'auto_save': True,
            'math_display': 'unicode',  # 'unicode', 'latex', or 'both'
            'session_timeout': 3600,  # 1 hour in seconds
            'max_history': 100,
            'log_level': 'INFO'
        }
        
        if not self.config_file.exists():
            self._save_config(default_config)
            return default_config
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                # Merge with defaults (in case new settings were added)
                return {**default_config, **config}
        except (json.JSONDecodeError, IOError):
            # If config is corrupted, use defaults
            return default_config
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except IOError:
            # Fail silently if we can't save config
            pass
    
    def _get_or_create_jwt_secret(self) -> str:
        """Get JWT secret key or create a new one"""
        secret_file = self.app_dir / '.jwt_secret'
        
        if secret_file.exists():
            try:
                return secret_file.read_text().strip()
            except IOError:
                pass
        
        # Generate new secret
        import secrets
        secret = secrets.token_urlsafe(32)
        
        try:
            secret_file.write_text(secret)
            secret_file.chmod(0o600)  # Read-write for owner only
        except IOError:
            pass
        
        return secret
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        self.settings[key] = value
        self._save_config(self.settings)
    
    def get_database_url(self) -> str:
        """Get SQLite database URL"""
        return f"sqlite:///{self.database_file}"
    
    def validate_google_api_key(self) -> bool:
        """Check if Google API key is configured"""
        return bool(self.google_api_key and self.google_api_key.strip())
    
    def prompt_for_api_key(self) -> Optional[str]:
        """Prompt user for Google API key"""
        from rich.console import Console
        from rich.prompt import Prompt
        
        console = Console()
        
        console.print("\n[bold red]⚠️  Google API Key Required[/bold red]")
        console.print(
            "Faust requires a Google API key to access Gemini AI.\n"
            "Get your free API key at: [link]https://makersuite.google.com/app/apikey[/link]\n"
        )
        
        api_key = Prompt.ask(
            "Enter your Google API key",
            password=True,
            show_default=False
        )
        
        if api_key and api_key.strip():
            # Save to environment file
            env_file = self.app_dir / '.env'
            try:
                with open(env_file, 'a') as f:
                    f.write(f"\nGOOGLE_API_KEY={api_key.strip()}\n")
                
                self.google_api_key = api_key.strip()
                console.print("[green]✅ API key saved successfully![/green]")
                return self.google_api_key
            except IOError:
                console.print("[red]❌ Failed to save API key[/red]")
        
        return None

# Global configuration instance
_config = None

def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = Config()
    return _config