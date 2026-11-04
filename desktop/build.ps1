# Пересборка настольной версии Zmeika.exe (Windows, Python 3.11+).
# Запуск: powershell -ExecutionPolicy Bypass -File desktop\build.ps1
# Для варианта «папка» замените --onefile на --onedir.

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

python -m pip install --upgrade pyinstaller

python -m PyInstaller --noconfirm --clean --onefile --windowed --name Zmeika `
    --icon "$root\desktop\icon.ico" `
    --distpath "$root\desktop\dist" `
    --workpath "$root\.build\pyi" `
    --specpath "$root\.build" `
    --paths "$root" `
    "$root\desktop\app.py"

if ($LASTEXITCODE -ne 0) { throw "PyInstaller завершился с ошибкой" }
Write-Host ""
Write-Host "Готово: desktop\dist\Zmeika.exe" -ForegroundColor Green
