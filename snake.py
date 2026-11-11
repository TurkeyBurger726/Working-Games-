
import pygame
import random

pygame.init()

# Screen settings
WIDTH = 600
HEIGHT = 400
CELL_SIZE = 20

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Snake Game")

clock = pygame.time.Clock()

# Colours
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
WHITE = (255, 255, 255)
GREY = (40, 40, 40)

# Fonts
title_font = pygame.font.SysFont("Arial", 55, bold=True)
ui_font = pygame.font.SysFont("Arial", 28)
small_font = pygame.font.SysFont("Arial", 20)

# Snake settings
snake = [(300, 200)]
direction = (CELL_SIZE, 0)

# Food settings
food = (
    random.randrange(0, WIDTH, CELL_SIZE),
    random.randrange(0, HEIGHT, CELL_SIZE)
)

# Game settings
score = 0
running = True
game_started = False
game_over = False


# UI FUNCTIONS

def draw_text(text, font, colour, y):

    text_surface = font.render(text, True, colour)

    text_rect = text_surface.get_rect(
        center=(WIDTH // 2, y)
    )

    screen.blit(text_surface, text_rect)


def draw_start_screen():

    screen.fill(BLACK)

    draw_text("SNAKE GAME", title_font, GREEN, 100)

    draw_text("Press SPACE to start", ui_font, WHITE, 200)

    draw_text("Use arrow keys to move", small_font, WHITE, 250)

    pygame.display.flip()


def draw_game_over():

    screen.fill(BLACK)

    draw_text("GAME OVER", title_font, RED, 100)

    draw_text(f"Final Score: {score}", ui_font, WHITE, 190)

    draw_text("Press SPACE to restart", small_font, WHITE, 250)

    pygame.display.flip()


def draw_ui():

    # Score panel
    pygame.draw.rect(
        screen,
        GREY,
        (0, 0, WIDTH, 45)
    )

    # Score
    score_text = ui_font.render(
        f"Score: {score}",
        True,
        WHITE
    )

    screen.blit(score_text, (10, 7))

    # Title
    title_text = small_font.render(
        "SNAKE",
        True,
        GREEN
    )

    screen.blit(title_text, (WIDTH - 85, 12))


def reset_game():

    global snake, direction, score, food, game_over

    snake = [(300, 200)]
    direction = (CELL_SIZE, 0)
    score = 0
    game_over = False

    food = (
        random.randrange(0, WIDTH, CELL_SIZE),
        random.randrange(0, HEIGHT, CELL_SIZE)
    )


# MAIN GAME LOOP

while running:

    # Handle events
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_SPACE:

                if not game_started:
                    game_started = True

                elif game_over:
                    reset_game()

            if game_started and not game_over:

                if event.key == pygame.K_UP and direction != (0, CELL_SIZE):
                    direction = (0, -CELL_SIZE)

                elif event.key == pygame.K_DOWN and direction != (0, -CELL_SIZE):
                    direction = (0, CELL_SIZE)

                elif event.key == pygame.K_LEFT and direction != (CELL_SIZE, 0):
                    direction = (-CELL_SIZE, 0)

                elif event.key == pygame.K_RIGHT and direction != (-CELL_SIZE, 0):
                    direction = (CELL_SIZE, 0)

    # GAME LOGIC
    if game_started and not game_over:

        # Move snake
        head_x = snake[0][0] + direction[0]
        head_y = snake[0][1] + direction[1]

        new_head = (head_x, head_y)

        snake.insert(0, new_head)

        # Check food collision
        if new_head == food:

            score += 1

            # Generate new food
            while True:

                new_food = (
                    random.randrange(0, WIDTH, CELL_SIZE),
                    random.randrange(0, HEIGHT, CELL_SIZE)
                )

                if new_food not in snake:
                    food = new_food
                    break

        else:
            snake.pop()

        # Check wall collision
        if (
            head_x < 0 or head_x >= WIDTH
            or head_y < 0 or head_y >= HEIGHT
        ):

            game_over = True

        # Check snake collision
        if new_head in snake[1:]:

            game_over = True

    # DRAWING

    if not game_started:

        draw_start_screen()

    elif game_over:

        draw_game_over()

    else:

        screen.fill(BLACK)

        # Draw snake
        for segment in snake:

            pygame.draw.rect(
                screen,
                GREEN,
                (segment[0], segment[1], CELL_SIZE, CELL_SIZE)
            )

        # Draw food
        pygame.draw.rect(
            screen,
            RED,
            (food[0], food[1], CELL_SIZE, CELL_SIZE)
        )

        # Draw UI
        draw_ui()

        pygame.display.flip()

    clock.tick(10)

pygame.quit()
