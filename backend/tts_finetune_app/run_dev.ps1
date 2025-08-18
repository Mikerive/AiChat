# PowerShell script to activate conda env and run training (Windows)
param([string[]]$Args)

$envName = "tts_finetune_app"

if (Get-Command conda -ErrorAction SilentlyContinue) {
    & conda activate $envName
} else {
    Write-Host "conda not found on PATH. Activate the $envName env manually."
}

python backend/tts_finetune_app/train_voice.py $Args