# Creates training\.venv: PyTorch with CUDA (for the NVIDIA GPU) + Ultralytics.
# Separate from backend\.venv on purpose, so the backend keeps its small CPU build.
# Download is about 3 GB; disk use about 5 GB. Run from the repo root:
#
#   powershell -ExecutionPolicy Bypass -File training\setup_training.ps1
#
# Needs: Python 3.12 and a recent NVIDIA driver (check with: nvidia-smi).

$ErrorActionPreference = "Stop"
$venv = Join-Path $PSScriptRoot ".venv"
$python = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Creating $venv"
    py -3.12 -m venv $venv
}
& $python -m pip install --upgrade pip
& $python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
& $python -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")

& $python -c "import torch; ok = torch.cuda.is_available(); print('PyTorch', torch.__version__, '| GPU:', torch.cuda.get_device_name(0) if ok else 'NOT FOUND')"
