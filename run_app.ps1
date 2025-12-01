# ---------------------------
# Windows PowerShell Script: Setup & Run FastAPI App
# ---------------------------

# --- CONFIGURATION ---
$ProjectFolder = "affilate autopost -3.0 - apply different shape and color"

Write-Host "`n=== Starting FastAPI App Setup ===`n"

# --- Navigate to project directory ---
if (-Not (Test-Path $ProjectFolder)) {
    Write-Host "❌ Project folder not found: $ProjectFolder"
    exit 1
}
Set-Location $ProjectFolder
Write-Host "📂 Working directory: $ProjectFolder`n"

# --- Create virtual environment if missing ---
if (-Not (Test-Path ".\.venv")) {
    Write-Host "🐍 Creating virtual environment..."
    python -m venv .venv
} else {
    Write-Host "✅ Virtual environment already exists."
}

# --- Activate virtual environment ---
Write-Host "⚡ Activating virtual environment..."
& ".\.venv\Scripts\Activate.ps1"

# --- Upgrade pip ---
Write-Host "⬆️  Upgrading pip..."
python -m pip install --upgrade pip

# --- Install dependencies ---
Write-Host "📦 Installing required packages..."
python -m pip install --upgrade fastapi "uvicorn[standard]" python-dotenv gspread pillow requests

# --- Start the FastAPI app ---
Write-Host "`n🚀 Starting FastAPI app..."
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload

Write-Host "`n✅ Server running at: http://127.0.0.1:8000"
