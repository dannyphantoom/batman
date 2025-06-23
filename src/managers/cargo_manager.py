"""
Cargo package manager for Batman package manager (Rust)
"""

import json
import os
import re
from typing import List, Dict, Optional, Any
from pathlib import Path

from .base_manager import PackageManagerBase

class CargoManager(PackageManagerBase):
    """Package manager for Rust cargo packages"""
    
    def __init__(self, config: Dict[str, Any], logger):
        super().__init__(config, logger)
        self.cargo_cmd = 'cargo'
        self.cargo_home = Path(os.environ.get('CARGO_HOME', Path.home() / '.cargo'))
        self.bin_dir = self.cargo_home / 'bin'
    
    def is_available(self) -> bool:
        """Check if cargo is available on the system"""
        return self.check_command_exists('cargo')
    
    def install(self, package_name: str, version: Optional[str] = None, **kwargs) -> bool:
        """Install a Rust crate using cargo"""
        try:
            self.logger.command_start("install", package_name, "cargo")
            
            if not self.validate_package_name(package_name):
                raise ValueError(f"Invalid package name: {package_name}")
            
            # Build install command
            install_cmd = ['cargo', 'install']
            
            # Add version if specified
            if version:
                install_cmd.extend(['--version', version])
            
            # Add force flag if requested (reinstall)
            if kwargs.get('force', False):
                install_cmd.append('--force')
            
            # Add git source if specified
            if kwargs.get('git'):
                install_cmd.extend(['--git', kwargs['git']])
            
            # Add branch if specified
            if kwargs.get('branch'):
                install_cmd.extend(['--branch', kwargs['branch']])
            
            # Add features if specified
            if kwargs.get('features'):
                features = kwargs['features']
                if isinstance(features, list):
                    features = ','.join(features)
                install_cmd.extend(['--features', features])
            
            # All features flag
            if kwargs.get('all_features', False):
                install_cmd.append('--all-features')
            
            # No default features
            if kwargs.get('no_default_features', False):
                install_cmd.append('--no-default-features')
            
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
        """Update a Rust crate (reinstall latest version)"""
        try:
            self.logger.command_start("update", package_name, "cargo")
            
            # Check if package is installed first
            if not self.is_installed(package_name):
                self.logger.info(f"Package {package_name} not installed, installing instead...")
                return self.install(package_name, **kwargs)
            
            # For cargo, update means reinstall with force
            kwargs['force'] = True
            return self.install(package_name, **kwargs)
                
        except Exception as e:
            self.logger.command_error("update", str(e), package_name)
            return False
    
    def remove(self, package_name: str, **kwargs) -> bool:
        """Remove a Rust crate"""
        try:
            self.logger.command_start("remove", package_name, "cargo")
            
            # Check if package is installed
            if not self.is_installed(package_name):
                self.logger.warning(f"Package {package_name} is not installed")
                return True
            
            # Remove the binary from cargo bin directory
            bin_path = self.bin_dir / package_name
            if bin_path.exists():
                bin_path.unlink()
                self.logger.command_success("remove", package_name)
                return True
            else:
                # Try to find the binary with different name
                # Some crates install with different binary names
                for bin_file in self.bin_dir.glob(f"{package_name}*"):
                    if bin_file.is_file():
                        bin_file.unlink()
                        self.logger.command_success("remove", package_name)
                        return True
                
                self.logger.command_error("remove", "Binary not found", package_name)
                return False
                
        except Exception as e:
            self.logger.command_error("remove", str(e), package_name)
            return False
    
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Search for Rust crates"""
        try:
            search_cmd = ['cargo', 'search', query]
            
            # Limit results
            limit = kwargs.get('limit', 10)
            search_cmd.extend(['--limit', str(limit)])
            
            result = self.run_command(search_cmd)
            
            if result.returncode == 0:
                packages = []
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if not line or line.startswith('...'):
                        continue
                    
                    # Parse search results (format: name = "version"    # description)
                    match = re.match(r'^([^\s=]+)\s*=\s*"([^"]+)"\s*#?\s*(.*)', line)
                    if match:
                        name, version, description = match.groups()
                        packages.append({
                            'name': name,
                            'version': version,
                            'description': description.strip(),
                            'manager': 'cargo'
                        })
                
                return packages
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []
    
    def list_installed(self, **kwargs) -> List[Dict[str, Any]]:
        """List installed Rust crates"""
        try:
            if not self.bin_dir.exists():
                return []
            
            packages = []
            for bin_file in self.bin_dir.iterdir():
                if bin_file.is_file() and bin_file.stat().st_mode & 0o111:  # Executable
                    name = bin_file.name
                    
                    # Try to get version info
                    version = "unknown"
                    try:
                        # Try common version flags
                        for flag in ['--version', '-V', '--help']:
                            try:
                                result = self.run_command([str(bin_file), flag], 
                                                        capture_output=True, check=False)
                                if result.returncode == 0:
                                    output = result.stdout.strip()
                                    # Extract version from output
                                    version_match = re.search(r'(\d+\.\d+\.\d+)', output)
                                    if version_match:
                                        version = version_match.group(1)
                                        break
                            except:
                                continue
                    except:
                        pass
                    
                    packages.append({
                        'name': name,
                        'version': version,
                        'manager': 'cargo'
                    })
            
            return packages
                
        except Exception as e:
            self.logger.error(f"Failed to list packages: {e}")
            return []
    
    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a Rust crate"""
        try:
            # Use cargo search to get basic info
            search_cmd = ['cargo', 'search', package_name, '--limit', '1']
            result = self.run_command(search_cmd)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('...'):
                        match = re.match(r'^([^\s=]+)\s*=\s*"([^"]+)"\s*#?\s*(.*)', line)
                        if match:
                            name, version, description = match.groups()
                            if name == package_name:
                                return {
                                    'name': name,
                                    'version': version,
                                    'description': description.strip(),
                                    'manager': 'cargo',
                                    'registry': 'crates.io'
                                }
            
            return None
                
        except Exception as e:
            self.logger.error(f"Failed to get package info: {e}")
            return None
    
    def is_installed(self, package_name: str) -> bool:
        """Check if a Rust crate is installed"""
        try:
            # Check if binary exists in cargo bin directory
            bin_path = self.bin_dir / package_name
            if bin_path.exists() and bin_path.is_file():
                return True
            
            # Some crates might have different binary names
            # Check if any binary starts with the package name
            for bin_file in self.bin_dir.glob(f"{package_name}*"):
                if bin_file.is_file():
                    return True
            
            return False
        except:
            return False
    
    def get_version(self, package_name: str) -> Optional[str]:
        """Get installed version of a Rust crate"""
        try:
            bin_path = self.bin_dir / package_name
            if not bin_path.exists():
                return None
            
            # Try to get version from the binary
            for flag in ['--version', '-V']:
                try:
                    result = self.run_command([str(bin_path), flag], 
                                            capture_output=True, check=False)
                    if result.returncode == 0:
                        output = result.stdout.strip()
                        # Extract version from output
                        version_match = re.search(r'(\d+\.\d+\.\d+)', output)
                        if version_match:
                            return version_match.group(1)
                except:
                    continue
            
            return "unknown"
        except:
            return None
    
    def update_all(self, **kwargs) -> List[str]:
        """Update all installed Rust crates"""
        try:
            updated_packages = []
            installed_packages = self.list_installed()
            
            for package in installed_packages:
                package_name = package['name']
                self.logger.info(f"Updating {package_name}...")
                
                if self.update(package_name, **kwargs):
                    updated_packages.append(package_name)
                else:
                    self.logger.warning(f"Failed to update {package_name}")
            
            return updated_packages
                
        except Exception as e:
            self.logger.error(f"Failed to update all packages: {e}")
            return []
    
    def normalize_package_name(self, name: str) -> str:
        """Normalize package name for cargo"""
        # Cargo package names are generally lowercase with hyphens
        return name.strip().lower().replace('_', '-')
    
    def validate_package_name(self, package_name: str) -> bool:
        """Validate package name format for cargo"""
        if not super().validate_package_name(package_name):
            return False
        
        # Cargo package names should be lowercase, alphanumeric with hyphens/underscores
        return bool(re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', package_name))
    
    def auto_detect_project_type(self, directory: Path = None) -> bool:
        """Auto-detect if this is a Rust project"""
        search_dir = directory or Path.cwd()
        
        # Look for Cargo.toml or Cargo.lock
        for pattern in ['Cargo.toml', 'Cargo.lock']:
            if list(search_dir.glob(pattern)):
                self.logger.debug(f"Auto-detected Rust project in {search_dir}")
                return True
        
        return False 