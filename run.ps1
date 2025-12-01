# Run script for Windows PowerShell
$ErrorActionPreference = 'Stop'

# Helper: choose a python command (py, python, python3)
function Get-PythonCmd {
	if (Get-Command py -ErrorAction SilentlyContinue) { return 'py' }
	if (Get-Command python -ErrorAction SilentlyContinue) { return 'python' }
	if (Get-Command python3 -ErrorAction SilentlyContinue) { return 'python3' }
	return $null
}

$pythonCmd = Get-PythonCmd
if (-not $pythonCmd) {
	Write-Host "No Python interpreter found. Please install Python 3.10+ and ensure 'py' or 'python' is on PATH." -ForegroundColor Red
	exit 1
}

# Create virtual environment if missing
if (-not (Test-Path ".\.venv")) {
	Write-Host "Creating virtual environment in .venv..."
	if ($pythonCmd -eq 'py') { & $pythonCmd -3 -m venv .venv } else { & $pythonCmd -m venv .venv }
}

# Temporarily allow script execution for this session so Activate.ps1 runs correctly
try {
	Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force | Out-Null
} catch {
	Write-Host "Could not set ExecutionPolicy (you're probably not running as admin). Continuing; Activation may still work." -ForegroundColor Yellow
}

# Activate virtual environment
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
	& ".\.venv\Scripts\Activate.ps1"
} else {
	Write-Host "Activation script not found. Ensure venv was created properly." -ForegroundColor Red
	exit 1
}

# Install/upgrade pip, then install requirements
Write-Host "Installing dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "Starting FastAPI server (uvicorn) ..."
python -m uvicorn app:app --reload

# Right-click → Run with PowerShell
# OR inside an elevated PowerShell session: .\run.ps1