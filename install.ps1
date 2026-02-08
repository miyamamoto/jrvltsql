#Requires -Version 5.1
<#
.SYNOPSIS
    JLTSQL One-Command Installer
.DESCRIPTION
    Installs JLTSQL with all dependencies.
    Usage: irm https://raw.githubusercontent.com/miyamamoto/jrvltsql/master/install.ps1 | iex
.NOTES
    Requires: Windows, 32-bit Python 3.12, Git
#>

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"  # Speed up Invoke-WebRequest

# --- Configuration ---
$REPO_URL = "https://github.com/miyamamoto/jrvltsql.git"
$INSTALL_DIR = "$env:USERPROFILE\jrvltsql"
$PYTHON_VERSION = "3.12"
$PYTHON_DOWNLOAD_URL = "https://www.python.org/ftp/python/3.12.8/python-3.12.8.exe"

# --- Helper Functions ---
function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "  $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "  [OK] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "  [!!] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "  [NG] $Message" -ForegroundColor Red
}

function Write-Banner {
    Write-Host ""
    Write-Host "  ============================================" -ForegroundColor Blue
    Write-Host "    JLTSQL Installer" -ForegroundColor White
    Write-Host "    JRA-VAN DataLab / UmaConn -> SQL" -ForegroundColor DarkGray
    Write-Host "  ============================================" -ForegroundColor Blue
    Write-Host ""
}

# --- Main ---
Write-Banner

# Step 1: Check 32-bit Python
Write-Step "Step 1/7: Checking 32-bit Python $PYTHON_VERSION..."

$python32 = $null
$pythonCmd = $null

# Try py launcher with 32-bit flag
try {
    $ver = & py "-$PYTHON_VERSION-32" --version 2>&1
    if ($LASTEXITCODE -eq 0 -and $ver -match "Python 3\.12") {
        $python32 = "py -$PYTHON_VERSION-32"
        $pythonCmd = @("py", "-$PYTHON_VERSION-32")
        Write-Ok "Found: $ver (py launcher)"
    }
} catch {}

# Try common install paths
if (-not $python32) {
    $paths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312-32\python.exe",
        "C:\Python312-32\python.exe",
        "C:\Python312\python.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) {
            # Verify it's 32-bit
            $archCheck = & $p -c "import struct; print(struct.calcsize('P') * 8)" 2>&1
            if ($archCheck -eq "32") {
                $python32 = $p
                $pythonCmd = @($p)
                $ver = & $p --version 2>&1
                Write-Ok "Found: $ver at $p"
                break
            }
        }
    }
}

if (-not $python32) {
    Write-Fail "32-bit Python $PYTHON_VERSION not found."
    Write-Host ""
    Write-Host "  Please install Python $PYTHON_VERSION (32-bit):" -ForegroundColor Yellow
    Write-Host "    1. Download from: https://www.python.org/downloads/" -ForegroundColor White
    Write-Host "       Direct link: $PYTHON_DOWNLOAD_URL" -ForegroundColor DarkGray
    Write-Host "    2. Choose 'Windows installer (32-bit)'" -ForegroundColor White
    Write-Host "    3. Check 'Add Python to PATH' during install" -ForegroundColor White
    Write-Host "    4. Re-run this installer" -ForegroundColor White
    Write-Host ""

    $download = Read-Host "  Download Python now? (y/N)"
    if ($download -eq "y" -or $download -eq "Y") {
        Write-Step "Downloading Python $PYTHON_VERSION (32-bit)..."
        $installer = "$env:TEMP\python-3.12-32bit.exe"
        Invoke-WebRequest -Uri $PYTHON_DOWNLOAD_URL -OutFile $installer
        Write-Ok "Downloaded to $installer"
        Write-Host "  Starting installer... Please select '32-bit' and check 'Add to PATH'." -ForegroundColor Yellow
        Start-Process -FilePath $installer -Wait
        Write-Host ""
        Write-Warn "Please restart this installer after Python installation completes."
    }
    exit 1
}

# Step 2: Check Git
Write-Step "Step 2/7: Checking Git..."

try {
    $gitVer = & git --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Found: $gitVer"
    } else {
        throw "git not found"
    }
} catch {
    Write-Fail "Git not found."
    Write-Host "  Install from: https://git-scm.com/download/win" -ForegroundColor Yellow
    Write-Host "  Or: winget install Git.Git" -ForegroundColor DarkGray
    exit 1
}

# Step 3: Clone or update repository
Write-Step "Step 3/7: Setting up repository..."

if (Test-Path "$INSTALL_DIR\.git") {
    Write-Ok "Repository exists at $INSTALL_DIR"
    Push-Location $INSTALL_DIR
    try {
        & git pull --ff-only origin master 2>&1 | Out-Null
        Write-Ok "Updated to latest version"
    } catch {
        Write-Warn "Could not update (you may have local changes)"
    }
    Pop-Location
} else {
    Write-Host "  Cloning to $INSTALL_DIR..." -ForegroundColor DarkGray
    & git clone $REPO_URL $INSTALL_DIR 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Failed to clone repository"
        exit 1
    }
    Write-Ok "Cloned to $INSTALL_DIR"
}

# Step 4: Create virtual environment
Write-Step "Step 4/7: Creating virtual environment (32-bit)..."

$venvDir = "$INSTALL_DIR\venv32"

if (Test-Path "$venvDir\Scripts\python.exe") {
    # Verify existing venv is 32-bit
    $archCheck = & "$venvDir\Scripts\python.exe" -c "import struct; print(struct.calcsize('P') * 8)" 2>&1
    if ($archCheck -eq "32") {
        Write-Ok "Virtual environment exists (32-bit verified)"
    } else {
        Write-Warn "Existing venv is not 32-bit, recreating..."
        Remove-Item -Recurse -Force $venvDir
        & @pythonCmd -m venv $venvDir
        Write-Ok "Virtual environment created (32-bit)"
    }
} else {
    & @pythonCmd -m venv $venvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Failed to create virtual environment"
        exit 1
    }
    Write-Ok "Virtual environment created"
}

# Step 5: Install dependencies
Write-Step "Step 5/7: Installing dependencies..."

$pipExe = "$venvDir\Scripts\pip.exe"
$pythonExe = "$venvDir\Scripts\python.exe"

# Upgrade pip first
& $pythonExe -m pip install --upgrade pip 2>&1 | Out-Null

# Install in editable mode
Push-Location $INSTALL_DIR
& $pipExe install -e "." 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Failed to install dependencies"
    Pop-Location
    exit 1
}
Write-Ok "Dependencies installed"
Pop-Location

# Step 6: Setup config
Write-Step "Step 6/7: Setting up configuration..."

$configDir = "$INSTALL_DIR\config"
$configFile = "$configDir\config.yaml"
$configExample = "$configDir\config.yaml.example"

if (Test-Path $configFile) {
    Write-Ok "config.yaml already exists"
} elseif (Test-Path $configExample) {
    Copy-Item $configExample $configFile
    Write-Ok "Created config.yaml from template"
    Write-Warn "Edit $configFile to set your service keys"
} else {
    Write-Warn "config.yaml.example not found, run 'jltsql init' later"
}

# Create data and logs directories
foreach ($dir in @("$INSTALL_DIR\data", "$INSTALL_DIR\logs")) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# Step 7: Add to PATH
Write-Step "Step 7/7: Setting up PATH..."

$scriptsDir = "$venvDir\Scripts"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")

if ($userPath -notlike "*$scriptsDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$scriptsDir", "User")
    $env:Path = "$env:Path;$scriptsDir"
    Write-Ok "Added $scriptsDir to PATH"
    Write-Warn "Restart your terminal for PATH changes to take effect"
} else {
    Write-Ok "PATH already configured"
}

# Also add the install dir to PATH for convenience
if ($userPath -notlike "*$INSTALL_DIR*") {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$INSTALL_DIR", "User")
}

# --- Complete ---
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "    Installation Complete!" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Install directory: $INSTALL_DIR" -ForegroundColor White
Write-Host "  Python (32-bit):   $python32" -ForegroundColor White
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Yellow
Write-Host "    1. Restart your terminal (PATH update)" -ForegroundColor White
Write-Host "    2. Run quickstart (recommended):" -ForegroundColor White
Write-Host "       cd $INSTALL_DIR && quickstart.bat" -ForegroundColor Cyan
Write-Host "       -> Interactive setup: DB creation, data fetch, all-in-one" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Or manual setup:" -ForegroundColor Yellow
Write-Host "    1. Edit config: $configFile" -ForegroundColor White
Write-Host "    2. Run: jltsql init" -ForegroundColor White
Write-Host "    3. Run: jltsql fetch --from 20240101 --to 20241231 --spec RACE" -ForegroundColor White
Write-Host ""
Write-Host "  Commands:" -ForegroundColor Yellow
Write-Host "    jltsql version     Show version info" -ForegroundColor DarkGray
Write-Host "    jltsql update      Update to latest version" -ForegroundColor DarkGray
Write-Host "    jltsql --help      Show all commands" -ForegroundColor DarkGray
Write-Host ""
