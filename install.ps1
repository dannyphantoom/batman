# Batman Package Manager Installation Script for Windows
# This script installs Batman and creates a global 'batman' command

param(
    [switch]$ForceGlobal,
    [switch]$UserOnly
)

# Set error action preference
$ErrorActionPreference = "Stop"

# ASCII Art
Write-Host @"
    ____        __                         
   / __ )____ _/ /_____ ___  ____ _____    
  / __  / __ `/ __/ __ `__ \/ __ `/ __ \   
 / /_/ / /_/ / /_/ / / / / / /_/ / / / /   
/_____/\__,_/\__/_/ /_/ /_/\__,_/_/ /_/    
                                          
Universal Package Manager Installation (Windows)
"@ -ForegroundColor Magenta

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> " -ForegroundColor Blue -NoNewline
    Write-Host $Message -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠ " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ " -ForegroundColor Red -NoNewline
    Write-Host $Message
}

function Test-CommandExists {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatmanPath = Join-Path $ScriptDir "batman.py"

Write-Step "Starting Batman Package Manager Installation"

# Check if running as administrator
$IsAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($IsAdmin -and -not $ForceGlobal) {
    Write-Warning "Running as administrator. Use -ForceGlobal to install globally or run without admin privileges."
}

# Check prerequisites
Write-Step "Checking prerequisites"

# Check Python 3
$PythonCmd = $null
if (Test-CommandExists "python") {
    $PythonVersion = & python --version 2>&1
    if ($PythonVersion -match "Python 3\.") {
        Write-Success "Python 3 found: $PythonVersion"
        $PythonCmd = "python"
    }
    else {
        Write-Error "Python 3 is required, but found: $PythonVersion"
        exit 1
    }
}
elseif (Test-CommandExists "python3") {
    $PythonVersion = & python3 --version 2>&1
    Write-Success "Python 3 found: $PythonVersion"
    $PythonCmd = "python3"
}
else {
    Write-Error "Python 3 is not installed. Please install Python 3 from https://python.org"
    exit 1
}

# Check pip
$PipCmd = $null
if (Test-CommandExists "pip") {
    $PipCmd = "pip"
}
elseif (Test-CommandExists "pip3") {
    $PipCmd = "pip3"
}
else {
    Write-Error "pip is not installed. Please install pip first."
    exit 1
}
Write-Success "pip found: $PipCmd"

# Check if batman.py exists
if (-not (Test-Path $BatmanPath)) {
    Write-Error "batman.py not found in $ScriptDir"
    exit 1
}
Write-Success "Batman source found: $BatmanPath"

# Install Python dependencies
Write-Step "Installing Python dependencies"
$RequirementsPath = Join-Path $ScriptDir "requirements.txt"
if (Test-Path $RequirementsPath) {
    try {
        & $PipCmd install --user -r $RequirementsPath 2>$null
        Write-Success "Dependencies installed successfully (user install)"
    }
    catch {
        Write-Warning "User installation failed, trying alternative methods..."
        
        # Check if it's the externally-managed-environment error
        $ErrorOutput = & $PipCmd install --user -r $RequirementsPath 2>&1 | Out-String
        if ($ErrorOutput -match "externally-managed-environment") {
            Write-Warning "Detected externally-managed-environment (PEP 668)"
            Write-Host "`nChoose installation method:" -ForegroundColor Cyan
            Write-Host "  1) Use --break-system-packages (override system protection)"
            Write-Host "  2) Create a virtual environment (recommended)" 
            Write-Host "  3) Skip dependency installation (Batman uses only standard library)"
            
            $Choice = Read-Host "Enter choice (1/2/3)"
            
            switch ($Choice) {
                "1" {
                    Write-Step "Installing with --break-system-packages"
                    try {
                        & $PipCmd install --user --break-system-packages -r $RequirementsPath
                        Write-Success "Dependencies installed successfully (system packages override)"
                    }
                    catch {
                        Write-Error "Failed to install dependencies even with --break-system-packages"
                        exit 1
                    }
                }
                "2" {
                    Write-Step "Creating virtual environment"
                    $VenvDir = Join-Path $ScriptDir ".venv"
                    
                    try {
                        & $PythonCmd -m venv $VenvDir
                        Write-Success "Virtual environment created: $VenvDir"
                        
                        # Install dependencies in venv
                        $VenvPip = Join-Path $VenvDir "Scripts\pip.exe"
                        & $VenvPip install -r $RequirementsPath
                        Write-Success "Dependencies installed in virtual environment"
                        
                        # Update Python command to use venv
                        $PythonCmd = Join-Path $VenvDir "Scripts\python.exe"
                        
                        # Create wrapper batch file that uses venv
                        $WrapperPath = Join-Path $ScriptDir "batman_wrapper.bat"
                        $WrapperContent = @"
@echo off
"$PythonCmd" "$BatmanPath" %*
"@
                        Set-Content -Path $WrapperPath -Value $WrapperContent
                        $BatmanPath = $WrapperPath
                        Write-Success "Created wrapper script for virtual environment"
                    }
                    catch {
                        Write-Error "Failed to create or setup virtual environment"
                        exit 1
                    }
                }
                "3" {
                    Write-Warning "Skipping dependency installation"
                    Write-Warning "Batman should work with standard library only"
                }
                default {
                    Write-Error "Invalid choice. Exiting."
                    exit 1
                }
            }
        }
        else {
            Write-Error "Failed to install dependencies for unknown reason"
            Write-Warning "You can try installing dependencies manually later"
        }
    }
}
else {
    Write-Warning "requirements.txt not found, skipping dependency installation"
}

# Create Batman configuration directory
Write-Step "Setting up Batman configuration directory"
$BatmanConfigDir = Join-Path $env:USERPROFILE ".batman"
$null = New-Item -ItemType Directory -Force -Path (Join-Path $BatmanConfigDir "logs")
$null = New-Item -ItemType Directory -Force -Path (Join-Path $BatmanConfigDir "cache")
$null = New-Item -ItemType Directory -Force -Path (Join-Path $BatmanConfigDir "backups")
$null = New-Item -ItemType Directory -Force -Path (Join-Path $BatmanConfigDir "packages")
Write-Success "Configuration directory created: $BatmanConfigDir"

# Create batch file wrapper
Write-Step "Creating Batman command wrapper"

$BatchContent = @"
@echo off
"$PythonCmd" "$BatmanPath" %*
"@

# Determine installation location
if ($ForceGlobal -or ($IsAdmin -and -not $UserOnly)) {
    # Global installation
    $InstallDir = Join-Path $env:ProgramFiles "Batman"
    $BatchPath = Join-Path $InstallDir "batman.bat"
    
    Write-Step "Installing globally to $InstallDir"
    
    try {
        $null = New-Item -ItemType Directory -Force -Path $InstallDir
        Set-Content -Path $BatchPath -Value $BatchContent
        Write-Success "Global batman command created: $BatchPath"
        
        # Add to system PATH if not already there
        $SystemPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
        if ($SystemPath -notlike "*$InstallDir*") {
            Write-Step "Adding $InstallDir to system PATH"
            [Environment]::SetEnvironmentVariable("Path", "$SystemPath;$InstallDir", "Machine")
            Write-Success "Added to system PATH"
            Write-Warning "Please restart your command prompt or PowerShell to use the batman command"
        }
        
        $GlobalInstall = $true
    }
    catch {
        Write-Warning "Failed to install globally, falling back to user installation"
        $GlobalInstall = $false
    }
}
else {
    $GlobalInstall = $false
}

# User installation
if (-not $GlobalInstall) {
    $UserBinDir = Join-Path $env:USERPROFILE ".local\bin"
    $BatchPath = Join-Path $UserBinDir "batman.bat"
    
    Write-Step "Installing for current user to $UserBinDir"
    
    $null = New-Item -ItemType Directory -Force -Path $UserBinDir
    Set-Content -Path $BatchPath -Value $BatchContent
    Write-Success "User batman command created: $BatchPath"
    
    # Add to user PATH if not already there
    $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($UserPath -notlike "*$UserBinDir*") {
        Write-Step "Adding $UserBinDir to user PATH"
        if ($UserPath) {
            [Environment]::SetEnvironmentVariable("Path", "$UserPath;$UserBinDir", "User")
        }
        else {
            [Environment]::SetEnvironmentVariable("Path", $UserBinDir, "User")
        }
        Write-Success "Added to user PATH"
        Write-Warning "Please restart your command prompt or PowerShell to use the batman command"
    }
}

# Test installation
Write-Step "Testing installation"
try {
    & $PythonCmd $BatmanPath --help | Out-Null
    Write-Success "Batman installation test passed"
}
catch {
    Write-Error "Batman installation test failed"
    exit 1
}

# Summary
Write-Host "`n🦇 Batman Package Manager Installation Complete! 🦇`n" -ForegroundColor Green

Write-Host "Installation Summary:" -ForegroundColor Cyan
Write-Host "  • Batman installed at: " -NoNewline
Write-Host $BatmanPath -ForegroundColor Yellow
Write-Host "  • Command wrapper: " -NoNewline
Write-Host $BatchPath -ForegroundColor Yellow
Write-Host "  • Configuration directory: " -NoNewline
Write-Host $BatmanConfigDir -ForegroundColor Yellow

Write-Host "`nUsage Examples:" -ForegroundColor Cyan
Write-Host "  batman -i numpy                    # Install latest numpy"
Write-Host "  batman -i numpy==1.21.0            # Install specific version"
Write-Host "  batman -i express --manager npm    # Install via npm"
Write-Host "  batman --list                      # List installed packages"
Write-Host "  batman --help                      # Show all options"

Write-Host "`nNext Steps:" -ForegroundColor Cyan
Write-Host "  1. Restart your command prompt or PowerShell"
Write-Host "  2. Test with: " -NoNewline
Write-Host "batman --help" -ForegroundColor Yellow

Write-Host "`nHappy package managing! 🚀" -ForegroundColor Magenta 