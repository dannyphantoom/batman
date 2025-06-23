# 🦇 Batman Package Manager

Batman is a universal package manager that unifies multiple package management systems into a single, easy-to-use interface. Never again worry about remembering different commands for pip, npm, apt, cargo, and more!

## Features

- **Universal Interface**: One command to rule them all! Install packages from any package manager using the same syntax
- **Auto-Detection**: Automatically detects the right package manager based on your project files
- **Unified Database**: Keeps track of all installed packages across all managers
- **Update Management**: Update individual packages or your entire system with one command
- **Multiple Manager Support**: Currently supports:
  - 🐍 **pip** (Python packages)
  - 📦 **npm** (Node.js packages)
  - 🐧 **apt** (Debian/Ubuntu packages)
  - 🦀 **cargo** (Rust packages)
  - 🏗️ **pacman** (Arch Linux packages)
  - *(More coming soon: brew, yum/dnf, etc.)*
- **Smart Organization**: Packages are organized in appropriate directories
- **Backup Support**: Optional backup before updates
- **Dry Run Mode**: See what would happen before making changes
- **Colored Output**: Beautiful, informative console output

## Installation

### Quick Install
```bash
git clone https://github.com/yourusername/batman.git
cd batman
chmod +x batman.py

# Create symbolic link for global access
sudo ln -s $(pwd)/batman.py /usr/local/bin/batman
```

### From Source
```bash
git clone https://github.com/yourusername/batman.git
cd batman
python3 batman.py --help
```

## Usage

### Basic Commands

```bash
# Install packages (auto-detects package manager)
batman -i numpy                    # Install Python package
batman -i numpy==1.21.0            # Install specific version
batman -i express --manager npm    # Install Node.js package
batman -i express@4.18.0 --manager npm  # Install specific npm version
batman -i git --manager apt        # Install system package
batman -i serde --manager cargo    # Install Rust crate
batman -i curl --manager pacman    # Install via pacman (Arch Linux)

# Update packages
batman -u numpy                    # Update specific package
batman -u --all                    # Update all packages

# Remove packages
batman -r numpy                    # Remove package

# Search for packages
batman --search numpy              # Search across all managers
batman --search express --manager npm  # Search in specific manager

# List installed packages
batman --list                      # List all packages
batman --list --manager pip        # List packages from specific manager
```

### Advanced Usage

```bash
# Force installation (overwrite existing)
batman -i numpy --force

# Dry run (see what would happen)
batman -i express --dry-run

# Verbose output
batman -i numpy --verbose

# Version specification (multiple ways)
batman -i numpy --version 1.21.0    # Using --version flag
batman -i numpy==1.21.0             # Using == syntax
batman -i numpy@1.21.0              # Using @ syntax (npm style)

# Manager-specific options
batman -i package_name --manager pip
batman -i package_name --manager npm
batman -i package_name --manager apt
batman -i package_name --manager cargo
batman -i package_name --manager pacman
```

### Auto-Detection

Batman automatically detects the appropriate package manager based on project files:

- **Python Projects**: Looks for `requirements.txt`, `pyproject.toml`, `setup.py`
- **Node.js Projects**: Looks for `package.json`, `package-lock.json`
- **Rust Projects**: Looks for `Cargo.toml`, `Cargo.lock`
- **System Packages**: Falls back to system package managers (pacman on Arch, apt on Debian/Ubuntu)

## Configuration

Batman stores its configuration in `~/.batman/config.json`. The configuration is automatically created on first run with sensible defaults.

### Configuration Options

```json
{
  "package_managers": {
    "pip": {
      "enabled": true,
      "install_dir": "/home/user/.batman/packages/python",
      "auto_detect_files": ["requirements.txt", "pyproject.toml", "setup.py"]
    },
    "npm": {
      "enabled": true,
      "install_dir": "/home/user/.batman/packages/node",
      "auto_detect_files": ["package.json", "package-lock.json"]
    },
    "cargo": {
      "enabled": true,
      "install_dir": "/home/user/.batman/packages/rust",
      "auto_detect_files": ["Cargo.toml", "Cargo.lock"]
    },
    "pacman": {
      "enabled": true,
      "install_dir": "/usr/local",
      "auto_detect_files": []
    }
  },
  "global_settings": {
    "auto_update_check": true,
    "update_interval_days": 7,
    "parallel_downloads": true,
    "max_parallel_jobs": 4,
    "backup_before_update": true,
    "log_level": "INFO"
  }
}
```

## Directory Structure

Batman organizes packages in a clean directory structure:

```
~/.batman/
├── config.json          # Configuration file
├── packages.json         # Package database
├── logs/                 # Log files
├── cache/               # Cache directory
├── backups/             # Package backups
└── packages/            # Installed packages
    ├── python/          # Python packages
    ├── node/            # Node.js packages
    └── rust/            # Rust packages (cargo installs to ~/.cargo/bin)
```

## Examples

### Python Development
```bash
cd my-python-project
batman -i requests flask numpy  # Auto-detects Python, installs via pip
batman -u --all                 # Updates all Python packages
```

### Node.js Development
```bash
cd my-node-project
batman -i express lodash        # Auto-detects Node.js, installs via npm
batman -i typescript --manager npm --save-dev  # Dev dependency
```

### System Administration
```bash
batman -i git curl wget --manager apt  # Install system tools
batman -u --all --manager apt          # Update system packages
```

### Mixed Environment
```bash
batman -i numpy --manager pip          # Python data science
batman -i express --manager npm        # Web server
batman -i postgresql --manager apt     # Database
batman -i ripgrep --manager cargo      # Rust tool
batman -i git --manager pacman         # System tool (Arch)
batman --list                          # See everything installed
```

## Supported Package Managers

| Manager | Status | Notes |
|---------|--------|-------|
| pip     | ✅ Full | Python packages from PyPI, supports version specification |
| npm     | ✅ Full | Node.js packages, local and global, supports version specification |
| apt     | ✅ Full | Debian/Ubuntu system packages |
| cargo   | ✅ Full | Rust packages from crates.io, supports version specification |
| pacman  | ✅ Full | Arch Linux packages (latest version only) |
| brew    | 🚧 Planned | macOS packages |
| yum/dnf | 🚧 Planned | RedHat/Fedora packages |

## Troubleshooting

### Common Issues

1. **Command not found**: Make sure Batman is in your PATH or use the full path
2. **Permission denied**: Some operations may require sudo (automatically handled for system packages)
3. **Manager not available**: Install the required package manager (e.g., npm, pip)

### Debug Mode
```bash
batman -i package_name --verbose  # Enable verbose logging
```

### Logs
Check logs in `~/.batman/logs/batman.log` for detailed information.

## Development

### Architecture

Batman follows a modular architecture:

- **Core**: Main orchestration logic (`src/core/`)
- **Managers**: Individual package manager implementations (`src/managers/`)
- **Database**: Package tracking and metadata (`src/database/`)
- **Utils**: Configuration and logging utilities (`src/utils/`)

### Adding a New Package Manager

1. Create a new manager class inheriting from `PackageManagerBase`
2. Implement all abstract methods
3. Add the manager to the `BatmanManager` initialization
4. Update configuration defaults

### Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/batman/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/batman/discussions)
- 📧 **Email**: batman-support@example.com

---

**Made with ❤️ for developers who are tired of remembering different package manager commands!** 