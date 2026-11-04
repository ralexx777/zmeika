[app]

# Название на экране телефона
title = Змейка

# Идентификатор приложения: org.example.zmeika
package.name = zmeika
package.domain = org.example

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
source.exclude_dirs = bin, .buildozer, build, .github

version = 1.0.0

# Kivy — единственная сторонняя зависимость, всё остальное из stdlib.
requirements = python3,kivy==2.3.1

# Телефон держим горизонтально, экран занимаем целиком.
orientation = landscape
fullscreen = 1

icon.filename = %(source.dir)s/icon.png

android.api = 34
android.minapi = 24
android.ndk = 25b
android.ndk_api = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = False

p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
