import random
import sys

import pygame

# =========================
# THE LEGEND OF SPUD
# A single-player RPG. Everything is drawn with shapes, so no image files needed.
#
# Controls: WASD / arrows = move, E or SPACE = talk / continue,
#           UP/DOWN + ENTER in battle, R = restart, ESC = quit
# =========================
pygame.init()
W, H = 800, 600
screen = pygame.display.set_mode((W, H))
screen_rect = screen.get_rect()
pygame.display.set_caption("The Legend of Spud")
clock = pygame.time.Clock()

font = pygame.font.SysFont("Arial", 22)
small = pygame.font.SysFont("Arial", 18)
big = pygame.font.SysFont("Arial", 48, bold=True)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

ENEMY_TYPES = {
    "Onion Ring": {"hp": 18, "atk": (2, 4), "xp": 12, "boss": False},
    "Chef Fryer": {"hp": 60, "atk": (4, 8), "xp": 60, "boss": True},
}
BATTLE_MENU = ["Attack", "Potion", "Run"]


# =========================
# Helpers
# =========================
def text(s, x, y, fnt=font, color=WHITE):
    screen.blit(fnt.render(s, True, color), (x, y))


def wrap(s, fnt, width):
    """Split a long sentence into lines that fit inside `width` pixels."""
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


# =========================
# Story / dialogue
# =========================
INTRO = [
    "Deep in the Spud Kingdom, the little village of Tuberton lay fast asleep...",
    "But you, Spud, wake up with a strange chill. Something is very wrong.",
    "Find Elder Mash (the old spud in the middle of the village) and talk to him. Press E near people to talk.",
]


def say(lines, after=None):
    """Start a dialogue. `after` is a function to run when the last line is done."""
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
             "Elder Mash: Chef Fryer is hiding in Deep Fry Castle, east of the Whispering Forest. The gate is locked, and the Rusty Key is in a chest somewhere in the forest.",
             "Elder Mash: Beware the Onion Rings on the way. Off you go, hero!"])
    elif not flags["key"]:
        say(["Elder Mash: Head east into the Whispering Forest. The Rusty Key is in a chest in the far corner."])
    else:
        say(["Elder Mash: You have the key! Deep Fry Castle is at the far east end of the forest. Be careful!"])


def hermit_talk():
    if not flags["hermit"]:
        flags["hermit"] = True
        stats["atk"] += 3
        stats["potions"] += 2
        say(["Old Sprout: Ah, a young spud! I've watched Chef Fryer for years.",
             "Old Sprout: He used to be the kindest cook in the kingdom. Then he tasted the Golden Butter's power and went mad with greed.",
             "Old Sprout: Take this Butter Knife. It's a bit blunt, but it's magical.",
             "You got the Butter Knife (Attack +3) and 2 potions!",
             "Old Sprout: Heal before you're in trouble. Fryer hits hard!"])
    else:
        say(["Old Sprout: The chest is in the south-east corner of the forest. Good luck, Spud!"])


def chest_open():
    if not flags["key"]:
        flags["key"] = True
        say(["You open the chest... and find the Rusty Key!",
             "Now you can unlock the gate of Deep Fry Castle, at the east edge of the forest."])
    else:
        say(["The chest is empty."])


# =========================
# World
# =========================
def build_scenes():
    R = pygame.Rect
    return {
        "village": {
            "name": "Tuberton Village", "bg": (95, 165, 85),
            "walls": [(R(100, 100, 140, 100), (150, 90, 60)),
                      (R(560, 100, 140, 100), (150, 90, 60)),
                      (R(330, 400, 140, 90), (70, 130, 200))],
            "ents": [{"kind": "npc", "name": "Elder Mash", "rect": R(385, 250, 30, 30),
                      "color": (215, 195, 140), "talk": elder_talk}],
            "exits": {"east": ("forest", (40, 300), None)},
        },
        "forest": {
            "name": "Whispering Forest", "bg": (30, 100, 50),
            "walls": [(R(x, y, 50, 50), (15, 70, 30)) for x, y in
                      [(60, 60), (200, 140), (300, 60), (520, 90), (650, 180), (120, 360),
                       (330, 300), (480, 400), (620, 340), (220, 470), (60, 500), (400, 520)]],
            "ents": [
                {"kind": "npc", "name": "Old Sprout", "rect": R(400, 140, 30, 30),
                 "color": (140, 190, 110), "talk": hermit_talk},
                {"kind": "chest", "name": "Chest", "rect": R(700, 500, 34, 28),
                 "color": (200, 150, 40), "talk": chest_open},
                {"kind": "enemy", "name": "Onion Ring", "rect": R(250, 250, 32, 32), "cool": 0},
                {"kind": "enemy", "name": "Onion Ring", "rect": R(450, 300, 32, 32), "cool": 0},
                {"kind": "enemy", "name": "Onion Ring", "rect": R(600, 250, 32, 32), "cool": 0},
            ],
            "exits": {"west": ("village", (W - 70, 300), None),
                      "east": ("castle", (40, 300), "key")},
        },
        "castle": {
            "name": "Deep Fry Castle", "bg": (60, 55, 70),
            "walls": [(R(x, y, 40, 40), (110, 100, 130)) for x, y in
                      [(200, 150), (200, 400), (560, 150), (560, 400)]],
            "ents": [{"kind": "enemy", "name": "Chef Fryer", "rect": R(500, 280, 44, 44), "cool": 0}],
            "exits": {"west": ("forest", (W - 70, 300), None)},
        },
    }


def obstacles():
    scene = scenes[current]
    solid = [w[0] for w in scene["walls"]]
    solid += [e["rect"] for e in scene["ents"] if e["kind"] in ("npc", "chest")]
    return solid


def move_player(dx, dy):
    global current
    # Move one axis at a time so you can slide along walls.
    player.x += dx
    if any(player.colliderect(o) for o in obstacles()):
        player.x -= dx
    player.y += dy
    if any(player.colliderect(o) for o in obstacles()):
        player.y -= dy

    # Leaving the screen edge = travelling to another area.
    exits = scenes[current]["exits"]
    side = "west" if player.left <= 0 else "east" if player.right >= W else None
    if side in exits:
        dest, pos, need = exits[side]
        if need and not flags[need]:
            player.x += 20 if side == "west" else -20
            say(["The castle gate is locked tight. You need a key."])
        else:
            current = dest
            player.topleft = pos
    player.clamp_ip(screen_rect)
    if player.top < 0 or player.bottom > H:
        player.clamp_ip(screen_rect)


def interact():
    for e in scenes[current]["ents"]:
        if e["kind"] in ("npc", "chest") and player.inflate(30, 30).colliderect(e["rect"]):
            e["talk"]()
            return


def near_interactable():
    return any(e["kind"] in ("npc", "chest") and player.inflate(30, 30).colliderect(e["rect"])
               for e in scenes[current]["ents"])


def objective():
    if flags["butter"]:
        return "Return to Elder Mash in Tuberton"
    if flags["key"]:
        return "Enter Deep Fry Castle and beat Chef Fryer"
    if flags["elder"]:
        return "Find the Rusty Key in the Whispering Forest"
    return "Talk to Elder Mash"


# =========================
# Battle
# =========================
def start_battle(ent):
    global state, battle
    t = ENEMY_TYPES[ent["name"]]
    battle = {"ent": ent, "name": ent["name"], "hp": t["hp"], "max": t["hp"], "t": t,
              "sel": 0, "msg": [f"{ent['name']} appears!"]}
    state = "battle"


def win_battle():
    global state, battle
    b, t = battle, battle["t"]
    scenes[current]["ents"].remove(b["ent"])
    stats["xp"] += t["xp"]
    lines = [f"You defeated {b['name']}! (+{t['xp']} XP)"]
    if not t["boss"] and random.random() < 0.3:
        stats["potions"] += 1
        lines.append("It dropped a potion!")
    while stats["xp"] >= stats["level"] * 20:
        stats["xp"] -= stats["level"] * 20
        stats["level"] += 1
        stats["max_hp"] += 6
        stats["atk"] += 1
        stats["hp"] = stats["max_hp"]
        lines.append(f"LEVEL UP! You are now level {stats['level']}! (HP restored)")
    battle = None
    if t["boss"]:
        flags["butter"] = True
        lines = ["Chef Fryer: Noooo! My beautiful reign of grease!",
                 "Chef Fryer: I only wanted to be the crispiest chef in the land...",
                 "You found the Golden Butter! Take it back to Elder Mash in Tuberton."] + lines
    say(lines)


def battle_action(choice):
    global state
    b, t = battle, battle["t"]
    b["msg"] = []
    if choice == 0:  # Attack
        dmg = max(1, stats["atk"] + random.randint(-2, 2))
        b["hp"] -= dmg
        b["msg"].append(f"You hit {b['name']} for {dmg}!")
        if b["hp"] <= 0:
            win_battle()
            return
    elif choice == 1:  # Potion
        if stats["potions"] <= 0:
            b["msg"].append("You have no potions!")
            return
        stats["potions"] -= 1
        heal = min(15, stats["max_hp"] - stats["hp"])
        stats["hp"] += heal
        b["msg"].append(f"You drink a potion and heal {heal} HP.")
    else:  # Run
        if t["boss"]:
            b["msg"].append("You can't run from the boss!")
            return
        if random.random() < 0.5:
            b["ent"]["cool"] = pygame.time.get_ticks() + 2500  # can't re-trigger right away
            state = "explore"
            return
        b["msg"].append("You couldn't get away!")

    # Enemy's turn
    dmg = random.randint(*t["atk"])
    stats["hp"] -= dmg
    b["msg"].append(f"{b['name']} hits you for {dmg}!")
    if stats["hp"] <= 0:
        state = "gameover"


# =========================
# Game setup / reset
# =========================
def reset():
    global scenes, current, player, stats, flags, state, dialogue, battle
    scenes = build_scenes()
    current = "village"
    player = pygame.Rect(60, 300, 30, 30)
    stats = {"hp": 30, "max_hp": 30, "atk": 5, "level": 1, "xp": 0, "potions": 2}
    flags = {"elder": False, "hermit": False, "key": False, "butter": False}
    dialogue = None
    battle = None
    state = "explore"
    say(INTRO)


# =========================
# Drawing
# =========================
def draw_enemy_shape(name, rect, scale=1.0):
    boss = ENEMY_TYPES[name]["boss"]
    if boss:
        r = pygame.Rect(0, 0, int(rect.w * scale), int(rect.h * scale))
        r.center = rect.center
        pygame.draw.rect(screen, (200, 40, 40), r)
        pygame.draw.rect(screen, WHITE, (r.x + r.w // 8, r.y - r.h // 3, r.w * 3 // 4, r.h // 3))
        pygame.draw.circle(screen, BLACK, (r.x + r.w // 3, r.y + r.h // 3), max(2, r.w // 10))
        pygame.draw.circle(screen, BLACK, (r.x + r.w * 2 // 3, r.y + r.h // 3), max(2, r.w // 10))
    else:
        radius = int(rect.w // 2 * scale)
        pygame.draw.circle(screen, (230, 190, 90), rect.center, radius)
        pygame.draw.circle(screen, (0, 0, 0), rect.center, radius // 2)
        pygame.draw.circle(screen, (230, 190, 90), rect.center, radius // 2, 2)


def draw_world():
    scene = scenes[current]
    screen.fill(scene["bg"])
    for rect, color in scene["walls"]:
        pygame.draw.rect(screen, color, rect)
    for e in scene["ents"]:
        r = e["rect"]
        if e["kind"] == "npc":
            pygame.draw.ellipse(screen, e["color"], r)
            pygame.draw.circle(screen, BLACK, (r.x + 10, r.y + 11), 3)
            pygame.draw.circle(screen, BLACK, (r.x + 20, r.y + 11), 3)
            label = small.render(e["name"], True, WHITE)
            screen.blit(label, (r.centerx - label.get_width() // 2, r.y - 22))
        elif e["kind"] == "chest":
            pygame.draw.rect(screen, e["color"], r)
            pygame.draw.rect(screen, (100, 60, 10), r, 3)
        else:
            draw_enemy_shape(e["name"], r)

    # Player (a potato with eyes)
    pygame.draw.ellipse(screen, (180, 130, 70), player)
    pygame.draw.circle(screen, BLACK, (player.x + 10, player.y + 11), 3)
    pygame.draw.circle(screen, BLACK, (player.x + 20, player.y + 11), 3)


def draw_hud():
    bar(10, 10, 160, 18, stats["hp"], stats["max_hp"], (200, 50, 50))
    text(f"HP {stats['hp']}/{stats['max_hp']}", 14, 8, small)
    text(f"Lv {stats['level']}  ATK {stats['atk']}  XP {stats['xp']}/{stats['level'] * 20}  Potions {stats['potions']}",
         10, 34, small)
    if flags["key"]:
        text("Key", 10, 58, small, (255, 220, 80))
    text(scenes[current]["name"], W - 10 - font.size(scenes[current]["name"])[0], 8)
    goal = "Goal: " + objective()
    text(goal, W - 10 - small.size(goal)[0], 36, small, (255, 240, 150))
    if state == "explore" and near_interactable():
        text("Press E", player.x - 5, player.y - 24, small, (255, 255, 120))


def draw_dialogue():
    box = pygame.Rect(20, 440, 760, 140)
    pygame.draw.rect(screen, (20, 20, 40), box)
    pygame.draw.rect(screen, WHITE, box, 3)
    line = dialogue["lines"][dialogue["i"]]
    for n, part in enumerate(wrap(line, font, 720)):
        text(part, 40, 455 + n * 28)
    text("Press SPACE / E", 620, 552, small, (180, 180, 200))


def draw_battle():
    screen.fill((35, 25, 45))
    b = battle
    big_rect = pygame.Rect(0, 0, 160, 160)
    big_rect.center = (W // 2, 170)
    draw_enemy_shape(b["name"], big_rect)
    text(b["name"], W // 2 - font.size(b["name"])[0] // 2, 20)
    bar(W // 2 - 100, 60, 200, 16, b["hp"], b["max"], (200, 50, 50))

    pygame.draw.rect(screen, (20, 20, 40), (20, 300, 760, 280))
    pygame.draw.rect(screen, WHITE, (20, 300, 760, 280), 3)
    for n, m in enumerate(b["msg"]):
        text(m, 40, 320 + n * 28)
    for n, option in enumerate(BATTLE_MENU):
        label = option + (f" (x{stats['potions']})" if option == "Potion" else "")
        color = (255, 240, 120) if n == b["sel"] else WHITE
        text(("> " if n == b["sel"] else "  ") + label, 40, 420 + n * 32, font, color)
    text(f"Your HP: {stats['hp']}/{stats['max_hp']}", 500, 420)
    bar(500, 452, 240, 18, stats["hp"], stats["max_hp"], (60, 180, 60))
    text("UP/DOWN to choose, ENTER to confirm", 40, 545, small, (180, 180, 200))


def draw_end_screen(title, lines, color):
    screen.fill((20, 20, 40))
    t = big.render(title, True, color)
    screen.blit(t, t.get_rect(center=(W // 2, 180)))
    for n, line in enumerate(lines):
        surf = font.render(line, True, WHITE)
        screen.blit(surf, surf.get_rect(center=(W // 2, 280 + n * 36)))


# =========================
# Main loop
# =========================
reset()
while True:
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type != pygame.KEYDOWN:
            continue
        if event.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()
        if state == "explore" and event.key in (pygame.K_e, pygame.K_SPACE):
            interact()
        elif state == "dialogue" and event.key in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN):
            advance()
        elif state == "battle":
            if event.key in (pygame.K_UP, pygame.K_w):
                battle["sel"] = (battle["sel"] - 1) % len(BATTLE_MENU)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                battle["sel"] = (battle["sel"] + 1) % len(BATTLE_MENU)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                battle_action(battle["sel"])
        elif state in ("gameover", "end") and event.key == pygame.K_r:
            reset()

    if state == "explore":
        keys = pygame.key.get_pressed()
        dx = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP])
        move_player(dx * 4, dy * 4)

        # Touching an enemy starts a battle.
        now = pygame.time.get_ticks()
        for e in scenes[current]["ents"]:
            if e["kind"] == "enemy" and e["cool"] < now and player.colliderect(e["rect"]):
                start_battle(e)
                break

    # --- Drawing ---
    if state == "battle":
        draw_battle()
    elif state == "gameover":
        draw_end_screen("YOU WERE SQUASHED", ["Chef Fryer wins... this time.", "",
                                              "Press R to try again, ESC to quit"], (220, 70, 70))
    elif state == "end":
        draw_end_screen("THE END", ["Spud saved the Spud Kingdom!", f"You finished at level {stats['level']}.", "",
                                    "Press R to play again, ESC to quit"], (255, 220, 80))
    else:
        draw_world()
        draw_hud()
        if state == "dialogue":
            draw_dialogue()

    pygame.display.flip()
