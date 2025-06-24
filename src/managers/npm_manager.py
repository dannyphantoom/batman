"""
NPM package manager for Batman package manager
"""

import json
from typing import List, Dict, Optional, Any
from pathlib import Path

from .base_manager import PackageManagerBase

class NpmManager(PackageManagerBase):
    """Package manager for Node.js npm packages"""
    
    def __init__(self, config: Dict[str, Any], logger):
        super().__init__(config, logger)
        self.npm_cmd = 'npm'
    
    def is_available(self) -> bool:
        """Check if npm is available on the system"""
        return self.check_command_exists('npm')
    
    def install(self, package_name: str, version: Optional[str] = None, **kwargs) -> bool:
        """Install a Node.js package using npm"""
        try:
            self.logger.command_start("install", package_name, "npm")
            
            if not self.validate_package_name(package_name):
                raise ValueError(f"Invalid package name: {package_name}")
            
            # Prepare package specification
            if version:
                package_spec = f"{package_name}@{version}"
            else:
                package_spec = package_name
            
            # Build install command
            install_cmd = ['npm', 'install']
            
            # Global installation flag
            if kwargs.get('global', False):
                install_cmd.append('-g')
            
            # Save flags
            if kwargs.get('save_dev', False):
                install_cmd.append('--save-dev')
            elif kwargs.get('save', True):
                install_cmd.append('--save')
            
            install_cmd.append(package_spec)
            
            # Run installation
            result = self.run_command(install_cmd)
            
            if result.returncode == 0:
                self.logger.command_success("install", package_name)
                return True
            else:
                self.logger.command_error("install", "Installation failed", package_name)
                return False
                
        except Exception as e:
            self.logger.command_error("install", str(e), package_name)
            return False
    
    def update(self, package_name: str, **kwargs) -> bool:
        """Update a Node.js package"""
        try:
            self.logger.command_start("update", package_name, "npm")
            
            update_cmd = ['npm', 'update']
            
            if kwargs.get('global', False):
                update_cmd.append('-g')
            
            update_cmd.append(package_name)
            
            result = self.run_command(update_cmd)
            
            if result.returncode == 0:
                self.logger.command_success("update", package_name)
                return True
            else:
                self.logger.command_error("update", "Update failed", package_name)
                return False
                
        except Exception as e:
            self.logger.command_error("update", str(e), package_name)
            return False
    
    def remove(self, package_name: str, **kwargs) -> bool:
        """Remove a Node.js package"""
        try:
            self.logger.command_start("remove", package_name, "npm")
            
            uninstall_cmd = ['npm', 'uninstall']
            
            if kwargs.get('global', False):
                uninstall_cmd.append('-g')
            
            uninstall_cmd.append(package_name)
            
            result = self.run_command(uninstall_cmd)
            
            if result.returncode == 0:
                self.logger.command_success("remove", package_name)
                return True
            else:
                self.logger.command_error("remove", "Removal failed", package_name)
                return False
                
        except Exception as e:
            self.logger.command_error("remove", str(e), package_name)
            return False
    
    def search(self, query: str, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """Search for Node.js packages"""
        try:
            search_cmd = ['npm', 'search', '--json', query]
            result = self.run_command(search_cmd)
            
            if result.returncode == 0:
                packages = json.loads(result.stdout)
                return [{
                    'name': pkg.get('name', ''),
                    'version': pkg.get('version', ''),
                    'description': pkg.get('description', ''),
                    'keywords': pkg.get('keywords', []),
                    'author': pkg.get('author', {}).get('name', '') if isinstance(pkg.get('author'), dict) else str(pkg.get('author', '')),
                    'homepage': pkg.get('links', {}).get('homepage', ''),
                } for pkg in packages]
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []
    
    def list_installed(self, **kwargs) -> List[Dict[str, Any]]:
        """List installed Node.js packages"""
        try:
            list_cmd = ['npm', 'list', '--json', '--depth=0']
            
            if kwargs.get('global', False):
                list_cmd.append('-g')
            
            result = self.run_command(list_cmd)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                dependencies = data.get('dependencies', {})
                
                return [{
                    'name': name,
                    'version': info.get('version', 'unknown'),
                    'manager': 'npm'
                } for name, info in dependencies.items()]
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to list packages: {e}")
            return []
    
    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a Node.js package"""
        try:
            info_cmd = ['npm', 'view', package_name, '--json']
            result = self.run_command(info_cmd)
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                
                return {
                    'name': info.get('name', package_name),
                    'version': info.get('version', 'unknown'),
                    'description': info.get('description', ''),
                    'author': info.get('author', {}).get('name', '') if isinstance(info.get('author'), dict) else str(info.get('author', '')),
                    'homepage': info.get('homepage', ''),
                    'repository': info.get('repository', {}),
                    'keywords': info.get('keywords', []),
                    'dependencies': list(info.get('dependencies', {}).keys()),
                    'manager': 'npm'
                }
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get package info: {e}")
            return None
    
    def is_installed(self, package_name: str) -> bool:
        """Check if a Node.js package is installed"""
        # Check both local and global installations
        for global_flag in [False, True]:
            packages = self.list_installed(**{'global': global_flag})
            if any(pkg['name'] == package_name for pkg in packages):
                return True
        return False
    
    def get_version(self, package_name: str) -> Optional[str]:
        """Get installed version of a Node.js package"""
        for global_flag in [False, True]:
            packages = self.list_installed(**{'global': global_flag})
            for pkg in packages:
                if pkg['name'] == package_name:
                    return pkg['version']
        return None
    
    def update_all(self, **kwargs) -> List[str]:
        """Update all installed packages"""
        try:
            # Get list of outdated packages
            outdated_cmd = ['npm', 'outdated', '--json']
            
            if kwargs.get('global', False):
                outdated_cmd.append('-g')
            
            result = self.run_command(outdated_cmd, check=False)  # npm outdated returns non-zero when packages are outdated
            
            if result.stdout:
                outdated_packages = json.loads(result.stdout)
                updated_packages = []
                
                for package_name, info in outdated_packages.items():
                    current_version = info.get('current', 'unknown')
                    wanted_version = info.get('wanted', 'unknown')
                    
                    self.logger.info(f"Updating {package_name} from {current_version} to {wanted_version}")
                    
                    if self.update(package_name, **kwargs):
                        updated_packages.append(package_name)
                
                return updated_packages
            else:
                self.logger.info("All packages are up to date")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to update packages: {e}")
            return [] 