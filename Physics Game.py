import pygame
import sys
import random
import math

# Initialize Pygame
pygame.init()

# Screen dimensions
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Simple Physics with Collision and Shooting")

# Colors
white = (255, 255, 255)
red = (255, 0, 0)
blue = (0, 0, 255)
green = (0, 255, 0)
yellow = (255, 255, 0)

# Player properties
player_size = 50
player_x = screen_width // 4 - player_size // 2
player_y = screen_height - player_size - 20
player_speed = 5
player_velocity_y = 0
gravity = 1
jump_strength = -20
is_jumping = False

# Bullet properties
bullet_size = 10
bullet_speed = 10
bullets = []

def create_bullet(x, y, angle):
    dx = bullet_speed * math.cos(angle)
    dy = -bullet_speed * math.sin(angle)
    return {'rect': pygame.Rect(x + player_size // 2 - bullet_size // 2, y + player_size // 2 - bullet_size // 2, bullet_size, bullet_size), 'dx': dx, 'dy': dy}

def move_bullet(bullet):
    bullet['rect'].x += bullet['dx']
    bullet['rect'].y += bullet['dy']

# Target properties
target_size = 30
target_x = screen_width * 3 // 4 - target_size // 2
target_y = screen_height - target_size - 20
target_color = green

# Obstacle properties
obstacle_width = 60
obstacle_height = 40
obstacle_x = screen_width // 2 - obstacle_width // 2
obstacle_y = screen_height - obstacle_height - 50
obstacle_color = red

# Score
score = 0
top_score_announced = False
font = pygame.font.Font(None, 36)

# Objective: Collect the green target while avoiding the red obstacle.
objective_text = font.render("Objective: Collect the Green Target, Avoid the Red!", True, white)
objective_rect = objective_text.get_rect(topleft=(10, 10))

def draw_player():
    pygame.draw.rect(screen, blue, (player_x, player_y, player_size, player_size))

def draw_target():
    pygame.draw.rect(screen, target_color, (target_x, target_y, target_size, target_size))

def draw_obstacle():
    pygame.draw.rect(screen, obstacle_color, (obstacle_x, obstacle_y, obstacle_width, obstacle_height))

def draw_bullets():
    for bullet in bullets:
        pygame.draw.rect(screen, yellow, bullet['rect'])

def check_collision(rect1, rect2):
    return rect1.colliderect(rect2)

def display_score():
    score_text = font.render(f"Score: {score}", True, white)
    screen.blit(score_text, (10, 50))

running = True
clock = pygame.time.Clock()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and not is_jumping:
                is_jumping = True
                player_velocity_y = jump_strength
            if event.key == pygame.K_z:
                bullets.append(create_bullet(player_x, player_y, math.radians(135)))
            if event.key == pygame.K_x:
                bullets.append(create_bullet(player_x, player_y, math.radians(45)))
            if event.key == pygame.K_a:
                bullets.append(create_bullet(player_x, player_y, math.radians(225)))
            if event.key == pygame.K_s:
                bullets.append(create_bullet(player_x, player_y, math.radians(315)))

    # Player movement
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        player_x -= player_speed
    if keys[pygame.K_RIGHT]:
        player_x += player_speed

    # Player physics (gravity and jumping)
    player_velocity_y += gravity
    player_y += player_velocity_y

    # Ground collision
    if player_y >= screen_height - player_size:
        player_y = screen_height - player_size
        player_velocity_y = 0
        is_jumping = False

    # Keep player within screen bounds
    if player_x < 0:
        player_x = 0
    elif player_x > screen_width - player_size:
        player_x = screen_width - player_size

    # Update bullet positions and remove off-screen bullets
    bullets = [bullet for bullet in bullets if 0 < bullet['rect'].x < screen_width and 0 < bullet['rect'].y < screen_height]
    for bullet in bullets:
        move_bullet(bullet)

    # Create Pygame Rect objects for collision detection
    player_rect = pygame.Rect(player_x, player_y, player_size, player_size)
    target_rect = pygame.Rect(target_x, target_y, target_size, target_size)
    obstacle_rect = pygame.Rect(obstacle_x, obstacle_y, obstacle_width, obstacle_height)

    # Collision with target
    if check_collision(player_rect, target_rect):
        score += 1
        # Move target to a new random location
        target_x = random.randint(50, screen_width - 50 - target_size)
        target_y = screen_height - target_size - 20  # Keep it on the ground for simplicity
        target_rect.topleft = (target_x, target_y)

    # Collision with obstacle
    if check_collision(player_rect, obstacle_rect):
        print("Game Over! You hit the obstacle.")
        running = False

    # Collision with bullets
    for bullet in bullets[:]:
        if check_collision(bullet['rect'], target_rect):
            score += 1
            bullets.remove(bullet)
            target_x = random.randint(50, screen_width - 50 - target_size)
            target_y = screen_height - target_size - 20
            target_rect.topleft = (target_x, target_y)
        if check_collision(bullet['rect'], obstacle_rect):
            print("Game Over! Bullet hit the obstacle.")
            running = False
            break

    if score >= 100 and not top_score_announced:
        print("Congratulations! You've reached the top score!")
        top_score_announced = True
          
    # Drawing
    screen.fill((0, 0, 0))
    screen.blit(objective_text, objective_rect)
    draw_player()
    draw_target()
    draw_obstacle()
    draw_bullets()
    display_score()

    pygame.display.flip()

    clock.tick(60)

pygame.quit()
sys.exit()