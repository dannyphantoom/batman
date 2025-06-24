"""
Base package manager class for Batman package manager
"""

import subprocess
import shutil
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path

class PackageManagerBase(ABC):
    """Abstract base class for all package managers"""
    
    def __init__(self, config: Dict[str, Any], logger):
        self.config = config
        self.logger = logger
        self.name = self.__class__.__name__.lower().replace('manager', '')
        self.enabled = config.get('enabled', True)
        self.install_dir = Path(config.get('install_dir', '/tmp'))
        self.auto_detect_files = config.get('auto_detect_files', [])
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this package manager is available on the system"""
        pass
    
    @abstractmethod
    def install(self, package_name: str, version: Optional[str] = None, **kwargs) -> bool:
        """Install a package"""
        pass
    
    @abstractmethod
    def update(self, package_name: str, **kwargs) -> bool:
        """Update a package"""
        pass
    
    @abstractmethod
    def remove(self, package_name: str, **kwargs) -> bool:
        """Remove a package"""
        pass
    
    @abstractmethod
    def search(self, query: str, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """Search for packages"""
        pass
    
    @abstractmethod
    def list_installed(self, **kwargs) -> List[Dict[str, Any]]:
        """List installed packages"""
        pass
    
    @abstractmethod
    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a package"""
        pass
    
    @abstractmethod
    def is_installed(self, package_name: str) -> bool:
        """Check if a package is installed"""
        pass
    
    @abstractmethod
    def get_version(self, package_name: str) -> Optional[str]:
        """Get installed version of a package"""
        pass
    
    def run_command(self, command: List[str], capture_output: bool = True, 
                   check: bool = True, **kwargs) -> subprocess.CompletedProcess:
        """Run a shell command and return the result"""
        try:
            self.logger.debug(f"Running command: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                check=check,
                **kwargs
            )
            
            if result.stdout:
                self.logger.debug(f"Command output: {result.stdout.strip()}")
            if result.stderr:
                self.logger.debug(f"Command error: {result.stderr.strip()}")
                
            return result
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {' '.join(command)}")
            self.logger.error(f"Exit code: {e.returncode}")
            if e.stdout:
                self.logger.error(f"Stdout: {e.stdout}")
            if e.stderr:
                self.logger.error(f"Stderr: {e.stderr}")
            raise
    
    def check_command_exists(self, command: str) -> bool:
        """Check if a command exists in the system PATH"""
        return shutil.which(command) is not None
    
    def auto_detect_project_type(self, directory: Path = None) -> bool:
        """Auto-detect if this manager should be used based on project files"""
        if not self.auto_detect_files:
            return False
        
        search_dir = directory or Path.cwd()
        for file_pattern in self.auto_detect_files:
            if list(search_dir.glob(file_pattern)):
                self.logger.debug(f"Auto-detected {self.name} project in {search_dir}")
                return True
        
        return False
    
    def normalize_package_name(self, name: str) -> str:
        """Normalize package name for this manager"""
        return name.strip().lower()
    
    def parse_package_spec(self, package_spec: str) -> Tuple[str, Optional[str]]:
        """Parse package specification into name and version"""
        if '==' in package_spec:
            name, version = package_spec.split('==', 1)
            return name.strip(), version.strip()
        elif '=' in package_spec:
            name, version = package_spec.split('=', 1)
            return name.strip(), version.strip()
        elif '@' in package_spec:
            name, version = package_spec.split('@', 1)
            return name.strip(), version.strip()
        else:
            return package_spec.strip(), None
    
    def format_package_list(self, packages: List[Dict[str, Any]]) -> str:
        """Format package list for display"""
        if not packages:
            return "No packages found."
        
        lines = []
        for pkg in packages:
            name = pkg.get('name', 'Unknown')
            version = pkg.get('version', 'Unknown')
            description = pkg.get('description', '')
            
            line = f"{name} ({version})"
            if description:
                line += f" - {description[:80]}..."
            lines.append(line)
        
        return '\n'.join(lines)
    
    def backup_before_operation(self, operation: str, package_name: str) -> Optional[Path]:
        """Create backup before potentially destructive operation"""
        if not self.config.get('backup_before_update', False):
            return None
        
        try:
            backup_dir = Path.home() / '.batman' / 'backups' / self.name
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = subprocess.run(
                ['date', '+%Y%m%d_%H%M%S'],
                capture_output=True,
                text=True
            ).stdout.strip()
            
            backup_file = backup_dir / f"{package_name}_{operation}_{timestamp}.backup"
            
            # This is a placeholder - specific managers would implement actual backup logic
            with open(backup_file, 'w') as f:
                f.write(f"Backup for {operation} of {package_name} at {timestamp}\n")
            
            self.logger.info(f"Created backup: {backup_file}")
            return backup_file
            
        except Exception as e:
            self.logger.warning(f"Failed to create backup: {e}")
            return None
    
    def validate_package_name(self, package_name: str) -> bool:
        """Validate package name format"""
        if not package_name or not package_name.strip():
            return False
        
        # Basic validation - can be overridden by specific managers
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        return not any(char in package_name for char in invalid_chars)
    
    def get_install_path(self, package_name: str) -> Path:
        """Get the installation path for a package"""
        return self.install_dir / package_name
    
    def cleanup_failed_install(self, package_name: str):
        """Clean up after a failed installation"""
        install_path = self.get_install_path(package_name)
        if install_path.exists():
            try:
                shutil.rmtree(install_path)
                self.logger.debug(f"Cleaned up failed installation at {install_path}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup {install_path}: {e}")
    
    def __str__(self) -> str:
        return f"{self.name.title()} Package Manager"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(enabled={self.enabled})>" 