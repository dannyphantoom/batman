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
            
            # Try installation with different strategies
            return self._install_with_fallback(package_spec, **kwargs)
                
        except Exception as e:
            self.logger.command_error("install", str(e), package_name)
            return False
    
    def _install_with_fallback(self, package_spec: str, **kwargs) -> bool:
        """Install with fallback strategies for externally-managed-environment"""
        package_name = package_spec.split('=')[0].split('@')[0]
        
        # Strategy 1: Try normal user installation first
        if self._try_user_install(package_spec, **kwargs):
            return True
        
        # Strategy 2: Handle externally-managed-environment error
        return self._handle_externally_managed_error(package_spec, **kwargs)
    
    def _try_user_install(self, package_spec: str, **kwargs) -> bool:
        """Try standard user installation"""
        try:
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
            result = self.run_command(install_cmd, check=False)
            
            if result.returncode == 0:
                package_name = package_spec.split('=')[0].split('@')[0]
                self.logger.command_success("install", package_name)
                return True
            
            # Check if it's the externally-managed-environment error
            if "externally-managed-environment" in result.stderr:
                return False  # Will trigger fallback handling
            else:
                # Some other error
                self.logger.command_error("install", f"Installation failed: {result.stderr}", package_name)
                return False
                
        except Exception as e:
            self.logger.debug(f"User install attempt failed: {e}")
            return False
    
    def _handle_externally_managed_error(self, package_spec: str, **kwargs) -> bool:
        """Handle externally-managed-environment error with user choices"""
        package_name = package_spec.split('=')[0].split('@')[0]
        
        self.logger.warning("Detected externally-managed-environment (PEP 668)")
        self.logger.info("This Python environment is managed by your system package manager.")
        self.logger.info("\nChoose installation method:")
        self.logger.info("  1) Use --break-system-packages (override system protection)")
        self.logger.info("  2) Create a virtual environment (recommended)")
        self.logger.info("  3) Try system package manager (pacman/apt)")
        self.logger.info("  4) Cancel installation")
        
        try:
            choice = input("Enter choice (1/2/3/4): ").strip()
        except (EOFError, KeyboardInterrupt):
            self.logger.info("Installation cancelled by user")
            return False
        
        if choice == "1":
            return self._install_with_break_system_packages(package_spec, **kwargs)
        elif choice == "2":
            return self._install_with_venv(package_spec, **kwargs)
        elif choice == "3":
            return self._suggest_system_package(package_name)
        else:
            self.logger.info("Installation cancelled")
            return False
    
    def _install_with_break_system_packages(self, package_spec: str, **kwargs) -> bool:
        """Install using --break-system-packages flag"""
        try:
            self.logger.info("Installing with --break-system-packages...")
            
            install_cmd = self.pip_cmd.split() + ['install', '--user', '--break-system-packages']
            
            # Add upgrade flag if requested
            if kwargs.get('upgrade', False):
                install_cmd.append('--upgrade')
            
            install_cmd.append(package_spec)
            
            result = self.run_command(install_cmd)
            
            if result.returncode == 0:
                package_name = package_spec.split('=')[0].split('@')[0]
                self.logger.command_success("install", package_name, "Installed with --break-system-packages")
                return True
            else:
                self.logger.command_error("install", "Installation failed even with --break-system-packages")
                return False
                
        except Exception as e:
            self.logger.command_error("install", f"Failed with --break-system-packages: {e}")
            return False
    
    def _install_with_venv(self, package_spec: str, **kwargs) -> bool:
        """Install using a virtual environment"""
        try:
            package_name = package_spec.split('=')[0].split('@')[0]
            self.logger.info("Creating virtual environment for package...")
            
            # Create venv in Batman's directory
            venv_dir = Path.home() / '.batman' / 'venvs' / package_name
            venv_dir.parent.mkdir(parents=True, exist_ok=True)
            
            if venv_dir.exists():
                self.logger.warning(f"Virtual environment already exists: {venv_dir}")
                overwrite = input("Overwrite existing virtual environment? (y/N): ").strip().lower()
                if overwrite != 'y':
                    self.logger.info("Installation cancelled")
                    return False
                
                import shutil
                shutil.rmtree(venv_dir)
            
            # Create virtual environment
            import subprocess
            create_cmd = [sys.executable, '-m', 'venv', str(venv_dir)]
            result = subprocess.run(create_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.command_error("install", f"Failed to create virtual environment: {result.stderr}")
                return False
            
            self.logger.info(f"Virtual environment created: {venv_dir}")
            
            # Install package in venv
            venv_pip = venv_dir / 'bin' / 'pip'
            if not venv_pip.exists():
                # Windows
                venv_pip = venv_dir / 'Scripts' / 'pip.exe'
            
            install_cmd = [str(venv_pip), 'install']
            
            if kwargs.get('upgrade', False):
                install_cmd.append('--upgrade')
            
            install_cmd.append(package_spec)
            
            result = subprocess.run(install_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.command_success("install", package_name, f"Installed in virtual environment: {venv_dir}")
                self.logger.info(f"💡 To use: source {venv_dir}/bin/activate  # or {venv_dir}\\Scripts\\activate on Windows")
                
                # Update our install directory to point to the venv
                self.install_dir = venv_dir
                return True
            else:
                self.logger.command_error("install", f"Failed to install in virtual environment: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.command_error("install", f"Virtual environment installation failed: {e}")
            return False
    
    def _suggest_system_package(self, package_name: str) -> bool:
        """Try to install using system package manager instead"""
        self.logger.info(f"Checking if '{package_name}' is available as a system package...")
        
        # Common Python package name mappings for system packages
        system_mappings = {
            'numpy': 'python-numpy',
            'scipy': 'python-scipy', 
            'matplotlib': 'python-matplotlib',
            'pandas': 'python-pandas',
            'requests': 'python-requests',
            'flask': 'python-flask',
            'django': 'python-django',
            'sympy': 'python-sympy',
            'pillow': 'python-pillow',
            'pil': 'python-pillow',
            'pyqt5': 'python-pyqt5',
            'pyqt6': 'python-pyqt6',
            'psutil': 'python-psutil',
            'lxml': 'python-lxml',
            'beautifulsoup4': 'python-beautifulsoup4',
            'selenium': 'python-selenium',
            'cryptography': 'python-cryptography',
            'setuptools': 'python-setuptools',
            'wheel': 'python-wheel',
            'virtualenv': 'python-virtualenv',
            'pytest': 'python-pytest',
            'pylint': 'python-pylint',
            'black': 'python-black',
            'flake8': 'python-flake8',
            'isort': 'python-isort',
            'mypy': 'python-mypy',
            'poetry': 'python-poetry',
            'tox': 'python-tox',
            'sphinx': 'python-sphinx',
            'click': 'python-click',
            'pyyaml': 'python-yaml',
            'yaml': 'python-yaml',
            'redis': 'python-redis',
            'celery': 'python-celery',
            'sqlalchemy': 'python-sqlalchemy',
            'alembic': 'python-alembic',
            'jinja2': 'python-jinja',
            'markupsafe': 'python-markupsafe',
            'werkzeug': 'python-werkzeug',
            'twisted': 'python-twisted',
            'tornado': 'python-tornado',
            'aiohttp': 'python-aiohttp',
            'fastapi': 'python-fastapi',
        }
        
        system_name = system_mappings.get(package_name.lower(), f'python-{package_name}')
        
        # Detect the system package manager
        system_manager = self._detect_system_package_manager()
        if not system_manager:
            self.logger.warning("Could not detect system package manager")
            self.logger.info(f"💡 Try installing with system package manager:")
            self.logger.info(f"  pacman -S {system_name}  # Arch Linux")
            self.logger.info(f"  apt install {system_name}  # Debian/Ubuntu")
            self.logger.info(f"\nOr run: batman -i {system_name} --manager pacman")
            return False
        
        # Try to install with the detected system package manager
        self.logger.info(f"Attempting to install '{system_name}' using {system_manager}...")
        
        try:
            if system_manager == 'pacman':
                install_cmd = ['sudo', 'pacman', '-S', '--noconfirm', system_name]
            elif system_manager == 'apt':
                install_cmd = ['sudo', 'apt', 'install', '-y', system_name]
            elif system_manager == 'yum':
                install_cmd = ['sudo', 'yum', 'install', '-y', system_name]
            elif system_manager == 'dnf':
                install_cmd = ['sudo', 'dnf', 'install', '-y', system_name]
            elif system_manager == 'brew':
                install_cmd = ['brew', 'install', system_name]
            else:
                self.logger.warning(f"Unsupported system package manager: {system_manager}")
                return False
            
            result = self.run_command(install_cmd, check=False)
            
            if result.returncode == 0:
                self.logger.command_success("install", package_name, f"Installed {system_name} with {system_manager}")
                return True
            else:
                self.logger.warning(f"Failed to install {system_name} with {system_manager}")
                self.logger.info(f"💡 You can try manually:")
                self.logger.info(f"  {' '.join(install_cmd)}")
                self.logger.info(f"\nOr run: batman -i {system_name} --manager {system_manager}")
                return False
                
        except Exception as e:
            self.logger.warning(f"Error attempting system installation: {e}")
            self.logger.info(f"💡 Try installing manually with system package manager:")
            self.logger.info(f"  {system_manager} install {system_name}")
            return False
    
    def _detect_system_package_manager(self) -> Optional[str]:
        """Detect the system's package manager"""
        # Check for package managers in order of preference
        package_managers = [
            ('pacman', 'pacman'),
            ('apt', 'apt'),
            ('yum', 'yum'), 
            ('dnf', 'dnf'),
            ('brew', 'brew'),
        ]
        
        for manager_name, command in package_managers:
            if self.check_command_exists(command):
                self.logger.debug(f"Detected system package manager: {manager_name}")
                return manager_name
        
        return None
    
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
    
    def search(self, query: str, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
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