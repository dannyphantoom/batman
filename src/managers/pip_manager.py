"""
Pip package manager for Batman package manager
"""

import json
import re
import sys
from typing import List, Dict, Optional, Any
from pathlib import Path

from .base_manager import PackageManagerBase

class PipManager(PackageManagerBase):
    """Package manager for Python pip packages"""
    
    def __init__(self, config: Dict[str, Any], logger):
        super().__init__(config, logger)
        self.pip_cmd = self._find_pip_command()
    
    def _find_pip_command(self) -> str:
        """Find the appropriate pip command"""
        # Try different pip commands in order of preference
        pip_commands = ['pip3', 'pip', 'python3 -m pip', 'python -m pip']
        
        for cmd in pip_commands:
            if self.check_command_exists(cmd.split()[0]):
                try:
                    # Test the command
                    result = self.run_command(cmd.split() + ['--version'], capture_output=True)
                    if result.returncode == 0:
                        self.logger.debug(f"Using pip command: {cmd}")
                        return cmd
                except:
                    continue
        
        raise RuntimeError("Could not find pip command")
    
    def is_available(self) -> bool:
        """Check if pip is available on the system"""
        try:
            self._find_pip_command()
            return True
        except RuntimeError:
            return False
    
    def install(self, package_name: str, version: Optional[str] = None, **kwargs) -> bool:
        """Install a Python package using pip"""
        try:
            self.logger.command_start("install", package_name, "pip")
            
            if not self.validate_package_name(package_name):
                raise ValueError(f"Invalid package name: {package_name}")
            
            # Prepare the package specification
            if version:
                package_spec = f"{package_name}=={version}"
            else:
                package_spec = package_name
            
            # Build install command
            install_cmd = self.pip_cmd.split() + ['install']
            
            # Add user flag if not running as root and not in virtual environment
            if not kwargs.get('system_wide', False) and not self._in_virtual_env():
                install_cmd.append('--user')
            
            # Add upgrade flag if requested
            if kwargs.get('upgrade', False):
                install_cmd.append('--upgrade')
            
            # Add target directory if specified
            target_dir = kwargs.get('target', self.install_dir)
            if target_dir and target_dir != self.install_dir:
                install_cmd.extend(['--target', str(target_dir)])
            
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
        """Update a Python package"""
        return self.install(package_name, upgrade=True, **kwargs)
    
    def remove(self, package_name: str, **kwargs) -> bool:
        """Remove a Python package"""
        try:
            self.logger.command_start("remove", package_name, "pip")
            
            uninstall_cmd = self.pip_cmd.split() + ['uninstall', '-y', package_name]
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
    
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Search for Python packages (using pip search alternative)"""
        try:
            # pip search was removed, so we'll use pypi.org API
            import urllib.request
            import urllib.parse
            
            encoded_query = urllib.parse.quote(query)
            url = f"https://pypi.org/pypi/{encoded_query}/json"
            
            try:
                with urllib.request.urlopen(url) as response:
                    data = json.loads(response.read())
                
                package_info = data.get('info', {})
                return [{
                    'name': package_info.get('name', query),
                    'version': package_info.get('version', 'unknown'),
                    'description': package_info.get('summary', ''),
                    'homepage': package_info.get('home_page', ''),
                    'author': package_info.get('author', ''),
                }]
            except:
                # If direct package lookup fails, return empty list
                # In a full implementation, we'd use a proper search API
                return []
                
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []
    
    def list_installed(self, **kwargs) -> List[Dict[str, Any]]:
        """List installed Python packages"""
        try:
            list_cmd = self.pip_cmd.split() + ['list', '--format=json']
            result = self.run_command(list_cmd)
            
            if result.returncode == 0:
                packages = json.loads(result.stdout)
                return [{
                    'name': pkg['name'],
                    'version': pkg['version'],
                    'manager': 'pip'
                } for pkg in packages]
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to list packages: {e}")
            return []
    
    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a Python package"""
        try:
            show_cmd = self.pip_cmd.split() + ['show', package_name]
            result = self.run_command(show_cmd)
            
            if result.returncode == 0:
                info = {}
                for line in result.stdout.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        info[key.strip().lower().replace('-', '_')] = value.strip()
                
                return {
                    'name': info.get('name', package_name),
                    'version': info.get('version', 'unknown'),
                    'description': info.get('summary', ''),
                    'author': info.get('author', ''),
                    'homepage': info.get('home_page', ''),
                    'location': info.get('location', ''),
                    'dependencies': [dep.strip() for dep in info.get('requires', '').split(',') if dep.strip()],
                    'manager': 'pip'
                }
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get package info: {e}")
            return None
    
    def is_installed(self, package_name: str) -> bool:
        """Check if a Python package is installed"""
        return self.get_package_info(package_name) is not None
    
    def get_version(self, package_name: str) -> Optional[str]:
        """Get installed version of a Python package"""
        info = self.get_package_info(package_name)
        return info.get('version') if info else None
    
    def _in_virtual_env(self) -> bool:
        """Check if running in a virtual environment"""
        return hasattr(sys, 'real_prefix') or (
            hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
        )
    
    def update_all(self, **kwargs) -> List[str]:
        """Update all installed packages"""
        try:
            # Get list of outdated packages
            outdated_cmd = self.pip_cmd.split() + ['list', '--outdated', '--format=json']
            result = self.run_command(outdated_cmd)
            
            if result.returncode != 0:
                return []
            
            outdated_packages = json.loads(result.stdout)
            updated_packages = []
            
            for pkg in outdated_packages:
                package_name = pkg['name']
                self.logger.info(f"Updating {package_name} from {pkg['version']} to {pkg['latest_version']}")
                
                if self.update(package_name, **kwargs):
                    updated_packages.append(package_name)
            
            return updated_packages
            
        except Exception as e:
            self.logger.error(f"Failed to update packages: {e}")
            return [] 