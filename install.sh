#!/bin/bash

# Batman Package Manager Installation Script
# This script installs Batman and creates a global 'batman' command

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Batman ASCII Art
echo -e "${PURPLE}"
cat << "EOF"
    ____        __                         
   / __ )____ _/ /_____ ___  ____ _____    
  / __  / __ `/ __/ __ `__ \/ __ `/ __ \   
 / /_/ / /_/ / /_/ / / / / / /_/ / / / /   
/_____/\__,_/\__/_/ /_/ /_/\__,_/_/ /_/    
                                          
Universal Package Manager Installation
EOF
echo -e "${NC}"

# Functions
print_step() {
    echo -e "\n${BLUE}==>${NC} ${CYAN}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BATMAN_PATH="$SCRIPT_DIR/batman.py"

print_step "Starting Batman Package Manager Installation"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_warning "Running as root. This is not recommended for development."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check prerequisites
print_step "Checking prerequisites"

# Check Python 3
if check_command python3; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    print_success "Python 3 found: $PYTHON_VERSION"
    PYTHON_CMD="python3"
elif check_command python; then
    PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
    if [[ $PYTHON_VERSION == 3.* ]]; then
        print_success "Python 3 found: $PYTHON_VERSION"
        PYTHON_CMD="python"
    else
        print_error "Python 3 is required, but found Python $PYTHON_VERSION"
        exit 1
    fi
else
    print_error "Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check pip
if check_command pip3; then
    PIP_CMD="pip3"
elif check_command pip; then
    PIP_CMD="pip"
else
    print_error "pip is not installed. Please install pip first."
    exit 1
fi
print_success "pip found: $PIP_CMD"

# Check if batman.py exists
if [[ ! -f "$BATMAN_PATH" ]]; then
    print_error "batman.py not found in $SCRIPT_DIR"
    exit 1
fi
print_success "Batman source found: $BATMAN_PATH"

# Install Python dependencies
print_step "Installing Python dependencies"
if [[ -f "$SCRIPT_DIR/requirements.txt" ]]; then
    if $PIP_CMD install --user -r "$SCRIPT_DIR/requirements.txt"; then
        print_success "Dependencies installed successfully"
    else
        print_error "Failed to install dependencies"
        exit 1
    fi
else
    print_warning "requirements.txt not found, skipping dependency installation"
fi

# Make batman.py executable
print_step "Making batman.py executable"
chmod +x "$BATMAN_PATH"
print_success "batman.py is now executable"

# Create Batman configuration directory
print_step "Setting up Batman configuration directory"
BATMAN_CONFIG_DIR="$HOME/.batman"
mkdir -p "$BATMAN_CONFIG_DIR/logs"
mkdir -p "$BATMAN_CONFIG_DIR/cache" 
mkdir -p "$BATMAN_CONFIG_DIR/backups"
mkdir -p "$BATMAN_CONFIG_DIR/packages"
print_success "Configuration directory created: $BATMAN_CONFIG_DIR"

# Determine installation method
print_step "Setting up global batman command"

# Option 1: Try to create symlink in /usr/local/bin (preferred)
if [[ -w "/usr/local/bin" ]] || sudo -n true 2>/dev/null; then
    INSTALL_PATH="/usr/local/bin/batman"
    if [[ -f "$INSTALL_PATH" ]]; then
        print_warning "Batman already exists at $INSTALL_PATH"
        read -p "Overwrite existing installation? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo rm -f "$INSTALL_PATH"
        else
            print_warning "Skipping global installation"
            INSTALL_PATH=""
        fi
    fi
    
    if [[ -n "$INSTALL_PATH" ]]; then
        if sudo ln -sf "$BATMAN_PATH" "$INSTALL_PATH"; then
            print_success "Global batman command created: $INSTALL_PATH"
            GLOBAL_INSTALL=true
        else
            print_warning "Failed to create global symlink, falling back to user installation"
            GLOBAL_INSTALL=false
        fi
    else
        GLOBAL_INSTALL=false
    fi
else
    GLOBAL_INSTALL=false
fi

# Option 2: Create symlink in user's local bin
if [[ "$GLOBAL_INSTALL" != true ]]; then
    USER_BIN_DIR="$HOME/.local/bin"
    mkdir -p "$USER_BIN_DIR"
    INSTALL_PATH="$USER_BIN_DIR/batman"
    
    if ln -sf "$BATMAN_PATH" "$INSTALL_PATH"; then
        print_success "User batman command created: $INSTALL_PATH"
        
        # Check if user's bin is in PATH
        if [[ ":$PATH:" != *":$USER_BIN_DIR:"* ]]; then
            print_warning "$USER_BIN_DIR is not in your PATH"
            ADD_TO_PATH=true
        fi
    else
        print_error "Failed to create user symlink"
        exit 1
    fi
fi

# Add to shell configuration files
if [[ "$ADD_TO_PATH" == true ]]; then
    print_step "Adding $USER_BIN_DIR to PATH"
    
    # Detect shell and add to appropriate config file
    CURRENT_SHELL=$(basename "$SHELL")
    
    case "$CURRENT_SHELL" in
        "bash")
            SHELL_CONFIG="$HOME/.bashrc"
            if [[ -f "$HOME/.bash_profile" ]]; then
                SHELL_CONFIG="$HOME/.bash_profile"
            fi
            ;;
        "zsh")
            SHELL_CONFIG="$HOME/.zshrc"
            ;;
        "fish")
            SHELL_CONFIG="$HOME/.config/fish/config.fish"
            mkdir -p "$(dirname "$SHELL_CONFIG")"
            ;;
        *)
            SHELL_CONFIG="$HOME/.profile"
            ;;
    esac
    
    # Add PATH export line
    if [[ "$CURRENT_SHELL" == "fish" ]]; then
        PATH_LINE="set -gx PATH \$PATH $USER_BIN_DIR"
    else
        PATH_LINE="export PATH=\"\$PATH:$USER_BIN_DIR\""
    fi
    
    if [[ -f "$SHELL_CONFIG" ]] && grep -q "$USER_BIN_DIR" "$SHELL_CONFIG"; then
        print_warning "PATH already contains $USER_BIN_DIR in $SHELL_CONFIG"
    else
        echo "" >> "$SHELL_CONFIG"
        echo "# Added by Batman Package Manager installer" >> "$SHELL_CONFIG"
        echo "$PATH_LINE" >> "$SHELL_CONFIG"
        print_success "Added $USER_BIN_DIR to PATH in $SHELL_CONFIG"
        print_warning "Please restart your shell or run: source $SHELL_CONFIG"
    fi
fi

# Create alias for current session
print_step "Creating alias for current session"
alias batman="$BATMAN_PATH"
print_success "Alias 'batman' created for current session"

# Test installation
print_step "Testing installation"
if "$BATMAN_PATH" --help >/dev/null 2>&1; then
    print_success "Batman installation test passed"
else
    print_error "Batman installation test failed"
    exit 1
fi

# Summary
echo -e "\n${GREEN}🦇 Batman Package Manager Installation Complete! 🦇${NC}\n"

echo -e "${CYAN}Installation Summary:${NC}"
echo -e "  • Batman installed at: ${YELLOW}$BATMAN_PATH${NC}"
if [[ -n "$INSTALL_PATH" ]]; then
    echo -e "  • Global command: ${YELLOW}$INSTALL_PATH${NC}"
fi
echo -e "  • Configuration directory: ${YELLOW}$BATMAN_CONFIG_DIR${NC}"
echo -e "  • Shell: ${YELLOW}$CURRENT_SHELL${NC}"

echo -e "\n${CYAN}Usage Examples:${NC}"
echo -e "  batman -i numpy                    # Install latest numpy"
echo -e "  batman -i numpy==1.21.0            # Install specific version"
echo -e "  batman -i express --manager npm    # Install via npm"
echo -e "  batman --list                      # List installed packages"
echo -e "  batman --help                      # Show all options"

echo -e "\n${CYAN}Next Steps:${NC}"
if [[ "$ADD_TO_PATH" == true ]]; then
    echo -e "  1. Restart your shell or run: ${YELLOW}source $SHELL_CONFIG${NC}"
    echo -e "  2. Test with: ${YELLOW}batman --help${NC}"
else
    echo -e "  1. Test with: ${YELLOW}batman --help${NC}"
fi

echo -e "\n${PURPLE}Happy package managing! 🚀${NC}" 