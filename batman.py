#!/usr/bin/env python3
"""
Batman Package Manager - Universal Package Management Tool
A unified package manager that can handle multiple package systems
"""

import argparse
import sys
import os
from pathlib import Path

from src.core.batman_manager import BatmanManager
from src.utils.logger import setup_logger
from src.utils.config import load_config

def main():
    """Main entry point for batman package manager"""
    
    # Setup logging
    logger = setup_logger()
    
    # Load configuration
    config = load_config()
    
    # Initialize Batman Manager
    batman = BatmanManager(config, logger)
    
    # Setup argument parser
    parser = argparse.ArgumentParser(
        description="Batman - Universal Package Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  batman -i numpy                      # Install latest numpy via pip
  batman -i numpy==1.21.0              # Install specific version
  batman -i numpy@1.21.0               # Alternative version syntax
  batman -i nodejs --manager npm       # Install nodejs via npm
  batman -i express@4.18.0 --manager npm  # Install specific npm version
  batman -i git --manager apt          # Install via apt
  batman -i curl --manager pacman      # Install via pacman (Arch Linux)
  batman -i serde --manager cargo      # Install Rust crate
  batman -u numpy                      # Update numpy
  batman -u --all                      # Update all packages
  batman --list                        # List all installed packages
  batman --search numpy                # Search for packages
        """
    )
    
    # Main commands
    parser.add_argument('-i', '--install', metavar='PACKAGE', 
                       help='Install a package (supports version: pkg==1.0.0 or pkg@1.0.0)')
    parser.add_argument('-u', '--update', metavar='PACKAGE', nargs='?', const='',
                       help='Update a package (or all packages with --all)')
    parser.add_argument('-r', '--remove', metavar='PACKAGE',
                       help='Remove a package')
    parser.add_argument('--search', metavar='QUERY',
                       help='Search for packages')
    parser.add_argument('--list', action='store_true',
                       help='List all installed packages')
    
    # Options
    parser.add_argument('--manager', choices=['auto', 'pip', 'npm', 'cargo', 'apt', 'pacman'],
                       default='auto', help='Specify package manager (default: auto-detect)')
    parser.add_argument('--version', metavar='VERSION',
                       help='Specify package version (alternative to pkg==version syntax)')
    parser.add_argument('--all', action='store_true',
                       help='Apply to all packages (used with update)')
    parser.add_argument('--force', action='store_true',
                       help='Force operation without confirmation')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without executing')
    
    args = parser.parse_args()
    
    # Set verbosity
    if args.verbose:
        logger.setLevel('DEBUG')
    
    try:
        # Execute commands
        if args.install:
            batman.install_package(args.install, args.manager, args.version, args.force, args.dry_run)
        elif args.update is not None:
            if args.all or args.update == '':
                batman.update_all_packages(args.force, args.dry_run)
            else:
                batman.update_package(args.update, args.manager, args.force, args.dry_run)
        elif args.remove:
            batman.remove_package(args.remove, args.manager, args.force, args.dry_run)
        elif args.search:
            batman.search_packages(args.search, args.manager)
        elif args.list:
            batman.list_packages(args.manager)
        else:
            parser.print_help()
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 