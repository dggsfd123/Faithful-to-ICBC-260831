import os
import sys
import csv
import math
import random
import pygame

pygame.init()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
GROUND_Y = SCREEN_HEIGHT - 60
MAX_LIVES = 3
INVINCIBLE_FRAMES = 90

ASSETS = {
    "background": os.path.join(BASE_DIR, "background_test.png"),
    "player": os.path.join(BASE_DIR, "player.png"),
    "wall": os.path.join(BASE_DIR, "wall.png"),
    "hurt": os.path.join(BASE_DIR, "hurt.png"),
    "gold": os.path.join(BASE_DIR, "gold.png"),
}
RANKING_FILE = os.path.join(BASE_DIR, "ranking.csv")

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (80, 80, 80)
LIGHT_GRAY = (230, 230, 230)
BLUE = (70, 130, 180)
RED = (220, 60, 60)
GREEN = (60, 180, 80)
GOLD = (255, 215, 0)

DIFFICULTIES = {
    "easy": {
        "name": "简单",
        "speed": 5,
        "spawn_min": 1500,
        "spawn_max": 2600,
        "wall_prob": 0.55,
        "hurt_prob": 0.15,
        "gold_prob": 0.30,
        "hurt_extra": 3,
        "gold_extra": 2,
    },
    "medium": {
        "name": "中等",
        "speed": 8,
        "spawn_min": 1100,
        "spawn_max": 2000,
        "wall_prob": 0.40,
        "hurt_prob": 0.35,
        "gold_prob": 0.25,
        "hurt_extra": 5,
        "gold_extra": 3,
    },
    "hard": {
        "name": "困难",
        "speed": 12,
        "spawn_min": 700,
        "spawn_max": 1400,
        "wall_prob": 0.30,
        "hurt_prob": 0.50,
        "gold_prob": 0.20,
        "hurt_extra": 7,
        "gold_extra": 4,
    },
}


def load_image(path, scale=None):
    img = pygame.image.load(path).convert_alpha()
    if scale:
        img = pygame.transform.scale(img, scale)
    return img


def circles_overlap(center1, radius1, center2, radius2):
    dx = center1[0] - center2[0]
    dy = center1[1] - center2[1]
    return dx * dx + dy * dy <= (radius1 + radius2) ** 2


def heart_points(width, cx, cy):
    raw = []
    for i in range(64):
        t = 2 * math.pi * i / 64
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        raw.append((x, y))
    xs = [p[0] for p in raw]
    ys = [p[1] for p in raw]
    scale = width / (max(xs) - min(xs))
    mid_x = (min(xs) + max(xs)) / 2
    mid_y = (min(ys) + max(ys)) / 2
    return [(cx + (x - mid_x) * scale, cy + (y - mid_y) * scale) for x, y in raw]


class GameObject:
    def __init__(self, obj_type, image, x, y, speed, radius):
        self.type = obj_type
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.speed = speed
        self.radius = radius

    @property
    def center(self):
        return self.rect.center

    def update(self):
        self.rect.x -= self.speed

    def draw(self, screen):
        screen.blit(self.image, self.rect)

    def off_screen(self):
        return self.rect.right < 0


class Particle:
    def __init__(self, x, y, color, speed=6, size=5, life=40, gravity=0.15):
        angle = random.uniform(0, math.tau)
        v = random.uniform(speed * 0.35, speed)
        self.x = float(x)
        self.y = float(y)
        self.vx = math.cos(angle) * v
        self.vy = math.sin(angle) * v
        self.gravity = gravity
        self.size = size
        self.life = life
        self.max_life = life
        r = size + 1
        self.image = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (r, r), size)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.vx *= 0.99
        self.life -= 1

    @property
    def alive(self):
        return self.life > 0

    def draw(self, surf):
        self.image.set_alpha(max(0, int(255 * self.life / self.max_life)))
        surf.blit(self.image, (self.x - self.size - 1, self.y - self.size - 1))


class FloatingText:
    def __init__(self, text, x, y, color, font, life=55, vy=-1.8):
        self.image = font.render(text, True, color)
        self.rect = self.image.get_rect(center=(x, y))
        self.life = life
        self.max_life = life
        self.vy = vy

    def update(self):
        self.rect.y += self.vy
        self.vy *= 0.97
        self.life -= 1

    @property
    def alive(self):
        return self.life > 0

    def draw(self, surf):
        self.image.set_alpha(max(0, min(255, int(255 * self.life / self.max_life))))
        surf.blit(self.image, self.rect)


class Ring:
    def __init__(self, x, y, color, max_radius, life=26, width=5):
        self.x = x
        self.y = y
        size = (max_radius + width) * 2
        self.base = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self.base, color, (size // 2, size // 2), max_radius, width)
        self.life = life
        self.max_life = life

    def update(self):
        self.life -= 1

    @property
    def alive(self):
        return self.life > 0

    def draw(self, surf):
        t = 1 - self.life / self.max_life
        w = max(4, int(self.base.get_width() * (0.25 + 0.75 * t)))
        img = pygame.transform.smoothscale(self.base, (w, w))
        img.set_alpha(max(0, int(255 * (1 - t))))
        surf.blit(img, (self.x - w // 2, self.y - w // 2))


class Button:
    def __init__(self, rect, text, color=BLUE, hover_color=(100, 160, 210), text_color=WHITE):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.font = pygame.font.SysFont("simhei", 28)

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, BLACK, self.rect, 2, border_radius=8)
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def is_clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


class InputBox:
    def __init__(self, rect, text=""):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.active = False
        self.font = pygame.font.SysFont("simhei", 28)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                return "submit"
            else:
                char = event.unicode
                if char and len(self.text) < 12:
                    self.text += char
        return None

    def draw(self, screen):
        color = BLUE if self.active else GRAY
        pygame.draw.rect(screen, WHITE, self.rect)
        pygame.draw.rect(screen, color, self.rect, 3)
        text_surf = self.font.render(self.text, True, BLACK)
        screen.blit(text_surf, (self.rect.x + 10, self.rect.y + 10))


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("跳跃游戏")
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.SysFont("simhei", 64)
        self.font_medium = pygame.font.SysFont("simhei", 36)
        self.font_small = pygame.font.SysFont("simhei", 24)

        # 背景不透明，用 convert() 提速
        self.bg = pygame.image.load(ASSETS["background"]).convert()
        self.bg = pygame.transform.smoothscale(self.bg, (self.bg.get_width(), SCREEN_HEIGHT))
        self.bg_width = self.bg.get_width()
        self.player_img = load_image(ASSETS["player"], (80, 80))
        self.wall_img = load_image(ASSETS["wall"], (80, 80))
        self.hurt_img = load_image(ASSETS["hurt"], (70, 70))
        self.gold_img = load_image(ASSETS["gold"], (60, 60))
        # 圆形碰撞体半径（比外接矩形更宽容，操作手感更好）
        self.player_radius = min(self.player_img.get_size()) * 0.38

        # 世界画面先画到离屏 surface，便于整体做震屏且不留残影
        self.world = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.heart_shapes = [
            heart_points(34, SCREEN_WIDTH - 150 + i * 45, 40) for i in range(MAX_LIVES)
        ]

        self.state = "START"
        self.difficulty = "easy"
        self.player_name = ""
        self.saved = False
        self.show_hitbox = False
        self.reset_game()

        self.start_buttons = {
            key: Button((SCREEN_WIDTH // 2 - 220 + i * 160, 240, 120, 50), cfg["name"])
            for i, (key, cfg) in enumerate(DIFFICULTIES.items())
        }
        self.replay_button = Button((SCREEN_WIDTH // 2 - 130, 460, 120, 50), "再玩一次", GREEN)
        self.menu_button = Button((SCREEN_WIDTH // 2 + 20, 460, 120, 50), "主菜单", DARK_GRAY)
        self.save_button = Button((SCREEN_WIDTH // 2 - 60, 400, 120, 50), "保存分数", RED)
        self.name_input = InputBox((SCREEN_WIDTH // 2 - 150, 330, 300, 50))

    def reset_game(self):
        cfg = DIFFICULTIES[self.difficulty]
        self.world_speed = cfg["speed"]
        self.bg_offset = 0
        self.distance = 0
        self.coins = 0
        self.score = 0
        self.obstacles = []
        self.last_spawn_time = pygame.time.get_ticks()
        self.spawn_interval = random.randint(cfg["spawn_min"], cfg["spawn_max"])

        self.player_x = 80
        self.target_x = SCREEN_WIDTH // 2 - self.player_img.get_width() // 2
        self.player_y = GROUND_Y - self.player_img.get_height()
        self.player_vy = 0
        self.on_ground = True
        self.intro_done = False
        self.game_over = False
        self.player_name = ""
        self.saved = False

        self.lives = MAX_LIVES
        self.invincible = 0
        self.effects = []
        self.shake = 0
        self.hit_flash = 0

    def load_ranking(self):
        ranking = []
        if not os.path.exists(RANKING_FILE):
            return ranking
        try:
            with open(RANKING_FILE, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if len(row) >= 2:
                        try:
                            score = int(row[1])
                            ranking.append({"name": row[0].strip(), "score": score})
                        except ValueError:
                            continue
        except Exception:
            pass
        ranking.sort(key=lambda x: x["score"], reverse=True)
        return ranking

    def save_ranking(self, name, score):
        fieldnames = ["name", "score"]
        rows = []
        if os.path.exists(RANKING_FILE):
            with open(RANKING_FILE, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames:
                    rows = list(reader)
        rows.append({"name": name, "score": str(score)})
        with open(RANKING_FILE, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def spawn_object(self):
        cfg = DIFFICULTIES[self.difficulty]
        choices = ["wall"] * int(cfg["wall_prob"] * 100) + \
                  ["hurt"] * int(cfg["hurt_prob"] * 100) + \
                  ["gold"] * int(cfg["gold_prob"] * 100)
        obj_type = random.choice(choices) if choices else "wall"

        x = SCREEN_WIDTH + random.randint(20, 200)
        ground_top = GROUND_Y - self.wall_img.get_height()
        sky_top = GROUND_Y - self.player_img.get_height() - 160

        if obj_type == "wall":
            y = ground_top
            speed = self.world_speed
            img = self.wall_img
            radius = min(self.wall_img.get_size()) * 0.36
        elif obj_type == "hurt":
            y = random.choice([ground_top + 10, sky_top])
            speed = self.world_speed + cfg["hurt_extra"]
            img = self.hurt_img
            radius = min(self.hurt_img.get_size()) * 0.36
        else:  # gold
            y = random.choice([ground_top + 15, sky_top + 20])
            speed = self.world_speed + cfg["gold_extra"]
            img = self.gold_img
            # 金币拾取判定放宽一点，手感更好
            radius = min(self.gold_img.get_size()) * 0.5 + 6

        self.obstacles.append(GameObject(obj_type, img, x, y, speed, radius))

    def spawn_coin_effect(self, x, y):
        colors = [GOLD, (255, 240, 150), (255, 200, 60)]
        for _ in range(22):
            self.effects.append(Particle(
                x, y, random.choice(colors),
                speed=6, size=random.randint(3, 6), life=random.randint(30, 55)))
        self.effects.append(Ring(x, y, GOLD, 55, life=24, width=4))
        self.effects.append(FloatingText("+100", x, y - 30, GOLD, self.font_medium))

    def spawn_hit_effect(self, x, y):
        colors = [RED, (180, 30, 30), (255, 120, 60)]
        for _ in range(30):
            self.effects.append(Particle(
                x, y, random.choice(colors),
                speed=8, size=random.randint(4, 8), life=random.randint(30, 60)))
        self.effects.append(Ring(x, y, RED, 95, life=22, width=6))
        self.effects.append(FloatingText("-1", x, y - 40, RED, self.font_medium))
        self.shake = 16
        self.hit_flash = 14

    def update(self):
        if self.state != "PLAYING":
            # 游戏结束后让特效继续播完，避免粒子定格
            if self.state == "GAME_OVER":
                for effect in self.effects:
                    effect.update()
                self.effects = [effect for effect in self.effects if effect.alive]
                if self.shake > 0:
                    self.shake -= 1
                if self.hit_flash > 0:
                    self.hit_flash -= 1
            return

        cfg = DIFFICULTIES[self.difficulty]
        now = pygame.time.get_ticks()

        # Background scroll
        self.bg_offset = (self.bg_offset - self.world_speed) % self.bg_width
        self.distance += self.world_speed

        # Intro: player runs to center
        if not self.intro_done:
            run_speed = self.world_speed + 4
            self.player_x += run_speed
            if self.player_x >= self.target_x:
                self.player_x = self.target_x
                self.intro_done = True
                self.last_spawn_time = now
            return

        # Gravity
        self.player_vy += 0.8
        self.player_y += self.player_vy
        ground = GROUND_Y - self.player_img.get_height()
        if self.player_y >= ground:
            self.player_y = ground
            self.player_vy = 0
            self.on_ground = True

        # Spawn objects
        if now - self.last_spawn_time > self.spawn_interval:
            self.spawn_object()
            self.last_spawn_time = now
            self.spawn_interval = random.randint(cfg["spawn_min"], cfg["spawn_max"])

        # Update objects（圆形碰撞判定）
        player_center = self.player_img.get_rect(topleft=(self.player_x, self.player_y)).center
        remaining = []
        for obj in self.obstacles:
            obj.update()
            if circles_overlap(player_center, self.player_radius, obj.center, obj.radius):
                if obj.type == "gold":
                    self.coins += 1
                    self.spawn_coin_effect(*obj.center)
                    continue  # 金币被吃掉，直接移除
                if self.invincible <= 0:
                    self.lives -= 1
                    self.spawn_hit_effect(*obj.center)
                    self.invincible = INVINCIBLE_FRAMES
                    continue  # 障碍物被撞碎，避免连续扣血
            remaining.append(obj)
        self.obstacles = [obj for obj in remaining if not obj.off_screen()]

        self.score = int(self.distance) + self.coins * 100

        # 无敌帧、震屏、红闪与特效
        if self.invincible > 0:
            self.invincible -= 1
        if self.shake > 0:
            self.shake -= 1
        if self.hit_flash > 0:
            self.hit_flash -= 1
        for effect in self.effects:
            effect.update()
        self.effects = [effect for effect in self.effects if effect.alive]

        if self.lives <= 0:
            self.lives = 0
            self.game_over = True
            self.state = "GAME_OVER"
            self.name_input.text = ""
            self.saved = False

    def draw_background(self, surf=None):
        if surf is None:
            surf = self.screen
        # 每帧先整体清屏，避免上一帧残留造成残影
        surf.fill(WHITE)
        # 保持偏移在 (-bg_width, 0]，多张背景首尾相接完整覆盖屏幕
        x = self.bg_offset - self.bg_width
        while x < SCREEN_WIDTH:
            surf.blit(self.bg, (x, 0))
            x += self.bg_width

    def draw_player(self, surf=None):
        if surf is None:
            surf = self.screen
        # 受伤后无敌时间内闪烁
        if self.invincible > 0 and (self.invincible // 6) % 2 == 0:
            return
        surf.blit(self.player_img, (self.player_x, self.player_y))

    def draw_effects(self, surf):
        for effect in self.effects:
            effect.draw(surf)

    def draw_hitboxes(self, surf):
        center = self.player_img.get_rect(topleft=(self.player_x, self.player_y)).center
        pygame.draw.circle(surf, GREEN, center, int(self.player_radius), 2)
        for obj in self.obstacles:
            pygame.draw.circle(surf, BLUE, obj.center, int(obj.radius), 2)

    def draw_lives(self, surf):
        panel = pygame.Surface((240, 60), pygame.SRCALPHA)
        panel.fill((255, 255, 255, 150))
        surf.blit(panel, (SCREEN_WIDTH - 250, 10))

        label = self.font_small.render("生命", True, BLACK)
        surf.blit(label, (SCREEN_WIDTH - 238, 30))

        for i, points in enumerate(self.heart_shapes):
            if i < self.lives:
                pygame.draw.polygon(surf, RED, points)
                pygame.draw.polygon(surf, BLACK, points, 2)
            else:
                pygame.draw.polygon(surf, (210, 210, 210), points)
                pygame.draw.polygon(surf, (130, 130, 130), points, 2)

    def draw_ui(self, surf=None):
        if surf is None:
            surf = self.screen
        # 左上角半透明底板，保证文字在任意背景上都清晰
        panel = pygame.Surface((190, 100), pygame.SRCALPHA)
        panel.fill((255, 255, 255, 150))
        surf.blit(panel, (10, 10))

        score_text = self.font_medium.render(f"分数: {self.score}", True, BLACK)
        surf.blit(score_text, (20, 20))
        coin_text = self.font_small.render(f"金币: {self.coins}", True, (170, 120, 0))
        surf.blit(coin_text, (22, 66))

        self.draw_lives(surf)

        if self.show_hitbox:
            tip = self.font_small.render("圆形碰撞体显示中（F1 切换）", True, BLUE)
            surf.blit(tip, (20, 116))

    def draw_start_screen(self):
        self.draw_background()
        title = self.font_large.render("誓死效忠中国工商银行", True, BLACK)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 100)))

        hint = self.font_small.render("操作说明：空格键跳跃 ", True, BLACK)
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 150)))

        diff_label = self.font_medium.render("选择难度：", True, BLACK)
        self.screen.blit(diff_label, diff_label.get_rect(center=(SCREEN_WIDTH // 2, 210)))

        for btn in self.start_buttons.values():
            btn.draw(self.screen)

        ranking = self.load_ranking()
        panel = pygame.Rect(SCREEN_WIDTH // 2 - 220, 320, 440, 360)
        pygame.draw.rect(self.screen, LIGHT_GRAY, panel, border_radius=10)
        pygame.draw.rect(self.screen, BLACK, panel, 2, border_radius=10)

        rank_title = self.font_medium.render("排行榜", True, BLACK)
        self.screen.blit(rank_title, rank_title.get_rect(center=(SCREEN_WIDTH // 2, 350)))

        y = 390
        for i, record in enumerate(ranking[:10], start=1):
            line = f"{i:2d}. {record['name']:<12s} {record['score']:>8d}"
            text = self.font_small.render(line, True, BLACK)
            self.screen.blit(text, (SCREEN_WIDTH // 2 - 180, y))
            y += 28

        if not ranking:
            empty = self.font_small.render("暂无记录", True, DARK_GRAY)
            self.screen.blit(empty, empty.get_rect(center=(SCREEN_WIDTH // 2, 420)))

    def draw_game(self):
        # 世界内容统一画到离屏 surface，再整块贴到屏幕，便于震屏且不会残留
        world = self.world
        self.draw_background(world)
        for obj in self.obstacles:
            obj.draw(world)
        self.draw_effects(world)
        self.draw_player(world)
        if self.show_hitbox:
            self.draw_hitboxes(world)

        # 受击红闪
        if self.hit_flash > 0:
            flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            flash.fill(RED)
            flash.set_alpha(min(110, self.hit_flash * 9))
            world.blit(flash, (0, 0))

        dx = dy = 0
        if self.shake > 0:
            dx = random.randint(-self.shake, self.shake)
            dy = random.randint(-self.shake, self.shake)

        self.screen.fill(BLACK)
        self.screen.blit(world, (dx, dy))
        self.draw_ui()

    def draw_game_over(self):
        self.draw_game()
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 250, 180, 500, 360)
        pygame.draw.rect(self.screen, WHITE, panel, border_radius=12)
        pygame.draw.rect(self.screen, BLACK, panel, 3, border_radius=12)

        over_text = self.font_large.render("游戏结束", True, RED)
        self.screen.blit(over_text, over_text.get_rect(center=(SCREEN_WIDTH // 2, 220)))

        final = self.font_medium.render(f"最终分数: {self.score}", True, BLACK)
        self.screen.blit(final, final.get_rect(center=(SCREEN_WIDTH // 2, 270)))

        name_label = self.font_small.render("输入星辰姓名：", True, BLACK)
        self.screen.blit(name_label, name_label.get_rect(center=(SCREEN_WIDTH // 2, 305)))
        self.name_input.draw(self.screen)

        if not self.saved:
            self.save_button.draw(self.screen)
        else:
            saved_text = self.font_small.render("已保存", True, GREEN)
            self.screen.blit(saved_text, saved_text.get_rect(center=(SCREEN_WIDTH // 2, 425)))

        self.replay_button.draw(self.screen)
        self.menu_button.draw(self.screen)

    def handle_start_events(self, event):
        for key, btn in self.start_buttons.items():
            if btn.is_clicked(event):
                self.difficulty = key
                self.reset_game()
                self.state = "PLAYING"

    def handle_game_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if self.on_ground:
                    self.player_vy = -17
                    self.on_ground = False
            elif event.key == pygame.K_F1:
                self.show_hitbox = not self.show_hitbox

    def handle_game_over_events(self, event):
        result = self.name_input.handle_event(event)
        if self.save_button.is_clicked(event) or result == "submit":
            name = self.name_input.text.strip()
            if name and not self.saved:
                self.save_ranking(name, self.score)
                self.saved = True
        if self.replay_button.is_clicked(event):
            self.reset_game()
            self.state = "PLAYING"
        if self.menu_button.is_clicked(event):
            self.state = "START"

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif self.state == "START":
                    self.handle_start_events(event)
                elif self.state == "PLAYING":
                    self.handle_game_events(event)
                elif self.state == "GAME_OVER":
                    self.handle_game_over_events(event)

            self.update()

            if self.state == "START":
                self.draw_start_screen()
            elif self.state == "GAME_OVER":
                self.draw_game_over()
            else:
                self.draw_game()

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
