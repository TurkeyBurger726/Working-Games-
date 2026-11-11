
import random

# Ask the player to enter their name
my_name = input("Enter your name: ")

# Check if the player is Ben and display a special welcome message
if my_name == "Ben":
    print("Welcome back, master Benjamin! Ready to play?")

    # Ask if Ben wants to continue playing or exit the game
    if input("Enter 'yes' to continue or 'no' to exit: ").lower() == "no":
        print("Goodbye, master Benjamin!")
        exit()

# Display a special message if the player's name is Femi
if my_name.lower() == "femi":
    print("You love Lyla!")

# Welcome the player to the game
print(f"Hello, {my_name}! Welcome to Rock, Paper, Scissors!")

# Create a list containing all possible choices
choices = ["rock", "paper", "scissors"]

# Randomly select one choice for the computer
answer = random.choice(choices)
print(f"Computer chose: {answer}")

# Print 5 random choices to demonstrate random.choice()
for i in range(5):
    print(random.choice(choices))

# Create a variable to keep track of the player's wins
wins = 0

# Run the game for 3 rounds
for round_num in range(1, 4):
    print(f"\nRound {round_num}")

    # Ask the player to enter their choice
    user_choice = input("Enter your choice (rock, paper, or scissors): ").lower()

    # Check that the player has entered a valid choice
    if user_choice not in choices:
        print("Invalid choice! Please try again.")
        continue

    # Randomly generate the computer's choice
    computer_choice = random.choice(choices)

    # Display the computer's choice
    print(f"Computer chose {computer_choice}.")

    # Check if both players selected the same option
    if user_choice == computer_choice:
        print("It's a tie!")

    # Check if the player has selected the winning combination
    elif (
        (user_choice == "rock" and computer_choice == "scissors") or
        (user_choice == "paper" and computer_choice == "rock") or
        (user_choice == "scissors" and computer_choice == "paper")
    ):
        print("You won this round!")

        # Add 1 to the player's total wins
        wins += 1

    # If neither a tie nor a player win, the computer wins
    else:
        print("Computer won this round!")

# Display the player's final score after all rounds
print(f"\nYou won {wins} out of 3 rounds!")
