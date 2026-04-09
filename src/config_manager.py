"""Configuration manager for persistent user settings.

Handles saving and loading user preferences across sessions with cross-platform
support and graceful error handling.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """Manages persistent configuration for the application.

    Stores user preferences like last used files, directories, and UI settings
    in a JSON file in the user's config directory.
    """

    DEFAULT_CONFIG = {
        "last_input_file": "",
        "last_output_dir": "",
        "organization_option": "none",
        "generate_positive_summary": True,
        "window_geometry": {
            "width": 1000,
            "height": 700,
            "x": None,
            "y": None
        },
        "recent_input_files": [],
        "recent_output_dirs": [],
        "max_recent_items": 10,
        "show_welcome": True,
        # Email settings
        "email_enabled": False,
        "email_smtp_server": "",
        "email_smtp_port": 587,
        "email_username": "",
        "email_password": "",
        "email_recipient": "",
        "email_use_tls": True,
        # Google Drive settings
        "gdrive_enabled": False,
        "gdrive_service_account_file": "",
        "gdrive_folder_id": "",
        "gdrive_share_emails": [],
        # ZIP archive settings
        "create_zip": True,
        # Search settings
        "search_reports_directory": ""
    }

    def __init__(self, app_name: str = "clia-report-generator"):
        """Initialize the configuration manager.

        Args:
            app_name: Application name for config directory (default: "clia-report-generator")
        """
        self.app_name = app_name
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.json"
        self._config = None

    def _get_config_dir(self) -> Path:
        """Get cross-platform configuration directory path.

        Returns:
            Path to configuration directory
        """
        if os.name == 'nt':  # Windows
            config_base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        elif os.name == 'posix':
            if os.uname().sysname == 'Darwin':  # macOS
                config_base = Path.home() / 'Library' / 'Application Support'
            else:  # Linux and other UNIX-like systems
                config_base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
        else:
            # Fallback for unknown systems
            config_base = Path.home() / '.config'

        return config_base / self.app_name

    def ensure_config_dir(self) -> bool:
        """Ensure configuration directory exists.

        Returns:
            True if directory exists or was created successfully, False otherwise
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            return True
        except (OSError, PermissionError) as e:
            print(f"Warning: Could not create config directory {self.config_dir}: {e}")
            return False

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file.

        Returns:
            Configuration dictionary. Returns defaults if file doesn't exist or is corrupted.
        """
        if self._config is not None:
            return self._config

        # Start with defaults
        config = self.DEFAULT_CONFIG.copy()

        # Try to load from file
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge loaded config with defaults (preserves new defaults if added)
                    config.update(loaded_config)
            except (json.JSONDecodeError, OSError, PermissionError) as e:
                print(f"Warning: Could not load config file {self.config_file}: {e}")
                print("Using default configuration.")

        # Validate and clean config
        config = self._validate_config(config)
        self._config = config
        return config

    def save_config(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Save configuration to file.

        Args:
            config: Configuration dictionary to save. If None, saves current config.

        Returns:
            True if saved successfully, False otherwise
        """
        if config is not None:
            self._config = config
        elif self._config is None:
            # Nothing to save
            return False

        if not self.ensure_config_dir():
            return False

        try:
            # Atomic write: write to temp file then rename
            temp_file = self.config_file.with_suffix('.json.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)

            # Rename temp file to actual config file (atomic on most systems)
            temp_file.replace(self.config_file)
            return True

        except (OSError, PermissionError) as e:
            print(f"Warning: Could not save config file {self.config_file}: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        config = self.load_config()
        return config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value.

        Args:
            key: Configuration key
            value: Value to set
        """
        config = self.load_config()
        config[key] = value
        self._config = config

    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple configuration values.

        Args:
            updates: Dictionary of key-value pairs to update
        """
        config = self.load_config()
        config.update(updates)
        self._config = config

    def reset_to_defaults(self) -> Dict[str, Any]:
        """Reset configuration to defaults.

        Returns:
            Default configuration dictionary
        """
        self._config = self.DEFAULT_CONFIG.copy()
        return self._config

    def add_recent_file(self, file_path: str) -> None:
        """Add file to recent files list.

        Args:
            file_path: Path to add to recent files
        """
        config = self.load_config()
        recent = config.get("recent_input_files", [])

        # Remove if already exists (to move it to top)
        if file_path in recent:
            recent.remove(file_path)

        # Add to beginning
        recent.insert(0, file_path)

        # Trim to max items
        max_items = config.get("max_recent_items", 10)
        config["recent_input_files"] = recent[:max_items]
        self._config = config

    def add_recent_dir(self, dir_path: str) -> None:
        """Add directory to recent directories list.

        Args:
            dir_path: Path to add to recent directories
        """
        config = self.load_config()
        recent = config.get("recent_output_dirs", [])

        # Remove if already exists (to move it to top)
        if dir_path in recent:
            recent.remove(dir_path)

        # Add to beginning
        recent.insert(0, dir_path)

        # Trim to max items
        max_items = config.get("max_recent_items", 10)
        config["recent_output_dirs"] = recent[:max_items]
        self._config = config

    def get_recent_files(self) -> list:
        """Get list of recent input files.

        Returns:
            List of recent file paths (only existing files)
        """
        config = self.load_config()
        recent = config.get("recent_input_files", [])
        # Filter to only existing files
        return [f for f in recent if os.path.exists(f)]

    def get_recent_dirs(self) -> list:
        """Get list of recent output directories.

        Returns:
            List of recent directory paths (only existing directories)
        """
        config = self.load_config()
        recent = config.get("recent_output_dirs", [])
        # Filter to only existing directories
        return [d for d in recent if os.path.isdir(d)]

    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            Validated configuration dictionary
        """
        # Ensure all default keys exist
        for key, value in self.DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value

        # Validate organization option
        valid_org_options = ["none", "collection-date", "tested-date", "mrn"]
        if config.get("organization_option") not in valid_org_options:
            config["organization_option"] = "none"

        # Validate boolean values
        if not isinstance(config.get("generate_positive_summary"), bool):
            config["generate_positive_summary"] = True

        if not isinstance(config.get("show_welcome"), bool):
            config["show_welcome"] = True

        # Validate window geometry
        if not isinstance(config.get("window_geometry"), dict):
            config["window_geometry"] = self.DEFAULT_CONFIG["window_geometry"].copy()

        # Validate recent lists
        if not isinstance(config.get("recent_input_files"), list):
            config["recent_input_files"] = []

        if not isinstance(config.get("recent_output_dirs"), list):
            config["recent_output_dirs"] = []

        # Clean up invalid paths from recent files
        config["recent_input_files"] = [f for f in config["recent_input_files"]
                                        if isinstance(f, str)]
        config["recent_output_dirs"] = [d for d in config["recent_output_dirs"]
                                        if isinstance(d, str)]

        # Validate email settings
        if not isinstance(config.get("email_enabled"), bool):
            config["email_enabled"] = False
        if not isinstance(config.get("email_smtp_port"), int):
            try:
                config["email_smtp_port"] = int(config.get("email_smtp_port", 587))
            except (ValueError, TypeError):
                config["email_smtp_port"] = 587
        if not isinstance(config.get("email_use_tls"), bool):
            config["email_use_tls"] = True

        # Validate ZIP settings
        if not isinstance(config.get("create_zip"), bool):
            config["create_zip"] = True

        # Validate Google Drive settings
        if not isinstance(config.get("gdrive_enabled"), bool):
            config["gdrive_enabled"] = False
        if not isinstance(config.get("gdrive_share_emails"), list):
            config["gdrive_share_emails"] = []
        # Clean up invalid entries in share emails
        config["gdrive_share_emails"] = [e for e in config["gdrive_share_emails"]
                                         if isinstance(e, str) and e.strip()]

        return config

    def get_config_path(self) -> Path:
        """Get path to configuration file.

        Returns:
            Path to configuration file
        """
        return self.config_file
