#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Точка входа настольной сборки: тот же интерфейс, что в snake_tk.py.

Нужна только для PyInstaller: при сборке код запускается из временной
папки, поэтому файл рекорда кладём рядом с exe, а не рядом с модулем.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import snake  # noqa: E402

if getattr(sys, "frozen", False):
    # exe: рекорд рядом с исполняемым файлом
    snake.SCORE_FILE = Path(sys.executable).resolve().parent / "snake_highscore.txt"
else:
    # запуск из исходников: рекорд в корне проекта
    snake.SCORE_FILE = ROOT / "snake_highscore.txt"

import snake_tk  # noqa: E402


def main() -> int:
    return snake_tk.main()


if __name__ == "__main__":
    sys.exit(main())
