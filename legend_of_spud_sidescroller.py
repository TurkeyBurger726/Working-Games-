import math
import random
import sys
from pathlib import Path

import pygame

# =========================
# THE LEGEND OF SPUD  -  side-scrolling (Terraria-style) edition
#
# A / D or arrows ... move          W / UP / SPACE ... jump
# J or F ............ swing the Butter Knife
# Left click ........ dig a block   Right click ..... place a dirt block
# E ................. talk / open chests / continue dialogue
# Q ................. drink a potion    R ... restart    ESC ... quit
#
# Needs an "images" folder next to this file containing:
#   Potato.png (you!), mashedpotatoes.jpg (Elder Mash), adventuretime.jpg (backdrop)
# If a picture is missing, the game falls back to simple drawn shapes.
# =========================
pygame.init()
W, H = 800, 600
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("The Legend of Spud")
clock = pygame.time.Clock()

font = pygame.font.SysFont("Arial", 22)
small = pygame.font.SysFont("Arial", 18)
big = pygame.font.SysFont("Arial", 48, bold=True)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

T = 32            # size of one block in pixels
ROWS = 30         # world height in blocks
GRAVITY = 0.6
MAX_FALL = 15
JUMP = -12
SPEED = 4
REACH = 160       # how far (pixels) you can dig / build from your body

# Block types: 0 air, 1 grass, 2 dirt, 3 stone, 5 brick, 9 bedrock (can't be dug)
TILE_COLOR = {1: (134, 96, 67), 2: (134, 96, 67), 3: (115, 115, 125),
              5: (105, 85, 120), 9: (35, 35, 45)}

ENEMY_TYPES = {
    "Onion Ring": {"hp": 18, "atk": (2, 4), "xp": 12, "speed": 2, "sight": 260,
                   "size": (32, 32), "boss": False},
    "Chef Fryer": {"hp": 60, "atk": (4, 8), "xp": 60, "speed": 2, "sight": 700,
                   "size": (44, 56), "boss": True},
}


# =========================
# Pictures
# =========================
ASSET_DIR = Path(__file__).parent / "images"


def load_sprite(filename, box):
    """Load a picture, turn its white background see-through, trim the empty
    edges and shrink it to fit inside `box` (width, height) without squashing."""
    try:
        img = pygame.image.load(ASSET_DIR / filename).convert_alpha()
    except (FileNotFoundError, pygame.error):
        return None
    w, h = img.get_size()
    for x in range(w):
        for y in range(h):
            r, g, b, a = img.get_at((x, y))
            if r > 225 and g > 225 and b > 225:
                img.set_at((x, y), (r, g, b, 0))
    img = img.subsurface(img.get_bounding_rect()).copy()
    iw, ih = img.get_size()
    scale = min(box[0] / iw, box[1] / ih)
    return pygame.transform.smoothscale(img, (max(1, int(iw * scale)), max(1, int(ih * scale))))


def load_backdrop(filename, size):
    try:
        img = pygame.image.load(ASSET_DIR / filename).convert()
    except (FileNotFoundError, pygame.error):
        return None
    return pygame.transform.smoothscale(img, size)


POTATO = load_sprite("Potato.png", (30, 26))              # the player
POTATO_LEFT = pygame.transform.flip(POTATO, True, False) if POTATO else None
MASH = load_sprite("mashedpotatoes.jpg", (40, 40))         # Elder Mash
TITLE_POTATO = load_sprite("Potato.png", (150, 130))
TITLE_MASH = load_sprite("mashedpotatoes.jpg", (160, 150))
BACKDROP = load_backdrop("adventuretime.jpg", (W + 200, H))   # scrolling scenery
TITLE_BG = load_backdrop("adventuretime.jpg", (W, H))
SHADE = pygame.Surface((W, H))                                 # darkens the forest a bit
SHADE.fill((0, 25, 10))


# =========================
# Helpers
# =========================
def text(s, x, y, fnt=font, color=WHITE):
    screen.blit(fnt.render(s, True, color), (x, y))


def wrap(s, fnt, width):
    lines, cur = [], ""
    for word in s.split(" "):
        test = (cur + " " + word).strip()
        if fnt.size(test)[0] <= width:
            cur = test
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


def bar(x, y, w, h, value, maximum, color):
    pygame.draw.rect(screen, (60, 60, 60), (x, y, w, h))
    pygame.draw.rect(screen, color, (x, y, int(w * max(value, 0) / maximum), h))
    pygame.draw.rect(screen, WHITE, (x, y, w, h), 2)


def show_toast(msg):
    global toast_text, toast_until
    toast_text = msg
    toast_until = pygame.time.get_ticks() + 2500


# =========================
# World / physics
# =========================
def solid_at(tx, ty):
    if tx < 0 or tx >= area["cols"]:
        return True          # invisible walls at the sides of the world
    if ty < 0:
        return False
    if ty >= ROWS:
        return True
    return area["grid"][ty][tx] != 0


def tile_hits(rect):
    """Every solid block that overlaps `rect`."""
    for ty in range(rect.top // T, (rect.bottom - 1) // T + 1):
        for tx in range(rect.left // T, (rect.right - 1) // T + 1):
            if solid_at(tx, ty):
                yield pygame.Rect(tx * T, ty * T, T, T)


def first_solid_row(tx):
    for ty in range(ROWS):
        if area["grid"][ty][tx] != 0:
            return ty
    return ROWS - 1


class Body:
    """Anything that falls with gravity and bumps into blocks (player, enemies)."""

    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
        self.vx = 0
        self.vy = 0.0
        self.on_ground = False
        self.hit_x = False
        self.facing = 1
        self.kb_until = 0        # while knocked back, ignore steering
        self.invuln_until = 0
        self.attack_until = 0
        self.next_attack = 0

    def move(self, dx, dy):
        hit = False
        self.rect.x += dx
        for t in list(tile_hits(self.rect)):
            hit = True
            if dx > 0:
                self.rect.right = t.left
            elif dx < 0:
                self.rect.left = t.right
        self.rect.y += dy
        for t in list(tile_hits(self.rect)):
            hit = True
            if dy > 0:
                self.rect.bottom = t.top
                self.vy = 0
            elif dy < 0:
                self.rect.top = t.bottom
                self.vy = 0
        return hit

    def physics(self):
        if self.on_ground and self.vy > 0:
            self.vy = 0
        self.vy = min(self.vy + GRAVITY, MAX_FALL)
        self.hit_x = self.move(int(self.vx), 0)
        self.move(0, int(self.vy))
        self.on_ground = any(True for _ in tile_hits(self.rect.move(0, 1)))


class Enemy(Body):
    def __init__(self, name, x, y):
        t = ENEMY_TYPES[name]
        super().__init__(x, y, *t["size"])
        self.name = name
        self.hp = t["hp"]
        self.dir = random.choice((-1, 1))
        self.next_jump = 0

    def update(self, now):
        t = ENEMY_TYPES[self.name]
        near = False
        if now >= self.kb_until:
            dist = player.rect.centerx - self.rect.centerx
            near = abs(dist) < t["sight"] and abs(player.rect.centery - self.rect.centery) < 250
            if near:
                self.dir = 1 if dist > 0 else -1
                speed = t["speed"] + (1 if t["boss"] and self.hp < t["hp"] // 2 else 0)
            else:
                speed = 1
            self.vx = self.dir * speed
            # The boss jumps around; everyone hops over walls when chasing.
            if t["boss"] and near and self.on_ground and now > self.next_jump:
                self.vy = -13
                self.next_jump = now + 1500
        self.physics()
        if self.hit_x and now >= self.kb_until:
            if near and self.on_ground:
                self.vy = -10
            else:
                self.dir = -self.dir


# =========================
# Story / dialogue
# =========================
INTRO = [
    "Deep in the Spud Kingdom, the little village of Tuberton lay fast asleep...",
    "But you, Spud, wake up with a strange chill. Something is very wrong.",
    "Find Elder Mash (the old spud in the middle of the village) and press E to talk to him.",
]


def say(lines, after=None):
    global state, dialogue
    state = "dialogue"
    dialogue = {"lines": lines, "i": 0, "after": after}


def advance():
    global state, dialogue
    dialogue["i"] += 1
    if dialogue["i"] >= len(dialogue["lines"]):
        after = dialogue["after"]
        dialogue = None
        state = "explore"
        if after:
            after()


def finish_game():
    global state
    state = "end"


def elder_talk():
    if flags["butter"]:
        say(["Elder Mash: You... you found it! The Golden Butter!",
             "The butter melts into the Great Spud Well, and warm golden light floods Tuberton once more.",
             "Elder Mash: You are no ordinary potato, Spud. You are the Legend of Spud!"],
            after=finish_game)
    elif not flags["elder"]:
        flags["elder"] = True
        say(["Elder Mash: Spud! Thank goodness you're awake. Tuberton is in terrible danger.",
             "Elder Mash: Last night the wicked Chef Fryer stole the Golden Butter that keeps our kingdom warm and golden.",
             "Elder Mash: Without it, we'll all turn cold and soggy by the end of the week!",
             "Elder Mash: He's hiding in Deep Fry Castle, at the far east end of the Whispering Forest. But the gate is locked.",
             "Elder Mash: The Rusty Key is buried somewhere deep in the forest. Old Sprout the hermit knows where. Watch out for Onion Rings!"])
    elif not flags["key"]:
        say(["Elder Mash: Head east into the Whispering Forest and find Old Sprout. He'll help you find the key."])
    else:
        say(["Elder Mash: You have the key! Deep Fry Castle is at the far east end of the forest. Be careful!"])


def hermit_talk():
    if not flags["hermit"]:
        flags["hermit"] = True
        stats["atk"] += 3
        stats["potions"] += 2
        say(["Old Sprout: Ah, a young spud! I've watched Chef Fryer for years.",
             "Old Sprout: He used to be the kindest cook in the kingdom. Then he tasted the Golden Butter's power and went mad with greed.",
             "Old Sprout: Take this Butter Knife. It's a bit blunt, but it's magical. Press J to swing it.",
             "You got the Butter Knife (Attack +3) and 2 potions! Press Q to drink one.",
             "Old Sprout: The Rusty Key is buried in a hidden cave at the far east of the forest. Look for the red X, then dig straight down with the left mouse button!",
             "Old Sprout: Right-click places dirt, so build yourself a staircase to climb back out."])
    else:
        say(["Old Sprout: Dig down beneath the red X at the far east of the forest. Left-click digs, right-click builds!"])


def chest_open():
    if not flags["key"]:
        flags["key"] = True
        say(["You open the old chest... and find the Rusty Key!",
             "Now climb out and unlock the gate of Deep Fry Castle at the east edge of the forest."])
    else:
        say(["The chest is empty."])


# =========================
# Building the areas
# =========================
def make_area(name, sky, cols, base, amp, freq, kind):
    surf = []
    for x in range(cols):
        # Hills fade out towards both ends of the world so the edges are flat.
        ramp = min(1.0, x / 12, (cols - 1 - x) / 12)
        surf.append(base + int(round(amp * ramp * math.sin(x * freq))))
    grid = [[0] * cols for _ in range(ROWS)]
    for x in range(cols):
        for y in range(surf[x], ROWS):
            if y == ROWS - 1:
                grid[y][x] = 9
            elif kind == "castle":
                grid[y][x] = 5 if y < surf[x] + 4 else 3
            elif y == surf[x]:
                grid[y][x] = 1
            elif y <= surf[x] + 5:
                grid[y][x] = 2
            else:
                grid[y][x] = 3
    return {"name": name, "sky": sky, "cols": cols, "surf": surf, "grid": grid,
            "things": [], "enemies": [], "decor": [], "exits": {},
            "backdrop": False, "shade": 0}


def stand_y(a, col, h):
    return a["surf"][col] * T - h


def build_scenes():
    # ---- Village ----
    village = make_area("Tuberton Village", (135, 200, 240), 60, 16, 1, 0.15, "grass")
    village["decor"] = [("house", 10), ("house", 42), ("well", 34)]
    village["things"].append({"kind": "npc", "name": "Elder Mash", "color": (215, 195, 140),
                              "rect": pygame.Rect(26 * T, stand_y(village, 26, 38), 40, 38),
                              "talk": elder_talk})
    village["exits"] = {"east": ("forest", None)}
    village["backdrop"] = True

    # ---- Forest ----
    forest = make_area("Whispering Forest", (90, 150, 190), 100, 16, 3, 0.09, "grass")
    rng = random.Random(3)
    chest_col = 90
    for c in range(10, 88, 4):
        col = c + rng.randint(0, 2)
        if rng.random() < 0.65 and abs(col - 14) > 2:
            forest["decor"].append(("tree", col))
    forest["decor"].append(("marker", chest_col))
    forest["things"].append({"kind": "npc", "name": "Old Sprout", "color": (140, 190, 110),
                             "rect": pygame.Rect(14 * T, stand_y(forest, 14, 40), 28, 40),
                             "talk": hermit_talk})
    # A hidden cave below the red X, with the chest inside.
    s = forest["surf"][chest_col]
    for row in (s + 8, s + 9):
        for col in range(chest_col - 2, chest_col + 3):
            forest["grid"][row][col] = 0
    forest["things"].append({"kind": "chest", "name": "Chest", "color": (200, 150, 40),
                             "rect": pygame.Rect(chest_col * T, (s + 10) * T - 28, 34, 28),
                             "talk": chest_open})
    for col in (25, 42, 58, 74):
        forest["enemies"].append(Enemy("Onion Ring", col * T, stand_y(forest, col, 32)))
    forest["exits"] = {"west": ("village", None), "east": ("castle", "key")}
    forest["backdrop"] = True
    forest["shade"] = 100

    # ---- Castle ----
    castle = make_area("Deep Fry Castle", (55, 45, 70), 45, 16, 0, 0, "castle")
    for row, c0, c1 in ((13, 8, 12), (10, 15, 19), (13, 22, 26)):
        for col in range(c0, c1 + 1):
            castle["grid"][row][col] = 5
    for col in (18, 25):
        castle["enemies"].append(Enemy("Onion Ring", col * T, stand_y(castle, col, 32)))
    castle["enemies"].append(Enemy("Chef Fryer", 34 * T, stand_y(castle, 34, 56)))
    castle["exits"] = {"west": ("forest", None)}

    return {"village": village, "forest": forest, "castle": castle}


def load_scene(name, from_side):
    """Switch area. from_side = which edge of the NEW area you arrive at."""
    global area, current
    current = name
    area = scenes[name]
    col = 3 if from_side == "west" else area["cols"] - 4
    player.rect.topleft = (col * T + 4, first_solid_row(col) * T - player.rect.h)
    player.vx, player.vy = 0, 0.0


def check_exits():
    ex = area["exits"]
    if player.rect.left <= 2:
        side = "west"
    elif player.rect.right >= area["cols"] * T - 2:
        side = "east"
    else:
        return
    if side not in ex:
        return
    dest, need = ex[side]
    if need and not flags[need]:
        player.rect.x += 40 if side == "west" else -40
        say(["The castle gate is locked tight. You need the Rusty Key."])
    else:
        load_scene(dest, "east" if side == "west" else "west")


# =========================
# Combat / actions
# =========================
def attack_box():
    r = player.rect
    if player.facing > 0:
        return pygame.Rect(r.right, r.y + 6, 46, 28)
    return pygame.Rect(r.left - 46, r.y + 6, 46, 28)


def attack(now):
    if now < player.next_attack:
        return
    player.next_attack = now + 400
    player.attack_until = now + 150
    box = attack_box()
    for e in area["enemies"][:]:
        if box.colliderect(e.rect):
            e.hp -= max(1, stats["atk"] + random.randint(-1, 2))
            e.kb_until = now + 200
            e.vx = 6 * player.facing
            e.vy = -5
            if e.hp <= 0:
                kill(e)


def kill(e):
    t = ENEMY_TYPES[e.name]
    area["enemies"].remove(e)
    stats["xp"] += t["xp"]
    msgs = [f"{e.name} defeated! +{t['xp']} XP"]
    if not t["boss"] and random.random() < 0.3:
        stats["potions"] += 1
        msgs.append("+1 potion")
    while stats["xp"] >= stats["level"] * 20:
        stats["xp"] -= stats["level"] * 20
        stats["level"] += 1
        stats["max_hp"] += 6
        stats["atk"] += 1
        stats["hp"] = stats["max_hp"]
        msgs.append(f"LEVEL UP! Lv {stats['level']}")
    show_toast("   ".join(msgs))
    if t["boss"]:
        flags["butter"] = True
        say(["Chef Fryer: Noooo! My beautiful reign of grease!",
             "Chef Fryer: I only wanted to be the crispiest chef in the land...",
             "You found the Golden Butter! Take it back to Elder Mash in Tuberton."])


def hurt_player(dmg, source_x, now):
    global state
    if now < player.invuln_until:
        return
    stats["hp"] -= dmg
    player.invuln_until = now + 900
    player.kb_until = now + 250
    player.vx = 6 if player.rect.centerx > source_x else -6
    player.vy = -6
    if stats["hp"] <= 0:
        state = "gameover"


def drink_potion():
    if stats["potions"] <= 0:
        show_toast("No potions left!")
    elif stats["hp"] >= stats["max_hp"]:
        show_toast("You're already at full health.")
    else:
        stats["potions"] -= 1
        heal = min(15, stats["max_hp"] - stats["hp"])
        stats["hp"] += heal
        show_toast(f"+{heal} HP")


def interact():
    zone = player.rect.inflate(40, 20)
    for th in area["things"]:
        if zone.colliderect(th["rect"]):
            th["talk"]()
            return


def near_interactable():
    zone = player.rect.inflate(40, 20)
    return any(zone.colliderect(th["rect"]) for th in area["things"])


def objective():
    if flags["butter"]:
        return "Return to Elder Mash in Tuberton"
    if flags["key"]:
        return "Unlock Deep Fry Castle and beat Chef Fryer"
    if flags["hermit"]:
        return "Dig up the Rusty Key (red X, far east)"
    if flags["elder"]:
        return "Find Old Sprout in the forest"
    return "Talk to Elder Mash"


def update_camera():
    global cam_x, cam_y
    cam_x = max(0, min(player.rect.centerx - W // 2, area["cols"] * T - W))
    cam_y = max(0, min(player.rect.centery - H // 2, ROWS * T - H))


def mining(now):
    """Left click = dig, right click = place dirt."""
    global next_mine
    if now < next_mine:
        return
    buttons = pygame.mouse.get_pressed()
    if not (buttons[0] or buttons[2]):
        return
    mx, my = pygame.mouse.get_pos()
    tx, ty = (mx + cam_x) // T, (my + cam_y) // T
    if not (0 <= tx < area["cols"] and 0 <= ty < ROWS):
        return
    cx, cy = tx * T + T // 2, ty * T + T // 2
    if math.hypot(cx - player.rect.centerx, cy - player.rect.centery) > REACH:
        return
    tile = area["grid"][ty][tx]
    if buttons[0] and tile not in (0, 9):
        area["grid"][ty][tx] = 0
        if tile in (1, 2):
            stats["dirt"] += 1
        next_mine = now + 120
    elif buttons[2] and tile == 0 and stats["dirt"] > 0:
        block = pygame.Rect(tx * T, ty * T, T, T)
        blocked = block.colliderect(player.rect)
        blocked = blocked or any(block.colliderect(e.rect) for e in area["enemies"])
        blocked = blocked or any(block.colliderect(th["rect"]) for th in area["things"])
        if not blocked:
            area["grid"][ty][tx] = 2
            stats["dirt"] -= 1
            next_mine = now + 120


def update_game(now):
    keys = pygame.key.get_pressed()
    left = int(keys[pygame.K_a] or keys[pygame.K_LEFT])
    right = int(keys[pygame.K_d] or keys[pygame.K_RIGHT])
    jump = keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_SPACE]

    if now >= player.kb_until:
        player.vx = (right - left) * SPEED
        if right != left:
            player.facing = 1 if right else -1
        if jump and player.on_ground:
            player.vy = JUMP
    player.physics()
    check_exits()

    for e in area["enemies"]:
        e.update(now)
    for e in area["enemies"]:
        if e.rect.colliderect(player.rect):
            hurt_player(random.randint(*ENEMY_TYPES[e.name]["atk"]), e.rect.centerx, now)

    update_camera()
    mining(now)


# =========================
# Drawing
# =========================
def draw_decor():
    for kind, tx in area["decor"]:
        x = tx * T - cam_x
        base = area["surf"][tx] * T - cam_y
        if kind == "house":
            pygame.draw.rect(screen, (170, 110, 70), (x, base - 96, 128, 96))
            pygame.draw.polygon(screen, (150, 50, 50), [(x - 10, base - 96), (x + 138, base - 96), (x + 64, base - 140)])
            pygame.draw.rect(screen, (80, 50, 30), (x + 52, base - 56, 24, 56))
            pygame.draw.rect(screen, (200, 230, 255), (x + 14, base - 70, 22, 22))
        elif kind == "well":
            pygame.draw.rect(screen, (120, 120, 130), (x, base - 40, 50, 40))
            pygame.draw.rect(screen, (60, 100, 200), (x + 6, base - 44, 38, 10))
        elif kind == "tree":
            pygame.draw.rect(screen, (100, 65, 35), (x + 10, base - 100, 12, 100))
            pygame.draw.circle(screen, (25, 110, 45), (x + 16, base - 105), 42)
            pygame.draw.circle(screen, (40, 140, 60), (x + 4, base - 120), 26)
        elif kind == "marker":
            pygame.draw.rect(screen, (100, 65, 35), (x + 14, base - 36, 6, 36))
            pygame.draw.line(screen, (230, 40, 40), (x + 2, base - 62), (x + 32, base - 32), 6)
            pygame.draw.line(screen, (230, 40, 40), (x + 32, base - 62), (x + 2, base - 32), 6)


def draw_tiles():
    surf = area["surf"]
    for ty in range(max(0, cam_y // T), min(ROWS, (cam_y + H) // T + 2)):
        for tx in range(max(0, cam_x // T), min(area["cols"], (cam_x + W) // T + 2)):
            tile = area["grid"][ty][tx]
            r = pygame.Rect(tx * T - cam_x, ty * T - cam_y, T, T)
            if tile == 0:
                if ty > surf[tx]:
                    pygame.draw.rect(screen, (55, 42, 38), r)   # cave background
                continue
            color = TILE_COLOR[tile]
            pygame.draw.rect(screen, color, r)
            if tile == 1:
                pygame.draw.rect(screen, (60, 170, 70), (r.x, r.y, T, 8))
            pygame.draw.rect(screen, tuple(int(c * 0.75) for c in color), r, 1)


def draw_body_face(r, facing):
    ex = r.centerx + facing * 4
    pygame.draw.circle(screen, WHITE, (ex - 4, r.y + 12), 5)
    pygame.draw.circle(screen, WHITE, (ex + 6, r.y + 12), 5)
    pygame.draw.circle(screen, BLACK, (ex - 4 + facing * 2, r.y + 12), 2)
    pygame.draw.circle(screen, BLACK, (ex + 6 + facing * 2, r.y + 12), 2)


def draw_world(now):
    screen.fill(area["sky"])
    if BACKDROP and area["backdrop"]:
        # Scenery slides slowly as you walk and stays put on the horizon when you jump.
        span = max(1, area["cols"] * T - W)
        screen.blit(BACKDROP, (-int(cam_x / span * 200), 20 * T - cam_y - H))
        if area["shade"]:
            SHADE.set_alpha(area["shade"])
            screen.blit(SHADE, (0, 0))
    draw_decor()
    draw_tiles()

    for th in area["things"]:
        r = th["rect"].move(-cam_x, -cam_y)
        if th["kind"] == "npc":
            if th["name"] == "Elder Mash" and MASH:
                screen.blit(MASH, MASH.get_rect(midbottom=r.midbottom))
            else:
                pygame.draw.ellipse(screen, th["color"], r)
                draw_body_face(r, 1)
            label = small.render(th["name"], True, WHITE)
            screen.blit(label, (r.centerx - label.get_width() // 2, r.y - 22))
        else:
            pygame.draw.rect(screen, th["color"], r)
            pygame.draw.rect(screen, (100, 60, 10), r, 3)

    for e in area["enemies"]:
        r = e.rect.move(-cam_x, -cam_y)
        t = ENEMY_TYPES[e.name]
        if t["boss"]:
            pygame.draw.rect(screen, (200, 40, 40), r)
            pygame.draw.rect(screen, WHITE, (r.x + 5, r.y - 16, r.w - 10, 18))
            draw_body_face(r, e.dir)
        else:
            pygame.draw.circle(screen, (230, 190, 90), r.center, r.w // 2)
            pygame.draw.circle(screen, (60, 45, 20), r.center, r.w // 4)
        bar(r.centerx - 20, r.y - 10 if not t["boss"] else r.y - 26, 40, 5, e.hp, t["hp"], (220, 60, 60))

    # Player (blinks while invulnerable)
    if not (now < player.invuln_until and (now // 100) % 2 == 0):
        r = player.rect.move(-cam_x, -cam_y)
        if POTATO:
            img = POTATO if player.facing > 0 else POTATO_LEFT
            screen.blit(img, img.get_rect(midbottom=r.midbottom))
        else:
            pygame.draw.ellipse(screen, (180, 130, 70), r)
            draw_body_face(r, player.facing)
    if now < player.attack_until:
        box = attack_box().move(-cam_x, -cam_y)
        pygame.draw.rect(screen, (225, 225, 235), (box.x, box.centery - 4, box.w, 8))
        pygame.draw.rect(screen, (200, 160, 40), (box.x if player.facing > 0 else box.right - 10, box.centery - 6, 10, 12))

    # Highlight the block under the mouse if it's in reach.
    mx, my = pygame.mouse.get_pos()
    tx, ty = (mx + cam_x) // T, (my + cam_y) // T
    if math.hypot(tx * T + T // 2 - player.rect.centerx, ty * T + T // 2 - player.rect.centery) <= REACH:
        pygame.draw.rect(screen, (255, 255, 255), (tx * T - cam_x, ty * T - cam_y, T, T), 2)


def draw_hud(now):
    bar(10, 10, 160, 18, stats["hp"], stats["max_hp"], (200, 50, 50))
    text(f"HP {stats['hp']}/{stats['max_hp']}", 14, 8, small)
    text(f"Lv {stats['level']}  ATK {stats['atk']}  XP {stats['xp']}/{stats['level'] * 20}", 10, 34, small)
    text(f"Potions {stats['potions']}   Dirt {stats['dirt']}" + ("   Rusty Key" if flags["key"] else ""), 10, 56, small)
    name = area["name"]
    text(name, W - 10 - font.size(name)[0], 8)
    goal = "Goal: " + objective()
    text(goal, W - 10 - small.size(goal)[0], 36, small, (255, 240, 150))
    text("A/D move  W jump  J attack  Click dig  Right-click build  Q potion  E talk",
         10, H - 24, small, (255, 255, 255))
    if state == "explore" and near_interactable():
        text("Press E", player.rect.x - cam_x - 12, player.rect.y - cam_y - 28, small, (255, 255, 120))
    if now < toast_until:
        surf = font.render(toast_text, True, (255, 255, 120))
        screen.blit(surf, surf.get_rect(center=(W // 2, 90)))


def draw_dialogue():
    box = pygame.Rect(20, 430, 760, 140)
    pygame.draw.rect(screen, (20, 20, 40), box)
    pygame.draw.rect(screen, WHITE, box, 3)
    line = dialogue["lines"][dialogue["i"]]
    for n, part in enumerate(wrap(line, font, 720)):
        text(part, 40, 445 + n * 28)
    text("Press E / SPACE", 630, 542, small, (180, 180, 200))


def draw_title():
    if TITLE_BG:
        screen.blit(TITLE_BG, (0, 0))
    else:
        screen.fill((20, 20, 40))
    band = pygame.Surface((W, 130))
    band.set_alpha(180)
    band.fill((10, 10, 25))
    screen.blit(band, (0, H - 130))
    if TITLE_POTATO:
        screen.blit(TITLE_POTATO, TITLE_POTATO.get_rect(bottomleft=(30, H - 120)))
    if TITLE_MASH:
        screen.blit(TITLE_MASH, TITLE_MASH.get_rect(bottomright=(W - 30, H - 120)))
    t = big.render("THE LEGEND OF SPUD", True, (255, 220, 80))
    screen.blit(t, t.get_rect(center=(W // 2, H - 85)))
    p = font.render("Press ENTER to start", True, WHITE)
    screen.blit(p, p.get_rect(center=(W // 2, H - 35)))


def draw_end_screen(title, lines, color):
    screen.fill((20, 20, 40))
    t = big.render(title, True, color)
    screen.blit(t, t.get_rect(center=(W // 2, 180)))
    for n, line in enumerate(lines):
        surf = font.render(line, True, WHITE)
        screen.blit(surf, surf.get_rect(center=(W // 2, 280 + n * 36)))


# =========================
# Game setup / reset
# =========================
def reset(title=False):
    global scenes, area, current, player, stats, flags, state, dialogue
    global toast_text, toast_until, next_mine, cam_x, cam_y
    scenes = build_scenes()
    area = scenes["village"]
    current = "village"
    player = Body(0, 0, 30, 26)
    stats = {"hp": 30, "max_hp": 30, "atk": 5, "level": 1, "xp": 0, "potions": 2, "dirt": 10}
    flags = {"elder": False, "hermit": False, "key": False, "butter": False}
    dialogue = None
    toast_text, toast_until = "", 0
    next_mine = 0
    cam_x = cam_y = 0
    load_scene("village", "west")
    update_camera()
    if title:
        state = "title"
    else:
        say(INTRO)


# =========================
# Main loop
# =========================
reset(title=True)
while True:
    clock.tick(60)
    now = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type != pygame.KEYDOWN:
            continue
        if event.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()
        if state == "explore":
            if event.key == pygame.K_e:
                interact()
            elif event.key in (pygame.K_j, pygame.K_f):
                attack(now)
            elif event.key == pygame.K_q:
                drink_potion()
        elif state == "title":
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                say(INTRO)
        elif state == "dialogue":
            if event.key in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN):
                advance()
        elif state in ("gameover", "end") and event.key == pygame.K_r:
            reset()

    if state == "explore":
        update_game(now)

    if state == "title":
        draw_title()
    elif state == "gameover":
        draw_end_screen("YOU WERE SQUASHED", ["Chef Fryer wins... this time.", "",
                                              "Press R to try again, ESC to quit"], (220, 70, 70))
    elif state == "end":
        draw_end_screen("THE END", ["Spud saved the Spud Kingdom!", f"You finished at level {stats['level']}.", "",
                                    "Press R to play again, ESC to quit"], (255, 220, 80))
    else:
        draw_world(now)
        draw_hud(now)
        if state == "dialogue":
            draw_dialogue()

    pygame.display.flip()
