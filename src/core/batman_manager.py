"""
Main Batman package manager that orchestrates all individual package managers
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from ..database.package_db import PackageDatabase, PackageInfo
from ..managers.pip_manager import PipManager
from ..managers.npm_manager import NpmManager
from ..managers.apt_manager import AptManager
from ..managers.pacman_manager import PacmanManager
from ..managers.cargo_manager import CargoManager
from ..utils.logger import BatmanLogger

class BatmanManager:
    """Main Batman package manager class"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        
        # Initialize package database
        db_path = Path.home() / '.batman' / 'packages.json'
        self.package_db = PackageDatabase(db_path)
        
        # Initialize package managers
        self.managers = {}
        self._initialize_managers()
        
        # Auto-detection order (priority)
        self.auto_detect_order = ['cargo', 'pip', 'npm', 'pacman', 'apt']
    
    def _initialize_managers(self):
        """Initialize all available package managers"""
        manager_classes = {
            'pip': PipManager,
            'npm': NpmManager,
            'apt': AptManager,
            'pacman': PacmanManager,
            'cargo': CargoManager,
        }
        
        for manager_name, manager_class in manager_classes.items():
            manager_config = self.config.get_manager_config(manager_name)
            
            if manager_config.get('enabled', True):
                try:
                    manager = manager_class(manager_config, self.logger)
                    if manager.is_available():
                        self.managers[manager_name] = manager
                        self.logger.debug(f"Initialized {manager_name} manager")
                    else:
                        self.logger.debug(f"{manager_name} manager not available on system")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize {manager_name} manager: {e}")
    
    def _auto_detect_manager(self, package_name: str, directory: Path = None) -> Optional[str]:
        """Auto-detect the appropriate package manager"""
        search_dir = directory or Path.cwd()
        
        # First, try project-based detection
        for manager_name in self.auto_detect_order:
            if manager_name in self.managers:
                manager = self.managers[manager_name]
                if manager.auto_detect_project_type(search_dir):
                    self.logger.debug(f"Auto-detected {manager_name} for {package_name}")
                    return manager_name
        
        # Fallback to pip as default for most cases
        if 'pip' in self.managers:
            return 'pip'
        
        # If pip not available, return first available manager
        if self.managers:
            return list(self.managers.keys())[0]
        
        return None
    
    def _resolve_manager(self, manager_hint: str, package_name: str) -> Optional[str]:
        """Resolve the actual manager to use"""
        if manager_hint == 'auto':
            return self._auto_detect_manager(package_name)
        
        if manager_hint in self.managers:
            return manager_hint
        
        # If specified manager not available, try auto-detection
        self.logger.warning(f"Manager '{manager_hint}' not available, auto-detecting...")
        return self._auto_detect_manager(package_name)
    
    def install_package(self, package_name: str, manager_hint: str = 'auto', 
                       version: Optional[str] = None, force: bool = False, dry_run: bool = False) -> bool:
        """Install a package using the appropriate manager"""
        try:
            # Resolve manager
            manager_name = self._resolve_manager(manager_hint, package_name)
            if not manager_name:
                self.logger.error(f"No suitable package manager found for {package_name}")
                return False
            
            manager = self.managers[manager_name]
            
            # Parse package specification
            name, parsed_version = manager.parse_package_spec(package_name)
            
            # Use explicit version if provided, otherwise use parsed version
            target_version = version or parsed_version
            
            # Check if already installed
            if not force and self.package_db.is_installed(name, manager_name):
                current_version = self.package_db.get_package(name, manager_name).version
                self.logger.info(f"Package {name} already installed (version {current_version})")
                if not force:
                    return True
            
            if dry_run:
                version_info = f" (version {target_version})" if target_version else ""
                self.logger.dry_run(f"Install {name}{version_info} using {manager_name}")
                return True
            
            # Perform installation
            self.logger.command_start("install", name, manager_name)
            
            success = manager.install(name, target_version)
            
            if success:
                # Update package database
                install_path = manager.get_install_path(name)
                package_info = PackageInfo(
                    name=name,
                    version=target_version or manager.get_version(name) or 'unknown',
                    manager=manager_name,
                    install_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    install_path=str(install_path),
                    dependencies=[],
                    metadata={}
                )
                
                # Get additional package info
                detailed_info = manager.get_package_info(name)
                if detailed_info:
                    package_info.dependencies = detailed_info.get('dependencies', [])
                    package_info.metadata = {
                        'description': detailed_info.get('description', ''),
                        'author': detailed_info.get('author', ''),
                        'homepage': detailed_info.get('homepage', ''),
                    }
                
                self.package_db.add_package(package_info)
                self.logger.command_success("install", name, f"Installed with {manager_name}")
                return True
            else:
                manager.cleanup_failed_install(name)
                return False
                
        except Exception as e:
            self.logger.command_error("install", str(e), package_name)
            return False
    
    def update_package(self, package_name: str, manager_hint: str = 'auto',
                      force: bool = False, dry_run: bool = False) -> bool:
        """Update a specific package"""
        try:
            # Check if package is installed
            for manager_name in self.managers.keys():
                if self.package_db.is_installed(package_name, manager_name):
                    manager = self.managers[manager_name]
                    
                    if dry_run:
                        self.logger.dry_run(f"Update {package_name} using {manager_name}")
                        return True
                    
                    self.logger.command_start("update", package_name, manager_name)
                    
                    success = manager.update(package_name)
                    
                    if success:
                        # Update package database
                        new_version = manager.get_version(package_name)
                        if new_version:
                            self.package_db.update_package_info(
                                package_name, manager_name,
                                version=new_version,
                                install_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            )
                        
                        self.logger.command_success("update", package_name)
                        return True
                    else:
                        return False
            
            # Package not found in database, try to install it
            self.logger.info(f"Package {package_name} not found in database, attempting to install...")
            return self.install_package(package_name, manager_hint, force, dry_run)
            
        except Exception as e:
            self.logger.command_error("update", str(e), package_name)
            return False
    
    def update_all_packages(self, force: bool = False, dry_run: bool = False) -> List[str]:
        """Update all installed packages"""
        updated_packages = []
        
        try:
            if dry_run:
                self.logger.dry_run("Update all packages")
                return ["dry-run-complete"]
            
            self.logger.info("🔄 Starting update of all packages...")
            
            # Get packages by manager and update them
            for manager_name, manager in self.managers.items():
                self.logger.info(f"Updating {manager_name} packages...")
                
                try:
                    if hasattr(manager, 'update_all'):
                        # Use manager's bulk update if available
                        manager_updated = manager.update_all()
                        updated_packages.extend([f"{pkg}:{manager_name}" for pkg in manager_updated])
                    else:
                        # Update packages individually
                        db_packages = self.package_db.get_packages_by_manager(manager_name)
                        for package in db_packages:
                            if manager.update(package.name):
                                updated_packages.append(f"{package.name}:{manager_name}")
                                
                                # Update database
                                new_version = manager.get_version(package.name)
                                if new_version:
                                    self.package_db.update_package_info(
                                        package.name, manager_name,
                                        version=new_version,
                                        install_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    )
                
                except Exception as e:
                    self.logger.error(f"Failed to update {manager_name} packages: {e}")
            
            if updated_packages:
                self.logger.command_success("update all packages", 
                                          details=f"Updated {len(updated_packages)} packages")
            else:
                self.logger.info("All packages are already up to date")
            
            return updated_packages
            
        except Exception as e:
            self.logger.command_error("update all packages", str(e))
            return []
    
    def remove_package(self, package_name: str, manager_hint: str = 'auto',
                      force: bool = False, dry_run: bool = False) -> bool:
        """Remove a package"""
        try:
            # Find which manager installed this package
            for manager_name in self.managers.keys():
                if self.package_db.is_installed(package_name, manager_name):
                    manager = self.managers[manager_name]
                    
                    if dry_run:
                        self.logger.dry_run(f"Remove {package_name} using {manager_name}")
                        return True
                    
                    self.logger.command_start("remove", package_name, manager_name)
                    
                    success = manager.remove(package_name)
                    
                    if success:
                        # Remove from database
                        self.package_db.remove_package(package_name, manager_name)
                        self.logger.command_success("remove", package_name)
                        return True
                    else:
                        return False
            
            self.logger.error(f"Package {package_name} not found")
            return False
            
        except Exception as e:
            self.logger.command_error("remove", str(e), package_name)
            return False
    
    def search_packages(self, query: str, manager_hint: str = 'auto') -> None:
        """Search for packages across all managers"""
        try:
            self.logger.info(f"🔍 Searching for '{query}'...")
            
            if manager_hint != 'auto' and manager_hint in self.managers:
                # Search in specific manager
                managers_to_search = [manager_hint]
            else:
                # Search in all available managers
                managers_to_search = list(self.managers.keys())
            
            all_results = []
            
            for manager_name in managers_to_search:
                manager = self.managers[manager_name]
                try:
                    results = manager.search(query)
                    if results:
                        self.logger.info(f"\n📦 Results from {manager_name.upper()}:")
                        for pkg in results[:5]:  # Limit to top 5 results per manager
                            name = pkg.get('name', 'Unknown')
                            version = pkg.get('version', 'Unknown')
                            description = pkg.get('description', '')
                            
                            self.logger.info(f"  {name} ({version})")
                            if description:
                                self.logger.info(f"    {description[:100]}...")
                        
                        all_results.extend(results)
                        
                except Exception as e:
                    self.logger.warning(f"Search failed in {manager_name}: {e}")
            
            if not all_results:
                self.logger.info("No packages found matching your query")
            else:
                self.logger.info(f"\nFound {len(all_results)} total results")
                
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
    
    def list_packages(self, manager_hint: str = 'auto') -> None:
        """List installed packages"""
        try:
            if manager_hint != 'auto' and manager_hint in self.managers:
                # List packages from specific manager
                packages = self.package_db.get_packages_by_manager(manager_hint)
                self.logger.info(f"📦 Packages managed by {manager_hint.upper()}:")
            else:
                # List all packages
                packages = self.package_db.list_packages()
                self.logger.info("📦 All installed packages:")
            
            if not packages:
                self.logger.info("No packages found")
                return
            
            # Group by manager
            by_manager = {}
            for pkg in packages:
                if pkg.manager not in by_manager:
                    by_manager[pkg.manager] = []
                by_manager[pkg.manager].append(pkg)
            
            for manager_name, manager_packages in by_manager.items():
                self.logger.info(f"\n{manager_name.upper()} ({len(manager_packages)} packages):")
                for pkg in sorted(manager_packages, key=lambda x: x.name):
                    self.logger.info(f"  {pkg.name} ({pkg.version}) - {pkg.install_date}")
                    if pkg.metadata.get('description'):
                        desc = pkg.metadata['description'][:80]
                        self.logger.info(f"    {desc}...")
            
        except Exception as e:
            self.logger.error(f"Failed to list packages: {e}")
    
    def get_statistics(self) -> None:
        """Display Batman statistics"""
        try:
            stats = self.package_db.get_statistics()
            
            self.logger.info("🦇 Batman Package Manager Statistics")
            self.logger.info("=" * 40)
            self.logger.info(f"Total packages: {stats['total_packages']}")
            
            self.logger.info(f"\nBy manager:")
            for manager, count in stats['by_manager'].items():
                self.logger.info(f"  {manager}: {count} packages")
            
            self.logger.info(f"\nAvailable managers: {', '.join(self.managers.keys())}")
            
            # Configuration info
            config_file = Path.home() / '.batman' / 'config.json'
            self.logger.info(f"Configuration: {config_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}") 