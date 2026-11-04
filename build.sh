#!/usr/bin/env bash
# Сборка debug-APK локально: Linux, WSL2 или Docker-образ kivy/buildozer.
# Первый запуск скачивает Android SDK/NDK (~3 ГБ) и идёт 20–40 минут.
set -euo pipefail
cd "$(dirname "$0")"

python3 -m pip install --user --upgrade "buildozer==1.5.0" "cython==0.29.36"
buildozer -v android debug

echo
echo "Готово. APK лежит здесь:"
ls -lh bin/*.apk
