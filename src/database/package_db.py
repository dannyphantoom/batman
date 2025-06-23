"""
Package database management for Batman package manager
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class PackageInfo:
    """Information about an installed package"""
    name: str
    version: str
    manager: str
    install_date: str
    install_path: str
    dependencies: List[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PackageInfo':
        """Create from dictionary"""
        return cls(**data)

class PackageDatabase:
    """Manages the local package database"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.packages = self._load_packages()
    
    def _load_packages(self) -> Dict[str, PackageInfo]:
        """Load packages from database file"""
        if not self.db_path.exists():
            return {}
        
        try:
            with open(self.db_path, 'r') as f:
                data = json.load(f)
            
            packages = {}
            for pkg_key, pkg_data in data.items():
                packages[pkg_key] = PackageInfo.from_dict(pkg_data)
            
            return packages
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not load package database: {e}")
            return {}
    
    def _save_packages(self):
        """Save packages to database file"""
        data = {}
        for pkg_key, pkg_info in self.packages.items():
            data[pkg_key] = pkg_info.to_dict()
        
        with open(self.db_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _get_package_key(self, name: str, manager: str) -> str:
        """Generate unique key for package"""
        return f"{manager}:{name}"
    
    def add_package(self, package_info: PackageInfo):
        """Add or update package in database"""
        key = self._get_package_key(package_info.name, package_info.manager)
        self.packages[key] = package_info
        self._save_packages()
    
    def remove_package(self, name: str, manager: str):
        """Remove package from database"""
        key = self._get_package_key(name, manager)
        if key in self.packages:
            del self.packages[key]
            self._save_packages()
    
    def get_package(self, name: str, manager: str) -> Optional[PackageInfo]:
        """Get package information"""
        key = self._get_package_key(name, manager)
        return self.packages.get(key)
    
    def is_installed(self, name: str, manager: str) -> bool:
        """Check if package is installed"""
        return self.get_package(name, manager) is not None
    
    def list_packages(self, manager: Optional[str] = None) -> List[PackageInfo]:
        """List all packages, optionally filtered by manager"""
        packages = list(self.packages.values())
        if manager:
            packages = [pkg for pkg in packages if pkg.manager == manager]
        return sorted(packages, key=lambda x: (x.manager, x.name))
    
    def get_packages_by_manager(self, manager: str) -> List[PackageInfo]:
        """Get all packages for a specific manager"""
        return [pkg for pkg in self.packages.values() if pkg.manager == manager]
    
    def search_packages(self, query: str, manager: Optional[str] = None) -> List[PackageInfo]:
        """Search for packages by name or description"""
        query_lower = query.lower()
        results = []
        
        for pkg in self.packages.values():
            if manager and pkg.manager != manager:
                continue
            
            # Search in name, metadata description, etc.
            if (query_lower in pkg.name.lower() or 
                query_lower in pkg.metadata.get('description', '').lower() or
                query_lower in pkg.metadata.get('keywords', [])):
                results.append(pkg)
        
        return sorted(results, key=lambda x: x.name)
    
    def get_outdated_packages(self) -> List[PackageInfo]:
        """Get packages that might need updates (placeholder for future implementation)"""
        # This would require checking against remote repositories
        # For now, return packages older than 30 days as potentially outdated
        thirty_days_ago = time.time() - (30 * 24 * 60 * 60)
        outdated = []
        
        for pkg in self.packages.values():
            try:
                install_time = time.mktime(time.strptime(pkg.install_date, "%Y-%m-%d %H:%M:%S"))
                if install_time < thirty_days_ago:
                    outdated.append(pkg)
            except ValueError:
                # If we can't parse the date, consider it potentially outdated
                outdated.append(pkg)
        
        return outdated
    
    def update_package_info(self, name: str, manager: str, **kwargs):
        """Update specific fields of a package"""
        package = self.get_package(name, manager)
        if package:
            for key, value in kwargs.items():
                if hasattr(package, key):
                    setattr(package, key, value)
            self._save_packages()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {
            'total_packages': len(self.packages),
            'by_manager': {},
            'install_dates': [],
            'total_size_estimate': 0  # Could be calculated if we track sizes
        }
        
        for pkg in self.packages.values():
            manager = pkg.manager
            if manager not in stats['by_manager']:
                stats['by_manager'][manager] = 0
            stats['by_manager'][manager] += 1
            stats['install_dates'].append(pkg.install_date)
        
        return stats
    
    def backup_database(self, backup_path: Optional[Path] = None):
        """Create a backup of the package database"""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.db_path.parent / f"packages_backup_{timestamp}.json"
        
        data = {}
        for pkg_key, pkg_info in self.packages.items():
            data[pkg_key] = pkg_info.to_dict()
        
        with open(backup_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        return backup_path
    
    def restore_database(self, backup_path: Path):
        """Restore database from backup"""
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        with open(backup_path, 'r') as f:
            data = json.load(f)
        
        packages = {}
        for pkg_key, pkg_data in data.items():
            packages[pkg_key] = PackageInfo.from_dict(pkg_data)
        
        self.packages = packages
        self._save_packages() 