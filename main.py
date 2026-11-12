"""
NEON SNAKE

A true-fullscreen cyberpunk Snake game with:
- Aspect-adaptive logical canvas scaled across the display
- Launches fullscreen; ESC during play switches to windowed mode
- Neon menu and difficulty selection
- Level progression and level-based scoring
- Pause/resume button and Space/P shortcut
- Speed increases with each level, starting from the chosen difficulty
- Persistent high scores and run history
- Restart and main menu buttons on the end screens
- Level-up effect, pulsing apple food, and collection particles
- A YOU WIN screen when the snake fills the entire grid
- Glossy segmented snake with smooth movement, neon glow, and a trail
- Expressive animated eyes and a polished death animation
- Dark checkerboard playfield with a neon border

Run with:
    python main.py
"""

import json
import math
import os
import random
import shutil
import sys

import pygame

# Keep save data next to the script during development and next to the .exe
# when the game is packaged as a standalone Windows application.
APP_DIRECTORY = (
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__))
)

# ---------------------------------------------------------------------------
# Window and board settings
# ---------------------------------------------------------------------------
WIDTH = 960
HEIGHT = 720
BASE_WIDTH = 960
BASE_HEIGHT = 720

COLS = 30
ROWS = 21
CELL = 30

BOARD_WIDTH = COLS * CELL
BOARD_HEIGHT = ROWS * CELL
BOARD_X = (WIDTH - BOARD_WIDTH) // 2
BOARD_Y = 30
BOARD_RECT = pygame.Rect(BOARD_X, BOARD_Y, BOARD_WIDTH, BOARD_HEIGHT)

HUD_HEIGHT = 50
HUD_Y = BOARD_Y + BOARD_HEIGHT + 10
FPS = 60

FOOD_PER_LEVEL = 5
POINTS_PER_FOOD = 10
SPEED_STEP = 0.01
LEVEL_UP_DURATION = 1.2
DEATH_DURATION = 1.15
HISTORY_LIMIT = 50


def choose_save_file():
    """Pick a writable save location for both development and installed builds.

    Installed applications often live in a read-only folder (for example
    Program Files), so frozen builds keep their data in the per-user app data
    directory. An existing file next to the executable is migrated once.
    """
    local_file = os.path.join(APP_DIRECTORY, "high_scores.json")

    if not getattr(sys, "frozen", False):
        return local_file

    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, "NeonSnake")
    target = os.path.join(folder, "high_scores.json")

    try:
        os.makedirs(folder, exist_ok=True)
        if not os.path.exists(target) and os.path.exists(local_file):
            shutil.copyfile(local_file, target)
        return target
    except OSError:
        return local_file


HIGH_SCORE_FILE = choose_save_file()

DIFFICULTIES = {
    "EASY": {"delay": 0.18, "min_delay": 0.10},
    "NORMAL": {"delay": 0.13, "min_delay": 0.07},
    "HARD": {"delay": 0.09, "min_delay": 0.05},
}

# ---------------------------------------------------------------------------
# Neon color palette
# ---------------------------------------------------------------------------
BACKGROUND = (3, 6, 14)
MENU_TOP = (5, 12, 27)
MENU_BOTTOM = (1, 3, 9)
MENU_GRID = (9, 25, 34)
TILE_A = (8, 15, 31)
TILE_B = (11, 21, 41)
HUD_COLOR = (6, 14, 26)
BUTTON_FILL = (8, 20, 36)
BUTTON_HOVER_FILL = (13, 38, 55)
BUTTON_BORDER = (28, 60, 82)
PANEL_COLOR = (6, 15, 28)
PANEL_ALT = (10, 22, 38)
BORDER_DIM = (28, 58, 76)

NEON = (0, 255, 200)
NEON_DIM = (0, 180, 160)
NEON_DARK = (0, 65, 72)
NEON_GREEN = (57, 255, 136)
GREEN_DIM = (0, 185, 105)
CYAN = (0, 235, 255)
PURPLE = (175, 90, 255)
GOLD = (255, 210, 90)
SILVER = (200, 215, 230)
BRONZE = (220, 140, 80)
TEXT_COLOR = (226, 245, 246)
MUTED_COLOR = (110, 150, 170)

MINT = (170, 255, 225)
TEAL = (0, 150, 165)
HEAD_COLOR = (190, 255, 235)
GAME_OVER_COLOR = (255, 70, 160)
APPLE_RED = (255, 35, 55)
APPLE_LIGHT = (255, 120, 130)
APPLE_HIGHLIGHT = (255, 210, 215)
WIN_COLOR = (255, 220, 100)
SNAKE_GLOW_OUTER = (0, 38, 45)
SNAKE_GLOW_INNER = (0, 90, 90)
MENU_PARTICLE_COLORS = (NEON_GREEN, CYAN, PURPLE, MINT)

DIFFICULTY_COLORS = {
    "EASY": NEON_GREEN,
    "NORMAL": CYAN,
    "HARD": PURPLE,
}

DIFFICULTY_TAGS = {
    "EASY": "RELAXED",
    "NORMAL": "BALANCED",
    "HARD": "INTENSE",
}

BODY_RADIUS = 12
BODY_WIDTH = 24
HEAD_RADIUS = 15

# Math: each direction is a vector in grid units.
# In Pygame, y increases downward.
DIRECTIONS = {
    pygame.K_UP: pygame.Vector2(0, -1),
    pygame.K_DOWN: pygame.Vector2(0, 1),
    pygame.K_LEFT: pygame.Vector2(-1, 0),
    pygame.K_RIGHT: pygame.Vector2(1, 0),
}


def configure_display(fullscreen=True):
    """Open the game on a logical canvas scaled to the display.

    Fullscreen uses a logical canvas matching the desktop aspect so the extra
    room is used by the responsive layouts. Windowed mode returns to the
    original 960 x 720 design size.
    """
    global WIDTH, BOARD_X, BOARD_RECT

    if fullscreen:
        try:
            desktop_width, desktop_height = pygame.display.get_desktop_sizes()[0]
        except (pygame.error, IndexError):
            desktop_width, desktop_height = BASE_WIDTH, BASE_HEIGHT

        if desktop_height > 0:
            WIDTH = max(
                BASE_WIDTH,
                round(desktop_width * BASE_HEIGHT / desktop_height),
            )
        else:
            WIDTH = BASE_WIDTH
    else:
        WIDTH = BASE_WIDTH

    BOARD_X = (WIDTH - BOARD_WIDTH) // 2
    BOARD_RECT = pygame.Rect(BOARD_X, BOARD_Y, BOARD_WIDTH, BOARD_HEIGHT)

    if fullscreen:
        # Prefer scaled fullscreen; fall back to plain fullscreen.
        for flags in (pygame.FULLSCREEN | pygame.SCALED, pygame.FULLSCREEN):
            try:
                return pygame.display.set_mode((WIDTH, HEIGHT), flags)
            except pygame.error:
                continue

        # If fullscreen is unavailable, fall back to the windowed design size.
        WIDTH = BASE_WIDTH
        BOARD_X = (WIDTH - BOARD_WIDTH) // 2
        BOARD_RECT = pygame.Rect(BOARD_X, BOARD_Y, BOARD_WIDTH, BOARD_HEIGHT)

    return pygame.display.set_mode((WIDTH, HEIGHT))


def centered_rect(width, height, y):
    rect = pygame.Rect(0, 0, width, height)
    rect.center = (WIDTH // 2, y)
    return rect


def lerp_color(start, end, amount):
    amount = max(0.0, min(1.0, amount))
    return tuple(
        int(start[index] + (end[index] - start[index]) * amount)
        for index in range(3)
    )


def load_font(size, family="bahnschrift", bold=False):
    """Load a system font with a safe fallback."""
    path = pygame.font.match_font(family)
    font = pygame.font.Font(path, size) if path else pygame.font.Font(None, size)
    font.set_bold(bold)
    return font


def cell_center(cell):
    """Convert a grid coordinate to the center of its cell, in board pixels."""
    return pygame.Vector2(
        int(cell.x) * CELL + CELL / 2,
        int(cell.y) * CELL + CELL / 2,
    )


def body_gradient(index, length):
    """Blend from mint near the head to teal near the tail."""
    if length <= 1:
        return MINT

    t = index / (length - 1)
    return (
        int(MINT[0] + (TEAL[0] - MINT[0]) * t),
        int(MINT[1] + (TEAL[1] - MINT[1]) * t),
        int(MINT[2] + (TEAL[2] - MINT[2]) * t),
    )


# ---------------------------------------------------------------------------
# High score storage
# ---------------------------------------------------------------------------
def load_game_data():
    """Load best scores plus the history of completed runs."""
    scores = {name: {"score": 0, "level": 1} for name in DIFFICULTIES}
    history = []

    try:
        with open(HIGH_SCORE_FILE, "r", encoding="utf-8") as file:
            saved = json.load(file)
    except (OSError, ValueError, TypeError):
        return scores, history

    if not isinstance(saved, dict):
        return scores, history

    for name in scores:
        entry = saved.get(name)
        if isinstance(entry, dict):
            try:
                scores[name]["score"] = max(0, int(entry.get("score", 0)))
                scores[name]["level"] = max(1, int(entry.get("level", 1)))
            except (ValueError, TypeError):
                pass

    raw_history = saved.get("history", [])
    if isinstance(raw_history, list):
        for item in raw_history:
            if not isinstance(item, dict):
                continue
            difficulty = item.get("difficulty")
            if difficulty not in DIFFICULTIES:
                continue
            try:
                score = max(0, int(item.get("score", 0)))
                level = max(1, int(item.get("level", 1)))
            except (ValueError, TypeError):
                continue

            history.append(
                {
                    "score": score,
                    "level": level,
                    "difficulty": difficulty,
                    "won": bool(item.get("won", False)),
                }
            )

    # Carry over best scores from older save files.
    if not history:
        for name, best in scores.items():
            if best["score"] > 0:
                history.append(
                    {
                        "score": best["score"],
                        "level": best["level"],
                        "difficulty": name,
                        "won": False,
                    }
                )

    history.sort(key=lambda run: (run["score"], run["level"]), reverse=True)
    return scores, history[:HISTORY_LIMIT]


def load_high_scores():
    """Compatibility wrapper for callers that only need the best scores."""
    return load_game_data()[0]


def save_game_data(scores, history):
    data = {name: dict(scores[name]) for name in DIFFICULTIES}
    data["history"] = history[:HISTORY_LIMIT]

    try:
        with open(HIGH_SCORE_FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
    except OSError:
        pass


def save_high_scores(scores):
    """Compatibility wrapper that keeps the existing history intact."""
    _, history = load_game_data()
    save_game_data(scores, history)


# ---------------------------------------------------------------------------
# Snake
# ---------------------------------------------------------------------------
class Snake:
    def __init__(self):
        start = pygame.Vector2(COLS // 2, ROWS // 2)

        # Body positions are grid-coordinate vectors, with the head first.
        self.body = [start - pygame.Vector2(i, 0) for i in range(5)]
        self.prev_body = [cell.copy() for cell in self.body]
        self.direction = pygame.Vector2(1, 0)
        self.next_direction = self.direction.copy()

    def turn(self, direction):
        # Reject reversals against both the current heading and the queued
        # heading. Without the current-heading check, two quick turns in one
        # tick could still steer the snake straight into its own neck.
        if (
            direction != -self.direction
            and direction != -self.next_direction
        ):
            self.next_direction = direction

    def move(self, food):
        self.direction = self.next_direction

        # Math: new head = old head + direction vector.
        head = self.body[0] + self.direction

        # Math: linear inequalities define the playable grid.
        if not (0 <= head.x < COLS and 0 <= head.y < ROWS):
            return "wall"

        # The tail cell is vacated this turn, so exclude it.
        if head in self.body[:-1]:
            return "self"

        ate_food = food is not None and head == food

        # Remember where every segment was so drawing can interpolate smoothly.
        self.prev_body = [cell.copy() for cell in self.body]
        self.body.insert(0, head)
        if not ate_food:
            self.body.pop()

        return "ate" if ate_food else "moved"

    def visual_body(self, progress):
        """Return smoothly interpolated centers for every body cell."""
        progress = max(0.0, min(1.0, progress))
        centers = []
        for index, cell in enumerate(self.body):
            current = cell_center(cell)
            if index < len(self.prev_body):
                previous = cell_center(self.prev_body[index])
            else:
                previous = current
            centers.append(previous.lerp(current, progress))
        return centers

    def draw_chain(self, surface, centers, color, width, radius):
        """Draw connected circles and lines to form a smooth body."""
        for index in range(len(centers) - 1, 0, -1):
            start = centers[index]
            end = centers[index - 1]
            pygame.draw.line(surface, color, start, end, width)
            pygame.draw.circle(
                surface,
                color,
                (int(start.x), int(start.y)),
                radius,
            )

        head = centers[0]
        pygame.draw.circle(
            surface,
            color,
            (int(head.x), int(head.y)),
            radius,
        )

    def draw_glossy_segment(self, surface, start, end, base, index, time):
        """Draw one segment with shading, a scale ring, and a gloss line."""
        delta = end - start
        if delta.length_squared() > 0.001:
            perpendicular = pygame.Vector2(-delta.y, delta.x).normalize()
        else:
            perpendicular = pygame.Vector2(0, -1)

        # Keep the light source consistently above the snake.
        if perpendicular.y > 0:
            perpendicular = -perpendicular

        # Base tube.
        pygame.draw.line(surface, base, start, end, BODY_WIDTH)
        pygame.draw.circle(
            surface,
            base,
            (int(start.x), int(start.y)),
            BODY_RADIUS,
        )

        # Segment ring and a darker underside add volume.
        pygame.draw.circle(
            surface,
            lerp_color(base, BACKGROUND, 0.30),
            (int(start.x), int(start.y)),
            BODY_RADIUS - 2,
            1,
        )
        pygame.draw.line(
            surface,
            lerp_color(base, BACKGROUND, 0.36),
            start - perpendicular * 5,
            end - perpendicular * 5,
            4,
        )

        # Soft glossy strip toward the top edge.
        gloss = lerp_color(base, (235, 255, 250), 0.62)
        offset = perpendicular * (BODY_RADIUS * 0.42)
        pygame.draw.line(
            surface,
            gloss,
            start + offset,
            end + offset,
            max(2, int(BODY_WIDTH * 0.20)),
        )

        # Subtle moving specular glint.
        shimmer = (math.sin(time * 4.5 - index * 0.9) + 1.0) * 0.5
        glint = start + offset + delta * 0.30
        pygame.draw.circle(
            surface,
            (230, 255, 248),
            (int(glint.x), int(glint.y)),
            1 + int(round(shimmer * 1.5)),
        )

    def draw_eyes(
        self,
        surface,
        head_center,
        eye_time,
        look_target=None,
        dead=False,
    ):
        """Expressive eyes that blink, look at food, or become Xs."""
        direction = self.direction
        perpendicular = pygame.Vector2(-direction.y, direction.x)

        if dead:
            for side in (-1, 1):
                eye = head_center + direction * 5 + perpendicular * (side * 5)
                for angle in (math.pi / 4, -math.pi / 4):
                    offset = pygame.Vector2(
                        math.cos(angle), math.sin(angle)
                    ) * 3
                    pygame.draw.line(
                        surface,
                        (255, 120, 160),
                        eye - offset,
                        eye + offset,
                        2,
                    )
            return

        # Quick blink every few seconds.
        blink_phase = eye_time % 3.6
        openness = 1.0
        if blink_phase < 0.16:
            openness = 1.0 - 0.92 * math.sin(
                math.pi * blink_phase / 0.16
            )

        pupil_shift = direction * 1.6
        if look_target is not None:
            to_food = pygame.Vector2(look_target) - head_center
            if to_food.length_squared() > 0.001:
                pupil_shift += to_food.normalize() * 1.2

        for side in (-1, 1):
            eye = head_center + direction * 5 + perpendicular * (side * 5)
            eye_height = max(1, int(round(7 * openness)))
            eye_rect = pygame.Rect(0, 0, 6, eye_height)
            eye_rect.center = (int(eye.x), int(eye.y))

            pygame.draw.ellipse(surface, (238, 255, 250), eye_rect)
            if openness > 0.28:
                pupil = eye + pupil_shift
                pygame.draw.circle(
                    surface,
                    (3, 15, 22),
                    (int(pupil.x), int(pupil.y)),
                    max(1, int(round(2 * openness))),
                )
                pygame.draw.circle(
                    surface,
                    (210, 255, 250),
                    (int(pupil.x) - 1, int(pupil.y) - 1),
                    1,
                )
            else:
                pygame.draw.line(
                    surface,
                    (3, 35, 40),
                    (int(eye.x) - 3, int(eye.y)),
                    (int(eye.x) + 3, int(eye.y)),
                    1,
                )

    def draw(
        self,
        surface,
        progress=1.0,
        eye_time=0.0,
        look_target=None,
        dead=False,
        tint=None,
        tint_amount=0.0,
    ):
        """Draw the snake with neon glow, glossy segments, and eyes."""
        centers = self.visual_body(progress)
        span = len(centers)

        # Layered halos create the neon bloom.
        self.draw_chain(
            surface,
            centers,
            lerp_color(SNAKE_GLOW_OUTER, CYAN, 0.10),
            BODY_WIDTH + 16,
            BODY_RADIUS + 8,
        )
        self.draw_chain(
            surface,
            centers,
            SNAKE_GLOW_OUTER,
            BODY_WIDTH + 10,
            BODY_RADIUS + 5,
        )
        self.draw_chain(
            surface,
            centers,
            SNAKE_GLOW_INNER,
            BODY_WIDTH + 4,
            BODY_RADIUS + 2,
        )

        # Main body with a mint-to-teal gradient and glossy highlights.
        for index in range(span - 1, 0, -1):
            base = body_gradient(index, span)
            if tint is not None and tint_amount > 0:
                base = lerp_color(base, tint, min(1.0, tint_amount))
            self.draw_glossy_segment(
                surface,
                centers[index],
                centers[index - 1],
                base,
                index,
                eye_time,
            )

        # Distinct head with a glossy dome.
        head_center = centers[0]
        head_point = (int(head_center.x), int(head_center.y))
        head_color = HEAD_COLOR
        if tint is not None and tint_amount > 0:
            head_color = lerp_color(
                head_color,
                tint,
                min(1.0, tint_amount),
            )

        pygame.draw.circle(surface, head_color, head_point, HEAD_RADIUS)
        pygame.draw.circle(
            surface,
            lerp_color(head_color, BACKGROUND, 0.35),
            head_point,
            HEAD_RADIUS,
            2,
        )

        gloss_rect = pygame.Rect(0, 0, 11, 7)
        gloss_rect.center = (head_point[0] - 4, head_point[1] - 5)
        pygame.draw.ellipse(
            surface,
            lerp_color(head_color, (255, 255, 255), 0.75),
            gloss_rect,
        )
        pygame.draw.circle(
            surface,
            (255, 255, 255),
            (head_point[0] - 6, head_point[1] - 7),
            2,
        )

        self.draw_eyes(
            surface,
            head_center,
            eye_time,
            look_target=look_target,
            dead=dead,
        )


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        self.screen = configure_display(True)
        self.fullscreen = bool(self.screen.get_flags() & pygame.FULLSCREEN)
        pygame.display.set_caption("Neon Snake")
        self.clock = pygame.time.Clock()

        self.title_font = load_font(78, "bahnschrift", bold=True)
        self.menu_font = load_font(30, "bahnschrift", bold=True)
        self.number_font = load_font(26, "bahnschrift", bold=True)
        self.row_font = load_font(20, "bahnschrift", bold=True)
        self.small_font = load_font(19, "consolas")
        self.tiny_font = load_font(14, "consolas")

        self.high_scores, self.history = load_game_data()
        self.difficulty = "NORMAL"
        self.visual_time = 0.0
        self.button_animations = {}
        self.click_ripples = []
        self.mouse_position = (0, 0)
        self.setup_buttons()
        self.build_board_layers()
        self.build_menu_layers()

        self.snake = Snake()
        self.food = None
        self.score = 0
        self.level = 1
        self.food_eaten = 0
        self.move_delay = DIFFICULTIES[self.difficulty]["delay"]
        self.move_timer = 0.0
        self.over_reason = ""
        self.new_high_score = False
        self.paused = False
        self.particles = []
        self.collect_rings = []
        self.trail = []
        self.board_shake = (0, 0)
        self.anim_time = 0.0
        self.level_up_timer = 0.0
        self.death_timer = 0.0
        self.death_total = DEATH_DURATION
        self.death_origin = pygame.Vector2(
            BOARD_WIDTH // 2,
            BOARD_HEIGHT // 2,
        )
        self.death_kind = ""
        self.state = "menu"
        self.running = True

    def setup_buttons(self):
        button_width = 200
        button_height = 104
        gap = 24
        total_width = button_width * 3 + gap * 2
        left = (WIDTH - total_width) // 2
        top = 225

        self.difficulty_buttons = {}
        for index, name in enumerate(DIFFICULTIES):
            self.difficulty_buttons[name] = pygame.Rect(
                left + index * (button_width + gap),
                top,
                button_width,
                button_height,
            )

        self.play_button = centered_rect(300, 64, 402)
        self.scores_button = centered_rect(300, 54, 482)
        self.quit_button = centered_rect(300, 54, 548)
        self.back_button = centered_rect(240, 54, 606)

        # End screen buttons, side by side.
        self.restart_button = centered_rect(230, 60, 455).move(-130, 0)
        self.menu_button = centered_rect(230, 60, 455).move(130, 0)

        # Small pause/resume control inside the HUD.
        self.pause_button = pygame.Rect(WIDTH - 134, HUD_Y + 8, 110, 34)

        # Buttons shown inside the pause card.
        self.resume_button = centered_rect(210, 52, 420).move(-115, 0)
        self.pause_menu_button = centered_rect(210, 52, 420).move(115, 0)

        self.all_button_rects = (
            list(self.difficulty_buttons.values())
            + [
                self.play_button,
                self.scores_button,
                self.quit_button,
                self.back_button,
                self.restart_button,
                self.menu_button,
                self.pause_button,
                self.resume_button,
                self.pause_menu_button,
            ]
        )

    def build_board_layers(self):
        # Pre-render the checkerboard.
        self.checkerboard = pygame.Surface(
            (BOARD_WIDTH, BOARD_HEIGHT),
            pygame.SRCALPHA,
        )
        self.checkerboard.fill(TILE_A)
        for row in range(ROWS):
            for col in range((row + 1) % 2, COLS, 2):
                pygame.draw.rect(
                    self.checkerboard,
                    TILE_B,
                    (col * CELL, row * CELL, CELL, CELL),
                )

        # Rounded mask for the board corners.
        self.board_mask = pygame.Surface(
            (BOARD_WIDTH, BOARD_HEIGHT),
            pygame.SRCALPHA,
        )
        pygame.draw.rect(
            self.board_mask,
            (255, 255, 255, 255),
            self.board_mask.get_rect(),
            border_radius=18,
        )

        self.board_surface = pygame.Surface(
            (BOARD_WIDTH, BOARD_HEIGHT),
            pygame.SRCALPHA,
        )

        # Reusable layers for trail, collection rings, and the death effect.
        self.effect_layer = pygame.Surface(
            (BOARD_WIDTH, BOARD_HEIGHT),
            pygame.SRCALPHA,
        )
        # Particles live on their own layer so they can glow above the snake.
        self.particle_layer = pygame.Surface(
            (BOARD_WIDTH, BOARD_HEIGHT),
            pygame.SRCALPHA,
        )
        self.death_layer = pygame.Surface(
            (BOARD_WIDTH, BOARD_HEIGHT),
            pygame.SRCALPHA,
        )
        self.death_flash = pygame.Surface(
            (BOARD_WIDTH, BOARD_HEIGHT),
        )

    def build_menu_layers(self):
        # Smooth vertical gradient for the menu and score screens.
        self.menu_background = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            color = lerp_color(MENU_TOP, MENU_BOTTOM, y / (HEIGHT - 1))
            pygame.draw.line(
                self.menu_background,
                color,
                (0, y),
                (WIDTH, y),
            )

        # Soft neon ambience behind the menu content.
        self.menu_glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for center_x, center_y, radius, color in (
            (round(WIDTH * 0.20), 130, 280, NEON_GREEN),
            (round(WIDTH * 0.81), 570, 320, PURPLE),
            (round(WIDTH * 0.73), 110, 230, CYAN),
        ):
            for step in range(6, 0, -1):
                alpha = int(3 + (6 - step) * 2.5)
                pygame.draw.circle(
                    self.menu_glow,
                    (*color, alpha),
                    (center_x, center_y),
                    int(radius * step / 6),
                )

        self.menu_particle_layer = pygame.Surface(
            (WIDTH, HEIGHT),
            pygame.SRCALPHA,
        )
        self.menu_particles = []
        particle_count = max(
            55,
            round(55 * WIDTH / BASE_WIDTH),
        )
        for _ in range(particle_count):
            self.menu_particles.append(
                {
                    "x": random.uniform(0, WIDTH),
                    "y": random.uniform(0, HEIGHT),
                    "radius": random.uniform(0.8, 2.4),
                    "speed": random.uniform(5, 18),
                    "phase": random.uniform(0, math.tau),
                    "wobble": random.uniform(0.4, 1.2),
                    "drift": random.uniform(2, 8),
                    "color": random.choice(MENU_PARTICLE_COLORS),
                }
            )

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.update_visuals(dt)
            self.draw()

        pygame.quit()

    def update_visuals(self, dt):
        """Animate menu particles, buttons, and click ripples."""
        self.visual_time += dt

        for particle in self.menu_particles:
            particle["phase"] += particle["wobble"] * dt
            particle["y"] -= particle["speed"] * dt
            particle["x"] += (
                math.sin(particle["phase"]) * particle["drift"] * dt
            )

            if particle["y"] < -10:
                particle["y"] = HEIGHT + random.uniform(0, 40)
                particle["x"] = random.uniform(0, WIDTH)
            if particle["x"] < -10:
                particle["x"] = WIDTH + 10
            elif particle["x"] > WIDTH + 10:
                particle["x"] = -10

        mouse_position = self.mouse_position
        active_ids = {id(rect) for rect in self.active_buttons()}
        for rect in self.all_button_rects:
            animation = self.button_animation(rect)
            hovered = (
                id(rect) in active_ids
                and rect.collidepoint(mouse_position)
            )
            target = 1.0 if hovered else 0.0
            animation["hover"] += (
                target - animation["hover"]
            ) * min(1.0, dt * 14.0)
            animation["press"] = max(
                0.0,
                animation["press"] - dt * 4.5,
            )

        for ripple in self.click_ripples:
            ripple["life"] -= dt
        self.click_ripples = [
            ripple for ripple in self.click_ripples if ripple["life"] > 0
        ]

        # Death particles and collection rings keep animating on end screens.
        if self.state != "playing":
            self.update_effects(dt)

        if self.death_timer > 0:
            self.death_timer = max(0.0, self.death_timer - dt)
            # Decaying screen-shake driven by visual_time, which keeps
            # running after the game state stops updating.
            strength = self.death_timer / self.death_total
            magnitude = 11.0 * strength ** 1.4
            self.board_shake = (
                int(round(math.sin(self.visual_time * 63.0) * magnitude)),
                int(
                    round(
                        math.cos(self.visual_time * 49.0)
                        * magnitude
                        * 0.8
                    )
                ),
            )
        else:
            self.board_shake = (0, 0)

        self.update_trail(dt)

    def move_progress(self):
        """Fraction between the previous and current grid positions."""
        if self.state == "playing" and self.move_delay > 0:
            return max(0.0, min(1.0, self.move_timer / self.move_delay))
        return 1.0

    def visual_head_center(self):
        progress = self.move_progress()
        return self.snake.visual_body(progress)[0]

    def update_trail(self, dt):
        for point in self.trail:
            point["life"] -= dt
        self.trail = [point for point in self.trail if point["life"] > 0]

        if self.state != "playing" or self.paused:
            return

        center = self.visual_head_center()
        if not self.trail or (
            center - self.trail[-1]["pos"]
        ).length() >= 3.0:
            self.trail.append(
                {
                    "pos": center,
                    "life": 0.30,
                    "max_life": 0.30,
                    "radius": BODY_RADIUS * 0.85,
                }
            )
            if len(self.trail) > 36:
                self.trail.pop(0)

    def active_buttons(self):
        if self.state == "menu":
            return list(self.difficulty_buttons.values()) + [
                self.play_button,
                self.scores_button,
                self.quit_button,
            ]
        if self.state == "playing":
            if self.paused:
                return [
                    self.pause_button,
                    self.resume_button,
                    self.pause_menu_button,
                ]
            return [self.pause_button]
        if self.state == "scores":
            return [self.back_button]
        if self.state in ("game_over", "win"):
            if self.state == "game_over" and self.death_timer > 0:
                return []
            return [self.restart_button, self.menu_button]
        return []

    def button_animation(self, rect):
        return self.button_animations.setdefault(
            id(rect),
            {"hover": 0.0, "press": 0.0},
        )

    def register_click(self, position):
        for rect in self.active_buttons():
            if rect.collidepoint(position):
                self.button_animation(rect)["press"] = 1.0
                self.click_ripples.append(
                    {
                        "pos": pygame.Vector2(position),
                        "life": 0.24,
                        "max_life": 0.24,
                    }
                )
                break

    # -----------------------------------------------------------------------
    # Events
    # -----------------------------------------------------------------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if self.state == "menu":
                    self.handle_menu_key(event.key)
                elif self.state == "playing":
                    self.handle_game_key(event.key)
                elif self.state in ("scores", "game_over", "win"):
                    if event.key == pygame.K_ESCAPE:
                        self.go_to_menu()

            elif event.type == pygame.MOUSEMOTION:
                self.mouse_position = event.pos

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.mouse_position = event.pos
                self.register_click(event.pos)
                if self.state == "menu":
                    self.handle_menu_click(event.pos)
                elif self.state == "playing":
                    if self.paused:
                        if self.resume_button.collidepoint(event.pos):
                            self.toggle_pause()
                        elif self.pause_menu_button.collidepoint(event.pos):
                            self.go_to_menu()
                        elif self.pause_button.collidepoint(event.pos):
                            self.toggle_pause()
                    elif self.pause_button.collidepoint(event.pos):
                        self.toggle_pause()
                elif self.state == "scores":
                    if self.back_button.collidepoint(event.pos):
                        self.go_to_menu()
                elif self.state in ("game_over", "win"):
                    if self.state == "game_over" and self.death_timer > 0:
                        continue
                    if self.restart_button.collidepoint(event.pos):
                        self.start_game()
                    elif self.menu_button.collidepoint(event.pos):
                        self.go_to_menu()

    def handle_menu_key(self, key):
        if key == pygame.K_RETURN:
            self.start_game()
        elif key == pygame.K_ESCAPE:
            self.running = False

    def handle_menu_click(self, position):
        for name, rect in self.difficulty_buttons.items():
            if rect.collidepoint(position):
                self.difficulty = name
                return

        if self.play_button.collidepoint(position):
            self.start_game()
        elif self.scores_button.collidepoint(position):
            self.state = "scores"
        elif self.quit_button.collidepoint(position):
            self.running = False

    def handle_game_key(self, key):
        if key == pygame.K_ESCAPE:
            # Leave fullscreen without interrupting the current run.
            self.toggle_fullscreen()
        elif key in (pygame.K_SPACE, pygame.K_p):
            self.toggle_pause()
        elif not self.paused and key in DIRECTIONS:
            self.snake.turn(DIRECTIONS[key])

    def toggle_fullscreen(self):
        """Switch display modes while keeping the run exactly as it was."""
        self.screen = configure_display(not self.fullscreen)
        self.fullscreen = bool(self.screen.get_flags() & pygame.FULLSCREEN)
        pygame.display.set_caption("Neon Snake")

        # Layout depends on the logical canvas width, so rebuild only the UI.
        self.setup_buttons()
        self.build_board_layers()
        self.build_menu_layers()
        self.button_animations.clear()
        self.click_ripples.clear()
        self.mouse_position = (0, 0)

    def toggle_pause(self):
        self.paused = not self.paused

    def go_to_menu(self):
        self.paused = False
        self.state = "menu"

    # -----------------------------------------------------------------------
    # Game state
    # -----------------------------------------------------------------------
    def start_game(self):
        config = DIFFICULTIES[self.difficulty]

        self.snake = Snake()
        self.score = 0
        self.level = 1
        self.food_eaten = 0
        self.move_delay = config["delay"]
        self.move_timer = 0.0
        self.over_reason = ""
        self.new_high_score = False
        self.paused = False
        self.particles = []
        self.collect_rings = []
        self.trail = []
        self.board_shake = (0, 0)
        self.anim_time = 0.0
        self.level_up_timer = 0.0
        self.death_timer = 0.0
        self.death_total = DEATH_DURATION
        self.death_origin = pygame.Vector2(
            BOARD_WIDTH // 2,
            BOARD_HEIGHT // 2,
        )
        self.death_kind = ""
        self.spawn_food()
        self.state = "playing"

    def spawn_food(self):
        cells = (
            pygame.Vector2(x, y)
            for x in range(COLS)
            for y in range(ROWS)
        )
        free_cells = [cell for cell in cells if cell not in self.snake.body]
        self.food = random.choice(free_cells) if free_cells else None

    def spawn_particles(self, position):
        """Create a bright burst and shockwave when an apple is eaten."""
        colors = (
            APPLE_RED,
            APPLE_LIGHT,
            APPLE_HIGHLIGHT,
            (255, 175, 70),
            (255, 255, 255),
        )

        for _ in range(26):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(70, 230)
            life = random.uniform(0.4, 0.85)
            self.particles.append(
                {
                    "pos": pygame.Vector2(position),
                    "vel": pygame.Vector2(
                        math.cos(angle),
                        math.sin(angle),
                    )
                    * speed,
                    "life": life,
                    "max_life": life,
                    "color": random.choice(colors),
                    "radius": random.uniform(1.5, 3.8),
                    "gravity": 45.0,
                }
            )

        # Two expanding rings give the pickup a satisfying pop.
        self.collect_rings.append(
            {
                "pos": pygame.Vector2(position),
                "life": 0.42,
                "max_life": 0.42,
                "color": APPLE_LIGHT,
            }
        )
        self.collect_rings.append(
            {
                "pos": pygame.Vector2(position),
                "life": 0.58,
                "max_life": 0.58,
                "color": APPLE_RED,
            }
        )

        # Keep the effect bounded during long games.
        if len(self.particles) > 300:
            self.particles = self.particles[-300:]

    def spawn_death_particles(self):
        """Dissolve the snake into a drifting neon burst."""
        colors = (
            GAME_OVER_COLOR,
            APPLE_RED,
            APPLE_LIGHT,
            (255, 235, 240),
            CYAN,
            NEON_GREEN,
        )

        for index, cell in enumerate(self.snake.body):
            position = cell_center(cell)
            count = 3 if index == 0 else 2
            for _ in range(count):
                angle = random.uniform(0, math.tau)
                speed = random.uniform(45, 210) * (1.4 if index == 0 else 1.0)
                life = random.uniform(0.45, 1.05)
                self.particles.append(
                    {
                        "pos": pygame.Vector2(position),
                        "vel": pygame.Vector2(
                            math.cos(angle),
                            math.sin(angle),
                        )
                        * speed,
                        "life": life,
                        "max_life": life,
                        "color": random.choice(colors),
                        "radius": random.uniform(1.5, 4.0),
                        "gravity": 90.0,
                    }
                )

        if len(self.particles) > 420:
            self.particles = self.particles[-420:]

    def begin_death(self, kind):
        """Start the death animation while the run state stays intact."""
        self.death_kind = kind
        self.death_timer = DEATH_DURATION
        self.death_total = DEATH_DURATION
        self.death_origin = cell_center(self.snake.body[0])
        self.spawn_death_particles()

    def update_effects(self, dt):
        if self.level_up_timer > 0:
            self.level_up_timer = max(0.0, self.level_up_timer - dt)

        for ring in self.collect_rings:
            ring["life"] -= dt
        self.collect_rings = [
            ring for ring in self.collect_rings if ring["life"] > 0
        ]

        alive = []
        for particle in self.particles:
            particle["life"] -= dt
            if particle["life"] <= 0:
                continue

            particle["vel"] = particle["vel"] + pygame.Vector2(
                0,
                particle.get("gravity", 0.0) * dt,
            )
            particle["pos"] += particle["vel"] * dt
            particle["vel"] = particle["vel"] * max(0.0, 1.0 - 3.0 * dt)
            alive.append(particle)

        self.particles = alive

    def update(self, dt):
        if self.state != "playing" or self.paused:
            return

        self.anim_time += dt
        self.update_effects(dt)
        self.move_timer += dt
        if self.move_timer >= self.move_delay:
            self.move_timer = 0.0
            result = self.snake.move(self.food)

            if result in ("wall", "self"):
                self.begin_death(result)
                self.state = "game_over"
                self.over_reason = (
                    "The snake hit the wall"
                    if result == "wall"
                    else "The snake hit its own body"
                )
                self.finish_run()
            elif result == "ate":
                self.eat_food()

    def eat_food(self):
        self.food_eaten += 1
        self.score += POINTS_PER_FOOD * self.level

        if self.food is not None:
            self.spawn_particles(cell_center(self.food))

        if self.food_eaten % FOOD_PER_LEVEL == 0:
            self.level += 1
            self.level_up_timer = LEVEL_UP_DURATION
            config = DIFFICULTIES[self.difficulty]
            self.move_delay = max(
                config["min_delay"],
                config["delay"] - (self.level - 1) * SPEED_STEP,
            )

        if len(self.snake.body) >= COLS * ROWS:
            self.food = None
            self.win_game()
        else:
            self.spawn_food()

    def win_game(self):
        self.state = "win"
        self.over_reason = "You filled the entire grid!"
        self.finish_run(won=True)

    def finish_run(self, won=False):
        """Record every completed run for the leaderboard."""
        self.history.append(
            {
                "score": self.score,
                "level": self.level,
                "difficulty": self.difficulty,
                "won": won,
            }
        )
        self.history.sort(
            key=lambda run: (run["score"], run["level"]),
            reverse=True,
        )
        self.history = self.history[:HISTORY_LIMIT]
        self.new_high_score = self.record_high_score()
        save_game_data(self.high_scores, self.history)

    def record_high_score(self):
        best = self.high_scores[self.difficulty]
        current = (self.score, self.level)
        previous = (best["score"], best["level"])

        if current > previous:
            self.high_scores[self.difficulty] = {
                "score": self.score,
                "level": self.level,
            }
            return True

        return False

    # -----------------------------------------------------------------------
    # Drawing
    # -----------------------------------------------------------------------
    def draw(self):
        self.screen.fill(BACKGROUND)

        if self.state in ("menu", "scores"):
            self.draw_menu_background()
            if self.state == "menu":
                self.draw_menu()
            else:
                self.draw_high_scores()
        else:
            self.draw_board()

            if self.state == "game_over" and self.death_timer > 0:
                self.draw_death_effect()

            if self.state == "playing":
                self.draw_level_up_effect()
                if self.paused:
                    self.draw_pause_overlay()

            self.draw_hud()

            if self.state == "game_over":
                if self.death_timer <= 0:
                    self.draw_game_over()
            elif self.state == "win":
                self.draw_win_screen()

        self.draw_click_ripples()
        pygame.display.flip()

    def draw_click_ripples(self):
        if not self.click_ripples:
            return

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for ripple in self.click_ripples:
            progress = 1.0 - ripple["life"] / ripple["max_life"]
            radius = int(10 + 32 * progress)
            alpha = int(140 * (1.0 - progress))
            if alpha <= 0:
                continue
            pygame.draw.circle(
                overlay,
                (*NEON_DIM, alpha),
                (int(ripple["pos"].x), int(ripple["pos"].y)),
                radius,
                width=2,
            )

        self.screen.blit(overlay, (0, 0))

    def blit_text(self, text, font, color, **anchor):
        image = font.render(text, True, color)
        self.screen.blit(image, image.get_rect(**anchor))

    def draw_centered(self, text, font, color, y):
        self.blit_text(text, font, color, center=(WIDTH // 2, y))

    def draw_panel(self, rect, fill=BUTTON_FILL, border=NEON_DARK):
        pygame.draw.rect(self.screen, fill, rect, border_radius=10)
        pygame.draw.rect(
            self.screen,
            border,
            rect,
            width=2,
            border_radius=10,
        )

    def draw_glow_panel(self, rect, accent, fill=PANEL_COLOR):
        for spread, strength in ((18, 0.22), (12, 0.42), (6, 0.7)):
            pygame.draw.rect(
                self.screen,
                lerp_color(BACKGROUND, accent, strength),
                rect.inflate(spread, spread),
                width=1,
                border_radius=18,
            )
        pygame.draw.rect(self.screen, fill, rect, border_radius=14)
        pygame.draw.rect(
            self.screen,
            accent,
            rect,
            width=2,
            border_radius=14,
        )

    def draw_accent_strip(self, rect, y):
        colors = (NEON_GREEN, CYAN, PURPLE)
        total_width = rect.width - 28
        segment = total_width // 3
        for index, color in enumerate(colors):
            start = rect.left + 14 + index * segment
            end = (
                rect.left + 14 + total_width
                if index == 2
                else start + segment
            )
            pygame.draw.line(
                self.screen,
                color,
                (start, y),
                (end, y),
                2,
            )

    def draw_overlay(self, width, height, alpha, position=(0, 0)):
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill(BACKGROUND + (alpha,))
        self.screen.blit(overlay, position)

    def draw_glow_text(self, text, font, y, color=NEON, glow_color=None):
        glow = font.render(text, True, glow_color or NEON_DIM)
        glow.set_alpha(55)

        for dx, dy in (
            (-4, 0),
            (4, 0),
            (0, -4),
            (0, 4),
            (-3, -3),
            (3, -3),
            (-3, 3),
            (3, 3),
        ):
            rect = glow.get_rect(center=(WIDTH // 2 + dx, y + dy))
            self.screen.blit(glow, rect)

        self.draw_centered(text, font, color, y)

    def draw_button(
        self,
        rect,
        label,
        selected=False,
        primary=False,
        font=None,
    ):
        font = font or self.menu_font
        animation = self.button_animation(rect)
        hover = animation["hover"]
        press = animation["press"]

        # A small inward shift gives the button a tactile click.
        draw_rect = rect.move(0, int(2 * press)).inflate(
            -int(4 * press),
            -int(4 * press),
        )

        if primary:
            fill = lerp_color(GREEN_DIM, NEON_GREEN, hover)
            border = NEON_GREEN
            text_color = BACKGROUND
        elif selected:
            pulse = 0.5 + 0.5 * math.sin(self.visual_time * 3.0)
            fill = lerp_color(
                NEON_DARK,
                (0, 95, 88),
                hover * 0.6 + pulse * 0.15,
            )
            border = NEON
            text_color = NEON
        else:
            fill = lerp_color(BUTTON_FILL, BUTTON_HOVER_FILL, hover)
            border = lerp_color(BUTTON_BORDER, NEON_DIM, hover)
            text_color = lerp_color(TEXT_COLOR, (245, 255, 255), hover)

        glow = max(hover, press * 0.8)
        if glow > 0.03:
            glow_color = NEON_GREEN if primary else NEON_DIM
            pygame.draw.rect(
                self.screen,
                lerp_color(BACKGROUND, glow_color, 0.16 + 0.3 * glow),
                draw_rect.inflate(
                    10 + int(6 * glow),
                    10 + int(6 * glow),
                ),
                width=1,
                border_radius=14,
            )

        self.draw_panel(draw_rect, fill, border)

        if selected:
            pulse = 0.5 + 0.5 * math.sin(self.visual_time * 3.0)
            pygame.draw.rect(
                self.screen,
                lerp_color(NEON_DARK, (0, 150, 135), pulse),
                draw_rect.inflate(8, 8),
                width=1,
                border_radius=14,
            )

        if press > 0.02:
            pygame.draw.line(
                self.screen,
                lerp_color(BUTTON_FILL, (0, 0, 0), press * 0.4),
                (draw_rect.left + 10, draw_rect.top + 3),
                (draw_rect.right - 10, draw_rect.top + 3),
                1,
            )

        self.blit_text(label, font, text_color, center=draw_rect.center)

    def draw_menu_background(self):
        self.screen.blit(self.menu_background, (0, 0))

        for x in range(0, WIDTH + 1, 60):
            pygame.draw.line(
                self.screen,
                MENU_GRID,
                (x, 0),
                (x, HEIGHT),
            )

        for y in range(0, HEIGHT + 1, 60):
            pygame.draw.line(
                self.screen,
                MENU_GRID,
                (0, y),
                (WIDTH, y),
            )

        self.screen.blit(self.menu_glow, (0, 0))
        self.draw_menu_particles()

    def draw_menu_particles(self):
        layer = self.menu_particle_layer
        layer.fill((0, 0, 0, 0))

        for particle in self.menu_particles:
            twinkle = 0.5 + 0.5 * math.sin(
                self.visual_time * 2.0 + particle["phase"]
            )
            alpha = int(45 + 90 * twinkle)
            color = particle["color"]
            x = int(particle["x"])
            y = int(particle["y"])

            pygame.draw.circle(
                layer,
                (*color, max(10, alpha // 3)),
                (x, y),
                max(2, int(particle["radius"] * 3)),
            )
            pygame.draw.circle(
                layer,
                (*color, alpha),
                (x, y),
                max(1, int(particle["radius"])),
            )

        self.screen.blit(layer, (0, 0))

    def draw_pulsing_title(
        self,
        text,
        y,
        font=None,
        color=None,
        glow_color=None,
    ):
        font = font or self.title_font
        color = color or NEON_GREEN
        glow_color = glow_color or NEON_DIM
        pulse = 0.5 + 0.5 * math.sin(self.visual_time * 2.6)
        glow = font.render(text, True, glow_color)

        for distance, base_alpha in ((3, 50), (6, 34), (9, 20)):
            glow.set_alpha(int(base_alpha * (0.65 + 0.7 * pulse)))
            for step in range(8):
                angle = math.tau * step / 8
                offset = (
                    int(math.cos(angle) * distance),
                    int(math.sin(angle) * distance),
                )
                rect = glow.get_rect(
                    center=(WIDTH // 2 + offset[0], y + offset[1])
                )
                self.screen.blit(glow, rect)

        # Subtle cyan and purple chromatic light.
        for shadow_color, offset_x in ((CYAN, -2), (PURPLE, 2)):
            shadow = font.render(text, True, shadow_color)
            shadow.set_alpha(int(30 + 30 * pulse))
            self.screen.blit(
                shadow,
                shadow.get_rect(center=(WIDTH // 2 + offset_x, y)),
            )

        title_color = lerp_color(color, MINT, 0.1 + 0.3 * pulse)
        self.draw_centered(text, font, title_color, y)

    def draw_difficulty_card(self, name, rect, selected):
        animation = self.button_animation(rect)
        hover = animation["hover"]
        press = animation["press"]
        accent = DIFFICULTY_COLORS[name]
        pulse = 0.5 + 0.5 * math.sin(self.visual_time * 3.0)

        draw_rect = rect.move(0, int(2 * press)).inflate(
            -int(4 * press),
            -int(4 * press),
        )

        if selected:
            fill = lerp_color(PANEL_COLOR, accent, 0.12 + 0.06 * pulse)
            border = accent
        else:
            fill = lerp_color(PANEL_COLOR, PANEL_ALT, hover)
            border = lerp_color(BORDER_DIM, accent, 0.25 + hover * 0.6)

        intensity = max(hover, 0.55 if selected else 0.0)
        if intensity > 0.04:
            for spread, strength in (
                (14, 0.10 + 0.12 * intensity),
                (8, 0.22 + 0.20 * intensity),
                (3, min(1.0, 0.5 + 0.5 * intensity)),
            ):
                pygame.draw.rect(
                    self.screen,
                    lerp_color(BACKGROUND, accent, strength),
                    draw_rect.inflate(spread, spread),
                    width=1,
                    border_radius=18,
                )

        self.draw_panel(draw_rect, fill, border)

        # Accent strip across the top of the card.
        pygame.draw.line(
            self.screen,
            accent,
            (draw_rect.left + 14, draw_rect.top + 2),
            (draw_rect.right - 14, draw_rect.top + 2),
            2,
        )

        self.blit_text(
            name,
            self.menu_font,
            TEXT_COLOR if not selected else accent,
            midleft=(draw_rect.left + 16, draw_rect.top + 32),
        )
        self.blit_text(
            DIFFICULTY_TAGS[name],
            self.tiny_font,
            accent if selected else MUTED_COLOR,
            midleft=(draw_rect.left + 16, draw_rect.top + 55),
        )

        # Small difficulty meter.
        level = list(DIFFICULTIES).index(name) + 1
        for index in range(3):
            bar = pygame.Rect(
                draw_rect.left + 16 + index * 23,
                draw_rect.top + 78,
                18,
                4,
            )
            pygame.draw.rect(
                self.screen,
                accent if index < level else (19, 42, 55),
                bar,
                border_radius=2,
            )

        best = self.high_scores[name]["score"]
        self.blit_text(
            f"BEST {best}",
            self.tiny_font,
            MUTED_COLOR,
            midright=(draw_rect.right - 16, draw_rect.top + 80),
        )

        if selected:
            pygame.draw.circle(
                self.screen,
                accent,
                (draw_rect.right - 18, draw_rect.top + 20),
                4,
            )

    def draw_menu(self):
        self.draw_pulsing_title("NEON SNAKE", 105)
        self.draw_centered(
            "CYBER ARCADE // SNAKE",
            self.tiny_font,
            CYAN,
            165,
        )
        self.draw_centered(
            "CHOOSE YOUR DIFFICULTY",
            self.small_font,
            MUTED_COLOR,
            203,
        )

        for name, rect in self.difficulty_buttons.items():
            self.draw_difficulty_card(
                name,
                rect,
                selected=(name == self.difficulty),
            )

        self.draw_button(self.play_button, "PLAY", primary=True)
        self.draw_button(self.scores_button, "HIGH SCORES")
        self.draw_button(self.quit_button, "QUIT")

        best_score = max(best["score"] for best in self.high_scores.values())
        stats_rect = centered_rect(380, 34, 612)
        self.draw_panel(stats_rect, PANEL_COLOR, BORDER_DIM)
        self.blit_text(
            f"BEST {best_score}   //   {len(self.history)} RUNS RECORDED",
            self.tiny_font,
            MUTED_COLOR,
            center=stats_rect.center,
        )

        self.draw_centered(
            "ENTER: play    ESC: quit",
            self.tiny_font,
            MUTED_COLOR,
            665,
        )

    def draw_high_scores(self):
        self.draw_pulsing_title(
            "HIGH SCORES",
            80,
            color=NEON_GREEN,
            glow_color=CYAN,
        )
        self.draw_centered(
            f"{len(self.history)} RUNS RECORDED   //   TOP 8",
            self.tiny_font,
            CYAN,
            148,
        )

        # Per-difficulty best cards.
        card_width = 210
        gap = 20
        total_width = card_width * 3 + gap * 2
        left = (WIDTH - total_width) // 2
        top = 172

        for index, name in enumerate(DIFFICULTIES):
            card = pygame.Rect(
                left + index * (card_width + gap),
                top,
                card_width,
                68,
            )
            accent = DIFFICULTY_COLORS[name]
            best = self.high_scores[name]

            self.draw_panel(
                card,
                PANEL_COLOR,
                lerp_color(BORDER_DIM, accent, 0.65),
            )
            pygame.draw.line(
                self.screen,
                accent,
                (card.left + 12, card.top + 2),
                (card.right - 12, card.top + 2),
                2,
            )
            self.blit_text(
                name,
                self.tiny_font,
                accent,
                midleft=(card.left + 14, card.top + 15),
            )
            self.blit_text(
                str(best["score"]),
                self.number_font,
                TEXT_COLOR,
                midleft=(card.left + 14, card.top + 43),
            )
            self.blit_text(
                f"LVL {best['level']}",
                self.tiny_font,
                MUTED_COLOR,
                midright=(card.right - 14, card.top + 46),
            )

        # History leaderboard, directly beneath the difficulty cards.
        panel = centered_rect(min(900, WIDTH - 160), 310, 415)
        self.draw_glow_panel(panel, NEON_GREEN)
        self.draw_accent_strip(panel, panel.top + 2)

        rank_x = panel.left + int(panel.width * 0.10)
        score_x = panel.left + int(panel.width * 0.35)
        level_x = panel.left + int(panel.width * 0.60)
        mode_x = panel.left + int(panel.width * 0.85)

        columns = (
            (rank_x, "RANK"),
            (score_x, "SCORE"),
            (level_x, "LEVEL"),
            (mode_x, "MODE"),
        )
        for x, label in columns:
            self.blit_text(
                label,
                self.tiny_font,
                MUTED_COLOR,
                center=(x, panel.top + 26),
            )

        if not self.history:
            self.blit_text(
                "NO RUNS RECORDED YET  -  PLAY A GAME",
                self.small_font,
                MUTED_COLOR,
                center=panel.center,
            )
        else:
            for index, run in enumerate(self.history[:8]):
                y = panel.top + 46 + index * 31
                row = pygame.Rect(
                    panel.left + 10,
                    y,
                    panel.width - 20,
                    27,
                )
                row_fill = (
                    PANEL_ALT if index % 2 == 0 else PANEL_COLOR
                )
                pygame.draw.rect(
                    self.screen,
                    row_fill,
                    row,
                    border_radius=6,
                )

                if index < 3:
                    medal = (GOLD, SILVER, BRONZE)[index]
                    pygame.draw.rect(
                        self.screen,
                        medal,
                        (row.left, row.top, 3, row.height),
                        border_radius=2,
                    )
                else:
                    medal = MUTED_COLOR

                self.blit_text(
                    f"{index + 1:02d}",
                    self.row_font,
                    medal,
                    center=(rank_x, row.centery),
                )
                self.blit_text(
                    str(run["score"]),
                    self.row_font,
                    TEXT_COLOR,
                    center=(score_x, row.centery),
                )
                self.blit_text(
                    str(run["level"]),
                    self.small_font,
                    TEXT_COLOR,
                    center=(level_x, row.centery),
                )

                accent = DIFFICULTY_COLORS[run["difficulty"]]
                pill = pygame.Rect(0, 0, 74, 20)
                pill.center = (mode_x, row.centery)
                pygame.draw.rect(
                    self.screen,
                    lerp_color(PANEL_COLOR, accent, 0.16),
                    pill,
                    border_radius=10,
                )
                pygame.draw.rect(
                    self.screen,
                    accent,
                    pill,
                    width=1,
                    border_radius=10,
                )
                self.blit_text(
                    run["difficulty"],
                    self.tiny_font,
                    accent,
                    center=pill.center,
                )

        self.draw_button(self.back_button, "BACK")
        self.draw_centered(
            "ESC: back",
            self.tiny_font,
            MUTED_COLOR,
            652,
        )

    def draw_board(self):
        board = self.board_surface
        board.fill((0, 0, 0, 0))
        board.blit(self.checkerboard, (0, 0))

        # Trail and collection rings sit beneath the snake and apple.
        self.effect_layer.fill((0, 0, 0, 0))
        self.draw_trail(self.effect_layer)
        self.draw_collect_rings(self.effect_layer)
        board.blit(self.effect_layer, (0, 0))

        self.draw_food(board)

        death_progress = self.death_progress()
        tint = None
        tint_amount = 0.0
        if death_progress < 1.0:
            tint = GAME_OVER_COLOR
            tint_amount = 0.55 * max(
                0.0,
                1.0 - death_progress / 0.4,
            )

        self.snake.draw(
            board,
            self.move_progress(),
            self.anim_time,
            look_target=(
                cell_center(self.food) if self.food is not None else None
            ),
            dead=self.state == "game_over",
            tint=tint,
            tint_amount=tint_amount,
        )
        # Glowing particles sit above the snake but are clipped to the board.
        self.particle_layer.fill((0, 0, 0, 0))
        self.draw_particles(self.particle_layer)
        board.blit(self.particle_layer, (0, 0))

        # Round the board corners.
        board.blit(
            self.board_mask,
            (0, 0),
            special_flags=pygame.BLEND_RGBA_MULT,
        )
        offset_x, offset_y = self.board_shake
        self.screen.blit(
            board,
            (BOARD_X + offset_x, BOARD_Y + offset_y),
        )
        self.draw_board_border(self.board_shake)

    def draw_board_border(self, offset=(0, 0)):
        offset_x, offset_y = offset
        board_rect = BOARD_RECT.move(offset_x, offset_y)
        # Layered outlines create a soft neon glow.
        for inflate, width, color in (
            (14, 2, (0, 35, 48)),
            (8, 2, (0, 90, 95)),
            (2, 2, NEON),
        ):
            pygame.draw.rect(
                self.screen,
                color,
                board_rect.inflate(inflate, inflate),
                width=width,
                border_radius=22,
            )

        pygame.draw.rect(
            self.screen,
            NEON_DIM,
            board_rect.inflate(-2, -2),
            width=1,
            border_radius=16,
        )

    def death_progress(self):
        """0.0 at the moment of death, 1.0 when the animation is done."""
        if self.death_timer <= 0 or self.death_total <= 0:
            return 1.0
        return 1.0 - self.death_timer / self.death_total

    def draw_trail(self, layer):
        """A soft fading trail that follows the interpolated head."""
        for point in self.trail:
            fraction = max(0.0, point["life"] / point["max_life"])
            radius = max(
                1,
                int(point["radius"] * (0.35 + 0.65 * fraction)),
            )
            alpha = int(70 * fraction)
            if alpha <= 0:
                continue
            pygame.draw.circle(
                layer,
                (*NEON_DIM, alpha),
                (int(point["pos"].x), int(point["pos"].y)),
                radius,
            )

    def draw_collect_rings(self, layer):
        """Expanding shockwaves from a collected apple."""
        for ring in self.collect_rings:
            progress = 1.0 - ring["life"] / ring["max_life"]
            radius = int(10 + 30 * progress)
            alpha = int(170 * (1.0 - progress))
            if alpha <= 0:
                continue

            pygame.draw.circle(
                layer,
                (*ring["color"], alpha),
                (int(ring["pos"].x), int(ring["pos"].y)),
                radius,
                2,
            )
            pygame.draw.circle(
                layer,
                (*ring["color"], alpha // 3),
                (int(ring["pos"].x), int(ring["pos"].y)),
                radius + 4,
                1,
            )

    def draw_death_effect(self):
        """Flash, shockwave rings, and a red vignette around the board."""
        if self.death_timer <= 0:
            return

        progress = self.death_progress()
        elapsed = (1.0 - progress) * self.death_total
        origin = (
            int(self.death_origin.x),
            int(self.death_origin.y),
        )

        self.death_layer.fill((0, 0, 0, 0))

        for delay, duration in ((0.0, 0.75), (0.14, 0.85), (0.28, 0.95)):
            local = (elapsed - delay) / duration
            if not 0.05 <= local <= 1.0:
                continue

            radius = int(18 + 120 * local)
            alpha = int(170 * (1.0 - local) ** 1.4)
            if alpha <= 0:
                continue

            pygame.draw.circle(
                self.death_layer,
                (*GAME_OVER_COLOR, alpha),
                origin,
                radius,
                3,
            )
            pygame.draw.circle(
                self.death_layer,
                (*APPLE_LIGHT, alpha // 2),
                origin,
                radius + 6,
                1,
            )

        border_alpha = int(150 * max(0.0, 1.0 - progress))
        if border_alpha > 0:
            pygame.draw.rect(
                self.death_layer,
                (*GAME_OVER_COLOR, border_alpha),
                (0, 0, BOARD_WIDTH, BOARD_HEIGHT),
                width=6,
                border_radius=18,
            )

        offset_x, offset_y = self.board_shake
        self.screen.blit(
            self.death_layer,
            (BOARD_X + offset_x, BOARD_Y + offset_y),
        )

        flash = max(0.0, 1.0 - elapsed / 0.22)
        if flash > 0:
            self.death_flash.fill((255, 80, 110))
            self.death_flash.set_alpha(int(110 * flash))
            self.screen.blit(
                self.death_flash,
                (BOARD_X + offset_x, BOARD_Y + offset_y),
            )

    def draw_food(self, surface):
        """Draw a glossy apple with pulsing halo, rings, and sparkles."""
        if self.food is None:
            return

        center = cell_center(self.food)
        x, y = int(center.x), int(center.y)

        pulse = math.sin(self.anim_time * 5.5)
        squash = 1.0 + 0.06 * math.sin(
            self.anim_time * 5.5 + 0.7
        )
        radius = max(6, int(round(8.4 + 0.9 * pulse)))

        # Soft halo with two expanding pulse rings.
        halo = pygame.Surface((54, 54), pygame.SRCALPHA)
        for glow_radius, alpha in ((17, 26), (13, 40), (9, 55)):
            pygame.draw.circle(
                halo,
                (*APPLE_RED, alpha),
                (27, 27),
                glow_radius + int(pulse * 2),
            )
        for ring_index in range(2):
            phase = (self.anim_time * 0.8 + ring_index * 0.5) % 1.0
            ring_radius = int(11 + phase * 12)
            ring_alpha = int(70 * (1.0 - phase))
            if ring_alpha > 0:
                pygame.draw.circle(
                    halo,
                    (*APPLE_LIGHT, ring_alpha),
                    (27, 27),
                    ring_radius,
                    1,
                )
        surface.blit(halo, (x - 27, y - 27))

        # Body made from two lobes with a gentle squash.
        body_radius = max(5, int(radius * squash))
        pygame.draw.circle(
            surface,
            (150, 8, 24),
            (x, y + 2),
            body_radius + 1,
        )
        pygame.draw.circle(surface, APPLE_RED, (x - 3, y + 1), body_radius)
        pygame.draw.circle(surface, APPLE_RED, (x + 3, y + 1), body_radius)
        pygame.draw.circle(surface, (255, 62, 74), (x, y + 1), body_radius)

        # Glossy highlight and a bright specular dot.
        pygame.draw.ellipse(
            surface,
            APPLE_HIGHLIGHT,
            (
                x - 6,
                y - 5,
                max(3, body_radius // 2),
                max(2, body_radius // 3),
            ),
        )
        pygame.draw.circle(surface, (255, 255, 255), (x - 4, y - 4), 1)

        # Stem and a gently wobbling leaf.
        stem_top = y - body_radius - 3
        pygame.draw.line(
            surface,
            (105, 65, 35),
            (x, y - body_radius + 1),
            (x + 1, stem_top),
            2,
        )
        leaf_offset = int(round(math.sin(self.anim_time * 3.0) * 1.5))
        pygame.draw.ellipse(
            surface,
            (80, 220, 110),
            (x + 2, stem_top - 2 + leaf_offset, 7, 4),
        )
        pygame.draw.line(
            surface,
            (40, 160, 80),
            (x + 2, stem_top + leaf_offset),
            (x + 8, stem_top + leaf_offset),
            1,
        )

        # Small orbiting sparkles.
        for index in range(3):
            angle = self.anim_time * 1.6 + index * math.tau / 3
            orbit = body_radius + 5
            sparkle_x = int(x + math.cos(angle) * orbit)
            sparkle_y = int(y + math.sin(angle) * orbit * 0.75)
            alpha = 140 + int(
                80 * math.sin(self.anim_time * 4 + index)
            )
            sparkle = pygame.Surface((7, 7), pygame.SRCALPHA)
            pygame.draw.line(
                sparkle,
                (255, 220, 200, min(255, alpha)),
                (3, 0),
                (3, 6),
                1,
            )
            pygame.draw.line(
                sparkle,
                (255, 220, 200, min(255, alpha)),
                (0, 3),
                (6, 3),
                1,
            )
            surface.blit(sparkle, (sparkle_x - 3, sparkle_y - 3))

    def draw_particles(self, layer):
        """Soft glowing motes with a bright core."""
        for particle in self.particles:
            fraction = max(0.0, particle["life"] / particle["max_life"])
            radius = max(1, int(particle["radius"] * fraction))
            position = (
                int(particle["pos"].x),
                int(particle["pos"].y),
            )
            color = particle["color"]
            alpha = int(235 * fraction)
            if alpha <= 0:
                continue

            glow_alpha = max(10, int(85 * fraction))
            pygame.draw.circle(
                layer,
                (*color, glow_alpha),
                position,
                radius + 3,
            )
            pygame.draw.circle(
                layer,
                (*color, alpha),
                position,
                radius,
            )
            if radius >= 2:
                pygame.draw.circle(
                    layer,
                    (255, 255, 255, alpha),
                    position,
                    max(1, radius // 2),
                )

    def draw_level_up_effect(self):
        if self.level_up_timer <= 0:
            return

        progress = 1.0 - self.level_up_timer / LEVEL_UP_DURATION
        scale = 1.0 + 0.25 * max(0.0, 0.35 - progress) / 0.35
        if progress < 0.55:
            alpha = 255
        else:
            alpha = int(255 * max(0.0, (1.0 - progress) / 0.45))

        text = self.title_font.render("LEVEL UP!", True, WIN_COLOR)
        glow = self.title_font.render("LEVEL UP!", True, (255, 150, 50))

        def scaled(image, factor):
            size = (
                max(1, int(image.get_width() * factor)),
                max(1, int(image.get_height() * factor)),
            )
            return pygame.transform.smoothscale(image, size)

        text = scaled(text, scale)
        glow = scaled(glow, scale * 1.06)
        text.set_alpha(alpha)
        glow.set_alpha(alpha // 2)

        center = (
            BOARD_X + BOARD_WIDTH // 2,
            BOARD_Y + BOARD_HEIGHT // 2,
        )
        self.screen.blit(glow, glow.get_rect(center=center))
        self.screen.blit(text, text.get_rect(center=center))

    def draw_pause_overlay(self):
        self.draw_overlay(WIDTH, HEIGHT, 175)

        card = pygame.Rect(0, 0, 520, 268)
        card.center = (WIDTH // 2, 367)
        self.draw_glow_panel(card, CYAN)
        self.draw_accent_strip(card, card.top + 2)

        self.draw_glow_text(
            "PAUSED",
            self.title_font,
            card.top + 64,
            CYAN,
            PURPLE,
        )
        self.draw_centered(
            "GAME SUSPENDED",
            self.tiny_font,
            MUTED_COLOR,
            card.top + 112,
        )
        self.blit_text(
            f"SCORE {self.score}    //    LEVEL {self.level}"
            f"    //    {self.difficulty}",
            self.small_font,
            TEXT_COLOR,
            center=(WIDTH // 2, card.top + 145),
        )

        self.draw_button(
            self.resume_button,
            "RESUME",
            primary=True,
            font=self.small_font,
        )
        self.draw_button(
            self.pause_menu_button,
            "MAIN MENU",
            font=self.small_font,
        )

        self.draw_centered(
            "SPACE / P: RESUME   //   ESC: DISPLAY MODE",
            self.tiny_font,
            MUTED_COLOR,
            card.bottom - 22,
        )

    def draw_hud(self):
        pygame.draw.rect(
            self.screen,
            HUD_COLOR,
            (0, HUD_Y, WIDTH, HUD_HEIGHT),
        )
        pygame.draw.line(
            self.screen,
            NEON_DARK,
            (0, HUD_Y),
            (WIDTH, HUD_Y),
            2,
        )

        top = HUD_Y + 5
        height = HUD_HEIGHT - 10
        accent = DIFFICULTY_COLORS[self.difficulty]

        # Spread the cards across the available width, centered in fullscreen.
        margin = 12
        gap = 10
        right_edge = self.pause_button.left - 16
        score_width = 160
        level_width = 164
        best_width = 160
        available_width = right_edge - margin
        fixed_width = score_width + level_width + best_width + gap * 3
        progress_width = max(
            220,
            min(520, available_width - fixed_width),
        )
        total_width = fixed_width + progress_width
        left = margin + max(0, (available_width - total_width) // 2)

        # Score panel.
        score_rect = pygame.Rect(left, top, score_width, height)
        self.draw_panel(score_rect, PANEL_COLOR, BORDER_DIM)
        self.blit_text(
            "SCORE",
            self.tiny_font,
            MUTED_COLOR,
            midleft=(score_rect.left + 10, score_rect.centery),
        )
        self.blit_text(
            str(self.score),
            self.number_font,
            TEXT_COLOR,
            midright=(score_rect.right - 10, score_rect.centery),
        )

        # Level and current mode.
        level_rect = pygame.Rect(
            score_rect.right + gap,
            top,
            level_width,
            height,
        )
        self.draw_panel(level_rect, PANEL_COLOR, BORDER_DIM)
        self.blit_text(
            "LVL",
            self.tiny_font,
            MUTED_COLOR,
            midleft=(level_rect.left + 10, level_rect.centery),
        )
        self.blit_text(
            str(self.level),
            self.number_font,
            accent,
            midleft=(level_rect.left + 40, level_rect.centery),
        )

        mode_pill = pygame.Rect(0, 0, 70, 20)
        mode_pill.midright = (level_rect.right - 8, level_rect.centery)
        pygame.draw.rect(
            self.screen,
            lerp_color(PANEL_COLOR, accent, 0.18),
            mode_pill,
            border_radius=10,
        )
        pygame.draw.rect(
            self.screen,
            accent,
            mode_pill,
            width=1,
            border_radius=10,
        )
        self.blit_text(
            self.difficulty,
            self.tiny_font,
            accent,
            center=mode_pill.center,
        )

        # Progress toward the next level.
        progress_rect = pygame.Rect(
            level_rect.right + gap,
            top,
            progress_width,
            height,
        )
        self.draw_panel(progress_rect, PANEL_COLOR, BORDER_DIM)
        progress = self.food_eaten % FOOD_PER_LEVEL
        self.blit_text(
            "NEXT LEVEL",
            self.tiny_font,
            MUTED_COLOR,
            midleft=(progress_rect.left + 10, progress_rect.top + 13),
        )
        self.blit_text(
            f"{progress} / {FOOD_PER_LEVEL}",
            self.tiny_font,
            accent,
            midright=(progress_rect.right - 10, progress_rect.top + 13),
        )

        segments = FOOD_PER_LEVEL
        segment_gap = 4
        track_left = progress_rect.left + 10
        track_width = progress_rect.width - 20
        segment_width = (
            track_width - segment_gap * (segments - 1)
        ) // segments
        for index in range(segments):
            segment = pygame.Rect(
                track_left + index * (segment_width + segment_gap),
                progress_rect.top + 27,
                segment_width,
                6,
            )
            filled = index < progress
            pygame.draw.rect(
                self.screen,
                accent if filled else (19, 42, 55),
                segment,
                border_radius=3,
            )

        # Best score for the selected mode.
        best_rect = pygame.Rect(
            progress_rect.right + gap,
            top,
            best_width,
            height,
        )
        self.draw_panel(best_rect, PANEL_COLOR, BORDER_DIM)
        self.blit_text(
            "BEST",
            self.tiny_font,
            MUTED_COLOR,
            midleft=(best_rect.left + 10, best_rect.centery),
        )
        self.blit_text(
            str(self.high_scores[self.difficulty]["score"]),
            self.number_font,
            GOLD,
            midright=(best_rect.right - 10, best_rect.centery),
        )

        self.draw_button(
            self.pause_button,
            "RESUME" if self.paused else "PAUSE",
            primary=self.paused,
            font=self.small_font,
        )

    def draw_end_screen(self, title, title_color, message, glow_color):
        self.draw_overlay(WIDTH, HEIGHT, 215)

        accent = title_color
        card = pygame.Rect(0, 0, 640, 430)
        card.center = (WIDTH // 2, 356)
        self.draw_glow_panel(card, accent)
        self.draw_accent_strip(card, card.top + 2)

        self.draw_glow_text(
            title,
            self.title_font,
            card.top + 64,
            title_color,
            glow_color,
        )
        self.draw_centered(
            message,
            self.small_font,
            TEXT_COLOR,
            card.top + 124,
        )

        # Compact stat cards.
        stat_width = 168
        gap = 18
        total_width = stat_width * 3 + gap * 2
        stat_left = card.centerx - total_width // 2
        stat_top = card.top + 148
        stat_height = 68
        stats = (
            ("SCORE", str(self.score), TEXT_COLOR, BORDER_DIM),
            ("LEVEL", str(self.level), TEXT_COLOR, BORDER_DIM),
            (
                "MODE",
                self.difficulty,
                DIFFICULTY_COLORS[self.difficulty],
                DIFFICULTY_COLORS[self.difficulty],
            ),
        )

        for index, (label, value, value_color, border_color) in enumerate(
            stats
        ):
            stat_rect = pygame.Rect(
                stat_left + index * (stat_width + gap),
                stat_top,
                stat_width,
                stat_height,
            )
            self.draw_panel(
                stat_rect,
                PANEL_ALT,
                lerp_color(BORDER_DIM, border_color, 0.8),
            )
            self.blit_text(
                label,
                self.tiny_font,
                MUTED_COLOR,
                center=(stat_rect.centerx, stat_rect.top + 18),
            )
            self.blit_text(
                value,
                self.number_font,
                value_color,
                center=(stat_rect.centerx, stat_rect.top + 47),
            )

        if self.new_high_score:
            badge_text = "NEW HIGH SCORE!"
            badge_color = accent
        else:
            best = self.high_scores[self.difficulty]
            badge_text = f"BEST {best['score']}"
            badge_color = MUTED_COLOR

        badge = pygame.Rect(0, 0, 300, 32)
        badge.center = (WIDTH // 2, card.top + 250)
        self.draw_panel(
            badge,
            lerp_color(PANEL_COLOR, badge_color, 0.12),
            badge_color,
        )
        self.blit_text(
            badge_text,
            self.small_font,
            badge_color,
            center=badge.center,
        )

        self.draw_button(
            self.restart_button,
            "RESTART",
            primary=True,
        )
        self.draw_button(self.menu_button, "MAIN MENU")

        self.draw_centered(
            "ESC: RETURN TO MENU",
            self.tiny_font,
            MUTED_COLOR,
            card.bottom - 30,
        )

    def draw_game_over(self):
        self.draw_end_screen(
            "GAME OVER",
            GAME_OVER_COLOR,
            self.over_reason,
            (150, 20, 55),
        )

    def draw_win_screen(self):
        self.draw_end_screen(
            "YOU WIN!",
            WIN_COLOR,
            self.over_reason,
            (170, 120, 20),
        )


def main():
    Game().run()


if __name__ == "__main__":
    main()
