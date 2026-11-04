# Змейка для Android

Та же игра, что в `snake.py`, но с сенсорным управлением: логика (`snake.py`)
не менялась, сверху добавлен интерфейс на Kivy и сборка в APK.

![Вид игры](preview.png)

*Скриншот Kivy-версии, запущенной на десктопе в окне 1000×460 — примерно
такое соотношение сторон у телефона в горизонтальной ориентации.*

```
android/
├── main.py               интерфейс: отрисовка, свайпы, пауза, рекорд
├── snake.py              та же логика игры, что и в консольной версии
├── buildozer.spec        параметры APK: имя, иконка, ориентация, SDK/NDK
├── icon.png              иконка приложения
├── build.sh              сборка на Linux/WSL2
└── .github/workflows/    сборка APK в GitHub Actions (без своего тулчейна)
```

## Проверить на компьютере

```
python -m pip install "kivy==2.3.1"
python main.py
```

Управление: стрелки/WASD, пробел — пауза, Esc — пауза/выход.
На телефоне: свайп — поворот, касание — пауза/продолжить, кнопка «назад» — пауза.

## Собрать APK

Buildozer (то, что превращает Python+Kivy в APK) работает только на Linux.
На Windows есть три пути — по возрастанию удобства.

### 1. Docker (проще всего на Windows)

Нужен [Docker Desktop](https://www.docker.com/products/docker-desktop/).
Из папки `android`:

```
docker run --rm -v "%cd%":/home/user/hostcwd kivy/buildozer -v android debug
```

Готовый файл: `bin/zmeika-1.0.0-arm64-v8a_armeabi-v7a-debug.apk`.

### 2. WSL2 или Linux

```
wsl --install -d Ubuntu      # один раз, если WSL2 ещё нет
bash build.sh
```

### 3. GitHub Actions — вообще без установки тулчейна

1. Завести пустой репозиторий на GitHub.
2. Залить туда **содержимое папки `android`** (чтобы `buildozer.spec` был в корне).
3. Открыть Actions → «Собрать APK» → Run workflow.
4. Через 20–40 минут скачать `zmeika-debug-apk` из раздела Artifacts.

Эта сборка уже настроена: JDK 17, Android SDK/NDK, buildozer и кеш
устанавливаются в workflow автоматически.

> Первая сборка всегда долгая: скачивается Android SDK + NDK (~3 ГБ) и
> компилируется Python для Android. Повторные сборки идут в разы быстрее.

## Установить на телефон

1. Перекинуть APK на телефон (кабель, облако, Telegram «себе»).
2. Открыть файл и разрешить установку из этого источника, если телефон спросит.
3. Или по кабелю с включённой отладкой: `adb install bin/*.apk`.

APK отладочный (debug), подписан отладочным ключом — для игры на своём
телефоне этого достаточно; для Google Play нужен release-ключ и
`buildozer android release`.

## Если что-то менять

- Скорость, очки, правила — в `snake.py` (класс `Game`), он общий с десктопом.
- Размер поля — `GameWidget._pick_grid()` в `main.py`: число клеток
  подбирается под экран (целевой размер клетки — `dp(22)`), с ограничениями
  18–34 по ширине и 10–24 по высоте.
- Цвета — константы `BG`, `BOARD`, `GRID`, `HEAD`, `BODY`, `FOOD` в `main.py`.
- Версия Kivy — `requirements` в `buildozer.spec`.
