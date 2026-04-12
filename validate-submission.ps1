#
# validate-submission.ps1 - OpenEnv Submission Validator (Windows PowerShell)
#
# Checks that your HF Space is live, Docker image builds, and openenv validate passes.
#
# Prerequisites:
#   - Docker:       https://docs.docker.com/get-docker/
#   - openenv-core: pip install openenv-core
#   - PowerShell 3.0+
#
# Usage:
#   .\validate-submission.ps1 -PingUrl "https://your-space.hf.space" [-RepoDir "."]
#
# Example:
#   .\validate-submission.ps1 -PingUrl "https://Kaustubhd365-code-review-env.hf.space"
#   .\validate-submission.ps1 -PingUrl "https://Kaustubhd365-code-review-env.hf.space" -RepoDir "C:\Users\Kaustubh\OneDrive\Desktop\code-review-env"
#

param(
    [string]$PingUrl = "",
    [string]$RepoDir = "."
)

function Write-Pass {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] " -NoNewline
    Write-Host "PASSED" -ForegroundColor Green -NoNewline
    Write-Host " -- $Message"
}

function Write-Fail {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] " -NoNewline
    Write-Host "FAILED" -ForegroundColor Red -NoNewline
    Write-Host " -- $Message"
}

function Write-Hint {
    param([string]$Message)
    Write-Host "  " -NoNewline
    Write-Host "Hint:" -ForegroundColor Yellow -NoNewline
    Write-Host " $Message"
}

function Write-Step {
    param([string]$Message)
    Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] " -NoNewline
    Write-Host $Message -ForegroundColor Cyan
}

function Stop-Validation {
    param([string]$Step)
    Write-Host "`n"
    Write-Host "Validation stopped at $Step. Fix the above before continuing." -ForegroundColor Red
    exit 1
}

# Validate arguments
if (-not $PingUrl) {
    Write-Host "Usage: .\validate-submission.ps1 -PingUrl <url> [-RepoDir <path>]`n"
    Write-Host "  -PingUrl   Your HuggingFace Space URL (e.g. https://your-space.hf.space)"
    Write-Host "  -RepoDir   Path to your repo (default: current directory)"
    exit 1
}

# Validate repo directory
$RepoDir = Resolve-Path $RepoDir -ErrorAction SilentlyContinue
if (-not $RepoDir) {
    Write-Fail "directory '$RepoDir' not found"
    exit 1
}

# Remove trailing slash
$PingUrl = $PingUrl.TrimEnd("/")
$PASS = 0

Write-Host "`n"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  OpenEnv Submission Validator (Windows)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Repo:     $RepoDir"
Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Ping URL: $PingUrl"

# ============================================================================
# Step 1: Ping HF Space
# ============================================================================
Write-Step "Step 1/3: Pinging HF Space ($PingUrl/reset)..."

try {
    $response = Invoke-WebRequest -Uri "$PingUrl/reset" `
        -Method POST `
        -Headers @{"Content-Type"="application/json"} `
        -Body '{}' `
        -TimeoutSec 30 `
        -ErrorAction Stop
    
    if ($response.StatusCode -eq 200) {
        Write-Pass "HF Space is live and responds to /reset"
        $PASS++
    } else {
        Write-Fail "HF Space /reset returned HTTP $($response.StatusCode) (expected 200)"
        Write-Hint "Make sure your Space is running and the URL is correct."
        Stop-Validation "Step 1"
    }
} catch {
    Write-Fail "HF Space not reachable (connection failed or timed out)"
    Write-Hint "Check your network connection and that the Space is running."
    Write-Hint "Try in PowerShell: Invoke-WebRequest -Uri '$PingUrl/reset' -Method POST"
    Stop-Validation "Step 1"
}

# ============================================================================
# Step 2: Docker Build
# ============================================================================
Write-Step "Step 2/3: Running docker build..."

# Check if Docker is installed
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Fail "docker command not found"
    Write-Hint "Install Docker: https://docs.docker.com/get-docker/"
    Stop-Validation "Step 2"
}

# Find Dockerfile
$DockerFile = Join-Path $RepoDir "Dockerfile"
$DockerContext = $RepoDir

if (-not (Test-Path $DockerFile)) {
    $AltPath = Join-Path $RepoDir "server" "Dockerfile"
    if (Test-Path $AltPath) {
        $DockerContext = Join-Path $RepoDir "server"
        $DockerFile = $AltPath
    } else {
        Write-Fail "No Dockerfile found in repo root or server/ directory"
        Stop-Validation "Step 2"
    }
}

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Found Dockerfile in $DockerContext"

# Run docker build
try {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Building Docker image (timeout: 600s)..."
    $output = & docker build $DockerContext 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "Docker build succeeded"
        $PASS++
    } else {
        Write-Fail "Docker build failed"
        $output | Select-Object -Last 20 | ForEach-Object { Write-Host $_ }
        Stop-Validation "Step 2"
    }
} catch {
    Write-Fail "Docker build failed: $_"
    Stop-Validation "Step 2"
}

# ============================================================================
# Step 3: OpenEnv Validate
# ============================================================================
Write-Step "Step 3/3: Running openenv validate..."

# Check if openenv is installed
if (-not (Get-Command openenv -ErrorAction SilentlyContinue)) {
    Write-Fail "openenv command not found"
    Write-Hint "Install it: pip install openenv-core"
    Write-Hint "Or use: python -m openenv_core validate $RepoDir/openenv.yaml"
    Stop-Validation "Step 3"
}

# Run openenv validate
try {
    Push-Location $RepoDir
    $output = & openenv validate 2>&1
    Pop-Location
    
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "openenv validate passed"
        if ($output) { Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $output" }
        $PASS++
    } else {
        Write-Fail "openenv validate failed"
        $output | ForEach-Object { Write-Host $_ }
        Stop-Validation "Step 3"
    }
} catch {
    Write-Fail "openenv validate failed: $_"
    Write-Hint "Try: python -m openenv_core validate $RepoDir/openenv.yaml"
    Stop-Validation "Step 3"
}

# ============================================================================
# Success
# ============================================================================
Write-Host "`n"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All 3/3 checks passed!" -ForegroundColor Green
Write-Host "  Your submission is ready to submit." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`n"

exit 0