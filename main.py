#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Змейка для Android — Kivy-версия с сенсорным управлением.

Логика игры взята из snake.py (тот же класс Game), здесь только отрисовка
и ввод. Запускается и на компьютере, и на телефоне:

    python main.py                          # проверить на десктопе
    buildozer -v android debug              # собрать APK (Linux/WSL/Docker)
    см. README.md — там же сборка без установки тулчейна (GitHub Actions)

Управление на телефоне:
    свайп в любую сторону — поворот,
    касание — пауза / продолжить,
    касание после проигрыша — новая игра,
    кнопка «назад» — пауза.
"""

from __future__ import annotations

import json
import os

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from snake import Game

# --------------------------------------------------------------------------- #
#  Палитра и геометрия
# --------------------------------------------------------------------------- #

BG = (0.051, 0.067, 0.090, 1)
BOARD = (0.059, 0.086, 0.125, 1)
GRID = (0.102, 0.141, 0.196, 1)
HEAD = (0.714, 1.000, 0.369, 1)
BODY = (0.239, 0.863, 0.518, 1)
FOOD = (1.000, 0.302, 0.427, 1)
TEXT = (0.902, 0.929, 0.953, 1)
MUTED = (0.545, 0.596, 0.647, 1)

# Направление змейки в координатах экрана (ось Y смотрит вверх).
SCREEN_VECTORS = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}

HUD_HEIGHT = dp(44)


class GameWidget(Widget):
    """Игровое поле: рисует змейку и принимает свайпы."""

    TAP_THRESHOLD = 16  # dp: меньше — считаем касанием, больше — свайпом

    def __init__(self, app: "SnakeApp", **kwargs) -> None:
        super().__init__(**kwargs)
        self.app = app
        self.cols, self.rows = self._pick_grid()
        self.game = Game(self.cols, self.rows)
        self.state = "running"  # running | paused | over
        self.info: Label | None = None
        self._event = None
        self._touch_start = None

        self.bind(size=self._on_size, pos=self._on_pos)
        self.redraw()
        self.schedule()

    @staticmethod
    def _pick_grid() -> tuple[int, int]:
        """Подогнать число клеток под экран, чтобы поле занимало его целиком.

        Клетка должна быть примерно одного размера по обеим осям, поэтому
        на широком экране телефона поле получается длинным и невысоким,
        а на квадратном — компактным.
        """
        target = dp(22)
        avail_w = Window.width
        avail_h = max(dp(160), Window.height - HUD_HEIGHT)
        cols = int(max(18, min(34, avail_w // target)))
        rows = int(max(10, min(24, avail_h // target)))
        return cols, rows

    # -- таймер ------------------------------------------------------------- #

    def schedule(self) -> None:
        if self._event is None and self.state == "running":
            delay = max(0.045, self.game.delay)
            self._event = Clock.schedule_once(self._tick, delay)

    def cancel(self) -> None:
        if self._event is not None:
            Clock.unschedule(self._event)
            self._event = None

    def _tick(self, _dt: float) -> None:
        self._event = None
        if self.state != "running":
            return
        self.game.step()
        if self.game.dead or self.game.won:
            self.state = "over"
            self.app.remember_high(self.game.score)
        self.redraw()
        self.schedule()

    # -- состояния ---------------------------------------------------------- #

    def pause(self) -> None:
        if self.state == "running":
            self.state = "paused"
            self.cancel()
            self.redraw()

    def resume(self) -> None:
        if self.state == "paused":
            self.state = "running"
            self.schedule()
            self.redraw()

    def restart(self) -> None:
        self.cancel()
        self.game.reset()
        self.state = "running"
        self.redraw()
        self.schedule()

    def on_tap(self) -> None:
        if self.state == "over":
            self.restart()
        elif self.state == "paused":
            self.resume()
        else:
            self.pause()

    # -- ввод --------------------------------------------------------------- #

    def on_touch_down(self, touch) -> bool:
        self._touch_start = touch.pos
        return True

    def on_touch_up(self, touch) -> bool:
        start = self._touch_start
        self._touch_start = None
        if start is None:
            return True

        dx = touch.x - start[0]
        dy = touch.y - start[1]

        if max(abs(dx), abs(dy)) < dp(self.TAP_THRESHOLD):
            self.on_tap()
            return True

        if self.state == "paused":
            self.resume()
        if abs(dx) > abs(dy):
            self.game.turn("right" if dx > 0 else "left")
        else:
            self.game.turn("up" if dy > 0 else "down")
        return True

    def _on_size(self, *_args) -> None:
        self.redraw()

    def _on_pos(self, *_args) -> None:
        self.redraw()

    # -- отрисовка ---------------------------------------------------------- #

    def _metrics(self):
        w, h = self.size
        cell = min(w / self.cols, h / self.rows)
        board_w, board_h = cell * self.cols, cell * self.rows
        return cell, board_w, board_h, (w - board_w) / 2, (h - board_h) / 2

    def redraw(self) -> None:
        cell, board_w, board_h, ox, oy = self._metrics()
        if cell <= 0:
            return

        self.canvas.clear()
        with self.canvas:
            Color(*BOARD)
            Rectangle(pos=(self.x + ox, self.y + oy), size=(board_w, board_h))

            Color(*GRID)
            thin = max(1.0, cell * 0.02)
            for i in range(self.cols + 1):
                x = self.x + ox + i * cell
                Line(points=[x, self.y + oy, x, self.y + oy + board_h],
                     width=thin)
            for j in range(self.rows + 1):
                y = self.y + oy + j * cell
                Line(points=[self.x + ox, y, self.x + ox + board_w, y],
                     width=thin)

            self._draw_food(cell, ox, oy)
            self._draw_snake(cell, ox, oy)
            self._draw_overlay(cell, board_w, board_h, ox, oy)

        if self.info is not None:
            self.info.text = (
                f"Очки {self.game.score}    Рекорд {self.app.high}    "
                f"Длина {len(self.game.snake)}    Ур. {self.game.level}"
            )

    def _center(self, cell: float, ox: float, oy: float, x: int, y: int):
        """Центр клетки (x, y) игрового поля в координатах экрана."""
        return (self.x + ox + (x + 0.5) * cell,
                self.y + oy + (self.rows - y - 0.5) * cell)

    def _draw_food(self, cell: float, ox: float, oy: float) -> None:
        if self.game.food is None:
            return
        cx, cy = self._center(cell, ox, oy, *self.game.food)
        r = cell * 0.34
        Color(*FOOD)
        Ellipse(pos=(cx - r, cy - r), size=(2 * r, 2 * r))
        Color(1, 1, 1, 0.35)
        hr = r * 0.45
        Ellipse(pos=(cx - hr, cy + r * 0.05), size=(2 * hr, 2 * hr))

    def _draw_snake(self, cell: float, ox: float, oy: float) -> None:
        snake = list(self.game.snake)
        # Тело — толстая линия с круглыми стыками; при телепорте через
        # край поля линия рвётся на отдельные куски.
        runs = [[snake[0]]]
        for prev, cur in zip(snake, snake[1:]):
            if abs(prev[0] - cur[0]) + abs(prev[1] - cur[1]) == 1:
                runs[-1].append(cur)
            else:
                runs.append([cur])

        width = cell * 0.62
        Color(*BODY)
        for run in runs:
            points = []
            for x, y in run:
                cx, cy = self._center(cell, ox, oy, x, y)
                points += [cx, cy]
            if len(points) == 2:
                cx, cy = points
                Ellipse(pos=(cx - width / 2, cy - width / 2),
                        size=(width, width))
            else:
                Line(points=points, width=width, cap="round", joint="round")

        hx, hy = snake[0]
        cx, cy = self._center(cell, ox, oy, hx, hy)
        r = cell * 0.36
        Color(*HEAD)
        Ellipse(pos=(cx - r, cy - r), size=(2 * r, 2 * r))

        dx, dy = SCREEN_VECTORS[self.game.direction]
        px, py = -dy, dx
        eye = max(1.5, cell * 0.08)
        offset = cell * 0.16
        Color(*BG)
        for side in (-1, 1):
            ex = cx + dx * offset + px * side * offset
            ey = cy + dy * offset + py * side * offset
            Ellipse(pos=(ex - eye, ey - eye), size=(2 * eye, 2 * eye))

    def _draw_overlay(self, cell: float, board_w: float, board_h: float,
                      ox: float, oy: float) -> None:
        if self.state == "running":
            return
        Color(0.02, 0.03, 0.05, 0.72)
        Rectangle(pos=(self.x + ox, self.y + oy), size=(board_w, board_h))

        cx = self.x + ox + board_w / 2
        cy = self.y + oy + board_h / 2
        if self.state == "paused":
            title, hint = "ПАУЗА", "коснитесь, чтобы продолжить"
        elif self.game.won:
            title, hint = "ПОБЕДА!", "коснитесь, чтобы сыграть ещё"
        else:
            title, hint = "ИГРА ОКОНЧЕНА", "коснитесь, чтобы начать заново"

        self._text(title, dp(28), (cx, cy + dp(18)))
        self._text(hint, dp(13), (cx, cy - dp(20)), color=MUTED)

    def _text(self, text: str, size: float, center, color=TEXT) -> None:
        label = CoreLabel(text=text, font_size=size, color=color)
        label.refresh()
        texture = label.texture
        Color(1, 1, 1, 1)
        Rectangle(texture=texture, size=texture.size,
                  pos=(center[0] - texture.size[0] / 2,
                       center[1] - texture.size[1] / 2))


class SnakeRoot(BoxLayout):
    """Строка со счётом + игровое поле."""

    def __init__(self, app: "SnakeApp", **kwargs) -> None:
        super().__init__(orientation="vertical", **kwargs)
        self.hud = Label(text="", font_size=dp(16), color=TEXT,
                         size_hint_y=None, height=HUD_HEIGHT)
        self.board = GameWidget(app)
        self.board.info = self.hud
        self.add_widget(self.hud)
        self.add_widget(self.board)


class SnakeApp(App):
    """Приложение: хранит рекорд и обрабатывает системные события."""

    def build(self) -> SnakeRoot:
        self.title = "Змейка"
        Window.clearcolor = BG
        self.high = self._load_high()
        self.screen = SnakeRoot(self)
        return self.screen

    def on_start(self) -> None:
        Window.bind(on_keyboard=self._on_keyboard)

    def on_stop(self) -> None:
        Window.unbind(on_keyboard=self._on_keyboard)
        self.remember_high(self.screen.board.game.score)

    def on_pause(self) -> bool:
        # Android: приложение свёрнули — ставим игру на паузу.
        self.screen.board.pause()
        return True

    def _on_keyboard(self, _window, key, *_args) -> bool:
        if key == 27:  # Esc на десктопе и кнопка «назад» на Android
            board = self.screen.board
            if board.state == "running":
                board.pause()
                return True
        return False

    # -- рекорд ------------------------------------------------------------- #

    def _high_path(self) -> str:
        return os.path.join(self.user_data_dir, "highscore.json")

    def _load_high(self) -> int:
        try:
            with open(self._high_path(), encoding="utf-8") as fh:
                return int(json.load(fh).get("high", 0))
        except (OSError, ValueError, AttributeError, TypeError):
            return 0

    def remember_high(self, score: int) -> None:
        if score <= self.high:
            return
        self.high = score
        try:
            with open(self._high_path(), "w", encoding="utf-8") as fh:
                json.dump({"high": self.high}, fh)
        except OSError:
            pass  # некуда писать — просто не сохраняем рекорд


if __name__ == "__main__":
    SnakeApp().run()
