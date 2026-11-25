<# setup_env.ps1 — Recreate the NLP_Project conda environment from scratch. #>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$CONDA = "C:\ProgramData\miniconda3\condabin\conda.bat"
$ENV_NAME = "NLP_Project"
$REPO_ROOT = Split-Path -Parent $PSScriptRoot   # one level up from scripts/

Write-Host "=== Creating conda env '$ENV_NAME' (Python 3.11) ===" -ForegroundColor Cyan
& $CONDA create -n $ENV_NAME python=3.11 -y

Write-Host "`n=== Installing PyTorch (CUDA 12.6 — cu121 maxes out at 2.5.1, accelerate needs >=2.6.0) ===" -ForegroundColor Cyan
& $CONDA run -n $ENV_NAME --no-capture-output `
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

Write-Host "`n=== Installing core requirements ===" -ForegroundColor Cyan
& $CONDA run -n $ENV_NAME --no-capture-output `
    pip install -r "$REPO_ROOT\requirements-core.txt"

Write-Host "`n=== Installing ML requirements ===" -ForegroundColor Cyan
& $CONDA run -n $ENV_NAME --no-capture-output `
    pip install -r "$REPO_ROOT\requirements-ml.txt"

Write-Host "`n=== Verifying torch + CUDA ===" -ForegroundColor Cyan
& $CONDA run -n $ENV_NAME --no-capture-output `
    python -c "import torch; print(f'torch {torch.__version__}  CUDA available: {torch.cuda.is_available()}')"

Write-Host "`n=== Running smoke tests ===" -ForegroundColor Cyan
& $CONDA run -n $ENV_NAME --no-capture-output pytest "$REPO_ROOT\tests" -v

Write-Host "`n=== Done! ===" -ForegroundColor Green
