"""
APT package manager for Batman package manager
"""

import re
from typing import List, Dict, Optional, Any
from pathlib import Path

from .base_manager import PackageManagerBase

class AptManager(PackageManagerBase):
    """Package manager for Debian/Ubuntu apt packages"""
    
    def __init__(self, config: Dict[str, Any], logger):
        super().__init__(config, logger)
        self.apt_cmd = 'apt'
    
    def is_available(self) -> bool:
        """Check if apt is available on the system"""
        return self.check_command_exists('apt')
    
    def install(self, package_name: str, version: Optional[str] = None, **kwargs) -> bool:
        """Install a package using apt"""
        try:
            self.logger.command_start("install", package_name, "apt")
            
            if not self.validate_package_name(package_name):
                raise ValueError(f"Invalid package name: {package_name}")
            
            # Prepare package specification
            if version:
                package_spec = f"{package_name}={version}"
            else:
                package_spec = package_name
            
            # Build install command
            install_cmd = ['sudo', 'apt', 'install', '-y']
            
            # Add options
            if kwargs.get('no_recommends', False):
                install_cmd.append('--no-install-recommends')
            
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
        """Update a package using apt"""
        try:
            self.logger.command_start("update", package_name, "apt")
            
            # First update package lists
            update_cmd = ['sudo', 'apt', 'update']
            self.run_command(update_cmd)
            
            # Then upgrade the specific package
            upgrade_cmd = ['sudo', 'apt', 'install', '-y', '--only-upgrade', package_name]
            result = self.run_command(upgrade_cmd)
            
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
        """Remove a package using apt"""
        try:
            self.logger.command_start("remove", package_name, "apt")
            
            remove_cmd = ['sudo', 'apt', 'remove', '-y']
            
            # Purge configuration files if requested
            if kwargs.get('purge', False):
                remove_cmd = ['sudo', 'apt', 'purge', '-y']
            
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
    
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Search for packages using apt"""
        try:
            search_cmd = ['apt', 'search', query]
            result = self.run_command(search_cmd)
            
            packages = []
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.strip() and not line.startswith('WARNING'):
                        # Parse apt search output
                        match = re.match(r'^(\S+)/(\S+)\s+(\S+)\s+(.*)$', line)
                        if match:
                            name, repo, version, description = match.groups()
                            packages.append({
                                'name': name,
                                'version': version,
                                'description': description,
                                'repository': repo,
                                'manager': 'apt'
                            })
            
            return packages
                
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []
    
    def list_installed(self, **kwargs) -> List[Dict[str, Any]]:
        """List installed packages using apt"""
        try:
            list_cmd = ['dpkg', '-l']
            result = self.run_command(list_cmd)
            
            packages = []
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    # Parse dpkg -l output
                    if line.startswith('ii '):  # ii means installed
                        parts = line.split()
                        if len(parts) >= 3:
                            name = parts[1]
                            version = parts[2]
                            description = ' '.join(parts[3:]) if len(parts) > 3 else ''
                            
                            packages.append({
                                'name': name,
                                'version': version,
                                'description': description,
                                'manager': 'apt'
                            })
            
            return packages
                
        except Exception as e:
            self.logger.error(f"Failed to list packages: {e}")
            return []
    
    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a package"""
        try:
            show_cmd = ['apt', 'show', package_name]
            result = self.run_command(show_cmd)
            
            if result.returncode == 0:
                info = {}
                for line in result.stdout.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        info[key.strip().lower().replace('-', '_')] = value.strip()
                
                return {
                    'name': info.get('package', package_name),
                    'version': info.get('version', 'unknown'),
                    'description': info.get('description', ''),
                    'maintainer': info.get('maintainer', ''),
                    'homepage': info.get('homepage', ''),
                    'section': info.get('section', ''),
                    'size': info.get('installed_size', ''),
                    'dependencies': [dep.strip() for dep in info.get('depends', '').split(',') if dep.strip()],
                    'manager': 'apt'
                }
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get package info: {e}")
            return None
    
    def is_installed(self, package_name: str) -> bool:
        """Check if a package is installed"""
        try:
            check_cmd = ['dpkg', '-l', package_name]
            result = self.run_command(check_cmd, check=False)
            
            # Check if package is in installed state
            for line in result.stdout.split('\n'):
                if line.startswith('ii ') and package_name in line:
                    return True
            
            return False
            
        except Exception:
            return False
    
    def get_version(self, package_name: str) -> Optional[str]:
        """Get installed version of a package"""
        try:
            version_cmd = ['dpkg', '-l', package_name]
            result = self.run_command(version_cmd, check=False)
            
            for line in result.stdout.split('\n'):
                if line.startswith('ii ') and package_name in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        return parts[2]
            
            return None
            
        except Exception:
            return None
    
    def update_all(self, **kwargs) -> List[str]:
        """Update all installed packages"""
        try:
            self.logger.info("Updating package lists...")
            update_cmd = ['sudo', 'apt', 'update']
            self.run_command(update_cmd)
            
            # Get list of upgradable packages
            upgradable_cmd = ['apt', 'list', '--upgradable']
            result = self.run_command(upgradable_cmd)
            
            upgradable_packages = []
            for line in result.stdout.split('\n'):
                if '/' in line and '[upgradable' in line:
                    package_name = line.split('/')[0]
                    if package_name != 'Listing':
                        upgradable_packages.append(package_name)
            
            if not upgradable_packages:
                self.logger.info("All packages are up to date")
                return []
            
            self.logger.info(f"Upgrading {len(upgradable_packages)} packages...")
            
            # Perform the upgrade
            upgrade_cmd = ['sudo', 'apt', 'upgrade', '-y']
            result = self.run_command(upgrade_cmd)
            
            if result.returncode == 0:
                self.logger.command_success("update all packages")
                return upgradable_packages
            else:
                self.logger.command_error("update all packages", "Upgrade failed")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to update packages: {e}")
            return [] 