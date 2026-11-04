#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Змейка — мини-игра для терминала.

Никаких зависимостей: только стандартная библиотека Python 3.9+.

    python snake.py            # играть
    python snake.py --wrap     # стены насквозь (телепорт через край)
    python snake.py --demo     # смотреть, как играет бот
    python snake.py --selftest # прогнать проверки логики и выйти

Управление:
    стрелки или WASD (работает и в русской раскладке ЦФЫВ)
    P — пауза, Q — выход, R — заново после проигрыша

Правила: собирайте «*», не врезайтесь в стены и в собственный хвост.
Каждое яблоко — 10 очков и +1 к длине. Чем больше съедено, тем выше
скорость. Рекорд сохраняется в snake_highscore.txt рядом со скриптом.
"""

from __future__ import annotations

import argparse
import os
import random
import re
import shutil
import sys
import time
from collections import deque
from pathlib import Path

# --------------------------------------------------------------------------- #
#  Константы
# --------------------------------------------------------------------------- #

DIRECTIONS = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}

# Латинская и русская раскладки — чтобы не переключать язык во время игры.
KEYMAP = {
    "w": "up", "ц": "up",
    "s": "down", "ы": "down",
    "a": "left", "ф": "left",
    "d": "right", "в": "right",
}

# Клавиши, которые на Windows приходят как "{H}", "{P}", ... (стрелки).
WIN_SPECIAL = {"H": "up", "P": "down", "K": "left", "M": "right"}

# Escape-последовательности стрелок в Unix-терминалах.
UNIX_SPECIAL = {
    "\x1b[A": "up", "\x1b[B": "down", "\x1b[C": "right", "\x1b[D": "left",
    "\x1bOA": "up", "\x1bOB": "down", "\x1bOC": "right", "\x1bOD": "left",
}

STYLES = {
    "reset": "\x1b[0m",
    "border": "\x1b[38;5;242m",
    "head": "\x1b[1;38;5;46m",
    "body": "\x1b[38;5;35m",
    "food": "\x1b[1;38;5;203m",
    "title": "\x1b[1;38;5;221m",
    "text": "\x1b[38;5;250m",
    "dim": "\x1b[38;5;244m",
    "bad": "\x1b[1;38;5;203m",
}
USE_COLOR = True

SCORE_FILE = Path(__file__).resolve().with_name("snake_highscore.txt")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Рамка: псевдографика, а если терминал её не переваривает — обычный ASCII.
FRAME_UNICODE = ("┌", "─", "┐", "│", "└", "┘")
FRAME_ASCII = ("+", "-", "+", "|", "+", "+")
FRAME = FRAME_UNICODE


def setup_stdio() -> None:
    """UTF-8 вывод: иначе на Windows в cp1251 ломается псевдографика."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def choose_frame_chars() -> None:
    """ASCII-рамка, если текущая кодировка вывода не умеет рисовать рамку."""
    global FRAME
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        "".join(FRAME_UNICODE).encode(encoding)
        FRAME = FRAME_UNICODE
    except (LookupError, UnicodeEncodeError):
        FRAME = FRAME_ASCII


def paint(text: str, style: str) -> str:
    """Покрасить строку, если цвета включены."""
    if not USE_COLOR:
        return text
    return STYLES[style] + text + STYLES["reset"]


# --------------------------------------------------------------------------- #
#  Логика игры (не зависит от терминала — её можно тестировать отдельно)
# --------------------------------------------------------------------------- #

class Game:
    """Состояние партии. Вся игровая логика — в step()."""

    def __init__(self, width: int = 24, height: int = 14,
                 wrap: bool = False, rng: random.Random | None = None) -> None:
        self.w = width
        self.h = height
        self.wrap = wrap
        self.rng = rng or random.Random()
        self.reset()

    # -- состояние ---------------------------------------------------------- #

    def reset(self) -> None:
        cx, cy = self.w // 2, self.h // 2
        self.snake = deque([(cx, cy), (cx - 1, cy), (cx - 2, cy)])
        self.occupied = set(self.snake)
        self.direction = "right"
        self.pending: deque[str] = deque()  # буфер поворотов
        self.score = 0
        self.eaten = 0
        self.dead = False
        self.won = False
        self.food: tuple[int, int] | None = None
        self.spawn_food()

    @property
    def level(self) -> int:
        return 1 + min(8, self.eaten // 4)

    @property
    def delay(self) -> float:
        """Пауза между шагами змейки, секунды."""
        return max(0.055, 0.17 - 0.015 * (self.level - 1))

    # -- действия ----------------------------------------------------------- #

    def turn(self, direction: str) -> None:
        """Повернуть змейку. Разворот на 180° и дубли игнорируются."""
        if direction not in DIRECTIONS:
            return
        last = self.pending[-1] if self.pending else self.direction
        if direction != last and direction != OPPOSITE[last]:
            if len(self.pending) < 2:
                self.pending.append(direction)

    def spawn_food(self) -> None:
        free = [
            (x, y)
            for y in range(self.h)
            for x in range(self.w)
            if (x, y) not in self.occupied
        ]
        if not free:
            self.food = None
            self.won = True  # вся доска занята змейкой
            return
        self.food = self.rng.choice(free)

    def step(self) -> None:
        """Один шаг. Обновляет состояние; self.dead ставится при столкновении."""
        if self.dead or self.won:
            return
        if self.pending:
            self.direction = self.pending.popleft()

        dx, dy = DIRECTIONS[self.direction]
        head = self.snake[0]
        nx, ny = head[0] + dx, head[1] + dy

        if self.wrap:
            nx %= self.w
            ny %= self.h
        elif not (0 <= nx < self.w and 0 <= ny < self.h):
            self.dead = True
            return

        new_head = (nx, ny)
        growing = new_head == self.food
        # Хвост сдвинется, поэтому в его клетку входить можно (если не едим).
        blocked = self.occupied if growing else self.occupied - {self.snake[-1]}
        if new_head in blocked:
            self.dead = True
            return

        self.snake.appendleft(new_head)
        self.occupied.add(new_head)
        if growing:
            self.score += 10
            self.eaten += 1
            self.spawn_food()
        else:
            self.occupied.discard(self.snake.pop())


# --------------------------------------------------------------------------- #
#  Бот для демо-режима и автотестов
# --------------------------------------------------------------------------- #

def _shift(point, dx, dy, game):
    """Соседняя клетка с учётом стен или телепорта. None — за границей."""
    x, y = point[0] + dx, point[1] + dy
    if game.wrap:
        return (x % game.w, y % game.h)
    if 0 <= x < game.w and 0 <= y < game.h:
        return (x, y)
    return None


def _free_area(start, blocked, game, limit=64):
    """Сколько свободных клеток вокруг (ограниченный заливкой подсчёт)."""
    seen = {start}
    queue = deque([start])
    while queue and len(seen) < limit:
        cur = queue.popleft()
        for dx, dy in DIRECTIONS.values():
            nxt = _shift(cur, dx, dy, game)
            if nxt is None or nxt in seen or nxt in blocked:
                continue
            seen.add(nxt)
            queue.append(nxt)
    return len(seen)


def _fallback(game):
    """Короткого пути нет: уходим туда, где больше свободного места."""
    start = game.snake[0]
    blocked = set(game.snake)
    blocked.discard(start)
    blocked.discard(game.snake[-1])

    best, best_area = None, -1
    for name, (dx, dy) in DIRECTIONS.items():
        if name == OPPOSITE[game.direction]:
            continue
        nxt = _shift(start, dx, dy, game)
        if nxt is None or nxt in blocked:
            continue
        area = _free_area(nxt, blocked, game)
        if area > best_area:
            best, best_area = name, area
    return best


def ai_direction(game) -> str | None:
    """Следующий ход бота: BFS по кратчайшему пути к еде, иначе — выживание."""
    start = game.snake[0]
    target = game.food
    if target is None:
        return None

    blocked = set(game.snake)
    blocked.discard(start)
    blocked.discard(game.snake[-1])

    prev = {start: None}
    queue = deque([start])
    while queue and target not in prev:
        cur = queue.popleft()
        for dx, dy in DIRECTIONS.values():
            nxt = _shift(cur, dx, dy, game)
            if nxt is None or nxt in prev or nxt in blocked:
                continue
            prev[nxt] = cur
            queue.append(nxt)

    if target not in prev:
        return _fallback(game)

    # Идём по цепочке от еды назад к голове и берём первый шаг.
    cur = target
    while prev[cur] != start:
        cur = prev[cur]
    for name, (dx, dy) in DIRECTIONS.items():
        if _shift(start, dx, dy, game) == cur:
            return name
    return None


# --------------------------------------------------------------------------- #
#  Отрисовка
# --------------------------------------------------------------------------- #

def render(game: Game, high: int = 0, paused: bool = False) -> str:
    """Собрать кадр целиком (без анимации) — удобно и рисовать, и тестировать."""
    w, h = game.w, game.h
    left, bar, right, wall, bottom_left, bottom_right = FRAME
    grid = [[" "] * w for _ in range(h)]

    if game.food is not None:
        fx, fy = game.food
        grid[fy][fx] = paint("*", "food")

    for i, (x, y) in enumerate(game.snake):
        grid[y][x] = paint("@", "head") if i == 0 else paint("o", "body")

    lines = [
        paint(" ЗМЕЙКА ", "title")
        + " "
        + paint(
            f"очки {game.score}   длина {len(game.snake)}   "
            f"рекорд {high}   ур. {game.level}",
            "text",
        ),
        paint(left + bar * w + right, "border"),
    ]
    for row in grid:
        lines.append(paint(wall, "border") + "".join(row) + paint(wall, "border"))
    lines.append(paint(bottom_left + bar * w + bottom_right, "border"))

    if game.won:
        status = paint(" ПОБЕДА! Доска заполнена целиком.  R — заново",
                       "title")
    elif game.dead:
        status = paint(" ИГРА ОКОНЧЕНА.  R — заново, Q — выход", "bad")
    elif paused:
        status = paint(" ПАУЗА.  P — продолжить", "title")
    else:
        status = paint(" ←↑↓→ / WASD — движение   P — пауза   Q — выход", "dim")
    lines.append(status)
    return "\r\n".join(lines)


# --------------------------------------------------------------------------- #
#  Ввод с клавиатуры
# --------------------------------------------------------------------------- #

def has_console() -> bool:
    """Есть ли у процесса консоль Windows, даже если stdin перенаправлен."""
    if os.name != "nt":
        return False
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        create = kernel32.CreateFileW
        create.restype = ctypes.c_void_p
        create.argtypes = [
            ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
            ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
        ]
        handle = create("CONIN$", 0x80000000 | 0x40000000, 3, None, 3, 0, None)
        if not handle or handle == ctypes.c_void_p(-1).value:
            return False
        kernel32.CloseHandle(ctypes.c_void_p(handle))
        return True
    except Exception:
        return False


class KeyReader:
    """Неблокирующее чтение клавиш.

    Windows: msvcrt читает консоль напрямую, поэтому управление работает
    даже когда stdin перенаправлен (IDE, панель вывода, конвейер).
    Unix: termios на stdin, а если он не терминал — напрямую /dev/tty.
    """

    def __init__(self) -> None:
        self.win = os.name == "nt"
        self.mode = "none"  # "console" | "termios" | "none"
        self._buf = ""
        self._fd = None
        self._owns_fd = False
        self._old_attrs = None
        self._msvcrt = None

        if self.win:
            if has_console():
                import msvcrt
                self._msvcrt = msvcrt
                self.mode = "console"
            return

        import termios
        import tty

        try:
            if sys.stdin.isatty():
                self._fd = sys.stdin.fileno()
            else:
                self._fd = os.open("/dev/tty", os.O_RDONLY)
                self._owns_fd = True
            self._old_attrs = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
            self.mode = "termios"
        except Exception:
            if self._owns_fd and self._fd is not None:
                os.close(self._fd)
            self._fd = None
            self._owns_fd = False

    def keys(self) -> list[str]:
        if self.mode == "none":
            return []
        return [k for k in (normalize(t) for t in self._read_raw()) if k]

    def _read_raw(self) -> list[str]:
        if self.mode == "console":
            tokens = []
            while self._msvcrt.kbhit():
                ch = self._msvcrt.getwch()
                if ch in ("\x00", "\xe0"):  # префикс спецклавиши
                    tokens.append("{" + self._msvcrt.getwch() + "}")
                else:
                    tokens.append(ch)
            return tokens

        import select
        if not select.select([self._fd], [], [], 0)[0]:
            return []
        self._buf += os.read(self._fd, 64).decode("utf-8", "replace")
        tokens = []
        while self._buf:
            if self._buf.startswith("\x1b["):
                if len(self._buf) < 3:
                    break  # ждём остаток последовательности
                tokens.append(self._buf[:3])
                self._buf = self._buf[3:]
            else:
                tokens.append(self._buf[0])
                self._buf = self._buf[1:]
        return tokens

    def close(self) -> None:
        if self._old_attrs is not None:
            import termios
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_attrs)
            self._old_attrs = None
        if self._owns_fd and self._fd is not None:
            os.close(self._fd)
        self._fd = None
        self._owns_fd = False


def normalize(token: str) -> str | None:
    """Привести «сырую» клавишу к действию игры."""
    if token in UNIX_SPECIAL:
        return UNIX_SPECIAL[token]
    if token.startswith("{") and token.endswith("}"):
        return WIN_SPECIAL.get(token[1:-1])
    ch = token.lower()
    if ch in ("q", "й"):
        return "quit"
    if ch in ("p", "з"):
        return "pause"
    if ch in ("r", "к"):
        return "restart"
    return KEYMAP.get(ch)


def enable_ansi() -> bool:
    """Включить поддержку ANSI-последовательностей в консоли Windows."""
    if os.name != "nt":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        if mode.value & 0x0004:  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
            return True
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


# --------------------------------------------------------------------------- #
#  Рекорд
# --------------------------------------------------------------------------- #

def load_high_score() -> int:
    try:
        return int(SCORE_FILE.read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return 0


def save_high_score(value: int) -> None:
    try:
        SCORE_FILE.write_text(str(value), encoding="utf-8")
    except OSError:
        pass  # запись недоступна — просто играем без сохранения рекорда


# --------------------------------------------------------------------------- #
#  Главный цикл
# --------------------------------------------------------------------------- #

def play(args) -> None:
    global USE_COLOR

    ansi = enable_ansi()
    if args.no_color or not ansi:
        USE_COLOR = False

    size = shutil.get_terminal_size((80, 24))
    width = max(18, min(46, size.columns - 3))
    height = max(10, min(20, size.lines - 7))

    game = Game(width, height, wrap=args.wrap)
    high = load_high_score()
    reader = KeyReader()
    interactive = sys.stdout.isatty()

    if not args.demo and (reader.mode == "none" or not interactive):
        reader.close()
        if reader.mode == "none":
            print("Не удалось подключиться к клавиатуре: программа запущена "
                  "без консоли (так бывает в IDE и в панелях вывода).\n"
                  "Запустите её в PowerShell / Windows Terminal — или откройте "
                  "оконную версию:  python snake_tk.py")
        else:
            print("Вывод перенаправлен, а игре нужен экран терминала.\n"
                  "Запустите её прямо в терминале — или откройте оконную "
                  "версию:  python snake_tk.py")
        return

    def draw(paused: bool = False) -> None:
        if not interactive:
            return
        frame = render(game, high, paused)
        if ansi:
            sys.stdout.write("\x1b[H" + frame + "\x1b[J")
        else:
            os.system("cls" if os.name == "nt" else "clear")
            sys.stdout.write(frame + "\n")
        sys.stdout.flush()

    if interactive and ansi:
        sys.stdout.write("\x1b[?25l")  # спрятать курсор

    paused = False
    steps_done = 0
    over_handled = False
    next_step = time.perf_counter() + game.delay

    try:
        while True:
            # --- партия закончена: ждём R (заново) или Q (выход) ----------- #
            if game.dead or game.won:
                if not over_handled:
                    if game.score > high:
                        high = game.score
                        save_high_score(high)
                    draw()
                    over_handled = True
                    if args.demo:
                        break
                for key in reader.keys():
                    if key == "quit":
                        return
                    if key == "restart":
                        game.reset()
                        paused = False
                        over_handled = False
                        steps_done = 0
                        next_step = time.perf_counter() + game.delay
                        draw()
                time.sleep(0.03)
                continue

            # --- управление ------------------------------------------------ #
            for key in reader.keys():
                if key == "quit":
                    return
                if key == "pause":
                    paused = not paused
                    next_step = time.perf_counter() + game.delay
                    draw(paused=paused)
                elif key in DIRECTIONS:
                    game.turn(key)

            if args.demo:
                if args.demo_steps and steps_done >= args.demo_steps:
                    break
                if not paused:
                    move = ai_direction(game)
                    if move:
                        game.turn(move)

            # --- движение по времени --------------------------------------- #
            now = time.perf_counter()
            if paused:
                draw(paused=True)
                time.sleep(0.05)
                continue
            if now >= next_step:
                game.step()
                steps_done += 1
                next_step = now + game.delay
                draw()
            time.sleep(0.004)
    finally:
        reader.close()
        if interactive and ansi:
            sys.stdout.write("\x1b[?25h\n")
            sys.stdout.flush()


# --------------------------------------------------------------------------- #
#  Проверки логики
# --------------------------------------------------------------------------- #

def selftest() -> None:
    global USE_COLOR
    rng = random.Random(7)
    checks = 0

    # 1. Разворот на 180° запрещён.
    game = Game(20, 10, rng=rng)
    game.turn("left")
    assert game.direction == "right" and not game.pending
    checks += 1

    # 2. Стена убивает.
    game = Game(10, 6, rng=rng)
    for _ in range(20):
        game.step()
    assert game.dead
    checks += 1

    # 3. С --wrap стены не убивают.
    game = Game(10, 6, wrap=True, rng=rng)
    for _ in range(20):
        game.step()
    assert not game.dead
    checks += 1

    # 4. Съеденная еда даёт очки, длину и новую еду.
    game = Game(20, 10, rng=rng)
    game.snake = deque([(5, 5), (4, 5), (3, 5)])
    game.occupied = set(game.snake)
    game.direction = "right"
    game.food = (6, 5)
    game.score, game.eaten = 0, 0
    game.step()
    assert game.score == 10 and len(game.snake) == 4 and game.eaten == 1
    assert game.food is not None and game.food not in game.occupied
    checks += 1

    # 5. Бот играет, инварианты состояния не нарушаются.
    for wrap in (False, True):
        game = Game(24, 14, wrap=wrap, rng=rng)
        for _ in range(3000):
            if game.dead or game.won:
                break
            move = ai_direction(game)
            if move:
                game.turn(move)
            game.step()
            assert len(set(game.snake)) == len(game.snake), "тело пересеклось"
            assert len(game.snake) == 3 + game.eaten, "неверная длина"
            assert game.score == 10 * game.eaten, "неверные очки"
            assert game.food is None or game.food not in game.occupied
        print(f"  бот (wrap={wrap}): очки={game.score}, "
              f"длина={len(game.snake)}, финал="
              f"{'победа' if game.won else 'смерть' if game.dead else 'идёт'}")
    checks += 1

    # 6. Кадр собирается и все строки поля нужной ширины.
    USE_COLOR = True
    game = Game(20, 8, rng=rng)
    frame = render(game, high=120)
    lines = frame.split("\r\n")
    assert len(lines) == 8 + 4, f"ожидалось 12 строк, получено {len(lines)}"
    plain = ANSI_RE.sub("", frame)
    wall = FRAME[3]
    board = [line for line in plain.split("\r\n") if line.startswith(wall)]
    assert len(board) == 8
    assert all(len(line) == 20 + 2 for line in board)
    checks += 1

    print(f"Все проверки пройдены: {checks}/6")


# --------------------------------------------------------------------------- #
#  Точка входа
# --------------------------------------------------------------------------- #

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Змейка — мини-игра для терминала")
    parser.add_argument("--wrap", action="store_true",
                        help="проходить сквозь стены")
    parser.add_argument("--demo", action="store_true",
                        help="демо: играет бот")
    parser.add_argument("--demo-steps", type=int, default=0,
                        help=argparse.SUPPRESS)
    parser.add_argument("--selftest", action="store_true",
                        help="проверить логику и выйти")
    parser.add_argument("--no-color", action="store_true",
                        help="выключить цвета")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    setup_stdio()
    choose_frame_chars()
    if args.selftest:
        selftest()
        return 0
    try:
        play(args)
    except KeyboardInterrupt:
        print("\nВыход.")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
