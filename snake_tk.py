#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Змейка в графическом окне — tkinter, только стандартная библиотека.

    python snake_tk.py
    pythonw snake_tk.py   # без лишнего окна консоли

Управление: стрелки или WASD (работает и в русской раскладке ЦФЫВ),
пробел — пауза, R — заново, Esc — выход.
Рекорд общий с консольной версией (snake_highscore.txt).
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

try:
    from snake import Game, load_high_score, save_high_score
except ImportError:  # запуск из другой папки
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from snake import Game, load_high_score, save_high_score

# --------------------------------------------------------------------------- #
#  Оформление
# --------------------------------------------------------------------------- #

CELL = 26
COLS, ROWS = 26, 18
BOARD_W, BOARD_H = COLS * CELL, ROWS * CELL

BG = "#0d1117"
BOARD = "#0f1620"
GRID = "#1a2432"
BORDER = "#26344a"
HEAD = "#b6ff5e"
BODY = "#3ddc84"
FOOD = "#ff4d6d"
FOOD_LIGHT = "#ffa3b2"
TEXT = "#e6edf3"
MUTED = "#8b98a5"

VECTORS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}

KEYS = {
    "up": "up", "down": "down", "left": "left", "right": "right",
    "w": "up", "s": "down", "a": "left", "d": "right",
    "ц": "up", "ы": "down", "ф": "left", "в": "right",
}


class SnakeApp:
    """Окно игры: отрисовка на Canvas, тики через after()."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.game = Game(COLS, ROWS)
        self.high = load_high_score()
        self.state = "running"  # running | paused | over
        self.after_id = None
        self._static_done = False

        root.title("Змейка")
        root.configure(bg=BG)
        root.resizable(False, False)

        top = tk.Frame(root, bg=BG)
        top.pack(fill="x", padx=18, pady=(14, 4))
        tk.Label(top, text="ЗМЕЙКА", bg=BG, fg=HEAD,
                 font=("Segoe UI", 16, "bold")).pack(side="left")
        self.info = tk.StringVar()
        tk.Label(top, textvariable=self.info, bg=BG, fg=MUTED,
                 font=("Segoe UI", 11)).pack(side="right")

        self.canvas = tk.Canvas(root, width=BOARD_W, height=BOARD_H,
                                bg=BOARD, highlightthickness=1,
                                highlightbackground=BORDER)
        self.canvas.pack(padx=18, pady=6)

        tk.Label(root,
                 text="← ↑ ↓ → / WASD — движение    Пробел — пауза    "
                      "R — заново    Esc — выход",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(pady=(0, 12))

        root.bind("<Key>", self.on_key)
        self.canvas.focus_set()

        self.draw()
        self.schedule()

    # -- таймер ------------------------------------------------------------- #

    def schedule(self) -> None:
        if self.after_id is None and self.state == "running":
            delay = max(40, int(self.game.delay * 1000))
            self.after_id = self.root.after(delay, self.tick)

    def cancel(self) -> None:
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def tick(self) -> None:
        self.after_id = None
        if self.state != "running":
            return
        self.game.step()
        if self.game.dead or self.game.won:
            self.state = "over"
            self.remember_high()
        self.draw()
        self.schedule()

    def remember_high(self) -> None:
        if self.game.score > self.high:
            self.high = self.game.score
            save_high_score(self.high)

    # -- управление --------------------------------------------------------- #

    def on_key(self, event) -> None:
        sym = (event.keysym or "").lower()
        ch = (event.char or "").lower()

        if sym in ("escape", "q", "й"):
            self.on_close()
            return
        if sym in ("space", "p", "з"):
            self.toggle_pause()
            return
        if sym in ("r", "к"):
            self.restart()
            return

        direction = KEYS.get(sym) or KEYS.get(ch)
        if direction is None:
            return
        if self.state == "over":
            self.restart()
        elif self.state == "paused":
            self.toggle_pause()
        self.game.turn(direction)

    def toggle_pause(self) -> None:
        if self.state == "running":
            self.state = "paused"
            self.cancel()
        elif self.state == "paused":
            self.state = "running"
            self.schedule()
        self.draw()

    def restart(self) -> None:
        self.cancel()
        self.game.reset()
        self.state = "running"
        self.draw()
        self.schedule()

    def on_close(self) -> None:
        self.remember_high()
        self.cancel()
        self.root.destroy()

    # -- отрисовка ---------------------------------------------------------- #

    def _draw_static(self) -> None:
        c = self.canvas
        c.delete("all")
        for x in range(0, BOARD_W + 1, CELL):
            c.create_line(x, 0, x, BOARD_H, fill=GRID)
        for y in range(0, BOARD_H + 1, CELL):
            c.create_line(0, y, BOARD_W, y, fill=GRID)

    def _draw_food(self) -> None:
        if self.game.food is None:
            return
        c = self.canvas
        x, y = self.game.food
        x0, y0 = x * CELL, y * CELL
        c.create_oval(x0 + 4, y0 + 4, x0 + CELL - 4, y0 + CELL - 4,
                      fill=FOOD, outline="", tags="dyn")
        c.create_oval(x0 + 8, y0 + 7, x0 + 12, y0 + 11,
                      fill=FOOD_LIGHT, outline="", tags="dyn")

    def _draw_snake(self) -> None:
        c = self.canvas
        snake = list(self.game.snake)

        # Тело рисуем одной толстой линией с круглыми стыками — получается
        # гладкая змейка. При телепорте через край линия рвётся на куски.
        runs = [[snake[0]]]
        for prev, cur in zip(snake, snake[1:]):
            if abs(prev[0] - cur[0]) + abs(prev[1] - cur[1]) == 1:
                runs[-1].append(cur)
            else:
                runs.append([cur])

        for run in runs:
            points = [(x * CELL + CELL / 2, y * CELL + CELL / 2)
                      for x, y in run]
            if len(points) == 1:
                x, y = points[0]
                c.create_oval(x - 7, y - 7, x + 7, y + 7,
                              fill=BODY, outline="", tags="dyn")
            else:
                c.create_line(*points, width=15, fill=BODY,
                              capstyle=tk.ROUND, joinstyle=tk.ROUND,
                              tags="dyn")

        # Голова и глаза, смотрящие по направлению движения.
        hx, hy = snake[0]
        cx, cy = hx * CELL + CELL / 2, hy * CELL + CELL / 2
        r = 9
        c.create_oval(cx - r, cy - r, cx + r, cy + r,
                      fill=HEAD, outline="", tags="dyn")
        dx, dy = VECTORS[self.game.direction]
        px, py = -dy, dx
        for side in (-1, 1):
            ex = cx + dx * 4 + px * side * 4
            ey = cy + dy * 4 + py * side * 4
            c.create_oval(ex - 2, ey - 2, ex + 2, ey + 2,
                          fill=BG, outline="", tags="dyn")

    def _overlay(self, title: str, hint: str) -> None:
        c = self.canvas
        c.create_rectangle(0, 0, BOARD_W, BOARD_H, fill=BG,
                           stipple="gray50", outline="", tags="dyn")
        c.create_text(BOARD_W / 2, BOARD_H / 2 - 20, text=title, fill=TEXT,
                      font=("Segoe UI", 24, "bold"), tags="dyn")
        c.create_text(BOARD_W / 2, BOARD_H / 2 + 24, text=hint, fill=MUTED,
                      font=("Segoe UI", 12), tags="dyn")

    def draw(self) -> None:
        if not self._static_done:
            self._draw_static()
            self._static_done = True
        self.canvas.delete("dyn")
        self._draw_food()
        self._draw_snake()
        self.info.set(
            f"Очки {self.game.score}    Рекорд {self.high}    "
            f"Длина {len(self.game.snake)}    Ур. {self.game.level}"
        )
        if self.state == "paused":
            self._overlay("ПАУЗА", "пробел — продолжить")
        elif self.state == "over":
            self._overlay("ПОБЕДА!" if self.game.won else "ИГРА ОКОНЧЕНА",
                          "R — заново,   Esc — выход")


def main() -> int:
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"Не удалось открыть окно: {exc}", file=sys.stderr)
        print("Похоже, нет графической среды. Консольная версия: "
              "python snake.py", file=sys.stderr)
        return 1

    app = SnakeApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.focus_force()
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
