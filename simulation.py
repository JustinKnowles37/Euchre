import argparse
import random
from typing import Callable

from cards import card_int, suit_int
from game import EuchreGame, SimpleStrategy

"""
simulation.py — Monte Carlo hand simulations for Euchre EV
"""


class SimulationStats:
    def __init__(self):
        self.count = 0
        self.tricks = 0
        self.points = 0
        self.wins = 0

    def record(self, outcome: dict):
        self.count += 1
        self.tricks += outcome["tricks"]
        self.points += outcome["points"]
        if outcome["is_win"]:
            self.wins += 1

    def report(self):
        return {
            "count": self.count,
            "avg_tricks": self.tricks / self.count if self.count else 0,
            "avg_points": self.points / self.count if self.count else 0,
            "win_rate": self.wins / self.count if self.count else 0,
        }


def simulate_hand(
    fixed_hand: list[int],
    fixed_upcard: int,
    fixed_seat: int,
    trials: int,
    force_suit: int = None,
    force_alone_choice: bool = False,
    rng_seed: int = None,
    verbose: bool = False,
):
    """
    fixed_seat of 0 is dealer
    """
    stats = SimulationStats()
    rng = random.Random(rng_seed)

    for i in range(trials):
        game = EuchreGame(
            strategies=[SimpleStrategy() for _ in range(4)], verbose=verbose
        )

        # Adjust fixed_seat relative to the dealer
        relative_seat = (fixed_seat + game.dealer) % 4

        outcome = game.play_hand(
            True,
            fixed_hand,
            fixed_upcard,
            relative_seat,
            force_suit,
            force_alone_choice,
            rng,
        )
        stats.record(outcome)

    return stats.report()


# Example CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=50000)
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    hand = ["Jc", "Js", "Ac", "Kc", "Qc"]
    upcard = "9c"
    seat = 0
    # seat = 1
    # seat = 2
    # seat = 3
    force_suit_name = None
    # force_suit_name = "clubs"
    # force_suit_name = "diamonds"
    # force_suit_name = "hearts"
    # force_suit_name = "spades"
    force_alone_choice = None
    # force_alone_choice = False
    # force_alone_choice = True

    hand_int = card_int(hand)
    upcard_int = card_int(upcard)
    force_suit = suit_int(force_suit_name)
    """print("Simulate calling trump always")
    report_call = simulate_hand(
        example_hand,
        example_upcard,
        fixed_seat=0,
        trials=args.trials,
        # call_override=lambda *a, **k: (0, False),
        call_override=lambda *a, **k: None,
        rng_seed=42,
    )
    print(report_call)"""

    # print("Simulate passing always")
    report_pass = simulate_hand(
        hand_int,
        upcard_int,
        seat,
        args.trials,
        force_suit,
        force_alone_choice,
        args.seed,
        args.verbose,
    )
    print(report_pass)
