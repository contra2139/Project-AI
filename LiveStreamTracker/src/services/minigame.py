import random

class MinigameModule:
    """
    Module for running minigames like random giveaways.
    """
    def __init__(self):
        self.participants = set()

    def add_participant(self, username):
        self.participants.add(username)

    def pick_winner(self):
        if not self.participants:
            return None
        return random.choice(list(self.participants))

    def reset(self):
        self.participants.clear()
