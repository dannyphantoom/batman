"""
Configuration management for Batman package manager
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

class BatmanConfig:
    """Configuration management class"""
    
    def __init__(self):
        self.config_dir = Path.home() / '.batman'
        self.config_file = self.config_dir / 'config.json'
        self.packages_db = self.config_dir / 'packages.json'
        self.cache_dir = self.config_dir / 'cache'
        
        # Default configuration
        self.default_config = {
            'package_managers': {
                'pip': {
                    'enabled': True,
                    'install_dir': str(Path.home() / '.batman' / 'packages' / 'python'),
                    'auto_detect_files': ['requirements.txt', 'pyproject.toml', 'setup.py']
                },
                'npm': {
                    'enabled': True,
                    'install_dir': str(Path.home() / '.batman' / 'packages' / 'node'),
                    'auto_detect_files': ['package.json', 'package-lock.json']
                },
                'cargo': {
                    'enabled': True,
                    'install_dir': str(Path.home() / '.batman' / 'packages' / 'rust'),
                    'auto_detect_files': ['Cargo.toml', 'Cargo.lock']
                },
                'apt': {
                    'enabled': True,
                    'install_dir': '/usr/local',
                    'auto_detect_files': []
                },
                'pacman': {
                    'enabled': True,
                    'install_dir': '/usr/local',
                    'auto_detect_files': []
                }
            },
            'global_settings': {
                'auto_update_check': True,
                'update_interval_days': 7,
                'parallel_downloads': True,
                'max_parallel_jobs': 4,
                'backup_before_update': True,
                'log_level': 'INFO'
            }
        }
        
        self._ensure_config_exists()
        self.config = self._load_config()
    
    def _ensure_config_exists(self):
        """Ensure configuration directory and files exist"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create packages directories
        for manager_config in self.default_config['package_managers'].values():
            install_dir = Path(manager_config['install_dir'])
            if str(install_dir).startswith(str(Path.home())):
                install_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.config_file.exists():
            self._save_config(self.default_config)
        
        if not self.packages_db.exists():
            self._save_packages_db({})
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            # Merge with defaults for any missing keys
            return self._merge_configs(self.default_config, config)
        except (json.JSONDecodeError, FileNotFoundError):
            return self.default_config.copy()
    
    def _merge_configs(self, default: Dict, user: Dict) -> Dict:
        """Recursively merge user config with defaults"""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result
    
    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _save_packages_db(self, packages: Dict[str, Any]):
        """Save packages database to file"""
        with open(self.packages_db, 'w') as f:
            json.dump(packages, f, indent=2)
    
    def get(self, key_path: str, default=None):
        """Get configuration value using dot notation (e.g., 'package_managers.pip.enabled')"""
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, key_path: str, value):
        """Set configuration value using dot notation"""
        keys = key_path.split('.')
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
        self._save_config(self.config)
    
    def get_manager_config(self, manager_name: str) -> Dict[str, Any]:
        """Get configuration for a specific package manager"""
        return self.config['package_managers'].get(manager_name, {})
    
    def is_manager_enabled(self, manager_name: str) -> bool:
        """Check if a package manager is enabled"""
        return self.get_manager_config(manager_name).get('enabled', False)

def load_config() -> BatmanConfig:
    """Load and return Batman configuration"""
    return BatmanConfig() 