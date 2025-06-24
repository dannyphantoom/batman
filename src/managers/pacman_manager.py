"""
Pacman package manager for Batman package manager (Arch Linux)
"""

import json
import re
from typing import List, Dict, Optional, Any
from pathlib import Path

from .base_manager import PackageManagerBase

class PacmanManager(PackageManagerBase):
    """Package manager for Arch Linux pacman packages"""
    
    def __init__(self, config: Dict[str, Any], logger):
        super().__init__(config, logger)
        self.pacman_cmd = 'pacman'
    
    def is_available(self) -> bool:
        """Check if pacman is available on the system"""
        return self.check_command_exists('pacman')
    
    def install(self, package_name: str, version: Optional[str] = None, **kwargs) -> bool:
        """Install a package using pacman"""
        try:
            self.logger.command_start("install", package_name, "pacman")
            
            if not self.validate_package_name(package_name):
                raise ValueError(f"Invalid package name: {package_name}")
            
            # Pacman doesn't support installing specific versions directly
            # We'll warn the user if they try to specify a version
            if version:
                self.logger.warning(f"Pacman doesn't support installing specific versions. "
                                  f"Installing latest version of {package_name}")
            
            # Build install command
            install_cmd = ['sudo', 'pacman', '-S', '--noconfirm']
            
            # Add needed flag if requested
            if kwargs.get('needed', True):
                install_cmd.append('--needed')
            
            install_cmd.append(package_name)
            
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
        """Update a specific package"""
        try:
            self.logger.command_start("update", package_name, "pacman")
            
            # Check if package is installed first
            if not self.is_installed(package_name):
                self.logger.info(f"Package {package_name} not installed, installing instead...")
                return self.install(package_name, **kwargs)
            
            # Upgrade specific package
            update_cmd = ['sudo', 'pacman', '-S', '--noconfirm', package_name]
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
        """Remove a package"""
        try:
            self.logger.command_start("remove", package_name, "pacman")
            
            remove_cmd = ['sudo', 'pacman', '-R', '--noconfirm']
            
            # Add cascade option if requested
            if kwargs.get('cascade', False):
                remove_cmd.append('--cascade')
            
            # Add recursive option if requested (remove dependencies)
            if kwargs.get('recursive', False):
                remove_cmd.append('--recursive')
            
            remove_cmd.append(package_name)
            
            result = self.run_command(remove_cmd)
            
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
        """Search for packages"""
        try:
            search_cmd = ['pacman', '-Ss', query]
            result = self.run_command(search_cmd)
            
            if result.returncode == 0:
                packages = []
                lines = result.stdout.split('\n')
                
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    if not line:
                        i += 1
                        continue
                    
                    # Parse package info line (format: repo/name version [group] (size))
                    match = re.match(r'^([^/]+)/([^\s]+)\s+([^\s]+)', line)
                    if match:
                        repo, name, version = match.groups()
                        
                        # Get description from next line if available
                        description = ""
                        if i + 1 < len(lines) and lines[i + 1].startswith('    '):
                            description = lines[i + 1].strip()
                            i += 1
                        
                        packages.append({
                            'name': name,
                            'version': version,
                            'description': description,
                            'repository': repo,
                            'manager': 'pacman'
                        })
                    
                    i += 1
                
                return packages
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []
    
    def list_installed(self, **kwargs) -> List[Dict[str, Any]]:
        """List installed packages"""
        try:
            list_cmd = ['pacman', '-Q']
            
            # Add explicit packages only flag if requested
            if kwargs.get('explicit', False):
                list_cmd.append('-e')
            
            result = self.run_command(list_cmd)
            
            if result.returncode == 0:
                packages = []
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line:
                        parts = line.split(' ', 1)
                        if len(parts) == 2:
                            name, version = parts
                            packages.append({
                                'name': name,
                                'version': version,
                                'manager': 'pacman'
                            })
                
                return packages
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to list packages: {e}")
            return []
    
    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a package"""
        try:
            # Try to get info for installed package first
            info_cmd = ['pacman', '-Qi', package_name]
            result = self.run_command(info_cmd, check=False)
            
            if result.returncode != 0:
                # If not installed, try to get info from repositories
                info_cmd = ['pacman', '-Si', package_name]
                result = self.run_command(info_cmd, check=False)
            
            if result.returncode == 0:
                info = {}
                for line in result.stdout.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip().lower().replace(' ', '_')
                        value = value.strip()
                        info[key] = value
                
                # Parse dependencies
                dependencies = []
                if 'depends_on' in info:
                    deps = info['depends_on']
                    if deps and deps != 'None':
                        dependencies = [dep.strip() for dep in deps.split()]
                
                return {
                    'name': info.get('name', package_name),
                    'version': info.get('version', 'unknown'),
                    'description': info.get('description', ''),
                    'architecture': info.get('architecture', ''),
                    'url': info.get('url', ''),
                    'repository': info.get('repository', ''),
                    'packager': info.get('packager', ''),
                    'install_size': info.get('installed_size', ''),
                    'dependencies': dependencies,
                    'manager': 'pacman'
                }
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get package info: {e}")
            return None
    
    def is_installed(self, package_name: str) -> bool:
        """Check if a package is installed"""
        try:
            check_cmd = ['pacman', '-Q', package_name]
            result = self.run_command(check_cmd, check=False)
            return result.returncode == 0
        except:
            return False
    
    def get_version(self, package_name: str) -> Optional[str]:
        """Get installed version of a package"""
        try:
            version_cmd = ['pacman', '-Q', package_name]
            result = self.run_command(version_cmd, check=False)
            
            if result.returncode == 0:
                parts = result.stdout.strip().split(' ', 1)
                if len(parts) == 2:
                    return parts[1]
            
            return None
        except:
            return None
    
    def update_all(self, **kwargs) -> List[str]:
        """Update all packages"""
        try:
            self.logger.info("Updating all packages with pacman...")
            
            # First update package database
            sync_cmd = ['sudo', 'pacman', '-Sy']
            self.run_command(sync_cmd)
            
            # Then upgrade all packages
            upgrade_cmd = ['sudo', 'pacman', '-Su', '--noconfirm']
            result = self.run_command(upgrade_cmd)
            
            if result.returncode == 0:
                # Get list of upgraded packages from output
                # This is simplified - in reality you'd parse the output
                return ["system-upgrade"]
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to update all packages: {e}")
            return []
    
    def normalize_package_name(self, name: str) -> str:
        """Normalize package name for pacman"""
        # Pacman package names are generally lowercase
        return name.strip().lower()
    
    def validate_package_name(self, package_name: str) -> bool:
        """Validate package name format for pacman"""
        if not super().validate_package_name(package_name):
            return False
        
        # Additional pacman-specific validation
        # Package names should not start with hyphen and should be alphanumeric with hyphens
        return bool(re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._+-]*$', package_name)) 